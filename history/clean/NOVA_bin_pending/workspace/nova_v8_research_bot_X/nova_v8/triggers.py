"""Module — directional entry triggers.

Per design: "any indicator that fires opens a position; first to fire wins".
Every entry trigger is computed vectorized over the trade-TF matrix. At each
bar, if one or more triggers fire, we tag the position with the trigger that
opened it (priority order = first in the ordered list that is true that bar).

A position is only opened when the regime is directional (bull/bear); grid and
BTC modes are handled by their own modules. Structure events are also exported
here because they feed the truth oracle.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ordered trigger definitions: name -> (long_cond_series, short_cond_series)
# Each is evaluated on the matrix columns. We build them inside build_events.
PRIORITY = [
    "MSS", "SFP", "MicroBurst", "RSI", "MACD", "Bollinger", "EMA",
    "ADX", "Stochastic", "OBV", "SuperTrend", "RSI7", "KAMA",
]

# flags for which bespoke-colour triggers we keep on (KAMA/RSI7 folded in)


def _cols(df: pd.DataFrame) -> pd.Series:
    return pd.Series(np.zeros(len(df), dtype=bool), index=df.index)


def build_triggers(df: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    """Return {name: (long_cond, short_cond)} boolean series, causal."""
    o, h, l, c = df.open, df.high, df.low, df.close
    long_, short_ = {}, {}

    # MSS structure break
    long_["MSS"] = df["mss"] == 1
    short_["MSS"] = df["mss"] == -1

    # SFP liquidity sweep reversal (bullish/bearish close)
    long_["SFP"] = (df["sfp"] == 1) & (c > o)
    short_["SFP"] = (df["sfp"] == -1) & (c < o)

    # Micro-burst momentum: macd rising + volume burst + RSI rising
    mh = df["macd"]
    vol_burst = df["volume"] > 1.5 * df["vol_sma20"]
    long_["MicroBurst"] = (mh > mh.shift(1)) & (c > o) & vol_burst
    short_["MicroBurst"] = (mh < mh.shift(1)) & (c < o) & vol_burst

    # RSI14
    rsi = df["rsi"]
    long_["RSI"] = (rsi < 35) & (rsi > rsi.shift(1))
    short_["RSI"] = (rsi > 65) & (rsi.shift(1) > rsi)

    # MACD histogram sign change
    long_["MACD"] = (mh > 0) & (mh.shift(1) <= 0)
    short_["MACD"] = (mh < 0) & (mh.shift(1) >= 0)

    # Bollinger rebound from lower band (long) / upper band (short)
    long_["Bollinger"] = (l <= df["bb_low"] * 1.005) & (c > o)
    short_["Bollinger"] = (h >= df["bb_up"] * 0.995) & (c < o)

    # EMA trend alignment
    long_["EMA"] = (c > df["ema50"]) & (df["ema50"] > df["ema200"])
    short_["EMA"] = (c < df["ema50"]) & (df["ema50"] < df["ema200"])

    # ADX strong trend
    long_["ADX"] = df["adx"] > 22
    short_["ADX"] = df["adx"] > 22

    # Stochastic cross above 20 (long) / below 80 (short)
    long_["Stochastic"] = (df["stoch_k"] > df["stoch_d"]) & (df["stoch_k"] < 25)
    short_["Stochastic"] = (df["stoch_k"] < df["stoch_d"]) & (df["stoch_k"] > 75)

    # OBV above its 20-sma
    long_["OBV"] = df["obv"] > df["obv_sma20"]
    short_["OBV"] = df["obv"] < df["obv_sma20"]

    # SuperTrend flip
    long_["SuperTrend"] = (df["st"] == 1) & (df["st"].shift(1) == -1)
    short_["SuperTrend"] = (df["st"] == -1) & (df["st"].shift(1) == 1)

    # RSI7 fast
    r7 = df["rsi7"]
    long_["RSI7"] = (r7 < 30) & (r7 > r7.shift(1))
    short_["RSI7"] = (r7 > 70) & (r7.shift(1) > r7)

    # KAMA-alma price filter (long above alma etc.) as a mild trigger proxy
    long_["KAMA"] = c > df["alma200"]
    short_["KAMA"] = c < df["alma200"]

    return {"long": long_, "short": short_}


def compute_entry_events(df: pd.DataFrame, triggers=None, edge: bool = True):
    """Return (entry_side, entry_trigger) Series per bar (first-to-fire wins).

    entry_side: +1 long / -1 short / 0 none. entry_trigger: str or None.

    `edge=True` turns each condition into a *discrete fire* (rising edge), so an
    always-on level condition (e.g. price>EMA in a trend) opens a fresh position
    only once, when it first becomes true — it does NOT re-open every bar.
    """
    t = triggers or build_triggers(df)
    side = pd.Series(0, index=df.index, dtype=np.int8)
    trig = pd.Series(None, index=df.index, dtype=object)

    def _rise(cond):
        c = cond.fillna(False)
        return c & ~c.shift(1, fill_value=False)

    for name in PRIORITY:
        lon = t["long"].get(name)
        sho = t["short"].get(name)
        if lon is None or sho is None:
            continue
        fire_long = _rise(lon) if edge else lon
        fire_short = _rise(sho) if edge else sho
        open_long = fire_long & (side == 0)
        open_short = fire_short & (side == 0)
        side = side.where(~open_long, 1)
        trig = trig.where(~open_long, name)
        side = side.where(~open_short, -1)
        trig = trig.where(~open_short, name)
    return side, trig
