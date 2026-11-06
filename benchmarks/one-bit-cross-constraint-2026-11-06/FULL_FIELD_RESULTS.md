# Full-field packed 1-bit HingeZero — independently logged experiment

**6 November 2026. Research; not a product or safety system.**

This supersedes the earlier Hamming-shortlisted proof of concept within this
directory. Hamming is an **isolated control**. In HZ0 and HZ8, all original
binary records are admitted directly to the original HingeZeroWitness's
associative field (180 fictional cases or 128 real FineWeb excerpts).
No ANN filter, Hamming shortlist, Hamming gate, or nearest-neighbour
preselection occurs in the HingeZero retrieval path.

## Storage vs arithmetic

- One stored vector is exactly **256 packed bits = 32 bytes**.
- The 180-pattern fictional bank is **5,760 bytes** of stored binary patterns.
- HingeZero's **unchanged dual-tanh formula** cannot itself be evaluated
  as purely one-bit arithmetic: the original Core expands the entire small
  bank into a temporary float32 workspace. This is one-bit **memory storage**,
  **not** a wholly binary compute pipeline or memory-only C++ accelerator.
- Original HingeZeroWitness supplies full-field 8-step refinement,
  all-pattern scoring and stored-state identity verification.
- The unrefined zero-step bipolar dot and Hamming have mathematically
  equivalent rankings, up to floating-point ties.
- Full-field Core uses at most 256 stored patterns because original
  `HZ_TOP = 256`. This experiment **does not** support 1B full-field
  attractor interactions, or claim that an O(PD) scan is scalable to 1B.

## Confirmed GitHub Actions results

[Successful full-field workflow](https://github.com/HingeZero/HingeZero-1B-Memory/actions/runs/42245296572).

**180 fictional deterministic cases** under identical cues:

| Bit flips | Hamming identity accuracy | Full HZ0 | Full HZ8 |
| --- | ---: | ---: | ---: |
| 0 | 100% | 100% | 100% |
| 32 | 100% | 100% | 100% |
| 64 | 100% | 100% | 100% |
| 96 | 97.78% | 97.78% | 97.78% |
| 128 | 0% | 0% | 0% |

For 96-bit flips all methods missed two of the 36 labelled conflicts. At
128-bit flips all 36 were **missed** and all 180 decisions were sent to
REVIEW. Zero unsafe ALLOW outputs in these fictional rules do **not** mean
all conflicts were detected. Witness verification passed for every stored
state selected by full-field HZ0/HZ8—even when the intended identity was
incorrect. That is the intended identity-only Witness behaviour.

Mean wall latency for 64-flipped-bit queries on the CI runner:
Hamming 0.1167 ms, full-field HZ0 0.1063 ms, full-field HZ8 0.4960 ms.
Python/numpy timings are implementation-specific; no universal speedup claim.

**128 authentic FineWeb webpage excerpts, 32 source-derived queries:**

| Query | Hamming ID R@1 | Full HZ0 | Full HZ8 |
| --- | ---: | ---: | ---: |
| Whole original excerpt | 100% | 100% | 100% |
| Contiguous 25-word fragment | 78.125% | 78.125% | 50% |

All unlabeled public documents were sent to REVIEW. HZ0/HZ8 Witness
verified 32/32 selected stored identities in each condition. This is
source-text identity retrieval, not semantic understanding, patient safety,
clinical decision-making, or proof of 1B-scale recall.

**Conclusion:** The original full-field eight-step HingeZero attractor
iteration **did not improve identity retrieval** in the measured conditions
and substantially degraded retrieval from partial real-document cues.
The cross-constraint rule masks are deterministic encodings of supplied
facts, not self-discovered truth. The next hypothesis to test is
**adaptive or evidence-constrained refinement**, compared against the
strong zero-step control and with nontrivial held-out relationships.

## Reproduce

From repository root after installing `numpy`:

```bash
python -m unittest discover -s benchmarks/one-bit-cross-constraint-2026-11-06 -p 'test_*.py' -v

OPENBLAS_NUM_THREADS=1 python benchmarks/one-bit-cross-constraint-2026-11-06/run_full_field.py \
  --records 180 --output full_field_results.json

OPENBLAS_NUM_THREADS=1 python benchmarks/one-bit-cross-constraint-2026-11-06/real_full_field.py \
  --records 128 --queries 32
```

The data are either fictional deterministic records or public authentic
FineWeb excerpts. The 32 queries are drawn directly from source documents;
no outside QA judgement is used. Real download requires network access.
