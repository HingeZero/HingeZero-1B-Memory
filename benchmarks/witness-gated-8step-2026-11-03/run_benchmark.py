"""Deterministic, synthetic evidence-gate test; no human truth judgments.
Usage from repo root: python benchmarks/witness-gated-8step-2026-11-03/run_benchmark.py
"""
import csv
import json
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from HingeZero_Core import HingeZeroWitness, HZ_STEPS, _unit
from decision_gate import Evidence, EvidenceGatedWitness

SEED = 20261103
PATTERNS = 64
DIMENSIONS = 128
TESTS_PER_CONDITION = 100
MAX_STEPS = 8
FLIPS = (0.0, 0.20, 0.30, 0.40)


def run():
    rng = np.random.default_rng(SEED)
    bank = rng.choice([-1.0, 1.0], size=(PATTERNS, DIMENSIONS)).astype(np.float32)
    witness = HingeZeroWitness(bank, np.zeros(PATTERNS, dtype=np.float32))
    # All candidates have independently supplied (simulated) positive attestations.
    # These are not verified by the gate; this is NOT a real truth benchmark.
    supported = [Evidence((f'source_A_for_{i}', f'source_B_for_{i}')) for i in range(PATTERNS)]
    absent = [Evidence() for _ in range(PATTERNS)]
    conflicted = [Evidence((f'A_{i}', f'B_{i}'), (f'dispute_{i}',)) for i in range(PATTERNS)]
    configs = {
        'GATED_MAX_8': EvidenceGatedWitness(witness, supported, max_steps=8),
        'GATED_MAX_0': EvidenceGatedWitness(witness, supported, max_steps=0),
        'NO_SOURCES_8': EvidenceGatedWitness(witness, absent, max_steps=8),
        'CONTRADICTION_8': EvidenceGatedWitness(witness, conflicted, max_steps=8),
    }
    records = []
    for noise in FLIPS:
        for trial in range(TESTS_PER_CONDITION):
            target = int(rng.integers(PATTERNS))
            cue = bank[target].copy()
            flipped = rng.choice(DIMENSIONS, size=round(noise * DIMENSIONS), replace=False)
            cue[flipped] *= -1
            # Plain cosine nearest neighbour baseline: no gate, no witness checks.
            plain_id = int(np.argmax(witness.memories @ _unit(cue)))
            records.append({'condition':'PLAIN_TOP1', 'noise':noise,'trial':trial,
                            'truth_id':target,'selected_id':plain_id,'correct':int(plain_id==target),
                            'accepted':1,'steps':0,'reason':'no_gate','witness_valid':''})
            for name, gate in configs.items():
                result = gate.decide(cue)
                records.append({'condition':name,'noise':noise,'trial':trial,
                                'truth_id':target,'selected_id':result.candidate_id if result.candidate_id is not None else '',
                                'correct':int(result.candidate_id == target) if result.status == 'ACCEPT' else '',
                                'accepted':int(result.status == 'ACCEPT'),'steps':result.steps,
                                'reason':result.reason,'witness_valid':int(result.witness_valid)})
    # Deterministic safety test vectors.
    safety = {}
    for label, cue, gate in [
        ('zero_cue', np.zeros(DIMENSIONS, np.float32), configs['GATED_MAX_8']),
        ('nan_cue', np.full(DIMENSIONS, np.nan, np.float32), configs['GATED_MAX_8']),
        ('missing_sources', bank[0], configs['NO_SOURCES_8']),
        ('contradictory_sources', bank[0], configs['CONTRADICTION_8']),
        ('exact_supported', bank[0], configs['GATED_MAX_8']),
        ('ambiguous_midpoint', _unit(witness.memories[0] + witness.memories[1]), configs['GATED_MAX_8']),
        ('duplicate_support_ids', bank[0], EvidenceGatedWitness(witness, [Evidence(('same', 'same')) for _ in range(PATTERNS)])),
        ('unverified_source_ids', bank[0], EvidenceGatedWitness(witness, [Evidence(('any_string_1', 'any_string_2')) for _ in range(PATTERNS)])),
    ]:
        d=gate.decide(cue)
        safety[label]=d.to_dict()
    assert safety['zero_cue']['status']=='HUMAN_REVIEW'
    assert safety['nan_cue']['status']=='HUMAN_REVIEW'
    assert safety['missing_sources']['status']=='HUMAN_REVIEW'
    assert safety['contradictory_sources']['status']=='HUMAN_REVIEW'
    assert safety['exact_supported']['status']=='ACCEPT' and safety['exact_supported']['steps']==0
    assert safety['ambiguous_midpoint']['status']=='HUMAN_REVIEW', safety['ambiguous_midpoint']
    assert safety['duplicate_support_ids']['status']=='HUMAN_REVIEW'
    assert safety['unverified_source_ids']['status']=='ACCEPT'  # Important limitation: strings are not authenticated.
    assert all(int(r['steps'])<=8 for r in records)
    assert all(r['selected_id']=='' for r in records if r['condition']!='PLAIN_TOP1' and not r['accepted'])
    # Verify the one-step arithmetic agrees with original refine at eight steps.
    def eight_steps_in_wrapper(q):
        x=_unit(q)
        from HingeZero_Core import HZ_ALPHA,HZ_EPS,HZ_LAMBDA,hinge_phi
        for _ in range(HZ_STEPS):
            response=hinge_phi(witness.field_memories@x,HZ_ALPHA)
            field=witness.field_memories.T@response
            field/=float(np.sum(np.abs(response)))+1e-12
            x=_unit((1-HZ_LAMBDA)*x+HZ_EPS*field)
        return x
    checkcue=_unit(bank[0]+0.5*bank[1])
    assert np.array_equal(witness.refine(checkcue),eight_steps_in_wrapper(checkcue))
    # Early support, negative evidence and abstention behavior.
    assert all(r['steps']==0 for r in records if r['condition']=='NO_SOURCES_8')
    assert all(r['steps']==0 for r in records if r['condition']=='CONTRADICTION_8')
    # Summary grouped by scenario & noise.
    groups=defaultdict(list)
    for r in records:
        groups[(r['condition'],r['noise'])].append(r)
    rows=[]
    for (condition,noise),data in sorted(groups.items()):
        accepted=[r for r in data if r['accepted']]
        correct=sum(int(r['correct']) for r in accepted)
        wrong=len(accepted)-correct
        rows.append({'condition':condition,'bit_flip_fraction':noise,'queries':len(data),
                     'accepted':len(accepted),'human_review':len(data)-len(accepted),
                     'correct_accepted':correct,'wrong_accepted':wrong,
                     'accepted_precision':round(correct/len(accepted),4) if accepted else '',
                     'average_steps':round(sum(int(r['steps']) for r in data)/len(data),3),
                     'max_steps':max(int(r['steps']) for r in data)})
    assert (sum(r['accepted'] for r in records if r['condition']=='GATED_MAX_8' and r['noise']==0.20) >
            sum(r['accepted'] for r in records if r['condition']=='GATED_MAX_0' and r['noise']==0.20))
    with (HERE/'trials.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    with (HERE/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    manifest={
        'title':'HingeZero Witness evidence-gated decision demonstration',
        'date':'2026-11-03','seed':SEED,'patterns':PATTERNS,'dimensions':DIMENSIONS,
        'trials_per_noise':TESTS_PER_CONDITION,'bit_flip_fractions':FLIPS,
        'max_steps':MAX_STEPS,'original_core_git_blob':'ec0ec9c56c233b97038d88618ad9f2bcff26bcab',
        'configured_thresholds':{'min_similarity':0.60,'min_margin':0.10,'min_distinct_support_ids':2},
        'evidence_note':'Synthetic per-candidate source IDs; no real-world provenance, truth, or authenticity verification. Every candidate is labeled supported in supported scenarios. A deliberate unverified-source test shows that arbitrary IDs can pass without external validation.',
        'safety_checks':safety,'core_parity_exact':True,
        'questions_answered':'Fail-closed hold, eight-step cap, early zero-step accept, use of real Witness checks, comparative selective-retrieval outcomes.',
        'questions_not_answered':'Whether the gate detects truth, independence of source claims, safety in real deployments, novel Hopfield capacity improvement, energy or production latency.'
    }
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print('Safety checks:',json.dumps({k:(v['status'],v['steps'],v['reason']) for k,v in safety.items()},indent=2))
    print('\nSUMMARY')
    for row in rows: print(row)
    print('\nPASS: source parity, 8-step bound, zero-step acceptance, mandatory human review on missing/contradictory evidence or ambiguity, and unverified-source limitation.')

if __name__=='__main__':
    run()
