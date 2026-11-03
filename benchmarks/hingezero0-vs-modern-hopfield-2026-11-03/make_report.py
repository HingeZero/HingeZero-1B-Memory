from pathlib import Path
import csv,json
from collections import defaultdict
p=Path(__file__).resolve().parent
s=list(csv.DictReader((p/'summary.csv').open()))
m=json.loads((p/'manifest.json').read_text())
k={(int(x['n']),int(x['p']),round(float(x['noise']),2),x['method']):x for x in s}
def num(v):return f"{float(v):.1f}"
rows=[]
for n,P,noise in [(128,256,.20),(128,256,.35),(128,256,.40),(128,256,.45),
                  (128,1024,.20),(128,1024,.35),(128,1024,.40),(128,1024,.45),
                  (128,4096,.20),(128,4096,.35),(128,4096,.40),(128,4096,.45),
                  (256,1024,.20),(256,1024,.35),(256,1024,.40)]:
 hz=k[n,P,noise,'HZ_0_Witness']; mh=k[n,P,noise,'MH_1_softmax_full']; fast=k[n,P,noise,'MH_softmax_top1']
 ratio=float(mh['median_us'])/float(hz['median_us'])
 rows.append(f"| {n} | {P:,} | {noise:.0%} | {float(hz['accuracy'])*100:.1f}% | {float(mh['accuracy'])*100:.1f}% | {float(hz['median_us']):.1f} | {float(mh['median_us']):.1f} | {float(fast['median_us']):.1f} | {ratio:.2f}× |")

text=f'''# HingeZero 0-step + Witness vs Modern Hopfield — Native CPU Benchmark

**Date:** 3 November 2026  
**Status:** completed local test; **not published to GitHub**  
**CPU:** {m['cpu']}  
**Compiler:** {m['compiler']}  
**Build:** `{m['compile_options']}`  
**Execution:** one CPU thread; 3 seeds ({', '.join(map(str,m['seeds']))}), 80 fresh test queries per seed and condition. 15 configurations = **3,600 test queries per method**.  
**Original source:** `HingeZero_Core.py`, exact Git blob `{m['source_Git_blob']}` from HingeZero/HingeZero-1B-Memory.  

## What was actually compared

1. **HZ0+Witness:** Uses the original HingeZero Witness **zero-refinement ablation**: score all stored memory rows with cosine/dot, choose the highest-scoring row, return its **exact stored vector and ID**, verify exact tagged-row membership and preserve identity on repeat. No dual-tanh refinement, softmax, top-K prefilter or Hebbian matrix. The published Python core has 8 steps fixed, so the native comparator implements the equivalent zero-step selection using the reference `observe(query, scores=...)` route; its outputs were checked against that original source. This does **not** benchmark the original Python implementation's execution speed.
2. **MH1 full:** One-step Modern Hopfield operator `x_new = M.T @ softmax(beta * (M @ x))`, then a common closest-stored-pattern readout for exact target-ID accuracy. Beta calibrated on *different validation queries* with the same banks. The raw Modern Hopfield updated state is a weighted combination, not necessarily an exact stored pattern.
3. **MH softmax-top1 (optimized control):** Compute cosine scores and softmax weights, return the largest-weight stored ID without forming the new weighted state. This is **not a complete Modern Hopfield state update**; it is an optimized exact-pattern readout that fairly tests how much overhead the softmax itself introduces.
4. **Plain exact cosine:** Identical full-bank ranking, with no witness. This measures verification overhead relative to an optimised nearest-memory lookup.

Every method sees **the same float32 normalised bipolar pattern bank**, target IDs and corrupted queries for each condition. Bit flips are sampled with a fixed seed, no ground-truth labels passed to the retrieval algorithms. No GPU, threading or ANN/index prefilter. The final stored-pattern projection is shared by the full MH method only to make target-ID accuracy comparable. Training of semantic models was not tested.

## Main result

**HZ0+Witness had 3,600/3,600 identity-valid stored outputs, but correct-target retrieval varied with noise and bank size.**

**HZ0, plain cosine and MH softmax-top1 selected the same IDs on all 3,600 queries.** Therefore the 0-step results **do not show** an accuracy improvement from the HingeZero nonlinear operator, which is inactive at zero steps.

**HZ0 was roughly 2.1–2.3 times faster** than the *full one-step MH state update* in these native C++ paths. However the optimised MH softmax-top1 path was within a few percent of HZ0, demonstrating that most of the full-update timing difference comes from forming and re-scanning the blended state, rather than exponentiation alone. These are implementation-level results, not a general architecture or energy advantage.

### Complete results

Accuracy = **correct intended target ID**, not merely witness validity. Latency = median CPU time per query in microseconds (µs), measured with warmed-up native C++ and three repeated calls per query. Lower is better. The final column compares MH full update latency with HZ0+Witness latency.

| Dimension | Patterns | Bit flips | HZ0 accuracy | MH full accuracy | HZ0 µs | MH full µs | MH softmax-top1 µs | MH full/HZ speed ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
'''+'\n'.join(rows)+f'''

For 128-dimensional banks with 4,096 records and 35% corruption, HZ0 achieved 23.8% correct ID vs MH full's 25.0%. HZ0's median latency was 450.7 µs vs 994.7 µs for full MH, but 462.0 µs for MH softmax-top1. This makes the output requirements central to any speed comparison.

For 256 dimensions with 1,024 records at 40% corruption, HZ0 achieved 55.0% correct ID vs full MH's 56.7%. Neither difference should be presented as a statistically conclusive accuracy victory: these are 240 cases per condition and the score gaps are small.

### Witness and failed answers

The native HZ0 path checks a selected stored row's exact bytes and verifies preservation of its associated ID. The *original Python Witness source* is included and used for parity checks. **Witness validity is not truth verification**. At 128 dimensions, 4,096 patterns and 35% bit flips, Witness returned a valid stored record on all 240 queries while the intended target was recovered on only 57/240. These two quantities must never be conflated.

All 3,600 HZ0 returns passed the native witness check. The MH full method's **raw updated state** was not exactly any stored pattern in these conditions. After the same explicit stored-row projection for the accuracy task, its output ID always corresponded to a stored memory. This is a *choice of readout*, not a proof of spurious-attractor elimination in an unconstrained dynamical system.

### Source parity and precision

Exact reference source SHA-1 (Git blob): `{m['source_Git_blob']}`. Independent Python-vs-native sample checks used the original `HingeZeroWitness.observe(q, scores=...)` followed by its `verify()` method, with the refinement loop bypassed. {len(m['float32_tie_parity_differences'])} differing native-vs-NumPy selections occurred among 180 spot checks, all at mathematically tied similarities (absolute double-precision score difference < 1e-6). Native C++ uses deterministic earliest-row tie selection; NumPy's float32 BLAS can resolve mathematical ties differently. See `manifest.json` for the discrepancies. Comparisons among all native methods use precisely the same C++ dot-product scoring and tie handling.

### Memory usage

- **Common pattern bank:** `P * N * sizeof(float32)` for each method, e.g. 4,096 × 128 × 4 = **2.00 MiB**.
- **Native HZ0** needs the bank and an O(N) tagged-state buffer to check identity; the benchmark shares the input bank and uses a small copy during Witness verification.
- **Native MH full** needs the same pattern bank plus roughly `2*P+N` float32 scratch values (scores, softmax weights and blended state), **~32.5 KiB** extra for P=4,096, N=128.
- **Original Python HingeZeroWitness** retains additional copies of the raw and normalized memory arrays, candidate field arrays and evidence. It should not be compared to native MH's storage as if it were an optimized native HZ runtime. The benchmark's reported numbers are analytical buffer sizes, **not measured RSS or hardware cache traffic**.

### Reproduce

Requires Python 3 with NumPy, a C++20 compiler, and a CPU environment:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python run_benchmark.py
```

The command compiles `compare.cpp`, deterministically recreates pattern banks and queries, uses separate validation cues to tune MH's inverse temperature, checks sampled outcomes against the **original Python** HingeZero Witness (allowing only mathematically exact-score ties), and writes:

- `trials.csv`: all 14,400 method-query measurements and correct-target indicators.
- `summary.csv`: grouped accuracy, 95% Wilson binomial intervals, median/p95/mean latency, estimated serial QPS and Witness pass rate.
- `mh_beta_validation.csv`: held-out MH-beta tuning results.
- `manifest.json`: CPU/compiler, input settings, hash, tie discrepancies and caveats.

Original memory bank files are regenerated and removed; no records from real users are included. Native QPS estimated as 1e6 divided by mean measured per-query latency; it is not a sustained load-test measurement. Timings depend on machine, compiler, clock, cache and memory bandwidth. Results do not measure total energy or use equivalently optimized GPU kernels.

### Interpretation

The supported conclusion is narrower than "HingeZero solves all Modern Hopfield limitations". **Zero-step HingeZero with Witness is a highly direct, deterministic, no-softmax, integrity-verified memory-bank readout.** For this exact stored-ID task it is functionally equivalent to nearest cosine search and optimised MH softmax-index selection. The speed comparison against full MH shows a practical advantage of not performing a weighted-state update, but this advantage is not unique to HingeZero's nonlinear mathematics. If a downstream task requires blended associative states, direct HZ0 retrieval and MH's full update are different computations, and output utility must be evaluated independently.

### References

- HingeZero Witness Core: https://github.com/HingeZero/HingeZero-1B-Memory/blob/main/HingeZero_Core.py
- Ramsauer et al., *Hopfield Networks is All You Need*: https://arxiv.org/abs/2008.02217
- Published Modern Hopfield update equation: https://www.mdpi.com/2504-2289/10/3/71

**No files were uploaded or changed on GitHub.**
'''
(p/'README.md').write_text(text)
print('Wrote README',len(text),'chars')