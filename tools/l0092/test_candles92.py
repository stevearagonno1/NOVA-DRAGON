import sys,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path('l0090/package').resolve()))
from candles92 import pattern,definitions
base={k:np.array([10.,9.,8.,7.,6.,6.,5.,5.4,5.,5.]) for k in ['o','h','l','c']}
def make(vals):
 d={k:v.copy() for k,v in base.items()}
 for i,ohlc in vals.items():
  for k,v in zip(['o','h','l','c'],ohlc):d[k][i]=v
 return d
hammer=make({7:(5.2,5.5,4.5,5.4)});assert pattern(hammer,definitions()[0])[7] and pattern(hammer,definitions()[1])[7]
engulf=make({6:(6.,6.1,4.9,5.),7:(5.,6.6,4.9,6.5)});assert pattern(engulf,definitions()[2])[7] and pattern(engulf,definitions()[3])[7]
star=make({5:(8.,8.2,5.8,6.),6:(6.,6.3,5.9,6.2),7:(6.2,7.6,6.1,7.5)});assert pattern(star,definitions()[4])[7] and not pattern(star,definitions()[5])[7]
for d in [hammer,engulf,star]:
 for q in definitions():assert np.array_equal(pattern(d,q),pattern(d,q,True))
print('HAND_FIXTURES_PASS: hammer,engulf,morning midpoint/full recovery distinctions')
