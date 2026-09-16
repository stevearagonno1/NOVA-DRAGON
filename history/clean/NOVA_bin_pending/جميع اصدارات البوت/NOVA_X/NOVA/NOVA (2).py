#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA V6.2 AI-HFT — Hybrid + Shadow Lab + Maker Entries
==============================================================================
بوت سكالبينج Spot غير متزامن بالكامل على Binance. V6.1 تطوّر جوهري عن V6.0:
من «قنّاص واحد نادر» إلى «هجين بشخصيتين» يوفّق بين العدد الهائل والاقتناع:

V6.1 — ما الجديد:
1) محرك الرشاش (SPRAY): ثلاثة زنادات OR دائمة بلا انتظار الكوارث —
   • اندفاعة صاعدة (impulse): صعود ≥ عتبة تكيفية داخل نافذة 15ث مع هيمنة مشترين.
   • هيمنة تدفق (flow): نسبة شراء/بيع aggTrade مرتفعة + سعر قرب قمة النافذة.
   • اختراق تقلب (breakout): كسر قمة آخر 20 دقيقة بقوة تدفق مؤكدة.
   العتبات تكيفية لكل عملة: k × وسيط حركة النافذة (15ث) لآخر 30 دقيقة —
   بيتكوين يُقاس بمعياره وميم-كوين بمعياره (لا تجمود في الساعات الهادئة).
2) القنّاص (flash-crash) يبقى كما هو منطقياً لكن بحجم مضخّم (SNIPER_RISK_MULT)
   وسقف مركز أعلى (SNIPER_MAX_NOTIONAL_USD) ووقف زمني متسامح (يتنفّس 3×)،
   وسبريد تكيفي أرحب (الانهيار يتسع طبيعياً — لا نقتل الفرصة في لحظتها).
3) الوعي بالرسوم (Fee-Aware Lab): PnL صافٍ بعد عمولة Taker لكل الجهتين
   (تُقدَّر FEE_TAKER_RATE وتُخصم من كل خروج جزئي/نهائي)، تصنيف win/loss
   على الصافي، وقفل التعادل يصبح +0.25% (رسوم ذهاب/إياب + انزلاق) بترغية
   +0.30% — «صفقة ناجحة صافيها سالب» صارت مستحيلة محاسبياً.
4) البيع الجزئي (Scale-Out): عند +0.40% يُباع نصف المركز (بشرط بقاء الباقي
   قابلاً للبيع فوق minNotional) ويستمر التتبّع على النصف الباقي.
5) خروج بانعكاس التدفق: في الربح، انقلاب aggTrade إلى بيع ضاغط ⇒ MARKET فوراً
   قبل أن يلمس السعر وقف التتبّع (الخروج قبل الكسر لا عنده).
6) الحاكم (Governor): قاطع 3 خسائر متتالية (10 دقائق)، سقف خسارة ساعة
   (−2$ ⇒ 30 دقيقة)، سقف يوم (−5$ ⇒ حتى الغد)، وميزانية أوامر صريحة
   (40/10ث بهامش أمان تحت حد Binance 50) تُفحص قبل الإطلاق لا بعده.
7) تشخيص V6.1: عدّاد لكل زناد (أُطلق/قُتل)، تقرير /context يعرض البيئة
   (TESTNET/LIVE) وصفقات/ساعة ومتوسط الصافي وحالة الحاكم وميزانية الأوامر.

V6.2 — الوضع الظلي + دخول الصانع (الإجابة بالأدلة لا بالظن):
9) SHADOW Lab: كل زناد يفتح صفقة افتراضية موحدة (12$) تُدار بنفس محرك الخروج
   الحقيقي (تعادل/تتبّع/بيع جزئي/وقف زمني/وقف صلب) بلا أي أمر يُرسل، وتُقيد
   أرباحها صافية بعد الرسوم لكل زناد على حدة (/shadow). الزناد الرابح بعد
   50+ صفقة مغلقة يستحق التفعيل الحقيقي؛ SHADOW_ONLY=1 يجعل البوت مختبراً
   صامتاً بالكامل (قياس بلا أي أوامر).
10) MAKER Entries: الدخول LIMIT_MAKER عند أفضل شراء بدل MARKET — يكسب
    السبريد (~0.1%/صفقة) بدل دفعه. مهلة MAKER_TTL_SEC (≤10ث < Watchdog 12ث)
    ثم إلغاء تلقائي إن لم يُنفَّذ (الزخم فات)، ورفض -2010 (كتاب مقفول) يُسقط
    الإشارة بأمان. الحجم/الوقف/الأحداث كما هي تماماً.

المحفوظ من V6.0/V5.3: قنص الانهيار بالذاكرة المتدحرجة O(1)/tick، وقف طوارئ
صلب ATR(1m)×1.5 بسقف 3% على Binance، محرك التتبّع المحلي (تعادل/تتبّع واسع
ثم خناق)، معمارية STATE_LOCK وطابور أحداث User بمستهلك واحد ومطالبة خروج
ذرية ومصالحة لقطية وWatchdog وDust→BNB، Gemini Brain (Auto-Tune + /autopsy
+ /insight) بحدود صلبة أوسع الآن لتلائم اقتصاد الرسوم الجديد.

الإعداد:
    export BINANCE_ENV='testnet'
    export BINANCE_API_KEY='مفتاح Binance Spot'
    export BINANCE_API_SECRET='سر Binance Spot'
    export TELEGRAM_BOT_TOKEN='توكن Telegram'
    export TELEGRAM_CHAT_ID='معرف المحادثة'
    export GEMINI_API_KEY='مفتاح Google AI Studio'

التثبيت (Termux / Python 3.10+):
    pkg update -y
    pkg install python -y
    pip install aiohttp numpy pandas google-generativeai

التشغيل:
    python NOVA.py --selftest
    python NOVA.py --dry-run
    python NOVA.py
    python NOVA.py --once

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
import re
import signal as _signal
import sys
import time
import traceback
import uuid
import warnings
from collections import Counter, deque
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from html import escape
from urllib.parse import urlencode

import numpy as np
import pandas as pd

try:
    import aiohttp
except ImportError:  # يسمح بتشغيل --selftest دون aiohttp
    aiohttp = None

try:
    warnings.filterwarnings("ignore", category=FutureWarning)  # إسكات تنبيه إهمال SDK
    import google.generativeai as genai
except ImportError:  # مزايا الدماغ الذكي تتعطل بأمان دون SDK
    genai = None


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

# ── Gemini AI Brain (V6.0): الدماغ المستقل + المستشار التفاعلي ───────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"
GEMINI_TIMEOUT = clamp(env_float("GEMINI_TIMEOUT", 60.0), 10.0, 300.0)
GEMINI_TUNE_EVERY = max(600, env_int("GEMINI_TUNE_EVERY", 4 * 3600))   # حلقة Auto-Tune: كل 4 ساعات

AUTO_TRADE = env_bool("AUTO_TRADE", True)
DRY_RUN = env_bool("DRY_RUN", False)
# الصمت التام: لا رسائل تلقائية إطلاقاً سوى إشعار البدء وإشعار Auto-Tune المصرّح به
STEALTH_MODE = True

STARTUP_TEXT = "✅ NOVA V6.2 Hybrid AI-HFT Started & Connected to Binance WebSockets."
RESET_REPLY = "✅ تم تصفير جميع الإحصائيات بنجاح."

# ── الكون الديناميكي: أفضل N زوجاً حسب حجم 24 ساعة، تحديث كل ساعة ────────────
TOP_N_SYMBOLS = max(10, min(100, env_int("TOP_N_SYMBOLS", 50)))  # V5.1: من البيئة (start.sh=50)
UNIVERSE_REFRESH_EVERY = max(300, env_int("UNIVERSE_REFRESH_EVERY", 3600))
MIN_24H_QUOTE_VOLUME = env_float("MIN_24H_QUOTE_VOLUME", 1_000_000)

# ── المحرك (V6.0): شموع 1m للذاكرة الحسابية فقط (ATR) — لا فريم إشارة إطلاقاً ──
MICRO_INTERVAL = "1m"          # مصدر ATR(1m) لوقف الطوارئ الصلب (حماية فقط)
INTERVAL_SECONDS = {"1m": 60}
KLINE_REST_LIMITS = {MICRO_INTERVAL: clamp(env_int("KLINE_LIMIT_1M", 90), 30, 500)}
HISTORY_MAX = {MICRO_INTERVAL: 180}

ATR_PERIOD = max(2, env_int("ATR_PERIOD", 14))
VR_BASELINE = max(2, env_int("VR_BASELINE", 20))   # متوسط ATR14 لآخر 20 شمعة

# ── محرك القنص اللحظي (V6.0): Flash-Crash Sniping بلا أي شموع إشارة ──────────
TICK_MEMORY_SEC = clamp(env_float("TICK_MEMORY_SEC", 15.0), 2.0, 120.0)  # ذاكرة aggTrade المتدحرجة
FLASH_DROP_PCT = env_float("FLASH_DROP_PCT", 0.25)      # هبوط ≥ 0.25% داخل نافذة الذاكرة → زناد
BUY_WALL_RATIO = env_float("BUY_WALL_RATIO", 1.5)      # جدار شراء هائل: bid_vol > 1.5× ask_vol
BUY_WALL_MAX_AGE = clamp(env_float("BUY_WALL_MAX_AGE", 2.0), 0.2, 10.0)  # حداثة bookTicker
SNIPER_RETRY_SEC = clamp(env_float("SNIPER_RETRY_SEC", 3.0), 0.5, 30.0)  # خنق محاولات العملة
SNIPER_PENDING_TTL = clamp(env_float("SNIPER_PENDING_TTL", 10.0), 1.0, 60.0)  # صيد ينتظر الجدار

# ── V6.1: محرك الرشاش (3 زنادات OR دائمة بعتبات تكيفية لكل عملة) ─────────────
SPRAY_ENABLED = env_bool("SPRAY_ENABLED", True)
SPRAY_EVAL_EVERY = clamp(env_float("SPRAY_EVAL_EVERY", 1.0), 0.2, 10.0)   # تقييم كل عملة ≤ 1Hz
SPRAY_SAMPLE_EVERY = clamp(env_float("SPRAY_SAMPLE_EVERY", 5.0), 1.0, 30.0)  # عينة خط الأساس
SPRAY_BASELINE_SEC = clamp(env_float("SPRAY_BASELINE_SEC", 1800.0), 300.0, 7200.0)  # ذاكرة 30د
SPRAY_MIN_SAMPLES = max(2, env_int("SPRAY_MIN_SAMPLES", 8))   # أدنى ticks بالنافذة
SPRAY_BASELINE_K = env_float("SPRAY_BASELINE_K", 6.0)         # العتبة = 6 × وسيط حركة 15ث
SPRAY_BASELINE_FLOOR_PCT = env_float("SPRAY_BASELINE_FLOOR_PCT", 0.12)  # أرضية مطلقة
SPRAY_NEAR_TOP_PCT = env_float("SPRAY_NEAR_TOP_PCT", 0.10)    # آخر سعر ضمن 0.10% من القمة
SPRAY_FLOW_RATIO = env_float("SPRAY_FLOW_RATIO", 2.5)         # شراء ≥ 2.5× بيع (زناد التدفق)
SPRAY_FLOW_MOVE_K = env_float("SPRAY_FLOW_MOVE_K", 0.6)       # حركة ≥ 0.6× عتبة الاندفاعة
SPRAY_IMPULSE_FLOW = env_float("SPRAY_IMPULSE_FLOW", 1.8)     # شراء ≥ 1.8× بيع (زناد الاندفاعة)
SPRAY_BREAKOUT_BARS = max(5, env_int("SPRAY_BREAKOUT_BARS", 20))  # كسر قمة آخر 20 دقيقة
SPRAY_BREAKOUT_FLOW = env_float("SPRAY_BREAKOUT_FLOW", 1.2)   # تأكيد تدفق للاختراق
SPRAY_COOLDOWN_SEC = clamp(env_float("SPRAY_COOLDOWN_SEC", 40.0), 5.0, 300.0)  # تهدئة الرشاش/عملة

# ── V6.1: القنّاص بحجم مضخّم + تنفّس زمني (اقتناع أعلى = حجم أعلى) ───────────
SNIPER_RISK_MULT = clamp(env_float("SNIPER_RISK_MULT", 2.5), 1.0, 5.0)   # مخاطرة ×2.5
SNIPER_MAX_NOTIONAL_USD = Decimal(str(env_float("SNIPER_MAX_NOTIONAL_USD", 30.0)))
SNIPER_TIMESTOP_MULT = env_float("SNIPER_TIMESTOP_MULT", 3.0)  # مهلة القنّاص ×3 (لا وقف جائع)

# ── V6.1: الوعي بالرسوم — معمل Testnet يحسب كما في Live ─────────────────────
FEE_TAKER_RATE = clamp(env_float("FEE_TAKER_RATE", 0.001), 0.0, 0.01)    # 0.1% للجهة
SLIPPAGE_COST_PCT = env_float("SLIPPAGE_COST_PCT", 0.05)                 # هامش انزلاق
FEE_ROUND_TRIP_PCT = (FEE_TAKER_RATE * 2.0 * 100.0) + SLIPPAGE_COST_PCT  # ≈ 0.25%

# ── V6.1: سبريد تكيفي (الانهيار يتسع طبيعياً — لا نقتل الفرصة بحاجد جامد) ────
SPREAD_SNIPE_MULT = env_float("SPREAD_SNIPE_MULT", 3.5)   # القنّاص: 3.5× السبريد النمطي
SPREAD_SPRAY_MULT = env_float("SPREAD_SPRAY_MULT", 2.5)   # الرشاش: 2.5× السبريد النمطي
SPREAD_ADAPTIVE_CAP = clamp(env_float("SPREAD_ADAPTIVE_CAP", 0.60), 0.05, 2.0)  # سقف مطلق

# ── V6.1: البيع الجزئي (Scale-Out) + خروج بانعكاس التدفق ────────────────────
SCALE_OUT_ENABLED = env_bool("SCALE_OUT_ENABLED", True)
SCALE_OUT_AT_PCT = env_float("SCALE_OUT_AT_PCT", 0.40)    # عند +0.40% ربح القمة
SCALE_OUT_FRACTION = clamp(env_float("SCALE_OUT_FRACTION", 0.5), 0.1, 0.9)  # نصف المركز
FLOW_REV_EXIT = env_bool("FLOW_REV_EXIT", True)
FLOW_REV_RATIO = env_float("FLOW_REV_RATIO", 2.5)         # بيع ≥ 2.5× شراء في النافذة
FLOW_REV_MIN_USD = env_float("FLOW_REV_MIN_USD", 150.0)   # كتلة البيع الضاغطة (USDT)
FLOW_REV_MIN_GAIN = env_float("FLOW_REV_MIN_GAIN", 0.15)  # لا انعكاس قبل +0.15% ربح
FLOW_REV_COOLDOWN = clamp(env_float("FLOW_REV_COOLDOWN", 3.0), 0.5, 30.0)  # خنق لكل مركز

# ── V6.2: الوضع الظلي — مختبر أفضلية الدخول بلا أي أوامر ────────────────────

def shadow_state():
    """دفتر البحث الظلي داخل STATE (يُحفظ ويُستعاد مع الإقلاع)."""
    sh = STATE.setdefault("shadow", {})
    sh.setdefault("stats", {})
    sh.setdefault("open", {})
    sh.setdefault("history", [])
    sh.setdefault("skipped", 0)
    return sh


def normalize_shadow(raw):
    """V6.2.1 — معقم دفتر الظل: يُنظف البيانات الفاسدة من state.json القديم.

    يُستعمل عند الإقلاع وقابل للاختبار مباشرة — الأعداد صحيحة، الأرباح عائمة،
    والسجل مقصوص بسقف صلب، والمراكز المفتوحة تُمرر كما هي (تُدار بعد الإقلاع).
    """
    sh = raw if isinstance(raw, dict) else {}
    def _si(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _sf(value):
        try:
            out = float(value)
            return out if math.isfinite(out) else 0.0
        except (TypeError, ValueError):
            return 0.0

    stats_in = sh.get("stats") if isinstance(sh.get("stats"), dict) else {}
    stats = {}
    for trig, s in stats_in.items():
        if not isinstance(s, dict):
            continue
        stats[str(trig)] = {
            "opened": _si(s.get("opened", 0)),
            "closed": _si(s.get("closed", 0)),
            "wins": _si(s.get("wins", 0)),
            "losses": _si(s.get("losses", 0)),
            "net": _sf(s.get("net", 0.0)),
            "gross": _sf(s.get("gross", 0.0)),
            "fees": _sf(s.get("fees", 0.0)),
        }
    open_pos = sh.get("open") if isinstance(sh.get("open"), dict) else {}
    history = [row for row in (sh.get("history") or []) if isinstance(row, dict)]
    return {
        "stats": stats,
        "open": open_pos,
        "history": history[-SHADOW_HISTORY_MAX:],
        "skipped": _si(sh.get("skipped", 0)),
    }


def shadow_open(signal):
    """يفتح صفقة افتراضية موحدة (12$) لقياس جودة الزناد — نفس قواعد الحماية الحقيقية."""
    if not SHADOW_ENABLED:
        return
    symbol = str(signal.get("symbol") or "")
    if not symbol:
        return
    SHADOW_SYMS.add(symbol)
    now = time.time()
    if now - float(SHADOW_THROTTLE.get(symbol, 0.0)) < SHADOW_THROTTLE_SEC:
        FUNNEL["shadow-throttle"] += 1
        return
    sh = shadow_state()
    if len(sh["open"]) >= SHADOW_MAX_OPEN:
        sh["skipped"] += 1
        return
    price, _age = market_price(symbol)
    if price <= 0:
        return
    atr_1m = float(signal.get("atr_1m") or 0.0)
    sl_distance = atr_1m * HARD_STOP_ATR_MULT
    sl_distance = min(max(sl_distance, price * SL_MIN_PCT / 100.0),
                      price * SL_MAX_PCT / 100.0)
    if not math.isfinite(sl_distance) or sl_distance <= 0:
        sl_distance = price * 0.005
    qty = float(SHADOW_NOTIONAL_USD) / price
    trigger = str(signal.get("trigger") or "unknown")
    sid = f"SH#{symbol}@{trigger}@{int(now * 1000)}"
    sh["open"][sid] = {
        "symbol": symbol, "trigger": trigger,
        "entry": price, "qty": qty, "initial_qty": qty,
        "stop": price - sl_distance, "peak": price,
        "trail_armed": False, "trail_stop": 0.0, "trail_mode": "off",
        "fees": price * qty * FEE_TAKER_RATE, "partial_pnl": 0.0, "scaled": False,
        "opened_at": now, "setup": str(signal.get("setup_id") or ""),
    }
    SHADOW_THROTTLE[symbol] = now
    sh["stats"].setdefault(trigger, {"opened": 0, "closed": 0, "wins": 0, "losses": 0,
                                     "net": 0.0, "gross": 0.0, "fees": 0.0})["opened"] += 1


def shadow_close(sid, pos, price, reason):
    """يُغلق صفقة ظلية ويقيد الصافي (بعد كل الرسوم) على زنادها في الإحصاء."""
    sh = shadow_state()
    sh["open"].pop(sid, None)
    _sym_closed = str(pos.get("symbol") or "")
    if _sym_closed and not any(
            p.get("symbol") == _sym_closed for p in sh["open"].values()):
        SHADOW_SYMS.discard(_sym_closed)
    entry = float(pos["entry"])
    qty = float(pos["qty"])
    gross = (price - entry) * qty + float(pos.get("partial_pnl", 0.0) or 0.0)
    fees = float(pos.get("fees", 0.0) or 0.0) + price * qty * FEE_TAKER_RATE
    net = gross - fees
    trigger = str(pos.get("trigger") or "unknown")
    st = sh["stats"].setdefault(trigger, {"opened": 0, "closed": 0, "wins": 0, "losses": 0,
                                          "net": 0.0, "gross": 0.0, "fees": 0.0})
    st["closed"] += 1
    st["gross"] += gross
    st["fees"] += fees
    st["net"] += net
    if net >= 0:
        st["wins"] += 1
    else:
        st["losses"] += 1
    sh["history"].append({
        "ts": datetime.now(timezone.utc).isoformat(), "sid": sid, "trigger": trigger,
        "net": round(net, 6), "reason": str(reason),
        "duration": round(time.time() - float(pos.get("opened_at", 0) or 0), 1),
    })
    if len(sh["history"]) > SHADOW_HISTORY_MAX:
        del sh["history"][:-SHADOW_HISTORY_MAX]


def shadow_on_price(symbol, bid_price):
    """إدارة المراكز الظلية بنفس محرك الخروج الحقيقي (تعادل/تتبّع/جزئي/زمني/صلب)."""
    if not SHADOW_ENABLED or symbol not in SHADOW_SYMS:
        return                      # قفزة O(1): لا صفقات ظلية على هذه العملة
    sh = shadow_state()
    open_pos = sh.get("open") or {}
    if not open_pos:
        return
    price = float(bid_price or 0.0)
    if price <= 0 or not math.isfinite(price):
        return
    now = time.time()
    vr = float(btc_ctx_stats().get("vr", 1.0) or 1.0)
    base_stop_sec = get_time_stop_sec()
    for sid in list(open_pos.keys()):
        pos = open_pos.get(sid)
        if not pos or pos.get("symbol") != symbol:
            continue
        entry = float(pos["entry"])
        if entry <= 0:
            continue
        peak = max(float(pos.get("peak", entry) or entry), price)
        pos["peak"] = peak
        plan = trailing_plan(entry, peak, price)      # نفس محرك الخروج الحقيقي حرفياً
        if plan["armed"]:
            pos["trail_armed"] = True
            pos["trail_stop"] = float(plan["stop"])
            pos["trail_mode"] = plan["mode"]
        # بيع جزئي افتراضي بنفس شرط الحقيقي
        if (SCALE_OUT_ENABLED and not pos.get("scaled")
                and (peak - entry) / entry * 100.0 >= SCALE_OUT_AT_PCT
                and float(pos["qty"]) > 0):
            half = float(pos["qty"]) * SCALE_OUT_FRACTION
            pos["partial_pnl"] = float(pos.get("partial_pnl", 0.0)) + (price - entry) * half
            pos["fees"] = float(pos.get("fees", 0.0)) + price * half * FEE_TAKER_RATE
            pos["qty"] = float(pos["qty"]) - half
            pos["scaled"] = True
        stop_hit = price <= float(pos.get("stop", 0.0) or 0.0) or (plan["armed"] and plan["hit"])
        if stop_hit:
            shadow_close(sid, pos, price,
                         "وقف صلب ظلي" if not plan["armed"] else f"تتبّع ظلي ({plan['mode']})")
            continue
        # وقف زمني ظلي — نفس الديناميكية الحقيقية (القنّاص يتنفس، التقلب يمدد/يقصّر)
        trig = str(pos.get("trigger") or "")
        if trig == "flash-crash":
            eff = base_stop_sec * max(1.0, SNIPER_TIMESTOP_MULT)
        elif vr < VR_SLOW:
            eff = base_stop_sec * 1.5
        elif vr > VR_FAST:
            eff = base_stop_sec * 0.75
        else:
            eff = base_stop_sec
        min_profit = 0.0 if trig == "flash-crash" else TIME_STOP_MIN_PROFIT_PCT
        if now - float(pos.get("opened_at", 0) or 0) >= eff:
            gain_pct = (price - entry) / entry * 100.0
            if gain_pct < min_profit:
                shadow_close(sid, pos, price, f"وقف زمني ظلي ({eff:.0f}ث بلا زخم)")


def shadow_report_text():
    """لوحة البحث الظلي: أفضلية كل زناد صافية بعد الرسوم — القرار بالأرقام."""
    sh = shadow_state()
    stats = sh.get("stats") or {}
    opened_total = sum(int(s.get("opened", 0) or 0) for s in stats.values())
    closed_total = sum(int(s.get("closed", 0) or 0) for s in stats.values())
    lines = [
        "🔬 <b>الوضع الظلي — مختبر أفضلية الزناد</b>",
        f"صفقات افتراضية: {opened_total} مفتوحة/مُطلقة | {closed_total} مغلقة | "
        f"متخطاة: {int(sh.get('skipped', 0) or 0)} | حجم موحد {SHADOW_NOTIONAL_USD}$ "
        f"(رسوم {FEE_TAKER_RATE * 100:g}%/جهة محسوبة)",
        "",
    ]
    if not stats:
        lines.append("لا بيانات بعد — كل زناد يفتح صفقة ظلية تلقائياً (خنق 30ث/عملة).")
    else:
        lines.append(f"{'الزناد':<14} مفتوحة مغلقة  فوز%    صافي$      متوسط/صفقة")
        ranked = sorted(stats.items(), key=lambda kv: float(kv[1].get("net", 0) or 0),
                        reverse=True)
        for trig, s in ranked:
            closed = int(s.get("closed", 0) or 0)
            net = float(s.get("net", 0) or 0)
            wr = (int(s.get("wins", 0) or 0) * 100.0 / closed) if closed else 0.0
            avg = (net / closed) if closed else 0.0
            verdict = "✅" if (closed >= 50 and net > 0) else ("⏳" if closed < 50 else "❌")
            lines.append(f"{verdict} {trig:<12} {s.get('opened', 0):>6} {closed:>6} "
                         f"{wr:>6.1f} {net:>+9.4f} {avg:>+10.5f}")
        lines.append("")
        lines.append("القرار: الزناد الرابح صافياً بعد 50+ صفقة مغلقة يُفعَّل حقيقيًا، "
                     "وما دون ذلك يبقى مقيّداً.")
    return "\n".join(lines)


# ── V6.1: الحاكم — الحكيم في متى يتوقف ──────────────────────────────────────
GOV_MAX_STREAK = max(2, env_int("GOV_MAX_STREAK", 3))     # 3 خسائر متتالية
GOV_STREAK_PAUSE_SEC = max(60, env_int("GOV_STREAK_PAUSE_SEC", 600))  # ⇒ توقف 10 دقائق
GOV_HOURLY_LOSS_USD = Decimal(str(env_float("GOV_HOURLY_LOSS_USD", 2.0)))  # −2$/ساعة
GOV_HOURLY_PAUSE_SEC = max(300, env_int("GOV_HOURLY_PAUSE_SEC", 1800))     # ⇒ 30 دقيقة
GOV_DAILY_LOSS_USD = Decimal(str(env_float("GOV_DAILY_LOSS_USD", 5.0)))    # −5$/يوم ⇒ حتى الغد

# ── V6.1: ميزانية الأوامر (حد Binance 50/10ث — نعمل بهامش أمان) ─────────────
ORDER_BUDGET_MAX = max(6, env_int("ORDER_BUDGET_MAX", 40))
ORDER_BUDGET_WINDOW = 10.0
ORDER_BUDGET_ENTRY_COST = max(2, env_int("ORDER_BUDGET_ENTRY_COST", 3))  # شراء+وقف+احتياط خروج

# ── V6.2: الوضع الظلي — إثبات أفضلية الزناد بالأدلة قبل أي مال حقيقي ────────
SHADOW_ENABLED = env_bool("SHADOW_ENABLED", True)
SHADOW_ONLY = env_bool("SHADOW_ONLY", False)    # 1 ⇒ مختبر صامت: قياس بلا أي أوامر حقيقية
SHADOW_NOTIONAL_USD = Decimal(str(env_float("SHADOW_NOTIONAL_USD", 12.0)))  # حجم موحد للمقارنة
SHADOW_THROTTLE_SEC = clamp(env_float("SHADOW_THROTTLE_SEC", 30.0), 5.0, 600.0)
SHADOW_MAX_OPEN = max(10, env_int("SHADOW_MAX_OPEN", 200))
SHADOW_HISTORY_MAX = max(50, env_int("SHADOW_HISTORY_MAX", 400))

# ── V6.2: دخول الصانع (LIMIT_MAKER) — اربح السبريد بدل دفعه ─────────────────
MAKER_ENTRIES = env_bool("MAKER_ENTRIES", True)
MAKER_TTL_SEC = clamp(env_float("MAKER_TTL_SEC", 8.0), 2.0, 10.0)  # < Watchdog (12ث) دائماً

# ── إيقاظ الحيتان (V6.0): تلميح تشخيصي فقط يظهر في /insight (لا تأثير على الدخول) ──
WHALE_TRADE_USD = env_float("WHALE_TRADE_USD", 25_000.0)
WHALE_MEMORY_SEC = max(30.0, env_float("WHALE_MEMORY_SEC", 60.0))
WHALES_MAX = max(50, env_int("WHALES_MAX", 300))

# ── التدفق الحقيقي (aggTrade) بدل اختلال الدفتر على Testnet ─────────────────
FLOW_WINDOW_SEC = max(2.0, env_float("FLOW_WINDOW_SEC", 15.0))
FLOW_MAX_BUCKETS = 96
MAX_SPREAD_PCT = env_float("MAX_SPREAD_PCT", 0.15)
# قدم البيانات: آخر tick أقدم من هذه النافذة → إلغاء الإشارة (بديل الطلقة المعلقة)
MAX_STALE_SEC = clamp(env_float("MAX_STALE_SEC", 3.0), 0.5, 30.0)

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
# V6.1: التعادل واعٍ بالرسوم — لا قفل تحت تكلفة التداول (0.20% عمولات + 0.05% انزلاق)
BREAKEVEN_TRIGGER_PCT = env_float("BREAKEVEN_TRIGGER_PCT", 0.30)  # ربح يفعّل التعادل (Gemini-aware)
BREAKEVEN_LOCK_PCT = env_float("BREAKEVEN_LOCK_PCT", 0.25)     # الوقف يُقفل فوق تكلفة العمولات
TRAIL_WIDE_PCT = env_float("TRAIL_WIDE_PCT", 0.20)             # ربح 0.4–1.0% → تتبّع 0.20%
TRAIL_TIGHT_PCT = env_float("TRAIL_TIGHT_PCT", 0.08)           # ربح > 1.0% → خنق 0.08%
TRAIL_TIGHT_AFTER_PCT = env_float("TRAIL_TIGHT_AFTER_PCT", 1.0)
FEE_BUFFER = env_float("FEE_BUFFER", 0.0015)
LIMIT_SLIPPAGE_PCT = env_float("LIMIT_SLIPPAGE_PCT", 0.20)

# ── المراكز والتهدئة ──────────────────────────────────────────────────────────
MAX_OPEN_POSITIONS = max(1, env_int("MAX_OPEN_POSITIONS", 15))   # V5.3: رشاش 15 مركزاً
MAX_POSITIONS_PER_SYMBOL = max(1, env_int("MAX_POSITIONS_PER_SYMBOL", 3))
SAME_SYMBOL_COOLDOWN = max(0, env_int("SAME_SYMBOL_COOLDOWN", 90))  # تُغطى ديناميكياً
TIME_STOP_ENABLED = env_bool("TIME_STOP_ENABLED", True)
TIME_STOP_SEC = max(15, env_int("TIME_STOP_SEC", 45))        # V6.0 Hit & Run: 45 ثانية فقط
TIME_STOP_CHECK_EVERY = max(3, env_int("TIME_STOP_CHECK_EVERY", 5))  # فحص دقيق: سقف 45ث لا يحتمل 60ث
TIME_STOP_MIN_PROFIT_PCT = env_float("TIME_STOP_MIN_PROFIT_PCT", 0.10)  # ربح < +0.10% بعد المهلة → تصفية

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
CANDLES = {}          # (symbol, "1m") -> {"t","o","h","l","c","v","live"} — ATR(1m) فقط (V6.0)
BOOK = {}             # symbol -> {"bid","ask","bid_vol","ask_vol","spread_pct","ts"}
FLOW = {}             # symbol -> {"buy","sell","ts","epoch","price","buckets"} (aggTrade حقيقي)
TICKS = {}            # V6.0: symbol -> {"prices","maxq","minq"} ذاكرة aggTrade متدحرجة 15ث
PENDING_SNIPES = {}   # V6.0: symbol -> monotonic ts — هبوط قائم ينتظر تأكيد جدار bookTicker
HFT_ATTEMPT = {}      # V6.0: symbol -> monotonic ts — خنق محاولات القنّاص لكل عملة
SPRAY_BASE = {}       # V6.1: symbol -> {"dq","next","med","med_ts"} خط أساس التقلب التكيفي
SPRAY_ATTEMPT = {}    # V6.1: symbol -> monotonic ts — خنق تقييم الرشاش (≤1Hz/عملة)
SPREAD_MEM = {}       # V6.1: symbol -> deque(spread_pct) — سبريد نمطي لكل عملة (تكيفي)
FLOW_REV_AT = {}      # V6.1: pid -> monotonic ts — خنق خروج انعكاس التدفق لكل مركز
SCALE_PENDING = set() # V6.1: pids قيد بيع جزئي جارٍ (منع تكرار Scale-Out)
ORDER_TS = deque()    # V6.1: طوابع monotonic للأوامر المُرسلة — ميزانية 10ث (حد Binance)
SHADOW_THROTTLE = {}  # V6.2: symbol -> ts — خنق فتح الصفقات الظلية لكل عملة
SHADOW_ATTEMPT = {}   # V6.2.1: symbol -> ts — خنق مسبار القنّاص الظلي (3ث)
SHADOW_SYMS = set()   # V6.2.1: رموز ذات صفقات ظلية مفتوحة — قفز مبكر O(1) لكل tick
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
GEMINI_READY = False          # V6.0: تُضبط بواسطة gemini_configure() عند الإقلاع


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
        "scale_outs": 0,         # V6.1: عدد عمليات البيع الجزئي الرابحة
        "fees_paid": 0.0,        # V6.1: إجمالي العمولات المقدَّرة (وعي بالرسوم)
        "gov": {                 # V6.1: الحاكم — قواطع التوقف الحكيمة
            "pause_until": 0.0,  # طابع time.time — لا دخولات قبله
            "pause_reason": "",
            "hourly": [],        # [(ts, pnl_net), ...] نافذة متدحرجة ساعة
            "daily_pnl": 0.0,
            "daily_date": "",    # YYYY-MM-DD — تصفير تلقائي عند تغير اليوم
        },
        "shadow": {              # V6.2: دفتر البحث الظلي (بلا أي أوامر حقيقية)
            "stats": {},         # trigger -> {opened, closed, wins, losses, net, gross, fees}
            "open": {},          # sid -> مركز افتراضي قيد الإدارة
            "history": [],       # آخر النتائج المسجلة (سقف صلب)
            "skipped": 0,        # صفقات ظلية لم تُفتح لامتلاء السقف
        },
        "trade_log": [],         # V6.0: سجل الصفقات المغلقة (تشريح /autopsy)
        "be_trigger_pct": None,  # V6.0: يضبطه Gemini Auto-Tune ديناميكياً (None = الافتراضي)
        "time_stop_sec": None,   # V6.0: يضبطه Gemini Auto-Tune ديناميكياً (None = الافتراضي)
        "last_tune": None,       # V6.0: آخر ضبط ناجح {ts, القيم, السبب}
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
        # V6.1: حقول محاسبة الرسوم/البيع الجزئي (افتراضيات آمنة للمراكز القديمة)
        position.setdefault("entry_quote", 0.0)
        position.setdefault("fees_entry", 0.0)
        position.setdefault("partial_pnl", 0.0)
        position.setdefault("fees_partial", 0.0)
        position.setdefault("scaled", False)
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
        if not isinstance(base.get("trade_log"), list):
            base["trade_log"] = []
        for key in ("be_trigger_pct", "time_stop_sec", "last_tune"):
            base.setdefault(key, None)
        base["last_dust_sweep"] = float(base.get("last_dust_sweep", 0.0) or 0.0)
        base["scale_outs"] = int(base.get("scale_outs", 0) or 0)
        base["fees_paid"] = float(base.get("fees_paid", 0.0) or 0.0)
        gov = base.get("gov") if isinstance(base.get("gov"), dict) else {}
        base["gov"] = {
            "pause_until": float(gov.get("pause_until", 0.0) or 0.0),
            "pause_reason": str(gov.get("pause_reason", "") or ""),
            "hourly": [row for row in (gov.get("hourly") or [])
                       if isinstance(row, (list, tuple)) and len(row) == 2],
            "daily_pnl": float(gov.get("daily_pnl", 0.0) or 0.0),
            "daily_date": str(gov.get("daily_date", "") or ""),
        }
        base["shadow"] = normalize_shadow(base.get("shadow"))
        SHADOW_SYMS.update({p.get("symbol") for p in base["shadow"]["open"].values()
                            if isinstance(p, dict) and p.get("symbol")})
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
    """تسخين أولي: شموع 1m فقط — ذاكرة ATR(1m) لوقف الطوارئ (لا شموع إشارة في V6.0)."""
    payload = await REST.klines(symbol, MICRO_INTERVAL, KLINE_REST_LIMITS[MICRO_INTERVAL])
    buffer = build_buffer(payload, MICRO_INTERVAL)
    if buffer is None:
        raise BinanceError(f"بيانات {symbol} {MICRO_INTERVAL} غير كافية")
    if len(buffer["c"]) < ATR_PERIOD + 1:
        log(f"تحذير: تاريخ 1m قصير لـ {symbol} ({len(buffer['c'])}) — الوقف سيعتمد الأرضية")
    CANDLES[(symbol, MICRO_INTERVAL)] = buffer
    BOOK.pop(symbol, None)
    TICKS.pop(symbol, None)
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
    """معالج aggTrade: Micro-Memory 15ث + تدفق + تقييم قنّاص لحظي لكل صفقة.

    V6.0: هذا هو قلب الإشارة — لا شموع ولا إغلاقات؛ كل tick قد يكون الزناد.
    """
    try:
        if SYMBOLS and symbol not in SYMBOLS_SET:
            return
        ts_ms = float(data.get("T") or data.get("t") or 0)
        price = float(data.get("p") or 0)
        qty = float(data.get("q") or 0)
        if price <= 0 or qty <= 0:
            return
        quote = price * qty
        ts = ts_ms / 1000.0 if ts_ms else time.time()
        # V6.0 — الحوت تلميح تشخيصي فقط (/insight): لا تأثير على الدخول
        if quote >= WHALE_TRADE_USD and not bool(data.get("m")):
            whale_mark(symbol, quote, ts)
        if bool(data.get("m")):
            state = flow_add(symbol, ts, 0.0, quote)
        else:
            state = flow_add(symbol, ts, quote, 0.0)
        state["price"] = price
        state["epoch"] = time.time()
        tick_add(symbol, ts, price)            # ذاكرة الأسعار المتدحرجة 15ث
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


def plan_position(entry, sl_distance, step=None, vr=1.0,
                  risk_target=None, notional_cap=None):
    """حجم مبانٍ على المخاطرة: notional = R / (sl_distance / entry).

    V5.3: إذا كان VR > VR_FAST (فوضى/تقلب متطرف) يُنصَّف الحجم لتقليل التعرض.
    V6.1: risk_target/notional_cap يسمحان لمسار القنّاص بحجم مضخّم دون لمس
    افتراضيات الرشاش.

    يُقيَّد بسقف المركز، ويُرفض إن كان أصغر من حد Binance الأدنى.
    يعيد (qty, notional, risk_usd) أو (None, None, None).
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
    risk_usd_target = D(TARGET_RISK_USD) if risk_target is None else D(str(risk_target))
    cap = D(MAX_POSITION_NOTIONAL_USD) if notional_cap is None else D(str(notional_cap))
    # notional = R / (sl/entry) = R × entry / sl — صيغة واحدة بلا تقريب المقلوب
    notional = (risk_usd_target * entry) / sl_distance
    try:
        vr_f = float(vr)
    except (TypeError, ValueError):
        vr_f = 1.0
    if VOL_SIZE_HALVE and math.isfinite(vr_f) and vr_f > VR_FAST:
        notional = notional / Decimal("2")     # سوق فوضوي → نصف التعرض
    if notional > cap:
        notional = cap
    if not math.isfinite(float(notional)) or notional <= 0:
        return None, None, None
    qty = round_step(notional / entry, step) if step > 0 else (notional / entry)
    if qty <= 0:
        return None, None, None
    notional = qty * entry
    risk_usd = (notional * sl_distance) / entry
    # حارس V5.3: بعد التقريب/السقف قد تتجاوز المخاطرة الفعلية الهدف — لا تتجاوزه أبداً
    if risk_usd > risk_usd_target * D(RISK_TOLERANCE):
        return None, None, None
    return qty, notional, risk_usd


def micro_atr(symbol, atr_fallback=0.0):
    """ATR(1m) لوقف الطوارئ الصلب — رجوع آمن إلى القيمة المُمرَّرة عند غياب 1m."""
    try:
        buffer = CANDLES.get((symbol, MICRO_INTERVAL))
        if buffer and len(buffer.get("c") or []) >= ATR_PERIOD + 1:
            value = atr_last(buffer["h"], buffer["l"], buffer["c"], ATR_PERIOD)
            if math.isfinite(value) and value > 0:
                return float(value)
    except Exception:
        pass
    fallback = float(atr_fallback or 0.0)
    if not math.isfinite(fallback) or fallback <= 0:
        return 0.0
    return fallback


def market_price(symbol):
    """أفضل سعر تنفيذ متاح: آخر tick (aggTrade) ثم BBA ثم الشمعة الحية 1m."""
    flow = FLOW.get(symbol) or {}
    book = BOOK.get(symbol) or {}
    buffer = CANDLES.get((symbol, MICRO_INTERVAL)) or {}
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
# 6) محرك القنص اللحظي (V6.0): Micro-Memory 15ث + Flash-Crash + Buy Wall
# ══════════════════════════════════════════════════════════════════════════════
# لا شموع إشارة ولا تنقيط ولا بوابات AND: القرار من تدفق aggTrade (ذاكرة 15ث)
# وتأكيد bookTicker اللحظي (جدار الشراء) — تنفيذ MARKET في نفس اللحظة.


def tick_memory(symbol):
    """ذاكرة أسعار aggTrade لكل عملة: نافذة متدحرجة + عارضتا قمة وقاع انزلاقيتان.

    "maxq"/"minq" تنفّذان sliding-window maximum/minimum بلا أي مسح للنافذة: كل tick يدخل
    ويخرج مرة واحدة بالضبط ⇒ O(1) مُستهلكة لكل صفقة (HFT-safe).
    """
    return TICKS.setdefault(symbol, {"prices": deque(), "maxq": deque(), "minq": deque()})


def tick_prune(mem):
    """يُقلم ما خرج من نافذة الذاكرة (سعر التسلسل + القمم المنتهية).

    الأفق نسبي لآخر طابع زمني داخل التدفق نفسه (mem["latest"]) لا لساعة
    الجهاز: انزياح ساعة المضيف عن وقت خادم Binance بما يفوق النافذة كان
    سيُفرّغ الذاكرة بالكامل ويقتل الزناد صامتةً — ثغرة ساعة، سُدّت.
    """
    horizon = float(mem.get("latest", 0.0) or 0.0) - TICK_MEMORY_SEC
    if horizon <= 0:
        return
    prices = mem["prices"]
    maxq = mem["maxq"]
    while prices and prices[0][0] < horizon:
        prices.popleft()
    while maxq and maxq[0][0] < horizon:
        maxq.popleft()
    minq = mem.get("minq")
    if minq is not None:
        while minq and minq[0][0] < horizon:
            minq.popleft()


def tick_add(symbol, ts, price):
    """يُسجّل سعراً لحظياً في Micro-Memory (15ث) ويُقلم المنتهي — بلا حجب.

    صفقة أقدم من أفق النافذة (وصلت متأخرة/خارج الترتيب) تُهمَل كلياً حتى
    لا تُلوّث «آخر سعر» الذي يُحسب عليه هبوط الفلاش كراش.
    """
    mem = tick_memory(symbol)
    ts = float(ts)
    price = float(price)
    if not math.isfinite(price) or price <= 0 or not math.isfinite(ts):
        return mem
    latest = float(mem.get("latest", 0.0) or 0.0)
    if latest > 0 and ts < latest - TICK_MEMORY_SEC:
        return mem          # صفقة متأخرة جداً — خارج النافذة، تُهمَل
    if ts > latest:
        mem["latest"] = ts
    mem["prices"].append((ts, price))
    maxq = mem["maxq"]
    while maxq and maxq[-1][1] <= price:
        maxq.pop()
    maxq.append((ts, price))
    minq = mem.get("minq")
    if minq is None:
        minq = mem["minq"] = deque()
    while minq and minq[-1][1] >= price:
        minq.pop()
    minq.append((ts, price))
    tick_prune(mem)
    return mem


def tick_window_stats(symbol):
    """إحصاء النافذة: {high, low, last, samples, span} أو None إذا الذاكرة غير كافية."""
    mem = TICKS.get(symbol)
    if not mem:
        return None
    tick_prune(mem)
    prices = mem["prices"]
    maxq = mem["maxq"]
    minq = mem.get("minq")
    if len(prices) < 2 or not maxq:
        return None
    low = float(minq[0][1]) if minq else min(p[1] for p in prices)
    return {"high": float(maxq[0][1]), "low": low,
            "last": float(prices[-1][1]),
            "samples": len(prices), "span": float(prices[-1][0] - prices[0][0])}


def flash_drop_pct(symbol):
    """نسبة الهبوط داخل نافذة 15ث: (قمة النافذة − آخر سعر) / القمة × 100."""
    stats = tick_window_stats(symbol)
    if not stats:
        return 0.0
    high = stats["high"]
    if high <= 0:
        return 0.0
    return (high - stats["last"]) / high * 100.0


def buy_wall_ratio(book):
    """نسبة جدار الشراء اللحظي: bid_vol / ask_vol (0.0 بلا بيانات، inf بلا طلبات)."""
    if not book:
        return 0.0
    ask_vol = float(book.get("ask_vol", 0) or 0)
    bid_vol = float(book.get("bid_vol", 0) or 0)
    if ask_vol <= 0:
        return math.inf if bid_vol > 0 else 0.0
    return bid_vol / ask_vol


def buy_wall_confirmed(symbol):
    """جدار شراء هائل وحديث: bid_vol > BUY_WALL_RATIO× ask_vol ضمن BUY_WALL_MAX_AGE.

    يعيد (مؤكد؟, النسبة) — bookTicker هو مصدر «الجرعة الفورية» للزناد.
    """
    book = BOOK.get(symbol) or {}
    age = time.monotonic() - float(book.get("ts", 0) or 0)
    if age > BUY_WALL_MAX_AGE:
        return False, 0.0
    ratio = buy_wall_ratio(book)
    return (ratio >= BUY_WALL_RATIO), ratio


def build_sniper_signal(symbol, drop_pct, wall_ratio):
    """يبني إشارة قنص جاهزة لنفس مسار التنفيذ اللاحق (حجم بالمخاطرة/وقف صلب)."""
    price, _age = market_price(symbol)
    if price <= 0:
        return None
    atr_1m = micro_atr(symbol)
    return {
        "symbol": symbol,
        "setup_id": f"{symbol}@flash@{int(time.time() * 1000)}",
        "trigger": "flash-crash",
        "drop_pct": float(drop_pct),
        "wall_ratio": float(wall_ratio if math.isfinite(wall_ratio) else 999.0),
        "atr": 0.0,
        "atr_1m": float(atr_1m),
        "vr": float(btc_ctx_stats().get("vr", 1.0)),
        "close": float(price), "live": float(price),
        "score": 0.0,
        "flow_imbalance": float(flow_imbalance(symbol)[0] or 0.0),
        "created_at": time.time(),
    }


def sniper_decision(symbol, for_shadow=False):
    """قرار القنّاص من الأحداث فقط (نقي — قابل للاختبار بلا شبكة).

    يعيد None (لا ظروف) أو {"action": "pending"|"fire", "drop_pct", "wall_ratio"}.
    pending = الانهيار قائم لكن bookTicker لم يؤكد الجدار بعد (ينتظر on_book).

    for_shadow=True (V6.2.1): يتجاوز بوابات المحرك الحقيقي (سقوف/تهدئة/حاكم)
    — المختبر الظلي يقيس جودة الزناد ذاتها ولا يجوز أن تتوقف عينته عندما
    يتوقف التنفيذ الحقيقي، وإلا تَشوّهت التجربة بفجوات مُحيّزة.
    """
    if not for_shadow and not _entry_gates_open(symbol):
        PENDING_SNIPES.pop(symbol, None)
        return None
    drop = flash_drop_pct(symbol)
    if drop < FLASH_DROP_PCT:
        PENDING_SNIPES.pop(symbol, None)     # الانهيار تبخّر من نافذة الذاكرة
        return None
    wall_ok, ratio = buy_wall_confirmed(symbol)
    if not wall_ok:
        return {"action": "pending", "drop_pct": drop, "wall_ratio": ratio}
    return {"action": "fire", "drop_pct": drop, "wall_ratio": ratio}


def handle_sniper_decision(symbol, decision):
    """ينفّذ قرار القنّاص: fire ⇒ MARKET BUY فوري عبر launch_entry (بلا حجب).

    HFT_ATTEMPT يخنق محاولات العملة (يمنع إغراق خيوط التنفيذ أثناء انهيار
    مستمر)، وPENDING_SNIPES يُبقي الصيد حياً لحين تأكيد الجدار في on_book.
    """
    now = time.monotonic()
    if now - float(HFT_ATTEMPT.get(symbol, 0.0)) < SNIPER_RETRY_SEC:
        return
    HFT_ATTEMPT[symbol] = now
    if decision.get("action") != "fire":
        if symbol not in PENDING_SNIPES:
            FUNNEL["no-buywall"] += 1
            log(f"قنّاص {symbol}: هبوط {decision['drop_pct']:.2f}% خلال {TICK_MEMORY_SEC:.0f}ث — "
                f"بانتظار جدار الشراء (bid/ask = {decision['wall_ratio']:.2f}x < {BUY_WALL_RATIO:g}x)")
        PENDING_SNIPES[symbol] = now
        return
    PENDING_SNIPES.pop(symbol, None)
    signal = build_sniper_signal(symbol, decision["drop_pct"], decision["wall_ratio"])
    if signal is None:
        return
    if signal["setup_id"] in SETUPS:
        return
    FUNNEL["flash-trigger"] += 1
    shadow_open(signal)      # V6.2: القياس الظلي يعمل مهما كان مسار التنفيذ الحقيقي
    log(f"⚡ قنّاص الانهيار: {symbol} هبوط {decision['drop_pct']:.2f}% خلال {TICK_MEMORY_SEC:.0f}ث "
        f"+ جدار شراء {decision['wall_ratio']:.2f}x → دخول فوري")
    launch_entry(signal)


def on_market_tick(symbol):
    """tick حقيقي (aggTrade): القنّاص + الرشاش + حرّاس الخروج في نفس اللحظة.

    V6.1: كل tick يمر على ثلاث طبقات: قنص الانهيار (V6.0)، ثم خروج بانعكاس
    التدفق للمراكز الرابحة، ثم زنادات الرشاش التكيفية — التنفيذ حدثي بالكامل
    (بلا إغلاق شموع).
    """
    decision = sniper_decision(symbol)
    if decision is not None:
        handle_sniper_decision(symbol, decision)
    shadow_sniper_tick(symbol)      # V6.2.1: القياس الظلي مستقل عن بوابات التنفيذ
    flow_reversal_check(symbol)
    handle_spray_tick(symbol)


# ── V6.1: الحاكم — الحكيم في متى يتوقف ──────────────────────────────────────

def _gov_default():
    return {"pause_until": 0.0, "pause_reason": "", "hourly": [],
            "daily_pnl": 0.0, "daily_date": ""}


def governor_update(pnl_net):
    """يحدّث نوافذ الخسارة بعد كل إغلاق ويشغّل قواطع التوقف. يعيد سبب الإيقاف أو ''.

    • 3 خسائر متتالية ⇒ توقف 10 دقائق (السوق يقول: ليس وقتك).
    • خسارة الساعة المتدحرجة ≤ −GOV_HOURLY_LOSS ⇒ توقف 30 دقيقة (لا انتقام).
    • خسارة اليوم ≤ −GOV_DAILY_LOSS ⇒ توقف حتى منتصف الليل (حماية رأس المال).
    """
    gov = STATE.setdefault("gov", dict(_gov_default()))
    now = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if gov.get("daily_date") != today:
        gov["daily_date"] = today
        gov["daily_pnl"] = 0.0
    hourly = [(float(t), float(p)) for t, p in (gov.get("hourly") or [])
              if now - float(t) <= 3600.0]
    hourly.append((now, float(pnl_net)))
    gov["hourly"] = hourly[-500:]
    gov["daily_pnl"] = float(gov.get("daily_pnl", 0.0)) + float(pnl_net)
    if float(gov.get("pause_until", 0.0)) > now:
        return str(gov.get("pause_reason") or "gov")     # إيقاف قائم بالفعل
    reason = ""
    if int(STATE.get("metrics", {}).get("consecutive_losses", 0)) >= GOV_MAX_STREAK:
        reason = (f"gov-streak ({GOV_MAX_STREAK} خسائر متتالية ⇒ توقف "
                  f"{GOV_STREAK_PAUSE_SEC // 60}د)")
        gov["pause_until"] = now + GOV_STREAK_PAUSE_SEC
        FUNNEL["gov-streak"] += 1
    else:
        hour_pnl = sum(p for _t, p in hourly)
        if Decimal(str(round(hour_pnl, 6))) <= -GOV_HOURLY_LOSS_USD:
            reason = (f"gov-hourly (خسارة الساعة {hour_pnl:.2f}$ ≤ "
                      f"-{GOV_HOURLY_LOSS_USD}$ ⇒ توقف {GOV_HOURLY_PAUSE_SEC // 60}د)")
            gov["pause_until"] = now + GOV_HOURLY_PAUSE_SEC
            FUNNEL["gov-hourly"] += 1
        elif Decimal(str(round(gov["daily_pnl"], 6))) <= -GOV_DAILY_LOSS_USD:
            midnight = datetime.now(timezone.utc).replace(hour=0, minute=0,
                                                          second=0, microsecond=0)
            midnight = midnight.timestamp() + 86400.0
            reason = (f"gov-daily (خسارة اليوم {gov['daily_pnl']:.2f}$ ≤ "
                      f"-{GOV_DAILY_LOSS_USD}$ ⇒ توقف حتى الغد)")
            gov["pause_until"] = midnight
            FUNNEL["gov-daily"] += 1
    if reason:
        gov["pause_reason"] = reason
        log(f"🛑 الحاكم: {reason}")
    return reason


def governor_blocked():
    """(ممنوع؟, السبب): لا دخولات جديدة أثناء أي إيقاف حاكم."""
    gov = STATE.get("gov") or {}
    if time.time() < float(gov.get("pause_until", 0.0) or 0.0):
        return True, str(gov.get("pause_reason") or "gov-pause")
    return False, ""


# ── V6.1: ميزانية الأوامر — نحترم حد Binance (50 أمر/10ث) بهامش أمان ────────

def order_budget_take(n, force=False):
    """يستهلك n خانة من ميزانية الأوامر في نافذة 10ث. force=True للخروج الأماني فقط."""
    now = time.monotonic()
    while ORDER_TS and now - ORDER_TS[0] > ORDER_BUDGET_WINDOW:
        ORDER_TS.popleft()
    if not force and len(ORDER_TS) + n > ORDER_BUDGET_MAX:
        return False
    for _ in range(int(n)):
        ORDER_TS.append(now)
    return True


def order_budget_usage():
    """(مستهلك الآن, السقف) — للتشخيص في /context."""
    now = time.monotonic()
    while ORDER_TS and now - ORDER_TS[0] > ORDER_BUDGET_WINDOW:
        ORDER_TS.popleft()
    return len(ORDER_TS), ORDER_BUDGET_MAX


# ── V6.1: سبريد تكيفي — السبريد النمطي لكل عملة بدل الحاجز الجامد ───────────

def spread_typical(symbol):
    """السبريد النمطي (وسيط آخر 120 تحديث bookTicker) — 0.0 بلا بيانات كافية."""
    mem = SPREAD_MEM.get(symbol)
    if not mem or len(mem) < 20:
        return 0.0
    try:
        return float(np.median(np.fromiter(mem, dtype=float, count=len(mem))))
    except Exception:
        return 0.0


def spread_limit_for(symbol, signal=None):
    """الحد الأقصى للسبريد: تكيفي حسب المسار (القنّاص أرحب لأن الانهيار يوسّعه طبيعياً)."""
    typ = spread_typical(symbol)
    trig = str((signal or {}).get("trigger", "") or "")
    mult = SPREAD_SNIPE_MULT if trig == "flash-crash" else SPREAD_SPRAY_MULT
    if typ <= 0:
        return MAX_SPREAD_PCT
    return min(SPREAD_ADAPTIVE_CAP, max(MAX_SPREAD_PCT, typ * mult))


# ── V6.1: خروج بانعكاس التدفق — اخرج قبل الكسر لا عنده ──────────────────────

def flow_reversal_check(symbol):
    """مراكز رابحة + انقلاب aggTrade إلى بيع ضاغط ⇒ MARKET SELL فوري (خنق لكل مركز)."""
    if not FLOW_REV_EXIT:
        return
    positions = STATE.get("positions") or {}
    if not positions:
        return
    state = FLOW.get(symbol) or {}
    sell_quote = float(state.get("sell", 0.0) or 0.0)
    buy_quote = float(state.get("buy", 0.0) or 0.0)
    if sell_quote < FLOW_REV_MIN_USD or buy_quote <= 0:
        return
    if sell_quote / buy_quote < FLOW_REV_RATIO:
        return
    now = time.monotonic()
    for pid, position in list(positions.items()):
        if position.get("symbol") != symbol or not position.get("trail_armed"):
            continue
        if pid in EXIT_PENDING or pid in EXIT_CLAIMED or pid in SCALE_PENDING:
            continue
        entry = float(position.get("entry", 0) or 0)
        price = float(position.get("last_price", 0) or 0)
        peak = float(position.get("peak", entry) or entry)
        if entry <= 0 or price <= 0:
            continue
        gain_pct = (price - entry) / entry * 100.0
        if gain_pct < FLOW_REV_MIN_GAIN:
            continue
        if now - float(FLOW_REV_AT.get(pid, 0.0)) < FLOW_REV_COOLDOWN:
            continue
        FLOW_REV_AT[pid] = now
        FUNNEL["flow-rev"] += 1
        reason = (f"انعكاس التدفق: بيع {sell_quote:.0f}$ ≥ {FLOW_REV_RATIO:g}× شراء "
                  f"{buy_quote:.0f}$ عند ربح {gain_pct:+.2f}% → خروج قبل الكسر")
        log(f"🌊 {pid}: {reason}")
        trigger_trailing_exit(pid, position, reason)


# ── V6.1: محرك الرشاش — 3 زنادات OR بعتبات تكيفية لكل عملة ──────────────────

def spray_baseline_push(symbol, stats):
    """عينة خط الأساس: حركة النافذة تُدفع لذاكرة 30د كل SPRAY_SAMPLE_EVERY.

    حاجز التلوّث: الاندفاع الجاري لا يُسمح له برفع عتبته بنفسه — القيمة
    المسجَّلة تُقصّ عند max(3× الوسيط الحالي, 4× الأرضية).
    """
    now = time.monotonic()
    base = SPRAY_BASE.get(symbol)
    if base is None:
        base = SPRAY_BASE[symbol] = {"dq": deque(maxlen=720), "next": 0.0,
                                     "med": 0.0, "med_ts": 0.0}
    if now >= float(base.get("next", 0.0)):
        base["next"] = now + SPRAY_SAMPLE_EVERY
        high = float(stats.get("high", 0.0) or 0.0)
        low = float(stats.get("low", 0.0) or 0.0)
        if high > 0 and low > 0:
            move = abs(high - low) / low * 100.0
            med_now = float(base.get("med", 0.0) or 0.0)
            cap = max(3.0 * med_now, 4.0 * SPRAY_BASELINE_FLOOR_PCT)
            if math.isfinite(move) and move > 0:
                base["dq"].append((now, min(move, cap)))


def spray_threshold(symbol):
    """العتبة التكيفية: max(أرضية, SPRAY_BASELINE_K × وسيط النوافذ المغلقة فقط).

    «المغلقة» = عيّنات أقدم من نافذة الذاكرة بهامش — الاندفاع الجاري لا
    يدخل في وسيطه، فتبقى العتبة مستقرة ولا تُصمّ على الحركة الأولى.
    """
    base = SPRAY_BASE.get(symbol)
    now = time.monotonic()
    if base:
        closed = [float(mv) for ts, mv in base.get("dq", ())
                  if now - float(ts) > TICK_MEMORY_SEC + 10.0]
        if now - float(base.get("med_ts", 0.0)) > 30.0:
            try:
                base["med"] = float(np.median(closed)) if len(closed) >= 6 else 0.0
                base["med_ts"] = now
            except Exception:
                base["med"] = 0.0
    med = float((base or {}).get("med", 0.0) or 0.0)
    return max(SPRAY_BASELINE_FLOOR_PCT, SPRAY_BASELINE_K * med)


def rolling_high(symbol, bars=SPRAY_BREAKOUT_BARS):
    """قمة آخر N شمعة 1m مغلقة (Donchian مصغّر) — 0.0 بلا بيانات كافية."""
    buffer = CANDLES.get((symbol, MICRO_INTERVAL))
    if not buffer:
        return 0.0
    highs = buffer.get("h") or []
    closed = highs[:-1] if buffer.get("live") else highs
    if len(closed) < bars:
        return 0.0
    try:
        return float(np.max(np.asarray(closed[-bars:], dtype=float)))
    except Exception:
        return 0.0


def spray_decision(symbol):
    """قرار الرشاش من الأحداث فقط — أول زناد يشتغل يفوز (OR logic).

    يعيد None أو {"trigger": "impulse"|"flow"|"breakout", "move_pct", "thr", "flow_ratio"}.
    """
    stats = tick_window_stats(symbol)
    if not stats or int(stats.get("samples", 0)) < SPRAY_MIN_SAMPLES:
        return None
    spray_baseline_push(symbol, stats)
    thr = spray_threshold(symbol)
    low = float(stats.get("low", 0.0) or 0.0)
    high = float(stats.get("high", 0.0) or 0.0)
    last = float(stats.get("last", 0.0) or 0.0)
    if low <= 0 or high <= 0 or last <= 0:
        return None
    if last < high * (1.0 - SPRAY_NEAR_TOP_PCT / 100.0):
        return None                      # الحركة تلاشت — السعر بعيد عن القمة
    rise_pct = (last - low) / low * 100.0
    ratio, _age = flow_imbalance(symbol)
    # زناد 1 — اندفاعة صاعدة: صعود ≥ عتبة + هيمنة مشترين حقيقية
    if rise_pct >= thr and ratio >= SPRAY_IMPULSE_FLOW:
        return {"trigger": "impulse", "move_pct": rise_pct, "thr": thr,
                "flow_ratio": ratio}
    # زناد 2 — هيمنة تدفق: شراء ≥ 2.5× بيع + حركة ≥ 0.6× العتبة
    if ratio >= SPRAY_FLOW_RATIO and rise_pct >= thr * SPRAY_FLOW_MOVE_K:
        return {"trigger": "flow", "move_pct": rise_pct, "thr": thr,
                "flow_ratio": ratio}
    # زناد 3 — اختراق تقلب: كسر قمة آخر 20 دقيقة + تدفق مؤكد
    if rise_pct >= thr:
        high20 = rolling_high(symbol, SPRAY_BREAKOUT_BARS)
        if high20 > 0 and last > high20 and ratio >= SPRAY_BREAKOUT_FLOW:
            return {"trigger": "breakout", "move_pct": rise_pct, "thr": thr,
                    "flow_ratio": ratio}
    return None


def build_spray_signal(symbol, decision):
    """يبني إشارة رشاش جاهزة لنفس مسار التنفيذ (حجم الرشاش الافتراضي/وقف صلب)."""
    price, _age = market_price(symbol)
    if price <= 0:
        return None
    atr_1m = micro_atr(symbol)
    return {
        "symbol": symbol,
        "setup_id": f"{symbol}@{decision['trigger']}@{int(time.time() * 1000)}",
        "trigger": decision["trigger"],
        "move_pct": float(decision["move_pct"]),
        "thr": float(decision["thr"]),
        "flow_ratio": float(decision["flow_ratio"]),
        "atr": 0.0,
        "atr_1m": float(atr_1m),
        "vr": float(btc_ctx_stats().get("vr", 1.0)),
        "close": float(price), "live": float(price),
        "score": 0.0,
        "flow_imbalance": float(decision["flow_ratio"]),
        "created_at": time.time(),
    }


def shadow_sniper_tick(symbol):
    """V6.2.1 — مسبار القنّاص الظلي: يقيس زناد الانهيار بلا أي بوابات تنفيذ.

    يُخنق كل 3ث/عملة (نفس إيقاع القنّاص الحقيقي) ويحترم kill/paused فقط
    (نية المستخدم)، أما سقوف المراكز والتهدئة والحاكم فهي قيود مالٍ حقيقي
    لا علاقة لها بجودة الإشارة — القياس فوقها مباشرة.
    """
    if not SHADOW_ENABLED:
        return
    if kill_switch_active() or STATE.get("paused"):
        return
    now = time.monotonic()
    if now - float(SHADOW_ATTEMPT.get(symbol, 0.0)) < SNIPER_RETRY_SEC:
        return
    SHADOW_ATTEMPT[symbol] = now
    decision = sniper_decision(symbol, for_shadow=True)
    if decision is None or decision.get("action") != "fire":
        return
    signal = build_sniper_signal(symbol, decision["drop_pct"], decision["wall_ratio"])
    if signal is not None:
        shadow_open(signal)      # الخنق 30ث/عملة داخل shadow_open


def handle_spray_tick(symbol):
    """تقييم رشاش مخنوق (≤1Hz/عملة) — الإطلاق عبر launch_entry بلا حجب."""
    if not SPRAY_ENABLED:
        return
    now = time.monotonic()
    if now - float(SPRAY_ATTEMPT.get(symbol, 0.0)) < SPRAY_EVAL_EVERY:
        return
    SPRAY_ATTEMPT[symbol] = now
    if SYMBOLS and symbol not in SYMBOLS_SET:
        SPRAY_BASE.pop(symbol, None)
        SPRAY_ATTEMPT.pop(symbol, None)
        return
    if data_age(symbol) > MAX_STALE_SEC:
        FUNNEL["spray-stale"] += 1
        return                          # تدفق ميت — لا إشارات من بيانات متقادمة
    decision = spray_decision(symbol)
    if decision is None:
        return
    signal = build_spray_signal(symbol, decision)
    if signal is None or signal["setup_id"] in SETUPS:
        return
    FUNNEL[f"spray-{decision['trigger']}"] += 1
    shadow_open(signal)      # V6.2: كل زناد رشاش يقاس ظلياً أيضاً
    log(f"🚀 رشاش {symbol}: {decision['trigger']} حركة {decision['move_pct']:.2f}% "
        f"(عتبة {decision['thr']:.2f}%) تدفق {decision['flow_ratio']:.1f}x → دخول فوري")
    launch_entry(signal)



def veto_reason(symbol, signal=None):
    """الفلاتر القاطعة بعد التنقيط: سياق BTC + سبريد تكيفي + قدم البيانات."""
    blocked, why = btc_circuit_block()
    if blocked:
        FUNNEL["btc-breaker"] += 1
        return why
    book = BOOK.get(symbol) or {}
    limit = spread_limit_for(symbol, signal)
    if book and float(book.get("spread_pct") or 0) > limit:
        FUNNEL["spread"] += 1
        return "spread"
    if data_age(symbol) > MAX_STALE_SEC:
        FUNNEL["stale-tick"] += 1
        return "stale-tick"
    return None


def _entry_gates_open(symbol):
    """بوابات رخيصة قبل أي تقييم: قاطع، حاكم، سقف مراكز، تهدئة ديناميكية."""
    if kill_switch_active() or STATE.get("paused"):
        return False
    if governor_blocked()[0]:
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



def on_kline(data):
    """معالج kline_1m: يحدّث الحية ويُلحق المغلقة — ذاكرة ATR(1m) للحماية فقط.

    V6.0: إعدام on_signal_candle_closed نهائياً؛ الشموع هنا حسابية فقط
    (ATR لوقف الطوارئ وحجم المخاطرة) ولا علاقة لها بأي قرار دخول.
    """
    try:
        if not isinstance(data, dict) or data.get("e") != "kline":
            return
        k = data.get("k") or {}
        symbol = data.get("s")
        interval = k.get("i")
        if interval != MICRO_INTERVAL:
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
            try:      # V6.1: ذاكرة السبريد النمطي (وسيط 120 تحديثاً) للحد التكيفي
                _sp = float(parsed.get("spread_pct") or 0.0)
                if math.isfinite(_sp) and _sp >= 0:
                    SPREAD_MEM.setdefault(symbol, deque(maxlen=120)).append(_sp)
            except Exception:
                pass
            # التسعير للخروج يعتمد أفضل سعر بيع فوري (bid) — تحفّظ سليم
            on_price_update(symbol, parsed.get("bid") or 0.0)
            shadow_on_price(symbol, parsed.get("bid") or 0.0)   # V6.2
            shadow_sniper_tick(symbol)                          # V6.2.1: تأكيد الجدار يصل المسبار أيضاً
            # V6.0: هبوط قائم ينتظر الجدار فقط ⇒ bookTicker هو حدث التأكيد الثاني
            if symbol in PENDING_SNIPES:
                decision = sniper_decision(symbol)
                if decision is not None:
                    handle_sniper_decision(symbol, decision)
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
                log(f"تعادل مؤمَّن {pid}: ربح القمة {plan['peak_gain_pct']:+.2f}% "
                    f"(عتبة +{get_be_trigger_pct():g}%) → "
                    f"وقف محلي {fmt_price(symbol, plan['stop'])} (دخول +{BREAKEVEN_LOCK_PCT}%)")
            position["trail_stop"] = float(plan["stop"])
            position["trail_mode"] = plan["mode"]
            maybe_scale_out(pid, position, symbol, plan["peak_gain_pct"])
            if plan["hit"]:
                trigger_trailing_exit(pid, position, plan)
    except Exception as exc:
        log(f"خطأ محرك التتبّع {symbol}: {exc}")


def maybe_scale_out(pid, position, symbol, peak_gain_pct):
    """V6.1 — البيع الجزئي: عند +SCALE_OUT_AT_PCT ربح القمة يُباع جزء ويبقي الباقي للتتبّع.

    حرّاس صارمة: الباقي يجب أن يبقى قابلاً للبيع فوق minNotional حتى بعد وقف
    الطوارئ، وإلا نُعلّم المركز scale_skip ولا نحاول مجدداً (منع غبار عالق).
    """
    if not SCALE_OUT_ENABLED or pid in SCALE_PENDING:
        return
    if pid in EXIT_CLAIMED or pid in EXIT_PENDING:
        return
    if position.get("scaled") or position.get("scale_skip"):
        return
    try:
        if float(peak_gain_pct or 0.0) < SCALE_OUT_AT_PCT:
            return
        qty = D(position.get("qty", "0"))
        entry = float(position.get("entry", 0) or 0)
        price = float(position.get("last_price", 0) or 0)
        if qty <= 0 or entry <= 0 or price <= 0:
            return
        half = sellable_qty(symbol, qty * D(str(SCALE_OUT_FRACTION)), price)
        if half is None or half <= 0:
            position["scale_skip"] = True
            return
        rest = sellable_qty(symbol, qty - half, price * (1.0 - SL_MAX_PCT / 100.0))
        if rest is None:
            position["scale_skip"] = True   # البقايا ستغدو غباراً — لا بيع جزئي
            return
        position["scaled"] = True
        SCALE_PENDING.add(pid)
        order_budget_take(1, force=True)
        asyncio.get_running_loop().create_task(_scale_out_task(pid, half, price))
    except RuntimeError:
        position["scaled"] = False
    except Exception as exc:
        log(f"خطأ بيع جزئي {pid}: {exc}")
        position["scaled"] = False


async def _scale_out_task(pid, half_qty, ref_price):
    """مهمة البيع الجزئي: MARKET SELL للجزء + تحديث محاسبة الرسوم + إعادة تركيب الوقف."""
    try:
        async with STATE_LOCK:
            live = STATE.get("positions", {}).get(pid)
        if live is None:
            return
        symbol = live.get("symbol", "")
        entry = float(live.get("entry", 0) or 0)
        if not live_execution_allowed():
            log(f"[DRY] بيع جزئي {pid}: {dec_str(half_qty)} عند {fmt_price(symbol, ref_price)} "
                f"(التنفيذ غير مفعّل)")
            return
        order = await emergency_sell(symbol, half_qty, "بيع جزئي (Scale-Out)", already_net=True)
        if not order:
            async with STATE_LOCK:
                live = STATE.get("positions", {}).get(pid)
                if live is not None:
                    live["scaled"] = False      # أعِد المحاولة عند التِك التالي
            return
        qty_out, quote_out, avg = parse_fill(order, ref_price)
        gross = (float(avg or 0) - entry) * float(qty_out or 0)
        fees = float(quote_out or 0) * FEE_TAKER_RATE
        async with STATE_LOCK:
            live = STATE.get("positions", {}).get(pid)
            if live is not None:
                live["qty"] = dec_str(max(D("0"), D(live.get("qty", "0")) - D(str(qty_out))))
                live["partial_pnl"] = float(live.get("partial_pnl", 0.0) or 0.0) + gross
                live["fees_partial"] = float(live.get("fees_partial", 0.0) or 0.0) + fees
                STATE["scale_outs"] = int(STATE.get("scale_outs", 0)) + 1
                STATE["fees_paid"] = float(STATE.get("fees_paid", 0.0) or 0.0) + fees
        FUNNEL["scale-out"] += 1
        log(f"💰 بيع جزئي {pid}: {dec_str(D(str(qty_out)))} @ {fmt_price(symbol, avg)} "
            f"ربح جزئي {gross:+.4f}$ (رسوم {fees:.4f}$) — الباقي يستمر بالتتبّع")
        # الوقف على Binance ما زال بالكمية الكاملة القديمة ⇒ بدّله بكمية الباقي
        async with STATE_LOCK:
            live = STATE.get("positions", {}).get(pid)
        if live is not None:
            try:
                await cancel_hard_stop(live)
            except Exception as exc:
                log(f"بيع جزئي {pid}: تعذر إلغاء الوقف القديم ({exc})")
            await rearm_hard_stop(pid, reason="بيع جزئي — وقف بكمية الباقي")
    except Exception as exc:
        log(f"خطأ مهمة البيع الجزئي {pid}: {exc}")
        async with STATE_LOCK:
            live = STATE.get("positions", {}).get(pid)
            if live is not None:
                live["scaled"] = False
    finally:
        SCALE_PENDING.discard(pid)


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
        micro = float(atr_value or 0.0)      # V6.0: 1m أولاً ثم قيمة مرجعية مُمرَّرة
        if not math.isfinite(micro) or micro <= 0:
            micro = 0.0                      # بلا ATR إطلاقاً → أرضية الوقف SL_MIN_PCT
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


def get_be_trigger_pct():
    """BREAKEVEN_TRIGGER_PCT الفعّال: يُحدَّث ديناميكياً بمعاملات Gemini داخل STATE.

    قراءة قاموس بلا قفل (GIL-atomic) — آمن في المسار الساخن لكل bookTicker tick.
    """
    try:
        value = float(STATE.get("be_trigger_pct"))
    except (TypeError, ValueError):
        return BREAKEVEN_TRIGGER_PCT
    if not math.isfinite(value) or value <= 0:
        return BREAKEVEN_TRIGGER_PCT
    return clamp(value, 0.05, 5.0)


def get_time_stop_sec():
    """TIME_STOP_SEC الفعّال: يُحدَّث ديناميكياً بمعاملات Gemini داخل STATE."""
    try:
        value = int(round(float(STATE.get("time_stop_sec"))))
    except (TypeError, ValueError):
        return TIME_STOP_SEC
    if value <= 0:
        return TIME_STOP_SEC
    return int(clamp(value, 10, 3600))


def trailing_plan(entry, peak, price):
    """محرك الخروج الهجين (نقي وقابل للاختبار) — عتبة التعادل من STATE (Gemini-aware).

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
    be_trigger = get_be_trigger_pct()
    if peak_gain_pct < be_trigger:
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


async def reserve_entry(symbol, cost=None, cooldown_sec=None):
    """حجز ذري (ENTRY_LOCK): سقف مراكز + تهدئة + حاكم + حجز تكلفة تقديرية.

    أمر MARKET لا يحمل سعراً مسبقاً، لذا تُحجز تكلفة تقديرية (قيمة المركز
    + هامش انزلاق) لمنع تجاوز الرصيد عند تزامن عدة دخولات — ترقيع سباق الدخول.
    cooldown_sec: تهدئة خاصة بالمسار (الرشاش أقصر من تهدئة القنّاص/الكلية).
    """
    global RESERVED_QUOTE
    cost = D(TARGET_RISK_USD) if cost is None else D(cost)
    async with ENTRY_LOCK:
        if kill_switch_active() or STATE.get("paused"):
            return False
        if governor_blocked()[0]:
            FUNNEL["reserve-gov"] += 1
            return False
        current = count_symbol_positions(symbol)
        reserved = ENTRY_RESERVATIONS.get(symbol, 0)
        if current + reserved >= MAX_POSITIONS_PER_SYMBOL:
            FUNNEL["reserve-symbol-cap"] += 1
            return False
        if count_open_positions() + total_reserved_slots() >= MAX_OPEN_POSITIONS:
            FUNNEL["reserve-global-cap"] += 1
            return False
        limit = btc_cooldown() if cooldown_sec is None else min(
            btc_cooldown(), float(cooldown_sec))
        if time.time() - float(STATE.get("last_entry_at", {}).get(symbol, 0.0)) < limit:
            FUNNEL["reserve-cooldown"] += 1
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
    if SHADOW_ONLY:
        FUNNEL["shadow-only"] += 1
        return False                    # مختبر صامت: القياس الظلي فقط بلا أي أوامر
    is_sniper = str(signal.get("trigger", "") or "") == "flash-crash"
    if not order_budget_take(ORDER_BUDGET_ENTRY_COST):
        FUNNEL["budget"] += 1
        log(f"إلغاء إشارة {symbol}: ميزانية الأوامر ({ORDER_BUDGET_MAX}/{ORDER_BUDGET_WINDOW:.0f}ث) ممتلئة")
        return False
    veto = veto_reason(symbol, signal)
    if veto:
        log(f"إلغاء إشارة {symbol}: {veto} (score={signal.get('score', 0):.0f})")
        return False
    priced = estimate_entry_cost(signal)
    if priced is None:
        log(f"إلغاء إشارة {symbol}: بيانات سوق قديمة أو حجم دون الحد الأدنى")
        return False
    est_cost = D(priced["est_cost"])
    cooldown = None if is_sniper else SPRAY_COOLDOWN_SEC
    if not await reserve_entry(symbol, est_cost, cooldown_sec=cooldown):
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
    if not atr_1m or float(atr_1m) <= 0:
        FUNNEL["no-atr"] += 1
        return None     # V6.0: بلا ATR(1m) لا وقف طوارئ عاقل ⇒ تُرفض القنصة
    risk = calculate_dynamic_risk(price, signal["atr"], signal.get("vr", 1.0), atr_1m)
    step = (SYMBOL_RULES.get(symbol) or {}).get("step")
    # V6.1: القنّاص (اقتناع أعلى) يحصل على مخاطرة وسقف مركز مضخّمين؛ الرشاش بالافتراضي
    if str(signal.get("trigger", "") or "") == "flash-crash":
        qty, notional, risk_usd = plan_position(
            price, risk["sl_distance"], step, signal.get("vr", 1.0),
            risk_target=D(TARGET_RISK_USD) * D(str(SNIPER_RISK_MULT)),
            notional_cap=SNIPER_MAX_NOTIONAL_USD)
    else:
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
    # V6.2: سعر الصانع = أفضل شراء حالي (نكسب السبريد بدل دفعه) — مع حارس معقولية
    _book = BOOK.get(symbol) or {}
    _bid = float(_book.get("bid") or 0)
    updated["maker_price"] = _bid if 0 < _bid < float(price) else float(price)
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
            log(f"قنصة V6 [DRY-RUN] {symbol} @ {fmt_price(symbol, price)} "
                f"trigger={signal.get('trigger', 'flash-crash')} "
                f"drop={signal.get('drop_pct', 0.0):.2f}% wall={signal.get('wall_ratio', 0.0):.2f}x "
                f"VR={signal.get('vr', 1.0):.2f} "
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
            "trigger": str(signal.get("trigger", "flash-crash") or "flash-crash"),
            "drop_pct": float(signal.get("drop_pct", 0.0) or 0.0),
            "wall_ratio": float(signal.get("wall_ratio", 0.0) or 0.0),
            "maker": bool(MAKER_ENTRIES),
            "placed_at": time.time(), "active": True, "phase": "placing",
        }
        async with STATE_LOCK:
            STATE["pending_entries"][entry_client_id] = record
        await save_state()
        # V6.2: الصانع (LIMIT_MAKER) عند أفضل شراء = نكسب السبريد بدل دفعه؛
        # وإلا MARKET كما في V6.0/V6.1. كلاهما نفس مسار الأحداث والوقف.
        order_params = {
            "symbol": symbol, "side": "BUY",
            "quantity": dec_str(qty),
            "newClientOrderId": entry_client_id, "newOrderRespType": "FULL",
        }
        if MAKER_ENTRIES:
            maker_price = round_price(D(str(signal.get("maker_price") or price)),
                                      rule["tick"], "down")
            if maker_price >= price:
                maker_price = round_price(price - rule["tick"], rule["tick"], "down")
            order_params["type"] = "LIMIT_MAKER"
            order_params["price"] = dec_str(maker_price)
        else:
            order_params["type"] = "MARKET"
        order = await REST.new_order(order_params)
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
        if bool(record.get("maker")) and executed_qty <= 0:
            arm_maker_ttl(entry_client_id, symbol, order_id)   # V6.2: مهلة الصانع
        await save_state()
        _otxt = "LIMIT_MAKER(صانع)" if record.get("maker") else "MARKET"
        log(f"أمر دخول {_otxt} {symbol} @ {fmt_price(symbol, price)} (cid={entry_client_id}) "
            f"— بانتظار executionReport")
        return True
    except BinanceError as exc:
        if exc.code == -2010 and bool(MAKER_ENTRIES):
            FUNNEL["maker-reject"] += 1   # كتاب مقفول: أمر الصانع كان سيعبر السبريد
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


def arm_maker_ttl(client_id, symbol, order_id):
    """V6.2: يسلّح مهلة أمر الصانع — لو لم يُنفَّذ خلال MAKER_TTL_SEC يُلغى تلقائياً."""
    try:
        asyncio.get_running_loop().create_task(
            maker_ttl_watchdog(client_id, symbol, order_id))
    except RuntimeError:
        pass


async def maker_ttl_watchdog(client_id, symbol, order_id):
    """أمر الصانع الذي لم يُنفَّذ خلال المهلة = الزخم فات ⇒ إلغاء وتحرير الحجز.

    يجب أن تبقى MAKER_TTL_SEC أصغر من ENTRY_EVENT_TIMEOUT (12ث) كي يسبق هذا
    الواتش دوغ العام — القيد مفروض في clamp الثابت. التنفيذ الجزئي قبل
    الإلغاء يحسمه مسار الأحداث المعتاد (complete_entry).
    """
    await asyncio.sleep(MAKER_TTL_SEC)
    rec = STATE.get("pending_entries", {}).get(client_id)
    if rec is None or rec.get("phase") in ("done", "filled"):
        return
    try:
        if order_id:
            await REST.cancel_order(symbol, order_id)
        else:
            await REST.cancel_order_client(symbol, client_id)
        FUNNEL["maker-expired"] += 1
        STATE.setdefault("last_entry_at", {})[symbol] = time.time()  # خنق إعادة النار الفورية
        log(f"صانع {symbol}: انتهت مهلة {MAKER_TTL_SEC:g}ث بلا تنفيذ — أُلغي أمر الصانع")
    except BinanceError as exc:
        log(f"صانع {symbol}: تعذر إلغاء المهلة ({exc}) — الأحداث/الواتش دوغ تحسم")


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
            "atr_ref": float(D(str(record.get("atr", 0.0)))),
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
            # ── V6.1: محاسبة الوعي بالرسوم (PnL صافٍ بعد عمولة Taker للجهتين) ──
            "entry_quote": float(D(str(quote_filled or 0))),
            "fees_entry": round(float(D(str(quote_filled or 0))) * FEE_TAKER_RATE, 8),
            "partial_pnl": 0.0, "fees_partial": 0.0, "scaled": False,
            "score": float(record.get("score", 0) or 0),
            "trigger": str(record.get("trigger", "flash-crash") or "flash-crash"),
            "drop_pct": float(record.get("drop_pct", 0.0) or 0.0),
            "wall_ratio": float(record.get("wall_ratio", 0.0) or 0.0),
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
        log(f"دخول V6.0 {symbol} pid={pid} entry={fmt_price(symbol, avg_price)} qty={position['qty']} "
            f"hardSL={fmt_price(symbol, protection['stop'])} ({risk['sl_pct']:.2f}%) "
            f"protection={protection['type']} trigger={position['trigger']} "
            f"drop={position['drop_pct']:.2f}% wall={position['wall_ratio']:.2f}x "
            f"VR={position['vr']:.2f} risk={position['risk_usd']:.2f}$ "
            f"(خروج هجين: تعادل +{get_be_trigger_pct():g}% ثم تتبّع {TRAIL_WIDE_PCT:g}/{TRAIL_TIGHT_PCT:g}%)")
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
    """محاسبة صفقة إنقاذ (شراء+بيع مباشر دون مركز مُدار) — صافية بعد الرسوم (V6.1)."""
    try:
        gross = float(exit_quote) - float(entry_quote)
        fees = (float(entry_quote) + float(exit_quote)) * FEE_TAKER_RATE
        pnl = gross - fees
        async with STATE_LOCK:
            metrics = STATE["metrics"]
            metrics["trades"] += 1
            metrics["realized_pnl"] += pnl
            STATE["fees_paid"] = float(STATE.get("fees_paid", 0.0) or 0.0) + fees
            if pnl >= 0:
                metrics["wins"] += 1
                metrics["consecutive_losses"] = 0
            else:
                metrics["losses"] += 1
                metrics["consecutive_losses"] = int(metrics.get("consecutive_losses", 0)) + 1
            governor_update(pnl)
            STATE["cooldowns"][symbol] = time.time()
            trade_log = STATE.get("trade_log")
            if isinstance(trade_log, list):
                trade_log.append({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "symbol": symbol, "pid": "salvage",
                    "pnl": round(pnl, 8), "duration_sec": 0.0,
                    "reason": str(reason), "entry": float(entry_quote), "exit": float(exit_quote),
                    "trigger": "salvage", "fees": round(fees, 8),
                })
                if len(trade_log) > 120:
                    del trade_log[:-100]
        record_trade([datetime.now(timezone.utc).isoformat(), symbol, "salvage",
                      float(entry_quote), float(exit_quote), float(exit_qty), round(pnl, 8), reason, BINANCE_ENV])
        await save_state()
        log(f"بيع إنقاذ {symbol}: pnl={pnl:+.6f}$ (رسوم {fees:.6f}$) reason={reason}")
    except Exception as exc:
        log(f"خطأ محاسبة الإنقاذ {symbol}: {exc}")


async def finalize_position_event(pid, position, exit_price, exit_qty, reason):
    """إغلاق مركز من حدث executionReport (تنفيذ OCO) — بلا أي REST.

    V6.1: PnL صافٍ = (فرق سعر الخروج المتبقي + أرباح البيع الجزئي) − كل
    العمولات (دخول + جزئيات + خروج). تصنيف win/loss على الصافي — لا «فوز
    صافيه سالب» بعد اليوم.
    """
    entry = float(position.get("entry", 0))
    qty = float(position.get("qty", 0))
    exit_price_value = float(exit_price)
    exit_qty_used = min(qty, float(exit_qty) if exit_qty else qty)
    gross = (exit_price_value - entry) * exit_qty_used
    partial_pnl = float(position.get("partial_pnl", 0.0) or 0.0)
    fees_entry = float(position.get("fees_entry", 0.0) or 0.0)
    if fees_entry <= 0:      # مراكز أقدم من V6.1: قدّر عمولة الدخول
        entry_quote_est = float(position.get("entry_quote", 0) or 0) or entry * (
            float(position.get("quote_qty", 0) or 0) or qty)
        fees_entry = entry_quote_est * FEE_TAKER_RATE
    fees_partial = float(position.get("fees_partial", 0.0) or 0.0)
    fees_exit = exit_price_value * exit_qty_used * FEE_TAKER_RATE
    fees_total = fees_entry + fees_partial + fees_exit
    pnl = gross + partial_pnl - fees_total
    symbol = position.get("symbol", "")
    async with STATE_LOCK:
        if STATE["positions"].get(pid) is None:
            return  # حُسم مسبقاً (حدث مكرر/سباق) — منع الإغلاق المزدوج
        STATE["positions"].pop(pid, None)
        EXIT_CLAIMED.discard(pid)   # أُغلق فعلاً → حرّر مطالبة الخروج إن وُجدت
        EXIT_PENDING.discard(pid)   # V5.3: تحرير حارس مهمة التتبّع (لا تسرّب)
        FLOW_REV_AT.pop(pid, None)  # V6.2.1: تحرير خنق انعكاس التدفق (لا تسرّب ذاكرة)
        metrics = STATE["metrics"]
        metrics["realized_pnl"] += pnl
        STATE["fees_paid"] = float(STATE.get("fees_paid", 0.0) or 0.0) + fees_total
        if pnl >= 0:
            metrics["wins"] += 1
            metrics["consecutive_losses"] = 0
        else:
            metrics["losses"] += 1
            metrics["consecutive_losses"] = int(metrics.get("consecutive_losses", 0)) + 1
        governor_update(pnl)
        STATE["cooldowns"][symbol] = time.time()
        try:
            opened = float(position.get("opened_at", 0) or 0)
            duration = max(0.0, time.time() - opened) if opened > 0 else 0.0
        except (TypeError, ValueError):
            duration = 0.0
        trade_log = STATE.get("trade_log")
        if isinstance(trade_log, list):
            trade_log.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol, "pid": pid,
                "pnl": round(pnl, 8), "duration_sec": round(duration, 1),
                "reason": str(reason), "entry": float(entry), "exit": float(exit_price_value),
                "trigger": str(position.get("trigger", "") or ""),
                "fees": round(fees_total, 8),
                "partial": round(partial_pnl, 8),
            })
            if len(trade_log) > 120:            # سقف صلب: آخر 100 صفقة فقط (لا تسرّب ذاكرة)
                del trade_log[:-100]
        for leg_id in position.get("order_ids", []):
            ORDERS.pop(str(leg_id), None)
    record_trade([datetime.now(timezone.utc).isoformat(), symbol, pid, entry, exit_price_value, qty,
                  round(pnl, 8), reason, BINANCE_ENV])
    await save_state()
    log(f"إغلاق {pid}: exit={fmt_price(symbol, exit_price_value)} pnl={pnl:+.6f}$ "
        f"(رسوم {fees_total:.6f}$) reason={reason}")


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
        order_budget_take(2, force=True)    # إلغاء + بيع — الخروج لا ينتظر الميزانية أبداً
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


def trades_last_hour():
    """عدد الصفقات المغلقة خلال آخر 60 دقيقة (من trade_log) — مقياس الإنتاجية."""
    now = time.time()
    count = 0
    for row in (STATE.get("trade_log") or []):
        try:
            ts = datetime.fromisoformat(str(row.get("ts", ""))).timestamp()
        except (TypeError, ValueError):
            continue
        if now - ts <= 3600.0:
            count += 1
    return count


def productivity_text():
    """V6.1: لوحة الإنتاجية والحاكم — البيئة، صفقات/ساعة، الصافي/صفقة، الرسوم."""
    m = STATE.get("metrics", {})
    trades = int(m.get("trades", 0))
    pnl = float(m.get("realized_pnl", 0.0))
    fees = float(STATE.get("fees_paid", 0.0) or 0.0)
    per_trade = (pnl / trades) if trades > 0 else 0.0
    used, cap = order_budget_usage()
    blocked, why = governor_blocked()
    gov_line = (f"🛑 متوقف: {why}" if blocked else "🟢 يسمح بالدخول")
    if blocked:
        until = float((STATE.get("gov") or {}).get("pause_until", 0.0) or 0.0)
        gov_line += f" ({max(0, int(until - time.time()))}ث متبقية)"
    _sh = STATE.get("shadow", {}) or {}
    _sh_stats = _sh.get("stats") or {}
    _sh_closed = sum(int(s.get("closed", 0) or 0) for s in _sh_stats.values())
    _sh_best = "لا بيانات بعد"
    if _sh_stats:
        _bt, _bv = max(_sh_stats.items(), key=lambda kv: float(kv[1].get("net", 0) or 0))
        _sh_best = f"{_bt} {float(_bv.get('net', 0) or 0):+.3f}$"
    _sh_line = (f"الظلي: {len(_sh.get('open') or {})} مفتوحة | {_sh_closed} مغلقة | "
                f"أفضل زناد: {_sh_best}")
    return (
        f"\n📊 إنتاجية V6.2 ({'⚠️ TESTNET' if BINANCE_ENV != 'live' else '🔴 LIVE'}):\n"
        f"صفقات/ساعة: {trades_last_hour()} | متوسط الصافي/صفقة: {per_trade:+.4f}$ | "
        f"رسوم مقدَّرة: {fees:.4f}$ | بيع جزئي: {int(STATE.get('scale_outs', 0))}\n"
        f"الحاكم: {gov_line} | ميزانية الأوامر: {used}/{cap} لكل {ORDER_BUDGET_WINDOW:.0f}ث\n"
        f"{_sh_line} | الدخول: {'صانع LIMIT_MAKER' if MAKER_ENTRIES else 'سوقي MARKET'}\n"
        f"الرشاش: {'🟢' if SPRAY_ENABLED else '🔴'} (اندفاعة/تدفق/اختراق، عتبة ≥ "
        f"{SPRAY_BASELINE_FLOOR_PCT:g}% تكيفية) | قنّاص: ×{SNIPER_RISK_MULT:g} حجم، "
        f"سقف {SNIPER_MAX_NOTIONAL_USD}$ | رسوم مفترضة: {FEE_TAKER_RATE * 100:g}%/جهة "
        f"(ذهاب-إياب ≈ {FEE_ROUND_TRIP_PCT:.2f}%)\n"
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
        f"⚡ محرك القنّاص اللحظي (HFT — بلا أي شموع إشارة):\n"
        f"  • Micro-Memory: {TICK_MEMORY_SEC:.0f}ث aggTrade | زناد هبوط ≥ {FLASH_DROP_PCT}%\n"
        f"  • جدار الشراء: bid_vol &gt; {BUY_WALL_RATIO:g}× ask_vol خلال {BUY_WALL_MAX_AGE:g}ث\n"
        f"  • إعادة المحاولة كل {SNIPER_RETRY_SEC:g}ث | مهلة انتظار الجدار {SNIPER_PENDING_TTL:g}ث\n"
        f"الحماية: وقف طوارئ صلب ATR(1m)×{HARD_STOP_ATR_MULT:g} بسقف {SL_MAX_PCT}% (بلا هدف ثابت)\n"
        f"الخروج الهجين: تعادل عند +{get_be_trigger_pct():g}% → قفل +{BREAKEVEN_LOCK_PCT:g}% | "
        f"تتبّع {TRAIL_WIDE_PCT:g}% ثم {TRAIL_TIGHT_PCT:g}% فوق +{TRAIL_TIGHT_AFTER_PCT:g}%\n"
        f"وقف زمني ديناميكي (Hit & Run): {get_time_stop_sec()}ث أساس (يتكيف مع VR؛ القنّاص ×{SNIPER_TIMESTOP_MULT:g}) "
        f"بربح &lt; +{TIME_STOP_MIN_PROFIT_PCT:g}% ⇒ تصفية MARKET ({'مفعّل' if TIME_STOP_ENABLED else 'معطّل'})\n"
        f"الحجم: مخاطرة {TARGET_RISK_USD}$ (سقف مركز {MAX_POSITION_NOTIONAL_USD}$، نصف الحجم عند VR&gt;{VR_FAST:g}) "
        f"| مراكز {len(STATE.get('positions', {}))}/{MAX_OPEN_POSITIONS} ({MAX_POSITIONS_PER_SYMBOL}/عملة)\n"
        f"🧠 Gemini: {'🟢 ' + GEMINI_MODEL if gemini_available() else '🔴 معطل'} | "
        f"Auto-Tune كل {GEMINI_TUNE_EVERY // 3600}س | آخر ضبط: {'مسجَّل' if STATE.get('last_tune') else 'لا يوجد'}\n"
        f"حوت: صفقة مفردة ≥ {WHALE_TRADE_USD:,.0f}$ (تلميح تشخيصي في /insight)\n"
        f"تدفق {FLOW_WINDOW_SEC:.0f}ث (aggTrade) | قدم بيانات ≤{MAX_STALE_SEC:.0f}ث | سبريد نمطي×"
        f"{SPREAD_SPRAY_MULT:g} (قنّاص ×{SPREAD_SNIPE_MULT:g}) ≤{SPREAD_ADAPTIVE_CAP}%\n"
        + productivity_text()
        + f"📈 قمع التشخيص (أسباب المنع/الإطلاق منذ التشغيل):\n"
        + "\n".join(f"  • {name_ar}: {count}" for name_ar, count in (
            ("⚡ قنص فلاش كراش", FUNNEL.get("flash-trigger", 0)),
            ("🚀 رشاش: اندفاعة", FUNNEL.get("spray-impulse", 0)),
            ("🚀 رشاش: هيمنة تدفق", FUNNEL.get("spray-flow", 0)),
            ("🚀 رشاش: اختراق", FUNNEL.get("spray-breakout", 0)),
            ("هبوط بلا جدار", FUNNEL.get("no-buywall", 0)),
            ("صيد انتهى بلا تأكيد", FUNNEL.get("snipe-expired", 0)),
            ("أُطلقت (كل المسارات)", FUNNEL.get("fired", 0)),
            ("قاطع BTC", FUNNEL.get("btc-breaker", 0)),
            ("سبريد واسع", FUNNEL.get("spread", 0)),
            ("بيانات قديمة", FUNNEL.get("stale-tick", 0)),
            ("رفض بلا ATR(1m)", FUNNEL.get("no-atr", 0)),
            ("ميزانية أوامر ممتلئة", FUNNEL.get("budget", 0)),
            ("رشاش: بيانات قديمة", FUNNEL.get("spray-stale", 0)),
            ("وقف زمني", FUNNEL.get("time-stop", 0)),
            ("خروج بانعكاس التدفق", FUNNEL.get("flow-rev", 0)),
            ("بيع جزئي (Scale-Out)", FUNNEL.get("scale-out", 0)),
            ("إيقاف حاكم: متتالية", FUNNEL.get("gov-streak", 0)),
            ("إيقاف حاكم: ساعة", FUNNEL.get("gov-hourly", 0)),
            ("إيقاف حاكم: يوم", FUNNEL.get("gov-daily", 0)),
            ("صانع: انتهت المهلة بلا تنفيذ", FUNNEL.get("maker-expired", 0)),
            ("صانع: مرفوض (كتاب مقفول)", FUNNEL.get("maker-reject", 0)),
            ("مختبر صامت SHADOW_ONLY", FUNNEL.get("shadow-only", 0)),
            ("ظلي: خنق 30ث", FUNNEL.get("shadow-throttle", 0)),
            ("حجز: تهدئة", FUNNEL.get("reserve-cooldown", 0)),
            ("حجز: سقوف المراكز", FUNNEL.get("reserve-symbol-cap", 0)
             + FUNNEL.get("reserve-global-cap", 0)),
            ("حجز: الحاكم", FUNNEL.get("reserve-gov", 0)),
            ("إيقاظ حيتان (تلميح)", FUNNEL.get("whale", 0)),
            ("خروج بالتتبّع", FUNNEL.get("trail-exit", 0)),
            ("حد أدنى غير قابل للبيع", FUNNEL.get("min-notional", 0)),
            ("إعادة تركيب وقف", FUNNEL.get("stop-rearmed", 0)),
            ("مركز مكشوف (حرج)", FUNNEL.get("naked-position", 0)),
        ))
    )


HELP_TEXT = (
    "🤖 <b>NOVA V6.2 Hybrid AI-HFT — رشاش + قنّاص + مختبر ظلي</b>\n\n"
    "/start أو /menu القائمة الرئيسية\n/status تقرير الأداء\n/context حالة السياق والإنتاجية\n"
    "/autopsy 🔬 تشريح آخر 5 صفقات خاسرة بالذكاء الاصطناعي\n"
    "/shadow 🔬 لوحة البحث الظلي (أفضلية كل زناد)\n"
    "/insight 🧠 تحليل حالة السوق بالذكاء الاصطناعي\n"
    "/reset تصفير الإحصائيات\n/pause إيقاف الدخولات الجديدة\n/resume استئناف\n"
    "/cancelall إلغاء حمايات البوت\n/panic إلغاء + تصفية فورية\n"
    "/kill قاطع تداول يدوي\n/unkill إزالة القاطع\n/help هذه المساعدة\n\n"
    f"🚀 الرشاش (3 زنادات OR دائمة): اندفاعة صاعدة ≥ عتبة تكيفية ({SPRAY_BASELINE_K:g}× وسيط حركة "
    f"{TICK_MEMORY_SEC:.0f}ث، أرضية {SPRAY_BASELINE_FLOOR_PCT:g}%) + هيمنة تدفق ≥ {SPRAY_FLOW_RATIO:g}x "
    f"+ اختراق قمة {SPRAY_BREAKOUT_BARS} دقيقة — تهدئة {SPRAY_COOLDOWN_SEC:.0f}ث/عملة.\n"
    f"⚡ القنّاص (حجم ×{SNIPER_RISK_MULT:g}): هبوط ≥ {FLASH_DROP_PCT}% خلال {TICK_MEMORY_SEC:.0f}ث على aggTrade "
    f"+ جدار شراء bid_vol > {BUY_WALL_RATIO:g}× ask_vol ⇒ MARKET BUY فوري بسقف {SNIPER_MAX_NOTIONAL_USD}$.\n"
    f"🎯 الخروج الواعي بالرسوم ({FEE_TAKER_RATE * 100:g}%/جهة): تعادل عند +{BREAKEVEN_TRIGGER_PCT:g}% "
    f"يقفل +{BREAKEVEN_LOCK_PCT:g}% (فوق تكلفة التداول {FEE_ROUND_TRIP_PCT:.2f}%) — الصفقة تصبح بلا خسارة ممكنة، "
    f"تتبّع {TRAIL_WIDE_PCT:g}% ثم {TRAIL_TIGHT_PCT:g}% فوق +{TRAIL_TIGHT_AFTER_PCT:g}%، "
    f"بيع جزئي {SCALE_OUT_FRACTION * 100:g}% عند +{SCALE_OUT_AT_PCT:g}%، وخروج فوري عند انعكاس التدفق.\n"
    f"⏱️ وقف زمني ديناميكي: {TIME_STOP_SEC}ث أساس (يتكيف مع التقلب؛ القنّاص ×{SNIPER_TIMESTOP_MULT:g}).\n"
    f"🛡️ شبكة الأمان: وقف طوارئ صلب STOP_LOSS_LIMIT عند ATR(1m)×{HARD_STOP_ATR_MULT:g} بسقف {SL_MAX_PCT}%.\n"
    f"🛑 الحاكم: {GOV_MAX_STREAK} خسائر متتالية ⇒ توقف {GOV_STREAK_PAUSE_SEC // 60}د | "
    f"−{GOV_HOURLY_LOSS_USD}$/ساعة ⇒ {GOV_HOURLY_PAUSE_SEC // 60}د | −{GOV_DAILY_LOSS_USD}$/يوم ⇒ حتى الغد | "
    f"ميزانية {ORDER_BUDGET_MAX} أمر/{ORDER_BUDGET_WINDOW:.0f}ث.\n"
    f"🔬 الوضع الظلي (/shadow): كل زناد يقاس بصفقة افتراضية موحدة {SHADOW_NOTIONAL_USD}$ بنفس "
    f"محرك الخروج الحقيقي — الأرباح تُقيد صافية بعد الرسوم لكل زناد؛ الرابح بعد 50+ صفقة "
    f"يستحق التفعيل الحقيقي. SHADOW_ONLY=1 يجعل البوت مختبراً صامتاً بالكامل.\n"
    f"🏦 دخول الصانع: {'مفعّل — LIMIT_MAKER عند أفضل شراء (تكسب السبريد) بمهلة ' + format(MAKER_TTL_SEC, 'g') + 'ث' if MAKER_ENTRIES else 'معطّل (MARKET)'}\n"
    "🧠 الدماغ: Gemini يضبط BREAKEVEN_TRIGGER_PCT وTIME_STOP_SEC تلقائياً كل 4 ساعات، "
    "ويجيب على /autopsy و/insight بالعربية.\n"
    "⚖️ الحجم: الرشاش مخاطرة 1$ (سقف 12$) | القنّاص ×2.5 (سقف 30$) | نصف الحجم عند VR>1.5.\n"
    "قاطع سياق كلي: BTCUSDT@kline_1m يمنع الشراء إذا هوى BTC ≥ 0.5% خلال 3 دقائق.\n"
    "User Data Stream (executionReport) مصدر حقيقة الأوامر — بلا REST Polling.\n"
    "الصمت التام: رسالة بدء واحدة ثم الرد على الأوامر اليدوية فقط."
)


# ══════════════════════════════════════════════════════════════════════════════
# 10.5) Gemini AI Brain — العقل المستقل (Auto-Tune) + المستشار التفاعلي
# ══════════════════════════════════════════════════════════════════════════════
# كل استدعاءات Gemini تُنفَّذ عبر asyncio.to_thread + wait_for — لا يُحجب حلق
# الأحداث إطلاقاً، وحلقات WebSocket تبقى على ازدواج كامل السرعة.


def gemini_configure():
    """تهيئة google.generativeai بمفتاح GEMINI_API_KEY (متسامح: تعطل آمن)."""
    global GEMINI_READY
    if genai is None:
        log("Gemini: مكتبة google-generativeai غير مثبتة (pip install google-generativeai) — الدماغ معطل")
        return False
    if not GEMINI_API_KEY:
        log("Gemini: GEMINI_API_KEY غير مضبوط — الدماغ الذكي معطل (القنّاص يعمل بدونه)")
        return False
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_READY = True
        log(f"Gemini AI جاهز (النموذج: {GEMINI_MODEL})")
        return True
    except Exception as exc:
        log(f"Gemini: فشل التهيئة ({exc}) — الدماغ معطل")
        return False


def gemini_available():
    return bool(GEMINI_READY and genai is not None and GEMINI_API_KEY)


def _gemini_generate_sync(prompt, json_mode=False):
    """استدعاء متزامن — يُنفَّذ دائماً داخل خيط عامل عبر asyncio.to_thread."""
    config = None
    if json_mode:      # إجبار JSON على النسخ الحديثة من SDK، مع رجوع آمن
        try:
            config = genai.GenerationConfig(response_mime_type="application/json", temperature=0.2)
        except Exception:
            config = genai.GenerationConfig(temperature=0.2)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt, generation_config=config)
    return (getattr(response, "text", None) or "").strip()


async def gemini_ask(prompt, json_mode=False, timeout=None):
    """غلاف غير حاجب لـ Gemini: to_thread + wait_for ⇒ حلقات WS لا تتوقف أبداً.

    يعيد (نص, خطأ) — النص None عند الفشل مع سبب واضح في err.
    """
    if not gemini_available():
        return None, "gemini-unavailable"
    timeout = GEMINI_TIMEOUT if timeout is None else float(timeout)

    def _call():
        return _gemini_generate_sync(prompt, json_mode)

    try:
        text = await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout)
        if not text:
            return None, "empty-response"
        return text, None
    except asyncio.TimeoutError:
        return None, f"timeout>{timeout:.0f}s"
    except Exception as exc:
        return None, str(exc)[:200]


def parse_json_loose(text):
    """يستخرج JSON من رد Gemini حتى لو مُحيط بنص أو أسوار كود (نقي وقابل للاختبار)."""
    if not text:
        return None
    raw = str(text).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except ValueError:
        pass
    match = re.search(r"\{.*\}", raw, re.S)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except ValueError:
            return None
    return None


# حدود صلبة لاقتراحات Gemini — الذكاء يقترح، والهندسة تُصادق (V6.1: لا قفل تحت الرسوم)
TUNE_BE_MIN, TUNE_BE_MAX = 0.25, 1.20
TUNE_TS_MIN, TUNE_TS_MAX = 30, 240


def clamp_tuned_params(parsed):
    """يقيد مخرجات Gemini داخل حدود آمنة صلبة. None = رد مرفوض."""
    if not isinstance(parsed, dict):
        return None
    result = {}
    try:
        result["breakeven_trigger_pct"] = round(
            clamp(float(parsed.get("breakeven_trigger_pct")), TUNE_BE_MIN, TUNE_BE_MAX), 3)
    except (TypeError, ValueError):
        return None
    try:
        result["time_stop_sec"] = int(
            clamp(int(round(float(parsed.get("time_stop_sec")))), TUNE_TS_MIN, TUNE_TS_MAX))
    except (TypeError, ValueError):
        return None
    result["reason"] = str(parsed.get("reason", "") or "")[:280]
    return result


def funnel_snapshot():
    return {key: int(value) for key, value in dict(FUNNEL).items()}


async def build_tune_prompt():
    """يجمّع FUNNEL + Win/Loss + تقلب BTC_CTX + المعاملات الحالية في برومبت JSON."""
    async with STATE_LOCK:
        metrics = dict(STATE.get("metrics", {}) or {})
        be_now = get_be_trigger_pct()
        ts_now = get_time_stop_sec()
    funnel = funnel_snapshot()
    btc = btc_ctx_stats()
    drop_text = "—" if btc["drop_pct"] is None else f"{btc['drop_pct']:+.2f}%"
    return (
        "أنت محرك تحسين كمي (Quant Auto-Tuner) لبوت سكالبينج HFT على Binance Spot. "
        "يصطاد البوت الانهيارات المفاجئة (هبوط ≥ 1.2% خلال 15 ثانية مع جدار شراء لحظي) ويخرج Hit & Run خلال ثوانٍ.\n"
        f"مقاييس Win/Loss: {json.dumps(metrics, ensure_ascii=False)}\n"
        f"عدّادات قمع التشخيص FUNNEL: {json.dumps(funnel, ensure_ascii=False)}\n"
        f"تقلب BTC_CTX: VR={btc['vr']:.2f} | تغير 3 دقائق={drop_text} | عمر المصدر={btc['age']:.0f}ث\n"
        f"المعاملات الحالية: BREAKEVEN_TRIGGER_PCT={be_now:.2f}% | TIME_STOP_SEC={ts_now}ث\n\n"
        "المطلوب: اقترح قيماً محسّنة للمعاملين بحسب الأداء الأخير "
        "(نسبة نجاح منخفضة ⇒ شدّد الفلترة؛ خروج زمني كثير ⇒ مدّد المهلة قليلاً؛ "
        "أرباح صغيرة تتلاشى ⇒ خفّض عتبة التفعيل مع بقائها فوق تكلفة الرسوم 0.25%). "
        "أعد JSON فقط بهذا الشكل بالضبط: "
        '{"breakeven_trigger_pct": <رقم بين 0.25 و1.20>, '
        '"time_stop_sec": <عدد صحيح بين 30 و240>, '
        '"reason": "<سبب عربي في جملة واحدة>"}'
    )


async def gemini_autotune_once():
    """دورة ضبط واحدة: بيانات → Gemini (JSON مفروض) → تحقّق → STATE + حفظ + إشعار."""
    prompt = await build_tune_prompt()
    text, err = await gemini_ask(prompt, json_mode=True)
    if err:
        log(f"Auto-Tune: تعذرت استشارة Gemini ({err})")
        return False
    tuned = clamp_tuned_params(parse_json_loose(text))
    if tuned is None:
        log(f"Auto-Tune: رد Gemini ليس JSON صالحاً: {str(text)[:160]}")
        return False
    async with STATE_LOCK:
        STATE["be_trigger_pct"] = tuned["breakeven_trigger_pct"]
        STATE["time_stop_sec"] = tuned["time_stop_sec"]
        STATE["last_tune"] = {"ts": time.time(), **tuned}
    await save_state()     # يُكتب في state.json فوراً (كتابة ذرية عبر to_thread)
    log(f"Auto-Tune: BREAKEVEN_TRIGGER_PCT={tuned['breakeven_trigger_pct']}% "
        f"TIME_STOP_SEC={tuned['time_stop_sec']}ث — السبب: {tuned['reason']}")
    await send_message(
        "🧠 <b>NOVA Auto-Tune (Gemini)</b>\n"
        f"BREAKEVEN_TRIGGER_PCT → {tuned['breakeven_trigger_pct']:.2f}%\n"
        f"TIME_STOP_SEC → {tuned['time_stop_sec']}ث\n"
        f"السبب: {tuned['reason']}",
        chat_id=TELEGRAM_CHAT_ID)
    return True


async def gemini_autotune_loop():
    """حلقة Auto-Tune كل 4 ساعات (غير حاجبة — Gemini يعمل في خيط منفصل)."""
    if not gemini_available():
        log(f"Auto-Tune: معطل حالياً — الحلقة ستفحص كل {GEMINI_TUNE_EVERY // 3600} ساعات")
    while True:
        await asyncio.sleep(GEMINI_TUNE_EVERY)
        try:
            if gemini_available():
                await gemini_autotune_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ حلقة Auto-Tune: {exc}")


# ── AI Commander: التشريح (/autopsy) وتحليل السوق (/insight) ─────────────────

AUTOPSY_TRADES = 5


def collect_losing_trades(limit=AUTOPSY_TRADES):
    """آخر N صفقات خاسرة من ذاكرة STATE (pnl < 0)."""
    rows = []
    for row in (STATE.get("trade_log") or []):
        try:
            if float(row.get("pnl", 0) or 0) < 0:
                rows.append(row)
        except (TypeError, ValueError):
            continue
    return rows[-limit:]


def describe_trade_row(row):
    """سطر عربي موجز لصفقة: الرمز + PnL + المدة + سبب الخروج."""
    minutes = float(row.get("duration_sec", 0) or 0) / 60.0
    return (f"- الرمز: {row.get('symbol', '?')} | PnL: {float(row.get('pnl', 0) or 0):+.4f}$ | "
            f"مدة الصفقة: {minutes:.1f} دقيقة | سبب الخروج: {row.get('reason', '?')} | "
            f"دخول {row.get('entry', '?')} → خروج {row.get('exit', '?')} | الزناد: {row.get('trigger', 'flash-crash')}")


async def build_autopsy_prompt():
    """آخر 5 خسائر من STATE → برومبت تشخيص كمي من 3 جمل بالعربية."""
    async with STATE_LOCK:
        losers = [dict(row) for row in collect_losing_trades()]
        total_losses = int((STATE.get("metrics", {}) or {}).get("losses", 0))
    if not losers:
        return None, None
    lines = "\n".join(describe_trade_row(row) for row in losers)
    avg = sum(float(row.get("pnl", 0) or 0) for row in losers) / len(losers)
    fallback = (f"متوسط الخسارة {avg:+.4f}$ على آخر {len(losers)} صفقات خاسرة "
                f"(إجمالي الخسائر المسجلة: {total_losses}) — راجع /context لمعرفة الخانق.")
    prompt = (
        "أنت مستشار تداول كمي (Quant Advisor). هذه آخر 5 صفقات خاسرة لبوت قنص الانهيارات اللحظية:\n"
        f"{lines}\n\n"
        "شخّص الأسباب الكمية للفشل (التوقيت، جودة جدار الشراء، سقف الوقت، عمق الانهيار) "
        "في 3 جمل عربية بالضبط — بلا مقدمات ولا تعداد نقطي ولا نصائح عامة."
    )
    return prompt, fallback


async def autopsy_report():
    prompt, fallback = await build_autopsy_prompt()
    if prompt is None:
        return "🔬 لا توجد صفقات خاسرة مسجّلة بعد — لا شيء لتشريحه. الصيد مستمر."
    text, err = await gemini_ask(prompt)
    if err or not text:
        log(f"/autopsy: Gemini غير متاح ({err}) — تشخيص محلي")
        return "🔬 <b>تشريح محلي</b> (Gemini غير متاح): " + fallback
    return "🔬 <b>تشريح الصفقات (Gemini)</b>\n" + escape(text.strip())


async def build_insight_prompt():
    """عدّادات FUNNEL + تقلب BTC + ملخص الأداء → برومبت تحليل سوق من 3 جمل."""
    async with STATE_LOCK:
        positions = len(STATE.get("positions", {}) or {})
        metrics = dict(STATE.get("metrics", {}) or {})
    funnel = funnel_snapshot()
    btc = btc_ctx_stats()
    drop_text = "—" if btc["drop_pct"] is None else f"{btc['drop_pct']:+.2f}%"
    return (
        "أنت محلل أسواق كريبتو لحظي. حالة بوت قنّاص الانهيارات الآن:\n"
        f"عدّادات FUNNEL (أسباب الرفض/الإطلاق): {json.dumps(funnel, ensure_ascii=False)}\n"
        f"تقلب BTC (VR على 1m): {btc['vr']:.2f} | تغير BTC في 3 دقائق: {drop_text} | عمر المصدر: {btc['age']:.0f}ث\n"
        f"مراكز مفتوحة: {positions} | صفقات: {metrics.get('trades', 0)} | "
        f"رابحة: {metrics.get('wins', 0)} | خاسرة: {metrics.get('losses', 0)}\n\n"
        "قدّم تحليلاً لحالة السوق الحالية (انفجار تقلب؟ هدوء قاتل؟ رياح كلية معاكسة؟) "
        "في 3 جمل عربية بالضبط — بلا مقدمات ولا تعداد نقطي."
    )


async def insight_report():
    prompt = await build_insight_prompt()
    text, err = await gemini_ask(prompt)
    if err or not text:
        btc = btc_ctx_stats()
        drop_text = "—" if btc["drop_pct"] is None else f"{btc['drop_pct']:+.2f}%"
        return (f"🧠 <b>تحليل محلي</b> (Gemini غير متاح): تقلب BTC VR={btc['vr']:.2f} "
                f"وتغير 3 دقائق {drop_text} — أعِد المحاولة لاحقاً لتحليل الذكاء الاصطناعي.")
    return "🧠 <b>تحليل السوق (Gemini)</b>\n" + escape(text.strip())


AI_TASKS = set()          # مراجع حيّة لمهام ردود Gemini (منع التقديم المهمل)
AI_REPLY_COOLDOWN = 10.0  # خنق أوامر الذكاء: منع استنزاف حصة Gemini بالتكرار
LAST_AI_REPLY_AT = {}


def spawn_ai_task(coro):
    """يشغّل مهمة رد Gemini مع الإمساك بمرجع حيّ (توصية توثيق asyncio)."""
    try:
        task = asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        return None
    AI_TASKS.add(task)
    task.add_done_callback(AI_TASKS.discard)
    return task


def ai_throttled(kind):
    """True إذا تكرر أمر الذكاء نفسه بسرعة أكبر من AI_REPLY_COOLDOWN."""
    now = time.monotonic()
    if now - float(LAST_AI_REPLY_AT.get(kind, 0.0)) < AI_REPLY_COOLDOWN:
        return True
    LAST_AI_REPLY_AT[kind] = now
    return False


async def autopsy_reply(chat):
    """يرد على مستخدم Telegram بالتشريح (خارج مسار WebSocket تماماً)."""
    if ai_throttled("autopsy"):
        await send_message("⏳ طلب تشريح متكرر بسرعة — انتظر ثوانٍ ثم أعد المحاولة.", main_keyboard(), chat)
        return
    try:
        text = await autopsy_report()
    except Exception as exc:
        text = f"تعذر التشريح: {exc}"
    await send_message(text, main_keyboard(), chat)


async def insight_reply(chat):
    if ai_throttled("insight"):
        await send_message("⏳ طلب تحليل متكرر بسرعة — انتظر ثوانٍ ثم أعد المحاولة.", main_keyboard(), chat)
        return
    try:
        text = await insight_report()
    except Exception as exc:
        text = f"تعذر التحليل: {exc}"
    await send_message(text, main_keyboard(), chat)


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
        [button("🔬 تشريح الصفقات", "/autopsy"), button("🧠 تحليل السوق", "/insight")],
        [button("⏸ إيقاف", "/pause"), button("▶ استئناف", "/resume")],
        [button("🧯 إلغاء الأوامر", "/cancelall"), button("🆘 تصفية", "/panic")],
        [button("🔬 الوضع الظلي", "/shadow"), button("❓ المساعدة", "/help")],
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
    elif data in ("shadow", "الظلي"):
        # V6.2: لوحة البحث الظلي — أفضلية كل زناد صافية بعد الرسوم
        await send_message(shadow_report_text(), main_keyboard(), chat)
    elif data in ("autopsy", "تشريح"):
        # V6.0: Gemini يعمل في خيط منفصل — الرد يُرسل عند جاهزيته (لا حجب للحلقة)
        await send_message("🔬 جارٍ تشريح آخر 5 صفقات خاسرة عبر Gemini…", main_keyboard(), chat)
        spawn_ai_task(autopsy_reply(chat))
    elif data in ("insight", "تحليل"):
        await send_message("🧠 جارٍ تحليل حالة السوق عبر Gemini…", main_keyboard(), chat)
        spawn_ai_task(insight_reply(chat))
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
        await send_message("🎛️ <b>NOVA V6.2 Hybrid AI-HFT</b>\nاختر عملية:", main_keyboard(), chat)
    elif command == "/help":
        await send_message(HELP_TEXT, main_keyboard(), chat)
    elif command == "/status":
        await send_message(status_text(), main_keyboard(), chat)
    elif command in ("/context", "/btc"):
        await send_message(context_text(), main_keyboard(), chat)
    elif command == "/shadow":
        await send_message(shadow_report_text(), main_keyboard(), chat)
    elif command == "/autopsy":
        await send_message("🔬 جارٍ تشريح آخر 5 صفقات خاسرة عبر Gemini…", main_keyboard(), chat)
        spawn_ai_task(autopsy_reply(chat))
    elif command == "/insight":
        await send_message("🧠 جارٍ تحليل حالة السوق عبر Gemini…", main_keyboard(), chat)
        spawn_ai_task(insight_reply(chat))
    elif command == "/reset":
        async with STATE_LOCK:
            STATE["metrics"] = {
                "trades": 0,
                "realized_pnl": 0.0,
                "wins": 0,
                "losses": 0,
                "consecutive_losses": 0,
            }
            STATE["fees_paid"] = 0.0
            STATE["scale_outs"] = 0
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
        # V6.0: kline_1m للذاكرة الحسابية فقط (ATR) + التدفقان الحدثيان للقنّاص
        s = str(symbol).lower()
        return (f"{s}@kline_{MICRO_INTERVAL}", f"{s}@aggTrade", f"{s}@bookTicker")

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
                    TICKS.pop(symbol, None)
                    PENDING_SNIPES.pop(symbol, None)
                    HFT_ATTEMPT.pop(symbol, None)
                    WHALES.pop(symbol, None)
                    SPRAY_BASE.pop(symbol, None)       # V6.2.1: لا تراكم ذاكرة مع دوران الكون
                    SPRAY_ATTEMPT.pop(symbol, None)
                    SPREAD_MEM.pop(symbol, None)
                    SHADOW_THROTTLE.pop(symbol, None)
                    SHADOW_ATTEMPT.pop(symbol, None)
                    if symbol in held:
                        continue      # مركز مفتوح → أبقِ بياناته حتى يُغلق
                    BOOK.pop(symbol, None)
                    FLOW.pop(symbol, None)
                    CANDLES.pop((symbol, MICRO_INTERVAL), None)
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
            # V6.0: صيد معلّق تجاوز مهلة انتظار الجدار → يُعتبر منتهياً
            now_mono = time.monotonic()
            for _sniper_sym in [s for s, t in PENDING_SNIPES.items()
                                if now_mono - float(t) > SNIPER_PENDING_TTL]:
                PENDING_SNIPES.pop(_sniper_sym, None)
                FUNNEL["snipe-expired"] += 1
            # سدّة أمان: أعد تقييم التتبّع من آخر سعر معروف (لو صمتت bookTicker)
            for _pid, _pos in list((STATE.get("positions") or {}).items()):
                _sym = _pos.get("symbol", "")
                _px, _ = market_price(_sym)
                if _px > 0:
                    on_price_update(_sym, _px)
            # V6.2: نفس السدّة للمراكز الظلية (وقف زمني/صلب لو صمت التدفق)
            if SHADOW_ENABLED and SHADOW_SYMS:
                for _ssym in list(SHADOW_SYMS):
                    _spx, _ = market_price(_ssym)
                    if _spx > 0:
                        shadow_on_price(_ssym, _spx)
            stale = {cid: rec for cid, rec in STATE.get("pending_entries", {}).items()
                     if time.time() - float(rec.get("placed_at", 0)) > 120}
            if stale:
                await reconcile_snapshot("معلقات قديمة")
            if STATE.get("positions") or ((STATE.get("shadow") or {}).get("open") or {}):
                await save_state()    # تثبيت القمم/التتبّع/المراكز الظلية دورياً (نجاة من تعطل مفاجئ)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log(f"خطأ حلقة الصيانة: {exc}")


async def time_stop_loop():
    """وقف زمني دقيق (V6.0 — Hit & Run): سكالب بلا زخم خلال ~45 ثانية يُصفى بسعر السوق.

    الاندفاعة اللحظية إما تكمل فوراً أو لا تكمل أبداً: مركز يتجاوز
    TIME_STOP_SEC (من STATE — قابل للضبط الآلي بواسطة Gemini) بلا ربح
    مقبول (≥ TIME_STOP_MIN_PROFIT_PCT) ⇒ إلغاء وقف الطوارئ على Binance
    وMARKET SELL لتحرير رأس المال للقنصة التالية.
    """
    while True:
        await asyncio.sleep(TIME_STOP_CHECK_EVERY)
        if not TIME_STOP_ENABLED or DRY_RUN or not live_execution_allowed():
            continue
        try:
            stop_sec = get_time_stop_sec()
            async with STATE_LOCK:
                open_positions = [(pid, dict(pos)) for pid, pos in STATE.get("positions", {}).items()]
            now = time.time()
            vr_now = float(btc_ctx_stats().get("vr", 1.0) or 1.0)
            for pid, position in open_positions:
                opened = float(position.get("opened_at", 0) or 0)
                trigger = str(position.get("trigger", "") or "")
                # V6.1: مهلة ديناميكية — سوق بطيء تُمدَّد وسريع تُقصَّر؛ القنّاص يتنفّس ×3
                if trigger == "flash-crash":
                    effective = stop_sec * max(1.0, SNIPER_TIMESTOP_MULT)
                elif vr_now < VR_SLOW:
                    effective = stop_sec * 1.5
                elif vr_now > VR_FAST:
                    effective = stop_sec * 0.75
                else:
                    effective = stop_sec
                if opened <= 0 or now - opened < effective:
                    continue
                symbol = position.get("symbol", "")
                # لا تبيع على سعر قديم (انقطاع تدفق) — أنتظر دورة الحلقة القادمة
                if data_age(symbol) > max(MAX_STALE_SEC * 4, 30.0):
                    continue
                price, _age = market_price(symbol)
                if price <= 0:
                    continue
                entry = float(position.get("entry", 0) or 0)
                gain_pct = (price - entry) / entry * 100.0 if entry > 0 else 0.0
                # نُصفّي فقط إذا لم يكن الربح مقبولاً (الرابح يُترك لمحرك التتبّع).
                # القنّاص: المهلة الطويلة تصفّي الخاسر فقط (الربح أي عليه تتبّع).
                min_profit = 0.0 if trigger == "flash-crash" else TIME_STOP_MIN_PROFIT_PCT
                if gain_pct >= min_profit:
                    continue
                if pid in EXIT_PENDING or pid in EXIT_CLAIMED:
                    continue      # مهمة خروج جارية بالفعل → لا بيع مزدوج
                FUNNEL["time-stop"] += 1
                log(f"وقف زمني {pid}: عمر {now - opened:.0f}ث (سقف {effective:.0f}ث) "
                    f"ربح {gain_pct:+.2f}% → تصفية MARKET")
                await force_exit_position(pid, position, f"وقف زمني ({effective:.0f}ث بلا زخم)")
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
    """وضع --once: قنّص لحظي عبر بذر REST (aggTrades) ثم تقييم حدثي واحد."""
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
            decision = sniper_decision(symbol)
            if decision is None or decision.get("action") != "fire":
                continue
            signal = build_sniper_signal(symbol, decision["drop_pct"], decision["wall_ratio"])
            if signal is None or signal["setup_id"] in SETUPS:
                continue
            FUNNEL["flash-trigger"] += 1
            if await process_signal(signal):
                fired += 1
            else:
                log(f"تخطي {symbol}: drop={decision['drop_pct']:.2f}% veto={veto_reason(symbol, signal)}")
        except BinanceError as exc:
            log(f"فحص {symbol}: {exc}")
    log(f"الفحص الفوري: {fired} قنصة منفذة")


async def prime_flow_from_rest(symbol, limit=100):
    """يبذّر نافذة التدفق من aggTrades (REST) — يكفي وضع --once/إعادة الاتصال."""
    rows = await REST.agg_trades(symbol, limit)
    parsed_rows = []
    for row in rows if isinstance(rows, list) else []:
        # مخطط aggTrades الرسمي: [a, p, q, f, l, T, m, M] — كل صف = صفقة واحدة
        try:
            price = float(row[1])
            quantity = float(row[2])
            ts = float(row[5]) / 1000.0          # T: طابع الخادم (ms) — وليس عدّاد صفقات
            is_buyer_maker = bool(row[6])        # m: اتجاه الصفقة — وليس الطابع الزمني
        except (IndexError, TypeError, ValueError):
            continue
        if price <= 0 or quantity <= 0:
            continue
        parsed_rows.append((ts, price, quantity, is_buyer_maker))
    parsed_rows.sort(key=lambda item: item[0])   # نافذة القمة تتطلب ترتيباً زمنياً صحيحاً
    buy_quote = sell_quote = 0.0
    last_ts = time.time()
    price = 0.0
    for ts, price, quantity, is_buyer_maker in parsed_rows:
        quote = price * quantity
        if is_buyer_maker:
            sell_quote += quote
        else:
            buy_quote += quote
        tick_add(symbol, ts, price)              # بذر Micro-Memory (15ث) للقنّاص
        last_ts = ts
    if buy_quote + sell_quote <= 0:
        return False
    state = flow_add(symbol, last_ts, buy_quote, sell_quote)
    state["price"] = price or float((BOOK.get(symbol) or {}).get("ask") or 0)
    state["epoch"] = time.time()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# 13) الاختبار الذاتي (بلا شبكة إطلاقاً)
# ══════════════════════════════════════════════════════════════════════════════


def _synthetic_rows(interval="1m", wick=False):
    """صفوف klines تركيبية (1m): ذاكرة ATR للحماية فقط — لا إشارات من الشموع في V6."""
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
        out[i] = current
    return out


async def run_selftest():
    global STATE, STARTUP_NOTIFIED, ENTRY_RESERVATIONS, RESERVED_QUOTE
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN, BTC_CTX
    print("NOVA V6.2 Hybrid SELFTEST — Spray+Sniper / Fee-Aware Exits / Governor")
    results = []

    def check(name, condition):
        results.append(bool(condition))
        print(("✅ " if condition else "❌ ") + name)

    ensure_dirs()
    try:
        os.remove(KILL_SWITCH_FILE)
    except OSError:
        pass

    # 1) ATR متجهي (Wilder) يطابق المرجع الكلاسيكي حرفياً
    closes = [100.0 + (i % 13) * 0.5 for i in range(260)]
    highs = [100.0 + (i % 7) for i in range(120)]
    lows = [99.0 + (i % 5) for i in range(120)]
    atr_ours = atr_series(highs, lows, closes[:120], ATR_PERIOD)
    atr_ref = _reference_wilder_atr(highs, lows, closes[:120], ATR_PERIOD)
    compared = [i for i in range(len(atr_ref)) if atr_ref[i] is not None]
    atr_err = max(abs(float(atr_ours[i]) - atr_ref[i]) for i in compared)
    check(f"ATR(numpy+pandas) يطابق مرجع Wilder في كل {len(compared)} قيمة",
          len(compared) == 120 - ATR_PERIOD + 1 and atr_err < 1e-9)
    n = 200
    flat_atr, flat_vr = volatility_ratio([101.0] * n, [99.0] * n, [100.0] * n, ATR_PERIOD, VR_BASELINE)
    check("VR = 1.0 في سوق ثابت", abs(flat_atr - 2.0) < 1e-9 and abs(flat_vr - 1.0) < 1e-9)
    spike_h = [101.0] * (n - 4) + [140.0, 141.0, 142.0, 143.0]
    spike_l = [99.0] * (n - 4) + [99.5, 99.5, 99.5, 99.5]
    spike_c = [100.0] * (n - 4) + [130.0, 135.0, 138.0, 142.0]
    _atr_spike, vr_spike = volatility_ratio(spike_h, spike_l, spike_c, ATR_PERIOD, VR_BASELINE)
    check("VR = ATR14/متوسط 20 (نظام fast عند الانفجار)",
          vr_spike > VR_FAST and atr_multiplier(vr_spike) == (ATR_MULT_FAST, "fast"))

    # 2) بناء المخزن من REST + إلحاق/تكرار/فجوة على 1m (ذاكرة حسابية فقط)
    buffer = build_buffer(_synthetic_rows(), "1m")
    check("بناء مخزن الشموع 1m", buffer is not None and len(buffer["c"]) == 99 and buffer["live"] == 110.0)
    last_t = buffer["t"][-1]
    check("إزالة تكرار شمعة مغلقة",
          buffer_append(buffer, "1m", last_t, 105.0, 110.3, 104.0, 110.0, 4000.0) == "updated"
          and len(buffer["c"]) == 99)
    check("إلحاق شمعة جديدة + كشف فجوة",
          buffer_append(buffer, "1m", last_t + 60_000, 109.5, 110.4, 109.0, 109.8, 900.0) == "appended"
          and buffer_append(buffer, "1m", last_t + 4 * 60_000, 109.0, 110.0, 108.5, 109.5, 800.0) == "gap")

    # 3) ثوابت V6.0 الحرفية (Micro-Exits + زناد القنّاص)
    check(f"Micro-Exits: وقف زمني {TIME_STOP_SEC}ث بربح أدنى {TIME_STOP_MIN_PROFIT_PCT}%",
          TIME_STOP_SEC == 45 and TIME_STOP_MIN_PROFIT_PCT == 0.10)
    check(f"تعادل واعٍ بالرسوم: تفعيل +{BREAKEVEN_TRIGGER_PCT:g}% وقفل +{BREAKEVEN_LOCK_PCT:g}% (فوق تكلفة {FEE_ROUND_TRIP_PCT:.2f}%)",
          BREAKEVEN_TRIGGER_PCT == 0.30 and BREAKEVEN_LOCK_PCT == 0.25
          and BREAKEVEN_LOCK_PCT >= FEE_ROUND_TRIP_PCT - 1e-9)
    check(f"زناد القنّاص: هبوط ≥ {FLASH_DROP_PCT}% خلال {TICK_MEMORY_SEC:.0f}ث + جدار {BUY_WALL_RATIO:g}x",
          FLASH_DROP_PCT == 0.25 and BUY_WALL_RATIO == 1.5 and TICK_MEMORY_SEC == 15.0)
    check("ثوابت V6.1: الرشاش مفعّل والقنّاص مضخّم وميزانية الأوامر تحت حد Binance",
          SPRAY_ENABLED and SNIPER_RISK_MULT > 1.0
          and float(SNIPER_MAX_NOTIONAL_USD) > float(MAX_POSITION_NOTIONAL_USD)
          and ORDER_BUDGET_MAX < 50)

    # 4) Micro-Memory: sliding-window maximum بلا أي مسح نافذة (O(1)/tick)
    TICKS.clear()
    now_ts = time.time()
    for ts, px in [(now_ts - 10, 100.0), (now_ts - 8, 99.5), (now_ts - 6, 100.4),
                   (now_ts - 4, 99.9), (now_ts - 2, 99.0)]:
        tick_add("TSTUSDT", ts, px)
    stats = tick_window_stats("TSTUSDT")
    check("Micro-Memory تحفظ قمة النافذة وآخر سعر",
          stats is not None and abs(stats["high"] - 100.4) < 1e-9
          and abs(stats["last"] - 99.0) < 1e-9 and stats["samples"] == 5)
    TICKS.clear()
    for ts, px in [(now_ts - 30, 105.0), (now_ts - 25, 104.8)]:
        tick_add("TSTUSDT", ts, px)
    tick_add("TSTUSDT", now_ts - 1, 99.0)     # تقدّم التدفق يُقليم القمم المنتهية
    mem_probe = TICKS["TSTUSDT"]
    stats2 = tick_window_stats("TSTUSDT")
    check("تقادم النافذة (أفق نسبي للتدفق): لا قمة شبح والذاكرة تُنظَّف",
          stats2 is None and len(mem_probe["prices"]) == 1
          and abs(mem_probe["prices"][0][1] - 99.0) < 1e-9
          and len(mem_probe["maxq"]) == 1)
    tick_add("TSTUSDT", now_ts - 30, 200.0)   # صفقة متأخرة خارج الأفق
    check("الصفقات المتأخرة جداً تُهمَل (لا تلوث آخر سعر الذي يُقاس عليه الهبوط)",
          len(TICKS["TSTUSDT"]["prices"]) == 1
          and abs(TICKS["TSTUSDT"]["prices"][-1][1] - 99.0) < 1e-9)
    tick_add("TSTUSDT", now_ts, 98.9)
    stats3 = tick_window_stats("TSTUSDT")
    check("النافذة تتدحرج للأمام: القمة 99.0 والآخر 98.9 (O(1)/tick)",
          stats3 is not None and abs(stats3["high"] - 99.0) < 1e-9
          and abs(stats3["last"] - 98.9) < 1e-9)
    TICKS.clear()
    check("ذاكرة فارغة ⇒ بلا هبوط", flash_drop_pct("TSTUSDT") == 0.0)

    # 5) قرار القنّاص النقي: هبوط ≥ 0.25% + جدار شراء 1.5x
    STATE = default_state()
    SYMBOLS.clear(); SYMBOLS.extend(["TSTUSDT"]); SYMBOLS_SET.clear(); SYMBOLS_SET.add("TSTUSDT")
    TICKS.clear(); BOOK.clear(); PENDING_SNIPES.clear(); HFT_ATTEMPT.clear()
    now_ts = time.time()
    for ts, px in [(now_ts - 12, 100.0), (now_ts - 6, 99.4), (now_ts - 1, 98.6)]:
        tick_add("TSTUSDT", ts, px)
    check("هبوط 1.4% ≥ العتبة داخل نافذة الذاكرة",
          abs(flash_drop_pct("TSTUSDT") - 1.4) < 1e-9)
    decision = sniper_decision("TSTUSDT")
    check("هبوط بلا bookTicker ⇒ pending (الصيد يبقى حياً بانتظار الجدار)",
          decision is not None and decision["action"] == "pending"
          and abs(decision["drop_pct"] - 1.4) < 1e-9)
    BOOK["TSTUSDT"] = {"bid": 98.6, "ask": 98.61, "bid_qty": 3.0, "ask_qty": 1.0,
                       "bid_vol": 300.0, "ask_vol": 100.0, "spread_pct": 0.01, "ts": time.monotonic()}
    decision = sniper_decision("TSTUSDT")
    check("جدار شراء 3x حديث ⇒ fire فوري",
          decision is not None and decision["action"] == "fire"
          and abs(decision["wall_ratio"] - 3.0) < 1e-9)
    BOOK["TSTUSDT"]["bid_vol"] = 140.0
    decision = sniper_decision("TSTUSDT")
    check("جدار 1.4x تحت العتبة ⇒ pending فقط",
          decision is not None and decision["action"] == "pending")
    BOOK["TSTUSDT"]["bid_vol"] = 300.0
    BOOK["TSTUSDT"]["ts"] = time.monotonic() - (BUY_WALL_MAX_AGE + 1.0)
    decision = sniper_decision("TSTUSDT")
    check("bookTicker أقدم من BUY_WALL_MAX_AGE ⇒ لا تأكيد (pending)",
          decision is not None and decision["action"] == "pending")
    TICKS.clear()
    for ts, px in [(now_ts - 12, 100.0), (now_ts - 1, 99.8)]:
        tick_add("TSTUSDT", ts, px)
    check("هبوط 0.2% < العتبة ⇒ لا قرار ويُمسح الصيد المعلّق",
          sniper_decision("TSTUSDT") is None and "TSTUSDT" not in PENDING_SNIPES)

    # 5ب) إيقاظ الحيتان: تلميح تشخيصي فقط (/insight) — لا تأثير على الدخول
    WHALES.clear()
    check("whale_mark يتجاهل ما دون العتبة ويسجّل ما فوقها",
          whale_mark("TSTUSDT", WHALE_TRADE_USD / 2.0) is False
          and whale_mark("TSTUSDT", WHALE_TRADE_USD * 2.0) is True
          and whale_recent("TSTUSDT")[0] is True)
    WHALES["TSTUSDT"]["ts"] = time.time() - (WHALE_MEMORY_SEC + 5)
    check("ذاكرة الحوت تنتهي زمنياً وتُنظَّف (لا تسرّب ذاكرة)",
          whale_recent("TSTUSDT")[0] is False and "TSTUSDT" not in WHALES)
    WHALES.clear()

    # 5ج) الرشاش (V6.1): اندفاعة صاعدة + هيمنة مشترين ⇒ إطلاق (محرك OR التكيفي)
    SPRAY_BASE.clear(); SPRAY_ATTEMPT.clear()
    STATE = default_state()
    SYMBOLS.clear(); SYMBOLS.extend(["TSTUSDT"]); SYMBOLS_SET.clear(); SYMBOLS_SET.add("TSTUSDT")
    TICKS.clear(); BOOK.clear(); FLOW.clear()
    CANDLES[("TSTUSDT", MICRO_INTERVAL)] = build_buffer(_synthetic_rows(), "1m")
    BOOK["TSTUSDT"] = {"bid": 100.20, "ask": 100.21, "bid_qty": 5.0, "ask_qty": 5.0,
                       "bid_vol": 500.0, "ask_vol": 500.0, "spread_pct": 0.01, "ts": time.monotonic()}
    BTC_CTX = {"closes": deque([100.0] * 8, maxlen=BTC_DROP_WINDOW_MIN + 25), "live": 100.0,
               "last_t": int(time.time() * 1000) // 60_000 * 60_000,
               "last_update": time.monotonic(), "seeded": True, "vr": 1.0}
    sprayed = []
    real_launch_spray = launch_entry
    saved_eval = SPRAY_EVAL_EVERY
    globals()["SPRAY_EVAL_EVERY"] = 0.0     # التوقيتات اصطناعية أسرع من الواقع — بلا خنق زمني
    globals()["launch_entry"] = lambda signal: sprayed.append(dict(signal))
    base_t2 = int(time.time() * 1000)
    for i in range(12):      # صعود 0.24% خلال 12 ثانية بصفقات مشترين حقيقية فقط
        px = 100.0 + i * 0.02
        on_agg_trade("TSTUSDT", {"p": f"{px:.3f}", "q": "3", "m": False,
                                 "T": base_t2 - 12_000 + i * 1_000})
    globals()["launch_entry"] = real_launch_spray
    globals()["SPRAY_EVAL_EVERY"] = saved_eval
    check("الرشاش: اندفاعة ≥ العتبة التكيفية + هيمنة مشترين ⇒ إطلاق (impulse/flow)",
          len(sprayed) >= 1 and sprayed[0]["trigger"] in ("impulse", "flow")
          and float(sprayed[0]["flow_ratio"]) >= SPRAY_IMPULSE_FLOW
          and float(sprayed[0]["move_pct"]) >= SPRAY_BASELINE_FLOOR_PCT)
    sprayed.clear()
    globals()["SPRAY_EVAL_EVERY"] = 0.0
    globals()["launch_entry"] = lambda signal: sprayed.append(dict(signal))
    for i in range(6):       # هبوط حقيقي: لا اندفاعة صاعدة ولا هيمنة بائعين تُشترى
        px = 100.0 - i * 0.05
        on_agg_trade("TSTUSDT", {"p": f"{px:.3f}", "q": "3", "m": True,
                                 "T": base_t2 + 15_000 + i * 1_000})
    globals()["launch_entry"] = real_launch_spray
    globals()["SPRAY_EVAL_EVERY"] = saved_eval
    check("الرشاش لا يشتري الهبوط (اتجاه واحد خاطئ ⇒ صفر إطلاق)", len(sprayed) == 0)
    TICKS.clear(); FLOW.clear(); SPRAY_BASE.clear(); SPRAY_ATTEMPT.clear()

    # 6) المسار الحدثي: on_agg_trade ⇒ إطلاق واحد + خنق، وon_book يؤكد الجدار
    TICKS.clear(); PENDING_SNIPES.clear(); HFT_ATTEMPT.clear(); BOOK.clear()
    STATE = default_state()
    CANDLES[("TSTUSDT", MICRO_INTERVAL)] = build_buffer(_synthetic_rows(), "1m")
    BOOK["TSTUSDT"] = {"bid": 98.6, "ask": 98.61, "bid_qty": 3.0, "ask_qty": 1.0,
                       "bid_vol": 300.0, "ask_vol": 100.0, "spread_pct": 0.01, "ts": time.monotonic()}
    fired = []
    real_launch = launch_entry
    globals()["launch_entry"] = lambda signal: fired.append(dict(signal))
    base_t = int(time.time() * 1000)
    for i, px in enumerate(("100.0", "99.9", "99.8", "99.7", "98.6")):
        on_agg_trade("TSTUSDT", {"p": px, "q": "2", "m": False, "T": base_t - 10_000 + i * 2_000})
    check("aggTrade هابط ≥0.25% مع جدار 3x ⇒ إطلاق فوري واحد (بلا أي إغلاق شمعة)",
          len(fired) == 1 and fired[0]["symbol"] == "TSTUSDT"
          and fired[0]["trigger"] == "flash-crash" and fired[0]["drop_pct"] >= FLASH_DROP_PCT
          and fired[0]["wall_ratio"] >= BUY_WALL_RATIO and fired[0]["atr_1m"] > 0)
    on_agg_trade("TSTUSDT", {"p": "98.6", "q": "2", "m": False, "T": base_t})
    check("خنق المحاولات: لا إطلاق مزدوج أثناء نفس الانهيار", len(fired) == 1)
    PENDING_SNIPES.clear(); HFT_ATTEMPT.clear()
    TICKS.clear()
    for ts, px in [(time.time() - 10, 100.0), (time.time() - 1, 98.7)]:
        tick_add("TSTUSDT", ts, px)
    BOOK["TSTUSDT"] = {"bid": 98.7, "ask": 98.72, "bid_qty": 1.0, "ask_qty": 1.0,
                       "bid_vol": 100.0, "ask_vol": 100.0, "spread_pct": 0.02, "ts": time.monotonic()}
    on_market_tick("TSTUSDT")
    check("هبوط بلا جدار يُسجَّل معلّقاً (انتظار bookTicker)",
          "TSTUSDT" in PENDING_SNIPES and len(fired) == 1)
    saved_retry = SNIPER_RETRY_SEC
    globals()["SNIPER_RETRY_SEC"] = 0.0
    on_book("TSTUSDT", {"b": "98.7", "B": "4", "a": "98.71", "A": "1"})
    globals()["SNIPER_RETRY_SEC"] = saved_retry
    check("on_book يؤكد الجدار ⇒ إطلاق فوري من الصيد المعلّق",
          len(fired) == 2 and fired[1]["trigger"] == "flash-crash" and "TSTUSDT" not in PENDING_SNIPES)
    globals()["launch_entry"] = real_launch
    TICKS.clear(); PENDING_SNIPES.clear(); HFT_ATTEMPT.clear()

    # 7) get_* الديناميكي (Gemini) + محرك التتبّع يقرأ STATE حياً
    STATE = default_state()
    check("getters ترجع الافتراضي قبل أي Auto-Tune",
          get_be_trigger_pct() == BREAKEVEN_TRIGGER_PCT and get_time_stop_sec() == TIME_STOP_SEC)
    STATE["be_trigger_pct"] = 0.35
    STATE["time_stop_sec"] = 90
    check("Auto-Tune يغيّر المعاملات فعلياً من STATE",
          get_be_trigger_pct() == 0.35 and get_time_stop_sec() == 90)
    STATE["be_trigger_pct"] = 99.0
    STATE["time_stop_sec"] = -5
    check("getters تُقيّد القيم الشاذة داخل حدود آمنة",
          get_be_trigger_pct() == 5.0 and get_time_stop_sec() == TIME_STOP_SEC)
    STATE["be_trigger_pct"] = None
    STATE["time_stop_sec"] = None
    p_be = trailing_plan(100.0, 100.31, 100.31)
    check(f"تتبّع يسلّح عند +{BREAKEVEN_TRIGGER_PCT:g}% ويقفل +{BREAKEVEN_LOCK_PCT:g}% (فوق الرسوم)",
          p_be["armed"] and p_be["stop"] >= 100.0 * (1 + BREAKEVEN_LOCK_PCT / 100.0) - 1e-9)
    check("ربح 0.2% (تحت الرسوم) لا يسلّح التعادل",
          trailing_plan(100.0, 100.20, 100.20)["armed"] is False)
    STATE["be_trigger_pct"] = 0.50
    check("Auto-Tune يغيّر سلوك التتبّع حياً (عتبة 0.5% لا تُسلّح ربح 0.2%)",
          trailing_plan(100.0, 100.20, 100.20)["armed"] is False
          and trailing_plan(100.0, 100.50, 100.50)["armed"] is True)
    STATE["be_trigger_pct"] = None
    p_tight = trailing_plan(100.0, 102.0, 102.0)
    check(f"ربح > {TRAIL_TIGHT_AFTER_PCT:g}% ⇒ خنق التتبّع إلى {TRAIL_TIGHT_PCT:g}%",
          p_tight["mode"] == "trail-tight" and abs(p_tight["trail_pct"] - TRAIL_TIGHT_PCT) < 1e-9
          and abs(p_tight["stop"] - 102.0 * (1 - TRAIL_TIGHT_PCT / 100.0)) < 1e-9)
    p_hit = trailing_plan(100.0, 102.0, 101.90)
    check("لمس الوقف المتحرك ⇒ hit=True بربح مؤمَّن موجب",
          p_hit["hit"] is True and p_hit["gain_pct"] > 0)
    p_bad = trailing_plan(0.0, 0.0, 0.0)
    check("مدخلات فاسدة لمحرك التتبّع لا تفجّره",
          p_bad["armed"] is False and p_bad["hit"] is False)
    check("الوقف المتحرك لا يتراجع مع هبوط السعر (peak أحادي الاتجاه)",
          trailing_plan(100.0, 102.0, 100.5)["stop"]
          >= trailing_plan(100.0, 101.0, 100.5)["stop"] - 1e-12)

    # 8) وقف الطوارئ ATR(1m)×1.5 + سقف + أرضية (بلا أي رجل هدف)
    r_micro = calculate_dynamic_risk(100.0, 0.0, 1.0, 1.0)
    check(f"وقف الطوارئ = ATR(1m) × {HARD_STOP_ATR_MULT:g}",
          abs(r_micro["sl_distance"] - 1.5) < 1e-9 and abs(r_micro["sl"] - 98.5) < 1e-9
          and "tp" not in r_micro)
    r_cap = calculate_dynamic_risk(100.0, 0.0, 2.0, 10.0)
    check(f"سقف الوقف الصلب {SL_MAX_PCT}% (Flash-Crash Cap)",
          abs(r_cap["sl_distance"] - 3.0) < 1e-9 and abs(r_cap["sl_pct"] - 3.0) < 1e-9
          and r_cap["capped"])
    r_floor = calculate_dynamic_risk(100.0, 0.0, 1.0, 0.0)
    check(f"أرضية الوقف {SL_MIN_PCT}% عند غياب أي ATR",
          r_floor["sl"] < 100.0 and abs(r_floor["sl_pct"] - SL_MIN_PCT) < 1e-9)
    hs, hs_risk = hard_stop_price(100.0, 1.0, 0.0, 1.0)
    check("hard_stop_price يعيد وقفاً وحيداً بلا أي رجل هدف",
          hs == D("98.5") and "tp" not in hs_risk)

    # 9) الحجم المصغّر المبني على المخاطرة (Risk Parity — محفوظ حرفياً)
    q1, n1, k1 = plan_position(100.0, 10.0, D("0.001"))
    q2, n2, k2 = plan_position(100.0, 0.5, D("0.001"))
    q3, n3, k3 = plan_position(100.0, 10.0, D("0.001"), 3.0)
    check(f"مخاطرة ثابتة {TARGET_RISK_USD}$ (وقف واسع ⇒ مركز صغير)",
          abs(float(k1) - 1.0) < 1e-6 and float(q1) == 0.1)
    check(f"سقف المركز {MAX_POSITION_NOTIONAL_USD}$ يمنع انفجار الحجم",
          abs(float(n2) - float(MAX_POSITION_NOTIONAL_USD)) < 1e-9)
    check(f"تنصيف الحجم عند VR > {VR_FAST:g} (تقليل التعرض في الفوضى)",
          abs(float(n3) - 5.0) < 1e-6 and abs(float(k3) - 0.5) < 1e-6)
    bad_qty, bad_notional, _bad_risk = plan_position(100.0, 0.0, D("0.001"))
    check("وقف بصفر مسافة → رفض (لا قسمة على صفر)", bad_qty is None and bad_notional is None)

    # 10) قاطع سياق BTC (Circuit Breaker) + التهدئة الديناميكية
    STATE = default_state()
    minute_ms = 60_000
    t_now = int(time.time() * 1000) // minute_ms * minute_ms
    BTC_CTX = {"closes": deque([100.0] * 8, maxlen=BTC_DROP_WINDOW_MIN + 25), "live": 99.0,
               "last_t": t_now, "last_update": time.monotonic(), "seeded": True, "vr": 1.0}
    blocked, why = btc_circuit_block()
    check(f"منع الشراء عند هبوط BTC 1% في 3د (سبب: {why})",
          blocked and abs(btc_ctx_stats()["drop_pct"] + 1.0) < 1e-6)
    BTC_CTX["live"] = 100.0
    check("سوق BTC مستقر → لا منع", btc_circuit_block()[0] is False)
    BTC_CTX["last_update"] = time.monotonic() - (BTC_CTX_MAX_AGE + 10)
    check("مصدر سياق ميت → منع (فشل آمن)", btc_circuit_block()[1] == "context-unavailable")
    BTC_CTX = {"closes": deque([100.0] * 8, maxlen=BTC_DROP_WINDOW_MIN + 25), "live": 100.0,
               "last_t": t_now, "last_update": time.monotonic(), "seeded": True, "vr": 1.0}
    BTC_CTX["vr"] = 2.0
    check(f"سوق متقلب → تهدئة {COOLDOWN_FAST}ث", btc_cooldown() == COOLDOWN_FAST)
    BTC_CTX["vr"] = 1.0
    check(f"سوق طبيعي → تهدئة {COOLDOWN_NORMAL}ث", btc_cooldown() == COOLDOWN_NORMAL)

    # 11) توقيع HMAC مع aiohttp (سلسلة حرفية واحدة بلا إعادة ترميز)
    globals()["BINANCE_API_KEY"] = "TEST_KEY"
    globals()["BINANCE_API_SECRET"] = "TEST_SECRET"
    values = {"symbol": "BTCUSDT", "quantity": "0.001", "recvWindow": 5000, "timestamp": 1700000000000}
    query, headers = build_signed(values)
    expected_query = "symbol=BTCUSDT&quantity=0.001&recvWindow=5000&timestamp=1700000000000"
    expected_sig = hmac.new(b"TEST_SECRET", expected_query.encode(), hashlib.sha256).hexdigest()
    globals()["BINANCE_API_KEY"], globals()["BINANCE_API_SECRET"] = "", ""
    check("توقيع HMAC-SHA256 مطابق حرفياً",
          query == f"{expected_query}&signature={expected_sig}" and headers["X-MBX-APIKEY"] == "TEST_KEY")

    # 12) الحجز الذري: 5 محاولات متزامنة → 3 فقط (ترقيع السباق محفوظ)
    ENTRY_RESERVATIONS = {}
    RESERVED_QUOTE = Decimal("0")
    outcomes = await asyncio.gather(*[reserve_entry("TSTUSDT", Decimal("80")) for _ in range(5)])
    for _ in range(3):
        await release_entry("TSTUSDT", Decimal("80"))
    check("Pyramiding: 3 مراكز كحد أقصى (بلا سباق)",
          sum(1 for x in outcomes if x) == 3 and RESERVED_QUOTE == Decimal("0"))

    # 13) Gemini Brain: JSON المفروض + الحدود الصلبة + البرومبتات + الفشل الآمن
    check("parse_json_loose: JSON نظيف", (parse_json_loose('{"a": 1}') or {}).get("a") == 1)
    check("parse_json_loose: أسوار كود ونص محيط",
          (parse_json_loose('إليك النتيجة:\n```json\n{"breakeven_trigger_pct": 0.3}\n```') or {})
          .get("breakeven_trigger_pct") == 0.3)
    check("parse_json_loose: فوضى ⇒ None", parse_json_loose("لا JSON هنا") is None)
    tuned = clamp_tuned_params({"breakeven_trigger_pct": 9.9, "time_stop_sec": 5000, "reason": "اختبار"})
    check("clamp_tuned_params يُجمّد جسور Gemini داخل الحدود الصلبة",
          tuned is not None and tuned["breakeven_trigger_pct"] == 1.20 and tuned["time_stop_sec"] == 240)
    tuned_low = clamp_tuned_params({"breakeven_trigger_pct": 0.01, "time_stop_sec": 5})
    check("clamp_tuned_params يرفع المتدني للحد الأدنى الآمن (لا قفل تحت الرسوم)",
          tuned_low is not None and tuned_low["breakeven_trigger_pct"] == 0.25
          and tuned_low["time_stop_sec"] == 30)
    check("clamp_tuned_params يرفض الفوضى",
          clamp_tuned_params({"breakeven_trigger_pct": "abc"}) is None
          and clamp_tuned_params("نص") is None)
    class _StubAggRest:
        async def agg_trades(self, symbol, limit=100):
            now_ms = time.time() * 1000
            return [[1, "100.0", "2", 0, 0, now_ms - 5000, False, True],
                    [2, "98.0", "3", 0, 0, now_ms - 1000, True, True]]
    _saved_agg_rest = REST
    globals()["REST"] = _StubAggRest()
    TICKS.clear(); FLOW.clear()
    seed_ok = await prime_flow_from_rest("TSTUSDT")
    stats_seed = tick_window_stats("TSTUSDT")
    ratio_seed, _age_seed = flow_imbalance("TSTUSDT")
    globals()["REST"] = _saved_agg_rest
    check("بذر --once يقرأ مخطط aggTrades الرسمي (T=index5، m=index6) ويبذر الذاكرة",
          seed_ok is True and stats_seed is not None
          and abs(stats_seed["high"] - 100.0) < 1e-9
          and abs(stats_seed["last"] - 98.0) < 1e-9 and ratio_seed < 1.0)
    FLOW.clear(); TICKS.clear()

    prompt_tune = await build_tune_prompt()
    check("برومبت Auto-Tune يحمل FUNNEL وWin/Loss وتقلب BTC_CTX",
          all(key in prompt_tune for key in ("FUNNEL", "Win/Loss", "BTC_CTX", "breakeven_trigger_pct")))
    err_text, err = await gemini_ask("اختبار", timeout=5)
    check("gemini_ask بلا مفتاح ⇒ فشل آمن (لا استثناء ولا حجب)",
          err_text is None and err == "gemini-unavailable")

    # 14) سجل الصفقات (trade_log) + بيانات التشريح (/autopsy)
    STATE = default_state()
    STATE["positions"]["TSTUSDT#z"] = {"symbol": "TSTUSDT", "entry": 100.0, "qty": "0.2",
                                       "order_ids": [701], "opened_at": time.time() - 60.0,
                                       "trigger": "flash-crash"}
    real_save = save_state

    async def _noop_save():
        return None
    globals()["save_state"] = _noop_save
    await finalize_position_event("TSTUSDT#z", STATE["positions"]["TSTUSDT#z"], 98.0, 0.2, "وقف زمني")
    log_rows = STATE.get("trade_log")
    check("trade_log يسجّل PnL والمدة والرمز عند كل إغلاق",
          isinstance(log_rows, list) and len(log_rows) == 1 and log_rows[0]["symbol"] == "TSTUSDT"
          and log_rows[0]["pnl"] < 0 and 55.0 <= log_rows[0]["duration_sec"] <= 65.0
          and log_rows[0]["trigger"] == "flash-crash")
    prompt_autopsy, fallback_autopsy = await build_autopsy_prompt()
    check("برومبت التشريح يضم PnL/المدة/الرمز للخسائر",
          prompt_autopsy is not None and "TSTUSDT" in prompt_autopsy
          and "مدة الصفقة" in prompt_autopsy and fallback_autopsy is not None
          and collect_losing_trades() == log_rows)
    STATE["trade_log"].clear()
    check("بلا خسائر ⇒ لا برومبت تشريح", (await build_autopsy_prompt())[0] is None)

    # 15) المسار الكامل: قنصة → MARKET BUY → وقف صلب وحيد → تتبّع حي → MARKET SELL
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
            self.maker_calls = []
            self.maker_reject = False
        async def account(self):
            return {"balances": [{"asset": "USDT", "free": "5000", "locked": "0"}]}
        async def new_order(self, params):
            self.order_calls.append(params)
            qty = D(params.get("quantity", "0"))
            if params.get("type") == "LIMIT_MAKER":
                if self.maker_reject:
                    raise BinanceError("would immediately match and take", -2010, 400)
                self.maker_calls.append(params)
                return {"orderId": 600 + len(self.maker_calls), "status": "NEW",
                        "executedQty": "0", "cummulativeQuoteQty": "0"}
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
    globals()["save_state"] = _noop_save
    globals()["BINANCE_API_KEY"] = "TEST_KEY"
    globals()["BINANCE_API_SECRET"] = "TEST_SECRET"
    saved_dry, saved_auto = DRY_RUN, AUTO_TRADE
    saved_scale_out = SCALE_OUT_ENABLED
    saved_maker_legacy = MAKER_ENTRIES
    globals()["DRY_RUN"] = False
    globals()["AUTO_TRADE"] = True
    globals()["SCALE_OUT_ENABLED"] = False      # اختبار المسار القديم بلا بيع جزئي — له اختبار مستقل
    globals()["MAKER_ENTRIES"] = False          # المسار التراثي: MARKET كما في V6.0/V6.1
    ORDER_TS.clear()
    STATE = default_state()
    ORDERS.clear()
    SETUPS.clear()
    EXIT_CLAIMED.clear()
    EXIT_PENDING.clear()
    ENTRY_RESERVATIONS = {}
    RESERVED_QUOTE = Decimal("0")
    BTC_CTX["vr"] = 1.0
    BTC_CTX["live"] = 100.0
    BTC_CTX["closes"] = deque([100.0] * 8, maxlen=BTC_DROP_WINDOW_MIN + 25)
    BTC_CTX["last_update"] = time.monotonic()
    SYMBOL_RULES["TSTUSDT"] = {
        "status": "TRADING", "base": "TST", "quote": "USDT",
        "tick": D("0.01"), "step": D("0.001"), "min_qty": D("0"), "max_qty": D("999999"),
        "market_step": D("0.001"), "market_min_qty": D("0"), "min_notional": D("5"),
    }
    signal_sniper = {
        "symbol": "TSTUSDT", "setup_id": "TSTUSDT@flash@1700000000000",
        "trigger": "flash-crash", "drop_pct": 1.45, "wall_ratio": 3.4,
        "atr": 0.0, "atr_1m": 1.0, "vr": 1.0, "score": 0.0,
        "flow_imbalance": 9.0, "close": 110.0, "live": 110.0,
        "created_at": time.time(),
    }
    BOOK["TSTUSDT"] = {"bid": 98.6, "ask": 98.61, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 986.0, "ask_vol": 986.1, "imbalance": 0.5,
                       "spread_pct": 0.01, "ts": time.monotonic()}
    FLOW.clear()
    flow_add("TSTUSDT", time.time(), 9000.0, 1000.0)
    FLOW["TSTUSDT"]["price"] = 110.0
    FLOW["TSTUSDT"]["epoch"] = time.time()
    CANDLES.pop(("TSTUSDT", MICRO_INTERVAL), None)
    signal_noatr = dict(signal_sniper)
    signal_noatr["atr_1m"] = 0.0
    check("رفض قنصة بلا ATR(1m): لا وقف طوارئ عاقل ⇒ لا تنفيذ",
          estimate_entry_cost(signal_noatr) is None and FUNNEL.get("no-atr", 0) >= 1)
    CANDLES[("TSTUSDT", MICRO_INTERVAL)] = build_buffer(_synthetic_rows(), "1m")
    priced = estimate_entry_cost(signal_sniper)
    sizing_ok = (priced is not None and abs(float(priced["price"]) - 110.0) < 1e-9
                 and abs(float(priced["sl_distance"]) - 1.5) < 1e-9
                 and abs(float(priced["notional"]) - float(SNIPER_MAX_NOTIONAL_USD)) < 0.2
                 and float(priced["notional"]) <= float(SNIPER_MAX_NOTIONAL_USD)
                 and float(priced["notional"]) > float(MAX_POSITION_NOTIONAL_USD)
                 and "target" not in priced)
    entry_ok = await process_signal(signal_sniper)
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
    check("قنصة ⇒ MARKET BUY فوري + وقف طوارئ صلب وحيد (بلا OCO ولا هدف)", market_ok)
    check(f"قنّاص مضخّم: سقف {SNIPER_MAX_NOTIONAL_USD}$ (فوق سقف الرشاش {MAX_POSITION_NOTIONAL_USD}$) ووقف ATR(1m)×{HARD_STOP_ATR_MULT:g}",
          sizing_ok and float(stub.order_calls[0]["quantity"]) > 0)
    check("المركز يحمل تلميحات القنصة (trigger/drop_pct/wall_ratio)",
          position.get("trigger") == "flash-crash"
          and abs(float(position.get("drop_pct", 0)) - 1.45) < 1e-9
          and abs(float(position.get("wall_ratio", 0)) - 3.4) < 1e-9)
    check("حالة المركز مهيأة لمحرك التتبّع (peak/trail بلا تسريب)",
          abs(float(position.get("peak", 0)) - 100.0) < 1e-9
          and position.get("trail_armed") is False and position.get("trail_mode") == "off")
    dedup_ok = position.get("setup_id") in SETUPS
    check("Setup ID سُجِّل لمنع التكرار", dedup_ok)
    check("الأمر المُعبأ من الاستجابة لا يترك معلَّقاً ولا Watchdog",
          not STATE["pending_entries"] and stub.get_order_calls == 0)
    if pid:
        cid_repeat = position.get("entry_client_id")
        STATE["pending_entries"][cid_repeat] = {
            "symbol": "TSTUSDT", "client_order_id": cid_repeat, "order_id": 501,
            "qty": "0.109", "price": "110", "atr": 0.0, "atr_1m": 1.0, "vr": 1.0, "phase": "done",
        }
        await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid_repeat, "i": 501,
                                  "S": "BUY", "x": "TRADE", "X": "FILLED",
                                  "l": "0.109", "L": "100", "z": "0.109", "Z": "10.9"})
        STATE["pending_entries"].pop(cid_repeat, None)
    check("ترقيع السباق: الحدث المكرر لا يكرر الحماية ولا المركز",
          len(stub.stop_calls) == 1 and len(STATE["positions"]) == 1)

    # 15ب) محرك الخروج الهجين حياً: bookTicker ⇒ تعادل +0.30% ⇒ قفل فوق الرسوم ⇒ تتبّع ⇒ MARKET SELL
    on_book("TSTUSDT", {"b": "100.10", "B": "5", "a": "100.11", "A": "5"})
    armed_no = STATE["positions"][pid].get("trail_armed") is False
    on_book("TSTUSDT", {"b": "100.31", "B": "5", "a": "100.32", "A": "5"})
    live = STATE["positions"][pid]
    armed_yes = (live.get("trail_armed") is True and live.get("trail_mode") == "breakeven"
                 and abs(float(live.get("trail_stop")) - 100.0 * (1 + BREAKEVEN_LOCK_PCT / 100.0)) < 1e-9)
    check(f"bookTicker يفعّل التعادل عند +{BREAKEVEN_TRIGGER_PCT:g}% ويقفل +{BREAKEVEN_LOCK_PCT:g}% (فوق الرسوم)",
          armed_no and armed_yes)
    on_book("TSTUSDT", {"b": "100.50", "B": "5", "a": "100.51", "A": "5"})
    wide_ok = (STATE["positions"][pid].get("trail_mode") == "trail-wide"
               and abs(float(STATE["positions"][pid]["trail_stop"]) - 100.5 * (1 - TRAIL_WIDE_PCT / 100.0)) < 1e-9)
    check(f"ربح فوق العتبة ⇒ تتبّع واسع {TRAIL_WIDE_PCT:g}%", wide_ok)
    on_book("TSTUSDT", {"b": "102.00", "B": "5", "a": "102.01", "A": "5"})
    tight_ok = (STATE["positions"][pid].get("trail_mode") == "trail-tight"
                and abs(float(STATE["positions"][pid]["trail_stop"]) - 102.0 * (1 - TRAIL_TIGHT_PCT / 100.0)) < 1e-9)
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
    on_book("TSTUSDT", {"b": "101.00", "B": "5", "a": "101.01", "A": "5"})
    for _ in range(4):
        await asyncio.sleep(0)
    check("لا بيع مزدوج: تحديثات السعر بعد الإغلاق لا تُصدر أوامر",
          len(stub.sell_calls) == 1 and not STATE["positions"])

    # 15ج) فشل إلغاء الوقف ⇒ لا MARKET SELL إطلاقاً (حماية من الكمية المزدوجة)
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

    # 15د) فشل البيع بعد إلغاء الوقف ⇒ إعادة تركيب الحماية فوراً (لا مركز مكشوف)
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
    await force_exit_position("TSTUSDT#naked", dict(STATE["positions"]["TSTUSDT#naked"]), "تنظيف")
    STATE["positions"].pop("TSTUSDT#naked", None)

    # 15هـ) تعبئة جزئية لوقف الطوارئ تُقلّص كمية المركز (لا بيع كمية غير مملوكة)
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
    cid2 = make_client_id("nv6")
    STATE["pending_entries"][cid2] = {
        "symbol": "TSTUSDT", "client_order_id": cid2, "order_id": 112,
        "qty": "0.19", "price": "103", "atr": 0.0, "atr_1m": 1.0, "vr": 1.0,
        "placed_at": time.time(), "active": False, "phase": "placed",
    }
    ORDERS["112"] = {"role": "entry", "cid": cid2, "symbol": "TSTUSDT"}
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid2, "i": 112,
                              "S": "BUY", "x": "CANCELED", "X": "CANCELED",
                              "l": "0", "L": "0", "z": "0", "Z": "0"})
    check("executionReport CANCELED (بلا تعبئة) → حذف المعلق", cid2 not in STATE["pending_entries"])
    check("صفر REST Polling لحالة الأوامر في المسار السعيد",
          stub.get_order_calls == 0 and stub.open_orders_calls == 0)

    # 15ط) البيع الجزئي (Scale-Out): نصف المركز يُقفل ربحاً والباقي يستمر بتتبّع ثم يُغلق صافياً
    globals()["SCALE_OUT_ENABLED"] = True
    SCALE_PENDING.clear()
    STATE["positions"]["TSTUSDT#so"] = {
        "pid": "TSTUSDT#so", "symbol": "TSTUSDT", "entry": 100.0, "qty": "1.0",
        "entry_quote": 100.0, "fees_entry": 0.1, "partial_pnl": 0.0, "fees_partial": 0.0,
        "order_ids": [950], "peak": 100.0, "trail_armed": False, "trail_mode": "off",
        "stop": 98.5, "hard_stop": 98.5, "opened_at": time.time(), "trigger": "flow",
    }
    ORDERS["950"] = {"role": "leg", "pid": "TSTUSDT#so", "symbol": "TSTUSDT"}
    sells_before_so = len(stub.sell_calls)
    stops_before_so = len(stub.stop_calls)
    wins_before_so = int(STATE["metrics"]["wins"])
    on_book("TSTUSDT", {"b": "100.50", "B": "5", "a": "100.51", "A": "5"})
    for _ in range(10):
        await asyncio.sleep(0)
    so_live = STATE["positions"].get("TSTUSDT#so") or {}
    so_ok = (len(stub.sell_calls) == sells_before_so + 1
             and abs(float(so_live.get("qty", "0")) - 0.501) < 1e-9
             and float(so_live.get("partial_pnl", 0) or 0) > 0.4
             and int(STATE.get("scale_outs", 0)) == 1
             and FUNNEL.get("scale-out", 0) >= 1
             and len(stub.stop_calls) == stops_before_so + 1)
    check("بيع جزئي عند +0.5%: نصف يُقفل ربحاً + وقف الباقي يُعاد بكمية الباقي", so_ok)
    on_book("TSTUSDT", {"b": "101.00", "B": "5", "a": "101.01", "A": "5"})
    on_book("TSTUSDT", {"b": "100.70", "B": "5", "a": "100.71", "A": "5"})   # لمس الوقف المتحرك
    for _ in range(10):
        await asyncio.sleep(0)
    so_final = (not STATE["positions"]
                and STATE["metrics"]["wins"] == wins_before_so + 1
                and STATE["metrics"]["realized_pnl"] > 0.4
                and bool(STATE["trade_log"])
                and float(STATE["trade_log"][-1].get("fees", 0) or 0) > 0
                and float(STATE["trade_log"][-1].get("partial", 0) or 0) > 0.4)
    check("إغلاق ما بعد البيع الجزئي: PnL صافٍ = جزئي + متبقٍ − كل الرسوم (وعي بالرسوم حي)", so_final)
    globals()["SCALE_OUT_ENABLED"] = saved_scale_out

    # 15ث) دخول الصانع: LIMIT_MAKER عند أفضل شراء + مهلة إلغاء + تنفيذ بالأحداث
    saved_maker, saved_ttl, saved_evt = MAKER_ENTRIES, MAKER_TTL_SEC, ENTRY_EVENT_TIMEOUT
    globals()["MAKER_ENTRIES"] = True
    globals()["MAKER_TTL_SEC"] = 0.3
    globals()["ENTRY_EVENT_TIMEOUT"] = 0.4     # الواتش دوغ يصمت بلا ضجيج بعد نهاية الفحص
    ORDER_TS.clear()
    maker_signal = dict(signal_sniper)
    maker_signal["trigger"] = "impulse"
    maker_signal["setup_id"] = "TSTUSDT@impulse@maker1"
    maker_signal["maker_price"] = 98.6
    stops_before_m = len(stub.stop_calls)
    STATE.setdefault("last_entry_at", {}).pop("TSTUSDT", None)   # تهدئة الاختبارات السابقة لا تحجب
    maker_placed = await process_signal(maker_signal)
    check("الصانع: أمر LIMIT_MAKER عند أحدث أفضل شراء بدل MARKET (بلا تنفيذ فوري)",
          maker_placed and stub.order_calls[-1]["type"] == "LIMIT_MAKER"
          and abs(float(stub.order_calls[-1]["price"]) - float(BOOK["TSTUSDT"]["bid"])) < 1e-9
          and len(STATE["pending_entries"]) == 1
          and next(iter(STATE["pending_entries"].values())).get("maker") is True)
    cid_m = next(iter(STATE["pending_entries"]))
    oid_m = STATE["pending_entries"][cid_m]["order_id"]
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid_m, "i": oid_m,
                              "S": "BUY", "x": "TRADE", "X": "CANCELED",
                              "l": "0", "L": "0", "z": "0", "Z": "0"})
    check("الصانع: إلغاء بلا تنفيذ ⇒ لا مركز ولا وقف (الإشارة تُسقط بأمان)",
          not STATE["pending_entries"] and not STATE["positions"]
          and len(stub.stop_calls) == stops_before_m)
    STATE["pending_entries"]["MKR2"] = {"symbol": "TSTUSDT", "client_order_id": "MKR2",
                                        "order_id": 677, "maker": True, "phase": "placed"}
    arm_maker_ttl("MKR2", "TSTUSDT", 677)
    await asyncio.sleep(0.55)
    check("الصانع: مهلة TTL ⇒ إلغاء تلقائي لأمر لم يُنفَّذ (الزخم فات)",
          677 in stub.cancel_calls and FUNNEL.get("maker-expired", 0) >= 1)
    await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": "MKR2", "i": 677,
                              "S": "BUY", "x": "TRADE", "X": "CANCELED",
                              "l": "0", "L": "0", "z": "0", "Z": "0"})
    STATE.pop("MKR2", None)
    STATE.setdefault("last_entry_at", {}).pop("TSTUSDT", None)
    ORDER_TS.clear()
    stub.maker_reject = True                       # كتاب مقفول: أمر الصانع كان سيعبر
    maker_signal["setup_id"] = "TSTUSDT@impulse@makerR"
    maker_placed_r = await process_signal(maker_signal)
    stub.maker_reject = False
    check("الصانع: رفض -2010 (كتاب مقفول) ⇒ إشارة تُسقط بأمان وتُعدّ",
          maker_placed_r is False and not STATE["pending_entries"]
          and FUNNEL.get("maker-reject", 0) >= 1)
    ORDER_TS.clear()
    maker_signal["setup_id"] = "TSTUSDT@impulse@maker2"
    maker_placed2 = await process_signal(maker_signal)
    cid_m2 = next(iter(STATE["pending_entries"])) if STATE["pending_entries"] else None
    oid_m2 = STATE["pending_entries"][cid_m2]["order_id"] if cid_m2 else None
    if cid_m2 and oid_m2:
        await process_user_event({"e": "executionReport", "s": "TSTUSDT", "c": cid_m2, "i": oid_m2,
                                  "S": "BUY", "x": "TRADE", "X": "FILLED",
                                  "l": "0.109", "L": "98.6", "z": "0.109", "Z": "10.7474"})
    maker_pos = next(iter(STATE["positions"].values()), {}) if STATE["positions"] else {}
    check("الصانع: تنفيذ أمر الصانع عبر executionReport يبني مركزاً بوقف صلب كامل",
          maker_placed2 and len(STATE["positions"]) == 1
          and abs(float(maker_pos.get("entry", 0)) - 98.6) < 1e-9
          and len(stub.stop_calls) == stops_before_m + 1)
    STATE["positions"].clear()
    globals()["MAKER_ENTRIES"], globals()["MAKER_TTL_SEC"] = saved_maker, saved_ttl
    globals()["ENTRY_EVENT_TIMEOUT"] = saved_evt
    globals()["MAKER_ENTRIES"] = saved_maker_legacy

    EXIT_CLAIMED.clear(); EXIT_PENDING.clear()
    globals()["DRY_RUN"], globals()["AUTO_TRADE"] = saved_dry, saved_auto
    globals()["BINANCE_API_KEY"], globals()["BINANCE_API_SECRET"] = "", ""
    globals()["REST"] = real_rest

    # 16ت) الحاكم: المتتالية والساعة واليوم — الحكيم في متى يتوقف
    STATE = default_state()
    STATE["metrics"]["consecutive_losses"] = GOV_MAX_STREAK
    reason_g1 = governor_update(-0.5)
    blocked_g1, why_g1 = governor_blocked()
    gates_gov = _entry_gates_open("TSTUSDT")
    check("الحاكم: خسائر متتالية ⇒ إيقاف مؤقت يغلق البوابات",
          blocked_g1 and "streak" in reason_g1 and "streak" in why_g1 and gates_gov is False)
    STATE["gov"] = dict(_gov_default())
    STATE["metrics"]["consecutive_losses"] = 0
    reason_g2 = governor_update(-2.5)
    blocked_g2, why_g2 = governor_blocked()
    check("الحاكم: خسارة الساعة ≤ -2$ ⇒ إيقاف 30 دقيقة (لا تداول انتقامي)",
          blocked_g2 and "hourly" in reason_g2 and "hourly" in why_g2)
    STATE["gov"] = dict(_gov_default())
    saved_hourly_cap = GOV_HOURLY_LOSS_USD
    globals()["GOV_HOURLY_LOSS_USD"] = Decimal("999")   # عزل فرع اليوم عن فرع الساعة
    reason_g3 = governor_update(-5.0)
    blocked_g3, why_g3 = governor_blocked()
    check("الحاكم: خسارة اليوم ≤ -5$ ⇒ إيقاف حتى الغد (حماية رأس المال)",
          blocked_g3 and "daily" in reason_g3 and "daily" in why_g3)
    globals()["GOV_HOURLY_LOSS_USD"] = saved_hourly_cap
    STATE["gov"] = dict(_gov_default())

    # 16ظ) الوضع الظلي: مختبر أفضلية الزناد بلا أي أوامر (V6.2)
    SHADOW_THROTTLE.clear()
    STATE = default_state()
    FLOW.clear()
    flow_add("TSTUSDT", time.time(), 100.0, 0.0)
    FLOW["TSTUSDT"]["price"] = 100.0
    FLOW["TSTUSDT"]["epoch"] = time.time()
    BOOK["TSTUSDT"] = {"bid": 100.0, "ask": 100.01, "bid_qty": 5.0, "ask_qty": 5.0,
                       "bid_vol": 500.0, "ask_vol": 500.0, "spread_pct": 0.01,
                       "ts": time.monotonic()}
    shadow_open({"symbol": "TSTUSDT", "trigger": "impulse", "setup_id": "sh1", "atr_1m": 1.0})
    sid1 = next(iter(STATE["shadow"]["open"]))
    pos1 = STATE["shadow"]["open"][sid1]
    check("الظلي: إشارة ⇒ مركز افتراضي (12$) بوقف ATR×1.5 — بلا أي أمر حقيقي",
          len(STATE["shadow"]["open"]) == 1 and abs(pos1["entry"] - 100.0) < 1e-9
          and abs(pos1["qty"] - 0.12) < 1e-9 and abs(pos1["stop"] - 98.5) < 1e-9)
    shadow_on_price("TSTUSDT", 100.50)     # +0.5% ⇒ بيع جزئي افتراضي + تسليح التعادل
    pos1 = STATE["shadow"]["open"][sid1]
    check("الظلي: بيع جزئي افتراضي عند +0.4% والتعادل يُسلَّح بنفس قواعد الحقيقي",
          pos1.get("scaled") and abs(pos1["qty"] - 0.06) < 1e-9 and pos1["trail_armed"])
    shadow_on_price("TSTUSDT", 100.20)     # لمس وقف التتبّع الافتراضي (القمة 100.50)
    check("الظلي: خروج رابح صافٍ بعد الرسوم مُقيد على زناده",
          len(STATE["shadow"]["open"]) == 0
          and STATE["shadow"]["stats"]["impulse"]["closed"] == 1
          and STATE["shadow"]["stats"]["impulse"]["wins"] == 1
          and STATE["shadow"]["stats"]["impulse"]["net"] > 0)
    SHADOW_THROTTLE.clear()
    shadow_open({"symbol": "TSTUSDT", "trigger": "impulse", "setup_id": "sh2", "atr_1m": 1.0})
    shadow_on_price("TSTUSDT", 98.0)       # وقف صلب افتراضي
    check("الظلي: خسارة الوقف الصلب تُقيد على الزناد نفسه",
          STATE["shadow"]["stats"]["impulse"]["closed"] == 2
          and STATE["shadow"]["stats"]["impulse"]["losses"] == 1)
    SHADOW_THROTTLE.clear()
    shadow_open({"symbol": "TSTUSDT", "trigger": "flow", "setup_id": "sh3", "atr_1m": 1.0})
    _sid3 = next(iter(STATE["shadow"]["open"]))
    STATE["shadow"]["open"][_sid3]["opened_at"] = time.time() - 300.0
    shadow_on_price("TSTUSDT", 100.0)
    check("الظلي: الوقف الزمني يُغلق اللازخم ويقيد زناده",
          len(STATE["shadow"]["open"]) == 0
          and STATE["shadow"]["stats"]["flow"]["closed"] == 1)
    report_s = shadow_report_text()
    check("الظلي: لوحة /shadow تعرض إحصاء الزنادات بعد الرسوم",
          "الوضع الظلي" in report_s and "impulse" in report_s and "flow" in report_s)
    STATE["shadow"] = {"stats": {}, "open": {}, "history": [], "skipped": 0}
    SHADOW_SYMS.clear()

    # 16ظ2) مسبار القنّاص الظلي يتجاوز بوابات المحرك الحقيقي (V6.2.1 — سلامة التجربة)
    STATE.setdefault("last_entry_at", {})["TSTUSDT"] = time.time()   # تهدئة قائمة ⇒ بوابات مغلقة
    TICKS.clear()
    now_ts = time.time()
    for ts, px in [(now_ts - 12, 100.0), (now_ts - 1, 98.6)]:
        tick_add("TSTUSDT", ts, px)
    BOOK["TSTUSDT"] = {"bid": 98.6, "ask": 98.61, "bid_qty": 3.0, "ask_qty": 1.0,
                       "bid_vol": 300.0, "ask_vol": 100.0, "spread_pct": 0.01,
                       "ts": time.monotonic()}
    check("بوابات حقيقية مغلقة (تهدئة) ⇒ القنّاص الحقيقي لا يقرر",
          sniper_decision("TSTUSDT") is None)
    SHADOW_ATTEMPT.clear()
    SHADOW_THROTTLE.clear()
    shadow_sniper_tick("TSTUSDT")
    sh_probe = (STATE.get("shadow", {}).get("open") or {})
    probe_trig = next(iter(sh_probe.values()), {}).get("trigger")
    check("المسبار الظلي يفتح صفقة قياس رغم بوابات التنفيذ (عينات بلا فجوات مُحيّزة)",
          len(sh_probe) == 1 and probe_trig == "flash-crash")
    STATE.setdefault("last_entry_at", {}).pop("TSTUSDT", None)
    STATE["shadow"] = {"stats": {}, "open": {}, "history": [], "skipped": 0}
    SHADOW_SYMS.clear()

    # 16ظ3) معقم دفتر الظل: بيانات فاسدة من state.json قديم لا تفجّر الإقلاع
    dirty = {"stats": {"impulse": {"opened": "7", "closed": None, "net": "1.5", "wins": 3,
                                   "losses": "x", "gross": "2", "fees": 0.5},
                      "bad": "فساد"},
             "open": None, "history": "ليست قائمة", "skipped": "9"}
    clean = normalize_shadow(dirty)
    st_imp = clean["stats"].get("impulse", {})
    check("الظلي: المعقم ينظف دفتراً فاسداً (أعداد صحيحة وأرباح عائمة وسجل مقصوص)",
          st_imp.get("opened") == 7 and st_imp.get("closed") == 0
          and abs(st_imp.get("net", 0.0) - 1.5) < 1e-9 and st_imp.get("losses") == 0
          and "bad" not in clean["stats"] and clean["open"] == {}
          and clean["history"] == [] and clean["skipped"] == 9
          and normalize_shadow(None) == {"stats": {}, "open": {}, "history": [], "skipped": 0})
    FLOW.clear()

    # 16) القواطع: قاطع BTC يمنع قنصة + DRY-RUN + بوابة LIVE
    STATE = default_state()
    ORDER_TS.clear()
    stub2 = _StubRest()
    globals()["BINANCE_API_KEY"] = "TEST_KEY"; globals()["BINANCE_API_SECRET"] = "TEST_SECRET"
    globals()["DRY_RUN"] = False; globals()["AUTO_TRADE"] = True
    globals()["REST"] = stub2
    BTC_CTX["live"] = 98.0          # هبوط ~2% خلال النافذة
    veto_before = veto_reason("TSTUSDT")
    blocked_signal = await process_signal(signal_sniper)
    check("قاطع BTC يمنع تنفيذ القنصة (صفر أوامر)",
          veto_before.startswith("btc-drop") and blocked_signal is False and not stub2.order_calls)
    BTC_CTX["live"] = 100.0
    globals()["DRY_RUN"], globals()["AUTO_TRADE"] = True, saved_auto
    blocked_dryrun = await process_signal(signal_sniper)
    globals()["DRY_RUN"], globals()["AUTO_TRADE"] = saved_dry, saved_auto
    globals()["BINANCE_API_KEY"], globals()["BINANCE_API_SECRET"] = "", ""
    globals()["REST"] = real_rest
    check("DRY-RUN لا يرسل أوامر (القنصة تُسجَّل فقط)",
          blocked_dryrun is False and not stub2.order_calls)
    saved_env, saved_confirm = BINANCE_ENV, LIVE_CONFIRM
    globals()["BINANCE_ENV"] = "live"; globals()["LIVE_CONFIRM"] = ""
    globals()["DRY_RUN"] = False; globals()["AUTO_TRADE"] = True
    globals()["BINANCE_API_KEY"] = "K"; globals()["BINANCE_API_SECRET"] = "S"
    gate_no_confirm = live_execution_allowed() is False
    globals()["LIVE_CONFIRM"] = "I_UNDERSTAND_SPOT_RISK"
    gate_confirm = live_execution_allowed() is True
    globals()["BINANCE_ENV"] = saved_env; globals()["LIVE_CONFIRM"] = saved_confirm
    globals()["BINANCE_API_KEY"], globals()["BINANCE_API_SECRET"] = "", ""
    globals()["DRY_RUN"], globals()["AUTO_TRADE"] = saved_dry, saved_auto
    check("بوابة LIVE مشروطة بتأكيد نصي (I_UNDERSTAND_SPOT_RISK)", gate_no_confirm and gate_confirm)

    # 16ب) القواطع بعد التنقيط: سبريد + قدم البيانات
    BOOK["TSTUSDT"] = {"bid": 109.0, "ask": 111.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1090.0, "ask_vol": 1110.0, "imbalance": 0.5,
                       "spread_pct": 1.8, "ts": time.monotonic()}
    check("سبريد عريض يلغي القنصة", veto_reason("TSTUSDT") == "spread")
    BOOK["TSTUSDT"] = {"bid": 109.9, "ask": 110.0, "bid_qty": 10.0, "ask_qty": 10.0,
                       "bid_vol": 1099.0, "ask_vol": 1100.0, "imbalance": 0.5,
                       "spread_pct": 0.0909, "ts": time.monotonic()}
    FLOW["TSTUSDT"] = {"buy": 9.0, "sell": 1.0, "ts": time.time() - 99.0,
                       "epoch": time.time() - 99.0, "price": 110.0, "buckets": deque()}
    BOOK["TSTUSDT"]["ts"] = time.monotonic() - 99.0
    check(f"بيانات أقدم من {MAX_STALE_SEC:.0f}ث → إلغاء (حارس Latency Spike)",
          veto_reason("TSTUSDT") == "stale-tick")
    BOOK["TSTUSDT"]["ts"] = time.monotonic()
    FLOW["TSTUSDT"]["epoch"] = time.time()
    check("بيانات طازجة → لا veto", veto_reason("TSTUSDT") is None)
    FLOW.clear()

    # 17) Telegram AI Commander: الأزرار + مسارا Gemini + الصمت + /reset + إشعار البدء
    kb = main_keyboard()
    flat_kb = [btn for row in kb for btn in row]
    check("زرا AI Commander في القائمة الرئيسية",
          any(b["callback_data"] == "/autopsy" and "تشريح" in b["text"] for b in flat_kb)
          and any(b["callback_data"] == "/insight" and "تحليل السوق" in b["text"] for b in flat_kb))
    saved_token, saved_chat, saved_dry2 = TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN = "fake-token", "42", False
    sent_payloads = []
    real_tg_api = tg_api
    real_gemini_ask = gemini_ask

    async def _spy_tg(method, payload=None, retries=3):
        if method == "sendMessage":
            sent_payloads.append(payload)
        return {"message_id": 1}

    async def _fake_gemini_ask(prompt, json_mode=False, timeout=None):
        if "آخر 5 صفقات خاسرة" in prompt:
            return "التشخيص الكمي في ثلاث جمل.", None
        if "الانهيارات الآن" in prompt:
            return "تحليل السوق في ثلاث جمل.", None
        return '{"breakeven_trigger_pct": 0.25, "time_stop_sec": 60, "reason": "توازن بين السرعة والأرباح"}', None

    STATE["trade_log"] = [{"ts": "test", "symbol": "TSTUSDT", "pnl": -0.15, "duration_sec": 45.0,
                           "reason": "وقف زمني (45ث بلا زخم)", "entry": 100.0, "exit": 99.85,
                           "trigger": "flash-crash"}]
    globals()["tg_api"] = _spy_tg
    globals()["gemini_ask"] = _fake_gemini_ask
    globals()["save_state"] = _noop_save
    before_count = len(sent_payloads)
    auto_blocked = await send_message("رسالة تلقائية — يجب أن تُحجب") is False \
        and len(sent_payloads) == before_count
    await handle_callback({"callback_query": {"id": "1", "data": "/autopsy",
                                              "message": {"chat": {"id": "42"}}}})
    for _ in range(12):
        await asyncio.sleep(0)
    autopsy_ok = any("تشريح الصفقات (Gemini)" in (p.get("text") or "")
                     and "التشخيص الكمي" in (p.get("text") or "") for p in sent_payloads)
    await handle_callback({"callback_query": {"id": "2", "data": "/insight",
                                              "message": {"chat": {"id": "42"}}}})
    for _ in range(12):
        await asyncio.sleep(0)
    insight_ok = any("تحليل السوق (Gemini)" in (p.get("text") or "")
                     and "تحليل السوق في ثلاث جمل" in (p.get("text") or "") for p in sent_payloads)
    check("زر /autopsy يرد بتشخيص Gemini العربي", autopsy_ok)
    check("زر /insight يرد بتحليل Gemini العربي", insight_ok)
    STATE["metrics"] = {"trades": 9, "realized_pnl": -3.5, "wins": 4, "losses": 5, "consecutive_losses": 2}
    await handle_command("/reset", "42")
    reset_ok = (STATE["metrics"] == {"trades": 0, "realized_pnl": 0.0, "wins": 0, "losses": 0,
                                     "consecutive_losses": 0}
                and any((p.get("text") or "") == RESET_REPLY for p in sent_payloads))
    check("أمر /reset: تصفير الإحصائيات + الرد الحرفي", reset_ok)

    # 17ب) Auto-Tune: JSON مفروض → STATE → حفظ → إشعار Telegram
    STATE["metrics"] = {"trades": 5, "wins": 1, "losses": 4, "realized_pnl": -2.0, "consecutive_losses": 2}
    applied = await gemini_autotune_once()
    tune_ok = (applied is True and abs(float(STATE["be_trigger_pct"]) - 0.25) < 1e-9
               and int(STATE["time_stop_sec"]) == 60
               and isinstance(STATE["last_tune"], dict)
               and any("Auto-Tune" in (p.get("text") or "") for p in sent_payloads))
    check("Auto-Tune يطبّق JSON المفروض في STATE ويُخطِر Telegram", tune_ok)
    LAST_AI_REPLY_AT.clear()
    await handle_command("/autopsy", "42")
    for _ in range(12):
        await asyncio.sleep(0)
    await handle_command("/autopsy", "42")   # تكرار فوري ⇒ يجب أن يُخنَق
    for _ in range(6):
        await asyncio.sleep(0)
    throttle_ok = any("متكرر بسرعة" in (p.get("text") or "") for p in sent_payloads)
    LAST_AI_REPLY_AT.clear()
    await handle_command("/insight", "42")
    for _ in range(12):
        await asyncio.sleep(0)
    commands_ok = sum(1 for p in sent_payloads if "تشريح" in (p.get("text") or "")) >= 2 \
        and sum(1 for p in sent_payloads if "تحليل السوق" in (p.get("text") or "")) >= 2
    check("أمرا /autopsy و/insight النصيان مدعومان + خنق التكرار السريع", commands_ok and throttle_ok)
    STARTUP_NOTIFIED = False
    notify_first = await notify_startup()
    notify_again = await notify_startup()
    startup_ok = (notify_first is True and notify_again is False
                  and any((p.get("text") or "") == STARTUP_TEXT for p in sent_payloads))
    check("إشعار البدء: مرة واحدة بالضبط بالنص الحرفي", startup_ok)
    globals()["tg_api"] = real_tg_api
    globals()["gemini_ask"] = real_gemini_ask
    globals()["save_state"] = real_save
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DRY_RUN = saved_token, saved_chat, saved_dry2
    check("الوضع الصامت: لا رسائل تلقائية — ردود الأوامر والإشعارات المصرّح بها فقط", auto_blocked)

    # 18) /status الحرفية + تقرير السياق مع القنّاص
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
    ctx_text_out = context_text()
    check("تقرير السياق يعرض القاطع وVR والتهدئة والقنّاص",
          "BTC" in ctx_text_out and "VR" in ctx_text_out
          and f"{COOLDOWN_NORMAL}ث" in ctx_text_out and "القنّاص" in ctx_text_out
          and f"{FLASH_DROP_PCT}" in ctx_text_out)

    # 19) بنية V6: إعدام المحرك البنيوي + اشتراكات HFT + مكونات الدماغ
    check("إعدام كامل لمحرك 5m البنيوي وأسمائه",
          all(name not in globals() for name in (
              "compute_score", "detect_mss", "detect_fvg", "on_signal_candle_closed",
              "_evaluate_frame", "build_signal", "update_trend_ema", "ema_series", "ema_last",
              "SCORE_MSS", "SCORE_FVG", "SCORE_EMA", "SCORE_TRIGGER", "SCORE_MOMENTUM_BONUS",
              "FLOW_CHECK_EVERY", "READY", "SIGNAL_INTERVAL", "TREND_INTERVAL", "EMA_TREND_PERIOD",
              "MIN_ATR_PCT", "VR_EXTREME", "WICK_REJECT_RATIO", "MSS_LOOKBACK", "FVG_LOOKBACK")))
    streams = MarketStreamHub.streams_for("TSTUSDT")
    check("اشتراكات HFT: aggTrade + bookTicker + kline_1m فقط (بلا شموع إشارة)",
          "tstusdt@aggTrade" in streams and "tstusdt@bookTicker" in streams
          and "tstusdt@kline_1m" in streams
          and not any("kline_5m" in s or "kline_15m" in s for s in streams))
    check("محرك القنّاص والدماغ الخطين مركّبان بالكامل",
          all(name in globals() for name in (
              "tick_add", "tick_window_stats", "flash_drop_pct", "buy_wall_ratio",
              "buy_wall_confirmed", "build_sniper_signal", "sniper_decision",
              "handle_sniper_decision", "gemini_configure", "gemini_available", "gemini_ask",
              "parse_json_loose", "clamp_tuned_params", "build_tune_prompt",
              "gemini_autotune_loop", "gemini_autotune_once", "collect_losing_trades",
              "build_autopsy_prompt", "build_insight_prompt", "autopsy_report", "insight_report",
              "get_be_trigger_pct", "get_time_stop_sec",
              "spawn_ai_task", "ai_throttled", "escape")))
    check("محرك الخروج الهجين محفوظ حرفياً وواجهات OCO مُزالة",
          all(name in globals() for name in ("trailing_plan", "on_price_update",
                                             "trigger_trailing_exit", "place_hard_stop",
                                             "cancel_hard_stop"))
          and all(name not in globals() for name in ("place_initial_oco", "oco_levels")))

    # 20) Backoff + Dust
    b = WS_RECONNECT_MIN
    growth = []
    for _ in range(8):
        b, delay = next_backoff(b)
        growth.append(b)
    check("Backoff متزايد بسقف", abs(growth[0] - 2.0) < 1e-9 and growth[-1] == WS_RECONNECT_MAX)
    details = [
        {"asset": "TST", "amountFree": "12", "minTransferAmount": "10"},
        {"asset": "ALPHA", "amountFree": "5", "minTransferAmount": "10"},
        {"asset": "BNB", "amountFree": "0.5", "minTransferAmount": "0.001"},
    ]
    check("انتقاء Dust (مؤهل ضمن أصول البوت فقط)", pick_dust_assets(details, {"TST"}) == ["TST"])

    # تنظيف
    STATE = default_state()
    CANDLES.clear(); BOOK.clear(); FLOW.clear(); ORDERS.clear()
    SETUPS.clear(); WHALES.clear(); EXIT_CLAIMED.clear(); EXIT_PENDING.clear()
    TICKS.clear(); PENDING_SNIPES.clear(); HFT_ATTEMPT.clear()
    SPRAY_BASE.clear(); SPRAY_ATTEMPT.clear(); SPREAD_MEM.clear()
    FLOW_REV_AT.clear(); SCALE_PENDING.clear(); ORDER_TS.clear()
    SHADOW_THROTTLE.clear(); SHADOW_ATTEMPT.clear(); SHADOW_SYMS.clear()
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
    gemini_configure()     # الدماغ الذكي: تهيئة مبكرة متسامحة (تعطل آمن بلا مفتاح)
    connector = aiohttp.TCPConnector(limit=HTTP_CONCURRENCY, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector,
                                     headers={"User-Agent": "NOVA-AI-HFT/6.0"}) as session:
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
            asyncio.create_task(gemini_autotune_loop(), name="gemini-autotune-loop"),
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
            f"تشغيل NOVA V6.2 Hybrid AI-HFT [رشاش + قنّاص] | {regime_text()} | Spot فقط | "
            f"التنفيذ حدثي بالكامل: aggTrade + bookTicker (لا شموع إشارة ولا إغلاقات) | "
            f"أفضل {TOP_N_SYMBOLS} زوجاً (تحديث كل {UNIVERSE_REFRESH_EVERY}ث) | "
            f"WebSocket: kline_1m (ATR فقط)+aggTrade+bookTicker+{BTC_CONTEXT_SYMBOL.lower()}@kline_1m"
            f"{' + User Data Stream' if trading_enabled else ''} | "
            f"الزناد: هبوط ≥ {FLASH_DROP_PCT}% خلال {TICK_MEMORY_SEC:.0f}ث + جدار شراء > {BUY_WALL_RATIO:g}x bid/ask | "
            f"مخاطرة {TARGET_RISK_USD}$/صفقة بسقف مركز {MAX_POSITION_NOTIONAL_USD}$ | "
            f"وقف طوارئ ATR(1m)×{HARD_STOP_ATR_MULT:g} بسقف {SL_MAX_PCT}% + خروج هجين "
            f"(تعادل +{get_be_trigger_pct():g}% ثم تتبّع {TRAIL_WIDE_PCT:g}/{TRAIL_TIGHT_PCT:g}%) | "
            f"وقف زمني {get_time_stop_sec()}ث (Hit & Run) | "
            f"تهدئة ديناميكية {COOLDOWN_FAST}/{COOLDOWN_NORMAL}/{COOLDOWN_SLOW}ث | "
            f"قاطع BTC بهبوط {BTC_DROP_PCT}%/{BTC_DROP_WINDOW_MIN}د | "
            f"حتى {MAX_OPEN_POSITIONS} مركزاً ({MAX_POSITIONS_PER_SYMBOL}/عملة) | "
            f"Gemini Auto-Tune كل {GEMINI_TUNE_EVERY // 3600}س ({'مفعّل' if gemini_available() else 'معطّل'}) | "
            f"Dust→BNB كل {DUST_SWEEP_EVERY // 3600}س | "
            f"التنفيذ: {execution_line} | الحاكم: {GOV_MAX_STREAK} متتالية/{GOV_HOURLY_LOSS_USD}$ ساعة/"
            f"{GOV_DAILY_LOSS_USD}$ يوم | ميزانية أوامر {ORDER_BUDGET_MAX}/{ORDER_BUDGET_WINDOW:.0f}ث"
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
