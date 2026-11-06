#!/usr/bin/env python3
"""Real-document desktop retrieval benchmark using FineWeb, not synthetic memory.

HingeZero's actual encrypted Vault.add(), indexed candidate lookup, original
Core and Witness are exercised. Queries are copied from held-out source text.
No document text is fabricated, repeated to inflate N, or planted with a key.
This benchmark measures lexical-evidence retrieval, NOT semantic question answering.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hzdesktop.retrieval import search, tokens
from hzdesktop.vault import Vault

DATASET = "HuggingFaceFW/fineweb"
CONFIG = "sample-10BT"
REVISION = "9bb295ddab0e05d785b879661af7260fed5140fc"
PASSWORD = "public-corpus-only-ephemeral-test-password"


def iter_real_documents():
    from datasets import load_dataset
    ds = load_dataset(DATASET, name=CONFIG, split="train",
                      revision=REVISION, streaming=True)
    for row in ds:
        if not isinstance(row, dict):
            continue
        body = row.get("text")
        source_id = row.get("id")
        source_url = row.get("url")
        if not isinstance(body, str) or not isinstance(source_id, str):
            continue
        if not isinstance(source_url, str):
            source_url = ""
        yield source_id, source_url, body


def real_query(text: str) -> tuple[str, str] | None:
    """Contiguous evidence fragment and partial-word-loss version, both sourced."""
    words = tokens(text)
    if len(words) < 24:
        return None
    start = len(words) // 3
    phrase = words[start:start + 9]
    if len(phrase) < 9 or len(set(phrase)) < 5:
        return None
    return " ".join(phrase), " ".join(phrase[::2])


def main(args):
    if not 1 <= args.records <= 1_000_000_000:
        raise ValueError("records must be 1..1,000,000,000")
    if not 1 <= args.queries <= args.records:
        raise ValueError("queries must be 1..records")
    if args.records >= 100_000 and not args.confirm_large_run:
        raise ValueError("Large jobs require --confirm-large-run and persistent storage")
    if args.records >= 100_000 and not args.vault:
        raise ValueError("For large jobs specify an existing large volume with --vault")
    if not 400 <= args.max_chars <= 10_000:
        raise ValueError("max-chars must be 400..10,000")
    t0 = time.perf_counter()
    tmp = tempfile.TemporaryDirectory(prefix="hz-real-") if not args.vault else None
    try:
        path = Path(args.vault) if args.vault else Path(tmp.name) / "fineweb.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError("Refusing to overwrite an existing real-data vault")
        samples = {}
        sample_indices = {
            int(round((args.records - 1) * i / max(1, args.queries - 1)))
            for i in range(args.queries)
        }
        counted = 0
        seen_source_ids = set() if args.records <= 100_000 else None
        source_hash = hashlib.sha256()
        with Vault(path, PASSWORD, create=True) as vault:
            for source_id, source_url, body in iter_real_documents():
                if seen_source_ids is not None:
                    if source_id in seen_source_ids:
                        continue
                    seen_source_ids.add(source_id)
                content = body[:args.max_chars].strip()
                query = real_query(content)
                if not query:
                    continue
                # The stored text is an authentic excerpt from an original webpage.
                hostname = urlsplit(source_url).hostname or "FineWeb document"
                identifier = vault.add(hostname, content, source_url[:400])
                source_hash.update(source_id.encode("utf-8", "replace"))
                source_hash.update(b"\x00")
                source_hash.update(hashlib.sha256(content.encode("utf-8")).digest())
                if counted in sample_indices:
                    samples[counted] = {
                        "id": identifier,
                        "source_id_sha256": hashlib.sha256(source_id.encode()).hexdigest(),
                        "url": source_url,
                        "queries": query,
                    }
                counted += 1
                if counted % args.progress == 0:
                    print(json.dumps({"actual_records": counted, "insert_s": round(time.perf_counter()-t0, 2)}), flush=True)
                if counted == args.records:
                    break
            if counted < args.records:
                raise RuntimeError(f"Source exhausted after {counted}; target was {args.records}")
            insert_s = time.perf_counter() - t0
            reports = []
            for position, sample in samples.items():
                exact, missing = sample["queries"]
                for label, phrase in [("verbatim_evidence", exact), ("half_terms_removed", missing)]:
                    start = time.perf_counter()
                    candidates = vault.search_candidates(phrase)
                    candidate_ms = (time.perf_counter()-start)*1000
                    for steps in (0, 8):
                        start = time.perf_counter()
                        ranked = search(candidates, phrase, steps=steps)
                        query_ms = (time.perf_counter()-start)*1000
                        reports.append({
                            "position": position,
                            "regime": label,
                            "steps": steps,
                            "candidate_count": len(candidates),
                            "target_in_candidate_set": any(r["id"] == sample["id"] for r in candidates),
                            "recall_at_1": bool(ranked and ranked[0]["record"]["id"] == sample["id"]),
                            "recall_at_5": any(r["record"]["id"] == sample["id"] for r in ranked),
                            "all_witness_verified": all(r["witness_verified"] for r in ranked),
                            "candidate_lookup_ms": round(candidate_ms, 3),
                            "core_rerank_ms": round(query_ms, 3),
                            "source_id_sha256": sample["source_id_sha256"],
                        })
            sizes = path.stat().st_size
            count = vault.count()
        t = time.perf_counter()
        with Vault(path, PASSWORD) as vault:
            reopened_ms = round((time.perf_counter()-t)*1000, 3)
            assert vault.count() == count
            first = next(iter(samples.values()))
            assert vault.search_candidates(first["queries"][0])
        metrics = {}
        for regime in ("verbatim_evidence", "half_terms_removed"):
            for steps in (0, 8):
                subset = [x for x in reports if x["regime"] == regime and x["steps"] == steps]
                metrics[f"{regime}_steps_{steps}"] = {
                    "queries": len(subset),
                    "recall_at_1": sum(x["recall_at_1"] for x in subset)/len(subset),
                    "recall_at_5": sum(x["recall_at_5"] for x in subset)/len(subset),
                    "in_candidate_set": sum(x["target_in_candidate_set"] for x in subset)/len(subset),
                    "all_witness_verified": all(x["all_witness_verified"] for x in subset),
                    "max_candidate_lookup_ms": max(x["candidate_lookup_ms"] for x in subset),
                    "max_core_rerank_ms": max(x["core_rerank_ms"] for x in subset),
                }
        result = {
            "status": "PASS" if all(x["all_witness_verified"] for x in reports) else "FAIL",
            "dataset": DATASET, "config": CONFIG, "revision": REVISION,
            "record_type": "authentic webpage text excerpts, not entire documents",
            "max_chars_per_excerpt": args.max_chars,
            "actual_encrypted_records": count,
            "target_1b_reached": count == 1_000_000_000,
            "source_record_digest": source_hash.hexdigest(),
            "insert_seconds": round(insert_s, 3),
            "vault_bytes": sizes,
            "reopen_ms": reopened_ms,
            "metrics": metrics,
            "limitation": "Source-text lexical queries, not semantic QA, not independent 1B validation",
        }
        print("REAL_DATA_RESULT=" + json.dumps(result, sort_keys=True), flush=True)
        if args.out:
            Path(args.out).write_text(json.dumps({"summary": result, "queries": reports}, indent=2) + "\n")
        if result["status"] != "PASS":
            raise AssertionError("Failed Witness verification")
    finally:
        if tmp:
            tmp.cleanup()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--records", type=int, default=1000)
    p.add_argument("--queries", type=int, default=40)
    p.add_argument("--max-chars", type=int, default=1200)
    p.add_argument("--progress", type=int, default=500)
    p.add_argument("--vault", type=str, help="Fresh vault file on persistent external storage")
    p.add_argument("--out", type=str)
    p.add_argument("--confirm-large-run", action="store_true")
    main(p.parse_args())
