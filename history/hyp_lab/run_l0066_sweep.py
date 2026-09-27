#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0066 — المسح المنظّم على فترة الاختيار فقط (2592 إعدادًا × 16 عملة) ثم الاختيار بدرجة الهضبة المكتوبة سلفًا.
    python3 history/hyp_lab/run_l0066_sweep.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
import pullback_engine66 as PE  # noqa: E402
import run_l0065_sweep as S65  # noqa: E402  (basket_metrics, FULL16, MEMES, TARGET13)

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0066"
OUT.mkdir(parents=True, exist_ok=True)
FRAMES, DAILY = S65.FRAMES, S65.DAILY
FULL16, MEMES, TARGET13 = S65.FULL16, S65.MEMES, S65.TARGET13
SEL_S, CUT, COST = S65.SEL_S, S65.CUT, S65.COST
MIN_CYCLES_SEL = 138
MAX_DD_PCT, MAX_UW_DAYS = 35.0, 540


def load_ctx(sym: str, end: pd.Timestamp) -> PE.CoinContext | None:
    h4 = pd.read_parquet(FRAMES / f"{sym}_4h.parquet")
    d1 = pd.read_parquet(DAILY / f"{sym}_1d.parquet")
    h4 = h4[h4.index < end]
    d1 = d1[d1.index < end]
    if len(h4) < 200 or len(d1) < 40:
        return None
    return PE.CoinContext(sym, h4, d1)


def main() -> int:
    t0 = time.time()
    grid = pd.date_range(SEL_S, CUT, freq="4h", tz="UTC", inclusive="left")
    ctxs, closes = {}, {}
    for sym in FULL16:
        ctx = load_ctx(sym, CUT)
        if ctx is None:
            print(f"  {sym}: لا بيانات كافية في الاختيار", flush=True)
            continue
        ctxs[sym] = ctx
        closes[sym] = pd.Series(ctx.c, index=ctx.idx).reindex(grid).ffill().to_numpy(float)
    cfgs = PE.all_configs()
    print(f"══ مسح الاختيار: {len(cfgs)} إعدادًا × {len(ctxs)} عملة ══", flush=True)
    rows_out, per_coin_net = [], {}
    for ci, cfg in enumerate(cfgs):
        all_rows, pc = [], {}
        for sym, ctx in ctxs.items():
            recs = PE.run_config(ctx, cfg)
            PE.price_pnl(recs, COST)
            all_rows.extend(recs)
            pc[sym] = round(sum(r["pnl_usd"] for r in recs), 2)
        t_rows = [r for r in all_rows if r["symbol"] not in MEMES]
        mt = S65.basket_metrics(t_rows, grid, closes)
        mf = S65.basket_metrics(all_rows, grid, closes)
        avg_trade = mt["net"] / mt["slices"] if mt["slices"] else 0.0
        rows_out.append({"key": cfg.key, "ref": cfg.ref, "depth": cfg.depth, "trend": cfg.trend, "cancel": cfg.cancel, "stages": cfg.stages,
                         "template": cfg.template, "exit": cfg.exit, "t13_avg_trade": round(avg_trade, 3),
                         **{f"t13_{k}": v for k, v in mt.items()}, **{f"f16_{k}": v for k, v in mf.items()}})
        per_coin_net[cfg.key] = pc
        if (ci + 1) % 250 == 0:
            print(f"    {ci + 1}/{len(cfgs)} ({time.time() - t0:.0f}s)", flush=True)
    df = pd.DataFrame(rows_out)
    (OUT / "sweep_SEL_per_coin.json").write_text(json.dumps(per_coin_net, ensure_ascii=False), encoding="utf-8")

    by_key = df.set_index("key")
    ret = by_key["t13_ret_pct"].fillna(-999.0)
    plateau, n_neigh, neigh_min = {}, {}, {}
    for cfg in cfgs:
        di, xi = PE.DEPTHS.index(cfg.depth), PE.CANCELS.index(cfg.cancel)
        ks = [cfg.key]
        for dd_ in (-1, 1):
            if 0 <= di + dd_ < len(PE.DEPTHS):
                ks.append(PE.Config(cfg.ref, PE.DEPTHS[di + dd_], cfg.trend, cfg.cancel, cfg.stages, cfg.template, cfg.exit).key)
        for dx in (-1, 1):
            if 0 <= xi + dx < len(PE.CANCELS):
                ks.append(PE.Config(cfg.ref, cfg.depth, cfg.trend, PE.CANCELS[xi + dx], cfg.stages, cfg.template, cfg.exit).key)
        vals = [float(ret[k_]) for k_ in ks]
        plateau[cfg.key] = float(np.mean(vals)); n_neigh[cfg.key] = len(ks); neigh_min[cfg.key] = float(min(vals))
    df["plateau_score"] = df.key.map(plateau); df["n_neighbors"] = df.key.map(n_neigh); df["neighbors_min_ret"] = df.key.map(neigh_min)
    df.to_csv(OUT / "sweep_SEL.csv", index=False, encoding="utf-8-sig")
    elig = df[(df.t13_net > 0) & (df.t13_cycles >= MIN_CYCLES_SEL) & (df.t13_dd_pct >= -MAX_DD_PCT) & (df.t13_underwater_days <= MAX_UW_DAYS) & (df.t13_avg_trade > 0)].copy()
    elig = elig.sort_values(["plateau_score", "t13_cycles"], ascending=[False, False])
    chosen = elig.iloc[0].to_dict() if not elig.empty else None
    peak_best = df[(df.t13_net > 0)].sort_values("t13_ret_pct", ascending=False).iloc[0].to_dict() if (df.t13_net > 0).any() else None
    finalists = {e: (elig[elig.exit == e].iloc[0].to_dict() if not elig[elig.exit == e].empty else None) for e in PE.EXITS}
    neighbors, sens = [], {}
    if chosen:
        for dd_ in (-1, 0, 1):
            for dx in (-1, 0, 1):
                di, xi = PE.DEPTHS.index(chosen["depth"]), PE.CANCELS.index(chosen["cancel"])
                if 0 <= di + dd_ < len(PE.DEPTHS) and 0 <= xi + dx < len(PE.CANCELS):
                    k_ = PE.Config(chosen["ref"], PE.DEPTHS[di + dd_], chosen["trend"], PE.CANCELS[xi + dx], int(chosen["stages"]), chosen["template"], chosen["exit"]).key
                    r = by_key.loc[k_]
                    neighbors.append({"key": k_, "t13_net": float(r.t13_net), "t13_ret_pct": float(r.t13_ret_pct), "t13_cycles": int(r.t13_cycles), "t13_dd_pct": float(r.t13_dd_pct)})
        for axis, vals in (("depth", PE.DEPTHS), ("cancel", PE.CANCELS), ("template", list(PE.TEMPLATES[int(chosen["stages"])])), ("ref", list(PE.REF_WINDOWS)), ("trend", list(PE.TRENDS)), ("stages", (2, 3, 4)), ("exit", PE.EXITS)):
            sens[axis] = {}
            for v in vals:
                kw = dict(ref=chosen["ref"], depth=chosen["depth"], trend=chosen["trend"], cancel=chosen["cancel"], stages=int(chosen["stages"]), template=chosen["template"], exit=chosen["exit"])
                if axis == "stages":
                    kw["stages"] = int(v); kw["template"] = list(PE.TEMPLATES[int(v)])[0] if chosen["template"] not in PE.TEMPLATES[int(v)] else chosen["template"]
                else:
                    kw[axis] = v
                k_ = PE.Config(**kw).key
                r = by_key.loc[k_]
                sens[axis][str(v)] = {"net": float(r.t13_net), "ret_pct": float(r.t13_ret_pct), "cycles": int(r.t13_cycles), "dd_pct": float(r.t13_dd_pct), "template_used": kw["template"]}
    summary = {
        "n_configs": int(len(df)), "n_coins": len(ctxs), "seconds": round(time.time() - t0, 1),
        "eligibility": {"min_cycles": MIN_CYCLES_SEL, "max_dd_pct": MAX_DD_PCT, "max_underwater_days": MAX_UW_DAYS, "net_gt_0": True, "avg_trade_gt_0": True, "n_eligible": int(len(elig))},
        "share_positive_t13": round(float((df.t13_net > 0).mean()), 4), "median_t13_net": round(float(df.t13_net.median()), 2), "median_t13_ret": round(float(df.t13_ret_pct.median()), 3),
        "best_t13_net_any": round(float(df.t13_net.max()), 2), "share_cycles_ge_138": round(float((df.t13_cycles >= MIN_CYCLES_SEL).mean()), 4),
        "share_dd_ok": round(float((df.t13_dd_pct >= -MAX_DD_PCT).mean()), 4), "share_uw_ok": round(float((df.t13_underwater_days <= MAX_UW_DAYS).mean()), 4),
        "chosen_by_plateau": chosen, "single_peak_best": peak_best, "finalists_by_exit": finalists, "neighbors_of_chosen": neighbors, "sensitivity_around_chosen": sens,
        "top10_by_plateau": elig.head(10).to_dict("records"),
        "by_exit_median_net": {e: round(float(df[df.exit == e].t13_net.median()), 2) for e in PE.EXITS},
        "by_depth_median_net": {str(d): round(float(df[df.depth == d].t13_net.median()), 2) for d in PE.DEPTHS},
        "by_ref_median_net": {r: round(float(df[df.ref == r].t13_net.median()), 2) for r in PE.REF_WINDOWS},
        "by_trend_median_net": {t: round(float(df[df.trend == t].t13_net.median()), 2) for t in PE.TRENDS},
        "by_cancel_median_net": {str(x): round(float(df[df.cancel == x].t13_net.median()), 2) for x in PE.CANCELS},
        "by_stages_median_net": {str(k): round(float(df[df.stages == k].t13_net.median()), 2) for k in (2, 3, 4)},
        "by_template_median_net": {t: round(float(df[df.template == t].t13_net.median()), 2) for k in PE.TEMPLATES for t in PE.TEMPLATES[k]},
        "by_depth_median_cycles": {str(d): int(df[df.depth == d].t13_cycles.median()) for d in PE.DEPTHS},
        "sha_sweep_csv": hashlib.sha256((OUT / "sweep_SEL.csv").read_bytes()).hexdigest()[:16],
    }
    (OUT / "selection.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("eligibility", "share_positive_t13", "median_t13_net", "best_t13_net_any", "share_cycles_ge_138", "share_dd_ok", "share_uw_ok",
                                               "by_exit_median_net", "by_depth_median_net", "by_ref_median_net", "by_trend_median_net", "by_cancel_median_net", "by_stages_median_net", "by_depth_median_cycles")}, ensure_ascii=False, indent=1), flush=True)
    print("المختار (هضبة):", None if chosen is None else {k: chosen[k] for k in ("key", "t13_net", "t13_cycles", "t13_ret_pct", "t13_dd_pct", "t13_underwater_days", "plateau_score", "neighbors_min_ret", "t13_avg_trade")}, flush=True)
    print("القمة المنفردة:", None if peak_best is None else {k: peak_best[k] for k in ("key", "t13_net", "t13_cycles", "t13_ret_pct", "plateau_score")}, flush=True)
    for e, f in finalists.items():
        print(f"  أفضل {e}:", None if f is None else {k: f[k] for k in ("key", "t13_net", "t13_cycles", "t13_ret_pct", "t13_dd_pct", "plateau_score")}, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
