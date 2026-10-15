"""Fixed independent alert conditions and horizon-free descriptive price outcomes."""
from array import array
import math

RULES = [
 ('EMA_PRICE_RECLAIM','directional',4,0,'gt'),
 ('EMA_SLOPE5_TURN','directional',5,0,'gt'),
 ('MACD_SIGNAL_CROSS','directional',8,0,'gt'),
 ('MACD_ZERO_CROSS','directional',6,0,'gt'),
 ('MACD_HIST5_TURN','directional',9,0,'gt'),
 ('RSI_30_RECLAIM','directional',10,30,'ge'),
 ('RSI_50_RECLAIM','directional',10,50,'ge'),
 ('RSI_CHANGE5_TURN','directional',11,0,'gt'),
 ('ATR_CHANGE5_TURN','activity_only',2,0,'gt'),
 ('VOLUME_MEAN_RECLAIM','activity_only',13,1,'gt'),
]

def triggers(previous,current):
    found=[]
    for name,kind,k,level,op in RULES:
        a,b=previous[k],current[k]
        if not (math.isfinite(a) and math.isfinite(b)):continue
        if (a<=level<b if op=='gt' else a<level<=b):found.append((name,kind))
    return found

def outcomes(prices):
    """Each label uses future only for evaluation, never for alert generation."""
    n=len(prices);above=array('i',[-1])*n;different=array('i',[-1])*n
    prior=array('b',[0])*n;stack=[]
    for i,p in enumerate(prices):
        while stack and p>prices[stack[-1]]:above[stack.pop()]=i
        stack.append(i)
        if i:
            prior[i]=(1 if p>prices[i-1] else -1) if p!=prices[i-1] else prior[i-1]
    for i in range(n-2,-1,-1):
        different[i]=i+1 if prices[i+1]!=prices[i] else different[i+1]
    return above,different,prior

def describe(prices,labels,index):
    above,different,prior=labels;j=different[index];u=above[index]
    direction=0 if j<0 else (1 if prices[j]>prices[index] else -1)
    return {'next_direction':direction,'next_change_index':j,'first_above_index':u,
            'prior_direction':prior[index],'wait_minutes':None if u<0 else u-index,
            'observed_minutes':len(prices)-1-index}

def empty():
    return dict(n=0,next_up=0,next_down=0,next_unobserved=0,above_seen=0,above_not_seen=0,
                down_then_up_turn=0,already_up_then_up=0,wait_sum=0,wait_max=0,
                observed_minutes_sum=0)

def add(stat,d):
    stat['n']+=1;stat['next_up' if d['next_direction']==1 else 'next_down' if d['next_direction']==-1 else 'next_unobserved']+=1
    stat['above_seen' if d['first_above_index']>=0 else 'above_not_seen']+=1
    stat['down_then_up_turn']+=d['prior_direction']==-1 and d['next_direction']==1
    stat['already_up_then_up']+=d['prior_direction']==1 and d['next_direction']==1
    if d['wait_minutes'] is not None:
        stat['wait_sum']+=d['wait_minutes'];stat['wait_max']=max(stat['wait_max'],d['wait_minutes'])
    stat['observed_minutes_sum']+=d['observed_minutes']

def self_test():
    import random
    cases=[[100],[100,100,100],[100,101,100,102],[100,99,98],[100,99,100,100,101]]
    rng=random.Random(20261015)
    for _ in range(40):
        p=[100]
        for k in range(39):p.append(p[-1]+rng.choice([-2,-1,0,0,1,2]))
        cases.append(p)
    checks=0
    for p in cases:
        a,d,pr=outcomes(p)
        for i in range(len(p)):
            assert a[i]==next((j for j in range(i+1,len(p)) if p[j]>p[i]),-1)
            assert d[i]==next((j for j in range(i+1,len(p)) if p[j]!=p[i]),-1)
            old=next((j for j in range(i-1,-1,-1) if p[j]!=p[i]),-1)
            assert pr[i]==(0 if old<0 else 1 if p[i]>p[old] else -1)
            checks+=3
    for name,kind,k,level,op in RULES:
        p=[float('nan')]*14;c=p.copy();p[k]=level-1;c[k]=level+1
        assert triggers(p,c)==[(name,kind)]
        c[k]=float('nan');assert not triggers(p,c)
        checks+=2
    return {'status':'PASS','brute_force_label_checks':checks,'label_cases':len(cases),'rule_count':len(RULES)}
