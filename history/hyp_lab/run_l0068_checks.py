#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0068 — فحوص المسار الثاني: تسرب المستقبل في المحاكي (بتر البيانات عند T بما فيها BTC والاتساع)، حارس التعبئة، الحتمية."""
import json, subprocess, sys, pathlib, hashlib
import pandas as pd
sys.path.insert(0, "/home/user/repo/history/hyp_lab")
import l0067_common as K
import l0068_sim as S
OUT = K.ROOT / "history/research/hyp_lab_out/L0068"
COINS = list(K.TARGET13)
full = {s: K.h4(s) for s in COINS}
mk = S.market_by_day(full, COINS)
CF = {s: S.Coin(s, full[s], mk) for s in COINS}
CFG = [{"L": 90, "D": 20, "rec": "MSS6+EMA20"}, {"L": 20, "D": 8, "rec": "MSS3", "market": "breadth50"},
       {"L": 60, "D": 12, "rec": "C>EMA50", "trend": "ema200", "aux": "rsi40"}, {"L": 30, "D": 16, "rec": "MSS12", "inv": "atr2", "exit": "partial", "tl": 90},
       {"L": 90, "D": 20, "rec": "MSS6+EMA20", "market": "btc200_50", "stages": 2}]
rep = {"leakage": {}, "fill_guard": {}}
ok = True
for T in ("2022-11-15", "2024-02-01", "2025-07-01"):
    Tt = K.T(T)
    tr = {s: full[s][full[s].index < Tt] for s in COINS if (full[s].index < Tt).sum() > 250}
    mt = S.market_by_day({**tr, "BTCUSDT": tr["BTCUSDT"]}, [s for s in COINS if s in tr])
    for s in ("BTCUSDT", "ETHUSDT", "LINKUSDT", "SOLUSDT"):
        ct = S.Coin(s, tr[s], mt)
        for j, p in enumerate(CFG):
            a = S.run(CF[s], p); b = S.run(ct, p)
            ka = sorted((r["entry_bar"], r["stage"]) for r in a if CF[s].idx[r["entry_bar"]] < Tt)
            kb = sorted((r["entry_bar"], r["stage"]) for r in b)
            closed = {(r["entry_bar"], r["stage"]): (r["exit_bar"], r["reason"], round(r["exit_px"], 10)) for r in a if CF[s].idx[r["exit_bar"]] < Tt - pd.Timedelta(hours=4)}
            mb = {(r["entry_bar"], r["stage"]): (r["exit_bar"], r["reason"], round(r["exit_px"], 10)) for r in b}
            good = ka == kb and all(mb.get(k) == v for k, v in closed.items())
            rep["leakage"][f"{T}_{s}_cfg{j}"] = good; ok &= good
fr = pathlib.Path.home() / ".cache/l0068_frames"; fr.mkdir(exist_ok=True)
for s in COINS:
    full[s].to_parquet(fr / f"{s}_4h.parquet")
for f in sorted(OUT.glob("trades_oos_*.csv")):
    st = subprocess.run([sys.executable, str(K.ROOT / "tools/fill_invariant_check.py"), "--trades", str(f), "--frames", str(fr), "--cost", "0", "--bar-tag", "4h"],
                        capture_output=True, text=True)
    line = [x for x in st.stdout.splitlines() if "صفقات=" in x]
    rep["fill_guard"][f.name] = {"rc": st.returncode, "line": line[0].strip() if line else st.stdout[-300:]}; ok &= st.returncode == 0
a, b = OUT / "walkforward_results_pass1.json", OUT / "walkforward_results_pass2.json"
if a.exists() and b.exists():
    ja, jb = json.loads(a.read_text()), json.loads(b.read_text()); ja.pop("pass"); jb.pop("pass")
    h = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    rep["determinism"] = {k: {"pass1": h(ja[k]), "pass2": h(jb[k]), "equal": h(ja[k]) == h(jb[k])} for k in ja}
    rep["determinism_ALL_EQUAL"] = all(v["equal"] for v in rep["determinism"].values()); ok &= rep["determinism_ALL_EQUAL"]
rep["leak_count"] = f"{sum(rep['leakage'].values())}/{len(rep['leakage'])}"
rep["ALL_OK"] = bool(ok)
(OUT / "checks_l0068.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
print(rep["leak_count"], rep["fill_guard"], rep.get("determinism_ALL_EQUAL"), rep["ALL_OK"])
