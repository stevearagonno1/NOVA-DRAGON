"""
NOVA v5 — إدارة المخاطر والتنفيذ الصارم (مُحافَظ عليه من v4.0.2)
================================================================
الأهداف: حماية رأس المال، خروج بربحٍ صافٍ بعد العمولة، منع الانزلاق.
(يُستبدل الحجم الثابت فقط بالتخضيم الديناميكي من §7 — الباقي كما هو.)
"""

from __future__ import annotations
from typing import Dict, Optional


def compute_stop_target(cfg, entry: float, atr_value: float):
    """
    وقف الخسارة = 1.15·ATR (لكن ضمن [SL_MIN, SL_MAX]% لمنع الضجيج/الفادح).
    الهدف = وقف لرفع نسبة مخاطرة:عائد (2R أوليّ) لكن لا يقل عن MIN_TARGET%.
    """
    if entry <= 0 or atr_value <= 0:
        return None
    stop_dist = cfg.sl_atr_mult * atr_value
    stop_pct = stop_dist / entry * 100.0
    stop_pct = max(cfg.sl_min_pct, min(cfg.sl_max_pct, stop_pct))
    stop = entry * (1.0 - stop_pct / 100.0)
    # الهدف: ضعف المسافة (2R) على الأقل، لكن لا يقل عن MIN_TARGET (أكبر من العمولة)
    target_dist_pct = max(2.0 * stop_pct, cfg.target_min_pct)
    target = entry * (1.0 + target_dist_pct / 100.0)
    if target - entry <= entry * cfg.target_min_pct / 100.0:
        return None  # الهدف لا يغطّي العمولة — لا صفقة
    return {"stop": stop, "target": target, "stop_pct": stop_pct, "target_pct": target_dist_pct}


def break_even_lock_price(cfg, entry: float) -> float:
    """الوقف يقفز فوق الدخول بصافٍ موجب (يغطي العمولة)."""
    return entry * (1.0 + cfg.breakeven_lock_pct / 100.0)


def time_stop_due(cfg, age_sec: float, gain_pct: float,
                  be_armed: bool, trailing_active: bool) -> bool:
    """خروج زمني ذكي: تُغلق الصفقة إذا مرّ الوقت بلا ربحٍ يتجاوز الذروة."""
    if be_armed or trailing_active:
        return False
    if age_sec >= cfg.time_stop_sec and gain_pct <= 0.10:
        return True
    return False


def fee_net(cfg, entry_quote: float, exit_quote: float) -> float:
    """صافي الربح بعد عمولة Binance (~0.20% ذهاباً وإياباً)."""
    cost = (entry_quote + exit_quote) * (cfg.fee_bps / 10000.0)
    return exit_quote - entry_quote - cost


def position_qty(cfg, score_mult: float, price: float, risk_pct: float = 0.0) -> float:
    """حجم المركزي = قيمة اسمية متدرّجة حسب درجة الثقة. يراعي الحفاظ على رأس المال."""
    notional = cfg.trade_notional_usd * score_mult
    if price <= 0:
        return 0.0
    return notional / price


def governor_should_pause(cfg, streak: int, cooldown_left: float) -> bool:
    """حاكم العملة: 3 خسائر متتالية ⇒ إيقاف مؤقت (10 دقائق)."""
    return int(streak) >= cfg.gov_max_losses and cooldown_left > 0
