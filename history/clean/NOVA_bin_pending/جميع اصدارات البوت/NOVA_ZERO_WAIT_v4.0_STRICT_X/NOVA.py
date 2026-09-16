#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA ZERO-WAIT v4.0.2 STRICT — Microstructure Scalper + قوانين وقف الخسارة الصارمة
بوت سكالبينج Spot عالي التردد على Binance مبني على نموذج
Hybrid Microstructure Scalping Model (HMSM).

الفلسفة المعمارية:
1) Zero-Wait: لا حفظ لإعدادات ولا انتظار Pullback إطلاقاً. كل دورة فحص تقرأ
   الشموع مباشرة؛ إذا تحققت الأعمدة الثلاثة في اللحظة نفسها يُنفَّذ LIMIT BUY
   فوري على سعر Ask، وإلا تُتجاوز العملة فوراً إلى التالية.
2) الأعمدة الثلاثة (يجب أن تجتمع في اللحظة نفسها):
   • MSS  : كسر هيكل صاعد (Market Structure Shift) بإزاحة قوية على 1m.
   • FVG  : فجوة قيمة عادلة (Fair Value Gap) صاعدة حديثة وغير معبأة.
   • Flow : اختلال تدفق الأوامر من دفتر Level-1 عبر book_stats لصالح الطلب.
3) لا مؤشرات بطيئة: لا MACD ولا RSI ولا EMA ولا Fibonacci. السعر + الدفتر فقط.
4) الكون الديناميكي: أفضل 50 زوجاً حسب حجم التداول 24 ساعة، تحديث دوري كل
   10 دقائق، بلا عملة قائدة ولا قوائم ثابتة.
5) الأداء الأقصى: SCAN_WORKERS وHTTP_CONCURRENCY مرتفعان، صفر sleep()
   تعطيلي داخل الفحص، Connection-Pooling، ومراقبة ذاتية لوزن الطلبات
   (X-MBX-USED-WEIGHT-1M) مع تهدئة تلقائية لتفادي 429/حظر API.
6) الحجم: 10$ ثابتة لكل مركز. Pyramiding: حتى 3 مراكز متزامنة مستقلة لكل
   عملة، لكل مركز معرّف فريد (pid) في الذاكرة وOCO خاص يُدار منفصلاً.
7) الحماية: وقف وهدف ديناميكان مشتقان من ATR(1m) لكل عملة، وعند التفعيل
   يُستبدلان بـ OCO متحرك بمسافة ATR لحظية (Trailing Delta). لا نسب ثابتة.
8) لا قواطع خسائر متتالية ولا حدود خسارة يومية: البوت يتداول إلى ما لا
   نهاية، مع الاحتفاظ بعدّاد الخسائر المتتالية للتقرير فقط.

شبكة الأمان (لا أوامر يتيمة ولا عملات ضائعة):
• pending_entries: كل أمر دخول يُسجَّل قبل إرساله ويُحذف بعد اليقين بالحالة
  النهائية؛ عند أي انقطاع شبكة أو انهيار تتولى "المصالحة" حسمه: تعبئة →
  مركز+OCO أو بيع إنقاذ، أمر جديد → إلغاء.
• Dust: أي كمية أصغر من الحد الأدنى للبيع تُتبَّع وتُباع تلقائياً فور
  بلوغها الحد الأدنى.
• قفل نسخة واحدة (bot.lock) يمنع تشغيل نسختين معاً.
   (ملاحظة: دفتر أوامر Testnet اصطناعي؛ لذلك يعتمد عمود Flow الحقيقي على
   live/demo، ويعمل عمود السعر/الإزاحة على أي بيئة.)

التثبيت في Termux:
    pkg update -y
    pkg install python -y
    pip install requests

الإعداد:
    export BINANCE_ENV='testnet'
    export BINANCE_API_KEY='مفتاح Binance Spot Testnet'
    export BINANCE_API_SECRET='سر Binance Spot Testnet'
    export TELEGRAM_BOT_TOKEN='توكن Telegram'
    export TELEGRAM_CHAT_ID='معرف المحادثة'

التشغيل:
    python NOVA.py --selftest
    python NOVA.py --dry-run
    python NOVA.py
    python NOVA.py --once

لا Futures ولا رافعة ولا بيع على المكشوف. لا ضمان للربح؛ ابدأ بالـ Testnet.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import hmac
import html
import json
import math
import os
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
    from requests.adapters import HTTPAdapter
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


def clamp(value, low, high):
    return max(low, min(high, value))


BINANCE_ENV = os.getenv("BINANCE_ENV", "testnet").strip().lower()
if BINANCE_ENV not in ("demo", "testnet", "live"):
    BINANCE_ENV = "testnet"
BINANCE_BASE = {
    "demo": "https://demo-api.binance.com",
    "testnet": "https://testnet.binance.vision",
    "live": "https://api.binance.com",
}[BINANCE_ENV]
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "").strip()
LIVE_CONFIRM = os.getenv("LIVE_TRADING_CONFIRM", "")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

AUTO_TRADE = env_bool("AUTO_TRADE", True)
DRY_RUN = env_bool("DRY_RUN", False)

# ── الكون الديناميكي: أفضل 50 زوجاً حسب حجم 24 ساعة ──────────────────────────
TOP_N_SYMBOLS = 50
UNIVERSE_REFRESH_EVERY = max(60, env_int("UNIVERSE_REFRESH_EVERY", 600))
MIN_24H_QUOTE_VOLUME = env_float("MIN_24H_QUOTE_VOLUME", 1_000_000)

# ── محرك HMSM على فريم 1m ─────────────────────────────────────────────────────
SIGNAL_INTERVAL = "1m"
INTERVAL_SECONDS = {"1m": 60}
KLINE_LIMIT = clamp(env_int("KLINE_LIMIT", 100), 80, 300)
MIN_CLOSED_CANDLES = max(30, env_int("MIN_CLOSED_CANDLES", 60))
KLINE_TTL = {"1m": max(2, env_int("KLINE_TTL_1M", 6))}

MSS_LOOKBACK = max(5, env_int("MSS_LOOKBACK", 20))
MSS_MAX_AGE = max(1, env_int("MSS_MAX_AGE", 2))
MSS_MIN_RANGE_ATR = env_float("MSS_MIN_RANGE_ATR", 0.80)
MSS_BODY_RATIO = clamp(env_float("MSS_BODY_RATIO", 0.50), 0.0, 1.0)

FVG_LOOKBACK = max(3, env_int("FVG_LOOKBACK", 8))
FVG_MIN_ATR = env_float("FVG_MIN_ATR", 0.05)

MAX_SPREAD_PCT = env_float("MAX_SPREAD_PCT", 0.15)
MIN_BOOK_IMBALANCE = clamp(env_float("MIN_BOOK_IMBALANCE", 0.58), 0.5, 1.0)

# ── ATR والحماية الديناميكية (لا نسب ثابتة) ──────────────────────────────────
ATR_PERIOD = max(2, env_int("ATR_PERIOD", 14))
STOP_ATR_MULT = env_float("STOP_ATR_MULT", 1.15)
TP_ATR_MULT = env_float("TP_ATR_MULT", 2.20)
TRAIL_ACTIVATION_ATR_MULT = env_float("TRAIL_ACTIVATION_ATR_MULT", 1.50)
TRAIL_DISTANCE_ATR_MULT = env_float("TRAIL_DISTANCE_ATR_MULT", 1.20)
FEE_BUFFER = env_float("FEE_BUFFER", 0.0015)
LIMIT_SLIPPAGE_PCT = env_float("LIMIT_SLIPPAGE_PCT", 0.20)
OCO_LEGACY_FALLBACK = env_bool("OCO_LEGACY_FALLBACK", True)

# ── التنفيذ: 10$ ثابتة + حتى 3 مراكز متزامنة لكل عملة ───────────────────────
TRADE_NOTIONAL_D = Decimal("10")        # ثابت بالمواصفات: عشرة دولارات لكل مركز
MAX_POSITIONS_PER_SYMBOL = 3            # ثابت بالمواصفات: Pyramiding مستقل
SYMBOL_COOLDOWN = max(0, env_int("SYMBOL_COOLDOWN", 8))

# ═══ V4.0 STRICT: القوانين الصارمة لوقف الخسارة + الفلاتر + حاكم العملات ═══
SL_MIN_PCT = env_float("SL_MIN_PCT", 0.30)        # أضيق وقف (% من السعر)
SL_MAX_PCT = env_float("SL_MAX_PCT", 3.0)         # أوسع وقف
BREAKEVEN_TRIGGER_PCT = env_float("BREAKEVEN_TRIGGER_PCT", 0.50)  # قفل الأرباح عند +
BREAKEVEN_LOCK_PCT = env_float("BREAKEVEN_LOCK_PCT", 0.45)        # فوق عمولة الجولة ⇒ صافي موجب
TIME_STOP_SEC = max(20, env_int("TIME_STOP_SEC", 60))             # خروج الزمن الذكي
TIME_STOP_MIN_PROFIT_PCT = env_float("TIME_STOP_MIN_PROFIT_PCT", 0.10)
MIN_ATR_MOVE_PCT = env_float("MIN_ATR_MOVE_PCT", 0.08)            # منع العملات النائمة
MIN_VOLUME_RATIO = env_float("MIN_VOLUME_RATIO", 1.2)             # منع السوق النائم
MIN_TARGET_PCT = env_float("MIN_TARGET_PCT", 0.35)                # الهدف > العمولة
FEE_SIM_PCT = env_float("FEE_SIM_PCT", 0.20)                      # عمولة محسوبة للصدق
GOV_MAX_LOSSES = max(2, env_int("GOV_MAX_LOSSES", 3))             # خسائر متتالية/عملة
GOV_SYMBOL_COOLDOWN = max(60, env_int("GOV_SYMBOL_COOLDOWN", 600)) # عقوبة 10د للعملة فقط
PYRAMID_REQUIRE_PROFIT = env_bool("PYRAMID_REQUIRE_PROFIT", True) # التسليم بشرط الربح
ORDER_BUDGET_MAX = max(6, env_int("ORDER_BUDGET_MAX", 40))
ORDER_BUDGET_WINDOW = max(5.0, env_float("ORDER_BUDGET_WINDOW", 10.0))
DAILY_REPORT_HOUR = env_int("DAILY_REPORT_HOUR", 20)              # تقرير يومي (توقيت الجهاز)
LOG_BOOK_CAP = max(50, env_int("LOG_BOOK_CAP", 200))              # سجل الصفقات التفاعلي
LOG_PAGE_SIZE = 8                                                 # صفوف صفحة السجل
LIMIT_FILL_TIMEOUT = env_float("LIMIT_FILL_TIMEOUT", 4.0)
LIMIT_FILL_POLL = max(0.2, env_float("LIMIT_FILL_POLL", 0.5))

# ── الأداء الأقصى ─────────────────────────────────────────────────────────────
SCAN_EVERY = max(1, env_int("SCAN_EVERY", 3))
MANAGE_EVERY = max(1, env_int("MANAGE_EVERY", 5))
SCAN_WORKERS = max(8, min(64, env_int("SCAN_WORKERS", 25)))
HTTP_CONCURRENCY = max(4, min(64, env_int("HTTP_CONCURRENCY", 32)))
MAX_ENTRY_WORKERS = max(1, min(16, env_int("MAX_ENTRY_WORKERS", 6)))
SAFE_WEIGHT_LIMIT = max(120, env_int("SAFE_WEIGHT_LIMIT", 1000 if BINANCE_ENV == "testnet" else 5000))

# ── الملفات ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "nova_hmsm_data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
TRADES_FILE = os.path.join(DATA_DIR, "trades.csv")
KILL_SWITCH_FILE = os.path.join(DATA_DIR, "STOP_TRADING")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "NOVA-ZERO-WAIT/4.0"})
try:
    _ADAPTER = HTTPAdapter(pool_connections=HTTP_CONCURRENCY, pool_maxsize=HTTP_CONCURRENCY)
    SESSION.mount("https://", _ADAPTER)
except Exception:
    pass

STATE_LOCK = threading.RLock()
SCAN_LOCK = threading.Lock()
MANAGE_LOCK = threading.Lock()
ENTRY_LOCK = threading.Lock()
KLINE_CACHE_LOCK = threading.RLock()
ENTRY_SEMAPHORE = threading.BoundedSemaphore(MAX_ENTRY_WORKERS)
HTTP_LIMITER = threading.BoundedSemaphore(HTTP_CONCURRENCY)

TIME_OFFSET_MS = 0
SYMBOL_RULES = {}
SYMBOLS = []
TICKER_CACHE = {}
KLINE_CACHE = {}
MAX_KLINE_CACHE_ENTRIES = max(64, TOP_N_SYMBOLS * 3)
LAST_UNIVERSE_REFRESH = 0.0
LAST_USED_WEIGHT = 0
RATE_BACKOFF_UNTIL = 0.0
# حجز ذري لقيمة الدخول قبل تشغيل خيوط الدخول المتوازية
ENTRY_RESERVATIONS = {}
RESERVED_QUOTE = Decimal("0")


# ══════════════════════════════════════════════════════════════════════════════
# 2) الذاكرة والسجل
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
        "last_heartbeat": 0.0,
        "cooldowns": {},
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
        # ═══ V4.0 STRICT ═══
        "gov_streak": {},          # خسائر متتالية لكل عملة
        "filters": {"dead": 0, "sleepy": 0, "target": 0, "pyramid": 0,
                    "budget": 0, "gov": 0, "trail-floor": 0},
        "log_book": [],            # سجل الصفقات المفصل (للزر التفاعلي)
        "fees_sim": 0.0,           # عمولات محسوبة تراكمياً
        "net_fees": 0.0,           # الصافي بعد العمولة المحسوبة
        "order_ts": [],            # طوابع ميزانية الأوامر
        "daily": {},               # بطاقة اليوم {date, trades, wins, losses, net, best, worst}
        "last_daily": "",
    }


STATE = default_state()


def migrate_positions(raw):
    """يحوّل مراكز v2 (مفتاح=رمز) إلى مفاتيح pid فريدة، ويحفظ المراكز الحديثة."""
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
            saved.pop("setups", None)
            base.update(saved)
        if not isinstance(base.get("positions"), dict):
            base["positions"] = {}
        base["positions"] = migrate_positions(base["positions"])
        if not isinstance(base.get("pending_entries"), dict):
            base["pending_entries"] = {}
        if not isinstance(base.get("dust"), list):
            base["dust"] = []
        metrics = base.get("metrics")
        if not isinstance(metrics, dict):
            metrics = {}
        base["metrics"] = {
            "trades": int(metrics.get("trades", 0)),
            "realized_pnl": float(metrics.get("realized_pnl", 0.0)),
            "wins": int(metrics.get("wins", 0)),
            "losses": int(metrics.get("losses", 0)),
            "consecutive_losses": int(metrics.get("consecutive_losses", 0)),
        }
        STATE = base
        log(f"ذاكرة HMSM: {len(STATE['positions'])} مركزاً مفتوحاً | صفقات {STATE['metrics']['trades']}")
    except FileNotFoundError:
        log("لا توجد ذاكرة سابقة؛ بداية جديدة")
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
                writer.writerow(["time", "symbol", "pid", "entry", "exit", "qty", "pnl", "reason", "environment"])
            writer.writerow(row)
    except Exception as exc:
        log(f"تعذر كتابة سجل الصفقة: {exc}")


def esc(value):
    return html.escape(str(value))


def coin_name(symbol):
    """اسم نظيف بلا USDT للعرض: BTCUSDT → BTC"""
    symbol = str(symbol)
    return symbol[:-4] if symbol.endswith("USDT") else symbol


def pct(value):
    return f"{float(value):+.2f}%"


def make_client_id(prefix):
    return (prefix + uuid.uuid4().hex[:20]).upper()[:36]


def new_position_id(symbol):
    """معرّف فريد لكل مركز مستقل (يدعم 3 مراكز متزامنة على نفس العملة)."""
    return f"{symbol}#{uuid.uuid4().hex[:8]}"


def kill_switch_active():
    return os.path.exists(KILL_SWITCH_FILE)


LOCK_FILE = os.path.join(DATA_DIR, "bot.lock")


def acquire_single_instance():
    """يمنع تشغيل نسختين من البوت معاً (حماية ملف الذاكرة والأوامر)."""
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


def mark_cooldown(symbol):
    STATE.setdefault("cooldowns", {})[symbol] = time.time()


# ═══ V4.0 STRICT: دوال نقية قابلة للاختبار — لا شبكة ولا حالة ═══


def strict_stop_target(entry, atr_value, reject_below_fee=True):
    """وقف بأرضية وسقف + هدف معاد اشتقاقه. None فقط عندما reject_below_fee=True.

    القاعدة: المسافة لا تنزل تحت SL_MIN_PCT (كي لا تقتلها هزّة عادية) ولا
    تتجاوز SL_MAX_PCT (كي لا تحرق الصفقة)، ثم الهدف = 2.2×المسافة النهائية.
    reject_below_fee=True (قبل الشراء): يُرفض كل هدف لا يغطي العمولة.
    reject_below_fee=False (بعد تعبئة الأمر): قصّ فقط — لا يجوز أبداً رفض
    مركز نملكه فعلاً وإلا صار يتماً بلا حماية ولا سجل.
    """
    entry = float(entry)
    atr_value = float(atr_value or 0.0)
    if entry <= 0:
        return None
    dist = STOP_ATR_MULT * atr_value if atr_value > 0 else 0.0
    dist = min(max(dist, entry * SL_MIN_PCT / 100.0), entry * SL_MAX_PCT / 100.0)
    stop = entry - dist
    target = entry + TP_ATR_MULT * dist
    if reject_below_fee and (target - entry) / entry * 100.0 < MIN_TARGET_PCT:
        return None
    return {"stop": stop, "target": target, "dist": dist,
            "target_pct": (target - entry) / entry * 100.0}


def be_lock_price(entry):
    """سعر وقف ما بعد القفل: فوق الدخول — الربح مضمون من هذه اللحظة."""
    return float(entry) * (1.0 + BREAKEVEN_LOCK_PCT / 100.0)


def time_stop_due(age_sec, gain_pct, be_armed, trailing_active):
    """الخروج الزمني الذكي: راكدة بلا ربح يُذكر بعد TIME_STOP_SEC — المحمية لا تُمس."""
    if be_armed or trailing_active:
        return False
    return age_sec >= TIME_STOP_SEC and gain_pct < TIME_STOP_MIN_PROFIT_PCT


def fee_sim(entry_quote, exit_quote):
    """العمولة المحسوبة (دخول+خروج) — الصدق المحاسبي في كل رسالة وتقرير."""
    return (float(entry_quote) + float(exit_quote)) * FEE_SIM_PCT / 100.0


def gov_should_pause(symbol):
    """(ممنوع؟, سبب): عقوبة GOV_SYMBOL_COOLDOWN على العملة الخاسرة فقط —
    لا إيقاف عام إطلاقاً؛ بقية العملات تستمر طبيعياً."""
    streak = int((STATE.get("gov_streak") or {}).get(symbol, 0))
    if streak < GOV_MAX_LOSSES:
        return False, ""
    since = time.time() - float(STATE.get("cooldowns", {}).get(symbol, 0.0))
    if since < GOV_SYMBOL_COOLDOWN:
        return True, f"حاكم العملة: {streak} خسائر متتالية — تجاوز {int((GOV_SYMBOL_COOLDOWN - since) / 60) + 1}د"
    return False, ""


def budget_take(n=1, force=False):
    """ميزانية الأوامر في نافذة ORDER_BUDGET_WINDOW — الخروج المحمي لا ينتظرها."""
    now = time.time()
    ts = [t for t in STATE.setdefault("order_ts", []) if now - t < ORDER_BUDGET_WINDOW]
    if len(ts) + n > ORDER_BUDGET_MAX and not force:
        STATE["order_ts"] = ts
        STATE["filters"]["budget"] = STATE["filters"].get("budget", 0) + 1
        return False
    STATE["order_ts"] = ts + [now] * n
    return True


def log_book_add(symbol, pid, entry, exit_price, qty, pnl, reason):
    """قيد مفصل في سجل الصفقات (زر 📋) + المحاسبة بعد العمولة المحسوبة."""
    fee = fee_sim(float(entry) * float(qty), float(exit_price) * float(qty))
    net = float(pnl) - fee
    with STATE_LOCK:
        STATE["fees_sim"] = float(STATE.get("fees_sim", 0.0)) + fee
        STATE["net_fees"] = float(STATE.get("net_fees", 0.0)) + net
        book = STATE.setdefault("log_book", [])
        book.append({"t": time.time(), "symbol": symbol, "pid": pid,
                     "entry": round(float(entry), 8), "exit": round(float(exit_price), 8),
                     "qty": round(float(qty), 8), "pnl": round(float(pnl), 6),
                     "fee": round(fee, 6), "net": round(net, 6), "reason": str(reason)[:60]})
        if len(book) > LOG_BOOK_CAP:
            del book[:-LOG_BOOK_CAP]
        # بطاقة اليوم
        today = datetime.now().strftime("%Y-%m-%d")
        daily = STATE.setdefault("daily", {})
        if daily.get("date") != today:
            STATE["daily"] = {"date": today, "trades": 0, "wins": 0, "losses": 0, "net": 0.0}
            daily = STATE["daily"]
        daily["trades"] += 1
        daily["net"] = round(daily.get("net", 0.0) + net, 6)
        if net >= 0:
            daily["wins"] = daily.get("wins", 0) + 1
        else:
            daily["losses"] = daily.get("losses", 0) + 1
        best = daily.get("best")
        worst = daily.get("worst")
        if best is None or net > float(best.get("net", 0)):
            daily["best"] = {"symbol": symbol, "net": round(net, 6)}
        if worst is None or net < float(worst.get("net", 0)):
            daily["worst"] = {"symbol": symbol, "net": round(net, 6)}
    return net


def build_log_page(page):
    """نص صفحة من السجل المفصل + عدد الصفحات — زر 📋 سجل الصفقات."""
    book = list(STATE.get("log_book") or [])
    total = max(1, (len(book) + LOG_PAGE_SIZE - 1) // LOG_PAGE_SIZE)
    page = max(0, min(int(page), total - 1))
    chunk = list(reversed(book))          # الأحدث أولاً
    start = page * LOG_PAGE_SIZE
    rows = chunk[start:start + LOG_PAGE_SIZE]
    L = [f"📋 <b>سجل الصفقات المفصل</b> — صفحة {page + 1}/{total} "
         f"({len(book)} صفقة)", ""]
    if not rows:
        L.append("لا صفقات بعد — السجل يُبنى تلقائياً مع كل إغلاق.")
    for r in rows:
        icon = "🟢" if r["net"] >= 0 else "🔴"
        t = datetime.fromtimestamp(r["t"]).strftime("%H:%M:%S")
        L.append(
            f"{icon} <b>{r['symbol'].replace('USDT','')}</b> | {t}\n"
            f"   دخول <code>{r['entry']:g}</code> ← خروج <code>{r['exit']:g}</code> "
            f"(كمية {r['qty']:g})\n"
            f"   خام {r['pnl']:+.4f}$ | عمولة −{r['fee']:.4f}$ | "
            f"<b>صافي {r['net']:+.4f}$</b>\n"
            f"   السبب: {esc(r['reason'])}")
    L.append("")
    L.append(f"💰 إجمالي الصافي بعد العمولة المحسوبة: "
             f"<b>{float(STATE.get('net_fees', 0.0)):+.4f}$</b> "
             f"(عمولات {float(STATE.get('fees_sim', 0.0)):.4f}$)")
    return "\n".join(L), total


def log_keyboard(page, total):
    row = []
    if page > 0:
        row.append(button("◀ السابق", f"log:{page - 1}"))
    row.append(button(f"{page + 1}/{total}", "log:refresh"))
    if page < total - 1:
        row.append(button("التالي ▶", f"log:{page + 1}"))
    return [row, [button("🔄 تحديث", f"log:{page}"), button("🏠 القائمة", "help")]]


def build_stats_text():
    """إحصاء صادق: اليوم + العمر الكلي + الحاكم + أعلى الفلاتر خنقاً."""
    daily = STATE.get("daily") or {}
    filters = STATE.get("filters") or {}
    L = ["📊 <b>إحصاء NOVA ZERO-WAIT v4.0.2 STRICT</b>", ""]
    if daily.get("date"):
        L.append(f"📅 اليوم {daily['date']}: {daily.get('trades', 0)} صفقة | "
                 f"🟢 {daily.get('wins', 0)} / 🔴 {daily.get('losses', 0)} | "
                 f"صافي بعد العمولة: <b>{daily.get('net', 0.0):+.4f}$</b>")
        if daily.get("best"):
            L.append(f"   الأفضل: {daily['best'].get('symbol', '').replace('USDT','')} "
                     f"({daily['best'].get('net', 0.0):+.4f}$)"
                     + (f" | الأسوأ: {daily['worst'].get('symbol', '').replace('USDT','')} "
                        f"({daily['worst'].get('net', 0.0):+.4f}$)" if daily.get("worst") else ""))
    m = STATE.get("metrics") or {}
    L.append(f"🧮 كلي: {m.get('trades', 0)} صفقة | صافي الخام {m.get('realized_pnl', 0.0):+.4f}$ | "
             f"بعد العمولة: <b>{float(STATE.get('net_fees', 0.0)):+.4f}$</b>")
    paused_syms = []
    now = time.time()
    for sym, streak in (STATE.get("gov_streak") or {}).items():
        if int(streak) >= GOV_MAX_LOSSES and now - float(STATE.get("cooldowns", {}).get(sym, 0.0)) < GOV_SYMBOL_COOLDOWN:
            paused_syms.append(sym.replace("USDT", ""))
    L.append(f"⚖️ حاكم العملات: {len(paused_syms)} تحت العقوبة "
             f"({', '.join(paused_syms) if paused_syms else 'لا شيء'}) — بقية السوق يتداول")
    top = sorted(filters.items(), key=lambda kv: int(kv[1]), reverse=True)[:4]
    line = " | ".join(f"{k}: {v}" for k, v in top if int(v) > 0)
    if line:
        L.append(f"🚧 الفلاتر رفضت: {line}")
    L.append("")
    L.append("💡 أرسل 📋 لسجل الصفقات المفصل صفحةً صفحة.")
    return "\n".join(L)


def maybe_daily_report():
    """تقرير يومي آلي عند الساعة المحددة — مرة واحدة في اليوم."""
    now = datetime.now()
    key = now.strftime("%Y-%m-%d")
    if now.hour == DAILY_REPORT_HOUR and STATE.get("last_daily") != key:
        STATE["last_daily"] = key
        save_state()
        try:
            send_message("🗓 " + build_stats_text(), main_keyboard())
        except Exception as exc:
            log(f"تعذر إرسال التقرير اليومي: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# 3) الرياضيات النقية (ATR فقط — لا مؤشرات بطيئة)
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
    return result


def last_valid(values, default=0.0):
    for value in reversed(values):
        if value is not None:
            return value
    return default


# ══════════════════════════════════════════════════════════════════════════════
# 4) عميل Binance REST الموقّع (مع مراقبة الوزن والتهدئة الذاتية)
# ══════════════════════════════════════════════════════════════════════════════


class BinanceError(Exception):
    def __init__(self, message, code=None, status=None):
        super().__init__(message)
        self.code = code
        self.status = status


class BinanceClient:
    def __init__(self):
        self.base = BINANCE_BASE

    def _after_response(self, response):
        """يقرأ وزن الطلبات من الترويسات ويضبط التهدئة الذاتية عند 429/418."""
        global LAST_USED_WEIGHT, RATE_BACKOFF_UNTIL
        header = response.headers.get("X-MBX-USED-WEIGHT-1M")
        if header:
            try:
                LAST_USED_WEIGHT = int(header)
            except (TypeError, ValueError):
                pass
        if response.status_code == 429:
            retry = response.headers.get("Retry-After")
            try:
                wait_seconds = int(retry)
            except (TypeError, ValueError):
                wait_seconds = 30
            RATE_BACKOFF_UNTIL = max(RATE_BACKOFF_UNTIL, time.time() + max(5, wait_seconds))
        elif response.status_code == 418:
            RATE_BACKOFF_UNTIL = max(RATE_BACKOFF_UNTIL, time.time() + 180)

    def parse(self, response):
        global RATE_BACKOFF_UNTIL
        try:
            payload = response.json()
        except ValueError:
            raise BinanceError(f"استجابة Binance غير صالحة HTTP {response.status_code}", status=response.status_code)
        if isinstance(payload, dict) and payload.get("code") == -1003:
            RATE_BACKOFF_UNTIL = max(RATE_BACKOFF_UNTIL, time.time() + 30)
        if response.status_code >= 400 or (isinstance(payload, dict) and payload.get("code", 0) < 0):
            message = payload.get("msg", "خطأ Binance") if isinstance(payload, dict) else "خطأ Binance"
            raise BinanceError(message, payload.get("code") if isinstance(payload, dict) else None, response.status_code)
        return payload

    def public(self, path, params=None, timeout=12):
        try:
            with HTTP_LIMITER:
                response = SESSION.get(self.base + path, params=params or {}, timeout=timeout)
            self._after_response(response)
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
            with HTTP_LIMITER:
                if method == "GET":
                    response = SESSION.get(self.base + path, params=values, headers=headers, timeout=timeout)
                elif method == "DELETE":
                    response = SESSION.delete(self.base + path, params=values, headers=headers, timeout=timeout)
                else:
                    response = SESSION.post(self.base + path, data=values, headers=headers, timeout=timeout)
            self._after_response(response)
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
                "live": float(payload[-1][4]),
            }
        except (IndexError, TypeError, ValueError):
            return None

    def ticker_24h(self, symbols=None):
        params = {}
        if symbols:
            params["symbols"] = json.dumps(symbols, separators=(",", ":"))
        payload = self.public("/api/v3/ticker/24hr", params, timeout=20)
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

    def get_order_client(self, symbol, client_order_id):
        return self.signed("GET", "/api/v3/order", {"symbol": symbol, "origClientOrderId": client_order_id})

    def cancel_order(self, symbol, order_id):
        return self.signed("DELETE", "/api/v3/order", {"symbol": symbol, "orderId": order_id})

    def cancel_oco(self, symbol, order_list_id):
        return self.signed("DELETE", "/api/v3/orderList", {"symbol": symbol, "orderListId": order_list_id})

    def order_list(self, order_list_id=None, client_order_id=None):
        params = {}
        if order_list_id is not None:
            params["orderListId"] = order_list_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise BinanceError("يجب تحديد orderListId أو origClientOrderId")
        return self.signed("GET", "/api/v3/orderList", params)

    def order_list_by_client_id(self, client_order_id):
        return self.order_list(client_order_id=client_order_id)

    def new_oco(self, params):
        # واجهة OCO الحديثة: above*/below*
        return self.signed("POST", "/api/v3/orderList/oco", params)

    def new_oco_legacy(self, params):
        # الواجهة القديمة فقط: price/stopPrice/stopLimitPrice
        return self.signed("POST", "/api/v3/order/oco", params)

    def open_orders_all(self):
        return self.signed("GET", "/api/v3/openOrders", {})

    def cancel_all(self, symbol):
        return self.signed("DELETE", "/api/v3/openOrders", {"symbol": symbol})


CLIENT = BinanceClient()


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
        trailing = filters.get("TRAILING_DELTA", {})
        step = D(lot.get("stepSize", "0.00000001"))
        SYMBOL_RULES[symbol] = {
            "status": item.get("status"),
            "base": item.get("baseAsset"),
            "quote": item.get("quoteAsset"),
            "tick": D(price.get("tickSize", "0.00000001")),
            "step": step,
            "min_qty": D(lot.get("minQty", "0")),
            "max_qty": D(lot.get("maxQty", "999999999")),
            # فلاتر أوامر MARKET (قد تختلف عن LOT_SIZE في بعض الأزواج)
            "market_step": D(market_lot.get("stepSize", lot.get("stepSize", "0.00000001"))),
            "market_min_qty": D(market_lot.get("minQty", lot.get("minQty", "0"))),
            "min_notional": D(notion.get("minNotional", "0")),
            "min_trailing_below": int(trailing.get("minTrailingBelowDelta", 10)),
            "max_trailing_below": int(trailing.get("maxTrailingBelowDelta", 2000)),
        }
    log(f"قواعد Binance USDT: {len(SYMBOL_RULES)} زوجاً")


def refresh_universe(force=False):
    """أفضل 50 زوجاً ديناميكياً حسب حجم التداول 24 ساعة — بلا قوائم ثابتة."""
    global SYMBOLS, LAST_UNIVERSE_REFRESH, TICKER_CACHE
    now = time.time()
    if not force and SYMBOLS and now - LAST_UNIVERSE_REFRESH < UNIVERSE_REFRESH_EVERY:
        return SYMBOLS
    try:
        tickers = CLIENT.ticker_24h()
        TICKER_CACHE = tickers
        stable = {"USDT", "USDC", "FDUSD", "BUSD", "TUSD", "USDP", "DAI", "USD1"}
        candidates = []
        for symbol, rule in SYMBOL_RULES.items():
            base = str(rule.get("base", "")).upper()
            row = tickers.get(symbol)
            if rule.get("status") != "TRADING" or not row:
                continue
            if base in stable or base.startswith("1000") or base.endswith(("UP", "DOWN", "BULL", "BEAR")):
                continue
            volume = float(row.get("quote_volume", 0.0))
            if volume < MIN_24H_QUOTE_VOLUME:
                continue
            candidates.append((volume, symbol))
        candidates.sort(reverse=True)
        chosen = [symbol for _, symbol in candidates[: max(1, TOP_N_SYMBOLS)]]
        if chosen:
            SYMBOLS = chosen
            LAST_UNIVERSE_REFRESH = now
            log(f"كون HMSM: أفضل {len(SYMBOLS)} زوجاً حسب حجم 24س")
        return SYMBOLS
    except BinanceError as exc:
        log(f"تعذر تحديث كون التداول: {exc}")
        return SYMBOLS


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
# 5) تحليل الفريم 1m (سريع وخفيف) + دفتر Level-1
# ══════════════════════════════════════════════════════════════════════════════


def analyze_frame(raw, interval):
    """تحليل خفيف: شموع مغلقة + ATR(1m) + نسبة حجم. لا مؤشرات بطيئة."""
    if not raw:
        return None
    closed = {key: raw[key][:-1] for key in ("t", "o", "h", "l", "c", "v")}
    if len(closed["c"]) < MIN_CLOSED_CANDLES:
        return None
    c, h, l, o, v = closed["c"], closed["h"], closed["l"], closed["o"], closed["v"]
    # فحص جودة سريع على آخر الشموع فقط (أداء أقصى)
    for i in range(len(c) - 5, len(c)):
        try:
            if not all(math.isfinite(float(x)) for x in (o[i], h[i], l[i], c[i], v[i])):
                return None
            if h[i] < max(o[i], c[i]) or l[i] > min(o[i], c[i]):
                return None
        except (IndexError, TypeError, ValueError):
            return None
    interval_ms = INTERVAL_SECONDS.get(interval, 60) * 1000
    server_now_ms = time.time() * 1000 + TIME_OFFSET_MS
    if closed["t"] and server_now_ms - closed["t"][-1] > interval_ms * 3:
        return None  # بيانات قديمة
    at = atr(h, l, c, ATR_PERIOD)
    atr_value = last_valid(at, 0.0)
    av = sma(v, 20)
    volume_ratio = v[-1] / av[-1] if av and av[-1] else 0.0
    return {
        "interval": interval, "t": closed["t"], "o": o, "h": h, "l": l, "c": c, "v": v,
        "close": c[-1], "live": raw.get("live", c[-1]), "atr": atr_value,
        "atr_pct": atr_value / c[-1] * 100.0 if c[-1] else 0.0,
        "volume_ratio": volume_ratio,
    }


def fetch_frame_cached(symbol, interval, force=False):
    key = (symbol, interval)
    now = time.time()
    if not force:
        with KLINE_CACHE_LOCK:
            cached = KLINE_CACHE.get(key)
            if cached and now - cached["time"] < KLINE_TTL.get(interval, 5):
                return cached["frame"]
    raw = CLIENT.klines(symbol, interval, limit=KLINE_LIMIT)
    frame = analyze_frame(raw, interval) if raw else None
    if frame:
        with KLINE_CACHE_LOCK:
            KLINE_CACHE[key] = {"time": time.time(), "frame": frame}
            while len(KLINE_CACHE) > MAX_KLINE_CACHE_ENTRIES:
                oldest = min(KLINE_CACHE, key=lambda item: KLINE_CACHE[item]["time"])
                KLINE_CACHE.pop(oldest, None)
    return frame


def book_stats(symbol):
    """إحصاءات Level-1: أفضل عرض/طلب + السبريد + اختلال تدفق الأوامر من depth."""
    book = CLIENT.book_ticker(symbol)
    mid = (book["bid"] + book["ask"]) / 2.0
    spread = (book["ask"] - book["bid"]) / mid * 100.0 if mid else 99.0
    # دفتر Testnet اصطناعي؛ عمود Flow يُطبَّق حرفياً على live/demo فقط.
    if BINANCE_ENV == "testnet":
        return {"bid": book["bid"], "ask": book["ask"], "spread_pct": spread, "imbalance": 0.5, "synthetic": True}
    try:
        imbalance = CLIENT.depth(symbol, 20)
    except BinanceError:
        imbalance = 0.5
    return {"bid": book["bid"], "ask": book["ask"], "spread_pct": spread, "imbalance": imbalance, "synthetic": False}


# ══════════════════════════════════════════════════════════════════════════════
# 6) محرك HMSM: MSS + FVG + Order Flow في اللحظة نفسها
# ══════════════════════════════════════════════════════════════════════════════


def detect_mss(frame):
    """Market Structure Shift: إغلاق فوق آخر قمة هيكلية مع إزاحة قوية.

    يجب أن يحدث الكسر على آخر شمعة مغلقة (أحدثها ضمن MSS_MAX_AGE) حتى يكون
    لحظياً تماماً — لا انتظار ولا تخزين.
    """
    h, l, o, c = frame["h"], frame["l"], frame["o"], frame["c"]
    n = len(c)
    if n < MSS_LOOKBACK + MSS_MAX_AGE + 3:
        return None
    atr_value = frame["atr"]
    if atr_value <= 0:
        return None
    for age in range(MSS_MAX_AGE):
        i = n - 1 - age
        body = c[i] - o[i]
        rng = h[i] - l[i]
        if body <= 0 or rng <= 0:
            continue
        if body / rng < MSS_BODY_RATIO:
            continue
        if rng < MSS_MIN_RANGE_ATR * atr_value:
            continue
        window = h[max(0, i - MSS_LOOKBACK): i]
        if not window:
            continue
        prior_high = max(window)
        # الكسر حدث داخل هذه الشمعة: فتح تحت القمة وإغلاق فوقها
        if o[i] <= prior_high < c[i]:
            # وآخر إغلاق ما يزال فوق القمة المكسورة (الهيكل صامد ولم يُرفض فوراً)
            if c[-1] <= prior_high:
                continue
            return {
                "age": age, "index": i, "prior_high": prior_high,
                "close": c[i], "body": body, "range": rng,
                "displacement": rng / atr_value,
            }
    return None


def detect_fvg(frame):
    """أحدث فجوة قيمة عادلة صاعدة غير معبأة ضمن آخر الشموع.

    FVG صاعدة: قاع الشمعة الثالثة فوق قمة الشمعة الأولى، ولم يكسر السعر
    منتصف الفجوة منذ تكوّنها.
    """
    h, l = frame["h"], frame["l"]
    n = len(l)
    atr_value = frame["atr"]
    start = max(0, n - FVG_LOOKBACK)
    best = None
    for i in range(start, n - 2):
        gap_low = h[i]
        gap_high = l[i + 2]
        if gap_high <= gap_low:
            continue
        if atr_value > 0 and (gap_high - gap_low) < FVG_MIN_ATR * atr_value:
            continue
        mid = (gap_low + gap_high) / 2.0
        broken = any(l[j] <= mid for j in range(i + 3, n))
        if broken:
            continue
        best = {"low": gap_low, "high": gap_high, "mid": mid, "index": i, "age": n - 1 - (i + 2)}
    return best


def dynamic_trailing_plan(symbol, price, atr_1m):
    """خطة تتبع ديناميكية بالكامل من ATR(1m) اللحظي لكل عملة.

    activation = entry + 1.5×ATR | trailing distance = 1.2×ATR
    المسافة تُحوَّل إلى Bips لـ Binance مع احترام فلتر TRAILING_DELTA للزوج.
    """
    price = float(price)
    atr_1m = float(atr_1m)
    if price <= 0 or atr_1m <= 0:
        return None
    activation_distance = TRAIL_ACTIVATION_ATR_MULT * atr_1m
    trailing_distance = TRAIL_DISTANCE_ATR_MULT * atr_1m
    raw_bips = max(1, int(round(trailing_distance / price * 10000.0)))
    rule = SYMBOL_RULES.get(symbol, {})
    min_bips = int(rule.get("min_trailing_below", 1))
    max_bips = int(rule.get("max_trailing_below", 10000))
    effective_bips = int(clamp(raw_bips, min_bips, max_bips))
    return {
        "atr_1m": atr_1m,
        "activation_distance": activation_distance,
        "trailing_distance": trailing_distance,
        "activation_price": price + activation_distance,
        "raw_trail_bips": raw_bips,
        "trail_bips": effective_bips,
        "trail_pct": effective_bips / 100.0,
    }


def scan_one_symbol(symbol):
    """عامل فحص مستقل: MSS + FVG + Flow الآن → إشارة، وإلا None فوراً."""
    rule = SYMBOL_RULES.get(symbol)
    if not rule or rule.get("status") != "TRADING":
        return None
    if D(rule.get("min_notional", "0")) > TRADE_NOTIONAL_D * Decimal("0.85"):
        return None  # مركز 10$ لا يمكن حمايته تحت الحد الأدنى للطلب
    try:
        frame = fetch_frame_cached(symbol, SIGNAL_INTERVAL)
        if not frame:
            return None
        # ═══ V4.0: منع العملات النائمة — حركة الدقيقة أقل من الحد ⇒ تجاوز كامل ═══
        if float(frame.get("atr_pct", 0.0) or 0.0) < MIN_ATR_MOVE_PCT:
            with STATE_LOCK:
                STATE["filters"]["dead"] = STATE["filters"].get("dead", 0) + 1
            return None
        # ═══ V4.0: منع السوق النائم — فوليوم أقل من 1.2× متوسطه ⇒ لا شراء ═══
        if float(frame.get("volume_ratio", 0.0) or 0.0) < MIN_VOLUME_RATIO:
            with STATE_LOCK:
                STATE["filters"]["sleepy"] = STATE["filters"].get("sleepy", 0) + 1
            return None
        # ═══ V4.0: حاكم العملة — خسائر متتالية هنا ⇒ تجاوز هذه العملة فقط ═══
        gov_block, gov_why = gov_should_pause(symbol)
        if gov_block:
            with STATE_LOCK:
                STATE["filters"]["gov"] = STATE["filters"].get("gov", 0) + 1
            return None
        # ═══ V4.0: التسليم بشرط الربح — مركز سابق على العملة يجب أن يكون رابحاً ═══
        if PYRAMID_REQUIRE_PROFIT:
            for other in STATE.get("positions", {}).values():
                if other.get("symbol") == symbol:
                    if float(other.get("entry", 0)) <= 0:
                        continue
                    try:
                        probe = CLIENT.book_ticker(symbol)
                        live_px = (probe["bid"] + probe["ask"]) / 2.0
                    except BinanceError:
                        return None
                    if live_px < float(other["entry"]):
                        with STATE_LOCK:
                            STATE["filters"]["pyramid"] = STATE["filters"].get("pyramid", 0) + 1
                        return None
        mss = detect_mss(frame)
        if not mss:
            return None
        fvg = detect_fvg(frame)
        if not fvg:
            return None
        book = book_stats(symbol)
        if BINANCE_ENV != "testnet":
            if book["spread_pct"] > MAX_SPREAD_PCT:
                return None
            if book["imbalance"] < MIN_BOOK_IMBALANCE:
                return None
        price = book["ask"]
        if price <= 0 or price < fvg["mid"]:
            return None  # السعر يجب أن يبقى فوق منتصف الفجوة
        atr_value = float(frame["atr"])
        # ═══ V4.0: الإشارة نفسها تُولد بالقوانين الصارمة (وقف مقصوص + هدف ≥ العمولة) ═══
        strict = strict_stop_target(price, atr_value)
        if strict is None:
            with STATE_LOCK:
                STATE["filters"]["target"] = STATE["filters"].get("target", 0) + 1
            return None   # الهدف لا يغطي العمولة — لا صفقة
        plan = dynamic_trailing_plan(symbol, price, atr_value)
        if not plan:
            return None
        return {
            "symbol": symbol, "price": price, "atr": atr_value, "atr_pct": frame["atr_pct"],
            "volume_ratio": frame["volume_ratio"], "mss": mss, "fvg": fvg, "book": book,
            "stop": strict["stop"],
            "target": strict["target"],
            "trail_bips": plan["trail_bips"], "trail_pct": plan["trail_pct"],
            "activation_price": plan["activation_price"],
            "trailing_distance": plan["trailing_distance"],
            "created_at": time.time(),
        }
    except BinanceError as exc:
        log(f"خطأ فحص {symbol}: {exc}")
        return None
    except Exception as exc:
        log(f"خطأ تحليل {symbol}: {exc}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 7) التنفيذ: LIMIT فوري + OCO مستقل لكل مركز + Trailing ديناميكي
# ══════════════════════════════════════════════════════════════════════════════


def live_execution_allowed():
    if DRY_RUN or not AUTO_TRADE or not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return False
    if BINANCE_ENV == "live" and LIVE_CONFIRM != "I_UNDERSTAND_SPOT_RISK":
        return False
    return True


def circuit_allows_entry():
    """لا قواطع خسائر متتالية ولا حدود يومية — التداول بلا توقف."""
    if kill_switch_active():
        return False, "STOP_TRADING نشط"
    if STATE.get("paused"):
        return False, "الإيقاف المؤقت مفعّل"
    return True, "OK"


def parse_fill(order, fallback_price):
    qty = D(order.get("executedQty", "0"))
    quote = D(order.get("cummulativeQuoteQty", "0"))
    average = quote / qty if qty > 0 and quote > 0 else D(fallback_price)
    return qty, quote, average


def recover_oco_by_client_id(client_order_id):
    """يمنع البيع المزدوج إذا قُبل OCO ثم ضاعت الاستجابة."""
    if not client_order_id:
        return None
    try:
        result = CLIENT.order_list_by_client_id(client_order_id)
        if result and result.get("orderListId") is not None:
            return result
    except BinanceError:
        pass
    return None


def place_initial_oco(symbol, qty, entry, stop_price, target_price):
    """OCO أولي: وقف وهدف مشتقان من ATR، مع fallback للواجهة القديمة."""
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
        result = CLIENT.new_oco(modern)
        return {"type": "OCO", "order_list_id": result.get("orderListId"), "orders": result.get("orders", []), "qty": quantity, "stop": stop, "target": target_trigger}
    except BinanceError as modern_error:
        if modern_error.code not in (-1102, -1128, -2010):
            recovered = recover_oco_by_client_id(modern_client_id)
            if recovered:
                return {"type": "OCO", "order_list_id": recovered.get("orderListId"), "orders": recovered.get("orders", []), "qty": quantity, "stop": stop, "target": target_trigger}
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
            result = CLIENT.new_oco_legacy(legacy)
        except BinanceError as legacy_error:
            recovered = recover_oco_by_client_id(legacy_client_id)
            if recovered:
                return {"type": "OCO_LEGACY", "order_list_id": recovered.get("orderListId"), "orders": recovered.get("orders", []), "qty": quantity, "stop": stop, "target": target_trigger}
            raise legacy_error
        return {"type": "OCO_LEGACY", "order_list_id": result.get("orderListId"), "orders": result.get("orders", []), "qty": quantity, "stop": stop, "target": target_trigger}


def place_trailing_oco(symbol, qty, target_price, trail_bips, reference_price):
    """OCO متحرك: مسافة Trailing Delta بـ Bips مشتقة من ATR اللحظي."""
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
    trailing_client_id = make_client_id("trc")
    params = {
        "symbol": symbol, "side": "SELL", "quantity": dec_str(quantity),
        "aboveType": "TAKE_PROFIT_LIMIT", "abovePrice": dec_str(target_limit),
        "aboveStopPrice": dec_str(target_trigger), "aboveTimeInForce": "GTC",
        "belowType": "STOP_LOSS_LIMIT", "belowPrice": dec_str(below_limit),
        "belowTimeInForce": "GTC", "belowTrailingDelta": bips,
        "listClientOrderId": trailing_client_id, "newOrderRespType": "RESULT",
    }
    try:
        result = CLIENT.new_oco(params)
    except BinanceError:
        result = recover_oco_by_client_id(trailing_client_id)
        if not result:
            raise
    return {"type": "OCO", "order_list_id": result.get("orderListId"), "orders": result.get("orders", []), "qty": quantity, "trail_bips": bips, "target": target_trigger}


def emergency_sell(symbol, qty, reason):
    try:
        rule = SYMBOL_RULES[symbol]
        step = rule.get("market_step", rule["step"])
        min_qty = rule.get("market_min_qty", rule["min_qty"])
        quantity = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), step)
        if quantity < min_qty:
            return None
        result = CLIENT.new_order({"symbol": symbol, "side": "SELL", "type": "MARKET", "quantity": dec_str(quantity), "newClientOrderId": make_client_id("pan"), "newOrderRespType": "FULL"})
        log(f"خروج طارئ {symbol}: {reason}")
        return result
    except BinanceError as exc:
        log(f"فشل الخروج الطارئ {symbol}: {exc}")
        return None


def sellable_qty(symbol, qty, price):
    """كمية قابلة للبيع فعلاً (فلاتر LOT/MARKET_LOT/NOTIONAL) أو None."""
    rule = SYMBOL_RULES.get(symbol)
    if not rule:
        return None
    sell_qty = round_step(D(qty) * (Decimal("1") - D(FEE_BUFFER)), rule.get("market_step", rule["step"]))
    if sell_qty < rule.get("market_min_qty", rule.get("min_qty", D("0"))):
        return None
    if rule.get("min_notional", D("0")) > 0 and sell_qty * D(price) < rule["min_notional"]:
        return None
    return sell_qty


def add_dust(symbol, qty, cost, reason):
    """يسجل كمية لا يمكن بيعها حالياً؛ تُباع تلقائياً عند بلوغها الحد الأدنى."""
    changed = False
    with STATE_LOCK:
        dust = STATE.setdefault("dust", [])
        for item in dust:
            if item.get("symbol") == symbol:
                item["qty"] = dec_str(D(item.get("qty", "0")) + D(qty))
                item["cost"] = dec_str(D(item.get("cost", "0")) + D(cost))
                changed = True
                break
        if not changed:
            dust.append({
                "symbol": symbol, "qty": dec_str(D(qty)), "cost": dec_str(D(cost)),
                "since": time.time(), "last_attempt": 0.0, "reason": str(reason),
            })
    save_state()
    send_message(
        f"🧪 <b>Dust — {coin_name(symbol)}</b>\n"
        f"الكمية: <code>{dec_str(D(qty))}</code> غير قابلة للبيع حالياً ({esc(reason)})\n"
        "ستُباع تلقائياً فور بلوغ قيمتها الحد الأدنى للطلب."
    )
    log(f"Dust {symbol}: qty={dec_str(D(qty))} reason={reason}")


def sell_dust(books):
    """يبيع الـ Dust المتراكم تلقائياً متى أصبح قابلًا للبيع."""
    dust_items = list(STATE.get("dust", []))
    if not dust_items:
        return
    for item in dust_items:
        symbol = item.get("symbol", "")
        qty = D(item.get("qty", "0"))
        cost = D(item.get("cost", "0"))
        rule = SYMBOL_RULES.get(symbol)
        if not rule or qty <= 0:
            continue
        now = time.time()
        if now - float(item.get("last_attempt", 0.0)) < 60:
            continue
        price = books.get(symbol)
        if price is None:
            try:
                book = CLIENT.book_ticker(symbol)
                price = (book["bid"] + book["ask"]) / 2.0
                books[symbol] = price
            except BinanceError:
                continue
        sell_qty = sellable_qty(symbol, qty, price)
        if sell_qty is None:
            with STATE_LOCK:
                for entry in STATE.get("dust", []):
                    if entry.get("symbol") == symbol:
                        entry["last_attempt"] = now
            continue
        try:
            order = CLIENT.new_order({
                "symbol": symbol, "side": "SELL", "type": "MARKET",
                "quantity": dec_str(sell_qty), "newClientOrderId": make_client_id("dst"),
                "newOrderRespType": "FULL",
            })
        except BinanceError as exc:
            log(f"فشل بيع Dust {symbol}: {exc}")
            with STATE_LOCK:
                for entry in STATE.get("dust", []):
                    if entry.get("symbol") == symbol:
                        entry["last_attempt"] = now
            continue
        _, exit_quote, exit_average = parse_fill(order, price)
        pnl = float(exit_quote) - float(cost) if cost > 0 else float(exit_quote)
        with STATE_LOCK:
            STATE["dust"] = [x for x in STATE.get("dust", []) if x.get("symbol") != symbol]
            STATE["metrics"]["realized_pnl"] += pnl
        save_state()
        send_message(f"♻️ <b>بيع Dust — {coin_name(symbol)}</b>\nالكمية: <code>{dec_str(sell_qty)}</code> | النتيجة: <b>{pnl:+.4f}$</b>")
        log(f"بيع Dust {symbol}: qty={dec_str(sell_qty)} pnl={pnl:+.4f}$")


def wait_limit_fill(symbol, order_id):
    """ينتظر تنفيذ LIMIT عدواني؛ يعيد (order, certain).

    certain=True فقط عند اليقين بالحالة النهائية (تنفيذ/إلغاء مؤكد)؛
    أما فشل الشبكة فيعيد certain=False ليظل الأمر مسجلاً في pending
    وتتولاه المصالحة لاحقاً بدل افتراض اللا-تعبئة.
    """
    deadline = time.time() + LIMIT_FILL_TIMEOUT
    network_failures = 0
    while True:
        try:
            order = CLIENT.get_order(symbol, order_id)
            network_failures = 0
        except BinanceError as exc:
            log(f"تعذر جلب أمر الدخول {symbol}: {exc}")
            network_failures += 1
            if network_failures >= 3 or time.time() >= deadline:
                return None, False  # غير مؤكد — المصالحة تتكفل
            time.sleep(0.3)
            continue
        executed = D(order.get("executedQty", "0"))
        status = order.get("status")
        if executed > 0 and status == "FILLED":
            return order, True
        if status in ("CANCELED", "REJECTED", "EXPIRED", "EXPIRED_IN_MATCH", "PENDING_CANCEL"):
            return (order if executed > 0 else None), True
        if time.time() >= deadline:
            break
        time.sleep(LIMIT_FILL_POLL)
    try:
        CLIENT.cancel_order(symbol, order_id)
    except BinanceError as exc:
        if exc.code != -2011:
            log(f"تعذر إلغاء أمر الدخول {symbol}: {exc}")
    try:
        order = CLIENT.get_order(symbol, order_id)
        if order and D(order.get("executedQty", "0")) > 0:
            return order, True
        if order:
            return None, True  # ملغى بلا تعبئة — يقين
    except BinanceError:
        pass
    return None, False  # الحالة النهائية غير معروفة


def count_symbol_positions(symbol):
    return sum(1 for p in list(STATE.get("positions", {}).values()) if p.get("symbol") == symbol)


def reserve_entry(symbol):
    """حجز ذري: حتى 3 مراكز متزامنة لكل عملة (Pyramiding مستقل)."""
    global RESERVED_QUOTE
    with ENTRY_LOCK:
        current = count_symbol_positions(symbol)
        reserved = ENTRY_RESERVATIONS.get(symbol, 0)
        if current + reserved >= MAX_POSITIONS_PER_SYMBOL:
            return False
        if kill_switch_active() or STATE.get("paused"):
            return False
        ENTRY_RESERVATIONS[symbol] = reserved + 1
        RESERVED_QUOTE += TRADE_NOTIONAL_D
        return True


def release_entry(symbol):
    global RESERVED_QUOTE
    with ENTRY_LOCK:
        reserved = ENTRY_RESERVATIONS.get(symbol, 0)
        if reserved <= 1:
            ENTRY_RESERVATIONS.pop(symbol, None)
        else:
            ENTRY_RESERVATIONS[symbol] = reserved - 1
        RESERVED_QUOTE = max(Decimal("0"), RESERVED_QUOTE - TRADE_NOTIONAL_D)


def execute_entry(signal):
    """Zero-Wait: LIMIT BUY فوري على Ask ثم OCO مستقل فور الامتلاء.

    أمر الدخول يُسجل في pending_entries قبل إرساله ويُحذف بعد اليقين
    بالحالة النهائية؛ بحيث لا يمكن لأي انقطاع شبكة/انهيار أن يُنتج
    أمراً يتيمًا أو عملات بلا حماية.
    """
    symbol = signal["symbol"]
    allowed, reason = circuit_allows_entry()
    if not allowed:
        log(f"تخطي {symbol}: {reason}")
        return False
    # ═══ V4.0: ميزانية الأوامر — الحماية من الحظر حتى في أعنف زحمة ═══
    if not budget_take(3):
        log(f"تخطي {symbol}: ميزانية الأوامر ممتلئة ({ORDER_BUDGET_MAX}/{ORDER_BUDGET_WINDOW:.0f}ث)")
        return False
    rule = SYMBOL_RULES.get(symbol)
    if not rule or rule.get("status") != "TRADING":
        return False
    if not live_execution_allowed():
        if DRY_RUN:
            send_message("🟡 <b>إشارة HMSM مؤكدة — بدون تنفيذ</b>\n\n" + entry_message(signal))
        else:
            log(f"إشارة مؤكدة بدون تنفيذ (التنفيذ غير مفعّل): {symbol}")
        mark_cooldown(symbol)
        return False
    entry_qty = Decimal("0")
    entry_client_id = make_client_id("hms")
    pending_registered = False
    try:
        account = CLIENT.account()
        free_quote = CLIENT.free_balance(rule.get("quote", "USDT"), account)
        with ENTRY_LOCK:
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
        # سجل الأوامر المعلقة: يُكتب قبل الإرسال لضمان التتبع حتى عند الانهيار
        with STATE_LOCK:
            STATE["pending_entries"][entry_client_id] = {
                "symbol": symbol, "client_order_id": entry_client_id, "order_id": None,
                "qty": dec_str(qty), "price": dec_str(price), "atr": float(signal["atr"]),
                "placed_at": time.time(), "active": True,
            }
        pending_registered = True
        save_state()
        order = CLIENT.new_order({
            "symbol": symbol, "side": "BUY", "type": "LIMIT", "timeInForce": "GTC",
            "quantity": dec_str(qty), "price": dec_str(price),
            "newClientOrderId": entry_client_id, "newOrderRespType": "FULL",
        })
        order_id = order.get("orderId") if isinstance(order, dict) else None
        if not order_id:
            # استجابة بلا orderId: نجلب الأمر بمعرّف العميل
            try:
                order = CLIENT.get_order_client(symbol, entry_client_id)
                order_id = order.get("orderId")
            except BinanceError:
                order_id = None
        if order_id:
            with STATE_LOCK:
                record = STATE["pending_entries"].get(entry_client_id)
                if record is not None:
                    record["order_id"] = order_id
        certain = True
        if not order_id or (isinstance(order, dict) and order.get("status") != "FILLED"):
            if order_id:
                order, certain = wait_limit_fill(symbol, order_id)
            else:
                certain = False
        if not certain:
            # الحالة غير المؤكدة: يبقى السجل معلقاً وتتولاه المصالحة
            log(f"حالة أمر الدخول غير مؤكدة لـ {symbol}; ستتولاه المصالحة")
            mark_cooldown(symbol)
            return False
        if not order or D(order.get("executedQty", "0")) <= 0:
            with STATE_LOCK:
                STATE["pending_entries"].pop(entry_client_id, None)
            save_state()
            mark_cooldown(symbol)
            log(f"لم ينفذ LIMIT في {symbol}؛ تجاوز فوري")
            return False
        entry_qty, quote_filled, entry = parse_fill(order, price)
        # حماية من سباق المصالحة: التعبئة استُعيدت مسبقاً من خيط آخر
        with STATE_LOCK:
            already_recovered = any(p.get("entry_client_id") == entry_client_id for p in STATE["positions"].values())
        if already_recovered:
            log(f"تعبئة {symbol} استُعيدة مسبقاً بالمصالحة؛ منع التسجيل المزدوج")
            with STATE_LOCK:
                STATE["pending_entries"].pop(entry_client_id, None)
            save_state()
            mark_cooldown(symbol)
            return False
        # تعبئة جزئية أصغر من الحد الأدنى للبيع → Dust متتبع بدل عملات ضائعة
        if sellable_qty(symbol, entry_qty, float(entry) * 0.95) is None:
            add_dust(symbol, entry_qty, quote_filled, "تعبئة جزئية دون الحد الأدنى للبيع")
            with STATE_LOCK:
                STATE["pending_entries"].pop(entry_client_id, None)
            save_state()
            mark_cooldown(symbol)
            return False
        atr_d = D(str(signal["atr"]))
        # ═══ V4.0: الوقف الصارم — بعد تعبئة الأمر: قصّ فقط (المركز لنا ولا يتيمة) ═══
        # رفض الهدف حدث قبل إرسال الأمر في scan_one_symbol؛ هنا نملك العملة فعلاً
        strict = strict_stop_target(float(entry), float(atr_d), reject_below_fee=False)
        if strict is None:      # مستحيل عملياً (entry>0) — حارس شكلي فقط
            stop_price = round_price(entry - D(str(STOP_ATR_MULT)) * atr_d, rule["tick"], "down")
            target_price = round_price(entry + D(str(TP_ATR_MULT)) * atr_d, rule["tick"], "up")
        else:
            stop_price = D(str(round(strict["stop"], 8)))
            target_price = D(str(round(strict["target"], 8)))
        plan = dynamic_trailing_plan(symbol, float(entry), float(atr_d))
        trail_bips = int(plan["trail_bips"]) if plan else int(signal["trail_bips"])
        activation_price = float(plan["activation_price"]) if plan else float(entry) + TRAIL_ACTIVATION_ATR_MULT * float(atr_d)
        trailing_distance = float(plan["trailing_distance"]) if plan else float(signal["trailing_distance"])
        protection = place_initial_oco(symbol, entry_qty, float(entry), float(stop_price), float(target_price))
        pid = new_position_id(symbol)
        position = {
            "pid": pid, "symbol": symbol, "entry_client_id": entry_client_id,
            "entry": float(entry), "qty": dec_str(protection["qty"]),
            "quote_qty": float(quote_filled or TRADE_NOTIONAL_D),
            "stop": float(protection["stop"]), "target": float(protection["target"]),
            "trail_bips": trail_bips, "atr_1m": float(atr_d),
            "activation_price": activation_price, "trailing_distance": trailing_distance,
            "order_list_id": protection.get("order_list_id"),
            "order_ids": [x.get("orderId") for x in protection.get("orders", []) if x.get("orderId") is not None],
            "protection_type": protection.get("type"), "trailing_active": False,
            "be_armed": False, "strict_dist": strict["dist"],
            "opened_at": time.time(), "imbalance": signal["book"]["imbalance"],
            "mss_prior_high": signal["mss"]["prior_high"],
            "fvg_low": signal["fvg"]["low"], "fvg_high": signal["fvg"]["high"],
        }
        with STATE_LOCK:
            STATE["positions"][pid] = position
            STATE["pending_entries"].pop(entry_client_id, None)
            STATE["metrics"]["trades"] += 1
            STATE["cooldowns"][symbol] = time.time()
        save_state()
        send_message(entry_message(signal, position))
        log(f"دخول HMSM {symbol} pid={pid} entry={fmt_price(symbol, entry)} qty={position['qty']} protection={protection['type']}")
        return True
    except BinanceError as exc:
        # رفض صريح من Binance = لا أمر موجود؛ خطأ شبكة = قد يكون الأصل قائماً
        if exc.code is None and exc.status is None and pending_registered:
            log(f"شبكة غير مؤكدة أثناء دخول {symbol}; المصالحة ستتولى الأمر")
            mark_cooldown(symbol)
            return False
        if pending_registered:
            with STATE_LOCK:
                STATE["pending_entries"].pop(entry_client_id, None)
            save_state()
        if entry_qty > 0 and live_execution_allowed():
            exit_order = emergency_sell(symbol, entry_qty, "فشل حماية الدخول")
            if exit_order:
                account_salvage(symbol, quote_filled, exit_order, "بيع إنقاذ: فشل حماية الدخول")
            else:
                add_dust(symbol, entry_qty, quote_filled, "فشل حماية الدخول والبيع الطارئ")
        log(f"فشل دخول {symbol}: {exc}")
        return False
    except Exception as exc:
        if pending_registered:
            with STATE_LOCK:
                STATE["pending_entries"].pop(entry_client_id, None)
            save_state()
        if entry_qty > 0 and live_execution_allowed():
            exit_order = emergency_sell(symbol, entry_qty, "خطأ غير متوقع بعد الدخول")
            if exit_order:
                account_salvage(symbol, quote_filled, exit_order, "بيع إنقاذ: خطأ غير متوقع بعد الدخول")
            else:
                add_dust(symbol, entry_qty, quote_filled, "خطأ غير متوقع وفشل البيع الطارئ")
        log(f"خطأ دخول {symbol}: {exc}\n{traceback.format_exc()[-400:]}")
        return False
    finally:
        with STATE_LOCK:
            record = STATE["pending_entries"].get(entry_client_id)
            if record is not None:
                record["active"] = False


def reconcile_pending_entries():
    """مصالحة أوامر الدخول المعلقة: لا أمر يتيم ولا عملات بلا حماية.

    تعالج السجلات الأقدم من 30 ثانية غير النشطة (أو الأقدم من 120 ثانية
    حتى لو كانت نشطة — خيط ميت)، وتفعل واحدة من ثلاث:
    تعبئة غير متتبعة → بناء مركز+OCO أو Dust | أمر جديد → إلغاء | منتهٍ → حذف.
    """
    now = time.time()
    records = list(STATE.get("pending_entries", {}).items())
    if not records:
        return
    for client_id, record in records:
        try:
            age = now - float(record.get("placed_at", 0.0))
            if record.get("active") and age < 120:
                continue  # خيط الدخول ما يزال يعمل
            if age < 30:
                continue  # ضمن نافذة الانتظار الطبيعية
            symbol = record.get("symbol", "")
            order_id = record.get("order_id")
            cid = record.get("client_order_id") or client_id
            try:
                order = CLIENT.get_order(symbol, order_id) if order_id else CLIENT.get_order_client(symbol, cid)
            except BinanceError as exc:
                if exc.code == -2013 and not order_id:
                    # استعلام بمعرّف العميل عن أمر غير موجود = لم يقبله الخادم إطلاقاً
                    with STATE_LOCK:
                        STATE["pending_entries"].pop(client_id, None)
                    save_state()
                    log(f"مصالحة {symbol}: الأمر لم يصل للخادم؛ حُذف السجل {cid}")
                    continue
                attempts = int(record.get("reconcile_attempts", 0)) + 1
                record["reconcile_attempts"] = attempts
                if attempts > 60:
                    with STATE_LOCK:
                        STATE["pending_entries"].pop(client_id, None)
                    save_state()
                    send_message(f"⚠️ تعذر حسم أمر دخول معلق {symbol} بعد {attempts} محاولة؛ حُذف السجل. تحقق من محفظتك.")
                else:
                    log(f"مصالحة {symbol}: تعذر جلب الأمر ({exc})؛ إعادة المحاولة لاحقاً")
                continue
            executed = D(order.get("executedQty", "0"))
            if executed > 0:
                recover_filled_entry(client_id, record, order)
            elif order.get("status") in ("NEW", "PARTIALLY_FILLED"):
                try:
                    CLIENT.cancel_order(symbol, order.get("orderId"))
                except BinanceError as exc:
                    log(f"مصالحة {symbol}: تعذر إلغاء الأمر يتيم ({exc})")
                    continue
                with STATE_LOCK:
                    STATE["pending_entries"].pop(client_id, None)
                save_state()
                log(f"مصالحة: أُلغي أمر دخول يتيم {symbol} #{order.get('orderId')}")
            else:
                with STATE_LOCK:
                    STATE["pending_entries"].pop(client_id, None)
                save_state()
                log(f"مصالحة: حُذف سجل دخول منتهٍ {symbol}")
        except Exception as exc:
            log(f"خطأ مصالحة دخول {client_id}: {exc}")


def account_salvage(symbol, entry_quote, exit_order, reason):
    """محاسبة صفقة إنقاذ (شراء+بيع مباشر دون مركز مُدار)."""
    try:
        exit_qty, exit_quote, exit_average = parse_fill(exit_order, 0)
        pnl = float(exit_quote) - float(entry_quote)
        with STATE_LOCK:
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
        try:
            log_book_add(symbol, "salvage", float(entry_quote) / max(float(exit_qty), 1e-12),
                         float(exit_average), float(exit_qty), pnl, reason)
        except Exception:
            pass
        record_trade([datetime.now(timezone.utc).isoformat(), symbol, "salvage", float(entry_quote), float(exit_average), float(exit_qty), round(pnl, 8), reason, BINANCE_ENV])
        save_state()
        send_message(close_message(symbol, {"pid": "salvage"}, pnl, float(entry_quote), float(exit_average), reason))
    except Exception as exc:
        log(f"خطأ محاسبة الإنقاذ {symbol}: {exc}")


def recover_filled_entry(client_id, record, order):
    """يستعيد تعبئة غير متتبعة: مركز+OCO، أو بيع إنقاذ، أو Dust."""
    symbol = record.get("symbol", "")
    executed, quote_filled, average = parse_fill(order, record.get("price", 0))
    cid = record.get("client_order_id") or client_id

    def drop():
        STATE["pending_entries"].pop(client_id, None)

    if executed <= 0:
        with STATE_LOCK:
            drop()
        save_state()
        return
    # منع التكرار إن كان المركز مسجلاً بالفعل بنفس أمر الدخول
    with STATE_LOCK:
        already = any(p.get("entry_client_id") == cid for p in STATE["positions"].values())
    if already:
        with STATE_LOCK:
            drop()
        save_state()
        return
    rule = SYMBOL_RULES.get(symbol)
    if not rule:
        add_dust(symbol, executed, quote_filled, "استعادة تعبئة بقواعد غير معروفة")
        with STATE_LOCK:
            drop()
        save_state()
        return
    # احترام سقف 3 مراكز: الرمز ممتلئ → بيع إنقاذ فوري بدل كسر السقف
    if count_symbol_positions(symbol) >= MAX_POSITIONS_PER_SYMBOL:
        exit_order = emergency_sell(symbol, executed, "استعادة تعبئة والرمز بلغ سقف المراكز")
        if exit_order:
            account_salvage(symbol, quote_filled, exit_order, "بيع إنقاذ: استعادة والرمز ممتلئ")
        else:
            add_dust(symbol, executed, quote_filled, "فشل بيع الإنقاذ والرمز ممتلئ")
        with STATE_LOCK:
            drop()
        save_state()
        return
    atr_now = float(record.get("atr", 0.0))
    try:
        frame = fetch_frame_cached(symbol, "1m", force=True)
        if frame and frame.get("atr", 0.0) > 0:
            atr_now = float(frame["atr"])
    except Exception:
        pass
    if atr_now <= 0 or sellable_qty(symbol, executed, float(average) * 0.95) is None:
        add_dust(symbol, executed, quote_filled, "استعادة تعبئة غير قابلة للحماية")
        with STATE_LOCK:
            drop()
        save_state()
        return
    entry = average
    atr_d = D(str(atr_now))
    stop_price = entry - D(str(STOP_ATR_MULT)) * atr_d
    target_price = entry + D(str(TP_ATR_MULT)) * atr_d
    try:
        protection = place_initial_oco(symbol, executed, float(entry), float(stop_price), float(target_price))
    except BinanceError as exc:
        log(f"مصالحة {symbol}: فشل OCO للاستعادة ({exc})؛ بيع طارئ")
        exit_order = emergency_sell(symbol, executed, "فشل OCO أثناء الاستعادة")
        if exit_order:
            account_salvage(symbol, quote_filled, exit_order, "بيع إنقاذ: فشل OCO أثناء الاستعادة")
        else:
            add_dust(symbol, executed, quote_filled, "فشل البيع الطارئ أثناء الاستعادة")
        with STATE_LOCK:
            drop()
        save_state()
        return
    plan = dynamic_trailing_plan(symbol, float(entry), float(atr_d))
    pid = new_position_id(symbol)
    position = {
        "pid": pid, "symbol": symbol, "entry_client_id": client_id,
        "entry": float(entry), "qty": dec_str(protection["qty"]),
        "quote_qty": float(quote_filled or 0), "stop": float(protection["stop"]),
        "target": float(protection["target"]),
        "trail_bips": int(plan["trail_bips"]) if plan else 10,
        "atr_1m": float(atr_d),
        "activation_price": float(plan["activation_price"]) if plan else float(entry) + TRAIL_ACTIVATION_ATR_MULT * float(atr_d),
        "trailing_distance": float(plan["trailing_distance"]) if plan else 0.0,
        "order_list_id": protection.get("order_list_id"),
        "order_ids": [x.get("orderId") for x in protection.get("orders", []) if x.get("orderId") is not None],
        "protection_type": protection.get("type"), "trailing_active": False,
        "opened_at": time.time(), "imbalance": 0.5, "recovered": True,
    }
    with STATE_LOCK:
        STATE["positions"][pid] = position
        drop()
        STATE["metrics"]["trades"] += 1
        STATE["cooldowns"][symbol] = time.time()
    save_state()
    send_message(
        f"🔁 <b>استعادة مركز يتيم — {coin_name(symbol)}</b>\n"
        f"المركز: <code>{pid}</code> | الدخول: <code>{fmt_price(symbol, entry)}</code> | الكمية: <code>{position['qty']}</code>\n"
        f"وقف ATR: <code>{fmt_price(symbol, stop_price)}</code> | هدف ATR: <code>{fmt_price(symbol, target_price)}</code>\n"
        "تم ربط حماية OCO بعد مصالحة أمر دخول غير مؤكد."
    )
    log(f"مصالحة: استعادة مركز {pid} على {symbol} entry={fmt_price(symbol, entry)}")


def order_status(position):
    symbol = position["symbol"]
    orders = []
    for order_id in position.get("order_ids", []):
        if order_id is None:
            continue
        try:
            orders.append(CLIENT.get_order(symbol, order_id))
        except BinanceError as exc:
            log(f"تعذر جلب أمر {order_id}: {exc}")
    for order in orders:
        if order.get("status") == "FILLED" and D(order.get("executedQty", "0")) > 0:
            return order
    return None


def finalize_position(pid, position, exit_order, reason, exit_price=None):
    """إغلاق مركز مستقل: تحديث الإحصاءات وعدّاد الخسائر المتتالية (بلا قواطع)."""
    exit_qty, exit_quote, exit_average = parse_fill(exit_order or {}, position.get("entry", 0))
    if exit_price is not None:
        exit_average = D(exit_price)
        exit_qty = D(position.get("qty", 0))
    entry = float(position.get("entry", 0))
    qty = float(position.get("qty", 0))
    exit_price_value = float(exit_average)
    pnl = (exit_price_value - entry) * min(qty, float(exit_qty) if exit_qty else qty)
    symbol = position.get("symbol", "")
    net_after_fee = log_book_add(symbol, pid, entry, exit_price_value,
                                 min(qty, float(exit_qty) if exit_qty else qty), pnl, reason)
    with STATE_LOCK:
        metrics = STATE["metrics"]
        metrics["realized_pnl"] += pnl
        # ═══ V4.0.2: التصنيف بالصافي بعد العمولة — خام صفر مع عمولة = خسارة حقيقية ═══
        if net_after_fee >= 0:
            metrics["wins"] += 1
            metrics["consecutive_losses"] = 0
            # الفوز الصافي يصفرّ عقارب حاكم هذه العملة فقط
            STATE.setdefault("gov_streak", {})[symbol] = 0
        else:
            metrics["losses"] += 1
            metrics["consecutive_losses"] = int(metrics.get("consecutive_losses", 0)) + 1
            # الحاكم — 3 خسائر صافية متتالية ⇒ عقوبة على هذه العملة فقط 10د
            streak = int(STATE.setdefault("gov_streak", {}).get(symbol, 0)) + 1
            STATE["gov_streak"][symbol] = streak
            gov_penalty = streak >= GOV_MAX_LOSSES
        STATE["positions"].pop(pid, None)
        STATE["cooldowns"][symbol] = time.time()
    record_trade([datetime.now(timezone.utc).isoformat(), symbol, pid, entry, exit_price_value, qty, round(pnl, 8), reason, BINANCE_ENV])
    save_state()
    fee_note = (f"\n💰 <b>الصافي بعد العمولة المحسوبة ({FEE_SIM_PCT:g}%): "
                f"{net_after_fee:+.4f}$</b>")
    gov_note = ""
    if net_after_fee < 0 and locals().get("gov_penalty"):
        gov_note = (f"\n⚖️ <b>حاكم العملة:</b> {GOV_MAX_LOSSES} خسائر متتالية على "
                    f"{coin_name(symbol)} — تجاوزها {GOV_SYMBOL_COOLDOWN // 60} دقائق "
                    f"(بقية السوق يتداول طبيعي).")
    send_message(close_message(symbol, position, pnl, entry, exit_price_value, reason)
                 + fee_note + gov_note)
    log(f"إغلاق {pid}: pnl={pnl:+.6f}$ net_after_fee={net_after_fee:+.6f}$ reason={reason}")


def arm_breakeven(pid, position, current_price):
    """V4.0 — قفل الأرباح: إلغاء OCO الحالي ووضع وقف جديد فوق الدخول.

    من هذه اللحظة الصفقة لا يمكن أن تتحول لخسارة، والهدف الأصلي يبقى قائماً،
    والترقب المتحرك (1.5×ATR) يبقى ممكناً لاحقاً فوق القفل.
    """
    symbol = position["symbol"]
    if position.get("be_armed"):
        return True
    try:
        budget_take(2, force=True)          # حماية الأرباح لا تنتظر الميزانية
        if position.get("order_list_id"):
            try:
                CLIENT.cancel_oco(symbol, position["order_list_id"])
            except BinanceError:
                filled = order_status(position)
                if filled:
                    finalize_position(pid, position, filled, "نفذ OCO أثناء قفل الأرباح")
                    return False
                raise
        new_stop = be_lock_price(position["entry"])
        protection = place_initial_oco(symbol, D(position["qty"]), float(position["entry"]),
                                       float(new_stop), float(position["target"]))
        position.update({
            "order_list_id": protection.get("order_list_id"),
            "order_ids": [x.get("orderId") for x in protection.get("orders", []) if x.get("orderId") is not None],
            "stop": float(protection.get("stop", new_stop)),
            "be_armed": True,
            # V4.0.1: الكمية القابلة للبيع قد تُقصّ طفيفاً في إعادة التركيب — نُحدّثها
            # كي لا يحاول أي خروج طارئ بيع أكثر مما نملك
        })
        if protection.get("qty"):
            position["qty"] = dec_str(D(protection["qty"]))
        save_state()
        send_message(
            f"🛡 <b>قفل الأرباح — {coin_name(symbol)}</b>\n"
            f"المركز: <code>{pid}</code> | السعر: <code>{fmt_price(symbol, current_price)}</code>\n"
            f"الوقف انتقل إلى <code>{fmt_price(symbol, new_stop)}</code> (+{BREAKEVEN_LOCK_PCT:g}%)\n"
            f"🔒 الصفقة الآن ربح مضمون — والهدف <code>{fmt_price(symbol, position['target'])}</code> باقٍ."
        )
        return True
    except BinanceError as exc:
        log(f"فشل قفل الأرباح لـ {pid}: {exc}")
        exit_order = emergency_sell(symbol, D(position["qty"]), "فشل قفل الأرباح")
        if exit_order:
            finalize_position(pid, position, exit_order, "خروج طارئ بعد فشل القفل")
        return False


def activate_trailing(pid, position, current_price):
    """يستبدل OCO الثابت بـ OCO متحرك بمسافة ATR لحظية (ديناميكي 100%)."""
    symbol = position["symbol"]
    if position.get("trailing_active"):
        return True
    try:
        if position.get("order_list_id"):
            try:
                CLIENT.cancel_oco(symbol, position["order_list_id"])
            except BinanceError:
                filled = order_status(position)
                if filled:
                    finalize_position(pid, position, filled, "نفذ OCO أثناء التحويل للتتبع")
                    return False
                raise
        atr_now = float(position.get("atr_1m", 0.0))
        try:
            frame = fetch_frame_cached(symbol, "1m", force=True)
            if frame and frame.get("atr", 0.0) > 0:
                atr_now = float(frame["atr"])
        except Exception:
            pass
        plan = dynamic_trailing_plan(symbol, current_price, atr_now) if atr_now > 0 else None
        trail_bips = int(plan["trail_bips"]) if plan else int(position.get("trail_bips", 10))
        # ═══ V4.0: أرضية الترقب — إن كان وقف التتبع أدنى من قفل الأرباح نرفض التنزيل ═══
        trail_pct_now = trail_bips / 100.0
        if (position.get("be_armed")
                and current_price * (1 - trail_pct_now / 100.0) < be_lock_price(position["entry"])):
            with STATE_LOCK:
                STATE["filters"]["trail-floor"] = STATE["filters"].get("trail-floor", 0) + 1
            return True      # قفل الأرباح أقوى — نبقيه ونؤجل الترقب لقمة أعلى
        protection = place_trailing_oco(symbol, D(position["qty"]), position["target"], trail_bips, current_price)
        position.update({
            "order_list_id": protection.get("order_list_id"),
            "order_ids": [x.get("orderId") for x in protection.get("orders", []) if x.get("orderId") is not None],
            "protection_type": "OCO", "trailing_active": True,
            "trail_bips": trail_bips,
            "atr_1m": atr_now if atr_now > 0 else position.get("atr_1m"),
        })
        save_state()
        send_message(
            f"🛤 <b>تفعيل الوقف المتحرك — {coin_name(symbol)}</b>\n"
            f"المركز: <code>{pid}</code>\n"
            f"السعر: <code>{fmt_price(symbol, current_price)}</code> تجاوز <code>{fmt_price(symbol, position.get('activation_price'))}</code>\n"
            f"ATR(1m) اللحظي: <b>{atr_now:.8g}</b> | مسافة التتبع: <b>{TRAIL_DISTANCE_ATR_MULT}×ATR</b>\n"
            f"Trailing Delta: <b>{trail_bips} bips</b>"
        )
        return True
    except BinanceError as exc:
        log(f"فشل تفعيل trailing لـ {pid}: {exc}")
        exit_order = emergency_sell(symbol, D(position["qty"]), "فشل تركيب الوقف المتحرك")
        if exit_order:
            finalize_position(pid, position, exit_order, "خروج طارئ بعد فشل trailing")
        return False


def monitor_position(pid, position, open_ids, books):
    symbol = position["symbol"]
    order_ids = [oid for oid in position.get("order_ids", []) if oid is not None]
    if not order_ids:
        log(f"مركز {pid} بلا حماية مسجلة؛ تخطي الدورة")
        return
    if open_ids is not None:
        still_open = any((symbol, oid) in open_ids for oid in order_ids)
        if not still_open:
            filled = order_status(position)
            if filled:
                finalize_position(pid, position, filled, "تنفيذ OCO/STOP على Binance")
                return
            log(f"اختفت حماية {pid} دون تنفيذ؛ محاولة خروج طارئ")
            exit_order = emergency_sell(symbol, D(position.get("qty", "0")), "اختفاء الحماية")
            if exit_order:
                finalize_position(pid, position, exit_order, "خروج طارئ بعد اختفاء OCO")
                return
            # سقف المحاولات: تحويل إلى Dust متتبع بدل حلقة بيع لا نهائية
            failures = int(position.get("sell_failures", 0)) + 1
            position["sell_failures"] = failures
            if failures >= 5:
                add_dust(symbol, D(position.get("qty", "0")), Decimal("0"), "تعذر البيع الطارئ مراراً (خُصمت القيمة بالكامل)")
                finalize_position(pid, position, None, "تحويل إلى Dust بعد فشل البيع", exit_price=0)
            return
    else:
        filled = order_status(position)
        if filled:
            finalize_position(pid, position, filled, "تنفيذ OCO/STOP على Binance")
            return
    if position.get("trailing_active"):
        return
    price = books.get(symbol)
    if price is None:
        try:
            book = CLIENT.book_ticker(symbol)
            price = (book["bid"] + book["ask"]) / 2.0
        except BinanceError:
            return
        books[symbol] = price
    if not position.get("activation_price"):
        # مراكز مهاجرة من ذاكرة قديمة: بناء مستويات ATR حية
        try:
            frame = fetch_frame_cached(symbol, "1m", force=True)
            if frame and frame.get("atr", 0.0) > 0:
                atr_now = float(frame["atr"])
                position["atr_1m"] = atr_now
                position["activation_price"] = float(position.get("entry", 0)) + TRAIL_ACTIVATION_ATR_MULT * atr_now
                position["trailing_distance"] = TRAIL_DISTANCE_ATR_MULT * atr_now
        except Exception as exc:
            log(f"تعذر تحديث ATR للمركز {pid}: {exc}")
    # ═══ V4.0: قفل الأرباح عند +BREAKEVEN_TRIGGER_PCT ═══
    entry_px = float(position.get("entry", 0) or 0)
    if entry_px > 0 and not position.get("be_armed") and price >= entry_px * (1 + BREAKEVEN_TRIGGER_PCT / 100.0):
        if arm_breakeven(pid, position, price):
            return
    # ═══ V4.0: الخروج الزمني الذكي — راكدة بلا ربح ⇒ رأس المال يعود للعمل ═══
    age_sec = time.time() - float(position.get("opened_at", time.time()))
    gain_pct = ((price - entry_px) / entry_px * 100.0) if entry_px > 0 else 0.0
    if time_stop_due(age_sec, gain_pct, position.get("be_armed", False),
                     position.get("trailing_active", False)):
        budget_take(2, force=True)
        exit_order = emergency_sell(symbol, D(position.get("qty", "0")), "خروج زمني ذكي")
        if exit_order:
            finalize_position(pid, position, exit_order, "خروج زمني ذكي (راكدة بلا ربح)")
            return
    activation = position.get("activation_price")
    if activation is not None and price >= float(activation):
        activate_trailing(pid, position, price)


def manage_positions():
    """إدارة كل المراكز المستقلة: مصالحة المعلق → بيع Dust → مراقبة OCO."""
    if not live_execution_allowed():
        return
    if not MANAGE_LOCK.acquire(blocking=False):
        return
    try:
        books = {}
        try:
            reconcile_pending_entries()
        except Exception as exc:
            log(f"خطأ مصالحة المعلق: {exc}")
        try:
            sell_dust(books)
        except Exception as exc:
            log(f"خطأ بيع Dust: {exc}")
        positions = list(STATE.get("positions", {}).items())
        if not positions:
            return
        open_ids = None
        try:
            open_orders = CLIENT.open_orders_all()
            open_ids = {(o.get("symbol"), o.get("orderId")) for o in open_orders if o.get("orderId")}
        except BinanceError as exc:
            log(f"تعذر جلب الأوامر المفتوحة: {exc}")
        for pid, position in positions:
            try:
                monitor_position(pid, position, open_ids, books)
            except Exception as exc:
                log(f"خطأ إدارة {pid}: {exc}")
    finally:
        MANAGE_LOCK.release()


def cancel_all_orders():
    """يلغي حمايات البوت المسجلة فقط (كل مركز مستقل بمعرّفه)."""
    for pid, position in list(STATE.get("positions", {}).items()):
        symbol = position.get("symbol")
        if not symbol:
            continue
        try:
            if position.get("order_list_id"):
                CLIENT.cancel_oco(symbol, position["order_list_id"])
            else:
                for order_id in set(x for x in position.get("order_ids", []) if x is not None):
                    CLIENT.cancel_order(symbol, order_id)
        except BinanceError as exc:
            log(f"تعذر إلغاء حماية {pid}: {exc}")


def panic_close_all():
    cancel_all_orders()
    for pid, position in list(STATE.get("positions", {}).items()):
        order = emergency_sell(position.get("symbol", ""), D(position.get("qty", 0)), "PANIC")
        if order:
            finalize_position(pid, position, order, "PANIC")


# ══════════════════════════════════════════════════════════════════════════════
# 8) التنسيق: رسائل الدخول/الإغلاق وتقرير /status بالصيغة المطلوبة
# ══════════════════════════════════════════════════════════════════════════════


def regime_text():
    return {"demo": "DEMO", "testnet": "TESTNET", "live": "LIVE"}.get(BINANCE_ENV, BINANCE_ENV.upper())


def status_text():
    """تقرير الحالة — الصيغة العربية المطلوبة حرفياً."""
    m = STATE.get("metrics", {})
    total = int(m.get("trades", 0))
    wins = int(m.get("wins", 0))
    losses = int(m.get("losses", 0))
    consecutive = int(m.get("consecutive_losses", 0))
    pnl = float(m.get("realized_pnl", 0.0))
    decided = wins + losses
    win_rate = (wins * 100.0 / decided) if decided > 0 else 0.0
    active = []
    for position in STATE.get("positions", {}).values():
        name = coin_name(position.get("symbol", ""))
        if name and name not in active:
            active.append(name)
    active_text = " , ".join(active) if active else "لا يوجد"
    net_after = float(STATE.get("net_fees", 0.0) or 0.0)
    gov_now = sum(1 for s, k in (STATE.get("gov_streak") or {}).items()
                  if int(k) >= GOV_MAX_LOSSES
                  and time.time() - float(STATE.get("cooldowns", {}).get(s, 0.0)) < GOV_SYMBOL_COOLDOWN)
    return (
        f"إجمالي الصفقات : {total}\n\n"
        f"🟢الناجحة : {wins}\n\n"
        f"🔴الخاسرة : {losses}\n\n"
        f"الخسائر المتتالية : {consecutive}\n\n"
        f"اجمالي المكاسب : {pnl:.2f}$\n\n"
        f"نسبة النجاح : {win_rate:.2f}%\n\n"
        f"العملات النشطة : {active_text}\n\n"
        f"الصافي بعد العمولة : {net_after:+.4f}$\n\n"
        f"⚖️ عملات تحت عقوبة الحاكم : {gov_now} (بقية السوق يتداول)"
    )


def entry_message(signal, position=None):
    symbol = signal["symbol"]
    book = signal["book"]
    mss = signal["mss"]
    fvg = signal["fvg"]
    position = position or {}
    entry = position.get("entry", signal["price"])
    lines = [
        "🚀 <b>HMSM Zero-Wait — LIMIT BUY فوري</b>",
        f"🔹 {coin_name(symbol)} | {regime_text()} | المركز: <code>{position.get('pid', '—')}</code>",
        f"السعر: <code>{fmt_price(symbol, entry)}</code> | الكمية: <code>{position.get('qty', '—')}</code> | القيمة: <b>10$</b>",
        "",
        "⚡ <b>الأعمدة الثلاثة لحظة التنفيذ:</b>",
        f"• MSS: كسر قمة <code>{fmt_price(symbol, mss['prior_high'])}</code> بإزاحة <b>{mss['displacement']:.2f}×ATR</b>",
        f"• FVG: <code>{fmt_price(symbol, fvg['low'])}</code> — <code>{fmt_price(symbol, fvg['high'])}</code> (غير معبأة)",
        f"• Order Flow: طلب <b>{book['imbalance'] * 100:.1f}%</b> | سبريد {book['spread_pct']:.3f}%" + (" (دفتر Testnet اصطناعي)" if book.get("synthetic") else ""),
        f"• ATR(1m): <b>{signal['atr']:.8g}</b> ({signal['atr_pct']:.3f}%) | حجم {signal['volume_ratio']:.2f}x",
        "",
        f"🛑 وقف ATR: <code>{fmt_price(symbol, position.get('stop', signal['stop']))}</code> ({STOP_ATR_MULT}×ATR)",
        f"🎯 هدف ATR: <code>{fmt_price(symbol, position.get('target', signal['target']))}</code> ({TP_ATR_MULT}×ATR)",
        f"🛤 تفعيل Trailing عند <code>{fmt_price(symbol, position.get('activation_price', signal['activation_price']))}</code> بمسافة {TRAIL_DISTANCE_ATR_MULT}×ATR",
    ]
    if position:
        lines.append(f"حماية Binance: OCO ✅ ({position.get('protection_type')}) — إدارة مستقلة لهذا المركز")
    lines.append("\n⚠️ Spot فقط — بدون رافعة.")
    return "\n".join(lines)


def close_message(symbol, position, pnl, entry, exit_price, reason):
    icon = "✅" if pnl >= 0 else "❌"
    return (
        f"{icon} <b>إغلاق مركز {coin_name(symbol)}</b>\n"
        f"المركز: <code>{position.get('pid', '—')}</code> | السبب: {esc(reason)}\n"
        f"الدخول: <code>{fmt_price(symbol, entry)}</code> | الخروج: <code>{fmt_price(symbol, exit_price)}</code>\n"
        f"النتيجة: <b>{pnl:+.4f}$</b>"
    )


HELP_TEXT = (
    "🤖 <b>NOVA ZERO-WAIT v4.0.2 STRICT</b>\n\n"
    "/status تقرير الأداء\n/scan فحص فوري\n/coin SOL تحليل عملة\n"
    "📋 <b>سجل الصفقات</b> — كل صفقة مفصلة بالصافي بعد العمولة\n"
    "/log سجل الصفقات من هنا\n/stats الإحصاء الصادق + الحاكم\n"
    "/pause إيقاف الدخولات الجديدة\n/resume استئناف\n"
    "/cancelall إلغاء حمايات البوت (ستُصفّى المراكز تلقائياً)\n"
    "/panic إلغاء + تصفية فورية\n/prices أفضل الأزواج\n"
    "/kill قاطع تداول يدوي\n/unkill إزالة القاطع\n\n"
    "⚡ السرعة: MSS + FVG + Flow في اللحظة نفسها → LIMIT BUY فوري 10$ (كما هي).\n"
    "🛡 <b>القوانين الصارمة (جديدة):</b>\n"
    f"• وقف بأرضية {SL_MIN_PCT:g}% وسقف {SL_MAX_PCT:g}% — لا اختناق ولا حرق\n"
    f"• قفل أرباح: +{BREAKEVEN_TRIGGER_PCT:g}% ⇒ الوقف يقفز +{BREAKEVEN_LOCK_PCT:g}% (ربح مضمون)\n"
    f"• خروج زمني ذكي: راكدة بلا ربح بعد {TIME_STOP_SEC}ث ⇒ خروج نظيف\n"
    f"• حاكم العملة: {GOV_MAX_LOSSES} خسائر متتالية ⇒ تجاوزها {GOV_SYMBOL_COOLDOWN // 60}د — بلا إيقاف عام\n"
    f"• لا عملات نائمة (حركة < {MIN_ATR_MOVE_PCT}%) ولا سوق نائم (فوليوم < {MIN_VOLUME_RATIO:g}x)\n"
    f"• لا هدف يقل عن {MIN_TARGET_PCT:g}% (العمولة أولاً)\n"
    "• كل رسالة وتقرير يعرض الصافي بعد العمولة المحسوبة — صفر خداع."
)


# ══════════════════════════════════════════════════════════════════════════════
# 9) Telegram
# ══════════════════════════════════════════════════════════════════════════════


def tg_call(method, payload=None, retries=3):
    if not TELEGRAM_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    for attempt in range(retries):
        try:
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


def button(text, data):
    return {"text": text, "callback_data": data}


def main_keyboard():
    return [
        [button("📡 الحالة", "status"), button("⚡ فحص فوري", "scan")],
        [button("📋 سجل الصفقات", "log:0"), button("📊 إحصاء صادق", "stats")],
        [button("⏸ إيقاف", "pause"), button("▶ استئناف", "resume")],
        [button("🧯 إلغاء الأوامر", "cancelall"), button("🆘 تصفية", "panic")],
        [button("❓ المساعدة", "help")],
    ]


def prices_report():
    rows = []
    for symbol in SYMBOLS[:15]:
        row = TICKER_CACHE.get(symbol)
        if not row:
            continue
        icon = "🟢" if row["change"] >= 0 else "🔴"
        rows.append(f"{icon} {coin_name(symbol)}: <code>{fmt_price(symbol, row['price'])}</code> {pct(row['change'])} | {row['quote_volume'] / 1_000_000:.1f}M$")
    if not rows:
        return "لا توجد بيانات أسعار بعد."
    return "💲 <b>أفضل الأزواج (حجم 24س)</b>\n" + "\n".join(rows)


def coin_report(symbol):
    try:
        frame = fetch_frame_cached(symbol, "1m", force=True)
        if not frame:
            return f"⚠️ بيانات {coin_name(symbol)} غير كافية."
        mss = detect_mss(frame)
        fvg = detect_fvg(frame)
        book = book_stats(symbol)
        if mss:
            mss_text = "✅ كسر " + fmt_price(symbol, mss["prior_high"]) + " بإزاحة " + "{:.2f}×ATR".format(mss["displacement"])
        else:
            mss_text = "— غير متحقق"
        if fvg:
            fvg_text = "✅ " + fmt_price(symbol, fvg["low"]) + " — " + fmt_price(symbol, fvg["high"])
        else:
            fvg_text = "— غير متحققة"
        flow_text = "طلب <b>" + "{:.1f}%</b>".format(book["imbalance"] * 100.0)
        if book.get("synthetic"):
            flow_text += " (دفتر Testnet اصطناعي)"
        lines = [
            f"⚡ <b>{coin_name(symbol)} — HMSM 1m</b>",
            f"السعر: <code>{fmt_price(symbol, book['ask'])}</code> | سبريد {book['spread_pct']:.3f}%",
            f"ATR(1m): <b>{frame['atr']:.8g}</b> ({frame['atr_pct']:.3f}%) | حجم الشمعة {frame['volume_ratio']:.2f}x",
            "MSS: " + mss_text,
            "FVG: " + fvg_text,
            "Order Flow: " + flow_text,
            "الإشارة الآن: " + ("🟢 MSS + FVG + Flow متحققة" if (mss and fvg) else "غير متحققة"),
            f"المراكز المفتوحة: {count_symbol_positions(symbol)}/{MAX_POSITIONS_PER_SYMBOL}",
        ]
        return "\n".join(lines)
    except Exception as exc:
        log(f"coin_report {symbol}: {exc}")
        return "⚠️ فشل التحليل."


def normalize_symbol(value):
    raw = value.strip().upper().replace("/", "")
    symbol = raw if raw.endswith("USDT") else raw + "USDT"
    return symbol if symbol in SYMBOL_RULES else None


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
        send_message("⚡ بدأ فحص HMSM الفوري.", main_keyboard(), chat)
        threading.Thread(target=run_scan, args=(True,), daemon=True).start()
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
        send_message("🧯 جارٍ إلغاء حمايات البوت.", main_keyboard(), chat)
    elif data == "panic":
        STATE["paused"] = True
        save_state()
        threading.Thread(target=panic_close_all, daemon=True).start()
        send_message("🆘 بدأت التصفية الشاملة، وأُوقفت الدخولات الجديدة. استخدم /resume لاستئنافها.", main_keyboard(), chat)
    elif data == "help":
        send_message(HELP_TEXT, main_keyboard(), chat)
    elif data == "stats":
        send_message(build_stats_text(), main_keyboard(), chat)
    elif data.startswith("log:"):
        arg = data.split(":", 1)[1]
        page = 0 if arg == "refresh" else int(arg)
        text_log, total = build_log_page(page)
        send_message(text_log, log_keyboard(page, total), chat)


def handle_command(text, chat):
    command, _, argument = text.partition(" ")
    command = command.split("@", 1)[0].lower()
    if command in ("/start", "/menu"):
        send_message("🎛️ <b>NOVA ZERO-WAIT v4.0.2 STRICT</b>\nاختر عملية:", main_keyboard(), chat)
    elif command == "/help":
        send_message(HELP_TEXT, main_keyboard(), chat)
    elif command == "/status":
        send_message(status_text(), main_keyboard(), chat)
    elif command == "/scan":
        send_message("⚡ بدأ فحص HMSM الفوري.", main_keyboard(), chat)
        threading.Thread(target=run_scan, args=(True,), daemon=True).start()
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
        send_message("🧯 جارٍ إلغاء حمايات البوت.", main_keyboard(), chat)
    elif command == "/panic":
        STATE["paused"] = True
        save_state()
        threading.Thread(target=panic_close_all, daemon=True).start()
        send_message("🆘 بدأت التصفية الشاملة، وأُوقفت الدخولات الجديدة. استخدم /resume لاستئنافها.", main_keyboard(), chat)
    elif command == "/coin":
        symbol = normalize_symbol(argument)
        if not symbol:
            send_message("اكتب مثلاً: /coin SOL", chat_id=chat)
            return
        threading.Thread(target=lambda: send_message(coin_report(symbol), main_keyboard(), chat), daemon=True).start()
    elif command == "/log":
        text_log, total = build_log_page(0)
        send_message(text_log, log_keyboard(0, total), chat)
    elif command == "/stats":
        send_message(build_stats_text(), main_keyboard(), chat)
    elif command == "/prices":
        send_message(prices_report(), main_keyboard(), chat)
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
    updates = tg_call("getUpdates", {"offset": STATE.get("offset", 0), "timeout": 20, "allowed_updates": ["message", "callback_query"]}, retries=1)
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
# 10) دورة الفحص Zero-Wait
# ══════════════════════════════════════════════════════════════════════════════


def process_signal(signal):
    symbol = signal["symbol"]
    if not reserve_entry(symbol):
        return False
    try:
        with ENTRY_SEMAPHORE:
            return execute_entry(signal)
    finally:
        release_entry(symbol)


def run_scan(force=False):
    """يفحص الكون كاملاً بأقصى سرعة: لا sleep ولا انتظار ولا تخزين إعدادات."""
    if not SCAN_LOCK.acquire(blocking=False):
        return None
    try:
        now = time.time()
        if now < RATE_BACKOFF_UNTIL:
            return None
        if LAST_USED_WEIGHT >= SAFE_WEIGHT_LIMIT:
            log(f"تهدئة ذاتية: الوزن {LAST_USED_WEIGHT} ≥ {SAFE_WEIGHT_LIMIT}")
            return None
        if not SYMBOL_RULES:
            log("لا توجد قواعد Binance محمّلة؛ لا يمكن الفحص")
            return None
        refresh_universe(force=False)
        cooldowns = STATE.get("cooldowns", {})
        position_counts = {}
        for position in STATE.get("positions", {}).values():
            s = position.get("symbol")
            if s:
                position_counts[s] = position_counts.get(s, 0) + 1
        with ENTRY_LOCK:
            reserved = dict(ENTRY_RESERVATIONS)
        symbols = []
        for symbol in SYMBOLS:
            if position_counts.get(symbol, 0) + reserved.get(symbol, 0) >= MAX_POSITIONS_PER_SYMBOL:
                continue
            if now - cooldowns.get(symbol, 0.0) < SYMBOL_COOLDOWN:
                continue
            symbols.append(symbol)
        signals = []
        if symbols:
            with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
                futures = [pool.submit(scan_one_symbol, s) for s in symbols]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        signals.append(result)
        # الأقوى تدفقاً أولاً
        signals.sort(key=lambda item: item["book"].get("imbalance", 0.5), reverse=True)
        if signals and not STATE.get("paused"):
            for signal in signals:
                threading.Thread(target=process_signal, args=(signal,), daemon=True).start()
        log(f"فحص HMSM: {len(symbols)} زوجاً | إشارات فورية: {len(signals)} | وزن API: {LAST_USED_WEIGHT}")
        if force:
            if signals:
                preview = "، ".join(f"{coin_name(x['symbol'])} (تدفق {x['book']['imbalance'] * 100:.0f}%)" for x in signals[:10])
                send_message(f"⚡ <b>فحص HMSM فوري</b>\nإشارات: {len(signals)}\n{esc(preview)}")
            else:
                send_message("⚡ <b>فحص HMSM فوري</b>\nلا توجد مواءمة MSS + FVG + Flow في هذه اللحظة.")
        return signals
    except Exception as exc:
        log(f"خطأ فحص عام: {exc}\n{traceback.format_exc()[-500:]}")
        return None
    finally:
        SCAN_LOCK.release()


# ══════════════════════════════════════════════════════════════════════════════
# 11) الاختبار الذاتي والتشغيل
# ══════════════════════════════════════════════════════════════════════════════


def _selftest_frame():
    """شموع تركيبية: شمعة إزاحة تكسر القمة وتصنع FVG غير معبأة."""
    n = 100
    o, h, l, c, v, t = [], [], [], [], [], []
    now_ms = int(time.time() * 1000)
    for i in range(n):
        t.append(now_ms - (n - i) * 60_000)
        v.append(1000.0 + (i % 7))
        if i <= 96:
            o.append(100.0); c.append(100.0); h.append(100.5); l.append(99.5)
        elif i == 97:
            o.append(100.2); c.append(109.0); h.append(109.2); l.append(100.1)
        else:  # i == 99 هي الشمعة الحية وتُهمل؛ i == 98 آخر شمعة مغلقة
            o.append(105.0); c.append(110.0); h.append(110.3); l.append(104.0)
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": v, "live": c[-1]}


def selftest():
    print("NOVA ZERO-WAIT v4.0.2 STRICT SELFTEST")
    results = []

    def check(name, condition):
        results.append(bool(condition))
        print(("✅ " if condition else "❌ ") + name)

    # ATR
    n = 200
    highs = [101.0] * n
    lows = [99.0] * n
    closes = [100.0] * n
    check("ATR", last_valid(atr(highs, lows, closes, ATR_PERIOD)) > 0)

    # فريم تركيبي + جودة
    raw = _selftest_frame()
    frame = analyze_frame(raw, "1m")
    check("تحليل فريم 1m", frame is not None and frame["atr"] > 0)

    # MSS: كسر قمة 109.2 بإغلاق 110 مع إزاحة
    mss = detect_mss(frame) if frame else None
    check("MSS لحظي", mss is not None and mss["prior_high"] == 109.2 and mss["displacement"] > MSS_MIN_RANGE_ATR)

    # FVG: فجوة [100.5, 104.0] غير معبأة
    fvg = detect_fvg(frame) if frame else None
    check("FVG غير معبأة", fvg is not None and fvg["low"] == 100.5 and fvg["high"] == 104.0)

    # سوق عرضي: لا MSS
    flat_raw = {
        "t": [int(time.time() * 1000) - (n - i) * 60_000 for i in range(n)],
        "o": [100.0] * n, "h": [100.5] * n, "l": [99.5] * n, "c": [100.0] * n,
        "v": [1000.0] * n, "live": 100.0,
    }
    flat_frame = analyze_frame(flat_raw, "1m")
    check("لا MSS في سوق عرضي", detect_mss(flat_frame) is None)

    # MSS قديم (age=1) ثم انهيار الهيكل فوراً → رفض الإشارة
    rejected_raw = _selftest_frame()
    rejected_raw["o"][-2] = 106.0
    rejected_raw["c"][-2] = 100.2   # آخر إغلاق مغلقة تحت القمة المكسورة 100.5
    rejected_raw["h"][-2] = 106.5
    rejected_raw["l"][-2] = 99.8
    rejected_frame = analyze_frame(rejected_raw, "1m")
    check("رفض MSS مرفوض هيكلياً", detect_mss(rejected_frame) is None)

    # قواعد رمز الاختبار (للفحوصات التالية)
    SYMBOL_RULES["SELFTESTUSDT"] = {
        "status": "TRADING", "base": "SELFTEST", "quote": "USDT",
        "tick": D("0.01"), "step": D("0.001"), "min_qty": D("0"), "max_qty": D("999999"),
        "market_step": D("0.001"), "market_min_qty": D("0"),
        "min_notional": D("5"), "min_trailing_below": 10, "max_trailing_below": 2000,
    }

    # sellable_qty: دون الحد الأدنى → None
    check(
        "فحص قابلية البيع",
        sellable_qty("SELFTESTUSDT", D("0.01"), 100.0) is None and sellable_qty("SELFTESTUSDT", D("1"), 100.0) is not None,
    )

    # يقين wait_limit_fill: إلغاء مؤكد بلا تعبئة / فشل شبكة → غير مؤكد
    _real_get_order = CLIENT.get_order
    CLIENT.get_order = lambda symbol, order_id: {"status": "CANCELED", "executedQty": "0", "orderId": order_id}
    order_result, certain = wait_limit_fill("SELFTESTUSDT", 1)
    check("يقين الإلغاء بلا تعبئة", order_result is None and certain is True)

    def _network_boom(symbol, order_id):
        raise BinanceError("شبكة Binance: timeout")
    CLIENT.get_order = _network_boom
    order_result, certain = wait_limit_fill("SELFTESTUSDT", 1)
    check("فشل الشبكة → غير مؤكد (للمصالحة)", order_result is None and certain is False)
    CLIENT.get_order = _real_get_order

    # التقريب
    check("Decimal rounding", round_step(D("1.23456"), D("0.001")) == D("1.234") and round_price(D("1.23451"), D("0.001"), "up") == D("1.235"))

    # خطة التتبع الديناميكية: clamp حسب فلتر TRAILING_DELTA
    plan = dynamic_trailing_plan("SELFTESTUSDT", 100.0, 0.5)
    check(
        "Trailing ديناميكي ATR",
        plan is not None and plan["trail_bips"] == 60 and abs(plan["activation_price"] - 100.75) < 1e-9 and abs(plan["trailing_distance"] - 0.6) < 1e-9,
    )

    # Pyramiding: حتى 3 مراكز لكل عملة
    STATE["positions"] = {}
    ok1 = all(reserve_entry("SELFTESTUSDT") for _ in range(3))
    ok2 = not reserve_entry("SELFTESTUSDT")
    for _ in range(3):
        release_entry("SELFTESTUSDT")
    STATE["positions"] = {f"SELFTESTUSDT#{i}": {"symbol": "SELFTESTUSDT"} for i in range(3)}
    ok3 = not reserve_entry("SELFTESTUSDT")
    STATE["positions"] = {}
    check("Pyramiding: 3 مراكز كحد أقصى لكل عملة", ok1 and ok2 and ok3)

    # صيغة تقرير الحالة المطلوبة حرفياً
    STATE["metrics"] = {"trades": 5, "realized_pnl": -1.25, "wins": 2, "losses": 3, "consecutive_losses": 3}
    STATE["positions"] = {
        "BTCUSDT#aaa": {"symbol": "BTCUSDT"},
        "ETHUSDT#bbb": {"symbol": "ETHUSDT"},
        "BTCUSDT#ccc": {"symbol": "BTCUSDT"},
    }
    text = status_text()
    lines = text.split("\n")
    check(
        "صيغة /status العربية",
        "إجمالي الصفقات : 5" in lines
        and "🟢الناجحة : 2" in lines
        and "🔴الخاسرة : 3" in lines
        and "الخسائر المتتالية : 3" in lines
        and "اجمالي المكاسب : -1.25$" in lines
        and "نسبة النجاح : 40.00%" in lines
        and "العملات النشطة : BTC , ETH" in lines
        and "USDT" not in lines[-1],
    )
    STATE["positions"] = {}
    STATE["metrics"] = default_state()["metrics"]

    # ═══ V4.0 STRICT: القوانين الصارمة — دوال نقية بلا شبكة ═══
    print("قسم V4.0: الوقف الصارم / القفل / الزمني / الحاكم / الميزانية / السجل")
    globals()["STATE"] = default_state()   # تصفير عالمي (تجنب التحويل لمتغير محلي)

    # 1) الوقف بأرضية وسقف + هدف أكبر من العمولة
    st = strict_stop_target(100.0, 0.05)          # ATR صغير ⇒ الوقف يلتصق بالأرضية 0.30%
    check("V4: أرضية الوقف 0.30% تمنع الاختناق (ATR ضئيل)",
          st is not None and abs(st["stop"] - 99.7) < 1e-9
          and abs(st["target"] - (100 + 2.2 * 0.30)) < 1e-9)
    st2 = strict_stop_target(100.0, 4.0)          # 1.15×ATR=4.6 ⇒ يقص عند سقف 3%
    check("V4: سقف الوقف 3% يمنع الحرق", abs(st2["stop"] - 97.0) < 1e-9
          and abs(st2["dist"] - 3.0) < 1e-9)
    check("V4: هدف ATR عادي مرتفع فوق العمولة",
          strict_stop_target(100.0, 0.3) is not None)
    # هدف لا يغطي العمولة ⇒ رفض قبل الشراء (نحاكي ATR أصغر من أن يعطي 0.35%)
    saved_min = MIN_TARGET_PCT
    globals()["MIN_TARGET_PCT"] = 1.0             # الأرضية تعطي هدفاً 0.66% < العتبة
    check("V4: هدف دون عتبة العمولة ⇒ إشارة مرفوضة (قبل الشراء)",
          strict_stop_target(100.0, 0.05) is None)
    # بعد تعبئة الأمر: قصّ فقط — المركز لنا ولا يتيمة أبداً
    st_fill = strict_stop_target(100.0, 0.05, reject_below_fee=False)
    check("V4: بعد تعبئة الأمر ⇒ وقف مقصوص بالأرضية ولا رفض (لا يتيمة)",
          st_fill is not None and abs(st_fill["stop"] - 99.7) < 1e-9)
    globals()["MIN_TARGET_PCT"] = saved_min

    # 2) قفل الأرباح فوق الدخول بالضبط
    check("V4: قفل الأرباح = دخول +0.45% (فوق عمولة الجولة ⇒ صافي موجب)",
          abs(be_lock_price(100.0) - 100.45) < 1e-9)

    # 3) الخروج الزمني الذكي: قواعده الأربع
    check("V4: زمني — 61ث وربح 0.05% ⇒ خروج",
          time_stop_due(61, 0.05, False, False))
    check("V4: زمني — صفقة محمية بالقفل لا تُمس",
          not time_stop_due(999, 0.3, True, False)
          and not time_stop_due(999, 0.3, False, True))
    check("V4: زمني — قبل الموعد لا خروج",
          not time_stop_due(30, 0.0, False, False))
    check("V4: زمني — 61ث وربح 0.2% (فوق الحد الأدنى) ⇒ اصبر",
          not time_stop_due(61, 0.2, False, False))

    # 4) العمولة المحسوبة
    check("V4: عمولة 0.20% على الجولة (10$ دخول + 10$ خروج) = 0.04$",
          abs(fee_sim(10.0, 10.0) - 0.04) < 1e-9)

    # 5) الحاكم: عقوبة على العملة الخاسرة فقط — بلا إيقاف عام
    STATE["gov_streak"] = {"AAAUSDT": 3, "BBBUSDT": 1}
    STATE["cooldowns"] = {"AAAUSDT": time.time()}
    block_a, why_a = gov_should_pause("AAAUSDT")
    block_b, _ = gov_should_pause("BBBUSDT")
    block_c, _ = gov_should_pause("CCCUSDT")
    check("V4: 3 خسائر متتالية ⇒ تجاوز العملة فقط (الباقي حر)",
          block_a and "خسائر" in why_a and not block_b and not block_c)
    STATE["cooldowns"]["AAAUSDT"] = time.time() - (GOV_SYMBOL_COOLDOWN + 1)
    block_expired, _ = gov_should_pause("AAAUSDT")
    check("V4: العقوبة تنتهي تلقائياً بعد 10 دقائق", not block_expired)
    STATE["gov_streak"] = {"AAAUSDT": 2}
    check("V4: خسارتان فقط ⇒ لا عقوبة بعد", not gov_should_pause("AAAUSDT")[0])

    # 6) ميزانية الأوامر: تمتلئ ⇒ ترفض الدخول، والإجبار (الخروج) يعمل دائماً
    STATE["order_ts"] = [time.time()] * ORDER_BUDGET_MAX
    check("V4: ميزانية ممتلئة ⇒ دخول مرفوض", not budget_take(3))
    check("V4: الحماية (force) تعبر دائماً", budget_take(2, force=True))
    STATE["order_ts"] = []

    # 7) السجل المفصل: قيد + عمولة + صفحات + تنقل
    STATE["log_book"] = []
    net1 = log_book_add("AAAUSDT", "AAAUSDT#1", 100.0, 100.4, 0.1, 0.04, "ترقب حصد")
    check("V4: قيد السجل يخصم العمولة من الخام (0.04 − 0.08 = −0.04)",
          abs(net1 - (0.04 - fee_sim(10.0, 10.04))) < 1e-9
          and abs(STATE["log_book"][0]["net"] - net1) < 1e-9)
    for i in range(25):
        log_book_add("BBBUSDT", f"BBBUSDT#{i}", 10.0, 10.1, 1.0, 0.1 * i - 1.0, "اختبار صفحات")
    page0, total = build_log_page(0)
    page_last, _ = build_log_page(total - 1)
    check(f"V4: السجل يتقاسم صفحات ({total} صفحة لـ26 قيداً) والأحدث أولاً",
          total >= 4 and "صفحة 1/" in page0 and "BBB" in page0
          and "AAA" in page_last)
    check("V4: صفحة خارج النطاق تُقحم بأمان", build_log_page(999)[0] is not None)
    kb = log_keyboard(0, total)
    check("V4: أزرار التنقل: تالٍ موجود وماضٍ غائب في الأولى",
          any(b.get("callback_data") == "log:1" for row in kb for b in row)
          and not any(b.get("callback_data") == "log:-1" for row in kb for b in row))

    # 8) الإحصاء الصادق + بطاقة اليوم
    STATE["metrics"]["trades"] = 26
    txt_stats = build_stats_text()
    check("V4: الإحصاء يعرض الصافي بعد العمولة + الحاكم + الفلاتر",
          "بعد العمولة" in txt_stats and "حاكم العملات" in txt_stats
          and "الفلاتر" in txt_stats)
    check("V4: بطاقة اليوم ترصد الصفقات (26)",
          (STATE.get("daily") or {}).get("trades") == 26)

    # 9) الحالة تحفظ الأجهزة الجديدة (توافق خلفي)
    fresh = default_state()
    check("V4: الحالة الافتراضية تحمل كل أجهزة V4.0",
          "gov_streak" in fresh and "log_book" in fresh and "filters" in fresh
          and "net_fees" in fresh and "order_ts" in fresh and "daily" in fresh)

    print("النتيجة: " + ("ALL PASS ✅" if all(results) else "FAIL ❌"))
    return 0 if all(results) else 1


def startup_checks():
    if BINANCE_ENV == "live" and LIVE_CONFIRM != "I_UNDERSTAND_SPOT_RISK":
        raise SystemExit("Live يتطلب LIVE_TRADING_CONFIRM=I_UNDERSTAND_SPOT_RISK")
    CLIENT.sync_time()
    load_symbol_rules(CLIENT.exchange_info())
    refresh_universe(force=True)
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
    acquire_single_instance()
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
    execution_line = "مفعّل" if live_execution_allowed() else "غير مفعّل"
    if STATE.get("paused"):
        execution_line += " | ⏸ الإيقاف المؤقت مفعّل (الدخولات موقوفة — /resume)"
    send_message(
        "🚀 <b>NOVA HMSM SCALPER v3</b>\n"
        f"البيئة: {regime_text()} | Spot فقط | Zero-Wait\n"
        f"أفضل {TOP_N_SYMBOLS} زوجاً حسب حجم 24س | MSS + FVG + Order Flow → LIMIT فوري\n"
        f"حجم الصفقة: 10$ | حتى {MAX_POSITIONS_PER_SYMBOL} مراكز متزامنة لكل عملة | Trailing ديناميكي بـ ATR\n"
        f"التنفيذ: {execution_line} | لا قواطع خسائر متتالية\n"
        "/menu لفتح لوحة التحكم.",
        main_keyboard(),
    )
    threading.Thread(target=telegram_loop, daemon=True, name="telegram-loop").start()
    last_scan = 0.0
    last_manage = 0.0
    last_startup_retry = 0.0
    while True:
        try:
            now = time.time()
            try:
                maybe_daily_report()
            except Exception:
                pass
            if not startup_ready and now - last_startup_retry >= 30:
                last_startup_retry = now
                try:
                    startup_checks()
                    startup_ready = True
                    send_message("✅ عاد اتصال Binance؛ الرادار جاهز بأقصى سرعة.")
                except BinanceError as exc:
                    log(f"إعادة اتصال Binance لم تنجح: {exc}")
            if startup_ready and now - last_scan >= SCAN_EVERY:
                last_scan = now
                threading.Thread(target=run_scan, daemon=True).start()
            if startup_ready and now - last_manage >= MANAGE_EVERY:
                last_manage = now
                threading.Thread(target=manage_positions, daemon=True).start()
            if now - STATE.get("last_heartbeat", 0.0) >= 12 * 3600:
                STATE["last_heartbeat"] = now
                save_state()
                send_message(status_text(), main_keyboard())
            time.sleep(0.5)
        except KeyboardInterrupt:
            save_state()
            send_message("👋 تم إيقاف البوت؛ الذاكرة محفوظة.")
            return
        except Exception as exc:
            log(f"خطأ الحلقة: {exc}\n{traceback.format_exc()[-500:]}")
            time.sleep(3)


if __name__ == "__main__":
    main()
