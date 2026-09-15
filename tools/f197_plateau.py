#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص اعتماد F-197 على فريم أعلى — الهضبة (جيران ±20%) وتركز الصفقات. لا جولة جديدة.

أداة تدقيق لجولة الفريم (L0007-tf1h): تقرأ التركيبة المنتقاة من test_selected.csv ثم:
  الوضع الافتراضي  : يعيد تشغيل جيران ±20% حول (TRIG/LOCK) على نافذة التدريب فقط،
                     بنفس الآلة حرفياً (common.simulate + نواة MSS + dual-spec) —
                     ويقاطع مركز الشبكة مع قيمة sweep_train المودعة (يجب أن تتطابق).
  --stats          : يشتق من trades.csv (التركيبة المنتقاة، نافذة الاختبار):
                     أكبر خسارة منفردة · أسوأ شهر تقويمي · نسبة الصافي على أفضل 5 صفقات.

لا تعديل على السائق ولا على nova_v8/** — يقرأ ويحسب ويكتب CSV جدول الجيران فقط.
الاستعمال:
    python3 tools/f197_plateau.py --tf 1h            # جدول الجيران ±20% (تدريب)
    python3 tools/f197_plateau.py --tf 1h --stats    # تركز الصفقات (اختبار، من trades.csv)
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "hyp_lab"))
import run_v5 as R  # noqa: E402  (الثوابت نفسها: SYMBOLS/النوافذ/الأرشيف/pf_of)
from common import TF_MINUTES, atr, load, simulate, to_5m, to_bars  # noqa: E402
import F_126_mss_core as M126  # noqa: E402
import F_197_dual_trail as M197  # noqa: E402


def out_dir(tf: str) -> pathlib.Path:
    return REPO / "research" / "hyp_lab_out" / ("L0007" if tf == "5m" else f"L0007-tf{tf}")


def passers_of(base: pathlib.Path) -> list[str]:
    test = pd.read_csv(base / "F_197" / "all_symbols_test.csv", encoding="utf-8-sig")
    return test[test["gate"] == True]["symbol"].tolist()  # noqa: E712


def neighbors(tf: str) -> None:
    base = out_dir(tf)
    minutes = TF_MINUTES[tf]
    train = pd.read_csv(base / "F_197" / "all_symbols_train.csv", encoding="utf-8-sig")
    passers = passers_of(base)
    print(f"F-197 على {tf} — العابرون بالبوابة ({len(passers)}): {passers}\n")
    all_rows: list[dict] = []
    for sym in passers:
        sel = pd.read_csv(base / "F_197" / sym / "test_selected.csv", encoding="utf-8-sig").iloc[0]
        trig0, lock0 = float(sel["sel_NOVA_TRIG"]), float(sel["sel_NOVA_LOCK"])
        df1m = load(str(R.ARCHIVE / f"{sym}_1m.parquet"), start=R.WARM_START, end=R.TEST_END)
        bars = to_5m(df1m) if minutes == 5 else to_bars(df1m, minutes)
        tr = bars[(bars.index >= R.TRAIN_START) & (bars.index <= R.TRAIN_END)]
        a = atr(tr)
        sig = M126.mss_signal(tr)  # سائق F-197 = نواة MSS (مستقل عن التركيبة) — كما في السائق
        rows = []
        for tfac in (0.8, 1.0, 1.2):
            for lfac in (0.8, 1.0, 1.2):
                t, l = round(trig0 * tfac, 6), round(lock0 * lfac, 6)
                st, trades = simulate(tr, sig, a, notional=1000, bar_secs=minutes * 60,
                                      exit_mode="dual", dual=M197.make_dual_spec(trig=t, lock=l))
                rows.append({"symbol": sym, "trig": t, "lock": l, "trig_x": tfac, "lock_x": lfac,
                             "net": st["net"], "trades": st["trades"], "win_pct": st["win_pct"],
                             "pf": R.pf_of(trades), "center": tfac == 1.0 and lfac == 1.0})
        center = next(r for r in rows if r["center"])
        # تحقق متقاطع: مركز الشبكة يجب أن يساوي قيمة sweep_train المودعة لنفس التركيبة
        # (صف dual حصراً — صفوف std تتشارك مع dual نفس قيم trig/lock في السويب)
        dep = train[(train["symbol"] == sym) & (train["NOVA_EXIT"] == "dual")
                    & (train["NOVA_TRIG"] == trig0) & (train["NOVA_LOCK"] == lock0)]
        d_center = (center["net"] - float(dep["net"].iloc[0])) if len(dep) else float("nan")
        nb = [r for r in rows if not r["center"]]
        pos = sum(1 for r in nb if r["net"] > 0)
        print(f"── {sym}  (المنتقاة: trig={trig0} lock={lock0}) — تدريب {len(tr):,} شمعة {tf}")
        print(f"   net بحسب lock_x (صفوف) × trig_x (أعمدة) — المركز بين قوسين:")
        for lfac in (0.8, 1.0, 1.2):
            cells = []
            for tfac in (0.8, 1.0, 1.2):
                r = next(x for x in rows if x["trig_x"] == tfac and x["lock_x"] == lfac)
                mark = f"[{r['net']:+.2f}]" if r["center"] else f"{r['net']:+.2f}"
                cells.append(f"{mark:>12}")
            print(f"   lock×{lfac:<3}: " + " ".join(cells))
        print(f"   trig: {round(trig0*0.8,6):>9} {trig0:>9} {round(trig0*1.2,6):>9}")
        print(f"   المركز: net={center['net']:+.2f}$ trades={center['trades']} فوز={center['win_pct']}% "
              f"PF={center['pf']:.2f} | Δمركز مقابل المودّع={d_center:.2e}")
        print(f"   الجيران الثمانية: موجبون {pos}/8 · أدنى جار={min(r['net'] for r in nb):+.2f}$ · "
              f"أعلى جار={max(r['net'] for r in nb):+.2f}$ · صفقات المركز≥100: "
              f"{'نعم' if center['trades'] >= R.GATE_TRADES else 'لا'} · "
              f"جيران ≥100 صفقة: {sum(1 for r in nb if r['trades'] >= R.GATE_TRADES)}/8\n")
        all_rows.extend(rows)
    out = base / "F_197" / "plateau_neighbors_train.csv"
    pd.DataFrame(all_rows).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"الجدول الكامل: {out} ({len(all_rows)} صفاً)")


def _concentration(name: str, d: pd.DataFrame) -> dict:
    d = d.copy()
    d["entry_time"] = pd.to_datetime(d["entry_time"])
    net = float(d["pnl"].sum())
    wt = d.loc[d["pnl"].idxmin()] if len(d) else None
    m = d.groupby(d["entry_time"].dt.strftime("%Y-%m"))["pnl"].sum()
    wm_val = float(m.min()) if len(m) else 0.0
    wm_tag = str(m.idxmin()) if len(m) else "-"
    top5 = float(d["pnl"].nlargest(5).sum()) if len(d) >= 5 else float(d["pnl"].sum())
    return {"symbol": name, "net_csv": net, "trades": len(d),
            "max_loss": float(wt["pnl"]) if wt is not None else 0.0,
            "max_loss_at": f"{wt['symbol']}@{wt['entry_time']:%Y-%m-%d}" if wt is not None else "-",
            "worst_month": wm_val, "worst_month_tag": wm_tag,
            "months_traded": int(len(m)), "neg_months": int((m < 0).sum()),
            "top5_sum": top5, "top5_pct_of_net": (100.0 * top5 / net) if net else float("nan")}


def stats(tf: str) -> None:
    base = out_dir(tf)
    test = pd.read_csv(base / "F_197" / "all_symbols_test.csv", encoding="utf-8-sig")
    passers = passers_of(base)
    frames, rows = [], []
    for sym in passers:
        d = pd.read_csv(base / "F_197" / sym / "trades.csv", encoding="utf-8-sig")
        frames.append(d)
        rows.append(_concentration(sym, d))
    rows.append(_concentration(f"POOLED({len(passers)})", pd.concat(frames, ignore_index=True)))
    t = pd.DataFrame(rows)
    print(f"F-197 على {tf} — تركز الصفقات من trades.csv (نافذة الاختبار، العابرون {len(passers)})\n")
    print(t.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    # تحقق متقاطع: صافي trades.csv مقابل test_net المودّع (pnl مقرب لـ4 كسور ⇒ Δ متوقع ≤ ~1e-3)
    print("\n── تقاطع الصافي (trades.csv مقابل test_selected.csv المودّع):")
    for sym in passers:
        dep = float(test[test["symbol"] == sym]["test_net"].iloc[0])
        got = float(pd.read_csv(base / "F_197" / sym / "trades.csv", encoding="utf-8-sig")["pnl"].sum())
        print(f"   {sym}: Δ={got - dep:+.4f}$")


def main() -> int:
    ap = argparse.ArgumentParser(description="فحص اعتماد F-197: هضبة الجيران ±20% وتركز الصفقات")
    ap.add_argument("--tf", choices=["5m", "1h", "4h"], default="1h")
    ap.add_argument("--stats", action="store_true", help="إحصاء التركز من trades.csv بدل جدول الجيران")
    args = ap.parse_args()
    (stats if args.stats else neighbors)(args.tf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
