# الورقة الشاملة — إشارات بداية صعود البيتكوين

**الإصدار MASTER-BTC-ENTRY-01 — 2026-10-15. الحالة: مواصفات جامعة وحصر مصادر موثق؛ ليست بعدُ حزمة تنفيذ جاهزة لاختبار جميع الأكواد.**

هذه الورقة تجمع العمل بدل سلسلة أوراق صغيرة: الحصر، حسم النسخ، فحص المصدر، تجهيز الحساب، اختبار الجاهزية، الحساب الشامل، المقارنة حسب الحالات، التدقيق والتسليم. لا يُرسل المنفذ لإكمال التعريفات أو تحويل الأكواد. لا تدّعي الورقة أن 5940 إعلان إعداد هي 5940 نسخة مؤشر جاهزة، أو أن القائمة التاريخية52 تغطي جميع المكتبة.

## 1. السؤال الواحد
أي نسخة مستقلة من مؤشر أو تأكيد تلتقط بداية الصعود على البيتكوين، وفي أي إطار وحالة سوق تكون أنفع، وهل صعد السعر بعد الإشارة؟
يختبر كل مؤشر/تأكيد ونسخة إعدادات منفردًا. لا يُشترط اتفاق الجميع، ولا توجد تركيبات ثنائية أو ثلاثية جديدة في هذه الجولة.

## 2. لماذا هذه الحزمة
طلب المالك تجربة شاملة للبيتكوين فقط، ودمج التحضير والأعمال الصغيرة المترابطة داخل العمل نفسه لتقليل التكرار. الجولة الجارية ENTRY-01 لا تغطي هذا النطاق؛ لا يُغيّر تشغيلها، وتستعمل نتائجها السابقة فقط حيث تتطابق التعريفات والمدخلات والمتابعة.

## 3. ما حُصر فعلًا وما لم يُجهز
| البند | الحالة المثبتة |
|---|---|
| مكتبة history/library/indicators | قرئت129ملفًا:123مصدرًا نصيًا و6مذكرات بحث |
| إعلانات input المستخرجة |5940 إعلانًا؛ ليست عدد النسخ أو المؤشرات |
| خيارات حرفية صريحة أو خيارات منطقية |1927 إعلانًا له مجال خيارات صريح؛ لا اعتماد دلالته للدخول بعد |
| قيمة افتراضية دون مجال كامل معدود |2853 إعلانًا |
| افتراضي/مجال رمزي يحتاج مراجعة |1160 إعلانًا |
| مطابقة هوية المصدر |129 من129 هوية Git مطابقة للبيانات المسترجعة |
| مرجع تاريخي قابل للقراءة |52تعريف إشارة في indicators84.py؛ جدول كامل بملحق ب |
| تأكيدات الشموع المسجلة سابقًا |6 تعريفات منفردة؛ لا تُجلب مزائج CCI معها |
| إطار ENTRY-01 الحالي |40سلسلة:32اتجاهية و8نشاط على4أطر؛ ليس مسح جميع المكتبة |
| وثائق ثنائية في المستودع |18ملف PDF/DOCX حُصرت؛ لم يستخرج محتواها في هذا التحضير |
| محرك موحد لكل المصادر والنسخ |غير مكتمل؛ لا ادعاء جاهزية شاملة |

المصدر المثبت: 6d0226a03b84656e14b94dd8a37e39332cc2f68f. عدد الملفات هو عدد مصادر داخل المجلد المحدد، وليس ادعاء حصر كل مؤشر معروف على الإنترنت. المصادر الأخرى والوثائق الـ18 جزء صريح من قائمة استكمال التغطية، ولا تُعد مقروءة بمجرد معرفة مسارها.

## 4. الفرضية والحكم
قد تكون نسخة نافعة في حالة وضعيفة في أخرى. هذا سؤال للقياس، وليس نتيجة أو افتراض تفوق. لا عتبة نجاح مرتفعة لاستبعاد مؤشر، ولا وعد بإشارة لا تخطئ. تحفظ النتائج الضعيفة والنادرة والصفرية.

## 5. البيانات وإعادة الاستخدام
الأصل BTCUSDT Spot فقط. إطار المصدر دقيقة UTC، والأطر المسجلة للمقارنة1و5و15و60دقيقة. لا يدعي ذلك اختبار كل إطار زمني ممكن. إضافة إطار لاحق تغيّر سجل التغطية قبل حسابه.
المصدر المرشح للتوسعة: crypto_archive/BTCUSDT_1m.parquet، هوية Git376ab0ab3e3c190ab208dcb0700adf6fc442bb84،89135771بايت، ومداه الموثق سبتمبر2021–أغسطس2026. المصدر الحالي المثبت بالمستودع يضم سبتمبر2025–سبتمبر2026، والتحليل المسجل أكتوبر2025–سبتمبر2026. لا يتطابق المديان كاملًا.
يُضم فحص التكافؤ إلى تحضير الحزمة: مقارنة دقيقة-بدقيقة للوقت وOHLC والحجم والفجوات في المدى المشترك، ثم محاذاة الأطر وتاريخ بدء التهيئة والبذور ونهاية المتابعة. تطابق السعر وحده لا يثبت تطابق مؤشر أُعيد بدء حسابه بتاريخ آخر. لا يُستبدل المصدر الجاري دون هذا الفحص. عند التطابق يعاد استخدام الحسابات نفسها؛ عند الاختلاف يسجل السبب ولا ينسب إلى المؤشر.
النطاق المشترك الأول للمقارنة: أكتوبر2025–مارس2026 مع سبتمبر2025 تهيئة. فترة مطابقة المصدر ليست مهلة نجاح للإشارة. تحليل السنوات الإضافية يعرض منفصلًا؛ توسيع التاريخ ليس اختبارًا مستقلًا للصفوف المتداخلة.
تقرأ البيانات مرة، وتشتق الأطر مرة، وتخزن القياسات المشتركة ونتائج التقييم مرة. لا تنزيل جديد لكل نسخة. اختيار مسار قراءة Parquet وإصدارات اعتماده لم يُختبر بعد؛ لا يُعرض كاختصار مقاس.

## 6. معنى الصعود بعد الإشارة
مرجع الإشارة آخر إغلاق دقيقة كان متاحًا عند إطلاقها؛ هذا مرجع قياس وليس سعر صفقة مفترضًا. يسجل أول إغلاق لاحق مختلف عنه: أعلى أو أدنى؛ تتجاوز المساواة إلى أول اختلاف. ويسجل هل ظهر إغلاق أعلى لاحقًا، ووقت أول ظهور له وزمن الانتظار والمتابعة المتاحة.
لا هدف صعود نسبي ولا مهلة موحدة لاعتبار الإشارة ناجحة. نهاية البيانات أو فجوة تمنع المتابعة تجعل النتيجة غير مكتملة/غير مرصودة، ولا تُسمى خسارة أو نجاحًا. ارتفاع بعيد بعد هبوط طويل لا يكفي وحده لتسمية الدخول دقيقًا؛ يُقرأ مع جهة أول تغير وقربه الزمني. لا تتبع لنهاية الموجة أو مخارجها أو ربحها.
عند مقارنة مصدرين تُثبت نهاية المتابعة نفسها؛ إطالتها وحدها قد تزيد عدد الارتفاعات المرصودة. لا تجمع نسبًا بمدد متابعة مختلفة في ترتيب موحد مضلل.

## 7. المقارنة المرجعية
لكل نسخة وإطار وحالة وفترة، خط المقارنة هو الأوقات المؤهلة نفسها في تلك الحالة والفترة والإطار دون شرط النسخة. تحفظ كثافة الإشارات وتغطيتها والمدة المتاحة للمتابعة، وتظهر الأعداد بجانب أي نسبة. الترابط بين الإشارات المتتابعة أو المتزامنة لا يمنح عينات مستقلة إضافية.
لا اختيار فائز من إجمالي واحد، ولا إعادة تسمية ترتيب مكتشف بأنه تحقق مستقل. الاستدلال المصحح والدقة المستقبلية غير مقاسين حتى تجهيز اختبارهما. الأرقام في المصادر القديمة التي تستخدم أرباحًا أو حواجز أو مهلة24شمعة لا تُنقل إلى هذا التقييم.

## 8. سجل النسخ المستقلة
كل نسخة سجل صريح: family_id، source_path، source_blob، formula_version، seed، price_source، جميع المعاملات، جميع الحدود، قاعدة الإشارة، مرجع التثبيت، سياسة التأكيد، warmup، availability_rule، timeframe، data_requirements.
variant_id هو SHA256 لتمثيل JSON معياري لهذه الحقول. أي تغيير حسابي أو عتبة أو تثبيت أو بذرة أو وقت تأكيد ينتج نسخة مستقلة. اسم بديل لنسخة متطابقة حسابيًا يحتفظ به كاسم مرتبط بالهوية نفسها؛ يمكن إعادة استعمال الحساب دون إسقاط الاسم أو ادعاء تجربتين مستقلتين.
قائمة كاملة من tuples تُقفل وتُعد قبل القياس. options الحرفية المصرح بها تسجل، والمجال العددي المحدود بخطوة صريحة يمكن عده بعد التحقق. الافتراضي وحده لا يحدد كل الأرقام المعروفة. لا تُختلق حدود رقمية للحقول المفتوحة، ولا يسمى مجال مستمر غير محدود «كل الاحتمالات».
إعدادات الألوان والرسم والتنبيهات والوقف والخروج وحجم الصفقة تُفصل بعد فحص أثرها على إشارة الدخول؛ لا تتحول آليًا إلى نسخ دخول. الاستراتيجية المركبة الأصلية تُسجل بهويتها الأصلية إن اختبرت، ولا يقدم استخراج داخلي غير مطابق كأنه الأصل.
تعريفات RSI/EMA التاريخية ذات ewm من أول قيمة تختلف عن النسخ ذات بدء SMA/Wilder المسجلة في الحزمة الحالية؛ تسجل كنسخ حسابية مختلفة ولا توحّد صامتًا.

## 9. قاموس الحالات التشغيلي المقترح V1
هذا قاموس جديد محدد لهذه الورقة، وليس ادعاء اكتشاف جميع حالات السوق أو استرجاع قاموس مكتمل سابقًا. من قياسات الأساس الثابتة ATR14 وEMA20 وMACD12/26/9 وRSI14 والحجم، تؤخذ ستة محاور، ولكل محور−1أو0أو+1بحسب الإشارة الحسابية:
| المحور | تعريف القيمة عند شمعة مكتملة |
|---|---|
| موضع السعر | sign(close−EMA20) |
| ميل EMA | sign(EMA20الحالي−EMA20قبل5شموع) |
| زخم MACD | sign(MACD−Signal) |
| اتجاه RSI | sign(RSI14الحالي−RSI14قبل5شموع) |
| تغير التقلب | sign(ATR14الحالي/ATR14قبل5−1) |
| نشاط الحجم | sign(volume/متوسط60سابقة−1) |
عدد الخلايا النظري3^6=729حالة لكل إطار، و2916خلية حالة/إطار على الأطر الأربعة. الصفر مساواة حسابية فعلية، لا نطاق تسامح يخترع بعد النتائج. القيم غير المتاحة تسجل UNAVAILABLE خارج الخلايا الصالحة ولا تحوّل إلى صفر.
الحالة تُقرأ عند الإشارة من آخر شمعة مكتملة في إطارها. لا معلومات مستقبلية في تعريفها. المعرفات0..728تنتج بترتيب معجمي لمحاور−1و0و1كما في state-dictionary-v1.json. لا تُحذف حالة لأنها نادرة أو لم تظهر.
هذا وصف للسياق وليس شرط AND إضافيًا للدخول. إذا تداخل تعريف إشارة مع أحد محاور القاموس، يوضح الارتباط الحتمي بينهما، ولا يعد ذلك وحده ميزة تنبؤية.
الحالات التاريخية الخاصة مثل ضغط Taker أو OBV في volume_states90.py تبقى تعريفات إضافية مستقلة عند إدراجها صراحة؛ لا يُستبدل تدفق فعلي بحجم شمعة صاعدة. القاموس المقترح لم يُدمج في محرك السوق أو يختبر على السوق بعد.

## 10. الميزانية وعدد الاختبارات
عند إكمال السجل، عدد السلاسل المستقلة=عدد النسخ المعتمدة حسابيًا×4. عدد صفوف التغطية النظرية=ذلك العدد×729لكل فترة مسجلة، إضافة UNAVAILABLE وصفوف المقارنة والتغطية. هذا عدد خلايا نتائج، وليس عدد إشارات مستقلة.
عدد النسخ الشامل لم يحسم؛ لذلك لا يوجد الآن رقم صادق لعدد الاختبارات النهائية أو مدة شاملة مقاسة. إعلانات الإدخال5940 ليست هذا العدد، وحاصل ضرب كل مفاتيح العرض والخروج ليس شبكة الدخول المطلوبة.
النسخ52والتأكيدات6والسلاسل40 قوائم بداية موثقة، وليست بديلًا مختصرًا عن باقي المصادر. لا دمج بين مؤشرين/ثلاثة في هذه الجولة؛ يحفظ تصميمه داخل الخطة العامة لجولة لاحقة بعد المراجعة دون اختراع اختبار من نتائج التحقق.

## 11. التوقيت وصلاحية المصادر
الإشارة لا تسبق اكتمال الشمعة التي تتطلبها. القاع أو القمة ذات right-confirmation لا يعرفان قبل مرور شموع التأكيد؛ وقت التنبيه هو وقت العلم، لا موضع القاع الماضي. request.security والإطارات الأعلى لا تتيح إلا الشموع المكتملة. الإطار الأدنى يحتاج بياناته الفعلية، لا إعادة بناء مختلقة من OHLC أكبر.
العلامة future_sensitive في الجرد تنبيه لفحص المصدر، لا حكم آلي بوجود تسرب.100مصدر يحمل كلمات أو تراكيب تستدعي هذا الفحص، وقد تكون في ملاحظة أو فرع لا يؤثر في الإشارة.
المصدر الذي يعيد الرسم لا يعدل صامتًا: تسجل النسخة الأصلية وحدودها، وأي تحويل سببي يحصل على هوية جديدة مع فرق تعريف واضح. لا تختبر إشارة لا يمكن معرفتها وقتها كدخول صالح.

## 12. متطلبات البيانات الخاصة
| العائلة | ما يلزم قبل قبولها |
|---|---|
| OHLCV والمؤشرات التقليدية | صيغ ومعاملات وبذور وتوقيت محدد |
| فيبوناتشي | نسب محددة ومرساة سببية ومتى تصبح معروفة؛ لا أدنى قاع مختار من المستقبل |
| Anchored VWAP | قاعدة تثبيت معلومة حينها وسعر وحجم محددان |
| Fixed/Session Volume Profile وHVN/LVN | مجال وصفوف ونسبة قيمة وصيغة توزيع وبيانات حجم عند السعر؛ تقريب OHLCV نسخة مشتقة مسماة، لا ملف حجم فعلي مزعوم |
| Taker ratio وCVD | حقول شراء المعتدي الفعلية ومجال تجميع واضح؛ ملف OHLCV ذي5أعمدة لا يكفي لتعويضها |
| Footprint والامتصاص ودفتر الأوامر | صفقات عند السعر/جهة المعتدي ولقطات/تحديثات عمق مؤرخة حسب التعريف؛ لا ادعاء توفرها في الشموع |
| SMC وFVG وOrder Blocks وZigZag | تعريف كامل وتثبيت وقت العلم ومنع إعادة إسناد الإشارة للماضي |
| نماذج الشموع | جسم وظلال وحدود وسياق وتوقيت واضح، وكل تعديل نسخة مستقلة |
| GO Seeker/Maestro/Hunter/Radar/Bell أو أي اسم تجاري | المصدر أو المعادلات والإعدادات متاحة؛ الاسم أو صورة الإعلان لا يكفيان لاختراع الأصل |

أسماء الحالات: READY_VERIFIED،NEEDS_DEFINITION،NEEDS_PORT،NEEDS_DATA،NEEDS_CAUSAL_REVIEW،OUT_OF_ENTRY_SCOPE. يلزم دليل قبل READY_VERIFIED؛ غياب البيانات ليس نتيجة سلبية للمؤشر. تحفظ جميع الأسماء والنواقص في تقرير التغطية.

## 13. مراحل داخل الورقة نفسها
أ. حصر المصادر والنصوص والوثائق الثنائية وإعلان المعاملات، ثم تنقية ما يؤثر في الدخول وحسم المجالات. جزء منه أنجز في هذا التحضير كما في الملحق؛ لا ادعاء اكتمال دلالي.
ب. تجهيز محرك موحد وسجل نسخ مقفل وقاموس حالات وحساب مرجعي ومقارنة مصدر الأرشيف، ثم فحص قصير عبر مسار الحساب والتقرير والتدقيق والرفع نفسه. هذا عمل القائد، لا يُسلّم للمنفذ كبرمجة ناقصة.
ج. المنفذ يحسب الدفعات المسجلة، وكل دفعة تحفظ النسخ والحالات والفريمات والصفوف الصفرية والأدلة. لا ورقة منفصلة للتنزيل أو البصمات أو كل مجموعة صغيرة.
د. تجميع النتائج ومقارنتها حسب الحالة والفريم والفترة، ثم تدقيق القائد. لا يصبح التنقيب في سنوات سبق فحصها تحققًا أعمى. أي مرحلة تحقق مستقلة تغلق مرشحيها قبل قراءة نتائجها، ولا تستخدم لإعادة اختيار بديل.

## 14. المخرجات ومخطط المقارنة
coverage: لكل مصدر/عائلة/معامل حالة التغطية والسبب. variants: كل tupleوIDوصيغته وبذرته وتوقيته ومتطلبات بياناته. source-equivalence: تطابق الصفوف أو اختلافها والفجوات والتهيئة.
alerts: variant_id،frame،state_id،feature_open،available_at،reference_close،source_id،جهة أول تغير لاحق،وقت أول إغلاق أعلى،زمن الانتظار،المتابعة المتاحة،حالة النتيجة،سبب عدم الأهلية. هوية التنبيه لا تتكرر داخل النسخة، والتكرار بين نسخ مختلفة محفوظ وموسوم بالترابط.
summary: صف لكل نسخة/إطار/حالة/شهر ومجموع الفترة، بما فيها الحالات الصفرية، والأعداد ونسب الوصف وخط المقارنة وتوزيع زمن الانتظار والتغطية. لا يمحو الإجمالي الاختلافات بين الحالات أو الفترات.
أدلة AUDIT،المدة الكاملة وأجزاء التنفيذ،المساحة،البصمات،التزام المصدر والنتيجة وإيصال القراءة المتحققة. التقرير العربي يحفظ العناوين الإلزامية مع كتابة الحقول المالية «غير مقاسة — خارج المرحلة».

## 15. فحوص النزاهة
مطابقة المصادر، اكتمال سجل النسخ وعدّ حاصل المجالات المسجلة، عدم وجود حلقة تتخطى نسخًا بصمت، الأطر المغلقة، التهيئة والفجوات، منع المستقبل، توقيت تأكيد القمم والقيعان، مطابقة مرجع مستقل لعينة موزعة، تطابق حساب البادئة، حالات المساواة/الصفر/عدم الإشارة ونهاية البيانات، مطابقة سجلات التنبيه بالملخص، حفظ كل خلية حالة صفرية، وعدم إسقاط النتائج السلبية.
يُختبر انقطاع واستئناف الدفعة قبل ادعاء دعمه. لا عامل مكرر ولا ناشران متزامنان. أي اختلاف جوهري يوقف القياس المعني ويحفظ الأدلة، ولا يغير تعريف النسخة لتمرير الفحص.

## 16. قبول العمل والتفسير
قبول التسليم يثبت تغطية السجل المقفل وصحة الحساب والتدقيق والنشر، لا نسبة نجاح محددة. لا إلغاء لمؤشر بسبب نسبة منخفضة، ولا اعتماد بسبب حالات قليلة ناجحة. تعرض قوة الأدلة وعددها وتكرارها عبر الزمن.
اكتمال «الجميع» يتطلب أن يطابق العدد المنفذ قائمة النسخ المقفلة، وأن تظهر النواقص بوضوح. لا يكتب COMPLETE_ALL بينما بعض المصادر لم تتحول أو تنقص بياناتها. الصيغ الأصلية والمشتقة لا تخلط.

## 17. خارج النطاق
المخارج وإدارة الصفقة والمال الحقيقي والأرباح والرافعة والبيع المكشوف، وتغيير أصول غير البيتكوين، وتعديل التشغيل الجاري أو الأرشيف الأصلي، وإضافة مزائج جديدة غير مسجلة. لا دمج أو PR أو كتابة إلى main.

## 18. حدود التنفيذ والاختصار
حد مجلد المهمة125000000بايت، والملف المنشور أقل من25000000بايت. القراءة بالدفعات وإعادة استعمال الأعمدة والأقنعة والنتائج المشتركة، والكتابة المضغوطة المجزأة، دون نسخ المستودع أو حذف أدلة. لا حد وقت مصطنع لنجاح إشارة.
الكود والفحص والورقة الجاهزة من القائد؛ الحساب الثقيل المتوقع أن يتجاوز600ثانية مع التدقيق والنشر من المنفذ وفق الحزمة الجاهزة. لا تقدير نهائي لزمن هذه الشبكة قبل معرفة عدد نسخها. لا تقسيم شكلي إلى عشرات أوراق صغيرة للتحايل على حجم العمل.

## 19. الجاهزية الفعلية الآن
أنجز حصر129مصدرًا و5940إعلانًا ومطابقة هوياتها، وحصر18وثيقة ثنائية، وفحص عدّ المجالات، وتوليد729معرف حالة مقترحة لكل إطار. coverage.py خرج0 وفحص المحاسبة فقط. لم يشغّل محركًا شاملًا أو يختبر السوق أو يثبت دعم جميع مدخلات Pine.
ما لم ينجز: قراءة محتويات الوثائق الثنائية، مراجعة دلالة5940إعلانًا وفصل العرض والخروج، حسم المجالات المفتوحة، تحويل بقية الإشارات والتحقق من توقيتها، دمج القاموس في محرك السوق، مطابقة ملف الأرشيف، وفحص الحزمة الشاملة عبر مسارها الكامل. هذه نواقص تجهيز للقائد وليست مهمة ينفذها الوكيل بالتخمين.
إعادة محاسبة الحصر وتوليد قاموس الحالات: python3 coverage.py داخل مجلد الحزمة. الخيار --verify-sources يعيد جلب المصادر ومقارنة نصوص إعلان الإدخال وهوياتها؛ هذا الجلب الإضافي لم يشغل هنا، وقد قرئت المصادر من موصل المستودع وطوبقت هوياتها.
تتضمن الحزمة inventory.json.gz وسجل الوثائق وhistorical-52-grid.json وstate-dictionary-v1.json وcoverage-check.json. فك gzip ينتج الجرد الكامل لإعلانات الإدخال ومواقعها ونصوصها وحدودها وخياراتها، دون إسقاط الرمزي أو المفتوح.

## 20. التسليم والمسؤولية والخطوة التالية
هذه ورقة المواصفات الجامعة التي تستمر عليها مراحل العمل. لا أمر تشغيل وهمي أو ملفات register مفقودة، ولا وسم جاهز لتنفيذ جميع المصادر.
بعد إكمال التجهيز، يوضع هنا التزام الحزمة المقفل وأمر واحد مجرّب للحساب والتدقيق والتقرير والسجل والنشر والقراءة المتحققة، مع الاعتماد داخل نسخة تنفيذ خاصة فقط. لا يوضع اعتماد في هذه الورقة العامة أو أي سجل. المالك سبق أن أجاز النشر في فروع العمل؛ لا إذن اختياري مكرر.
المنفذ وقتها يحسب ويدقق ويسلم فقط؛ رده النهائي «تم» أو «فشل: السبب الفعلي». القائد يحفظ الدليل ويصدر المراجعة. الخطوة التالية استكمال نواقص القسم19داخل هذه الحزمة نفسها، ثم إغلاق الجاهزية قبل الإرسال للمنفذ.

## ملحق أ — جميع مصادر المكتبة المقروءة
| م | المصدر المثبت | إعلانات إدخال | النوع | المراجعة |
|---:|---|---:|---|---|
| 1 | [hft_edge_extraction_batch2.md](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/0/hft_edge_extraction_batch2.md) | 0 | نص بحثي | مراجعة توقيت لازمة |
| 2 | [hft_edge_extraction_batch3.md](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/0/hft_edge_extraction_batch3.md) | 0 | نص بحثي | مراجعة توقيت لازمة |
| 3 | [hft_edge_extraction_batch4.md](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/0/hft_edge_extraction_batch4.md) | 0 | نص بحثي | مراجعة توقيت لازمة |
| 4 | [hft_edge_extraction_batch5.md](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/0/hft_edge_extraction_batch5.md) | 0 | نص بحثي | مراجعة توقيت لازمة |
| 5 | [hft_edge_extraction_batch6.md](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/0/hft_edge_extraction_batch6.md) | 0 | نص بحثي | مراجعة توقيت لازمة |
| 6 | [hft_edge_extraction_batch7.md](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/0/hft_edge_extraction_batch7.md) | 0 | نص بحثي | مراجعة توقيت لازمة |
| 7 | [2-1 strategy.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/2-1%20strategy.txt) | 126 | كود مصدر | مراجعة توقيت لازمة |
| 8 | [ABO LANA-𝑀.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/ABO%20LANA-%F0%9D%91%80.txt) | 49 | كود مصدر | مراجعة توقيت لازمة |
| 9 | [AI Gold Scalping.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/AI%20Gold%20Scalping.txt) | 34 | كود مصدر | مراجعة توقيت لازمة |
| 10 | [AI RSI MTF STRATEGY.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/AI%20RSI%20MTF%20STRATEGY.txt) | 70 | كود مصدر | مراجعة توقيت لازمة |
| 11 | [AI SWING Algo.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/AI%20SWING%20Algo.txt) | 12 | كود مصدر | لم تحسم الجاهزية |
| 12 | [AI Signal Remastered.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/AI%20Signal%20Remastered.txt) | 12 | كود مصدر | لم تحسم الجاهزية |
| 13 | [AI Signal.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/AI%20Signal.txt) | 12 | كود مصدر | لم تحسم الجاهزية |
| 14 | [AI Vanga V3.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/AI%20Vanga%20V3.txt) | 43 | كود مصدر | مراجعة توقيت لازمة |
| 15 | [AI_TRENDLINE.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/AI_TRENDLINE.txt) | 9 | كود مصدر | مراجعة توقيت لازمة |
| 16 | [ALGOX V11.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/ALGOX%20V11.txt) | 90 | كود مصدر | مراجعة توقيت لازمة |
| 17 | [ASK.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/ASK.txt) | 48 | كود مصدر | مراجعة توقيت لازمة |
| 18 | [Adaptive Ichimoku Nexus.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/Adaptive%20Ichimoku%20Nexus.txt) | 47 | كود مصدر | مراجعة توقيت لازمة |
| 19 | [Advanced Liquidity Sweep.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/Advanced%20Liquidity%20Sweep.txt) | 32 | كود مصدر | مراجعة توقيت لازمة |
| 20 | [Advanced SMC.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/Advanced%20SMC.txt) | 141 | كود مصدر | مراجعة توقيت لازمة |
| 21 | [AlgoX V22 SuperTrend.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/AlgoX%20V22%20SuperTrend.txt) | 31 | كود مصدر | مراجعة توقيت لازمة |
| 22 | [Alpha Hunter.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/Alpha%20Hunter.txt) | 15 | كود مصدر | لم تحسم الجاهزية |
| 23 | [Anchored VWAP Trade Planner.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/Anchored%20VWAP%20Trade%20Planner.txt) | 24 | كود مصدر | مراجعة توقيت لازمة |
| 24 | [Apex Trend.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/Apex%20Trend.txt) | 18 | كود مصدر | مراجعة توقيت لازمة |
| 25 | [Ayman Entry.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/Ayman%20Entry.txt) | 53 | كود مصدر | مراجعة توقيت لازمة |
| 26 | [breakout +TP-SL.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/1/breakout%20%2BTP-SL.txt) | 21 | كود مصدر | لم تحسم الجاهزية |
| 27 | [Breakout Lines + TPSL.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Breakout%20Lines%20%2B%20TPSL.txt) | 22 | كود مصدر | مراجعة توقيت لازمة |
| 28 | [Breakout Lines.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Breakout%20Lines.txt) | 22 | كود مصدر | مراجعة توقيت لازمة |
| 29 | [Breakout Targets.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Breakout%20Targets.txt) | 10 | كود مصدر | مراجعة توقيت لازمة |
| 30 | [Clear Trend Algo.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Clear%20Trend%20Algo.txt) | 19 | كود مصدر | لم تحسم الجاهزية |
| 31 | [Clustering Clouds v2.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Clustering%20Clouds%20v2.txt) | 90 | كود مصدر | مراجعة توقيت لازمة |
| 32 | [Combined Algo v5.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Combined%20Algo%20v5.txt) | 24 | كود مصدر | مراجعة توقيت لازمة |
| 33 | [Combined Trendlines Breakouts.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Combined%20Trendlines%20Breakouts.txt) | 48 | كود مصدر | مراجعة توقيت لازمة |
| 34 | [Cute Dragon.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Cute%20Dragon.txt) | 11 | كود مصدر | لم تحسم الجاهزية |
| 35 | [DTC V1.35.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/DTC%20V1.35.txt) | 22 | كود مصدر | مراجعة توقيت لازمة |
| 36 | [DTC.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/DTC.txt) | 135 | كود مصدر | مراجعة توقيت لازمة |
| 37 | [DTC_V1.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/DTC_V1.txt) | 6 | كود مصدر | لم تحسم الجاهزية |
| 38 | [Delta Reaction Zones.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Delta%20Reaction%20Zones.txt) | 16 | كود مصدر | مراجعة توقيت لازمة |
| 39 | [Double SuperTrend.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Double%20SuperTrend.txt) | 8 | كود مصدر | لم تحسم الجاهزية |
| 40 | [Drone Arrows.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Drone%20Arrows.txt) | 17 | كود مصدر | مراجعة توقيت لازمة |
| 41 | [ELITE SMART.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/ELITE%20SMART.txt) | 60 | كود مصدر | مراجعة توقيت لازمة |
| 42 | [Edge Algo pro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Edge%20Algo%20pro.txt) | 10 | كود مصدر | لم تحسم الجاهزية |
| 43 | [ExProfit SuperTrend.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/ExProfit%20SuperTrend.txt) | 128 | كود مصدر | مراجعة توقيت لازمة |
| 44 | [Eyops Fx Premium.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Eyops%20Fx%20Premium.txt) | 217 | كود مصدر | مراجعة توقيت لازمة |
| 45 | [Fibonacci.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/2/Fibonacci.txt) | 72 | كود مصدر | مراجعة توقيت لازمة |
| 46 | [FLI.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/FLI.txt) | 18 | كود مصدر | مراجعة توقيت لازمة |
| 47 | [FTR.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/FTR.txt) | 40 | كود مصدر | مراجعة توقيت لازمة |
| 48 | [FVG Sniper.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/FVG%20Sniper.txt) | 48 | كود مصدر | مراجعة توقيت لازمة |
| 49 | [FVG+Fractals.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/FVG%2BFractals.txt) | 7 | كود مصدر | مراجعة توقيت لازمة |
| 50 | [Fresh Algo (1).txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/Fresh%20Algo%20%281%29.txt) | 34 | كود مصدر | مراجعة توقيت لازمة |
| 51 | [Fresh Algo.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/Fresh%20Algo.txt) | 34 | كود مصدر | مراجعة توقيت لازمة |
| 52 | [GBS.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/GBS.txt) | 5 | كود مصدر | لم تحسم الجاهزية |
| 53 | [GainzAlgo Pro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/GainzAlgo%20Pro.txt) | 9 | كود مصدر | لم تحسم الجاهزية |
| 54 | [GainzAlgo V2.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/GainzAlgo%20V2.txt) | 10 | كود مصدر | لم تحسم الجاهزية |
| 55 | [HADYAN NEW SCALPING V 2.9.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/HADYAN%20NEW%20SCALPING%20V%202.9.txt) | 54 | كود مصدر | مراجعة توقيت لازمة |
| 56 | [HalfTrend.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/HalfTrend.txt) | 21 | كود مصدر | مراجعة توقيت لازمة |
| 57 | [Haper Trend.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/Haper%20Trend.txt) | 48 | كود مصدر | مراجعة توقيت لازمة |
| 58 | [Historical Pattern Projection.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/Historical%20Pattern%20Projection.txt) | 36 | كود مصدر | مراجعة توقيت لازمة |
| 59 | [ICT Validated SMC v1.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/ICT%20Validated%20SMC%20v1.txt) | 78 | كود مصدر | مراجعة توقيت لازمة |
| 60 | [Indicator GG Beluga KHST.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/Indicator%20GG%20Beluga%20KHST.txt) | 65 | كود مصدر | مراجعة توقيت لازمة |
| 61 | [Indicator ICT Master Suite.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/Indicator%20ICT%20Master%20Suite.txt) | 50 | كود مصدر | مراجعة توقيت لازمة |
| 62 | [Indicator MM ALGO PREMIUM for TradingView.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/Indicator%20MM%20ALGO%20PREMIUM%20for%20TradingView.txt) | 36 | كود مصدر | مراجعة توقيت لازمة |
| 63 | [Infinity and Sniper by Leo.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/Infinity%20and%20Sniper%20by%20Leo.txt) | 134 | كود مصدر | مراجعة توقيت لازمة |
| 64 | [Institutional Flow Toolkit MMDV.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/Institutional%20Flow%20Toolkit%20MMDV.txt) | 143 | كود مصدر | مراجعة توقيت لازمة |
| 65 | [floop pro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/3/floop%20pro.txt) | 31 | كود مصدر | مراجعة توقيت لازمة |
| 66 | [Inversion Order Blocks [iOB].txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Inversion%20Order%20Blocks%20%5BiOB%5D.txt) | 34 | كود مصدر | لم تحسم الجاهزية |
| 67 | [Jack Of All Trades.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Jack%20Of%20All%20Trades.txt) | 43 | كود مصدر | مراجعة توقيت لازمة |
| 68 | [Jackson_Zones.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Jackson_Zones.txt) | 4 | كود مصدر | مراجعة توقيت لازمة |
| 69 | [Joker.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Joker.txt) | 48 | كود مصدر | مراجعة توقيت لازمة |
| 70 | [KD System.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/KD%20System.txt) | 140 | كود مصدر | مراجعة توقيت لازمة |
| 71 | [Key Levels.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Key%20Levels.txt) | 153 | كود مصدر | مراجعة توقيت لازمة |
| 72 | [LIQUIDITY TRAIL MATRIX.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/LIQUIDITY%20TRAIL%20MATRIX.txt) | 57 | كود مصدر | مراجعة توقيت لازمة |
| 73 | [Lion Trend.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Lion%20Trend.txt) | 15 | كود مصدر | لم تحسم الجاهزية |
| 74 | [Liquidity Reaper.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Liquidity%20Reaper.txt) | 34 | كود مصدر | مراجعة توقيت لازمة |
| 75 | [Liquidity sweep (1;2RR).txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Liquidity%20sweep%20%281%3B2RR%29.txt) | 2 | كود مصدر | مراجعة توقيت لازمة |
| 76 | [Luxy BIG beautiful Dynamic.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Luxy%20BIG%20beautiful%20Dynamic.txt) | 86 | كود مصدر | مراجعة توقيت لازمة |
| 77 | [LyroRS v1.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/LyroRS%20v1.txt) | 15 | كود مصدر | لم تحسم الجاهزية |
| 78 | [MELONA.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/MELONA.txt) | 78 | كود مصدر | مراجعة توقيت لازمة |
| 79 | [MONEY ALGORITHM.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/MONEY%20ALGORITHM.txt) | 48 | كود مصدر | مراجعة توقيت لازمة |
| 80 | [Market Matrice.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Market%20Matrice.txt) | 40 | كود مصدر | مراجعة توقيت لازمة |
| 81 | [Million Moves Alga.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Million%20Moves%20Alga.txt) | 21 | كود مصدر | مراجعة توقيت لازمة |
| 82 | [Mirage Liquidity Sweep Pro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Mirage%20Liquidity%20Sweep%20Pro.txt) | 54 | كود مصدر | مراجعة توقيت لازمة |
| 83 | [Money Moves.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/Money%20Moves.txt) | 45 | كود مصدر | مراجعة توقيت لازمة |
| 84 | [iqfxpro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/4/iqfxpro.txt) | 6 | كود مصدر | مراجعة توقيت لازمة |
| 85 | [NAS Ultimate Algo Remastered.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/NAS%20Ultimate%20Algo%20Remastered.txt) | 10 | كود مصدر | لم تحسم الجاهزية |
| 86 | [NEXT CANDLE PREDICTOR V4.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/NEXT%20CANDLE%20PREDICTOR%20V4.txt) | 9 | كود مصدر | لم تحسم الجاهزية |
| 87 | [NOSTRADAMUS.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/NOSTRADAMUS.txt) | 61 | كود مصدر | مراجعة توقيت لازمة |
| 88 | [NOVA ALGO.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/NOVA%20ALGO.txt) | 22 | كود مصدر | مراجعة توقيت لازمة |
| 89 | [PRECISION SNIPER.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/PRECISION%20SNIPER.txt) | 33 | كود مصدر | مراجعة توقيت لازمة |
| 90 | [Pearson SLTP.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/Pearson%20SLTP.txt) | 19 | كود مصدر | لم تحسم الجاهزية |
| 91 | [RSI divergence entry.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/RSI%20divergence%20entry.txt) | 9 | كود مصدر | مراجعة توقيت لازمة |
| 92 | [RSI entry.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/RSI%20entry.txt) | 28 | كود مصدر | لم تحسم الجاهزية |
| 93 | [Reactive Trail System.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/Reactive%20Trail%20System.txt) | 49 | كود مصدر | مراجعة توقيت لازمة |
| 94 | [River Strategy.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/River%20Strategy.txt) | 140 | كود مصدر | مراجعة توقيت لازمة |
| 95 | [S&D zones.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/S%26D%20zones.txt) | 2 | كود مصدر | لم تحسم الجاهزية |
| 96 | [SELF-AWARE TREND SYSTEM.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/SELF-AWARE%20TREND%20SYSTEM.txt) | 76 | كود مصدر | مراجعة توقيت لازمة |
| 97 | [SFI MAGIC.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/SFI%20MAGIC.txt) | 9 | كود مصدر | لم تحسم الجاهزية |
| 98 | [Scalper.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/Scalper.txt) | 35 | كود مصدر | مراجعة توقيت لازمة |
| 99 | [Setup Scanner [GBB].txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/Setup%20Scanner%20%5BGBB%5D.txt) | 48 | كود مصدر | مراجعة توقيت لازمة |
| 100 | [sfi scalper 1.0.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/sfi%20scalper%201.0.txt) | 8 | كود مصدر | لم تحسم الجاهزية |
| 101 | [short and long.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/5/short%20and%20long.txt) | 13 | كود مصدر | مراجعة توقيت لازمة |
| 102 | [SMC Algo Pro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/SMC%20Algo%20Pro.txt) | 171 | كود مصدر | مراجعة توقيت لازمة |
| 103 | [SMC.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/SMC.txt) | 88 | كود مصدر | مراجعة توقيت لازمة |
| 104 | [SUPER Scalping.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/SUPER%20Scalping.txt) | 123 | كود مصدر | مراجعة توقيت لازمة |
| 105 | [SWIFT ALGO.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/SWIFT%20ALGO.txt) | 57 | كود مصدر | مراجعة توقيت لازمة |
| 106 | [Simple System.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/Simple%20System.txt) | 120 | كود مصدر | مراجعة توقيت لازمة |
| 107 | [Smart Money Trades Pro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/Smart%20Money%20Trades%20Pro.txt) | 13 | كود مصدر | مراجعة توقيت لازمة |
| 108 | [Sniper Trading Algo Pro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/Sniper%20Trading%20Algo%20Pro.txt) | 22 | كود مصدر | مراجعة توقيت لازمة |
| 109 | [Stocks Algo.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/Stocks%20Algo.txt) | 5 | كود مصدر | لم تحسم الجاهزية |
| 110 | [TJR SMC.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/TJR%20SMC.txt) | 36 | كود مصدر | مراجعة توقيت لازمة |
| 111 | [TM Sniper Pro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/TM%20Sniper%20Pro.txt) | 23 | كود مصدر | مراجعة توقيت لازمة |
| 112 | [Trend Trader Pro.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/Trend%20Trader%20Pro.txt) | 38 | كود مصدر | مراجعة توقيت لازمة |
| 113 | [TrendFilter.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/TrendFilter.txt) | 120 | كود مصدر | مراجعة توقيت لازمة |
| 114 | [Ultimate Opening Range Breakout.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/Ultimate%20Opening%20Range%20Breakout.txt) | 29 | كود مصدر | لم تحسم الجاهزية |
| 115 | [Unmitigated.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/Unmitigated.txt) | 35 | كود مصدر | مراجعة توقيت لازمة |
| 116 | [VCE - Volatility Coil Edge.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/VCE%20-%20Volatility%20Coil%20Edge.txt) | 25 | كود مصدر | لم تحسم الجاهزية |
| 117 | [simplealgo v3.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/simplealgo%20v3.txt) | 62 | كود مصدر | مراجعة توقيت لازمة |
| 118 | [sniper entry with tp&sl.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/sniper%20entry%20with%20tp%26sl.txt) | 5 | كود مصدر | مراجعة توقيت لازمة |
| 119 | [sqzmom.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/sqzmom.txt) | 19 | كود مصدر | لم تحسم الجاهزية |
| 120 | [strategy with signals.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/6/strategy%20with%20signals.txt) | 126 | كود مصدر | مراجعة توقيت لازمة |
| 121 | [Viprasol.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/7/Viprasol.txt) | 25 | كود مصدر | لم تحسم الجاهزية |
| 122 | [Volatility Covenant Ribbon.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/7/Volatility%20Covenant%20Ribbon.txt) | 28 | كود مصدر | لم تحسم الجاهزية |
| 123 | [WaveTrend.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/7/WaveTrend.txt) | 261 | كود مصدر | مراجعة توقيت لازمة |
| 124 | [X.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/7/X.txt) | 54 | كود مصدر | مراجعة توقيت لازمة |
| 125 | [XALGOX-15M_1H_1D.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/7/XALGOX-15M_1H_1D.txt) | 57 | كود مصدر | مراجعة توقيت لازمة |
| 126 | [XALGOX.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/7/XALGOX.txt) | 57 | كود مصدر | مراجعة توقيت لازمة |
| 127 | [Xpert Algo.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/7/Xpert%20Algo.txt) | 54 | كود مصدر | مراجعة توقيت لازمة |
| 128 | [ZZ Algo  Signals & Overlays.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/7/ZZ%20Algo%20%20Signals%20%26%20Overlays.txt) | 34 | كود مصدر | مراجعة توقيت لازمة |
| 129 | [ZZ Algo.txt](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/library/indicators/7/ZZ%20Algo.txt) | 34 | كود مصدر | مراجعة توقيت لازمة |

## ملحق ب — التعريفات التاريخية الـ52، كل سطر نسخة مستقلة
المصدر tools/l0090/indicators84.py. هذه أسماء معرفة في كود تاريخي؛ لا تعني أن المحرك الشامل الجديد اختبرها أو أن إعداداتها هي أفضل إعدادات. الصيغ والمجالات والبذور مثبتة في مصدرها وتدخل سجل النسخ عند مراجعتها، ولا تُحوّل قائمتهما إلى52عائلة مختلفة.
| المعرف | التعريف المسجل تاريخيًا |
|---|---|
| H52-01 | Aroon14_bull_x |
| H52-02 | Aroon25_bull_x |
| H52-03 | BB20_2.0_reenter |
| H52-04 | BB20_2.5_reenter |
| H52-05 | BB20_3.0_reenter |
| H52-06 | BullEngulfing |
| H52-07 | CCI14_xup_-100 |
| H52-08 | CCI20_xup_-100 |
| H52-09 | Donchian10_break |
| H52-10 | Donchian20_break |
| H52-11 | Donchian20_fail |
| H52-12 | Donchian55_break |
| H52-13 | EMA_x_20_200 |
| H52-14 | EMA_x_20_50 |
| H52-15 | EMA_x_50_200 |
| H52-16 | FVG_single |
| H52-17 | Hammer |
| H52-18 | MACD_12_26_9_xup |
| H52-19 | MACD_5_35_5_xup |
| H52-20 | MFI14_xup_20 |
| H52-21 | PX_x_EMA200 |
| H52-22 | PX_x_EMA50 |
| H52-23 | RSI14_bull_divergence |
| H52-24 | RSI14_xup_20 |
| H52-25 | RSI14_xup_25 |
| H52-26 | RSI14_xup_30 |
| H52-27 | RSI21_bull_divergence |
| H52-28 | RSI21_xup_20 |
| H52-29 | RSI21_xup_25 |
| H52-30 | RSI21_xup_30 |
| H52-31 | RSI7_xup_20 |
| H52-32 | RSI7_xup_25 |
| H52-33 | RSI7_xup_30 |
| H52-34 | Stoch14_3_xup_15 |
| H52-35 | Stoch14_3_xup_20 |
| H52-36 | Stoch14_3_xup_25 |
| H52-37 | Stoch21_5_xup_15 |
| H52-38 | Stoch21_5_xup_20 |
| H52-39 | Stoch21_5_xup_25 |
| H52-40 | TakerRatioZ_ge_1.5 |
| H52-41 | TakerRatioZ_ge_2.0 |
| H52-42 | TakerRatioZ_ge_2.5 |
| H52-43 | TakerRatio_gt_0.48 |
| H52-44 | TakerRatio_gt_0.5 |
| H52-45 | TakerRatio_gt_0.52 |
| H52-46 | TakerRatio_gt_0.55 |
| H52-47 | VolSpike_z1.5 |
| H52-48 | VolSpike_z2.0 |
| H52-49 | VolSpike_z2.5 |
| H52-50 | VolSpike_z3.0 |
| H52-51 | WilliamsR14_xup_-80 |
| H52-52 | WilliamsR21_xup_-80 |

## ملحق ج — تأكيدات الشموع المستقلة الموثقة
المصدر history/research/hyp_lab_out/L0092-candle-confirmation/REGISTRATION.md. توجد6نسخ: Hammer2وHammer3،BullEngulf1وBullEngulf1.25،MorningStar0.5وMorningStar1. تتطلب التعريفات السابقة هبوطًا معلومًا عبر6شموع؛ المطرقة جسم موجب≤35%المدى وظل سفلي≥2أو3أضعاف الجسم وعلوي≤الجسم وإغلاق في أعلى40%؛ الابتلاع سابقة هابطة وحالية صاعدة واحتواء الجسم مع معامل1أو1.25؛ نجم الصباح الأولى هابطة جسمها≥50%مدىها، الوسطى جسمها≤30%جسم الأولى، الثالثة صاعدة جسمها≥50%مدىها وتسترد0.5أو1من جسم الأولى، دون اشتراط فجوة افتتاح. هذه تعريفات معدلة للعملات المتصلة، لا نماذج تقليدية مزعومة مطابقة. تُراجع إتاحتها عند اكتمال الشمعة الأخيرة؛ لا تنقل حدود النتيجة المالية أو الحواجز أو مزائج CCI من الجولة القديمة.

## ملحق د — الأسماء والمتطلبات الإضافية
الأسماء الموثقة في history/docs/library/اسماء المؤشرات.txt تشمل CCI،Fibonacci،SMA،EMA،MACD،SuperTrend،ADX،RSI،Cardwell RSI،Stochastic،Momentum،DeMarker،Volume،Volume MA،Fixed/Session Volume Profile،VWAP،Anchored VWAP،CVD،Bollinger،ATR،ZigZag،Footprint،Lorentzian Classification. ورود الاسم لا يثبت اكتمال تعريفه أو برمجته.
ورقة إعدادات المؤشرات القديمة تسجل مثلًا ValueArea70وRows70–100،VWAP bands1/2/3،Cardwell RSI14وSMA9وEMA45ومناطق40–80و20–60. هذه قيم مذكورة في المصدر، وليست كلها شبكات كاملة أو قيمًا «مثبتة الأفضلية». لا يُتبنى ادعاء مساواة70%بانحراف معياري دون فحص، ولا تختار نقطة تثبيت من المستقبل.

## ملحق هـ — الوثائق الثنائية المحصورة ولم يُقرأ محتواها في هذا التحضير
| الوثيقة المثبتة | بايت | حالة التغطية |
|---|---:|---|
| [استراتيجيات تداول السبوت الناجحة.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/workspace/uploads/%D8%A7%D8%B3%D8%AA%D8%B1%D8%A7%D8%AA%D9%8A%D8%AC%D9%8A%D8%A7%D8%AA%20%D8%AA%D8%AF%D8%A7%D9%88%D9%84%20%D8%A7%D9%84%D8%B3%D8%A8%D9%88%D8%AA%20%D8%A7%D9%84%D9%86%D8%A7%D8%AC%D8%AD%D8%A9.pdf) | 278325 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [الاستعداد للتحليل المعماري للاستراتيجيات.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/workspace/uploads/%D8%A7%D9%84%D8%A7%D8%B3%D8%AA%D8%B9%D8%AF%D8%A7%D8%AF%20%D9%84%D9%84%D8%AA%D8%AD%D9%84%D9%8A%D9%84%20%D8%A7%D9%84%D9%85%D8%B9%D9%85%D8%A7%D8%B1%D9%8A%20%D9%84%D9%84%D8%A7%D8%B3%D8%AA%D8%B1%D8%A7%D8%AA%D9%8A%D8%AC%D9%8A%D8%A7%D8%AA.pdf) | 381133 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [بحث_التداول_الفوري_المؤشرات_والاستراتيجيات.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/workspace/uploads/%D8%A8%D8%AD%D8%AB_%D8%A7%D9%84%D8%AA%D8%AF%D8%A7%D9%88%D9%84_%D8%A7%D9%84%D9%81%D9%88%D8%B1%D9%8A_%D8%A7%D9%84%D9%85%D8%A4%D8%B4%D8%B1%D8%A7%D8%AA_%D9%88%D8%A7%D9%84%D8%A7%D8%B3%D8%AA%D8%B1%D8%A7%D8%AA%D9%8A%D8%AC%D9%8A%D8%A7%D8%AA.pdf) | 136021 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [تاريخ العملات وارتباطها بالبيتكوين.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/workspace/uploads/%D8%AA%D8%A7%D8%B1%D9%8A%D8%AE%20%D8%A7%D9%84%D8%B9%D9%85%D9%84%D8%A7%D8%AA%20%D9%88%D8%A7%D8%B1%D8%AA%D8%A8%D8%A7%D8%B7%D9%87%D8%A7%20%D8%A8%D8%A7%D9%84%D8%A8%D9%8A%D8%AA%D9%83%D9%88%D9%8A%D9%86.pdf) | 268561 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [تطوير بوت تداول ذكي بتيرمكس.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/workspace/uploads/%D8%AA%D8%B7%D9%88%D9%8A%D8%B1%20%D8%A8%D9%88%D8%AA%20%D8%AA%D8%AF%D8%A7%D9%88%D9%84%20%D8%B0%D9%83%D9%8A%20%D8%A8%D8%AA%D9%8A%D8%B1%D9%85%D9%83%D8%B3.pdf) | 460886 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [دليل التداول الفوري الشامل.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/workspace/uploads/%D8%AF%D9%84%D9%8A%D9%84%20%D8%A7%D9%84%D8%AA%D8%AF%D8%A7%D9%88%D9%84%20%D8%A7%D9%84%D9%81%D9%88%D8%B1%D9%8A%20%D8%A7%D9%84%D8%B4%D8%A7%D9%85%D9%84.pdf) | 263719 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [شرح شامل لبوتات التداول في بينانس.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/workspace/uploads/%D8%B4%D8%B1%D8%AD%20%D8%B4%D8%A7%D9%85%D9%84%20%D9%84%D8%A8%D9%88%D8%AA%D8%A7%D8%AA%20%D8%A7%D9%84%D8%AA%D8%AF%D8%A7%D9%88%D9%84%20%D9%81%D9%8A%20%D8%A8%D9%8A%D9%86%D8%A7%D9%86%D8%B3.pdf) | 198439 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [مخطط البوت الجديد.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/workspace/uploads/%D9%85%D8%AE%D8%B7%D8%B7%20%D8%A7%D9%84%D8%A8%D9%88%D8%AA%20%D8%A7%D9%84%D8%AC%D8%AF%D9%8A%D8%AF.pdf) | 250405 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [Master Blueprint.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D8%A4%D8%B4%D8%B1%D8%A7%D8%AA/Master%20Blueprint.pdf) | 204649 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [استراتيجيات سكالبينج سريعة وناجحة.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D9%84%D9%81%D8%A7%D8%AA/%D8%A7%D8%B3%D8%AA%D8%B1%D8%A7%D8%AA%D9%8A%D8%AC%D9%8A%D8%A7%D8%AA%20%D8%B3%D9%83%D8%A7%D9%84%D8%A8%D9%8A%D9%86%D8%AC%20%D8%B3%D8%B1%D9%8A%D8%B9%D8%A9%20%D9%88%D9%86%D8%A7%D8%AC%D8%AD%D8%A9.pdf) | 285461 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [استراتيجيات ومؤشرات التداول الاحترافية.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D9%84%D9%81%D8%A7%D8%AA/%D8%A7%D8%B3%D8%AA%D8%B1%D8%A7%D8%AA%D9%8A%D8%AC%D9%8A%D8%A7%D8%AA%20%D9%88%D9%85%D8%A4%D8%B4%D8%B1%D8%A7%D8%AA%20%D8%A7%D9%84%D8%AA%D8%AF%D8%A7%D9%88%D9%84%20%D8%A7%D9%84%D8%A7%D8%AD%D8%AA%D8%B1%D8%A7%D9%81%D9%8A%D8%A9.pdf) | 260187 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [بحث خوارزميات مؤشر هانتر للتداول.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D9%84%D9%81%D8%A7%D8%AA/%D8%A8%D8%AD%D8%AB%20%D8%AE%D9%88%D8%A7%D8%B1%D8%B2%D9%85%D9%8A%D8%A7%D8%AA%20%D9%85%D8%A4%D8%B4%D8%B1%20%D9%87%D8%A7%D9%86%D8%AA%D8%B1%20%D9%84%D9%84%D8%AA%D8%AF%D8%A7%D9%88%D9%84.pdf) | 241407 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [تحسين أداء بوت التداول الآلي.docx](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D9%84%D9%81%D8%A7%D8%AA/%D8%AA%D8%AD%D8%B3%D9%8A%D9%86%20%D8%A3%D8%AF%D8%A7%D8%A1%20%D8%A8%D9%88%D8%AA%20%D8%A7%D9%84%D8%AA%D8%AF%D8%A7%D9%88%D9%84%20%D8%A7%D9%84%D8%A2%D9%84%D9%8A.docx) | 359784 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [تحليل أكواد MQL5 لبوت بايثون.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D9%84%D9%81%D8%A7%D8%AA/%D8%AA%D8%AD%D9%84%D9%8A%D9%84%20%D8%A3%D9%83%D9%88%D8%A7%D8%AF%20MQL5%20%D9%84%D8%A8%D9%88%D8%AA%20%D8%A8%D8%A7%D9%8A%D8%AB%D9%88%D9%86.pdf) | 327894 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [تحليل شامل لاستراتيجية الزيرو انعكاس (2).docx](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D9%84%D9%81%D8%A7%D8%AA/%D8%AA%D8%AD%D9%84%D9%8A%D9%84%20%D8%B4%D8%A7%D9%85%D9%84%20%D9%84%D8%A7%D8%B3%D8%AA%D8%B1%D8%A7%D8%AA%D9%8A%D8%AC%D9%8A%D8%A9%20%D8%A7%D9%84%D8%B2%D9%8A%D8%B1%D9%88%20%D8%A7%D9%86%D8%B9%D9%83%D8%A7%D8%B3%20%282%29.docx) | 3147341 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [تحليل شامل لمحتوى كورس يوتيوب.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D9%84%D9%81%D8%A7%D8%AA/%D8%AA%D8%AD%D9%84%D9%8A%D9%84%20%D8%B4%D8%A7%D9%85%D9%84%20%D9%84%D9%85%D8%AD%D8%AA%D9%88%D9%89%20%D9%83%D9%88%D8%B1%D8%B3%20%D9%8A%D9%88%D8%AA%D9%8A%D9%88%D8%A8.pdf) | 2539390 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [دليل شامل عن مؤشر هنتر - Google Gemini.pdf](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D9%84%D9%81%D8%A7%D8%AA/%D8%AF%D9%84%D9%8A%D9%84%20%D8%B4%D8%A7%D9%85%D9%84%20%D8%B9%D9%86%20%D9%85%D8%A4%D8%B4%D8%B1%20%D9%87%D9%86%D8%AA%D8%B1%20-%20Google%20Gemini.pdf) | 2697833 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
| [دليل شامل عن مؤشر هنتر.docx](https://github.com/stevearagonno1/NOVA-DRAGON/blob/6d0226a03b84656e14b94dd8a37e39332cc2f68f/history/clean/NOVA_bin_pending/%D9%85%D9%84%D9%81%D8%A7%D8%AA/%D8%AF%D9%84%D9%8A%D9%84%20%D8%B4%D8%A7%D9%85%D9%84%20%D8%B9%D9%86%20%D9%85%D8%A4%D8%B4%D8%B1%20%D9%87%D9%86%D8%AA%D8%B1.docx) | 3331271 | حُصر مساره؛ لم يستخرج محتواه في هذا التحضير |
