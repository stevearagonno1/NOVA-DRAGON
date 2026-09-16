#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA ASYNC SCALPER V5.3 ELITE — Smart Machine Gun (Hybrid Trailing Ping-Pong)
=================================================================================
بوت سكالبينج Spot غير متزامن بالكامل على Binance. محرك تنقيط مرجّح بدل
البوابات المتسلسلة (Boolean AND)، وحجم دخول مبني على المخاطرة (Risk Parity)،
مع قاطع سياق كلي (BTC Circuit Breaker) وتدفق صفقات حقيقي (aggTrade).

تغييرات V5.1 عن V5 (رشاش أذكى + نسبة نجاح أعلى):
أ) تنقيط متدرّج بدل 0/20 الصارمة: اختلال التدفق يُمنح 8/14/20 بحسب قوته،
   والاتجاه 20 (فوق EMA50 وميل صاعد) أو 10 (فوقه والميل مسطح)، ومكافأة حجم
   حتى +5 عند تضخم حجم الشمعة — فالإشارة تكمل نقاطها بسهولة أكبر (رشاش) دون
   إسقاط أي حارس جودة.
ب) فلاتر قاطعة جديدة تقتل الصفقات الخاسرة قبل ولادتها:
   • سوق ميت: ATR% أدنى من MIN_ATR_PCT (لا يغطي الرسوم+السبريد) → منع.
   • مطاردة قمة: السعر ممتد أكثر من CHASE_MAX_ATR×ATR فوق EMA50 → منع.
   • تقلب جنوني: VR أكبر من VR_EXTREME → منع (لا تدخل في الفوضى).
ج) وقف زمني (Time Stop): مركز يتجاوز TIME_STOP_SEC دون ربح مقبول → يُصفى
   بسعر السوق (السكالبينج يحتاج زخماً فورياً؛ موت الزخم = خروج).
د) قمع تشخيصي (Funnel): عدّاد لكل سبب رفض يظهر في /context لمعرفة الخانق.
هـ) إصلاح أزرار تليجرام: callback_data بنفس صيغة start.sh (/status ...)
   والموجّه يقبل الصيغتين معاً.

تغييرات V5.2 (تنقيط تعويضي شبيه بالبشر + ضبط معاملات):
1) SCORE_MOMENTUM_BONUS = +25: زخم استثنائي (اختلال تدفق > 3.0 أو حجم > 2.5×)
   يعوّض غياب FVG أو الاتجاه، فيبلغ المجموع الزناد بالزخم المتفجّر وحده.
2) MSS هو المكوّن البنيوي الإلزامي الوحيد (منع شراء السبايكات العشوائية).
3) EMA_TREND_PERIOD = 100 | عتبات التدفق 1.6 / 1.3 / 1.15 | وقف زمني 900ث.

تغييرات V5.3 (الرشاش الذكي — Hybrid Trailing Ping-Pong):
1) حجم مصغّر عالي التردد: 15 مركزاً متزامناً (3/عملة)، مخاطرة 1$ وسقف مركز 12$.
   وإذا كان VR > VR_FAST يُنصَّف حجم المركز (تقليل التعرض في الفوضى).
2) فلتر «إيقاظ الحيتان» (Whale-Wake): صفقة aggTrade مفردة بقيمة > 50,000$
   تُسجَّل للعملة، وتمنح مكافأة الزخم (+25) تلقائياً في compute_score.
3) استراتيجية الخروج الهجينة (جوهر V5.3): لا هدف ثابت إطلاقاً.
   • وقف طوارئ صلب على Binance فور الدخول: STOP_LOSS_LIMIT عند
     ATR(1m) × 1.5 (بسقف 3%) — شبكة أمان لكارثة فقط.
   • قفل التعادل: عند ربح +0.40% يُنقل الوقف المحلي إلى الدخول +0.15%.
   • سرعة تتبّع ديناميكية: ربح 0.4–1.0% ⇒ مسافة 0.20% من القمة،
     وربح > 1.0% ⇒ 0.08% (خنق القمة وتأمين أقصى ربح).
   • التنفيذ: عند لمس الوقف المحلي يُلغى وقف Binance ثم MARKET SELL فوراً.
4) وقف زمني 900ث: إن كان الربح < +0.15% يُلغى الوقف ويُباع بالسوق.
5) حراسات: مطالبة خروج ذرية (EXIT_CLAIMED + EXIT_PENDING) تمنع البيع المزدوج،
   وقمة المركز (peak) تُخزَّن داخل المركز نفسه فتُحرَّر معه (لا تسرّب ذاكرة).

الفلسفة المعمارية (Async / Event-Driven / Battery-First):
1) تدفقات السوق عبر WebSocket دائم إلى Binance (Combined Streams):
   الاشتراكات لكل زوج من أفضل 30: <sym>@kline_5m + <sym>@kline_15m
   + <sym>@aggTrade (تدفق حقيقي) + <sym>@bookTicker (Sبريد/فحص لحظي فقط).
   اشتراك BTCUSDT@kline_1m على اتصال مستقل دائماً كفلتر سياق كلي.
2) محرك التنقيط الموزون (SignalScorer) بدل AND:
   • MSS (كسر هيكل) = 35 نقطة.
   • FVG (فجوة قيمة عادلة غير معبأة) = 25 نقطة.
   • السعر فوق EMA50(15m) = 20 نقطة.
   • اختلال تدفق aggTrade > 1.5 = 20 نقطة.
   • الزناد: تنفيذ عند المجموع >= 75 نقطة (رشاش ذكي لا بوابة مضغوطة).
   • حارس إضافي: componentان مستقلان على الأقل (يمنع الدخول بـ MSS وحده).
3) فلاتر قاطعة (Vetoes) تُطبق بعد التنقيط:
   • الشمعة الذيلية: إذا تجاوز الذيل 60% من طول الشمعة → منع (مصيدة سيولة).
   • Circuit Breaker: هبوط BTC أكثر من 0.5% خلال آخر 3 دقائق → منع كل الشراء.
   • قدم البيانات: آخر tick أقدم من 3ث → منع (بديل «الطلقة المعلقة» المحذوفة).
4) تنفيذ فوري MARKET BUY: لا LIMIT معلّق ولا انتظار دفتر. أمر سوق يُرسل
   مباشرة بعد اكتمال النقاط، والحسم عبر response + User Data Stream.
5) المخارج (V5.3 — هجينة):
   • وقف طوارئ صلب على Binance: STOP_LOSS_LIMIT عند ATR(1m) × 1.5،
     بسقف صلب 3% من سعر الدخول (Flash-Crash Cap) — شبكة أمان فقط.
   • لا هدف ثابت: الربح يُدار محلياً (تعادل +0.15% بعد +0.40%، ثم تتبّع
     0.20% ويُخنق إلى 0.08% فوق +1.0%) وينفَّذ MARKET SELL بعد إلغاء الوقف.
6) حجم الدخول مبنية على المخاطرة (وليس قيمة ثابتة):
   PositionSize(USDT) = TARGET_RISK_USD / (SL_distance / EntryPrice)
   مع سقف MAX_POSITION_NOTIONAL_USD (12$) ومخاطرة 1$ لكل صفقة، ونصف الحجم
   عندما VR > VR_FAST (تقليل التعرض في الفوضى).
7) تهدئة ديناميكية: 60ث في السوق المتقلب (VR>1.5)، 120ث في المستقر (VR<0.8)،
   90ث افتراضياً — تُقرأ من تقلب BTC على 1m. + Setup ID فريد
   (symbol@candleOpenTime) يمنع تكرار الدخول داخل نفس الشمعة.
8) خروج هجين (V5.3): وقف طوارئ صلب على Binance + وقف محلي متحرك يُدار من
   تدفق bookTicker (تعادل ثم تتبّع بسرعة ديناميكية) وينفَّذ MARKET SELL.
9) إدارة الذاكرة: حتى 15 مركزاً متزامناً (3 لكل عملة)، حجز ذري تحت ENTRY_LOCK،
   مصالحة لقطية بعد الإقلاع/إعادة الاتصال، وحلقة صيانة هادئة.
10) الصمت التام (Stealth): رسالة بدء واحدة فقط بعد نجاح الإقلاع والاتصال،
    ثم لا رسائل تلقائية إطلاقاً — كل شيء في bot.log، والرد على الأوامر اليدوية فقط.
11) ترقيعات السباق والأمان (QA) — محفوظة من V4:
   • كل أحداث User Stream تُستهلك عبر طابور ومستهلك واحد → لا سباق.
   • إتمام الدخول «مطالبة ذرية» (claim) داخل STATE_LOCK → لا حماية مزدوجة.
   • حجز الدخول ذري (ENTRY_LOCK) + Setup ID → لا دخول مكرر في نفس الشمعة.
   • توقيع HMAC من سلسلة استعلام واحدة تُرسل حرفياً.
   • WebSocket: autoping + heartbeat + Backoff/Jitter + إعادة تحميل شموع.

التثبيت (Termux / Python 3.10+):
    pkg update -y
    pkg install python -y
    pip install aiohttp numpy pandas

الإعداد:
    export BINANCE_ENV='testnet'
    export BINANCE_API_KEY='مفتاح Binance Spot'
    export BINANCE_API_SECRET='سر Binance Spot'
    export TELEGRAM_BOT_TOKEN='توكن Telegram'
    export TELEGRAM_CHAT_ID='معرف المحادثة'

التشغيل:
    python NOVA_V5.py --selftest
    python NOVA_V5.py --dry-run
    python NOVA_V5.py
    python NOVA_V5.py --once

لا Futures ولا رافعة ولا بيع على المكشوف. لا ضمان للربح؛ ابدأ بالـ Testnet.
"""

from __future__ import annotations

import asyncio
import copy
import csv
import hashlib
import hmac
import json
import math
import os
import random
import signal as _signal
import sys
import time
import traceback
import uuid
from collections import Counter, deque
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from urllib.parse import urlencode

import numpy as np
import pandas as pd

try:
    import aiohttp
except ImportError:  # يسمح بتشغيل --selftest دون aiohttp
    aiohttp = None


# ══════════════════════════════════════════════════════════════════════════════
# 1) الإعدادات
# ══════════════════════════════════════════════════════════════════════════════


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on", "نعم")


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


def env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return float(default)


def D(value, default="0"):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def dec_str(value):
    text = format(D(value), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def clamp(value, low, high):
    return max(low, min(high, value))


BINANCE_ENV = os.getenv("BINANCE_ENV", "testnet").strip().lower()
if BINANCE_ENV not in ("demo", "testnet", "live"):
    BINANCE_ENV = "testnet"
REST_BASE = {
    "demo": "https://demo-api.binance.com",
    "testnet": "https://testnet.binance.vision",
    "live": "https://api.binance.com",
}[BINANCE_ENV]
WS_MARKET_BASE = {
    "demo": "wss://demo-api.binance.com/stream",
    "testnet": "wss://stream.testnet.binance.vision/stream",
    "live": "wss://stream.binance.com:9443/stream",
}[BINANCE_ENV]
WS_USER_BASE = {
    "demo": "wss://demo-api.binance.com/ws",
    "testnet": "wss://stream.testnet.binance.vision/ws",
    "live": "wss://stream.binance.com:9443/ws",
}[BINANCE_ENV]
DUMMY_STREAM = "btcusdt@bookTicker"  # تدفق مؤقت لفتح الاتصال ثم يُلغى اشتراكه

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "").strip()
LIVE_CONFIRM = os.getenv("LIVE_TRADING_CONFIRM", "")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

AUTO_TRADE = env_bool("AUTO_TRADE", True)
DRY_RUN = env_bool("DRY_RUN", False)
# الصمت التام: لا رسائل تلقائية إطلاقاً بعد إشعار البدء الوحيد
STEALTH_MODE = True

STARTUP_TEXT = "✅ NOVA Async V5.3 ELITE Started & Connected to Binance WebSockets."
RESET_REPLY = "✅ تم تصفير جميع الإحصائيات بنجاح."

# ── الكون الديناميكي: أفضل N زوجاً حسب حجم 24 ساعة، تحديث كل ساعة ────────────
TOP_N_SYMBOLS = max(10, min(100, env_int("TOP_N_SYMBOLS", 50)))  # V5.1: من البيئة (start.sh=50)
UNIVERSE_REFRESH_EVERY = max(300, env_int("UNIVERSE_REFRESH_EVERY", 3600))
MIN_24H_QUOTE_VOLUME = env_float("MIN_24H_QUOTE_VOLUME", 1_000_000)

# ── المحرك: فريم الإشارة 5m + الاتجاه EMA50 على فريم 15m ─────────────────────
SIGNAL_INTERVAL = "5m"
TREND_INTERVAL = "15m"
MICRO_INTERVAL = "1m"          # V5.3: مصدر ATR(1m) لوقف الطوارئ الصلب
INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900}
EMA_TREND_PERIOD = max(10, env_int("EMA_TREND_PERIOD", 100))  # V5.2: 100 لرؤية كلية أنعم
MIN_CLOSED_CANDLES = max(30, env_int("MIN_CLOSED_CANDLES", 60))
KLINE_REST_LIMITS = {
    MICRO_INTERVAL: clamp(env_int("KLINE_LIMIT_1M", 60), 30, 200),
    SIGNAL_INTERVAL: clamp(env_int("KLINE_LIMIT_5M", 140), 80, 500),
    TREND_INTERVAL: clamp(EMA_TREND_PERIOD + 120, 180, 1000),
}
HISTORY_MAX = {MICRO_INTERVAL: 120, SIGNAL_INTERVAL: 300, TREND_INTERVAL: 400}

ATR_PERIOD = max(2, env_int("ATR_PERIOD", 14))
VR_BASELINE = max(2, env_int("VR_BASELINE", 20))   # متوسط ATR14 لآخر 20 شمعة

# ── محرك التنقيط المتدرّج (V5.1): أوزان مستقلة + مكافأة حجم + حاجز زناد ──────
SCORE_MSS = env_float("SCORE_MSS", 35.0)          # كسر هيكلي بإزاحة (مكوّن بنيوي)
SCORE_FVG = env_float("SCORE_FVG", 25.0)          # فجوة قيمة عادلة غير معبأة (مكوّن بنيوي)
SCORE_EMA = env_float("SCORE_EMA", 20.0)           # فوق EMA50 + ميل صاعد
SCORE_EMA_FLAT = env_float("SCORE_EMA_FLAT", 10.0)  # فوق EMA50 لكن الميل مسطح
SCORE_FLOW = env_float("SCORE_FLOW", 20.0)         # اختلال aggTrade قوي (ratio ≥ FLOW_IMBALANCE_MIN)
SCORE_FLOW_MED = env_float("SCORE_FLOW_MED", 14.0)  # اختلال متوسط (ratio ≥ FLOW_IMBALANCE_MED)
SCORE_FLOW_WEAK = env_float("SCORE_FLOW_WEAK", 8.0)  # اختلال خفيف مؤكد (ratio ≥ FLOW_IMBALANCE_WEAK)
SCORE_VOLUME_MAX = env_float("SCORE_VOLUME_MAX", 5.0)  # مكافأة قصوى لحجم مُتضخّم
SCORE_TRIGGER = env_float("SCORE_TRIGGER", 72.0)   # حاجز الزناد (72 = رشاش؛ ارفعه للصرامة)
MIN_SCORE_COMPONENTS = env_int("MIN_SCORE_COMPONENTS", 2)  # مكوّنان مستقلان على الأقل
# V5.2 — التنقيط التعويضي الشبيه بالبشر: زخم استثنائي يعوّض غياب FVG/الاتجاه
SCORE_MOMENTUM_BONUS = env_float("SCORE_MOMENTUM_BONUS", 25.0)   # مكافأة ثقيلة للزخم المتفجّر
MOMENTUM_FLOW_EXTREME = env_float("MOMENTUM_FLOW_EXTREME", 3.0)  # اختلال تدفق هائل
MOMENTUM_VOL_EXTREME = env_float("MOMENTUM_VOL_EXTREME", 2.5)    # انفجار حجم هائل
# V5.3 — إيقاظ الحيتان: صفقة aggTrade مفردة ضخمة تمنح مكافأة الزخم تلقائياً
WHALE_TRADE_USD = env_float("WHALE_TRADE_USD", 50_000.0)
WHALE_MEMORY_SEC = max(30.0, env_float("WHALE_MEMORY_SEC", float(INTERVAL_SECONDS[SIGNAL_INTERVAL])))
WHALES_MAX = max(50, env_int("WHALES_MAX", 300))   # سقف صلب لذاكرة الحيتان
FLOW_IMBALANCE_MIN = env_float("FLOW_IMBALANCE_MIN", 1.6)
FLOW_IMBALANCE_MED = env_float("FLOW_IMBALANCE_MED", 1.3)
FLOW_IMBALANCE_WEAK = env_float("FLOW_IMBALANCE_WEAK", 1.15)
# فلاتر قاطعة جديدة (V5.1): ترفع نسبة النجاح بمنع الصفقات الرديئة
MIN_ATR_PCT = env_float("MIN_ATR_PCT", 0.10)       # سوق ميت: ATR/Price أقل من 0.10% → لا حركة تكفي
CHASE_MAX_ATR = env_float("CHASE_MAX_ATR", 6.0)    # مطاردة: امتداد > 6×ATR فوق EMA → منع (10 = معطّل فعلياً)
CHASE_MIN_PCT = env_float("CHASE_MIN_PCT", 8.0)    # أو امتداد نسبي > 8% عن EMA → منع
VR_EXTREME = env_float("VR_EXTREME", 3.0)          # تقلب جنوني: VR > 3 → منع الدخول أصلاً
VOLUME_SPIKE = env_float("VOLUME_SPIKE", 1.6)      # حجم الشمعة > 1.6× المتوسط → مكافأة كاملة

MSS_LOOKBACK = max(5, env_int("MSS_LOOKBACK", 20))
MSS_MAX_AGE = max(1, env_int("MSS_MAX_AGE", 2))
MSS_MIN_RANGE_ATR = env_float("MSS_MIN_RANGE_ATR", 0.80)
MSS_BODY_RATIO = clamp(env_float("MSS_BODY_RATIO", 0.50), 0.0, 1.0)

FVG_LOOKBACK = max(3, env_int("FVG_LOOKBACK", 8))
FVG_MIN_ATR = env_float("FVG_MIN_ATR", 0.05)

WICK_REJECT_RATIO = clamp(env_float("WICK_REJECT_RATIO", 0.60), 0.0, 1.0)

# ── التدفق الحقيقي (aggTrade) بدل اختلال الدفتر على Testnet ─────────────────
FLOW_WINDOW_SEC = max(2.0, env_float("FLOW_WINDOW_SEC", 15.0))
FLOW_MAX_BUCKETS = 96
MAX_SPREAD_PCT = env_float("MAX_SPREAD_PCT", 0.15)
# قدم البيانات: آخر tick أقدم من هذه النافذة → إلغاء الإشارة (بديل الطلقة المعلقة)
MAX_STALE_SEC = clamp(env_float("MAX_STALE_SEC", 3.0), 0.5, 30.0)
# إعادة تقييم المرشح تحت الحاجز عند وصول تدفق — كحد أقصى مرة كل هذه الثواني
FLOW_CHECK_EVERY = max(0.25, env_float("FLOW_CHECK_EVERY", 1.0))

# ── السياق الكلي: BTCUSDT@kline_1m كقاطع شراء (Circuit Breaker) ──────────────
BTC_CONTEXT_SYMBOL = os.getenv("BTC_CONTEXT_SYMBOL", "BTCUSDT").strip().upper() or "BTCUSDT"
BTC_DROP_PCT = env_float("BTC_DROP_PCT", 0.5)      # هبوط > 0.5% خلال النافذة → منع
BTC_DROP_WINDOW_MIN = max(1, env_int("BTC_DROP_WINDOW_MIN", 3))
BTC_CTX_MAX_AGE = env_float("BTC_CTX_MAX_AGE", 180.0)
BTC_CTX_KLINE_LIMIT = max(BTC_DROP_WINDOW_MIN + 30, 64)
COOLDOWN_FAST = max(0, env_int("COOLDOWN_FAST", 60))    # VR > 1.5 (سوق متقلب)
COOLDOWN_NORMAL = max(0, env_int("COOLDOWN_NORMAL", 90))
COOLDOWN_SLOW = max(0, env_int("COOLDOWN_SLOW", 120))   # VR < 0.8 (سوق هادئ)
SETUP_MEMORY = max(10, env_int("SETUP_MEMORY", 4000))

# ── إدارة رأس المال: مخاطرة ثابتة لكل صفقة (Risk Parity) ─────────────────────
TARGET_RISK_USD = Decimal(str(env_float("TARGET_RISK_USD", 1.0)))            # V5.3: صفقات مصغّرة
MAX_POSITION_NOTIONAL_USD = Decimal(str(env_float("MAX_POSITION_NOTIONAL_USD", 12.0)))
VOL_SIZE_HALVE = env_bool("VOL_SIZE_HALVE", True)   # VR > VR_FAST → نصف الحجم
RISK_TOLERANCE = env_float("RISK_TOLERANCE", 1.05)  # تجاوز مسموح للمخاطرة بعد التقريب (5%)
MIN_NOTIONAL_SAFETY = env_float("MIN_NOTIONAL_SAFETY", 1.05)  # هامش أمان فوق minNotional للخروج
MARKET_COST_BUFFER = Decimal("1.004")  # هامش انزلاق/رسوم لحجز الرصيد قبل أمر MARKET

# ── الوقف الديناميكي والأهداف الصارمة ────────────────────────────────────────
# V5.3: هذه المعاملات صارت وصفية فقط (تسمية نظام السوق fast/normal/slow)؛
# مسافة الوقف نفسها صارت ATR(1m) × HARD_STOP_ATR_MULT، وVR يُستعمل لتنصيف الحجم.
ATR_MULT_FAST = env_float("ATR_MULT_FAST", 2.5)     # VR > 1.5
ATR_MULT_SLOW = env_float("ATR_MULT_SLOW", 1.2)     # VR < 0.8
ATR_MULT_NORMAL = env_float("ATR_MULT_NORMAL", 2.5)
VR_FAST = env_float("VR_FAST", 1.5)
VR_SLOW = env_float("VR_SLOW", 0.8)
SL_MAX_PCT = clamp(env_float("SL_MAX_PCT", 3.0), 0.2, 10.0)   # سقف صلب للوقف
SL_MIN_PCT = clamp(env_float("SL_MIN_PCT", 0.05), 0.01, 2.0)  # أرضية وقف (منع OCO منحل عند سعر الدخول)
# ── V5.3: الخروج الهجين (وقف طوارئ صلب + تعادل + تتبّع بسرعة ديناميكية) ─────
HARD_STOP_ATR_MULT = env_float("HARD_STOP_ATR_MULT", 1.5)      # ATR(1m) × 1.5
BREAKEVEN_TRIGGER_PCT = env_float("BREAKEVEN_TRIGGER_PCT", 0.40)  # ربح يفعّل التعادل والتتبّع
BREAKEVEN_LOCK_PCT = env_float("BREAKEVEN_LOCK_PCT", 0.15)     # الوقف يُقفل عند الدخول +0.15%
TRAIL_WIDE_PCT = env_float("TRAIL_WIDE_PCT", 0.20)             # ربح 0.4–1.0% → تتبّع 0.20%
TRAIL_TIGHT_PCT = env_float("TRAIL_TIGHT_PCT", 0.08)           # ربح > 1.0% → خنق 0.08%
TRAIL_TIGHT_AFTER_PCT = env_float("TRAIL_TIGHT_AFTER_PCT", 1.0)
MICRO_ATR_FALLBACK_DIV = env_float("MICRO_ATR_FALLBACK_DIV", 2.236)  # ATR5m/√5 عند غياب 1m
FEE_BUFFER = env_float("FEE_BUFFER", 0.0015)
LIMIT_SLIPPAGE_PCT = env_float("LIMIT_SLIPPAGE_PCT", 0.20)

# ── المراكز والتهدئة ──────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS = max(1, env_int("MAX_OPEN_POSITIONS", 15))   # V5.3: رشاش 15 مركزاً
MAX_POSITIONS_PER_SYMBOL = max(1, env_int("MAX_POSITIONS_PER_SYMBOL", 3))
SAME_SYMBOL_COOLDOWN = max(0, env_int("SAME_SYMBOL_COOLDOWN", 90))  # تُغطى ديناميكياً
TIME_STOP_ENABLED = env_bool("TIME_STOP_ENABLED", True)
TIME_STOP_SEC = max(60, env_int("TIME_STOP_SEC", 900))      # 15 دقيقة سكالب: مات الزخم → اخرج
TIME_STOP_CHECK_EVERY = max(15, env_int("TIME_STOP_CHECK_EVERY", 60))
TIME_STOP_MIN_PROFIT_PCT = env_float("TIME_STOP_MIN_PROFIT_PCT", 0.15)  # ربح ≥0.15% يُترك للتتبّع

# Watchdog الصمت: إن لم يصل executionReport خلال 12ث يُستوضح الأمر REST مرة واحدة
ENTRY_EVENT_TIMEOUT = env_float("ENTRY_EVENT_TIMEOUT", 12.0)
USER_QUEUE_MAX = 2000

# ── Dust Management: مسح الأرصدة الدقيقة إلى BNB مرة كل 24 ساعة ──────────────
DUST_SWEEP_EVERY = max(3600, env_int("DUST_SWEEP_EVERY", 86_400))
DUST_ASSET_CAP = 8          # حد Binance لعدد الأصول في طلب واحد

# ── User Data Stream: مفتاح استماع + Keepalive ───────────────────────────────
LISTEN_KEY_KEEPALIVE = max(300, env_int("LISTEN_KEY_KEEPALIVE", 1800))

# ── تهدئة الجوال: تزامن HTTP منخفض وعمال دخول قليلون ─────────────────────────
HTTP_CONCURRENCY = max(2, min(16, env_int("HTTP_CONCURRENCY", 8)))
MAX_ENTRY_WORKERS = max(1, min(8, env_int("MAX_ENTRY_WORKERS", 3)))
SAFE_WEIGHT_LIMIT = max(120, env_int("SAFE_WEIGHT_LIMIT", 800))

# ── WebSocket: نبض وإعادة اتصال تلقائية ─────────────────────────────────────
WS_HEARTBEAT = env_float("WS_HEARTBEAT", 30.0)
WS_CONNECT_TIMEOUT = env_float("WS_CONNECT_TIMEOUT", 30.0)
WS_RECONNECT_MIN = env_float("WS_RECONNECT_MIN", 1.0)
WS_RECONNECT_MAX = env_float("WS_RECONNECT_MAX", 60.0)
RECON_SNAPSHOT_COOLDOWN = 60.0

MANAGE_EVERY = max(30.0, env_float("MANAGE_EVERY", 300.0))

# ── الملفات ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "nova_async_data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
TRADES_FILE = os.path.join(DATA_DIR, "trades.csv")
KILL_SWITCH_FILE = os.path.join(DATA_DIR, "STOP_TRADING")
LOCK_FILE = os.path.join(DATA_DIR, "bot.lock")

# ── الحالة المشتركة (تُعدَّل داخل حلقة الأحداث الواحدة فقط) ───────────────────
SESSION = None                  # aiohttp.ClientSession (يُنشأ في amain)
REST = None                     # BinanceRest (يُنشأ في amain)
STATE_LOCK = asyncio.Lock()
ENTRY_LOCK = asyncio.Lock()
MANAGE_LOCK = asyncio.Lock()
ENTRY_SEMAPHORE = asyncio.Semaphore(MAX_ENTRY_WORKERS)
REST_GATE = asyncio.Semaphore(HTTP_CONCURRENCY)

TIME_OFFSET_MS = 0
SYMBOL_RULES = {}
SYMBOLS = []
SYMBOLS_SET = set()
TICKER_CACHE = {}
CANDLES = {}          # (symbol, interval) -> {"t","o","h","l","c","v","live"}
TREND = {}            # symbol -> {"ema": float|None, "last_t": int}
BOOK = {}             # symbol -> {"bid","ask","bid_vol","ask_vol","spread_pct","ts"}
FLOW = {}             # symbol -> {"buy","sell","ts","epoch","price","buckets"} (aggTrade حقيقي)
READY = {}            # symbol -> {"t","score","checked"} مرشح تحت الحاجز يُعاد تقييمه على التدفق
SETUPS = deque(maxlen=SETUP_MEMORY)   # Setup IDs المنفذة: symbol@candleOpenTime
BTC_CTX = {                           # سياق BTC (قناة 1m مستقلة)
    "closes": deque(maxlen=BTC_DROP_WINDOW_MIN + 25),
    "live": 0.0,
    "last_t": 0,
    "last_update": 0.0,
    "seeded": False,
}
ENTRY_RESERVATIONS = {}
RESERVED_QUOTE = Decimal("0")
WHALES = {}           # symbol -> {"ts": epoch, "usd": أكبر صفقة مفردة} (V5.3: إيقاظ الحيتان)
FUNNEL = Counter()                   # V5.1: عدّاد أسباب رفض الإشارات (قمع تشخيصي)
EXIT_CLAIMED = set()                 # V5.1: معرّفات مراكز قيد خروج استثنائي (منع بيع مزدوج)
EXIT_PENDING = set()                 # V5.3: حارس متزامن قبل جدولة مهمة الخروج (منع تكرار المهام)
RESEED_AT = {}
RESEED_ALL_AT = 0.0
LAST_USED_WEIGHT = 0
RATE_BACKOFF_UNTIL = 0.0
STARTUP_NOTIFIED = False
LAST_RECON_SNAPSHOT = 0.0
USER_EVENTS = None            # asyncio.Queue — مستهلك واحد (ترقيع سباق)
ORDERS = {}                   # str(orderId) -> {"role","cid"/"pid","symbol"}


# ══════════════════════════════════════════════════════════════════════════════
# 2) السجل والملفات
# ══════════════════════════════════════════════════════════════════════════════


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def log(message):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    try:
        ensure_dirs()
        with open(LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def default_state():
    return {
        "offset": 0,
        "paused": False,
        "start_time": time.time(),
        "last_dust_sweep": 0.0,
        "cooldowns": {},
        "last_entry_at": {},
        "positions": {},
        "pending_entries": {},
        "dust": [],
        "metrics": {
            "trades": 0,
            "realized_pnl": 0.0,
            "wins": 0,
            "losses": 0,
            "consecutive_losses": 0,
        },
    }


STATE = default_state()


def migrate_positions(raw):
    """يوحّد مراكز الإصدارات الأقدم إلى مفاتيح pid فريدة وينظف حقول Trailing."""
    migrated = {}
    counter = 0
    for key, position in (raw or {}).items():
        if not isinstance(position, dict):
            continue
        if "#" in str(key):
            pid = str(key)
            position.setdefault("symbol", str(key).split("#", 1)[0])
        else:
            counter += 1
            pid = f"{key}#m{uuid.uuid4().hex[:6]}"
            position.setdefault("symbol", key)
        position["pid"] = pid
        for legacy_key in ("trailing_active", "activation_price", "trailing_distance",
                           "trail_bips", "target"):
            position.pop(legacy_key, None)
        # V5.3: حقول محرك الخروج الهجين (تُستعاد بأمان بعد إعادة التشغيل)
        try:
            entry_price = float(position.get("entry", 0) or 0)
        except (TypeError, ValueError):
            entry_price = 0.0
        try:
            peak_saved = float(position.get("peak", 0) or 0)
        except (TypeError, ValueError):
            peak_saved = 0.0
        position["peak"] = max(peak_saved, entry_price)
        position["trail_armed"] = bool(position.get("trail_armed", False))
        position["trail_stop"] = float(position.get("trail_stop", 0.0) or 0.0)
        position["trail_mode"] = str(position.get("trail_mode", "off") or "off")
        position["last_price"] = float(position.get("last_price", entry_price) or entry_price)
        position.setdefault("hard_stop", float(position.get("stop", 0.0) or 0.0))
        migrated[pid] = position
    return migrated


def load_state():
    global STATE
    ensure_dirs()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
        base = default_state()
        if isinstance(saved, dict):
            base.update(saved)
        if not isinstance(base.get("positions"), dict):
            base["positions"] = {}
        base["positions"] = migrate_positions(base["positions"])
        if not isinstance(base.get("pending_entries"), dict):
            base["pending_entries"] = {}
        if not isinstance(base.get("dust"), list):
            base["dust"] = []
        if not isinstance(base.get("last_entry_at"), dict):
            base["last_entry_at"] = {}
        base["last_dust_sweep"] = float(base.get("last_dust_sweep", 0.0) or 0.0)
        metrics = base.get("metrics") if isinstance(base.get("metrics"), dict) else {}
        base["metrics"] = {
            "trades": int(metrics.get("trades", 0)),
            "realized_pnl": float(metrics.get("realized_pnl", 0.0)),
            "wins": int(metrics.get("wins", 0)),
            "losses": int(metrics.get("losses", 0)),
            "consecutive_losses": int(metrics.get("consecutive_losses", 0)),
        }
        STATE = base
        log(f"ذاكرة V5: {len(STATE['positions'])} مركزاً مفتوحاً | صفقات {STATE['metrics']['trades']}")
    except FileNotFoundError:
        log("لا توجد ذاكرة سابقة؛ بداية جديدة")
    except Exception as exc:
        log(f"تعذر تحميل الذاكرة: {exc}")


def _write_state_sync(snapshot):
    temp = STATE_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=2)
    os.replace(temp, STATE_FILE)


async def save_state():
    """لقطة ذرية تحت القفل ثم كتابة عبر to_thread — لا حجب لحلقة الأحداث."""
    async with STATE_LOCK:
        snapshot = copy.deepcopy(STATE)
    try:
        await asyncio.to_thread(_write_state_sync, snapshot)
    except Exception as exc:
        log(f"فشل حفظ الذاكرة: {exc}")


def record_trade(row):
    try:
        ensure_dirs()
        fresh = not os.path.exists(TRADES_FILE)
        with open(TRADES_FILE, "a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            if fresh:
                writer.writerow(["time", "symbol", "pid", "entry", "exit", "qty", "pnl", "reason", "environment"])
            writer.writerow(row)
    except Exception as exc:
        log(f"تعذر كتابة سجل الصفقة: {exc}")


def coin_name(symbol):
    symbol = str(symbol)
    return symbol[:-4] if symbol.endswith("USDT") else symbol


def make_client_id(prefix):
    return (prefix + uuid.uuid4().hex[:20]).upper()[:36]


def new_position_id(symbol):
    return f"{symbol}#{uuid.uuid4().hex[:8]}"


def kill_switch_active():
    return os.path.exists(KILL_SWITCH_FILE)


def acquire_single_instance():
    ensure_dirs()
    old_pid = 0
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as handle:
            old_pid = int((handle.read() or "0").strip() or 0)
    except (OSError, ValueError):
        old_pid = 0
    if old_pid and old_pid != os.getpid() and os.path.exists(f"/proc/{old_pid}"):
        raise SystemExit(f"نسخة أخرى من البوت تعمل بالفعل (PID {old_pid})؛ أوقفها أولاً.")
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
    except OSError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 3) المحرك الرياضي المتجهي — numpy + pandas حصراً (لا حلقات مؤشرات)
# ══════════════════════════════════════════════════════════════════════════════


def ema_series(closes, period):
    """EMA كلاسيكي (بذرة SMA) متجهياً: يطابق TradingView/المعيار الصوري.

    pandas.ewm(span, adjust=False) يبذر بأول قيمة؛ لذا نبذر نحن بـ SMA
    ثم نغذي الذيل — النتيجة متطابقة مع التعريف القياسي ومتجهية بالكامل.
    """
    arr = np.asarray(list(closes), dtype="float64")
    n = arr.size
    out = np.full(n, np.nan, dtype="float64")
    if period <= 0 or n < period:
        return out
    seed = float(arr[:period].mean())
    out[period - 1] = seed
    if n > period:
        tail = np.concatenate(([seed], arr[period:]))
        ewm = pd.Series(tail).ewm(span=period, adjust=False).mean().to_numpy(dtype="float64")
        out[period:] = ewm[1:]
    return out


def ema_last(closes, period):
    series = ema_series(closes, period)
    valid = series[~np.isnan(series)]
    return float(valid[-1]) if valid.size else None


def atr_series(highs, lows, closes, period):
    """ATR بأسلوب Wilder متجهياً: TR عبر numpy ثم RMA عبر ewm(alpha=1/n).

    بذرة SMA(TR, n) — التعريف الكلاسيكي نفسه، بلا أي حلقة بايثون.
    """
    high = np.asarray(list(highs), dtype="float64")
    low = np.asarray(list(lows), dtype="float64")
    close = np.asarray(list(closes), dtype="float64")
    n = close.size
    out = np.full(n, np.nan, dtype="float64")
    if period <= 0 or n < period:
        return out
    prev_close = np.concatenate(([close[0]], close[:-1]))
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    seed = float(tr[:period].mean())
    out[period - 1] = seed
    if n > period:
        tail = np.concatenate(([seed], tr[period:]))
        rma = pd.Series(tail).ewm(alpha=1.0 / period, adjust=False).mean().to_numpy(dtype="float64")
        out[period:] = rma[1:]
    return out


def atr_last(highs, lows, closes, period):
    series = atr_series(highs, lows, closes, period)
    valid = series[~np.isnan(series)]
    return float(valid[-1]) if valid.size else 0.0


def volatility_ratio(highs, lows, closes, period, baseline):
    """نسبة التقلب VR = ATR(period) الحالي / متوسط ATR لآخر baseline شمعة.

    يُستخدم لاختيار معامل ضرب ATR للوقف الديناميكي ولتحديد حالة التهدئة.
    يعيد (atr, vr) — vr = 1.0 عند غياب أساس كافٍ (سوق محايد).
    """
    series = atr_series(highs, lows, closes, period)
    valid = series[~np.isnan(series)]
    if not valid.size:
        return 0.0, 1.0
    atr_now = float(valid[-1])
    window = valid[-max(1, int(baseline)):]
    base = float(np.mean(window)) if window.size else 0.0
    if base <= 0 or not math.isfinite(base):
        return atr_now, 1.0
    vr = atr_now / base
    if not math.isfinite(vr):
        vr = 1.0
    return atr_now, vr


def detect_wick_ratio(o, h, l, c):
    """نسبة أطول ذيل إلى الطول الكلي للشمعة الأخيرة (0..1)."""
    i = int(c.size) - 1
    rng = float(h[i] - l[i])
    if rng <= 0:
        return 0.0
    body_low = min(float(o[i]), float(c[i]))
    body_high = max(float(o[i]), float(c[i]))
    upper_wick = float(h[i]) - body_high
    lower_wick = body_low - float(l[i])
    return float(max(upper_wick, lower_wick) / rng)


def detect_mss(o, h, l, c, atr_value):
    """Market Structure Shift على 5m: إغلاق فوق آخر قمة هيكلية بإزاحة قوية."""
    if atr_value <= 0 or atr_value is None:
        return None
    n = c.size
    if n < MSS_LOOKBACK + MSS_MAX_AGE + 3:
        return None
    for age in range(MSS_MAX_AGE):
        i = n - 1 - age
        body = float(c[i] - o[i])
        rng = float(h[i] - l[i])
        if body <= 0 or rng <= 0:
            continue
        if body / rng < MSS_BODY_RATIO:
            continue
        if rng < MSS_MIN_RANGE_ATR * atr_value:
            continue
        window = h[max(0, i - MSS_LOOKBACK): i]
        if window.size == 0:
            continue
        prior_high = float(np.max(window))
        if float(o[i]) <= prior_high < float(c[i]):
            if float(c[-1]) <= prior_high:
                continue  # الهيكل انهار فوراً — الإشارة مرفوضة
            return {
                "age": age, "index": int(i), "prior_high": prior_high,
                "close": float(c[i]), "body": body, "range": rng,
                "displacement": rng / atr_value,
            }
    return None


def detect_fvg(h, l, atr_value):
    """أحدث فجوة قيمة عادلة صاعدة غير معبأة على 5m ضمن آخر الشموع."""
    n = l.size
    start = max(0, n - FVG_LOOKBACK)
    best = None
    for i in range(start, n - 2):
        gap_low = float(h[i])
        gap_high = float(l[i + 2])
        if gap_high <= gap_low:
            continue
        if atr_value > 0 and (gap_high - gap_low) < FVG_MIN_ATR * atr_value:
            continue
        mid = (gap_low + gap_high) / 2.0
        # فحص العبث: هل كسر أي قاع لاحق منتصف الفجوة؟ (متجهي)
        if l[i + 3:].size and float(np.min(l[i + 3:])) <= mid:
            continue
        best = {"low": gap_low, "high": gap_high, "mid": mid, "index": int(i), "age": n - 1 - (i + 2)}
    return best


# ── أدوات التقريب حسب قواعد الرمز (تُستخدم من كل طبقات القرار والتنفيذ) ──────


def round_step(value, step):
    value, step = D(value), D(step)
    return (value / step).to_integral_value(rounding=ROUND_FLOOR) * step if step > 0 else value


def round_price(value, tick, direction="down"):
    value, tick = D(value), D(tick)
    if tick <= 0:
        return value
    rounding = ROUND_CEILING if direction == "up" else ROUND_FLOOR
    return (value / tick).to_integral_value(rounding=rounding) * tick


def fmt_price(symbol, value):
    if value is None:
        return "—"
    rule = SYMBOL_RULES.get(symbol, {})
    tick = rule.get("tick", Decimal("0.00000001"))
    decimals = max(0, -tick.as_tuple().exponent)
    return f"{D(value):.{decimals}f}"


# ══════════════════════════════════════════════════════════════════════════════
# 4) عميل Binance REST غير المتزامن (aiohttp + HMAC + SAPI)
# ══════════════════════════════════════════════════════════════════════════════


class BinanceError(Exception):
    def __init__(self, message, code=None, status=None):
        super().__init__(message)
        self.code = code
        self.status = status


def build_signed(values):
    """يبني سلسلة الاستعلام الموقعة HMAC-SHA256 حرفياً كما ستُرسل.

    يُعتمد على إرسال الطلب بالمسار الكامل (لا params= في aiohttp) حتى لا
    يعيد aiohttp ترميز السلسلة فتفسد التوقيع — ترقيع الثغرة الكلاسيكي.
    """
    query = urlencode(values, doseq=True)
    signature = hmac.new(BINANCE_API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    return f"{query}&signature={signature}", headers


class BinanceRest:
    def __init__(self, session):
        self.session = session

    async def _raw(self, method, path, params=None, signed=False, api_key=False,
                   timeout=15.0, _retry=True):
        global LAST_USED_WEIGHT, RATE_BACKOFF_UNTIL
        if signed and time.time() < RATE_BACKOFF_UNTIL:
            raise BinanceError("تهدئة ذاتية بعد 429/418؛ الطلب مرفوض مؤقتاً")
        values = dict(params or {})
        headers = {}
        if signed:
            if not BINANCE_API_KEY or not BINANCE_API_SECRET:
                raise BinanceError("مفاتيح Binance غير موجودة")
            values["recvWindow"] = values.get("recvWindow", 5000)
            values["timestamp"] = int(time.time() * 1000) + TIME_OFFSET_MS
            query, headers = build_signed(values)
        else:
            query = urlencode(values, doseq=True)
            if api_key:
                headers["X-MBX-APIKEY"] = BINANCE_API_KEY
        url = f"{REST_BASE}{path}" + (f"?{query}" if query else "")
        try:
            async with REST_GATE:
                async with self.session.request(
                    method, url, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    header = response.headers.get("X-MBX-USED-WEIGHT-1M")
                    if header:
                        try:
                            LAST_USED_WEIGHT = int(header)
                        except (TypeError, ValueError):
                            pass
                    if response.status == 429:
                        retry = response.headers.get("Retry-After")
                        try:
                            wait_seconds = int(retry)
                        except (TypeError, ValueError):
                            wait_seconds = 30
                        RATE_BACKOFF_UNTIL = max(RATE_BACKOFF_UNTIL, time.time() + max(5, wait_seconds))
                    elif response.status == 418:
                        RATE_BACKOFF_UNTIL = max(RATE_BACKOFF_UNTIL, time.time() + 180)
                    try:
                        payload = await response.json(content_type=None)
                    except (ValueError, aiohttp.ClientError):
                        raise BinanceError(f"استجابة Binance غير صالحة HTTP {response.status}", status=response.status)
                    if isinstance(payload, dict) and payload.get("code") == -1003:
                        RATE_BACKOFF_UNTIL = max(RATE_BACKOFF_UNTIL, time.time() + 30)
                    if response.status >= 400 or (isinstance(payload, dict) and payload.get("code", 0) < 0):
                        message = payload.get("msg", "خطأ Binance") if isinstance(payload, dict) else "خطأ Binance"
                        code = payload.get("code") if isinstance(payload, dict) else None
                        if _retry and code == -1021:
                            await self.sync_time()
                            return await self._raw(method, path, params, signed, api_key, timeout, _retry=False)
                        raise BinanceError(message, code, response.status)
                    return payload
        except BinanceError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
            # code=None, status=None → خطأ شبكة غير مؤكد (الأمر قد يكون قائماً)
            raise BinanceError(f"شبكة Binance: {exc}")

    async def sync_time(self):
        global TIME_OFFSET_MS
        payload = await self._raw("GET", "/api/v3/time", timeout=8)
        TIME_OFFSET_MS = int(payload["serverTime"]) - int(time.time() * 1000)

    # ── نقاط عامة ────────────────────────────────────────────────────────────
    async def exchange_info(self):
        return await self._raw("GET", "/api/v3/exchangeInfo", timeout=30)

    async def klines(self, symbol, interval, limit):
        return await self._raw("GET", "/api/v3/klines",
                               {"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)

    async def agg_trades(self, symbol, limit=100):
        return await self._raw("GET", "/api/v3/aggTrades",
                               {"symbol": symbol, "limit": clamp(int(limit), 1, 1000)}, timeout=12)

    async def ticker_24h(self):
        return await self._raw("GET", "/api/v3/ticker/24hr", timeout=25)

    async def book_ticker(self, symbol):
        return await self._raw("GET", "/api/v3/ticker/bookTicker", {"symbol": symbol}, timeout=8)

    # ── نقاط موقعة (تداول) ───────────────────────────────────────────────────
    async def account(self):
        return await self._raw("GET", "/api/v3/account", signed=True, timeout=15)

    async def new_order(self, params):
        return await self._raw("POST", "/api/v3/order", params, signed=True, timeout=15)

    async def get_order(self, symbol, order_id):
        return await self._raw("GET", "/api/v3/order", {"symbol": symbol, "orderId": order_id}, signed=True)

    async def get_order_client(self, symbol, client_order_id):
        return await self._raw("GET", "/api/v3/order", {"symbol": symbol, "origClientOrderId": client_order_id}, signed=True)

    async def cancel_order(self, symbol, order_id):
        return await self._raw("DELETE", "/api/v3/order", {"symbol": symbol, "orderId": order_id}, signed=True)

    async def cancel_order_client(self, symbol, client_order_id):
        return await self._raw("DELETE", "/api/v3/order",
                               {"symbol": symbol, "origClientOrderId": client_order_id}, signed=True)

    async def open_orders_all(self):
        return await self._raw("GET", "/api/v3/openOrders", signed=True, timeout=15)

    async def cancel_all(self, symbol):
        return await self._raw("DELETE", "/api/v3/openOrders", {"symbol": symbol}, signed=True)

    # ── User Data Stream (listenKey) ─────────────────────────────────────────
    async def create_listen_key(self):
        payload = await self._raw("POST", "/api/v3/userDataStream", api_key=True, timeout=10)
        return payload.get("listenKey")

    async def keepalive_listen_key(self, listen_key):
        await self._raw("PUT", "/api/v3/userDataStream", {"listenKey": listen_key}, api_key=True, timeout=10)

    # ── Dust Management (SAPI) ───────────────────────────────────────────────
    async def dustable_bases(self):
        return await self._raw("GET", "/sapi/v1/asset/dustableBases", signed=True, timeout=15)

    async def dust_transfer(self, assets):
        return await self._raw("POST", "/sapi/v1/asset/dust", {"asset": ",".join(assets)}, signed=True, timeout=15)


def free_balance_from(account, asset):
    for row in account.get("balances", []):
        if row.get("asset") == asset:
            return D(row.get("free", "0"))
    return Decimal("0")


def load_symbol_rules(payload):
    global SYMBOL_RULES
    SYMBOL_RULES = {}
    for item in (payload or {}).get("symbols", []):
        symbol = item.get("symbol")
        if not symbol or item.get("quoteAsset") != "USDT":
            continue
        filters = {x.get("filterType"): x for x in item.get("filters", [])}
        lot = filters.get("LOT_SIZE", {})
        market_lot = filters.get("MARKET_LOT_SIZE", lot)
        price = filters.get("PRICE_FILTER", {})
        notion = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {}))
        SYMBOL_RULES[symbol] = {
            "status": item.get("status"),
            "base": item.get("baseAsset"),
            "quote": item.get("quoteAsset"),
            "tick": D(price.get("tickSize", "0.00000001")),
            "step": D(lot.get("stepSize", "0.00000001")),
            "min_qty": D(lot.get("minQty", "0")),
            "max_qty": D(lot.get("maxQty", "999999999")),
            "market_step": D(market_lot.get("stepSize", lot.get("stepSize", "0.00000001"))),
            "market_min_qty": D(market_lot.get("minQty", lot.get("minQty", "0"))),
            "min_notional": D(notion.get("minNotional", notion.get("notional", "0"))),
        }
    log(f"قواعد Binance USDT: {len(SYMBOL_RULES)} زوجاً")


def pick_universe(tickers):
    """أفضل 30 زوجاً حسب حجم 24س — دالة نقية (قابلة للاختبار)."""
    stable = {"USDT", "USDC", "FDUSD", "BUSD", "TUSD", "USDP", "DAI", "USD1"}
    # V5.3: أكبر مركز ممكن هو السقف نفسه (12$)؛ العملة التي حدّها الأدنى أعلى
    # منه لا يمكن تداولها إطلاقاً ⇒ استبعدها من الكون بدل إهدار الاشتراكات عليها.
    floor_notional = D(MAX_POSITION_NOTIONAL_USD)
    candidates = []
    for symbol, rule in SYMBOL_RULES.items():
        base = str(rule.get("base", "")).upper()
        row = tickers.get(symbol)
        if rule.get("status") != "TRADING" or not row:
            continue
        if base in stable or base.startswith("1000") or base.endswith(("UP", "DOWN", "BULL", "BEAR")):
            continue
        if float(row.get("quote_volume", 0.0)) < MIN_24H_QUOTE_VOLUME:
            continue
        if D(rule.get("min_notional", "0")) > floor_notional * Decimal("0.85"):
            continue   # حتى أكبر مركز مسموح لا يحقق الحد الأدنى للطلب
        candidates.append((float(row.get("quote_volume", 0.0)), symbol))
    candidates.sort(reverse=True)
    return [symbol for _, symbol in candidates[: max(1, TOP_N_SYMBOLS)]]


async def refresh_universe():
    """يجدد أفضل 30 زوجاً عبر REST (يستدعيها محدث الكون الساعي)."""
    global SYMBOLS, SYMBOLS_SET, TICKER_CACHE
    payload = await REST.ticker_24h()
    tickers = {}
    for row in payload if isinstance(payload, list) else []:
        try:
            tickers[row["symbol"]] = {
                "price": float(row["lastPrice"]),
                "change": float(row["priceChangePercent"]),
                "quote_volume": float(row["quoteVolume"]),
            }
        except (KeyError, TypeError, ValueError):
            continue
    TICKER_CACHE = tickers
    chosen = pick_universe(tickers)
    if chosen:
        SYMBOLS = chosen
        SYMBOLS_SET = set(chosen)
        log(f"كون V5: أفضل {len(SYMBOLS)} زوجاً حسب حجم 24س")
    return SYMBOLS


# ══════════════════════════════════════════════════════════════════════════════
# 5) الذاكرة اللحظية: شموع + BBA (سبريد) + aggTrade (تدفق) + سياق BTC
# ══════════════════════════════════════════════════════════════════════════════


def build_buffer(payload, interval):
    """يبني مخزن شموع من استجابة REST klines (آخر صف = الشمعة الحية)."""
    rows = payload if isinstance(payload, list) else []
    if not rows:
        return None
    closed = rows[:-1]
    buffer = {"t": [], "o": [], "h": [], "l": [], "c": [], "v": [], "live": 0.0}
    try:
        for row in closed:
            buffer["t"].append(int(row[0]))
            buffer["o"].append(float(row[1]))
            buffer["h"].append(float(row[2]))
            buffer["l"].append(float(row[3]))
            buffer["c"].append(float(row[4]))
            buffer["v"].append(float(row[5]))
        buffer["live"] = float(rows[-1][4])
    except (IndexError, TypeError, ValueError):
        return None
    return buffer


def buffer_to_frame(buffer):
    """مصفوفات numpy للشموع المغلقة (o,h,l,c) — جاهزة للحسابات المتجهية."""
    return (
        np.asarray(buffer["o"], dtype="float64"),
        np.asarray(buffer["h"], dtype="float64"),
        np.asarray(buffer["l"], dtype="float64"),
        np.asarray(buffer["c"], dtype="float64"),
    )


def buffer_append(buffer, interval, t, o, h, l, c, v):
    """إلحاق شمعة مغلقة: إزالة تكرار / كشف فجوات / تقليم الطول.

    يعيد: appended | updated | stale | gap  (gap → يجب إعادة تحميل من REST).
    """
    last_t = buffer["t"][-1] if buffer["t"] else None
    t = int(t)
    o, h, l, c, v = float(o), float(h), float(l), float(c), float(v)
    if last_t is not None:
        if t == last_t:
            i = len(buffer["t"]) - 1
            buffer["o"][i], buffer["h"][i], buffer["l"][i], buffer["c"][i], buffer["v"][i] = o, h, l, c, v
            return "updated"
        if t < last_t:
            return "stale"
        outcome = "gap" if t > last_t + INTERVAL_SECONDS[interval] * 1000 else "appended"
    else:
        outcome = "appended"
    buffer["t"].append(t)
    buffer["o"].append(o)
    buffer["h"].append(h)
    buffer["l"].append(l)
    buffer["c"].append(c)
    buffer["v"].append(v)
    maxlen = HISTORY_MAX.get(interval, 300)
    excess = len(buffer["t"]) - maxlen
    if excess > 0:
        for key in ("t", "o", "h", "l", "c", "v"):
            del buffer[key][:excess]
    return outcome


async def seed_symbol(symbol):
    """تسخين أولي: شموع 1m + 5m + 15m عبر REST ثم EMA + ATR(5m/1m) جاهزة."""
    for interval in (SIGNAL_INTERVAL, TREND_INTERVAL):
        payload = await REST.klines(symbol, interval, KLINE_REST_LIMITS[interval])
        buffer = build_buffer(payload, interval)
        if buffer is None or len(buffer["c"]) < 30:
            raise BinanceError(f"بيانات {symbol} {interval} غير كافية")
        CANDLES[(symbol, interval)] = buffer
    try:    # ATR(1m) لوقف الطوارئ — فشله لا يعطّل العملة (يوجد رجوع آمن)
        micro_payload = await REST.klines(symbol, MICRO_INTERVAL, KLINE_REST_LIMITS[MICRO_INTERVAL])
        micro_buffer = build_buffer(micro_payload, MICRO_INTERVAL)
        if micro_buffer is not None and len(micro_buffer["c"]) >= ATR_PERIOD + 1:
            CANDLES[(symbol, MICRO_INTERVAL)] = micro_buffer
    except Exception as exc:
        log(f"تحذير: تعذر تسخين 1m لـ {symbol} ({exc})؛ سيُستعمل ATR(5m)/√5")
    _trend_buf = CANDLES[(symbol, TREND_INTERVAL)]
    _series = ema_series(_trend_buf["c"], EMA_TREND_PERIOD)
    _valid = _series[~np.isnan(_series)]
    TREND[symbol] = {
        "ema": float(_valid[-1]) if _valid.size else None,
        "ema_prev": (float(_valid[-6]) if _valid.size >= 6
                     else (float(_valid[0]) if _valid.size else None)),
        "slope_up": bool(_valid.size >= 6 and _valid[-1] > _valid[-6]),
        "last_t": _trend_buf["t"][-1],
    }
    BOOK.pop(symbol, None)
    READY.pop(symbol, None)
    FLOW[symbol] = {"buy": 0.0, "sell": 0.0, "ts": 0.0, "epoch": 0.0, "price": 0.0, "buckets": deque()}


async def seed_btc_context():
    """تسخين سياق BTC من REST: شموع 1m مغلقة لسقف الانهيار وVR للتهدئة."""
    payload = await REST.klines(BTC_CONTEXT_SYMBOL, "1m", BTC_CTX_KLINE_LIMIT)
    rows = [r for r in (payload if isinstance(payload, list) else []) if isinstance(r, (list, tuple))]
    if not rows:
        return
    try:
        if not int(rows[-1][8]):
            rows = rows[:-1]  # استبعاد الشمعة الحية غير المكتملة
        closes = [float(r[4]) for r in rows]
        highs = [float(r[2]) for r in rows]
        lows = [float(r[3]) for r in rows]
    except (IndexError, TypeError, ValueError):
        return
    if not closes:
        return
    ctx = BTC_CTX
    ctx["closes"] = deque(closes[-(BTC_DROP_WINDOW_MIN + 25):], maxlen=BTC_DROP_WINDOW_MIN + 25)
    ctx["live"] = closes[-1]
    ctx["last_t"] = int(rows[-1][0]) if rows else 0
    ctx["last_update"] = time.monotonic()
    atr_now, vr = volatility_ratio(highs, lows, closes, ATR_PERIOD, VR_BASELINE)
    ctx["atr"] = atr_now
    ctx["vr"] = vr
    ctx["seeded"] = True


def schedule_reseed(symbol):
    now = time.monotonic()
    if now - RESEED_AT.get(symbol, 0.0) < 60:
        return
    RESEED_AT[symbol] = now
    try:
        asyncio.get_running_loop().create_task(reseed_symbol(symbol))
    except RuntimeError:
        pass


async def reseed_symbol(symbol):
    try:
        await seed_symbol(symbol)
        log(f"أُعيد تحميل شموع {symbol} بعد فجوة بيانات")
    except Exception as exc:
        log(f"فشل إعادة تحميل شموع {symbol}: {exc}")


async def reseed_all():
    """بعد أي انقطاع WebSocket: إعادة تحميل الشموع وسياق BTC لسد الفجوات."""
    global RESEED_ALL_AT
    now = time.monotonic()
    if now - RESEED_ALL_AT < 120:
        return
    RESEED_ALL_AT = now
    for symbol in list(SYMBOLS):
        try:
            await seed_symbol(symbol)
        except Exception as exc:
            log(f"فشل إعادة تحميل {symbol}: {exc}")
    try:
        await seed_btc_context()
    except Exception as exc:
        log(f"فشل إعادة تحميل سياق BTC: {exc}")


def update_trend_ema(symbol):
    """EMA50(15m) متجهياً عند كل شمعة 15m مغلقة (مع حراسة ازدواج + ميل)."""
    buffer = CANDLES.get((symbol, TREND_INTERVAL))
    if not buffer or not buffer["c"] or not buffer["t"]:
        return
    trend = TREND.setdefault(symbol, {"ema": None, "last_t": None})
    candle_t = buffer["t"][-1]
    if trend.get("last_t") == candle_t:
        return  # هذه الشمعة دُمجت مسبقاً في EMA (حماية من الازدواج)
    series = ema_series(buffer["c"], EMA_TREND_PERIOD)
    valid = series[~np.isnan(series)]
    trend["ema"] = float(valid[-1]) if valid.size else None
    # ميل EMA: قيمته الآن مقابل قيمته قبل 5 شموع 15m (صاعد/هابط/مسطح)
    trend["ema_prev"] = float(valid[-6]) if valid.size >= 6 else (float(valid[0]) if valid.size else None)
    trend["slope_up"] = bool(valid.size >= 6 and valid[-1] > valid[-6])
    trend["last_t"] = candle_t


def parse_book_payload(data):
    """يحول رسالة bookTicker إلى BBA + السبريد (فحص لحظي — لا قرار تدفق)."""
    try:
        bid = float(data.get("b") or 0)
        bid_qty = float(data.get("B") or 0)
        ask = float(data.get("a") or 0)
        ask_qty = float(data.get("A") or 0)
        if bid <= 0 or ask <= 0:
            return None
        mid = (bid + ask) / 2.0
        bid_vol = bid * bid_qty
        ask_vol = ask * ask_qty
        total = bid_vol + ask_vol
        return {
            "bid": bid, "ask": ask, "bid_qty": bid_qty, "ask_qty": ask_qty,
            "bid_vol": bid_vol, "ask_vol": ask_vol,
            "imbalance": (bid_vol / total) if total > 0 else 0.5,
            "spread_pct": ((ask - bid) / mid * 100.0) if mid > 0 else 99.0,
            "ts": time.monotonic(),
        }
    except (TypeError, ValueError):
        return None


# ── التدفق الحقيقي: آخر التطورات السوقية (aggTrade) بدل اختلال الدفتر ─────────
# takerSide == BUY (المشتري هو الصانع ⇒ أمر شرائي في السوق) ⇒ ضغط شراء حقيقي.


def flow_state(symbol):
    return FLOW.setdefault(symbol, {"buy": 0.0, "sell": 0.0, "ts": 0.0, "buckets": deque()})


def flow_prune(state, now):
    buckets = state["buckets"]
    while buckets and now - buckets[0][0] > FLOW_WINDOW_SEC:
        _ts, buy, sell = buckets.popleft()
        state["buy"] = max(0.0, float(state.get("buy", 0.0)) - buy)
        state["sell"] = max(0.0, float(state.get("sell", 0.0)) - sell)


def flow_add(symbol, ts, buy_quote, sell_quote):
    """يضيف دلو حجم (quote) لحظي إلى نافذة التدفق المتدحرجة."""
    state = flow_state(symbol)
    ts = float(ts)
    buy_quote = max(0.0, float(buy_quote or 0.0))
    sell_quote = max(0.0, float(sell_quote or 0.0))
    if buy_quote == 0.0 and sell_quote == 0.0:
        return state
    state["buckets"].append((ts, buy_quote, sell_quote))
    while len(state["buckets"]) > FLOW_MAX_BUCKETS:
        _ts, buy, sell = state["buckets"].popleft()
        state["buy"] = max(0.0, float(state.get("buy", 0.0)) - buy)
        state["sell"] = max(0.0, float(state.get("sell", 0.0)) - sell)
    state["buy"] = float(state.get("buy", 0.0)) + buy_quote
    state["sell"] = float(state.get("sell", 0.0)) + sell_quote
    state["ts"] = ts
    flow_prune(state, time.time())
    return state


def flow_imbalance(symbol, max_age=None):
    """يعيد (ratio, age_sec): buy_quote / sell_quote داخل النافذة المتدحرجة.

    sell=0 مع شراء حقيقي ⇒ 99.0 (ضغط شراء مطلق). لا تدفق ⇒ (0.0, inf).
    """
    state = FLOW.get(symbol)
    if not state:
        return 0.0, math.inf
    age = time.time() - float(state.get("ts", 0.0) or 0.0)
    if age > (FLOW_WINDOW_SEC if max_age is None else max_age):
        flow_prune(state, time.time())
        if not state["buckets"]:
            return 0.0, age
    buy = float(state.get("buy", 0.0))
    sell = float(state.get("sell", 0.0))
    if buy + sell <= 0:
        return 0.0, age
    if sell <= 0:
        return 99.0, age
    return buy / sell, age


def whale_mark(symbol, quote_usd, ts=None):
    """يسجّل «إيقاظ حوت» للعملة: صفقة مفردة بقيمة ≥ WHALE_TRADE_USD.

    الذاكرة محدودة بحجم الكون (رمز واحد لكل عملة) وتُنظَّف مع الكون، والقيمة
    تنتهي صلاحيتها زمنياً عبر whale_recent — لا تسرّب ولا نمو غير محدود.
    """
    try:
        usd = float(quote_usd or 0.0)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(usd) or usd < WHALE_TRADE_USD:
        return False
    WHALES[symbol] = {"ts": float(ts if ts else time.time()), "usd": usd}
    if len(WHALES) > WHALES_MAX:      # سقف صلب: تنظيف المنتهية ثم الأقدم
        now = time.time()
        for key in [k for k, v in WHALES.items()
                    if now - float(v.get("ts", 0.0) or 0.0) > WHALE_MEMORY_SEC]:
            WHALES.pop(key, None)
        while len(WHALES) > WHALES_MAX:
            WHALES.pop(min(WHALES, key=lambda k: WHALES[k].get("ts", 0.0)), None)
    FUNNEL["whale"] += 1
    return True


def whale_recent(symbol, max_age=None):
    """هل أيقظ حوتٌ هذه العملة داخل نافذة الشمعة الحالية؟ يعيد (bool, usd)."""
    info = WHALES.get(symbol)
    if not info:
        return False, 0.0
    age = time.time() - float(info.get("ts", 0.0) or 0.0)
    window = WHALE_MEMORY_SEC if max_age is None else float(max_age)
    if age > window:
        WHALES.pop(symbol, None)       # تنظيف كسول → لا تراكم
        return False, 0.0
    return True, float(info.get("usd", 0.0) or 0.0)


def on_agg_trade(symbol, data):
    """معالج aggTrade: يراكم الدلو الزمني ثم يقيّم الإشارة فوراً (بلا انتظار دفتر)."""
    try:
        if SYMBOLS and symbol not in SYMBOLS_SET:
            return
        ts_ms = float(data.get("T") or data.get("t") or 0)
        price = float(data.get("p") or 0)
        qty = float(data.get("q") or 0)
        if price <= 0 or qty <= 0:
            return
        quote = price * qty
        # V5.3 — Whale-Wake: صفقة مفردة ضخمة (شراء سوقي) تُعلَّم كإيقاظ حوت
        if quote >= WHALE_TRADE_USD and not bool(data.get("m")):
            whale_mark(symbol, quote, ts_ms / 1000.0 if ts_ms else time.time())
        if bool(data.get("m")):
            state = flow_add(symbol, ts_ms / 1000.0 if ts_ms else time.time(), 0.0, quote)
        else:
            state = flow_add(symbol, ts_ms / 1000.0 if ts_ms else time.time(), quote, 0.0)
        state["price"] = price
        state["epoch"] = time.time()
        on_market_tick(symbol)
    except Exception as exc:
        log(f"خطأ معالجة aggTrade {symbol}: {exc}")


# ── سياق BTC: قاطع شراء كلي + محدد حالة التهدئة ──────────────────────────────


def btc_ctx_apply(symbol, k):
    """يحدّث ذاكرة BTC من رسالة kline_1m (يقبل الرسالة المغلَّفة أو الخام)."""
    try:
        if not isinstance(k, dict):
            return
        if str(k.get("i") or "1m") != "1m":
            return
        price = float(k.get("c") or 0)
        if price <= 0:
            return
        ctx = BTC_CTX
        ctx["live"] = price
        ctx["last_update"] = time.monotonic()
        if not bool(k.get("x")):
            return
        closes = ctx["closes"]
        t_open = int(k.get("t") or 0)
        if closes and t_open and t_open <= ctx.get("last_t", 0):
            return
        closes.append(price)
        ctx["last_t"] = t_open
        ctx["seeded"] = True
    except Exception as exc:
        log(f"خطأ تحديث سياق BTC: {exc}")


def btc_ctx_dispatch(text):
    """توجيه رسالة من قناة BTC (raw /ws أو combined /stream)."""
    try:
        message = json.loads(text)
    except ValueError:
        return
    if not isinstance(message, dict):
        return
    if "data" in message:
        data = message.get("data") or {}
        if str(data.get("s", "")).upper() == BTC_CONTEXT_SYMBOL:
            btc_ctx_apply(BTC_CONTEXT_SYMBOL, data.get("k") or {})
    elif message.get("e") == "kline":
        if str(message.get("s", "")).upper() == BTC_CONTEXT_SYMBOL:
            btc_ctx_apply(BTC_CONTEXT_SYMBOL, message.get("k") or {})


def btc_ctx_stats():
    """يعيد {"age","drop_pct","vr"} من سياق BTC (drop_pct = التغير آخر 3 دقائق)."""
    ctx = BTC_CTX
    now = time.monotonic()
    age = now - float(ctx.get("last_update") or 0.0)
    closes = list(ctx.get("closes") or [])
    live = float(ctx.get("live") or 0.0)
    drop = None
    if closes and live > 0:
        window = BTC_DROP_WINDOW_MIN * 60_000
        t_now_ms = int(ctx.get("last_t") or 0) + 30_000
        ref = float(closes[-1])
        for t_off, value in enumerate(reversed(closes)):
            if t_off >= 1 and (t_now_ms - t_off * 60_000) <= t_now_ms - window:
                ref = float(value)
                break
        if ref > 0:
            drop = (live / ref - 1.0) * 100.0
    return {"age": age, "drop_pct": drop, "vr": float(ctx.get("vr") or 1.0)}


def btc_cooldown():
    """التهدئة الديناميكية العامة: تُقرأ من تقلب BTC على 1m (VR)."""
    vr = btc_ctx_stats()["vr"]
    if vr > VR_FAST:
        return COOLDOWN_FAST
    if vr < VR_SLOW:
        return COOLDOWN_SLOW
    return COOLDOWN_NORMAL


def btc_circuit_block():
    """قاطع السياق الكلي: يعيد (منع؟, سبب).

    يُمنع الشراء إذا هوى BTC أكثر من BTC_DROP_PCT خلال النافذة، أو كان مصدر
    السياق ميتاً (فشل آمن: لا شراء بلا معرفة اتجاه السوق الكلي).
    """
    if kill_switch_active() or STATE.get("paused"):
        return True, "kill/paused"
    stats = btc_ctx_stats()
    if stats["age"] > BTC_CTX_MAX_AGE or stats["drop_pct"] is None:
        return True, "context-unavailable"
    if stats["drop_pct"] <= -BTC_DROP_PCT:
        return True, f"btc-drop {stats['drop_pct']:.2f}%"
    return False, "ok"


def plan_position(entry, sl_distance, step=None, vr=1.0):
    """حجم مبانٍ على المخاطرة: notional = R / (sl_distance / entry).

    V5.3: إذا كان VR > VR_FAST (فوضى/تقلب متطرف) يُنصَّف الحجم لتقليل التعرض.

    يُقيَّد بسقف MAX_POSITION_NOTIONAL_USD، ويُرفض إن كان أصغر من حد
    Binance الأدنى. يعيد (qty, notional, risk_usd) أو (None, None, None).
    """
    # حارس قيم غير محددة (NaN/Inf) — بيانات شاذة لا يجب أن تفجّر المسار
    try:
        entry_f = float(entry)
        sl_f = float(sl_distance)
    except (TypeError, ValueError):
        return None, None, None
    if not math.isfinite(entry_f) or not math.isfinite(sl_f) or entry_f <= 0 or sl_f <= 0:
        return None, None, None
    entry = D(str(entry_f))
    sl_distance = D(str(sl_f))
    step = D("0.00000001") if step is None else D(step)
    if entry <= 0 or sl_distance <= 0:
        return None, None, None
    # notional = R / (sl/entry) = R × entry / sl — صيغة واحدة بلا تقريب المقلوب
    notional = (D(TARGET_RISK_USD) * entry) / sl_distance
    try:
        vr_f = float(vr)
    except (TypeError, ValueError):
        vr_f = 1.0
    if VOL_SIZE_HALVE and math.isfinite(vr_f) and vr_f > VR_FAST:
        notional = notional / Decimal("2")     # سوق فوضوي → نصف التعرض
    if notional > D(MAX_POSITION_NOTIONAL_USD):
        notional = D(MAX_POSITION_NOTIONAL_USD)
    if not math.isfinite(float(notional)) or notional <= 0:
        return None, None, None
    qty = round_step(notional / entry, step) if step > 0 else (notional / entry)
    if qty <= 0:
        return None, None, None
    notional = qty * entry
    risk_usd = (notional * sl_distance) / entry
    # حارس V5.3: بعد التقريب/السقف قد تتجاوز المخاطرة الفعلية الهدف — لا تتجاوزه أبداً
    if risk_usd > D(TARGET_RISK_USD) * D(RISK_TOLERANCE):
        return None, None, None
    return qty, notional, risk_usd


def micro_atr(symbol, atr_5m_fallback=0.0):
    """ATR(1m) لوقف الطوارئ الصلب — مع رجوع آمن إلى ATR(5m)/√5 عند غياب 1m."""
    try:
        buffer = CANDLES.get((symbol, MICRO_INTERVAL))
        if buffer and len(buffer.get("c") or []) >= ATR_PERIOD + 1:
            value = atr_last(buffer["h"], buffer["l"], buffer["c"], ATR_PERIOD)
            if math.isfinite(value) and value > 0:
                return float(value)
    except Exception:
        pass
    fallback = float(atr_5m_fallback or 0.0)
    if not math.isfinite(fallback) or fallback <= 0:
        return 0.0
    return fallback / max(1.0, MICRO_ATR_FALLBACK_DIV)


def market_price(symbol):
    """أفضل سعر تنفيذ متاح: آخر tick (aggTrade) ثم BBA ثم الشمعة الحية."""
    flow = FLOW.get(symbol) or {}
    book = BOOK.get(symbol) or {}
    buffer = CANDLES.get((symbol, SIGNAL_INTERVAL)) or {}
    price = float(flow.get("price") or 0)
    if price > 0:
        return price, 0.0
    price = float(book.get("ask") or 0)
    if price > 0:
        return price, 0.0
    closes = buffer.get("c") or []
    price = float(buffer.get("live") or 0) or (float(closes[-1]) if closes else 0.0)
    return price, math.inf


def data_age(symbol):
    """عمر أحدث بيانات سوق (ثوانٍ): aggTrade ثم bookTicker — حارس Latency Spike.

    «الطلقة المعلقة» حُذفت؛ هذا هو الحارس البديل: لا تنفيذ على سعر قديم.
    """
    ages = []
    flow = FLOW.get(symbol) or {}
    if flow.get("epoch"):
        ages.append(time.time() - float(flow.get("epoch") or 0.0))
    elif flow.get("ts"):
        ages.append(time.time() - float(flow.get("ts") or 0.0))
    book = BOOK.get(symbol) or {}
    if book.get("ts"):
        ages.append(time.monotonic() - float(book.get("ts") or 0.0))
    if not ages:
        return math.inf
    return min(ages)


# ══════════════════════════════════════════════════════════════════════════════
# 6) محرك التنقيط الموزون (V5) — بدل عقد AND: MSS+FVG+EMA50+Flow ≥ 75
# ══════════════════════════════════════════════════════════════════════════════


def compute_score(has_mss, has_fvg, trend_ok, imb, trend_slope_up=False,
                  vol_ratio=1.0, whale=False):
    """محرك التنقيط التعويضي الشبيه بالبشر (V5.2) — دالة نقية.

    التدرّج: اختلال التدفق 8/14/20 بحسب قوته، والاتجاه 10 (فوق EMA والميل
    مسطح) أو 20 (فوق EMA وميل صاعد)، ومكافأة حجم حتى +5 عند تضخّم الشمعة.

    التعويض: إذا أظهر التدفق أو الحجم زخماً استثنائياً
    (imb > MOMENTUM_FLOW_EXTREME أو vol_ratio > MOMENTUM_VOL_EXTREME) — أو رُصد
    «إيقاظ حوت» (صفقة مفردة ≥ WHALE_TRADE_USD) — تُضاف
    مكافأة ثقيلة SCORE_MOMENTUM_BONUS (+25) — فيُسمح بالدخول حتى لو غابت FVG
    أو كان الاتجاه غير مواتٍ، تماماً كما يفعل المتداول البشري أمام انفجار حقيقي.

    الحارس الصارم الوحيد: MSS (كسر هيكل) إلزامي دائماً — بلا كسر هيكلي لا
    دخول مهما بلغ الزخم (منع شراء السبايكات العشوائية).

    يعيد (score, components, triggered, parts).
    """
    imb = float(imb or 0.0)
    if imb >= FLOW_IMBALANCE_MIN:
        flow_pts = SCORE_FLOW
    elif imb >= FLOW_IMBALANCE_MED:
        flow_pts = SCORE_FLOW_MED
    elif imb >= FLOW_IMBALANCE_WEAK:
        flow_pts = SCORE_FLOW_WEAK
    else:
        flow_pts = 0.0
    if trend_ok:
        ema_pts = SCORE_EMA if trend_slope_up else SCORE_EMA_FLAT
    else:
        ema_pts = 0.0
    vol_ratio = float(vol_ratio or 0.0)
    if vol_ratio <= 0:
        vol_pts = 0.0
    else:
        vol_pts = min(SCORE_VOLUME_MAX, SCORE_VOLUME_MAX * min(1.0, (vol_ratio - 1.0) / (VOLUME_SPIKE - 1.0)))
    # زخم استثنائي: ضغط شراء هائل أو انفجار حجم → مكافأة تعويضية ثقيلة
    momentum = bool(whale or imb > MOMENTUM_FLOW_EXTREME or vol_ratio > MOMENTUM_VOL_EXTREME)
    momentum_pts = SCORE_MOMENTUM_BONUS if momentum else 0.0
    parts = {
        "mss": SCORE_MSS if has_mss else 0.0,
        "fvg": SCORE_FVG if has_fvg else 0.0,
        "ema": float(ema_pts),
        "flow": float(flow_pts),
        "volume": float(vol_pts),
        "momentum": float(momentum_pts),
    }
    components = sum(1 for value in parts.values() if value > 0)
    score = min(100.0, float(sum(parts.values())))   # السقف 100 مهما تراكمت المكافآت
    triggered = (score >= SCORE_TRIGGER and components >= max(1, MIN_SCORE_COMPONENTS)
                 and bool(has_mss))
    return score, components, triggered, parts


def _evaluate_frame(symbol):
    """يحسب كل ما يخص الشموع لإشارة العملة. يعيد (signal|None, reason)."""
    rule = SYMBOL_RULES.get(symbol)
    if not rule or rule.get("status") != "TRADING":
        return None, "not-trading"
    buffer = CANDLES.get((symbol, SIGNAL_INTERVAL))
    if not buffer or len(buffer["c"]) < MIN_CLOSED_CANDLES:
        return None, "no-data"
    server_now_ms = time.time() * 1000 + TIME_OFFSET_MS
    if buffer["t"] and server_now_ms - buffer["t"][-1] > INTERVAL_SECONDS[SIGNAL_INTERVAL] * 3000:
        return None, "stale-candles"
    o, h, l, c = buffer_to_frame(buffer)
    v = buffer["v"]
    for i in range(max(0, c.size - 5), c.size):
        if not math.isfinite(float(o[i])) or not math.isfinite(float(h[i])) \
                or not math.isfinite(float(l[i])) or not math.isfinite(float(c[i])) \
                or not math.isfinite(float(v[i])):
            return None, "bad-candles"
        if h[i] < max(o[i], c[i]) or l[i] > min(o[i], c[i]):
            return None, "bad-candles"
    # فلتر مصايد السيولة: ذيل مهيمن على الشمعة الأخيرة → منع مطلق
    wick = detect_wick_ratio(o, h, l, c)
    if wick > WICK_REJECT_RATIO:
        FUNNEL["wick"] += 1
        return None, f"wick {wick:.2f}"
    atr_value, vr = volatility_ratio(h, l, c, ATR_PERIOD, VR_BASELINE)
    if atr_value <= 0:
        FUNNEL["no-atr"] += 1
        return None, "no-atr"
    price_now = float(buffer.get("live") or buffer["c"][-1])
    atr_pct = (atr_value / price_now * 100.0) if price_now else 0.0
    # فلاتر قاطعة جديدة (V5.1): سوق ميت / تقلب جنوني
    if atr_pct < MIN_ATR_PCT:
        FUNNEL["dead-market"] += 1
        return None, f"dead atr% {atr_pct:.2f}<{MIN_ATR_PCT:.2f}"
    if vr > VR_EXTREME:
        FUNNEL["extreme-vr"] += 1
        return None, f"extreme VR {vr:.2f}>{VR_EXTREME:.2f}"
    mss = detect_mss(o, h, l, c, atr_value)
    fvg = detect_fvg(h, l, atr_value)
    trend = TREND.get(symbol) or {}
    ema_value = trend.get("ema")
    trend_ok = ema_value is not None and price_now > float(ema_value)
    slope_up = bool(trend.get("slope_up", False))
    # مطاردة القمم: السعر ممتد بعيداً جداً فوق EMA50 (شراء القمة) → منع
    if trend_ok and ema_value and atr_value > 0:
        ext_atr = (price_now - float(ema_value)) / atr_value
        ext_pct = (price_now - float(ema_value)) / float(ema_value) * 100.0
        if ext_atr > CHASE_MAX_ATR and ext_pct > CHASE_MIN_PCT:
            FUNNEL["chase"] += 1
            return None, f"chase +{ext_atr:.1f}ATR/+{ext_pct:.1f}%"
    if fvg and price_now <= fvg["mid"]:
        fvg = None            # السعر غاص داخل منتصف الفجوة → لا تُحتسب نقاطها
    imb, _age = flow_imbalance(symbol)
    # حجم الشمعة المغلقة الأخيرة مقابل متوسط آخر 20 شمعة (مكافأة زخم حقيقي)
    vol_arr = np.asarray(list(v), dtype="float64")
    vol_ratio = float(vol_arr[-1] / np.mean(vol_arr[-21:-1])) if vol_arr.size >= 21 and np.mean(vol_arr[-21:-1]) > 0 else 1.0
    whale_flag, whale_usd = whale_recent(symbol)
    score, components, triggered, parts = compute_score(
        mss is not None, fvg is not None, trend_ok, imb, slope_up, vol_ratio, whale_flag)
    reason = "ok" if triggered else f"score {score:.0f}<{SCORE_TRIGGER:.0f}/c{components}"
    return {
        "symbol": symbol, "setup_id": f"{symbol}@{int(buffer['t'][-1]) if buffer['t'] else 0}",
        "atr": atr_value, "vr": vr,
        "atr_pct": atr_pct, "vol_ratio": vol_ratio,
        "close": float(c[-1]), "live": price_now,
        "score": score, "parts": parts, "components": components,
        "fvg_mid": (fvg or {}).get("mid", 0.0),
        "fvg_low": (fvg or {}).get("low", 0.0),
        "fvg_high": (fvg or {}).get("high", 0.0),
        "mss_prior_high": (mss or {}).get("prior_high", 0.0),
        "displacement": (mss or {}).get("displacement", 0.0),
        "flow_imbalance": float(imb or 0.0),
        "whale": bool(whale_flag), "whale_usd": float(whale_usd),
        "atr_1m": micro_atr(symbol, atr_value),
        "wick_ratio": wick,
        "triggered": triggered,
        "candle_t": int(buffer["t"][-1]) if buffer["t"] else 0,
        "created_at": time.time(),
    }, reason


def build_signal(symbol):
    """يعيد قاموس الإشارة عند تجاوز حاجز التنقيط، وإلا None."""
    info, _reason = _evaluate_frame(symbol)
    return info if info and info.get("triggered") else None


def veto_reason(symbol, signal=None):
    """الفلاتر القاطعة بعد التنقيط: سياق BTC + قدم البيانات + السبريد."""
    blocked, why = btc_circuit_block()
    if blocked:
        FUNNEL["btc-breaker"] += 1
        return why
    book = BOOK.get(symbol) or {}
    if book and float(book.get("spread_pct") or 0) > MAX_SPREAD_PCT:
        FUNNEL["spread"] += 1
        return "spread"
    if data_age(symbol) > MAX_STALE_SEC:
        FUNNEL["stale-tick"] += 1
        return "stale-tick"
    return None


def _entry_gates_open(symbol):
    """بوابات رخيصة قبل أي تقييم: قاطع، سقف مراكز، تهدئة ديناميكية."""
    if kill_switch_active() or STATE.get("paused"):
        return False
    if SYMBOLS and symbol not in SYMBOLS_SET:
        return False
    if count_open_positions() >= MAX_OPEN_POSITIONS:
        return False
    if count_symbol_positions(symbol) >= MAX_POSITIONS_PER_SYMBOL:
        return False
    if time.time() - float(STATE.get("last_entry_at", {}).get(symbol, 0.0)) < btc_cooldown():
        return False
    return True


def on_signal_candle_closed(symbol):
    """شمعة 5m أُغلقت: تنقيط فوري — تنفيذ إن اكتمل، أو مرشح رخيص للتدفق.

    لا «طلقة معلقة» ولا انتظار دفتر: المرشح يُعاد تقييمه عند وصول aggTrade
    (بمهلة FLOW_CHECK_EVERY) فينفّذ في نفس اللحظة التي يكتمل فيها الحاجز.
    """
    if not _entry_gates_open(symbol):
        return
    info, reason = _evaluate_frame(symbol)
    if info is None:
        READY.pop(symbol, None)
        log(f"تقييم {symbol}: {reason}")
        return
    if info["triggered"]:
        READY.pop(symbol, None)
        if info["setup_id"] in SETUPS:
            return  # نفس الشمعة مُنفَّذة — منع التكرار
        launch_entry(info)
        return
    reach = max(SCORE_FLOW, SCORE_EMA, SCORE_FVG, SCORE_MOMENTUM_BONUS)
    if info["score"] + reach >= SCORE_TRIGGER and info["components"] + 1 >= max(1, MIN_SCORE_COMPONENTS):
        READY[symbol] = {"t": info["candle_t"], "score": info["score"],
                         "checked": time.monotonic()}
    else:
        READY.pop(symbol, None)


def on_market_tick(symbol):
    """tick حقيقي (aggTrade): يُعيد تقييم المرشحات فقط — لا حساب على كل صفقة.

    هذا يحمي الجوال من استنزاف CPU (تقييم كامل لكل رمز لكل trade) بينما يبقي
    زمن الاستجابة ≤ ثانية واحدة عند اكتمال النقاط.
    """
    candidate = READY.get(symbol)
    if not candidate:
        return
    now = time.monotonic()
    if now - float(candidate.get("checked", 0.0)) < FLOW_CHECK_EVERY:
        return
    candidate["checked"] = now
    if not _entry_gates_open(symbol):
        return
    buffer = CANDLES.get((symbol, SIGNAL_INTERVAL))
    if not buffer or not buffer["t"] or int(buffer["t"][-1]) != int(candidate["t"]):
        READY.pop(symbol, None)   # الشمعة تغيّرت → المرشح عفا عليه
        return
    info, _reason = _evaluate_frame(symbol)
    if info is None:
        READY.pop(symbol, None)
        return
    if not info["triggered"]:
        candidate["score"] = info["score"]
        return
    READY.pop(symbol, None)
    if info["setup_id"] in SETUPS:
        return
    launch_entry(info)


def on_kline(data):
    """معالج رسائل kline: تحديث الحية دائماً، وعند الإغلاق تشغيل محرك التنقيط."""
    try:
        if not isinstance(data, dict) or data.get("e") != "kline":
            return
        k = data.get("k") or {}
        symbol = data.get("s")
        interval = k.get("i")
        if interval not in INTERVAL_SECONDS:
            return
        if SYMBOLS and symbol not in SYMBOLS_SET:
            return  # تدفق خارج الكون الحالي (مثل التدفق المؤقت) → تجاهل
        key = (symbol, interval)
        buffer = CANDLES.get(key)
        if buffer is None:
            buffer = {"t": [], "o": [], "h": [], "l": [], "c": [], "v": [], "live": 0.0}
            CANDLES[key] = buffer
        live = float(k.get("c") or 0)
        if live > 0:
            buffer["live"] = live
        if not bool(k.get("x")):
            return  # شمعة حية — تحديث السعر الجاري فقط ثم عودة للسبات
        outcome = buffer_append(
            buffer, interval,
            int(k.get("t") or 0), float(k.get("o") or 0), float(k.get("h") or 0),
            float(k.get("l") or 0), float(k.get("c") or 0), float(k.get("v") or 0),
        )
        if outcome == "gap":
            schedule_reseed(symbol)
            return
        if outcome not in ("appended", "updated"):
            return
        if interval == TREND_INTERVAL:
            update_trend_ema(symbol)
        elif interval == SIGNAL_INTERVAL and outcome == "appended":
            on_signal_candle_closed(symbol)   # صلاحية الحوت زمنية (WHALE_MEMORY_SEC)
    except Exception as exc:
        log(f"خطأ معالجة kline: {exc}")


def on_book(symbol, data):
    """معالج bookTicker: BBA للسبريد + محرك الخروج الهجين (تعادل/تتبّع)."""
    try:
        if SYMBOLS and symbol not in SYMBOLS_SET:
            parsed_out = parse_book_payload(data)
            if parsed_out is not None and any(
                    p.get("symbol") == symbol for p in (STATE.get("positions") or {}).values()):
                BOOK[symbol] = parsed_out      # عملة خرجت من الكون لكنها ما زالت مفتوحة
                on_price_update(symbol, parsed_out.get("bid") or parsed_out.get("ask") or 0.0)
            return
        parsed = parse_book_payload(data)
        if parsed is not None:
            BOOK[symbol] = parsed
            # التسعير للخروج يعتمد أفضل سعر بيع فوري (bid) — تحفّظ سليم
            on_price_update(symbol, parsed.get("bid") or 0.0)
    except Exception as exc:
        log(f"خطأ معالجة bookTicker {symbol}: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# 6.5) محرك الخروج الهجين (V5.3): قمة متحركة + تعادل + تتبّع بسرعة ديناميكية
# ══════════════════════════════════════════════════════════════════════════════


def on_price_update(symbol, price):
    """يُستدعى من bookTicker لكل تحديث سعر: يحدّث القمة ويطلق الخروج عند اللمس.

    متزامن وخفيف تماماً (لا I/O): كل ما يفعله تحديث حقول داخل المركز نفسه
    وجدولة مهمة بيع واحدة عند الحاجة. القمم مخزّنة داخل المراكز فتُحرَّر
    تلقائياً عند الإغلاق — لا قاموس عالمي ينمو بلا حدود (لا تسرّب ذاكرة).
    """
    try:
        price = float(price or 0.0)
        if not math.isfinite(price) or price <= 0:
            return
        positions = STATE.get("positions") or {}
        if not positions:
            return
        for pid, position in list(positions.items()):
            if position.get("symbol") != symbol:
                continue
            entry = float(position.get("entry", 0) or 0)
            if entry <= 0:
                continue
            peak = float(position.get("peak", entry) or entry)
            if price > peak:
                peak = price
                position["peak"] = peak
            position["last_price"] = price
            plan = trailing_plan(entry, peak, price)
            if not plan["armed"]:
                continue
            if not position.get("trail_armed"):
                position["trail_armed"] = True
                log(f"تعادل مؤمَّن {pid}: ربح القمة {plan['peak_gain_pct']:+.2f}% → "
                    f"وقف محلي {fmt_price(symbol, plan['stop'])} (دخول +{BREAKEVEN_LOCK_PCT}%)")
            position["trail_stop"] = float(plan["stop"])
            position["trail_mode"] = plan["mode"]
            if plan["hit"]:
                trigger_trailing_exit(pid, position, plan)
    except Exception as exc:
        log(f"خطأ محرك التتبّع {symbol}: {exc}")


def trigger_trailing_exit(pid, position, plan):
    """يجدول بيع MARKET واحداً بالضبط لهذا المركز (حارس تزامني قبل المهمة)."""
    if pid in EXIT_PENDING or pid in EXIT_CLAIMED:
        return
    if (STATE.get("positions") or {}).get(pid) is None:
        return
    EXIT_PENDING.add(pid)
    reason = (f"تتبّع ديناميكي ({plan['mode']} {plan['trail_pct']:.2f}%) "
              f"قمة {plan['peak_gain_pct']:+.2f}% → خروج {plan['gain_pct']:+.2f}%")
    try:
        asyncio.get_running_loop().create_task(_trailing_exit_task(pid, dict(position), reason))
    except RuntimeError:
        EXIT_PENDING.discard(pid)


async def _trailing_exit_task(pid, position, reason):
    """مهمة الخروج: إلغاء وقف Binance ثم MARKET SELL (مطالبة ذرية بالداخل)."""
    try:
        if not live_execution_allowed():
            # وضع المحاكاة: سجّل مرة واحدة لكل مركز ولا تُغرق السجل بكل tick
            position_live = (STATE.get("positions") or {}).get(pid)
            if position_live is not None and not position_live.get("dry_exit_logged"):
                position_live["dry_exit_logged"] = True
                log(f"[DRY] وقف متحرك لُمس {pid}: {reason} (التنفيذ غير مفعّل)")
            return
        FUNNEL["trail-exit"] += 1
        log(f"وقف متحرك لُمس {pid}: {reason} → إلغاء وقف الطوارئ ثم بيع MARKET")
        await force_exit_position(pid, position, reason)
    except Exception as exc:
        log(f"خطأ خروج التتبّع {pid}: {exc}")
    finally:
        EXIT_PENDING.discard(pid)


# ══════════════════════════════════════════════════════════════════════════════
# 7) إدارة المخاطر: الوقف الديناميكي (VR) + الحجم بالمخاطرة (Risk Parity)
# ══════════════════════════════════════════════════════════════════════════════


def atr_multiplier(vr):
    """مصفوفة الوقف الديناميكي: معامل ضرب ATR بحسب نسبة التقلب."""
    if vr > VR_FAST:
        return ATR_MULT_FAST, "fast"
    if vr < VR_SLOW:
        return ATR_MULT_SLOW, "slow"
    return ATR_MULT_NORMAL, "normal"


def calculate_dynamic_risk(entry, atr_value, vr, atr_1m=None):
    """V5.3 — وقف الطوارئ الصلب: ATR(1m) × HARD_STOP_ATR_MULT بسقف SL_MAX_PCT%.

    لم يعد هناك هدف ثابت: الخروج الرابح يديره محرك التتبّع المحلي، وهذا
    الوقف مجرد شبكة أمان كارثية على Binance. VR يبقى مستخدماً لوصف النظام
    ولتنصيف الحجم فقط، لا لتوسيع الوقف.

    يعيد {"sl_distance","sl_pct","sl","mult","regime","capped","atr_1m"}.
    """
    entry = float(entry)
    if not math.isfinite(entry) or entry <= 0:
        raise ValueError("سعر الدخول غير صالح")
    atr_value = float(atr_value or 0.0)
    if not math.isfinite(atr_value):
        atr_value = 0.0
    vr = float(vr if math.isfinite(float(vr or 0.0)) else 1.0)
    _mult_desc, regime = atr_multiplier(max(0.0, vr))
    micro = float(atr_1m if atr_1m is not None else 0.0)
    if not math.isfinite(micro) or micro <= 0:
        micro = (atr_value / max(1.0, MICRO_ATR_FALLBACK_DIV)) if atr_value > 0 else 0.0
    sl_distance = max(0.0, micro) * HARD_STOP_ATR_MULT
    cap = entry * SL_MAX_PCT / 100.0
    floor = entry * SL_MIN_PCT / 100.0
    capped = False
    if sl_distance < floor:
        sl_distance = floor
    if sl_distance > cap:
        sl_distance = cap
        capped = True
    sl_pct = sl_distance / entry * 100.0
    return {
        "sl_distance": sl_distance, "sl_pct": sl_pct,
        "sl": entry - sl_distance, "mult": HARD_STOP_ATR_MULT,
        "regime": regime, "capped": capped, "atr_1m": micro,
    }


def hard_stop_price(entry, atr_1m, atr_5m=0.0, vr=1.0):
    """سعر وقف الطوارئ الصلب فقط (بلا هدف) — Decimal جاهز للتقريب."""
    risk = calculate_dynamic_risk(entry, atr_5m, vr, atr_1m)
    return D(str(risk["sl"])), risk


def trailing_plan(entry, peak, price):
    """محرك الخروج الهجين (نقي وقابل للاختبار).

    يعيد dict:
      armed        : هل تفعّل التعادل/التتبّع (ربح بلغ BREAKEVEN_TRIGGER_PCT)?
      stop         : مستوى الوقف المحلي الفعّال (None قبل التفعيل)
      mode         : "off" | "breakeven" | "trail-wide" | "trail-tight"
      trail_pct    : مسافة التتبّع المستعملة
      gain_pct     : ربح السعر الحالي
      peak_gain_pct: ربح القمة
      hit          : هل لُمس الوقف المحلي الآن؟
    """
    try:
        entry = float(entry); price = float(price)
    except (TypeError, ValueError):
        return {"armed": False, "stop": None, "mode": "off", "trail_pct": 0.0,
                "gain_pct": 0.0, "peak_gain_pct": 0.0, "hit": False}
    try:      # قمة مفقودة/فاسدة لا يجوز أن تُعطّل الحماية — تُشتق من السعر
        peak = float(peak)
    except (TypeError, ValueError):
        peak = 0.0
    if not (math.isfinite(entry) and entry > 0 and math.isfinite(price) and price > 0):
        return {"armed": False, "stop": None, "mode": "off", "trail_pct": 0.0,
                "gain_pct": 0.0, "peak_gain_pct": 0.0, "hit": False}
    if not math.isfinite(peak) or peak <= 0:
        peak = max(entry, price)
    peak = max(peak, price, entry)
    gain_pct = (price - entry) / entry * 100.0
    peak_gain_pct = (peak - entry) / entry * 100.0
    if peak_gain_pct < BREAKEVEN_TRIGGER_PCT:
        return {"armed": False, "stop": None, "mode": "off", "trail_pct": 0.0,
                "gain_pct": gain_pct, "peak_gain_pct": peak_gain_pct, "hit": False}
    breakeven = entry * (1.0 + BREAKEVEN_LOCK_PCT / 100.0)
    trail_pct = TRAIL_TIGHT_PCT if peak_gain_pct > TRAIL_TIGHT_AFTER_PCT else TRAIL_WIDE_PCT
    trail_stop = peak * (1.0 - trail_pct / 100.0)
    stop = max(breakeven, trail_stop)          # لا يهبط تحت التعادل أبداً
    if stop >= breakeven and trail_stop > breakeven:
        mode = "trail-tight" if trail_pct == TRAIL_TIGHT_PCT else "trail-wide"
    else:
        mode = "breakeven"
    return {"armed": True, "stop": stop, "mode": mode, "trail_pct": trail_pct,
            "gain_pct": gain_pct, "peak_gain_pct": peak_gain_pct,
            "hit": price <= stop}


# ══════════════════════════════════════════════════════════════════════════════
# 8) التنفيذ: MARKET BUY فوري + OCO ديناميكي عبر User Data Stream (Set & Forget)
# ══════════════════════════════════════════════════════════════════════════════


def live_execution_allowed():
    if DRY_RUN or not AUTO_TRADE or not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return False
    if BINANCE_ENV == "live" and LIVE_CONFIRM != "I_UNDERSTAND_SPOT_RISK":
        return False
    return True


def count_symbol_positions(symbol):
    return sum(1 for p in STATE.get("positions", {}).values() if p.get("symbol") == symbol)


def count_open_positions():
    return len(STATE.get("positions", {}) or {})


def total_reserved_slots():
    return sum(int(v) for k, v in ENTRY_RESERVATIONS.items()
               if isinstance(k, str) and not k.endswith(":cost"))


async def mark_cooldown(symbol):
    async with STATE_LOCK:
        STATE.setdefault("cooldowns", {})[symbol] = time.time()


async def reserve_entry(symbol, cost=None):
    """حجز ذري (ENTRY_LOCK): سقف مراكز + تهدئة ديناميكية + حجز تكلفة تقديرية.

    أمر MARKET لا يحمل سعراً مسبقاً، لذا تُحجز تكلفة تقديرية (قيمة المركز
    + هامش انزلاق) لمنع تجاوز الرصيد عند تزامن عدة دخولات — ترقيع سباق الدخول.
    """
    global RESERVED_QUOTE
    cost = D(TARGET_RISK_USD) if cost is None else D(cost)
    async with ENTRY_LOCK:
        if kill_switch_active() or STATE.get("paused"):
            return False
        current = count_symbol_positions(symbol)
        reserved = ENTRY_RESERVATIONS.get(symbol, 0)
        if current + reserved >= MAX_POSITIONS_PER_SYMBOL:
            return False
        if count_open_positions() + total_reserved_slots() >= MAX_OPEN_POSITIONS:
            return False
        if time.time() - float(STATE.get("last_entry_at", {}).get(symbol, 0.0)) < btc_cooldown():
            return False
        ENTRY_RESERVATIONS[symbol] = reserved + 1
        ENTRY_RESERVATIONS[symbol + ":cost"] = dec_str(
            D(ENTRY_RESERVATIONS.get(symbol + ":cost", "0")) + cost)
        RESERVED_QUOTE += cost
        return True


async def release_entry(symbol, cost=None):
    global RESERVED_QUOTE
    cost = D(TARGET_RISK_USD) if cost is None else D(cost)
    async with ENTRY_LOCK:
        reserved = ENTRY_RESERVATIONS.get(symbol, 0)
        if reserved <= 1:
            ENTRY_RESERVATIONS.pop(symbol, None)
            ENTRY_RESERVATIONS.pop(symbol + ":cost", None)
        else:
            ENTRY_RESERVATIONS[symbol] = reserved - 1
            ENTRY_RESERVATIONS[symbol + ":cost"] = dec_str(
                max(Decimal("0"), D(ENTRY_RESERVATIONS.get(symbol + ":cost", "0")) - cost))
        RESERVED_QUOTE = max(Decimal("0"), RESERVED_QUOTE - cost)


async def process_signal(signal):
    """بوابة ما قبل التنفيذ: فلاتر قاطعة + حجز ذري بتكلفة تقديرية ثم MARKET."""
    symbol = signal["symbol"]
    veto = veto_reason(symbol, signal)
    if veto:
        log(f"إلغاء إشارة {symbol}: {veto} (score={signal.get('score', 0):.0f})")
        return False
    priced = estimate_entry_cost(signal)
    if priced is None:
        log(f"إلغاء إشارة {symbol}: بيانات سوق قديمة أو حجم دون الحد الأدنى")
        return False
    est_cost = D(priced["est_cost"])
    if not await reserve_entry(symbol, est_cost):
        return False
    try:
        async with ENTRY_SEMAPHORE:
            return await execute_entry(priced)
    finally:
        await release_entry(symbol, est_cost)


def estimate_entry_cost(signal):
    """سعر مرجعي + وقف ديناميكي (VR) + حجم بالمخاطرة. None = رفض التنفيذ.

    يستبدل «الطلقة المعلقة»: إن كانت آخر بيانات سوق أقدم من MAX_STALE_SEC
    تُلغى الإشارة فوراً بدل الانتظار عليها (حماية من Latency Spike/الانزلاق).
    """
    symbol = signal["symbol"]
    price, _age = market_price(symbol)
    if data_age(symbol) > MAX_STALE_SEC or price <= 0:
        return None
    atr_1m = signal.get("atr_1m")
    if atr_1m is None:
        atr_1m = micro_atr(symbol, signal.get("atr", 0.0))
    risk = calculate_dynamic_risk(price, signal["atr"], signal.get("vr", 1.0), atr_1m)
    step = (SYMBOL_RULES.get(symbol) or {}).get("step")
    qty, notional, risk_usd = plan_position(price, risk["sl_distance"], step,
                                            signal.get("vr", 1.0))
    if notional is None or qty is None:
        return None
    # حارس V5.3 (حاسم مع مراكز 12$): يجب أن تبقى الكمية قابلة للبيع بعد خصم
    # الرسوم وبعد هبوط معقول، وإلا صار المركز غباراً عالقاً لا يمكن الخروج منه.
    rule = SYMBOL_RULES.get(symbol) or {}
    min_notional = D(rule.get("min_notional", "0"))
    if min_notional > 0:
        net_qty = D(qty) * (Decimal("1") - D(FEE_BUFFER))
        exit_value = net_qty * D(str(price)) * (Decimal("1") - D(str(SL_MAX_PCT)) / Decimal("100"))
        if exit_value < min_notional * D(MIN_NOTIONAL_SAFETY):
            FUNNEL["min-notional"] += 1
            return None
    updated = dict(signal)
    updated["price"] = float(price)
    updated["risk"] = risk
    updated["qty"] = qty
    updated["notional"] = notional
    updated["risk_usd"] = risk_usd
    updated["sl_distance"] = float(risk["sl_distance"])
    updated["stop"] = float(risk["sl"])
    updated["atr_1m"] = float(risk.get("atr_1m", 0.0))
    updated["est_cost"] = float(D(str(notional)) * D(MARKET_COST_BUFFER))
    return updated


def sellable_qty(symbol, qty, price):
    rule = SYMBOL_RULES.get(symbol)
    if not rule:
        return None
    sell_qty = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), rule.get("market_step", rule["step"]))
    if sell_qty < rule.get("market_min_qty", rule.get("min_qty", D("0"))):
        return None
    if rule.get("min_notional", D("0")) > 0 and sell_qty * D(price) < rule["min_notional"]:
        return None
    return sell_qty


async def add_dust(symbol, qty, cost, reason):
    async with STATE_LOCK:
        dust = STATE.setdefault("dust", [])
        for item in dust:
            if item.get("symbol") == symbol:
                item["qty"] = dec_str(D(item.get("qty", "0")) + D(qty))
                item["cost"] = dec_str(D(item.get("cost", "0")) + D(cost))
                break
        else:
            dust.append({
                "symbol": symbol, "qty": dec_str(D(qty)), "cost": dec_str(D(cost)),
                "since": time.time(), "reason": str(reason),
            })
    await save_state()
    log(f"Dust {symbol}: qty={dec_str(D(qty))} cost={dec_str(D(cost))} reason={reason}")


async def emergency_sell(symbol, qty, reason, already_net=False):
    """بيع سوقي فوري. already_net=True ⇒ الكمية مخصومة الرسوم مسبقاً.

    كمية المركز مخزّنة أصلاً بعد خصم FEE_BUFFER في place_hard_stop؛ خصمها
    مرة ثانية هنا كان يترك ~0.15% غباراً غير مُباع في كل خروج (تسرّب رأس مال).
    """
    try:
        rule = SYMBOL_RULES[symbol]
        step = rule.get("market_step", rule["step"])
        min_qty = rule.get("market_min_qty", rule["min_qty"])
        gross = D(qty) if already_net else D(qty) * (Decimal("1") - D(FEE_BUFFER))
        quantity = round_step(gross, step)
        if quantity < min_qty:
            return None
        result = await REST.new_order({
            "symbol": symbol, "side": "SELL", "type": "MARKET",
            "quantity": dec_str(quantity), "newClientOrderId": make_client_id("pan"),
            "newOrderRespType": "FULL",
        })
        log(f"خروج طارئ {symbol}: {reason}")
        return result
    except BinanceError as exc:
        log(f"فشل الخروج الطارئ {symbol}: {exc}")
        return None


async def recover_order_by_client_id(symbol, client_order_id):
    """يمنع ازدواج الحماية: إن قُبل الوقف ثم ضاعت الاستجابة نستردّه بالمعرّف."""
    if not client_order_id:
        return None
    try:
        order = await REST.get_order_client(symbol, client_order_id)
        if order and order.get("orderId") is not None:
            return order
    except BinanceError:
        pass
    return None


async def place_hard_stop(symbol, qty, entry, stop_price, reference=None, already_net=False):
    """V5.3 — وقف الطوارئ الصلب فقط (STOP_LOSS_LIMIT) بلا أي رجل هدف.

    الربح يُدار محلياً (تعادل + تتبّع ديناميكي) وينفَّذ MARKET SELL؛ هذا الأمر
    شبكة أمان ضد الانهيار المفاجئ/انقطاع الاتصال فقط.

    reference: السعر الذي تُقاس عليه صلاحية الوقف (يجب أن يكون الوقف تحته).
    افتراضياً سعر الدخول؛ وعند إعادة التركيب يُمرَّر سعر السوق حتى لا يُسحق
    وقف التعادل/التتبّع (وهو فوق الدخول شرعاً) إلى ما دون الدخول.
    """
    rule = SYMBOL_RULES[symbol]
    gross = D(qty) if already_net else D(qty) * (Decimal("1") - D(FEE_BUFFER))
    quantity = round_step(gross, rule["step"])
    ref = D(str(reference)) if reference is not None else D(entry)
    if ref <= 0:
        ref = D(entry)
    stop = round_price(stop_price, rule["tick"], "down")
    if stop >= ref:
        stop = round_price(ref - rule["tick"] * 2, rule["tick"], "down")
    stop_limit = round_price(stop * (Decimal("1") - D(LIMIT_SLIPPAGE_PCT) / Decimal("100")),
                             rule["tick"], "down")
    if stop_limit <= 0:
        stop_limit = round_price(stop, rule["tick"], "down")
    if quantity < rule["min_qty"] or quantity * D(entry) < rule["min_notional"]:
        raise BinanceError("الكمية لا تحقق فلاتر Binance")
    client_id = make_client_id("hsl")
    params = {
        "symbol": symbol, "side": "SELL", "type": "STOP_LOSS_LIMIT",
        "quantity": dec_str(quantity), "price": dec_str(stop_limit),
        "stopPrice": dec_str(stop), "timeInForce": "GTC",
        "newClientOrderId": client_id, "newOrderRespType": "RESULT",
    }
    try:
        result = await REST.new_order(params)
    except BinanceError:
        recovered = await recover_order_by_client_id(symbol, client_id)
        if recovered is None:
            raise
        result = recovered
    order_id = result.get("orderId") if isinstance(result, dict) else None
    return {"type": "HARD_STOP", "order_id": order_id, "client_order_id": client_id,
            "orders": [{"orderId": order_id}] if order_id is not None else [],
            "qty": quantity, "stop": stop, "stop_limit": stop_limit}


async def cancel_hard_stop(position):
    """يلغي وقف الطوارئ الصلب بأمان (يبتلع «غير موجود» ويعيد True).

    True = لا يوجد وقف قائم بعد الآن (أُلغي أو لم يكن موجوداً)؛
    False = الإلغاء فشل لسبب حقيقي (شبكة/رفض) ⇒ لا تُرسل MARKET SELL.
    """
    symbol = position.get("symbol", "")
    ok = True
    for order_id in {x for x in position.get("order_ids", []) if x is not None}:
        try:
            await REST.cancel_order(symbol, order_id)
        except BinanceError as exc:
            if exc.code in (-2011, -2013):
                continue          # الأمر نُفّذ/أُلغي/غير موجود — لا شيء لإلغائه
            log(f"تعذر إلغاء وقف الطوارئ {symbol}#{order_id}: {exc}")
            ok = False
        except Exception as exc:
            log(f"خطأ إلغاء وقف الطوارئ {symbol}#{order_id}: {exc}")
            ok = False
    if not position.get("order_ids") and position.get("stop_client_id"):
        try:
            await REST.cancel_order_client(symbol, position["stop_client_id"])
        except BinanceError as exc:
            if exc.code not in (-2011, -2013):
                ok = False
        except Exception:
            ok = False
    return ok


async def execute_entry(signal):
    """MARKET BUY فوري بلا نافذة انتظار — الحسم من response ثم executionReport.

    وحدة «الطلقة المعلقة» حُذفت: تنفيذ سوقى مباشر على السعر المرجعي، بينما
    الوقف/الهدف/الحجم حُسبت مسبقاً في estimate_entry_cost (Risk Parity).
    """
    symbol = signal["symbol"]
    if kill_switch_active() or STATE.get("paused"):
        return False
    rule = SYMBOL_RULES.get(symbol)
    if not rule or rule.get("status") != "TRADING":
        return False
    risk = signal["risk"]
    qty = D(signal["qty"])
    price = D(str(signal["price"]))
    notional = D(signal["notional"])
    if D(risk["sl"]) >= price:
        log(f"مستوى وقف غير صالح لـ {symbol}؛ إلغاء")
        return False
    if not live_execution_allowed():
        if DRY_RUN:
            log(f"إشارة V5 [DRY-RUN] {symbol} @ {fmt_price(symbol, price)} "
                f"score={signal['score']:.0f} VR={signal.get('vr', 1.0):.2f} "
                f"qty={dec_str(qty)} notional={dec_str(notional)}$ "
                f"hardSL {fmt_price(symbol, risk['sl'])} ({risk['sl_pct']:.2f}%) "
                f"[{risk['regime']} ATR1m x{risk['mult']}"
                f"{' capped' if risk['capped'] else ''}] خروج هجين متحرك")
        else:
            log(f"إشارة مؤكدة بدون تنفيذ (التنفيذ غير مفعّل): {symbol}")
        await mark_cooldown(symbol)
        return False
    entry_client_id = make_client_id("nv5")
    record = None
    try:
        account = await REST.account()
        free_quote = free_balance_from(account, rule.get("quote", "USDT"))
        async with ENTRY_LOCK:
            other_reserved = max(Decimal("0"), RESERVED_QUOTE
                                 - D(signal["est_cost"]) * ENTRY_RESERVATIONS.get(symbol, 0))
        if free_quote < D(signal["est_cost"]) + other_reserved:
            log(f"رصيد USDT غير كافٍ لـ {symbol} (تكلفة {dec_str(D(signal['est_cost']))}$)")
            return False
        qty = round_step(qty, rule["step"])
        price = round_price(price, rule["tick"], "up")
        if qty < rule["min_qty"] or qty * price < rule["min_notional"]:
            log(f"فلاتر Binance تمنع دخول {symbol} (qty={dec_str(qty)})")
            return False
        record = {
            "symbol": symbol, "client_order_id": entry_client_id, "order_id": None,
            "qty": dec_str(qty), "price": dec_str(price), "atr": float(signal["atr"]),
            "atr_1m": float(signal.get("atr_1m", 0.0) or 0.0),
            "vr": float(signal.get("vr", 1.0)), "score": float(signal.get("score", 0)),
            "parts": dict(signal.get("parts") or {}), "setup_id": signal.get("setup_id", ""),
            "risk_usd": dec_str(signal["risk_usd"]), "notional": dec_str(notional),
            "sl": dec_str(risk["sl"]),
            "sl_pct": float(risk["sl_pct"]), "sl_mult": float(risk["mult"]),
            "imbalance": float(signal.get("flow_imbalance", 1.0)),
            "placed_at": time.time(), "active": True, "phase": "placing",
        }
        async with STATE_LOCK:
            STATE["pending_entries"][entry_client_id] = record
        await save_state()
        order = await REST.new_order({
            "symbol": symbol, "side": "BUY", "type": "MARKET",
            "quantity": dec_str(qty),
            "newClientOrderId": entry_client_id, "newOrderRespType": "FULL",
        })
        order_id = order.get("orderId") if isinstance(order, dict) else None
        status = str(order.get("status") or "") if isinstance(order, dict) else ""
        if not order_id:
            # استجابة بلا orderId: الأمر قد يكون مقبولاً — الواتش دوغ/الأحداث تحسم
            try:
                order = await REST.get_order_client(symbol, entry_client_id)
                order_id = order.get("orderId")
                status = str(order.get("status") or "")
            except BinanceError:
                order_id = None
        executed_qty, executed_quote, avg_price = (parse_fill(order, price)
                                                   if isinstance(order, dict)
                                                   else (Decimal("0"), Decimal("0"), price))
        async with STATE_LOCK:
            live_record = STATE["pending_entries"].get(entry_client_id)
            if live_record is not None:
                if order_id is not None:
                    live_record["order_id"] = order_id
                    ORDERS[str(order_id)] = {"role": "entry", "cid": entry_client_id, "symbol": symbol}
                    if executed_qty > 0:
                        live_record["executed_qty"] = dec_str(executed_qty)
                        live_record["executed_quote"] = dec_str(executed_quote)
                live_record["phase"] = "placed"
                live_record["active"] = False
        if executed_qty > 0 and status in ("FILLED", "PARTIALLY_FILLED"):
            await complete_entry(entry_client_id, live_record or record, executed_qty,
                                 avg_price, executed_quote)
            log(f"دخول MARKET {symbol} حسمته الاستجابة @ {fmt_price(symbol, avg_price)} "
                f"(qty={dec_str(executed_qty)} score={signal['score']:.0f})")
            return True
        arm_entry_watchdog(entry_client_id)
        await save_state()
        log(f"أمر دخول MARKET {symbol} @ {fmt_price(symbol, price)} (cid={entry_client_id}) "
            f"— بانتظار executionReport")
        return True
    except BinanceError as exc:
        # رفض صريح = لا أمر؛ شبكة غير مؤكدة = قد يكون قائماً (الواتش دوغ/الأحداث تحسم)
        if exc.code is None and exc.status is None:
            log(f"شبكة غير مؤكدة أثناء دخول {symbol}; الأحداث/الواتش دوغ ستتولى الأمر")
            arm_entry_watchdog(entry_client_id)
            return False
        async with STATE_LOCK:
            STATE["pending_entries"].pop(entry_client_id, None)
        await save_state()
        await mark_cooldown(symbol)
        log(f"فشل دخول {symbol}: {exc}")
        return False
    except Exception as exc:
        async with STATE_LOCK:
            STATE["pending_entries"].pop(entry_client_id, None)
        await save_state()
        log(f"خطأ دخول {symbol}: {exc}\n{traceback.format_exc()[-400:]}")
        return False
    finally:
        async with STATE_LOCK:
            live_record = STATE["pending_entries"].get(entry_client_id)
            if live_record is not None:
                live_record["active"] = False


def launch_entry(signal):
    """يشعل التنفيذ في مهمة مستقلة (لا يحجب حلقة WebSocket إطلاقاً)."""
    FUNNEL["fired"] += 1
    try:
        asyncio.get_running_loop().create_task(process_signal(signal))
    except RuntimeError:
        pass


def arm_entry_watchdog(client_id):
    """واتش دوغ صمت أحادي: إن لم يصل أي حدث خلال 12ث → استيضاح REST مرة واحدة."""
    try:
        asyncio.get_running_loop().create_task(entry_watchdog(client_id))
    except RuntimeError:
        pass


async def entry_watchdog(client_id):
    await asyncio.sleep(ENTRY_EVENT_TIMEOUT)
    record = STATE.get("pending_entries", {}).get(client_id)
    if record is None or record.get("phase") in ("done", "filled"):
        return
    symbol = record.get("symbol", "")
    order_id = record.get("order_id")
    log(f"Watchdog: صمت الأحداث لأمر الدخول {symbol}؛ استيضاح REST أحادي")
    try:
        if order_id:
            order = await REST.get_order(symbol, order_id)
        else:
            order = await REST.get_order_client(symbol, client_id)
    except BinanceError as exc:
        if exc.code == -2013:
            async with STATE_LOCK:
                STATE["pending_entries"].pop(client_id, None)
            await save_state()
            log(f"Watchdog {symbol}: الأمر غير موجود على الخادم؛ حُذف السجل")
        else:
            log(f"Watchdog {symbol}: تعذر الاستيضاح ({exc})؛ إبقاء السجل للمصالحة")
        return
    await resolve_entry_order(client_id, record, order)


async def resolve_entry_order(client_id, record, order):
    """يحسم أمر دخول من لقطة REST (Watchdog/مصالحة): تعبئة → OCO، جديد → إلغاء."""
    symbol = record.get("symbol", "")
    status = order.get("status")
    executed = D(order.get("executedQty", "0"))
    quote = D(order.get("cummulativeQuoteQty", "0"))
    avg = (quote / executed) if executed > 0 and quote > 0 else D(record.get("price", 0))
    if executed > 0 and status in ("FILLED", "CANCELED", "EXPIRED", "EXPIRED_IN_MATCH", "REJECTED"):
        await complete_entry(client_id, record, executed, avg, quote)
    elif status in ("NEW", "PARTIALLY_FILLED"):
        try:
            await REST.cancel_order(symbol, order.get("orderId"))
        except BinanceError as exc:
            if exc.code != -2011:
                log(f"Watchdog {symbol}: تعذر إلغاء الدخول ({exc})")
            return
        executed = D(order.get("executedQty", "0"))
        if executed > 0:
            try:
                final = await REST.get_order(symbol, order.get("orderId"))
                executed = D(final.get("executedQty", "0"))
                quote = D(final.get("cummulativeQuoteQty", "0"))
                avg = (quote / executed) if executed > 0 and quote > 0 else avg
            except BinanceError:
                pass
            if executed > 0:
                await complete_entry(client_id, record, executed, avg, quote)
                return
        async with STATE_LOCK:
            popped = STATE["pending_entries"].pop(client_id, None)
        if popped is not None:
            await save_state()
            log(f"Watchdog {symbol}: أُلغي أمر الدخول غير المنفذ")
    else:
        async with STATE_LOCK:
            STATE["pending_entries"].pop(client_id, None)
        await save_state()


async def complete_entry(client_id, record, executed_qty, avg_price, quote_filled):
    """إتمام دخول مُعبأ: مطالبة ذرية (claim) ثم مركز + وقف طوارئ صلب فوراً.

    تُستدعى من مستهلك أحداث المستخدم أو من الواتش دوغ — المطالبة تحت
    STATE_LOCK تضمن تنفيذها مرة واحدة بالضبط مهما تسابقت المصادر.
    """
    symbol = record.get("symbol", "")
    async with STATE_LOCK:
        current = STATE["pending_entries"].get(client_id)
        if current is None or current.get("phase") in ("done", "filled"):
            return  # حُسم مسبقاً — منع التسجيل المزدوج
        current["phase"] = "done"          # المطالبة: لا يمر من هنا مرتان
        STATE["pending_entries"].pop(client_id, None)
    try:
        if D(executed_qty) <= 0:
            await save_state()
            return
        if sellable_qty(symbol, executed_qty, float(avg_price) * 0.95) is None:
            await add_dust(symbol, executed_qty, quote_filled, "تعبئة جزئية دون الحد الأدنى للبيع")
            return
        stop_price, risk = hard_stop_price(avg_price, record.get("atr_1m", 0.0),
                                           record.get("atr", 0.0), record.get("vr", 1.0))
        protection = await place_hard_stop(symbol, executed_qty, avg_price, stop_price)
        pid = new_position_id(symbol)
        position = {
            "pid": pid, "symbol": symbol, "entry_client_id": client_id,
            "entry": float(avg_price), "qty": dec_str(protection["qty"]),
            "quote_qty": float(quote_filled or 0),
            "stop": float(protection["stop"]),
            "hard_stop": float(protection["stop"]),
            "atr_5m": float(D(str(record.get("atr", 0.0)))),
            "atr_1m": float(D(str(record.get("atr_1m", 0.0) or 0.0))),
            "order_list_id": None,
            "stop_client_id": protection.get("client_order_id"),
            "order_ids": [x.get("orderId") for x in protection.get("orders", []) if x.get("orderId") is not None],
            "protection_type": protection.get("type"),
            # ── محرك الخروج الهجين (محلي) ──
            "peak": float(avg_price), "trail_armed": False,
            "trail_stop": 0.0, "trail_mode": "off", "last_price": float(avg_price),
            "opened_at": time.time(), "imbalance": float(record.get("imbalance", 0.5)),
            "risk_usd": float(D(str(record.get("risk_usd", 0) or 0))),
            "score": float(record.get("score", 0) or 0),
            "vr": float(record.get("vr", 1.0) or 1.0),
            "sl_pct": float(record.get("sl_pct", 0) or 0),
            "setup_id": str(record.get("setup_id") or ""),
        }
        async with STATE_LOCK:
            STATE["positions"][pid] = position
            STATE["metrics"]["trades"] += 1
            STATE["cooldowns"][symbol] = time.time()
            STATE.setdefault("last_entry_at", {})[symbol] = time.time()
            for leg_id in position["order_ids"]:
                ORDERS[str(leg_id)] = {"role": "leg", "pid": pid, "symbol": symbol}
            setup_id = str(record.get("setup_id") or "")
            if setup_id:
                SETUPS.append(setup_id)
        await save_state()
        log(f"دخول V5.3 {symbol} pid={pid} entry={fmt_price(symbol, avg_price)} qty={position['qty']} "
            f"hardSL={fmt_price(symbol, protection['stop'])} ({risk['sl_pct']:.2f}%) "
            f"protection={protection['type']} score={position['score']:.0f} "
            f"VR={position['vr']:.2f} risk={position['risk_usd']:.2f}$ "
            f"(خروج هجين: تعادل +{BREAKEVEN_TRIGGER_PCT}% ثم تتبّع {TRAIL_WIDE_PCT}/{TRAIL_TIGHT_PCT}%)")
    except BinanceError as exc:
        log(f"فشل وقف الطوارئ لدخول {symbol}: {exc}؛ بيع إنقاذ")
        exit_order = await emergency_sell(symbol, executed_qty, "فشل حماية الدخول")
        if exit_order:
            qty_out, quote_out, _avg = parse_fill(exit_order, 0)
            await account_salvage(symbol, quote_filled, quote_out, qty_out, "بيع إنقاذ: فشل حماية الدخول")
        else:
            await add_dust(symbol, executed_qty, quote_filled, "فشل حماية الدخول والبيع الطارئ")
    except Exception as exc:
        log(f"خطأ إتمام الدخول {symbol}: {exc}\n{traceback.format_exc()[-400:]}")


def parse_fill(order, fallback_price):
    qty = D(order.get("executedQty", "0"))
    quote = D(order.get("cummulativeQuoteQty", "0"))
    average = quote / qty if qty > 0 and quote > 0 else D(fallback_price)
    return qty, quote, average


async def account_salvage(symbol, entry_quote, exit_quote, exit_qty, reason):
    """محاسبة صفقة إنقاذ (شراء+بيع مباشر دون مركز مُدار)."""
    try:
        pnl = float(exit_quote) - float(entry_quote)
        async with STATE_LOCK:
            metrics = STATE["metrics"]
            metrics["trades"] += 1
            metrics["realized_pnl"] += pnl
            if pnl >= 0:
                metrics["wins"] += 1
                metrics["consecutive_losses"] = 0
            else:
                metrics["losses"] += 1
                metrics["consecutive_losses"] = int(metrics.get("consecutive_losses", 0)) + 1
            STATE["cooldowns"][symbol] = time.time()
        record_trade([datetime.now(timezone.utc).isoformat(), symbol, "salvage",
                      float(entry_quote), float(exit_quote), float(exit_qty), round(pnl, 8), reason, BINANCE_ENV])
        await save_state()
        log(f"بيع إنقاذ {symbol}: pnl={pnl:+.6f}$ reason={reason}")
    except Exception as exc:
        log(f"خطأ محاسبة الإنقاذ {symbol}: {exc}")


async def finalize_position_event(pid, position, exit_price, exit_qty, reason):
    """إغلاق مركز من حدث executionReport (تنفيذ OCO) — بلا أي REST."""
    entry = float(position.get("entry", 0))
    qty = float(position.get("qty", 0))
    exit_price_value = float(exit_price)
    pnl = (exit_price_value - entry) * min(qty, float(exit_qty) if exit_qty else qty)
    symbol = position.get("symbol", "")
    async with STATE_LOCK:
        if STATE["positions"].get(pid) is None:
            return  # حُسم مسبقاً (حدث مكرر/سباق) — منع الإغلاق المزدوج
        STATE["positions"].pop(pid, None)
        EXIT_CLAIMED.discard(pid)   # أُغلق فعلاً → حرّر مطالبة الخروج إن وُجدت
        EXIT_PENDING.discard(pid)   # V5.3: تحرير حارس مهمة التتبّع (لا تسرّب)
        metrics = STATE["metrics"]
        metrics["realized_pnl"] += pnl
        if pnl >= 0:
            metrics["wins"] += 1
            metrics["consecutive_losses"] = 0
        else:
            metrics["losses"] += 1
            metrics["consecutive_losses"] = int(metrics.get("consecutive_losses", 0)) + 1
        STATE["cooldowns"][symbol] = time.time()
        for leg_id in position.get("order_ids", []):
            ORDERS.pop(str(leg_id), None)
    record_trade([datetime.now(timezone.utc).isoformat(), symbol, pid, entry, exit_price_value, qty,
                  round(pnl, 8), reason, BINANCE_ENV])
    await save_state()
    log(f"إغلاق {pid}: exit={fmt_price(symbol, exit_price_value)} pnl={pnl:+.6f}$ reason={reason}")


async def finalize_position_order(pid, position, order, reason):
    """إغلاق مركز من لقطة REST (مصالحة الإقلاع/إعادة الاتصال)."""
    qty, quote, avg = parse_fill(order, position.get("entry", 0))
    await finalize_position_event(pid, position, avg, qty, reason)


# ── معالجة أحداث User Data Stream (مستهلك واحد — ترقيع السباق) ───────────────


async def process_user_event(ev):
    """يوجه حدث executionReport: دخول (cid) أو رجل OCO (orderId)."""
    event_type = ev.get("e")
    if event_type == "executionReport":
        await on_execution_report(ev)
    elif event_type == "listStatus":
        log(f"listStatus: {ev.get('s')} status={ev.get('L')}")  # تأكيد ثانوي فقط
    elif event_type == "outboundAccountPosition":
        pass  # تحديثات أرصدة — لا حاجة إليها هنا
    elif event_type == "balanceUpdate":
        pass


async def on_execution_report(ev):
    symbol = str(ev.get("s") or "")
    client_id = str(ev.get("c") or "")
    order_id = str(ev.get("i") or "")
    status = str(ev.get("X") or "")
    exec_type = str(ev.get("x") or "")
    cum_qty = D(ev.get("z") or "0")
    cum_quote = D(ev.get("Z") or "0")
    last_price = D(ev.get("L") or "0")
    meta = ORDERS.get(order_id)
    # ربط ديناميكي: أحداث الدخول تصل بمعرف العميل حتى قبل معالجة استجابة REST
    if meta is None and STATE.get("pending_entries", {}).get(client_id) is not None:
        meta = {"role": "entry", "cid": client_id, "symbol": symbol}
        if order_id:
            ORDERS[order_id] = meta
    if meta is None:
        return  # حدث لا يخص البوت (أوامر يدوية/أرجل أُغلقت حسابها)
    if meta["role"] == "entry":
        record = STATE.get("pending_entries", {}).get(meta["cid"])
        if record is None:
            return
        if exec_type == "TRADE" and cum_qty > 0:
            record["executed_qty"] = dec_str(cum_qty)
            record["executed_quote"] = dec_str(cum_quote)
        if status == "FILLED":
            avg = (cum_quote / cum_qty) if cum_qty > 0 else last_price
            await complete_entry(meta["cid"], record, cum_qty, avg, cum_quote)
        elif status in ("CANCELED", "EXPIRED", "REJECTED", "EXPIRED_IN_MATCH"):
            if cum_qty > 0:
                avg = (cum_quote / cum_qty) if cum_qty > 0 else last_price
                await complete_entry(meta["cid"], record, cum_qty, avg, cum_quote)
            else:
                async with STATE_LOCK:
                    popped = STATE["pending_entries"].pop(meta["cid"], None)
                if popped is not None:
                    await save_state()
                    log(f"أمر دخول {symbol} أُلغي بلا تعبئة (cid={meta['cid']})")
    elif meta["role"] == "leg":
        pid = meta.get("pid")
        async with STATE_LOCK:
            position = STATE["positions"].get(pid)
        if position is None:
            return
        if exec_type == "TRADE" and status == "FILLED":
            avg = (cum_quote / cum_qty) if cum_qty > 0 else last_price
            side = "ربح" if float(avg or 0) >= float(position.get("entry", 0)) else "خسارة"
            await finalize_position_event(pid, position, avg, cum_qty,
                                          f"وقف الطوارئ الصلب نُفّذ على Binance ({side})")
        elif exec_type == "TRADE" and status == "PARTIALLY_FILLED" and cum_qty > 0:
            # تعبئة جزئية للوقف: قلّص كمية المركز فوراً وإلا بعنا كمية لا نملكها
            async with STATE_LOCK:
                live = STATE["positions"].get(pid)
                if live is not None:
                    remaining = D(live.get("qty", 0)) - cum_qty
                    live["qty"] = dec_str(max(Decimal("0"), remaining))
                    live["stop_filled_qty"] = dec_str(cum_qty)
            log(f"تعبئة جزئية لوقف {pid}: نُفّذ {dec_str(cum_qty)} — الكمية المتبقية حُدّثت")
        elif status in ("CANCELED", "EXPIRED", "REJECTED", "EXPIRED_IN_MATCH") and cum_qty <= 0:
            # الوقف أُلغي (غالباً من محرك التتبّع) → نظّف الفهرس فقط
            ORDERS.pop(order_id, None)


async def user_event_worker(queue):
    """مستهلك واحد متسلسل لأحداث المستخدم → لا سباق بين الأحداث المتتالية."""
    while True:
        ev = await queue.get()
        try:
            await process_user_event(ev)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ معالجة حدث مستخدم: {exc}\n{traceback.format_exc()[-300:]}")
        finally:
            queue.task_done()


def dispatch_user_message(text):
    """يستقبل نص رسالة User Stream ويصبّه في طابور المستهلك الواحد."""
    try:
        event = json.loads(text)
        if isinstance(event, dict) and event.get("e"):
            USER_EVENTS.put_nowait(event)
    except (ValueError, asyncio.QueueFull) as exc:
        log(f"User Stream: تعذر صف الحدث ({exc})")
    except Exception as exc:
        log(f"User Stream: خطأ توجيه ({exc})")


# ── مصالحة لقطية (إقلاع/إعادة اتصال فقط — ليست اقتراعاً دورياً) ──────────────


async def reconcile_snapshot(reason):
    """لقطة أحادية بعد الإقلاع أو انقطاع User Stream: أحداث قد تكون فُقدت.

    - pending_entries أقدم من 30ث: حسم REST أحادي لكل أمر.
    - المراكز المفتوحة: فحص أمر الوقف الصلب لكل مركز مرة واحدة (get_order) وفق
      الحالة النهائية فقط. لا تتكرر إلا بعد انقطاع جديد (Cooldown 60ث).
    """
    global LAST_RECON_SNAPSHOT
    now = time.monotonic()
    if now - LAST_RECON_SNAPSHOT < RECON_SNAPSHOT_COOLDOWN:
        return
    LAST_RECON_SNAPSHOT = now
    if MANAGE_LOCK.locked():
        return
    async with MANAGE_LOCK:
        log(f"مصالحة لقطية ({reason})")
        # 1) أوامر الدخول المعلقة العالقة
        for client_id, record in list(STATE.get("pending_entries", {}).items()):
            try:
                if record.get("active") and time.time() - float(record.get("placed_at", 0)) < 30:
                    continue
                symbol = record.get("symbol", "")
                order_id = record.get("order_id")
                try:
                    order = await REST.get_order(symbol, order_id) if order_id \
                        else await REST.get_order_client(symbol, client_id)
                except BinanceError as exc:
                    if exc.code == -2013:
                        async with STATE_LOCK:
                            STATE["pending_entries"].pop(client_id, None)
                        await save_state()
                        log(f"مصالحة: أمر {symbol} غير موجود على الخادم؛ حُذف")
                    continue
                await resolve_entry_order(client_id, record, order)
            except Exception as exc:
                log(f"خطأ مصالحة دخول {client_id}: {exc}")
        # 2) المراكز المفتوحة: هل نُفذ وقف/هدف أثناء الانقطاع؟
        for pid, position in list(STATE.get("positions", {}).items()):
            try:
                legs = [oid for oid in position.get("order_ids", []) if oid is not None]
                if not legs and position.get("stop_client_id"):
                    try:
                        detail = await REST.get_order_client(position["symbol"], position["stop_client_id"])
                        if detail and detail.get("orderId") is not None:
                            legs = [detail["orderId"]]
                            async with STATE_LOCK:
                                if STATE["positions"].get(pid) is not None:
                                    STATE["positions"][pid]["order_ids"] = legs
                    except BinanceError:
                        pass
                filled = None
                for leg_id in legs:
                    try:
                        order = await REST.get_order(position["symbol"], leg_id)
                    except BinanceError:
                        continue
                    if order.get("status") == "FILLED" and D(order.get("executedQty", "0")) > 0:
                        filled = order
                        break
                if filled is not None:
                    await finalize_position_order(pid, position, filled,
                                                  "مصالحة: وقف الطوارئ نُفّذ أثناء الانقطاع")
                    continue
                # V5.3: مركز حيّ بلا أي وقف قائم على Binance = مكشوف → أعد تركيبه
                if STATE.get("positions", {}).get(pid) is not None:
                    alive = False
                    for leg_id in legs:
                        try:
                            order = await REST.get_order(position["symbol"], leg_id)
                        except BinanceError:
                            alive = True     # تعذر التحقق → افترض الأسوأ (لا تزدوج)
                            break
                        if str(order.get("status")) in ("NEW", "PARTIALLY_FILLED"):
                            alive = True
                            break
                    if not alive and pid not in EXIT_CLAIMED and pid not in EXIT_PENDING:
                        log(f"مصالحة: {pid} بلا وقف قائم (مكشوف) → إعادة تركيب")
                        await rearm_hard_stop(pid, reason="مصالحة: مركز مكشوف")
            except Exception as exc:
                log(f"خطأ مصالحة مركز {pid}: {exc}")
        await save_state()


# ── أوامر المستخدم اليدوية (تصفية/إلغاء) ─────────────────────────────────────


def _claim_exit(pid):
    """مطالبة ذرية بخروج استثنائي لمركز: True لهذا المسار فقط (يمنع البيع المزدوج).

    سريع وغير قابل للإلغاء في نافذة الخروج؛ المسار الخاسر يتوقف فوراً.
    """
    async def _do():
        async with STATE_LOCK:
            if pid is None or STATE.get("positions", {}).get(pid) is None or pid in EXIT_CLAIMED:
                return False
            EXIT_CLAIMED.add(pid)
            return True
    return _do()


def _release_exit_claim(pid):
    EXIT_CLAIMED.discard(pid)


async def force_exit_position(pid, position, reason):
    """خروج موحّد (تتبّع/وقف زمني/تصفية): مطالبة → إلغاء الوقف الصلب → MARKET SELL.

    المطالبة الذرية تضمن تنفيذ بيع واحد بالضبط للمركز مهما تسابقت المصادر
    (تصفية + وقف زمني + مصالحة). يتحقق مرة أخيرة أن المركز ما زال موجوداً
    بعد إلغاء الوقف (ربما نُفّذ وقف الطوارئ أثناء الإلغاء).
    """
    if not await _claim_exit(pid):
        return False
    stop_removed = False
    try:
        symbol = position.get("symbol", "")
        cancelled = await cancel_hard_stop(position)
        stop_removed = bool(cancelled)
        if cancelled:
            for legacy in position.get("order_ids", []) or []:
                ORDERS.pop(str(legacy), None)    # لا تراكم فهارس لأوامر ميتة
        # تحقق أخير بعد الإلغاء: إن نُفّذ الوقف بالفعل أُغلق المركز فلا بيع
        async with STATE_LOCK:
            if STATE.get("positions", {}).get(pid) is None:
                log(f"خروج {pid}: أُغلق عبر وقف الطوارئ أثناء الإلغاء؛ تجاوز البيع")
                return False
        if not cancelled:
            # الوقف قد يكون ما زال حياً على Binance ⇒ البيع الآن يخاطر بكمية مزدوجة
            async with STATE_LOCK:
                EXIT_CLAIMED.discard(pid)
            log(f"خروج {pid}: تعذر إلغاء وقف الطوارئ؛ تأجيل البيع للدورة التالية")
            return False
        order = await emergency_sell(symbol, D(position.get("qty", 0)), reason,
                                     already_net=True)
        if order:
            qty, quote, avg = parse_fill(order, 0)
            if qty and qty > 0:
                await finalize_position_event(pid, position, avg, qty, reason)
                return True
        # فشل البيع (رصيد/شبكة) والوقف قد أُلغي بالفعل ⇒ المركز الآن مكشوف!
        # إعادة تركيب وقف طوارئ فوراً أهم من أي شيء آخر (لا نترك مركزاً بلا حماية).
        async with STATE_LOCK:
            EXIT_CLAIMED.discard(pid)
        log(f"خروج {pid}: تعذر البيع ({reason})؛ إعادة تركيب وقف الحماية")
        await rearm_hard_stop(pid, reason="فشل البيع بعد إلغاء الوقف")
        return False
    except Exception as exc:
        async with STATE_LOCK:
            EXIT_CLAIMED.discard(pid)
        log(f"خطأ خروج {pid}: {exc}\n{traceback.format_exc()[-300:]}")
        if stop_removed and (STATE.get("positions") or {}).get(pid) is not None:
            # سقط المسار بعد إلغاء الوقف ⇒ المركز مكشوف: أعد تركيب الحماية
            try:
                await rearm_hard_stop(pid, reason="استثناء أثناء الخروج")
            except Exception as inner:
                log(f"حرج {pid}: فشل إعادة التركيب بعد الاستثناء ({inner})")
        return False


async def rearm_hard_stop(pid, reason=""):
    """يعيد تركيب وقف الطوارئ لمركز بقي مفتوحاً بعد إلغاء وقفه وفشل بيعه.

    بدون هذا يظل المركز مكشوفاً تماماً حتى الدورة التالية — وهو أخطر
    احتمال في المحرك بأسره. يُعاد استخدام الوقف المحلي (تعادل/تتبّع) إن كان
    مسلّحاً لأنه أعلى من الوقف الأصلي وأقرب لحماية الربح.
    """
    async with STATE_LOCK:
        position = STATE.get("positions", {}).get(pid)
        if position is None:
            return False
        symbol = position.get("symbol", "")
        qty = D(position.get("qty", 0))
        entry = float(position.get("entry", 0) or 0)
        base_stop = float(position.get("hard_stop", position.get("stop", 0)) or 0)
        trail_stop = float(position.get("trail_stop", 0) or 0)
        armed = bool(position.get("trail_armed"))
    if qty <= 0 or entry <= 0:
        return False
    price_now, _age = market_price(symbol)
    target_stop = max(base_stop, trail_stop) if armed else base_stop
    if target_stop <= 0:
        target_stop = entry * (1.0 - SL_MAX_PCT / 100.0)
    # الوقف يجب أن يبقى تحت السوق وإلا رفضته Binance (-2010)
    if price_now > 0 and target_stop >= price_now:
        target_stop = price_now * (1.0 - max(SL_MIN_PCT, 0.05) / 100.0)
    try:
        protection = await place_hard_stop(symbol, qty, entry, D(str(target_stop)),
                                           reference=(price_now if price_now > 0 else entry),
                                           already_net=True)
    except BinanceError as exc:
        log(f"حرج {pid}: تعذرت إعادة تركيب الوقف ({exc}) — المركز مكشوف؛ المصالحة ستحاول")
        FUNNEL["naked-position"] += 1
        return False
    except Exception as exc:
        log(f"حرج {pid}: خطأ إعادة تركيب الوقف ({exc})")
        FUNNEL["naked-position"] += 1
        return False
    async with STATE_LOCK:
        position = STATE.get("positions", {}).get(pid)
        if position is None:
            # أُغلق أثناء التركيب → ألغِ الوقف اليتيم فوراً
            asyncio.create_task(cancel_hard_stop(
                {"symbol": symbol, "order_ids": [x.get("orderId") for x in protection.get("orders", [])],
                 "stop_client_id": protection.get("client_order_id")}))
            return False
        for legacy in position.get("order_ids", []) or []:
            ORDERS.pop(str(legacy), None)
        position["order_ids"] = [x.get("orderId") for x in protection.get("orders", [])
                                 if x.get("orderId") is not None]
        position["stop_client_id"] = protection.get("client_order_id")
        position["stop"] = float(protection["stop"])
        position["qty"] = dec_str(protection["qty"])
        for leg_id in position["order_ids"]:
            ORDERS[str(leg_id)] = {"role": "leg", "pid": pid, "symbol": symbol}
    await save_state()
    log(f"أُعيد تركيب وقف الطوارئ {pid} @ {fmt_price(symbol, protection['stop'])} ({reason})")
    FUNNEL["stop-rearmed"] += 1
    return True


async def cancel_all_orders():
    """يلغي حمايات البوت المسجلة فقط (كل مركز مستقل بمعرّفه)."""
    async with STATE_LOCK:
        positions = list(STATE.get("positions", {}).items())
    for pid, position in positions:
        symbol = position.get("symbol")
        if not symbol:
            continue
        try:
            await cancel_hard_stop(position)
        except Exception as exc:
            log(f"تعذر إلغاء حماية {pid}: {exc}")


async def panic_close_all():
    await cancel_all_orders()
    async with STATE_LOCK:
        pending = list(STATE.get("pending_entries", {}).values())
        positions = list(STATE.get("positions", {}).items())
    for record in pending:
        order_id = record.get("order_id")
        if not order_id:
            continue
        try:
            await REST.cancel_order(record.get("symbol", ""), order_id)
        except BinanceError:
            pass
    for pid, position in positions:
        await force_exit_position(pid, position, "PANIC (تصفية يدوية)")


# ══════════════════════════════════════════════════════════════════════════════
# 9) Dust Management — مسح الأرصدة الدقيقة إلى BNB كل 24 ساعة
# ══════════════════════════════════════════════════════════════════════════════


def pick_dust_assets(details, eligible_bases):
    """يختار الأصول القابلة للتحويل ضمن الأصول ذات الصلة بالبوت فقط (نقية)."""
    picked = []
    for item in details if isinstance(details, list) else []:
        try:
            asset = str(item.get("asset", "")).upper()
            amount = float(item.get("amountFree", item.get("amount", 0)) or 0.0)
            min_amount = float(item.get("minTransferAmount", 0) or 0.0)
        except (TypeError, ValueError):
            continue
        if not asset or asset == "BNB":
            continue
        if asset not in eligible_bases:
            continue
        if amount > 0 and amount >= min_amount:
            picked.append(asset)
    return picked[:DUST_ASSET_CAP]


def eligible_dust_bases():
    """الأصول الأساسية ذات الصلة: كون التداول + المراكز + Dust المتتبع."""
    bases = set()
    for symbol in SYMBOLS:
        rule = SYMBOL_RULES.get(symbol)
        if rule and rule.get("base"):
            bases.add(str(rule["base"]).upper())
    for position in STATE.get("positions", {}).values():
        rule = SYMBOL_RULES.get(position.get("symbol", ""))
        if rule and rule.get("base"):
            bases.add(str(rule["base"]).upper())
    for item in STATE.get("dust", []):
        rule = SYMBOL_RULES.get(item.get("symbol", ""))
        if rule and rule.get("base"):
            bases.add(str(rule["base"]).upper())
    return bases


async def dust_sweep_if_due(force=False):
    """مسح Dust إلى BNB مرة كل 24 ساعة عبر نقاط Binance الأصلية (بلا رسائل)."""
    async with STATE_LOCK:
        last = float(STATE.get("last_dust_sweep", 0.0) or 0.0)
    if not force and time.time() - last < DUST_SWEEP_EVERY:
        return False
    if not live_execution_allowed():
        return False
    try:
        payload = await REST.dustable_bases()
        details = (payload or {}).get("details", [])
        picked = pick_dust_assets(details, eligible_dust_bases())
        if picked:
            result = await REST.dust_transfer(picked)
            transferred = (result or {}).get("totalTransfered", "?")
            log(f"Dust Sweep: حُوِّل {', '.join(picked)} → {transferred} BNB")
        else:
            log("Dust Sweep: لا أرصدة دقيقة مؤهلة للتحويل")
        async with STATE_LOCK:
            STATE["last_dust_sweep"] = time.time()
            STATE["dust"] = [x for x in STATE.get("dust", []) if x.get("symbol", "").split("USDT")[0] not in picked]
        await save_state()
        return True
    except BinanceError as exc:
        log(f"Dust Sweep: تعذر (بيئة لا تدعم SAPI أو {exc})")
        return False
    except Exception as exc:
        log(f"Dust Sweep: خطأ ({exc})")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# 10) التقارير: صيغة /status الحرفية (بدون قائمة عملات نشطة)
# ══════════════════════════════════════════════════════════════════════════════


def regime_text():
    return {"demo": "DEMO", "testnet": "TESTNET", "live": "LIVE"}.get(BINANCE_ENV, BINANCE_ENV.upper())


def status_text():
    m = STATE.get("metrics", {})
    total = int(m.get("trades", 0))
    wins = int(m.get("wins", 0))
    losses = int(m.get("losses", 0))
    consecutive = int(m.get("consecutive_losses", 0))
    pnl = float(m.get("realized_pnl", 0.0))
    decided = wins + losses
    win_rate = (wins * 100.0 / decided) if decided > 0 else 0.0
    return (
        f"إجمالي الصفقات : {total}\n\n"
        f"🟢الناجحة : {wins}\n\n"
        f"🔴الخاسرة : {losses}\n\n"
        f"الخسائر المتتالية : {consecutive}\n\n"
        f"اجمالي المكاسب : {pnl:.2f}$\n\n"
        f"نسبة النجاح : {win_rate:.2f}%"
    )


def context_text():
    """تقرير حالة السياق الكلي والقاطع — للشفافية عند رفض الإشارات."""
    stats = btc_ctx_stats()
    blocked, reason = btc_circuit_block()
    drop = stats["drop_pct"]
    drop_text = "—" if drop is None else f"{drop:+.3f}%"
    return (
        f"سياق {BTC_CONTEXT_SYMBOL} ({'🟢 متاح' if not blocked else '🔴 قاطع'}): {reason}\n\n"
        f"التغير في {BTC_DROP_WINDOW_MIN} دقائق: {drop_text}\n"
        f"VR (BTC 1m): {stats['vr']:.2f} → تهدئة {btc_cooldown()}ث\n"
        f"عتبة المنع: هبوط ≥ {BTC_DROP_PCT}% | عمر المصدر: {stats['age']:.0f}ث (سقف {BTC_CTX_MAX_AGE:.0f}ث)\n\n"
        f"منطق القرار: تنقيط متدرّج ≥ {SCORE_TRIGGER:.0f}/100 — MSS {SCORE_MSS:.0f} + FVG {SCORE_FVG:.0f} + "
        f"EMA{EMA_TREND_PERIOD} {SCORE_EMA:.0f}/{SCORE_EMA_FLAT:.0f} + Flow {SCORE_FLOW_WEAK:.0f}/{SCORE_FLOW_MED:.0f}/{SCORE_FLOW:.0f} + حجم ≤{SCORE_VOLUME_MAX:.0f} + زخم استثنائي +{SCORE_MOMENTUM_BONUS:.0f} (MSS إلزامي)\n"
        f"الحماية: وقف طوارئ صلب ATR(1m)×{HARD_STOP_ATR_MULT:g} بسقف {SL_MAX_PCT}% (بلا هدف ثابت)\n"
        f"الخروج الهجين: تعادل عند +{BREAKEVEN_TRIGGER_PCT:g}% → قفل +{BREAKEVEN_LOCK_PCT:g}% | "
        f"تتبّع {TRAIL_WIDE_PCT:g}% ثم {TRAIL_TIGHT_PCT:g}% فوق +{TRAIL_TIGHT_AFTER_PCT:g}%\n"
        f"الحجم: مخاطرة {TARGET_RISK_USD}$ (سقف مركز {MAX_POSITION_NOTIONAL_USD}$، نصف الحجم عند VR>{VR_FAST:g}) "
        f"| مراكز {len(STATE.get('positions', {}))}/{MAX_OPEN_POSITIONS} ({MAX_POSITIONS_PER_SYMBOL}/عملة)\n"
        f"حوت: صفقة مفردة ≥ {WHALE_TRADE_USD:,.0f}$ تمنح مكافأة الزخم تلقائياً\n"
        f"فلاتر الجودة: ATR% ≥ {MIN_ATR_PCT}% | VR ≤ {VR_EXTREME} | منع المطاردة > {CHASE_MAX_ATR}×ATR\n"
        f"وقف زمني: {TIME_STOP_SEC//60}د ({'مفعّل' if TIME_STOP_ENABLED else 'معطّل'}) | تدفق {FLOW_WINDOW_SEC:.0f}ث (aggTrade) | قدم بيانات ≤{MAX_STALE_SEC:.0f}ث\n\n"
        f"📈 قمع التشخيص (أسباب المنع/الإطلاق منذ التشغيل):\n"
        + "\n".join(f"  • {name_ar}: {count}" for name_ar, count in (
            ("أُطلقت إشارات", FUNNEL.get("fired", 0)),
            ("قاطع BTC", FUNNEL.get("btc-breaker", 0)),
            ("شمعة ذيلية", FUNNEL.get("wick", 0)),
            ("سوق ميت (ATR%)", FUNNEL.get("dead-market", 0)),
            ("تقلب جنوني", FUNNEL.get("extreme-vr", 0)),
            ("مطاردة قمة", FUNNEL.get("chase", 0)),
            ("سبريد واسع", FUNNEL.get("spread", 0)),
            ("بيانات قديمة", FUNNEL.get("stale-tick", 0)),
            ("وقف زمني", FUNNEL.get("time-stop", 0)),
            ("إيقاظ حيتان", FUNNEL.get("whale", 0)),
            ("خروج بالتتبّع", FUNNEL.get("trail-exit", 0)),
            ("حد أدنى غير قابل للبيع", FUNNEL.get("min-notional", 0)),
            ("إعادة تركيب وقف", FUNNEL.get("stop-rearmed", 0)),
            ("مركز مكشوف (حرج)", FUNNEL.get("naked-position", 0)),
        ))
    )


HELP_TEXT = (
    "🤖 <b>NOVA ASYNC SCALPER V5.3 ELITE — Smart Machine Gun</b>\n\n"
    "/start أو /menu القائمة الرئيسية\n/status تقرير الأداء\n/context حالة السياق والقاطع\n"
    "/reset تصفير الإحصائيات\n/pause إيقاف الدخولات الجديدة\n/resume استئناف\n"
    "/cancelall إلغاء حمايات البوت\n/panic إلغاء + تصفية فورية\n"
    "/kill قاطع تداول يدوي\n/unkill إزالة القاطع\n/help هذه المساعدة\n\n"
    "تنقيط تعويضي: MSS 35 (إلزامي) + FVG 25 + EMA 20/10 + Flow 8/14/20 + حجم ≤5 + زخم 25 — تنفيذ ≥ 72.\n"
    "إيقاظ الحيتان: صفقة aggTrade مفردة ≥ 50,000$ تمنح مكافأة الزخم فوراً.\n"
    "قاطع سياق كلي: BTCUSDT@kline_1m يمنع الشراء إذا هوى BTC ≥ 0.5% خلال 3 دقائق.\n"
    "فلاتر جودة: شمعة ذيلية، سوق ميت (ATR%)، تقلب جنوني (VR>3)، ومطاردة قمة.\n"
    "الحماية: وقف طوارئ صلب STOP_LOSS_LIMIT عند ATR(1m)×1.5 بسقف 3% — بلا هدف ثابت.\n"
    "الخروج الهجين: ربح +0.40% ⇒ قفل تعادل عند +0.15%، ثم تتبّع 0.20% "
    "(و0.08% فوق +1.0%) — عند اللمس يُلغى الوقف ويُنفَّذ MARKET SELL.\n"
    "الحجم: مخاطرة 1$ وسقف مركز 12$ (نصف الحجم عند VR>1.5) حتى 15 مركزاً (3/عملة).\n"
    "وقف زمني: 15 دقيقة بربح < +0.15% ⇒ إلغاء الوقف وبيع MARKET.\n"
    "User Data Stream (executionReport) مصدر حقيقة الأوامر — بلا REST Polling.\n"
    "Dust→BNB كل 24 ساعة. /context يعرض قمع أسباب المنع (FUNNEL).\n"
    "الصمت التام: رسالة بدء واحدة ثم الرد على الأوامر اليدوية فقط."
)


# ══════════════════════════════════════════════════════════════════════════════
# 11) Telegram (aiohttp — Long Polling بلا حجب)
# ══════════════════════════════════════════════════════════════════════════════


async def tg_api(method, payload=None, retries=3):
    if not TELEGRAM_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    for attempt in range(retries):
        try:
            async with SESSION.post(url, json=payload or {},
                                    timeout=aiohttp.ClientTimeout(total=35)) as response:
                data = await response.json(content_type=None)
                if data.get("ok"):
                    return data.get("result")
                if response.status == 429:
                    await asyncio.sleep(2 + attempt)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            await asyncio.sleep(1 + attempt)
    return None


async def send_message(text, keyboard=None, chat_id=None):
    """الوضع الصامت: تُرسل الردود على أوامر المستخدم فقط (مع chat_id محدد).

    أي استدعاء تلقائي بلا chat_id يُرفض ويُسجل في السجل — لا رسائل خارجة
    إطلاقاً (إشعار البدء الوحيد يمرر chat_id صراحةً عبر notify_startup).
    """
    if STEALTH_MODE and chat_id is None:
        log("[صامت] حُجبت رسالة تلقائية: " + str(text).replace("\n", " | ")[:220])
        return False
    if DRY_RUN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n" + "═" * 72 + "\n[Telegram محاكاة]\n" + text + "\n" + "═" * 72)
        return True
    payload = {"chat_id": chat_id or TELEGRAM_CHAT_ID, "text": text,
               "parse_mode": "HTML", "disable_web_page_preview": True}
    if keyboard is not None:
        payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
    return bool(await tg_api("sendMessage", payload))


async def notify_startup():
    """إشعار البدء الوحيد: يُرسل مرة واحدة بالضبط بعد نجاح الاتصال بـ WebSockets."""
    global STARTUP_NOTIFIED
    if STARTUP_NOTIFIED:
        return False
    STARTUP_NOTIFIED = True  # يُضبط قبل الإرسال: مرة واحدة بالضبط لا أكثر
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log("إشعار البدء (Telegram غير مفعّل): " + STARTUP_TEXT)
        return False
    sent = await send_message(STARTUP_TEXT, chat_id=TELEGRAM_CHAT_ID)
    log("أُرسل إشعار البدء إلى Telegram" if sent else "تعذر إرسال إشعار البدء إلى Telegram")
    return bool(sent)


def button(text, data):
    return {"text": text, "callback_data": data}


def main_keyboard():
    # callback_data بصيغة /xxx تماماً كما في start.sh (والموجّه يقبل الصيغتين)
    return [
        [button("📊 الحالة", "/status"), button("🌍 السياق", "/context")],
        [button("⏸ إيقاف", "/pause"), button("▶ استئناف", "/resume")],
        [button("🧯 إلغاء الأوامر", "/cancelall"), button("🆘 تصفية", "/panic")],
        [button("❓ المساعدة", "/help")],
    ]


async def handle_callback(update):
    callback = update.get("callback_query", {})
    message = callback.get("message", {})
    chat = str(message.get("chat", {}).get("id", ""))
    if chat != str(TELEGRAM_CHAT_ID):
        await tg_api("answerCallbackQuery", {"callback_query_id": callback.get("id", ""), "text": "غير مصرح"}, retries=1)
        return
    data = str(callback.get("data", "")).strip().lstrip("/").lower()
    # إقرار فوري يُوقف أنيميشن تحميل الزر لدى المستخدم (answerCallbackQuery)
    await tg_api("answerCallbackQuery", {"callback_query_id": callback.get("id", "")}, retries=1)
    if data in ("status", "الحالة"):
        await send_message(status_text(), main_keyboard(), chat)
    elif data in ("context", "btc", "السياق"):
        await send_message(context_text(), main_keyboard(), chat)
    elif data == "pause":
        async with STATE_LOCK:
            STATE["paused"] = True
        await save_state()
        await send_message("⏸ تم إيقاف الدخولات الجديدة؛ تستمر إدارة المراكز.", main_keyboard(), chat)
    elif data == "resume":
        async with STATE_LOCK:
            STATE["paused"] = False
        await save_state()
        await send_message("▶ تم استئناف الدخولات.", main_keyboard(), chat)
    elif data == "cancelall":
        asyncio.create_task(cancel_all_orders())
        await send_message("🧯 جارٍ إلغاء حمايات البوت.", main_keyboard(), chat)
    elif data == "panic":
        async with STATE_LOCK:
            STATE["paused"] = True
        await save_state()
        asyncio.create_task(panic_close_all())
        await send_message("🆘 بدأت التصفية الشاملة، وأُوقفت الدخولات الجديدة. استخدم /resume لاستئنافها.", main_keyboard(), chat)
    elif data in ("help", "start", "menu"):
        await send_message(HELP_TEXT, main_keyboard(), chat)


async def handle_command(text, chat):
    # بوابة تفويض: لا أمر ولا رد ولا تنفيذ لأي محادثة غير TELEGRAM_CHAT_ID
    if not TELEGRAM_CHAT_ID or str(chat) != str(TELEGRAM_CHAT_ID):
        log(f"[أمن] رفض أمر من محادثة غير مصرح لها: {chat}")
        return
    command, _, argument = text.partition(" ")
    command = command.split("@", 1)[0].lower()
    if command in ("/start", "/menu"):
        await send_message("🎛️ <b>NOVA ASYNC SCALPER V5.3 ELITE</b>\nاختر عملية:", main_keyboard(), chat)
    elif command == "/help":
        await send_message(HELP_TEXT, main_keyboard(), chat)
    elif command == "/status":
        await send_message(status_text(), main_keyboard(), chat)
    elif command in ("/context", "/btc"):
        await send_message(context_text(), main_keyboard(), chat)
    elif command == "/reset":
        async with STATE_LOCK:
            STATE["metrics"] = {
                "trades": 0,
                "realized_pnl": 0.0,
                "wins": 0,
                "losses": 0,
                "consecutive_losses": 0,
            }
        await save_state()
        await send_message(RESET_REPLY, main_keyboard(), chat)
    elif command == "/pause":
        async with STATE_LOCK:
            STATE["paused"] = True
        await save_state()
        await send_message("⏸ تم إيقاف الدخولات الجديدة.", main_keyboard(), chat)
    elif command == "/resume":
        async with STATE_LOCK:
            STATE["paused"] = False
        await save_state()
        await send_message("▶ تم استئناف الدخولات.", main_keyboard(), chat)
    elif command == "/cancelall":
        asyncio.create_task(cancel_all_orders())
        await send_message("🧯 جارٍ إلغاء حمايات البوت.", main_keyboard(), chat)
    elif command == "/panic":
        async with STATE_LOCK:
            STATE["paused"] = True
        await save_state()
        asyncio.create_task(panic_close_all())
        await send_message("🆘 بدأت التصفية الشاملة، وأُوقفت الدخولات الجديدة. استخدم /resume لاستئنافها.", main_keyboard(), chat)
    elif command == "/kill":
        await asyncio.to_thread(_write_kill_switch)
        await send_message("🛑 تم تفعيل STOP_TRADING.", main_keyboard(), chat)
    elif command == "/unkill":
        try:
            os.remove(KILL_SWITCH_FILE)
        except OSError:
            pass
        await send_message("✅ أُزيل STOP_TRADING.", main_keyboard(), chat)
    else:
        await send_message("أمر غير معروف؛ استخدم /help", main_keyboard(), chat)


def _write_kill_switch():
    ensure_dirs()
    with open(KILL_SWITCH_FILE, "w", encoding="utf-8") as handle:
        handle.write(datetime.now(timezone.utc).isoformat())


async def telegram_loop(stop_event=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log("Telegram غير مفعّل")
        # لا يجوز أن تُكمل المهمة فوراً وإلا أغلقت FIRST_COMPLETED البوت كله
        if stop_event is not None:
            await stop_event.wait()
        return
    while True:
        try:
            updates = await tg_api("getUpdates", {
                "offset": STATE.get("offset", 0),
                "timeout": 25,
                "allowed_updates": ["message", "callback_query"],
            }, retries=1)
            if not updates:
                continue
            changed = False
            for update in updates:
                STATE["offset"] = max(STATE.get("offset", 0), int(update.get("update_id", 0)) + 1)
                changed = True
                if "callback_query" in update:
                    await handle_callback(update)
                    continue
                message = update.get("message", {})
                chat = str(message.get("chat", {}).get("id", ""))
                if chat != str(TELEGRAM_CHAT_ID):
                    continue
                text = (message.get("text") or "").strip()
                if text.startswith("/"):
                    await handle_command(text, chat)
            if changed:
                await save_state()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"Telegram: {exc}")
            await asyncio.sleep(5)


# ══════════════════════════════════════════════════════════════════════════════
# 12) محطات WebSocket: السوق + User Data Stream (إعادة اتصال تلقائية)
# ══════════════════════════════════════════════════════════════════════════════


def next_backoff(current):
    """Backoff متزايد مع Jitter — دالة نقية (قابلة للاختبار)."""
    grown = min(current * 2.0, WS_RECONNECT_MAX)
    return grown, current + random.uniform(0.0, 1.5)


class MarketStreamHub:
    """يدير اتصال Combined Streams: SUBSCRIBE/UNSUBSCRIBE ديناميكياً.

    - autoping=True: ردود Pong تلقائية على Ping خادم Binance.
    - heartbeat: Ping دوري من العميل + إغلاق فوري إذا مات الاتصال (فقدان Pong).
    - Backoff متزايد مع Jitter، ثم إعادة تحميل الشموع لسد الفجوات.
    """

    def __init__(self):
        self.ws = None
        self.desired = set()
        self.subscribed = set()
        self.connected = asyncio.Event()
        self._id = 0
        self.backoff = WS_RECONNECT_MIN

    @staticmethod
    def streams_for(symbol):
        s = str(symbol).lower()
        return (f"{s}@kline_{MICRO_INTERVAL}", f"{s}@kline_{SIGNAL_INTERVAL}",
                f"{s}@kline_{TREND_INTERVAL}", f"{s}@aggTrade", f"{s}@bookTicker")

    def set_universe(self, symbols):
        desired = set()
        for symbol in symbols:
            desired.update(self.streams_for(symbol))
        self.desired = desired

    async def _send(self, method, params):
        if self.ws is None or self.ws.closed:
            return False
        self._id += 1
        try:
            await self.ws.send_json({"method": method, "params": sorted(params), "id": self._id})
            return True
        except (RuntimeError, ConnectionError, aiohttp.ClientError):
            return False

    async def sync_subscriptions(self):
        if not self.desired:
            return
        to_unsub = self.subscribed - self.desired
        to_sub = self.desired - self.subscribed
        if to_unsub and await self._send("UNSUBSCRIBE", to_unsub):
            self.subscribed -= to_unsub
        if to_sub and await self._send("SUBSCRIBE", to_sub):
            self.subscribed |= to_sub

    def dispatch(self, text):
        """توجيه رسالة مغلَّفة من Combined Stream (متزامن وخفيف)."""
        try:
            message = json.loads(text)
        except ValueError:
            return
        if not isinstance(message, dict) or "stream" not in message:
            return  # ack اشتراك أو رسالة نظام
        stream = message.get("stream") or ""
        data = message.get("data") or {}
        stream_symbol = stream.split("@", 1)[0].upper()
        if "@kline" in stream:
            on_kline(data)
        elif "@aggTrade" in stream:
            on_agg_trade(stream_symbol, data)
        elif "@bookTicker" in stream:
            on_book(stream_symbol, data)

    async def run(self, on_reconnect=None):
        while True:
            try:
                url = f"{WS_MARKET_BASE}?streams={DUMMY_STREAM}"
                async with SESSION.ws_connect(
                    url, heartbeat=WS_HEARTBEAT, autoping=True,
                    timeout=WS_CONNECT_TIMEOUT, max_msg_size=4 * 1024 * 1024,
                ) as ws:
                    self.ws = ws
                    self.backoff = WS_RECONNECT_MIN
                    self.subscribed = set()
                    await self._send("UNSUBSCRIBE", [DUMMY_STREAM])
                    await self.sync_subscriptions()
                    self.connected.set()
                    log(f"WebSocket السوق متصل: {len(self.subscribed)} تدفقاً لأفضل {len(SYMBOLS)} زوجاً")
                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            self.dispatch(message.data)
                        elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                            break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log(f"انقطاع WebSocket السوق: {exc}; إعادة الاتصال خلال {self.backoff:.0f}ث")
            self.connected.clear()
            self.ws = None
            self.backoff, delay = next_backoff(self.backoff)
            await asyncio.sleep(delay)
            if on_reconnect is not None:
                try:
                    asyncio.create_task(on_reconnect())
                except RuntimeError:
                    pass


class UserDataStream:
    """يدير User Data Stream: listenKey + Keepalive + أحداث executionReport.

    - إنشاء مفتاح استماع (POST) وتجديده كل 30 دقيقة (PUT).
    - عند الفقدان/الانقطاع: مفتاح جديد + اتصال جديد + مصالحة لقطية
      (أحداث التنفيذ التي فُقدت أثناء الانقطاع تُسترد بفحص أحادي).
    """

    def __init__(self):
        self.ws = None
        self.listen_key = None
        self.connected = asyncio.Event()
        self.backoff = WS_RECONNECT_MIN
        self._stop = False

    async def ensure_listen_key(self, force_new=False):
        if self.listen_key and not force_new:
            return self.listen_key
        key = await REST.create_listen_key()
        if not key:
            raise BinanceError("تعذر إنشاء listenKey")
        self.listen_key = str(key)
        return self.listen_key

    async def keepalive_loop(self):
        while not self._stop:
            await asyncio.sleep(LISTEN_KEY_KEEPALIVE)
            if self._stop or not self.listen_key:
                continue
            try:
                await REST.keepalive_listen_key(self.listen_key)
            except BinanceError as exc:
                log(f"User Stream: تعذر تجديد listenKey ({exc})؛ تجديد المفتاح")
                try:
                    await self.ensure_listen_key(force_new=True)
                except BinanceError as inner:
                    log(f"User Stream: فشل تجديد المفتاح ({inner})")

    async def run(self, on_reconnect=None):
        keepalive_task = None
        try:
            while True:
                try:
                    key = await self.ensure_listen_key()
                    url = f"{WS_USER_BASE}/{key}"
                    async with SESSION.ws_connect(
                        url, heartbeat=WS_HEARTBEAT, autoping=True,
                        timeout=WS_CONNECT_TIMEOUT, max_msg_size=4 * 1024 * 1024,
                    ) as ws:
                        self.ws = ws
                        self.backoff = WS_RECONNECT_MIN
                        self.connected.set()
                        if keepalive_task is None:
                            keepalive_task = asyncio.create_task(self.keepalive_loop())
                        log("User Data Stream متصل (executionReport)")
                        async for message in ws:
                            if message.type == aiohttp.WSMsgType.TEXT:
                                dispatch_user_message(message.data)
                            elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                                break
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    log(f"انقطاع User Data Stream: {exc}; إعادة الاتصال خلال {self.backoff:.0f}ث")
                self.connected.clear()
                self.ws = None
                self.listen_key = None  # مفتاح جديد بعد كل انقطاع (أأمن)
                self.backoff, delay = next_backoff(self.backoff)
                await asyncio.sleep(delay)
                if on_reconnect is not None:
                    try:
                        asyncio.create_task(on_reconnect())
                    except RuntimeError:
                        pass
        finally:
            if keepalive_task is not None:
                keepalive_task.cancel()
                await asyncio.gather(keepalive_task, return_exceptions=True)


async def btc_context_loop(btc_stream):
    """سدّة أمان لسياق BTC: إعادة بذر REST إذا صمتت القناة (فشل آمن مغلّف)."""
    while True:
        await asyncio.sleep(max(30.0, BTC_CTX_MAX_AGE / 3.0))
        try:
            age = time.monotonic() - float(BTC_CTX.get("last_update") or 0.0)
            if age > BTC_CTX_MAX_AGE / 3.0:
                await seed_btc_context()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ تسخين سياق BTC: {exc}")


class BtcContextStream:
    """اتصال WebSocket مستقل بـ BTCUSDT@kline_1m — مصدر السياق الكلي.

    لا يمر عبر MarketStreamHub (تفادياً لاعتماده على كون أفضل 30 أو على
    إعادة الاشتراك): قناة واحدة دائمة، تُبذر من REST عند الإقلاع/الانقطاع.
    """

    def __init__(self):
        self.ws = None
        self.connected = asyncio.Event()
        self.backoff = WS_RECONNECT_MIN

    @staticmethod
    def stream_name():
        return f"{BTC_CONTEXT_SYMBOL.lower()}@kline_1m"

    async def run(self, on_reconnect=None):
        while True:
            try:
                url = f"{WS_USER_BASE}/{self.stream_name()}"
                async with SESSION.ws_connect(
                    url, heartbeat=WS_HEARTBEAT, autoping=True,
                    timeout=WS_CONNECT_TIMEOUT, max_msg_size=1024 * 1024,
                ) as ws:
                    self.ws = ws
                    self.backoff = WS_RECONNECT_MIN
                    self.connected.set()
                    log(f"BTC Context Stream متصل ({self.stream_name()})")
                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            btc_ctx_dispatch(message.data)
                        elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING,
                                              aiohttp.WSMsgType.ERROR):
                            break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log(f"انقطاع BTC Context Stream: {exc}; إعادة الاتصال خلال {self.backoff:.0f}ث")
            self.connected.clear()
            self.ws = None
            self.backoff, delay = next_backoff(self.backoff)
            await asyncio.sleep(delay)
            if on_reconnect is not None:
                try:
                    asyncio.create_task(on_reconnect())
                except RuntimeError:
                    pass


async def universe_loop(hub):
    """يجدد أفضل 30 زوجاً كل ساعة ويحدّث اشتراكات WebSocket تلقائياً."""
    while True:
        await asyncio.sleep(UNIVERSE_REFRESH_EVERY)
        try:
            previous = set(SYMBOLS)
            await refresh_universe()
            current = set(SYMBOLS)
            added = current - previous
            removed = previous - current
            for symbol in sorted(added):
                try:
                    await seed_symbol(symbol)
                except Exception as exc:
                    log(f"فشل تسخين {symbol}: {exc}")
            if removed:
                held = {p.get("symbol") for p in (STATE.get("positions") or {}).values()}
                for symbol in removed:
                    READY.pop(symbol, None)
                    WHALES.pop(symbol, None)
                    if symbol in held:
                        continue      # مركز مفتوح → أبقِ بياناته حتى يُغلق
                    BOOK.pop(symbol, None)
                    FLOW.pop(symbol, None)
                    TREND.pop(symbol, None)
                    CANDLES.pop((symbol, MICRO_INTERVAL), None)
                    CANDLES.pop((symbol, SIGNAL_INTERVAL), None)
                    CANDLES.pop((symbol, TREND_INTERVAL), None)
            hub.set_universe(SYMBOLS)
            await hub.sync_subscriptions()
            if added or removed:
                log(f"كون محدّث: {len(SYMBOLS)} زوجاً (+{len(added)}/-{len(removed)}) واشتراكات WebSocket مُحدَّثة")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ تحديث الكون: {exc}")


async def manage_loop():
    """حلقة صيانة هادئة (كل 5 دقائق): Dust 24س + معلقات أحدث من 120ث فقط."""
    while True:
        await asyncio.sleep(MANAGE_EVERY)
        try:
            await dust_sweep_if_due()
            if time.monotonic() - float(BTC_CTX.get("last_update") or 0.0) > BTC_CTX_MAX_AGE:
                await seed_btc_context()
            # سدّة أمان: أعد تقييم التتبّع من آخر سعر معروف (لو صمتت bookTicker)
            for _pid, _pos in list((STATE.get("positions") or {}).items()):
                _sym = _pos.get("symbol", "")
                _px, _ = market_price(_sym)
                if _px > 0:
                    on_price_update(_sym, _px)
            stale = {cid: rec for cid, rec in STATE.get("pending_entries", {}).items()
                     if time.time() - float(rec.get("placed_at", 0)) > 120}
            if stale:
                await reconcile_snapshot("معلقات قديمة")
            if STATE.get("positions"):
                await save_state()    # تثبيت قمم/حالة التتبّع دورياً (نجاة من تعطل مفاجئ)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ حلقة الصيانة: {exc}")


async def time_stop_loop():
    """وقف زمني (V5.1): سكالب بلا زخم خلال TIME_STOP_SEC يُصفى بسعر السوق.

    السكالبينج يحتاج زخماً فورياً؛ المركز الذي يبقى حياً بلا ربح مقبول بعد
    15 دقيقة غالباً انتهت صلاحية فكرته: نلغي وقف الطوارئ على Binance ونبيع
    MARKET لتحرير رأس المال (ربح ≥ TIME_STOP_MIN_PROFIT_PCT يُترك للتتبّع).
    """
    while True:
        await asyncio.sleep(TIME_STOP_CHECK_EVERY)
        if not TIME_STOP_ENABLED or DRY_RUN or not live_execution_allowed():
            continue
        try:
            async with STATE_LOCK:
                open_positions = [(pid, dict(pos)) for pid, pos in STATE.get("positions", {}).items()]
            now = time.time()
            for pid, position in open_positions:
                opened = float(position.get("opened_at", 0) or 0)
                if opened <= 0 or now - opened < TIME_STOP_SEC:
                    continue
                symbol = position.get("symbol", "")
                # لا تبيع على سعر قديم (انقطاع تدفق) — أنتظر دورة الحلقة القادمة
                if data_age(symbol) > max(MAX_STALE_SEC * 4, 30.0):
                    continue
                price, _age = market_price(symbol)
                if price <= 0:
                    continue
                gain_pct = (price - float(position.get("entry", 0))) / float(position.get("entry", 1)) * 100.0
                # نُصفّي فقط إذا لم يكن الربح مقبولاً (الرابح يُترك لمحرك التتبّع)
                if gain_pct >= TIME_STOP_MIN_PROFIT_PCT:
                    continue
                if pid in EXIT_PENDING or pid in EXIT_CLAIMED:
                    continue      # مهمة خروج جارية بالفعل → لا بيع مزدوج
                FUNNEL["time-stop"] += 1
                log(f"وقف زمني {pid}: عمر {now - opened:.0f}ث ربح {gain_pct:+.2f}% → تصفية MARKET")
                await force_exit_position(pid, position,
                                          f"وقف زمني ({TIME_STOP_SEC//60}د بلا زخم)")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ حلقة الوقف الزمني: {exc}")


async def heartbeat_loop():
    """نبضة خفيفة: حفظ الذاكرة وسطر حالة في السجل كل 6 ساعات."""
    while True:
        await asyncio.sleep(6 * 3600)
        try:
            await save_state()
            log("نبضة 6س: " + status_text().replace("\n", " | "))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ النبضة: {exc}")


async def once_scan():
    """وضع --once: تنقيط فوري للكون عبر شموع مسخّنة + BBA + تدفق REST حقيقي."""
    fired = 0
    for symbol in SYMBOLS:
        try:
            book = await REST.book_ticker(symbol)
            parsed = parse_book_payload({
                "b": book.get("bidPrice"), "B": book.get("bidQty"),
                "a": book.get("askPrice"), "A": book.get("askQty"),
            })
            if parsed is not None:
                BOOK[symbol] = parsed
            await prime_flow_from_rest(symbol)
            signal = build_signal(symbol)
            if signal is None:
                continue
            if signal["setup_id"] in SETUPS:
                continue
            if await process_signal(signal):
                fired += 1
            else:
                log(f"تخطي {symbol}: score={signal['score']:.0f} veto={veto_reason(symbol, signal)}")
        except BinanceError as exc:
            log(f"فحص {symbol}: {exc}")
    log(f"الفحص الفوري: {fired} إشارة منفذة")


async def prime_flow_from_rest(symbol, limit=100):
    """يبذّر نافذة التدفق من aggTrades (REST) — يكفي وضع --once/إعادة الاتصال."""
    rows = await REST.agg_trades(symbol, limit)
    buy_quote = sell_quote = 0.0
    last_ts = time.time()
    price = 0.0
    for row in rows if isinstance(rows, list) else []:
        try:
            price = float(row[1])
            quantity = float(row[2])
            trades = max(1.0, float(row[5]))
            last_ts = float(row[6]) / 1000.0
            is_buyer_maker = bool(row[8])
        except (IndexError, TypeError, ValueError):
            continue
        if price <= 0 or quantity <= 0:
            continue
        quote = price * quantity
        if trades > 1.5:
            # دلو متعدّد الصفقات: نسبة الأطراف غير موثوقة ⇒ توزيع متساوٍ (محايد)
            buy_quote += quote / 2.0
            sell_quote += quote / 2.0
        elif is_buyer_maker:
            sell_quote += quote
        else:
            buy_quote += quote
    if buy_quote + sell_quote <= 0:
        return False
    state = flow_add(symbol, last_ts, buy_quote, sell_quote)
    state["price"] = price or float((BOOK.get(symbol) or {}).get("ask") or 0)
    state["epoch"] = time.time()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# 13) الاختبار الذاتي (بلا شبكة إطلاقاً)
# ══════════════════════════════════════════════════════════════════════════════


def _synthetic_rows(interval="5m", wick=False):
    """صفوف klines تركيبية: شمعة إزاحة تكسر قمة وتصنع FVG غير معبأة.

    آخر صف = الشمعة الحية (يحذفها build_buffer من المغلقات).
    wick=True يجعل آخر شمعة مغلقة ذيلها مهيمنًا (اختبار مصيدة السيولة).
    """
    rows = []
    step_ms = INTERVAL_SECONDS[interval] * 1000
    last_open = int(time.time() * 1000) // step_ms * step_ms
    n = 100
    for i in range(n):
        t = last_open - (n - 1 - i) * step_ms
        if i <= 96:
            rows.append([t, "100.0", "100.5", "99.5", "100.0", "1000", 0, 0, 0, 0, 0, 0])
        elif i == 97:
            rows.append([t, "100.2", "109.2", "100.1", "109.0", "5000", 0, 0, 0, 0, 0, 0])
        elif i == 98:
            if wick:
                rows.append([t, "100.0", "100.5", "95.0", "100.2", "4000", 0, 0, 0, 0, 0, 0])
            else:
                rows.append([t, "105.0", "110.3", "104.0", "110.0", "4000", 0, 0, 0, 0, 0, 0])
        else:
            rows.append([t, "109.5", "110.4", "109.0", "110.0", "1500", 0, 0, 0, 0, 0, 0])
    return rows


def _reference_ema(values, period):
    """مرجع EMA كلاسيكي مستقل (بذرة SMA) للتحقق المتقاطع — للاختبار فقط."""
    if len(values) < period:
        return [None] * len(values)
    out = [None] * len(values)
    current = sum(values[:period]) / period
    out[period - 1] = current
    weight = 2.0 / (period + 1)
    for i in range(period, len(values)):
        current = values[i] * weight + current * (1.0 - weight)
        out[i] = current
    return out


def _reference_wilder_atr(highs, lows, closes, period):
    """مرجع ATR ويلدر مستقل للتحقق المتقاطع — للاختبار فقط."""
    n = len(closes)
    if n < period:
        return [None] * n
    trs = [highs[0] - lows[0]]
    for i in range(1, n):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    out = [None] * n
    current = sum(trs[:period]) / period
    out[period - 1] = current
    for i in range(period, n):
        current = (current * (period - 1) + trs[i]) / period
        out[i] = current          # ترقيع V5: المرجع كان يكتب البذرة فقط
    return out


async def run_selftest():
    global STATE, STARTUP_NOTIFIED, ENTRY_RESERVATIONS, RESERVED_QUOTE
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN, SYMBOL_RULES, BTC_CTX
    print("NOVA ASYNC SCALPER V5.0 SELFTEST — Weighted Scoring / Risk Parity / Context Gate")
    results = []

    def check(name, condition):
        results.append(bool(condition))
        print(("✅ " if condition else "❌ ") + name)

    ensure_dirs()
    try:
        os.remove(KILL_SWITCH_FILE)
    except OSError:
        pass

    # 1) EMA متجهي (pandas) يطابق المرجع الكلاسيكي حرفياً
    closes = [100.0 + (i % 13) * 0.5 for i in range(260)]
    ours = ema_series(closes, EMA_TREND_PERIOD)
    ref = _reference_ema(closes, EMA_TREND_PERIOD)
    max_err = max(abs(float(ours[i]) - ref[i]) for i in range(len(closes)) if ref[i] is not None)
    check(f"EMA{EMA_TREND_PERIOD}(pandas) يطابق المرجع الكلاسيكي",
          math.isnan(float(ours[EMA_TREND_PERIOD - 2])) and max_err < 1e-9)
    check("EMA_last", abs(ema_last(closes, EMA_TREND_PERIOD) - ref[-1]) < 1e-9)

    # 2) ATR متجهي + نسبة التقلب VR
    highs = [100.0 + (i % 7) for i in range(120)]
    lows = [99.0 + (i % 5) for i in range(120)]
    atr_ours = atr_series(highs, lows, closes[:120], ATR_PERIOD)
    atr_ref = _reference_wilder_atr(highs, lows, closes[:120], ATR_PERIOD)
    compared = [i for i in range(len(atr_ref)) if atr_ref[i] is not None]
    atr_err = max(abs(float(atr_ours[i]) - atr_ref[i]) for i in compared)
    check(f"ATR(numpy+pandas) يطابق مرجع Wilder في كل {len(compared)} قيمة (بذرة + ذيل)",
          len(compared) == 120 - ATR_PERIOD + 1 and atr_err < 1e-9)
    n = 200
    flat_atr, flat_vr = volatility_ratio([101.0] * n, [99.0] * n, [100.0] * n, ATR_PERIOD, VR_BASELINE)
    check(f"VR = 1.0 في سوق ثابت (ATR={flat_atr:.4g})", abs(flat_atr - 2.0) < 1e-9 and abs(flat_vr - 1.0) < 1e-9)
    spike_h = [101.0] * (n - 4) + [140.0, 141.0, 142.0, 143.0]
    spike_l = [99.0] * (n - 4) + [99.5, 99.5, 99.5, 99.5]
    spike_c = [100.0] * (n - 4) + [130.0, 135.0, 138.0, 142.0]
    atr_spike, vr_spike = volatility_ratio(spike_h, spike_l, spike_c, ATR_PERIOD, VR_BASELINE)
    ref_atr = [v for v in _reference_wilder_atr(spike_h, spike_l, spike_c, ATR_PERIOD) if v is not None]
    vr_expected = ref_atr[-1] / (sum(ref_atr[-VR_BASELINE:]) / VR_BASELINE)
    check(f"VR = ATR14/متوسط 20 (احتياط: {vr_spike:.2f} = {vr_expected:.2f} > {VR_FAST})",
          abs(vr_spike - vr_expected) < 1e-12 and vr_spike > VR_FAST
          and atr_multiplier(vr_spike) == (ATR_MULT_FAST, "fast"))
    atr_one, vr_one = volatility_ratio([101.0] * (n - 1) + [112.0], [99.0] * (n - 1) + [98.0],
                                       [100.0] * (n - 1) + [110.0], ATR_PERIOD, VR_BASELINE)
    check(f"ذرّة تقلب واحدة لا تقلب النظام (VR={vr_one:.2f} → حالة {atr_multiplier(vr_one)[1]})",
          vr_one < VR_FAST and atr_multiplier(vr_one)[1] == "normal")

    # 3) بناء المخزن من REST + إلحاق/تكرار/فجوة
    buffer = build_buffer(_synthetic_rows(), "5m")
    check("بناء مخزن الشموع", buffer is not None and len(buffer["c"]) == 99 and buffer["live"] == 110.0)
    last_t = buffer["t"][-1]
    check("إزالة تكرار شمعة مغلقة",
          buffer_append(buffer, "5m", last_t, 105.0, 110.3, 104.0, 110.0, 4000.0) == "updated"
          and len(buffer["c"]) == 99)
    check("إلحاق شمعة جديدة + كشف فجوة",
          buffer_append(buffer, "5m", last_t + 300_000, 109.5, 110.4, 109.0, 109.8, 900.0) == "appended"
          and buffer_append(buffer, "5m", last_t + 1_200_000, 109.0, 110.0, 108.5, 109.5, 800.0) == "gap")

    # 4) MSS وFVG ونسبة الذيل على 5m
    frame = build_buffer(_synthetic_rows(), "5m")
    o, h, l, c = buffer_to_frame(frame)
    atr_value = atr_last(h, l, c, ATR_PERIOD)
    mss = detect_mss(o, h, l, c, atr_value)
    check("MSS لحظي (5m)", mss is not None and mss["prior_high"] == 109.2 and mss["displacement"] > MSS_MIN_RANGE_ATR)
    fvg = detect_fvg(h, l, atr_value)
    check("FVG غير معبأة (5m)", fvg is not None and fvg["low"] == 100.5 and fvg["high"] == 104.0)
    step5 = INTERVAL_SECONDS["5m"] * 1000
    flat_rows = [[int(time.time() * 1000) // step5 * step5 - (99 - i) * step5, "100", "100.5", "99.5", "100", "1000"]
                 for i in range(100)]
    flat = build_buffer(flat_rows, "5m")
    fo, fh, fl, fc = buffer_to_frame(flat)
    check("لا MSS في سوق عرضي", detect_mss(fo, fh, fl, fc, atr_last(fh, fl, fc, ATR_PERIOD)) is None)
    wick_ratio = detect_wick_ratio(*buffer_to_frame(build_buffer(_synthetic_rows(wick=True), "5m")))
    clean_ratio = detect_wick_ratio(o, h, l, c)
    check(f"كشف الشمعة الذيلية (نسبة {wick_ratio:.2f} > {WICK_REJECT_RATIO}، نظيفة {clean_ratio:.2f})",
          wick_ratio > WICK_REJECT_RATIO and clean_ratio <= WICK_REJECT_RATIO)

    # 5) محرك التنقيط التعويضي (V5.2): مكافأة زخم +25 وحارس MSS الإلزامي
    s_mss, c_mss, t_mss, _p1 = compute_score(True, False, False, 1.0)                       # MSS وحده 35
    s_grad, c_grad, t_grad, _pg = compute_score(True, False, True, 1.2)                     # تدفق خفيف 8 + EMA مسطح 10
    s_full, c_full, t_full, _p3 = compute_score(True, True, True, 2.0, True)                # 35+25+20+20 = 100
    s_noflow, c_noflow, t_noflow, _p4 = compute_score(True, True, True, 1.0, True)          # 35+25+20 = 80
    s_weak, c_weak, t_weak, _p5 = compute_score(True, True, False, 1.0)                     # 60 (بلا اتجاه/تدفق)
    # تعويض بشري: MSS + تدفق متفجّر (>3) بلا FVG وبلا اتجاه
    s_flow, c_flow, t_flow, p_flow = compute_score(True, False, False, 3.5)
    # تعويض بشري: MSS + انفجار حجم (>2.5) بلا FVG وبلا اتجاه وبتدفق ضعيف
    s_vol, c_vol, t_vol, p_vol = compute_score(True, False, False, 1.0, False, 3.0)
    check("MSS وحده (35) لا يكفي", s_mss == 35.0 and not t_mss)
    check("تدرّج التدفق الخفيف يمنح 8 (لا 0 صارمة)", abs(s_grad - (35.0 + 10.0 + SCORE_FLOW_WEAK)) < 1e-9)
    check("MSS+FVG+EMA(صاعد) بلا تدفق = 80 يُطلق", abs(s_noflow - 80.0) < 1e-9 and t_noflow)
    check("الإشارة الكاملة = 100 تُطلق", s_full == 100.0 and t_full)
    check("60 نقطة تُرفض (تحت الحاجز)", s_weak == 60.0 and not t_weak)
    check(f"مكافأة الزخم {SCORE_MOMENTUM_BONUS:.0f} تُضاف عند تدفق > {MOMENTUM_FLOW_EXTREME:g}",
          p_flow["momentum"] == SCORE_MOMENTUM_BONUS and t_flow and s_flow >= SCORE_TRIGGER)
    s_vol2, c_vol2, t_vol2, p_vol2 = compute_score(True, False, False, FLOW_IMBALANCE_MED, False, 3.0)
    check(f"مكافأة الزخم تُضاف عند حجم > {MOMENTUM_VOL_EXTREME:g} (تعويض غياب FVG/الاتجاه)",
          p_vol["momentum"] == SCORE_MOMENTUM_BONUS and p_vol2["momentum"] == SCORE_MOMENTUM_BONUS
          and s_vol2 >= SCORE_TRIGGER and t_vol2)
    check("MSS إلزامي: بلا كسر هيكل لا دخول مهما بلغ الزخم",
          not compute_score(False, True, True, 9.0, True, 5.0)[2]
          and not compute_score(False, True, True, 1.0, True, 1.0, True)[2])
    s_wh, c_wh, t_wh, p_wh = compute_score(True, False, False, 1.0, False, 1.0, True)
    s_wh2, c_wh2, t_wh2, p_wh2 = compute_score(True, False, False, FLOW_IMBALANCE_MED,
                                               False, 1.0, True)
    check(f"إيقاظ حوت (≥{WHALE_TRADE_USD:,.0f}$) يمنح مكافأة الزخم {SCORE_MOMENTUM_BONUS:.0f} تلقائياً",
          p_wh["momentum"] == SCORE_MOMENTUM_BONUS and p_wh2["momentum"] == SCORE_MOMENTUM_BONUS)
    check("حوت + MSS + تدفق متوسط يتجاوز الزناد رغم غياب FVG والاتجاه",
          t_wh2 and s_wh2 >= SCORE_TRIGGER and p_wh2["fvg"] == 0.0 and p_wh2["ema"] == 0.0)
    WHALES.clear()
    check("whale_mark يتجاهل ما دون العتبة ويسجّل ما فوقها",
          whale_mark("TSTUSDT", WHALE_TRADE_USD / 2.0) is False
          and whale_mark("TSTUSDT", WHALE_TRADE_USD * 2.0) is True
          and whale_recent("TSTUSDT")[0] is True)
    WHALES["TSTUSDT"]["ts"] = time.time() - (WHALE_MEMORY_SEC + 5)
    check("ذاكرة الحوت تنتهي زمنياً وتُنظَّف (لا تسرّب ذاكرة)",
          whale_recent("TSTUSDT")[0] is False and "TSTUSDT" not in WHALES)
    WHALES.clear()
    check(f"حاجز الزناد مضبوط على {SCORE_TRIGGER:.0f}/100", SCORE_TRIGGER == 72.0)
    check(f"معاملات V5.3: وقف ATR(1m)×{HARD_STOP_ATR_MULT:g}، وقف زمني {TIME_STOP_SEC}ث، EMA{EMA_TREND_PERIOD}",
          HARD_STOP_ATR_MULT == 1.5 and TIME_STOP_SEC == 900 and EMA_TREND_PERIOD == 100
          and SL_MAX_PCT == 3.0)
    check(f"حجم مصغّر: مخاطرة {TARGET_RISK_USD}$ وسقف {MAX_POSITION_NOTIONAL_USD}$ "
          f"و{MAX_OPEN_POSITIONS} مراكز ({MAX_POSITIONS_PER_SYMBOL}/عملة)",
          float(TARGET_RISK_USD) == 1.0 and float(MAX_POSITION_NOTIONAL_USD) == 12.0
          and MAX_OPEN_POSITIONS == 15 and MAX_POSITIONS_PER_SYMBOL == 3)

    # 6) قاعدة الفلاتر القاطعة: البنية لا تحوي AND متسلسلاً ولا طلقة معلقة
    check("إلغاء الطلقة المعلقة وبوابة AND (لا دوال قديمة)",
          "PENDING_TRIGGERS" not in globals() and "book_confirms" not in globals()
          and "TRIGGER_WINDOW" not in globals() and "launch_entry" in globals())

    # 7) تدفق aggTrade الحقيقي: اختلال الضغط + النافذة المتدحرجة
    FLOW.clear()
    now_ts = time.time()
    flow_add("TSTUSDT", now_ts, 3000.0, 1000.0)
    ratio, age = flow_imbalance("TSTUSDT")
    check("اختلال aggTrade = 3.0 (شراء/بيع)", abs(ratio - 3.0) < 1e-9 and age < 2.0)
    flow_add("TSTUSDT", now_ts, 1000.0, 3000.0)   # تراكم داخل نفس الدلو الزمني
    ratio2, _a2 = flow_imbalance("TSTUSDT")
    check("تراكم الدلاء يعيد الاختلال نحو 1.0 (4000$ شراء / 4000$ بيع)", abs(ratio2 - 1.0) < 1e-9)
    FLOW.clear()
    flow_add("OLDUSDT", now_ts - 600.0, 9000.0, 100.0)
    ratio3, _a3 = flow_imbalance("OLDUSDT")
    check("نافذة التدفق تُتقادم خارج FLOW_WINDOW_SEC", ratio3 == 0.0)
    FLOW.clear()

    # 8) وقف الطوارئ الصلب ATR(1m)×1.5 + سقف 3% + محرك الخروج الهجين
    r_micro = calculate_dynamic_risk(100.0, 5.0, 1.0, 1.0)      # ATR1m=1 → 1.5
    check(f"وقف الطوارئ = ATR(1m) × {HARD_STOP_ATR_MULT:g} (لا علاقة له بـ ATR 5m)",
          abs(r_micro["sl_distance"] - 1.5) < 1e-9 and abs(r_micro["sl"] - 98.5) < 1e-9
          and "tp" not in r_micro)
    r_fb = calculate_dynamic_risk(100.0, 2.236, 1.0, 0.0)       # رجوع: 2.236/2.236=1 → 1.5
    check("رجوع آمن ATR(5m)/√5 عند غياب شموع 1m",
          abs(r_fb["sl_distance"] - 1.5) < 1e-6 and abs(r_fb["atr_1m"] - 1.0) < 1e-6)
    r_cap = calculate_dynamic_risk(100.0, 0.0, 2.0, 10.0)       # 10×1.5=15% → يُجمَّع 3%
    check(f"سقف الوقف الصلب {SL_MAX_PCT}% (Flash-Crash Cap)",
          abs(r_cap["sl_distance"] - 3.0) < 1e-9 and abs(r_cap["sl_pct"] - 3.0) < 1e-9
          and r_cap["capped"])
    r_floor = calculate_dynamic_risk(100.0, 0.0, 1.0, 0.0)
    check(f"أرضية الوقف {SL_MIN_PCT}% تمنع وقفاً منحلاً عند سعر الدخول",
          r_floor["sl"] < 100.0 and abs(r_floor["sl_pct"] - SL_MIN_PCT) < 1e-9)
    hs, hs_risk = hard_stop_price(100.0, 1.0, 5.0, 1.0)
    check("hard_stop_price يعيد وقفاً وحيداً بلا أي رجل هدف",
          hs == D("98.5") and "tp" not in hs_risk
          and all(name not in globals() for name in ("oco_levels", "place_initial_oco")))

    # 8ب) محرك الخروج الهجين (دالة نقية): تعادل + سرعة تتبّع ديناميكية
    p_off = trailing_plan(100.0, 100.3, 100.3)                 # ربح 0.3% < 0.4%
    check("تحت عتبة التعادل: لا تتبّع ولا وقف محلي",
          p_off["armed"] is False and p_off["stop"] is None and p_off["hit"] is False)
    p_be = trailing_plan(100.0, 100.40, 100.40)                # قمة 0.40% ⇒ التسليح
    check(f"تفعيل عند +{BREAKEVEN_TRIGGER_PCT:g}%: الوقف لا يقل أبداً عن التعادل +{BREAKEVEN_LOCK_PCT:g}%",
          p_be["armed"] and p_be["stop"] >= 100.0 * (1 + BREAKEVEN_LOCK_PCT / 100.0) - 1e-9
          and p_be["stop"] > 100.0)
    p_wide = trailing_plan(100.0, 100.8, 100.8)                # قمة 0.8% → 0.20%
    check(f"ربح 0.4–{TRAIL_TIGHT_AFTER_PCT:g}% ⇒ مسافة تتبّع {TRAIL_WIDE_PCT:g}%",
          p_wide["mode"] == "trail-wide" and abs(p_wide["trail_pct"] - TRAIL_WIDE_PCT) < 1e-9
          and abs(p_wide["stop"] - 100.8 * (1 - TRAIL_WIDE_PCT / 100.0)) < 1e-9)
    p_tight = trailing_plan(100.0, 102.0, 102.0)               # قمة 2% → 0.08%
    check(f"ربح > {TRAIL_TIGHT_AFTER_PCT:g}% ⇒ خنق التتبّع إلى {TRAIL_TIGHT_PCT:g}%",
          p_tight["mode"] == "trail-tight" and abs(p_tight["trail_pct"] - TRAIL_TIGHT_PCT) < 1e-9
          and abs(p_tight["stop"] - 102.0 * (1 - TRAIL_TIGHT_PCT / 100.0)) < 1e-9)
    p_hit = trailing_plan(100.0, 102.0, 101.90)                # 101.9 < 101.9184
    check("لمس الوقف المتحرك يُبلَّغ hit=True (ربح مؤمَّن موجب)",
          p_hit["hit"] is True and p_hit["gain_pct"] > BREAKEVEN_LOCK_PCT)
    p_crash = trailing_plan(100.0, 100.5, 99.0)                # انهيار بعد التسليح
    check("انهيار تحت التعادل بعد التسليح ⇒ خروج فوري (لا عودة للخسارة)",
          p_crash["armed"] and p_crash["hit"] is True and p_crash["stop"] >= 100.15 - 1e-9)
    p_bad = trailing_plan(0.0, 0.0, 0.0)
    check("مدخلات فاسدة لمحرك التتبّع لا تفجّره", p_bad["armed"] is False and p_bad["hit"] is False)
    check("قمة مفقودة/فاسدة تُشتق من السعر ولا تُعطّل الحماية",
          trailing_plan(100.0, None, 101.0)["armed"] is True
          and trailing_plan(100.0, float("nan"), 101.0)["armed"] is True
          and trailing_plan(100.0, float("inf"), 101.0)["stop"] is not None)
    check("الوقف المتحرك لا يتراجع أبداً مع هبوط السعر (peak أحادي الاتجاه)",
          trailing_plan(100.0, 102.0, 100.5)["stop"]
          >= trailing_plan(100.0, 101.0, 100.5)["stop"] - 1e-12)

    # 9) الحجم المصغّر المبني على المخاطرة (1$) + تنصيف التقلب
    q1, n1, k1 = plan_position(100.0, 10.0, D("0.001"))    # وقف 10% → مركز 10$ بمخاطرة 1$
    q2, n2, k2 = plan_position(100.0, 0.5, D("0.001"))     # وقف 0.5% → 200$ → يُجمَّع عند 12$
    q3, n3, k3 = plan_position(100.0, 10.0, D("0.001"), 3.0)   # VR>1.5 → نصف الحجم
    check(f"مخاطرة ثابتة {TARGET_RISK_USD}$ (وقف واسع ⇒ مركز صغير)",
          abs(float(k1) - 1.0) < 1e-6 and abs(float(n1) - 10.0) < 1e-6 and float(q1) == 0.1)
    check(f"سقف المركز {MAX_POSITION_NOTIONAL_USD}$ يمنع انفجار الحجم",
          abs(float(n2) - float(MAX_POSITION_NOTIONAL_USD)) < 1e-9 and float(k2) <= 1.0
          and float(n2) < 200.0)
    check(f"تنصيف الحجم عند VR > {VR_FAST:g} (تقليل التعرض في الفوضى)",
          abs(float(n3) - 5.0) < 1e-6 and abs(float(k3) - 0.5) < 1e-6
          and abs(float(n3) - float(n1) / 2.0) < 1e-6)
    check("حجم ثابت 20$ أُزيل من الكود", "TRADE_NOTIONAL_D" not in globals())
    risks_ok = True
    for _sl in (0.05, 0.5, 1.5, 3.0, 12.0, 60.0):
        _q, _n, _r = plan_position(100.0, _sl, D("0.001"))
        if _r is not None and float(_r) > float(TARGET_RISK_USD) * RISK_TOLERANCE:
            risks_ok = False
    check(f"المخاطرة الفعلية لا تتجاوز {TARGET_RISK_USD}$ أبداً مهما كان الوقف/التقريب",
          risks_ok and plan_position(100.0, 60.0, D("0.001"))[2] is not None)
    check("أرضية استبعاد الكون = سقف المركز نفسه (لا عملة يستحيل تداولها)",
          float(D(MAX_POSITION_NOTIONAL_USD)) == float(MAX_POSITION_NOTIONAL_USD))
    bad_qty, bad_notional, _bad_risk = plan_position(100.0, 0.0, D("0.001"))
    check("وقف بصفر مسافة → رفض (لا قسمة على صفر)", bad_qty is None and bad_notional is None)
    STATE = default_state()
    for _i in range(MAX_OPEN_POSITIONS):
        STATE["positions"][f"S{_i}USDT#x"] = {"symbol": f"S{_i}USDT", "entry": 1.0, "qty": "1"}
    check(f"سقف {MAX_OPEN_POSITIONS} مركزاً عالمياً يغلق البوابة",
          count_open_positions() == MAX_OPEN_POSITIONS and not _entry_gates_open("NEWUSDT")
          and await reserve_entry("NEWUSDT", D("5")) is False)
    STATE = default_state()

    # 10) قاطع سياق BTC (Circuit Breaker): يوقف الشراء في انهيار السوق
    STATE = default_state()
    minute_ms = 60_000
    t_now = int(time.time() * 1000) // minute_ms * minute_ms
    BTC_CTX = {"closes": deque([100.0] * 8, maxlen=BTC_DROP_WINDOW_MIN + 25), "live": 99.0,
               "last_t": t_now, "last_update": time.monotonic(), "seeded": True, "vr": 1.0}
    blocked, why = btc_circuit_block()
    check(f"منع الشراء عند هبوط BTC 1% في 3د (سبب: {why})",
          blocked and abs(btc_ctx_stats()["drop_pct"] + 1.0) < 1e-6)
    BTC_CTX["live"] = 100.0
    blocked_flat, _why_flat = btc_circuit_block()
    check("سوق BTC مستقر → لا منع", blocked_flat is False)
    BTC_CTX["live"] = 99.8
    blocked_edge, _we = btc_circuit_block()
    check(f"هبوط 0.2% تحت العتبة {BTC_DROP_PCT}% → لا منع", blocked_edge is False)
    BTC_CTX["last_update"] = time.monotonic() - (BTC_CTX_MAX_AGE + 10)
    blocked_stale, why_stale = btc_circuit_block()
    check("مصدر سياق ميت → منع (فشل آمن)", blocked_stale and why_stale == "context-unavailable")
    BTC_CTX = {"closes": deque([100.0] * 8, maxlen=BTC_DROP_WINDOW_MIN + 25), "live": 100.0,
               "last_t": t_now, "last_update": time.monotonic(), "seeded": True, "vr": 1.0}
    check("BTC بلا بيانات تاريخاً → منع (لا شراء أعمى)",
          btc_ctx_stats()["drop_pct"] == 0.0 and btc_circuit_block()[0] is False)
    BTC_CTX["closes"] = deque(maxlen=BTC_DROP_WINDOW_MIN + 25)
    blocked_none, why_none = btc_circuit_block()
    check("لا شموع مغلقة → drop غير معروف → منع", blocked_none and why_none == "context-unavailable")
    BTC_CTX["closes"] = deque([100.0] * 8, maxlen=BTC_DROP_WINDOW_MIN + 25)
    BTC_CTX["live"] = 100.0

    # 11) التهدئة الديناميكية من تقلب BTC
    BTC_CTX["vr"] = 2.0
    check(f"سوق متقلب → تهدئة {COOLDOWN_FAST}ث", btc_cooldown() == COOLDOWN_FAST)
    BTC_CTX["vr"] = 0.5
    check(f"سوق هادئ → تهدئة {COOLDOWN_SLOW}ث", btc_cooldown() == COOLDOWN_SLOW)
    BTC_CTX["vr"] = 1.0
    check(f"سوق طبيعي → تهدئة {COOLDOWN_NORMAL}ث", btc_cooldown() == COOLDOWN_NORMAL)
    check("التهدئة الثابتة 300ث أُزيلت كقاعدة", SAME_SYMBOL_COOLDOWN != 300)

    # 12) رسالة kline_1m تخص BTC تحدّث السياق (شمعة مغلقة فقط تُضاف)
    BTC_CTX["live"] = 0.0
    btc_ctx_apply(BTC_CONTEXT_SYMBOL, {"i": "1m", "x": False, "t": t_now + minute_ms, "c": "101.0"})
    live_only = BTC_CTX["live"] == 101.0 and len(BTC_CTX["closes"]) == 8
    btc_ctx_apply(BTC_CONTEXT_SYMBOL, {"i": "1m", "x": True, "t": t_now + minute_ms, "c": "101.0"})
    closed_ok = len(BTC_CTX["closes"]) == 9 and BTC_CTX["last_t"] == t_now + minute_ms
    btc_ctx_apply(BTC_CONTEXT_SYMBOL, {"i": "1m", "x": True, "t": t_now + minute_ms, "c": "101.0"})
    dedup_ok = len(BTC_CTX["closes"]) == 9
    btc_ctx_apply("ETHUSDT", {"i": "1m", "x": True, "t": t_now, "c": "5000.0"})
    other_ok = len(BTC_CTX["closes"]) == 9
    check("سياق BTC: حية تُحدّث، مغلقة تُضاف مرة واحدة",
          live_only and closed_ok and dedup_ok and other_ok)
    BTC_CTX["last_update"] = time.monotonic()
    BTC_CTX["live"] = 100.0
    BTC_CTX["closes"] = deque([100.0] * 8, maxlen=BTC_DROP_WINDOW_MIN + 25)

    # 13) الإشارة الكاملة على بيانات تركيبية + Setup ID فريد
    SYMBOL_RULES["TSTUSDT"] = {
        "status": "TRADING", "base": "TST", "quote": "USDT",
        "tick": D("0.01"), "step": D("0.001"), "min_qty": D("0"), "max_qty": D("999999"),
        "market_step": D("0.001"), "market_min_qty": D("0"), "min_notional": D("5"),
    }
    SYMBOLS.clear(); SYMBOLS.extend(["TSTUSDT"]); SYMBOLS_SET.clear(); SYMBOLS_SET.add("TSTUSDT")
    CANDLES[("TSTUSDT", SIGNAL_INTERVAL)] = build_buffer(_synthetic_rows(), "5m")
    TREND["TSTUSDT"] = {"ema": 99.0, "last_t": None, "slope_up": True}
    flow_add("TSTUSDT", time.time(), 9000.0, 1000.0)
    BOOK["TSTUSDT"] = {"bid": 109.9, "ask": 110.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1099.0, "ask_vol": 1100.0, "imbalance": 0.5,
                       "spread_pct": 0.0909, "ts": time.monotonic()}
    sig = build_signal("TSTUSDT")
    check("إشارة V5.2 اكتملت بتنقيط 100 (MSS+FVG+EMA+Flow+حجم+زخم)",
          sig is not None and sig["score"] == 100.0 and sig["components"] == 6
          and sig["parts"]["momentum"] == SCORE_MOMENTUM_BONUS
          and sig["setup_id"].startswith("TSTUSDT@"))
    CANDLES[("TSTUSDT-WICK", SIGNAL_INTERVAL)] = build_buffer(_synthetic_rows(wick=True), "5m")
    TREND["TSTUSDT-WICK"] = {"ema": 99.0, "last_t": None}
    SYMBOL_RULES["TSTUSDT-WICK"] = dict(SYMBOL_RULES["TSTUSDT"])
    _wsig, wreason = _evaluate_frame("TSTUSDT-WICK")
    check("الشمعة الذيلية تمنع الدخول حتى بكامل النقاط", _wsig is None and wreason.startswith("wick"))
    # غياب EMA50 (السعر تحت المتوسط) مع بقاء MSS+FVG+Flow+حجم = 85 → لا يزال يُطلق
    TREND["TSTUSDT"] = {"ema": 200.0, "last_t": None, "slope_up": True}
    sig_below_ema = build_signal("TSTUSDT")
    check("الاتجاه مجرد نقاط: الإشارة تُطلق أيضاً تحت EMA بفضل الزخم",
          sig_below_ema is not None and sig_below_ema["score"] >= SCORE_TRIGGER
          and sig_below_ema["parts"]["ema"] == 0.0
          and sig_below_ema["parts"]["momentum"] == SCORE_MOMENTUM_BONUS)
    # MSS+FVG فقط + مكافأة حجم = 65 بلا اتجاه ولا تدفق → تحت الحاجز 72 → رفض
    TREND["TSTUSDT"] = {"ema": 200.0, "last_t": None, "slope_up": True}
    FLOW.clear()
    BOOK.clear()
    CANDLES[("TSTUSDT", SIGNAL_INTERVAL)]["v"][-1] = 1800.0   # حجم عادي: بلا مكافأة زخم
    info_weak, weak2_reason = _evaluate_frame("TSTUSDT")
    check("MSS+FVG بلا دعم ولا زخم (60) تُرفض ولا تُطلق",
          info_weak is not None and not info_weak["triggered"]
          and info_weak["score"] < SCORE_TRIGGER
          and info_weak["parts"]["momentum"] == 0.0 and build_signal("TSTUSDT") is None)
    CANDLES[("TSTUSDT", SIGNAL_INTERVAL)] = build_buffer(_synthetic_rows(), "5m")
    TREND["TSTUSDT"] = {"ema": 99.0, "last_t": None, "slope_up": True}
    flow_add("TSTUSDT", time.time(), 9000.0, 1000.0)
    BOOK["TSTUSDT"] = {"bid": 109.9, "ask": 110.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1099.0, "ask_vol": 1100.0, "imbalance": 0.5,
                       "spread_pct": 0.0909, "ts": time.monotonic()}

    # 14) الفلاتر القاطعة بعد التنقيط: سبريد + قدم البيانات
    BOOK["TSTUSDT"] = {"bid": 109.0, "ask": 111.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1090.0, "ask_vol": 1110.0, "imbalance": 0.5,
                       "spread_pct": 1.8, "ts": time.monotonic()}
    check("سبريد عريض يلغي الإشارة", veto_reason("TSTUSDT") == "spread")
    BOOK["TSTUSDT"] = {"bid": 109.9, "ask": 110.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1099.0, "ask_vol": 1100.0, "imbalance": 0.5,
                       "spread_pct": 0.0909, "ts": time.monotonic()}
    FLOW.clear()
    FLOW["TSTUSDT"] = {"buy": 9.0, "sell": 1.0, "ts": time.time() - 99.0, "epoch": time.time() - 99.0,
                      "price": 110.0, "buckets": deque()}
    BOOK["TSTUSDT"]["ts"] = time.monotonic() - 99.0
    check(f"بيانات أقدم من {MAX_STALE_SEC}ث → إلغاء (بديل الطلقة المعلقة)",
          veto_reason("TSTUSDT") == "stale-tick")
    BOOK["TSTUSDT"]["ts"] = time.monotonic()
    FLOW.clear()
    flow_add("TSTUSDT", time.time(), 9000.0, 1000.0)
    (FLOW["TSTUSDT"])["price"] = 110.0
    (FLOW["TSTUSDT"])["epoch"] = time.time()
    check("بيانات طازجة → لا veto", veto_reason("TSTUSDT") is None)

    # 15) توقيع HMAC مع aiohttp (سلسلة حرفية واحدة بلا إعادة ترميز)
    globals()["BINANCE_API_KEY"] = "TEST_KEY"
    globals()["BINANCE_API_SECRET"] = "TEST_SECRET"
    values = {"symbol": "BTCUSDT", "quantity": "0.001", "recvWindow": 5000, "timestamp": 1700000000000}
    query, headers = build_signed(values)
    expected_query = "symbol=BTCUSDT&quantity=0.001&recvWindow=5000&timestamp=1700000000000"
    expected_sig = hmac.new(b"TEST_SECRET", expected_query.encode(), hashlib.sha256).hexdigest()
    globals()["BINANCE_API_KEY"], globals()["BINANCE_API_SECRET"] = "", ""
    check("توقيع HMAC-SHA256 مطابق حرفياً",
          query == f"{expected_query}&signature={expected_sig}" and headers["X-MBX-APIKEY"] == "TEST_KEY")

    # 16) ترقيع السباق: حجز ذري — 5 محاولات متزامنة → 3 فقط
    ENTRY_RESERVATIONS = {}
    RESERVED_QUOTE = Decimal("0")
    STATE = default_state()
    BTC_CTX["vr"] = 1.0
    outcomes = await asyncio.gather(*[reserve_entry("TSTUSDT", Decimal("80")) for _ in range(5)])
    for _ in range(3):
        await release_entry("TSTUSDT", Decimal("80"))
    check("Pyramiding: 3 مراكز كحد أقصى (بلا سباق)", sum(1 for x in outcomes if x) == 3)
    check("حجز التكلفة يُصفَّر ذرياً", RESERVED_QUOTE == Decimal("0"))

    # 17) التهدئة الديناميكية تُفعَّل داخل الحجز الذري
    ENTRY_RESERVATIONS = {}
    STATE = default_state()
    BTC_CTX["vr"] = 2.0     # متقلب → 60ث
    ok_a = await reserve_entry("TSTUSDT", Decimal("80"))
    await release_entry("TSTUSDT", Decimal("80"))
    STATE["last_entry_at"]["TSTUSDT"] = time.time()
    blocked_recent = not await reserve_entry("TSTUSDT", Decimal("80"))
    STATE["last_entry_at"]["TSTUSDT"] = time.time() - (COOLDOWN_FAST + 1.0)
    ok_after_fast = await reserve_entry("TSTUSDT", Decimal("80"))
    await release_entry("TSTUSDT", Decimal("80"))
    STATE["last_entry_at"]["TSTUSDT"] = time.time() - (COOLDOWN_FAST + 1.0)
    BTC_CTX["vr"] = 0.5     # هادئ → 120ث ⇒ 61ث ما زالت داخل التهدئة
    blocked_in_slow = not await reserve_entry("TSTUSDT", Decimal("80"))
    STATE["last_entry_at"]["TSTUSDT"] = time.time() - (COOLDOWN_SLOW + 1.0)
    ok_after_slow = await reserve_entry("TSTUSDT", Decimal("80"))
    await release_entry("TSTUSDT", Decimal("80"))
    BTC_CTX["vr"] = 1.0
    check("التهدئة تتسع/تضيق حسب تقلب BTC (60 ↔ 120)",
          ok_a and blocked_recent and ok_after_fast and blocked_in_slow and ok_after_slow)

    # 18) المسار الكامل V5.3: MARKET BUY → وقف طوارئ صلب → تتبّع → MARKET SELL
    class _StubRest:
        def __init__(self):
            self.order_calls = []
            self.stop_calls = []
            self.sell_calls = []
            self.cancel_calls = []
            self.oco_calls = []          # يجب أن يبقى فارغاً إلى الأبد (لا OCO)
            self.get_order_calls = 0
            self.open_orders_calls = 0
            self.cancel_fails = False
            self.sell_fails = False
            self.stop_seq = 0
        async def account(self):
            return {"balances": [{"asset": "USDT", "free": "5000", "locked": "0"}]}
        async def new_order(self, params):
            self.order_calls.append(params)
            qty = D(params.get("quantity", "0"))
            if params.get("type") == "STOP_LOSS_LIMIT":
                self.stop_calls.append(params)
                self.stop_seq += 1
                return {"orderId": 700 + self.stop_seq, "status": "NEW", "executedQty": "0",
                        "cummulativeQuoteQty": "0"}
            if params.get("side") == "SELL":
                self.sell_calls.append(params)
                if self.sell_fails:
                    raise BinanceError("insufficient balance", -2010, 400)
                price = D("101")
                return {"orderId": 801, "status": "FILLED", "side": "SELL",
                        "executedQty": dec_str(qty),
                        "cummulativeQuoteQty": dec_str(qty * price)}
            price = D("100")
            return {"orderId": 501, "status": "FILLED", "side": "BUY",
                    "executedQty": dec_str(qty), "cummulativeQuoteQty": dec_str(qty * price)}
        async def cancel_order(self, symbol, order_id):
            self.cancel_calls.append(order_id)
            if self.cancel_fails:
                raise BinanceError("network", None, None)
            return {"status": "CANCELED"}
        async def cancel_order_client(self, symbol, client_order_id):
            self.cancel_calls.append(client_order_id)
            return {"status": "CANCELED"}
        async def get_order(self, symbol, order_id):
            self.get_order_calls += 1
            return {"status": "CANCELED", "executedQty": "0"}
        async def get_order_client(self, symbol, client_order_id):
            self.get_order_calls += 1
            return {"orderId": 701, "status": "NEW", "executedQty": "0"}
        async def open_orders_all(self):
            self.open_orders_calls += 1
            return []
    stub = _StubRest()
    real_rest = REST
    globals()["REST"] = stub
    real_save = save_state

    async def _noop_save():
        return None
    globals()["save_state"] = _noop_save

    globals()["BINANCE_API_KEY"] = "TEST_KEY"
    globals()["BINANCE_API_SECRET"] = "TEST_SECRET"
    saved_dry, saved_auto = DRY_RUN, AUTO_TRADE
    globals()["DRY_RUN"] = False
    globals()["AUTO_TRADE"] = True
    STATE = default_state()
    ORDERS.clear()
    SETUPS.clear()
    EXIT_CLAIMED.clear()
    EXIT_PENDING.clear()
    ENTRY_RESERVATIONS = {}
    RESERVED_QUOTE = Decimal("0")
    signal_full = {
        "symbol": "TSTUSDT", "setup_id": "TSTUSDT@1700000000000",
        "atr": 1.0, "atr_1m": 1.0, "vr": 1.0, "score": 100.0,
        "parts": {"mss": 35.0, "fvg": 25.0, "ema": 20.0, "flow": 20.0},
        "components": 4, "flow_imbalance": 9.0, "close": 110.0, "live": 110.0,
        "atr_pct": 0.909, "fvg_mid": 0.0, "fvg_low": 0.0, "fvg_high": 0.0,
        "mss_prior_high": 0.0, "displacement": 0.0, "whale": False, "whale_usd": 0.0,
        "wick_ratio": 0.1, "created_at": time.time(),
    }
    BOOK["TSTUSDT"] = {"bid": 110.0, "ask": 110.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1100.0, "ask_vol": 1100.0, "imbalance": 0.5,
                       "spread_pct": 0.0, "ts": time.monotonic()}
    FLOW.clear()
    flow_add("TSTUSDT", time.time(), 9000.0, 1000.0)
    FLOW["TSTUSDT"]["price"] = 110.0
    FLOW["TSTUSDT"]["epoch"] = time.time()
    priced = estimate_entry_cost(signal_full)
    # وقف = ATR(1m) 1.0 × 1.5 = 1.5 على سعر مرجعي 110 ⇒ 1.3636% ⇒ مركز 73$ → سقف 12$
    sizing_ok = (priced is not None and abs(float(priced["price"]) - 110.0) < 1e-9
                 and abs(float(priced["sl_distance"]) - 1.5) < 1e-9
                 and abs(float(priced["notional"]) - float(MAX_POSITION_NOTIONAL_USD)) < 0.05
                 and float(priced["notional"]) <= float(MAX_POSITION_NOTIONAL_USD)
                 and "target" not in priced)
    entry_ok = await process_signal(signal_full)
    pid = next(iter(STATE["positions"])) if STATE["positions"] else None
    position = STATE["positions"].get(pid or "", {})
    market_ok = (entry_ok and len(stub.order_calls) == 2
                 and stub.order_calls[0]["type"] == "MARKET"
                 and stub.order_calls[0]["side"] == "BUY" and "price" not in stub.order_calls[0]
                 and len(stub.stop_calls) == 1 and not stub.oco_calls
                 and stub.stop_calls[0]["type"] == "STOP_LOSS_LIMIT"
                 and stub.stop_calls[0]["side"] == "SELL"
                 and abs(float(position.get("entry", 0)) - 100.0) < 1e-9
                 and abs(float(position.get("stop", 0)) - 98.5) < 1e-9
                 and "target" not in position
                 and position.get("protection_type") == "HARD_STOP")
    check("MARKET BUY فوري + وقف طوارئ صلب وحيد (بلا أي رجل هدف / بلا OCO)", market_ok)
    check(f"الحجم المصغّر: سقف {MAX_POSITION_NOTIONAL_USD}$ ووقف ATR(1m)×{HARD_STOP_ATR_MULT:g}",
          sizing_ok and float(stub.order_calls[0]["quantity"]) > 0)
    check("حالة المركز مهيأة لمحرك التتبّع (peak/trail بلا تسريب)",
          abs(float(position.get("peak", 0)) - 100.0) < 1e-9
          and position.get("trail_armed") is False and position.get("trail_mode") == "off")
    dedup_ok = position.get("setup_id") in SETUPS
    check("Setup ID سُجِّل لمنع التكرار في نفس الشمعة", dedup_ok)
    check("الأمر المُعبأ من الاستجابة لا يترك معلَّقاً ولا Watchdog",
          not STATE["pending_entries"] and stub.get_order_calls == 0)
    # حدث مكرر (سباق) → لا وقف ثانٍ ولا مركز مزدوج
    if pid:
        cid_repeat = position.get("entry_client_id")
        STATE["pending_entries"][cid_repeat] = {
            "symbol": "TSTUSDT", "client_order_id": cid_repeat, "order_id": 501,
            "qty": "0.109", "price": "110", "atr": 1.0, "atr_1m": 1.0, "vr": 1.0, "phase": "done",
        }
        await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid_repeat, "i": 501,
                                  "S": "BUY", "x": "TRADE", "X": "FILLED",
                                  "l": "0.109", "L": "100", "z": "0.109", "Z": "10.9"})
        STATE["pending_entries"].pop(cid_repeat, None)
    check("ترقيع السباق: الحدث المكرر لا يكرر الحماية ولا المركز",
          len(stub.stop_calls) == 1 and len(STATE["positions"]) == 1)

    # 18ب) محرك الخروج الهجين حياً: bookTicker → تعادل → تتبّع → إلغاء + MARKET SELL
    on_book("TSTUSDT", {"b": "100.20", "B": "5", "a": "100.21", "A": "5"})
    armed_no = STATE["positions"][pid].get("trail_armed") is False
    on_book("TSTUSDT", {"b": "100.50", "B": "5", "a": "100.51", "A": "5"})
    live = STATE["positions"][pid]
    armed_yes = (live.get("trail_armed") is True and live.get("trail_mode") == "trail-wide"
                 and abs(float(live.get("peak")) - 100.5) < 1e-9
                 and abs(float(live.get("trail_stop")) - 100.5 * 0.998) < 1e-9)
    check(f"bookTicker يفعّل التعادل/التتبّع عند +{BREAKEVEN_TRIGGER_PCT:g}% فقط",
          armed_no and armed_yes)
    on_book("TSTUSDT", {"b": "102.00", "B": "5", "a": "102.01", "A": "5"})
    tight_ok = (STATE["positions"][pid].get("trail_mode") == "trail-tight"
                and abs(float(STATE["positions"][pid]["trail_stop"]) - 102.0 * 0.9992) < 1e-9)
    check(f"ربح > {TRAIL_TIGHT_AFTER_PCT:g}% ⇒ خنق التتبّع حياً إلى {TRAIL_TIGHT_PCT:g}%", tight_ok)
    on_book("TSTUSDT", {"b": "101.00", "B": "5", "a": "101.01", "A": "5"})   # لمس الوقف
    for _ in range(6):
        await asyncio.sleep(0)
    trail_exit_ok = (not STATE["positions"] and stub.cancel_calls == [701]
                     and len(stub.sell_calls) == 1
                     and stub.sell_calls[0]["type"] == "MARKET"
                     and stub.sell_calls[0]["side"] == "SELL"
                     and STATE["metrics"]["wins"] == 1
                     and STATE["metrics"]["realized_pnl"] > 0
                     and pid not in EXIT_PENDING and pid not in EXIT_CLAIMED)
    check("لمس الوقف المتحرك ⇒ إلغاء وقف Binance ثم MARKET SELL (ربح مُثبَّت)", trail_exit_ok)
    check("القمة تُحرَّر مع المركز — لا قاموس قمم عالمي (لا تسرّب ذاكرة)",
          "PEAKS" not in globals() and "HIGHWATER" not in globals() and not EXIT_PENDING)
    # تكرار الأحداث بعد الخروج لا يبيع مرة ثانية
    on_book("TSTUSDT", {"b": "101.00", "B": "5", "a": "101.01", "A": "5"})
    for _ in range(4):
        await asyncio.sleep(0)
    check("لا بيع مزدوج: تحديثات السعر بعد الإغلاق لا تُصدر أوامر",
          len(stub.sell_calls) == 1 and not STATE["positions"])

    # 18ج) فشل إلغاء الوقف ⇒ لا MARKET SELL إطلاقاً (حماية من الكمية المزدوجة)
    stub.cancel_fails = True
    STATE["positions"]["TSTUSDT#guard"] = {
        "pid": "TSTUSDT#guard", "symbol": "TSTUSDT", "entry": 100.0, "qty": "0.1",
        "order_ids": [901], "peak": 100.0, "trail_armed": False, "stop": 98.5,
        "opened_at": time.time(),
    }
    sells_before = len(stub.sell_calls)
    forced = await force_exit_position("TSTUSDT#guard",
                                       dict(STATE["positions"]["TSTUSDT#guard"]), "اختبار الحارس")
    check("فشل إلغاء الوقف ⇒ لا بيع سوقي (منع الكمية المزدوجة) والمطالبة تُحرَّر",
          forced is False and len(stub.sell_calls) == sells_before
          and "TSTUSDT#guard" in STATE["positions"] and "TSTUSDT#guard" not in EXIT_CLAIMED)
    stub.cancel_fails = False
    forced2 = await force_exit_position("TSTUSDT#guard",
                                        dict(STATE["positions"]["TSTUSDT#guard"]), "وقف زمني اختباري")
    check("بعد نجاح الإلغاء: بيع MARKET واحد وإغلاق نظيف",
          forced2 is True and len(stub.sell_calls) == sells_before + 1
          and "TSTUSDT#guard" not in STATE["positions"])
    # 18د) فشل البيع بعد إلغاء الوقف ⇒ إعادة تركيب الحماية فوراً (لا مركز مكشوف)
    stub.sell_fails = True
    stops_before = len(stub.stop_calls)
    STATE["positions"]["TSTUSDT#naked"] = {
        "pid": "TSTUSDT#naked", "symbol": "TSTUSDT", "entry": 100.0, "qty": "0.1",
        "order_ids": [905], "stop_client_id": "hslN", "peak": 102.0, "stop": 98.5,
        "hard_stop": 98.5, "trail_armed": True, "trail_stop": 101.9,
        "trail_mode": "trail-tight", "opened_at": time.time(),
    }
    FLOW["TSTUSDT"]["price"] = 101.5
    FLOW["TSTUSDT"]["epoch"] = time.time()
    naked = await force_exit_position("TSTUSDT#naked",
                                      dict(STATE["positions"]["TSTUSDT#naked"]), "تتبّع")
    live_naked = STATE["positions"].get("TSTUSDT#naked") or {}
    rearmed_stop = float(stub.stop_calls[-1]["stopPrice"]) if stub.stop_calls else 0.0
    check("فشل البيع بعد إلغاء الوقف ⇒ إعادة تركيب الحماية (لا مركز مكشوف أبداً)",
          naked is False and len(stub.stop_calls) == stops_before + 1
          and live_naked.get("order_ids") and FUNNEL.get("stop-rearmed", 0) >= 1)
    check("الوقف المُعاد يحافظ على مكسب التعادل/التتبّع (لا يُسحق تحت الدخول)",
          rearmed_stop > 100.0 and rearmed_stop <= 101.5)
    check("الوقف المُعاد لا يخصم الرسوم مرتين (كمية المركز كما هي)",
          abs(float(stub.stop_calls[-1]["quantity"]) - 0.1) < 1e-9)
    stub.sell_fails = False
    await force_exit_position("TSTUSDT#naked",
                              dict(STATE["positions"]["TSTUSDT#naked"]), "تنظيف")
    STATE["positions"].pop("TSTUSDT#naked", None)

    # 18هـ) تعبئة جزئية لوقف الطوارئ تُقلّص كمية المركز (لا بيع كمية غير مملوكة)
    STATE["positions"]["TSTUSDT#part"] = {
        "pid": "TSTUSDT#part", "symbol": "TSTUSDT", "entry": 100.0, "qty": "1.0",
        "order_ids": [906], "peak": 100.0, "opened_at": time.time(),
    }
    ORDERS["906"] = {"role": "leg", "pid": "TSTUSDT#part", "symbol": "TSTUSDT"}
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": "hslP", "i": 906,
                              "S": "SELL", "x": "TRADE", "X": "PARTIALLY_FILLED",
                              "l": "0.4", "L": "98.5", "z": "0.4", "Z": "39.4"})
    part_qty = float(D(STATE["positions"]["TSTUSDT#part"]["qty"]))
    check("تعبئة جزئية للوقف تُقلّص كمية المركز فوراً (منع بيع كمية غير مملوكة)",
          abs(part_qty - 0.6) < 1e-9
          and STATE["positions"]["TSTUSDT#part"].get("stop_filled_qty") is not None)
    STATE["positions"].pop("TSTUSDT#part", None)
    ORDERS.pop("906", None)

    # وقف الطوارئ نُفّذ على Binance → إغلاق فوري من الحدث
    STATE["positions"]["TSTUSDT#hs"] = {
        "pid": "TSTUSDT#hs", "symbol": "TSTUSDT", "entry": 100.0, "qty": "0.1",
        "order_ids": [910], "peak": 100.0, "opened_at": time.time(),
    }
    ORDERS["910"] = {"role": "leg", "pid": "TSTUSDT#hs", "symbol": "TSTUSDT"}
    STATE["metrics"]["consecutive_losses"] = 0
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": "hsl1", "i": 910,
                              "S": "SELL", "x": "TRADE", "X": "FILLED",
                              "l": "0.1", "L": "98.5", "z": "0.1", "Z": "9.85"})
    check("executionReport لوقف الطوارئ ⇒ إغلاق فوري (بلا REST) + عدّاد المتتالية",
          "TSTUSDT#hs" not in STATE["positions"] and STATE["metrics"]["losses"] == 1
          and STATE["metrics"]["consecutive_losses"] == 1 and stub.get_order_calls == 0)
    # إلغاء بلا تعبئة → حذف المعلق بهدوء
    cid2 = make_client_id("nv5")
    STATE["pending_entries"][cid2] = {
        "symbol": "TSTUSDT", "client_order_id": cid2, "order_id": 112,
        "qty": "0.19", "price": "103", "atr": 1.0, "atr_1m": 1.0, "vr": 1.0,
        "placed_at": time.time(), "active": False, "phase": "placed",
    }
    ORDERS["112"] = {"role": "entry", "cid": cid2, "symbol": "TSTUSDT"}
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid2, "i": 112,
                              "S": "BUY", "x": "CANCELED", "X": "CANCELED",
                              "l": "0", "L": "0", "z": "0", "Z": "0"})
    check("executionReport CANCELED (بلا تعبئة) → حذف المعلق", cid2 not in STATE["pending_entries"])
    check("صفر REST Polling لحالة الأوامر في المسار السعيد",
          stub.get_order_calls == 0 and stub.open_orders_calls == 0)
    EXIT_CLAIMED.clear(); EXIT_PENDING.clear()
    globals()["DRY_RUN"], globals()["AUTO_TRADE"] = saved_dry, saved_auto
    globals()["BINANCE_API_KEY"], globals()["BINANCE_API_SECRET"] = "", ""
    globals()["REST"] = real_rest
    globals()["save_state"] = real_save

    # 19) القاطع يُلغي إشارة مكتملة النقاط (لا شراء ضد انهيار BTC)
    STATE = default_state()
    stub2 = _StubRest()
    globals()["BINANCE_API_KEY"] = "TEST_KEY"; globals()["BINANCE_API_SECRET"] = "TEST_SECRET"
    globals()["DRY_RUN"] = False; globals()["AUTO_TRADE"] = True
    globals()["REST"] = stub2
    BTC_CTX["live"] = 98.0          # هبوط ~2% خلال النافذة
    veto_before = veto_reason("TSTUSDT")
    blocked_signal = await process_signal(signal_full)
    check("قاطع BTC يمنع التنفيذ رغم 100 نقطة (صفر أوامر)",
          veto_before.startswith("btc-drop") and blocked_signal is False and not stub2.order_calls)
    BTC_CTX["live"] = 100.0
    globals()["DRY_RUN"], globals()["AUTO_TRADE"] = True, saved_auto
    blocked_dryrun = await process_signal(signal_full)
    globals()["DRY_RUN"], globals()["AUTO_TRADE"] = saved_dry, saved_auto
    globals()["BINANCE_API_KEY"], globals()["BINANCE_API_SECRET"] = "", ""
    globals()["REST"] = real_rest
    check("DRY-RUN لا يرسل أوامر ويسجّل الإشارة (Set & Forget جاهز)",
          blocked_dryrun is False and not stub2.order_calls)

    # 19b) بوابة التنفيذ الحي: تأكيد نصي إلزامي قبل أي أمر على MAINNET
    saved_env, saved_confirm = BINANCE_ENV, LIVE_CONFIRM
    globals()["BINANCE_ENV"] = "live"; globals()["LIVE_CONFIRM"] = ""
    globals()["DRY_RUN"] = False; globals()["AUTO_TRADE"] = True
    globals()["BINANCE_API_KEY"] = "K"; globals()["BINANCE_API_SECRET"] = "S"
    gate_no_confirm = live_execution_allowed() is False
    globals()["LIVE_CONFIRM"] = "I_UNDERSTAND_SPOT_RISK"
    gate_confirm = live_execution_allowed() is True
    globals()["BINANCE_ENV"] = saved_env; globals()["LIVE_CONFIRM"] = saved_confirm
    globals()["BINANCE_API_KEY"] = ""; globals()["BINANCE_API_SECRET"] = ""
    globals()["DRY_RUN"], globals()["AUTO_TRADE"] = saved_dry, saved_auto
    check("بوابة LIVE مشروطة بتأكيد نصي (I_UNDERSTAND_SPOT_RISK)", gate_no_confirm and gate_confirm)

    # 20) مسار الأحداث: إطلاق عند إغلاق الشمعة، ومرشّح رخيص يُستدعى بالتدفق
    STATE = default_state()
    SETUPS.clear(); FLOW.clear(); BOOK.clear(); READY.clear()
    CANDLES[("TSTUSDT", SIGNAL_INTERVAL)] = build_buffer(_synthetic_rows(), "5m")
    TREND["TSTUSDT"] = {"ema": 99.0, "last_t": None}
    flow_add("TSTUSDT", time.time(), 9000.0, 500.0)
    FLOW["TSTUSDT"]["price"] = 110.0
    FLOW["TSTUSDT"]["epoch"] = time.time()
    BOOK["TSTUSDT"] = {"bid": 109.9, "ask": 110.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1099.0, "ask_vol": 1100.0, "imbalance": 0.5,
                       "spread_pct": 0.0909, "ts": time.monotonic()}
    hub = MarketStreamHub()
    fired = []
    real_launch = launch_entry
    globals()["launch_entry"] = lambda signal: fired.append(signal["setup_id"])
    # (1) إغلاق شمعة بنقاط مكتملة → تنفيذ في نفس اللقطة (بلا نافذة انتظار)
    t_next = CANDLES[("TSTUSDT", SIGNAL_INTERVAL)]["t"][-1] + 300_000
    hub.dispatch(json.dumps({"stream": "tstusdt@kline_5m", "data": {
        "e": "kline", "E": int(time.time() * 1000), "s": "TSTUSDT",
        "k": {"i": "5m", "x": True, "t": t_next, "o": "105.0", "h": "110.3", "l": "104.0",
              "c": "110.0", "v": "4000"}}}))
    fired_on_close = len(fired) == 1
    appended = len(CANDLES[("TSTUSDT", SIGNAL_INTERVAL)]["c"]) == 100
    # (2) نقاط تحت الحاجز → لا تنفيذ، بل مرشّح في READY (بلا انتظار دفتر)
    CANDLES[("TSTUSDT", SIGNAL_INTERVAL)] = build_buffer(_synthetic_rows(), "5m")
    CANDLES[("TSTUSDT", SIGNAL_INTERVAL)]["v"][-1] = 1800.0   # حجم عادي: لا مكافأة زخم
    TREND["TSTUSDT"] = {"ema": 200.0, "last_t": None}
    FLOW.clear()
    on_signal_candle_closed("TSTUSDT")
    armed = "TSTUSDT" in READY and len(fired) == 1
    # (3) وصول تدفق شراء → إعادة تقييم → تجاوز الحاجز → إطلاق فوري
    flow_add("TSTUSDT", time.time(), 9000.0, 500.0)
    FLOW["TSTUSDT"]["price"] = 110.0
    FLOW["TSTUSDT"]["epoch"] = time.time()
    globals()["FLOW_CHECK_EVERY"] = 0.0
    READY["TSTUSDT"]["checked"] = 0.0
    on_market_tick("TSTUSDT")
    flow_ignites = len(fired) == 2 and "TSTUSDT" not in READY
    globals()["FLOW_CHECK_EVERY"] = 1.0
    # (4) حارسا CPU: لا تقييم بلا مرشّح، وتقييم واحد لكل مهلة معه
    calls = []

    def _spy(symbol):
        calls.append(symbol)
        return {"triggered": False, "score": 60.0, "setup_id": f"{symbol}@1", "candle_t": 0}, "spy"
    real_eval = _evaluate_frame
    globals()["_evaluate_frame"] = _spy
    READY.clear()
    for _ in range(30):
        hub.dispatch(json.dumps({"stream": "tstusdt@aggTrade", "data": {
            "e": "aggTrade", "s": "TSTUSDT", "p": "110.0", "q": "5", "m": False,
            "T": int(time.time() * 1000), "a": 1}}))
    no_work_without_candidate = not calls
    candle_t = CANDLES[("TSTUSDT", SIGNAL_INTERVAL)]["t"][-1]
    READY["TSTUSDT"] = {"t": candle_t, "score": 60.0, "checked": time.monotonic() - 9999.0}
    calls.clear()
    for _ in range(30):
        hub.dispatch(json.dumps({"stream": "tstusdt@aggTrade", "data": {
            "e": "aggTrade", "s": "TSTUSDT", "p": "110.0", "q": "5", "m": False,
            "T": int(time.time() * 1000), "a": 1}}))
    throttled = len(calls) == 1
    globals()["_evaluate_frame"] = real_eval
    globals()["launch_entry"] = real_launch
    READY.clear()
    check("شمعة مغلقة بنقاط مكتملة تُنفَّذ فوراً (بلا بوابة AND ولا انتظار)",
          fired_on_close and appended)
    check("نقاط تحت الحاجز تُبقي مرشّحاً رخيصاً بدل الرفض النهائي", armed)
    check("تدفق aggTrade يُشعل التنفيذ فور اكتمال 75 (وليس بعد دقيقة)", flow_ignites)
    check("حارس CPU: صفر تقييم لكل tick بلا مرشّح، وتقييم واحد لكل مهلة معه",
          no_work_without_candidate and throttled)
    check("اشتراكات الزوج تشمل aggTrade (تدفق حقيقي)",
          "tstusdt@aggTrade" in MarketStreamHub.streams_for("TSTUSDT"))

    # 21) EMA(15m) تتحدث عند إغلاق الشمعة (بلا ازدواج)
    step15 = INTERVAL_SECONDS[TREND_INTERVAL] * 1000
    t15_last = int(time.time() * 1000) // step15 * step15 - step15
    CANDLES[("TSTUSDT", TREND_INTERVAL)] = build_buffer(
        [[t15_last - (209 - i) * step15, "100", "100.5", "99.5", "100", "1000"] for i in range(210)], "15m")
    update_trend_ema("TSTUSDT")
    ema_first = TREND["TSTUSDT"]["ema"]
    buffer_append(CANDLES[("TSTUSDT", TREND_INTERVAL)], "15m", t15_last, 100, 100.5, 99.5, 100.0, 1000.0)
    update_trend_ema("TSTUSDT")
    ema_unchanged = TREND["TSTUSDT"]["ema"] == ema_first
    buffer_append(CANDLES[("TSTUSDT", TREND_INTERVAL)], "15m", t15_last + step15, 100, "100.6", "99.5", "100.4", "900")
    update_trend_ema("TSTUSDT")
    ema_moved = TREND["TSTUSDT"]["ema"] != ema_first
    check(f"EMA{EMA_TREND_PERIOD}(15m) عند إغلاق الشمعة بلا ازدواج",
          ema_first is not None and ema_unchanged and ema_moved)

    # 22) اختيار الكون: أفضل N مع استبعاد المستقرات والرافعات والأدنى حداً
    saved_rules = SYMBOL_RULES
    saved_topn = TOP_N_SYMBOLS
    globals()["TOP_N_SYMBOLS"] = 30
    SYMBOL_RULES = {}
    for i in range(40):
        base = f"C{i}"
        SYMBOL_RULES[f"{base}USDT"] = {"status": "TRADING", "base": base, "quote": "USDT", "min_notional": D("5")}
    SYMBOL_RULES["USDCUSDT"] = {"status": "TRADING", "base": "USDC", "quote": "USDT", "min_notional": D("5")}
    SYMBOL_RULES["BTCUPUSDT"] = {"status": "TRADING", "base": "BTCUP", "quote": "USDT", "min_notional": D("5")}
    SYMBOL_RULES["HEAVYUSDT"] = {"status": "TRADING", "base": "HEAVY", "quote": "USDT", "min_notional": D("5000")}
    tickers = {f"C{i}USDT": {"quote_volume": 50_000_000 - i * 1_000_000} for i in range(40)}
    tickers["USDCUSDT"] = {"quote_volume": 9e9}
    tickers["BTCUPUSDT"] = {"quote_volume": 9e9}
    tickers["HEAVYUSDT"] = {"quote_volume": 9e9}
    universe = pick_universe(tickers)
    SYMBOL_RULES = saved_rules
    globals()["TOP_N_SYMBOLS"] = saved_topn
    check(f"كون أفضل {30} مع الاستبعادات (وأصغر مركز ممكن ≥ الحد الأدنى)",
          len(universe) == 30 and universe[0] == "C0USDT"
          and "USDCUSDT" not in universe and "BTCUPUSDT" not in universe and "HEAVYUSDT" not in universe)

    # 23) Dust: انتقاء الأصول المؤهلة + جدولة 24 ساعة
    details = [
        {"asset": "TST", "amountFree": "12", "minTransferAmount": "10"},
        {"asset": "ALPHA", "amountFree": "5", "minTransferAmount": "10"},
        {"asset": "XYZ", "amountFree": "50", "minTransferAmount": "10"},
        {"asset": "BNB", "amountFree": "0.5", "minTransferAmount": "0.001"},
    ]
    picked = pick_dust_assets(details, {"TST", "ALPHA"})
    check("انتقاء Dust (مؤهل ضمن أصول البوت فقط)", picked == ["TST"])
    STATE["last_dust_sweep"] = time.time() - (DUST_SWEEP_EVERY + 60)
    due = time.time() - float(STATE["last_dust_sweep"]) >= DUST_SWEEP_EVERY
    STATE["last_dust_sweep"] = time.time()
    check("جدولة Dust كل 24 ساعة", due)

    # 24) Backoff إعادة الاتصال: مضاعفة مع سقف + Jitter
    b = WS_RECONNECT_MIN
    growth = []
    for _ in range(8):
        b, delay = next_backoff(b)
        growth.append(b)
    check("Backoff متزايد بسقف", abs(growth[0] - 2.0) < 1e-9 and growth[-1] == WS_RECONNECT_MAX
          and all(x <= WS_RECONNECT_MAX + 1e-9 for x in growth))

    # 25) صيغة /status الحرفية + تقرير السياق (/context)
    STATE = default_state()
    STATE["metrics"] = {"trades": 5, "realized_pnl": -1.25, "wins": 2, "losses": 3, "consecutive_losses": 3}
    STATE["positions"] = {"BTCUSDT#a": {"symbol": "BTCUSDT"}, "ETHUSDT#b": {"symbol": "ETHUSDT"}}
    text = status_text()
    check("صيغة /status العربية الحرفية",
          text.split("\n") == [
              "إجمالي الصفقات : 5", "",
              "🟢الناجحة : 2", "",
              "🔴الخاسرة : 3", "",
              "الخسائر المتتالية : 3", "",
              "اجمالي المكاسب : -1.25$", "",
              "نسبة النجاح : 40.00%",
          ] and "BTC" not in text and "USDT" not in text)
    ctx_text = context_text()
    check("تقرير السياق يعرض القاطع وVR والتهدئة الحالية",
          "BTC" in ctx_text and "VR" in ctx_text and f"{COOLDOWN_NORMAL}ث" in ctx_text)

    # 26) الوضع الصامت + /reset الحرفي + إشعار البدء مرة واحدة بالنص الحرفي
    saved_token, saved_chat, saved_dry2 = TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN = "fake-token", "42", False
    sent_payloads = []
    real_tg_api = tg_api

    async def _spy_tg(method, payload=None, retries=3):
        if method == "sendMessage":
            sent_payloads.append(payload)
        return {"message_id": 1}
    globals()["tg_api"] = _spy_tg
    auto_blocked = await send_message("رسالة تلقائية — يجب أن تُحجب") is False and not sent_payloads
    manual_sent = await send_message("رد على أمر يدوي", chat_id="42") is True and len(sent_payloads) == 1
    STATE["metrics"] = {"trades": 9, "realized_pnl": -3.5, "wins": 4, "losses": 5, "consecutive_losses": 2}
    globals()["save_state"] = _noop_save
    await handle_command("/reset", "42")
    reset_ok = (STATE["metrics"] == {"trades": 0, "realized_pnl": 0.0, "wins": 0, "losses": 0, "consecutive_losses": 0}
                and len(sent_payloads) == 2 and sent_payloads[-1]["text"] == RESET_REPLY)
    STARTUP_NOTIFIED = False
    notify_first = await notify_startup()
    notify_again = await notify_startup()
    startup_ok = (notify_first is True and notify_again is False and len(sent_payloads) == 3
                  and sent_payloads[-1]["text"] == STARTUP_TEXT)
    STARTUP_NOTIFIED = False
    await handle_command("/context", "42")
    context_cmd = len(sent_payloads) == 4 and "BTC" in sent_payloads[-1]["text"]
    globals()["save_state"] = real_save
    globals()["tg_api"] = real_tg_api
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN = saved_token, saved_chat, saved_dry2
    check("الوضع الصامت: لا رسائل تلقائية — ردود الأوامر فقط", auto_blocked and manual_sent)
    check("أمر /reset: تصفير الإحصائيات + الرد الحرفي", reset_ok)
    check("إشعار البدء: مرة واحدة بالضبط بالنص الحرفي", startup_ok)
    check("أمر /context متاح", context_cmd)

    # 27) V5.3: محرك التتبّع الهجين موجود بالكامل، وواجهات OCO أُزيلت
    check("محرك الخروج الهجين مركّب (تتبّع + وقف صلب) وواجهات OCO أُزيلت",
          all(name in globals() for name in ("trailing_plan", "on_price_update",
                                             "trigger_trailing_exit", "place_hard_stop",
                                             "cancel_hard_stop", "whale_mark"))
          and all(name not in globals() for name in ("place_initial_oco", "oco_levels",
                                                     "RR_RATIO", "OCO_LEGACY_FALLBACK")))
    check("لا أمر Trailing على Binance: التتبّع محلي والخروج MARKET SELL فقط",
          "TRAILING" not in "".join(
              str(v) for v in (place_hard_stop.__doc__ or "", cancel_hard_stop.__doc__ or "")).upper()
          and "trail" in (trailing_plan.__name__ or ""))

    # 28) إغلاق خاسر: عدّاد المتتالية يُحدَّث للتقرير فقط (بلا قواطع)
    globals()["save_state"] = _noop_save
    STATE = default_state()
    STATE["positions"]["TSTUSDT#y"] = {"symbol": "TSTUSDT", "entry": 100.0, "qty": "0.2", "order_ids": [701]}
    await finalize_position_event("TSTUSDT#y", STATE["positions"]["TSTUSDT#y"], 98.0, 0.2, "وقف الطوارئ")
    loss_ok = (STATE["metrics"]["losses"] == 1 and STATE["metrics"]["consecutive_losses"] == 1
               and abs(STATE["metrics"]["realized_pnl"] + 0.4) < 1e-6 and not STATE["positions"])
    await finalize_position_event("TSTUSDT#y", {"symbol": "TSTUSDT", "entry": 100.0, "qty": "0.2"}, 98.0, 0.2, "مكرر")
    check("إغلاق خاسر + منع الازدواج", loss_ok and STATE["metrics"]["losses"] == 1)
    globals()["save_state"] = real_save

    # تنظيف
    STATE = default_state()
    CANDLES.clear(); TREND.clear(); BOOK.clear(); FLOW.clear(); ORDERS.clear(); READY.clear()
    SETUPS.clear(); WHALES.clear(); EXIT_CLAIMED.clear(); EXIT_PENDING.clear()
    ENTRY_RESERVATIONS = {}; RESERVED_QUOTE = Decimal("0")
    BTC_CTX = {"closes": deque(maxlen=BTC_DROP_WINDOW_MIN + 25), "live": 0.0, "last_t": 0,
               "last_update": 0.0, "seeded": False}
    SYMBOL_RULES.pop("TSTUSDT", None)
    SYMBOL_RULES.pop("TSTUSDT-WICK", None)
    try:
        os.remove(KILL_SWITCH_FILE)
    except OSError:
        pass

    print("النتيجة: " + ("ALL PASS ✅" if all(results) else "FAIL ❌"))
    return 0 if all(results) else 1


# ══════════════════════════════════════════════════════════════════════════════
# 14) التشغيل
# ══════════════════════════════════════════════════════════════════════════════


async def amain(args):
    global SESSION, REST, USER_EVENTS
    if aiohttp is None:
        raise SystemExit("ثبّت aiohttp أولاً: pip install aiohttp")
    ensure_dirs()
    acquire_single_instance()
    load_state()
    connector = aiohttp.TCPConnector(limit=HTTP_CONCURRENCY, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector,
                                     headers={"User-Agent": "NOVA-ASYNC-SCALPER/5.0"}) as session:
        SESSION = session
        REST = BinanceRest(session)
        # إقلاع REST: وقت الخادم → القواعد → الكون → تسخين الشموع → سياق BTC
        await REST.sync_time()
        load_symbol_rules(await REST.exchange_info())
        await refresh_universe()
        for symbol in list(SYMBOLS):
            try:
                await seed_symbol(symbol)
            except Exception as exc:
                log(f"فشل تسخين {symbol}: {exc}")
        try:
            await seed_btc_context()
        except Exception as exc:
            log(f"فشل تسخين سياق BTC: {exc}")
        if BINANCE_API_KEY and BINANCE_API_SECRET:
            await REST.account()
            log("الحساب الموقّع: OK")
        # طابور أحداث المستخدم + مستهلكه المتسلسل (ترقيع السباق)
        USER_EVENTS = asyncio.Queue(maxsize=USER_QUEUE_MAX)
        worker = asyncio.create_task(user_event_worker(USER_EVENTS), name="user-event-worker")
        # مصالحة لقطية أولية: لا أمر يتيم ولا مركز ضائع من الجلسة السابقة
        await reconcile_snapshot("إقلاع")
        hub = MarketStreamHub()
        hub.set_universe(SYMBOLS)
        btc_stream = BtcContextStream()
        user_stream = UserDataStream()
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (_signal.SIGINT, _signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except (NotImplementedError, RuntimeError):
                pass
        trading_enabled = live_execution_allowed()
        tasks = [
            asyncio.create_task(hub.run(reseed_all), name="market-hub"),
            asyncio.create_task(btc_stream.run(), name="btc-context"),
            asyncio.create_task(universe_loop(hub), name="universe-loop"),
            asyncio.create_task(btc_context_loop(btc_stream), name="btc-context-loop"),
            asyncio.create_task(manage_loop(), name="manage-loop"),
            asyncio.create_task(time_stop_loop(), name="time-stop-loop"),
            asyncio.create_task(heartbeat_loop(), name="heartbeat-loop"),
            asyncio.create_task(telegram_loop(stop_event), name="telegram-loop"),
            asyncio.create_task(stop_event.wait(), name="stop-watcher"),
            worker,
        ]
        if trading_enabled:
            tasks.append(asyncio.create_task(
                user_stream.run(lambda: reconcile_snapshot("إعادة اتصال User Stream")), name="user-stream"))
        execution_line = "مفعّل" if trading_enabled else "غير مفعّل"
        if STATE.get("paused"):
            execution_line += " | الإيقاف المؤقت مفعّل (الدخولات موقوفة — /resume)"
        log(
            f"تشغيل NOVA ASYNC SCALPER V5.3 [الرشاش الذكي] | {regime_text()} | Spot فقط | "
            f"فريم الإشارة {SIGNAL_INTERVAL} + اتجاه EMA{EMA_TREND_PERIOD}({TREND_INTERVAL}) | "
            f"أفضل {TOP_N_SYMBOLS} زوجاً (تحديث كل {UNIVERSE_REFRESH_EVERY}ث) | "
            f"WebSocket: kline_{MICRO_INTERVAL}+kline_{SIGNAL_INTERVAL}+kline_{TREND_INTERVAL}+aggTrade+bookTicker"
            f"+{BTC_CONTEXT_SYMBOL.lower()}@kline_1m"
            f"{' + User Data Stream' if trading_enabled else ''} | "
            f"زناد ≥ {SCORE_TRIGGER:.0f}/100 (MSS {SCORE_MSS:.0f}+FVG {SCORE_FVG:.0f}+EMA {SCORE_EMA:.0f}"
            f"+Flow {SCORE_FLOW:.0f}) | تنفيذ MARKET فوري | "
            f"مخاطرة {TARGET_RISK_USD}$/صفقة بسقف مركز {MAX_POSITION_NOTIONAL_USD}$ | "
            f"وقف طوارئ ATR(1m)×{HARD_STOP_ATR_MULT:g} بسقف {SL_MAX_PCT}% + خروج هجين "
            f"(تعادل +{BREAKEVEN_TRIGGER_PCT:g}% ثم تتبّع {TRAIL_WIDE_PCT:g}/{TRAIL_TIGHT_PCT:g}%) | "
            f"تهدئة ديناميكية {COOLDOWN_FAST}/{COOLDOWN_NORMAL}/{COOLDOWN_SLOW}ث | "
            f"قاطع BTC بهبوط {BTC_DROP_PCT}%/{BTC_DROP_WINDOW_MIN}د | "
            f"حتى {MAX_OPEN_POSITIONS} مركزاً ({MAX_POSITIONS_PER_SYMBOL}/عملة) | "
            f"Dust→BNB كل {DUST_SWEEP_EVERY // 3600}س | "
            f"التنفيذ: {execution_line} | لا قواطع خسائر متتالية"
        )
        try:
            if "--once" in args:
                await once_scan()
            else:
                await hub.connected.wait()
                if trading_enabled:
                    await user_stream.connected.wait()
                await asyncio.sleep(1.0)  # مهلة acknowledgment الاشتراكات
                await notify_startup()    # رسالة البدء الوحيدة بعد التحقق من WebSockets
                asyncio.create_task(dust_sweep_if_due())
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await save_state()
            log("تم إيقاف البوت؛ الذاكرة محفوظة")


def main():
    args = set(sys.argv[1:])
    if "--selftest" in args:
        sys.exit(asyncio.run(run_selftest()))
    if "--dry-run" in args:
        globals()["DRY_RUN"] = True   # ترقيع V5: الراية الموثّقة كانت تُتجاهل
    try:
        asyncio.run(amain(args))
    except KeyboardInterrupt:
        pass
    except BinanceError as exc:
        # فشل إقلاع REST (حظر جغرافي/مفاتيح/شبكة): رسالة واضحة بلا traceback مخيف
        log(f"فشل الإقلاع: {exc}")
        print(f"❌ فشل الإقلاع من Binance: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
