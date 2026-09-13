#!/usr/bin/env python3
"""NOVA-DRAGON — new_lane.py : افتح مسار تجربة في 5 ثوانٍ.

    python3 tools/new_lane.py "عنوان المسار" --type research --budget "3h" \
        --question "ما …؟" --command "python3 nova_v8/sweep_engine.py …"

يفعل ثلاثة أشياء فقط: ينسخ docs/lanes/_TEMPLATE.md إلى docs/lanes/L{next}-{slug}.md
مع تعويض الحقول، ويضيف سطراً للوحة docs/lanes/INDEX.md، ويطبع ما تلصقه في المحادثة الجديدة.
stdlib فقط — يعمل على تيرمكس.
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LANES = ROOT / "docs" / "lanes"
TEMPLATE = LANES / "_TEMPLATE.md"
INDEX = LANES / "INDEX.md"


def slugify(s: str, fallback: str = "") -> str:
    """ASCII-only slug (العربية لا تصلح أسماء ملفات في git على بعض الأنظمة)."""
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return (s[:34] or fallback or "lane").rstrip("-")


def next_id() -> int:
    used = [int(m.group(1)) for p in LANES.glob("L*.md")
            for m in [re.match(r"L(\d{4})", p.name)] if m]
    return (max(used) + 1) if used else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("title")
    ap.add_argument("--type", default="research", choices=["research", "data", "infra", "maintenance"])
    ap.add_argument("--status", default="📝 مسودة")
    ap.add_argument("--budget", default="3h")
    ap.add_argument("--question", default="(اكتب السؤال الواحد هنا)")
    ap.add_argument("--hypothesis", default="(فرضية قابلة للتكذيب)")
    ap.add_argument("--success", default="(ما الذي يجعلها نجاحاً — رقمياً)")
    ap.add_argument("--failure", default="(ما الذي يجعلها فشلاً — رقمياً)")
    ap.add_argument("--command", default="(أمر التشغيل الحرفي)")
    ap.add_argument("--slug", default="", help="اسم ملف لاتيني (يُشتق تلقائياً من الكلمات اللاتينية في العنوان)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not TEMPLATE.exists():
        print(f"❌ القالب مفقود: {TEMPLATE}", file=sys.stderr)
        return 1
    lid = f"{next_id():04d}"
    dest = LANES / f"L{lid}-{slugify(a.title, a.slug)}.md"
    if dest.exists():
        print(f"❌ موجود: {dest}", file=sys.stderr)
        return 1

    txt = TEMPLATE.read_text(encoding="utf-8")
    reps = {"{{ID}}": lid, "{{TITLE}}": a.title, "{{STATUS}}": f"{a.status} · {dt.date.today().isoformat()}",
            "{{TYPE}}": a.type, "{{BUDGET}}": a.budget, "{{QUESTION}}": a.question,
            "{{HYPOTHESIS}}": a.hypothesis, "{{SUCCESS}}": a.success, "{{FAILURE}}": a.failure,
            "{{COMMAND}}": a.command}
    for k, v in reps.items():
        txt = txt.replace(k, v)

    row = (f"| **L‑{lid}** | {a.title} | {a.type} | {a.status} | محادثة تجربة | "
           f"`docs/lanes/{dest.name}` | — |")
    if a.dry_run:
        print(f"# سأنشئ {dest}\n# وسأضيف لهذا السطر في اللوحة:\n{row}")
        return 0
    dest.write_text(txt, encoding="utf-8")

    if INDEX.exists():
        lines = INDEX.read_text(encoding="utf-8").splitlines()
        idx = max((i for i, l in enumerate(lines) if l.startswith("|")), default=len(lines) - 1)
        lines.insert(idx + 1, row)
        INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ أنشأت {dest.relative_to(ROOT)} وأضفت سطراً إلى {INDEX.relative_to(ROOT)}\n")
    print("الآن: افتح محادثة جديدة والصق عليها قسم «نصّ الإطلاق» من الملف، وأخبرني بالمسار لأتابعه.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
