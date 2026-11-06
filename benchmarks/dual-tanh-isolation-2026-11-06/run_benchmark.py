#!/usr/bin/env python3
"""Predeclared, direct mathematical dual-tanh advantage search.

1. Synthetic *correlated* packed 1-bit families: multiple independent seeds,
   matching corruption and identical full-field bank for all operators.
2. Authentic FineWeb documents: exact, 25-word and 12-word source cues.
3. Fixed original eight-step budget, lambda/epsilon/normalization.
4. Controls: zero step, tanh(h), tanh(2h), dual tanh alpha=.25,
   original HZ dual tanh alpha=4.5. No Hamming shortlist or trick labels.
5. Counts rescues AND damaged previously-correct target IDs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
from operators import (
    AttractorBank, METHODS, flip, make_correlated_bank, packed_from_text,
    real_fineweb,
)

SEEDS = (20261101, 20261102, 20261103, 20261104)
SHARED = (0.0, .5, .8)
CORRUPTION = (32, 64, 96)


def measure(bank: AttractorBank, queries: list[tuple[bytes, int]]):
    hits = {name: [] for name in METHODS}
    duration_ms = {name: [] for name in METHODS}
    margins = {name: [] for name in METHODS}
    witness_bad = {name: 0 for name in METHODS}
    for cue, target in queries:
        for name in METHODS:
            result = bank.retrieve(cue, name, target)
            hits[name].append(result.chosen == target)
            duration_ms[name].append(result.elapsed_ms)
            margins[name].append(result.target_margin)
            witness_bad[name] += not result.witness_valid
    zero = hits["zero"]
    outcome = {"n": len(queries), "methods": {}}
    for name in METHODS:
        v = hits[name]
        outcome["methods"][name] = {
            "correct": sum(v),
            "accuracy": sum(v) / len(queries),
            "rescued_from_zero": sum((not a) and b for a, b in zip(zero, v)),
            "damaged_from_zero": sum(a and (not b) for a, b in zip(zero, v)),
            "mean_target_margin": float(statistics.mean(margins[name])),
            "mean_latency_ms": round(statistics.mean(duration_ms[name]), 4),
            "witness_failures": witness_bad[name],
        }
        if witness_bad[name]:
            raise AssertionError("Stored-state Witness verification failed")
    return outcome


def synthetic(seed_limit: int):
    report = []
    for shared in SHARED:
        for noise in CORRUPTION:
            by_seed = []
            for seed in SEEDS[:seed_limit]:
                packed = make_correlated_bank(seed + round(shared * 1000), 96, shared)
                bank = AttractorBank(packed)
                rng = np.random.default_rng(seed + round(shared * 1000) + noise * 777)
                queries = [(flip(code, noise, rng), i) for i, code in enumerate(packed)]
                row = measure(bank, queries)
                row["seed"] = seed
                by_seed.append(row)
            values = {}
            for name in METHODS:
                correct = sum(x["methods"][name]["correct"] for x in by_seed)
                total = sum(x["n"] for x in by_seed)
                values[name] = {
                    "correct": correct,
                    "accuracy": correct / total,
                    "rescued": sum(x["methods"][name]["rescued_from_zero"] for x in by_seed),
                    "damaged": sum(x["methods"][name]["damaged_from_zero"] for x in by_seed),
                    "mean_latency_ms": round(statistics.mean(
                        x["methods"][name]["mean_latency_ms"] for x in by_seed
                    ), 4),
                    "witness_failures": sum(
                        x["methods"][name]["witness_failures"] for x in by_seed),
                    "individual_seed_accuracy": [
                        x["methods"][name]["accuracy"] for x in by_seed],
                }
            row = {
                "family_shared_fraction": shared, "flipped_bits": noise,
                "actual_pattern_count": 96,
                "queries": sum(x["n"] for x in by_seed),
                "methods": values,
            }
            report.append(row)
            print("ABLATION_SYNTH=" + json.dumps(row, sort_keys=True), flush=True)
    return report


def real_docs(target_count: int, query_count: int):
    source = real_fineweb(target_count)
    packed = [x[2] for x in source]
    bank = AttractorBank(packed)
    if not 2 <= query_count <= target_count:
        raise ValueError("Query count must be 2..records")
    targets = sorted(set(round(i*(target_count-1) / (query_count-1))
                         for i in range(query_count)))
    digest = hashlib.sha256()
    for uid, content, _, _ in source:
        digest.update(uid.encode())
        digest.update(hashlib.sha256(content.encode()).digest())
    reports = []
    for regime in ("full_source", "source_fragment25", "source_fragment12"):
        queries = []
        for i in targets:
            _, _, code, words = source[i]
            at = len(words)//3
            cue = code if regime == "full_source" else packed_from_text(
                " ".join(words[at:at + (25 if regime.endswith("25") else 12)])
            )
            queries.append((cue, i))
        m = measure(bank, queries)
        row = {"regime": regime, "queries": len(queries), **m}
        reports.append(row)
        print("ABLATION_REAL=" + json.dumps({
            "regime": regime,
            "n": m["n"],
            "methods": m["methods"]
        }, sort_keys=True), flush=True)
    return {
        "dataset": "HuggingFaceFW/fineweb sample-10BT public original webpage excerpts",
        "corpus_size": len(source),
        "source_digest": digest.hexdigest(),
        "real_labels": "source-document identity only, not semantic QA",
        "results": reports,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--real-records", type=int, default=128)
    parser.add_argument("--real-queries", type=int, default=48)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not 1 <= args.seeds <= len(SEEDS):
        raise ValueError("Seeds must be 1..4")
    started = time.perf_counter()
    simulation = synthetic(args.seeds)
    authenticity = real_docs(args.real_records, args.real_queries)

    # Criterion declared BEFORE observing the data, deliberately demanding:
    # core HZ45 must exceed *all* controls by >=3pp on BOTH real fragments
    # and on ALL correlated synthetic noise scenarios. This is a gate for
    # a broad general advantage, not a test of statistical significance.
    compare = ("zero", "tanh", "tanh2")
    real_hard = [x for x in authenticity["results"] if "fragment" in x["regime"]]
    correlated_hard = [x for x in simulation if x["family_shared_fraction"] >= .5]
    def advantage(row):
        d = row["methods"]
        return d["dual45"]["accuracy"] - max(d[c]["accuracy"] for c in compare)
    broad = all(advantage(x) >= .03 for x in real_hard + correlated_hard)
    best_case = max(simulation + real_hard, key=advantage)
    report = {
        "title": "isolating HingeZero dual tanh against matched associative controls",
        "original_core_file_modified": False,
        "activation": "tanh(h) + alpha*tanh(2h)",
        "original_alpha": 4.5,
        "exploratory_alpha": .25,
        "same_lambda_epsilon_step_budget": True,
        "steps_per_nonlinear_mode": 8,
        "zero_step_control": True,
        "normalization": "sum absolute responses; unit state",
        "packed_one_bit_storage": True,
        "full_field_no_hamming_or_ann_shortlist": True,
        "float_compute_workspace": True,
        "synthetic": simulation,
        "real_web_source": authenticity,
        "broad_3pp_advantage_vs_all_controls": broad,
        "best_observed_context": {
            "context": ("real" if best_case in real_hard else "synthetic"),
            "case": best_case.get("regime", {
                "shared": best_case.get("family_shared_fraction"),
                "noise_bits": best_case.get("flipped_bits"),
            }),
            "dual45_gap_vs_best_control": advantage(best_case),
        },
        "limitations": [
            "Not one billion real memories",
            "No real-life semantic, clinical, or safety truth assessment",
            "Correlated tests are synthetic, source retrieval is from public webpages",
            "Candidate identity projection and Witness validity are not factual correctness",
            "Four seeds and 48 real target queries are not independent external replication",
            "Positive selected-context findings are exploratory; avoid cherry-picking",
        ],
        "elapsed_seconds": round(time.perf_counter()-started, 2),
    }
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("ABLATION_CONCLUSION="+json.dumps({
        "broad_3pp_advantage": broad,
        "best_observed_context": report["best_observed_context"],
        "records": authenticity["corpus_size"],
        "real_query_targets": args.real_queries,
        "synthetic_configs": len(simulation),
        "elapsed_seconds": report["elapsed_seconds"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
