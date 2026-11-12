"""Unit tests for isolating the dual-tanh term, not merely Witness parity."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from HingeZero_Core import HZ_ALPHA, HZ_EPS, HZ_LAMBDA, HZ_STEPS
from operators import (
    BITS, BYTES, METHODS, AttractorBank, as_packed, flip,
    make_correlated_bank, packed_from_text, unpack
)


class DualTanhIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codes = make_correlated_bank(20261106, 64, .5)
        cls.bank = AttractorBank(cls.codes)

    def test_packed_bits_really_occupy_one_bit_per_dimension(self):
        self.assertEqual(self.bank.packed_bytes, len(self.codes) * 32)
        self.assertEqual(self.bank.memories.shape, (64, BITS))
        self.assertEqual(self.bank.witness.field_memories.shape, (64, BITS))
        self.assertEqual(len(set(self.codes)), 64)
        for code in self.codes:
            self.assertIs(type(code), bytes)
            self.assertEqual(len(code), BYTES)
            self.assertEqual(as_packed(unpack(code)), code)

    def test_original_dual45_has_exact_core_parity(self):
        self.assertEqual(HZ_ALPHA, 4.5)
        self.assertEqual(HZ_STEPS, 8)
        self.assertEqual(HZ_EPS, .1)
        self.assertEqual(HZ_LAMBDA, .02)
        for i in (1, 7, 18, 42):
            cue = flip(self.codes[i], 41, np.random.default_rng(300 + i))
            query = unpack(cue) / math.sqrt(BITS)
            expected = self.bank.witness.refine(query)
            actual = self.bank.iterate(query, "dual45", 8)
            np.testing.assert_array_equal(actual, expected)
            self.assertTrue(self.bank.retrieve(cue, "dual45", i).witness_valid)

    def test_all_modes_consider_all_memories_no_ann(self):
        self.assertEqual(len(self.bank.witness.field_ids), len(self.codes))
        for mode in METHODS:
            result = self.bank.retrieve(self.codes[13], mode, 13)
            self.assertEqual(result.chosen, 13, mode)
            self.assertTrue(result.witness_valid)
        with self.assertRaises(ValueError):
            AttractorBank(self.codes + self.codes)

    def test_two_tanh_components_are_not_just_linear_gain(self):
        cue = flip(self.codes[12], 57, np.random.default_rng(123))
        x = unpack(cue) / math.sqrt(BITS)
        tanh = self.bank.iterate(x, "tanh", 8)
        tanh2 = self.bank.iterate(x, "tanh2", 8)
        dual = self.bank.iterate(x, "dual45", 8)
        self.assertGreater(float(np.linalg.norm(tanh - dual)), 1e-7)
        self.assertGreater(float(np.linalg.norm(tanh2 - dual)), 1e-7)

    def test_source_codes_are_deterministic_and_nonsemantic(self):
        self.assertEqual(packed_from_text("Alpha Omega"),
                         packed_from_text("Alpha Omega"))
        self.assertEqual(len(packed_from_text("ordinary webpage text")), BYTES)
        with self.assertRaises(ValueError):
            packed_from_text("")

    def test_reject_invalid_method_and_packed_code(self):
        x = unpack(self.codes[0]) / math.sqrt(BITS)
        with self.assertRaises(ValueError):
            self.bank.iterate(x, "fabricated_method", 8)
        with self.assertRaises(ValueError):
            self.bank.iterate(x, "dual45", 12)
        with self.assertRaises(ValueError):
            self.bank.retrieve(b"not-a-256-bit-code", "dual45", 0)


if __name__ == "__main__":
    unittest.main()
