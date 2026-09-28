#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0082 — بناء وتخزين كل إشارات FVG للأصول الاثني عشر مع نتائج الهندسة المرجعية
(E1، 1×ATR، أفق 6) والتداخل لكل أصل. مخزّن للاستعمال في P2..P6.
"""
from __future__ import annotations

import json
import sys
import pathlib
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import l0082_common as C  # noqa: E402
import l0082_engine as E  # noqa: E402

CACHE = C.OUT / "_cache"
CACHE.mkdir(exist_ok=True)


def main():
    all_sig = []
    overlaps = {}
    coverage = {}
    e1_all = []
    for sym in C.ASSETS:
        sig, df, ind = E.build_signals(sym)
        e1 = E.resolve_e1(df, sig, stop_mult=C.REF_R_MULT, horizon=C.REF_HORIZON)
        ov, cov, cbars, nbars = E.asset_overlap(df, e1)
        overlaps[sym] = ov
        coverage[sym] = {"coverage": round(cov, 4), "covered_bars": cbars, "total_bars": nbars}
        merged = sig.copy()
        for col in ["outcome", "rr", "dur", "cov_start", "cov_end"]:
            merged["e1_" + col] = e1[col].values
        all_sig.append(merged)
        print(f"[SIG] {sym}: signals={len(sig)} overlap={ov:.3f} coverage={cov:.3f}", flush=True)
    S = pd.concat(all_sig, ignore_index=True)
    S["gap_mid"] = (S["gap_low"] + S["gap_high"]) / 2.0
    S.to_parquet(CACHE / "signals_ref.parquet")
    (CACHE / "overlaps_ref.json").write_text(json.dumps(overlaps, ensure_ascii=False, indent=2))
    (CACHE / "coverage_ref.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2))
    print(f"[SIG] total signals = {len(S)}")
    print("[SIG] overlaps:", {k: round(v, 3) for k, v in overlaps.items()})
    return S


if __name__ == "__main__":
    main()
