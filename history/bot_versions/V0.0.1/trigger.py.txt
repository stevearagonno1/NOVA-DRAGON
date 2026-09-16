"""
NOVA v5 — محفّز الدخول (مُبسّط)
================================
استراتيجية مبسّطة: الدخول يعتمد حصراً على فلترين أساسيين فقط:

  1) KAMA trend filter (indicators.AnchoredKAMA) — اتجاه + قوة.
  2) Naive-Bayes classifier (nb.NaiveBayes) — posterior صف Bull ≥ 0.55 (Testnet).

أُزيل بالكامل مسار Sweep → MSS → FVG وكل شروط المحاذاة الثانوية
(Displacement gate, FVG Zone-Tap, Liquidity Sweep) من هذا الملف ومن
engine.py. لم يعد هذا الملف يقدّم أي منطق دخول؛ الفحوص الفعلية تتم
داخل engine._run_pipeline عبر KAMA + Naive-Bayes فقط.
"""

from __future__ import annotations
