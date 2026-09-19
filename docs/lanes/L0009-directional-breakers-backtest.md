# L0009 — Directional breakers backtest

> الحالة: 📝 مسودة · 2026-09-19 · النوع: research · ميزانية الحوسبة: 3h
> مِلك: المسار يملأ `RUN` و`HANDOFF`؛ العقل يملأ `BRIEF` و`VERDICT` فقط.

## BRIEF (العقل → المسار)

**السؤال الواحد:** هل يعيش أي قاطع اتجاهي من الأربعة عشر (أو مركب النخبة أو مركب الكل) كمدخل طويل صاف على فريم الساعة بخروج قياسي أو مزدوج ضمن بوابة البروتوكول؟
**الفرضية القابلة للتكذيب:** قاطع واحد على الأقل يعبر البوابة (صافي موجب وعامل ربح 1.3 فأكثر ومئة صفقة فأكثر) على نافذة الاختبار على رمز واحد فأكثر
**النجاح يعني / الفشل يعني:** تركيبة واحدة على الأقل تعبر بوابة الاختبار على رمز واحد فأكثر مع ملفات تدقيق كاملة / صفر تركيبة عابرة على كل الرموز والفريمين، أو كل العبور من نواتج تعادل متحلل
**خارج النطاق (لا تفعله):** لا تعديل `nova_v8/**`، لا توسيع الشبكة أثناء التشغيل، لا إعادة تدوير نافذة الاختبار.

### نصّ الإطلاق — انسخه كما هو إلى محادثة المسار الجديد

```
اقرأ من github.com/stevearagonno1/NOVA-DRAGON : CONSTITUTION.md ثم docs/lanes/L0009-*.md
أنت «مسار تجربة». نفّذ BRIEF حرفياً ولا تخرج عنه.

0) التحضير
   git clone --depth 1 --filter=blob:none --sparse https://github.com/stevearagonno1/NOVA-DRAGON && cd NOVA-DRAGON
   git sparse-checkout set history tools nova_v8 docs CONSTITUTION.md    # بلا crypto_archive (732MB) — يُجلب بثاً
   python3 -m venv .v && . .v/bin/activate
   pip install -r history/docs/source/requirements.txt   # إصدارات المرجع (المسار الحي — الجذر بلا requirements)
   # لا تنزيل للأرشيف إطلاقاً: stream يجلب كل رمز إلى الذاكرة ثم يطرحه (نمط canary --source stream)
   export NOVA_HOME=~/.nova_scratch/home             # كتابة الإعداد خارج git

1) البوابة الإلزامية (لا تشغيل قبل PASS منها)
   python3 tools/canary.py --json --source stream
   # المطلوب: net=-98.59031619937323 trades=68 (أو Δnet ≤ 1e-9) وإلّا توقّف وأبلغ.

2) التنفيذ: python3 history/hyp_lab/run_breakers.py --tf both --source stream --trades
   - لا تحذف sweep_train_partial.csv (آلية الاستكمال تعتمد عليه).
   - كل ~30 دقيقة: احفظ وأبلغ «كم/من» فقط. إن تجاوزت الميزانية 3h → أوقف وسلّم ما عندك.
   - أي فشل بيانات/ذاكرة/تعليق = سطر صريح في HANDOFF، لا حلّ خفي.

3) التدقيق قبل التسليم
   for d in history/research/hyp_lab_out/L0009/F_213/*/ history/research/hyp_lab_out/L0009-tf4h/F_213/*/; do python3 tools/audit_lane.py "$d" --json; done   # لخّص كل FAIL/NOTICE في HANDOFF
   # إلزامي (D-0013): احفظ إعدادات التشغيل بجانب النتائج، وإلا لا تُعتمد:
   { echo "# $(date -u +%FT%TZ)"; env | grep '^NOVA_' | sort; } | tee -a history/research/hyp_lab_out/L0009/env_dump.txt >> history/research/hyp_lab_out/L0009-tf4h/env_dump.txt
   # (السائق كتب الإصدارات والبصمات في الملفين نفسيهما أثناء التشغيل)

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
