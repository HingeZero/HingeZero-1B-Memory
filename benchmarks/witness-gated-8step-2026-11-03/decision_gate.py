"""Bounded, fail-closed decision gate around David Duffy's original HingeZeroWitness.

No modification of the original HingeZero_Core.py is required. The gate verifies
stored-state identity and checks *externally supplied* evidence metadata.
Source IDs are assertions by callers, not cryptographic authentication or truth.
"""
from dataclasses import asdict, dataclass
from typing import Sequence
import numpy as np

from HingeZero_Core import (HingeZeroWitness, HZ_ALPHA, HZ_EPS,
                             HZ_LAMBDA, hinge_phi, _unit)


@dataclass(frozen=True)
class Evidence:
    support_ids: tuple[str, ...] = ()
    contradiction_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Decision:
    status: str                 # ACCEPT or HUMAN_REVIEW
    candidate_id: int | None
    steps: int
    reason: str
    similarity: float | None
    margin: float | None
    witness_valid: bool

    def to_dict(self):
        return asdict(self)


class EvidenceGatedWitness:
    def __init__(self, witness: HingeZeroWitness, records: Sequence[Evidence],
                 min_similarity: float = 0.60, min_margin: float = 0.10,
                 min_support: int = 2, max_steps: int = 8):
        if len(records) != len(witness.memories):
            raise ValueError("Each stored candidate requires an evidence record")
        if max_steps < 0 or max_steps > 8:
            raise ValueError("Refinement must not exceed eight steps")
        if min_support < 1 or not (-1 <= min_similarity <= 1) or not (0 <= min_margin <= 2):
            raise ValueError("Invalid gate thresholds")
        self.witness = witness
        self.records = tuple(records)
        self.min_similarity = float(min_similarity)
        self.min_margin = float(min_margin)
        self.min_support = int(min_support)
        self.max_steps = int(max_steps)

    def _check(self, x, steps):
        scores = (self.witness.memories @ x).astype(np.float64)
        # Identify the winner with exactly the witness's own observe function.
        locked = self.witness.observe(x, scores=scores)
        verified = bool(self.witness.verify(locked))
        selected = int(locked.candidate_index)
        ranked = np.sort(scores)
        similarity = float(scores[selected])
        margin = float(ranked[-1] - ranked[-2]) if len(scores) > 1 else float('inf')
        ev = self.records[selected]
        sources = {s for s in ev.support_ids if isinstance(s, str) and s.strip()}
        disputes = {s for s in ev.contradiction_ids if isinstance(s, str) and s.strip()}
        if not verified:
            reason = 'witness_failed'
        elif disputes:
            reason = 'contradictory_evidence'
        elif len(sources) < self.min_support:
            reason = 'insufficient_external_support'
        elif similarity < self.min_similarity:
            reason = 'weak_retrieval_similarity'
        elif margin < self.min_margin:
            reason = 'ambiguous_near_tie'
        else:
            return Decision('ACCEPT', selected, steps, 'supported_by_supplied_evidence',
                            similarity, margin, verified)
        return Decision('HUMAN_REVIEW', None, steps, reason, similarity, margin, verified)

    def decide(self, cue):
        cue = np.asarray(cue, dtype=np.float32)
        if cue.shape != (self.witness.memories.shape[1],):
            raise ValueError('Query dimension mismatch')
        # Do not let a completely missing or invalid cue become a guessed answer.
        if not np.isfinite(cue).all() or float(np.linalg.norm(cue)) <= 1e-12:
            return Decision('HUMAN_REVIEW', None, 0, 'invalid_or_missing_cue', None, None, False)
        x = _unit(cue)
        initial = self._check(x, 0)
        # Evidence cannot be fabricated by more iterations; challenge/hold at once.
        if (initial.status == 'ACCEPT' or self.max_steps == 0 or
            initial.reason in {'contradictory_evidence', 'insufficient_external_support', 'witness_failed'}):
            return initial
        last = initial
        for step in range(1, self.max_steps + 1):
            # Exactly one iteration from original HingeZeroWitness.refine().
            h = self.witness.field_memories @ x
            response = hinge_phi(h, alpha=HZ_ALPHA)
            field = self.witness.field_memories.T @ response
            field /= float(np.sum(np.abs(response))) + 1e-12
            x = _unit((1.0 - HZ_LAMBDA) * x + HZ_EPS * field)
            last = self._check(x, step)
            if (last.status == 'ACCEPT' or last.reason in
                {'contradictory_evidence', 'insufficient_external_support', 'witness_failed'}):
                return last
        return last
