"""Short deterministic integrity tests; never market performance."""
import unittest,math,tempfile,json,gzip,random
from pathlib import Path
import numpy as np
import indicators84 as I,signals85 as S,research85 as R
class Checks(unittest.TestCase):
 def test_budget(self):
  g=S.catalogue();self.assertEqual(len(g),476);self.assertEqual(len(set(x['family'] for x in g)),32);self.assertEqual(sum(1 for _ in R.candidates(g)),339626)
 def test_matching_duplicates_zero(self):
  e=[{'onset':10,'mask':sum(1<<i for i in range(8,13))}]
  self.assertEqual(R.score(0,e),(0,0,0));self.assertEqual(R.score(sum(1<<i for i in [8,9,10,13]),e),(4,1,-2));self.assertEqual(R.score_reference(sum(1<<i for i in [8,9,10,13]),e),(4,1,-2))
 def test_modes_scalar(self):
  rng=random.Random(85)
  for _ in range(80):
   a=rng.getrandbits(70);b=rng.getrandbits(70);data=[((1<<70)-1,[a,b],[{'onset':30,'mask':sum(1<<i for i in range(28,33))}])]
   for mode in ['S',*R.MODES]:self.assertEqual(R.row_for((0,0,1,mode),data),R.row_for((0,0,1,mode),data,True))
 def test_ema_rsi_reference(self):
  c=np.array([100+math.sin(i/3)+i*.003 for i in range(100)])
  for n in [7,14,21]:
   x=c[0];e=[]
   for z in c:x=2/(n+1)*z+(1-2/(n+1))*x;e.append(x)
   self.assertTrue(np.allclose(I.ema(c,n)[n-1:],e[n-1:]))
   delta=np.diff(c);up=max(delta[0],0);dn=max(-delta[0],0);rs=[float('nan')]
   for z in delta:up=up*(1-1/n)+max(z,0)/n;dn=dn*(1-1/n)+max(-z,0)/n;rs.append(100-100/(1+up/dn) if dn else float('nan'))
   self.assertTrue(np.allclose(I.rsi(c,n)[n:],rs[n:],equal_nan=True))
 def test_bollinger_reference(self):
  c=np.array([100+math.sin(i/3) for i in range(100)]);l,m,h=I.bollinger(c,20,2)
  for i in range(19,len(c)):
   vals=list(c[i-19:i+1]);mean=sum(vals)/20;sd=math.sqrt(sum((x-mean)**2 for x in vals)/20);self.assertAlmostEqual(l[i],mean-2*sd,places=8)
 def test_labels_reference_boundaries(self):
  for d in R.fixture().values():
   e=R.labels(d,260,420);self.assertEqual([(x['onset'],x['hit']) for x in e],R.labels_reference(d,260,420));self.assertTrue(all(x['hit']<420 and x['onset']+24<420 for x in e));self.assertTrue(all(b['onset']-a['onset']>=25 for a,b in zip(e,e[1:])))
 def test_label_hand_tie_and_missing_horizon(self):
  n=100;c=np.full(n,100.);h=np.full(n,100.5);l=np.full(n,99.5);l[40]=99.;h[42]=110.
  d={'c':c,'h':h,'l':l};ev=R.labels(d,20,n);self.assertEqual([(e['onset'],e['hit']) for e in ev],[(40,42)])
  l[42]=90.;self.assertEqual(R.labels(d,20,n),[])
  l[42]=99.5;self.assertEqual(R.labels(d,20,60),[])
 def test_output_integrity_and_resume_short(self):
  # Actual writer/checkpoint/audit/report path; only this unit fixture narrows catalogue.
  original=S.catalogue;S.catalogue=lambda:original()[:6]
  try:
   with tempfile.TemporaryDirectory() as tmp:
    out=Path(tmp);R.run(out,True);before={p.name:p.read_bytes() for p in out.iterdir()};R.run(out,True)
    self.assertEqual(before,{p.name:p.read_bytes() for p in out.iterdir()})
    p=out/'scores-00000.csv.gz';p.write_bytes(p.read_bytes()+b'X')
    with self.assertRaises(AssertionError):R.audit(out)
  finally:S.catalogue=original
if __name__=='__main__':unittest.main()
