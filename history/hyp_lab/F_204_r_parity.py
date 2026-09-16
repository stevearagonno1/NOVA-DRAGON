# -*- coding: utf-8 -*-
# [F-204] تكافؤ المخاطرة بسقف وحارس وتنصيف (تحجيم) — إدارة حصة
# المصدر: معرفة: مقتنص بطي V5.3 (plan_position + RISK_TOLERANCE + VOL_SIZE_HALVE) — يخلف F-121 بإضافات
# notional = R×entry/SL_distance بسقف cap$ وحارس (المخاطرة الفعلية ≤ R×1.05)
# وتنصيف تلقائي عند VR > halve_vr (VR = ATR14/متوسطه 20).
from typing import Tuple
import numpy as np
import pandas as pd

SWEEP_PARAMS = {
    "R": [0.20, 1.0, 2.0],
    "cap": [12.0, 25.0],
    "halve_vr": [1.30, 1.50, 2.00],
}


def make_sizing_spec(df: pd.DataFrame, **params) -> dict:
    """يرجع مواصفات التحجيم للآلة (تُستأنف عند كل دخول)."""
    from common import atr
    a14 = atr(df)
    vr = a14 / a14.rolling(20, min_periods=10).mean()
    return {
        "R": params.get("R", 1.0),
        "cap": params.get("cap", 12.0),
        "halve_vr": params.get("halve_vr", 1.5),
        "vr": vr,
    }


def self_test():
    """اختبار ذاتي: R ثابت → المخاطرة الفعلية لكل صفقة ≈ R مهما اتسع الوقف."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import simulate, atr
    rng = np.random.default_rng(42)
    n = 2000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({
        "open": 100 + rng.normal(0, 1, n).cumsum(),
        "volume": rng.uniform(1, 100, n),
    }, index=idx)
    df["close"] = df["open"] + rng.normal(0, 0.5, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng.normal(0, 0.3, n))
    sig = pd.Series(False, index=idx)
    sig.iloc[[20, 100, 300, 500]] = True
    for R in SWEEP_PARAMS["R"]:
        spec = make_sizing_spec(df, R=R, cap=25.0, halve_vr=2.0)
        st, tr = simulate(df, sig, atr(df), sizing=spec)
        if st["trades"]:
            risks = [t["risk"] for t in tr if t["risk"] is not None]
            mx = max(risks)
            assert mx <= R * 1.05 + 1e-9, f"الحارس خُرق: R={R} max_risk={mx}"
    print("[F-204] self_test OK — الحارس صامد على كل قيم R")


if __name__ == "__main__":
    self_test()
