#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOVA — حارس استحالة التعبئة (L0046) · قابل للتشغيل في كل جولة قادمة.

القاعدة الحاكمة التي يحرسها:
    l[شمعة التعبئة] <= سعر التعبئة الفعلي <= h[شمعة التعبئة]
على **جانبي الدخول والخروج**، لكل صفقة، وفي كل جولة.

الاستخدام:
    python3 tools/fill_invariant_check.py --selftest
        حالات اختبار مصغّرة على بيانات مصطنعة: تُثبت أن العطب الأصلي صار مستحيلًا،
        وأن الوقف العادي والفجوة والهدف والإغلاق النهائي تعمل كما يجب.

    python3 tools/fill_invariant_check.py --trades <ملف.csv> [--frames <مجلد>]
        يمرّ على كل صفقة في الملف ويتحقق من النطاق مقابل شموع الإطار نفسه.

    python3 tools/fill_invariant_check.py --dir <مجلد> [--frames <مجلد>]
        يفحص كل ملفات *.csv في المجلد.

المخرج: عدد المخالفات. **يجب أن يكون صفرًا** — أي مخالفة = الإصلاح فاشل.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT))

COST = 0.0013           # كلفة الطرف (common.COST_PER_SIDE) — تُستعمل لعكس أثر الكلفة


# ═══════════════════════════ أدوات ═══════════════════════════
def _mk_df(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="4h", tz="UTC")
    df = pd.DataFrame(rows, index=idx,
                      columns=["open", "high", "low", "close", "volume"]).astype(float)
    return df


def _atr_const(df, val):
    return pd.Series(val, index=df.index)


def _run(common_mod, df, sig, atr_s, stop_atr, trig=0.0015, lock=0.0060, wide=0.0020, tight=0.0008):
    old = common_mod.STOP_ATR
    common_mod.STOP_ATR = stop_atr
    try:
        st, tr = common_mod.simulate(
            df, sig, atr_s, exit_mode="dual",
            dual={"trig": trig, "lock": lock, "wide": wide, "tight": tight},
            notional=20.0, bar_secs=14400)
    finally:
        common_mod.STOP_ATR = old
    return st, tr


# ═══════════════════════════ حالات الاختبار ═══════════════════════════
def selftest() -> int:
    import importlib.util
    import common as NEW                       # المحرك المصلَح

    broken_path = ROOT / "history" / "hyp_lab" / "common_broken_preL0046.py"
    spec = importlib.util.spec_from_file_location("common_broken_preL0046", broken_path)
    OLD = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(OLD)
    OLD.COST_PER_SIDE = COST

    fails = []
    print("═" * 74)
    print(" حارس التعبئة — حالات اختبار مصغّرة (بيانات مصطنعة)")
    print("═" * 74)

    def check_range(name, tr, df, expect_old_impossible=None):
        ok = True
        for p in tr:
            j = p["exit_j"]
            lo, hi = float(df["low"].iloc[j]), float(df["high"].iloc[j])
            px = p["exit_fill"] / (1 - COST)          # عكس الكلفة → سعر السوق
            if not (lo - 1e-12 <= px <= hi + 1e-12):
                ok = False
                print(f"  ❌ {name}: تعبئة خارج النطاق — السعر {px:.6f} ∉ [{lo:.6f}, {hi:.6f}] (شمعة {j})")
        return ok

    SIG0 = lambda n: pd.Series([True] + [False] * (n - 1))   # إشارة في الشمعة 0 ⇒ الدخول على افتتاح 1

    # ── س1: السيناريو الذي كشف العطب — دخول 100.1300 · القفل 100.7308 · أعلى سعر حقيقي 100.4000 ──
    df = _mk_df([(100.00, 100.01, 99.99, 100.00, 1.0),     # شمعة الإشارة
                 (100.00, 100.40, 99.99, 100.38, 1.0),     # الدخول على افتتاحها (100.00 → 100.1300) · القمة 100.40
                 (100.30, 100.35, 100.10, 100.25, 1.0)])   # هبوط
    a = _atr_const(df, 10.0)                                # وقف قاسٍ بعيد لا يتدخل
    _, tr_o = _run(OLD, df, SIG0(3), a, 2.5)
    _, tr_n = _run(NEW, df, SIG0(3), a, 2.5)
    old_px = tr_o[0]["exit_fill"] / (1 - COST) if tr_o else float("nan")
    new_px = tr_n[0]["exit_fill"] / (1 - COST) if tr_n else float("nan")
    _j = tr_n[0]["exit_j"] if tr_n else 0
    _lo, _hi = float(df["low"].iloc[_j]), float(df["high"].iloc[_j])
    print(f"\n س1 — السيناريو الكاشف: دخول 100.1300 · مستوى القفل 100.7308 · أعلى سعر بلغه السوق 100.4000")
    print(f"      المحرك المعطوب خرج عند: {old_px:.4f}")
    print(f"      المحرك المصلَح خرج عند: {new_px:.4f}  (نطاق شمعة الخروج [{_lo:.4f}, {_hi:.4f}])")
    if not (100.70 <= old_px <= 100.74):
        fails.append(f"س1: المحرك المعطوب لم يُظهر العطب (خرج عند {old_px})")
    if not (new_px <= 100.4000 + 1e-9):
        fails.append("س1: الإصلاح لم يمنع الخروج فوق أعلى سعر حقيقي")
    if not check_range("س1", tr_n, df):
        fails.append("س1: تعبئة خارج النطاق")
    if not [f for f in fails if f.startswith("س1")]:
        print("      ✅ المعطوب خرج فوق كل سعر موجود · والمصلَح خرج داخل النطاق")

    # ── س2: وقف عادي (الهبوط يلمس الوقف القاسي) ──
    df2 = _mk_df([(100.00, 100.01, 99.99, 100.00, 1.0),
                  (100.00, 100.05, 94.00, 95.00, 1.0)])
    _, tr2 = _run(NEW, df2, SIG0(2), _atr_const(df2, 1.0), 2.5)   # وقف = 100.1300 − 2.5 = 97.6300
    px2 = tr2[0]["exit_fill"] / (1 - COST) if tr2 else None
    exp2 = 100.00 * 1.0013 - 2.5
    r2 = check_range("س2", tr2, df2)
    print(f"\n س2 — وقف عادي: خرج عند {px2:.4f} (المتوقّع {exp2:.4f}) · داخل النطاق: {r2}")
    if not (tr2 and tr2[0]["exit_side"] == "stop" and abs(px2 - exp2) < 1e-6) or not r2:
        fails.append("س2: الوقف العادي لا يعمل كما يجب")
    else:
        print("      ✅")

    # ── س3: فجوة هابطة تحت الوقف → التعبئة عند الافتتاح ──
    df3 = _mk_df([(100.00, 100.01, 99.99, 100.00, 1.0),   # شمعة الإشارة
                  (100.00, 100.05, 99.99, 100.00, 1.0),   # شمعة الدخول (100.1300)
                  (90.00, 90.50, 89.00, 89.50, 1.0)])     # فجوة هابطة تحت الوقف
    _, tr3 = _run(NEW, df3, SIG0(3), _atr_const(df3, 1.0), 2.5)
    px3 = tr3[0]["exit_fill"] / (1 - COST) if tr3 else None
    r3 = check_range("س3", tr3, df3)
    print(f"\n س3 — فجوة هابطة: خرج عند {px3:.4f} (المتوقّع = الافتتاح 90.0000 لا مستوى الوقف 97.6300)")
    if not (tr3 and abs(px3 - 90.00) < 1e-9) or not r3:
        fails.append("س3: الفجوة الهابطة عُبِّئت عند مستوى الوقف لا عند الافتتاح")
    else:
        print("      ✅")

    # ── س4: الهدف في وضع std مع فجوة صاعدة فوق الهدف ──
    df4 = _mk_df([(100.00, 100.01, 99.99, 100.00, 1.0),
                  (100.00, 100.50, 99.99, 100.40, 1.0),
                  (110.00, 115.00, 109.00, 114.00, 1.0)])   # فتح فوق الهدف (tp = 100.13 + 4 = 104.1300)
    old_stop = NEW.STOP_ATR; NEW.STOP_ATR = 2.5
    try:
        _, tr4 = NEW.simulate(df4, SIG0(3), _atr_const(df4, 1.0), exit_mode="std", notional=20.0)
    finally:
        NEW.STOP_ATR = old_stop
    px4 = tr4[0]["exit_fill"] / (1 - COST) if tr4 else None
    r4 = check_range("س4", tr4, df4)
    print(f"\n س4 — هدف مع فجوة صاعدة: خرج عند {px4:.4f} (المتوقّع = الافتتاح 110.0000 لا الهدف 104.1300)")
    if not (tr4 and tr4[0]["exit_side"] == "tp" and abs(px4 - 110.00) < 1e-9) or not r4:
        fails.append("س4: مسار الهدف لا يعمل كما يجب مع الفجوة")
    else:
        print("      ✅")

    # ── س5: لا خروج مُشغَّل → الإغلاق النهائي عند إغلاق آخر شمعة ──
    df5 = _mk_df([(100.00, 100.01, 99.99, 100.00, 1.0),
                  (100.50, 100.90, 100.40, 100.80, 1.0)])
    _, tr5 = _run(NEW, df5, SIG0(2), _atr_const(df5, 10.0), 2.5)
    px5 = tr5[0]["exit_fill"] / (1 - COST) if tr5 else None
    r5 = check_range("س5", tr5, df5)
    print(f"\n س5 — لا خروج مُشغَّل: إغلاق نهائي عند {px5:.4f} (المتوقّع = إغلاق آخر شمعة 100.8000)")
    if not (tr5 and tr5[0]["exit_side"] == "eod" and abs(px5 - 100.80) < 1e-9) or not r5:
        fails.append("س5: الإغلاق النهائي لا يعمل كما يجب")
    else:
        print("      ✅")

    # ── س6: قفل مشروع (بلغه السعر فعلًا) ثم عودة إليه ──
    df6 = _mk_df([(100.00, 100.01, 99.99, 100.00, 1.0),
                  (100.00, 100.90, 99.99, 100.85, 1.0),    # القمة 100.90 > 100.7308 ⇒ القفل يُمنح
                  (101.00, 101.10, 100.50, 100.60, 1.0)])  # هبوط يلمس القفل
    _, tr6 = _run(NEW, df6, SIG0(3), _atr_const(df6, 10.0), 2.5)
    px6 = tr6[0]["exit_fill"] / (1 - COST) if tr6 else None
    lock_px = 100.00 * 1.0013 * 1.006
    r6 = check_range("س6", tr6, df6)
    print(f"\n س6 — قفل مشروع: خرج عند {px6:.4f} (المتوقّع = {lock_px:.4f}) · داخل النطاق: {r6}")
    if not (tr6 and abs(px6 - lock_px) < 1e-6) or not r6:
        fails.append("س6: القفل المشروع (بلغه السعر فعلًا) لا يعمل")
    else:
        print("      ✅")

    # ── س7/س8: شبكة L0058 — شمعة كلها تحت الشراء، وأخرى كلها فوق البيع ──
    import nova_v8.grid as _grid
    buy_cell = _grid._Cell(100.0, 110.0, 1000.0)
    buy_cell.on_bar(90.0, 92.0, 88.0, 91.0)
    print(f"\n س7 — شبكة: شمعة كلها تحت الشراء. التعبئة={buy_cell.fill_buy:.4f} (المتوقّع الافتتاح 90 لا المستوى 100)")
    if not (buy_cell.open and abs(buy_cell.fill_buy - 90.0) < 1e-9 and 88.0 <= buy_cell.fill_buy <= 92.0):
        fails.append("س7: شراء الشبكة لم يُعبَّأ عند الافتتاح داخل النطاق")
    else:
        print("      ✅")
    sell_cell = _grid._Cell(100.0, 110.0, 1000.0)
    sell_cell.on_bar(100.0, 100.0, 100.0, 100.0)
    sell_cell.on_bar(120.0, 125.0, 118.0, 122.0)
    print(f" س8 — شبكة: شمعة كلها فوق البيع. التعبئة={sell_cell.fill_sell:.4f} (المتوقّع الافتتاح 120 لا المستوى 110)")
    if not (sell_cell.cycles == 1 and abs(sell_cell.fill_sell - 120.0) < 1e-9 and 118.0 <= sell_cell.fill_sell <= 125.0):
        fails.append("س8: بيع الشبكة لم يُعبَّأ عند الافتتاح داخل النطاق")
    else:
        print("      ✅")

    print("\n" + "═" * 74)
    if fails:
        print(f" ❌ فشل {len(fails)} اختبار:")
        for f in fails:
            print("   -", f)
        return 1
    print(" ✅ PASS — 8/8: العطب الأصلي مستحيل · الوقف والفجوة والهدف والإغلاق والقفل سليمة · فجوات الشبكة داخل النطاق")
    print("═" * 74)
    return 0


# ═══════════════════════════ فحص ملفات الصفقات ═══════════════════════════
def check_csv(path: pathlib.Path, frames: pathlib.Path, verbose: bool = True, *,
              cost: float | None = None, bar_tag: str = "4h") -> dict:
    """الافتراضي cost=None (أي 0.0013) وbar_tag=4h — سلوك الفحص القديم حرفياً.

    كلفة أو إطار مختلف يُمرَّران صراحة. صف بلا شمعة مطابقة يُحسب skipped ولا يُعدّ سليماً بصمت.
    """
    use_cost = COST if cost is None else float(cost)
    t = pd.read_csv(path, encoding="utf-8-sig")
    need = {"symbol", "entry_time", "exit_time", "entry", "exit"}
    if not need.issubset(t.columns):
        return {"file": path.name, "status": "تخطٍّ (أعمدة ناقصة)", "n": 0, "viol": 0,
                "checked": 0, "skipped": 0, "missing_frames": 0}
    frames_cache = {}
    viol_exit = viol_entry = 0
    cost_out_exit = cost_out_entry = 0
    max_dev = 0.0
    examples = []
    checked = skipped = missing_frames = 0
    for _, r in t.iterrows():
        sym = str(r["symbol"])
        if sym not in frames_cache:
            f = frames / f"{sym}_{bar_tag}.parquet"
            frames_cache[sym] = pd.read_parquet(f) if f.exists() else None
        df = frames_cache[sym]
        if df is None:
            missing_frames += 2
            continue
        for side, tcol, pcol in (("entry", "entry_time", "entry"), ("exit", "exit_time", "exit")):
            try:
                ts = pd.Timestamp(r[tcol])
            except Exception:
                skipped += 1
                continue
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            if ts not in df.index:
                skipped += 1
                continue
            checked += 1
            bar = df.loc[ts]
            px = float(r[pcol])
            market = px / (1 + use_cost) if side == "entry" else px / (1 - use_cost)
            lo, hi = float(bar["low"]), float(bar["high"])
            # تسامح نسبي 1e-6 (0.0001%) لأن أسعار الملفات مقرَّبة إلى 6 خانات ⇒ أثر تقريب
            # بحجم ~1e-9 عند الحد. أي انحراف أكبر = مخالفة حقيقية.
            tol = 1e-6 * max(abs(lo), abs(hi), 1e-9)
            if (lo - market) > tol or (market - hi) > tol:
                if side == "exit":
                    viol_exit += 1
                else:
                    viol_entry += 1
                if len(examples) < 5:
                    examples.append((side, sym, str(ts), market, lo, hi))
            if (lo - px) > tol or (px - hi) > tol:        # التعبئة بعد الكلفة (يُبلَّغ منفصلًا)
                if side == "exit":
                    cost_out_exit += 1
                else:
                    cost_out_entry += 1
    res = {"file": path.name, "n": len(t), "viol_entry": viol_entry, "viol_exit": viol_exit,
           "cost_out_entry": cost_out_entry, "cost_out_exit": cost_out_exit,
           "viol": viol_entry + viol_exit, "examples": examples,
           "checked": checked, "skipped": skipped, "missing_frames": missing_frames,
           "cost": use_cost, "bar_tag": bar_tag}
    if verbose:
        mark = "✅" if res["viol"] == 0 else "❌"
        print(f"  {mark} {path.name}: صفقات={len(t)} · فُحص={checked} · تُخطّي={skipped} · "
              f"شموع ناقصة={missing_frames} · مخالفات الدخول={viol_entry} · "
              f"مخالفات الخروج={viol_exit}")
        if cost_out_entry or cost_out_exit:
            print(f"      (خارج النطاق بعد إضافة الكلفة: دخول {cost_out_entry} · خروج {cost_out_exit}"
                  f" — أثر كلفة لا سعر سوق)")
        for e in examples:
            print(f"      مثال: {e[0]} {e[1]} {e[2]} السوق={e[3]:.6f} ∉ [{e[4]:.6f}, {e[5]:.6f}]")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--trades", type=str)
    ap.add_argument("--dir", type=str)
    ap.add_argument("--frames", type=str,
                    default=str(pathlib.Path.home() / ".cache" / "l0046_frames"))
    ap.add_argument("--cost", type=float, default=None,
                    help="كلفة الطرف لعكس التعبئة. الافتراضي 0.0013 كما كان — لا تغيّره إلا لفحص ملف كلفته مختلفة")
    ap.add_argument("--bar-tag", default="4h",
                    help="لاحقة ملف الشمعة {sym}_{tag}.parquet. الافتراضي 4h حتى لا يتغيّر فحص الملفات القديمة")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    frames = pathlib.Path(a.frames)
    if not frames.exists():
        print(f"❌ مجلد الشموع غير موجود: {frames} (مرّر --frames)")
        return 2
    files = []
    if a.trades:
        files = [pathlib.Path(a.trades)]
    elif a.dir:
        files = sorted(pathlib.Path(a.dir).rglob("trades*.csv"))
    else:
        ap.print_help()
        return 2
    print("═" * 74)
    print(f" حارس التعبئة — {len(files)} ملف")
    print("═" * 74)
    tot = 0
    for f in files:
        r = check_csv(f, frames, cost=a.cost, bar_tag=a.bar_tag)
        tot += r["viol"]
    print("═" * 74)
    print(f" مجموع المخالفات: {tot}  →  {'✅ صفر — الآلة سليمة' if tot == 0 else '❌ الإصلاح فاشل'}")
    print("═" * 74)
    return 0 if tot == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
