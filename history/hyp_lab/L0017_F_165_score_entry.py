# -*- coding: utf-8 -*-
"""[L0017 · F-165] التنقيط التعويضي المتدرج — دخول (مرتبة 5)

عقد الآلة حرفياً من عقد الجولة:
  (الدرجة = 35×كسر الهيكل + 25×الفجوة + المتوسطان + التدفق + الحجم + الزخم ≥ العتبة)
  و (مكونان موجبان على الأقل) و (كسر الهيكل موجود إلزاميًا)
  و (تقلب% ≥ 0.10) و (نسبة الحجم ≤ 3.0) و فيتو الامتداد الزائد
  السويب: العتبة=[70,72,75] × زخم_التدفق=[2.5,3.0,4.0] × زخم_الحجم=[2.0,2.5,3.0] ⇒ 27 تركيبة

أمانة إلزامية رقم (1) من عقد الجولة — تُسطر صراحةً ولا تُدّعى أصلاً:
  **وكيل التدفق** = حصة حجم الشموع الصاعدة داخل نافذة تأكيد الكسر (5 شموع).
  هذا **وكيل** لا تدفق أوامر أصلي؛ بياناتنا شمعية ولا تحوي دفتر أوامر. نفس عهد جبهة L0016.

أمانة إلزامية رقم (2): اصطلاح كسر الهيكل على نواة F_126 حرفاً، والفجوة على نسق F_127
(الإزاحة = مدى الشمعة ÷ ATR14 — مقياس «فجوة الإزاحة» المعتمد في الوحدتين القائمتين).

أوزان المكونات الخفيفة الأربعة (المتوسطان · التدفق · الحجم · الزخم) غير منصوص عليها رقماً
في الكتلة؛ الكتلة تسمي الوزنين الكبيرين فقط (35 و 25). الافتراض الموثق v1: 10 لكل مكون
خفيف ⇒ السقف 35+25+4×10 = 100، فتصير العتبات 70/72/75 نسباً مئوية طبيعية من السقف —
وهو التفسير الوحيد الذي يجعل عتبة 75 قابلة للبلوغ ومعنى «التعويض» قائماً (كسر + فجوة
= 60 لا يكفي وحده، فيلزم تعويض من مكونين خفيفين على الأقل — وهو نص شرط «مكونان موجبان»).
أي تعديل لهذه الأوزان = قرار قائد جديد يُسطر في سجل القرارات.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from F_126_mss_core import mss_signal

SWEEP_PARAMS = {
    "score_th": [70, 72, 75],
    "flow_mom": [2.5, 3.0, 4.0],
    "vol_mom": [2.0, 2.5, 3.0],
}

W_MSS, W_GAP, W_LIGHT = 35.0, 25.0, 10.0
CONFIRM_BARS = 5        # نافذة تأكيد الكسر (وكيل التدفق)
VOLP_MIN = 0.0010       # تقلب% ≥ 0.10%
VOL_RATIO_MAX = 3.0     # نسبة الحجم ≤ 3.0
EMA_SPAN = 20
EXT_VETO_X, EXT_VETO_PCT = 6.0, 0.08   # فيتو الامتداد الزائد (نفس ثابت V5.2 في F-192)


def _parts(df: pd.DataFrame, flow_mom: float, vol_mom: float):
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14, min_periods=14).mean()
    rng = (h - l).replace(0, np.nan)

    mss = mss_signal(df)                                    # كسر الهيكل — إلزامي
    gap = (rng / atr14) >= 1.6                              # الفجوة/الإزاحة (نسق F-127)

    ema_f = c.ewm(span=EMA_SPAN, adjust=False).mean()
    ema_s = c.ewm(span=50, adjust=False).mean()
    emas = (c > ema_f) & (ema_f > ema_s)                    # المتوسطان مصطفّان صعوداً

    up_vol = v.where(c > o, 0.0)
    flow = (up_vol.rolling(CONFIRM_BARS, min_periods=CONFIRM_BARS).sum()
            / v.rolling(CONFIRM_BARS, min_periods=CONFIRM_BARS).sum().replace(0, np.nan))
    vol_ratio = v / v.rolling(20, min_periods=20).mean().replace(0, np.nan)
    # محورا السويب عتبتان على الوكيلين، مُسوّاتان إلى مجال [0,1] بقسمة معيارية
    flow_ok = flow >= (flow_mom / 5.0)                      # 2.5→0.50 · 3.0→0.60 · 4.0→0.80
    vol_ok = vol_ratio >= (vol_mom / 2.0)                   # 2.0→1.00 · 2.5→1.25 · 3.0→1.50

    mom = (c / c.shift(CONFIRM_BARS) - 1.0) > 0             # الزخم القصير موجب

    volp = (rng / c)                                        # تقلب%
    fill = o.shift(-1)
    ext_veto = (fill > ema_f + EXT_VETO_X * atr14) & (fill > ema_f * (1 + EXT_VETO_PCT))

    return mss, gap, emas, flow_ok, vol_ok, mom, volp, vol_ratio, ext_veto


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    th = params.get("score_th", 72)
    fm = params.get("flow_mom", 3.0)
    vm = params.get("vol_mom", 2.5)
    mss, gap, emas, flow_ok, vol_ok, mom, volp, vol_ratio, ext_veto = _parts(df, fm, vm)

    light = (emas.astype(float) + flow_ok.astype(float)
             + vol_ok.astype(float) + mom.astype(float))
    score = W_MSS * mss.astype(float) + W_GAP * gap.astype(float) + W_LIGHT * light

    sig = (mss                                   # كسر الهيكل إلزامي
           & (score >= th)                       # العتبة
           & (light >= 2)                        # مكونان موجبان على الأقل
           & (volp >= VOLP_MIN)                  # تقلب% ≥ 0.10
           & (vol_ratio <= VOL_RATIO_MAX)        # نسبة الحجم ≤ 3.0
           & (~ext_veto.fillna(False)))          # فيتو الامتداد الزائد
    return sig.fillna(False)


def self_test():
    rng_ = np.random.default_rng(42)
    n = 6000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": 100 + rng_.normal(0, 1, n).cumsum(),
                       "volume": rng_.uniform(1, 100, n)}, index=idx)
    df["close"] = df["open"] + rng_.normal(0, 0.5, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng_.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng_.normal(0, 0.3, n))

    s70 = make_signals(df, score_th=70, flow_mom=2.5, vol_mom=2.0)
    s75 = make_signals(df, score_th=75, flow_mom=4.0, vol_mom=3.0)
    assert s70.dtype == bool and len(s70) == n
    assert bool((s75 & ~s70).sum() == 0), "رتابة العتبة/الوكيلين مكسورة"
    # كسر الهيكل إلزامي: كل إشارة ⊆ نواة MSS
    base = mss_signal(df)
    assert bool((s70 & ~base).sum() == 0), "إشارة بلا كسر هيكل — خرق العقد"
    # السقف المنطقي: 35+25+40 = 100 ⇒ عتبة 75 قابلة للبلوغ
    assert W_MSS + W_GAP + 4 * W_LIGHT == 100.0
    k = 0
    for t in SWEEP_PARAMS["score_th"]:
        for f in SWEEP_PARAMS["flow_mom"]:
            for v in SWEEP_PARAMS["vol_mom"]:
                make_signals(df, score_th=t, flow_mom=f, vol_mom=v)
                k += 1
    assert k == 27, f"الشبكة يجب أن تكون 27 لا {k}"
    print(f"[L0017·F-165] self_test OK — 27 تركيبة · وكيل التدفق مسطر | إشارات: {int(s70.sum())} (أوسع) / {int(s75.sum())} (أصرم)")


if __name__ == "__main__":
    self_test()
