"""
NOVA v5 — Six-Factor Scoring (M5, مُقفل 50/70/85)
==================================================
المصدر: KB §4.1 — يحوّل شروط الدخول إلى درجة 0–100، ثم يحدّد حجم دخول ذكي:
    < 50  → لا تداول
    50–69 → 0% (رفض)
    70–84 → 50% (نصف)
    ≥ 85  → 100% (كامل)
"""

from __future__ import annotations
from typing import Dict, Optional


def six_factor_score(cfg, *, bullish: bool,
                     high: float, low: float, open_: float, close: float,
                     atr_value: float, volume: float, vol_ma: float,
                     ema50: float, touches: int, pierce: float) -> Optional[float]:
    """يُعيد درجة 0–100، أو None إذا كان المدخل غير صالح."""
    rng = max(high - low, 1e-12)
    atr_v = max(atr_value, 1e-12)

    # عليّة الرفض (wick): نسبة الذيل إلى النطاق
    wick = abs(close - low) / rng if bullish else abs(high - close) / rng
    # عمق الاختراق (atr)
    atr_factor = min(pierce / atr_v, 1.0)
    # اندفاع الحجم (vol) — منقوص الحد حتى 2×
    vol_factor = min(volume / max(vol_ma, 1e-12) / 2.0, 1.0) if vol_ma > 0 else 0.0
    # الإغلاق عبر المستوى (body)
    dir_body = (close - open_) if bullish else (open_ - close)
    body_factor = min(max(dir_body, 0.0) / rng, 1.0)
    # الامتداد عن الاتجاه (ema) — وقود الإرجاع
    ema_factor = min(abs(close - ema50) / (3.0 * atr_v), 1.0)
    # مجموعة التوقف المتحد (eq)
    eq_factor = min(touches / 3.0, 1.0)

    c = dict(wick=wick, atr=atr_factor, vol=vol_factor, body=body_factor,
             ema=ema_factor, eq=eq_factor)
    w = cfg.zw_weights
    total_w = sum(w.values())
    if total_w <= 0:
        return None
    score = 100.0 * sum(w[k] * c[k] for k in c) / total_w
    return score


def size_multiplier(cfg, score: float) -> float:
    """0.0 / 0.5 / 1.0 حسب درجة الثقة (مُقفل 50/70/85)."""
    if score < cfg.score_reject:
        return 0.0
    if score < cfg.score_half:
        return 0.0          # 50–69 ⇒ رفض
    if score < cfg.score_full:
        return 0.5          # 70–84 ⇒ نصف
    return 1.0              # ≥85 ⇒ كامل


def tier_label(score: float) -> str:
    if score < 50:
        return "🟥 رفض (ثقة منخفضة)"
    if score < 70:
        return "🟧 رفض (تحت الحد)"
    if score < 85:
        return "🟨 نصف حجم (ثقة متوسطة)"
    return "🟩 حجم كامل (ثقة عالية)"
