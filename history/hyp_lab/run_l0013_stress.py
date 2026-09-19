# -*- coding: utf-8 -*-
"""L0013 — جولة الضغط على نجوم التوسعة (عابرو L0012 على 4h) — بأمر القائد 2026-09-19.

المنهج: نفس محاور ضغط L0010 بتطبيقها على السبع العابرة من L0012 (ATOM · DOGE · IMX ·
PEPE · SHIB · TON · VET)، والتركيبات **مقفلة من إيداع L0012** (بلا أي إعادة اختيار):
  matrix  : الـ32 خلية على نافذة الامتحان — يفصل الخلية المنتقاة من الشبكة
  slip    : انزلاق مجهد 0.10% و0.30% لكل طرف بدل الأساس 0.03% (العمولة 0.10% ثابتة)
  blind   : النافذة العمياء 2021-09-01→2023-08-31 — لكل رمز بياناته تسمح؛ وغير الممكن يوثق
  plateau : الجوار ±20% حول ثنائية المزدوج (تسليح 0.0025 × قفل 0.0045) = 9 خلايا لكل رمز

لا يُلمس محرك nova_v8 ولا إيداع L0009/L0012. المخرجات في
history/research/hyp_lab_out/L0013/ بأشكال ملفات L0010 حرفًا (مقارنة مباشرة ممكنة).
TON: تدريب جزئي مثبت سابقًا (874 شمعة) — يوثق في التقرير ولا يخفى.

    python3 history/hyp_lab/run_l0013_stress.py --source stream --ref <sha> [--trades]
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_stress as RS  # noqa: E402

REF = "a52026f94c775ff8a744ea3ba25f91807c084dee"      # رأس main لحظة الأمر (2026-09-19)
SYMBOLS = "ATOMUSDT,DOGEUSDT,IMXUSDT,PEPEUSDT,SHIBUSDT,TONUSDT,VETUSDT"
# BNB مستبعد: لم يعبر بوابة L0012 (net=-1379.49$ · PF 0.89) — لا يُضغط ما سقط.
RS.SYMBOLS = [s for s in SYMBOLS.split(",")]
RS.OUT_ROOT = RS.HIST / "research" / "hyp_lab_out" / "L0013"


def main() -> int:
    # مصدر المقفلات: إيداع L0012 (نفس عمود `sel_*` وشكل ملف L0009) — يفرضه القرص قبل الإقلاع.
    locked_dir = RS.HIST / "research" / "hyp_lab_out" / "L0012"
    src = locked_dir / "F_213" / "all_symbols_test.csv"
    dst_dir = RS.HIST / "research" / "hyp_lab_out" / "L0009-tf4h" / "F_213"
    if not src.exists():
        raise SystemExit(f"مختارات L0012 غير موجودة: {src}")
    dst_dir.mkdir(parents=True, exist_ok=True)
    (dst_dir / "all_symbols_test.csv").write_bytes(src.read_bytes())

    sys.argv = ["run_l0013_stress", "--tf", "4h", "--source", "stream", "--ref", REF,
                "--symbols", SYMBOLS, "--mode", "all"]
    if "--trades" not in sys.argv:
        sys.argv.append("--trades")
    return RS.main()


if __name__ == "__main__":
    raise SystemExit(main())
