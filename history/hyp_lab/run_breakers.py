# -*- coding: utf-8 -*-
"""L0009 — إخضاع القواطع الاتجاهية كاملة (F‑213) على الأرشيف التاريخي (بروتوكول L0007 نفسه)

الأمر: القائد 2026-09-19 — «ملف القواطع يجرّب كل استراتيجياته + محادثة مستقلة على الأرشيف».
البروتوكول (منسوخ من run_v5 بلا تغيير في الحكم):
  - النوافذ: تدريب 2023-09-01→2024-12-31 | اختبار 2025-01-01→2026-08-31 (دفء من 2023-06-01)
  - الاختيار على التدريب فقط (من التركيبات غير المتحللة ≥100 صفقة)؛ الحكم على الاختبار فقط
  - بوابة القبول على الاختبار: net>0 AND PF≥1.3 AND trades≥100
  - التكاليف: 0.13% لكل طرف · قيمة اسمية 20$ (محفظة التجربة 1000$) · طرف طويل فقط (بديهي: لا بيع مكشوف)

الشبكة: 16 قاطعاً (14 منفرداً + ELITE8 + ALL14) × خروجان (std | dual بتركيبة L0007‑tf1h
الذهبية trig=0.0025/lock=0.0045 والثوابت من F‑197) = 32 تركيبة لكل رمز — صغيرة عمداً:
الغرض أحكام قاطعٍ قاطع لا صيد قمم حظ (الشبكات العريضة محكومة لاحقاً لكل عابر بمساره).

انحرافان موثقان عن run_v5 (لا يغيّران بروتوكول الحكم):
  1) مصفوفة المؤشرات تُحسب على الإطار المدفأ كاملاً ثم تُقص الإشارة للنافذة —
     مبرره: مؤشرات 200 شمعة (ema200/alma200) تخسر رأس التدريب لو حسبت على المقطع،
     والمحرك الحي يقرأ بتاريخ خلفه دائماً (run_v5 كان يقص أولاً لأن مؤشراته ≤50 شمعة).
  2) لا فريم 5m هنا أصلاً: قاعدة مضخة التكاليف في ملف القواطع (>~5 إشارات/شهر مرفوض على 5m)
     وحكم AUDIT‑L0007 أن كسر التعادل على 5m يحتاج فوز 68.4% — 1h أساس، 4h ثانٍ.

البيانات: crypto_archive/ (الأرشيف الرسمي). وضعان:
  --source disk   : يقرأ الملفات من القرص (--archive يجبر المسار، وإلا $NOVA_ARCHIVE،
                    وإلا أول موجود من: <root>/crypto_archive ثم <history>/crypto_archive).
  --source stream : يجلب كل {sym}_1m.parquet من raw.githubusercontent إلى الذاكرة فحسب
                    (صفر قرص — نمط canary --source stream نفسه) فتعمل المحادثة بلا تنزيل 732MB.
الكاناري (tools/canary.py --json) بوابة إلزامية قبل أي تشغيل؛ --skip-canary للتطوير فقط.

المخرجات (مطابقة شكل L0007 حرفاً): history/research/hyp_lab_out/L0009/ (1h) و
L0009-tf4h/ (4h)، تحت كل منهما: F_213/<sym>/{sweep_train.csv,test_selected.csv[,trades.csv]}
+ F_213/all_symbols_{train,test}.csv + env_dump.txt + summary.txt
حتمية: بلا عشوائية — نفس البيانات والإصدارات تعطي نفس الأرقام.
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

# إعداد البيئة قبل أي استيراد للمحرك (config.py يُنشئ DATA_DIR عند الاستيراد)
_SCRATCH = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_SCRATCH / "home"))

HIST = pathlib.Path(__file__).resolve().parents[1]            # history/
ROOT = pathlib.Path(__file__).resolve().parents[2]            # جذر المستودع
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import BASE_NOTIONAL, load, to_bars, TF_MINUTES, atr, simulate, trade_rows  # noqa: E402

import F_213_breakers as M213  # noqa: E402

EXPS = {"F_213": M213}

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XLMUSDT", "LINKUSDT", "GRAMUSDT", "RENDERUSDT", "FILUSDT"]
WARM_START = "2023-06-01"          # دفء المؤشرات قبل بداية التدريب (مؤشرات 200 شمعة)
TRAIN_START, TRAIN_END = "2023-09-01", "2024-12-31"
TEST_START, TEST_END = "2025-01-01", "2026-08-31"
GATE_PF, GATE_TRADES = 1.3, 100
RAW_BASE = "https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON"
TRADE_COLS = ["symbol", "exp", "entry_time", "exit_time", "entry", "exit",
              "notional", "pnl", "r_mult", "exit_side", "bars_held"]
TF_OUT = {"1h": "L0009", "4h": "L0009-tf4h"}


# ---------- الشبكة والإشارات ----------

def combos_for(exp: str) -> list[dict]:
    mod = EXPS[exp]
    return [{"exit": e, "trigger": t}
            for e in mod.EXITS for t in mod.SWEEP_PARAMS["trigger"]]


def param_cols(exp: str) -> list[str]:
    return ["NOVA_EXIT", "NOVA_TRIGGER"]


def combo_row(exp: str, combo: dict) -> dict:
    return {"NOVA_EXIT": combo["exit"], "NOVA_TRIGGER": combo["trigger"]}


def signals_for(exp: str, df_full: pd.DataFrame, window: pd.DataFrame, combo: dict) -> pd.Series:
    """إشارة على الإطار المدفأ كاملاً ثم تقص لنافذة التدريب/الاختبار (انحراف موثق 1)."""
    sig_full = EXPS[exp].make_signals(df_full, trigger=combo["trigger"])
    return sig_full.loc[window.index]


def sim_kwargs(exp: str, combo: dict) -> dict:
    if combo["exit"] == "dual":
        return {"exit_mode": "dual", "dual": EXPS[exp].make_dual_spec()}
    return {"exit_mode": "std"}


def pf_of(trades: list[dict]) -> float:
    g = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    lo = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    if lo > 0:
        return g / lo
    return float("inf") if g > 0 else 0.0


def stats_row(st: dict, trades: list[dict]) -> dict:
    return {"net": st["net"], "trades": st["trades"], "win_pct": st["win_pct"], "pf": pf_of(trades)}


# ---------- البيانات ----------

def resolve_archive(cli: str | None) -> pathlib.Path:
    if cli:
        p = pathlib.Path(cli).expanduser()
        return p
    env = os.environ.get("NOVA_ARCHIVE", "")
    if env:
        return pathlib.Path(env).expanduser()
    for cand in (ROOT / "crypto_archive", HIST / "crypto_archive"):
        if (cand / "BTCUSDT_1m.parquet").exists():
            return cand
    return ROOT / "crypto_archive"      # للرسالة الواضحة عند الغياب


def stream_symbol(sym: str, ref: str) -> pd.DataFrame:
    """جلب باركيه الرمز إلى الذاكرة (صفر قرص) — نمط canary --source stream."""
    url = f"{RAW_BASE}/{ref}/crypto_archive/{sym}_1m.parquet"
    req = urllib.request.Request(url, headers={"User-Agent": "nova-l0009-stream"})
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
    """ترجع (إطار الدقي المدفأ حتى نهاية الاختبار، بصمة قصيرة)."""
    if args.source == "stream":
        df, sha, nbytes = stream_symbol(sym, args.ref)
        df = df[(df.index >= pd.Timestamp(WARM_START, tz="UTC")) &
                (df.index < pd.Timestamp(TEST_END, tz="UTC"))]
        return df, f"stream:{sha}:{nbytes}"
    p = resolve_archive(args.archive) / f"{sym}_1m.parquet"
    if not p.exists():
        raise FileNotFoundError(f"لا يوجد {p} — جرّب --source stream أو --archive PATH")
    sha = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return load(str(p), start=WARM_START, end=TEST_END), sha


# ---------- الجولة ----------

def run_exp(exp: str, frames: dict[str, pd.DataFrame], out: pathlib.Path,
            symbols: list[str], bar_secs: int, dump_trades: bool = False) -> list[dict]:
    base = out / exp
    base.mkdir(parents=True, exist_ok=True)
    train_rows, test_rows = [], []
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
        bc = {k: best[k] for k in param_cols(exp)}
        bcombo = {"exit": str(bc["NOVA_EXIT"]), "trigger": str(bc["NOVA_TRIGGER"])}

        sig_t = signals_for(exp, df_full, te, bcombo)
        st_t, trades_t = simulate(te, sig_t, te_a, notional=BASE_NOTIONAL, bar_secs=bar_secs,
                                  **sim_kwargs(exp, bcombo))
        trow = {"symbol": sym, "n_ties_train": n_ties, "sel_status": "ok",
                "train_net": best["net"], "train_trades": int(best["trades"]),
                "test_net": st_t["net"], "test_trades": st_t["trades"],
                "test_win_pct": st_t["win_pct"], "test_pf": pf_of(trades_t),
                "gate": bool(st_t["net"] > 0 and pf_of(trades_t) >= GATE_PF
                             and st_t["trades"] >= GATE_TRADES)}
        for k in param_cols(exp):
            trow[f"sel_{k}"] = bc[k]
        tdf_t = pd.DataFrame([trow])
        tdf_t.to_csv(symdir / "test_selected.csv", index=False, encoding="utf-8-sig")
        if dump_trades:
            pd.DataFrame(trade_rows(sym, exp, trades_t), columns=TRADE_COLS
                         ).to_csv(symdir / "trades.csv", index=False, encoding="utf-8-sig")
        train_rows.append(tdf)
        test_rows.append(tdf_t)
        print(f"  {exp}/{sym}: تدريب {len(tr)} شمعة → اختبار {len(te)} شمعة | "
              f"أفضل تدريب [{bcombo['exit']}/{bcombo['trigger']}] net={best['net']:.2f}$ → "
              f"اختبار net={st_t['net']:.2f}$ ({st_t['trades']} صفقة، "
              f"PF={pf_of(trades_t):.2f}) gate={'✓' if trow['gate'] else '✗'}", flush=True)

    allt = pd.concat(train_rows, ignore_index=True)
    allt.to_csv(base / "all_symbols_train.csv", index=False, encoding="utf-8-sig")
    allt = pd.concat(test_rows, ignore_index=True)
    allt.to_csv(base / "all_symbols_test.csv", index=False, encoding="utf-8-sig")
    return allt.to_dict("records")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="L0009 — القواطع الاتجاهية كاملة (F‑213) على 1h/4h ببروتوكول L0007")
    ap.add_argument("--tf", choices=["1h", "4h", "both"], default="1h",
                    help="1h (افتراضي) | 4h | both (يعبئ الفريمين بتحميل واحد — الموفّر للبث)")
    ap.add_argument("--source", choices=["disk", "stream"], default="disk",
                    help="disk = crypto_archive من القرص | stream = جلب كل رمز إلى الذاكرة")
    ap.add_argument("--archive", default=None, help="مسار الأرشيف (disk) — يجبر التلقائي")
    ap.add_argument("--ref", default="main", help="git ref للبث (stream)")
    ap.add_argument("--symbols", default=None,
                    help="قائمة فاصلة من الرموز للتطوير (الافتراضي: الثمانية المعتمدة)")
    ap.add_argument("--trades", action="store_true",
                    help="يحفظ trades.csv للتركيبة المنتقاة على نافذة الاختبار")
    ap.add_argument("--skip-canary", action="store_true",
                    help="تطوير فقط: يتخطى بوابة الكاناري — محظور في أي تشغيل رسمي")
    return ap.parse_args(argv)


def main() -> int:
    args = parse_args()
    tfs = ["1h", "4h"] if args.tf == "both" else [args.tf]
    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else SYMBOLS
    t0 = time.time()

    # 0) الكاناري إلزامي (بوابة سلامة) — إلا بعلم التطوير الصريح
    canary_net = "skipped (--skip-canary — تطوير، لا اعتماد)"
    if not args.skip_canary:
        import subprocess
        cmd = [sys.executable, str(ROOT / "tools" / "canary.py"), "--json"]
        if args.source == "stream":
            cmd += ["--source", "stream"]
        can = subprocess.run(cmd, capture_output=True, text=True)
        canary = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
        if canary.get("canary") != "ok":
            print("الكاناري فشل — إيقاف L0009 (بوابة سلامة).", file=sys.stderr)
            print(can.stdout)
            print(can.stderr, file=sys.stderr)
            return 1
        canary_net = canary["got"]["net"]
        print(f"الكاناري: PASS (net={canary_net} trades={canary['got']['trades']})", flush=True)
    else:
        print("تحذير: --skip-canary — خرج هذا التشغيل خارج أي اعتماد.", flush=True)

    # 1) تحميل مرة واحدة لكل رمز + تعبئة كل الفريمات المطلوبة منه
    frames = {tf: {} for tf in tfs}
    sha = {}
    for sym in symbols:
        df1m, sha[sym] = load_symbol(sym, args)
        for tf in tfs:
            frames[tf][sym] = to_bars(df1m, TF_MINUTES[tf])
        msg = f"{sym}: " + " | ".join(f"{len(frames[tf][sym]):,} شمعة {tf}" for tf in tfs)
        del df1m
        print(f"{msg} ({frames[tfs[0]][sym].index[0]} → {frames[tfs[0]][sym].index[-1]})",
              flush=True)

    # 2) الجولات — لكل فريم مجلد إخراج مستقل (لا يُلمس مرجع L0007 أبداً)
    for tf in tfs:
        out = HIST / "research" / "hyp_lab_out" / TF_OUT[tf]
        out.mkdir(parents=True, exist_ok=True)
        bar_secs = TF_MINUTES[tf] * 60
        verdicts = {}
        for exp in EXPS:
            print(f"[{exp} · {tf}]", flush=True)
            verdicts[exp] = run_exp(exp, frames[tf], out, symbols, bar_secs=bar_secs,
                                    dump_trades=args.trades)

        # 3) env dump + summary (إلزام D‑0013)
        import platform
        arch = ("stream:" + args.ref) if args.source == "stream" else str(resolve_archive(args.archive))
        (out / "env_dump.txt").write_text(
            f"python={platform.python_version()}\n"
            f"pandas={pd.__version__}\nnumpy={np.__version__}\n"
            f"window: train={TRAIN_START}→{TRAIN_END} | test={TEST_START}→{TEST_END}\n"
            f"cost=0.13%/side | notional=20$ | bar={tf} | canary={canary_net}\n"
            f"source={args.source} | archive={arch}\n"
            f"dual_spec={M213.make_dual_spec()}\n"
            + "".join(f"sha256[:16] {k}={v}\n" for k, v in sha.items()), encoding="utf-8")
        title = f"# L0009 — القواطع الاتجاهية (F_213) — أفضل (اختبار) لكل رمز — شبكة {tf}"
        lines = [title, f"# مدة التشغيل حتى هذا الفريم: {time.time()-t0:.1f} ث"]
        for exp, rows in verdicts.items():
            df = pd.DataFrame(rows).sort_values("test_net", ascending=False)
            for _, x in df.head(8).iterrows():
                lines.append(
                    f"  {exp} {x['symbol']}: test_net={x['test_net']:.2f}$ "
                    f"trades={int(x['test_trades'])} win={x['test_win_pct']:.1f}% "
                    f"PF={x['test_pf']:.2f} gate={'نعم' if x['gate'] else 'لا'} "
                    f"| sel={x['sel_NOVA_EXIT']}/{x['sel_NOVA_TRIGGER']} "
                    f"| train_net={x['train_net']:.2f}$ | {x['sel_status']}")
        (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n" + "\n".join(lines), flush=True)
        print(f"فريم {tf} اكتمل → {out}", flush=True)

    print(f"الكل: {time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
