# HingeZero Cross-Constraint Attractor Grid — genuine 1-bit prototype

**Research prototype, 6 November 2026. Not a clinical, industrial, or emergency safety system.**

This experiment answers a focused question: does adding HingeZero's genuine
eight-step dual-tanh refinement and stored-state Witness verification improve a
deterministic *packed 1-bit* candidate retrieval and explicit constraint gate,
compared with (1) binary retrieval + rules and (2) HingeZero 0-step + rules?

## Actual architecture

1. **Low-level 1-bit bank:** each code occupies **256 bits / 32 bytes** as
   actual packed `bytes`. An encoder builds a signed random token sketch and
   discards its temporary vote counters. Candidate generation scans the full
   binary bank using XOR plus `int.bit_count()` (**Hamming distance**). The
   bank does **not** store float32 embeddings. It is not a semantic encoder.
2. **High-level unchanged HingeZero:** only the nearest 32 binary candidates
   are unpacked to bipolar float32 values. `HingeZeroWitness` from the
   repository's **unchanged original `HingeZero_Core.py`** is used:
   - baseline: binary nearest candidate, no HingeZero nor Witness;
   - HZ0: original Witness, zero refinement;
   - HZ8: original Witness and all **eight** dual-tanh steps.
   This stage adds **no new memories** and never claims the float shortlist is
   still stored as one-bit. The float workspace is temporary.
3. **Explicit 1-bit geometric constraint gate:** every known fictional
   action/condition pair maps to a stable, packed **256-bit rule wall**.
   The validated typed "clear" Boolean is encoded as the matching wall
   (Hamming distance **0**). A typed contradictory Boolean is encoded as
   its exact complement (Hamming distance **256**) and returns **BLOCK**.
   Each retrieved record has a subject, action, named rule input and
   a caller-supplied `provenance_ok` assertion. Wrong subject/action,
   unknown or missing rules, untrusted claims and malformed evidence return
   **REVIEW**, never ALLOW. The complementary mask is *constructed from*
   the typed input—it does not discover contradictions by itself.

**Key correction:** exact bitwise opposite codes have Hamming distance 256,
not destructive interference. HingeZero Witness verifies *stored identity*,
**not** rule truth; `BLOCK` is decided by the explicit rules. The simulated
source assertion is not a cryptographic signature.

## Reproduce

From repository root, with `numpy` installed:

```bash
python -m unittest discover -s benchmarks/one-bit-cross-constraint-2026-11-06 -p 'test_*.py' -v
python benchmarks/one-bit-cross-constraint-2026-11-06/run_benchmark.py \
  --records 180 \
  --output one_bit_cross_constraint_results.json
```

The benchmark runs **identical cases and identical corrupted bit cues** for
the three modes, with 0, 32, 64, 96 and 128 flipped bits, recording:

- Exact record-identity recovery, final decision accuracy, conflict BLOCK recall
- Missed BLOCK count, false BLOCK count, unsafe ALLOW count, REVIEW/abstention
- Witness checks, mean/median/p95 **single-core-process** wall latency
- Confusion tables per corruption rate and memory use

For clean and bit-corrupted cues, the action/evidence flag lives in the **record
metadata**; the cue does not contain the conflict flag. All cases are
**fictional, deterministic, labelled by the same rule engine** (there is no
independent clinical truth set). In this baseline, each correct cue starts as an
exact binary match before controlled bit flips. This tests controlled bit
corruption, **not** language understanding, real medical data, device accuracy,
paraphrased questions, or a one-billion-record implementation.

A perfect clean-result score would primarily reflect exact-match retrieval and
a shared rule table, not a novel learned safety capability. `BLOCK` missed
because of wrong retrieval becomes `REVIEW` (fail-closed) but still counts as a
**missed detected conflict**. Merely returning REVIEW for everything is **not**
considered success.

The benchmark code is deterministic, audit-friendly, and intentionally separate
from the desktop release and from the 1B real-memory benchmark.

## Genuine web-text retrieval control

The same packed one-bit encoder and zero/eight-step Core can also be probed
against **128 actual FineWeb webpage excerpts**, using 24 documents as held-out
query targets. The script downloads public source records from the official
FineWeb dataset-server API and reports the original-source digest.

```bash
python benchmarks/one-bit-cross-constraint-2026-11-06/real_text_probe.py \
  --records 128 --queries 24
```

It separately tests exact original-excerpt cues and a contiguous 25-word
fragment taken from that same document. Only **document identity recovery**
is scored, not factual contradictions. Every public web document is labelled
REVIEW, as no validated rule or fact accompanies the page.

These genuine documents are **not** used to construct plausible fictional
safety decisions. Real text does not supply independently adjudicated safety
conflict labels, so the two benchmarks are deliberately separate.

## Future tests

Use independently labelled, independently sourced evidence and calibrate
typed rules against domain experts. Compare against an indexed exact rule
engine, and test document semantics, contradictory evidence from multiple
sources, stale timestamps, spoofed provenance, false correlations, memory
updating, energy/CPU cost, and corrupt or missing sensory measurements. For
safety-critical applications, keep human oversight and require a domain-specific
safety assurance case; do not deploy these fictional rules.
