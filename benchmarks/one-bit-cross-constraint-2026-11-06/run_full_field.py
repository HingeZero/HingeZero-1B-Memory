#!/usr/bin/env python3
"""Full-bank native packed-1-bit associative HingeZero versus Hamming control.

Same cues, same original evidence, same rule logic. 256 or fewer patterns are
required to make the ORIGINAL HingeZero Core's top-256 field include ALL of
the bank, without ANN, Hamming shortlist, or a simulated billion records.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import statistics
import time

from engine import Challenge, BITS, flip_bits, make_fixture
from full_field import FullFieldOneBit, MODES


def run(records: int, top_noise: int) -> dict:
    memory, challenges = make_fixture(records)
    full = FullFieldOneBit(memory)
    results = []
    for flips in (0, 32, 64, 96, 128):
        if flips > top_noise:
            continue
        cues = [
            Challenge(c.subject, c.action,
                      flip_bits(c.cue, flips, 100003 * i + flips + 11),
                      c.expected_record_id, c.label)
            for i, c in enumerate(challenges)
        ]
        for mode in MODES:
            t = []
            counts = {
                "ALLOW": {"ALLOW": 0, "BLOCK": 0, "REVIEW": 0},
                "BLOCK": {"ALLOW": 0, "BLOCK": 0, "REVIEW": 0},
                "REVIEW": {"ALLOW": 0, "BLOCK": 0, "REVIEW": 0},
            }
            identity = witness_checks = witness_passed = 0
            for c in cues:
                start = time.perf_counter_ns()
                output = full.decide(c, mode)
                t.append((time.perf_counter_ns() - start) / 1e6)
                counts[c.label][output.status] += 1
                identity += output.match
                witness_checks += output.witness_verified is not None
                witness_passed += output.witness_verified is True
            expected_blocks = sum(counts["BLOCK"].values())
            missed_blocks = counts["BLOCK"]["ALLOW"] + counts["BLOCK"]["REVIEW"]
            wrong_allows = counts["BLOCK"]["ALLOW"] + counts["REVIEW"]["ALLOW"]
            false_blocks = counts["ALLOW"]["BLOCK"] + counts["REVIEW"]["BLOCK"]
            ordered = sorted(t)
            result = {
                "mode": mode,
                "flipped_bits": flips,
                "flip_fraction": flips / BITS,
                "queries": len(cues),
                "identity_accuracy": identity / len(cues),
                "decision_accuracy": sum(counts[k][k] for k in counts) / len(cues),
                "abstention_rate": sum(counts[k]["REVIEW"] for k in counts) / len(cues),
                "conflict_recall": (
                    counts["BLOCK"]["BLOCK"] / expected_blocks
                    if expected_blocks else None
                ),
                "missed_conflicts": missed_blocks,
                "unsafe_allow": wrong_allows,
                "false_block": false_blocks,
                "witness_checks": witness_checks,
                "witness_passed": witness_passed,
                "mean_query_ms": round(statistics.mean(t), 4),
                "median_query_ms": round(statistics.median(t), 4),
                "p95_query_ms": round(ordered[int(.95 * (len(ordered) - 1))], 4),
                "confusion": counts,
            }
            results.append(result)
            print("FULL_FIELD_ROW=" + json.dumps(
                {k: v for k, v in result.items() if k != "confusion"},
                sort_keys=True
            ), flush=True)
    return {
        "experiment": "one_bit_full_field_associative",
        "original_hinge_core": "unchanged 8-step dual tanh",
        "corpus": "fictional deterministic typed rules and bit-error cues",
        "record_count": records,
        "total_packed_memory_bytes": full.packed_bytes,
        "bits_per_record": BITS,
        "full_bank_witness_field_count": len(full.witness.field_memories),
        "float_workspace_bytes": full.workspace.nbytes,
        "reduction_to_hamming_shortlist": False,
        "hamming_only_a_control": True,
        "no_production_safety_claim": True,
        "not_1b_scale": True,
        "results": results,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=180)
    parser.add_argument("--top-noise", type=int, default=128)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run(args.records, args.top_noise)
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("FULL_FIELD_RESULT=" + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
