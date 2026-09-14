#!/usr/bin/env python3
"""Rebuild crypto_archive/BTCUSDT_1m.parquet from data_raw zips.

Same logic as nova_v8/fetch_archive.py build(), with one technical fix:
Binance monthly klines use MILLISECOND open_time up to 2024-12 and
MICROSECOND from 2025-01 onward. The unit is detected per row-block
(magnitude of the first timestamp in each file) instead of assuming µs.
Engine code under nova_v8/ is NOT touched — this only regenerates the
input data artifact.
"""
import glob
import os

import pandas as pd

RAW_DIR = "/home/user/work/data_raw"
OUT_DIR = "/home/user/work/crypto_archive"
SYMBOL = "BTCUSDT"

frames = []
zips = sorted(glob.glob(os.path.join(RAW_DIR, "*.zip")))
assert len(zips) == 36, f"expected 36 zips, found {len(zips)}"
for z in zips:
    df = pd.read_csv(
        z, compression="zip", header=None,
        names=["open_time", "open", "high", "low", "close", "volume",
               "close_time", "qav", "trades", "tbb", "tbq", "ignore"])
    df = df[["open_time", "open", "high", "low", "close", "volume"]]
    first = int(df["open_time"].iloc[0])
    unit = "ms" if first < 1e13 else "us"
    df["open_time"] = pd.to_datetime(df["open_time"], unit=unit, utc=True)
    frames.append(df)
    print(f"{os.path.basename(z)}: {len(df):,} rows, unit={unit}, "
          f"{df['open_time'].iloc[0]} → {df['open_time'].iloc[-1]}", flush=True)

all_df = pd.concat(frames, ignore_index=True)
all_df = all_df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
all_df = all_df.set_index("open_time")
for c in ["open", "high", "low", "close", "volume"]:
    all_df[c] = pd.to_numeric(all_df[c], errors="coerce")
assert all_df.index.min() >= pd.Timestamp("2023-09-01", tz="UTC"), all_df.index.min()
assert all_df.index.max() <= pd.Timestamp("2026-09-01", tz="UTC"), all_df.index.max()
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, f"{SYMBOL}_1m.parquet")
all_df.to_parquet(out)
print(f"✅ {out}: {len(all_df):,} candles ({all_df.index.min()} → {all_df.index.max()})")
# sanity: no missing minutes inside the range
expected = int((all_df.index.max() - all_df.index.min()).total_seconds() // 60) + 1
print(f"expected {expected:,} minutes in span → got {len(all_df):,} "
      f"(missing {expected - len(all_df):,})")
