"""Prepare exact work-branch publishing payload; performs no network or trading."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,os,sys,time,zipfile,io
import specialist as S
ROOT=Path(__file__).resolve().parent
DEST='history/research/hyp_lab_out/BTC-STATE-SPECIALIST-R2-2026-10-20/'
def build(out,context,code_commit,allow_synthetic=False):
    out=Path(out);ctx=json.loads(Path(context).read_text());S.audit(out)
    cp=json.loads((out/'checkpoint.json').read_text())
    assert not cp['fixture'] or allow_synthetic,'synthetic fixture is not a market delivery'
    assert cp['months']==(['2024-01'] if cp['fixture'] else S.MONTHS)
    files={}
    for item in cp['parts']:
        for k in ['raw','rows']:files[DEST+item[k]]=(out/item[k]).read_bytes()
    for name in ['checkpoint.json','audit.json','results.csv.gz','REPORT_AR.md']:files[DEST+name]=(out/name).read_bytes()
    for name in ['registration.json','grid.json','definitions.json','coverage_scope.json','inputs.json','requirements.txt','package_manifest.json','paper.md','readiness.json']:files[DEST+name]=(ROOT/name).read_bytes()
    elapsed=time.time()-ctx['task_started_epoch']
    assert elapsed>=0
    receipt={'status':'SYNTHETIC_REHEARSAL_ONLY' if cp['fixture'] else 'MEASURED_AUDITED_UPLOAD_PENDING_LEAD_REVIEW','code_commit':code_commit,'source_main':'8af2aae214f65a370110921928eaabf07771a6d1','candidate_records':len(S.grid()),'result_rows':len(cp['months'])*(len(S.grid())+3),'months':cp['months'],'scope':'conditional discovery; no full-stream precision, validation, trading or adoption','elapsed_to_payload_seconds':elapsed,'full_task_elapsed_seconds':'not measured until final verified delivery','compute_only_seconds':ctx.get('compute_only_seconds','not measured'),'workspace_bytes':S.workspace_bytes(os.environ.get('NOVA_WORKSPACE',ROOT.parent)),'code_paths':'tools/btc_state_specialist/','error_policy':'preserve partial evidence and actual error; never claim verified delivery before immutable readback'}
    files[DEST+'DELIVERY.json']=S.encode(receipt)
    docs=ctx['documents'];note='\n\n## 2026-10-18 — BTC state-specialist conditional discovery\n'+receipt['status']+'; '+str(receipt['candidate_records'])+' source-backed BTC version records; '+str(len(cp['months']))+' months and '+str(receipt['result_rows'])+' reconciled rows. Full-stream false alerts, precision, validation, full catalogue/axis sweep and profitability not measured. Evidence: '+DEST+'REPORT_AR.md. Lead independent review pending; no adoption, PR, main push or merge.\n'
    for name in ['LOG.md','docs/DECISIONS.md','docs/HANDOFF.md']:files[name]=(docs[name]+note).encode()
    files['docs/journal/2026-10-18-btc-state-specialist-execution/001-measured-delivery.md']=('القرار: تنفيذ الدفعة المسجلة دون توسيع.\nالتنفيذ: القياس والتدقيق الآلي وإعداد الرفع على فرع العمل.\nالناتج: الأدلة الكاملة؛ انتظار إثبات الوصول الثابت، والدقة العامة غير مقاسة.\nالتالي: إثبات وصول الملفات ثم مراجعة القائد المستقلة.\n').encode()
    # Transport archive retains exact output bytes; no source prices or secrets are introduced.
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name,b in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,18,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
    archive=buf.getvalue();files[DEST+'EVIDENCE.zip']=archive
    payload={'fixture':cp['fixture'],'expected_head':ctx['head'],'base_tree':ctx['tree'],'destination_branch':'agent/btc-state-specialist-results-r2-2026-10-20','code_commit':code_commit,'files':[{'path':name,'encoding':'base64','content':base64.b64encode(b).decode(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()} for name,b in sorted(files.items())],'archive_bytes':len(archive),'archive_sha256':hashlib.sha256(archive).hexdigest()}
    target=out/'publish_payload.json';data=S.encode(payload)
    if S.workspace_bytes(os.environ.get('NOVA_WORKSPACE',ROOT.parent))+len(data)>125000000:raise RuntimeError('125 MB limit before publishing payload')
    target.write_bytes(data);print(json.dumps({'status':'UPLOAD_PAYLOAD_READY','files':len(files),'payload':str(target),'archive_bytes':len(archive)}))
def verify(out,readback):
    out=Path(out);p=json.loads((out/'publish_payload.json').read_text());r=json.loads(Path(readback).read_text());entries={x['path']:x for x in r['tree'] if x['type']=='blob'}
    for item in p['files']:
        actual=entries[item['path']];assert actual['sha']==item['git_blob_sha'] and actual['size']==item['bytes'],item['path']
    assert r['truncated'] is False
    receipt={'status':'SYNTHETIC_TRANSPORT_CHECK_ONLY' if p['fixture'] else 'REMOTE_PAYLOAD_VERIFIED_LEAD_REVIEW_PENDING','fixture':p['fixture'],'payload_commit':r['commit'],'code_commit':p['code_commit'],'files':[{k:x[k] for k in ['path','bytes','sha256','git_blob_sha']} for x in p['files']],'archive_bytes':p['archive_bytes'],'archive_sha256':p['archive_sha256'],'branch':p['destination_branch'],'report_path':DEST+'REPORT_AR.md','independent_lead_review':'pending','no_adoption':True}
    target=out/'VERIFIED_DELIVERY.json'
    if target.exists():
        existing=json.loads(target.read_text())
        if any(existing.get(k)!=v for k,v in receipt.items()):
            raise RuntimeError('existing receipt differs from verified payload')
    else:
        S.jsonout(target,receipt)
    print(json.dumps({'status':receipt['status'],'files':len(p['files'])}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['build','verify']);p.add_argument('--out',required=True);p.add_argument('--context');p.add_argument('--code-commit');p.add_argument('--readback');p.add_argument('--allow-synthetic',action='store_true');a=p.parse_args()
    if a.mode=='build':build(a.out,a.context,a.code_commit,a.allow_synthetic)
    else:verify(a.out,a.readback)

