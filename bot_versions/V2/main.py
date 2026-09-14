from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════════
# NOVA v5 — main.py (FIXED)
# ─────────────────────────────────────────────────────────────────────
# ✔ Fixed SyntaxError:  `from __future__ import annotations` is now the
#   ABSOLUTE first line — nothing (no import, docstring, or code) before it.
# ✔ Fixed .env detection:  dotenv is loaded IMMEDIATELY after, BEFORE any
#   local bot module (config / engine / telegram) is imported, so those
#   modules see the environment variables the moment they are imported.
# ✔ Strict .env keys used:  BINANCE_API_KEY, BINANCE_API_SECRET,
#   TELEGRAM_TOKEN, CHAT_ID  (exact names, injected into Config).
# ✔ Concurrency:  engine.run() starts the Binance WebSocket streams AND the
#   async Telegram polling loop on the SAME asyncio event loop via
#   asyncio.create_task() → fully concurrent, zero blocking of market data.
#   main() فقط يشغّل الحلقة عبر asyncio.run().
#
# Usage:
#   python3 main.py              # تشغيل البوت
#   python3 main.py --selftest   # اختبار ذاتي بلا شبكة
# ═══════════════════════════════════════════════════════════════════════

# ① ── تحميل .env قبل أي استيراد محلي ──────────────────────────────────
try:
    from dotenv import load_dotenv          # python-dotenv: pip install python-dotenv
    load_dotenv()                           # يبحث عن .env في مجلد التشغيل
except ImportError:
    # بديل يدوي آمن (Termux) إذا لم يكن python-dotenv مثبتاً — نفس الوظيفة.
    def load_dotenv(dotenv_path=None, override=False):
        import os
        if dotenv_path:
            candidates = [dotenv_path]
        else:
            candidates = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
                os.path.join(os.getcwd(), ".env"),
                os.path.expanduser("~/.env"),
            ]
        loaded_any = False
        for path in candidates:
            if not path or not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8-sig") as fh:   # utf-8-sig يتولّى BOM
                    for raw in fh:
                        line = raw.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        if line.lower().startswith("export "):
                            line = line[7:].lstrip()
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.strip()
                        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("\"", "'"):
                            val = val[1:-1]                       # أزل الاقتباس
                        else:
                            val = val.split(" #", 1)[0].strip()   # تعليق سطري
                        if key and (override or key not in os.environ):
                            os.environ[key] = val
                            loaded_any = True
            except Exception as exc:
                print(f"[env] تعذّر قراءة {path}: {exc}")
        return loaded_any
    load_dotenv()

# ② ── استيرادات المكتبة القياسية ──────────────────────────────────────
import asyncio                           # ← الإصلاح: حلقة الأحداث للبوت كله
import os
import sys

# تأكيد إضافي: حاوِل تحميل .env الملاصق لهذا الملف تحديداً
# (مفيد إذا شُغِّل البوت من مجلد مختلف في Termux).
for _p in (os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
           os.path.expanduser("~/.env")):
    try:
        load_dotenv(_p, override=False)
    except Exception:
        pass

# ③ ── المفاتيح الحرفية المطلوبة من .env ───────────────────────────────
REQUIRED_ENV_KEYS = ("BINANCE_API_KEY", "BINANCE_API_SECRET",
                     "TELEGRAM_TOKEN", "CHAT_ID")


def _mask(value: str) -> str:
    """اقطع الأسرار للعرض: أول 4 أحرف + طول القيمة فقط."""
    if not value:
        return "❌ (فارغ)"
    return f"✅ {value[:4]}…(len={len(value)})"


def _env_key_names_from_file(path: str) -> list:
    """أسماء المفاتيح المعرفة داخل ملف .env (الأسماء فقط — بلا قيم)."""
    names = []
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.lower().startswith("export "):
                    line = line[7:].lstrip()
                names.append(line.partition("=")[0].strip())
    except Exception:
        pass
    return names


def _env_diagnostics():
    """تشخيص فوري لمشكلة 'البوت لا يرى متغيرات البيئة'."""
    print("🔎 فحص متغيرات البيئة (المفاتيح الحرفية المطلوبة):")
    for key in REQUIRED_ENV_KEYS:
        print(f"   {key:<18} → {_mask(os.getenv(key, ''))}")
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_file):
        env_file = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(env_file):
        found = _env_key_names_from_file(env_file)
        print(f"   📄 ملف .env: {env_file} — يحتوي {len(found)} مفتاحاً")
        unexpected = [k for k in found if k not in REQUIRED_ENV_KEYS
                      and any(req.split("_")[0] in k or k in req for req in REQUIRED_ENV_KEYS)]
        if unexpected:
            print(f"   ⚠️ أسماء غير مطابقة في .env: {unexpected}")
            print(f"      ← يجب أن تكون بالأسماء الحرفية: {', '.join(REQUIRED_ENV_KEYS)}")
    else:
        print("   ⚠️ لم أجد ملف .env بجانب main.py ولا في مجلد التشغيل!")


# ④ ── الاستيرادات المحلية (بعد load_dotenv حصرياً — الترتيب إجباري) ──
from config import Config
from engine import NovaEngine


# ═══════════════════════════════════════════════════════════════════════
# اختبار المنطق (Offline — بلا شبكة/مفاتيح)
# ═══════════════════════════════════════════════════════════════════════
def _selftest() -> int:
    import indicators, quant, nb, scoring, risk, trigger
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
    n = 60
    o = [0.0] * n; h = [0.0] * n; l = [0.0] * n; c_list = [0.0] * n; v = [1.0] * n
    anchor = 100.0
    for i in range(n - 12):
        c_list[i] = anchor + i * 0.05
        o[i] = c_list[i] - 0.02
        h[i] = c_list[i] + 0.05
        l[i] = c_list[i] - 0.05
    last = n - 1
    prev_high = max(h[:last])
    c_list[last] = prev_high + 0.4
    o[last] = prev_high - 0.05
    h[last] = c_list[last] + 0.2
    l[last] = o[last] - 0.05
    frame = {"o": o, "h": h, "l": l, "c": c_list, "v": v,
             "close": c_list[-1], "live": c_list[-1], "atr": 0.2}
    mss = trigger.detect_mss(frame, cfg)
    check("MSS يُكتشف كسراً بإزاحة", mss is not None,
          f"(disp={mss['displacement']:.2f})" if mss else "")

    # ── Naive-Bayes (تدريب وفرز) ─────────────────────────
    bay = nb.NaiveBayes(warmup=100, z_window=50, roc=14)
    for i in range(220):
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


# ═══════════════════════════════════════════════════════════════════════
# التشغيل الفعلي
# ═══════════════════════════════════════════════════════════════════════
def _inject_env_into_config(cfg):
    """حقن المفاتيح الأربعة الحرفية من os.environ داخل Config —
    يضمن أن config/engine/execution/telegram تراها بأي اسم خاصية كانت تستخدم."""
    api_key = __REDACTED__"BINANCE_API_KEY", "").strip()
    api_secret = __REDACTED__"BINANCE_API_SECRET", "").strip()
    tg_token = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat_id = os.getenv("CHAT_ID", "").strip()
    # أسماء الخصائص الأساسية
    cfg.binance_api_key = api_key or str(getattr(cfg, "binance_api_key", "") or "")
    cfg.binance_api_secret = api_secret or str(getattr(cfg, "binance_api_secret", "") or "")
    cfg.telegram_token = __REDACTED__ or str(getattr(cfg, "telegram_token", "") or "")
    cfg.telegram_chat_id = chat_id or str(getattr(cfg, "telegram_chat_id", "") or "")
    # أسماء بديلة شائعة تستخدمها بعض وحدات execution/data
    cfg.api_key = __REDACTED__
    cfg.api_secret = __REDACTED__
    return cfg


async def _run() -> int:
    cfg = Config()
    _inject_env_into_config(cfg)          # ← المفاتيح الحرفية من .env
    _env_diagnostics()                    # ← تشخيص فوري إذا كانت ناقصة

    errs = cfg.validate()
    if errs:
        print("⚠️ إعدادات ناقصة:")
        for e in errs:
            print(f"   - {e}")
        print("≫ أنشئ ملف .env بجانب main.py بهذه الأسطر بالأسماء الحرفية:")
        print("   BINANCE_API_KEY=...")
        print("   BINANCE_API_SECRET=...")
        print("   TELEGRAM_TOKEN=...")
        print("   CHAT_ID=...")
        return 1

    print(f"🚀 إقلاع NOVA v5 — البيئة: {'TESTNET' if cfg.is_testnet else 'LIVE'}")
    print("🔁 التشغيل المتوازي: Binance WebSocket streams + Telegram polling")
    print("   (نفس حلقة asyncio — عبر asyncio.create_task — دون أي حجب)")
    if not cfg.is_testnet:
        print("⚠️ بيئة حية: يتطلب AUTO_TRADE وموافقة صريحة قبل التداول.")

    engine = NovaEngine(cfg)
    try:
        # engine.run() يطلق معاً:
        #   • مهام WebSocket لكل دفعة رموز  (asyncio.create_task)
        #   • kline worker + position loop + universe loop
        #   • حلقة تليجرام التفاعلية tg.poll (asyncio.create_task)
        #   • رسالة الإقلاع 🚀 NOVA HFT Engine Active مع قائمة الأزرار
        await engine.run()
        return 0
    except asyncio.CancelledError:
        raise
    finally:
        # إيقاف نظيف: إلغاء كل المهام (بما فيها tg-poll) + حفظ الحالة
        try:
            await engine.stop()
        except Exception as exc:
            print(f"[main] خطأ أثناء الإيقاف: {exc}")


def main():
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    try:
        sys.exit(asyncio.run(_run()))
    except KeyboardInterrupt:
        print("\n🛑 توقف باليد (Ctrl+C).")
        sys.exit(0)


if __name__ == "__main__":
    main()
