"""Causal indicator primitives and candidate conditions. Null is always invalid, never forward-filled.
FOREIGN_SOURCE: Wilder/EMA/ATR reference inspected in tools/percoin_states/math_core.py at 86304b62bf9c7d0914572e100892fac66f3f09dd; formulas independently implemented for this fixed grid.
"""
from math import sqrt

def _mean(v): return sum(v)/len(v) if v else None
def sma(x,n):
 out=[None]*len(x)
 for i in range(n-1,len(x)):
  w=x[i-n+1:i+1]
  if all(v is not None for v in w): out[i]=sum(w)/n
 return out
def ema(x,n):
 out=[None]*len(x); acc=None; seen=0; a=2/(n+1)
 for i,v in enumerate(x):
  if v is None: acc=None; seen=0; continue
  acc=v if acc is None else a*v+(1-a)*acc; seen+=1
  if seen>=n: out[i]=acc
 return out
def wilder(x,n):
 out=[None]*len(x); buf=[]; acc=None
 for i,v in enumerate(x):
  if v is None: buf=[]; acc=None; continue
  if acc is None:
   buf.append(v)
   if len(buf)==n: acc=sum(buf)/n; out[i]=acc
  else: acc=((n-1)*acc+v)/n; out[i]=acc
 return out
def tr_atr(bars,n=14):
 tr=[]
 for i,b in enumerate(bars):
  if i==0: tr.append(b['high']-b['low'])
  else:
   c=bars[i-1]['close']; tr.append(max(b['high']-b['low'],abs(b['high']-c),abs(b['low']-c)))
 return tr,wilder(tr,n)
def rsi(close,n):
 out=[None]*len(close); changes=[None]
 for i in range(1,len(close)): changes.append(close[i]-close[i-1] if close[i] is not None and close[i-1] is not None else None)
 gains=[None if d is None else max(d,0) for d in changes]; losses=[None if d is None else max(-d,0) for d in changes]
 ag=wilder(gains,n); al=wilder(losses,n)
 for i,(g,l) in enumerate(zip(ag,al)):
  if g is None or l is None: continue
  out[i]=50 if g==0 and l==0 else (100 if l==0 else 100-100/(1+g/l))
 return out
def cross_up(x,y):
 out=[False]*len(x)
 for i in range(1,len(x)):
  if None not in (x[i-1],y[i-1],x[i],y[i]): out[i]=x[i-1]<=y[i-1] and x[i]>y[i]
 return out
def cross_level(x,t):
 out=[False]*len(x)
 for i in range(1,len(x)):
  if x[i-1] is not None and x[i] is not None: out[i]=x[i-1]<t and x[i]>=t
 return out
def _bars_features(bars):
 n=len(bars); O=[b['open'] for b in bars]; H=[b['high'] for b in bars]; L=[b['low'] for b in bars]; C=[b['close'] for b in bars]; V=[b['volume'] for b in bars]; TP=[(h+l+c)/3 for h,l,c in zip(H,L,C)]
 return O,H,L,C,V,TP
def rolling_extreme(x,n,prior=False,which=max):
 out=[None]*len(x)
 for i in range(len(x)):
  end=i if prior else i+1; start=end-n
  if start<0 or end>len(x): continue
  w=x[start:end]
  if all(v is not None for v in w): out[i]=which(w)
 return out
def cci(bars,n):
 _,H,L,C,_,TP=_bars_features(bars); out=[None]*len(C)
 for i in range(n-1,len(C)):
  w=TP[i-n+1:i+1]; m=sum(w)/n; md=sum(abs(q-m) for q in w)/n
  if md: out[i]=(TP[i]-m)/(.015*md)
 return out
def stochastic(bars,n):
 _,H,L,C,_,_=_bars_features(bars); hi=rolling_extreme(H,n); lo=rolling_extreme(L,n); out=[None]*len(C)
 for i in range(len(C)):
  if hi[i] is not None and hi[i]!=lo[i]: out[i]=100*(C[i]-lo[i])/(hi[i]-lo[i])
 return out
def williams(bars,n):
 _,H,L,C,_,_=_bars_features(bars); hi=rolling_extreme(H,n); lo=rolling_extreme(L,n); out=[None]*len(C)
 for i in range(len(C)):
  if hi[i] is not None and hi[i]!=lo[i]: out[i]=-100*(hi[i]-C[i])/(hi[i]-lo[i])
 return out
def mfi(bars,n):
 _,_,_,C,V,TP=_bars_features(bars); pos=[None]; neg=[None]
 for i in range(1,len(C)):
  raw=TP[i]*V[i]
  pos.append(raw if TP[i]>TP[i-1] else 0); neg.append(raw if TP[i]<TP[i-1] else 0)
 out=[None]*len(C)
 for i in range(n,len(C)):
  p=pos[i-n+1:i+1]; q=neg[i-n+1:i+1]
  if any(x is None for x in p+q): continue
  ps=sum(p); ns=sum(q); out[i]=50 if ps==0 and ns==0 else (100 if ns==0 else 100-100/(1+ps/ns))
 return out
def cmf(bars,n):
 _,H,L,C,V,_=_bars_features(bars); mf=[]
 for h,l,c,v in zip(H,L,C,V): mf.append((0 if h==l else ((2*c-h-l)/(h-l))*v))
 out=[None]*len(C)
 for i in range(n-1,len(C)):
  vs=sum(V[i-n+1:i+1])
  if vs: out[i]=sum(mf[i-n+1:i+1])/vs
 return out
def macd(bars,fast,slow,signal):
 C=[b['close'] for b in bars]; f=ema(C,fast); s=ema(C,slow); line=[None if a is None or b is None else a-b for a,b in zip(f,s)]; sig=ema(line,signal)
 return line,sig
def bands(bars,n,k):
 C=[b['close'] for b in bars]; m=sma(C,n); lo=[None]*len(C); hi=[None]*len(C)
 for i in range(n-1,len(C)):
  w=C[i-n+1:i+1]; sd=sqrt(sum((v-m[i])**2 for v in w)/n); lo[i]=m[i]-k*sd; hi[i]=m[i]+k*sd
 return lo,hi
def roc(bars,n):
 C=[b['close'] for b in bars]; out=[None]*len(C)
 for i in range(n,len(C)):
  if C[i-n]!=0: out[i]=100*(C[i]/C[i-n]-1)
 return out
def aroon(bars,n):
 H=[b['high'] for b in bars]; L=[b['low'] for b in bars]; up=[None]*len(H); dn=[None]*len(H)
 for i in range(n,len(H)):
  hh=H[i-n:i+1]; ll=L[i-n:i+1]
  # latest extreme wins
  up[i]=100*max(j for j,v in enumerate(hh) if v==max(hh))/n
  dn[i]=100*max(j for j,v in enumerate(ll) if v==min(ll))/n
 return up,dn
def obv(bars):
 C=[b['close'] for b in bars]; V=[b['volume'] for b in bars]; out=[0.0]*len(C)
 for i in range(1,len(C)): out[i]=out[i-1]+(V[i] if C[i]>C[i-1] else -V[i] if C[i]<C[i-1] else 0)
 return out
def adx(bars,n):
 H=[b['high'] for b in bars]; L=[b['low'] for b in bars]; up=[0.0]; dn=[0.0]
 for i in range(1,len(H)):
  u=H[i]-H[i-1]; d=L[i-1]-L[i]; up.append(u if u>d and u>0 else 0.0); dn.append(d if d>u and d>0 else 0.0)
 _,atr=tr_atr(bars,n); p=wilder(up,n); m=wilder(dn,n); pi=[None]*len(H); mi=[None]*len(H); dx=[None]*len(H)
 for i in range(len(H)):
  if atr[i] is None or atr[i]==0: continue
  pi[i]=100*p[i]/atr[i]; mi[i]=100*m[i]/atr[i]; denom=pi[i]+mi[i]; dx[i]=0 if denom==0 else 100*abs(pi[i]-mi[i])/denom
 return wilder(dx,n),pi,mi

def conditions(bars, registry):
 """Return setting_id -> Boolean vector; all computations causal and deterministic."""
 C=[b['close'] for b in bars]; V=[b['volume'] for b in bars]; out={}
 cache={}
 def get(key,fn):
  if key not in cache: cache[key]=fn()
  return cache[key]
 for r in registry:
  f=r['family']; p=r['params']; n=p.get('n'); cond=[False]*len(C)
  if f=='RSI_LEVEL': cond=cross_level(get(('rsi',n),lambda:rsi(C,n)),p['t'])
  elif f=='STOCH_LEVEL': cond=cross_level(get(('stoch',n),lambda:stochastic(bars,n)),p['t'])
  elif f=='STOCH_KD':
   k=get(('stoch',n),lambda:stochastic(bars,n)); d=sma(k,p['d']); cond=[a and k[i] is not None and k[i]<=p['t'] for i,a in enumerate(cross_up(k,d))]
  elif f=='CCI_LEVEL': cond=cross_level(get(('cci',n),lambda:cci(bars,n)),p['t'])
  elif f=='WILLIAMS_LEVEL': cond=cross_level(get(('will',n),lambda:williams(bars,n)),p['t'])
  elif f=='MFI_LEVEL': cond=cross_level(get(('mfi',n),lambda:mfi(bars,n)),p['t'])
  elif f=='CMF_LEVEL': cond=cross_level(get(('cmf',n),lambda:cmf(bars,n)),p['t'])
  elif f=='PRICE_EMA': cond=cross_up(C,get(('ema',n),lambda:ema(C,n)))
  elif f=='EMA_CROSS': cond=cross_up(get(('ema',p['fast']),lambda:ema(C,p['fast'])),get(('ema',p['slow']),lambda:ema(C,p['slow'])))
  elif f=='MACD_CROSS':
   a,b=get(('macd',p['fast'],p['slow'],p['signal']),lambda:macd(bars,p['fast'],p['slow'],p['signal'])); cond=cross_up(a,b)
  elif f=='BB_RECLAIM_BREAK':
   lo,hi=get(('bb',n,p['k']),lambda:bands(bars,n,p['k'])); cond=cross_up(C,lo if p['mode']=='LOWER' else hi)
  elif f=='DONCHIAN':
   if p['mode']=='UPPER':
    top=rolling_extreme([b['high'] for b in bars],n,prior=True); cond=[top[i] is not None and C[i]>top[i] for i in range(len(C))]
   else:
    top=rolling_extreme([b['high'] for b in bars],n,prior=True); bot=rolling_extreme([b['low'] for b in bars],n,prior=True,which=min); mid=[None if a is None or b is None else (a+b)/2 for a,b in zip(top,bot)]; cond=cross_up(C,mid)
  elif f=='ROC_LEVEL': cond=cross_level(get(('roc',n),lambda:roc(bars,n)),p['t'])
  elif f=='AROON_CROSS':
   a,b=get(('aroon',n),lambda:aroon(bars,n)); cond=cross_up(a,b)
  elif f=='OBV_EMA': cond=cross_up(get(('obv',),lambda:obv(bars)),get(('obve',n),lambda:ema(obv(bars),n)))
  elif f=='RVOL_STATE':
   cond=[False]*len(C)
   for i in range(n,len(C)):
    m=sum(V[i-n:i])/n
    if m and V[i]/m>=p['t']: cond[i]=True
  elif f=='ADX_DIRECTION':
   a,pi,mi=get(('adx',n),lambda:adx(bars,n)); cond=[i>0 and a[i] is not None and a[i-1] is not None and a[i]>=p['t'] and a[i]>a[i-1] and pi[i] is not None and mi[i] is not None and pi[i]>mi[i] for i in range(len(C))]
  out[r['setting_id']]=cond
 return out

# Independent scalar audit implementation: intentionally direct, no production helpers used.
def independent_ema(x,n):
 z=[None]*len(x); prev=None; count=0; alpha=2/(n+1)
 for i in range(len(x)):
  v=x[i]
  if v is None: prev=None; count=0
  else:
   prev=v if prev is None else alpha*v+(1-alpha)*prev; count+=1
   if count>=n:z[i]=prev
 return z
def independent_rsi(close,n):
 out=[None]*len(close); vals=[]; ag=al=None
 for i in range(1,len(close)):
  d=close[i]-close[i-1]; g=max(0,d); l=max(0,-d); vals.append((g,l))
  if ag is None:
   if len(vals)==n: ag=sum(x[0] for x in vals)/n; al=sum(x[1] for x in vals)/n
  else: ag=((n-1)*ag+g)/n; al=((n-1)*al+l)/n
  if ag is not None: out[i]=50 if ag==al==0 else 100 if al==0 else 100-100/(1+ag/al)
 return out
