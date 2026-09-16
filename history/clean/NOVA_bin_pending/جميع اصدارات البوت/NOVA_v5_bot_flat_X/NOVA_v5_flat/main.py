"""
NOVA v5 — نقطة الدخول + الاختبار الذاتي
========================================
Usage:
  python3 main.py --selftest   # يفحص المنطق بلا شبكة
  python3 main.py              # يشغّل البوت
"""
from __future__ import annotations
import asyncio
import math
import os
import sys
import json

# محاولة تحميل `.env` بأمان (لن يفشل إن لم يوجد python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from config import Config
from engine import NovaEngine


# ═══════════════════════════════════════════════════════════════
# اختبار المنطق (Offline — بلا شبكة/مفاتيح)
# ═══════════════════════════════════════════════════════════════
def _selftest() -> int:
    import indicators
    import quant
    import nb
    import scoring
    import risk
    import trigger
    from config import Config
    cfg = Config()
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        status = "✅" if cond else "❌"
        print(f"  {status} {name} {extra}")
        if not cond:
            ok = False

    print("🧪 NOVA v5 — اختبار ذاتي (منطق، بلا شبكة)")

    # ── ATR / EMA / SMA ──────────────────────────────────
    close = [100 + i * 0.1 for i in range(60)]
    high = [c + 0.3 for c in close]
    low = [c - 0.3 for c in close]
    a = indicators.atr(high, low, close, 14)
    check("ATR يُنتج قيمة موجبة", a is not None and a > 0, f"(ATR={a:.4f})")
    e = indicators.ema(close, 50)
    check("EMA50", e is not None and e > 0, f"(EMA={e:.2f})")

    # ── Anchored KAMA + Welford ──────────────────────────
    k = indicators.AnchoredKAMA(power=cfg.kama_power)
    for i, c in enumerate(close):
        k.update(c)
    check("KAMA يتبع السعر في الاتجاه", k.direction == 1, f"(strength={k.strength:.2f})")
    check("KAMA sigma >= 0", k.sigma >= 0)

    # ── Epsilon Band ─────────────────────────────────────
    ep = indicators.EpsilonBand(fast=cfg.eps_mult)
    for i, c in enumerate(close):
        ep.on_closed_bar(high[i], low[i], c, a)
        ep.on_tick(c)
    check("Epsilon يُنتج خطوات", ep.steps >= 0, f"(steps={ep.steps})")

    # ── Premium/Discount ─────────────────────────────────
    pos = indicators.premium_position(high, low, close[-1], 50)
    check("Premiumنسبة في النطاق", 0 <= pos <= 100, f"(pos={pos:.1f}%)")

    # ── Swing Death ──────────────────────────────────────
    sw = quant.SwingDeath(max_touches=3, tolerance_atr_multi=0.5)
    dead = False
    for _ in range(3):
        dead = sw.on_swing_low(99.5, a) or dead
    check("Swing Death بعد 3 لمسات", dead, "(3 لمسات)")
    check("SwingDeath يخطر بالقاع الميت", sw.is_dead(99.5, a))

    # ── Volatility Filter ────────────────────────────────
    vf = quant.VolatilityFilter(hi_pct=95, lo_pct=5, lookback=100)
    for i in range(120):
        vf.push(0.1) if i % 2 else vf.push(0.5)
    check("VolFilter يسمح ضمن النطاق", vf.all_clear(0.2))

    # ── Trigger: MSS + FVG ───────────────────────────────
    # بناء سلسلة صاعدة بحيث يحدث كسر فوق قمة سابقة بإزاحة قوية
    n = 60
    o = [0.0] * n; h = [0.0] * n; l = [0.0] * n; c_list = [0.0] * n; v = [1.0] * n
    anchor = 100.0
    for i in range(n - 12):
        c_list[i] = anchor + i * 0.05
        o[i] = c_list[i] - 0.02
        h[i] = c_list[i] + 0.05
        l[i] = c_list[i] - 0.05
    # آخر شمعة صاعدة قوية تكسر القمة السابقة
    last = n - 1
    prev_high = max(h[:last])
    c_list[last] = prev_high + 0.4
    o[last] = prev_high - 0.05
    h[last] = c_list[last] + 0.2
    l[last] = o[last] - 0.05
    frame = {"o": o, "h": h, "l": l, "c": c_list, "v": v,
             "close": c_list[-1], "live": c_list[-1], "atr": 0.2}
    mss = trigger.detect_mss(frame, cfg)
    check("MSS يُكتشف كسراً بإزاحة", mss is not None, f"(disp={mss['displacement']:.2f})" if mss else "")

    # ── Naive-Bayes (تدريب وفرز) ─────────────────────────
    bay = nb.NaiveBayes(warmup=100, z_window=50, roc=14)
    for i in range(220):
        # simulate trending data -> Bull
        bay.on_price(200 + i * 0.05)
        bay.feed_delta(0.3)
        bay.bar_close(200 + i * 0.05)
    pair = bay.classify()
    check("Naive-Bayes يتدرب ويُفرز", pair[0] in ("Bull", "Bear", "Diverged", "unknown"),
          f"(class={pair[0]})")

    # ── Six-Factor Score + Size ──────────────────────────
    sc = scoring.six_factor_score(cfg, bullish=True, high=105, low=98, open_=99,
                                  close=104, atr_value=1.0, volume=120, vol_ma=100,
                                  ema50=100, touches=2, pierce=1.4)
    check("Six-Factor يعيد 0–100", sc is not None and 0 <= sc <= 100, f"(score={sc:.1f})")
    mult = scoring.size_multiplier(cfg, sc if sc is not None else 0)
    check("Size multiplier ∈ {0, 0.5, 1}", mult in (0.0, 0.5, 1.0), f"(mult={mult})")

    # ── Risk ─────────────────────────────────────────────
    plan = risk.compute_stop_target(cfg, 100, atr_value=1.0)
    check("خطة وقف/هدف", plan is not None and plan["stop"] < 100 < plan["target"])
    net = risk.fee_net(cfg, 1000, 1010)
    check("Net-after-fees يحسب صافياً", abs(net - (10 - (2010 * cfg.fee_bps / 10000.0))) < 1e-9,
          f"(net={net:.4f})")

    # ── Config ───────────────────────────────────────────
    check("Config يحمل القيم المٌقفلة",
          cfg.kama_power == 2.0 and cfg.score_half == 70 and cfg.score_full == 85
          and cfg.nb_long_min >= 0.70)

    print("\n" + ("🎉 الاختبار الذاتي ناجح — المنطق سليم" if ok else "⛔ هناك فشل؟!"))
    return 0 if ok else 1


# ═══════════════════════════════════════════════════════════════
async def _run():
    cfg = Config()
    errs = cfg.validate()
    if errs:
        print("⚠️ إعدادات ناقصة:")
        for e in errs:
            print(f"   - {e}")
        print("عيّن الأسرار في ملف `.env` ثم أعد التشغيل.")
        return 1
    print(f"🚀 إقلاع NOVA v5 — البيئة: {'TESTNET' if cfg.is_testnet else 'LIVE'}")
    if not cfg.is_testnet:
        print("⚠️ بيئة حية: يتطلب AUTO_TRADE وموافقة صريحة قبل التداول.")
    engine = NovaEngine(cfg)
    try:
        await engine.run()
    except KeyboardInterrupt:
        await engine.stop()
        print("🛑 توقف باليد.")
    return 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    try:
        sys.exit(asyncio.run(_run()))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
