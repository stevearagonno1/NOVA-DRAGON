# -*- coding: utf-8 -*-
# [F-015] Z-Score متطرف + شمعة انعكاس + بوابة نظام (SSRN) — دخول
# المصدر: بحث حر: SSRN Bhatti – Regime-Conditioned MR + TheLedgerMind – Z-Score confluence
# بوابة الساعة: تُحسب من df نفسها (إعادة عينة 5m→1h) على ساعات مغلقة فقط — لا أعمدة خارجية.
from typing import Tuple
import numpy as np
import pandas as pd

SWEEP_PARAMS = {
    "z_p": [20, 30, 50],
    "z_th": [-1.5, -2.0, -2.5],
    "wick_ratio": [0.5, 0.6],
}


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    """الشرط الآلي حرفياً: (Z(n) < th) AND (close>open) AND ((close-low) >= w*range) AND (close_1h > SMA200_1h)."""
    zp = params.get("z_p", 30)
    zth = params.get("z_th", -2.0)
    w = params.get("wick_ratio", 0.6)
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    z = (c - c.rolling(zp, min_periods=zp).mean()) / c.rolling(zp, min_periods=zp).std()
    rng = (h - l).replace(0, np.nan)
    # الساعة (سببي): 1h-بر [H, H+1h) يُعرف إغلاقه عند H+1h → نضبطه على «لحظة العلم»
    # ونسأل: ما آخر حالة معروفة عند إغلاق شمعة الإشارة (t+5m)؟
    c1h = c.resample("1h", label="left", closed="left").last()
    known = c1h.copy()
    known.index = known.index + pd.Timedelta(hours=1)
    sma200_1h = known.rolling(200, min_periods=100).mean()
    gate = known > sma200_1h
    gnum = gate.astype("float64").reindex(df.index + pd.Timedelta(minutes=5), method="ffill")
    gate5v = (gnum > 0.5).to_numpy()   # NaN → False
    sig = ((z < zth) & (c > o) & ((c - l) >= w * rng)).to_numpy() & gate5v
    return pd.Series(sig, index=df.index)


def self_test():
    rng = np.random.default_rng(42)
    n = 3000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    # مسار صاعد ثابت (بوابة الساعة صالحة) ثم هبوط حاد + شمعة انعكاس → إشارة حتمية
    px = 100 + np.linspace(0, 30, n) + rng.normal(0, 0.3, n)
    df = pd.DataFrame({
        "open": px,
        "volume": rng.uniform(1, 100, n),
    }, index=idx)
    df["close"] = df["open"] + 0.01
    df["high"] = df[["open", "close"]].max(axis=1) + 0.05
    df["low"] = df[["open", "close"]].min(axis=1) - 0.05
    base = df["close"].iloc[2499]
    drop = base - 4.0
    df.loc[idx[2501], "open"] = drop
    df.loc[idx[2501], "close"] = drop + 1.0
    df.loc[idx[2501], "high"] = drop + 1.0
    df.loc[idx[2501], "low"] = drop - 0.1
    sig = make_signals(df)
    assert isinstance(sig, pd.Series) and sig.dtype == bool and len(sig) == len(df)
    assert bool(sig.iloc[2501]), "الهبوط الحاد + الانعكاس في صعود لم يُنتج إشارة"
    for p in SWEEP_PARAMS["z_th"]:
        make_signals(df, z_th=p)
    print(f"[F-015] self_test OK — إشارات: {int(sig.sum())} (والحدث الحتمي مُصطاد)")


if __name__ == "__main__":
    self_test()
