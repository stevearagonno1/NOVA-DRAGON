"""Offline publication contract test, synthetic evidence only; no GitHub credential."""
import base64,csv,gzip,hashlib,json,tempfile
from pathlib import Path
import publish_existing as p
def write(root,name,obj):
 path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj));return path
class Mock:
 def __init__(self):self.head=None;self.blobs={'old-log':b'Prior immutable log\n'};self.commits={p.SOURCE:{'sha':p.SOURCE,'tree':{'sha':'base-tree'}}};self.trees={};self.n=0;self.methods=[]
 def ref(self):
  if self.head is None:raise RuntimeError('HTTP404')
  return self.head
 def call(self,method,path,data=None):
  self.methods.append((method,path));assert '/pulls' not in path and '/merges' not in path and not path.endswith('/heads/main')
  if path.endswith('/'+p.REPO):return {'permissions':{'push':True}}
  if '/git/commits/' in path and method=='GET':return self.commits[path.rsplit('/',1)[-1]]
  if path.endswith('/git/refs') and method=='POST':self.head=data['sha'];return {}
  if method=='PATCH':self.head=data['sha'];return {}
  if path.endswith('/git/blobs'):
   b=base64.b64decode(data['content']);h=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();self.blobs[h]=b;return {'sha':h}
  if '/git/blobs/' in path:return {'content':base64.b64encode(self.blobs[path.rsplit('/',1)[-1]]).decode()}
  if '/git/trees/' in path:return {'tree':[{'path':'LOG.md','sha':'old-log'}]}
  if path.endswith('/git/trees'):self.n+=1;h=f'tree{self.n}';self.trees[h]=data;return {'sha':h}
  if path.endswith('/git/commits'):self.n+=1;h=f'commit{self.n}';self.commits[h]={'sha':h,'tree':{'sha':data['tree']}};return {'sha':h}
  raise RuntimeError((method,path))
root=Path(__file__).parent/'synthetic-existing-run';e=root/'execution';e.mkdir(parents=True,exist_ok=True);fixed={'source_sha256_by_month':{},'task_id':'synthetic'}
manifest={'counts':p.COUNTS,'sources':[],'frame_sha256':{}}
for n in p.COUNTS:
 f=e/f'data/frames/BTCUSDT-{n}m.csv.gz';f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b'fixture-'+n.encode());manifest['frame_sha256'][n]=p.sha(f)
for month in p.MONTHS:
 f=e/f'data/raw/BTCUSDT-1m-{month}.zip';f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(('synthetic source '+month).encode());h=p.sha(f);f.with_suffix('.zip.CHECKSUM').write_text(h+' '+f.name);fixed['source_sha256_by_month'][month]=h;manifest['sources'].append({'month':month,'source_sha256':h})
write(e,'data/manifest.json',manifest);resolved=dict(fixed,input_manifest_sha256=p.sha(e/'data/manifest.json'),frame_sha256=manifest['frame_sha256']);write(e,'protocol.json',resolved);write(e,'result/frozen-protocol.json',resolved)
split_sizes={'discovery':262080,'historical_validation':131040,'historical_reserve':132480};splits={k:{'feature_anchor_rows':n,'eligible_all_9_windows':n-240} for k,n in split_sizes.items()}
write(e,'result/registration.json',{'passed':10,'total':10,'no_predictive_result':True,'splits':splits})
with gzip.open(e/'result/split-calendar.csv.gz','wt',newline='') as f:
 w=csv.writer(f);w.writerow(['split','eligible_all_9_windows','boundary_excluded'])
 for k,n in split_sizes.items():
  for i in range(n):w.writerow([k,int(i<n-240),int(i>=n-240)])
(e/'BTC-year-minute-and-frames.zip').write_bytes(b'synthetic transport')
write(e,'DELIVERY.json',{'status':'PASS_YEAR_DATA_AND_REGISTRATION_LEAD_REVIEW_PENDING','mode':'execution','input_archive_sha256':p.sha(e/'BTC-year-minute-and-frames.zip')});write(e,'data/audit.json',{'status':'PASS_AUTOMATED_DATA_CHECKS_LEAD_REVIEW_PENDING'});write(e,'INPUT_IDENTITY.json',{'fixture':True})
(e/'REPORT.md').write_text('Synthetic fixture only');(e/'result/REPORT.md').write_text('Synthetic fixture only')
mock=Mock();r=p.publish(mock,e,fixed,(Path(__file__).parent/'publish_existing.py').read_bytes());assert r['files_verified']==40 and r['no_year_or_research_rerun']
old=(e/'data/raw/BTCUSDT-1m-2025-09.zip').read_bytes();(e/'data/raw/BTCUSDT-1m-2025-09.zip').write_bytes(b'corrupt');rejected=False
try:p.check_local(e,fixed)
except AssertionError:rejected=True
assert rejected;(e/'data/raw/BTCUSDT-1m-2025-09.zip').write_bytes(old)
missing=False
try:p.API('')
except RuntimeError:missing=True
assert missing
result={'status':'PASS_OFFLINE_PUBLICATION_FIXTURE_ONLY','immutable_blobs_verified':r['files_verified'],'split_rows_reconciled':525600,'tampered_source_rejected':True,'missing_credential_rejected':True,'no_main_or_merge_or_PR_requests':True,'live_authenticated_GitHub_upload':'NOT_TESTED_TOKEN_PENDING','real_existing_executor_evidence':'REPORTED_ONLY_NOT_AVAILABLE_IN_LEAD_WORKSPACE'}
(Path(__file__).parent/'READINESS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
