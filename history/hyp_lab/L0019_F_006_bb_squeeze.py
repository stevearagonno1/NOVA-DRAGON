# -*- coding: utf-8 -*-
"""[L0019 · F-006] انضغاط بولنجر ثم انفجار بحجم — دخول

عقد الآلة حرفيًا:
  (Bandwidth تحت percentile(Bandwidth, lookback, pct) لآخر duration شمعة متتالية)
  AND (close > BB_upper(bb_p, bb_std))
  AND (volume > 1.2 × VOL_SMA(20))
  AND (close > SMA(50))
السويب: bb_p=[20,35] × bb_std=[2.0,2.5] × pct=[5,12,15,20] × lookback=[50,120] × duration=[3,6]
        ⇒ 64 تركيبة
المصدر: بحث حر — NPF (Bollinger Intraday Squeeze) + TradingCompendium + EverHint Squeeze

شراء فقط 🔒. percentile(X,n,p) = الرتبة المئوية p للقيمة الحالية داخل آخر n شمعة (دليل الرموز).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from L0019_indicators import bb, rolling_percentile, vol_sma

SWEEP_PARAMS = {
    "bb_p": [20, 35],
    "bb_std": [2.0, 2.5],
    "pct": [5, 12, 15, 20],
    "lookback": [50, 120],
    "duration": [3, 6],
}
VOL_CONFIRM = 1.2


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    bp = params.get("bb_p", 20)
    bs = params.get("bb_std", 2.0)
    pct = params.get("pct", 15)
    lb = params.get("lookback", 50)
    dur = params.get("duration", 6)
    c, v = df["close"], df["volume"]
    _, upper, _, bw = bb(c, bp, bs)
    squeeze = rolling_percentile(bw, lb) < (pct / 100.0)
    dur_ok = squeeze.rolling(dur, min_periods=dur).sum() == dur
    sig = (dur_ok & (c > upper) & (v > VOL_CONFIRM * vol_sma(v, 20))
           & (c > c.rolling(50, min_periods=50).mean()))
    return sig.fillna(False)


def self_test():
    rng = np.random.default_rng(42)
    n = 5000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": 100 + rng.normal(0, 1, n).cumsum(),
                       "volume": rng.uniform(1, 100, n)}, index=idx)
    df["close"] = df["open"] + rng.normal(0, 0.5, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng.normal(0, 0.3, n))
    s_lo = make_signals(df, pct=5, duration=6, bb_p=35, bb_std=2.5)
    s_hi = make_signals(df, pct=20, duration=3, bb_p=20, bb_std=2.0)
    assert s_lo.dtype == bool and len(s_lo) == n
    assert int(s_lo.sum()) <= int(s_hi.sum()), "ضغط أضيق/أطول يجب ألا يزيد الإشارات"
    # الرتبة المئوية في [0,1] وليست ثابتة
    _, _, _, bw = bb(df["close"], 20, 2.0)
    rp = rolling_percentile(bw, 50).dropna()
    assert rp.between(0, 1).all() and rp.nunique() > 10
    k = 0
    for a in SWEEP_PARAMS["bb_p"]:
        for b in SWEEP_PARAMS["bb_std"]:
            for p in SWEEP_PARAMS["pct"]:
                for lb in SWEEP_PARAMS["lookback"]:
                    for d in SWEEP_PARAMS["duration"]:
                        make_signals(df, bb_p=a, bb_std=b, pct=p, lookback=lb, duration=d)
                        k += 1
    assert k == 64, f"الشبكة يجب أن تكون 64 لا {k}"
    print(f"[L0019·F-006] self_test OK — 64 تركيبة | إشارات: {int(s_lo.sum())} / {int(s_hi.sum())}")


if __name__ == "__main__":
    self_test()
