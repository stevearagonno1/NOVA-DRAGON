"""Remote partition reconciliation and independent execution rebuild helpers."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

try:
    from .streaming import BASE, TRADE_SCHEMA, _row as trade_row
    from .metrics import METRIC_SCHEMA, CONTROL_SCHEMA
    from .transport import GitHubTransport, TransportError
    from . import engine as E
    from . import measure as M
    from . import indicators as I
except ImportError:
    from streaming import BASE, TRADE_SCHEMA, _row as trade_row
    from metrics import METRIC_SCHEMA, CONTROL_SCHEMA
    from transport import GitHubTransport, TransportError
    import engine as E
    import measure as M
    import indicators as I


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _run_receipts(client,head,run_id):
    raw=client.blob_from_commit(head,f"{BASE}/storage_journal.jsonl")
    pointers=[json.loads(x) for x in raw.decode().splitlines() if x]
    pointers=[x for x in pointers if x.get("run_id")==run_id]
    if not pointers:raise TransportError("no storage journal shards for run")
    receipts=[]
    for pointer in pointers:
        shard=client.blob_from_commit(head,pointer["path"])
        if len(shard)!=int(pointer["bytes"]) or hashlib.sha256(shard).hexdigest()!=pointer["sha256"]:
            raise TransportError("storage journal shard hash/size mismatch: "+pointer["path"])
        if _git_blob_sha(shard)!=pointer["git_blob_sha"]:raise TransportError("storage journal shard Git SHA mismatch")
        for line in shard.decode().splitlines():
            rec=json.loads(line)
            if rec.get("event")=="trade_partition_committed":receipts.append(rec)
    return pointers,receipts


def _run_index(client,head,run_id):
    directory=f"{BASE}/measurement_index/run={run_id}"
    names=client.list_directory(head,directory)
    rows=[]
    for name in sorted(names):
        if name.endswith('.jsonl'):
            path=directory+'/'+name
            raw=client.blob_from_commit(head,path)
            for line in raw.decode().splitlines():rows.append(json.loads(line))
    return rows


def verify_remote_partitions(client: GitHubTransport, head: str, run_id: str) -> dict:
    """Re-read every run partition at a fixed head and reconcile all indices."""
    pointers,receipts=_run_receipts(client,head,run_id)
    paths={};trade_rows=0
    for rec in receipts:
        path=rec["path"]
        if path in paths:raise TransportError("duplicate partition receipt: "+path)
        paths[path]=rec
        current=client.blob_from_commit(head,path)
        committed=client.blob_from_commit(rec["commit_sha"],path)
        for data in (current,committed):
            if len(data)!=int(rec["bytes"]) or hashlib.sha256(data).hexdigest()!=rec["sha256"]:
                raise TransportError("partition content hash/size mismatch: "+path)
            if _git_blob_sha(data)!=rec["git_blob_sha"]:raise TransportError("partition Git blob SHA mismatch")
        table=pq.read_table(pa.BufferReader(current))
        if not table.schema.equals(TRADE_SCHEMA,check_metadata=False):raise TransportError("partition schema mismatch: "+path)
        if table.num_rows!=int(rec["rows"]):raise TransportError("partition row count mismatch: "+path)
        for field,value in (("candidate_id",rec["candidate_id"]),("role",rec["role"]),("window",rec["window"])):
            if any(x!=value for x in table[field].to_pylist()):raise TransportError(f"partition label mismatch {field}: {path}")
        if any(x<=0 for x in table["entry"].to_pylist()):raise TransportError("nonpositive entry in raw partition")
        if any(abs(x-20.0)>1e-12 for x in table["notional"].to_pylist()):raise TransportError("notional mismatch")
        if any(abs(x-0.052)>1e-12 for x in table["cost_dollars"].to_pylist()):raise TransportError("cost mismatch")
        if any(abs(n-(g-c))>1e-9 for n,g,c in zip(table["net_dollars"].to_pylist(),table["gross_dollars"].to_pylist(),table["cost_dollars"].to_pylist())):
            raise TransportError("gross-cost-net arithmetic mismatch")
        if any(h!=x-f+1 for h,x,f in zip(table["holding_bars"].to_pylist(),table["exit_bar"].to_pylist(),table["fill_bar"].to_pylist())):
            raise TransportError("inclusive holding-bar mismatch")
        trade_rows+=table.num_rows
    coverage=_run_index(client,head,run_id);coverage_map={};indexed=set()
    for row in coverage:
        key=(row["candidate_id"],row["role"],row["window"])
        if key in coverage_map:raise TransportError("duplicate candidate-window index: "+str(key))
        coverage_map[key]=row
        for path in row.get("partition_paths",[]):
            if path in indexed:raise TransportError("duplicate partition in coverage index: "+path)
            indexed.add(path)
    if indexed!=set(paths):
        raise TransportError(f"ledger/index partition mismatch; missing={sorted(indexed-set(paths))[:3]} extra={sorted(set(paths)-indexed)[:3]}")
    for key,row in coverage_map.items():
        found=[r for r in receipts if (r["candidate_id"],r["role"],r["window"])==key]
        if sum(int(x["rows"]) for x in found)!=int(row["trade_rows"]):raise TransportError("index row count differs from raw partitions: "+str(key))
        if len(found)!=int(row["partition_count"]):raise TransportError("index partition count differs from receipts: "+str(key))
        if set(row.get("partition_paths",[]))!={x["path"] for x in found}:raise TransportError("index paths disagree with receipts: "+str(key))
    return {"head":head,"run_id":run_id,"partitions":len(paths),"trade_rows":trade_rows,
            "coverage_rows":len(coverage),"zero_trade_candidate_windows":sum(int(x["trade_rows"])==0 for x in coverage),
            "storage_journal_shards":len(pointers),"sha_size_schema_reconciliation":"PASS"}


def independent_trade(o,h,l,c,atr,seg,i,symbol,candidate):
    """Reference one execution using a literal loop and no engine exit helper."""
    n=len(c);f=i+1;last=i+18
    if i<0 or f>=n or last>=n or np.any(seg[f:last+1]!=seg[i]):return None,"incomplete"
    q=float(o[f]);a=float(atr[i])
    if not np.isfinite(a) or a<=0 or not np.isfinite(q) or q<=0:return None,"rejected"
    stop=q-1.5*a;target=q+1.5*a
    if not np.isfinite(stop) or stop<=0:return None,"rejected"
    exit_bar=None;exit_price=None;outcome=None;gap=False;double=False
    for j in range(f,last+1):
        op=float(o[j]);hi=float(h[j]);lo=float(l[j])
        if op<=stop:exit_bar=j;exit_price=op;outcome="stop";gap=True;break
        if op>=target:exit_bar=j;exit_price=target;outcome="target";gap=True;break
        stop_hit=lo<=stop;target_hit=hi>=target
        if stop_hit and target_hit:exit_bar=j;exit_price=stop;outcome="stop";double=True;break
        if stop_hit:exit_bar=j;exit_price=stop;outcome="stop";break
        if target_hit:exit_bar=j;exit_price=target;outcome="target";break
    if exit_bar is None:exit_bar=last;exit_price=float(c[last]);outcome="timeout"
    qty=20.0/q;gross=qty*(exit_price-q);cost=0.052;cost_atr=0.0026*q/a
    return {"candidate_id":candidate,"symbol":symbol,"signal_bar":int(i),"fill_bar":f,
        "exit_bar":exit_bar,"entry":q,"exit":exit_price,"atr":a,"quantity":qty,
        "notional":20.0,"outcome":outcome,"gap_flag":gap,"double_touch":double,
        "holding_bars":exit_bar-f+1,"gross_dollars":gross,"cost_dollars":cost,
        "net_dollars":gross-cost,"gross_atr_r":(exit_price-q)/a,
        "cost_atr":cost_atr,"net_atr_r":(exit_price-q)/a-cost_atr,
        "barrier_r":((exit_price-q)/a-cost_atr)/1.5,
        "mae_atr_r":(float(np.min(l[f:exit_bar+1]))-q)/a,
        "mfe_atr_r":(float(np.max(h[f:exit_bar+1]))-q)/a,
        "seg":int(seg[i])},None


def independent_simulate_window(o,h,l,c,atr,seg,mask,symbol,candidate,first,last,embargo=18):
    """Independent per-window portfolio loop, including cash and re-entry."""
    n=len(c);left=int(first)+embargo;right=int(last)-18
    if left>right:return []
    accepted=np.ones(n,dtype=bool) if mask is None else np.asarray(mask,dtype=bool)
    if len(accepted)!=n:raise ValueError("mask length mismatch")
    cash=1000.0;busy=-1;rows=[]
    for i in range(left,right+1):
        if not accepted[i] or i<busy:continue
        trade,why=independent_trade(o,h,l,c,atr,seg,i,symbol,candidate)
        if why is not None:continue
        if cash<20.052:continue
        rows.append(trade);cash+=trade["net_dollars"];busy=trade["exit_bar"]
    return rows


def _read_csv(client,head,name,base=BASE):
    raw=client.blob_from_commit(head,f"{base}/{name}").decode("utf-8")
    return list(csv.DictReader(io.StringIO(raw)))


def _resolve_candidate(cid,prefix,role,pair_map,triple_map,selected,neighbor_map):
    if role=="baseline":return None,None
    if role=="single":return (cid,),"AND0"
    if role=="pair":
        pid,mode=cid.split("|",1);return pair_map[pid],mode
    if role=="triple":
        pfx,tid=cid.split(":",1);row=triple_map[(pfx,tid)]
        return (row["member_a"],row["member_b"],row["member_c"]),row["mode"]
    if role=="outer":
        pfx,base=cid.split(":",1)
        lookup=f"{pfx}:{base}" if base.startswith("T") else base
        return _resolve_candidate(lookup,pfx,_role_for_id(base),pair_map,triple_map,selected,neighbor_map)
    if role=="neighbour":
        row=neighbor_map[cid];base=row["base_candidate"];pfx=row["prefix_id"]
        lookup=f"{pfx}:{base}" if base.startswith("T") else base
        members,mode=_resolve_candidate(lookup,pfx,_role_for_id(base),pair_map,triple_map,selected,neighbor_map)
        return tuple(row["neighbour_setting"] if x==row["member"] else x for x in members),mode
    raise TransportError("unknown trade-ledger role: "+role)


def _role_for_id(cid):
    if cid.startswith("P"):return "pair"
    if cid.startswith("T"):return "triple"
    return "single"


def _combine_independent(masks,mode,seg):
    arr=list(masks)
    if mode=="AND0":return np.logical_and.reduce(arr)
    if mode=="OR0":return np.logical_or.reduce(arr)
    if mode!="AND2":raise ValueError(mode)
    n=len(seg);out=np.zeros(n,bool)
    for i in range(n):
        if i<2 or seg[i]!=seg[i-1] or seg[i]!=seg[i-2]:continue
        if not any(a[i] for a in arr):continue
        if all(bool(a[i] or a[i-1] or a[i-2]) for a in arr):out[i]=True
    return out


def _random_reference(p,window,count,candidate,replicate):
    lo,hi=p.ranges[window];first=lo+18;last=hi-18
    if last<first or count<=0:return []
    seed=M.sha_seed(f"84|{p.sym}|{window}|{candidate}|{replicate}")
    rng=np.random.default_rng(seed);pool=list(range(first,last+1));cash=1000.0;earliest=first;out=[]
    while len(out)<count:
        choices=[i for i in pool if i>=earliest]
        if not choices:break
        i=int(rng.choice(choices));pool.remove(i)
        trade,why=independent_trade(p.o,p.h,p.l,p.c,p.atr,p.seg,i,p.sym,candidate)
        if why is not None:continue
        if cash<20.052:break
        out.append(trade);cash+=trade["net_dollars"];earliest=trade["exit_bar"]
    return out


def _actual_rows(client,head,paths):
    rows=[]
    for path in paths:
        tab=pq.read_table(pa.BufferReader(client.blob_from_commit(head,path)))
        rows.extend(tab.to_pylist())
    return rows


def _independent_paired_difference(base_rows,control_rows,window,panel):
    """Independent synchronized block bootstrap for one matched asset pair."""
    if not base_rows or not control_rows or len(base_rows)!=len(control_rows):return None
    first,last=M.WIN_RANGE[window];n_days=int((np.datetime64(last)-np.datetime64(first)).astype(int))+1
    sums=[np.zeros(n_days),np.zeros(n_days)];counts=[np.zeros(n_days),np.zeros(n_days)]
    for side,rows in enumerate((base_rows,control_rows)):
        for r in rows:
            day=np.datetime64(pd.Timestamp(panel.dt[int(r["fill_bar"])]).date())
            idx=int((day-np.datetime64(first)).astype(int))
            if idx<0 or idx>=n_days:raise TransportError("paired trade day outside requested window")
            sums[side][idx]+=float(r["net_dollars"]);counts[side][idx]+=1
    rng=np.random.default_rng(84);reps=2000;block=7
    if n_days<=block:chosen=rng.integers(0,n_days,size=(reps,n_days))
    else:
        blocks=int(np.ceil(n_days/block));starts=rng.integers(0,n_days-block+1,size=(reps,blocks))
        chosen=(starts[:,:,None]+np.arange(block)[None,None,:]).reshape(reps,-1)[:,:n_days]
    c0=counts[0][chosen].sum(axis=1);c1=counts[1][chosen].sum(axis=1)
    with np.errstate(invalid="ignore",divide="ignore"):
        vals=sums[0][chosen].sum(axis=1)/c0-sums[1][chosen].sum(axis=1)/c1
    vals=vals[np.isfinite(vals)]
    if not len(vals):return None
    observed=float(sums[0].sum()/counts[0].sum()-sums[1].sum()/counts[1].sum())
    return {"diff":observed,"lo5":float(np.percentile(vals,5)),"hi95":float(np.percentile(vals,95))}


def _independent_asset_stats(rows,window,panel):
    if window not in M.WIN_RANGE:return None
    first,last=M.WIN_RANGE[window];n_days=int((np.datetime64(last)-np.datetime64(first)).astype(int))+1
    base_expected=independent_simulate_window(panel.o,panel.h,panel.l,panel.c,panel.atr,panel.seg,None,panel.sym,"NO-SIGNAL",*panel.ranges[window])
    bw=sum(x["outcome"]=="target" for x in base_expected);bd=sum(x["outcome"] in ("target","stop") for x in base_expected)
    baseline=bw/bd if bd else None
    if not rows:return {"baseline_win_rate":baseline,"breakeven_rate":None,"lift_win_points":None,"p_raw":None,"ci_lo":None,"ci_hi":None}
    s=np.zeros(n_days);c=np.zeros(n_days);nets=np.asarray([float(r["net_dollars"]) for r in rows]);wins=sum(r["outcome"]=="target" for r in rows);stops=sum(r["outcome"]=="stop" for r in rows)
    for r in rows:
        day=np.datetime64(pd.Timestamp(panel.dt[int(r["fill_bar"])]).date());idx=int((day-np.datetime64(first)).astype(int))
        if idx<0 or idx>=n_days:raise TransportError("per-asset trade day outside window")
        s[idx]+=float(r["net_dollars"]);c[idx]+=1
    rng=np.random.default_rng(84);reps=2000;block=7
    if n_days<=block:idxs=rng.integers(0,n_days,size=(reps,n_days))
    else:
        nb=int(np.ceil(n_days/block));starts=rng.integers(0,n_days-block+1,size=(reps,nb))
        idxs=(starts[:,:,None]+np.arange(block)[None,None,:]).reshape(reps,-1)[:,:n_days]
    den=c[idxs].sum(axis=1);num=s[idxs].sum(axis=1);vals=np.divide(num,den,out=np.full(reps,np.nan),where=den>0);vals=vals[np.isfinite(vals)]
    lo=float(np.percentile(vals,5));hi=float(np.percentile(vals,95));se=float(np.std(vals,ddof=1));expectancy=float(nets.mean())
    from scipy.stats import norm
    praw=float(norm.sf(expectancy/se)) if se>0 else float("nan")
    winrate=wins/(wins+stops) if wins+stops else None
    mean_cost=float(np.mean([r["cost_atr"] for r in rows]))
    lift=(winrate-baseline)*100 if winrate is not None and baseline is not None else None
    return {"baseline_win_rate":baseline,"breakeven_rate":0.5+mean_cost/3,"lift_win_points":lift,"p_raw":praw,"ci_lo":lo,"ci_hi":hi}


def _independent_block_stats(rows,window,panels):
    """Literal independent synchronized seven-day bootstrap over raw rebuilt trades."""
    if window not in M.WIN_RANGE or not rows:return None
    first,last=M.WIN_RANGE[window]
    n_days=int((np.datetime64(last)-np.datetime64(first)).astype(int))+1
    daily_sum=np.zeros(n_days);daily_count=np.zeros(n_days)
    nets=np.asarray([float(r["net_dollars"]) for r in rows])
    for r in rows:
        p=panels[r["asset"]]
        day=np.datetime64(pd.Timestamp(p.dt[int(r["fill_bar"])]).date())
        idx=int((day-np.datetime64(first)).astype(int))
        if idx<0 or idx>=n_days:raise TransportError("rebuilt trade day outside requested window")
        daily_sum[idx]+=float(r["net_dollars"]);daily_count[idx]+=1
    rng=np.random.default_rng(84)
    reps=2000;block=7
    if n_days<=block:
        chosen=rng.integers(0,n_days,size=(reps,n_days))
    else:
        blocks=int(np.ceil(n_days/block))
        starts=rng.integers(0,n_days-block+1,size=(reps,blocks))
        chosen=(starts[:,:,None]+np.arange(block)[None,None,:]).reshape(reps,-1)[:,:n_days]
    denom=daily_count[chosen].sum(axis=1);numer=daily_sum[chosen].sum(axis=1)
    vals=np.divide(numer,denom,out=np.full(reps,np.nan),where=denom>0)
    vals=vals[np.isfinite(vals)]
    if not len(vals):return None
    expectancy=float(nets.mean());lo=float(np.percentile(vals,5));hi=float(np.percentile(vals,95));se=float(np.std(vals,ddof=1))
    from scipy.stats import norm
    praw=float(norm.sf(expectancy/se)) if se>0 else float("nan")
    wins=sum(r["outcome"]=="target" for r in rows);stops=sum(r["outcome"]=="stop" for r in rows)
    resolved=wins+stops;winrate=wins/resolved if resolved else float("nan")
    base=[]
    for sym,p in panels.items():
        lo_bar,hi_bar=p.ranges[window]
        expected=independent_simulate_window(p.o,p.h,p.l,p.c,p.atr,p.seg,None,sym,"NO-SIGNAL",lo_bar,hi_bar)
        base.extend(expected)
    base_w=sum(x["outcome"]=="target" for x in base);base_d=sum(x["outcome"] in ("target","stop") for x in base)
    base_win=base_w/base_d if base_d else float("nan")
    mean_cost_atr=float(np.mean([float(r["cost_atr"]) for r in rows]))
    lift=(winrate-base_win)*100 if np.isfinite(winrate) and np.isfinite(base_win) else float("nan")
    return {"baseline_win_rate":base_win,"breakeven_rate":0.5+mean_cost_atr/3,
      "lift_win_points":lift,
      "p_raw":praw,"ci_lo":lo,"ci_hi":hi}


def _audit_metric_row(candidate,role,window,asset,scope,trades,panel):
    """Independent descriptive-statistic implementation over rebuilt trades."""
    rows=sorted(trades,key=lambda x:(int(x["fill_bar"]),int(x["signal_bar"])))
    n=len(rows);wins=sum(x["outcome"]=="target" for x in rows);stops=sum(x["outcome"]=="stop" for x in rows)
    timeouts=sum(x["outcome"]=="timeout" for x in rows);resolved=wins+stops
    winrate=wins/resolved if resolved else None
    if resolved:
        z=1.959963984540054;ph=wins/resolved;den=1+z*z/resolved
        center=(ph+z*z/(2*resolved))/den
        half=z*math.sqrt(ph*(1-ph)/resolved+z*z/(4*resolved*resolved))/den
        wlo,whi=center-half,center+half
    else:wlo=whi=None
    net=np.asarray([x["net_dollars"] for x in rows],dtype=float)
    pos=float(net[net>0].sum());neg=-float(net[net<0].sum())
    pfv=(pos/neg if neg else (float("inf") if pos else float("nan"))) if n else None
    def mean(field):return float(np.mean([x[field] for x in rows])) if rows else None
    if rows:
        equity=1000.0;peak=1000.0;mdd=0.0;run_dd=max_dd=0
        daily={};losing=max_losing=0
        for x in rows:
            equity+=float(x["net_dollars"]);peak=max(peak,equity);drawdown=equity-peak
            mdd=min(mdd,drawdown);run_dd=run_dd+1 if drawdown<0 else 0;max_dd=max(max_dd,run_dd)
            losing=losing+1 if float(x["net_dollars"])<0 else 0;max_losing=max(max_losing,losing)
            day=str(pd.Timestamp(panel.dt[int(x["fill_bar"])]).date());daily[day]=daily.get(day,0.0)+float(x["net_dollars"])
        lo,hi=panel.ranges[window];ndays=max(1,(pd.Timestamp(panel.dt[int(hi)]).date()-pd.Timestamp(panel.dt[int(lo)]).date()).days+1)
        active=len(daily);coverage=active/ndays;worst=min(daily.values()) if daily else None
    else:mdd=0.0;max_dd=0;max_losing=0;active=0;coverage=0.0;worst=None
    gp=float(sum(x["gross_dollars"] for x in rows));cost=float(sum(x["cost_dollars"] for x in rows))
    hit=[x for x in rows if x["outcome"] in ("target","stop")]
    return {"candidate_id":str(candidate),"role":str(role),"window":str(window),"asset":str(asset),"scope":str(scope),
      "n_exec":n,"n_win":wins,"n_stop":stops,"n_timeout":timeouts,"n_resolved":resolved,"n_eff":n,
      "n_signals":None,"n_incomplete":None,"win_rate":winrate,"wilson_lo":wlo,"wilson_hi":whi,
      "gross_dollars":gp,"cost_dollars":cost,"net_dollars":float(net.sum()) if n else 0.0,
      "expectancy_dollars":float(net.mean()) if n else None,"profit_factor":pfv,
      "gross_atr_r":mean("gross_atr_r"),"cost_atr":mean("cost_atr"),"net_atr_r":mean("net_atr_r"),
      "barrier_r":mean("barrier_r"),"mae_atr_r":mean("mae_atr_r"),"mfe_atr_r":mean("mfe_atr_r"),
      "mean_holding_bars":mean("holding_bars"),"mean_time_to_hit_bars":float(np.mean([x["holding_bars"] for x in hit])) if hit else None,
      "gap_count":sum(bool(x["gap_flag"]) for x in rows),"double_touch_count":sum(bool(x["double_touch"]) for x in rows),
      "n_active_days":active,"coverage":coverage,"mdd_dollars":mdd,"mdd_pct_book":mdd/1000*100,
      "drawdown_duration_trades":max_dd,"worst_day_dollars":worst,"longest_losing_streak":max_losing,
      "exposure_bars":sum(int(x["holding_bars"]) for x in rows),"baseline_win_rate":None,"breakeven_rate":None,
      "lift_win_points":None,"p_raw":None,"p_adjusted":None,"ci_lo":None,"ci_hi":None,"power80":None,
      "metric_status":"ZERO_TRADES; inference_not_computed" if not n else "RAW_DESCRIPTIVE; inference_not_computed"}


def _metric_rows(client,head,kind,run_id):
    directory=f"{BASE}/{kind}/run={run_id}"
    names=client.list_directory(head,directory)
    count=0;part_meta=[]
    for name in sorted(names):
        if not name.endswith(".parquet"):continue
        path=directory+"/"+name;raw=client.blob_from_commit(head,path)
        if len(raw)>8_000_000:raise TransportError("metric partition exceeds 8,000,000 bytes: "+path)
        table=pq.read_table(pa.BufferReader(raw))
        if not table.schema.equals(METRIC_SCHEMA,check_metadata=False):raise TransportError("metric schema mismatch: "+path)
        rows=table.to_pylist();count+=len(rows)
        part_meta.append({"path":path,"rows":len(rows),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"git_blob_sha":_git_blob_sha(raw)})
        for row in rows:yield row
    _metric_rows.last_meta=(count,part_meta)


def _control_rows(client,head,run_id):
    directory=f"{BASE}/controls/run={run_id}"
    try:names=client.list_directory(head,directory)
    except TransportError as exc:
        if "directory resolution failed" in str(exc):return [],[]
        raise
    out=[];parts=[]
    for name in sorted(names):
        if not name.endswith(".parquet"):continue
        path=directory+"/"+name;raw=client.blob_from_commit(head,path)
        if len(raw)>8_000_000:raise TransportError("control partition exceeds 8,000,000 bytes: "+path)
        tab=pq.read_table(pa.BufferReader(raw))
        if not tab.schema.equals(CONTROL_SCHEMA,check_metadata=False):raise TransportError("control schema mismatch: "+path)
        out.extend(tab.to_pylist());parts.append({"path":path,"rows":tab.num_rows,"sha256":hashlib.sha256(raw).hexdigest()})
    return out,parts


def _halfyear_rows(client,head,run_id):
    directory=f"{BASE}/halfyears.csv/run={run_id}"
    try:names=client.list_directory(head,directory)
    except TransportError as exc:
        if "directory resolution failed" in str(exc):return [],[]
        raise
    rows=[];parts=[]
    for name in sorted(names):
        if not name.endswith(".csv"):continue
        path=directory+"/"+name;raw=client.blob_from_commit(head,path)
        if len(raw)>8_000_000:raise TransportError("half-year partition exceeds byte cap")
        local=list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
        rows.extend(local);parts.append({"path":path,"rows":len(local),"sha256":hashlib.sha256(raw).hexdigest()})
    return rows,parts


def _compare_halfyear_rows(got_rows,want_rows):
    keys=("candidate","asset","halfyear")
    def key(r):return tuple(r[k] for k in keys)
    got={key(r):r for r in got_rows};want={key(r):r for r in want_rows}
    if len(got)!=len(got_rows) or len(want)!=len(want_rows):raise TransportError("duplicate half-year result row")
    if set(got)!=set(want):raise TransportError("half-year table coverage mismatch")
    numeric=("partial","n","net","pf","win","baseline","lift","ci_lo","ci_hi")
    for k,b in want.items():
        a=got[k]
        for field in numeric:
            av=a.get(field);bv=b.get(field)
            if bv is None:
                if av not in (None,""):raise TransportError(f"half-year null mismatch {k} {field}")
            else:
                try:actual=float(av)
                except (TypeError,ValueError):raise TransportError(f"half-year missing numeric {k} {field}")
                if not math.isclose(actual,float(bv),rel_tol=0,abs_tol=1e-9):raise TransportError(f"half-year value mismatch {k} {field}: {actual} vs {bv}")


def _compare_control_rows(got_rows,want_rows):
    key_fields=("candidate","control_type","replicate","asset","window")
    got={tuple(r[k] for k in key_fields):r for r in got_rows}
    want={tuple(r[k] for k in key_fields):r for r in want_rows}
    if len(got)!=len(got_rows) or len(want)!=len(want_rows):raise TransportError("duplicate control result row")
    if set(got)!=set(want):raise TransportError(f"control row coverage mismatch: missing={list(set(want)-set(got))[:2]} extra={list(set(got)-set(want))[:2]}")
    for key,b in want.items():
        a=got[key]
        for field in CONTROL_SCHEMA.names:
            av,bv=a.get(field),b.get(field)
            if av is None or bv is None:
                if av is not None or bv is not None:raise TransportError(f"control null mismatch {key} {field}")
            elif isinstance(bv,float):
                if not math.isclose(float(av),bv,rel_tol=0,abs_tol=1e-9):raise TransportError(f"control value mismatch {key} {field}: {av} vs {bv}")
            elif av!=bv:raise TransportError(f"control value mismatch {key} {field}: {av} vs {bv}")


def _compare_metric(got,want,key):
    for field in METRIC_SCHEMA.names:
        a=got.get(field);b=want.get(field)
        if a is None or b is None:
            if a is not None or b is not None:raise TransportError(f"metric null mismatch {key} {field}: {a} vs {b}")
        elif isinstance(b,float):
            if math.isnan(b):
                if not isinstance(a,float) or not math.isnan(a):raise TransportError(f"metric NaN mismatch {key} {field}")
            elif not math.isclose(float(a),b,rel_tol=0,abs_tol=1e-9):raise TransportError(f"metric value mismatch {key} {field}: {a} vs {b}")
        elif a!=b:raise TransportError(f"metric value mismatch {key} {field}: {a} vs {b}")


def rebuild_all(client: GitHubTransport,head: str,run_id: str,measurer=None,
                metadata_base=BASE) -> dict:
    """Independently regenerate every indexed trade group at one fixed head.

    ``metadata_base`` is normally the immutable R1 registry directory; the
    explicit override lets the exact same auditor use a separately labelled
    synthetic fixture without replacing production registrations.
    """
    base_check=verify_remote_partitions(client,head,run_id)
    coverage=_run_index(client,head,run_id)
    _pointers,receipts=_run_receipts(client,head,run_id)
    pair_rows=_read_csv(client,head,"pairs_registry.csv",metadata_base)
    pair_map={r["pair_id"]:(r["member_a"],r["member_b"]) for r in pair_rows}
    tr_rows=_read_csv(client,head,"triples_registry.csv",metadata_base)
    triple_map={(r["prefix_id"],r["triple_id"]):r for r in tr_rows if r.get("triple_id")}
    sel_rows=_read_csv(client,head,"selection_log.csv",metadata_base)
    selected={r["prefix"]:r["candidate"] for r in sel_rows if r.get("selected")=="1" and r.get("candidate")!="CASH"}
    ng=_read_csv(client,head,"neighbors_registry.csv",metadata_base)
    neighbor_map={r["neighbour_id"]:r for r in ng if r.get("neighbour_id")}
    if measurer is None:measurer=M.Measurer()
    receipts_by_key={}
    for r in receipts:receipts_by_key.setdefault((r["candidate_id"],r["role"],r["window"]),[]).append(r["path"])
    checked_groups=checked_trades=0;violations=[]
    summary_metrics=iter(_metric_rows(client,head,"metrics",run_id))
    asset_metrics=iter(_metric_rows(client,head,"metrics_by_asset",run_id))
    checked_summary_metrics=checked_asset_metrics=checked_inference_metrics=0
    expected_control_rows=[];expected_halfyear_rows=[]
    for entry in coverage:
        cid,role,window=entry["candidate_id"],entry["role"],entry["window"]
        key=(cid,role,window);paths=entry.get("partition_paths",[])
        actual=_actual_rows(client,head,paths)
        if len(actual)!=int(entry["trade_rows"]):raise TransportError("coverage vs decoded ledger row count mismatch: "+str(key))
        prefix=None
        if role in ("triple","outer"):
            prefix=cid.split(":",1)[0]
        elif role=="neighbour":prefix=neighbor_map[cid]["prefix_id"]
        elif role=="random_control":prefix=cid.split(":",2)[1]
        if role=="random_control":members,mode=None,None
        else:members,mode=_resolve_candidate(cid,prefix,role,pair_map,triple_map,selected,neighbor_map)
        expected=[]
        if role=="random_control":
            # Controls match the base candidate's executed trade counts by asset.
            _tag,pfx,rest=cid.split(":",2);baseid,rep=rest.rsplit(":rep",1);replicate=int(rep)
            base_role=_role_for_id(baseid)
            base_key=(f"{pfx}:{baseid}" if base_role=="triple" else baseid,base_role,window)
            if window==pfx:base_key=(f"{pfx}:{baseid}","outer",window)
            base_paths=receipts_by_key.get(base_key,[])
            base_rows=_actual_rows(client,head,base_paths) if base_paths else []
            counts={sym:sum(x["asset"]==sym for x in base_rows) for sym in measurer.panels}
            if window==pfx:
                base_members,base_mode=_resolve_candidate(f"{pfx}:{baseid}",pfx,"outer",pair_map,triple_map,selected,neighbor_map)
            else:
                base_members,base_mode=_resolve_candidate(baseid,pfx,base_role,pair_map,triple_map,selected,neighbor_map)
            base_expected_by_asset={}
            for sym,p in measurer.panels.items():
                masks=[p.mask_of(nm) for nm in base_members]
                base_mask=_combine_independent(masks,base_mode,p.seg)
                lo,hi=p.ranges[window]
                base_expected_by_asset[sym]=independent_simulate_window(p.o,p.h,p.l,p.c,p.atr,p.seg,base_mask,sym,baseid,lo,hi)
                expected.extend(_random_reference(p,window,counts.get(sym,0),baseid,replicate))
        else:
            for sym,p in measurer.panels.items():
                if role=="baseline":mask=None
                else:
                    assert members is not None and mode is not None
                    masks=[p.mask_of(nm) for nm in members]
                    mask=_combine_independent(masks,mode,p.seg)
                lo,hi=p.ranges[window]
                expected.extend(independent_simulate_window(p.o,p.h,p.l,p.c,p.atr,p.seg,mask,sym,cid,lo,hi))
        exp_rows=[trade_row(t,cid,role,window,measurer.panels) for t in expected]
        if role=="baseline":
            for sym in measurer.panels:
                ar=[x for x in exp_rows if x["asset"]==sym];n=len(ar);net=float(sum(x["net_dollars"] for x in ar))
                expected_control_rows.append({"candidate":"NO-SIGNAL","control_type":"no_signal","replicate":0,
                    "asset":sym,"window":window,"n":n,"matched_count":None,"net":net,
                    "expectancy":net/n if n else None,"paired_difference":None,"ci_lo":None,"ci_hi":None,"seed":None})
        elif role=="random_control":
            for sym in measurer.panels:
                ar=[x for x in exp_rows if x["asset"]==sym];n=len(ar);net=float(sum(x["net_dollars"] for x in ar))
                base_asset=[dict(x,asset=sym) for x in base_expected_by_asset.get(sym,[])]
                paired=_independent_paired_difference(base_asset,ar,window,measurer.panels[sym]) if n==int(counts.get(sym,0)) else None
                expected_control_rows.append({"candidate":baseid,"control_type":"random_entry","replicate":replicate,
                    "asset":sym,"window":window,"n":n,"matched_count":int(counts.get(sym,0)),"net":net,
                    "expectancy":net/n if n else None,"paired_difference":paired["diff"] if paired else None,
                    "ci_lo":paired["lo5"] if paired else None,"ci_hi":paired["hi95"] if paired else None,
                    "seed":M.sha_seed(f"84|{sym}|{window}|{baseid}|{replicate}")})
        try:stored_metric=next(summary_metrics)
        except StopIteration:raise TransportError("missing raw-derived summary metric row: "+str(key))
        expected_metric=_audit_metric_row(cid,role,window,"ALL","summary",exp_rows,next(iter(measurer.panels.values())))
        inferential_role=role in ("single","pair","triple","outer","neighbour","descriptive")
        registered_stats=_independent_block_stats(exp_rows,window,measurer.panels) if exp_rows else None
        infer_fields=("p_raw","ci_lo","ci_hi","baseline_win_rate","breakeven_rate","lift_win_points")
        stored_has_inference=any(stored_metric.get(field) is not None for field in infer_fields)
        registered=stored_metric.get("metric_status","").startswith("REGISTERED_BLOCK_STATS")
        if stored_has_inference:
            if not registered_stats:raise TransportError("inferential metric exists for empty raw group: "+str(key))
            expected_metric.update({k:registered_stats[k] for k in ("p_raw","ci_lo","ci_hi","breakeven_rate")})
            if registered and inferential_role:
                expected_metric.update({k:registered_stats[k] for k in ("baseline_win_rate","lift_win_points")})
                expected_metric["metric_status"]="REGISTERED_BLOCK_STATS; Holm_and_power_pending"
                checked_inference_metrics+=1
            else:
                expected_metric["baseline_win_rate"]=None;expected_metric["lift_win_points"]=None
        else:
            expected_metric.update({field:None for field in infer_fields})
        _compare_metric(stored_metric,expected_metric,key);checked_summary_metrics+=1
        for sym,panel in measurer.panels.items():
            asset_trades=[x for x in exp_rows if x["asset"]==sym]
            try:stored_asset=next(asset_metrics)
            except StopIteration:raise TransportError("missing raw-derived per-asset metric row: "+str((key,sym)))
            expected_asset=_audit_metric_row(cid,role,window,sym,"asset",asset_trades,panel)
            asset_infer_fields=("baseline_win_rate","breakeven_rate","lift_win_points","p_raw","ci_lo","ci_hi")
            stored_has_asset_stats=any(stored_asset.get(field) is not None for field in asset_infer_fields)
            asset_registered=stored_asset.get("metric_status","").startswith("REGISTERED_BLOCK_STATS")
            if stored_has_asset_stats:
                asset_stats=_independent_asset_stats(asset_trades,window,panel)
                expected_asset.update({k:asset_stats[k] for k in ("breakeven_rate","p_raw","ci_lo","ci_hi")})
                if asset_registered:
                    expected_asset.update({k:asset_stats[k] for k in ("baseline_win_rate","lift_win_points")})
                    if asset_trades:expected_asset["metric_status"]="REGISTERED_BLOCK_STATS; Holm_and_power_pending"
                else:
                    expected_asset["baseline_win_rate"]=None;expected_asset["lift_win_points"]=None
            else:expected_asset.update({field:None for field in asset_infer_fields})
            _compare_metric(stored_asset,expected_asset,(key,sym));checked_asset_metrics+=1
            if len(window) in (6,7) and window[:4].isdigit() and window[4:] in ("H1","H2","H2p"):
                expected_halfyear_rows.append({"candidate":cid,"asset":sym,"halfyear":window,
                    "partial":int(window.endswith("p")),"n":expected_asset["n_exec"],
                    "net":expected_asset["net_dollars"],"pf":expected_asset["profit_factor"],
                    "win":expected_asset["win_rate"],"baseline":expected_asset["baseline_win_rate"],
                    "lift":expected_asset["lift_win_points"],"ci_lo":expected_asset["ci_lo"],"ci_hi":expected_asset["ci_hi"]})
        keyfn=lambda x:(x["asset"],int(x["signal_bar"]))
        actual.sort(key=keyfn);exp_rows.sort(key=keyfn)
        if len(actual)!=len(exp_rows):raise TransportError(f"independent rebuild count mismatch {key}: stored={len(actual)} rebuilt={len(exp_rows)}")
        for ai,(a,b) in enumerate(zip(actual,exp_rows)):
            for field in TRADE_SCHEMA.names:
                av,bv=a[field],b[field]
                if isinstance(bv,float):
                    if not math.isclose(float(av),float(bv),rel_tol=0,abs_tol=1e-9):
                        raise TransportError(f"independent rebuild mismatch {key} row {ai} field {field}: {av} vs {bv}")
                elif av!=bv:
                    raise TransportError(f"independent rebuild mismatch {key} row {ai} field {field}: {av} vs {bv}")
        checked_groups+=1;checked_trades+=len(exp_rows)
    try:next(summary_metrics);raise TransportError("extra summary metric rows after coverage exhausted")
    except StopIteration:pass
    summary_rows,summary_parts=_metric_rows.last_meta
    try:next(asset_metrics);raise TransportError("extra per-asset metric rows after coverage exhausted")
    except StopIteration:pass
    asset_rows,asset_parts=_metric_rows.last_meta
    stored_controls,control_parts=_control_rows(client,head,run_id)
    _compare_control_rows(stored_controls,expected_control_rows)
    stored_halfyears,halfyear_parts=_halfyear_rows(client,head,run_id)
    _compare_halfyear_rows(stored_halfyears,expected_halfyear_rows)
    if checked_trades!=base_check["trade_rows"]:raise TransportError("full rebuild trade total differs from verified raw total")
    if checked_summary_metrics!=len(coverage) or summary_rows!=len(coverage):raise TransportError("summary metric coverage does not match trade coverage")
    if checked_asset_metrics!=len(coverage)*len(measurer.panels) or asset_rows!=checked_asset_metrics:raise TransportError("per-asset metric coverage does not match trade coverage")
    return {**base_check,"groups_rebuilt":checked_groups,"trades_rebuilt":checked_trades,
            "independent_execution_rebuild":"PASS","raw_metric_reconciliation":"PASS",
            "metrics_reconciliation":"PARTIAL_RAW_METRICS; Holm_power_and_complete_control_tests_pending",
            "independent_inference_rows_reconciled":checked_inference_metrics,
            "controls_reconciliation":"PASS_RAW_CONTROL_TABLE; paired_difference_and_CI_pending",
            "control_result_rows":len(stored_controls),"control_partitions":len(control_parts),
            "halfyear_raw_reconciliation":"PASS; per_asset_baseline_lift_CI_pending",
            "halfyear_rows":len(stored_halfyears),"halfyear_partitions":len(halfyear_parts),
            "summary_metric_rows":summary_rows,"asset_metric_rows":asset_rows,
            "metric_partitions":summary_parts+asset_parts+control_parts+halfyear_parts,
            "metric_partition_receipts":summary_parts+asset_parts+control_parts+halfyear_parts,
            "violations":0}
