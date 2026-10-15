import collections,csv,datetime as dt,gzip,hashlib,io,json,math,struct,urllib.request,zipfile
from pathlib import Path
import source_collect as src
RECORD=struct.Struct('<q14d');FRAMES=[1,5,15,60]
def sha(p):return src.sha(p)
def ms(s):return int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()*1000)
def acquire(root,spec):
 out=root/'inputs';out.mkdir(parents=True,exist_ok=True);handles={};writers={};chunks={n:[] for n in FRAMES if n>1};hashes={};next_time=ms(spec['collection_start'])
 for n in FRAMES:
  handles[n]=io.TextIOWrapper(gzip.GzipFile(filename='',fileobj=(out/f'BTCUSDT-{n}m.csv.gz').open('wb'),mode='wb',mtime=0),encoding='utf-8',newline='');writers[n]=csv.writer(handles[n]);writers[n].writerow(src.FIELDS)
 try:
  for month,expected in spec['source_sha256_by_month'].items():
   url=f'https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/{spec["raw_data_commit"]}/research/btc-registration-from-repo-2026-10-15/executor/data/raw/BTCUSDT-1m-{month}.zip'
   with urllib.request.urlopen(url,timeout=45) as f:content=f.read(25000000)
   assert hashlib.sha256(content).hexdigest()==expected
   with zipfile.ZipFile(io.BytesIO(content)) as z:
    assert len(z.namelist())==1
    with z.open(z.namelist()[0]) as f:
     for raw in csv.reader(io.TextIOWrapper(f)):
      row=src.normalize(raw,'us');assert int(row[0])==next_time;next_time+=60000;writers[1].writerow(row)
      for n,b in chunks.items():
       b.append(row)
       if len(b)==n:writers[n].writerow(src.aggregate(b,n));b.clear()
   src.budget(root)
 finally:
  for h in handles.values():h.close()
 assert next_time==ms(spec['analysis_end_exclusive']) and all(not b for b in chunks.values())
 return out
class Average:
 def __init__(self,n,wilder=False):self.n=n;self.a=1/n if wilder else 2/(n+1);self.v=None;self.seed=[];self.wilder=wilder
 def step(self,x):
  if x is None:return None
  if self.v is None:
   self.seed.append(x)
   if len(self.seed)==self.n:self.v=sum(self.seed)/self.n
  elif self.wilder:self.v=(self.v*(self.n-1)+x)/self.n
  else:self.v=self.a*x+(1-self.a)*self.v
  return self.v
class State:
 def __init__(self):
  self.atr=Average(14,True);self.ema=Average(20);self.fast=Average(12);self.slow=Average(26);self.signal=Average(9);self.gain=Average(14,True);self.loss=Average(14,True);self.prev=None;self.hist=collections.deque(maxlen=6);self.vol=collections.deque(maxlen=60);self.i=-1
 def step(self,row):
  self.i+=1;o,h,l,c,v=map(float,row[1:6]);tr=h-l if self.prev is None else max(h-l,abs(h-self.prev),abs(l-self.prev));change=None if self.prev is None else c-self.prev
  a=self.atr.step(tr);e=self.ema.step(c);f=self.fast.step(c);s=self.slow.step(c);m=None if s is None else f-s;sig=self.signal.step(m);hist=None if sig is None else m-sig
  g=self.gain.step(None if change is None else max(change,0));loss=self.loss.step(None if change is None else max(-change,0));r=None if g is None else 50.0 if g==loss==0 else 100.0 if loss==0 else 100-100/(1+g/loss)
  previous=self.hist[0] if len(self.hist)==5 else self.hist[1] if len(self.hist)==6 else None
  div=lambda x,y:math.nan if x is None or y in (None,0) else x/y
  vals=(a,div(100*a,c) if a is not None else math.nan,div(a,previous[0])-1 if previous and previous[0] else math.nan,e,div(None if e is None else c-e,a),div(None if not previous or e is None or previous[1] is None else e-previous[1],a),m,sig,div(hist,a),div(None if not previous or hist is None or previous[2] is None else hist-previous[2],a),r,None if not previous or r is None or previous[3] is None else r-previous[3],v,div(v,sum(self.vol)/60) if len(self.vol)==60 else math.nan)
  self.hist.append((a,e,hist,r));self.vol.append(v);self.prev=c
  return tuple(math.nan if x is None else x for x in vals)
def compute(inputs,out,spec,begin,end,history=1440):
 out.mkdir(exist_ok=True);descriptors=[];totals={};rawhashes={}
 for n in FRAMES:
  path=inputs/f'BTCUSDT-{n}m.csv.gz';logical=hashlib.sha256()
  with gzip.open(path,'rb') as f:
   for b in iter(lambda:f.read(1048576),b''):logical.update(b)
  if begin==ms(spec['analysis_start']):assert logical.hexdigest()==spec['canonical_fingerprints'][str(n)]['uncompressed_csv_sha256']
  rawhashes[str(n)]=logical.hexdigest();state=State();current=None;h=None;d=None;count=0;last=None
  def close():
   if h:h.close();d['sha256']=sha(out/d['file']);descriptors.append(d)
  with gzip.open(path,'rt',newline='') as f:
   reader=csv.reader(f);assert next(reader)==src.FIELDS
   for row in reader:
    t=int(row[0]);assert last is None or t-last==n*60000;assert int(row[6])==t+n*60000-1;last=t;values=state.step(row)
    if not begin-history*60000<=t<end:continue
    assert state.i>=200,'Insufficient historical warmup'
    month=dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime('%Y-%m')
    if month!=current:
     close();current=month;name=f'features-{n}m-{month}.bin';h=(out/name).open('wb');d={'file':name,'frame_minutes':n,'first_open_ms':t,'records':0,'nan_by_field':[0]*14}
    h.write(RECORD.pack(t,*values));d['records']+=1;count+=1
    for j,x in enumerate(values):d['nan_by_field'][j]+=math.isnan(x)
  close();totals[str(n)]=count
  assert count==(end-begin+history*60000)//(n*60000)
 result={'format':'little-endian int64 open_ms +14float64;120bytes/record','fields':spec['features_per_frame'],'history_start_ms':begin-history*60000,'analysis_start_ms':begin,'analysis_end_exclusive_ms':end,'counts':totals,'files':descriptors,'input_uncompressed_sha256':rawhashes,'future_labels_computed':False,'parameter_variants':0,'calculation_only':True}
 (out/'FEATURES.json').write_text(json.dumps(result,indent=2)+'\n');return result
def latest(out,manifest,frame,decision,offset=0):
 at=decision-offset*60000;target=(at//(frame*60000)-1)*frame*60000
 for d in manifest['files']:
  if d['frame_minutes']!=frame:continue
  index=(target-d['first_open_ms'])//(frame*60000)
  if 0<=index<d['records']:
   with (out/d['file']).open('rb') as f:f.seek(index*RECORD.size);record=RECORD.unpack(f.read(RECORD.size))
   assert record[0]+frame*60000<=at;return record
 return None
