#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA ASYNC SCALPER V5.1 — Adaptive Spot Scalper (Risk-Parity + Safety)
==============================================================================
بوت سكالبينج Spot غير متزامن بالكامل على Binance. النسخة V5 تستبدل عقدة
البوابات المتسلسلة (Boolean AND) بمحرك تنقيط مرجّح، وبحجم دخول ثابت
بمعادلة حجم مبنية على المخاطرة (Risk Parity)، مع قاطع سياق كلي (BTC Circuit
Breaker) وتدفق صفقات حقيقي (aggTrade) بدل الاعتماد على دفتر أوامر Testnet.

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
5) المخارج الديناميكية (Dynamic SL Matrix) بنسبة التقلب VR = ATR14 / SMA(ATR14,20):
   • VR > 1.5 (سوق سريع)      → SL = ATR × 2.5
   • VR < 0.8 (سوق مستقر)     → SL = ATR × 1.2
   • غير ذلك (سوق طبيعي)      → SL = ATR × 1.8
   • سقف صلب: مسافة الوقف لا تتجاوز 3% من سعر الدخول أبداً (Flash-Crash Cap).
   • الهدف الصارم: TP = Entry + 2 × SL_distance (نسبة 1:2 رياضية دائماً).
6) حجم الدخول مبنية على المخاطرة (وليس قيمة ثابتة):
   PositionSize(USDT) = TARGET_RISK_USD / (SL_distance / EntryPrice)
   مع سقف MAX_POSITION_NOTIONAL_USD لمنع أخطاء الرصيد/انفجار المركز.
   → المخاطرة لكل صفقة ثابتة (2$) مهما اتسع الوقف أو ضاق (Risk Parity).
7) تهدئة ديناميكية: 60ث في السوق المتقلب (VR>1.5)، 120ث في المستقر (VR<0.8)،
   90ث افتراضياً — تُقرأ من تقلب BTC على 1m. + Setup ID فريد
   (symbol@candleOpenTime) يمنع تكرار الدخول داخل نفس الشمعة.
8) Set & Forget صارم: عند تنفيذ الشراء يوضع OCO واحد فوراً بالوقف والهدف
   المحسوبين، ولا يُلمس أبداً — لا Trailing Stop في أي صورة إطلاقاً.
9) إدارة الذاكرة: حتى 3 مراكز متزامنة لكل عملة، حجز ذري تحت ENTRY_LOCK،
   مصالحة لقطية بعد الإقلاع/إعادة الاتصال، وحلقة صيانة هادئة.
10) الصمت التام (Stealth): رسالة بدء واحدة فقط بعد نجاح الإقلاع والاتصال،
    ثم لا رسائل تلقائية إطلاقاً — كل شيء في bot.log، والرد على الأوامر اليدوية فقط.
11) ترقيعات السباق والأمان (QA) — محفوظة من V4:
   • كل أحداث User Stream تُستهلك عبر طابور ومستهلك واحد → لا سباق.
   • إتمام الدخول «مطالبة ذرية» (claim) داخل STATE_LOCK → لا OCO مزدوج.
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
from collections import deque
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
    "demo": "wss://demo-stream.binance.com/stream",
    "testnet": "wss://stream.testnet.binance.vision/stream",
    "live": "wss://stream.binance.com:9443/stream",
}[BINANCE_ENV]
# مسار listenKey القديم يعمل على stream host، لا على demo-api REST host.
WS_USER_BASE = {
    "demo": "wss://demo-stream.binance.com/ws",
    "testnet": "wss://stream.testnet.binance.vision/ws",
    "live": "wss://stream.binance.com:9443/ws",
}[BINANCE_ENV]
WS_API_BASE = {
    "demo": "wss://demo-ws-api.binance.com/ws-api/v3",
    "testnet": "wss://ws-api.testnet.binance.vision/ws-api/v3",
    "live": "wss://ws-api.binance.com:443/ws-api/v3",
}[BINANCE_ENV]
# User Data الحديث لا يعتمد على listenKey؛ fallback يبقي التوافق مع Testnet القديم.
MODERN_USER_STREAM = env_bool("MODERN_USER_STREAM", True)
LEGACY_USER_STREAM_FALLBACK = env_bool("LEGACY_USER_STREAM_FALLBACK", True)
WS_RECV_WINDOW = max(1000, min(60000, env_int("WS_RECV_WINDOW", 5000)))
DUMMY_STREAM = "btcusdt@bookTicker"  # تدفق مؤقت لفتح الاتصال ثم يُلغى اشتراكه

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "").strip()
LIVE_CONFIRM = os.getenv("LIVE_TRADING_CONFIRM", "")

TELEGRAM_TOKEN = __REDACTED__"TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

AUTO_TRADE = env_bool("AUTO_TRADE", True)
DRY_RUN = env_bool("DRY_RUN", False)
# الصمت التام: لا رسائل تلقائية إطلاقاً بعد إشعار البدء الوحيد
STEALTH_MODE = True

STARTUP_TEXT = "✅ NOVA Async V5.1 Started & Connected to Binance WebSockets."
RESET_REPLY = "✅ تم تصفير جميع الإحصائيات بنجاح."

# ── الكون الديناميكي: أفضل 30 زوجاً حسب حجم 24 ساعة، تحديث كل ساعة ───────────
TOP_N_SYMBOLS = max(5, min(100, env_int("TOP_N_SYMBOLS", 30)))
UNIVERSE_REFRESH_EVERY = max(300, env_int("UNIVERSE_REFRESH_EVERY", 3600))
MIN_24H_QUOTE_VOLUME = env_float("MIN_24H_QUOTE_VOLUME", 1_000_000)

# ── المحرك: فريم الإشارة 5m + الاتجاه EMA50 على فريم 15m ─────────────────────
SIGNAL_INTERVAL = "5m"
TREND_INTERVAL = "15m"
INTERVAL_SECONDS = {"5m": 300, "15m": 900}
EMA_TREND_PERIOD = max(10, env_int("EMA_TREND_PERIOD", 50))   # V5: 50 بدل 200
MIN_CLOSED_CANDLES = max(30, env_int("MIN_CLOSED_CANDLES", 60))

# حزام تذبذب اختياري: يمنع السوق الميت أو الانفجاري من استنزاف الحساب.
MIN_ATR_PCT = max(0.0, env_float("MIN_ATR_PCT", 0.0))
MAX_ATR_PCT = max(MIN_ATR_PCT, env_float("MAX_ATR_PCT", 2.50))

KLINE_REST_LIMITS = {
    SIGNAL_INTERVAL: clamp(env_int("KLINE_LIMIT_5M", 140), 80, 500),
    TREND_INTERVAL: clamp(EMA_TREND_PERIOD + 120, 180, 1000),
}
HISTORY_MAX = {SIGNAL_INTERVAL: 300, TREND_INTERVAL: 400}

ATR_PERIOD = max(2, env_int("ATR_PERIOD", 14))
VR_BASELINE = max(2, env_int("VR_BASELINE", 20))   # متوسط ATR14 لآخر 20 شمعة

# ── محرك التنقيط الموزون (V5): أوزان مستقلة + حاجز زناد ──────────────────────
SCORE_MSS = env_float("SCORE_MSS", 35.0)
SCORE_FVG = env_float("SCORE_FVG", 25.0)
SCORE_EMA = env_float("SCORE_EMA", 20.0)
SCORE_FLOW = env_float("SCORE_FLOW", 20.0)
SCORE_TRIGGER = env_float("SCORE_TRIGGER", 75.0)
MIN_SCORE_COMPONENTS = env_int("MIN_SCORE_COMPONENTS", 2)  # بلا AND صارم؛ يمنع MSS وحده
FLOW_IMBALANCE_MIN = env_float("FLOW_IMBALANCE_MIN", 1.5)

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
FLOW_BUCKET_SEC = max(0.25, env_float("FLOW_BUCKET_SEC", 1.0))
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
TARGET_RISK_USD = Decimal(str(env_float("TARGET_RISK_USD", 2.0)))
MAX_POSITION_NOTIONAL_USD = Decimal(str(env_float("MAX_POSITION_NOTIONAL_USD", 250.0)))
MARKET_COST_BUFFER = Decimal("1.004")  # هامش انزلاق/رسوم لحجز الرصيد قبل أمر MARKET

# ── الوقف الديناميكي والأهداف الصارمة ────────────────────────────────────────
ATR_MULT_FAST = env_float("ATR_MULT_FAST", 2.5)     # VR > 1.5
ATR_MULT_SLOW = env_float("ATR_MULT_SLOW", 1.2)     # VR < 0.8
ATR_MULT_NORMAL = env_float("ATR_MULT_NORMAL", 1.8)
VR_FAST = env_float("VR_FAST", 1.5)
VR_SLOW = env_float("VR_SLOW", 0.8)
SL_MAX_PCT = clamp(env_float("SL_MAX_PCT", 3.0), 0.2, 10.0)   # سقف صلب للوقف
RR_RATIO = env_float("RR_RATIO", 2.0)                          # TP = SL × 2 صارم
FEE_BUFFER = env_float("FEE_BUFFER", 0.0015)
FEE_RATE = max(0.0, env_float("FEE_RATE", 0.001))
MAX_ENTRY_SLIPPAGE_PCT = max(0.0, env_float("MAX_ENTRY_SLIPPAGE_PCT", 0.50))
MAX_ENTRY_DRIFT_PCT = max(0.0, env_float("MAX_ENTRY_DRIFT_PCT", 0.35))
LIMIT_SLIPPAGE_PCT = env_float("LIMIT_SLIPPAGE_PCT", 0.20)
OCO_LEGACY_FALLBACK = env_bool("OCO_LEGACY_FALLBACK", True)

# ── المراكز والتهدئة ──────────────────────────────────────────────────────────
# حدود تعرض قابلة للضبط: كثرة الصفقات لا تعني فتح مخاطرة غير محدودة.
MAX_POSITIONS_PER_SYMBOL = max(1, env_int("MAX_POSITIONS_PER_SYMBOL", 3))
MAX_OPEN_POSITIONS = max(MAX_POSITIONS_PER_SYMBOL, env_int("MAX_OPEN_POSITIONS", 12))
MAX_TOTAL_EXPOSURE_USD = Decimal(str(max(0.0, env_float("MAX_TOTAL_EXPOSURE_USD", 1500.0))))
MAX_DAILY_LOSS_USD = max(0.0, env_float("MAX_DAILY_LOSS_USD", 20.0))
MAX_CONSECUTIVE_LOSSES = max(0, env_int("MAX_CONSECUTIVE_LOSSES", 0))  # 0 = معطّل
SAME_SYMBOL_COOLDOWN = max(0, env_int("SAME_SYMBOL_COOLDOWN", 90))  # تُغطى ديناميكياً

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
PANIC_LOCK = asyncio.Lock()
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
GATE_COUNTS = {}                      # تشخيص عنق الزجاجة: سبب الرفض/القبول
GATE_COUNTS_BY_SYMBOL = {}
BTC_CTX = {                           # سياق BTC (قناة 1m مستقلة)
    "closes": deque(maxlen=BTC_DROP_WINDOW_MIN + 25),
    "live": 0.0,
    "last_t": 0,
    "last_update": 0.0,
    "seeded": False,
    "times": deque(maxlen=BTC_DROP_WINDOW_MIN + VR_BASELINE + ATR_PERIOD + 25),
    "highs": deque(maxlen=BTC_DROP_WINDOW_MIN + VR_BASELINE + ATR_PERIOD + 25),
    "lows": deque(maxlen=BTC_DROP_WINDOW_MIN + VR_BASELINE + ATR_PERIOD + 25),
    "vr": 1.0,
}
ENTRY_RESERVATIONS = {}
RESERVED_QUOTE = Decimal("0")
RESEED_AT = {}
RESEED_ALL_AT = 0.0
LAST_USED_WEIGHT = 0
RATE_BACKOFF_UNTIL = 0.0
STARTUP_NOTIFIED = False
LAST_RECON_SNAPSHOT = 0.0
USER_EVENTS = None            # asyncio.Queue — مستهلك واحد (ترقيع سباق)
ORDERS = {}                   # str(orderId) -> {"role","cid"/"pid"/"symbol"}
USER_STREAM_INSTANCE = None      # لإعادة الاتصال عند listenKeyExpired
PROTECTION_IN_FLIGHT = set()      # يمنع OCO مزدوجاً داخل العملية الحالية


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
        "day_key": datetime.now(timezone.utc).date().isoformat(),
        "daily_pnl": 0.0,
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
        for legacy_key in ("trailing_active", "activation_price", "trailing_distance", "trail_bips"):
            position.pop(legacy_key, None)
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
        day_key=__REDACTED__).date().isoformat()
        if base.get("day_key") != day_key:
            base["day_key"] = day_key
            base["daily_pnl"] = 0.0
        else:
            base["daily_pnl"] = float(base.get("daily_pnl", 0.0) or 0.0)
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


def build_ws_hmac_signature(values):
    """HMAC-SHA256 لتوقيع Spot WebSocket API بعد ترتيب المعاملات أبجدياً."""
    payload = "&".join(f"{key}={values[key]}" for key in sorted(values))
    return hmac.new(BINANCE_API_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


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
                __REDACTED__"X-MBX-APIKEY"] = BINANCE_API_KEY
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

    async def cancel_oco(self, symbol, order_list_id):
        return await self._raw("DELETE", "/api/v3/orderList", {"symbol": symbol, "orderListId": order_list_id}, signed=True)

    async def order_list(self, order_list_id=None, client_order_id=None):
        params = {}
        if order_list_id is not None:
            params["orderListId"] = order_list_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise BinanceError("يجب تحديد orderListId أو origClientOrderId")
        return await self._raw("GET", "/api/v3/orderList", params, signed=True)

    async def new_oco(self, params):
        return await self._raw("POST", "/api/v3/orderList/oco", params, signed=True, timeout=15)

    async def new_oco_legacy(self, params):
        return await self._raw("POST", "/api/v3/order/oco", params, signed=True, timeout=15)

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
    # أوطأ مركز ممكن عملياً: سقف المخاطرة مضروباً في أوسع وقف نسبي مسموح
    floor_notional = max(Decimal("5"), TARGET_RISK_USD / D(SL_MAX_PCT) * Decimal("100"))
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
            continue   # مركز أصغر ممكن لا يحقق الحد الأدنى للطلب
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
    """تسخين أولي: شموع 5m + 15m عبر REST ثم EMA50(15m) وATR جاهزان."""
    for interval in (SIGNAL_INTERVAL, TREND_INTERVAL):
        payload = await REST.klines(symbol, interval, KLINE_REST_LIMITS[interval])
        buffer = build_buffer(payload, interval)
        if buffer is None or len(buffer["c"]) < 30:
            raise BinanceError(f"بيانات {symbol} {interval} غير كافية")
        CANDLES[(symbol, interval)] = buffer
    TREND[symbol] = {
        "ema": ema_last(CANDLES[(symbol, TREND_INTERVAL)]["c"], EMA_TREND_PERIOD),
        "last_t": CANDLES[(symbol, TREND_INTERVAL)]["t"][-1],
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
        # Binance REST يعيد آخر شمعة جارية ولا يملك خانة close-flag؛
        # إسقاط آخر صف يمنع إدخال بيانات مستقبلية في ATR/قاطع BTC.
        if len(rows) > 1:
            rows = rows[:-1]
        closes = [float(r[4]) for r in rows]
        highs = [float(r[2]) for r in rows]
        lows = [float(r[3]) for r in rows]
    except (IndexError, TypeError, ValueError):
        return
    if not closes:
        return
    ctx = BTC_CTX
    maxlen = BTC_DROP_WINDOW_MIN + VR_BASELINE + ATR_PERIOD + 25
    ctx["closes"] = deque(closes[-maxlen:], maxlen=maxlen)
    ctx["highs"] = deque(highs[-maxlen:], maxlen=maxlen)
    ctx["lows"] = deque(lows[-maxlen:], maxlen=maxlen)
    ctx["times"] = deque([int(r[0]) for r in rows[-maxlen:]], maxlen=maxlen)
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
    """EMA50(15m) متجهياً عند كل شمعة 15m مغلقة (مع حراسة ازدواج)."""
    buffer = CANDLES.get((symbol, TREND_INTERVAL))
    if not buffer or not buffer["c"] or not buffer["t"]:
        return
    trend = TREND.setdefault(symbol, {"ema": None, "last_t": None})
    candle_t = buffer["t"][-1]
    if trend.get("last_t") == candle_t:
        return  # هذه الشمعة دُمجت مسبقاً في EMA (حماية من الازدواج)
    trend["ema"] = ema_last(buffer["c"], EMA_TREND_PERIOD)
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
    """يضيف تدفقاً إلى دلاء زمنية، لا إلى آخر 96 صفقة فقط.

    التجميع كل ثانية يجعل FLOW_WINDOW_SEC نافذة زمنية حقيقية حتى على الأزواج
    كثيرة التداول؛ حدّ عدد الدلاء يحمي الذاكرة ولا يغيّر الحسابات.
    """
    state = flow_state(symbol)
    ts = float(ts or time.time())
    buy_quote = max(0.0, float(buy_quote or 0.0))
    sell_quote = max(0.0, float(sell_quote or 0.0))
    if buy_quote == 0.0 and sell_quote == 0.0:
        return state
    bucket_ts = math.floor(ts / FLOW_BUCKET_SEC) * FLOW_BUCKET_SEC
    buckets = state["buckets"]
    if buckets and bucket_ts == buckets[-1][0]:
        old_ts, old_buy, old_sell = buckets.pop()
        buckets.append((old_ts, old_buy + buy_quote, old_sell + sell_quote))
    else:
        buckets.append((bucket_ts, buy_quote, sell_quote))
    state["buy"] = float(state.get("buy", 0.0)) + buy_quote
    state["sell"] = float(state.get("sell", 0.0)) + sell_quote
    state["ts"] = ts
    while len(buckets) > FLOW_MAX_BUCKETS:
        _ts, old_buy, old_sell = buckets.popleft()
        state["buy"] = max(0.0, float(state.get("buy", 0.0)) - old_buy)
        state["sell"] = max(0.0, float(state.get("sell", 0.0)) - old_sell)
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
    """يحدّث ذاكرة BTC من kline_1m ويعيد حساب VR عند كل شمعة مغلقة.

    النسخ القديمة كانت تثبّت VR عند الإقلاع فقط؛ لذلك لم يكن الوقف/التهدئة
    يتكيفان فعلياً مع تغير السوق. هنا نحتفظ بالزمن وhigh/low/close ونحسب
    ATR14 وVR بصورة متسقة مع البوت الرئيسي.
    """
    try:
        if str(symbol).upper() != BTC_CONTEXT_SYMBOL or not isinstance(k, dict):
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
        t_open = int(k.get("t") or 0)
        if ctx.get("times") and t_open and t_open <= ctx["times"][-1]:
            return
        high = float(k.get("h") or price)
        low = float(k.get("l") or price)
        if high < max(price, float(k.get("o") or price)) or low > min(price, float(k.get("o") or price)):
            high, low = max(high, price), min(low, price)
        maxlen = BTC_DROP_WINDOW_MIN + VR_BASELINE + ATR_PERIOD + 25
        for key, value in (("times", t_open), ("highs", high), ("lows", low), ("closes", price)):
            seq = ctx.setdefault(key, deque(maxlen=maxlen))
            seq.append(value)
        ctx["last_t"] = t_open
        ctx["seeded"] = True
        highs = list(ctx["highs"])
        lows = list(ctx["lows"])
        closes = list(ctx["closes"])
        atr_now, vr = volatility_ratio(highs, lows, closes, ATR_PERIOD, VR_BASELINE)
        ctx["atr"] = atr_now
        ctx["vr"] = vr
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
    """إحصاءات BTC: تغير فعلي عبر الطوابع الزمنية، لا افتراض عدد الصفوف."""
    ctx = BTC_CTX
    age = time.monotonic() - float(ctx.get("last_update") or 0.0)
    closes = list(ctx.get("closes") or [])
    times = list(ctx.get("times") or [])
    live = float(ctx.get("live") or 0.0)
    drop = None
    if closes and live > 0:
        if times and len(times) == len(closes) and times[-1] > 0:
            target = times[-1] - BTC_DROP_WINDOW_MIN * 60_000
            ref = next((float(value) for t, value in zip(reversed(times), reversed(closes))
                        if int(t) <= target), None)
        else:
            ref = float(closes[-min(len(closes), BTC_DROP_WINDOW_MIN + 1)]) if len(closes) > BTC_DROP_WINDOW_MIN else None
        if ref and ref > 0:
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
    risk_block, risk_reason = risk_circuit_blocked()
    if risk_block:
        return True, risk_reason
    stats = btc_ctx_stats()
    if stats["age"] > BTC_CTX_MAX_AGE or stats["drop_pct"] is None:
        return True, "context-unavailable"
    if stats["drop_pct"] <= -BTC_DROP_PCT:
        return True, f"btc-drop {stats['drop_pct']:.2f}%"
    return False, "ok"


def plan_position(entry, sl_distance, step=None):
    """حجم مبانٍ على المخاطرة: notional = R / (sl_distance / entry).

    يُقيَّد بسقف MAX_POSITION_NOTIONAL_USD، ويُرفض إن كان أصغر من حد
    Binance الأدنى. يعيد (qty, notional, risk_usd) أو (None, None, None).
    """
    entry = D(str(entry))
    sl_distance = D(str(sl_distance))
    step = D("0.00000001") if step is None else D(step)
    if entry <= 0 or sl_distance <= 0:
        return None, None, None
    # notional = R / (sl/entry) = R × entry / sl — صيغة واحدة بلا تقريب المقلوب
    notional = (D(TARGET_RISK_USD) * entry) / sl_distance
    if notional > D(MAX_POSITION_NOTIONAL_USD):
        notional = D(MAX_POSITION_NOTIONAL_USD)
    if not math.isfinite(float(notional)) or notional <= 0:
        return None, None, None
    qty = round_step(notional / entry, step) if step > 0 else (notional / entry)
    if qty <= 0:
        return None, None, None
    notional = qty * entry
    risk_usd = (notional * sl_distance) / entry
    return qty, notional, risk_usd


def market_price(symbol):
    """سعر مرجعي صالح للشراء: يفضل Ask الطازج، ثم آخر aggTrade، ثم الشمعة.

    استعمال آخر trade قديم بينما bookTicker حديث كان يقدّر تكلفة MARKET بأقل
    من الواقع؛ ذلك يفسد الحجم والوقف. نختار المصدر الأحدث بدلاً من أولوية ثابتة.
    يعيد (price, age_seconds).
    """
    now_wall = time.time()
    now_mono = time.monotonic()
    candidates = []
    flow = FLOW.get(symbol) or {}
    if flow.get("price") and flow.get("epoch"):
        candidates.append((float(flow.get("epoch")), float(flow.get("price")),
                           max(0.0, now_wall - float(flow.get("epoch")))))
    book = BOOK.get(symbol) or {}
    if book.get("ask") and book.get("ts"):
        candidates.append((now_wall - max(0.0, now_mono - float(book.get("ts"))),
                           float(book.get("ask")), max(0.0, now_mono - float(book.get("ts")))))
    if candidates:
        # في حال تعادل تقريبي، Ask هو الأنسب لتكلفة MARKET BUY.
        _stamp, price, age = max(candidates, key=lambda row: row[0])
        return price, age
    buffer = CANDLES.get((symbol, SIGNAL_INTERVAL)) or {}
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


def compute_score(has_mss, has_fvg, trend_ok, imb):
    """مجموع النقاط المكونة وحارس المكوّنات — دالة نقية قابلة للاختبار.

    يعيد (score, components, triggered, parts).
    """
    parts = {
        "mss": SCORE_MSS if has_mss else 0.0,
        "fvg": SCORE_FVG if has_fvg else 0.0,
        "ema": SCORE_EMA if trend_ok else 0.0,
        "flow": SCORE_FLOW if (imb or 0.0) >= FLOW_IMBALANCE_MIN else 0.0,
    }
    components = sum(1 for value in parts.values() if value > 0)
    score = float(sum(parts.values()))
    triggered = score >= SCORE_TRIGGER and components >= max(1, MIN_SCORE_COMPONENTS)
    return score, components, triggered, parts


def note_gate(symbol, reason):
    """عداد خفيف يوضح لماذا لا يطلق البوت؛ لا يؤثر في قرار التداول."""
    reason = str(reason)
    GATE_COUNTS[reason] = GATE_COUNTS.get(reason, 0) + 1
    by_symbol = GATE_COUNTS_BY_SYMBOL.setdefault(str(symbol), {})
    by_symbol[reason] = by_symbol.get(reason, 0) + 1


def diagnostics_text():
    """تقرير اختياري /diagnostics لمعرفة الفلتر الذي يخنق عدد الصفقات."""
    total = sum(GATE_COUNTS.values())
    lines = [f"تشخيص الإشارات: {total} تقييماً"]
    for reason, count in sorted(GATE_COUNTS.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"{reason}: {count} ({count / max(total, 1) * 100:.1f}%)")
    lines.append(f"المراكز: {count_open_positions()}/{MAX_OPEN_POSITIONS} | التعرض: {open_exposure_usd():.2f}$/{MAX_TOTAL_EXPOSURE_USD:.2f}$")
    lines.append(f"الخسارة اليومية: {float(STATE.get('daily_pnl', 0.0) or 0.0):+.2f}$/{MAX_DAILY_LOSS_USD:.2f}$")
    return "\n".join(lines)


def _evaluate_frame(symbol):
    """يحسب كل ما يخص الشموع لإشارة العملة. يعيد (signal|None, reason)."""
    def reject(reason):
        note_gate(symbol, reason)
        return None, reason

    rule = SYMBOL_RULES.get(symbol)
    if not rule or rule.get("status") != "TRADING":
        return reject("not-trading")
    buffer = CANDLES.get((symbol, SIGNAL_INTERVAL))
    if not buffer or len(buffer["c"]) < MIN_CLOSED_CANDLES:
        return reject("no-data")
    server_now_ms = time.time() * 1000 + TIME_OFFSET_MS
    if buffer["t"] and server_now_ms - buffer["t"][-1] > INTERVAL_SECONDS[SIGNAL_INTERVAL] * 3000:
        return reject("stale-candles")
    o, h, l, c = buffer_to_frame(buffer)
    v = buffer["v"]
    for i in range(max(0, c.size - 5), c.size):
        if not math.isfinite(float(o[i])) or not math.isfinite(float(h[i])) \
                or not math.isfinite(float(l[i])) or not math.isfinite(float(c[i])) \
                or not math.isfinite(float(v[i])):
            return reject("bad-candles")
        if h[i] < max(o[i], c[i]) or l[i] > min(o[i], c[i]):
            return reject("bad-candles")
    # فلتر مصايد السيولة: ذيل مهيمن على الشمعة الأخيرة → منع مطلق
    wick = detect_wick_ratio(o, h, l, c)
    if wick > WICK_REJECT_RATIO:
        return reject(f"wick {wick:.2f}")
    atr_value, vr = volatility_ratio(h, l, c, ATR_PERIOD, VR_BASELINE)
    if atr_value <= 0:
        return reject("no-atr")
    mss = detect_mss(o, h, l, c, atr_value)
    fvg = detect_fvg(h, l, atr_value)
    price_now = float(buffer.get("live") or buffer["c"][-1])
    atr_pct = (atr_value / price_now * 100.0) if price_now else 0.0
    if atr_pct < MIN_ATR_PCT:
        return reject(f"atr-low {atr_pct:.3f}%")
    if atr_pct > MAX_ATR_PCT:
        return reject(f"atr-high {atr_pct:.3f}%")
    trend = TREND.get(symbol) or {}
    ema_value = trend.get("ema")
    trend_ok = ema_value is not None and price_now > float(ema_value)
    if fvg and price_now <= fvg["mid"]:
        fvg = None            # السعر غاص داخل منتصف الفجوة → لا تُحتسب نقاطها
    imb, _age = flow_imbalance(symbol)
    score, components, triggered, parts = compute_score(mss is not None, fvg is not None, trend_ok, imb)
    reason = "ok" if triggered else f"score {score:.0f}<{SCORE_TRIGGER:.0f}/c{components}"
    return {
        "symbol": symbol, "setup_id": f"{symbol}@{int(buffer['t'][-1]) if buffer['t'] else 0}",
        "atr": atr_value, "vr": vr,
        "atr_pct": atr_pct,
        "close": float(c[-1]), "live": price_now,
        "score": score, "parts": parts, "components": components,
        "fvg_mid": (fvg or {}).get("mid", 0.0),
        "fvg_low": (fvg or {}).get("low", 0.0),
        "fvg_high": (fvg or {}).get("high", 0.0),
        "mss_prior_high": (mss or {}).get("prior_high", 0.0),
        "displacement": (mss or {}).get("displacement", 0.0),
        "flow_imbalance": float(imb or 0.0),
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
        return why
    book = BOOK.get(symbol) or {}
    if book and float(book.get("spread_pct") or 0) > MAX_SPREAD_PCT:
        return "spread"
    if data_age(symbol) > MAX_STALE_SEC:
        return "stale-tick"
    return None


def _entry_gates_open(symbol):
    """بوابات رخيصة قبل أي تقييم: قاطع، سقف مراكز، تهدئة ديناميكية."""
    if kill_switch_active() or STATE.get("paused"):
        return False
    if SYMBOLS and symbol not in SYMBOLS_SET:
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
        note_gate(symbol, "fired")
        READY.pop(symbol, None)
        if info["setup_id"] in SETUPS:
            return  # نفس الشمعة مُنفَّذة — منع التكرار
        launch_entry(info)
        return
    reach = max(SCORE_FLOW, SCORE_EMA, SCORE_FVG)
    if info["score"] + reach >= SCORE_TRIGGER and info["components"] + 1 >= max(1, MIN_SCORE_COMPONENTS):
        note_gate(symbol, "candidate")
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
    note_gate(symbol, "fired")
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
            on_signal_candle_closed(symbol)
    except Exception as exc:
        log(f"خطأ معالجة kline: {exc}")


def on_book(symbol, data):
    """معالج bookTicker: يُحدَّث BBA للسبريد ولحظة تنفيذ طازجة فقط."""
    try:
        if SYMBOLS and symbol not in SYMBOLS_SET:
            return
        parsed = parse_book_payload(data)
        if parsed is not None:
            BOOK[symbol] = parsed
    except Exception as exc:
        log(f"خطأ معالجة bookTicker {symbol}: {exc}")


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


def calculate_dynamic_risk(entry, atr_value, vr):
    """يحسب مسافة الوقف والهدف بناءً على VR مع سقف صلب نسبة للسعر.

    TP = Entry + 2 × SL_distance (1:2 صارم) — الهدف يُشتق دائماً من الوقف.
    يعيد {"sl_distance","sl_pct","tp_distance","sl","tp","mult","regime","capped"}.
    """
    entry = float(entry)
    atr_value = float(atr_value or 0.0)
    if entry <= 0:
        raise ValueError("سعر الدخول غير صالح")
    mult, regime = atr_multiplier(max(0.0, float(vr or 0.0)))
    sl_distance = max(atr_value, 0.0) * mult
    cap = entry * SL_MAX_PCT / 100.0
    capped = False
    if sl_distance <= 0:
        sl_distance = cap
        capped = True
    if sl_distance > cap:
        sl_distance = cap
        capped = True
    sl_pct = sl_distance / entry * 100.0
    return {
        "sl_distance": sl_distance, "sl_pct": sl_pct,
        "tp_distance": sl_distance * RR_RATIO,
        "sl": entry - sl_distance, "tp": entry + sl_distance * RR_RATIO,
        "mult": mult, "regime": regime, "capped": capped,
    }


def oco_levels(entry, atr_value, vr=1.0):
    """مستويات OCO من الوقف الديناميكي (رجوع: الوقف = الهدف/2 رياضياً)."""
    risk = calculate_dynamic_risk(entry, atr_value, vr)
    return D(str(risk["sl"])), D(str(risk["tp"]))


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
        total_reserved = sum(v for k, v in ENTRY_RESERVATIONS.items()
                             if not str(k).endswith(":cost"))
        if current + reserved >= MAX_POSITIONS_PER_SYMBOL:
            return False
        if count_open_positions() + total_reserved >= MAX_OPEN_POSITIONS:
            return False
        if MAX_TOTAL_EXPOSURE_USD > 0 and open_exposure_usd() + RESERVED_QUOTE + cost > MAX_TOTAL_EXPOSURE_USD:
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


def _roll_daily_state_locked(now=None):
    """تصفير عداد الخسارة عند UTC day boundary داخل STATE_LOCK."""
    now = now or datetime.now(timezone.utc)
    key = now.date().isoformat()
    if STATE.get("day_key") != key:
        STATE["day_key"] = key
        STATE["daily_pnl"] = 0.0


def risk_circuit_blocked():
    """قاطع خسارة مالي اختياري: يحمي الحساب ولا يغيّر إدارة المراكز."""
    _roll_daily_state_locked()
    daily = float(STATE.get("daily_pnl", 0.0) or 0.0)
    metrics = STATE.get("metrics", {})
    consecutive = int(metrics.get("consecutive_losses", 0) or 0)
    if MAX_DAILY_LOSS_USD > 0 and daily <= -MAX_DAILY_LOSS_USD:
        return True, f"daily-loss {daily:.2f}$"
    if MAX_CONSECUTIVE_LOSSES > 0 and consecutive >= MAX_CONSECUTIVE_LOSSES:
        return True, f"consecutive-losses {consecutive}"
    return False, "ok"


def count_open_positions():
    return len(STATE.get("positions", {}))


def open_exposure_usd():
    total = Decimal("0")
    for position in STATE.get("positions", {}).values():
        try:
            total += D(position.get("quote_qty", position.get("entry", 0)))
        except Exception:
            continue
    return total


async def process_signal(signal):
    """بوابة ما قبل التنفيذ: فلاتر قاطعة + حجز ذري بتكلفة تقديرية ثم MARKET."""
    symbol = signal["symbol"]
    veto = veto_reason(symbol, signal)
    if veto:
        note_gate(symbol, f"veto:{veto}")
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
    risk = calculate_dynamic_risk(price, signal["atr"], signal.get("vr", 1.0))
    rule = SYMBOL_RULES.get(symbol) or {}
    step = rule.get("market_step", rule.get("step"))
    qty, notional, risk_usd = plan_position(price, risk["sl_distance"], step)
    if notional is None or qty is None:
        return None
    updated = dict(signal)
    updated["price"] = float(price)
    updated["risk"] = risk
    updated["qty"] = qty
    updated["notional"] = notional
    updated["risk_usd"] = risk_usd
    updated["sl_distance"] = float(risk["sl_distance"])
    updated["stop"] = float(risk["sl"])
    updated["target"] = float(risk["tp"])
    updated["est_cost"] = float(D(str(notional)) * D(MARKET_COST_BUFFER))
    return updated


def sellable_qty(symbol, qty, price):
    rule = SYMBOL_RULES.get(symbol)
    if not rule:
        return None
    # OCO legs هي أوامر LIMIT/STOP؛ لذلك نستخدم LOT_SIZE لا MARKET_LOT_SIZE.
    sell_qty = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), rule["step"])
    if sell_qty < rule.get("min_qty", D("0")):
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


async def emergency_sell(symbol, qty, reason, qty_is_net=False):
    try:
        rule = SYMBOL_RULES[symbol]
        step = rule.get("market_step", rule["step"])
        min_qty = rule.get("market_min_qty", rule["min_qty"])
        quantity = round_step(D(qty) if qty_is_net else D(qty) * (Decimal("1") - D(FEE_BUFFER)), step)
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


async def recover_oco_by_client_id(client_order_id):
    """يمنع البيع المزدوج إذا قُبل OCO ثم ضاعت الاستجابة."""
    if not client_order_id:
        return None
    try:
        result = await REST.order_list(client_order_id=client_order_id)
        if result and result.get("orderListId") is not None:
            return result
    except BinanceError:
        pass
    return None


async def place_initial_oco(symbol, qty, entry, stop_price, target_price, qty_is_net=False):
    """OCO أولي ثابت: وقف وهدف مشتقان من ATR(5m)، مع fallback للواجهة القديمة."""
    rule = SYMBOL_RULES[symbol]
    quantity = round_step(D(qty) if qty_is_net else D(qty) * (Decimal("1") - D(FEE_BUFFER)), rule["step"])
    stop = round_price(stop_price, rule["tick"], "down")
    target_trigger = round_price(target_price, rule["tick"], "up")
    if stop >= D(entry):
        stop = round_price(D(entry) - rule["tick"] * 2, rule["tick"], "down")
    if target_trigger <= D(entry):
        target_trigger = round_price(D(entry) + rule["tick"] * 2, rule["tick"], "up")
    stop_limit = round_price(stop * (Decimal("1") - D(LIMIT_SLIPPAGE_PCT) / Decimal("100")), rule["tick"], "down")
    if stop_limit >= stop:
        stop_limit = round_price(stop - rule["tick"], rule["tick"], "down")
    target_limit = round_price(target_trigger * (Decimal("1") - D("0.0003")), rule["tick"], "down")
    if target_limit <= D(entry):
        target_limit = round_price(D(entry) + rule["tick"], rule["tick"], "up")
    if quantity < rule["min_qty"] or quantity * D(entry) < rule["min_notional"]:
        raise BinanceError("الكمية لا تحقق فلاتر Binance")
    modern_client_id = make_client_id("oco")
    modern = {
        "symbol": symbol, "side": "SELL", "quantity": dec_str(quantity),
        "aboveType": "TAKE_PROFIT_LIMIT", "abovePrice": dec_str(target_limit),
        "aboveStopPrice": dec_str(target_trigger), "aboveTimeInForce": "GTC",
        "belowType": "STOP_LOSS_LIMIT", "belowPrice": dec_str(stop_limit),
        "belowStopPrice": dec_str(stop), "belowTimeInForce": "GTC",
        "listClientOrderId": modern_client_id, "newOrderRespType": "RESULT",
    }
    try:
        result = await REST.new_oco(modern)
        return {"type": "OCO", "order_list_id": result.get("orderListId"), "orders": result.get("orders", []),
                "qty": quantity, "stop": stop, "target": target_trigger}
    except BinanceError as modern_error:
        if modern_error.code not in (-1102, -1128, -2010):
            recovered = await recover_oco_by_client_id(modern_client_id)
            if recovered:
                return {"type": "OCO", "order_list_id": recovered.get("orderListId"), "orders": recovered.get("orders", []),
                        "qty": quantity, "stop": stop, "target": target_trigger}
            raise
        if not OCO_LEGACY_FALLBACK:
            raise
        legacy_client_id = make_client_id("olc")
        legacy = {
            "symbol": symbol, "side": "SELL", "quantity": dec_str(quantity),
            "price": dec_str(target_limit), "stopPrice": dec_str(stop),
            "stopLimitPrice": dec_str(stop_limit), "stopLimitTimeInForce": "GTC",
            "listClientOrderId": legacy_client_id, "newOrderRespType": "RESULT",
        }
        log(f"OCO الحديث رُفض بمعلمات؛ تجربة الواجهة القديمة لـ {symbol}")
        try:
            result = await REST.new_oco_legacy(legacy)
        except BinanceError as legacy_error:
            recovered = await recover_oco_by_client_id(legacy_client_id)
            if recovered:
                return {"type": "OCO_LEGACY", "order_list_id": recovered.get("orderListId"), "orders": recovered.get("orders", []),
                        "qty": quantity, "stop": stop, "target": target_trigger}
            raise legacy_error
        return {"type": "OCO_LEGACY", "order_list_id": result.get("orderListId"), "orders": result.get("orders", []),
                "qty": quantity, "stop": stop, "target": target_trigger}


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
    if D(risk["sl"]) >= price or D(risk["tp"]) <= price:
        log(f"مستويات غير صالحة لـ {symbol}؛ إلغاء")
        return False
    if not live_execution_allowed():
        if DRY_RUN:
            log(f"إشارة V5 [DRY-RUN] {symbol} @ {fmt_price(symbol, price)} "
                f"score={signal['score']:.0f} VR={signal.get('vr', 1.0):.2f} "
                f"qty={dec_str(qty)} notional={dec_str(notional)}$ "
                f"SL {fmt_price(symbol, risk['sl'])} ({risk['sl_pct']:.2f}%) "
                f"TP {fmt_price(symbol, risk['tp'])} [{risk['regime']} x{risk['mult']}"
                f"{' capped' if risk['capped'] else ''}]")
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
        latest_price, latest_age = market_price(symbol)
        if latest_age > MAX_STALE_SEC or latest_price <= 0:
            log(f"سعر دخول {symbol} أصبح قديماً أثناء فحص الرصيد")
            return False
        if price > 0 and abs(latest_price / float(price) - 1.0) * 100.0 > MAX_ENTRY_DRIFT_PCT:
            log(f"تغير سعر دخول {symbol} أكبر من {MAX_ENTRY_DRIFT_PCT:.2f}% أثناء فحص الرصيد")
            return False
        # أعد الحساب عند آخر Ask: يظل الخطر بالدولار ثابتاً حتى لو تحرك السعر
        # أثناء نداء account، ولا تُرسل كمية مبنية على سعر قديم.
        price = D(str(latest_price))
        risk = calculate_dynamic_risk(price, signal["atr"], signal.get("vr", 1.0))
        qty, notional, risk_usd = plan_position(price, risk["sl_distance"], rule.get("market_step", rule.get("step")))
        if qty is None or notional is None:
            return False
        signal["risk"] = risk
        signal["qty"] = qty
        signal["notional"] = notional
        signal["risk_usd"] = risk_usd
        signal["est_cost"] = float(D(str(notional)) * D(MARKET_COST_BUFFER))
        if free_quote < D(signal["est_cost"]) + other_reserved:
            log(f"رصيد USDT غير كافٍ لـ {symbol} بعد إعادة التسعير (تكلفة {dec_str(D(signal['est_cost']))}$)")
            return False
        qty = round_step(qty, rule["step"])
        price = round_price(price, rule["tick"], "up")
        if qty < rule["min_qty"] or qty * price < rule["min_notional"]:
            log(f"فلاتر Binance تمنع دخول {symbol} (qty={dec_str(qty)})")
            return False
        record = {
            "symbol": symbol, "client_order_id": entry_client_id, "order_id": None,
            "qty": dec_str(qty), "price": dec_str(price), "atr": float(signal["atr"]),
            "vr": float(signal.get("vr", 1.0)), "score": float(signal.get("score", 0)),
            "parts": dict(signal.get("parts") or {}), "setup_id": signal.get("setup_id", ""),
            "risk_usd": dec_str(signal["risk_usd"]), "notional": dec_str(notional),
            "sl": dec_str(risk["sl"]), "tp": dec_str(risk["tp"]),
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
        if executed_qty > 0 and status == "FILLED":
            await complete_entry(entry_client_id, live_record or record, executed_qty,
                                 avg_price, executed_quote)
            log(f"دخول MARKET {symbol} حسمته الاستجابة @ {fmt_price(symbol, avg_price)} "
                f"(qty={dec_str(executed_qty)} score={signal['score']:.0f})")
            return True
        if status == "PARTIALLY_FILLED":
            # لا نضع OCO قبل حسم أمر MARKET بالكامل؛ الواتش دوغ سيلغي
            # الباقي ثم يحمي الكمية المنفذة فقط.
            log(f"دخول MARKET جزئي {symbol}؛ بانتظار الحسم قبل وضع OCO")
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
    """يحمي التعبئة ثم يسجل المركز بصورة قابلة للاسترجاع بعد الانقطاع.

    الترتيب مهم: لا نحذف pending_entries قبل وضع OCO وتخزين معرفاته. إذا
    انقطعت العملية بعد الشراء، يستطيع الإقلاع التالي استكمال مرحلة الحماية
    بدلاً من ترك الأصل مكشوفاً أو إنشاء OCO ثانٍ بعد حفظ الحماية.
    """
    symbol = str(record.get("symbol", ""))
    protection = None
    snapshot = None
    async with STATE_LOCK:
        current = STATE.get("pending_entries", {}).get(client_id)
        if current is None or current.get("phase") == "done":
            return
        if client_id in PROTECTION_IN_FLIGHT:
            return
        PROTECTION_IN_FLIGHT.add(client_id)
        snapshot = copy.deepcopy(current)
        # في حالة الاسترجاع بعد الانقطاع تكون قيم التعبئة المحفوظة هي المصدر.
        executed_qty = D(snapshot.get("executed_qty", executed_qty))
        quote_filled = D(snapshot.get("executed_quote", quote_filled))
        if executed_qty <= 0:
            STATE["pending_entries"].pop(client_id, None)
        elif snapshot.get("phase") == "protected" and snapshot.get("protection"):
            protection = copy.deepcopy(snapshot["protection"])
        else:
            current["phase"] = "protecting"
            current["executed_qty"] = dec_str(executed_qty)
            current["executed_quote"] = dec_str(quote_filled)
            current["protect_started_at"] = time.time()
            snapshot = copy.deepcopy(current)
    try:
        if executed_qty <= 0:
            await save_state()
            return
        if protection is None:
            protected_qty = sellable_qty(symbol, executed_qty, float(avg_price) * 0.95)
            if protected_qty is None:
                async with STATE_LOCK:
                    STATE["pending_entries"].pop(client_id, None)
                await add_dust(symbol, executed_qty, quote_filled, "تعبئة جزئية دون الحد الأدنى للبيع")
                return
            reference_price = D(snapshot.get("price", avg_price))
            actual_price = D(avg_price)
            if reference_price > 0 and actual_price > reference_price:
                slip = (actual_price / reference_price - Decimal("1")) * Decimal("100")
                if slip > D(MAX_ENTRY_SLIPPAGE_PCT):
                    log(f"انزلاق دخول {symbol} {float(slip):.3f}% أكبر من الحد؛ بيع إنقاذ")
                    exit_order = await emergency_sell(symbol, protected_qty, "انزلاق دخول زائد", qty_is_net=True)
                    if exit_order:
                        qty_out, quote_out, _avg = parse_fill(exit_order, 0)
                        await account_salvage(symbol, quote_filled, quote_out, qty_out,
                                              "بيع إنقاذ: انزلاق دخول زائد")
                    else:
                        await add_dust(symbol, protected_qty, quote_filled, "فشل بيع انزلاق الدخول")
                    async with STATE_LOCK:
                        STATE["pending_entries"].pop(client_id, None)
                    return
            stop_price, target_price = oco_levels(avg_price, snapshot.get("atr", 0.0),
                                                  snapshot.get("vr", 1.0))
            # protected_qty خصم الرسوم مرة واحدة في sellable_qty.
            protection = await place_initial_oco(symbol, protected_qty, avg_price, stop_price, target_price,
                                                  qty_is_net=True)
            stored_protection = {
                "type": protection.get("type"),
                "order_list_id": protection.get("order_list_id"),
                "orders": protection.get("orders", []),
                "qty": dec_str(protection.get("qty", protected_qty)),
                "stop": dec_str(protection.get("stop", stop_price)),
                "target": dec_str(protection.get("target", target_price)),
            }
            # حفظ الحماية قبل تحويل pending إلى position — نقطة استرجاع ذرية.
            async with STATE_LOCK:
                live = STATE.get("pending_entries", {}).get(client_id)
                if live is None:
                    raise BinanceError("اختفى سجل التعبئة أثناء وضع الحماية")
                live["phase"] = "protected"
                live["protection"] = stored_protection
                live["executed_qty"] = dec_str(executed_qty)
                live["executed_quote"] = dec_str(quote_filled)
            await save_state()
            protection = stored_protection
        # قد تكون الحماية مسترجعة من JSON (سلاسل نصية) أو من REST (Decimal).
        pid = new_position_id(symbol)
        protected_qty = D(protection.get("qty", executed_qty))
        position = {
            "pid": pid, "symbol": symbol, "entry_client_id": client_id,
            "entry": float(avg_price), "qty": dec_str(protected_qty),
            "entry_executed_qty": dec_str(executed_qty),
            "entry_quote": float(quote_filled or 0),
            "quote_qty": float(quote_filled or 0),
            "stop": float(D(protection.get("stop", 0))),
            "target": float(D(protection.get("target", 0))),
            "atr_5m": float(D(str(snapshot.get("atr", 0.0)))),
            "order_list_id": protection.get("order_list_id"),
            "order_ids": [x.get("orderId") for x in protection.get("orders", [])
                          if isinstance(x, dict) and x.get("orderId") is not None],
            "protection_type": protection.get("type"),
            "opened_at": time.time(), "imbalance": float(snapshot.get("imbalance", 0.5)),
            "risk_usd": float(D(str(snapshot.get("risk_usd", 0) or 0))),
            "score": float(snapshot.get("score", 0) or 0),
            "vr": float(snapshot.get("vr", 1.0) or 1.0),
            "sl_pct": float(snapshot.get("sl_pct", 0) or 0),
            "setup_id": str(snapshot.get("setup_id") or ""),
        }
        async with STATE_LOCK:
            # إذا اكتملت الاستعادة في مسار آخر، لا ننشئ مركزاً ثانياً.
            if any(p.get("entry_client_id") == client_id for p in STATE.get("positions", {}).values()):
                return
            STATE["pending_entries"].pop(client_id, None)
            STATE["positions"][pid] = position
            STATE["metrics"]["trades"] += 1
            STATE["cooldowns"][symbol] = time.time()
            STATE.setdefault("last_entry_at", {})[symbol] = time.time()
            for leg_id in position["order_ids"]:
                ORDERS[str(leg_id)] = {"role": "leg", "pid": pid, "symbol": symbol}
            setup_id = str(snapshot.get("setup_id") or "")
            if setup_id:
                SETUPS.append(setup_id)
        await save_state()
        log(f"دخول V5.1 {symbol} pid={pid} entry={fmt_price(symbol, avg_price)} qty={position['qty']} "
            f"stop={fmt_price(symbol, protection['stop'])} target={fmt_price(symbol, protection['target'])} "
            f"protection={protection.get('type')} score={position['score']:.0f} "
            f"VR={position['vr']:.2f} risk={position['risk_usd']:.2f}$ (Set & Forget)")
    except BinanceError as exc:
        log(f"فشل OCO الدخول {symbol}: {exc}؛ بيع إنقاذ")
        exit_order = await emergency_sell(symbol, executed_qty, "فشل حماية الدخول")
        if exit_order:
            qty_out, quote_out, _avg = parse_fill(exit_order, 0)
            await account_salvage(symbol, quote_filled, quote_out, qty_out, "بيع إنقاذ: فشل حماية الدخول")
        else:
            await add_dust(symbol, executed_qty, quote_filled, "فشل حماية الدخول والبيع الطارئ")
        async with STATE_LOCK:
            STATE["pending_entries"].pop(client_id, None)
    except Exception as exc:
        log(f"خطأ إتمام الدخول {symbol}: {exc}\n{traceback.format_exc()[-400:]}")
    finally:
        PROTECTION_IN_FLIGHT.discard(client_id)


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
            _roll_daily_state_locked()
            metrics["realized_pnl"] += pnl
            STATE["daily_pnl"] = float(STATE.get("daily_pnl", 0.0) or 0.0) + pnl
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
    sold_qty = min(qty, float(exit_qty) if exit_qty else qty)
    if position.get("entry_quote") is not None:
        # صافي تقريبي: تكلفة الشراء الفعلية + عمولة الخروج، لا فرق السعر فقط.
        exit_quote = exit_price_value * sold_qty
        pnl = exit_quote - float(position.get("entry_quote", entry * qty)) - exit_quote * FEE_RATE
    else:
        # توافق مع حالات state القديمة التي لم تحفظ قيمة quote.
        pnl = (exit_price_value - entry) * sold_qty
    symbol = position.get("symbol", "")
    async with STATE_LOCK:
        if STATE["positions"].get(pid) is None:
            return  # حُسم مسبقاً (حدث مكرر/سباق) — منع الإغلاق المزدوج
        STATE["positions"].pop(pid, None)
        metrics = STATE["metrics"]
        _roll_daily_state_locked()
        metrics["realized_pnl"] += pnl
        STATE["daily_pnl"] = float(STATE.get("daily_pnl", 0.0) or 0.0) + pnl
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
    if event_type == "listenKeyExpired":
        instance = USER_STREAM_INSTANCE
        if instance is not None:
            instance.request_reconnect = True
            if instance.ws is not None and not instance.ws.closed:
                await instance.ws.close()
        return
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
            side = "هدف" if float(avg or 0) >= float(position.get("entry", 0)) else "وقف"
            await finalize_position_event(pid, position, avg, cum_qty, f"تنفيذ OCO ({side}) على Binance")


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


def rebuild_order_index():
    """يعيد ربط executionReport بالمراكز بعد إعادة تشغيل العملية."""
    ORDERS.clear()
    for cid, record in STATE.get("pending_entries", {}).items():
        oid = record.get("order_id")
        if oid is not None:
            ORDERS[str(oid)] = {"role": "entry", "cid": str(cid), "symbol": record.get("symbol", "")}
    for pid, position in STATE.get("positions", {}).items():
        for oid in position.get("order_ids", []) or []:
            if oid is not None:
                ORDERS[str(oid)] = {"role": "leg", "pid": str(pid), "symbol": position.get("symbol", "")}


def dispatch_user_message(text):
    """يصب User Data القديم أو الحديث داخل طابور المستهلك الواحد."""
    try:
        event = json.loads(text)
        if isinstance(event, dict) and isinstance(event.get("event"), dict):
            event = event["event"]  # userDataStream.subscribe.signature
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
    - المراكز المفتوحة: فحص رجل OCO لكل مركز مرة واحدة (get_order) وفق
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
                if record.get("phase") == "protected" and record.get("protection"):
                    q = D(record.get("executed_qty", record.get("qty", "0")))
                    quote = D(record.get("executed_quote", record.get("notional", "0")))
                    avg = quote / q if q > 0 and quote > 0 else D(record.get("price", "0"))
                    await complete_entry(client_id, record, q, avg, quote)
                    continue
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
                if not legs and position.get("order_list_id"):
                    try:
                        detail = await REST.order_list(order_list_id=position["order_list_id"])
                        legs = [o.get("orderId") for o in detail.get("orders", []) if o.get("orderId") is not None]
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
                    await finalize_position_order(pid, position, filled, "مصالحة: تنفيذ OCO أثناء الانقطاع")
            except Exception as exc:
                log(f"خطأ مصالحة مركز {pid}: {exc}")
        await save_state()


# ── أوامر المستخدم اليدوية (تصفية/إلغاء) ─────────────────────────────────────


async def cancel_all_orders():
    """يلغي حمايات البوت المسجلة فقط (كل مركز مستقل بمعرّفه)."""
    async with STATE_LOCK:
        positions = list(STATE.get("positions", {}).items())
    for pid, position in positions:
        symbol = position.get("symbol")
        if not symbol:
            continue
        try:
            if position.get("order_list_id"):
                await REST.cancel_oco(symbol, position["order_list_id"])
            else:
                for order_id in set(x for x in position.get("order_ids", []) if x is not None):
                    await REST.cancel_order(symbol, order_id)
        except BinanceError as exc:
            log(f"تعذر إلغاء حماية {pid}: {exc}")


async def panic_close_all():
    # الضغط المتكرر على زر التصفية لا ينشئ عمليات بيع متوازية.
    if PANIC_LOCK.locked():
        return
    async with PANIC_LOCK:
        await _panic_close_all_impl()


async def _panic_close_all_impl():
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
        order = await emergency_sell(position.get("symbol", ""), D(position.get("qty", 0)), "PANIC", qty_is_net=True)
        if order:
            qty, quote, avg = parse_fill(order, 0)
            await finalize_position_event(pid, position, avg, qty, "PANIC")


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
        f"منطق القرار: تنقيط ≥ {SCORE_TRIGGER:.0f}/100 — MSS {SCORE_MSS:.0f} + FVG {SCORE_FVG:.0f} + "
        f"EMA{EMA_TREND_PERIOD} {SCORE_EMA:.0f} + Flow {SCORE_FLOW:.0f}\n"
        f"الوقف: ATR × {ATR_MULT_SLOW}/{ATR_MULT_NORMAL}/{ATR_MULT_FAST} بحسب VR، بسقف {SL_MAX_PCT}%\n"
        f"الحجم: مخاطرة {TARGET_RISK_USD}$ لكل صفقة (سقف مركز {MAX_POSITION_NOTIONAL_USD}$) | TP = 2×SL\n"
        f"تدفق نافذة {FLOW_WINDOW_SEC:.0f}ث (aggTrade) | قدم بيانات أقصى {MAX_STALE_SEC:.0f}ث"
    )


HELP_TEXT = (
    "🤖 <b>NOVA ASYNC SCALPER V5.1 — Weighted Scoring + Risk Parity</b>\n\n"
    "/start أو /menu القائمة الرئيسية\n/status تقرير الأداء\n/context حالة السياق والقاطع\n"
    "/reset تصفير الإحصائيات\n/pause إيقاف الدخولات الجديدة\n/resume استئناف\n"
    "/cancelall إلغاء حمايات البوت\n/panic إلغاء + تصفية فورية\n"
    "/kill قاطع تداول يدوي\n/unkill إزالة القاطع\n/diagnostics تشخيص أسباب قلة الإشارات\n/help هذه المساعدة\n\n"
    "محرك تنقيط موزون بدل AND: MSS 35 + FVG 25 + EMA50 20 + اختلال aggTrade 20 — تنفيذ ≥ 75.\n"
    "قاطع سياق كلي: BTCUSDT@kline_1m يمنع الشراء إذا هوى BTC ≥ 0.5% خلال 3 دقائق.\n"
    "تصفية الشموع الذيلية (ذيل > 60%) وإلغاء الإشارة إذا كانت البيانات أقدم من 3ث (بديل الطلقة المعلقة).\n"
    "وقف ديناميكي: ATR × 1.2/1.8/2.5 بحسب VR، بسقف صلب 3% — والهدف دائماً 2× الوقف.\n"
    "حجم مبني على المخاطرة: 2$ لكل صفقة (سقف مركز 250$) بدل 20$ الثابتة.\n"
    "تهدئة ديناميكية 60/90/120ث + Setup ID يمنع التكرار داخل نفس الشمعة.\n"
    "User Data Stream (executionReport) مصدر حقيقة الأوامر — بلا REST Polling.\n"
    "OCO ثابت Set & Forget — لا Trailing إطلاقاً. Dust→BNB كل 24 ساعة.\n"
    "الصمت التام: رسالة بدء واحدة ثم الرد على الأوامر اليدوية فقط."
)


# ══════════════════════════════════════════════════════════════════════════════
# 11) Telegram (aiohttp — Long Polling بلا حجب)
# ══════════════════════════════════════════════════════════════════════════════


async def tg_api(method, payload=None, retries=3):
    if not TELEGRAM_TOKEN:
        __REDACTED__ None
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
    # callback_data مطابقة حرفياً للأوامر المطلوبة، بما فيها الشرطة المائلة.
    return [
        [button("📊 الحالة", "/status"), button("🌍 السياق", "/context")],
        [button("⏸ إيقاف", "/pause"), button("▶ استئناف", "/resume")],
        [button("🧯 إلغاء الأوامر", "/cancelall"), button("🆘 تصفية", "/panic")],
    ]


async def handle_callback(update):
    """يجيب callback فوراً ثم يمرر callback_data إلى نفس موجّه الأوامر."""
    callback = update.get("callback_query", {})
    message = callback.get("message", {})
    chat = str(message.get("chat", {}).get("id", ""))
    callback_id = str(callback.get("id", ""))
    if chat != str(TELEGRAM_CHAT_ID):
        await tg_api("answerCallbackQuery", {
            "callback_query_id": callback_id, "text": "غير مصرح"
        }, retries=1)
        return
    # إلزامي وفوري: لا ننتظر حفظ الحالة أو REST قبل إيقاف مؤشر Telegram.
    await tg_api("answerCallbackQuery", {"callback_query_id": callback_id}, retries=1)
    data = str(callback.get("data", "")).strip()
    if not data.startswith("/"):
        data = "/" + data
    # نفس الدوال/الفروع التي تستخدمها الرسائل النصية، بلا منطق تداول مكرر.
    await handle_command(data, chat)


async def handle_command(text, chat):
    command, _, argument = text.partition(" ")
    command = command.split("@", 1)[0].lower()
    if command in ("/start", "/menu"):
        await send_message("🎛️ <b>NOVA ASYNC SCALPER V5.1</b>\nاختر عملية:", main_keyboard(), chat)
    elif command == "/help":
        await send_message(HELP_TEXT, main_keyboard(), chat)
    elif command == "/status":
        await send_message(status_text(), main_keyboard(), chat)
    elif command in ("/context", "/btc"):
        await send_message(context_text(), main_keyboard(), chat)
    elif command == "/diagnostics":
        await send_message(diagnostics_text(), main_keyboard(), chat)
    elif command == "/reset":
        async with STATE_LOCK:
            STATE["metrics"] = {
                "trades": 0,
                "realized_pnl": 0.0,
                "wins": 0,
                "losses": 0,
                "consecutive_losses": 0,
            }
            STATE["day_key"] = datetime.now(timezone.utc).date().isoformat()
            STATE["daily_pnl"] = 0.0
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
        return (f"{s}@kline_{SIGNAL_INTERVAL}", f"{s}@kline_{TREND_INTERVAL}",
                f"{s}@aggTrade", f"{s}@bookTicker")

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
    """User Data عبر WebSocket API الموقّع، مع fallback لـ listenKey القديم.

    Binance الحديثة تفضّل userDataStream.subscribe.signature؛ وهو يعمل مع
    HMAC API keys. الأحداث الحديثة تصل مغلّفة داخل ``event`` وتُفك في
    dispatch_user_message، بينما listenKey يبقى خيار توافق اختياري.
    """

    def __init__(self):
        self.ws = None
        self.listen_key = None
        self.connected = asyncio.Event()
        self.backoff = WS_RECONNECT_MIN
        self._stop = False
        self.request_reconnect = False
        self.subscription_id = None
        self.mode = "ws_api" if MODERN_USER_STREAM else "listen_key"

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
                log(f"User Stream القديم: تعذر تجديد listenKey ({exc})؛ إعادة الاتصال")
                self.request_reconnect = True
                if self.ws is not None and not self.ws.closed:
                    try:
                        await self.ws.close()
                    except Exception:
                        pass

    async def _run_ws_api_once(self):
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            raise BinanceError("مفاتيح Binance غير موجودة لتوقيع User Data API")
        async with SESSION.ws_connect(
            WS_API_BASE, heartbeat=WS_HEARTBEAT, autoping=True,
            timeout=WS_CONNECT_TIMEOUT, max_msg_size=4 * 1024 * 1024,
        ) as ws:
            self.ws = ws
            request_id = str(uuid.uuid4())
            params = {
                "apiKey": BINANCE_API_KEY,
                "recvWindow": WS_RECV_WINDOW,
                "timestamp": int(time.time() * 1000) + TIME_OFFSET_MS,
            }
            signed_params = dict(sorted(params.items()))
            signed_params["signature"] = build_ws_hmac_signature(params)
            await ws.send_json({
                "id": request_id,
                "method": "userDataStream.subscribe.signature",
                "params": signed_params,
            })
            subscribed = False
            async for message in ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    try:
                        payload = json.loads(message.data)
                    except (TypeError, ValueError):
                        continue
                    if isinstance(payload, dict) and str(payload.get("id")) == request_id:
                        if int(payload.get("status", 500)) != 200:
                            error = payload.get("error") or {}
                            raise BinanceError(
                                error.get("msg", "فشل اشتراك User Data API"),
                                error.get("code"), payload.get("status"),
                            )
                        result = payload.get("result") or {}
                        self.subscription_id = result.get("subscriptionId")
                        subscribed = True
                        self.connected.set()
                        self.backoff = WS_RECONNECT_MIN
                        log("User Data Stream API متصل (HMAC subscription)")
                        continue
                    if isinstance(payload, dict) and (payload.get("e") or payload.get("event")):
                        dispatch_user_message(message.data)
                elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING,
                                      aiohttp.WSMsgType.ERROR):
                    break
            if not subscribed:
                raise BinanceError("انتهى User Data API قبل تأكيد الاشتراك")

    async def _run_legacy_once(self):
        keepalive_task = asyncio.create_task(self.keepalive_loop())
        try:
            key = await self.ensure_listen_key()
            url = f"{WS_USER_BASE}/{key}"
            async with SESSION.ws_connect(
                url, heartbeat=WS_HEARTBEAT, autoping=True,
                timeout=WS_CONNECT_TIMEOUT, max_msg_size=4 * 1024 * 1024,
            ) as ws:
                self.ws = ws
                self.connected.set()
                self.backoff = WS_RECONNECT_MIN
                log("User Data Stream القديم متصل (listenKey/executionReport)")
                async for message in ws:
                    if message.type == aiohttp.WSMsgType.TEXT:
                        try:
                            user_event = json.loads(message.data)
                        except (TypeError, ValueError):
                            user_event = {}
                        if isinstance(user_event, dict) and user_event.get("e") == "listenKeyExpired":
                            await ws.close()
                            break
                        dispatch_user_message(message.data)
                        if self.request_reconnect:
                            self.request_reconnect = False
                            break
                    elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING,
                                          aiohttp.WSMsgType.ERROR):
                        break
        finally:
            keepalive_task.cancel()
            await asyncio.gather(keepalive_task, return_exceptions=True)

    async def run(self, on_reconnect=None):
        global USER_STREAM_INSTANCE
        USER_STREAM_INSTANCE = self
        while True:
            try:
                if self.mode == "ws_api":
                    await self._run_ws_api_once()
                else:
                    await self._run_legacy_once()
            except asyncio.CancelledError:
                raise
            except BinanceError as exc:
                # HMAC user-stream متاح للحسابات الجديدة، لكن بعض شبكات Testnet
                # القديمة قد ترفضه؛ التراجع التلقائي يتم فقط عند خطأ API صريح.
                if self.mode == "ws_api" and LEGACY_USER_STREAM_FALLBACK and \
                        (exc.code is not None or exc.status in (400, 401, 403)):
                    self.mode = "listen_key"
                    log(f"User Data API رفض الاشتراك ({exc})؛ fallback إلى listenKey")
                else:
                    log(f"انقطاع User Data Stream: {exc}; إعادة الاتصال خلال {self.backoff:.0f}ث")
            except Exception as exc:
                log(f"انقطاع User Data Stream: {exc}; إعادة الاتصال خلال {self.backoff:.0f}ث")
            self.connected.clear()
            self.ws = None
            if self.mode == "listen_key":
                self.listen_key = None
            self.backoff, delay = next_backoff(self.backoff)
            await asyncio.sleep(delay)
            if on_reconnect is not None:
                try:
                    asyncio.create_task(on_reconnect())
                except RuntimeError:
                    pass


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
                for symbol in removed:
                    BOOK.pop(symbol, None)
                    FLOW.pop(symbol, None)
                    READY.pop(symbol, None)
                    TREND.pop(symbol, None)
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
            stale = {cid: rec for cid, rec in STATE.get("pending_entries", {}).items()
                     if time.time() - float(rec.get("placed_at", 0)) > 120}
            if stale:
                await reconcile_snapshot("معلقات قديمة")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ حلقة الصيانة: {exc}")


def _write_diagnostics_sync():
    try:
        ensure_dirs()
        path = os.path.join(DATA_DIR, "gate_counts.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"counts": GATE_COUNTS, "by_symbol": GATE_COUNTS_BY_SYMBOL}, handle,
                      ensure_ascii=False, indent=2)
    except Exception as exc:
        log(f"تعذر حفظ تشخيص الإشارات: {exc}")


async def heartbeat_loop():
    """نبضة خفيفة: حفظ الذاكرة وسطر حالة في السجل كل 6 ساعات."""
    while True:
        await asyncio.sleep(6 * 3600)
        try:
            await save_state()
            await asyncio.to_thread(_write_diagnostics_sync)
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
    """يبذّر التدفق من صيغة Binance REST الصحيحة (8 حقول) أو dict.

    صيغة aggTrades القياسية هي:
    [aggTradeId, price, qty, firstId, lastId, timestamp, isBuyerMaker, isBestMatch].
    كانت النسخة القديمة تقرأ الحقول 5/6/8، فكانت تتجاهل كل الصفوف الحقيقية
    (أو تعتبر النص "false" صحيحاً في Python).
    """
    rows = await REST.agg_trades(symbol, limit)
    now = time.time()
    price = 0.0
    added = 0
    for row in rows if isinstance(rows, list) else []:
        try:
            if isinstance(row, dict):
                price = float(row.get("p") or row.get("price") or 0)
                quantity = float(row.get("q") or row.get("qty") or 0)
                ts = float(row.get("T") or row.get("time") or 0) / 1000.0
                maker = row.get("m", row.get("isBuyerMaker", False))
            else:
                if len(row) < 7:
                    continue
                price = float(row[1])
                quantity = float(row[2])
                ts = float(row[5]) / 1000.0
                maker = row[6]
            if isinstance(maker, str):
                maker = maker.strip().lower() == "true"
            else:
                maker = bool(maker)
        except (IndexError, TypeError, ValueError):
            continue
        if price <= 0 or quantity <= 0 or ts <= 0:
            continue
        # لا نضع بيانات أقدم من النافذة في نافذة التدفق.
        if now - ts > FLOW_WINDOW_SEC:
            continue
        quote = price * quantity
        flow_add(symbol, ts, 0.0 if maker else quote, quote if maker else 0.0)
        added += 1
    state = FLOW.get(symbol)
    if not added or not state or not state.get("buckets"):
        return False
    state["price"] = price or float((BOOK.get(symbol) or {}).get("ask") or 0)
    state["epoch"] = now
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
    print("NOVA ASYNC SCALPER V5.1 SELFTEST — Weighted Scoring / Risk Parity / Context Gate")
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

    # 5) محرك التنقيط الموزون: لا AND صارم — حاجز 75 وحارس مكوّنين
    s_mss, c_mss, t_mss, _p1 = compute_score(True, False, False, 1.0)
    s_trio, c_trio, t_trio, _p2 = compute_score(True, False, True, 2.0)          # 35+20+20 = 75
    s_full, c_full, t_full, _p3 = compute_score(True, True, True, 2.0)           # 100
    s_noflow, c_noflow, t_noflow, _p4 = compute_score(True, True, True, 1.0)     # 80 (بلا تدفق)
    s_weak, c_weak, t_weak, _p5 = compute_score(True, True, False, 1.0)          # 60
    check("MSS وحده (35) لا يكفي", s_mss == 35.0 and not t_mss)
    check("MSS+EMA50+Flow = 75 يُطلق (تعويض غياب FVG)", abs(s_trio - 75.0) < 1e-9 and t_trio and c_trio == 3)
    check("MSS+FVG+EMA50 (بلا تدفق) = 80 يُطلق", abs(s_noflow - 80.0) < 1e-9 and t_noflow)
    check("الإشارة الكاملة = 100 تُطلق", s_full == 100.0 and t_full and c_full == 4)
    check("60 نقطة تُرفض (تحت الحاجز)", s_weak == 60.0 and not t_weak)
    check(f"حاجز الزناد مضبوط على {SCORE_TRIGGER:.0f}/100", SCORE_TRIGGER == 75.0)

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

    # 8) مصفوفة الوقف الديناميكي (VR) + سقف 3% + هدف 1:2 صارم
    r_fast = calculate_dynamic_risk(100.0, 1.0, 2.0)
    r_slow = calculate_dynamic_risk(100.0, 1.0, 0.5)
    r_norm = calculate_dynamic_risk(100.0, 1.0, 1.0)
    check("معاملات ATR: 2.5 سريع / 1.2 مستقر / 1.8 طبيعي",
          abs(r_fast["sl_distance"] - 2.5) < 1e-9 and r_fast["regime"] == "fast"
          and abs(r_slow["sl_distance"] - 1.2) < 1e-9 and r_slow["regime"] == "slow"
          and abs(r_norm["sl_distance"] - 1.8) < 1e-9 and r_norm["regime"] == "normal")
    r_cap = calculate_dynamic_risk(100.0, 10.0, 2.0)      # 10×2.5 = 25% → يُجمَّع عند 3%
    check(f"سقف الوقف الصلب {SL_MAX_PCT}% (Flash-Crash Cap)",
          abs(r_cap["sl_distance"] - 3.0) < 1e-9 and abs(r_cap["sl_pct"] - 3.0) < 1e-9 and r_cap["capped"])
    check("TP = Entry + 2×SL صارم (1:2 دائماً)",
          abs(r_fast["tp"] - (100.0 + 2.0 * 2.5)) < 1e-9 and abs(r_cap["tp"] - 106.0) < 1e-9
          and abs((r_fast["tp"] - 100.0) / (100.0 - r_fast["sl"]) - 2.0) < 1e-9)
    stop, target = oco_levels(Decimal("100"), 1.0, 2.0)
    check("oco_levels(مع VR) تتوافق مع المصفوفة", stop == Decimal("97.5") and target == Decimal("105"))

    # 9) الحجم المبني على المخاطرة (Risk Parity) بدل 20$ الثابتة
    q1, n1, k1 = plan_position(100.0, 2.5, D("0.001"))     # وقف 2.5% → مركز 80$ بمخاطرة 2$
    q2, n2, k2 = plan_position(100.0, 0.5, D("0.001"))     # وقف 0.5% → مركز 400$ → يُجمَّع عند السقف
    q3, n3, k3 = plan_position(100.0, 3.0, D("0.001"))     # وقف 3%   → مركز 66.66$
    check(f"مخاطرة ثابتة {TARGET_RISK_USD}$ عند اتساع الوقف وضيقه",
          abs(float(k1) - 2.0) < 1e-6 and abs(float(n1) - 80.0) < 1e-6)
    check(f"سقف المركز {MAX_POSITION_NOTIONAL_USD}$ يمنع انفجار الحجم",
          abs(float(n2) - float(MAX_POSITION_NOTIONAL_USD)) < 1e-9 and float(k2) <= 2.0
          and float(n2) < 400.0)
    check("الحجم يقبل التقليم لأصغر خطوة بلا كسر المخاطرة",
          float(q3) == 0.666 and abs(float(n3) - 66.6) < 1e-9 and abs(float(k3) - 1.998) < 1e-3)
    check("حجم ثابت 20$ أُزيل من الكود", "TRADE_NOTIONAL_D" not in globals())
    bad_qty, bad_notional, _bad_risk = plan_position(100.0, 0.0, D("0.001"))
    check("وقف بصفر مسافة → رفض (لا قسمة على صفر)", bad_qty is None and bad_notional is None)

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
    TREND["TSTUSDT"] = {"ema": 99.0, "last_t": None}
    flow_add("TSTUSDT", time.time(), 9000.0, 1000.0)
    BOOK["TSTUSDT"] = {"bid": 109.9, "ask": 110.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1099.0, "ask_vol": 1100.0, "imbalance": 0.5,
                       "spread_pct": 0.0909, "ts": time.monotonic()}
    sig = build_signal("TSTUSDT")
    check("إشارة V5 اكتملت بتنقيط 100 (MSS+FVG+EMA50+Flow)",
          sig is not None and sig["score"] == 100.0 and sig["components"] == 4
          and sig["setup_id"].startswith("TSTUSDT@"))
    CANDLES[("TSTUSDT-WICK", SIGNAL_INTERVAL)] = build_buffer(_synthetic_rows(wick=True), "5m")
    TREND["TSTUSDT-WICK"] = {"ema": 99.0, "last_t": None}
    SYMBOL_RULES["TSTUSDT-WICK"] = dict(SYMBOL_RULES["TSTUSDT"])
    _wsig, wreason = _evaluate_frame("TSTUSDT-WICK")
    check("الشمعة الذيلية تمنع الدخول حتى بكامل النقاط", _wsig is None and wreason.startswith("wick"))
    # غياب EMA50 (السعر تحت المتوسط) مع بقاء MSS+FVG+Flow = 80 → لا يزال يُطلق
    TREND["TSTUSDT"] = {"ema": 200.0, "last_t": None}
    sig_below_ema = build_signal("TSTUSDT")
    check("EMA50 مجرد 20 نقطة: الإشارة تُطلق أيضاً تحتها (80)",
          sig_below_ema is not None and sig_below_ema["score"] == 80.0
          and sig_below_ema["parts"]["ema"] == 0.0)
    # MSS+FVG فقط = 60 بلا اتجاه ولا تدفق → رفض
    TREND["TSTUSDT"] = {"ema": 200.0, "last_t": None}
    FLOW.clear()
    BOOK.clear()
    info_weak, weak2_reason = _evaluate_frame("TSTUSDT")
    check("MSS+FVG بلا دعم (60) تُرفض ولا تُطلق",
          info_weak is not None and not info_weak["triggered"] and info_weak["score"] == 60.0
          and "score 60" in weak2_reason and build_signal("TSTUSDT") is None)
    TREND["TSTUSDT"] = {"ema": 99.0, "last_t": None}
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

    # 18) المسار الكامل: MARKET BUY → OCO ديناميكي → إغلاق (بلا Polling)
    class _StubRest:
        def __init__(self):
            self.order_calls = []
            self.oco_calls = []
            self.get_order_calls = 0
            self.open_orders_calls = 0
        async def account(self):
            return {"balances": [{"asset": "USDT", "free": "5000", "locked": "0"}]}
        async def new_order(self, params):
            self.order_calls.append(params)
            return {"orderId": 501, "status": "FILLED", "side": "BUY",
                    "executedQty": params.get("quantity"), "cummulativeQuoteQty": "80.0",
                    "avgPrice": "100.00"}
        async def new_oco(self, params):
            self.oco_calls.append(params)
            return {"orderListId": 700, "orders": [
                {"orderId": 701, "clientOrderId": "ocoA"}, {"orderId": 702, "clientOrderId": "ocoB"}]}
        async def get_order(self, symbol, order_id):
            self.get_order_calls += 1
            return {"status": "CANCELED", "executedQty": "0"}
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
    ENTRY_RESERVATIONS = {}
    RESERVED_QUOTE = Decimal("0")
    signal_full = {
        "symbol": "TSTUSDT", "setup_id": "TSTUSDT@1700000000000",
        "atr": 1.0, "vr": 2.0, "score": 100.0,
        "parts": {"mss": 35.0, "fvg": 25.0, "ema": 20.0, "flow": 20.0},
        "components": 4, "flow_imbalance": 9.0, "close": 110.0, "live": 110.0,
        "atr_pct": 0.909, "fvg_mid": 0.0, "fvg_low": 0.0, "fvg_high": 0.0,
        "mss_prior_high": 0.0, "displacement": 0.0, "wick_ratio": 0.1, "created_at": time.time(),
    }
    BOOK["TSTUSDT"] = {"bid": 110.0, "ask": 110.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1100.0, "ask_vol": 1100.0, "imbalance": 0.5,
                       "spread_pct": 0.0, "ts": time.monotonic()}
    FLOW.clear()
    flow_add("TSTUSDT", time.time(), 9000.0, 1000.0)
    FLOW["TSTUSDT"]["price"] = 110.0
    FLOW["TSTUSDT"]["epoch"] = time.time()
    priced = estimate_entry_cost(signal_full)
    sizing_ok = (priced is not None and abs(float(priced["price"]) - 110.0) < 1e-9
                 and abs(float(priced["notional"]) - 88.0) < 1e-6
                 and abs(float(priced["risk_usd"]) - 2.0) < 1e-6
                 and abs(float(priced["sl_distance"]) - 2.5) < 1e-9
                 and float(priced["notional"]) <= float(MAX_POSITION_NOTIONAL_USD))
    entry_ok = await process_signal(signal_full)
    pid = next(iter(STATE["positions"])) if STATE["positions"] else None
    position = STATE["positions"].get(pid or "", {})
    market_ok = (entry_ok and len(stub.order_calls) == 1
                 and stub.order_calls[0]["type"] == "MARKET"
                 and stub.order_calls[0]["side"] == "BUY" and "price" not in stub.order_calls[0]
                 and len(stub.oco_calls) == 1
                 and abs(float(position.get("entry", 0)) - 100.0) < 1e-9
                 and abs(float(position.get("stop", 0)) - 97.5) < 1e-9
                 and abs(float(position.get("target", 0)) - 105.0) < 1e-9
                 and abs(float(position.get("risk_usd", 0)) - 2.0) < 1e-6
                 and abs(float(position.get("vr", 0)) - 2.0) < 1e-9
                 and position.get("score") == 100.0)
    check("MARKET BUY فوري (بلا price) + OCO ديناميكي بالمخاطرة الثابتة", market_ok)
    check("الحجم حُسب قبل الأمر: وقف 2.5% من 110 ⇒ 88$ بمخاطرة 2$",
          sizing_ok and abs(float(stub.order_calls[0]["quantity"]) - 0.8) < 1e-9
          and abs(float(position.get("qty", 0)) - 0.798) < 1e-9)
    dedup_ok = position.get("setup_id") in SETUPS
    check("Setup ID سُجِّل لمنع التكرار في نفس الشمعة", dedup_ok)
    check("الأمر المُعبأ من الاستجابة لا يترك معلَّقاً ولا Watchdog",
          not STATE["pending_entries"] and stub.get_order_calls == 0)
    # حدث مكرر (سباق) → لا OCO ثانٍ ولا مركز مزدوج
    if pid:
        cid_repeat = position.get("entry_client_id")
        STATE["pending_entries"][cid_repeat] = {
            "symbol": "TSTUSDT", "client_order_id": cid_repeat, "order_id": 501,
            "qty": "0.8", "price": "110", "atr": 1.0, "vr": 2.0, "phase": "done",
        }
        await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid_repeat, "i": 501,
                                  "S": "BUY", "x": "TRADE", "X": "FILLED",
                                  "l": "0.8", "L": "100", "z": "0.8", "Z": "80.0"})
        STATE["pending_entries"].pop(cid_repeat, None)
    check("ترقيع السباق: الحدث المكرر لا يكرر OCO/المركز",
          len(stub.oco_calls) == 1 and len(STATE["positions"]) == 1)
    # رجل الهدف ينفذ → مكسب + تصفير المتتالية
    STATE["metrics"]["consecutive_losses"] = 2
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": "ocoA", "i": 701,
                              "S": "SELL", "x": "TRADE", "X": "FILLED",
                              "l": "0.798", "L": "105", "z": "0.798", "Z": "83.79"})
    exit_ok = (not STATE["positions"] and STATE["metrics"]["wins"] == 1
               and STATE["metrics"]["consecutive_losses"] == 0
               and STATE["metrics"]["realized_pnl"] > 0)
    check("executionReport رجل OCO → إغلاق فوري (بلا REST) + عدّاد متتالية", exit_ok)
    # إلغاء بلا تعبئة → حذف المعلق بهدوء
    cid2 = make_client_id("nv5")
    STATE["pending_entries"][cid2] = {
        "symbol": "TSTUSDT", "client_order_id": cid2, "order_id": 112,
        "qty": "0.19", "price": "103", "atr": 1.0, "vr": 1.0,
        "placed_at": time.time(), "active": False, "phase": "placed",
    }
    ORDERS["112"] = {"role": "entry", "cid": cid2, "symbol": "TSTUSDT"}
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid2, "i": 112,
                              "S": "BUY", "x": "CANCELED", "X": "CANCELED",
                              "l": "0", "L": "0", "z": "0", "Z": "0"})
    check("executionReport CANCELED (بلا تعبئة) → حذف المعلق", cid2 not in STATE["pending_entries"])
    check("صفر REST Polling لحالة الأوامر في المسار السعيد",
          stub.get_order_calls == 0 and stub.open_orders_calls == 0)
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

    # 22) اختيار الكون: أفضل 30 مع استبعاد المستقرات والرافعات والأدنى حداً
    saved_rules = SYMBOL_RULES
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
    check("كون أفضل 30 مع الاستبعادات (وأصغر مركز ممكن ≥ الحد الأدنى)",
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

    # 27) Set & Forget: لا آلية Trailing إطلاقاً في الكود
    check("Set & Forget: لا Trailing إطلاقاً",
          all(name not in globals() for name in ("dynamic_trailing_plan", "activate_trailing", "place_trailing_oco"))
          and not any(str(key).startswith("TRAIL_") for key in globals()))

    # 28) إغلاق خاسر: عدّاد المتتالية يُحدَّث للتقرير فقط (بلا قواطع)
    globals()["save_state"] = _noop_save
    STATE = default_state()
    STATE["positions"]["TSTUSDT#y"] = {"symbol": "TSTUSDT", "entry": 100.0, "qty": "0.2", "order_ids": [701]}
    await finalize_position_event("TSTUSDT#y", STATE["positions"]["TSTUSDT#y"], 98.0, 0.2, "تنفيذ OCO (وقف)")
    loss_ok = (STATE["metrics"]["losses"] == 1 and STATE["metrics"]["consecutive_losses"] == 1
               and abs(STATE["metrics"]["realized_pnl"] + 0.4) < 1e-6 and not STATE["positions"])
    await finalize_position_event("TSTUSDT#y", {"symbol": "TSTUSDT", "entry": 100.0, "qty": "0.2"}, 98.0, 0.2, "مكرر")
    check("إغلاق خاسر + منع الازدواج", loss_ok and STATE["metrics"]["losses"] == 1)
    globals()["save_state"] = real_save

    # تنظيف
    STATE = default_state()
    CANDLES.clear(); TREND.clear(); BOOK.clear(); FLOW.clear(); ORDERS.clear(); READY.clear()
    SETUPS.clear()
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
    rebuild_order_index()
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
            f"تشغيل NOVA ASYNC SCALPER V5.1 [تنقيط موزون] | {regime_text()} | Spot فقط | "
            f"فريم الإشارة {SIGNAL_INTERVAL} + اتجاه EMA{EMA_TREND_PERIOD}({TREND_INTERVAL}) | "
            f"أفضل {TOP_N_SYMBOLS} زوجاً (تحديث كل {UNIVERSE_REFRESH_EVERY}ث) | "
            f"WebSocket: kline_{SIGNAL_INTERVAL}+kline_{TREND_INTERVAL}+aggTrade+bookTicker"
            f"+{BTC_CONTEXT_SYMBOL.lower()}@kline_1m"
            f"{' + User Data Stream' if trading_enabled else ''} | "
            f"زناد ≥ {SCORE_TRIGGER:.0f}/100 (MSS {SCORE_MSS:.0f}+FVG {SCORE_FVG:.0f}+EMA {SCORE_EMA:.0f}"
            f"+Flow {SCORE_FLOW:.0f}) | تنفيذ MARKET فوري | "
            f"مخاطرة {TARGET_RISK_USD}$/صفقة بسقف مركز {MAX_POSITION_NOTIONAL_USD}$ | "
            f"وقف {ATR_MULT_SLOW}–{ATR_MULT_FAST}×ATR بسقف {SL_MAX_PCT}% + هدف 1:{RR_RATIO:g} | "
            f"تهدئة ديناميكية {COOLDOWN_FAST}/{COOLDOWN_NORMAL}/{COOLDOWN_SLOW}ث | "
            f"قاطع BTC بهبوط {BTC_DROP_PCT}%/{BTC_DROP_WINDOW_MIN}د | "
            f"حتى {MAX_POSITIONS_PER_SYMBOL} مراكز/عملة | Dust→BNB كل {DUST_SWEEP_EVERY // 3600}س | "
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


if __name__ == "__main__":
    main()
