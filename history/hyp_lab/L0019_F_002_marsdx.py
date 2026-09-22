# -*- coding: utf-8 -*-
"""[L0019 · F-002] تفوق RSI2 على ADX2 مع فلتر متوسطات (MARSdx) — دخول

عقد الآلة حرفيًا من `history/hypotheses/فرضيات_الباحث_النهائي.txt`:
  (close > SMA(sma)) AND (close > EMA(ema_fast)) AND (RSI(osc_p) > ADX(osc_p))
السويب: sma=[20,50,100] × ema_fast=[5,7,9] × osc_p=[2,7,14] ⇒ 27 تركيبة
المصدر: بحث حر — Reddit r/algotrading (Bitcoin Strategy That Outperformed Buy&Hold / MARSdx)

شراء فقط 🔒. الإشارة عند إغلاق الشمعة (التعبئة على الافتتاح التالية — عقد common.simulate).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from L0019_indicators import adx, rsi

SWEEP_PARAMS = {
    "sma": [20, 50, 100],
    "ema_fast": [5, 7, 9],
    "osc_p": [2, 7, 14],
}


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    sma_n = params.get("sma", 50)
    ema_n = params.get("ema_fast", 7)
    osc_n = params.get("osc_p", 2)
    c = df["close"]
    sig = ((c > c.rolling(sma_n, min_periods=sma_n).mean())
           & (c > c.ewm(span=ema_n, adjust=False).mean())
           & (rsi(c, osc_n) > adx(df, osc_n)))
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
    s_lo = make_signals(df, sma=100, ema_fast=9, osc_p=2)
    s_hi = make_signals(df, sma=20, ema_fast=5, osc_p=2)
    assert s_lo.dtype == bool and len(s_lo) == n
    assert int(s_lo.sum()) <= int(s_hi.sum()), "فلتر أضيق يجب ألا يزيد الإشارات"
    k = 0
    for a in SWEEP_PARAMS["sma"]:
        for b in SWEEP_PARAMS["ema_fast"]:
            for o in SWEEP_PARAMS["osc_p"]:
                make_signals(df, sma=a, ema_fast=b, osc_p=o)
                k += 1
    assert k == 27, f"الشبكة يجب أن تكون 27 لا {k}"
    print(f"[L0019·F-002] self_test OK — 27 تركيبة | إشارات: {int(s_lo.sum())} / {int(s_hi.sum())}")


if __name__ == "__main__":
    self_test()
