"""Production source/preflight/complete package upload and immutable byte readback."""
from pathlib import Path
import base64,json,hashlib,tempfile,zipfile
import publish89 as P
ROOT=Path(__file__).parent;files={};commits={};blobs={};ref={};counter=0
for p in ROOT.iterdir():
 if p.is_file():files['tools/l0089/'+p.name]=p.read_bytes()
files['LOG.md']=b'fixture only\n'
commits['base']=dict(files)
def api(path,method='GET',body=None):
 global counter,files
 if path.startswith('/git/ref/heads/'):
  if P.BRANCH not in ref:raise RuntimeError('HTTP 404')
  return {'object':{'sha':ref[P.BRANCH]}}
 if path.startswith('/contents/'):
  name,commit=path[len('/contents/'):].split('?ref=');return {'encoding':'base64','content':base64.b64encode(commits[commit][name]).decode()}
 if path.startswith('/git/commits/') and method=='GET':return {'tree':{'sha':'base'}}
 if path=='/git/blobs':
  b=base64.b64decode(body['content']);h=P.blob_sha(b);blobs[h]=b;return {'sha':h}
 if path.startswith('/git/blobs/'):
  h=path.rsplit('/',1)[1]
  if h not in blobs:
   b=next(b for snapshot in commits.values() for b in snapshot.values() if P.blob_sha(b)==h)
  else:b=blobs[h]
  return {'content':base64.b64encode(b).decode()}
 if path=='/git/trees':
  snapshot=dict(commits.get(ref.get(P.BRANCH),commits['base']))
  for x in body['tree']:snapshot[x['path']]=blobs[x['sha']] if 'sha' in x else x['content'].encode()
  counter+=1;key='tree'+str(counter);commits[key]=snapshot;return {'sha':key}
 if path=='/git/commits':
  counter+=1;key='commit'+str(counter);commits[key]=commits[body['tree']];return {'sha':key}
 if path=='/git/refs' or path.startswith('/git/refs/heads/'):
  ref[P.BRANCH]=body['sha'];return {}
 raise AssertionError(path)
P.api=api
head=P.ensure_source(ROOT,'fixture-package');assert P.ensure_source(ROOT,'fixture-package')==head
# Existing real transport is unchanged; this tests current path names and payload.
ref[P.BRANCH]=head
try:P.preflight(ROOT,'fixture-package')
except KeyError:
 # Missing fixture proof is modelled as a404, as real API does.
 original=api
 def wrapped(path,method='GET',body=None):
  try:return original(path,method,body)
  except KeyError:raise RuntimeError('HTTP 404') from None
 P.api=wrapped
 P.preflight(ROOT,'fixture-package')
with tempfile.TemporaryDirectory() as d:
 root=Path(d);out=root/'market';out.mkdir();(out/'audit.json').write_text(json.dumps({'status':'PASS'}));(out/'delivery.json').write_text(json.dumps({'synthetic':False,'rows':360,'status':'DISCOVERY_COMPLETE_LEAD_REVIEW_PENDING'}));(out/'REPORT.md').write_text('fixture only');(out/'selection.json').write_text('{}')
 # Publisher retains filename selection87 from old route: current explicit mapping below.
 head,receipt=P.complete(ROOT,out,'fixture-package');assert receipt['rows']==360
 assert (root/'L0089-evidence.zip').stat().st_size==receipt['archive_bytes']
print('TRANSPORT89_PASS: prepared source, preflight, complete archive, paths and byte readback; in-memory transport fixture')
