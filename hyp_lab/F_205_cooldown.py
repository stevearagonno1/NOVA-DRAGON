# -*- coding: utf-8 -*-
# [F-205] الهرم المهدّأ + معرّف الإعداد (إدارة مراكز) — إدارة حصة
# المصدر: معرفة: NOVA (2).txt (v3.2 تهدئة 300ث) + V5.0 (Setup ID + تهدئة BTC-VR) + البوت الهجين
# السائق التجريبي (موثق): نواة MSS على شبكة 1m (نفس منطق F-126) — لتفصل A/B آلية
# التهدئة فقط. معرّف الإعداد (رمز@شمعة) مضمون بنيوياً: إشارة واحدة لكل شمعة.
# التهديئة بالسانية على شبكة 1m: 120ث = شمعان، 300ث = 5 شموع.
from typing import Tuple
import numpy as np
import pandas as pd

from F_126_mss_core import mss_signal

SWEEP_PARAMS = {
    "cooldown_s": [120.0, 300.0],
    "max_per": [2, 3],
}


def driver_signals_1m(df1m: pd.DataFrame) -> pd.Series:
    """سائق MSS على الدقي (قيم F-126 الافتراضية)."""
    return mss_signal(df1m, body_ratio=0.50, range_atr=0.80, lookback=20)


def make_signals(df: pd.DataFrame, **params) -> pd.Series:
    # على شبكة 1m (جولة هذه الفرضية)
    return driver_signals_1m(df)


def self_test():
    """اختبار ذاتي: التهدئة الطويلة يجب أن تقلل عدد الدخولات على نفس السائق."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import simulate, atr
    rng = np.random.default_rng(42)
    n = 4000
    idx = pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC")
    # حركة موجية متكررة تُنتج كسوراً متقاربة
    px = 100 + 3 * np.sin(np.arange(n) / 40.0) + rng.normal(0, 0.15, n).cumsum() * 0.02
    o = pd.Series(px, index=idx)
    df = pd.DataFrame({
        "open": o, "close": o.shift(-1).fillna(o.iloc[-1]),
        "high": np.maximum(o, o.shift(-1).fillna(o.iloc[-1])) + 0.05,
        "low": np.minimum(o, o.shift(-1).fillna(o.iloc[-1])) - 0.05,
        "volume": np.ones(n),
    }, index=idx)
    sig = make_signals(df)
    assert isinstance(sig, pd.Series) and sig.dtype == bool and len(sig) == len(df)
    # اختبار حتمي للبوابة: 3 إشارات متباعدة شمعان (120ث)
    # 300ث → يفتح واحد فقط (120ث و240ث < 300ث) | 120ث → يفتح الثلاثة (max_per=3)
    burst = pd.Series(False, index=idx)
    burst.iloc[[100, 102, 104]] = True
    st_c5, _ = simulate(df, burst, atr(df), max_per=3, cooldown_s=300.0, bar_secs=60)
    st_c2, _ = simulate(df, burst, atr(df), max_per=3, cooldown_s=120.0, bar_secs=60)
    assert st_c5["trades"] == 1, f"تهدئة 300ث: المتوقع دخول واحد، وجدنا {st_c5['trades']}"
    assert st_c2["trades"] == 3, f"تهدئة 120ث: المتوقع ثلاثة دخولات، وجدنا {st_c2['trades']}"
    print(f"[F-205] self_test OK — بوابة التهديئة: 300ث→{st_c5['trades']} دخول، 120ث→{st_c2['trades']} دخول")


if __name__ == "__main__":
    self_test()
