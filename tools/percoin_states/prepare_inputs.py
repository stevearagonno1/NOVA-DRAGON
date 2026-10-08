import pathlib,csv,json,hashlib
import pyarrow.parquet as pq
P=pathlib.Path(__file__).parent;BEGIN=1780272000;END=1785542400
SOURCES={'BTC':(P/'BTC.parquet','data/BTCUSDT_1m.parquet','3d7c5d3f6c8f2dd45b2f53922a92d4d5f3930f23',1_000_000),'ETH':(P/'ETH.parquet','crypto_archive/ETHUSDT_1m.parquet','4f458623833ad59f94a3cdd65d9f3511d660ce7b',1000),'SOL':(P.parent/'rise_wave_design/SOL-small.parquet','data/SOLUSDT_1m.parquet','08e03aa6c126d9fe94a8b8d519b399f8d48a67b9',1_000_000)}
out={}
for asset,(file,path,blob,unit) in SOURCES.items():
 b=file.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob
 d=pq.read_table(file,filters=[('open_time','>=',BEGIN*unit),('open_time','<',END*unit)]).to_pydict();rows=[]
 for i,t in enumerate(d['open_time']):
  assert t%unit==0;rows.append([t//unit]+[d[k][i] for k in ['open','high','low','close','volume']])
 assert len(rows)==61*1440 and rows[0][0]==BEGIN and rows[-1][0]==END-60
 assert all(rows[i][0]-rows[i-1][0]==60 for i in range(1,len(rows)))
 f=P/(asset+'.csv')
 with f.open('w',newline='') as stream:w=csv.writer(stream);w.writerow(['open_time_seconds','open','high','low','close','volume']);w.writerows(rows)
 out[asset]={'commit':'6d0226a03b84656e14b94dd8a37e39332cc2f68f','path':path,'git_blob_sha':blob,'parquet_sha256':hashlib.sha256(b).hexdigest(),'source_timestamp_divisor':unit,'csv_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'rows':len(rows),'missing_minutes':0,'duplicates':0,'first':rows[0][0],'last':rows[-1][0]}
 del b,d,rows
(P/'sources.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
