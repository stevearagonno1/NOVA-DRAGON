"""Resume published snapshot verification with parallel independent reads."""
import concurrent.futures,datetime,json,base64,time
import publish_archive as p
def verify(item):
    got=p.api.call('GET',p.base+'/git/blobs/'+item['blob_sha']);b=base64.b64decode(got['content'])
    assert len(b)==item['bytes'] and p.sha(b)==item['sha256'],item['path']
    return item['path']
def main():
    checkpoint=json.loads((p.OUT/'PUBLISHED-COMMIT.json').read_text());commit=checkpoint['commit'];assert p.ref()==commit
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for name in pool.map(verify,checkpoint['files']):print('verified',name,flush=True)
    manifest=json.loads((p.OUT/'WORKSPACE-MANIFEST.json').read_text());now=datetime.datetime.now(datetime.timezone.utc)
    receipt={'status':'PUBLIC_SESSION_WORK_ARCHIVED_AND_IMMUTABLE_BYTES_VERIFIED','commit':commit,'branch':p.BRANCH,'files_verified':checkpoint['files'],'snapshot_unique_files':manifest['unique_files_in_archive'],'snapshot_duplicate_paths':manifest['duplicate_paths'],'snapshot_parts':len(manifest['parts']),'damaged_archives_excluded':[x for x in manifest['entries'] if x['status']=='excluded_damaged_archive_not_safely_inspectable'],'private_papers_excluded':manifest['excluded_private_papers'],'credentials_published':False,'full_market_run':False,'universal_execution_paper_ready':False,'completed_utc':now.isoformat(),'elapsed_since_owner_submission_seconds':(now-datetime.datetime.fromisoformat('2026-10-16T12:28:51+00:00')).total_seconds(),'exact_first_tool_start':'not measured','main_changed':False,'merge_or_pr':False,'readback_resume':'Sequential verifier safely interrupted after content commit; independent GET reads resumed in parallel; one publisher only','workspace_limit_status':'Existing workspace exceeded125MB before preservation; no deletion; not an executor-budget PASS'}
    p.write('VERIFIED-DELIVERY.json',receipt)
    tick=p.OUT/'FINAL-TICK.md';tick.write_text('القرار: توثيق اكتمال رفع أعمال الجلسة دون تغيير نطاق البحث.\nالتنفيذ: التحقق من بصمات جميع الملفات المنشورة وقراءة إيصال التسليم من التزام ثابت.\nالناتج: الأرشيف الأصلي وقاموس الحالات والخطة وملفات العمل محفوظة؛ لا نتائج سوق أو جاهزية شاملة جديدة.\nالتالي: مطابقة المخزون الكامل بالحسابات السابقة وإكمال نواقص الجاهزية.\n')
    mapping={p.PREFIX+'/VERIFIED-DELIVERY.json':p.OUT/'VERIFIED-DELIVERY.json',p.PREFIX+'/finish_verification.py':p.OUT/'finish_verification.py','docs/journal/2026-10-16-session-work-archive/002-verified-delivery.md':tick}
    final,expected=p.commit_files(commit,mapping,'Record immutable session archive verification',{})
    for item in expected:verify(item)
    assert p.ref()==final
    assert p.api.call('GET',p.base+'/git/ref/heads/main')['object']['sha']=='6d0226a03b84656e14b94dd8a37e39332cc2f68f'
    result={'status':'PASS','commit':final,'content_commit':commit,'branch':p.BRANCH,'files_verified':len(checkpoint['files'])+len(expected),'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':'https://github.com/'+p.REPO+'/tree/'+final+'/'+p.PREFIX,'main_unchanged':True}
    p.write('FINAL-DELIVERY.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
