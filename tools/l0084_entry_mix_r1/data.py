#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — data acquisition and integrity (one asset at a time).

Source: https://data.binance.vision/data/futures/um/{monthly,daily}/klines/
        {SYM}/4h/{SYM}-4h-{YYYY-MM}.zip  or  {SYM}-4h-{YYYY-MM-DD}.zip
12 fixed assets, 4h UTC 2021-01-01 .. 2026-09-27.  No other endpoints.

Pipeline per asset: download monthly zips -> detect header and ms/us
magnitude -> validate OHLCV/timestamps -> union with daily files for the
partial month -> dedupe -> gap analysis -> contiguous segments -> parquet
(raw zips deleted after conversion, never kept beside the result).
Gap > 24h, unrepaired corruption or asset absence => BLOCKED (no universe
shrink).  Missing monthly days are repaired from daily files, max 3 retries.
"""
from __future__ import annotations

import io
import os
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

ASSETS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
          "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT", "ATOMUSDT"]
START = datetime(2021, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 27, 23, 59, 59, tzinfo=timezone.utc)
BASE = "https://data.binance.vision/data/futures/um"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume",
        "ignore"]


class Blocked(Exception):
    """Critical data defect: stop, keep evidence, do not shrink the universe."""


def _fetch(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": "l0084-audit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _parse_zip(raw, name):
    z = zipfile.ZipFile(io.BytesIO(raw))
    member = z.namelist()[0]
    text = z.read(member).decode("utf-8")
    first = text.split("\n", 1)[0].strip()
    has_header = not first.split(",")[0].strip().lstrip("-").isdigit()
    df = pd.read_csv(io.StringIO(text), header=0 if has_header else None)
    df.columns = COLS if has_header else COLS[:df.shape[1]]
    # magnitude: ms (13 digits) vs us (16 digits)
    mag = int(np.log10(float(df["open_time"].iloc[0]))) + 1
    if mag >= 16:
        ts = pd.to_datetime(df["open_time"], unit="us", utc=True)
    elif mag == 13:
        ts = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    else:
        raise Blocked(f"{name}: unknown timestamp magnitude {mag}")
    df.index = ts
    return df[["open", "high", "low", "close", "volume",
               "taker_buy_volume"]].astype("float64")


def repair_gaps(df, sym, raw_dir, log=print):
    """Repair missing days from daily files (max 3 retries per file).

    A missing tail/segment in a monthly file is repaired day-by-day.  Any
    remaining gap larger than 24h is a critical defect => BLOCKED.
    """
    step = pd.Timedelta(hours=4)
    for _round in range(3):
        dt_sec = df.index.to_series().diff().dt.total_seconds().to_numpy()
        bad = np.nonzero((dt_sec > step.total_seconds())
                         & np.isfinite(dt_sec))[0]
        if bad.size == 0:
            break
        added = 0
        for k in bad:
            t0 = df.index[k - 1]
            t1 = df.index[k]
            day = t0.floor("D")
            while day < t1:
                tag = day.strftime("%Y-%m-%d")
                url = f"{BASE}/daily/klines/{sym}/4h/{sym}-4h-{tag}.zip"
                zpath = os.path.join(raw_dir, f"{sym}-4h-{tag}.zip")
                got = None
                for attempt in range(3):
                    try:
                        raw = _fetch(url)
                        open(zpath, "wb").write(raw)
                        got = _parse_zip(raw, tag)
                        break
                    except Exception as e:                # noqa: BLE001
                        if attempt == 2:
                            log(f"  {sym}: daily repair {tag} failed 3x: {e!r}")
                if got is not None:
                    df = pd.concat([df, got])
                    added += 1
                day += pd.Timedelta(days=1)
        df = df[~df.index.duplicated(keep="first")].sort_index()
        if added == 0:
            break
    dt_sec = df.index.to_series().diff().dt.total_seconds().to_numpy()
    bad = np.nonzero((dt_sec > 24 * 3600) & np.isfinite(dt_sec))[0]
    if bad.size:
        k = int(bad[0])
        raise Blocked(f"{sym}: unrepaired gap "
                      f"{dt_sec[k] / 3600:.1f}h at {df.index[k]}")
    return df


def download_asset(sym, work, log=print):
    raw_dir = os.path.join(work, "raw_zip")
    os.makedirs(raw_dir, exist_ok=True)
    parts = []
    months = []
    y, m = 2021, 1
    while (y, m) <= (2026, 9):
        months.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    for (y, m) in months:
        tag = f"{y:04d}-{m:02d}"
        url = f"{BASE}/monthly/klines/{sym}/4h/{sym}-4h-{tag}.zip"
        zpath = os.path.join(raw_dir, f"{sym}-4h-{tag}.zip")
        ok = False
        if os.path.exists(zpath):
            try:
                parts.append(_parse_zip(open(zpath, "rb").read(), tag))
                ok = True
            except Exception:
                os.remove(zpath)
        for attempt in range(3):
            if ok:
                break
            try:
                raw = _fetch(url)
                open(zpath, "wb").write(raw)
                parts.append(_parse_zip(raw, tag))
                ok = True
            except Exception as e:                       # noqa: BLE001
                if attempt == 2:
                    log(f"  {sym}: monthly {tag} failed 3x: {e!r} "
                        f"- daily repair will be attempted")
        if not ok:
            log(f"  {sym}: monthly {tag} unavailable - will use daily files")
    # partial month 2026-09: monthly may be absent -> daily files
    have_sep = any(getattr(p.index, "min", lambda: None)() is not None
                   and len(p) and p.index.min().strftime("%Y-%m") == "2026-09"
                   for p in parts[-1:])
    if not have_sep:
        log(f"  {sym}: fetching daily files for 2026-09-01..27")
        for d in range(1, 28):
            tag = f"2026-09-{d:02d}"
            url = f"{BASE}/daily/klines/{sym}/4h/{sym}-4h-{tag}.zip"
            zpath = os.path.join(raw_dir, f"{sym}-4h-{tag}.zip")
            got = False
            for attempt in range(3):
                try:
                    raw = _fetch(url)
                    open(zpath, "wb").write(raw)
                    parts.append(_parse_zip(raw, tag))
                    got = True
                    break
                except Exception as e:                   # noqa: BLE001
                    if attempt == 2:
                        log(f"  {sym}: daily {tag} failed 3x: {e!r}")
            if not got:
                continue
    df = pd.concat(parts)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df = df[(df.index >= START) & (df.index <= END)]
    if len(df) == 0:
        raise Blocked(f"{sym}: empty after concat")
    df = repair_gaps(df, sym, raw_dir, log)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    # OHLCV integrity
    bad = ((df[["open", "high", "low", "close"]] <= 0).any(axis=1)
           | (df["high"] < df["low"]) | (df["volume"] < 0)
           | (df["taker_buy_volume"] < 0)
           | (df["taker_buy_volume"] > df["volume"]))
    if bad.any():
        raise Blocked(f"{sym}: {int(bad.sum())} impossible OHLCV rows")
    # cadence / contiguous segments
    dt_sec = df.index.to_series().diff().dt.total_seconds().to_numpy()
    step = 4 * 3600
    off = np.nonzero((dt_sec != step) & np.isfinite(dt_sec))[0]
    gaps = []
    for k in off:
        gap_h = dt_sec[k] / 3600.0
        gaps.append((df.index[k - 1], df.index[k], gap_h))
        if gap_h > 24.0:
            raise Blocked(f"{sym}: unrepaired gap {gap_h:.1f}h at {df.index[k]}")
    seg = np.zeros(len(df), dtype=np.int32)
    if off.size:
        seg[off] = 1
    seg = np.cumsum(seg)          # segment id per bar (0-based)
    for f in os.listdir(raw_dir):
        if f.startswith(sym + "-"):
            os.remove(os.path.join(raw_dir, f))          # raw deleted post-conversion
    out = os.path.join(work, f"{sym}_4h.parquet")
    df.rename_axis("dt").reset_index().assign(seg=seg).to_parquet(out,
                                                                  index=False)
    log(f"  {sym}: {len(df)} bars, segments={int(seg[-1]) + 1}, "
        f"gaps={len(gaps)}, span {df.index[0]} .. {df.index[-1]}")
    return {
        "asset": sym, "start": df.index[0].isoformat(),
        "end": df.index[-1].isoformat(), "n_bars": int(len(df)),
        "duplicates": 0, "segments": int(seg[-1]) + 1,
        "gap_count": len(gaps),
        "max_gap_hours": max([g[2] for g in gaps], default=0.0),
        "action": "parquet-converted, raw zips deleted",
    }


def load_asset(work, sym):
    df = pd.read_parquet(os.path.join(work, f"{sym}_4h.parquet"))
    return df
