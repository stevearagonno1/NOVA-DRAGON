#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0067 — قراءة بعدية للسياق فقط (بعد قفل الاختيار وتوثيقه): الحكم لكل النسخ الست والثلاثين على المحفظة المشتركة،
ونتائج كل النسخ في نوافذ Walk-Forward الخارجية. ليست اختيارًا ولا يجوز أن تُستعمل لاختيار نسخة (ورقة L0067)."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, "/home/user/work/history/hyp_lab")
sys.path.insert(0, "/home/user/work/history/hyp_lab/l0067_replication_b")
import run_l0067_measure as R
W_SEL, W_JUD = R.Win("SEL", R.T0, R.CUT), R.Win("JUD", R.CUT, R.END)
cs = R.coin_sets(W_SEL)
out = {"note": "قراءة بعدية بعد قفل الاختيار (المثبَّت = M0_C0_none بالقاعدة). للسياق فقط.", "versions": {}}
for m in R.MARKETS:
    for t in R.TLIMITS:
        for c in R.CSETS:
            k = f"{m}_{c}_{t}"; out["versions"][k] = {}
            for wname, w in (("SEL", W_SEL), ("JUD", W_JUD)):
                rows = R.rows_version(cs[c], m, t, w)
                srows, st = R.shared_portfolio(rows, R.POOL, R.CAP)
                mt = R.metrics(srows, w, cs[c], R.POOL)
                out["versions"][k][wname] = {kk: mt.get(kk) for kk in ("net115", "net130", "cycles", "peak", "ret_pct_peak", "dd_pct_peak", "underwater_days", "avg_slice", "win_rate_pct", "top_coin", "top_share_pct", "best_month_share", "annualized_net")}
# WF OOS لكل نسخة (بمجموعات العملات المشتقة من الجزء الأول لكل نافذة)
wfv = {}
for wname, (is_end, oos_end) in R.WF.items():
    w_is, w_oos = R.Win(wname + "_IS", R.T0, is_end), R.Win(wname + "_OOS", is_end, oos_end)
    css = R.coin_sets(w_is); wfv[wname] = {}
    for m in R.MARKETS:
        for t in R.TLIMITS:
            for c in ("C0", "C1"):
                rows, _ = R.shared_portfolio(R.rows_version(css[c], m, t, w_oos), R.POOL, R.CAP)
                mt = R.metrics(rows, w_oos, css[c], R.POOL)
                wfv[wname][f"{m}_{c}_{t}"] = {"net": mt["net115"], "cycles": mt["cycles"], "dd_pct": mt.get("dd_pct_peak")}
out["walkforward_oos_all_versions"] = wfv
summ = {}
for k in out["versions"]:
    nets = [wfv[w].get(k, {}).get("net", 0.0) for w in R.WF]
    if k in wfv["W1"]:
        summ[k] = {"n_positive": int(sum(x > 0 for x in nets)), "sum": round(sum(nets), 2), "median": round(sorted(nets)[len(nets)//2 - 1] * 0.5 + sorted(nets)[len(nets)//2] * 0.5, 2), "nets": nets}
out["walkforward_summary_all_versions"] = summ
p = R.OUT / "context_all_versions.json"; p.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("JUD (مشترك 13k) لكل النسخ — للسياق:")
for k, v in sorted(out["versions"].items(), key=lambda x: -(x[1]["JUD"]["net115"] or 0)):
    s, j = v["SEL"], v["JUD"]
    print(f"  {k:14s} SEL {s['net115']:>8} ({s['cycles']:>3}c dd {s['dd_pct_peak']!s:>7} uw {s['underwater_days']!s:>6}) | JUD {j['net115']:>8} ({j['cycles']:>3}c dd {j['dd_pct_peak']!s:>7} uw {j['underwater_days']!s:>6} bestM {j['best_month_share']!s:>6}) | WF +{summ.get(k,{}).get('n_positive','-')}/8 sum {summ.get(k,{}).get('sum','-')}")
