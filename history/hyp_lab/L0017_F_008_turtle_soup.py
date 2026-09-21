# -*- coding: utf-8 -*-
"""[L0017 · F-008] كنس سيولة القيعان والاسترداد — عكس السلاحف (مرتبة 8 · مرشحة تنويع ارتباط)

عقد الآلة حرفياً:
  (القاع < أدنى النطاق) و (الإغلاق > أدنى النطاق)
  و (الذيل السفلي ≥ النسبة × مدى الشمعة) و (الإغلاق > الافتتاح)
  السويب: النطاق=[10,20,55] × نسبة الذيل=[0.5,0.6,0.7] ⇒ 9 تركيبات

مطابق لوحدة F_008_turtle_soup.py المرجعية في كل ساق. شراء فقط 🔒
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SWEEP_PARAMS = {
    "lookback": [10, 20, 55],
    "wick_ratio": [0.5, 0.6, 0.7],
}


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    lb = params.get("lookback", 20)
    w = params.get("wick_ratio", 0.6)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ll_n = l.shift(1).rolling(lb, min_periods=lb).min()
    rng = (h - l).replace(0, np.nan)
    lw = np.minimum(o, c) - l                      # الذيل السفلي
    sig = (l < ll_n) & (c > ll_n) & (lw >= w * rng) & (c > o)
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

    s_loose = make_signals(df, lookback=10, wick_ratio=0.5)
    s_strict = make_signals(df, lookback=10, wick_ratio=0.7)
    assert s_loose.dtype == bool and len(s_loose) == n
    assert bool((s_strict & ~s_loose).sum() == 0), "رتابة نسبة الذيل مكسورة"
    # كل إشارة شمعة خضراء بالضرورة (حاجز: شراء فقط على استرداد)
    assert bool(((df["close"] > df["open"]) | ~s_loose).all()), "إشارة على شمعة حمراء — خرق العقد"
    import F_008_turtle_soup as REF
    for lb in SWEEP_PARAMS["lookback"]:
        for w in SWEEP_PARAMS["wick_ratio"]:
            assert make_signals(df, lookback=lb, wick_ratio=w).equals(
                REF.make_signals(df, lookback=lb, wick_ratio=w)), f"انحراف عن المرجع {lb}/{w}"
    print(f"[L0017·F-008] self_test OK — 9 تركيبات · مطابقة للمرجع | إشارات: {int(s_loose.sum())} (0.5) / {int(s_strict.sum())} (0.7)")


if __name__ == "__main__":
    self_test()
