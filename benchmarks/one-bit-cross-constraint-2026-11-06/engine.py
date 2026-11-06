"""1-bit packed retrieval + original HingeZero Core + auditable constraint gate.

Research-only demonstrator. Codes are *256 physical bits* (32 bytes) per
memory; no float vectors are stored in the low-level bank. A shortlist is
decoded to float32 only for the unchanged HingeZeroWitness high-level stage.

Logical contradictions are NOT magically rejected by Hamming cancellation or
the original Witness. The explicit rule gate makes the safety decision.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from HingeZero_Core import HingeZeroWitness, HingeZeroState

BITS = 256
BYTES = BITS // 8
ACTIONS = (
    "activate_motor", "transfer_payload", "unlock_door",
    "start_pump", "enable_heater", "apply_torque",
)
# Fictional demonstration rules; not qualified for clinical, industrial,
# emergency, or other real-world safety decisions.
CONFLICT_FACT = {
    "activate_motor": "guard_open",
    "transfer_payload": "isolation_active",
    "unlock_door": "authorisation_missing",
    "start_pump": "leak_detected",
    "enable_heater": "overtemp_alarm",
    "apply_torque": "safety_lock",
}


def pack_1bit(text: str) -> bytes:
    """Deterministic signed random-hyperplane-like token sketch, packed to bits.

    Python integer vote counters exist only while encoding; no full-precision
    representation is retained in the 1-bit bank. Not a semantic embedding.
    """
    words = re.findall(r"[a-z0-9_]+", text.lower())
    if not words:
        raise ValueError("Empty cue cannot be represented")
    votes = [0] * BITS
    for word in words:
        hashed = hashlib.shake_256(b"HZ_1BIT_V1\x00" + word.encode()).digest(BYTES)
        for j in range(BITS):
            votes[j] += 1 if hashed[j // 8] & (1 << (j % 8)) else -1
    code = bytearray(BYTES)
    for j, vote in enumerate(votes):
        if vote > 0:
            code[j // 8] |= 1 << (j % 8)
    return bytes(code)


def hamming(a: bytes, b: bytes) -> int:
    if len(a) != BYTES or len(b) != BYTES:
        raise ValueError("Expected exactly 256 packed bits per state")
    return (int.from_bytes(a, "little") ^ int.from_bytes(b, "little")).bit_count()


def flip_bits(code: bytes, n: int, seed: int) -> bytes:
    if not 0 <= n <= BITS or len(code) != BYTES:
        raise ValueError("Invalid 1-bit corruption")
    data = bytearray(code)
    rng = random.Random(seed)
    for j in rng.sample(range(BITS), n):
        data[j // 8] ^= 1 << (j % 8)
    return bytes(data)


def unpack_for_hinge(code: bytes) -> np.ndarray:
    """The ONLY 1-bit -> float conversion; performed after shortlist."""
    if len(code) != BYTES:
        raise ValueError("Invalid packed memory code")
    bits = np.unpackbits(np.frombuffer(code, dtype=np.uint8), bitorder="little")
    return (bits.astype(np.float32) * 2.0) - 1.0


@dataclass(frozen=True)
class Record:
    id: str
    subject: str
    action: str
    context: str
    fact_name: str
    fact_value: bool | None
    provenance_ok: bool
    code: bytes


@dataclass(frozen=True)
class Challenge:
    subject: str
    action: str
    cue: bytes
    expected_record_id: str
    label: str


@dataclass(frozen=True)
class Decision:
    status: str  # ALLOW, BLOCK, or REVIEW (no default 'allow')
    reason: str
    selected_id: str | None
    witness_verified: bool | None
    match: bool
    hamming_distance: int | None


def expected_status(record: Record) -> str:
    if not record.provenance_ok or record.fact_value is None:
        return "REVIEW"
    return "BLOCK" if record.fact_value else "ALLOW"


def make_fixture(count: int = 192) -> tuple[list[Record], list[Challenge]]:
    """Reproducible *fictional* cases, never claims real medical/safety data."""
    if not 6 <= count <= 2500:
        raise ValueError("Fixture supports 6..2500 unique records")
    records, challenges = [], []
    for i in range(count):
        subject = f"asset_{i:06d}"
        action = ACTIONS[i % len(ACTIONS)]
        context = (f"facility_zone_{i % 17} {subject} task_{action} "
                   f"station_{i % 11} inspection_group_{i % 7}")
        code = pack_1bit(context)
        flag = (False, True, None, True, False)[i % 5]
        provenance_ok = i % 5 <= 2
        rec = Record(f"evidence_{i:06d}", subject, action, context,
                     CONFLICT_FACT[action], flag, provenance_ok, code)
        records.append(rec)
        challenges.append(Challenge(subject, action, code, rec.id,
                                    expected_status(rec)))
    return records, challenges


def constraint_wall(action: str, fact: str) -> bytes:
    """Permanent 256-bit rule mask for a known externally checked condition."""
    if CONFLICT_FACT.get(action) != fact:
        raise ValueError("Unknown or mismatched constraint")
    return hashlib.shake_256(
        b"HZ_CONSTRAINT_WALL_V1\\x00" + (action + ":" + fact).encode()
    ).digest(BYTES)


def encode_typed_fact(wall: bytes, value: bool) -> bytes:
    """safe=wall, conflict=exact complement; does not infer external truth."""
    if len(wall) != BYTES or type(value) is not bool:
        raise ValueError("Expected a valid 1-bit wall and Boolean evidence")
    return bytes((bit ^ 0xFF) if value else bit for bit in wall)


def explicit_rule_gate(rec: Record, challenge: Challenge) -> tuple[str, str]:
    """External typed constraints, not a geometric Witness truth oracle."""
    if rec.subject != challenge.subject or rec.action != challenge.action:
        return "REVIEW", "wrong_identity_or_action"
    if not rec.provenance_ok:
        return "REVIEW", "unverified_claimed_source"
    if rec.action not in CONFLICT_FACT or rec.fact_name != CONFLICT_FACT[rec.action]:
        return "REVIEW", "missing_or_unknown_rule"
    if rec.fact_value is None:
        return "REVIEW", "missing_typed_evidence"
    if type(rec.fact_value) is not bool:
        return "REVIEW", "malformed_typed_evidence"
    # The complementary state is assembled from typed evidence, rather
    # than magically emerging from Hamming retrieval or Witness identity.
    wall = constraint_wall(rec.action, rec.fact_name)
    observation = encode_typed_fact(wall, rec.fact_value)
    distance = hamming(wall, observation)
    if distance == BITS:
        return "BLOCK", "exact_opposing_1bit_constraint"
    if distance == 0:
        return "ALLOW", "same_1bit_constraint"
    return "REVIEW", "partial_or_corrupted_constraint"


def decide(records: list[Record], challenge: Challenge, *,
           mode: str, top_k: int = 32) -> Decision:
    if mode not in {"binary", "hz0", "hz8"}:
        raise ValueError("Unknown baseline/HZ condition")
    if not records or not 1 <= top_k <= 256:
        raise ValueError("Invalid records/candidate count")
    if len(challenge.cue) != BYTES:
        return Decision("REVIEW", "invalid_binary_cue", None, False, False, None)
    # Actual packed XOR/popcount retrieval over ALL the low-level 1-bit bank.
    shortlist = sorted(
        ((hamming(challenge.cue, rec.code), rec.id, rec)
         for rec in records), key=lambda row: (row[0], row[1])
    )[:top_k]
    if not shortlist:
        return Decision("REVIEW", "no_candidates", None, None, False, None)

    witness_valid: bool | None = None
    if mode == "binary":
        distance, _, selected = shortlist[0]
    else:
        # Decoding occurs ONLY here, on the 1-bit shortlist.
        matrix = np.stack([unpack_for_hinge(item[2].code) for item in shortlist])
        similarity_evidence = np.asarray(
            [(BITS - item[0]) / BITS for item in shortlist], dtype=np.float32
        )
        witness = HingeZeroWitness(matrix, similarity_evidence)
        cue = unpack_for_hinge(challenge.cue)
        if mode == "hz8":
            cue = witness.refine(cue)  # unchanged 8-step dual-tanh Core
        # Correct normalized bipolar dot product; no hidden reranker.
        scores = witness.memories @ (cue / float(np.linalg.norm(cue)))
        locked = witness.observe(cue, scores)
        witness_valid = bool(witness.verify(locked))
        if not witness_valid:
            return Decision("REVIEW", "witness_state_invalid", None, False,
                            False, None)
        distance, _, selected = shortlist[locked.candidate_index]
    status, reason = explicit_rule_gate(selected, challenge)
    return Decision(status, reason, selected.id, witness_valid,
                    selected.id == challenge.expected_record_id, distance)
