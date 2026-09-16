# -*- coding: utf-8 -*-
# [F-197] المطاردة ثنائية السرعة + سلم التعادل (خروج هجين) — خروج
# المصدر: معرفة: مقتنص بطي V5.3 (trailing_plan رباعي الأطوار) + المخطط الشامل + تحسين PDF (BNB)
# انحراف موثق عن قالب العقد: الخروج هنا يحمل حالة (peak) → يُنفَّذ في آلة الاختبار
# (common.simulate exit_mode='dual') ولا يمكن التعبير عنه كسلسلة بوليانية نقية.
# ثابتا التتبع من فكرة الفرضية نفسها: wide=0.20% (قمة ≤1%) · tight=0.08% (فوق 1%).
# لا هدف ثابت في وضع dual (التتبع هو المخرج كما في التصميم الأصلي).
from typing import Tuple
import numpy as np
import pandas as pd

SWEEP_PARAMS = {
    "trig": [0.0025, 0.0040, 0.0050],   # عتبة التسليح (فكرة الفرضية: 0.25/0.40/0.50%)
    "lock": [0.0015, 0.0045],            # القفل % (القائمة من الكتلة؛ الافتراضي V5.3 = 0.25% بينهما)
}
WIDE = 0.0020
TIGHT = 0.0008


def make_dual_spec(**params) -> dict:
    return {
        "trig": params.get("trig", 0.0040),
        "lock": params.get("lock", 0.0025),
        "wide": WIDE, "tight": TIGHT,
    }


def self_test():
    """اختبار ذاتي: محاكاة كاملة على بيانات تركيبية — التسليح يجب أن يقفل جزءاً من الربح."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import simulate, atr
    rng = np.random.default_rng(42)
    n = 3000
    idx = pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC")
    # مسار اصطناعي: صعود ثابت ثم هبوط → التتبع يجب أن يخرج قرب القمة.
    # مقياس الخطوة 0.3/شمعة حتى ATR (≈0.3) يتفوق على التكلفة (0.13%) — كما في الحقيقي.
    up = np.linspace(0, 450, 1500)
    down = np.linspace(450, 300, 1500)
    px = 100 + np.concatenate([up, down]) + rng.normal(0, 0.01, n)
    o = pd.Series(px, index=idx)
    df = pd.DataFrame({
        "open": o, "close": o.shift(-1).fillna(o.iloc[-1]),
        "high": np.maximum(o, o.shift(-1).fillna(o.iloc[-1])) + 0.02,
        "low": np.minimum(o, o.shift(-1).fillna(o.iloc[-1])) - 0.02,
        "volume": np.ones(n),
    }, index=idx)
    sig = pd.Series(False, index=idx)
    sig.iloc[100] = True   # إشارة واحدة (بعد توفر ATR14)
    st_d, tr_d = simulate(df, sig, atr(df), exit_mode="dual",
                          dual=make_dual_spec(trig=0.004, lock=0.0025))
    st_s, tr_s = simulate(df, sig, atr(df), exit_mode="std")
    assert st_d["trades"] == 1 and st_s["trades"] == 1
    # في مسار صعود ثم هبوط حاد: المتتبع المسلح يجب أن يقفل ربحاً ومخرجه = التتبع
    assert tr_d[0]["pnl"] > 0, "التتبع لم يقفل ربحاً في مسار صاعد ثم هابط"
    assert tr_d[0]["exit_side"] == "stop", "المخرج المتوقع هو الوقف المتتبع المسلح"
    for t in SWEEP_PARAMS["trig"]:
        make_dual_spec(trig=t)
    print(f"[F-197] self_test OK — dual net={st_d['net']:.2f} (exit={tr_d[0]['exit_side']}) | std net={st_s['net']:.2f}")


if __name__ == "__main__":
    self_test()
