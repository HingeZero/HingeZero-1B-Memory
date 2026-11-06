# Evidence-anchored 1-bit associative memory — measured findings

**Research experiment, 6 November 2026. Not production software or a clinical/safety decision engine.**

## Research question

Can an associative system use distinct observations to identify its intended
stored attractor **before** reinforcing one, and can David Duffy's HingeZero
dual-tanh activation outperform matched ordinary-tanh or unrefined methods?

### Implementation and attribution

- Actual memory storage: each of 128 authentic source-document records is a
  **256-bit (32-byte) packed 1-bit code**. Original HingeZero Core's full
  field includes **all 128 patterns**; **no Hamming or ANN preselection**.
- The original `HingeZero_Core.py` file is **unchanged**. Eight ungated dual
  updates pass parity checks against original `HingeZeroWitness.refine()`.
- Proposed **NEW architecture**: two cue vectors `a,b` independently
  produce full-bank scores `sa=M@a`, `sb=M@b`. Candidate-specific support
  weights `w_i ~ max(sa_i,0)*max(sb_i,0)` are calculated **without any
  target ID or answer labels**. The nonlinear field multiplies individual
  responses by `w_i` to suppress candidates not supported by both cues.
  That is a **modified field operator**, not a result for the original Core
  alone. A matched **ordinary-tanh** operator gets exactly the same weights,
  lambda, epsilon, iteration count, readout and Witness.
- All modes use the same post-readout two-cue agreement gate. A later,
  explicitly **exploratory**, stricter version requires both cues'
  standalone top-1 records to agree **before running refinement**; any
  disagreement causes immediate REVIEW, with no further state updates.
- Selected HingeZero Witness verifies that the chosen binary-backed record
  is an actual retained state. It does **not** verify that the chosen
  record is the intended one or that a statement is objectively true.
- The 1-bit pattern bank is physically binary, but the dual-tanh arithmetic
  expands it into a temporary float32 workspace. No billion-scale claim.

## Experimental data

- **Real:** 128 genuine FineWeb public webpage excerpts (no invented
  documents); 64 selected target pages per condition.
- Each correct paired query consists of **two non-overlapping 25-word or
  12-word fragments from the SAME page**. This is two pieces of information,
  **not independent sources** or independently verified corroboration.
- Contradictory paired queries combine a fragment from page A with a fragment
  from a **different page B**. An incorrect 'ACCEPT' here means the system
  treated mutually different source identities as an acceptable pair.
- **Synthetic control:** 96 packed bipolar memories, correlated families,
  independently flipped noisy cues at 48/80/96 bits, 3 random seeds, plus
  intentionally different-identity second cues.
- Labels and source identities are used **only for scoring**, not passed to
  `EvidenceAnchoredAttractors.decide()`.
- The initial evidence rule (`topk=5`) was fixed before results; the
  stricter `top-1` agreement rule was introduced **after the first real-data
  measurement revealed conflicting-pair false acceptance**, so it is
  **exploratory**, not independently held-out model selection.

[Successful GitHub Actions run](https://github.com/HingeZero/HingeZero-1B-Memory/actions/runs/42257718413). Eleven regression tests passed.

## Original two-cue experiment — raw identity accuracy

| Original document recovered | One cue / 0 steps | Two cues / 0 steps | Two cues / gated HZ dual-tanh |
| --- | ---: | ---: | ---: |
| 25-word source fragments | 55/64 = 85.94% | **63/64 = 98.44%** | 62/64 = 96.88% |
| 12-word source fragments | 36/64 = 56.25% | **49/64 = 76.56%** | 48/64 = 75.00% |

**The improvement comes from using more source information.** The gated
HingeZero refinement did **not** improve raw record-identity recovery
beyond simple two-cue fusion.

## The decision gate trades coverage against mistaken acceptance

`ACCEPT` below is **only a document-identity agreement signal**, not a
permission to perform any clinical or industrial action.

| Real-source condition | Two-cue 0-step with top-5 agreement | Two-cue dual-tanh with top-5 agreement |
| --- | ---: | ---: |
| Genuine 25-word pair: correct ACCEPT | **55/64** | **55/64** |
| Genuine 25-word pair: wrong ACCEPT | 0/64 | 1/64 |
| **Different-page 25-word pair: false ACCEPT** | **8/64** | **12/64** |
| Genuine 12-word pair: correct ACCEPT | **32/64** | 30/64 |
| Genuine 12-word pair: wrong ACCEPT | 2/64 | 3/64 |
| **Different-page 12-word pair: false ACCEPT** | **5/64** | **8/64** |

The matched **ordinary-tanh** gated operator produced exactly the same
25-word correct-ACCEPT count and conflicting-pair false-ACCEPT count
as gated dual-tanh (55 and 12 respectively). The predeclared
dual-tanh-specific improvement condition **FAILED**.

## Exploratory strict pre-refinement gate

Hard hold if the two independent cues select different initial top-1
stored identities. If they agree, all candidates still participate in
the field, but final ACCEPT is permitted only if the selected memory
is the common preflight anchor.

| Real-source condition | Strict 0-step | Strict HingeZero dual |
| --- | ---: | ---: |
| Genuine 25-word pair: correct ACCEPT | **41/64** | **41/64** |
| Different-page 25-word pair: false ACCEPT | **0/64** | **0/64** |
| Genuine 12-word pair: correct ACCEPT | **14/64** | **14/64** |
| Different-page 12-word pair: false ACCEPT | **0/64** | **0/64** |

The stricter gate eliminated false acceptance for **these 64 different-page
cases per cue length**, but cut genuine coverage substantially. It was not
demonstrated to generalise to other sources, noisy sensors, correlated
webpages or adversarial data. In the *separately generated* correlated
96-record synthetic fixture at 80 bit flips, all three seeds (288 genuine
pairs) were accepted correctly and all 288 deliberately mixed pairs
were held by the same strict gate. These artificial patterns are not
external validation.

### No free "correct attractor detector"

If the two observations do not contain enough information to distinguish
their underlying source, the system cannot discover their true identity
from geometry alone. Witness is an exact stored-state integrity check,
not a truth oracle. A system that sends everything to REVIEW avoids false
ACCEPT but is also unusable; **coverage is an essential metric**.

## Reproduce

Research branch includes the original dual-tanh isolation files from
the unmerged parent draft PR #11, against which this experiment is
stacked. After checking out the new branch:

```bash
python -m pip install 'numpy==2.3.5'
OPENBLAS_NUM_THREADS=1 python -m unittest discover \
  -s benchmarks/evidence-anchored-attractors-2026-11-06 -p 'test_*.py' -v
OPENBLAS_NUM_THREADS=1 python \
  benchmarks/evidence-anchored-attractors-2026-11-06/run_benchmark.py \
  --records 128 --queries 64 --seeds 3 \
  --output evidence_anchored_attractor_results.json
```

The workflow uploads complete per-mode source-cohort summaries, including
correct record recovery, true/false ACCEPT counts, REVIEW counts, preflight
holds, Witness checks, coverage and latency. Public dataset-server access
is required to fetch original FineWeb source records.

**Conclusion:** independent *views* of evidence can substantially help
retrieval, and conservative preflight disagreement checks can prevent
some premature reinforcement. **Neither the improvement nor the hold
behaviour was unique to HingeZero.** Ordinary tanh matched dual-tanh,
and zero-step fusion outperformed refinement in record recovery.
The original dual-tanh's special advantage remains unproven.
