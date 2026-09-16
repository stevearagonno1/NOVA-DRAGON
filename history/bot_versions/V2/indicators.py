"""
NOVA v5 — المؤشرات الرياضية النقية (M2 / M4)
=============================================
كل المكوّنات O(1) أو قابلة للتحديث المتدرّج — لا إعادة حساب على كل tick.

يتضمّن:
  - ATR (Wilder) و SMA / EMA السريعة
  - Anchored Powered KAMA + Welford σ (KB §1.2)  ← بديل ALMA (مُقفل)
  - Quantized Epsilon-Midpoint Hysteresis Band (KB §1.1)  ← تصفية الضوضاء
  - Premium / Discount Zone (KB §1.19)
  - z-score نافذة منزلقة (O(1))
  - حجمية الفوليوم ومؤشرات الجودة
"""

from __future__ import annotations
import math
from typing import List, Optional


# ═══════════════════════════════════════════════════════════════
# متحركات الأطوال
# ═══════════════════════════════════════════════════════════════
def sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period or period <= 0:
        return None
    return sum(values[-period:]) / period


def ema(values: List[float], period: int) -> Optional[float]:
    if len(values) < period or period <= 0:
        return None
    alpha = 2.0 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = alpha * v + (1 - alpha) * e
    return e


def rma(values: List[float], period: int) -> List[float]:
    """Wilder smoothing — يُعيد متسلسلة بنفس طول المدخل."""
    if period <= 0:
        return list(values)
    out = [None] * len(values)
    if len(values) < period:
        return out
    acc = sum(values[:period]) / period
    out[period - 1] = acc
    for i in range(period, len(values)):
        acc = (acc * (period - 1) + values[i]) / period
        out[i] = acc
    return out


def true_ranges(highs: List[float], lows: List[float], closes: List[float]) -> List[float]:
    tr = [0.0] * len(closes)
    for i in range(len(closes)):
        if i == 0:
            tr[i] = highs[i] - lows[i]
        else:
            h, l, pc = highs[i], lows[i], closes[i - 1]
            tr[i] = max(h - l, abs(h - pc), abs(l - pc))
    return tr


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """آخر قيمة ATR (Wilder) — يُتوقّع قبول تسلسلات مكتملة."""
    tr = true_ranges(highs, lows, closes)
    smooth = rma(tr, period)
    for x in reversed(smooth):
        if x is not None:
            return float(x)
    return None


# ═══════════════════════════════════════════════════════════════
# Anchored Powered KAMA + Welford σ  (KB §1.2)
# ═══════════════════════════════════════════════════════════════
class AnchoredKAMA:
    """
    anchor = بداية الجلسة.
    ER = |p − anchor| / Σ|Δp|  (كفاءة الحركة منذ الجلسة)
    SC = ER^power                      (power=2 مُقفل)
    kama = SC·p + (1−SC)·kama_prev
    sigma = √(Σ(p−kama)²/n)  عبر Welford  (O(1)، بلا تخزين نوافذ)

    direction = sign(p − kama)  |  strength = |p − kama|/σ
    """

    def __init__(self, power: float = 2.0, anchor: float | None = None):
        self.power = power
        self.reset(anchor)

    def reset(self, anchor: float | None = None):
        self.counter = 0
        self.kama: float | None = None
        self.prev: float | None = None
        self.welford = 0.0
        self.sum_abs = 0.0
        self.anchor = anchor

    def update(self, price: float) -> float:
        if self.kama is None:
            self.anchor = price if self.anchor is None else self.anchor
            self.kama = price
            self.prev = price
            self.counter = 1
            return self.kama
        d = price - self.prev
        self.sum_abs += abs(d)
        eff = abs(price - self.anchor) / (self.sum_abs + 1e-12)
        sc = eff ** self.power
        kama_prev = self.kama
        self.kama = sc * price + (1 - sc) * kama_prev
        self.welford += (price - kama_prev) * (price - self.kama)
        self.counter += 1
        self.prev = price
        return self.kama

    @property
    def sigma(self) -> float:
        if self.counter <= 1:
            return 0.0
        return math.sqrt(max(0.0, self.welford) / self.counter)

    @property
    def direction(self) -> int:
        if self.kama is None:
            return 0
        return 1 if self.prev > self.kama else (-1 if self.prev < self.kama else 0)

    @property
    def strength(self) -> float:
        if self.kama is None or self.sigma <= 0:
            return 0.0
        return abs(self.prev - self.kama) / self.sigma


# ═══════════════════════════════════════════════════════════════
# Quantized Epsilon-Midpoint Hysteresis Band  (KB §1.1)
# ═══════════════════════════════════════════════════════════════
class EpsilonBand:
    """
    SLOW (على إغلاق شمعة): h=max(200), l=min(200), eps=2.8·ATR_prev, m=منتصف.
      upper=m+eps ، lower=m−eps.
    FAST (كل tick): عندما يخترق السعر upper ⇒ m+=eps (خطوة فوق).
                    عندما يخترق السعر lower ⇒ m−=eps (خطوة تحت).
    الإشارة: حدث «خطوة» (step) يعني أن الحركة حقيقية لا ضوضاء.
    """

    def __init__(self, fast: float = 2.8, atr_period: int = 53, range_n: int = 200):
        self.mult = fast
        self.atr_period = atr_period
        self.range_n = range_n
        self.max_hist: List[float] = []
        self.min_hist: List[float] = []
        self.atr_hist: List[float] = []   # يخزّن ATR(period) لكل شمعة مغلقة
        self.m: float | None = None
        self.eps: float | None = None
        self.last_upper: float | None = None
        self.last_lower: float | None = None
        self.steps = 0

    def on_closed_bar(self, high: float, low: float, close: float, atr_value: float | None):
        """يُستدعى عند إغلاق شمعة 1m — يُحدّث الحزام (SLOW STATE)."""
        self.max_hist.append(high)
        self.min_hist.append(low)
        if len(self.max_hist) > self.range_n:
            self.max_hist.pop(0)
            self.min_hist.pop(0)
        if atr_value is not None:
            self.atr_hist.append(atr_value)
            if len(self.atr_hist) > self.range_n:
                self.atr_hist.pop(0)
        if len(self.max_hist) < 2:
            return
        prev_atr = self.atr_hist[-1] if self.atr_hist else atr_value
        self.eps = self.mult * (prev_atr if prev_atr else 0.0)
        hi = max(self.max_hist)
        lo = min(self.min_hist)
        mid = (hi + lo) / 2.0
        if self.m is None:
            self.m = mid
        self.last_upper = (self.m or mid) + (self.eps or 0.0)
        self.last_lower = (self.m or mid) - (self.eps or 0.0)

    def on_tick(self, price: float) -> int:
        """تُعيد +1 إذا حدثت خطوة فوق (bullish step)، −1 تحت، 0 لا شيء."""
        if self.last_upper is None or self.last_lower is None or self.eps is None:
            return 0
        step = 0
        if price > self.last_upper:
            self.m = (self.m or 0.0) + self.eps
            step = 1
        elif price < self.last_lower:
            self.m = (self.m or 0.0) - self.eps
            step = -1
        if step:
            self.steps += 1
            self.last_upper = self.m + self.eps
            self.last_lower = self.m - self.eps
        return step


# ═══════════════════════════════════════════════════════════════
# Premium / Discount Zone  (KB §1.19)
# ═══════════════════════════════════════════════════════════════
def premium_position(highs: List[float], lows: List[float], price: float, window: int = 50) -> float:
    """النسبة المئوية لموقع السعر بين القاع والقمة لآخر `window` شمعة (0→100)."""
    if not highs or not lows:
        return 50.0
    hi = max(highs[-window:])
    lo = min(lows[-window:])
    rng = hi - lo
    if rng <= 0:
        return 50.0
    return (price - lo) / rng * 100.0


def is_premium(pos_pct: float, threshold: float = 50.0) -> bool:
    """True = السعر في النصف العلوي (منطقة غالية) ⇒ يُرفض الشراء."""
    return pos_pct > threshold


# ═══════════════════════════════════════════════════════════════
# z-score نافذة منزلقة (O(1) عبر التخزين، بسيط وسهل التدقيق)
# ═══════════════════════════════════════════════════════════════
class RollingZ:
    def __init__(self, window: int = 50):
        self.window = window
        self.buf: List[float] = []

    def update(self, value: float) -> Optional[float]:
        self.buf.append(value)
        if len(self.buf) > self.window:
            self.buf.pop(0)
        if len(self.buf) < max(3, self.window // 2):
            return None
        n = len(self.buf)
        mean = sum(self.buf) / n
        var = sum((x - mean) ** 2 for x in self.buf) / n
        std = math.sqrt(var + 1e-12)
        return (value - mean) / std

    @property
    def last(self) -> Optional[float]:
        return self.update(self.buf[-1]) if self.buf else None


# ═══════════════════════════════════════════════════════════════
# حجم الفوليوم / جودة
# ═══════════════════════════════════════════════════════════════
def volume_ratio(volumes: List[float], period: int = 20) -> float:
    if len(volumes) < period:
        return 0.0
    avg = sum(volumes[-period:]) / period
    if avg <= 0:
        return 0.0
    return volumes[-1] / avg


def close_location_value(open_: float, high: float, low: float, close: float) -> float:
    """CLV ∈ [−1, 1] — تُستخدم فقط كـ fallback bar-level (KB §0.2-5)."""
    rng = high - low
    if rng <= 0:
        return 0.0
    return (2.0 * close - high - low) / rng
