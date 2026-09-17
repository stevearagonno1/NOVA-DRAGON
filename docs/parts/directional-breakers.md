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
