# L0008 — F197 dual deepening 1h

> الحالة: 📝 مسودة · 2026-09-17 · النوع: research · ميزانية الحوسبة: 6h
> مِلك: المسار يملأ `RUN` و`HANDOFF`؛ العقل يملأ `BRIEF` و`VERDICT` فقط.

## BRIEF (العقل → المسار)

**السؤال الواحد:** هل توسعة شبكة الخروج المزدوج على فريم الساعة تعبر البوابة على ستة رموز على الأقل مع هضبة صحيحة
**الفرضية القابلة للتكذيب:** الشبكة الموسعة حول القيم العابرة تعبر البوابة على ستة رموز فأكثر والمركز هضبة لا قمة معزولة
**النجاح يعني / الفشل يعني:** عبور ستة رموز فأكثر مع هضبة عشرين بالمئة وثبات عند الانزلاقات الثلاثة / عبور أقل من ستة رموز أو قمة معزولة أو انهيار عند أي انزلاق
**خارج النطاق (لا تفعله):** لا تعديل `nova_v8/**`، لا توسيع الشبكة أثناء التشغيل، لا إعادة تدوير نافذة الاختبار.

### نصّ الإطلاق — انسخه كما هو إلى محادثة المسار الجديد

```
اقرأ من github.com/stevearagonno1/NOVA-DRAGON : CONSTITUTION.md ثم docs/lanes/L0008-*.md
أنت «مسار تجربة». نفّذ BRIEF حرفياً ولا تخرج عنه.

0) التحضير
   git clone --depth 1 https://github.com/stevearagonno1/NOVA-DRAGON && cd NOVA-DRAGON
   python3 -m venv .v && . .v/bin/activate
   pip install -r requirements.txt          # مثبت لإصدارات المرجع (pandas 2.2.3 / numpy 2.3.5)
   mkdir -p ~/.nova_scratch/archive
   ln crypto_archive/BTCUSDT_1m.parquet ~/.nova_scratch/archive/ 2>/dev/null || \
     cp crypto_archive/BTCUSDT_1m.parquet ~/.nova_scratch/archive/
   export NOVA_ARCHIVE=~/.nova_scratch/archive      # الكاش يذهب خارج git — لا تكتب داخل المستودع

1) البوابة الإلزامية (لا تشغيل قبل PASS منها)
   python3 tools/canary.py --json
   # المطلوب: net=-98.59031619937323 trades=68 (أو Δnet ≤ 1e-9) وإلّا توقّف وأبلغ.

2) التنفيذ: read run_v5.py --help + docs/parts/directional-breakers.md + docs/lanes/L0007-hyp-lab-five-year.md then F-197-dual 1h extended grid TRIG 0.0015-0.0030 LOCK 0.0040-0.0060 plateau +-20pct slippage 0.03/0.10/0.30 unseen-holdout
   - لا تحذف sweep_train_partial.csv (آلية الاستكمال تعتمد عليه).
   - كل ~30 دقيقة: احفظ وأبلغ «كم/من» فقط. إن تجاوزت الميزانية 6h → أوقف وسلّم ما عندك.
   - أي فشل بيانات/ذاكرة/تعليق = سطر صريح في HANDOFF، لا حلّ خفي.

3) التدقيق قبل التسليم
   python3 tools/audit_lane.py <مجلد النتائج> --json      # ألصِق خلاصته في HANDOFF
   # إلزامي (D-0013): احفظ إعدادات التشغيل بجانب النتائج، وإلا لا تُعتمد:
   { echo "# $(date -u +%FT%TZ)"; env | grep '^NOVA_' | sort; echo "ARCHIVE=$NOVA_ARCHIVE";
     python3 -c "import sys,platform;print('py',platform.python_version())";
     python3 -c "import pandas,numpy,pyarrow;print('pandas',pandas.__version__,'numpy',numpy.__version__,'pyarrow',pyarrow.__version__)";
   } > <مجلد_النتائج>/env_dump.txt

4) السلّم الأخلاقي: سلّم الأرقام كما هي. السالب نتيجة كاملة. لا «تحسينات» بعد رؤية الاختبار.
```

## RUN (المسار — يوميات التنفيذ)

| وقت | ما | ملاحظة |
|---|---|---|
| | | |

## HANDOFF (المسار → العقل)

```
CANARY : PASS/FAIL + |Δnet| + الإصدارات (pandas/numpy/python)
أوامر التشغيل الحرفية:
ملفات مُنتَجة (المسار + الحجم + عدد الصفوف):
audit_lane.py: عدد الفحوص الناجحة + كل FAIL/NOTICE بنصّه
أرقام رأسية: عدد الصفوف، النتائج المميزة، أفضل/أسوأ net على التدريب والاختبار
أمانة: كل ما لم أستطع إثباته:
```

## VERDICT (العقل فقط)

**الحكم:** … · **الفحوص المُعاد اشتقاقها:** … · **ما تغيّر في المشروع:** … · **القرار التالي:** `D-xxxx` أو `Lyyyy`
