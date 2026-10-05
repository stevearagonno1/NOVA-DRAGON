"""Bounded, raw-trade-derived descriptive metric partitions.

This first version deliberately leaves inferential/selection fields null;
those require the registered synchronized bootstrap and are not fabricated.
"""
from __future__ import annotations
import hashlib
import io
import math
import urllib.parse
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .stats import wilson, pf, block_ci, z_from_lb, holm, power_n
from . import measure as M
from .transport import GitHubTransport, TransportError

BASE="history/research/hyp_lab_out/L0084-entry-mix-r1"
MAX_PART_BYTES=8_000_000
ROWS_PER_PART=2400
HALFYEAR_COLUMNS=("candidate","asset","halfyear","partial","n","net","pf","win","baseline","lift","ci_lo","ci_hi")
ADJUSTMENT_SCHEMA=pa.schema([
    ("candidate_id",pa.string()),("role",pa.string()),("window",pa.string()),
    ("p_raw",pa.float64()),("p_adjusted",pa.float64()),("power80",pa.float64()),
    ("n80",pa.int64()),("alpha",pa.float64()),("family_m",pa.int64())])

CONTROL_SCHEMA=pa.schema([
    ("candidate",pa.string()),("control_type",pa.string()),("replicate",pa.int64()),
    ("asset",pa.string()),("window",pa.string()),("n",pa.int64()),
    ("matched_count",pa.int64()),("net",pa.float64()),("expectancy",pa.float64()),
    ("paired_difference",pa.float64()),("ci_lo",pa.float64()),("ci_hi",pa.float64()),
    ("seed",pa.uint64())])

METRIC_SCHEMA=pa.schema([
    ("candidate_id",pa.string()),("members",pa.string()),("mode",pa.string()),
    ("role",pa.string()),("window",pa.string()),
    ("asset",pa.string()),("scope",pa.string()),
    ("n_exec",pa.int64()),("n_win",pa.int64()),("n_stop",pa.int64()),
    ("n_timeout",pa.int64()),("n_resolved",pa.int64()),("n_eff",pa.int64()),
    ("n_signals",pa.int64()),("n_incomplete",pa.int64()),
    ("win_rate",pa.float64()),("wilson_lo",pa.float64()),("wilson_hi",pa.float64()),
    ("gross_dollars",pa.float64()),("cost_dollars",pa.float64()),
    ("net_dollars",pa.float64()),("expectancy_dollars",pa.float64()),
    ("profit_factor",pa.float64()),("gross_atr_r",pa.float64()),
    ("cost_atr",pa.float64()),("net_atr_r",pa.float64()),("barrier_r",pa.float64()),
    ("mae_atr_r",pa.float64()),("mfe_atr_r",pa.float64()),
    ("mean_holding_bars",pa.float64()),("mean_time_to_hit_bars",pa.float64()),
    ("gap_count",pa.int64()),("double_touch_count",pa.int64()),
    ("n_active_days",pa.int64()),("coverage",pa.float64()),
    ("mdd_dollars",pa.float64()),("mdd_pct_book",pa.float64()),
    ("drawdown_duration_trades",pa.int64()),("worst_day_dollars",pa.float64()),
    ("longest_losing_streak",pa.int64()),("exposure_bars",pa.int64()),
    ("baseline_win_rate",pa.float64()),("breakeven_rate",pa.float64()),
    ("lift_win_points",pa.float64()),("p_raw",pa.float64()),
    ("p_adjusted",pa.float64()),("ci_lo",pa.float64()),("ci_hi",pa.float64()),
    ("power80",pa.float64()),("metric_status",pa.string())])


def _metric_row(candidate,role,window,asset,scope,trades,panel,baseline_trades=None,members=None,mode=None):
    trades=sorted(trades,key=lambda t:(int(t["fill_bar"]),int(t["signal_bar"])))
    n=len(trades);wins=sum(t["outcome"]=="target" for t in trades)
    stops=sum(t["outcome"]=="stop" for t in trades);timeouts=sum(t["outcome"]=="timeout" for t in trades)
    resolved=wins+stops
    winrate=wins/resolved if resolved else None
    _,wlo,whi=wilson(wins,resolved) if resolved else (None,None,None)
    nets=np.asarray([t["net_dollars"] for t in trades],dtype=float)
    gross=np.asarray([t["gross_dollars"] for t in trades],dtype=float)
    costs=np.asarray([t["cost_dollars"] for t in trades],dtype=float)
    def mean(key):
        return float(np.mean([t[key] for t in trades])) if trades else None
    if trades:
        eq=1000.0+np.cumsum(nets);peaks=np.maximum.accumulate(np.r_[1000.0,eq])[:-1]
        dd=eq-peaks;mdd=min(0.0,float(dd.min())) if len(dd) else 0.0;cur=duration=streak=maxstreak=0
        for x in dd:
            cur=cur+1 if x<0 else 0;duration=max(duration,cur)
        cur=0
        for x in nets:
            cur=cur+1 if x<0 else 0;maxstreak=max(maxstreak,cur)
        byday={}
        for t in trades:
            day=str(pd.Timestamp(panel.dt[int(t["fill_bar"])]).date())
            byday[day]=byday.get(day,0.0)+float(t["net_dollars"])
        worst=min(byday.values()) if byday else None
        active=len(byday)
        lo,hi=panel.ranges[window]
        days=max(1,(pd.Timestamp(panel.dt[int(hi)]).date()-pd.Timestamp(panel.dt[int(lo)]).date()).days+1)
        coverage=active/days
    else:
        mdd=0.0;duration=0;maxstreak=0;worst=None;active=0;coverage=0.0
    gross_sum=float(gross.sum()) if n else 0.0;cost_sum=float(costs.sum()) if n else 0.0;net_sum=float(nets.sum()) if n else 0.0
    p_factor=pf(nets) if n else None
    base=list(baseline_trades or []);base_w=sum(t["outcome"]=="target" for t in base);base_d=sum(t["outcome"] in ("target","stop") for t in base)
    baseline_wr=base_w/base_d if base_d else None
    breakeven=0.5+float(np.mean([t["cost_atr"] for t in trades]))/3 if trades else None
    lift=(winrate-baseline_wr)*100 if winrate is not None and baseline_wr is not None else None
    ci_lo=ci_hi=p_raw=None
    if trades and window in M.WIN_RANGE:
        start,end=M.WIN_RANGE[window];n_days=int((np.datetime64(end)-np.datetime64(start)).astype(int))+1
        first=np.datetime64(start);day_ix=[]
        for t in trades:
            stamp=np.datetime64(pd.Timestamp(panel.dt[int(t["fill_bar"])]).date())
            day_ix.append(int((stamp-first).astype(int)))
        ci=block_ci(np.asarray(day_ix,dtype=int),nets,n_days)
        ci_lo=ci["lo5"];ci_hi=ci["hi95"];p_raw=z_from_lb(ci["lo5"],ci["expectancy"],ci["se"])
    status="REGISTERED_BLOCK_STATS; Holm_and_power_pending" if baseline_trades is not None and n else ("ZERO_TRADES; inference_not_computed" if not n else "RAW_DESCRIPTIVE; inference_not_computed")
    return {"candidate_id":str(candidate),"members":"|".join(members) if members else None,"mode":str(mode) if mode else None,
      "role":str(role),"window":str(window),"asset":str(asset),"scope":str(scope),
      "n_exec":n,"n_win":wins,"n_stop":stops,"n_timeout":timeouts,"n_resolved":resolved,"n_eff":n,
      "n_signals":None,"n_incomplete":None,"win_rate":winrate,"wilson_lo":wlo,"wilson_hi":whi,
      "gross_dollars":gross_sum,"cost_dollars":cost_sum,"net_dollars":net_sum,
      "expectancy_dollars":float(nets.mean()) if n else None,"profit_factor":p_factor,
      "gross_atr_r":mean("gross_atr_r"),"cost_atr":mean("cost_atr"),"net_atr_r":mean("net_atr_r"),
      "barrier_r":mean("barrier_r"),"mae_atr_r":mean("mae_atr_r"),"mfe_atr_r":mean("mfe_atr_r"),
      "mean_holding_bars":mean("holding_bars"),
      "mean_time_to_hit_bars":float(np.mean([t["holding_bars"] for t in trades if t["outcome"] in ("target","stop")])) if any(t["outcome"] in ("target","stop") for t in trades) else None,
      "gap_count":sum(bool(t["gap_flag"]) for t in trades),"double_touch_count":sum(bool(t["double_touch"]) for t in trades),
      "n_active_days":active,"coverage":coverage,"mdd_dollars":mdd,"mdd_pct_book":mdd/1000*100,
      "drawdown_duration_trades":duration,"worst_day_dollars":worst,"longest_losing_streak":maxstreak,
      "exposure_bars":sum(int(t["holding_bars"]) for t in trades),"baseline_win_rate":baseline_wr,"breakeven_rate":breakeven,
      "lift_win_points":lift,"p_raw":p_raw,"p_adjusted":None,"ci_lo":ci_lo,"ci_hi":ci_hi,"power80":None,"metric_status":status}


def _encode(rows,schema=METRIC_SCHEMA):
    tab=pa.Table.from_pylist(rows,schema=schema);sink=pa.BufferOutputStream()
    pq.write_table(tab,sink,compression="zstd",version="2.6")
    return sink.getvalue().to_pybytes(),tab


def _same_table(a,b):
    if not a.schema.equals(b.schema,check_metadata=False) or a.num_rows!=b.num_rows:return False
    for ra,rb in zip(a.to_pylist(),b.to_pylist()):
        for name in a.schema.names:
            x,y=ra[name],rb[name]
            if x is None or y is None:
                if x is not None or y is not None:return False
            elif isinstance(x,float) and isinstance(y,float):
                if math.isnan(x) and math.isnan(y):continue
                if not math.isclose(x,y,rel_tol=0,abs_tol=0):return False
            elif x!=y:return False
    return True


class RawMetricWriter:
    """Creates resumable summary and per-asset metrics from each raw group."""
    def __init__(self,transport,run_id,rows_per_part=ROWS_PER_PART):
        self.transport=transport or GitHubTransport();self.run_id=str(run_id);self.rows_per_part=int(rows_per_part)
        self.summary=[];self.assets=[];self.controls=[];self.halfyears=[];self.adjustment_groups={};self.adjustment_map={};self.group_count=0;self.summary_part=0;self.asset_part=0;self.control_part=0;self.halfyear_part=0;self.adjustment_part=0;self.final_part=0
        self.expected_summary_parts=0;self.expected_asset_parts=0;self.expected_control_parts=0;self.expected_halfyear_parts=0;self.expected_adjustment_parts=0;self.expected_final_parts=0;self.adjustment_rows=0;self.final_metric_rows=0
        self.parts=[];self.closed=False
        if hasattr(self.transport,"list_directory"):
            for kind,attr in (("metrics_raw","expected_summary_parts"),("metrics_by_asset","expected_asset_parts"),("controls","expected_control_parts"),("metric_adjustments","expected_adjustment_parts")):  
                try:names=self.transport.list_directory(self.transport.branch_head(),f"{BASE}/{kind}/run={urllib.parse.quote(self.run_id,safe='-_=.')}")
                except TransportError:names=[]
                ids=[]
                for name in names:
                    if name.startswith("part-") and name.endswith(".parquet"):
                        try:ids.append(int(name[5:-8]))
                        except ValueError:raise TransportError("invalid metric partition name")
                setattr(self,attr,max(ids,default=-1)+1)
            try:names=self.transport.list_directory(self.transport.branch_head(),f"{BASE}/metrics/run={urllib.parse.quote(self.run_id,safe='-_=.')}")
            except TransportError:names=[]
            ids=[]
            for name in names:
                if name.startswith("part-") and name.endswith(".parquet"):
                    try:ids.append(int(name[5:-8]))
                    except ValueError:raise TransportError("invalid final metric partition name")
            self.expected_final_parts=max(ids,default=-1)+1
            try:names=self.transport.list_directory(self.transport.branch_head(),f"{BASE}/halfyears.csv/run={urllib.parse.quote(self.run_id,safe='-_=.')}")
            except TransportError:names=[]
            ids=[]
            for name in names:
                if name.startswith("part-") and name.endswith(".csv"):
                    try:ids.append(int(name[5:-4]))
                    except ValueError:raise TransportError("invalid halfyear partition name")
            self.expected_halfyear_parts=max(ids,default=-1)+1
    def add_window(self,candidate,role,window,trades_by_asset,panels,stats=None,baseline_by_asset=None,control_info=None,members=None,mode=None):
        asset_rows=[];all_trades=[]
        for asset,panel in panels.items():
            trades=list(trades_by_asset.get(asset,[]));all_trades.extend(trades)
            asset_rows.append(_metric_row(candidate,role,window,asset,"asset",trades,panel,
                (baseline_by_asset or {}).get(asset) if baseline_by_asset is not None else None,members,mode))
        is_halfyear=(len(window) in (6,7) and window[:4].isdigit() and window[4:] in ("H1","H2","H2p"))
        if is_halfyear:
            for row in asset_rows:
                self.halfyears.append({"candidate":str(candidate),"asset":row["asset"],"halfyear":str(window),
                    "partial":int(window.endswith("p")),"n":int(row["n_exec"]),"net":float(row["net_dollars"]),
                    "pf":row["profit_factor"],"win":row["win_rate"],"baseline":row["baseline_win_rate"],
                    "lift":row["lift_win_points"],"ci_lo":row["ci_lo"],"ci_hi":row["ci_hi"]})
        # A synthetic or partial group missing an asset is still represented as zero.
        summary_panel=next(iter(panels.values()))
        summary=_metric_row(candidate,role,window,"ALL","summary",all_trades,summary_panel,members=members,mode=mode)
        # The runner's registered synchronized block bootstrap is computed once
        # by stat_window and handed in; never substitute a second, unsynchronized
        # per-trade resampling implementation here.
        if stats:
            summary.update({
                "baseline_win_rate":stats.get("baseline_win"),
                "breakeven_rate":stats.get("breakeven_ref"),
                "lift_win_points":stats.get("lift_win_pts"),
                "p_raw":stats.get("p_raw"),
                "ci_lo":stats.get("exp_lo5"),
                "ci_hi":stats.get("exp_hi95"),
                "metric_status":"REGISTERED_BLOCK_STATS; Holm_and_power_pending"})
        self.summary.append(summary)
        self.assets.extend(asset_rows);self.group_count+=1
        if role in ("single","pair","triple"):
            raw_p=stats.get("p_raw") if stats else None
            power=None;n80=None
            if stats and all_trades:
                vals=np.asarray([float(t["net_dollars"]) for t in all_trades],dtype=float)
                sd=float(np.std(vals,ddof=1)) if len(vals)>1 else float("nan")
                effect=float(stats["expectancy"])
                pw=(power_n(effect,sd,float(stats.get("exp_se",float("nan"))),len(vals),0.05/70330)
                    if effect!=0 else {})
                power=pw.get("power_at_n");n80=pw.get("n80")
            self.adjustment_groups.setdefault(str(window),[]).append((str(candidate),str(role),raw_p,power,n80))
        if role=="baseline":
            for row in asset_rows:
                count=int(row["n_exec"]);net=float(row["net_dollars"])
                self.controls.append({"candidate":"NO-SIGNAL","control_type":"no_signal","replicate":0,
                    "asset":row["asset"],"window":window,"n":count,"matched_count":None,
                    "net":net,"expectancy":net/count if count else None,"paired_difference":None,
                    "ci_lo":None,"ci_hi":None,"seed":None})
        elif role=="random_control" and control_info:
            for row in asset_rows:
                count=int(row["n_exec"]);net=float(row["net_dollars"]);asset=row["asset"]
                self.controls.append({"candidate":str(control_info["candidate"]),"control_type":"random_entry",
                    "replicate":int(control_info["replicate"]),"asset":asset,"window":window,"n":count,
                    "matched_count":int(control_info["matched_counts"].get(asset,0)),"net":net,
                    "expectancy":net/count if count else None,
                    "paired_difference":(control_info.get("paired_by_asset",{}).get(asset) or {}).get("diff"),
                    "ci_lo":(control_info.get("paired_by_asset",{}).get(asset) or {}).get("lo5"),
                    "ci_hi":(control_info.get("paired_by_asset",{}).get(asset) or {}).get("hi95"),
                    "seed":int(control_info["seeds"][asset])})
        if (len(self.controls)>=self.rows_per_part or len(self.halfyears)>=self.rows_per_part
                or len(self.summary)>=self.rows_per_part or len(self.assets)>=self.rows_per_part):
            self.flush()
    def _commit_table(self,kind,part,rows):
        if not rows:return None
        schema=CONTROL_SCHEMA if kind=="controls" else ADJUSTMENT_SCHEMA if kind=="metric_adjustments" else METRIC_SCHEMA
        payload,table=_encode(rows,schema=schema)
        if len(payload)>MAX_PART_BYTES:
            if len(rows)<2:raise TransportError("single metric row exceeds 8MB")
            mid=len(rows)//2
            first=self._commit_table(kind,part,rows[:mid]);second=self._commit_table(kind,part+1,rows[mid:])
            return [x for value in (first,second) for x in (value if isinstance(value,list) else [value]) if x]
        path=f"{BASE}/{kind}/run={urllib.parse.quote(self.run_id,safe='-_=.')}/part-{part:05d}.parquet"
        head=self.transport.branch_head()
        try:
            remote=self.transport.blob_from_commit(head,path)
            if len(remote)!=len(payload) or hashlib.sha256(remote).digest()!=hashlib.sha256(payload).digest():raise TransportError("resumed metric partition differs: "+path)
            rt=pq.read_table(pa.BufferReader(remote))
            if not _same_table(rt,table):raise TransportError("resumed metric schema/values differ: "+path)
            commit=head;receipts=[];reused=True
        except TransportError as exc:
            if "path resolution failed" not in str(exc):raise
            commit,receipts=self.transport.commit_files({path:payload},head,"L0084-R1: append raw-derived metric partition")
            remote=self.transport.blob_from_commit(commit,path)
            if hashlib.sha256(remote).digest()!=hashlib.sha256(payload).digest():raise TransportError("metric readback hash mismatch")
            rt=pq.read_table(pa.BufferReader(remote))
            if not _same_table(rt,table):raise TransportError("metric readback values/schema mismatch")
            reused=False
        rec=receipts[0] if receipts else None
        actual_blob=rec.blob_sha if rec else hashlib.sha1(b"blob "+str(len(remote)).encode()+b"\0"+remote).hexdigest()
        item={"path":path,"rows":table.num_rows,"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest(),
          "git_blob_sha":actual_blob,"commit_sha":commit,"reused":reused}
        self.parts.append(item);return item
    def _commit_halfyear_csv(self,part,rows):
        if not rows:return None
        payload=pd.DataFrame(rows,columns=HALFYEAR_COLUMNS).to_csv(index=False,lineterminator="\n").encode("utf-8")
        if len(payload)>MAX_PART_BYTES:raise TransportError("half-year CSV partition exceeds 8,000,000 bytes")
        path=f"{BASE}/halfyears.csv/run={urllib.parse.quote(self.run_id,safe='-_=.')}/part-{part:05d}.csv"
        head=self.transport.branch_head()
        try:
            remote=self.transport.blob_from_commit(head,path)
            if remote!=payload:raise TransportError("resumed half-year CSV differs: "+path)
            commit=head;reused=True
        except TransportError as exc:
            if "path resolution failed" not in str(exc):raise
            commit,receipts=self.transport.commit_files({path:payload},head,"L0084-R1: append half-year CSV partition")
            remote=self.transport.blob_from_commit(commit,path)
            if remote!=payload:raise TransportError("half-year CSV readback mismatch: "+path)
            reused=False
        item={"path":path,"rows":len(rows),"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest(),
              "commit_sha":commit,"reused":reused}
        self.parts.append(item);return item
    def flush(self):
        srows,self.summary=self.summary,[];arows,self.assets=self.assets,[];crows,self.controls=self.controls,[];hrows,self.halfyears=self.halfyears,[]
        if srows:
            made=self._commit_table("metrics_raw",self.summary_part,srows)
            self.summary_part+=len(made) if isinstance(made,list) else 1
            self.expected_summary_parts=max(self.expected_summary_parts,self.summary_part)
        if arows:
            made=self._commit_table("metrics_by_asset",self.asset_part,arows)
            self.asset_part+=len(made) if isinstance(made,list) else 1
            self.expected_asset_parts=max(self.expected_asset_parts,self.asset_part)
        if crows:
            made=self._commit_table("controls",self.control_part,crows)
            self.control_part+=len(made) if isinstance(made,list) else 1
            self.expected_control_parts=max(self.expected_control_parts,self.control_part)
        if hrows:
            made=self._commit_halfyear_csv(self.halfyear_part,hrows)
            self.halfyear_part+=1
            self.expected_halfyear_parts=max(self.expected_halfyear_parts,self.halfyear_part)
    def _finalize_adjustments(self):
        pending=[]
        for window,items in sorted(self.adjustment_groups.items()):
            valid=[i for i,x in enumerate(items) if x[2] is not None and math.isfinite(float(x[2]))]
            adjusted=holm([float(items[i][2]) for i in valid],m=70330) if valid else []
            adjmap={i:float(v) for i,v in zip(valid,adjusted)}
            for i,(candidate,role,praw,power,n80) in sorted(enumerate(items),key=lambda z:(z[1][0],z[1][1])):
                record={"candidate_id":candidate,"role":role,"window":window,
                    "p_raw":None if praw is None else float(praw),"p_adjusted":adjmap.get(i,1.0),
                    "power80":power,"n80":n80,"alpha":0.05/70330,"family_m":70330}
                self.adjustment_map[(candidate,role,window)]=record
                pending.append(record)
                if len(pending)>=self.rows_per_part:
                    self._commit_table("metric_adjustments",self.adjustment_part,pending)
                    self.adjustment_part+=1;self.expected_adjustment_parts=max(self.expected_adjustment_parts,self.adjustment_part)
                    self.adjustment_rows+=len(pending);pending=[]
        if pending:
            self._commit_table("metric_adjustments",self.adjustment_part,pending)
            self.adjustment_part+=1;self.expected_adjustment_parts=max(self.expected_adjustment_parts,self.adjustment_part)
            self.adjustment_rows+=len(pending)
        self.adjustment_groups.clear()
    def _finalize_full_metrics(self):
        for kind in ("metrics_raw","metrics_by_asset"):
            directory=f"{BASE}/{kind}/run={urllib.parse.quote(self.run_id,safe='-_=.')}"
            try:names=self.transport.list_directory(self.transport.branch_head(),directory)
            except TransportError as exc:
                if "directory resolution failed" in str(exc):continue
                raise
            for name in sorted(x for x in names if x.endswith(".parquet")):
                raw=self.transport.blob_from_commit(self.transport.branch_head(),directory+"/"+name)
                tab=pq.read_table(pa.BufferReader(raw))
                if not tab.schema.equals(METRIC_SCHEMA,check_metadata=False):raise TransportError("raw metric schema mismatch during final join")
                rows=tab.to_pylist()
                for row in rows:
                    if row["scope"]=="summary":
                        adj=self.adjustment_map.get((row["candidate_id"],row["role"],row["window"]))
                        if adj is not None:
                            row["p_adjusted"]=adj["p_adjusted"];row["power80"]=adj["power80"]
                            row["metric_status"]="REGISTERED_BLOCK_STATS; Holm_adjusted; power_on_file"
                for start in range(0,len(rows),self.rows_per_part):
                    block=rows[start:start+self.rows_per_part]
                    made=self._commit_table("metrics",self.final_part,block)
                    self.final_part+=len(made) if isinstance(made,list) else 1
                    self.expected_final_parts=max(self.expected_final_parts,self.final_part)
                    self.final_metric_rows+=len(block)
    def close(self):
        if self.closed:raise TransportError("metric writer already closed")
        self.flush();self._finalize_adjustments();self._finalize_full_metrics();self.closed=True
        if (self.summary_part!=self.expected_summary_parts or self.asset_part!=self.expected_asset_parts
                or self.control_part!=self.expected_control_parts or self.halfyear_part!=self.expected_halfyear_parts
                or self.adjustment_part!=self.expected_adjustment_parts or self.final_part!=self.expected_final_parts):
            raise TransportError(f"metric resume coverage mismatch: summary {self.summary_part}/{self.expected_summary_parts}; asset {self.asset_part}/{self.expected_asset_parts}; controls {self.control_part}/{self.expected_control_parts}; halfyears {self.halfyear_part}/{self.expected_halfyear_parts}; adjustments {self.adjustment_part}/{self.expected_adjustment_parts}; final metrics {self.final_part}/{self.expected_final_parts}")
        return {"groups":self.group_count,"parts":list(self.parts),"summary_part_count":self.summary_part,
                "asset_part_count":self.asset_part,"control_part_count":self.control_part,
                "halfyear_part_count":self.halfyear_part,"adjustment_part_count":self.adjustment_part,
                "adjustment_rows":self.adjustment_rows,"final_metric_part_count":self.final_part,
                "final_metric_rows":self.final_metric_rows}
