#!/usr/bin/env python3
"""DEMO: backtest NOVA_V8 adaptive_trend with data STREAMED over HTTP into RAM.

Zero data bytes touch the disk: HTTP response -> io.BytesIO -> pyarrow -> pandas.
All engine modules (nova_v8.*) are used UNMODIFIED; only feeds.load_matrix's
file-read is replaced by the in-memory stream (same slice + matrix logic).

Validation target (documented from the disk-based run):
  combo 3.0/0.5/288/6/0/0/0 on train 2023-09→2024-12  =>  net=-98.59031619937323, trades=68
"""
import io, os, sys, time, urllib.request

# ---- 1) combo env BEFORE importing engine (config reads env at import) ----
os.environ.update({
    "NOVA_AT_TRAIL": "3.0", "NOVA_AT_STOP": "0.5", "NOVA_AT_PB": "288",
    "NOVA_AT_TRIG": "6", "NOVA_AT_V3A": "0", "NOVA_AT_V3B": "0", "NOVA_AT_V3C": "0",
})
sys.path.insert(0, "/home/user/work")

import pandas as pd
import pyarrow.parquet as pq

# ---- 2) stream the parquet over HTTP into RAM (stand-in for raw.githubusercontent.com) ----
URL = "http://127.0.0.1:8123/BTCUSDT_1m.parquet"
t0 = time.time()
resp = urllib.request.urlopen(URL)
buf = io.BytesIO(resp.read())          # 86MB live in RAM only
t_stream = time.time() - t0
print(f"[1/5] streamed {buf.getbuffer().nbytes/1e6:.1f} MB over HTTP in {t_stream:.1f}s — 0 bytes on disk")

# ---- 3) parse parquet from the RAM buffer (footer-first, no disk) ----
t1 = time.time()
df = pq.ParquetFile(buf).read().to_pandas()
print(f"[2/5] parsed parquet from RAM in {time.time()-t1:.1f}s — {len(df):,} rows, index: {df.index.min()} → {df.index.max()}")

# ---- 4) engine's own standardize + window slice + indicator matrix (unmodified funcs) ----
from nova_v8 import config as C
from nova_v8 import feeds
from nova_v8.sweep_engine import _month_bounds
C.START_DATE, _ = _month_bounds("2023-09")
_, C.END_DATE = _month_bounds("2024-12")
t2 = time.time()
raw = feeds._standardize(df)
del df
raw = raw[raw.index >= pd.Timestamp(C.START_DATE, tz="UTC")]
raw = raw[raw.index <= pd.Timestamp(C.END_DATE, tz="UTC")]
base = feeds.make_matrix_parquet(raw)   # ~40 causal indicators, in RAM
del raw
mat = feeds.Matrix("BTCUSDT", base)     # regime + entry events (engine dataclass)
print(f"[3/5] sliced {C.START_DATE}→{C.END_DATE} + built matrix in {time.time()-t2:.1f}s — {mat.n:,} bars")

# ---- 5) replay the strategy (engine, unmodified) ----
from nova_v8 import adaptive_trend
t3 = time.time()
recs = adaptive_trend.replay_adaptive_trend(mat)
net = sum(r.get("pnl_usd", 0.0) for r in recs)
wins = sum(1 for r in recs if r.get("pnl_usd", 0) > 0)
print(f"[4/5] replayed {mat.n:,} bars in {time.time()-t3:.1f}s")
print(f"[5/5] RESULT: net={net!r} trades={len(recs)} win_pct={100*wins/len(recs) if recs else 0.0!r}")

ok = len(recs) == 68 and abs(net - (-98.59031619937323)) < 1e-9
print("MATCH vs documented disk-based run:", "✅ EXACT" if ok else "❌ MISMATCH")
print(f"TOTAL wall time: {time.time()-t0:.1f}s | data written to disk: 0 MB")
