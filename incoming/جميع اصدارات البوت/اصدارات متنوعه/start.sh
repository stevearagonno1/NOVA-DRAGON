#!/bin/bash

# إعدادات Binance
export BINANCE_ENV='testnet'
export BINANCE_API_KEY='__REDACTED__'
export BINANCE_API_SECRET='__REDACTED__'


# إعدادات Telegram
export TELEGRAM_BOT_TOKEN="__REDACTED_TG__"
export TELEGRAM_CHAT_ID="7112691967"
 
# إعدادات الذكاء الاصطناعي (اختياري)
export AI_GATE_ENABLED='1'
export GEMINI_API_KEY="__REDACTED__"

# تشغيل البوت

export AUTO_TRADE='1'
export TOP_N_SYMBOLS='50'

python NOVA.py
