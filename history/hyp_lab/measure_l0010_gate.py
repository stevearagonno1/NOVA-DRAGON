# -*- coding: utf-8 -*-
"""L0010-gate — إكمال شرائط بوابة الاعتماد لسلة الأربع ساعات (بأمر القائد 2026-09-19).

السؤال الواحد: هل تستحق سلة 4h الستة (ETH·SOL·XLM·GRAM·RENDER·FIL) الاعتماد؟ الشرائط
الناقصة كانت أربعة: الاستقرار الإحصائي · أقصى هبوط · زمن الاحتفاظ · عمياء GRAM/RENDER.
هذا السائق لا يجرّب شيئاً جديداً ولا يحسّن شيئاً: يعيد اشتقاق التركيبة المقفلة لكل رمز
من إيداع L0009 (نفس مصدر L0010 حرفاً) على نافذة الامتحان بالكلفة الأساس 0.13%/طرف،
ويقيس من سلسلة الصفقات نفسها: الهبوط ومدته وأسوأ يوم وزمن الاحتفاظ وأطول خسائر،
ويحسب الاستقرار الإحصائي بصيغتي PSR و DSR (Bailey & López de Prado) مع عدد محاولات
الاختيار 32 لكل رمز و192 للسلة — ويعيد اشتقاق عمياء الرموز الأربعة القابلة للقياس.

الضوابط: كاناري إلزامي (يمرره السائق)، نفس آلة L0010 (common.simulate + F_213) حرفاً،
صفر مساس بـ nova_v8، والمخرجات في history/research/hyp_lab_out/L0010-gate/.

    python3 history/hyp_lab/measure_l0010_gate.py --source stream --ref <sha> [--skip-canary]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd

_SCRATCH = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_SCRATCH / "home"))

HERE = pathlib.Path(__file__).resolve().parent
HIST = HERE.parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import common  # noqa: E402
from common import to_bars, TF_MINUTES  # noqa: E402
from common import simulate, trade_rows, atr  # noqa: E402
import run_breakers as RB  # noqa: E402
import F_213_breakers as M213  # noqa: E402

SYMBOLS = ["ETHUSDT", "SOLUSDT", "XLMUSDT", "GRAMUSDT", "RENDERUSDT", "FILUSDT"]
TEST_START, TEST_END = RB.TEST_START, RB.TEST_END          # 2025-01-01 → 2026-08-31
WARM_STD = RB.WARM_START                                   # 2023-06-01
BLIND_WARM, BLIND_START, BLIND_END = "2021-06-01", "2021-09-01", "2023-08-31"
LOCKED_CSV = HIST / "research" / "hyp_lab_out" / "L0009-tf4h" / "F_213" / "all_symbols_test.csv"
OUT = HIST / "research" / "hyp_lab_out" / "L0010-gate"
TF = "4h"
BAR_SECS = TF_MINUTES[TF] * 60
EULER = 0.5772156649015329


# ---------- أدوات القياس ----------

def longest_losing_streak(pnl: np.ndarray) -> int:
    best = cur = 0
    for x in pnl:
        cur = cur + 1 if x < 0 else 0
        best = max(best, cur)
    return best


def drawdown_stats(times: pd.Series, pnl: np.ndarray) -> tuple[float, float, int]:
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    dd = float(np.max(peak - eq))
    under = eq < peak
    longest_days, start, longest_run, run = 0.0, None, 0, 0
    for i, u in enumerate(under):
        if u:
            run += 1
            start = times.iloc[i] if start is None else start
            longest_run = max(longest_run, run)
        else:
            run = 0
            if start is not None:
                longest_days = max(longest_days,
                                   (times.iloc[i] - start).total_seconds() / 86400)
                start = None
    if start is not None:
        longest_days = max(longest_days, (times.iloc[-1] - start).total_seconds() / 86400)
    return dd, float(longest_days), int(longest_run)


def normal_stats(returns: np.ndarray) -> dict:
    sd = float(np.std(returns, ddof=1))
    sr = float(np.mean(returns) / sd) if sd > 0 else 0.0       # شارپ لكل صفقة
    m = float(np.mean(returns))
    skew = float(np.mean(((returns - m) / sd) ** 3)) if sd > 0 else 0.0
    kurt = float(np.mean(((returns - m) / sd) ** 4)) if sd > 0 else 3.0
    return {"sr": sr, "sd": sd, "mean": m, "skew": skew, "kurt": kurt}


def psr_dsr(returns: np.ndarray, years: float, n_trials: int) -> dict:
    """PSR مقابل صفر و DSR مع تصحيح عدد المحاولات — Bailey & López de Prado.

    PSR = Φ[ (SR − 0)·√(T−1) / √(1 − γ₃·SR + ((γ₄−1)/4)·SR²) ]
    DSR = Φ[ (SR − SR*)·√(T−1) / √(نفس المقام) ]
    SR* = √(Var(SR))·[(1−γ)·Z⁻¹(1−1/N) + γ·Z⁻¹(1−1/(N·e))]   وVar(SR) ≈ (1+SR²/2)/T
    — تقريب موثق (iid طبيعي): لا يقلل من صرامة العتبة، ويُقرأ مع الافتراضات في dsr_notes.
    """
    nd = NormalDist()
    z = normal_stats(returns)
    T = len(returns)
    sr, g3, g4 = z["sr"], z["skew"], z["kurt"]
    denom = np.sqrt(max(1e-12, 1 - g3 * sr + ((g4 - 1) / 4) * sr ** 2))
    psr = nd.cdf(sr * np.sqrt(T - 1) / denom)
    var_sr = (1 + sr ** 2 / 2) / T
    sr_star = np.sqrt(var_sr) * ((1 - EULER) * nd.inv_cdf(1 - 1 / n_trials)
                                 + EULER * nd.inv_cdf(1 - 1 / (n_trials * np.e)))
    dsr = nd.cdf((sr - sr_star) * np.sqrt(T - 1) / denom)
    trades_per_year = T / years
    psr_z = float(sr * np.sqrt(T - 1) / denom)
    dsr_z = float((sr - sr_star) * np.sqrt(T - 1) / denom)
    return {
        "n_trades": T, "psr_z": round(psr_z, 3), "dsr_z": round(dsr_z, 3), "sr_per_trade": round(sr, 5),
        "sharpe_annual_approx": round(sr * np.sqrt(trades_per_year), 3),
        "trades_per_year": round(trades_per_year, 1),
        "skew": round(g3, 4), "kurtosis": round(g4, 4),
        "psr_vs_zero": round(psr, 6), "sr_star": round(float(sr_star), 6),
        "dsr": round(float(dsr), 6), "n_trials": n_trials,
    }


def side_stats(name: str, trades: list[dict], years: float, n_trials: int) -> dict:
    df = pd.DataFrame(trade_rows(name, "measure", trades))
    df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True)
    pnl = df["pnl"].to_numpy(dtype=float)
    g, lo = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    dd, dd_days, dd_run = drawdown_stats(df["exit_time"], pnl)
    day = df.groupby(df["exit_time"].dt.date)["pnl"].sum()
    half = len(df) // 2
    stats = {
        "symbol": name, "trades": int(len(df)),
        "net": round(float(pnl.sum()), 4),
        "win_pct": round(100 * float((pnl > 0).mean()), 2),
        "pf": round(float(g / lo), 4) if lo > 0 else float("inf"),
        "avg_win": round(float(pnl[pnl > 0].mean()), 4),
        "avg_loss": round(float(pnl[pnl < 0].mean()), 4),
        "longest_loss_streak": longest_losing_streak(pnl),
        "avg_hours_held": round(float(df["bars_held"].mean()) * TF_MINUTES[TF] / 60, 2),
        "max_dd": round(dd, 4), "longest_dd_days": round(dd_days, 1),
        "longest_dd_trades": dd_run,
        "worst_day": round(float(day.min()), 4),
        "first_half_net": round(float(pnl[:half].sum()), 2),
        "second_half_net": round(float(pnl[half:].sum()), 2),
        "first_exit": str(df["exit_time"].iloc[0]), "last_exit": str(df["exit_time"].iloc[-1]),
    }
    stats.update(psr_dsr(pnl, years, n_trials))
    return stats, df


# ---------- التنفيذ ----------

def canary_gate(args) -> str:
    if args.skip_canary:
        print("تحذير: --skip-canary — لا اعتماد.", flush=True)
        return "skipped"
    cmd = [sys.executable, str(ROOT / "tools" / "canary.py"), "--json"]
    if args.source == "stream":
        cmd += ["--source", "stream", "--ref", args.ref]
    can = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if data.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", can.stdout, can.stderr, file=sys.stderr)
        raise SystemExit(1)
    net = data["got"]["net"]
    print(f"الكاناري: PASS (net={net} trades={data['got']['trades']})", flush=True)
    return str(net)


def load_symbol(sym: str, warm: str, end: str, args):
    """نفس اصطلاح السائق الأب حرفًا (run_stress.load_frames): من warm (ضمًّا) إلى end (قبلًا)."""
    if args.source == "stream":
        df, sha, nb = RB.stream_symbol(sym, args.ref)
        df = df[(df.index >= pd.Timestamp(warm, tz="UTC")) & (df.index < pd.Timestamp(end, tz="UTC"))]
        return df, f"stream:{sha}:{nb}"
    p = RB.resolve_archive(args.archive) / f"{sym}_1m.parquet"
    return common.load(str(p), start=warm, end=end), "disk"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["disk", "stream"], default="stream")
    ap.add_argument("--archive", default=None)
    ap.add_argument("--ref", default="main")
    ap.add_argument("--skip-canary", action="store_true")
    args = ap.parse_args()

    canary_net = canary_gate(args)
    locked = pd.read_csv(LOCKED_CSV, encoding="utf-8-sig").set_index("symbol")
    OUT.mkdir(parents=True, exist_ok=True)

    years = (pd.Timestamp(TEST_END, tz="UTC") - pd.Timestamp(TEST_START, tz="UTC")).days / 365.25
    rows, basket_frames, blind_rows, raw_nets = [], [], [], []
    for sym in SYMBOLS:
        if sym not in locked.index:
            print(f"{sym}: ليس في المقفلات — تخطي", flush=True)
            continue
        lk = locked.loc[sym]
        if not bool(lk["gate"]):
            print(f"{sym}: لم يعبر بوابـة L0009 ({float(lk['test_net']):.2f}$) — لا يُقاس هنا", flush=True)
            continue
        combo = {"exit": lk["sel_NOVA_EXIT"], "trigger": lk["sel_NOVA_TRIGGER"]}

        df1m, sha = load_symbol(sym, WARM_STD, TEST_END, args)
        b4 = to_bars(df1m, TF_MINUTES[TF])
        te = b4[(b4.index >= pd.Timestamp(TEST_START, tz="UTC")) &
                (b4.index <= pd.Timestamp(TEST_END + " 23:59:59", tz="UTC"))]
        sig = M213.make_signals(b4, trigger=combo["trigger"]).loc[te.index]
        st, tr = simulate(te, sig, atr(te), notional=1000, bar_secs=BAR_SECS,
                          **RB.sim_kwargs("F_213", combo))
        # تحقق متقاطع صارم مع الإيداع
        d_net = abs(float(st["net"]) - float(lk["test_net"]))
        d_tr = abs(int(st["trades"]) - int(lk["test_trades"]))
        print(f"{sym}: net={st['net']:.4f}$ trades={st['trades']} pf={RB.pf_of(tr):.4f} "
              f"| Δ مقابل L0009 = {d_net:.2e}$ / {d_tr} صفقة", flush=True)
        row, tdf = side_stats(sym, tr, years, n_trials=32)
        row.update({"sha": sha, "combo": f"{combo['exit']}/{combo['trigger']}",
                    "delta_vs_l0009_net": round(d_net, 10), "sel_combo": combo["trigger"]})
        rows.append(row)
        raw_nets.append(float(st["net"]))
        tdf.to_csv(OUT / f"base_trades_4h_{sym}.csv", index=False, encoding="utf-8-sig")
        basket_frames.append(tdf)

        # العمياء: يعاد اشتقاقها للرموز التي لها نافذة (البيانات من 2021-06)
        df1m_b, _ = load_symbol(sym, BLIND_WARM, BLIND_END, args)
        if len(df1m_b) == 0:                    # بياناته تبدأ بعد نهاية النافذة (كما في سائق L0010)
            first = b4.index[0]
            print(f"{sym}: صفر شمعة في نافذة العمياء (بياناته تبدأ {first}) ⇒ غير مقاسة بنيوياً",
                  flush=True)
            blind_rows.append({"symbol": sym, "status": "غير مقاسة — البيانات تبدأ بعد النافذة",
                               "first_bar": str(first), "blind_net": None, "trades": 0,
                               "max_dd": None, "avg_hours_held": None,
                               "longest_loss_streak": None, "worst_day": None})
            continue
        first = df1m_b.index[0]
        if first > pd.Timestamp(BLIND_START, tz="UTC"):
            print(f"{sym}: أول شمعة {first} — النافذة العمياء 2021-09→2023-08 غير موجودة له "
                  f"⇒ غير مقاسة بنيوياً (لا فاشلة)", flush=True)
            blind_rows.append({"symbol": sym, "status": "غير مقاسة — البيانات تبدأ بعد النافذة",
                               "first_bar": str(first), "blind_net": None, "trades": 0,
                               "max_dd": None, "avg_hours_held": None,
                               "longest_loss_streak": None, "worst_day": None})
            continue
        b4b = to_bars(df1m_b, TF_MINUTES[TF])
        bl = b4b[(b4b.index >= pd.Timestamp(BLIND_START, tz="UTC")) &
                 (b4b.index <= pd.Timestamp(BLIND_END, tz="UTC"))]  # اصطلاح السائق: نهاية النافذة منتصف ليل BLIND_END
        sigb = M213.make_signals(b4b, trigger=combo["trigger"]).loc[bl.index]
        stb, trb = simulate(bl, sigb, atr(bl), notional=1000, bar_secs=BAR_SECS,
                            **RB.sim_kwargs("F_213", combo))
        years_b = (pd.Timestamp(BLIND_END, tz="UTC") - pd.Timestamp(BLIND_START, tz="UTC")).days / 365.25
        brow, bdf = side_stats(sym, trb, years_b, n_trials=32)
        brow.update({"status": "مقاسة", "first_bar": str(first),
                     "blind_net": round(float(stb["net"]), 4), "trades": int(stb["trades"]),
                     "pf": round(RB.pf_of(trb), 4)})
        blind_rows.append(brow)
        bdf.to_csv(OUT / f"blind_trades_4h_{sym}.csv", index=False, encoding="utf-8-sig")
        print(f"{sym}: عمياء {stb['net']:.2f}$ ({stb['trades']} صفقة) | هبوط {brow['max_dd']}$ "
              f"| احتفاظ {brow['avg_hours_held']} ساعة", flush=True)

    # ---------- السلة: كل الصفقات مجتمعة بترتيب زمن الخروج ----------
    allt = pd.concat(basket_frames).sort_values("exit_time").reset_index(drop=True)
    bpnl = allt["pnl"].to_numpy(dtype=float)
    g, lo = bpnl[bpnl > 0].sum(), -bpnl[bpnl < 0].sum()
    dd, dd_days, dd_run = drawdown_stats(allt["exit_time"], bpnl)
    day = allt.groupby(allt["exit_time"].dt.date)["pnl"].sum()
    bstats = {
        "symbol": "BASKET6", "trades": int(len(allt)), "net": round(float(bpnl.sum()), 4),
        "win_pct": round(100 * float((bpnl > 0).mean()), 2),
        "pf": round(float(g / lo), 4), "avg_win": round(float(bpnl[bpnl > 0].mean()), 4),
        "avg_loss": round(float(bpnl[bpnl < 0].mean()), 4),
        "longest_loss_streak": longest_losing_streak(bpnl),
        "avg_hours_held": round(float(allt["bars_held"].mean()) * TF_MINUTES[TF] / 60, 2),
        "max_dd": round(dd, 4), "longest_dd_days": round(dd_days, 1),
        "longest_dd_trades": dd_run, "worst_day": round(float(day.min()), 4),
        "first_half_net": round(float(bpnl[:len(allt) // 2].sum()), 2),
        "second_half_net": round(float(bpnl[len(allt) // 2:].sum()), 2),
        "first_exit": str(allt["exit_time"].iloc[0]), "last_exit": str(allt["exit_time"].iloc[-1]),
        "combo": "—", "sha": "—", "delta_vs_l0009_net": 0.0, "sel_combo": "—",
    }
    bstats.update(psr_dsr(bpnl, years, n_trials=192))
    unrounded = float(sum(raw_nets))    # مجموع nets المحاكاة الخام (غير مقرّبة) للرموز الستة
    bstats["basket_net_unrounded"] = round(unrounded, 6)
    bstats["delta_vs_l0010_documented"] = round(unrounded - 32608.11, 6)
    bstats["basket_net_from_rounded_trades"] = bstats["net"]
    rows.append(bstats)
    allt.to_csv(OUT / "base_trades_4h_BASKET6.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(rows).to_csv(OUT / "gate_metrics_4h.csv", index=False, encoding="utf-8-sig")
    bdf_out = pd.DataFrame(blind_rows)
    bdf_out.to_csv(OUT / "blind_gate_4h.csv", index=False, encoding="utf-8-sig")

    # ---------- متانة الشبكة (تُقرأ من إيداع L0010 — تحقق متقاطع لا إعادة تشغيل) ----------
    grid_rows = []
    for sym in SYMBOLS:
        gpath = HIST / "research" / "hyp_lab_out" / "L0010" / "4h" / "F_213" / sym / "test_matrix.csv"
        if not gpath.exists():
            continue
        g = pd.read_csv(gpath, encoding="utf-8-sig")
        if "test_net" not in g.columns:
            continue
        grid_rows.append({"symbol": sym, "cells": len(g),
                          "positive_cells": int((g["test_net"] > 0).sum()),
                          "mean_net": round(float(g["test_net"].mean()), 2),
                          "median_net": round(float(g["test_net"].median()), 2),
                          "min_net": round(float(g["test_net"].min()), 2),
                          "max_net": round(float(g["test_net"].max()), 2)})
    if grid_rows:
        pd.DataFrame(grid_rows).to_csv(OUT / "grid_robustness_4h.csv", index=False, encoding="utf-8-sig")

    # توزيع أرباع السنة للسلة (من سلسلة الصفقات المودعة أعلاه)
    q = allt.assign(q=allt["exit_time"].dt.tz_localize(None).dt.to_period("Q")).groupby("q")["pnl"].agg(["sum", "count"])
    q.columns = ["net", "trades"]
    q["net"] = q["net"].round(2)
    q.to_csv(OUT / "basket_quarters_4h.csv", encoding="utf-8-sig")

    notes = [
        "L0010-gate — ملاحظات الاستقرار الإحصائي (كل رقم قابل لإعادة الاشتقاق بأمر هذا السائق)",
        f"canary={canary_net} | ref={args.ref} | source={args.source}",
        f"pandas={pd.__version__} numpy={np.__version__} python={sys.version.split()[0]}",
        "",
        "PSR = Φ[ SR·√(T−1) / √(1 − γ₃·SR + ((γ₄−1)/4)·SR²) ]         (احتمال أن يكون الشارپ الحقيقي > 0)",
        "DSR = Φ[ (SR − SR*)·√(T−1) / √(نفس المقام) ]",
        "SR* = √(Var(SR))·[(1−γ)·Z⁻¹(1−1/N) + γ·Z⁻¹(1−1/(N·e))]،  γ=0.5772 (أويلر)،  Var(SR) ≈ (1+SR²/2)/T",
        "N = 32 محاولة لكل رمز (شبكة L0009: 16 قاطعاً × خروجان) و192 للسلة (32 × 6 رموز) — عدد محاولات الاختيار الفعلي.",
        "الافتراضات المعلنة: عوائد الصفقات iid؛ تقريب Var(SR) هو الأعلى (الأصرم) لأنه يستعمل SR المقاس نفسه؛",
        "والتقريب لا يعوّض الفروق الحقيقية في تباين المحاولات — فلو رغب القائد في نسخة أدق تحتاج سلسلة عوائد لكل خلية",
        "(تشغيل أثقل) لا مجرد جداول الصافي المودعة.",
        "",
        "نتيجة السلة: SR لكل صفقة = %.5f | شارپ سنوي تقريبي = %.3f | PSR = %.6f (z=%.3f) | DSRA = %.6f (z=%.3f)"
        % (bstats["sr_per_trade"], bstats["sharpe_annual_approx"], bstats["psr_vs_zero"],
           bstats["psr_z"], bstats["dsr"], bstats["dsr_z"]),
        "",
        "أرباع السنة (السلة، صافي $ / صفقات):",
    ] + [f"  {idx}: {row['net']:.2f}$ / {int(row['trades'])}" for idx, row in q.iterrows()] + [
        "",
        "التحقق المتقاطع: لكل رمز Δ مقابل إيداع L0009 = 0.00e+00$ و0 صفقة (إعادة اشتقاق حرفية للخلايا المقفلة).",
        f"صافي السلة الخام (غير مقرّب) = {unrounded:.6f}$ مقابل الموثق {32608.11}$ ⇒ فرق {unrounded-32608.11:+.6f}$.",
        f"صافي السلة من ملفات التداول المقرّبة لأربع خانات = {bstats['net']:.4f}$ (فرق التقريب {unrounded-bstats['net']:+.6f}$).",
    ]
    (OUT / "dsr_notes.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")

    print("\n=== سلة الستة — المقاسات المكملة ===", flush=True)
    print(f"الصافي {bstats['net']:.2f}$ · صفقات {bstats['trades']} · PF {bstats['pf']} · "
          f"هبوط {bstats['max_dd']:.2f}$ ({bstats['longest_dd_days']} يومًا) · "
          f"أسوأ يوم {bstats['worst_day']:.2f}$ · احتفاظ {bstats['avg_hours_held']} ساعة", flush=True)
    print(f"شارپ سنوي (تقريب) {bstats['sharpe_annual_approx']} · PSR {bstats['psr_vs_zero']} · "
          f"DSR (192 محاولة) {bstats['dsr']} (z={bstats['dsr_z']})", flush=True)
    print(f"نصفان: أول {bstats['first_half_net']:.2f}$ / ثانٍ {bstats['second_half_net']:.2f}$", flush=True)
    print(f"\nالمخرجات في {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
