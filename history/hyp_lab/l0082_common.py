#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0082 — مكتبة مشتركة: تعريفات القسم 1 الحرفية بلا إحالة خارجية.

كل ثابت وكل تعريف هنا منقول حرفيًا من ورقة TASK-L0082-EXECUTION.
ممنوع تغيير أي تعريف (القسم 6). البذرة 82 في كل مكان. UTC حصرًا. 4 خانات عشرية.
"""
from __future__ import annotations

import io
import time
import zipfile
import pathlib
import urllib.request
import urllib.error

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- الثوابت المقفلة
SEED = 82
ROUND = 4

# الكون (12) + الاحتياط المرتب
ASSETS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT", "ATOMUSDT",
]
RESERVE = ["NEARUSDT", "FILUSDT", "XLMUSDT", "UNIUSDT", "ETCUSDT", "TRXUSDT"]

# الفترات (UTC)
TRAIN = ("2021-01-01", "2025-03-31")
HOLDOUT = ("2025-04-01", "2026-06-30")
FORWARD = ("2026-07-01", "2026-09-27")
DATA_START = "2021-01-01"
DATA_END = "2026-09-27"

PURGE = 18
EMBARGO = 18

# الرسوم (القسم 1P / ملحق 9)
FEE_MAKER_BPS = 2.0   # 0.0200%
FEE_TAKER_BPS = 5.0   # 0.0500%
NOTIONAL = 10_000.0   # USDT

# الهندسة المرجعية (1.4)
REF_R_MULT = 1.0      # R = 1.0 * ATR
REF_HORIZON = 6
REF_RR = 1.0

ROOT = pathlib.Path(__file__).resolve().parents[2]  # /home/user/repo
DATA_DIR = ROOT / "history" / "data" / "um"
OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0082"
OUT.mkdir(parents=True, exist_ok=True)

BASE_VISION = "https://data.binance.vision/data/futures/um"

KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore",
]


# ---------------------------------------------------------------- أدوات التنزيل
def _http_get(url: str, timeout: int = 60) -> bytes | None:
    """يعيد المحتوى أو None عند 404. يرمي عند أخطاء أخرى بعد المحاولات."""
    req = urllib.request.Request(url, headers={"User-Agent": "l0082/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_zip_csv(url: str, retries: int = 3, sleep: float = 5.0) -> bytes | None:
    """تنزيل zip من binance.vision وإخراج بايتات ملف الـcsv بداخله.
    يعيد None عند 404 (غير موجود). ثلاث محاولات بفاصل 5 ثوانٍ للأخطاء العابرة (ملحق 8)."""
    last = None
    for attempt in range(retries):
        try:
            raw = _http_get(url)
            if raw is None:
                return None
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                name = z.namelist()[0]
                return z.read(name)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(sleep)
    raise RuntimeError(f"فشل التنزيل بعد {retries} محاولات: {url} :: {last}")


def _first_row_is_header(text_bytes: bytes) -> bool:
    """القاعدة المتحقق منها (2.1): افحص الصف الأول — إن لم يكن open_time رقمًا فهو ترويسة."""
    first_line = text_bytes.split(b"\n", 1)[0].strip()
    if not first_line:
        return False
    first_field = first_line.split(b",", 1)[0].strip().strip(b'"')
    try:
        int(first_field)
        return False
    except ValueError:
        return True


def parse_kline_csv(csv_bytes: bytes) -> pd.DataFrame:
    header = 0 if _first_row_is_header(csv_bytes) else None
    df = pd.read_csv(io.BytesIO(csv_bytes), header=header, names=KLINE_COLS)
    for c in ["open", "high", "low", "close", "volume", "quote_volume",
              "taker_buy_volume", "taker_buy_quote_volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce").astype("int64")
    return df


# ---------------------------------------------------------------- المؤشرات (1.2, 1.5)
def wilder_atr(high, low, close, n=14):
    high = np.asarray(high, float); low = np.asarray(low, float); close = np.asarray(close, float)
    m = len(close)
    tr = np.full(m, np.nan)
    tr[0] = high[0] - low[0]
    for i in range(1, m):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    atr = np.full(m, np.nan)
    if m >= n:
        atr[n-1] = np.mean(tr[:n])
        for i in range(n, m):
            atr[i] = (atr[i-1] * (n - 1) + tr[i]) / n
    return atr, tr


def ema(series, n):
    s = np.asarray(series, float)
    m = len(s)
    out = np.full(m, np.nan)
    if m < n:
        return out
    k = 2.0 / (n + 1.0)
    out[n-1] = np.mean(s[:n])
    for i in range(n, m):
        out[i] = s[i] * k + out[i-1] * (1 - k)
    return out


def sma(series, n):
    return pd.Series(series, dtype=float).rolling(n, min_periods=n).mean().to_numpy()


def wilder_adx(high, low, close, n=14):
    high = np.asarray(high, float); low = np.asarray(low, float); close = np.asarray(close, float)
    m = len(close)
    tr = np.zeros(m); pdm = np.zeros(m); ndm = np.zeros(m)
    for i in range(1, m):
        up = high[i] - high[i-1]
        dn = low[i-1] - low[i]
        pdm[i] = up if (up > dn and up > 0) else 0.0
        ndm[i] = dn if (dn > up and dn > 0) else 0.0
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    str_ = np.full(m, np.nan); spdm = np.full(m, np.nan); sndm = np.full(m, np.nan)
    if m > n:
        str_[n] = tr[1:n+1].sum()
        spdm[n] = pdm[1:n+1].sum()
        sndm[n] = ndm[1:n+1].sum()
        for i in range(n+1, m):
            str_[i] = str_[i-1] - str_[i-1]/n + tr[i]
            spdm[i] = spdm[i-1] - spdm[i-1]/n + pdm[i]
            sndm[i] = sndm[i-1] - sndm[i-1]/n + ndm[i]
    pdi = 100.0 * spdm / str_
    ndi = 100.0 * sndm / str_
    dx = 100.0 * np.abs(pdi - ndi) / (pdi + ndi)
    adx = np.full(m, np.nan)
    # أول ADX = متوسط أول n قيمة DX متاحة، ثم تنعيم Wilder
    first = n  # index حيث تبدأ DX بالتوفر تقريبيًا
    valid_idx = np.where(~np.isnan(dx))[0]
    if len(valid_idx) >= n:
        start = valid_idx[0]
        adx[start + n - 1] = np.nanmean(dx[start:start + n])
        for i in range(start + n, m):
            adx[i] = (adx[i-1] * (n - 1) + dx[i]) / n
    return adx, pdi, ndi


def macd(close, fast=12, slow=26, signal=9):
    ef = ema(close, fast); es = ema(close, slow)
    line = ef - es
    sig = ema(line[~np.isnan(line)], signal)
    out_sig = np.full(len(close), np.nan)
    valid = np.where(~np.isnan(line))[0]
    if len(valid) >= signal:
        out_sig[valid[0]:valid[0]+len(sig)] = sig
    return line, out_sig


def obv(close, volume):
    close = np.asarray(close, float); volume = np.asarray(volume, float)
    m = len(close)
    out = np.zeros(m)
    for i in range(1, m):
        if close[i] > close[i-1]:
            out[i] = out[i-1] + volume[i]
        elif close[i] < close[i-1]:
            out[i] = out[i-1] - volume[i]
        else:
            out[i] = out[i-1]
    return out
