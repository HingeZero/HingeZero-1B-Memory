#!/usr/bin/env python3
"""Fetch public FineWeb rows as real JSONL from the official HF dataset server.

This is a small regression-test fixture downloader, NOT a bulk 1B data path.
It refuses to create filler and verifies actual id, URL and original text.
"""
from __future__ import annotations
import argparse
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://datasets-server.huggingface.co/rows"


def fetch(output: str, count: int):
    if not 1 <= count <= 500:
        raise ValueError("Small public API fixture only: 1..500")
    offset = 0
    seen = set()
    with open(output, "x", encoding="utf-8") as out:
        while len(seen) < count:
            url = BASE + "?" + urlencode({
                "dataset": "HuggingFaceFW/fineweb",
                "config": "sample-10BT",
                "split": "train",
                "offset": offset,
                "length": min(100, count - len(seen)),
            })
            req = Request(url, headers={"User-Agent": "HingeZero-public-real-data-benchmark/1.0"})
            with urlopen(req, timeout=90) as response:
                result = json.load(response)
            rows = result.get("rows") or []
            if not rows:
                raise RuntimeError("FineWeb public API returned no more actual rows")
            for entry in rows:
                row = entry.get("row") or {}
                if not isinstance(row.get("id"), str) or not isinstance(row.get("text"), str):
                    continue
                if row["id"] in seen:
                    continue
                seen.add(row["id"])
                out.write(json.dumps({"id": row["id"], "text": row["text"],
                                      "url": row.get("url") or ""},
                                     ensure_ascii=False) + "\n")
                if len(seen) == count:
                    break
            offset += len(rows)
    print("REAL_FINEWEB_DATASET_SERVER_ROWS=" + str(len(seen)), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--rows", type=int, default=180)
    args = p.parse_args()
    fetch(args.output, args.rows)
