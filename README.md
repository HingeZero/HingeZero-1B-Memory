# HingeZero Memory

**New research (3 November 2026):** [Witness evidence-gated decision test — 0 to 8 HingeZero steps](https://github.com/HingeZero/HingeZero-1B-Memory/tree/main/benchmarks/witness-gated-8step-2026-11-03). Includes runnable Python source, synthetic corruption trials, zero-step and ungated controls, abstention/human-review results, and explicit limitations. **This experiment is separate from the desktop release.**

**[HingeZero project contents — code, benchmarks, downloads and research](https://github.com/HingeZero/HingeZero-)**

**Save information locally. Recall it later. Connect it to your local AI.**

HingeZero Memory Desktop is an offline-first memory vault built around David Duffy's original HingeZero associative-memory core. Add notes or import documents, search your saved information, and optionally give a local AI application access through an authenticated API.

**[Download the desktop preview](https://github.com/HingeZero/HingeZero-1B-Memory/releases/latest)** · **[User guide](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/README.md)** · **[Developer integration](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/README.md#local-api-for-existing-ai-tools)**

## Download and try it

| Platform | Download |
| --- | --- |
| Windows x64 | [HZMemory-Windows-x64.zip](https://github.com/HingeZero/HingeZero-1B-Memory/releases/latest/download/HZMemory-Windows-x64.zip) |
| Linux x64 | [HZMemory-Linux-x64.tar.gz](https://github.com/HingeZero/HingeZero-1B-Memory/releases/latest/download/HZMemory-Linux-x64.tar.gz) |
| macOS | [HZMemory-macOS.zip](https://github.com/HingeZero/HingeZero-1B-Memory/releases/latest/download/HZMemory-macOS.zip) |

These are **unsigned preview builds**. Check the [release notes and SHA-256 checksums](https://github.com/HingeZero/HingeZero-1B-Memory/releases/latest) for compatibility and verification details.

1. Download and extract the package for your operating system.
2. Start `HZMemory.exe`, `HZMemory` or `HZMemory.app`, accept the permissions notice and create your vault passphrase.
3. Choose **Add memory**. Try a note such as “The HingeZero demo is Thursday at 14:00.”
4. Search for “HingeZero demo” to retrieve the saved note. Close and reopen the app, unlock the vault and search again to try persistent storage.

The desktop app works without an AI model or an internet connection. It imports only the files you select. See the [setup guide](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/README.md#start-in-60-seconds) for platform details.

## What you can use it for

- **Keep notes and documents across sessions:** saved records are encrypted in a local vault.
- **Find saved information:** word-based candidate search feeds the original eight-step HingeZero Core; results include the stored source text.
- **Use local semantic search:** optionally enable an Ollama embedding model for matching beyond shared words.
- **Connect your AI tools:** use the local API to save memories and retrieve evidence for an AI's context.

The desktop release includes the original Core, Witness verification of stored-state identity and a session-local retaining loop with rollback. Stored notes persist across restarts; retaining-loop checkpoints are session-local.

**Current scope:** up to 20,000 memory chunks, with up to 256 candidates supplied to the Core. Retrieval quality depends on the information, queries and embedding setup. Witness verification checks stored-state identity, not factual truth or answer relevance. Benchmark speeds from other HingeZero configurations are not desktop performance measurements.

## Integrate with your application

Enable **Permissions & Integration → Start local API** in the desktop app. Use the displayed port and an appropriate session token from an application on the same computer.

| Operation | Endpoint | JSON body |
| --- | --- | --- |
| Save a memory | `POST /v1/remember` | `{"title":"Project","content":"Demo Thursday at 14:00"}` |
| Search memories | `POST /v1/search` | `{"query":"When is the demo?"}` |

Requests use `Authorization: Bearer <session-token>` and `Content-Type: application/json`. Saving requires the full-access token; a read-only token can search. The API binds to `127.0.0.1`, is off by default and stops when the app closes. Port and tokens are session-specific.

Your application decides what to save, when to search and how to include retrieved records in the AI's context.

- [Python API example and setup](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/README.md#local-api-for-existing-ai-tools)
- [Optional Ollama integration](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/README.md#optional-local-ai)
- [ChatGPT save-and-recall bridge](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/chatgpt-bridge/README.md)
- [Source, local tests and self-check](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/README.md#running-from-source-python-311)

Use the **[current source](https://github.com/HingeZero/HingeZero-1B-Memory/tree/main/desktop)** for the updated save-and-recall bridge. It works with desktop v0.1.5 or later; the latest packaged release is linked above.

## Licensing and collaboration

The **desktop application** is source-available under [PolyForm Noncommercial 1.0.0](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/LICENSE.md), with its [Required Notice](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/NOTICE.txt). Permitted noncommercial use is free. Commercial use requires a separate written agreement; see [commercial licensing](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/COMMERCIAL-LICENSING.md).

These desktop terms do not relicense research files elsewhere in this repository.

**Created by David Duffy / HingeZero.** For technical collaboration or commercial licensing, contact David through the [established project contact](https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/desktop/COMMERCIAL-LICENSING.md#enquiring-about-commercial-terms).

## Billion-memory research

This repository also preserves the separate **C++20 one-billion-pattern reproducibility kit**, including the protocol, source, recorded results and reproduction scripts.

[Research report](HingeZero_Cpp20_1B_Report.md) · [Frozen protocol](SEALED_BENCHMARK.md) · [Recorded results](billion_results.csv) · [Original Python core](HingeZero_Core.py)

<details>
<summary>Read the full research overview, results and reproduction instructions</summary>

## HingeZero: One Billion Memories — C++20 Reproducibility Kit

**Research architecture:** David Duffy / HingeZero  
**Benchmark date:** 10 October 2026  
**Platform:** C++20, Linux x86-64 little-endian tested; standard library only for C++ engine  
**Repository contents:** source, verification scripts, frozen protocol and recorded outputs; **no 16 GB bank is included**.

### What the experiment actually did

The C++20 adaptation generated **1,000,000,000 deterministic bipolar 128-bit patterns**, occupying **16,000,000,000 bytes** (14.90 GiB). It created 900 million first, then appended 100 million. The SHA-256 digest of the *entire original prefix* remained unchanged.

Each query uses HingeZero's **eight-step dual-tanh refinement** (alpha 4.5, epsilon 0.10, lambda 0.02) with a fixed 256-pattern field. The implementation then computes a score for **every one of the one billion records** against that refined query using a streamed byte-lookup implementation of signed dot product. It has **no externally selected Hamming or nearest-neighbour shortlist**. It returns a tagged bank row and verifies exact stored-state membership and preservation.

It is a **packed binary specialization**, not a complete replacement of the original Python core. It is **not** a semantic-memory/clinical-care test, and it does not embed documents or conversational content.

### Reported results (original hardware/run)

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

### Quick start (~seconds; creates only 128 KiB plus append)

You need a C++20 compiler (`g++` 11+ tested using g++ 14), Python 3 for the smoke assertion, and bash.

```bash
git clone https://github.com/HingeZero/HingeZero-1B-Memory.git
cd HingeZero-1B-Memory
bash run_smoke.sh
```

This compiles C++, creates 8,192 memory rows, appends 256, compares the *original prefix SHA-256*, checks witnessed tagged state, then tests exact and 20%-corrupted retrieval. It prints **SMOKE TEST PASS** if all conditions succeed.

**Optional independent comparison to original Python core:** install NumPy and run `python3 parity_check.py` after compiling; this creates an 8,192-row bank if missing, then compares five native outputs to the unmodified `HingeZero_Core.py`. Running this script writes `parity_results.json` with the five numerical comparison results. For a basic internal-consistency check on the archived full-bank evidence, run `python3 verify_recorded_results.py`. This checks the recorded CSV's case count, witness flags and success count only; it does **not** verify JSON logs or replace an independent billion-record rerun.

### Full billion-memory reproduction

Requires **at least 16 GB of free disk** (more recommended), 64-bit system with little-endian binary storage, a few hundred MB free RAM for execution, and adequate time for 12 full-bank scans. **Use an output filename that does not yet exist:**

```bash
g++ -O3 -std=c++20 HingeZero_Native_1B.cpp -o hz_native
bash run_1b.sh /path/to/fast/disk/hz_1b_bank.bin
```

`run_1b.sh` writes `reproduced_1b_run.log` in the kit folder. It generates the bank with deterministic seed and ID mapping, verifies old-prefix hash after append, then executes the two targets across all six cue regimes. The 16 GB bank remains wherever you asked it to be written; delete it manually when finished.

Expected per-case selected indices and measurements from the original run appear in `billion_results.csv` and `HingeZero_Cpp20_1B_Report.md`. Compare your output against those files. Timing will vary. The reference bank prefix hash should match on the same little-endian representation.

### Files

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

### Limitations and provenance

The bank contains reproducible random binary patterns, not text or larger memory payloads. The witness verifies exact stored-state membership, **not whether the intended identity was selected**. This variant covers uniform evidence and a fixed field but not the complete Python retaining-loop, per-record metadata or permissions. The generated bank is intentionally absent to keep the public archive small.

Source is provided for inspection and reproducing these experiments; **no open-source licence is specified** in this package.

</details>


## Published benchmark: HingeZero 0-step vs Modern Hopfield (3 November 2026)

The reproducible [native CPU benchmark](benchmarks/hingezero0-vs-modern-hopfield-2026-11-03/README.md) compares **HingeZero zero-refinement Witness retrieval**, full one-step softmax Modern Hopfield, softmax-top1 indexing, and exact cosine on identical stored binary-pattern banks and noisy cues.

- 3,600 queries per method across 15 configurations, one CPU thread, compiled C++20.
- Zero-step HingeZero + Witness was approximately **2.1–2.3× faster than the complete one-step Modern Hopfield state update** in these implementations, with similar target-ID accuracy.
- **Witness verified all 3,600 returned stored-state identities**, independently of whether the intended memory was selected.
- Important control: zero-step HingeZero, exact cosine and MH softmax-top1 selected identical IDs in all queries; their speeds were comparable. No unique zero-step accuracy gain from the inactive HingeZero nonlinear refinement is claimed.
- [Source, full trial results, MH beta validation, and reproduction instructions](benchmarks/hingezero0-vs-modern-hopfield-2026-11-03/).

This benchmark concerns *stored-pattern-ID retrieval*, not neural semantic reasoning, an energy benchmark, or general computational superiority.
