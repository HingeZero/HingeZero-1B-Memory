"""Sanity-check exact published Python HingeZero Witness semantics."""
import numpy as np
from HingeZero_Core import HingeZeroWitness, HingeZeroState, _unit


def main():
    bank = np.array([[1., -1., 1., 1.],
                     [-1., 1., -1., 1.],
                     [1., 1., -1., -1.]], dtype=np.float32)
    witness = HingeZeroWitness(bank, np.zeros(len(bank), dtype=np.float32))
    cue = _unit(np.array([1., -.7, 1., .5], dtype=np.float32))
    # Explicit scoring is the reference 0-step path: no refinement.
    scores = witness.memories @ cue
    state = witness.observe(cue, scores=scores)
    assert state.candidate_index == int(np.argmax(scores))
    assert witness.verify(state)
    # Witness rejects mismatched tagged identities and tampered values.
    damaged = HingeZeroState(state.candidate_index, state.state.copy())
    damaged.state[0] += np.float32(.001)
    assert not witness.accepts(damaged)
    assert not witness.verify(damaged)
    wrong_tag = HingeZeroState((state.candidate_index + 1) % len(bank), state.state)
    assert not witness.accepts(wrong_tag)
    print('PASS: zero-refinement observation, exact-state witness, tamper rejection')

if __name__ == '__main__': main()