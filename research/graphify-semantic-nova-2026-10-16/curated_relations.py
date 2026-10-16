"""Small explicit semantic supplement read by the lead, not whole-corpus completion."""
import json
from pathlib import Path
import semantic_pipeline as p
w=p.ROOT/'execution';g=json.loads((w/'evidence-graph.json').read_text());inv=json.loads((w/'INVENTORY.json').read_text());nodes={n['id']:n for n in g['nodes']};extra=[]
prefix='research/session-work-archive-2026-10-16/WORKSPACE-v2.zip!/'
test=prefix+'publish_resume/test_publisher.py';features=prefix+'causal_features_prep/features.py'
localtest=(p.ROOT.parent/'publish_resume/test_publisher.py').read_text();localfeatures=(p.ROOT.parent/'causal_features_prep/features.py').read_text()
for r in inv:
 if r.get('proof_source') not in [test,features]:continue
 producer=r['proof_source'];source=localtest if producer==test else localfeatures
 if r['status']=='INVALID_CONTAINER_FIXTURE':
  quote="(e/'BTC-year-minute-and-frames.zip').write_bytes(b'synthetic transport')" if r['path'].endswith('/BTC-year-minute-and-frames.zip') else "f.write_bytes(b'fixture-'+n.encode())" if '/frames/' in r['path'] else "f.write_bytes(('synthetic source '+month).encode())"
  relation='created_by_fixture_generator'
 else:quote="RECORD=struct.Struct('<q14d')";relation='encoded_by'
 assert quote in source and p.gid(producer) in nodes
 extra.append({'source':p.gid(r['path']),'target':p.gid(producer),'relation':relation,'confidence':'EXTRACTED','confidence_score':1.0,'source_file':producer,'evidence_quote':quote,'review_method':'lead read producer and verified original member SHA256','not_market_evidence':True})
for concept,quote,params in [('ATR','self.atr=Average(14,True)',{'period':14,'smoothing':'Wilder'}),('EMA','self.ema=Average(20)',{'period':20}),('MACD','self.fast=Average(12);self.slow=Average(26);self.signal=Average(9)',{'fast':12,'slow':26,'signal':9}),('RSI','self.gain=Average(14,True);self.loss=Average(14,True)',{'period':14,'smoothing':'Wilder'}),('Volume','div(v,sum(self.vol)/60) if len(self.vol)==60 else math.nan',{'baseline_bars':60,'current_bar_excluded':True})]:
 assert quote in localfeatures
 cid='concept_'+p.gid(concept)
 assert cid in nodes and p.gid(features) in nodes
 extra.append({'source':p.gid(features),'target':cid,'relation':'defines_measurement','confidence':'EXTRACTED','confidence_score':1.0,'source_file':features,'evidence_quote':quote,'parameters':params,'review_method':'lead read full State calculation; no efficacy claim'})
g['edges'].extend(extra);p.write(w/'CURATED-RELATIONS.json',extra);p.write(w/'evidence-graph.json',g)
a=json.loads((w/'EVIDENCE-AUDIT.json').read_text());a['edges']=len(g['edges']);a['lead_curated_relations']=len(extra);a['dangling_endpoints']=sum(e['source'] not in nodes or e['target'] not in nodes for e in g['edges']);p.write(w/'EVIDENCE-AUDIT.json',a)
print('Evidence-backed semantic additions',len(extra))
