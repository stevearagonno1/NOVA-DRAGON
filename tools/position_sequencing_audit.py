#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOVA — حارس تتابع المراكز (L0048).

يقيس تداخل المراكز على ملف صفقات واحد (دفتر واحد). بعد إصلاح
``strict_single`` يجب أن يكون التداخل صفرًا.

التعريف (يطابق قاعدة «لا فتح ما دام السابق مفتوحًا»):
    على الرمز نفسه، صفقتان تتداخلان إذا تقاطع وقتاهما بمدة موجبة:
    max(entry) < min(exit).
    إعادة الدخول في لحظة الخروج تمامًا ليست تداخلًا (الخروج يُعالَج قبل الدخول).

الاستعمال:
    python3 tools/position_sequencing_audit.py --trades ملف.csv
    python3 tools/position_sequencing_audit.py --dir مجلد
    python3 tools/position_sequencing_audit.py --trades ملف.csv --require-zero
    python3 tools/position_sequencing_audit.py --selftest

المخرج: نسبة التداخل = صفقات متداخلة / كل الصفقات، وأقصى تزامن.
رمز الخروج 1 إذا طُلب --require-zero وكان التداخل غير صفر.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import pandas as pd


def _ts(v) -> pd.Timestamp:
    t = pd.Timestamp(v)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t


def audit_frame(t: pd.DataFrame) -> dict:
    need = {"symbol", "entry_time", "exit_time"}
    if t is None or t.empty or not need.issubset(t.columns):
        return {"trades": 0, "overlapping_trades": 0, "overlap_ratio": 0.0,
                "max_concurrent": 0, "symbols_with_overlap": 0, "status": "empty"}
    overlap_ids: set[int] = set()
    max_c = 0
    syms_bad = 0
    gid = 0
    for _, g in t.groupby("symbol", sort=False):
        ivs = []
        for _, r in g.iterrows():
            ivs.append((_ts(r["entry_time"]), _ts(r["exit_time"]), gid))
            gid += 1
        ivs.sort(key=lambda x: (x[0], x[1], x[2]))
        # صفقة ما زالت مفتوحة عند دخول لاحقة إذا كان خروجها بعد ذلك الدخول.
        # الخروج في لحظة الدخول تمامًا ليس تداخلًا (إعادة دخول بعد الإغلاق).
        # صفقة مدتها صفر (دخول=خروج) لا تُبقي نفسها «مفتوحة» بعدها — وإلا عُدّت
        # متداخلة مع كل ما يليها، وهذا خطأ مسح الأحداث.
        active: list[tuple] = []
        local_max = 0
        bad = False
        batch_en = None
        batch_n = 0
        for en, ex, k in ivs:
            active = [(exit_t, i) for exit_t, i in active if exit_t > en]
            if batch_en != en:
                batch_en, batch_n = en, 1
            else:
                batch_n += 1
            if active or batch_n > 1:
                bad = True
                overlap_ids.add(k)
                overlap_ids.update(i for _, i in active)
            active.append((ex, k))
            local_max = max(local_max, len(active), batch_n)
        max_c = max(max_c, local_max)
        if bad:
            syms_bad += 1
    n = len(t)
    ov = len(overlap_ids)
    return {
        "trades": n,
        "overlapping_trades": ov,
        "overlap_ratio": round(ov / n, 6) if n else 0.0,
        "max_concurrent": max_c,
        "symbols_with_overlap": syms_bad,
        "status": "ok" if ov == 0 else "overlap",
    }


def audit_csv(path: pathlib.Path) -> dict:
    t = pd.read_csv(path, encoding="utf-8-sig")
    r = audit_frame(t)
    r["file"] = path.name
    return r


def selftest() -> int:
    """يثبت أن التعريف يلتقط التداخل ولا يحتسب إعادة الدخول عند لحظة الخروج."""
    base = pd.Timestamp("2024-01-01", tz="UTC")
    rows = [
        {"symbol": "BTCUSDT", "entry_time": base, "exit_time": base + pd.Timedelta(hours=12)},
        {"symbol": "BTCUSDT", "entry_time": base + pd.Timedelta(hours=4),
         "exit_time": base + pd.Timedelta(hours=8)},
        {"symbol": "ETHUSDT", "entry_time": base, "exit_time": base + pd.Timedelta(hours=4)},
        {"symbol": "ETHUSDT", "entry_time": base + pd.Timedelta(hours=4),
         "exit_time": base + pd.Timedelta(hours=8)},
    ]
    r = audit_frame(pd.DataFrame(rows))
    fails = []
    if r["overlapping_trades"] != 2:
        fails.append(f"المتوقع صفقتان متداخلتان على BTC، جاء {r}")
    if r["symbols_with_overlap"] != 1:
        fails.append(f"المتوقع رمز واحد متداخل، جاء {r['symbols_with_overlap']}")
    if r["max_concurrent"] != 2:
        fails.append(f"أقصى تزامن المتوقع 2، جاء {r['max_concurrent']}")
    clean = pd.DataFrame([
        {"symbol": "BTCUSDT", "entry_time": base, "exit_time": base + pd.Timedelta(hours=4)},
        {"symbol": "BTCUSDT", "entry_time": base + pd.Timedelta(hours=4),
         "exit_time": base + pd.Timedelta(hours=8)},
    ])
    r2 = audit_frame(clean)
    if r2["overlapping_trades"] != 0 or r2["max_concurrent"] != 1:
        fails.append(f"إعادة الدخول عند لحظة الخروج ليست تداخلًا، جاء {r2}")
    if fails:
        print("❌ selftest فشل:")
        for f in fails:
            print("  -", f)
        return 1
    print("✅ selftest — التداخل يُلتقط، والتلامس عند الخروج لا يُحتسب")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", type=str)
    ap.add_argument("--dir", type=str)
    ap.add_argument("--require-zero", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    files = []
    if a.trades:
        files = [pathlib.Path(a.trades)]
    elif a.dir:
        files = sorted(pathlib.Path(a.dir).rglob("trades*.csv"))
    else:
        ap.print_help()
        return 2
    results = [audit_csv(f) for f in files]
    bad = [r for r in results if r["overlapping_trades"]]
    summary = {"files": len(results), "files_with_overlap": len(bad),
               "overlap": 0 if not bad else sum(r["overlapping_trades"] for r in bad),
               "results": results}
    if a.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("═" * 74)
        print(" حارس تتابع المراكز")
        print("═" * 74)
        for r in results:
            mark = "✅" if r["overlapping_trades"] == 0 else "❌"
            print(f"  {mark} {r['file']}: صفقات={r['trades']} · متداخلة={r['overlapping_trades']}"
                  f" · نسبة={r['overlap_ratio']:.4%} · أقصى تزامن={r['max_concurrent']}")
        print("═" * 74)
        print(" تداخل إجمالي:", summary["overlap"],
              "→", "صفر" if summary["overlap"] == 0 else "يوجد تداخل")
    if a.require_zero and summary["overlap"] != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
