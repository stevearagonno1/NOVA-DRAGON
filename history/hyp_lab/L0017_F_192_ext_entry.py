# -*- coding: utf-8 -*-
"""[L0017 · F-192] انحراف الدخول تحت القمة المكسورة — دخول (مرتبة 1 من النخبة)

عقد الآلة حرفياً من docs/lanes/L0017-inventory-batch1-elite-entries.md:
  (كسر هيكل صاعد صالح)
  و (الامتداد = (سعر الدخول − القمة المكسورة) ÷ متوسط الحركة(14) ≤ الحد الأقصى)
  و ليس (السعر > المتوسط + حدود×متوسط الحركة  و  السعر > المتوسط × (1+النسبة))
  السويب: ext_max=[-0.15,0.10,0.50,1.00] × ema_x=[4,6,8] × ema_pct=[5,8,10]%  ⇒ 36 تركيبة

فرق موثق عن F_192_ext_dive.py المرجعي (الذي لا يُمس): ذاك جمّد ema_x=6 و ema_pct=8
(شبكة 4 تركيبات). عقد L0017 يفتح المحورين صراحةً ⇒ 4×3×3 = 36. لا تغيير في أي ساق منطقية.

اصطلاح كسر الهيكل: نواة F_126 القائمة حرفياً (D-0046: «على نسق وحدتي F_126 و F_213»).
سعر الدخول = افتتاح الشمعة التالية (عقد الترجمة: إشارة عند الإغلاق → تعبئة على الافتتاح التالي).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from F_126_mss_core import mss_signal

SWEEP_PARAMS = {
    "ext_max": [-0.15, 0.10, 0.50, 1.00],
    "ema_x": [4, 6, 8],
    "ema_pct": [0.05, 0.08, 0.10],
}
EMA_SPAN = 20   # افتراض موثق من V5.2 (غير محدد في الكتلة الأصلية) — ثابت لا يُسوَّى


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    emax = params.get("ext_max", 0.10)
    ex = params.get("ema_x", 6)
    epct = params.get("ema_pct", 0.08)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    base = mss_signal(df)
    hh20 = h.shift(1).rolling(20, min_periods=20).max()      # القمة المكسورة
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14, min_periods=14).mean()
    fill = o.shift(-1)                                        # سعر الدخول الفعلي
    ext = (fill - hh20) / atr14
    ema = c.ewm(span=EMA_SPAN, adjust=False).mean()
    chase = (fill > ema + ex * atr14) & (fill > ema * (1 + epct))
    return (base & (ext <= emax) & (~chase)).fillna(False)


def self_test():
    rng = np.random.default_rng(42)
    n = 4000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": 100 + rng.normal(0, 1, n).cumsum(),
                       "volume": rng.uniform(1, 100, n)}, index=idx)
    df["close"] = df["open"] + rng.normal(0, 0.5, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng.normal(0, 0.3, n))

    s_dive = make_signals(df, ext_max=-0.15, ema_x=4, ema_pct=0.05)
    s_any = make_signals(df, ext_max=1.00, ema_x=8, ema_pct=0.10)
    assert s_dive.dtype == bool and len(s_dive) == n
    assert int(s_dive.sum()) <= int(s_any.sum()), "سقف غوص أصرم + فيتو أقسى يجب أن يقلل الإشارات"
    # رتابة محور ext: أوسع سقف ⊇ أضيق سقف
    a = make_signals(df, ext_max=-0.15, ema_x=6, ema_pct=0.08)
    b = make_signals(df, ext_max=1.00, ema_x=6, ema_pct=0.08)
    assert bool((a & ~b).sum() == 0), "رتابة ext مكسورة"
    # كل الشبكة تعمل
    k = 0
    for e in SWEEP_PARAMS["ext_max"]:
        for x in SWEEP_PARAMS["ema_x"]:
            for p in SWEEP_PARAMS["ema_pct"]:
                make_signals(df, ext_max=e, ema_x=x, ema_pct=p)
                k += 1
    assert k == 36, f"الشبكة يجب أن تكون 36 لا {k}"
    # لا تسرب مستقبل: الإشارة عند i تعتمد open[i+1] فقط (حارس تعبئة موثق في العقد)
    print(f"[L0017·F-192] self_test OK — 36 تركيبة | إشارات: {int(s_dive.sum())} (أصرم) / {int(s_any.sum())} (أوسع)")


if __name__ == "__main__":
    self_test()
