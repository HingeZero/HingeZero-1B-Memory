# Why HingeZero's second tanh does not currently improve 1-bit retrieval

**Date:** 6 November 2026. **Status:** tested in GitHub Actions, exploratory research, not a production-core change.

## Question and mathematical isolation

The original David Duffy HingeZero Core defines

```python
phi(h) = tanh(h) + 4.5*tanh(2*h)
field = M.T @ phi(h)
field /= sum(abs(phi(h))) + 1e-12
x = unit((1 - 0.02)*x + 0.1*field)
```

with eight updates. The original Core was **not modified**.

The second tanh saturates faster. At `h=0.1` vs `h=0.8`, weak-to-strong activation ratios are approximately:

- plain `tanh(h)`: **0.15009**
- dual-tanh with `alpha=0.25`: **0.16660**
- original dual-tanh with `alpha=4.5`: **0.20531**

Thus the second term **increases the relative strength of weak competing matches** at these activations; it is not a guaranteed selective return to the original memory.

The scalar `sum(abs(phi(h)))` denominator removes the common gain of all responses but does **not** change their relative ratios. Changing a single positive scalar denominator can alter overall update size and subsequent dynamics, **not fix the relative weak/strong weighting at that step**.

For small inputs,
`phi(h) ~= (1+2*alpha)*h - (1+8*alpha)*h**3/3 + ...`.
With `alpha=4.5`, this becomes `10*h - (37/3)*h**3 + ...`.
The original L1 normalisation largely cancels the common linear factor `10`, explaining why the dual-tanh field can behave similarly to ordinary tanh when most activations are small.

## Reproducible matched ablation

[Full CI run and logs](https://github.com/HingeZero/HingeZero-1B-Memory/actions/runs/42251691683).

Files:
- `normalization.py`: original dual tanh, plain tanh, and alpha=.25.
- `run_normalization.py`: the **same banks and queries for all conditions**.
- `test_normalization.py`: exact parity with the unchanged original Core for its L1 configuration, scalar-invariant activation-ratio proof, and genuine packed-bit assertions.

**19 configurations:** zero-step control plus 3 activations × 3 denominators × 2 response-shape powers. Eight updates per nonlinear configuration, same lambda/epsilon and same Witness, full 1-bit field with **no Hamming candidate filter**.

Denominators tested:
1. `l1_original`: original `sum(abs(response))`.
2. `l2_scaled`: `sqrt(number_of_patterns) * ||response||_2`.
3. `fixed_response_bound`: `number_of_patterns * max_activation_magnitude`. This reduces update strength at low activation; it is **not the original normaliser**.

Power 1 is the unchanged activation response. Power 2 is an **experimental, sign-preserving shape modification**, *not* the original HingeZero equation or a purely scalar-normalisation change. It was applied to tanh controls too.

Storage is physical packed 1-bit (**256 bits = 32 bytes per record**); the nonlinear computation uses an ephemeral full float workspace and the original `HingeZeroWitness`. This is **not** all-binary computation or 1-billion-pattern attractor testing.

## Real documents

128 authentic FineWeb webpage excerpts, 48 source-derived identity queries in each condition. Accuracy is **correct document identity**, not semantic understanding or a safety decision.

| Method | 25-word fragment | 12-word fragment |
| --- | ---: | ---: |
| No refinement | **40/48 = 83.3%** | 27/48 = 56.3% |
| Plain tanh, original L1 | 37/48 = 77.1% | 25/48 = 52.1% |
| HingeZero alpha=4.5, original L1 | 37/48 = 77.1% | 25/48 = 52.1% |
| Plain tanh, L2-scaled | 37/48 = 77.1% | 26/48 = 54.2% |
| HingeZero alpha=4.5, L2-scaled | 37/48 = 77.1% | 26/48 = 54.2% |
| Plain tanh, fixed bound | 38/48 = 79.2% | **28/48 = 58.3%** |
| HingeZero alpha=4.5, fixed bound | 38/48 = 79.2% | **28/48 = 58.3%** |
| Plain tanh, original L1 + response power 2 | 37/48 = 77.1% | 26/48 = 54.2% |
| HingeZero alpha=4.5, original L1 + response power 2 | 37/48 = 77.1% | 26/48 = 54.2% |

The matched activation families (`tanh`, `dual025`, `dual45`) returned the **same number of correct identities under each matched normalisation/shape setting** on the two real-text probes. Where a change improved recall, **ordinary tanh improved equally**. The best 12-word result was only 1/48 better than zero refinement, and the same setting was 2/48 worse on 25-word queries.

At original L1 strength, both plain tanh and HingeZero rescued 1 previously wrong 25-word query but **damaged 4 previously correct ones**, and rescued 1/damaged 3 among 12-word queries. All selected states passed original Witness identity verification—even wrong targets.

## Correlated packed-1bit controls

2 correlation levels (0.5, 0.8), noise 80/96/112 flipped bits, 3 independently seeded banks of 96 memories, 288 queries per scenario, **1,728 paired synthetic queries overall**. This supplements authentic FineWeb identity retrieval but is **not** real-language reasoning.

All matched tanh and dual-tanh methods had the same final accuracy under original L1, with both successes and failures. Fixed-denominator and sharpened-response variants had small mixed changes (sometimes positive, sometimes negative). No condition showed a robust, dual-tanh-specific retrieval improvement against the plain-tanh control. The predeclared >=3-percentage-point broad advantage criterion for the original dual-tanh method **failed**.

## Conclusion

**The equation is implemented correctly.** The current field response and L1 normalisation do not make the second tanh selectively anchor the correct attractor. A scalar denominator can tune how strongly the state moves, but it cannot suppress competing weak responses *relative* to strong ones. The measured improvements from reduced update gain were **not unique to HingeZero**.

The dual-tanh specific associative-retrieval advantage remains **unproven** here. Further optimising alpha or normalisation on these same small probes would risk overfitting. Any new selective weighting, attraction gate or evidence-aware memory dynamics should be declared a **new architectural hypothesis**, with held-out evaluation and a plain-tanh comparator.

## Reproduce

```bash
OPENBLAS_NUM_THREADS=1 python -m unittest discover \
  -s benchmarks/dual-tanh-isolation-2026-11-06 -p 'test_*.py' -v

OPENBLAS_NUM_THREADS=1 python \
  benchmarks/dual-tanh-isolation-2026-11-06/run_normalization.py \
  --seeds 3 --real-records 128 --real-queries 48 \
  --output dual_tanh_normalization_results.json
```

Results include all 19 configurations, source digest, matched plain-tanh controls, zero-step baselines, Witness checks, rescues/damages and measured timings. GitHub Actions attaches the full JSON as an artifact.
