#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0067 — بوابة المطابقة: محرك المختبر (M0 · بلا حد زمني) على إطارات 4h يجب أن يعيد ملفات صفقات L0064 حرفيًّا."""
import hashlib, json, sys
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0067_common as K
OUT = K.ROOT / "history/research/hyp_lab_out/L0067"; OUT.mkdir(parents=True, exist_ok=True)
REF = K.ROOT / "history/research/hyp_lab_out/L0064"
K.L.set_cost(K.COST)
R = {s: {"bear_cut": K.run_sym(s, end=K.SEL[1]), "bear_full": K.run_sym(s)} for s in K.FULL16}
rep, ok = {}, True
for b, coins in (("FULL16", K.FULL16), ("TARGET13", K.TARGET13)):
    for w in ("SEL", "JUD", "FULL"):
        key = "bear_cut" if w == "SEL" else "bear_full"
        s_, e_ = {"SEL": K.SEL, "JUD": K.JUD, "FULL": (K.SEL[0], K.JUD[1])}[w]
        rows = [r for c in coins for r in K.rows_in(R[c][key], s_, e_)]
        p = K.save_trades(OUT / f"match_{b}_{w}.csv", rows)
        a = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        r = hashlib.sha256((REF / f"trades_strategy_{b}_{w}.csv").read_bytes()).hexdigest()[:16]
        rep[f"{b}_{w}"] = {"lab": a, "L0064": r, "match": a == r, "rows": len(rows)}
        ok &= a == r; p.unlink()
        print(b, w, a, r, a == r, len(rows))
rep["MATCH_GATE_PASSED"] = bool(ok)
(OUT / "match_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2))
sys.exit(0 if ok else 1)
