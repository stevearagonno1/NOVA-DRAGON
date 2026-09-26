# -*- coding: utf-8 -*-
"""يكمل L0058 من ملفات المرحلة الأولى بعد أن قتل نقص الذاكرة الحارس المجمع."""
from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path("/home/user/l0058")
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT))

import run_l0058_grid as G

OUT = G.OUT


def main() -> int:
    units = json.loads((OUT / "grid_units_c00115.json").read_text(encoding="utf-8"))
    fills = pd.read_csv(OUT / "trades_grid_repaired_c00115.csv").to_dict("records")
    broken = pd.read_csv(OUT / "trades_grid_broken_c00115.csv")
    guard = G._official_guard(OUT / "trades_grid_repaired_c00115.csv", G.COST)
    G.dump(OUT / "guard_repaired_c00115.json", guard)
    print(f"حارس المصلَح: {guard}", flush=True)
    if guard["viol"] != 0 or guard.get("skipped") or guard.get("missing_frames"):
        print("أوقف. لا تفسير.", flush=True)
        return 2
    if G._reconcile(units, fills, "static") > 0.05:
        print("أوقف. محاسبة الثابتة لا تطابق.", flush=True)
        return 2
    results = {}
    for engine in ("static", "dynamic", "static_broken", "dynamic_broken"):
        results[engine] = {}
        for window in ("اختيار", "حكم"):
            un = [u for u in units if u["engine"] == engine and u["window"] == window]
            if engine.endswith("broken"):
                lg = broken[(broken.engine == engine) & (broken.window == window)]
                leg = round(float(lg.pnl.sum()), 2) if len(lg) else 0.0
            else:
                lg = [f for f in fills if f["engine"] == engine and f["window"] == window]
                leg = round(sum(float(f["pnl"]) for f in lg), 2)
            st = G.summarize(un)
            st["leg_net"] = leg
            st["engine_net"] = st["net"]
            st["used_net"] = st["leg_net"] if engine.startswith("dynamic") else st["net"]
            results[engine][window] = st
            phase = "ج" if "broken" in engine else "ب"
            G.log(f"{engine} 0.115%", window, phase)
            print(f"  [{len(G.LEDGER)}/{G.CAP}] {engine} {window}: {st['used_net']} شبكات={st['grids']} محرك={st['engine_net']}", flush=True)
    sel_s = results["static"]["اختيار"]["used_net"]
    sel_d = results["dynamic"]["اختيار"]["used_net"]
    winner = "static" if sel_s >= sel_d else "dynamic"
    G.dump(OUT / "winner_deposited.json", {
        "winner": winner,
        "rule": "أعلى صافٍ في الاختيار عند 0.115% بعد حارس صفر. التعادل للثابتة.",
        "selection_static": sel_s,
        "selection_dynamic": sel_d,
        "written_before_judgement_read": True,
    })
    print(f"أُودع الأفضل من الاختيار: {winner} ثابتة={sel_s} ديناميكية={sel_d}", flush=True)
    for window in ("اختيار", "حكم"):
        print(f"  حكم مؤجَّل يُقرأ الآن {winner} ليس بعد — {window} ثابتة={results['static'][window]['used_net']} ديناميكية={results['dynamic'][window]['used_net']}", flush=True)
    syms = sorted({u["symbol"] for u in units})
    counts = {w: {} for w in ("اختيار", "حكم")}
    for u in units:
        if u["engine"] == winner:
            counts[u["window"]][u["symbol"]] = counts[u["window"]].get(u["symbol"], 0) + 1
    jobs = []
    for sym in syms:
        jobs.append((sym, winner, {w: counts[w].get(sym, 0) for w in counts}, G.COST))
    rnd_units, rnd_fills = [], []
    for rec in G.run_map(G.random_batch, jobs, 1):
        print(f"  عشوائي {rec['symbol']} وحدات={len(rec['units'])} أرجل={len(rec['fills'])}", flush=True)
        rnd_units.extend(rec["units"])
        rnd_fills.extend(rec["fills"])
    pd.DataFrame(rnd_fills).to_csv(OUT / "trades_grid_random_c00115.csv", index=False)
    rg = G._official_guard(OUT / "trades_grid_random_c00115.csv", G.COST)
    G.dump(OUT / "guard_random.json", rg)
    print(f"حارس العشوائي: {rg}", flush=True)
    if rg["viol"] != 0:
        print("أوقف عند العشوائي.", flush=True)
        return 2
    results["random"] = {}
    for window in ("اختيار", "حكم"):
        results["random"][window] = {}
        for seed in G.SEEDS:
            un = [u for u in rnd_units if u["window"] == window and u["engine"] == f"rnd{seed}"]
            lg = [f for f in rnd_fills if f["window"] == window and f["engine"] == f"rnd{seed}"]
            st = G.summarize(un)
            st["leg_net"] = round(sum(float(f["pnl"]) for f in lg), 2)
            st["used_net"] = st["leg_net"] if winner == "dynamic" else st["net"]
            results["random"][window][str(seed)] = st
            G.log(f"عشوائي {seed}", window, "ب")
            print(f"  [{len(G.LEDGER)}/{G.CAP}] عشوائي {seed} {window}: {st['used_net']} شبكات={st['grids']}", flush=True)
    jobs = [(sym, G.COST_130, (winner,)) for sym in syms]
    u130, f130 = [], []
    for rec in G.run_map(G.measure_job, jobs, 1):
        print(f"  0.130 {rec['symbol']} {rec['seconds']}s", flush=True)
        u130.extend(rec["units"])
        f130.extend(rec["fills"])
    pd.DataFrame(f130).to_csv(OUT / "trades_grid_winner_c00130.csv", index=False)
    g130 = G._official_guard(OUT / "trades_grid_winner_c00130.csv", G.COST_130)
    G.dump(OUT / "guard_c00130.json", g130)
    print(f"حارس 0.130: {g130}", flush=True)
    if g130["viol"] != 0:
        print("أوقف عند 0.130.", flush=True)
        return 2
    results["cost_130"] = {}
    for window in ("اختيار", "حكم"):
        un = [u for u in u130 if u["engine"] == winner and u["window"] == window]
        lg = [f for f in f130 if f["engine"] == winner and f["window"] == window]
        st = G.summarize(un)
        st["leg_net"] = round(sum(float(f["pnl"]) for f in lg), 2)
        st["used_net"] = st["leg_net"] if winner == "dynamic" else st["net"]
        results["cost_130"][window] = st
        G.log(f"{winner} 0.130%", window, "ب")
        print(f"  [{len(G.LEDGER)}/{G.CAP}] {winner} 0.130% {window}: {st['used_net']} شبكات={st['grids']}", flush=True)
    results["silence"] = G._silence()
    results["winner"] = winner
    results["ledger"] = G.LEDGER
    G.dump(OUT / "results.json", results)
    stop = OUT / "STOP.json"
    if stop.exists():
        stop.unlink()
    print(f"اكتمل. المستهلك {len(G.LEDGER)}/{G.CAP}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
