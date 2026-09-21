# -*- coding: utf-8 -*-
"""[L0017 · F-015] الانحراف المتطرف مع شمعة الانعكاس وبوابة النظام (مرتبة 6)

عقد الآلة حرفياً:
  (الانحراف المعياري للفترة < العتبة) و (الإغلاق > الافتتاح)
  و ((الإغلاق − القاع) ≥ 0.6 × المدى) و (إغلاق الساعة > متوسط 200 على الساعة)
  السويب: الفترة=[20,30,50] × العتبة=[-1.5,-2.0,-2.5] × نسبة الارتداد=[0.5,0.6] ⇒ 18 تركيبة

بوابة الفريم الأعلى سببية صارمة: شمعة الساعة [H, H+1h) لا يُعرف إغلاقها إلا عند H+1h،
فتُزاح لحظة العلم ساعةً كاملة ثم تُسقط على شبكة الفريم العامل بـ ffill — لا تسرب مستقبل.
تعميم موثق عن المرجع F_015: المرجع جمّد الإزاحة على 5 دقائق (index + 5min)؛ هنا تُشتق
من تباعد شبكة الفريم نفسه ليصح على 1h و 4h أيضاً. على 5m النتيجة مطابقة للمرجع حرفاً
(مؤكَّد بالفحص الذاتي أدناه).

ملاحظة على 4h: شمعة الأربع ساعات أوسع من شمعة البوابة، فالبوابة تصير «آخر ساعة معلومة
قبل إغلاق الشمعة» — سببية سليمة وأدق تحفظاً، وتُسطر أمانةً هنا.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SWEEP_PARAMS = {
    "z_p": [20, 30, 50],
    "z_th": [-1.5, -2.0, -2.5],
    "wick_ratio": [0.5, 0.6],
}


def _bar_delta(df: pd.DataFrame) -> pd.Timedelta:
    """تباعد شبكة الفريم — من أكثر الفروق تكراراً (حصين ضد الفجوات)."""
    d = pd.Series(df.index).diff().dropna()
    return pd.Timedelta(d.mode().iloc[0]) if len(d) else pd.Timedelta(minutes=5)


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    zp = params.get("z_p", 30)
    zth = params.get("z_th", -2.0)
    w = params.get("wick_ratio", 0.6)
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    z = (c - c.rolling(zp, min_periods=zp).mean()) / c.rolling(zp, min_periods=zp).std()
    rng = (h - l).replace(0, np.nan)

    c1h = c.resample("1h", label="left", closed="left").last()
    known = c1h.copy()
    known.index = known.index + pd.Timedelta(hours=1)      # لحظة العلم بالإغلاق
    sma200_1h = known.rolling(200, min_periods=100).mean()
    gate = known > sma200_1h
    gnum = gate.astype("float64").reindex(df.index + _bar_delta(df), method="ffill")
    gate_v = (gnum > 0.5).to_numpy()                        # NaN → False

    sig = ((z < zth) & (c > o) & ((c - l) >= w * rng)).to_numpy() & gate_v
    return pd.Series(sig, index=df.index)


def self_test():
    rng = np.random.default_rng(42)
    n = 6000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    px = 100 + np.linspace(0, 30, n) + rng.normal(0, 0.3, n)
    df = pd.DataFrame({"open": px, "volume": rng.uniform(1, 100, n)}, index=idx)
    df["close"] = df["open"] + rng.normal(0, 0.4, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng.normal(0, 0.3, n))

    s = make_signals(df, z_p=30, z_th=-1.5, wick_ratio=0.5)
    assert s.dtype == bool and len(s) == n
    s_strict = make_signals(df, z_p=30, z_th=-2.5, wick_ratio=0.5)
    assert bool((s_strict & ~s).sum() == 0), "رتابة العتبة مكسورة"
    # مطابقة حرفية للمرجع على الفريم الأصلي 5m (تعميم الإزاحة لا يغيّر شيئاً هناك)
    import F_015_zscore_regime as REF
    for p_ in SWEEP_PARAMS["z_p"]:
        for t_ in SWEEP_PARAMS["z_th"]:
            for w_ in SWEEP_PARAMS["wick_ratio"]:
                assert make_signals(df, z_p=p_, z_th=t_, wick_ratio=w_).equals(
                    REF.make_signals(df, z_p=p_, z_th=t_, wick_ratio=w_)), f"انحراف عن المرجع {p_}/{t_}/{w_}"
    # يعمل على 1h و 4h بلا انهيار
    for m in (60, 240):
        agg = df.resample(f"{m}min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
        out = make_signals(agg, z_p=20, z_th=-1.5, wick_ratio=0.5)
        assert len(out) == len(agg) and out.dtype == bool
    print(f"[L0017·F-015] self_test OK — 18 تركيبة · مطابقة للمرجع على 5m · تعمل على 1h/4h | إشارات: {int(s.sum())}")


if __name__ == "__main__":
    self_test()
