# -*- coding: utf-8 -*-
"""L0013 — اشتقاق تقرير القسم 23 من أوراق الضغط المودعة (بلا إعادة تشغيل).

المصادر: history/research/hyp_lab_out/L0013/4h/F_213/<sym>/{slip_tiers,blind_selected,
blind_trades,plateau,ablate,test_matrix}.csv + ملفات تداول الأساس من إيداع L0012
(نفس الخلية المقفلة، تحقق متقاطع مثبت) + buyhold من L0012.
يستعمل دوال القياس نفسها من measure_l0010_gate (PSR/DSR/الهبوط) — بلا نسخ ثانٍ.
المخرجات: <L0013>/metrics_test_4h.csv · blind_metrics_4h.csv · stress_summary_4h.csv
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
HIST = HERE.parent
sys.path.insert(0, str(HERE))
import run_stress as RS  # noqa: E402
from measure_l0010_gate import drawdown_stats, longest_losing_streak, psr_dsr  # noqa: E402

OUT = HIST / "research" / "hyp_lab_out" / "L0013" / "4h" / "F_213"
SRC12 = HIST / "research" / "hyp_lab_out" / "L0012"
SYMS = ["ATOMUSDT", "DOGEUSDT", "IMXUSDT", "PEPEUSDT", "SHIBUSDT", "TONUSDT", "VETUSDT"]
TEST_YEARS = (pd.Timestamp("2026-08-31", tz="UTC") - pd.Timestamp("2025-01-01", tz="UTC")).days / 365.25
BLIND_YEARS = (pd.Timestamp("2023-08-31", tz="UTC") - pd.Timestamp("2021-09-01", tz="UTC")).days / 365.25


def metrics_from_trades(t: pd.DataFrame, name: str, years: float, n_trials: int) -> dict:
    t = t.copy()
    t["exit_time"] = pd.to_datetime(t["exit_time"], utc=True)
    t = t.sort_values("exit_time").reset_index(drop=True)
    pnl = t["pnl"].to_numpy(dtype=float)
    g, lo = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    dd, dd_days, dd_run = drawdown_stats(t["exit_time"], pnl)
    day = t.groupby(t["exit_time"].dt.date)["pnl"].sum()
    half = len(t) // 2
    row = {
        "symbol": name, "trades": int(len(t)), "net": round(float(pnl.sum()), 4),
        "win_pct": round(100 * float((pnl > 0).mean()), 2),
        "pf": round(float(g / lo), 4) if lo > 0 else float("inf"),
        "avg_win": round(float(pnl[pnl > 0].mean()), 4),
        "avg_loss": round(float(pnl[pnl < 0].mean()), 4),
        "longest_loss_streak": longest_losing_streak(pnl),
        "avg_hours_held": round(float(t["bars_held"].mean()) * 4, 2),
        "max_dd": round(dd, 4), "longest_dd_days": round(dd_days, 1),
        "longest_dd_trades": int(dd_run), "worst_day": round(float(day.min()), 4),
        "first_half_net": round(float(pnl[:half].sum()), 2),
        "second_half_net": round(float(pnl[half:].sum()), 2),
        "first_exit": str(t["exit_time"].iloc[0]), "last_exit": str(t["exit_time"].iloc[-1]),
    }
    row.update(psr_dsr(pnl, years, n_trials))
    return row


def main() -> int:
    # ---- 1) الأساس: ملفات تداول L0012 (نفس الخلية المقفلة على نفس النافذة) ----
    base_rows, frames = [], []
    for sym in SYMS:
        p = SRC12 / "F_213" / sym / "trades.csv"
        t = pd.read_csv(p, encoding="utf-8-sig")
        base_rows.append(metrics_from_trades(t, sym, TEST_YEARS, 32))
        frames.append(t.assign(exit_time=pd.to_datetime(t["exit_time"], utc=True)))
    basket = pd.concat(frames).sort_values("exit_time").reset_index(drop=True)
    base_rows.append(metrics_from_trades(basket, "BASKET7", TEST_YEARS, 224))
    pd.DataFrame(base_rows).to_csv(OUT.parent / "metrics_test_4h.csv", index=False, encoding="utf-8-sig")

    # ---- 2) الانزلاق المجهد + الجوار: إعادة قراءة أوراق السائق ----
    slip_rows, neigh_rows = [], []
    for sym in SYMS:
        s = pd.read_csv(OUT / sym / "slip_tiers.csv", encoding="utf-8-sig")
        for _, r in s.iterrows():
            slip_rows.append({"symbol": sym, "slip_per_side": r["slip_per_side"],
                              "cost_per_side": r["cost_per_side"], "net": round(r["net"], 2),
                              "trades": int(r["trades"]), "pf": round(r["pf"], 3)})
        pl = pd.read_csv(OUT / sym / "plateau.csv", encoding="utf-8-sig")
        pos = int((pl["net"] > 0).sum())
        ratio_min = float(pl["ratio_vs_base"].min())
        neigh_rows.append({"symbol": sym, "neighbors": int(len(pl)), "positive": pos,
                           "min_ratio_vs_base": round(ratio_min, 4),
                           "base_net": round(float(pl[pl["is_base"]]["net"].iloc[0]), 2)})
    slip = pd.DataFrame(slip_rows)
    slip.to_csv(OUT.parent / "slip_matrix_4h.csv", index=False, encoding="utf-8-sig")
    neigh = pd.DataFrame(neigh_rows)
    neigh.to_csv(OUT.parent / "plateau_4h.csv", index=False, encoding="utf-8-sig")

    # ---- 3) العمياء: مقاسات من صفقات العمياء المودعة ----
    blind_rows = []
    for sym in SYMS:
        bt = OUT / sym / "blind_trades.csv"
        sel = pd.read_csv(OUT / sym / "blind_selected.csv", encoding="utf-8-sig")
        if not bt.exists() or len(pd.read_csv(bt, encoding="utf-8-sig")) == 0:
            blind_rows.append({"symbol": sym, "status": str(sel.iloc[0].get("status", "غير مقاسة")),
                               "trades": 0, "net": None, "max_dd": None,
                               "avg_hours_held": None, "longest_loss_streak": None,
                               "worst_day": None, "psr_vs_zero": None, "dsr": None, "dsr_z": None})
            continue
        t = pd.read_csv(bt, encoding="utf-8-sig")
        row = metrics_from_trades(t, sym, BLIND_YEARS, 32)
        row["status"] = "مقاسة"
        blind_rows.append(row)
    bl = pd.DataFrame(blind_rows)
    measured = [r for r in blind_rows if r.get("status") == "مقاسة"]
    if measured:
        bframes = [pd.read_csv(OUT / r["symbol"] / "blind_trades.csv", encoding="utf-8-sig") for r in measured]
        bb = pd.concat(bframes)
        bb["exit_time"] = pd.to_datetime(bb["exit_time"], utc=True)
        bb = bb.sort_values("exit_time").reset_index(drop=True)
        bb_row = metrics_from_trades(bb, "BASKET_BLIND", BLIND_YEARS, 32 * len(measured))
        bb_row["status"] = "مقاسة"
        bl = pd.concat([bl, pd.DataFrame([bb_row])], ignore_index=True)
    bl.to_csv(OUT.parent / "blind_metrics_4h.csv", index=False, encoding="utf-8-sig")

    # ---- 4) ملخص الضغط المجمّع ----
    summary = []
    for sym in SYMS:
        s = slip[slip.symbol == sym]
        tiers = {float(r["slip_per_side"]): round(r["net"], 2) for _, r in s.iterrows()}
        summary.append({
            "symbol": sym,
            "base_net": tiers.get(0.0003), "slip_10_net": tiers.get(0.0010),
            "slip_30_net": tiers.get(0.0030),
            "survives_30": bool((tiers.get(0.0030) or 0) > 0),
            "plateau_positive": f"{int(neigh[neigh.symbol == sym]['positive'].iloc[0])}/{int(neigh[neigh.symbol == sym]['neighbors'].iloc[0])}",
            "blind_net": next((r["net"] for r in blind_rows if r["symbol"] == sym and r.get("status") == "مقاسة"), None),
        })
    su = pd.DataFrame(summary)
    su["slip_30_net_sum"] = None
    su.to_csv(OUT.parent / "stress_summary_4h.csv", index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 250)
    print("=== الأساس (نافذة الامتحان) ===", flush=True)
    print(pd.DataFrame(base_rows)[["symbol", "trades", "net", "pf", "max_dd", "avg_hours_held",
                                   "worst_day", "longest_loss_streak", "psr_vs_zero", "dsr", "dsr_z"]].to_string(index=False), flush=True)
    print("\n=== الانزلاق المجهد ===", flush=True)
    print(su.to_string(index=False), flush=True)
    tot30 = su["slip_30_net"].sum()
    tot10 = su["slip_10_net"].sum()
    print(f"\nمجموع السلة: أساس {su['base_net'].sum():.2f}$ · 0.10% {tot10:.2f}$ · 0.30% {tot30:.2f}$", flush=True)
    print(f"نجاة 0.30%: {int(su['survives_30'].sum())} من {len(su)} رموز", flush=True)
    print("\n=== العمياء ===", flush=True)
    print(bl[["symbol", "status", "trades", "net", "pf", "max_dd", "avg_hours_held", "worst_day", "dsr_z"]].to_string(index=False), flush=True)
    print("\n=== الجوار ===", flush=True)
    print(neigh.to_string(index=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
