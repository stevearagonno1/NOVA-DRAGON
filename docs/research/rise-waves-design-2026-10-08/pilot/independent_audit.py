"""Independent raw audit: no imports from measurement package."""
import csv,json,gzip,pathlib,math,hashlib,collections,statistics
P=pathlib.Path(__file__).parent;M=P/'market-r1'
rawobj=json.loads(gzip.decompress((M/'raw.json.gz').read_bytes()));begin,end=rawobj['window'];source=json.loads((P/'package/source.json').read_text())
b=(P/'package/minutes.csv').read_bytes();assert hashlib.sha256(b).hexdigest()==source['csv_sha256']
with (P/'package/minutes.csv').open() as f:data=[[int(x[0])]+list(map(float,x[1:])) for x in list(csv.reader(f))[1:]]
data=[x for x in data if x[0]<end];hours=[]
for start in range(0,len(data),60):
 x=data[start:start+60];hours.append([x[0][0],max(v[2] for v in x),min(v[3] for v in x),x[-1][4]])
tr=[hours[0][1]-hours[0][2]]+[max(h[1]-h[2],abs(h[1]-hours[i-1][3]),abs(h[2]-hours[i-1][3])) for i,h in enumerate(hours[1:],1)]
A=[None]*len(hours)
for i in range(13,len(hours)):
 decay=13/14
 A[i]=sum(tr[:14])/14*decay**(i-13)+sum(tr[j]/14*decay**(i-j) for j in range(14,i+1))
def scan(j,price,a,h):
 top=price+(2 if h==24 else 4)*a;bottom=price-(1 if h==24 else 2)*a
 stop=j+h*60
 for k in range(j,stop):
  if data[k][3]<=bottom:return 'FAIL',k-j
  if data[k][2]>=top:return 'SUCCESS',k-j
 return 'FAIL',h*60
alerts=rawobj['alerts'];summary=json.loads((M/'results.json').read_text())
for r in alerts:
 j=(r['at']-data[0][0])//60;hi=(r['at']-hours[0][0])//3600-1
 assert math.isclose(r['atr1h'],A[hi],rel_tol=1e-12)
 assert r['entry']==data[j][1]
 expected=('CENSORED',None) if r['at']+r['hours']*3600>end else scan(j,r['entry'],A[hi],r['hours'])
 assert expected==(r['status'],r['minutes'])
for r in summary:
 z=[x for x in alerts if (x['frame'],x['rule'],x['hours'])==(r['frame'],r['rule'],r['hours'])];v=[x for x in z if x['status']!='CENSORED'];n=len(v);k=sum(x['status']=='SUCCESS' for x in v)
 assert (r['alerts'],r['evaluable'],r['success'])==(len(z),n,k)
 assert r['precision']==(k/n if n else None)
 if n:
  p=k/n;z2=1.959963984540054**2;den=n+z2;lo=(k+z2/2-math.sqrt(z2*(k*(1-p)+z2/4)))/den;up=(k+z2/2+math.sqrt(z2*(k*(1-p)+z2/4)))/den
  assert math.isclose(lo,r['wilson95_descriptive'][0],abs_tol=1e-12) and math.isclose(up,r['wilson95_descriptive'][1],abs_tol=1e-12)
# Independent event catalog reconstruction: prior/next local lows, first target, no overlap.
events={24:[],168:[]};last={24:-1,168:-1}
for i in range(15,len(hours)-3):
 if not all(hours[i][2]<hours[k][2] for k in range(i-3,i)):continue
 if not all(hours[i][2]<=hours[k][2] for k in range(i+1,i+4)):continue
 first=i*60;j=min(range(first,first+60),key=lambda k:data[k][3]);at=data[j][0]
 if not begin<=at<end or not A[i-1] or A[i-1]<=0:continue
 for h in (24,168):
  if at<=last[h] or at+60+h*3600>end:continue
  status,d=scan(j+1,data[j][3],A[i-1],h)
  if status=='SUCCESS':
   hit=at+60+d*60;events[h].append({'onset':at,'hit':hit,'trough':data[j][3],'atr1h':A[i-1]});last[h]=hit
for h in (24,168):
 assert len(events[h])==len(rawobj['events'][str(h)])
 for a,b in zip(events[h],rawobj['events'][str(h)]):
  assert all(a[k]==b[k] for k in ['onset','hit','trough']) and math.isclose(a['atr1h'],b['atr1h'],rel_tol=1e-12)
cov=json.loads((M/'wave-coverage.json').read_text())
for row in cov:
 h=row['hours'];z=[r for r in alerts if r['frame']==row['frame'] and r['rule']==row['rule'] and r['hours']==h and r['status']=='SUCCESS'];used=set();matches=[];lags=[]
 for ei,e in enumerate(events[h]):
  possible=[r for r in z if r['at'] not in used and e['onset']<=r['at']<=min(e['hit'],e['onset']+(6 if h==24 else 24)*3600) and r['entry']<=e['trough']+(1 if h==24 else 2)*e['atr1h']]
  if possible:
   at=min(r['at'] for r in possible);used.add(at);matches.append({'event_id':ei,'alert_at':at});lags.append((at-e['onset'])/3600)
 assert matches==row['matches'] and row['captured_early']==len(matches)
 assert row['median_onset_lag_hours']==(statistics.median(lags) if lags else None)
assert len(summary)==len(cov)==40
result={'status':'PASS','audit_imports_measurement_code':False,'alert_outcomes_rebuilt':len(alerts),'summary_rows_rebuilt':40,'coverage_rows_rebuilt':40,'daily_events':len(events[24]),'weekly_events':len(events[168]),'atr_independent_exponential_formula':True,'wilson_independent_formula':True,'adoption':'NOT AUTHORISED'}
(M/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
