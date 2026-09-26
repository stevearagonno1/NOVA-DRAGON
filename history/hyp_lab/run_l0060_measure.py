# -*- coding: utf-8 -*-
"""قياس L0060 بعد اجتياز المرحلة 0 والمسبار. القاعدة في acceptance_rule_l0060.json."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import zlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/l0060")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")

import common as CM
import nova_v8.config as C
import nova_v8.indicators as ind
import nova_v8.long_cycle as LC
from nova_v8.execution import market_cost_pct, market_fill, net_fraction, settle_directional, Position

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0060"
FRAMES = pathlib.Path.home() / ".cache" / "l0060_h4"
FRAMES.mkdir(parents=True, exist_ok=True)
DEC_S, DEC_E = "2021-09-01", "2024-01-01"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
ALLOWED = ("BTCUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT")
COST = 0.00115
COST_130 = 0.00130
CAP = 24
LEDGER: list[dict] = []


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def log(name: str, window: str, phase: str) -> None:
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف {CAP}")
    LEDGER.append({"#": len(LEDGER) + 1, "المرحلة": phase, "القياس": name, "الفترة": window})
    print(f"  [{len(LEDGER)}/{CAP}] {phase} {name}", flush=True)


def set_cost(cost: float) -> None:
    C.COMMISSION_PCT = float(cost)
    C.SLIPPAGE_PCT = 0.0


def pnl_of(entry_px: float, exit_px: float, notional: float) -> float:
    if entry_px <= 0:
        return 0.0
    return float(net_fraction(entry_px, exit_px, 1, 0.0) * notional)


def run_gated(df1m: pd.DataFrame, symbol: str, entry_ok=None) -> list[dict]:
    """نسخة المختبر من run(). البوابة فقط عند الشراء. تُستخدم بعد إثبات التطابق."""
    if symbol not in {"BTCUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"}:
        return []
    h4 = df1m.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    daily = df1m.resample("1D", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    if len(h4) < 200 or len(daily) < max(40, C.LONG_CYCLE_DAILY_LOOKBACK // 2):
        return []
    prior_low = daily["low"].shift(1).rolling(
        C.LONG_CYCLE_DAILY_LOOKBACK, min_periods=max(30, C.LONG_CYCLE_DAILY_LOOKBACK // 3)
    ).min()
    prior_high = daily["high"].shift(1).rolling(
        C.LONG_CYCLE_DAILY_LOOKBACK, min_periods=max(30, C.LONG_CYCLE_DAILY_LOOKBACK // 3)
    ).max()
    known = pd.DataFrame({"prior_low": prior_low, "prior_high": prior_high},
                         index=daily.index + pd.Timedelta(days=1))
    dctx = known.reindex(h4.index, method="ffill")
    atr = ind.wilder_atr(h4, C.ATR_LEN)
    atr_pct = (atr / h4["close"].replace(0.0, np.nan)).to_numpy(float)
    ema20 = ind.ema(h4["close"], 20)
    prior6_high = h4["high"].shift(1).rolling(C.LONG_CYCLE_CONFIRM_BARS_4H).max()
    prior3_low = h4["low"].shift(1).rolling(3).min()
    close = h4["close"]
    low = h4["low"]
    mss = close > prior6_high
    _v2 = os.getenv("NOVA_LC_V2", "1") == "1"
    _zbuf = 0.08 if _v2 else C.LONG_CYCLE_ZONE_BUFFER_PCT
    zone = close <= dctx["prior_low"] * (1.0 + _zbuf)
    zone_seen = zone.shift(1).rolling(C.LONG_CYCLE_CONFIRM_BARS_4H, min_periods=1).max().astype(bool)
    stabilised = (close > close.shift(1)) & (low >= low.shift(1))
    entry_signal = (zone_seen & mss & (close > ema20)) if _v2 else (
        zone_seen & stabilised & mss & (close > ema20))
    if C.SMC_GATE_ENABLED:
        from nova_v8 import smc
        _h = h4["high"].to_numpy(float)
        _l = h4["low"].to_numpy(float)
        _c = h4["close"].to_numpy(float)
        smc_arr = np.array([smc.smc_confirm(_h, _l, _c, i, 1, C.SMC_GATE_LOOKBACK) for i in range(len(h4))])
        entry_signal = entry_signal & smc_arr
    top_zone = close >= dctx["prior_high"] * (1.0 - C.LONG_CYCLE_ZONE_BUFFER_PCT)
    weakness = ((close < prior3_low) | (close < ema20)).fillna(False).astype(bool)
    weakness_event = weakness & ~weakness.shift(1, fill_value=False)
    idx = h4.index
    n = len(h4)
    weights = C.LONG_CYCLE_STAGE_WEIGHTS
    tranches: list[dict] = []
    pending: dict[int, list[tuple]] = {}
    records: list[dict] = []
    series = 0
    top_seen = False
    next_stage = 0

    def cost_at(i: int) -> float:
        ref = i - 1 if i > 0 else i
        v = atr_pct[ref] if 0 <= ref < n and np.isfinite(atr_pct[ref]) else None
        return market_cost_pct(v, C.REGIME_BULL)

    def schedule_buy(stage: int, decision_i: int):
        if stage >= len(weights) or any(a[0] == "buy" for vals in pending.values() for a in vals):
            return
        pending.setdefault(decision_i + 1, []).append(("buy", stage, decision_i))

    def close_tranches(exit_i: int, reason: str, px: float):
        nonlocal tranches, top_seen, next_stage
        for tr in list(tranches):
            pos = Position(symbol=symbol, side=1, entry=tr["entry_px"], entry_px=tr["entry_px"],
                           atr_pct=0.02, trigger="CycleBottom", regime=C.REGIME_BULL,
                           notional=tr["notional"], entry_bar=tr["entry_i"],
                           entry_ref_px=tr["entry_ref"], entry_cost_pct=tr["entry_cost"], series=series)
            slip = cost_at(exit_i)
            net = settle_directional(pos, px, slip_pct=slip)
            records.append({
                "symbol": symbol, "stage": int(tr["stage"]), "series": int(series),
                "entry_bar": int(tr["entry_i"]), "exit_bar": int(exit_i),
                "entry_time": pd.Timestamp(idx[tr["entry_i"]]).isoformat(),
                "exit_time": pd.Timestamp(idx[exit_i]).isoformat(),
                "bars_held": int(exit_i - tr["entry_i"]),
                "pnl_usd": net * tr["notional"], "notional_usd": tr["notional"],
                "reason": reason, "entry_px": tr["entry_px"], "entry_ref_px": tr["entry_ref"],
                "exit_px": px,
            })
        tranches = []
        top_seen = False
        next_stage = 0

    def allowed(i: int) -> bool:
        return entry_ok is None or bool(entry_ok(idx[i]))

    for i in range(1, n):
        o, h, l, c = (float(h4.iloc[i][x]) for x in ("open", "high", "low", "close"))
        for action, stage, decision_i in pending.pop(i, []):
            if action != "buy" or len(tranches) >= len(weights):
                continue
            if not np.isfinite(o) or o <= 0:
                continue
            ecost = cost_at(i)
            epx = market_fill(o, 1, ecost)
            notional = C.LONG_CYCLE_CAPITAL_USD * float(weights[stage])
            tranches.append({"stage": stage, "entry_i": i, "entry_ref": o, "entry_px": epx,
                             "entry_cost": ecost, "notional": notional, "peak": epx})
            next_stage = max(next_stage, stage + 1)
        if not tranches:
            if bool(entry_signal.iloc[i]) and allowed(i):
                schedule_buy(0, i)
            continue
        broad_low = dctx["prior_low"].iloc[i]
        invalid_level = min(
            min(t["entry_px"] for t in tranches) * (1.0 - C.LONG_CYCLE_HARD_INVALIDATION_PCT),
            float(broad_low) * (1.0 - 0.02) if np.isfinite(broad_low) else float("-inf"),
        )
        if np.isfinite(l) and l <= invalid_level:
            fill = o if o < invalid_level else invalid_level
            close_tranches(i, "إلغاء-دورة", fill)
            continue
        for tr in tranches:
            tr["peak"] = max(tr["peak"], h)
        if bool(top_zone.iloc[i]):
            top_seen = True
        if top_seen and bool(weakness_event.iloc[i]) and tranches:
            tr = tranches.pop()
            pos = Position(symbol=symbol, side=1, entry=tr["entry_px"], entry_px=tr["entry_px"],
                           atr_pct=0.02, trigger="CycleBottom", regime=C.REGIME_BULL,
                           notional=tr["notional"], entry_bar=tr["entry_i"],
                           entry_ref_px=tr["entry_ref"], entry_cost_pct=tr["entry_cost"], series=series)
            net = settle_directional(pos, c, slip_pct=cost_at(i))
            records.append({
                "symbol": symbol, "stage": int(tr["stage"]), "series": int(series),
                "entry_bar": int(tr["entry_i"]), "exit_bar": int(i),
                "entry_time": pd.Timestamp(idx[tr["entry_i"]]).isoformat(),
                "exit_time": pd.Timestamp(idx[i]).isoformat(),
                "bars_held": int(i - tr["entry_i"]),
                "pnl_usd": net * tr["notional"], "notional_usd": tr["notional"],
                "reason": "توزيع-قمة", "entry_px": tr["entry_px"], "entry_ref_px": tr["entry_ref"],
                "exit_px": c,
            })
            if not tranches:
                top_seen = False
                next_stage = 0
            continue
        if (not top_seen and next_stage < len(weights) and bool(entry_signal.iloc[i])
                and c <= min(t["entry_px"] for t in tranches) * (1.0 - C.LONG_CYCLE_STAGE_GAP_PCT)
                and allowed(i)):
            schedule_buy(next_stage, i)
    if tranches:
        final_i = n - 1
        close_tranches(final_i, "نهاية-العينة", float(h4["close"].iloc[final_i]))
    return records


def from_engine(recs: list[dict]) -> list[dict]:
    out = []
    for r in recs:
        out.append({
            "symbol": r["symbol"],
            "stage": int(json.loads(r["snapshot"])["stage"]),
            "series": int(r["series"]),
            "entry_bar": int(r["entry_bar"]),
            "exit_bar": int(r["exit_bar"]),
            "entry_time": r["entry_time"],
            "exit_time": r["exit_time"],
            "bars_held": int(r["bars_held"]),
            "pnl_usd": float(r["pnl_usd"]),
            "notional_usd": float(r["notional_usd"]),
            "reason": r["reason"],
            "entry_px": float(r["entry_px"]),
            "entry_ref_px": float(r["entry_ref_px"]),
            "exit_px": float(r["exit_px"]),
        })
    return out


def key_of(rows: list[dict]) -> list[tuple]:
    return sorted((r["symbol"], r["entry_time"], r["exit_time"], r["reason"],
                   round(r["entry_ref_px"], 6), round(r["exit_px"], 6),
                   round(r["pnl_usd"], 6), round(r["notional_usd"], 4)) for r in rows)


def in_window(rows: list[dict], start: str, end: str) -> tuple[list[dict], list[dict]]:
    s = pd.Timestamp(start, tz="UTC")
    e = pd.Timestamp(end, tz="UTC")
    keep, warm = [], []
    for r in rows:
        ts = pd.Timestamp(r["entry_time"])
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        if ts < s:
            warm.append(r)
        elif ts < e:
            keep.append(r)
    return keep, warm


def cycles(rows: list[dict]) -> list[list[dict]]:
    out = []
    for sym, g in pd.DataFrame(rows).groupby("symbol") if rows else []:
        g = g.sort_values(["entry_bar", "stage"])
        cur: list[dict] = []
        for rec in g.to_dict("records"):
            if int(rec["stage"]) == 0 and cur:
                out.append(cur)
                cur = []
            cur.append(rec)
        if cur:
            out.append(cur)
    return out


def peak_capital(rows: list[dict]) -> float:
    events = []
    for i, r in enumerate(rows):
        en = pd.Timestamp(r["entry_time"])
        ex = pd.Timestamp(r["exit_time"])
        events.append((en, 1, float(r["notional_usd"]), i))
        events.append((ex, -1, float(r["notional_usd"]), i))
    events.sort(key=lambda x: (x[0], x[1]))
    open_n = 0.0
    peak = 0.0
    for _, sign, notional, _ in events:
        open_n += sign * notional
        peak = max(peak, open_n)
    return round(peak, 2)


def drawdown(rows: list[dict], frames: dict[str, pd.DataFrame]) -> dict:
    if not rows:
        return {"dd_usd": 0.0, "dd_pct_of_peak": None}
    events = []
    for r in rows:
        events.append((pd.Timestamp(r["exit_time"]), r))
    # علامة على كل إغلاق شمعة 4س أثناء وجود شريحة مفتوحة
    times = set()
    for r in rows:
        fr = frames[r["symbol"]]
        en, ex = pd.Timestamp(r["entry_time"]), pd.Timestamp(r["exit_time"])
        sl = fr[(fr.index >= en) & (fr.index <= ex)]
        times.update(sl.index)
    times = sorted(times)
    realized = 0.0
    closed = set()
    peak = 0.0
    worst = 0.0
    by_exit: dict[pd.Timestamp, list[dict]] = {}
    for r in rows:
        by_exit.setdefault(pd.Timestamp(r["exit_time"]), []).append(r)
    open_rows = list(rows)
    for ts in times:
        for r in by_exit.get(ts, []):
            if id(r) not in closed:
                realized += float(r["pnl_usd"])
                closed.add(id(r))
        mtm = realized
        for r in open_rows:
            en, ex = pd.Timestamp(r["entry_time"]), pd.Timestamp(r["exit_time"])
            if en <= ts < ex and id(r) not in closed:
                fr = frames[r["symbol"]]
                if ts not in fr.index:
                    continue
                px = float(fr.loc[ts, "close"])
                mtm += pnl_of(float(r["entry_px"]), px, float(r["notional_usd"]))
        peak = max(peak, mtm)
        worst = min(worst, mtm - peak)
    return {"dd_usd": round(worst, 2), "peak_equity": round(peak, 2)}


def summarize(rows: list[dict], warm: list[dict], frames: dict[str, pd.DataFrame]) -> dict:
    net = round(sum(float(r["pnl_usd"]) for r in rows), 2)
    cyc = cycles(rows)
    holds = [int(r["bars_held"]) for r in rows]
    peak = peak_capital(rows)
    dd = drawdown(rows, frames)
    reasons = {}
    for r in rows:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    gaps = touches = 0
    for r in rows:
        if r["reason"] != "إلغاء-دورة":
            continue
        bar = frames[r["symbol"]].loc[pd.Timestamp(r["exit_time"])]
        if float(r["exit_px"]) == float(bar["open"]) or abs(float(r["exit_px"]) - float(bar["open"])) < 1e-6:
            gaps += 1
        else:
            touches += 1
    gross = 0.0
    for r in rows:
        qty = float(r["notional_usd"]) / float(r["entry_ref_px"])
        gross += qty * (float(r["exit_px"]) - float(r["entry_ref_px"]))
    n = len(rows)
    return {
        "net": net,
        "slices": n,
        "cycles": len(cyc),
        "slices_per_cycle": round(n / len(cyc), 3) if cyc else None,
        "mean_hold_bars": round(float(np.mean(holds)), 2) if holds else None,
        "mean_hold_days": round(float(np.mean(holds)) * 4 / 24, 2) if holds else None,
        "peak_concurrent": peak,
        "deployed_programmed": 4000.0,
        "return_pct_on_peak": None if peak <= 0 else round(100.0 * net / peak, 3),
        "return_pct_on_4000": round(100.0 * net / 4000.0, 3),
        "dd_usd": dd["dd_usd"],
        "dd_pct_of_peak": None if peak <= 0 else round(100.0 * dd["dd_usd"] / peak, 3),
        "warmup_excluded": len(warm),
        "reasons": reasons,
        "invalidation_gaps": gaps,
        "invalidation_touches": touches,
        "move": None if n == 0 else round(gross / n, 5),
        "per_slice": None if n == 0 else round(net / n, 5),
    }


def save_trades(name: str, rows: list[dict]) -> pathlib.Path:
    frame = pd.DataFrame(rows)
    cols = ["symbol", "entry_time", "exit_time", "entry", "exit", "notional", "pnl",
            "reason", "stage", "bars_held"]
    if frame.empty:
        frame = pd.DataFrame(columns=cols)
    else:
        frame = pd.DataFrame({
            "symbol": frame["symbol"],
            "entry_time": frame["entry_time"],
            "exit_time": frame["exit_time"],
            "entry": frame["entry_ref_px"],
            "exit": frame["exit_px"],
            "notional": frame["notional_usd"],
            "pnl": frame["pnl_usd"].map(lambda x: round(float(x), 4)),
            "reason": frame["reason"],
            "stage": frame["stage"],
            "bars_held": frame["bars_held"],
        })
    path = OUT / f"trades_{name}.csv"
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def guard(name: str) -> None:
    path = OUT / f"trades_{name}.csv"
    st = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
         "--trades", str(path), "--frames", str(FRAMES), "--cost", "0", "--bar-tag", "4h"],
        capture_output=True, text=True,
    )
    if st.returncode != 0 or "مخالفات الدخول=0" not in st.stdout or "تُخطّي=0" not in st.stdout:
        raise SystemExit(f"حارس التعبئة فشل على {name}:\n{st.stdout}\n{st.stderr}")
    if "مخالفات الخروج=0" not in st.stdout:
        raise SystemExit(f"مخالفة خروج في {name}")


def save_frames(sym: str, df: pd.DataFrame) -> pd.DataFrame:
    h4 = df.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    official = CM.to_bars(df, 240)
    both = h4.index.intersection(official.index)
    if len(h4) != len(official) or len(both) != len(h4):
        raise SystemExit(f"اصطفاف 4h خالف to_bars في {sym}")
    for col in ("open", "high", "low", "close"):
        if (h4[col] - official[col]).abs().gt(1e-8).any():
            raise SystemExit(f"شموع 4h خالفت to_bars في {sym}")
    broken = ((h4["open"] < h4["low"]) | (h4["open"] > h4["high"])
              | (h4["close"] < h4["low"]) | (h4["close"] > h4["high"])).any()
    if broken:
        raise SystemExit(f"OHLC مكسور في {sym}")
    h4.to_parquet(FRAMES / f"{sym}_4h.parquet")
    return h4


def regime_falling(sym: str, h4: pd.DataFrame, daily: pd.DataFrame) -> pd.Series:
    c = daily["close"]
    e50 = c.ewm(span=50, adjust=False).mean()
    e200 = c.ewm(span=200, adjust=False).mean()
    slope = e50.diff(10)
    lab = pd.Series("عرضي", index=daily.index)
    lab[(e50 > e200) & (slope > 0)] = "صاعد"
    lab[(e50 < e200) & (slope < 0)] = "هابط"
    lab = lab.shift(1)
    lookup = {ts.normalize(): val for ts, val in lab.items()}
    return pd.Series([lookup.get(ts.normalize(), np.nan) for ts in h4.index], index=h4.index, dtype=object)


def reprice(rows: list[dict], cost: float) -> list[dict]:
    set_cost(cost)
    out = []
    for r in rows:
        if abs(float(r["entry_px"]) - float(r["entry_ref_px"])) > 1e-8:
            raise SystemExit("سعر الدخول اختلف عن الافتتاح. إعادة التسعير ليست قياسًا.")
        q = dict(r)
        q["pnl_usd"] = pnl_of(float(r["entry_px"]), float(r["exit_px"]), float(r["notional_usd"]))
        out.append(q)
    return out


def emit(name: str, window: str, phase: str, rows: list[dict], warm: list[dict],
         frames: dict[str, pd.DataFrame], counted: bool, cost: float = COST) -> dict:
    set_cost(cost)
    for r in rows:
        ts = pd.Timestamp(r["exit_time"])
        bar = frames[r["symbol"]].loc[ts]
        px = float(r["exit_px"])
        en = frames[r["symbol"]].loc[pd.Timestamp(r["entry_time"])]
        ep = float(r["entry_ref_px"])
        if ep < float(en["low"]) - 1e-6 or ep > float(en["high"]) + 1e-6:
            raise SystemExit(f"دخول خارج الشمعة في {name}")
        if px < float(bar["low"]) - 1e-6 or px > float(bar["high"]) + 1e-6:
            raise SystemExit(f"خروج خارج الشمعة في {name}: {px} [{bar['low']}, {bar['high']}]")
    st = summarize(rows, warm, frames)
    save_trades(name, rows)
    guard(name)
    if counted:
        log(name, window, phase)
    print(f"    {name}: صافي={st['net']} دورات={st['cycles']} شرائح={st['slices']} "
          f"ذروة={st['peak_concurrent']} عائد%={st['return_pct_on_peak']} هبوط={st['dd_usd']}", flush=True)
    return st


def buyhold(frames: dict[str, pd.DataFrame], capital: float, start: str, end: str) -> tuple[list[dict], dict]:
    s, e = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    usable = []
    for sym, fr in frames.items():
        w = fr[(fr.index >= s) & (fr.index < e)]
        if len(w) >= 2:
            usable.append((sym, w))
    if not usable or capital <= 0:
        return [], {"net": 0.0, "capital": capital, "symbols": 0, "return_pct": None}
    each = capital / len(usable)
    set_cost(COST)
    rows = []
    for sym, w in usable:
        entry = float(w["open"].iloc[0])
        exit_ = float(w["close"].iloc[-1])
        rows.append({
            "symbol": sym,
            "entry_time": w.index[0].isoformat(),
            "exit_time": w.index[-1].isoformat(),
            "entry_ref_px": entry, "entry_px": entry, "exit_px": exit_,
            "notional_usd": each, "pnl_usd": pnl_of(entry, exit_, each),
            "reason": "احتفاظ", "stage": 0, "bars_held": len(w) - 1, "entry_bar": 0,
        })
    net = round(sum(r["pnl_usd"] for r in rows), 2)
    return rows, {"net": net, "capital": round(capital, 2), "symbols": len(usable),
                  "return_pct": round(100.0 * net / capital, 3)}


def random_book(frames: dict[str, pd.DataFrame], template: list[dict], seed: int,
                start: str, end: str) -> list[dict]:
    s, e = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    rows = []
    cyc = cycles(template)
    by = {}
    for group in cyc:
        by.setdefault(group[0]["symbol"], []).append(group)
    set_cost(COST)
    for sym, fr in frames.items():
        groups = by.get(sym, [])
        n = len(groups)
        if n == 0:
            continue
        hold = int(np.median([max(int(r["bars_held"]) for r in g) for g in groups]))
        hold = max(hold, 1)
        notional = float(np.mean([sum(float(r["notional_usd"]) for r in g) for g in groups]))
        w = fr[(fr.index >= s) & (fr.index < e)]
        if len(w) <= hold + 2:
            continue
        rng = np.random.default_rng(np.random.SeedSequence([int(seed), zlib.crc32(sym.encode()) & 0xFFFFFFFF]))
        starts = list(range(0, len(w) - hold - 1))
        rng.shuffle(starts)
        chosen = []
        for i in starts:
            if all(i >= c + hold or i + hold <= c for c in chosen):
                chosen.append(i)
            if len(chosen) == n:
                break
        for i in chosen:
            entry = float(w["open"].iloc[i + 1])
            exit_ = float(w["close"].iloc[i + 1 + hold])
            rows.append({
                "symbol": sym,
                "entry_time": w.index[i + 1].isoformat(),
                "exit_time": w.index[i + 1 + hold].isoformat(),
                "entry_ref_px": entry, "entry_px": entry, "exit_px": exit_,
                "notional_usd": notional, "pnl_usd": pnl_of(entry, exit_, notional),
                "reason": "عشوائي", "stage": 0, "bars_held": hold, "entry_bar": i + 1,
            })
    return rows


def main() -> int:
    set_cost(COST)
    probe = CM.load(str(ROOT / "crypto_archive" / "BTCUSDT_1m.parquet"), start="2022-01-01", end="2022-07-01")
    a = key_of(from_engine(LC.run(probe, "BTCUSDT")))
    b = key_of(run_gated(probe, "BTCUSDT", None))
    if a != b:
        dump("identity.json", {"ok": False, "engine": len(a), "copy": len(b)})
        print("نسخة البوابة لم تطابق الاستيراد. الهابط لن يُقاس.", flush=True)
        gated_ok = False
    else:
        dump("identity.json", {"ok": True, "trades": len(a)})
        print(f"  نسخة البوابة طابقت الاستيراد على مسبار BTC ({len(a)} صفقة)", flush=True)
        gated_ok = True
    del probe

    data = {}
    frames = {}
    daily = {}
    falling = {}
    for sym in ALLOWED:
        print(f"  تحميل {sym}", flush=True)
        df = CM.load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), start=WARM, end=JUD_E)
        data[sym] = df
        frames[sym] = save_frames(sym, df)
        daily[sym] = CM.to_bars(df, 1440)
        lab = regime_falling(sym, frames[sym], daily[sym])
        falling[sym] = lab

    def run_all(kind: str, start_load_end: str, win_s: str, win_e: str) -> tuple[list[dict], list[dict]]:
        rows, warm = [], []
        end = pd.Timestamp(start_load_end, tz="UTC")
        for sym, df in data.items():
            sl = df[df.index < end]
            if kind == "open":
                recs = from_engine(LC.run(sl, sym))
            else:
                lab = falling[sym]
                lookup = {ts.normalize(): val for ts, val in lab.items()}

                def ok(ts, lookup=lookup):
                    return lookup.get(pd.Timestamp(ts).tz_convert("UTC").normalize(), np.nan) == "هابط"
                recs = run_gated(sl, sym, ok)
            keep, w = in_window(recs, win_s, win_e)
            rows.extend(keep)
            warm.extend(w)
        return rows, warm

    print("══ مرحلة ب ══", flush=True)
    sel, sel_w = run_all("open", "2024-01-01", DEC_S, DEC_E)
    jud, jud_w = run_all("open", "2026-08-31", JUD_S, JUD_E)
    st_sel = emit("b_open_c00115_SEL", "اختيار", "ب", sel, sel_w, frames, True)
    st_jud = emit("b_open_c00115_JUD", "حكم", "ب", jud, jud_w, frames, True)
    sel130 = reprice(sel, COST_130)
    jud130 = reprice(jud, COST_130)
    st_sel130 = emit("b_open_c00130_SEL", "اختيار", "ب", sel130, sel_w, frames, True, COST_130)
    st_jud130 = emit("b_open_c00130_JUD", "حكم", "ب", jud130, jud_w, frames, True, COST_130)
    table = {"open": {"c00115": {"اختيار": st_sel, "حكم": st_jud},
                      "c00130": {"اختيار": st_sel130, "حكم": st_jud130}}}

    print("══ مرحلة ج: الهابط ══", flush=True)
    if not gated_ok:
        table["falling"] = "لم يُقَس. نسخة البوابة لم تطابق."
        better = "open"
    else:
        fsel, fsel_w = run_all("falling", "2024-01-01", DEC_S, DEC_E)
        fjud, fjud_w = run_all("falling", "2026-08-31", JUD_S, JUD_E)
        st_fsel = emit("c_fall_c00115_SEL", "اختيار", "ج", fsel, fsel_w, frames, True)
        st_fjud = emit("c_fall_c00115_JUD", "حكم", "ج", fjud, fjud_w, frames, True)
        table["falling"] = {"c00115": {"اختيار": st_fsel, "حكم": st_fjud}, "c00130": "لم يُقَس"}
        rj = st_jud["return_pct_on_peak"]
        fj = st_fjud["return_pct_on_peak"]
        rj = -1e18 if rj is None else rj
        fj = -1e18 if fj is None else fj
        better = "falling" if fj > rj else "open"
    table["better"] = better
    print(f"  الأفضل قبل الضوابط: {better}", flush=True)

    chosen_sel = sel if better == "open" else fsel
    chosen_jud = jud if better == "open" else fjud
    peak_sel = peak_capital(chosen_sel)
    peak_jud = peak_capital(chosen_jud)

    print("══ احتفاظ بنفس الذروة ══", flush=True)
    bh_s_rows, bh_s = buyhold(frames, peak_sel, DEC_S, "2024-01-01")
    bh_j_rows, bh_j = buyhold(frames, peak_jud, JUD_S, JUD_E)
    emit("c_hold_SEL", "اختيار", "ج", bh_s_rows, [], frames, True)
    emit("c_hold_JUD", "حكم", "ج", bh_j_rows, [], frames, True)
    table["buyhold_fair"] = {"اختيار": bh_s, "حكم": bh_j}

    print("══ عشوائي ══", flush=True)
    seeds_run = (110060, 210060, 310060, 410060)
    random_stats = []
    for seed, phase in ((110060, "ج"), (210060, "ج"), (310060, "د"), (410060, "د")):
        for label, start, end, template in (
            ("SEL", DEC_S, "2024-01-01", chosen_sel),
            ("JUD", JUD_S, JUD_E, chosen_jud),
        ):
            rows = random_book(frames, template, seed, start, end)
            st = emit(f"r_{seed}_{label}", "اختيار" if label == "SEL" else "حكم", phase, rows, [], frames, True)
            random_stats.append({"seed": seed, "window": label, **st})
    table["random"] = random_stats
    table["random_unmeasured"] = [510060]
    dump("results.json", table)
    dump("ledger.json", LEDGER)

    print("══ حتمية ══", flush=True)
    h1 = hashlib.sha256((OUT / "trades_b_open_c00115_SEL.csv").read_bytes()).hexdigest()
    h2 = hashlib.sha256((OUT / "trades_b_open_c00115_JUD.csv").read_bytes()).hexdigest()
    sel2, _ = run_all("open", "2024-01-01", DEC_S, DEC_E)
    jud2, _ = run_all("open", "2026-08-31", JUD_S, JUD_E)
    save_trades("b_open_c00115_SEL", sel2)
    save_trades("b_open_c00115_JUD", jud2)
    if hashlib.sha256((OUT / "trades_b_open_c00115_SEL.csv").read_bytes()).hexdigest() != h1:
        raise SystemExit("حتمية الاختيار فشلت")
    if hashlib.sha256((OUT / "trades_b_open_c00115_JUD.csv").read_bytes()).hexdigest() != h2:
        raise SystemExit("حتمية الحكم فشلت")
    print("  sha256 طابق", flush=True)
    dump("env_dump.txt", {
        "cap": CAP, "counted": len(LEDGER),
        "cost": "COMMISSION=0.00115 or 0.00130, SLIPPAGE=0, in memory",
        "v2": os.getenv("NOVA_LC_V2", "1"),
        "smc": str(C.SMC_GATE_ENABLED),
        "universe": list(ALLOWED),
        "paper_17_not_run": "الكود يرفضها. nova_v8 لم يُعدَّل.",
        "capital_programmed": 1000,
        "weights": list(C.LONG_CYCLE_STAGE_WEIGHTS),
        "better": better,
        "seed_unmeasured": 510060,
        "falling_0130": "لم يُقَس",
        "identity": gated_ok,
        "determinism": "sha256 match on open 0.115 both periods",
        "regime_py": False,
    })
    print(f"اكتمل. المستهلك {len(LEDGER)}/{CAP}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
