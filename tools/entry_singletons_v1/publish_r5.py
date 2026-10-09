"""R5 publisher: in-memory evidence ZIP, pre-write gate, one lease-checked batch, immutable readback, receipt commit.

No local ZIP, no market data, no main/PR/merge. Token is read only from the GH_TOKEN process environment.
"""
import base64,csv,gzip,hashlib,io,json,os,re,zipfile
from pathlib import PurePosixPath
from pathlib import Path
from .run import WORKSPACE,PACKAGE,RESULT_FIELDS,workspace_bytes,write_budgeted,_category,CATEGORY_LIMITS,MAX_WORKSPACE,MAX_TASK_OUTPUT,BASE_WORKSPACE_BYTES
from .publish import (GitHub,ApiError,WriteOutcomeUnknown,_zip_in_memory,_safe_payload_scan,_read_text_api,BRANCH,BASE,EVIDENCE,_combined_alerts,build_package_payload)
from .gate import RUN_DIR,RUN_ID

JOURNAL='docs/journal/2026-10-08-entry-singletons-package-v1/'
RUN_NAME='run-r4'
ARCHIVE_NAMES=['fixture-generator.py','fixture-runner.py','independent-audit.py','scope.json','registry.json','checksums.json',
 'run-manifest.json','fixtures-results.csv','audit.json','quality-tests.json','runtime.json','commands.log','PREPARATION-REPORT.md',
 'fixture-alerts.csv','masks-BTC.bin.gz','masks-ETH.bin.gz','masks-SOL.bin.gz','resume-audit.json','tamper-audit.json','secret-scan.json']
MAX_ZIP=8_000_000

def _sha(b):return hashlib.sha256(b).hexdigest()
def _json(obj):return (json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()

def redact_paper(text,token):
    """Replace the owner token value and any token-shaped strings; keep all other paper text intact."""
    out=text
    if token:out=out.replace(token,'[REDACTED]')
    out=re.sub(r'github_pat_[A-Za-z0-9_]{22,}|gh[pousr]_[A-Za-z0-9]{36,}','[REDACTED]',out)
    return out

def _check_members(entries):
    for name in entries:
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or name!=str(p):raise ValueError(f'unsafe archive member name: {name}')

def build_archive(workspace,run_dir,tests_result,commands_log):
    run=Path(run_dir);pkg=Path(workspace)/'tools/entry_singletons_v1'
    e={'fixture-generator.py':(pkg/'fixture_generator.py').read_bytes(),'fixture-runner.py':(pkg/'run.py').read_bytes(),
       'independent-audit.py':(pkg/'audit.py').read_bytes(),'scope.json':(pkg/'scope.json').read_bytes(),
       'registry.json':(pkg/'registry.json').read_bytes(),'checksums.json':(pkg/'checksums.json').read_bytes(),
       'run-manifest.json':(run/'run-manifest.json').read_bytes(),'fixtures-results.csv':(run/'fixtures-results.csv').read_bytes(),
       'audit.json':(run/'audit.json').read_bytes(),'quality-tests.json':_json(tests_result),
       'runtime.json':(run/'runtime.json').read_bytes(),'commands.log':commands_log,
       'PREPARATION-REPORT.md':(run/'PREPARATION-REPORT.md').read_bytes()}
    alerts,n=_combined_alerts(run);e['fixture-alerts.csv']=alerts
    for a in ('BTC','ETH','SOL'):e[f'masks-{a}.bin.gz']=(run/f'asset-{a}-masks.bin.gz').read_bytes()
    for name in ('resume-audit.json','tamper-audit.json','secret-scan.json'):e[name]=(run/name).read_bytes()
    _check_members(e)
    art_manifest={'members':{k:{'bytes':len(v),'sha256':_sha(v)} for k,v in sorted(e.items())},
                  'exception':'artifact-manifest.json excludes itself to avoid a self-hash'}
    e['artifact-manifest.json']=_json(art_manifest)
    pkg_audit={'members_expected':ARCHIVE_NAMES+['artifact-manifest.json','package-audit.json'],'members_present_before_package_audit':sorted(e),
               'excluded_from_hash':['package-audit.json (self)','artifact-manifest.json (self)'],'duplicate_names':False}
    e['package-audit.json']=_json(pkg_audit)
    zb=_zip_in_memory(e)
    if len(zb)>MAX_ZIP:raise OSError(f'in-memory evidence ZIP exceeds 8MB: {len(zb)}')
    with zipfile.ZipFile(io.BytesIO(zb)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('duplicate ZIP members')
        for name in names:
            if z.read(name)!=e[name]:raise ValueError(f'ZIP member bytes differ: {name}')
        missing=[n_ for n_ in ARCHIVE_NAMES+['artifact-manifest.json','package-audit.json'] if n_ not in names]
        if missing:raise ValueError(f'ZIP missing members: {missing}')
    return zb,e,n

def build_payloads(workspace,run_dir,archive_entries,zip_bytes,tests_result):
    ws=Path(workspace);docs=ws/'docs/research/entry-singletons-package-v1-2026-10-08';run=Path(run_dir)
    code=build_package_payload()
    evid={}
    for p in sorted(docs.iterdir()):
        if p.is_file():evid[f'{EVIDENCE}/{p.name}']=p.read_bytes()
    evid[f'{EVIDENCE}/fixtures-results.csv']=(run/'fixtures-results.csv').read_bytes()
    evid[f'{EVIDENCE}/fixture-alerts.csv']=archive_entries['fixture-alerts.csv']
    for name in ('audit.json','run-manifest.json','runtime.json','resume-audit.json','tamper-audit.json','secret-scan.json'):
        evid[f'{EVIDENCE}/{name}']=(run/name).read_bytes()
    for a in ('BTC','ETH','SOL'):evid[f'{EVIDENCE}/masks-{a}.bin.gz']=(run/f'asset-{a}-masks.bin.gz').read_bytes()
    evid[f'{EVIDENCE}/evidence.zip']=zip_bytes
    evid[f'{EVIDENCE}/preserved-r3/fixtures-results.r3.csv.gz']=(ws/'run/preserved-r3/fixtures-results.r3.csv.gz').read_bytes()
    evid[f'{EVIDENCE}/preserved-r3/preservation-r3.json']=(ws/'run/preserved-r3/preservation-r3.json').read_bytes()
    return code,evid

def main(argv=None):
    import argparse
    ap=argparse.ArgumentParser(description='R5 publisher. Default: dry gate only. --publish performs the remote batch.')
    ap.add_argument('--publish',action='store_true')
    a=ap.parse_args(argv)
    ws=WORKSPACE;run=ws/RUN_NAME
    tests=json.loads((run/'quality-tests.json').read_text(encoding='utf-8'))
    commands=(run/'commands.log').read_bytes()
    zb,entries,alerts_n=build_archive(ws,run,tests,commands)
    code,evid=build_payloads(ws,run,entries,zb,tests)
    # Secret gate: payloads and every ZIP member, exact value and shape.
    token=os.environ.get('GH_TOKEN','')
    _safe_payload_scan({**code,**evid},token)
    with zipfile.ZipFile(io.BytesIO(zb)) as z:
        _safe_payload_scan({n_:z.read(n_) for n_ in z.namelist()},token)
    gate={'zip_bytes':len(zb),'zip_sha256':_sha(zb),'zip_members':len(entries),'fixture_alert_rows':alerts_n,'secret_gate':'PASS'}
    print(json.dumps(gate,sort_keys=True))
    if not a.publish:return 0
    api=GitHub(token)
    head=api.branch_head()
    # Ancestry and package-path checks before any write. Branch may be an ancestor of BASE chain only.
    c=api.json('GET','/git/commits/'+head);seen=[];cur=c
    for _ in range(12):
        seen.append(cur['sha'])
        if BASE in seen:break
        if not cur['parents']:break
        cur=api.json('GET','/git/commits/'+cur['parents'][0]['sha'])
    if BASE not in seen:raise ApiError('remote branch does not descend from pinned tools base; stop without overwrite')
    tree=api.json('GET','/git/trees/'+c['tree']['sha']+'?recursive=1')
    if tree.get('truncated') or any(x.get('path','').startswith('tools/entry_singletons_v1') for x in tree.get('tree',[])):
        raise ApiError('remote branch already contains package path or truncated tree; stop without overwrite')
    # Read existing text files at the lease head, then batch all payloads in one tree.
    log=_read_text_api(api,'LOG.md',head).decode('utf-8')
    handoff=_read_text_api(api,'docs/HANDOFF.md',head).decode('utf-8')
    log+=f"\n\n## 2026-10-08 — Entry singletons package R4/R5\n- Status: batch published; receipt pending immutable readback.\n- Run `{RUN_ID}` in `run-r4/`; R3 CSV copies replaced by one verified gzip under `preserved-r3/`.\n- `market_run=false`; synthetic fixture only; no August or market claim.\n- Evidence: `{EVIDENCE}/`.\n"
    handoff+=f"\n\n## Entry singletons R4/R5 — 2026-10-08\n**State:** batch pending receipt. **Limits:** synthetic only; no market run; no performance claim.\n"
    tickets={JOURNAL+'010-r4-publish-gate.md':'# 010 — R4 publish gate\n\n- Publisher credential scanner now matches credential shapes and exact value; no path exemption.\n',
             JOURNAL+'011-r4-resume-tamper.md':'# 011 — R4 resume and tamper\n\n- See resume-audit.json and tamper-audit.json in the evidence directory.\n',
             JOURNAL+'012-r4-delivery.md':'# 012 — R4 delivery\n\n- Superseded by R5 batch; see 015.\n',
             JOURNAL+'013-r5-lossless-storage.md':'# 013 — R5 lossless storage\n\n- Two identical R3 CSV copies replaced by one verified gzip; manifest in preserved-r3/.\n',
             JOURNAL+'014-r5-acceptance.md':'# 014 — R5 acceptance\n\n- Acceptance results are in the evidence audits listed in the receipt.\n',
             JOURNAL+'015-r5-delivery.md':'# 015 — R5 delivery\n\n- Batch commit then receipt commit; readback reported only after verification.\n'}
    batch={**code,**evid,'LOG.md':log.encode(),'docs/HANDOFF.md':handoff.encode(),**{k:v.encode() for k,v in tickets.items()}}
    _safe_payload_scan(batch,token)
    if workspace_bytes()>MAX_WORKSPACE:raise OSError('workspace ceiling exceeded before publication')
    if workspace_bytes()-BASE_WORKSPACE_BYTES>MAX_TASK_OUTPUT:raise OSError('R5 local output cap exceeded before publication')
    if api.branch_head()!=head:raise ApiError('lease changed before batch tree')
    btree=api.tree(c['tree']['sha'],batch)
    bcommit=api.commit(btree,head,'Add synthetic-only entry singletons package R4/R5 batch')
    try:api.json('PATCH','/git/refs/heads/'+BRANCH,{'sha':bcommit,'force':False})
    except WriteOutcomeUnknown:
        if api.branch_head()!=bcommit:raise
    if api.branch_head()!=bcommit:raise ApiError('lease failed after batch publication')
    read_paths=api.readback(bcommit,batch)
    receipt={'status':'PACKAGE_READY_LEAD_REVIEW_PENDING','verified_remote':True,'immutable_code_commit':bcommit,'immutable_evidence_commit':bcommit,
             'archive_sha256':gate['zip_sha256'],'archive_bytes':gate['zip_bytes'],'readback_paths':len(read_paths),
             'final_receipt_publication_excluded':True,'market_run':False,'synthetic':True}
    rb=_json(receipt)
    rc=api.tree(api.json('GET','/git/commits/'+bcommit)['tree']['sha'],{f'{EVIDENCE}/remote-delivery.json':rb})
    rcommit=api.commit(rc,bcommit,'Record verified immutable R4/R5 readback receipt')
    try:api.json('PATCH','/git/refs/heads/'+BRANCH,{'sha':rcommit,'force':False})
    except WriteOutcomeUnknown:
        if api.branch_head()!=rcommit:raise
    if api.branch_head()!=rcommit:raise ApiError('lease failed after receipt')
    api.readback(rcommit,{**batch,f'{EVIDENCE}/remote-delivery.json':rb})
    out={'status':'PACKAGE_READY_LEAD_REVIEW_PENDING','branch':BRANCH,'batch_commit':bcommit,'receipt_commit':rcommit,'archive_sha256':gate['zip_sha256'],'readback_paths':len(read_paths)}
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=='__main__':raise SystemExit(main())
