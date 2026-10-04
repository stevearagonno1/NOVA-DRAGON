# L0084-ENTRY-MIX — التقرير الدستوري (نسخة عربية كاملة)

> كل رقم في هذا التقرير منسوخ من المخرجات المقيسة في `history/research/hyp_lab_out/L0084-entry-mix/`؛ والأمر القابل لإعادة الاشتقاق مذكور لكل جدول. **الدولار أولاً**، ثم ATR-R و barrier-R كوحدات منفصلة. ما لم يُقس يبقى حرفياً «not measured».

## بطاقة الثمانية أسطر

- L0084-ENTRY-MIX — 8 prefixes rolled; frozen: null (CASH)
- Universe: 12 assets 4h UTC 2021-01-01..2026-09-27; container fixed $20, ±1.5 ATR, horizon 18 bars, cost $0.052 round trip
- Attempts: 52 singletons + 3978 pair-modes + 0 registered triples (cap 1500/prefix)
- Holm family 70,330; bootstrap 2000×7-day blocks, seed 84, synchronised across assets
- Integrity: PASS (18 of 18 checks recorded, plus 16b full-run confirmation)
- Verdict scope: eligible hypothesis only; no adoption, no live orders, no profit forecast
- Future validation: NOT MEASURED until BOTH 100 trades and 90 days after the freeze commit
- Dollars first; ATR-R and barrier-R reported separately; legacy headlines documented, never re-based

## الجدول 1 — الأعداد والتعددية (multiplicity)

| البند | القيمة |
|---|---|
| الإعدادات | 52 |
| أزواج | 1,326 |
| أوضاع الأزواج المقيسة | 3,978 |
| الثواليث المتاحة نظرياً | 66,300 |
| سقف المحاولات لكل بادئة | 1,500 (قبل التنقيح) |
| أسرة هولم | 70,330 |
| الثواليث المسجَّلة (مجموع البادئات) | 0 |
| صفوف سلوك مكررة (نُقّحت) | 0 |
| صفوف سلوك فريدة | 0 |

## الجدول 2 — التصميم الزمني والنوافذ

| البادئة | نوافذ التحقق الداخلية | حُجب/تهدئة |
|---|---|---|
| 2023H1 | 2022H1; 2022H2 | 18 شمعة عند كل حد |
| 2023H2 | 2022H1; 2022H2; 2023H1 | 18 شمعة عند كل حد |
| 2024H1 | 2022H1; 2022H2; 2023H1; 2023H2 | 18 شمعة عند كل حد |
| 2024H2 | 2022H1; 2022H2; 2023H1; 2023H2; 2024H1 | 18 شمعة عند كل حد |
| 2025H1 | 2022H1; 2022H2; 2023H1; 2023H2; 2024H1; 2024H2 | 18 شمعة عند كل حد |
| 2025H2 | 2022H1; 2022H2; 2023H1; 2023H2; 2024H1; 2024H2; 2025H1 | 18 شمعة عند كل حد |
| 2026H1 | 2022H1; 2022H2; 2023H1; 2023H2; 2024H1; 2024H2; 2025H1; 2025H2 | 18 شمعة عند كل حد |
| 2026H2p | 2022H1; 2022H2; 2023H1; 2023H2; 2024H1; 2024H2; 2025H1; 2025H2; 2026H1 | 18 شمعة عند كل حد |

## الجدول 3 — البوابات والمعايير المقفلة

| البوابة | القيمة |
|---|---|
| صفقات منفذة لكل نافذة داخلية | ≥ 100 |
| أصول موجبة | ≥ 8 من 12 |
| PF | ≥ 1.3 |
| حد أدنى أحادي 95% (bootstrap كتل 7 أيام) | > 0 |
| تفوق مقترن | > 0 فوق كِلا الأبوين (زوج) / الأساس (فردي) / 3 أفراد وكل زوج مكوّن (ثلاثي) |
| ترتيب الأزواج المحتفظ بها | أسوأ حدّ ثم أصغر عدد ثم ID |
| الاختيار النهائي | أسوأ حدّ ثم أعضاء أقل ثم عدد أكبر ثم ID؛ وإلا CASH |

## الجدول 4 — الاختيار المتدحرج وأداء نافذة الهدف

| البادئة | المختار | النوع | أسوأ حدّ داخلي | أصغر عدد | نافذة الهدف: صفقات | فوز | توقع$ | حدّ أدنى | رفع مقابل no-signal (نقطة) |
|---|---|---|---|---|---|---|---|---|---|
| 2023H1 | CASH | cash | not measured | — | 0 | not measured | not measured | not measured | not measured |
| 2023H2 | CASH | cash | not measured | — | 0 | not measured | not measured | not measured | not measured |
| 2024H1 | CASH | cash | not measured | — | 0 | not measured | not measured | not measured | not measured |
| 2024H2 | CASH | cash | not measured | — | 0 | not measured | not measured | not measured | not measured |
| 2025H1 | CASH | cash | not measured | — | 0 | not measured | not measured | not measured | not measured |
| 2025H2 | CASH | cash | not measured | — | 0 | not measured | not measured | not measured | not measured |
| 2026H1 | CASH | cash | not measured | — | 0 | not measured | not measured | not measured | not measured |
| 2026H2p | CASH | cash | not measured | — | 0 | not measured | not measured | not measured | not measured |

## الجدول 5 — الضوابط المعاصرة

| المرشح | النافذة | صفقات | توقع$ | no-signal فوز | رفع (نقطة) | عشوائي 200 (توقع وسطي) | حدّ 5% | شراء-احتفاظ 1000$ | الفرق |
|---|---|---|---|---|---|---|---|---|---|
| NO-SIGNAL | 2022H1 | 1903 | -0.1576 | 0.4398 | not measured | not measured | not measured | not measured | not measured |
| NO-SIGNAL | 2022H2 | 1837 | -0.0660 | 0.4920 | not measured | not measured | not measured | not measured | not measured |
| NO-SIGNAL | 2023H1 | 1878 | -0.0665 | 0.4914 | not measured | not measured | not measured | not measured | not measured |
| NO-SIGNAL | 2023H2 | 1918 | -0.0275 | 0.5034 | not measured | not measured | not measured | not measured | not measured |
| NO-SIGNAL | 2024H1 | 1818 | -0.0666 | 0.4859 | not measured | not measured | not measured | not measured | not measured |
| NO-SIGNAL | 2024H2 | 2064 | -0.0266 | 0.5028 | not measured | not measured | not measured | not measured | not measured |
| NO-SIGNAL | 2025H1 | 1942 | -0.1029 | 0.4680 | not measured | not measured | not measured | not measured | not measured |
| NO-SIGNAL | 2025H2 | 1975 | -0.0607 | 0.5000 | not measured | not measured | not measured | not measured | not measured |
| NO-SIGNAL | 2026H1 | 1944 | -0.1330 | 0.4437 | not measured | not measured | not measured | not measured | not measured |
| NO-SIGNAL | 2026H2p | 889 | -0.0045 | 0.5487 | not measured | not measured | not measured | not measured | not measured |

## الجدول 6 — الجيران (±20%، عائلة هولم منفصلة)

لا جيران مُقاسون (لا نهائي مؤهل) ⇒ **not measured** بحسب القاعدة، لا إعفاء تلقائي.

## الجدول 7 — فحوص النزاهة الثمانية عشر

| # | الفحص | الحالة | الدليل |
|---|---|---|---|
| 1 | source pins and hashes | PASS | 17 fetches; mismatches=[]; commits outside pins=[] |
| 2 | exactly 52 setting names | PASS | unique=52; catalogue_rows=52 |
| 3 | 1,326 pairs / 3,978 pair modes | PASS | pairs=1326 pair_modes=3978 registry_rows=3978 |
| 4 | timestamp units, OHLC and volume integrity | PASS | 12 assets checked; problems=[] |
| 5 | contiguous bars and gap resets | PASS | intra-segment holes/edge masks: none; synthetic boundary test: no crossing, pre-gap signal rejected as incomplete (n=1) |
| 6 | prefix-truncation tests (all masks/modes) | PASS | 3 truncation points x 52 settings x 12 assets + 3 modes; mismatches=none |
| 7 | independent RSI/ATR/stochastic references | PASS | max abs err: RSI 3.55e-14, ATR 4.26e-09, %K 0.00e+00 |
| 8 | pivot signal emitted only after confirmation | PASS | pivot fires=[11] (>= 11); tail-safe=True |
| 9 | centered labels excluded from features | PASS | masks changed by truncation=none; labels changed on 1 bars; feature modules importing labels=none (label is evaluation-only) |
| 10 | synthetic container cases | PASS | {"fill_at_next_open": true, "timeout_at_18th_close": true, "adverse_gap_exit_at_open": true, "favourable_gap_withheld": true, "double_touch_stop_first |
| 11 | $20 sizing and $0.052 charged exactly once | PASS | 439 trades sampled (439); violations=none |
| 12 | cash and position constraints | PASS | one-position-per-asset and cash book >= 0 verified on 6 settings; violations=none |
| 13 | purge, embargo and temporal isolation | PASS | 15 kept of 159; embargo=18 bars; boundary leakage=0; candidate straddlers rejected=0 |
| 14 | parent selection precedes triple/target outcomes | PASS | {"order": ["triples_measured", "selection_written", "outer_measured"], "registry_content_frozen_before_measure": true, "selection_sha_before_target":  |
| 15 | confidence bounds/tests vs scipy references | PASS | {"wilson": "ok", "z": "ok", "holm": "ok", "bootstrap": "reproducible", "power": 396} |
| 16 | synthetic end-to-end deterministic rerun | PASS | {"mismatches": "none", "compared_trades": 599} |
| 17 | raw-ledger/table reconciliation | PASS | {"sample": 40, "violations": [], "hashes": {"trades.parquet": "ef0dc3804f553b829776595e2217aaee4aeeeda1fca35f216fa5e001761911f9", "metrics.parquet": " |
| 18 | workspace <=125MB, no secrets/pushes | PASS | {"workspace_mb": 65.16, "secrets": [], "branch": "arena/l0084-entry-mix-2026-10-04", "remotes": "none"} |

## بطاقة الحكم

- لا مرشّح مؤهل في البادئة الأخيرة ⇒ المجمّد = null والموقف الافتراضي CASH.
- الحالة المستقبلية: **NOT MEASURED** (لا شيء يُقاس بعد).
- تجميد: 2026-10-04T15:10:39Z؛ هذا فرز فرضيات، ليس اعتماداً ولا وعد ربح.

## المصلحتان (توثيق لا إعادة قياس)

1. صف Horizon الناقص في وراثة القياس قيمته 0.000 نقطة — يُوثّق ولا يُعاد بناؤه.
2. التكلفة المقاسة عند 0.0506$ تعطي حاجز تعادل 0.5169 في الوراثة، وحاجز هذا المسار يُحسب من الصفقات الفعلية 0.5 + mean(cost_ATR)/3 ولا يُنسخ.

## ملحق تشخيصي (وصفي فقط — لا يدخل الاختيار)

| البادئة | لا صفقات | <100 صفقة | <8 أصول موجبة | PF<1.3 | حدّ≤0 | تفوق مقترن≤0 | مؤهل |
|---|---|---|---|---|---|---|---|
| 2023H1 | 401 | 1839 | 3745 | 3536 | 3660 | 3661 | 0 |
| 2023H2 | 425 | 1903 | 3796 | 3675 | 3714 | 3717 | 0 |
| 2024H1 | 446 | 1983 | 3818 | 3736 | 3753 | 3756 | 0 |
| 2024H2 | 475 | 2000 | 3826 | 3749 | 3759 | 3762 | 0 |
| 2025H1 | 502 | 2006 | 3829 | 3760 | 3767 | 3770 | 0 |
| 2025H2 | 532 | 2020 | 3840 | 3774 | 3778 | 3781 | 0 |
| 2026H1 | 553 | 2028 | 3845 | 3777 | 3781 | 3783 | 0 |
| 2026H2p | 560 | 2037 | 3850 | 3788 | 3790 | 3792 | 0 |

أقرب المرشحين (بالحد الأدنى، وصفي):

| البادئة | المرشح | النمط | أسوأ حدّ | أصغر عدد |
|---|---|---|---|---|
| 2023H1 | P0038|AND2 | AND2 | -0.0834 | 105 |
| 2023H1 | P0738|OR0 | OR0 | -0.1091 | 478 |
| 2023H1 | P0346|AND2 | AND2 | -0.1132 | 138 |
| 2023H2 | P1293|AND0 | AND0 | -0.1507 | 327 |
| 2023H2 | P0017|AND2 | AND2 | -0.1536 | 151 |
| 2023H2 | P0744|OR0 | OR0 | -0.1543 | 541 |
| 2024H1 | P1293|AND0 | AND0 | -0.1507 | 327 |
| 2024H1 | P0017|AND2 | AND2 | -0.1536 | 151 |
| 2024H1 | P0744|OR0 | OR0 | -0.1543 | 541 |
| 2024H2 | P1293|AND0 | AND0 | -0.1507 | 231 |
| 2024H2 | P0790|AND2 | AND2 | -0.1555 | 658 |
| 2024H2 | P0347|AND0 | AND0 | -0.1775 | 145 |
| 2025H1 | P1293|AND0 | AND0 | -0.1507 | 231 |
| 2025H1 | P0790|AND2 | AND2 | -0.1555 | 658 |
| 2025H1 | P0771|OR0 | OR0 | -0.1795 | 683 |
| 2025H2 | P1293|AND0 | AND0 | -0.1507 | 231 |
| 2025H2 | P0771|OR0 | OR0 | -0.1795 | 678 |
| 2025H2 | P0770|OR0 | OR0 | -0.1820 | 666 |
| 2026H1 | P1293|AND0 | AND0 | -0.1507 | 231 |
| 2026H1 | P1066|OR0 | OR0 | -0.1938 | 603 |
| 2026H1 | P0941|OR0 | OR0 | -0.1988 | 603 |
| 2026H2p | P1066|OR0 | OR0 | -0.1938 | 603 |
| 2026H2p | P1293|AND0 | AND0 | -0.1950 | 231 |
| 2026H2p | P0941|OR0 | OR0 | -0.1988 | 603 |

السلسلة الوصفية الكاملة (12 نصف سنة) لكل الإعدادات الـ52 مع دفتر no-signal موجودة في `halfyears.csv`، منفصلة تماماً عن أداء الاختيار المتدحرج.

## المعجم الأول — وحدات (لا تُخلط)

| الوحدة | التعريف |
|---|---|
| gross/net dollars | (20/q)·(exit−q) ثم ناقص 0.052 مرة واحدة |
| ATR-R | (exit−q)/ATR مع cost_ATR = 0.0026·q/ATR |
| barrier-R | ATR-R ÷ 1.5 |
| f0 نسبة الفوز | الفائزون/المحسومون (بلا مهلات) |

## المعجم الثاني — أدوات المراجعة

| الأداة | الأمر |
|---|---|
| إعادة الاشتقاق من الدفتر | `python -m l0084_entry_mix.cli audit --rebuild-sample 1200` |
| الفحوص بعد القياس | `python -m l0084_entry_mix.cli check --phase post` |
| إعادة توليد الجداول | `python -m l0084_entry_mix.cli summarize` |

## ملاحظات صدق الحدود

- النوافذ التاريخية استكشاف لا إثبات أعمى؛ لا اعتماد من بيانات قديمة.
- دفتر الصفقات الكامل (13.29M صفقة على كامل الشبكة) لا يُخزَّن صفاً صفاً داخل سقف 125MB؛ تُخزَّن المفاتيح المضغوطة لكل صفقة (`trades_keys.parquet`) مع أمر إعادة بناء بايت-دقيق، والصفوف الكاملة للصفقات المُبلَّغ عنها في `trades.parquet`.
- إحصاءات مرشحي الشبكة غير المُبلَّغ عنهم محصورة في بوابات الأهلية؛ الإحصاءات الموسعة (MDD، مدة، أسوأ يوم، انكشاف) للأفراد ولمرشحي البادئات والثواليث المؤهلة.