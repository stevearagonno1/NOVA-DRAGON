"""Resume verification after prepared tree was published via GitHub connector."""
import publish_graphify as g
import datetime,json,concurrent.futures
p=g.p;R=g.R
commit='b8a7e5ae93aa82ff5bfd58cd036ab70a20cf50f6'
expected=json.loads((R/'EXPECTED.json').read_text())
assert p.ref()==commit
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(g.verify,expected))
now=datetime.datetime.now(datetime.timezone.utc)
receipt={'status':'GRAPHIFY_CODE_GRAPH_IMMUTABLE_BYTES_VERIFIED','commit':commit,'branch':p.BRANCH,'files_verified':expected,'audit':json.loads((R/'GRAPH-AUDIT.json').read_text()),'elapsed_until_payload_readback_seconds':(now-datetime.datetime.fromisoformat('2026-10-16T12:50:30+00:00')).total_seconds(),'compute_seconds':json.loads((R/'RUN.json').read_text())['seconds'],'completed_utc':now.isoformat(),'estimate_exceeded':True,'publication_resume':'Single Python publisher interrupted before ref update; existing uploaded ZIP blob reused in prepared tree; GitHub connector committed/ref-updated; independent readbacks resumed here','semantic_full_repo_graph':False,'main_changed':False,'no_merge_or_pr':True,'source_code_not_executed':True}
p.write('DELIVERY.json',receipt)
final,extra=p.commit_files(commit,{p.PREFIX+'/DELIVERY.json':R/'DELIVERY.json',p.PREFIX+'/verify_delivery.py':R/'verify_delivery.py'},'Record verified Graphify graph delivery',{})
for item in extra:g.verify(item)
assert p.ref()==final
assert p.api.call('GET',p.base+'/git/ref/heads/main')['object']['sha']=='6d0226a03b84656e14b94dd8a37e39332cc2f68f'
result={'status':'PASS_WITH_DECLARED_SOURCE_WARNINGS','commit':final,'content_commit':commit,'branch':p.BRANCH,'files_verified':len(expected)+len(extra),'url':'https://github.com/'+p.REPO+'/tree/'+final+'/'+p.PREFIX,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
p.write('FINAL-DELIVERY.json',result);print(json.dumps(result),flush=True)
