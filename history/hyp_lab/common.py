# -*- coding: utf-8 -*-
"""NOVA hyp_lab — آلة اختبار الفرضيات (v1) — كود جديد مستقل، لا يلمس nova_v8/** (مجمّد).

القواعد الموثقة (مصادرها):
- التكاليف (الدستور، الأرقام الحاكمة): عمولة 0.10% + انزلاق قاعدي 0.03% لكل طرف = 0.13% لكل طرف.
- التنفيذ: إشارة عند إغلاق الشمعة → تعبئة على افتتاح الشمعة التالية (عقد الترجمة البرمجية).
- الخروج القياسي (موحّد لكل فرضيات الدخول لعدالة المقارنة): وقف 2.0×ATR14 · هدف 4.0×ATR14
  — القيمتان المعتمدتان في طبقة V4.1 (NOVA_3.txt البند 7: «نُبقي 2.0 ... يبقى 4.0»).
- إن لُمس الوقف والهدف في شمعة واحدة → يُفترض الوقف أولاً (محافظ).
- ⚠️ إصلاح L0046 (2026-09-24): ثلاثة عطوب في التعبئة صُلحت — تفاصيلها في docs/lanes/L0046-VERDICT-engine-repair.md
  (١) القفل كان يُمنح بمجرد التسليح ⇒ تعبئة فوق السوق · (٢) لا حارس نطاق على سعر الخروج ·
  (٣) مسار الإغلاق النهائي كان يخصم الكلفة مرتين. النسخة المعطوبة محفوظة: common_broken_preL0046.py
- مسطرة المختبر (الدستور §27، حكم القائد 2026-09-20): صفقة واحدة = 20$ ثابت.
  محفظة التجربة = 1000$ ورقية لكل عملة/تجربة (2% للصفقة — لا المحفظة كلها).
  1000$ للصفقة ملغاة. فرضية التحجيم F-204 تبقى استثناءً مكتوباً داخل خطتها فقط.
- ATR14 = متوسط متحرك لمدى السعة الحقيقي (TR) على 14 شمعة.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEE_PER_SIDE = 0.0010
SLIP_PER_SIDE = 0.0003
COST_PER_SIDE = FEE_PER_SIDE + SLIP_PER_SIDE
STOP_ATR = 2.0
TP_ATR = 4.0
TRADE_USD = 20.0
EXPERIMENT_BOOK_USD = 1000.0
BASE_NOTIONAL = TRADE_USD  # كان 1000.0 — أُلغي بحكم القائد 2026-09-20


def load(path: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """قراءة باركيه دقي → إطار دقي مرتب.

    وحدة open_time تُكتشف من حجمها: data/ بالميكروثانية (≈1.8e15) و
    crypto_archive/ بالميلي ثانية (≈1.6e12) — عتبة 1e14 تفصل الواقعيين.
    """
    df = pd.read_parquet(path)
    v = int(df["open_time"].iloc[0])
    unit = "ms" if abs(v) < 10**14 else "us"
    ts = pd.to_datetime(df["open_time"], unit=unit, utc=True)
    out = df[["open", "high", "low", "close", "volume"]].astype(float).copy()
    out.index = ts
    out = out[~out.index.duplicated(keep="first")].sort_index()
    if start:
        out = out[out.index >= pd.Timestamp(start, tz="UTC")]
    if end:
        out = out[out.index < pd.Timestamp(end, tz="UTC")]
    return out.dropna()


def to_5m(df1m: pd.DataFrame) -> pd.DataFrame:
    return df1m.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()


TF_MINUTES = {"5m": 5, "1h": 60, "4h": 240}


def to_bars(df1m: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """تجميع الدقي إلى شبكة أعلى (1h/4h) — نفس قواعد to_5m حرفياً.

    label=left, closed=left، والاصطفاف من 00:00 UTC (origin=start_day):
    1h → شموع ساعية، 4h → 00/04/08/12/16/20 — الاصطفاف المعياري لشمعات الكريبتو.
    ملاحظة مسماة: مسار 5m يبقى عبر to_5m نفسه (مطابقة بايت‑ببايت لملفات L0007 المرجعية).
    """
    return df1m.resample(f"{minutes}min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def hh(df: pd.DataFrame, n: int) -> pd.Series:
    """أعلى high لآخر n شمعة باستثناء الحالية (دليل الرموز)."""
    return df["high"].shift(1).rolling(n, min_periods=n).max()


def ll(df: pd.DataFrame, n: int) -> pd.Series:
    return df["low"].shift(1).rolling(n, min_periods=n).min()


def _close_position(p: dict, j: int, price: float, side: str) -> None:
    # ── إصلاح L0046 (١): حارس إلزامي — سعر التعبئة يُقيَّد بنطاق الشمعة [low, high] ──
    #    فيستحيل تسجيل تعبئة بسعر لم تتداوله السوق في تلك الشمعة.
    #    (p["_lo"]/p["_hi"] مراجع لمصفوفات الشمعة نفسها — لا نسخ ولا ذاكرة إضافية.)
    _lo = p["_lo"][j]; _hi = p["_hi"][j]
    if price < _lo:
        price = _lo
    elif price > _hi:
        price = _hi
    fill = price * (1 - COST_PER_SIDE)
    qty = p["notional"] / p["entry"]
    p["pnl"] = qty * (fill - p["entry"])
    p["exit_fill"] = fill
    p["exit_j"] = j
    p["exit_time"] = p["idx"][j]
    p["exit_side"] = side
    p["done"] = True


def simulate(df: pd.DataFrame, sig: pd.Series, atr_s: pd.Series,
             exit_mode: str = "std", dual: dict | None = None,
             sizing: dict | None = None, max_per: int = 1,
             cooldown_s: float = 0.0, notional: float = BASE_NOTIONAL,
             bar_secs: int = 300, strict_single: bool = False,
             atr_trail: float = 0.0):
    """حلقة الصفقات. ترجع (stats, trades).

    - sig: بولياني عند إغلاق الشمعة. الدخول على افتتاح الشمعة التالية.
    - exit_mode='std': وقف STOP_ATR×ATR + هدف TP_ATR×ATR (أقصى مركز واحد افتراضياً).
    - exit_mode='dual' (F-197): وقف قاسي أولي كما هو + مطاردة ثنائية السرعة:
      يُسلّح عند peak_gain ≥ trig؛ stop_local = max(entry×(1+lock), peak×(1−trail))؛
      trail = wide إذا peak_gain ≤ 1% وإلا tight؛ الفعّال = min(القاسي، المحلّي).
      لا هدف ثابت في هذا الوضع (التتبع هو المخرج — كما في التصميم الأصلي).
    - sizing (F-204): {R, cap, halve_vr, vr} → قيمة اسمية بمتكافؤ المخاطرة + حارس 1.05R.
    - max_per/cooldown_s (F-205): مراكز متعددة + تهدئة بالسانية.
    - strict_single (L0048، افتراضي False): إن True، لا يُفتح مركز جديد ما دام آخر
      مفتوحًا على السلسلة نفسها. الافتراضي False يُبقي مسار max_per==1 القديم حرفيًا
      (بما فيه عطب نسيان الانشغال). لا يُفعَّل إلا مع max_per==1 وcooldown_s==0.
    - atr_trail (L0048، افتراضي 0): إن >0، الخروج = وقف قاسٍ STOP_ATR×ATR
      + تتبّع atr_trail×ATR تحت القمة (ATR لحظة الإشارة، ثابت). لا تسليح ولا قفل
      ولا هدف. الافتراضي 0 لا يلمس مسار الخروج القديم.
    """
    o = df["open"].to_numpy(); h = df["high"].to_numpy()
    l = df["low"].to_numpy(); c = df["close"].to_numpy()
    a = atr_s.to_numpy()
    n = len(df)
    idx = df.index
    sig_b = sig.to_numpy()
    sig_i = np.flatnonzero(sig_b)
    if sig_i.size == 0:
        return {"net": 0.0, "trades": 0, "wins": 0, "losses": 0, "win_pct": 0.0,
                "gross": 0.0, "costs": 0.0, "risk_total": 0.0}, []

    trades: list[dict] = []
    vr_arr = (sizing["vr"].to_numpy() if sizing is not None else None)

    def _open(i: int) -> dict | None:
        e = i + 1
        if e >= n or not np.isfinite(a[i]):
            return None
        ef = o[e] * (1 + COST_PER_SIDE)
        sl_dist = STOP_ATR * a[i]
        notl = notional
        risk = None
        if sizing is not None:
            R, cap, hv = sizing["R"], sizing["cap"], sizing["halve_vr"]
            vr = vr_arr[i]
            notl = min(R * ef / sl_dist, cap)
            if np.isfinite(vr) and vr > hv:
                notl /= 2.0
            risk = notl * sl_dist / ef
            if risk > R * 1.05:
                notl *= (R * 1.05) / risk
                risk = R * 1.05
        return {
            "entry_j": e, "entry": ef, "entry_time": idx[e],
            "atr_sig": a[i], "notional": notl, "risk": risk,
            "hard_stop": ef - STOP_ATR * a[i],
            "tp": ef + TP_ATR * a[i],
            "peak": o[e], "done": False, "pnl": 0.0, "idx": idx,
            "_lo": l, "_hi": h,          # إصلاح L0046: مرجعا نطاق الشمعة لحارس التعبئة
            "trig": dual["trig"] if dual else None,
            "lock": dual["lock"] if dual else None,
            "wide": dual["wide"] if dual else None,
            "tight": dual["tight"] if dual else None,
            **({"atr_trail": float(atr_trail)} if atr_trail and atr_trail > 0 else {}),
        }

    def _step(p: dict, j: int) -> bool:
        """فحص خروج المركز عند شمعة j بحالة ما قبل الشمعة (محافظ).

        ── إصلاح L0046 (٢) ──
        (أ) لا يُرفع الوقف إلى مستوى القفل (lock) إلا إذا بلغ السعر ذلك المستوى فعلًا
            (peak >= entry*(1+lock)). سابقًا كان القفل يُمنح بمجرد التسليح (trig) — أي
            يُحجز ربح 0.60% وقد ربحت 0.15% فقط ⇒ تعبئة مستحيلة.
        (ب) عند الوقف: إن فتحت الشمعة تحت المستوى (فجوة هابطة) فالتعبئة عند الافتتاح لا
            عند مستوى الوقف — لا تعبئة بسعر أفضل من الواقع.
        (ج) عند الهدف: إن فتحت الشمعة فوق الهدف (فجوة صاعدة) فالتعبئة عند الافتتاح.
        وحارس النطاق في _close_position يضمن الاستحالة مطلقًا.
        """
        if p.get("atr_trail"):
            eff = p["hard_stop"]
            local = p["peak"] - p["atr_trail"] * p["atr_sig"]
            if local > eff:
                eff = local
            if l[j] <= eff:
                fill = eff if o[j] >= eff else o[j]
                _close_position(p, j, fill, "stop")
                return True
            p["peak"] = max(p["peak"], h[j])
            return False
        eff = p["hard_stop"]
        if p["trig"] is not None:
            peak = p["peak"]
            gain = (peak - p["entry"]) / p["entry"]
            if gain >= p["trig"]:
                trail = p["wide"] if gain <= 0.01 else p["tight"]
                local = peak * (1 - trail)
                if peak >= p["entry"] * (1 + p["lock"]):     # إصلاح L0046(أ)
                    local = max(local, p["entry"] * (1 + p["lock"]))
                eff = max(eff, local)   # الوقف يتسلق للأعلى فقط
        if l[j] <= eff:
            fill = eff if o[j] >= eff else o[j]              # إصلاح L0046(ب)
            _close_position(p, j, fill, "stop")
            return True
        if p["trig"] is None and h[j] >= p["tp"]:
            _close_position(p, j, max(p["tp"], o[j]), "tp")  # إصلاح L0046(ج)
            return True
        if p["trig"] is not None:
            p["peak"] = max(p["peak"], h[j])
        return False

    def _run_to_exit(p: dict) -> None:
        j = p["entry_j"]
        while j < n and not _step(p, j):
            j += 1
        if not p["done"]:
            _close_position(p, n - 1, c[-1], "eod")   # إصلاح L0046: الكلفة تُخصم مرة واحدة

    if strict_single and not (max_per == 1 and cooldown_s == 0):
        raise ValueError("strict_single يتطلب max_per==1 و cooldown_s==0")
    if max_per == 1 and cooldown_s == 0:
        if strict_single:
            last_exit = -1
            for i in sig_i:
                if last_exit > i:
                    continue
                p = _open(i)
                if p is None:
                    continue
                _run_to_exit(p)
                trades.append(p)
                last_exit = int(p["exit_j"])
        else:
            pos = None
            for i in sig_i:
                if pos is not None:
                    _run_to_exit(pos)
                    trades.append(pos)
                    if pos["exit_j"] > i:   # ما زالت مفتوحة عند هذه الإشارة → تُهمَل
                        pos = None
                        continue
                    pos = None
                p = _open(i)
                if p is None:
                    continue
                pos = p
            if pos is not None:
                _run_to_exit(pos)
                trades.append(pos)
    else:
        open_pos: list[dict] = []
        last_entry_j = -10**9
        for j in range(n):
            still: list[dict] = []
            for p in open_pos:
                if not p["done"]:
                    _step(p, j)
                if p["done"]:
                    trades.append(p)
                else:
                    still.append(p)
            open_pos = still
            if j > 0 and sig_b[j - 1]:
                if len(open_pos) < max_per and (j - last_entry_j) * bar_secs >= cooldown_s:
                    p = _open(j - 1)
                    if p is not None:
                        open_pos.append(p)
                        last_entry_j = p["entry_j"]
        for p in open_pos:
            if not p["done"]:
                _close_position(p, n - 1, c[-1], "eod")   # إصلاح L0046: الكلفة تُخصم مرة واحدة
            trades.append(p)

    trades.sort(key=lambda p: p["entry_j"])
    net = float(sum(p["pnl"] for p in trades))
    wins = sum(1 for p in trades if p["pnl"] > 0)
    costs = 0.0
    for p in trades:
        qty = p["notional"] / p["entry"]
        costs += qty * (p["entry"] * COST_PER_SIDE + p["exit_fill"] * COST_PER_SIDE)
    risk_total = float(sum(p["risk"] for p in trades if p["risk"] is not None))
    stats = {
        "net": net, "trades": len(trades), "wins": wins,
        "losses": len(trades) - wins,
        "win_pct": round(100.0 * wins / len(trades), 2) if trades else 0.0,
        "gross": net + costs, "costs": costs, "risk_total": risk_total,
    }
    return stats, trades


def trade_rows(symbol: str, exp: str, trades: list[dict]) -> list[dict]:
    rows = []
    for p in trades:
        rows.append({
            "symbol": symbol, "exp": exp,
            "entry_time": p["entry_time"].isoformat(),
            "exit_time": p["exit_time"].isoformat(),
            # إصلاح L0046 (تدقيقي): دقة كاملة بدل 6 خانات — التقريب إلى 6 خانات كان
            # يدمّر أسعار العملات دون السنت (PEPE/SHIB ≈ 8e-06) فيستحيل تدقيق التعبئة.
            # لا أثر على الأرباح: pnl و notional كما هي.
            "entry": float(f"{p['entry']:.12g}"), "exit": float(f"{p['exit_fill']:.12g}"),
            "notional": round(p["notional"], 2),
            "pnl": round(p["pnl"], 4),
            "r_mult": round(p["pnl"] / p["risk"], 3) if p["risk"] else "",
            "exit_side": p["exit_side"],
            "bars_held": p["exit_j"] - p["entry_j"],
        })
    return rows
