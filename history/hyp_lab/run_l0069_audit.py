#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0069 — بوابة القياس: مطابقة مستقلة للنسخ الأربع (محاذاة code/text × V3/V2)، اختبار ذهبي زمني D1،
فرق D1 على مستوى الصفقة، سجل ذهبي للنسخة المصححة، واختبار تسرب ببتر البيانات."""
from __future__ import annotations
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0067_common as K
import l0068_replayer as RP
import l0069_engine as E9
OUT = K.ROOT / "history/research/hyp_lab_out/L0069"; OUT.mkdir(parents=True, exist_ok=True)
K.L.set_cost(K.COST)
TR = K.TARGET13
KEY = lambda r: (r["symbol"], r["entry_time"], r["exit_time"], int(r["stage"]), r["reason"], round(float(r["exit_px"]), 8), round(float(r["pnl_usd"]), 6))
VARIANTS = {"code_V3": ("code", True), "code_V2": ("code", False), "text_V3": ("text", True), "text_V2": ("text", False)}
rep = {}

# ── 1) مطابقة: نسخة المختبر من المحرك مقابل المُعيد المستقل (لا SHA؛ حقول الإشارة والمرحلة والمخرج) ──
match = {}
ENG, REP = {}, {}
for vn, (ctx, gate) in VARIANTS.items():
    m = {"runs": 0, "slices": 0, "mismatch_runs": []}
    for s in TR:
        for tag, end in (("SEL_cut", K.SEL[1]), ("FULL", None)):
            fr = K.h4(s) if end is None else K.h4(s)[K.h4(s).index < end]
            a = K.L.from_engine(E9.run(fr, s, ctx=ctx, gate=gate), s) if len(fr) else []
            b = RP.replay(fr, s, gate=gate, ctx_extra_lag=(ctx == "text"))
            ENG[(vn, s, tag)], REP[(vn, s, tag)] = a, b
            m["runs"] += 1; m["slices"] += len(a)
            if sorted(map(KEY, a)) != sorted(map(KEY, b)):
                m["mismatch_runs"].append(f"{s}:{tag}")
    m["MATCH"] = not m["mismatch_runs"]
    match[vn] = m
    print("مطابقة", vn, m, flush=True)
# نسخة المختبر (code_V3) = محرك L0067 الأصلي حرفيًا
copy_ok = all(sorted(map(KEY, ENG[("code_V3", s, "FULL")])) == sorted(map(KEY, K.run_sym(s))) for s in TR)
match["engine_copy_equals_L0067_engine"] = bool(copy_ok)
rep["match"] = match

# ── 2) الاختبار الذهبي الزمني D1 (قوة غاشمة شمعة بشمعة) ──
def brute_ctx(h4, lag_days):
    d = RP.daily_of(h4); dl, dh = d["low"].to_numpy(), d["high"].to_numpy(); dend = d.index + pd.Timedelta(days=1)
    PL = np.full(len(h4), np.nan); PH = np.full(len(h4), np.nan)
    for i, t in enumerate(h4.index):
        # الأيام المغلقة بالكامل قبل (t − lag): نهاية اليوم ≤ t − lag
        k = int(np.searchsorted(dend.values, (t - pd.Timedelta(days=lag_days)).to_datetime64(), side="right"))
        a = max(0, k - 90)
        if k - a >= 30:
            PL[i], PH[i] = dl[a:k].min(), dh[a:k].max()
    return PL, PH
d1 = {}
for vn, lag in (("code", 0), ("text", 1)):
    bad_ctx = bad_clim = bad_exec = 0; bars = 0
    for s in TR:
        fr = K.h4(s)
        if len(fr) < 200: continue
        tr = {}; rows = RP.replay(fr, s, trace=tr, ctx_extra_lag=(vn == "text"))
        PL, PH = brute_ctx(fr, lag)
        both = np.isfinite(PL) | np.isfinite(tr["PL"])
        bad_ctx += int((~np.isclose(PL[both], tr["PL"][both], equal_nan=True) | ~np.isclose(PH[both], tr["PH"][both], equal_nan=True)).sum())
        # المناخ: وسم اليوم D = تصنيف إغلاق D-1 (إغلاق معروف قبل أي شمعة من D)
        d = RP.daily_of(fr); c = d["close"].to_numpy(); e50, e200 = RP.ema(c, 50), RP.ema(c, 200)
        sl = np.full(len(c), np.nan); sl[10:] = e50[10:] - e50[:-10]; bear = (e50 < e200) & (sl < 0)
        lab = {d.index[k]: bool(bear[k - 1]) for k in range(1, len(c))}
        exp = np.array([lab.get(t.normalize(), False) for t in fr.index])
        bad_clim += int((exp != tr["ok"]).sum())
        bad_exec += sum(1 for r in rows if r["entry_bar"] != r["signal_bar"] + 1)
        bars += len(fr)
    d1[vn] = {"bars_checked": bars, "ctx_mismatch": bad_ctx, "climate_mismatch": bad_clim, "exec_not_next_open": bad_exec,
              "rule": "code: أيام منتهية ≤ وقت الشمعة" if vn == "code" else "text: أيام منتهية ≤ وقت الشمعة − يوم"}
    print("D1 ذهبي", vn, d1[vn], flush=True)
# D1 على مستوى الصفقة (V3، التشغيل الكامل)
def keyset(rows): return {(r["symbol"], int(r["stage"]), r["entry_time"]): r for r in rows}
diff = {"only_code_entries": 0, "only_text_entries": 0, "same_entry_diff_exit": 0, "same_entry_diff_reason": 0, "common": 0, "examples": []}
for g in ("V3", "V2"):
    dd = {"only_code_entries": 0, "only_text_entries": 0, "same_entry_diff_exit": 0, "same_entry_diff_reason": 0, "common": 0,
          "code_cycles": 0, "text_cycles": 0, "examples": []}
    for s in TR:
        a = keyset(REP[(f"code_{g}", s, "FULL")]); b = keyset(REP[(f"text_{g}", s, "FULL")])
        dd["code_cycles"] += sum(1 for k in a if k[1] == 0); dd["text_cycles"] += sum(1 for k in b if k[1] == 0)
        dd["only_code_entries"] += len(a.keys() - b.keys()); dd["only_text_entries"] += len(b.keys() - a.keys())
        for k in a.keys() & b.keys():
            dd["common"] += 1
            if a[k]["exit_time"] != b[k]["exit_time"]:
                dd["same_entry_diff_exit"] += 1
                if len(dd["examples"]) < 8:
                    dd["examples"].append({"key": list(k), "code_exit": a[k]["exit_time"], "code_reason": a[k]["reason"],
                                           "text_exit": b[k]["exit_time"], "text_reason": b[k]["reason"]})
            if a[k]["reason"] != b[k]["reason"]:
                dd["same_entry_diff_reason"] += 1
        for k in sorted(a.keys() - b.keys())[:1] + sorted(b.keys() - a.keys())[:1]:
            if len(dd["examples"]) < 14:
                dd["examples"].append({"key": list(k), "in": "code" if k in a else "text"})
    diff[g] = dd
    print("D1 فرق الصفقات", g, {k: v for k, v in dd.items() if k != "examples"}, flush=True)
rep["D1_golden_time"] = d1
rep["D1_trade_diff"] = {g: diff[g] for g in ("V3", "V2")}

# ── 3) السجل الذهبي للنسخة المصححة V3 (text) مقابل نسخة المحرك ──
def cyc_of(rows):
    out, cur = [], []
    for r in sorted(rows, key=lambda r: (r["entry_bar"], r["stage"])):
        if r["stage"] == 0 and cur:
            out.append(cur); cur = []
        cur.append(r)
    if cur: out.append(cur)
    return out
cands = []
for s in TR:
    fr = K.h4(s); tr = {}; RP.replay(fr, s, trace=tr, ctx_extra_lag=True)
    for g in cyc_of(REP[("text_V3", s, "FULL")]):
        sb = g[0]["signal_bar"]
        cands.append({"symbol": s, "cycle_start": g[0]["entry_time"], "cycle_end": max(r["exit_time"] for r in g),
                      "signal_time": fr.index[sb].isoformat(), "exec_time": g[0]["entry_time"],
                      "prior90_low_used": float(tr["PL"][sb]), "prior90_high_used": float(tr["PH"][sb]),
                      "signal_close": float(fr["close"].iloc[sb]), "ema20": float(tr["e20"][sb]),
                      "stages": [{"stage": r["stage"], "time": r["entry_time"], "px": r["entry_px"], "order_usd": 20.0,
                                  "exit_time": r["exit_time"], "exit_px": r["exit_px"], "reason": r["reason"],
                                  "ret_gross_pct": round(100 * (r["exit_px"] / r["entry_px"] - 1), 4)} for r in g],
                      "n_stages": len(g), "reasons": sorted({r["reason"] for r in g}),
                      "gross_20usd": round(sum(20 * (r["exit_px"] / r["entry_px"] - 1) for r in g), 4),
                      "no_add_after_invalidation": all(not (r2["entry_bar"] > r["exit_bar"] and r["reason"] == "إلغاء-دورة") for r in g for r2 in g)})
cdf = pd.DataFrame(cands); pick = []
def take(mask, k):
    for i in cdf[mask & ~cdf.index.isin(pick)].sort_values("cycle_start").index[:k]:
        pick.append(i)
for s in TR:
    sub = cdf.symbol == s
    take(sub & (cdf.gross_20usd > 0), 1); take(sub & (cdf.gross_20usd <= 0), 1)
take(cdf.n_stages >= 3, 4); take(cdf.reasons.map(lambda x: "نهاية-العينة" in x), 3)
take(cdf.reasons.map(lambda x: "إلغاء-دورة" in x) & (cdf.n_stages >= 2), 3)
take(cdf.index >= 0, max(0, 34 - len(set(pick))))
gold = cdf.loc[sorted(set(pick))]
eng_map = {(r["symbol"], r["entry_time"], int(r["stage"])): r for (vn, s_, t), rows in ENG.items() if vn == "text_V3" and t == "FULL" for r in rows}
ok = []
for _, g in gold.iterrows():
    good = True
    for st in g.stages:
        e = eng_map.get((g.symbol, st["time"], int(st["stage"])))
        good &= e is not None and e["exit_time"] == st["exit_time"] and e["reason"] == st["reason"] and abs(e["exit_px"] - st["exit_px"]) < 1e-9
    ok.append(bool(good))
gold = gold.assign(engine_match=ok)
(OUT / "golden_record_corrected_v3.json").write_text(gold.to_json(orient="records", force_ascii=False, indent=1), encoding="utf-8")
rep["golden"] = {"cycles": len(gold), "coins": int(gold.symbol.nunique()), "winners": int((gold.gross_20usd > 0).sum()),
                 "losers": int((gold.gross_20usd <= 0).sum()), "multi_stage": int((gold.n_stages > 1).sum()),
                 "all_engine_match": bool(all(ok)), "no_add_after_invalidation": bool(gold.no_add_after_invalidation.all()),
                 "total_cycles_available": len(cdf)}
print("السجل الذهبي:", rep["golden"], flush=True)

# ── 4) تسرب المستقبل: بتر عند T — الدخولات قبل T والمخارج المغلقة قبل T متطابقة ──
leak = {}
for T in ("2022-11-15", "2024-02-01", "2025-07-01"):
    Tt = K.T(T)
    for s in TR:
        fr = K.h4(s); ft = fr[fr.index < Tt]
        if len(ft) < 250: continue
        for g in (True, False):
            a = RP.replay(fr, s, gate=g, ctx_extra_lag=True); b = RP.replay(ft, s, gate=g, ctx_extra_lag=True)
            ea = sorted((r["entry_time"], r["stage"]) for r in a if pd.Timestamp(r["entry_time"]) < Tt)
            eb = sorted((r["entry_time"], r["stage"]) for r in b)
            ca = {(r["entry_time"], r["stage"]): (r["exit_time"], r["reason"], round(r["exit_px"], 10)) for r in a if pd.Timestamp(r["exit_time"]) < Tt - pd.Timedelta(hours=4)}
            cb = {(r["entry_time"], r["stage"]): (r["exit_time"], r["reason"], round(r["exit_px"], 10)) for r in b}
            leak[f"{T}|{s}|{'V3' if g else 'V2'}"] = bool(ea == eb and all(cb.get(k) == v for k, v in ca.items()))
rep["leak"] = {"cases": len(leak), "ok": int(sum(leak.values())), "failed": [k for k, v in leak.items() if not v]}
print("تسرب:", rep["leak"], flush=True)
rep["MEASUREMENT_GATE_PARTIAL"] = bool(all(m["MATCH"] for k, m in match.items() if isinstance(m, dict)) and copy_ok
                                       and all(v["ctx_mismatch"] == 0 and v["climate_mismatch"] == 0 and v["exec_not_next_open"] == 0 for v in d1.values())
                                       and rep["golden"]["all_engine_match"] and rep["golden"]["cycles"] >= 34 and rep["golden"]["no_add_after_invalidation"]
                                       and not rep["leak"]["failed"])
(OUT / "audit_l0069.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("بوابة القياس (جزئي):", rep["MEASUREMENT_GATE_PARTIAL"])
