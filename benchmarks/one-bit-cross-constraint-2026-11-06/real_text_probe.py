#!/usr/bin/env python3
"""1-bit Hamming/HZ identity retrieval on authentic public FineWeb text.

This is NOT a contradictory-action/clinical benchmark: document records have
no decision metadata and every rule decision must remain REVIEW. Only the
stored-document identity test is scored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from engine import Challenge, Record, decide, pack_1bit


def get_fineweb(n: int, max_chars: int) -> list[Record]:
    if not 16 <= n <= 500:
        raise ValueError("Public REST probe limited to 16..500 records")
    rows: list[Record] = []
    seen: set[str] = set()
    offset = 0
    while len(rows) < n:
        query = urlencode({
            "dataset": "HuggingFaceFW/fineweb",
            "config": "sample-10BT", "split": "train",
            "offset": offset,
            "length": min(100, n - len(rows)),
        })
        req = Request("https://datasets-server.huggingface.co/rows?" + query,
                      headers={"User-Agent": "HingeZero-real-one-bit-probe/0.1"})
        with urlopen(req, timeout=60) as response:
            payload = json.load(response)
        entries = payload.get("rows") or []
        if not entries:
            raise RuntimeError("FineWeb dataset server returned no further source rows")
        for entry in entries:
            record = entry.get("row") or {}
            identifier = record.get("id")
            raw = record.get("text")
            url = str(record.get("url") or "")
            if not isinstance(identifier, str) or not isinstance(raw, str):
                continue
            if identifier in seen:
                continue
            seen.add(identifier)
            excerpt = raw[:max_chars].strip()
            if len(re.findall(r"[a-z0-9_]+", excerpt.lower())) < 60:
                continue
            rows.append(Record(
                id=identifier, subject=identifier, action="public_document_only",
                context=excerpt, fact_name="", fact_value=None,
                provenance_ok=False, code=pack_1bit(excerpt)))
            if len(rows) >= n:
                break
        offset += len(entries)
        if offset > 10_000:
            raise RuntimeError("Insufficient qualifying real FineWeb excerpts")
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--records", type=int, default=128)
    p.add_argument("--queries", type=int, default=24)
    p.add_argument("--max-chars", type=int, default=1200)
    args = p.parse_args()
    if not 1 <= args.queries <= args.records:
        raise ValueError("queries must be within the corpus size")
    docs = get_fineweb(args.records, args.max_chars)
    source_hash = hashlib.sha256()
    for doc in docs:
        source_hash.update(doc.id.encode())
        source_hash.update(hashlib.sha256(doc.context.encode()).digest())
    indices = sorted(set(round(i*(len(docs)-1)/max(1,args.queries-1))
                         for i in range(args.queries)))
    results = []
    for regime in ("exact_source_excerpt", "contiguous_source_fragment"):
        for mode in ("binary", "hz0", "hz8"):
            times = []
            hits = 0
            held = 0
            witness_count = 0
            for index in indices:
                d = docs[index]
                words = re.findall(r"[a-z0-9_]+", d.context.lower())
                offset = len(words)//3
                fragment = " ".join(words[offset:offset+25])
                cue_text = d.context if regime == "exact_source_excerpt" else fragment
                challenge = Challenge(d.subject, d.action, pack_1bit(cue_text),
                                      d.id, "REVIEW")
                start = time.perf_counter_ns()
                decision = decide(docs, challenge, mode=mode)
                times.append((time.perf_counter_ns()-start)/1e6)
                hits += decision.match
                held += decision.status == "REVIEW"
                witness_count += decision.witness_verified is True
                if decision.status != "REVIEW":
                    raise AssertionError("Unlabelled public text must never get safety ALLOW/BLOCK")
            results.append({
                "condition":regime, "mode":mode, "queries":len(indices),
                "identity_recall_at_1":hits/len(indices),
                "review_rate":held/len(indices),
                "witness_verified_count":witness_count,
                "mean_query_ms":round(statistics.mean(times),3),
                "p95_query_ms":round(sorted(times)[int((len(times)-1)*.95)],3),
            })
    report={
        "dataset":"HuggingFaceFW/fineweb", "sample":"sample-10BT",
        "data":"real original webpage excerpts",
        "record_count":len(docs),
        "bits_per_stored_memory":len(docs[0].code)*8,
        "source_digest":source_hash.hexdigest(),
        "query_source":"same document full excerpt or contiguous 25-word source fragment",
        "not_safety_evaluation":True,
        "no_billion_capacity_claim":True,
        "results":results,
    }
    for row in results:
        print("REAL_1BIT_ROW="+json.dumps(row,sort_keys=True),flush=True)
    print("REAL_1BIT_RESULT="+json.dumps(report,sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
