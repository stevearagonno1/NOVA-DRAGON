# -*- coding: utf-8 -*-
# [F-126] كسر الهيكل MSS بجسم وإزاحة (نواة NOVA) — دخول
# المصدر: معرفة: NOVA (6).py.txt (v3.0 detect_mss) — ثابتة عبر كل الأجيال حتى V5.3
# ملاحظة v1: معاملا max_age/trig_frame مستبعدان من الجولة الأولى (معناؤهما غير محسوم
# في الكتلة) — يُفصل فيهما بجولة جهاز المستخدم.
from typing import Tuple
import numpy as np
import pandas as pd

SWEEP_PARAMS = {
    "body_ratio": [0.40, 0.50, 0.60],
    "range_atr": [0.60, 0.80, 1.00],
    "lookback": [10, 20, 50],
}


def mss_signal(df: pd.DataFrame, body_ratio=0.50, range_atr=0.80, lookback=20) -> pd.Series:
    """الشرط الآلي حرفياً:
    (open <= HH(n) < close) AND (body/range >= body_ratio) AND (range >= range_atr*ATR(14))
    AND (آخر إغلاق > القمة المكسورة)  [متضمنة في open <= HH < close]"""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    hh_n = h.shift(1).rolling(lookback, min_periods=lookback).max()
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14, min_periods=14).mean()
    rng = (h - l).replace(0, np.nan)
    body = (c - o).abs()
    sig = (o <= hh_n) & (hh_n < c) & (body / rng >= body_ratio) & (rng >= range_atr * atr14)
    return sig.fillna(False)


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    return mss_signal(
        df,
        body_ratio=params.get("body_ratio", 0.50),
        range_atr=params.get("range_atr", 0.80),
        lookback=params.get("lookback", 20),
    )


def self_test():
    rng = np.random.default_rng(42)
    n = 3000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({
        "open": 100 + rng.normal(0, 1, n).cumsum(),
        "volume": rng.uniform(1, 100, n),
    }, index=idx)
    df["close"] = df["open"] + rng.normal(0, 0.5, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng.normal(0, 0.3, n))
    sig = make_signals(df)
    assert isinstance(sig, pd.Series) and sig.dtype == bool and len(sig) == len(df)
    # اختبار دلالي: قمة داخل نافذة الـ20 ثم شمعة خضراء تكسرها → إشارة حتمية
    df2 = df.copy()
    peak = df2["high"].iloc[1000:1050].max() + 0.5
    df2.loc[idx[1030], "high"] = peak          # داخل نافذة HH(20) عند الشمعة 1050
    df2.loc[idx[1050], "open"] = peak - 0.01
    df2.loc[idx[1050], "close"] = peak + 2.0
    df2.loc[idx[1050], "high"] = peak + 2.0
    df2.loc[idx[1050], "low"] = peak - 0.01
    sig2 = make_signals(df2)
    assert bool(sig2.loc[idx[1050]]), "كسر صريح لم يُنتج إشارة"
    for p in SWEEP_PARAMS["body_ratio"]:
        make_signals(df, body_ratio=p)
    print(f"[F-126] self_test OK — إشارات: {int(sig.sum())} (والكسر الصريح مُصطاد)")


if __name__ == "__main__":
    self_test()
