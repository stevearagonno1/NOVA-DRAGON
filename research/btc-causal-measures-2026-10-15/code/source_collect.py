"""Binance immutable monthly-source collection and closed UTC-frame aggregation."""
import argparse,calendar,csv,datetime as dt,gzip,hashlib,io,json,os,time,urllib.request,zipfile
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).parent;BASE='https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/'
FIELDS=['open_time_ms','open','high','low','close','volume_base','close_time_ms','volume_quote','number_of_trades','taker_buy_volume_base','taker_buy_volume_quote','ignore']
MONTHS=['2025-09']+[f'2025-{m:02}' for m in range(10,13)]+[f'2026-{m:02}' for m in range(1,10)]
START=1756684800000;END=1790812800000;ANALYSIS=1759276800000;LIMIT=125000000

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def size(p):return sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
def budget(p):
 n=size(p)
 if n>LIMIT:raise RuntimeError('Scoped workspace exceeds125000000bytes; retain checkpoint; no automatic historical deletion')
 return n

def fetch(url,path,scope):
 if path.exists():return
 temp=path.with_suffix(path.suffix+'.part');path.parent.mkdir(parents=True,exist_ok=True)
 # A prior incomplete transfer is explicitly disposable own collector temporary output.
 with urllib.request.urlopen(url,timeout=40) as src,temp.open('wb') as dst:
  while b:=src.read(1048576):dst.write(b);budget(scope)
 os.replace(temp,path);budget(scope)

def normalize(r,unit):
 if len(r)!=12:raise ValueError('Expected12 columns')
 a=r.copy();factor=1000 if unit=='us' else 1;raw0=int(a[0]);raw6=int(a[6]);a[0]=str(raw0//factor);a[6]=str(raw6//factor)
 if raw0%factor or raw6%factor!=factor-1:raise ValueError('Timestamp unit boundary')
 t=int(a[0]);assert t%60000==0 and int(a[6])==t+59999
 o,h,l,c,v,q,tv,tq=map(D,[a[i] for i in [1,2,3,4,5,7,9,10]])
 assert all(x.is_finite() for x in [o,h,l,c,v,q,tv,tq]) and 0<l<=min(o,c)<=max(o,c)<=h
 assert 0<=tv<=v and 0<=tq<=q and int(a[8])>=0
 assert l*v-D('.00000001')<=q<=h*v+D('.00000001')
 assert l*tv-D('.00000001')<=tq<=h*tv+D('.00000001')
 return a

def aggregate(chunk,minutes):
 assert len(chunk)==minutes
 start=int(chunk[0][0]);assert start%(minutes*60000)==0
 assert [int(r[0]) for r in chunk]==list(range(start,start+minutes*60000,60000))
 r=chunk[0].copy();r[2]=str(max(D(x[2]) for x in chunk));r[3]=str(min(D(x[3]) for x in chunk));r[4]=chunk[-1][4];r[6]=str(start+minutes*60000-1)
 for i in [5,7,9,10]:r[i]=str(sum((D(x[i]) for x in chunk),D(0)))
 r[8]=str(sum(int(x[8]) for x in chunk));r[11]='0';return r

def source_rows(raw,months,receipts):
 for month in months:
  p=raw/f'BTCUSDT-1m-{month}.zip';cs=p.with_suffix('.zip.CHECKSUM');expected=cs.read_text().split()[0]
  if sha(p)!=expected:raise ValueError('Source checksum mismatch '+month)
  with zipfile.ZipFile(p) as z:
   names=z.namelist();assert len(names)==1 and names[0].endswith('.csv')
   count=0
   with z.open(names[0]) as file:
    for r in csv.reader(io.TextIOWrapper(file)):
     a=normalize(r,'us');count+=1;yield a
  y,m=map(int,month.split('-'));assert count==calendar.monthrange(y,m)[1]*1440
  receipts.append({'month':month,'url':BASE+p.name,'checksum_url':BASE+cs.name,'source_sha256':expected,'source_rows':count,'source_timestamp_unit':'microseconds','normalized_timestamp_unit':'milliseconds'})

def build(scope,months=MONTHS,start=START,end=END):
 out=scope/'frames';out.mkdir(exist_ok=True);receipts=[];files={};writers={};chunks={n:[] for n in [5,15,60]};counts={n:0 for n in [1,5,15,60]};next_t=start
 try:
  for n in counts:
   files[n]=gzip.open(out/f'BTCUSDT-{n}m.csv.gz','wt',newline='');writers[n]=csv.writer(files[n]);writers[n].writerow(FIELDS)
  for row in source_rows(scope/'raw',months,receipts):
   t=int(row[0]);assert t==next_t and start<=t<end;next_t+=60000;writers[1].writerow(row);counts[1]+=1
   for n in chunks:
    chunks[n].append(row)
    if len(chunks[n])==n:writers[n].writerow(aggregate(chunks[n],n));counts[n]+=1;chunks[n].clear()
   if counts[1]%10000==0:budget(scope)
  assert next_t==end and all(not x for x in chunks.values())
 finally:
  for f in files.values():f.close()
 budget(scope)
 manifest={'status':'COLLECTED_AND_AGGREGATED_PENDING_LEAD_ADMISSION','symbol':'BTCUSDT','market':'Spot','collection_start_ms':start,'collection_end_exclusive_ms':end,'analysis_start_ms':ANALYSIS,'warmup_minutes':43200,'analysis_minutes':525600,'counts':counts,'sources':receipts,'frame_sha256':{str(n):sha(out/f'BTCUSDT-{n}m.csv.gz') for n in counts},'closed_alignment':'frame available_at=open_time_ms+frame_minutes*60000; select latest available_at<=decision; raw close_time=end-1ms','future_labels_computed':False,'indicators_computed':False}
 (scope/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest

def audit(scope):
 m=json.loads((scope/'manifest.json').read_text());expected={1:568800,5:113760,15:37920,60:9480};checks={};firstlast={}
 for n in [1,5,15,60]:
  p=scope/'frames'/f'BTCUSDT-{n}m.csv.gz';assert sha(p)==m['frame_sha256'][str(n)];count=0;next_t=m['collection_start_ms'];first=None;last=None
  with gzip.open(p,'rt',newline='') as f:
   rr=csv.reader(f);assert next(rr)==FIELDS
   for r in rr:
    t=int(r[0]);assert t==next_t and t%(n*60000)==0 and int(r[6])==t+n*60000-1
    o,h,l,c=map(D,r[1:5]);assert 0<l<=min(o,c)<=max(o,c)<=h
    if first is None:first=t
    last=t;count+=1;next_t+=n*60000
  assert next_t==m['collection_end_exclusive_ms'];assert count==m['counts'][str(n)];checks[str(n)]={'rows':count,'hash_calendar_ohlc':'PASS'};firstlast[str(n)]=[first,last]
 # Rebuild higher frames independently from the saved normalized minute stream.
 with gzip.open(scope/'frames/BTCUSDT-1m.csv.gz','rt',newline='') as f:
  source=csv.reader(f);next(source);handles={n:gzip.open(scope/'frames'/f'BTCUSDT-{n}m.csv.gz','rt',newline='') for n in [5,15,60]};readers={n:csv.reader(h) for n,h in handles.items()};buffers={n:[] for n in handles};compared={n:0 for n in handles}
  for rr in readers.values():next(rr)
  for row in source:
   for n in buffers:
    buffers[n].append(row)
    if len(buffers[n])==n:
     b=buffers[n];target=next(readers[n]);assert target[0]==b[0][0] and target[1]==b[0][1] and target[4]==b[-1][4]
     assert D(target[2])==max(D(x[2]) for x in b) and D(target[3])==min(D(x[3]) for x in b)
     for i in [5,7,9,10]:assert D(target[i])==sum((D(x[i]) for x in b),D(0))
     assert int(target[8])==sum(int(x[8]) for x in b);compared[n]+=1;buffers[n].clear()
  for h in handles.values():h.close()
 result={'status':'PASS_AUTOMATED_DATA_CHECKS_LEAD_REVIEW_PENDING','frames':checks,'independently_reconciled_higher_bars':compared,'first_last_open_ms':firstlast,'source_checksums_verified_during_build':True,'scope_bytes':budget(scope),'indicator_measurement':False};(scope/'audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

def collect(scope,months=MONTHS,start=START,end=END):
 scope.mkdir(parents=True,exist_ok=True);budget(scope);raw=scope/'raw';raw.mkdir(exist_ok=True)
 for month in months:
  name=f'BTCUSDT-1m-{month}.zip';fetch(BASE+name+'.CHECKSUM',raw/(name+'.CHECKSUM'),scope);fetch(BASE+name,raw/name,scope)
  assert sha(raw/name)==(raw/(name+'.CHECKSUM')).read_text().split()[0]
 return build(scope,months=months,start=start,end=end)

def latest_closed(frame_opens,n,decision):
 import bisect
 k=bisect.bisect_right(frame_opens,decision-n*60000)-1
 return k if k>=0 else None

def main():
 a=argparse.ArgumentParser();a.add_argument('command',choices=['collect','build','audit','run']);a.add_argument('--scope',type=Path,default=Path('execution'));a.add_argument('--rehearsal-month',choices=['2025-09']);x=a.parse_args();start=time.time();budget(Path.cwd())
 if x.command in ['collect','run']:
  if x.rehearsal_month:
   m=collect(x.scope,months=['2025-09'],start=START,end=ANALYSIS);m['rehearsal_only']=True;m['analysis_minutes']=0;m['status']='ONE_MONTH_REHEARSAL_NOT_YEAR_RESULTS';(x.scope/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
  else:collect(x.scope)
 if x.command=='build':build(x.scope)
 if x.command in ['audit','run']:audit(x.scope)
 (x.scope/'execution-timing.json').write_text(json.dumps({'elapsed_seconds':time.time()-start,'command':x.command,'publication_not_included_in_this_timer':True})+'\n');print(json.dumps({'command':x.command,'status':'DONE','scope_bytes':size(x.scope)}))
if __name__=='__main__':main()

