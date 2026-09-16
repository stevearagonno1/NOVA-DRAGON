#!/bin/bash
# ═══ NOVA v5 ZERO-WAIT QUANT — مشغّل سكالبينج (نسخة مسطّحة، بلا أسرار في الكود) ═══
# الأسرار تُقرأ من ملف `.env` (M0: الأمان)
cd "$(dirname "$0")"

# 1) فحص أن ملف الأسرار موجود
if [ ! -f ".env" ]; then
  echo "❌ ملف .env غير موجود. انسخ .env.example إلى .env واملأ قيمك."
  exit 1
fi

# 2) الاختبار الذاتي (بلا شبكة — يتحقق من سلامة المنطق)
echo "🧪 اختبار ذاتي قبل الإقلاع..."
python3 main.py --selftest || { echo "❌ الاختبار فشل — لن يعمل البوت"; exit 1; }

# 3) إقلاع NOVA v5
echo "🚀 إقلاع NOVA v5 ZERO-WAIT QUANT (Testnet)..."
python3 main.py
