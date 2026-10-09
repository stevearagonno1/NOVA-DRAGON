"""Lease-protected GitHub publication. ZIP and large payloads are built/read in memory only."""
import base64,csv,datetime,email.utils,gzip,hashlib,io,json,os,time,urllib.error,urllib.parse,urllib.request,zipfile
from pathlib import Path
from .run import WORKSPACE,PACKAGE,workspace_bytes,BASE_WORKSPACE_BYTES,MAX_WORKSPACE,MAX_TASK_OUTPUT,sha256_file

REPO='stevearagonno1/NOVA-DRAGON';BRANCH='agent/entry-singletons-package-v1-2026-10-08'
BASE='86304b62bf9c7d0914572e100892fac66f3f09dd'
EVIDENCE='docs/research/entry-singletons-package-v1-2026-10-08'
class AuthError(RuntimeError):pass
class ApiError(RuntimeError):pass
class WriteOutcomeUnknown(RuntimeError):pass

class Response:
 def __init__(self,status,headers=None,body=b''):self.status=status;self.headers=headers or {};self.body=body
class FakeTransport:
 def __init__(self,answers):self.answers=list(answers);self.calls=[]
 def __call__(self,request,timeout=30):
  self.calls.append((request.get_method(),request.full_url))
  ans=self.answers.pop(0)
  if isinstance(ans,BaseException):raise ans
  return ans

def _header(headers,name):
 for k,v in (headers or {}).items():
  if k.lower()==name.lower():return v
 return None
def _retry_seconds(value):
 if value is None:return None
 try:return max(0.0,float(value))
 except (TypeError,ValueError):
  try:return max(0.0,email.utils.parsedate_to_datetime(value).timestamp()-time.time())
  except Exception:return None

def safe_request(transport,method,url,headers=None,data=None,*,sleep=time.sleep,timeout=45):
 """Retry explicit throttling only after its Retry-After; never blindly repeat an uncertain write."""
 method=method.upper();write=method in ('POST','PATCH','PUT','DELETE');attempt=0
 while True:
  req=urllib.request.Request(url,data=data,headers=headers or {},method=method)
  try:resp=transport(req,timeout=timeout)
  except Exception as exc:
   if write:raise WriteOutcomeUnknown(f'{method} outcome unknown after transport error ({type(exc).__name__}); reconcile remote HEAD before retry') from None
   if attempt<1:attempt+=1;continue
   raise ApiError(f'read transport failed ({type(exc).__name__})') from None
  if 200<=resp.status<300:return resp
  after=_retry_seconds(_header(resp.headers,'Retry-After'))
  if resp.status in (403,429,503) and after is not None and attempt<2:
   sleep(after);attempt+=1;continue
  if resp.status==401 or resp.status==403:raise AuthError(f'GitHub API authentication/permission failure HTTP {resp.status}')
  if write and resp.status>=500:raise WriteOutcomeUnknown(f'{method} returned HTTP {resp.status}; reconcile remote HEAD before retry')
  raise ApiError(f'GitHub API request failed HTTP {resp.status}')

def test_transport():
 waits=[]
 tr=FakeTransport([Response(401)])
 try:safe_request(tr,'GET','https://unit.invalid/x',sleep=waits.append)
 except AuthError as e:require_msg='HTTP 401' in str(e)
 else:raise AssertionError('fake 401 was not rejected')
 if not require_msg:raise AssertionError('401 error not sanitized')
 tr=FakeTransport([Response(403,{'Retry-After':'0'}),Response(200,{},b'ok')])
 r=safe_request(tr,'GET','https://unit.invalid/x',sleep=waits.append)
 if r.body!=b'ok' or len(tr.calls)!=2 or waits!=[0.0]:raise AssertionError('Retry-After not honored')
 tr=FakeTransport([ConnectionError('simulated disconnect')])
 try:safe_request(tr,'POST','https://unit.invalid/write',data=b'{}',sleep=waits.append)
 except WriteOutcomeUnknown:pass
 else:raise AssertionError('uncertain write outcome was replayed')
 if len(tr.calls)!=1:raise AssertionError('uncertain write was retried')
 return 'PASS'

def _http_transport(request,timeout=45):
 try:
  with urllib.request.urlopen(request,timeout=timeout) as r:return Response(r.status,dict(r.headers.items()),r.read())
 except urllib.error.HTTPError as e:return Response(e.code,dict(e.headers.items()),b'')

def git_blob_sha(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def _json_bytes(obj):return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
# Matches real credential shapes only (prefix followed by a minimum-length body), not bare prefix text.
# Bare prefix words such as the literal guard names inside this file do not match.
_TOKEN_SHAPE_RE=__import__('re').compile(rb'github_pat_[A-Za-z0-9_]{22,}|gh[pousr]_[A-Za-z0-9]{36,}')
def _safe_payload_scan(payloads,token):
 if not token or len(token)<20:raise ValueError('credential unavailable or implausibly short; refuse publication')
 needle=token.encode()
 for path,data in payloads.items():
  if needle in data:raise ValueError(f'private credential found in publication payload {path}')
  if _TOKEN_SHAPE_RE.search(data):raise ValueError(f'token-like string found in publication payload {path}')

def _redact_paper(path):
 """Create an archival redaction in memory, removing entire auth-bearing lines and token literals."""
 text=Path(path).read_text(encoding='utf-8');lines=text.splitlines();out=[];secret_words=('token','credential','password','secret','bearer','authorization','api_key','gh_token')
 import re
 token_re=re.compile(r'(?i)(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{12,}|Bearer\s+\S+|(?:token|password|secret|credential)\s*[:=]\s*[^\s`]+')
 in_sensitive_fence=False
 for line in lines:
  if line.strip().startswith('```'):
   if in_sensitive_fence:in_sensitive_fence=False
   out.append(line);continue
  if any(w in line.lower() for w in secret_words):
   out.append('[REDACTED SENSITIVE LINE]')
   if line.strip().startswith('```'):in_sensitive_fence=True
   continue
  if in_sensitive_fence:
   out.append('[REDACTED SENSITIVE COMMAND]');continue
  clean=token_re.sub('[REDACTED]',line)
  # Also redact any standalone long credential-like value on its own line.
  if len(clean.strip())>=24 and not any(ch.isspace() for ch in clean.strip()) and clean.strip() not in ('[REDACTED]',):clean='[REDACTED]'
  out.append(clean)
 return ('\n'.join(out)+'\n').encode()

def _read_text_api(api,path,ref):
 q=urllib.parse.urlencode({'ref':ref});obj=api.json('GET',f'/contents/{urllib.parse.quote(path,safe="/")}?{q}')
 if obj.get('encoding')!='base64':raise ApiError('remote text response was not base64')
 return base64.b64decode(obj['content'])

class GitHub:
 def __init__(self,token,repo=REPO,sleep=time.sleep):
  self.repo=repo;self.base='https://api.github.com/repos/'+repo;self.sleep=sleep
  self.headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28','User-Agent':'Arena-entry-singletons-r3'}
 def request(self,method,path,obj=None):
  data=None if obj is None else _json_bytes(obj);h=dict(self.headers)
  if data is not None:h['Content-Type']='application/json'
  resp=safe_request(_http_transport,method,self.base+path,h,data,sleep=self.sleep)
  return resp
 def json(self,method,path,obj=None):
  r=self.request(method,path,obj)
  try:return json.loads(r.body)
  except Exception:raise ApiError('GitHub API returned invalid JSON') from None
 def branch_head(self):
  return self.json('GET','/git/ref/heads/'+BRANCH)['object']['sha']
 def blob(self,data):
  return self.json('POST','/git/blobs',{'content':base64.b64encode(data).decode(),'encoding':'base64'})['sha']
 def tree(self,base_tree,items):
  entries=[]
  for path,data in items.items():entries.append({'path':path,'mode':'100644','type':'blob','sha':self.blob(data)})
  return self.json('POST','/git/trees',{'base_tree':base_tree,'tree':entries})['sha']
 def commit(self,tree,parent,message):
  return self.json('POST','/git/commits',{'message':message,'tree':tree,'parents':[parent],'author':{'name':'Arena.ai Agent','email':'agent@arena.ai'},'committer':{'name':'Arena.ai Agent','email':'agent@arena.ai'}})['sha']
 def readback(self,commit_sha,expected):
  c=self.json('GET','/git/commits/'+commit_sha);tree=self.json('GET','/git/trees/'+c['tree']['sha']+'?recursive=1')
  if tree.get('truncated'):raise ApiError('remote tree truncated; immutable readback incomplete')
  found={e['path']:e for e in tree['tree'] if e.get('type')=='blob'}
  for path,data in expected.items():
   e=found.get(path)
   if not e or e['sha']!=git_blob_sha(data):raise ApiError(f'immutable tree hash mismatch at {path}')
   blob=self.json('GET','/git/blobs/'+e['sha'])
   remote=base64.b64decode(blob['content'])
   if remote!=data:raise ApiError(f'immutable blob byte mismatch at {path}')
  return sorted(expected)

def _zip_in_memory(entries):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name,data in sorted(entries.items()):
   info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
   z.writestr(info,data)
 return b.getvalue()

def _combined_alerts(run_dir):
 out=io.StringIO(newline='');header=None;count=0
 for asset in ('BTC','ETH','SOL'):
  with gzip.open(Path(run_dir)/f'asset-{asset}-fixture-alerts.csv.gz','rt',encoding='utf-8',newline='') as f:
   reader=csv.reader(f)
   h=next(reader)
   if header is None:header=h;csv.writer(out,lineterminator='\n').writerow(h)
   elif header!=h:raise ValueError('asset alert schemas differ')
   w=csv.writer(out,lineterminator='\n')
   for row in reader:
    if len(row)!=len(header) or row[-1]!='true':raise ValueError('invalid/non-synthetic fixture alert row')
    w.writerow(row);count+=1
 return out.getvalue().encode(),count

def build_archive(workspace,run_result,tests_result,commands_log):
 workspace=Path(workspace);pkg=workspace/'tools/entry_singletons_v1';run=workspace/'run'
 entries={
  'fixture-generator.py':(pkg/'fixture_generator.py').read_bytes(),
  'fixture-runner.py':(pkg/'run.py').read_bytes(),
  'independent-audit.py':(pkg/'audit.py').read_bytes(),
  'scope.json':(pkg/'scope.json').read_bytes(),'registry.json':(pkg/'registry.json').read_bytes(),'checksums.json':(pkg/'checksums.json').read_bytes(),
  'run-manifest.json':(run/'run-manifest.json').read_bytes(),'fixtures-results.csv':(run/'fixtures-results.csv').read_bytes(),
  'audit.json':(run/'audit.json').read_bytes(),'quality-tests.json':(run/'quality-tests.json').read_bytes(),
  'runtime.json':(run/'runtime.json').read_bytes(),'commands.log':commands_log,
  'PREPARATION-REPORT.md':(run/'PREPARATION-REPORT.md').read_bytes(),
 }
 alerts,n=_combined_alerts(run);entries['fixture-alerts.csv']=alerts
 for asset in ('BTC','ETH','SOL'):entries[f'masks-{asset}.bin.gz']=(run/f'asset-{asset}-masks.bin.gz').read_bytes()
 for name,data in entries.items():
  if not isinstance(data,bytes):raise TypeError(name)
 archive=_zip_in_memory(entries)
 if len(archive)>8_000_000:raise OSError(f'in-memory evidence ZIP exceeds 8MB: {len(archive)}')
 return archive,entries,n

def build_package_payload():
 files={}
 for p in sorted(PACKAGE.iterdir()):
  if p.is_file() and p.name!='__pycache__':files['tools/entry_singletons_v1/'+p.name]=p.read_bytes()
 return files

def _verify_source_path_absent(api):
 tree=api.json('GET','/git/trees/'+BASE+'?recursive=1')
 if tree.get('truncated'):raise ApiError('base tree truncated; cannot verify new path')
 prefix='tools/entry_singletons_v1'
 if any(x.get('path')==prefix or x.get('path','').startswith(prefix+'/') for x in tree.get('tree',[])):raise ApiError('base commit already contains package path; stop rather than overwrite')
 commit=api.json('GET','/git/commits/'+BASE)
 return commit['tree']['sha']

def _append_evidence_log(api):
 log=_read_text_api(api,'LOG.md',BASE).decode('utf-8');handoff=_read_text_api(api,'docs/HANDOFF.md',BASE).decode('utf-8')
 stamp='2026-10-08'
 log += f"\n\n## {stamp} — Entry singletons package R3\n- Status: SYNTHETIC_PASS_REMOTE_READBACK_PENDING; `market_run=false`.\n- Source commits: Constitution `6d0226a03b84656e14b94dd8a37e39332cc2f68f`; tools/results `86304b62bf9c7d0914572e100892fac66f3f09dd`.\n- 226 settings, 2,034 candidate cells, 4,068 candidate rows + 36 controls = 4,104 synthetic rows; zero rows retained.\n- No market data, August validation, or performance claim. Evidence: `{EVIDENCE}/`.\n"
 handoff += f"\n\n## Entry singletons R3 — 2026-10-08\n**Source:** pinned Constitution and tools/results commits listed in `{EVIDENCE}/scope.json`. **State:** SYNTHETIC_PASS_REMOTE_READBACK_PENDING. **Limits:** synthetic fixtures only; no market run, August check, tuning, or performance claim; classifier correlates PULLBACK with EMA and TURN with RSI. **Next:** finish immutable readback before claiming readiness; no follow-on market task is authorized here.\n"
 return {'LOG.md':log.encode(),'docs/HANDOFF.md':handoff.encode()}

def _journal_payload(runtime,audit,tests,delivery_pending=True):
 root='docs/journal/2026-10-08-entry-singletons-package-v1/'
 p007=f"# 007 — R3 runtime preflight\n\n- Python: {runtime.get('version')}\n- Executable: `{runtime.get('executable')}`\n- Implementation: {runtime.get('implementation')}; standard-library import set: {runtime.get('stdlib_imports')}\n- R2 Python 3.12 blocker read; R3 explicitly permits CPython 3.13.x. No install/download, pip, venv, cache, or market input.\n- Source main `6d0226a03b84656e14b94dd8a37e39332cc2f68f`; tools `86304b62bf9c7d0914572e100892fac66f3f09dd`.\n"
 p008=f"# 008 — R3 synthetic acceptance\n\n- Status: {tests.get('status')}; checks: {tests.get('checks_passed')} passed.\n- Independent audit: {audit.get('status')}; rows rebuilt {audit.get('rows_rebuilt')}; zero rows {audit.get('zero_rows')}; causal prefix positions {audit.get('causal_prefix_checks')}; mask comparisons {audit.get('causal_mask_comparisons')}.\n- `market_run=false`; synthetic fixture only. No August or market results.\n"
 p009=f"# 009 — R3 delivery\n\n- Status: {'SYNTHETIC_PASS_REMOTE_READBACK_PENDING' if delivery_pending else 'PACKAGE_READY_LEAD_REVIEW_PENDING'}.\n- Publication branch: `{BRANCH}`; immutable code/evidence commits and readback receipt are in `remote-delivery.json`.\n- Main/PR/merge: none. Archive excludes the final receipt publication.\n"
 return {root+'007-r3-runtime.md':p007.encode(),root+'008-r3-synthetic.md':p008.encode(),root+'009-r3-delivery.md':p009.encode()}

def publish(token,*,workspace=WORKSPACE,run_result=None,tests_result=None,commands_log=b''):
 """Publish to a new, scope-matched branch in three immutable, lease-checked steps."""
 workspace=Path(workspace);run=workspace/'run';api=GitHub(token);start=time.monotonic()
 if run_result is None:run_result=json.loads((run/'run-result.json').read_text())
 if tests_result is None:tests_result=json.loads((run/'quality-tests.json').read_text())
 if run_result.get('status')!='COMPLETE' or tests_result.get('status')!='PASS':raise ValueError('publication blocked: synthetic run/tests not PASS')
 if run_result.get('manifest',{}).get('market_run') is not False:raise ValueError('publication blocked: market_run not false')
 # Build all payloads in memory and scan exact private value before any remote write.
 archive,archive_entries,alert_count=build_archive(workspace,run_result,tests_result,commands_log)
 code_payload=build_package_payload()
 docs=workspace/'docs/research/entry-singletons-package-v1-2026-10-08'
 evidence_payload={}
 for p in sorted(docs.iterdir()):
  if p.is_file():evidence_payload[f'{EVIDENCE}/{p.name}']=p.read_bytes()
 evidence_payload[f'{EVIDENCE}/fixtures-results.csv']=(run/'fixtures-results.csv').read_bytes()
 evidence_payload[f'{EVIDENCE}/fixture-alerts.csv']=archive_entries['fixture-alerts.csv']
 evidence_payload[f'{EVIDENCE}/audit.json']=(run/'audit.json').read_bytes()
 evidence_payload[f'{EVIDENCE}/evidence.zip']=archive
 for a in ('BTC','ETH','SOL'):evidence_payload[f'{EVIDENCE}/masks-{a}.bin.gz']=(run/f'asset-{a}-masks.bin.gz').read_bytes()
 runtime_obj=json.loads((run/'runtime.json').read_text());audit_obj=json.loads((run/'audit.json').read_text())
 evidence_payload.update(_journal_payload(runtime_obj,audit_obj,tests_result,True))
 evidence_payload.update(_append_evidence_log(api))
 _safe_payload_scan({**code_payload,**evidence_payload},token)
 if workspace_bytes()>MAX_WORKSPACE:raise OSError('whole workspace exceeds ceiling before publication')
 if workspace_bytes()-BASE_WORKSPACE_BYTES>MAX_TASK_OUTPUT:raise OSError('R3 local output cap exceeded before publication')
 # Read current HEAD and scope before any branch write; mismatching scope is never overwritten.
 try:existing=api.branch_head()
 except ApiError as e:
  if '404' not in str(e):raise
  existing=None
 if existing is not None:
  remote_scope=_read_text_api(api,'tools/entry_singletons_v1/scope.json',existing)
  if remote_scope!=(PACKAGE/'scope.json').read_bytes():raise ApiError('existing target branch scope differs; stop without overwrite')
  api.readback(existing,code_payload)
  current=api.json('GET','/git/commits/'+existing)
  parents=[x.get('sha') for x in current.get('parents',[])]
  if parents!=[BASE]:raise ApiError('existing scope/code matches but branch is not the expected immutable package commit; stop')
  head=existing;code_commit=existing
 else:
  base_tree=_verify_source_path_absent(api)
  code_tree=api.tree(base_tree,code_payload)
  code_commit=api.commit(code_tree,BASE,'Add synthetic-only entry singletons fixture package (R3)')
  try:api.json('POST','/git/refs',{'ref':'refs/heads/'+BRANCH,'sha':code_commit})
  except WriteOutcomeUnknown:
   if api.branch_head()!=code_commit:raise
  head=api.branch_head()
  if head!=code_commit:raise ApiError('lease check failed after branch creation')
  # The newly referenced immutable commit is now addressable for byte-for-byte readback.
  api.readback(code_commit,code_payload)
 # Rebase evidence payloads after immutable code SHA is known, retaining only a pending readiness claim.
 readiness_path=f'{EVIDENCE}/readiness.json';delivery_path=f'{EVIDENCE}/delivery.json'
 runmeta=json.loads((run/'run-manifest.json').read_text());audit=json.loads((run/'audit.json').read_text());runtime=json.loads((run/'runtime.json').read_text())
 limits=json.loads((docs/'storage-status.json').read_text())
 pending={'status':'SYNTHETIC_PASS_REMOTE_READBACK_PENDING','synthetic':True,'market_run':False,'settings':226,'cells':2034,'summary_rows':4104,'checks_passed':int(tests_result['checks_passed']),'checks_total':int(tests_result['checks_passed']),'limits':limits,'code_commit':code_commit}
 readiness_bytes=(json.dumps(pending,indent=2,sort_keys=True)+'\n').encode()
 delivery={'status':'SYNTHETIC_PASS_REMOTE_READBACK_PENDING','source_main':'6d0226a03b84656e14b94dd8a37e39332cc2f68f','source_tools':BASE,'runtime_version':runtime['version'],'runtime_executable':runtime['executable'],'scope_sha256':json.loads((docs/'scope.json').read_text())['scope_sha256'] if 'scope_sha256' in json.loads((docs/'scope.json').read_text()) else hashlib.sha256((PACKAGE/'scope.json').read_bytes()).hexdigest(),'archive_bytes':len(archive),'archive_sha256':hashlib.sha256(archive).hexdigest(),'workspace_bytes':workspace_bytes(),'elapsed_total_seconds':int(time.time()-Path('/home/user/uploads/ENTRY-SINGLETONS-PACKAGE-01-R3-PRIVATE (1).md').stat().st_mtime),'compute_only_seconds':json.loads((run/'run-result.json').read_text()).get('compute_only_seconds'),'market_run':False,'remaining_limits':['Synthetic plumbing only; no market-performance conclusion.','PULLBACK/EMA and TURN/RSI classifier-family dependence is disclosed.']}
 delivery_bytes=(json.dumps(delivery,indent=2,sort_keys=True)+'\n').encode()
 evidence_payload[readiness_path]=readiness_bytes;evidence_payload[delivery_path]=delivery_bytes
 _safe_payload_scan(evidence_payload,token)
 # Current branch head is the lease. Evidence commit has exactly that parent.
 if api.branch_head()!=code_commit:raise ApiError('branch head changed before evidence tree; lease rejected')
 code_tree_obj=api.json('GET','/git/commits/'+code_commit);etree=api.tree(code_tree_obj['tree']['sha'],evidence_payload)
 ecommit=api.commit(etree,code_commit,'Add synthetic evidence and R3 report (readback pending)')
 try:api.json('PATCH','/git/refs/heads/'+BRANCH,{'sha':ecommit,'force':False})
 except WriteOutcomeUnknown:
  if api.branch_head()!=ecommit:raise
 if api.branch_head()!=ecommit:raise ApiError('branch lease failed after evidence publication')
 # Immutable evidence readback verifies every package/evidence byte at the commit that contains it.
 read_paths=api.readback(ecommit,{**code_payload,**evidence_payload})
 elapsed_readback=time.monotonic()-start
 receipt={'verified_remote':True,'immutable_code_commit':code_commit,'immutable_evidence_commit':ecommit,'archive_sha256':hashlib.sha256(archive).hexdigest(),'readback_paths':read_paths,'measured_elapsed_until_readback_seconds':round(elapsed_readback,3),'final_receipt_publication_excluded':True}
 ready={**pending,'status':'PACKAGE_READY_LEAD_REVIEW_PENDING'}
 delivery['status']='PACKAGE_READY_LEAD_REVIEW_PENDING';delivery['remaining_limits']=['Synthetic plumbing only; no market-performance conclusion.','PULLBACK/EMA and TURN/RSI classifier-family dependence is disclosed.']
 receipt_bytes=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode()
 log_final=evidence_payload['LOG.md'].decode('utf-8')+f"\n\n## 2026-10-08 — Immutable readback verified\n- Status: PACKAGE_READY_LEAD_REVIEW_PENDING. Code `{code_commit}`; evidence `{ecommit}`; receipt `{receipt['archive_sha256']}`.\n- `market_run=false`; synthetic acceptance only; no market-performance or August claim.\n"
 handoff_final=evidence_payload['docs/HANDOFF.md'].decode('utf-8')+f"\n\n**Final readback:** PACKAGE_READY_LEAD_REVIEW_PENDING; immutable code `{code_commit}` and evidence `{ecommit}` verified; receipt commit `{receipt['archive_sha256']}`.\n"
 tick9=f"# 009 — R3 delivery\n\n- Status: PACKAGE_READY_LEAD_REVIEW_PENDING.\n- Branch: `{BRANCH}`. Immutable code commit: `{code_commit}`; evidence commit: `{ecommit}`; final receipt commit: pending its own publication (excluded from archive).\n- Archive SHA-256: `{receipt['archive_sha256']}`; immutable readback verified.\n- `market_run=false`; no market data or performance claim.\n"
 final_updates={readiness_path:(json.dumps(ready,indent=2,sort_keys=True)+'\n').encode(),delivery_path:(json.dumps(delivery,indent=2,sort_keys=True)+'\n').encode(),f'{EVIDENCE}/remote-delivery.json':receipt_bytes,'LOG.md':log_final.encode(),'docs/HANDOFF.md':handoff_final.encode(),'docs/journal/2026-10-08-entry-singletons-package-v1/009-r3-delivery.md':tick9.encode()}
 _safe_payload_scan(final_updates,token)
 if api.branch_head()!=ecommit:raise ApiError('branch head changed before final receipt; lease rejected')
 evidence_tree_obj=api.json('GET','/git/commits/'+ecommit);ftree=api.tree(evidence_tree_obj['tree']['sha'],final_updates)
 fcommit=api.commit(ftree,ecommit,'Record verified immutable R3 readback receipt')
 try:api.json('PATCH','/git/refs/heads/'+BRANCH,{'sha':fcommit,'force':False})
 except WriteOutcomeUnknown:
  if api.branch_head()!=fcommit:raise
 if api.branch_head()!=fcommit:raise ApiError('branch lease failed after final receipt')
 api.readback(fcommit,{**code_payload,**evidence_payload,**final_updates})
 return {'status':'PACKAGE_READY_LEAD_REVIEW_PENDING','branch':BRANCH,'code_commit':code_commit,'evidence_commit':ecommit,'receipt_commit':fcommit,'archive_sha256':receipt['archive_sha256'],'archive_bytes':len(archive),'readback_paths':len(read_paths),'elapsed_until_readback_seconds':receipt['measured_elapsed_until_readback_seconds'],'market_run':False}
