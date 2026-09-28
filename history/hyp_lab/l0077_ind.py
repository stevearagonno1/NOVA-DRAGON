"""L0077 expanded candidate conditions — LEVEL agreement at decision bar i, using the
REGISTERED math & thresholds from history/hyp_lab/l0072_ind.py (verified against
docs/lanes/L0072-VERDICT.md). All causal: value at i uses data <= i (lo20/hi20 use
shift(1) => completed bars < i). Definitions frozen in preregistration_l0077.json.
"""
import numpy as np, pandas as pd

FAMILIES = {
    "A_liquidity_flow": ["OBV", "MFI14", "CMF14", "CMF20"],
    "B_price_candle_reversal": ["BollingerZ", "RSI2", "RSI14", "Stochastic", "TurtleSoup"],
    "C_trend_momentum_breakout": ["MACD", "EMA20_50", "EMA200", "ADX_DI", "Donchian"],
}
ALL_CANDIDATES = [c for lst in FAMILIES.values() for c in lst]


def _wilder(x, n):
    out = np.full(len(x), np.nan); s = np.nan
    for i, v in enumerate(x):
        if np.isnan(v):
            continue
        s = v if np.isnan(s) else s + (v - s) / n
        out[i] = s
    return out


def _rsi(c, n):
    d = np.diff(c, prepend=np.nan)
    up = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    up[0] = dn[0] = np.nan
    au, ad = _wilder(up, n), _wilder(dn, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + au / ad)
    return np.where(ad == 0, 100.0, r)


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def candidate_conditions(df):
    """Return {(name, dir): bool ndarray} for the 14 expanded candidates (dir in {1,-1})."""
    S = pd.Series
    o = df.open.to_numpy(float); h = df.high.to_numpy(float)
    l = df.low.to_numpy(float); c = df.close.to_numpy(float); v = df.volume.to_numpy(float)

    rsi2 = _rsi(c, 2); rsi14 = _rsi(c, 14)
    ll14 = S(l).rolling(14).min().to_numpy(); hh14 = S(h).rolling(14).max().to_numpy()
    raw = 100 * (c - ll14) / np.where(hh14 - ll14 == 0, np.nan, hh14 - ll14)
    k = S(raw).rolling(3).mean().to_numpy(); d = S(k).rolling(3).mean().to_numpy()
    tp = (h + l + c) / 3; mf = tp * v; dtp = np.diff(tp, prepend=np.nan)
    pos = S(np.where(dtp > 0, mf, 0.0)).rolling(14).sum().to_numpy()
    neg = S(np.where(dtp < 0, mf, 0.0)).rolling(14).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        mfi = np.where(neg == 0, 100.0, 100 - 100 / (1 + pos / neg))
    macd_line = _ema(c, 12) - _ema(c, 26)
    e20, e50, e200 = _ema(c, 20), _ema(c, 50), _ema(c, 200)
    pc = np.r_[np.nan, c[:-1]]; ph = np.r_[np.nan, h[:-1]]; pl = np.r_[np.nan, l[:-1]]
    upm, dnm = h - ph, pl - l
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0); ndm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    pdm[0] = ndm[0] = tr[0] = np.nan
    atr = _wilder(tr, 14)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100 * _wilder(pdm, 14) / atr; ndi = 100 * _wilder(ndm, 14) / atr
        dx = 100 * np.abs(pdi - ndi) / (pdi + ndi)
    adx = _wilder(dx, 14)
    obv = np.cumsum(np.sign(np.diff(c, prepend=c[0])) * v); obv_e = _ema(obv, 20)
    with np.errstate(divide="ignore", invalid="ignore"):
        mfm = np.where(h - l == 0, 0.0, ((c - l) - (h - c)) / (h - l))
    cmf14 = (S(mfm * v).rolling(14).sum().to_numpy()) / (S(v).rolling(14).sum().to_numpy())
    cmf20 = (S(mfm * v).rolling(20).sum().to_numpy()) / (S(v).rolling(20).sum().to_numpy())
    m20 = S(c).rolling(20).mean().to_numpy(); sd20 = S(c).rolling(20).std(ddof=0).to_numpy()
    z = (c - m20) / np.where(sd20 == 0, np.nan, sd20)
    lo20 = S(l).shift(1).rolling(20).min().to_numpy()
    hi20 = S(h).shift(1).rolling(20).max().to_numpy()

    def b(x):
        return np.asarray(x, dtype=bool)

    cond = {}
    # Family A
    cond[("OBV", 1)] = b(obv > obv_e); cond[("OBV", -1)] = b(obv < obv_e)
    cond[("MFI14", 1)] = b(mfi < 20); cond[("MFI14", -1)] = b(mfi > 80)
    cond[("CMF14", 1)] = b(cmf14 > 0); cond[("CMF14", -1)] = b(cmf14 < 0)
    cond[("CMF20", 1)] = b(cmf20 > 0); cond[("CMF20", -1)] = b(cmf20 < 0)
    # Family B
    cond[("BollingerZ", 1)] = b(z <= -2); cond[("BollingerZ", -1)] = b(z >= 2)
    cond[("RSI2", 1)] = b(rsi2 < 15); cond[("RSI2", -1)] = b(rsi2 > 85)
    cond[("RSI14", 1)] = b(rsi14 < 30); cond[("RSI14", -1)] = b(rsi14 > 70)
    cond[("Stochastic", 1)] = b((k > d) & (k < 20)); cond[("Stochastic", -1)] = b((k < d) & (k > 80))
    cond[("TurtleSoup", 1)] = b((l < lo20) & (c > lo20)); cond[("TurtleSoup", -1)] = b((h > hi20) & (c < hi20))
    # Family C
    cond[("MACD", 1)] = b(macd_line > 0); cond[("MACD", -1)] = b(macd_line < 0)
    cond[("EMA20_50", 1)] = b(e20 > e50); cond[("EMA20_50", -1)] = b(e20 < e50)
    cond[("EMA200", 1)] = b(c > e200); cond[("EMA200", -1)] = b(c < e200)
    cond[("ADX_DI", 1)] = b((pdi > ndi) & (adx >= 20)); cond[("ADX_DI", -1)] = b((ndi > pdi) & (adx >= 20))
    cond[("Donchian", 1)] = b(c > hi20); cond[("Donchian", -1)] = b(c < lo20)
    # NaN in comparisons -> False already (numpy), ensure no NaN leaked as True
    return cond
