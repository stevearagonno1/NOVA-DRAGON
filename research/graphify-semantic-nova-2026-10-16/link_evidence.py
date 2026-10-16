"""Conservative evidence graph. Lexical mention is never a trading conclusion.
This is NOT a replacement for the host semantic reading stage.
"""
import collections, hashlib, html, json, re, sys, zipfile
from pathlib import Path
import semantic_pipeline as p
ROOT=Path(__file__).parent
CONCEPTS={
 'RSI':r'\bRSI\b|مؤشر القوة النسبية', 'MACD':r'\bMACD\b|ماكد',
 'ATR':r'\bATR\b|متوسط المدى الحقيقي', 'EMA':r'\bEMA\b|المتوسط المتحرك الأسي',
 'SMA':r'\bSMA\b|المتوسط المتحرك البسيط','VWAP':r'\bVWAP\b',
 'Volume':r'\bvolume\b|الفوليوم|حجم التداول','Fibonacci':r'\bfibonacci\b|فيبوناتشي',
 'Fixed Range Volume Profile':r'\bFRVP\b|fixed.range.volume.profile',
 'Order book':r'order.book|دفتر الأوامر','Footprint':r'\bfootprint\b',
 'SMC':r'\bSMC\b|smart.money.concepts','FVG':r'\bFVG\b|fair.value.gap',
 'Order Block':r'order.blocks?|اوردر بلوك','Bitcoin':r'\bBTC(?:USDT)?\b|\bbitcoin\b|البيتكوين',
 'Candlestick patterns':r'candlestick|نماذج الشموع|أنماط الشموع',
 'Rise onset':r'rise.onset|بداية الصعود|بدايه الصعود',
 'Independent settings':r'independent.parameter|نسخ مستقلة|نسخ مستقله',
 'Market states':r'market.states?|حالات السوق','Causality':r'causal|look.ahead|تسرب المستقبل',
 'Synthetic validation':r'\bsynthetic\b|بيانات اصطناعية|بيانات صناعية',
 'Out of sample':r'out.of.sample|holdout|blind.period|الفترة العمياء',
 'Fees':r'\bfees?\b|الرسوم','Slippage':r'\bslippage\b|الانزلاق',
 'Go Hunter':r'go.hunter|مؤشر هنتر|مؤشر هانتر','Go Seeker':r'go.seeker',
 'Go Maestro':r'go.maestro','Go Radar':r'go.radar','Go Bell':r'go.bell',
 'CCI':r'\bCCI\b','Bollinger Bands':r'bollinger|بولينجر',
 'Stochastic':r'\bstochastic\b|ستوكاستيك','ADX':r'\bADX\b','OBV':r'\bOBV\b',
 'MFI':r'\bMFI\b','Ichimoku':r'ichimoku|إيشيموكو','Supertrend':r'supertrend',
 'Heikin Ashi':r'heik[ie]n.ashi|هايكن', 'Divergence':r'\bdivergence\b|دايفرجنس|تباعد',
}
def main(work):
 inventory=json.loads((work/'INVENTORY.json').read_text());nodes={};edges={};unresolved=[]
 paths={r['path'] for r in inventory};byhash=collections.defaultdict(list)
 def add_node(i,label,kind,**kw):nodes.setdefault(i,dict(id=i,label=label,file_type=kind,**kw));return i
 def edge(a,b,rel,source,quote,**kw):
  assert a in nodes and b in nodes
  key=(a,b,rel,source,quote);edges[key]=dict(source=a,target=b,relation=rel,confidence='EXTRACTED',confidence_score=1.0,source_file=source,evidence_quote=quote,**kw)
 for r in inventory:
  add_node(p.gid(r['path']),r['path'],'document',source_file=r['path'],status=r['status'])
  if r.get('sha256'):byhash[r['sha256']].append(r['path'])
 for r in inventory:
  if '!/' in r['path']:
   parent=r['path'].rsplit('!/',1)[0]
   if parent in paths:edge(p.gid(parent),p.gid(r['path']),'archive_contains',parent,r['path'],evidence_type='decoded_archive_inventory')
 for sha,ps in byhash.items():
  ps=sorted(set(ps))
  for path in ps[1:]:edge(p.gid(path),p.gid(ps[0]),'same_bytes_as',path,sha,evidence_type='verified_sha256')
 patterns={k:re.compile(v,re.I) for k,v in CONCEPTS.items()}
 keys={k:re.findall(r'[A-Za-z\u0600-\u06FF]{3,}',v.replace(r'\b',' ')) for k,v in CONCEPTS.items()}
 seen=set()
 for batch in [work/'batches'/n for n in json.loads((work/'BATCH-MANIFEST.json').read_text())]:
  for s in json.loads(batch.read_text()):
   path=s['source_file'];sid=p.gid(path);text=s['text'];lower=text.lower()
   for name,pattern in patterns.items():
    if (path,name) in seen or not any(k.lower() in lower for k in keys[name]):continue
    match=pattern.search(text)
    if match:
     seen.add((path,name))
     cid=add_node('concept_'+p.gid(name),name,'concept')
     quote=text[max(0,match.start()-80):min(len(text),match.end()+120)]
     edge(sid,cid,'mentions',path,quote,segment_id=s['segment_id'],character_offset=s['offset']+match.start(),interpretation='Term mentioned; no implication of implementation, effectiveness, direction, or approval.')
   # Pine declarations stored as source-specific identities, never merged by display name.
   for match in re.finditer(r"(?m)^\s*(?:indicator|strategy|study)\s*\(\s*[\"']([^\"']+)[\"'][^\n]*",text):
    label=match.group(1);nid=add_node('pine_'+p.gid(path+':'+str(s['offset']+match.start())),label,'code',source_file=path)
    edge(sid,nid,'declares_indicator',path,match.group(0),segment_id=s['segment_id'])
   for match in re.finditer(r'(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*input(?:\.[A-Za-z_]+)?\s*\([^\n]*',text):
    nid=add_node('setting_'+p.gid(path+':'+str(s['offset']+match.start())),match.group(1),'code',source_file=path,raw_declaration=match.group(0))
    edge(sid,nid,'declares_input',path,match.group(0),segment_id=s['segment_id'])
   # Only exact, resolvable repository-relative targets are accepted. No fuzzy filename linking.
   candidates=re.findall(r'`([^`\n]{1,400})`|\]\(([^\s)]+)\)',text)
   for pair in candidates:
    target=next(x for x in pair if x);target=target.split('#')[0]
    if target in paths:
     if target!=path:edge(sid,p.gid(target),'references_path',path,target,segment_id=s['segment_id'])
    elif re.match(r'https?://',target):
     uid=add_node('url_'+p.gid(target),target,'concept',verification='URL cited, destination not verified')
     edge(sid,uid,'cites_url',path,target,segment_id=s['segment_id'])
    elif '/' in target and re.search(r'\.[a-z0-9]{1,8}$',target,re.I):unresolved.append({'source_file':path,'target':target,'segment_id':s['segment_id'],'status':'UNRESOLVED_REFERENCE_NOT_LINKED'})
 # Preserve structural graph with explicit namespace and provenance; do not reclassify its inferences.
 current_sha={f['path']:f['sha'] for f in json.loads((ROOT/'SOURCE-TREE.json').read_text())['tree'] if f['type']=='blob'}
 previous=json.loads((ROOT.parent/'graphify_integration_2026_10_16/SOURCE-FILES.json').read_text())
 prior_sha={f['path']:f['sha'] for f in previous['files']}
 old=ROOT.parent/'graphify_integration_2026_10_16/graphify-out/graph.json'
 if old.exists():
  g=json.loads(old.read_text());old_nodes=g.get('nodes',[]);old_edges=g.get('edges',g.get('links',[]))
  for n in old_nodes:
   n=dict(n);original=n['id'];n['id']='ast_'+str(original);n['provenance']='prior_graphify_code_graph';nodes[n['id']]=n
   source=n.get('source_file','')
   if source in paths and prior_sha.get(source)==current_sha.get(source):edge(p.gid(source),n['id'],'declares_symbol',source,original,evidence_type='prior_AST_extraction')
  for e0 in old_edges:
   e=dict(e0);e['source']='ast_'+str(e['source']);e['target']='ast_'+str(e['target']);e['provenance']='prior_graphify_code_graph'
   edges[('ast',len(edges))]=e
 E=list(edges.values());N=list(nodes.values());dangling=[e for e in E if e['source'] not in nodes or e['target'] not in nodes]
 nonstruct=[e for e in E if e['relation'] not in ['declares_symbol','same_bytes_as','archive_contains'] and not e.get('provenance')]
 linked={e[k] for e in nonstruct for k in ['source','target']};isolated=[r['path'] for r in inventory if p.gid(r['path']) not in linked]
 unavailable=[r for r in inventory if r['status'] in ['BLOCKED','FETCH_FAILED','NEEDS_VISUAL_REVIEW']]
 sys.path.insert(0,str(ROOT.parent/'graphify_integration_2026_10_16/runtime'))
 import networkx as nx
 topology=nx.Graph();topology.add_nodes_from(nodes);topology.add_edges_from((e['source'],e['target']) for e in E if e['source'] in nodes and e['target'] in nodes)
 components=sorted((len(c) for c in nx.connected_components(topology)),reverse=True)
 p.write(work/'TOPOLOGY-AUDIT.json',{'components':len(components),'component_sizes':components,'isolates':list(nx.isolates(topology)),'self_loops':list(nx.selfloop_edges(topology)),'note':'No artificial containment edges were added to make the graph connected; mentions can create broad hubs.'})
 p.write(work/'evidence-graph.json',{'nodes':N,'edges':E,'method':'Evidence/mention indexing plus preserved Graphify AST. Full host semantic review remains separate.'})
 p.write(work/'UNRESOLVED-REFERENCES.json',unresolved)
 p.write(work/'EVIDENCE-AUDIT.json',{'nodes':len(N),'edges':len(E),'dangling_endpoints':len(dangling),'tracked_sources':len(current_sha),'inventory_records':len(inventory),'concept_dictionary_size':len(CONCEPTS),'semantic_isolates':isolated,'unavailable':unavailable,'full_semantic_review_complete':False,'warning':'Connectedness, valid quotations and term mentions do not prove semantic correctness or trading validity.'})
 print(json.dumps({'nodes':len(N),'edges':len(E),'dangling':len(dangling),'semantic_review':'pending'}))
if __name__=='__main__':main(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'execution')
