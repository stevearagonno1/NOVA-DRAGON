# -*- coding: utf-8 -*-
"""NOVA hyp_lab — آلة اختبار الفرضيات (v1) — كود جديد مستقل، لا يلمس nova_v8/** (مجمّد).

القواعد الموثقة (مصادرها):
- التكاليف (الدستور، الأرقام الحاكمة): عمولة 0.10% + انزلاق قاعدي 0.03% لكل طرف = 0.13% لكل طرف.
- التنفيذ: إشارة عند إغلاق الشمعة → تعبئة على افتتاح الشمعة التالية (عقد الترجمة البرمجية).
- الخروج القياسي (موحّد لكل فرضيات الدخول لعدالة المقارنة): وقف 2.0×ATR14 · هدف 4.0×ATR14
  — القيمتان المعتمدتان في طبقة V4.1 (NOVA_3.txt البند 7: «نُبقي 2.0 ... يبقى 4.0»).
- إن لُمس الوقف والهدف في شمعة واحدة → يُفترض الوقف أولاً (محافظ).
- رأس المال: قيمة اسمية ثابتة 1000$ لكل صفقة (إلا فرضية التحجيم F-204).
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
BASE_NOTIONAL = 1000.0


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
             bar_secs: int = 300):
    """حلقة الصفقات. ترجع (stats, trades).

    - sig: بولياني عند إغلاق الشمعة. الدخول على افتتاح الشمعة التالية.
    - exit_mode='std': وقف STOP_ATR×ATR + هدف TP_ATR×ATR (أقصى مركز واحد افتراضياً).
    - exit_mode='dual' (F-197): وقف قاسي أولي كما هو + مطاردة ثنائية السرعة:
      يُسلّح عند peak_gain ≥ trig؛ stop_local = max(entry×(1+lock), peak×(1−trail))؛
      trail = wide إذا peak_gain ≤ 1% وإلا tight؛ الفعّال = min(القاسي، المحلّي).
      لا هدف ثابت في هذا الوضع (التتبع هو المخرج — كما في التصميم الأصلي).
    - sizing (F-204): {R, cap, halve_vr, vr} → قيمة اسمية بمتكافؤ المخاطرة + حارس 1.05R.
    - max_per/cooldown_s (F-205): مراكز متعددة + تهدئة بالسانية.
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
            "trig": dual["trig"] if dual else None,
            "lock": dual["lock"] if dual else None,
            "wide": dual["wide"] if dual else None,
            "tight": dual["tight"] if dual else None,
        }

    def _step(p: dict, j: int) -> bool:
        """فحص خروج المركز عند شمعة j بحالة ما قبل الشمعة (محافظ)."""
        eff = p["hard_stop"]
        if p["trig"] is not None:
            peak = p["peak"]
            gain = (peak - p["entry"]) / p["entry"]
            if gain >= p["trig"]:
                trail = p["wide"] if gain <= 0.01 else p["tight"]
                local = max(p["entry"] * (1 + p["lock"]), peak * (1 - trail))
                eff = max(eff, local)   # الوقف يتسلق للأعلى فقط
        if l[j] <= eff:
            _close_position(p, j, eff, "stop")
            return True
        if p["trig"] is None and h[j] >= p["tp"]:
            _close_position(p, j, p["tp"], "tp")
            return True
        if p["trig"] is not None:
            p["peak"] = max(p["peak"], h[j])
        return False

    def _run_to_exit(p: dict) -> None:
        j = p["entry_j"]
        while j < n and not _step(p, j):
            j += 1
        if not p["done"]:
            _close_position(p, n - 1, c[-1] * (1 - COST_PER_SIDE), "eod")

    if max_per == 1 and cooldown_s == 0:
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
                _close_position(p, n - 1, c[-1] * (1 - COST_PER_SIDE), "eod")
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
            "entry": round(p["entry"], 6), "exit": round(p["exit_fill"], 6),
            "notional": round(p["notional"], 2),
            "pnl": round(p["pnl"], 4),
            "r_mult": round(p["pnl"] / p["risk"], 3) if p["risk"] else "",
            "exit_side": p["exit_side"],
            "bars_held": p["exit_j"] - p["entry_j"],
        })
    return rows
