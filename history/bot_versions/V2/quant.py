"""
NOVA v5 — طبقة الكوانت (M3): تشديد إضافي قبل محفّز الدخول
========================================================
Swing Death / Touch Count (KB §3.7–§3.8) + Volatility Filter.
"""

from __future__ import annotations
import math
from typing import Dict, List


# ═══════════════════════════════════════════════════════════════
# Swing Death / Touch Count
# ═══════════════════════════════════════════════════════════════
class SwingDeath:
    """
    يحتفظ بسجل قمم/قيعان، ويعُدّ اللمسات لكل قاع.
    عند وصول القاع إلى `touches` لمسات ⇒ يُعلن "Swing Death"
    (مستوى استُهلكت سيولته) ويُحظر الشراء منه نهائياً حتى نكسرٍ جديد.
    """

    def __init__(self, max_touches: int = 3, tolerance_atr_multi: float = 0.5):
        self.max_touches = max_touches
        self.tol_multi = tolerance_atr_multi
        # القاع النشط: [sweep_low, touches]
        self.active_low: List = None  # [level, touches]
        self.active_high: List = None
        self.dead_lows: List[float] = []  # القيعان الميتة (مُستهلكة)
        self.log: Dict[str, int] = {}

    def on_swing_low(self, low: float, atr_value: float) -> bool:
        """
        يُستدعى عند تشكّل قاعٍ جديد. يُعيد True إذا كان هذا القاع "ميتاً"
        (غير قابل للشراء منه) بسبب تعدد اللمسات.
        """
        tol = self.tol_multi * (atr_value or 0.0)
        if self.active_low is not None:
            level, touches = self.active_low
            if abs(low - level) <= tol:
                touches += 1
                self.active_low[1] = touches
                self.log["touches"] = touches
                if touches >= self.max_touches:
                    self.dead_lows.append(level)
                    self.active_low = None
                    return True  # ميت — احظر الشراء منه
                return False
        self.active_low = [low, 1]
        self.log["touches"] = 1
        return False

    def is_dead(self, price: float, atr_value: float, lookback_dead: int = 4) -> bool:
        """هل السعر يرتد حقيقةً من قاعٍ ميت؟ — يمنع الشراء المكرر."""
        if not self.dead_lows or atr_value <= 0:
            return False
        tol = self.tol_multi * atr_value
        for lvl in self.dead_lows:
            if abs(price - lvl) <= tol:
                return True
        # احتفاظ بحد أقصى
        if len(self.dead_lows) > 8:
            self.dead_lows = self.dead_lows[-8:]
        return False


# ═══════════════════════════════════════════════════════════════
# Volatility Filter
# ═══════════════════════════════════════════════════════════════
class VolatilityFilter:
    """
    يمنع التداول في: تقلب شديد (> P95)، أو تقلب ميت (< P5)، أو جمود السوق.
    يتكيّف مع كل عملة عبر تاريخها (percentile).
    """

    def __init__(self, hi_pct: float = 95.0, lo_pct: float = 5.0, lookback: int = 1440):
        self.hi_pct = hi_pct
        self.lo_pct = lo_pct
        self.lookback = lookback
        self.history: List[float] = []  # سلسلة ATR% لكل شمعة مغلقة

    def push(self, atr_pct: float):
        self.history.append(atr_pct)
        if len(self.history) > self.lookback:
            self.history.pop(0)

    def _percentile(self, arr: List[float], p: float) -> float:
        if not arr:
            return 0.0
        s = sorted(arr)
        idx = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
        return s[idx]

    def all_clear(self, current_atr_pct: float) -> bool:
        if len(self.history) < 100:
            return True  # لا نملك تاريخاً كافياً — لا نعاقب
        hi = self._percentile(self.history, self.hi_pct)
        lo = self._percentile(self.history, self.lo_pct)
        if hi <= 0:
            return True
        if current_atr_pct > hi:
            return False  # ذروة تقلب — توقف
        if current_atr_pct < lo:
            return False  # تجمّد — توقف
        return True
