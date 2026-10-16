"""Single sequential GitHub work-branch publisher; no credentials in output."""
from pathlib import Path
import base64,hashlib,importlib.util,json,re,time,datetime,sys,urllib.parse
ROOT=Path(__file__).resolve().parent.parent;OUT=Path(__file__).resolve().parent
REPO='stevearagonno1/NOVA-DRAGON';BRANCH='agent/btc-causal-measures-2026-10-15';PREFIX='research/session-work-archive-2026-10-16'
spec=importlib.util.spec_from_file_location('existing_delivery',ROOT/'entry_signal_prep/delivery.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
private=(ROOT/'causal_features_prep/PRIVATE-BTC-CAUSAL-R3-55cbdbce.md').read_text()
match=re.search(r'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}',private)
if not match:raise RuntimeError('Owner-authorised private credential unavailable')
api=module.API(match.group());base='/repos/'+REPO
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def ref():return api.call('GET',base+'/git/ref/heads/'+urllib.parse.quote(BRANCH,safe=''))['object']['sha']
def commit_files(head,mapping,message,cache):
    parent=api.call('GET',base+'/git/commits/'+head);entries=[];expected=[]
    for remote,p in mapping.items():
        b=p.read_bytes();h=sha(b);blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        expected.append({'path':remote,'bytes':len(b),'sha256':h,'blob_sha':blob})
        try:text=b.decode('utf-8')
        except UnicodeDecodeError:text=None
        if text is not None and len(b)<2_000_000:
            entries.append({'path':remote,'mode':'100644','type':'blob','content':text})
        else:
            if cache.get(h)!=blob:
                got=api.call('POST',base+'/git/blobs',{'content':base64.b64encode(b).decode(),'encoding':'base64'})['sha'];assert got==blob
                cache[h]=got;write('UPLOAD-CHECKPOINT.json',cache)
                print('blob_uploaded',p.name,len(b),flush=True)
            entries.append({'path':remote,'mode':'100644','type':'blob','sha':blob})
    tree=api.call('POST',base+'/git/trees',{'base_tree':parent['tree']['sha'],'tree':entries})['sha']
    commit=api.call('POST',base+'/git/commits',{'parents':[head],'tree':tree,'message':message})['sha']
    assert ref()==head,'Work branch changed; inspect before retry'
    api.call('PATCH',base+'/git/refs/heads/'+urllib.parse.quote(BRANCH,safe=''),{'sha':commit,'force':False})
    return commit,expected
def main():
    initial=ref();assert initial=='b21539cb23455046ef62b58236adb288e0dfc619','Inspect unexpected work-branch head before publishing'
    mapping={}
    names=['README_AR.md','WORK-PLAN_AR.md','CORRECTIONS_AR.md','RESTORE_AR.md','CATALOG-AUDIT.json','WORKSPACE-MANIFEST.json','TASK-PLAN.json','build_archive.py','verify_catalog.py','restore_workspace.py','publish_archive.py']
    for n in names:mapping[PREFIX+'/'+n]=OUT/n
    for p in (OUT/'original-catalog').rglob('*'):
        if p.is_file():mapping[PREFIX+'/'+p.relative_to(OUT).as_posix()]=p
    manifest=json.loads((OUT/'WORKSPACE-MANIFEST.json').read_text())
    for item in manifest['parts']:mapping[PREFIX+'/'+item['name']]=OUT/item['name']
    mapping[PREFIX+'/NOVA-all-originals-and-independent-versions.zip']=ROOT/'upload/NOVA-all-originals-and-independent-versions (1).zip'
    mapping[PREFIX+'/NOVA-MARKET-STATE-DICTIONARY-V1_AR.md']=ROOT/'deliverables/NOVA-MARKET-STATE-DICTIONARY-V1_AR.md'
    mapping[PREFIX+'/state-dictionary-v1.json']=ROOT/'btc_comprehensive_prep/state-dictionary-v1.json'
    for p in (OUT/'repository-updates').rglob('*'):
        if p.is_file():mapping[p.relative_to(OUT/'repository-updates').as_posix()]=p
    pattern=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
    for remote,p in mapping.items():assert not pattern.search(p.read_bytes()),'Credential scan blocked '+remote
    cache=json.loads((OUT/'UPLOAD-CHECKPOINT.json').read_text()) if (OUT/'UPLOAD-CHECKPOINT.json').exists() else {}
    commit,expected=commit_files(initial,mapping,'Preserve full owner indicator catalog, state dictionary and session work',cache)
    write('PUBLISHED-COMMIT.json',{'commit':commit,'branch':BRANCH,'files':expected,'status':'UPLOADED_READBACK_PENDING'})
    for item in expected:
        got=api.call('GET',base+'/git/blobs/'+item['blob_sha']);b=base64.b64decode(got['content']);assert len(b)==item['bytes'] and sha(b)==item['sha256'],item['path']
        print('verified',item['path'],flush=True)
    assert ref()==commit
    now=datetime.datetime.now(datetime.timezone.utc);start=datetime.datetime.fromisoformat('2026-10-16T12:28:51+00:00')
    receipt={'status':'PUBLIC_SESSION_WORK_ARCHIVED_AND_IMMUTABLE_BYTES_VERIFIED','commit':commit,'branch':BRANCH,'base_commit':initial,'files_verified':expected,'snapshot_unique_files':manifest['unique_files_in_archive'],'snapshot_duplicate_paths':manifest['duplicate_paths'],'snapshot_parts':len(manifest['parts']),'private_papers_excluded':manifest['excluded_private_papers'],'damaged_archives_excluded':[x for x in manifest['entries'] if x['status']=='excluded_damaged_archive_not_safely_inspectable'],'credentials_published':False,'full_market_run':False,'universal_execution_paper_ready':False,'completed_utc':now.isoformat(),'elapsed_since_owner_submission_seconds':(now-start).total_seconds(),'exact_first_tool_start':'not measured','compute_only_seconds':'not measured — preservation task','main_changed':False,'merge_or_pr':False,'workspace_bytes_including_existing_files':sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()),'workspace_limit_status':'existing workspace already above125MB before preservation; no files deleted; snapshot adds preservation copies; not an executor-budget PASS'}
    write('VERIFIED-DELIVERY.json',receipt)
    final,extra=commit_files(commit,{PREFIX+'/VERIFIED-DELIVERY.json':OUT/'VERIFIED-DELIVERY.json'},'Record verified session archive delivery',cache)
    got=api.call('GET',base+'/git/blobs/'+extra[0]['blob_sha']);assert sha(base64.b64decode(got['content']))==extra[0]['sha256']
    assert ref()==final
    main=api.call('GET',base+'/git/ref/heads/main')['object']['sha'];assert main=='6d0226a03b84656e14b94dd8a37e39332cc2f68f'
    final_receipt={'status':'PASS','commit':final,'content_commit':commit,'branch':BRANCH,'files_verified':len(expected)+1,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'main_unchanged':True,'url':'https://github.com/'+REPO+'/tree/'+final+'/'+PREFIX}
    write('FINAL-DELIVERY.json',final_receipt);print(json.dumps(final_receipt),flush=True)
if __name__=='__main__':main()
