# HingeZero Native C++20 — One Billion Stored Memories

**Executed 10 October 2026** | **HingeZero architecture: David Duffy** | **Implementation: C++20 packed binary bank**

## Executive result

A C++20 packed binary adaptation of the HingeZero witnessed-associative-memory architecture **stored one billion 128-dimensional bipolar memories and scored every record on every retrieval query directly from the HingeZero-refined query**. No external Hamming shortlist selected the answers.

- **Physical storage:** 1,000,000,000 records x 16 bytes = 16,000,000,000 bytes (14.901 GiB).
- **Append test:** created 900,000,000 memories and appended 100,000,000 more. The SHA-256 digest of the entire original 14.4-billion-byte prefix was exactly unchanged.
- **Original records preserved after append:** SHA-256 `0ab2870c17c77733d6645ae11187f794786dd7bf05eabe970b36f70ec27847bc` before and after.
- **Correct target IDs:** 8 / 12 across two old targets and six pre-registered cue regimes.
- **Witness verification:** 12 / 12 selections passed exact tagged-row verification and preservation-on-repeat.
- **Native full-bank search:** median 7.046 seconds per standalone query across the 12 samples (range 6.829–7.714 s).
- **Dual-tanh refinement:** median 0.243 ms. This does not include the bank-wide scan.

## Accuracy by fixed cue regime

| Cue condition | Original memories correctly recovered (out of two) |
|---|---:|
| Exact complete cue | 2/2 |
| 20% bits flipped (26/128) | 2/2 |
| 35% bits flipped (45/128) | 0/2 |
| Half the coordinates missing | 2/2 |
| One severely damaged cue (75% missing, six flipped visible positions) | 0/2 |
| Four independent severely damaged cues combined | 2/2 |

The two old records tested were IDs 417 and 777,777,777, selected before the billion-bank run. The full bank contained one billion records during every retrieval condition. These are two examples per regime, not a statistical population estimate.

## Native algorithm and fidelity

The engine uses HingeZero's original core constants: alpha 4.5, epsilon 0.1, lambda 0.02 and eight refinement steps. The fixed associative field contains the first 256 stored patterns (uniform zero evidence). It then streams **all 1,000,000,000** bipolar stored memories and computes cosine/dot scores against the **refined continuous state**. The maximum-scoring stored row is returned as its exact tagged identity and checked by the witness. A bytewise precomputed signed dot-product lookup accelerates scoring without excluding any row. This **replaces the data representation and computation backend**, not the decision rule, for the binary test bank.

Independent smaller-bank parity checks against the original Python `HingeZero_Core.py` produced **5/5 identical selected identities** and a maximum absolute difference of 5.98e-08 across corresponding refined vector coordinates. These checks support numeric equivalence for the specific tested cases and data representation.

## Technical conclusion

**A native HingeZero-compatible C++20 pipeline completed a full-bank observation over one billion stored bipolar patterns, with witness verification of all returned stored states.** The append operation preserved every byte of the original 900-million-record bank. Exact, moderate corruption, 50%-missing and four-cue regimes recovered both tested old identities; more severe single-cue damage failed for both. The result establishes functioning end-to-end native HingeZero refined scoring at this scale, at the measured latency of approximately seven seconds per query on this machine.

**Scope:** This build supports fixed 128-bit bipolar memories and zero evidence. It does not implement the general float32 memory bank, complete dynamic evidence selection, full original retaining-loop API or metadata/record-authorisation layers. Existing mathematical witness properties are implemented through exact tagged membership and a preservation branch; correct intended identity remains a separately measured outcome. A different indexed implementation and sub-second full-bank retrieval were not tested.

## Reproducibility record

- `HingeZero_Native_1B.cpp`: complete self-contained C++20 source.
- `SEALED_BENCHMARK.md`: frozen protocol written before the 1B run.
- `billion_run_log.txt`: timestamped generation, append, SHA-256 verification and twelve measured retrieval lines.
- `billion_results.csv` and `.json`: actual per-condition identifiers and times.
- `parity_check.py`, `parity_results.json` and `HingeZero_Core.py`: source-equivalence verification.
- The 16 GB temporary memory-bank file is **not** packaged; `run_1b.sh` recreates it deterministically from the fixed integer seed.
