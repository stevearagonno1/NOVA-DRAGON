"""Publish ledger and additive records, then verify immutable bytes."""
import json,re,base64,datetime,concurrent.futures
import publish_archive as p
def verify(item):
    b=base64.b64decode(p.api.call('GET',p.base+'/git/blobs/'+item['blob_sha'])['content'])
    assert len(b)==item['bytes'] and p.sha(b)==item['sha256'],item['path']
def main():
    head=p.ref();assert head=='5df0d0ac38db0f83176368c380cb113f03ce70e4'
    files={}
    for name in ['REQUEST-EXECUTION-LEDGER_AR.md','REQUEST-EXECUTION-LEDGER.json','build_request_ledger.py','REQUEST-LEDGER-PROVENANCE.json','publish_request_ledger.py']:
        files[p.PREFIX+'/'+name]=p.OUT/name
    for f in (p.OUT/'ledger-updates').rglob('*'):
        if f.is_file():files[f.relative_to(p.OUT/'ledger-updates').as_posix()]=f
    pattern=re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')
    assert all(not pattern.search(f.read_bytes()) for f in files.values())
    commit,expected=p.commit_files(head,files,'Record owner requests against actual execution and evidence',{})
    p.write('REQUEST-LEDGER-PUBLISHED.json',{'commit':commit,'files':expected})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(verify,expected))
    now=datetime.datetime.now(datetime.timezone.utc)
    d=json.loads((p.OUT/'REQUEST-EXECUTION-LEDGER.json').read_text())
    receipt={'status':'REQUEST_LEDGER_PUBLISHED_AND_IMMUTABLE_BYTES_VERIFIED','commit':commit,'parent':head,'branch':p.BRANCH,'request_entries':len(d['requests']),'status_counts':d['status_counts'],'files_verified':expected,'scope':'semantic ledger of requests visible in conversation; repeated messages consolidated, not verbatim','whole_task_elapsed_until_payload_readback_seconds':(now-datetime.datetime.fromisoformat('2026-10-16T12:42:45+00:00')).total_seconds(),'completed_utc':now.isoformat(),'prework_estimate':'not recorded before first operation','new_market_test':False,'comprehensive_paper_ready':False,'credentials_published':False}
    p.write('REQUEST-LEDGER-DELIVERY.json',receipt)
    final,more=p.commit_files(commit,{p.PREFIX+'/REQUEST-LEDGER-DELIVERY.json':p.OUT/'REQUEST-LEDGER-DELIVERY.json'},'Record verified request-ledger delivery',{})
    for item in more:verify(item)
    assert p.ref()==final
    assert p.api.call('GET',p.base+'/git/ref/heads/main')['object']['sha']=='6d0226a03b84656e14b94dd8a37e39332cc2f68f'
    result={'status':'PASS','commit':final,'content_commit':commit,'request_entries':len(d['requests']),'files_verified':len(expected)+len(more),'url':'https://github.com/'+p.REPO+'/blob/'+final+'/'+p.PREFIX+'/REQUEST-EXECUTION-LEDGER_AR.md','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    p.write('REQUEST-LEDGER-FINAL.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
