# 📊 الإحصاء الشامل للحزمة الجديدة — new/CENSUS.md

> تاريخ التوليد: 2026-09-16 · أمر إعادة الاشتقاق: `python3 new/census.py`
> الحزمة الأم: `nova_upload_bundle.tar.gz` —
> `sha256 = 31d64494ec40e4cb65ea5f90fa11a68cfc2ba5324d0abdaf8a0b3b49086349f3`

**الملخص:** 260 ملف كود مُحصى · 245 بايثون سليم · 5 بايثون معطوب ·
10 ملف شل · 17 ملف معزول (مفاتيح ⚠️ — انظر _quarantine/MAP.md) · 93 ملف غير كودي (PDF/ZIP/RAR/DOCX/وثائق نصية).

| # | المسار | النوع | الحجم (بايت) | sha256-12 | العنوان من الترويسة | ast | دوال | جروح |
|---|---|---|---|---|---|---|---|---|
| 1 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/README.py` | بايثون | 16,443 | `ae2d476fa227` | NOVA_V8 — Research-first adaptive quant trading bot | معطوب (سطر 4) | 0 | 0 |
| 2 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/__init__.py` | بايثون | 462 | `d82503ef206d` | """NOVA_V8 — adaptive multi-mode quant research engine. | سليم | 0 | 0 |
| 3 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/__main__.py` | بايثون | 12,662 | `05b26d28864f` | """Command-line entry for NOVA_V8. | سليم | 13 | 0 |
| 4 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/adaptive_trend.py` | بايثون | 13,826 | `fa423cf8b932` | """Adaptive Trend sleeve — spec 8.2 "الاتجاه + الارتداد إلى القيمة" (trend + | سليم | 5 | 0 |
| 5 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/btc_leadlag.py` | بايثون | 11,001 | `6c76acf65888` | """Module — BTC lead-lag for lagging altcoins (separate research unit). | سليم | 6 | 0 |
| 6 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/config.py` | بايثون | 25,142 | `fd2c127ff8d5` | """NOVA_V8 — central configuration (single source of truth). | سليم | 0 | 0 |
| 7 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/don_filter_doc.py` | بايثون | 1,274 | `854d7fff6829` | coding: utf-8 | سليم | 0 | 0 |
| 8 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/donchian.py` | بايثون | 6,907 | `f34fa28854f3` | """Donchian long-only sleeve — classic Turtle-style Donchian breakout as an | سليم | 4 | 0 |
| 9 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/dynamic_grid.py` | بايثون | 19,105 | `82981561da2f` | """Dynamic Grid (DGT) — independent research sleeve; a variant of the static | سليم | 17 | 0 |
| 10 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/engine.py` | بايثون | 48,970 | `e2e9b48d710f` | """Engine — research replay that turns a symbol's feature matrix into results. | سليم | 32 | 0 |
| 11 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/evaluation.py` | بايثون | 15,133 | `e3e76c2a82e5` | """Evaluation layer — post-hoc statistics on research trade records. | سليم | 15 | 0 |
| 12 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/execution.py` | بايثون | 13,320 | `79535bb31286` | """Module — directional trade lifecycle: entry fill, ATR-based exit engine, | سليم | 13 | 0 |
| 13 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/feeds.py` | بايثون | 9,917 | `6db83861e0de` | """Module — data ingestion + feature-matrix cache for research. | سليم | 16 | 0 |
| 14 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/grid.py` | بايثون | 5,782 | `7e38d9856ae6` | """Module — Spot Grid mode for choppy/quiet markets. | سليم | 12 | 0 |
| 15 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/indicators.py` | بايثون | 9,575 | `407dadf4bb94` | """Module — vectorized, causal indicator math (numpy/pandas, non-repainting). | سليم | 18 | 0 |
| 16 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/long_cycle.py` | بايثون | 9,630 | `e9ae1ab7f1d5` | """Long-horizon cycle accumulation/distribution research sleeve. | سليم | 6 | 0 |
| 17 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/market_open.py` | بايثون | 14,028 | `aeec13f7c95d` | """Independent market-open expansion sleeve. | سليم | 5 | 0 |
| 18 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/microstructure.py` | بايثون | 2,377 | `aa3c2195183c` | """Module — microstructure structure signals (MSS / SFP / FVG levels). | سليم | 3 | 0 |
| 19 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/oracle.py` | بايثون | 5,996 | `6b9558c0f6d6` | """Module — Structure Truth Oracle + regime transition record. | سليم | 11 | 0 |
| 20 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/regime.py` | بايثون | 4,271 | `dea0bbe4be0e` | """Module — market regime classification. | سليم | 3 | 0 |
| 21 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/risk.py` | بايثون | 7,391 | `c1baea69f2c7` | """Deterministic portfolio protection and audit layer. | سليم | 8 | 0 |
| 22 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/smc.py` | بايثون | 3,066 | `8ca791aa4c0b` | """Wyckoff/SMC entry-confirmation gate (specs 8.9/8.10) — an optional, | سليم | 3 | 0 |
| 23 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/strategy_registry.py` | بايثون | 1,674 | `21f46019a99d` | """Independent strategy-sleeve registry. | سليم | 3 | 0 |
| 24 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/sweep_engine.py` | بايثون | 10,871 | `0d9bcbb29be7` | coding: utf-8 | سليم | 4 | 0 |
| 25 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/synth.py` | بايثون | 7,611 | `5aa58b9ae495` | """Synthetic 1m archive generator — a clearly-labeled stand-in for historical | سليم | 4 | 0 |
| 26 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/telegram_notify.py` | بايثون | 3,056 | `f89fee414dd1` | """Module — Telegram notifications for the research phase. | سليم | 6 | 0 |
| 27 | `NOVA_bin_pending/workspace/NOVA_v8_bundle_X/nova_v8/triggers.py` | بايثون | 4,908 | `960012c346b5` | """Module — directional entry triggers. | سليم | 4 | 0 |
| 28 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/README.py` | بايثون | 16,443 | `ae2d476fa227` | NOVA_V8 — Research-first adaptive quant trading bot | معطوب (سطر 4) | 0 | 0 |
| 29 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/__init__.py` | بايثون | 462 | `d82503ef206d` | """NOVA_V8 — adaptive multi-mode quant research engine. | سليم | 0 | 0 |
| 30 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/__main__.py` | بايثون | 12,662 | `05b26d28864f` | """Command-line entry for NOVA_V8. | سليم | 13 | 0 |
| 31 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/adaptive_trend.py` | بايثون | 13,826 | `fa423cf8b932` | """Adaptive Trend sleeve — spec 8.2 "الاتجاه + الارتداد إلى القيمة" (trend + | سليم | 5 | 0 |
| 32 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/btc_leadlag.py` | بايثون | 11,001 | `6c76acf65888` | """Module — BTC lead-lag for lagging altcoins (separate research unit). | سليم | 6 | 0 |
| 33 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/config.py` | بايثون | 25,142 | `fd2c127ff8d5` | """NOVA_V8 — central configuration (single source of truth). | سليم | 0 | 0 |
| 34 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/don_filter_doc.py` | بايثون | 1,274 | `854d7fff6829` | coding: utf-8 | سليم | 0 | 0 |
| 35 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/donchian.py` | بايثون | 6,907 | `f34fa28854f3` | """Donchian long-only sleeve — classic Turtle-style Donchian breakout as an | سليم | 4 | 0 |
| 36 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/dynamic_grid.py` | بايثون | 19,105 | `82981561da2f` | """Dynamic Grid (DGT) — independent research sleeve; a variant of the static | سليم | 17 | 0 |
| 37 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/engine.py` | بايثون | 48,970 | `e2e9b48d710f` | """Engine — research replay that turns a symbol's feature matrix into results. | سليم | 32 | 0 |
| 38 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/evaluation.py` | بايثون | 15,133 | `e3e76c2a82e5` | """Evaluation layer — post-hoc statistics on research trade records. | سليم | 15 | 0 |
| 39 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/execution.py` | بايثون | 13,320 | `79535bb31286` | """Module — directional trade lifecycle: entry fill, ATR-based exit engine, | سليم | 13 | 0 |
| 40 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/feeds.py` | بايثون | 9,917 | `6db83861e0de` | """Module — data ingestion + feature-matrix cache for research. | سليم | 16 | 0 |
| 41 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/grid.py` | بايثون | 5,782 | `7e38d9856ae6` | """Module — Spot Grid mode for choppy/quiet markets. | سليم | 12 | 0 |
| 42 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/indicators.py` | بايثون | 9,575 | `407dadf4bb94` | """Module — vectorized, causal indicator math (numpy/pandas, non-repainting). | سليم | 18 | 0 |
| 43 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/long_cycle.py` | بايثون | 9,630 | `e9ae1ab7f1d5` | """Long-horizon cycle accumulation/distribution research sleeve. | سليم | 6 | 0 |
| 44 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/market_open.py` | بايثون | 14,028 | `aeec13f7c95d` | """Independent market-open expansion sleeve. | سليم | 5 | 0 |
| 45 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/microstructure.py` | بايثون | 2,377 | `aa3c2195183c` | """Module — microstructure structure signals (MSS / SFP / FVG levels). | سليم | 3 | 0 |
| 46 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/oracle.py` | بايثون | 5,996 | `6b9558c0f6d6` | """Module — Structure Truth Oracle + regime transition record. | سليم | 11 | 0 |
| 47 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/regime.py` | بايثون | 4,271 | `dea0bbe4be0e` | """Module — market regime classification. | سليم | 3 | 0 |
| 48 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/risk.py` | بايثون | 7,391 | `c1baea69f2c7` | """Deterministic portfolio protection and audit layer. | سليم | 8 | 0 |
| 49 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/smc.py` | بايثون | 3,066 | `8ca791aa4c0b` | """Wyckoff/SMC entry-confirmation gate (specs 8.9/8.10) — an optional, | سليم | 3 | 0 |
| 50 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/strategy_registry.py` | بايثون | 1,674 | `21f46019a99d` | """Independent strategy-sleeve registry. | سليم | 3 | 0 |
| 51 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/sweep_engine.py` | بايثون | 10,871 | `0d9bcbb29be7` | coding: utf-8 | سليم | 4 | 0 |
| 52 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/synth.py` | بايثون | 7,611 | `5aa58b9ae495` | """Synthetic 1m archive generator — a clearly-labeled stand-in for historical | سليم | 4 | 0 |
| 53 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/telegram_notify.py` | بايثون | 3,056 | `f89fee414dd1` | """Module — Telegram notifications for the research phase. | سليم | 6 | 0 |
| 54 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/NOVA_v8_bundle_X/nova_v8/triggers.py` | بايثون | 4,908 | `960012c346b5` | """Module — directional entry triggers. | سليم | 4 | 0 |
| 55 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/nova/عقد_الترجمة_البرمجية.txt` | بايثون | 5,028 | `fe1f062f7c40` | عقد الترجمة البرمجية — مصنع الفرضيات NOVA_V8 | معطوب (سطر 1) | 0 | 0 |
| 56 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/الملف_الشامل_التداول_الفوري.txt` | بايثون | 116,255 | `2a5322135217` | ================================================================================ | معطوب (سطر 7) | 0 | 0 |
| 57 | `NOVA_bin_pending/workspace/NOVA_نقل_كامل_X/حزمة_الوكيل_كاملة.txt` | بايثون | 316,738 | `22a02166bf11` | ========================= الجزء: العقد (اقرأه أولاً) ========================= | معطوب (سطر 5) | 0 | 0 |
| 58 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/README.md` | شل | 12,471 | `da4f066c390c` | NOVA_V8 — Research-first adaptive quant trading bot | — | 0 | 0 |
| 59 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/__init__.py` | بايثون | 462 | `d82503ef206d` | """NOVA_V8 — adaptive multi-mode quant research engine. | سليم | 0 | 0 |
| 60 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/__main__.py` | بايثون | 8,134 | `ad51e67680dd` | """Command-line entry for NOVA_V8. | سليم | 11 | 0 |
| 61 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/btc_leadlag.py` | بايثون | 11,001 | `6c76acf65888` | """Module — BTC lead-lag for lagging altcoins (separate research unit). | سليم | 6 | 0 |
| 62 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/config.py` | بايثون | 14,554 | `fdf048ebc2f1` | """NOVA_V8 — central configuration (single source of truth). | سليم | 0 | 0 |
| 63 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/engine.py` | بايثون | 36,101 | `08819e63e07b` | """Engine — research replay that turns a symbol's feature matrix into results. | سليم | 27 | 0 |
| 64 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/execution.py` | بايثون | 12,319 | `dd257011ee99` | """Module — directional trade lifecycle: entry fill, ATR-based exit engine, | سليم | 13 | 0 |
| 65 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/feeds.py` | بايثون | 8,248 | `5cd88d6b05c0` | """Module — data ingestion + feature-matrix cache for research. | سليم | 16 | 0 |
| 66 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/grid.py` | بايثون | 5,782 | `7e38d9856ae6` | """Module — Spot Grid mode for choppy/quiet markets. | سليم | 12 | 0 |
| 67 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/indicators.py` | بايثون | 8,725 | `85a907ff4bd0` | """Module — vectorized, causal indicator math (numpy/pandas, non-repainting). | سليم | 17 | 0 |
| 68 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/long_cycle.py` | بايثون | 8,689 | `96aea438ef30` | """Long-horizon cycle accumulation/distribution research sleeve. | سليم | 6 | 0 |
| 69 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/market_open.py` | بايثون | 13,979 | `7570988f7515` | """Independent market-open expansion sleeve. | سليم | 5 | 0 |
| 70 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/microstructure.py` | بايثون | 2,377 | `aa3c2195183c` | """Module — microstructure structure signals (MSS / SFP / FVG levels). | سليم | 3 | 0 |
| 71 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/oracle.py` | بايثون | 5,996 | `6b9558c0f6d6` | """Module — Structure Truth Oracle + regime transition record. | سليم | 11 | 0 |
| 72 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/regime.py` | بايثون | 4,271 | `dea0bbe4be0e` | """Module — market regime classification. | سليم | 3 | 0 |
| 73 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/risk.py` | بايثون | 7,391 | `c1baea69f2c7` | """Deterministic portfolio protection and audit layer. | سليم | 8 | 0 |
| 74 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/strategy_registry.py` | بايثون | 1,431 | `c732da9d92cc` | """Independent strategy-sleeve registry. | سليم | 3 | 0 |
| 75 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/telegram_notify.py` | بايثون | 3,056 | `f89fee414dd1` | """Module — Telegram notifications for the research phase. | سليم | 6 | 0 |
| 76 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/tests/__init__.py` | بايثون | 0 | `e3b0c44298fc` | (بلا ترويسة) | سليم | 0 | 0 |
| 77 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/tests/selftest.py` | بايثون | 14,394 | `cf87518e6330` | """Self-test: run the full research engine on a small synthetic archive to catch | سليم | 14 | 0 |
| 78 | `NOVA_bin_pending/workspace/nova_v8_final_X/nova_v8/triggers.py` | بايثون | 4,908 | `960012c346b5` | """Module — directional entry triggers. | سليم | 4 | 0 |
| 79 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/README.md` | شل | 12,471 | `da4f066c390c` | NOVA_V8 — Research-first adaptive quant trading bot | — | 0 | 0 |
| 80 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/__init__.py` | بايثون | 462 | `d82503ef206d` | """NOVA_V8 — adaptive multi-mode quant research engine. | سليم | 0 | 0 |
| 81 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/__main__.py` | بايثون | 8,134 | `ad51e67680dd` | """Command-line entry for NOVA_V8. | سليم | 11 | 0 |
| 82 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/btc_leadlag.py` | بايثون | 11,001 | `6c76acf65888` | """Module — BTC lead-lag for lagging altcoins (separate research unit). | سليم | 6 | 0 |
| 83 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/config.py` | بايثون | 14,554 | `fdf048ebc2f1` | """NOVA_V8 — central configuration (single source of truth). | سليم | 0 | 0 |
| 84 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/engine.py` | بايثون | 36,101 | `08819e63e07b` | """Engine — research replay that turns a symbol's feature matrix into results. | سليم | 27 | 0 |
| 85 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/execution.py` | بايثون | 12,319 | `dd257011ee99` | """Module — directional trade lifecycle: entry fill, ATR-based exit engine, | سليم | 13 | 0 |
| 86 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/feeds.py` | بايثون | 8,248 | `5cd88d6b05c0` | """Module — data ingestion + feature-matrix cache for research. | سليم | 16 | 0 |
| 87 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/grid.py` | بايثون | 5,782 | `7e38d9856ae6` | """Module — Spot Grid mode for choppy/quiet markets. | سليم | 12 | 0 |
| 88 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/indicators.py` | بايثون | 8,725 | `85a907ff4bd0` | """Module — vectorized, causal indicator math (numpy/pandas, non-repainting). | سليم | 17 | 0 |
| 89 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/long_cycle.py` | بايثون | 8,689 | `96aea438ef30` | """Long-horizon cycle accumulation/distribution research sleeve. | سليم | 6 | 0 |
| 90 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/market_open.py` | بايثون | 13,979 | `7570988f7515` | """Independent market-open expansion sleeve. | سليم | 5 | 0 |
| 91 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/microstructure.py` | بايثون | 2,377 | `aa3c2195183c` | """Module — microstructure structure signals (MSS / SFP / FVG levels). | سليم | 3 | 0 |
| 92 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/oracle.py` | بايثون | 5,996 | `6b9558c0f6d6` | """Module — Structure Truth Oracle + regime transition record. | سليم | 11 | 0 |
| 93 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/regime.py` | بايثون | 4,271 | `dea0bbe4be0e` | """Module — market regime classification. | سليم | 3 | 0 |
| 94 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/risk.py` | بايثون | 7,391 | `c1baea69f2c7` | """Deterministic portfolio protection and audit layer. | سليم | 8 | 0 |
| 95 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/strategy_registry.py` | بايثون | 1,431 | `c732da9d92cc` | """Independent strategy-sleeve registry. | سليم | 3 | 0 |
| 96 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/telegram_notify.py` | بايثون | 3,056 | `f89fee414dd1` | """Module — Telegram notifications for the research phase. | سليم | 6 | 0 |
| 97 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/tests/__init__.py` | بايثون | 0 | `e3b0c44298fc` | (بلا ترويسة) | سليم | 0 | 0 |
| 98 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/tests/selftest.py` | بايثون | 14,394 | `cf87518e6330` | """Self-test: run the full research engine on a small synthetic archive to catch | سليم | 14 | 0 |
| 99 | `NOVA_bin_pending/workspace/nova_v8_final_updated_X/nova_v8/triggers.py` | بايثون | 4,908 | `960012c346b5` | """Module — directional entry triggers. | سليم | 4 | 0 |
| 100 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/README.md` | شل | 8,884 | `26de6a2f7234` | NOVA_V8 — Research-first adaptive quant trading bot | — | 0 | 0 |
| 101 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/__init__.py` | بايثون | 462 | `d82503ef206d` | """NOVA_V8 — adaptive multi-mode quant research engine. | سليم | 0 | 0 |
| 102 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/__main__.py` | بايثون | 3,395 | `9e162b970c60` | """Command-line entry for NOVA_V8. | سليم | 8 | 0 |
| 103 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/btc_leadlag.py` | بايثون | 5,667 | `640f7be2b801` | """Module — BTC lead-lag for lagging altcoins (separate research unit). | سليم | 5 | 0 |
| 104 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/config.py` | بايثون | 7,464 | `ba3eb21d3ef5` | """NOVA_V8 — central configuration (single source of truth). | سليم | 0 | 0 |
| 105 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/engine.py` | بايثون | 16,736 | `b2c425cf39d3` | """Engine — research replay that turns a symbol's feature matrix into results. | سليم | 17 | 0 |
| 106 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/execution.py` | بايثون | 6,525 | `e6ea4c2a7547` | """Module — directional trade lifecycle: entry fill, ATR-based exit engine, | سليم | 7 | 0 |
| 107 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/feeds.py` | بايثون | 4,828 | `37115e110698` | """Module — data ingestion + feature-matrix cache for research. | سليم | 8 | 0 |
| 108 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/grid.py` | بايثون | 5,016 | `8137cd651be7` | """Module — Spot Grid mode for choppy/quiet markets. | سليم | 12 | 0 |
| 109 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/indicators.py` | بايثون | 8,693 | `edd9e885c9c9` | """Module — vectorized, causal indicator math (numpy/pandas, non-repainting). | سليم | 17 | 0 |
| 110 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/microstructure.py` | بايثون | 2,377 | `aa3c2195183c` | """Module — microstructure structure signals (MSS / SFP / FVG levels). | سليم | 3 | 0 |
| 111 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/oracle.py` | بايثون | 5,088 | `0d5cd0a160d5` | """Module — Structure Truth Oracle + regime transition record. | سليم | 9 | 0 |
| 112 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/regime.py` | بايثون | 2,573 | `8ef9fedbce3e` | """Module — market regime classification. | سليم | 2 | 0 |
| 113 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/telegram_notify.py` | بايثون | 3,056 | `f89fee414dd1` | """Module — Telegram notifications for the research phase. | سليم | 6 | 0 |
| 114 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/tests/__init__.py` | بايثون | 0 | `e3b0c44298fc` | (بلا ترويسة) | سليم | 0 | 0 |
| 115 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/tests/selftest.py` | بايثون | 6,646 | `01e95521bf05` | """Self-test: run the full research engine on a small synthetic archive to catch | سليم | 8 | 0 |
| 116 | `NOVA_bin_pending/workspace/nova_v8_research_bot_X/nova_v8/triggers.py` | بايثون | 4,728 | `1a6f2cbb9634` | """Module — directional entry triggers. | سليم | 4 | 0 |
| 117 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/README.md` | شل | 8,884 | `26de6a2f7234` | NOVA_V8 — Research-first adaptive quant trading bot | — | 0 | 0 |
| 118 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/__init__.py` | بايثون | 462 | `d82503ef206d` | """NOVA_V8 — adaptive multi-mode quant research engine. | سليم | 0 | 0 |
| 119 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/__main__.py` | بايثون | 3,395 | `9e162b970c60` | """Command-line entry for NOVA_V8. | سليم | 8 | 0 |
| 120 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/btc_leadlag.py` | بايثون | 6,484 | `6769a5adf365` | """Module — BTC lead-lag for lagging altcoins (separate research unit). | سليم | 5 | 0 |
| 121 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/config.py` | بايثون | 7,694 | `a22dfa620f31` | """NOVA_V8 — central configuration (single source of truth). | سليم | 0 | 0 |
| 122 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/engine.py` | بايثون | 16,736 | `b2c425cf39d3` | """Engine — research replay that turns a symbol's feature matrix into results. | سليم | 17 | 0 |
| 123 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/execution.py` | بايثون | 6,525 | `e6ea4c2a7547` | """Module — directional trade lifecycle: entry fill, ATR-based exit engine, | سليم | 7 | 0 |
| 124 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/feeds.py` | بايثون | 4,828 | `37115e110698` | """Module — data ingestion + feature-matrix cache for research. | سليم | 8 | 0 |
| 125 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/grid.py` | بايثون | 5,016 | `8137cd651be7` | """Module — Spot Grid mode for choppy/quiet markets. | سليم | 12 | 0 |
| 126 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/indicators.py` | بايثون | 8,725 | `85a907ff4bd0` | """Module — vectorized, causal indicator math (numpy/pandas, non-repainting). | سليم | 17 | 0 |
| 127 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/microstructure.py` | بايثون | 2,377 | `aa3c2195183c` | """Module — microstructure structure signals (MSS / SFP / FVG levels). | سليم | 3 | 0 |
| 128 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/oracle.py` | بايثون | 5,088 | `0d5cd0a160d5` | """Module — Structure Truth Oracle + regime transition record. | سليم | 9 | 0 |
| 129 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/regime.py` | بايثون | 3,112 | `4a2802acc810` | """Module — market regime classification. | سليم | 2 | 0 |
| 130 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/telegram_notify.py` | بايثون | 3,056 | `f89fee414dd1` | """Module — Telegram notifications for the research phase. | سليم | 6 | 0 |
| 131 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/tests/__init__.py` | بايثون | 0 | `e3b0c44298fc` | (بلا ترويسة) | سليم | 0 | 0 |
| 132 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/tests/selftest.py` | بايثون | 6,646 | `01e95521bf05` | """Self-test: run the full research engine on a small synthetic archive to catch | سليم | 8 | 0 |
| 133 | `NOVA_bin_pending/workspace/nova_v8_research_bot_reviewed_X/nova_v8/triggers.py` | بايثون | 4,728 | `1a6f2cbb9634` | """Module — directional entry triggers. | سليم | 4 | 0 |
| 134 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/README.md` | شل | 8,884 | `26de6a2f7234` | NOVA_V8 — Research-first adaptive quant trading bot | — | 0 | 0 |
| 135 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/__init__.py` | بايثون | 462 | `d82503ef206d` | """NOVA_V8 — adaptive multi-mode quant research engine. | سليم | 0 | 0 |
| 136 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/__main__.py` | بايثون | 3,395 | `9e162b970c60` | """Command-line entry for NOVA_V8. | سليم | 8 | 0 |
| 137 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/btc_leadlag.py` | بايثون | 8,660 | `0dddef775e6a` | """Module — BTC lead-lag for lagging altcoins (separate research unit). | سليم | 5 | 0 |
| 138 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/config.py` | بايثون | 8,995 | `3b63d18bc4b7` | """NOVA_V8 — central configuration (single source of truth). | سليم | 0 | 0 |
| 139 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/engine.py` | بايثون | 21,991 | `58cf02554f12` | """Engine — research replay that turns a symbol's feature matrix into results. | سليم | 21 | 0 |
| 140 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/execution.py` | بايثون | 6,706 | `929070a85c2c` | """Module — directional trade lifecycle: entry fill, ATR-based exit engine, | سليم | 7 | 0 |
| 141 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/feeds.py` | بايثون | 4,828 | `37115e110698` | """Module — data ingestion + feature-matrix cache for research. | سليم | 8 | 0 |
| 142 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/grid.py` | بايثون | 5,167 | `b8a08010ea81` | """Module — Spot Grid mode for choppy/quiet markets. | سليم | 12 | 0 |
| 143 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/indicators.py` | بايثون | 8,725 | `85a907ff4bd0` | """Module — vectorized, causal indicator math (numpy/pandas, non-repainting). | سليم | 17 | 0 |
| 144 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/microstructure.py` | بايثون | 2,377 | `aa3c2195183c` | """Module — microstructure structure signals (MSS / SFP / FVG levels). | سليم | 3 | 0 |
| 145 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/oracle.py` | بايثون | 6,007 | `b602183b1c37` | """Module — Structure Truth Oracle + regime transition record. | سليم | 11 | 0 |
| 146 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/regime.py` | بايثون | 4,271 | `dea0bbe4be0e` | """Module — market regime classification. | سليم | 3 | 0 |
| 147 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/telegram_notify.py` | بايثون | 3,056 | `f89fee414dd1` | """Module — Telegram notifications for the research phase. | سليم | 6 | 0 |
| 148 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/tests/__init__.py` | بايثون | 0 | `e3b0c44298fc` | (بلا ترويسة) | سليم | 0 | 0 |
| 149 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/tests/selftest.py` | بايثون | 9,207 | `78ed58c9ef1c` | """Self-test: run the full research engine on a small synthetic archive to catch | سليم | 10 | 0 |
| 150 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v2_X/nova_v8/triggers.py` | بايثون | 4,908 | `960012c346b5` | """Module — directional entry triggers. | سليم | 4 | 0 |
| 151 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/README.md` | شل | 8,884 | `26de6a2f7234` | NOVA_V8 — Research-first adaptive quant trading bot | — | 0 | 0 |
| 152 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/__init__.py` | بايثون | 462 | `d82503ef206d` | """NOVA_V8 — adaptive multi-mode quant research engine. | سليم | 0 | 0 |
| 153 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/__main__.py` | بايثون | 3,395 | `9e162b970c60` | """Command-line entry for NOVA_V8. | سليم | 8 | 0 |
| 154 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/btc_leadlag.py` | بايثون | 8,660 | `0dddef775e6a` | """Module — BTC lead-lag for lagging altcoins (separate research unit). | سليم | 5 | 0 |
| 155 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/config.py` | بايثون | 10,343 | `0998abebc7d6` | """NOVA_V8 — central configuration (single source of truth). | سليم | 0 | 0 |
| 156 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/engine.py` | بايثون | 24,725 | `fa6bbf6bb0d1` | """Engine — research replay that turns a symbol's feature matrix into results. | سليم | 23 | 0 |
| 157 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/execution.py` | بايثون | 9,132 | `39fcbf405028` | """Module — directional trade lifecycle: entry fill, ATR-based exit engine, | سليم | 9 | 0 |
| 158 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/feeds.py` | بايثون | 4,828 | `37115e110698` | """Module — data ingestion + feature-matrix cache for research. | سليم | 8 | 0 |
| 159 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/grid.py` | بايثون | 5,167 | `b8a08010ea81` | """Module — Spot Grid mode for choppy/quiet markets. | سليم | 12 | 0 |
| 160 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/indicators.py` | بايثون | 8,725 | `85a907ff4bd0` | """Module — vectorized, causal indicator math (numpy/pandas, non-repainting). | سليم | 17 | 0 |
| 161 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/microstructure.py` | بايثون | 2,377 | `aa3c2195183c` | """Module — microstructure structure signals (MSS / SFP / FVG levels). | سليم | 3 | 0 |
| 162 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/oracle.py` | بايثون | 6,007 | `b602183b1c37` | """Module — Structure Truth Oracle + regime transition record. | سليم | 11 | 0 |
| 163 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/regime.py` | بايثون | 4,271 | `dea0bbe4be0e` | """Module — market regime classification. | سليم | 3 | 0 |
| 164 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/telegram_notify.py` | بايثون | 3,056 | `f89fee414dd1` | """Module — Telegram notifications for the research phase. | سليم | 6 | 0 |
| 165 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/tests/__init__.py` | بايثون | 0 | `e3b0c44298fc` | (بلا ترويسة) | سليم | 0 | 0 |
| 166 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/tests/selftest.py` | بايثون | 11,436 | `a71d559b5fba` | """Self-test: run the full research engine on a small synthetic archive to catch | سليم | 11 | 0 |
| 167 | `NOVA_bin_pending/workspace/nova_v8_research_bot_v3_X/nova_v8/triggers.py` | بايثون | 4,908 | `960012c346b5` | """Module — directional entry triggers. | سليم | 4 | 0 |
| 168 | `NOVA_bin_pending/جميع اصدارات البوت/1/NOVA.Finally_X/NOVA.py` | بايثون | 383,374 | `3e08f1f8f103` | coding: utf-8 | سليم | 262 | 0 |
| 169 | `NOVA_bin_pending/جميع اصدارات البوت/1/NOVA.Finally_X/check.py` | بايثون | 7,109 | `4ec231a8ddc7` | """حاضنة تشغيل غير متصلة (V7.0): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.""" | سليم | 20 | 0 |
| 170 | `NOVA_bin_pending/جميع اصدارات البوت/1/NOVA_ALERT_PRO_v6.0_X/NOVA_ALERT.py` | بايثون | 150,630 | `9f69acd2606f` | coding: utf-8 | سليم | 101 | 0 |
| 171 | `NOVA_bin_pending/جميع اصدارات البوت/1/NOVA_V6.2 (1)_X/NOVA.py` | بايثون | 330,652 | `bc7ad0cfac23` | coding: utf-8 | سليم | 242 | 0 |
| 172 | `NOVA_bin_pending/جميع اصدارات البوت/1/NOVA_V6.2 (1)_X/check.py` | بايثون | 6,026 | `143485a2ba31` | """حاضنة تشغيل غير متصلة (V6.2): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.""" | سليم | 20 | 0 |
| 173 | `NOVA_bin_pending/جميع اصدارات البوت/1/NOVA_V6.2_X/NOVA.py` | بايثون | 323,251 | `1f099c0539a8` | coding: utf-8 | سليم | 238 | 0 |
| 174 | `NOVA_bin_pending/جميع اصدارات البوت/1/NOVA_V6.2_X/check.py` | بايثون | 6,026 | `143485a2ba31` | """حاضنة تشغيل غير متصلة (V6.2): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.""" | سليم | 20 | 0 |
| 175 | `NOVA_bin_pending/جميع اصدارات البوت/1/NOVA_V7.0_X/NOVA.py` | بايثون | 377,124 | `de644baf970b` | coding: utf-8 | سليم | 262 | 0 |
| 176 | `NOVA_bin_pending/جميع اصدارات البوت/1/NOVA_V7.0_X/check.py` | بايثون | 7,109 | `4ec231a8ddc7` | """حاضنة تشغيل غير متصلة (V7.0): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.""" | سليم | 20 | 0 |
| 177 | `NOVA_bin_pending/جميع اصدارات البوت/1fg/NOVA_V6.2 (1)_X/NOVA.py` | بايثون | 330,652 | `bc7ad0cfac23` | coding: utf-8 | سليم | 242 | 0 |
| 178 | `NOVA_bin_pending/جميع اصدارات البوت/1fg/NOVA_V6.2 (1)_X/check.py` | بايثون | 6,026 | `143485a2ba31` | """حاضنة تشغيل غير متصلة (V6.2): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.""" | سليم | 20 | 0 |
| 179 | `NOVA_bin_pending/جميع اصدارات البوت/1fg/NOVA_V6.2_X/NOVA.py` | بايثون | 323,251 | `1f099c0539a8` | coding: utf-8 | سليم | 238 | 0 |
| 180 | `NOVA_bin_pending/جميع اصدارات البوت/1fg/NOVA_V6.2_X/check.py` | بايثون | 6,026 | `143485a2ba31` | """حاضنة تشغيل غير متصلة (V6.2): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.""" | سليم | 20 | 0 |
| 181 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/0.py` | بايثون | 100,408 | `4ceea9b55563` | coding: utf-8 | سليم | 109 | 0 |
| 182 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/000.py` | بايثون | 100,514 | `43435d7a3348` | coding: utf-8 | سليم | 109 | 0 |
| 183 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/1 (2).txt` | بايثون | 116,270 | `ace1d282a3c6` | coding: utf-8 | سليم | 120 | 0 |
| 184 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/1.py` | بايثون | 100,255 | `1fdcb57d9202` | coding: utf-8 | سليم | 109 | 0 |
| 185 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/2.py` | بايثون | 100,298 | `99a44316478c` | coding: utf-8 | سليم | 109 | 0 |
| 186 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/3.py` | بايثون | 100,356 | `d176028060ee` | coding: utf-8 | سليم | 109 | 0 |
| 187 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/9.p9` | بايثون | 112,611 | `db606f0435ee` | coding: utf-8 | سليم | 115 | 0 |
| 188 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/9.txt` | بايثون | 107,108 | `a54b4a5fadd8` | coding: utf-8 | سليم | 114 | 0 |
| 189 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/999.txt` | بايثون | 102,514 | `15d63514ce93` | coding: utf-8 | سليم | 110 | 0 |
| 190 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/9_3.txt` | بايثون | 111,570 | `a381861fbfb8` | coding: utf-8 | سليم | 115 | 0 |
| 191 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (2) (2) (2).txt` | بايثون | 114,494 | `664dca785702` | coding: utf-8 | سليم | 108 | 0 |
| 192 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (2) (2).py` | بايثون | 216,916 | `ef509125e9e4` | coding: utf-8 | سليم | 188 | 0 |
| 193 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (2) (2).txt` | بايثون | 115,423 | `4bc3cc68e7dc` | coding: utf-8 | سليم | 109 | 0 |
| 194 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (2) (3) (2).py` | بايثون | 112,054 | `e2651aa4a41f` | coding: utf-8 | سليم | 109 | 0 |
| 195 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (2) (3).py` | بايثون | 118,116 | `8528765d4332` | coding: utf-8 | سليم | 109 | 0 |
| 196 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (2).py` | بايثون | 330,652 | `bc7ad0cfac23` | coding: utf-8 | سليم | 242 | 0 |
| 197 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (2).txt` | بايثون | 255,466 | `b7770b614dbe` | coding: utf-8 | سليم | 190 | 0 |
| 198 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (3) (2) (2).txt` | بايثون | 114,494 | `664dca785702` | coding: utf-8 | سليم | 108 | 0 |
| 199 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (3) (2).txt` | بايثون | 122,306 | `5d3dfe58f1ed` | coding: utf-8 | سليم | 111 | 0 |
| 200 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (3).py` | بايثون | 118,116 | `8528765d4332` | coding: utf-8 | سليم | 109 | 0 |
| 201 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (3).txt` | بايثون | 255,160 | `080ebb707ac1` | coding: utf-8 | سليم | 213 | 0 |
| 202 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (4).py` | بايثون | 142,242 | `2aaa20c1ec47` | coding: utf-8 | سليم | 142 | 0 |
| 203 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (4).txt` | بايثون | 122,306 | `5d3dfe58f1ed` | coding: utf-8 | سليم | 111 | 0 |
| 204 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (5).py` | بايثون | 194,083 | `6483aada97f7` | coding: utf-8 | سليم | 175 | 0 |
| 205 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (5).txt` | بايثون | 116,723 | `e0e0f5209761` | coding: utf-8 | سليم | 120 | 0 |
| 206 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (6) (2).py` | بايثون | 112,645 | `1907fb9fa445` | coding: utf-8 | سليم | 111 | 0 |
| 207 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (6).py` | بايثون | 116,270 | `ace1d282a3c6` | coding: utf-8 | سليم | 120 | 0 |
| 208 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA (7).py` | بايثون | 298,399 | `6d6825f98b2f` | coding: utf-8 | سليم | 231 | 0 |
| 209 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA.py` | بايثون | 255,465 | `f54376fb1c01` | coding: utf-8 | سليم | 190 | 0 |
| 210 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA.py.txt` | بايثون | 255,173 | `de2f77e02819` | coding: utf-8 | سليم | 213 | 0 |
| 211 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA.txt` | بايثون | 213,546 | `f2f98067cd3d` | coding: utf-8 | سليم | 180 | 0 |
| 212 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/NOVA_V4_1.py` | بايثون | 175,860 | `656e6cefdbf2` | coding: utf-8 | سليم | 167 | 0 |
| 213 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/bot (2).py` | بايثون | 93,997 | `15ddc1e8ecd4` | coding: utf-8 | سليم | 91 | 0 |
| 214 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/bot (3).py` | بايثون | 93,997 | `15ddc1e8ecd4` | coding: utf-8 | سليم | 91 | 0 |
| 215 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/bot.py` | بايثون | 93,997 | `15ddc1e8ecd4` | coding: utf-8 | سليم | 91 | 0 |
| 216 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/check (2).py` | بايثون | 6,026 | `f69a5524b327` | """حاضنة تشغيل غير متصلة (V6.1): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.""" | سليم | 20 | 0 |
| 217 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/check.py` | بايثون | 6,026 | `143485a2ba31` | """حاضنة تشغيل غير متصلة (V6.2): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.""" | سليم | 20 | 0 |
| 218 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/check.py.txt` | بايثون | 6,018 | `d3722218ff65` | """حاضنة تشغيل غير متصلة: تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.""" | سليم | 20 | 0 |
| 219 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/scalp_bot (2).py` | بايثون | 79,747 | `ee9521d761f9` | coding: utf-8 | سليم | 96 | 0 |
| 220 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/scalp_bot.py` | بايثون | 90,538 | `ec69b3bbb700` | coding: utf-8 | سليم | 103 | 0 |
| 221 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_X/NOVA/مقتنص بطي حذر بخساره قليه جدا.py` | بايثون | 255,466 | `b7770b614dbe` | coding: utf-8 | سليم | 190 | 0 |
| 222 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_ZERO_WAIT_v4.0_STRICT_X/NOVA.py` | بايثون | 142,483 | `1f39383b47b8` | coding: utf-8 | سليم | 123 | 0 |
| 223 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/__init__.py` | بايثون | 0 | `e3b0c44298fc` | (بلا ترويسة) | سليم | 0 | 0 |
| 224 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/config.py` | بايثون | 9,540 | `71638b8ff2e3` | NOVA v5 — الإعدادات والسريّة (M0: الأمان) | سليم | 7 | 0 |
| 225 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/data.py` | بايثون | 6,692 | `2307ba892cde` | NOVA v5 — طبقة البيانات WebSockets (M1) | سليم | 10 | 0 |
| 226 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/engine.py` | بايثون | 20,104 | `f1f5f38f654c` | NOVA v5 — المحرك الرئيسي (Orchestrator) | سليم | 26 | 0 |
| 227 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/execution.py` | بايثون | 4,809 | `d0dd5894a43c` | NOVA v5 — التنفيذ المُوقّع + إدارة المراكز (M8) | سليم | 12 | 0 |
| 228 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/indicators.py` | بايثون | 11,369 | `dbe5e52f0d94` | NOVA v5 — المؤشرات الرياضية النقية (M2 / M4) | سليم | 21 | 0 |
| 229 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/main.py` | بايثون | 8,017 | `d85e677d2474` | NOVA v5 — نقطة الدخول + الاختبار الذاتي | سليم | 4 | 0 |
| 230 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/nb.py` | بايثون | 10,404 | `43c1fc6ecd55` | NOVA v5 — Online Naive-Bayes Order-Flow Classifier (M4 = مُقفل) | سليم | 19 | 0 |
| 231 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/quant.py` | بايثون | 4,802 | `e54535f2cd63` | NOVA v5 — طبقة الكوانت (M3): تشديد إضافي قبل محفّز الدخول | سليم | 7 | 0 |
| 232 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/risk.py` | بايثون | 3,028 | `0b460b300458` | NOVA v5 — إدارة المخاطر والتنفيذ الصارم (مُحافَظ عليه من v4.0.2) | سليم | 6 | 0 |
| 233 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/scoring.py` | بايثون | 2,625 | `2b23b604e559` | NOVA v5 — Six-Factor Scoring (M5, مُقفل 50/70/85) | سليم | 3 | 0 |
| 234 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/telegram.py` | بايثون | 8,633 | `5693da601245` | NOVA v5 — تليجرام Async (M6) عبر aiohttp | سليم | 16 | 0 |
| 235 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/nova_bot/trigger.py` | بايثون | 4,115 | `9d17460a0c80` | NOVA v5 — محفّز الدخول (M3): Sweep → MSS → FVG/Tap | سليم | 5 | 0 |
| 236 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_X/nova_bot/start.sh` | شل | 803 | `ce95b2751a5c` | NOVA v5 ZERO-WAIT QUANT — مشغّل سكالبينج (نسخة آمنة، بلا أسرار في الكود) | — | 0 | 0 |
| 237 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/README.md` | شل | 3,129 | `0b8a1f431b89` | 🤖 NOVA v5 — ZERO-WAIT QUANT ENGINE (نسخة مسطّحة) | — | 0 | 0 |
| 238 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/config.py` | بايثون | 9,540 | `71638b8ff2e3` | NOVA v5 — الإعدادات والسريّة (M0: الأمان) | سليم | 7 | 0 |
| 239 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/data.py` | بايثون | 6,692 | `2307ba892cde` | NOVA v5 — طبقة البيانات WebSockets (M1) | سليم | 10 | 0 |
| 240 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/engine.py` | بايثون | 20,088 | `bd070ce2b86d` | NOVA v5 — المحرك الرئيسي (Orchestrator) | سليم | 26 | 0 |
| 241 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/execution.py` | بايثون | 4,809 | `d0dd5894a43c` | NOVA v5 — التنفيذ المُوقّع + إدارة المراكز (M8) | سليم | 12 | 0 |
| 242 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/indicators.py` | بايثون | 11,369 | `dbe5e52f0d94` | NOVA v5 — المؤشرات الرياضية النقية (M2 / M4) | سليم | 21 | 0 |
| 243 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/main.py` | بايثون | 8,039 | `de61235f9bd2` | NOVA v5 — نقطة الدخول + الاختبار الذاتي | سليم | 4 | 0 |
| 244 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/nb.py` | بايثون | 10,404 | `43c1fc6ecd55` | NOVA v5 — Online Naive-Bayes Order-Flow Classifier (M4 = مُقفل) | سليم | 19 | 0 |
| 245 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/quant.py` | بايثون | 4,802 | `e54535f2cd63` | NOVA v5 — طبقة الكوانت (M3): تشديد إضافي قبل محفّز الدخول | سليم | 7 | 0 |
| 246 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/risk.py` | بايثون | 3,028 | `0b460b300458` | NOVA v5 — إدارة المخاطر والتنفيذ الصارم (مُحافَظ عليه من v4.0.2) | سليم | 6 | 0 |
| 247 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/scoring.py` | بايثون | 2,625 | `2b23b604e559` | NOVA v5 — Six-Factor Scoring (M5, مُقفل 50/70/85) | سليم | 3 | 0 |
| 248 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/start.sh` | شل | 789 | `8ea78f1e5254` | NOVA v5 ZERO-WAIT QUANT — مشغّل سكالبينج (نسخة مسطّحة، بلا أسرار في الكود) | — | 0 | 0 |
| 249 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/telegram.py` | بايثون | 8,633 | `5693da601245` | NOVA v5 — تليجرام Async (M6) عبر aiohttp | سليم | 16 | 0 |
| 250 | `NOVA_bin_pending/جميع اصدارات البوت/NOVA_v5_bot_flat_X/NOVA_v5_flat/trigger.py` | بايثون | 4,115 | `9d17460a0c80` | NOVA v5 — محفّز الدخول (M3): Sweep → MSS → FVG/Tap | سليم | 5 | 0 |
| 251 | `NOVA_bin_pending/جميع اصدارات البوت/V0.0.1/bot_X/engine.py.txt` | بايثون | 25,867 | `1127def4f0b3` | NOVA v5 — المحرك الرئيسي (Orchestrator) + Telegram Interactive Wiring | سليم | 28 | 0 |
| 252 | `NOVA_bin_pending/جميع اصدارات البوت/V0.0.1/bot_X/execution.py.txt` | بايثون | 4,809 | `d0dd5894a43c` | NOVA v5 — التنفيذ المُوقّع + إدارة المراكز (M8) | سليم | 12 | 0 |
| 253 | `NOVA_bin_pending/جميع اصدارات البوت/V0.0.1/bot_X/nb.py.txt` | بايثون | 8,697 | `03da03b9398f` | NOVA v5 — Online Naive-Bayes Order-Flow Classifier (M4 = مُقفل) | سليم | 14 | 0 |
| 254 | `NOVA_bin_pending/جميع اصدارات البوت/V0.0.1/bot_X/telegram.py.txt` | بايثون | 20,802 | `81865a08d916` | NOVA v5 — Interactive Async Telegram (M6 — Refactored) | سليم | 21 | 0 |
| 255 | `NOVA_bin_pending/جميع اصدارات البوت/V3/nova_v5_forward_profiling_UPDATE2_X/engine.py` | بايثون | 55,452 | `5630ad3de167` | NOVA v5 — المحرك الرئيسي (Orchestrator) + Telegram Interactive Wiring | سليم | 43 | 0 |
| 256 | `NOVA_bin_pending/جميع اصدارات البوت/V3/nova_v5_forward_profiling_UPDATE2_X/nb.py` | بايثون | 10,397 | `ebec5996a2d1` | NOVA v5 — Online Naive-Bayes Order-Flow Classifier (M4) | سليم | 15 | 0 |
| 257 | `NOVA_bin_pending/جميع اصدارات البوت/V3/nova_v5_forward_profiling_UPDATE2_X/telegram.py` | بايثون | 30,231 | `7b27b51c7162` | NOVA v5 — Interactive Async Telegram (M6 — Forward-Profiling Refactor) | سليم | 27 | 0 |
| 258 | `NOVA_bin_pending/جميع اصدارات البوت/V3/nova_v5_forward_profiling_UPDATE2_X/trigger.py` | بايثون | 1,567 | `094be37d6292` | NOVA v5 — محفّز الدخول (Forward-Profiling build) | سليم | 0 | 0 |
| 259 | `census.py` | بايثون | 10,244 | `8ce565e64227` | coding: utf-8 | سليم | 8 | 2 |
| 260 | `extract.sh` | شل | 3,649 | `a4686a7d708a` | NOVA — إعادة اشتقاق شجرة الفحص new/ من الحزمة الأم بأمر واحد | — | 0 | 0 |

## ملاحظات
- «جروح» = عدد مواضع `__REDACTED__` (أثر المنقّي السري في نسخ المستودع القديمة).
- الملفات المعزولة (مفاتيح حقيقية) نُقلت إلى `new/_quarantine/` — انظر MAP.md هناك.
- كل ملف نصي (كود أو وثيقة) خضع لمسح المفاتيح — لا استثناءات.
- ملفات «بايثون المعطوب» الخمسة ليست كوداً فعلياً: اثنان `README.py` (وثيقة شرح
  بامتداد py) وثلاثة وثائق عربية تحوي كتل كود توضيحية (عقد/ملفات شاملة) —
  صنّفها الكاشف كوداً لتوفر تلميحات بايثون داخلها. لا يوجد أي ملف بوت معطوب في الحزمة.

