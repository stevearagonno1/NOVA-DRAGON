# 🤖 NOVA v5 — ZERO-WAIT QUANT ENGINE (نسخة مسطّحة)

بوت سكالبينج كريبتو (Binance Spot) مبني وفق الخطة المٌقفلة.
**نسخة مسطّحة (flat)**: كل الملفات في مجلد واحد، تُشغَّل مباشرة بـ `python3 main.py` — **بدون استيرادات نسبية، بدون package.**

> ⚠️ يعمل على **Testnet حصراً** حتى اجتياز Backtest واختبار الضغط. لا تداول حي قبل قرارك.

## 📁 الملفات (مجلد واحد مسطّح)

| الملف | الدور |
|---|---|
| `main.py` | نقطة الدخول + الاختبار الذاتي (تُشغَّل مباشرة) |
| `config.py` | الإعدادات + القيم القابلة للمعايرة + قراءة `.env` |
| `indicators.py` | ATR/EMA + **KAMA+Welford** + **Epsilon** + Premium/Discount + z-score |
| `quant.py` | **Swing Death** + **Volatility Filter** |
| `trigger.py` | **Sweep → MSS → FVG** (محفّز الدخول) |
| `nb.py` | **Naive-Bayes** (تدفق أوامر، Diverged=فيتو، self-audit) |
| `scoring.py` | **Six-Factor Score** (0–100 → حجم 0/50/100%) |
| `risk.py` | وقف/هدف/Breakeven/Trailing/Time-stop + **Net-after-fees** |
| `data.py` | **WebSockets** (kline/aggTrade/bookTicker) + عملات ديناميكية |
| `execution.py` | التنفيذ المُوقّع (Binance) + OCO |
| `telegram.py` | **تليجرام Async** (سجل مبوّب + تقرير يومي) |
| `engine.py` | الأوركسترا (كل المهام في حلقة واحدة) |

## 🚀 التشغيل (Termux/كمبيوتر) — من نفس المجلد

```bash
# 1) التبعيات
pip install -r requirements.txt

# 2) الأسرار — انسخ المثال ثم املأ القيم (لا ترفعه أبداً)
cp .env.example .env
nano .env    # ضع مفاتيحك الأربعة فقط

# 3) الاختبار الذاتي (بلا شبكة)
python3 main.py --selftest

# 4) الإقلاع
bash start.sh
# أو مباشرة:
python3 main.py
```

## ⚠️ تأكد أنك داخل مجلد الملفات الصحيح
فتح `main.py` و`requirements.txt` و`.env.example` **في نفس المجلد** قبل التشغيل.
لو نفّذت `python3 main.py` من مجلد `downloads` مباشرة بينما الملفات داخل مجلد فرعي، ستفشل — **`cd` إلى مجلد الملفات أولاً.**

## ✅ ما نُفِّذ (من الخطة المٌقفلة)
- M0 أمان: الأسرار في `.env` فقط.
- M1 WebSockets + CVD + قائمة 50 عملة ديناميكية.
- M2 ماكرو: KAMA+Welford، Epsilon 2.8·ATR، Premium/Discount، Volatility.
- M3 كوانت: Swing Death + Sweep→MSS→FVG.
- M4 Naive-Bayes: Diverged=فيتو، NB≥0.70، self-audit.
- M5 Six-Factor: 0/50/100% (50/70/85).
- M6 تليجرام Async + Net-after-fees في كل رسالة.
- M8 مخاطر: وقف/هدف/Breakeven/Trailing/Time-stop + حاكم.

## ⚠️ أمان
- لا ترفع `.env` في أي مكان.
- جدّد مفاتيح Binance القديمة المكشوفة سابقاً.
