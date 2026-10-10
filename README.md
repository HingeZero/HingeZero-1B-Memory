# HingeZero: One Billion Memories — C++20 Reproducibility Kit

**Research architecture:** David Duffy / HingeZero  
**Benchmark date:** 10 October 2026  
**Platform:** C++20, Linux x86-64 little-endian tested; standard library only for C++ engine  
**Repository contents:** source, verification scripts, frozen protocol and recorded outputs; **no 16 GB bank is included**.

## What the experiment actually did

The C++20 adaptation generated **1,000,000,000 deterministic bipolar 128-bit patterns**, occupying **16,000,000,000 bytes** (14.90 GiB). It created 900 million first, then appended 100 million. The SHA-256 digest of the *entire original prefix* remained unchanged.

Each query uses HingeZero's **eight-step dual-tanh refinement** (alpha 4.5, epsilon 0.10, lambda 0.02) with a fixed 256-pattern field. The implementation then computes a score for **every one of the one billion records** against that refined query using a streamed byte-lookup implementation of signed dot product. It has **no externally selected Hamming or nearest-neighbour shortlist**. It returns a tagged bank row and verifies exact stored-state membership and preservation.

It is a **packed binary specialization**, not a complete replacement of the original Python core. It is **not** a semantic-memory/clinical-care test, and it does not embed documents or conversational content.

## Reported results (original hardware/run)

| Cue type | Correct among 2 target records |
| --- | ---: |
| Exact | 2/2 |
| 20% bit flips (26 positions) | 2/2 |
| 35% bit flips (45 positions) | 0/2 |
| 50% missing | 2/2 |
| One severely damaged cue | 0/2 |
| Four separate severely damaged cues combined | 2/2 |

- **8/12** correct IDs across the twelve preregistered retrieval cases.
- **12/12** selections passed the tagged-state witness.
- **~7.05 seconds median per full-bank scan**, plus **~0.243 ms median refinement** in the measured environment.
- SHA-256 of first 900 million records before/after append: `0ab2870c17c77733d6645ae11187f794786dd7bf05eabe970b36f70ec27847bc`.

*With just two target IDs, these are example-case counts rather than an estimate of population recall accuracy.* Hardware and compiler affect timing. Library math/rounding can affect borderline retrieval ties.

## Quick start (~seconds; creates only 128 KiB plus append)

You need a C++20 compiler (`g++` 11+ tested using g++ 14), Python 3 for the smoke assertion, and bash.

```bash
git clone https://github.com/HingeZero/HingeZero-1B-Memory.git
cd HingeZero-1B-Memory
bash run_smoke.sh
```

This compiles C++, creates 8,192 memory rows, appends 256, compares the *original prefix SHA-256*, checks witnessed tagged state, then tests exact and 20%-corrupted retrieval. It prints **SMOKE TEST PASS** if all conditions succeed.

**Optional independent comparison to original Python core:** install NumPy and run `python3 parity_check.py` after compiling; this creates an 8,192-row bank if missing, then compares five native outputs to the unmodified `HingeZero_Core.py`. Running this script writes `parity_results.json` with the five numerical comparison results. For a basic internal-consistency check on the archived full-bank evidence, run `python3 verify_recorded_results.py`. This checks the recorded CSV's case count, witness flags and success count; it does **not** replace an independent rerun.

## Full billion-memory reproduction

Requires **at least 16 GB of free disk** (more recommended), 64-bit system with little-endian binary storage, a few hundred MB free RAM for execution, and adequate time for 12 full-bank scans. **Use an output filename that does not yet exist:**

```bash
g++ -O3 -std=c++20 HingeZero_Native_1B.cpp -o hz_native
bash run_1b.sh /path/to/fast/disk/hz_1b_bank.bin
```

`run_1b.sh` writes `reproduced_1b_run.log` in the kit folder. It generates the bank with deterministic seed and ID mapping, verifies old-prefix hash after append, then executes the two targets across all six cue regimes. The 16 GB bank remains wherever you asked it to be written; delete it manually when finished.

Expected per-case selected indices and measurements from the original run appear in `billion_results.csv` and `HingeZero_Cpp20_1B_Report.md`. Compare your output against those files. Timing will vary. The reference bank prefix hash should match on the same little-endian representation.

## Files

- `HingeZero_Native_1B.cpp` — C++20 complete source (single translation unit).
- `HingeZero_Core.py` — original Python HingeZero witness reference.
- `run_smoke.sh` — small, executable integrity/retrieval check.
- `run_1b.sh` — portable, 900M+100M bank generation and twelve native full scans.
- `parity_check.py` — optional Python/NumPy numerical comparison.
- `SEALED_BENCHMARK.md` — protocol recorded before the final run.
- `billion_results.csv` — measured case-level outputs (including failures).
- `HingeZero_Cpp20_1B_Report.md` — full explanation and scope.
- `verify_recorded_results.py` — independently cross-check reported CSV, JSON and run-log values.
- Use `git` commit history and the recorded benchmark logs to inspect revisions.

## Limitations and provenance

The bank contains reproducible random binary patterns, not text or larger memory payloads. The witness verifies exact stored-state membership, **not whether the intended identity was selected**. This variant covers uniform evidence and a fixed field but not the complete Python retaining-loop, per-record metadata or permissions. The generated bank is intentionally absent to keep the public archive small.

Source is provided for inspection and reproducing these experiments; **no open-source licence is specified** in this package.
