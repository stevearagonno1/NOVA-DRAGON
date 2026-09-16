"""Module — vectorized, causal indicator math (numpy/pandas, non-repainting).

Combines the original bespoke indicators (ALMA, Cardwell RSI zones, hysteresis,
anchored KAMA, rolling Hurst, MSS/FVG/SFP) with the classic set added per the
design (RSI14, MACD, Bollinger, EMA50/200, ADX, Stochastic, OBV, SuperTrend).

Every function is causal: value at t depends only on data <= t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


# ---------------------------------------------------------------- helpers
def rma(s: pd.Series, n: int) -> pd.Series:
    """Wilder smoothing (RMA)."""
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def true_range(h: pd.Series, l: pd.Series, c: pd.Series) -> pd.Series:
    pc = c.shift(1)
    return pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)


def wilder_atr(df: pd.DataFrame, n: int = C.ATR_LEN) -> pd.Series:
    return rma(true_range(df.high, df.low, df.close), n)


# ------------------------------------------------------------------- ALMA
def alma(close: pd.Series, length: int = C.ALMA_LEN,
         offset: float = C.ALMA_OFFSET, sigma: float = C.ALMA_SIGMA) -> pd.Series:
    m = offset * (length - 1)
    s = length / sigma
    w = np.exp(-((np.arange(length) - m) ** 2) / (2.0 * s * s))
    w /= w.sum()
    x = close.to_numpy(dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= length:
        out[length - 1:] = np.convolve(x, w[::-1])[length - 1:len(x)]
    return pd.Series(out, index=close.index)


# --------------------------------------------------------------------- RSI
def rsi_wilder(close: pd.Series, n: int) -> pd.Series:
    d = close.diff()
    rs = rma(d.clip(lower=0.0), n) / rma(-d.clip(upper=0.0), n)
    return 100.0 - 100.0 / (1.0 + rs)


# ------------------------------------------------------------ Cardwell zones
def cardwell_zone(rsi: pd.Series) -> pd.Series:
    """Bullish zone 40-80 / Bearish 20-60, causal state machine."""
    r = rsi.to_numpy(dtype=float)
    out = np.full(len(r), "NEUTRAL", dtype=object)
    state = "NEUTRAL"
    for i, v in enumerate(r):
        if np.isfinite(v):
            if state != "BULL_ZONE" and v >= 55.0:
                state = "BULL_ZONE"
            elif state == "BULL_ZONE" and v < 40.0:
                state = "NEUTRAL"
            if state != "BEAR_ZONE" and v <= 45.0:
                state = "BEAR_ZONE"
            elif state == "BEAR_ZONE" and v > 60.0:
                state = "NEUTRAL"
        out[i] = state
    return pd.Series(out, index=rsi.index)


# --------------------------------------------------------------------- ADX
def adx(df: pd.DataFrame, n: int = C.ADX_LEN) -> pd.Series:
    h, l, c = df.high, df.low, df.close
    up, dn = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr = rma(true_range(h, l, c), n)
    plus_di = 100.0 * rma(plus_dm, n) / atr
    minus_di = 100.0 * rma(minus_dm, n) / atr
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return rma(dx, n)


def macd_hist(close: pd.Series, fast: int = C.MACD_FAST,
              slow: int = C.MACD_SLOW, sig: int = C.MACD_SIG) -> pd.Series:
    dif = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    dea = dif.ewm(span=sig, adjust=False).mean()
    return dif - dea


def bollinger(close: pd.Series, n: int = C.BB_LEN, k: float = C.BB_STD):
    mid = close.rolling(n).mean()
    sd = close.rolling(n).std(ddof=0)
    return mid, mid + k * sd, mid - k * sd


def ema(close: pd.Series, n: int) -> pd.Series:
    return close.ewm(span=n, adjust=False).mean()


def stochastic(df: pd.DataFrame, k: int = C.STOCH_K, d: int = C.STOCH_D,
               smooth: int = C.STOCH_SMOOTH):
    ll = df.low.rolling(k).min()
    hh = df.high.rolling(k).max()
    raw = 100.0 * (df.close - ll) / (hh - ll).replace(0.0, np.nan)
    kk = raw.rolling(smooth).mean()
    dd = kk.rolling(d).mean()
    return kk, dd


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    sign = np.sign(close.diff()).fillna(0.0)
    return (sign * volume).cumsum()


def supertrend(df: pd.DataFrame, atr_n: int = C.SUPERTREND_ATR,
               mult: float = C.SUPERTREND_MULT):
    """Return +1 (bull) / -1 (bear) supertrend state, causal."""
    atr = wilder_atr(df, atr_n)
    hl2 = (df.high + df.low) / 2.0
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    up = upper.copy().to_numpy(float)
    lo = lower.copy().to_numpy(float)
    st = np.ones(len(df), dtype=float)   # state +1 bull
    close = df.close.to_numpy(float)
    n = len(df)
    for i in range(1, n):
        if not np.isfinite(close[i]) or not np.isfinite(up[i]):
            st[i] = st[i - 1]
            continue
        prev = st[i - 1]
        if prev > 0:
            up[i] = max(up[i], up[i - 1]) if np.isfinite(up[i - 1]) else up[i]
            if close[i] < lo[i]:
                st[i] = -1.0
            else:
                st[i] = 1.0
        else:
            lo[i] = min(lo[i], lo[i - 1]) if np.isfinite(lo[i - 1]) else lo[i]
            if close[i] > up[i]:
                st[i] = 1.0
            else:
                st[i] = -1.0
    return pd.Series(st, index=df.index)


def hurst_rolling(close: pd.Series, window: int = C.HURST_LEN,
                  chunk: int = 200_000) -> pd.Series:
    x = np.log(np.clip(close.to_numpy(dtype=float), 1e-12, None))
    n = len(x)
    out = np.full(n, np.nan)
    taus = np.array([2, 4, 8, 16, 32])
    lts = np.log(taus)
    xm = lts - lts.mean()
    den = float((xm * xm).sum())

    def block(vals: np.ndarray) -> np.ndarray:
        Y = np.empty((len(vals), len(taus)))
        for i, t in enumerate(taus):
            with np.errstate(divide="ignore", invalid="ignore"):
                Y[:, i] = np.log((vals[:, t:] - vals[:, :-t]).std(axis=1))
        bad = ~np.isfinite(Y).all(axis=1)
        hh = ((Y - Y.mean(axis=1, keepdims=True)) * xm).sum(axis=1) / den
        hh[bad] = np.nan
        return hh

    start = 0
    while start < n:
        end = min(n, start + chunk)
        if end - start >= window:
            sw = np.lib.stride_tricks.sliding_window_view(x[start:end], window)
            out[start + window - 1:end] = block(sw)
        start = end
    return pd.Series(out, index=close.index)


# =================================================================== full matrix
def compute_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """One-shot causal feature matrix over OHLCV (trade TF)."""
    df = df.copy()
    o, h, l, c, v = df.open, df.high, df.low, df.close, df.volume

    # ---- classic indicators ----
    df["atr14"] = wilder_atr(df, C.ATR_LEN)
    df["atr_sma100"] = df["atr14"].rolling(100).mean()
    df["vr"] = df["atr14"] / df["atr_sma100"].replace(0.0, np.nan)
    df["ema50"] = ema(c, C.EMA_FAST)
    df["ema200"] = ema(c, C.EMA_SLOW)
    df["rsi"] = rsi_wilder(c, C.RSI_LEN)
    df["macd"] = macd_hist(c)
    bm, bu, bl = bollinger(c)
    df["bb_mid"], df["bb_up"], df["bb_low"] = bm, bu, bl
    df["adx"] = adx(df, C.ADX_LEN)
    df["stoch_k"], df["stoch_d"] = stochastic(df)
    df["obv"] = obv(c, v)
    df["obv_sma20"] = df["obv"].rolling(20).mean()
    df["st"] = supertrend(df)
    df["vol_sma20"] = v.rolling(20).mean()

    # ---- bespoke ----
    df["alma200"] = alma(c)
    df["rsi7"] = rsi_wilder(c, C.RSI_FAST)
    df["rsi_zone"] = cardwell_zone(df["rsi7"])
    df["hurst"] = hurst_rolling(c)

    rng = (h - l).replace(0.0, np.nan)
    df["bar_delta"] = (v * (c - o) / rng).fillna(0.0)   # wick-split delta proxy

    # ---- structure signals (computed on this frame) ----
    from . import microstructure as micro
    df["mss"] = micro.mss_signal(o.to_numpy(float), h.to_numpy(float),
                                 l.to_numpy(float), c.to_numpy(float),
                                 df["atr14"].to_numpy(float))
    df["sfp"] = micro.sfp_signal(o, h, l, c)
    bt, bb, s_up, s_dn = micro.fvg_levels(h.to_numpy(float), l.to_numpy(float))
    df["fvg_bull_top"], df["fvg_bull_bot"] = bt, bb
    df["fvg_bear_top"], df["fvg_bear_bot"] = s_up, s_dn
    df["fvg_bull"] = np.isfinite(bt)
    df["fvg_bear"] = np.isfinite(s_up)
    return df


def resample_higher(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate a 1m OHLCV frame up to a higher timeframe rule ('5min'/'15min')."""
    ohlc = {
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }
    out = df.resample(rule, label="left", closed="left").agg(ohlc).dropna()
    return out
