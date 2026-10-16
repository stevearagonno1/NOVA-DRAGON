from pathlib import Path
import json,hashlib,os
root=Path(__file__).parent;want={f['sha'] for f in json.loads((root/'SOURCE-TREE.json').read_text())['tree'] if f['type']=='blob'};found={}
for d,dirs,files in os.walk(root.parent):
 dirs[:]=[x for x in dirs if x not in ['runtime','node_modules','__pycache__','.git','execution','pine_runtime']]
 for name in files:
  f=Path(d)/name
  if f.stat().st_size>100000000:continue
  b=f.read_bytes();sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
  if sha in want:found[sha]=str(f.resolve())
(root/'LOCAL-MATCHES.json').write_text(json.dumps(found))
print('Pinned blobs available locally:',len(found))
