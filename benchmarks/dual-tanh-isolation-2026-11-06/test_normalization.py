"""Unit tests separating normalisation, nonlinearity, and response sharpening."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from HingeZero_Core import HZ_ALPHA
from operators import AttractorBank, flip, make_correlated_bank, unpack
from normalization import (Configuration, configurations, diagnostic,
                           field_response, refine, retrieve, response)


class NormalizationIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codes = make_correlated_bank(20261106, 64, .8)
        cls.bank = AttractorBank(cls.codes)

    def test_original_l1_original_phi_exact_parity(self):
        cfg = Configuration("original", "dual45", "l1_original", 1)
        for i, flips in ((4, 20), (7, 48), (31, 72), (48, 92)):
            cue = flip(self.codes[i], flips, np.random.default_rng(i+11))
            original = self.bank.witness.refine(unpack(cue)/math.sqrt(256))
            np.testing.assert_array_equal(refine(self.bank, cue, cfg), original)
            match = retrieve(self.bank, cue, i, cfg)
            self.assertTrue(match.valid)

    def test_l1_scalar_preserves_response_ratios(self):
        h = np.array([0.1, 0.8], np.float32)
        for act in ("tanh", "dual025", "dual45"):
            prior, _ = response(h, act)
            for denominator in ("l1_original", "l2_scaled", "fixed_response_bound"):
                r, denom = field_response(h, Configuration(
                    "probe", act, denominator, 1
                ))
                self.assertTrue(denom > 0)
                self.assertAlmostEqual(float(r[0]/r[1]),
                                       float((r[0]/denom)/(r[1]/denom)), places=7)
                np.testing.assert_allclose(r, prior)

    def test_dual45_amplifies_weaker_relative_matches(self):
        v = diagnostic()
        self.assertGreater(v["dual45"]["weak_over_strong"],
                           v["tanh"]["weak_over_strong"])
        self.assertGreater(v["dual025"]["weak_over_strong"],
                           v["tanh"]["weak_over_strong"])

    def test_power_two_is_separate_shape_modification(self):
        h = np.array([0.1, 0.8], np.float32)
        for act in ("tanh", "dual45"):
            linear, _ = field_response(h, Configuration("base", act, "l1_original", 1))
            sharp, _ = field_response(h, Configuration("sharp", act, "l1_original", 2))
            self.assertLess(abs(float(sharp[0]/sharp[1])),
                            abs(float(linear[0]/linear[1])))

    def test_exhaustive_controls(self):
        all_configs = configurations()
        self.assertEqual(len(all_configs), 18)
        self.assertEqual(len({c.name for c in all_configs}), len(all_configs))
        for cfg in all_configs:
            cue = flip(self.codes[4], 64, np.random.default_rng(7))
            result = retrieve(self.bank, cue, 4, cfg)
            self.assertTrue(result.valid)
            self.assertTrue(np.isfinite(result.target_margin))

    def test_control_uses_true_packed_binary_bank(self):
        self.assertEqual(len(self.bank.witness.field_memories), len(self.codes))
        self.assertEqual(sum(map(len, self.bank.packed)), 64 * 32)
        self.assertEqual(HZ_ALPHA, 4.5)


if __name__ == "__main__":
    unittest.main()
