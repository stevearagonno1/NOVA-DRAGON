"""Prepared single-command foreground path: setup -> fixture -> measure -> audit -> publish."""
from pathlib import Path
import argparse,fcntl,hashlib,json,os,sys,time
import prepare_runtime as E
import supervision85 as V
import publish89 as P
ROOT=Path(__file__).resolve().parent
STATE_ROOT=None

def guard(workspace,reserve=0):
    total=0
    for p in Path(workspace).rglob('*'):
        if p.is_file() and not p.is_symlink():total+=p.stat().st_size
    if total+reserve>125000000:raise RuntimeError('Workspace bytes '+str(total)+' + reserved '+str(reserve)+' exceeds 125000000; no deletion authorised')
    return total

def main():
    global STATE_ROOT
    ap=argparse.ArgumentParser();ap.add_argument('--workspace',required=True);ap.add_argument('--source',required=True);ap.add_argument('--runtime',default='/tmp/nova-l0089-runtime-'+sys.implementation.cache_tag);ap.add_argument('--preflight-only',action='store_true');a=ap.parse_args()
    workspace=Path(a.workspace).resolve();root=workspace/'nova-l0089';root.mkdir(parents=True,exist_ok=True);STATE_ROOT=root
    lock=(root/'run.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('L0089 supervisor or its child is active; follow that process instead of starting another') from None
    V.LOCK_FD=lock.fileno()
    manifest=json.loads((ROOT/'package_manifest.json').read_text())
    for name,digest in manifest.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,('pinned package changed',name)
    V.durable(root/'scope.json',json.loads((ROOT/'scope.json').read_text()))
    start=time.monotonic();guard(workspace,20000000)
    env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1';env['OPENBLAS_NUM_THREADS']='1';env['OMP_NUM_THREADS']='1';env['NOVA89_WORKSPACE']=str(workspace);env['NOVA85_WORKSPACE']=str(workspace)
    setup=E.prepare(a.runtime,workspace);V.durable(root/'environment.json',setup)
    env['PYTHONPATH']=str(Path(a.runtime).resolve())+os.pathsep+str(ROOT)+os.pathsep+env.get('PYTHONPATH','')
    V.run_checked('tests',[sys.executable,str(ROOT/'test89.py')],env,root)
    V.run_checked('synthetic',[sys.executable,str(ROOT/'experiment89.py'),'synthetic','--out',str(root/'synthetic')],env,root)
    V.run_checked('synthetic-audit',[sys.executable,str(ROOT/'experiment89.py'),'audit','--out',str(root/'synthetic'),'--synthetic-audit'],env,root)
    guard(workspace,16000000)
    # Public reading does not need credentials. Upload is tested before long work.
    P.ensure_source(ROOT,a.source)
    head=P.preflight(ROOT,a.source);V.durable(root/'upload-preflight.json',{'head':head,'status':'PASS'})
    if a.preflight_only:print('PREFLIGHT_PASS; MARKET NOT RUN',flush=True);return
    V.run_checked('measure',[sys.executable,str(ROOT/'experiment89.py'),'measure','--out',str(root/'market')],env,root)
    V.run_checked('audit',[sys.executable,str(ROOT/'experiment89.py'),'audit','--out',str(root/'market')],env,root)
    V.durable(root/'market/delivery.json',{'status':'DISCOVERY_COMPLETE_LEAD_REVIEW_PENDING','synthetic':False,'rows':360,'adoption':'NOT AUTHORISED','full_execution_seconds_before_upload':time.monotonic()-start})
    guard(workspace,8000000)
    head,receipt=P.complete(ROOT,root/'market',a.source)
    receipt.update(commit=head,workspace_bytes=guard(workspace),verified_remote=True,full_execution_seconds=time.monotonic()-start);V.durable(root/'remote-delivery.json',receipt)
    print('تم',flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        token=os.environ.get('GH_TOKEN','');s=type(e).__name__+': '+str(e);safe=s.replace(token,'[REDACTED]') if token else s
        if STATE_ROOT:V.durable(STATE_ROOT/'BLOCKED.json',{'status':'BLOCKED','actual_error':safe,'no_completion_claim':True})
        print('خطأ: '+safe,flush=True);raise SystemExit(1)
