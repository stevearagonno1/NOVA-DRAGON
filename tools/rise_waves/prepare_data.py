"""Lead-only input preparation; verifies immutable Parquet bytes, emits stdlib CSV."""
import pathlib,hashlib,json,csv,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
COMMIT='6d0226a03b84656e14b94dd8a37e39332cc2f68f';BLOB='08e03aa6c126d9fe94a8b8d519b399f8d48a67b9'
def main():
    import pyarrow.parquet as pq
    p=ROOT.parent/'SOL-small.parquet'
    if not p.exists():
        b=urllib.request.urlopen('https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/'+COMMIT+'/data/SOLUSDT_1m.parquet',timeout=45).read();p.write_bytes(b)
    b=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==BLOB
    t=pq.read_table(p).to_pydict();rows=[]
    for i,x in enumerate(t['open_time']):
        assert x%1_000_000==0
        rows.append([x//1_000_000]+[t[k][i] for k in ('open','high','low','close','volume')])
    with (ROOT/'minutes.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['open_time_seconds','open','high','low','close','volume']);w.writerows(rows)
    src={'commit':COMMIT,'path':'data/SOLUSDT_1m.parquet','git_blob_sha':BLOB,'parquet_sha256':hashlib.sha256(b).hexdigest(),'csv_sha256':hashlib.sha256((ROOT/'minutes.csv').read_bytes()).hexdigest(),'rows':len(rows)}
    (ROOT/'source.json').write_text(json.dumps(src,indent=2)+'\n')
if __name__=='__main__':main()
