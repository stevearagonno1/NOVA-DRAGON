# -*- coding: utf-8 -*-
# [F-001] سناب-باك RSI2 في ترند صاعد (كونورز) — دخول
# المصدر: بحث حر: Swingfolio – RSI-2 Strategy (Larry Connors) + CoinQuant – 78 Backtests (Strategy B)
# ملاحظة: الفترة ثابتة 2 (حرفياً من الكتلة: RSI(2)) والسويب على عتبة التشبع.
from typing import Tuple
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
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    return rsi


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    """الشرط الآلي حرفياً: (close > SMA(trend)) AND (close < SMA(pull)) AND (RSI(2) < os)."""
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
    for p in SWEEP_PARAMS["rsi2_os"]:
        make_signals(df, rsi2_os=p)
    print(f"[F-001] self_test OK — إشارات: {int(sig.sum())}")


if __name__ == "__main__":
    self_test()
