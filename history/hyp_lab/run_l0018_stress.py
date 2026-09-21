# -*- coding: utf-8 -*-
"""L0018 — جولة الضغط على عابري دفعة الجرد الأولى (L0017) — نهج L0010/L0013 حرفًا.

المحاور الأربعة (نفس محاور L0010، مطبقة على عابري L0017 المقفلين بلا أي إعادة اختيار):
  slip    : انزلاق مجهد 0.10% و 0.30% لكل طرف بدل الأساس 0.03% (العمولة 0.10% ثابتة)
  blind   : النافذة العمياء 2021-09-01→2023-08-31 — ما لم ترَه التجربة أبدًا؛ وغير الممكن يوثق
  plateau : الجوار ±20% حول محاور الفرضية المنتقاة — يفصل الجوار الآمن عن قمة الحظ المنفردة
  dsr     : الاستقرار الإحصائي PSR/DSR بتصحيح عدد المحاولات (Bailey & López de Prado)

التركيبات **مقفلة من إيداع L0017** (عمود sel_* في all_symbols_test.csv) — صفر إعادة اختيار،
وهذا شرط الضغط: نمتحن ما انتُقي، لا ننتقي من جديد حتى ينجح (الدستور §27 البند 6).

لا مساس بـ nova_v8/** ولا بإيداع L0017. المخرجات في
history/research/hyp_lab_out/L0018/ بأشكال ملفات L0010 (مقارنة مباشرة ممكنة).

    python3 history/hyp_lab/run_l0018_stress.py --tf 4h --mode all
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import pathlib
import platform
import subprocess
import sys
import time

import numpy as np
import pandas as pd

_SCRATCH = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_SCRATCH / "home"))

HIST = pathlib.Path(__file__).resolve().parents[1]
ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import common as C  # noqa: E402
from common import load, to_5m, to_bars, TF_MINUTES, atr, simulate, trade_rows  # noqa: E402
from measure_l0010_gate import drawdown_stats, longest_losing_streak, psr_dsr  # noqa: E402
import F_197_dual_trail as M197  # noqa: E402

import run_l0017 as R17  # noqa: E402

O = HIST / "research" / "hyp_lab_out"
OUT_ROOT = O / "L0018"

TEST_START, TEST_END = "2025-01-01", "2026-08-31"
BLIND_START, BLIND_END = "2021-09-01", "2023-08-31"
BLIND_WARM = "2021-06-01"
SLIP_TIERS = [0.0003, 0.0010, 0.0030]          # الأساس ثم المجهدان
FEE = 0.0010
DUAL_TRIG, DUAL_LOCK = 0.0025, 0.0045
PLATEAU_FACTORS = [0.8, 1.0, 1.2]              # ±20%

TEST_YEARS = (pd.Timestamp(TEST_END, tz="UTC") - pd.Timestamp(TEST_START, tz="UTC")).days / 365.25
BLIND_YEARS = (pd.Timestamp(BLIND_END, tz="UTC") - pd.Timestamp(BLIND_START, tz="UTC")).days / 365.25

# الفرضية المدفونة لا تُضغط: لا يُضغط ما سقط (نهج L0013 مع BNB)
BURIED = {"F_015_zscore_regime"}


def set_cost(slip: float) -> None:
    """يضبط تكلفة الطرف في وحدة المختبر المشتركة (العمولة ثابتة + الانزلاق متغير)."""
    C.SLIP_PER_SIDE = slip
    C.COST_PER_SIDE = FEE + slip


def dual_spec() -> dict:
    return M197.make_dual_spec(trig=DUAL_TRIG, lock=DUAL_LOCK)


def locked_cells(tf: str) -> list[dict]:
    """عابرو L0017 على هذا الفريم مع محاورهم المقفلة من الإيداع."""
    lane = {"1h": "L0017-tf1h", "4h": "L0017-tf4h"}[tf]
    cells = []
    for exp_dir in sorted((O / lane).iterdir()):
        if not exp_dir.is_dir() or exp_dir.name in BURIED:
            continue
        f = exp_dir / "all_symbols_test.csv"
        if not f.exists():
            continue
        t = pd.read_csv(f, encoding="utf-8-sig")
        for _, r in t[t["gate"] == True].iterrows():          # noqa: E712
            keys = list(R17.EXPS[exp_dir.name].SWEEP_PARAMS.keys())
            combo = {k: r[f"sel_NOVA_{k.upper()}"] for k in keys}
            # الأعداد الصحيحة تعود من CSV كـ float — تُعاد لنوعها الأصلي
            for k in keys:
                ref = R17.EXPS[exp_dir.name].SWEEP_PARAMS[k][0]
                combo[k] = int(combo[k]) if isinstance(ref, int) else float(combo[k])
            cells.append({"exp": exp_dir.name, "symbol": r["symbol"], "combo": combo,
                          "dep_net": float(r["test_net"]), "dep_trades": int(r["test_trades"]),
                          "dep_pf": float(r["test_pf"])})
    return cells


def pf_of(trades: list[dict]) -> float:
    g = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    lo = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    if lo > 0:
        return g / lo
    return float("inf") if g > 0 else 0.0


def frame_for(sym: str, tf: str, start: str, end: str) -> pd.DataFrame:
    p = ROOT / "crypto_archive" / f"{sym}_1m.parquet"
    df1m = load(str(p), start=start, end=end)
    if not len(df1m):
        return df1m
    return to_5m(df1m) if tf == "5m" else to_bars(df1m, TF_MINUTES[tf])


def run_cell(exp: str, df_full: pd.DataFrame, win: pd.DataFrame, combo: dict, bar_secs: int):
    sig = R17.EXPS[exp].make_signals(df_full, **combo).loc[win.index]
    return simulate(win, sig, atr(win), notional=C.TRADE_USD, bar_secs=bar_secs,
                    exit_mode="dual", dual=dual_spec())


# ---------------- المحاور ----------------

def axis_slip(cells, tf, frames_test, bar_secs, out) -> pd.DataFrame:
    rows = []
    for c in cells:
        df = frames_test[c["symbol"]]
        win = df[(df.index >= TEST_START) & (df.index <= TEST_END)]
        for slip in SLIP_TIERS:
            set_cost(slip)
            st, tr = run_cell(c["exp"], df, win, c["combo"], bar_secs)
            rows.append({"exp": c["exp"], "symbol": c["symbol"], "slip_per_side": slip,
                         "net": round(st["net"], 4), "trades": st["trades"],
                         "win_pct": st["win_pct"], "pf": round(pf_of(tr), 4),
                         "survives": bool(st["net"] > 0 and pf_of(tr) >= 1.3)})
        set_cost(0.0003)
    d = pd.DataFrame(rows)
    d.to_csv(out / f"slip_tiers_{tf}.csv", index=False, encoding="utf-8-sig")
    return d


def axis_blind(cells, tf, bar_secs, out) -> pd.DataFrame:
    rows = []
    set_cost(0.0003)
    cache = {}
    for c in cells:
        sym = c["symbol"]
        if sym not in cache:
            cache[sym] = frame_for(sym, tf, BLIND_WARM, BLIND_END)
        df = cache[sym]
        win = df[(df.index >= BLIND_START) & (df.index <= BLIND_END)] if len(df) else df
        if len(win) < 200:
            rows.append({"exp": c["exp"], "symbol": sym, "net": np.nan, "trades": 0,
                         "win_pct": np.nan, "pf": np.nan, "measurable": False,
                         "note": "غير مقاسة بنيويًا — بيانات الرمز تبدأ بعد النافذة العمياء"})
            continue
        st, tr = run_cell(c["exp"], df, win, c["combo"], bar_secs)
        rows.append({"exp": c["exp"], "symbol": sym, "net": round(st["net"], 4),
                     "trades": st["trades"], "win_pct": st["win_pct"],
                     "pf": round(pf_of(tr), 4), "measurable": True, "note": ""})
    d = pd.DataFrame(rows)
    d.to_csv(out / f"blind_{tf}.csv", index=False, encoding="utf-8-sig")
    return d


def axis_plateau(cells, tf, frames_test, bar_secs, out) -> pd.DataFrame:
    """الجوار ±20% على كل محور عددي للفرضية (المحاور الصحيحة تُدوَّر، والقوائم تلتزم قيمها)."""
    rows = []
    set_cost(0.0003)
    for c in cells:
        df = frames_test[c["symbol"]]
        win = df[(df.index >= TEST_START) & (df.index <= TEST_END)]
        keys = list(c["combo"].keys())
        grids = []
        for k in keys:
            v = c["combo"][k]
            vals = []
            for f in PLATEAU_FACTORS:
                nv = v * f
                nv = int(round(nv)) if isinstance(v, int) else round(nv, 6)
                if nv not in vals:
                    vals.append(nv)
            grids.append(vals)
        for vals in itertools.product(*grids):
            nb = dict(zip(keys, vals))
            st, tr = run_cell(c["exp"], df, win, nb, bar_secs)
            rows.append({"exp": c["exp"], "symbol": c["symbol"],
                         "neighbour": "/".join(f"{k}={nb[k]}" for k in keys),
                         "is_center": nb == c["combo"],
                         "net": round(st["net"], 4), "trades": st["trades"],
                         "pf": round(pf_of(tr), 4), "positive": bool(st["net"] > 0)})
    d = pd.DataFrame(rows)
    d.to_csv(out / f"plateau_{tf}.csv", index=False, encoding="utf-8-sig")
    return d


def axis_dsr(cells, tf, frames_test, bar_secs, out) -> pd.DataFrame:
    """الاستقرار الإحصائي على سلة العابرين وعلى كل فرضية — بتصحيح عدد المحاولات الحقيقي."""
    set_cost(0.0003)
    per_trades = {}
    for c in cells:
        df = frames_test[c["symbol"]]
        win = df[(df.index >= TEST_START) & (df.index <= TEST_END)]
        st, tr = run_cell(c["exp"], df, win, c["combo"], bar_secs)
        d = pd.DataFrame(trade_rows(c["symbol"], c["exp"], tr))
        if len(d):
            d["exp"] = c["exp"]
            per_trades[(c["exp"], c["symbol"])] = d

    rows = []
    allt = pd.concat(per_trades.values(), ignore_index=True) if per_trades else pd.DataFrame()

    def block(name: str, d: pd.DataFrame, n_trials: int):
        d = d.copy()
        d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
        d = d.sort_values("exit_time")
        p = d["pnl"].to_numpy(float)
        dd, dd_days, _ = drawdown_stats(d["exit_time"], p)
        r = {"block": name, "trades": len(d), "net": round(float(p.sum()), 2),
             "pf": round(float(p[p > 0].sum() / -p[p < 0].sum()), 4) if (p < 0).any() else np.inf,
             "max_dd": round(dd, 2), "dd_days": round(dd_days, 1),
             "longest_loss_streak": longest_losing_streak(p)}
        r.update(psr_dsr(p, TEST_YEARS, n_trials))
        return r

    n_cells = len(cells)
    if len(allt):
        # عدد المحاولات الحقيقي = كل خلايا الشبكة التي مرت في الاختيار على هذا الفريم
        trials_all = sum(len(R17.combos_for(e)) for e in R17.EXPS if e not in BURIED) * 8
        rows.append(block(f"سلة العابرين {tf} ({n_cells} خلية)", allt, trials_all))
        for exp, sub in allt.groupby("exp"):
            rows.append(block(f"{exp} · {tf}", sub, len(R17.combos_for(exp)) * 8))
    d = pd.DataFrame(rows)
    d.to_csv(out / f"dsr_{tf}.csv", index=False, encoding="utf-8-sig")
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description="L0018 — ضغط عابري L0017")
    ap.add_argument("--tf", choices=["1h", "4h", "both"], default="4h")
    ap.add_argument("--mode", choices=["all", "slip", "blind", "plateau", "dsr"], default="all")
    ap.add_argument("--skip-canary", action="store_true")
    args = ap.parse_args()
    tfs = ["1h", "4h"] if args.tf == "both" else [args.tf]
    t0 = time.time()

    canary_net = "skipped"
    if not args.skip_canary:
        can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                             capture_output=True, text=True)
        cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
        if cj.get("canary") != "ok":
            print("الكاناري فشل — إيقاف L0018.", file=sys.stderr)
            return 1
        canary_net = cj["got"]["net"]
        print(f"الكاناري: PASS (net={canary_net})", flush=True)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 250)

    for tf in tfs:
        out = OUT_ROOT / tf
        out.mkdir(parents=True, exist_ok=True)
        bar_secs = TF_MINUTES[tf] * 60
        cells = locked_cells(tf)
        syms = sorted({c["symbol"] for c in cells})
        print(f"\n[{tf}] خلايا مقفلة من إيداع L0017: {len(cells)} · رموز: {len(syms)}", flush=True)
        for c in cells:
            print(f"   {c['exp']}/{c['symbol']} ← {c['combo']} (إيداع {c['dep_net']:.2f}$)", flush=True)

        frames_test = {s: frame_for(s, tf, "2023-06-01", TEST_END) for s in syms}

        if args.mode in ("all", "slip"):
            d = axis_slip(cells, tf, frames_test, bar_secs, out)
            print(f"\n— الانزلاق المجهد ({tf}) —", flush=True)
            piv = d.pivot_table(index=["exp", "symbol"], columns="slip_per_side",
                                values="net", aggfunc="first").round(2)
            print(piv.to_string(), flush=True)
            for s in SLIP_TIERS:
                sub = d[d["slip_per_side"] == s]
                print(f"  انزلاق {s*100:.2f}%: صافي السلة {sub['net'].sum():.2f}$ · "
                      f"ناجية {int(sub['survives'].sum())}/{len(sub)}", flush=True)

        if args.mode in ("all", "blind"):
            d = axis_blind(cells, tf, bar_secs, out)
            m = d[d["measurable"]]
            print(f"\n— العمياء 2021-2023 ({tf}) — قابلة للقياس {len(m)}/{len(d)}", flush=True)
            if len(m):
                print(m[["exp", "symbol", "net", "trades", "pf"]].to_string(index=False), flush=True)
                print(f"  صافي السلة العمياء: {m['net'].sum():.2f}$ · "
                      f"موجبة {int((m['net'] > 0).sum())}/{len(m)}", flush=True)
            nm = d[~d["measurable"]]
            if len(nm):
                print(f"  غير مقاسة بنيويًا: {sorted(set(nm['symbol']))}", flush=True)

        if args.mode in ("all", "plateau"):
            d = axis_plateau(cells, tf, frames_test, bar_secs, out)
            print(f"\n— الجوار ±20% ({tf}) —", flush=True)
            g = d.groupby(["exp", "symbol"]).agg(
                جيران=("positive", "size"), موجب=("positive", "sum")).reset_index()
            print(g.to_string(index=False), flush=True)
            print(f"  الإجمالي: {int(d['positive'].sum())}/{len(d)} جار موجب "
                  f"({100*d['positive'].mean():.1f}%)", flush=True)

        if args.mode in ("all", "dsr"):
            d = axis_dsr(cells, tf, frames_test, bar_secs, out)
            print(f"\n— الاستقرار الإحصائي ({tf}) —", flush=True)
            print(d[["block", "trades", "net", "pf", "max_dd", "dd_days",
                     "dsr", "dsr_z", "psr_vs_zero", "n_trials"]].to_string(index=False), flush=True)

        (out / "env_dump.txt").write_text(
            f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
            f"canary={canary_net}\nbar={tf}\nnotional={C.TRADE_USD}$\nfee={FEE}/side\n"
            f"slip_tiers={SLIP_TIERS}\nblind={BLIND_START}→{BLIND_END}\n"
            f"plateau=±20% ({PLATEAU_FACTORS})\nlocked_from=L0017 deposit (no re-selection)\n"
            f"buried_not_stressed={sorted(BURIED)}\ncells={len(cells)}\n", encoding="utf-8")
        print(f"\nفريم {tf} اكتمل → {out}", flush=True)

    print(f"\nالكل: {time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
