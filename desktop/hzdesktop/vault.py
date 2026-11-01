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

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITERATIONS = 600_000
MAX_RECORDS = 20_000
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
            raise ValueError("Vault limit reached: 20,000 memories")
        record_id = str(uuid.uuid4())
        raw = json.dumps({"title": title or "Untitled", "content": content,
                          "source": source[:400], "embedding": embedding,
                          "embedding_model": embedding_model},
                         ensure_ascii=False).encode("utf-8")
        payload = self._seal(raw, record_id.encode("ascii"))
        with self.db:
            self.db.execute("INSERT INTO records VALUES (?, ?)", (record_id, payload))
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
    def count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM records").fetchone()[0])

    @synchronized
    def delete(self, record_id: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM records WHERE id=?", (record_id,))

    @synchronized
    def backup_encrypted(self, destination: str | Path) -> None:
        dest = Path(destination).expanduser().resolve()
        if dest == self.path:
            raise ValueError("Backup destination must differ from active vault")
        if dest.exists():
            raise FileExistsError("Refusing to overwrite an existing backup")
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
