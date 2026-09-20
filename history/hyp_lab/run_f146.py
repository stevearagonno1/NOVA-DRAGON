# -*- coding: utf-8 -*-
"""L0016 — آلة الحالات F-146 على 5 سنوات وثلاثة فريمات (بروتوكول L0007 حرفياً)

العقد: docs/lanes/L0016-state-machine-f146.md
  - شبكة 27: eps × fvg_min × mss_window
  - شراء فقط · خروج F-197 dual المقاس (trig=0.0025 / lock=0.0045)
  - نوافذ: تدريب 2023-09-01→2024-12-31 | اختبار 2025-01-01→2026-08-31 | دفء 2023-06-01
  - اختيار على التدريب فقط من غير المتحلل (≥100 صفقة) · الحكم على الاختبار
  - بوابة: net>0 AND PF≥1.3 AND trades≥100
  - تكلفة 0.13%/طرف · 1000$/صفقة
  - المخرجات: history/research/hyp_lab_out/L0016{,-tf1h,-tf4h}/
  - لا مساس nova_v8/** ولا ملفات المختبر المرجعية ولا مخرجات L0007
"""
from __future__ import annotations

import argparse
import hashlib
import io
import itertools
import json
import os
import pathlib
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

_SCRATCH = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_SCRATCH / "home"))

HIST = pathlib.Path(__file__).resolve().parents[1]
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import load, to_5m, to_bars, TF_MINUTES, atr, simulate, trade_rows  # noqa: E402

import F_146_state_machine as M146  # noqa: E402

EXPS = {"F_146": M146}
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XLMUSDT", "LINKUSDT", "GRAMUSDT", "RENDERUSDT", "FILUSDT"]
WARM_START = "2023-06-01"
TRAIN_START, TRAIN_END = "2023-09-01", "2024-12-31"
TEST_START, TEST_END = "2025-01-01", "2026-08-31"
GATE_PF, GATE_TRADES = 1.3, 100
RAW_BASE = "https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON"
TRADE_COLS = ["symbol", "exp", "entry_time", "exit_time", "entry", "exit",
              "notional", "pnl", "r_mult", "exit_side", "bars_held"]
TF_OUT = {"5m": "L0016", "1h": "L0016-tf1h", "4h": "L0016-tf4h"}


def combos_for(_exp: str) -> list[dict]:
    names = list(M146.SWEEP_PARAMS)
    vals = [M146.SWEEP_PARAMS[n] for n in names]
    return [dict(zip(names, v)) for v in itertools.product(*vals)]


def param_cols(_exp: str) -> list[str]:
    return ["NOVA_EPS", "NOVA_FVG_MIN", "NOVA_MSS_WINDOW"]


def combo_row(_exp: str, combo: dict) -> dict:
    return {
        "NOVA_EPS": combo["eps"],
        "NOVA_FVG_MIN": combo["fvg_min"],
        "NOVA_MSS_WINDOW": combo["mss_window"],
    }


def signals_for(_exp: str, df_full: pd.DataFrame, window: pd.DataFrame, combo: dict) -> pd.Series:
    sig_full = M146.make_signals(df_full, **combo)
    return sig_full.loc[window.index]


def sim_kwargs(_exp: str, _combo: dict) -> dict:
    return {"exit_mode": "dual", "dual": M146.make_dual_spec()}


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


def stream_symbol(sym: str, ref: str):
    url = f"{RAW_BASE}/{ref}/crypto_archive/{sym}_1m.parquet"
    req = urllib.request.Request(url, headers={"User-Agent": "nova-l0016-stream"})
    with urllib.request.urlopen(req, timeout=600) as r:
        blob = r.read()
    sha = hashlib.sha256(blob).hexdigest()[:16]
    raw = pd.read_parquet(io.BytesIO(blob))
    v = int(raw["open_time"].iloc[0])
    unit = "ms" if abs(v) < 10**14 else "us"
    ts = pd.to_datetime(raw["open_time"], unit=unit, utc=True)
    df = raw[["open", "high", "low", "close", "volume"]].astype(float).copy()
    df.index = ts
    df = df[~df.index.duplicated(keep="first")].sort_index().dropna()
    return df, sha, len(blob)


def load_symbol(sym: str, args) -> tuple[pd.DataFrame, str]:
    if args.source == "stream":
        df, sha, nbytes = stream_symbol(sym, args.ref)
        df = df[(df.index >= pd.Timestamp(WARM_START, tz="UTC"))
                & (df.index < pd.Timestamp(TEST_END, tz="UTC"))]
        return df, f"stream:{sha}:{nbytes}"
    p = resolve_archive(args.archive) / f"{sym}_1m.parquet"
    if not p.exists():
        raise FileNotFoundError(f"لا يوجد {p} — جرّب --source stream أو --archive PATH")
    sha = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return load(str(p), start=WARM_START, end=TEST_END), sha


def run_exp(exp: str, frames: dict[str, pd.DataFrame], out: pathlib.Path,
            symbols: list[str], bar_secs: int, dump_trades: bool = False) -> list[dict]:
    base = out / exp
    base.mkdir(parents=True, exist_ok=True)
    train_rows, test_rows = [], []
    for sym in symbols:
        df_full = frames[sym]
        tr = df_full[(df_full.index >= TRAIN_START) & (df_full.index <= TRAIN_END)]
        te = df_full[(df_full.index >= TEST_START) & (df_full.index <= TEST_END)]
        if len(tr) < 50 or len(te) < 50:
            trow = {"symbol": sym, "n_ties_train": 0,
                    "sel_status": "تغطية غير كافية (غير مقاسة بنيوياً)",
                    "train_net": np.nan, "train_trades": 0,
                    "test_net": 0.0, "test_trades": 0, "test_win_pct": 0.0, "test_pf": 0.0,
                    "gate": False}
            for k in param_cols(exp):
                trow[f"sel_{k}"] = np.nan
            empty = pd.DataFrame([{**{"symbol": sym, "net": 0.0, "trades": 0,
                                      "win_pct": 0.0, "pf": 0.0}, **combo_row(exp, c)}
                                  for c in combos_for(exp)])
            symdir = base / sym
            symdir.mkdir(exist_ok=True)
            empty.to_csv(symdir / "sweep_train.csv", index=False, encoding="utf-8-sig")
            pd.DataFrame([trow]).to_csv(symdir / "test_selected.csv", index=False, encoding="utf-8-sig")
            train_rows.append(empty)
            test_rows.append(pd.DataFrame([trow]))
            print(f"  {exp}/{sym}: تغطية غير كافية — غير مقاسة بنيوياً", flush=True)
            continue
        tr_a, te_a = atr(tr), atr(te)
        symdir = base / sym
        symdir.mkdir(exist_ok=True)

        rows = []
        for combo in combos_for(exp):
            sig = signals_for(exp, df_full, tr, combo)
            st, trades = simulate(tr, sig, tr_a, notional=1000, bar_secs=bar_secs,
                                  **sim_kwargs(exp, combo))
            r = {"symbol": sym}
            r.update(combo_row(exp, combo))
            r.update(stats_row(st, trades))
            rows.append(r)
        tdf = pd.DataFrame(rows)
        tdf.to_csv(symdir / "sweep_train.csv", index=False, encoding="utf-8-sig")

        cand = tdf[tdf["trades"] >= GATE_TRADES]
        if len(cand) == 0:
            trow = {"symbol": sym, "n_ties_train": 0,
                    "sel_status": "بلا تركيبة غير متحللة (تدريب <100 صفقة)",
                    "train_net": np.nan, "train_trades": 0,
                    "test_net": 0.0, "test_trades": 0, "test_win_pct": 0.0, "test_pf": 0.0,
                    "gate": False}
            for k in param_cols(exp):
                trow[f"sel_{k}"] = np.nan
            pd.DataFrame([trow]).to_csv(symdir / "test_selected.csv", index=False,
                                        encoding="utf-8-sig")
            if dump_trades:
                pd.DataFrame(columns=TRADE_COLS).to_csv(symdir / "trades.csv", index=False,
                                                        encoding="utf-8-sig")
            train_rows.append(tdf)
            test_rows.append(pd.DataFrame([trow]))
            print(f"  {exp}/{sym}: بلا تركيبة غير متحللة (كل تركيبات التدريب <100 صفقة)",
                  flush=True)
            continue

        best_label = int(cand["net"].idxmax())
        best = cand.loc[best_label]
        n_ties = int((cand["net"] == best["net"]).sum())
        bcombo = {
            "eps": float(best["NOVA_EPS"]),
            "fvg_min": float(best["NOVA_FVG_MIN"]),
            "mss_window": int(best["NOVA_MSS_WINDOW"]),
        }
        sig_t = signals_for(exp, df_full, te, bcombo)
        st_t, trades_t = simulate(te, sig_t, te_a, notional=1000, bar_secs=bar_secs,
                                  **sim_kwargs(exp, bcombo))
        trow = {"symbol": sym, "n_ties_train": n_ties, "sel_status": "ok",
                "train_net": best["net"], "train_trades": int(best["trades"]),
                "test_net": st_t["net"], "test_trades": st_t["trades"],
                "test_win_pct": st_t["win_pct"], "test_pf": pf_of(trades_t),
                "gate": bool(st_t["net"] > 0 and pf_of(trades_t) >= GATE_PF
                             and st_t["trades"] >= GATE_TRADES)}
        trow["sel_NOVA_EPS"] = bcombo["eps"]
        trow["sel_NOVA_FVG_MIN"] = bcombo["fvg_min"]
        trow["sel_NOVA_MSS_WINDOW"] = bcombo["mss_window"]
        tdf_t = pd.DataFrame([trow])
        tdf_t.to_csv(symdir / "test_selected.csv", index=False, encoding="utf-8-sig")
        if dump_trades:
            pd.DataFrame(trade_rows(sym, exp, trades_t), columns=TRADE_COLS
                         ).to_csv(symdir / "trades.csv", index=False, encoding="utf-8-sig")
        train_rows.append(tdf)
        test_rows.append(tdf_t)
        print(f"  {exp}/{sym}: تدريب {len(tr)} شمعة → اختبار {len(te)} شمعة | "
              f"أفضل تدريب eps={bcombo['eps']}/fvg={bcombo['fvg_min']}/w={bcombo['mss_window']} "
              f"net={best['net']:.2f}$ → اختبار net={st_t['net']:.2f}$ "
              f"({st_t['trades']} صفقة، PF={pf_of(trades_t):.2f}) "
              f"gate={'✓' if trow['gate'] else '✗'}", flush=True)

    allt = pd.concat(train_rows, ignore_index=True)
    allt.to_csv(base / "all_symbols_train.csv", index=False, encoding="utf-8-sig")
    allt = pd.concat(test_rows, ignore_index=True)
    allt.to_csv(base / "all_symbols_test.csv", index=False, encoding="utf-8-sig")
    return allt.to_dict("records")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="L0016 — F-146 state machine 5m/1h/4h")
    ap.add_argument("--tf", choices=["5m", "1h", "4h", "all"], default="all")
    ap.add_argument("--source", choices=["disk", "stream"], default="disk")
    ap.add_argument("--archive", default=None)
    ap.add_argument("--ref", default="main")
    ap.add_argument("--symbols", default=None)
    ap.add_argument("--trades", action="store_true")
    ap.add_argument("--skip-canary", action="store_true")
    return ap.parse_args(argv)


def main() -> int:
    args = parse_args()
    tfs = ["5m", "1h", "4h"] if args.tf == "all" else [args.tf]
    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else SYMBOLS
    t0 = time.time()

    canary_net = "skipped (--skip-canary — تطوير، لا اعتماد)"
    if not args.skip_canary:
        import subprocess
        cmd = [sys.executable, str(ROOT / "tools" / "canary.py"), "--json"]
        if args.source == "stream":
            cmd += ["--source", "stream"]
        can = subprocess.run(cmd, capture_output=True, text=True)
        try:
            canary = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
        except (ValueError, json.JSONDecodeError):
            canary = {}
        if canary.get("canary") != "ok":
            print("الكاناري فشل — إيقاف L0016 (بوابة سلامة).", file=sys.stderr)
            print(can.stdout)
            print(can.stderr, file=sys.stderr)
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
            minutes = TF_MINUTES[tf]
            frames[tf][sym] = to_5m(df1m) if minutes == 5 else to_bars(df1m, minutes)
        msg = f"{sym}: " + " | ".join(f"{len(frames[tf][sym]):,} شمعة {tf}" for tf in tfs)
        del df1m
        print(f"{msg} ({frames[tfs[0]][sym].index[0]} → {frames[tfs[0]][sym].index[-1]})",
              flush=True)

    for tf in tfs:
        out = HIST / "research" / "hyp_lab_out" / TF_OUT[tf]
        out.mkdir(parents=True, exist_ok=True)
        bar_secs = TF_MINUTES[tf] * 60
        print(f"[F_146 · {tf}]", flush=True)
        verdicts = {"F_146": run_exp("F_146", frames[tf], out, symbols, bar_secs=bar_secs,
                                     dump_trades=args.trades)}

        import platform
        arch = ("stream:" + args.ref) if args.source == "stream" else str(resolve_archive(args.archive))
        (out / "env_dump.txt").write_text(
            f"python={platform.python_version()}\n"
            f"pandas={pd.__version__}\nnumpy={np.__version__}\n"
            f"window: train={TRAIN_START}→{TRAIN_END} | test={TEST_START}→{TEST_END}\n"
            f"cost=0.13%/side | notional=1000$ | bar={tf} | canary={canary_net}\n"
            f"source={args.source} | archive={arch}\n"
            f"dual_spec={M146.make_dual_spec()}\n"
            f"ssl_lookback={M146.SSL_LOOKBACK} | mss_disp_atr={M146.MSS_DISP_ATR} | "
            f"flow_min={M146.FLOW_MIN} | flow=up_volume_share_proxy\n"
            + "".join(f"sha256[:16] {k}={v}\n" for k, v in sha.items()), encoding="utf-8")
        title = f"# L0016 — آلة الحالات F_146 — أفضل (اختبار) لكل رمز — شبكة {tf}"
        lines = [title, f"# مدة التشغيل حتى هذا الفريم: {time.time()-t0:.1f} ث"]
        n_gate = 0
        for exp, rows in verdicts.items():
            dfv = pd.DataFrame(rows).sort_values("test_net", ascending=False)
            n_gate = int(dfv["gate"].sum()) if "gate" in dfv.columns else 0
            for _, x in dfv.iterrows():
                lines.append(
                    f"  {exp} {x['symbol']}: test_net={x['test_net']:.2f}$ "
                    f"trades={int(x['test_trades'])} win={x['test_win_pct']:.1f}% "
                    f"PF={x['test_pf']:.2f} gate={'نعم' if x['gate'] else 'لا'} "
                    f"| sel=eps{x.get('sel_NOVA_EPS')}/fvg{x.get('sel_NOVA_FVG_MIN')}/w{x.get('sel_NOVA_MSS_WINDOW')} "
                    f"| train_net={x['train_net']:.2f}$ | {x['sel_status']}")
            lines.append(f"  عبور البوابة: {n_gate}/{len(dfv)}")
        (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n" + "\n".join(lines), flush=True)
        print(f"فريم {tf} اكتمل → {out}", flush=True)

    print(f"الكل: {time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
