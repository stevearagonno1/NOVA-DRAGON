import tempfile,json,gzip
from pathlib import Path
import experiment89 as E
import research85 as R
# Ordered confirmation excludes same-bar and future conditions.
a=(1<<10);b=(1<<10)|(1<<11)|(1<<12);v=(1<<20)-1
for mode in ['S','AND0','AND2','PRICE_THEN_VOLUME2','VOLUME_THEN_PRICE2']:assert E.combine(a,b,mode,v)==E.combine(a,b,mode,v,True)
assert E.combine(a,1<<10,'PRICE_THEN_VOLUME2',v)==0
assert E.rotate((1<<5)|(1<<9),5,5,1)==(1<<5)|(1<<6)
with tempfile.TemporaryDirectory() as folder:
 p=Path(folder);E.run(p,True,stop_after=24);E.run(p,True);saved=(p/'results.json').read_bytes();E.run(p,True);assert (p/'results.json').read_bytes()==saved;E.run(p,True,True)
 f=next(p.glob('BTCUSDT-0.json.gz'));x=json.loads(gzip.decompress(f.read_bytes()));x['null_matched_by_period'][0][0]+=1;f.write_bytes(gzip.compress(json.dumps(x).encode()))
 try:E.run(p,True,True)
 except AssertionError:pass
 else:raise AssertionError('tamper not detected')
import subprocess,sys
subprocess.run([sys.executable,str(Path(__file__).parent/'test_transport89.py')],check=True)
print('TEST89_PASS: modes, wrap, checkpoint restart, scalar null audit and tamper')
