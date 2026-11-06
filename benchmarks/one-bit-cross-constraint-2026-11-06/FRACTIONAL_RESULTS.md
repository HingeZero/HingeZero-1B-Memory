# Fractional-strength 1-bit HingeZero: real-data result

Date: 2026-11-06. **Research experiment; not yet a product improvement.**

## Question

Can *gentle* original HingeZero refinement updates improve the loss
observed at the stock eight full-strength iterations?

The original HingeZero core and Witness are unchanged. In this
experimental wrapper, the update gain `eta` multiplies both the original
lambda and epsilon terms, preserving the dual-tanh equation:

```
F(x) = W_field.T @ (tanh(W_field @ x) + alpha*tanh(2*(W_field @ x)))
       / (sum(abs(tanh(h) + alpha*tanh(2*h))) + 1e-12)

x_next = unit((1 - eta * lambda)*x + eta * eps*F(x))
```

Each update still counts as **one integer iteration**; `eta=0.001`
is one-thousandth strength per iteration, not 0.001 iterations.
`eta=1.0` for eight iterations matches the unchanged Core (regression
test checks parity). No Hamming preselection or Hamming scoring enters
the HingeZero paths; all 128 packed 256-bit stored patterns participate
in the full original Witness field. Floating point is used only as a
temporary associative computation workspace.

## Experiment

- 128 real FineWeb document excerpts, 256 packed bits / record.
- 64 source-derived target queries: 32 calibration and **32 held-out**.
- Each query has a 25-word, 12-word, and full-excerpt cue.
- **105 parameter configurations:** zero-step control, plus 26 update
  gains (0.001 to 0.020 inclusive in increments of 0.001; 0.025,
  0.05, 0.1, 0.2, 0.5, 1.0) times 1, 2, 4 or 8 iterations.
- Configuration selection uses **only calibration 25-word Recall@1**;
  tie breaker prefers fewer updates, avoiding extra compute with no gain.
  Held-out labels are never used to select the winning configuration.

## Actual held-out results (32 target queries)

| Condition | 25-word Recall@1 | 12-word Recall@1 | Full excerpt |
| --- | ---: | ---: | ---: |
| No refinement, 0 steps | 21/32 = 65.625% | 8/32 = 25% | 32/32 |
| `eta=0.001`, 1 step (best nonzero by calibration) | 21/32 = 65.625% | 9/32 = 28.125% | 32/32 |
| `eta=0.001`, 8 steps | 21/32 = 65.625% | 9/32 = 28.125% | 32/32 |
| `eta=0.002`, 8 steps | 21/32 = 65.625% | 9/32 = 28.125% | 32/32 |
| `eta=0.005`, 8 steps | 21/32 = 65.625% | 9/32 = 28.125% | 32/32 |
| `eta=0.010`, 8 steps | 21/32 = 65.625% | 9/32 = 28.125% | 32/32 |
| `eta=0.020`, 8 steps | 21/32 = 65.625% | 9/32 = 28.125% | 32/32 |
| `eta=0.050`, 8 steps | 21/32 = 65.625% | 9/32 = 28.125% | 32/32 |
| `eta=0.100`, 8 steps | 19/32 = 59.375% | 9/32 = 28.125% | 32/32 |
| `eta=0.200`, 8 steps | 19/32 = 59.375% | 8/32 = 25% | 32/32 |
| `eta=0.500`, 8 steps | 17/32 = 53.125% | 8/32 = 25% | 32/32 |
| Original `eta=1`, 8 steps | 16/32 = 50% | 6/32 = 18.75% | 32/32 |

**Selected configuration: 0 steps.** Its calibration 25-word
Recall@1 was 24/32 (75%); the strongest nonzero candidate tied but
requires additional computation. All 32 Witness state checks passed
for every displayed HingeZero configuration.

The one-case advantage (9/32 instead of 8/32) with a 12-word query is
a **hypothesis, not statistical evidence of a real advantage**. With
32 queries the result is highly sensitive to dataset choice. Full
excerpt recovery at 100% is an easy exact-cue control.

## Conclusion

Gentler updates **avoid the pronounced damage** of eight full-strength
updates. However, no nonzero update gain improved the held-out 25-word
Recall@1 over the zero-step baseline, and calibrating specifically for
this retrieval task selected zero refinement.

Avoid claiming small-step superiority, improved safety, or a 1-billion
full-field associative memory from this experiment. A future test
should use larger, independent datasets, multiple independent seeds,
independently annotated associations, and predeclared success metrics.
The algorithm remains a genuine packed 1-bit **storage** experiment
with float working-space arithmetic.

## Reproduce

```bash
python -m unittest discover \
  -s benchmarks/one-bit-cross-constraint-2026-11-06 -p 'test_*.py' -v
OPENBLAS_NUM_THREADS=1 python \
  benchmarks/one-bit-cross-constraint-2026-11-06/run_fractional.py \
  --records 128 --queries 64 --out fractional_results.json
```

The workflow publishes the entire 105-configuration JSON result as a
GitHub Actions artifact. [Successful GitHub workflow](https://github.com/HingeZero/HingeZero-1B-Memory/actions/runs/42246763297).
