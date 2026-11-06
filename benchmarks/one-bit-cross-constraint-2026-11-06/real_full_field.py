#!/usr/bin/env python3
"""Real FineWeb: native FULL-FIELD 1-bit HingeZero vs Hamming control.

Only public source-document identity is scored. There are no real clinical
safety labels; every document yields REVIEW in the constraint stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import time
from engine import Challenge, pack_1bit
from full_field import FullFieldOneBit, MODES
from real_text_probe import get_fineweb


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--records", type=int, default=128)
    p.add_argument("--queries", type=int, default=32)
    args = p.parse_args()
    if not 16 <= args.records <= 256 or not 2 <= args.queries <= args.records:
        raise ValueError("A genuinely full Core field requires 16..256 records")
    records = get_fineweb(args.records, 1200)
    field = FullFieldOneBit(records)
    selected = sorted(set(round(i * (len(records) - 1) / (args.queries - 1))
                          for i in range(args.queries)))
    digest = hashlib.sha256()
    for rec in records:
        digest.update(rec.id.encode("utf-8"))
        digest.update(hashlib.sha256(rec.context.encode("utf-8")).digest())
    results = []
    for regime in ("entire_original_excerpt", "25_word_contiguous_fragment"):
        cues = []
        for i in selected:
            rec = records[i]
            words = re.findall(r"[a-z0-9_]+", rec.context.lower())
            excerpt = (" ".join(words[len(words)//3:len(words)//3+25])
                       if regime == "25_word_contiguous_fragment" else rec.context)
            cues.append(Challenge(rec.subject, rec.action, pack_1bit(excerpt),
                                  rec.id, "REVIEW"))
        for mode in MODES:
            hits = 0
            all_review = 0
            witnesses = 0
            times = []
            for challenge in cues:
                t = time.perf_counter_ns()
                output = field.decide(challenge, mode)
                times.append((time.perf_counter_ns() - t) / 1e6)
                hits += output.match
                all_review += output.status == "REVIEW"
                witnesses += output.witness_verified is True
            result = {
                "regime": regime, "mode": mode, "queries": len(cues),
                "identity_recall_at_1": hits / len(cues),
                "review_rate": all_review / len(cues),
                "witness_verified_count": witnesses,
                "mean_query_ms": round(statistics.mean(times), 4),
                "median_query_ms": round(statistics.median(times), 4),
            }
            if all_review != len(cues):
                raise AssertionError("Public documents were issued fictional safety approvals")
            results.append(result)
            print("REAL_FULL_FIELD_ROW=" + json.dumps(result, sort_keys=True), flush=True)
    summary = {
        "real_source": "HuggingFaceFW/fineweb sample-10BT, public dataset server",
        "records": len(records),
        "full_bank_field_count": len(field.witness.field_ids),
        "packed_bank_bytes": field.packed_bytes,
        "source_digest": digest.hexdigest(),
        "real_semantic_question_answering": False,
        "hamming_preselection": False,
        "results": results,
    }
    print("REAL_FULL_FIELD_RESULT=" + json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
