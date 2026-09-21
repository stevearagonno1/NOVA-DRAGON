# -*- coding: utf-8 -*-
"""L0017 — اشتقاق إحصاءات التقرير (القسم ٢٣): سلة العابرين · المخاطر · الاحتفاظ · الجوار.

لا إعادة تشغيل للإشارات: يقرأ trades.csv المودعة من جولة L0017 كما هي.
الاحتفاظ: يُقاس على نفس نافذة الامتحان بنفس المسطرة (20$ يُشترى ويُحتفظ) — شرط المبدأ 6.
الجوار: يُقرأ من sweep_train/test ولا يُفترض؛ ما لا يُقاس يُكتب «غير مقاس».
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

HIST = pathlib.Path(__file__).resolve().parents[1]
ROOT = HIST.parent
O = HIST / "research" / "hyp_lab_out"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import load, to_bars, TF_MINUTES, COST_PER_SIDE, TRADE_USD  # noqa: E402

TEST_START, TEST_END = "2025-01-01", "2026-08-31"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XLMUSDT", "LINKUSDT", "GRAMUSDT", "RENDERUSDT", "FILUSDT"]


def drawdown(times: pd.Series, pnl: np.ndarray):
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    i = int(np.argmax(dd))
    if dd[i] <= 0:
        return 0.0, 0.0
    j = int(np.argmax(eq[:i + 1])) if i > 0 else 0
    days = (times.iloc[i] - times.iloc[j]).total_seconds() / 86400
    return float(dd[i]), float(days)


def longest_loss_streak(pnl: np.ndarray) -> int:
    best = cur = 0
    for x in pnl:
        cur = cur + 1 if x < 0 else 0
        best = max(best, cur)
    return best


def basket(lane: str, tf: str) -> pd.DataFrame:
    rows = []
    for exp_dir in sorted((O / lane).iterdir()):
        f = exp_dir / "all_symbols_test.csv"
        if not exp_dir.is_dir() or not f.exists():
            continue
        t = pd.read_csv(f, encoding="utf-8-sig")
        for _, r in t[t["gate"] == True].iterrows():          # noqa: E712
            tp = exp_dir / r["symbol"] / "trades.csv"
            if tp.exists():
                d = pd.read_csv(tp, encoding="utf-8-sig")
                if len(d):
                    d["exp"] = exp_dir.name
                    rows.append(d)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def stats(d: pd.DataFrame, tf: str, label: str) -> dict:
    d = d.copy()
    d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
    d = d.sort_values("exit_time").reset_index(drop=True)
    p = d["pnl"].to_numpy(float)
    w, l = p[p > 0], p[p < 0]
    g, lo = w.sum(), -l.sum()
    dd, dd_days = drawdown(d["exit_time"], p)
    day = d.groupby(d["exit_time"].dt.date)["pnl"].sum()
    bar_h = TF_MINUTES[tf] / 60
    return {
        "سلة": label, "صفقات": len(d), "صافي$": round(float(p.sum()), 2),
        "نصيب الصفقة$": round(float(p.sum() / len(d)), 4),
        "عامل الربح": round(float(g / lo), 4) if lo > 0 else np.inf,
        "فوز%": round(100 * float((p > 0).mean()), 2),
        "متوسط الرابحة$": round(float(w.mean()), 4) if len(w) else 0.0,
        "متوسط الخاسرة$": round(float(l.mean()), 4) if len(l) else 0.0,
        "عضلة النسبة": round(float(w.mean() / abs(l.mean())), 3) if len(l) and len(w) else np.inf,
        "توقع الصفقة$": round(float((p > 0).mean() * (w.mean() if len(w) else 0)
                                    + (p < 0).mean() * (l.mean() if len(l) else 0)), 4),
        "عمولات$": round(2 * COST_PER_SIDE * TRADE_USD * len(d), 2),
        "أقصى هبوط$": round(dd, 2), "مدة الهبوط(يوم)": round(dd_days, 1),
        "أسوأ يوم$": round(float(day.min()), 2),
        "أطول سلسلة خسائر": longest_loss_streak(p),
        "زمن الاحتفاظ(ساعة)": round(float(d["bars_held"].mean()) * bar_h, 2),
    }


def buy_hold() -> pd.DataFrame:
    rows = []
    for sym in SYMBOLS:
        p = ROOT / "crypto_archive" / f"{sym}_1m.parquet"
        df = load(str(p), start=TEST_START, end=TEST_END)
        if not len(df):
            continue
        e = float(df["open"].iloc[0]) * (1 + COST_PER_SIDE)
        x = float(df["close"].iloc[-1]) * (1 - COST_PER_SIDE)
        rows.append({"symbol": sym, "entry": round(e, 6), "exit": round(x, 6),
                     "net_20usd$": round(TRADE_USD / e * (x - e), 4),
                     "ret%": round(100 * (x - e) / e, 2),
                     "from": str(df.index[0].date()), "to": str(df.index[-1].date())})
    return pd.DataFrame(rows)


def main() -> int:
    out = O / "L0017-stats"
    out.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 250)

    all_rows = []
    per_exp_rows = []
    for tf, lane in (("1h", "L0017-tf1h"), ("4h", "L0017-tf4h")):
        d = basket(lane, tf)
        if not len(d):
            continue
        all_rows.append(stats(d, tf, f"عابرو {tf} (كل الفرضيات)"))
        for exp, sub in d.groupby("exp"):
            r = stats(sub, tf, f"{exp} · {tf}")
            per_exp_rows.append(r)

    b = pd.DataFrame(all_rows)
    e = pd.DataFrame(per_exp_rows)
    b.to_csv(out / "basket_stats.csv", index=False, encoding="utf-8-sig")
    e.to_csv(out / "by_hypothesis_stats.csv", index=False, encoding="utf-8-sig")

    bh = buy_hold()
    bh.to_csv(out / "buy_and_hold_test.csv", index=False, encoding="utf-8-sig")

    print("=== سلة العابرين ===");  print(b.to_string(index=False))
    print("\n=== بالفرضية ===");     print(e.to_string(index=False))
    print("\n=== الشراء والاحتفاظ على نافذة الامتحان (20$ للرمز) ===")
    print(bh.to_string(index=False))
    print(f"\nمجموع الاحتفاظ للثمانية: {bh['net_20usd$'].sum():.2f}$ "
          f"(موجب {int((bh['net_20usd$'] > 0).sum())}/{len(bh)})")
    print(f"→ {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
