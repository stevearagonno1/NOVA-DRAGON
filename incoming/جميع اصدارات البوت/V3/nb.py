"""
NOVA v5 — Online Naive-Bayes Order-Flow Classifier (M4)
========================================================
⚗️ FORWARD-PROFILING MODE (this build):
  - NB is now a pure OBSERVER. It still trains every closed bar, still
    computes the exact Bull/Bear/Diverged posteriors, and still self-audits —
    but it NEVER gates entries any more.
  - NB_MIN_ENTRY_PROB is pinned to 0.0 (zero-threshold).
  - NB_VETO_ENABLED is False (the "Diverged" veto no longer rejects a trade).
  - The engine records the exact score on every signal (console + Telegram +
    .txt journal) so the profiling phase can later correlate NB score vs PnL.
  - To go BACK to gated trading: ZERO_THRESHOLD_MODE = False (and the engine
    will re-apply the legacy 55% Bull floor + Diverged veto automatically).

Original spec (kept — the classifier itself is unchanged):
  - الميزات لكل بار (O(1)): delta حقيقي (aggTrade), CVD, cvdRoc, priceRoc, slopeR.
    F1/F2/F3 = z-score متحرك (نافذة z_window) عبر مخازن منزلقة.
  - تدريب آلي عبر مجاميع تشغيلية فقط (n_c, ΣF, ΣF²) — لا عينات مخزّنة.
  - الصفوف: Bull / Bear / Diverged.
  - posterior = prior · ∏ N(F_k; mu, sigma) / normalizer.
  - Warm-up labels + self-audit لمراقبة الانحراف.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple

# ══════════════════════════════════════════════════════════════════════
# Zero-Threshold / Forward-Profiling switches (engine + diagnostics read)
# ══════════════════════════════════════════════════════════════════════
# Master switch. True  ⇒ every generated core signal (KAMA) is EXECUTED on
# Testnet regardless of the NB posterior — NB score is recorded, never applied.
# False ⇒ legacy behaviour: Bull posterior must clear the floor below and the
# Diverged class vetoes the entry.
ZERO_THRESHOLD_MODE = True

# Minimum acceptable Bull posterior for opening on Testnet.
# ⚗️ FORCED TO 0.0 during forward profiling (was 0.55).
NB_MIN_ENTRY_PROB = 0.0

# The historical floor, kept ONLY for reporting purposes ("NB would have
# rejected this: 38.125% < 55%") in console diagnostics and in the .txt
# journal — so the profiling data stays interpretable after we revert.
LEGACY_NB_MIN_ENTRY_PROB = 0.55

# "Diverged" veto (reject-on-classification). Disabled while profiling.
NB_VETO_ENABLED = False


def effective_min_prob() -> float:
    """Single source of truth for the entry floor, honouring the master switch."""
    return 0.0 if ZERO_THRESHOLD_MODE else LEGACY_NB_MIN_ENTRY_PROB


class NaiveBayes:
    def __init__(self, warmup: int = 100, z_window: int = 50, roc: int = 14):
        self.warmup = warmup
        self.roc = roc
        self.z_window = z_window
        self.classes = ("Bull", "Bear", "Diverged")
        # مجاميع تشغيلية لكل صف: n, sum_F[k], sum_F2[k]
        self.sums: Dict[str, Dict] = {c: {"n": 0, "sf": [0.0, 0.0, 0.0], "s2": [0.0, 0.0, 0.0]} for c in self.classes}
        self.history: List[float] = []       # سلسلة الأسعار (لنسب ROC)
        self.cvd: float = 0.0                # CVD تراكمي (يُغذّى عبر feed_delta)
        self.cvd_hist: List[float] = []      # CVD عند إغلاق كل بار
        # self-audit
        self.audit_correct = 0
        self.audit_total = 0
        self.labels_seen = 0
        self.live_class: Optional[str] = None

    # ── بيانات واردة (يستدعيها المحرك) ──────────────────────
    def feed_delta(self, delta: float):
        self.cvd += delta

    def on_price(self, price: float):
        self.history.append(price)
        if len(self.history) > 300:
            self.history.pop(0)

    def compute_features(self) -> Optional[Tuple[float, float, float]]:
        """F1/F2/F3 كقيم z-scored للبار الحالي (تُدفع مرة واحدة لكل بار)."""
        if len(self.history) < self.roc + 1 or len(self.cvd_hist) < self.roc + 1:
            return None
        price = self.history[-1]
        price_n = self.history[-1 - self.roc]
        cvd_n = self.cvd_hist[-1 - self.roc]
        if price_n == 0:
            return None
        price_roc = (price - price_n) / (abs(price_n) + 1e-12)
        cvd_roc = (self.cvd - cvd_n) / (abs(cvd_n) + 1e-12)
        # slope من آخر 10 نقاط CVD (linreg مبسّط)
        k = min(10, len(self.cvd_hist))
        xs = list(range(k)); ys = self.cvd_hist[-k:]
        mx = (k - 1) / 2.0
        my = sum(ys) / k
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sxx = sum((x - mx) ** 2 for x in xs)
        slopeR = (sxy / sxx) if sxx > 0 else 0.0
        # نسجّل القيم الخام في مخازن z ثم نُعيد z-score للبار الحالي
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

    def _z_last(self, name: str) -> float:
        buf: List[float] = getattr(self, "_zbuf_" + name, [])
        if len(buf) < 8:
            return 0.0
        tail = buf[-self.z_window:]
        mean = sum(tail) / len(tail)
        var = sum((x - mean) ** 2 for x in tail) / len(tail)
        if var <= 0:
            return 0.0
        return (buf[-1] - mean) / math.sqrt(var)

    # ── واجهة تكامل مبسّطة للـ Engine ─────────────────────────
    def bar_close(self, close: float):
        """يُستدعى عند إغلاق شمعة: يُحدّث السلسلة، يزحزح CVD، يدرب، ويُعيد posterior.
        تُحسب الفيشورز مرة واحدة فقط وتُعاد استخدامها للتدريب وللتصنيف."""
        self.on_price(close)
        self.cvd_hist.append(self.cvd)
        if len(self.cvd_hist) > 300:
            self.cvd_hist.pop(0)
        feats = self.compute_features()
        if feats is None:
            return ("unknown", {})
        # تسمية الصف من آخر شمعة مغلقة (price_roc/cvd_roc) ثم تدريب بنفس الفيشورز.
        if len(self.history) >= self.roc + 2 and len(self.cvd_hist) >= self.roc + 2:
            price = self.history[-1]
            price_n = self.history[-1 - self.roc]
            cvd = self.cvd_hist[-1]
            cvd_n = self.cvd_hist[-1 - self.roc]
            price_roc = (price - price_n) / (abs(price_n) + 1e-12)
            cvd_roc = (cvd - cvd_n) / (abs(cvd_n) + 1e-12)
            self.train_online(feats, price_roc, cvd_roc)
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

    def train_online(self, feats: Tuple[float, float, float], price_roc: float, cvd_roc: float):
        """نمذجة الصفّ من شمعةٍ مغلقة، ثم تدخل بياناتها للمجاميع الحيّة.
        تستقبل الفيشورز محسوبة مسبقاً — لا تعيد حسابها (يمنع ازدواج دفع z)."""
        label = self._classify_label(price_roc, cvd_roc)
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
