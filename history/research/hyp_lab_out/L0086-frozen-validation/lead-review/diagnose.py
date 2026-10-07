from pathlib import Path
import runpy,contextlib,io,json
R=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):n=runpy.run_path(str(R/'audit_lead.py'))
details={};total={k:0 for k in ['pair_caught','bb_caught','shared','bb_only','pair_only','neither','bb_only_vwap_false_in_window','pair_false_no_label','pair_duplicate']}
for sym,d in n['data'].items():
 ids=n['parents'];a=ids.index(11);b=ids.index(454);pa=n['alerts'](d,a,b,'AND0');bb=n['alerts'](d,a,-1,'S');_,_,pm=n['score'](pa,d);_,_,bm=n['score'](bb,d);ps=set(pm.values());bs=set(bm.values());vwap=d['masks'][b];allids=set(range(len(d['events'])));window=lambda j:set(range(d['events'][j][0]-2,d['events'][j][0]+3))
 dup=sum(any(abs(i-t)<=2 for t,_ in d['events']) and i not in pm for i in pa)
 z={'pair_caught':len(ps),'bb_caught':len(bs),'shared':len(ps&bs),'bb_only':len(bs-ps),'pair_only':len(ps-bs),'neither':len(allids-(ps|bs)),'bb_only_vwap_false_in_window':sum(not(window(j)&vwap) for j in bs-ps),'pair_false_no_label':len(pa)-len(ps)-dup,'pair_duplicate':dup,'bb_only_events':[{'onset':d['times'][d['events'][j][0]],'vwap_true_in_window':bool(window(j)&vwap)} for j in sorted(bs-ps)]};details[sym]=z
 for k in total:total[k]+=z[k]
record={'scope':'post-validation diagnosis only; no rule change or new trial','by_asset':details,'totals':total};(R/'diagnosis.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
