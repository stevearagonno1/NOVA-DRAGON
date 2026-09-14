#!/usr/bin/env python3
"""تحميل بيانات Binance الشهرية وبناء parquet موحد — وكيل التشغيل"""
import os, sys, glob
import pandas as pd

OUT_DIR = "crypto_archive"
RAW_DIR = "data_raw"
SYMBOL = "BTCUSDT"

# روابط الشهور المطلوبة (2023-09 → 2026-08)
LINKS = []
for y in range(2023, 2027):
    for m in range(1, 13):
        if (y == 2023 and m < 9) or (y == 2026 and m > 8):
            continue
        LINKS.append(f"https://data.binance.vision/data/spot/monthly/klines/{SYMBOL}/1m/{SYMBOL}-1m-{y}-{m:02d}.zip")

def download():
    os.makedirs(RAW_DIR, exist_ok=True)
    import urllib.request
    for i, url in enumerate(LINKS, 1):
        name = url.split("/")[-1]
        path = os.path.join(RAW_DIR, name)
        if os.path.exists(path) and os.path.getsize(path) > 10000:
            print(f"[{i}/{len(LINKS)}] موجود مسبقاً: {name}")
            continue
        print(f"[{i}/{len(LINKS)}] ينزل: {name}")
        try:
            urllib.request.urlretrieve(url, path)
        except Exception as e:
            print(f"  ⚠️ فشل: {e} — يتخطى")

def build():
    frames = []
    zips = sorted(glob.glob(os.path.join(RAW_DIR, "*.zip")))
    if not zips:
        print("❌ لا zips — نزّل أولاً")
        return
    for z in zips:
        try:
            df = pd.read_csv(z, compression="zip", header=None,
                             names=["open_time","open","high","low","close","volume",
                                    "close_time","qav","trades","tbb","tbq","ignore"])
            frames.append(df[["open_time","open","high","low","close","volume"]])
        except Exception as e:
            print(f"⚠️ تالف {z}: {e}")
    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    all_df["open_time"] = pd.to_datetime(all_df["open_time"], unit="us", utc=True)
    all_df = all_df.set_index("open_time")
    for c in ["open","high","low","close","volume"]:
        all_df[c] = pd.to_numeric(all_df[c], errors="coerce")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{SYMBOL}_1m.parquet")
    all_df.to_parquet(out)
    print(f"✅ {out}: {len(all_df):,} شمعة ({all_df.index.min()} → {all_df.index.max()})")

if __name__ == "__main__":
    if "--build-only" not in sys.argv:
        download()
    build()
