"""
NOVA v5 — محفّز الدخول (M3): Sweep → MSS → FVG/Tap
====================================================
مُطوَّر من MSS/FVG الحالي مع إضافة:
  - Liquidity Sweep / SFP (KB §2.2)
  - Displacement gate (|c−o| > 0.6·ATR) (KB §2.1)
  - FVG Zone-Tap (KB §2.3)
بنية تعمل على بيانات شموع مغلقة (slow state) + tick (fast path).
"""

from __future__ import annotations
from typing import Dict, List, Optional


def detect_sweep(frame: Dict, ss_low: Optional[float], ss_high: Optional[float]) -> Optional[bool]:
    """
    Swift-level Sweep: اختراق ذروة ثم إغلاق خلفها.
    يُعيد True إذا سُحبت سيولة أسفل قاعٍ (sweep_low)، False إذا كانت من قمة.
    """
    close, low, high = frame["close"], frame["low"], frame["high"]
    wick_below = ss_low is not None and low < ss_low and close > ss_low
    if wick_below:
        return True
    wick_above = ss_high is not None and high > ss_high and close < ss_high
    if wick_above:
        return False
    return None  # لا سحب


def detect_mss(frame: Dict, cfg) -> Optional[Dict]:
    """
    Market Structure Shift: إغلاق فوق آخر قمة هيكلية مع إزاحة قوية.
    (مطوَّر من منطق NOVA الحالي + Displacement 0.6·ATR)
    """
    h, l, o, c = frame["h"], frame["l"], frame["o"], frame["c"]
    n = len(c)
    if n < cfg.mss_lookback + cfg.mss_max_age + 3:
        return None
    atr_value = frame.get("atr", 0.0)
    if atr_value <= 0:
        return None
    for age in range(cfg.mss_max_age):
        i = n - 1 - age
        body = c[i] - o[i]
        rng = h[i] - l[i]
        if body <= 0 or rng <= 0:
            continue
        if body / rng < cfg.mss_body_ratio:
            continue
        if rng < cfg.mss_min_range_atr * atr_value:
            continue
        window = h[max(0, i - cfg.mss_lookback): i]
        if not window:
            continue
        prior_high = max(window)
        if o[i] <= prior_high < c[i]:
            if c[-1] <= prior_high:
                continue  # الهيكل لم يصمد — رُفض فوراً
            displacement = rng / atr_value
            if displacement < cfg.ms_displace_atr:
                continue  # كسر ضعيف (بلا إزاحة) — لا يُقبل
            return {
                "age": age, "index": i, "prior_high": prior_high,
                "close": c[i], "body": body, "range": rng,
                "displacement": displacement,
            }
    return None


def detect_fvg(frame: Dict, cfg) -> Optional[Dict]:
    """أحدث فجوة قيمة عادلة صاعدة غير معبأة (KB §2.3)."""
    h, l = frame["h"], frame["l"]
    n = len(l)
    atr_value = frame.get("atr", 0.0)
    start = max(0, n - cfg.fvg_lookback)
    best = None
    for i in range(start, n - 2):
        gap_low = h[i]
        gap_high = l[i + 2]
        if gap_high <= gap_low:
            continue
        if atr_value > 0 and (gap_high - gap_low) < cfg.fvg_min_atr * atr_value:
            continue
        mid = (gap_low + gap_high) / 2.0
        if any(l[j] <= mid for j in range(i + 3, n)):
            continue  # معبأة
        best = {"low": gap_low, "high": gap_high, "mid": mid, "index": i, "age": n - 1 - (i + 2)}
    return best


def evaluate_entry(frame: Dict, cfg, swing: Optional[SwingLike] = None) -> Optional[Dict]:
    """
    يمرّغ المحفّز: يشترط MSS + FVG + بقاء السعر فوق منتصف الفجوة.
    يُعيد dict الإشارة أو None.
    """
    mss = detect_mss(frame, cfg)
    if not mss:
        return None
    fvg = detect_fvg(frame, cfg)
    if not fvg:
        return None
    price = frame.get("live", frame["close"])
    if price <= 0 or price < fvg["mid"]:
        return None
    return {"mss": mss, "fvg": fvg}


# فئة مؤقتة للتوافق مع التلميح
class SwingLike:
    """DUCK-TYPE للـ SwingDeath (يُمرَّر اختيارياً)."""
    def is_dead(self, price, atr_value):  # pragma: no cover
        return False
