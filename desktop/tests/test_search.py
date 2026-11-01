"""Tests that the actual original HingeZero Core is used by desktop search."""
import hashlib
from pathlib import Path

import numpy as np
import pytest

from hzdesktop.HingeZero_Core import (
    HingeZeroRetainingLoop, HingeZeroState, HingeZeroWitness, HZ_STEPS,
)
from hzdesktop.retrieval import (
    RetainedMemorySession, search, phi, hz_refine, lexical_vector,
)


def _records():
    return [
        {"id": "001", "title": "Dentist",
         "content": "Dentist appointment Thursday at 2pm", "source": "note"},
        {"id": "002", "title": "Shopping",
         "content": "Buy milk and orange juice", "source": "note"},
    ]


def test_original_core_exact_git_blob_unchanged():
    original = Path(__file__).parents[1] / "hzdesktop" / "HingeZero_Core.py"
    data = original.read_bytes()
    digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\x00" + data).hexdigest()
    assert digest == "ec0ec9c56c233b97038d88618ad9f2bcff26bcab"
    assert HZ_STEPS == 8


def test_desktop_retrieval_uses_original_witness(monkeypatch):
    calls = []
    real = HingeZeroWitness.verify

    def observed(self, state):
        calls.append(state.candidate_index)
        return real(self, state)

    monkeypatch.setattr(HingeZeroWitness, "verify", observed)
    results = search(_records(), "dentist appointment thursday")
    assert calls, "Desktop search must call the original Witness"
    assert results[0]["record"]["id"] == "001"
    assert all(r["witness_verified"] for r in results)
    assert sum(r["witness_selected"] for r in results) == 1


def test_repeatability_and_empty_query():
    first = search(_records(), "dentist appointment thursday")
    assert first == search(_records(), "dentist appointment thursday")
    assert search(_records(), " ") == []


def test_original_refinement_and_unrefined_control():
    cue = lexical_vector("broken refrigerator freezer")
    bank = [lexical_vector("refrigerator freezer"),
            lexical_vector("car wheel")]
    unrefined = hz_refine(cue, bank, steps=0)
    refined = hz_refine(cue, bank, steps=8)
    assert refined == hz_refine(cue, bank, steps=8)
    assert refined != unrefined
    assert phi(0.0) == 0.0
    with pytest.raises(ValueError):
        hz_refine(cue, bank, steps=2)
    with pytest.raises(ValueError):
        search(_records(), "dentist", steps=2)


def test_retaining_loop_persists_with_same_candidate_bank():
    session = RetainedMemorySession()
    first = search(_records(), "dentist appointment", session=session)
    assert first and first[0]["retained_checkpoint"]
    loop = session._loop
    assert isinstance(loop, HingeZeroRetainingLoop)
    second = search(_records(), "dentist appointment", session=session)
    assert session._loop is loop
    assert any(row["retained_checkpoint"] for row in second)
    assert session._loop.witness.verify(session._loop.checkpoint)


def test_retaining_loop_rollback_on_strong_disturbance():
    session = RetainedMemorySession()
    search(_records(), "dentist appointment", session=session)
    checkpoint = session._loop.checkpoint
    bad = (-2.0 * checkpoint.state).astype(np.float32)
    out = session.disturb(bad)
    assert out["rolled_back"] is True
    assert session._loop.witness.verify(session._loop.checkpoint)


def test_new_bank_resets_retention():
    session = RetainedMemorySession()
    rows = [
        {"id": "1", "title": "Project", "content": "project alpha"},
        {"id": "2", "title": "Project", "content": "project beta"},
    ]
    search(rows, "project", session=session)
    assert len(session._signature[0]) == 2
    previous = session._loop
    search(rows[:1], "project", session=session)
    assert len(session._signature[0]) == 1
    assert session._loop is not previous


def test_semantic_and_lexical_dimension_safety():
    rows = [
        {"id": "1", "title": "summer project", "content": "milestone today",
         "embedding_model": "embeddinggemma",
         "embedding": [1.0] + [0.0] * 31},
        {"id": "2", "title": "summer project", "content": "milestone tomorrow"},
    ]
    q = [1.0] + [0.0] * 31
    first = search(rows, "summer project", query_embedding=q,
                   embedding_model="embeddinggemma")
    second = search(rows, "summer project", query_embedding=q,
                    embedding_model="embeddinggemma")
    assert first == second
    assert {x["record"]["id"] for x in first} == {"1", "2"}
    assert all(x["witness_verified"] for x in first)


def test_all_semantic_records_produce_verified_winner():
    records = [
        {"id": "1", "title": "project alpha", "content": "task completed",
         "embedding_model": "embeddinggemma",
         "embedding": [1.0] + [0.0] * 31},
        {"id": "2", "title": "project beta", "content": "task planned",
         "embedding_model": "embeddinggemma",
         "embedding": [0.0, 1.0] + [0.0] * 30},
    ]
    found = search(records, "project", query_embedding=[1.0] + [0.0] * 31,
                   embedding_model="embeddinggemma")
    assert found and found[0]["record"]["id"] == "1"
    assert any(x["witness_selected"] for x in found)


def test_original_witness_does_not_verify_factual_truth():
    rows = [{"id": "1", "title": "note", "content": "The moon is made of cheese"}]
    result = search(rows, "moon cheese")[0]
    assert result["witness_verified"]
    assert result["record"]["content"] == "The moon is made of cheese"
