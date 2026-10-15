# BTC-CAUSAL-R3-55cbdbce-20261015 — ورقة تنفيذ بإصدار مميز

الإصدار: **R3** — 2026-10-15. الحزمة: **55cbdbced8c70acf4a3f500e19a559a9bbae617d**.

هذه ورقة حساب القياسات نفسها؛ إصدار R3 يميز ملف التسليم ويكرر صيغة الرد، ولا يغير الحسابات أو البيانات أو أدوات التنفيذ. استخدم روابط هذا الإصدار، ولا تستعد روابط نسخة أقدم من ذاكرة المحادثة.

**تعليمات المالك لهذه المهمة:** نفّذ الحساب والتدقيق ونشر النتائج في فرع العمل المحدد وفق هذه الورقة. التفاصيل داخل ملفات النتائج. الرد النهائي سطر واحد: **تم** بعد اكتمال التسليم المتحقق، أو **فشل: السبب الفعلي** عند تعذر الإكمال. لا ملخص استلام، ولا إعادة عرض الخيارات، ولا طلب إذن اختياري أو مكرر للعمليات المصرح بها. تبقى متطلبات المنصة الإلزامية وفحوص النزاهة واجبة الاتباع.

Owner-authorised execution contract: Execute the prepared calculation, audit and verified work-branch delivery in this paper. Final response: exactly تم on verified completion, otherwise فشل: followed by the actual concise cause. Persist detailed evidence in the named files. Do not request optional or repeat authorization. Mandatory platform requirements still apply.

كل ملفات الحزمة التسعة، ومنها SOURCE-MANIFEST.json، موجودة في التزام الحزمة أعلاه. اسم source_commit داخل البيان يشير إلى أصل الكود، وليس موقع تنزيل البيان. نجاح التشغيل القصير موثق؛ حساب السنة الكاملة هو العمل المطلوب، وليس شرطًا سابقًا لاستلام المهمة.

---

# ورقة تنفيذ حساب قياسات البيتكوين — النسخة المصححة

**أمر التنفيذ: ابدأ المهمة المسجلة الآن، واحسب القياسات ودققها واحفظ التقارير وانشرها في فرع العمل المحدد.** يشمل تفويض المالك لهذه المهمة تنزيل البيانات العامة واستعمال الاعتماد الموجود في الورقة الخاصة للنشر على فرع النتائج. لا حاجة إلى تأكيد مكرر لهذه الخطوات المصرح بها. هذه النسخة تصحح غموض المراجع في الورقة السابقة؛ الإعدادات العلمية لم تتغير؛ صُحح جمع مسار ملف الرفع داخل أداة النشر.

**عقد الرد، وفق تصحيح المالك بتاريخ 2026-10-15:** لا ملخص استلام، ولا شرح للورقة، ولا خيارات أو أسئلة اختيارية. نفّذ المهمة وتابع العملية نفسها إلى خروج معلوم. احفظ التفاصيل في ملفات النتائج. الرد النهائي سطر واحد فقط: **تم** بعد نجاح الحساب والتدقيق والنشر والقراءة المتحققة؛ أو **فشل: السبب الفعلي** عند وجود مانع حقيقي. لا تصف عطلًا بأنه نجاح، ولا تتجاهل فحص نزاهة فاشل. أي متطلب إلزامي تفرضه المنصة نفسها يظل واجب الاتباع؛ هذه الورقة لا تتجاوزه.

تجاوز 600 ثانية هو سبب إسناد المهمة الطويلة إلى المنفذ، وليس سببًا لرفضها. نطاق هذه الورقة هو الحساب والتدقيق والتسليم؛ استخراج حالات الصعود وقياس دقتها مرحلة لاحقة.

## 1. السؤال
إنتاج القياسات 14 لكل إطار من 1 و 5 و 15 و 60 دقيقة، دون استخدام شمعة مفتوحة أو معلومات مستقبلية.
## 2. لماذا الآن
قبل القائد الخام والتقسيم في f38a07b70c022e4f6e92cac459e9d5fcb4692907. الحساب شرط سابق لدراسة التشابه، ولا يثبت فائدته التنبؤية.
## 3. المعروف
المصادر 13 والأطر 568800/113760/37920/9480 مقبولة. مصدر الخام في e68689a0aa560d27677ec703f85cea3877910b56 تحت research/btc-registration-from-repo-2026-10-15/executor/data/raw/. بصمات CSV المعيارية غير المضغوطة مثبتة في protocol.json.
## 4. الفرضية
لا فرضية توقع. القبول الحسابي يعني سلامة القيم والتوقيت فقط.
## 5. البيانات
BTCUSDT Spot ، UTC. إدخال 2025-09-01 حتى 2026-10-01 حصريًا؛ التحليل 2025-10-01 حتى 2026-10-01 ، وسبتمبر تهيئة. يعيد acquire بناء الأطر من أرشيفات المستودع المثبتة، في الذاكرة شهرًا بشهر؛ لا مرفق ولا تخزين نسخة خام محلية ثانية. البيانات الأصلية تبقى محفوظة في المستودع. تدقق بصمات CSV قبل الحساب.
## 6. الوعاء
لا أهداف مستقبلية أو حواجز أو أوامر أو صفقات. فترة يوم سابق للتحليل تحفظ قياسات الإطار المغلق للقراءات عند t و t−5 و t−15 دقيقة. لا تغير نافذة اليوم معاملات المؤشر.
## 7. المقارنة
مرجع حسابي مستقل بدقة Decimal40 ، سماح مطلق 1e−8 ونسبي 1e−10. المقارنة السعرية والمالية not measured.
## 8. القياسات المقفلة
ATR14: TR=max(H−L,abs(H−C السابق),abs(L−C السابق))، أول TR=H−L ، بدء متوسط 14 ثم Wilder=(13×السابق+الحالي)/14. EMA20 للإغلاق، بدء SMA20 ثم α=2/21. MACD=EMA12−EMA26 ، الإشارة EMA9 لأول قيم MACD المتاحة، Hist=MACD−Signal ؛ كل EMA يبدأ بمتوسط أول nقيم. RSI14 من أول 14 فرق إغلاق، Wilder للمكاسب والخسائر؛ 100−100/(1+G/L)، مع G=L=0 يعطي 50 وخسارة 0ومكاسب موجبة يعطي 100. الحجم BTC الخام.

القياسات 14 بالترتيب: ATR ؛100×ATR/C ؛ATR/ATR قبل 5−1 ؛EMA ؛(C−EMA)/ATR ؛(EMA−EMA قبل 5)/ATR ؛MACD ؛Signal ؛Hist/ATR ؛(Hist−Hist قبل 5)/ATR ؛RSI ؛RSI−RSI قبل 5؛الحجم؛الحجم/متوسط 60 شمعةحجم سابقة تستثني الحالية. التغير 5شموع داخل إطار المؤشر، أما إزاحة القراءة 5/15 بالدقائق. مقام 0يعطي NaN موثقًا، لا صفرًا.200 شمعة تهيئة على الأقل. لا تقسيم نطاقات أو تغيير أرقام.


| المؤشر | الإعداد المقفل |
|---|---|
| ATR | 14، تنعيم Wilder، بدء SMA14 |
| EMA | 20، سعر الإغلاق، بدء SMA20 |
| MACD | EMA12 وEMA26، إشارة EMA9؛ بدء كل EMA بمتوسط الفترة |
| RSI | 14، تنعيم Wilder، على فروق الإغلاق |
| Volume | حجم BTC الأساسي؛ نسبة الحجم إلى متوسط 60 شمعة سابقة تستثني الحالية |

## 9. الفترات والتوقيت
تظل الفترات اكتشاف 2025-10-01 إلى 2026-04-01 ، تحقق إلى 2026-07-01 ، احتياط إلى 2026-10-01 حصرية النهاية؛ لا تفتح نتائجها. كل سجل يمثل شمعة native و available_at=open+مدةالإطار. latest يأخذ آخر شمعة انتهت عند t−offset أو قبله؛ لا يتطلب اتفاق الأطر. التقسيم التاريخي ليس اختبارًا مستقبليًا أعمى.
## 10. المحاولات
صفر بحث إعدادات أو مرشحين.56 قياسًا=14×4 ، و 168 موضع قراءة=56×3 إزاحات، تحسب عند الطلب دون ملف واسع إضافي. لا قياس دقة أو تصحيح تعدد مطلوب لعدم وجود اختبار فرضيات.
## 11. الإحصاءات
674520 سجل native للتحليل، و 676368 مع يوم التاريخ السابق.52 ملفًا إطار/شهر، وإجمالي 81164160 بايت سجلات. تبين الأعداد والبصمات و NaN لكل حقل والفحوص وأزمنة التنفيذ والنشر منفصلة. الدقة والربح والرسوم والمخارج not measured.
## 12. النزاهة
تحقق من هويات مصادر 13 و CSV الأطر، استمرارية الزمن، 200 شمعةتهيئة، حجمكلسجل 120 بايت، كلتوقيت native ، مرجع Decimal بعينة ثابتة 24 موضعًا لكل إطار مع الأطراف و 14 حقلًا، 48 حالةتوقيت، 225 تطابقبادئة. لا نتائج مستقبلية أو عينات صعود منتقاة. فشل أي فحص يوقف التسليم، ولا يصلح المنفذ الكود بنفسه.
## 13. القبول
التعداد الكامل 676368 ، و 52 ملفًا، و 81164160 بايت، وتطابق هويات المدخلات، و PASS_NUMERIC_AND_CAUSAL_CHECKS ، وصفر اطلاع على مستقبل، ونشر متحقق عند التزام ثابت. الحكم Lead-review-pending ، لا اعتماد تداول.
## 14. الرفض
أي اختلاف هوية أو تعداد أو توقيت أو تجاوزالسماح العددي أو حجم 125000000 بايت يمنع PASS. لا تقليل الفترة أو حذف التاريخ لإجبار النجاح. عند عطل نقل تحفظ الملفات والخطأ المحجوب ويتوقف المنفذ لمراجعة القائد بعد فحص عدم وجود عامل يعمل.
## 15. خارج المهمة
استخراج الحالات، نسب النجاح، اختيار حدود أو تركيب مؤشرات، دفتر الأوامر، تصفقات أو ربح أو أي تعديل حي. لا تعيد دراسة التسجيل السابقة.
## 16. الملفات والمخطط
مصدر الحزمة research/btc-causal-measures-2026-10-15/، والأدوات run_task.py و features.py و audit_features.py و source_collect.py و api.py و protocol.json و SHA256.json. ثبت الالتزام المرسل من القائد والبصمات.

execution/features-{frame}m-{YYYY-MM}.bin يحتوي سجلات little-endian بصيغة q14d: int64 وقتفتح بالمللي ثانية ثم 14float64 بالترتيب أعلاه، 120 بايت. FEATURES.json يحدد كل ملف وعدده وتوقيته وبصمته و NaN. AUDIT.json الفحوص؛ RESULT.json الأعداد والحجم؛ REPORT.md التقرير؛  DELIVERY.json التزام البيانات المتحقق؛ LOCAL-RECEIPT.json إيصال الالتزام النهائي. latest واجهة قراءة الإزاحات دون نسخ 168 عمودًا.
## 17. التسليم وتقسيم المسؤولية

القائد يجهز الكود والورقة ويصلح العيوب ويراجع النتائج. المنفذ يشغل الحزمة الجاهزة، يحسب ويدقق وينشر التقارير والنتائج وLOG وتكة جديدة، ثم يلتزم بالرد المحدد أعلاه. لا يغير الإعدادات أو نطاق الدراسة، ولا يعتمد النتائج للتداول.

فرع النتائج: `agent/btc-causal-measures-execution-2026-10-15`.

مسار النتائج: `research/btc-causal-measures-2026-10-15/execution/`.

لا PR أو دمج أو كتابة إلى main. فشل النشر يعني عدم اكتمال التسليم، وتُحفظ الأدلة والسبب الفعلي في ملفات المهمة.

## 18. الحزمة وأمر التنفيذ

ما يفعله: تنزيل الملفات المحددة، التحقق من بصماتها، حساب القياسات المسجلة، تدقيقها، ونشر النتائج والتحقق منها.

مكان التشغيل: بيئة المنفذ، في `/home/user/btc-causal-measures-2026-10-15/`. شغّل مقطع Python التالي كما هو. النسخة الخاصة تهيئ GH_TOKEN مباشرة؛ لا تحتاج إلى تخمين مكان ملف مرفق أو اتصال GitHub خاص أو gh أو origin.

ما يعاد: سطر واحد، تم أو فشل: السبب الفعلي. احفظ المخرجات التفصيلية في الملفات ولا تنسخها إلى الرد.

**التزام تنزيل الحزمة بجميع ملفاتها:** `55cbdbced8c70acf4a3f500e19a559a9bbae617d`.

**التزام أصل الكود الذي سبق اختباره:** `8b41e1f3c07658ca39c3e6ced345bb10fc1251a7`. الملفات البرمجية الستة مطابقة له بايتًا. قيمة source_commit داخل SOURCE-MANIFEST.json توثق أصل الكود، وليست موقع تنزيل ملف البيان نفسه. لا تطلب SOURCE-MANIFEST.json من التزام أصل الكود؛ تنزيل الملفات التسعة كلها يكون من التزام الحزمة أعلاه.

| الملف | الرابط المثبت |
|---|---|
| SHA256.json | [تنزيل](https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/SHA256.json) |
| SOURCE-MANIFEST.json | [تنزيل](https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/SOURCE-MANIFEST.json) |
| READINESS.json | [تنزيل](https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/READINESS.json) |
| features.py | [تنزيل](https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/features.py) |
| audit_features.py | [تنزيل](https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/audit_features.py) |
| source_collect.py | [تنزيل](https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/source_collect.py) |
| api.py | [تنزيل](https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/api.py) |
| run_task.py | [تنزيل](https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/run_task.py) |
| protocol.json | [تنزيل](https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/protocol.json) |

```python
from pathlib import Path
import hashlib, json, os, re, subprocess, sys
token = os.environ.get("GH_TOKEN", "")
try:
    if not re.fullmatch(r"[A-Za-z0-9_]{30,}", token):
        raise RuntimeError("اعتماد التنفيذ غير مهيأ في الورقة الخاصة")
    os.environ["GH_TOKEN"] = token
    commit = "55cbdbced8c70acf4a3f500e19a559a9bbae617d"
    work = Path("/home/user/btc-causal-measures-2026-10-15")
    work.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/55cbdbced8c70acf4a3f500e19a559a9bbae617d/research/btc-causal-measures-2026-10-15/"
    expected = {'SHA256.json': 'd3b85ec13058412d05ba5715d5547b3b53bf20d1b0431f2f72735ab6e432383d', 'SOURCE-MANIFEST.json': 'bdc134e741b22f0ef9ee6700e9de9a7f8bc5b8ebb9af4a54812d2ac835cf43bb', 'READINESS.json': 'd1a5dde221991f2ae491e1dd9013724a7590f668321879d3c4ce45637769bc4c', 'features.py': '14c7445fa8917a278b415de83ae173c83306ecce89c6bc5745cc87e60eb9a2c1', 'audit_features.py': 'd98506dab4f479ab99f7e9ca4bee511284432d8034a226a0b8c9dab1c2e85f1d', 'source_collect.py': 'ce07492a625348e2137c0796018a8334594f2fc7346a6850feac3da87b9b79b4', 'api.py': 'c97740883cdb6c070aa0c23977ee3117b0906c356ec26d35b6aa8bcbec419c35', 'run_task.py': '02432ee87de01ce3e38fa3ceaf1c2144fb4abf14852f9c5c5ee5c90f6112dd59', 'protocol.json': '13e7eee63867b83674519cbe0df297d84a273df7ce2d9a7ab981a05c9ce88e17'}
    import urllib.request
    for name, digest in expected.items():
        with urllib.request.urlopen(base + name, timeout=60) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != digest:
            raise RuntimeError("اختلاف بصمة الملف " + name)
        (work / name).write_bytes(content)
    manifest = json.loads((work / "SOURCE-MANIFEST.json").read_text())
    assert manifest["source_commit"] == "8b41e1f3c07658ca39c3e6ced345bb10fc1251a7"
    assert manifest["code_sha256"] == json.loads((work / "SHA256.json").read_text())
    log_path = work / "EXECUTION-CONSOLE.log"
    with log_path.open("w") as log:
        result = subprocess.run([sys.executable, "run_task.py", "--publish", "--source-commit", commit], cwd=work, env=os.environ, stdout=log, stderr=subprocess.STDOUT)
    log_text = log_path.read_text().replace(token, "[REDACTED]")
    log_path.write_text(log_text)
    if result.returncode:
        lines = [line for line in log_text.splitlines() if line.strip()]
        raise RuntimeError(lines[-1] if lines else "انتهى أمر الحساب برمز " + str(result.returncode))
    receipt = json.loads((work / "execution/LOCAL-RECEIPT.json").read_text())
    assert receipt["status"] == "PASS_FIXED_CAUSAL_MEASUREMENTS_LEAD_REVIEW_PENDING"
    assert re.fullmatch(r"[0-9a-f]{40}", receipt["receipt_commit"])
    print("تم")
except Exception as exc:
    reason = str(exc).replace(token, "[REDACTED]") if token else str(exc)
    print("فشل: " + (reason.replace("\n", " ") or type(exc).__name__)[:400])
    sys.exit(1)
```

English execution contract: This is an execution assignment, not a request to review or summarize the attachment. Run the exact registered calculation, audit, report and work-branch publication. The owner has authorised these task-scoped operations. Do not ask optional or repeat approval questions. Continue polling the same foreground process to a known exit; do not start a duplicate worker. Keep optional progress and all detailed results in files. Final chat: exactly تم, or فشل: followed by the actual concise cause. Do not suppress mandatory platform requirements or bypass a failed integrity check.

## 19. الجاهزية المثبتة وحدودها

فحص الحصول على شهر حقيقي **مكتمل وناجح**: أربعة أطر مشتقة من مصدر المستودع المثبت. الأمر القصير حسب 3696 سجلًا و443520 بايت، واجتاز 1428 مقارنة Decimal و48 حالة توقيت و225 مطابقة بادئة. أعادت تجربتان بعد خروج معلوم البصمات الثنائية الأربع نفسها. سجل READINESS.json السابق يوثق ذلك صراحةً؛ لا يصح تفسيره بأن تنزيل الشهر لم يكتمل.

فحص نشر خمسة ملفات وقراءة بايتاتها تحقق عند `e76f85e43edf56deca39c6e55a56c1e05bedc307`. حالة فحص أمر الحساب والتدقيق والنشر مجتمعًا موثقة في ملحق التصحيح أدناه. لم تُحسب السنة الكاملة بعد. حسابها هو مهمة المنفذ، وليس شرطًا يجب تنفيذه مسبقًا لإعداد الورقة.

لم يُختبر استئناف عملية انقطعت أثناء التشغيل. عند انقطاع غير محسوم، احفظ الأدلة وافحص بقاء العملية؛ لا تعتبر خطأ المنصة خروجًا، ولا تبدأ عاملًا ثانيًا. إذا تعذر الاستمرار الآمن، أعد فشل: السبب الفعلي للقائد. لا تتجاوز فحصًا فاشلًا لإجبار النجاح.

## 20. التخزين والاعتماد والتوثيق

حد مساحة المهمة 125000000 بايت، وكل ملف منشور أقل من 25MB. المدخلات المعيارية 35.496MB والناتج الثنائي المتوقع 81.164MB؛ المجموع الأساسي المتوقع 116.661MB قبل الملفات الصغيرة، ويُقاس الحجم الفعلي. لا تنسخ المستودع كاملًا أو تضف أرشيف سنة أو ملفًا واسعًا يكرر القراءات. لا تحذف أدلة أو ملفات المالك لتجاوز الحد.

الاعتماد موجود في النسخة الخاصة ويهيأ داخل العملية؛ لا يوضع في مصدر الكود أو التقارير أو LOG أو التكة أو الروابط أو النسخة العامة. النشر عبر GitHub REST إلى فرع النتائج المحدد. قراءة المصادر العامة لا تحتاج اعتمادًا. النسخة العامة من مقطع التشغيل تتوقع GH_TOKEN من البيئة؛ النسخة الخاصة تضع القيمة المصرح بها مباشرة.

التقارير والفحوص والبصمات والتعدادات وإيصالات الالتزامات هي محل التفاصيل؛ الرد النهائي للمنفذ يبقى تم أو فشل: السبب الفعلي. تُراجع النتائج بعد التسليم قبل ورقة اكتشاف التشابه. الدقة التنبؤية والربح not measured في هذه المهمة.

تصحيح 2026-10-15: عولج خلط التزام أصل الكود مع التزام ملف البيان، وأزيلت صياغة الجاهزية المستقبلية الملتبسة، وثُبت التفويض وعقد الرد. لا تغيير في المؤشرات أو الإعدادات أو البيانات أو الكود العلمي. هذه الورقة تُقرأ بوصفها النسخة الحالية؛ سجل الجاهزية السابق دليل تاريخي، وعبارته الإدارية القديمة لا تنشئ طلب إذن جديدًا.

نتيجة إعادة الفحص الكامل بعد إصلاح مسار الرفع: خروج 0؛ حساب العينة والتدقيق والنشر وقراءة الملفات اجتمعت في الأمر نفسه. التزام الإيصال المتحقق: `04693e28def7878798ca4f9dff5476be44611cfe`. هذا فحص عينة قصيرة؛ حساب السنة لم ينفذ بعد.
