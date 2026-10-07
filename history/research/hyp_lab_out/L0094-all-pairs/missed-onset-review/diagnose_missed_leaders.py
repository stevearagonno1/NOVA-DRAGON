from pathlib import Path
import gzip,hashlib,json,collections,time
p=Path('l0094/remote-market');begin=time.monotonic();raw=json.loads(gzip.decompress((p/'raw_signals.json.gz').read_bytes()));selection=json.loads(Path('l0094/all-quality-review.json').read_text())['highest_precision_eligible_diagnostic']
assert hashlib.sha256((p/'raw_signals.json.gz').read_bytes()).hexdigest()=='551918480f66ae32257b5bd4115451ec1f6d9351fbec202f046a0ff7949e547b'
records=[];summaries=[]
for asset,d in selection.items():
 c=collections.Counter();near=collections.Counter();period_counts=[];caught=0;total=0
 for pi in range(3):
  r=raw['assets'][asset+'_P'+str(pi)];valid=int(r['valid'],16);a=int(r['masks'][d['a']],16);b=int(r['masks'][d['b']],16)
  truth=a&b if d['mode']=='AND0' else a|b if d['mode']=='OR0' else (a|a<<1|a<<2)&(b|b<<1|b<<2)
  mix=truth&~(truth<<1)&valid
  own_count=0;own_hit=0
  for event in r['events']:
   o=event['onset'];window=range(o-2,o+3);first=next((t for t in window if mix>>t&1),None)
   aa=[t-o for t in window if (a&valid)>>t&1];bb=[t-o for t in window if (b&valid)>>t&1]
   total+=1;own_count+=1
   record={'asset':asset,'candidate':d['candidate'],'period':pi,'onset':o,'matched_mix_lag':None if first is None else first-o,'a_lags_in_success_window':aa,'b_lags_in_success_window':bb}
   if first is not None:caught+=1;own_hit+=1;record['miss_reason']=None
   else:
    reason='neither_component_in_window' if not aa and not bb else 'only_a_in_window' if aa and not bb else 'only_b_in_window' if bb and not aa else 'both_in_window_without_mix_pulse'
    c[reason]+=1;record['miss_reason']=reason
    nearby=[t for t in range(max(0,o-12),o+13) if mix>>t&1]
    nearest=min(nearby,key=lambda t:(abs(t-o),t)) if nearby else None
    timing='absent_12' if nearest is None else 'early_outside' if nearest<o else 'late_outside'
    near[timing]+=1;record.update(nearest_mix_lag=None if nearest is None else nearest-o,nearest_mix_timing=timing,
          a_lags_diagnostic=[t-o for t in range(max(0,o-12),o+13) if (a&valid)>>t&1],b_lags_diagnostic=[t-o for t in range(max(0,o-12),o+13) if (b&valid)>>t&1])
    assert reason!='both_in_window_without_mix_pulse' or d['mode']!='AND0' or not(set(aa)&set(bb))
   records.append(record)
  period_counts.append({'events':own_count,'caught':own_hit})
 assert caught==d['matched_events'] and total==d['events'] and sum(c.values())==total-caught and sum(near.values())==total-caught
 summaries.append({'asset':asset,'candidate':d['candidate'],'mode':d['mode'],'rules':d['rule'],'events':total,'caught':caught,'missed':total-caught,'miss_reasons':{k:c[k] for k in ['neither_component_in_window','only_a_in_window','only_b_in_window','both_in_window_without_mix_pulse']},'nearest_confirmation_timing':{k:near[k] for k in ['early_outside','late_outside','absent_12']},'period_counts':period_counts})
assert len(records)==106 and sum(s['missed'] for s in summaries)==65
result={'status':'PASS','decision':'D-L0094-MISSED-ONSET-20261007','verdict':'Defer','kind':'post-hoc descriptive diagnosis;not new signal performance','source':'d7e72e6d8639088243e93ced30ab682bcdbf0985','summaries':summaries,'records':records,'compute_seconds':time.monotonic()-begin,'limits':'Presence of pulses around future-labelled onsets is evaluation-only;absence in diagnostic12 bars is not proof of impossibility;no causal state tested','adoption':'NOT AUTHORISED'}
Path('l0094/missed-onset-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'summaries':summaries,'compute_seconds':result['compute_seconds']},indent=2))
