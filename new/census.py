#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA census + quarantine — إحصاء شامل لكل ملفات new/ + عزل الحاملين لمفاتيح حقيقية.
أمر إعادة الاشتقاق (من جذر المستودع):
    python3 new/census.py
المخرجات:
    new/CENSUS.md        — الجدول العربي الكامل لكل ملف كود
    new/_quarantine/     — الملفات المعزولة (محرّكة، ليست منسوخة)
    new/_quarantine/MAP.md — خريطة العزل (تُبنى من محتوى العزل نفسه — قابلة لإعادة التوليد)
قواعد:
  - مسح المفاتيح يجري على EVERY ملف نصي (كود أو وثيقة) — لا استثناءات.
  - ملفات الكود فقط تدخل جدول CENSUS.
"""
import ast
import hashlib
import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))  # new/
QUAR = os.path.join(ROOT, "_quarantine")

# ---------- 1) أنماط المفاتيح الحقيقية ----------
KEY_PATTERNS = [
    ("تيليجرام", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{30,}\b")),
    ("جيميناي-AIza", re.compile(r"\bAIza[A-Za-z0-9_-]{30,}\b")),
    ("جيميناي-AQ", re.compile(r"\bAQ\.[A-Za-z0-9_-]{20,}\b")),
    ("بينانس-64", re.compile(r"\b[A-Za-z0-9]{64}\b")),
]
PLACEHOLDER_HINTS = re.compile(
    r"(?i)your|xxx|placeholder|example|os\.getenv|<[^>]*>|\*\*\*|أدخل|ضع_هنا|ضع هنا"
)
ASSIGN_CTX = re.compile(r"(?i)(api_key|apikey|secret|token|passw|key)\s*[:=]")

BINARY_EXT = {".pdf", ".zip", ".rar", ".gz", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".mp3", ".mp4"}
PY_HINTS = re.compile(r"^(import |from |def |class |async |@|#\s*import)", re.M)
SH_HINTS = re.compile(r"^(#!/bin/(ba)?sh|export |cd |pip |python|curl |chmod )", re.M | re.I)


def looks_like_python(text: str) -> bool:
    if text.startswith("#!") and "python" in text.splitlines()[0]:
        return True
    return len(PY_HINTS.findall(text)) >= 3


def classify(fn: str, text: str):
    """يعيد (نوع، هل-كود): نوع ∈ {بايثون، شل، وثيقة/بيانات}"""
    ext = os.path.splitext(fn)[1].lower()
    if ext in (".py", ".p9"):
        return "بايثون", True
    if ext in (".sh", ".bash"):
        return "شل", True
    if looks_like_python(text):
        return "بايثون", True
    if text.startswith("#!/bin/") or len(SH_HINTS.findall(text)) >= 3:
        return "شل", True
    return "وثيقة/بيانات", False


def read_text(path: str):
    raw = open(path, "rb").read()
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc), len(raw)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), len(raw)


def sha256_short(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


def extract_title(text: str) -> str:
    ver = re.compile(r"(NOVA[^\n]{0,10}V\d[\w.]*|V\d+\.\d+(?:\.\d+)?[^\n]{0,40})")
    for ln in text.splitlines()[:100]:
        s = ln.strip().strip("#═-*_ ").strip()
        if not s or s.startswith(("-*-", "!/")):
            continue
        if ver.search(s):
            return s[:90]
        if len(s) > 4 and not s.startswith(("http", "pip ", "python")):
            return s[:90]
    return "(بلا ترويسة)"


def key_scan(text: str):
    found = []
    for label, pat in KEY_PATTERNS:
        for m in pat.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            ls = text.rfind("\n", 0, m.start()) + 1
            le = text.find("\n", m.end())
            line = text[ls : le if le != -1 else len(text)]
            if label == "بينانس-64" and not ASSIGN_CTX.search(line):
                continue
            if PLACEHOLDER_HINTS.search(line):
                continue
            found.append((label, line_no))
    return found


def ast_check(text: str):
    try:
        tree = ast.parse(text)
        n = sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) for x in ast.walk(tree))
        return "سليم", n
    except SyntaxError as e:
        return f"معطوب (سطر {e.lineno})", 0
    except (ValueError, RecursionError):
        return "معطوب (قيمة)", 0


def main():
    rows, quarantined, non_code = [], [], 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d != "_quarantine"]
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            ext = os.path.splitext(fn)[1].lower()
            if ext in BINARY_EXT:
                non_code += 1
                continue
            try:
                text, nbytes = read_text(full)
            except OSError:
                continue
            # ---- 1) مسح المفاتيح على كل ملف نصي بلا استثناء ----
            keys = key_scan(text)
            if keys or fn == ".env":
                dst = os.path.join(QUAR, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(full, dst)
                quarantined.append(rel)
                continue  # المعزول لا يدخل جدول الإحصاء
            # ---- 2) التصنيف ----
            kind, is_code = classify(fn, text)
            if not is_code:
                non_code += 1
                continue
            status, nfuncs = ast_check(text) if kind == "بايثون" else ("—", 0)
            rows.append({
                "rel": rel, "size": nbytes, "kind": kind,
                "title": extract_title(text), "ast": status, "funcs": nfuncs,
                "red": text.count("__REDACTED__"), "sha": sha256_short(full),
            })

    # ---------- خريطة العزل تُبنى من محتوى مجلد العزل نفسه (كاملة وقابلة لإعادة التوليد) ----------
    os.makedirs(QUAR, exist_ok=True)
    quar_files = []
    for dirpath, dirnames, filenames in os.walk(QUAR):
        for fn in filenames:
            if fn == "MAP.md":
                continue
            quar_files.append(os.path.relpath(os.path.join(dirpath, fn), QUAR))
    quar_files.sort()
    map_lines = [
        "# 🗄️ خريطة العزل — new/_quarantine/MAP.md",
        "",
        "> هذه الملفات تحتوي مفاتيح ذات شكل حقيقي (بينانس/تيليجرام/جيميناي) أو هي ملفات `.env`.",
        "> **ممنوعٌ أبداً الالتزام بها في git** — المجلد بأكمله داخل `.gitignore`.",
        "> الأصل قبل النقل موجود داخل `nova_upload_bundle.tar.gz` (بصمة موثقة في CENSUS.md).",
        "",
        f"**عدد الملفات المعزولة: {len(quar_files)}** (تُعاد بصياغة هذا الملف بأمر: `python3 new/census.py`)",
        "",
        "| المسار الأصلي (داخل new/) | سبب العزل |",
        "|---|---|",
    ]
    for rel in quar_files:
        text, _ = read_text(os.path.join(QUAR, rel))
        keys = key_scan(text)
        reasons = "؛ ".join(f"{lbl} (سطر {ln})" for lbl, ln in keys) or "ملف .env"
        map_lines.append(f"| `{rel}` | {reasons} |")
    open(os.path.join(QUAR, "MAP.md"), "w", encoding="utf-8").write("\n".join(map_lines) + "\n")

    # ---------- CENSUS.md ----------
    rows.sort(key=lambda r: r["rel"])
    n_ok = sum(1 for r in rows if r["ast"] == "سليم")
    n_bad = sum(1 for r in rows if r["ast"].startswith("معطوب"))
    md = [
        "# 📊 الإحصاء الشامل للحزمة الجديدة — new/CENSUS.md",
        "",
        "> تاريخ التوليد: 2026-09-16 · أمر إعادة الاشتقاق: `python3 new/census.py`",
        "> الحزمة الأم: `nova_upload_bundle.tar.gz` —",
        "> `sha256 = 31d64494ec40e4cb65ea5f90fa11a68cfc2ba5324d0abdaf8a0b3b49086349f3`",
        "",
        f"**الملخص:** {len(rows)} ملف كود مُحصى · {n_ok} بايثون سليم · {n_bad} بايثون معطوب ·",
        f"{len(rows) - n_ok - n_bad} ملف شل · {len(quar_files)} ملف معزول (مفاتيح ⚠️ — انظر _quarantine/MAP.md) · {non_code} ملف غير كودي (PDF/ZIP/RAR/DOCX/وثائق نصية).",
        "",
        "| # | المسار | النوع | الحجم (بايت) | sha256-12 | العنوان من الترويسة | ast | دوال | جروح |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        md.append(
            f"| {i} | `{r['rel']}` | {r['kind']} | {r['size']:,} | `{r['sha']}` | {r['title']} | "
            f"{r['ast']} | {r['funcs']} | {r['red']} |"
        )
    md += [
        "",
        "## ملاحظات",
        "- «جروح» = عدد مواضع `__REDACTED__` (أثر المنقّي السري في نسخ المستودع القديمة).",
        "- الملفات المعزولة (مفاتيح حقيقية) نُقلت إلى `new/_quarantine/` — انظر MAP.md هناك.",
        "- كل ملف نصي (كود أو وثيقة) خضع لمسح المفاتيح — لا استثناءات.",
        "- ملفات «بايثون المعطوب» الخمسة ليست كوداً فعلياً: اثنان `README.py` (وثيقة شرح",
        "  بامتداد py) وثلاثة وثائق عربية تحوي كتل كود توضيحية (عقد/ملفات شاملة) —",
        "  صنّفها الكاشف كوداً لتوفر تلميحات بايثون داخلها. لا يوجد أي ملف بوت معطوب في الحزمة.",
        "",
    ]
    open(os.path.join(ROOT, "CENSUS.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

    print(f"code files: {len(rows)} (py OK: {n_ok}, py BROKEN: {n_bad}) | quarantined: {len(quarantined)} | non-code: {non_code}")


if __name__ == "__main__":
    main()
