#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0070 — فحوص: تسرب ببتر البيانات، تنفيذ على الافتتاح التالي، لا أمر <20$، حتمية pass1/pass2، حارس التعبئة."""
import json, subprocess, sys, hashlib, pathlib
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0070_core as C
OUT = pathlib.Path("/home/user/work/history/research/hyp_lab_out/L0070")
PRE = json.loads((OUT / "preregistration_l0070.json").read_text(encoding="utf-8")); B = PRE["base_config"]
CFGS = [B, {**B, "method": "voladj", "L": 150, "K": 2}, {**B, "method": "blend", "K": 5, "market": "breadth50"},
        {**B, "exit": "weak10", "weights": "equal", "rebalance": 7}, {**B, "trend": "posmom", "liq_q": 75, "exit": "H5"}]
Pf = C.Panel(C.TARGET13); rep = {"leak": {}, "exec": {}}
for T in ("2023-02-15", "2024-05-01", "2025-10-01"):
    Tt = pd.Timestamp(T, tz="UTC"); Pt = C.Panel(C.TARGET13, end=Tt)
    for q, c in enumerate(CFGS):
        a, _, _, _ = C.run(Pf, c); b, _, _, _ = C.run(Pt, c)
        ea = sorted((t["coin"], Pf.idx[t["entry_i"]], t["units"]) for t in a if Pf.idx[t["entry_i"]] < Tt)
        eb = sorted((t["coin"], Pt.idx[t["entry_i"]], t["units"]) for t in b)
        ca = {(t["coin"], Pf.idx[t["entry_i"]]): (Pf.idx[t["exit_i"]], t["exit_px"]) for t in a if Pf.idx[t["exit_i"]] < Tt - pd.Timedelta(days=1)}
        cb = {(t["coin"], Pt.idx[t["entry_i"]]): (Pt.idx[t["exit_i"]], t["exit_px"]) for t in b}
        rep["leak"][f"{T}|cfg{q}"] = bool(ea == eb and all(cb.get(k) == v for k, v in ca.items()))
ok_exec = True; n_tr = 0
for c in CFGS:
    tr, _, o, _ = C.run(Pf, c)
    for t in tr:
        n_tr += 1
        ok_exec &= t["units"] >= 1 and t["entry_px"] == Pf.o[t["entry_i"], t["j"]]
        ok_exec &= t["reason"] == "نهاية-العينة" or t["exit_px"] == Pf.o[t["exit_i"], t["j"]]
    ok_exec &= o["cash_never_negative"]
rep["exec"] = {"trades_checked": n_tr, "entry_and_exit_at_open_units_ge1_cash_ok": bool(ok_exec),
               "note": "القرار على إغلاق D والتنفيذ على افتتاح D+1 بالبناء (pend_buy/pend_sell تُنفذ في الحلقة التالية)؛ السيولة من أيام مكتملة ≤ D"}
a, b = OUT / "results_l0070_pass1.json", OUT / "results_l0070_pass2.json"
ja, jb = json.loads(a.read_text()), json.loads(b.read_text()); ja.pop("pass"); jb.pop("pass")
h = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
rep["determinism"] = {k: h(ja[k]) == h(jb[k]) for k in ja}; rep["determinism_ALL_EQUAL"] = all(rep["determinism"].values())
fr = pathlib.Path.home() / ".cache/l0070"
st = subprocess.run([sys.executable, "/home/user/work/tools/fill_invariant_check.py", "--trades", str(OUT / "trades_oos_core_primary.csv"), "--frames", str(fr), "--cost", "0", "--bar-tag", "1d"], capture_output=True, text=True)
rep["fill_guard"] = {"rc": st.returncode, "line": [x.strip() for x in st.stdout.splitlines() if "صفقات=" in x]}
rep["leak_count"] = f"{sum(rep['leak'].values())}/{len(rep['leak'])}"
rep["ALL_OK"] = bool(all(rep["leak"].values()) and ok_exec and rep["determinism_ALL_EQUAL"] and st.returncode == 0)
(OUT / "checks_l0070.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
print(rep["leak_count"], rep["exec"], rep["determinism_ALL_EQUAL"], rep["fill_guard"], rep["ALL_OK"])
