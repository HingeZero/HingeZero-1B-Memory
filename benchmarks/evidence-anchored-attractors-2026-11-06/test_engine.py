"""Regression tests: no target leakage, actual packed bits, matched controls."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from operators import AttractorBank, flip, make_correlated_bank, unpack
from engine import EvidenceAnchoredAttractors, METHODS


class TwoCueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codes = make_correlated_bank(20261106, 96, .5)
        cls.bank = AttractorBank(cls.codes)
        cls.engine = EvidenceAnchoredAttractors(cls.bank, topk=5)

    def test_all_96_memories_in_actual_full_field(self):
        self.assertEqual(len(self.bank.packed), 96)
        self.assertEqual(len(self.bank.witness.field_ids), 96)
        self.assertEqual(self.bank.witness.field_memories.shape, (96, 256))
        self.assertEqual(self.engine.fully_packed_storage_bytes, 96*32)
        self.assertTrue(all(type(x) is bytes and len(x) == 32 for x in self.codes))

    def test_original_ungated_dual_is_exact_core(self):
        a=unpack(self.codes[1]) / math.sqrt(256)
        b=unpack(self.codes[7]) / math.sqrt(256)
        q=(a+b)/np.linalg.norm(a+b)
        original=self.bank.witness.refine(q)
        wrapped=self.engine._refine(q, np.ones(96,np.float32),
                                    "two_cue_dual_original")
        np.testing.assert_array_equal(original,wrapped)

    def test_same_stored_cue_all_modes_accept_witness(self):
        for i in (1, 24, 77):
            for method in METHODS:
                result = self.engine.decide(self.codes[i], self.codes[i], method)
                self.assertEqual(result.candidate, i, (i, method, result))
                self.assertTrue(result.witness_valid)
                self.assertEqual(result.decision, "ACCEPT")

    def test_opposing_cues_fail_closed(self):
        target=self.codes[6]
        opposite=bytes(x ^ 255 for x in target)
        for method in METHODS:
            outcome=self.engine.decide(target, opposite, method)
            self.assertEqual(outcome.decision, "REVIEW")

    def test_missing_evidence_cannot_trigger_accept(self):
        for method in METHODS:
            a=self.engine.decide(self.codes[0], None, method)
            self.assertEqual(a.decision, "REVIEW")
            b=self.engine.decide(b"invalid", self.codes[1], method)
            self.assertEqual(b.decision, "REVIEW")

    def test_no_target_ids_or_ground_truth_required(self):
        # Engine signature takes only cues and mode, no expected target IDs.
        for method in METHODS:
            x = self.engine.decide(self.codes[10], self.codes[10], method)
            self.assertEqual(x.candidate,10)
            self.assertEqual(x.reason, "two_cues_support_same_stored_pattern")

    def test_no_hamming_shortlist_in_any_attractor_path(self):
        # AttractorBank has full float32 working copy derived from packed data;
        # no Hamming search anywhere in this engine's path.
        import engine
        self.assertNotIn("hamming(", Path(engine.__file__).read_text())
        x=self.engine.decide(self.codes[1],self.codes[1],
                             "two_cue_dual_gate")
        self.assertTrue(x.witness_valid)

    def test_untrusted_extra_cues_cannot_verify_truth(self):
        # Agreement proves consistency of two retrieved codes, not truth.
        outcome=self.engine.decide(self.codes[4],self.codes[4],
                                    "two_cue_dual_gate")
        self.assertEqual(outcome.decision,"ACCEPT")
        self.assertEqual(outcome.reason,"two_cues_support_same_stored_pattern")
        self.assertNotIn("truth",outcome.reason)

    def test_two_cue_gate_changes_operator(self):
        cue_a=flip(self.codes[12],64,np.random.default_rng(12))
        cue_b=flip(self.codes[12],64,np.random.default_rng(13))
        a,b,sa,sb,weights=self.engine._scored(cue_a,cue_b)
        self.assertEqual(weights.shape,(96,))
        self.assertTrue(np.all(weights>=0))
        self.assertTrue(np.all(weights<=1))
        query=(a+b)/np.linalg.norm(a+b)
        baseline=self.engine._refine(query,weights,"two_cue_dual_original")
        conditioned=self.engine._refine(query,weights,"two_cue_dual_gate")
        self.assertGreater(float(np.linalg.norm(baseline-conditioned)),1e-7)


if __name__=="__main__":
    unittest.main()
