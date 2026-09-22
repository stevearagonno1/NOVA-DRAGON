# -*- coding: utf-8 -*-
"""[L0019 · F-007] إطلاق TTM Squeeze مع انعكاس الزخم — دخول

عقد الآلة حرفيًا:
  (BB(length,bb_mult) داخل Keltner(length,kc_mult) لآخر 6 شمعات على الأقل)
  AND (BB_upper الحالي > Keltner_upper الحالي)   ← لحظة التحرر
  AND (MOM(mom_p) يعبر فوق 0)
  AND (close > BB_upper(length,bb_mult))
  AND (volume > 1.5 × VOL_SMA(20))
السويب: length=[12,20] × bb_mult=[2.0,2.5] × kc_mult=[1.0,1.5] × mom_p=[8,12] ⇒ 16 تركيبة
المصدر: بحث حر — JournalPlus (Momentum Squeeze) + LuxAlgo (TTM Squeeze) + HotPennyStocks

الضغط "داخل" = علوي بولنجر تحت علوي كيلتنر وسفلي بولنجر فوق سفلي كيلتنر.
شراء فقط 🔒.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from L0019_indicators import bb, keltner, vol_sma

SWEEP_PARAMS = {
    "length": [12, 20],
    "bb_mult": [2.0, 2.5],
    "kc_mult": [1.0, 1.5],
    "mom_p": [8, 12],
}
INSIDE_BARS = 6
VOL_CONFIRM = 1.5


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    ln = params.get("length", 20)
    bm = params.get("bb_mult", 2.0)
    km = params.get("kc_mult", 1.5)
    mp = params.get("mom_p", 12)
    c, v = df["close"], df["volume"]
    atr_s = _atr(df, ln)
    _, bb_up, bb_lo, _ = bb(c, ln, bm)
    kc_up, kc_lo = keltner(df, ln, km, atr_s)
    inside = (bb_up < kc_up) & (bb_lo > kc_lo)
    in_squeeze = inside.rolling(INSIDE_BARS, min_periods=INSIDE_BARS).sum() == INSIDE_BARS
    mom = c - c.shift(mp)
    cross_up = (mom > 0) & (mom.shift(1) <= 0)
    sig = (in_squeeze.shift(1, fill_value=False)      # الضغط كان قائمًا قبل شمعة التحرر
           & (bb_up > kc_up)                          # التحرر الآن
           & cross_up
           & (c > bb_up)
           & (v > VOL_CONFIRM * vol_sma(v, 20)))
    return sig.fillna(False)


def _atr(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def self_test():
    rng = np.random.default_rng(42)
    n = 5000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": 100 + rng.normal(0, 1, n).cumsum(),
                       "volume": rng.uniform(1, 100, n)}, index=idx)
    df["close"] = df["open"] + rng.normal(0, 0.5, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng.normal(0, 0.3, n))
    s_lo = make_signals(df, length=12, bb_mult=2.0, kc_mult=1.5, mom_p=8)
    s_hi = make_signals(df, length=20, bb_mult=2.5, kc_mult=1.0, mom_p=12)
    assert s_lo.dtype == bool and len(s_lo) == n
    assert int(s_lo.sum()) <= int(s_hi.sum()), "ضغط أضيق يجب ألا يزيد الإشارات"
    k = 0
    for a in SWEEP_PARAMS["length"]:
        for b in SWEEP_PARAMS["bb_mult"]:
            for m in SWEEP_PARAMS["kc_mult"]:
                for p in SWEEP_PARAMS["mom_p"]:
                    make_signals(df, length=a, bb_mult=b, kc_mult=m, mom_p=p)
                    k += 1
    assert k == 16, f"الشبكة يجب أن تكون 16 لا {k}"
    print(f"[L0019·F-007] self_test OK — 16 تركيبة | إشارات: {int(s_lo.sum())} / {int(s_hi.sum())}")


if __name__ == "__main__":
    self_test()
