# -*- coding: utf-8 -*-
"""[L0019 · F-004] اختراق ORB مع إعادة اختبار وفوق VWAP — دخول

عقد الآلة حرفيًا:
  (ORB_high = أعلى high لأول orb_min دقيقة من الجلسة)
  AND (حدث إغلاق فوق ORB_high خلال آخر retest_window شمعة)
  AND (low <= ORB_high) AND (close > ORB_high) AND (close > VWAP)
السويب: orb_min=[5,15,30] × retest_window=[3,6,12] ⇒ 9 تركيبات
المصدر: بحث حر — ChartingLens (ORB Guide / Retest entry) + Reddit r/Daytrading (5m ORB retest)

الجلسة على الكريبتو 24/7 = اليوم UTC. ORB_high لا يُستخدم قبل إغلاق نافذته (حارس سببية).
شراء فقط 🔒.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from L0019_indicators import day_rank, day_rolling_max, vwap_utc

SWEEP_PARAMS = {
    "orb_min": [5, 15, 30],
    "retest_window": [3, 6, 12],
}
BAR_MIN = 5  # الفريم الأصلي للفرضية


def _orb_high(df: pd.DataFrame, bars: int) -> pd.Series:
    """أعلى high لأول `bars` شمعة من اليوم UTC، مبثوثًا على كل شمعة في اليوم.

    أول bars شمعة تُترك NaN (لا ORB معروف بعد) — حارس سببية.
    """
    day = df.index.floor("D")
    rank = day_rank(df)
    mask = rank < bars
    hi = df["high"].where(mask)
    return hi.groupby(day).transform("max").where(rank >= bars)


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    orb_min = params.get("orb_min", 15)
    w = params.get("retest_window", 6)
    bars = max(1, int(round(orb_min / BAR_MIN)))
    c, l = df["close"], df["low"]
    orb = _orb_high(df, bars)
    broke = (c > orb) & orb.notna()
    recent = day_rolling_max(broke, w)
    sig = (orb.notna() & recent & (l <= orb) & (c > orb) & (c > vwap_utc(df)))
    return sig.fillna(False)


def self_test():
    rng = np.random.default_rng(42)
    n = 4000
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": 100 + rng.normal(0, 1, n).cumsum(),
                       "volume": rng.uniform(1, 100, n)}, index=idx)
    df["close"] = df["open"] + rng.normal(0, 0.5, n)
    df["high"] = df[["open", "close"]].max(axis=1) + abs(rng.normal(0, 0.3, n))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(rng.normal(0, 0.3, n))
    orb = _orb_high(df, 3)
    assert orb.iloc[:3].isna().all(), "ORB يجب أن يكون غير معروف في أول 3 شمعات"
    s_lo = make_signals(df, orb_min=30, retest_window=3)
    s_hi = make_signals(df, orb_min=5, retest_window=12)
    assert s_lo.dtype == bool and len(s_lo) == n
    assert int(s_lo.sum()) <= int(s_hi.sum()), "نافذة أضيق + عتبة أعلى يجب ألا تزيد الإشارات"
    k = 0
    for a in SWEEP_PARAMS["orb_min"]:
        for b in SWEEP_PARAMS["retest_window"]:
            make_signals(df, orb_min=a, retest_window=b)
            k += 1
    assert k == 9, f"الشبكة يجب أن تكون 9 لا {k}"
    print(f"[L0019·F-004] self_test OK — 9 تركيبات | إشارات: {int(s_lo.sum())} / {int(s_hi.sum())}")


if __name__ == "__main__":
    self_test()
