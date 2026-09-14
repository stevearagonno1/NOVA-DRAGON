# L{{ID}} — {{TITLE}}

> الحالة: {{STATUS}} · النوع: {{TYPE}} · ميزانية الحوسبة: {{BUDGET}}
> مِلك: المسار يملأ `RUN` و`HANDOFF`؛ العقل يملأ `BRIEF` و`VERDICT` فقط.

## BRIEF (العقل → المسار)

**السؤال الواحد:** {{QUESTION}}
**الفرضية القابلة للتكذيب:** {{HYPOTHESIS}}
**النجاح يعني / الفشل يعني:** {{SUCCESS}} / {{FAILURE}}
**خارج النطاق (لا تفعله):** لا تعديل `nova_v8/**`، لا توسيع الشبكة أثناء التشغيل، لا إعادة تدوير نافذة الاختبار.

### نصّ الإطلاق — انسخه كما هو إلى محادثة المسار الجديد

```
اقرأ من github.com/stevearagonno1/NOVA-DRAGON : AGENTS.md ثم docs/lanes/L{{ID}}-*.md
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

2) التنفيذ: {{COMMAND}}
   - لا تحذف sweep_train_partial.csv (آلية الاستكمال تعتمد عليه).
   - كل ~30 دقيقة: احفظ وأبلغ «كم/من» فقط. إن تجاوزت الميزانية {{BUDGET}} → أوقف وسلّم ما عندك.
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
