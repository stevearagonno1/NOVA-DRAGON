#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0082 · المحرّك المشترك — كشف FVG، الخصائص A1–A12، نقاط الدخول E1–E4،
حسم الحواجز، والإحصاء (نسبة الفوز، التداخل لكل أصل، العينة الفعلية،
الحد الأدنى بعد تصحيح العينة، الربحية بعد التكلفة).

كل التعريفات من القسم 1 للورقة، حرفيًا. RR=1، الهندسة المرجعية 1×ATR/أفق6 ما لم يُذكر غير ذلك.
"""
from __future__ import annotations

import sys
import pathlib
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import l0082_common as C  # noqa: E402

Z = 1.96  # 95%


# ---------------------------------------------------------------- تحميل + مؤشرات
def load_bars(sym: str) -> pd.DataFrame:
    df = pd.read_parquet(C.DATA_DIR / sym / "4h.parquet").reset_index(drop=True)
    return df


def compute_indicators(df: pd.DataFrame) -> dict:
    h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float); o = df["open"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    atr, tr = C.wilder_atr(h, l, c, 14)
    atr_pct = atr / c * 100.0
    ema50 = C.ema(c, 50); ema200 = C.ema(c, 200)
    adx, pdi, ndi = C.wilder_adx(h, l, c, 14)
    vsma20 = C.sma(v, 20)
    return dict(h=h, l=l, c=c, o=o, v=v, atr=atr, atr_pct=atr_pct,
                ema50=ema50, ema200=ema200, adx=adx, pdi=pdi, ndi=ndi, vsma20=vsma20)


def fvg_mask(h, l):
    """FVG صاعدة على i-2,i-1,i:  low[i] > high[i-2]."""
    n = len(h)
    m = np.zeros(n, bool)
    for i in range(2, n):
        if l[i] > h[i-2]:
            m[i] = True
    return m


# ---------------------------------------------------------------- الخصائص
def build_signals(sym: str) -> pd.DataFrame:
    df = load_bars(sym)
    ind = compute_indicators(df)
    h, l, c, o, v = ind["h"], ind["l"], ind["c"], ind["o"], ind["v"]
    atr, atr_pct = ind["atr"], ind["atr_pct"]
    ema50, ema200, adx = ind["ema50"], ind["ema200"], ind["adx"]
    vsma20 = ind["vsma20"]
    n = len(df)
    fvg = fvg_mask(h, l)
    dt = df["dt"]

    # مساعدات نافذة
    def prior_min(arr, k, w):  # min of arr[k-w..k-1]
        if k - w < 0:
            return np.nan
        return float(np.min(arr[k-w:k]))

    rows = []
    for i in range(2, n):
        if not fvg[i]:
            continue
        gap_low = h[i-2]; gap_high = l[i]; gap_size = gap_high - gap_low
        rec = {
            "symbol": sym, "i": i, "dt": dt.iloc[i], "year": int(dt.iloc[i].year),
            "entry_close": c[i], "atr": atr[i], "atr_pct": atr_pct[i],
            "gap_low": gap_low, "gap_high": gap_high, "gap_size": gap_size,
        }
        A = {}
        A["A1"] = gap_size / atr[i] if atr[i] and not np.isnan(atr[i]) else np.nan
        rng1 = h[i-1] - l[i-1]
        A["A2"] = abs(c[i-1] - o[i-1]) / rng1 if rng1 > 0 else np.nan
        A["A3"] = rng1 / atr[i] if atr[i] and not np.isnan(atr[i]) else np.nan
        A["A4"] = v[i-1] / vsma20[i-1] if not np.isnan(vsma20[i-1]) and vsma20[i-1] > 0 else np.nan
        # A5: عدد إشارات FVG خلال آخر 20 شمعة (تشمل الحالية) i-19..i
        lo5 = max(0, i-19)
        A["A5"] = int(fvg[lo5:i+1].sum())
        A["A6"] = (c[i] - ema50[i]) / atr[i] if not np.isnan(ema50[i]) and not np.isnan(atr[i]) else np.nan
        A["A7"] = (c[i] - ema200[i]) / atr[i] if not np.isnan(ema200[i]) and not np.isnan(atr[i]) else np.nan
        A["A8"] = adx[i] if not np.isnan(adx[i]) else np.nan
        # A9: الموقع داخل نطاق آخر 20 (تشمل i)
        if i - 19 >= 0:
            wlo = float(np.min(l[i-19:i+1])); whi = float(np.max(h[i-19:i+1]))
            A["A9"] = (c[i] - wlo) / (whi - wlo) if whi > wlo else np.nan
        else:
            A["A9"] = np.nan
        # A10: كنس سيولة سابق على i-2 أو i-1
        def swept(k):
            pl = prior_min(l, k, 10)
            if np.isnan(pl):
                return False
            return (l[k] < pl) and (c[k] > pl)
        A["A10"] = bool(swept(i-2) or swept(i-1))
        # A11: نسبة رتبة atr_pct ضمن آخر 100
        if i - 99 >= 0 and not np.isnan(atr_pct[i]):
            win = atr_pct[i-99:i+1]
            win = win[~np.isnan(win)]
            A["A11"] = float(np.mean(win <= atr_pct[i])) if len(win) else np.nan
        else:
            A["A11"] = np.nan
        # A12: ساعة فتح الشمعة UTC
        A["A12"] = int(dt.iloc[i].hour)
        rec.update(A)
        rows.append(rec)
    sig = pd.DataFrame(rows)
    return sig, df, ind


# ---------------------------------------------------------------- حسم الحواجز
def resolve_e1(df, sig, stop_mult=1.0, horizon=6):
    """أمر سوق عند إغلاق i. يعيد أعمدة: outcome (win/loss/undecided), rr, dur, cover_start, cover_end."""
    h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    n = len(df)
    out = []
    for _, r in sig.iterrows():
        i = int(r["i"]); atr = r["atr"]
        if np.isnan(atr) or atr <= 0:
            out.append(("na", np.nan, 0, i+1, i)); continue
        R = stop_mult * atr
        entry = c[i]; stop = entry - R; target = entry + R
        res = "undecided"; rr = np.nan; end = min(i+horizon, n-1)
        jlast = i
        done = False
        for j in range(i+1, min(i+horizon, n-1)+1):
            jlast = j
            hit_t = h[j] >= target; hit_s = l[j] <= stop
            if hit_t and hit_s:
                res, rr = "loss", -1.0; done = True; break
            if hit_s:
                res, rr = "loss", -1.0; done = True; break
            if hit_t:
                res, rr = "win", +1.0; done = True; break
        if not done:
            res = "undecided"; rr = (c[jlast] - entry) / R if jlast > i else np.nan
        dur = jlast - i
        out.append((res, rr, dur, i+1, jlast))
    o = pd.DataFrame(out, columns=["outcome", "rr", "dur", "cov_start", "cov_end"], index=sig.index)
    return o


def resolve_limit(df, sig, level_col, stop_mult=1.0, horizon=6, fill_window=3):
    """أمر حد عند مستوى (gap_high/mid/gap_low). التنفيذ باللمس خلال 3 شموع.
    لمس المستوى والوقف في نفس الشمعة ⇒ خاسر. يعيد filled/outcome/rr."""
    h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    n = len(df)
    out = []
    for _, r in sig.iterrows():
        i = int(r["i"]); atr = r["atr"]; L = r[level_col]
        if np.isnan(atr) or atr <= 0 or np.isnan(L):
            out.append((False, "na", np.nan)); continue
        # التنفيذ: أول شمعة j في i+1..i+3 حيث low[j] <= L
        f = None
        for j in range(i+1, min(i+fill_window, n-1)+1):
            if l[j] <= L:
                f = j; break
        if f is None:
            out.append((False, "unfilled", np.nan)); continue
        R = stop_mult * atr; stop = L - R; target = L + R
        # على شمعة التنفيذ: إن لُمس الوقف أيضًا ⇒ خاسر (نفس الشمعة)
        if l[f] <= stop:
            out.append((True, "loss", -1.0)); continue
        res = "undecided"; rr = np.nan; jlast = f
        done = False
        for j in range(f+1, min(f+horizon, n-1)+1):
            jlast = j
            hit_t = h[j] >= target; hit_s = l[j] <= stop
            if hit_t and hit_s:
                res, rr = "loss", -1.0; done = True; break
            if hit_s:
                res, rr = "loss", -1.0; done = True; break
            if hit_t:
                res, rr = "win", +1.0; done = True; break
        if not done:
            res = "undecided"; rr = (c[jlast] - L) / R if jlast > f else np.nan
        out.append((True, res, rr))
    o = pd.DataFrame(out, columns=["filled", "outcome", "rr"], index=sig.index)
    return o


# ---------------------------------------------------------------- التداخل لكل أصل
def asset_overlap(df, e1):
    """overlap = مجموع أيام الحمل / عدد الشموع المغطاة (على مستوى الأصل).
    coverage = الشموع المغطاة / إجمالي الشموع."""
    n = len(df)
    covered = np.zeros(n, dtype=np.int32)
    total_hold = 0
    valid = e1[e1["outcome"] != "na"]
    for _, r in valid.iterrows():
        s = int(r["cov_start"]); e = int(r["cov_end"])
        if e < s:
            continue
        covered[s:e+1] += 1
        total_hold += (e - s + 1)
    covered_bars = int((covered > 0).sum())
    overlap = total_hold / covered_bars if covered_bars > 0 else np.nan
    coverage = covered_bars / n
    return overlap, coverage, covered_bars, n


# ---------------------------------------------------------------- الإحصاء للشرائح
def wilson_style_lb(p, n_eff):
    if n_eff is None or n_eff <= 0 or np.isnan(p):
        return np.nan
    return p - Z * np.sqrt(p * (1 - p) / n_eff)


def two_sided_p_vs_half(p, n_eff):
    """اختبار نسبة ثنائي الطرف H0:p=0.5 على العينة الفعلية (محافظ)."""
    from scipy.stats import norm
    if n_eff is None or n_eff <= 0:
        return np.nan
    se = np.sqrt(0.25 / n_eff)
    if se == 0:
        return np.nan
    z = (p - 0.5) / se
    return float(2 * (1 - norm.cdf(abs(z))))


def subset_overlap(sub):
    """التداخل لكل أصل محسوبًا على فترات صفقات هذه المجموعة نفسها (لا العالمية).
    overlap = مجموع أيام الحمل / الشموع المغطاة، باستعمال أعمدة e1_cov_start/e1_cov_end.
    يُحسب على كل الإشارات (لا المحسومة فقط) اتساقًا مع تعريف التغطية."""
    cs = "e1_cov_start" if "e1_cov_start" in sub.columns else "cov_start"
    ce = "e1_cov_end" if "e1_cov_end" in sub.columns else "cov_end"
    out = {}
    for symv, g in sub.groupby("symbol"):
        s = g[cs].to_numpy(); e = g[ce].to_numpy()
        m = ~(pd.isna(s) | pd.isna(e))
        s = s[m].astype(int); e = e[m].astype(int)
        if len(s) == 0:
            out[symv] = np.nan; continue
        lo = s.min(); hi = e.max()
        cover = np.zeros(hi - lo + 2, dtype=np.int32)
        total = 0
        for a, b in zip(s, e):
            if b < a:
                continue
            cover[a - lo:b - lo + 1] += 1
            total += (b - a + 1)
        covered_bars = int((cover > 0).sum())
        out[symv] = (total / covered_bars) if covered_bars > 0 else np.nan
    return out


def slice_stats(sub, overlaps, cost_lookup=None, stop_mult=1.0, rr=1.0):
    """sub: صفوف الإشارات لشريحة، فيها outcome, rr, symbol, year, atr_pct.
    التداخل يُعاد حسابه على فترات صفقات المجموعة نفسها (subset_overlap)، وليس عالميًا،
    كي يعكس التخفيف/إزالة التكتّل بصدق. overlaps (العالمية) احتياط عند غياب أعمدة الفترة."""
    dec = sub[sub["outcome"].isin(["win", "loss"])]
    n_sig = len(sub)
    n_dec = len(dec)
    wins = int((dec["outcome"] == "win").sum())
    p = wins / n_dec if n_dec > 0 else np.nan
    # التداخل لكل أصل على مجموعة هذه الشريحة
    if ("e1_cov_start" in sub.columns) or ("cov_start" in sub.columns):
        ov_sub = subset_overlap(sub)
    else:
        ov_sub = overlaps
    # العينة الفعلية = مجموع (المحسوم لكل أصل / overlap الأصل في هذه المجموعة)
    n_eff = 0.0
    for symv, g in dec.groupby("symbol"):
        ov = ov_sub.get(symv, overlaps.get(symv, np.nan))
        if ov and not np.isnan(ov) and ov > 0:
            n_eff += len(g) / ov
    n_eff = n_eff if n_eff > 0 else np.nan
    lb = wilson_style_lb(p, n_eff)
    pval = two_sided_p_vs_half(p, n_eff)
    # التداخل الممثِّل للشريحة = المحسوم / العينة الفعلية
    slice_overlap = (n_dec / n_eff) if (n_eff and not np.isnan(n_eff)) else np.nan
    # الربحية بعد التكلفة
    prof1 = prof3 = np.nan
    if cost_lookup is not None and n_dec > 0:
        net1 = []
        for _, rrow in dec.iterrows():
            cm = cost_lookup(rrow["symbol"], int(rrow["year"]))
            atrp = rrow["atr_pct"]
            if cm is None or np.isnan(atrp) or atrp <= 0:
                continue
            cost_R = cm / (stop_mult * atrp * 100.0)
            payoff = rr if rrow["outcome"] == "win" else -1.0
            net1.append(payoff - cost_R)
        prof1 = float(np.mean(net1)) if net1 else np.nan
        # سيناريو 3: حد/حد، cost_limit = 2 + p*2 + (1-p)*(5+spread+impact)
        net3 = []
        for _, rrow in dec.iterrows():
            cm = cost_lookup(rrow["symbol"], int(rrow["year"]))
            atrp = rrow["atr_pct"]
            if cm is None or np.isnan(atrp) or atrp <= 0:
                continue
            spread_plus = cm - 2 * C.FEE_TAKER_BPS  # = spread + 2*impact
            cl = 2.0 + p * 2.0 + (1 - p) * (5.0 + spread_plus)
            cost_R3 = cl / (stop_mult * atrp * 100.0)
            payoff = rr if rrow["outcome"] == "win" else -1.0
            net3.append(payoff - cost_R3)
        prof3 = float(np.mean(net3)) if net3 else np.nan
    return {
        "n_signals": n_sig, "n_decided": n_dec, "wins": wins,
        "win_rate": round(p, 4) if not np.isnan(p) else None,
        "overlap": round(slice_overlap, 4) if slice_overlap and not np.isnan(slice_overlap) else None,
        "n_effective": round(n_eff, 1) if n_eff and not np.isnan(n_eff) else None,
        "lower_bound": round(lb, 4) if not np.isnan(lb) else None,
        "p_value": round(pval, 5) if pval is not None and not np.isnan(pval) else None,
        "prof_after_cost_scen1": round(prof1, 5) if not np.isnan(prof1) else None,
        "prof_after_cost_scen3": round(prof3, 5) if not np.isnan(prof3) else None,
    }


# ---------------------------------------------------------------- التكلفة
_COST_DF = None
def cost_lookup_factory():
    global _COST_DF
    if _COST_DF is None:
        _COST_DF = pd.read_csv(C.OUT / "cost_model_l0082.csv")
    tbl = {(r["symbol"], int(r["year"])): r["cost_market_bps"] for _, r in _COST_DF.iterrows()}
    def look(symbol, year):
        if (symbol, year) in tbl:
            return float(tbl[(symbol, year)])
        # أقرب سنة متاحة
        yrs = [y for (s, y) in tbl if s == symbol]
        if not yrs:
            return None
        y2 = min(yrs, key=lambda y: abs(y - year))
        return float(tbl[(symbol, y2)])
    return look


def in_period(sig, start, end):
    a = pd.Timestamp(start, tz="UTC"); b = pd.Timestamp(end + " 23:59:59", tz="UTC")
    return sig[(sig["dt"] >= a) & (sig["dt"] <= b)].copy()
