# -*- coding: utf-8 -*-
"""L0010 — جولة الضغط على عابري L0009 (F‑213) بأمر القائد 2026-09-19.

لا اختيار ولا تحسين هنا بتاتاً: هذا السائق يقرأ التركيبات المقفلة من إيداع L0009
(history/research/hyp_lab_out/L0009{,-tf4h}/F_213/all_symbols_test.csv — يصل المستودع مع فرع
التوثيق مدموجاً، لذا ترتيب الدمج ملزم: التوثيق أولاً) ثم يعذّبها بخمسة محاور:

  matrix  : تقييم المصفوفة الـ32 كاملة على نافذة الاختبار (لا المختارة وحدها) — يفصل
            القاطع الفائز فعلاً من هيمنة المركب البنيوية (اتحاد ⊇ كل منفرد).
  slip    : انزلاق مجهد: 0.10% ثم 0.30% لكل طرف بدل الأساس 0.03% (العمولة 0.10% ثابتة)
            ⇒ الكلفة/طرف: 0.20% و0.40%. متوسط الربح المقاس 1.64%/صفقة — الحكم قد ينقلب هنا.
  blind   : النافذة العمياء 2021-09-01→2023-08-31 (دفء 2021-06-01) بتركيبة L0009 نفسها مقفلة
            + المصفوفة كاملة معلوماتياً. GRAM/RENDER: بلا نافذة (بداية بياناتهما 2024) — توثق لا تُخفى.
  plateau : الجوار ±20%: للمزدوج (تسليح، قفل) ×{0.8,1,1.2}² حول (0.0025, 0.0045)؛
            للقياسي (وقف، هدف)×ATR ×{0.8,1,1.2}² حول (2.0, 4.0) — كلها على الاختبار.
  ablate  : تفكيك ALL14: حذف كل قاطع مرة (14 تشغيلاً) على الخلايا المقفلة بالمركب —
            أي قاطع يسقط الصافي عند حذفه هو من يحمل الربح.

الضوابط: نفس آلة المحاكاة وثوابت L0009 حرفاً (إعادة استعمال بلا نسخ من run_breakers)،
الكاناري بوابة إلزامية، الكلفة تُبدّل عبر common.COST_PER_SIDE مؤقتاً داخل العملية فحسب
(الكاناري عملية منفصلة فلا يتأثر)، وكل مخرج تحت history/research/hyp_lab_out/L0010/.
ملاحظة شكل: مخرجات هذه الجولة جداول تحليل لا شبكات L0007 — audit_lane غير منطبق هنا،
والتثبت الرسمي = إعادة اشتقاق العقل (كما جرى لـ L0009) موثقاً في ملف المسار.
"""
from __future__ import annotations

import argparse
import hashlib
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

HERE = pathlib.Path(__file__).resolve().parent
HIST = HERE.parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import common  # noqa: E402
from common import BASE_NOTIONAL, to_bars, TF_MINUTES, atr, simulate, trade_rows  # noqa: E402
import run_breakers as RB  # noqa: E402  (إعادة استعمال: البث/الأرشيف/الشبكة/الإشارات)
import F_213_breakers as M213  # noqa: E402

SYMBOLS = RB.SYMBOLS
TEST_START, TEST_END = RB.TEST_START, RB.TEST_END
WARM_STD = RB.WARM_START                       # 2023-06-01 — نفس دفء L0009 (تطابق بايتي)
BLIND_WARM, BLIND_START, BLIND_END = "2021-06-01", "2021-09-01", "2023-08-31"
BASE_SLIP = common.SLIP_PER_SIDE               # 0.0003 — الأساس الموثق
SLIP_TIERS = (0.0010, 0.0030)                  # مجهدة لكل طرف (بدل الأساس)
NEIGH = (0.8, 1.0, 1.2)                        # الجوار ±20%
DUAL_TRIG, DUAL_LOCK = M213.DUAL_TRIG, M213.DUAL_LOCK
OUT_ROOT = HIST / "research" / "hyp_lab_out" / "L0010"


# ---------- البيانات (إعادة استعمال أنبوب L0009) ----------

def load_frames(args, warm: str, end: str, symbols: list[str], tfs: list[str]):
    """يحمل الدقي مرة واحدة لكل رمز في النافذة المطلوبة ويشتق الفريمين."""
    frames = {tf: {} for tf in tfs}
    sha = {}
    for sym in symbols:
        if args.source == "stream":
            df1m, s, nb = RB.stream_symbol(sym, args.ref)
            df1m = df1m[(df1m.index >= pd.Timestamp(warm, tz="UTC")) &
                        (df1m.index < pd.Timestamp(end, tz="UTC"))]
            sha[sym] = f"stream:{s}:{nb}"
        else:
            p = RB.resolve_archive(args.archive) / f"{sym}_1m.parquet"
            if not p.exists():
                raise FileNotFoundError(f"لا يوجد {p}")
            sha[sym] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            df1m = common.load(str(p), start=warm, end=end)
        for tf in tfs:
            frames[tf][sym] = to_bars(df1m, TF_MINUTES[tf]) if len(df1m) else df1m
        n0 = len(frames[tfs[0]][sym])
        print(f"  {sym}: مدفأة {warm}→{end} ({n0:,} شمعة {tfs[0]})" if n0 else
              f"  {sym}: مدفأة {warm}→{end} — فارغة", flush=True)
        del df1m
    return frames, sha


def sig_on_window(df_full: pd.DataFrame, window: pd.DataFrame, trigger: str) -> pd.Series:
    return M213.make_signals(df_full, trigger=trigger).loc[window.index]


def sig_ablate(df_full: pd.DataFrame, window: pd.DataFrame, drop: str) -> pd.Series:
    """اتحاد حواف كل القواطع عدا المحذوف — إعادة استعمال داخلية موثقة من وحدة المختبر."""
    longs = M213._long_triggers(df_full)
    sig = None
    for n in M213._trg.PRIORITY:
        if n == drop:
            continue
        e = M213._edge(longs[n])
        sig = e if sig is None else (sig | e)
    return sig.fillna(False).loc[window.index]


def sim_eval(window: pd.DataFrame, sig: pd.Series, combo: dict, bar_secs: int,
             slip: float | None = None, stop: float | None = None, tp: float | None = None,
             dual_spec: dict | None = None):
    """محاكاة واحدة مع ردّ ثوابت الكلفة/الوقف بعدها — صفر تسريب بين التشغيلات."""
    base_cost, base_stop, base_tp = common.COST_PER_SIDE, common.STOP_ATR, common.TP_ATR
    try:
        if slip is not None:
            common.COST_PER_SIDE = common.FEE_PER_SIDE + slip
        if stop is not None:
            common.STOP_ATR, common.TP_ATR = stop, tp
        kwargs = RB.sim_kwargs("F_213", combo)
        if dual_spec is not None:
            kwargs = {"exit_mode": "dual", "dual": dual_spec}
        return simulate(window, sig, atr(window), notional=BASE_NOTIONAL, bar_secs=bar_secs, **kwargs)
    finally:
        common.COST_PER_SIDE, common.STOP_ATR, common.TP_ATR = base_cost, base_stop, base_tp


def canary_gate(args) -> str:
    if args.skip_canary:
        print("تحذير: --skip-canary — تطوير فقط.", flush=True)
        return "skipped"
    cmd = [sys.executable, str(ROOT / "tools" / "canary.py"), "--json"]
    if args.source == "stream":
        cmd += ["--source", "stream"]
    can = subprocess.run(cmd, capture_output=True, text=True)
    res = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if res.get("canary") != "ok":
        print("الكاناري فشل — إيقاف L0010 (بوابة سلامة).", file=sys.stderr)
        sys.exit(1)
    net = res["got"]["net"]
    print(f"الكاناري: PASS (net={net} trades={res['got']['trades']})", flush=True)
    return net


def read_locked(tf_dir: pathlib.Path, symbols: list[str]) -> dict[str, dict]:
    """التركيبات المقفلة من إيداع L0009 — بلا إعادة اختيار أبداً."""
    sel_file = tf_dir / "F_213" / "all_symbols_test.csv"
    if not sel_file.exists():
        raise FileNotFoundError(
            f"مختارات L0009 غير مودعة: {sel_file} — ادمج فرع التوثيق أولاً (الترتيب ملزم)")
    df = pd.read_csv(sel_file, encoding="utf-8-sig")
    locked = {}
    for sym in symbols:
        row = df[df.symbol == sym]
        if row.empty or str(row.iloc[0].sel_status) != "ok":
            continue
        r = row.iloc[0]
        locked[sym] = {"exit": str(r.sel_NOVA_EXIT), "trigger": str(r.sel_NOVA_TRIGGER),
                       "base_net": float(r.test_net), "base_trades": int(r.test_trades),
                       "gate": bool(r.gate)}
    return locked


def write_csv(rows: list[dict], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


# ---------- المحاور الخمسة ----------

def run_tf(tf: str, frames: dict, locked: dict[str, dict], symbols: list[str],
           blind_frames: dict | None, modes: set[str], args, summary: list[str],
           dump_trades: bool) -> None:
    bar_secs = TF_MINUTES[tf] * 60
    out = OUT_ROOT / tf / "F_213"

    # 1) matrix — الـ32 على نافذة الاختبار كاملة
    if "matrix" in modes:
        for sym in symbols:
            df_full = frames[tf][sym]
            if len(df_full) == 0:
                continue
            te = df_full[(df_full.index >= TEST_START) & (df_full.index <= TEST_END)]
            rows = []
            for combo in RB.combos_for("F_213"):
                sig = sig_on_window(df_full, te, combo["trigger"])
                st, tr = sim_eval(te, sig, combo, bar_secs)
                rows.append({"symbol": sym, "NOVA_EXIT": combo["exit"],
                             "NOVA_TRIGGER": combo["trigger"], "test_net": st["net"],
                             "trades": st["trades"], "win_pct": st["win_pct"],
                             "pf": RB.pf_of(tr)})
            write_csv(rows, out / sym / "test_matrix.csv")
            n_pos = sum(1 for r in rows if r["test_net"] > 0)
            best = max(rows, key=lambda r: r["test_net"])
            print(f"[matrix {tf} {sym}] موجب {n_pos}/32 | الأعلى {best['NOVA_EXIT']}/{best['NOVA_TRIGGER']} {best['test_net']:.2f}$", flush=True)
            summary.append(f"matrix {tf} {sym}: positive={n_pos}/32 top={best['NOVA_EXIT']}/{best['NOVA_TRIGGER']} net={best['test_net']:.2f}$")

    # 2) slip — انزلاق مجهد على المقفلة
    if "slip" in modes:
        for sym, lk in locked.items():
            df_full = frames[tf][sym]
            if len(df_full) == 0:
                continue
            te = df_full[(df_full.index >= TEST_START) & (df_full.index <= TEST_END)]
            combo = {"exit": lk["exit"], "trigger": lk["trigger"]}
            sig = sig_on_window(df_full, te, combo["trigger"])
            rows = []
            for slip in (BASE_SLIP,) + SLIP_TIERS:
                st, tr = sim_eval(te, sig, combo, bar_secs, slip=slip)
                rows.append({"symbol": sym, "exit": lk["exit"], "trigger": lk["trigger"],
                             "slip_per_side": slip, "cost_per_side": common.FEE_PER_SIDE + slip,
                             "net": st["net"], "trades": st["trades"], "win_pct": st["win_pct"],
                             "pf": RB.pf_of(tr), "delta_vs_base": st["net"] - lk["base_net"]})
            write_csv(rows, out / sym / "slip_tiers.csv")
            if dump_trades:
                stx, trx = sim_eval(te, sig, combo, bar_secs, slip=SLIP_TIERS[-1])
                write_csv(trade_rows(sym, "F_213_slip", trx), out / sym / "slip_trades.csv")
            state = " · ".join(f"انزلاق {r['slip_per_side']:.3%}: {r['net']:.2f}$" for r in rows)
            print(f"[slip {tf} {sym}] {state}", flush=True)
            summary.append(f"slip {tf} {sym} [{lk['exit']}/{lk['trigger']}]: {state}")

    # 3) blind — النافذة العمياء بتركيبة مقفلة + المصفوفة
    if "blind" in modes and blind_frames is not None:
        for sym in symbols:
            df_full = blind_frames[tf][sym]
            symdir = out / sym
            if len(df_full) == 0:
                write_csv([{"symbol": sym, "status": "بلا نافذة عمياء — بداية البيانات 2024",
                            "blind_net": 0.0, "trades": 0, "pf": 0.0}], symdir / "blind_selected.csv")
                write_csv([{"symbol": sym, "status": "بلا نافذة عمياء — بداية البيانات 2024"}],
                          symdir / "blind_matrix.csv")
                print(f"[blind {tf} {sym}] بلا نافذة عمياء (بداية البيانات 2024) — موثق", flush=True)
                summary.append(f"blind {tf} {sym}: no blind window (data starts 2024)")
                continue
            bl = df_full[(df_full.index >= BLIND_START) & (df_full.index <= BLIND_END)]
            if sym in locked:
                combo = {"exit": locked[sym]["exit"], "trigger": locked[sym]["trigger"]}
                sig = sig_on_window(df_full, bl, combo["trigger"])
                st, tr = sim_eval(bl, sig, combo, bar_secs)
                write_csv([{"symbol": sym, "exit": combo["exit"], "trigger": combo["trigger"],
                            "status": "ok", "blind_net": st["net"], "trades": st["trades"],
                            "win_pct": st["win_pct"], "pf": RB.pf_of(tr)}], symdir / "blind_selected.csv")
                if dump_trades:
                    write_csv(trade_rows(sym, "F_213_blind", tr), symdir / "blind_trades.csv")
                print(f"[blind {tf} {sym}] {combo['exit']}/{combo['trigger']}: {st['net']:.2f}$ ({st['trades']} صفقة)", flush=True)
                summary.append(f"blind {tf} {sym} [{combo['exit']}/{combo['trigger']}]: net={st['net']:.2f}$ trades={st['trades']} pf={RB.pf_of(tr):.2f}")
            rows = []
            for combo in RB.combos_for("F_213"):
                sig = sig_on_window(df_full, bl, combo["trigger"])
                st, tr = sim_eval(bl, sig, combo, bar_secs)
                rows.append({"symbol": sym, "NOVA_EXIT": combo["exit"],
                             "NOVA_TRIGGER": combo["trigger"], "blind_net": st["net"],
                             "trades": st["trades"], "win_pct": st["win_pct"],
                             "pf": RB.pf_of(tr)})
            write_csv(rows, symdir / "blind_matrix.csv")

    # 4) plateau — الجوار ±20% على الاختبار
    if "plateau" in modes:
        for sym, lk in locked.items():
            df_full = frames[tf][sym]
            if len(df_full) == 0:
                continue
            te = df_full[(df_full.index >= TEST_START) & (df_full.index <= TEST_END)]
            sig = sig_on_window(df_full, te, lk["trigger"])
            rows = []
            if lk["exit"] == "dual":
                for k1 in NEIGH:
                    for k2 in NEIGH:
                        spec = M213.M197.make_dual_spec(trig=DUAL_TRIG * k1, lock=DUAL_LOCK * k2)
                        st, tr = sim_eval(te, sig, lk, bar_secs, dual_spec=spec)
                        rows.append({"symbol": sym, "trigger": lk["trigger"],
                                     "trig": spec["trig"], "lock": spec["lock"],
                                     "net": st["net"], "trades": st["trades"], "pf": RB.pf_of(tr),
                                     "ratio_vs_base": (st["net"] / lk["base_net"]) if lk["base_net"] else np.nan,
                                     "is_base": k1 == 1.0 and k2 == 1.0})
            else:
                for k1 in NEIGH:
                    for k2 in NEIGH:
                        st, tr = sim_eval(te, sig, lk, bar_secs, stop=2.0 * k1, tp=4.0 * k2)
                        rows.append({"symbol": sym, "trigger": lk["trigger"],
                                     "stop_atr": 2.0 * k1, "tp_atr": 4.0 * k2,
                                     "net": st["net"], "trades": st["trades"], "pf": RB.pf_of(tr),
                                     "ratio_vs_base": (st["net"] / lk["base_net"]) if lk["base_net"] else np.nan,
                                     "is_base": k1 == 1.0 and k2 == 1.0})
            write_csv(rows, out / sym / "plateau.csv")
            pos = sum(1 for r in rows if not r["is_base"] and r["net"] > 0)
            print(f"[plateau {tf} {sym}] جيران موجبون {pos}/8", flush=True)
            summary.append(f"plateau {tf} {sym} [{lk['exit']}]: positive neighbors {pos}/8")

    # 5) ablate — تفكيك المركب (الخلايا المقفلة بمركب الكل فحسب)
    if "ablate" in modes:
        for sym, lk in locked.items():
            if lk["trigger"] != "ALL14":
                print(f"[ablate {tf} {sym}] غير منطبق (المقفل {lk['trigger']})", flush=True)
                continue
            df_full = frames[tf][sym]
            if len(df_full) == 0:
                continue
            te = df_full[(df_full.index >= TEST_START) & (df_full.index <= TEST_END)]
            rows = []
            for drop in M213._trg.PRIORITY:
                sig = sig_ablate(df_full, te, drop)
                st, tr = sim_eval(te, sig, lk, bar_secs)
                rows.append({"symbol": sym, "dropped": drop, "net": st["net"],
                             "trades": st["trades"], "win_pct": st["win_pct"],
                             "pf": RB.pf_of(tr), "delta_vs_all14": st["net"] - lk["base_net"]})
            write_csv(rows, out / sym / "ablate.csv")
            worst = min(rows, key=lambda r: r["delta_vs_all14"])
            print(f"[ablate {tf} {sym}] الحامل الأكبر (أسوأ حذف): {worst['dropped']} Δ={worst['delta_vs_all14']:.2f}$", flush=True)
            summary.append(f"ablate {tf} {sym}: biggest carrier={worst['dropped']} (Δ={worst['delta_vs_all14']:.2f}$)")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="L0010 — جولة الضغط الخمسية على عابري L0009")
    ap.add_argument("--tf", choices=["1h", "4h", "both"], default="both")
    ap.add_argument("--source", choices=["disk", "stream"], default="disk")
    ap.add_argument("--archive", default=None)
    ap.add_argument("--ref", default="main")
    ap.add_argument("--symbols", default=None)
    ap.add_argument("--mode", choices=["all", "matrix", "slip", "blind", "plateau", "ablate"],
                    default="all")
    ap.add_argument("--trades", action="store_true")
    ap.add_argument("--skip-canary", action="store_true", help="تطوير فقط")
    return ap.parse_args(argv)


def main() -> int:
    args = parse_args()
    tfs = ["1h", "4h"] if args.tf == "both" else [args.tf]
    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else SYMBOLS
    modes = {"matrix", "slip", "blind", "plateau", "ablate"} if args.mode == "all" else {args.mode}
    t0 = time.time()
    canary_net = canary_gate(args)

    print("== تحميل نافذة الاختبار (دفء كـ L0009) ==", flush=True)
    frames, sha_std = load_frames(args, WARM_STD, TEST_END, symbols, tfs)
    blind_frames, sha_blind = None, {}
    if "blind" in modes:
        print("== تحميل النافذة العمياء 2021-2023 ==", flush=True)
        blind_frames, sha_blind = load_frames(args, BLIND_WARM, BLIND_END, symbols, tfs)

    locked = {tf: read_locked(HIST / "research" / "hyp_lab_out"
                              / ("L0009" if tf == "1h" else "L0009-tf4h"), symbols)
              for tf in tfs}
    print("المقفلات:", {tf: {s: f"{v['exit']}/{v['trigger']}" for s, v in locked[tf].items()}
                       for tf in tfs}, flush=True)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary: list[str] = [f"# L0010 — جولة الضغط | محاور={','.join(sorted(modes))} | "
                          f"مصدر={args.source} | فحص الثبات={canary_net}"]
    for tf in tfs:
        run_tf(tf, frames, locked[tf], symbols, blind_frames, modes, args, summary, args.trades)

    (OUT_ROOT / "env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"windows: test={TEST_START}→{TEST_END} | blind={BLIND_START}→{BLIND_END}\n"
        f"cost base=0.13%/side | slip stress={SLIP_TIERS} | notional=20$ | dual_spec base:"
        f" trig={DUAL_TRIG}/lock={DUAL_LOCK}/wide={M213.M197.WIDE}/tight={M213.M197.TIGHT}\n"
        f"canary={canary_net} | source={args.source}\n"
        + "".join(f"sha std {k}={v}\n" for k, v in sha_std.items())
        + "".join(f"sha blind {k}={v}\n" for k, v in sha_blind.items()), encoding="utf-8")
    summary.append(f"# المدة الكلية: {time.time()-t0:.1f} ث")
    (OUT_ROOT / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary), flush=True)
    print(f"اكتمل → {OUT_ROOT} في {time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
