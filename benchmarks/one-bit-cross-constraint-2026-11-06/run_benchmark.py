#!/usr/bin/env python3
"""Reproducible three-way 1-bit/HingeZero constraint experiment.

All measurements are on fictional labelled engineering situations. Labels
come from the explicit rules, not external or independent safety adjudication.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import statistics
import time

from engine import BITS, decide, flip_bits, make_fixture, Challenge


def evaluate(records, challenges, flips: int, method: str) -> dict:
    elapsed_ms = []
    identity_hits = 0
    reviews = 0
    blocked = 0
    expected_blocks = 0
    caught_blocks = 0
    missed_blocks = 0
    unsafe_allows = 0
    false_blocks = 0
    witness_checked = 0
    witness_passed = 0
    confusion = {"ALLOW": {"ALLOW": 0, "BLOCK": 0, "REVIEW": 0},
                 "BLOCK": {"ALLOW": 0, "BLOCK": 0, "REVIEW": 0},
                 "REVIEW": {"ALLOW": 0, "BLOCK": 0, "REVIEW": 0}}
    for i, original in enumerate(challenges):
        cue = flip_bits(original.cue, flips, i * 100003 + flips + 11)
        case = Challenge(original.subject, original.action, cue,
                         original.expected_record_id, original.label)
        start = time.perf_counter_ns()
        output = decide(records, case, mode=method)
        elapsed_ms.append((time.perf_counter_ns() - start) / 1_000_000)
        confusion[original.label][output.status] += 1
        identity_hits += output.match
        reviews += output.status == "REVIEW"
        blocked += output.status == "BLOCK"
        if original.label == "BLOCK":
            expected_blocks += 1
            caught_blocks += output.status == "BLOCK"
            missed_blocks += output.status != "BLOCK"
            unsafe_allows += output.status == "ALLOW"
        if original.label == "ALLOW":
            false_blocks += output.status == "BLOCK"
        if output.witness_verified is not None:
            witness_checked += 1
            witness_passed += output.witness_verified
    n = len(challenges)
    times = sorted(elapsed_ms)
    return {
        "mode": method,
        "bit_flip_count": flips,
        "bit_error_rate": flips / BITS,
        "cases": n,
        "identity_accuracy": identity_hits / n,
        "decision_accuracy": sum(confusion[s][s] for s in confusion) / n,
        "abstention_rate": reviews / n,
        "predicted_block_count": blocked,
        "actual_block_count": expected_blocks,
        "block_recall": caught_blocks / expected_blocks if expected_blocks else None,
        "missed_block_count": missed_blocks,
        "unsafe_allow_count": unsafe_allows,
        "false_block_count": false_blocks,
        "witness_checked_count": witness_checked,
        "witness_valid_count": witness_passed,
        "mean_query_ms": round(statistics.mean(times), 4),
        "median_query_ms": round(statistics.median(times), 4),
        "p95_query_ms": round(times[min(n-1, int(0.95 * (n-1)))], 4),
        "confusion": confusion,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=180)
    parser.add_argument("--top-noise", type=int, default=128)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    records, cases = make_fixture(args.records)
    assert len(records) == len(cases)
    assert all(len(r.code) == BITS // 8 for r in records)
    assert sum(len(r.code) for r in records) == args.records * 32
    levels = [x for x in (0, 32, 64, 96, 128) if x <= args.top_noise]
    if not levels:
        raise ValueError("Need a noise level")
    result = {
        "experiment": "1-bit_cross_constraint_v1",
        "data_type": "fictional_deterministic_labeled_engineering_scenarios",
        "packed_bits_per_record": BITS,
        "total_packed_bank_bytes": sum(len(r.code) for r in records),
        "record_count": len(records),
        "hamming_full_bank_scanned": True,
        "hinge_refinement": "original_unchanged_8step_core",
        "witness_role": "stored_state_identity_only",
        "rule_role": "external_explicit_conflict_checks_not_bit_cancellation",
        "modes": ["binary", "hz0", "hz8"],
        "results": [],
    }
    for flips in levels:
        for mode in result["modes"]:
            entry = evaluate(records, cases, flips, mode)
            result["results"].append(entry)
            print("CASE_RESULT=" + json.dumps({
                k: v for k, v in entry.items() if k != "confusion"
            }, sort_keys=True), flush=True)
            if entry["unsafe_allow_count"] or entry["false_block_count"]:
                raise AssertionError("Explicit identity gate unexpectedly issued unsafe allow/false block")
            if mode != "binary" and entry["witness_valid_count"] != entry["witness_checked_count"]:
                raise AssertionError("HingeZero Witness rejected a selected stored identity")
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("CROSS_CONSTRAINT_RESULT=" + json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
