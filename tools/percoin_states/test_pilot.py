import pathlib,json,math,tempfile
import pilot as R,math_core as I
raw,start,end=R.fixture()
a,states,_=R.masks(raw);b,refs,_=R.masks(raw,True);assert (a,states)==(b,refs)
assert all(s in (None,*R.STATES) for s in states)
assert len(R.GRID)==16
flat=[[1767225600+60*i,100,100,100,100,1] for i in range(5*1440)]
m,ss,_=R.masks(flat);assert all(s is None for s in ss) and all(not v for mm in m.values() for v in mm.values())
assert R.metric([])['precision'] is None
for h in R.HORIZONS:
 rr=[[60*i,100,100,100,100,1] for i in range(h*60)];rr[2][2]=104;rr[2][3]=98
 assert R.scan(rr,0,100,1,h)==R.scan(rr,0,100,1,h,True)==('FAIL',2)
for n in (20,50):
 c=[100+i*.1+math.sin(i/7) for i in range(90)];a=2/(n+1)
 for i,v in enumerate(I.ema(c,n)):
  ref=c[0]*(1-a)**i+sum(a*c[j]*(1-a)**(i-j) for j in range(1,i+1));assert math.isclose(v,ref,rel_tol=1e-12)
with tempfile.TemporaryDirectory() as t:
 R.run(t,True);a=pathlib.Path(t,'results.json').read_bytes();s=pathlib.Path(t,'selection.json').read_bytes();raw=pathlib.Path(t,'raw.json.gz').read_bytes()
 R.run(t,True);assert pathlib.Path(t,'results.json').read_bytes()==a and pathlib.Path(t,'selection.json').read_bytes()==s and pathlib.Path(t,'raw.json.gz').read_bytes()==raw
print('PASS: synthetic full144-candidate/288-row path;scalar states;causal prefixes;zero cases;exclusive state priority;minute barriers;EMA independent formula;deterministic results and selection')
