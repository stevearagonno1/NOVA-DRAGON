from pathlib import Path
import hashlib,json,urllib.request,time,concurrent.futures,collections
R=Path(__file__).parent;meta=json.loads((R/'remote.json').read_text());HEAD=meta['fixed_head'];BASE='history/research/hyp_lab_out/L0084-entry-mix-r1';RUN='stage1-singletons-v1'
rows=[r for r in meta['tree']['tree'] if r['type']=='blob' and (('/run='+RUN+'/') in r['path'] or r['path'].startswith(BASE+'/inputs/') or r['path']==BASE+'/storage_journal.jsonl')];cache=R/'blobs';cache.mkdir(exist_ok=True)
def get(row):
 p=cache/row['sha']
 if p.exists():b=p.read_bytes()
 else:
  for attempt in range(3):
   try:
    with urllib.request.urlopen('https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+HEAD+'/'+row['path'],timeout=45) as f:b=f.read()
    break
   except Exception:
    if attempt==2:raise
    time.sleep(2*(attempt+1))
  if hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=row['sha']:raise RuntimeError('Git blob mismatch '+row['path'])
  p.write_bytes(b)
 assert len(b)==row['size']
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['sha']
 return {'path':row['path'],'git_blob_sha':row['sha'],'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
result=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for item in pool.map(get,rows):
  result.append(item)
  if len(result)%50==0:print('VERIFIED',len(result),'/',len(rows),flush=True)
(R/'download_manifest.json').write_text(json.dumps({'head':HEAD,'files':result,'bytes':sum(x['bytes'] for x in result)},indent=2));print('ALL_DOWNLOADED_VERIFIED',len(result),sum(x['bytes'] for x in result))
