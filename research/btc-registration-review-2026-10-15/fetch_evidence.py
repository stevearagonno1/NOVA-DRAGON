import concurrent.futures,hashlib,json,time,urllib.request,urllib.parse
from pathlib import Path
P=Path(__file__).parent;plan=json.loads((P/'review-plan.json').read_text());root=P/'remote';root.mkdir(exist_ok=True)
files=dict(plan['publication']['published_file_sha256']);base='research/btc-registration-from-repo-2026-10-15/executor/'
files[base+'PUBLICATION_PLAN.json']=hashlib.sha256(plan['exact_text']['PUBLICATION_PLAN.json'].encode()).hexdigest()
assert len(files)==40
def get(item):
 path,expected=item;assert path.startswith(base) or path=='LOG.md' or path=='docs/journal/2026-10-15-btc-registration-from-repo/002-existing-run-published.md'
 dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():
  assert hashlib.sha256(dest.read_bytes()).hexdigest()==expected
  return {'path':path,'sha256':expected,'bytes':dest.stat().st_size,'cached':True}
 urls=['https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+plan['commit']+'/'+path,'https://api.github.com/repos/stevearagonno1/NOVA-DRAGON/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+plan['commit']]
 errors=[]
 for url in urls:
  try:
   req=urllib.request.Request(url,headers={'Accept':'application/vnd.github.raw+json','User-Agent':'NOVA-independent-review'})
   with urllib.request.urlopen(req,timeout=25) as r:content=r.read(25000001)
   if content[:1]==b'{' and not path.endswith('.json'):
    try:
     import base64
     obj=json.loads(content)
     if obj.get('encoding')=='base64':content=base64.b64decode(obj['content'])
    except (ValueError,KeyError):pass
   assert hashlib.sha256(content).hexdigest()==expected,'Publication SHA mismatch'
   dest.write_bytes(content);assert sum(f.stat().st_size for f in P.rglob('*') if f.is_file())<=125000000
   return {'path':path,'sha256':expected,'bytes':len(content),'url':url}
  except Exception as e:errors.append(str(e))
 raise RuntimeError(path+' '+str(errors))
started=time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(get,files.items()))
(P/'download-audit.json').write_text(json.dumps({'status':'PASS_40_IMMUTABLE_PUBLICATION_HASHES','commit':plan['commit'],'files':results,'total_bytes':sum(r['bytes'] for r in results),'seconds':time.time()-started},indent=2)+'\n')
print(json.dumps({'status':'PASS_40_IMMUTABLE_PUBLICATION_HASHES','files':len(results),'bytes':sum(r['bytes'] for r in results),'seconds':time.time()-started}))
