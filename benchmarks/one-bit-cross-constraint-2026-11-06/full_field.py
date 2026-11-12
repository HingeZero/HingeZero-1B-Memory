"""Full-field 1-bit HingeZero associative retrieval with no Hamming shortlist.

A memory is stored as 256 packed bits/32 bytes. Original HingeZeroWitness
sees ALL stored patterns in its attractor field (up to HZ_TOP=256 records),
and scores EVERY memory. Only an ephemeral float32 workspace is expanded.

The Hamming baseline is a separate control, never a candidate preselector
for the HingeZero conditions. Zero-step full-field signed-dot and Hamming
nearest-neighbour are mathematically equivalent for equal-length bipolar
codes, except floating-point rounding/ties.

This prototype is a SMALL full-field research experiment, not a billion
memory implementation or clinical/industrial safety system.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np

from engine import (
    BITS, BYTES, Challenge, Decision, Record, explicit_rule_gate,
    hamming, unpack_for_hinge,
)
from HingeZero_Core import HingeZeroWitness, HZ_TOP

MODES = ("hamming_control", "hz_full_0", "hz_full_8")


@dataclass(frozen=True)
class Retrieval:
    index: int
    similarity: float
    margin: float
    witness_valid: bool | None


class FullFieldOneBit:
    """One shared packed bank and a single full-field Witness for all cues."""

    def __init__(self, records: list[Record]):
        if not records or len(records) > HZ_TOP:
            raise ValueError(
                f"Full-field original Core can include 1..{HZ_TOP} patterns; "
                "do not pretend a 256-pattern field is a billion-pattern field."
            )
        self.records = tuple(records)
        self.packed = tuple(r.code for r in records)
        if any(len(code) != BYTES for code in self.packed):
            raise ValueError("1-bit bank contains an invalid packed state")
        self.packed_bytes = sum(len(code) for code in self.packed)
        if self.packed_bytes != len(records) * 32:
            raise AssertionError("Binary storage is not packed 1-bit")
        # Float matrix is temporary *working state* for original dual-tanh
        # arithmetic; NOT the bank's on-disk or compact representation.
        self.workspace = np.stack([unpack_for_hinge(code) for code in self.packed])
        self.witness = HingeZeroWitness(
            self.workspace, np.zeros(len(self.workspace), dtype=np.float32)
        )
        if len(self.witness.field_ids) != len(self.records):
            raise AssertionError("A full-bank HingeZero field was not constructed")

    def retrieve(self, cue: bytes, mode: str) -> Retrieval:
        if mode not in MODES:
            raise ValueError(f"Unrecognised retrieval mode {mode}")
        if len(cue) != BYTES:
            raise ValueError("Cue must be precisely 256 packed bits")

        if mode == "hamming_control":
            # Baseline ONLY, independent of HingeZero's associative field.
            distances = np.asarray(
                [hamming(cue, code) for code in self.packed], dtype=np.int32
            )
            order = np.argsort(distances, kind="stable")
            winner = int(order[0])
            best = 1.0 - (2.0 * float(distances[winner]) / BITS)
            margin = (2.0 * float(distances[int(order[1])] - distances[winner])
                      / BITS) if len(order) > 1 else 2.0
            return Retrieval(winner, best, margin, None)

        # Both HingeZero modes inspect the entire packed bank. There is no
        # preselection, approximate ANN, fixed 32-row shortlist or Hamming gate.
        query = unpack_for_hinge(cue) / math.sqrt(BITS)
        refined = self.witness.refine(query) if mode == "hz_full_8" else query
        scores = self.witness.memories @ refined
        state = self.witness.observe(query, scores)
        valid = bool(self.witness.verify(state))
        order = np.argsort(-scores, kind="stable")
        winner = int(state.candidate_index)
        margin = (float(scores[int(order[0])] - scores[int(order[1])])
                  if len(order) > 1 else 2.0)
        return Retrieval(winner, float(scores[winner]), margin, valid)

    def decide(self, challenge: Challenge, mode: str,
               min_similarity: float = 0.10,
               min_margin: float = 0.015) -> Decision:
        if not isinstance(challenge.cue, bytes) or len(challenge.cue) != BYTES:
            return Decision("REVIEW", "invalid_binary_cue", None, False,
                            False, None)
        result = self.retrieve(challenge.cue, mode)
        selected = self.records[result.index]
        if result.witness_valid is False:
            return Decision("REVIEW", "witness_state_invalid", None, False,
                            False, None)
        if result.similarity < min_similarity:
            return Decision("REVIEW", "insufficient_attractor_similarity",
                            selected.id, result.witness_valid,
                            selected.id == challenge.expected_record_id, None)
        if result.margin < min_margin:
            return Decision("REVIEW", "ambiguous_attractor_margin",
                            selected.id, result.witness_valid,
                            selected.id == challenge.expected_record_id, None)
        status, reason = explicit_rule_gate(selected, challenge)
        return Decision(
            status, reason, selected.id, result.witness_valid,
            selected.id == challenge.expected_record_id, None
        )
