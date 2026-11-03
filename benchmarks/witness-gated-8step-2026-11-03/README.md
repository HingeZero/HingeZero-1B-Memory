# HingeZero Witness — Evidence-Gated Decisions (0–8 Steps)

**Author:** David Duffy / HingeZero  
**Date:** 3 November 2026  
**Status:** Local synthetic test completed; reproducible code and measured summary published. **Not an independently validated truth detector or production safety system.**

## Purpose

Test a concrete decision rule built **around the original HingeZero Witness**, without changing its nonlinear mathematics:

1. Check a proposed stored-memory match at **0 refinement steps**.
2. Require exact stored-state identity (original Witness `observe` / `verify`).
3. Require at least **two distinct supplied supporting source IDs**, **no recorded contradiction**, cosine similarity **≥0.60**, and top-1/top-2 similarity gap **≥0.10**.
4. **ACCEPT** immediately if all gates pass. If source evidence is absent, contradictory, or Witness verification fails, return **HUMAN_REVIEW** immediately; no extra refinement can manufacture missing evidence.
5. If retrieval alone is uncertain, use the **original HingeZero Witness one-step update** iteratively, stopping at the first passing result or after **at most eight steps**.
6. After eight steps without meeting all requirements, return **HUMAN_REVIEW** with **no selected ID or executable action**.

`HUMAN_REVIEW` is a structured handoff signal only. This experiment does **not** implement a human ticket queue, external notification, or physical-action controller.

## Source and protocol

- Original reference code: [HingeZero_Core.py](../../HingeZero_Core.py), original **Git blob `ec0ec9c56c233b97038d88618ad9f2bcff26bcab`**.
- Decision layer: [decision_gate.py](decision_gate.py). Uses the original `HingeZeroWitness`, `hinge_phi`, constants and float32 update; original source **not modified**.
- Reproduction test: [run_benchmark.py](run_benchmark.py).
- [Summary of measured outcomes](summary.csv) and [manifest / edge cases](manifest.json).
- Running the test generates `trials.csv` (2,000 method-query rows), `summary.csv` and `manifest.json` on your machine. The complete raw trial file is generated on reproduction, not committed here.

**Environment:** Python 3.10+, NumPy. One NumPy RNG seed `20261103`, 64 random bipolar memories of dimension 128, 100 queries at each of 0%, 20%, 30%, and 40% randomly flipped bits. All candidates in supported scenarios have two **simulated** source IDs. The actual independent reliability of those sources is **not** tested.

**Run:**

```bash
python -m pip install numpy
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python benchmarks/witness-gated-8step-2026-11-03/run_benchmark.py
```

## Results

Each row shows accepted/correct selections out of **100 queries** at that corruption level. A held query is **not** counted as a correct retrieval.

| Method | 0% flips | 20% flips | 30% flips | 40% flips |
| --- | ---: | ---: | ---: | ---: |
| Plain cosine top-1, always answer | 100/100 | 100/100 | 100/100 | **44/100** (56 wrong) |
| Gated HingeZero + Witness, **0 steps** | 100/100 | **0 accepted** | 0 accepted | 0 accepted |
| Gated HingeZero + Witness, **up to 8 steps** | 100/100 | **100/100** | 0 accepted | 0 accepted |
| Gated + **no support IDs** | 0 accepted | 0 accepted | 0 accepted | 0 accepted |
| Gated + **contradiction IDs** | 0 accepted | 0 accepted | 0 accepted | 0 accepted |

**Refinement on 20% flips:** The base top-1 cosine selector **already identified the correct memory** on all 100 queries. The zero-step **gate** held the result because 20% corruption put its cosine similarity just below the preset 0.60 threshold. The HingeZero update raised similarity enough to pass the gate, with mean **1.63 steps** and maximum **2 steps**. Thus, **this is not a demonstration of HingeZero correcting wrong top-1 IDs**; it demonstrates threshold-crossing and bounded acceptance under the selected artificial conditions.

**At 30% flips:** Plain top-1 was correct on all 100 test queries, while the conservative gate withheld all 100, even after eight steps. The gate trades coverage for caution. **At 40% flips:** plain top-1 made 56 wrong forced selections; the gate withheld all 100. This does **not** establish how it performs across other seeds, distributions, memory counts, or tuned thresholds.

### Explicit safety/limitation checks

| Input | Result | Steps |
| --- | --- | ---: |
| Exact cue with supplied support IDs | ACCEPT | 0 |
| Missing or non-finite cue | HUMAN_REVIEW | 0 |
| No support IDs | HUMAN_REVIEW | 0 |
| Contradictory source IDs | HUMAN_REVIEW | 0 |
| Duplicate support ID presented twice | HUMAN_REVIEW | 0 |
| Mixed ambiguous cue | HUMAN_REVIEW | 8 |
| Two arbitrary, **unverified** source ID strings | **ACCEPT** | 0 |

**Critical limitation:** The gate checks only the presence/uniqueness of **user-supplied IDs**, not whether their underlying claims are accurate, independent, trustworthy, or even real. The last test deliberately shows arbitrary IDs can pass. Therefore **it is not a truth/lie detector**; trustworthy external provenance checking would be required in a production design.

### What this demonstrates — and does not

**Demonstrated locally:** a bounded 0–8-step decision policy that uses the actual Witness identity check, avoids accepting decisions in explicitly unsupported or contradicted synthetic scenarios, exits early when evidence is missing, and provides a machine-readable abstention/human-review outcome. The eight-step floating-point update agrees exactly with the original `HingeZeroWitness.refine` in an explicit parity check.

**Not demonstrated:** a mathematically optimal eight-step limit, discovery of objective truth, independent evidence authentication, freedom from false positives across other data, elimination of Hopfield spurious attractors, superiority over equivalently gated classical or Modern Hopfield baselines, or real-world safety.

**Thresholds (0.60 similarity, 0.10 margin, 2 source IDs) are illustrative test settings, not independently calibrated operating values.** Re-test and calibrate them with real workloads before relying on the decision gate. This is an opt-in experimental wrapper, not a change to the original HingeZero Core, the Witness memory, or the desktop application's runtime behaviour.

## File index

- [decision_gate.py](decision_gate.py) — new gate; max eight original HingeZero updates.
- [run_benchmark.py](run_benchmark.py) — seeded synthetic experiment, controls, parity and safety assertions.
- [summary.csv](summary.csv) — committed aggregate outcomes.
- [manifest.json](manifest.json) — parameters and observed edge-case results.
- `trials.csv` — recreated by running the script (not checked in).

**David Duffy / HingeZero — reproducible research for external examination.**
