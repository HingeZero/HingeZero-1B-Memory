#!/usr/bin/env python3
"""Fine-grained step-strength sweep on genuine packed 1-bit memory bank.

Fits update strength (eta) on a calibration half of real FineWeb queries,
then reports locked-out, distinct held-out queries. Does not tune using
held-out labels. All modes use the *full* HingeZero bank, no Hamming shortlist.
The original eight-step Core is the eta=1, steps=8 control.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import time
from pathlib import Path

from engine import Challenge, pack_1bit
from fractional import fractional_retrieve
from full_field import FullFieldOneBit
from real_text_probe import get_fineweb


def queries_for(records, count):
    positions = sorted(set(round(i * (len(records)-1) / (count-1))
                           for i in range(count)))
    rows = []
    for j, i in enumerate(positions):
        record = records[i]
        terms = re.findall(r"[a-z0-9_]+", record.context.lower())
        start = len(terms) // 3
        rows.append({
            "target": i,
            "cohort": "calibration" if j % 2 == 0 else "heldout",
            "exact": record.code,
            "fragment25": pack_1bit(" ".join(terms[start:start+25])),
            "fragment12": pack_1bit(" ".join(terms[start:start+12])),
        })
    return rows


def metrics(bank, rows, regime, eta, steps):
    correct = valid = 0
    timings = []
    for row in rows:
        t0 = time.perf_counter_ns()
        result = fractional_retrieve(bank, row[regime], eta, steps)
        timings.append((time.perf_counter_ns() - t0) / 1e6)
        correct += result.index == row["target"]
        valid += result.witness_valid is True
    return {
        "n": len(rows),
        "recall_at_1": correct / len(rows),
        "correct": correct,
        "witness_valid": valid,
        "mean_query_ms": round(statistics.mean(timings), 4),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=128)
    parser.add_argument("--queries", type=int, default=64)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    if not 16 <= args.records <= 256 or not 4 <= args.queries <= args.records:
        raise ValueError("Experiment requires 16..256 records and 4..N source queries")
    records = get_fineweb(args.records, 1200)
    bank = FullFieldOneBit(records)
    source_hash = hashlib.sha256()
    for rec in records:
        source_hash.update(rec.id.encode("utf-8"))
        source_hash.update(hashlib.sha256(rec.context.encode("utf-8")).digest())
    queries = queries_for(records, args.queries)
    calibration = [r for r in queries if r["cohort"] == "calibration"]
    heldout = [r for r in queries if r["cohort"] == "heldout"]
    # True .001 increments over [0.001..0.020] plus larger controls.
    etas = [i / 1000 for i in range(1, 21)] + [.025, .05, .1, .2, .5, 1.0]
    configs = [(0.0, 0)] + [(eta, steps) for eta in etas
                             for steps in (1, 2, 4, 8)]
    outcome = []
    for eta, steps in configs:
        row = {"eta": eta, "steps": steps, "calibration": {},
               "heldout": {}}
        for regime in ("fragment25", "fragment12", "exact"):
            row["calibration"][regime] = metrics(
                bank, calibration, regime, eta, steps)
            row["heldout"][regime] = metrics(
                bank, heldout, regime, eta, steps)
        outcome.append(row)
    # Select only from the calibration half; prefer zero iterations at
    # equal Recall@1 to avoid mistaking unnecessary extra compute for gain.
    def preference(x):
        return (x["calibration"]["fragment25"]["correct"],
                -x["steps"], -x["eta"])
    chosen = max(outcome, key=preference)
    best_nonzero = max((x for x in outcome if x["eta"] > 0), key=preference)
    zero = next(x for x in outcome if x["eta"] == 0 and x["steps"] == 0)
    original = next(x for x in outcome if x["eta"] == 1 and x["steps"] == 8)
    best_five = sorted(outcome, key=preference, reverse=True)[:5]
    result = {
        "experiment": "fractional_full_field_1bit_v1",
        "dataset": "FineWeb sample-10BT, authentic webpage excerpt source",
        "records": len(records), "bits_per_stored_record": 256,
        "packed_bank_bytes": bank.packed_bytes,
        "full_field_patterns": len(bank.witness.field_memories),
        "no_hamming_candidate_preselection": True,
        "original_core_unchanged": True,
        "fractional_update": "unit((1-eta*lambda)*x + eta*eps*F(x))",
        "eta_grid": etas,
        "step_counts": [1, 2, 4, 8],
        "source_digest": source_hash.hexdigest(),
        "query_cohorts": {"calibration": len(calibration), "heldout": len(heldout)},
        "selection_metric": "calibration fragment25 Recall@1; prefer fewer steps on ties",
        "selected": {"eta": chosen["eta"], "steps": chosen["steps"]},
        "zero": zero, "original": original,
        "selected_result": chosen,
        "best_nonzero_result": best_nonzero,
        "calibration_top_five": [
            {"eta": x["eta"], "steps": x["steps"],
             "fragment25_recall": x["calibration"]["fragment25"]["recall_at_1"]}
            for x in best_five
        ],
        "all_parameter_results": outcome,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    # Include numbers for all reference conditions on a separate holdout.
    for name, item in (("zero", zero), ("original_8_steps", original),
                       ("best_nonzero", best_nonzero),
                       ("calibration_selected", chosen)):
        print("FRACTIONAL_HOLDOUT=" + json.dumps({
            "name": name, "eta": item["eta"], "steps": item["steps"],
            "calibration_fragment25": item["calibration"]["fragment25"],
            "heldout_fragment25": item["heldout"]["fragment25"],
            "heldout_fragment12": item["heldout"]["fragment12"],
            "heldout_exact": item["heldout"]["exact"],
        }, sort_keys=True), flush=True)
    # Report the user-requested tiny increments explicitly. The full grid
    # is included in the downloadable JSON artifact.
    for eta in (.001, .002, .005, .010, .020, .050, .1, .2, .5, 1.0):
        item = next(x for x in outcome if x["eta"] == eta and x["steps"] == 8)
        print("FRACTIONAL_8STEP_GRID=" + json.dumps({
            "eta": eta,
            "calibration_25word": item["calibration"]["fragment25"]["recall_at_1"],
            "holdout_25word": item["heldout"]["fragment25"]["recall_at_1"],
            "holdout_12word": item["heldout"]["fragment12"]["recall_at_1"],
            "holdout_exact": item["heldout"]["exact"]["recall_at_1"],
            "mean_query_ms": item["heldout"]["fragment25"]["mean_query_ms"],
        }, sort_keys=True), flush=True)
    print("FRACTIONAL_RESULT=" + json.dumps({
        "records": result["records"],
        "query_cohorts": result["query_cohorts"],
        "source_digest": result["source_digest"],
        "eta_grid_count": len(etas),
        "config_count": len(configs),
        "selected": result["selected"],
        "holdout_delta_vs_zero": (
            chosen["heldout"]["fragment25"]["recall_at_1"] -
            zero["heldout"]["fragment25"]["recall_at_1"]
        ),
        "holdout_delta_vs_original": (
            chosen["heldout"]["fragment25"]["recall_at_1"] -
            original["heldout"]["fragment25"]["recall_at_1"]
        ),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
