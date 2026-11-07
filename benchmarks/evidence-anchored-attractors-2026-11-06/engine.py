"""Evidence-anchored attractor dynamics over the FULL genuine 1-bit memory bank.

Experimental *architecture*: two distinct cues, common source only when
constructed by the benchmark. A fixed cross-cue compatibility weighting
is applied BEFORE each dual-tanh or tanh field update.

No target IDs, labels, Hamming preselection, or ANN in any retrieval path.
Original HingeZero_Core.py is imported unchanged. Here the field is
MODIFIED by explicit candidate weights; it must not be called original
HingeZero performance. A matched ordinary-tanh control uses IDENTICAL
weights, step budget, scoring and abstention.

One 'cue' can be an independent bit-corrupted observation, or a separate
nonoverlapping text fragment from the SAME public web page. Neither
certifies a claim is true, and excerpts from one page are not
independent evidence sources.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sys

import numpy as np

# Stacked on the dual-tanh research branch, not a standalone installed package.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "dual-tanh-isolation-2026-11-06"))
sys.path.insert(0, str(HERE.parents[1]))

from HingeZero_Core import HZ_ALPHA, HZ_EPS, HZ_LAMBDA, HZ_STEPS, hinge_phi, _unit
from operators import AttractorBank, BITS, unpack

METHODS = (
    "single_zero",
    "two_cue_zero",
    "two_cue_tanh_original",
    "two_cue_dual_original",
    "two_cue_zero_gate",
    "two_cue_tanh_gate",
    "two_cue_dual_gate",
)


@dataclass(frozen=True)
class Resolution:
    candidate: int | None
    decision: str  # ACCEPT or REVIEW; never a safety or truth decision
    witness_valid: bool
    reason: str
    score: float
    agreement: float
    margin: float
    preserved_initial: bool = False  # zero-step support stopped gated refinement


class EvidenceAnchoredAttractors:
    def __init__(self, bank: AttractorBank, topk: int = 5,
                 require_initial_top1_agreement: bool = False,
                 preserve_supported_initial: bool = True,
                 min_initial_margin: float = 0.0):
        if not 1 <= topk <= min(32, len(bank.packed)):
            raise ValueError("Invalid corroboration topK")
        self.bank = bank
        self.topk = int(topk)
        self.require_initial_top1_agreement = bool(require_initial_top1_agreement)
        self.preserve_supported_initial = bool(preserve_supported_initial)
        if not math.isfinite(min_initial_margin) or min_initial_margin < 0:
            raise ValueError("min_initial_margin must be finite and nonnegative")
        self.min_initial_margin = float(min_initial_margin)
        self.matrix = bank.witness.memories
        if len(bank.witness.field_memories) != len(bank.packed):
            raise AssertionError("Original core must see every stored memory")
        self.fully_packed_storage_bytes = sum(map(len, bank.packed))

    def _scored(self, cue_a: bytes, cue_b: bytes):
        a = _unit(unpack(cue_a))
        b = _unit(unpack(cue_b))
        sa = self.matrix @ a
        sb = self.matrix @ b
        supports = np.maximum(sa, 0) * np.maximum(sb, 0)
        maximum = float(supports.max())
        # Relative per-candidate competition; not a cryptographic truth test.
        weights = supports / maximum if maximum > 1e-12 else np.zeros_like(supports)
        return a, b, sa, sb, weights

    @staticmethod
    def _top_margin(scores) -> float:
        """Gap between highest two scores, with exact ties giving zero."""
        if len(scores) < 2:
            return math.inf
        largest = np.partition(scores, -2)[-2:]
        return float(largest[1] - largest[0])

    def _supported_before_refinement(self, sa, sb, combined_scores,
                                     min_consensus: float) -> bool:
        """Source-identity agreement, NOT factual certainty.

        Both cues and the unrefined combined query must select the same
        unambiguous stored row with positive support. An optional combined
        score margin can make this check stricter; no truth labels are used.
        """
        best_a = int(np.argmax(sa))
        best_b = int(np.argmax(sb))
        best_joint = int(np.argmax(combined_scores))
        return (
            best_a == best_b == best_joint
            and min(float(sa[best_joint]), float(sb[best_joint])) > min_consensus
            and self._top_margin(sa) > 0.0
            and self._top_margin(sb) > 0.0
            and self._top_margin(combined_scores) > self.min_initial_margin
        )

    def _refine(self, query, weights, method):
        x = query.copy()
        if method in ("single_zero", "two_cue_zero", "two_cue_zero_gate"):
            return x
        if method == "two_cue_dual_original":
            return self.bank.witness.refine(x)
        if method == "two_cue_tanh_original":
            # Identical original Core update, only activation replaced.
            return self.bank.iterate(x, "tanh", HZ_STEPS)
        if method not in ("two_cue_tanh_gate", "two_cue_dual_gate"):
            raise ValueError("Unknown method")
        if self.bank.witness._stored_index(x) is not None:
            return x
        for _ in range(HZ_STEPS):
            h = self.bank.witness.field_memories @ x
            response = np.tanh(h) if method == "two_cue_tanh_gate" else hinge_phi(h, alpha=HZ_ALPHA)
            # IMPORTANT: the explicit corroboration mask changes original
            # dynamics. Plain-tanh has the EXACT same mask and budget.
            masked = response * weights[self.bank.witness.field_ids]
            field = self.bank.witness.field_memories.T @ masked
            field /= float(np.sum(np.abs(masked))) + 1e-12
            x = _unit((1.0 - HZ_LAMBDA) * x + HZ_EPS * field)
        return x

    def decide(self, cue_a: bytes, cue_b: bytes | None,
               method: str, *, min_consensus: float = 0.0) -> Resolution:
        if method not in METHODS:
            raise ValueError("Unknown method")
        if not isinstance(cue_a, bytes) or len(cue_a) != BITS // 8:
            return Resolution(None, "REVIEW", False, "missing_primary_cue", 0., 0., 0.)
        if cue_b is None or not isinstance(cue_b, bytes) or len(cue_b) != BITS // 8:
            return Resolution(None, "REVIEW", False, "missing_corrob_cue", 0., 0., 0.)
        a, b, sa, sb, weights = self._scored(cue_a, cue_b)
        agreement_anchor = None
        if self.require_initial_top1_agreement:
            # STRICT PRE-FLIGHT: do not reinforce an attractor at all unless
            # the two observed cues already name the same best stored row.
            # This is an evidence-gate policy, NOT nonlinear discovery.
            best_a = int(np.argmax(sa))
            best_b = int(np.argmax(sb))
            if best_a != best_b or min(float(sa[best_a]), float(sb[best_b])) <= min_consensus:
                return Resolution(None, "REVIEW", False, "preflight_disagreement",
                                  0., 0., 0.)
            agreement_anchor = best_a
        if method == "single_zero":
            query = a
        else:
            query = _unit(a+b)
        if float(np.linalg.norm(query)) <= 1e-12:
            return Resolution(None, "REVIEW", False, "opposing_or_undefined_cues", 0., 0., 0.)
        # Gated experimental methods only: don't distort a well-supported
        # zero-step selection. Original-core and zero-step controls are intact.
        preserved_initial = False
        zero_scores = None
        if self.preserve_supported_initial and method in (
                "two_cue_tanh_gate", "two_cue_dual_gate"):
            zero_scores = self.matrix @ query
            preserved_initial = self._supported_before_refinement(
                sa, sb, zero_scores, min_consensus)
        if preserved_initial:
            x = query
            scores = zero_scores
        else:
            x = self._refine(query, weights, method)
            scores = self.matrix @ x
        state = self.bank.witness.observe(query, scores)
        valid = bool(self.bank.witness.verify(state))
        winner = int(state.candidate_index)
        top = np.argsort(-scores, kind="stable")
        gap = (float(scores[top[0]] - scores[top[1]])
               if len(top)>1 else math.inf)
        if not valid:
            return Resolution(None, "REVIEW", False, "witness_identity_failed",
                              0., 0., gap, preserved_initial=preserved_initial)
        corroboration = float(min(sa[winner], sb[winner]))
        if agreement_anchor is not None and winner != agreement_anchor:
            return Resolution(winner, "REVIEW", True,
                              "refinement_diverged_from_preflight_anchor",
                              float(scores[winner]), corroboration, gap,
                              preserved_initial=preserved_initial)
        # The SAME deterministic evidence gate is used on every method.
        # Avoid calling this 'truth verification'. It checks agreement
        # of two hashes against the SAME stored candidate.
        rank_a = set(np.argsort(-sa, kind="stable")[:self.topk])
        rank_b = set(np.argsort(-sb, kind="stable")[:self.topk])
        if winner not in rank_a or winner not in rank_b or corroboration <= min_consensus:
            return Resolution(winner, "REVIEW", True, "insufficient_two_cue_agreement",
                              float(scores[winner]), corroboration, gap,
                              preserved_initial=preserved_initial)
        return Resolution(winner, "ACCEPT", True, "two_cues_support_same_stored_pattern",
                          float(scores[winner]), corroboration, gap,
                          preserved_initial=preserved_initial)
