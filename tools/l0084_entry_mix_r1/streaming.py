"""Bounded-memory R1 Parquet writer backed only by the authorized GitHub API.

Parquet payloads are constructed in memory, committed in small batches, read
back from the exact commit, decoded and compared before their buffers are
released. No raw-trade temp file or local Git object is used.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
import math
import os
import resource
import urllib.parse
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

try:
    from .transport import GitHubTransport, TransportError
except ImportError:
    from transport import GitHubTransport, TransportError

BASE = "history/research/hyp_lab_out/L0084-entry-mix-r1"
MAX_PART_BYTES = 8_000_000
BATCH_BYTES = 5_000_000
BATCH_PARTS = 24
ROW_CHUNK = 500
SCHEMA_VERSION = "l0084-r1-trade-v1"
TRADE_SCHEMA = pa.schema([
    ("candidate_id", pa.string()), ("role", pa.string()),
    ("window", pa.string()), ("asset", pa.string()),
    ("signal_bar", pa.int64()), ("fill_bar", pa.int64()),
    ("exit_bar", pa.int64()), ("signal_time_utc", pa.string()),
    ("fill_time_utc", pa.string()), ("exit_time_utc", pa.string()),
    ("entry", pa.float64()), ("exit", pa.float64()), ("atr", pa.float64()),
    ("quantity", pa.float64()), ("notional", pa.float64()),
    ("outcome", pa.string()), ("gap_flag", pa.bool_()),
    ("double_touch", pa.bool_()), ("holding_bars", pa.int64()),
    ("gross_dollars", pa.float64()), ("cost_dollars", pa.float64()),
    ("net_dollars", pa.float64()), ("gross_atr_r", pa.float64()),
    ("cost_atr", pa.float64()), ("net_atr_r", pa.float64()),
    ("barrier_r", pa.float64()), ("mae_atr_r", pa.float64()),
    ("mfe_atr_r", pa.float64()), ("seg", pa.int64()),
])


def _quote(s):
    return urllib.parse.quote(str(s), safe="-_.")


def _utc_string(value):
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.isoformat().replace("+00:00", "Z")


def _row(t, candidate, role, window, panels):
    sym = t.get("symbol") or t.get("asset")
    if sym not in panels:
        raise ValueError(f"trade asset not in pinned universe: {sym}")
    p = panels[sym]
    i, f, j = int(t["signal_bar"]), int(t["fill_bar"]), int(t["exit_bar"])
    return {
        "candidate_id": str(candidate), "role": str(role), "window": str(window),
        "asset": str(sym), "signal_bar": i, "fill_bar": f, "exit_bar": j,
        "signal_time_utc": _utc_string(p.dt[i]),
        "fill_time_utc": _utc_string(p.dt[f]),
        "exit_time_utc": _utc_string(p.dt[j]),
        "entry": float(t["entry"]), "exit": float(t["exit"]),
        "atr": float(t["atr"]), "quantity": float(t["quantity"]),
        "notional": float(t["notional"]), "outcome": str(t["outcome"]),
        "gap_flag": bool(t["gap_flag"]), "double_touch": bool(t["double_touch"]),
        "holding_bars": int(t["holding_bars"]),
        "gross_dollars": float(t["gross_dollars"]),
        "cost_dollars": float(t["cost_dollars"]),
        "net_dollars": float(t["net_dollars"]),
        "gross_atr_r": float(t["gross_atr_r"]),
        "cost_atr": float(t["cost_atr"]), "net_atr_r": float(t["net_atr_r"]),
        "barrier_r": float(t["barrier_r"]),
        "mae_atr_r": float(t["mae_atr_r"]), "mfe_atr_r": float(t["mfe_atr_r"]),
        "seg": int(t["seg"]),
    }


def encode_rows(rows):
    table = pa.Table.from_pylist(rows, schema=TRADE_SCHEMA)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression="zstd", version="2.6")
    return sink.getvalue().to_pybytes(), table


@dataclass
class Pending:
    path: str
    payload: bytes
    table: pa.Table
    candidate: str
    role: str
    window: str
    part: int
    recovered_commit: str = ""


class RemoteTradeWriter:
    """Bounded writer for full trade rows and zero/nonzero window index rows."""
    def __init__(self, transport=None, run_id="r1", max_rows=ROW_CHUNK,
                 batch_bytes=BATCH_BYTES, batch_parts=BATCH_PARTS):
        self.transport = transport or GitHubTransport()
        self.run_id = str(run_id)
        self.max_rows = int(max_rows)
        self.batch_bytes = int(batch_bytes)
        self.batch_parts = int(batch_parts)
        if self.max_rows < 1 or self.batch_bytes > MAX_PART_BYTES or self.batch_bytes < 1:
            raise ValueError("invalid streaming limits")
        from .metrics import RawMetricWriter
        self.metric_writer=RawMetricWriter(self.transport,self.run_id)
        self.pending = []
        self.pending_bytes = 0
        self.index_rows = []
        self.index_part = 0
        self.part_counter = {}
        self.partition_count = 0
        self.row_count = 0
        self.peak_pending_bytes = 0
        self.peak_pending_rows = 0
        self.index_paths=[]
        self.journal_paths=[]
        self.journaled_paths=set()
        self.journal_part=0
        self._index_flush_limit=1000
        self.completed_windows={}
        self.completed_paths=set()
        self.run_has_remote_data=False
        self.memory_limit_bytes,self.memory_limit_source=self._detect_memory_limit()
        self._load_completed_journal()
        self._load_completed_index()
        self.peak_workspace_bytes,self.peak_rss_bytes=self._resource_snapshot()
        if hasattr(self.transport,"list_directory"):
            head=self.transport.branch_head()
            try:
                names=self.transport.list_directory(head,f"{BASE}/trades/run={_quote(self.run_id)}")
                self.run_has_remote_data=bool(names)
            except TransportError:pass
            try:
                names=self.transport.list_directory(head,f"{BASE}/measurement_index/run={_quote(self.run_id)}")
                parts=[int(x.split("part-")[1].split(".")[0]) for x in names if x.startswith("part-")]
                self.index_part=max(parts,default=-1)+1
            except TransportError:pass
            try:
                names=self.transport.list_directory(head,f"{BASE}/storage_journal/run={_quote(self.run_id)}")
                parts=[int(x.split("part-")[1].split(".")[0]) for x in names if x.startswith("part-")]
                self.journal_part=max(parts,default=-1)+1
            except TransportError:pass

    @staticmethod
    def _detect_memory_limit():
        limits=[]
        for path,source in (("/sys/fs/cgroup/memory.max","cgroup-v2"),
                            ("/sys/fs/cgroup/memory/memory.limit_in_bytes","cgroup-v1")):
            try:
                raw=open(path,encoding="ascii").read().strip()
                if raw!="max":
                    value=int(raw)
                    if 0<value<(1<<60):limits.append((value,source))
            except (OSError,ValueError):pass
        try:
            soft,_=resource.getrlimit(resource.RLIMIT_AS)
            if soft not in (-1,resource.RLIM_INFINITY) and soft>0:limits.append((int(soft),"RLIMIT_AS"))
        except (AttributeError,OSError,ValueError):pass
        return min(limits) if limits else (None,"unbounded-or-unknown")

    def _load_completed_journal(self):
        if not hasattr(self.transport,"list_directory"):return
        head=self.transport.branch_head()
        try:raw=self.transport.blob_from_commit(head,f"{BASE}/storage_journal.jsonl")
        except TransportError as exc:
            if "path resolution failed" not in str(exc):raise
            return
        for line in raw.decode("utf-8").splitlines():
            pointer=json.loads(line)
            if pointer.get("run_id")!=self.run_id:continue
            shard=self.transport.blob_from_commit(head,pointer["path"])
            if len(shard)!=int(pointer["bytes"]) or hashlib.sha256(shard).hexdigest()!=pointer["sha256"]:
                raise TransportError("resume storage-journal shard hash mismatch")
            if hashlib.sha1(b"blob "+str(len(shard)).encode()+b"\0"+shard).hexdigest()!=pointer["git_blob_sha"]:
                raise TransportError("resume storage-journal Git blob SHA mismatch")
            self.journal_paths.append({"path":pointer["path"],"rows":int(pointer["rows"]),
                "bytes":int(pointer["bytes"]),"sha256":pointer["sha256"],
                "blob_sha":pointer["git_blob_sha"],"commit_sha":pointer["commit_sha"]})
            for entry in shard.decode("utf-8").splitlines():
                rec=json.loads(entry)
                if rec.get("event")=="trade_partition_committed":self.journaled_paths.add(rec["path"])

    def _resource_snapshot(self):
        total=0
        for root,dirs,files in os.walk("/home/user"):
            for name in files:
                try:total+=os.path.getsize(os.path.join(root,name))
                except OSError:pass
        rss=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        if total>125_000_000:raise TransportError(f"workspace disk guard exceeded: {total} bytes")
        self.peak_workspace_bytes=max(getattr(self,"peak_workspace_bytes",0),total)
        self.peak_rss_bytes=max(getattr(self,"peak_rss_bytes",0),rss)
        return self.peak_workspace_bytes,self.peak_rss_bytes

    def _load_completed_index(self):
        if not hasattr(self.transport,"list_directory"):
            return
        head=self.transport.branch_head()
        directory=f"{BASE}/measurement_index/run={_quote(self.run_id)}"
        try:names=self.transport.list_directory(head,directory)
        except TransportError:
            return
        for name in sorted(names):
            if not name.endswith(".jsonl"):continue
            path=directory+"/"+name
            raw=self.transport.blob_from_commit(head,path)
            rows_in_part=raw.decode("utf-8").splitlines()
            self.index_paths.append({"path":path,"rows":len(rows_in_part),"bytes":len(raw),
                "sha256":hashlib.sha256(raw).hexdigest(),
                "blob_sha":hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest(),
                "commit_sha":head,"verified_at_head":head})
            for line in rows_in_part:
                row=json.loads(line)
                key=(row["candidate_id"],row["role"],row["window"])
                if key in self.completed_windows:
                    raise TransportError("duplicate candidate-window index entry")
                self.completed_windows[key]=row
                self.completed_paths.update(row.get("partition_paths",[]))
                self.row_count+=int(row["trade_rows"])
                self.partition_count+=int(row["partition_count"])

    def add_window(self, candidate, role, window, trades_by_asset, panels, stats=None, baseline_by_asset=None, control_info=None, members=None, mode=None):
        """Persist all rows for one candidate/window; records zero windows too."""
        key=(str(candidate),str(role),str(window))
        previous=self.completed_windows.get(key)
        chunk = []
        row_count = 0
        partition_paths = []
        for sym, trades in trades_by_asset.items():
            for t in trades:
                row = _row(t, candidate, role, window, panels)
                if row["asset"] != sym:
                    raise ValueError("trade asset key disagrees with record")
                chunk.append(row)
                row_count += 1
                if len(chunk) >= self.max_rows:
                    made=self._add_chunk(candidate, role, window, chunk, panels)
                    partition_paths.extend(made if isinstance(made,list) else [made])
                    chunk = []
        if chunk:
            made=self._add_chunk(candidate, role, window, chunk, panels)
            partition_paths.extend(made if isinstance(made,list) else [made])
        current={"candidate_id":str(candidate),"role":str(role),
            "window":str(window),"trade_rows":row_count,
            "partition_count":len(partition_paths),"partition_paths":partition_paths,
            "schema_version":SCHEMA_VERSION}
        if previous is not None:
            if (int(previous["trade_rows"])!=row_count or
                previous.get("partition_paths",[])!=partition_paths or
                previous.get("schema_version")!=SCHEMA_VERSION):
                raise TransportError("resumed candidate-window output differs from committed index")
            self._resource_snapshot()
            return row_count
        else:
            self.index_rows.append(current)
            self.completed_windows[key]=current
            self.row_count += row_count
        if len(self.index_rows) >= self._index_flush_limit:
            self.flush()
            self.flush_index()
        if self.pending_bytes >= self.batch_bytes or len(self.pending) >= self.batch_parts:
            self.flush()
        self.metric_writer.add_window(candidate,role,window,trades_by_asset,panels,stats=stats,baseline_by_asset=baseline_by_asset,control_info=control_info,members=members,mode=mode)
        self._resource_snapshot()
        return row_count

    def add_control_results(self,rows):
        self.metric_writer.add_control_results(rows)

    def _add_chunk(self, candidate, role, window, rows, panels):
        payload, table = encode_rows(rows)
        if len(payload) > MAX_PART_BYTES:
            if len(rows) <= 1:
                raise TransportError("one-row Parquet partition exceeds 8,000,000 bytes")
            middle = len(rows) // 2
            left=self._add_chunk(candidate, role, window, rows[:middle], panels)
            right=self._add_chunk(candidate, role, window, rows[middle:], panels)
            return (left if isinstance(left,list) else [left]) + (right if isinstance(right,list) else [right])
        key = (self.run_id, str(candidate), str(role), str(window))
        part = self.part_counter.get(key, 0)
        self.part_counter[key] = part + 1
        path = (f"{BASE}/trades/run={_quote(self.run_id)}/role={_quote(role)}"
                f"/candidate={_quote(candidate)}/window={_quote(window)}"
                f"/part-{part:05d}.parquet")
        if len(payload) > MAX_PART_BYTES:
            raise TransportError("partition exceeds 8,000,000-byte cap")
        if path in self.completed_paths:
            head=self.transport.branch_head();remote=self.transport.blob_from_commit(head,path)
            if len(remote)!=len(payload) or hashlib.sha256(remote).digest()!=hashlib.sha256(payload).digest():
                raise TransportError("resumed partition hash differs from committed data: "+path)
            decoded=pq.read_table(pa.BufferReader(remote))
            if not decoded.schema.equals(TRADE_SCHEMA,check_metadata=False) or not decoded.equals(table):
                raise TransportError("resumed partition values/schema differ: "+path)
            return path
        recovered_commit=""
        if self.run_has_remote_data:
            head=self.transport.branch_head()
            try:remote=self.transport.blob_from_commit(head,path)
            except TransportError as exc:
                if "path resolution failed" not in str(exc):raise
                remote=None
            if remote is not None:
                if len(remote)!=len(payload) or hashlib.sha256(remote).digest()!=hashlib.sha256(payload).digest():
                    raise TransportError("orphan partition path has different content: "+path)
                decoded=pq.read_table(pa.BufferReader(remote))
                if not decoded.schema.equals(TRADE_SCHEMA,check_metadata=False) or not decoded.equals(table):
                    raise TransportError("orphan partition values/schema differ: "+path)
                recovered_commit=head
        self.pending.append(Pending(path,payload,table,str(candidate),str(role),
                                    str(window),part,recovered_commit))
        self.pending_bytes += len(payload)
        self.peak_pending_bytes = max(self.peak_pending_bytes, self.pending_bytes)
        self.peak_pending_rows = max(self.peak_pending_rows,
                                     sum(x.table.num_rows for x in self.pending))
        self.partition_count += 1
        return path

    def flush(self):
        if not self.pending:
            return
        if self.pending_bytes > MAX_PART_BYTES:
            raise TransportError("bounded commit buffer exceeds 8,000,000 bytes")
        batch = self.pending
        head = self.transport.branch_head()
        new_items=[x for x in batch if not x.recovered_commit]
        files = {x.path: x.payload for x in new_items}
        if files:
            commit,receipts=self.transport.commit_files(files,head,
                f"L0084-R1: append {len(files)} bounded trade partitions")
            self._resource_snapshot()
            by_path={r.path:r for r in receipts}
        else:
            commit=head;by_path={}
        journal = []
        for item in batch:
            item_commit=item.recovered_commit or commit
            remote = self.transport.blob_from_commit(item_commit, item.path)
            if len(remote) != len(item.payload) or hashlib.sha256(remote).digest() != hashlib.sha256(item.payload).digest():
                raise TransportError("remote trade partition byte/hash mismatch: " + item.path)
            decoded = pq.read_table(pa.BufferReader(remote))
            if not decoded.schema.equals(TRADE_SCHEMA, check_metadata=False) or not decoded.equals(item.table):
                raise TransportError("remote Parquet schema/value mismatch: " + item.path)
            receipt=by_path.get(item.path)
            if receipt is None:
                git_blob_sha=hashlib.sha1(b"blob "+str(len(item.payload)).encode()+b"\0"+item.payload).hexdigest()
                content_sha=hashlib.sha256(item.payload).hexdigest()
                size_bytes=len(item.payload)
            else:
                git_blob_sha=receipt.blob_sha;content_sha=receipt.content_sha256;size_bytes=receipt.size_bytes
            if item.recovered_commit and item.path in self.journaled_paths:
                continue
            journal.append({
                "event": "trade_partition_committed", "path": item.path,
                "candidate_id": item.candidate, "role": item.role,
                "window": item.window, "partition": item.part,
                "rows": item.table.num_rows, "schema_version": SCHEMA_VERSION,
                "bytes": size_bytes, "sha256": content_sha,
                "git_blob_sha": git_blob_sha, "commit_sha": item_commit,
                "remote_readback": "PASS", "recovered_orphan": bool(item.recovered_commit),
            })
        if journal:self._append_journal(journal)
        self.pending = []
        self.pending_bytes = 0

    def _append_journal(self, rows):
        shard=f"{BASE}/storage_journal/run={_quote(self.run_id)}/part-{self.journal_part:05d}.jsonl"
        payload=b"".join((json.dumps(r,sort_keys=True,separators=(",",":"))+"\n").encode() for r in rows)
        if len(payload)>MAX_PART_BYTES:raise TransportError("storage-journal shard exceeds byte cap")
        head=self.transport.branch_head()
        commit,receipts=self.transport.commit_files({shard:payload},head,
            f"L0084-R1: commit storage receipt shard {self.journal_part:05d}")
        self._resource_snapshot()
        if self.transport.blob_from_commit(commit,shard)!=payload:
            raise TransportError("storage journal shard readback mismatch")
        pointer={"event":"journal_shard_committed","run_id":self.run_id,
            "path":shard,"rows":len(rows),"bytes":len(payload),
            "sha256":hashlib.sha256(payload).hexdigest(),
            "git_blob_sha":receipts[0].blob_sha,"commit_sha":commit,
            "readback":"PASS"}
        index_path=f"{BASE}/storage_journal.jsonl"
        old_head=self.transport.branch_head()
        try:old=self.transport.blob_from_commit(old_head,index_path)
        except TransportError as exc:
            if "path resolution failed" not in str(exc):raise
            old=b""
        new=old+(json.dumps(pointer,sort_keys=True,separators=(",",":"))+"\n").encode()
        jcommit,jrec=self.transport.commit_files({index_path:new},old_head,
            "L0084-R1: append storage-journal shard pointer")
        self._resource_snapshot()
        if self.transport.blob_from_commit(jcommit,index_path)!=new:
            raise TransportError("storage journal pointer readback mismatch")
        self.journal_paths.append({"path":shard,"rows":len(rows),"bytes":len(payload),
            "sha256":pointer["sha256"],"blob_sha":receipts[0].blob_sha,
            "commit_sha":commit,"pointer_commit":jcommit})
        self.journal_part+=1
        for row in rows:
            if row.get("event")=="trade_partition_committed":self.journaled_paths.add(row["path"])
        return jcommit

    def flush_index(self):
        if not self.index_rows:
            return
        rows, self.index_rows = self.index_rows, []
        payload = b"".join((json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n").encode() for r in rows)
        if len(payload) > MAX_PART_BYTES:
            self.index_rows = rows + self.index_rows
            raise TransportError("index partition exceeds byte cap")
        path = f"{BASE}/measurement_index/run={_quote(self.run_id)}/part-{self.index_part:05d}.jsonl"
        self.index_part += 1
        head = self.transport.branch_head()
        commit, receipts = self.transport.commit_files({path: payload}, head,
            f"L0084-R1: append candidate-window coverage index {self.index_part:05d}")
        self._resource_snapshot()
        remote = self.transport.blob_from_commit(commit, path)
        if remote != payload:
            raise TransportError("measurement index readback mismatch")
        self.index_paths.append({"path": path, "rows": len(rows), "bytes": len(payload),
                                 "sha256": hashlib.sha256(payload).hexdigest(),
                                 "blob_sha": receipts[0].blob_sha,
                                 "commit_sha": commit})

    def close(self):
        self.flush()
        self.flush_index()
        metric_summary=self.metric_writer.close()
        self._resource_snapshot()
        return {"rows": self.row_count, "partitions": self.partition_count,
                "peak_pending_bytes": self.peak_pending_bytes,
                "peak_pending_rows": self.peak_pending_rows,
                "index_parts": list(self.index_paths),
                "journal_parts": list(self.journal_paths),
                "metrics":metric_summary,
                "peak_workspace_bytes":self.peak_workspace_bytes,
                "peak_rss_bytes":self.peak_rss_bytes,
                "memory_limit_bytes":self.memory_limit_bytes,
                "memory_limit_source":self.memory_limit_source,
                "head": self.transport.branch_head()}
