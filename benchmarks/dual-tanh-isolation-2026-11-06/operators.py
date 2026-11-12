"""Predeclared 1-bit associative-field ablation: dual tanh vs matched controls.

True packed 256-bit stored memories, all members in the original 256-pattern
Witness field, NO Hamming preselector, ANN, learned semantic embedding or
post-hoc chosen refinement strength. Temporary float arithmetic is necessary
for the original HingeZero dual-tanh operator.

All nonlinear candidates share original EPS, LAMBDA, eight steps and
normalization. The original HingeZero_Core.py source remains unchanged.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
import re
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import time

import numpy as np

from HingeZero_Core import (
    HZ_ALPHA, HZ_EPS, HZ_LAMBDA, HZ_STEPS, HZ_TOP,
    HingeZeroWitness, hinge_phi, _unit,
)

BITS = 256
BYTES = BITS // 8
METHODS = ("zero", "tanh", "tanh2", "dual025", "dual45")


def packed_from_text(text: str) -> bytes:
    """Signed hashing to 256 packed bits; NOT semantic understanding."""
    tokens = re.findall(r"[a-z0-9_]+", text.lower())
    if not tokens:
        raise ValueError("Cannot encode empty source text")
    votes = [0] * BITS
    for token, count in Counter(tokens).items():
        sign_bytes = hashlib.shake_256(
            b"HZ_DUAL_ABLATION_1BIT_V1\x00" + token.encode()
        ).digest(BYTES)
        weight = 1.0 + math.log(count)
        for i in range(BITS):
            votes[i] += weight if (sign_bytes[i // 8] >> (i % 8)) & 1 else -weight
    arr = bytearray(BYTES)
    for i, vote in enumerate(votes):
        if vote > 0:
            arr[i // 8] |= 1 << (i % 8)
    return bytes(arr)


def unpack(code: bytes) -> np.ndarray:
    if type(code) is not bytes or len(code) != BYTES:
        raise ValueError("Memory must be exactly 32 bytes/256 bits")
    bits = np.unpackbits(np.frombuffer(code, dtype=np.uint8),
                         bitorder="little")
    return bits.astype(np.float32) * 2.0 - 1.0


def as_packed(bits: np.ndarray) -> bytes:
    if bits.shape != (BITS,) or not np.all(np.isin(bits, [-1, 1])):
        raise ValueError("Expected bipolar 256-element input")
    return np.packbits((bits > 0).astype(np.uint8), bitorder="little").tobytes()


def flip(code: bytes, count: int, rng: np.random.Generator) -> bytes:
    if not 0 <= count <= BITS:
        raise ValueError("Illegal bit flip count")
    b = bytearray(code)
    for j in rng.choice(BITS, size=count, replace=False):
        k = int(j)
        b[k // 8] ^= (1 << (k % 8))
    return bytes(b)


@dataclass(frozen=True)
class Retrieval:
    target: int
    chosen: int
    elapsed_ms: float
    witness_valid: bool
    target_similarity: float
    target_margin: float
    drift: float


class AttractorBank:
    def __init__(self, packed: list[bytes]):
        if not 2 <= len(packed) <= HZ_TOP:
            raise ValueError("Original full field requires 2..256 records")
        if any(type(x) is not bytes or len(x) != BYTES for x in packed):
            raise ValueError("Bank must contain only packed 1-bit memories")
        if len(set(packed)) != len(packed):
            raise ValueError("Duplicate 1-bit identities would make target ID ambiguous")
        self.packed = tuple(packed)
        self.packed_bytes = sum(len(x) for x in packed)
        self.matrix = np.stack([unpack(x) for x in packed])
        self.witness = HingeZeroWitness(
            self.matrix, np.zeros(len(packed), dtype=np.float32)
        )
        if self.witness.field_memories.shape != (len(packed), BITS):
            raise AssertionError("Not a full, original Witness field")
        self.memories = self.witness.memories

    def iterate(self, query: np.ndarray, method: str, steps: int = HZ_STEPS):
        if method not in METHODS or steps not in (0, 1, 2, 4, 8):
            raise ValueError("Unsupported matched control")
        x = _unit(query)
        if steps == 0 or method == "zero":
            return x
        if method == "dual45":
            return self.witness.refine(x) if steps == HZ_STEPS else self._iterate(x, method, steps)
        # For all ablations, preserve exact stored input just like original.
        idx = self.witness._stored_index(x)
        if idx is not None:
            return self.memories[idx].copy()
        return self._iterate(x, method, steps)

    def _iterate(self, x: np.ndarray, method: str, steps: int):
        for _ in range(steps):
            h = self.witness.field_memories @ x
            if method == "tanh":
                response = np.tanh(h)
            elif method == "tanh2":
                response = np.tanh(2.0 * h)
            elif method == "dual025":
                response = hinge_phi(h, alpha=0.25)
            elif method == "dual45":
                response = hinge_phi(h, alpha=HZ_ALPHA)
            else:
                raise ValueError(method)
            field = self.witness.field_memories.T @ response
            field /= float(np.sum(np.abs(response))) + 1e-12
            x = _unit((1.0 - HZ_LAMBDA) * x + HZ_EPS * field)
        return x

    def retrieve(self, cue: bytes, method: str, target: int, steps: int = 8) -> Retrieval:
        if not 0 <= target < len(self.packed):
            raise ValueError("Invalid target")
        start = time.perf_counter_ns()
        query = _unit(unpack(cue))
        refined = self.iterate(query, method, steps)
        scores = self.memories @ refined
        locked = self.witness.observe(query, scores)
        valid = self.witness.verify(locked)
        selected = int(locked.candidate_index)
        others = np.delete(scores, target)
        margin = float(scores[target] - np.max(others))
        dt = (time.perf_counter_ns() - start) / 1e6
        return Retrieval(target, selected, dt, bool(valid),
                         float(scores[target]), margin,
                         float(1.0 - np.dot(query, refined)))


def make_correlated_bank(seed: int, count: int, shared: float) -> list[bytes]:
    """Controlled, non-identical binary attractors grouped by latent family."""
    if not 0 <= shared <= .95 or count % 8:
        raise ValueError("Invalid family setup")
    rng = np.random.default_rng(seed)
    prototypes = rng.choice(np.array([-1.0, 1.0], dtype=np.float32),
                            size=(8, BITS))
    codes: list[bytes] = []
    for i in range(count):
        if shared == 0:
            vector = rng.choice(np.array([-1.0, 1.0], np.float32), size=BITS)
        else:
            vector = prototypes[i % 8].copy()
            n = int(round((1.0 - shared) * BITS))
            indices = rng.choice(BITS, n, replace=False)
            vector[indices] *= -1
        code = as_packed(vector)
        if code in codes:
            # Never silently reuse a stored pattern and mislabel retrieval.
            raise RuntimeError("Duplicate synthetic identity")
        codes.append(code)
    return codes


def real_fineweb(count: int = 128, max_chars: int = 1200):
    """Authentic FineWeb public source excerpts via dataset server (no filler)."""
    if not 32 <= count <= 200:
        raise ValueError("Small-source real-data control only: 32..200")
    data = []
    seen_ids = set()
    seen_codes = set()
    offset = 0
    while len(data) < count:
        params = urlencode({
            "dataset": "HuggingFaceFW/fineweb",
            "config": "sample-10BT",
            "split": "train",
            "offset": offset,
            "length": min(100, count - len(data) + 10),
        })
        req = Request("https://datasets-server.huggingface.co/rows?" + params,
                      headers={"User-Agent": "HingeZero-DualTanh-Control/1.0"})
        for attempt in range(3):
            try:
                with urlopen(req, timeout=75) as result:
                    payload = json.load(result)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
        rows = payload.get("rows") or []
        if not rows:
            raise RuntimeError("Source API returned no real records")
        for item in rows:
            item = item.get("row") or {}
            uid, text = item.get("id"), item.get("text")
            if not isinstance(uid, str) or not isinstance(text, str):
                continue
            if uid in seen_ids:
                continue
            seen_ids.add(uid)
            excerpt = text[:max_chars]
            words = re.findall(r"[a-z0-9_]+", excerpt.lower())
            if len(words) < 70:
                continue
            code = packed_from_text(excerpt)
            if code in seen_codes:
                continue
            seen_codes.add(code)
            data.append((uid, excerpt, code, words))
            if len(data) == count:
                break
        offset += len(rows)
        if offset > 8000:
            raise RuntimeError("Insufficient original FineWeb source rows")
    return data
