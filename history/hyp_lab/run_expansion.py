# -*- coding: utf-8 -*-
"""L0012 — جولة التوسعة: القواطع الاتجاهية (F‑213) على العملات غير الممتحنة — فريم 4h
(بأمر القائد 2026-09-19: «جولة على العملات غير الممتحنة بفريم الأربع ساعات»).

النصوص الملزمة:
  • نفس بروتوكول L0009 حرفاً: نفس الشبكة (16 قاطعاً × خروجان = 32 تركيبة لكل رمز)،
    نفس النوافذ (دفء 2023‑06‑01 | تدريب 2023‑09‑01→2024‑12‑31 | اختبار 2025‑01‑01→2026‑08‑31)،
    نفس البوابة (net>0 AND PF≥1.3 AND trades≥100)، نفس التكاليف 0.13%/طرف، طول فقط، اسمي 20$ (محفظة التجربة 1000$).
  • الفرق الوحيد: قائمة الرموز — التسعة غير الممتحنة من الأرشيف الرسمي (الممتحنون الثمانية
    في L0009/L0010 هم: BTC ETH SOL XLM LINK GRAM RENDER FIL)، والفريم 4h فقط
    (1h مدفون موثقاً بحكم D‑0038 فلا يُعاد فتحه بلا أمر جديد).
  • الإخراج إلى history/research/hyp_lab_out/L0012/ — لا مساس بإيداع L0009 ولا محرك nova_v8.
  • الكاناري بوابة إلزامية (يشغّله السائق الأب run_breakers.main داخل العملية).

التشغيل (من جذر المستودع):
    python3 history/hyp_lab/run_expansion.py
المصدر: بثّ كل رمز من raw.githubusercontent عند البصمة المثبتة REF (صفر قرص).
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_breakers as RB  # noqa: E402

REF = "b27052e87d9c810ce401c4f64ec359944b164eaf"   # رأس main لحظة الأمر (2026-09-19)
# المسح التشخيصي (probe_coverage.py، دليله في L0012/coverage_probe.csv):
#   HNTUSDT مستبعد بدليل مقاس: بياناته في الأرشيف تنتهي 2022-10-14 ⇒ صفر شمعة في
#   نافذتي التدريب والاختبار ⇒ «غير مقاس» لا «فاشل» (القسم 10).
#   TONUSDT مدفوع بتوثيق انحراف نوافذه: التدريب جزئي 874 شمعة (بياناته تبدأ 2024-08-08)
#   والاختبار ينتهي 2026-06-30 (نهاية بياناته) — يُقاس ويُوثَّق الانحراف، لا يُخفى.
SYMBOLS = "ATOMUSDT,BNBUSDT,DOGEUSDT,IMXUSDT,PEPEUSDT,SHIBUSDT,TONUSDT,VETUSDT"

RB.TF_OUT = {"4h": "L0012"}                      # مجلد إخراج الجولة الجديدة


def main() -> int:
    sys.argv = ["run_expansion", "--tf", "4h", "--source", "stream", "--ref", REF,
                "--symbols", SYMBOLS, "--trades"]
    return RB.main()


if __name__ == "__main__":
    raise SystemExit(main())
