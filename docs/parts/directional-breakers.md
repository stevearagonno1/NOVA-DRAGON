# ملف القواطع الاتجاهية

## الأمر المؤسس والحالة

- أنشئ هذا الملف بأمر القائد في سبتمبر سنة ألفين وستة وعشرين
- الفكرة ملف خاص لكل جزء نطوره إلى الأقصى ثم ننتقل لغيره
- القواطع الاتجاهية هي الجزء الأول المختار من القائد نفسه
- هذا الملف هو بيت كل ما يخص القواطع من معلومات وتفاصيل

user order 2026-09-17 : one dossier per part, breakers first
status : living dossier, sequential development plan

## الهوية الرسمية

- القواطع هي جناح الدخول الاتجاهي في المحرك
- حالته الرسمية نشطة مع جناحين آخرين
- حكمه البحثي مثبت بالانتخاب وهو الافتراضي الرسمي

nova_v8/strategy_registry.py : directional, Directional trigger sleeve, active
docs/RESEARCH-JUDGMENTS.md : section 5, elected, official default

## الحكم الرسمي الكامل

- النخبة ثمانية قواطع منتخبة خفضت الجرح تسعة وسبعين بالمئة
- القاعدة المستخرجة أي قاطع يتجاوز خمس إشارات شهريا مضخة تكاليف
- الفائض خارج النخبة مستبعد من فريم الدقائق الخمس
- المستبعد يعاد تقييمه على فريم الساعة فما فوق مستقبلا

elite 8 : MACD EMA KAMA OBV ADX Stochastic SFP MSS
wound reduction : -79%, elite = official default
cost-pump rule : > ~5 signals per month = rejected
surplus rule : excluded from 5m, re-evaluate on 1h+

## قاعدة الاشتباك

- أي قاطع يشتعل يفتح صفقة والأول اشتعالا يفوز
- لا فتح إلا في النظام الاتجاهي صاعد أو هابط فقط
- الترتيب أربعة عشر قاطعا بالأولوية عند التزاحم
- أحداث البنية تصدر أيضا لأنها تغذي أوراكل الحقيقة

nova_v8/triggers.py : first-to-fire-wins, bull-bear only
PRIORITY 14 : MSS FVG SFP MicroBurst RSI MACD Bollinger EMA ADX Stochastic OBV SuperTrend RSI7 KAMA

## خريطة النخبة في الكود

- كل قاطع من الثمانية يعيش في ملفات الإعداد والمؤشرات والاشتعال
- كسر الهيكل وفشل التأرجح يمتدان أيضا إلى البنية الدقيقة والبوابة
- متوسط الحركة منتشر في كل الأجنحة لأنه مرجع عام

MACD : config + indicators + triggers
EMA : config + indicators + triggers + all sleeves (common ref)
KAMA : config + indicators + triggers + dynamic_grid
OBV : config + indicators + triggers
ADX : config + indicators + triggers + dynamic_grid + regime + synth
Stochastic : config + indicators + triggers
SFP : config + indicators + triggers + long_cycle + microstructure + smc
MSS : config + indicators + triggers + btc_leadlag + long_cycle + microstructure + oracle + smc

## المحرك الرياضي

- كل المؤشرات سببية لا تعيد الرسم وقيمتها من الماضي فقط
- المؤشرات تجمع الأصيلة والكلاسيكية معا في ملف واحد
- النظام يقرأ من فريم أعلى ويثبت لحظة الدخول ولا يتغير وسط الصفقة
- الأنظمة أربعة صاعد وهابط ومتقطع وصادم

nova_v8/indicators.py : causal, non-repainting, t depends on data <= t
bespoke : ALMA Cardwell-RSI hysteresis anchored-KAMA Hurst MSS FVG SFP
classic : RSI14 MACD Bollinger EMA50-200 ADX Stochastic OBV SuperTrend
nova_v8/regime.py : higher-TF read, fixed at entry, 4 regimes

## الحقيقة الصعبة بأمانة كاملة

- نواة كسر الهيكل كمدخل مستقل ميتة على خمس سنوات
- ثمانية رموز من ثمانية سالبة على التدريب والاختبار معا
- ملف النواة المستقلة مغلق بحكم الحارة السابعة الحاسم
- لكن النواة مع الخروج المزدوج تعبر البوابة على فريمي الساعة والأربع ساعات
- الدرس النواة سائق ممتاز ومدخل مستقل فاشل
- محور التهدئة ميت على سائق الدقائق الخمس لتباعد الإشارات

L0007 : F-126 MSS core 8/8 negative train+test, PF 0.28-0.54, DEAD standalone
L0007-tf : F-197 dual exit on MSS core crosses on 1h 6/40 + 4h 2/40
L0007 : F-205 cooldown axis dead on 5m driver, needs richer driver
lesson : MSS = great driver, failed standalone entry

## البوت التاج

- البوت الموحد يستخدم نسخة مصغرة من كسر الهيكل في التنقيط
- نقاط الكسر عشرون ونافذة البحث اثنتا عشرة شمعة
- النخبة الثمانية الكاملة ليست في البوت بل في المحرك البحثي
- المحرك مختبر والبوت تاج والترجمة بينهما بعقد صارم

bot/NOVA.py : mini-MSS scoring, SCORE_MSS_PTS = 20, LOOKBACK = 12
bot/NOVA.py : MACD KAMA OBV ADX STOCH SFP = 0 hits, elite lives in engine
engine vs bot : research vs crown, strict translation contract

## الملفات المرتبطة

- سجل الأحكام يحمل الحكم الرسمي والقاعدة الذهبية
- حارة الجولة الأولى وثقت موت النواة على نافذة السنة
- حارة السنوات الخمس وثقت الموت الحاسم والعبور الفريمي
- مجلد الفرضيات يحمل العقد والجرد النهائي ولوحة الخط
- مجلدا نتائج المسح يحملان جولتي الاتجاه والسلاحف

docs/RESEARCH-JUDGMENTS.md : section 5 verdict
docs/lanes/L0006-hyp-lab-first-sweep.md : F-126 dead on 2026 window
docs/lanes/L0007-hyp-lab-five-year.md : F-126 dead 5y, F-197 crosses 1h+4h
history/hypotheses/ : factory contract + final inventory + elite + board
history/sweep_results/ : adaptive_trend + donchian rounds

## فرص التطوير العشر

- الأولى إعادة تقييم الفائض على فريم الساعة فما فوق بحكم مسجل
- الثانية تطوير النواة كسائق مبوب لا كمدخل مستقل
- الثالثة آلة الحالات كسائق جديد مختلف الارتباط بتوصية الحارة
- الرابعة فلتر الحجم الذكي فلا دخول إلا بتوسع حقيقي
- الخامسة مرشح التقلب المزدوج فلا دخول في تقطع قاتل
- السادسة ساعات الجلسات فلا مسالمة في سيولة ميتة
- السابعة الدخول الوريث إعداد خاص لكل عملة من نتائج مسحها
- الثامنة مقياس الحصص الديناميكي حسب سلاسل الفوز والخسارة
- التاسعة حارس الخمس إشارات شهريا لمنع مضخات التكاليف
- العاشرة جسر البوت نقل نقاط التنقيط المجربة إلى المحرك

ordered by : verdict orders first, lane verdicts second, backlog third
F-146 : state machine, next recommended driver, different correlation
BACKLOG.md : ideas 2 3 4 7 8 feed this part directly

## بوابة الخروج المقترحة

- عائد لا يقل عن ثلاثة أعشار فوق الواحد
- مئة صفقة على الأقل في القياس النهائي
- هضبة تتحمل عشرين بالمئة حول الإعداد المختار
- نافذة مستقلة لم ترها عين البحث أبدا
- تفوق على الاحتفاظ في نفس الفترة وإلا فلا معنى
- ثبات عند مستويات الانزلاق الثلاثة

PF >= 1.3, trades >= 100, plateau +-20%, unseen holdout
vs BuyHold : must win same period, slippage 0.03 0.10 0.30 pct
source : section 16 + live/LIVE-TRADING-RULES.md adoption gate

## سجل العمل

- سبتمبر ألفين وستة وعشرين إنشاء الملف بأمر القائد مع البحث الشامل

2026-09-17 : dossier created by user order + full repo search

## المصادر

- كل رقم أعلاه مشتق من الملفات التالية مباشرة

nova_v8/strategy_registry.py
nova_v8/triggers.py
nova_v8/indicators.py
nova_v8/regime.py
nova_v8/smc.py
docs/RESEARCH-JUDGMENTS.md
docs/lanes/L0006-hyp-lab-first-sweep.md
docs/lanes/L0007-hyp-lab-five-year.md
history/hyp_lab/F_126_mss_core.py
history/hypotheses/
BACKLOG.md
bot/NOVA.py

## جولة الإخضاع الكاملة للقواطع (2026-09-19)

- الأمر: القائد أمر أن يجرب هذا الملف كل استراتيجيات القواطع الاتجاهية
- وأمر بمحادثة مستقلة مرتبطة بالمنصة تجري الباكتست على الأرشيف التاريخي
- النطاق: أربعة عشر قاطعا منفردا ومركب النخبة ومركب الكل — طرف طويل فقط
- الخروج: القياسي المشترك والمزدوج بتركيبة الجولة الذهبية المقاسة
- الفريم: ساعة أساس وأربع ساعات ثان — الخمس دقائق مقضي فيها بقاعدة التكاليف
- المحرك كما هو يستورد ولا يعدل — الشروط حرفية من ملفاته المجمدة
- بلا بوابة نظام في هذه الجولة — عزل جودة المدخل وتفاعل النظام قرار لاحق

F_213 : history/hyp_lab/F_213_breakers.py — رقم بعد نطاق المصنع 212
driver : history/hyp_lab/run_breakers.py — نفس بروتوكول L0007 حرفا
lane : docs/lanes/L0009-directional-breakers-backtest.md
dual spec : trig 0.0025 · lock 0.0045 · wide 0.0020 · tight 0.0008 (L0007-tf1h)
grid : 16 triggers x 2 exits = 32 combos per symbol, 8 approved symbols
gates : net>0 and PF>=1.3 and trades>=100 on test window only
stream : كل رمز يجلب للذاكرة بلا تنزيل الأرشيف 732MB

## سجل العمل — إلحاق 2026-09-19

- سبتمبر ألفين وستة وعشرين فتح جولة الإخضاع بأمر القائد مع ملفين جديدين
- التوثيق: سطر قرار مئتان وثلاثة عشر وكتلة سجل بنفس التاريخ

D-0036 : docs/DECISIONS.md — فتح L0009 + تجربة F-213 بأمر القائد
LOG : LOG.md — جولة إخضاع القواطع 2026-09-19

## نتيجة جولة الإخضاع (2026-09-19 — بعد تدقيق العقل)

- اثنتا عشرة خلية من ست عشرة عبرت بوابة الامتحان — ست على كل فريم
- أفضل الخلايا: ريندر رباعية 8813.55 دولارا بعامل ربح 4.09 ثم فايل 5937.69
- الاحتفاظ سالب على الرموز الثمانية كلها في الامتحان فتفوق البوت موثق في ثلاث عشرة خلية
- بيتكوين ميت على الفريمين ولينك ينهار رباعيا من قمة تدريبه — مسطران بلا تجميل
- هيمنة مركب الكل بنيوية متوقعة — فصل القاطع الفائز الحقيقي مهمة الجولة العاشرة
- الحكم: نطور ولا اعتماد — الجوار والعمياء والانزلاق المجهد لم تقس بعد

audit : brain re-run main@2c687a2 — 16/16 cells byte-equal
buyhold : test window negative on all 8 symbols (-172 to -867 per 1000)
verdict : develop not adopt — D-0037 — L0010 awaits user permission


## جولة الضغط L0010 (2026-09-19) — مصير الحافة محسوم

- النطاق: أقفال L0009 كما هي بلا لمس — خمسة محاور: مصفوفة امتحان · انزلاق مجهد 0.10%/0.30% · عمياء 2021-2023 · جوار ±20% · تفكيك مركب الكل · فريما 1h و4h على الثمانية
- الحكم (D-0038): **فريم 1h مدفون** (لا قاطع ينجو عند 0.30% — الثمانية سالبون) · **سلة 4h الستة ناجية:** ‏+32,608.11‏$ أساس · ‏+25,681.09‏$ عند 0.10% · ‏+4,033.40‏$ عند 0.30% · نجوم الضغط: RENDER/FIL/XLM
- الشواهد: عمياء 4h موجبة 4/4 حيث قيست (SOL ‏+10,246.61‏ الأعلى) · جوار 8/8 للستة · تفكيك الـ14 لا يقلب خلية ⇒ الحافة سلة أنماط لا خيط واحد
- المطرودان بالدليل: BTC وLINK (0/8 جوارًا، سالبان في العمياء) · غير مقاس قبل L0011: DSR · الهبوط الأقصى · زمن الاحتفاظ · عمياء GRAM/RENDER
- الأدلة: غرفتان × جولتان بايتيًا واحدة — 124 ملفًا في history/research/hyp_lab_out/L0010/ + التقرير الكامل في docs/lanes/L0010


## جولة التوسعة L0012 (2026-09-19) — أول اختبار للقواطع خارج الثمانية

- النطاق: نفس البروتوكول حرفًا على ثماني عملات غير ممتحنة بفريم 4h (ATOM · BNB · DOGE · IMX · PEPE · SHIB · TON · VET) — وHNT مستبعد بدليل تغطية (بياناته تنتهي 2022-10-14)
- النتيجة: **سبع عابرة** — IMX ‏+7,876.21‏$ (PF 3.23) · PEPE ‏+6,962.92‏$ · VET ‏+5,510.45‏$ · DOGE ‏+4,994.62‏$ · SHIB ‏+4,697.64‏$ · ATOM ‏+4,343.97‏$ · TON ‏+3,691.74‏$ — والساقط BNB ‏−1,379.49‏$ (PF 0.89)
- سلة الثماني في الامتحان: ‏+36,698.04‏$ (5,771 صفقة · PF 2.00 · ‏+6.36‏$/صفقة) مقابل احتفاظ ‏−5,591.08‏$ على النافذة نفسها ⇒ الفرق ‏+42,289.12‏$
- الشواهد: اختيار المزدوج/الكل في السبع كلها · الاحتفاظ قوي في التدريب (PEPE ‏+23,639.38‏$) وضعيف سالب في الامتحان — يوثق لا يخفى
- الحدود: محاور الضغط (جوار · عمياء · انزلاق مجهد · استقرار إحصائي) غير مقاسة — لا اعتماد قبلها
- الأدلة: `history/research/hyp_lab_out/L0012/` (34 ملفًا) + التقرير الكامل بقالب القسم 23 في `docs/lanes/L0012-expansion-untested-4h.md`


## جولة ضغط نجوم التوسعة L0013 (2026-09-19) — الحافة عبرت وثلاثة رموز لا تصمد عند أقصى انزلاق

- النطاق: السبعة العابرة من L0012 على 4h بخمسة محاور ضغط (مصفوفة · انزلاق مجهد · عمياء · جوار ±20% · تفكيك) — تركيبات مقفلة بلا إعادة اختيار
- الأساس: سلة ‏+38,077.55‏$ · 5,169 صفقة · PF 2.56 · هبوط 717.19$ · احتفاظ 6.30 ساعة · DSR z=16.43
- الجوار: 9/9 لكل رمز · العمياء 2021-2023: 6 من 7 موجبة بقوة (سلة ‏+50,804.29‏$) · TON بلا نافذة بنيويًا
- الانزلاق المجهد: 0.10% كلها موجبة · 0.30% نجاة 4 من 7 (IMX · PEPE · VET · DOGE) وسقوط ATOM وTON وتعادل SHIB
- ضد الاحتفاظ: ‏−5,568.44‏$ للاحتفاظ مقابل ‏+38,077.55‏$ للبوت (فرق ‏+43,645.99‏$)
- التفكيك: لا حامل واحد — الحامل الأكبر يختلف بالرمز (MicroBurst · FVG · OBV)
- التدقيق: تشغيلان مستقلان — 62 ملفًا، 61 مطابق بايتيًا والفرق سطر مدة التشغيل فقط
- الحكم المقترح: نطوّر — الاعتماد مشروط بقياس كلفة التنفيذ الحية (مسبار ورقي بإذن صريح)
- الأدلة: `docs/lanes/L0013-expansion-stars-stress.md` + `history/research/hyp_lab_out/L0013/`
