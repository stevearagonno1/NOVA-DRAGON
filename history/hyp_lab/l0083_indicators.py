#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0083 — مكتبة المؤشرات. كل دالة تعيد قناع إشارة boolean طوله = عدد الشموع،
حيث True عند شمعة i تعني «قرار عند إغلاق i، تنفيذ من i+1». كلها سببية بحتة.

كل عتبة/شريحة تُجمَّد لاحقًا من التدريب فقط (في l0083_run). هنا الحساب الخام فقط.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _s(a):
    return pd.Series(a, dtype="float64")


def rsi(close, n=14):
    c = _s(close)
    d = c.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    # Wilder smoothing
    ru = up.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rd = dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = ru / rd.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.to_numpy()


def cross_up_through(series, thr):
    a = np.asarray(series, float)
    prev = np.roll(a, 1); prev[0] = np.nan
    return (prev < thr) & (a >= thr)


def cross_down_through(series, thr):
    a = np.asarray(series, float)
    prev = np.roll(a, 1); prev[0] = np.nan
    return (prev > thr) & (a <= thr)


def cross_above(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    pa = np.roll(a, 1); pb = np.roll(b, 1); pa[0] = np.nan; pb[0] = np.nan
    return (pa <= pb) & (a > b)


def stochastic(high, low, close, n=14, d=3):
    h = _s(high); l = _s(low); c = _s(close)
    ll = l.rolling(n, min_periods=n).min()
    hh = h.rolling(n, min_periods=n).max()
    k = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    dd = k.rolling(d, min_periods=d).mean()
    return k.to_numpy(), dd.to_numpy()


def bollinger(close, n=20, k=2.0):
    c = _s(close)
    mid = c.rolling(n, min_periods=n).mean()
    sd = c.rolling(n, min_periods=n).std(ddof=0)
    lower = mid - k * sd
    upper = mid + k * sd
    return lower.to_numpy(), mid.to_numpy(), upper.to_numpy()


def aroon(high, low, n=14):
    h = _s(high); l = _s(low)
    up = h.rolling(n + 1, min_periods=n + 1).apply(lambda x: 100 * (n - (n - np.argmax(x))) / n, raw=True)
    dn = l.rolling(n + 1, min_periods=n + 1).apply(lambda x: 100 * (n - (n - np.argmin(x))) / n, raw=True)
    return up.to_numpy(), dn.to_numpy()


def donchian(high, low, close, n=20):
    h = _s(high); l = _s(low)
    upper = h.shift(1).rolling(n, min_periods=n).max()
    lower = l.shift(1).rolling(n, min_periods=n).min()
    return lower.to_numpy(), upper.to_numpy()


def rolling_z(x, n=50):
    s = _s(x)
    m = s.rolling(n, min_periods=n).mean()
    sd = s.rolling(n, min_periods=n).std(ddof=0)
    return ((s - m) / sd.replace(0, np.nan)).to_numpy()


def cci(high, low, close, n=20):
    tp = (_s(high) + _s(low) + _s(close)) / 3
    ma = tp.rolling(n, min_periods=n).mean()
    md = tp.rolling(n, min_periods=n).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return ((tp - ma) / (0.015 * md.replace(0, np.nan))).to_numpy()


def williams_r(high, low, close, n=14):
    h = _s(high); l = _s(low); c = _s(close)
    hh = h.rolling(n, min_periods=n).max(); ll = l.rolling(n, min_periods=n).min()
    return (-100 * (hh - c) / (hh - ll).replace(0, np.nan)).to_numpy()


def mfi(high, low, close, volume, n=14):
    tp = (_s(high) + _s(low) + _s(close)) / 3
    rmf = tp * _s(volume)
    dtp = tp.diff()
    pos = rmf.where(dtp > 0, 0.0).rolling(n, min_periods=n).sum()
    neg = rmf.where(dtp < 0, 0.0).rolling(n, min_periods=n).sum()
    mr = pos / neg.replace(0, np.nan)
    return (100 - 100 / (1 + mr)).to_numpy()


def ema(close, n):
    return _s(close).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def macd(close, fast=12, slow=26, signal=9):
    ef = _s(close).ewm(span=fast, adjust=False, min_periods=fast).mean()
    es = _s(close).ewm(span=slow, adjust=False, min_periods=slow).mean()
    line = ef - es
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line.to_numpy(), sig.to_numpy()


def hammer(open_, high, low, close):
    o = np.asarray(open_, float); h = np.asarray(high, float)
    l = np.asarray(low, float); c = np.asarray(close, float)
    body = np.abs(c - o)
    lower = np.minimum(o, c) - l
    upper = h - np.maximum(o, c)
    rng = h - l
    ok = (body > 0) & (rng > 0)
    return ok & (lower >= 2 * body) & (upper <= body)


def bullish_engulfing(open_, close):
    o = np.asarray(open_, float); c = np.asarray(close, float)
    po = np.roll(o, 1); pc = np.roll(c, 1); po[0] = np.nan; pc[0] = np.nan
    prev_red = pc < po
    cur_green = c > o
    engulf = (o <= pc) & (c >= po)
    return prev_red & cur_green & engulf


def fvg_bull(high, low):
    h = np.asarray(high, float); l = np.asarray(low, float)
    out = np.zeros(len(h), bool)
    out[2:] = l[2:] > h[:-2]
    return out


def pivot_low(low, left=2, right=2):
    """قاع محوري مؤكَّد: low[i-right] أدنى من left يسار وright يمين. يُعلَّم عند i (بعد التأكيد)."""
    l = np.asarray(low, float); n = len(l)
    out = np.zeros(n, bool)
    for i in range(left + right, n):
        c = i - right
        if l[c] == np.min(l[c - left:c + right + 1]) and l[c] < l[c - 1] and l[c] < l[c + 1]:
            out[i] = True
    return out


def rsi_bull_divergence(low, close, n=14, lookback=20, left=2, right=2):
    """انحراف صعودي: عند تأكيد قاع محوري (i)، السعر يصنع قاعًا أدنى وRSI يصنع قاعًا أعلى مقارنة بآخر قاع محوري."""
    l = np.asarray(low, float); r = rsi(close, n)
    piv = pivot_low(low, left, right)
    n_ = len(l); out = np.zeros(n_, bool)
    last_pl_idx = None; last_pl_low = None; last_pl_rsi = None
    for i in range(n_):
        if piv[i]:
            c = i - right
            cur_low = l[c]; cur_rsi = r[c]
            if last_pl_idx is not None and (c - last_pl_idx) <= lookback:
                if cur_low < last_pl_low and not np.isnan(cur_rsi) and not np.isnan(last_pl_rsi) and cur_rsi > last_pl_rsi:
                    out[i] = True
            last_pl_idx, last_pl_low, last_pl_rsi = c, cur_low, cur_rsi
    return out
