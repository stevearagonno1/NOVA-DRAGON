"""Module — market regime classification.

The regime is read from a HIGHER timeframe than the trade timeframe (per
design) and is forward-filled onto every 1m bar. The regime is fixed at the
moment of entry (does not change mid-trade) and used to pick the operating
mode (directional triggers vs grid vs avoid) and to group results.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from . import indicators as ind


def _classify_frame(df: pd.DataFrame) -> pd.Series:
    """Classify each higher-TF bar into one of the 4 regimes (causal)."""
    df = df.copy()
    atr = ind.wilder_atr(df, C.ATR_LEN)
    atr_sma100 = atr.rolling(100).mean()
    vr = (atr / atr_sma100.replace(0.0, np.nan)).to_numpy(float)
    adx = ind.adx(df, C.ADX_LEN).to_numpy(float)
    close = df.close.to_numpy(float)
    alma = ind.alma(df.close).to_numpy(float)
    hurst = ind.hurst_rolling(df.close).to_numpy(float)

    n = len(df)
    out = np.full(n, C.REGIME_CHOP, dtype=object)
    for i in range(n):
        if not np.isfinite(close[i]) or not np.isfinite(atr.iloc[i]):
            continue
        if np.isfinite(vr[i]) and vr[i] > C.VR_SHOCK:
            out[i] = C.REGIME_SHOCK
            continue
        adx_i = adx[i] if np.isfinite(adx[i]) else 0.0
        hst = hurst[i] if np.isfinite(hurst[i]) else 0.5
        al = alma[i] if np.isfinite(alma[i]) else close[i]
        if adx_i > C.ADX_TREND and close[i] > al and hst > 0.55:
            out[i] = C.REGIME_BULL
        elif adx_i > C.ADX_TREND and close[i] < al and hst > 0.55:
            out[i] = C.REGIME_BEAR
        else:
            out[i] = C.REGIME_CHOP
    return pd.Series(out, index=df.index)


def _hysteresis(arr, shock, min_bars):
    """Debounce a regime label series: a change only takes effect once the new
    label has persisted `min_bars` consecutive bars (anti-flicker). Shock still
    switches immediately (it is a safety state)."""
    n = len(arr)
    if n == 0:
        return []
    out = [None] * n
    keep = arr[0]
    out[0] = keep
    run_val, run_len = keep, 0
    for i in range(1, n):
        v = arr[i]
        if v == keep:
            run_val, run_len = v, 0
            out[i] = keep
            continue
        if v == shock:
            keep = v
            out[i] = v
            run_val, run_len = v, 0
            continue
        if v == run_val:
            run_len += 1
            if run_len >= min_bars:
                keep = v
                out[i] = v
                run_val, run_len = v, 0
            else:
                out[i] = keep
        else:
            run_val, run_len = v, 1
            out[i] = keep
    return out


def map_regime_to_1m(df1m: pd.DataFrame, tf: str = C.REGIME_TF) -> pd.Series:
    """Return a 1m-aligned regime series, WITHOUT look-ahead and debounced.

    A higher-TF bar (e.g. 15m starting 10:00 spanning 10:00-10:14) can only be
    *known* once it has fully closed, i.e. from the 10:15 1m bar onward. We
    therefore shift every higher-bar label forward by exactly one higher period
    before forward-filling onto the 1m timeline (no information leakage). The
    higher-TF labels are also debounced with hysteresis so a single stray bar
    can not flip the regime (Shock still applies immediately).

    df1m must be sorted ascending with a DatetimeIndex.
    """
    rule = {"5m": "5min", "15m": "15min"}.get(tf, tf)
    higher = ind.resample_higher(df1m, rule)
    if len(higher) < 260:
        # not enough higher bars to classify meaningfully -> all choppy
        return pd.Series(C.REGIME_CHOP, index=df1m.index)
    labels_np = _classify_frame(higher).to_numpy(dtype=object)
    labels_np = np.array(_hysteresis(labels_np, C.REGIME_SHOCK,
                                     C.REGIME_HYSTERESIS_BARS), dtype=object)
    # one higher period = most common gap between higher-bar starts
    diffs = pd.Series(higher.index).diff().dropna()
    period = diffs.mode().iloc[0] if len(diffs) else pd.Timedelta("1min")
    known_at = higher.index + period          # time a label first becomes usable
    s = pd.Series(labels_np, index=known_at, dtype=object)
    out = s.reindex(df1m.index, method="ffill").ffill().fillna(C.REGIME_CHOP)
    return out.astype(object)
