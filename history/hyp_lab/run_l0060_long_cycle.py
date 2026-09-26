# -*- coding: utf-8 -*-
"""L0060 — قياس دورة التراكم كما بُنيت. لا تطوير.

مكتوب قبل أي رقم ربح للوحدة.

السقف 24. لا يُتجاوز.
  مرحلة 0 لا تُحسب. فرق أكبر من 0.5$ يوقف الجولة.
  مرحلة أ لا تُحسب. مخالفة تعبئة واحدة في سعر السوق توقف الجولة. لا إصلاح.
  ب (4 من 12): بلا قيد مناخي، الفترتان، 0.115% ثم 0.130%. المقاعد 5–12 لا تُملأ بعد الرؤية.
  ج (8 من 8) بهذا الترتيب ثم توقف:
    1–2 الهابط فقط، الفترتان، 0.115%.
    3–4 الشراء والاحتفاظ برأس مال الذروة نفسه، الفترتان، 0.115%.
    5–8 عشوائي، البذرتان 110060 و210060، الفترتان، على الأفضل.
  د (4 من 4): البذرتان 310060 و410060، الفترتان. البذرة 510060 لا تتسع. لم تُقَس.
  لذلك صف «أسعد بذرة من خمس» لا يكتمل. لا اعتماد حتى لو ربحت الباقي.

الأفضل = أعلى عائد مئوي على ذروة التزامن في الحكم. التعادل للمسار بلا قيد، كما صُممت.
الهابط عند 0.130% لم يُحجز مقعد له. إن صار هو الأفضل فصف 0.130% يبقى لم يُقَس.

انحرافات مكتوبة قبل الرؤية، لا بعدها:
  - الكود يعيد قائمة فارغة لغير BTC وBNB وSOL وLINK. الورقة قالت 17. تعديل nova_v8 ممنوع.
    القياس على الأربع المبرمجة. الثلاث عشرة الأخرى لم تُقَس.
  - رأس المال المبرمج 1000$ للعملة، لا 20$. الأوزان 0.15/0.25/0.30/0.30.
  - NOVA_LC_V2 افتراضه 1: نطاق 8% بلا شرط الاستقرار. لا أطفئه.
  - الكلفة تُوحَّد في الذاكرة: COMMISSION=0.00115 وSLIPPAGE=0، فتدفع كل جهة 0.115% مرة.
    ثوابت الملف 0.10% + 0.03% لا تُستخدم في المقارنة.
  - الفترتان تشغيلان مستقلان. صفقة التسخين قبل بداية الفترة لا تُحسب. لا صفقة في الفترتين.
    الإغلاق عند آخر شمعة هو قاعدة الوحدة (نهاية-العينة)، لا خروجًا اخترعته.
  - سعر السوق للحارس: افتتاح الدخول، وسعر الخروج الخام. الحارس بكلفة 0.
    سعر الدخول بعد الانزلاق أثر كلفة، لا مخالفة سوق، إن بقي الافتتاح داخل الشمعة.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/l0060")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "tools"))

os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0060"
OUT.mkdir(parents=True, exist_ok=True)
FRAMES = pathlib.Path.home() / ".cache" / "l0060_h4"
FRAMES.mkdir(parents=True, exist_ok=True)
CACHE4 = pathlib.Path.home() / ".cache" / "l0046_frames"

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
COST = 0.00115
COST_130 = 0.00130
CAP = 24
SEEDS = (110060, 210060, 310060, 410060, 510060)
ALLOWED = ("BTCUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT")
BASE_COINS = (
    "ATOMUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "FILUSDT", "GRAMUSDT",
    "IMXUSDT", "LINKUSDT", "PEPEUSDT", "RENDERUSDT", "SHIBUSDT", "SOLUSDT",
    "TONUSDT", "VETUSDT", "XLMUSDT",
)
LEDGER: list[dict] = []

RULE = {
    "written_before_long_cycle_profit": True,
    "cap": CAP,
    "B": "4: بلا قيد × فترتين × كلفتين. لا ملء بعد الرؤية.",
    "C_order": ["هابط اختيار", "هابط حكم", "احتفاظ اختيار", "احتفاظ حكم",
                "عشوائي 110060 اختيار", "عشوائي 110060 حكم",
                "عشوائي 210060 اختيار", "عشوائي 210060 حكم"],
    "D": "310060 و410060 في الفترتين. 510060 لم يُقَس.",
    "better": "أعلى عائد % على ذروة التزامن في الحكم. التعادل للمسار بلا قيد.",
    "windows": "مستقلتان. التسخين لا يُحسب. لا ازدواج.",
    "cost": "COMMISSION=الكلفة وSLIPPAGE=0 في الذاكرة. لا تعديل لملف.",
    "universe": "الأربع المبرمجة فقط. 17 لم تُقَس لأن الكود يرفضها والتعديل ممنوع.",
    "seeds": list(SEEDS),
    "fill_stop": "سعر سوق خارج [low, high] يوقف. لا إصلاح.",
}


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def log(name: str, window: str, phase: str) -> None:
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف {CAP}")
    LEDGER.append({"#": len(LEDGER) + 1, "المرحلة": phase, "القياس": name, "الفترة": window})
    print(f"  [{len(LEDGER)}/{CAP}] {phase} {name} {window}", flush=True)


def load_l56():
    src = (ROOT / "history" / "hyp_lab" / "run_l0056_widen_book.py").read_text(encoding="utf-8")
    src = src.replace('pathlib.Path("/home/user/l0056")', 'pathlib.Path("/home/user/l0060")')
    src = src.replace('if __name__ == "__main__":', "if False:")
    path = pathlib.Path("/tmp/r56_l0060.py")
    path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("r56_l0060", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["r56_l0060"] = mod
    spec.loader.exec_module(mod)
    mod.OUT = OUT
    return mod


def phase0(R56) -> None:
    print("══ مرحلة 0 ══", flush=True)
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    raw = can.stdout
    cj = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
    dump("canary.json", cj)
    print(f"  كاناري: {cj.get('canary')} net={cj.get('got', {}).get('net')}", flush=True)
    if cj.get("canary") != "ok":
        raise SystemExit("الكاناري ليس ok")
    R56.prepare()
    R56.build_regimes(R56.archive_symbols())
    R56.use_syms(R56.archive_symbols())
    enabled, _ = R56.load_frozen_map()
    fp = hashlib.sha256((ROOT / "history/research/hyp_lab_out/L0051/routing_map.json").read_bytes()).hexdigest()
    if not fp.startswith("14df873e"):
        raise SystemExit(f"بصمة الخريطة خالفت: {fp[:16]}")
    rec, _ = R56.run_book("p0_c00115_JUD", "p0_c00115_JUD", R56.routed(enabled), R56.WINNER,
                          JUD_S, JUD_E, "حكم", COST, False, "0")
    if abs(rec["net"] - 33.24) > 0.5 or rec["trades"] != 464:
        raise SystemExit(f"حكم المحفظة خالف الورقة: {rec['net']} / {rec['trades']}")
    rec, _ = R56.run_book("p0_c00115_SEL", "p0_c00115_SEL", R56.routed(enabled), R56.WINNER,
                          DEC_S, DEC_E, "اختيار", COST, False, "0")
    if abs(rec["net"] - 45.66) > 0.5 or rec["trades"] != 328:
        raise SystemExit(f"اختيار المحفظة خالف الورقة: {rec['net']} / {rec['trades']}")
    # الشراء والاحتفاظ كما قيس في L0046: 20$ و0.13% على سلة الأساس
    # صيغة L0046 حرفيًا: 20$ · 0.13% · أول افتتاح وآخر إغلاق في نافذة 4h الرسمية
    tot = 0.0
    n = 0
    for sym in BASE_COINS:
        w = R56.R46.frames(sym)
        w = w[(w.index >= JUD_S) & (w.index <= JUD_E)]
        if len(w) < 2:
            continue
        e = float(w["open"].iloc[0]) * (1 + 0.0013)
        x = float(w["close"].iloc[-1]) * (1 - 0.0013)
        tot += 20.0 * (x / e - 1.0)
        n += 1
    tot = round(tot, 2)
    print(f"  احتفاظ الحكم: {tot} / {n} عملة · المرجع −73.29", flush=True)
    if abs(tot - (-73.29)) > 0.5:
        raise SystemExit(f"الشراء والاحتفاظ خالف الورقة: {tot}")
    print("  ✅ المرحلة 0 طابقت", flush=True)
    dump("phase0.json", {"judgement": "33.24/464", "selection": "45.66/328", "buyhold_judgement": tot, "buyhold_n": n})


if __name__ == "__main__":
    dump("acceptance_rule_l0060.json", RULE)
    phase0(load_l56())
