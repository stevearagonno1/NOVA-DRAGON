"""L0085 causal indicator grid; reuses pinned L0084 numerical primitives.
New definitions are versioned here; no L0084 file or locked trading engine changes.
"""
import itertools
import numpy as np
import pandas as pd
import indicators84 as I
N=[7,10,14,21,28]
def catalogue():
    g=[]
    def add(f,**axes):
        for p in itertools.product(*axes.values()):
            d={'family':f,**dict(zip(axes,p))};d['id']=f+'_'+ '_'.join(str(x) for x in p);g.append(d)
    add('RSI',n=N,t=[15,20,25,30,35,40],form=['cross','state'])
    add('STOCH',n=N,d=[3,5],t=[15,20,25,30])
    add('STOCHRSI',n=[7,14,21],t=[.1,.2,.3])
    add('WR',n=N,t=[-90,-80,-70])
    add('CCI',n=N,t=[-150,-100,-50])
    for f in ['DIV_RSI','DIV_MACD','DIV_OBV','DIV_TAKER']:add(f,look=[20,40,60],right=[2,3])
    add('VOLZ',n=[20,50,100],t=[1.5,2,2.5,3],upper=[.5,2/3])
    add('TAKERZ',n=[20,50,100],t=[1,1.5,2,2.5])
    add('FORCE',n=[2,7,13,21])
    add('CMF',n=[10,14,20,30,50],t=[0,.05,.1])
    add('SWEEP',n=[5,10,20,40,55],depth=[0,.25,.5])
    add('FVG',gap=[0,.1,.25,.5])
    add('BOS',n=[3,5,10],look=[10,20,40])
    add('DONCHIAN_FAIL',n=[10,20,40,55])
    add('HAMMER',lower=[1.5,2,3],upper=[.25,.5,1],bottom=[3,5,10])
    add('ENGULF',bottom=[3,5,10])
    add('EMA',fast=[5,10,20,50],slow=[20,30,50,100,200])
    g=[x for x in g if x['family']!='EMA' or x['fast']<x['slow']]
    add('MACD',fast=[5,8,12,19],slow=[21,26,35,39],signal=[5,9])
    add('SUPERTREND',n=[7,10,14,21],k=[1.5,2,2.5,3])
    add('DMI',n=[7,14,21],t=[15,20,25,30])
    add('AROON',n=[7,14,21,25,50])
    add('VORTEX',n=[7,14,21,28])
    add('BB',n=[10,20,30,50],k=[1.5,2,2.5,3])
    add('KELTNER',n=[10,20,30,50],k=[1,1.5,2,2.5])
    add('VWAP',n=[10,20,30,50],k=[1,1.5,2,2.5])
    add('MFI',n=N,t=[15,20,25,30],form=['cross','state'])
    add('PXEMA',n=[10,20,30,50,100,200])
    add('DONCHIAN_BREAK',n=[5,10,20,40,55])
    add('TAKER',t=[.45,.48,.5,.52,.55,.58],form=['cross','state'])
    assert len({x['id'] for x in g})==len(g)
    return sorted(g,key=lambda x:x['id'])
def roll(x,n,what):return getattr(pd.Series(x).rolling(n,min_periods=n),what)().to_numpy()
def shift(x,n=1):return pd.Series(x).shift(n).to_numpy()
def div(a,b):return np.divide(a,b,out=np.full(len(a),np.nan),where=np.isfinite(b)&(b!=0))
def ew(x,n):return pd.Series(x).ewm(alpha=1/n,adjust=False,min_periods=n).mean().to_numpy()
def pulse(x):return x & ~np.r_[False,x[:-1]]
def divergence(l,x,atr,look,right):
    piv=I.pivot_low(l,2,right);out=np.zeros(len(l),bool);prev=None
    for i in np.flatnonzero(piv):
        k=i-right
        if prev is not None and 5<=k-prev<=look:
            out[i]=l[k]<=l[prev]-.25*atr[k] and np.isfinite(x[k]) and np.isfinite(x[prev]) and x[k]>x[prev]
        prev=k
    return out

def supertrend(h,l,c,n,k):
    a=I.wilder_atr(h,l,c,n);u=(h+l)/2+k*a;d=(h+l)/2-k*a;direction=np.zeros(len(c),int);prev=None
    for i in range(n-1,len(c)):
        if prev is None:direction[i]=-1;prev=i;continue
        u[i]=u[i] if u[i]<u[i-1] or c[i-1]>u[i-1] else u[i-1]
        d[i]=d[i] if d[i]>d[i-1] or c[i-1]<d[i-1] else d[i-1]
        direction[i]=1 if (direction[i-1]==-1 and c[i]>u[i]) else (-1 if direction[i-1]==1 and c[i]<d[i] else direction[i-1])
    return (direction==1)&(shift(direction)==-1)

def build(d,grid=None):
    g=catalogue() if grid is None else grid;o,h,l,c,v,tbv=[np.asarray(d[k],float) for k in ['o','h','l','c','v','tbv']]
    tp=(h+l+c)/3;atr=I.wilder_atr(h,l,c,14);ratio=div(tbv,v);cache={};out={}
    def get(key,fn):
        if key not in cache:cache[key]=fn()
        return cache[key]
    def rs(n):return get(('rsi',n),lambda:I.rsi(c,n))
    def em(n):return get(('ema',n),lambda:I.ema(c,n))
    def mac(f,s,z):return get(('mac',f,s,z),lambda:I.macd(c,f,s,z))
    for q in g:
        f=q['family'];n=q.get('n');t=q.get('t')
        if f in ['RSI','MFI','TAKER']:
            x=rs(n) if f=='RSI' else get(('mfi',n),lambda:I.mfi(h,l,c,v,n)) if f=='MFI' else ratio
            a=I.cross_up_through(x,t) if q['form']=='cross' else (x<t if f!='TAKER' else x>t)
        elif f=='STOCH':
            x,y=get(('stoch',n,q['d']),lambda:I.stochastic(h,l,c,n,q['d']));a=I.cross_above(x,y)&(x<t)&(y<t)
        elif f=='STOCHRSI':
            x=rs(n);z=div(x-roll(x,n,'min'),roll(x,n,'max')-roll(x,n,'min'));a=I.cross_up_through(z,t)
        elif f=='WR':a=I.cross_up_through(get(('wr',n),lambda:I.williams_r(h,l,c,n)),t)
        elif f=='CCI':a=I.cross_up_through(get(('cci',n),lambda:I.cci(h,l,c,n)),t)
        elif f.startswith('DIV_'):
            if f=='DIV_RSI':x=rs(14)
            elif f=='DIV_MACD':x,y=mac(12,26,9);x=x-y
            elif f=='DIV_OBV':x=get('obv',lambda:np.cumsum(np.nan_to_num(np.sign(c-shift(c)))*v))
            else:x=ratio
            a=divergence(l,x,atr,q['look'],q['right'])
        elif f in ['VOLZ','TAKERZ']:
            x=v if f=='VOLZ' else ratio;y=shift(x);mu=roll(y,n,'mean');sd=pd.Series(y).rolling(n,min_periods=n).std(ddof=0).to_numpy();z=div(x-mu,sd);a=z>=t
            if f=='VOLZ':a &= c>=l+q['upper']*(h-l)
        elif f=='FORCE':a=I.cross_up_through(I.ema((c-shift(c))*v,n),0)
        elif f=='CMF':
            flow=np.nan_to_num(div(2*c-h-l,h-l))*v;x=div(roll(flow,n,'sum'),roll(v,n,'sum'));a=I.cross_up_through(x,t)
        elif f in ['SWEEP','DONCHIAN_FAIL']:
            bottom=roll(shift(l),n,'min');a=(l<bottom-q.get('depth',0)*atr)&(c>bottom)
        elif f=='FVG':a=(l-shift(h,2)>q['gap']*atr)
        elif f=='BOS':
            lower=l<roll(shift(l),q['look'],'min');recent=roll(shift(lower.astype(float)),q['look'],'max')>0
            a=(c>roll(shift(h),n,'max'))&recent
        elif f in ['HAMMER','ENGULF']:
            bottom=l<=roll(l,q['bottom'],'min')
            if f=='ENGULF':a=I.bullish_engulfing(o,c)&bottom
            else:
                body=abs(c-o);a=(body>0)&(np.minimum(c,o)-l>=q['lower']*body)&(h-np.maximum(c,o)<=q['upper']*body)&(c>=(h+l)/2)&bottom
        elif f=='EMA':a=I.cross_above(em(q['fast']),em(q['slow']))
        elif f=='MACD':x,y=mac(q['fast'],q['slow'],q['signal']);a=I.cross_above(x,y)
        elif f=='SUPERTREND':a=supertrend(h,l,c,n,q['k'])
        elif f=='DMI':
            up=h-shift(h);dn=shift(l)-l;plus=np.where((up>dn)&(up>0),up,0);minus=np.where((dn>up)&(dn>0),dn,0)
            an=I.wilder_atr(h,l,c,n);p=100*div(ew(plus,n),an);m=100*div(ew(minus,n),an);adx=ew(100*div(abs(p-m),p+m),n)
            a=I.cross_above(p,m)&(adx>=t)&(adx>shift(adx))
        elif f=='AROON':x,y=get(('aroon',n),lambda:I.aroon(h,l,n));a=I.cross_above(x,y)
        elif f=='VORTEX':
            tr=np.maximum.reduce([h-l,abs(h-shift(c)),abs(l-shift(c))]);den=roll(tr,n,'sum');x=div(roll(abs(h-shift(l)),n,'sum'),den);y=div(roll(abs(l-shift(h)),n,'sum'),den);a=I.cross_above(x,y)
        elif f=='BB':x,_,_=get(('bb',n,q['k']),lambda:I.bollinger(c,n,q['k']));a=(l<=x)&(c>x)
        elif f=='KELTNER':x=em(n)-q['k']*I.wilder_atr(h,l,c,n);a=(l<=x)&(c>x)
        elif f=='VWAP':
            mean=div(roll(tp*v,n,'sum'),roll(v,n,'sum'));second=div(roll(tp*tp*v,n,'sum'),roll(v,n,'sum'));sd=np.sqrt(np.maximum(0,second-mean*mean));x=mean-q['k']*sd;a=(l<=x)&(c>x)
        elif f=='PXEMA':a=I.cross_above(c,em(n))
        elif f=='DONCHIAN_BREAK':a=c>roll(shift(h),n,'max')
        else:raise ValueError(f)
        out[q['id']]=np.asarray(a,bool)
    return out
