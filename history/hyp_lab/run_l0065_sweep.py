#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0065 — المسح المنظّم على فترة الاختيار فقط (1620 إعدادًا × 16 عملة)، ثم الاختيار بقاعدة مكتوبة سلفًا.

المخرجات في hyp_lab_out/L0065: sweep_SEL.csv (كل إعداد: السلة المستهدفة والكاملة)، selection.json (المختار،
أفضل إعداد لكل طريقة خروج، الجيران).
    python3 history/hyp_lab/run_l0065_sweep.py
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
import pullback_engine as PE  # noqa: E402

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0065"
OUT.mkdir(parents=True, exist_ok=True)
FRAMES = pathlib.Path.home() / ".cache" / "l0061_h4"
DAILY = pathlib.Path.home() / ".cache" / "l0061_1d"
FULL16 = ("ATOMUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "FILUSDT", "GRAMUSDT", "HNTUSDT", "IMXUSDT", "LINKUSDT",
          "PEPEUSDT", "RENDERUSDT", "SHIBUSDT", "SOLUSDT", "VETUSDT", "XLMUSDT")
MEMES = ("DOGEUSDT", "SHIBUSDT", "PEPEUSDT")
TARGET13 = tuple(s for s in FULL16 if s not in MEMES)
SEL_S, CUT = pd.Timestamp("2021-09-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC")
COST = 0.00115
BAR = pd.Timedelta(hours=4)
L64 = {"SEL": {"cycles": 92}, "JUD": {"cycles": 97}}
MIN_CYCLES_SEL = int(round(1.5 * L64["SEL"]["cycles"]))     # 138
MAX_DD_PCT = 25.0


def load_ctx(sym: str, end: pd.Timestamp) -> PE.CoinContext | None:
    h4 = pd.read_parquet(FRAMES / f"{sym}_4h.parquet")
    d1 = pd.read_parquet(DAILY / f"{sym}_1d.parquet")
    h4 = h4[h4.index < end]
    d1 = d1[d1.index < end]
    if len(h4) < 200 or len(d1) < 40:
        return None
    return PE.CoinContext(sym, h4, d1)


def basket_metrics(rows: list[dict], grid: pd.DatetimeIndex, closes: dict) -> dict:
    """صافي، دورات، ذروة، هبوط، أطول فترة تحت القمة — بسرعة (مصفوفات)."""
    if not rows:
        return {"net": 0.0, "cycles": 0, "slices": 0, "peak": 0.0, "ret_pct": None, "dd": 0.0, "dd_pct": None, "underwater_days": 0.0}
    s0 = grid[0]
    gi0 = np.array([int((pd.Timestamp(r["entry_time"]) - s0) / BAR) for r in rows])
    gi1 = np.array([int((pd.Timestamp(r["exit_time"]) - s0) / BAR) for r in rows])
    notional = np.array([r["notional_usd"] for r in rows])
    pnl = np.array([r["pnl_usd"] for r in rows])
    n = len(grid)
    dep = np.zeros(n + 1)
    np.add.at(dep, gi0, notional)
    np.add.at(dep, gi1, -notional)
    dep = np.cumsum(dep)[:n]
    peak = float(dep.max())
    eq = np.zeros(n)
    for k, r in enumerate(rows):
        a, b = int(gi0[k]), int(gi1[k])
        if b > a:
            cl = closes[r["symbol"]][a:b]
            g = cl / r["entry_px"]
            eq[a:b] += ((g * (1 - COST) - (1 + COST)) / (1 + COST)) * r["notional_usd"]
        eq[b:] += pnl[k]
    rm = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    dd = float((eq - rm).min())
    under = (eq - rm) < -1e-9
    longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    cycles = len({(r["symbol"], r["series"]) for r in rows})
    net = float(pnl.sum())
    return {"net": round(net, 2), "cycles": cycles, "slices": len(rows), "peak": round(peak, 2),
            "ret_pct": round(100 * net / peak, 3) if peak > 0 else None, "dd": round(dd, 2),
            "dd_pct": round(100 * dd / peak, 2) if peak > 0 else None, "underwater_days": round(longest * 4 / 24, 1),
            "avg_dep": round(float(dep.mean()), 2)}


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
    rows_out = []
    per_coin_net: dict[str, dict] = {}
    for ci, cfg in enumerate(cfgs):
        all_rows = []
        pc = {}
        for sym, ctx in ctxs.items():
            recs = PE.run_config(ctx, cfg)
            PE.price_pnl(recs, COST)
            all_rows.extend(recs)
            pc[sym] = round(sum(r["pnl_usd"] for r in recs), 2)
        t_rows = [r for r in all_rows if r["symbol"] not in MEMES]
        mt = basket_metrics(t_rows, grid, closes)
        mf = basket_metrics(all_rows, grid, closes)
        rows_out.append({"key": cfg.key, "depth": cfg.depth, "trend": cfg.trend, "split": cfg.split, "stages": cfg.stages,
                         "cancel": cfg.cancel, "exit": cfg.exit,
                         **{f"t13_{k}": v for k, v in mt.items()}, **{f"f16_{k}": v for k, v in mf.items()}})
        per_coin_net[cfg.key] = pc
        if (ci + 1) % 100 == 0:
            print(f"    {ci + 1}/{len(cfgs)} ({time.time() - t0:.0f}s)", flush=True)
    df = pd.DataFrame(rows_out)
    df.to_csv(OUT / "sweep_SEL.csv", index=False, encoding="utf-8-sig")
    (OUT / "sweep_SEL_per_coin.json").write_text(json.dumps(per_coin_net, ensure_ascii=False), encoding="utf-8")
    # ───── الاختيار بالقاعدة المكتوبة سلفًا ─────
    elig = df[(df.t13_net > 0) & (df.t13_cycles >= MIN_CYCLES_SEL) & (df.t13_dd_pct >= -MAX_DD_PCT)].copy()
    relaxed = False
    if elig.empty:
        relaxed = True
        elig = df[(df.t13_net > 0) & (df.t13_cycles >= L64["SEL"]["cycles"])].copy()
    elig = elig.sort_values(["t13_ret_pct", "t13_cycles"], ascending=[False, False])
    chosen = elig.iloc[0].to_dict() if not elig.empty else None
    finalists = {}
    for e in PE.EXITS:
        sub = elig[elig.exit == e]
        finalists[e] = sub.iloc[0].to_dict() if not sub.empty else None
    neighbors = []
    if chosen:
        d_i = PE.DEPTHS.index(chosen["depth"]); x_i = PE.CANCELS.index(chosen["cancel"]); tw = list(PE.WINDOWS_TREND)
        for dd_ in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for tw_ in tw:
                    if 0 <= d_i + dd_ < len(PE.DEPTHS) and 0 <= x_i + dx < len(PE.CANCELS):
                        k = PE.Config(PE.DEPTHS[d_i + dd_], tw_, chosen["split"], int(chosen["stages"]), PE.CANCELS[x_i + dx], chosen["exit"]).key
                        r = df[df.key == k]
                        if len(r):
                            neighbors.append({"key": k, "t13_net": float(r.t13_net.iloc[0]), "t13_ret_pct": float(r.t13_ret_pct.iloc[0]),
                                              "t13_cycles": int(r.t13_cycles.iloc[0]), "t13_dd_pct": float(r.t13_dd_pct.iloc[0])})
    summary = {
        "n_configs": int(len(df)), "n_coins": len(ctxs), "seconds": round(time.time() - t0, 1),
        "eligibility": {"min_cycles": MIN_CYCLES_SEL, "max_dd_pct": MAX_DD_PCT, "net_gt_0": True, "relaxed_used": relaxed, "n_eligible": int(len(elig))},
        "share_positive_t13": round(float((df.t13_net > 0).mean()), 4), "share_positive_f16": round(float((df.f16_net > 0).mean()), 4),
        "median_t13_net": round(float(df.t13_net.median()), 2), "best_t13_net_any": round(float(df.t13_net.max()), 2),
        "max_cycles_t13": int(df.t13_cycles.max()), "share_cycles_ge_138": round(float((df.t13_cycles >= MIN_CYCLES_SEL).mean()), 4),
        "share_dd_ok": round(float((df.t13_dd_pct >= -MAX_DD_PCT).mean()), 4),
        "chosen": chosen, "finalists_by_exit": finalists, "neighbors_of_chosen": neighbors,
        "top10_by_score": elig.head(10).to_dict("records"),
        "by_exit_median_net": {e: round(float(df[df.exit == e].t13_net.median()), 2) for e in PE.EXITS},
        "by_depth_median_net": {str(d): round(float(df[df.depth == d].t13_net.median()), 2) for d in PE.DEPTHS},
        "by_trend_median_net": {t: round(float(df[df.trend == t].t13_net.median()), 2) for t in PE.WINDOWS_TREND},
        "by_cancel_median_net": {str(x): round(float(df[df.cancel == x].t13_net.median()), 2) for x in PE.CANCELS},
        "by_stages_median_net": {str(k): round(float(df[df.stages == k].t13_net.median()), 2) for k in PE.STAGES},
        "by_split_median_net": {s: round(float(df[df.split == s].t13_net.median()), 2) for s in PE.SPLITS},
        "sha_sweep_csv": hashlib.sha256((OUT / "sweep_SEL.csv").read_bytes()).hexdigest()[:16],
    }
    (OUT / "selection.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("eligibility", "share_positive_t13", "median_t13_net", "best_t13_net_any", "max_cycles_t13",
                                               "share_cycles_ge_138", "share_dd_ok", "by_exit_median_net", "by_depth_median_net",
                                               "by_trend_median_net", "by_cancel_median_net", "by_stages_median_net")}, ensure_ascii=False, indent=1), flush=True)
    print("المختار:", json.dumps(chosen, ensure_ascii=False, default=str), flush=True)
    for e, f in finalists.items():
        print(f"  أفضل {e}:", None if f is None else {k: f[k] for k in ("key", "t13_net", "t13_cycles", "t13_ret_pct", "t13_dd_pct", "t13_underwater_days")}, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
