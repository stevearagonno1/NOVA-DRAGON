# L0001 — donchian: إعادة التشغيل بمحاور المحرك الفعلية (DON_FILTER)

> الحالة: 📝 مسودة · 2026-09-13 · النوع: research · ميزانية الحوسبة: 30m
> مِلك: المسار يملأ `RUN` و`HANDOFF`؛ العقل يملأ `BRIEF` و`VERDICT` فقط.

## BRIEF (العقل → المسار)

**السؤال الواحد:** هل شبكة donchian الحالية (ENTRY1×EXIT1×FILTER = 40 تركيبة) تُنتج تركيبة موجبة خارج العينة؟
**الفرضية القابلة للتكذيب:** الماكرو/تشوبب الموثقة في الملفات القديمة غير موجودة في المحرك؛ الشبكة الحقيقية قد تعطي نتيجة مختلفة كلياً
**النجاح يعني / الفشل يعني:** تركيبة واحدة net>0 على holdout 2021-09:2023-08 مع trades>=30 / كل النهائيين سالبون خارج العينة ⇒ donchian تُغلق بلا نشر
**خارج النطاق (لا تفعله):** لا تعديل `nova_v8/**`، لا توسيع الشبكة أثناء التشغيل، لا إعادة تدوير نافذة الاختبار.

### نصّ الإطلاق — انسخه كما هو إلى محادثة المسار الجديد

```
اقرأ من github.com/stevearagonno1/NOVA-DRAGON : AGENTS.md ثم docs/lanes/L0001-*.md
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

2) التنفيذ: python3 nova_v8/sweep_engine.py --strategy donchian --symbol BTCUSDT --train 2023-09:2024-12 --test 2025-01:2026-08 --out sweep_results_donchian_v2
   - لا تحذف sweep_train_partial.csv (آلية الاستكمال تعتمد عليه).
   - كل ~30 دقيقة: احفظ وأبلغ «كم/من» فقط. إن تجاوزت الميزانية 30m → أوقف وسلّم ما عندك.
   - أي فشل بيانات/ذاكرة/تعليق = سطر صريح في HANDOFF، لا حلّ خفي.

3) التدقيق قبل التسليم
   python3 tools/audit_lane.py <مجلد النتائج> --json      # ألصِق خلاصته في HANDOFF

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
