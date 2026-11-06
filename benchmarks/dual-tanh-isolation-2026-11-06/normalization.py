"""Inspect response normalisation in the original dual-tanh HingeZero Core.

All stored memories are genuine packed 1-bit bipolar states. All memory rows
participate in each field update (up to the original HZ_TOP=256).
Normalisation tests change the scalar denominator only. Separate sharpening
tests intentionally change response *shape*; that is NOT the original Core.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

from HingeZero_Core import HZ_EPS, HZ_LAMBDA, HZ_STEPS, hinge_phi, _unit
from operators import AttractorBank, BITS, unpack


class Configuration(NamedTuple):
    name: str
    activation: str
    denominator: str
    power: int


ACTIVATIONS = ("tanh", "dual025", "dual45")
DENOMINATORS = ("l1_original", "l2_scaled", "fixed_response_bound")
# Shape modification is deliberately segregated from the denominator-only
# ablation. Compare tanh and dual with the same shape modification.
SHAPES = (1, 2)


def configurations() -> list[Configuration]:
    return [
        Configuration(
            name=f"{act}__{denom}__p{power}", activation=act,
            denominator=denom, power=power
        )
        for act in ACTIVATIONS
        for denom in DENOMINATORS
        for power in SHAPES
    ]


def response(h: np.ndarray, activation: str) -> tuple[np.ndarray, float]:
    if activation == "tanh":
        return np.tanh(h), 1.0
    if activation == "dual025":
        return hinge_phi(h, alpha=0.25), 1.25
    if activation == "dual45":
        return hinge_phi(h, alpha=4.5), 5.5
    raise ValueError("Unknown activation")


def field_response(h: np.ndarray, config: Configuration) -> tuple[np.ndarray, float]:
    r, limit = response(h, config.activation)
    if config.power not in SHAPES:
        raise ValueError("Unknown shape")
    if config.power == 2:
        # Sign-preserving concentration; preserves absolute saturation bound
        # after scaling by the activation's maximum theoretical magnitude.
        r = np.sign(r) * (np.abs(r) ** 2 / limit)
    if config.denominator == "l1_original":
        denominator = float(np.sum(np.abs(r))) + 1e-12
    elif config.denominator == "l2_scaled":
        denominator = (math.sqrt(len(r)) * float(np.linalg.norm(r))) + 1e-12
    elif config.denominator == "fixed_response_bound":
        denominator = len(r) * limit
    else:
        raise ValueError("Unknown denominator")
    return r, denominator


def refine(bank: AttractorBank, cue: bytes, config: Configuration,
           steps: int = HZ_STEPS) -> np.ndarray:
    if steps not in (0, 1, 2, 4, 8):
        raise ValueError("Unsupported number of iterations")
    x = _unit(unpack(cue))
    if steps == 0:
        return x
    # Original Core returns exact stored state immediately, which is common
    # to all methods in these controls.
    if bank.witness._stored_index(x) is not None:
        return x
    for _ in range(steps):
        h = bank.witness.field_memories @ x
        r, denominator = field_response(h, config)
        field = bank.witness.field_memories.T @ r
        field /= denominator
        x = _unit((1.0 - HZ_LAMBDA) * x + HZ_EPS * field)
    return x


@dataclass(frozen=True)
class Outcome:
    correct: bool
    selected: int
    valid: bool
    elapsed_ms: float
    target_margin: float


def retrieve(bank: AttractorBank, cue: bytes, target: int,
             config: Configuration | None) -> Outcome:
    start = time.perf_counter_ns()
    x = _unit(unpack(cue)) if config is None else refine(bank, cue, config)
    scores = bank.memories @ x
    stored = bank.witness.observe(x, scores)
    valid = bool(bank.witness.verify(stored))
    selected = int(stored.candidate_index)
    score_target = float(scores[target])
    margin = score_target - max(float(scores[j]) for j in range(len(scores)) if j != target)
    return Outcome(selected == target, selected, valid,
                   (time.perf_counter_ns()-start)/1e6, margin)


def diagnostic() -> dict:
    h = np.array([0.1, 0.8], dtype=np.float64)
    values = {}
    for act in ACTIVATIONS:
        r, _ = response(h, act)
        values[act] = {
            "weak_h_0p1": float(r[0]),
            "strong_h_0p8": float(r[1]),
            "weak_over_strong": float(abs(r[0]/r[1])),
            "weak_fraction_after_l1": float(abs(r[0])/np.sum(np.abs(r))),
        }
    return values
