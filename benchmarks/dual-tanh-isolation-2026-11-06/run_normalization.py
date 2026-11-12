#!/usr/bin/env python3
"""Activation/normalisation isolation using real and correlated 1-bit memories.

The study is a matched 19-condition ablation, not parameter tuning on the
held-out labels. "Response power=2" changes the field weighting and is clearly
separated from pure scalar normalisation. All methods retrieve via ALL stored
1-bit patterns and the original HingeZero Witness identity mechanism.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
import statistics
import time
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from operators import (
    AttractorBank, flip, make_correlated_bank, packed_from_text, real_fineweb,
)
from normalization import Configuration, configurations, diagnostic, retrieve

SEEDS = (20261101, 20261102, 20261103)
SHARED = (.5, .8)
BIT_ERRORS = (80, 96, 112)


def measure(bank, queries):
    configs = [None] + configurations()
    record = {"n": len(queries), "methods": {}}
    for cfg in configs:
        key = "zero" if cfg is None else cfg.name
        results = [retrieve(bank, code, target, cfg) for code, target in queries]
        record["methods"][key] = {
            "correct": sum(r.correct for r in results),
            "all_witness_valid": all(r.valid for r in results),
            "mean_ms": round(statistics.mean(r.elapsed_ms for r in results), 4),
            "mean_target_margin": round(statistics.mean(r.target_margin for r in results), 6),
            # Store per-query outcomes for computing paired rescues/damages
            # without putting source text into the GitHub logs.
            "_correct": [bool(r.correct) for r in results],
        }
        if not record["methods"][key]["all_witness_valid"]:
            raise AssertionError(f"Invalid stored state in {key}")
    reference = record["methods"]["zero"]["_correct"]
    for method in record["methods"].values():
        data = method.pop("_correct")
        method["rescues_vs_zero"] = sum(not a and b for a,b in zip(reference,data))
        method["damages_vs_zero"] = sum(a and not b for a,b in zip(reference,data))
        method["accuracy"] = method["correct"] / len(queries)
    return record


def synthetic(seed_limit):
    cases=[]
    for shared in SHARED:
        for bits in BIT_ERRORS:
            batches=[]
            for seed in SEEDS[:seed_limit]:
                codes=make_correlated_bank(seed + round(shared*1000), 96, shared)
                bank=AttractorBank(codes)
                rng=np.random.default_rng(seed + round(shared*1000) + bits*777)
                q=[(flip(c,bits,rng),i) for i,c in enumerate(codes)]
                batches.append(measure(bank,q))
            methods={}
            for key in batches[0]["methods"]:
                group=[r["methods"][key] for r in batches]
                correct=sum(r["correct"] for r in group)
                n=sum(x["n"] for x in batches)
                methods[key]={
                    "correct": correct, "n": n, "accuracy": correct/n,
                    "rescues":sum(x["rescues_vs_zero"] for x in group),
                    "damages":sum(x["damages_vs_zero"] for x in group),
                    "mean_ms":round(statistics.mean(x["mean_ms"] for x in group),4),
                    "witness_all_valid":all(x["all_witness_valid"] for x in group),
                }
            row={"source":"synthetic_correlated_bipolar",
                 "shared":shared, "bit_errors":bits,
                 "seeds":SEEDS[:seed_limit], "records_per_bank":96,
                 "methods":methods}
            cases.append(row)
            brief={
                "shared":shared,"noise_bits":bits,"queries":methods["zero"]["n"],
                "zero":methods["zero"]["accuracy"],
                "tanh_l1":methods["tanh__l1_original__p1"]["accuracy"],
                "dual45_l1":methods["dual45__l1_original__p1"]["accuracy"],
                "dual45_l2":methods["dual45__l2_scaled__p1"]["accuracy"],
                "dual45_fixed":methods["dual45__fixed_response_bound__p1"]["accuracy"],
                "dual45_sharp_l1":methods["dual45__l1_original__p2"]["accuracy"]
            }
            print("NORMALISATION_SYNTH="+json.dumps(brief,sort_keys=True),flush=True)
    return cases


def real_conditions(corpus_size, query_count):
    corpus=real_fineweb(corpus_size)
    bank=AttractorBank([row[2] for row in corpus])
    targets=sorted(set(round(i*(len(corpus)-1)/(query_count-1))
                       for i in range(query_count)))
    h=hashlib.sha256()
    for uid,excerpt,_,_ in corpus:
        h.update(uid.encode())
        h.update(hashlib.sha256(excerpt.encode()).digest())
    rows=[]
    for words_count in (25, 12):
        queries=[]
        for index in targets:
            tokens=corpus[index][3]
            at=len(tokens)//3
            cue=packed_from_text(" ".join(tokens[at:at+words_count]))
            queries.append((cue,index))
        m=measure(bank,queries)
        row={"source":"real_fineweb_source_fragments",
             "words":words_count,"source_document_count":len(corpus),
             "source_digest":h.hexdigest(), **m}
        rows.append(row)
        print("NORMALISATION_REAL_ALL="+json.dumps({
            "words": words_count, "queries":m["n"],
            "methods": {name:{
                "correct":item["correct"],"accuracy":item["accuracy"],
                "rescues":item["rescues_vs_zero"],
                "damages":item["damages_vs_zero"]
            } for name,item in m["methods"].items()}
        },sort_keys=True),flush=True)
        variants=["zero","tanh__l1_original__p1",
                  "dual45__l1_original__p1","dual45__l2_scaled__p1",
                  "dual45__fixed_response_bound__p1",
                  "dual45__l1_original__p2","tanh__l1_original__p2"]
        print("NORMALISATION_REAL="+json.dumps({
            "words":words_count, "queries":m["n"],
            "methods":{k:m["methods"][k] for k in variants}
        },sort_keys=True),flush=True)
    return rows


def conclusion(synthetic_rows, real_rows):
    key="dual45__l1_original__p1"
    benchmark="tanh__l1_original__p1"
    # Originally claimed "the second term helps retrieval" would require
    # a positive gain vs both zero and plain tanh. Predeclared broad
    # >3pp criterion at each genuine evidence condition plus >=4/6
    # correlated synthetic cases. Not a statistical significance claim.
    def delta(row):
        m=row["methods"]
        return m[key]["accuracy"]-max(m["zero"]["accuracy"],m[benchmark]["accuracy"])
    real_gains=[delta(x) for x in real_rows]
    positive_synthetic=sum(delta(x)>=.03 for x in synthetic_rows)
    broad=all(x>=.03 for x in real_gains) and positive_synthetic>=4

    return {
        "original_dual_tanh_broad_advantage_criterion_met":broad,
        "original_dual_tanh_real_deltas_vs_best_zero_or_tanh":real_gains,
        "synthetic_cases_with_3pp_gain":positive_synthetic,
        "synthetic_cases_total":len(synthetic_rows),
        "meaning":"Measured record-identity accuracy; no evidence validation or deployed safety",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",type=int,default=3)
    p.add_argument("--real-records",type=int,default=128)
    p.add_argument("--real-queries",type=int,default=48)
    p.add_argument("--output")
    args=p.parse_args()
    if not 1<=args.seeds<=3 or not 2<=args.real_queries<=args.real_records:
        raise ValueError("Invalid experiment dimensions")
    start=time.perf_counter()
    simulations=synthetic(args.seeds)
    reality=real_conditions(args.real_records,args.real_queries)
    verdict=conclusion(simulations,reality)
    report={
        "hypothesis":"Is dual-tanh retrieval failure due to relative response weighting or scalar field normalisation?",
        "bit_memory_storage":"256 packed bits (32 bytes) each",
        "original_hinge_zero_core_changed":False,
        "original_setting":"dual45__l1_original__p1",
        "same_epsilon_lambda_eight_steps":True,
        "matched_activations": ["tanh","dual025","dual45"],
        "scalar_denominators":["l1_original","l2_scaled","fixed_response_bound"],
        "shape_conditions":[
            {"power":1,"status":"unchanged activation response"},
            {"power":2,"status":"EXPERIMENTAL shape modification, not original Core"}
        ],
        "hamming_shortlist":False,
        "small_field_limit":256,
        "source_of_truth":"known document ID or labelled synthetic memory ID, never a verified clinical fact",
        "diagnostic":diagnostic(),
        "synthetic":simulations,
        "real":reality,
        "verdict":verdict,
        "seconds":round(time.perf_counter()-start,3),
    }
    if args.output:
        Path(args.output).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("NORMALISATION_CONCLUSION="+json.dumps({
        "verdict":verdict,
        "weak_strong_ratios":{k:round(v["weak_over_strong"],5)
                              for k,v in report["diagnostic"].items()},
        "configs":len(configurations())+1,
        "real_queries":args.real_queries,
        "seconds":report["seconds"]
    },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
