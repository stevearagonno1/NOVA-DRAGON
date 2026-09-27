# -*- coding: utf-8 -*-
"""L0068 — محاكي مكتبة الفرضيات (المسار الثاني). مستقل عن nova_v8. 4h، سببي بالكامل.

القيم اليومية (أعلى L يومًا، متوسطات العملة، مرشحات BTC والاتساع) محسوبة من أيام مغلقة قبل يوم الشمعة فقط.
الإشارة على إغلاق الشمعة i ⇒ التنفيذ على افتتاح i+1. لا وقف متحرك.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

GAP = 0.015


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _daily(h4):
    return h4.resample("1D", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def _to4h(daily_series: pd.Series, idx4: pd.DatetimeIndex) -> np.ndarray:
    """قيمة اليوم D-1 (مغلق) متاحة طوال اليوم D."""
    s = daily_series.shift(1)
    return s.reindex(idx4.normalize()).to_numpy()


def market_by_day(h4s: dict, coins) -> dict:
    """مرشحات السوق اليومية (قبل الإزاحة): BTC وأنواع الاتساع."""
    bd = _daily(h4s["BTCUSDT"])
    c = bd.close; e50, e200 = _ema(c, 50), _ema(c, 200)
    out = {"btc200": (c > e200), "btc200_50": (c > e200) & (e50 > e200), "btc_bear": (c < e200) & (e50 < e200)}
    above, avail = [], []
    for s in coins:
        d = _daily(h4s[s]); ok = d.close > _ema(d.close, 200)
        ok[d.index < d.index[0] + pd.Timedelta(days=200)] = np.nan  # EMA200 غير ناضجة = غير متوفرة
        above.append(ok.astype(float))
    A = pd.concat(above, axis=1)
    share = A.mean(axis=1, skipna=True)
    for th in (40, 50, 60):
        out[f"breadth{th}"] = share >= th / 100
    return {k: v.astype(float) for k, v in out.items()}


class Coin:
    def __init__(self, sym, h4: pd.DataFrame, mkt: dict):
        self.sym = sym; self.idx = h4.index
        self.o, self.h, self.l, self.c, self.v = (h4[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
        c = h4.close
        self.e20, self.e50 = _ema(c, 20).to_numpy(), _ema(c, 50).to_numpy()
        tr = pd.concat([h4.high - h4.low, (h4.high - c.shift()).abs(), (h4.low - c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
        self.atr = atr.to_numpy(); self.vr = (atr / atr.rolling(100).mean()).to_numpy()
        d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
        rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
        self.rsi_min6 = rsi.rolling(6).min().to_numpy()
        m = c.rolling(20).mean(); sd = c.rolling(20).std(ddof=0); self.bbw = (4 * sd / m).to_numpy()
        self.vol_up = (h4.volume > h4.volume.rolling(20).mean().shift(1)).to_numpy()
        self.phigh = {k: h4.high.shift(1).rolling(k).max().to_numpy() for k in (3, 6, 12)}
        self.plow3 = h4.low.shift(1).rolling(3).min().to_numpy()
        dd = _daily(h4)
        self.Hd = {L: _to4h(dd.high.rolling(L, min_periods=L).max(), self.idx) for L in (20, 30, 60, 90)}
        self.Ld90 = _to4h(dd.low.rolling(90, min_periods=30).min(), self.idx)
        self.trend = {f"ema{n}": _to4h((dd.close > _ema(dd.close, n)).astype(float), self.idx) for n in (20, 50, 100, 200)}
        self.trend["x20_50"] = _to4h((_ema(dd.close, 20) > _ema(dd.close, 50)).astype(float), self.idx)
        self.trend["x50_200"] = _to4h((_ema(dd.close, 50) > _ema(dd.close, 200)).astype(float), self.idx)
        self.mkt = {k: _to4h(v, self.idx) for k, v in mkt.items()}
        self.n = len(h4)


def signal(cn: Coin, p: dict) -> np.ndarray:
    L, D = p["L"], p["D"] / 100
    H = cn.Hd[L]
    zone = cn.c <= H * (1 - D)
    zs = pd.Series(zone.astype(float)).shift(1).rolling(6, min_periods=1).max().fillna(0).to_numpy() > 0
    r = p["rec"]
    if r.startswith("MSS"):
        k = int(r[3:].split("+")[0]); rec = cn.c > cn.phigh[k]
        if "+EMA20" in r:
            rec = rec & (cn.c > cn.e20)
    elif r == "C>EMA20":
        rec = cn.c > cn.e20
    else:
        rec = cn.c > cn.e50
    s = zs & rec
    if p.get("market"):
        s &= cn.mkt[p["market"]] == 1
    if p.get("trend"):
        s &= cn.trend[p["trend"]] == 1
    a = p.get("aux")
    if a:
        if a.startswith("rsi"):
            s &= cn.rsi_min6 <= int(a[3:])
        elif a == "bb10":
            s &= cn.bbw >= 0.10
        elif a == "volup":
            s &= cn.vol_up
        elif a == "voldn":
            s &= ~cn.vol_up
    return np.nan_to_num(s, nan=0).astype(bool)


def run(cn: Coin, p: dict, allow: np.ndarray | None = None) -> list[dict]:
    """allow: قناع إضافي (أوضاع التوقف) يمنع قرارات الشراء فقط."""
    sig = signal(cn, p)
    if allow is not None:
        sig = sig & allow
    S = p.get("stages", 4); inv = p.get("inv", "pct8"); ex = p.get("exit", "top"); tl = p.get("tl")
    o, h, l, c, idx = cn.o, cn.h, cn.l, cn.c, cn.idx
    Htop = cn.Hd[p["L"]]
    weak = np.zeros(cn.n, bool)
    with np.errstate(invalid="ignore"):
        weak = (c < cn.plow3) | (c < cn.e20)
    wev = weak & ~np.concatenate([[False], weak[:-1]])
    tlb = int(tl * 6) if tl else None
    out, trs, pend = [], [], None
    topseen = hit = False; nxt = 0; invlvl = None

    def close_all(i, px, why):
        nonlocal trs, topseen, hit, nxt, invlvl
        for t in trs:
            out.append((t[0], t[1], i, float(px), why, t[2]))
        trs = []; topseen = hit = False; nxt = 0; invlvl = None

    for i in range(1, cn.n):
        if pend is not None and pend[0] == i:
            _, st, sb = pend; pend = None
            if len(trs) < S and o[i] > 0:
                trs.append((st, i, sb))
                nxt = max(nxt, st + 1)
                if inv.startswith("atr") and invlvl is None:
                    invlvl = ("atr", float(inv[3:]) * cn.atr[sb])
        if not trs:
            if sig[i] and pend is None:
                pend = (i + 1, 0, i)
            continue
        mn = min(o[t[1]] for t in trs)
        if inv == "pct8":
            lvl = min(mn * 0.92, cn.Ld90[i] * 0.98 if np.isfinite(cn.Ld90[i]) else -np.inf)
        else:
            lvl = mn - invlvl[1]
        if l[i] <= lvl:
            close_all(i, o[i] if o[i] < lvl else lvl, "إلغاء"); continue
        if tlb is not None and i - trs[0][1] >= tlb:
            close_all(i, c[i], "حد-زمني"); continue
        if ex == "top":
            if np.isfinite(Htop[i]) and c[i] >= Htop[i] * 0.97:
                topseen = True
            if topseen and wev[i]:
                t = trs.pop(); out.append((t[0], t[1], i, float(c[i]), "توزيع-ضعف", t[2]))
                if not trs:
                    topseen = False; nxt = 0; invlvl = None
                continue
        else:  # هدف جزئي +10% لنصف الشرائح ثم ضعف
            avg = np.mean([o[t[1]] for t in trs])
            if not hit and c[i] >= avg * 1.10:
                k = (len(trs) + 1) // 2
                for _ in range(k):
                    t = trs.pop(); out.append((t[0], t[1], i, float(c[i]), "هدف-جزئي", t[2]))
                hit = True
                if not trs:
                    hit = False; nxt = 0; invlvl = None
                continue
            if hit and wev[i]:
                t = trs.pop(); out.append((t[0], t[1], i, float(c[i]), "توزيع-ضعف", t[2]))
                if not trs:
                    hit = False; nxt = 0; invlvl = None
                continue
        if (not topseen and not hit and nxt < S and sig[i] and pend is None and c[i] <= mn * (1 - GAP)):
            pend = (i + 1, nxt, i)
    if trs:
        close_all(cn.n - 1, c[cn.n - 1], "نهاية-العينة")
    return [{"symbol": cn.sym, "stage": st, "entry_bar": ei, "exit_bar": xi, "entry_ref": float(o[ei]), "exit_px": px,
             "reason": why, "signal_bar": sb} for st, ei, xi, px, why, sb in out]


# ───────────── الكلفة ─────────────
def slip_mult(v):
    return np.where(v >= 1.5, 3.0, np.where(v >= 1.2, 2.0, 1.0))


def pnl(rows, coins: dict, layer: str, size=20.0) -> np.ndarray:
    """layer: gross | c115 | c130 | intended | s10 | s30"""
    if not rows:
        return np.zeros(0)
    ep = np.array([r["entry_ref"] for r in rows]); xp = np.array([r["exit_px"] for r in rows])
    if layer == "gross":
        return (xp / ep - 1) * size
    if layer in ("c115", "c130"):
        c = 0.00115 if layer == "c115" else 0.0013
        return ((xp / ep) * (1 - c) - (1 + c)) / (1 + c) * size
    fee = 0.0010
    if layer == "intended":
        se = np.array([0.0003 * slip_mult(np.nan_to_num(coins[r["symbol"]].vr[max(r["entry_bar"] - 1, 0)], nan=0.0)) for r in rows])
        sx = np.array([0.0003 * slip_mult(np.nan_to_num(coins[r["symbol"]].vr[max(r["exit_bar"] - 1, 0)], nan=0.0)) for r in rows])
    else:
        s = 0.0010 if layer == "s10" else 0.0030
        se = sx = np.full(len(rows), s)
    epx = ep * (1 + se); xpx = xp * (1 - sx)
    return ((xpx / epx) * (1 - fee) - (1 + fee)) / (1 + fee) * size
