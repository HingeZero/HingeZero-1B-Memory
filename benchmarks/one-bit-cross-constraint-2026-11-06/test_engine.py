"""Unit tests for packed binary data, original Core and fail-closed rules."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from engine import (BITS, BYTES, Challenge, Record, decide, expected_status,
                    explicit_rule_gate, flip_bits, hamming, make_fixture,
                    pack_1bit, unpack_for_hinge, constraint_wall,
                    encode_typed_fact)
from HingeZero_Core import HingeZeroWitness, HingeZeroState


class OneBitConstraintTests(unittest.TestCase):
    def test_physically_packed_one_bit_states(self):
        records, _ = make_fixture(30)
        self.assertEqual(len(records), 30)
        self.assertEqual(sum(len(r.code) for r in records), 30 * 32)
        self.assertTrue(all(type(r.code) is bytes for r in records))
        self.assertEqual(pack_1bit("demo phrase"), pack_1bit("demo phrase"))
        self.assertEqual(unpack_for_hinge(records[0].code).shape, (256,))
        self.assertEqual(set(np.unique(unpack_for_hinge(records[0].code))), {-1.0, 1.0})

    def test_hamming_opposites_do_not_automatically_cancel(self):
        original = pack_1bit("counter example")
        opposite = bytes(b ^ 0xFF for b in original)
        self.assertEqual(hamming(original, opposite), BITS)
        self.assertEqual(hamming(original, original), 0)
        self.assertEqual(hamming(original, flip_bits(original, 64, 11)), 64)
        self.assertEqual(float(unpack_for_hinge(original) @ unpack_for_hinge(opposite)), -256.0)

    def test_exact_1bit_rule_walls(self):
        wall = constraint_wall("activate_motor", "guard_open")
        self.assertEqual(len(wall), BYTES)
        clear = encode_typed_fact(wall, False)
        conflict = encode_typed_fact(wall, True)
        self.assertEqual(hamming(wall, clear), 0)
        self.assertEqual(hamming(wall, conflict), BITS)
        self.assertEqual(hamming(clear, conflict), BITS)
        with self.assertRaises(ValueError):
            constraint_wall("activate_motor", "wrong_fact")
        with self.assertRaises(ValueError):
            encode_typed_fact(wall, None)

    def test_clean_recall_three_methods(self):
        records, cases = make_fixture(60)
        for mode in ("binary", "hz0", "hz8"):
            for case in cases:
                result = decide(records, case, mode=mode)
                self.assertTrue(result.match, (mode, case.subject, result))
                self.assertEqual(result.status, case.label)
                if mode == "binary":
                    self.assertIsNone(result.witness_verified)
                else:
                    self.assertTrue(result.witness_verified)

    def test_wrong_identity_never_allows_or_blocks(self):
        records, cases = make_fixture(36)
        target = cases[1]
        wrong = Challenge("unrelated_asset", target.action,
                          target.cue, target.expected_record_id, "REVIEW")
        for mode in ("binary", "hz0", "hz8"):
            self.assertEqual(decide(records, wrong, mode=mode).status, "REVIEW")

    def test_missing_and_untrusted_evidence_hold(self):
        records, cases = make_fixture(30)
        for index in (2, 3, 4, 7, 8, 9):
            self.assertEqual(cases[index].label, "REVIEW")
            self.assertEqual(decide(records, cases[index], mode="hz8").status, "REVIEW")

    def test_stored_identity_is_not_semantic_truth(self):
        records, _ = make_fixture(6)
        bank = np.stack([unpack_for_hinge(r.code) for r in records])
        witness = HingeZeroWitness(bank, np.zeros(6, dtype=np.float32))
        genuine = HingeZeroState(0, witness.memories[0])
        counterfeit = HingeZeroState(0, -witness.memories[0])
        self.assertTrue(witness.verify(genuine))
        self.assertFalse(witness.verify(counterfeit))
        # A source can be internally consistent and still explicitly blocked.
        self.assertEqual(expected_status(records[1]), "BLOCK")

    def test_unknown_rules_or_flags_fail_closed(self):
        records, cases = make_fixture(6)
        r = records[0]
        absent_rule = Record(r.id, r.subject, "unlisted_action", r.context,
                             r.fact_name, False, True, r.code)
        status, reason = explicit_rule_gate(absent_rule, Challenge(
            r.subject, "unlisted_action", r.code, r.id, "REVIEW"))
        self.assertEqual((status, reason), ("REVIEW", "missing_or_unknown_rule"))
        malformed = Record(r.id, r.subject, r.action, r.context,
                           r.fact_name, 1, True, r.code)
        self.assertEqual(explicit_rule_gate(malformed, cases[0])[0], "REVIEW")

    def test_invalid_binary_code_held(self):
        records, cases = make_fixture(6)
        damaged = Challenge(cases[0].subject, cases[0].action,
                            b"too short", cases[0].expected_record_id, "REVIEW")
        for mode in ("binary", "hz0", "hz8"):
            self.assertEqual(decide(records, damaged, mode=mode).status, "REVIEW")


if __name__ == "__main__":
    unittest.main()
