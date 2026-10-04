# TASK-L0079 — اختبار نسخ إعدادات المؤشرات مع تسجيل كل تعديل

## الهدف

اختبار نفس المؤشر بعد تغييرات إعداداته، مع إبقاء كل نسخة فرضية مستقلة ومسمّاة، لمعرفة:

- أي إعداد يعطي دقة أعلى.
- أي إعداد يسبق بدايات الصعود.
- أي إعداد يحافظ على تغطية معقولة.
- هل يبقى التحسن خارج العينة أم يختفي.

هذه ليست إذنًا باختيار أفضل إعداد بعد رؤية holdout. الاختيار يكون من train فقط ثم يُجمّد.

---

## 1. مكان العمل والرفع

المستودع:

```text
https://github.com/stevearagonno1/NOVA-DRAGON.git
```

ابدأ من آخر فرع L0077:

```text
arena/l0077-expanded-three-families-2026-09-27
```

أنشئ:

```text
arena/l0079-parameter-variants-2026-09-27
```

النتائج في:

```text
history/research/hyp_lab_out/L0079/
```

والحكم في:

```text
docs/lanes/L0079-VERDICT.md
```

---

## 2. الفترة

### Train للاختيار

```text
2021-09-01 → 2024-08-31 UTC
```

### حظر

```text
18 شمعة 4H على الأقل
```

### Holdout بعد تجميد الأسماء

```text
2024-09-04 → 2026-08-30 UTC
```

النتيجة:

```text
+1 ATR قبل −1 ATR خلال 6 شموع 4H
```

والحساسية:

```text
+2 ATR قبل −1 ATR خلال 18 شمعة
```

لا إدارة صفقة، لا رسوم، لا رأس مال.

---

## 3. قاعدة تسمية النسخ

كل تعديل يحصل على `variant_id` ثابت، مثل:

```text
MACD_12_26_9
MACD_8_21_5
EMA_20_50
EMA_50_200
OBV_SMA20
OBV_SMA50
SFP_LOOK20
SFP_LOOK40
MSS_L5
MSS_L8
VPFR_L48_B24_VA70
```

لا تستخدم أسماء عامة مثل `best_macd` أو `tuned_ema`.

لكل نسخة سجل:

```text
variant_id
family
parameters
source_file
train_period
holdout_period
signal_definition
```

---

## 4. شبكة الإعدادات المقفلة الأولية

يجب تسجيل هذه الشبكة قبل التشغيل. لا تُضاف قيم أخرى بعد رؤية النتائج.

### MSS

```text
MSS_L3
MSS_L5
MSS_L8
```

### FVG

```text
FVG_3BAR_BASE
```

لا تُخترع عتبة فجوة جديدة؛ النسخة الحالية لا تحتوي إعدادًا مستقلًا آخر.

### SFP

```text
SFP_LOOK10
SFP_LOOK20
SFP_LOOK40
```

### RSI

```text
RSI2
RSI7
RSI14
```

مع الحفاظ على منطق الإشارة المقفل لكل طول.

### MACD

```text
MACD_8_21_5
MACD_12_26_9
MACD_19_39_9
```

### EMA

```text
EMA_10_30
EMA_20_50
EMA_50_200
```

### Stochastic

```text
STOCH_9_3_3
STOCH_14_3_3
STOCH_21_5_5
```

### OBV

```text
OBV_SMA10
OBV_SMA20
OBV_SMA50
```

### MFI وCMF

```text
MFI14
MFI20
MFI30
CMF14
CMF20
CMF30
```

### Bollinger/Z-Score

عائلة واحدة فقط:

```text
BB_20_1.5
BB_20_2.0
BB_50_2.0
```

لا تُحسب Z-Score كمرشح مستقل عن Bollinger.

### ADX/DI

```text
ADXDI_14_22
ADXDI_20_22
ADXDI_28_22
```

### Turtle Soup وDonchian

```text
TURTLE_20
TURTLE_55
DONCHIAN_20
DONCHIAN_55
```

### Volume Profile Fixed Range

لا يُشغّل إلا بعد تثبيت تعريفه الأصلي وإعداداته. إذا لم يقدم المستخدم المصدر أو الإعدادات، يُسجل `VPFR_PENDING` ولا تُخترع نسخة.

---

## 5. المقارنة

كل نسخة تُقاس منفردة على:

```text
MSS
FVG
SFP
```

ثم تُجمع النتائج الوصفية دون دمج مؤشرات.

لكل نسخة:

- عدد الإشارات.
- الحالات المحسومة.
- الدقة الاتجاهية.
- `hit_rate_all`.
- Wilson 95%.
- `MAE/MFE`.
- مدة الوصول للهدف.
- تغطية إشارات البنية.
- تغطية بدايات الصعود.
- نتيجة العشوائي.
- نتيجة كل أصل وكل سنة.

يجب عرض قائمتين:

1. أعلى دقة خام مهما كان حجم العينة.
2. أعلى دقة بين النسخ التي حققت عينة كافية وتغطية موثقة.

لا تُخفى النسخ الضعيفة.

---

## 6. التغطية المطلوبة

يُسجل مقياسان منفصلان:

```text
signal_coverage
= confirmed_valid / raw_structure_valid
```

و:

```text
rise_start_coverage
= بدايات الصعود التي سبقها المرشح / جميع بدايات الصعود المؤهلة
```

المقياس الثاني هو الأهم لسؤال: «من بدأ الإشارة قبل الصعود؟».

---

## 7. الاختيار والـholdout

لا يُختار الإعداد من holdout.

من train فقط:

- تُرتب النسخ داخل كل عائلة.
- تُسجل أعلى الدقة، حجم العينة، التغطية، والـWilson.
- تُختار النسخ التي ستُختبر لاحقًا.
- تُجمّد في commit مستقل.

بعد ذلك فقط يُقرأ holdout.

لا يوجد دمج ثلاثي في L0079. دمج أفضل ثلاثة يكون في ورقة لاحقة بعد تثبيت النسخ.

---

## 8. العشوائي والفحوص

```text
1000 سحب
seed = 79
```

الفحوص:

1. كل نسخة سببية ولا تستخدم المستقبل.
2. كل `variant_id` له إعداد مسجل.
3. لا تعديل بعد قراءة النتائج.
4. Bollinger وZ-Score عائلة واحدة.
5. VPFR لا يستخدم نطاقًا يدويًا اختير بعد رؤية الرسم.
6. train منفصل عن holdout.
7. لا إدارة صفقة أو رسوم.
8. لا أسرار.

---

## 9. الملفات المطلوبة

```text
history/hyp_lab/l0079_variants.py
history/hyp_lab/l0079_checks.py
history/hyp_lab/l0079_report.py

history/research/hyp_lab_out/L0079/preregistration_l0079.json
history/research/hyp_lab_out/L0079/variant_catalog_l0079.csv
history/research/hyp_lab_out/L0079/train_results_l0079.csv
history/research/hyp_lab_out/L0079/holdout_results_l0079.csv
history/research/hyp_lab_out/L0079/rise_coverage_l0079.csv
history/research/hyp_lab_out/L0079/random_control_l0079.csv
history/research/hyp_lab_out/L0079/checks_l0079.json
history/research/hyp_lab_out/L0079/REPORT-L0079.md

docs/lanes/L0079-VERDICT.md
```

الـcommit النهائي يجب أن يظهر على:

```text
arena/l0079-parameter-variants-2026-09-27
```

لا دمج إلى `main`، ولا تشغيل حي.
