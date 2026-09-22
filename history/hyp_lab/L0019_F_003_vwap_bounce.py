# -*- coding: utf-8 -*-
"""[L0019 · F-003] ارتداد VWAP مع رصّ EMA فوقه — دخول

عقد الآلة حرفيًا:
  (low <= VWAP) AND (close > VWAP) AND (EMA(ef) > EMA(es)) AND (EMA(es) > VWAP)
  AND (volume > vol_mult × VOL_SMA(20))
السويب: ef=[8,9] × es=[20,21] × vol_mult=[1.0,1.2,1.5] ⇒ 12 تركيبة
المصدر: بحث حر — TradeZella (VWAP Bounce Setup 1) + Medium (EMA+VWAP 5m test)

VWAP من بداية اليوم UTC (وكيل موثق: بيانات شمعية لا دفتر أوامر). شراء فقط 🔒.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from L0019_indicators import vol_sma, vwap_utc

SWEEP_PARAMS = {
    "ema_fast": [8, 9],
    "ema_slow": [20, 21],
    "vol_mult": [1.0, 1.2, 1.5],
}


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    ef = params.get("ema_fast", 8)
    es = params.get("ema_slow", 21)
    vm = params.get("vol_mult", 1.0)
    c, l, v = df["close"], df["low"], df["volume"]
    vwap = vwap_utc(df)
    ema_f = c.ewm(span=ef, adjust=False).mean()
    ema_s = c.ewm(span=es, adjust=False).mean()
    sig = ((l <= vwap) & (c > vwap) & (ema_f > ema_s) & (ema_s > vwap)
           & (v > vm * vol_sma(v, 20)))
    return sig.fillna(False)


def self_test():
    rng = np.random.default_rng(42)
    n = 4000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": 100 + rng.normal(0, 1, n).cumsum(),
                       "volume": rng.uniform(1, 100, n)}, index=idx)
    df["close"] = df["open"] + rng.normal(0, 0.5, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng.normal(0, 0.3, n))
    s_lo = make_signals(df, ema_fast=9, ema_slow=21, vol_mult=1.5)
    s_hi = make_signals(df, ema_fast=8, ema_slow=20, vol_mult=1.0)
    assert s_lo.dtype == bool and len(s_lo) == n
    assert int(s_lo.sum()) <= int(s_hi.sum()), "شرط حجم أصرم يجب ألا يزيد الإشارات"
    vw = vwap_utc(df)
    assert vw.notna().sum() > 0 and np.isfinite(vw.dropna()).all()
    k = 0
    for a in SWEEP_PARAMS["ema_fast"]:
        for b in SWEEP_PARAMS["ema_slow"]:
            for m in SWEEP_PARAMS["vol_mult"]:
                make_signals(df, ema_fast=a, ema_slow=b, vol_mult=m)
                k += 1
    assert k == 12, f"الشبكة يجب أن تكون 12 لا {k}"
    print(f"[L0019·F-003] self_test OK — 12 تركيبة | إشارات: {int(s_lo.sum())} / {int(s_hi.sum())}")


if __name__ == "__main__":
    self_test()
