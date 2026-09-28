#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0083 — الحكم على المؤشرات: مسح مقاس فعليًا.

الحاوية = نفس حاجز L0082 (R=1×ATR14 وايلدر، أفق 6، لمس الحاجزين نفس الشمعة=خسارة)،
الدخول عند إغلاق كل شمعة. الأساس = شراء كل شمعة. الرفع = نسبة فوز الإشارة − أساس الفترة.
التكلفة من جدول L0082 المجمّد. الفصل: تدريب/محجوز/أمامية. المحجوز يُقرأ مرة واحدة.

السؤال الحاسم: هل ترتيب الرفع على التدريب يتنبأ بترتيبه على المحجوز؟ (ارتباط + انكماش)
+ محاكاة العدم (20,000 عالمًا) لعدد العابرين بالصدفة.
"""
from __future__ import annotations
import json, sys, pathlib
import numpy as np
import pandas as pd
from scipy import stats as sstats

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import l0082_common as C   # noqa: E402
import l0083_indicators as I  # noqa: E402

SEED = 82
np.random.seed(SEED)
OUT = C.ROOT / "history" / "research" / "hyp_lab_out" / "L0083"
OUT.mkdir(parents=True, exist_ok=True)
ALT = pathlib.Path("/home/user/l0083"); ALT.mkdir(exist_ok=True)

TRAIN = ("2021-01-01", "2025-03-31")
HOLDOUT = ("2025-04-01", "2026-06-30")
FORWARD = ("2026-07-01", "2026-09-27")
HORIZON = 6
Z = 1.96

_COST = pd.read_csv(C.OUT / "cost_model_l0082.csv")
_COSTTBL = {(r["symbol"], int(r["year"])): float(r["cost_market_bps"]) for _, r in _COST.iterrows()}


def cost_bps(sym, year):
    if (sym, year) in _COSTTBL:
        return _COSTTBL[(sym, year)]
    yrs = [y for (s, y) in _COSTTBL if s == sym]
    return _COSTTBL[(sym, min(yrs, key=lambda y: abs(y - year)))] if yrs else 15.0


# ----------------------------------------------------------- الحاوية: نتائج كل شمعة
def resolve_all(df):
    h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    atr, _ = C.wilder_atr(h, l, c, 14)
    n = len(c)
    outcome = np.array(["na"] * n, dtype=object); rr = np.full(n, np.nan)
    cs = np.full(n, -1, int); ce = np.full(n, -1, int)
    for i in range(n):
        a = atr[i]
        if np.isnan(a) or a <= 0 or i + 1 >= n:
            continue
        R = a; entry = c[i]; stop = entry - R; target = entry + R
        res = "undecided"; val = np.nan; jlast = i
        for j in range(i + 1, min(i + HORIZON, n - 1) + 1):
            jlast = j
            ht = h[j] >= target; hs = l[j] <= stop
            if hs and ht:
                res, val = "loss", -1.0; break
            if hs:
                res, val = "loss", -1.0; break
            if ht:
                res, val = "win", 1.0; break
        else:
            val = (c[jlast] - entry) / R
        if res == "undecided" and jlast > i and np.isnan(val):
            val = (c[jlast] - entry) / R
        outcome[i] = res; rr[i] = val; cs[i] = i + 1; ce[i] = jlast
    return outcome, rr, cs, ce, atr


# ----------------------------------------------------------- سجل الإعدادات
def build_signals(d):
    """d: dict of arrays. يعيد dict name->bool array. سببي بحت."""
    o, h, l, c, v, tbv = d["o"], d["h"], d["l"], d["c"], d["v"], d["tbv"]
    S = {}
    # RSI cross-up (عائلة عمق RSI)
    for per in (7, 14, 21):
        r = I.rsi(c, per)
        for thr in (20, 25, 30):
            S[f"RSI{per}_xup_{thr}"] = I.cross_up_through(r, thr)
    # Stochastic cross-up
    for (n, dd) in ((14, 3), (21, 5)):
        k, _ = I.stochastic(h, l, c, n, dd)
        for thr in (15, 20, 25):
            S[f"Stoch{n}_{dd}_xup_{thr}"] = I.cross_up_through(k, thr)
    # Bollinger: إغلاق يعبر النطاق السفلي صعودًا
    for k in (2.0, 2.5, 3.0):
        low_b, _, _ = I.bollinger(c, 20, k)
        S[f"BB20_{k}_reenter"] = I.cross_above(c, low_b)
    # EMA cross (تقاطع ذهبي)
    for (a, b) in ((20, 50), (50, 200), (20, 200)):
        S[f"EMA_x_{a}_{b}"] = I.cross_above(I.ema(c, a), I.ema(c, b))
    # سعر يعبر EMA صعودًا
    for p in (50, 200):
        S[f"PX_x_EMA{p}"] = I.cross_above(c, I.ema(c, p))
    # MACD cross
    for (f, s, sg) in ((12, 26, 9), (5, 35, 5)):
        ml, sl = I.macd(c, f, s, sg)
        S[f"MACD_{f}_{s}_{sg}_xup"] = I.cross_above(ml, sl)
    # Aroon
    for n in (14, 25):
        au, ad = I.aroon(h, l, n)
        S[f"Aroon{n}_bull_x"] = I.cross_above(au, ad)
    # Donchian breakout
    for n in (10, 20, 55):
        lo, up = I.donchian(h, l, c, n)
        S[f"Donchian{n}_break"] = np.asarray(c, float) > up
    # Donchian failure (اختراق ثم إغلاق داخل)
    lo, up = I.donchian(h, l, c, 20)
    S["Donchian20_fail"] = (np.asarray(h, float) > up) & (np.asarray(c, float) <= up)
    # ذروة الحجم (z على نافذة 50)
    vz = I.rolling_z(v, 50)
    for z in (1.5, 2.0, 2.5, 3.0):
        S[f"VolSpike_z{z}"] = vz >= z
    # نسبة شراء التيكر > عتبة
    ratio = np.divide(np.asarray(tbv, float), np.asarray(v, float),
                      out=np.full(len(v), np.nan), where=np.asarray(v, float) > 0)
    for thr in (0.48, 0.50, 0.52, 0.55):
        S[f"TakerRatio_gt_{thr}"] = ratio > thr
    # z-score لنسبة شراء التيكر
    rz = I.rolling_z(ratio, 50)
    for z in (1.5, 2.0, 2.5):
        S[f"TakerRatioZ_ge_{z}"] = rz >= z
    # CCI cross up through -100
    for n in (14, 20):
        S[f"CCI{n}_xup_-100"] = I.cross_up_through(I.cci(h, l, c, n), -100)
    # Williams %R cross up through -80
    for n in (14, 21):
        S[f"WilliamsR{n}_xup_-80"] = I.cross_up_through(I.williams_r(h, l, c, n), -80)
    # MFI cross up through 20
    for n in (14,):
        S[f"MFI{n}_xup_20"] = I.cross_up_through(I.mfi(h, l, c, v, n), 20)
    # أنماط شمعية
    S["Hammer"] = I.hammer(o, h, l, c)
    S["BullEngulfing"] = I.bullish_engulfing(o, c)
    # FVG مفرد
    S["FVG_single"] = I.fvg_bull(h, l)
    # انحراف RSI صعودي
    for per in (14, 21):
        S[f"RSI{per}_bull_divergence"] = I.rsi_bull_divergence(l, c, per)
    return S, ratio, vz, rz


# ----------------------------------------------------------- بناء الجدول الكامل
def build_panel():
    rows = []
    for sym in C.ASSETS:
        df = pd.read_parquet(C.DATA_DIR / sym / "4h.parquet").reset_index(drop=True)
        outcome, rr, cs, ce, atr = resolve_all(df)
        d = dict(o=df["open"].to_numpy(float), h=df["high"].to_numpy(float),
                 l=df["low"].to_numpy(float), c=df["close"].to_numpy(float),
                 v=df["volume"].to_numpy(float), tbv=df["taker_buy_volume"].to_numpy(float))
        S, ratio, vz, rz = build_signals(d)
        base = pd.DataFrame({
            "symbol": sym, "i": np.arange(len(df)), "dt": df["dt"].values,
            "year": df["dt"].dt.year.values, "hour": df["dt"].dt.hour.values,
            "close": d["c"], "atr": atr, "atr_pct": atr / d["c"] * 100,
            "outcome": outcome, "rr": rr, "cs": cs, "ce": ce,
            "ratio": ratio, "vol_z": vz, "ratio_z": rz,
        })
        for name, mask in S.items():
            base["S_" + name] = mask
        rows.append(base)
    panel = pd.concat(rows, ignore_index=True)
    return panel, [c[2:] for c in panel.columns if c.startswith("S_")]


# ----------------------------------------------------------- إحصاء
def subset_overlap(sub):
    out = {}
    for sym, g in sub.groupby("symbol"):
        s = g["cs"].to_numpy(); e = g["ce"].to_numpy()
        m = (s >= 0) & (e >= 0)
        s = s[m]; e = e[m]
        if len(s) == 0:
            out[sym] = np.nan; continue
        lo = s.min(); hi = e.max()
        cov = np.zeros(hi - lo + 2, np.int32); tot = 0
        for a, b in zip(s, e):
            if b < a:
                continue
            cov[a - lo:b - lo + 1] += 1; tot += (b - a + 1)
        cb = int((cov > 0).sum())
        out[sym] = tot / cb if cb else np.nan
    return out


def period_slice(panel, per):
    a = pd.Timestamp(per[0]); b = pd.Timestamp(per[1] + " 23:59:59")
    dt = pd.to_datetime(panel["dt"]).dt.tz_localize(None) if getattr(panel["dt"].dtype, "tz", None) else panel["dt"]
    return panel[(dt >= a) & (dt <= b)]


def baseline_stats(pan):
    dec = pan[pan["outcome"].isin(["win", "loss"])]
    wins = (dec["outcome"] == "win").sum()
    return wins / len(dec) if len(dec) else np.nan, len(dec)


def stat_setting(sub, base_p):
    dec = sub[sub["outcome"].isin(["win", "loss"])]
    n_sig = len(sub); n_dec = len(dec)
    if n_dec == 0:
        return None
    wins = int((dec["outcome"] == "win").sum())
    p = wins / n_dec
    ov = subset_overlap(sub)
    n_eff = 0.0
    for sym, g in dec.groupby("symbol"):
        o = ov.get(sym, np.nan)
        if o and not np.isnan(o) and o > 0:
            n_eff += len(g) / o
    n_eff = n_eff if n_eff > 0 else np.nan
    lb = p - Z * np.sqrt(p * (1 - p) / n_eff) if n_eff and not np.isnan(n_eff) else np.nan
    # اختبار نسبة مقابل الأساس على العينة الفعلية
    se = np.sqrt(base_p * (1 - base_p) / n_eff) if n_eff and not np.isnan(n_eff) else np.nan
    zst = (p - base_p) / se if se and not np.isnan(se) and se > 0 else np.nan
    pval = float(2 * (1 - sstats.norm.cdf(abs(zst)))) if not np.isnan(zst) else np.nan
    # صافي R بعد التكلفة
    net = []
    for _, r in dec.iterrows():
        cb = cost_bps(r["symbol"], int(r["year"])); ap = r["atr_pct"]
        if np.isnan(ap) or ap <= 0:
            continue
        cost_R = cb / (ap * 100.0)
        net.append((1.0 if r["outcome"] == "win" else -1.0) - cost_R)
    net_R = float(np.mean(net)) if net else np.nan
    # أصول موجبة (رفع فوق أساس الأصل)
    pos_assets = 0; tot_assets = 0
    for sym, g in dec.groupby("symbol"):
        gp = (g["outcome"] == "win").mean()
        pos_assets += int(gp > base_p); tot_assets += 1
    return dict(n_signals=n_sig, n_decided=n_dec, win_rate=round(p, 4),
                lift=round((p - base_p) * 100, 3), n_eff=round(n_eff, 1) if not np.isnan(n_eff) else None,
                lower_bound=round(lb, 4) if not np.isnan(lb) else None,
                p_value=round(pval, 5) if not np.isnan(pval) else None,
                net_R=round(net_R, 4) if not np.isnan(net_R) else None,
                pos_assets=pos_assets, tot_assets=tot_assets)


def main():
    print("[L0083] بناء الجدول ...", flush=True)
    panel, settings = build_panel()
    print(f"[L0083] شموع={len(panel)}  إعدادات معرَّفة={len(settings)}", flush=True)

    periods = {"train": TRAIN, "holdout": HOLDOUT, "forward": FORWARD}
    pans = {k: period_slice(panel, v) for k, v in periods.items()}
    base = {k: baseline_stats(v) for k, v in pans.items()}
    base_year = {}
    for y in range(2021, 2027):
        py = panel[panel["year"] == y]
        base_year[y] = baseline_stats(py)

    # الأساس + متوسط cost_R لتقدير حاجز التعادل
    dec_all = panel[panel["outcome"].isin(["win", "loss"])]
    costR_all = []
    for _, r in dec_all.sample(min(20000, len(dec_all)), random_state=SEED).iterrows():
        cb = cost_bps(r["symbol"], int(r["year"])); ap = r["atr_pct"]
        if ap and not np.isnan(ap) and ap > 0:
            costR_all.append(cb / (ap * 100))
    mean_costR = float(np.mean(costR_all))
    pstar = 0.5 + mean_costR / 2
    breakeven_lift = {k: round((pstar - base[k][0]) * 100, 3) for k in pans}

    # المسح
    rows = []
    for name in settings:
        rec = {"setting": name}
        n_produced = 0
        for k in pans:
            sub = pans[k][pans[k]["S_" + name]]
            st = stat_setting(sub, base[k][0])
            if st is None:
                for kk in ("n_signals", "n_decided", "win_rate", "lift", "n_eff",
                           "lower_bound", "p_value", "net_R", "pos_assets", "tot_assets"):
                    rec[f"{k}_{kk}"] = None
            else:
                if st["n_decided"] > 0:
                    n_produced += 1
                for kk, vv in st.items():
                    rec[f"{k}_{kk}"] = vv
        rec["produced_signals"] = n_produced > 0
        rows.append(rec)
    trig = pd.DataFrame(rows)
    trig.to_csv(OUT / "triggers_all.csv", index=False)
    trig.to_csv(ALT / "triggers_all.csv", index=False)

    # ---- الاختبار الحاسم: انتقال الرتبة تدريب→محجوز ----
    comp = trig.dropna(subset=["train_lift", "holdout_lift"]).copy()
    # عينة كافية في الفترتين
    comp = comp[(comp["train_n_eff"].fillna(0) >= 30) & (comp["holdout_n_eff"].fillna(0) >= 30)]
    tl = comp["train_lift"].to_numpy(float); hl = comp["holdout_lift"].to_numpy(float)
    sp = sstats.spearmanr(tl, hl); pe = sstats.pearsonr(tl, hl)
    slope = np.polyfit(tl, hl, 1)[0] if len(tl) >= 3 else np.nan
    pos_tr = comp[comp["train_lift"] > 0]; neg_tr = comp[comp["train_lift"] <= 0]
    stay_pos = int((pos_tr["holdout_lift"] > 0).sum())
    stay_neg = int((neg_tr["holdout_lift"] <= 0).sum())
    winners_hold_mean = round(float(pos_tr["holdout_lift"].mean()), 3) if len(pos_tr) else None
    transfer = {
        "n_settings_compared": int(len(comp)),
        "spearman_rho": round(float(sp.statistic), 4), "spearman_p": round(float(sp.pvalue), 4),
        "pearson_r": round(float(pe.statistic), 4), "pearson_p": round(float(pe.pvalue), 4),
        "shrinkage_slope": round(float(slope), 4),
        "train_positive": int(len(pos_tr)), "stayed_positive_holdout": stay_pos,
        "train_negative": int(len(neg_tr)), "stayed_negative_holdout": stay_neg,
        "winners_mean_holdout_lift": winners_hold_mean,
    }

    # ---- محاكاة العدم: عدد العابرين لحاجز التعادل على المحجوز بالصدفة ----
    be = breakeven_lift["holdout"]
    base_h = base["holdout"][0]
    ns = comp["holdout_n_eff"].fillna(comp["holdout_n_decided"]).to_numpy(float)
    ns = ns[ns > 0].astype(int)
    observed = int((comp["holdout_lift"] >= be).sum())
    NW = 20000
    counts = np.zeros(NW, int)
    for w in range(NW):
        wins = np.random.binomial(ns, base_h)
        lift = (wins / ns - base_h) * 100
        counts[w] = int((lift >= be).sum())
    null = {
        "breakeven_lift_holdout_pts": be,
        "observed_crossers": observed,
        "null_mean": round(float(counts.mean()), 3),
        "null_median": int(np.median(counts)),
        "null_p90_range": [int(np.percentile(counts, 5)), int(np.percentile(counts, 95))],
        "prob_ge_observed": round(float((counts >= observed).mean()), 4),
    }

    summary = {
        "n_settings_defined": len(settings),
        "n_produced": int(trig["produced_signals"].sum()),
        "baseline": {k: {"win": round(base[k][0], 4), "n_decided": base[k][1]} for k in base},
        "baseline_by_year": {y: {"win": round(base_year[y][0], 4), "n": base_year[y][1]} for y in base_year},
        "mean_costR": round(mean_costR, 4), "breakeven_winrate": round(pstar, 4),
        "breakeven_lift_pts": breakeven_lift,
        "transfer_test": transfer,
        "null_sim": null,
    }
    (OUT / "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
