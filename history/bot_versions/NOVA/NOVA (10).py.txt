#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA RADAR v6.0
نظام رادار ومحاكاة تداول متعدد الأطر الزمنية يعمل على Termux.

المزايا:
- requests فقط للاتصال بالشبكات: Binance / Telegram / CryptoCompare / Gemini.
- محرك المؤشرات مكتوب ببايثون النقي: EMA, RSI, MACD, ATR, Bollinger, VWAP.
- فحص جودة البيانات، السيولة، Volume Spikes، الحركات الشاذة، وLiquidity Sweeps.
- إشارات قاع/قمة على 15m أو 1h، مع فلترة 4h و1d وقائد BTC.
- محاكاة Trailing Stop Buy/Sell: لا ينفذ أوامر حقيقية في Binance.
- تقارير Telegram وشارتات matplotlib اختيارية.
- ذاكرة JSON وسجل CSV، مع اختبار ذاتي دون اتصال.

تثبيت Termux:
    pkg update -y
    pkg install python -y
    pip install requests matplotlib

الإعداد الآمن قبل التشغيل، ولا تضع المفاتيح داخل الملف:
    export TELEGRAM_BOT_TOKEN='__REDACTED__'
    export TELEGRAM_CHAT_ID='ضع_معرف_المحادثة_هنا'
    export GEMINI_API_KEY='__REDACTED__'

تشغيل:
    python bot.py
    python bot.py --once       # فحص واحد، ويطبع رسائل المحاكاة بدلاً من إرسالها
    python bot.py --selftest   # اختبار المحرك الرياضي دون شبكة

تنبيه: هذا النظام إنذاري ومحاكاة فقط، ولا يرسل أوامر شراء/بيع إلى Binance.
"""

import csv
import glob
import hashlib
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
from collections import deque
from datetime import datetime, timezone

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


def env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return float(default)


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


# لا توجد أسرار ثابتة داخل الملف.
TELEGRAM_TOKEN = __REDACTED__"TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

LEADER = "BTCUSDT"
COINS = [
    "SOLUSDT", "LINKUSDT", "RENDERUSDT", "TONUSDT", "FILUSDT",
    "ATOMUSDT", "VETUSDT", "XLMUSDT", "HNTUSDT", "IMXUSDT",
]
SYMBOLS = [LEADER] + COINS

# بيانات عامة
BINANCE_HOSTS = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api1.binance.com",
    "https://api2.binance.com",
]
BINANCE_INTERVALS = {"15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}

# حدود جودة البيانات والإشارات
MIN_CANDLES = 90
KLINE_LIMIT = 260
MIN_VOLUME_SPIKE = env_float("MIN_VOLUME_SPIKE", 1.50)
MIN_24H_LIQUIDITY_USD = env_float("MIN_24H_LIQUIDITY_USD", 500000)
FLASH_MOVE_PCT = env_float("FLASH_MOVE_PCT", 7.0)
FLASH_RANGE_ATR = env_float("FLASH_RANGE_ATR", 6.0)
MIN_SCORE = env_float("MIN_SIGNAL_SCORE", 62.0)
MAX_SIGNALS_PER_SCAN = env_int("MAX_SIGNALS_PER_SCAN", 2)

# إدارة الإشارات والمحاكاة
SCAN_INTERVAL = env_int("SCAN_INTERVAL", 180)
MANAGE_INTERVAL = env_int("MANAGE_INTERVAL", 15)
TELEGRAM_POLL_TIMEOUT = env_int("TELEGRAM_POLL_TIMEOUT", 25)
SIGNAL_COOLDOWN = env_int("SIGNAL_COOLDOWN", 1800)
SETUP_EXPIRY = env_int("SETUP_EXPIRY", 6 * 3600)
MAX_WAITING_SETUPS = env_int("MAX_WAITING_SETUPS", 6)
MAX_VIRTUAL_POSITIONS = env_int("MAX_VIRTUAL_POSITIONS", 5)
WALLET_USD = env_float("WALLET_USD", 100.0)
RISK_PER_TRADE_USD = env_float("RISK_PER_TRADE_USD", 1.0)
MAX_POSITION_USD = env_float("MAX_POSITION_USD", 25.0)

# الأخبار والذكاء الاصطناعي
REQUIRE_GEMINI = env_bool("REQUIRE_GEMINI", True)
REQUIRE_NEWS = env_bool("REQUIRE_NEWS", True)
NEWS_CACHE_SECONDS = env_int("NEWS_CACHE_SECONDS", 300)
GEMINI_MIN_INTERVAL = env_int("GEMINI_MIN_INTERVAL", 12)
GEMINI_MODELS = [
    x.strip() for x in os.getenv(
        "GEMINI_MODELS",
        "gemini-2.5-flash,gemini-2.0-flash,gemini-flash-latest",
    ).split(",") if x.strip()
]

# الرسوم والسلوك
SEND_CHARTS = env_bool("SEND_CHARTS", True)
DRY_RUN = env_bool("DRY_RUN", False)
DAILY_DIGEST = env_bool("DAILY_DIGEST", True)
DAILY_DIGEST_HOUR = env_int("DAILY_DIGEST_HOUR", 8)
CHART_BARS = env_int("CHART_BARS", 180)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "nova_data")
CHART_DIR = os.path.join(DATA_DIR, "charts")
STATE_FILE = os.path.join(DATA_DIR, "state_v6.json")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
SIGNALS_CSV = os.path.join(DATA_DIR, "signals_v6.csv")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "NOVA-RADAR/6.0 Termux"})
STATE_LOCK = threading.RLock()
SCAN_LOCK = threading.Lock()
GEMINI_LOCK = threading.Lock()
CHARTS_OK = None
TICK_SIZES = {}
LAST_GEMINI_CALL = 0.0
NEWS_CACHE = {"ts": 0.0, "items": []}


# ══════════════════════════════════════════════════════════════════════════════
# 2) السجل والذاكرة
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
        "tg_offset": 0,
        "host": None,
        "paused": False,
        "start_time": time.time(),
        "last_scan": 0.0,
        "last_manage": 0.0,
        "last_heartbeat": 0.0,
        "last_digest": "",
        "cooldowns": {},
        "last_signals": [],
        "setups": {},
        "virtual_positions": {},
        "gemini_model": None,
        "bootstrapped": False,
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
        for key in ("cooldowns", "setups", "virtual_positions"):
            if not isinstance(base.get(key), dict):
                base[key] = {}
        if not isinstance(base.get("last_signals"), list):
            base["last_signals"] = []
        STATE = base
        log(
            f"ذاكرة محمّلة: {len(STATE['setups'])} إعدادات تنتظر التفعيل، "
            f"{len(STATE['virtual_positions'])} محاكاة نشطة"
        )
    except FileNotFoundError:
        log("لا توجد ذاكرة سابقة؛ بداية جديدة")
    except Exception as exc:
        log(f"تعذر تحميل الذاكرة، ستبدأ نسخة جديدة: {exc}")


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


def csv_signal(row):
    try:
        ensure_dirs()
        fresh = not os.path.exists(SIGNALS_CSV)
        with open(SIGNALS_CSV, "a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            if fresh:
                writer.writerow([
                    "time", "symbol", "side", "timeframe", "price", "trail_pct",
                    "score", "ai_verdict", "news_count",
                ])
            writer.writerow(row)
    except Exception as exc:
        log(f"تعذر كتابة CSV: {exc}")


def esc(value):
    return html.escape(str(value))


def symbol_name(symbol):
    return symbol.replace("USDT", "/USDT")


def pct(value):
    return f"{value:+.2f}%"


def clamp(value, low, high):
    return max(low, min(high, value))


# ══════════════════════════════════════════════════════════════════════════════
# 3) محرك الرياضيات النقي
# ══════════════════════════════════════════════════════════════════════════════


def sma_series(values, period):
    result = [None] * len(values)
    if period <= 0 or len(values) < period:
        return result
    total = sum(values[:period])
    result[period - 1] = total / period
    for i in range(period, len(values)):
        total += values[i] - values[i - period]
        result[i] = total / period
    return result


def ema_series(values, period):
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


def rsi_series(closes, period=14):
    result = [None] * len(closes)
    if len(closes) < period + 1:
        return result
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    average_gain = gains / period
    average_loss = losses / period
    result[period] = 100.0 if average_loss == 0 else 100.0 - 100.0 / (
        1.0 + average_gain / average_loss
    )
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        average_gain = (average_gain * (period - 1) + max(change, 0.0)) / period
        average_loss = (average_loss * (period - 1) + max(-change, 0.0)) / period
        result[i] = 100.0 if average_loss == 0 else 100.0 - 100.0 / (
            1.0 + average_gain / average_loss
        )
    return result


def macd_series(closes, fast=12, slow=26, signal=9):
    fast_ema = ema_series(closes, fast)
    slow_ema = ema_series(closes, slow)
    line = [
        None if fast_ema[i] is None or slow_ema[i] is None
        else fast_ema[i] - slow_ema[i]
        for i in range(len(closes))
    ]
    valid_line = [value for value in line if value is not None]
    valid_signal = ema_series(valid_line, signal)
    signal_line = [None] * len(closes)
    pointer = 0
    for i, value in enumerate(line):
        if value is not None:
            signal_line[i] = valid_signal[pointer]
            pointer += 1
    histogram = [
        None if line[i] is None or signal_line[i] is None
        else line[i] - signal_line[i]
        for i in range(len(closes))
    ]
    return line, signal_line, histogram


def true_range_series(highs, lows, closes):
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


def atr_series(highs, lows, closes, period=14):
    result = [None] * len(closes)
    if len(closes) < period:
        return result
    trs = true_range_series(highs, lows, closes)
    current = sum(trs[:period]) / period
    result[period - 1] = current
    for i in range(period, len(trs)):
        current = (current * (period - 1) + trs[i]) / period
        result[i] = current
    return result


def bollinger_series(closes, period=20, multiplier=2.0):
    upper = [None] * len(closes)
    middle = [None] * len(closes)
    lower = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        mean = sum(window) / period
        deviation = statistics.pstdev(window)
        middle[i] = mean
        upper[i] = mean + multiplier * deviation
        lower[i] = mean - multiplier * deviation
    return upper, middle, lower


def vwap_series(highs, lows, closes, volumes, period=24):
    result = [None] * len(closes)
    if len(closes) < period:
        return result
    for i in range(period - 1, len(closes)):
        pv = 0.0
        volume_total = 0.0
        for j in range(i - period + 1, i + 1):
            typical = (highs[j] + lows[j] + closes[j]) / 3.0
            pv += typical * volumes[j]
            volume_total += volumes[j]
        result[i] = pv / volume_total if volume_total > 0 else None
    return result


def adx_series(highs, lows, closes, period=14):
    """ADX مبسط بطريقة وايلدر، يعيد DI+ وDI- وADX."""
    n = len(closes)
    di_plus = [None] * n
    di_minus = [None] * n
    adx = [None] * n
    if n < period * 2 + 1:
        return di_plus, di_minus, adx
    trs = []
    plus_dm = []
    minus_dm = []
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
        trs.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    tr_sum = sum(trs[:period])
    plus_sum = sum(plus_dm[:period])
    minus_sum = sum(minus_dm[:period])
    dx_values = []
    for i in range(period, len(trs)):
        tr_sum = tr_sum - tr_sum / period + trs[i]
        plus_sum = plus_sum - plus_sum / period + plus_dm[i]
        minus_sum = minus_sum - minus_sum / period + minus_dm[i]
        if tr_sum <= 0:
            continue
        pdi = 100.0 * plus_sum / tr_sum
        mdi = 100.0 * minus_sum / tr_sum
        di_plus[i + 1] = pdi
        di_minus[i + 1] = mdi
        denominator = pdi + mdi
        dx = 100.0 * abs(pdi - mdi) / denominator if denominator else 0.0
        dx_values.append((i + 1, dx))
    if len(dx_values) < period:
        return di_plus, di_minus, adx
    current = sum(value for _, value in dx_values[:period]) / period
    adx[dx_values[period - 1][0]] = current
    for j in range(period, len(dx_values)):
        current = (current * (period - 1) + dx_values[j][1]) / period
        adx[dx_values[j][0]] = current
    return di_plus, di_minus, adx


def last_value(series, default=None):
    for value in reversed(series):
        if value is not None:
            return value
    return default


def recent_cross(series_a, series_b, direction="up", bars=4):
    start = max(1, len(series_a) - bars)
    for i in range(start, len(series_a)):
        if None in (series_a[i - 1], series_b[i - 1], series_a[i], series_b[i]):
            continue
        if direction == "up" and series_a[i - 1] <= series_b[i - 1] and series_a[i] > series_b[i]:
            return True
        if direction == "down" and series_a[i - 1] >= series_b[i - 1] and series_a[i] < series_b[i]:
            return True
    return False


def trend_from_closes(closes):
    e20 = last_value(ema_series(closes, 20))
    e50 = last_value(ema_series(closes, 50))
    e200 = last_value(ema_series(closes, 200))
    price = closes[-1] if closes else 0.0
    if e20 is None or e50 is None:
        return "side", e20, e50, e200
    if e200 is not None and price > e20 > e50 > e200:
        return "up", e20, e50, e200
    if e200 is not None and price < e20 < e50 < e200:
        return "down", e20, e50, e200
    if price > e20 > e50:
        return "up", e20, e50, e200
    if price < e20 < e50:
        return "down", e20, e50, e200
    return "side", e20, e50, e200


# ══════════════════════════════════════════════════════════════════════════════
# 4) بنية الشموع وفحوص السلامة
# ══════════════════════════════════════════════════════════════════════════════


def candle_rejection(opens, highs, lows, closes):
    """قياس الذيل والرفض السعري للشمعة المغلقة الأخيرة."""
    o, h, low, c = opens[-1], highs[-1], lows[-1], closes[-1]
    candle_range = max(h - low, 1e-12)
    body = abs(c - o)
    lower_wick = min(o, c) - low
    upper_wick = h - max(o, c)
    close_position = (c - low) / candle_range
    return {
        "range": candle_range,
        "body": body,
        "lower_wick": lower_wick,
        "upper_wick": upper_wick,
        "lower_ratio": lower_wick / candle_range,
        "upper_ratio": upper_wick / candle_range,
        "close_position": close_position,
        "bullish": lower_wick / candle_range >= 0.42 and close_position >= 0.55,
        "bearish": upper_wick / candle_range >= 0.42 and close_position <= 0.45,
    }


def liquidity_sweep(highs, lows, closes, lookback=12):
    """يكتشف كسر قاع/قمة سابقة ثم الإغلاق داخل المستوى، كإشارة صيد سيولة."""
    if len(closes) < lookback + 2:
        return False, False, None, None
    previous_lows = lows[-lookback - 1:-1]
    previous_highs = highs[-lookback - 1:-1]
    prior_low = min(previous_lows)
    prior_high = max(previous_highs)
    current_low = lows[-1]
    current_high = highs[-1]
    bullish = current_low < prior_low and closes[-1] > prior_low
    bearish = current_high > prior_high and closes[-1] < prior_high
    return bullish, bearish, prior_low, prior_high


def valid_ohlcv(data, interval):
    errors = []
    required = ("t", "o", "h", "l", "c", "v", "qv")
    if not data or any(key not in data for key in required):
        return False, ["بيانات ناقصة"]
    n = len(data["c"])
    if n < MIN_CANDLES:
        errors.append(f"عدد الشموع {n} أقل من الحد")
    lengths = {len(data[key]) for key in required}
    if len(lengths) != 1:
        errors.append("أطوال مصفوفات OHLCV غير متساوية")
    for i in range(n):
        try:
            if not all(math.isfinite(float(data[key][i])) for key in ("o", "h", "l", "c", "v", "qv")):
                errors.append("رقم غير صالح")
                break
            if data["h"][i] < max(data["o"][i], data["c"][i]) or data["l"][i] > min(data["o"][i], data["c"][i]):
                errors.append("OHLC غير منطقي")
                break
            if data["v"][i] < 0 or data["qv"][i] < 0:
                errors.append("حجم سالب")
                break
        except (TypeError, ValueError, IndexError):
            errors.append("شمعة غير قابلة للقراءة")
            break
    for i in range(1, n):
        if data["t"][i] <= data["t"][i - 1]:
            errors.append("الطوابع الزمنية غير مرتبة")
            break
    # آخر شمعة قد تكون مفتوحة، لذلك نقيس التأخر بمرتين من الفريم.
    now_ms = int(time.time() * 1000)
    if n and now_ms - int(data["t"][-1]) > BINANCE_INTERVALS[interval] * 1000 * 3:
        errors.append("البيانات قديمة")
    return not errors, errors


def flash_event(highs, lows, closes, atr):
    if len(closes) < 2 or not atr or atr <= 0:
        return False, ""
    move_pct = abs(closes[-1] / closes[-2] - 1.0) * 100.0
    range_multiple = (highs[-1] - lows[-1]) / atr
    if move_pct >= FLASH_MOVE_PCT:
        return True, f"حركة جسم {move_pct:.1f}% في شمعة واحدة"
    if range_multiple >= FLASH_RANGE_ATR:
        return True, f"مدى الشمعة {range_multiple:.1f}× ATR"
    return False, ""


def data_quality(data, interval, atr, side=None):
    valid, errors = valid_ohlcv(data, interval)
    closes = data["c"][:-1]  # الشموع المغلقة فقط
    highs = data["h"][:-1]
    lows = data["l"][:-1]
    if len(closes) < MIN_CANDLES:
        return {"ok": False, "errors": errors or ["لا توجد شموع مغلقة كافية"]}
    is_flash, flash_reason = flash_event(highs, lows, closes, atr)
    bullish_sweep, bearish_sweep, prior_low, prior_high = liquidity_sweep(highs, lows, closes)
    rejection = candle_rejection(
        data["o"][:-1], highs, lows, closes
    )
    volume_window = data["v"][:-1]
    baseline = volume_window[-21:-1]
    average_volume = sum(baseline) / len(baseline) if baseline else 0.0
    volume_ratio = volume_window[-1] / average_volume if average_volume > 0 else 0.0
    volume_spike = volume_ratio >= MIN_VOLUME_SPIKE
    if side == "BUY":
        sweep_ok = bullish_sweep or rejection["bullish"]
    elif side == "SELL":
        sweep_ok = bearish_sweep or rejection["bearish"]
    else:
        sweep_ok = bullish_sweep or bearish_sweep or rejection["bullish"] or rejection["bearish"]
    errors = list(errors)
    if is_flash:
        errors.append(f"حركة شاذة: {flash_reason}")
    return {
        "ok": valid and not is_flash,
        "errors": errors,
        "flash": is_flash,
        "flash_reason": flash_reason,
        "bullish_sweep": bullish_sweep,
        "bearish_sweep": bearish_sweep,
        "prior_low": prior_low,
        "prior_high": prior_high,
        "rejection": rejection,
        "volume_ratio": volume_ratio,
        "volume_spike": volume_spike,
        "sweep_ok": sweep_ok,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5) Binance العام عبر requests
# ══════════════════════════════════════════════════════════════════════════════


def binance_get(path, params=None, timeout=12):
    hosts = []
    preferred = STATE.get("host")
    if preferred:
        hosts.append(preferred)
    hosts.extend(host for host in BINANCE_HOSTS if host not in hosts)
    for host in hosts:
        try:
            response = SESSION.get(host + path, params=params, timeout=timeout)
            if response.status_code == 200:
                STATE["host"] = host
                return response.json()
            if response.status_code in (418, 429):
                time.sleep(2.0)
        except requests.RequestException:
            continue
        except ValueError:
            continue
    return None


def load_tick_sizes():
    global TICK_SIZES
    params = {"symbols": json.dumps(SYMBOLS, separators=(",", ":"))}
    payload = binance_get("/api/v3/exchangeInfo", params=params)
    if not isinstance(payload, dict):
        log("تعذر جلب دقة الأسعار؛ سيستخدم النظام السعر الخام")
        return
    for item in payload.get("symbols", []):
        symbol = item.get("symbol")
        for rule in item.get("filters", []):
            if rule.get("filterType") == "PRICE_FILTER":
                try:
                    TICK_SIZES[symbol] = float(rule["tickSize"])
                except (TypeError, ValueError):
                    pass
    log(f"دقة الأسعار جاهزة: {len(TICK_SIZES)} زوج")


def round_tick(symbol, price, mode="nearest"):
    tick = TICK_SIZES.get(symbol)
    if not tick or price is None or price <= 0:
        return price
    quotient = price / tick
    if mode == "down":
        quotient = math.floor(quotient)
    elif mode == "up":
        quotient = math.ceil(quotient)
    else:
        quotient = round(quotient)
    return quotient * tick


def price_decimals(symbol, price):
    tick = TICK_SIZES.get(symbol)
    if tick and tick < 1:
        decimals = 0
        value = tick
        while value < 0.999999 and decimals < 10:
            value *= 10.0
            decimals += 1
        return decimals
    if price >= 1000:
        return 2
    if price >= 1:
        return 4
    return 7


def fmt_price(symbol, price):
    if price is None:
        return "—"
    return f"{price:.{price_decimals(symbol, price)}f}"


def fetch_klines(symbol, interval, limit=KLINE_LIMIT):
    payload = binance_get(
        "/api/v3/klines",
        {"symbol": symbol, "interval": interval, "limit": limit},
    )
    if not isinstance(payload, list) or len(payload) < MIN_CANDLES:
        return None
    try:
        result = {
            "t": [int(row[0]) for row in payload],
            "o": [float(row[1]) for row in payload],
            "h": [float(row[2]) for row in payload],
            "l": [float(row[3]) for row in payload],
            "c": [float(row[4]) for row in payload],
            "v": [float(row[5]) for row in payload],
            "qv": [float(row[7]) for row in payload],
            "live": float(payload[-1][4]),
        }
        return result
    except (IndexError, TypeError, ValueError):
        return None


def get_ticker(symbol):
    payload = binance_get("/api/v3/ticker/price", {"symbol": symbol}, timeout=8)
    try:
        return float(payload["price"]) if payload and "price" in payload else None
    except (TypeError, ValueError):
        return None


def get_24h_tickers():
    payload = binance_get(
        "/api/v3/ticker/24hr",
        {"symbols": json.dumps(SYMBOLS, separators=(",", ":"))},
        timeout=15,
    )
    if not isinstance(payload, list):
        return {}
    result = {}
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


# ══════════════════════════════════════════════════════════════════════════════
# 6) تحليل الفريمات وقائد BTC
# ══════════════════════════════════════════════════════════════════════════════


def analyze_timeframe(symbol, interval):
    raw = fetch_klines(symbol, interval)
    if not raw:
        return None
    closed = {key: values[:-1] for key, values in raw.items() if isinstance(values, list)}
    for key in ("t", "o", "h", "l", "c", "v", "qv"):
        if key not in closed or len(closed[key]) < MIN_CANDLES:
            return None
    c = closed["c"]
    h = closed["h"]
    l = closed["l"]
    o = closed["o"]
    v = closed["v"]
    qv = closed["qv"]
    rsi = rsi_series(c, 14)
    macd_line, macd_signal, histogram = macd_series(c)
    atr = last_value(atr_series(h, l, c, 14), 0.0) or 0.0
    bb_upper, bb_middle, bb_lower = bollinger_series(c, 20, 2.0)
    vwaps = vwap_series(h, l, c, v, 24)
    di_plus, di_minus, adx = adx_series(h, l, c, 14)
    trend, ema20, ema50, ema200 = trend_from_closes(c)
    quality = data_quality(raw, interval, atr)
    baseline_qv = qv[-25:-1]
    qv_24h = sum(qv[-97:]) if interval == "15m" and len(qv) >= 97 else (
        sum(qv[-25:]) if interval == "1h" and len(qv) >= 25 else sum(qv[-6:])
    )
    return {
        "symbol": symbol,
        "interval": interval,
        "raw": raw,
        "t": closed["t"],
        "o": o,
        "h": h,
        "l": l,
        "c": c,
        "v": v,
        "qv": qv,
        "live": raw["live"],
        "rsi_series": rsi,
        "rsi": last_value(rsi, 50.0),
        "rsi_prev": rsi[-2] if len(rsi) > 1 and rsi[-2] is not None else last_value(rsi, 50.0),
        "macd_line_series": macd_line,
        "macd_signal_series": macd_signal,
        "histogram_series": histogram,
        "macd": last_value(macd_line, 0.0),
        "macd_signal": last_value(macd_signal, 0.0),
        "hist": last_value(histogram, 0.0),
        "hist_prev": histogram[-2] if len(histogram) > 1 and histogram[-2] is not None else 0.0,
        "macd_cross_up": recent_cross(macd_line, macd_signal, "up", 4),
        "macd_cross_down": recent_cross(macd_line, macd_signal, "down", 4),
        "atr": atr,
        "atr_pct": atr / c[-1] * 100.0 if c[-1] else 0.0,
        "bb_upper": last_value(bb_upper),
        "bb_middle": last_value(bb_middle),
        "bb_lower": last_value(bb_lower),
        "vwap": last_value(vwaps),
        "adx": last_value(adx, 0.0) or 0.0,
        "di_plus": last_value(di_plus, 0.0) or 0.0,
        "di_minus": last_value(di_minus, 0.0) or 0.0,
        "trend": trend,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "quality": quality,
        "volume_ratio": quality.get("volume_ratio", 0.0),
        "volume_spike": quality.get("volume_spike", False),
        "bullish_sweep": quality.get("bullish_sweep", False),
        "bearish_sweep": quality.get("bearish_sweep", False),
        "rejection": quality.get("rejection", {}),
        "qv_24h": qv_24h,
        "baseline_qv": sum(baseline_qv) / len(baseline_qv) if baseline_qv else 0.0,
    }


def analyze_btc():
    frames = {}
    for interval in ("1h", "4h", "1d"):
        frames[interval] = analyze_timeframe(LEADER, interval)
    if any(value is None for value in frames.values()):
        return {
            "symbol": LEADER,
            "regime": "unknown",
            "frames": frames,
            "live": 0.0,
            "change24": 0.0,
            "safe": False,
            "reason": "بيانات BTC غير مكتملة",
        }
    f1, f4, fd = frames["1h"], frames["4h"], frames["1d"]
    if f4["trend"] == "up" and fd["trend"] == "up" and not f4["quality"]["flash"]:
        regime = "bullish"
    elif f4["trend"] == "down" and fd["trend"] == "down":
        regime = "bearish"
    else:
        regime = "neutral"
    change24 = (f1["c"][-1] / f1["c"][-25] - 1.0) * 100.0 if len(f1["c"]) > 25 else 0.0
    safe = regime != "bearish" and not f1["quality"]["flash"] and not f4["quality"]["flash"]
    return {
        "symbol": LEADER,
        "regime": regime,
        "frames": frames,
        "live": f1["live"],
        "change24": change24,
        "safe": safe,
        "reason": "BTC غير هابط على 4h و1d" if safe else "BTC في فلتر خطر",
    }


def analyze_symbol(symbol, btc, ticker=None):
    frames = {}
    for interval in ("15m", "1h", "4h", "1d"):
        frames[interval] = analyze_timeframe(symbol, interval)
    if any(value is None for value in frames.values()):
        return None
    live = ticker or frames["15m"]["live"]
    change24 = 0.0
    if ticker is not None:
        # النسبة الأدق تبقى من الشموع المغلقة، بينما السعر الحي يستخدم للتنفيذ الافتراضي.
        c = frames["1h"]["c"]
        if len(c) > 24:
            change24 = (c[-1] / c[-25] - 1.0) * 100.0
    else:
        c = frames["1h"]["c"]
        change24 = (c[-1] / c[-25] - 1.0) * 100.0 if len(c) > 25 else 0.0
    candidates = []
    for interval in ("15m", "1h"):
        candidate = build_candidate(symbol, interval, frames[interval], frames, btc, live)
        if candidate:
            candidates.append(candidate)
    return {
        "symbol": symbol,
        "live": live,
        "change24": change24,
        "frames": frames,
        "candidates": candidates,
        "btc": btc,
    }


def build_candidate(symbol, interval, signal, frames, btc, live):
    quality = signal["quality"]
    rejection = signal["rejection"]
    buy_core = (
        signal["rsi"] < 30.0
        and (signal["macd_cross_up"] or signal["hist"] > signal["hist_prev"] and signal["hist"] < 0)
        and (signal["bullish_sweep"] or rejection.get("bullish", False))
        and signal["volume_spike"]
    )
    sell_core = (
        signal["rsi"] > 70.0
        and (signal["macd_cross_down"] or signal["hist"] < signal["hist_prev"])
        and (signal["bearish_sweep"] or rejection.get("bearish", False))
        and signal["volume_spike"]
    )
    if not buy_core and not sell_core:
        return None
    side = "BUY" if buy_core else "SELL"
    f4 = frames["4h"]
    fd = frames["1d"]
    # فلتر BTC والأطر الكبرى. القمم قد تظهر حتى في اتجاه صاعد، لكن لا نطلقها
    # إذا كان كل شيء صاعداً بلا أي ضعف أعلى إطاراً.
    if side == "BUY":
        higher_ok = btc.get("safe", False) and not (f4["trend"] == "down" and fd["trend"] == "down")
    else:
        higher_ok = not (
            btc.get("regime") == "bullish"
            and f4["trend"] == "up"
            and fd["trend"] == "up"
            and signal["macd_cross_down"] is False
        )
    if not higher_ok:
        return None
    if not quality.get("ok"):
        return None
    if signal.get("qv_24h", 0.0) < MIN_24H_LIQUIDITY_USD:
        return None
    if not quality.get("sweep_ok"):
        return None
    score = score_candidate(side, signal, frames, btc)
    if score < MIN_SCORE:
        return None
    plan = build_trailing_plan(symbol, side, live, signal, frames)
    return {
        "symbol": symbol,
        "side": side,
        "interval": interval,
        "price": live,
        "signal": signal,
        "frames": frames,
        "btc": btc,
        "score": score,
        "plan": plan,
        "generated_at": time.time(),
    }


def score_candidate(side, signal, frames, btc):
    score = 0.0
    # 20 نقطة: شرط RSI
    score += 20.0 if (signal["rsi"] < 30 if side == "BUY" else signal["rsi"] > 70) else 0.0
    # 20 نقطة: MACD
    if side == "BUY":
        score += 20.0 if signal["macd_cross_up"] else 12.0 if signal["hist"] > signal["hist_prev"] else 0.0
    else:
        score += 20.0 if signal["macd_cross_down"] else 12.0 if signal["hist"] < signal["hist_prev"] else 0.0
    # 15 نقطة: الحجم
    score += min(15.0, 7.5 * signal["volume_ratio"] / MIN_VOLUME_SPIKE)
    # 15 نقطة: sweep/ذيل
    sweep = signal["bullish_sweep"] if side == "BUY" else signal["bearish_sweep"]
    wick_ratio = signal["rejection"].get("lower_ratio" if side == "BUY" else "upper_ratio", 0.0)
    score += 15.0 if sweep else min(12.0, wick_ratio * 20.0)
    # 15 نقطة: اتجاه الأطر الكبرى
    f4, fd = frames["4h"], frames["1d"]
    if side == "BUY":
        score += 8.0 if f4["trend"] == "up" else 5.0 if f4["trend"] == "side" else 0.0
        score += 7.0 if fd["trend"] == "up" else 4.0 if fd["trend"] == "side" else 0.0
        score += 5.0 if btc.get("regime") == "bullish" else 2.0 if btc.get("regime") == "neutral" else 0.0
    else:
        score += 8.0 if f4["trend"] == "down" else 5.0 if f4["trend"] == "side" else 2.0
        score += 7.0 if fd["trend"] == "down" else 4.0 if fd["trend"] == "side" else 2.0
        score += 5.0 if btc.get("regime") == "bearish" else 2.0
    # 10 نقاط: ADX مع اتجاه الحركة، دون استخدامه كشرط وحيد.
    score += 10.0 if 15.0 <= signal["adx"] <= 55.0 else 5.0 if signal["adx"] < 15 else 2.0
    return round(clamp(score, 0.0, 100.0), 1)


def build_trailing_plan(symbol, side, price, signal, frames):
    atr_signal = signal["atr"]
    atr_hour = frames["1h"]["atr"]
    # يمزج تقلب فريم الإشارة مع الساعة حتى لا يكون التتبع ضيقاً جداً.
    effective_atr = max(atr_signal * 1.15, atr_hour * 0.45)
    raw_delta = effective_atr / price * 100.0 if price else 1.0
    trail_pct = round(clamp(raw_delta * 1.35, 0.35, 5.0), 2)
    risk_distance = max(effective_atr * 1.4, price * 0.008)
    if side == "BUY":
        invalidation = round_tick(symbol, price - risk_distance, "down")
    else:
        invalidation = round_tick(symbol, price + risk_distance, "up")
    position_size = min(MAX_POSITION_USD, RISK_PER_TRADE_USD / max(risk_distance / price, 0.0001))
    return {
        "entry_reference": round_tick(symbol, price, "nearest"),
        "trail_pct": trail_pct,
        "trail_bips": int(round(trail_pct * 100.0)),
        "atr": effective_atr,
        "invalidation": invalidation,
        "position_usd": round(position_size, 2),
        "risk_usd": round(position_size * risk_distance / price, 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7) CryptoCompare + Gemini
# ══════════════════════════════════════════════════════════════════════════════


def fetch_news(symbol=None):
    global NEWS_CACHE
    now = time.time()
    if now - NEWS_CACHE["ts"] < NEWS_CACHE_SECONDS:
        items = NEWS_CACHE["items"]
    else:
        try:
            response = SESSION.get(
                "https://min-api.cryptocompare.com/data/v2/news/",
                params={"lang": "EN", "sortOrder": "latest", "limit": 30},
                timeout=15,
            )
            if response.status_code != 200:
                log(f"CryptoCompare HTTP {response.status_code}")
                return [], False
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("Data"), list):
                log("CryptoCompare أعاد صيغة غير صالحة")
                return [], False
            items = payload["Data"]
            NEWS_CACHE = {"ts": now, "items": items}
        except (requests.RequestException, ValueError) as exc:
            log(f"تعذر جلب CryptoCompare: {exc}")
            return [], False
    base = symbol.replace("USDT", "").upper() if symbol else ""
    filtered = []
    for item in items:
        text = " ".join(str(item.get(key, "")) for key in ("title", "body", "categories")).upper()
        if not base or base in text or any(word in text for word in ("BITCOIN", "CRYPTO", "MARKET", "SEC", "ETF")):
            filtered.append({
                "title": str(item.get("title", ""))[:180],
                "source": str(item.get("source", ""))[:60],
                "published": int(item.get("published_on", 0) or 0),
                "url": str(item.get("url", ""))[:300],
            })
        if len(filtered) >= 8:
            break
    return filtered, True


PERSONA = (
    "أنت مدير تداول مؤسسي صارم. راجع البيانات الفنية والأخبار الحالية. "
    "إذا كان هناك خطر جوهري أو خبر قد يدمر فرصة الإشارة، أجب بكلمة إلغاء فقط. "
    "إذا كانت مقبولة، أجب بتحليل مؤسساتي صارم في سطرين فقط، بالعربية، "
    "مع ذكر الخطر الرئيسي ومستوى المتابعة. لا تقدم ضماناً ولا تنفذ أوامر."
)


def news_text(items):
    if not items:
        return "لا توجد عناوين مطابقة متاحة الآن."
    lines = []
    for item in items:
        date = ""
        if item.get("published"):
            date = datetime.fromtimestamp(item["published"], timezone.utc).strftime("%Y-%m-%d")
        lines.append(f"- {item['title']} | المصدر: {item['source']} | {date}")
    return "\n".join(lines)


def gemini_call(prompt, max_tokens=260):
    global LAST_GEMINI_CALL
    if not GEMINI_API_KEY:
        return None, "لا يوجد GEMINI_API_KEY"
    with GEMINI_LOCK:
        wait = GEMINI_MIN_INTERVAL - (time.time() - LAST_GEMINI_CALL)
        if wait > 0:
            time.sleep(wait)
        models = []
        saved_model = STATE.get("gemini_model")
        if saved_model:
            models.append(saved_model)
        models.extend(model for model in GEMINI_MODELS if model not in models)
        for model in models:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent"
            )
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": max_tokens,
                },
            }
            for attempt in range(2):
                try:
                    response = SESSION.post(
                        url,
                        params={"key": GEMINI_API_KEY},
                        json=body,
                        timeout=35,
                    )
                    LAST_GEMINI_CALL = time.time()
                    if response.status_code in (429, 500, 503):
                        time.sleep(2.5 + attempt)
                        continue
                    payload = response.json()
                    candidates = payload.get("candidates") or []
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = " ".join(str(part.get("text", "")) for part in parts).strip()
                        if text:
                            STATE["gemini_model"] = model
                            return text, None
                    break
                except (requests.RequestException, ValueError, KeyError) as exc:
                    if attempt == 1:
                        log(f"Gemini {model} تعذر: {exc}")
                    time.sleep(1.0)
    return None, "تعذر الوصول إلى Gemini"


def clean_ai(text):
    if not text:
        return ""
    text = text.replace("**", "").replace("__", "").replace("```", "").replace("`", "")
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    return "\n".join(lines)[:850]


def ai_gate(candidate, news):
    symbol = candidate["symbol"]
    signal = candidate["signal"]
    f4 = candidate["frames"]["4h"]
    fd = candidate["frames"]["1d"]
    plan = candidate["plan"]
    prompt = (
        f"{PERSONA}\n\n"
        f"العملة: {symbol_name(symbol)} | نوع الفرصة: {candidate['side']} | "
        f"فريم الإشارة: {candidate['interval']}\n"
        f"السعر الحي: {candidate['price']:.12g} | التقييم: {candidate['score']}/100\n"
        f"RSI: {signal['rsi']:.2f} | MACD: {signal['macd']:.12g} | "
        f"Histogram: {signal['hist']:.12g} (السابق {signal['hist_prev']:.12g})\n"
        f"ATR: {signal['atr']:.12g} ({signal['atr_pct']:.2f}%) | "
        f"حجم/متوسط: {signal['volume_ratio']:.2f}x | ADX: {signal['adx']:.1f}\n"
        f"Sweep صاعد: {signal['bullish_sweep']} | Sweep هابط: {signal['bearish_sweep']} | "
        f"الرفض السفلي: {signal['rejection'].get('lower_ratio', 0):.2f} | "
        f"الرفض العلوي: {signal['rejection'].get('upper_ratio', 0):.2f}\n"
        f"اتجاه 4h: {f4['trend']} | اتجاه 1d: {fd['trend']} | "
        f"BTC: {candidate['btc'].get('regime')} | BTC آمن: {candidate['btc'].get('safe')}\n"
        f"Trailing Delta: {plan['trail_pct']:.2f}% ({plan['trail_bips']} bips) | "
        f"مستوى الإلغاء الفني: {plan['invalidation']:.12g}\n\n"
        f"الأخبار الحالية من CryptoCompare:\n{news_text(news)}\n\n"
        "التزم حرفياً: إذا يوجد خطر جوهري اكتب إلغاء فقط. وإلا اكتب سطرين فقط، "
        "السطر الأول السيناريو، والسطر الثاني الخطر والمستوى الذي يراقب."
    )
    text, reason = gemini_call(prompt)
    if not text:
        if REQUIRE_GEMINI:
            return False, "حجب آمن: Gemini غير متاح"
        return True, "لم يتوفر المحلل السحابي؛ تم الاعتماد على الفلاتر الرقمية فقط"
    cleaned = clean_ai(text)
    first = cleaned.strip().lower()
    if first.startswith("إلغاء") or first.startswith("cancel") or first == "الغاء":
        return False, "Gemini ألغى الفرصة بسبب خطر خبري/فني"
    return True, cleaned


# ══════════════════════════════════════════════════════════════════════════════
# 8) خطط ورسائل Telegram
# ══════════════════════════════════════════════════════════════════════════════


def tg_call(method, payload=None, files=None, retries=3):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    for attempt in range(retries):
        try:
            if files:
                response = SESSION.post(url, data=payload or {}, files=files, timeout=35)
            else:
                response = SESSION.post(url, json=payload or {}, timeout=30)
            data = response.json()
            if data.get("ok"):
                return data.get("result")
            if response.status_code in (429, 500, 502, 503):
                time.sleep(1.5 + attempt)
        except (requests.RequestException, ValueError):
            time.sleep(1.5 + attempt)
    return None


def send_message(text, keyboard=None, chat_id=None, reply_to=None):
    if DRY_RUN or not TELEGRAM_TOKEN or not CHAT_ID:
        print("\n" + "═" * 72 + "\n[رسالة محاكاة Telegram]\n" + text + "\n" + "═" * 72)
        return True
    payload = {
        "chat_id": chat_id or CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if keyboard is not None:
        payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    return bool(tg_call("sendMessage", payload))


def send_photo(path, caption, chat_id=None):
    if DRY_RUN or not TELEGRAM_TOKEN or not CHAT_ID:
        print(f"[صورة محاكاة Telegram] {path}\n{caption}")
        return True
    try:
        with open(path, "rb") as photo:
            result = tg_call(
                "sendPhoto",
                {"chat_id": chat_id or CHAT_ID, "caption": caption[:1024]},
                files={"photo": (os.path.basename(path), photo, "image/png")},
            )
        return bool(result)
    except OSError:
        return False


def send_typing(chat_id=None):
    if TELEGRAM_TOKEN and CHAT_ID and not DRY_RUN:
        tg_call("sendChatAction", {"chat_id": chat_id or CHAT_ID, "action": "typing"}, retries=1)


def button(text, callback):
    return {"text": text, "callback_data": callback}


def menu_keyboard():
    return [
        [button("🔎 فحص السوق", "scan"), button("📡 الحالة", "status")],
        [button("🪙 العملات", "coins"), button("💲 الأسعار", "prices")],
        [button("⏸ إيقاف الفحص", "pause"), button("▶ استئناف", "resume")],
        [button("❓ المساعدة", "help")],
    ]


def coins_keyboard():
    rows, row = [], []
    for symbol in SYMBOLS:
        row.append(button(symbol.replace("USDT", ""), "coin:" + symbol))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([button("🔙 القائمة", "main")])
    return rows


def regime_ar(regime):
    return {"bullish": "🟢 صاعد", "bearish": "🔴 هابط", "neutral": "🟡 محايد", "unknown": "⚪ غير مكتمل"}.get(regime, regime)


def trend_ar(trend):
    return {"up": "صاعد ⤴", "down": "هابط ⤵", "side": "عرضي →"}.get(trend, trend)


def signal_message(candidate, ai_text, news_count):
    symbol = candidate["symbol"]
    side = candidate["side"]
    signal = candidate["signal"]
    frames = candidate["frames"]
    plan = candidate["plan"]
    direction = "قاع" if side == "BUY" else "قمة"
    emoji = "🟢" if side == "BUY" else "🔴"
    sweep = signal["bullish_sweep"] if side == "BUY" else signal["bearish_sweep"]
    wick = signal["rejection"].get("lower_ratio" if side == "BUY" else "upper_ratio", 0.0)
    lines = [
        f"{emoji} <b>إشعار {direction} — فرصة Trailing Stop {side}</b>",
        f"🔹 <b>{symbol_name(symbol)}</b> | السعر الحي: <code>{fmt_price(symbol, candidate['price'])}</code>",
        f"⏱ فريم الإشارة: <b>{candidate['interval']}</b> | قوة الإشارة: <b>{candidate['score']}/100</b>",
        "",
        "✅ <b>تأكيدات الرادار:</b>",
        f"• RSI: <code>{signal['rsi']:.1f}</code> ({'أقل من 30' if side == 'BUY' else 'أعلى من 70'})",
        f"• MACD: <code>{signal['macd']:.8g}</code> | Histogram <code>{signal['hist']:.8g}</code>",
        f"• Volume Spike: <b>{signal['volume_ratio']:.2f}×</b> المتوسط",
        f"• Liquidity Sweep: {'✅ مؤكد' if sweep else '🟡 رفض سعري'} | نسبة الذيل: <b>{wick * 100:.1f}%</b>",
        f"• Flash Check: ✅ لا توجد حركة شاذة في الشمعة المغلقة",
        "",
        "🧭 <b>فلتر الأطر الكبرى:</b>",
        f"• 4H: {trend_ar(frames['4h']['trend'])} | 1D: {trend_ar(frames['1d']['trend'])}",
        f"• BTC: {regime_ar(candidate['btc'].get('regime', 'unknown'))} | "
        f"الحالة: {'✅ آمن' if candidate['btc'].get('safe') else '⚠️ حذر'}",
        "",
        f"🛤 <b>Trailing Delta المقترح: {plan['trail_pct']:.2f}% ({plan['trail_bips']} bips)</b>",
        f"📍 نقطة المراقبة الحالية: <code>{fmt_price(symbol, candidate['price'])}</code>",
        f"⛔ مستوى الإلغاء الفني: <code>{fmt_price(symbol, plan['invalidation'])}</code>",
        f"💵 حجم محاكاة مقترح: <b>{plan['position_usd']:.2f}$</b> | مخاطرة نظرية: <b>{plan['risk_usd']:.2f}$</b>",
        "",
        "🧠 <b>فلتر Gemini + الأخبار:</b>",
        esc(ai_text) if ai_text else "تم اجتياز الفلتر الرقمي",
        f"📰 عناوين CryptoCompare المستخدمة: {news_count}",
        "",
        f"🧪 <b>المحاكاة:</b> تم تسجيل الإعداد. {'إذا استمر الهبوط' if side == 'BUY' else 'إذا استمر الصعود'} "
        f"سيحدّث النظام {'أدنى قاع' if side == 'BUY' else 'أعلى قمة'}، ثم يرسل إنذار التفعيل عند ارتداد {plan['trail_pct']:.2f}%.",
    ]
    return "\n".join(lines)


def activation_message(setup, price):
    symbol = setup["symbol"]
    side = setup["side"]
    name = symbol_name(symbol)
    if side == "BUY":
        return (
            f"🚨 <b>تم تفعيل الشراء المتحرك في السوق — {name}</b>\n\n"
            f"ارتد السعر من أدنى قاع مسجل <code>{fmt_price(symbol, setup['extreme'])}</code> "
            f"ووصل إلى <code>{fmt_price(symbol, price)}</code>.\n"
            f"Trailing Delta: <b>{setup['trail_pct']:.2f}%</b>\n\n"
            "افتح المنصة الآن وقم بإعداد أمر البيع المتحرك Trailing Stop Sell لحماية الأرباح.\n"
            "هذه رسالة محاكاة/إنذار فقط؛ لا يوجد أمر آلي مرسل إلى Binance."
        )
    return (
        f"🚨 <b>تم تفعيل البيع المتحرك في السوق — {name}</b>\n\n"
        f"هبط السعر من أعلى قمة مسجلة <code>{fmt_price(symbol, setup['extreme'])}</code> "
        f"ووصل إلى <code>{fmt_price(symbol, price)}</code>.\n"
        f"Trailing Delta: <b>{setup['trail_pct']:.2f}%</b>\n\n"
        "افتح المنصة الآن ونفّذ خطة البيع/الإغلاق المناسبة، ثم ضع Trailing Stop جديداً للكمية المتبقية.\n"
        "هذه رسالة محاكاة/إنذار فقط؛ لا يوجد أمر آلي مرسل إلى Binance."
    )


def status_message(btc=None):
    if btc is None:
        btc = analyze_btc()
    uptime = int((time.time() - STATE.get("start_time", time.time())) / 3600)
    lines = [
        "📡 <b>NOVA RADAR v6.0</b>",
        f"الحالة: {'⏸ متوقف الفحص' if STATE.get('paused') else '✅ يعمل'} | مدة التشغيل: {uptime}س",
        f"BTC: <code>{fmt_price(LEADER, btc.get('live', 0))}</code> | {regime_ar(btc.get('regime', 'unknown'))} | "
        f"24س {pct(btc.get('change24', 0))}",
        f"إعدادات تنتظر التفعيل: <b>{len(STATE.get('setups', {}))}</b>/{MAX_WAITING_SETUPS}",
        f"محاكاة مفعلة: <b>{len(STATE.get('virtual_positions', {}))}</b>/{MAX_VIRTUAL_POSITIONS}",
    ]
    for key, setup in list(STATE.get("setups", {}).items()):
        lines.append(
            f"⏳ {symbol_name(setup['symbol'])} {setup['side']} | "
            f"Extreme <code>{fmt_price(setup['symbol'], setup.get('extreme', 0))}</code> | "
            f"Trail {setup.get('trail_pct', 0):.2f}%"
        )
    for key, position in list(STATE.get("virtual_positions", {}).items()):
        price = get_ticker(position["symbol"])
        entry = position.get("entry", 0)
        change = ((price / entry) - 1.0) * 100.0 if price and entry else 0.0
        lines.append(
            f"🧪 {symbol_name(position['symbol'])} {position['side']} | "
            f"تغير المحاكاة {pct(change)}"
        )
    lines.append("\nالأوامر: /menu /scan /status /coin XLM /chart XLM /close XLM /pause /resume")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 9) الرسوم بـ matplotlib مباشرة
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
        log(f"الشارتات غير متاحة؛ ثبّت matplotlib: {exc}")
    return CHARTS_OK


def make_chart(candidate, path):
    if not chart_ready():
        return False
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    frame = candidate["signal"]
    raw = frame["raw"]
    count = min(CHART_BARS, len(raw["c"]))
    start = len(raw["c"]) - count
    o = raw["o"][start:]
    h = raw["h"][start:]
    l = raw["l"][start:]
    c = raw["c"][start:]
    v = raw["v"][start:]
    n = len(c)
    ema20 = ema_series(c, 20)
    ema50 = ema_series(c, 50)
    ema200 = ema_series(c, 200)
    upper, middle, lower = bollinger_series(c)
    rsi = rsi_series(c)
    ml, ms, hist = macd_series(c)
    volume_average = sma_series(v, 20)

    bg, panel, grid, text = "#0d1117", "#121a22", "#26313c", "#d5d9e0"
    green, red, yellow, blue, purple, orange = "#0ecb81", "#f6465d", "#f0b90b", "#4c8bf5", "#b17ce8", "#ff9f43"
    fig = plt.figure(figsize=(12.5, 9.0), dpi=110)
    fig.patch.set_facecolor(bg)
    grid_spec = fig.add_gridspec(4, 1, height_ratios=(3.4, 0.8, 1.1, 1.1), hspace=0.06,
                                  left=0.07, right=0.985, top=0.93, bottom=0.06)
    ax_price = fig.add_subplot(grid_spec[0])
    ax_volume = fig.add_subplot(grid_spec[1], sharex=ax_price)
    ax_rsi = fig.add_subplot(grid_spec[2], sharex=ax_price)
    ax_macd = fig.add_subplot(grid_spec[3], sharex=ax_price)
    for axis in (ax_price, ax_volume, ax_rsi, ax_macd):
        axis.set_facecolor(panel)
        axis.grid(True, color=grid, linewidth=0.5, alpha=0.7)
        axis.tick_params(colors=text, labelsize=8)
        for spine in axis.spines.values():
            spine.set_color(grid)

    for i in range(n):
        color = green if c[i] >= o[i] else red
        axis_low, axis_high = min(o[i], c[i]), max(o[i], c[i])
        ax_price.plot([i, i], [l[i], h[i]], color=color, linewidth=0.75)
        ax_price.add_patch(Rectangle(
            (i - 0.35, axis_low), 0.7, max(axis_high - axis_low, max(c) * 0.00001),
            facecolor=color, edgecolor=color, linewidth=0,
        ))
        ax_volume.bar(i, v[i], color=color, width=0.7)
        if hist[i] is not None:
            ax_macd.bar(i, hist[i], color=green if hist[i] >= 0 else red, width=0.7)

    for series, color, label, width in (
        (ema20, yellow, "EMA20", 1.2),
        (ema50, blue, "EMA50", 1.2),
        (ema200, purple, "EMA200", 1.5),
    ):
        xs = [i for i, value in enumerate(series) if value is not None]
        if len(xs) > 2:
            ax_price.plot(xs, [series[i] for i in xs], color=color, linewidth=width, label=label)
    xs = [i for i, value in enumerate(upper) if value is not None]
    if len(xs) > 2:
        ax_price.fill_between(xs, [lower[i] for i in xs], [upper[i] for i in xs], color=text, alpha=0.05)
        ax_price.plot(xs, [upper[i] for i in xs], color=text, linewidth=0.5, linestyle="--")
        ax_price.plot(xs, [lower[i] for i in xs], color=text, linewidth=0.5, linestyle="--")

    plan = candidate.get("plan")
    if plan:
        level_color = green if candidate["side"] == "BUY" else red
        ax_price.axhline(plan["entry_reference"], color=blue, linestyle=":", linewidth=1.0, label="Reference")
        ax_price.axhline(plan["invalidation"], color=level_color, linestyle="--", linewidth=0.9, label="Invalidation")
        ax_price.annotate(
            f"Trail {plan['trail_pct']:.2f}%",
            xy=(0.99, 0.08), xycoords="axes fraction", ha="right", color=yellow, fontsize=9,
        )
    ax_price.set_title(
        f"{symbol_name(candidate['symbol'])} | {candidate['interval']} | "
        f"{candidate['side']} | Score {candidate['score']}/100 | "
        f"4H {candidate['frames']['4h']['trend'].upper()} / 1D {candidate['frames']['1d']['trend'].upper()}",
        color=text, fontsize=12, fontweight="bold", loc="left", pad=8,
    )
    ax_price.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=text, ncol=4)
    ax_volume.plot([i for i, value in enumerate(volume_average) if value is not None],
                   [value for value in volume_average if value is not None], color=yellow, linewidth=0.8)
    ax_volume.set_ylabel("VOL", color=text, fontsize=8)

    rsi_x = [i for i, value in enumerate(rsi) if value is not None]
    ax_rsi.plot(rsi_x, [rsi[i] for i in rsi_x], color=purple, linewidth=1.2)
    ax_rsi.axhline(70, color=red, linestyle="--", linewidth=0.7)
    ax_rsi.axhline(30, color=green, linestyle="--", linewidth=0.7)
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_ylabel("RSI", color=text, fontsize=8)
    ax_rsi.annotate(f"{frame['rsi']:.1f}", xy=(0.99, 0.88), xycoords="axes fraction", color=purple, ha="right")

    macd_x = [i for i, value in enumerate(ml) if value is not None]
    ax_macd.plot(macd_x, [ml[i] for i in macd_x], color=blue, linewidth=1.0, label="MACD")
    ax_macd.plot(macd_x, [ms[i] for i in macd_x], color=orange, linewidth=0.9, label="Signal")
    ax_macd.axhline(0, color=text, linewidth=0.5)
    ax_macd.set_ylabel("MACD", color=text, fontsize=8)
    ax_macd.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=text)

    step = max(1, n // 6)
    ticks = list(range(0, n, step))
    labels = []
    interval = candidate["interval"]
    for i in ticks:
        try:
            stamp = raw["t"][start + i] / 1000.0
            labels.append(datetime.fromtimestamp(stamp).strftime("%d/%m %H:%M"))
        except (ValueError, OSError):
            labels.append("")
    ax_macd.set_xticks(ticks)
    ax_macd.set_xticklabels(labels, color=text, fontsize=8)
    try:
        ensure_dirs()
        fig.savefig(path, facecolor=bg, bbox_inches="tight")
    finally:
        plt.close(fig)
    return True


def cleanup_charts(max_age_hours=48):
    try:
        cutoff = time.time() - max_age_hours * 3600
        for path in glob.glob(os.path.join(CHART_DIR, "*.png")):
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
    except OSError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 10) المحاكاة: إعداد ينتظر الارتداد، ثم مركز افتراضي يتبع السعر
# ══════════════════════════════════════════════════════════════════════════════


def setup_key(symbol, side):
    return f"{symbol}:{side}"


def add_setup(candidate, ai_text, news_count):
    key=__REDACTED__"symbol"], candidate["side"])
    now = time.time()
    with STATE_LOCK:
        if key in STATE["setups"] or key in STATE["virtual_positions"]:
            return False
        if len(STATE["setups"]) >= MAX_WAITING_SETUPS:
            return False
        setup = {
            "key": key,
            "symbol": candidate["symbol"],
            "side": candidate["side"],
            "interval": candidate["interval"],
            "signal_price": candidate["price"],
            "extreme": candidate["price"],
            "trail_pct": candidate["plan"]["trail_pct"],
            "score": candidate["score"],
            "created_at": now,
            "expires_at": now + SETUP_EXPIRY,
            "ai_text": ai_text[:850],
            "news_count": news_count,
            "last_price": candidate["price"],
        }
        STATE["setups"][key] = setup
        STATE["cooldowns"][key] = now
        STATE["last_signals"] = (STATE.get("last_signals") or [])[-9:] + [{
            "symbol": candidate["symbol"],
            "side": candidate["side"],
            "interval": candidate["interval"],
            "score": candidate["score"],
            "time": now,
        }]
    csv_signal([
        datetime.now(timezone.utc).isoformat(), candidate["symbol"], candidate["side"],
        candidate["interval"], candidate["price"], candidate["plan"]["trail_pct"],
        candidate["score"], "approved", news_count,
    ])
    return True


def activate_setup(key, setup, price):
    symbol = setup["symbol"]
    side = setup["side"]
    message = activation_message(setup, price)
    send_message(message)
    with STATE_LOCK:
        STATE["setups"].pop(key, None)
        if len(STATE["virtual_positions"]) < MAX_VIRTUAL_POSITIONS:
            STATE["virtual_positions"][key] = {
                "key": key,
                "symbol": symbol,
                "side": side,
                "entry": price,
                "extreme": price,
                "trail_pct": setup["trail_pct"],
                "activated_at": time.time(),
                "last_price": price,
                "ai_text": setup.get("ai_text", ""),
            }
    save_state()


def monitor_setups():
    for key, setup in list(STATE.get("setups", {}).items()):
        try:
            if time.time() > setup.get("expires_at", 0):
                with STATE_LOCK:
                    STATE["setups"].pop(key, None)
                log(f"انتهت صلاحية الإعداد: {key}")
                continue
            price = get_ticker(setup["symbol"])
            if not price:
                continue
            setup["last_price"] = price
            trail = setup["trail_pct"] / 100.0
            if setup["side"] == "BUY":
                if price < setup["extreme"]:
                    setup["extreme"] = price
                    log(f"تحديث أدنى قاع {setup['symbol']}: {price}")
                trigger = setup["extreme"] * (1.0 + trail)
                if price >= trigger:
                    activate_setup(key, setup, price)
            else:
                if price > setup["extreme"]:
                    setup["extreme"] = price
                    log(f"تحديث أعلى قمة {setup['symbol']}: {price}")
                trigger = setup["extreme"] * (1.0 - trail)
                if price <= trigger:
                    activate_setup(key, setup, price)
        except Exception as exc:
            log(f"خطأ في مراقبة الإعداد {key}: {exc}")
    save_state()


def close_virtual_position(key, position, price, reason):
    entry = position.get("entry", price)
    change = (price / entry - 1.0) * 100.0 if entry else 0.0
    if position["side"] == "SELL":
        change = -change
    send_message(
        f"✅ <b>انتهاء محاكاة Trailing Stop — {symbol_name(position['symbol'])}</b>\n\n"
        f"سبب الخروج: {reason}\n"
        f"سعر الدخول الافتراضي: <code>{fmt_price(position['symbol'], entry)}</code>\n"
        f"سعر الخروج الافتراضي: <code>{fmt_price(position['symbol'], price)}</code>\n"
        f"النتيجة النظرية: <b>{pct(change)}</b>\n"
        "لم يتم إرسال أي أمر حقيقي إلى منصة التداول."
    )
    with STATE_LOCK:
        STATE["virtual_positions"].pop(key, None)
    save_state()


def monitor_virtual_positions():
    for key, position in list(STATE.get("virtual_positions", {}).items()):
        try:
            price = get_ticker(position["symbol"])
            if not price:
                continue
            trail = position["trail_pct"] / 100.0
            entry = position["entry"]
            if position["side"] == "BUY":
                position["extreme"] = max(position.get("extreme", price), price)
                stop = position["extreme"] * (1.0 - trail)
                if price <= stop and position["extreme"] > entry:
                    close_virtual_position(key, position, price, "هبوط السعر تحت التتبع بعد ارتفاع")
                    continue
            else:
                position["extreme"] = min(position.get("extreme", price), price)
                stop = position["extreme"] * (1.0 + trail)
                if price >= stop and position["extreme"] < entry:
                    close_virtual_position(key, position, price, "صعود السعر فوق التتبع بعد هبوط")
                    continue
            position["last_price"] = price
        except Exception as exc:
            log(f"خطأ في مراقبة المحاكاة {key}: {exc}")
    save_state()


def manage_simulator():
    monitor_setups()
    monitor_virtual_positions()


# ══════════════════════════════════════════════════════════════════════════════
# 11) الفحص وإصدار الإشارة
# ══════════════════════════════════════════════════════════════════════════════


def signal_allowed(candidate, force=False):
    key=__REDACTED__"symbol"], candidate["side"])
    if key in STATE.get("setups", {}) or key in STATE.get("virtual_positions", {}):
        return False
    last = STATE.get("cooldowns", {}).get(key, 0.0)
    if not force and time.time() - last < SIGNAL_COOLDOWN:
        return False
    return True


def emit_candidate(candidate, force=False):
    if not signal_allowed(candidate, force=force):
        return False
    news, news_ok = fetch_news(candidate["symbol"])
    if REQUIRE_NEWS and not news_ok:
        log(f"حجب {candidate['symbol']} {candidate['side']}: الأخبار غير متاحة")
        return False
    approved, ai_text = ai_gate(candidate, news)
    if not approved:
        log(f"حجب {candidate['symbol']} {candidate['side']}: {ai_text}")
        with STATE_LOCK:
            STATE["cooldowns"][setup_key(candidate["symbol"], candidate["side"])] = time.time()
        return False
    if not add_setup(candidate, ai_text, len(news)):
        return False
    send_message(signal_message(candidate, ai_text, len(news)))
    if SEND_CHARTS:
        filename = (
            f"{candidate['symbol'].replace('USDT', '')}_"
            f"{candidate['side']}_{candidate['interval']}_{int(time.time())}.png"
        )
        path = os.path.join(CHART_DIR, filename)
        if make_chart(candidate, path):
            send_photo(
                path,
                f"{symbol_name(candidate['symbol'])} | {candidate['side']} | "
                f"{candidate['interval']} | Trail {candidate['plan']['trail_pct']:.2f}%",
            )
    log(
        f"إشارة معتمدة {candidate['symbol']} {candidate['side']} "
        f"{candidate['interval']} score={candidate['score']} trail={candidate['plan']['trail_pct']:.2f}%"
    )
    return True


def run_scan(force=False, announce=True):
    if not SCAN_LOCK.acquire(blocking=False):
        log("تم تخطي الفحص؛ فحص آخر ما زال يعمل")
        return None
    try:
        if announce:
            send_message("🔎 <b>بدأ فحص NOVA RADAR</b>\nتدقيق BTC + العملات على 15m/1h مع فلتر 4h/1d والأخبار.")
        btc = analyze_btc()
        if btc.get("regime") == "unknown":
            log("فحص غير مكتمل: بيانات BTC غير صالحة")
            return btc
        tickers = get_24h_tickers()
        found = 0
        for symbol in SYMBOLS:
            try:
                ticker = tickers.get(symbol, {}).get("price") or get_ticker(symbol)
                market = analyze_symbol(symbol, btc, ticker=ticker)
                if not market:
                    log(f"بيانات ناقصة: {symbol}")
                    continue
                for candidate in market["candidates"]:
                    if found >= MAX_SIGNALS_PER_SCAN and not force:
                        break
                    if emit_candidate(candidate, force=force):
                        found += 1
                time.sleep(0.15)
            except Exception as exc:
                log(f"خطأ تحليل {symbol}: {exc}")
        STATE["last_scan"] = time.time()
        save_state()
        log(f"انتهى الفحص؛ إشارات معتمدة جديدة: {found}")
        return btc
    except Exception as exc:
        log(f"خطأ عام في الفحص: {exc}\n{traceback.format_exc()[-500:]}")
        return None
    finally:
        SCAN_LOCK.release()


# ══════════════════════════════════════════════════════════════════════════════
# 12) تقارير العملة والأسعار والأوامر
# ══════════════════════════════════════════════════════════════════════════════


HELP_TEXT = (
    "🤖 <b>NOVA RADAR v6.0</b>\n\n"
    "/menu لوحة الأزرار\n"
    "/scan فحص السوق فوراً\n"
    "/status حالة BTC والإعدادات والمحاكاة\n"
    "/coin XLM تحليل فني وشارت\n"
    "/chart XLM شارت فقط\n"
    "/close XLM حذف محاكاة/إعداد العملة\n"
    "/pause إيقاف الإشارات الجديدة مع استمرار مراقبة الإعدادات\n"
    "/resume استئناف الفحص\n"
    "/ask سؤالك إرسال سؤال إلى Gemini\n\n"
    "الاستراتيجية: RSI أقل من 30 أو أعلى من 70 + ضعف/تقاطع MACD + رفض سعري + حجم مرتفع، "
    "ثم فحص السيولة والحركة الشاذة وفلتر 4H/1D وBTC والأخبار."
)


def normalize_symbol(value):
    raw = value.strip().upper().replace("/", "")
    if raw.endswith("USDT"):
        symbol = raw
    else:
        symbol = raw + "USDT"
    return symbol if symbol in SYMBOLS else None


def coin_report(symbol, market):
    btc = market["btc"]
    frames = market["frames"]
    lines = [
        f"🔍 <b>تقرير {symbol_name(symbol)}</b>",
        f"السعر: <code>{fmt_price(symbol, market['live'])}</code> | 24س: {pct(market['change24'])}",
        f"BTC: {regime_ar(btc.get('regime'))} | آمن: {'نعم' if btc.get('safe') else 'لا'}",
        "",
    ]
    for interval in ("15m", "1h", "4h", "1d"):
        frame = frames[interval]
        q = frame["quality"]
        lines.append(
            f"{interval}: {trend_ar(frame['trend'])} | RSI {frame['rsi']:.1f} | "
            f"MACD {frame['macd']:.6g} | ATR {frame['atr_pct']:.2f}% | "
            f"VOL {frame['volume_ratio']:.2f}x | "
            f"Sweep {'✅' if (frame['bullish_sweep'] or frame['bearish_sweep']) else '—'} | "
            f"سلامة {'✅' if q['ok'] else '⚠️'}"
        )
    if market["candidates"]:
        for item in market["candidates"]:
            lines.append(
                f"\n🟢 مرشح {item['side']} على {item['interval']}، "
                f"التقييم {item['score']}/100، Trail {item['plan']['trail_pct']:.2f}%"
            )
    else:
        lines.append("\n🟡 لا توجد إشارة مكتملة الآن؛ لا تتعجل.")
    lines.append("\n⚠️ التقرير تحليلي ومحاكاة فقط، وليس تنفيذاً آلياً.")
    return "\n".join(lines)


def prices_report():
    tickers = get_24h_tickers()
    if not tickers:
        return "⚠️ تعذر جلب أسعار Binance الآن."
    lines = ["💲 <b>أسعار السوق</b>"]
    for symbol in SYMBOLS:
        data = tickers.get(symbol)
        if data:
            icon = "🟢" if data["change"] >= 0 else "🔴"
            lines.append(
                f"{icon} {symbol_name(symbol)}: <code>{fmt_price(symbol, data['price'])}</code> "
                f"{pct(data['change'])} | حجم {data['quote_volume'] / 1_000_000:.2f}M$"
            )
    return "\n".join(lines)


def analyze_coin_command(symbol, chart_only=False):
    send_typing()
    btc = analyze_btc()
    market = analyze_symbol(symbol, btc, ticker=get_ticker(symbol))
    if not market:
        send_message(f"⚠️ تعذر تحليل {symbol_name(symbol)}؛ تحقق من الاتصال والرمز.")
        return
    if not chart_only:
        send_message(coin_report(symbol, market), keyboard=menu_keyboard())
    candidate = None
    if market["candidates"]:
        candidate = market["candidates"][0]
    else:
        # شارت محايد عندما لا يوجد مرشح.
        frame = market["frames"]["1h"]
        candidate = {
            "symbol": symbol, "side": "BUY", "interval": "1h", "price": market["live"],
            "signal": frame, "frames": market["frames"], "btc": btc, "score": 0,
            "plan": build_trailing_plan(symbol, "BUY", market["live"], frame, market["frames"]),
        }
    path = os.path.join(CHART_DIR, f"manual_{symbol.replace('USDT', '')}_{int(time.time())}.png")
    if make_chart(candidate, path):
        send_photo(path, f"{symbol_name(symbol)} | شارت {candidate['interval']}")
    elif chart_only:
        send_message("⚠️ matplotlib غير متاح؛ ثبّته عبر: pip install matplotlib")


def ask_gemini(question):
    btc = analyze_btc()
    ctx = (
        f"BTC {btc.get('live', 0):.8g}, regime={btc.get('regime')}, "
        f"safe={btc.get('safe')}, change24={btc.get('change24', 0):.2f}%"
    )
    prompt = (
        "أنت محلل تداول مؤسسي صارم. أجب بالعربية باختصار، اذكر الأرقام المتاحة، "
        "ولا تضمن الربح ولا تنفذ أوامر.\n"
        f"سياق حي: {ctx}\nسؤال المستخدم: {question}"
    )
    text, reason = gemini_call(prompt, max_tokens=350)
    if text:
        return clean_ai(text)
    return f"⚠️ تعذر المحلل السحابي: {reason}. استخدم /coin SYMBOL للتقرير الرقمي."


# ══════════════════════════════════════════════════════════════════════════════
# 13) Telegram polling والواجهة
# ══════════════════════════════════════════════════════════════════════════════


def edit_message(message_id, text, keyboard=None, chat_id=None):
    if not TELEGRAM_TOKEN or not CHAT_ID or DRY_RUN:
        return send_message(text, keyboard=keyboard, chat_id=chat_id)
    payload = {
        "chat_id": chat_id or CHAT_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if keyboard is not None:
        payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
    return bool(tg_call("editMessageText", payload))


def callback_answer(callback_id, text=""):
    if TELEGRAM_TOKEN and CHAT_ID and not DRY_RUN:
        tg_call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text}, retries=1)


def handle_callback(update):
    callback = update.get("callback_query", {})
    message = callback.get("message", {})
    chat = str(message.get("chat", {}).get("id", ""))
    if chat != str(CHAT_ID):
        callback_answer(callback.get("id", ""), "غير مصرح")
        return
    data = callback.get("data", "")
    callback_answer(callback.get("id", ""))
    if data == "main":
        edit_message(message.get("message_id"), "🎛️ <b>لوحة NOVA RADAR</b>\nاختر عملية:", menu_keyboard(), chat)
    elif data == "scan":
        threading.Thread(target=lambda: run_scan(force=True), daemon=True).start()
    elif data == "status":
        threading.Thread(target=lambda: send_message(status_message(), keyboard=menu_keyboard(), chat_id=chat), daemon=True).start()
    elif data == "prices":
        threading.Thread(target=lambda: send_message(prices_report(), keyboard=menu_keyboard(), chat_id=chat), daemon=True).start()
    elif data == "coins":
        send_message("🪙 اختر العملة للتحليل والشارت:", keyboard=coins_keyboard(), chat_id=chat)
    elif data == "pause":
        STATE["paused"] = True
        save_state()
        send_message("⏸ تم إيقاف الإشارات الجديدة؛ ستستمر مراقبة المحاكاة الحالية.", keyboard=menu_keyboard(), chat_id=chat)
    elif data == "resume":
        STATE["paused"] = False
        save_state()
        send_message("▶ تم استئناف الرادار.", keyboard=menu_keyboard(), chat_id=chat)
    elif data == "help":
        send_message(HELP_TEXT, keyboard=menu_keyboard(), chat_id=chat)
    elif data.startswith("coin:"):
        symbol = normalize_symbol(data.split(":", 1)[1])
        if symbol:
            threading.Thread(target=analyze_coin_command, args=(symbol,), daemon=True).start()


def handle_command(text, chat_id):
    parts = text.split(maxsplit=1)
    command = parts[0].split("@", 1)[0].lower()
    argument = parts[1].strip() if len(parts) > 1 else ""
    if command in ("/start", "/menu"):
        send_message("🎛️ <b>لوحة NOVA RADAR v6.0</b>\nاختر عملية:", keyboard=menu_keyboard(), chat_id=chat_id)
    elif command == "/help":
        send_message(HELP_TEXT, keyboard=menu_keyboard(), chat_id=chat_id)
    elif command == "/status":
        threading.Thread(target=lambda: send_message(status_message(), keyboard=menu_keyboard(), chat_id=chat_id), daemon=True).start()
    elif command == "/scan":
        threading.Thread(target=lambda: run_scan(force=True), daemon=True).start()
    elif command == "/pause":
        STATE["paused"] = True
        save_state()
        send_message("⏸ تم إيقاف الإشارات الجديدة؛ تستمر مراقبة المحاكاة.", chat_id=chat_id)
    elif command == "/resume":
        STATE["paused"] = False
        save_state()
        send_message("▶ تم استئناف الإشارات.", chat_id=chat_id)
    elif command in ("/coin", "/chart"):
        symbol = normalize_symbol(argument)
        if not symbol:
            send_message("اكتب مثلاً: /coin XLM أو /chart BTC", chat_id=chat_id)
            return
        threading.Thread(target=analyze_coin_command, args=(symbol, command == "/chart"), daemon=True).start()
    elif command == "/prices":
        threading.Thread(target=lambda: send_message(prices_report(), keyboard=menu_keyboard(), chat_id=chat_id), daemon=True).start()
    elif command == "/close":
        symbol = normalize_symbol(argument)
        if not symbol:
            send_message("اكتب مثلاً: /close XLM", chat_id=chat_id)
            return
        removed = []
        with STATE_LOCK:
            for key in list(STATE["setups"]):
                if STATE["setups"][key]["symbol"] == symbol:
                    STATE["setups"].pop(key, None)
                    removed.append(key)
            for key in list(STATE["virtual_positions"]):
                if STATE["virtual_positions"][key]["symbol"] == symbol:
                    STATE["virtual_positions"].pop(key, None)
                    removed.append(key)
        save_state()
        send_message(
            f"✔ تم حذف {symbol_name(symbol)} من المتابعة ({len(removed)} عنصر).",
            chat_id=chat_id,
        )
    elif command == "/ask":
        if not argument:
            send_message("اكتب مثلاً: /ask هل BTC آمن الآن؟", chat_id=chat_id)
            return
        threading.Thread(
            target=lambda: send_message("🧠 <b>المحلل:</b>\n" + esc(ask_gemini(argument)), chat_id=chat_id),
            daemon=True,
        ).start()
    else:
        send_message("أمر غير معروف. استخدم /help", keyboard=menu_keyboard(), chat_id=chat_id)


def route_text(text, chat_id):
    lower = text.lower()
    for symbol in SYMBOLS:
        base = symbol.replace("USDT", "").lower()
        if base in lower.split() or symbol.lower() in lower:
            threading.Thread(target=analyze_coin_command, args=(symbol,), daemon=True).start()
            return
    threading.Thread(
        target=lambda: send_message("🧠 <b>المحلل:</b>\n" + esc(ask_gemini(text)), chat_id=chat_id),
        daemon=True,
    ).start()


def poll_telegram_once():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    result = tg_call("getUpdates", {
        "offset": STATE.get("tg_offset", 0),
        "timeout": TELEGRAM_POLL_TIMEOUT,
        "allowed_updates": ["message", "callback_query"],
    }, retries=1)
    if not result:
        return
    for update in result:
        STATE["tg_offset"] = max(STATE.get("tg_offset", 0), update.get("update_id", 0) + 1)
        if "callback_query" in update:
            handle_callback(update)
            continue
        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        if chat_id != str(CHAT_ID):
            continue
        text = (message.get("text") or "").strip()
        if not text:
            continue
        if text.startswith("/"):
            handle_command(text, chat_id)
        else:
            route_text(text, chat_id)
    save_state()


def telegram_loop():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        log("Telegram غير مفعّل؛ سيتم التشغيل المحلي/DRY_RUN فقط")
        return
    log("بدأ Telegram long polling")
    while True:
        try:
            poll_telegram_once()
        except Exception as exc:
            log(f"خطأ Telegram: {exc}")
            time.sleep(5)


# ══════════════════════════════════════════════════════════════════════════════
# 14) بطاقة يومية واختبار ذاتي
# ══════════════════════════════════════════════════════════════════════════════


def daily_digest():
    if not DAILY_DIGEST:
        return
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if now.hour != DAILY_DIGEST_HOUR or STATE.get("last_digest") == today:
        return
    btc = analyze_btc()
    prices = get_24h_tickers()
    strongest = max(prices.items(), key=lambda pair: pair[1]["change"]) if prices else None
    weakest = min(prices.items(), key=lambda pair: pair[1]["change"]) if prices else None
    lines = [
        f"🌅 <b>بطاقة NOVA اليومية — {today}</b>",
        f"BTC: {regime_ar(btc.get('regime'))} | 24س {pct(btc.get('change24', 0))}",
        f"إعدادات تنتظر التفعيل: {len(STATE.get('setups', {}))}",
    ]
    if strongest:
        lines.append(f"🏆 الأقوى: {symbol_name(strongest[0])} {pct(strongest[1]['change'])}")
    if weakest:
        lines.append(f"📉 الأضعف: {symbol_name(weakest[0])} {pct(weakest[1]['change'])}")
    lines.append("/menu لفتح لوحة التحكم")
    send_message("\n".join(lines), keyboard=menu_keyboard())
    STATE["last_digest"] = today
    save_state()


def selftest():
    print("NOVA RADAR SELFTEST")
    random.seed(17)
    n = 420
    opens, highs, lows, closes, volumes = [], [], [], [], []
    price = 100.0
    for i in range(n):
        price += math.sin(i / 27.0) * 0.35 + random.gauss(0, 0.55)
        price = max(20.0, price)
        o = price
        c = max(20.0, price + random.gauss(0, 0.35))
        h = max(o, c) + abs(random.gauss(0, 0.25))
        low = min(o, c) - abs(random.gauss(0, 0.25))
        opens.append(o)
        highs.append(h)
        lows.append(low)
        closes.append(c)
        volumes.append(abs(random.gauss(1000, 160)))
        price = c

    ok = True

    def check(name, condition):
        nonlocal ok
        print(("✅ " if condition else "❌ ") + name)
        ok = ok and condition

    rsi = rsi_series(closes)
    check("RSI صالح", rsi[-1] is not None and 0 <= rsi[-1] <= 100)
    ema = ema_series(closes, 50)
    check("EMA صالح", ema[-1] is not None)
    ml, ms, hist = macd_series(closes)
    check("MACD صالح", ml[-1] is not None and ms[-1] is not None and hist[-1] is not None)
    at = atr_series(highs, lows, closes)
    check("ATR موجب", at[-1] is not None and at[-1] > 0)
    bu, bm, bl = bollinger_series(closes)
    check("Bollinger صالح", bu[-1] is not None and bl[-1] is not None and bu[-1] >= bl[-1])
    vw = vwap_series(highs, lows, closes, volumes)
    check("VWAP صالح", vw[-1] is not None)
    dp, dm, adx = adx_series(highs, lows, closes)
    check("ADX صالح", adx[-1] is not None and 0 <= adx[-1] <= 100)

    fake_raw = {
        "t": [int(time.time() * 1000) - (n - i) * 3600000 for i in range(n)],
        "o": opens, "h": highs, "l": lows,
        "c": closes, "v": volumes, "qv": [x * 100 for x in volumes], "live": closes[-1],
    }
    fake = analyze_timeframe_from_data_for_test(fake_raw)
    check("فحص الشموع صالح", fake["quality"]["ok"])
    plan = build_trailing_plan("TESTUSDT", "BUY", closes[-1], fake, {"1h": fake})
    check("Trailing Delta موجب", plan["trail_pct"] > 0)
    check("مستوى الإلغاء أسفل السعر", plan["invalidation"] < closes[-1])
    print("النتيجة: " + ("ALL PASS ✅" if ok else "FAIL ❌"))
    return 0 if ok else 1


def analyze_timeframe_from_data_for_test(raw):
    closed = {key: values[:-1] for key, values in raw.items() if isinstance(values, list)}
    c, h, l, o, v, qv = closed["c"], closed["h"], closed["l"], closed["o"], closed["v"], closed["qv"]
    rsi = rsi_series(c)
    ml, ms, hist = macd_series(c)
    at = last_value(atr_series(h, l, c), 0.0) or 0.0
    quality = data_quality(raw, "1h", at)
    dp, dm, adx = adx_series(h, l, c)
    return {
        "raw": raw, "c": c, "h": h, "l": l, "o": o, "v": v, "qv": qv,
        "rsi": last_value(rsi, 50), "macd": last_value(ml, 0), "hist": last_value(hist, 0),
        "hist_prev": hist[-2] or 0, "atr": at, "atr_pct": at / c[-1] * 100,
        "macd_cross_up": recent_cross(ml, ms, "up"), "macd_cross_down": recent_cross(ml, ms, "down"),
        "adx": last_value(adx, 0), "quality": quality, "volume_ratio": quality["volume_ratio"],
        "volume_spike": quality["volume_spike"], "bullish_sweep": quality["bullish_sweep"],
        "bearish_sweep": quality["bearish_sweep"], "rejection": quality["rejection"],
        "qv_24h": sum(qv[-25:]), "trend": "side",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 15) التشغيل الرئيسي
# ══════════════════════════════════════════════════════════════════════════════


def main():
    global DRY_RUN
    args = set(sys.argv[1:])
    ensure_dirs()
    if "--selftest" in args:
        raise SystemExit(selftest())
    if "--once" in args:
        DRY_RUN = True
    load_state()
    load_tick_sizes()
    if not TELEGRAM_TOKEN or not CHAT_ID:
        log("للتنبيهات الحقيقية عرّف TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID")
    if REQUIRE_GEMINI and not GEMINI_API_KEY:
        log("GEMINI_API_KEY غير موجود؛ الإشارات ستُحجب بأمان حتى تضيف المفتاح")
    if not DRY_RUN:
        ping = binance_get("/api/v3/ping")
        log("اتصال Binance: " + ("OK" if ping is not None else "غير متاح حالياً"))
    if "--once" in args:
        run_scan(force=True, announce=True)
        manage_simulator()
        cleanup_charts()
        return

    send_message(
        "🚀 <b>تم تشغيل NOVA RADAR v6.0</b>\n"
        "15m/1h للإشارة | 4h/1d للفلترة | BTC قائد | CryptoCompare + Gemini\n"
        "المحرك محاكاة وإنذار فقط ولا يرسل أوامر إلى Binance.",
        keyboard=menu_keyboard(),
    )
    threading.Thread(target=telegram_loop, daemon=True, name="telegram-loop").start()
    last_scan = 0.0
    last_manage = 0.0
    while True:
        try:
            now = time.time()
            if not STATE.get("paused") and now - last_scan >= SCAN_INTERVAL:
                last_scan = now
                threading.Thread(target=run_scan, kwargs={"force": False, "announce": False}, daemon=True).start()
            if now - last_manage >= MANAGE_INTERVAL:
                last_manage = now
                manage_simulator()
            daily_digest()
            if now - STATE.get("last_heartbeat", 0.0) >= 12 * 3600:
                STATE["last_heartbeat"] = now
                save_state()
                send_message(status_message(), keyboard=menu_keyboard())
            save_state()
            time.sleep(3)
        except KeyboardInterrupt:
            save_state()
            send_message("👋 تم إيقاف NOVA RADAR يدوياً؛ الذاكرة محفوظة.")
            return
        except Exception as exc:
            log(f"خطأ الحلقة الرئيسية: {exc}\n{traceback.format_exc()[-500:]}")
            time.sleep(10)


if __name__ == "__main__":
    main()
