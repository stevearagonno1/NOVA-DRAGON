export BINANCE_ENV='testnet'
export BINANCE_API_KEY='__REDACTED__'
export BINANCE_API_SECRET='__REDACTED__'
export TELEGRAM_BOT_TOKEN="__REDACTED_TG__"
export TELEGRAM_CHAT_ID="7112691967"
export AI_GATE_ENABLED='1'
export GEMINI_API_KEY="__REDACTED__"
export AUTO_TRADE='1'
export TOP_N_SYMBOLS='50'

# ═══ NOVA V6.1 — الهجين: رشاش + قنّاص | الوعي بالرسوم | الحاكم ═══
export SPRAY_ENABLED='1'              # محرك الرشاش (اندفاعة/تدفق/اختراق)
export SPRAY_COOLDOWN_SEC='40'        # تهدئة الرشاش لكل عملة
export SNIPER_RISK_MULT='2.5'         # حجم القنّاص ×2.5
export SNIPER_MAX_NOTIONAL_USD='30'   # سقف مركز القنّاص
export FEE_TAKER_RATE='0.001'         # 0.1% للجهة — المحاسبة صافية بعد الرسوم
export BREAKEVEN_TRIGGER_PCT='0.30'   # تفعيل التعادل
export BREAKEVEN_LOCK_PCT='0.25'      # قفل فوق تكلفة التداول (0.20% رسوم + 0.05% انزلاق)
export SCALE_OUT_ENABLED='1'          # بيع نصف المركز عند +0.40%
export FLOW_REV_EXIT='1'              # خروج فوري عند انعكاس التدفق
export GOV_MAX_STREAK='3'             # 3 خسائر متتالية ⇒ توقف 10 دقائق
export GOV_HOURLY_LOSS_USD='2.0'      # −2$/ساعة ⇒ توقف 30 دقيقة
export GOV_DAILY_LOSS_USD='5.0'       # −5$/يوم ⇒ توقف حتى الغد
export ORDER_BUDGET_MAX='40'          # ميزانية أوامر/10ث (حد Binance = 50)

# ═══ V6.2 — الوضع الظلي (بحث بأدلة) + دخول الصانع (Maker) ═══
export SHADOW_ENABLED='1'            # قياس أفضلية كل زناد بصفقة افتراضية
export SHADOW_ONLY='0'               # اجعلها 1 لإيقاف كل الأوامر الحقيقية أثناء البحث
export SHADOW_NOTIONAL_USD='12'      # حجم الصفقة الظلية الموحد للمقارنة العادلة
export MAKER_ENTRIES='1'             # الدخول LIMIT_MAKER عند أفضل شراء (تكسب السبريد)
export MAKER_TTL_SEC='8'             # مهلة انتظار تنفيذ الصانع ثم الإلغاء (≤10)

# 1. إزالة الأزرار الإنجليزية السفلية القديمة
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
     -d chat_id="${TELEGRAM_CHAT_ID}" \
     -d text="⏳ جاري تحديث واجهة البوت..." \
     -d reply_markup='{"remove_keyboard":true}' > /dev/null

# 2. تصميم وإرسال الأزرار الشفافة الأنيقة
INLINE_KEYBOARD='{"inline_keyboard":[[{"text":"📊 الحالة","callback_data":"/status"},{"text":"🌍 السياق","callback_data":"/context"}],[{"text":"⏸ إيقاف","callback_data":"/pause"},{"text":"▶ استئناف","callback_data":"/resume"}],[{"text":"🧯 إلغاء الأوامر","callback_data":"/cancelall"},{"text":"🆘 تصفية","callback_data":"/panic"}]]}'

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
     -d chat_id="${TELEGRAM_CHAT_ID}" \
     -d text="✅ بوت NOVA يعمل الآن في الخلفية. اختر الإجراء المطلوب:" \
     -d reply_markup="${INLINE_KEYBOARD}" > /dev/null

python check.py
python NOVA.py

