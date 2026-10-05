"""One prepared launcher: environment -> synthetic -> measure -> audit -> delivery.

Uses only stdlib until dependencies have passed their native admission probe.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

BASE='history/research/hyp_lab_out/L0084-entry-mix-r1/stages/01-singletons'
BRANCH='agent/l0084-stage1-checked-2026-10-05'
REPO='stevearagonno1/NOVA-DRAGON'


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NOVA-stage1-checked'}),timeout=40) as r:return r.read()
        except Exception:
            if attempt==2:raise
            time.sleep(2*(attempt+1))


def disk_bytes(workspace):
    return sum(p.stat().st_size for p in workspace.rglob('*') if p.is_file() and not p.is_symlink())


def materialize(source,workspace,local_source=None):
    url=f'https://raw.githubusercontent.com/{REPO}/{source}/'
    read=lambda path:(local_source/path).read_bytes() if local_source else get(url+path)
    raw=read(BASE+'/scope.json');scope=json.loads(raw)
    root=workspace/'nova-stage1-checked-v3';root.mkdir(parents=True,exist_ok=True)
    if disk_bytes(workspace)+1_000_000>125_000_000:
        raise RuntimeError('workspace admission: less than 1 MB reserved for prepared source/records')
    sources={'tools/l0084_entry_mix_r1/'+name:digest for name,digest in scope['code_sha256'].items()}
    sources.update(scope['helper_sha256'])
    def one(item):
        path,digest=item;destination=root/path
        candidates=[destination,workspace/'nova-stage1-20261005'/path]
        data=next((p.read_bytes() for p in candidates if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest),None)
        if data is None:data=read(path)
        if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('pinned source mismatch: '+path)
        if destination.exists() and destination.read_bytes()!=data:raise RuntimeError('existing source differs: '+str(destination))
        destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists():destination.write_bytes(data)
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(one,sources.items()))
    (root/'scope.json').write_bytes(raw)
    return root,scope


def run_checked(name,command,env,root,runner=subprocess.run):
    print('START '+name,flush=True)
    result=runner(command,env=env,text=True,capture_output=True)
    token=os.environ.get('GH_TOKEN','')
    output=result.stdout+'\n'+result.stderr
    if token:output=output.replace(token,'[REDACTED]')
    (root/(name+'.log')).write_text(output)
    print(output,flush=True)
    if result.returncode:raise RuntimeError(name+' exit '+str(result.returncode)+'; complete error retained in '+str(root/(name+'.log')))
    return output


def record(root,title,detail,files=None):
    # These imports deliberately remain independent of NumPy/PyArrow.
    from l0084_entry_mix_r1 import transport as T
    from l0084_entry_mix_r1.evidence import commit_evidence
    T.BRANCH=BRANCH
    try:
        from l0084_entry_mix_r1.stage1 import PacedTransport
        client=PacedTransport()
    except ImportError:
        client=T.GitHubTransport()
    return commit_evidence(files or {},'L0084 stage1: '+title,detail,title,
        '- Decision: stage 1 only.\n- Execution: '+detail+'\n- Produced: pinned evidence and status.\n- Next: finish current stage, then Lead review.',client=client)


def gated_steps(run,preflight_only=False):
    run('synthetic')
    if preflight_only:return
    run('measure');run('audit');run('delivery')


def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True)
    ap.add_argument('--workspace',default='/home/user');ap.add_argument('--preflight-only',action='store_true')
    ap.add_argument('--local-source',type=Path,help=argparse.SUPPRESS)
    ap.add_argument('--runtime',type=Path,help=argparse.SUPPRESS)
    args=ap.parse_args(argv);workspace=Path(args.workspace).resolve();workspace.mkdir(parents=True,exist_ok=True)
    lock=open(workspace/'nova-stage1-checked.lock','a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('another stage1 checked launcher is active in this workspace') from None
    root,scope=materialize(args.source,workspace,args.local_source)
    sys.path.insert(0,str(root/'tools'));os.environ['PYTHONDONTWRITEBYTECODE']='1'
    try:
        spec=importlib.util.spec_from_file_location('prepared_runtime',root/'tools/prepare_stage1_runtime.py')
        setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
        runtime=args.runtime or Path('/tmp/nova-stage1-runtime-'+sys.implementation.cache_tag)
        admission=setup.prepare(runtime,workspace)
        (root/'environment.json').write_text(json.dumps(admission,indent=2))
        env=dict(os.environ);env.update(PYTHONDONTWRITEBYTECODE='1',
            PYTHONPATH=str(root/'tools')+os.pathsep+str(runtime)+os.pathsep+env.get('PYTHONPATH',''),
            L0084_R1_ROOT=str(root),L0084_R1_OUTPUT=str(root/'local-record'),NOVA_STAGE1_WORKSPACE=str(workspace))
        sys.path.insert(0,str(runtime))
        def run(name):
            if name=='delivery':
                workspace_bytes=disk_bytes(workspace)
                if workspace_bytes>125_000_000:raise RuntimeError('final workspace guard exceeded: '+str(workspace_bytes))
                from l0084_entry_mix_r1 import transport as T
                from l0084_entry_mix_r1.stage1 import PacedTransport
                T.BRANCH=BRANCH;c=PacedTransport();head=c.branch_head()
                audit=json.loads(c.blob_from_commit(head,BASE+'/raw_audit.json'))
                measurement=json.loads(c.blob_from_commit(head,BASE+'/measurement.json'))
                if audit['status']!='PASS' or audit['groups']!=636 or audit['metric_coverage']!={'metrics_raw':636,'metrics_by_asset':7632,'metrics':8268}:
                    raise RuntimeError('final raw/metric coverage audit incomplete')
                if measurement['scope']!=scope:raise RuntimeError('delivery scope differs from pinned source')
                delivery={'status':'STAGE1_RAW_COMPLETE_LEAD_REVIEW_PENDING','branch':BRANCH,
                    'run_id':'stage1-singletons-v1','source_commit':args.source,'verified_parent':head,
                    'audit_fixed_head':audit['fixed_head'],'workspace_bytes':workspace_bytes,'coverage_groups':636,'settings':52,'assets':12,'windows':12,
                    'financial_report':'Lead review pending','pairs_triples':'NOT RUN'}
                receipt=record(root,'stage1 evidence delivered','Raw trades independently rebuilt; derived table coverage complete. Lead financial/inferential review pending.',
                    {BASE+'/delivery.json':json.dumps(delivery,indent=2).encode(),BASE+'/environment.json':json.dumps(admission,indent=2).encode(),
                     BASE+'/HANDOFF.md':b'Stage 1 raw evidence and table coverage complete. Lead audits financial values before the next stage. No adoption verdict.\n'})
                print(json.dumps({'status':delivery['status'],'verified_remote_commit':receipt['head']},indent=2));return
            command=[sys.executable,'-m','l0084_entry_mix_r1.stage1']+(['--synthetic'] if name=='synthetic' else ['--mode',name])
            run_checked(name,command,env,root)
            if not args.preflight_only:
                record(root,'stage1 '+name+' passed',name+' exited 0 under pinned scope; continue only this stage.')
        gated_steps(run,args.preflight_only)
        if args.preflight_only:print('PREFLIGHT_PASS_MARKET_NOT_RUN',flush=True)
        return 0
    except Exception as exc:
        error=str(exc);token=os.environ.get('GH_TOKEN','')
        if token:error=error.replace(token,'[REDACTED]')
        (root/'last_error.txt').write_text(error)
        if not args.preflight_only:
            try:record(root,'stage1 execution interrupted',error,{BASE+'/last_error.txt':error.encode()})
            except Exception as publish_error:print('STATUS_UPLOAD_ERROR '+str(publish_error),file=sys.stderr)
        raise


if __name__=='__main__':raise SystemExit(main())
