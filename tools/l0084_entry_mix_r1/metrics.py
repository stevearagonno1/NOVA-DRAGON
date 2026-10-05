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

from .stats import wilson, pf
from .transport import GitHubTransport, TransportError

BASE="history/research/hyp_lab_out/L0084-entry-mix-r1"
MAX_PART_BYTES=8_000_000
ROWS_PER_PART=2400
METRIC_SCHEMA=pa.schema([
    ("candidate_id",pa.string()),("role",pa.string()),("window",pa.string()),
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


def _metric_row(candidate,role,window,asset,scope,trades,panel):
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
    status="ZERO_TRADES; inference_not_computed" if not n else "RAW_DESCRIPTIVE; inference_not_computed"
    return {"candidate_id":str(candidate),"role":str(role),"window":str(window),"asset":str(asset),"scope":str(scope),
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
      "exposure_bars":sum(int(t["holding_bars"]) for t in trades),"baseline_win_rate":None,"breakeven_rate":None,
      "lift_win_points":None,"p_raw":None,"p_adjusted":None,"ci_lo":None,"ci_hi":None,"power80":None,"metric_status":status}


def _encode(rows):
    tab=pa.Table.from_pylist(rows,schema=METRIC_SCHEMA);sink=pa.BufferOutputStream()
    pq.write_table(tab,sink,compression="zstd",version="2.6")
    return sink.getvalue().to_pybytes(),tab


class RawMetricWriter:
    """Creates resumable summary and per-asset metrics from each raw group."""
    def __init__(self,transport,run_id,rows_per_part=ROWS_PER_PART):
        self.transport=transport or GitHubTransport();self.run_id=str(run_id);self.rows_per_part=int(rows_per_part)
        self.summary=[];self.assets=[];self.group_count=0;self.summary_part=0;self.asset_part=0
        self.expected_summary_parts=0;self.expected_asset_parts=0
        self.parts=[];self.closed=False
        if hasattr(self.transport,"list_directory"):
            for kind,attr in (("metrics","expected_summary_parts"),("metrics_by_asset","expected_asset_parts")):
                try:names=self.transport.list_directory(self.transport.branch_head(),f"{BASE}/{kind}/run={urllib.parse.quote(self.run_id,safe='-_=.')}")
                except TransportError:names=[]
                ids=[]
                for name in names:
                    if name.startswith("part-") and name.endswith(".parquet"):
                        try:ids.append(int(name[5:-8]))
                        except ValueError:raise TransportError("invalid metric partition name")
                setattr(self,attr,max(ids,default=-1)+1)
    def add_window(self,candidate,role,window,trades_by_asset,panels):
        asset_rows=[];all_trades=[]
        for asset,panel in panels.items():
            trades=list(trades_by_asset.get(asset,[]));all_trades.extend(trades)
            asset_rows.append(_metric_row(candidate,role,window,asset,"asset",trades,panel))
        # A synthetic or partial group missing an asset is still represented as zero.
        summary_panel=next(iter(panels.values()))
        self.summary.append(_metric_row(candidate,role,window,"ALL","summary",all_trades,summary_panel))
        self.assets.extend(asset_rows);self.group_count+=1
        if len(self.summary)>=self.rows_per_part or len(self.assets)>=self.rows_per_part:
            self.flush()
    def _commit_table(self,kind,part,rows):
        if not rows:return None
        payload,table=_encode(rows)
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
            if not rt.schema.equals(METRIC_SCHEMA,check_metadata=False) or not rt.equals(table):raise TransportError("resumed metric schema/values differ: "+path)
            commit=head;receipts=[];reused=True
        except TransportError as exc:
            if "path resolution failed" not in str(exc):raise
            commit,receipts=self.transport.commit_files({path:payload},head,"L0084-R1: append raw-derived metric partition")
            remote=self.transport.blob_from_commit(commit,path)
            if hashlib.sha256(remote).digest()!=hashlib.sha256(payload).digest():raise TransportError("metric readback hash mismatch")
            rt=pq.read_table(pa.BufferReader(remote))
            if not rt.schema.equals(METRIC_SCHEMA,check_metadata=False) or not rt.equals(table):raise TransportError("metric readback values/schema mismatch")
            reused=False
        rec=receipts[0] if receipts else None
        actual_blob=rec.blob_sha if rec else hashlib.sha1(b"blob "+str(len(remote)).encode()+b"\0"+remote).hexdigest()
        item={"path":path,"rows":table.num_rows,"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest(),
          "git_blob_sha":actual_blob,"commit_sha":commit,"reused":reused}
        self.parts.append(item);return item
    def flush(self):
        srows,self.summary=self.summary,[];arows,self.assets=self.assets,[]
        if srows:
            made=self._commit_table("metrics",self.summary_part,srows)
            self.summary_part+=len(made) if isinstance(made,list) else 1
            self.expected_summary_parts=max(self.expected_summary_parts,self.summary_part)
        if arows:
            made=self._commit_table("metrics_by_asset",self.asset_part,arows)
            self.asset_part+=len(made) if isinstance(made,list) else 1
            self.expected_asset_parts=max(self.expected_asset_parts,self.asset_part)
    def close(self):
        if self.closed:raise TransportError("metric writer already closed")
        self.flush();self.closed=True
        if self.summary_part!=self.expected_summary_parts or self.asset_part!=self.expected_asset_parts:
            raise TransportError(f"metric resume coverage mismatch: summary parts {self.summary_part}/{self.expected_summary_parts}; asset parts {self.asset_part}/{self.expected_asset_parts}")
        return {"groups":self.group_count,"parts":list(self.parts),"summary_part_count":self.summary_part,"asset_part_count":self.asset_part}
