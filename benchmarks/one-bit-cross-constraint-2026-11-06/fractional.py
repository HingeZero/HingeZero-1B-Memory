"""Fractional-strength full-field HingeZero on genuine packed one-bit memories.

An iteration is still discrete. Its *update strength* eta is continuous:
    x_next = unit((1 - eta*lambda)*x + eta*eps*field)
with field = W^T phi(W x) / (sum(abs(phi(W x))) + 1e-12).

For eta=1, 8 iterations reproduce the original (unchanged) HingeZero Core.
Eta=0 gives unrefined output. Original Witness verifies stored identity,
NOT semantic truth. This research helper never invokes Hamming selection.
"""
from __future__ import annotations

import math
import numpy as np

from HingeZero_Core import HZ_EPS, HZ_LAMBDA, HZ_STEPS, hinge_phi, _unit
from engine import BYTES, unpack_for_hinge
from full_field import FullFieldOneBit, Retrieval


def fractional_state(witness, query: np.ndarray, eta: float, steps: int) -> np.ndarray:
    """Smoothly vary update strength without changing dual-tanh activation.

    The original Core's exact-state identity preservation is respected.
    Iterations use the same lambda/epsilon and normalization as the Core.
    """
    if not isinstance(steps, int) or not 0 <= steps <= 128:
        raise ValueError("steps must be a whole number from 0 to 128")
    if not isinstance(eta, (int, float)) or not math.isfinite(eta) or not 0 <= eta <= 1:
        raise ValueError("eta must be finite within [0, 1]")
    x = _unit(np.asarray(query, dtype=np.float32))
    if x.shape != (witness.memories.shape[1],):
        raise ValueError("Cue dimensionality differs from stored HingeZero bank")
    if steps == 0 or eta == 0:
        return x
    stored = witness._stored_index(query)
    if stored is not None:
        return witness.memories[stored].copy()
    if float(np.linalg.norm(x)) <= 1e-12:
        x = witness.query_from_evidence()
    for _ in range(steps):
        h = witness.field_memories @ x
        response = hinge_phi(h)
        field = witness.field_memories.T @ response
        field /= float(np.sum(np.abs(response))) + 1e-12
        x = _unit((1.0 - eta * HZ_LAMBDA) * x + (eta * HZ_EPS) * field)
    return x


def fractional_retrieve(bank: FullFieldOneBit, cue: bytes,
                        eta: float, steps: int) -> Retrieval:
    """Evaluate ALL 1-bit memories using HingeZero; no Hamming shortlist."""
    if not isinstance(cue, bytes) or len(cue) != BYTES:
        raise ValueError("Cue must have 256 genuine binary bits")
    query = unpack_for_hinge(cue) / math.sqrt(256)
    refined = fractional_state(bank.witness, query, eta, steps)
    scores = bank.witness.memories @ refined
    locked = bank.witness.observe(query, scores)
    verified = bool(bank.witness.verify(locked))
    order = np.argsort(-scores, kind="stable")
    margin = (float(scores[int(order[0])] - scores[int(order[1])])
              if len(order) > 1 else 2.0)
    return Retrieval(int(locked.candidate_index), float(scores[locked.candidate_index]),
                     margin, verified)
