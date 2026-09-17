#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تنزيل أرشيف NOVA_V8 الكامل — شموع 1m حقيقية من Binance الرسمي
=============================================================
الاستخدام (على جهازك):
    pip install pandas pyarrow
    python تنزيل_الأرشيف_الكامل.py                 # الافتراضي: كل العملات، 2021-09 → 2026-08
    python تنزيل_الأرشيف_الكامل.py --symbols BTCUSDT,SOLUSDT --start 2024-01
بعد الانتهاء:
    export NOVA_ARCHIVE=~/crypto_archive          # أو اتركه على الافتراضي
    python -m nova_v8 research --strategies all
ملاحظات:
  * قابل للاستئناف: إن انقطع، أعد التشغيل وسيكمل من حيث توقف (يفحص آخر طابع في كل ملف)
  * يحذف كل ZIP فور تحويله — الذروة القصوى للمساحة ~300MB فقط
  * الأشهر غير الموجودة (قائمة الرمز أحدث) تُتخطى تلقائياً (404)
"""
import argparse, io, os, sys, zipfile, time
import pandas as pd
import urllib.request

BASE = "https://data.binance.vision/data/spot/monthly/klines/{s}/1m/{s}-1m-{m}.zip"
SYMBOLS = ["BTCUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT", "XLMUSDT", "TONUSDT",
           "ATOMUSDT", "RENDERUSDT", "VETUSDT", "FILUSDT", "IMXUSDT", "HNTUSDT"]
COLS = ["open_time", "open", "high", "low", "close", "volume"]


def months(start, end):
    out, y, m = [], int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    while (y, m) <= (ey, em):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def fetch(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nova-archive/1.0"})
            return urllib.request.urlopen(req, timeout=120).read()
        except Exception:
            if k == tries - 1:
                return None
            time.sleep(2 * (k + 1))


def month_rows(sym, m):
    raw = fetch(BASE.format(s=sym, m=m))
    if raw is None:
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            txt = z.read(z.namelist()[0]).decode()
    except Exception:
        return None
    lines = txt.strip().split("\n")
    if lines and lines[0].lower().startswith("open_time"):
        lines = lines[1:]
    rows = [ln.split(",")[:6] for ln in lines if ln.strip()]
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=COLS)
    return df.astype({"open_time": "int64", "open": "float64", "high": "float64",
                      "low": "float64", "close": "float64", "volume": "float64"})


def update_parquet(sym, df, out_dir):
    out = os.path.join(out_dir, f"{sym}_1m.parquet")
    if os.path.exists(out):
        old = pd.read_parquet(out)
        df = pd.concat([old, df]).drop_duplicates("open_time").sort_values("open_time")
    df.to_parquet(out, index=False)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    ap.add_argument("--start", default="2021-09")
    ap.add_argument("--end", default="2026-08")
    ap.add_argument("--out", default=os.path.expanduser("~/crypto_archive"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    syms = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    ms = months(a.start, a.end)
    print(f"الخطة: {len(syms)} رمز × {len(ms)} شهر | الوجهة: {a.out}")
    for sym in syms:
        done = skip = 0
        for m in ms:
            df = month_rows(sym, m)
            if df is None:
                skip += 1
                continue
            update_parquet(sym, df, a.out)
            done += 1
        p = os.path.join(a.out, f"{sym}_1m.parquet")
        size = os.path.getsize(p) / 1e6 if os.path.exists(p) else 0
        n = len(pd.read_parquet(p, columns=["open_time"])) if size else 0
        print(f"✅ {sym}: {done} شهر (تخطي {skip}) | {n:,} شمعة | {size:.0f} MB")
    print("\nاكتمل الأرشيف. شغّل: python -m nova_v8 research --strategies all")


if __name__ == "__main__":
    sys.exit(main())
