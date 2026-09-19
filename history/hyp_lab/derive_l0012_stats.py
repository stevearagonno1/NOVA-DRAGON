# -*- coding: utf-8 -*-
"""L0012 — اشتقاق أرقام تقرير القسم 23 من أوراق التداول المودعة (بلا أي إعادة تشغيل).

المصدر الوحيد: history/research/hyp_lab_out/L0012/F_213/<sym>/trades.csv (تداولات
التركيبة المنتقاة على نافذة الاختبار) + all_symbols_test.csv (للتحقق المتقاطع).
المخرجات: derived_stats_test.csv بجوار النتائج — كل رقم فيه قابل لإعادة الاشتقاق
بهذا الأمر نفسه (القسم 10: لا رقم بلا مصدر).
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "research" / "hyp_lab_out" / "L0012"


def longest_losing_streak(pnl: pd.Series) -> int:
    best = cur = 0
    for x in pnl:
        cur = cur + 1 if x < 0 else 0
        best = max(best, cur)
    return best


def max_drawdown(pnl: pd.Series) -> float:
    eq = pnl.cumsum()
    peak = eq.cummax()
    return float((peak - eq).max())


def per_symbol(sym: str) -> dict:
    t = pd.read_csv(OUT / "F_213" / sym / "trades.csv", encoding="utf-8-sig")
    t["exit_time"] = pd.to_datetime(t["exit_time"], utc=True)
    pnl = t["pnl"].astype(float)
    g = pnl[pnl > 0].sum()
    lo = -pnl[pnl < 0].sum()
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    day = t.groupby(t["exit_time"].dt.date)["pnl"].sum()
    eq = pnl.cumsum()
    # أطول مدة هبوط: من قمة إلى استرجاعها — بالتداولات وبالأيام
    peak = eq.cummax()
    under = (eq < peak).to_numpy()
    runs, cur = [], 0
    for u in under:
        cur = cur + 1 if u else 0
        runs.append(cur)
    longest_under_trades = max(runs) if runs else 0
    longest_days = 0.0
    start = None
    for i, u in enumerate(under):
        if u and start is None:
            start = t["exit_time"].iloc[i]
        if not u and start is not None:
            longest_days = max(longest_days, (t["exit_time"].iloc[i] - start).total_seconds() / 86400)
            start = None
    if start is not None:
        longest_days = max(longest_days,
                           (t["exit_time"].iloc[-1] - start).total_seconds() / 86400)
    return {
        "symbol": sym,
        "trades": int(len(t)),
        "net": round(float(pnl.sum()), 4),
        "win_pct": round(100 * len(wins) / len(t), 2),
        "pf": round(float(g / lo), 4) if lo > 0 else float("inf"),
        "avg_win": round(float(wins.mean()), 4),
        "avg_loss": round(float(losses.mean()), 4),
        "muscle": round(float(wins.mean() / -losses.mean()), 4),
        "longest_loss_streak": longest_losing_streak(pnl),
        "avg_bars_held": round(float(t["bars_held"].mean()), 3),
        "avg_hours_held": round(float(t["bars_held"].mean()) * 4, 2),
        "max_dd": round(max_drawdown(pnl), 4),
        "longest_dd_trades": int(longest_under_trades),
        "longest_dd_days": round(float(longest_days), 1),
        "worst_day": round(float(day.min()), 4),
        "best_day": round(float(day.max()), 4),
    }


def main() -> int:
    syms = sorted(p.name for p in (OUT / "F_213").iterdir() if p.is_dir())
    rows = [per_symbol(s) for s in syms]
    df = pd.DataFrame(rows)
    # صف السلة: كل التداولات مدموجة زمنياً (زمن الخروج) — عرض محفظة بسيط بلا ترجيح
    all_t = pd.concat([
        pd.read_csv(OUT / "F_213" / s / "trades.csv", encoding="utf-8-sig") for s in syms
    ])
    all_t["exit_time"] = pd.to_datetime(all_t["exit_time"], utc=True)
    all_t = all_t.sort_values("exit_time").reset_index(drop=True)
    pnl = all_t["pnl"].astype(float)
    g = pnl[pnl > 0].sum()
    lo = -pnl[pnl < 0].sum()
    day = all_t.groupby(all_t["exit_time"].dt.date)["pnl"].sum()
    eq = pnl.cumsum()
    peak = eq.cummax()
    under = (eq < peak).to_numpy()
    runs, cur = [], 0
    for u in under:
        cur = cur + 1 if u else 0
        runs.append(cur)
    longest_under_trades = max(runs) if runs else 0
    longest_days, start = 0.0, None
    for i, u in enumerate(under):
        if u and start is None:
            start = all_t["exit_time"].iloc[i]
        if not u and start is not None:
            longest_days = max(longest_days, (all_t["exit_time"].iloc[i] - start).total_seconds()/86400)
            start = None
    if start is not None:
        longest_days = max(longest_days, (all_t["exit_time"].iloc[-1] - start).total_seconds()/86400)
    basket = {
        "symbol": "BASKET8",
        "trades": int(len(all_t)),
        "net": round(float(pnl.sum()), 4),
        "win_pct": round(100 * len(pnl[pnl > 0]) / len(all_t), 2),
        "pf": round(float(g / lo), 4),
        "avg_win": round(float(pnl[pnl > 0].mean()), 4),
        "avg_loss": round(float(pnl[pnl < 0].mean()), 4),
        "muscle": round(float(pnl[pnl > 0].mean() / -pnl[pnl < 0].mean()), 4),
        "longest_loss_streak": longest_losing_streak(pnl),
        "avg_bars_held": round(float(all_t["bars_held"].mean()), 3),
        "avg_hours_held": round(float(all_t["bars_held"].mean()) * 4, 2),
        "max_dd": round(max_drawdown(pnl), 4),
        "longest_dd_trades": int(longest_under_trades),
        "longest_dd_days": round(float(longest_days), 1),
        "worst_day": round(float(day.min()), 4),
        "best_day": round(float(day.max()), 4),
    }
    rows.append(basket)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "derived_stats_test.csv", index=False, encoding="utf-8-sig")
    print(out.to_string(index=False), flush=True)

    # تحقق متقاطع مع all_symbols_test.csv
    a = pd.read_csv(OUT / "F_213" / "all_symbols_test.csv", encoding="utf-8-sig")
    chk = a[["symbol", "test_net", "test_trades", "test_pf"]].merge(
        out[["symbol", "net", "trades", "pf"]], on="symbol", how="left")
    chk["d_net"] = (chk["test_net"] - chk["net"]).abs()
    chk["d_trades"] = (chk["test_trades"] - chk["trades"]).abs()
    print("\nتحقق متقاطع (all_symbols_test مقابل مشتق من trades.csv):", flush=True)
    print(chk.to_string(index=False), flush=True)
    print(f"\nأقصى فرق net = {chk['d_net'].max():.2e} | أقصى فرق صفقات = {int(chk['d_trades'].max())}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
