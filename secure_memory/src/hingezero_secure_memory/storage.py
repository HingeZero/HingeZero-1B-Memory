"""Encrypted local store and capability-scoped interface to the full HingeZero witness."""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import hmac
import json
import math
import re
import os
import secrets
import sqlite3
import stat
import threading
import uuid

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from HingeZero_Core import HingeZeroWitness
from .encoder import encode, ENCODER_ID

MAX_RECORDS = 4096
MAX_TEXT = 4096
MAX_QUERY = 1024
MAX_SOURCE = 256
MAX_DAYS = 365
SENSITIVE = frozenset({"health", "medical", "biometric", "financial", "credentials", "children", "sensitive"})


class AccessDenied(PermissionError):
    pass


class IntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class MemoryResult:
    status: str
    record_id: str | None = None
    text: str | None = None
    source: str | None = None
    score: float | None = None
    margin: float | None = None
    verified: bool = False

    def as_dict(self):
        return vars(self).copy()


def _now():
    return datetime.now(timezone.utc)


def _seconds(dt):
    return int(dt.timestamp())


def _check_text(value, limit, name):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise ValueError(f"{name} must be a nonempty string of at most {limit} characters")
    return value


def _reject_obvious_secrets(text):
    if re.search(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----", text, re.I) or re.search(r"(?:api[_ -]?key|access[_ -]?token|password|secret[_ -]?key|bearer)[ \t]*[:=][ \t]*[^\s]{6,}", text, re.I):
        raise AccessDenied("Possible credential in memory; credentials must not be saved")


def _check_scope(scope):
    _check_text(scope, 48, "scope")
    if not all(c.isascii() and (c.islower() or c.isdigit() or c in "_-") for c in scope):
        raise ValueError("Scope must use lowercase ASCII letters, digits, _ or -")
    if scope in SENSITIVE:
        raise AccessDenied("Sensitive-data categories are disabled in this developer preview")
    return scope


def _secure_path(db_path):
    path = Path(db_path).expanduser().absolute()
    # Refuse symlinks along the full path, including existing ancestors.
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AccessDenied("Symbolic links are not permitted for the database path")
    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700)
    folder_mode = path.parent.stat().st_mode
    if not stat.S_ISDIR(folder_mode) or folder_mode & 0o077 or (hasattr(os, "geteuid") and path.parent.stat().st_uid != os.geteuid()):
        raise AccessDenied("Database directory must be accessible to its owner only (mode 0700)")
    if path.exists():
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o077 or (hasattr(os, "geteuid") and path.stat().st_uid != os.geteuid()):
            raise AccessDenied("Database must be a private regular file (mode 0600)")
    else:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        os.close(fd)
    return path


class SecureMemory:
    """Owner-operated local vault. Applications must use separately granted capabilities."""

    def __init__(self, db_path, passphrase):
        if not isinstance(passphrase, str) or len(passphrase) < 16:
            raise ValueError("Use a strong passphrase of at least 16 characters")
        self.path = _secure_path(db_path)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.path), timeout=8, check_same_thread=False, isolation_level=None)
        try:
            self._db.execute("PRAGMA trusted_schema=OFF")
            self._db.execute("PRAGMA secure_delete=ON")
            self._db.execute("PRAGMA journal_mode=DELETE")
            self._db.execute("PRAGMA busy_timeout=8000")
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS config (name TEXT PRIMARY KEY, value BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY, scope TEXT NOT NULL, created INTEGER NOT NULL,
                    expires INTEGER NOT NULL, ciphertext BLOB NOT NULL);
                CREATE INDEX IF NOT EXISTS records_scope_expires ON records(scope, expires);
                CREATE TABLE IF NOT EXISTS capabilities (
                    id TEXT PRIMARY KEY, token_hash BLOB NOT NULL, label TEXT NOT NULL,
                    scope TEXT NOT NULL, right TEXT NOT NULL CHECK(right IN ('read','write','readwrite')),
                    revoked INTEGER NOT NULL DEFAULT 0,
                    expires INTEGER NOT NULL);
            """)
            row = self._db.execute("SELECT value FROM config WHERE name='salt'").fetchone()
            if row is None:
                if self._db.execute("SELECT COUNT(*) FROM records").fetchone()[0]:
                    raise IntegrityError("Missing encryption metadata")
                salt = secrets.token_bytes(16)
                first_run = True
            else:
                salt = row[0]
                first_run = False
            if len(salt) != 16:
                raise IntegrityError("Encryption metadata corrupted")
            self._key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode("utf-8"))
            self._aes = AESGCM(self._key)
            if first_run:
                seal = self._seal(b"hingezero-key-check", b"key-check-v1")
                self._db.execute("BEGIN IMMEDIATE")
                try:
                    if self._db.execute("SELECT value FROM config WHERE name='salt'").fetchone():
                        raise IntegrityError("Vault was initialized concurrently; reopen")
                    self._db.execute("INSERT INTO config VALUES (?,?)", ("salt", salt))
                    self._db.execute("INSERT INTO config VALUES (?,?)", ("key_check", seal))
                    self._db.execute("INSERT INTO config VALUES (?,?)", ("encoder", ENCODER_ID.encode()))
                    self._db.execute("COMMIT")
                except Exception:
                    self._db.execute("ROLLBACK")
                    raise
            else:
                check = self._db.execute("SELECT value FROM config WHERE name='key_check'").fetchone()
                if not check:
                    raise IntegrityError("Missing key validation metadata")
                try:
                    if self._open(check[0], b"key-check-v1") != b"hingezero-key-check":
                        raise AccessDenied("Invalid vault credentials")
                except InvalidTag as exc:
                    raise AccessDenied("Invalid vault credentials or modified vault") from exc
                enc = self._db.execute("SELECT value FROM config WHERE name='encoder'").fetchone()
                if not enc or enc[0] != ENCODER_ID.encode():
                    raise IntegrityError("Unsupported encoder version")
        except Exception:
            self._db.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        with self._lock:
            self._db.close()

    def _seal(self, raw, aad):
        nonce = secrets.token_bytes(12)
        return nonce + self._aes.encrypt(nonce, raw, aad)

    def _open(self, ciphertext, aad):
        if len(ciphertext) < 29:
            raise IntegrityError("Truncated encrypted record")
        return self._aes.decrypt(ciphertext[:12], ciphertext[12:], aad)

    @staticmethod
    def _aad(record_id, scope, created, expires):
        return f"hz-record-v1|{record_id}|{scope}|{created}|{expires}".encode()

    def _purge_expired(self):
        self._db.execute("DELETE FROM records WHERE expires<=?", (_seconds(_now()),))

    def _verify_token(self, token, scope, right):
        _check_scope(scope)
        if not isinstance(token, str) or not token.startswith("hzm_") or len(token) > 120:
            raise AccessDenied("Valid capability token required")
        parts = token.split("_", 2)
        if len(parts) != 3:
            raise AccessDenied("Invalid capability")
        row = self._db.execute("SELECT token_hash,scope,right,revoked,expires FROM capabilities WHERE id=?", (parts[1],)).fetchone()
        if not row or row[3] or row[4] <= _seconds(_now()) or row[1] != scope or (row[2] != "readwrite" and row[2] != right):
            raise AccessDenied("Capability does not permit this operation")
        actual = hmac.digest(self._key, token.encode(), "sha256")
        if not hmac.compare_digest(actual, row[0]):
            raise AccessDenied("Invalid capability")

    def grant(self, label, scope="general", right="read", days=30):
        _check_text(label, 72, "application label")
        _check_scope(scope)
        if right not in {"read", "write", "readwrite"}:
            raise ValueError("Permission must be read, write or readwrite")
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 90:
            raise ValueError("Capability lifetime must be between 1 and 90 days")
        cap_id = uuid.uuid4().hex
        token = f"hzm_{cap_id}_{secrets.token_urlsafe(32)}"
        digest = hmac.digest(self._key, token.encode(), "sha256")
        with self._lock:
            self._db.execute("INSERT INTO capabilities(id,token_hash,label,scope,right,expires) VALUES(?,?,?,?,?,?)", (cap_id,digest,label,scope,right,_seconds(_now()+timedelta(days=days)) ))
        return cap_id, token

    def revoke(self, cap_id):
        _check_text(cap_id, 48, "capability ID")
        with self._lock:
            cur = self._db.execute("UPDATE capabilities SET revoked=1 WHERE id=?", (cap_id,))
            return cur.rowcount == 1

    def remember(self, text, source, *, scope="general", consent=False, days=30):
        _check_scope(scope)
        _check_text(text, MAX_TEXT, "memory")
        _reject_obvious_secrets(text)
        _check_text(source, MAX_SOURCE, "source")
        if consent is not True:
            raise AccessDenied("Explicit user authorisation required before saving memory")
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= MAX_DAYS:
            raise ValueError("Retention must be 1 through 365 days")
        vec = encode(text)
        created = _seconds(_now())
        expires = _seconds(_now() + timedelta(days=days))
        record_id = uuid.uuid4().hex
        payload = json.dumps({"text":text,"source":source,"vector":vec.tolist()},separators=(",",":"),ensure_ascii=False).encode("utf-8")
        enc = self._seal(payload, self._aad(record_id,scope,created,expires))
        with self._lock:
            self._purge_expired()
            count = self._db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            if count >= MAX_RECORDS:
                raise AccessDenied("Local memory limit reached; review and remove older records")
            self._db.execute("INSERT INTO records VALUES (?,?,?,?,?)",(record_id,scope,created,expires,enc))
        return record_id

    def remember_as(self, token, text, source, *, scope="general", consent=False, days=30):
        with self._lock:
            self._verify_token(token, scope, "write")
            return self.remember(text,source,scope=scope,consent=consent,days=days)

    def recall(self, query, *, scope="general", min_margin=0.1, min_similarity=0.35):
        _check_scope(scope)
        _check_text(query, MAX_QUERY, "query")
        if isinstance(min_margin,bool) or not isinstance(min_margin,(int,float)) or not math.isfinite(min_margin) or not 0 <= min_margin <= 2:
            raise ValueError("Invalid confidence margin")
        if isinstance(min_similarity, bool) or not isinstance(min_similarity, (int,float)) or not math.isfinite(min_similarity) or not -1 <= min_similarity <= 1:
            raise ValueError("Invalid minimum similarity")
        cue = encode(query)
        with self._lock:
            self._purge_expired()
            rows = self._db.execute("SELECT id,scope,created,expires,ciphertext FROM records WHERE scope=? ORDER BY id",(scope,)).fetchall()
        if not rows:
            return MemoryResult(status="no_memory")
        vectors = []
        data = []
        for rid, rscope, created, expires, ciphertext in rows:
            try:
                raw = self._open(ciphertext, self._aad(rid,rscope,created,expires))
                item = json.loads(raw)
                vector = np.asarray(item["vector"], dtype=np.float32)
                if vector.shape != (256,) or not np.all(np.isfinite(vector)):
                    raise IntegrityError("Stored vector is invalid")
                _check_text(item["text"], MAX_TEXT, "memory")
                _check_text(item["source"], MAX_SOURCE, "source")
                data.append((rid,item))
                vectors.append(vector)
            except (InvalidTag, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise IntegrityError("Encrypted memory verification failed") from exc
        bank = np.stack(vectors)
        witness = HingeZeroWitness(bank, np.zeros(len(bank), dtype=np.float32))
        refined = witness.refine(cue)
        scores = witness.memories @ refined
        ids = np.argsort(-scores, kind="stable")
        best = int(ids[0]); second = int(ids[1]) if len(ids)>1 else None
        margin = float(scores[best]-scores[second]) if second is not None else 2.0
        if float(scores[best]) < min_similarity:
            return MemoryResult(status="no_match", score=float(scores[best]), margin=margin)
        if margin < min_margin:
            return MemoryResult(status="ambiguous", score=float(scores[best]), margin=margin)
        verified = witness.verify(witness.observe(cue, scores))
        if not verified:
            raise IntegrityError("Witness verification failed")
        rid, item = data[best]
        return MemoryResult(status="found",record_id=rid,text=item["text"],source=item["source"],score=float(scores[best]),margin=margin,verified=True)

    def recall_as(self, token, query, *, scope="general", min_margin=0.1, min_similarity=0.35):
        with self._lock:
            self._verify_token(token, scope, "read")
            return self.recall(query, scope=scope, min_margin=min_margin, min_similarity=min_similarity)

    def delete(self, record_id):
        _check_text(record_id, 64, "record ID")
        with self._lock:
            cur = self._db.execute("DELETE FROM records WHERE id=?", (record_id,))
            return cur.rowcount == 1

    def list_metadata(self):
        with self._lock:
            self._purge_expired()
            return [dict(id=x[0],scope=x[1],created=x[2],expires=x[3]) for x in self._db.execute("SELECT id,scope,created,expires FROM records ORDER BY created")]
