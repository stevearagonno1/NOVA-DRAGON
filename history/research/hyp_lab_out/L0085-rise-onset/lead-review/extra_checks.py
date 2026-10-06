from pathlib import Path
import json,gzip,statistics,math
R=Path(__file__).resolve().parent;E=R/'evidence';x=json.load(open(R/'lead_audit.json'));w=x['winner'];raw=json.loads(gzip.decompress((E/'raw_signals.json.gz').read_bytes()));alerts=json.load(open(E/'alerts_top20.json'));diagnostics=json.load(open(E/'diagnostics_top20.json'));checks=0
for q in diagnostics:
 aa=[a for a in alerts if a['candidate']==q['candidate'] and a['asset']==q['asset']];lags=[a['lag'] for a in aa if a['lag'] is not None];assert q['signals']==len(aa)
 for field,values in [('lag_median_bars',lags),('mae_median_atr_24',[a['mae_atr_24'] for a in aa]),('mfe_median_atr_24',[a['mfe_atr_24'] for a in aa])]:
  if values:assert math.isclose(q[field],statistics.median(values),abs_tol=1e-9)
  else:assert q[field] is None
 checks+=1
for cid in set(a['candidate'] for a in alerts):
 for sym,r in raw['assets'].items():
  aa=[a for a in alerts if a['candidate']==cid and a['asset']==sym];used=set()
  for a in aa:
   j=next((j for j,e in enumerate(r['events']) if j not in used and abs(a['bar']-e['onset'])<=2),None);assert a['event']==j
   if j is not None:used.add(j);assert a['onset']==r['events'][j]['onset'] and a['lag']==a['bar']-a['onset']
ns=w['signals'];tp=w['matched'];z=1.959963984540054;p=tp/ns;den=1+z*z/ns;cen=(p+z*z/(2*ns))/den;half=z*math.sqrt(p*(1-p)/ns+z*z/(4*ns*ns))/den
wa=x['winner_alerts'];duplicate=sum(a['event'] is None and any(abs(a['bar']-e['onset'])<=2 for e in raw['assets'][a['asset']]['events']) for a in wa);monthly=[]
for month in ['2025-01','2025-02','2025-03']:
 aa=[a for a in wa if a['time'].startswith(month)];monthly.append({'month':month,'signals':len(aa),'matched':sum(a['event'] is not None for a in aa),'onsets':sum(sum(r['times'][e['onset']].startswith(month) for e in r['events']) for r in raw['assets'].values())})
extra={'diagnostic_groups_verified':checks,'winner_precision_wilson95_descriptive':[cen-half,cen+half],'winner_false_unmatched':ns-tp-duplicate,'winner_duplicate_alerts':duplicate,'missed_events':sum(x['events_per_asset'].values())-tp,'median_lag_bars':statistics.median(a['lag'] for a in wa if a['lag'] is not None),'matched_same_onset_bar':sum(a['lag']==0 for a in wa),'matched_early':sum(a['lag'] is not None and a['lag']<0 for a in wa),'matched_late':sum(a['lag'] is not None and a['lag']>0 for a in wa),'months':monthly,'winner_diagnostics':[d for d in diagnostics if d['candidate']==w['candidate']]}
json.dump(extra,open(R/'extra_audit.json','w'),indent=2);print(json.dumps(extra,indent=2))
