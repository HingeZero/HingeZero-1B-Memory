"""Encrypted on-disk vault. All user content and embeddings are encrypted."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import threading
from functools import wraps
import uuid

from .token_index import MAX_QUERY_TERMS, terms, key_for_term

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITERATIONS = 600_000
MAX_RECORDS = 1_000_000_000  # Storage-addressing ceiling; 1B real records NOT benchmarked.
BROWSE_PAGE_SIZE = 200
MAX_NOTE_LENGTH = 10_000


def _derive(password: str, salt: bytes) -> bytes:
    if not password:
        raise ValueError("Passphrase required")
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=salt, iterations=ITERATIONS).derive(password.encode("utf-8"))


def _private_dir(path: Path, restrict_existing: bool = True) -> None:
    existed = path.exists()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    # The app owns its vault directory, but not an arbitrary folder chosen for backups.
    if os.name == "posix" and (restrict_existing or not existed):
        # 0700 is required for a private DIRECTORY: only its owner may traverse it.
        # Semgrep rule incorrectly suggests 0644 (file permissions) for directories.
        os.chmod(path, 0o700)  # nosemgrep: python.lang.security.audit.insecure-file-permissions.insecure-file-permissions


def _private_file(path: Path) -> None:
    if os.name == "posix" and path.exists():
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def synchronized(fn):
    @wraps(fn)
    def run(self, *args, **kwargs):
        with self.lock:
            return fn(self, *args, **kwargs)
    return run


class Vault:
    def __init__(self, path: str | Path, password: str, create: bool = False):
        self.path = Path(path).expanduser().resolve()
        if create and len(password) < 12:
            raise ValueError("Use a passphrase with at least 12 characters")
        if create and self.path.exists():
            raise FileExistsError("A vault already exists at this path")
        if not create and not self.path.is_file():
            raise FileNotFoundError("Vault file not found")
        if create:
            _private_dir(self.path.parent)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        try:
            self.db.execute("PRAGMA secure_delete=ON")
            self.db.execute("PRAGMA journal_mode=DELETE")
            self.db.execute("PRAGMA synchronous=FULL")
            if create:
                self.db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value BLOB NOT NULL)")
                self.db.execute("CREATE TABLE records (id TEXT PRIMARY KEY, payload BLOB NOT NULL)")
                salt = secrets.token_bytes(16)
                self.key = _derive(password, salt)
                self.db.execute("INSERT INTO meta VALUES (?, ?)", ("salt", salt))
                self.db.execute("INSERT INTO meta VALUES (?, ?)", ("version", b"1"))
                self.db.execute("INSERT INTO meta VALUES (?, ?)", ("verifier", self._seal(b"HINGEZERO-VAULT-v1", b"check")))
                self.db.commit()
                _private_file(self.path)
            else:
                salt_row = self.db.execute("SELECT value FROM meta WHERE key='salt'").fetchone()
                version = self.db.execute("SELECT value FROM meta WHERE key='version'").fetchone()
                if not salt_row or not version or version[0] != b"1":
                    raise ValueError("Invalid or unsupported vault format")
                self.key = _derive(password, salt_row[0])
                verifier = self.db.execute("SELECT value FROM meta WHERE key='verifier'").fetchone()
                try:
                    if not verifier or self._open(verifier[0], b"check") != b"HINGEZERO-VAULT-v1":
                        raise ValueError("Invalid vault password")
                except InvalidTag as e:
                    raise ValueError("Invalid vault password or corrupted vault") from e
        except Exception:
            self.db.close()
            raise
        try:
            self._ensure_index()
        except Exception:
            self.db.close()
            raise

    def _ensure_index(self) -> None:
        """Upgrade existing v1 vaults without changing their encrypted payloads.

        Interrupted migrations restart from scratch on next unlock; the marker
        is only committed after every old record has been indexed.
        """
        with self.db:
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS term_index "
                "(term BLOB NOT NULL, record_id TEXT NOT NULL, "
                "PRIMARY KEY (term, record_id)) WITHOUT ROWID"
            )
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS term_index_by_record "
                "ON term_index(record_id)"
            )
            complete = self.db.execute(
                "SELECT value FROM meta WHERE key='token_index_v1'"
            ).fetchone()
            if complete is None:
                self.db.execute("DELETE FROM term_index")
                for record_id, payload in self.db.execute(
                    "SELECT id, payload FROM records"
                ):
                    record = json.loads(self._open(payload, record_id.encode("ascii")))
                    self._index_record(record_id, record["title"], record["content"])
                self.db.execute(
                    "INSERT INTO meta(key,value) VALUES (?,?)",
                    ("token_index_v1", b"complete"),
                )

    def _index_record(self, record_id: str, title: str, content: str) -> None:
        self.db.executemany(
            "INSERT INTO term_index(term, record_id) VALUES (?,?)",
            ((key_for_term(self.key, word), record_id)
             for word in terms(title + " " + content))
        )

    def _seal(self, plaintext: bytes, aad: bytes) -> bytes:
        nonce = secrets.token_bytes(12)
        return nonce + AESGCM(self.key).encrypt(nonce, plaintext, aad)

    def _open(self, data: bytes, aad: bytes) -> bytes:
        if len(data) < 29:
            raise ValueError("Corrupted encrypted record")
        return AESGCM(self.key).decrypt(data[:12], data[12:], aad)

    @synchronized
    def add(self, title: str, content: str, source: str = "manual",
            embedding: list[float] | None = None, embedding_model: str = "") -> str:
        title = str(title).strip()[:200]
        content = str(content).strip()
        if not content or len(content) > MAX_NOTE_LENGTH:
            raise ValueError("Memory must be between 1 and 10,000 characters")
        if self.count() >= MAX_RECORDS:
            raise ValueError("Vault record ceiling reached: 1,000,000,000")
        record_id = str(uuid.uuid4())
        raw = json.dumps({"title": title or "Untitled", "content": content,
                          "source": source[:400], "embedding": embedding,
                          "embedding_model": embedding_model},
                         ensure_ascii=False).encode("utf-8")
        payload = self._seal(raw, record_id.encode("ascii"))
        with self.db:
            self.db.execute("INSERT INTO records VALUES (?, ?)", (record_id, payload))
            self._index_record(record_id, title or "Untitled", content)
        return record_id

    @synchronized
    def list(self) -> list[dict]:
        result = []
        for record_id, payload in self.db.execute("SELECT id, payload FROM records ORDER BY rowid DESC"):
            record = json.loads(self._open(payload, record_id.encode("ascii")))
            record["id"] = record_id
            result.append(record)
        return result

    @synchronized
    def list_recent(self, limit: int = BROWSE_PAGE_SIZE,
                    before_rowid: int | None = None) -> tuple[list[dict], int | None]:
        """Keyset-paginated encrypted records; does not decrypt the whole vault."""
        limit = max(1, min(int(limit), BROWSE_PAGE_SIZE))
        if before_rowid is not None and before_rowid <= 0:
            return [], None
        if before_rowid is None:
            sql, args = ("SELECT rowid,id,payload FROM records "
                         "ORDER BY rowid DESC LIMIT ?", (limit + 1,))
        else:
            sql, args = ("SELECT rowid,id,payload FROM records "
                         "WHERE rowid < ? ORDER BY rowid DESC LIMIT ?",
                         (before_rowid, limit + 1))
        rows = self.db.execute(sql, args).fetchall()
        next_cursor = rows[limit - 1][0] if len(rows) > limit else None
        output = []
        for _, record_id, payload in rows[:limit]:
            record = json.loads(self._open(payload, record_id.encode("ascii")))
            record["id"] = record_id
            output.append(record)
        return output, next_cursor

    @synchronized
    def search_candidates(self, query: str, limit: int = 256) -> list[dict]:
        """Bounded lexical candidate generation; Witness verifies returned states.

        This does not provide semantic-only matches when words do not overlap.
        """
        words = terms(query)[:MAX_QUERY_TERMS]
        if not words:
            return []
        term_ids = [key_for_term(self.key, word) for word in words]
        placeholders = ",".join("?" for _ in term_ids)
        sql = ("SELECT record_id, COUNT(*) AS overlap FROM term_index "
               "WHERE term IN (" + placeholders + ") "
               "GROUP BY record_id ORDER BY overlap DESC, record_id LIMIT ?")
        candidates = self.db.execute(sql, (*term_ids, max(1, min(int(limit), 256))))
        output = []
        for record_id, _ in candidates.fetchall():
            row = self.db.execute(
                "SELECT payload FROM records WHERE id=?", (record_id,)
            ).fetchone()
            if row is None:
                raise RuntimeError("Vault lexical index points to missing record")
            record = json.loads(self._open(row[0], record_id.encode("ascii")))
            record["id"] = record_id
            output.append(record)
        return output

    @synchronized
    def count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM records").fetchone()[0])

    @synchronized
    def delete(self, record_id: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM term_index WHERE record_id=?", (record_id,))
            self.db.execute("DELETE FROM records WHERE id=?", (record_id,))

    @synchronized
    def backup_encrypted(self, destination: str | Path) -> None:
        # Do not resolve the destination: doing so follows dangling symlinks
        # and can silently create a file outside the user-selected path.
        dest = Path(destination).expanduser().absolute()
        if dest == self.path or dest.resolve() == self.path:
            raise ValueError("Backup destination must differ from active vault")
        if dest.is_symlink() or dest.exists():
            raise FileExistsError("Refusing to overwrite or follow an existing backup path")
        # Never change permissions of a directory picked by the user.
        _private_dir(dest.parent, restrict_existing=False)
        # Atomically reserve the output using owner-only mode; never follow a symlink.
        fd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
        try:
            with sqlite3.connect(dest) as output:
                self.db.backup(output)
            _private_file(dest)
        except Exception:
            dest.unlink(missing_ok=True)
            raise

    @synchronized
    def close(self) -> None:
        self.db.close()
        self.key = b""  # Best effort only; Python can't guarantee RAM erasure.

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
