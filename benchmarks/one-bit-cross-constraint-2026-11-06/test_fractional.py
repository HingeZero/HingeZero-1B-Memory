"""Fractional HingeZero invariants on the original 1-bit full field."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from engine import BITS, flip_bits, make_fixture, unpack_for_hinge
from fractional import fractional_retrieve, fractional_state
from full_field import FullFieldOneBit


class FractionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.cases = make_fixture(90)
        cls.full = FullFieldOneBit(cls.records)

    def test_exact_original_eight_step_parity(self):
        for i in (0, 2, 17, 43, 80):
            cue = flip_bits(self.cases[i].cue, 47, i + 91)
            x = unpack_for_hinge(cue) / math.sqrt(BITS)
            original = self.full.witness.refine(x)
            scaled = fractional_state(self.full.witness, x, 1.0, 8)
            np.testing.assert_allclose(scaled, original, atol=2e-7, rtol=2e-6)
            result = fractional_retrieve(self.full, cue, 1.0, 8)
            previous = self.full.retrieve(cue, "hz_full_8")
            self.assertEqual(result.index, previous.index)
            self.assertTrue(result.witness_valid)

    def test_zero_step_equivalence(self):
        for i in (1, 17, 56):
            cue = flip_bits(self.cases[i].cue, 64, i + 101)
            x = unpack_for_hinge(cue) / math.sqrt(BITS)
            np.testing.assert_array_equal(fractional_state(self.full.witness, x, 0, 8), x)
            np.testing.assert_array_equal(fractional_state(self.full.witness, x, .001, 0), x)
            a = fractional_retrieve(self.full, cue, 0, 8)
            b = self.full.retrieve(cue, "hz_full_0")
            self.assertEqual(a.index, b.index)

    def test_small_eta_changes_state_only_incrementally(self):
        cue = flip_bits(self.cases[31].cue, 64, 190)
        x = unpack_for_hinge(cue) / math.sqrt(BITS)
        tiny = fractional_state(self.full.witness, x, .001, 8)
        medium = fractional_state(self.full.witness, x, .1, 8)
        full = fractional_state(self.full.witness, x, 1, 8)
        self.assertGreater(float(np.linalg.norm(tiny - x)), 0)
        self.assertLess(float(np.linalg.norm(tiny - x)), float(np.linalg.norm(medium - x)))
        self.assertLess(float(np.linalg.norm(medium - x)), float(np.linalg.norm(full - x)))

    def test_invalid_eta_rejected(self):
        query = unpack_for_hinge(self.cases[0].cue) / math.sqrt(BITS)
        for invalid in (-.001, 1.001, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                fractional_state(self.full.witness, query, invalid, 8)
        for invalid_steps in (-1, 1.5, 129):
            with self.assertRaises(ValueError):
                fractional_state(self.full.witness, query, .001, invalid_steps)

    def test_fractional_hinge_never_invokes_hamming(self):
        import full_field
        old = full_field.hamming
        try:
            def forbidden(*_):
                raise AssertionError("Fractional HZ illegally used Hamming retrieval")
            full_field.hamming = forbidden
            for eta in (0.0, .001, .002, .01, .1, 1.):
                result = fractional_retrieve(self.full, self.cases[0].cue, eta, 8)
                self.assertTrue(result.witness_valid)
        finally:
            full_field.hamming = old


if __name__ == "__main__":
    unittest.main()
