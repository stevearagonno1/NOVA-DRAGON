"""Descriptive coverage constraint audit, not an alternative strategy measurement."""
import sys,json,pathlib,gzip
P=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(P/'package'))
import waves as W
p=P/'market-r1';r=json.loads(gzip.decompress((p/'raw.json.gz').read_bytes()));raw,_,_=W.load();out=[]
for m in (15,60):
 _,details=W.signals(raw,m)
 for h in (24,168):
  counts={'events':len(r['events'][str(h)]),'no_early_price_opportunity':0,'early_opportunity_but_context_never_up':0,'early_opportunity_and_context_up':0}
  for e in r['events'][str(h)]:
   opp=[]
   for at,d in details.items():
    if e['onset']<=at<=min(e['hit'],e['onset']+(6 if h==24 else 24)*3600):
     j=(at-raw[0][0])//60
     if j<len(raw) and raw[j][1]<=e['trough']+(1 if h==24 else 2)*e['atr1h']:opp.append(d['context'])
   counts['no_early_price_opportunity' if not opp else 'early_opportunity_and_context_up' if any(opp) else 'early_opportunity_but_context_never_up']+=1
  out.append({'frame':m,'hours':h,**counts})
assert out==json.loads((p/'context-diagnostic.json').read_text())
print('PASS: all4 descriptive context rows rebuilt')
