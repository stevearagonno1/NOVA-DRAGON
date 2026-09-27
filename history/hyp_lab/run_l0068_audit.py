#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0068 — المسار الأول: تدقيق المطابقة.
1) المُعيد المستقل (l0068_replayer، لا يستورد nova_v8) مقابل محرك L0064 صفقةً صفقة على TARGET13 (قص الاختيار + التشغيل الكامل).
2) السجل الذهبي: 24 دورة على 8 عملات بكل الحقول المطلوبة.
3) قياس أثر كل اختلاف بين القواعد والكود بمعزل عن غيره.
"""
from __future__ import annotations
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0067_common as K
import l0068_replayer as RP
import nova_v8.config as C
OUT = K.ROOT / "history/research/hyp_lab_out/L0068"; OUT.mkdir(parents=True, exist_ok=True)
K.L.set_cost(K.COST)
TR = K.TARGET13
KEY = lambda r: (r["symbol"], r["entry_time"], r["exit_time"], int(r["stage"]), r["reason"], round(float(r["exit_px"]), 8), round(float(r["pnl_usd"]), 6))

# ── 1) مطابقة كاملة ──
full = {"runs": 0, "slices": 0, "mismatch_runs": [], "fields": ["symbol", "entry_time", "exit_time", "stage", "reason", "exit_px(1e-8)", "pnl(1e-6)"]}
ENG, REP = {}, {}
for s in TR:
    for tag, end in (("SEL_cut", K.SEL[1]), ("FULL", None)):
        fr = K.h4(s) if end is None else K.h4(s)[K.h4(s).index < end]
        a = K.run_sym(s, end=end); b = RP.replay(fr, s)
        ENG[(s, tag)], REP[(s, tag)] = a, b
        full["runs"] += 1; full["slices"] += len(a)
        if sorted(map(KEY, a)) != sorted(map(KEY, b)):
            full["mismatch_runs"].append(f"{s}:{tag}")
full["MATCH"] = not full["mismatch_runs"]
print("مطابقة المُعيد المستقل:", full, flush=True)

# ── 2) السجل الذهبي ──
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
    rows = REP[(s, "FULL")]
    fr = K.h4(s); tr = {}; RP.replay(fr, s, trace=tr)
    for g in cyc_of(rows):
        pnl = sum(r["pnl_usd"] for r in g)
        reasons = sorted({r["reason"] for r in g})
        e0, e1 = min(r["entry_bar"] for r in g), max(r["exit_bar"] for r in g)
        span = range(e0, e1 + 1)
        rej_gate = int(sum(1 for i in span if tr["sig"][i] and not tr["ok"][i]))
        rej_top = int(sum(1 for i in span if tr["sig"][i] and tr["ok"][i] and tr["top"][i]))
        sb = g[0]["signal_bar"]
        cands.append({"symbol": s, "cycle_start": g[0]["entry_time"], "cycle_end": max(r["exit_time"] for r in g),
                      "tf": "4h", "signal_time": fr.index[sb].isoformat(), "exec_bar_time": g[0]["entry_time"],
                      "ref_zone_prior90_low": round(float(tr["PL"][sb]), 8), "zone_threshold_x1.08": round(float(tr["PL"][sb] * 1.08), 8),
                      "prior90_high": round(float(tr["PH"][sb]), 8), "signal_close": float(fr["close"].iloc[sb]), "ema20": round(float(tr["e20"][sb]), 8),
                      "allow_reason": "رُئيت المنطقة + MSS(6) + إغلاق>EMA20 + مناخ العملة «هابط» (أمس)",
                      "rejected_signals_in_cycle_by_climate": rej_gate, "rejected_signals_in_cycle_top_seen": rej_top,
                      "stages": [{"stage": r["stage"], "time": r["entry_time"], "px": r["entry_px"], "notional_research": r["notional_usd"],
                                  "notional_rule_20usd": 20.0, "exit_time": r["exit_time"], "exit_px": r["exit_px"], "exit_reason": r["reason"],
                                  "gross": round((r["exit_px"] / r["entry_px"] - 1) * r["notional_usd"], 4), "net_0.115": round(r["pnl_usd"], 4)} for r in g],
                      "n_stages": len(g), "reasons": reasons, "net_0.115_research": round(pnl, 4),
                      "cost": "0.115% لكل طرف · انزلاق 0 (مسطرة البحث)", "capital_available": "دفتر 1000$ للعملة؛ لا قيد مشترك (13×1000=13000)",
                      "no_add_after_invalidation": all(not (r2["entry_bar"] > r["exit_bar"] and r["reason"] == "إلغاء-دورة") for r in g for r2 in g)})
cdf = pd.DataFrame(cands)
pick = []
def take(mask, k):
    for i in cdf[mask & ~cdf.index.isin(pick)].sort_values("cycle_start").index[:k]:
        pick.append(i)

for s in TR:  # عملة ثم فئات
    sub = cdf.symbol == s
    take(sub & (cdf["net_0.115_research"] > 0) & (cdf.n_stages == 1), 1)
    take(sub & (cdf["net_0.115_research"] <= 0), 1)
take(cdf.n_stages >= 3, 3)
take(cdf.reasons.map(lambda x: "نهاية-العينة" in x), 3)
take(cdf.reasons.map(lambda x: "إلغاء-دورة" in x) & (cdf.n_stages >= 2), 2)
gold = cdf.loc[sorted(set(pick))]
# تحقق كل دورة ذهبية مقابل المحرك
eng_map = {(r["symbol"], r["entry_time"], int(r["stage"])): r for (s_, t), rows in ENG.items() if t == "FULL" for r in rows}
gold_ok = []
for _, g in gold.iterrows():
    ok = True
    for st in g.stages:
        e = eng_map.get((g.symbol, st["time"], int(st["stage"])))
        ok &= e is not None and e["exit_time"] == st["exit_time"] and e["reason"] == st["exit_reason"] \
            and abs(e["exit_px"] - st["exit_px"]) < 1e-9 and abs(e["pnl_usd"] - st["net_0.115"]) < 1e-4
    gold_ok.append(bool(ok))
gold = gold.assign(engine_match=gold_ok)
summary_gold = {"n": len(gold), "coins": int(gold.symbol.nunique()), "winners": int((gold["net_0.115_research"] > 0).sum()),
                "losers": int((gold["net_0.115_research"] <= 0).sum()), "single_stage": int((gold.n_stages == 1).sum()),
                "multi_stage": int((gold.n_stages > 1).sum()), "invalidation": int(gold.reasons.map(lambda x: "إلغاء-دورة" in x).sum()),
                "end_of_sample": int(gold.reasons.map(lambda x: "نهاية-العينة" in x).sum()), "all_engine_match": bool(all(gold_ok)),
                "no_add_after_invalidation": bool(gold.no_add_after_invalidation.all())}
(OUT / "golden_record.json").write_text(gold.to_json(orient="records", force_ascii=False, indent=1), encoding="utf-8")
print("السجل الذهبي:", summary_gold, flush=True)

# ── 3) أثر كل اختلاف معزولًا (TARGET13 · الاختيار والحكم) ──
def net_of(rows_by_sym, window, cost=K.COST, size=None, slip_fn=None):
    s0, e0 = window
    tot = 0.0; n = 0; gross = 0.0
    for s, rows in rows_by_sym.items():
        for r in rows:
            t = pd.Timestamp(r["entry_time"])
            if not (s0 <= t < e0): continue
            no = size if size is not None else r["notional_usd"]
            ce = cost + (slip_fn(s, r["entry_bar"]) if slip_fn else 0.0)
            cx = cost + (slip_fn(s, r["exit_bar"]) if slip_fn else 0.0)
            ep = r["entry_px"] * (1 + (slip_fn(s, r["entry_bar"]) if slip_fn else 0.0))
            tot += ((r["exit_px"] / ep) * (1 - cx) - (1 + cost)) / (1 + cost) * no
            gross += (r["exit_px"] / r["entry_px"] - 1) * no; n += 1
    return round(tot, 2), round(gross, 2), n

base = {w: {s: REP[(s, "SEL_cut" if w == "SEL" else "FULL")] for s in TR} for w in ("SEL", "JUD")}
WIN = {"SEL": K.SEL, "JUD": K.JUD}
lag = {"SEL": {s: RP.replay(K.h4(s)[K.h4(s).index < K.SEL[1]], s, ctx_extra_lag=True) for s in TR},
       "JUD": {s: RP.replay(K.h4(s), s, ctx_extra_lag=True) for s in TR}}
v2 = {"SEL": {s: RP.replay(K.h4(s)[K.h4(s).index < K.SEL[1]], s, gate=False) for s in TR},
      "JUD": {s: RP.replay(K.h4(s), s, gate=False) for s in TR}}
# مضاعف الانزلاق الصحيح: VR = ATR14 / متوسط ATR14 على 100 شمعة (كما في بقية المحرك)، لا ATR%
VR = {}
for s in TR:
    fr = K.h4(s); tr_ = pd.concat([fr.high - fr.low, (fr.high - fr.close.shift()).abs(), (fr.low - fr.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr_.ewm(alpha=1 / 14, adjust=False).mean(); VR[s] = (atr / atr.rolling(100).mean()).to_numpy()
    VR[s + "_pct"] = (atr / fr.close).to_numpy()
def slip_mult(v):
    return 3.0 if v >= 1.5 else 2.0 if v >= 1.2 else 1.0
slip_code = lambda s, i: 0.0003 * slip_mult(VR[s + "_pct"][i - 1] if i > 0 else np.nan)      # ما يفعله الكود (ATR% كـVR)
slip_rule = lambda s, i: 0.0003 * slip_mult(VR[s][i - 1] if i > 0 and np.isfinite(VR[s][i - 1]) else 0)  # القاعدة
mult_hits = {s: int(sum(slip_mult(v) > 1 for v in VR[s + "_pct"] if np.isfinite(v))) for s in TR}
div = {}
for w in ("SEL", "JUD"):
    b = base[w]
    div[w] = {
        "research_L0064 (1000$ دفتر، 0.115%، انزلاق 0)": net_of(b, WIN[w]),
        "ctx_extra_lag كما في تعليق الكود": net_of(lag[w], WIN[w]),
        "V2 بلا بوابة المناخ (الافتراضي المعتمد في الدستور)": net_of(v2[w], WIN[w]),
        "حجم 20$ لكل شريحة (قاعدة §27)": net_of(b, WIN[w], size=20.0),
        "20$ · 0.10% + انزلاق 0.03% (مضاعف الكود = 1 دائمًا)": net_of(b, WIN[w], cost=0.0010, size=20.0, slip_fn=slip_code),
        "20$ · 0.10% + انزلاق 0.03% ×2/×3 بـVR الصحيح": net_of(b, WIN[w], cost=0.0010, size=20.0, slip_fn=slip_rule),
        "20$ · 0.10% + انزلاق 0.10%": net_of(b, WIN[w], cost=0.0010, size=20.0, slip_fn=lambda s, i: 0.0010),
        "20$ · 0.10% + انزلاق 0.30%": net_of(b, WIN[w], cost=0.0010, size=20.0, slip_fn=lambda s, i: 0.0030),
    }
hold = []
for w in ("SEL", "JUD"):
    for s, rows in base[w].items():
        for r in rows:
            if WIN[w][0] <= pd.Timestamp(r["entry_time"]) < WIN[w][1]:
                hold.append(r["exit_bar"] - r["entry_bar"])
hold_days = np.array(hold) * 4 / 24
rep = {"full_match": full, "golden_summary": summary_gold, "divergence_impact_TARGET13": div,
       "vol_multiplier_bug": {"passed_value": "ATR14/close (≈0.01–0.10)", "threshold_highvol_vr": C.SPREAD_HIGHVOL_VR, "threshold_shock": C.VR_SHOCK,
                              "bars_where_code_multiplier_>1": mult_hits},
       "holding_days": {"median": float(np.median(hold_days)), "p75": float(np.percentile(hold_days, 75)), "max": float(hold_days.max()),
                        "share_ge_90d": float((hold_days >= 90).mean())},
       "sizing": {"research_notional_per_tranche": [1000 * x for x in C.LONG_CYCLE_STAGE_WEIGHTS], "rule_§27": 20.0,
                  "config_comment": "LONG_CYCLE_CAPITAL_USD = 1000.0 # experiment BOOK (§27), not trade size; each fill still 20$ pending sleeve rewrite"}}
(OUT / "audit_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: rep[k] for k in ("divergence_impact_TARGET13", "vol_multiplier_bug", "holding_days")}, ensure_ascii=False, indent=1))
