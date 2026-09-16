#!/usr/bin/env python3
"""NOVA_V8 — Lane Auditor (أداة العقل لتدقيق أي تجربة منتهية).

يعيد اشتقاق الادعاءات الرئيسية من ملفات CSV المرفوعة نفسها — لا يصدّق أي نص.
stdlib فقط (بلا pandas/شبكة) ليعمل على تيرمكس وأي sandbox في ثوانٍ.

الاستخدام:
    python3 tools/audit_lane.py                 # كل المسارات في history/sweep_results/
    python3 tools/audit_lane.py history/sweep_results/adaptive_trend --json

الفحوص:
  A1  عدد الصفوف == حجم الشبكة المشتق من القيم الفعلية (جداء عدد القيم لكل محور)
  A2  كل تركيبة فريدة (لا تكرار ولا صفوف زائدة)
  A3  لا تركيبة فاشلة (لا NaN، لا عمود err)
  A4  سلامة الاستكمال: صفوف sweep_train_partial.csv يجب أن تبقى كما هي داخل sweep_train.csv
  A5  صفّ الفائز في best_on_test.txt موجود فعلاً في sweep_train.csv
  A6  النهائيون في sweep_test.csv كلهم من التدريب + الفائز = الأفضل على الاختبار (مع التسامح مع التعادل)
  A7  plateau <= train_net
  A8  خمول المحاور: هل تبديل كل NOVA_* يغيّر النتيجة فعلاً؟ (اكتشاف الأعمدة الميتة)
  A9  الانضغاط: كم نتيجة مميزة فعلياً مقابل عدد التركيبات المعلنة
  A10 عدد التعادلات الدقيقة على net (تحذير: اختيار الفائز داخل التعادل ليس دليلاً)

ملاحظة تقنية إلزامية: ملفات المخرجات تُكتب بترميز utf-8-sig (حرف BOM في أول عمود).
أي قارئ يتجاهل ذلك يفقد أول محور في الشبكة — ولهذا كان القارئ الخاطئ يُظهر
"384 تركيبة فريدة من 1920" بينما الصحيح 1920. افتح دائماً بـ encoding="utf-8-sig".

خروج: 0 إذا نجحت كل الفحوص، 1 عند وجود فشل (F). التحذيرات (W) لا تُفشِل.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import sys

TOL = 1e-12  # tolerance for "identical float" comparisons


def _rows(path):
    if not os.path.exists(path):
        return None, None
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        return list(rd), (rd.fieldnames or [])


def _f(row, key):
    v = str((row or {}).get(key, "")).strip()
    if not v or v.lower() in {"nan", "none", "inf", "-inf"}:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def audit(lane_dir):
    lane = os.path.basename(lane_dir.rstrip("/"))
    checks = []

    def chk(cid, name, ok, detail, level="F"):
        checks.append({"id": cid, "name": name, "ok": bool(ok), "detail": detail, "level": level})

    train, header = _rows(os.path.join(lane_dir, "sweep_train.csv"))
    if not train:
        chk("A0", "sweep_train.csv موجود", False, "الملف مفقود")
        return lane, checks
    params = [c for c in header if c.startswith("NOVA_")]

    # A1 — grid size derived from the file itself
    vals = {c: sorted({r[c] for r in train}) for c in params}
    derived = 1
    for c in params:
        derived *= len(vals[c])
    complete = derived == len(train)
    chk("A1", "تغطية الشبكة كاملة", complete,
        f"{len(train)} صف مقابل جداء القيم {derived} "
        f"({'×'.join(str(len(vals[c])) for c in params)})", "F")

    # A2 — uniqueness
    keys = [tuple(r[c] for c in params) for r in train]
    dup = len(keys) - len(set(keys))
    chk("A2", "كل تركيبة فريدة", dup == 0, f"{dup} صف مكرر")

    # A3 — failures
    bad = sum(1 for r in train if _f(r, "net") is None or _f(r, "trades") is None)
    chk("A3", "لا تركيبة فاشلة", bad == 0 and "err" not in header,
        f"{bad} صف بصافي غير قابل للقراءة" + (" | عمود err موجود" if "err" in header else ""))

    # A4 — resume integrity (saved rows must survive verbatim)
    part, _ = _rows(os.path.join(lane_dir, "sweep_train_partial.csv"))
    if part is not None:
        fmap = {tuple(r[c] for c in params): r for r in train}
        verbatim, numeric, missing = 0, 0, 0
        worst_net = worst_other = 0.0
        for r in part:
            k = tuple(r[c] for c in params)
            m = fmap.get(k)
            if m is None:
                missing += 1
                continue
            if all(str(r[c]) == str(m[c]) for c in ["net", "trades", "win_pct"] if c in header):
                verbatim += 1
            else:
                numeric += 1
                for col in ("net", "trades", "win_pct"):
                    a, b = _f(r, col), _f(m, col)
                    if a is not None and b is not None:
                        d = abs(a - b)
                        if col == "net":
                            worst_net = max(worst_net, d)
                        else:
                            worst_other = max(worst_other, d)
        ok = missing == 0 and numeric == 0
        detail = (f"{verbatim}/{len(part)} مطابق نصياً؛ {numeric} اختلف في آخر خانة عشرية "
                  f"(max |Δnet|={worst_net:.1e}, max |Δtrades/win%|={worst_other:.1e}); "
                  f"مفقود من train: {missing}")
        if numeric and missing == 0 and worst_net < 1e-9:
            chk("A4", "سلامة الاستكمال (الصفوف المحفوظة بقيت كما هي)", False,
                detail + " → الأرقام سليمة ضمن ULP لكن عبارة «مطابقة بايت-ببايت» غير دقيقة", "W")
        else:
            chk("A4", "سلامة الاستكمال (الصفوف المحفوظة بقيت كما هي)", ok, detail)

    # A5 — winner row exists in train
    best_path = os.path.join(lane_dir, "best_on_test.txt")
    winner = None
    if os.path.exists(best_path):
        with open(best_path, encoding="utf-8-sig") as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
        if len(lines) >= 2:
            wtok = lines[0].split()
            wrow = dict(zip(wtok, lines[1].split()))
            winner = wrow
            hit = [r for r in train
                   if all(r.get(k) == v for k, v in wrow.items() if k in params and k in r)]
            chk("A5", "الفائز موجود كصف في sweep_train.csv", len(hit) >= 1,
                "تركيبة: " + " ".join(f"{k.replace('NOVA_', '')}={v}" for k, v in wrow.items() if k in params))
            tn, pl = _f(wrow, "train_net"), _f(wrow, "plateau")
            if tn is not None and pl is not None:
                chk("A7", "plateau <= train_net", pl <= tn + TOL, f"plateau={pl} train_net={tn}")

    # A6 — finalists + winner selection (tie-tolerant)
    test, theader = _rows(os.path.join(lane_dir, "sweep_test.csv"))
    if test:
        tparams = [c for c in theader if c.startswith("NOVA_")]
        fset = {tuple(r[c] for c in params) for r in train}
        alien = [r for r in test if tuple(r[c] for c in tparams) not in fset]
        chk("A6a", "كل النهائيين مسحبون من التدريب", not alien,
            f"{len(test)} نهائي، {len(alien)} غير موجود في التدريب")
        nets = [_f(r, "net") for r in test]
        valid = [n for n in nets if n is not None]
        if valid and winner:
            best = max(valid)
            winners_idx = [i for i, n in enumerate(nets) if n is not None and abs(n - best) <= max(TOL, abs(best) * 1e-9)]
            wcombo = tuple(winner.get(c) for c in tparams)
            chosen = any(tuple(test[i].get(c, "") for c in tparams) == wcombo for i in winners_idx)
            chk("A6b", "الفائز = الأفضل على نافذة الاختبار", chosen,
                f"أفضل net على الاختبار={best:.6f} مشترك بين {len(winners_idx)} نهائي "
                + ("→ الفائز واحد من تعادل دقيق (كسر التعادل بترتيب المحرك، ليس دليلاً)" if len(winners_idx) > 1 else ""))
            if len(winners_idx) > 1:
                chk("A6c", "لا تعادل على القمة", False, "انظر A6b", "W")
        neg = sum(1 for n in valid if n < 0)
        pos_tr = sum(1 for r in test if (_f(r, "train_net") or 0) > 0)
        flip = sum(1 for r in test if (_f(r, "train_net") or 0) > 0 and (_f(r, "net") or 0) < 0)
        chk("A8t", "حارس فرط الملاءمة: التقرير", True,
            f"{pos_tr}/{len(test)} نهائي موجب على التدريب، انقلب {flip} إلى سالب على الاختبار", "I")
        if valid and neg == len(valid):
            chk("VERDICT", "لا توجد تركيبة صالحة للنشر", False,
                f"كل النهائيين {len(valid)} سالبون خارج العينة "
                f"({min(valid):.2f}$ → {max(valid):.2f}$) ⇒ لا تُشغَّل أي تركيبة حياً", "F")

    # A8 — dead axes (inert flags): does flipping a param change the outcome at all?
    inert_report = []
    for c in params:
        groups = {}
        for r in train:
            others = tuple(r[k] for k in params if k != c)
            groups.setdefault(others, set()).add(r["net"])
        if not groups:
            continue
        same = sum(1 for v in groups.values() if len(v) == 1)
        rate = same / len(groups)
        inert_report.append((c, rate, len(groups)))
        level = "W" if rate >= 0.5 else "I"
        chk("A8", f"المحور {c.replace('NOVA_', '')} يُغيّر النتيجة", rate < 0.5,
            f"خامل في {same}/{len(groups)} من الأزواج ({rate:.0%})"
            + (" ← كل هذه التركيبات زائدة حسابياً" if rate >= 0.999 else ""), level)

    # A9 — compression: distinct outcomes vs declared combos
    distinct_out = len({(r["net"], r["trades"]) for r in train})
    ratio = distinct_out / len(train)
    chk("A9", "حجم البحث الفعلي مقابل المعلن", ratio > 0.5,
        f"{distinct_out} نتيجة مميزة فقط من {len(train)} تركيبة "
        f"({ratio:.0%}) ← الشبكة تكرّر نفسها", "W" if ratio <= 0.5 else "I")

    # A10 — ties on net
    counts = {}
    for r in train:
        counts[r["net"]] = counts.get(r["net"], 0) + 1
    tie_rows = sum(v for v in counts.values() if v > 1)
    chk("A10", "لا تعادلات دقيقة على net", tie_rows == 0,
        f"{len(counts)} قيمة net مميزة لـ{len(train)} صفاً؛ {tie_rows} صفاً ({tie_rows / len(train):.0%}) "
        f"يشارك صفاً آخر نفس net بالضبط", "W" if tie_rows else "I")
    return lane, checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lanes", nargs="*", help="مجلدات التجارب (افتراضياً كل history/sweep_results/*)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    lanes = a.lanes or ([os.path.join("history", "sweep_results", d) for d in sorted(os.listdir("history/sweep_results"))]
                        if os.path.isdir("history/sweep_results") else [])
    if not lanes:
        print("لا توجد مسارات للتدقيق")
        return 1
    all_checks, hard_fail = {}, False
    for l in lanes:
        lane, checks = audit(l)
        all_checks[lane] = checks
        print(f"\n{'=' * 66}\n  تدقيق المسار: {lane}   ({l})\n{'=' * 66}")
        for c in checks:
            mark = {"F": "❌" if not c["ok"] else "✅", "W": "⚠️ ", "I": "ℹ️ "}[c["level"]]
            stat = "PASS" if c["ok"] else ("FAIL" if c["level"] == "F" else "NOTICE")
            print(f"  {mark} {c['id']:5} {stat:6} {c['name']}")
            print(f"          {c['detail']}")
            if c["level"] == "F" and not c["ok"]:
                hard_fail = True
    n = sum(len(v) for v in all_checks.values())
    npass = sum(1 for v in all_checks.values() for c in v if c["ok"])
    print(f"\n{'—' * 66}\n  الخلاصة: {npass}/{n} فحص نظيف" +
          ("  ⇒ يحتاج تصحيحاً أو تقييماً من العقل" if hard_fail else "  ⇒ لا إخفاقات حرجة"))
    if a.json:
        print(json.dumps(all_checks, ensure_ascii=False, indent=2))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
