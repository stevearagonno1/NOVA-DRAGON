#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA ASYNC SCALPER V4.0 — Institutional Event-Driven 5M HMSM Engine
====================================================================
بوت سكالبينج Spot غير متزامن بالكامل على Binance مبني على نموذج
Hybrid Microstructure Scalping Model (HMSM) — معمارية مدفوعة بالأحداث
(WebSocket Push) مع محرك رياضي متجهي (numpy + pandas) مصمم للجوال.

الفلسفة المعمارية (Async / Event-Driven / Battery-First):
1) تدفقات السوق عبر WebSocket دائم إلى Binance:
  Combined Streams (/stream) مع SUBSCRIBE/UNSUBSCRIBE ديناميكية لأفضل 30
   زوج USDT حسب حجم 24 ساعة (تحديث REST كل ساعة ثم تحديث الاشتراكات).
   الاشتراكات حصراً: <sym>@kline_5m + <sym>@kline_15m + <sym>@bookTicker
   (BBA = Best Bid/Ask لحساب اختلال التدفق لحظياً).
2) User Data Stream عبر WebSocket (executionReport): مصدر الحقيقة الوحيد
   لحالة الأوامر — يعرف البوت فوراً بتنفيذ LIMIT أو أرجل OCO دون أي
   REST Polling لحالة الأوامر إطلاقاً. البدائل RESTية واحدة فقط عند:
   الإقلاع، إعادة اتصال User Stream (أحداث مفقودة)، أو Watchdog صمت 12ث
   (أمر معلق بلا أحداث) — استرجاع أحادي لا اقتراع دوري.
3) المحرك الرياضي متجهي بالكامل: EMA200 وATR عبر pandas.ewm/np.maximum
   فقط — لا حلقات بايثون للمؤشرات ولا مكتبات رسم إطلاقاً.
4) حلقة الأحداث في سبات عميق (await): يستيقظ المنطق فقط عندما يدفع
   Binance شمعة مغلقة أو bookTicker أو executionReport. كل REST عبر
   aiohttp، وكل ملفات عبر asyncio.to_thread — لا حجب إطلاقاً.
5) HMSM على 5m:
   • الفلتر الكلي: إغلاق 5m الحالي أعلى بشكل صارم من EMA200(15m) وإلا
     تُتخطى العملة فوراً.
   • الزناد: MSS (كسر هيكل بإزاحة) + FVG (فجوة قيمة عادلة صاعدة غير
     معبأة) على 5m + اختلال تدفق المستوى الأول من bookTicker
     (حجم البائعين > حجم السائلين) في اللحظة نفسها → LIMIT BUY فوري.
   • إن اجتمعت MSS+FVG دون تأكيد دفتر، تبقى "طلقة معلقة" 60ث تنطلق
     فور أول bookTicker مؤكد.
6) Set & Forget صارم: عند تنفيذ الشراء يوضع OCO واحد ثابت فوراً —
   وقف 2.0×ATR(5m) وهدف 4.0×ATR(5m) (عائد/مخاطرة 1:2 رياضي خالص) —
   لا يُلمس أبداً بعد وضعه؛ لا Trailing Stop في أي صورة إطلاقاً.
7) الحجم: 20$ ثابتة لكل مركز (TRADE_NOTIONAL_D). Pyramiding: حتى 3
   مراكز متزامنة لكل عملة بت cooled-down صارم 300ث بين دخولين على
   العملة نفسها. لا قواطع خسائر متتالية إطلاقاً.
8) Dust Management: مسح تلقائي للأرصدة الدقيقة غير القابلة للبيع إلى
   BNB عبر نقطتي Binance الأصليتين (/sapi/v1/asset/dustableBases ثم
   /sapi/v1/asset/dust) مرة كل 24 ساعة — يسجَّل في السجل فقط.
9) الصمت التام (Stealth): رسالة بدء واحدة بالضبط بعد نجاح الإقلاع
   والاتصال بـ WebSockets: "✅ NOVA Async V4 Started & Connected to
   Binance WebSockets." ثم لا رسائل تلقائية إطلاقاً (لا دخول ولا إغلاق
   ولا Dust ولا أخطاء) — كل ذلك في bot.log فقط. الردود فقط على أوامر
   المستخدم اليدوية.
10) ترقيعات السباق والأمان (QA):
   • كل أحداث User Stream تُستهلك عبر طابور ومستهلك واحد (sequential
     consumer) → لا سباق بين executionReport متتالية.
   • إتمام الدخول "مطالبة ذرية" (claim) داخل STATE_LOCK: مهام متزامنة
     لا يمكنها وضع OCO مرتين لنفس الأمر أبداً (حتى لو سبق الحدثُ
     استجابةَ REST).
   • حجز الدخول ذري (ENTRY_LOCK): سقف 3 مراكز + تهدئة 300ث.
   • توقيع HMAC يُبنى من سلسلة استعلام واحدة تُرسل حرفياً في المسار —
     لا إعادة ترميز من aiohttp فتفسد التوقيع.
   • WebSocket: autoping + heartbeat (Ping/Pong تلقائي مع إغلاق فوري
     عند فقدان Pong) + Backoff متزايد مع Jitter + إعادة تحميل الشموع
     وSnapshot مصالحة بعد كل انقطاع.

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
    python NOVA_V4.py --selftest
    python NOVA_V4.py --dry-run
    python NOVA_V4.py
    python NOVA_V4.py --once

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

TELEGRAM_TOKEN = __REDACTED__"TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

AUTO_TRADE = env_bool("AUTO_TRADE", True)
DRY_RUN = env_bool("DRY_RUN", False)
# الصمت التام: لا رسائل تلقائية إطلاقاً بعد إشعار البدء الوحيد
STEALTH_MODE = True

STARTUP_TEXT = "✅ NOVA Async V4 Started & Connected to Binance WebSockets."
RESET_REPLY = "✅ تم تصفير جميع الإحصائيات بنجاح."

# ── الكون الديناميكي: أفضل 30 زوجاً حسب حجم 24 ساعة، تحديث كل ساعة ───────────
TOP_N_SYMBOLS = 30
UNIVERSE_REFRESH_EVERY = max(300, env_int("UNIVERSE_REFRESH_EVERY", 3600))
MIN_24H_QUOTE_VOLUME = env_float("MIN_24H_QUOTE_VOLUME", 1_000_000)

# ── المحرك: فريم الإشارة 5m + الفلتر الكلي EMA200 على فريم 15m ───────────────
SIGNAL_INTERVAL = "5m"
TREND_INTERVAL = "15m"
INTERVAL_SECONDS = {"5m": 300, "15m": 900}
EMA_TREND_PERIOD = max(10, env_int("EMA_TREND_PERIOD", 200))
MIN_CLOSED_CANDLES = max(30, env_int("MIN_CLOSED_CANDLES", 60))
KLINE_REST_LIMITS = {
    SIGNAL_INTERVAL: clamp(env_int("KLINE_LIMIT_5M", 140), 80, 500),
    TREND_INTERVAL: clamp(EMA_TREND_PERIOD + 60, 210, 1000),
}
HISTORY_MAX = {SIGNAL_INTERVAL: 300, TREND_INTERVAL: 400}

ATR_PERIOD = max(2, env_int("ATR_PERIOD", 14))

MSS_LOOKBACK = max(5, env_int("MSS_LOOKBACK", 20))
MSS_MAX_AGE = max(1, env_int("MSS_MAX_AGE", 2))
MSS_MIN_RANGE_ATR = env_float("MSS_MIN_RANGE_ATR", 0.80)
MSS_BODY_RATIO = clamp(env_float("MSS_BODY_RATIO", 0.50), 0.0, 1.0)

FVG_LOOKBACK = max(3, env_int("FVG_LOOKBACK", 8))
FVG_MIN_ATR = env_float("FVG_MIN_ATR", 0.05)

MAX_SPREAD_PCT = env_float("MAX_SPREAD_PCT", 0.15)
# اختلال تدفق المستوى الأول من bookTicker: حجم البائعين > حجم السائلين بصرامة
MIN_BOOK_IMBALANCE = clamp(env_float("MIN_BOOK_IMBALANCE", 0.50), 0.50, 1.0)
BOOK_TTL = env_float("BOOK_TTL", 10.0)
# نافذة "الطلقة المعلقة": MSS+FVG جاهزتان وينتظران أول bookTicker مؤكد
TRIGGER_WINDOW = env_float("TRIGGER_WINDOW", 60.0)

# ── التنفيذ: 20$ ثابتة + حتى 3 مراكز لكل عملة + تهدئة 300ث ──────────────────
TRADE_NOTIONAL_D = Decimal("20")        # ثابت بالمواصفات: عشرون دولاراً لكل مركز
MAX_POSITIONS_PER_SYMBOL = 3            # ثابت بالمواصفات: Pyramiding مستقل
SAME_SYMBOL_COOLDOWN = max(0, env_int("SAME_SYMBOL_COOLDOWN", 300))

# ── المخارج الثابتة (Set & Forget — لا Trailing إطلاقاً) ────────────────────
STOP_ATR_MULT = 2.0
TP_ATR_MULT = 4.0
FEE_BUFFER = env_float("FEE_BUFFER", 0.0015)
LIMIT_SLIPPAGE_PCT = env_float("LIMIT_SLIPPAGE_PCT", 0.20)
OCO_LEGACY_FALLBACK = env_bool("OCO_LEGACY_FALLBACK", True)

# Watchdog الصمت: إن لم يصل executionReport خلال 12ث يُستوضح الأمر REST مرة واحدة
ENTRY_EVENT_TIMEOUT = env_float("ENTRY_EVENT_TIMEOUT", 12.0)
USER_QUEUE_MAX = 2000

# ── Dust Management: مسح الأرصدة الدقيقة إلى BNB مرة كل 24 ساعة ─────────────
DUST_SWEEP_EVERY = max(3600, env_int("DUST_SWEEP_EVERY", 86_400))
DUST_ASSET_CAP = 8          # حد Binance لعدد الأصول في طلب واحد

# ── User Data Stream: مفتاح استماع + Keepalive كل 30 دقيقة ───────────────────
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
BOOK = {}             # symbol -> {"bid","ask","bid_vol","ask_vol","imbalance","ts"}
PENDING_TRIGGERS = {} # symbol -> {"until": monotonic, "sig": {...}}
ENTRY_RESERVATIONS = {}
RESERVED_QUOTE = Decimal("0")
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
        log(f"ذاكرة V4: {len(STATE['positions'])} مركزاً مفتوحاً | صفقات {STATE['metrics']['trades']}")
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
    يعيد aiohttp ترميز السلسلة فتفسد التوقيع — ترقيع الثغرة الكلاسيكي عند
    الانتقال من requests إلى aiohttp.
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
            "min_notional": D(notion.get("minNotional", "0")),
        }
    log(f"قواعد Binance USDT: {len(SYMBOL_RULES)} زوجاً")


def pick_universe(tickers):
    """أفضل 30 زوجاً حسب حجم 24س — دالة نقية (قابلة للاختبار)."""
    stable = {"USDT", "USDC", "FDUSD", "BUSD", "TUSD", "USDP", "DAI", "USD1"}
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
        # مركز 20$ لا يمكن حمايته تحت الحد الأدنى للطلب
        if D(rule.get("min_notional", "0")) > TRADE_NOTIONAL_D * Decimal("0.85"):
            continue
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
        log(f"كون V4: أفضل {len(SYMBOLS)} زوجاً حسب حجم 24س")
    return SYMBOLS


# ══════════════════════════════════════════════════════════════════════════════
# 5) ذاكرة الشموع ودفتر BBA (تحديث دفعي عبر WebSocket — لا REST Polling)
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
    """تسخين أولي: شموع 5m + 15m عبر REST ثم EMA200(15m) جاهزة."""
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
    """بعد أي انقطاع WebSocket: إعادة تحميل الشموع لسد الفجوات الزمنية."""
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


def update_trend_ema(symbol):
    """EMA200(15m) متجهياً عند كل شمعة 15m مغلقة (مع حراسة ازدواج)."""
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
    """يحول رسالة bookTicker إلى BBA + أحجام الطرفين + اختلال التدفق."""
    try:
        bid = float(data.get("b") or 0)
        bid_qty = float(data.get("B") or 0)
        ask = float(data.get("a") or 0)
        ask_qty = float(data.get("A") or 0)
        if bid <= 0 or ask <= 0:
            return None
        bid_vol = bid * bid_qty
        ask_vol = ask * ask_qty
        total = bid_vol + ask_vol
        return {
            "bid": bid, "ask": ask, "bid_qty": bid_qty, "ask_qty": ask_qty,
            "bid_vol": bid_vol, "ask_vol": ask_vol,
            "imbalance": (bid_vol / total) if total > 0 else 0.5,
            "ts": time.monotonic(),
        }
    except (TypeError, ValueError):
        return None


def on_kline(data):
    """معالج رسائل kline: تحديث الحية دائماً، وعند الإغلاق تشغيل المحرك.

    دالة متزامنة بالكامل (لا await) — لا تتقاطع مع غيرها داخل حلقة الأحداث
    الواحدة؛ الأعمال الشبكية تُفصل إلى مهام مستقلة.
    """
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
    """معالج bookTicker: تحديث BBA ثم فحص الطلقات المعلقة (إن وجدت)."""
    try:
        if SYMBOLS and symbol not in SYMBOLS_SET:
            return
        parsed = parse_book_payload(data)
        if parsed is not None:
            BOOK[symbol] = parsed
        pending = PENDING_TRIGGERS.get(symbol)
        if not pending:
            return
        if time.monotonic() > pending["until"]:
            PENDING_TRIGGERS.pop(symbol, None)
            return
        sig = pending["sig"]
        confirmed, ask, imbalance, _reason = book_confirms(symbol, sig["fvg_mid"])
        if confirmed:
            PENDING_TRIGGERS.pop(symbol, None)
            launch_entry(sig, ask, imbalance)
    except Exception as exc:
        log(f"خطأ معالجة bookTicker {symbol}: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# 6) محرك HMSM: الفلتر الكلي EMA200(15m) + MSS + FVG + Flow على 5m
# ══════════════════════════════════════════════════════════════════════════════


def build_signal(symbol):
    """الجزء المعتمد على الشموع: Macro(EMA200 15m) + MSS + FVG على 5m."""
    rule = SYMBOL_RULES.get(symbol)
    if not rule or rule.get("status") != "TRADING":
        return None
    buffer = CANDLES.get((symbol, SIGNAL_INTERVAL))
    if not buffer or len(buffer["c"]) < MIN_CLOSED_CANDLES:
        return None
    server_now_ms = time.time() * 1000 + TIME_OFFSET_MS
    if buffer["t"] and server_now_ms - buffer["t"][-1] > INTERVAL_SECONDS[SIGNAL_INTERVAL] * 3000:
        return None  # بيانات قديمة
    o, h, l, c = buffer_to_frame(buffer)
    v = buffer["v"]
    for i in range(max(0, c.size - 5), c.size):
        if not math.isfinite(float(o[i])) or not math.isfinite(float(h[i])) \
                or not math.isfinite(float(l[i])) or not math.isfinite(float(c[i])) \
                or not math.isfinite(float(v[i])):
            return None
        if h[i] < max(o[i], c[i]) or l[i] > min(o[i], c[i]):
            return None
    atr_value = atr_last(h, l, c, ATR_PERIOD)
    if atr_value <= 0:
        return None
    mss = detect_mss(o, h, l, c, atr_value)
    if not mss:
        return None
    fvg = detect_fvg(h, l, atr_value)
    if not fvg:
        return None
    # الفلتر الكلي الصارم: إغلاق 5m الحالي أعلى بشكل صارم من EMA200(15m)
    price_now = float(buffer.get("live") or buffer["c"][-1])
    trend = TREND.get(symbol) or {}
    ema_value = trend.get("ema")
    if ema_value is None or not (price_now > float(ema_value)):
        return None
    return {
        "symbol": symbol, "atr": atr_value,
        "atr_pct": (atr_value / price_now * 100.0) if price_now else 0.0,
        "close": float(c[-1]), "live": price_now,
        "fvg_mid": fvg["mid"], "fvg_low": fvg["low"], "fvg_high": fvg["high"],
        "mss_prior_high": mss["prior_high"], "displacement": mss["displacement"],
        "created_at": time.time(),
    }


def book_confirms(symbol, fvg_mid):
    """فحص BBA اللحظي من bookTicker: سبريد + تدفق + صمود الفجوة."""
    book = BOOK.get(symbol)
    if not book or time.monotonic() - book["ts"] > BOOK_TTL:
        return False, 0.0, 0.0, "no-book"
    bid, ask, imbalance = book["bid"], book["ask"], book["imbalance"]
    mid = (bid + ask) / 2.0
    if mid <= 0 or ask <= 0:
        return False, ask, imbalance, "bad-book"
    if (ask - bid) / mid * 100.0 > MAX_SPREAD_PCT:
        return False, ask, imbalance, "spread"
    # اختلال التدفق من bookTicker: حجم البائعين > حجم السائلين بصرامة
    if not (imbalance > MIN_BOOK_IMBALANCE):
        return False, ask, imbalance, "flow"
    if ask <= fvg_mid:
        return False, ask, imbalance, "fvg-break"
    return True, ask, imbalance, "ok"


def on_signal_candle_closed(symbol):
    """شمعة 5m أُغلقت للتو: قيّم الإشارة كاملة أو علّقها بانتظار الدفتر."""
    signal = build_signal(symbol)
    if not signal:
        PENDING_TRIGGERS.pop(symbol, None)
        return
    confirmed, ask, imbalance, _reason = book_confirms(symbol, signal["fvg_mid"])
    if confirmed:
        PENDING_TRIGGERS.pop(symbol, None)
        launch_entry(signal, ask, imbalance)
    else:
        # MSS+FVG+EMA جاهزة؛ الانتظار حتى أول bookTicker مؤكد خلال النافذة
        PENDING_TRIGGERS[symbol] = {"until": time.monotonic() + TRIGGER_WINDOW, "sig": signal}


def launch_entry(sig, ask, imbalance):
    """يشعل التنفيذ: بوابات سريعة متزامنة ثم مهمة دخول مستقلة (لا يحجب WS)."""
    symbol = sig["symbol"]
    if kill_switch_active() or STATE.get("paused"):
        return
    if count_symbol_positions(symbol) >= MAX_POSITIONS_PER_SYMBOL:
        return
    if time.time() - float(STATE.get("last_entry_at", {}).get(symbol, 0.0)) < SAME_SYMBOL_COOLDOWN:
        return
    signal = dict(sig)
    signal["price"] = float(ask)
    signal["imbalance"] = float(imbalance)
    signal["stop"] = signal["price"] - STOP_ATR_MULT * sig["atr"]
    signal["target"] = signal["price"] + TP_ATR_MULT * sig["atr"]
    try:
        asyncio.get_running_loop().create_task(process_signal(signal))
    except RuntimeError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 7) التنفيذ: LIMIT فوري + OCO ثابت عبر User Data Stream (Set & Forget)
# ══════════════════════════════════════════════════════════════════════════════


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


async def reserve_entry(symbol):
    """حجز ذري (ENTRY_LOCK): سقف 3 مراكز + تهدئة 300ث — ترقيع سباق الدخول."""
    global RESERVED_QUOTE
    async with ENTRY_LOCK:
        if kill_switch_active() or STATE.get("paused"):
            return False
        current = count_symbol_positions(symbol)
        reserved = ENTRY_RESERVATIONS.get(symbol, 0)
        if current + reserved >= MAX_POSITIONS_PER_SYMBOL:
            return False
        if time.time() - float(STATE.get("last_entry_at", {}).get(symbol, 0.0)) < SAME_SYMBOL_COOLDOWN:
            return False
        ENTRY_RESERVATIONS[symbol] = reserved + 1
        RESERVED_QUOTE += TRADE_NOTIONAL_D
        return True


async def release_entry(symbol):
    global RESERVED_QUOTE
    async with ENTRY_LOCK:
        reserved = ENTRY_RESERVATIONS.get(symbol, 0)
        if reserved <= 1:
            ENTRY_RESERVATIONS.pop(symbol, None)
        else:
            ENTRY_RESERVATIONS[symbol] = reserved - 1
        RESERVED_QUOTE = max(Decimal("0"), RESERVED_QUOTE - TRADE_NOTIONAL_D)


async def process_signal(signal):
    symbol = signal["symbol"]
    if not await reserve_entry(symbol):
        return False
    try:
        async with ENTRY_SEMAPHORE:
            return await execute_entry(signal)
    finally:
        await release_entry(symbol)


def oco_levels(entry, atr_value):
    """مستويات ثابتة رياضية: وقف 2×ATR وهدف 4×ATR (1:2 خالص)."""
    atr_d = D(str(atr_value))
    stop = D(entry) - D(str(STOP_ATR_MULT)) * atr_d
    target = D(entry) + D(str(TP_ATR_MULT)) * atr_d
    return stop, target


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


async def emergency_sell(symbol, qty, reason):
    try:
        rule = SYMBOL_RULES[symbol]
        step = rule.get("market_step", rule["step"])
        min_qty = rule.get("market_min_qty", rule["min_qty"])
        quantity = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), step)
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


async def place_initial_oco(symbol, qty, entry, stop_price, target_price):
    """OCO أولي ثابت: وقف وهدف مشتقان من ATR(5m)، مع fallback للواجهة القديمة."""
    rule = SYMBOL_RULES[symbol]
    quantity = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), rule["step"])
    stop = round_price(stop_price, rule["tick"], "down")
    target_trigger = round_price(target_price, rule["tick"], "up")
    if stop >= D(entry):
        stop = round_price(D(entry) - rule["tick"] * 2, rule["tick"], "down")
    if target_trigger <= D(entry):
        target_trigger = round_price(D(entry) + rule["tick"] * 2, rule["tick"], "up")
    stop_limit = round_price(stop * (Decimal("1") - D(LIMIT_SLIPPAGE_PCT) / Decimal("100")), rule["tick"], "down")
    target_limit = round_price(target_trigger * (Decimal("1") - D("0.0003")), rule["tick"], "down")
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
    """LIMIT BUY فوري على Ask — الحسم عبر executionReport حصراً (بلا Polling).

    أمر الدخول يُسجَّل في pending_entries قبل إرساله؛ الوصول للحالة النهائية
    عبر User Data Stream، مع Watchdog صمت أحادي (12ث) كشبكة أمان قصوى.
    """
    symbol = signal["symbol"]
    if kill_switch_active() or STATE.get("paused"):
        return False
    rule = SYMBOL_RULES.get(symbol)
    if not rule or rule.get("status") != "TRADING":
        return False
    if not live_execution_allowed():
        if DRY_RUN:
            log(f"إشارة مؤكدة بدون تنفيذ (DRY-RUN): {symbol} @ {fmt_price(symbol, signal['price'])} | "
                f"ATR(5m) {signal['atr']:.8g} | وقف {fmt_price(symbol, signal['stop'])} هدف {fmt_price(symbol, signal['target'])}")
        else:
            log(f"إشارة مؤكدة بدون تنفيذ (التنفيذ غير مفعّل): {symbol}")
        await mark_cooldown(symbol)
        return False
    entry_client_id = make_client_id("nv4")
    try:
        account = await REST.account()
        free_quote = free_balance_from(account, rule.get("quote", "USDT"))
        async with ENTRY_LOCK:
            other_reserved = max(Decimal("0"), RESERVED_QUOTE - TRADE_NOTIONAL_D * ENTRY_RESERVATIONS.get(symbol, 0))
        if free_quote < TRADE_NOTIONAL_D + other_reserved:
            log(f"رصيد USDT غير كافٍ لـ {symbol}")
            return False
        price = round_price(signal["price"], rule["tick"])
        if price <= 0:
            return False
        qty = round_step(TRADE_NOTIONAL_D / price, rule["step"])
        if qty < rule["min_qty"] or qty * price < rule["min_notional"]:
            log(f"فلاتر الكمية تمنع دخول {symbol}")
            return False
        async with STATE_LOCK:
            STATE["pending_entries"][entry_client_id] = {
                "symbol": symbol, "client_order_id": entry_client_id, "order_id": None,
                "qty": dec_str(qty), "price": dec_str(price), "atr": float(signal["atr"]),
                "placed_at": time.time(), "active": True, "phase": "placing",
            }
        await save_state()
        order = await REST.new_order({
            "symbol": symbol, "side": "BUY", "type": "LIMIT", "timeInForce": "GTC",
            "quantity": dec_str(qty), "price": dec_str(price),
            "newClientOrderId": entry_client_id, "newOrderRespType": "FULL",
        })
        order_id = order.get("orderId") if isinstance(order, dict) else None
        if not order_id:
            # استجابة بلا orderId: الأمر قد يكون مقبولاً — الواتش دوغ/الأحداث تحسم
            try:
                order = await REST.get_order_client(symbol, entry_client_id)
                order_id = order.get("orderId")
            except BinanceError:
                order_id = None
        async with STATE_LOCK:
            record = STATE["pending_entries"].get(entry_client_id)
            if record is not None and order_id is not None:
                record["order_id"] = order_id
                record["phase"] = "placed"
                ORDERS[str(order_id)] = {"role": "entry", "cid": entry_client_id, "symbol": symbol}
        if order_id is None and (not isinstance(order, dict) or order.get("status") not in ("FILLED",)):
            # حالة غير معروفة تماماً: يبقى المعلق للواتش دوغ
            log(f"حالة أمر الدخول غير مؤكدة لـ {symbol}; الواتش دوغ سيحسمه")
        arm_entry_watchdog(entry_client_id)
        await save_state()
        log(f"أمر دخول LIMIT {symbol} @ {fmt_price(symbol, price)} (cid={entry_client_id}) — بانتظار executionReport")
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
            record = STATE["pending_entries"].get(entry_client_id)
            if record is not None:
                record["active"] = False


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
    """إتمام دخول مُعبأ: مطالبة ذرية (claim) ثم مركز + OCO ثابت فوراً.

    تُستدعى من مستهلك أحداث المستخدم أو من الواتش دوغ — المطالبة تحت
    STATE_LOCK تضمن تنفيذها مرة واحدة بالضبط مهما تسابقت المصادر.
    """
    symbol = record.get("symbol", "")
    async with STATE_LOCK:
        current = STATE["pending_entries"].get(client_id)
        if current is None or current.get("phase") in ("done", "filled"):
            return  # حُسم مسبقاً — منع التسجيل المزدوج
        current["phase"] = "done"
        snapshot = dict(current)
        STATE["pending_entries"].pop(client_id, None)
    try:
        if D(executed_qty) <= 0:
            await save_state()
            return
        if sellable_qty(symbol, executed_qty, float(avg_price) * 0.95) is None:
            await add_dust(symbol, executed_qty, quote_filled, "تعبئة جزئية دون الحد الأدنى للبيع")
            return
        stop_price, target_price = oco_levels(avg_price, record.get("atr", 0.0))
        protection = await place_initial_oco(symbol, executed_qty, avg_price, stop_price, target_price)
        pid = new_position_id(symbol)
        position = {
            "pid": pid, "symbol": symbol, "entry_client_id": client_id,
            "entry": float(avg_price), "qty": dec_str(protection["qty"]),
            "quote_qty": float(quote_filled or 0),
            "stop": float(protection["stop"]), "target": float(protection["target"]),
            "atr_5m": float(D(str(record.get("atr", 0.0)))),
            "order_list_id": protection.get("order_list_id"),
            "order_ids": [x.get("orderId") for x in protection.get("orders", []) if x.get("orderId") is not None],
            "protection_type": protection.get("type"),
            "opened_at": time.time(), "imbalance": float(record.get("imbalance", 0.5)),
        }
        async with STATE_LOCK:
            STATE["positions"][pid] = position
            STATE["metrics"]["trades"] += 1
            STATE["cooldowns"][symbol] = time.time()
            STATE.setdefault("last_entry_at", {})[symbol] = time.time()
            for leg_id in position["order_ids"]:
                ORDERS[str(leg_id)] = {"role": "leg", "pid": pid, "symbol": symbol}
        await save_state()
        log(f"دخول HMSM(5m) {symbol} pid={pid} entry={fmt_price(symbol, avg_price)} qty={position['qty']} "
            f"stop={fmt_price(symbol, protection['stop'])} target={fmt_price(symbol, protection['target'])} "
            f"protection={protection['type']} (Set & Forget)")
    except BinanceError as exc:
        log(f"فشل OCO الدخول {symbol}: {exc}؛ بيع إنقاذ")
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
    last_qty = D(ev.get("l") or "0")
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
        order = await emergency_sell(position.get("symbol", ""), D(position.get("qty", 0)), "PANIC")
        if order:
            qty, quote, avg = parse_fill(order, 0)
            await finalize_position_event(pid, position, avg, qty, "PANIC")


# ══════════════════════════════════════════════════════════════════════════════
# 8) Dust Management — مسح الأرصدة الدقيقة إلى BNB كل 24 ساعة
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
# 9) التقارير: صيغة /status الحرفية (بدون قائمة عملات نشطة)
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


HELP_TEXT = (
    "🤖 <b>NOVA ASYNC SCALPER V4.0 — Event-Driven 5M (Stealth + Set &amp; Forget)</b>\n\n"
    "/start أو /menu القائمة الرئيسية\n/status تقرير الأداء\n/reset تصفير الإحصائيات\n"
    "/pause إيقاف الدخولات الجديدة\n/resume استئناف\n"
    "/cancelall إلغاء حمايات البوت\n/panic إلغاء + تصفية فورية\n"
    "/kill قاطع تداول يدوي\n/unkill إزالة القاطع\n/help هذه المساعدة\n\n"
    "محرك غير متزامن مدفوع بأحداث WebSocket: kline_5m + kline_15m + bookTicker لأفضل 30 زوجاً.\n"
    "User Data Stream (executionReport) هو مصدر حقيقة الأوامر — بلا REST Polling.\n"
    "الفلتر الكلي: إغلاق 5m أعلى بشكل صارم من EMA200(15m) وإلا تُتخطى العملة.\n"
    "الزناد: MSS + FVG (5m) + اختلال تدفق BBA في اللحظة نفسها → LIMIT BUY بحجم 20$.\n"
    "حتى 3 مراكز لكل عملة بتهدئة صارمة 300ث بينها.\n"
    "وقف 2×ATR(5m) وهدف 4×ATR(5m) (1:2) — OCO ثابت لا يُلمس بعد وضعه.\n"
    "Dust يُمسح تلقائياً إلى BNB كل 24 ساعة.\n"
    "لا Trailing ولا قواطع خسائر متتالية.\n"
    "الصمت التام: رسالة بدء واحدة عند الإقلاع ثم لا رسائل تلقائية إطلاقاً."
)


# ══════════════════════════════════════════════════════════════════════════════
# 10) Telegram (aiohttp — Long Polling بلا حجب)
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
    return [
        [button("📊 الحالة", "status")],
        [button("⏸ إيقاف", "pause"), button("▶ استئناف", "resume")],
        [button("🧯 إلغاء الأوامر", "cancelall"), button("🆘 تصفية", "panic")],
        [button("❓ المساعدة", "help")],
    ]


async def handle_callback(update):
    callback = update.get("callback_query", {})
    message = callback.get("message", {})
    chat = str(message.get("chat", {}).get("id", ""))
    if chat != str(TELEGRAM_CHAT_ID):
        await tg_api("answerCallbackQuery", {"callback_query_id": callback.get("id", ""), "text": "غير مصرح"}, retries=1)
        return
    data = callback.get("data", "")
    await tg_api("answerCallbackQuery", {"callback_query_id": callback.get("id", "")}, retries=1)
    if data == "status":
        await send_message(status_text(), main_keyboard(), chat)
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
    elif data == "help":
        await send_message(HELP_TEXT, main_keyboard(), chat)


async def handle_command(text, chat):
    command, _, argument = text.partition(" ")
    command = command.split("@", 1)[0].lower()
    if command in ("/start", "/menu"):
        await send_message("🎛️ <b>NOVA ASYNC SCALPER V4.0</b>\nاختر عملية:", main_keyboard(), chat)
    elif command == "/help":
        await send_message(HELP_TEXT, main_keyboard(), chat)
    elif command == "/status":
        await send_message(status_text(), main_keyboard(), chat)
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
# 11) محطات WebSocket: السوق + User Data Stream (إعادة اتصال تلقائية)
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
        return (f"{s}@kline_{SIGNAL_INTERVAL}", f"{s}@kline_{TREND_INTERVAL}", f"{s}@bookTicker")

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
        if "@kline" in stream:
            on_kline(data)
        elif "@bookTicker" in stream:
            on_book(stream.split("@", 1)[0].upper(), data)

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
                    PENDING_TRIGGERS.pop(symbol, None)
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
            stale = {cid: rec for cid, rec in STATE.get("pending_entries", {}).items()
                     if time.time() - float(rec.get("placed_at", 0)) > 120}
            if stale:
                await reconcile_snapshot("معلقات قديمة")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ حلقة الصيانة: {exc}")


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
    """وضع --once: تقييم فوري للكون عبر البيانات المسخنة + BBA من REST."""
    fired = 0
    for symbol in SYMBOLS:
        signal = build_signal(symbol)
        if not signal:
            continue
        try:
            book = await REST.book_ticker(symbol)
            parsed = parse_book_payload({
                "b": book.get("bidPrice"), "B": book.get("bidQty"),
                "a": book.get("askPrice"), "A": book.get("askQty"),
            })
            if parsed is None:
                continue
            BOOK[symbol] = parsed
            confirmed, ask, imb, reason = book_confirms(symbol, signal["fvg_mid"])
            if confirmed:
                await process_signal({**signal, "price": ask, "imbalance": imb,
                                      "stop": ask - STOP_ATR_MULT * signal["atr"],
                                      "target": ask + TP_ATR_MULT * signal["atr"]})
                fired += 1
            else:
                log(f"تخطي {symbol}: {reason}")
        except BinanceError as exc:
            log(f"فحص {symbol}: {exc}")
    log(f"الفحص الفوري: {fired} إشارة منفذة")


# ══════════════════════════════════════════════════════════════════════════════
# 12) الاختبار الذاتي (بلا شبكة إطلاقاً)
# ══════════════════════════════════════════════════════════════════════════════


def _synthetic_rows(interval="5m"):
    """صفوف klines تركيبية: شمعة إزاحة تكسر قمة وتصنع FVG غير معبأة.

    آخر صف = الشمعة الحية (يحذفها build_buffer من المغلقات).
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
    return out


async def run_selftest():
    global STATE, STARTUP_NOTIFIED, ENTRY_RESERVATIONS, RESERVED_QUOTE, BINANCE_ENV
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN, REST, SYMBOL_RULES, BINANCE_API_KEY, BINANCE_API_SECRET
    print("NOVA ASYNC SCALPER V4.0 SELFTEST")
    results = []

    def check(name, condition):
        results.append(bool(condition))
        print(("✅ " if condition else "❌ ") + name)

    ensure_dirs()

    # 1) EMA متجهي (pandas) يطابق المرجع الكلاسيكي حرفياً
    closes = [100.0 + (i % 13) * 0.5 for i in range(260)]
    ours = ema_series(closes, EMA_TREND_PERIOD)
    ref = _reference_ema(closes, EMA_TREND_PERIOD)
    max_err = max(abs(float(ours[i]) - ref[i]) for i in range(len(closes)) if ref[i] is not None)
    check("EMA(pandas) يطابق المرجع الكلاسيكي (بذرة SMA)",
          math.isnan(float(ours[EMA_TREND_PERIOD - 2])) and max_err < 1e-9)
    check("EMA_last", abs(ema_last(closes, EMA_TREND_PERIOD) - ref[-1]) < 1e-9)

    # 2) ATR متجهي (numpy+pandas) يطابق مرجع Wilder
    highs = [100.0 + (i % 7) for i in range(120)]
    lows = [99.0 + (i % 5) for i in range(120)]
    atr_ours = atr_series(highs, lows, closes[:120], ATR_PERIOD)
    atr_ref = _reference_wilder_atr(highs, lows, closes[:120], ATR_PERIOD)
    atr_err = max(abs(float(atr_ours[i]) - atr_ref[i]) for i in range(len(atr_ref)) if atr_ref[i] is not None)
    check("ATR(numpy+pandas) يطابق مرجع Wilder", atr_err < 1e-9)
    n = 200
    check("ATR نطاق ثابت", abs(atr_last([101.0] * n, [99.0] * n, [100.0] * n, ATR_PERIOD) - 2.0) < 1e-9)

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

    # 4) MSS وFVG على 5m (متجهي)
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

    # 5) الفلتر الكلي: إغلاق 5m أعلى بشكل صارم من EMA200(15m)
    SYMBOL_RULES["TSTUSDT"] = {
        "status": "TRADING", "base": "TST", "quote": "USDT",
        "tick": D("0.01"), "step": D("0.001"), "min_qty": D("0"), "max_qty": D("999999"),
        "market_step": D("0.001"), "market_min_qty": D("0"), "min_notional": D("5"),
    }
    CANDLES[("TSTUSDT", SIGNAL_INTERVAL)] = build_buffer(_synthetic_rows(), "5m")
    TREND["TSTUSDT"] = {"ema": 99.0, "last_t": None}
    signal_ok = build_signal("TSTUSDT")
    TREND["TSTUSDT"] = {"ema": 200.0, "last_t": None}
    signal_rejected = build_signal("TSTUSDT")
    TREND["TSTUSDT"] = {"ema": None, "last_t": None}
    signal_cold = build_signal("TSTUSDT")
    check("الفلتر الكلي EMA200(15m) صارم",
          signal_ok is not None and signal_rejected is None and signal_cold is None)
    TREND["TSTUSDT"] = {"ema": 99.0, "last_t": None}

    # 6) BBA من bookTicker: اختلال التدفق + الاتجاه + السبريد + كسر الفجوة
    bid_heavy = parse_book_payload({"b": "102.9", "B": "3", "a": "103.0", "A": "1"})
    ask_heavy = parse_book_payload({"b": "103.0", "B": "1", "a": "103.1", "A": "3"})
    check("parse bookTicker (BBA)", bid_heavy is not None and bid_heavy["imbalance"] > 0.5
          and ask_heavy is not None and ask_heavy["imbalance"] < 0.5)
    BOOK["TSTUSDT"] = bid_heavy
    ok_live, ask, imb, _r = book_confirms("TSTUSDT", signal_ok["fvg_mid"])
    BOOK["TSTUSDT"] = ask_heavy
    ok_flow_fail, _a2, _i2, reason_flow = book_confirms("TSTUSDT", signal_ok["fvg_mid"])
    wide = dict(bid_heavy)
    wide.update({"bid": 90.0, "ask": 91.5, "ts": time.monotonic()})
    BOOK["TSTUSDT"] = wide
    ok_spread_fail, _a3, _i3, reason_spread = book_confirms("TSTUSDT", signal_ok["fvg_mid"])
    below = dict(bid_heavy)
    below.update({"bid": 100.5, "ask": 100.6, "ts": time.monotonic()})
    BOOK["TSTUSDT"] = below
    ok_break, _a4, _i4, reason_break = book_confirms("TSTUSDT", signal_ok["fvg_mid"])
    BOOK.pop("TSTUSDT", None)
    check("تأكيد BBA (تدفق/سبريد/صمود الفجوة)",
          ok_live and ask == 103.0 and (not ok_flow_fail) and reason_flow == "flow"
          and (not ok_spread_fail) and reason_spread == "spread"
          and (not ok_break) and reason_break == "fvg-break")

    # 7) توقيع HMAC مع aiohttp (سلسلة حرفية واحدة بلا إعادة ترميز)
    globals()["BINANCE_API_KEY"] = "TEST_KEY"
    globals()["BINANCE_API_SECRET"] = "TEST_SECRET"
    values = {"symbol": "BTCUSDT", "quantity": "0.001", "recvWindow": 5000, "timestamp": 1700000000000}
    query, headers = build_signed(values)
    expected_query = "symbol=BTCUSDT&quantity=0.001&recvWindow=5000&timestamp=1700000000000"
    expected_sig = hmac.new(b"TEST_SECRET", expected_query.encode(), hashlib.sha256).hexdigest()
    globals()["BINANCE_API_KEY"], globals()["BINANCE_API_SECRET"] = "", ""
    check("توقيع HMAC-SHA256 مطابق حرفياً",
          query == f"{expected_query}&signature={expected_sig}" and headers["X-MBX-APIKEY"] == "TEST_KEY")

    # 8) مستويات OCO: 2×ATR وقفاً و4×ATR هدفاً (1:2 رياضي خالص)
    stop, target = oco_levels(Decimal("100"), 1.0)
    check("OCO ثابت 2×/4× ATR (1:2 R:R)",
          stop == Decimal("98") and target == Decimal("104")
          and abs(float((target - Decimal("100")) / (Decimal("100") - stop)) - 2.0) < 1e-9
          and TRADE_NOTIONAL_D == Decimal("20"))

    # 9) ترقيع السباق: حجز ذري — 5 محاولات متزامنة → 3 فقط
    ENTRY_RESERVATIONS = {}
    RESERVED_QUOTE = Decimal("0")
    STATE = default_state()
    outcomes = await asyncio.gather(*[reserve_entry("TSTUSDT") for _ in range(5)])
    for _ in range(3):
        await release_entry("TSTUSDT")
    check("Pyramiding: 3 مراكز كحد أقصى (بلا سباق)", sum(1 for x in outcomes if x) == 3)

    # 10) تهدئة 300ث الصارمة بين دخولين على العملة نفسها
    ENTRY_RESERVATIONS = {}
    cool_a = await reserve_entry("TSTUSDT")
    await release_entry("TSTUSDT")
    STATE["last_entry_at"]["TSTUSDT"] = time.time()
    cool_b = not await reserve_entry("TSTUSDT")
    STATE["last_entry_at"]["TSTUSDT"] = time.time() - (SAME_SYMBOL_COOLDOWN + 1.0)
    cool_c = await reserve_entry("TSTUSDT")
    await release_entry("TSTUSDT")
    check(f"تهدئة {SAME_SYMBOL_COOLDOWN}ث بين دخولين لنفس العملة", cool_a and cool_b and cool_c)

    # 11) مسار التنفيذ الكامل عبر User Data Stream (بلا أي REST Polling)
    class _StubRest:
        def __init__(self):
            self.oco_calls = []
            self.get_order_calls = 0
            self.open_orders_calls = 0
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

    STATE = default_state()
    ORDERS.clear()
    cid = make_client_id("nv4")
    STATE["pending_entries"][cid] = {
        "symbol": "TSTUSDT", "client_order_id": cid, "order_id": 111,
        "qty": "0.19", "price": "103", "atr": 1.0,
        "placed_at": time.time() - 1, "active": False, "phase": "placed",
    }
    ORDERS["111"] = {"role": "entry", "cid": cid, "symbol": "TSTUSDT"}
    # حدث TRADE جزئي ثم FILLED — المستهلك يحسم ويضع OCO فوراً
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid, "i": 111,
                              "S": "BUY", "x": "TRADE", "X": "PARTIALLY_FILLED",
                              "l": "0.1", "L": "103", "z": "0.1", "Z": "10.3"})
    partial_ok = STATE["pending_entries"][cid]["executed_qty"] == "0.1"
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid, "i": 111,
                              "S": "BUY", "x": "TRADE", "X": "FILLED",
                              "l": "0.09", "L": "103", "z": "0.19", "Z": "19.57"})
    pid = next(iter(STATE["positions"]))
    position = STATE["positions"][pid]
    entry_ok = (STATE["metrics"]["trades"] == 1 and cid not in STATE["pending_entries"]
                and len(stub.oco_calls) == 1 and position["order_list_id"] == 700
                and position["stop"] == 101.0 and position["target"] == 107.0)
    check("executionReport FILLED → مركز + OCO ثابت فوراً", partial_ok and entry_ok)
    # حدث مكرر (سباق) → لا OCO ثانٍ ولا مركز مزدوج
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid, "i": 111,
                              "S": "BUY", "x": "TRADE", "X": "FILLED",
                              "l": "0.19", "L": "103", "z": "0.19", "Z": "19.57"})
    check("ترقيع السباق: الحدث المكرر لا يكرر OCO/المركز",
          len(stub.oco_calls) == 1 and len(STATE["positions"]) == 1)
    # رجل الهدف ينفذ (فوق الدخول) → مكسب + عدّاد متتالية يُصفَّر
    STATE["metrics"]["consecutive_losses"] = 2
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": "ocoA", "i": 701,
                              "S": "SELL", "x": "TRADE", "X": "FILLED",
                              "l": "0.19", "L": "107", "z": "0.19", "Z": "20.33"})
    exit_ok = (not STATE["positions"] and STATE["metrics"]["wins"] == 1
               and STATE["metrics"]["consecutive_losses"] == 0
               and STATE["metrics"]["realized_pnl"] > 0)
    check("executionReport رجل OCO → إغلاق فوري (بلا REST) + عدّاد متتالية", exit_ok)
    # إلغاء بلا تعبئة → حذف المعلق بهدوء
    cid2 = make_client_id("nv4")
    STATE["pending_entries"][cid2] = {
        "symbol": "TSTUSDT", "client_order_id": cid2, "order_id": 112,
        "qty": "0.19", "price": "103", "atr": 1.0,
        "placed_at": time.time(), "active": False, "phase": "placed",
    }
    ORDERS["112"] = {"role": "entry", "cid": cid2, "symbol": "TSTUSDT"}
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid2, "i": 112,
                              "S": "BUY", "x": "CANCELED", "X": "CANCELED",
                              "l": "0", "L": "0", "z": "0", "Z": "0"})
    check("executionReport CANCELED (بلا تعبئة) → حذف المعلق", cid2 not in STATE["pending_entries"])
    check("صفر REST Polling لحالة الأوامر في المسار السعيد",
          stub.get_order_calls == 0 and stub.open_orders_calls == 0)
    globals()["REST"] = real_rest
    globals()["save_state"] = real_save

    # 12) توجيه رسائل WebSocket السوق المغلَّفة (kline + bookTicker) + طلقة معلقة
    SYMBOLS.clear(); SYMBOLS.extend(["TSTUSDT"]); SYMBOLS_SET.clear(); SYMBOLS_SET.add("TSTUSDT")
    hub = MarketStreamHub()
    fired = []
    real_launch = launch_entry
    globals()["launch_entry"] = lambda sig, ask, imb: fired.append((sig["symbol"], ask))
    CANDLES[("TSTUSDT", SIGNAL_INTERVAL)] = build_buffer(_synthetic_rows(), "5m")
    TREND["TSTUSDT"] = {"ema": 99.0, "last_t": None}
    t_next = CANDLES[("TSTUSDT", SIGNAL_INTERVAL)]["t"][-1] + 300_000
    hub.dispatch(json.dumps({"stream": "tstusdt@kline_5m", "data": {
        "e": "kline", "E": int(time.time() * 1000), "s": "TSTUSDT",
        "k": {"i": "5m", "x": False, "t": t_next, "o": "109.5", "h": "110.4", "l": "109.0", "c": "109.9", "v": "800"}}}))
    live_updated = CANDLES[("TSTUSDT", SIGNAL_INTERVAL)]["live"] == 109.9
    hub.dispatch(json.dumps({"stream": "tstusdt@kline_5m", "data": {
        "e": "kline", "E": int(time.time() * 1000), "s": "TSTUSDT",
        "k": {"i": "5m", "x": True, "t": t_next, "o": "109.5", "h": "110.4", "l": "109.0", "c": "109.8", "v": "800"}}}))
    appended = len(CANDLES[("TSTUSDT", SIGNAL_INTERVAL)]["c"]) == 100
    hub.dispatch(json.dumps({"stream": "tstusdt@bookTicker", "data": {"b": "102.9", "B": "5", "a": "103.0", "A": "1"}}))
    book_set = BOOK.get("TSTUSDT", {}).get("ask") == 103.0
    pending_fired = bool(fired) and fired[-1] == ("TSTUSDT", 103.0)
    PENDING_TRIGGERS["TSTUSDT"] = {"until": time.monotonic() - 1, "sig": signal_ok}
    hub.dispatch(json.dumps({"stream": "tstusdt@bookTicker", "data": {"b": "102.9", "B": "5", "a": "103.0", "A": "1"}}))
    expired_ok = "TSTUSDT" not in PENDING_TRIGGERS
    globals()["launch_entry"] = real_launch
    check("توجيه WebSocket + طلقة معلقة تنطلق من bookTicker",
          live_updated and appended and book_set and pending_fired and expired_ok)

    # 13) EMA(15m) تتحدث عند إغلاق الشمعة (بلا ازدواج)
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
    check("EMA200(15m) عند إغلاق الشمعة بلا ازدواج", ema_first is not None and ema_unchanged and ema_moved)

    # 14) اختيار الكون: أفضل 30 فقط مع استبعاد المستقرات والرافعات
    saved_rules = SYMBOL_RULES
    SYMBOL_RULES = {}
    for i in range(40):
        base = f"C{i}"
        SYMBOL_RULES[f"{base}USDT"] = {"status": "TRADING", "base": base, "quote": "USDT", "min_notional": D("5")}
    SYMBOL_RULES["USDCUSDT"] = {"status": "TRADING", "base": "USDC", "quote": "USDT", "min_notional": D("5")}
    SYMBOL_RULES["BTCUPUSDT"] = {"status": "TRADING", "base": "BTCUP", "quote": "USDT", "min_notional": D("5")}
    SYMBOL_RULES["HEAVYUSDT"] = {"status": "TRADING", "base": "HEAVY", "quote": "USDT", "min_notional": D("50")}
    tickers = {f"C{i}USDT": {"quote_volume": 50_000_000 - i * 1_000_000} for i in range(40)}
    tickers["USDCUSDT"] = {"quote_volume": 9e9}
    tickers["BTCUPUSDT"] = {"quote_volume": 9e9}
    tickers["HEAVYUSDT"] = {"quote_volume": 9e9}
    universe = pick_universe(tickers)
    SYMBOL_RULES = saved_rules
    check("كون أفضل 30 مع الاستبعادات", len(universe) == 30 and universe[0] == "C0USDT"
          and "USDCUSDT" not in universe and "BTCUPUSDT" not in universe and "HEAVYUSDT" not in universe)

    # 15) Dust: انتقاء الأصول المؤهلة + جدولة 24 ساعة
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

    # 16) Backoff إعادة الاتصال: مضاعفة مع سقف + Jitter
    b = WS_RECONNECT_MIN
    growth = []
    for _ in range(8):
        b, delay = next_backoff(b)
        growth.append(b)
    check("Backoff متزايد بسقف", abs(growth[0] - 2.0) < 1e-9 and growth[-1] == WS_RECONNECT_MAX
          and all(x <= WS_RECONNECT_MAX + 1e-9 for x in growth))

    # 17) صيغة /status الحرفية (بدون قائمة عملات نشطة)
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

    # 18) الوضع الصامت + /reset الحرفي + إشعار البدء مرة واحدة بالنص الحرفي
    saved_token, saved_chat, saved_dry = TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN
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
    globals()["save_state"] = real_save
    globals()["tg_api"] = real_tg_api
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN = saved_token, saved_chat, saved_dry
    check("الوضع الصامت: لا رسائل تلقائية — ردود الأوامر فقط", auto_blocked and manual_sent)
    check("أمر /reset: تصفير الإحصائيات + الرد الحرفي", reset_ok)
    check("إشعار البدء: مرة واحدة بالضبط بالنص الحرفي", startup_ok)

    # 19) Set & Forget: لا آلية Trailing إطلاقاً في الكود
    check("Set & Forget: لا Trailing إطلاقاً",
          all(name not in globals() for name in ("dynamic_trailing_plan", "activate_trailing", "place_trailing_oco"))
          and not any(str(key).startswith("TRAIL_") for key in globals()))

    # 20) إغلاق خاسر: عدّاد المتتالية يُحدَّث للتقرير فقط (بلا قواطع)
    globals()["save_state"] = _noop_save
    STATE = default_state()
    STATE["positions"]["TSTUSDT#y"] = {"symbol": "TSTUSDT", "entry": 100.0, "qty": "0.2", "order_ids": [701]}
    await finalize_position_event("TSTUSDT#y", STATE["positions"]["TSTUSDT#y"], 98.0, 0.2, "تنفيذ OCO (وقف)")
    loss_ok = (STATE["metrics"]["losses"] == 1 and STATE["metrics"]["consecutive_losses"] == 1
               and abs(STATE["metrics"]["realized_pnl"] + 0.4) < 1e-6 and not STATE["positions"])
    # حدث مكرر لنفس المركز → لا ازدواج محاسبة
    await finalize_position_event("TSTUSDT#y", {"symbol": "TSTUSDT", "entry": 100.0, "qty": "0.2"}, 98.0, 0.2, "مكرر")
    check("إغلاق خاسر + منع الازدواج", loss_ok and STATE["metrics"]["losses"] == 1)
    globals()["save_state"] = real_save

    # تنظيف
    STATE = default_state()
    CANDLES.clear(); TREND.clear(); BOOK.clear(); PENDING_TRIGGERS.clear(); ORDERS.clear()
    ENTRY_RESERVATIONS = {}; RESERVED_QUOTE = Decimal("0")
    SYMBOL_RULES.pop("TSTUSDT", None)
    try:
        os.remove(KILL_SWITCH_FILE)
    except OSError:
        pass

    print("النتيجة: " + ("ALL PASS ✅" if all(results) else "FAIL ❌"))
    return 0 if all(results) else 1


# ══════════════════════════════════════════════════════════════════════════════
# 13) التشغيل
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
                                     headers={"User-Agent": "NOVA-ASYNC-SCALPER/4.0"}) as session:
        SESSION = session
        REST = BinanceRest(session)
        # إقلاع REST: وقت الخادم → القواعد → الكون → تسخين الشموع
        await REST.sync_time()
        load_symbol_rules(await REST.exchange_info())
        await refresh_universe()
        for symbol in list(SYMBOLS):
            try:
                await seed_symbol(symbol)
            except Exception as exc:
                log(f"فشل تسخين {symbol}: {exc}")
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
            asyncio.create_task(universe_loop(hub), name="universe-loop"),
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
            f"تشغيل NOVA ASYNC SCALPER V4.0 [مدفوع بالأحداث] | {regime_text()} | Spot فقط | "
            f"فريم الإشارة {SIGNAL_INTERVAL} + فلتر EMA200({TREND_INTERVAL}) | "
            f"أفضل {TOP_N_SYMBOLS} زوجاً (تحديث كل {UNIVERSE_REFRESH_EVERY}ث) | "
            f"WebSocket: kline_{SIGNAL_INTERVAL}+kline_{TREND_INTERVAL}+bookTicker"
            f"{' + User Data Stream' if trading_enabled else ''} | "
            f"حجم {TRADE_NOTIONAL_D}$ | حتى {MAX_POSITIONS_PER_SYMBOL} مراكز/عملة بتهدئة {SAME_SYMBOL_COOLDOWN}ث | "
            f"وقف {STOP_ATR_MULT}×ATR هدف {TP_ATR_MULT}×ATR (OCO ثابت Set & Forget) | "
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
                # Dust: مسح أول إن كان مستحقاً (أكثر من 24 ساعة)
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
    try:
        asyncio.run(amain(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
