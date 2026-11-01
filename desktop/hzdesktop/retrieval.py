"""Deterministic local lexical retrieval + actual HingeZero dual-tanh refinement.

Embedding vectors from a user-enabled local Ollama instance may be supplied.
Neither method claims full semantic understanding without an embedding model.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

DIMS = 256
STOP = set("the a an and or are is i you we it this that was were be in on to of for with what when where who how my me do did at from about please can".split())


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[\w']+", text.lower(), flags=re.UNICODE) if len(w) > 1 and w not in STOP]


def unit(v: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(x * x for x in v))
    return [x / magnitude for x in v] if magnitude > 1e-12 else [0.0] * len(v)


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def lexical_vector(text: str) -> list[float]:
    v = [0.0] * DIMS
    counts = Counter(tokens(text))
    for word, count in counts.items():
        h = hashlib.blake2b(word.encode("utf-8"), digest_size=8, person=b"HZMEMv1").digest()
        idx = int.from_bytes(h[:4], "little") % DIMS
        v[idx] += (1.0 if h[4] % 2 == 0 else -1.0) * (1.0 + math.log(count))
    return unit(v)


def phi(x: float, alpha: float = 0.25) -> float:
    return math.tanh(x) + alpha * math.tanh(2.0 * x)


def hz_refine(query: list[float], candidates: list[list[float]],
              steps: int = 2, alpha: float = 0.25,
              eps: float = 0.10, lam: float = 0.02, beta: float = 8.0) -> list[float]:
    x = unit(query)
    if not candidates:
        return x
    for _ in range(steps):
        similarities = [dot(x, c) for c in candidates]
        highest = max(similarities)
        weights = [math.exp(beta * (s - highest)) for s in similarities]
        z = sum(weights)
        weights = [w / z for w in weights]
        field = [sum(w * c[i] for w, c in zip(weights, candidates)) for i in range(len(x))]
        x = unit([(1.0 - lam) * old + eps * phi(h, alpha) for old, h in zip(x, field)])
    return x


def search(records: list[dict], query: str, limit: int = 5,
           query_embedding: list[float] | None = None,
           embedding_model: str = "", steps: int = 2) -> list[dict]:
    if not query.strip():
        return []
    qlex = lexical_vector(query)
    qsemantic = unit(query_embedding) if query_embedding else None
    pool = []
    for rec in records:
        lex = lexical_vector(rec["title"] + " " + rec["content"])
        score = max(0.0, dot(qlex, lex)) if any(qlex) else 0.0
        semantic = None
        if (qsemantic and rec.get("embedding_model") == embedding_model
                and isinstance(rec.get("embedding"), list)
                and len(rec["embedding"]) == len(qsemantic)):
            candidate = [float(x) for x in rec["embedding"]]
            if all(math.isfinite(x) for x in candidate):
                semantic = unit(candidate)
                score = 0.15 * score + 0.85 * max(0.0, dot(qsemantic, semantic))
        if score > 1e-9:
            # Retain BOTH representations. Never mix lexical and semantic vector
            # spaces in a single associative refinement field.
            pool.append((score, rec, lex, semantic))
    pool.sort(key=lambda x: (-x[0], x[1]["id"]))
    pool = pool[:32]
    if not pool:
        return []
    use_semantic = qsemantic is not None and all(sem is not None for _, _, _, sem in pool)
    q = qsemantic if use_semantic else qlex
    vectors = [sem if use_semantic else lex for _, _, lex, sem in pool]
    if any(q):
        transformed = hz_refine(q, vectors, steps=steps)
    else:
        transformed = q
    results = []
    for (base, rec, _, _), vec in zip(pool, vectors):
        refined = max(0.0, dot(transformed, vec))
        # Retain original evidence ranking; optional HZ only contributes a bounded adjustment.
        blended = 0.85 * base + 0.15 * refined
        results.append({"score": blended, "base_score": base, "record": rec})
    results.sort(key=lambda item: (-item["score"], item["record"]["id"]))
    return results[:max(1, min(limit, 20))]
