# -*- coding: utf-8 -*-
# [F-127] بوابة الإزاحة الدنيا للكسر (قياس V4.1) — فلتر
# المصدر: معرفة: NOVA_V4_2_fixed.py.txt (طبقة المعايرة V4.1، البند 2 — قياس لا رأي)
# نواة MSS = قيم F-126 الافتراضية (0.50/0.80/20)؛ الفلتر: range/ATR(14) >= disp_min على شمعة الكسر.
from typing import Tuple
import numpy as np
import pandas as pd

from F_126_mss_core import mss_signal

SWEEP_PARAMS = {
    "disp_min": [1.00, 1.50, 1.60, 2.00],
}


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    """الشرط الآلي حرفياً: (disp = range / ATR(14) >= disp_min) مضروباً مع نواة MSS."""
    dmin = params.get("disp_min", 1.6)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14, min_periods=14).mean()
    disp = (h - l).replace(0, np.nan) / atr14
    sig = mss_signal(df) & (disp >= dmin)
    return sig.fillna(False)


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
    s_loose = make_signals(df, disp_min=1.0)
    s_strict = make_signals(df, disp_min=2.0)
    assert isinstance(s_strict, pd.Series) and s_strict.dtype == bool
    assert int(s_strict.sum()) <= int(s_loose.sum()), "فلتر صارم يجب أن يقلل الإشارات"
    for p in SWEEP_PARAMS["disp_min"]:
        make_signals(df, disp_min=p)
    print(f"[F-127] self_test OK — إشارات: {int(s_strict.sum())} (عند 2.0) / {int(s_loose.sum())} (عند 1.0)")


if __name__ == "__main__":
    self_test()
