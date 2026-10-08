"""Prepared pure indicator functions; no original bot/network imports."""
def aggregate(raw,m):
    out=[]
    for start in range(0,len(raw),m):
        ix=raw[start:start+m]
        if len(ix)!=m:continue
        assert ix[0][0]%(m*60)==0
        out.append([ix[0][0],ix[0][1],max(x[2] for x in ix),min(x[3] for x in ix),ix[-1][4],sum(x[5] for x in ix)])
    return out
def ema(c,n):
    out=[];v=c[0]
    for x in c:v+=2/(n+1)*(x-v);out.append(v)
    return out
def ema_sma_seed(c,n):
    out=[None]*len(c)
    if len(c)<n:return out
    out[n-1]=sum(c[:n])/n
    for i in range(n,len(c)):out[i]=2/(n+1)*c[i]+(1-2/(n+1))*out[i-1]
    return out
def atr(b,n=14):
    tr=[b[0][2]-b[0][3]]+[max(x[2]-x[3],abs(x[2]-b[i-1][4]),abs(x[3]-b[i-1][4])) for i,x in enumerate(b[1:],1)]
    out=[None]*len(b)
    if len(b)<n:return out
    out[n-1]=sum(tr[:n])/n
    for i in range(n,len(b)):out[i]=(out[i-1]*(n-1)+tr[i])/n
    return out
def rsi(c,n=14,flat_value=50):
    out=[None]*len(c)
    if len(c)<=n:return out
    g=sum(max(c[i]-c[i-1],0) for i in range(1,n+1))/n;l=sum(max(c[i-1]-c[i],0) for i in range(1,n+1))/n
    def val():return flat_value if g==l==0 else 100 if l==0 else 100-100/(1+g/l)
    out[n]=val()
    for i in range(n+1,len(c)):
        d=c[i]-c[i-1];g=(g*(n-1)+max(d,0))/n;l=(l*(n-1)+max(-d,0))/n;out[i]=val()
    return out
