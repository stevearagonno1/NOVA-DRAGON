# -*- coding: utf-8 -*-
"""L0068 — مُعيد تشغيل مستقل لدورة القاع، مكتوب من نص القواعد لا من كود المحرك.

لا يستورد nova_v8 إطلاقًا. المؤشرات محسوبة هنا من الصفر.
القواعد المكتوبة (مصدرها: docstring وتعليقات long_cycle.py، ورقة L0061 المادة 13، وتقرير L0064):
  R1  شموع 4h ويومية من الدقيقة (label/closed = left).
  R2  أدنى قاع 90 يومًا من قيعان اليوم السابق (min_periods 30)، معروف من اليوم التالي فقط.
  R3  المنطقة: إغلاق 4h ≤ أدنى قاع × 1.08 (V2). «رُئيت المنطقة» = منطقة في إحدى الشموع الست السابقة.
  R4  MSS: إغلاق > أعلى قمة الشموع الست السابقة. الإشارة = رُئيت المنطقة و MSS وإغلاق > EMA20(4h).
  R5  بوابة المناخ (V3): وسم يومي EMA50/EMA200 وميل EMA50 على 10 أيام، مزاح يومًا واحدًا؛ الشراء فقط إن كان «هابط».
  R6  التنفيذ على افتتاح الشمعة التالية. أمر شراء معلق واحد فقط في كل لحظة.
  R7  أوزان الشرائح 0.15/0.25/0.30/0.30 من دفتر العملة. الإضافة فقط بإشارة جديدة وسعر ≤ أدنى دخول × (1 − 1.5%) وقبل رؤية القمة.
  R8  الإلغاء: قاع الشمعة ≤ min(أدنى دخول × 0.92، أدنى قاع 90 يومًا × 0.98) ⇒ إغلاق الكل على min(الافتتاح، المستوى).
  R9  القمة: إغلاق ≥ أعلى قمة 90 يومًا × 0.97. الضعف: إغلاق < أدنى قاع الشموع الثلاث السابقة أو < EMA20؛ حدث = أول شمعة ضعف.
  R10 التوزيع: بعد رؤية القمة، كل حدث ضعف يبيع آخر شريحة على الإغلاق.
  R11 نهاية العينة: إغلاق المفتوح على إغلاق آخر شمعة.
  R12 الكلفة: عمولة c لكل طرف، الصافي = ((خروج/دخول)(1−c) − (1+c)) / (1+c).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

W = (0.15, 0.25, 0.30, 0.30)


def daily_of(h4: pd.DataFrame) -> pd.DataFrame:
    return h4.resample("1D", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def ema(x: np.ndarray, span: int) -> np.ndarray:
    a = 2.0 / (span + 1.0)
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def climate_bear_by_day(daily: pd.DataFrame) -> dict:
    c = daily["close"].to_numpy(float)
    e50, e200 = ema(c, 50), ema(c, 200)
    slope = np.full(len(c), np.nan)
    slope[10:] = e50[10:] - e50[:-10]
    bear = (e50 < e200) & (slope < 0)
    out = {}
    for k in range(1, len(c)):  # الوسم في اليوم k هو تصنيف إغلاق اليوم k-1
        out[daily.index[k]] = bool(bear[k - 1])
    return out


def replay(h4: pd.DataFrame, symbol: str, book: float = 1000.0, cost: float = 0.00115, gate: bool = True,
           trace: dict | None = None, ctx_extra_lag: bool = False) -> list[dict]:
    """ctx_extra_lag=True = نص تعليق المحرك (إزاحة يوم إضافية)؛ False = ما يفعله الكود فعلًا (انظر L0068 §الاختلافات)."""
    if len(h4) < 200:
        return []
    o, h, l, c = (h4[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    idx = h4.index
    n = len(h4)
    d = daily_of(h4)
    dl, dh = d["low"].to_numpy(float), d["high"].to_numpy(float)
    plow = np.full(len(d), np.nan); phigh = np.full(len(d), np.nan)
    for k in range(len(d)):  # R2: نافذة 90 يومًا من الأيام السابقة فقط
        a = max(0, k - 90)
        seg_l, seg_h = dl[a:k], dh[a:k]
        if len(seg_l) >= 30:
            plow[k] = seg_l.min(); phigh[k] = seg_h.max()
    # قيمة اليوم k (المحسوبة من الأيام < k) صالحة من بداية اليوم k+1 (إزاحة المحرك: shift(1) ثم +1 يوم)
    if ctx_extra_lag:
        known_from = {d.index[k] + pd.Timedelta(days=1): (plow[k], phigh[k]) for k in range(len(d))}
    else:  # الكود: DataFrame يعيد محاذاة السلسلة على الفهرس المزاح فتضيع الإزاحة الإضافية
        known_from = {d.index[k]: (plow[k], phigh[k]) for k in range(len(d))}
    keys = sorted(known_from)
    PL = np.full(n, np.nan); PH = np.full(n, np.nan)
    j = -1
    for i in range(n):
        while j + 1 < len(keys) and keys[j + 1] <= idx[i]:
            j += 1
        if j >= 0:
            PL[i], PH[i] = known_from[keys[j]]
    e20 = ema(c, 20)
    zone = c <= PL * 1.08
    sig = np.zeros(n, bool); zone_seen = np.zeros(n, bool); mss = np.zeros(n, bool)
    for i in range(n):
        zone_seen[i] = bool(np.any(zone[max(0, i - 6):i]))
        if i >= 6:
            mss[i] = c[i] > h[i - 6:i].max()
        sig[i] = zone_seen[i] and mss[i] and c[i] > e20[i]
    bear = climate_bear_by_day(d)
    ok = np.array([bear.get(t.normalize(), False) if gate else True for t in idx])
    top = c >= PH * 0.97
    weak = np.zeros(n, bool)
    for i in range(n):
        if i >= 3:
            weak[i] = (c[i] < l[i - 3:i].min()) or (c[i] < e20[i])
        else:
            weak[i] = c[i] < e20[i]
    wev = weak & ~np.concatenate([[False], weak[:-1]])
    if trace is not None:
        trace.update({"PL": PL, "PH": PH, "e20": e20, "zone_seen": zone_seen, "mss": mss, "sig": sig, "ok": ok, "top": top, "wev": wev})

    def rec(tr, xi, px, why):
        net = ((px / tr["px"]) * (1 - cost) - (1 + cost)) / (1 + cost)
        return {"symbol": symbol, "stage": tr["stage"], "entry_bar": tr["i"], "exit_bar": xi,
                "entry_time": idx[tr["i"]].isoformat(), "exit_time": idx[xi].isoformat(),
                "entry_px": tr["px"], "exit_px": float(px), "notional_usd": tr["no"], "pnl_usd": net * tr["no"],
                "reason": why, "signal_bar": tr["sig"]}

    out, trs, pend = [], [], None
    topseen, nxt = False, 0
    for i in range(1, n):
        if pend is not None and pend[0] == i:          # R6
            _, st, sb = pend; pend = None
            if len(trs) < 4 and np.isfinite(o[i]) and o[i] > 0:
                trs.append({"stage": st, "i": i, "px": o[i], "no": book * W[st], "sig": sb})
                nxt = max(nxt, st + 1)
        if not trs:
            if sig[i] and ok[i] and pend is None:
                pend = (i + 1, 0, i)
            continue
        lvl = min(min(t["px"] for t in trs) * 0.92, PL[i] * 0.98 if np.isfinite(PL[i]) else -np.inf)  # R8
        if l[i] <= lvl:
            px = o[i] if o[i] < lvl else lvl
            out += [rec(t, i, px, "إلغاء-دورة") for t in trs]
            trs, topseen, nxt = [], False, 0
            continue
        if top[i]:
            topseen = True
        if topseen and wev[i]:                         # R10
            t = trs.pop(); out.append(rec(t, i, c[i], "توزيع-قمة"))
            if not trs:
                topseen, nxt = False, 0
            continue
        if (not topseen and nxt < 4 and sig[i] and ok[i] and pend is None
                and c[i] <= min(t["px"] for t in trs) * (1 - 0.015)):   # R7
            pend = (i + 1, nxt, i)
    if trs:
        out += [rec(t, n - 1, c[n - 1], "نهاية-العينة") for t in trs]
    return out
