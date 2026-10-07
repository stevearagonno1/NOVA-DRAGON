"""Post-hoc diagnosis of frozen CCI alerts. No search, new signal or adoption."""
from pathlib import Path
import argparse,csv,json,gzip,hashlib,sys,collections,math
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--package',default='l0090/package');p.add_argument('--market',default='l0090/market');p.add_argument('--out',default='l0090/diagnosis');args=p.parse_args();package=Path(args.package).resolve();market=Path(args.market);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(package));import research85 as R
D=R.load_market();raw=json.loads(gzip.decompress((market/'raw.json.gz').read_bytes()));results=json.loads((market/'results.json').read_text())['rows'];summary={};alert_rows=[];event_rows=[];mask_checks=0
for asset,n in [('BTCUSDT',14),('ETHUSDT',14),('SOLUSDT',21)]:
 d=D[asset];a=raw['assets'][asset];name=f'CCI_{n}_-150';tp=(d['h']+d['l']+d['c'])/3;cci=np.full(len(tp),np.nan)
 # Scalar CCI definition independently reconstructed from OHLCV, same registered10-decimal boundary.
 for i in range(n-1,len(tp)):
  w=list(tp[i-n+1:i+1]);mean=sum(w)/n;mad=sum(abs(v-mean) for v in w)/n
  if mad>0:cci[i]=round((tp[i]-mean)/(.015*mad),10)
 pulse=set(i for i in range(1,len(tp)) if cci[i-1]<-150 and cci[i]>=-150);stored=set(R.bits(int(a['masks'][name],16)));assert pulse==stored,(asset,'CCI mask');mask_checks+=1
 atr=R.I.wilder_atr(d['h'],d['l'],d['c'],14);counts=collections.Counter();period_summary=[]
 for j,period in enumerate(a['periods']):
  alerts=sorted(pulse.intersection(period['valid']));events=period['events'];claimed=set();hits={};pc=collections.Counter()
  for i in alerts:
   match=next((q for q,e in enumerate(events) if q not in claimed and abs(i-e['onset'])<=2),None)
   if match is not None:claimed.add(match);hits[match]=i;kind='MATCHED'
   elif any(abs(i-e['onset'])<=2 for e in events):kind='DUPLICATE'
   else:kind='UNMATCHED'
   outcome='NO_BARRIER';delay=None;upper=d['c'][i]+2*atr[i];lower=d['c'][i]-atr[i]
   for k in range(i+1,i+25):
    if d['l'][k]<=lower:outcome='LOWER_FIRST';delay=k-i;break
    if d['h'][k]>=upper:outcome='UPPER_FIRST';delay=k-i;break
   nearest=min(events,key=lambda e:abs(i-e['onset'])) if events else None;offset=i-nearest['onset'] if nearest else None
   counts[kind]+=1;pc[kind]+=1
   if kind!='MATCHED':counts['FALSE_'+outcome]+=1
   past_min=float(np.nanmin(cci[max(0,i-12):i+1]));past_return=float(d['c'][i]/d['c'][i-6]-1) if i>=6 else None
   alert_rows.append({'asset':asset,'period':j,'bar':i,'time':d['dt'][i],'signal':name,'classification':kind,'matched_onset':events[match]['onset'] if match is not None else None,'nearest_event_alert_minus_onset_bars':offset,'diagnostic_forward_barrier':outcome,'diagnostic_barrier_delay':delay,'causal_cci_at_close':float(cci[i]),'causal_min_cci_last13':past_min,'causal_return_last6':past_return})
  for q,e in enumerate(events):
   t=e['onset'];captured=q in claimed;near=[i for i in sorted(pulse) if abs(i-t)<=12];nearest=min(near,key=lambda i:abs(i-t)) if near else None
   oversold=[i for i in range(max(0,t-12),t+3) if cci[i]<-150]
   if captured:kind='MATCHED'
   elif not oversold:kind='NO_DEEP_OVERSOLD_IN_DIAGNOSTIC_WINDOW'
   elif nearest is None:kind='OVERSOLD_WITHOUT_RECOVERY_CROSS_WITHIN12'
   elif nearest<t-2:kind='NEAREST_CROSS_EARLY'
   elif nearest>t+2:kind='NEAREST_CROSS_LATE'
   else:kind='CROSS_OUTSIDE_ELIGIBLE_DECISION_BARS'
   if not captured:counts['MISSED_'+kind]+=1
   pc['EVENTS']+=1;pc['MISSED_EVENTS']+=int(not captured)
   event_rows.append({'asset':asset,'period':j,'onset':t,'time':d['dt'][t],'signal':name,'captured':captured,'alert_bar':hits.get(q),'diagnostic_miss_category':kind,'diagnostic_nearest_cross_minus_onset_bars':nearest-t if nearest is not None else None,'diagnostic_oversold_seen_from_minus12_to_plus2':bool(oversold),'causal_cci_at_onset_close':float(cci[t])})
  expected=next(r for r in results if r['asset']==asset and r['candidate']=='PRICE_0')['periods'][j];assert len(alerts)==expected['signals'];assert len(claimed)==expected['matched_events'];assert len(events)==expected['events'];period_summary.append(dict(pc))
 parent=next(r for r in results if r['asset']==asset and r['candidate']=='PRICE_0');assert counts['MATCHED']==parent['matched_events'];assert counts['MATCHED']+counts['UNMATCHED']+counts['DUPLICATE']==parent['signals']
 summary[asset]={'signal':name,'signals':parent['signals'],'matched_events':parent['matched_events'],'events':parent['events'],'precision':parent['precision'],'recall':parent['recall'],'false_or_duplicate':parent['signals']-parent['matched_events'],'missed_events':parent['events']-parent['matched_events'],'categories':dict(counts),'periods':period_summary}
for filename,rows in [('alerts.csv',alert_rows),('events.csv',event_rows)]:
 with (out/filename).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
all_false=[r for r in alert_rows if r['classification']!='MATCHED'];missed=[r for r in event_rows if not r['captured']];totals={'signals':len(alert_rows),'matched_events':len(alert_rows)-len(all_false),'events':len(event_rows),'false_or_duplicate':len(all_false),'missed_events':len(missed),'false_forward_outcomes':dict(collections.Counter(r['diagnostic_forward_barrier'] for r in all_false)),'missed_categories':dict(collections.Counter(r['diagnostic_miss_category'] for r in missed))}
assert totals['signals']==137 and totals['matched_events']==56 and totals['events']==106
result={'scope':'post-hoc diagnosis of existing frozen CCI; no new strategy or parameter search','source_commit':'ad6fd8dd724d24c3205ad578890a122a78d71d7f','raw_sha256':hashlib.sha256((market/'raw.json.gz').read_bytes()).hexdigest(),'per_asset':summary,'totals':totals,'audit':{'status':'PASS','independent_scalar_cci_masks_checked':mask_checks,'asset_period_count_reconciliations':9,'alert_rows':len(alert_rows),'event_rows':len(event_rows)},'lookahead_warning':'forward barriers and miss categorisation up to onset+2/+12 are diagnostic labels ONLY, never deployable features; no candidate selected or tested','false_label_warning':'unmatched against onset window is not synonymous with a losing trade; barrier outcomes are price diagnostics with no fills or costs','new_grid_search':False,'adoption':'NOT AUTHORISED'}
(out/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(totals,indent=2))
