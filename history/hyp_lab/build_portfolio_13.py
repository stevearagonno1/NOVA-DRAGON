# -*- coding: utf-8 -*-
"""محفظة الأربع ساعات الموحدة — 13 عملة (اتحاد سلة L0010 الستة + سلة L0013 السبعة).

الطريقة: تحميل سلاسل الصفقات المودعة في الفرع المحمي وبناء منحنى المال للمحفظة
(وزن متساوٍ: 1000$ اسمي لكل صفقة، كما في كل الجولات)، ثم قياس:
  الصافي · الصفقات · عامل الربح · أقصى هبوط ومدته · أسوأ يوم · زمن الاحتفاظ · PSR/DSR
  · نصوص الأرباع · ترابط العوائد اليومية بين العملات (تشابه/توزيع المخاطر).
السيناريوهات الثلاثة: الأساس 0.13%/طرف · المجهد 0.30%/طرف · الفترة العمياء 2021-09→2023-08.
صفر إعادة تشغيل وصفر اختيار: كل ملف هو ناتج جولة مدققة ومودعة.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(pathlib.Path("/home/user/.work/root/history/hyp_lab")))
from measure_l0010_gate import drawdown_stats, longest_losing_streak, psr_dsr  # noqa: E402

OUT = pathlib.Path("/home/user/.work/pf/out")
OUT.mkdir(exist_ok=True)
TEST_YEARS = (pd.Timestamp("2026-08-31", tz="UTC") - pd.Timestamp("2025-01-01", tz="UTC")).days / 365.25
BLIND_YEARS = (pd.Timestamp("2023-08-31", tz="UTC") - pd.Timestamp("2021-09-01", tz="UTC")).days / 365.25


def load(folder: pathlib.Path) -> pd.DataFrame:
    frames = []
    for p in sorted(folder.glob("*.csv")):
        d = pd.read_csv(p, encoding="utf-8-sig")
        d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def portfolio(t: pd.DataFrame, name: str, years: float, n_trials: int) -> dict:
    t = t.sort_values("exit_time").reset_index(drop=True)
    pnl = t["pnl"].to_numpy(dtype=float)
    g, lo = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    dd, dd_days, dd_run = drawdown_stats(t["exit_time"], pnl)
    day = t.groupby(t["exit_time"].dt.date)["pnl"].sum()
    row = {
        "portfolio": name, "coins": int(t["symbol"].nunique()), "trades": int(len(t)),
        "net": round(float(pnl.sum()), 2),
        "win_pct": round(100 * float((pnl > 0).mean()), 2),
        "pf": round(float(g / lo), 4) if lo > 0 else float("inf"),
        "net_per_trade": round(float(pnl.sum() / len(t)), 2),
        "max_dd": round(dd, 2), "longest_dd_days": round(dd_days, 1),
        "worst_day": round(float(day.min()), 2),
        "avg_hours_held": round(float(t["bars_held"].mean()) * 4, 2),
        "longest_loss_streak": longest_losing_streak(pnl),
        "usd_cost_drag": round(2 * 0.0013 * 1000 * len(t), 2),
    }
    row.update(psr_dsr(pnl, years, n_trials))
    return row


def quarters(t: pd.DataFrame) -> pd.DataFrame:
    q = t.assign(q=t["exit_time"].dt.tz_localize(None).dt.to_period("Q")).groupby("q")["pnl"].agg(["sum", "count"])
    q.columns = ["net", "trades"]
    return q.round(2)


def daily_corr(t: pd.DataFrame) -> pd.DataFrame:
    d = t.assign(day=t["exit_time"].dt.date).groupby(["day", "symbol"])["pnl"].sum().unstack(fill_value=0.0)
    return d.corr().round(3)


def main() -> int:
    base10, base13 = load(HERE / "base10"), load(HERE / "base13")
    slip10, slip13 = load(HERE / "slip10"), load(HERE / "slip13")
    blind = load(HERE / "blind")

    base, slip = pd.concat([base10, base13], ignore_index=True), pd.concat([slip10, slip13], ignore_index=True)
    rows = [
        portfolio(base, "BASE_13", TEST_YEARS, 32 * 13),
        portfolio(base10, "BASE_6_old", TEST_YEARS, 192),
        portfolio(base13, "BASE_7_new", TEST_YEARS, 224),
        portfolio(slip, "STRESS_0.30%_13", TEST_YEARS, 32 * 13),
        portfolio(slip10, "STRESS_0.30%_6", TEST_YEARS, 192),
        portfolio(slip13, "STRESS_0.30%_7", TEST_YEARS, 224),
        portfolio(blind, "BLIND_2021-2023_10", BLIND_YEARS, 32 * 10),
    ]
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "portfolio_4h_13.csv", index=False, encoding="utf-8-sig")
    quarters(base).to_csv(OUT / "quarters_4h_13.csv", encoding="utf-8-sig")
    quarters(slip).to_csv(OUT / "quarters_4h_13_stress030.csv", encoding="utf-8-sig")
    corr = daily_corr(base)
    corr.to_csv(OUT / "corr_daily_4h_13.csv", encoding="utf-8-sig")
    off = corr.where(~np.eye(len(corr), dtype=bool)).copy()
    off.index.name = "a"; off.columns.name = "b"
    par = off.stack().reset_index(name="corr")
    par = par[par["a"] < par["b"]]
    par.to_csv(OUT / "corr_pairs_4h_13.csv", index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 250)
    print(df[["portfolio", "coins", "trades", "net", "pf", "net_per_trade", "max_dd", "longest_dd_days",
              "worst_day", "avg_hours_held", "longest_loss_streak", "usd_cost_drag", "dsr", "dsr_z"]].to_string(index=False), flush=True)
    print(f"\nترابط العوائد اليومية: متوسط {par['corr'].mean():.3f} · أعلى {par['corr'].max():.3f} · أدنى {par['corr'].min():.3f} · عدد الأزواج {len(par)}", flush=True)
    print("\n=== الأرباع (الأساس) ===", flush=True)
    print(quarters(base).to_string(), flush=True)
    print("\n=== الأرباع (عند 0.30%) ===", flush=True)
    print(quarters(slip).to_string(), flush=True)
    print("\n=== أعلى 8 أزواج ترابطًا ===", flush=True)
    print(par.sort_values("corr", ascending=False).head(8).to_string(index=False), flush=True)
    print("\n=== أدنى 5 أزواج ===", flush=True)
    print(par.sort_values("corr").head(5).to_string(index=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
