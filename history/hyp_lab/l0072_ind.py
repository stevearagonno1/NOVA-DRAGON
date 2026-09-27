"""L0072 indicator triggers (causal: values at bar i use data up to close of i only)."""
import numpy as np, pandas as pd
import l0072_core as C

_IND = {}


def rsi(c, n):
    d = np.diff(c, prepend=np.nan); up = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    up[0] = dn[0] = np.nan
    au, ad = C.wilder(up, n), C.wilder(dn, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + au / ad)
    return np.where(ad == 0, 100.0, r)


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def ind(sym):
    if sym in _IND: return _IND[sym]
    P = C.prep(sym); o, h, l, c, v = P["o"], P["h"], P["l"], P["c"], P["v"]
    S = pd.Series; I = {}
    I["rsi2"], I["rsi14"] = rsi(c, 2), rsi(c, 14)
    ll, hh = S(l).rolling(14).min().to_numpy(), S(h).rolling(14).max().to_numpy()
    raw = 100 * (c - ll) / np.where(hh - ll == 0, np.nan, hh - ll)
    I["k"] = S(raw).rolling(3).mean().to_numpy(); I["d"] = S(I["k"]).rolling(3).mean().to_numpy()
    tp = (h + l + c) / 3; mf = tp * v; dtp = np.diff(tp, prepend=np.nan)
    pos = S(np.where(dtp > 0, mf, 0.0)).rolling(14).sum().to_numpy(); neg = S(np.where(dtp < 0, mf, 0.0)).rolling(14).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        I["mfi"] = np.where(neg == 0, 100.0, 100 - 100 / (1 + pos / neg))
    I["macd"] = ema(c, 12) - ema(c, 26)
    I["e20"], I["e50"], I["e200"] = ema(c, 20), ema(c, 50), ema(c, 200)
    pc = np.r_[np.nan, c[:-1]]; ph = np.r_[np.nan, h[:-1]]; pl = np.r_[np.nan, l[:-1]]
    upm, dnm = h - ph, pl - l
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0); ndm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1); pdm[0] = ndm[0] = tr[0] = np.nan
    atr = C.wilder(tr, 14)
    with np.errstate(divide="ignore", invalid="ignore"):
        I["pdi"] = 100 * C.wilder(pdm, 14) / atr; I["ndi"] = 100 * C.wilder(ndm, 14) / atr
        dx = 100 * np.abs(I["pdi"] - I["ndi"]) / (I["pdi"] + I["ndi"])
    I["adx"] = C.wilder(dx, 14)
    obv = np.cumsum(np.sign(np.diff(c, prepend=c[0])) * v); I["obv"] = obv; I["obv_e"] = ema(obv, 20)
    with np.errstate(divide="ignore", invalid="ignore"):
        mfm = np.where(h - l == 0, 0.0, ((c - l) - (h - c)) / (h - l))
    for n in (14, 20):
        I[f"cmf{n}"] = S(mfm * v).rolling(n).sum().to_numpy() / S(v).rolling(n).sum().to_numpy()
    m20, sd20 = S(c).rolling(20).mean().to_numpy(), S(c).rolling(20).std(ddof=0).to_numpy()
    I["bbl"] = m20 - 2 * sd20; I["z"] = (c - m20) / np.where(sd20 == 0, np.nan, sd20)
    for n in (20, 55):
        I[f"lo{n}"] = S(l).shift(1).rolling(n).min().to_numpy()   # completed bars before i
    I["hi20"] = S(h).shift(1).rolling(20).max().to_numpy()
    _IND[sym] = I
    return I


def xup(a, b, i):
    return a[i - 1] <= b[i - 1] and a[i] > b[i] if np.isscalar(b) is False else a[i - 1] <= b and a[i] > b


def trig(name, I, P, i, thr):
    c, l = P["c"], P["l"]
    def up(a, t): return a[i - 1] <= t and a[i] > t
    def dn(a, t): return a[i - 1] > t and a[i] <= t
    if name == "I01": return up(I["rsi2"], thr or 15)
    if name == "I02": return up(I["rsi14"], thr or 30)
    if name == "I03": return I["k"][i - 1] <= I["d"][i - 1] and I["k"][i] > I["d"][i] and I["k"][i] <= (thr or 20)
    if name == "I04": return up(I["mfi"], 20)
    if name == "I05": return up(I["macd"], 0)
    if name == "I06": return I["e20"][i - 1] <= I["e50"][i - 1] and I["e20"][i] > I["e50"][i]
    if name == "I07": return c[i - 1] <= I["e200"][i - 1] and c[i] > I["e200"][i]
    if name == "I08": return I["pdi"][i - 1] <= I["ndi"][i - 1] and I["pdi"][i] > I["ndi"][i] and I["adx"][i] >= (thr or 20)
    if name == "I09": return I["obv"][i - 1] <= I["obv_e"][i - 1] and I["obv"][i] > I["obv_e"][i]
    if name == "I10": a = I[f"cmf{thr or 20}"]; return up(a, 0)
    if name == "I11": return c[i - 1] < I["bbl"][i - 1] and c[i] >= I["bbl"][i]
    if name == "I12": return up(I["z"], thr or -2)
    if name == "I13": L = I[f"lo{thr or 20}"][i]; return l[i] < L and c[i] > L
    if name == "I14": return c[i] > I["hi20"][i] and c[i - 1] <= I["hi20"][i - 1]
    # first-touch controls
    if name == "F01": return dn(I["rsi2"], thr or 15)
    if name == "F02": return dn(I["rsi14"], 30)
    if name == "F03": return dn(I["k"], 20)
    if name == "F04": return dn(I["mfi"], 20)
    if name == "F11": return c[i - 1] >= I["bbl"][i - 1] and c[i] < I["bbl"][i]
    if name == "F12": return dn(I["z"], -2)
    if name == "F13": return l[i] < I["lo20"][i]
    raise KeyError(name)


NAMES = [f"I{k:02d}" for k in range(1, 15)]
FT = {"I01": "F01", "I02": "F02", "I03": "F03", "I04": "F04", "I11": "F11", "I12": "F12", "I13": "F13"}


def make_sigfn(names, thr=None):
    names = [names] if isinstance(names, str) else list(names)

    def fn(sym, cfg):
        P = C.prep(sym); I = ind(sym); n = len(P["c"])
        hc = P["ctx"]["hc120"]; dclose = P["ctx"]["close"]; out = []; mh_last = None
        for i in range(1, n):
            j = i - 2
            if j >= 2 and P["mph"][j]: mh_last = P["h"][j]
            if not P["valid"][i] or np.isnan(hc[i]): continue
            dd = 1 - dclose[i] / hc[i]
            if dd < 0.25: continue
            hit = None
            with np.errstate(invalid="ignore"):
                for nm in names:
                    try:
                        ok = bool(trig(nm, I, P, i, thr))
                    except (FloatingPointError, IndexError):
                        ok = False
                    if ok: hit = nm; break
            if hit is None: continue
            out.append(dict(sym=sym, sweep_bar=i, conf_bar=i, level=float(P["l"][i]), kind=hit, sl=float(P["l"][i]),
                            sh=float(P["h"][i]), conf_high=float(P["h"][i]), dd=float(dd), regime=int(P["regime"][i]),
                            mss_px=mh_last, mss=False, ext=0.0, vol_ok=True, reject="", stop_from_fill=True))
        return out
    return fn
