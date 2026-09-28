"""Fetch 4H OHLCV for P4 cross-sectional OOS assets (NEVER used in L0072-L0080) from binance.us
(binance.com is geo-blocked 451). Cache to ~/l007x_4h/newassets/ as parquet (survives resets).
Fetch from 2024-01-01 to give indicator warmup before the 2024-09-04 evaluation window."""
import os, sys, time, json, datetime as dt, urllib.request
import numpy as np, pandas as pd

NEW = ["ADA", "XRP", "DOGE", "AVAX", "DOT", "LTC", "BCH", "TRX"]  # none used in L0072-L0080
CACHE = os.path.expanduser("~/l007x_4h/newassets")
START = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
END = dt.datetime(2026, 8, 31, 23, tzinfo=dt.timezone.utc)


def fetch(sym):
    start_ms = int(START.timestamp() * 1000); end_ms = int(END.timestamp() * 1000)
    out = []; cur = start_ms
    while cur < end_ms:
        u = (f"https://api.binance.us/api/v3/klines?symbol={sym}USDT&interval=4h"
             f"&startTime={cur}&endTime={end_ms}&limit=1000")
        d = json.load(urllib.request.urlopen(u, timeout=20))
        if not d:
            break
        out += d; cur = d[-1][0] + 1
        if len(d) < 1000:
            break
        time.sleep(0.1)
    rows = [(dt.datetime.fromtimestamp(k[0] / 1000, dt.timezone.utc), float(k[1]), float(k[2]),
             float(k[3]), float(k[4]), float(k[5])) for k in out]
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"]).set_index("time")
    df = df[~df.index.duplicated()].sort_index()
    return df


def main():
    os.makedirs(CACHE, exist_ok=True)
    manifest = {}
    for s in NEW:
        p = f"{CACHE}/{s}USDT_4h.parquet"
        if os.path.exists(p):
            df = pd.read_parquet(p)
        else:
            df = fetch(s)
            df.to_parquet(p)
        manifest[s] = [str(df.index.min()), str(df.index.max()), len(df)]
        print(f"{s}: {len(df)} bars {df.index.min()} -> {df.index.max()}")
    json.dump(manifest, open(f"{CACHE}/manifest.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
