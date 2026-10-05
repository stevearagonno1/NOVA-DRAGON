"""Corrected, fixed-parameter L0084-R1 execution engine.

Every eligible trade evaluates bars i+1 through i+18 inclusive (fill bar
included). Decision at close i, fill at open i+1, ATR sampled at i.
"""
from __future__ import annotations
import numpy as np

NOTIONAL=20.0
COST_RT=0.052
BARRIER_ATR=1.5
HORIZON=18
BOOK0=1000.0
OUTCOME_TARGET='target'
OUTCOME_STOP='stop'
OUTCOME_TIMEOUT='timeout'


def _record(symbol,candidate,i,f,j,q,x,a,outcome,gap,double,seg,o,h,l):
    qty=NOTIONAL/q
    gross=qty*(x-q)
    cost_atr=0.0026*q/a
    return {
      'candidate_id':candidate,'symbol':symbol,'signal_bar':int(i),
      'fill_bar':int(f),'exit_bar':int(j),'entry':float(q),'exit':float(x),
      'atr':float(a),'quantity':float(qty),'notional':NOTIONAL,
      'outcome':outcome,'gap_flag':bool(gap),'double_touch':bool(double),
      'holding_bars':int(j-f+1),'gross_dollars':float(gross),
      'cost_dollars':COST_RT,'net_dollars':float(gross-COST_RT),
      'gross_atr_r':float((x-q)/a),'cost_atr':float(cost_atr),
      'net_atr_r':float((x-q)/a-cost_atr),
      'barrier_r':float(((x-q)/a-cost_atr)/BARRIER_ATR),
      'mae_atr_r':float((np.min(l[f:j+1])-q)/a),
      'mfe_atr_r':float((np.max(h[f:j+1])-q)/a),'seg':int(seg),
    }


def _validate_arrays(o,h,l,c,atr,seg):
    n=len(c)
    if any(len(x)!=n for x in (o,h,l,atr,seg)):
        raise ValueError('OHLC/ATR/segment array lengths differ')
    return n


def _one(o,h,l,c,atr,seg,i,symbol,candidate):
    n=len(c);f=i+1;last=i+HORIZON
    # Validate all bars before indexing any of the horizon arrays.
    if i<0 or f>=n or last>=n:
        return None,'incomplete'
    if np.any(seg[f:last+1]!=seg[i]):
        return None,'incomplete'
    a=float(atr[i]);q=float(o[f])
    if not np.isfinite(a) or a<=0 or not np.isfinite(q) or q<=0:
        return None,'rejected'
    stop=q-BARRIER_ATR*a;target=q+BARRIER_ATR*a
    if not np.isfinite(stop) or stop<=0:
        return None,'rejected'
    # Scan from the fill bar, through the eighteenth complete bar.
    for j in range(f,last+1):
        op=float(o[j]);hi=float(h[j]);lo=float(l[j])
        if op<=stop:
            return _record(symbol,candidate,i,f,j,q,op,a,OUTCOME_STOP,True,False,seg[i],o,h,l),None
        if op>=target:
            return _record(symbol,candidate,i,f,j,q,target,a,OUTCOME_TARGET,True,False,seg[i],o,h,l),None
        hit_stop=lo<=stop
        hit_target=hi>=target
        if hit_stop and hit_target:
            return _record(symbol,candidate,i,f,j,q,stop,a,OUTCOME_STOP,False,True,seg[i],o,h,l),None
        if hit_stop:
            return _record(symbol,candidate,i,f,j,q,stop,a,OUTCOME_STOP,False,False,seg[i],o,h,l),None
        if hit_target:
            return _record(symbol,candidate,i,f,j,q,target,a,OUTCOME_TARGET,False,False,seg[i],o,h,l),None
    return _record(symbol,candidate,i,f,last,q,float(c[last]),a,OUTCOME_TIMEOUT,False,False,seg[i],o,h,l),None


def simulate(o,h,l,c,atr,seg_id,mask,symbol,cand):
    n=_validate_arrays(o,h,l,c,atr,seg_id)
    if mask is not None and len(mask)!=n: raise ValueError('mask length mismatch')
    accept=np.ones(n,dtype=bool) if mask is None else np.asarray(mask,dtype=bool)
    trades=[];signals=rejected=incomplete=skipped=0;busy_until=-1;cash=BOOK0
    for i0 in np.flatnonzero(accept[:max(0,n-1)]):
        i=int(i0)
        if i<busy_until:
            if mask is not None: skipped+=1
            continue
        signals+=1
        rec,why=_one(o,h,l,c,atr,seg_id,i,symbol,cand)
        if why=='incomplete': incomplete+=1;continue
        if why=='rejected': rejected+=1;continue
        if cash < NOTIONAL+COST_RT:
            rejected+=1;continue
        trades.append(rec);cash+=rec['net_dollars'];busy_until=rec['exit_bar']
    return trades,{'signals':signals,'executed':len(trades),'rejected':rejected,
                   'incomplete':incomplete,'skipped_occupied':skipped}


def simulate_window(o,h,l,c,atr,seg_id,mask,symbol,cand,first,last,
                    embargo=HORIZON):
    """Fresh $1,000 book for one evaluation window; no pre-window trade or
    cash state can affect decisions. Only signals with a full horizon inside
    the window and after the fixed left embargo are eligible."""
    n=_validate_arrays(o,h,l,c,atr,seg_id)
    first=int(first);last=int(last)
    if first<0 or last>=n or last<first: raise ValueError('invalid window bounds')
    if mask is None:
        allowed=np.ones(n,dtype=bool)
    else:
        if len(mask)!=n:raise ValueError('mask length mismatch')
        allowed=np.asarray(mask,dtype=bool).copy()
    left=first+int(embargo)
    right=last-HORIZON
    if left>right:
        allowed[:]=False
    else:
        allowed[:left]=False
        allowed[right+1:]=False
    return simulate(o,h,l,c,atr,seg_id,allowed,symbol,cand)


def execute_many(o,h,l,c,atr,seg_id,starts,symbol,cand):
    """Independent per-start path used by controls; no IndexError on bad starts."""
    n=_validate_arrays(o,h,l,c,atr,seg_id)
    starts=np.asarray(starts,dtype=np.int64).reshape(-1)
    records=[];bad=np.ones(len(starts),dtype=bool)
    for r,i0 in enumerate(starts):
        i=int(i0)
        f=i+1;last=i+HORIZON
        # Bounds and segment checks precede all OHLC indexing.
        if i<0 or f>=n or last>=n: continue
        if np.any(seg_id[f:last+1]!=seg_id[i]): continue
        a=float(atr[i]);q=float(o[f])
        if not np.isfinite(a) or a<=0 or not np.isfinite(q) or q<=0: continue
        stop=q-BARRIER_ATR*a;target=q+BARRIER_ATR*a
        if not np.isfinite(stop) or stop<=0: continue
        result=None
        # Separate literal loop from simulate() so parity is checked against
        # the independent test reference rather than shared exit branching.
        for j in range(f,last+1):
            op=float(o[j]);hi=float(h[j]);lo=float(l[j])
            if op<=stop:
                result=_record(symbol,cand,i,f,j,q,op,a,OUTCOME_STOP,True,False,seg_id[i],o,h,l);break
            if op>=target:
                result=_record(symbol,cand,i,f,j,q,target,a,OUTCOME_TARGET,True,False,seg_id[i],o,h,l);break
            stop_touch=lo<=stop;target_touch=hi>=target
            if stop_touch and target_touch:
                result=_record(symbol,cand,i,f,j,q,stop,a,OUTCOME_STOP,False,True,seg_id[i],o,h,l);break
            if stop_touch:
                result=_record(symbol,cand,i,f,j,q,stop,a,OUTCOME_STOP,False,False,seg_id[i],o,h,l);break
            if target_touch:
                result=_record(symbol,cand,i,f,j,q,target,a,OUTCOME_TARGET,False,False,seg_id[i],o,h,l);break
        if result is None:
            result=_record(symbol,cand,i,f,last,q,float(c[last]),a,OUTCOME_TIMEOUT,False,False,seg_id[i],o,h,l)
        records.append(result);bad[r]=False
    return records,bad


def combine(masks,mode,seg_id):
    arrays=list(masks.values())
    if not arrays: raise ValueError('empty masks')
    now=np.logical_or.reduce(arrays)
    if mode=='OR0': return now
    if mode=='AND0': return np.logical_and.reduce(arrays)
    if mode=='AND2':
        n=len(arrays[0]);contig=np.zeros(n,dtype=bool)
        if n>=3:contig[2:]=(seg_id[2:]==seg_id[:-2])
        ever=np.logical_and.reduce([np.convolve(a.astype(np.int8),np.ones(3,dtype=np.int8),'full')[:n]>=1 for a in arrays])
        return ever & now & contig
    raise ValueError(mode)


def window_trades(trades,win_first_bar,win_last_bar,embargo=HORIZON):
    return [t for t in trades if t['signal_bar']>=win_first_bar+embargo
            and t['signal_bar']>=win_first_bar
            and t['signal_bar']+HORIZON<=win_last_bar]
