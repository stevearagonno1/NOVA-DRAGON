#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0067 — فحوص: تسرب المستقبل (مرشح BTC والحد الزمني) · حارس التعبئة · تتابع/سقف المحفظة المشتركة (من results.json)."""
import json, subprocess, sys, pathlib
import pandas as pd
sys.path.insert(0, "/home/user/work/history/hyp_lab")
import l0067_common as K
OUT = K.ROOT / "history/research/hyp_lab_out/L0067"
K.L.set_cost(K.COST)
rep = {"leakage": {}, "fill_guard": {}, "shared_sequencing": {}}
ok = True
DATES = ("2022-09-01", "2023-06-01", "2025-03-01"); COINS = ("BTCUSDT", "ETHUSDT", "ATOMUSDT", "LINKUSDT")
for m in ("M1", "M2"):
    full = K.btc_filter(m)
    for T in DATES:
        Tt = K.T(T); saved = K._H4.pop("BTCUSDT")
        K._H4["BTCUSDT"] = saved[saved.index < Tt]
        tr = K.btc_filter(m); K._H4["BTCUSDT"] = saved
        same = all(tr[d] == full[d] for d in tr)
        rep["leakage"][f"filter_{m}_{T}"] = same; ok &= same
for m, tl in (("M0", 90), ("M2", 365), ("M1", 180)):
    filt = K.btc_filter(m)
    for sym in COINS:
        fullr = K.run_sym(sym, market=filt, tl=tl)
        for T in DATES:
            Tt = K.T(T)
            trr = K.run_sym(sym, end=Tt, market=filt, tl=tl)
            kf = sorted((r["entry_time"], r["stage"]) for r in fullr if pd.Timestamp(r["entry_time"]) < Tt)
            kt = sorted((r["entry_time"], r["stage"]) for r in trr)
            closed = {(r["entry_time"], r["stage"]): (r["exit_time"], r["reason"]) for r in fullr if pd.Timestamp(r["exit_time"]) < Tt}
            tmap = {(r["entry_time"], r["stage"]): (r["exit_time"], r["reason"]) for r in trr}
            ex = all(tmap.get(k) == v for k, v in closed.items())
            rep["leakage"][f"engine_{m}_{tl}_{sym}_{T}"] = bool(kf == kt and ex); ok &= kf == kt and ex
fr = pathlib.Path.home() / ".cache/l0067/frames_pq"; fr.mkdir(exist_ok=True)
for s in K.FULL16:
    K.h4(s).to_parquet(fr / f"{s}_4h.parquet")
for f in sorted(OUT.glob("trades_*.csv")):
    st = subprocess.run([sys.executable, str(K.ROOT / "tools/fill_invariant_check.py"), "--trades", str(f), "--frames", str(fr),
                         "--cost", "0", "--bar-tag", "4h"], capture_output=True, text=True)
    tail = (st.stdout.strip().splitlines() or [""])[-1]
    rep["fill_guard"][f.name] = {"rc": st.returncode, "tail": tail}; ok &= st.returncode == 0
R = json.load(open(OUT / "results.json"))
for lab, d in R["blocks"].items():
    for w, b in d.items():
        lg = b["shared"]["shared_log"]
        rep["shared_sequencing"][f"{lab}_{w}"] = lg; ok &= lg["cap_violations"] == 0 and lg["overdraft"] == 0
rep["ALL_OK"] = bool(ok)
(OUT / "checks.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
print(json.dumps({k: (v if k != "leakage" else all(v.values())) for k, v in rep.items()}, ensure_ascii=False, indent=1))
