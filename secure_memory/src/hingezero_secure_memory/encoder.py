"""Deterministic local text adapter, not a semantic language model."""
import hashlib
import re
import numpy as np

ENCODER_ID = "hz-local-hash-v1-256"


def encode(text: str) -> np.ndarray:
    if not isinstance(text, str) or not text.strip() or len(text) > 4096:
        raise ValueError("Text input must contain 1 to 4096 characters")
    tokens = re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
    if not tokens:
        raise ValueError("Text contains no indexable words")
    vec = np.zeros(256, dtype=np.float32)
    terms = tokens + [" ".join(tokens[i:i+2]) for i in range(len(tokens)-1)]
    for term in terms:
        raw = hashlib.blake2b(term.encode("utf-8"), digest_size=8, person=b"HZmem01").digest()
        idx = int.from_bytes(raw[:4], "little") % vec.size
        vec[idx] += 1 if raw[4] & 1 else -1
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-12:
        raise ValueError("Cannot encode this input")
    return vec / norm
