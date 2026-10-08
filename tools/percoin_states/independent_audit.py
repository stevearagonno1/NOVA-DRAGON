"""Independent minute-outcome and selection audit; does not import pilot or math_core."""
import csv,json,gzip,pathlib,math,hashlib,collections
P=pathlib.Path(__file__).parent;M=P/'market';raw=json.loads(gzip.decompress((M/'raw.json.gz').read_bytes()));rows=json.loads((M/'results.json').read_text());sel=json.loads((M/'selection.json').read_text());sources=raw['sources'];ASSETS=('BTC','ETH','SOL');STATES=('BREAKOUT','PULLBACK','TURN')
by=collections.defaultdict(list)
for r in raw['alerts']:by[(r['asset'],r['state'],r['id'],r['hours'])].append(r)
scans=0
for asset in ASSETS:
 path=P/(asset+'.csv');assert hashlib.sha256(path.read_bytes()).hexdigest()==sources[asset]['csv_sha256']
 with path.open() as f:data=[[int(r[0])]+list(map(float,r[1:])) for r in list(csv.reader(f))[1:]]
 hours=[]
 for j in range(0,len(data),60):
  z=data[j:j+60];hours.append([z[0][0],max(x[2] for x in z),min(x[3] for x in z),z[-1][4]])
 tr=[hours[0][1]-hours[0][2]]+[max(h[1]-h[2],abs(h[1]-hours[i-1][3]),abs(h[2]-hours[i-1][3])) for i,h in enumerate(hours[1:],1)];a=[None]*len(hours)
 for i in range(13,len(hours)):a[i]=sum(tr[:14])/14*(13/14)**(i-13)+sum(tr[k]/14*(13/14)**(i-k) for k in range(14,i+1))
 cache={}
 for r in [r for r in raw['alerts'] if r['asset']==asset]:
  at=r['at'];h=r['hours'];j=(at-data[0][0])//60;hi=(at-hours[0][0])//3600-1;assert r['entry']==data[j][1] and math.isclose(r['atr1h'],a[hi],rel_tol=1e-12)
  key=(at,h)
  if key not in cache:
   if at+h*3600>1785542400:cache[key]=('CENSORED',None)
   else:
    top=r['entry']+(2 if h==24 else 4)*a[hi];bottom=r['entry']-(1 if h==24 else 2)*a[hi];stop=j+h*60;u=next((k for k in range(j,stop) if data[k][2]>=top),stop);d=next((k for k in range(j,stop) if data[k][3]<=bottom),stop)
    cache[key]=('FAIL',d-j) if d<=u and d<stop else ('SUCCESS',u-j) if u<stop else ('FAIL',h*60);scans+=1
  assert cache[key]==(r['status'],r['minutes'])
for r in rows:
 z=by[(r['asset'],r['state'],r['id'],r['hours'])];v=[x for x in z if x['status']!='CENSORED'];n=len(v);k=sum(x['status']=='SUCCESS' for x in v);assert (len(z),n,k)==(r['alerts'],r['n'],r['success']) and r['precision']==(k/n if n else None)
 if n:
  p=k/n;z2=1.959963984540054**2;lo=max(0,(k+z2/2-math.sqrt(z2*(k*(1-p)+z2/4)))/(n+z2));assert math.isclose(lo,r['wilson95_descriptive'][0],abs_tol=1e-12)
# Rebuild both frozen selection lists independently from archived raw counts.
personal=[];shared=[]
for h in (24,168):
 for state in STATES:
  for asset in ASSETS:
   candidates=[r for r in rows if (r['asset'],r['state'],r['hours'])==(asset,state,h) and r['n']>=5];best=sorted(candidates,key=lambda r:(-r['wilson95_descriptive'][0],-r['precision'],-r['n'],r['id']))[0]['id'] if candidates else None;personal.append({'asset':asset,'state':state,'hours':h,'id':best})
  candidates=[]
  for i in range(16):
   r=[r for r in rows if (r['state'],r['hours'],r['id'])==(state,h,i)]
   if len(r)!=3 or min(x['n'] for x in r)<5:continue
   n=sum(x['n'] for x in r);k=sum(x['success'] for x in r);p=k/n;z2=1.959963984540054**2;lo=(k+z2/2-math.sqrt(z2*(k*(1-p)+z2/4)))/(n+z2);candidates.append((lo,p,n,-i))
  best=-max(candidates)[3] if candidates else None;shared.append({'state':state,'hours':h,'id':best})
assert personal==sel['personal'] and shared==sel['shared']
for asset in ASSETS:
 states=raw['assets'][asset]['states'];assert all(x is None or x in STATES for x in states)
assert len(rows)==288
out={'status':'PASS','imports_measurement_code':False,'raw_alert_outcomes_rebuilt':len(raw['alerts']),'distinct_minute_barrier_scans':scans,'summary_rows_rebuilt':288,'personal_selections_rebuilt':18,'shared_selections_rebuilt':6,'atr_independent_exponential_formula':True,'validation':'NOT RUN','adoption':'NOT AUTHORISED'}
(M/'independent-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
