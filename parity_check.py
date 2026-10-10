import sys, subprocess, json
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent
sys.path.insert(0, str(root))
from HingeZero_Core import HingeZeroWitness
bank_path=root/'test_bank_8192.bin'
if not (root/'hz_native').is_file():
 subprocess.run(['g++','-O3','-std=c++20',str(root/'HingeZero_Native_1B.cpp'),'-o',str(root/'hz_native')],check=True)
if not bank_path.is_file():
 subprocess.run([str(root/'hz_native'),'create',str(bank_path),'8192'],check=True)
p=np.fromfile(bank_path,dtype='<u8').reshape(-1,2)
bytes_view=p.view(np.uint8).reshape(-1,16)
bits=np.unpackbits(bytes_view,axis=1,bitorder='little').astype(np.float32)
raw=2*bits-1
bank=raw/np.linalg.norm(raw,axis=1,keepdims=True)
obj=HingeZeroWitness(raw,np.zeros(len(raw),np.float32))
executable=str(root/'hz_native')
results=[]
for target,regime in [(417,'flip20'),(20,'flip35'),(417,'missing50'),(20,'exact'),(1337,'severe')]:
 MASK=2**64-1
 def splitmix(s):
  s=(s+0x9E3779B97F4A7C15)&MASK;z=s
  z=((z^(z>>30))*0xBF58476D1CE4E5B9)&MASK
  z=((z^(z>>27))*0x94D049BB133111EB)&MASK
  return s, z^(z>>31)
 seed=(0x176e2eadcafe5315^target^0xba5ed)&MASK
 ids=list(range(128))
 for j in range(127,0,-1):
  seed,r=splitmix(seed); a=r%(j+1);ids[j],ids[a]=ids[a],ids[j]
 cue=bank[target].copy()
 if regime.startswith('flip'):
  for j in ids[:26 if regime=='flip20' else 45]:cue[j]*=-1
 if regime=='missing50':cue[ids[:64]]=0
 if regime=='severe':
  cue[ids[32:]]=0
  for j in ids[:6]:cue[j]*=-1
 norm=np.linalg.norm(cue)
 if norm: cue/=norm
 ours=json.loads(subprocess.check_output([executable,'parity',str(bank_path),'8192',str(target),regime]))['refined']
 native=json.loads(subprocess.check_output([executable,'test',str(bank_path),'8192',str(target),regime]))
 q=obj.refine(cue)
 scores=obj.memories@q
 expected=int(np.argmax(scores))
 results.append({'target':target,'regime':regime,'python_selected':expected,'cpp_selected':native['selected'],'max_abs_refine_error':float(np.max(np.abs(np.array(ours)-q))),'witness':native['witness']})
print(json.dumps(results,indent=2))
assert all(r['python_selected']==r['cpp_selected'] for r in results)
assert max(r['max_abs_refine_error'] for r in results)<0.00005
(root/'parity_results.json').write_text(json.dumps(results,indent=2))
