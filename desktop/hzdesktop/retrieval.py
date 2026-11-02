"""HingeZero Desktop retrieval using David Duffy's original HingeZero Core.

The original HingeZero_Core.py is bundled unchanged beside this module.
Witness verifies *stored state identity*, not factual truth or relevance.
The desktop vault remains encrypted; this is not the billion-pattern C++ backend.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import math
import re
import threading

import numpy as np

from .HingeZero_Core import (
    HingeZeroRetainingLoop, HingeZeroState, HingeZeroWitness, hinge_phi,
)

DIMS = 256
MAX_CANDIDATES = 256
STOP = set("the a an and or are is i you we it this that was were be in on to of for with what when where who how my me do did at from about please can".split())


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w']+", text.lower(), flags=re.UNICODE)
            if len(w) > 1 and w not in STOP]


def lexical_vector(text: str) -> list[float]:
    values = np.zeros(DIMS, dtype=np.float32)
    for word, count in Counter(tokens(text)).items():
        digest = hashlib.blake2b(word.encode("utf-8"), digest_size=8, person=b"HZMEMv1").digest()
        idx = int.from_bytes(digest[:4], "little") % DIMS
        values[idx] += (1.0 if digest[4] % 2 == 0 else -1.0) * (1.0 + math.log(count))
    return _unit(values).tolist()


def _unit(values) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise ValueError("Expected finite, one-dimensional memory vector")
    norm = float(np.linalg.norm(array))
    return array / norm if norm > 1e-12 else np.zeros_like(array)


def phi(value: float, alpha: float = 4.5) -> float:
    return float(hinge_phi(value, alpha))


def hz_refine(query, candidates, steps: int = 8) -> list[float]:
    """Use the original, unchanged 8-step HingeZero Core; 0 means no refinement.

    Other step counts are deliberately rejected: the original core has fixed
    HZ_STEPS=8, and silently ignoring requested values would mislead users.
    """
    if steps not in (0, 8):
        raise ValueError("Original HingeZero Core supports 0 (unrefined) or 8 steps")
    cue = _unit(query)
    if not candidates or steps == 0:
        return cue.tolist()
    bank = np.asarray(candidates, dtype=np.float32)
    if bank.ndim != 2 or bank.shape[1] != cue.size or not np.all(np.isfinite(bank)):
        raise ValueError("Incompatible associative memory bank")
    witness = HingeZeroWitness(bank, np.zeros(len(bank), dtype=np.float32))
    return witness.refine(cue).tolist()


class RetainedMemorySession:
    """Keep an authentic HingeZeroRetainingLoop over a stable candidate bank.

    When candidate identities or vector space change, reset safely. Checkpoints
    are session-local; only encrypted memory records persist across app restarts.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._signature = None
        self._loop = None

    def reset(self):
        with self._lock:
            self._signature = None
            self._loop = None

    def update(self, witness, signature, cue, locked):
        with self._lock:
            if self._signature != signature or self._loop is None:
                self._loop = HingeZeroRetainingLoop(witness, locked)
                self._signature = signature
                return {"checkpoint": locked.candidate_index,
                        "committed": True, "rolled_back": False, "reset": True}
            result = self._loop.step(cue=cue)
            checkpoint = result["state"]
            if not self._loop.witness.verify(checkpoint):
                raise RuntimeError("HingeZero retaining checkpoint failed Witness verification")
            return {"checkpoint": checkpoint.candidate_index,
                    "committed": result["committed"],
                    "rolled_back": result["rolled_back"], "reset": False}

    def disturb(self, disturbance):
        """Explicit drift test / rollback on the retained checkpoint."""
        with self._lock:
            if self._loop is None:
                raise ValueError("Search once to establish a retained checkpoint")
            result = self._loop.step(disturbance=disturbance)
            return {"checkpoint": result["state"].candidate_index,
                    "committed": result["committed"],
                    "rolled_back": result["rolled_back"],
                    "drift": result["drift"]}


def search(records: list[dict], query: str, limit: int = 5,
           query_embedding: list[float] | None = None,
           embedding_model: str = "", steps: int = 8,
           session: RetainedMemorySession | None = None) -> list[dict]:
    """Rank candidates using original HingeZero refine + Witness verification.

    A lexical shortlist remains part of the desktop retrieval architecture.
    No claim is made about billion-scale throughput or semantic accuracy.
    """
    if not isinstance(query, str) or not query.strip():
        return []
    if steps not in (0, 8):
        raise ValueError("Original HingeZero Core supports 0 or 8 steps")
    qlex = _unit(lexical_vector(query))
    qsemantic = _unit(query_embedding) if query_embedding is not None else None
    if qsemantic is not None and not np.any(qsemantic):
        qsemantic = None
    pool = []
    for rec in records:
        lex = _unit(lexical_vector(str(rec["title"]) + " " + str(rec["content"])))
        lexical_score = max(0.0, float(qlex @ lex))
        score = lexical_score
        semantic = None
        if (qsemantic is not None and rec.get("embedding_model") == embedding_model
                and isinstance(rec.get("embedding"), list)
                and len(rec["embedding"]) == qsemantic.size):
            candidate = np.asarray(rec["embedding"], dtype=np.float32)
            if np.all(np.isfinite(candidate)):
                semantic = _unit(candidate)
                score = 0.15 * lexical_score + 0.85 * max(0.0, float(qsemantic @ semantic))
        if score > 1e-9:
            pool.append((score, rec, lex, semantic))
    pool.sort(key=lambda value: (-value[0], str(value[1]["id"])))
    pool = pool[:MAX_CANDIDATES]
    if not pool:
        if session is not None:
            session.reset()
        return []
    semantic_space = qsemantic is not None and all(item[3] is not None for item in pool)
    cue = qsemantic if semantic_space else qlex
    bank = np.stack([sem if semantic_space else lex for _, _, lex, sem in pool])
    evidence = np.asarray([base for base, *_ in pool], dtype=np.float32)
    witness = HingeZeroWitness(bank, evidence)
    refined = witness.refine(cue) if steps == 8 else cue.copy()
    scores = witness.memories @ refined
    chosen = witness.observe(cue, scores)
    if not witness.verify(chosen):
        raise RuntimeError("Original HingeZero Witness rejected retrieved state")
    signature = (tuple(str(rec["id"]) for _, rec, _, _ in pool),
                 "semantic" if semantic_space else "lexical",
                 embedding_model if semantic_space else "",
                 int(bank.shape[1]))
    retention = (session.update(witness, signature, cue, chosen)
                 if session is not None else None)
    found = []
    for index, (base, rec, _, _) in enumerate(pool):
        state = HingeZeroState(index, witness.memories[index])
        if not witness.verify(state):
            raise RuntimeError("Original HingeZero Witness rejected stored candidate")
        similarity = max(0.0, float(scores[index]))
        found.append({
            "score": 0.80 * base + 0.20 * similarity,
            "base_score": base, "record": rec,
            "witness_verified": True,
            "witness_selected": index == chosen.candidate_index,
            "retained_checkpoint": bool(
                retention and index == retention["checkpoint"]),
            "retention_committed": bool(retention and retention["committed"]),
        })
    found.sort(key=lambda item: (-item["score"], str(item["record"]["id"])))
    return found[:max(1, min(int(limit), 20))]
