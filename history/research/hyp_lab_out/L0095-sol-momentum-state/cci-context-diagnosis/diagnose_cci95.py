from pathlib import Path
import sys,json,gzip,statistics,hashlib,time,math
import numpy as np
BASE=Path(__file__).resolve().parent
repo=next((p for p in BASE.parents if (p/'tools/l0095').is_dir()),None)
sys.path.insert(0,str(repo/'tools/l0095' if repo else BASE.parent/'package'))
import run95 as R
src=BASE.parent/'review' if (BASE.parent/'review/raw.json.gz').exists() else BASE.parent
if not (src/'raw.json.gz').exists():
 import zipfile
 with zipfile.ZipFile(src/'evidence.zip') as z:
  for n in ['raw.json.gz','alerts.json','results.json']: (BASE/n).write_bytes(z.read(n))
 src=BASE
raw=json.loads(gzip.decompress((src/'raw.json.gz').read_bytes()));aa=[a for a in json.loads((src/'alerts.json').read_text()) if a['case']=='CCI_ONLY'];d=R.H.load_market()['SOLUSDT'];ema=R.I.ema(d['c'],20);atr=R.I.wilder_atr(d['h'],d['l'],d['c'],14)
assert hashlib.sha256((src/'raw.json.gz').read_bytes()).hexdigest()=='d15e83a3f5d22004906f14bfeb8c73fd1b3a7981d50c477ca3ee148e205ca0d1'
assert len(aa)==128 and sum(a['onset'] is not None for a in aa)==32
rows=[]
def feature(panel,t):
 c=panel['c'];v=panel['v'];j=t-1
 e=R.I.ema(c,20);a=R.I.wilder_atr(panel['h'],panel['l'],c,14)
 return {'return_6_prior_pct':100*(c[j]/c[j-6]-1),'return_18_prior_pct':100*(c[j]/c[j-18]-1),'atr_prior_pct':100*a[j]/c[j], 'depth_18_prior_atr':(max(panel['h'][j-17:j+1])-c[j])/a[j], 'volume_prior_ratio':v[j]/np.mean(v[j-19:j+1]),'trend_above':bool(c[j]>=e[j]),'trend_rising':bool(e[j]>e[j-6])}
for a in aa:
 t=a['bar'];f=feature(d,t);p=raw['periods'][a['period']]
 duplicate=a['onset'] is None and any(abs(t-e['onset'])<=2 for e in p['events'])
 row={**a,**{k:float(v) if not isinstance(v,bool) else v for k,v in f.items()},'class':'captured' if a['onset'] is not None else 'duplicate' if duplicate else 'unmatched','regime':('ABOVE' if f['trend_above'] else 'BELOW')+'_'+('RISING' if f['trend_rising'] else 'FALLING')};rows.append(row)
 # Prefix invariance demonstrates no features read current/future candles.
 if len(rows)%16==0:
  small={k:v[:t] for k,v in d.items()};assert feature(small,t)==f
# Independently verify pre-alert returns and EMA trend against scalar recursions.
em=[float(d['c'][0])]
for value in d['c'][1:]:em.append(2/21*float(value)+19/21*em[-1])
for r in rows:
 j=r['bar']-1
 assert r['trend_above']==(float(d['c'][j])>=em[j]) and r['trend_rising']==(em[j]>em[j-6])
 assert math.isclose(r['return_6_prior_pct'],100*(float(d['c'][j])-float(d['c'][j-6]))/float(d['c'][j-6]),abs_tol=1e-10)
classes={k:sum(r['class']==k for r in rows) for k in ['captured','unmatched','duplicate']}
metrics=['return_6_prior_pct','return_18_prior_pct','atr_prior_pct','depth_18_prior_atr','volume_prior_ratio'];summary=[]
for key in metrics:
 summary.append({'metric':key,'captured_median':statistics.median(r[key] for r in rows if r['class']=='captured'),'other_median':statistics.median(r[key] for r in rows if r['class']!='captured')})
regimes=[]
for key in ['ABOVE_RISING','ABOVE_FALLING','BELOW_RISING','BELOW_FALLING']:
 vals=[r for r in rows if r['regime']==key];n=len(vals);tp=sum(r['class']=='captured' for r in vals)
 regimes.append({'regime':key,'alerts':n,'captured':tp,'others':n-tp,'descriptive_precision':tp/n if n else None,'periods':[{'alerts':sum(r['period']==i for r in vals),'captured':sum(r['period']==i and r['class']=='captured' for r in vals)} for i in range(3)]})
out={'source_head':'15d669e7f3fbee4c8e3c99852bafb16c0d4796e9','raw_sha256':hashlib.sha256((src/'raw.json.gz').read_bytes()).hexdigest(),'classes':classes,'medians':summary,'regimes':regimes,'alerts':rows,'feature_cutoff':'bar t-1; excludes alert candle and every future candle','audit':'PASS;128 partition,8 prefixes,128 scalar EMA/return checks','new_market_measurement':'NOT RUN','threshold_search':'NOT RUN','adoption':'NOT AUTHORISED'}
(BASE/'diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='alerts'},indent=2))
