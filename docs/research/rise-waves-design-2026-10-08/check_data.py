import hashlib,json,pathlib,datetime,collections
import pyarrow.parquet as pq
p=pathlib.Path(__file__).parent
b=(p/'SOL-small.parquet').read_bytes()
assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()=='08e03aa6c126d9fe94a8b8d519b399f8d48a67b9'
t=pq.read_table(p/'SOL-small.parquet').to_pydict(); n=len(t['open_time']); ts=t['open_time']
def iso(x):return datetime.datetime.fromtimestamp(x/1e6,datetime.timezone.utc).isoformat()
assert all(ts[i]-ts[i-1]==60_000_000 for i in range(1,n))
assert len(set(ts))==n
assert all(t['low'][i]<=min(t['open'][i],t['close'][i])<=max(t['open'][i],t['close'][i])<=t['high'][i] and t['volume'][i]>=0 for i in range(n))
period_start=1782864000000000 # 2026-07-01 UTC
period_end=1785542400000000 # 2026-08-01 UTC
out={'source_commit':'6d0226a03b84656e14b94dd8a37e39332cc2f68f','source_path':'data/SOLUSDT_1m.parquet','git_blob_sha':'08e03aa6c126d9fe94a8b8d519b399f8d48a67b9','sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'timestamp_unit':'microseconds','rows':n,'first_open':iso(ts[0]),'last_open':iso(ts[-1]),'duplicates':0,'missing_minutes':0,'invalid_ohlcv_rows':0,'design_period':['2026-07-01T00:00:00Z','2026-08-01T00:00:00Z'],'warmup':'2026-06-01..2026-06-30 UTC','signal_measurement':'NOT RUN','frames':{}}
for minutes in (15,60,240):
    groups=collections.defaultdict(list)
    for i,x in enumerate(ts):groups[x//(minutes*60_000_000)].append(i)
    assert all(len(ix)==minutes for ix in groups.values())
    rows=[]
    for k,ix in sorted(groups.items()):
        r={'open_time':k*minutes*60_000_000,'available_at':(k+1)*minutes*60_000_000,'open':t['open'][ix[0]],'high':max(t['high'][i] for i in ix),'low':min(t['low'][i] for i in ix),'close':t['close'][ix[-1]],'volume':sum(t['volume'][i] for i in ix)}
        rows.append(r)
    selected=[r for r in rows if period_start<=r['open_time']<period_end]
    out['frames'][str(minutes)+'m']={'complete_bars_full_source':len(rows),'complete_bars_design_period':len(selected),'expected_design_bars':31*1440//minutes,'last_available_at':iso(selected[-1]['available_at'])}
    assert len(selected)==31*1440//minutes
(p/'data-readiness.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
