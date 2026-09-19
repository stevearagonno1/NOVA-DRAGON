# -*- coding: utf-8 -*-
# [F-213] القواطع الاتجاهية — إخضاع جناح الدخول الاتجاهي كاملاً (nova_v8/triggers.py)
# لبروتوكول hyp_lab: كل قاطع من الأربعة عشر منفرداً + مركّب النخبة + مركّب الكل.
#
# المصدر: docs/parts/directional-breakers.md (D‑0035) — فرصة التطوير الأولى:
#   «إعادة تقييم الفائض على فريم الساعة فما فوق بحكم مسجل» + أمر القائد 2026-09-19:
#   «ملف القواطع يُجرِّب كل استراتيجياته، ومحادثة مستقلة مرتبطة بالمنصة تجري الباكتست».
#
# الرقم F‑213: أول رقم بعد نطاق مصنع الفرضيات (212 فرضية — docs/HYPOTHESIS-FACTORY.md)
#   فلا يصطدم مع أي فرضية مصنع حالية أو قادمة؛ هذه تجربة جناح محرك لا فرضية مصنع.
#
# الضوابط (موثقة لا مطبّعة):
#   1) طرف طويل فقط — الحواجز الحديدية (لا بيع على المكشوف، لا رافعة).
#   2) الشروط تُستورد حرفياً من nova_v8/triggers.py + nova_v8/indicators.py
#      (المحرك مجمّد: لا يُقرأ للتعديل بل للاستيراد فقط — صفر إعادة كتابة قواعد).
#   3) الاشتعال = حافة صاعدة (edge=True كما في compute_entry_events) فلا إشارة
#      متكررة ما دام الشرط مستمراً.
#   4) مركّبا ELITE8/ALL14 = «الأول اشتعالاً يفتح» على الطرف الطويل = اتحاد الحواف
#      الصاعدة لأعضاء المجموعة (توقيت الدخول مطابق للمحرك؛ وسْم القاطع الفائز بيانات
#      وصفية لا تغيّر الصفقة — ولا نحتاجه في قياس الصافي).
#   5) بدون بوابة النظام (صاعد/هابط) في هذه الجولة — انحراف موثق عن سلوك المحرك
#      الحي، مبرره: عزل جودة المدخل نفسه؛ تفاعل بوابة النظام محور مستقل يُفتح
#      بقرار منفصل بعد نتائج هذه الجولة.
#   6) محور الخروج يديره السائق (run_breakers.py): std (2×ATR/4×ATR) أو dual
#      بتركيبة الجولة الذهبية المقاسة (تسليح 0.0025 / قفل 0.0045 — L0007‑tf1h)
#      وثوابت التتبع من F‑197 نفسها (wide 0.0020 / tight 0.0008) بلا إعادة فحص
#      جديدة — فكسر الإعداد الفائز يحرمنا المقارنة المباشرة مع مرجع L0007.
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = pathlib.Path(__file__).resolve().parents[2]          # جذر المستودع
for _p in (str(_HERE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from nova_v8 import indicators as _ind   # noqa: E402  (قراءة مجمّدة — استيراد فقط)
from nova_v8 import triggers as _trg     # noqa: E402
import F_197_dual_trail as M197          # noqa: E402  (ثوابت التتبع المرجعية)

# النخبة الثمانية — النص الرسمي من ملف القواطع (D‑0035) وdocs/RESEARCH-JUDGMENTS.md §5
ELITE8 = ("MACD", "EMA", "KAMA", "OBV", "ADX", "Stochastic", "SFP", "MSS")
COMPOSITES = ("ELITE8", "ALL14")
TRIGGERS = list(_trg.PRIORITY) + list(COMPOSITES)     # 14 + 2 = 16 قيمة للمحور

SWEEP_PARAMS = {"trigger": TRIGGERS}                  # محور الخروج يديره السائق (كشكل F‑197)
EXITS = ("std", "dual")

# تركيبة الخروج المزدوج الفائزة (مقاسة — history/research/hyp_lab_out/L0007-tf1h):
# كل العابرين الستة على 1h عند trig=0.0025/lock=0.0045 (خمسة من ستة؛ RENDER عند 0.005)
DUAL_TRIG, DUAL_LOCK = 0.0025, 0.0045

_cache: dict[int, dict[str, pd.Series]] = {}


def make_dual_spec() -> dict:
    """مواصفة الخروج المزدوج المثبتة من مرجع F‑197 (بلا إعادة اشتقاق للثوابت)."""
    return M197.make_dual_spec(trig=DUAL_TRIG, lock=DUAL_LOCK)


def _long_triggers(df: pd.DataFrame) -> dict[str, pd.Series]:
    """أعمدة المصفوفة + شروط الطرف الطويل من المحرك — مرة واحدة لكل إطار (كاش خانة واحدة)."""
    key = id(df)
    hit = _cache.get(key)
    if hit is None:
        mat = _ind.compute_matrix(df)
        hit = _trg.build_triggers(mat)["long"]
        _cache.clear()                    # إطار واحد حي: الذاكرة 14 سلسة بوليانية فقط
        _cache[key] = hit
    return hit


def _edge(cond: pd.Series) -> pd.Series:
    c = cond.fillna(False)
    return (c & ~c.shift(1, fill_value=False)).fillna(False)


def make_signals(df: pd.DataFrame, trigger: str = "ELITE8", **_) -> pd.Series:
    """إشارة دخول طويل عند إغلاق الشمعة (التعبئة على افتتاح التالية — عقد common.simulate).

    trigger: اسم قاطع من PRIORITY للاختبار المنفرد، أو ELITE8/ALL14 للمركّب.
    """
    longs = _long_triggers(df)
    if trigger == "ALL14":
        names = list(_trg.PRIORITY)
    elif trigger == "ELITE8":
        names = list(ELITE8)
    elif trigger in _trg.PRIORITY:
        names = [trigger]
    else:
        raise ValueError(f"قاطع مجهول: {trigger!r} — المتاح: {TRIGGERS}")
    sig = None
    for n in names:                       # توقيت «الأول اشتعالاً» على الطرف الطويل
        e = _edge(longs[n])
        sig = e if sig is None else (sig | e)
    return sig.fillna(False)


def self_test():
    """اختبار ذاتي بلا أرشيف: بيانات تركيبية 1h + عقد الوحدة كاملاً."""
    import os
    os.environ.setdefault("NOVA_HOME",
                          str(pathlib.Path.home() / ".nova_scratch" / "selftest_home"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import simulate, atr

    rng = np.random.default_rng(42)
    n = 4000
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    drift = np.linspace(0, 30, n)                       # ميل يوقظ قواطع الاتجاه
    noise = rng.normal(0, 0.4, n).cumsum()
    close = 100 + drift + noise
    o = pd.Series(close, index=idx)
    df = pd.DataFrame({
        "open": o.shift(1).fillna(o.iloc[0]),
        "close": o,
        "high": o + rng.uniform(0.05, 0.6, n),
        "low": o - rng.uniform(0.05, 0.6, n),
        "volume": np.exp(rng.normal(3.0, 0.6, n)),      # فورات حجم توقظ MicroBurst
    }, index=idx)

    sigs = {}
    for t in TRIGGERS:
        s = make_signals(df, trigger=t)
        assert isinstance(s, pd.Series) and s.dtype == bool and len(s) == len(df)
        assert s.index.equals(df.index)
        sigs[t] = s

    # دلالة التركيب: كل قاطع منفرد ⊆ ALL14 وكل عضو نخبة ⊆ ALL14 وELITE8 ⊆ ALL14
    all14 = {i for i, v in sigs["ALL14"].items() if v}
    elite = {i for i, v in sigs["ELITE8"].items() if v}
    assert elite <= all14, "مركّب النخبة خرج عن مركّب الكل"
    for t in _trg.PRIORITY:
        single = {i for i, v in sigs[t].items() if v}
        assert single <= all14, f"القاطع {t} أطلق خارج مركّب الكل"
    assert all14, "لا إشارة إطلاقاً في بيانات حية الصنع — عطل في الأنبوب"
    mash = {i: sigs[t] for t in TRIGGERS for i, v in sigs[t].items() if v}
    assert len(mash) >= n // 500 + 1, "كثافة الإشارات متدهورة (صفر تقريباً)"

    # جدل الخروج: مواصفة dual المثبتة تعمل فعلاً داخل آلة المحاكاة
    st_d, tr_d = simulate(df, sigs["ALL14"], atr(df), exit_mode="dual", dual=make_dual_spec())
    st_s, _ = simulate(df, sigs["ALL14"], atr(df), exit_mode="std")
    assert st_d["trades"] >= 0 and st_s["trades"] >= 0
    spec = make_dual_spec()
    assert spec == {"trig": DUAL_TRIG, "lock": DUAL_LOCK, "wide": M197.WIDE, "tight": M197.TIGHT}

    print(f"[F-213] self_test OK — إشارات: ALL14={int(sigs['ALL14'].sum())} "
          f"ELITE8={int(sigs['ELITE8'].sum())} | dual trades={st_d['trades']} "
          f"net={st_d['net']:.2f}$ | std trades={st_s['trades']} net={st_s['net']:.2f}$")
    per = {t: int(sigs[t].sum()) for t in TRIGGERS}
    print("[F-213] إشارات كل قاطع:", per)


if __name__ == "__main__":
    self_test()
