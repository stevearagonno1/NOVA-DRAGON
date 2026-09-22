# -*- coding: utf-8 -*-
"""L0019 — دفعة الجرد الثانية: خمس فرضيات دخول من طابور المصنع (بروتوكول خط الإنتاج)

الأمر: أمر القائد 2026-09-22 («ابدء دفعه الفرضيات») + القرار D-0046 + العقد
      docs/lanes/L0019-inventory-batch2-entries.md

البروتوكول (على حرفية run_l0017.py — لا انحراف في الحكم):
  - النوافذ: تدريب 2023-09-01→2024-12-31 | اختبار 2025-01-01→2026-08-31 · دفء من 2023-06-01
  - الاختيار على التدريب فقط من التركيبات غير المتحللة (≥30 صفقة تدريب) — الحكم على الاختبار فقط
  - بوابة خط الإنتاج على الاختبار: net>0 AND PF≥1.3 AND trades≥30
  - التكاليف 0.13% لكل طرف · 20$ للصفقة (الدستور §27 / D-0044) · شراء فقط 🔒
  - الخروج: المطاردة ثنائية السرعة بالتركيبة الذهبية trig=0.0025 lock=0.0045 (ثابت المختبر)
  - الكاناري بوابة سابقة إلزامية · حتمية: بلا عشوائية · الجداول utf-8-sig (D-0011)

المخرجات: history/research/hyp_lab_out/L0019{,-tf1h,-tf4h}/<EXP>/<sym>/{sweep_train,test_selected}.csv
          + <EXP>/all_symbols_{train,test}.csv + env_dump.txt + summary.txt
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

HIST = pathlib.Path(__file__).resolve().parents[1]
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from common import BASE_NOTIONAL, load, to_5m, to_bars, TF_MINUTES, atr, simulate, trade_rows  # noqa: E402
import F_197_dual_trail as M197  # noqa: E402

import L0019_F_002_marsdx as E002          # noqa: E402
import L0019_F_003_vwap_bounce as E003     # noqa: E402
import L0019_F_004_orb_retest as E004      # noqa: E402
import L0019_F_006_bb_squeeze as E006      # noqa: E402
import L0019_F_007_ttm_squeeze as E007     # noqa: E402

EXPS = {
    "F_002_marsdx": E002,
    "F_003_vwap_bounce": E003,
    "F_004_orb_retest": E004,
    "F_006_bb_squeeze": E006,
    "F_007_ttm_squeeze": E007,
}

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XLMUSDT", "LINKUSDT", "GRAMUSDT", "RENDERUSDT", "FILUSDT"]
WARM_START = "2023-06-01"
TRAIN_START, TRAIN_END = "2023-09-01", "2024-12-31"
TEST_START, TEST_END = "2025-01-01", "2026-08-31"
GATE_PF, GATE_TRADES = 1.3, 30
MIN_TRAIN_TRADES = 30
TRADE_COLS = ["symbol", "exp", "entry_time", "exit_time", "entry", "exit",
              "notional", "pnl", "r_mult", "exit_side", "bars_held"]
TF_OUT = {"5m": "L0019", "1h": "L0019-tf1h", "4h": "L0019-tf4h"}
DUAL_TRIG, DUAL_LOCK = 0.0025, 0.0045


def dual_spec() -> dict:
    return M197.make_dual_spec(trig=DUAL_TRIG, lock=DUAL_LOCK)


def combos_for(exp: str) -> list[dict]:
    sp = EXPS[exp].SWEEP_PARAMS
    keys = list(sp.keys())
    return [dict(zip(keys, vals)) for vals in itertools.product(*(sp[k] for k in keys))]


def param_cols(exp: str) -> list[str]:
    return [f"NOVA_{k.upper()}" for k in EXPS[exp].SWEEP_PARAMS.keys()]


def combo_row(exp: str, combo: dict) -> dict:
    return {f"NOVA_{k.upper()}": v for k, v in combo.items()}


def signals_for(exp: str, df_full: pd.DataFrame, window: pd.DataFrame, combo: dict) -> pd.Series:
    return EXPS[exp].make_signals(df_full, **combo).loc[window.index]


def pf_of(trades: list[dict]) -> float:
    g = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    lo = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    if lo > 0:
        return g / lo
    return float("inf") if g > 0 else 0.0


def stats_row(st: dict, trades: list[dict]) -> dict:
    return {"net": st["net"], "trades": st["trades"], "win_pct": st["win_pct"], "pf": pf_of(trades)}


def resolve_archive(cli: str | None) -> pathlib.Path:
    if cli:
        return pathlib.Path(cli).expanduser()
    env = os.environ.get("NOVA_ARCHIVE", "")
    if env:
        return pathlib.Path(env).expanduser()
    for cand in (ROOT / "crypto_archive", HIST / "crypto_archive"):
        if (cand / "BTCUSDT_1m.parquet").exists():
            return cand
    return ROOT / "crypto_archive"


def load_symbol(sym: str, args) -> tuple[pd.DataFrame, str]:
    p = resolve_archive(args.archive) / f"{sym}_1m.parquet"
    if not p.exists():
        raise FileNotFoundError(f"لا يوجد {p} — مرّر --archive PATH")
    sha = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return load(str(p), start=WARM_START, end=TEST_END), sha


def run_exp(exp: str, frames: dict[str, pd.DataFrame], out: pathlib.Path,
            symbols: list[str], bar_secs: int, dump_trades: bool = False) -> list[dict]:
    base = out / exp
    base.mkdir(parents=True, exist_ok=True)
    train_rows, test_rows = [], []
    pcols = param_cols(exp)

    for sym in symbols:
        df_full = frames[sym]
        tr = df_full[(df_full.index >= TRAIN_START) & (df_full.index <= TRAIN_END)]
        te = df_full[(df_full.index >= TEST_START) & (df_full.index <= TEST_END)]
        tr_a, te_a = atr(tr), atr(te)
        symdir = base / sym
        symdir.mkdir(exist_ok=True)

        rows = []
        for combo in combos_for(exp):
            sig = signals_for(exp, df_full, tr, combo)
            st, trades = simulate(tr, sig, tr_a, notional=BASE_NOTIONAL, bar_secs=bar_secs,
                                  exit_mode="dual", dual=dual_spec())
            r = {"symbol": sym}
            r.update(combo_row(exp, combo))
            r.update(stats_row(st, trades))
            rows.append(r)
        tdf = pd.DataFrame(rows)
        tdf.to_csv(symdir / "sweep_train.csv", index=False, encoding="utf-8-sig")

        cand = tdf[tdf["trades"] >= MIN_TRAIN_TRADES]
        if len(cand) == 0:
            trow = {"symbol": sym, "n_ties_train": 0,
                    "sel_status": f"بلا تركيبة غير متحللة (تدريب <{MIN_TRAIN_TRADES} صفقة)",
                    "train_net": np.nan, "train_trades": 0,
                    "test_net": 0.0, "test_trades": 0, "test_win_pct": 0.0, "test_pf": 0.0,
                    "gate": False}
            for k in pcols:
                trow[f"sel_{k}"] = np.nan
            pd.DataFrame([trow]).to_csv(symdir / "test_selected.csv", index=False, encoding="utf-8-sig")
            if dump_trades:
                pd.DataFrame(columns=TRADE_COLS).to_csv(symdir / "trades.csv", index=False,
                                                        encoding="utf-8-sig")
            train_rows.append(tdf)
            test_rows.append(pd.DataFrame([trow]))
            print(f"  {exp}/{sym}: بلا تركيبة غير متحللة (كل تركيبات التدريب <{MIN_TRAIN_TRADES} صفقة)",
                  flush=True)
            continue

        best_label = int(cand["net"].idxmax())
        best = cand.loc[best_label]
        n_ties = int((cand["net"] == best["net"]).sum())
        bcombo = {k: best[f"NOVA_{k.upper()}"] for k in EXPS[exp].SWEEP_PARAMS.keys()}

        sig_t = signals_for(exp, df_full, te, bcombo)
        st_t, trades_t = simulate(te, sig_t, te_a, notional=BASE_NOTIONAL, bar_secs=bar_secs,
                                  exit_mode="dual", dual=dual_spec())
        pf_t = pf_of(trades_t)
        trow = {"symbol": sym, "n_ties_train": n_ties, "sel_status": "ok",
                "train_net": best["net"], "train_trades": int(best["trades"]),
                "test_net": st_t["net"], "test_trades": st_t["trades"],
                "test_win_pct": st_t["win_pct"], "test_pf": pf_t,
                "gate": bool(st_t["net"] > 0 and pf_t >= GATE_PF and st_t["trades"] >= GATE_TRADES)}
        for k in pcols:
            trow[f"sel_{k}"] = best[k]
        pd.DataFrame([trow]).to_csv(symdir / "test_selected.csv", index=False, encoding="utf-8-sig")
        if dump_trades:
            pd.DataFrame(trade_rows(sym, exp, trades_t), columns=TRADE_COLS
                         ).to_csv(symdir / "trades.csv", index=False, encoding="utf-8-sig")
        train_rows.append(tdf)
        test_rows.append(pd.DataFrame([trow]))
        sel = "/".join(f"{k}={bcombo[k]}" for k in bcombo)
        print(f"  {exp}/{sym}: أفضل تدريب [{sel}] net={best['net']:.2f}$ ({int(best['trades'])} صفقة) → "
              f"اختبار net={st_t['net']:.2f}$ ({st_t['trades']} صفقة، PF={pf_t:.2f}, "
              f"فوز={st_t['win_pct']:.1f}%) بوابة={'✓' if trow['gate'] else '✗'}", flush=True)

    allt = pd.concat(train_rows, ignore_index=True)
    allt.to_csv(base / "all_symbols_train.csv", index=False, encoding="utf-8-sig")
    allte = pd.concat(test_rows, ignore_index=True)
    allte.to_csv(base / "all_symbols_test.csv", index=False, encoding="utf-8-sig")
    return allte.to_dict("records")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="L0019 — دفعة الجرد الثانية: خمس فرضيات دخول")
    ap.add_argument("--tf", choices=["5m", "1h", "4h", "all"], default="all")
    ap.add_argument("--archive", default=None)
    ap.add_argument("--symbols", default=None)
    ap.add_argument("--exps", default=None, help="قائمة فاصلة من أسماء الفرضيات (تطوير)")
    ap.add_argument("--trades", action="store_true")
    ap.add_argument("--skip-canary", action="store_true",
                    help="تطوير فقط: يتخطى بوابة الكاناري — محظور في أي تشغيل رسمي")
    return ap.parse_args(argv)


def main() -> int:
    args = parse_args()
    tfs = ["5m", "1h", "4h"] if args.tf == "all" else [args.tf]
    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else SYMBOLS
    exps = [e.strip() for e in args.exps.split(",")] if args.exps else list(EXPS)
    t0 = time.time()

    canary_net = "skipped (--skip-canary — تطوير، لا اعتماد)"
    if not args.skip_canary:
        can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                             capture_output=True, text=True)
        canary = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
        if canary.get("canary") != "ok":
            print("الكاناري فشل — إيقاف L0019 (بوابة سلامة).", file=sys.stderr)
            print(can.stdout); print(can.stderr, file=sys.stderr)
            return 1
        canary_net = canary["got"]["net"]
        print(f"الكاناري: PASS (net={canary_net} trades={canary['got']['trades']})", flush=True)
    else:
        print("تحذير: --skip-canary — خرج هذا التشغيل خارج أي اعتماد.", flush=True)

    frames = {tf: {} for tf in tfs}
    sha = {}
    for sym in symbols:
        df1m, sha[sym] = load_symbol(sym, args)
        for tf in tfs:
            frames[tf][sym] = to_5m(df1m) if tf == "5m" else to_bars(df1m, TF_MINUTES[tf])
        msg = f"{sym}: " + " | ".join(f"{len(frames[tf][sym]):,} شمعة {tf}" for tf in tfs)
        del df1m
        print(f"{msg} ({frames[tfs[0]][sym].index[0]} → {frames[tfs[0]][sym].index[-1]})", flush=True)

    for tf in tfs:
        out = HIST / "research" / "hyp_lab_out" / TF_OUT[tf]
        out.mkdir(parents=True, exist_ok=True)
        bar_secs = TF_MINUTES[tf] * 60
        verdicts = {}
        for exp in exps:
            print(f"[{exp} · {tf}] — {len(combos_for(exp))} تركيبة × {len(symbols)} رمز", flush=True)
            verdicts[exp] = run_exp(exp, frames[tf], out, symbols, bar_secs=bar_secs,
                                    dump_trades=args.trades)

        (out / "env_dump.txt").write_text(
            f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
            f"window: train={TRAIN_START}→{TRAIN_END} | test={TEST_START}→{TEST_END}\n"
            f"warm={WARM_START}\n"
            f"cost=0.13%/side | notional={BASE_NOTIONAL}$ | bar={tf} | canary={canary_net}\n"
            f"gate: net>0 AND pf>={GATE_PF} AND trades>={GATE_TRADES} | min_train_trades={MIN_TRAIN_TRADES}\n"
            f"exit=dual golden {dual_spec()}\n"
            f"archive={resolve_archive(args.archive)}\n"
            f"exps={','.join(exps)}\n"
            + "".join(f"sha256[:16] {k}={v}\n" for k, v in sha.items()), encoding="utf-8")

        lines = [f"# L0019 — دفعة الجرد الثانية — أفضل (اختبار) لكل رمز — شبكة {tf}",
                 f"# مدة التشغيل حتى هذا الفريم: {time.time()-t0:.1f} ث"]
        n_gate = 0
        for exp, rows in verdicts.items():
            df = pd.DataFrame(rows).sort_values("test_net", ascending=False)
            n_gate += int(df["gate"].sum())
            lines.append(f"## {exp} — عابرون: {int(df['gate'].sum())}/{len(df)}")
            for _, x in df.iterrows():
                lines.append(f"  {x['symbol']}: test_net={x['test_net']:.2f}$ trades={int(x['test_trades'])} "
                             f"win={x['test_win_pct']:.1f}% PF={x['test_pf']:.2f} "
                             f"gate={'نعم' if x['gate'] else 'لا'} | {x['sel_status']}")
        lines.append(f"# إجمالي العابرين على {tf}: {n_gate}")
        (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n" + "\n".join(lines), flush=True)
        print(f"فريم {tf} اكتمل → {out}", flush=True)

    print(f"الكل: {time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
