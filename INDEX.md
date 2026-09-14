# فهرس المستودع — NOVA V8

الهيكل من `tools/organize_incoming.py`. المكرر الحرفي (نفس sha256) شُطب، وغيره نُقل بمساره — ولا معلومة ضاعت.
آخر تنظيم: 2026-09-14 | الملفات الواردة: 523 | منقولة: 332 | محذوفة لتطابقها: 191

| `library/indicators` | مكتبة المؤشرات: 129 ملفاً (مؤشرات/0..7) — خامات أفكار الفلاتر |
| `docs/library` | 14 ملفاً مرجعياً (أدلة ومؤشرات نصية) |

## خريطة المجلدات

| المجلد | ما فيه |
|---|---|
| `nova_v8` | الكود المجمّد للمحرك — لا يُعدَّل إلا بقرار D |
| `docs/constitution` | دستورك: الأعلى والتشغيلي |
| `docs/designs` | التصاميم: محرك الواجهة، المخطط الشامل، دليل الرموز، عقد الترجمة |
| `docs/reports` | تقارير التدقيق والنتائج والمراجعات |
| `docs/conversations` | سجلات المحادثات ورسائل التوجيه (ذاكرة القرارات) |
| `docs/lanes` | الحارات: كل تجربة = ملف فيه عقده وحكمه |
| `hypotheses` | الفرضيات: الـ212 + النخبة + لوحة الخط + عقد المصنع |
| `bot_versions` | كل نسخ البوت القديمة — تاريخ محفوظ، لا كود حيّ |
| `data` | باركيه صغير أعيد منه حساب النتائج |
| `research` | نتائج التشغيل الحقيقية (الأرشيف) |
| `tools` | أدواتنا: الفحص، البروبي، جدول الأرشيف، المنظّم |
| `crypto_archive` | البيانات الضخمة (BTC 1m لخمس سنوات) |
| `code_drafts` | مسودات كود مستقلة ليست من المحرك |
| `archive` | القديم وغير المطابق — محفوظ لا مربوط |

## كل ملف بمكانه

### `(أرشيف النتائج — على مستوى المجلد)` (27)

- `research/nova_v8_out/ATOMUSDT/` — 13 ملف (370K)
- `research/nova_v8_out/BNBUSDT/` — 13 ملف (377K)
- `research/nova_v8_out/BTCUSDT_2y/` — 12 ملف (228K)
- `research/nova_v8_out/FILUSDT/` — 13 ملف (338K)
- `research/nova_v8_out/IMXUSDT/` — 13 ملف (566K)
- `research/nova_v8_out/LINKUSDT/` — 13 ملف (330K)
- `research/nova_v8_out/RENDERUSDT/` — 13 ملف (288K)
- `research/nova_v8_out/SOLUSDT/` — 13 ملف (374K)
- `research/nova_v8_out/TONUSDT/` — 13 ملف (258K)
- `research/nova_v8_out/VETUSDT/` — 13 ملف (294K)
- `research/nova_v8_out/XLMUSDT/` — 13 ملف (169K)
- `research/nova_v8_out/d5y/` — 240 ملف (2.3M)
- `research/nova_v8_out/diag_fast/` — 12 ملف (5K)
- `research/nova_v8_out/diag_grid/` — 12 ملف (4K)
- `research/nova_v8_out/diag_grid2/` — 12 ملف (4K)
- `research/nova_v8_out/diag_grid3/` — 12 ملف (5K)
- `research/nova_v8_out/diag_qg_off/` — 12 ملف (5K)
- `research/nova_v8_out/diag_qg_on/` — 12 ملف (5K)
- `research/nova_v8_out/f5y/` — 264 ملف (22.1M)
- `research/nova_v8_out/sf/` — 72 ملف (871K)
- `research/nova_v8_out/test_at_atr/` — 12 ملف (16K)
- `research/nova_v8_out/test_at_wide/` — 12 ملف (12K)
- `research/nova_v8_out/test_don_bull/` — 12 ملف (94K)
- `research/nova_v8_out/test_don_c/` — 12 ملف (67K)
- `research/nova_v8_out/test_don_chop/` — 12 ملف (14K)
- `research/nova_v8_out/test_don_filter/` — 12 ملف (153K)
- `research/nova_v8_out/test_don_macro/` — 12 ملف (70K)

### `.` (10)

- `.gitignore` (1K) 
- `AGENTS.md` (4K) — NOVA-DRAGON — عقود العمل للوكلاء (اقرأ هذا أولاً)
- `NOVA_v8_bundle.zip` (101K) 
- `START.txt` (1K) — NOVA_V8 — خطوات ما بعد فك الضغط (Termux) ===
- `bot_output.log` (1K) — nohup: ignoring input
- `fetch_archive.py` (4K) — !/usr/bin/env python3
- `requirements.txt` (1K) — NOVA_V8 — إصدارات المرجع المُنتِجة للأرقام الموثقة (شغّل مساراتك عليها لتفادي فروق ULP).
- `الملف_الشامل_للوكيل_الجديد.txt` (64K) — ═══════════════════════════════════════════════════════════════════════
- `حزمة_الوكيل_كاملة.txt` (309K) — الجزء: العقد (اقرأه أولاً) =========================
- `نتائج_الاستراتيجيات_الكاملة.txt` (16K) — ═══════════════════════════════════════════════════════════════

### `archive/code_snapshot` (1)

- `archive/code_snapshot/PACK_README.txt` (1K) — حزمة التوثيق الكاملة — مشروع NOVA_V8

### `archive/code_snapshot/docs` (2)

- `archive/code_snapshot/docs/NOVA_V8_ORIGINAL_BUNDLE.txt` (309K) — الجزء: العقد (اقرأه أولاً) =========================
- `archive/code_snapshot/docs/PROJECT_LOG.txt` (14K) — ════════════════════════════════════════════════════════════════════

### `archive/code_snapshot/nova_v8` (8)

- `archive/code_snapshot/nova_v8/README.md` (12K) — NOVA_V8 — Research-first adaptive quant trading bot
- `archive/code_snapshot/nova_v8/adaptive_trend.py` (13K) — """Adaptive Trend sleeve — spec 8.2 "الاتجاه + الارتداد إلى القيمة" (trend +
- `archive/code_snapshot/nova_v8/config.py` (24K) — """NOVA_V8 — central configuration (single source of truth).
- `archive/code_snapshot/nova_v8/feeds.py` (9K) — """Module — data ingestion + feature-matrix cache for research.
- `archive/code_snapshot/nova_v8/fetch_archive.py` (2K) — !/usr/bin/env python3
- `archive/code_snapshot/nova_v8/requirements.txt` (1K) — numpy>=1.24
- `archive/code_snapshot/nova_v8/sweep_engine.py` (10K) — !/usr/bin/env python3
- `archive/code_snapshot/nova_v8/telegram_notify.py` (2K) — """Module — Telegram notifications for the research phase.

### `archive/code_snapshot/nova_v8/tests` (2)

- `archive/code_snapshot/nova_v8/tests/__init__.py` (1K) 
- `archive/code_snapshot/nova_v8/tests/selftest.py` (14K) — """Self-test: run the full research engine on a small synthetic archive to catch

### `archive/research_variants/nova_v8_out` (2)

- `archive/research_variants/nova_v8_out/data_quality_report.txt` (1K) — NOVA_V8 — تقرير جودة البيانات / Data Quality
- `archive/research_variants/nova_v8_out/portfolio_risk_audit.txt` (1K) — NOVA_V8 — Portfolio Risk Audit / حماية المحفظة

### `bot_versions` (20)

- `bot_versions/HFT_MASTER_KNOWLEDGE_BASE.md` (139K) — MASTER KNOWLEDGE BASE — Zero-Wait Tick Execution Edge Library
- `bot_versions/NOVA (2).txt` (249K) — !/usr/bin/env python3
- `bot_versions/NOVA (3).py` (249K) — !/usr/bin/env python3
- `bot_versions/NOVA (3).txt` (249K) — !/usr/bin/env python3
- `bot_versions/NOVA (4).txt` (208K) — !/usr/bin/env python3
- `bot_versions/NOVA.1.txt` (138K) — !/usr/bin/env python3
- `bot_versions/NOVA.ZERO.WAIT.py` (110K) — !/usr/bin/env python3
- `bot_versions/NOVA.py` (189K) — !/usr/bin/env python3
- `bot_versions/NOVA.py.txt` (139K) — !/usr/bin/env python3
- `bot_versions/NOVA_3.txt` (162K) — !/usr/bin/env python3
- `bot_versions/NOVA_4.txt` (187K) — !/usr/bin/env python3
- `bot_versions/Order&Breake.txt` (67K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `bot_versions/check.py` (6K) — """حاضنة تشغيل غير متصلة (V7.0): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي."""
- `bot_versions/check.txt` (16K) — """حاضنة تشغيل غير متصلة: تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.
- `bot_versions/hft_edge_extraction.md` (68K) — Reverse-Engineered Trading Logic — Distilled for a Tick-Based Binance Spot Engine
- `bot_versions/phantom flow.txt` (46K) — //@version=6
- `bot_versions/start.sh` (5K) — export BINANCE_ENV='testnet'
- `bot_versions/start_zero.sh.txt` (1K) — !/bin/bash
- `bot_versions/خطة_التنفيذ النهائيه_NOVA_v5.md` (18K) — 🗂 خطة التنفيذ الشاملة — NOVA v5 (وثيقة تخطيط فقط — لا كود، بانتظار الموافقة)
- `bot_versions/خطة_التنفيذ_NOVA_v5.md` (17K) — 🗂 خطة التنفيذ الشاملة — NOVA v5 (وثيقة تخطيط فقط — لا كود، بانتظار الموافقة)

### `bot_versions/1` (11)

- `bot_versions/1/NOVA (2).py` (322K) — !/usr/bin/env python3
- `bot_versions/1/NOVA (3).py` (374K) — !/usr/bin/env python3
- `bot_versions/1/NOVA.py` (291K) — !/usr/bin/env python3
- `bot_versions/1/NOVA.py.txt` (249K) — !/usr/bin/env python3
- `bot_versions/1/bot_output.log` (177K) — [2026-08-30 01:04:43] لا توجد ذاكرة سابقة؛ بداية جديدة
- `bot_versions/1/check (2).py` (5K) — """حاضنة تشغيل غير متصلة (V6.2): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي."""
- `bot_versions/1/check.py` (5K) — """حاضنة تشغيل غير متصلة (V6.1): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي."""
- `bot_versions/1/check.py.txt` (5K) — """حاضنة تشغيل غير متصلة: تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي."""
- `bot_versions/1/start (2).sh` (3K) — export BINANCE_ENV='testnet'
- `bot_versions/1/start.sh` (2K) — export BINANCE_ENV='testnet'
- `bot_versions/1/start.sh.txt` (1K) — export BINANCE_ENV='testnet'

### `bot_versions/NOVA` (28)

- `bot_versions/NOVA/, (2).txt` (23K) — coding: utf-8 -*-
- `bot_versions/NOVA/,.txt` (8K) — import requests
- `bot_versions/NOVA/1 (2).txt` (113K) — !/usr/bin/env python3
- `bot_versions/NOVA/9.txt` (104K) — !/usr/bin/env python3
- `bot_versions/NOVA/999.txt` (100K) — !/usr/bin/env python3
- `bot_versions/NOVA/9_3.txt` (108K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (1).py.txt` (98K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (10).py.txt` (91K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (13).py.txt` (211K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (14).py.txt` (109K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (15).py.txt` (115K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (2) (2) (2).txt` (111K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (2) (2).txt` (112K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (2).py.txt` (98K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (23).py.txt` (171K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (25).py.txt` (77K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (26).py.txt` (88K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (3) (2).txt` (119K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (3).py.txt` (97K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (4).py.txt` (97K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (5).py.txt` (98K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (5).txt` (113K) — !/usr/bin/env python3
- `bot_versions/NOVA/NOVA (6).py.txt` (109K) — !/usr/bin/env python3
- `bot_versions/NOVA/bot.txt` (108K) — !/usr/bin/env python3
- `bot_versions/NOVA/start (1).sh.txt` (1K) — export BINANCE_ENV='testnet'
- `bot_versions/NOVA/start (2).sh.txt` (1K) — !/bin/bash
- `bot_versions/NOVA/super_bot.txt` (53K) — coding: utf-8 -*-
- `bot_versions/NOVA/،،.txt` (4K) — الغرض والأهداف:

### `bot_versions/V0.0.1` (5)

- `bot_versions/V0.0.1/engine.py.txt` (25K) — """
- `bot_versions/V0.0.1/execution.py.txt` (4K) — """
- `bot_versions/V0.0.1/nb.py.txt` (8K) — """
- `bot_versions/V0.0.1/telegram.py.txt` (20K) — """
- `bot_versions/V0.0.1/trigger.py.txt` (1K) — """

### `bot_versions/V2` (10)

- `bot_versions/V2/README.md` (3K) — 🤖 NOVA v5 — ZERO-WAIT QUANT ENGINE
- `bot_versions/V2/config.py` (9K) — """
- `bot_versions/V2/data.py` (6K) — """
- `bot_versions/V2/indicators.py` (11K) — """
- `bot_versions/V2/main.py` (16K) — from __future__ import annotations
- `bot_versions/V2/quant.py` (4K) — """
- `bot_versions/V2/requirements.txt` (1K) — aiohttp>=3.9
- `bot_versions/V2/risk.py` (2K) — """
- `bot_versions/V2/scoring.py` (2K) — """
- `bot_versions/V2/start.sh` (1K) — !/bin/bash

### `bot_versions/V3` (4)

- `bot_versions/V3/engine.py` (54K) — """
- `bot_versions/V3/nb.py` (10K) — """
- `bot_versions/V3/telegram.py` (29K) — """
- `bot_versions/V3/trigger.py` (1K) — """

### `bot_versions/البوت الامن النهائي` (3)

- `bot_versions/البوت الامن النهائي/engine.py` (28K) — """
- `bot_versions/البوت الامن النهائي/nb.py` (10K) — """
- `bot_versions/البوت الامن النهائي/trigger.py` (4K) — """

### `bot_versions/بوت نهائي` (2)

- `bot_versions/بوت نهائي/NOVA.1.txt` (228K) — !/usr/bin/env python3
- `bot_versions/بوت نهائي/NOVA.txt` (205K) — !/usr/bin/env python3

### `bot_versions/تداول طويل المدى` (5)

- `bot_versions/تداول طويل المدى/claude.txt` (9K) — خطة شاملة لموازنة البوت وتحسين أدائه
- `bot_versions/تداول طويل المدى/gemini.txt` (4K) — لماذا لا يرى البوت فرصاً في السوق حالياً؟
- `bot_versions/تداول طويل المدى/gpt.txt` (10K) — المشكلة التي تصفها شائعة في أنظمة السكالبينج: عندما تجمع عدة شروط ثنائية صارمة AND، تصبح ا
- `bot_versions/تداول طويل المدى/kimi.txt` (6K) — المشكلة التي تواجهك هي **مشكلة التوازن بين الدقة والتردد (Precision vs. Frequency)**، وهي 
- `bot_versions/تداول طويل المدى/qwen.txt` (10K) — مشكلتك كلاسيكية جداً في تطوير بوتات التداول الخوارزمية، وتُعرف بمعضلة **"الموازنة بين الدق

### `bot_versions/تداول قصير و سريع` (4)

- `bot_versions/تداول قصير و سريع/claued.txt` (16K) — خطة تحسين شاملة لبوت NOVA
- `bot_versions/تداول قصير و سريع/gpt.txt` (12K) — نعم، ويمكن تحسين NOVA بشكل واضح، لكن توجد مفاضلة أساسية: إذا أردته "رشاش صفقات"، فلا يمكن 
- `bot_versions/تداول قصير و سريع/kimi.txt` (9K) — إليك تحليلاً تشخيصياً وحلولاً عملية لمشاكل بوت NOVA. المشكلة ليست في البوت ذاته، بل في **ف
- `bot_versions/تداول قصير و سريع/qwen.txt` (10K) — تحليل عميق وممتاز للبوت الذي بنيته (NOVA). البنية التحتية (Infrastructure) التي وصفتها (As

### `code_drafts` (17)

- `code_drafts/__init__.py.txt` (1K) — """NOVA_V8_QUANT_LAB — institutional async quant engine for Termux edge."""
- `code_drafts/backtest_sk.py` (3K) — import pandas as pd, numpy as np
- `code_drafts/config.py.txt` (4K) — """Central configuration — all environment-sensitive values live here."""
- `code_drafts/data_fetcher.py.txt` (7K) — !/usr/bin/env python3
- `code_drafts/engine.py.txt` (18K) — """NOVA_V8 orchestrator — one analytical pipeline for BOTH modes.
- `code_drafts/execution.py.txt` (20K) — """Modules 8 & 9 — micro-execution mechanics + hybrid in-memory exit engine.
- `code_drafts/feeds.py.txt` (7K) — """Module 1 — dual-mode data ingestion engine.
- `code_drafts/indicators.py.txt` (10K) — """Module 2 — pure vectorized indicator math (numpy/pandas, non-repainting).
- `code_drafts/main.py.txt` (1K) — """NOVA_V8_QUANT_LAB — entrypoint.
- `code_drafts/microstructure.py.txt` (5K) — """Module 5 — microstructure execution triggers (the catalysts).
- `code_drafts/orderflow.py.txt` (7K) — """Module 4 — online Naive-Bayes order-flow classifier + CVD engine.
- `code_drafts/regime.py.txt` (1K) — """Module 3 — Market Regime Detection Engine.
- `code_drafts/risk.py.txt` (1K) — """Module 7 — dynamic position sizing + the Symbol Governor."""
- `code_drafts/sizing.py` (2K) — import math
- `code_drafts/strategies.py.txt` (4K) — """Module 6 — Strategy Tournament Engine (multi-trigger dispatcher).
- `code_drafts/telegram_bot.py.txt` (6K) — """Modules 11 & 12 — non-blocking Telegram interface.
- `code_drafts/telemetry.py.txt` (7K) — """Module 10 — Master Telemetry Database (the Quant Matrix).

### `data` (4)

- `data/BNBUSDT_1m.parquet` (2.8M) 
- `data/BTCUSDT_1m.parquet` (4.8M) 
- `data/LINKUSDT_1m.parquet` (2.6M) 
- `data/SOLUSDT_1m.parquet` (2.8M) 

### `data/archive` (3)

- `data/archive/BTCUSDT_1m.parquet` (1.6M) 
- `data/archive/SOLUSDT_1m.parquet` (1.6M) 
- `data/archive/XLMUSDT_1m.parquet` (1.6M) 

### `docs` (8)

- `docs/ARCHIVE-VERIFIED-2026-09-14.md` (9K) — أرشيف الأدلة — تدقيق 14 سبتمبر 2026 (874 ملفاً / 72 تجربة)
- `docs/AUDIT-2026-09-13.md` (5K) — تدقيق 2026‑09‑13 — ما وجده العقل حين أعاد الاشتقاق بدل القراءة
- `docs/BRAIN.md` (11K) — BRAIN — ميثاق «العقل» (المحادثة التنسيقية العليا)
- `docs/DECISIONS.md` (8K) — DECISIONS — سجل القرارات الملزمة (Append‑only)
- `docs/EXECUTION_REPORT.md` (4K) — تقرير تنفيذ — NOVA_V8 adaptive_trend sweep (477→1920)
- `docs/NOVA_V8_ORIGINAL_BUNDLE.txt` (309K) — الجزء: العقد (اقرأه أولاً) =========================
- `docs/PROJECT_LOG.txt` (17K) — ════════════════════════════════════════════════════════════════════
- `docs/sweep_run.log` (176K) — البحث الشامل: adaptive_trend — 1920 تركيبة × نافذتين (تدريب+اختبار)

### `docs/constitution` (2)

- `docs/constitution/الدستور_الأعلى.md` (14K) — 🏛️ الدستور الأعلى — قواعد العمل الدائمة لـ NOVA_V8
- `docs/constitution/الدستور_التشغيلي.md` (14K) — 📜 الدستور التشغيلي — NOVA_V8 كحياة مستخدم المستخدم

### `docs/conversations` (7)

- `docs/conversations/رسالة_التوجيه_النهائية.txt` (6K) — رسالة توجيه كاملة — للمحادثة الجديدة (NOVA_V8)
- `docs/conversations/رسالة_التوجيه_للوكيل_الجديد.txt` (3K) — رسالة توجيه للوكيل الجديد — تحديث كامل بعد الملفات السابقة
- `docs/conversations/رسالة_تفضيلات_الحوار_للمحادثة_الجديدة.txt` (5K) — أريدك أن تتعامل معي بالطريقة التالية طوال هذه المحادثة:
- `docs/conversations/سجل_المحادثة_NOVA_V8.txt` (14K) — ════════════════════════════════════════════════════════════════════
- `docs/conversations/نجوم الارض.txt` (3K) — نجوم الارض
- `docs/conversations/وثيقة_السياق_الرئيسية_NOVA_V8.txt` (11K) — وثيقة السياق الرئيسية — NOVA_V8
- `docs/conversations/وثيقة_السياق_الرئيسية_المحدثة_للمحادثة_الجديدة.txt` (14K) — وثيقة السياق الرئيسية المحدثة — مشروع NOVA_V8

### `docs/designs` (8)

- `docs/designs/استراتيجيتان_منفصلتان_NOVA_V8_وثيقة_مبدئية.txt` (11K) — استراتيجيتان منفصلتان داخل NOVA_V8 — وثيقة مبدئية
- `docs/designs/تصميم_NOVA_V8_النهائي.txt` (29K) — تصميم NOVA_V8 — الوثيقة المرجعية النهائية الموحّدة
- `docs/designs/تصميم_NOVA_v8_المتفق_عليه.txt` (23K) — تصـميم محرك NOVA_V8 (البحث على التاريخ) — النسخة المتفق عليها بعد التشاور
- `docs/designs/تصميم_محرك_الواجهة.md` (3K) — تصميم محرك الواجهة — Vectorized Replay Engine (الجيل القادم)
- `docs/designs/دليل_الرموز.txt` (2K) — دليل الرموز — مرجع الترجمة (من ملف المصنع الأصلي)
- `docs/designs/عقد_الترجمة_البرمجية.txt` (4K) — عقد الترجمة البرمجية — مصنع الفرضيات NOVA_V8
- `docs/designs/مراجعة_قرارات_تصميم_NOVA.txt` (21K) — مراجعة شاملة لكل قرارات تصميم محرك NOVA_V8
- `docs/designs/وثيقة_تفويض_تطوير_NOVA_V8_المنهج_المحافظ.txt` (10K) — وثيقة تفويض تطوير NOVA_V8 — المنهج المحافظ

### `docs/designs/المخطط_الشامل_للبوت` (11)

- `docs/designs/المخطط_الشامل_للبوت/00_الفهرس_وخريطة_المشروع.md` (7K) — 🧭 المخطط الشامل للبوت — NOVA_V8_QUANT_LAB
- `docs/designs/المخطط_الشامل_للبوت/01_الدفعة_الأولى_الأساسيات_والتشخيص.md` (13K) — 📘 الدفعة الأولى — الأساسيات، التشخيص، والبوت الهجين
- `docs/designs/المخطط_الشامل_للبوت/02_الدفعة_الثانية_المعمارية_والركائز.md` (12K) — 📗 الدفعة الثانية — المعمارية الخمسية، الركائز الأربع، وهندسة الـ Spot
- `docs/designs/المخطط_الشامل_للبوت/03_الدفعة_الثالثة_المؤشرات_وقرار_الدخول.md` (15K) — 📙 الدفعة الثالثة — محرك المؤشرات، قواعد القرار، الخروج، والوقف التلقائي
- `docs/designs/المخطط_الشامل_للبوت/04_الدفعة_الرابعة_المخاطر_والتنفيذ_والخروج.md` (13K) — 📕 الدفعة الرابعة — إدارة المخاطر، التنفيذ المايكروي، ومحرك الخروج الهجين
- `docs/designs/المخطط_الشامل_للبوت/05_الدفعة_الخامسة_التليمتري_وتلغرام_والتجميع.md` (12K) — 📓 الدفعة الخامسة — قاعدة البيانات، واجهة تلغرام، والتجميع النهائي
- `docs/designs/المخطط_الشامل_للبوت/06_الدفعة_السادسة_البيانات_والباك_تست.md` (24K) — 📔 الدفعة السادسة — البيانات التاريخية، الأرشيف الذكي، والاختبار الرجعي
- `docs/designs/المخطط_الشامل_للبوت/07_الدفعة_السابعة_التقنيات_المؤسسية.md` (18K) — 📒 الدفعة السابعة — التقنيات المتقدمة المستوحاة من الروبوتات المؤسسية وصناديق التحوّط الكمي
- `docs/designs/المخطط_الشامل_للبوت/08_الدفعة_الثامنة_الثغرات_والنسخة_النهائية.md` (21K) — 📗 الدفعة الثامنة والأخيرة — الثغرات، الترقيعات السبعة، والنسخة النهائية المعتمدة
- `docs/designs/المخطط_الشامل_للبوت/09_ورقة_الثوابت_وجميع_الأرقام.md` (12K) — 📋 ورقة الثوابت — كل رقم ومعامل ورد في الملفات الأربعة
- `docs/designs/المخطط_الشامل_للبوت/المخطط_الشامل_ملف_واحد.txt` (367K) — المخطط الشامل للبوت  —  NOVA_V8_QUANT_LAB

### `docs/lanes` (6)

- `docs/lanes/INDEX.md` (2K) — LANES — لوحة المسارات (كل تجربة = ملف هنا)
- `docs/lanes/L0000-adaptive-trend-1920.md` (3K) — L0000 — adaptive_trend: جولة السويپ 477 → 1920 (مغلقة)
- `docs/lanes/L0001-donchian-current-engine-grid.md` (3K) — L0001 — donchian: إعادة التشغيل بمحاور المحرك الفعلية (DON_FILTER)
- `docs/lanes/L0002-grid-collapse-dead-axes.md` (3K) — L0002 — تخفيض الشبكة: إزالة الأعمدة الخاملة (grid_collapse)
- `docs/lanes/L0003-adoption-gate-holdout.md` (3K) — L0003 — بوابة القبول على holdout 2021-09:2023-08 (موجود في المستودع)
- `docs/lanes/_TEMPLATE.md` (3K) — L{{ID}} — {{TITLE}}

### `docs/misc` (17)

- `docs/misc/README.md` (4K) — NOVA_V8_QUANT_LAB
- `docs/misc/START.txt` (1K) — NOVA_V8 — دليل البداية للمحادثة الجديدة
- `docs/misc/requirements.txt` (1K) — Termux-safe: pure wheels, no heavy C-compilation, no matplotlib, no requests
- `docs/misc/sf_sleeves.txt` (2K) — ATOMUSDT
- `docs/misc/sle_f.txt` (10K) — INFO nova.research: بدء البحث...
- `docs/misc/sweep_don_btc.txt` (3K) — البحث الشامل: donchian — 80 تركيبة × نافذتين (تدريب+اختبار)
- `docs/misc/sweep_محلي_4_رموز.md` (1K) — 🧬 Sweep السلاحف عبر 4 رموز (نافذة محلية 2026-06→08)
- `docs/misc/التداول_الفوري_بحث_شامل.txt` (218K) — التداول الفوري (SPOT TRADING) — بحث مرجعي مُفصّل
- `docs/misc/الملف_الشامل_التداول_الفوري.txt` (113K) — الملف الشامل الموحد للتداول الفوري (SPOT TRADING)
- `docs/misc/بعد الأمر الثاني.txt` (3K) — ~/nova $ python -m nova_v8 research --symbols BTCUSDT --strategies all --start 2024-09 --e
- `docs/misc/بلا_عنوان (2).txt` (2K) — ~/nova $ cd ~/nova
- `docs/misc/بلا_عنوان.txt` (2K) — ~/nova $ python -m nova_v8 evaluate --csv ~/nova_v8_out/BTCUSDT_2y/research_results.csv --
- `docs/misc/تطوير بوت تداول ذكي بتيرمكس.txt` (71K) — PAGE 1 ---
- `docs/misc/حزمة_الوكيل_كاملة.txt` (310K) — الجزء صفر: START.txt (ابدأ هنا) =========================
- `docs/misc/شرح شامل لبوتات التداول في بينانس.txt` (30K) — PAGE 1 ---
- `docs/misc/مخطط البوت الجديد.txt` (40K) — PAGE 1 ---
- `docs/misc/مخطط_الباك_تست_الشامل.txt` (22K) — المخطط الشامل لمحرك الباك تست — NOVA_V8

### `docs/misc/مؤشرات/0` (6)

- `docs/misc/مؤشرات/0/hft_edge_extraction_batch2.md` (71K) — Reverse-Engineered Trading Logic — Batch 2 — Distilled for a Tick-Based Binance Spot Engin
- `docs/misc/مؤشرات/0/hft_edge_extraction_batch3.md` (76K) — HFT Edge Extraction — Batch 3 (20 files)
- `docs/misc/مؤشرات/0/hft_edge_extraction_batch4.md` (58K) — HFT Edge Extraction — Batch 4 (Files 61–81)
- `docs/misc/مؤشرات/0/hft_edge_extraction_batch5.md` (62K) — HFT Edge Extraction — Batch 5 (Files 82–101)
- `docs/misc/مؤشرات/0/hft_edge_extraction_batch6.md` (59K) — HFT Edge Extraction — BATCH 6 (files 102–121)
- `docs/misc/مؤشرات/0/hft_edge_extraction_batch7.md` (47K) — HFT Edge Extraction — BATCH 7 (files 122–130)

### `docs/misc/مؤشرات/1` (20)

- `docs/misc/مؤشرات/1/2-1 strategy.txt` (82K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/ABO LANA-𝑀.txt` (35K) — //@version=5
- `docs/misc/مؤشرات/1/AI Gold Scalping.txt` (22K) — //@version=5
- `docs/misc/مؤشرات/1/AI RSI MTF STRATEGY.txt` (53K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/AI SWING Algo.txt` (7K) — //@version=5
- `docs/misc/مؤشرات/1/AI Signal Remastered.txt` (11K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/AI Signal.txt` (11K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/AI Vanga V3.txt` (45K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/AI_TRENDLINE.txt` (10K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/ALGOX V11.txt` (62K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/ASK.txt` (47K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/Adaptive Ichimoku Nexus.txt` (44K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/Advanced Liquidity Sweep.txt` (37K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/Advanced SMC.txt` (122K) — //@version=5
- `docs/misc/مؤشرات/1/AlgoX V22 SuperTrend.txt` (97K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/Alpha Hunter.txt` (10K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/Anchored VWAP Trade Planner.txt` (28K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/Apex Trend.txt` (11K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/Ayman Entry.txt` (25K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/1/breakout +TP-SL.txt` (9K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt

### `docs/misc/مؤشرات/2` (19)

- `docs/misc/مؤشرات/2/Breakout Lines + TPSL.txt` (17K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/Breakout Lines.txt` (17K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/Breakout Targets.txt` (13K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/Clear Trend Algo.txt` (9K) — // This indicator is brought to you by @mrexpert_ai
- `docs/misc/مؤشرات/2/Clustering Clouds v2.txt` (67K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/Combined Algo v5.txt` (17K) — //@version=5
- `docs/misc/مؤشرات/2/Combined Trendlines Breakouts.txt` (24K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/Cute Dragon.txt` (13K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/DTC V1.35.txt` (15K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/DTC.txt` (94K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/DTC_V1.txt` (3K) — //@version=6
- `docs/misc/مؤشرات/2/Delta Reaction Zones.txt` (30K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/Double SuperTrend.txt` (5K) — //@version=6
- `docs/misc/مؤشرات/2/Drone Arrows.txt` (14K) — //@version=6
- `docs/misc/مؤشرات/2/ELITE SMART.txt` (54K) — // ALERT READY ON TELEGRAM ==> https://t.me/mrexpert_ai
- `docs/misc/مؤشرات/2/Edge Algo pro.txt` (5K) — ﻿//@version=6
- `docs/misc/مؤشرات/2/ExProfit SuperTrend.txt` (121K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/2/Eyops Fx Premium.txt` (102K) — //@version=5
- `docs/misc/مؤشرات/2/Fibonacci.txt` (50K) — //@version=6

### `docs/misc/مؤشرات/3` (20)

- `docs/misc/مؤشرات/3/FLI.txt` (10K) — //@version=5
- `docs/misc/مؤشرات/3/FTR.txt` (44K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/FVG Sniper.txt` (41K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/FVG+Fractals.txt` (2K) — //@version=5
- `docs/misc/مؤشرات/3/Fresh Algo (1).txt` (49K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/Fresh Algo.txt` (58K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/GBS.txt` (3K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/GainzAlgo Pro.txt` (3K) — // © GainzAlgo
- `docs/misc/مؤشرات/3/GainzAlgo V2.txt` (5K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/HADYAN NEW SCALPING V 2.9.txt` (63K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/HalfTrend.txt` (16K) — // This work is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 I
- `docs/misc/مؤشرات/3/Haper Trend.txt` (46K) — //@version=5
- `docs/misc/مؤشرات/3/Historical Pattern Projection.txt` (26K) — // This work is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 I
- `docs/misc/مؤشرات/3/ICT Validated SMC v1.txt` (89K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/Indicator GG Beluga KHST.txt` (28K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/Indicator ICT Master Suite.txt` (51K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/Indicator MM ALGO PREMIUM for TradingView.txt` (28K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/Infinity and Sniper by Leo.txt` (68K) — //@version=5
- `docs/misc/مؤشرات/3/Institutional Flow Toolkit MMDV.txt` (103K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/3/floop pro.txt` (42K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt

### `docs/misc/مؤشرات/4` (19)

- `docs/misc/مؤشرات/4/Inversion Order Blocks [iOB].txt` (31K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/Jack Of All Trades.txt` (32K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/Jackson_Zones.txt` (3K) — //@version=5
- `docs/misc/مؤشرات/4/Joker.txt` (47K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/KD System.txt` (61K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/Key Levels.txt` (63K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/LIQUIDITY TRAIL MATRIX.txt` (78K) — //@version=6
- `docs/misc/مؤشرات/4/Lion Trend.txt` (11K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/Liquidity Reaper.txt` (29K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/Liquidity sweep (1;2RR).txt` (3K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/Luxy BIG beautiful Dynamic.txt` (185K) — //@version=6
- `docs/misc/مؤشرات/4/LyroRS v1.txt` (13K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/MELONA.txt` (34K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/MONEY ALGORITHM.txt` (47K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/Market Matrice.txt` (23K) — / © MarkitTick
- `docs/misc/مؤشرات/4/Million Moves Alga.txt` (32K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/Mirage Liquidity Sweep Pro.txt` (61K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/4/Money Moves.txt` (36K) — //@version=5
- `docs/misc/مؤشرات/4/iqfxpro.txt` (4K) — //@version=5

### `docs/misc/مؤشرات/5` (17)

- `docs/misc/مؤشرات/5/NAS Ultimate Algo Remastered.txt` (11K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/5/NEXT CANDLE PREDICTOR V4.txt` (25K) — // ============================================================================
- `docs/misc/مؤشرات/5/NOSTRADAMUS.txt` (48K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/5/NOVA ALGO.txt` (22K) — //@version=5
- `docs/misc/مؤشرات/5/PRECISION SNIPER.txt` (45K) — //@version=6
- `docs/misc/مؤشرات/5/Pearson SLTP.txt` (20K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/5/RSI divergence entry.txt` (57K) — //@version=6
- `docs/misc/مؤشرات/5/RSI entry.txt` (21K) — //@version=6
- `docs/misc/مؤشرات/5/Reactive Trail System.txt` (57K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/5/River Strategy.txt` (80K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/5/S&D zones.txt` (4K) — // This work is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 I
- `docs/misc/مؤشرات/5/SELF-AWARE TREND SYSTEM.txt` (65K) — //@version=6
- `docs/misc/مؤشرات/5/SFI MAGIC.txt` (6K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/5/Scalper.txt` (41K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/5/Setup Scanner [GBB].txt` (39K) — //@version=6
- `docs/misc/مؤشرات/5/sfi scalper 1.0.txt` (9K) — //@version=5
- `docs/misc/مؤشرات/5/short and long.txt` (3K) — //@version=5

### `docs/misc/مؤشرات/6` (19)

- `docs/misc/مؤشرات/6/SMC Algo Pro.txt` (206K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/SMC.txt` (93K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/SUPER Scalping.txt` (80K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/SWIFT ALGO.txt` (46K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/Simple System.txt` (67K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/Smart Money Trades Pro.txt` (17K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/Sniper Trading Algo Pro.txt` (56K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/Stocks Algo.txt` (7K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/TJR SMC.txt` (33K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/TM Sniper Pro.txt` (34K) — //@version=6
- `docs/misc/مؤشرات/6/Trend Trader Pro.txt` (22K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/TrendFilter.txt` (86K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/Ultimate Opening Range Breakout.txt` (25K) — // This work is licensed under a Attribution-NonCommercial-ShareAlike 4.0 International (C
- `docs/misc/مؤشرات/6/Unmitigated.txt` (42K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/VCE - Volatility Coil Edge.txt` (48K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/simplealgo v3.txt` (43K) — //@version=5
- `docs/misc/مؤشرات/6/sniper entry with tp&sl.txt` (9K) — //@version=6
- `docs/misc/مؤشرات/6/sqzmom.txt` (13K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/6/strategy with signals.txt` (83K) — // This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at htt

### `docs/misc/مؤشرات/7` (9)

- `docs/misc/مؤشرات/7/Viprasol.txt` (26K) — // This Pine Script™ v6 indicator is subject to the terms of the Mozilla Public License 2.
- `docs/misc/مؤشرات/7/Volatility Covenant Ribbon.txt` (19K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/7/WaveTrend.txt` (153K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/7/X.txt` (59K) — //@version=5
- `docs/misc/مؤشرات/7/XALGOX-15M_1H_1D.txt` (47K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/7/XALGOX.txt` (47K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/7/Xpert Algo.txt` (59K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/7/ZZ Algo  Signals & Overlays.txt` (49K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt
- `docs/misc/مؤشرات/7/ZZ Algo.txt` (49K) — // This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0 at htt

### `docs/misc/ملفات` (13)

- `docs/misc/ملفات/claude.txt` (25K) — خطة شاملة لموازنة البوت وتحسين أدائه
- `docs/misc/ملفات/gemini.txt` (11K) — لماذا لا يرى البوت فرصاً في السوق حالياً؟
- `docs/misc/ملفات/gpt.txt` (22K) — المشكلة التي تصفها شائعة في أنظمة السكالبينج: عندما تجمع عدة شروط ثنائية صارمة AND، تصبح ا
- `docs/misc/ملفات/kimi.txt` (16K) — المشكلة التي تواجهك هي **مشكلة التوازن بين الدقة والتردد (Precision vs. Frequency)**، وهي 
- `docs/misc/ملفات/qwen.txt` (21K) — مشكلتك كلاسيكية جداً في تطوير بوتات التداول الخوارزمية، وتُعرف بمعضلة **"الموازنة بين الدق
- `docs/misc/ملفات/اخطاء و فخاخ.txt` (6K) — فخ البوابات المنطقية المتسلسلة (Boolean AND Trap): اشتراط تقاطع (EMA200 + MSS + FVG + Orde
- `docs/misc/ملفات/اسماء المؤشرات.txt` (2K) — بكل سرور. لقد قمت بمسح ملف "مشروع الكريبتو" واستخرجت لك كافة المؤشرات الفنية وأدوات التحلي
- `docs/misc/ملفات/اعدادات المؤشرات.txt` (3K) — لتحقيق أفضل قراءة بصرية للـ Gem على الفريمات الكبيرة (4 ساعات واليومي)، إليك أفضل الإعدادا
- `docs/misc/ملفات/البوت الهجين.txt` (6K) — ممتاز — إجاباتك حسمت الصورة. **Testnet + أولوية لعدد الصفقات + هجين + رسوم 0.1%** = التركي
- `docs/misc/ملفات/العملات الاقوى و الحلال تماما.txt` (1K) — BTC
- `docs/misc/ملفات/بوت جريد.txt` (3K) — نعم، يمكن لبوت الشبكة (Spot Grid) تحقيق أرباح حقيقية، والسر يكمن في فهم الميكانيكية الرياض
- `docs/misc/ملفات/فخاخ المبتدئين.txt` (1K) — فخاخ المبتدئين
- `docs/misc/ملفات/كثر خسارات البوت.txt` (7K) — بعد مراجعة شيفرة الإصدار البرمجي (NOVA V7.0), تتضح عدة أسباب جذرية تؤدي إلى سلسلة الخسائر 

### `docs/reports` (9)

- `docs/reports/استشارة_NOVA_V8_التقنية.txt` (17K) — استشارة تقنية — NOVA_V8
- `docs/reports/الاستعداد للتحليل المعماري للاستراتيجيات.txt` (53K) — PAGE 1 ---
- `docs/reports/الجدول_الختامي_5_سنوات.md` (3K) — 🎼 الجدول الختامي الكبير — كل استراتيجية × كل حالة سوق (5 سنوات حقيقية)
- `docs/reports/تحليل_ارتباط_العملات_بالبيتكوين.txt` (7K) — تحليل تبعية العملات البديلة للبيتكوين (استخلاص من التقرير المرفق)
- `docs/reports/تحليل_استراتيجيات_تداول_السبوت_مقابل_NOVA_V8.txt` (11K) — تحليل ملف «استراتيجيات تداول السبوت الناجحة» مقابل NOVA_V8
- `docs/reports/تقرير_الجولة_الشاملة.md` (3K) — 🏁 تقرير الجولة التطويرية الشاملة — اكتملت (2026-09-11)
- `docs/reports/سجل_العمل_الكامل.md` (8K) — 📋 سجل العمل الكامل — NOVA_V8
- `docs/reports/مراجعة_مطابقة_NOVA_V8_للمخطط.txt` (22K) — مراجعة مطابقة التطبيق (nova_v8) للمخطط النهائي الموحّد
- `docs/reports/ملخص_التشطيب_NOVA_V8.txt` (11K) — NOVA_V8 — ملخص التشطيب النهائي / FINAL FINISHING SUMMARY

### `docs/reports/ملفات` (1)

- `docs/reports/ملفات/التقرير_النهائي_تحليل_البوت_والمؤشرات.md` (14K) — 🔬 التقرير الشامل النهائي — تدقيق البوت «NOVA» + مراجعة مكتبة المؤشرات

### `hypotheses` (4)

- `hypotheses/عقد_مصنع_الفرضيات.txt` (5K) — عقد المهمة: مصنع الفرضيات التداولية — NOVA_V8
- `hypotheses/فرضيات_الباحث_النهائي.txt` (224K) — ملف NOVA الشامل — كل ما تمت فلترته (الفرضيات + البحث + سجل المرفوضات)
- `hypotheses/فرضياتك_النخبة.txt` (10K) — الفرضيات النخبة العشر — حصة الوكيل
- `hypotheses/لوحة_خط_الفرضيات.md` (3K) — 🏭 لوحة خط إنتاج الفرضيات — مرجع سريع

### `nova_v8` (27)

- `nova_v8/README.py` (16K) — NOVA_V8 — Research-first adaptive quant trading bot
- `nova_v8/__init__.py` (1K) — """NOVA_V8 — adaptive multi-mode quant research engine.
- `nova_v8/__main__.py` (12K) — """Command-line entry for NOVA_V8.
- `nova_v8/adaptive_trend.py` (15K) — """Adaptive Trend sleeve — spec 8.2 "الاتجاه + الارتداد إلى القيمة" (trend +
- `nova_v8/btc_leadlag.py` (10K) — """Module — BTC lead-lag for lagging altcoins (separate research unit).
- `nova_v8/config.py` (24K) — """NOVA_V8 — central configuration (single source of truth).
- `nova_v8/don_filter_doc.py` (1K) — coding: utf-8 -*-
- `nova_v8/donchian.py` (6K) — """Donchian long-only sleeve — classic Turtle-style Donchian breakout as an
- `nova_v8/dynamic_grid.py` (18K) — """Dynamic Grid (DGT) — independent research sleeve; a variant of the static
- `nova_v8/engine.py` (47K) — """Engine — research replay that turns a symbol's feature matrix into results.
- `nova_v8/evaluation.py` (14K) — """Evaluation layer — post-hoc statistics on research trade records.
- `nova_v8/execution.py` (13K) — """Module — directional trade lifecycle: entry fill, ATR-based exit engine,
- `nova_v8/feeds.py` (9K) — """Module — data ingestion + feature-matrix cache for research.
- `nova_v8/grid.py` (5K) — """Module — Spot Grid mode for choppy/quiet markets.
- `nova_v8/indicators.py` (9K) — """Module — vectorized, causal indicator math (numpy/pandas, non-repainting).
- `nova_v8/long_cycle.py` (9K) — """Long-horizon cycle accumulation/distribution research sleeve.
- `nova_v8/market_open.py` (13K) — """Independent market-open expansion sleeve.
- `nova_v8/microstructure.py` (2K) — """Module — microstructure structure signals (MSS / SFP / FVG levels).
- `nova_v8/oracle.py` (5K) — """Module — Structure Truth Oracle + regime transition record.
- `nova_v8/regime.py` (4K) — """Module — market regime classification.
- `nova_v8/risk.py` (7K) — """Deterministic portfolio protection and audit layer.
- `nova_v8/smc.py` (2K) — """Wyckoff/SMC entry-confirmation gate (specs 8.9/8.10) — an optional,
- `nova_v8/strategy_registry.py` (1K) — """Independent strategy-sleeve registry.
- `nova_v8/sweep_engine.py` (10K) — !/usr/bin/env python3
- `nova_v8/synth.py` (7K) — """Synthetic 1m archive generator — a clearly-labeled stand-in for historical
- `nova_v8/telegram_notify.py` (2K) — """Module — Telegram notifications for the research phase.
- `nova_v8/triggers.py` (4K) — """Module — directional entry triggers.

### `sweep_results/adaptive_trend` (4)

- `sweep_results/adaptive_trend/best_on_test.txt` (1K) — NOVA_AT_TRAIL NOVA_AT_STOP NOVA_AT_PB NOVA_AT_TRIG NOVA_AT_V3A NOVA_AT_V3B NOVA_AT_V3C  tr
- `sweep_results/adaptive_trend/sweep_test.csv` (1K) — ﻿NOVA_AT_TRAIL,NOVA_AT_STOP,NOVA_AT_PB,NOVA_AT_TRIG,NOVA_AT_V3A,NOVA_AT_V3B,NOVA_AT_V3C,tr
- `sweep_results/adaptive_trend/sweep_train.csv` (84K) — ﻿NOVA_AT_TRAIL,NOVA_AT_STOP,NOVA_AT_PB,NOVA_AT_TRIG,NOVA_AT_V3A,NOVA_AT_V3B,NOVA_AT_V3C,ne
- `sweep_results/adaptive_trend/sweep_train_partial.csv` (20K) — ﻿NOVA_AT_TRAIL,NOVA_AT_STOP,NOVA_AT_PB,NOVA_AT_TRIG,NOVA_AT_V3A,NOVA_AT_V3B,NOVA_AT_V3C,ne

### `sweep_results/donchian` (3)

- `sweep_results/donchian/best_on_test.txt` (1K) — NOVA_DON_ENTRY1 NOVA_DON_EXIT1 NOVA_DON_MACRO NOVA_DON_CHOP   train_net    plateau        
- `sweep_results/donchian/sweep_test.csv` (1K) — ﻿NOVA_DON_ENTRY1,NOVA_DON_EXIT1,NOVA_DON_MACRO,NOVA_DON_CHOP,train_net,plateau,net,trades,
- `sweep_results/donchian/sweep_train.csv` (4K) — ﻿NOVA_DON_ENTRY1,NOVA_DON_EXIT1,NOVA_DON_MACRO,NOVA_DON_CHOP,net,trades,win_pct

### `tools` (8)

- `tools/archive_report.py` (3K) — !/usr/bin/env python3
- `tools/audit_lane.py` (12K) — !/usr/bin/env python3
- `tools/backtest_stream_demo.py` (2K) — !/usr/bin/env python3
- `tools/canary.py` (6K) — !/usr/bin/env python3
- `tools/combo_probe.py` (3K) — !/usr/bin/env python3
- `tools/new_lane.py` (3K) — !/usr/bin/env python3
- `tools/organize_incoming.py` (11K) — import os, sys, re, hashlib, subprocess, shutil
- `tools/rebuild_archive.py` (2K) — !/usr/bin/env python3

