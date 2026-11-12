"""Full-field 1-bit HingeZero regression: no Hamming candidate preselection."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from engine import BITS, BYTES, Challenge, flip_bits, hamming, make_fixture
from full_field import FullFieldOneBit


class FullFieldTests(unittest.TestCase):
    def setUp(self):
        self.records, self.cases = make_fixture(90)
        self.bank = FullFieldOneBit(self.records)

    def test_actual_packed_storage_full_attractor_field(self):
        self.assertEqual(self.bank.packed_bytes, len(self.records) * BYTES)
        self.assertTrue(all(type(x) is bytes for x in self.bank.packed))
        self.assertEqual(self.bank.witness.memories.shape, (90, BITS))
        self.assertEqual(len(self.bank.witness.field_ids), len(self.records))
        self.assertEqual(len(self.bank.witness.field_memories), 90)

    def test_all_full_field_methods_on_clean_1bit_cues(self):
        for mode in ("hamming_control", "hz_full_0", "hz_full_8"):
            for item in self.cases:
                decision = self.bank.decide(item, mode)
                self.assertTrue(decision.match, (mode, item.subject, decision))
                self.assertEqual(decision.status, item.label)
                if mode.startswith("hz_"):
                    self.assertTrue(decision.witness_verified)

    def test_hamming_zero_step_equivalence_for_unique_nearest_codes(self):
        for noise in (0, 16, 32, 64):
            for i, case in enumerate(self.cases):
                cue = flip_bits(case.cue, noise, noise + i * 19)
                distances = [hamming(cue, c) for c in self.bank.packed]
                nearest = min(distances)
                # At a unique min the bipolar cosine and Hamming rankings
                # agree mathematically (rounding aside).
                if distances.count(nearest) == 1:
                    a = self.bank.retrieve(cue, "hamming_control")
                    b = self.bank.retrieve(cue, "hz_full_0")
                    self.assertEqual(a.index, b.index)

    def test_no_hamming_preselection_in_hinge_modes(self):
        # Modify the standalone Hamming helper: HZ must not call it.
        import full_field
        old = full_field.hamming
        try:
            def denied(*_):
                raise AssertionError("HZ mode illegally called Hamming")
            full_field.hamming = denied
            for mode in ("hz_full_0", "hz_full_8"):
                decision = self.bank.decide(self.cases[1], mode)
                self.assertEqual(decision.status, self.cases[1].label)
        finally:
            full_field.hamming = old

    def test_mismatched_identity_is_review_not_automatic_block(self):
        case = self.cases[0]
        altered = Challenge("another_subject", case.action,
                            case.cue, case.expected_record_id, "REVIEW")
        for mode in ("hamming_control", "hz_full_0", "hz_full_8"):
            self.assertEqual(self.bank.decide(altered, mode).status, "REVIEW")

    def test_incomplete_binary_input_is_held(self):
        case = self.cases[0]
        bad = Challenge(case.subject, case.action,
                        b"not-256-bits", case.expected_record_id, "REVIEW")
        for mode in ("hamming_control", "hz_full_0", "hz_full_8"):
            self.assertEqual(self.bank.decide(bad, mode).status, "REVIEW")

    def test_reject_bank_larger_than_original_field(self):
        records, _ = make_fixture(258)
        with self.assertRaises(ValueError):
            FullFieldOneBit(records)


if __name__ == "__main__":
    unittest.main()
