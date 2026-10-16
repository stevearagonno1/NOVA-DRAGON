from pathlib import Path
import json,collections,sys
import semantic_pipeline as p
w=p.ROOT/'execution';g=json.loads((w/'evidence-graph.json').read_text());inv={r['path']:r for r in json.loads((w/'INVENTORY.json').read_text())};nodes={n['id']:n for n in g['nodes']};errs=[];need=collections.defaultdict(list);counts=collections.Counter()
for e in g['edges']:
 if e['source'] not in nodes or e['target'] not in nodes:errs.append('dangling endpoint')
 if e.get('provenance')=='prior_graphify_code_graph':counts['inherited_AST_edges']+=1;continue
 if e['relation']=='same_bytes_as':
  a=nodes[e['source']]['source_file'];b=nodes[e['target']]['source_file'];assert inv[a]['sha256']==inv[b]['sha256']==e['evidence_quote'];counts['verified_hash_equivalence']+=1
 elif e['relation']=='archive_contains':
  parent=nodes[e['source']]['source_file'];child=nodes[e['target']]['source_file'];assert child.rsplit('!/',1)[0]==parent and child==e['evidence_quote'];assert inv[parent]['status']=='CONTAINER';counts['verified_archive_memberships']+=1
 elif e['relation']=='declares_symbol':counts['AST_to_unchanged_source_links']+=1
 elif e.get('segment_id'):need[e['segment_id']].append(e)
 elif e.get('review_method'):
  relative=e['source_file'].split('WORKSPACE-v2.zip!/',1)[-1];f=p.ROOT.parent/relative;b=f.read_bytes();assert p.digest(b)==inv[e['source_file']]['sha256'];assert e['evidence_quote'] in b.decode('utf-8');counts['lead_curated_exact_quotes']+=1
 else:errs.append('unrecognized evidence type')
found=set()
for name in json.loads((w/'BATCH-MANIFEST.json').read_text()):
 for s in json.loads((w/'batches'/name).read_text()):
  if s['segment_id'] not in need:continue
  found.add(s['segment_id'])
  for e in need[s['segment_id']]:
   if e['source_file']!=s['source_file'] or e['evidence_quote'] not in s['text']:errs.append('source quotation mismatch')
   else:counts['verified_segment_quotes']+=1
if set(need)-found:errs.append('missing segment identities')
if len(nodes)!=len(g['nodes']):errs.append('duplicate node IDs')
sys.path.insert(0,str(p.ROOT.parent/'graphify_integration_2026_10_16/runtime'));import networkx as nx
G=nx.Graph();G.add_nodes_from(nodes);G.add_edges_from((e['source'],e['target']) for e in g['edges']);sizes=sorted([len(c) for c in nx.connected_components(G)],reverse=True)
r={'status':'PASS_STRUCTURAL_AND_EVIDENCE_CHECKS_ONLY' if not errs else 'FAIL','nodes':len(nodes),'edges':len(g['edges']),'errors':errs,'checks':dict(counts),'connected_components':len(sizes),'component_sizes':sizes,'isolated_node_ids':list(nx.isolates(G)),'self_loop_edges':list(nx.selfloop_edges(G)),'all_relationships_semantically_reviewed':False,'legacy_inferences_independently_reviewed':False,'no_profitability_claim':True}
p.write(w/'FINAL-RELATION-AUDIT.json',r);print({k:v for k,v in r.items() if k not in ['component_sizes','isolated_node_ids','self_loop_edges']})
if errs:raise SystemExit(2)
