#!/usr/bin/env python3
"""Reproducible native CPU 0-step HingeZero Witness vs Modern Hopfield.

Python prepares inputs and tunes MH beta on independent validation cues.
C++20 measures 4 paths with identical float32 banks and queries. Uses
original Python HingeZeroWitness to verify native zero-step readout parity.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import platform
from pathlib import Path
import struct
import subprocess
import sys
from collections import defaultdict
from time import monotonic

import numpy as np
from HingeZero_Core import HingeZeroWitness, HingeZeroState, _unit

HERE = Path(__file__).resolve().parent
DATA = HERE / 'inputs'
SEEDS = (2026, 2027, 2028)
NOISES = (.20, .35, .40, .45)
PATTERN_COUNTS = (256, 1024, 4096)
DIM = 128
TRIALS = 80
VALIDATION = 24
BETAS = (8., 16., 32., 64., 128., 256.)
# An extra higher-dimensional sanity check (same corruption levels).
CONDITIONS = [(DIM, p, n) for p in PATTERN_COUNTS for n in NOISES] + [
    (256, 1024, n) for n in (.20, .35, .40)
]
METHODS = ('HZ_0_Witness', 'MH_1_softmax_full', 'MH_softmax_top1', 'Exact_cosine')


def make_bank(n, p, seed):
    rng = np.random.default_rng(900000 + seed + 7 * n + 101 * p)
    # Generate bipolar patterns; unit-norm their rows using reference HZ _unit.
    raw = rng.choice([-1., 1.], size=(p, n)).astype(np.float32)
    return np.ascontiguousarray(_unit(raw), dtype=np.float32)


def make_queries(bank, noise, seed, qty, offset):
    rng = np.random.default_rng(seed + 11 * bank.shape[0] + 41 * bank.shape[1] +
                                int(noise * 1000) * 100003 + offset)
    ids = rng.integers(0, len(bank), size=qty)
    q = np.array(bank[ids], copy=True)
    flipped = int(round(bank.shape[1] * noise))
    for row in q:
        bits = rng.choice(bank.shape[1], size=flipped, replace=False)
        row[bits] *= -1
    return np.ascontiguousarray(_unit(q), dtype=np.float32), ids.astype(np.int32)


def choose_beta(case_banks, noise):
    # Validation queries are sampled separately from test (offset 10 vs 100).
    performance = {}
    for beta in BETAS:
        success, total = 0, 0
        for seed, bank in case_banks:
            val, wanted = make_queries(bank, noise, seed, VALIDATION, 10)
            # Native and Python both use normalized patterns and query vectors.
            sims = val @ bank.T
            logits = beta * (sims - sims.max(axis=1, keepdims=True))
            weights = np.exp(logits).astype(np.float32)
            weights /= weights.sum(axis=1, keepdims=True)
            updated = weights @ bank
            selected = np.argmax(updated @ bank.T, axis=1)
            success += int(np.sum(selected == wanted))
            total += len(wanted)
        performance[beta] = success / total
    best = max(performance.values())
    chosen = min(beta for beta, score in performance.items() if score == best)
    return chosen, performance


def check_reference_parity(bank, cues):
    # Exact source from published HingeZero_Core.py. No refinement:
    # calling observe with explicit cosine scores skips its refine() loop.
    original = HingeZeroWitness(bank, np.zeros(len(bank), dtype=np.float32))
    got = []
    for cue in cues:
        explicit_scores = original.memories @ _unit(cue)
        state = original.observe(cue, scores=explicit_scores)
        assert original.verify(state)
        assert np.array_equal(state.state, original.memories[state.candidate_index])
        got.append(state.candidate_index)
    return np.asarray(got, dtype=np.int32)


def write_case(path, bank, queries, targets, *, beta, seed, noise):
    # Layout matches C++ Header (4 x uint32, float32, uint32, float32)
    with path.open('wb') as f:
        f.write(struct.pack('<IIIIfIf', 0x485a4d48, bank.shape[1], len(bank),
                            len(queries), beta, seed, noise))
        f.write(bank.astype('<f4', copy=False).tobytes(order='C'))
        f.write(queries.astype('<f4', copy=False).tobytes(order='C'))
        f.write(targets.astype('<i4', copy=False).tobytes(order='C'))


def wilson(k, n):
    if not n: return (0,0)
    z = 1.96
    ph = k / n
    d = 1 + z*z/n
    ctr = (ph + z*z/(2*n))/d
    half = z*np.sqrt((ph*(1-ph) + z*z/(4*n))/n)/d
    return (round(float(max(0, ctr-half)), 5), round(float(min(1,ctr+half)), 5))


def main():
    tic = monotonic()
    DATA.mkdir(exist_ok=True)
    src = (HERE / 'HingeZero_Core.py').read_bytes()
    ghblob = hashlib.sha1(b'blob '+str(len(src)).encode()+b'\0'+src).hexdigest()
    assert ghblob == 'ec0ec9c56c233b97038d88618ad9f2bcff26bcab', ghblob
    subprocess.run(['g++','-O3','-std=c++20','-ffp-contract=off','-Wall','-Wextra',
                    str(HERE / 'compare.cpp'),'-o',str(HERE / 'compare')],check=True)
    trials, choices, ties = [], [], []
    for n,p,noise in CONDITIONS:
        banks = [(seed, make_bank(n,p,seed)) for seed in SEEDS]
        beta, validation = choose_beta(banks, noise)
        choices.append({'n':n,'p':p,'noise':noise,'beta':beta,
                        **{f'validation_beta_{int(k)}':round(v,5) for k,v in validation.items()}})
        print(f'run N={n} P={p} bit-flips={noise:.0%} MH beta={beta}', flush=True)
        for seed,bank in banks:
            queries,targets = make_queries(bank,noise,seed,TRIALS,100)
            path = DATA/f'N{n}_P{p}_noise{int(noise*100)}_seed{seed}.bin'
            write_case(path,bank,queries,targets,beta=beta,seed=seed,noise=noise)
            proc=subprocess.run([str(HERE / 'compare'),str(path)],text=True,
                                capture_output=True,check=True)
            rows = [x for x in csv.reader(proc.stdout.splitlines()) if x]
            assert len(rows)==TRIALS*len(METHODS)
            if seed==SEEDS[0]:
                parity = check_reference_parity(bank,queries[:min(12,TRIALS)])
                native_hz = [int(row[8]) for row in rows if int(row[7])==0 and int(row[5])<len(parity)]
                for i,(ref_id,native_id) in enumerate(zip(parity,native_hz)):
                    if ref_id != native_id:
                        # With bipolar memory and heavy bit flips, multiple bank
                        # rows can have exactly equal cosine similarity. NumPy
                        # float32 BLAS and native float32/double may break these
                        # ties differently; require them to be genuinely tied.
                        q = queries[i]
                        a = float(np.dot(bank[ref_id].astype(np.float64),q.astype(np.float64)))
                        b = float(np.dot(bank[native_id].astype(np.float64),q.astype(np.float64)))
                        if not abs(a-b) < 1e-6:
                            raise AssertionError((n,p,noise,i,ref_id,native_id,a,b))
                        ties.append({'n':n,'p':p,'noise':noise,'seed':seed,'query':i,
                                     'python_selection':int(ref_id),'native_selection':int(native_id),
                                     'score_difference_double':a-b})
            for row in rows:
                d={'n':int(row[0]),'p':int(row[1]),'seed':int(row[2]),
                   'noise':float(row[3]),'beta':float(row[4]),'trial':int(row[5]),
                   'target':int(row[6]),'method':METHODS[int(row[7])],
                   'selected':int(row[8]),'correct':int(row[9]),
                   'witness_pass':int(row[10]),'natural_stored':int(row[11]),
                   'latency_us':float(row[12]),'target_cosine':float(row[13])}
                trials.append(d)
            path.unlink() # datasets reproducible from seeds; do not archive bulky banks
    if DATA.exists() and not list(DATA.iterdir()):DATA.rmdir()
    bygroup=defaultdict(list)
    for r in trials:bygroup[(r['n'],r['p'],round(r['noise'],2),r['method'])].append(r)
    summary=[]
    for (n,p,noise,method),rs in sorted(bygroup.items()):
        arr=np.asarray([r['latency_us'] for r in rs]);k=sum(r['correct'] for r in rs)
        summary.append({'n':n,'p':p,'noise':noise,'method':method,'trials':len(rs),
                        'hits':k,'accuracy':round(k/len(rs),5),'wilson95':wilson(k,len(rs)),
                        'median_us':round(float(np.median(arr)),3),
                        'mean_us':round(float(np.mean(arr)),3),
                        'p95_us':round(float(np.percentile(arr,95)),3),
                        'qps_per_thread':round(float(1e6/np.mean(arr)),1),
                        'witness_pass_rate':round(float(np.mean([r['witness_pass'] for r in rs if r['witness_pass']>=0])),5) if method=='HZ_0_Witness' else None,
                        'raw_output_exact_pattern_rate':round(float(np.mean([r['natural_stored'] for r in rs])),5)})
    with (HERE/'trials.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(trials[0].keys()));w.writeheader();w.writerows(trials)
    with (HERE/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0].keys()));w.writeheader();w.writerows(summary)
    with (HERE/'mh_beta_validation.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(choices[0].keys()));w.writeheader();w.writerows(choices)
    def cpu_model():
        try:
            return next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
        except (OSError,StopIteration):return platform.processor()
    meta={'test_date':'2026-11-03', 'version':'CPU zero-refinement matched comparison v1',
          'numpy':np.__version__,'python':sys.version.split()[0],
          'cpu':cpu_model(),'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
          'compile_options':'g++ -O3 -std=c++20 -ffp-contract=off -Wall -Wextra',
          'one_thread_env':{k:os.getenv(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')},
          'source_Git_blob':ghblob,'float32_tie_parity_differences':ties,'N_P_noise':CONDITIONS,'seeds':SEEDS,'test_queries_per_seed':TRIALS,
          'MH_validation_queries_per_seed':VALIDATION,'MH_betas':BETAS,
          'notes':['0-step HZ uses full-bank normalized dot/cosine selection and verifies exact tagged stored row (no tanh performed).',
                   'The full modern Hopfield update is M.T @ softmax(beta * M @ query), followed by stored-pattern nearest readout.',
                   'The MH softmax-top1 baseline reports argmax of softmax weights; it does NOT perform a full modern Hopfield updated-state readout.',
                   'Original HingeZeroWitness source is supplied unchanged and checked by exact Git blob SHA; parity checks use original observe(scores=...) and verify.',
                   'C++ native code uses a faithful zero-refinement observer and integrity branch, not the original Python runtime.',
                   'Benchmark includes implementation overhead; no energy measurement; no guarantee of broader performance or storage equivalence.',
                   'MH beta tuned on distinct validation query set. Same stored-pattern banks and test cues across methods.',
                   'Timing is for a single query, native C++, using median of three repeated executions per query, warmed up.',
                   'Memory storage: both methods share P x N x float32 pattern bank; original Python Witness additionally copies raw and normalized arrays and field state.'],
          'elapsed_s':round(monotonic()-tic,2)}
    (HERE/'manifest.json').write_text(json.dumps(meta,indent=2))
    print('\nRESULTS',flush=True)
    for s in summary:print(s,flush=True)
    print('total seconds',round(monotonic()-tic,2),flush=True)

if __name__=='__main__':main()