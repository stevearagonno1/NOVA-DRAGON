#!/usr/bin/env python3
"""NOVA_V8 — combo_probe.py: شغّل تركيبة واحدة (أو عدة تركيبات) على نافذة، بلا جولة كاملة.

مفيد لـ: «قبل/بعد» أي تعديل في الكود، وفحص فرضية قبل ما تصرف عليها ساعات.
يستدعي مشغّل المحرك نفسه (sweep_engine.run_combo) — لا منطق نسخة ثانية هنا.

    python3 tools/combo_probe.py -s adaptive_trend -w 2023-09:2024-12 \
        -e NOVA_AT_TRAIL=8.0 -e NOVA_AT_STOP=1.2 -e NOVA_AT_PB=1440 -e NOVA_AT_TRIG=6

    # عدة حالات في سطر واحد (كل حالة = تركيبة)، والأخيرة تُقارن بالأولى:
    python3 tools/combo_probe.py -s adaptive_trend -w 2023-09:2024-12 \
        --case "الأساس|NOVA_AT_TRAIL=8.0,NOVA_AT_V3A=0" \
        --case "مع V3A|NOVA_AT_TRAIL=8.0,NOVA_AT_V3A=1"

الخيار --archive يحدد مجلد البيانات (افتراضياً $NOVA_ARCHIVE ثم ~/nova_v8_out).
"""
from __future__ import annotations
import argparse, os, pathlib, sys

REPO = pathlib.Path(__file__).resolve().parent.parent


def parse_case(spec: str):
    label, _, rest = spec.partition("|")
    env = {}
    for tok in (t for t in rest.replace(",", " ").split() if t):
        k, _, v = tok.partition("=")
        env[k] = v
    if not rest:                      # حالة بلا مفاتيح = اسم فقط
        label, env = rest, {}
    return label or "case", env


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--strategy", default="adaptive_trend")
    ap.add_argument("-w", "--window", default="2023-09:2024-12", help="YYYY-MM:YYYY-MM")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("-e", "--env", action="append", default=[], help="NOVA_*=قيمة")
    ap.add_argument("--case", action="append", default=[], help='"اسم|K=V K=V"')
    ap.add_argument("--archive", default=os.getenv("NOVA_ARCHIVE", ""))
    a = ap.parse_args()

    if a.archive:
        os.environ["NOVA_ARCHIVE"] = str(pathlib.Path(a.archive).expanduser())
    elif not os.getenv("NOVA_ARCHIVE"):
        for cand in (REPO / "crypto_archive", pathlib.Path("~/crypto_archive").expanduser()):
            if (cand).exists():
                os.environ["NOVA_ARCHIVE"] = str(cand)
                break

    cases = [(f"case{i+1}", {}) for i in range(0)]
    if a.case:
        cases = [parse_case(c) for c in a.case]
    else:
        cases = [("default", dict(t.split("=", 1) for t in a.env if "=" in t))]

    sys.path.insert(0, str(REPO))
    from nova_v8.sweep_engine import run_combo            # noqa: E402

    fr, to = a.window.split(":")
    base = None
    print(f"{'الحالة':<26}{'صفقات':>7}{'صافي $':>12}{'فوز%':>8}{'الفرق عن الأساس':>18}")
    print("─" * 74)
    for label, env in cases:
        r = run_combo(a.strategy, env, fr, to, a.symbol)
        net, tr, wp = r["net"], r["trades"], r["win_pct"]
        delta = "—" if base is None else ("مطابق للأساس" if (net, tr) == base
                                          else f"{net - base[0]:+.2f}$ / {tr - base[1]:+d} صفقة")
        if base is None:
            base = (net, tr)
        print(f"{label:<26}{tr:>7}{net:>+12.2f}{wp:>8.1f}{delta:>18}")
    print("─" * 74)
    print(f"الاستراتيجية: {a.strategy} | {a.symbol} | النافذة: {fr} → {to} | "
          f"الأرشيف: {os.environ.get('NOVA_ARCHIVE')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
