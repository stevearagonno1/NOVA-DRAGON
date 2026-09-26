# -*- coding: utf-8 -*-
"""يعيد تصدير التعبئات المصلَحة بعد إصلاح شراء-وتسطيح الشمعة نفسها."""
from __future__ import annotations

import json
import sys
import pathlib

import pandas as pd

sys.path.insert(0, "/home/user/l0058/history/hyp_lab")
import run_l0058_grid as G

def main() -> int:
    old = json.loads((G.OUT / "grid_units_c00115.json").read_text(encoding="utf-8"))
    broken = [u for u in old if "broken" in u["engine"]]
    syms = sorted(p.name.split("_")[0] for p in (G.ROOT / "crypto_archive").glob("*USDT_1m.parquet"))
    units, fills = [], []
    for sym in syms:
        rec = G.measure_symbol(sym, engines=("static", "dynamic"))
        print(f"  {sym} {rec['seconds']}s وحدات={len(rec['units'])} أرجل={len(rec['fills'])}", flush=True)
        units.extend(rec["units"])
        fills.extend(rec["fills"])
    gap = G._reconcile(units, fills, "static")
    print(f"فرق الثابتة {gap}", flush=True)
    if gap > 0.05:
        raise SystemExit("الثابتة ما زالت لا تطابق")
    # compare engine nets to the first run
    def key(u):
        return (u["engine"], u["window"], u["symbol"], u["start"])
    old_map = {key(u): u["net"] for u in old if u["engine"] in ("static", "dynamic")}
    diffs = []
    for u in units:
        prev = old_map.get(key(u))
        if prev is None or abs(prev - u["net"]) > 0.01:
            diffs.append((u["symbol"], u["engine"], u["window"], u["start"], prev, round(u["net"], 4)))
    print(f"فروق عن التشغيل الأول: {len(diffs)}", flush=True)
    for row in diffs[:12]:
        print(" ", row, flush=True)
    pd.DataFrame(fills).to_csv(G.OUT / "trades_grid_repaired_c00115.csv", index=False)
    merged = broken + units
    (G.OUT / "grid_units_c00115.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print("حُفظ", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
