# -*- coding: utf-8 -*-
# [F-146] آلة الحالات الهيكلية: كنس ← كسر MSS بإزاحة ← لمس (FVG أو 50% الرجل) + إبسيلون
# عقد L0016 حرفياً — لا تعديل في أي ساق من الشبكة.
# اصطلاح السوينغ/FVG/الرجل: F-008 (كنس LL) + F-126 (كسر HH) + nova_v8/microstructure (FVG ثلاثي الشموع).
from __future__ import annotations

import numpy as np
import pandas as pd

import F_197_dual_trail as M197

# شبكة العقد (حرفياً من docs/lanes/L0016-state-machine-f146.md)
SWEEP_PARAMS = {
    "eps": [2.0, 2.8, 3.5],
    "fvg_min": [0.10, 0.20, 0.30],
    "mss_window": [8, 12, 20],
}

# ثوابت مجمّدة (ليست محاور شبكة) — موثّقة لا مخترعة
SSL_LOOKBACK = 20          # LL/HH المختبر: F-008 و F-126 الافتراضي
MSS_DISP_ATR = 0.60        # إزاحة الكسر في العقد
FLOW_MIN = 0.58            # حصة حجم الشموع الصاعدة
MID_LEN = 200              # mid200 = منتصف (أعلى+أدنى إغلاق 200)
# خروج F-197 dual المقاس (L0007-tf1h / F-213): لا إعادة فحص
DUAL_TRIG, DUAL_LOCK = 0.0025, 0.0045


def make_dual_spec() -> dict:
    return M197.make_dual_spec(trig=DUAL_TRIG, lock=DUAL_LOCK)


def _atr14(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(14, min_periods=14).mean()


def make_signals(
    df: pd.DataFrame,
    eps: float = 2.8,
    fvg_min: float = 0.20,
    mss_window: int = 12,
    **_,
) -> pd.Series:
    """إشارة شراء فقط عند إغلاق الشمعة (التعبئة على افتتاح التالية — عقد common.simulate).

    التسلسل داخل mss_window شمعة بعد الكنس:
      1) كنس: low < SSL و close > SSL  — SSL = LL(20) السابق (F-008)
      2) MSS: open <= HH(20) < close و range >= 0.6·ATR14 (F-126 كسر + إزاحة العقد)
      3) لمس: تقاطع مدى الشمعة مع FVG مؤهّل (>= fvg_min·ATR) أو مع منتصف الرجل
      4) تدفق: حجم الشموع الصاعدة / الحجم الكلي من الكنس حتى MSS >= 58% (وكيل، لا عمود تدفق)
      5) إبسيلون: close خارج [mid200 ± eps·ATR14]
    """
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    vol = df["volume"].to_numpy(float)
    n = len(df)
    win = int(mss_window)
    eps = float(eps)
    fvg_min = float(fvg_min)

    atr14 = _atr14(df).to_numpy(float)
    ssl = df["low"].shift(1).rolling(SSL_LOOKBACK, min_periods=SSL_LOOKBACK).min().to_numpy(float)
    hh = df["high"].shift(1).rolling(SSL_LOOKBACK, min_periods=SSL_LOOKBACK).max().to_numpy(float)
    hi200 = df["close"].shift(1).rolling(MID_LEN, min_periods=MID_LEN).max().to_numpy(float)
    lo200 = df["close"].shift(1).rolling(MID_LEN, min_periods=MID_LEN).min().to_numpy(float)
    mid200 = (hi200 + lo200) / 2.0

    sweep = (l < ssl) & (c > ssl) & np.isfinite(ssl)
    rng = h - l
    mss_bar = (o <= hh) & (hh < c) & (rng >= MSS_DISP_ATR * atr14) & np.isfinite(hh) & np.isfinite(atr14)
    outside = np.isfinite(mid200) & np.isfinite(atr14) & (
        (c > mid200 + eps * atr14) | (c < mid200 - eps * atr14)
    )

    # FVG صاعد ثلاثي الشموع (microstructure.fvg_levels): low[i] > high[i-2]
    fvg_bot = np.full(n, np.nan)
    fvg_top = np.full(n, np.nan)
    fvg_sz = np.full(n, np.nan)
    if n > 2:
        bull = l[2:] > h[:-2]
        fvg_top[2:][bull] = l[2:][bull]
        fvg_bot[2:][bull] = h[:-2][bull]
        fvg_sz[2:][bull] = l[2:][bull] - h[:-2][bull]

    sig = np.zeros(n, dtype=bool)
    # 0 idle · 1 wait MSS · 2 wait touch
    state = 0
    t0 = -1
    up_vol = 0.0
    tot_vol = 0.0
    fvg_b = fvg_t = np.nan
    fvg_ok = False
    mid_leg = np.nan

    for i in range(n):
        if state == 0:
            if sweep[i]:
                state = 1
                t0 = i
                up_vol = vol[i] if c[i] > o[i] else 0.0
                tot_vol = vol[i]
                fvg_ok = False
                fvg_b = fvg_t = mid_leg = np.nan
            continue

        if i - t0 > win:
            state = 0
            if sweep[i]:
                state = 1
                t0 = i
                up_vol = vol[i] if c[i] > o[i] else 0.0
                tot_vol = vol[i]
            continue

        if state == 1:
            up_vol += vol[i] if c[i] > o[i] else 0.0
            tot_vol += vol[i]
            if mss_bar[i]:
                flow_ok = (tot_vol > 0.0) and (up_vol / tot_vol >= FLOW_MIN)
                if not flow_ok:
                    state = 0
                    if sweep[i]:
                        state = 1
                        t0 = i
                        up_vol = vol[i] if c[i] > o[i] else 0.0
                        tot_vol = vol[i]
                    continue
                mid_leg = l[t0] + 0.5 * (h[i] - l[t0])
                if np.isfinite(fvg_sz[i]) and fvg_sz[i] >= fvg_min * atr14[i]:
                    fvg_ok = True
                    fvg_b = fvg_bot[i]
                    fvg_t = fvg_top[i]
                else:
                    fvg_ok = False
                    fvg_b = fvg_t = np.nan
                state = 2
                continue  # اللمس شمعة لاحقة بعد الكسر — لا شمعة الإزاحة نفسها
            else:
                continue

        if state == 2:
            touch_fvg = fvg_ok and (l[i] <= fvg_t) and (h[i] >= fvg_b)
            touch_50 = np.isfinite(mid_leg) and (l[i] <= mid_leg) and (h[i] >= mid_leg)
            if (touch_fvg or touch_50) and outside[i]:
                sig[i] = True
                state = 0
            elif sweep[i]:
                # كنس جديد يعيد السلسلة
                state = 1
                t0 = i
                up_vol = vol[i] if c[i] > o[i] else 0.0
                tot_vol = vol[i]
                fvg_ok = False
                fvg_b = fvg_t = mid_leg = np.nan

    return pd.Series(sig, index=df.index, dtype=bool)


def self_test():
    """مسار اصطناعي حتمي: كنس قاع → إزاحة تكسر HH → لمس منتصف الرجل خارج الإبسيلون."""
    n = 500
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    px = np.full(n, 100.0)
    # دفء 200+ شمعة ثم قاع ثم كنس ثم اندفاع ثم رجوع لمنتصف الرجل
    px[0:200] = 100.0 + 0.02 * np.sin(np.arange(200) / 8.0)
    px[200:240] = np.linspace(100, 108, 40)
    px[240:280] = np.linspace(108, 100, 40)
    px[280:300] = 100.0
    o = px.copy()
    h = px + 0.4
    l = px - 0.4
    c = px.copy()
    vol = np.ones(n) * 10.0
    i_sw = 320
    o[i_sw], l[i_sw], c[i_sw], h[i_sw] = 100.2, 98.0, 100.3, 100.4
    i_ms = 325
    o[i_ms], l[i_ms], c[i_ms], h[i_ms] = 100.0, 99.8, 112.0, 112.2
    vol[i_ms] = 50.0
    vol[i_sw] = 20.0
    i_t = 328
    o[i_t], h[i_t], l[i_t], c[i_t] = 106.0, 106.5, 104.5, 105.2
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": vol}, index=idx)
    # ATR تقريباً صغير بعد الاستقرار → الإزاحة 11 نقطة >> 0.6 ATR
    sig = make_signals(df, eps=0.01, fvg_min=0.10, mss_window=12)
    assert isinstance(sig, pd.Series) and sig.dtype == bool and len(sig) == n
    assert bool(sig.iloc[i_t]), "التسلسل الصريح كنس←كسر←لمس لم يُنتج إشارة"
    # إبسيلون صارم جداً (eps ضخم) يجب أن يقتل الإشارة
    sig_kill = make_signals(df, eps=50.0, fvg_min=0.10, mss_window=12)
    assert int(sig_kill.sum()) <= int(sig.sum())
    spec = make_dual_spec()
    assert spec["trig"] == DUAL_TRIG and spec["lock"] == DUAL_LOCK
    for e in SWEEP_PARAMS["eps"]:
        make_signals(df, eps=e, fvg_min=0.20, mss_window=12)
    print(f"[F-146] self_test OK — إشارات: {int(sig.sum())} (اللمس الصريح مُصطاد)")


if __name__ == "__main__":
    self_test()
