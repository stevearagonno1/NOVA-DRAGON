import numpy as np,json,gzip,tempfile
from pathlib import Path
import volume_states90 as V
import research85 as R
import experiment90 as E
checks=0
for asset,d in R.fixture().items():
 a=V.states(d);b=V.states(d,True)
 for k in a:assert np.array_equal(a[k],b[k]),(asset,k);checks+=1
 for cut in [80,160,300]:
  z=V.states({k:v[:cut] for k,v in d.items()})
  for k in a:assert np.array_equal(z[k],a[k][:cut]),(asset,k,cut);checks+=1
# Persistence differs from a rising-edge pulse; zero volume remains false.
d={'c':np.arange(80,dtype=float)+100,'v':np.full(80,100.),'tbv':np.full(80,60.)}
s=V.states(d);assert s['TAKER_PRESSURE_1_0.56'][20:50].all()
assert E.combine(1<<30,R.pack(s['TAKER_PRESSURE_1_0.56']),'STATE_NOW',(1<<80)-1)==1<<30
assert not V.states({**d,'v':np.zeros(80),'tbv':np.zeros(80)})['TAKER_PRESSURE_1_0.52'].any()
with tempfile.TemporaryDirectory() as folder:
 p=Path(folder);E.run(p,True);E.run(p,True,True)
 saved=(p/'results.json').read_bytes();E.run(p,True);assert (p/'results.json').read_bytes()==saved
 raw=p/'raw.json.gz';original=gzip.decompress(raw.read_bytes());b=raw.read_bytes();raw.write_bytes(b[:9]+b'\x03'+b[10:]);E.run(p,True,True);assert gzip.decompress(raw.read_bytes())==original
 # Changed decompressed content must remain blocked.
 x=json.loads(original);x['assets']['BTCUSDT']['times'][0]='TAMPER';raw.write_bytes(gzip.compress(json.dumps(x).encode(),mtime=0))
 try:E.run(p,True,True)
 except AssertionError:pass
 else:raise AssertionError('raw tamper accepted')
print(json.dumps({'status':'PASS','primitive_scalar_and_prefix_checks':checks,'synthetic_only':True,'market_run':False,'rows':441,'pairs':405,'synthetic_null_counts':405*64*3,'gzip_header_compatibility':True,'raw_tamper_rejected':True}))
