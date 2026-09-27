# -*- coding: utf-8 -*-
"""L0067 — أدوات مشتركة: الإطارات، مرشح BTC، تشغيل محرك المختبر، النوافذ."""
from __future__ import annotations
import pathlib, sys, os, json
import numpy as np, pandas as pd
ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
import run_l0061_lc as L  # noqa
import l0067_engine as E  # noqa
CACHE = pathlib.Path.home() / ".cache" / "l0067"
MEMES = ("DOGEUSDT", "SHIBUSDT", "PEPEUSDT")
FULL16 = tuple(L.UNIVERSE)
TARGET13 = tuple(s for s in FULL16 if s not in MEMES)
COST, COST_130 = 0.00115, 0.00130
T = lambda s: pd.Timestamp(s, tz="UTC")
SEL = (T("2021-09-01"), T("2024-01-01"))
JUD = (T("2024-01-01"), T("2026-08-31"))
# نوافذ Walk-Forward: (اسم، بداية الاختيار، نهاية الاختيار=بداية الاختبار، نهاية الاختبار)
WF = [("W1", "2022-09-01", "2023-03-01"), ("W2", "2023-03-01", "2023-09-01"), ("W3", "2023-09-01", "2024-03-01"),
      ("W4", "2024-03-01", "2024-09-01"), ("W5", "2024-09-01", "2025-03-01"), ("W6", "2025-03-01", "2025-09-01"),
      ("W7", "2025-09-01", "2026-03-01"), ("W8", "2026-03-01", "2026-08-31")]
WF = [(n, T(a), T(b)) for n, a, b in WF]
_H4: dict = {}

def h4(sym):
    if sym not in _H4:
        _H4[sym] = pd.read_pickle(CACHE / f"{sym}_4h.pkl")
    return _H4[sym]

def btc_filter(level: str, slope_days: int = 10):
    """M1/M2 على إغلاق BTC اليومي، مزاح يومًا واحدًا (الوسم في اليوم D معروف عند إغلاق D-1)."""
    if level == "M0":
        return None
    d = E._resample(h4("BTCUSDT"), "1D")
    c = d["close"]; e50 = c.ewm(span=50, adjust=False).mean(); e200 = c.ewm(span=200, adjust=False).mean()
    ok = c > e200
    if level == "M2":
        ok = ok & (e50 > e200) & (e50.diff(slope_days) > 0)
    ok = ok.shift(1).fillna(False).astype(bool)
    # لا تخمين قبل توفر بيانات BTC: قبل أول يوم لـBTC لا يوجد مفتاح ⇒ False (غير كافية البيانات)
    return {ts.normalize(): bool(v) for ts, v in ok.items()}

def run_sym(sym, end=None, market=None, tl=None):
    fr = h4(sym)
    if end is not None:
        fr = fr[fr.index < end]
    if len(fr) == 0:
        return []
    return L.from_engine(E.run(fr, sym, market, tl), sym)

def pnl(entry_px, exit_px, notional, cost):
    ep = np.asarray(entry_px, float); xp = np.asarray(exit_px, float)
    return (xp * (1 - cost) / (ep * (1 + cost)) - 1) * np.asarray(notional, float)


# ── نسخ حرفية من run_l0061_measure (ذلك الملف يحمّل سجلات L0061 عند الاستيراد) ──
def rows_in(recs: list[dict], s, e) -> list[dict]:
    return [dict(r) for r in recs if s <= pd.Timestamp(r["entry_time"]) < e]

def cycles(rows):
    out = []
    if not rows:
        return out
    for sym, g in pd.DataFrame(rows).groupby("symbol"):
        g = g.sort_values(["entry_bar", "stage"]); cur = []
        for rec in g.to_dict("records"):
            if int(rec["stage"]) == 0 and cur:
                out.append(cur); cur = []
            cur.append(rec)
        if cur:
            out.append(cur)
    return out

def save_trades(path, rows):
    cols = ["symbol", "entry_time", "exit_time", "entry", "exit", "notional", "pnl", "reason", "stage", "bars_held"]
    if not rows:
        frame = pd.DataFrame(columns=cols)
    else:
        f = pd.DataFrame(rows)
        frame = pd.DataFrame({"symbol": f["symbol"], "entry_time": f["entry_time"], "exit_time": f["exit_time"],
                              "entry": f["entry_ref_px"], "exit": f["exit_px"], "notional": f["notional_usd"],
                              "pnl": f["pnl_usd"].map(lambda x: round(float(x), 4)), "reason": f["reason"],
                              "stage": f["stage"], "bars_held": f["bars_held"]})
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path
