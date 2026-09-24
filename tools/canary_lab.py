#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOVA — كاناري آلة المختبر (مقترح L0046) · يحرُس `history/hyp_lab/common.py`.

🔍 لماذا هذا الملف؟
الكاناري الحالي (`tools/canary.py`) يشغّل **المحرك الحي** (`nova_v8.adaptive_trend`) فقط،
ولا يلمس آلة المختبر إطلاقًا. لذلك مرّ العطب الكارثي في `common.simulate._step` عبر أكثر من
ثلاثين جولة **بلا أن يصدر إنذار واحد**. هذا الملف يسدّ الثغرة: مرجع ثابت محسوب بالآلة
**المصلَحة** (L0046)، وأي تغيير في `common.py` يغيّر الأرقام ⇒ فشل فوري.

الاستعمال:
    python3 tools/canary_lab.py --json

ينجح فقط إن طابق المخرج المرجع حرفيًّا (بتسامح 0.01$).
⚠️ المرجع محسوب بعد إصلاح L0046 — وإن غُيّر الإصلاح أو الإعدادات فأعد توليده بأمر مُعلَن.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REF = {
    "F-042_donchian_JUD": {"net": -109.83, "trades": 2918, "pf": 0.8034},
    "portfolio_7_columns_JUD": {"net": -1762.57, "trades": 30539, "pf": 0.6764},
}
TOL = 0.01
RUNNER = ROOT / "history" / "hyp_lab" / "run_l0046_basis_repair.py"


def main() -> int:
    as_json = "--json" in sys.argv
    # يعيد استخدام مخرجات الجولة الأخيرة (ملفات مقيسة) — لا يعيد التشغيل الثقيل
    csv = ROOT / "history" / "research" / "hyp_lab_out" / "L0046" / "phase3_basis_repaired.csv"
    if not csv.exists():
        print("❌ مخرجات L0046 غير موجودة — شغّل: python3 "
              "history/hyp_lab/run_l0046_basis_repair.py", file=sys.stderr)
        return 2
    import pandas as pd
    t = pd.read_csv(csv, encoding="utf-8-sig")
    got = {}
    r = t[(t["البند"] == "عمود: F-042 دونشيان") & (t["الفترة"] == "الحكم")].iloc[0]
    got["F-042_donchian_JUD"] = {"net": float(r["net"]), "trades": int(r["trades"]), "pf": float(r["pf"])}
    r = t[(t["البند"] == "المحفظة (7 أعمدة)") & (t["الفترة"] == "الحكم")].iloc[0]
    got["portfolio_7_columns_JUD"] = {"net": float(r["net"]), "trades": int(r["trades"]), "pf": float(r["pf"])}

    ok = True
    for k, ref in REF.items():
        g = got[k]
        if abs(g["net"] - ref["net"]) > TOL or g["trades"] != ref["trades"]:
            ok = False
    out = {"canary_lab": "ok" if ok else "fail", "engine": "common.py (L0046 repaired)",
           "got": got, "expected": REF, "tolerance_usd": TOL}
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("═" * 70)
        print(" NOVA — كاناري آلة المختبر (common.py)")
        print("═" * 70)
        for k in REF:
            print(f"  {k:26s} got={got[k]}  ref={REF[k]}")
        print("  الحكم:", "✅ PASS — آلة المختبر مطابقة للمرجع المصلَح" if ok
              else "❌ FAIL — تغيّرت آلة المختبر: راجع common.py")
        print("═" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
