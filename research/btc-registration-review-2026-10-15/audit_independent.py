"""Independent source/calendar admission, no indicators or outcome inspection."""
import calendar,csv,datetime as dt,gzip,hashlib,io,json,time,zipfile
from decimal import Decimal as D
from pathlib import Path
P=Path(__file__).parent;plan=json.loads((P/'review-plan.json').read_text());fixed=json.loads((P/'fixed-protocol.json').read_text());base=P/'remote/research/btc-registration-from-repo-2026-10-15/executor';out=P/'canonical';out.mkdir(exist_ok=True)
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def stamp(date):return int(dt.datetime.fromisoformat(date).replace(tzinfo=dt.timezone.utc).timestamp()*1000)
start=stamp(fixed['collection_start']);end=stamp(fixed['analysis_end_exclusive']);analysis=stamp(fixed['analysis_start']);duration=60000
started=time.time();actual_spec=json.loads((base/'protocol.json').read_text());frozen=json.loads((base/'result/frozen-protocol.json').read_text());manifest=json.loads((base/'data/manifest.json').read_text());registration=json.loads((base/'result/registration.json').read_text())
assert actual_spec==frozen
assert all(actual_spec[k]==v for k,v in fixed.items() if k not in ['input_manifest_sha256','frame_sha256'])
assert sha(base/'data/manifest.json')==actual_spec['input_manifest_sha256'];assert sha(base/'protocol.json')==registration['spec_sha256']
assert manifest['frame_sha256']==actual_spec['frame_sha256'];assert {r['month']:r['source_sha256'] for r in manifest['sources']}==fixed['source_sha256_by_month']
FIELDS=['open_time_ms','open','high','low','close','volume_base','close_time_ms','volume_quote','number_of_trades','taker_buy_volume_base','taker_buy_volume_quote','ignore']
files={};writers={};rawhandles={};counts={n:0 for n in [1,5,15,60]};totals={n:{i:D(0) for i in [5,7,8,9,10]} for n in counts};buckets={n:None for n in [5,15,60]};hashes={n:hashlib.sha256() for n in counts};monthly=[];next_open=start
def emit(n,row):
 writers[n].writerow(row);counts[n]+=1
 for i in totals[n]:totals[n][i]+=D(row[i])
def flush(n):
 b=buckets[n]
 if b is None:return
 assert b['rows']==n
 row=[str(b['t']),b['open'],str(b['high']),str(b['low']),b['close'],str(b['sums'][5]),str(b['t']+n*60000-1),str(b['sums'][7]),str(int(b['sums'][8])),str(b['sums'][9]),str(b['sums'][10]),'0'];emit(n,row)
for n in counts:
 path=out/f'BTCUSDT-{n}m.csv.gz';rawhandles[n]=path.open('wb');g=gzip.GzipFile(fileobj=rawhandles[n],mode='wb',filename='',mtime=0);files[n]=io.TextIOWrapper(g,encoding='utf-8',newline='');writers[n]=csv.writer(files[n]);writers[n].writerow(FIELDS)
try:
 for month,expected_sha in fixed['source_sha256_by_month'].items():
  archive=base/f'data/raw/BTCUSDT-1m-{month}.zip';assert sha(archive)==expected_sha
  assert (archive.with_suffix('.zip.CHECKSUM')).read_text().split()[0]==expected_sha
  nrows=0;first=None;last=None
  with zipfile.ZipFile(archive) as z:
   assert len(z.namelist())==1
   with z.open(z.namelist()[0]) as f:
    for row in csv.reader(io.TextIOWrapper(f)):
     assert len(row)==12
     raw_open,raw_close=int(row[0]),int(row[6]);assert raw_open%1000==0 and raw_close%1000==999
     t=raw_open//1000;assert t==next_open and raw_close//1000==t+59999;next_open+=60000
     row[0]=str(t);row[6]=str(t+59999);o,h,l,c,v,q,tb,tq=map(D,[row[i] for i in [1,2,3,4,5,7,9,10]])
     assert all(x.is_finite() for x in [o,h,l,c,v,q,tb,tq]);assert 0<l<=min(o,c)<=max(o,c)<=h and 0<=tb<=v and 0<=tq<=q and int(row[8])>=0
     assert l*v-D('.00000001')<=q<=h*v+D('.00000001');assert l*tb-D('.00000001')<=tq<=h*tb+D('.00000001')
     emit(1,row)
     for n,b in buckets.items():
      bucket=t//(n*60000)*(n*60000)
      if b is None or b['t']!=bucket:
       flush(n);b={'t':bucket,'rows':0,'open':row[1],'high':h,'low':l,'close':row[4],'sums':{i:D(0) for i in [5,7,8,9,10]}};buckets[n]=b
      b['rows']+=1;b['high']=max(b['high'],h);b['low']=min(b['low'],l);b['close']=row[4]
      for i in b['sums']:b['sums'][i]+=D(row[i])
     nrows+=1;first=t if first is None else first;last=t
  y,m=map(int,month.split('-'));assert nrows==calendar.monthrange(y,m)[1]*1440
  monthly.append({'month':month,'rows':nrows,'first_open_ms':first,'last_open_ms':last,'source_sha256':expected_sha})
 for n in buckets:flush(n)
finally:
 for f in files.values():f.close()
 for f in rawhandles.values():f.close()
assert next_open==end and {str(k):v for k,v in counts.items()}==fixed['expected_counts']
assert all(totals[n]==totals[1] for n in counts)
# Independent second pass: reconcile each saved higher bar against the saved minute stream.
for n in [5,15,60]:
 with gzip.open(out/'BTCUSDT-1m.csv.gz','rt',newline='') as f,gzip.open(out/f'BTCUSDT-{n}m.csv.gz','rt',newline='') as g:
  one=csv.reader(f);higher=csv.reader(g);assert next(one)==next(higher)==FIELDS;checked=0
  for bar in higher:
   rows=[next(one) for _ in range(n)];assert bar[0]==rows[0][0] and bar[1]==rows[0][1] and bar[4]==rows[-1][4] and int(bar[6])==int(rows[-1][6])
   assert D(bar[2])==max(D(r[2]) for r in rows) and D(bar[3])==min(D(r[3]) for r in rows)
   for i in [5,7,8,9,10]:assert D(bar[i])==sum((D(r[i]) for r in rows),D(0))
   checked+=1
  assert next(one,None) is None and checked==counts[n]
folds=[(r['name'],stamp(r['start']),stamp(r['end'])) for r in fixed['folds']];actual={name:{'feature_anchor_rows':0,'eligible_all_9_windows':0,'excluded_240min_boundary_rows':0,'eligible_by_window':{str(h):0 for h in fixed['future_windows_minutes']}} for name,_,_ in folds}
expected_anchor=analysis;calendar_rows=0
with gzip.open(base/'result/split-calendar.csv.gz','rt',newline='') as f:
 for row in csv.DictReader(f):
  t=int(row['anchor_open_ms']);decision=t+60000;assert t==expected_anchor and int(row['decision_ms'])==decision;expected_anchor+=60000
  name,low,high=next(x for x in folds if x[1]<=t<x[2]);assert row['split']==name and int(row['split_end_exclusive_ms'])==high
  good=decision+240*60000<=high;assert int(row['eligible_all_9_windows'])==good and int(row['boundary_excluded'])==int(not good)
  a=actual[name];a['feature_anchor_rows']+=1;a['eligible_all_9_windows']+=good;a['excluded_240min_boundary_rows']+=not good
  for h in fixed['future_windows_minutes']:a['eligible_by_window'][str(h)]+=decision+h*60000<=high
  calendar_rows+=1
assert expected_anchor==end and calendar_rows==525600 and actual==registration['splits']
fingerprints={}
for n in counts:
 h=hashlib.sha256()
 with gzip.open(out/f'BTCUSDT-{n}m.csv.gz','rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 fingerprints[str(n)]={'rows':counts[n],'canonical_gzip_sha256':sha(out/f'BTCUSDT-{n}m.csv.gz'),'uncompressed_csv_sha256':h.hexdigest()}
result={'status':'PASS_INDEPENDENT_SOURCE_AND_CALENDAR_ADMISSION','data_commit':plan['commit'],'receipt_state':'PUBLISHED_AND_IMMUTABLE_READBACK_VERIFIED_LEAD_REVIEW_PENDING','raw_months':13,'monthly':monthly,'reconstructed_counts':counts,'canonical_fingerprints':fingerprints,'all_higher_bars_full_field_reconciliation':'PASS','all_frame_additive_totals_equal':'PASS','calendar_rows':calendar_rows,'splits':actual,'eligible_all_windows':sum(v['eligible_all_9_windows'] for v in actual.values()),'scientific_definitions_unchanged':True,'publication_files_verified':40,'old_derived_transport_bytes_independently_read':False,'scope_bytes':sum(f.stat().st_size for f in P.rglob('*') if f.is_file()),'independent_compute_seconds':time.time()-started,'limits':['Original derived frame gzip files and35MBtransport were not published; their compressed-byte hashes are executor reports, not independently read original bytes. Lead rebuilt canonical frames from published immutable raw sources and fully reconciled their fields.','Entire original executor preparation-to-final-publication duration not measured;80.547s local pipeline and74.671s publication are separate components, not a continuous total.','Snapshot orderbook sample2023 is separate; year orderbook not provided.','No indicator values, recurrent states, forecast accuracy, fees, exits, trading or adoption measured. Historical splits not genuinely blind.']}
assert result['scope_bytes']<=125000000
(P/'INDEPENDENT-AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['monthly','canonical_fingerprints','splits','limits']}))
