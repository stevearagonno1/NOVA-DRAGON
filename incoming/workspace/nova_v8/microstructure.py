"""Module — microstructure structure signals (MSS / SFP / FVG levels).

Vectorized causal detectors used by the "structure truth oracle" and as
indicators feeding trigger evaluation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sfp_signal(o: pd.Series, h: pd.Series, l: pd.Series, c: pd.Series,
               look: int = 20) -> pd.Series:
    """Swing-Failure-Pattern: +1 bullish, -1 bearish, 0 none."""
    prior_hi = h.shift(2).rolling(look).max()
    prior_lo = l.shift(2).rolling(look).min()
    body_hi = np.maximum(o, c)
    body_lo = np.minimum(o, c)
    bear = ((h > prior_hi) & (body_hi < prior_hi)).fillna(False)
    bull = ((l < prior_lo) & (body_lo > prior_lo)).fillna(False)
    sig = pd.Series(np.int8(0), index=h.index, dtype=np.int8)
    sig[bull] = 1
    sig[bear] = -1
    return sig


def mss_signal(o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
               atr14: np.ndarray, L: int = 5) -> np.ndarray:
    """Monotonic market-structure-shift: +1 bull break / -1 bear break / 0."""
    n = len(c)
    sig = np.zeros(n, dtype=np.int8)
    if n <= L:
        return sig
    dsh = np.r_[np.nan, np.sign(np.diff(h))]
    dsl = np.r_[np.nan, np.sign(np.diff(l))]
    rs_h = pd.Series(dsh).rolling(L - 1).sum().to_numpy()
    rs_l = pd.Series(dsl).rolling(L - 1).sum().to_numpy()
    desc = np.nan_to_num(rs_h) == -(L - 1)
    asc = np.nan_to_num(rs_l) == (L - 1)
    atr = np.nan_to_num(atr14)
    rng = h - l
    body = np.abs(c - o)
    disp_up = (body > 0.5 * rng) & (rng > 0.8 * atr) & (c > o)
    disp_dn = (body > 0.5 * rng) & (rng > 0.8 * atr) & (c < o)
    bull = np.zeros(n, bool)
    bear = np.zeros(n, bool)
    bull[L:] = desc[L - 1:-1] & disp_up[L:] & (c[L:] > h[:-L])
    bear[L:] = asc[L - 1:-1] & disp_dn[L:] & (c[L:] < l[:-L])
    sig[bull] = 1
    sig[bear] = -1
    return sig


def fvg_levels(h: np.ndarray, l: np.ndarray):
    """Vectorized 3-bar imbalance zones."""
    n = len(h)
    nan = np.nan
    bull_t, bull_b = np.full(n, nan), np.full(n, nan)
    bear_t, bear_b = np.full(n, nan), np.full(n, nan)
    if n > 2:
        bull = l[2:] > h[:-2]
        bull_t[2:][bull] = l[2:][bull]
        bull_b[2:][bull] = h[:-2][bull]
        bear = h[2:] < l[:-2]
        bear_t[2:][bear] = l[:-2][bear]
        bear_b[2:][bear] = h[2:][bear]
    return bull_t, bull_b, bear_t, bear_b
