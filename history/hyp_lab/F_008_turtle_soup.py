# -*- coding: utf-8 -*-
# [F-008] كنس سيولة القيعان والاسترداد (Turtle Soup شراء) — دخول
# المصدر: بحث حر: FundedTradingPlus – Turtle Soup + Orbex – Trapped Liquidity + UltimaMarkets rules
from typing import Tuple
import numpy as np
import pandas as pd

SWEEP_PARAMS = {
    "lookback": [10, 20, 55],
    "wick_ratio": [0.5, 0.6, 0.7],
}


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    """الشرط الآلي حرفياً: (low < LL(n)) AND (close > LL(n)) AND (lowerWick >= w*range) AND (close > open)."""
    lb = params.get("lookback", 20)
    w = params.get("wick_ratio", 0.6)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ll_n = l.shift(1).rolling(lb, min_periods=lb).min()
    rng = (h - l).replace(0, np.nan)
    lw = np.minimum(o, c) - l
    sig = (l < ll_n) & (c > ll_n) & (lw >= w * rng) & (c > o)
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
    sig = make_signals(df)
    assert isinstance(sig, pd.Series) and sig.dtype == bool and len(sig) == len(df)
    for p in SWEEP_PARAMS["lookback"]:
        make_signals(df, lookback=p)
    print(f"[F-008] self_test OK — إشارات: {int(sig.sum())}")


if __name__ == "__main__":
    self_test()
