# Genuine one-billion-real-memory experiment — protocol, not a result

## Current evidence and clear limitations

- The separate C++20 1B experiment stores **generated 128-bit patterns**, not genuine documents.
- Desktop scale tests stored up to 100,000 **generated short strings** in encrypted SQLite.
- The new `real_fineweb.py` pipeline ingests **actual web-page text excerpts** directly through `Vault.add`, then searches using the unchanged HingeZero Witness/Core. FineWeb dataset and licence: https://huggingface.co/datasets/HuggingFaceFW/fineweb (ODC-By 1.0 + CommonCrawl terms). Dataset revision is pinned in the source. We do **not** upload private user data.
- As of this protocol, **one billion genuine text records have not been inserted, queried, or validated**. The source and local disk scale are large enough to make this a separate external-compute experiment.

## Reproducible smaller real-data run

From the repository root:

```bash
cd desktop
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt 'datasets>=3.6,<5' 'huggingface_hub>=0.28'
python benchmarks/real_fineweb.py --records 10000 --queries 100 --config sample-10BT --max-chars 1200 --out real_10k_results.json
```

The script reads FineWeb source records, **never creates filler memories or pads the count**, preserves each original source URL in encrypted record metadata, stores an authentic excerpt (up to 1,200 characters by default), and constructs queries from source text. It measures Recall@1, Recall@5, candidate recall, latency, zero-versus-eight step HingeZero, Witness checks, persisted record count and file size. For this benchmark, Witness verification means genuine identity preservation, **not factual correctness**. Verbatim text fragments are much easier than natural-language questions and this is **not** a semantic QA or paraphrase benchmark.

## A sharded real-corpus smoke test

```bash
python benchmarks/real_fineweb.py --records 1000 --queries 12 --config sample-10BT \
  --shard-dir /path/to/new/external/experiment --shard-size 250
```

This forces four separate real encrypted vault shards and searches **every shard** before the global HingeZero Core ranks a bounded merged shortlist. The global retrieval is **approximate**: it starts with at most 256 lexical candidates per shard. Global Recall@1/@5 must be independently measured; it is not exact exhaustive nearest-neighbour retrieval over the full corpus.

## Full target: 1,000,000,000 genuine FineWeb excerpts

This run must use **the full dataset (`--config default`)**, not the much smaller 10BT sample. Full FineWeb has substantially more than a billion source documents. The following command specifies *what to measure* but has **not** been executed at 1B:

```bash
python benchmarks/real_fineweb.py \
  --records 1000000000 --queries 200 \
  --config default --max-chars 1200 \
  --shard-dir /mnt/large-persistent-volume/hingezero-fineweb-1b \
  --shard-size 250000 --progress 10000 \
  --confirm-large-run --out /mnt/large-persistent-volume/fineweb_1b_results.json
```

Approximately **4,000 SQLite shards** would be produced when the full target is reached. The benchmark requires a user-supplied persistent filesystem with potentially *many terabytes* free. The observed 10K real-excerpt run occupied about 149 MB, or approximately **14.9 TB for 1B if that observed per-record footprint stayed constant**; this is only a rough storage extrapolation, **not a capacity measurement**. Budget substantial headroom and a separate backup; an estimate based on 10K rows is not a promise the full corpus fits. Input transfer may also be many terabytes. The GitHub-hosted runner has only 14 GB disk, making the 1B job impossible on the normal public CI machine.

The current benchmark uses a fixed public-corpus-only development passphrase; it is **not** suitable for private or sensitive files. For private data use the user-controlled desktop vault with a unique passphrase.

### Interrupted runs

If persistent shards still exist, pass `--resume` with the same options. The current research prototype replays the ordered FineWeb stream from its start, skipping records already committed in the shards before resuming. That ensures a deterministic number of source rows if the upstream pinned dataset order remains stable, but it is **very inefficient at large offsets** and does not yet implement robust row-group resume checkpoints. Do not claim 1B readiness until restart/recovery at large scale is independently verified.

### Pass/fail and interpretation

A successful billion result requires all of the following, not just a configured integer:

1. Exactly 1,000,000,000 real source-derived encrypted records committed; shard counts and original-source digest recorded.
2. No generated filler, repeated hand-made identity strings, or synthetic records substituted for source text.
3. Reopening every shard confirms durable record count, and the full-shard retrieval search returns measured Recall@1 and Recall@5 with explicit failures.
4. Query latency distribution, end-to-end throughput, CPU/RAM, measured disk occupancy, and number of fetched source documents reported.
5. Both steps=0 and steps=8 reported on the same queries; Witness verified as stored-state identity, not correctness or semantic truth.
6. A documented, held-out real QA/paraphrase/noisy-evidence evaluation **in addition to** the current source-fragment tests before claiming improvements for AI memory.

Any storage exhaustion, partial data ingestion, source duplication, unmeasured full-bank queries, or cancelled run is **not** a one-billion-memory pass.

This sharded code is a research instrument, not a released one-billion-memory desktop product. It retains the actual encryption, candidate search and original HingeZero Core/Witness; its approximate cross-shard preselection and large-scale fault tolerance require further evaluation.
