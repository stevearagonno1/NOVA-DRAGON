"""
NOVA v5 — محفّز الدخول (Forward-Profiling build)
=================================================
⚗️ PHASE: FORWARD PROFILING / EXHAUSTIVE LOGGING

استراتيجية الدخول في هذا البناء:
  1) KAMA trend filter (indicators.AnchoredKAMA) — المحفّز_CORE الوحيد.
     أي KAMA signal مولّد (اتجاه + قوة ≥ الحد) يُنفَّذ فوراً على Testnet.
  2) Naive-Bayes — ⬅ في هذا الطور لم يعد فلترًا: أصبح مُسجِّلًا (observer).
     يُحسب الـ posterior ويُطبع بدقة كاملة (console + Telegram + journal.txt)
     لكنه لا يرفض شيئًا. NB_MIN_ENTRY_PROB = 0.0 (انظر nb.py).
     NB's exact score and class ride along inside every trade's anatomy so the
     journal can later answer: "does the old 55% floor actually add edge?"

للعودة إلى الفلترة القديمة: nb.ZERO_THRESHOLD_MODE = False
(أو Config.nb_zero_threshold = False) — سيعيد engine تطبيق شرط Bull ≥ 0.55
وفيتو Diverged تلقائياً مع طباعة سطر REJECTED لكل إشارة مرفوضة.

أُزيل بالكامل مسار Sweep → MSS → FVG وكل شروط المحاذاة الثانوية
(Displacement gate, FVG Zone-Tap, Liquidity Sweep) من هذا الملف ومن
engine.py. لم يعد هذا الملف يقدّم أي منطق دخول؛ الفحوص الفعلية تتم
داخل engine._run_pipeline عبر KAMA فقط (+ NB تسجيلي).
"""

from __future__ import annotations
