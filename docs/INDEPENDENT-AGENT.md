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

### Timeout correction after the first Telegram trial

The initial trial started a real council job but reported TimeoutError, not a
completed review. The original message did not identify the phase, so its exact
source remains undetermined. Council model HTTP waits now allow 360 seconds
(previously120), covering more gateway retry latency. Source fetching keeps its
existing25-second per-read bound. Phase and completed-request counters are stored
and exposed in nova_council_status; blocked notices name the stage and safe HTTP
code where present. This is diagnostic visibility, not proof that latency is fixed.
The parent should finish its turn promptly after submission and avoid stale running
claims or unrelated config_manager inspection. A small deployment retest is required.

### Streaming reviewer transport after zero-completion trial

The second live trial submitted a real job but stopped in independent_review with
zero of five requests complete. The root upstream cause remains unconfirmed.
The reviewer transport now uses the SAME configured Atria model/endpoint directly,
with SSE rather than buffering the entire non-stream JSON response via LiteLLM.
It reads existing private runtime deployments, never caller-selected URLs or keys.
The lead continues to use the LiteLLM gateway. Direct review HTTP is no longer
subject to the gateway's buffering and retry layers; it has its own bounded policy.

Unique configured credentials are ordered by existing deployment order. Preferred
slots1–3 correspond to the three reviewers; slots4–5 to cross-review/synthesis.
Slots6–10 are first reserves, then other healthy credentials. This guarantees
distinct preferred credentials when at least five unique keys are configured,
not different trained models or guaranteed independent account quotas. Maximum
three attempts per request. Auth/quota/transient failures receive cooldown;
Retry-After is respected. HTTP400 and malformed/incomplete answers do not rotate
blindly. Streaming is documented, but non-streaming is also officially supported;
we do not claim non-streaming is unsupported or proven to cause the failures.

Inter-read/start timeout90 seconds, total streaming bound600 seconds, body bound2MiB.
These are transport bounds, not a promise of fast upstream completion. Final-answer
content only is retained; reasoning fields/tags are excluded. A partial stream without
a terminal event is never delivered as a completed collective review. Model output
cap6144 tokens accommodates reasoning plus a concise final answer; this may consume
more quota than the earlier1800 cap. No new paid service is introduced.

References: https://api.atria-asi.ai/docs ·
https://github.com/adolfousier/opencrabs/blob/v0.5.4/src/brain/provider/custom_openai_compatible.rs
The preceding360-second non-stream transport description is historical and superseded
for reviewer model calls. Other JSON control/Telegram calls retain their own timeouts.

### Safe diagnostics after ValueError

Use `nova_council_diagnostics` before another long review trial. This performs only
local validation: fixed Atria endpoint/model, number of unique resolved credentials,
and whether three reviewer preferences can be distinct. It makes zero model/API
requests and explicitly does not verify provider acceptance. Error output contains
only enumerated safe reasons and slot numbers; never credentials/fingerprints/raw
exception bodies. Outer whitespace is trimmed; internal whitespace/control/non-ASCII
characters in a credential are rejected with a safe credential_invalid_format code.
Blocked jobs now expose reason_code, error_slot and source error_location; Render
logs have only job id/phase/code/location. No traceback locals or error body is logged.

### Isolated single-credential connection probe

`nova_council_probe` starts one background request using the first configured unique
credential only. It has a512-token cap, a fixed tiny connection-check prompt, zero
repository source reads, and no fallback. It does not run three reviewers, cross-review
or synthesis. A successful complete response verifies one real connection; it proves
neither acceptance of the other nine credentials nor completion of a collective task.
Use after local diagnostics are valid, before another full review trial. Probe failures
include the safe reason/location and expected/completed request count1. Raw model
probe text and credentials are not delivered to the owner.

### Repeated deliberation (prepared on isolated agent branch)

Supersedes the earlier single cross-review stage. Three independent reviewers first
read the same pinned source snapshot. A moderator creates one exact shared proposal;
all three reviewers then see every initial report, the proposal and previous votes.
Each returns a structured vote and any blocking objections. Later rounds revise the
proposal against those objections; reviewers are explicitly allowed to dissent.
The application validates the proposal identifier, boolean approval and empty blocking
objections for all three votes. A majority, prose claim of agreement, malformed vote,
or approval with a blocking objection cannot count as unanimous consensus.

Stop at validated unanimity or after three rounds. Persistent dissent is reported as
no final collective decision, rather than forcing agreement. Consensus is not evidence
of empirical correctness and does not replace measurement. One final Arabic summary
is delivered; full reviewer transcripts are not sent to Telegram. Three reviewers use
separate preferred credential slots; ten available keys do not create ten reviewers.
Existing bounded failover remains available, subject to provider account limits.

First-round unanimity uses eight completed model calls; three rounds use sixteen.
These are logical model calls, not HTTP attempt counts: failover may add bounded
attempts. Additional rounds consume more quota and time. No additional paid service
is introduced, and no free quota guarantee is made. Only one job runs at a time.
Read-only review scope and existing source/secret guards are retained.

Prepared on agent/deliberation-2026-10-02 without moving the deployed branch, so the
ongoing live review is not interrupted by an automatic Render restart. Activating
this branch requires a later deployment after that review reaches a terminal state.
Validation: 53 local tests pass, including early unanimity, second-round objection
sharing, persistent dissent, invalid votes and maximum round bounds. This is local
validation; repeated deliberation has not yet been tested with the live provider.

### Empty final-answer handling after live deliberation trial

The live review reported zero accepted completions and `no_final_answer` before any
round began. This does not establish zero provider usage or invalid credentials;
the old message cannot distinguish an empty response, reasoning-only response,
output cap, filter or refusal. No raw provider transcript is available for this trial.

Response validation now distinguishes those outcomes using fixed safe reason codes
and the credential slot only, never raw reasoning, refusal text or credentials.
Empty/reasoning-only completed responses try existing reserve candidates within the
same maximum of three attempts. Filters, refusals and output-limit responses do not
rotate. Truncated output is rejected for both SSE and JSON instead of being treated
as a finished reviewer answer. Standard text content parts are supported, while
reasoning parts remain excluded. Output token cap and round count remain unchanged.

Validation: 58 local tests pass. Added tests cover empty versus reasoning-only outcomes,
content parts, reserve fallback/three-attempt bound, no retry for refusal/filter/length,
and identical truncated-output rejection in JSON. Root cause of the historical trial
remains unconfirmed; live verification of the change is pending.

### Reviewer output budget after confirmed truncation

Live job 3b748395c5cb2e6d accepted two initial reviewer completions, then blocked
on output_limit_reached in credential slot7. No discussion round completed. This
confirms truncation in that attempt, not a credential failure or zero token usage.

Reviewer generation cap increased from6144 to16384 tokens. Official Atria docs
https://api.atria-asi.ai/docs, checked2026-10-02, state Chat Completions accepts
max_tokens or max_completion_tokens with output integer limits1..65536. This cap
reserves room for completion; it is not a target or a measured usage figure.
Initial findings are now requested under2400 characters, proposals under1200,
objections under500 and revisions under1200; these are prompt targets rather than
claims about provider-enforced character limits. Full evidence and source guards
remain. Three discussion rounds, concurrency two, transport time/size limits and
bounded failover remain unchanged. Truncated output still cannot count as success.
Higher allowed generation may increase quota use and latency; no new paid service.

Validation:58 local tests pass, including request cap16384 and separate probe cap512.
Live verification remains pending after the automatic Render deployment.

### Structured votes and shared review deadline

Live job de7facffa382ad43 blocked in discussion_round_1 at object_response after
six accepted logical calls. The location confirms JSON decoding failure; the raw
response was not available and cannot establish whether a prose wrapper, malformed
JSON or some other formatting error caused it. The previous vote example included
`true or false`, which is not valid JSON; it is now a valid JSON example with explicit
instructions to choose false for dissent and never interpret the example as approval.

One complete JSON object may now be read inside a prose/code-fence wrapper. Multiple
objects, duplicate fields, malformed/truncated objects, wrong proposal identifiers,
string booleans and blocking objections still cannot create consensus. No model call
is added to repair or reinterpret a vote. Provider response JSON-mode support is not
assumed. This improves wrapper handling but does not guarantee model compliance.

Production reviews now share one900-second monotonic deadline starting after source
fetching. It is passed through all stages, streams and fallback attempts. Queued calls
check it before sending; results arriving after it are rejected. Socket opening uses
at most the remaining deadline or90seconds. An in-flight read can take its already-set
socket timeout to finish, so900seconds is not a hard wall-clock guarantee. Source
fetch, job queue time and final Telegram notification are separate. Probe unchanged.
Failure is notified with a distinct Arabic deadline reason, never a invented decision.

Validation:63 local tests pass, including wrapped structured dissent, malformed,
truncated and duplicate/multiple objects, existing unanimity safeguards and shared
deadline checks before send, during streaming and after a late response. No live
provider trial has validated this change yet.

### Latency diagnosis after shared deadline trial

Live job d66e16defd7acc7d reached the shared deadline with two accepted initial
reviewer replies. No discussion round completed. This shows the current throughput
cannot finish this trial within the chosen budget; it does not determine provider
latency versus retry/input effects without request timings.

Independent reviews and round votes now start all three calls concurrently instead
of two with the third waiting for a worker. One active job, three rounds, request
counts, output caps and deadline remain unchanged. Provider limits still apply.
No throughput guarantee or free-instance load test is claimed.

Every production reviewer attempt now records only credential slot, elapsed seconds,
completed/failed outcome and enumerated reason code in request_timings, with its phase.
Status exposes these records (up to48 for16 calls times3 attempts) plus runtime_seconds,
including blocked jobs. No key, fingerprint, input, output or raw error body is recorded
in timing metadata. Probe job runtime is recorded; its direct single request does not
have reviewer attempt records. Runtime excludes queue wait and final notification.

Validation:66 local tests pass. Added a barrier test proving all three initial calls
can start together and timing tests for success/failure, ensuring metadata excludes
private input/output/error content. Live latency remains unmeasured by this change.
Do not repeat the full README review until the single small connection probe runtime
and subsequent per-attempt timing are available. Updates restart the free ephemeral
service and old job records can be lost.

### Identical three-credential latency probe

Recorded live task adedcdeff7dac22a: initial preferred slots1/2/3 completed in
154.17/174.85/344.99 seconds; moderator slot4 completed in49.11 seconds. First-round
votes on slots2/1 completed in209.43/260.23 seconds; slot3 was interrupted at505.98
seconds by the shared deadline. Job runtime901.34 seconds. Slot3 was the critical
path twice, but distinct reviewer roles/input still confound attributing this to its
credential alone. No credential is disabled or replaced on these observations.

`nova_council_probe_reviewers` schedules exactly one fixed tiny READY connection
request for each of the first three distinct resolved credentials, concurrently.
It does not load README, constitution, repository sources or task context; caller
parameters cannot alter its prompt, route, model, slots or source scope. No fallback,
no file writes apart from private job/timing records. Output cap512 per call and a
shared180-second deadline with existing socket-read completion caveat. A failure
is shown per slot, never as proof that all credentials succeeded. The diagnostic
job can complete even if a probe failed; completed_requests counts only successful
probe replies. It neither runs deliberation nor proves document-review throughput.

Tool count9 in combined deployment; standalone remains4. Explicit probes bypass
group-review dispatch. Status and the single-credential probe remain unchanged.
Validation:69 local tests pass, including simultaneous identical prompts, selection
of only first three slots, no retries/fallback, no sources, partial-failure reporting
and missing-credential refusal without an API call. Live comparison pending.

### Terminal control instructions and genuinely source-free council trial

Three-key probe560f5e6e9070f430 completed with slots1/2/3 at44.51/8.09/44.50seconds.
All three were accepted. This does not support disabling slot3 solely for the earlier
role-dependent latency. The main agent then attempted config_manager after the owner
asked for one probe only; that call was denied. Its claimed lack of an attempt was
incorrect. Native dynamic tools in pinned OpenCrabs do not expose a configurable
halts_turn flag; no hard native-tool disable is claimed by this change.

Managed instructions now put terminal control rules before general startup reading:
submit/probe/trial once, acknowledge ID/state, finish; explicit status once then finish;
stop/wait means zero tools. No config_manager, shell/session/cron search or suggestion
workflow around these narrowly scoped control operations. Service submit responses
include next_action=finish_turn. Missing job IDs return explicit not_found with a
safe ephemeral-record explanation and finish guidance instead of ambiguous []. These
are model instructions, not a guarantee against a model attempting a forbidden tool.
Existing approval gates remain enabled for native/general operations.

`nova_council_trial` is a fixed tiny diagnostic comparing two general report orders.
It ignores caller task/context/paths, loads no constitution or repository sources,
uses brief diagnostic reviewer roles, and runs the same validated repeated voting
pipeline up to3 rounds. It has a shared300-second review deadline with the existing
in-flight read caveat. It does not test full document-review latency or trading quality.
Normal nova_council_submit retains complete constitution/source review and900seconds.
Combined tool count10; standalone4. One active job and all existing safeguards remain.

Validation:71 local tests pass. Added explicit missing-record behavior and verification
that the diagnostic trial discards caller input, never fetches sources, and selects
its short deadline. Provider/model compliance and source-free trial are not live tested.

### Cited evidence in repeated rounds (2026-10-02)

Live trial e8c4e5d014eba5c0 completed in178.85seconds,8requests,one round,
unanimity3/3. Document review61b4ce6ac4ac1f11 hit the900-second shared deadline:
independent phase critical path426.35seconds,proposal144.49seconds,leaving about329
seconds for voting. All three voting attempts ended on the global deadline; these
measurements do not establish a rejected key or isolate the cause of latency.

All three independent reviewers still receive the complete pinned constitution and
selected source files, now with line labels. They must cite path:Lstart-Lend and the
commit for decisive findings. Proposal,voting and final synthesis receive task/context,
the source manifest,findings,proposal/objections,and only the cited original lines with
one context line on each side. Excerpts are copied locally from the pinned originals,
never from a model-generated quotation. Full caller task/context is retained as the
contract; no new network requests or model summarization step is added.

Each citation is bounded to80lines; total excerpt content is bounded to16000characters.
Invalid,out-of-range or over-budget citations are explicitly unavailable; no partial
quotation is silently substituted. If sources exist but no usable citations exist,or
any recognized citation is unavailable,the application denies validated unanimity and
adds an evidence objection. Reviewers must also dissent if omitted context is needed.
This guards availability of cited evidence,not the semantic accuracy/completeness of
model findings. Broader reviews may need another scoped task when evidence exceeds
the budget. The15-minute deadline,three reviewers,three-round cap,and reserve-key
behavior remain. No speed improvement is claimed until the next live document test.

Validation:74 local tests pass,including full independent input/compact later payloads,
unchanged source provenance,explicit evidence budget failures,and rejection of
unanimity based on uncited source claims. Existing repeated dissent and parallelism
checks remain passing.

### Default lead and two subagents (2026-10-02)

Owner authorized replacing repeated council deliberation with a main brain and two
subagents. The default Jobs runner is now run_background/agent_background.coordinate.
Existing nova_council_submit/status/trial names remain compatible but submit and trial
no longer invoke the repeated-voting pipeline. Legacy deliberation code/tests remain
as historical internal helpers; no production submit/trial route selects them.

The main Telegram agent answers simple questions directly and is instructed to
automatically delegate substantive multi-step research/audit tasks using a scoped
task paper. This routing is model guidance,not a deterministic classifier or a hard
ban on native tools. Existing native approvals,owner allowlist,read-only source
snapshot and no-trading/no-write rules remain. Heavy numeric execution is not enabled.

Two read-only workers run concurrently: analysis and independent audit. They receive
the complete pinned selected sources and constitution. Lead synthesis runs once on
available reports and locally copied cited source excerpts. Preferred distinct slots
are2,3 for workers and1 for lead; reserve failover/cooldown still belongs to transport.
At least three configured unique credentials are required. The lead stage is a
separate background completion on behalf of the main coordinator,not a new Telegram
conversation or an unrestricted child-agent session.

Normal worker collection budget360seconds; lead synthesis240seconds. Fixed source-free
trial budgets120seconds each. Budgets exclude queue/source fetch/notification; existing
in-flight network reads may outlive collection. Pending threads are not force-killed:
their results are ignored,own deadlines remain,and late worker telemetry is dropped.
The lead can proceed with one completed worker and explicitly labels partial coverage.
If neither completes,job is blocked without synthesis. Lead failure blocks the task.
No unanimous approval or repeated discussion is claimed. Incomplete source evidence
is also explicitly labeled; these are model findings,not empirical measurement.

Three logical requests maximum (two workers+one lead); reserve attempts can increase
actual API calls. Final owner-only report includes worker completion,logical completed
requests and runtime. Status includes mode and safe per-attempt timings. No intermediate
worker chatter or automatic polling. Trial discards caller task/context/paths as before.
Docker COPY includes agent_background.py. Free hosting,keys and original model pool
are unchanged. Main repository branch is not written.

Validation:80 local tests pass. New coverage verifies concurrent workers/distinct role
slots,one synthesis without voting,partial completion without waiting for pending
thread termination,both-worker failure without synthesis,explicit evidence gaps,and
production job integration sending one final owner result. Live behavior and latency
remain unverified until this deployment is running and a new trial completes.

### Activity-aware long background tasks (2026-10-03)

Owner requested time for work approaching one hour,with stopping based on inactivity.
Live trial5229a958a9e49324 completed workers in35.26/71.20seconds but its lead hit
the previous120-second deadline. Default submit AND fixed trial now share one5400-second
(90-minute) ceiling across worker collection and lead synthesis; separate120/240/360
phase deadlines no longer apply. This permits active work exceeding one hour without
promising that any provider response or heavy numerical execution will succeed.
Source fetching,queue and notification are outside this ceiling; an in-flight read may
add at most its configured socket timeout. Main interactive gateway is unchanged;
long tasks are delegated to the direct background transport.

Direct SSE transport has a300-second inactivity/start timeout and5400-second absolute
stream bound. Nonempty content/reasoning deltas or finish markers update activity;
empty events,role-only deltas and SSE heartbeats do not. Reasoning text is neither
stored nor emitted; only safe slot/phase/elapsed activity telemetry is saved at most
every15seconds. These signals show transport progress,not usefulness of reasoning.
Socket timeout handles absent bytes,while an explicit meaningful-progress clock
handles endless heartbeat traffic. Non-stream JSON fallback remains opaque and uses
the same socket timeout. Existing three-attempt failover and Retry-After cooldown
apply to start/idle failures; a global ceiling does not restart another90-minute window.
Output-token and byte limits remain; extended time does not bypass provider limits.

Completed worker findings are checkpointed immediately,with progress count,in private
mode600 temporary job files. Lead failure retains worker_reports,unavailable_workers
and source manifest for owner status. Main instructions allow answering from saved
findings upon an explicit request without rerunning workers; evidence gaps remain
explicit. No new automatic job/retry endpoint is introduced. These are concise final
worker findings,not internal reasoning transcripts. Render ephemeral reset/redeploy
can still lose records. Status exposes last_activity without raw stream content.
Background error wording now describes the failing stage and preserved findings,
without legacy claims about collective consensus.

Validation:86 local tests pass. Added simulated active streams beyond one hour,
heartbeat-only inactivity,absolute ceiling despite activity,checkpoint-before-second
worker completion,preserved findings when lead fails,one shared deadline for all
phases,and private telemetry/status integration. No real hour-long live run was made.

### Independent leaders with scoped tools and conditional consultation (2026-10-03)

Owner authorized implementing the leader organization: main coordinator,independent
analysis and audit leaders,shared evidence workspace,and consultation when needed.
Live previous mode trialdfecc8fc954a4e8a succeeded with2/2workers,3/3requests,
163.33seconds. That proved single-shot orchestration,not tool-using leader behavior.
Default run_background now selects agent_leaders.coordinate_leaders; legacy one-shot
and voting modules remain internal helpers,not default production dispatch.

Each leader runs up to8model steps on its preferred credential slot. The controller
executes only validated JSON actions: read a manifest path's exact pinned lines
(at most60lines/8000chars),literal search selected sources(max20hits,explicit preview
truncation),publish a concise1200-character finding/question to its own board slot,
or finish with a scoped summary,decision label,blockers and consultation need.
Paths outside the supplied snapshot,arbitrary URLs,shell,writes,credential files,
numeric execution and nested agent creation are unavailable. Leaders can pursue
independent bounded investigations,not unrestricted native-agent sessions.

Initial leader input supplies the complete constitution when present,task/context,
manifest and board. Subsequent steps receive task/context,board and the latest4tool
observations rather than replaying all source files. Leaders retrieve exact excerpts
as needed. The board stores public concise notes and citation references,not private
reasoning. Successful reads publish evidence references visible to both leaders.
Controller copies cited excerpts from the original pinned snapshot for consultation
and final synthesis. This does not guarantee semantic correctness or complete recall
of the initial constitution; absent evidence/context must be reported as uncertainty.

Two complete reports with distinct decision labels,blocking objections or explicit
consultation requests trigger up to2targeted parallel consultation rounds. Peers see
the exact prior reports and evidence; they may keep dissent. Labels are model-supplied,
so equivalent wording can trigger extra consultation and an unreported subtle
disagreement may escape the label test. The lead also assesses the findings. No votes
or forced unanimity. Failed consultation retains previous successful leader findings,
marks partial coverage,and does not loop indefinitely. One leader's failed/exhausted
8-step loop still allows a partial final result; neither completing blocks synthesis.

At most21logical requests:16leader steps+4consultation replies+1lead synthesis.
Actual API attempts can be higher because of bounded reserve failover. Existing90-minute
shared ceiling,300-second meaningful-inactivity rule,private keys and owner-only
notification remain. Checkpoints include worker_reports,unavailable_workers and
workspace; main status exposes the safe board,counts and phase. Records are temporary
and may disappear on redeploy. Header/footer report incomplete coverage,remaining
disagreement,tool steps,actual consultation rounds,logical completions and duration.
The main brain's automatic task-routing instructions remain model guidance.

nova_council_trial now uses an in-memory synthetic DIAGNOSTIC.md fixture rather than
real GitHub/project sources. Caller task/context/paths are ignored. Each leader MUST
complete at least one read/search action before finishing. Fixture citations are
explicitly synthetic,not repository evidence. The same default leader engine then
consults conditionally and synthesizes. This tests controller/model tool orchestration,
not open-ended numeric work or real document alignment. Docker includes agent_leaders.py.

Validation:94 local tests pass,including two parallel tool-using leaders and shared
board,citation provenance,conditional consultation,unresolved dissent at2rounds,
consultation failure preserving findings,literal/scoped tool rejection,bounded endless
publish loops,and full synthetic trial production integration. Live leader mode is
not yet verified. No changes to main,trading strategy,data or paid hosting.

### Explicit consultation schema and safe field diagnostics (2026-10-03)

Live trial29b008249dd9a478 completed both initial leaders,12tool steps,17requests,
365.81seconds. One consultation failed for both leaders with generic ValueError,
retaining their findings. Old records did not capture validation code/location,so
the exact rejected fields cannot be established retrospectively. Inspection found
the consultation prompt referred to the prior schema without reproducing it; the
new request is stateless and that instruction was insufficiently explicit.

Consultation now carries a complete JSON example and bounds for action=finish,
summary,decision,blockers,needs_consultation,and peer_relation. peer_relation is an
explicit comparison of the proposed actions,scope,conditions and next step:
equivalent/different/uncertain. Different labels may still trigger one verification
consultation; they are not silently rewritten by a slug/synonym heuristic. Both
leaders independently confirming equivalence can end label-only disagreement only
when neither has blockers/requests and pinned evidence is available. Explicit
difference/uncertainty remains unresolved even if labels are identical. This is
model assessment of semantic equivalence,not empirical verification or proof.

Final validation raises LeaderContractError with finite safe codes identifying
missing/invalid finish action,summary,decision,blockers,consultation flag or peer
relation. Failed leader/consultation records include reason_code,Arabic fixed
description,error_type,error_slot and file:line:function location from the traceback.
No raw response,traceback locals,provider error body,secret or private reasoning is
recorded in these diagnostics. Malformed JSON retains its existing distinct code.
Transport errors retain safe transport codes; no post-hoc repair of values is made.
Previously successful findings are retained as before. Global time/key/step/tool
limits and no-forced-consensus behavior remain unchanged.

Synthetic trial guidance now says one full read of its4lines normally suffices,
then finish instead of redundant reads/publishing,while allowing real objections.
This is model guidance and does not guarantee fewer calls. No historical result is
reclassified or treated as proof the new schema is live accepted.

Validation:99 local tests pass. Added field-specific/location-safe failure checks,
checkpointed consultation diagnostics,equivalent decisions with distinct labels,
real blockers/missing evidence resisting equivalence,and explicit substantive
disagreement despite equal labels. Live retry is still pending deployment.

### Scope-grounded blockers and explicit findings availability (2026-10-03)

Live trial920ec0bfe2811a93 completed both leaders,5tool steps,12requests,two successful
consultation rounds,426.85seconds,no unavailable_workers. Both peer_relation values
were equivalent,but analysis retained a blocker claiming the actual report texts
were absent. The task concerned presentation templates,not external authored reports.
The application correctly kept the blocker visible; semantic interpretation of scope
needed improvement rather than deleting objections or forcing agreement.

All leader/consultation/synthesis prompts now require blockers to name the missing
input or contradiction and explain which requested decision cannot be made without
it. Limited evidence is distinguished from a blocking gap: absent measurements limit
empirical superiority claims but do not automatically block a qualitative comparison.
Scope may not be widened to invented required artifacts. Genuine task-relevant source
gaps and objections remain and no programmatic blocker filter/override is introduced.

Consultation and synthesis payloads include report_inputs metadata naming included
worker IDs and actual fields:own_report.findings/peer_report.findings or leaders[].findings.
These contain the complete submitted final findings summaries,not external reports
or private reasoning. The instructions explicitly distinguish full_sources_omitted
from absence of these findings and do not require private transcripts for comparing
recommendations. This does not imply unavailable source documents were read.

The fixed synthetic trial task now explicitly compares decision-first/evidence-first
presentation TEMPLATES and audience fit. No pair of authored reports is required.
The fixture supports a limited qualitative comparison,never measured universal
superiority. Existing read/search prerequisite,conditional consultation,key/time/step
limits,evidence validation and source/write safeguards remain. These are model prompt
and input-clarity improvements,not guarantees that a model cannot invent a blocker.

Validation:101 local tests pass. Added evidence that complete leader findings and
availability metadata reach consultation and synthesis,and that an explicitly
requested missing numeric source remains unresolved through the round cap. New live
trial remains pending; prior records/results are unchanged.

### Controller metrics and verified documentation follow-up (2026-10-03)

Live real-source review04ce876a4c6387ce completed both leaders,one consultation,
5tool steps,10requests,382.42seconds against mainf418c95a. Its generated narrative
said runtime was unmeasured despite the service's measured footer. A claimed pair
of source reads can be distinct from5total tool steps; counters need explicit scope.

The lead now receives execution_metrics marked controller_measured,including total
tool steps,successful read/search/publish actions,rejected tool actions,consultation
rounds,and completed model requests before synthesis. Final runtime is explicitly
unavailable until the service adds its measured footer. Instructions require the
generated prose to omit operational counts/durations,leave those to the service,
and distinguish unmeasured financial/project claims from measured service execution.
Leader-supplied estimates are not authoritative counters. Safe action counts are
also exposed in counts. This is prompt guidance,not a guarantee against incorrect
generated prose; the application footer remains definitive.

Direct reading of current main constitution confirmed §8.4 has nine ordered sources
followed by the internal eight-field state card printed only on request. §19 lists
the amendment register but does not add it to the ordered resume list. README work
is prepared separately on agent/readme-state-card-2026-10-03,based on main,with only
README and one journal tick: keep nine items,add the state card,and preserve the
amendment register as an additional reference when needed. No constitution/register
file deletion or modification. This deployment branch does not merge that doc branch.
Owner alone may merge it from Termux under §16; no PR/main push is created by agent.

Validation:102 local tests pass. Added a scenario where fabricated leader estimates
do not replace actual controller counts,with separate read/publish totals and a final
runtime availability flag. README was directly checked for nine numbered items,eight
state fields and unchanged content after the resume section. Live report behavior
after this change is not yet verified.
