"""Post-hoc causal pre-alert context; no new candidate/filter scored."""
from pathlib import Path
import json,csv,sys,statistics,hashlib,argparse
p=argparse.ArgumentParser();p.add_argument('--package',default='l0090/package');p.add_argument('--market',default='l0091/market');p.add_argument('--out',default='l0091/context');args=p.parse_args();sys.path.insert(0,str(Path(args.package).resolve()));import research85 as R
M=Path(args.market);O=Path(args.out);O.mkdir(parents=True,exist_ok=True);D=R.load_market();results=json.loads((M/'results.json').read_text())['rows'];selected=json.loads((M/'selection.json').read_text())['selected_by_asset'];alerts=json.loads((M/'alerts.json').read_text());cases=[];audit_checks=0
for asset,d in D.items():
 c,h,l=[list(map(float,d[k])) for k in ['c','h','l']];atr=[];v=None
 for i in range(len(c)):
  tr=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) if i else h[i]-l[i];v=tr if v is None else 13*v/14+tr/14;atr.append(v)
 cci=next(r for r in results if r['asset']==asset and r['candidate']=='CCI_CONTROL')['captured_onsets_by_period'];chosen=next(r for r in results if r['asset']==asset and r['candidate']==selected[asset]);ac=[a for a in alerts if a['asset']==asset and a['candidate']==selected[asset]];assert len(ac)==chosen['signals'];assert sum(a['matched_onset'] is not None for a in ac)==chosen['matched_events']
 for a in ac:
  i=a['bar'];assert i>=21;ret20=c[i-1]/c[i-21]-1;ret6=c[i-1]/c[i-7]-1;draw=(max(h[i-6:i])-c[i-1])/atr[i-1];trend=c[i-1]>sum(c[i-20:i])/20
  # Independent prefix arithmetic checks; no use of current/future OHLC in these features.
  prefix={k:list(d[k][:i]) for k in ['c','h','l']};assert ret20==float(prefix['c'][-1]/prefix['c'][-21]-1);assert ret6==float(prefix['c'][-1]/prefix['c'][-7]-1);assert draw==(max(prefix['h'][-6:])-prefix['c'][-1])/atr[i-1];audit_checks+=3
  group='UNMATCHED' if a['matched_onset'] is None else 'MATCHED_SHARED_WITH_CCI' if a['matched_onset'] in cci[a['period']] else 'MATCHED_NEW_VS_CCI'
  cases.append({**a,'group':group,'prior_return20':ret20,'prior_return6':ret6,'prior_drawdown6_atr':draw,'prior_above_sma20':trend})
summary={}
for group in ['MATCHED_NEW_VS_CCI','MATCHED_SHARED_WITH_CCI','UNMATCHED']:
 z=[c for c in cases if c['group']==group];summary[group]={'n':len(z),'positive_return20_count':sum(c['prior_return20']>0 for c in z),'positive_return6_count':sum(c['prior_return6']>0 for c in z),'above_prior_sma20_count':sum(c['prior_above_sma20'] for c in z),'drawdown_at_least1_atr_count':sum(c['prior_drawdown6_atr']>=1 for c in z),'median_return20':statistics.median(c['prior_return20'] for c in z) if z else None,'median_drawdown6_atr':statistics.median(c['prior_drawdown6_atr'] for c in z) if z else None}
per={}
for asset in D:
 z=[c for c in cases if c['asset']==asset];r=next(x for x in results if x['asset']==asset and x['candidate']==selected[asset]);per[asset]={'selected':selected[asset],'signals':len(z),'matched':sum(c['group']!='UNMATCHED' for c in z),'new_events_vs_cci':sum(c['group']=='MATCHED_NEW_VS_CCI' for c in z),'lost_events_vs_cci':r['lost_events_vs_cci'],'unmatched':sum(c['group']=='UNMATCHED' for c in z)}
assert sum(x['n'] for x in summary.values())==523;assert summary['MATCHED_NEW_VS_CCI']['n']==20;assert summary['MATCHED_SHARED_WITH_CCI']['n']==24;assert summary['UNMATCHED']['n']==479
with (O/'cases.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(cases[0]));w.writeheader();w.writerows(cases)
result={'source_commit':'179d3684a5a0ac3bf2b069b53a5bc46f423b383a','scope':'post-hoc diagnosis of frozen selectedL0091 alerts; no new filter/grid/precision scored','definitions':{'return20':'close[t-1]/close[t-21]-1','return6':'close[t-1]/close[t-7]-1','drawdown6_atr':'(max(high[t-6:t])-close[t-1])/ATR14Wilder[t-1]','above_sma20':'close[t-1]>mean(close[t-20:t])'},'groups':summary,'per_asset':per,'audit':{'status':'PASS','prior_only_arithmetic_checks':audit_checks,'selected_alert_count_reconciliations':3,'frozen_rows_checked':523},'limits':'Post-hoc context bins, thresholds0 and1ATR and already-selected alerts. No inference, causal attribution,filterperformance or future prediction. Outcomes only form diagnostic cohorts.','input_sha256':{n:hashlib.sha256((M/n).read_bytes()).hexdigest() for n in ['results.json','selection.json','alerts.json']},'adoption':'NOT AUTHORISED'};(O/'context.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'groups':summary,'per_asset':per,'audit':result['audit']},indent=2))
