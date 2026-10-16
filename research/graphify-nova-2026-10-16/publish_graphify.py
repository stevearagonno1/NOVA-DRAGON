"""Publish tested Graphify outputs to the dedicated work branch."""
import sys,json,re,base64,datetime,concurrent.futures
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'repository_archive_2026_10_16'))
import publish_archive as p
p.OUT=R;p.BRANCH='agent/graphify-nova-2026-10-16';p.PREFIX='research/graphify-nova-2026-10-16'
def verify(item):
    b=base64.b64decode(p.api.call('GET',p.base+'/git/blobs/'+item['blob_sha'])['content']);assert p.sha(b)==item['sha256'] and len(b)==item['bytes']
def main():
    head=p.ref();assert head=='14be41aafa52f714ec4ad2c11fee472bede69dc7'
    names=['README_AR.md','TASK-PLAN.json','GRAPH-AUDIT.json','SOURCE-FILES.json','SOURCE-AUDIT.json','requirements-graphify.lock.txt','fetch_corpus.py','run_graphify.py','graphify_nova.py','finalize_graph.py','publish_graphify.py','extract.log','cluster.log','QUERY-EXAMPLE.txt','RUN.json','GRAPHIFY-OUTPUTS.zip']
    files={p.PREFIX+'/'+n:R/n for n in names}
    for n in ['GRAPH_REPORT.md','graph.html']:files[p.PREFIX+'/graphify-out/'+n]=R/'graphify-out'/n
    files['tools/graphify_nova.py']=R/'graphify_nova.py';files['.graphifyignore']=R/'.graphifyignore'
    for f in (R/'updates').rglob('*'):
        if f.is_file():files[f.relative_to(R/'updates').as_posix()]=f
    pattern=re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')
    assert all(not pattern.search(f.read_bytes()) for f in files.values())
    commit,expected=p.commit_files(head,files,'Apply Graphify code graph with reproducible coverage and source warnings',{})
    p.write('PUBLISHED.json',{'commit':commit,'files':expected})
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(verify,expected))
    now=datetime.datetime.now(datetime.timezone.utc);audit=json.loads((R/'GRAPH-AUDIT.json').read_text())
    receipt={'status':'GRAPHIFY_CODE_GRAPH_PUBLISHED_VERIFIED_WITH_DECLARED_LIMITS','commit':commit,'branch':p.BRANCH,'files_verified':expected,'audit':audit,'elapsed_until_payload_readback_seconds':(now-datetime.datetime.fromisoformat('2026-10-16T12:50:30+00:00')).total_seconds(),'compute_seconds':json.loads((R/'RUN.json').read_text())['seconds'],'completed_utc':now.isoformat(),'main_changed':False,'semantic_full_repo_graph':False}
    p.write('DELIVERY.json',receipt)
    final,extra=p.commit_files(commit,{p.PREFIX+'/DELIVERY.json':R/'DELIVERY.json'},'Record verified Graphify integration delivery',{})
    for item in extra:verify(item)
    assert p.ref()==final
    assert p.api.call('GET',p.base+'/git/ref/heads/main')['object']['sha']=='6d0226a03b84656e14b94dd8a37e39332cc2f68f'
    result={'status':'PASS_WITH_DECLARED_SOURCE_WARNINGS','commit':final,'content_commit':commit,'branch':p.BRANCH,'files_verified':len(expected)+len(extra),'url':'https://github.com/'+p.REPO+'/tree/'+final+'/'+p.PREFIX,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    p.write('FINAL-DELIVERY.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
