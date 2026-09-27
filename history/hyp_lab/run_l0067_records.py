#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0067 — المرحلة 1: سجلات المحرك لكل (مرشح السوق × الحد الزمني × تاريخ القص) على 16 عملة.
    python3 run_l0067_records.py <part> <nparts> [tag]"""
import json, pickle, sys, time
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0067_common as K
part, nparts = int(sys.argv[1]), int(sys.argv[2]); tag = sys.argv[3] if len(sys.argv) > 3 else "pass1"
OUT = K.CACHE / f"recs_{tag}"; OUT.mkdir(exist_ok=True)
CUTS = sorted({w[1] for w in K.WF} | {w[2] for w in K.WF} | {K.SEL[1]}) 
CUTS = [c for c in CUTS if c < K.JUD[1]] + [None]
jobs = [(m, tl, c) for m in ("M0", "M1", "M2") for tl in (None, 90, 180, 365) for c in CUTS]
K.L.set_cost(K.COST)
FILT = {m: K.btc_filter(m) for m in ("M0", "M1", "M2")}
for j, (m, tl, c) in enumerate(jobs):
    if j % nparts != part: continue
    name = f"{m}_{tl}_{'FULL' if c is None else c.date()}.pkl"
    if (OUT / name).exists(): continue
    t0 = time.time()
    recs = {s: K.run_sym(s, end=c, market=FILT[m], tl=tl) for s in K.FULL16}
    pickle.dump(recs, open(OUT / name, "wb"))
    print(name, sum(map(len, recs.values())), round(time.time() - t0, 1), flush=True)
