# -*- coding: utf-8 -*-
"""L0045 — ترجمة آلة عشر فرضيات دخول (حرفياً من عقود history/hypotheses/فرضيات_الباحث_النهائي.txt).

كل دالة: تتلقى إطار 4h (open/high/low/close/volume) وترجع Series بوليانية محاذية للفهرس.
كل الشروط سببية (لا تنظر للأمام). لا تعديل على nova_v8/** — الدوال محلية هنا.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


# ───────────────────────── أساسيات ─────────────────────────
def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def std(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).std(ddof=0)


def atr_s(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df.high, df.low, df.close
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def rsi_w(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    lo = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + g / lo.replace(0, np.nan))


def bollinger(c: pd.Series, n: int = 20, k: float = 2.0):
    m = sma(c, n)
    sd = std(c, n)
    return m, m + k * sd, m - k * sd


def adx_di(df: pd.DataFrame, n: int = 14):
    h, l, c = df.high, df.low, df.close
    up, dn = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr_ = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1 / n, adjust=False).mean() / atr_
    mdi = 100 * mdm.ewm(alpha=1 / n, adjust=False).mean() / atr_
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), pdi, mdi


def psar_state(df: pd.DataFrame, af0: float = 0.02, afm: float = 0.2):
    """يرجع (sar, bull) — تنفيذ كلاسيكي متسلسل (Wilder)."""
    h = df.high.to_numpy(float); l = df.low.to_numpy(float)
    n = len(df)
    sar = np.full(n, np.nan); bull = np.zeros(n, dtype=bool)
    b = True; af = af0; ep = h[0]; sar[0] = l[0]; bull[0] = True
    for i in range(1, n):
        s = sar[i - 1] + af * (ep - sar[i - 1])
        if b:
            s = min(s, l[i - 1], l[max(i - 2, 0)])
            if l[i] < s:
                b = False; s = ep; ep = l[i]; af = af0
            elif h[i] > ep:
                ep = h[i]; af = min(af + af0, afm)
        else:
            s = max(s, h[i - 1], h[max(i - 2, 0)])
            if h[i] > s:
                b = True; s = ep; ep = h[i]; af = af0
            elif l[i] < ep:
                ep = l[i]; af = min(af + af0, afm)
        sar[i] = s; bull[i] = b
    return pd.Series(sar, index=df.index), pd.Series(bull, index=df.index)


def _shift_var(s: pd.Series, lag: np.ndarray) -> np.ndarray:
    """قيمة s عند الشمعة (i - lag[i]) — إزاحة متغيرة سببية."""
    v = s.to_numpy(float)
    idx = np.arange(len(v)) - lag
    ok = idx >= 0
    return np.where(ok, v[np.clip(idx, 0, len(v) - 1)], np.nan)


# ───────────────────────── الفرضيات العشر ─────────────────────────
def f046_band_walk(df: pd.DataFrame, adx_min: float = 25.0, bb_n: int = 20) -> pd.Series:
    """F-046 المشي على الحد العلوي: إغلاقان فوق العلوي + متوسط 20 صاعد + ADX>25."""
    c = df.close
    _, bu, _ = bollinger(c, bb_n, 2.0)
    s20 = sma(c, bb_n)
    adx, _, _ = adx_di(df, 14)
    sig = (c > bu) & (c.shift(1) > bu.shift(1)) & (s20 > s20.shift(5)) & (adx > adx_min)
    return sig.fillna(False)


def f007_squeeze(df: pd.DataFrame, sq_bars: int = 6, kc_mult: float = 1.5) -> pd.Series:
    """F-007 إطلاق TTM Squeeze: بولنجر داخل كيلتنر 6 شمعات ثم تحرر + زخم + حجم."""
    c, v = df.close, df.volume
    _, bu, bl = bollinger(c, 20, 2.0)
    mid = sma(c, 20)
    a = atr_s(df, 20)
    ku, kl = mid + kc_mult * a, mid - kc_mult * a
    inside = (bu < ku) & (bl > kl)
    sq = inside.shift(1).rolling(sq_bars, min_periods=sq_bars).sum() == sq_bars
    mom = c - c.shift(12)
    mom_up = (mom > 0) & (mom.shift(1) <= 0)
    vs = v.rolling(20, min_periods=20).mean()
    sig = sq.fillna(False) & (bu > ku) & mom_up & (c > bu) & (v > 1.5 * vs)
    return sig.fillna(False)


def f054_rsi_div(df: pd.DataFrame, look: int = 20, trig: float = 30.0) -> pd.Series:
    """F-054 دايفرجنس RSI: قاع أدنى قبل 5-15 شمعة، قاع أعلى الآن، RSI أعلى، وعبور فوق 30."""
    l, c = df.low, df.close
    r = rsi_w(c, 14)
    ll = l.rolling(look, min_periods=look).min()
    arg = l.rolling(look, min_periods=look).apply(lambda x: float(np.argmin(x)), raw=True)
    lag = ((look - 1) - arg).to_numpy(float)
    lag = np.where(np.isfinite(lag), lag, np.nan)
    bars_ok = (lag >= 5) & (lag <= 15)
    rsi_at = _shift_var(r, np.nan_to_num(lag, nan=0).astype(int))
    cross_up = (r > trig) & (r.shift(1) <= trig)
    sig = pd.Series(bars_ok & (l > ll).to_numpy() & (r.to_numpy() > rsi_at) &
                    cross_up.to_numpy(), index=df.index)
    return sig.fillna(False)


def f032_sar_flip(df: pd.DataFrame, adx_min: float = 20.0, sar_af: float = 0.02) -> pd.Series:
    """F-032 انقلاب SAR صاعداً + فوق EMA200 + ADX>20."""
    _, bull = psar_state(df, sar_af, 0.2)
    flip = bull & ~bull.shift(1, fill_value=False)
    adx, _, _ = adx_di(df, 14)
    sig = flip & (df.close > ema(df.close, 200)) & (adx > adx_min)
    return sig.fillna(False)


def f009_adx_ema21(df: pd.DataFrame, adx_min: float = 25.0, ema_pull: int = 21) -> pd.Series:
    """F-009 ترند ADX>25 و+DI>-DI مع ملامسة EMA21 والإغلاق فوقه."""
    adx, pdi, mdi = adx_di(df, 14)
    e21 = ema(df.close, ema_pull)
    sig = (adx > adx_min) & (pdi > mdi) & (df.low <= e21) & (df.close > e21)
    return sig.fillna(False)


def f074_double_bottom(df: pd.DataFrame, tol: float = 0.005, vol_mult: float = 1.5) -> pd.Series:
    """F-074 قاع مزدوج (بفاصل 10-60 شمعة وفرق ≤0.5%) ثم كسر خط العنق بحجم ≥1.5×."""
    h = df.high.to_numpy(float); l = df.low.to_numpy(float)
    c = df.close.to_numpy(float); v = df.volume.to_numpy(float)
    vs = df.volume.rolling(20, min_periods=20).mean().to_numpy(float)
    n = len(df)
    sig = np.zeros(n, dtype=bool)
    last_pivot = -1
    cand = None                      # (i_b, neckline)
    for i in range(4, n):
        j = i - 2                    # سوينغ مؤكد عند j بعد شمعتين (سببية)
        if j >= 4:
            if l[j] < l[j - 1] and l[j] < l[j + 1] and l[j] < l[j - 2] and l[j] < l[j - 3]:
                if last_pivot >= 0 and 10 <= j - last_pivot <= 60:
                    a, b = last_pivot, j
                    if abs(l[b] - l[a]) / l[a] <= tol:
                        cand = (b, float(h[a:b + 1].max()))
                last_pivot = j
        if cand is not None and i > cand[0] and c[i] > cand[1] and v[i] > vol_mult * vs[i]:
            sig[i] = True
            cand = None              # لقطة واحدة (لا تكرار على نفس النموذج)
    return pd.Series(sig, index=df.index)


def f069_morning_star(df: pd.DataFrame, mid_frac: float = 0.5, vol_mult: float = 1.2) -> pd.Series:
    """F-069 نجمة الصباح: حمراء قوية ثم جسم صغير ثم خضراء تغلق فوق منتصف الأولى + حجم."""
    o, c, h, l, v = df.open, df.close, df.high, df.low, df.volume
    rng = (h - l)
    body = (c - o).abs()
    c2 = (c.shift(2) < o.shift(2)) & (body.shift(2) > 0.6 * rng.shift(2))
    c1 = body.shift(1) < 0.3 * rng.shift(1)
    c0 = (c > o) & (c > (o.shift(2) + c.shift(2)) / 2 + mid_frac * 0 * rng)
    vs = v.rolling(20, min_periods=20).mean()
    sig = c2 & c1 & c0 & (v > vol_mult * vs)
    return sig.fillna(False)


def f013_ichimoku(df: pd.DataFrame, adx_min: float = 20.0, tenkan: int = 9, kijun: int = 26) -> pd.Series:
    """F-013 إيشيموكو: فوق الغيمة + تقاطع TK حديث (≤3) + SpanA>SpanB + close>close[-26] + ADX>20."""
    h, l, c = df.high, df.low, df.close
    ten = (h.rolling(tenkan, min_periods=tenkan).max() + l.rolling(tenkan, min_periods=tenkan).min()) / 2
    kij = (h.rolling(kijun, min_periods=kijun).max() + l.rolling(kijun, min_periods=kijun).min()) / 2
    sa = ((ten + kij) / 2).shift(kijun)
    sb = ((h.rolling(52, min_periods=52).max() + l.rolling(52, min_periods=52).min()) / 2).shift(26)
    top = pd.concat([sa, sb], axis=1).max(axis=1)
    tk_up = (ten > kij) & (ten.shift(1) <= kij.shift(1))
    tk_recent = tk_up.rolling(3, min_periods=1).max().astype(bool)
    adx, _, _ = adx_di(df, 14)
    sig = (c > top) & (c > sa) & (c > sb) & tk_recent & (sa > sb) & (c > c.shift(kijun)) & (adx > adx_min)
    return sig.fillna(False)


def f067_engulf_sma(df: pd.DataFrame, sma_lvl: int = 100, vol_mult: float = 1.2) -> pd.Series:
    """F-067 ابتلاع صاعد يلمس SMA100 + حجم ≥1.2×."""
    o, h, l, c, v = df.open, df.high, df.low, df.close, df.volume
    s100 = sma(c, sma_lvl)
    vs = v.rolling(20, min_periods=20).mean()
    sig = ((c.shift(1) < o.shift(1)) & (c > o) & (c >= o.shift(1)) & (o <= c.shift(1)) &
           (l <= s100) & (s100 <= h) & (v > vol_mult * vs))
    return sig.fillna(False)


def f130_fvg(df: pd.DataFrame, lookback: int = 8, min_atr: float = 0.05) -> pd.Series:
    """F-130 فجوة قيمة عادلة صاعدة غير معبأة: low[t] > high[t-2] خلال آخر 8 شموع،
    الفجوة ≥ 0.05×ATR، لا low لاحق ≤ المنتصف، والسعر الحالي فوق المنتصف."""
    h = df.high.to_numpy(float); l = df.low.to_numpy(float); c = df.close.to_numpy(float)
    a = atr_s(df, 14).to_numpy(float)
    n = len(df)
    sig = np.zeros(n, dtype=bool)
    for i in range(4, n):
        for t in range(i, max(i - lookback, 2) - 1, -1):   # الفجوة تكوّنت في آخر lookback شمعة
            if not np.isfinite(a[t]):
                continue
            gap = l[t] - h[t - 2]
            if gap <= 0 or gap < min_atr * a[t]:
                continue
            mid = (l[t] + h[t - 2]) / 2
            if np.any(l[t + 1:i + 1] <= mid):          # عُبّئت → ساقطة
                continue
            if c[i] > mid:
                sig[i] = True
            break
    return pd.Series(sig, index=df.index)


HYPOTHESES = [
    ("F-046", "المشي على الحد العلوي (ركوب الزخم)", f046_band_walk),
    ("F-007", "إطلاق TTM Squeeze مع انعكاس الزخم", f007_squeeze),
    ("F-054", "دايفرجنس RSI الصاعد الميكانيكي", f054_rsi_div),
    ("F-032", "انقلاب SAR مفلتر بـ EMA200 و ADX", f032_sar_flip),
    ("F-009", "ترند ADX قوي مع شراء ملامسة EMA21", f009_adx_ema21),
    ("F-074", "قاع مزدوج ميكانيكي + كسر العنق", f074_double_bottom),
    ("F-069", "نجمة الصباح ثلاثية الشموع", f069_morning_star),
    ("F-013", "إيشيموكو محاذاة كاملة مع ADX", f013_ichimoku),
    ("F-067", "ابتلاع صاعد على متوسط متحرك رئيسي", f067_engulf_sma),
    ("F-130", "فجوة القيمة العادلة الصاعدة الصالحة", f130_fvg),
]
