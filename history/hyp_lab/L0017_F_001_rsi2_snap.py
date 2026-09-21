# -*- coding: utf-8 -*-
"""[L0017 · F-001] سناب مؤشر القوة القصير في الترند الصاعد — دخول (مرتبة 2 من النخبة)

عقد الآلة حرفياً:
  (الإغلاق > متوسط 200) و (الإغلاق < متوسط 5) و (المؤشر فترة 2 < العتبة)
  السويب: العتبة=[5,10,15] × متوسط الترند=[100,200] × متوسط التراجع=[3,5,10] ⇒ 18 تركيبة

مطابق لوحدة F_001_rsi2_snapback.py المرجعية في كل ساق (نُسخت الدالة نصاً) —
أُفرد ملفاً مستقلاً لأن L0017 جولة مستقلة لا تلمس أي مرجع قائم (حاجز الجولة).
RSI بترميز وايلدر (ewm alpha=1/period) كما في المرجع — لا تغيير.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SWEEP_PARAMS = {
    "rsi2_os": [5, 10, 15],
    "sma_trend": [100, 200],
    "sma_pull": [3, 5, 10],
}


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, np.nan))


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    os_level = params.get("rsi2_os", 10)
    sma_trend = params.get("sma_trend", 200)
    sma_pull = params.get("sma_pull", 5)
    c = df["close"]
    sig = (c > c.rolling(sma_trend, min_periods=sma_trend // 2).mean()) & \
          (c < c.rolling(sma_pull, min_periods=sma_pull).mean()) & \
          (_rsi(c, 2) < os_level)
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

    s5 = make_signals(df, rsi2_os=5, sma_trend=200, sma_pull=5)
    s15 = make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5)
    assert s5.dtype == bool and len(s5) == n
    assert bool((s5 & ~s15).sum() == 0), "رتابة العتبة مكسورة: os=5 ⊆ os=15"
    # مطابقة حرفية للوحدة المرجعية (لا انحراف)
    import F_001_rsi2_snapback as REF
    for o_ in SWEEP_PARAMS["rsi2_os"]:
        for t_ in SWEEP_PARAMS["sma_trend"]:
            for p_ in SWEEP_PARAMS["sma_pull"]:
                a = make_signals(df, rsi2_os=o_, sma_trend=t_, sma_pull=p_)
                b = REF.make_signals(df, rsi2_os=o_, sma_trend=t_, sma_pull=p_)
                assert a.equals(b), f"انحراف عن المرجع عند {o_}/{t_}/{p_}"
    print(f"[L0017·F-001] self_test OK — 18 تركيبة · مطابقة للمرجع | إشارات: {int(s5.sum())} (os=5) / {int(s15.sum())} (os=15)")


if __name__ == "__main__":
    self_test()
