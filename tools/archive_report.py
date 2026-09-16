#!/usr/bin/env python3
"""يجمع نتائج كل تجارب الأرشيف (history/research/nova_v8_out/**) في جدول واحد.

يقرأ سجلّات الصفقات (research_results.csv) ويعيد لكل تجربة × استراتيجية:
عدد الصفقات، صافي $، نسبة الفوز، ونسبة الربح للخسارة (PF).
stdlib فقط — يعمل على تيرمكس.

    python3 tools/archive_report.py                 # كل التجارب
    python3 tools/archive_report.py --by-experiment # تفصيل حسب وسم التجربة
"""
from __future__ import annotations
import argparse, csv, os, sys, collections

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "history", "research", "nova_v8_out")


def runs(root=ROOT):
    for dirpath, _dirs, files in os.walk(root):
        if "research_results.csv" in files:
            yield os.path.relpath(dirpath, root), os.path.join(dirpath, "research_results.csv")


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            yield row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--by-experiment", action="store_true")
    ap.add_argument("--min", type=int, default=5, help="أقل عدد صفقات للعرض")
    a = ap.parse_args()

    agg = collections.defaultdict(lambda: [0, 0.0, 0, 0.0])   # key -> [trades, net, wins, grossloss]
    for label, path in runs():
        for r in load(path):
            try:
                net = float(r.get("pnl_usd") or 0.0)
            except ValueError:
                continue
            strat = r.get("strategy") or "?"
            exp = r.get("experiment") or "baseline"
            key = (label, strat, exp) if a.by_experiment else (label, strat, "")
            rec = agg[key]
            rec[0] += 1
            rec[1] += net
            if net > 0:
                rec[2] += 1
            else:
                rec[3] += -net

    if not agg:
        print("لا نتائج — تأكد أن مجلد history/research/ موجود بعد git checkout")
        return 1

    print(f"{'التجربة':<26}{'الاستراتيجية':<16}{'صفقات':>7}{'صافي $':>11}{'فوز%':>7}{'PF':>7}")
    print("─" * 76)
    for (label, strat, exp), (n, net, wins, loss) in sorted(agg.items(), key=lambda kv: (-kv[1][1], kv[0])):
        if n < a.min:
            continue
        pf = (net / loss) if loss > 0 else float("inf")
        tag = f"{label}" + (f" · {exp}" if exp else "")
        print(f"{tag:<26}{strat:<16}{n:>7}{net:>+11.2f}{100 * wins / n:>7.1f}{pf:>7.2f}")

    # خلاصة لكل استراتيجية عبر كل التجارب
    print("\n" + "─" * 76)
    print("خلاصة كل استراتيجية (كل التجارب مجموعة):")
    bys = collections.defaultdict(lambda: [0, 0.0])
    for (_l, strat, _e), (n, net, _w, _gl) in agg.items():
        bys[strat][0] += n
        bys[strat][1] += net
    for strat, (n, net) in sorted(bys.items(), key=lambda kv: -kv[1][1]):
        print(f"  {strat:<18} صفقات={n:>7}  صافي={net:>+12.2f} $")
    return 0


if __name__ == "__main__":
    sys.exit(main())
