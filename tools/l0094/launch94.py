"""Prepared foreground sequence; no code repair or scope change by executor."""
from pathlib import Path
import argparse,base64,fcntl,hashlib,json,os,sys,time,zipfile
import run94 as R
import publish85 as P

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fixture-only',action='store_true');ap.add_argument('--out',default='nova-l0094');args=ap.parse_args()
    root=Path(args.out).resolve();root.mkdir(parents=True,exist_ok=True);lock=(root/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    started=root/'started.json'
    if not started.exists():R.write(started,{'time':time.time(),'estimate_minutes':[10,30],'estimate_includes_setup_audit_publication':True})
    def guard():
        used=sum(p.stat().st_size for p in Path.cwd().rglob('*') if p.is_file() and not p.is_symlink())
        if used>125000000:raise RuntimeError('workspace exceeds125000000:'+str(used))
        return used
    guard();R.execute(root/'synthetic',True,stop_after=1);R.execute(root/'synthetic',True)
    before=(root/'synthetic/selection.json').read_bytes();R.execute(root/'synthetic',True);assert before==(root/'synthetic/selection.json').read_bytes()
    checkpoint=root/'synthetic/checkpoint.json';saved=checkpoint.read_bytes();obj=json.loads(saved);obj['raw_sha256']='tampered';checkpoint.write_text(json.dumps(obj))
    try:
        try:R.execute(root/'synthetic',True)
        except AssertionError:pass
        else:raise RuntimeError('tamper test failed')
    finally:checkpoint.write_bytes(saved)
    R.write(root/'readiness.json',dict(status='PASS',fixture_rows=51,fixture_period_evaluations=459,resume=True,tamper=True,market='NOT RUN' if args.fixture_only else 'PENDING'))
    if args.fixture_only:print('PREFLIGHT_PASS; MARKET NOT RUN');return
    P.BRANCH=R.BRANCH
    source=json.loads((R.ROOT/'source.json').read_text());base=source['base_main']
    try:head=P.api('/git/ref/heads/'+R.BRANCH)['object']['sha']
    except RuntimeError as e:
        if 'HTTP 404' not in str(e):raise
        head=P.api('/git/refs','POST',{'ref':'refs/heads/'+R.BRANCH,'sha':base})['object']['sha']
    # A prior complete or admission delivery is read before any writes. One publisher only.
    admission=R.DEST+'/readiness/source.json'
    try:present=P.get_file(head,admission)
    except RuntimeError as e:
        if 'HTTP 404' not in str(e):raise
        present=None
    proof=(R.ROOT/'source.json').read_bytes()
    if present is None:
        if head!=base:raise RuntimeError('unexpected branch before source admission')
        fixturezip=root/'fixture.zip'
        with zipfile.ZipFile(fixturezip,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('readiness.json',(root/'readiness.json').read_bytes())
        files={admission:proof,R.DEST+'/readiness/fixture.zip':fixturezip.read_bytes()}
        for f in R.ROOT.iterdir():
            if f.is_file():files['tools/l0094/'+f.name]=f.read_bytes()
        files['docs/journal/2026-10-07-l0094-singletons/002-admission.md']=b'- Decision:follow frozen singleton scope.\n- Executed:fixture,resume,tamper and source archive upload/readback.\n- Produced:tools/l0094 and admission proof.\n- Next:measure,audit and deliver;no triples or adoption.\n'
        head=P.publish(files,'L0094: pinned source and synthetic admission',head)
    else:assert present==proof,'different source on branch'
    receiptpath=R.DEST+'/delivery.json'
    try:prior=json.loads(P.get_file(head,receiptpath))
    except RuntimeError as e:
        if 'HTTP 404' not in str(e):raise
        prior=None
    if prior:
        archive=base64.b64decode(P.api('/git/blobs/'+prior['archive_git_sha'])['content']);assert hashlib.sha256(archive).hexdigest()==prior['archive_sha256']
        assert prior['source_sha256']==hashlib.sha256(proof).hexdigest()
        print('VERIFIED_COMPLETE');return
    R.execute(root/'market',False);guard()
    archive=root/'evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted((root/'market').iterdir()):
            if f.is_file():
                info=zipfile.ZipInfo(f.name,(2026,10,7,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,f.read_bytes())
    elapsed=time.time()-json.loads(started.read_text())['time']
    audit=json.loads((root/'market/audit.json').read_text())
    receipt=dict(status='DISCOVERY_COMPLETE_LEAD_REVIEW_PENDING',source_sha256=hashlib.sha256(proof).hexdigest(),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),archive_bytes=archive.stat().st_size,archive_git_sha=P.blob_sha(archive.read_bytes()),settings=482,candidates=348245,pair_variants=347763,rows=348245,asset_evaluations=1044735,period_evaluations=3134205,elapsed_before_final_upload_seconds=elapsed,full_task_through_readback_seconds='recorded in remote-delivery local receipt after readback;not included in this pre-upload receipt',compute_seconds=audit['compute_seconds'],workspace_bytes=guard(),adoption='NOT AUTHORISED')
    files={R.DEST+'/evidence.zip':archive.read_bytes(),receiptpath:(json.dumps(receipt,indent=2)+'\n').encode(),R.DEST+'/REPORT.md':(root/'market/REPORT.md').read_bytes(),R.DEST+'/audit.json':(root/'market/audit.json').read_bytes(),R.DEST+'/selection.json':(root/'market/selection.json').read_bytes(),R.DEST+'/analysis.json':(root/'market/analysis.json').read_bytes(),
           'LOG.md':P.get_file(head,'LOG.md')+b'\n\n## L0094 singleton survey\n482parents+347763pair variants/348245candidate rows/3134205period evaluations;independent matching PASS. Historical discovery only;Lead review pending,no triples,trading or adoption.\n',
           'docs/journal/2026-10-07-l0094-singletons/003-complete.md':b'- Decision:run singleton discovery only.\n- Executed:all115921pairs in3modes plus482parents on3assets/3periods;scalar matching and causal prefixes checked.\n- Produced:raw masks,all rows,selection,report,analysis,audit,verified upload.\n- Next:Lead review;no automatic mixtures or main merge.\n'}
    commit=P.publish(files,'L0094: complete singleton discovery for Lead review',head)
    receipt.update(verified_remote=True,commit=commit,full_task_through_readback_seconds=time.time()-json.loads(started.read_text())['time'])
    R.write(root/'remote-delivery.json',receipt)
    # Persist final measured wall time separately; no recursive self-containing commit receipt.
    P.publish({R.DEST+'/remote-delivery.json':(json.dumps(receipt,indent=2)+'\n').encode()},'L0094: verified remote receipt and full elapsed time',commit)
    print('VERIFIED_COMPLETE')
if __name__=='__main__':
    try:main()
    except Exception as e:
        token=os.environ.get('GH_TOKEN','');message=type(e).__name__+': '+str(e)
        if token:message=message.replace(token,'[REDACTED]')
        root=Path('run');root.mkdir(exist_ok=True);(root/'last_error.txt').write_text(message+'\n');print('ERROR: '+message,flush=True);raise SystemExit(1)
