import math,json,pathlib,tempfile,shutil
import waves as W

def main():
    c=[100+math.sin(i/8)+i*.1 for i in range(90)]
    # Independent EMA via explicit exponential sum (initial seed included).
    for n in (12,20,26,50):
        alpha=2/(n+1)
        for i,v in enumerate(W.ema(c,n)):
            ref=(1-alpha)**i*c[0]+sum(alpha*(1-alpha)**(i-j)*c[j] for j in range(1,i+1))
            assert math.isclose(v,ref,rel_tol=1e-12,abs_tol=1e-12)
    assert W.rsi([2.]*30)[14]==50
    assert W.rsi(list(range(30)))[14]==100
    assert W.rsi(list(range(30,0,-1)))[14]==0
    r=[[60*i,100,100,100,100,1] for i in range(10080)]
    for minutes in (15,60,240):
        b=W.aggregate(r,minutes);assert len(b)==len(r)//minutes and all(x[5]==minutes for x in b)
        assert all(x==0 for x in W.atr(b)[13:])
    assert W.outcome(r,0,100,1,24)=={'status':'FAIL','minutes':1440}
    r[3][2]=102
    assert W.outcome(r,0,100,1,24)=={'status':'SUCCESS','minutes':3}
    r[3][3]=99
    assert W.outcome(r,0,100,1,24)=={'status':'FAIL','minutes':3}
    assert W.outcome(r,len(r)-100,100,1,24)['status']=='CENSORED'
    for h in (24,168):assert W.outcome(r,0,100,1,h)==W.outcome(r,0,100,1,h,True)
    masks,_=W.signals([[1767225600+60*i,100,100,100,100,1] for i in range(5*1440)],15)
    assert all(not v for v in masks.values())
    assert len(W.metrics([]))==40 and all(x['precision'] is None for x in W.metrics([]))
    with tempfile.TemporaryDirectory() as t:
        W.run(t,True);a=pathlib.Path(t,'results.json').read_bytes();raw=pathlib.Path(t,'raw.json.gz').read_bytes()
        W.run(t,True);assert pathlib.Path(t,'results.json').read_bytes()==a and pathlib.Path(t,'raw.json.gz').read_bytes()==raw
    with tempfile.TemporaryDirectory() as t:
        root=pathlib.Path(t)
        for name in json.loads((W.ROOT/'checksums.json').read_text()):shutil.copyfile(W.ROOT/name,root/name)
        shutil.copyfile(W.ROOT/'checksums.json',root/'checksums.json');W.verify_source(root)
        (root/'scope.json').write_text('tampered')
        try:W.verify_source(root)
        except AssertionError:pass
        else:raise AssertionError('tamper accepted')
    # Actual source prefix checks only; no market scoring or rankings.
    real,_,_=W.load()
    for m in W.FRAMES:
        full,_=W.signals(real,m)
        pre,_=W.signals(real[:21*1440],m)
        cutoff=real[21*1440-1][0]+60
        assert all(pre[q]==[at for at in full[q] if at<=cutoff] for q in W.RULES)
    print('PASS: indicators, minute barriers, aggregation, flat/zero input, deterministic rerun, synthetic full path, real-prefix causality; MARKET SCORES NOT RUN')
if __name__=='__main__':main()
