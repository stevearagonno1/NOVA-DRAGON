"""Read immutable delivered bytes; independently recompute a stratified Decimal sample.
No executor calculation functions are imported. Raw candles are reused read-only.
"""
import concurrent.futures as futures
import collections
import csv
from decimal import Decimal as D, localcontext
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / 'registration_lead_review/canonical'
PIN = '87d68c79e5e0263ce7c5ecf558761996a0e988d3'
BASE = 'https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/' + PIN + '/research/btc-causal-measures-2026-10-15/execution/'
RECORD = struct.Struct('<q14d')
manifest = json.loads((ROOT/'FEATURES.json').read_text())
remote = {f['name']:f for f in json.loads((ROOT/'REMOTE-FILES.json').read_text())}
started = time.time()
(ROOT/'ESTIMATE.json').write_text(json.dumps({'scope':'read-only independent review plus work-branch evidence publication','estimated_seconds':{'read_and_prepare':90,'remote_bytes_and_checks':180,'decimal_reference':120,'publish_and_readback':60},'estimated_total_seconds':450,'uncertainty':'Network latency may increase time; no binary files are copied to disk. Prior inspection start not captured; whole-turn measured time unavailable.'},indent=2)+'\n')

def inspect_file(meta):
    with urllib.request.urlopen(BASE+meta['file'], timeout=45) as response:
        data = response.read()
    entry = remote[meta['file']]
    assert len(data) == meta['records']*120 == entry['size']
    assert hashlib.sha256(data).hexdigest() == meta['sha256']
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == entry['sha']
    nan = [0]*14
    targets = {0,meta['records']//2,meta['records']-1}
    sample = {}
    for i,row in enumerate(RECORD.iter_unpack(data)):
        assert row[0] == meta['first_open_ms']+i*meta['frame_minutes']*60000
        for k,x in enumerate(row[1:]):
            assert not math.isinf(x)
            nan[k] += math.isnan(x)
        if i in targets:
            sample[row[0]] = row[1:]
    assert nan == meta['nan_by_field']
    return {'file':meta['file'],'frame':meta['frame_minutes'],'records':meta['records'],'bytes':len(data),'sha256':meta['sha256'],'first':meta['first_open_ms'],'last':row[0],'sample':sample}

with futures.ThreadPoolExecutor(max_workers=4) as pool:
    checked = list(pool.map(inspect_file,manifest['files']))
print('All immutable binary hashes, sizes, timestamps and NaN counts checked.',flush=True)
assert len(checked) == 52
assert sum(f['records'] for f in checked)==676368
assert sum(f['bytes'] for f in checked)==81164160
sampled = {}; frame_summary = {}
for frame in (1,5,15,60):
    fs = sorted((f for f in checked if f['frame']==frame),key=lambda f:f['first'])
    expected_start = manifest['history_start_ms']
    for f in fs:
        assert f['first']==expected_start
        expected_start=f['last']+frame*60000
    assert expected_start==manifest['analysis_end_exclusive_ms']
    assert sum(f['records'] for f in fs)==manifest['counts'][str(frame)]
    sampled[frame]={t:r for f in fs for t,r in f['sample'].items()}
    frame_summary[frame]={'records':sum(f['records'] for f in fs),'sample_records':len(sampled[frame])}

class Average:
    def __init__(self,n,wilder=False):
        self.n=n;self.weight=D(1)/D(n) if wilder else D(2)/D(n+1)
        self.seed=[];self.value=None
    def update(self,x):
        if x is None:return None
        if self.value is None:
            self.seed.append(x)
            if len(self.seed)==self.n:self.value=sum(self.seed)/D(self.n)
        else:self.value=(D(1)-self.weight)*self.value+self.weight*x
        return self.value

comparisons=0;max_error=0.;input_hashes={}
for frame in (1,5,15,60):
    source=INPUT/f'BTCUSDT-{frame}m.csv.gz'
    dig=hashlib.sha256()
    with gzip.open(source,'rb') as f:
        for block in iter(lambda:f.read(1048576),b''):dig.update(block)
    assert dig.hexdigest()==manifest['input_uncompressed_sha256'][str(frame)]
    input_hashes[str(frame)]=dig.hexdigest()
    with localcontext() as ctx,gzip.open(source,'rt',newline='') as f:
        ctx.prec=50
        atr=Average(14,True);ema=Average(20);fast=Average(12);slow=Average(26);signal=Average(9)
        gain=Average(14,True);loss=Average(14,True)
        history=collections.deque(maxlen=5);volumes=collections.deque(maxlen=60)
        previous=None;seen=set();rows=csv.reader(f);next(rows)
        input_rows=0;last_t=None
        for row in rows:
            t=int(row[0]);o,h,l,c,v=map(D,row[1:6]);input_rows+=1
            if last_t is not None:assert t-last_t==frame*60000
            last_t=t
            tr=h-l if previous is None else max(h-l,abs(h-previous),abs(l-previous))
            a=atr.update(tr);e=ema.update(c);fa=fast.update(c);sl=slow.update(c)
            m=None if sl is None else fa-sl;s=signal.update(m);hi=None if s is None else m-s
            change=None if previous is None else c-previous
            g=gain.update(None if change is None else max(change,D(0)))
            lo=loss.update(None if change is None else max(-change,D(0)))
            r=None if g is None else D(50) if g==lo==0 else D(100) if lo==0 else D(100)*g/(g+lo)
            if t in sampled[frame]:
                assert len(history)==5 and len(volumes)==60
                past=history[0]
                ref=[a,100*a/c,a/past[0]-1,e,(c-e)/a,(e-past[1])/a,m,s,hi/a,(hi-past[2])/a,r,r-past[3],v,v/(sum(volumes)/60)]
                for k,(expected,actual) in enumerate(zip(ref,sampled[frame][t])):
                    err=abs(float(expected)-actual);max_error=max(max_error,err)
                    assert math.isclose(float(expected),actual,rel_tol=1e-10,abs_tol=1e-8),(frame,t,k,str(expected),actual)
                    comparisons+=1
                seen.add(t)
            history.append((a,e,hi,r));volumes.append(v);previous=c
        assert seen==set(sampled[frame])
        assert input_rows==568800//frame
        frame_summary[frame]['input_rows']=input_rows
    print('Independent Decimal reference complete for '+str(frame)+'m.',flush=True)

result={'status':'PASS_INDEPENDENT_DELIVERY_AND_STRATIFIED_NUMERIC_REVIEW','reviewed_commit':PIN,'source_commit':'55cbdbced8c70acf4a3f500e19a559a9bbae617d','binary_files_verified':len(checked),'binary_records_checked':sum(f['records'] for f in checked),'binary_bytes':sum(f['bytes'] for f in checked),'independent_decimal_field_comparisons':comparisons,'max_absolute_decimal_difference':max_error,'frame_summary':frame_summary,'input_uncompressed_sha256':input_hashes,'review_script_elapsed_seconds':time.time()-started,'whole_turn_elapsed_seconds':'not measured; initial inspection start not captured','limits':['Numeric recalculation sampled first, middle and last record of every frame-month; it is not an independent recalculation of every published field.','Executor timing and prefix-check counts were read from its audit; no claim that those specific checks were independently repeated.','Executor resource and elapsed-time reports cannot be independently measured after its run.','No predictive accuracy, market-state discovery, entry-signal comparison or financial performance measured.'],'reproduce':'python3 causal_year_review/independent_review.py'}
(ROOT/'INDEPENDENT-REVIEW.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False),flush=True)
