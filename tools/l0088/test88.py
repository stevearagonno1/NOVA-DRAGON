from pathlib import Path
import json,sys,tempfile
import numpy as np
import signals88 as S
import research88 as M
inputs=Path(sys.argv[1]).resolve();sys.path.insert(0,str(inputs));import research85 as R
assert len(S.catalogue())==36 and len({q['family'] for q in S.catalogue()})==9
# Zero movement: all RSI denominators are zero, no false RSI/EMA/OBV crosses.
z=np.full(420,100.);d={'c':z,'h':z+1,'l':z-1,'o':z,'v':z,'tbv':z*.5}
a=S.primitives(d);b=S.primitives(d,True)
assert all(np.array_equal(a[k],b[k]) for k in a)
assert all(not a[q['id']].any() for q in S.catalogue() if q['family'] in ['RSI_RECLAIM','EMA_RECLAIM','OBV_EMA','MACD_REFERENCE'])
# Earliest alert wins; duplicate alerts remain false; events are disjoint.
ev=[{'onset':20},{'onset':50}];x={18,19,20,49,55};assert M.score(x,ev)==M.score_ref(x,ev);assert M.score(x,ev)[0]==M.metric(5,2,2)
# Zero denominators and confidence bound are retained.
assert M.metric(0,0,0)['precision']==0 and M.wilson(0,0)==0
with tempfile.TemporaryDirectory() as root:
 p=Path(root);M.execute(inputs,p,True);names=['raw.json.gz','results.json','asset_summary.json','shared_summary.json','alerts.json','selection.json','baselines.json','REPORT.md'];saved={n:(p/n).read_bytes() for n in names};M.execute(inputs,p,True);assert all((p/n).read_bytes()==b for n,b in saved.items())
 (p/'raw.json.gz').write_bytes(b'altered')
 try:M.execute(inputs,p,True)
 except AssertionError as e:assert 'changed raw' in str(e)
 else:raise AssertionError('tampering not caught')
print('TEST88_PASS: catalogue, scalar/prefix fixture, zero cases, matching, deterministic restart and tamper rejection')
