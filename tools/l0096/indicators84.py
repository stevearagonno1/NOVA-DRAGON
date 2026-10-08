#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0084-ENTRY-MIX — indicators library (executable 52-grid).

Port of the pinned executable 52-grid `history/hyp_lab/l0083_indicators.py`
@ 62f4d255e0fc6fce8e7c331a6349484ccb0b8fc0, reconciled line-by-line against
the L0084 paper section 5 (full textual definitions).  Every mask returns a
boolean array with True at decision bar i (decision at close i, fill at the
next contiguous open).  Purely causal: no centred/forward-looking input.

Additions required by L0084 (not in the L0083 library):
  - wilder_atr: TR=max(H-L,|H-Cprev|,|L-Cprev|), first TR=H-L, Wilder-14.
  - build_masks: the complete 52-setting catalogue in canonical order.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Canonical order == section 5 table order == Appendix B enumeration order.
SETTINGS_52 = [
    "Aroon14_bull_x", "Aroon25_bull_x",
    "BB20_2.0_reenter", "BB20_2.5_reenter", "BB20_3.0_reenter",
    "BullEngulfing", "CCI14_xup_-100", "CCI20_xup_-100",
    "Donchian10_break", "Donchian20_break", "Donchian20_fail",
    "Donchian55_break", "EMA_x_20_200", "EMA_x_20_50", "EMA_x_50_200",
    "FVG_single", "Hammer", "MACD_12_26_9_xup", "MACD_5_35_5_xup",
    "MFI14_xup_20", "PX_x_EMA200", "PX_x_EMA50",
    "RSI14_bull_divergence", "RSI14_xup_20", "RSI14_xup_25", "RSI14_xup_30",
    "RSI21_bull_divergence", "RSI21_xup_20", "RSI21_xup_25", "RSI21_xup_30",
    "RSI7_xup_20", "RSI7_xup_25", "RSI7_xup_30",
    "Stoch14_3_xup_15", "Stoch14_3_xup_20", "Stoch14_3_xup_25",
    "Stoch21_5_xup_15", "Stoch21_5_xup_20", "Stoch21_5_xup_25",
    "TakerRatioZ_ge_1.5", "TakerRatioZ_ge_2.0", "TakerRatioZ_ge_2.5",
    "TakerRatio_gt_0.48", "TakerRatio_gt_0.5", "TakerRatio_gt_0.52",
    "TakerRatio_gt_0.55",
    "VolSpike_z1.5", "VolSpike_z2.0", "VolSpike_z2.5", "VolSpike_z3.0",
    "WilliamsR14_xup_-80", "WilliamsR21_xup_-80",
]
assert len(SETTINGS_52) == 52
assert len(set(SETTINGS_52)) == 52


def _s(a):
    return pd.Series(a, dtype="float64")


# --------------------------------------------------------------------------
# series primitives (verbatim semantics of the pinned 52-grid)
# --------------------------------------------------------------------------
def rsi(close, n=14):
    c = _s(close)
    d = c.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    ru = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rd = dn.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = ru / rd.replace(0, np.nan)          # D=0 => NaN => false, never 100
    out = 100 - 100 / (1 + rs)
    return out.to_numpy()


def cross_up_through(series, thr):
    a = np.asarray(series, float)
    prev = np.roll(a, 1)
    prev[0] = np.nan                          # first previous is invalid
    return (prev < thr) & (a >= thr)


def cross_down_through(series, thr):
    a = np.asarray(series, float)
    prev = np.roll(a, 1)
    prev[0] = np.nan
    return (prev > thr) & (a <= thr)


def cross_above(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    pa = np.roll(a, 1)
    pb = np.roll(b, 1)
    pa[0] = np.nan
    pb[0] = np.nan
    return (pa <= pb) & (a > b)


def stochastic(high, low, close, n=14, d=3):
    h = _s(high)
    l = _s(low)
    c = _s(close)
    ll = l.rolling(n, min_periods=n).min()
    hh = h.rolling(n, min_periods=n).max()
    k = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    dd = k.rolling(d, min_periods=d).mean()
    return k.to_numpy(), dd.to_numpy()


def bollinger(close, n=20, k=2.0):
    c = _s(close)
    mid = c.rolling(n, min_periods=n).mean()
    sd = c.rolling(n, min_periods=n).std(ddof=0)     # population std
    lower = mid - k * sd
    upper = mid + k * sd
    return lower.to_numpy(), mid.to_numpy(), upper.to_numpy()


def aroon(high, low, n=14):
    h = _s(high)
    l = _s(low)
    up = h.rolling(n + 1, min_periods=n + 1).apply(
        lambda x: 100 * (n - (n - np.argmax(x))) / n, raw=True)
    dn = l.rolling(n + 1, min_periods=n + 1).apply(
        lambda x: 100 * (n - (n - np.argmin(x))) / n, raw=True)
    return up.to_numpy(), dn.to_numpy()


def donchian(high, low, close, n=20):
    h = _s(high)
    l = _s(low)
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
    md = tp.rolling(n, min_periods=n).apply(
        lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return ((tp - ma) / (0.015 * md.replace(0, np.nan))).to_numpy()


def williams_r(high, low, close, n=14):
    h = _s(high)
    l = _s(low)
    c = _s(close)
    hh = h.rolling(n, min_periods=n).max()
    ll = l.rolling(n, min_periods=n).min()
    return (-100 * (hh - c) / (hh - ll).replace(0, np.nan)).to_numpy()


def mfi(high, low, close, volume, n=14):
    tp = (_s(high) + _s(low) + _s(close)) / 3
    rmf = tp * _s(volume)
    dtp = tp.diff()
    pos = rmf.where(dtp > 0, 0.0).rolling(n, min_periods=n).sum()
    neg = rmf.where(dtp < 0, 0.0).rolling(n, min_periods=n).sum()
    mr = pos / neg.replace(0, np.nan)         # zero negative => NaN
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
    o = np.asarray(open_, float)
    h = np.asarray(high, float)
    l = np.asarray(low, float)
    c = np.asarray(close, float)
    body = np.abs(c - o)
    lower = np.minimum(o, c) - l
    upper = h - np.maximum(o, c)
    rng = h - l
    ok = (body > 0) & (rng > 0)
    return ok & (lower >= 2 * body) & (upper <= body)


def bullish_engulfing(open_, close):
    o = np.asarray(open_, float)
    c = np.asarray(close, float)
    po = np.roll(o, 1)
    pc = np.roll(c, 1)
    po[0] = np.nan
    pc[0] = np.nan
    prev_red = pc < po
    cur_green = c > o
    engulf = (o <= pc) & (c >= po)
    return prev_red & cur_green & engulf


def fvg_bull(high, low):
    h = np.asarray(high, float)
    l = np.asarray(low, float)
    out = np.zeros(len(h), bool)
    out[2:] = l[2:] > h[:-2]
    return out


def pivot_low(low, left=2, right=2):
    """Confirmed pivot low. Emitted at i = c + right (never at c)."""
    l = np.asarray(low, float)
    n = len(l)
    out = np.zeros(n, bool)
    for i in range(left + right, n):
        c = i - right
        if (l[c] == np.min(l[c - left:c + right + 1])
                and l[c] < l[c - 1] and l[c] < l[c + 1]):
            out[i] = True
    return out


def rsi_bull_divergence(low, close, n=14, lookback=20, left=2, right=2):
    """Bullish RSI divergence between successive confirmed pivots.

    Previous pivot is updated at EVERY confirmed pivot; emission only when
    current pivot low is strictly lower and RSI strictly higher+finite and
    (c - prev_c) <= lookback.
    """
    l = np.asarray(low, float)
    r = rsi(close, n)
    piv = pivot_low(low, left, right)
    n_ = len(l)
    out = np.zeros(n_, bool)
    last_pl_idx = None
    last_pl_low = None
    last_pl_rsi = None
    for i in range(n_):
        if piv[i]:
            c = i - right
            cur_low = l[c]
            cur_rsi = r[c]
            if last_pl_idx is not None and (c - last_pl_idx) <= lookback:
                if (cur_low < last_pl_low
                        and not np.isnan(cur_rsi) and not np.isnan(last_pl_rsi)
                        and cur_rsi > last_pl_rsi):
                    out[i] = True
            last_pl_idx, last_pl_low, last_pl_rsi = c, cur_low, cur_rsi
    return out


def wilder_atr(high, low, close, n=14):
    """ATR-14 Wilder: TR=max(H-L,|H-Cprev|,|L-Cprev|); first TR=H-L.

    alpha=1/n, adjust=False, min_periods=n (first ATR readable at bar n-1).
    """
    h = _s(high)
    l = _s(low)
    pc = _s(close).shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    tr.iloc[0] = (h - l).iloc[0]                 # first TR = H-L exactly
    atr = tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    return atr.to_numpy()


# --------------------------------------------------------------------------
# the complete 52-setting catalogue
# --------------------------------------------------------------------------
def build_masks(d):
    """d: dict of arrays o,h,l,c,v,tbv (floats).  Returns {name: bool array}.

    Definition order and formulas identical to the pinned executable 52-grid.
    """
    o, h, l, c, v, tbv = (d["o"], d["h"], d["l"], d["c"], d["v"], d["tbv"])
    S = {}
    for per in (7, 14, 21):
        r = rsi(c, per)
        for thr in (20, 25, 30):
            S[f"RSI{per}_xup_{thr}"] = cross_up_through(r, thr)
    for (n, dd) in ((14, 3), (21, 5)):
        k, _ = stochastic(h, l, c, n, dd)
        for thr in (15, 20, 25):
            S[f"Stoch{n}_{dd}_xup_{thr}"] = cross_up_through(k, thr)
    for k in (2.0, 2.5, 3.0):
        low_b, _, _ = bollinger(c, 20, k)
        S[f"BB20_{k}_reenter"] = cross_above(c, low_b)
    for (a, b) in ((20, 50), (50, 200), (20, 200)):
        S[f"EMA_x_{a}_{b}"] = cross_above(ema(c, a), ema(c, b))
    for p in (50, 200):
        S[f"PX_x_EMA{p}"] = cross_above(c, ema(c, p))
    for (f, s, sg) in ((12, 26, 9), (5, 35, 5)):
        ml, sl = macd(c, f, s, sg)
        S[f"MACD_{f}_{s}_{sg}_xup"] = cross_above(ml, sl)
    for n in (14, 25):
        au, ad = aroon(h, l, n)
        S[f"Aroon{n}_bull_x"] = cross_above(au, ad)
    for n in (10, 20, 55):
        lo, up = donchian(h, l, c, n)
        S[f"Donchian{n}_break"] = np.asarray(c, float) > up      # state
    lo, up = donchian(h, l, c, 20)
    S["Donchian20_fail"] = ((np.asarray(h, float) > up)
                            & (np.asarray(c, float) <= up))
    vz = rolling_z(v, 50)
    for z in (1.5, 2.0, 2.5, 3.0):
        S[f"VolSpike_z{z}"] = vz >= z
    v_arr = np.asarray(v, float)
    ratio = np.divide(np.asarray(tbv, float), v_arr,
                      out=np.full(len(v_arr), np.nan), where=v_arr > 0)
    for thr in (0.48, 0.50, 0.52, 0.55):
        S[f"TakerRatio_gt_{thr}"] = ratio > thr
    rz = rolling_z(ratio, 50)
    for z in (1.5, 2.0, 2.5):
        S[f"TakerRatioZ_ge_{z}"] = rz >= z
    for n in (14, 20):
        S[f"CCI{n}_xup_-100"] = cross_up_through(cci(h, l, c, n), -100)
    for n in (14, 21):
        S[f"WilliamsR{n}_xup_-80"] = cross_up_through(williams_r(h, l, c, n), -80)
    for n in (14,):
        S[f"MFI{n}_xup_20"] = cross_up_through(mfi(h, l, c, v, n), 20)
    S["Hammer"] = hammer(o, h, l, c)
    S["BullEngulfing"] = bullish_engulfing(o, c)
    S["FVG_single"] = fvg_bull(h, l)
    for per in (14, 21):
        S[f"RSI{per}_bull_divergence"] = rsi_bull_divergence(l, c, per)
    # canonical order + exact 52 membership
    assert set(S) == set(SETTINGS_52), sorted(set(S) ^ set(SETTINGS_52))
    return {name: np.asarray(S[name], dtype=bool) for name in SETTINGS_52}


# --------------------------------------------------------------------------
# name-driven construction (used by neighbour perturbation): rebuild any
# setting mask from its name alone; equivalence to build_masks is tested.
# --------------------------------------------------------------------------
def build_one(d, name):
    """Mask for one setting name (possibly perturbed); same primitives."""
    import re
    o, h, l, c, v, tbv = (d["o"], d["h"], d["l"], d["c"], d["v"], d["tbv"])
    o = np.asarray(o, float); h = np.asarray(h, float)
    l = np.asarray(l, float); c = np.asarray(c, float)
    v = np.asarray(v, float); tbv = np.asarray(tbv, float)
    def f(t):
        return float(t)
    m = re.fullmatch(r"RSI(\d+)_xup_(-?\d+)", name)
    if m:
        return cross_up_through(rsi(c, int(m.group(1))), f(m.group(2)))
    m = re.fullmatch(r"RSI(\d+)_bull_divergence", name)
    if m:
        return rsi_bull_divergence(l, c, int(m.group(1)))
    m = re.fullmatch(r"Stoch(\d+)_(\d+)_xup_(\d+)", name)
    if m:
        k, _ = stochastic(h, l, c, int(m.group(1)), int(m.group(2)))
        return cross_up_through(k, f(m.group(3)))
    m = re.fullmatch(r"BB(\d+)_([\d.]+)_reenter", name)
    if m:
        low_b, _, _ = bollinger(c, int(m.group(1)), f(m.group(2)))
        return cross_above(c, low_b)
    m = re.fullmatch(r"EMA_x_(\d+)_(\d+)", name)
    if m:
        return cross_above(ema(c, int(m.group(1))), ema(c, int(m.group(2))))
    m = re.fullmatch(r"PX_x_EMA(\d+)", name)
    if m:
        return cross_above(c, ema(c, int(m.group(1))))
    m = re.fullmatch(r"MACD_(\d+)_(\d+)_(\d+)_xup", name)
    if m:
        ml, sl = macd(c, int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return cross_above(ml, sl)
    m = re.fullmatch(r"Aroon(\d+)_bull_x", name)
    if m:
        au, ad = aroon(h, l, int(m.group(1)))
        return cross_above(au, ad)
    m = re.fullmatch(r"Donchian(\d+)_break", name)
    if m:
        _lo, up = donchian(h, l, c, int(m.group(1)))
        return np.asarray(c, float) > up
    m = re.fullmatch(r"Donchian(\d+)_fail", name)
    if m:
        _lo, up = donchian(h, l, c, int(m.group(1)))
        return (np.asarray(h, float) > up) & (np.asarray(c, float) <= up)
    m = re.fullmatch(r"VolSpike_z([\d.]+)", name)
    if m:
        return rolling_z(v, 50) >= f(m.group(1))
    m = re.fullmatch(r"TakerRatio_gt_([\d.]+)", name)
    if m:
        ratio = np.divide(tbv, v, out=np.full(len(v), np.nan), where=v > 0)
        return ratio > f(m.group(1))
    m = re.fullmatch(r"TakerRatioZ_ge_([\d.]+)", name)
    if m:
        ratio = np.divide(tbv, v, out=np.full(len(v), np.nan), where=v > 0)
        return rolling_z(ratio, 50) >= f(m.group(1))
    m = re.fullmatch(r"CCI(\d+)_xup_(-?\d+)", name)
    if m:
        return cross_up_through(cci(h, l, c, int(m.group(1))), f(m.group(2)))
    m = re.fullmatch(r"WilliamsR(\d+)_xup_(-?\d+)", name)
    if m:
        return cross_up_through(williams_r(h, l, c, int(m.group(1))),
                                f(m.group(2)))
    m = re.fullmatch(r"MFI(\d+)_xup_(\d+)", name)
    if m:
        return cross_up_through(mfi(h, l, c, v, int(m.group(1))),
                                f(m.group(2)))
    if name == "Hammer":
        return hammer(o, h, l, c)
    if name == "BullEngulfing":
        return bullish_engulfing(o, c)
    if name == "FVG_single":
        return fvg_bull(h, l)
    raise KeyError(f"unrecognised setting name: {name}")


def numeric_tokens(name):
    """Numeric tokens of a setting name as [(text, value, kind, decimals)].

    kind: 'period' (integer bars), 'threshold' or 'band' (multiplicative),
    'z' (z-score threshold).  Structural names return [].
    """
    import re
    out = []
    pats = [
        (r"^RSI(\d+)_xup_(-?\d+)$", ["period", "threshold"]),
        (r"^RSI(\d+)_bull_divergence$", ["period"]),
        (r"^Stoch(\d+)_(\d+)_xup_(\d+)$", ["period", "period", "threshold"]),
        (r"^BB(\d+)_([\d.]+)_reenter$", ["period", "band"]),
        (r"^EMA_x_(\d+)_(\d+)$", ["period", "period"]),
        (r"^PX_x_EMA(\d+)$", ["period"]),
        (r"^MACD_(\d+)_(\d+)_(\d+)_xup$", ["period", "period", "period"]),
        (r"^Aroon(\d+)_bull_x$", ["period"]),
        (r"^Donchian(\d+)_(break|fail)$", ["period"]),
        (r"^VolSpike_z([\d.]+)$", ["z"]),
        (r"^TakerRatio_gt_([\d.]+)$", ["threshold"]),
        (r"^TakerRatioZ_ge_([\d.]+)$", ["z"]),
        (r"^CCI(\d+)_xup_(-?\d+)$", ["period", "threshold"]),
        (r"^WilliamsR(\d+)_xup_(-?\d+)$", ["period", "threshold"]),
        (r"^MFI(\d+)_xup_(\d+)$", ["period", "threshold"]),
    ]
    for pat, kinds in pats:
        m = re.fullmatch(pat, name)
        if m:
            for txt, kind in zip(m.groups(), kinds):
                dec = len(txt.split(".")[1]) if "." in txt else 0
                out.append((txt, float(txt), kind, dec))
            return out
    return out


def perturb_name(name, idx, factor):
    """Perturb numeric token idx of a setting name by factor (+-20% steps).

    Periods are rounded half-up with a minimum of two; thresholds/bands keep
    their original decimal precision.  Returns (new_name, spec) or (None,
    spec) when the perturbation is invalid (ordering broken or unchanged).
    """
    import re
    toks = numeric_tokens(name)
    if idx >= len(toks):
        return None, {"reason": "no such numeric token"}
    txt, val, kind, dec = toks[idx]
    new_val = val * factor
    if kind == "period":
        new_val = int(np.floor(new_val + 0.5))
        if new_val < 2:
            new_val = 2
        new_txt = str(new_val)
    else:
        new_val = round(new_val + 0.0, dec) if dec else int(np.floor(new_val + 0.5))
        new_txt = f"{new_val:.{dec}f}" if dec else str(new_val)
    spec = {"index": idx, "old": val, "new": new_val, "kind": kind,
            "factor": factor}
    if new_txt == txt:
        spec["reason"] = "rounds to the same value"
        return None, spec
    # rebuild the name with the token replaced
    spans = [m.span() for m in re.finditer(r"-?\d+(?:\.\d+)?", name)]
    if idx >= len(spans):
        return None, {"reason": "span mismatch"}
    a, b = spans[idx]
    new_name = name[:a] + new_txt + name[b:]
    # keep fast < slow for EMA / MACD
    if new_name.startswith("EMA_x_") or new_name.startswith("MACD_"):
        nums = [float(t) for t in re.findall(r"\d+(?:\.\d+)?", new_name)]
        if new_name.startswith("EMA_x_") and not (nums[0] < nums[1]):
            return None, {"reason": "fast>=slow", **spec}
        if new_name.startswith("MACD_") and not (nums[0] < nums[1]):
            return None, {"reason": "fast>=slow", **spec}
    return new_name, spec
