#!/usr/bin/env python3
"""Paired full-bank 1-bit HingeZero experiment: two cues versus one.

A cue pair is either:
 - SAME_SOURCE: two non-overlapping public excerpts from a single document
 - CONFLICT: fragment A from source i and fragment B from distinct source j

These are not independent-source corroboration or correctness labels.
Metrics penalise false acceptance of conflicting pairs. Every method has
identical inputs and the SAME deterministic corroboration gate. No oracle IDs
are passed into retrieval. All 1-bit patterns participate in all updates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
import numpy as np

HERE=Path(__file__).resolve().parent
import sys
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parents[1]))

from engine import EvidenceAnchoredAttractors, METHODS
from operators import (
    AttractorBank, flip, make_correlated_bank, packed_from_text, real_fineweb,
)


def evaluate(engine, cases: list[tuple[bytes, bytes, int, bool]],
             name: str) -> dict:
    out={"condition":name,"cases":len(cases),"methods":{}}
    for mode in METHODS:
        exact=accepted=correct_accepts=wrong_accepts=reviews=valid=preflight_holds=preserved=0
        mean=[]
        for primary,second,target,is_consistent in cases:
            t0=time.perf_counter_ns()
            pred=engine.decide(primary,second,mode)
            mean.append((time.perf_counter_ns()-t0)/1e6)
            if pred.witness_valid:
                valid+=1
            elif pred.reason == "preflight_disagreement":
                # No Witness step occurs because conflicting cues were held
                # before any refinement or stored-state readout.
                preflight_holds+=1
            else:
                raise AssertionError("Original Witness failed to verify a selected state")
            if pred.preserved_initial:
                preserved+=1
            if pred.candidate==target:
                exact+=1
            if pred.decision=="ACCEPT":
                accepted+=1
                if is_consistent and pred.candidate==target:
                    correct_accepts+=1
                else:
                    wrong_accepts+=1
            else:
                reviews+=1
        results={
            "raw_target_id_recall_at_1":exact/len(cases),
            "accepted":accepted,
            "correctly_accepted":correct_accepts,
            "wrongly_accepted":wrong_accepts,
            "reviewed":reviews,
            "coverage":accepted/len(cases),
            "accepted_precision":correct_accepts/accepted if accepted else None,
            "witness_valid_count":valid,
            "preflight_hold_count":preflight_holds,
            "preserved_zero_step_count":preserved,
            "mean_ms":round(statistics.mean(mean),4),
        }
        if valid+preflight_holds!=len(cases):
            raise AssertionError("Unaccounted missing or invalid Witness state")
        out["methods"][mode]=results
        print("ANCHOR_ROW="+json.dumps(
            {"condition":name,"mode":mode,**results},sort_keys=True),flush=True)
    return out


def real_queries(target_size:int, query_count:int):
    raw=real_fineweb(target_size)
    bank=AttractorBank([r[2] for r in raw])
    engine=EvidenceAnchoredAttractors(bank,topk=5)
    strict=EvidenceAnchoredAttractors(
        bank,topk=5,require_initial_top1_agreement=True)
    picks=sorted(set(round(i*(target_size-1)/(query_count-1))
                     for i in range(query_count)))
    digest=hashlib.sha256()
    for uid,excerpt,_,_ in raw:
        digest.update(uid.encode())
        digest.update(hashlib.sha256(excerpt.encode()).digest())
    report=[]
    for wordcount in (25,12):
        genuine=[];conflict=[]
        for ix in picks:
            _,_,_,words=raw[ix]
            a=len(words)//5
            b=3*len(words)//5
            if a+wordcount>b or b+wordcount>len(words):
                raise AssertionError("Two cues must be strictly nonoverlapping")
            cue1=packed_from_text(" ".join(words[a:a+wordcount]))
            cue2=packed_from_text(" ".join(words[b:b+wordcount]))
            genuine.append((cue1,cue2,ix,True))
            other=(ix+target_size//2)%target_size
            other_words=raw[other][3]
            other_start=3*len(other_words)//5
            conflict_cue=packed_from_text(
                " ".join(other_words[other_start:other_start+wordcount]))
            conflict.append((cue1,conflict_cue,ix,False))
        report.append(evaluate(engine,genuine,f"same_public_webpage_{wordcount}words"))
        report.append(evaluate(engine,conflict,f"conflicting_public_webpages_{wordcount}words"))
        report.append(evaluate(strict,genuine,f"strict_same_webpage_{wordcount}words"))
        report.append(evaluate(strict,conflict,f"strict_conflicting_webpages_{wordcount}words"))
    return {"source":"FineWeb sample-10BT actual webpage excerpts",
            "record_count":target_size,"query_count":len(picks),
            "source_digest":digest.hexdigest(),
            "no_independent_truth_corroboration":True,
            "data_scope":"two nonoverlapping fragments from same page, or two different pages",
            "results":report}


def synthetic(seed_count:int):
    seeds=(20261101,20261102,20261103)[:seed_count]
    groups=[]
    for noise in (48,80,96):
        rows=[]
        for seed in seeds:
            bank=AttractorBank(make_correlated_bank(seed+66,96,.8))
            engine=EvidenceAnchoredAttractors(bank,topk=5)
            rng_a=np.random.default_rng(seed*17+noise)
            rng_b=np.random.default_rng(seed*29+noise)
            genuine=[];conflict=[]
            for i,code in enumerate(bank.packed):
                a=flip(code,noise,rng_a)
                b=flip(code,noise,rng_b)
                genuine.append((a,b,i,True))
                j=(i+bank.memories.shape[0]//2)%len(bank.packed)
                conflict.append((a,flip(bank.packed[j],noise,rng_b),i,False))
            rows.append(evaluate(engine,genuine,f"same_1bit_pattern_{noise}flips_seed{seed}"))
            rows.append(evaluate(engine,conflict,f"different_1bit_patterns_{noise}flips_seed{seed}"))
            if noise == 80:
                strict=EvidenceAnchoredAttractors(
                    bank,topk=5,require_initial_top1_agreement=True)
                rows.append(evaluate(strict,genuine,f"strict_same_1bit_{noise}flips_seed{seed}"))
                rows.append(evaluate(strict,conflict,f"strict_different_1bit_{noise}flips_seed{seed}"))
        groups.extend(rows)
    return {"source":"synthetic correlated binary patterns from seeded latent prototypes",
            "groups":groups,"seed_count":len(seeds),
            "bit_flips":[48,80,96],"synthetic_record_count":96}


def decide_verdict(real):
    pair25=next(x for x in real["results"] if x["condition"]=="same_public_webpage_25words")
    conflict25=next(x for x in real["results"] if x["condition"]=="conflicting_public_webpages_25words")
    d=pair25["methods"]
    # Must beat BOTH same-information controls in correct accepted outcomes,
    # WITHOUT causing more conflicting-cue accepts, a priori.
    h=d["two_cue_dual_gate"]
    zero=d["two_cue_zero_gate"]
    tanh=d["two_cue_tanh_gate"]
    false=conflict25["methods"]
    success=(
        h["correctly_accepted"]>max(zero["correctly_accepted"],tanh["correctly_accepted"])
        and false["two_cue_dual_gate"]["wrongly_accepted"]<=
            min(false["two_cue_zero_gate"]["wrongly_accepted"],
                false["two_cue_tanh_gate"]["wrongly_accepted"])
    )
    strict_same = next(x for x in real["results"]
                       if x["condition"] == "strict_same_webpage_25words")
    strict_conflict = next(x for x in real["results"]
                           if x["condition"] == "strict_conflicting_webpages_25words")
    return {
        "predeclared_dual_tanh_specific_gain": bool(success),
        "strict_exploratory_second_gate": {
            "zero_correct_accepts": strict_same["methods"]["two_cue_zero_gate"]["correctly_accepted"],
            "dual_correct_accepts": strict_same["methods"]["two_cue_dual_gate"]["correctly_accepted"],
            "zero_conflicting_pair_accepts": strict_conflict["methods"]["two_cue_zero_gate"]["wrongly_accepted"],
            "dual_conflicting_pair_accepts": strict_conflict["methods"]["two_cue_dual_gate"]["wrongly_accepted"],
        },
        "same_source_25word_correct_accepts":{
            "zero":zero["correctly_accepted"],
            "plain_tanh":tanh["correctly_accepted"],
            "dual_tanh":h["correctly_accepted"],
        },
        "different_source_25word_false_accepts":{
            "zero":false["two_cue_zero_gate"]["wrongly_accepted"],
            "plain_tanh":false["two_cue_tanh_gate"]["wrongly_accepted"],
            "dual_tanh":false["two_cue_dual_gate"]["wrongly_accepted"],
        },
        "important_limitation":"No model can infer source truth from matching 1-bit hashes alone",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--records",type=int,default=128)
    p.add_argument("--queries",type=int,default=64)
    p.add_argument("--seeds",type=int,default=3)
    p.add_argument("--output")
    a=p.parse_args()
    if not 32<=a.records<=200 or not 2<=a.queries<=a.records or not 1<=a.seeds<=3:
        raise ValueError("Invalid experiment configuration")
    start=time.perf_counter()
    syn=synthetic(a.seeds)
    real=real_queries(a.records,a.queries)
    verdict=decide_verdict(real)
    report={
        "title":"distinguish attractors using two observations before reinforcement",
        "original_hinge_zero_core_untouched":True,
        "stored_patterns_bits":256,
        "field":"all packed 1bit stored vectors, temporary float for tanh",
        "candidate_preselection":"none",
        "new_architecture":"cross-cue candidate weighting + matched deterministic review gate",
        "strict_preflight_conditions":"EXPLORATORY follow-up: require each separate cue to independently select same top1 before any updates",
        "baseline_equivalence":"all methods see both cues and the same review gate",
        "experiment_methods":METHODS,
        "real":real,
        "synthetic":syn,
        "verdict":verdict,
        "elapsed_seconds":round(time.perf_counter()-start,3)
    }
    if a.output:
        Path(a.output).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("ANCHOR_CONCLUSION="+json.dumps({
        "verdict":verdict,"real_records":a.records,
        "real_source_queries":a.queries,
        "synthetic_groups":len(syn["groups"]),
        "duration_seconds":report["elapsed_seconds"]
    },sort_keys=True),flush=True)


if __name__=="__main__":
    main()
