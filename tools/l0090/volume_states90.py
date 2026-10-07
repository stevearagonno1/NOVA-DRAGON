"""Causal persistent states, independent rolling/EMA scalar reference."""
import numpy as np
import pandas as pd

def states(d,scalar=False):
 c,v,t=[np.asarray(d[k],float) for k in ['c','v','tbv']];N=len(c);out={}
 for n in [1,3,6]:
  if scalar:
   total=np.array([sum(v[i-n+1:i+1]) if i>=n-1 else np.nan for i in range(N)])
   buys=np.array([sum(t[i-n+1:i+1]) if i>=n-1 else np.nan for i in range(N)])
  else:
   total=pd.Series(v).rolling(n,min_periods=n).sum().to_numpy();buys=pd.Series(t).rolling(n,min_periods=n).sum().to_numpy()
  ratio=np.divide(buys,total,out=np.full(N,np.nan),where=total>0)
  for threshold in [.52,.56]:out[f'TAKER_PRESSURE_{n}_{threshold}']=np.isfinite(ratio)&(np.round(ratio,10)>=threshold)
 if scalar:
  obv=np.zeros(N)
  for i in range(1,N):obv[i]=obv[i-1]+(1 if c[i]>c[i-1] else -1 if c[i]<c[i-1] else 0)*v[i]
 else:obv=np.cumsum(np.r_[0,np.sign(np.diff(c))]*v)
 def ema(span):
  if not scalar:return pd.Series(obv).ewm(span=span,adjust=False,min_periods=span).mean().to_numpy()
  x=np.full(N,np.nan);current=None;a=2/(span+1)
  for i,val in enumerate(obv):
   current=val if current is None else (1-a)*current+a*val
   if i+1>=span:x[i]=current
  return x
 for f,s in [(5,20),(10,30),(20,50)]:
  fast,slow=ema(f),ema(s);out[f'OBV_EMA_{f}_{s}']=np.isfinite(fast)&np.isfinite(slow)&(np.round(fast-slow,10)>0)
 return out
