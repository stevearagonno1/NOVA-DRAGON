#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA SCALP AUTO v2.0

بوت سكالبينج Spot تلقائي على Binance، مضبوط افتراضياً على Spot Testnet.

الاستراتيجية المطبقة:
1) Macro Trend: البيتكوين BTC هو القائد الوحيد للسوق، ويجب أن يكون فوق EMA200
   على 15m و30m. كما يجب أن تكون العملة المرشحة نفسها فوق EMA200 على الفريمين.
2) Demand Setup: أربع شموع خضراء متتالية على الأقل مع BOS وفجوة FVG صاعدة.
3) Trigger: ينتظر Pullback إلى منطقة الطلب/FVG، ثم MACD سريع صاعد وفوليوم مرتفع
   على 1m قبل تنفيذ Market BUY.
4) الحماية: OCO فوري بعد الامتلاء، وقف ثابت أسفل منطقة الطلب وهدف عند Swing High.
   عند ربح 1% تقريباً يلغي البوت الحماية الثابتة ويضع OCO جديداً بوقف متحرك.

الملف لا يستخدم Futures أو رافعة أو بيعاً على المكشوف، ولا يستخدم مكتبات تحليل
جدولية. كل الاتصال الشبكي عبر requests، وتوقيع Binance عبر HMAC من المكتبة القياسية.

التثبيت في Termux:
    pkg update -y
    pkg install python -y
    pip install requests matplotlib

الإعداد:
    export BINANCE_ENV='testnet'
    export BINANCE_API_KEY='مفتاح Binance Spot Testnet'
    export BINANCE_API_SECRET='سر Binance Spot Testnet'
    export TELEGRAM_BOT_TOKEN='توكن Telegram جديد'
    export TELEGRAM_CHAT_ID='معرف المحادثة'

التشغيل:
    python scalp_bot.py --selftest
    python scalp_bot.py --dry-run
    python scalp_bot.py

لتفعيل Gemini كحاجز اختياري قبل الدخول:
    export AI_GATE_ENABLED='1'
    export GEMINI_API_KEY='مفتاح Gemini'

تحويله إلى Live يتطلب تغيير BINANCE_ENV وإضافة عبارة تأكيد يدوية داخل البيئة.
لا يوجد ضمان للربح؛ ابدأ بـ Testnet واختبر السلوك قبل أي أموال حقيقية.
"""

import csv
import hashlib
import hmac
import html
import json
import math
import os
import random
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    raise SystemExit("ثبّت requests أولاً: pip install requests")


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


BINANCE_ENV = os.getenv("BINANCE_ENV", "testnet").strip().lower()
if BINANCE_ENV not in ("testnet", "live"):
    BINANCE_ENV = "testnet"
BINANCE_BASE = "https://testnet.binance.vision" if BINANCE_ENV == "testnet" else "https://api.binance.com"
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "").strip()
LIVE_CONFIRM = os.getenv("LIVE_TRADING_CONFIRM", "")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

LEADERS = ["BTCUSDT"]
DEFAULT_SCALP_SYMBOLS = "BTCUSDT,SOLUSDT,LINKUSDT,RENDERUSDT,TONUSDT,FILUSDT,ATOMUSDT,VETUSDT,XLMUSDT,HNTUSDT,IMXUSDT,BNBUSDT"
SYMBOLS = []
for _symbol in os.getenv("SCALP_SYMBOLS", DEFAULT_SCALP_SYMBOLS).split(","):
    _symbol = _symbol.strip().upper()
    if _symbol and _symbol not in SYMBOLS:
        SYMBOLS.append(_symbol)
for _symbol in LEADERS:
    if _symbol not in SYMBOLS:
        SYMBOLS.insert(0, _symbol)

INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800}
KLINE_LIMIT = env_int("KLINE_LIMIT", 230)
MIN_CLOSED_CANDLES = 205

# استراتيجية الاتجاه
MACRO_INTERVALS = ("15m", "30m")
SIGNAL_INTERVAL = "1m"
SETUP_INTERVAL = "5m"
EMA_FAST = 9
EMA_SLOW = 21
EMA_MACRO = 200
RSI_PERIOD = 7
MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 4
ATR_PERIOD = 14
MIN_GREEN_CANDLES = env_int("MIN_GREEN_CANDLES", 4)
MAX_GREEN_CANDLES = env_int("MAX_GREEN_CANDLES", 8)
BOS_MIN_PCT = env_float("BOS_MIN_PCT", 0.03)
MIN_FVG_PCT = env_float("MIN_FVG_PCT", 0.02)
ZONE_MAX_AGE_CANDLES = env_int("ZONE_MAX_AGE_CANDLES", 72)
TOUCH_LOOKBACK_BARS = env_int("TOUCH_LOOKBACK_BARS", 5)
FIB_REQUIRED = env_bool("FIB_REQUIRED", True)
MIN_VOLUME_RATIO = env_float("MIN_VOLUME_RATIO", 1.20)
FLASH_MOVE_PCT = env_float("FLASH_MOVE_PCT", 2.8)
FLASH_RANGE_ATR = env_float("FLASH_RANGE_ATR", 5.5)
MIN_24H_QUOTE_VOLUME = env_float("MIN_24H_QUOTE_VOLUME", 1_000_000)
MAX_SPREAD_PCT = env_float("MAX_SPREAD_PCT", 0.12)
MIN_BOOK_IMBALANCE = env_float("MIN_BOOK_IMBALANCE", 0.44)
MIN_SCORE = env_float("MIN_SCORE", 50.0)

# رأس المال والحماية
AUTO_TRADE = env_bool("AUTO_TRADE", True)
DRY_RUN = env_bool("DRY_RUN", False)
AI_GATE_ENABLED = env_bool("AI_GATE_ENABLED", False)
REQUIRE_NEWS = env_bool("REQUIRE_NEWS", True)
TRADE_QUOTE_USD = env_float("TRADE_QUOTE_USD", 15.0)
MAX_POSITION_USD = env_float("MAX_POSITION_USD", 25.0)
MAX_POSITIONS = env_int("MAX_POSITIONS", 0)  # 0 = غير محدود، ويظل الرصيد/القواطع حاكمة
MAX_DAILY_TRADES = env_int("MAX_DAILY_TRADES", 0)  # 0 = غير محدود
MAX_ENTRIES_PER_SCAN = env_int("MAX_ENTRIES_PER_SCAN", 0)  # 0 = كل الفرص المؤكدة
MAX_DAILY_LOSS_USD = env_float("MAX_DAILY_LOSS_USD", 5.0)
MAX_CONSECUTIVE_LOSSES = env_int("MAX_CONSECUTIVE_LOSSES", 3)
SYMBOL_COOLDOWN = env_int("SYMBOL_COOLDOWN", 0)
SCAN_STATUS_EVERY = env_int("SCAN_STATUS_EVERY", 300)
STOP_ATR_MULT = env_float("STOP_ATR_MULT", 1.15)
TAKE_RR_MIN = env_float("TAKE_RR_MIN", 1.50)
ZONE_STOP_BUFFER_PCT = env_float("ZONE_STOP_BUFFER_PCT", 0.15)
TRAIL_ACTIVATION_PCT = env_float("TRAIL_ACTIVATION_PCT", 1.0)
TRAIL_ATR_MULT = env_float("TRAIL_ATR_MULT", 1.35)
FEE_BUFFER = env_float("FEE_BUFFER", 0.0015)
LIMIT_SLIPPAGE_PCT = env_float("LIMIT_SLIPPAGE_PCT", 0.20)

# التشغيل والملفات
SCAN_EVERY = env_int("SCAN_EVERY", 12)
MANAGE_EVERY = env_int("MANAGE_EVERY", 4)
TELEGRAM_POLL_TIMEOUT = env_int("TELEGRAM_POLL_TIMEOUT", 20)
SEND_CHARTS = env_bool("SEND_CHARTS", True)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "scalp_data_v2")
CHART_DIR = os.path.join(DATA_DIR, "charts")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
TRADES_FILE = os.path.join(DATA_DIR, "trades.csv")
KILL_SWITCH_FILE = os.path.join(DATA_DIR, "STOP_TRADING")
GEMINI_MODELS = [x.strip() for x in os.getenv("GEMINI_MODELS", "gemini-2.5-flash,gemini-2.0-flash,gemini-flash-latest").split(",") if x.strip()]
GEMINI_MIN_INTERVAL = env_int("GEMINI_MIN_INTERVAL", 8)
NEWS_CACHE_SECONDS = env_int("NEWS_CACHE_SECONDS", 300)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "NOVA-SCALP-AUTO/2.0"})
STATE_LOCK = threading.RLock()
SCAN_LOCK = threading.Lock()
GEMINI_LOCK = threading.Lock()
LAST_GEMINI_CALL = 0.0
NEWS_CACHE = {"time": 0.0, "items": []}
TIME_OFFSET_MS = 0
SYMBOL_RULES = {}
CHARTS_OK = None
ENTRY_LOCK = threading.Lock()
ENTRY_RESERVATIONS = set()
LAST_STATUS_MESSAGE = 0.0


# ══════════════════════════════════════════════════════════════════════════════
# 2) الذاكرة والسجل
# ══════════════════════════════════════════════════════════════════════════════


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CHART_DIR, exist_ok=True)


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
        "last_heartbeat": 0.0,
        "last_digest": "",
        "cooldowns": {},
        "setups": {},
        "positions": {},
        "last_signals": [],
        "gemini_model": None,
        "metrics": {
            "day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "trades": 0,
            "realized_pnl": 0.0,
            "wins": 0,
            "losses": 0,
            "consecutive_losses": 0,
        },
    }


STATE = default_state()


def reset_metrics():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if STATE.get("metrics", {}).get("day") != today:
        STATE["metrics"] = {
            "day": today,
            "trades": 0,
            "realized_pnl": 0.0,
            "wins": 0,
            "losses": 0,
            "consecutive_losses": 0,
        }


def load_state():
    global STATE
    ensure_dirs()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
        base = default_state()
        if isinstance(saved, dict):
            base.update(saved)
        for key in ("setups", "positions", "cooldowns"):
            if not isinstance(base.get(key), dict):
                base[key] = {}
        if not isinstance(base.get("last_signals"), list):
            base["last_signals"] = []
        reset_metrics()
        STATE = base
        log(f"ذاكرة v2: {len(STATE['setups'])} إعدادات، {len(STATE['positions'])} مراكز")
    except FileNotFoundError:
        log("لا توجد ذاكرة v2؛ بداية جديدة")
    except Exception as exc:
        log(f"تعذر تحميل الذاكرة: {exc}")


def save_state():
    try:
        ensure_dirs()
        with STATE_LOCK:
            temp = STATE_FILE + ".tmp"
            with open(temp, "w", encoding="utf-8") as handle:
                json.dump(STATE, handle, ensure_ascii=False, indent=2)
            os.replace(temp, STATE_FILE)
    except Exception as exc:
        log(f"فشل حفظ الذاكرة: {exc}")


def record_trade(row):
    try:
        ensure_dirs()
        fresh = not os.path.exists(TRADES_FILE)
        with open(TRADES_FILE, "a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            if fresh:
                writer.writerow(["time", "symbol", "entry", "exit", "qty", "pnl", "reason", "score", "environment"])
            writer.writerow(row)
    except Exception as exc:
        log(f"تعذر كتابة سجل الصفقة: {exc}")


def esc(value):
    return html.escape(str(value))


def symbol_name(symbol):
    return symbol.replace("USDT", "/USDT")


def pct(value):
    return f"{float(value):+.2f}%"


def clamp(value, low, high):
    return max(low, min(high, value))


def make_client_id(prefix):
    return (prefix + uuid.uuid4().hex[:20]).upper()[:36]


def kill_switch_active():
    return os.path.exists(KILL_SWITCH_FILE)


# ══════════════════════════════════════════════════════════════════════════════
# 3) الرياضيات النقية
# ══════════════════════════════════════════════════════════════════════════════


def sma(values, period):
    result = [None] * len(values)
    if period <= 0 or len(values) < period:
        return result
    total = sum(values[:period])
    result[period - 1] = total / period
    for i in range(period, len(values)):
        total += values[i] - values[i - period]
        result[i] = total / period
    return result


def ema(values, period):
    result = [None] * len(values)
    if period <= 0 or len(values) < period:
        return result
    alpha = 2.0 / (period + 1.0)
    previous = sum(values[:period]) / period
    result[period - 1] = previous
    for i in range(period, len(values)):
        previous = values[i] * alpha + previous * (1.0 - alpha)
        result[i] = previous
    return result


def rsi(values, period=14):
    result = [None] * len(values)
    if len(values) < period + 1:
        return result
    gains = losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    average_gain = gains / period
    average_loss = losses / period
    result[period] = 100.0 if average_loss == 0 else 100.0 - 100.0 / (1.0 + average_gain / average_loss)
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        average_gain = (average_gain * (period - 1) + max(change, 0.0)) / period
        average_loss = (average_loss * (period - 1) + max(-change, 0.0)) / period
        result[i] = 100.0 if average_loss == 0 else 100.0 - 100.0 / (1.0 + average_gain / average_loss)
    return result


def macd(values, fast=12, slow=26, signal_period=9):
    fast_values = ema(values, fast)
    slow_values = ema(values, slow)
    line = [None if fast_values[i] is None or slow_values[i] is None else fast_values[i] - slow_values[i] for i in range(len(values))]
    valid = [x for x in line if x is not None]
    signal_valid = ema(valid, signal_period)
    signal = [None] * len(values)
    pointer = 0
    for i, value in enumerate(line):
        if value is not None:
            signal[i] = signal_valid[pointer]
            pointer += 1
    hist = [None if line[i] is None or signal[i] is None else line[i] - signal[i] for i in range(len(values))]
    return line, signal, hist


def true_ranges(highs, lows, closes):
    if not closes:
        return []
    result = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        result.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    return result


def atr(highs, lows, closes, period=14):
    result = [None] * len(closes)
    if len(closes) < period:
        return result
    ranges = true_ranges(highs, lows, closes)
    current = sum(ranges[:period]) / period
    result[period - 1] = current
    for i in range(period, len(ranges)):
        current = (current * (period - 1) + ranges[i]) / period
        result[i] = current
    return result


def vwap(highs, lows, closes, volumes, period=24):
    result = [None] * len(closes)
    if len(closes) < period:
        return result
    for i in range(period - 1, len(closes)):
        pv = 0.0
        vv = 0.0
        for j in range(i - period + 1, i + 1):
            pv += ((highs[j] + lows[j] + closes[j]) / 3.0) * volumes[j]
            vv += volumes[j]
        result[i] = pv / vv if vv else None
    return result


def last_valid(values, default=0.0):
    for value in reversed(values):
        if value is not None:
            return value
    return default


def crossed_up(left, right, bars=4):
    for i in range(max(1, len(left) - bars), len(left)):
        if None in (left[i - 1], right[i - 1], left[i], right[i]):
            continue
        if left[i - 1] <= right[i - 1] and left[i] > right[i]:
            return True
    return False


def fibonacci_levels(swing_low, swing_high):
    """مستويات Fibonacci من موجة صاعدة: 0 عند القمة و1 عند القاع."""
    swing_low = float(swing_low)
    swing_high = float(swing_high)
    distance = swing_high - swing_low
    if distance <= 0:
        return {}
    return {
        "0.236": swing_high - distance * 0.236,
        "0.382": swing_high - distance * 0.382,
        "0.500": swing_high - distance * 0.500,
        "0.618": swing_high - distance * 0.618,
        "0.786": swing_high - distance * 0.786,
        "1.000": swing_low,
        "1.272": swing_high + distance * 0.272,
        "1.618": swing_high + distance * 0.618,
    }


def fibonacci_confluence(levels, low_price, high_price):
    """يعيد أقرب Retracement داخل FVG/منطقة الطلب، إن وجد."""
    if not levels or high_price < low_price:
        return None, None
    preferred = ("0.382", "0.500", "0.618", "0.786")
    hits = [(ratio, price) for ratio, price in levels.items() if ratio in preferred and low_price <= price <= high_price]
    if not hits:
        return None, None
    # نفضل 0.5 و0.618 باعتبارهما منطقتي تراجع شائعتين.
    hits.sort(key=lambda item: (0 if item[0] in ("0.500", "0.618") else 1, abs(float(item[0]) - 0.55)))
    return hits[0]


# ══════════════════════════════════════════════════════════════════════════════
# 4) عميل Binance REST الموقّع
# ══════════════════════════════════════════════════════════════════════════════


class BinanceError(Exception):
    def __init__(self, message, code=None, status=None):
        super().__init__(message)
        self.code = code
        self.status = status


class BinanceClient:
    def __init__(self):
        self.base = BINANCE_BASE

    def parse(self, response):
        try:
            payload = response.json()
        except ValueError:
            raise BinanceError(f"استجابة Binance غير صالحة HTTP {response.status_code}", status=response.status_code)
        if response.status_code >= 400 or (isinstance(payload, dict) and payload.get("code", 0) < 0):
            message = payload.get("msg", "خطأ Binance") if isinstance(payload, dict) else "خطأ Binance"
            raise BinanceError(message, payload.get("code") if isinstance(payload, dict) else None, response.status_code)
        return payload

    def public(self, path, params=None, timeout=12):
        try:
            response = SESSION.get(self.base + path, params=params or {}, timeout=timeout)
            return self.parse(response)
        except requests.RequestException as exc:
            raise BinanceError(f"شبكة Binance: {exc}")

    def sync_time(self):
        global TIME_OFFSET_MS
        payload = self.public("/api/v3/time", timeout=8)
        TIME_OFFSET_MS = int(payload["serverTime"]) - int(time.time() * 1000)

    def signed(self, method, path, params=None, retry=True, timeout=15):
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            raise BinanceError("مفاتيح Binance غير موجودة")
        values = dict(params or {})
        values["recvWindow"] = values.get("recvWindow", 5000)
        values["timestamp"] = int(time.time() * 1000) + TIME_OFFSET_MS
        query = urlencode(values, doseq=True)
        values["signature"] = hmac.new(BINANCE_API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
        headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
        try:
            method = method.upper()
            if method == "GET":
                response = SESSION.get(self.base + path, params=values, headers=headers, timeout=timeout)
            elif method == "DELETE":
                response = SESSION.delete(self.base + path, params=values, headers=headers, timeout=timeout)
            else:
                response = SESSION.post(self.base + path, data=values, headers=headers, timeout=timeout)
            try:
                return self.parse(response)
            except BinanceError as exc:
                if retry and exc.code == -1021:
                    self.sync_time()
                    return self.signed(method, path, params, retry=False, timeout=timeout)
                raise
        except requests.RequestException as exc:
            raise BinanceError(f"شبكة Binance الموقعة: {exc}")

    def exchange_info(self):
        return self.public("/api/v3/exchangeInfo", timeout=20)

    def klines(self, symbol, interval, limit=KLINE_LIMIT):
        payload = self.public("/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit}, timeout=12)
        if not isinstance(payload, list) or len(payload) < 80:
            return None
        try:
            return {
                "t": [int(row[0]) for row in payload],
                "o": [float(row[1]) for row in payload],
                "h": [float(row[2]) for row in payload],
                "l": [float(row[3]) for row in payload],
                "c": [float(row[4]) for row in payload],
                "v": [float(row[5]) for row in payload],
                "qv": [float(row[7]) for row in payload],
                "live": float(payload[-1][4]),
            }
        except (IndexError, TypeError, ValueError):
            return None

    def ticker_24h(self, symbols):
        payload = self.public("/api/v3/ticker/24hr", {"symbols": json.dumps(symbols, separators=(",", ":"))}, timeout=15)
        result = {}
        for row in payload if isinstance(payload, list) else []:
            try:
                result[row["symbol"]] = {"price": float(row["lastPrice"]), "change": float(row["priceChangePercent"]), "quote_volume": float(row["quoteVolume"])}
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def book_ticker(self, symbol):
        row = self.public("/api/v3/ticker/bookTicker", {"symbol": symbol}, timeout=8)
        return {"bid": float(row["bidPrice"]), "ask": float(row["askPrice"]), "bid_qty": float(row["bidQty"]), "ask_qty": float(row["askQty"])}

    def depth(self, symbol, limit=20):
        row = self.public("/api/v3/depth", {"symbol": symbol, "limit": limit}, timeout=8)
        bids = [(float(x[0]), float(x[1])) for x in row.get("bids", [])]
        asks = [(float(x[0]), float(x[1])) for x in row.get("asks", [])]
        bid_value = sum(price * qty for price, qty in bids)
        ask_value = sum(price * qty for price, qty in asks)
        total = bid_value + ask_value
        return bid_value / total if total else 0.5

    def account(self):
        return self.signed("GET", "/api/v3/account")

    def free_balance(self, asset, account=None):
        account = account or self.account()
        for row in account.get("balances", []):
            if row.get("asset") == asset:
                return D(row.get("free", "0"))
        return Decimal("0")

    def new_order(self, params):
        return self.signed("POST", "/api/v3/order", params)

    def get_order(self, symbol, order_id):
        return self.signed("GET", "/api/v3/order", {"symbol": symbol, "orderId": order_id})

    def cancel_order(self, symbol, order_id):
        return self.signed("DELETE", "/api/v3/order", {"symbol": symbol, "orderId": order_id})

    def cancel_oco(self, symbol, order_list_id):
        return self.signed("DELETE", "/api/v3/orderList", {"symbol": symbol, "orderListId": order_list_id})

    def order_list(self, order_list_id):
        return self.signed("GET", "/api/v3/orderList", {"orderListId": order_list_id})

    def new_oco(self, params):
        return self.signed("POST", "/api/v3/orderList/oco", params)

    def cancel_all(self, symbol):
        return self.signed("DELETE", "/api/v3/openOrders", {"symbol": symbol})


CLIENT = BinanceClient()


def load_symbol_rules(payload):
    global SYMBOL_RULES
    SYMBOL_RULES = {}
    for item in (payload or {}).get("symbols", []):
        symbol = item.get("symbol")
        if symbol not in SYMBOLS:
            continue
        filters = {x.get("filterType"): x for x in item.get("filters", [])}
        lot = filters.get("LOT_SIZE", {})
        market_lot = filters.get("MARKET_LOT_SIZE", lot)
        price = filters.get("PRICE_FILTER", {})
        notion = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {}))
        trailing = filters.get("TRAILING_DELTA", {})
        SYMBOL_RULES[symbol] = {
            "status": item.get("status"),
            "base": item.get("baseAsset"),
            "quote": item.get("quoteAsset"),
            "tick": D(price.get("tickSize", "0.00000001")),
            "step": D(market_lot.get("stepSize", lot.get("stepSize", "0.00000001"))),
            "min_qty": D(market_lot.get("minQty", lot.get("minQty", "0"))),
            "max_qty": D(market_lot.get("maxQty", lot.get("maxQty", "999999999"))),
            "min_notional": D(notion.get("minNotional", "0")),
            "min_trailing_below": int(trailing.get("minTrailingBelowDelta", 10)),
            "max_trailing_below": int(trailing.get("maxTrailingBelowDelta", 2000)),
        }
    log(f"قواعد Binance: {len(SYMBOL_RULES)} زوجاً قابلاً للفحص")


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
# 5) فحص جودة البيانات وتحليل الفريم
# ══════════════════════════════════════════════════════════════════════════════


def quality_check(raw, interval, atr_value):
    errors = []
    if not raw or len(raw.get("c", [])) < 80:
        return {"ok": False, "flash": False, "errors": ["شموع غير كافية"]}
    n = len(raw["c"])
    for i in range(n):
        try:
            values = (raw["o"][i], raw["h"][i], raw["l"][i], raw["c"][i], raw["v"][i])
            if not all(math.isfinite(float(x)) for x in values):
                errors.append("رقم غير صالح")
                break
            if raw["h"][i] < max(raw["o"][i], raw["c"][i]) or raw["l"][i] > min(raw["o"][i], raw["c"][i]):
                errors.append("OHLC غير منطقي")
                break
        except (IndexError, TypeError, ValueError):
            errors.append("بيانات مكسورة")
            break
    for i in range(1, n):
        if raw["t"][i] <= raw["t"][i - 1]:
            errors.append("الوقت غير مرتب")
            break
    interval_ms = INTERVAL_SECONDS.get(interval, 60) * 1000
    if raw.get("t") and int(time.time() * 1000) - raw["t"][-1] > interval_ms * 3:
        errors.append("البيانات قديمة")
    closed_c = raw["c"][:-1]
    closed_h = raw["h"][:-1]
    closed_l = raw["l"][:-1]
    flash = False
    flash_reason = ""
    if len(closed_c) > 1 and atr_value > 0:
        move = abs(closed_c[-1] / closed_c[-2] - 1.0) * 100.0
        range_multiple = (closed_h[-1] - closed_l[-1]) / atr_value
        if move >= FLASH_MOVE_PCT:
            flash, flash_reason = True, f"حركة {move:.2f}% في شمعة"
        elif range_multiple >= FLASH_RANGE_ATR:
            flash, flash_reason = True, f"مدى {range_multiple:.1f}× ATR"
    if flash:
        errors.append("حركة شاذة: " + flash_reason)
    return {"ok": not errors, "flash": flash, "flash_reason": flash_reason, "errors": errors}


def analyze_frame(raw, interval):
    if not raw:
        return None
    closed = {key: raw[key][:-1] for key in ("t", "o", "h", "l", "c", "v", "qv")}
    if len(closed["c"]) < MIN_CLOSED_CANDLES:
        return None
    c, h, l, o, v = closed["c"], closed["h"], closed["l"], closed["o"], closed["v"]
    ema_fast = ema(c, EMA_FAST)
    ema_slow = ema(c, EMA_SLOW)
    ema_200 = ema(c, EMA_MACRO)
    ml, ms, hist = macd(c, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    rs = rsi(c, RSI_PERIOD)
    at = atr(h, l, c, ATR_PERIOD)
    vw = vwap(h, l, c, v, 24)
    av = sma(v, 20)
    atr_value = last_valid(at, 0.0)
    quality = quality_check(raw, interval, atr_value)
    volume_ratio = v[-1] / av[-1] if av[-1] else 0.0
    ef, es, e200 = last_valid(ema_fast), last_valid(ema_slow), last_valid(ema_200)
    trend = "up" if c[-1] > ef > es else "down" if c[-1] < ef < es else "side"
    candle_range = max(h[-1] - l[-1], 1e-12)
    lower = min(o[-1], c[-1]) - l[-1]
    upper = h[-1] - max(o[-1], c[-1])
    return {
        "interval": interval, "raw": raw, "t": closed["t"], "o": o, "h": h, "l": l, "c": c, "v": v,
        "close": c[-1], "ema_fast": ef, "ema_slow": es, "ema200": e200,
        "ema_fast_series": ema_fast, "ema_slow_series": ema_slow, "ema200_series": ema_200,
        "macd": last_valid(ml), "macd_signal": last_valid(ms), "hist": last_valid(hist),
        "hist_prev": hist[-2] if hist[-2] is not None else 0.0,
        "macd_up": crossed_up(ml, ms, 4), "macd_down": False,
        "macd_line_series": ml, "macd_signal_series": ms, "hist_series": hist,
        "rsi": last_valid(rs, 50.0), "rsi_prev": rs[-2] if rs[-2] is not None else 50.0, "rsi_series": rs,
        "atr": atr_value, "atr_pct": atr_value / c[-1] * 100.0 if c[-1] else 0.0, "atr_series": at,
        "vwap": last_valid(vw, c[-1]), "vwap_series": vw, "volume_average": av, "volume_ratio": volume_ratio,
        "trend": trend, "prev_high": h[-2], "prev_low": l[-2],
        "lower_wick_ratio": lower / candle_range, "upper_wick_ratio": upper / candle_range,
        "quality": quality,
    }


def fetch_frames(symbol):
    frames = {}
    for interval in ("1m", "5m", "15m", "30m"):
        frames[interval] = analyze_frame(CLIENT.klines(symbol, interval), interval)
    return frames if all(frames.values()) else None


def book_stats(symbol):
    book = CLIENT.book_ticker(symbol)
    mid = (book["bid"] + book["ask"]) / 2.0
    spread = (book["ask"] - book["bid"]) / mid * 100.0 if mid else 99.0
    try:
        imbalance = CLIENT.depth(symbol, 20)
    except BinanceError:
        imbalance = 0.5
    return {"bid": book["bid"], "ask": book["ask"], "spread_pct": spread, "imbalance": imbalance}


def macro_trend_ok(asset_frames, leader_frames):
    reasons = []
    for leader in LEADERS:
        frames = leader_frames.get(leader)
        if not frames:
            return False, f"بيانات {leader} غير مكتملة"
        for interval in MACRO_INTERVALS:
            frame = frames.get(interval)
            if not frame or not frame["quality"]["ok"]:
                return False, f"جودة {leader} {interval} غير صالحة"
            if frame["ema200"] is None or frame["close"] <= frame["ema200"]:
                return False, f"{leader} تحت EMA200 على {interval}"
    for interval in MACRO_INTERVALS:
        frame = asset_frames.get(interval)
        if not frame or frame["ema200"] is None or frame["close"] <= frame["ema200"]:
            return False, f"العملة تحت EMA200 على {interval}"
        reasons.append(f"{interval} فوق EMA200")
    return True, " و".join(reasons)


# ══════════════════════════════════════════════════════════════════════════════
# 6) Demand Zone + BOS + FVG + Pullback Trigger
# ══════════════════════════════════════════════════════════════════════════════


def detect_demand_zone(frame):
    """يبحث عن أحدث اندفاع أخضر متصل، كسر هيكل وفجوة FVG صاعدة."""
    if not frame:
        return None
    o, h, l, c, t = frame["o"], frame["h"], frame["l"], frame["c"], frame["t"]
    n = len(c)
    first_end = n - 1
    last_start = max(5, n - ZONE_MAX_AGE_CANDLES - MAX_GREEN_CANDLES)
    for end in range(first_end, last_start, -1):
        if c[end] <= o[end]:
            continue
        start = end
        while start > 0 and c[start - 1] > o[start - 1] and end - start + 1 < MAX_GREEN_CANDLES:
            start -= 1
        length = end - start + 1
        if length < MIN_GREEN_CANDLES:
            continue
        base_start = max(0, start - 3)
        prior_window = h[max(0, base_start - 20):base_start]
        if not prior_window:
            continue
        prior_swing_high = max(prior_window)
        impulse_high = max(h[start:end + 1])
        bos = max(c[start:end + 1]) > prior_swing_high * (1.0 + BOS_MIN_PCT / 100.0)
        if not bos:
            continue
        fvg = None
        for i in range(start, end - 1):
            # Bullish FVG: low of candle 3 remains above high of candle 1.
            if l[i + 2] > h[i] * (1.0 + MIN_FVG_PCT / 100.0):
                fvg = {"low": h[i], "high": l[i + 2], "index": i}
        if not fvg:
            continue
        zone_low = min(l[base_start:start + 1])
        zone_high = max(h[base_start:start + 1])
        if zone_high <= zone_low:
            continue
        impulse_low = min(l[base_start:start + 1])
        fib = fibonacci_levels(impulse_low, impulse_high)
        fib_ratio, fib_price = fibonacci_confluence(fib, fvg["low"], fvg["high"])
        if FIB_REQUIRED and fib_ratio is None:
            continue
        # لا نعتمد منطقة كسرت وأغلقت الشموع اللاحقة تحتها.
        invalidated = any(c[j] < zone_low for j in range(end + 1, n))
        if invalidated:
            continue
        age = n - 1 - end
        if age > ZONE_MAX_AGE_CANDLES:
            continue
        return {
            "id": hashlib.sha1(f"{frame['interval']}:{t[end]}:{fvg['low']}:{fvg['high']}".encode()).hexdigest()[:16],
            "created_time": t[end], "start_index": start, "end_index": end, "age": age,
            "green_count": length, "bos": True, "prior_swing_high": prior_swing_high,
            "zone_low": zone_low, "zone_high": zone_high,
            "fvg_low": fvg["low"], "fvg_high": fvg["high"], "fvg_index": fvg["index"],
            "target_high": impulse_high, "impulse_low": impulse_low,
            "fib": fib, "fib_ratio": fib_ratio, "fib_price": fib_price,
        }
    return None


def zone_touched(zone, signal_frame):
    if not zone or not signal_frame:
        return False
    lows, highs = signal_frame["l"], signal_frame["h"]
    start = max(0, len(lows) - TOUCH_LOOKBACK_BARS)
    for i in range(start, len(lows)):
        if lows[i] <= zone["zone_high"] and highs[i] >= zone["zone_low"]:
            return True
        if lows[i] <= zone["fvg_high"] and highs[i] >= zone["fvg_low"]:
            return True
    return False


def build_candidate(symbol, frames, leader_frames, quote_volume):
    if not frames or quote_volume < MIN_24H_QUOTE_VOLUME:
        return None
    if any(not frames[x]["quality"]["ok"] for x in ("1m", "5m", "15m", "30m")):
        return None
    macro_ok, macro_reason = macro_trend_ok(frames, leader_frames)
    if not macro_ok:
        return None
    zone = detect_demand_zone(frames["5m"])
    if not zone:
        return None
    signal = frames["1m"]
    setup = frames["5m"]
    touched = zone_touched(zone, signal)
    if not touched:
        # منطقة صحيحة لكن لم يحدث Pullback بعد؛ تسجل كإعداد انتظار.
        return {"symbol": symbol, "zone": zone, "frames": frames, "leader_frames": leader_frames,
                "macro_reason": macro_reason, "confirmed": False, "quote_volume": quote_volume}
    book = book_stats(symbol)
    if book["spread_pct"] > MAX_SPREAD_PCT or book["imbalance"] < MIN_BOOK_IMBALANCE:
        return None
    momentum = signal["macd_up"] or (signal["hist"] > signal["hist_prev"] and signal["hist"] > 0)
    volume_ok = signal["volume_ratio"] >= MIN_VOLUME_RATIO
    bullish_candle = signal["c"][-1] > signal["o"][-1] and signal["c"][-1] > signal["ema_fast"]
    vwap_ok = signal["c"][-1] >= signal["vwap"]
    confirmed = momentum and volume_ok and bullish_candle and vwap_ok
    score = 0.0
    score += 22.0  # macro فوق EMA200 على 15m/30m
    score += 20.0 if zone["green_count"] >= 4 else 0.0
    score += 18.0 if zone["bos"] else 0.0
    score += 15.0 if zone["fvg_high"] > zone["fvg_low"] else 0.0
    score += 5.0 if zone.get("fib_ratio") else 0.0
    score += 12.0 if signal["macd_up"] else 8.0 if momentum else 0.0
    score += min(8.0, 6.0 * signal["volume_ratio"] / max(MIN_VOLUME_RATIO, 0.1))
    score += 3.0 if book["imbalance"] >= 0.55 else 1.0
    score = round(clamp(score, 0.0, 100.0), 1)
    if not confirmed or score < MIN_SCORE:
        return {"symbol": symbol, "zone": zone, "frames": frames, "leader_frames": leader_frames,
                "macro_reason": macro_reason, "confirmed": False, "quote_volume": quote_volume,
                "book": book, "score": score}
    price = book["ask"]
    # الوقف تحت منطقة الطلب، والهدف عند القمة التي صنعها الاندفاع.
    stop = zone["zone_low"] * (1.0 - ZONE_STOP_BUFFER_PCT / 100.0)
    target = zone["target_high"] * (1.0 - 0.03 / 100.0)
    risk = price - stop
    reward = target - price
    if risk <= 0 or reward <= 0 or reward / risk < TAKE_RR_MIN:
        return None
    trail_pct = clamp(max(signal["atr_pct"] * TRAIL_ATR_MULT, 0.30), 0.30, 2.50)
    rule = SYMBOL_RULES.get(symbol, {})
    trail_bips = int(clamp(round(trail_pct * 100.0), rule.get("min_trailing_below", 10), rule.get("max_trailing_below", 2000)))
    stop_pct = risk / price * 100.0
    target_pct = reward / price * 100.0
    return {
        "symbol": symbol, "zone": zone, "frames": frames, "leader_frames": leader_frames,
        "macro_reason": macro_reason, "confirmed": True, "quote_volume": quote_volume,
        "signal": signal, "book": book, "price": price, "score": score,
        "stop": stop, "target": target, "stop_pct": stop_pct, "target_pct": target_pct,
        "trail_pct": trail_bips / 100.0, "trail_bips": trail_bips, "created_at": time.time(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7) الأخبار وGemini كحاجز اختياري
# ══════════════════════════════════════════════════════════════════════════════


def fetch_news(symbol):
    global NEWS_CACHE
    now = time.time()
    if now - NEWS_CACHE["time"] < NEWS_CACHE_SECONDS:
        source = NEWS_CACHE["items"]
    else:
        try:
            response = SESSION.get("https://min-api.cryptocompare.com/data/v2/news/", params={"lang": "EN", "sortOrder": "latest", "limit": 30}, timeout=12)
            if response.status_code != 200:
                return [], False
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("Data"), list):
                return [], False
            source = payload["Data"]
            NEWS_CACHE = {"time": now, "items": source}
        except (requests.RequestException, ValueError):
            return [], False
    base = symbol.replace("USDT", "").upper()
    result = []
    for item in source:
        text = " ".join(str(item.get(k, "")) for k in ("title", "body", "categories")).upper()
        if base in text or any(word in text for word in ("CRYPTO", "MARKET", "BITCOIN", "SEC", "ETF")):
            result.append({"title": str(item.get("title", ""))[:180], "source": str(item.get("source", ""))[:60]})
        if len(result) >= 6:
            break
    return result, True


PERSONA = (
    "أنت مدير تداول مؤسسي صارم. راجع بيانات سكالبينج والأخبار الحالية. "
    "إذا كان هناك خطر جوهري يفسد الدخول اكتب إلغاء فقط، وإلا اكتب سطرين بالعربية "
    "يذكران السيناريو والخطر الرئيسي. لا تضمن الربح ولا تنفذ أوامر."
)


def gemini_call(prompt):
    global LAST_GEMINI_CALL
    if not GEMINI_API_KEY:
        return None, "مفتاح Gemini غير موجود"
    with GEMINI_LOCK:
        wait = GEMINI_MIN_INTERVAL - (time.time() - LAST_GEMINI_CALL)
        if wait > 0:
            time.sleep(wait)
        models = []
        if STATE.get("gemini_model"):
            models.append(STATE["gemini_model"])
        models += [x for x in GEMINI_MODELS if x not in models]
        for model in models:
            try:
                response = SESSION.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": GEMINI_API_KEY},
                    json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.15, "maxOutputTokens": 180}},
                    timeout=25,
                )
                LAST_GEMINI_CALL = time.time()
                if response.status_code in (429, 500, 503):
                    time.sleep(2)
                    continue
                payload = response.json()
                candidates = payload.get("candidates") or []
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = " ".join(str(x.get("text", "")) for x in parts).strip()
                    if text:
                        STATE["gemini_model"] = model
                        return text, None
            except (requests.RequestException, ValueError, KeyError):
                continue
    return None, "تعذر الوصول إلى Gemini"


def ai_gate(candidate, news):
    signal = candidate["frames"]["1m"]
    zone = candidate["zone"]
    headlines = "\n".join(f"- {x['title']} | {x['source']}" for x in news) or "لا توجد عناوين مطابقة"
    prompt = (
        f"{PERSONA}\n"
        f"العملة {symbol_name(candidate['symbol'])}, السعر {candidate['price']:.12g}, score {candidate['score']}/100. "
        f"RSI7={signal['rsi']:.2f}, MACD Hist={signal['hist']:.8g}, Volume={signal['volume_ratio']:.2f}x, "
        f"FVG={zone['fvg_low']:.8g}-{zone['fvg_high']:.8g}, Demand={zone['zone_low']:.8g}-{zone['zone_high']:.8g}, "
        f"Fibonacci={zone.get('fib_ratio')} عند {zone.get('fib_price')}, "
        f"BOS=True, 15m/30m فوق EMA200، spread={candidate['book']['spread_pct']:.3f}%.\n"
        f"الأخبار:\n{headlines}\n"
        "التزم حرفياً: إلغاء فقط عند خطر جوهري، وإلا سطران فقط."
    )
    text, reason = gemini_call(prompt)
    if not text:
        return False, "حجب آمن: " + reason
    cleaned = text.replace("**", "").replace("`", "").strip()
    if cleaned.lower().startswith(("إلغاء", "الغاء", "cancel")):
        return False, "Gemini رفض الدخول"
    return True, cleaned[:650]


# ══════════════════════════════════════════════════════════════════════════════
# 8) Telegram والرسائل
# ══════════════════════════════════════════════════════════════════════════════


def tg_call(method, payload=None, files=None, retries=3):
    if not TELEGRAM_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    for attempt in range(retries):
        try:
            if files:
                response = SESSION.post(url, data=payload or {}, files=files, timeout=30)
            else:
                response = SESSION.post(url, json=payload or {}, timeout=30)
            data = response.json()
            if data.get("ok"):
                return data.get("result")
            if response.status_code == 429:
                time.sleep(2 + attempt)
        except (requests.RequestException, ValueError):
            time.sleep(1 + attempt)
    return None


def send_message(text, keyboard=None, chat_id=None):
    if DRY_RUN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n" + "═" * 72 + "\n[Telegram محاكاة]\n" + text + "\n" + "═" * 72)
        return True
    payload = {"chat_id": chat_id or TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if keyboard is not None:
        payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
    return bool(tg_call("sendMessage", payload))


def send_photo(path, caption, chat_id=None):
    if DRY_RUN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[صورة Telegram محاكاة] {path}\n{caption}")
        return True
    try:
        with open(path, "rb") as image:
            return bool(tg_call("sendPhoto", {"chat_id": chat_id or TELEGRAM_CHAT_ID, "caption": caption[:1024]}, {"photo": (os.path.basename(path), image, "image/png")}))
    except OSError:
        return False


def button(text, data):
    return {"text": text, "callback_data": data}


def main_keyboard():
    return [
        [button("📡 الحالة", "status"), button("🔎 فحص", "scan")],
        [button("⏸ إيقاف", "pause"), button("▶ استئناف", "resume")],
        [button("🧯 إلغاء الأوامر", "cancelall"), button("❓ المساعدة", "help")],
    ]


def regime_text():
    return "TESTNET" if BINANCE_ENV == "testnet" else "LIVE"


def status_text():
    reset_metrics()
    m = STATE["metrics"]
    lines = [
        f"📡 <b>NOVA SCALP AUTO v2</b> — {regime_text()}",
        f"التنفيذ: {'✅ آلي' if live_execution_allowed() else '🟡 غير مفعّل'} | الفحص: {'⏸' if STATE.get('paused') else '✅'}",
        f"اليوم: {m['day']} | صفقات {m['trades']}/{MAX_DAILY_TRADES if MAX_DAILY_TRADES > 0 else '∞'} | PnL {m['realized_pnl']:+.5f}$",
        f"خسائر متتالية: {m['consecutive_losses']}/{MAX_CONSECUTIVE_LOSSES}",
        f"إعدادات انتظار Pullback: {len(STATE.get('setups', {}))} | مراكز: {len(STATE.get('positions', {}))}/{MAX_POSITIONS if MAX_POSITIONS > 0 else '∞'}",
    ]
    for symbol, setup in STATE.get("setups", {}).items():
        lines.append(f"⏳ {symbol_name(symbol)} | Demand {fmt_price(symbol, setup['zone_low'])}-{fmt_price(symbol, setup['zone_high'])} | FVG {fmt_price(symbol, setup['fvg_low'])}-{fmt_price(symbol, setup['fvg_high'])} | Fib {setup.get('fib_ratio') or '—'}")
    for symbol, position in STATE.get("positions", {}).items():
        lines.append(f"🟢 {symbol_name(symbol)} | دخول {fmt_price(symbol, position['entry'])} | هدف {fmt_price(symbol, position['target'])} | {'Trailing ✅' if position.get('trailing_active') else 'Stop ثابت'}")
    if kill_switch_active():
        lines.append("🛑 STOP_TRADING نشط")
    return "\n".join(lines)


HELP_TEXT = (
    "🤖 <b>NOVA SCALP AUTO v2</b>\n\n"
    "/menu لوحة التحكم\n/scan فحص فوري\n/status الحالة\n/pause إيقاف الدخولات الجديدة\n/resume استئناف\n"
    "/cancelall إلغاء الأوامر المفتوحة\n/panic إلغاء الأوامر ومحاولة بيع مراكز البوت\n"
    "/coin SOL تحليل فني تفاعلي\n/chart BTC إرسال الشارت\n/prices أسعار السوق\n/ask سؤالك إلى Gemini\n"
    "/kill إنشاء قاطع تداول\n/unkill إزالة القاطع\n\n"
    "الدخول لا يحدث إلا بعد: BTC القائد والعملة فوق EMA200 على 15m و30m، "
    "ثم 4 شموع خضراء + BOS + FVG، وPullback، وMACD سريع وفوليوم مرتفع على 1m."
)


def setup_alert(candidate):
    z = candidate["zone"]
    return (
        f"🧩 <b>تم تسليح Demand Zone — بدون دخول بعد</b>\n\n"
        f"العملة: <b>{symbol_name(candidate['symbol'])}</b> | إطار المنطقة: 5m\n"
        f"• شموع خضراء متتالية: <b>{z['green_count']}</b>\n"
        f"• BOS فوق قمة: <code>{fmt_price(candidate['symbol'], z['prior_swing_high'])}</code>\n"
        f"• Demand Zone: <code>{fmt_price(candidate['symbol'], z['zone_low'])}</code> — <code>{fmt_price(candidate['symbol'], z['zone_high'])}</code>\n"
        f"• Bullish FVG: <code>{fmt_price(candidate['symbol'], z['fvg_low'])}</code> — <code>{fmt_price(candidate['symbol'], z['fvg_high'])}</code>\n"
        f"• Fibonacci: <b>{z.get('fib_ratio') or 'لا يوجد تداخل'}</b> عند <code>{fmt_price(candidate['symbol'], z.get('fib_price'))}</code>\n"
        f"• Macro: ✅ {candidate['macro_reason']}\n\n"
        "سأنتظر Pullback إلى المنطقة ثم MACD سريع صاعد مع Volume Spike قبل Market Buy."
    )


def entry_message(candidate, position=None, ai_text=""):
    symbol = candidate["symbol"]
    z = candidate["zone"]
    signal = candidate["frames"]["1m"]
    setup = candidate["frames"]["5m"]
    position = position or {}
    entry = position.get("entry", candidate["price"])
    stop = position.get("stop", candidate["stop"])
    target = position.get("target", candidate["target"])
    lines = [
        "🚀 <b>تم تنفيذ سكالبينج Spot تلقائياً — BUY</b>",
        f"🔹 {symbol_name(symbol)} | البيئة: {regime_text()} | Score {candidate['score']}/100",
        f"السعر: <code>{fmt_price(symbol, entry)}</code> | الكمية: <code>{position.get('qty', '—')}</code>",
        "",
        "🏗 <b>سبب الدخول:</b>",
        f"• 5m: {z['green_count']} شموع خضراء + BOS + FVG",
        f"• Demand: <code>{fmt_price(symbol, z['zone_low'])}</code>-<code>{fmt_price(symbol, z['zone_high'])}</code>",
        f"• FVG: <code>{fmt_price(symbol, z['fvg_low'])}</code>-<code>{fmt_price(symbol, z['fvg_high'])}</code>",
        f"• Fibonacci: <b>{z.get('fib_ratio') or '—'}</b> عند <code>{fmt_price(symbol, z.get('fib_price'))}</code>",
        f"• Pullback ✅ | 1m MACD Hist <code>{signal['hist']:.8g}</code> | Volume <b>{signal['volume_ratio']:.2f}x</b>",
        f"• Macro ✅ {candidate['macro_reason']}",
        "",
        f"🛑 Stop تحت الطلب: <code>{fmt_price(symbol, stop)}</code> (-{candidate['stop_pct']:.2f}%)",
        f"🎯 هدف Swing High: <code>{fmt_price(symbol, target)}</code> (+{candidate['target_pct']:.2f}%)",
        f"📐 Risk/Reward: <b>1:{candidate['target_pct'] / max(candidate['stop_pct'], 0.0001):.2f}</b>",
        f"🛤 Trailing Delta بعد +{TRAIL_ACTIVATION_PCT:.2f}%: <b>{candidate['trail_pct']:.2f}% ({candidate['trail_bips']} bips)</b>",
        f"📊 5m trend: {setup['trend']} | 1m RSI7: {signal['rsi']:.1f}",
    ]
    if position:
        lines.append(f"حماية Binance: {'OCO ✅' if position.get('protection_type') == 'OCO' else 'STOP بديل ⚠️'}")
    if ai_text:
        lines += ["", "🧠 Gemini:", esc(ai_text)]
    lines.append("\n⚠️ النظام Spot فقط، ولا يرسل Futures أو رافعة.")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 9) الشارت
# ══════════════════════════════════════════════════════════════════════════════


def chart_ready():
    global CHARTS_OK
    if CHARTS_OK is not None:
        return CHARTS_OK
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot  # noqa: F401
        CHARTS_OK = True
    except Exception as exc:
        CHARTS_OK = False
        log(f"matplotlib غير متاحة: {exc}")
    return CHARTS_OK


def make_chart(candidate):
    if not SEND_CHARTS or not chart_ready():
        return None
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    frame = candidate["frames"]["1m"]
    raw = frame["raw"]
    count = min(150, len(raw["c"]))
    start = len(raw["c"]) - count
    o, h, l, c, v = [raw[key][start:] for key in ("o", "h", "l", "c", "v")]
    ef, es, vw = ema(c, EMA_FAST), ema(c, EMA_SLOW), vwap(h, l, c, v, 24)
    rs = rsi(c, RSI_PERIOD)
    ml, ms, hist = macd(c, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    av = sma(v, 20)
    n = len(c)
    bg, panel, grid, txt = "#0d1117", "#121a22", "#27313d", "#d4d8df"
    green, red, blue, yellow, purple, orange = "#0ecb81", "#f6465d", "#4c8bf5", "#f0b90b", "#b17ce8", "#ff9f43"
    fig = plt.figure(figsize=(12, 8.5), dpi=110)
    fig.patch.set_facecolor(bg)
    gs = fig.add_gridspec(4, 1, height_ratios=(3.5, .8, 1.0, 1.0), hspace=.05, left=.07, right=.98, top=.92, bottom=.06)
    axes = [fig.add_subplot(gs[0])]
    axes += [fig.add_subplot(gs[i], sharex=axes[0]) for i in (1, 2, 3)]
    for axis in axes:
        axis.set_facecolor(panel)
        axis.grid(True, color=grid, linewidth=.5)
        axis.tick_params(colors=txt, labelsize=8)
        for spine in axis.spines.values():
            spine.set_color(grid)
    price_ax, vol_ax, rsi_ax, macd_ax = axes
    for i in range(n):
        color = green if c[i] >= o[i] else red
        price_ax.plot([i, i], [l[i], h[i]], color=color, linewidth=.7)
        price_ax.add_patch(Rectangle((i-.35, min(o[i], c[i])), .7, max(abs(c[i]-o[i]), max(c)*.00001), facecolor=color, edgecolor=color))
        vol_ax.bar(i, v[i], color=color, width=.7)
        if hist[i] is not None:
            macd_ax.bar(i, hist[i], color=green if hist[i] >= 0 else red, width=.7)
    for series, color, label in ((ef, yellow, "EMA9"), (es, blue, "EMA21"), (vw, purple, "VWAP")):
        xs = [i for i, x in enumerate(series) if x is not None]
        if len(xs) > 2:
            price_ax.plot(xs, [series[i] for i in xs], color=color, linewidth=1.1, label=label)
    price_ax.axhline(candidate.get("price", c[-1]), color=orange, linestyle=":", linewidth=.9, label="Ask")
    z = candidate.get("zone")
    if z:
        price_ax.axhspan(z["zone_low"], z["zone_high"], color=green, alpha=.08)
        price_ax.axhspan(z["fvg_low"], z["fvg_high"], color=yellow, alpha=.12)
        for ratio, fib_price in z.get("fib", {}).items():
            if ratio in ("0.382", "0.500", "0.618", "0.786"):
                price_ax.axhline(fib_price, color=orange, linestyle="--", linewidth=.45, alpha=.55)
    if candidate.get("stop"):
        price_ax.axhline(candidate["stop"], color=red, linestyle="--", linewidth=.9, label="Stop")
    if candidate.get("target"):
        price_ax.axhline(candidate["target"], color=green, linestyle="--", linewidth=.9, label="Target")
    price_ax.set_title(f"{symbol_name(candidate['symbol'])} | 1m Pullback Trigger | Score {candidate.get('score', 0)}/100", color=txt, fontsize=11, fontweight="bold", loc="left")
    price_ax.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=txt, ncol=5)
    xs = [i for i, x in enumerate(av) if x is not None]
    if xs:
        vol_ax.plot(xs, [av[i] for i in xs], color=yellow, linewidth=.8)
    vol_ax.set_ylabel("VOL", color=txt, fontsize=8)
    rx = [i for i, x in enumerate(rs) if x is not None]
    rsi_ax.plot(rx, [rs[i] for i in rx], color=purple, linewidth=1.1)
    rsi_ax.axhline(70, color=red, linestyle="--", linewidth=.6)
    rsi_ax.axhline(30, color=green, linestyle="--", linewidth=.6)
    rsi_ax.set_ylim(0, 100)
    rsi_ax.set_ylabel("RSI7", color=txt, fontsize=8)
    mx = [i for i, x in enumerate(ml) if x is not None]
    macd_ax.plot(mx, [ml[i] for i in mx], color=blue, linewidth=.9, label="MACD")
    macd_ax.plot(mx, [ms[i] for i in mx], color=orange, linewidth=.9, label="Signal")
    macd_ax.axhline(0, color=txt, linewidth=.5)
    macd_ax.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=txt)
    step = max(1, n // 6)
    ticks = list(range(0, n, step))
    labels = []
    for i in ticks:
        try:
            labels.append(datetime.fromtimestamp(raw["t"][start+i] / 1000).strftime("%H:%M:%S"))
        except (ValueError, OSError):
            labels.append("")
    macd_ax.set_xticks(ticks)
    macd_ax.set_xticklabels(labels, color=txt, fontsize=8)
    path = os.path.join(CHART_DIR, f"{candidate['symbol'].replace('USDT', '')}_{int(time.time())}.png")
    try:
        ensure_dirs()
        fig.savefig(path, facecolor=bg, bbox_inches="tight")
    finally:
        plt.close(fig)
    return path


# ══════════════════════════════════════════════════════════════════════════════
# 10) أوامر Spot: دخول + OCO ثابت + OCO متحرك
# ══════════════════════════════════════════════════════════════════════════════


def live_execution_allowed():
    if DRY_RUN or not AUTO_TRADE or not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return False
    if BINANCE_ENV == "live" and LIVE_CONFIRM != "I_UNDERSTAND_SPOT_RISK":
        return False
    return True


def reset_metrics_if_needed():
    reset_metrics()
    return STATE["metrics"]


def circuit_allows_entry():
    metrics = reset_metrics_if_needed()
    if kill_switch_active():
        return False, "STOP_TRADING نشط"
    if STATE.get("paused"):
        return False, "الفحص متوقف"
    if MAX_DAILY_TRADES > 0 and metrics.get("trades", 0) >= MAX_DAILY_TRADES:
        return False, "حد الصفقات اليومية"
    if metrics.get("realized_pnl", 0.0) <= -abs(MAX_DAILY_LOSS_USD):
        return False, "حد الخسارة اليومية"
    if metrics.get("consecutive_losses", 0) >= MAX_CONSECUTIVE_LOSSES:
        return False, "قاطع الخسائر المتتالية"
    if MAX_POSITIONS > 0 and len(STATE.get("positions", {})) >= MAX_POSITIONS:
        return False, "الحد الأقصى للمراكز"
    return True, "OK"


def parse_fill(order, fallback_price):
    qty = D(order.get("executedQty", "0"))
    quote = D(order.get("cummulativeQuoteQty", "0"))
    average = quote / qty if qty > 0 and quote > 0 else D(fallback_price)
    return qty, quote, average


def place_initial_oco(symbol, qty, entry, stop_price, target_price):
    rule = SYMBOL_RULES[symbol]
    quantity = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), rule["step"])
    stop = round_price(stop_price, rule["tick"], "down")
    stop_limit = round_price(stop * (Decimal("1") - D(LIMIT_SLIPPAGE_PCT) / Decimal("100")), rule["tick"], "down")
    target_trigger = round_price(target_price, rule["tick"], "up")
    target_limit = round_price(target_trigger * (Decimal("1") - D("0.0003")), rule["tick"], "down")
    if quantity < rule["min_qty"] or quantity * D(entry) < rule["min_notional"]:
        raise BinanceError("الكمية لا تحقق فلاتر Binance")
    params = {
        "symbol": symbol, "side": "SELL", "quantity": dec_str(quantity),
        "aboveType": "TAKE_PROFIT_LIMIT", "abovePrice": dec_str(target_limit),
        "aboveStopPrice": dec_str(target_trigger), "aboveTimeInForce": "GTC",
        "belowType": "STOP_LOSS_LIMIT", "belowPrice": dec_str(stop_limit),
        "belowStopPrice": dec_str(stop), "belowTimeInForce": "GTC",
        "listClientOrderId": make_client_id("oco"), "newOrderRespType": "RESULT",
    }
    try:
        result = CLIENT.new_oco(params)
        return {"type": "OCO", "order_list_id": result.get("orderListId"), "orders": result.get("orders", []), "qty": quantity, "stop": stop, "target": target_trigger}
    except BinanceError as oco_error:
        log(f"OCO الثابت فشل لـ {symbol}: {oco_error}")
        fallback = CLIENT.new_order({
            "symbol": symbol, "side": "SELL", "type": "STOP_LOSS_LIMIT", "timeInForce": "GTC",
            "quantity": dec_str(quantity), "price": dec_str(stop_limit), "stopPrice": dec_str(stop),
            "newClientOrderId": make_client_id("stp"), "newOrderRespType": "RESULT",
        })
        return {"type": "STOP", "order_list_id": None, "orders": [{"orderId": fallback.get("orderId")}], "stop_order_id": fallback.get("orderId"), "qty": quantity, "stop": stop, "target": target_trigger}


def place_trailing_oco(symbol, qty, target_price, trail_bips, reference_price):
    rule = SYMBOL_RULES[symbol]
    quantity = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), rule["step"])
    target_trigger = round_price(target_price, rule["tick"], "up")
    target_limit = round_price(target_trigger * (Decimal("1") - D("0.0003")), rule["tick"], "down")
    bips = int(clamp(int(trail_bips), rule.get("min_trailing_below", 10), rule.get("max_trailing_below", 2000)))
    if quantity < rule["min_qty"]:
        raise BinanceError("الكمية المتبقية لا تحقق minQty")
    trail_fraction = D(bips) / Decimal("10000")
    reference = D(reference_price)
    below_limit = round_price(reference * (Decimal("1") - trail_fraction * Decimal("1.5")), rule["tick"], "down")
    params = {
        "symbol": symbol, "side": "SELL", "quantity": dec_str(quantity),
        "aboveType": "TAKE_PROFIT_LIMIT", "abovePrice": dec_str(target_limit),
        "aboveStopPrice": dec_str(target_trigger), "aboveTimeInForce": "GTC",
        "belowType": "STOP_LOSS_LIMIT", "belowPrice": dec_str(below_limit),
        "belowTimeInForce": "GTC", "belowTrailingDelta": bips,
        "listClientOrderId": make_client_id("trc"), "newOrderRespType": "RESULT",
    }
    result = CLIENT.new_oco(params)
    return {"type": "OCO", "order_list_id": result.get("orderListId"), "orders": result.get("orders", []), "qty": quantity, "trail_bips": bips, "target": target_trigger}


def emergency_sell(symbol, qty, reason):
    try:
        rule = SYMBOL_RULES[symbol]
        quantity = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), rule["step"])
        if quantity < rule["min_qty"]:
            return None
        result = CLIENT.new_order({"symbol": symbol, "side": "SELL", "type": "MARKET", "quantity": dec_str(quantity), "newClientOrderId": make_client_id("pan"), "newOrderRespType": "FULL"})
        log(f"خروج طارئ {symbol}: {reason}")
        return result
    except BinanceError as exc:
        log(f"فشل الخروج الطارئ {symbol}: {exc}")
        send_message(f"🆘 <b>فشل الخروج الطارئ {symbol_name(symbol)}</b>\n{esc(exc)}")
        return None


def execute_entry(candidate, ai_text=""):
    symbol = candidate["symbol"]
    if symbol in STATE.get("positions", {}):
        return False
    allowed, reason = circuit_allows_entry()
    if not allowed:
        log(f"تخطي {symbol}: {reason}")
        return False
    if not live_execution_allowed():
        send_message("🟡 <b>Trigger مؤكد دون تنفيذ</b>\n\n" + entry_message(candidate, ai_text=ai_text))
        STATE["cooldowns"][symbol] = time.time()
        return False
    rule = SYMBOL_RULES.get(symbol)
    if not rule or rule.get("status") != "TRADING":
        return False
    entry_qty = Decimal("0")
    try:
        account = CLIENT.account()
        quote_asset = rule.get("quote", "USDT")
        free_quote = CLIENT.free_balance(quote_asset, account)
        quote = D(min(TRADE_QUOTE_USD, MAX_POSITION_USD))
        if free_quote < quote * D("1.01") or quote < rule["min_notional"]:
            log(f"رصيد/قيمة غير كافية لـ {symbol}")
            return False
        order = CLIENT.new_order({"symbol": symbol, "side": "BUY", "type": "MARKET", "quoteOrderQty": dec_str(quote), "newClientOrderId": make_client_id("ent"), "newOrderRespType": "FULL"})
        entry_qty, quote_filled, entry = parse_fill(order, candidate["price"])
        if entry_qty <= 0:
            raise BinanceError("أمر الدخول لم ينفذ")
        protection = place_initial_oco(symbol, entry_qty, entry, candidate["stop"], candidate["target"])
        position = {
            "symbol": symbol, "entry": float(entry), "qty": dec_str(protection["qty"]), "quote_qty": float(quote_filled or quote),
            "stop": float(protection["stop"]), "target": float(protection["target"]), "trail_bips": int(candidate["trail_bips"]),
            "entry_order_id": order.get("orderId"), "order_list_id": protection.get("order_list_id"),
            "order_ids": [x.get("orderId") for x in protection.get("orders", []) if x.get("orderId") is not None],
            "stop_order_id": protection.get("stop_order_id"), "protection_type": protection.get("type"),
            "trailing_active": False, "opened_at": time.time(), "score": candidate["score"],
            "stop_pct": candidate["stop_pct"], "target_pct": candidate["target_pct"], "zone": candidate["zone"],
            "last_check": 0.0, "protection_failures": 0,
        }
        with STATE_LOCK:
            STATE["positions"][symbol] = position
            STATE["setups"].pop(symbol, None)
            STATE["metrics"]["trades"] += 1
            STATE["cooldowns"][symbol] = time.time()
            STATE["last_signals"] = (STATE.get("last_signals") or [])[-9:] + [{"symbol": symbol, "score": candidate["score"], "time": time.time()}]
        save_state()
        send_message(entry_message(candidate, position, ai_text), main_keyboard())
        path = make_chart(candidate)
        if path:
            send_photo(path, f"{symbol_name(symbol)} | 1m BUY | OCO {protection['type']} | trail {candidate['trail_bips']} bips")
        log(f"دخول تلقائي {symbol}: entry={entry} qty={position['qty']} protection={protection['type']}")
        return True
    except BinanceError as exc:
        if entry_qty > 0 and live_execution_allowed():
            emergency_sell(symbol, entry_qty, "فشل وضع حماية الدخول")
        log(f"فشل دخول {symbol}: {exc}")
        send_message(f"⚠️ <b>فشل دخول {symbol_name(symbol)}</b>\n{esc(exc)}")
        return False
    except Exception as exc:
        if entry_qty > 0 and live_execution_allowed():
            emergency_sell(symbol, entry_qty, "خطأ غير متوقع بعد الدخول")
        log(f"خطأ دخول {symbol}: {exc}\n{traceback.format_exc()[-400:]}")
        return False


def order_status(position):
    symbol = position["symbol"]
    orders = []
    for order_id in position.get("order_ids", []):
        try:
            orders.append(CLIENT.get_order(symbol, order_id))
        except BinanceError as exc:
            log(f"تعذر جلب أمر {order_id}: {exc}")
    if position.get("stop_order_id") and position.get("stop_order_id") not in position.get("order_ids", []):
        try:
            orders.append(CLIENT.get_order(symbol, position["stop_order_id"]))
        except BinanceError as exc:
            log(f"تعذر جلب stop لـ {symbol}: {exc}")
    for order in orders:
        if order.get("status") == "FILLED" and D(order.get("executedQty", "0")) > 0:
            return order
    return None


def finalize_position(symbol, position, exit_order, reason):
    exit_qty, exit_quote, exit_average = parse_fill(exit_order or {}, position.get("entry", 0))
    entry = float(position.get("entry", 0))
    qty = float(position.get("qty", 0))
    exit_price = float(exit_average)
    pnl = (exit_price - entry) * min(qty, float(exit_qty) if exit_qty else qty)
    with STATE_LOCK:
        metrics = STATE["metrics"]
        metrics["realized_pnl"] += pnl
        if pnl >= 0:
            metrics["wins"] += 1
            metrics["consecutive_losses"] = 0
        else:
            metrics["losses"] += 1
            metrics["consecutive_losses"] += 1
        STATE["positions"].pop(symbol, None)
        STATE["cooldowns"][symbol] = time.time()
    record_trade([datetime.now(timezone.utc).isoformat(), symbol, entry, exit_price, qty, round(pnl, 8), reason, position.get("score", 0), BINANCE_ENV])
    save_state()
    send_message(f"{'✅' if pnl >= 0 else '🔴'} <b>إغلاق {symbol_name(symbol)}</b>\nالسبب: {esc(reason)}\nالدخول: <code>{fmt_price(symbol, entry)}</code> | الخروج: <code>{fmt_price(symbol, exit_price)}</code>\nالنتيجة التقريبية: <b>{pnl:+.6f}$</b>")


def activate_trailing(symbol, position, current_price):
    if position.get("trailing_active"):
        return True
    try:
        # إلغاء الحماية الثابتة قبل تركيب الحماية المتحركة الجديدة.
        if position.get("order_list_id"):
            CLIENT.cancel_oco(symbol, position["order_list_id"])
        elif position.get("stop_order_id"):
            CLIENT.cancel_order(symbol, position["stop_order_id"])
        protection = place_trailing_oco(symbol, D(position["qty"]), position["target"], position["trail_bips"], current_price)
        position.update({
            "order_list_id": protection.get("order_list_id"),
            "order_ids": [x.get("orderId") for x in protection.get("orders", []) if x.get("orderId") is not None],
            "stop_order_id": None, "protection_type": "OCO", "trailing_active": True,
        })
        save_state()
        send_message(f"🛤 <b>تم تفعيل الوقف المتحرك — {symbol_name(symbol)}</b>\nالسعر: <code>{fmt_price(symbol, current_price)}</code> تجاوز +{TRAIL_ACTIVATION_PCT:.2f}%\nTrailing Delta: <b>{position['trail_bips']} bips</b>\nتم استبدال الحماية الثابتة بحماية متحركة على Binance.")
        return True
    except BinanceError as exc:
        log(f"فشل تفعيل trailing لـ {symbol}: {exc}")
        exit_order = emergency_sell(symbol, D(position["qty"]), "فشل تركيب الوقف المتحرك")
        if exit_order:
            finalize_position(symbol, position, exit_order, "خروج طارئ بعد فشل trailing")
        return False


def monitor_position(symbol, position):
    now = time.time()
    if now - position.get("last_check", 0.0) < MANAGE_EVERY:
        return
    position["last_check"] = now
    filled = order_status(position)
    if filled:
        finalize_position(symbol, position, filled, "OCO/STOP تم تنفيذه على Binance")
        return
    try:
        book = CLIENT.book_ticker(symbol)
        current = (book["bid"] + book["ask"]) / 2.0
    except BinanceError:
        return
    entry = float(position["entry"])
    if not position.get("trailing_active") and current >= entry * (1.0 + TRAIL_ACTIVATION_PCT / 100.0):
        if activate_trailing(symbol, position, current):
            return
    if position.get("protection_type") == "STOP" and current >= float(position["target"]):
        try:
            CLIENT.cancel_order(symbol, position.get("stop_order_id"))
        except BinanceError:
            pass
        exit_order = emergency_sell(symbol, D(position["qty"]), "الوصول إلى هدف Swing High")
        if exit_order:
            finalize_position(symbol, position, exit_order, "هدف يدوي بعد STOP البديل")
    if position.get("order_list_id") and not position.get("trailing_active"):
        try:
            listing = CLIENT.order_list(position["order_list_id"])
            if listing.get("listOrderStatus") not in ("EXECUTING", "EXEC_STARTED"):
                position["protection_failures"] = position.get("protection_failures", 0) + 1
                if position["protection_failures"] >= 2:
                    exit_order = emergency_sell(symbol, D(position["qty"]), "اختفاء OCO الثابت")
                    if exit_order:
                        finalize_position(symbol, position, exit_order, "خروج طارئ بعد اختفاء OCO")
        except BinanceError as exc:
            log(f"تعذر فحص OCO {symbol}: {exc}")
    save_state()


def manage_positions():
    for symbol, position in list(STATE.get("positions", {}).items()):
        try:
            monitor_position(symbol, position)
        except Exception as exc:
            log(f"خطأ إدارة {symbol}: {exc}")


def cancel_all_orders():
    for symbol in list(SYMBOL_RULES):
        try:
            CLIENT.cancel_all(symbol)
        except BinanceError as exc:
            log(f"تعذر إلغاء {symbol}: {exc}")


def panic_close_all():
    cancel_all_orders()
    for symbol, position in list(STATE.get("positions", {}).items()):
        order = emergency_sell(symbol, D(position.get("qty", 0)), "PANIC")
        if order:
            finalize_position(symbol, position, order, "PANIC")


# ══════════════════════════════════════════════════════════════════════════════
# 11) إدارة الإعدادات والفحص
# ══════════════════════════════════════════════════════════════════════════════


def reserve_entry(symbol):
    """حجز ذري يمنع دخولاً مكرراً عند ظهور عدة فرص في نفس دورة الفحص."""
    with ENTRY_LOCK:
        if symbol in ENTRY_RESERVATIONS or symbol in STATE.get("positions", {}):
            return False
        if MAX_POSITIONS > 0 and len(STATE.get("positions", {})) + len(ENTRY_RESERVATIONS) >= MAX_POSITIONS:
            return False
        allowed, _ = circuit_allows_entry()
        if not allowed:
            return False
        ENTRY_RESERVATIONS.add(symbol)
        return True


def release_entry(symbol):
    with ENTRY_LOCK:
        ENTRY_RESERVATIONS.discard(symbol)


def setup_allowed(symbol, zone):
    last = STATE.get("cooldowns", {}).get(symbol, 0.0)
    if time.time() - last < SYMBOL_COOLDOWN:
        return False
    existing = STATE.get("setups", {}).get(symbol)
    if existing and existing.get("zone_id") == zone["id"]:
        return True
    return True


def upsert_setup(candidate):
    symbol = candidate["symbol"]
    zone = candidate["zone"]
    existing = STATE.get("setups", {}).get(symbol)
    if existing and existing.get("zone_id") == zone["id"]:
        existing["last_seen"] = time.time()
        return existing
    if existing and time.time() < existing.get("expires_at", 0) and existing.get("zone_id") != zone["id"]:
        # أحدث منطقة لها الأولوية، لكن لا نكرر التنبيه كل دورة.
        pass
    setup = {
        "symbol": symbol, "zone_id": zone["id"], "zone_low": zone["zone_low"], "zone_high": zone["zone_high"],
        "fvg_low": zone["fvg_low"], "fvg_high": zone["fvg_high"], "target_high": zone["target_high"],
        "prior_swing_high": zone["prior_swing_high"], "green_count": zone["green_count"],
        "fib": zone.get("fib", {}), "fib_ratio": zone.get("fib_ratio"), "fib_price": zone.get("fib_price"),
        "created_at": time.time(), "expires_at": time.time() + ZONE_MAX_AGE_CANDLES * 300,
        "last_seen": time.time(), "alerted": False,
    }
    STATE["setups"][symbol] = setup
    if not setup["alerted"]:
        send_message(setup_alert(candidate), main_keyboard())
        setup["alerted"] = True
    save_state()
    return setup


def setup_as_candidate(candidate, setup):
    z = candidate["zone"]
    candidate["stop"] = z["zone_low"] * (1.0 - ZONE_STOP_BUFFER_PCT / 100.0)
    candidate["target"] = z["target_high"] * (1.0 - 0.03 / 100.0)
    candidate["price"] = candidate.get("price") or candidate["frames"]["1m"]["close"]
    risk = candidate["price"] - candidate["stop"]
    reward = candidate["target"] - candidate["price"]
    if risk <= 0 or reward <= 0 or reward / risk < TAKE_RR_MIN:
        return None
    signal = candidate["frames"]["1m"]
    trail_pct = clamp(max(signal["atr_pct"] * TRAIL_ATR_MULT, 0.30), 0.30, 2.50)
    rule = SYMBOL_RULES.get(candidate["symbol"], {})
    bips = int(clamp(round(trail_pct * 100), rule.get("min_trailing_below", 10), rule.get("max_trailing_below", 2000)))
    candidate.update({"stop_pct": risk / candidate["price"] * 100, "target_pct": reward / candidate["price"] * 100, "trail_pct": bips / 100, "trail_bips": bips})
    candidate["score"] = max(candidate.get("score", 0), MIN_SCORE)
    return candidate


def process_candidate(candidate):
    symbol = candidate["symbol"]
    if not setup_allowed(symbol, candidate["zone"]) or not reserve_entry(symbol):
        return False
    try:
        news_text_value = ""
        if AI_GATE_ENABLED:
            news, news_ok = fetch_news(symbol)
            if REQUIRE_NEWS and not news_ok:
                log(f"حجب {symbol}: الأخبار غير متاحة")
                return False
            approved, news_text_value = ai_gate(candidate, news)
            if not approved:
                log(f"حجب {symbol}: {news_text_value}")
                STATE["cooldowns"][symbol] = time.time()
                save_state()
                return False
        return execute_entry(candidate, news_text_value)
    finally:
        release_entry(symbol)


def run_scan(force=False):
    global LAST_STATUS_MESSAGE
    if not SCAN_LOCK.acquire(blocking=False):
        log("تم تخطي دورة الفحص؛ دورة أخرى تعمل")
        return None
    started = time.time()
    if not SYMBOL_RULES:
        log("لا توجد قواعد Binance محمّلة؛ لا يمكن بدء الفحص")
        if force:
            send_message("⚠️ لا توجد قواعد Binance محمّلة؛ تحقق من الوصول إلى Binance Testnet.")
        SCAN_LOCK.release()
        return None
    report = force or started - LAST_STATUS_MESSAGE >= SCAN_STATUS_EVERY
    if report:
        LAST_STATUS_MESSAGE = started
        send_message(f"🔎 <b>بدأت دورة فحص جديدة</b>\n{len(SYMBOLS)} زوجاً | Macro 15m/30m | Setup 5m | Trigger 1m")
    try:
        allowed, reason = circuit_allows_entry()
        if not allowed:
            log(f"الفحص مستمر لكن الدخول مغلق: {reason}")
        leader_frames = {}
        for leader in LEADERS:
            leader_frames[leader] = fetch_frames(leader)
        if any(value is None for value in leader_frames.values()):
            log("فشل تحميل فلتر BTC القائد")
            if report:
                send_message("⚠️ فشل تحميل بيانات BTC القائد؛ سأعيد المحاولة تلقائياً.")
            return None
        tickers = CLIENT.ticker_24h(SYMBOLS)
        candidates = []
        for index, symbol in enumerate(SYMBOLS, 1):
            if symbol not in SYMBOL_RULES or SYMBOL_RULES[symbol].get("status") != "TRADING":
                continue
            if symbol in STATE.get("positions", {}) or symbol in ENTRY_RESERVATIONS:
                continue
            try:
                if force:
                    log(f"فحص {index}/{len(SYMBOLS)}: {symbol}")
                frames = fetch_frames(symbol)
                if not frames:
                    continue
                quote_volume = tickers.get(symbol, {}).get("quote_volume", 0.0)
                candidate = build_candidate(symbol, frames, leader_frames, quote_volume)
                if not candidate:
                    continue
                setup = upsert_setup(candidate)
                if not candidate.get("confirmed"):
                    continue
                prepared = setup_as_candidate(candidate, setup)
                if prepared:
                    candidates.append(prepared)
                time.sleep(0.10)
            except BinanceError as exc:
                log(f"تحليل {symbol}: {exc}")
            except Exception as exc:
                log(f"خطأ {symbol}: {exc}")
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        if not STATE.get("paused"):
            limit = MAX_ENTRIES_PER_SCAN if MAX_ENTRIES_PER_SCAN > 0 else len(candidates)
            for candidate in candidates[:limit]:
                threading.Thread(target=process_candidate, args=(candidate,), daemon=True).start()
        save_state()
        log(f"انتهى الفحص؛ مناطق مرصودة/مرشحو دخول: {len(candidates)}")
        if report:
            if candidates:
                preview = "، ".join(f"{x['symbol']} {x['score']}" for x in candidates[:8])
                send_message(f"✅ <b>انتهى الفحص</b>\nمرشحو Pullback المؤكد: {len(candidates)}\n{esc(preview)}")
            else:
                send_message("✅ <b>انتهى الفحص</b>\nلا توجد فرصة مكتملة الآن؛ البوت يعمل وسيعيد الفحص تلقائياً.")
        return candidates
    except BinanceError as exc:
        log(f"فشل الفحص: {exc}")
        if report:
            send_message(f"⚠️ تعذر إكمال الفحص: {esc(exc)}")
        return None
    except Exception as exc:
        log(f"خطأ فحص عام: {exc}\n{traceback.format_exc()[-500:]}")
        if report:
            send_message("⚠️ حدث خطأ في دورة الفحص؛ سأعيد المحاولة.")
        return None
    finally:
        SCAN_LOCK.release()


# ══════════════════════════════════════════════════════════════════════════════
# 12) تقارير تفاعلية وTelegram polling
# ══════════════════════════════════════════════════════════════════════════════


def normalize_symbol(value):
    raw = value.strip().upper().replace("/", "")
    symbol = raw if raw.endswith("USDT") else raw + "USDT"
    return symbol if symbol in SYMBOLS else None


def prices_report():
    try:
        data = CLIENT.ticker_24h(SYMBOLS)
    except BinanceError as exc:
        return f"⚠️ تعذر جلب الأسعار: {esc(exc)}"
    lines = ["💲 <b>أسعار السوق</b>"]
    for symbol in SYMBOLS:
        row = data.get(symbol)
        if not row:
            continue
        icon = "🟢" if row["change"] >= 0 else "🔴"
        lines.append(f"{icon} {symbol_name(symbol)}: <code>{fmt_price(symbol, row['price'])}</code> {pct(row['change'])} | {row['quote_volume'] / 1_000_000:.2f}M$")
    return "\n".join(lines)


def manual_analysis(symbol, chart_only=False, chat_id=None):
    try:
        leaders = {leader: fetch_frames(leader) for leader in LEADERS}
        frames = fetch_frames(symbol)
        if not frames or any(value is None for value in leaders.values()):
            send_message(f"⚠️ بيانات {symbol_name(symbol)} أو فلاتر القادة غير مكتملة.", chat_id=chat_id)
            return
        candidate = None
        try:
            ticker_data = CLIENT.ticker_24h([symbol]).get(symbol, {})
            candidate = build_candidate(symbol, frames, leaders, ticker_data.get("quote_volume", 0.0))
        except BinanceError:
            pass
        if not candidate or not candidate.get("confirmed"):
            macro_ok, macro_reason = macro_trend_ok(frames, leaders)
            zone = detect_demand_zone(frames["5m"])
            candidate = {
                "symbol": symbol, "frames": frames, "leader_frames": leaders,
                "zone": zone, "price": frames["1m"]["close"], "score": 0,
                "macro_reason": macro_reason if macro_ok else macro_reason,
            }
        if not chart_only:
            f1, f5, f15, f30 = frames["1m"], frames["5m"], frames["15m"], frames["30m"]
            macro_ok, macro_reason = macro_trend_ok(frames, leaders)
            z = detect_demand_zone(f5)
            lines = [
                f"🔍 <b>تحليل {symbol_name(symbol)}</b>",
                f"السعر: <code>{fmt_price(symbol, frames['1m']['close'])}</code>",
                f"Macro: {'✅' if macro_ok else '⛔'} {macro_reason}",
                f"15m: {f15['trend']} | السعر/EMA200: {f15['close']:.8g}/{f15['ema200'] or 0:.8g}",
                f"30m: {f30['trend']} | السعر/EMA200: {f30['close']:.8g}/{f30['ema200'] or 0:.8g}",
                f"1m: RSI {f1['rsi']:.1f} | MACD Hist {f1['hist']:.8g} | Volume {f1['volume_ratio']:.2f}x",
                f"5m: {f5['trend']} | Demand: {'✅' if z else '—'}",
            ]
            if z:
                lines += [
                    f"Demand: {fmt_price(symbol, z['zone_low'])}-{fmt_price(symbol, z['zone_high'])}",
                    f"FVG: {fmt_price(symbol, z['fvg_low'])}-{fmt_price(symbol, z['fvg_high'])} | BOS: ✅",
                    f"Fibonacci: {z.get('fib_ratio') or '—'} عند {fmt_price(symbol, z.get('fib_price'))}",
                ]
            send_message("\n".join(lines), main_keyboard(), chat_id)
        path = make_chart(candidate)
        if path:
            send_photo(path, f"{symbol_name(symbol)} | تحليل 1m/5m/15m/30m", chat_id)
        elif chart_only:
            send_message("⚠️ matplotlib غير متاح؛ ثبّته عبر pip install matplotlib", chat_id=chat_id)
    except Exception as exc:
        log(f"manual {symbol}: {exc}\n{traceback.format_exc()[-300:]}")
        send_message("⚠️ فشل التحليل التفاعلي.", chat_id=chat_id)


def ask_gemini(question, chat_id=None):
    if not GEMINI_API_KEY:
        send_message("⚠️ GEMINI_API_KEY غير مضبوط.", chat_id=chat_id)
        return
    try:
        btc = {leader: fetch_frames(leader) for leader in LEADERS}
        context = []
        for leader, frames in btc.items():
            if frames and frames.get("15m") and frames.get("30m"):
                context.append(f"{leader}: 15m close/EMA200={frames['15m']['close']:.8g}/{frames['15m']['ema200'] or 0:.8g}, 30m close/EMA200={frames['30m']['close']:.8g}/{frames['30m']['ema200'] or 0:.8g}")
        prompt = f"أنت محلل تداول Spot صارم. لا تضمن الربح ولا تنفذ أوامر. سياق السوق: {' | '.join(context)}\nسؤال المستخدم: {question}"
        answer, reason = gemini_call(prompt)
        send_message("🧠 <b>Gemini:</b>\n" + esc(answer or reason), chat_id=chat_id)
    except Exception as exc:
        send_message(f"⚠️ تعذر سؤال Gemini: {esc(exc)}", chat_id=chat_id)


def handle_callback(update):
    callback = update.get("callback_query", {})
    message = callback.get("message", {})
    chat = str(message.get("chat", {}).get("id", ""))
    if chat != str(TELEGRAM_CHAT_ID):
        tg_call("answerCallbackQuery", {"callback_query_id": callback.get("id", ""), "text": "غير مصرح"}, retries=1)
        return
    data = callback.get("data", "")
    tg_call("answerCallbackQuery", {"callback_query_id": callback.get("id", "")}, retries=1)
    if data == "status":
        send_message(status_text(), main_keyboard(), chat)
    elif data == "scan":
        threading.Thread(target=lambda: run_scan(force=True), daemon=True).start()
    elif data == "pause":
        STATE["paused"] = True
        save_state()
        send_message("⏸ تم إيقاف الدخولات الجديدة؛ تستمر إدارة المراكز.", main_keyboard(), chat)
    elif data == "resume":
        STATE["paused"] = False
        save_state()
        send_message("▶ تم استئناف الدخولات.", main_keyboard(), chat)
    elif data == "cancelall":
        threading.Thread(target=cancel_all_orders, daemon=True).start()
        send_message("🧯 جارٍ إلغاء الأوامر المفتوحة.", main_keyboard(), chat)
    elif data == "help":
        send_message(HELP_TEXT, main_keyboard(), chat)


def handle_command(text, chat):
    command, _, argument = text.partition(" ")
    command = command.split("@", 1)[0].lower()
    if command in ("/start", "/menu"):
        send_message("🎛️ <b>NOVA SCALP AUTO v2</b>\nاختر عملية:", main_keyboard(), chat)
    elif command == "/help":
        send_message(HELP_TEXT, main_keyboard(), chat)
    elif command == "/status":
        send_message(status_text(), main_keyboard(), chat)
    elif command == "/scan":
        threading.Thread(target=lambda: run_scan(force=True), daemon=True).start()
    elif command == "/pause":
        STATE["paused"] = True
        save_state()
        send_message("⏸ تم إيقاف الدخولات الجديدة.", main_keyboard(), chat)
    elif command == "/resume":
        STATE["paused"] = False
        save_state()
        send_message("▶ تم استئناف الدخولات.", main_keyboard(), chat)
    elif command == "/cancelall":
        threading.Thread(target=cancel_all_orders, daemon=True).start()
        send_message("🧯 جارٍ إلغاء الأوامر المفتوحة.", main_keyboard(), chat)
    elif command in ("/coin", "/chart"):
        symbol = normalize_symbol(argument)
        if not symbol:
            send_message("اكتب مثلاً: /coin SOL أو /chart BTC", chat_id=chat)
            return
        threading.Thread(target=manual_analysis, args=(symbol, command == "/chart", chat), daemon=True).start()
    elif command == "/prices":
        threading.Thread(target=lambda: send_message(prices_report(), main_keyboard(), chat), daemon=True).start()
    elif command == "/ask":
        if not argument:
            send_message("اكتب مثلاً: /ask هل BTC فوق EMA200؟", chat_id=chat)
            return
        threading.Thread(target=ask_gemini, args=(argument, chat), daemon=True).start()
    elif command == "/panic":
        threading.Thread(target=panic_close_all, daemon=True).start()
        send_message("🆘 بدأ PANIC.", main_keyboard(), chat)
    elif command == "/kill":
        ensure_dirs()
        with open(KILL_SWITCH_FILE, "w", encoding="utf-8") as handle:
            handle.write(datetime.now(timezone.utc).isoformat())
        send_message("🛑 تم تفعيل STOP_TRADING.", main_keyboard(), chat)
    elif command == "/unkill":
        try:
            os.remove(KILL_SWITCH_FILE)
        except OSError:
            pass
        send_message("✅ أُزيل STOP_TRADING.", main_keyboard(), chat)
    else:
        send_message("أمر غير معروف؛ استخدم /help", main_keyboard(), chat)


def poll_telegram_once():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    updates = tg_call("getUpdates", {"offset": STATE.get("offset", 0), "timeout": TELEGRAM_POLL_TIMEOUT, "allowed_updates": ["message", "callback_query"]}, retries=1)
    if not updates:
        return
    for update in updates:
        STATE["offset"] = max(STATE.get("offset", 0), update.get("update_id", 0) + 1)
        if "callback_query" in update:
            handle_callback(update)
            continue
        message = update.get("message", {})
        chat = str(message.get("chat", {}).get("id", ""))
        if chat != str(TELEGRAM_CHAT_ID):
            continue
        text = (message.get("text") or "").strip()
        if text.startswith("/"):
            handle_command(text, chat)
        else:
            symbol = normalize_symbol(text)
            if symbol:
                threading.Thread(target=manual_analysis, args=(symbol, False, chat), daemon=True).start()
            else:
                threading.Thread(target=ask_gemini, args=(text, chat), daemon=True).start()
    save_state()


def telegram_loop():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log("Telegram غير مفعّل")
        return
    while True:
        try:
            poll_telegram_once()
        except Exception as exc:
            log(f"Telegram: {exc}")
            time.sleep(5)


# ══════════════════════════════════════════════════════════════════════════════
# 13) الاختبار الذاتي والتشغيل
# ══════════════════════════════════════════════════════════════════════════════


def selftest():
    print("NOVA SCALP AUTO v2 SELFTEST")
    random.seed(22)
    n = 320
    closes, highs, lows, opens, volumes = [], [], [], [], []
    price = 100.0
    for _ in range(n):
        price += random.gauss(0.04, 0.35)
        price = max(20.0, price)
        op = price
        cl = max(20.0, price + random.gauss(0.04, 0.20))
        hi = max(op, cl) + abs(random.gauss(0.10, 0.05))
        lo = min(op, cl) - abs(random.gauss(0.10, 0.05))
        opens.append(op); closes.append(cl); highs.append(hi); lows.append(lo); volumes.append(abs(random.gauss(1000, 100)))
        price = cl
    results = []

    def check(name, condition):
        results.append(bool(condition))
        print(("✅ " if condition else "❌ ") + name)

    check("EMA", last_valid(ema(closes, 21)) is not None)
    ml, ms, hist = macd(closes, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    check("MACD", last_valid(ml) is not None and last_valid(ms) is not None and last_valid(hist) is not None)
    check("RSI", 0 <= last_valid(rsi(closes, RSI_PERIOD), 50) <= 100)
    check("ATR", last_valid(atr(highs, lows, closes, ATR_PERIOD)) > 0)
    check("VWAP", last_valid(vwap(highs, lows, closes, volumes, 24)) > 0)
    timestamps = [int(time.time() * 1000) - (n - i) * 60_000 for i in range(n)]
    raw = {"t": timestamps, "o": opens, "h": highs, "l": lows, "c": closes, "v": volumes, "qv": [x * 100 for x in volumes], "live": closes[-1]}
    frame = analyze_frame(raw, "1m")
    check("تحليل فريم", frame is not None and frame["quality"]["ok"])

    # اختبار صريح لمنطق الأربع شموع + BOS + FVG.
    m = 100
    oo = [100.0] * m
    cc = [100.0] * m
    hh = [101.0] * m
    ll = [99.0] * m
    tt = list(range(m))
    for i in range(82, 87):
        oo[i] = 100.0 + (i - 82) * 2.0
        cc[i] = oo[i] + 1.0
        hh[i] = cc[i] + 0.2
        ll[i] = oo[i] - 0.1
    # FVG bullish: candle 85 low فوق candle 83 high.
    ll[85] = 104.0
    hh[83] = 102.2
    fake_frame = {"o": oo, "c": cc, "h": hh, "l": ll, "t": tt, "interval": "5m"}
    zone = detect_demand_zone(fake_frame)
    check("Demand Zone + 4 Green + BOS + FVG", zone is not None and zone["green_count"] >= 4 and zone["bos"])
    check("Decimal rounding", round_step(D("1.23456"), D("0.001")) == D("1.234"))
    print("النتيجة: " + ("ALL PASS ✅" if all(results) else "FAIL ❌"))
    return 0 if all(results) else 1


def startup_checks():
    if BINANCE_ENV == "live" and LIVE_CONFIRM != "I_UNDERSTAND_SPOT_RISK":
        raise SystemExit("Live يتطلب LIVE_TRADING_CONFIRM=I_UNDERSTAND_SPOT_RISK")
    CLIENT.sync_time()
    load_symbol_rules(CLIENT.exchange_info())
    if BINANCE_API_KEY and BINANCE_API_SECRET:
        CLIENT.account()
        log("الحساب الموقّع: OK")
    return True


def main():
    global DRY_RUN
    args = set(sys.argv[1:])
    ensure_dirs()
    if "--selftest" in args:
        raise SystemExit(selftest())
    if "--dry-run" in args:
        DRY_RUN = True
    load_state()
    startup_ready = False
    try:
        startup_checks()
        startup_ready = True
    except BinanceError as exc:
        log(f"تعذر الاتصال بـ Binance؛ ستتم إعادة المحاولة تلقائياً: {exc}")
        send_message(f"⚠️ <b>Binance غير متاح حالياً</b>\n{esc(exc)}\nلن يتوقف البوت؛ ستتم إعادة المحاولة تلقائياً.")
    if not live_execution_allowed():
        log("التنفيذ غير مفعّل؛ ستظهر الإشارات المؤهلة فقط")
    if "--once" in args:
        run_scan(force=True)
        manage_positions()
        return
    send_message(
        f"🚀 <b>NOVA SCALP AUTO v2</b>\nالبيئة: {regime_text()} | Spot فقط\n"
        f"التنفيذ: {'مفعّل' if live_execution_allowed() else 'غير مفعّل'}\n"
        "Macro EMA200 + Demand/BOS/FVG + Pullback MACD/Volume + OCO/Trailing.\n"
        "/menu لفتح لوحة التحكم.", main_keyboard(),
    )
    threading.Thread(target=telegram_loop, daemon=True, name="telegram-loop").start()
    last_scan = 0.0
    last_manage = 0.0
    last_startup_retry = 0.0
    while True:
        try:
            now = time.time()
            if not startup_ready and now - last_startup_retry >= 60:
                last_startup_retry = now
                try:
                    startup_checks()
                    startup_ready = True
                    send_message("✅ عاد اتصال Binance وأصبح الرادار جاهزاً للعمل.")
                except BinanceError as exc:
                    log(f"إعادة اتصال Binance لم تنجح: {exc}")
            if startup_ready and not STATE.get("paused") and now - last_scan >= SCAN_EVERY:
                last_scan = now
                threading.Thread(target=run_scan, daemon=True).start()
            if startup_ready and now - last_manage >= MANAGE_EVERY:
                last_manage = now
                manage_positions()
            if now - STATE.get("last_heartbeat", 0.0) >= 12 * 3600:
                STATE["last_heartbeat"] = now
                save_state()
                send_message(status_text(), main_keyboard())
            time.sleep(1)
        except KeyboardInterrupt:
            save_state()
            send_message("👋 تم إيقاف البوت؛ الذاكرة محفوظة.")
            return
        except Exception as exc:
            log(f"خطأ الحلقة: {exc}\n{traceback.format_exc()[-500:]}")
            time.sleep(8)


if __name__ == "__main__":
    main()
