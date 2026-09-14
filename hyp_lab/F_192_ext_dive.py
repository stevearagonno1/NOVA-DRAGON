# -*- coding: utf-8 -*-
# [F-192] الدخول بالغوص تحت القمة المكسورة ext (قياس V4.1) — دخول
# المصدر: معرفة: NOVA_V4_2_fixed.py.txt (البند 1: قياس ext على 89,970 شمعة) + V5.2 (فيتو المطاردة)
# آلية ext: تُفحص عند سعر التعبئة (افتتاح الشمعة التالية) كحارس إلغاء — لا تدخل أبكر.
# افتراض موثق: فترة EMA في فيتو المطاردة غير محددة في الكتلة → v1: EMA(20)، ema_x=6، ema_pct=8 (قيم V5.2).
from typing import Tuple
import numpy as np
import pandas as pd

from F_126_mss_core import mss_signal

SWEEP_PARAMS = {
    "ext_max": [-0.15, 0.10, 0.50, 1.00],
}


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    """الشرط الآلي حرفياً:
    (MSS صاعد صالح) AND (ext = (سعر الدخول - القمة المكسورة)/ATR <= ext_max)
    AND (ليس (السعر > EMA + 6*ATR AND السعر > EMA*1.08))
    سعر الدخول = افتتاح الشمعة التالية (يُعرف وقت التعبئة)."""
    emax = params.get("ext_max", 0.10)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    base = mss_signal(df)
    hh20 = h.shift(1).rolling(20, min_periods=20).max()
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14, min_periods=14).mean()
    fill = o.shift(-1)                      # افتتاح الشمعة التالية (حارس تعبئة)
    ext = (fill - hh20) / atr14
    ema20 = c.ewm(span=20, adjust=False).mean()   # قيمة إغلاق شمعة الإشارة (معروف وقت التعبئة)
    chase = (fill > ema20 + 6 * atr14) & (fill > ema20 * 1.08)
    sig = base & (ext <= emax) & (~chase)
    return sig.fillna(False)


def self_test():
    rng = np.random.default_rng(42)
    n = 3000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({
        "open": 100 + rng.normal(0, 1, n).cumsum(),
        "volume": rng.uniform(1, 100, n),
    }, index=idx)
    df["close"] = df["open"] + rng.normal(0, 0.5, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng.normal(0, 0.3, n))
    s_dive = make_signals(df, ext_max=-0.15)
    s_any = make_signals(df, ext_max=1.0)
    assert isinstance(s_dive, pd.Series) and s_dive.dtype == bool
    assert int(s_dive.sum()) <= int(s_any.sum()), "سقف غوص صارم يجب أن يقلل الإشارات"
    for p in SWEEP_PARAMS["ext_max"]:
        make_signals(df, ext_max=p)
    print(f"[F-192] self_test OK — إشارات: {int(s_dive.sum())} (غوص≤-0.15) / {int(s_any.sum())} (≤1.0)")


if __name__ == "__main__":
    self_test()
