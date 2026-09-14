#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA SCALP AUTO v1.0
بوت سكالبينج Spot تلقائي على Binance، يعمل افتراضياً على Spot Testnet.

الفكرة:
- 1m للإشارة السريعة، 5m لتأكيد الزخم، 15m لفلتر الاتجاه، وBTC كفلتر سوق.
- EMA9/EMA21 + VWAP + RSI7 + MACD سريع + Volume Spike + السبريد + دفتر الأوامر.
- يمنع التداول عند البيانات القديمة، الشمعة الشاذة، ضعف السيولة، أو اتساع السبريد.
- يفتح MARKET BUY فقط في Spot، ثم يضع حماية OCO: هدف LIMIT_MAKER + Trailing Stop.
- إذا فشلت حماية OCO يحاول وضع STOP_LOSS_LIMIT، وإذا فشلت الحماية أيضاً يخرج من المركز فوراً.
- لا يستخدم Futures أو رافعة أو بيعاً على المكشوف.
- يستخدم requests للاتصال، وHMAC من المكتبة القياسية لتوقيع Binance.
- Gemini والأخبار اختياريان؛ لأن استدعاء نموذج سحابي في سكالبينج سريع قد يضيف تأخيراً.

تثبيت Termux:
    pkg update -y
    pkg install python -y
    pip install requests matplotlib

المتغيرات الأساسية:
    export BINANCE_ENV='testnet'
    export BINANCE_API_KEY='مفتاح Binance Spot Testnet'
    export BINANCE_API_SECRET='سر Binance Spot Testnet'
    export TELEGRAM_BOT_TOKEN='توكن جديد من BotFather'
    export TELEGRAM_CHAT_ID='معرف المحادثة'

تشغيل آمن:
    python scalp_bot.py --selftest
    python scalp_bot.py --dry-run
    python scalp_bot.py

للتجربة الحقيقية لا يتم تغيير الوضع إلا يدوياً، ويتطلب:
    export BINANCE_ENV='live'
    export LIVE_TRADING_CONFIRM='I_UNDERSTAND_SPOT_RISK'
    export AUTO_TRADE='1'

هذا الملف لا يضمن الربح. التنفيذ الحقيقي مسؤولية المستخدم، وابدأ دائماً بـ Testnet.
"""

import csv
import hashlib
import hmac
import html
import json
import math
import os
import random
import statistics
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
# 1) إعدادات قابلة للتعديل عبر متغيرات البيئة
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
    value = D(value)
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


BINANCE_ENV = os.getenv("BINANCE_ENV", "testnet").strip().lower()
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "").strip()
TELEGRAM_TOKEN = __REDACTED__"TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

if BINANCE_ENV == "live":
    BINANCE_BASE = "https://api.binance.com"
else:
    BINANCE_ENV = "testnet"
    BINANCE_BASE = "https://testnet.binance.vision"

LIVE_CONFIRM = os.getenv("LIVE_TRADING_CONFIRM", "")
AUTO_TRADE = env_bool("AUTO_TRADE", True)
DRY_RUN = env_bool("DRY_RUN", False)
AI_GATE_ENABLED = env_bool("AI_GATE_ENABLED", False)
REQUIRE_NEWS = env_bool("REQUIRE_NEWS", True)
SEND_CHARTS = env_bool("SEND_CHARTS", True)

# قائمة افتراضية للعملات الأكثر ملاءمة للسكالبينج، ويُستبعد أي زوج غير متاح على البيئة.
SYMBOLS = [
    x.strip().upper() for x in os.getenv(
        "SCALP_SYMBOLS",
        "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,LINKUSDT,RENDERUSDT",
    ).split(",") if x.strip()
]
LEADER = "BTCUSDT"

# إعدادات الاستراتيجية السريعة.
KLINE_LIMIT = env_int("KLINE_LIMIT", 220)
SCAN_EVERY = env_int("SCAN_EVERY", 12)
MANAGE_EVERY = env_int("MANAGE_EVERY", 4)
TELEGRAM_POLL_TIMEOUT = env_int("TELEGRAM_POLL_TIMEOUT", 20)
RSI_PERIOD = 7
EMA_FAST = 9
EMA_SLOW = 21
MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 4
ATR_PERIOD = 14
MIN_VOLUME_RATIO = env_float("MIN_VOLUME_RATIO", 1.20)
MAX_SPREAD_PCT = env_float("MAX_SPREAD_PCT", 0.12)
MIN_BOOK_IMBALANCE = env_float("MIN_BOOK_IMBALANCE", 0.44)
MIN_24H_QUOTE_VOLUME = env_float("MIN_24H_QUOTE_VOLUME", 1_000_000)
MIN_SCORE = env_float("MIN_SCORE", 76.0)
FLASH_MOVE_PCT = env_float("FLASH_MOVE_PCT", 2.8)
FLASH_RANGE_ATR = env_float("FLASH_RANGE_ATR", 5.5)

# إدارة رأس المال والحدود اليومية.
TRADE_QUOTE_USD = env_float("TRADE_QUOTE_USD", 15.0)
MAX_POSITION_USD = env_float("MAX_POSITION_USD", 25.0)
MAX_POSITIONS = env_int("MAX_POSITIONS", 2)
MAX_DAILY_TRADES = env_int("MAX_DAILY_TRADES", 30)
MAX_DAILY_LOSS_USD = env_float("MAX_DAILY_LOSS_USD", 5.0)
MAX_CONSECUTIVE_LOSSES = env_int("MAX_CONSECUTIVE_LOSSES", 3)
SYMBOL_COOLDOWN = env_int("SYMBOL_COOLDOWN", 180)
ENTRY_SLIPPAGE_PCT = env_float("ENTRY_SLIPPAGE_PCT", 0.20)
STOP_ATR_MULT = env_float("STOP_ATR_MULT", 1.15)
TAKE_PROFIT_R = env_float("TAKE_PROFIT_R", 1.25)
FEE_BUFFER = env_float("FEE_BUFFER", 0.0015)

# ذاكرة وملفات.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "scalp_data")
CHART_DIR = os.path.join(DATA_DIR, "charts")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
TRADES_FILE = os.path.join(DATA_DIR, "trades.csv")
KILL_SWITCH_FILE = os.path.join(DATA_DIR, "STOP_TRADING")

# Gemini وCryptoCompare اختياريان، مع حد زمني حتى لا تتراكم الاستدعاءات.
GEMINI_MODELS = [
    x.strip() for x in os.getenv(
        "GEMINI_MODELS", "gemini-2.5-flash,gemini-2.0-flash,gemini-flash-latest"
    ).split(",") if x.strip()
]
GEMINI_MIN_INTERVAL = env_int("GEMINI_MIN_INTERVAL", 8)
NEWS_CACHE_SECONDS = env_int("NEWS_CACHE_SECONDS", 300)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "NOVA-SCALP-AUTO/1.0"})
STATE_LOCK = threading.RLock()
SCAN_LOCK = threading.Lock()
API_LOCK = threading.Lock()
GEMINI_LOCK = threading.Lock()
LAST_GEMINI_CALL = 0.0
NEWS_CACHE = {"time": 0.0, "items": []}
CHARTS_OK = None
SYMBOL_RULES = {}
TIME_OFFSET_MS = 0


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
        "last_scan": 0.0,
        "last_manage": 0.0,
        "last_heartbeat": 0.0,
        "last_digest": "",
        "cooldowns": {},
        "positions": {},
        "metrics": {
            "day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "trades": 0,
            "realized_pnl": 0.0,
            "losses": 0,
            "wins": 0,
            "consecutive_losses": 0,
        },
        "last_signals": [],
        "gemini_model": None,
    }


STATE = default_state()


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
        if not isinstance(base.get("cooldowns"), dict):
            base["cooldowns"] = {}
        if not isinstance(base.get("metrics"), dict):
            base["metrics"] = default_state()["metrics"]
        STATE = base
        reset_daily_metrics()
        log(f"الذاكرة: {len(STATE['positions'])} مركزاً محفوظاً")
    except FileNotFoundError:
        log("لا توجد ذاكرة سابقة؛ بداية جديدة")
    except Exception as exc:
        log(f"تعذر تحميل الذاكرة: {exc}")


def save_state():
    try:
        ensure_dirs()
        with STATE_LOCK:
            temporary = STATE_FILE + ".tmp"
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(STATE, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, STATE_FILE)
    except Exception as exc:
        log(f"فشل حفظ الذاكرة: {exc}")


def reset_daily_metrics():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    metrics = STATE.setdefault("metrics", {})
    if metrics.get("day") != today:
        STATE["metrics"] = {
            "day": today,
            "trades": 0,
            "realized_pnl": 0.0,
            "losses": 0,
            "wins": 0,
            "consecutive_losses": 0,
        }


def record_trade(row):
    try:
        ensure_dirs()
        fresh = not os.path.exists(TRADES_FILE)
        with open(TRADES_FILE, "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if fresh:
                writer.writerow([
                    "time", "symbol", "entry", "exit", "qty", "pnl",
                    "reason", "score", "environment",
                ])
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


def make_client_id(prefix="nova"):
    return (prefix + uuid.uuid4().hex[:20]).upper()[:36]


def kill_switch_active():
    return os.path.exists(KILL_SWITCH_FILE)


# ══════════════════════════════════════════════════════════════════════════════
# 3) مؤشرات Pure Python
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
    gains = 0.0
    losses = 0.0
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
    fast_line = ema(values, fast)
    slow_line = ema(values, slow)
    line = [None if fast_line[i] is None or slow_line[i] is None else fast_line[i] - slow_line[i] for i in range(len(values))]
    valid = [x for x in line if x is not None]
    signal_valid = ema(valid, signal_period)
    signal_line = [None] * len(values)
    pointer = 0
    for i, value in enumerate(line):
        if value is not None:
            signal_line[i] = signal_valid[pointer]
            pointer += 1
    hist = [None if line[i] is None or signal_line[i] is None else line[i] - signal_line[i] for i in range(len(values))]
    return line, signal_line, hist


def true_ranges(highs, lows, closes):
    if not closes:
        return []
    result = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        result.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
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
        total_pv = 0.0
        total_volume = 0.0
        for j in range(i - period + 1, i + 1):
            typical = (highs[j] + lows[j] + closes[j]) / 3.0
            total_pv += typical * volumes[j]
            total_volume += volumes[j]
        result[i] = total_pv / total_volume if total_volume else None
    return result


def last_valid(values, default=0.0):
    for value in reversed(values):
        if value is not None:
            return value
    return default


def crossed_up(left, right, bars=3):
    start = max(1, len(left) - bars)
    for i in range(start, len(left)):
        if None in (left[i - 1], right[i - 1], left[i], right[i]):
            continue
        if left[i - 1] <= right[i - 1] and left[i] > right[i]:
            return True
    return False


def crossed_down(left, right, bars=3):
    start = max(1, len(left) - bars)
    for i in range(start, len(left)):
        if None in (left[i - 1], right[i - 1], left[i], right[i]):
            continue
        if left[i - 1] >= right[i - 1] and left[i] < right[i]:
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# 4) Binance REST: public + signed HMAC
# ══════════════════════════════════════════════════════════════════════════════


class BinanceError(Exception):
    def __init__(self, message, code=None, status=None):
        super().__init__(message)
        self.code = code
        self.status = status


class BinanceClient:
    def __init__(self):
        self.base = BINANCE_BASE
        self.api_key = __REDACTED__
        self.api_secret = __REDACTED__

    def _parse(self, response):
        try:
            payload = response.json()
        except ValueError:
            raise BinanceError(f"استجابة Binance غير JSON: HTTP {response.status_code}", status=response.status_code)
        if response.status_code >= 400 or (isinstance(payload, dict) and payload.get("code", 0) < 0):
            message = payload.get("msg", "خطأ Binance") if isinstance(payload, dict) else "خطأ Binance"
            raise BinanceError(message, payload.get("code") if isinstance(payload, dict) else None, response.status_code)
        return payload

    def public(self, path, params=None, timeout=12):
        try:
            response = SESSION.get(self.base + path, params=params or {}, timeout=timeout)
            return self._parse(response)
        except requests.RequestException as exc:
            raise BinanceError(f"شبكة Binance: {exc}")

    def server_time(self):
        payload = self.public("/api/v3/time", timeout=8)
        return int(payload["serverTime"])

    def sync_time(self):
        global TIME_OFFSET_MS
        try:
            TIME_OFFSET_MS = self.server_time() - int(time.time() * 1000)
        except Exception as exc:
            log(f"تعذر مزامنة وقت Binance: {exc}")

    def signed(self, method, path, params=None, retry=True, timeout=15):
        if not self.api_key or not self.api_secret:
            raise BinanceError("مفاتيح Binance غير موجودة")
        method = method.upper()
        values = dict(params or {})
        values["recvWindow"] = values.get("recvWindow", 5000)
        values["timestamp"] = int(time.time() * 1000) + TIME_OFFSET_MS
        query = urlencode(values, doseq=True)
        signature = hmac.new(self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        values["signature"] = signature
        headers = {"X-MBX-APIKEY": self.api_key}
        try:
            if method == "GET":
                response = SESSION.get(self.base + path, params=values, headers=headers, timeout=timeout)
            elif method == "DELETE":
                response = SESSION.delete(self.base + path, params=values, headers=headers, timeout=timeout)
            else:
                response = SESSION.post(self.base + path, data=values, headers=headers, timeout=timeout)
            try:
                return self._parse(response)
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
        if not isinstance(payload, list) or len(payload) < 60:
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
        if not isinstance(payload, list):
            return result
        for item in payload:
            try:
                result[item["symbol"]] = {
                    "price": float(item["lastPrice"]),
                    "change": float(item["priceChangePercent"]),
                    "quote_volume": float(item["quoteVolume"]),
                }
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def book_ticker(self, symbol):
        payload = self.public("/api/v3/ticker/bookTicker", {"symbol": symbol}, timeout=8)
        return {
            "bid": float(payload["bidPrice"]),
            "ask": float(payload["askPrice"]),
            "bid_qty": float(payload["bidQty"]),
            "ask_qty": float(payload["askQty"]),
        }

    def order_book(self, symbol, limit=20):
        payload = self.public("/api/v3/depth", {"symbol": symbol, "limit": limit}, timeout=8)
        bids = [(float(row[0]), float(row[1])) for row in payload.get("bids", [])]
        asks = [(float(row[0]), float(row[1])) for row in payload.get("asks", [])]
        bid_value = sum(price * qty for price, qty in bids)
        ask_value = sum(price * qty for price, qty in asks)
        total = bid_value + ask_value
        return {"imbalance": bid_value / total if total else 0.5, "bids": bids, "asks": asks}

    def account(self):
        return self.signed("GET", "/api/v3/account")

    def free_balance(self, asset, account_payload=None):
        payload = account_payload or self.account()
        for balance in payload.get("balances", []):
            if balance.get("asset") == asset:
                return D(balance.get("free"))
        return Decimal("0")

    def new_order(self, params):
        return self.signed("POST", "/api/v3/order", params=params)

    def get_order(self, symbol, order_id):
        return self.signed("GET", "/api/v3/order", {"symbol": symbol, "orderId": order_id})

    def cancel_order(self, symbol, order_id):
        return self.signed("DELETE", "/api/v3/order", {"symbol": symbol, "orderId": order_id})

    def cancel_all(self, symbol):
        return self.signed("DELETE", "/api/v3/openOrders", {"symbol": symbol})

    def order_list(self, order_list_id):
        return self.signed("GET", "/api/v3/orderList", {"orderListId": order_list_id})

    def new_oco(self, params):
        return self.signed("POST", "/api/v3/orderList/oco", params=params)


CLIENT = BinanceClient()


def prepare_symbol_rules(payload):
    global SYMBOL_RULES
    SYMBOL_RULES = {}
    for item in (payload or {}).get("symbols", []):
        symbol = item.get("symbol")
        if symbol not in SYMBOLS and symbol != LEADER:
            continue
        filters = {row.get("filterType"): row for row in item.get("filters", [])}
        lot = filters.get("LOT_SIZE", {})
        market_lot = filters.get("MARKET_LOT_SIZE", lot)
        price = filters.get("PRICE_FILTER", {})
        min_notional = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {}))
        trailing = filters.get("TRAILING_DELTA", {})
        SYMBOL_RULES[symbol] = {
            "status": item.get("status"),
            "base": item.get("baseAsset"),
            "quote": item.get("quoteAsset"),
            "tick": D(price.get("tickSize", "0.00000001")),
            "step": D(market_lot.get("stepSize", lot.get("stepSize", "0.00000001"))),
            "min_qty": D(market_lot.get("minQty", lot.get("minQty", "0"))),
            "max_qty": D(market_lot.get("maxQty", lot.get("maxQty", "999999999"))),
            "min_notional": D(min_notional.get("minNotional", "0")),
            "min_trailing_below": int(trailing.get("minTrailingBelowDelta", 10)),
            "max_trailing_below": int(trailing.get("maxTrailingBelowDelta", 2000)),
        }
    log(f"قواعد التداول محمّلة: {len(SYMBOL_RULES)} زوج")


def round_step(value, step):
    value, step = D(value), D(step)
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_FLOOR) * step


def round_price(value, tick, direction="down"):
    value, tick = D(value), D(tick)
    if tick <= 0:
        return value
    rounding = ROUND_CEILING if direction == "up" else ROUND_FLOOR
    return (value / tick).to_integral_value(rounding=rounding) * tick


def fmt_price(symbol, value):
    rule = SYMBOL_RULES.get(symbol, {})
    tick = rule.get("tick", Decimal("0.00000001"))
    value = D(value)
    if tick > 0:
        decimals = max(0, -tick.as_tuple().exponent)
    else:
        decimals = 8
    return f"{value:.{decimals}f}"


# ══════════════════════════════════════════════════════════════════════════════
# 5) تحليل الشموع وفحوص السلامة
# ══════════════════════════════════════════════════════════════════════════════


def quality_check(raw, interval, atr_value):
    errors = []
    if not raw or len(raw.get("c", [])) < 60:
        errors.append("شموع غير كافية")
        return {"ok": False, "flash": False, "errors": errors}
    n = len(raw["c"])
    for i in range(n):
        try:
            values = (raw["o"][i], raw["h"][i], raw["l"][i], raw["c"][i], raw["v"][i])
            if not all(math.isfinite(float(value)) for value in values):
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
            errors.append("وقت الشموع غير مرتب")
            break
    interval_ms = {"1m": 60_000, "5m": 300_000, "15m": 900_000}.get(interval, 60_000)
    if raw.get("t") and int(time.time() * 1000) - raw["t"][-1] > interval_ms * 3:
        errors.append("البيانات قديمة")
    # نستخدم الشموع المغلقة فقط في الحسابات، والشمعة الأخيرة في Binance قد تكون جارية.
    closed_close = raw["c"][:-1]
    closed_high = raw["h"][:-1]
    closed_low = raw["l"][:-1]
    flash = False
    flash_reason = ""
    if len(closed_close) >= 2 and atr_value > 0:
        move_pct = abs(closed_close[-1] / closed_close[-2] - 1.0) * 100.0
        range_multiple = (closed_high[-1] - closed_low[-1]) / atr_value
        if move_pct >= FLASH_MOVE_PCT:
            flash, flash_reason = True, f"حركة {move_pct:.2f}% في شمعة واحدة"
        elif range_multiple >= FLASH_RANGE_ATR:
            flash, flash_reason = True, f"مدى {range_multiple:.1f}× ATR"
    if flash:
        errors.append("حركة شاذة: " + flash_reason)
    return {"ok": not errors, "flash": flash, "flash_reason": flash_reason, "errors": errors}


def analyze_frame(raw, interval):
    if not raw:
        return None
    c, h, l, o, v = [raw[key][:-1] for key in ("c", "h", "l", "o", "v")]
    if len(c) < 60:
        return None
    ema_fast = ema(c, EMA_FAST)
    ema_slow = ema(c, EMA_SLOW)
    macd_line, macd_signal, histogram = macd(c, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    rsi_values = rsi(c, RSI_PERIOD)
    atr_values = atr(h, l, c, ATR_PERIOD)
    vwap_values = vwap(h, l, c, v, 24)
    volume_average = sma(v, 20)
    atr_value = last_valid(atr_values, 0.0)
    q = quality_check(raw, interval, atr_value)
    vol_ratio = v[-1] / volume_average[-1] if volume_average[-1] else 0.0
    trend = "up" if c[-1] > last_valid(ema_fast) > last_valid(ema_slow) else "down" if c[-1] < last_valid(ema_fast) < last_valid(ema_slow) else "side"
    candle_range = max(h[-1] - l[-1], 1e-12)
    lower_wick = min(o[-1], c[-1]) - l[-1]
    upper_wick = h[-1] - max(o[-1], c[-1])
    return {
        "interval": interval,
        "raw": raw,
        "t": raw["t"][:-1],
        "o": o, "h": h, "l": l, "c": c, "v": v,
        "close": c[-1],
        "ema_fast": last_valid(ema_fast),
        "ema_slow": last_valid(ema_slow),
        "ema_fast_series": ema_fast,
        "ema_slow_series": ema_slow,
        "macd": last_valid(macd_line),
        "macd_signal": last_valid(macd_signal),
        "hist": last_valid(histogram),
        "hist_prev": histogram[-2] if len(histogram) > 1 and histogram[-2] is not None else 0.0,
        "macd_up": crossed_up(macd_line, macd_signal, 4),
        "macd_down": crossed_down(macd_line, macd_signal, 4),
        "macd_line_series": macd_line,
        "macd_signal_series": macd_signal,
        "hist_series": histogram,
        "rsi": last_valid(rsi_values, 50.0),
        "rsi_prev": rsi_values[-2] if len(rsi_values) > 1 and rsi_values[-2] is not None else 50.0,
        "rsi_series": rsi_values,
        "atr": atr_value,
        "atr_pct": atr_value / c[-1] * 100.0 if c[-1] else 0.0,
        "atr_series": atr_values,
        "vwap": last_valid(vwap_values, c[-1]),
        "vwap_series": vwap_values,
        "volume_average": volume_average,
        "volume_ratio": vol_ratio,
        "trend": trend,
        "prev_high": h[-2] if len(h) > 1 else h[-1],
        "prev_low": l[-2] if len(l) > 1 else l[-1],
        "lower_wick_ratio": lower_wick / candle_range,
        "upper_wick_ratio": upper_wick / candle_range,
        "quality": q,
    }


def fetch_frames(symbol):
    frames = {}
    for interval in ("1m", "5m", "15m"):
        frames[interval] = analyze_frame(CLIENT.klines(symbol, interval), interval)
    return frames if all(frames.values()) else None


def book_stats(symbol):
    book = CLIENT.book_ticker(symbol)
    bid, ask = book["bid"], book["ask"]
    mid = (bid + ask) / 2.0
    spread = (ask - bid) / mid * 100.0 if mid else 99.0
    try:
        depth = CLIENT.order_book(symbol, 20)
        imbalance = float(depth.get("imbalance", 0.5))
    except BinanceError:
        imbalance = 0.5
    return {"bid": bid, "ask": ask, "mid": mid, "spread_pct": spread, "imbalance": imbalance}


def btc_filter(btc_frames):
    if not btc_frames:
        return False, "بيانات BTC غير مكتملة"
    f5, f15 = btc_frames["5m"], btc_frames["15m"]
    if f5["quality"]["flash"] or f15["quality"]["flash"]:
        return False, "حركة شاذة في BTC"
    if f15["trend"] == "down" and f5["trend"] == "down":
        return False, "BTC هابط على 5m و15m"
    return True, "BTC غير هابط على الفلاتر"


def make_candidate(symbol, frames, btc_frames, quote_volume):
    if not frames or not btc_frames:
        return None
    f1, f5, f15 = frames["1m"], frames["5m"], frames["15m"]
    if any(not frame["quality"]["ok"] for frame in (f1, f5, f15)):
        return None
    if quote_volume < MIN_24H_QUOTE_VOLUME:
        return None
    btc_ok, btc_reason = btc_filter(btc_frames)
    if not btc_ok:
        return None
    book = book_stats(symbol)
    if book["spread_pct"] > MAX_SPREAD_PCT:
        return None
    if book["imbalance"] < MIN_BOOK_IMBALANCE:
        return None

    trend_confirmed = f5["trend"] == "up" and f5["close"] > f5["vwap"]
    higher_filter = f15["trend"] != "down"
    momentum_cross = f1["macd_up"] or (f1["hist"] > 0 and f1["hist"] > f1["hist_prev"])
    rsi_ok = 45.0 <= f1["rsi"] <= 76.0 and f1["rsi"] > f1["rsi_prev"]
    volume_ok = f1["volume_ratio"] >= MIN_VOLUME_RATIO
    reclaim = f1["close"] > f1["ema_fast"] and f1["close"] > f1["prev_high"]
    pullback = f1["l"][-1] <= max(f1["ema_fast"], f1["vwap"]) * 1.002
    candle_ok = f1["close"] > f1["o"][-1] and f1["lower_wick_ratio"] >= 0.15
    core = trend_confirmed and higher_filter and momentum_cross and rsi_ok and volume_ok and (reclaim or pullback)
    if not core:
        return None

    score = 0.0
    score += 20.0 if trend_confirmed else 0.0
    score += 15.0 if higher_filter else 0.0
    score += 20.0 if f1["macd_up"] else 13.0 if f1["hist"] > f1["hist_prev"] else 0.0
    score += 15.0 if rsi_ok else 0.0
    score += min(15.0, 10.0 * f1["volume_ratio"] / max(MIN_VOLUME_RATIO, 0.1))
    score += 8.0 if book["imbalance"] >= 0.55 else 5.0
    score += 4.0 if reclaim else 2.0
    score += 3.0 if candle_ok else 0.0
    score = round(clamp(score, 0.0, 100.0), 1)
    if score < MIN_SCORE:
        return None

    price = book["ask"]
    atr_pct = max(f1["atr_pct"], f5["atr_pct"] * 0.45)
    stop_pct = clamp(max(atr_pct * STOP_ATR_MULT, 0.22), 0.30, 1.80)
    target_pct = clamp(stop_pct * TAKE_PROFIT_R, 0.40, 3.00)
    trail_pct = clamp(max(atr_pct * 1.35, 0.30), 0.30, 2.50)
    rule = SYMBOL_RULES.get(symbol, {})
    min_trail = rule.get("min_trailing_below", 10)
    max_trail = rule.get("max_trailing_below", 2000)
    trail_bips = int(clamp(round(trail_pct * 100.0), min_trail, max_trail))
    return {
        "symbol": symbol,
        "side": "BUY",
        "price": price,
        "score": score,
        "frames": frames,
        "btc_frames": btc_frames,
        "book": book,
        "quote_volume": quote_volume,
        "btc_reason": btc_reason,
        "stop_pct": stop_pct,
        "target_pct": target_pct,
        "trail_pct": trail_bips / 100.0,
        "trail_bips": trail_bips,
        "created_at": time.time(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 6) أخبار Gemini الاختيارية
# ══════════════════════════════════════════════════════════════════════════════


def fetch_news(symbol):
    global NEWS_CACHE
    now = time.time()
    if now - NEWS_CACHE["time"] < NEWS_CACHE_SECONDS:
        source = NEWS_CACHE["items"]
    else:
        try:
            response = SESSION.get(
                "https://min-api.cryptocompare.com/data/v2/news/",
                params={"lang": "EN", "sortOrder": "latest", "limit": 30},
                timeout=12,
            )
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
        content = " ".join(str(item.get(k, "")) for k in ("title", "body", "categories")).upper()
        if base in content or any(word in content for word in ("CRYPTO", "MARKET", "BITCOIN", "SEC", "ETF")):
            result.append({"title": str(item.get("title", ""))[:180], "source": str(item.get("source", ""))[:60]})
        if len(result) >= 6:
            break
    return result, True


PERSONA = (
    "أنت مدير تداول مؤسسي صارم. راجع بيانات سكالبينج قصيرة المدى والأخبار الحالية. "
    "إذا كان هناك خطر جوهري أو خبر قد يفسد الدخول اكتب إلغاء فقط. "
    "وإلا اكتب سطرين بالعربية يذكران السيناريو والخطر الرئيسي. لا تضمن الربح ولا تنفذ أوامر."
)


def gemini_call(prompt):
    global LAST_GEMINI_CALL
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY غير موجود"
    with GEMINI_LOCK:
        wait = GEMINI_MIN_INTERVAL - (time.time() - LAST_GEMINI_CALL)
        if wait > 0:
            time.sleep(wait)
        models = []
        if STATE.get("gemini_model"):
            models.append(STATE["gemini_model"])
        models.extend(model for model in GEMINI_MODELS if model not in models)
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.15, "maxOutputTokens": 180},
            }
            try:
                response = SESSION.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=25)
                LAST_GEMINI_CALL = time.time()
                if response.status_code in (429, 500, 503):
                    time.sleep(2)
                    continue
                payload = response.json()
                candidates = payload.get("candidates") or []
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = " ".join(str(part.get("text", "")) for part in parts).strip()
                    if text:
                        STATE["gemini_model"] = model
                        return text, None
            except (requests.RequestException, ValueError, KeyError):
                continue
    return None, "تعذر الوصول إلى Gemini"


def ai_veto(candidate, news):
    signal = candidate["frames"]["1m"]
    f5, f15 = candidate["frames"]["5m"], candidate["frames"]["15m"]
    headlines = "\n".join(f"- {item['title']} | {item['source']}" for item in news) or "لا توجد عناوين مطابقة"
    prompt = (
        f"{PERSONA}\n"
        f"العملة {symbol_name(candidate['symbol'])}, السعر {candidate['price']:.12g}, score {candidate['score']}/100. "
        f"RSI7={signal['rsi']:.2f}, MACD histogram={signal['hist']:.8g}, "
        f"Volume={signal['volume_ratio']:.2f}x, spread={candidate['book']['spread_pct']:.3f}%, "
        f"book imbalance={candidate['book']['imbalance']:.3f}, ATR={signal['atr_pct']:.3f}%. "
        f"5m={f5['trend']}, 15m={f15['trend']}, BTC={candidate['btc_reason']}.\n"
        f"الأخبار:\n{headlines}\n"
        "التزم: إلغاء فقط عند وجود خطر جوهري، وإلا سطران فقط."
    )
    text, reason = gemini_call(prompt)
    if not text:
        return (False, "حجب آمن: " + reason) if REQUIRE_NEWS else (True, "فلتر Gemini غير متاح")
    cleaned = text.replace("**", "").replace("`", "").strip()
    if cleaned.lower().startswith("إلغاء") or cleaned.lower().startswith("الغاء") or cleaned.lower().startswith("cancel"):
        return False, "Gemini رفض الإشارة"
    return True, cleaned[:650]


# ══════════════════════════════════════════════════════════════════════════════
# 7) Telegram
# ══════════════════════════════════════════════════════════════════════════════


def tg_call(method, payload=None, files=None, retries=3):
    if not TELEGRAM_TOKEN:
        __REDACTED__ None
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
                time.sleep(2.0 + attempt)
        except (requests.RequestException, ValueError):
            time.sleep(1.0 + attempt)
    return None


def send_message(text, keyboard=None, chat_id=None):
    if DRY_RUN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n" + "═" * 70 + "\n[Telegram محاكاة]\n" + text + "\n" + "═" * 70)
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


def keyboard_button(text, data):
    return {"text": text, "callback_data": data}


def main_keyboard():
    return [
        [keyboard_button("📡 الحالة", "status"), keyboard_button("🔎 فحص", "scan")],
        [keyboard_button("⏸ إيقاف", "pause"), keyboard_button("▶ استئناف", "resume")],
        [keyboard_button("🧯 إلغاء الأوامر", "cancelall"), keyboard_button("❓ مساعدة", "help")],
    ]


def status_text():
    reset_daily_metrics()
    m = STATE["metrics"]
    lines = [
        f"📡 <b>NOVA SCALP AUTO</b> — {'TESTNET' if BINANCE_ENV == 'testnet' else 'LIVE'}",
        f"التشغيل الآلي: {'✅' if AUTO_TRADE and not DRY_RUN else '🟡 محاكاة/متوقف'} | الفحص: {'⏸' if STATE.get('paused') else '✅'}",
        f"اليوم UTC: {m.get('day')} | صفقات: {m.get('trades', 0)}/{MAX_DAILY_TRADES} | PnL محقق: {m.get('realized_pnl', 0.0):+.4f}$",
        f"خسائر متتالية: {m.get('consecutive_losses', 0)}/{MAX_CONSECUTIVE_LOSSES}",
        f"مراكز: <b>{len(STATE.get('positions', {}))}</b>/{MAX_POSITIONS}",
    ]
    for key, pos in STATE.get("positions", {}).items():
        lines.append(
            f"🟢 {symbol_name(pos['symbol'])} | دخول <code>{fmt_price(pos['symbol'], pos['entry'])}</code> | "
            f"TP <code>{fmt_price(pos['symbol'], pos['target'])}</code> | "
            f"Trail {pos.get('trail_bips', 0)} bips"
        )
    if kill_switch_active():
        lines.append("\n🛑 ملف STOP_TRADING موجود — التداول مغلق")
    return "\n".join(lines)


HELP_TEXT = (
    "🤖 <b>NOVA SCALP AUTO</b>\n\n"
    "/start أو /menu لوحة التحكم\n"
    "/scan فحص فوري\n"
    "/status الحالة والمراكز والحدود\n"
    "/pause إيقاف الدخولات الجديدة\n"
    "/resume استئناف الدخولات\n"
    "/cancelall إلغاء الأوامر المفتوحة دون بيع الأصول\n"
    "/panic إلغاء الأوامر ومحاولة بيع مراكز البوت\n"
    "/kill إنشاء قاطع تداول محلي\n"
    "/unkill إزالة القاطع المحلي\n\n"
    "الاستراتيجية: اتجاه 5m، فلتر 15m وBTC، زخم 1m، EMA/VWAP/RSI/MACD/Volume، "
    "ثم حماية OCO على Binance."
)


# ══════════════════════════════════════════════════════════════════════════════
# 8) الشارت
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
    ema_fast = ema(c, EMA_FAST)
    ema_slow = ema(c, EMA_SLOW)
    vw = vwap(h, l, c, v, 24)
    rs = rsi(c, RSI_PERIOD)
    ml, ms, hist = macd(c, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    volume_avg = sma(v, 20)
    n = len(c)
    bg, panel, grid, txt = "#0d1117", "#121a22", "#27313d", "#d4d8df"
    green, red, blue, yellow, purple, orange = "#0ecb81", "#f6465d", "#4c8bf5", "#f0b90b", "#b17ce8", "#ff9f43"
    fig = plt.figure(figsize=(12, 8.5), dpi=110)
    fig.patch.set_facecolor(bg)
    gs = fig.add_gridspec(4, 1, height_ratios=(3.5, 0.8, 1.0, 1.0), hspace=0.05, left=0.07, right=0.98, top=0.92, bottom=0.06)
    axes = [fig.add_subplot(gs[0])]
    axes += [fig.add_subplot(gs[i], sharex=axes[0]) for i in (1, 2, 3)]
    for axis in axes:
        axis.set_facecolor(panel)
        axis.grid(True, color=grid, linewidth=0.5)
        axis.tick_params(colors=txt, labelsize=8)
        for spine in axis.spines.values():
            spine.set_color(grid)
    price_ax, vol_ax, rsi_ax, macd_ax = axes
    for i in range(n):
        color = green if c[i] >= o[i] else red
        price_ax.plot([i, i], [l[i], h[i]], color=color, linewidth=0.7)
        price_ax.add_patch(Rectangle((i - 0.35, min(o[i], c[i])), 0.7, max(abs(c[i] - o[i]), max(c) * 0.00001), facecolor=color, edgecolor=color))
        vol_ax.bar(i, v[i], color=color, width=0.7)
        if hist[i] is not None:
            macd_ax.bar(i, hist[i], color=green if hist[i] >= 0 else red, width=0.7)
    for series, color, label in ((ema_fast, yellow, "EMA9"), (ema_slow, blue, "EMA21"), (vw, purple, "VWAP")):
        xs = [i for i, value in enumerate(series) if value is not None]
        if len(xs) > 2:
            price_ax.plot(xs, [series[i] for i in xs], color=color, linewidth=1.1, label=label)
    price_ax.axhline(candidate["price"], color=orange, linestyle=":", linewidth=0.9, label="Ask")
    price_ax.set_title(
        f"{symbol_name(candidate['symbol'])} | 1m scalp BUY | Score {candidate['score']}/100 | "
        f"Trail {candidate['trail_bips']} bips",
        color=txt, fontsize=11, fontweight="bold", loc="left",
    )
    price_ax.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=txt, ncol=4)
    vol_ax.plot([i for i, value in enumerate(volume_avg) if value is not None], [value for value in volume_avg if value is not None], color=yellow, linewidth=0.8)
    vol_ax.set_ylabel("VOL", color=txt, fontsize=8)
    rx = [i for i, value in enumerate(rs) if value is not None]
    rsi_ax.plot(rx, [rs[i] for i in rx], color=purple, linewidth=1.1)
    rsi_ax.axhline(70, color=red, linestyle="--", linewidth=0.6)
    rsi_ax.axhline(30, color=green, linestyle="--", linewidth=0.6)
    rsi_ax.set_ylim(0, 100)
    rsi_ax.set_ylabel("RSI7", color=txt, fontsize=8)
    mx = [i for i, value in enumerate(ml) if value is not None]
    macd_ax.plot(mx, [ml[i] for i in mx], color=blue, linewidth=0.9, label="MACD")
    macd_ax.plot(mx, [ms[i] for i in mx], color=orange, linewidth=0.9, label="Signal")
    macd_ax.axhline(0, color=txt, linewidth=0.5)
    macd_ax.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=txt)
    step = max(1, n // 6)
    ticks = list(range(0, n, step))
    labels = []
    for i in ticks:
        try:
            labels.append(datetime.fromtimestamp(raw["t"][start + i] / 1000).strftime("%H:%M:%S"))
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
# 9) إدارة أوامر Spot التلقائية
# ══════════════════════════════════════════════════════════════════════════════


def live_execution_allowed():
    if DRY_RUN or not AUTO_TRADE:
        return False
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return False
    if BINANCE_ENV == "live" and LIVE_CONFIRM != "I_UNDERSTAND_SPOT_RISK":
        return False
    return True


def circuit_allows_entry():
    reset_daily_metrics()
    metrics = STATE["metrics"]
    if kill_switch_active():
        return False, "قاطع STOP_TRADING نشط"
    if STATE.get("paused"):
        return False, "الرادار متوقف"
    if metrics.get("trades", 0) >= MAX_DAILY_TRADES:
        return False, "تم بلوغ حد الصفقات اليومي"
    if metrics.get("realized_pnl", 0.0) <= -abs(MAX_DAILY_LOSS_USD):
        return False, "تم بلوغ حد الخسارة اليومية"
    if metrics.get("consecutive_losses", 0) >= MAX_CONSECUTIVE_LOSSES:
        return False, "قاطع الخسائر المتتالية"
    if len(STATE.get("positions", {})) >= MAX_POSITIONS:
        return False, "الحد الأقصى للمراكز ممتلئ"
    return True, "OK"


def trade_key(symbol):
    return symbol


def position_exists(symbol):
    return symbol in STATE.get("positions", {})


def entry_message(candidate, position=None, ai_text=""):
    symbol = candidate["symbol"]
    f1, f5, f15 = candidate["frames"]["1m"], candidate["frames"]["5m"], candidate["frames"]["15m"]
    entry = position.get("entry", candidate["price"]) if position else candidate["price"]
    target = position.get("target") if position else entry * (1.0 + candidate["target_pct"] / 100.0)
    stop = position.get("stop") if position else entry * (1.0 - candidate["stop_pct"] / 100.0)
    mode = "TESTNET تنفيذ آلي" if BINANCE_ENV == "testnet" and live_execution_allowed() else "إشارة/محاكاة"
    lines = [
        "🚀 <b>دخول سكالبينج تلقائي — BUY</b>",
        f"🔹 <b>{symbol_name(symbol)}</b> | {mode}",
        f"السعر: <code>{fmt_price(symbol, entry)}</code> | Score: <b>{candidate['score']}/100</b>",
        "",
        f"1m: RSI7 {f1['rsi']:.1f} | MACD Hist {f1['hist']:.8g} | Volume {f1['volume_ratio']:.2f}x",
        f"5m: {f5['trend']} فوق VWAP | 15m: {f15['trend']} | BTC: {candidate['btc_reason']}",
        f"Spread: {candidate['book']['spread_pct']:.3f}% | Book imbalance: {candidate['book']['imbalance']:.3f}",
        "",
        f"🎯 الهدف: <code>{fmt_price(symbol, target)}</code> (+{candidate['target_pct']:.2f}%)",
        f"🛑 الحماية المرجعية: <code>{fmt_price(symbol, stop)}</code> (-{candidate['stop_pct']:.2f}%)",
        f"🛤 Trailing Delta: <b>{candidate['trail_pct']:.2f}% ({candidate['trail_bips']} bips)</b>",
        f"💵 القيمة: <b>{position.get('quote_qty', TRADE_QUOTE_USD) if position else TRADE_QUOTE_USD:.2f}$</b>",
    ]
    if position:
        lines.append(f"Binance entry order: <code>{position.get('entry_order_id')}</code>")
        lines.append(f"حماية: {'OCO ✅' if position.get('order_list_id') else 'STOP fallback ⚠️'}")
    if ai_text:
        lines += ["", "🧠 <b>Gemini:</b>", esc(ai_text)]
    lines.append("\n⚠️ تداول Spot فقط؛ لا رافعة ولا بيع على المكشوف.")
    return "\n".join(lines)


def parse_fill(order, fallback_price):
    executed_qty = D(order.get("executedQty", "0"))
    quote_qty = D(order.get("cummulativeQuoteQty", "0"))
    avg = quote_qty / executed_qty if executed_qty > 0 and quote_qty > 0 else D(fallback_price)
    return executed_qty, quote_qty, avg


def place_protection(symbol, qty, entry, stop_pct, target_pct, trail_bips):
    rule = SYMBOL_RULES[symbol]
    target = round_price(D(entry) * (Decimal("1") + D(target_pct) / Decimal("100")), rule["tick"], "up")
    stop = round_price(D(entry) * (Decimal("1") - D(stop_pct) / Decimal("100")), rule["tick"], "down")
    stop_limit = round_price(stop * (Decimal("1") - D(ENTRY_SLIPPAGE_PCT) / Decimal("100")), rule["tick"], "down")
    qty = round_step(qty * (Decimal("1") - D(FEE_BUFFER)), rule["step"])
    if qty < rule["min_qty"] or qty * entry < rule["min_notional"]:
        raise BinanceError("الكمية بعد خصم هامش الرسوم أقل من فلاتر Binance")
    oco_params = {
        "symbol": symbol,
        "side": "SELL",
        "quantity": dec_str(qty),
        "aboveType": "LIMIT_MAKER",
        "abovePrice": dec_str(target),
        "belowType": "STOP_LOSS_LIMIT",
        "belowPrice": dec_str(stop_limit),
        "belowTimeInForce": "GTC",
        "belowTrailingDelta": int(trail_bips),
        "listClientOrderId": make_client_id("oco"),
        "newOrderRespType": "RESULT",
    }
    try:
        result = CLIENT.new_oco(oco_params)
        return {
            "type": "OCO",
            "order_list_id": result.get("orderListId"),
            "orders": result.get("orders", []),
            "target": target,
            "stop": stop,
            "qty": qty,
        }
    except BinanceError as oco_error:
        log(f"OCO فشل لـ {symbol}: {oco_error}; محاولة STOP_LOSS_LIMIT")
        fallback_params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "STOP_LOSS_LIMIT",
            "timeInForce": "GTC",
            "quantity": dec_str(qty),
            "price": dec_str(stop_limit),
            "stopPrice": dec_str(stop),
            "newClientOrderId": make_client_id("stp"),
            "newOrderRespType": "RESULT",
        }
        try:
            stop_order = CLIENT.new_order(fallback_params)
            return {
                "type": "STOP",
                "order_list_id": None,
                "orders": [{"orderId": stop_order.get("orderId")}],
                "stop_order_id": stop_order.get("orderId"),
                "target": target,
                "stop": stop,
                "qty": qty,
            }
        except BinanceError as stop_error:
            raise BinanceError(f"فشلت OCO والحماية البديلة: {stop_error}") from oco_error


def emergency_sell(symbol, qty, reason):
    try:
        rule = SYMBOL_RULES[symbol]
        quantity = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), rule["step"])
        if quantity < rule["min_qty"]:
            return None
        result = CLIENT.new_order({
            "symbol": symbol,
            "side": "SELL",
            "type": "MARKET",
            "quantity": dec_str(quantity),
            "newClientOrderId": make_client_id("panic"),
            "newOrderRespType": "FULL",
        })
        log(f"خروج طارئ {symbol}: {reason}")
        return result
    except BinanceError as exc:
        log(f"فشل الخروج الطارئ {symbol}: {exc}")
        send_message(f"🆘 <b>فشل خروج طارئ {symbol_name(symbol)}</b>\n{esc(exc)}")
        return None


def execute_entry(candidate, ai_text=""):
    symbol = candidate["symbol"]
    entry_qty = Decimal("0")
    if position_exists(symbol):
        return False
    allowed, reason = circuit_allows_entry()
    if not allowed:
        log(f"تخطي {symbol}: {reason}")
        return False
    if not live_execution_allowed():
        text = entry_message(candidate, ai_text=ai_text)
        send_message("🟡 <b>إشارة مؤهلة دون تنفيذ</b>\n\n" + text)
        STATE["cooldowns"][symbol] = time.time()
        return False
    rule = SYMBOL_RULES.get(symbol)
    if not rule or rule.get("status") != "TRADING":
        return False
    try:
        account = CLIENT.account()
        free_quote = CLIENT.free_balance(rule.get("quote", "USDT"), account)
        quote = D(min(TRADE_QUOTE_USD, MAX_POSITION_USD))
        if free_quote < quote * D("1.01"):
            log(f"رصيد {rule.get('quote')} غير كافٍ لـ {symbol}")
            return False
        if quote < rule["min_notional"]:
            log(f"القيمة {quote} أقل من minNotional لـ {symbol}")
            return False
        order = CLIENT.new_order({
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": dec_str(quote),
            "newClientOrderId": make_client_id("ent"),
            "newOrderRespType": "FULL",
        })
        qty, quote_filled, entry = parse_fill(order, candidate["price"])
        entry_qty = qty
        if qty <= 0:
            raise BinanceError("أمر الدخول لم ينفذ كمية")
        protection = place_protection(
            symbol, qty, entry, candidate["stop_pct"], candidate["target_pct"], candidate["trail_bips"]
        )
        position = {
            "symbol": symbol,
            "entry": float(entry),
            "qty": dec_str(protection["qty"]),
            "quote_qty": float(quote_filled or quote),
            "target": float(protection["target"]),
            "stop": float(protection["stop"]),
            "trail_bips": int(candidate["trail_bips"]),
            "entry_order_id": order.get("orderId"),
            "order_list_id": protection.get("order_list_id"),
            "order_ids": [x.get("orderId") for x in protection.get("orders", []) if x.get("orderId") is not None],
            "stop_order_id": protection.get("stop_order_id"),
            "protection_type": protection.get("type"),
            "opened_at": time.time(),
            "score": candidate["score"],
            "stop_pct": candidate["stop_pct"],
            "target_pct": candidate["target_pct"],
            "last_check": 0.0,
            "protection_failures": 0,
        }
        with STATE_LOCK:
            STATE["positions"][symbol] = position
            STATE["metrics"]["trades"] = STATE["metrics"].get("trades", 0) + 1
            STATE["cooldowns"][symbol] = time.time()
            STATE["last_signals"] = (STATE.get("last_signals") or [])[-9:] + [{
                "symbol": symbol, "score": candidate["score"], "time": time.time(), "side": "BUY",
            }]
        save_state()
        send_message(entry_message(candidate, position=position, ai_text=ai_text), keyboard=main_keyboard())
        path = make_chart(candidate)
        if path:
            send_photo(path, f"{symbol_name(symbol)} | 1m BUY | OCO {protection.get('type')} | Trail {candidate['trail_bips']} bips")
        log(f"تم الدخول {symbol} qty={position['qty']} entry={position['entry']} protection={position['protection_type']}")
        return True
    except BinanceError as exc:
        # لا نترك الأصل بلا حماية بعد امتلاء أمر الدخول.
        if entry_qty > 0 and live_execution_allowed():
            emergency_sell(symbol, entry_qty, "فشل وضع حماية الدخول")
        log(f"فشل تنفيذ الدخول {symbol}: {exc}")
        send_message(f"⚠️ <b>فشل دخول {symbol_name(symbol)}</b>\n{esc(exc)}")
        return False
    except Exception as exc:
        log(f"خطأ دخول {symbol}: {exc}\n{traceback.format_exc()[-400:]}")
        return False


def exit_price_from_order(order, fallback):
    qty, quote, avg = parse_fill(order, fallback)
    return float(avg), qty, quote


def finalize_position(symbol, position, exit_order, reason):
    exit_price, exit_qty, exit_quote = exit_price_from_order(exit_order or {}, position.get("entry", 0))
    entry = float(position.get("entry", 0))
    quantity = float(position.get("qty", 0))
    gross_pnl = (exit_price - entry) * min(quantity, float(exit_qty) if exit_qty else quantity)
    with STATE_LOCK:
        metrics = STATE["metrics"]
        metrics["realized_pnl"] = float(metrics.get("realized_pnl", 0.0)) + gross_pnl
        if gross_pnl >= 0:
            metrics["wins"] = metrics.get("wins", 0) + 1
            metrics["consecutive_losses"] = 0
        else:
            metrics["losses"] = metrics.get("losses", 0) + 1
            metrics["consecutive_losses"] = metrics.get("consecutive_losses", 0) + 1
        STATE["positions"].pop(symbol, None)
        STATE["cooldowns"][symbol] = time.time()
    record_trade([
        datetime.now(timezone.utc).isoformat(), symbol, entry, exit_price, quantity,
        round(gross_pnl, 8), reason, position.get("score", 0), BINANCE_ENV,
    ])
    save_state()
    icon = "✅" if gross_pnl >= 0 else "🔴"
    send_message(
        f"{icon} <b>إغلاق {symbol_name(symbol)}</b>\n"
        f"السبب: {esc(reason)}\n"
        f"الدخول: <code>{fmt_price(symbol, entry)}</code> | الخروج: <code>{fmt_price(symbol, exit_price)}</code>\n"
        f"النتيجة التقريبية: <b>{gross_pnl:+.6f}$</b>"
    )


def order_status(position):
    symbol = position["symbol"]
    found = []
    for order_id in position.get("order_ids", []):
        try:
            found.append(CLIENT.get_order(symbol, order_id))
        except BinanceError as exc:
            log(f"تعذر جلب order {order_id}: {exc}")
    if position.get("stop_order_id") and position.get("stop_order_id") not in position.get("order_ids", []):
        try:
            found.append(CLIENT.get_order(symbol, position["stop_order_id"]))
        except BinanceError as exc:
            log(f"تعذر جلب stop order: {exc}")
    for order in found:
        if order.get("status") == "FILLED" and D(order.get("executedQty", "0")) > 0:
            return order
    return None


def monitor_position(symbol, position):
    now = time.time()
    if now - position.get("last_check", 0.0) < MANAGE_EVERY:
        return
    position["last_check"] = now
    filled = order_status(position)
    if filled:
        finalize_position(symbol, position, filled, "أمر حماية Binance تم تنفيذه")
        return
    # في وضع STOP fallback لا يوجد هدف على المنصة؛ يراقبه البوت ويخرج Market عند الوصول.
    if position.get("protection_type") == "STOP":
        try:
            ticker = CLIENT.book_ticker(symbol)
            last = (ticker["bid"] + ticker["ask"]) / 2.0
            if last >= float(position["target"]):
                try:
                    CLIENT.cancel_order(symbol, position.get("stop_order_id"))
                except BinanceError:
                    pass
                exit_order = emergency_sell(symbol, D(position["qty"]), "تحقق هدف السكالبينج")
                if exit_order:
                    finalize_position(symbol, position, exit_order, "هدف يدوي بعد حماية بديلة")
        except BinanceError as exc:
            log(f"خطأ مراقبة {symbol}: {exc}")
    # إذا اختفى الأمر الوقائي دون امتلاء، أعد الحماية مرة واحدة ثم اخرج عند الفشل.
    if position.get("protection_type") == "OCO" and position.get("order_list_id"):
        try:
            listing = CLIENT.order_list(position["order_list_id"])
            status = listing.get("listOrderStatus")
            if status not in ("EXECUTING", "EXEC_STARTED"):
                position["protection_failures"] = position.get("protection_failures", 0) + 1
                if position["protection_failures"] >= 2:
                    exit_order = emergency_sell(symbol, D(position["qty"]), "اختفاء حماية OCO")
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
        if symbol not in SYMBOLS:
            continue
        try:
            CLIENT.cancel_all(symbol)
            log(f"أُلغيَت الأوامر المفتوحة: {symbol}")
        except BinanceError as exc:
            log(f"تعذر إلغاء {symbol}: {exc}")


def panic_close_all():
    cancel_all_orders()
    for symbol, position in list(STATE.get("positions", {}).items()):
        order = emergency_sell(symbol, D(position.get("qty", 0)), "أمر PANIC من المستخدم")
        if order:
            finalize_position(symbol, position, order, "PANIC")


# ══════════════════════════════════════════════════════════════════════════════
# 10) الفحص وإصدار الدخول
# ══════════════════════════════════════════════════════════════════════════════


def candidate_allowed(candidate):
    symbol = candidate["symbol"]
    if position_exists(symbol):
        return False
    last = STATE.get("cooldowns", {}).get(symbol, 0.0)
    if time.time() - last < SYMBOL_COOLDOWN:
        return False
    allowed, _ = circuit_allows_entry()
    return allowed


def process_candidate(candidate):
    if not candidate_allowed(candidate):
        return False
    ai_text = ""
    if AI_GATE_ENABLED:
        news, news_ok = fetch_news(candidate["symbol"])
        if REQUIRE_NEWS and not news_ok:
            log(f"حجب {candidate['symbol']}: الأخبار غير متاحة")
            return False
        approved, ai_text = ai_veto(candidate, news)
        if not approved:
            log(f"حجب {candidate['symbol']}: {ai_text}")
            STATE["cooldowns"][candidate["symbol"]] = time.time()
            return False
    return execute_entry(candidate, ai_text=ai_text)


def run_scan(force=False):
    if not SCAN_LOCK.acquire(blocking=False):
        return None
    try:
        allowed, reason = circuit_allows_entry()
        if not allowed and not force:
            log(f"الفحص بلا دخول: {reason}")
            return None
        btc_frames = fetch_frames(LEADER)
        if not btc_frames:
            log("فشل تحميل BTC")
            return None
        try:
            tickers = CLIENT.ticker_24h(SYMBOLS)
        except BinanceError as exc:
            log(f"فشل ticker24h: {exc}")
            return None
        candidates = []
        for symbol in SYMBOLS:
            if symbol not in SYMBOL_RULES or SYMBOL_RULES[symbol].get("status") != "TRADING":
                continue
            if position_exists(symbol):
                continue
            try:
                frames = fetch_frames(symbol)
                if not frames:
                    continue
                quote_volume = tickers.get(symbol, {}).get("quote_volume", 0.0)
                candidate = make_candidate(symbol, frames, btc_frames, quote_volume)
                if candidate:
                    candidates.append(candidate)
                time.sleep(0.10)
            except BinanceError as exc:
                log(f"تحليل {symbol}: {exc}")
            except Exception as exc:
                log(f"خطأ {symbol}: {exc}")
        candidates.sort(key=lambda item: item["score"], reverse=True)
        if candidates:
            process_candidate(candidates[0])
        STATE["last_scan"] = time.time()
        save_state()
        log(f"انتهى الفحص؛ مرشحون: {len(candidates)}")
        return candidates
    except Exception as exc:
        log(f"خطأ فحص عام: {exc}\n{traceback.format_exc()[-500:]}")
        return None
    finally:
        SCAN_LOCK.release()


# ══════════════════════════════════════════════════════════════════════════════
# 11) Telegram commands/polling
# ══════════════════════════════════════════════════════════════════════════════


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
        send_message("⏸ تم إيقاف الدخولات الجديدة؛ ستستمر إدارة المراكز.", main_keyboard(), chat)
    elif data == "resume":
        STATE["paused"] = False
        save_state()
        send_message("▶ تم استئناف الدخولات.", main_keyboard(), chat)
    elif data == "cancelall":
        threading.Thread(target=cancel_all_orders, daemon=True).start()
        send_message("🧯 جارٍ إلغاء الأوامر المفتوحة دون بيع الأصول.", main_keyboard(), chat)
    elif data == "help":
        send_message(HELP_TEXT, main_keyboard(), chat)


def handle_command(text, chat):
    command, _, argument = text.partition(" ")
    command = command.split("@", 1)[0].lower()
    if command in ("/start", "/menu"):
        send_message("🎛️ <b>NOVA SCALP AUTO</b>\nاختر عملية:", main_keyboard(), chat)
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
        send_message("🧯 جارٍ إلغاء الأوامر المفتوحة دون بيع الأصول.", main_keyboard(), chat)
    elif command == "/panic":
        threading.Thread(target=panic_close_all, daemon=True).start()
        send_message("🆘 بدأ PANIC: إلغاء الأوامر ومحاولة إغلاق مراكز البوت.", main_keyboard(), chat)
    elif command == "/kill":
        ensure_dirs()
        with open(KILL_SWITCH_FILE, "w", encoding="utf-8") as handle:
            handle.write(datetime.now(timezone.utc).isoformat())
        send_message("🛑 تم إنشاء STOP_TRADING؛ لن يدخل البوت صفقات جديدة.", main_keyboard(), chat)
    elif command == "/unkill":
        try:
            os.remove(KILL_SWITCH_FILE)
        except OSError:
            pass
        send_message("✅ أُزيل قاطع STOP_TRADING.", main_keyboard(), chat)
    else:
        send_message("أمر غير معروف؛ استخدم /help", main_keyboard(), chat)


def poll_telegram_once():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    result = tg_call("getUpdates", {
        "offset": STATE.get("offset", 0),
        "timeout": TELEGRAM_POLL_TIMEOUT,
        "allowed_updates": ["message", "callback_query"],
    }, retries=1)
    if not result:
        return
    for update in result:
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
# 12) اختبار ذاتي وتشغيل
# ══════════════════════════════════════════════════════════════════════════════


def selftest():
    print("NOVA SCALP AUTO SELFTEST")
    random.seed(9)
    n = 300
    closes, highs, lows, opens, volumes = [], [], [], [], []
    price = 100.0
    for _ in range(n):
        price += random.gauss(0.05, 0.45)
        price = max(price, 20.0)
        op = price
        cl = max(20.0, price + random.gauss(0.04, 0.25))
        hi = max(op, cl) + abs(random.gauss(0.12, 0.08))
        lo = min(op, cl) - abs(random.gauss(0.12, 0.08))
        opens.append(op); closes.append(cl); highs.append(hi); lows.append(lo)
        volumes.append(abs(random.gauss(1000.0, 100.0)))
        price = cl
    check_results = []

    def check(name, value):
        check_results.append(bool(value))
        print(("✅ " if value else "❌ ") + name)

    check("EMA", last_valid(ema(closes, 21)) is not None)
    ml, ms, mh = macd(closes, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    check("MACD", last_valid(ml) is not None and last_valid(ms) is not None and last_valid(mh) is not None)
    rs = rsi(closes, RSI_PERIOD)
    check("RSI", last_valid(rs) is not None and 0 <= last_valid(rs) <= 100)
    at = atr(highs, lows, closes, ATR_PERIOD)
    check("ATR", last_valid(at) > 0)
    vw = vwap(highs, lows, closes, volumes, 24)
    check("VWAP", last_valid(vw) > 0)
    raw = {
        "t": [int(time.time() * 1000) - (n - i) * 60000 for i in range(n)],
        "o": opens, "h": highs, "l": lows, "c": closes, "v": volumes,
        "qv": [x * 100 for x in volumes], "live": closes[-1],
    }
    frame = analyze_frame(raw, "1m")
    check("تحليل الفريم", frame is not None and frame["quality"]["ok"])
    check("Decimal rounding", round_step(D("1.23456"), D("0.001")) == D("1.234"))
    print("النتيجة: " + ("ALL PASS ✅" if all(check_results) else "FAIL ❌"))
    return 0 if all(check_results) else 1


def startup_checks():
    if BINANCE_ENV == "live" and LIVE_CONFIRM != "I_UNDERSTAND_SPOT_RISK":
        raise SystemExit("لمنع التشغيل الخطير: live يتطلب LIVE_TRADING_CONFIRM=I_UNDERSTAND_SPOT_RISK")
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        log("مفاتيح Binance غير موجودة؛ لن تُرسل أوامر")
    try:
        CLIENT.sync_time()
        info = CLIENT.exchange_info()
        prepare_symbol_rules(info)
        if BINANCE_API_KEY and BINANCE_API_SECRET:
            CLIENT.account()
            log("اختبار الحساب الموقّع: OK")
    except BinanceError as exc:
        log(f"فشل اتصال Binance: {exc}")
        if not DRY_RUN:
            raise


def main():
    global DRY_RUN
    args = set(sys.argv[1:])
    ensure_dirs()
    if "--selftest" in args:
        raise SystemExit(selftest())
    if "--dry-run" in args:
        DRY_RUN = True
    load_state()
    startup_checks()
    if not live_execution_allowed():
        log("الوضع الحالي لا يسمح بتنفيذ أوامر؛ ستظهر الإشارات فقط")
    if "--once" in args:
        run_scan(force=True)
        manage_positions()
        return
    send_message(
        f"🚀 <b>تم تشغيل NOVA SCALP AUTO</b>\n"
        f"البيئة: {'TESTNET' if BINANCE_ENV == 'testnet' else 'LIVE'} | Spot فقط\n"
        f"التنفيذ: {'مفعّل' if live_execution_allowed() else 'غير مفعّل'}\n"
        "الاستراتيجية: 1m + 5m + 15m + BTC + حماية OCO.\n"
        "/menu لفتح لوحة التحكم.",
        main_keyboard(),
    )
    threading.Thread(target=telegram_loop, daemon=True, name="telegram-loop").start()
    last_scan = 0.0
    last_manage = 0.0
    while True:
        try:
            now = time.time()
            if not STATE.get("paused") and now - last_scan >= SCAN_EVERY:
                last_scan = now
                threading.Thread(target=run_scan, daemon=True).start()
            if now - last_manage >= MANAGE_EVERY:
                last_manage = now
                manage_positions()
            if now - STATE.get("last_heartbeat", 0.0) > 12 * 3600:
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
