"""36 preregistered causal singleton signals; separate scalar reference."""
import math
import numpy as np
import pandas as pd

def catalogue():
 out=[]
 def add(f,**q):out.append({'id':f+'_'+ '_'.join(str(v) for v in q.values()),'family':f,**q})
 for n in [10,20,30]:
  for k in [2,2.5]:add('BB',n=n,k=k)
 for n in [10,14,21]:
  for t in [-150,-100]:add('CCI',n=n,t=t)
 for n in [10,20,30]:add('EMA_RECLAIM',n=n)
 for n in [10,20,40]:add('DONCHIAN_RECLAIM',n=n)
 for f,s in [(5,20),(10,30),(20,50)]:add('OBV_EMA',fast=f,slow=s)
 for n in [1,3,6]:
  for t in [.52,.56]:add('TAKER_PRESSURE',n=n,t=t)
 for n in [20,30]:add('SQUEEZE_BREAK',n=n)
 for n in [10,14,21]:
  for t in [30,40]:add('RSI_RECLAIM',n=n,t=t)
 add('MACD_REFERENCE',fast=12,slow=26,signal=9)
 assert len(out)==36 and len({x['id'] for x in out})==36
 return out

def primitives(d,scalar=False):
 c,h,l,v,t=[np.asarray(d[k],float) for k in ['c','h','l','v','tbv']];N=len(c)
 def roll(x,n,kind):
  if not scalar:return getattr(pd.Series(x).rolling(n,min_periods=n),kind)().to_numpy()
  a=np.full(N,np.nan)
  for i in range(n-1,N):
   z=x[i-n+1:i+1]
   if not np.isfinite(z).all():continue
   a[i]=sum(z)/n if kind=='mean' else sum(z) if kind=='sum' else min(z) if kind=='min' else max(z)
  return a
 def ema(x,n,alpha=None):
  alpha=2/(n+1) if alpha is None else alpha
  if not scalar:return pd.Series(x).ewm(alpha=alpha,adjust=False,min_periods=n).mean().to_numpy()
  a=np.full(N,np.nan);s=None;count=0
  for i,val in enumerate(x):
   if not math.isfinite(val):continue
   s=val if s is None else (1-alpha)*s+alpha*val;count+=1
   if count>=n:a[i]=s
  return a
 def cross(x,y,through=False):
  if np.isscalar(y):y=np.full(N,y)
  return np.r_[False,(x[:-1]<y[:-1] if through else x[:-1]<=y[:-1])&(x[1:]>=y[1:] if through else x[1:]>y[1:])]
 def shift(x):return np.r_[np.nan,x[:-1]]
 tp=(h+l+c)/3;obv=np.cumsum(np.r_[0,np.sign(np.diff(c))]*v);out={}
 for q in catalogue():
  f=q['family'];n=q.get('n')
  if f in ['BB','SQUEEZE_BREAK']:
   mean=roll(c,n,'mean')
   if scalar:sd=np.array([math.sqrt(sum((z-mean[i])**2 for z in c[i-n+1:i+1])/n) if i>=n-1 else np.nan for i in range(N)])
   else:sd=pd.Series(c).rolling(n,min_periods=n).std(ddof=0).to_numpy()
   if f=='BB':band=mean-q['k']*sd;truth=(l<=band)&(c>band)
   else:
    width=4*sd/mean;prev=shift(width)
    if scalar:
     threshold=np.array([float(np.quantile(prev[i-119:i+1],.2,method='linear')) if i>=119 and np.isfinite(prev[i-119:i+1]).all() else np.nan for i in range(N)])
    else:threshold=pd.Series(prev).rolling(120,min_periods=120).quantile(.2,interpolation='linear').to_numpy()
    squeeze=width<=threshold;breakout=c>roll(shift(h),20,'max');truth=np.zeros(N,bool)
    if not scalar:
     armed=None
     for i in range(N):
      if squeeze[i] and (i==0 or not squeeze[i-1]):armed=i
      if armed is not None and i-armed>2:armed=None
      if armed is not None and breakout[i]:truth[i]=True;armed=None
    else:
     deadline=-1;previous=False
     for i,(sq,bk) in enumerate(zip(squeeze,breakout)):
      if sq and not previous:deadline=i+2
      if i<=deadline and bk:truth[i]=True;deadline=-1
      previous=bool(sq)
  elif f=='CCI':
   mean=roll(tp,n,'mean')
   dev=np.array([sum(abs(z-mean[i]) for z in tp[i-n+1:i+1])/n if i>=n-1 else np.nan for i in range(N)])
   x=np.divide(tp-mean,.015*dev,out=np.full(N,np.nan),where=dev>0);truth=cross(np.round(x,10),q['t'],True)
  elif f=='EMA_RECLAIM':truth=cross(c,ema(c,n))
  elif f=='DONCHIAN_RECLAIM':bottom=roll(shift(l),n,'min');truth=(l<bottom)&(c>bottom)
  elif f=='OBV_EMA':truth=cross(ema(obv,q['fast']),ema(obv,q['slow']))
  elif f=='TAKER_PRESSURE':total=roll(v,n,'sum');x=roll(t,n,'sum')/total;truth=cross(x,q['t'],True)
  elif f=='RSI_RECLAIM':
   delta=np.r_[np.nan,np.diff(c)];up=ema(np.maximum(delta,0),n,1/n);dn=ema(np.maximum(-delta,0),n,1/n);rs=np.divide(up,dn,out=np.full(N,np.nan),where=dn>0);x=100-100/(1+rs);truth=cross(x,q['t'],True)
  elif f=='MACD_REFERENCE':
   line=ema(c,q['fast'])-ema(c,q['slow']);truth=cross(line,ema(line,q['signal']))
  else:raise ValueError(f)
  out[q['id']]=truth & ~np.r_[False,truth[:-1]]
 return out
