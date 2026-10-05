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
    from .transport import GitHubTransport, TransportError
    from . import engine as E
    from . import measure as M
    from . import indicators as I
except ImportError:
    from streaming import BASE, TRADE_SCHEMA, _row as trade_row
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


def _read_csv(client,head,name):
    raw=client.blob_from_commit(head,f"{BASE}/{name}").decode("utf-8")
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


def rebuild_all(client: GitHubTransport,head: str,run_id: str,measurer=None) -> dict:
    """Independently regenerate every indexed trade group at one fixed head."""
    base_check=verify_remote_partitions(client,head,run_id)
    coverage=_run_index(client,head,run_id)
    _pointers,receipts=_run_receipts(client,head,run_id)
    pair_rows=_read_csv(client,head,"pairs_registry.csv")
    pair_map={r["pair_id"]:(r["member_a"],r["member_b"]) for r in pair_rows}
    tr_rows=_read_csv(client,head,"triples_registry.csv")
    triple_map={(r["prefix_id"],r["triple_id"]):r for r in tr_rows if r.get("triple_id")}
    sel_rows=_read_csv(client,head,"selection_log.csv")
    selected={r["prefix"]:r["candidate"] for r in sel_rows if r.get("selected")=="1" and r.get("candidate")!="CASH"}
    ng=_read_csv(client,head,"neighbors_registry.csv")
    neighbor_map={r["neighbour_id"]:r for r in ng if r.get("neighbour_id")}
    if measurer is None:measurer=M.Measurer()
    receipts_by_key={}
    for r in receipts:receipts_by_key.setdefault((r["candidate_id"],r["role"],r["window"]),[]).append(r["path"])
    checked_groups=checked_trades=0;violations=[]
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
            for sym,p in measurer.panels.items():expected.extend(_random_reference(p,window,counts.get(sym,0),baseid,replicate))
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
    if checked_trades!=base_check["trade_rows"]:raise TransportError("full rebuild trade total differs from verified raw total")
    return {**base_check,"groups_rebuilt":checked_groups,"trades_rebuilt":checked_trades,
            "independent_execution_rebuild":"PASS","violations":0}
