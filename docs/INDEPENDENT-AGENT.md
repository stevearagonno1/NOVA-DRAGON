# الوكيل المستقل — تشغيل داخل خدمة Render الحالية

## القرار الأحدث: خدمة واحدة مجانية

المالك اشترط المجانية ثم طلب تعديل الخدمة الحالية بدل إنشاء خدمة ثانية. هذا هو المسار المعتمد الآن؛ أقسام الخدمة المنفصلة أدناه مرجع قديم فقط، ولا تُطبّق في هذا المسار.

لا تنشئ Web Service جديدة. استخدم خدمة NOVA DRAGON الحالية وعنوانها https://nova-dragon.onrender.com. تُشغّل الحزمة LiteLLM وOpenCrabs معًا؛ LiteLLM يحتفظ بالمنفذ العام وبمسار /v1، والوكيل يتصل به محليًا. ملف litellm_config.yaml الحالي يبقى دون تعديل. يستخدم OpenCrabs قناة Telegram الأصلية وموافقاتها؛ لا يصل الذكاء الاصطناعي إلى التداول الحي.

### إعدادات الخدمة الحالية، قبل إعادة النشر

| الحقل | القيمة |
|---|---|
| Branch | agent/independent-2026-10-01 |
| Dockerfile Path | tools/agent_combined.Dockerfile |
| Docker Build Context | جذر المستودع |
| Root Directory | فارغ |
| Compute | Free |
| AGENT_STORAGE_MODE | ephemeral |

أضف TELEGRAM_BOT_TOKEN وTELEGRAM_OWNER_ID وGITHUB_TOKEN إلى Environment في خدمة Render الحالية. لا ترسل قيمها في المحادثة. AGENT_MODEL الافتراضي opencrabs-model. في الوضع الموحّد يستخرج المشرف مفتاح بوابة LiteLLM من general_settings.master_key في ملفها الحالي، أو يستخدم LITELLM_API_KEY من Environment إن عيّنته؛ لا يحتاج نسخ المفتاح إلى الدردشة. اتصال LITELLM_BASE_URL داخلي ويحدده المشرف تلقائيًا.

قبل تغيير Branch تحقق من إعداد Auto-Deploy في Render: احفظ إعدادات Environment أولًا، ثم غيّر مسار Dockerfile والفرع في آخر خطوة. تغيير إعدادات الخدمة قد يطلق نشرًا، ولذلك لا تغيّر الفرع قبل تجهيز المفاتيح المطلوبة. لا دمج إلى main؛ النشر من فرع العمل.

يبقى cron-job.org على https://nova-dragon.onrender.com/ كل 10 دقائق كما ضبطه المالك. هذا طلب استيقاظ، وليس نسخًا احتياطيًا. خدمة واحدة طوال شهر من 31 يومًا تستهلك نحو 744 ساعة؛ سقف 750 ساعة على Render مشترك مع كل الخدمات المجانية الأخرى، وتظل حدود النقل والبناء قائمة. لا ضمان للعمل الدائم أو لعدم إعادة التشغيل. المحادثات المحلية قد تضيع؛ الوثائق المرفوعة إلى GitHub هي الذاكرة الموثوقة.

### اختبار بعد النشر

1. تحقق أن Render يعرض Live وأن /v1/models ما زال يعمل بالمفتاح المعتاد (لا تنشر المفتاح أو الرد المحتوي على معلومات حساسة).
2. افتح بوت Telegram وأرسل طلب قراءة CONSTITUTION.md وآخر تكة جلسة وسجل Git، دون تعديل. تحقق من استخدام الأدوات.
3. اختبر رفض طلب تعديل وثيقة تجريبية؛ يجب أن تمر أوامر shell والكتابة بالموافقة.
4. راقب Logs والذاكرة؛ تشغيل العمليتين على 512 MB لم يُختبر هنا. لو وقع نقص ذاكرة لا نغيّر الخطة إلى مدفوعة دون اختيار المالك.

توجد 10 اختبارات Python محلية ناجحة. Docker وتشغيل Render وTelegram وأدوات Atria الفعلية لم تُختبر هنا بعد. مجانية حساب Atria لم تُتحقق؛ المجانية المعلنة تخص خطة Render ضمن حدودها فقط.

التالي: ضبط Environment أولًا ثم نشر الحزمة على الخدمة القائمة والتحقق من /v1 ومن قراءة المستودع عبر Telegram.

---

## مرجع سابق: الخدمة المنفصلة (غير معتمد الآن)

# الوكيل المستقل — OpenCrabs عبر Telegram

## الاختيار ولماذا

واجهة Telegram الأصلية هي الاختيار لهذه النسخة: المحادثة تُشغّل OpenCrabs نفسه، مع اكتشاف الأدوات وقراءة الملفات وأوامر Git وطلبات الموافقة. لا تُرسل الرسائل مباشرة إلى LiteLLM وتتوقع منه إدارة المستودع.

المسار: المالك في Telegram ← OpenCrabs مستقل على Render ← بوابة LiteLLM الحالية ← Atria. أدوات GitHub تعمل داخل خدمة OpenCrabs؛ ربط GitHub هنا في ChatGPT لا ينتقل تلقائيًا إلى تلك الخدمة.

النسخة المثبتة: OpenCrabs v0.5.4، مع تحقق SHA256 من ملف الإصدار الرسمي. لا يُستخدم opencrabs.zip الموجود في المستودع لأن نسخته غير متحققة. لا تغير هذه الحزمة Dockerfile أو start.sh أو خدمة LiteLLM الحالية.

## التفعيل في Render

أنشئ بوتًا خاصًا عبر BotFather في Telegram، وخذ رمز البوت. احصل على رقم حسابك الرقمي من مصدر موثوق؛ اسم المستخدم لا يكفي. لا ترسل أي مفتاح في المحادثة أو تحفظه في المستودع.

أُتيح إنشاء فرع العمل بعد أن ثبّت المالك موصل GitHub على حسابه. الحزمة على فرع `agent/independent-2026-10-01` دون دمج إلى main. رفض الصلاحيات الأول محفوظ في التكة 001؛ استئناف الرفع محفوظ في التكة 002.

أنشئ **Web Service مستقلة** من فرع `agent/independent-2026-10-01`. اختر Docker، ومسار Dockerfile هو `tools/agent.Dockerfile`، وسياق البناء الجذر، وRoot Directory فارغ. اختر خطة **Free** بلا قرص دائم. إعداد health check هو `/health`. وضع التخزين الافتراضي `ephemeral` ولا يحتاج دفعًا لخدمة الوكيل. موارد التشغيل الفعلية على ذاكرة 512 MB لم تُقَس هنا.

**قيود المجاني:** الخدمة قد تنام عند الخمول؛ رسائل Telegram تستخدم polling ولا تُوقظ Render وحدها. قبل المحادثة افتح عنوان خدمة الوكيل الجديدة مع `/health` وانتظر استيقاظها، ثم افتح البوت. المحادثات المحلية والعمل غير المرفوع يمكن أن يُفقدا عند إعادة التشغيل أو النشر. الذاكرة الموثوقة هي الوثائق وتكات الجلسات المرفوعة إلى GitHub؛ حفظها يحتاج صلاحية كتابة وموافقتك. لا نعد بعمل دائم أو بذاكرة محادثة دائمة على Free.

المجانية هنا تخص خطة خدمة الوكيل ضمن حدود Render؛ بوابة LiteLLM تستهلك حساب Atria، ولم يتم التحقق من مجانية استدعاءات النموذج أو سقف رصيدك. لا تضف وسيلة دفع أو خطة مدفوعة إذا كان شرطك صفر تكلفة.

لا تشغّل نسختين بنفس رمز بوت Telegram. تستخدم هذه الخدمة polling، ويفحص أمر التحقق وجود webhook قد يتعارض معه.

ضع القيم التالية في **Environment** بالخدمة الجديدة:

| الاسم | القيمة المطلوبة |
|---|---|
| `TELEGRAM_BOT_TOKEN` | رمز البوت الخاص من BotFather |
| `TELEGRAM_OWNER_ID` | رقم حسابك في Telegram، أرقام فقط |
| `GITHUB_TOKEN` | رمز GitHub محدد لهذا المستودع فقط؛ ابدأ بـ Contents: Read-only. أضف Issues/Pull requests: Read-only إذا احتجت قراءة المناقشات |
| `LITELLM_API_KEY` | مفتاح دخول موزع LiteLLM، وليس مفتاح Atria |
| `LITELLM_BASE_URL` | `https://nova-dragon.onrender.com/v1` |
| `AGENT_MODEL` | `opencrabs-model` |
| `AGENT_STORAGE_MODE` | `ephemeral` (وضع Free؛ وهو الافتراضي) |

لو أردت حفظ تغييرات الوكيل في GitHub لاحقًا، يحتاج رمز GitHub صلاحية Contents: Read and write بعد قرارك. يبقى الدفع لفروع `agent/*` فقط. الرمز المحدد للمستودع لا يفرض وحده حصر الكتابة بفرع؛ للحماية الملزمة اضبط قواعد GitHub من حساب المالك بحيث لا يستطيع هذا الاعتماد تجاوز حماية `main`، أو أبقِه للقراءة فقط. خطاف pre-push حاجز ضد الخطأ ويمكن تجاوزه ممن لديه أوامر shell؛ لا نقدمه كحد أمني مطلق.

## اختبار الربط بعد نشر الخدمة

ماذا يفعل: يتحقق من البوت والمستودع والنموذج، ويطلب من النموذج استدعاء أداة اختبار دون أي تعديل؛ يتضمن طلب نموذج صغيرًا قد يُحتسب ماليًا.
أين يعمل: على جهاز يملك Python 3.11+ ومتغيرات البيئة المطلوبة، أو Render Shell إن كانت متاحة في خطتك؛ خطة Free لا توفر Shell، لذلك اختبار القراءة والموافقة من Telegram هو اختبار التفعيل العملي فيها.
ما ترسله عند الانتهاء: النص بين العلامتين؛ إذا ظهر خطأ أرسله كاملًا. لا ترسل مفاتيح.

```bash
printf '%s\n' 'NOVA_CHECK_BEGIN'
python3 /opt/nova-agent/agent_preflight.py --check-model
printf '%s\n' 'NOVA_CHECK_END'
```

بعد نجاح الفحص، افتح بوتك الخاص في Telegram وأرسل:

> اقرأ CONSTITUTION.md كاملًا من /state/repo ثم وثيقة التسليم والقرارات وآخر سجل جلسة. اعرض آخر حالة موثقة مع مسارات المصادر. نفّذ قراءة واحدة فعلية من سجل Git، ولا تعدّل شيئًا.

تحقق أن الرد يستند إلى قراءة ملفات وأدوات حقيقية. ثم اختبر طلب تعديل وثيقة تجريبية على فرع عمل: يجب أن تظهر موافقة قبل التنفيذ. ارفض أول طلب للتأكد من عدم وقوع التعديل. لا تختبر على البوت أو الدستور أو البيانات.

## ما يبقى محفوظًا وما يمكن قراءته

المحادثات وذاكرة OpenCrabs في `/state/opencrabs`، ونسخة العمل الخفيفة في `/state/repo`. على Free يمكن فقدهما عند إعادة التشغيل؛ لا تعني كلمة /state قرصًا دائمًا. اختيار persistent اختياري فقط إذا طلب المالك مستقبلًا قرصًا مدفوعًا. لا ينفذ التشغيل إعادة ضبط أو حذفًا أو سحبًا فوق عمل معلّق. تعليمات AGENTS.md المُدارة والإعدادات والمفاتيح تُعاد كتابتها من هذه الحزمة وEnvironment عند بدء الخدمة؛ لا تستخدمها لتعديلات شخصية غير موثقة.

تحتفظ نسخة Git بالتاريخ وتؤجل تنزيل الملفات الثقيلة. تُفتح الوثائق والأدوات وكود المختبر فقط؛ النتائج والأرشيف والمحرك متاحة بالمسار عبر git show أو gh عند الحاجة، وليست محملة كلها. يجب تحديث المعرفة بأداة قراءة أو git fetch؛ اتصال النموذج وحده ليس ذاكرة. آخر وثيقة تسليم قديمة بالنسبة إلى بعض السجلات؛ الوكيل ملزم بالإعلان عن هذا التعارض.

لا مفاتيح منصات تداول في هذه الخدمة. تشغيل RSI والتحديث التلقائي والبوابة العامة A2A معطل. سياسة الأدوات ask؛ قراءة الملفات العادية قد تعمل مباشرة، وأوامر shell والتعديلات تمر بموافقة القناة. لا تفعّل YOLO أو الموافقة الدائمة.

## ما تم التحقق منه وما لم يتم

- اختبارات Python محلية: صيغة إعدادات TOML، حصر المستخدم، رفض إعدادات غير صالحة، فصل المفاتيح وصلاحية ملفها، حفظ العمل عند إعادة التشغيل، خطاف الدفع، وصحة استدعاء الأداة.
- مطابقة خيارات الإعداد مع كود OpenCrabs في الوسم v0.5.4؛ تحقق من الاستدعاء الفعلي للوكيل وأزرار موافقة Telegram، ومن غياب الموافقة التفاعلية في A2A.
- **لم يُبنَ Docker ولم تُنشَر الخدمة هنا.** لم يُختبر تسجيل دخول Telegram أو GitHub من خدمة Render، ولا استدعاء الأدوات والبث من نموذج Atria؛ لذلك لا توجد شهادة تشغيل كامل بعد.
- فحص النموذج غير المتدفق لا يثبت بث الردود ولا سلسلة أدوات طويلة؛ اختبار المحادثة الفعلية أعلاه شرط إكمال التشغيل.
- قوة الاستدلال تعتمد على النموذج نفسه؛ زيادة الأدوات لا تثبت أن Atria أفضل نموذج للمشروع.

مراجع التحقق: https://github.com/adolfousier/opencrabs/tree/v0.5.4 · https://docs.opencrabs.com/getting-started/configuration.html · https://render.com/docs/disks

التالي: نشر خدمة Free ثم فتح /health واختبار قراءة المستودع والموافقة من Telegram؛ لا دمج إلى main ولا تداول حي.

## Scoped repository reads without approval

Bootstrap installs four managed OpenCrabs dynamic tools: `nova_repo_status`,
`nova_repo_commits`, `nova_repo_list`, and `nova_repo_read`. Discover them with
`tool_search`. They read GitHub main through fixed-repository GET requests and
require no interactive approval. The executor is a fixed Python command; inputs
are JSON through OPENCRABS_PARAMS, never interpolated into shell commands.
Read results include commit/blob provenance. Text reads are limited to 64 KiB;
hidden/credential paths, binaries, arbitrary URLs, writes and redirects are denied.
The GitHub token stays inside the helper process. Other shell commands still use
approval_policy="ask". This is not YOLO or blanket shell permission.
The managed tools.toml is regenerated on startup. Render deployment and a real
Telegram tool-discovery/read test are still needed to verify runtime behavior.

## Background review council and credential failover

The combined service now runs a private localhost review queue alongside LiteLLM
and the Telegram coordinator. `nova_council_submit` accepts a complete scoped
read-only task paper, lead context and up to five source paths. The constitution
is always read in full; all sources are pinned to the same GitHub main commit.
Three reviewers independently propose/audit/challenge, then a cross-review resolves
conflicts and a synthesizer emits one Arabic result. These are separate model
requests on the existing model, not different trained models or proof by consensus.
The roles have no tools, shell, trading or repository mutation capability.

One review job runs at a time with at most two reviewer calls concurrent; one more
job may queue. Identical active submissions return the same ID. Five model requests
per completed review, excluding gateway retries. The coordinator remains available.
Only the final result or a blocked notice is sent to TELEGRAM_OWNER_ID. Use
`nova_council_status` only when asked, not busy polling. Native spawn/team tools are
not used for this flow because v0.5.4 requires approval. A parent tool/progress card
may still appear; this version has no Telegram setting to hide all such cards.

`agent_router.py` builds a private runtime YAML overlay, preserving the original
source configuration, endpoints, alias and configured deployment limits. It adds
bounded same-pool retry/failover and cooldown, stable deployment IDs, and collapses
duplicate same-upstream credentials. Extra TOKEN_N variables alone do not configure
new deployments. A key is a credential, not a separate brain or a guaranteed
independent quota. Shared account limits and exhausted free allowances still apply.
The gateway returns an error after bounded attempts; it does not retry forever.

Files: tools/agent_council.py, tools/agent_router.py, tools/test_council.py,
tools/test_router.py. Runtime config and job files are private mode0600. Job state
is temporary on Render Free, not permanent repository memory. Interrupted jobs are
marked interrupted if the local files survived; they are not called completed.
32 retained job records are permitted before further submissions are blocked;
archival/cleanup must be arranged deliberately, not silently delete repository data.
This implementation delegates research/review, not CPU-heavy backtests or execution.
Long experiment execution still needs an explicitly scoped executor and compute.
No new paid services/providers are introduced; more review calls consume more quota.

Validation: 30 local tests passed. They cover phase ordering, final-only notification,
duplicate suppression, queue bounds, interruption/failure state, source pinning,
private file permissions, fixed command scopes, redaction, configuration preservation
and failover settings. Real provider failover, Render resource usage and Telegram
completion remain unmeasured until deployed/tested; no keys were used in local tests.

References: https://docs.litellm.ai/docs/routing ·
https://github.com/adolfousier/opencrabs/blob/v0.5.4/src/brain/tools/subagent/spawn.rs ·
https://github.com/adolfousier/opencrabs/blob/v0.5.4/src/channels/telegram/stream_loop.rs
