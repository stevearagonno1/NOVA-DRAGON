# 🤖 NOVA v5 — ZERO-WAIT QUANT ENGINE

بوت سكالبينج كريبتو (Binance Spot) مبني وفق **الخطة المٌقفلة** — مدرك لاسكالبينج اللحظي بفلاتر ماكرو وذكاء كمي وإدارة مخاطر صارمة وتقارير تليجرام تفاعلية، كل ذلك **غير حابس (Async)** ليعمل على Termux/Android.

> ⚠️ يعمل **على Testnet حصراً** حتى اجتياز Backtest واختبار الضغط. لا تداول حي قبل أن تقرر ذلك صراحةً.

---

## 🧩 البنية (ملف لكل طبقة)

| الملف | الدور |
|---|---|
| `config.py` | التحميل + كل القيم القابلة للمعايرة (CONFIG) |
| `indicators.py` | ATR/EMA/SMA + **KAMA+Welford** + **Epsilon** + Premium/Discount + z-score |
| `quant.py` | **Swing Death** + **Volatility Filter** |
| `trigger.py` | **Sweep → MSS → FVG** (محفّز الدخول) |
| `nb.py` | **Naive-Bayes** (تدفق أوامر، Diverged=فيتو، self-audit) |
| `scoring.py` | **Six-Factor Score** (0–100 → حجم 0/50/100%) |
| `risk.py` | وقف/هدف/Breakeven/Trailing/Time-stop + **Net-after-fees** |
| `data.py` | **WebSockets** (kline/aggTrade/bookTicker) + قائمة عملات ديناميكية |
| `execution.py` | التنفيذ المُوقّع (Binance) + OCO |
| `telegram.py` | **تليجرام Async** (سجل مبوّب + تقرير يومي) |
| `engine.py` | الأوركسترا (كل المهام في حلقة واحدة) |
| `main.py` | نقطة الدخول + الاختبار الذاتي |

---

## 🚀 التشغيل (Termux)

```bash
# 1) التبعيات
pip install -r requirements.txt

# 2) الأسرار — انسخ المثال ثم املأ القيم (لا ترفعه أبداً)
cp .env.example .env
#    → ضع مفاتيح Binance الجديدة + تليجرام في .env فقط

# 3) الاختبار الذاتي (بلا شبكة)
python3 -m nova_bot.main --selftest

# 4) الإقلاع (اقرأ الأسرار من .env تلقائياً)
bash start.sh
```

---

## ✅ ماذا نفّذنا من الخطة المٌقفلة

- **M0 أمان:** كل الأسرار في `.env` منفصل — لا أسرار في أي سكربت/ملف.
- **M1 WebSockets:** `kline_1m` + `aggTrade` + `bookTicker`، لا REST في حلقة الفحص، وCVD دقيقة.
- **M2 ماكرو:** `KAMA(power=2)+Welford`، `Epsilon(2.8·ATR)`، `Premium/Discount`، `Volatility Filter`.
- **M3 كوانت:** `Swing Death`، محفّز `Sweep→MSS→FVG` بإزاحة `0.6·ATR`.
- **M4 Naive-Bayes:** تدريب O(1)، فئة `Diverged`=فيتو مانع، `NB≥0.70`، self-audit.
- **M5 Scoring:** `Six-Factor 0–100` → حجم `0/50/100%` (حدود 50/70/85).
- **M6 تليجرام:** `aiohttp` Async، سجل مبوّب، تقرير يومي، و**Net-after-fees في كل رسالة**.
- **M8 مخاطر:** وقف/هدف/Breakeven/Trailing/Time-stop + حاكم العملات (من v4).

## 🧪 التحقق
- `--selftest` يفحص 16 فحصاً منطقياً **بلا شبكة** (كل المكوّنات) — لاحظناه ناجحاً.
- كل الوحدات تُستورد نظيفة.

---

## ⚠️ تنبيه أمان مهم (كلي)
مفاتيح Binance التي كانت مكشوفة في `start_zero.sh` السابق **يجب إلغاؤها وتجديدها** في لوحة المنصة الآن، ثم وضع الجديدة في `.env` فقط.
