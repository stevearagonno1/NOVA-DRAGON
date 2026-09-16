"""
NOVA v5 — Online Naive-Bayes Order-Flow Classifier (M4 = مُقفل)
================================================================
المصدر: KB §4.11 (Viprasol) — جزء أساسي من المحرك، لا خيار.
  - ميزات لكل بار (O(1)): delta حقيقي (aggTrade), CVD, cvdRoc, priceRoc, slopeR.
    ثم F1/F2/F3 = z50(...).
  - تدريب آلي عبر **مجاميع تشغيلية فقط** (n_c, ΣF, ΣF²) — لا عينات مخزّنة.
  - الصفوف: Bull / Bear / **Diverged** (فئة «منع التداول» صريحة — ليست فرعلة).
  - posterior = prior · ∏ N(F_k; mu, sigma) / normalizer.
  - Warm-up بعد 100 بار مُسمّى.
  - self-audit: معدل نجاح argmax-posterior مقابل النتيجة المحقّقة (مراقبة الانحراف).
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple


class NaiveBayes:
    def __init__(self, warmup: int = 100, z_window: int = 50, roc: int = 14):
        self.warmup = warmup
        self.roc = roc
        self.z_window = z_window
        self.classes = ("Bull", "Bear", "Diverged")
        # مجاميع تشغيلية لكل صف: n, sum_F[k], sum_F2[k]
        self.sums: Dict[str, Dict] = {c: {"n": 0, "sf": [0.0, 0.0, 0.0], "s2": [0.0, 0.0, 0.0]} for c in self.classes}
        self.history: List[float] = []       # سلسلة الأسعار (لنسب ROC)
        self.cvd: float = 0.0
        self.cvd_hist: List[float] = []      # CVD عند كل بار
        # صفوف البار المعلّم
        self.z1 = 0.0; self.z2 = 0.0; self.z3 = 0.0
        # self-audit
        self.audit_correct = 0
        self.audit_total = 0
        self.labels_seen = 0
        self.live_class: str | None = None

    # ── بيانات واردة (يستدعيها المحرك لكل بار مغلق أو tick) ──
    def feed_delta(self, delta: float):
        self.cvd += delta

    def on_price(self, price: float):
        self.history.append(price)
        if len(self.history) > 300:
            self.history.pop(0)

    def on_volume(self, close: float, high: float, low: float, volume: float):
        """استكمال بارٍ كامل — يُحدّث CVD وميزات الـ z ونُسمّي الصف."""
        delta_bar = volume * ((close - low) - (high - close)) / max(high - low, 1e-12)
        self.cvd += 0.0  # delta الحقيقي من aggTrade يُضاف عبر feed_delta
        self.cvd_hist.append(self.cvd)
        if len(self.cvd_hist) > 300:
            self.cvd_hist.pop(0)

    def _stats(self, values: List[float], n: int) -> float:
        if not values:
            return 0.0
        return values[-n - 1] if len(values) > n else (values[0] if values else 0.0)

    def extract_features(self) -> Tuple[float, float, float]:
        """F1/F2/F3 كقيم z-scored (نسب CTCK في نافذة 50)."""
        price = self.history[-1] if self.history else 0.0
        price_n = self._stats(self.history, self.roc)
        cvd_n = self._stats(self.cvd_hist, self.roc)
        cvd_roc = (self.cvd - cvd_n) / (abs(cvd_n) + 1e-12)
        price_roc = (price - price_n) / (abs(price_n) + 1e-12)
        # slope من آخر 10 نقاط CVD (linreg مبسّط)
        if len(self.cvd_hist) >= 2:
            k = min(10, len(self.cvd_hist))
            xs = list(range(k)); ys = self.cvd_hist[-k:]
            mx = (k - 1) / 2.0
            my = sum(ys) / k
            sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            sxx = sum((x - mx) ** 2 for x in xs)
            slopeR = sxy / (sxx + 1e-12)
        else:
            slopeR = 0.0
        # z-scores عبر توزيعات قيمنا
        z1 = self._z(price_roc)
        z2 = self._z(price_roc - cvd_roc)
        z3 = self._z(slopeR)
        return z1, z2, z3

    def _z(self, value: float) -> float:
        # توزيع بسيط عبر زخم: نحتفظ بآخر 100 قيمة لهذا المعيار
        pass  # توضيحية — يُنفَّذ عبر المتغيرات الذاتية في feed

    # ── الإصدار العملي: حفظ أوّل قيم قاعدة ووضع z من توزيعات متحركة ──
    def _z_from_buffer(self, buf: List[float], value: float, window: int) -> float:
        if len(buf) < 10:
            return 0.0
        tail = buf[-window:]
        mean = sum(tail) / len(tail)
        var = sum((x - mean) ** 2 for x in tail) / len(tail) + 1e-12
        return (value - mean) / math.sqrt(var)

    def compute_features(self) -> Optional[Tuple[float, float, float]]:
        if len(self.history) < self.roc + 1:
            return None
        price = self.history[-1]
        price_n = self._stats(self.history, self.roc)
        cvd_n = self._stats(self.cvd_hist, self.roc)
        cvd_roc = (self.cvd - cvd_n) / (abs(cvd_n) + 1e-12)
        price_roc = (price - price_n) / (abs(price_n) + 1e-12)
        if len(self.cvd_hist) >= 2:
            k = min(10, len(self.cvd_hist)); ys = self.cvd_hist[-k:]; xs = list(range(k))
            mx = (k - 1) / 2.0; my = sum(ys) / k
            sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)); sxx = sum((x - mx) ** 2 for x in xs)
            slopeR = sxy / (sxx + 1e-12)
        else:
            slopeR = 0.0
        # نسجّل هذه المخاطر في مخازن z
        self._push_z(price_roc, "z1")
        self._push_z(price_roc - cvd_roc, "z2")
        self._push_z(slopeR, "z3")
        f1 = self._z_last("z1"); f2 = self._z_last("z2"); f3 = self._z_last("z3")
        return (f1, f2, f3)

    def _push_z(self, val: float, name: str):
        buf = getattr(self, "_zbuf_" + name, None)
        if buf is None:
            buf = []
            setattr(self, "_zbuf_" + name, buf)
        buf.append(val)
        if len(buf) > 120:
            buf.pop(0)
        # نحدّث object ذريعياً
        setattr(self, "_z_last_" + name, val)

    def _z_last(self, name: str) -> float:
        buf: List[float] = getattr(self, "_zbuf_" + name, [])
        if len(buf) < 8:
            return 0.0
        tail = buf[-self.z_window:]
        mean = sum(tail) / len(tail)
        var = sum((x - mean) ** 2 for x in tail) / len(tail) + 1e-12
        return (buf[-1] - mean) / math.sqrt(var)

    # ── واجهة تكامل مبسّطة للـ Engine ─────────────────────────
    def bar_close(self, close: float):
        """يُستدعى عند إغلاق شمعة: يُحدّث السلسلة، يزحزح CVD، يدرب، ويُعيد posterior."""
        self.on_price(close)
        self.cvd_hist.append(self.cvd)
        if len(self.cvd_hist) > 300:
            self.cvd_hist.pop(0)
        # تسمية الصف من بيانات متفقهها (price_roc/cvd_roc) ثم تدريب.
        if len(self.history) >= self.roc + 2 and len(self.cvd_hist) >= self.roc + 2:
            price = self.history[-1]
            price_n = self.history[-1 - self.roc]
            cvd = self.cvd_hist[-1]
            cvd_n = self.cvd_hist[-1 - self.roc]
            price_roc = (price - price_n) / (abs(price_n) + 1e-12)
            cvd_roc = (cvd - cvd_n) / (abs(cvd_n) + 1e-12)
            self.train_online(price_roc, cvd_roc)
        feats = self.compute_features()
        if feats is None:
            return ("unknown", {})
        posts = self.posterior(feats)
        best = max(posts, key=posts.get) if posts else "unknown"
        self.live_class = best
        return (best, posts)

    # ── التدريب والتسمية ──────────────────────────────────────
    def _classify_label(self, price_roc: float, cvd_roc: float) -> str:
        if price_roc > 0 and cvd_roc > 0:
            return "Bull"
        if price_roc < 0 and cvd_roc < 0:
            return "Bear"
        return "Diverged"

    @property
    def ready(self) -> bool:
        return self.labels_seen >= self.warmup

    def train_online(self, price_roc: float, cvd_roc: float):
        """نمذجة الصفّ من شمعةٍ مغلقة، ثم تدخل بياناتها للمجاميع الحيّة."""
        label = self._classify_label(price_roc, cvd_roc)
        feats = self.compute_features()
        if feats is None:
            return
        st = self.sums[label]
        st["n"] += 1
        for k in range(3):
            st["sf"][k] += feats[k]
            st["s2"][k] += feats[k] * feats[k]
        self.labels_seen += 1

    # ── الاحتمالات ───────────────────────────────────────────
    def posterior(self, feats: Tuple[float, float, float]) -> Dict[str, float]:
        out = {}
        total_n = sum(self.sums[c]["n"] for c in self.classes)
        if total_n <= 0:
            return {}
        for c in self.classes:
            st = self.sums[c]
            n = st["n"]
            prior = n / total_n
            ll = math.log(prior + 1e-12)
            for k in range(3):
                mu = st["sf"][k] / n if n else 0.0
                var = max(st["s2"][k] / n - mu * mu, 1e-6) if n else 1.0
                sigma = math.sqrt(var)
                z = (feats[k] - mu) / sigma
                ll += -0.5 * z * z - 0.5 * math.log(2 * math.pi) - math.log(sigma)
            out[c] = math.exp(ll)
        s = sum(out.values()) + 1e-12
        for c in out:
            out[c] /= s
        return out

    def classify(self) -> Tuple[str, Dict[str, float]]:
        feats = self.compute_features()
        if feats is None:
            return ("unknown", {})
        posts = self.posterior(feats)
        best = max(posts, key=posts.get) if posts else "unknown"
        self.live_class = best
        # self-audit
        return (best, posts)

    def record_outcome(self, realized_bull: bool):
        """هل كانت prediction صحيحة؟ — يقود self-audit للانحراف."""
        if self.live_class is None:
            return
        self.audit_total += 1
        pred_bull = self.live_class == "Bull"
        self.live_class = None
        if pred_bull == realized_bull:
            self.audit_correct += 1

    @property
    def audit_accuracy(self) -> float:
        return (self.audit_correct / self.audit_total) if self.audit_total else 0.0
