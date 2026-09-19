# -*- coding: utf-8 -*-
"""L0015 — حجم المركز على رأس المال الحقيقي (المحفظة 13 على 4h).

الأرقام الحاكمة من live/LIVE-TRADING-RULES.md (ملزمة):
  البداية 200$ + 200$ شهريًا · حجم الصفقة 5% (ثم 15% بعد النضج) من رأس المال · وقف يومي ‏−3%‏
  ⇒ توقف اليوم · قاطع ‏−25%‏ من القمة التاريخية ⇒ توقف كلي ومراجعة.

الطريقة: إعادة تشغيل سلاسل الصفقات المودعة (لا إعادة حساب إشارات) بقيود رأس المال الحقيقي:
  • كل صفقة تأخذ حصة F من رأس المال اللحظي (Equity لحظة الدخول) — والنسبة تعوَّم من 1000$ الاسمي.
  • النقدية قيد (Spot): لا صفقة إلا إذا كان النقد الحر يكفي الحصة ⇒ الصفقات التي لا تكفيها النقدية تُعدّ «فاتت».
  • التمويل الشهري 200$ في أول كل شهر.
  • الوقف اليومي ‏−3%‏: خسارة اليوم المحققة توقف الدخول الجديد لبقية اليوم.
  • القاطع ‏−25%‏ من القمة: عند بلوغه يتوقف الدخول الجديد كليًا ويُوثّق اليوم.
  • توسيم: الربح/الخسارة للصفقة يُقاس لحظة الإغلاق (لا توسيم لحظي للصفقات المفتوحة — تقريب معلن).

المخرجات: مقاييس لكل سيناريو + منحنى شهري + سجل أيام الوقف والقاطع + مقارنة الاحتفاظ (بيتكوين بنفس الخطة).
"""
from __future__ import annotations

import heapq
import pathlib
import sys

import numpy as np
import pandas as pd

HERE = pathlib.Path("/home/user/.work/pf")
OUT = pathlib.Path("/home/user/.work/sizing/out")
OUT.mkdir(parents=True, exist_ok=True)

CAPITAL_START = 200.0
MONTHLY = 200.0
DAILY_STOP = -0.03
BREAKER = -0.25
START = pd.Timestamp("2025-01-01", tz="UTC")
END = pd.Timestamp("2026-08-31 23:59:59", tz="UTC")


def load_trades() -> pd.DataFrame:
    frames = []
    for folder in ("base10", "base13"):
        for p in sorted((HERE / folder).glob("*.csv")):
            d = pd.read_csv(p, encoding="utf-8-sig")
            d["entry_time"] = pd.to_datetime(d["entry_time"], utc=True)
            d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
            frames.append(d[["symbol", "entry_time", "exit_time", "notional", "pnl", "bars_held"]])
    t = pd.concat(frames, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    return t


def deposits_between(a: pd.Timestamp, b: pd.Timestamp) -> list[pd.Timestamp]:
    """التمويل الشهري: 200$ في أول كل شهر ميلادي (بتوقيت UTC)."""
    months = pd.date_range(a.normalize().replace(day=1), b, freq="MS", tz="UTC")
    return [m for m in months]


def run_case(trades: pd.DataFrame, frac: float, cap: float | None = None,
             label: str = "") -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """تشغيل محفظة بقيود النقد والوقف اليومي والقاطع. frac = نسبة الحصة من رأس المال.

    cap: سقف الحصة بالدولار — ضروري للأمانة: نموذج الكلفة الثابتة (0.13%/طرف) لا يصلح
    لأحجام تفوق ما قُيست عليه السجلات (1000$ اسمي)، فالسقف يمنع «ربح مركّب على ورق».
    """
    cash = CAPITAL_START
    equity = CAPITAL_START
    peak = equity
    open_heap: list[tuple] = []       # (exit_time, notional, pnl_scaled)
    open_notional = 0.0
    taken = skipped_cash = 0
    halted_at = None
    breaker_hits = []
    stop_days = []
    day_start_equity = {}
    day_pnl = {}
    events = []
    for _, r in trades.iterrows():
        events.append((r["entry_time"], 0, r))
        events.append((r["exit_time"], 1, r))
    events.sort(key=lambda e: (e[0], e[1]))      # الخروج قبل الدخول في نفس اللحظة (تحرير النقد أولاً)

    dep_set = set(deposits_between(START, END))
    eq_rows = []
    last_equity_snap = equity
    for ts, kind, r in events:
        day = ts.normalize()
        if day in dep_set:
            cash += MONTHLY
            equity += MONTHLY
            dep_set.discard(day)
            eq_rows.append({"time": ts, "equity": equity, "cash": cash,
                            "event": "deposit"})
        if day not in day_start_equity:
            day_start_equity[day] = equity
            day_pnl[day] = 0.0
        if kind == 1:      # خروج
            # ابحث في الكومة عن هذا المركز وأغلق أول تطابق زمني
            for i, (xt, nt, pn) in enumerate(open_heap):
                if xt == ts and abs(nt) > 0:
                    open_heap.pop(i)
                    open_notional -= nt
                    cash += nt + pn
                    equity += pn
                    day_pnl[day] = day_pnl.get(day, 0.0) + pn
                    break
            heapq.heapify(open_heap)
            peak = max(peak, equity)
            if equity <= (1 + BREAKER) * peak:
                if halted_at is None:
                    halted_at = ts
                    breaker_hits.append({"time": str(ts), "equity": round(equity, 2),
                                         "peak": round(peak, 2), "drawdown_pct": round(100 * (equity / peak - 1), 2)})
            eq_rows.append({"time": ts, "equity": equity, "cash": cash, "event": "exit"})
            continue
        # دخول
        if halted_at is not None:
            skipped_cash += 1
            continue
        start_eq = day_start_equity[day]
        if day_pnl.get(day, 0.0) <= DAILY_STOP * start_eq:
            if day not in [d for d in stop_days]:
                stop_days.append(str(day.date()))
            skipped_cash += 1
            continue
        notional = frac * equity
        if cap is not None:
            notional = min(notional, cap)
        if notional <= 0:
            skipped_cash += 1
            continue
        free_cash = cash - open_notional
        if notional > free_cash + 1e-9:
            skipped_cash += 1
            continue
        cash -= 0.0     # الحصة تُحتجز: تُخصم من المتاح عبر open_notional
        pnl_scaled = (r["pnl"] / r["notional"]) * notional
        open_heap.append((r["exit_time"], notional, pnl_scaled))
        heapq.heapify(open_heap)
        open_notional += notional
        taken += 1

    final_equity = equity
    contrib = CAPITAL_START + MONTHLY * len(deposits_between(START, END))
    eq = pd.DataFrame(eq_rows)
    if not eq.empty:
        eq["time"] = pd.to_datetime(eq["time"], utc=True)
        eq = eq[eq.event.isin(["exit", "deposit"])]
        eq = eq[eq.time >= START]
        eq["equity"] = eq["equity"].round(2)
    # منحنى شهري
    monthly = None
    if not eq.empty:
        m = eq.assign(month=eq["time"].dt.tz_localize(None).dt.to_period("M")).groupby("month")["equity"].last()
        monthly = m.reset_index()
    peak_final = eq["equity"].max() if not eq.empty else equity
    max_dd = 0.0
    if not eq.empty:
        roll = eq["equity"].cummax()
        dd = (eq["equity"] - roll) / roll
        max_dd = float(dd.min() * 100)
    worst_day_pct = None
    if day_pnl:
        rows = []
        for d, pnl in day_pnl.items():
            base = day_start_equity.get(d)
            if base and base > 0:
                rows.append(100 * pnl / base)
        worst_day_pct = round(min(rows), 2) if rows else None
        breach_days = sum(1 for x in rows if x <= -3.0)
    else:
        breach_days = 0
    metrics = {
        "case": label or f"F={frac:.0%}",
        "frac_per_trade": f"{frac:.0%}",
        "notional_cap": cap if cap else "بلا سقف",
        "trades_taken": taken, "trades_skipped_no_cash": skipped_cash,
        "skip_rate": f"{100*skipped_cash/max(1,taken+skipped_cash):.1f}%",
        "final_equity": round(final_equity, 2),
        "total_contributions": round(contrib, 2),
        "profit_multiple_on_contrib": round(final_equity / contrib, 4),
        "max_dd_pct": round(max_dd, 2),
        "worst_day_pct": worst_day_pct,
        "days_at_or_below_-3%": int(breach_days),
        "daily_stop_days": len(set(stop_days)),
        "breaker_events": len(breaker_hits),
        "breaker_first": breaker_hits[0]["time"] if breaker_hits else None,
    }
    return metrics, eq, (monthly if monthly is not None else pd.DataFrame())


def buyhold_btc() -> dict:
    """الاحتفاظ ببيتكوين بنفس خطة التمويل: كل إيداع يُشترى به بيتكوين في أول يوم تداول من الشهر."""
    sys.path.insert(0, "/home/user/.work/root/history/hyp_lab")
    import run_breakers as RB  # noqa: E402
    df, sha, _ = RB.stream_symbol("BTCUSDT", "600a1b6")
    df = df[(df.index >= START) & (df.index <= END)]
    dep_days = [d for d in deposits_between(START, END)]
    units = 0.0
    spent = 0.0
    for d in dep_days:
        s = df[df.index >= d]
        if len(s) == 0:
            continue
        px = float(s["open"].iloc[0]) * (1 + 0.0013)
        units += MONTHLY / px
        spent += MONTHLY
    final_px = float(df["close"].iloc[-1]) * (1 - 0.0013)
    value = units * final_px
    contrib = CAPITAL_START + spent
    return {"benchmark": "BUYHOLD_BTC", "contributions": round(contrib, 2),
            "final_value": round(value, 2), "multiple": round(value / contrib, 4),
            "note": "500$ الافتتاحية استُثمرت مع أول دفعة (تعادل الإيداع الأول)"}


def main() -> int:
    trades = load_trades()
    print(f"الصفقات المحمّلة: {len(trades)} · {trades.symbol.nunique()} عملة · "
          f"{trades.entry_time.min()} → {trades.exit_time.max()}", flush=True)
    cases = [
        (0.05, 1000.0, "القاعدة 5% بسقف حجم 1000$ (حجم ما قُيّست عليه السجلات)"),
        (0.05, 3000.0, "القاعدة 5% بسقف حجم 3000$"),
        (0.05, None, "القاعدة 5% بلا سقف (تركيب ورقي — للعلم فقط)"),
        (0.15, 3000.0, "النضج 15% بسقف حجم 3000$"),
    ]
    rows, eqs, months = [], {}, {}
    for frac, cap, label in cases:
        m, eq, mo = run_case(trades, frac, cap=cap, label=label)
        rows.append(m)
        eqs[label] = eq
        months[label] = mo
        print(f"[{label}] أُخذت {m['trades_taken']} · فاتت {m['trades_skipped_no_cash']} "
              f"({m['skip_rate']}) · رأس المال النهائي {m['final_equity']}$ من مساهمات "
              f"{m['total_contributions']}$ ({m['profit_multiple_on_contrib']}×) · "
              f"أقصى هبوط %{m['max_dd_pct']} · أسوأ يوم %{m['worst_day_pct']} · "
              f"أيام الوقف اليومي {m['daily_stop_days']} · القاطع {m['breaker_events']}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "sizing_cases_4h_13.csv", index=False, encoding="utf-8-sig")
    for label, eq in eqs.items():
        if not eq.empty:
            eq.to_csv(OUT / f"equity_{label.split(':')[0].strip().replace('%','pct').replace(' ','_')}.csv",
                      index=False, encoding="utf-8-sig")
    for label, mo in months.items():
        if not mo.empty:
            mo.to_csv(OUT / f"monthly_{label.split(':')[0].strip().replace('%','pct').replace(' ','_')}.csv",
                      index=False, encoding="utf-8-sig")
    bh = buyhold_btc()
    pd.DataFrame([bh]).to_csv(OUT / "buyhold_real_capital.csv", index=False, encoding="utf-8-sig")
    print(f"\n[احتفاظ بيتكوين بنفس الخطة] مساهمات {bh['contributions']}$ ⇒ قيمة {bh['final_value']}$ "
          f"({bh['multiple']}×)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
