"""Publish existing registered BTC evidence; never rerun research or access old tokens."""
import argparse,base64,csv,gzip,hashlib,json,os,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
REPO='stevearagonno1/NOVA-DRAGON'
SOURCE='b0b8064c64f75d9a028d30e03b6bb9a898423b65'
BRANCH='agent/btc-registration-from-repo-execution-2026-10-15'
DEST='research/btc-registration-from-repo-2026-10-15/executor'
MONTHS=['2025-09','2025-10','2025-11','2025-12']+[f'2026-{n:02}' for n in range(1,10)]
COUNTS={'1':568800,'5':113760,'15':37920,'60':9480}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def decode(blob):return base64.b64decode(blob['content'])
class API:
 def __init__(self,token):
  if not token or token.startswith('PENDING'):raise RuntimeError('GH_TOKEN missing: require owner-authorised current token')
  self.token=token
 def call(self,method,path,data=None):
  url='https://api.github.com'+path
  req=urllib.request.Request(url,data=None if data is None else json.dumps(data).encode(),method=method,headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'NOVA-registration-publisher'})
  if method!='GET':time.sleep(0.4)
  try:
   with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
  except urllib.error.HTTPError as e:
   msg=e.read().decode(errors='replace').replace(self.token,'[REDACTED]')
   retry=e.headers.get('Retry-After','unspecified')
   raise RuntimeError(f'GitHub {method} {path}: HTTP{e.code}; Retry-After={retry}; {msg[:1200]}') from None
 def ref(self):return self.call('GET',f'/repos/{REPO}/git/ref/heads/'+urllib.parse.quote(BRANCH,safe=''))['object']['sha']
def preflight(api):
 repo=api.call('GET',f'/repos/{REPO}');assert repo.get('permissions',{}).get('push') is True,'Token does not confirm repository write permission'
 c=api.call('GET',f'/repos/{REPO}/git/commits/{SOURCE}');assert c['sha']==SOURCE
 probe=b'NOVA authorised publication preflight; no market measurement'
 h=api.call('POST',f'/repos/{REPO}/git/blobs',{'content':base64.b64encode(probe).decode(),'encoding':'base64'})['sha']
 assert decode(api.call('GET',f'/repos/{REPO}/git/blobs/{h}'))==probe,'Write/read credential probe failed'
 return c
def check_local(execution,fixed):
 parent=execution.parent;publisher=Path(__file__).resolve().parent
 roots=[parent] if publisher.is_relative_to(parent) else [publisher] if parent.is_relative_to(publisher) else [parent,publisher]
 size=sum(f.stat().st_size for root in roots for f in root.rglob('*') if f.is_file());assert size<=125000000,'Entire task plus publisher directories exceed125MB'
 required=['DELIVERY.json','REPORT.md','INPUT_IDENTITY.json','protocol.json','data/manifest.json','data/audit.json','result/registration.json','result/frozen-protocol.json','result/split-calendar.csv.gz','result/REPORT.md']
 missing=[n for n in required if not (execution/n).is_file()];assert not missing,'Existing evidence missing: '+','.join(missing)+'; do not rerun year'
 load=lambda n:json.loads((execution/n).read_text())
 receipt=load('DELIVERY.json');assert receipt['status']=='PASS_YEAR_DATA_AND_REGISTRATION_LEAD_REVIEW_PENDING' and receipt['mode']=='execution'
 manifest=load('data/manifest.json');assert manifest['counts']==COUNTS and {r['month']:r['source_sha256'] for r in manifest['sources']}==fixed['source_sha256_by_month']
 audit=load('data/audit.json');assert audit['status']=='PASS_AUTOMATED_DATA_CHECKS_LEAD_REVIEW_PENDING'
 reg=load('result/registration.json');assert reg['passed']==reg['total']==10 and reg['no_predictive_result'] is True
 resolved=load('protocol.json');assert resolved==load('result/frozen-protocol.json')
 assert all(resolved[k]==v for k,v in fixed.items() if k not in ['input_manifest_sha256','frame_sha256'])
 assert digest((execution/'data/manifest.json').read_bytes())==resolved['input_manifest_sha256'];assert manifest['frame_sha256']==resolved['frame_sha256']
 bundle=execution/'BTC-year-minute-and-frames.zip';assert bundle.is_file() and sha(bundle)==receipt['input_archive_sha256']
 for n in COUNTS:assert sha(execution/f'data/frames/BTCUSDT-{n}m.csv.gz')==manifest['frame_sha256'][n]
 for month in MONTHS:
  f=execution/f'data/raw/BTCUSDT-1m-{month}.zip';assert f.is_file() and sha(f)==fixed['source_sha256_by_month'][month]
 counts={k:{'all':0,'eligible':0,'excluded':0} for k in reg['splits']}
 with gzip.open(execution/'result/split-calendar.csv.gz','rt',newline='') as f:
  for r in csv.DictReader(f):
   x=counts[r['split']];x['all']+=1;x['eligible']+=int(r['eligible_all_9_windows']);x['excluded']+=int(r['boundary_excluded'])
 for k,v in counts.items():assert v=={'all':reg['splits'][k]['feature_anchor_rows'],'eligible':reg['splits'][k]['eligible_all_9_windows'],'excluded':240}
 assert sum(x['all'] for x in counts.values())==525600
 return required,size
def publish(api,execution,fixed,code_bytes):
 started=time.time();required,size=check_local(execution,fixed);base=preflight(api)
 files={DEST+'/'+n:(execution/n).read_bytes() for n in required}
 files[DEST+'/tools/publish_existing.py']=code_bytes
 for month in MONTHS:
  for suffix in ['zip','zip.CHECKSUM']:
   n=f'data/raw/BTCUSDT-1m-{month}.{suffix}';files[DEST+'/'+n]=(execution/n).read_bytes()
 files['docs/journal/2026-10-15-btc-registration-from-repo/002-existing-run-published.md']=b'Decision: resume publication only after credential repair.\nExecution: existing full-year source hashes,frame hashes,archive and525600 split rows reconciled; no rerun.\nProduced: reports,raw monthly archives and immutable publication readback.\nNext: Lead independent review; no adoption or main merge.\n'
 assert all(len(b)<25000000 for b in files.values()),'Individual publication file exceeds25MB'
 try:parent=api.ref()
 except RuntimeError as e:
  if 'HTTP404' not in str(e):raise
  api.call('POST',f'/repos/{REPO}/git/refs',{'ref':'refs/heads/'+BRANCH,'sha':SOURCE});parent=SOURCE
 # Preserve append-only publication history on retry; all content paths are deterministic.
 parent_commit=api.call('GET',f'/repos/{REPO}/git/commits/{parent}')
 root=api.call('GET',f'/repos/{REPO}/git/trees/{parent_commit["tree"]["sha"]}')
 log=next(x for x in root['tree'] if x['path']=='LOG.md')
 old_log=decode(api.call('GET',f'/repos/{REPO}/git/blobs/{log["sha"]}'))
 files['LOG.md']=old_log+b'\n\n## Existing BTC registration publication resumed - 2026-10-15\nExisting year evidence only; original13source hashes,4frame hashes and525600 split rows reconciled before publication. No collection or signal research rerun. Work branch only; Lead review pending.\n'
 proof={'state':'CONTENT_READY_READBACK_PENDING','source_commit':SOURCE,'branch':BRANCH,'source_year_already_completed':True,'local_task_bytes':size,'published_file_sha256':{p:digest(b) for p,b in files.items()},'whole_original_executor_duration':'not measured unless executor retained its original start time','publish_attempt_started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 files[DEST+'/PUBLICATION_PLAN.json']=json.dumps(proof,indent=2).encode()
 entries=[];blobs={}
 for path,content in files.items():
  blob=api.call('POST',f'/repos/{REPO}/git/blobs',{'content':base64.b64encode(content).decode(),'encoding':'base64'})['sha'];blobs[path]=blob;entries.append({'path':path,'mode':'100644','type':'blob','sha':blob})
 tree=api.call('POST',f'/repos/{REPO}/git/trees',{'base_tree':parent_commit['tree']['sha'],'tree':entries})['sha']
 commit=api.call('POST',f'/repos/{REPO}/git/commits',{'message':'Publish existing BTC registration and source evidence; no research rerun','tree':tree,'parents':[parent]})['sha']
 assert api.ref()==parent,'Work branch changed concurrently; preserve local files and stop'
 api.call('PATCH',f'/repos/{REPO}/git/refs/heads/'+urllib.parse.quote(BRANCH,safe=''),{'sha':commit,'force':False})
 for path,expected in files.items():
  got=decode(api.call('GET',f'/repos/{REPO}/git/blobs/{blobs[path]}'));assert got==expected,'Immutable blob mismatch: '+path
 assert api.call('GET',f'/repos/{REPO}/git/commits/{commit}')['tree']['sha']==tree
 final={'status':'PUBLISHED_AND_IMMUTABLE_READBACK_VERIFIED_LEAD_REVIEW_PENDING','source_commit':SOURCE,'verified_data_commit':commit,'branch':BRANCH,'files_verified':len(files),'publication_seconds':time.time()-started,'no_year_or_research_rerun':True,'next':'Lead independent audit'}
 receiptpath=DEST+'/VERIFIED_DELIVERY.json';body=json.dumps(final,indent=2).encode();blob=api.call('POST',f'/repos/{REPO}/git/blobs',{'content':base64.b64encode(body).decode(),'encoding':'base64'})['sha']
 tree2=api.call('POST',f'/repos/{REPO}/git/trees',{'base_tree':tree,'tree':[{'path':receiptpath,'mode':'100644','type':'blob','sha':blob}]})['sha']
 commit2=api.call('POST',f'/repos/{REPO}/git/commits',{'message':'Record verified registration delivery','tree':tree2,'parents':[commit]})['sha']
 assert api.ref()==commit
 api.call('PATCH',f'/repos/{REPO}/git/refs/heads/'+urllib.parse.quote(BRANCH,safe=''),{'sha':commit2,'force':False})
 assert decode(api.call('GET',f'/repos/{REPO}/git/blobs/{blob}'))==body
 assert api.call('GET',f'/repos/{REPO}/git/commits/{commit2}')['tree']['sha']==tree2
 final['receipt_commit']=commit2;(execution/'VERIFIED_DELIVERY.json').write_text(json.dumps(final,indent=2)+'\n');return final
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execution',type=Path,default=Path('/home/user/btc-registration-from-repo-2026-10-15/execution'));p.add_argument('--preflight',action='store_true');a=p.parse_args()
 api=API(os.environ.get('GH_TOKEN',''))
 if a.preflight:preflight(api);print('PREFLIGHT_REPOSITORY_WRITE_PERMISSION_CONFIRMED')
 else:
  file=Path(__file__).resolve();fixed=json.loads(file.with_name('protocol.json').read_text());result=publish(api,a.execution,fixed,file.read_bytes());print(json.dumps(result))
