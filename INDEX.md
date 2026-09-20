# فهرس المستودع — NOVA V8

الهيكل من `tools/organize_incoming.py`. المكرر الحرفي (نفس sha256) شُطب، وغيره نُقل بمساره — ولا معلومة ضاعت.
آخر تنظيم: 2026-09-14 | الملفات الواردة: 523 | منقولة: 332 | محذوفة لتطابقها: 191
تحديث إعادة التنظيم 2026‑09‑16 (الدفعة ١ — قرار الخطة §٥): نُقلت المجموعات التاريخية إلى `history/` (bot_versions · archive · hypotheses · hyp_lab · research · sweep_results · sweep_results_donchian_v2 · library) والمسودات إلى `old/` (code_drafts) — القرار `D‑0021` رافق تحديث الأدوات الحية. الممنوع تحريكه لم يُمس (بند الخطة §٢-١).
تحديث إعادة التنظيم 2026‑09‑16 (الدفعة ٢ — القرار `D‑0022`): ملف قواعد التداول الحي انتقل إلى `live/` + وثيقة ربط `live/README.md`، والحزمة `nova_upload_bundle.tar.gz` إلى `history/`، و`fetch_archive.py` بقي في الجذر بعد مسح إشارات بلا أي مرجع حي.
تحديث إعادة التنظيم 2026‑09‑16 (الدفعة ٣ — القرار `D‑0023`): الكنز النقي الفريد (٢٠٠ نسخة ببصماتها الكاملة) في `history/clean/` مع الشهادة `MANIFEST-CLEAN.md`؛ المكررات في `old/bundle_rest/` غير المتعقبة بالتصميم؛ أُغلق staging `new/` وبقي المعزل السري في `new/_quarantine/`.
تحديث إعادة التنظيم 2026‑09‑16 (الدفعة ٤ — القرار `D‑0024`): بُني `bot/` من التاج — `bot/NOVA.py` نسخة حرفية من النقي (بصمة `3e08f1f8f103…`، ٢٦٢ دالة، صفر جروح) + وثيقة النسب؛ الأصل بقي في `history/clean/`.
تحديث إعادة التنظيم 2026‑09‑16 (دفعة وثائق النتائج — نقطة القرار ٣، القرار `D‑0025`): وثائق النتائج (التقارير والمحادثة والمتفرقات والمصادر والمكتبة + الملفات الموسومة بالتاريخ) انتقلت إلى `history/docs/` بعد مسح الإشارات؛ بقي في `docs/`: الدستور والتعديلات و`BRAIN.md` و`DECISIONS.md` و`HANDOFF.md` ومصنع الفرضيات وأحكام البحث وخطة التنظيم ووثيقة المنفِّذ والتصاميم + آلية الحارات الحيّة (`docs/lanes/` — تستقبل الجديد عبر `tools/new_lane.py`).
تحديث المرآة: 2026‑09‑14 — صُححت مسارات ما نُقل بعد التنظيم (الجذر → `history/docs/source` و`history/archive`؛ `history/docs/misc/مؤشرات` → `history/library/indicators`؛ `history/docs/misc/ملفات` → `history/docs/library`) وأُضيف الجديد. فحص المطابقة وأوامره: `history/docs/STATS-2026-09-14.md` §6.

| `history/library/indicators` | مكتبة المؤشرات: 129 ملفاً (مؤشرات/0..7) — خامات أفكار الفلاتر |
| `history/docs/library` | 14 ملفاً مرجعياً (أدلة ومؤشرات نصية) |

تحديث الصقل النهائي 2026-09-17 (D‑0030): الفهرس يُولَّد بأمر واحد `python3 tools/build_index.py` — البنية مجمدة، والسرد التاريخي أعلاه محفوظ بلا مساس.

تحديث الصقل النهائي 2026-09-17 (D‑0030): الفهرس يُولَّد بأمر واحد `python3 tools/build_index.py` — البنية مجمدة، والسرد التاريخي أعلاه محفوظ بلا مساس.

تحديث الصقل النهائي 2026-09-20 (D‑0030): الفهرس يُولَّد بأمر واحد `python3 tools/build_index.py` — البنية مجمدة، والسرد التاريخي أعلاه محفوظ بلا مساس.


## خريطة المجلدات

| البيت | الملفات | ما فيه |
|---|---|---|
| `bot/` | 3 | البوت الجاهز للتشغيل — التاج V7.0.1 النقي (NOVA.py + النسب + شهادة الجهوزية) |
| `live/` | 3 | التداول الحي: القواعد الملزمة + وثيقة الربط + توثيق المنفِّذ F-197 |
| `nova_v8/` | 27 | المحرك المقدَّس — لا يُعدَّل إلا بقرار D (البند ١١) |
| `data/` | 8 | باركيه البيانات + MANIFEST.md المقدَّس — لا يُمس |
| `crypto_archive/` | 17 | البيانات الضخمة (عملات 1m — أغلبيتها ٥ سنوات) — لا يُمس |
| `tools/` | 16 | كل أدوات المستودع بلا استثناء: الفحص والتنظيم والدمج والخريطة |
| `docs/` | 70 | الوثائق: الست الدستورية في المستوى الأول + constitution/ designs/ lanes/ security/ |
| `new/` | 5 | بوابة استقبال الحزم: أداتا الإحصاء والاستخراج + الشهادات + خريطة المعزل السري |
| `history/` | 2156 | المظلة الأرشيفية — كل مادة تاريخية/اختبارية (لا يُعاد ترتيبه داخلياً) |
| `old/` | 18 | المتقاعد: المسودات + مكررات الحزمة القابلة للاشتقاق بأمر واحد |
| ملفات الجذر | 8 | طبقة الدخول الدستورية + هذا الفهرس |

## الملفات التشغيلية (الجذر والبيوت الحيّة)

**الجذر:** `.gitattributes` · `.gitignore` · `BACKLOG.md` · `CONSTITUTION.md` · `INDEX.md` · `LOG.md` · `README.md` · `دستوري.txt`

**`bot/`** (3 ملفاً):
- `bot/NOVA.py` (0K)
- `bot/READINESS-CHECK.md` (0K)
- `bot/README.md` (0K)

**`live/`** (3 ملفاً):
- `live/EXECUTOR-F197.md` (0K)
- `live/LIVE-TRADING-RULES.md` (0K)
- `live/README.md` (0K)

**`tools/`** (16 ملفاً):
- `tools/archive_report.py` (3K)
- `tools/audit_lane.py` (12K)
- `tools/backtest_stream_demo.py` (2K)
- `tools/build_index.py` (4K)
- `tools/canary.py` (7K)
- `tools/combo_probe.py` (3K)
- `tools/executor_f197.py` (32K)
- `tools/f197_plateau.py` (8K)
- `tools/fetch_archive.py` (4K)
- `tools/merge_main.sh` (2K)
- `tools/new_lane.py` (3K)
- `tools/organize_incoming.py` (12K)
- `tools/rebuild_archive.py` (2K)
- `tools/redact_bundle_keys.py` (11K)
- `tools/restate_lab_dollars.py` (1K)
- `tools/test_executor_f197.py` (9K)

**`new/`** (5 ملفاً):
- `new/CENSUS.md` (0K)
- `new/CROWN-CHECK.md` (0K)
- `new/census.py` (0K)
- `new/extract.sh` (0K)

**`docs/`** (70 ملفاً):
- `docs/BRAIN.md` (15K)
- `docs/CONSTITUTION-AMENDMENTS.md` (13K)
- `docs/DECISIONS.md` (44K)
- `docs/HANDOFF.md` (26K)
- `docs/HYPOTHESIS-FACTORY.md` (2K)
- `docs/REPORT-LANGUAGE.md` (1K)
- `docs/RESEARCH-JUDGMENTS.md` (6K)

**`docs/constitution/`** (1): `الدستور_القائد_المرآة_العربية.md`

**`docs/designs/`** (8): `استراتيجيتان_منفصلتان_NOVA_V8_وثيقة_مبدئية.txt` · `تصميم_NOVA_V8_النهائي.txt` · `تصميم_NOVA_v8_المتفق_عليه.txt` · `تصميم_محرك_الواجهة.md` · `دليل_الرموز.txt` · `عقد_الترجمة_البرمجية.txt` · `مراجعة_قرارات_تصميم_NOVA.txt` · `وثيقة_تفويض_تطوير_NOVA_V8_المنهج_المحافظ.txt`

**`docs/lanes/`** (17): `INDEX.md` · `L0000-adaptive-trend-1920.md` · `L0001-donchian-current-engine-grid.md` · `L0002-grid-collapse-dead-axes.md` · `L0003-adoption-gate-holdout.md` · `L0006-hyp-lab-first-sweep.md` · `L0007-hyp-lab-five-year.md` · `L0008-f197-dual-deepening-1h.md` · `L0009-directional-breakers-backtest.md` · `L0010-breakers-stress-round.md` · `L0012-expansion-untested-4h.md` · `L0013-expansion-stars-stress.md` · `L0014-unified-portfolio-13.md` · `L0015-capital-sizing-13.md` · `L0016-state-machine-f146.md` · `LAB-YARDSTICK-20.md` · `_TEMPLATE.md`

**`docs/security/`** (1): `KEY-ROTATION-GUIDE.md`

## الأرشيف بالأرقام (تراكمي — لا يُعاد ترتيبه)

| المجموعة | ملفات |
|---|---|
| `history/` | 1 |
| `history/archive/` | 24 |
| `history/bot_versions/` | 92 |
| `history/clean/` | 201 |
| `history/docs/` | 70 |
| `history/hyp_lab/` | 24 |
| `history/hypotheses/` | 4 |
| `history/library/` | 129 |
| `history/research/` | 1598 |
| `history/sweep_results/` | 7 |
| `history/sweep_results_donchian_v2/` | 6 |
| `old/bundle_rest/` | 1 |
| `old/code_drafts/` | 17 |
| **الإجمالي المتعقَّب** | **2331** |

---
*وُلِّد آلياً بأمر `python3 tools/build_index.py` — البند ١٠: كل رقم قابل لإعادة الاشتقاق.*
