from pathlib import Path
import sys,gzip,shutil,json
source=Path(sys.argv[1]).resolve(); evidence=Path(sys.argv[2]).resolve(); output=Path(sys.argv[3]).resolve()
assert not output.exists(), 'use a new audit directory'
output.mkdir(parents=True)
for p in evidence.iterdir():
 if p.is_file() and not p.name.startswith('audited-'): shutil.copy2(p,output/p.name)
sys.path.insert(0,str(source));import experiment89 as E
assert gzip.decompress((evidence/'raw.json.gz').read_bytes())==json.dumps(E.raw(False),sort_keys=True).encode()
original=gzip.compress; header=(evidence/'raw.json.gz').read_bytes()[9]
def canonical(data,*args,**kwargs):
 b=original(data,*args,**kwargs);return b[:9]+bytes([header])+b[10:]
gzip.compress=canonical
E.run(output,False,True)
