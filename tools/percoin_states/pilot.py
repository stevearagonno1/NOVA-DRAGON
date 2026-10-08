import csv,json,pathlib,math,gzip,time,hashlib,statistics,argparse
import math_core as I
P=pathlib.Path(__file__).parent;ASSETS=('BTC','ETH','SOL');STATES=('BREAKOUT','PULLBACK','TURN');HORIZONS=(24,168)
GRID=[{'id':i,'confirmation':c,'volume':v,'momentum':mom} for i,(c,v,mom) in enumerate((c,v,m) for c in range(4) for v in (False,True) for m in (False,True))]
def dump(path,x):path.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def masks(raw,reference=False):
 b=I.aggregate(raw,15);hour=I.aggregate(raw,60);c=[x[4] for x in b];e=I.ema(c,20);rsi=I.rsi(c);hclose=[x[4] for x in hour];h20=I.ema(hclose,20);h50=I.ema(hclose,50);a=I.atr(hour)
 states=[];signals={s:{str(g['id']):[] for g in GRID} for s in STATES};prev={(s,g['id']):False for s in STATES for g in GRID};last={k:-10**18 for k in prev};detail={}
 for i,x in enumerate(b):
  at=x[0]+900;j=(at-hour[0][0])//3600-1
  if i<50 or j<50 or not a[j] or a[j]<=0:states.append(None);continue
  up=h20[j]>h50[j] and h20[j]>h20[j-1]
  prior=b[i-20:i];hi=max(z[2] for z in prior);lo=min(z[3] for z in prior)
  breakout=c[i]>hi and hi-lo<=4*a[j]
  pullback=up and any(c[k]<=e[k] for k in range(i-4,i)) and c[i]>e[i] and c[i]>x[1]
  turn=not up and c[i]>x[1] and c[i]>c[i-1] and rsi[i]>rsi[i-1]
  state='BREAKOUT' if breakout else 'PULLBACK' if pullback else 'TURN' if turn else None
  if reference:
   # State priority and range comparisons recomputed as separate scalar predicates.
   z=b[i-20:i];bo=all(x[4]>y[2] for y in z) and max(y[2] for y in z)-min(y[3] for y in z)<=4*a[j]
   pb=bool(up and sum(c[k]<=e[k] for k in range(i-4,i))>0 and x[4]>e[i] and x[4]>x[1])
   tu=bool(not up and x[4]>x[1] and x[4]>b[i-1][4] and rsi[i]>rsi[i-1])
   state=next((s for s,yes in zip(STATES,(bo,pb,tu)) if yes),None)
  states.append(state);detail[at]={'atr':a[j],'state':state}
  width=x[2]-x[3];strong=width>0 and x[4]>x[1] and (x[4]-x[1])/width>=.5 and (x[4]-x[3])/width>=.75
  close_break=x[4]>b[i-1][2];volmean=sum(y[5] for y in prior)/20;volume=volmean>0 and x[5]>=1.5*volmean;momentum=rsi[i]>=50 and rsi[i]>rsi[i-1]
  for s in STATES:
   for g in GRID:
    co=(True,strong,close_break,strong and close_break)[g['confirmation']];ok=bool(state==s and co and (not g['volume'] or volume) and (not g['momentum'] or momentum));key=(s,g['id'])
    if ok and not prev[key] and at-last[key]>=21600:signals[s][str(g['id'])].append(at);last[key]=at
    prev[key]=ok
 return signals,states,detail

def scan(raw,j,entry,a,h,reference=False):
 top=entry+(2 if h==24 else 4)*a;bot=entry-(1 if h==24 else 2)*a;end=j+h*60
 if reference:
  u=next((k for k in range(j,end) if raw[k][2]>=top),end);d=next((k for k in range(j,end) if raw[k][3]<=bot),end)
  return ('FAIL',d-j) if d<=u and d<end else ('SUCCESS',u-j) if u<end else ('FAIL',h*60)
 for k in range(j,end):
  if raw[k][3]<=bot:return 'FAIL',k-j
  if raw[k][2]>=top:return 'SUCCESS',k-j
 return 'FAIL',h*60

def metric(z):
 v=[r for r in z if r['status']!='CENSORED'];n=len(v);k=sum(r['status']=='SUCCESS' for r in v);p=k/n if n else None;ci=None
 if n:
  zz=1.959963984540054**2;den=n+zz;spread=math.sqrt(zz*(k*(1-p)+zz/4));ci=[max(0,(k+zz/2-spread)/den),min(1,(k+zz/2+spread)/den)]
 return {'alerts':len(z),'censored':len(z)-n,'n':n,'success':k,'precision':p,'wilson95_descriptive':ci,'descriptive_quality':bool(n>=100 and p>=.7 and ci[0]>=.6)}
def select(rows):
 def best(rr):return max(rr,key=lambda r:(r['wilson95_descriptive'][0],r['precision'],r['n'],-r['id']))['id'] if rr else None
 personal=[];shared=[]
 for h in HORIZONS:
  for s in STATES:
   for asset in ASSETS:
    rr=[r for r in rows if (r['asset'],r['state'],r['hours'])==(asset,s,h) and r['n']>=5];personal.append({'asset':asset,'state':s,'hours':h,'id':best(rr)})
   pooled=[]
   for g in GRID:
    rr=[r for r in rows if (r['state'],r['hours'],r['id'])==(s,h,g['id'])]
    if not all(r['n']>=5 for r in rr):continue
    n=sum(r['n'] for r in rr);k=sum(r['success'] for r in rr);p=k/n;zz=1.959963984540054**2;lo=(k+zz/2-math.sqrt(zz*(k*(1-p)+zz/4)))/(n+zz)
    pooled.append({'id':g['id'],'n':n,'precision':p,'wilson95_descriptive':[lo,None]})
   shared.append({'state':s,'hours':h,'id':best(pooled)})
 return {'personal':personal,'shared':shared,'exploratory_only':True,'validation_run':False,'adoption':'NOT AUTHORISED'}

def fixture():
 raw=[];base=1767225600
 for i in range(45*1440):
  c=100+.001*i+3*math.sin(i/750)+.8*math.sin(i/40);o=raw[-1][4] if raw else 100;raw.append([base+60*i,o,max(o,c)+.1,min(o,c)-.1,c,10+(i%180==0)*100])
 return raw,base+20*86400,base+38*86400

def run(out,synthetic=False):
 started=time.monotonic();out=pathlib.Path(out);out.mkdir(exist_ok=True);scope=json.loads((P/'scope.json').read_text());records=[];rawassets={};source=json.loads((P/'sources.json').read_text()) if not synthetic else {}
 for asset in ASSETS:
  if synthetic:raw,begin,end=fixture()
  else:
   path=P/(asset+'.csv');assert sha(path)==source[asset]['csv_sha256']
   with path.open() as f:raw=[[int(r[0])]+list(map(float,r[1:])) for r in list(csv.reader(f))[1:]]
   begin,end=1782864000,1785542400
  assert all(raw[i][0]-raw[i-1][0]==60 for i in range(1,len(raw)))
  assert all(x[3]<=min(x[1],x[4])<=max(x[1],x[4])<=x[2] and x[5]>=0 for x in raw)
  sig,states,detail=masks(raw);ref,rs,_=masks(raw,True);assert (sig,states)==(ref,rs)
  for cut in (13*1440,21*1440,len(raw)-1440):
   cut-=cut%240;pre,_,_=masks(raw[:cut]);limit=raw[cut-1][0]+60
   assert all(pre[s][str(g['id'])]==[t for t in sig[s][str(g['id'])] if t<=limit] for s in STATES for g in GRID)
  rawassets[asset]={'masks':sig,'states':states,'begin':begin,'end':end}
  for s in STATES:
   for g in GRID:
    for at in sig[s][str(g['id'])]:
     if not begin<=at<end:continue
     j=(at-raw[0][0])//60
     for h in HORIZONS:
      result=('CENSORED',None) if at+h*3600>end else scan(raw,j,raw[j][1],detail[at]['atr'],h)
      if result[0]!='CENSORED':assert result==scan(raw,j,raw[j][1],detail[at]['atr'],h,True)
      records.append({'asset':asset,'state':s,'id':g['id'],'hours':h,'at':at,'entry':raw[j][1],'atr1h':detail[at]['atr'],'status':result[0],'minutes':result[1]})
 rows=[]
 for asset in ASSETS:
  for s in STATES:
   for g in GRID:
    for h in HORIZONS:
     z=[r for r in records if (r['asset'],r['state'],r['id'],r['hours'])==(asset,s,g['id'],h)];rows.append({'asset':asset,'state':s,'id':g['id'],'hours':h,**metric(z)})
 rawobj={'synthetic':synthetic,'scope':scope,'sources':source,'assets':rawassets,'alerts':records}
 with gzip.GzipFile(filename=str(out/'raw.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps(rawobj,sort_keys=True).encode())
 dump(out/'results.json',rows);sel=select(rows);dump(out/'selection.json',sel)
 assert len(rows)==288 and len(sel['personal'])==18 and len(sel['shared'])==6
 saved=json.loads(gzip.decompress((out/'raw.json.gz').read_bytes()))
 for r in rows:
  z=[x for x in saved['alerts'] if all(x[k]==r[k] for k in ('asset','state','id','hours'))];assert metric(z)=={k:r[k] for k in metric(z)}
 dump(out/'audit.json',{'status':'PASS','synthetic':synthetic,'cells':9,'candidate_cells':144,'summary_rows':288,'alert_outcomes':len(records),'scalar_state_masks':True,'prefix_causality':True,'independent_barrier_scans':True,'zero_rows_retained':True,'raw_sha256':sha(out/'raw.json.gz'),'compute_seconds':time.monotonic()-started,'validation':'NOT RUN','adoption':'NOT AUTHORISED'})
 return rows,sel
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--synthetic',action='store_true');a.add_argument('--out',default='market');args=a.parse_args();run(args.out,args.synthetic)
