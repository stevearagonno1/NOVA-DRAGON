# -*- coding: utf-8 -*-
"""[L0019] مؤشرات مشتركة لدفعة الجرد الثانية — كود جديد مستقل، لا يلمس أي مرجع قائم.

كل دالة تُحسب لسببية كاملة (لا تسرّب مستقبل): الإشارة عند إغلاق الشمعة فقط.
الاصطلاحات حرفيًا من دليل الرموز في `history/hypotheses/فرضيات_الباحث_النهائي.txt`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def wilder(s: pd.Series, n: int) -> pd.Series:
    """تنعيم ويلدر (EMA بمعامل alpha=1/n) — اصطلاح ADX/RSI الكلاسيكي."""
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, np.nan))


def adx(df: pd.DataFrame, period: int) -> pd.Series:
    """ADX ويلدر: تنعيم TR/+DM/−DM ثم DX ثم متوسطه."""
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    up = h.diff()
    dn = -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr_n = wilder(tr, period)
    plus_di = 100.0 * wilder(plus_dm, period) / atr_n.replace(0, np.nan)
    minus_di = 100.0 * wilder(minus_dm, period) / atr_n.replace(0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return wilder(dx, period)


def vol_sma(volume: pd.Series, n: int = 20) -> pd.Series:
    return volume.rolling(n, min_periods=n).mean()


def bb(close: pd.Series, period: int, mult: float):
    """بولنجر: (الأوسط، العلوي، السفلي، عرض النطاق). StdDev بمقام n (ddof=0)."""
    mid = close.rolling(period, min_periods=period).mean()
    sd = close.rolling(period, min_periods=period).std(ddof=0)
    upper = mid + mult * sd
    lower = mid - mult * sd
    bw = (upper - lower) / mid.replace(0, np.nan)
    return mid, upper, lower, bw


def keltner(df: pd.DataFrame, period: int, mult: float, atr_s: pd.Series):
    """كيلتنر: EMA(period) ± mult×ATR(period) — ATR يُمرَّر (عقد common.atr)."""
    mid = df["close"].ewm(span=period, adjust=False).mean()
    return mid + mult * atr_s, mid - mult * atr_s


def vwap_utc(df: pd.DataFrame) -> pd.Series:
    """VWAP تراكمي من بداية اليوم UTC (typical=(h+l+c)/3) — يُصفَّر كل 00:00 UTC.

    وكيل موثق: بياناتنا شمعية بلا دفتر أوامر، فـVWAP هنا من الشموع لا من الصفقات.
    """
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = (tp * df["volume"]).groupby(df.index.floor("D")).cumsum()
    vv = df["volume"].groupby(df.index.floor("D")).cumsum()
    return pv / vv.replace(0, np.nan)


def day_rank(df: pd.DataFrame) -> pd.Series:
    """رتبة الشمعة داخل يومها UTC (0 = أول شمعة في اليوم)."""
    return df.groupby(df.index.floor("D")).cumcount()


def day_rolling_max(cond: pd.Series, w: int) -> pd.Series:
    """أقصى قيمة (0/1) خلال آخر w شمعة **داخل اليوم نفسه** — بلا تسرب بين الأيام."""
    g = cond.astype(float).groupby(cond.index.floor("D"))
    r = g.rolling(w, min_periods=1).max()
    return r.reset_index(level=0, drop=True).reindex(cond.index).fillna(0.0) > 0


def rolling_percentile(s: pd.Series, n: int) -> pd.Series:
    """رتبة القيمة الحالية المئوية داخل آخر n شمعة (0..1)."""
    return s.rolling(n, min_periods=n).rank(pct=True)
