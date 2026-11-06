"""Real encrypted-record desktop scale test; never claims 1B performance.

Run from desktop/: python benchmarks/scale_indexed_vault.py --records 25001
Uses the shipping Vault.add(), encrypted index, unchanged Core/Witness search.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hzdesktop.retrieval import search
from hzdesktop.vault import BROWSE_PAGE_SIZE, MAX_RECORDS, Vault

PASSWORD = "temporary-scale-test-password-only"


def benchmark(records: int) -> dict:
    if not 1 <= records <= 100_000:
        raise ValueError("This CI smoke benchmark supports 1..100,000 records")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="hz-index-scale-") as folder:
        path = Path(folder) / "encrypted.sqlite3"
        selected = [0, records // 2, records - 1]
        ids: dict[int, str] = {}
        with Vault(path, PASSWORD, create=True) as vault:
            for i in range(records):
                ids[i] = vault.add(
                    f"Project sector{i} milestone{i}",
                    f"private trialnote{i} projectarchive commonmarker, item {i}."
                ) if i in selected else vault.add(
                    f"Project sector{i} milestone{i}",
                    f"private trialnote{i} projectarchive commonmarker, item {i}."
                )
                if (i + 1) % 5_000 == 0:
                    print(json.dumps({"inserted": i + 1, "elapsed_s": round(time.perf_counter() - started, 2)}), flush=True)
            insert_s = time.perf_counter() - started
            assert vault.count() == records
            recent, cursor = vault.list_recent()
            assert len(recent) == min(BROWSE_PAGE_SIZE, records)
            if records > BROWSE_PAGE_SIZE:
                assert cursor is not None
                older, _ = vault.list_recent(before_rowid=cursor)
                assert older
                assert set(x["id"] for x in older).isdisjoint(x["id"] for x in recent)
            timings = []
            for index in selected:
                cue = f"sector{index} milestone{index} trialnote{index}"
                t = time.perf_counter()
                candidates = vault.search_candidates(cue)
                found = search(candidates, cue)
                took_ms = (time.perf_counter() - t) * 1_000
                assert found and found[0]["record"]["id"] == ids[index], (index, found[:1])
                assert found[0]["witness_verified"] is True
                timings.append(round(took_ms, 3))
            t = time.perf_counter()
            common_candidates = vault.search_candidates("commonmarker")
            common_ms = (time.perf_counter() - t) * 1_000
            assert 1 <= len(common_candidates) <= 256
            assert all("commonmarker" in x["content"] for x in common_candidates)
            database_bytes = path.stat().st_size
        t = time.perf_counter()
        with Vault(path, PASSWORD) as vault:
            reopen_ms = (time.perf_counter() - t) * 1_000
            assert vault.count() == records
            for index in selected:
                cue = f"sector{index} milestone{index} trialnote{index}"
                matches = search(vault.search_candidates(cue), cue)
                assert matches and matches[0]["record"]["id"] == ids[index]
            vault.delete(ids[records // 2])
            assert vault.count() == records - 1
            assert vault.search_candidates(f"sector{records // 2} milestone{records // 2}") == []
        raw = path.read_bytes()
        assert b"private trialnote" not in raw
        assert b"projectarchive" not in raw
        return {
            "status": "PASS",
            "actual_encrypted_records_inserted": records,
            "old_limit_exceeded": records > 20_000,
            "software_ceiling": MAX_RECORDS,
            "insert_seconds": round(insert_s, 3),
            "database_bytes": database_bytes,
            "indexed_retrieval_ms_by_position": timings,
            "common_term_candidate_lookup_ms": round(common_ms, 3),
            "common_term_candidates": len(common_candidates),
            "reopen_ms": round(reopen_ms, 3),
            "persisted_lookup": "PASS",
            "witness_id_checks": "PASS",
            "encrypted_plaintext_sample": "NOT_PRESENT",
            "delete_index_consistency": "PASS",
            "page_size": BROWSE_PAGE_SIZE,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "disclaimer": "Not a billion-memory scale or retrieval-accuracy benchmark",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=25_001)
    args = parser.parse_args()
    print("SCALE_TEST_RESULT=" + json.dumps(benchmark(args.records), sort_keys=True), flush=True)
