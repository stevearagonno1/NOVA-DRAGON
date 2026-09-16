"""Module — data ingestion + feature-matrix cache for research.

Loads one symbol's 1m OHLCV from Parquet (or its alias), computes the causal
indicator matrix once, maps the regime (higher TF), and precomputes entry
events. The whole result is cached on disk so repeated experiments are fast and
byte-identical. Memory stays bounded by processing one symbol at a time.
"""
from __future__ import annotations

import gc
import os
import logging
from dataclasses import dataclass

import pandas as pd
import pyarrow.parquet as pq

from . import config as C
from . import indicators as ind
from . import regime as regime_mod
from . import triggers as trig_mod

log = logging.getLogger("nova.feeds")

_TIME_COLS = ("open_time", "timestamp", "time", "date", "openTime", "time_open")


def _read_parquet(path: str) -> pd.DataFrame:
    pf = pq.ParquetFile(path, memory_map=True)
    names = pf.schema_arrow.names
    lower = {n.lower(): n for n in names}
    tkey = next((lower[c] for c in _TIME_COLS if c in lower), None)
    wanted = ["open", "high", "low", "close", "volume"]
    cols = ([tkey] if tkey else []) + [lower[w] for w in wanted if w in lower]
    table = pf.read(columns=cols or None)
    df = table.to_pandas(split_blocks=True, self_destruct=True)
    del table
    return df


def _standardize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    tcol = next((c for c in _TIME_COLS if c in df.columns), None)
    if tcol is not None:
        t = pd.to_numeric(df[tcol], errors="coerce")
        v = int(t.dropna().iloc[0])
        unit = "ns" if v > 1e16 else "us" if v > 1e13 else "ms" if v > 1e10 else "s"
        df.index = pd.to_datetime(t, unit=unit, utc=True)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("no usable timestamp column/index in parquet file")
    out = df[["open", "high", "low", "close", "volume"]].astype(float).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out


def _source_path(symbol: str) -> str | None:
    for cand in (symbol, *C.SYMBOL_ALIASES.get(symbol, ())):
        p = C.ARCHIVE_DIR / f"{cand}_1m.parquet"
        if p.exists():
            return str(p)
    return None


def make_matrix_parquet(df1m: pd.DataFrame) -> pd.DataFrame:
    """Build & return the causal indicator matrix from standardized 1m OHLCV."""
    return ind.compute_matrix(df1m)


@dataclass
class Matrix:
    symbol: str
    df: pd.DataFrame

    def __post_init__(self):
        # regime (fixed per bar via higher TF)
        self.regime = regime_mod.map_regime_to_1m(self.df, C.REGIME_TF)
        # entry events (side/trigger) computed on matrix
        self.side, self.trig = trig_mod.compute_entry_events(self.df)
        cols = self.df.columns
        self.arr = {c: self.df[c].to_numpy() for c in cols}
        self.n = len(self.df)

    def bar(self, i: int) -> dict:
        out = {c: self.arr[c][i] for c in self.arr}
        return out


def load_matrix(symbol: str) -> Matrix | None:
    """Load + (re)compute a symbol's research matrix, caching to disk."""
    src = _source_path(symbol)
    if src is None:
        log.warning("archive missing for %s", symbol)
        return None
    cache = C.ARCHIVE_DIR / f"{symbol}__matrix_v{C.MATRIX_CACHE_VER}.parquet"
    sliced = bool(C.START_DATE or C.END_DATE)
    base = None
    if not sliced and cache.exists() and os.path.getmtime(cache) >= os.path.getmtime(src):
        try:
            base = pd.read_parquet(cache)
            log.info("%s matrix cache hit (%d bars)", symbol, len(base))
        except Exception as exc:
            log.warning("cache read failed %s: %s", symbol, exc)
            base = None
    if base is None:
        raw = _standardize(_read_parquet(src))
        if C.START_DATE:
            raw = raw[raw.index >= pd.Timestamp(C.START_DATE, tz="UTC")]
        if C.END_DATE:
            raw = raw[raw.index <= pd.Timestamp(C.END_DATE, tz="UTC")]
        if len(raw) < 400:
            log.warning("%s: too few bars after slice (%d)", symbol, len(raw))
            return None
        base = make_matrix_parquet(raw)
        del raw
        gc.collect()
        if not sliced:
            try:
                base.to_parquet(cache)
            except Exception as exc:
                log.warning("matrix cache write failed: %s", exc)
    mat = Matrix(symbol, base)
    log.info("%s ready: %d bars", symbol, mat.n)
    return mat


def load_all(matrices_slice=None):
    """Load matrices for the symbol set, honouring one-symbol-at-a-time by the
    caller (this returns a dict which the engine may stream)."""
    symbols = matrices_slice or C.SYMBOLS
    out = {}
    for s in symbols:
        m = load_matrix(s)
        if m is not None:
            out[s] = m
        gc.collect()
    return out
