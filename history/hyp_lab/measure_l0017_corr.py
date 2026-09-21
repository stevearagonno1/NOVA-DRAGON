# -*- coding: utf-8 -*-
"""L0017 — قياس الترابط اليومي لعابري الدفعة مع سلسلة محفظة الـ13 المودعة.

نص العقد: «عند أي عبور: قياس الترابط اليومي مع سلسلة محفظة الـ13 المودعة
(رقم واحد يسطر في التسليم) — سائق مختلف الارتباط يُقاس لا يُفترض.»

الطريقة (نفس daily_corr في build_portfolio_13.py حرفاً):
  عوائد يومية = مجموع pnl الصفقات المغلقة في اليوم · الترابط = بيرسون على الأيام المشتركة.
  سلسلة المحفظة المرجعية = اتحاد slip/base trades المودعة لجولتي L0010 (الستة) و L0013 (السبعة)
  على فريم 4h — وهي السلسلة التي بُنيت عليها محفظة الـ13 في L0014.
  المقارنة على نافذة الاختبار المشتركة 2025-01-01→2026-08-31.

لا إعادة تشغيل ولا اختيار: تُقرأ الملفات المودعة كما هي.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

HIST = pathlib.Path(__file__).resolve().parents[1]
OUTDIR = HIST / "research" / "hyp_lab_out"
TEST_START = pd.Timestamp("2025-01-01", tz="UTC")
TEST_END = pd.Timestamp("2026-08-31", tz="UTC")


def daily(series_df: pd.DataFrame) -> pd.Series:
    d = series_df.copy()
    d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
    d = d[(d["exit_time"] >= TEST_START) & (d["exit_time"] <= TEST_END)]
    return d.groupby(d["exit_time"].dt.date)["pnl"].sum()


def load_portfolio_13() -> pd.Series:
    """سلسلة المحفظة المرجعية من الملفات المودعة (L0010 الستة + L0013 السبعة، 4h)."""
    frames = []
    for lane in ("L0010", "L0013"):
        for p in sorted((OUTDIR / lane / "4h").rglob("*trades.csv")):
            if "blind" in p.name:          # العمياء نافذة أخرى — تُستبعد
                continue
            d = pd.read_csv(p, encoding="utf-8-sig")
            if {"exit_time", "pnl"} <= set(d.columns) and len(d):
                d["symbol"] = p.parent.name
                frames.append(d[["symbol", "exit_time", "pnl"]])
    if not frames:
        raise FileNotFoundError("لم يُعثر على سلاسل صفقات المحفظة المودعة في L0010/L0013")
    allt = pd.concat(frames, ignore_index=True)
    # صفقة واحدة لكل (رمز، وقت خروج) — ملفات الانزلاق تكرر نفس الصفقة بتكلفة أخرى
    allt = allt.drop_duplicates(subset=["symbol", "exit_time"], keep="first")
    return daily(allt), allt["symbol"].nunique(), len(allt)


def load_l0017_passers() -> dict[str, pd.DataFrame]:
    """كل (فرضية، رمز) عابر للبوابة على 1h و 4h مع سلسلة صفقاته."""
    out = {}
    for tf, lane in (("1h", "L0017-tf1h"), ("4h", "L0017-tf4h")):
        base = OUTDIR / lane
        if not base.exists():
            continue
        for exp_dir in sorted(base.iterdir()):
            f = exp_dir / "all_symbols_test.csv"
            if not f.is_dir() and f.exists():
                t = pd.read_csv(f, encoding="utf-8-sig")
                for _, r in t[t["gate"].astype(str).str.lower().isin(["true", "نعم"])].iterrows():
                    tp = exp_dir / r["symbol"] / "trades.csv"
                    if tp.exists():
                        d = pd.read_csv(tp, encoding="utf-8-sig")
                        if len(d):
                            out[f"{exp_dir.name}|{r['symbol']}|{tf}"] = d
    return out


def main() -> int:
    pf_daily, n_coins, n_tr = load_portfolio_13()
    print(f"سلسلة المحفظة المرجعية: {n_coins} عملة · {n_tr:,} صفقة · "
          f"{len(pf_daily)} يوم تداول · صافٍ {pf_daily.sum():,.2f}$ (مسطرة الإيداع)", flush=True)

    passers = load_l0017_passers()
    print(f"عابرو L0017: {len(passers)} خلية (فرضية×رمز×فريم)\n", flush=True)

    rows = []
    for key, d in sorted(passers.items()):
        exp, sym, tf = key.split("|")
        s = daily(d)
        j = pd.concat([s.rename("l0017"), pf_daily.rename("pf13")], axis=1).dropna()
        c = float(j["l0017"].corr(j["pf13"])) if len(j) >= 20 else float("nan")
        rows.append({"exp": exp, "symbol": sym, "tf": tf, "days_overlap": len(j),
                     "corr_vs_pf13": round(c, 4) if c == c else np.nan,
                     "net": round(float(d["pnl"].sum()), 2), "trades": len(d)})

    df = pd.DataFrame(rows)
    out = OUTDIR / "L0017-corr"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "corr_vs_portfolio13.csv", index=False, encoding="utf-8-sig")

    per_exp = df.groupby("exp")["corr_vs_pf13"].agg(["count", "mean", "min", "max"]).round(4)
    per_exp.to_csv(out / "corr_by_hypothesis.csv", encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    print(df.sort_values("corr_vs_pf13").to_string(index=False), flush=True)
    print("\n— الترابط بالفرضية —", flush=True)
    print(per_exp.to_string(), flush=True)
    print(f"\nالترابط الإجمالي: متوسط {df['corr_vs_pf13'].mean():.4f} · "
          f"أدنى {df['corr_vs_pf13'].min():.4f} · أعلى {df['corr_vs_pf13'].max():.4f}", flush=True)
    print(f"→ {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
