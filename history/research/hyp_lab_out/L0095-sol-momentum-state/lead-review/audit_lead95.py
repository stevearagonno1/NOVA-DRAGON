from pathlib import Path
import gzip,json,hashlib,math,statistics,sys
ROOT=Path(__file__).resolve().parent
if not (ROOT/'raw.json.gz').exists():
 import zipfile
 with zipfile.ZipFile(ROOT.parent/'evidence.zip') as z:
  for n in z.namelist():
   assert Path(n).name==n
   (ROOT/n).write_bytes(z.read(n))
 for n in ['delivery.json','evidence.zip']:
  if not (ROOT/n).exists(): (ROOT/n).write_bytes((ROOT.parent/n).read_bytes())
sys.path.insert(0,str(next(x for x in ROOT.parents if (x/'tools/l0095').is_dir())/'tools/l0095'))
import run95 as R
raw=json.loads(gzip.decompress((ROOT/'raw.json.gz').read_bytes()));saved=json.loads((ROOT/'results.json').read_text());receipt=json.loads((ROOT/'delivery.json').read_text())
assert hashlib.sha256((ROOT/'evidence.zip').read_bytes()).hexdigest()==receipt['archive_sha256']
assert len((ROOT/'evidence.zip').read_bytes())==receipt['archive_bytes']
assert not raw['synthetic'] and len(raw['rules'])==4 and len(raw['periods'])==3
assert R.raw_input(False)==raw,'reconstructed masks/labels differ'
# Independent scalar CCI implementation from raw candles, no inherited CCI function.
d=R.H.load_market()['SOLUSDT'];tp=[(float(h)+float(l)+float(c))/3 for h,l,c in zip(d['h'],d['l'],d['c'])];cci=[float('nan')]*len(tp)
for t in range(6,len(tp)):
 w=tp[t-6:t+1];mean=sum(w)/7;mad=sum(abs(x-mean) for x in w)/7;cci[t]=(tp[t]-mean)/(.015*mad) if mad else 0
bits=sum(1<<t for t in range(7,len(tp)) if cci[t-1]<-100 and cci[t]>=-100)
assert bits==int(raw['masks']['CCI_ONLY'],16),'scalar CCI mismatch'
recomputed=[];allalerts=[]
for row in saved:
 mask=int(raw['masks'][row['id']],16);ns=tpcount=0;lags=[];captures=[]
 for pi,p in enumerate(raw['periods']):
  bars=[t for t in p['valid'] if mask&(1<<t)];remaining={e['onset'] for e in p['events']};captured=[];local=[]
  for t in bars:
   found=sorted(x for x in remaining if t-2<=x<=t+2);hit=found[0] if found else None
   if hit is not None:remaining.remove(hit);captured.append(hit);local.append(t-hit)
   allalerts.append(dict(case=row['id'],period=pi,bar=t,time=raw['times'][t],onset=hit))
  old=row['periods'][pi];assert old['signals']==len(bars) and old['matched_events']==len(captured) and old['events']==len(p['events'])
  ns+=len(bars);tpcount+=len(captured);lags+=local;captures.append(captured)
 n=sum(len(p['events']) for p in raw['periods']);precision=tpcount/ns if ns else 0;recall=tpcount/n
 assert row['signals']==ns and row['matched_events']==tpcount and row['captured_onsets']==captures
 assert math.isclose(row['precision'],precision) and math.isclose(row['recall'],recall) and math.isclose(row['f1'],2*tpcount/(ns+n))
 z=1.959963984540054;den=1+z*z/ns;mid=(precision+z*z/(2*ns))/den;half=z*math.sqrt(precision*(1-precision)/ns+z*z/(4*ns*ns))/den
 assert all(math.isclose(x,y) for x,y in zip(row['wilson95'],[mid-half,mid+half]))
 assert row['median_lag']==statistics.median(lags)
 eligible=ns>=20 and recall>=.3 and all(p['signals']>=3 and p['recall']>=.15 for p in row['periods']);quality=eligible and precision>=.7 and mid-half>=.6 and statistics.median(lags)<=1
 assert row['eligible']==eligible and row['quality_pass']==quality
 recomputed.append({'id':row['id'],'signals':ns,'matched':tpcount,'events':n,'precision':precision,'recall':recall,'false':ns-tpcount,'missed':n-tpcount,'quality':quality})
assert allalerts==json.loads((ROOT/'alerts.json').read_text())
base=saved[0]
for row in saved:
 added=sum(len(set(a)-set(b)) for a,b in zip(row['captured_onsets'],base['captured_onsets']));lost=sum(len(set(b)-set(a)) for a,b in zip(row['captured_onsets'],base['captured_onsets']))
 gain=row['id']!='CCI_ONLY' and row['precision']>=base['precision']+.05 and row['recall']>=.8*base['recall']
 assert (added,lost,gain)==(row['added_vs_cci'],row['lost_vs_cci'],row['marginal_gain'])
out={'status':'PASS','delivered_head':'0ca0e6256c16a5fca3a609720158a0054ee3f532','archive_sha256':receipt['archive_sha256'],'rows':recomputed,'alerts_checked':len(allalerts),'quality_passes':[],'marginal_passes':[],'new_experiment':'NOT RUN','duration_whole_review':'not measured;start timestamp not captured'}
(ROOT/'lead-audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
