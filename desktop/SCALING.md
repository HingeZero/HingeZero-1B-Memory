# Desktop scalability: what "1 billion" means

## Three distinct capacities

1. **C++20 research:** The separate `HingeZero_Native_1B.cpp` demonstration writes and scans **1,000,000,000 generated 128-bit bipolar patterns**. Its 16 GB bank is *not* a text vault. Refer to the frozen protocol, measured retrieval cases and documented failures.
2. **Published v0.1.6 desktop:** The latest previously published binary has a **20,000 encrypted chunk** cap and linear decrypt-and-score candidate search. Updating this source does not update already downloaded binaries.
3. **v0.1.7-dev source:** The local SQLite vault now exposes a **1,000,000,000-record software ceiling** and HMAC-keyed disk lexical index to avoid decrypting all records for search. **No billion-record text store or successful billion-query benchmark has been run or asserted.** Disk, SQLite limits, throughput, recovery and relevance remain unverified at scale.

## Retrieval path

The application encrypts each user-selected note/document chunk with AES-256-GCM as before. It additionally writes indexed, per-vault HMAC-SHA256-derived 128-bit digests of distinct lexical terms. Lookup uses those digests to select **up to 256 candidates** from SQLite, decrypts only those candidates and then runs the unchanged HingeZero Core's **eight-step dual-tanh refinement, Witness verification and session retention loop**. This is explicit lexical preselection, not a full-billion-pattern HingeZero scan. No external network connection is needed.

The 200-record browser uses rowid keyset pagination. API and local Ollama retrieval also use the new index. Token-frequency and query/access patterns still leak through the index; it is **not** a fully oblivious encrypted-search design. With no common indexed terms, semantic-only retrieval may miss relevant memories even with a local embedding model enabled. Multi-document import is not an atomic all-or-nothing batch; back up before bulk imports.

## Upgrade, storage and constraints

Opening an existing v1 encrypted vault creates the new token index locally and backfills existing encrypted records. **Back up the vault before trying development software.** Index creation may take time; if interrupted, it restarts at next unlock. The AES-GCM record format remains unchanged. Old published binaries have no knowledge of the new index and still enforce the original 20,000 cap.

A billion full-text chunks can require **hundreds of gigabytes to many terabytes** after encryption and lexical indexing, depending on chunk length and token diversity; the 16 GB synthetic pattern bank is not the relevant size estimate. The unchanged 256-candidate Core cannot guarantee recall on a very large corpus; common-token searches may still have substantial database work. These are engineering limits requiring actual load tests and recall-quality benchmarks before a claim of one-billion-record production readiness.

## Local validation

From `desktop/`:

```bash
python -m pip install -r requirements-build.txt
python -m pytest -q
python -m hzdesktop.selfcheck
```

The new tests check persistence, legacy index migration, encrypted term storage, candidate Witness use, deletion, 200-record browsing and the 1B configuration ceiling using small data only. **Tests do not simulate or prove one billion records.** The GitHub pull request runs the repository's audit workflow before changes are merged.

Commercial licensing remains governed by `desktop/LICENSE.md`, `desktop/NOTICE.txt` and `desktop/COMMERCIAL-LICENSING.md`. The separately licensed/unspecified research and secure-memory packages are not changed.
