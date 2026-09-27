# -*- coding: utf-8 -*-
"""L0061 — القياس من سجلّات run_l0061_lc.py (pass1) + الحتمية من pass2.

القاعدة في acceptance_rule_l0061.json (كُتبت قبل أي رقم). السقف 26. لا يُتجاوز.
  مرحلة 0 (لا تُحسب): إعادة إنتاج L0060 على الأربع ± 0.5$، وهوية النسخة/التسمية، وحارس التعبئة.
  أ  (4): open16 0.115 · open16 0.130 · hold16 · bear16 0.115 — الفترتان.
  ب (10): الدورة الكاملة: open/0.115 · open/0.130 · hold · bear/0.115 · bear/0.130 × {4 عملات، 16 عملة}.
  ج  (5): تشريح الإلغاء مقابل التوزيع على سجلّ open4·حكم (وسياق الدورة الكاملة). لا تغيير لشرط الإلغاء.
  د  (5): عشوائي 5 بذور على أفضل مسار (أعلى عائد % على الذروة في الحكم) في الفترتين.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import zlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")

import run_l0061_lc as L  # noqa: E402
import nova_v8.config as C  # noqa: E402

OUT = L.OUT
FRAMES, DAILY, RECS = L.FRAMES, L.DAILY, L.RECS
DEC_S, CUT, JUD_S, JUD_E = L.DEC_S, L.CUT, L.JUD_S, L.JUD_E
COST, COST_130 = L.COST, L.COST_130
ALLOWED = L.ALLOWED
UNIVERSE = L.UNIVERSE
CAP = 26
SEEDS = (110060, 210060, 310060, 410060, 510060)
LEDGER: list[dict] = []
WIN = {"SEL": (DEC_S, CUT), "JUD": (JUD_S, JUD_E), "FULL": (DEC_S, JUD_E)}
WIN_AR = {"SEL": "اختيار", "JUD": "حكم", "FULL": "الدورة الكاملة"}


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def log(name: str, window: str, phase: str) -> None:
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف {CAP}")
    LEDGER.append({"#": len(LEDGER) + 1, "المرحلة": phase, "القياس": name, "الفترة": window})
    print(f"  [{len(LEDGER)}/{CAP}] {phase} {name}", flush=True)


def ts(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


# ───────────────────────────── تحميل ─────────────────────────────
R: dict[str, dict] = {}
R2: dict[str, dict] = {}
FR: dict[str, pd.DataFrame] = {}
REG: dict[str, pd.Series] = {}
for sym in L.ALL_FILES:
    R[sym] = json.loads((RECS / f"pass1_{sym}.json").read_text(encoding="utf-8"))
    p2 = RECS / f"pass2_{sym}.json"
    if p2.exists():
        R2[sym] = json.loads(p2.read_text(encoding="utf-8"))
    FR[sym] = pd.read_parquet(FRAMES / f"{sym}_4h.parquet")
    REG[sym] = pd.read_parquet(DAILY / f"{sym}_regime.parquet")["regime"]


def rows_for(recs_by_sym: dict, path: str, coins, window: str) -> tuple[list[dict], list[dict]]:
    s, e = (ts(WIN[window][0]), ts(WIN[window][1]))
    key = ("open_cut" if path == "open" else "bear_cut") if window == "SEL" else ("open_full" if path == "open" else "bear_full")
    keep, warm = [], []
    for sym in coins:
        for r in recs_by_sym[sym][key]:
            t = ts(r["entry_time"])
            q = dict(r)
            if t < s:
                warm.append(q)
            elif t < e:
                keep.append(q)
    return keep, warm


def cycles(rows: list[dict]) -> list[list[dict]]:
    out = []
    if not rows:
        return out
    for sym, g in pd.DataFrame(rows).groupby("symbol"):
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
    for r in rows:
        events.append((ts(r["entry_time"]), 1, float(r["notional_usd"])))
        events.append((ts(r["exit_time"]), -1, float(r["notional_usd"])))
    events.sort(key=lambda x: (x[0], x[1]))
    open_n = peak = 0.0
    for _, sign, notional in events:
        open_n += sign * notional
        peak = max(peak, open_n)
    return round(peak, 2)


def exposure(rows: list[dict], window: str, coins) -> dict:
    """رأس المال المنشور مرجَّحًا بالزمن ونسبة الشموع التي فيها شريحة مفتوحة (على شبكة 4h موحّدة)."""
    s, e = ts(WIN[window][0]), ts(WIN[window][1])
    grid = pd.date_range(s, e, freq="4h", tz="UTC", inclusive="left")
    dep = np.zeros(len(grid))
    for r in rows:
        a = np.searchsorted(grid.values, np.datetime64(ts(r["entry_time"]).tz_convert(None)))
        b = np.searchsorted(grid.values, np.datetime64(ts(r["exit_time"]).tz_convert(None)))
        dep[a:b] += float(r["notional_usd"])
    return {"avg_deployed_usd": round(float(dep.mean()), 2),
            "bars_any_open_pct": round(100.0 * float((dep > 0).mean()), 2),
            "bars_total": int(len(grid))}


def drawdown(rows: list[dict]) -> dict:
    if not rows:
        return {"dd_usd": 0.0, "peak_equity": 0.0}
    rr = []
    for r in rows:
        rr.append((ts(r["entry_time"]), ts(r["exit_time"]), r["symbol"], float(r["entry_px"]),
                   float(r["notional_usd"]), float(r["pnl_usd"])))
    times = set()
    for en, ex, sym, _, _, _ in rr:
        fr = FR[sym]
        times.update(fr.index[(fr.index >= en) & (fr.index <= ex)])
    times = sorted(times)
    by_exit: dict[pd.Timestamp, float] = {}
    for en, ex, sym, _, _, pnl in rr:
        by_exit[ex] = by_exit.get(ex, 0.0) + pnl
    closes = {sym: FR[sym]["close"] for sym in {x[2] for x in rr}}
    realized = peak = worst = 0.0
    for t in times:
        realized += by_exit.get(t, 0.0)
        mtm = realized
        for en, ex, sym, epx, notional, _ in rr:
            if en <= t < ex:
                c = closes[sym].get(t)
                if c is None:
                    continue
                mtm += L.pnl_of(epx, float(c), notional)
        peak = max(peak, mtm)
        worst = min(worst, mtm - peak)
    return {"dd_usd": round(worst, 2), "peak_equity": round(peak, 2)}


def summarize(rows: list[dict], warm: list[dict], window: str, coins) -> dict:
    net = round(sum(float(r["pnl_usd"]) for r in rows), 2)
    cyc = cycles(rows)
    holds = [int(r["bars_held"]) for r in rows]
    peak = peak_capital(rows)
    dd = drawdown(rows)
    reasons, reason_pnl = {}, {}
    for r in rows:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
        reason_pnl[r["reason"]] = round(reason_pnl.get(r["reason"], 0.0) + float(r["pnl_usd"]), 2)
    gross = 0.0
    for r in rows:
        qty = float(r["notional_usd"]) / float(r["entry_ref_px"])
        gross += qty * (float(r["exit_px"]) - float(r["entry_ref_px"]))
    n = len(rows)
    symbols = sorted({r["symbol"] for r in rows})
    return {
        "net": net, "slices": n, "cycles": len(cyc),
        "slices_per_cycle": round(n / len(cyc), 3) if cyc else None,
        "mean_hold_days": round(float(np.mean(holds)) * 4 / 24, 2) if holds else None,
        "median_hold_days": round(float(np.median(holds)) * 4 / 24, 2) if holds else None,
        "peak_concurrent": peak,
        "return_pct_on_peak": None if peak <= 0 else round(100.0 * net / peak, 3),
        "dd_usd": dd["dd_usd"],
        "dd_pct_of_peak": None if peak <= 0 else round(100.0 * dd["dd_usd"] / peak, 3),
        "peak_equity": dd["peak_equity"],
        "warmup_excluded": len(warm),
        "reasons": reasons, "reason_pnl": reason_pnl,
        "gross": round(gross, 2),
        "move": None if n == 0 else round(gross / n, 5),
        "per_slice": None if n == 0 else round(net / n, 5),
        "symbols_traded": len(symbols), "symbols": symbols,
        "exposure": exposure(rows, window, coins) if rows else None,
        "programmed_capital": 1000.0 * len(coins),
    }


def save_trades(name: str, rows: list[dict]) -> pathlib.Path:
    cols = ["symbol", "entry_time", "exit_time", "entry", "exit", "notional", "pnl", "reason", "stage", "bars_held"]
    if not rows:
        frame = pd.DataFrame(columns=cols)
    else:
        f = pd.DataFrame(rows)
        frame = pd.DataFrame({
            "symbol": f["symbol"], "entry_time": f["entry_time"], "exit_time": f["exit_time"],
            "entry": f["entry_ref_px"], "exit": f["exit_px"], "notional": f["notional_usd"],
            "pnl": f["pnl_usd"].map(lambda x: round(float(x), 4)), "reason": f["reason"],
            "stage": f["stage"], "bars_held": f["bars_held"],
        })
    path = OUT / f"trades_{name}.csv"
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


GUARD_LOG: list[str] = []


def guard(name: str) -> None:
    path = OUT / f"trades_{name}.csv"
    st = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
         "--trades", str(path), "--frames", str(FRAMES), "--cost", "0", "--bar-tag", "4h"],
        capture_output=True, text=True)
    line = next((l.strip() for l in st.stdout.splitlines() if "مخالفات" in l and "صفقات=" in l), st.stdout[-200:])
    GUARD_LOG.append(line)
    if st.returncode != 0 or "مخالفات الدخول=0" not in st.stdout or "مخالفات الخروج=0" not in st.stdout \
            or "تُخطّي=0" not in st.stdout:
        raise SystemExit(f"حارس التعبئة فشل على {name}:\n{st.stdout}\n{st.stderr}")


def range_check(rows: list[dict], name: str) -> None:
    for r in rows:
        fr = FR[r["symbol"]]
        en = fr.loc[ts(r["entry_time"])]
        ex = fr.loc[ts(r["exit_time"])]
        ep, xp = float(r["entry_ref_px"]), float(r["exit_px"])
        if abs(float(r["entry_px"]) - ep) > 1e-9:
            raise SystemExit(f"سعر الدخول ≠ الافتتاح في {name} (انزلاق ليس صفرًا)")
        if ep < float(en["low"]) - 1e-6 or ep > float(en["high"]) + 1e-6:
            raise SystemExit(f"دخول خارج الشمعة في {name}")
        if xp < float(ex["low"]) - 1e-6 or xp > float(ex["high"]) + 1e-6:
            raise SystemExit(f"خروج خارج الشمعة في {name}: {xp} [{ex['low']}, {ex['high']}]")


def reprice(rows: list[dict], cost: float) -> list[dict]:
    L.set_cost(cost)
    out = []
    for r in rows:
        q = dict(r)
        q["pnl_usd"] = L.pnl_of(float(r["entry_px"]), float(r["exit_px"]), float(r["notional_usd"]))
        out.append(q)
    L.set_cost(COST)
    return out


def emit(name: str, window: str, phase: str, rows: list[dict], warm: list[dict], coins,
         counted: bool, cost: float = COST) -> dict:
    L.set_cost(cost)
    range_check(rows, name)
    st = summarize(rows, warm, window, coins)
    st["cost"] = cost
    save_trades(name, rows)
    guard(name)
    if counted:
        # عدّ الإعدادات: في أ و د يُسجَّل الإعداد مرة واحدة ويغطي الفترتين (ورقة L0061: 5 بذور في الفترتين بسقف 6)
        log(name, "اختيار+حكم" if phase in ("أ", "د") else WIN_AR[window], phase)
    print(f"    {name}: صافي={st['net']} دورات={st['cycles']} شرائح={st['slices']} ذروة={st['peak_concurrent']} "
          f"عائد%={st['return_pct_on_peak']} هبوط={st['dd_usd']} عملات={st['symbols_traded']}", flush=True)
    L.set_cost(COST)
    return st


def buyhold(coins, capital: float, window: str) -> tuple[list[dict], dict]:
    s, e = ts(WIN[window][0]), ts(WIN[window][1])
    usable = []
    for sym in coins:
        w = FR[sym][(FR[sym].index >= s) & (FR[sym].index < e)]
        if len(w) >= 2:
            usable.append((sym, w))
    if not usable or capital <= 0:
        return [], {"net": 0.0, "capital": capital, "symbols": 0, "return_pct": None}
    each = capital / len(usable)
    L.set_cost(COST)
    rows = []
    for sym, w in usable:
        entry, exit_ = float(w["open"].iloc[0]), float(w["close"].iloc[-1])
        rows.append({"symbol": sym, "entry_time": w.index[0].isoformat(), "exit_time": w.index[-1].isoformat(),
                     "entry_ref_px": entry, "entry_px": entry, "exit_px": exit_, "notional_usd": each,
                     "pnl_usd": L.pnl_of(entry, exit_, each), "reason": "احتفاظ", "stage": 0,
                     "bars_held": len(w) - 1, "entry_bar": 0, "exit_bar": len(w) - 1})
    net = round(sum(r["pnl_usd"] for r in rows), 2)
    per = {r["symbol"]: round(r["pnl_usd"], 2) for r in rows}
    return rows, {"net": net, "capital": round(capital, 2), "symbols": len(usable),
                  "return_pct": round(100.0 * net / capital, 3), "per_symbol": per,
                  "spans": {r["symbol"]: (r["entry_time"][:10], r["exit_time"][:10]) for r in rows}}


def random_book(coins, template: list[dict], seed: int, window: str) -> list[dict]:
    s, e = ts(WIN[window][0]), ts(WIN[window][1])
    rows = []
    by = {}
    for group in cycles(template):
        by.setdefault(group[0]["symbol"], []).append(group)
    L.set_cost(COST)
    for sym in coins:
        groups = by.get(sym, [])
        n = len(groups)
        if n == 0:
            continue
        hold = max(int(np.median([max(int(r["bars_held"]) for r in g) for g in groups])), 1)
        notional = float(np.mean([sum(float(r["notional_usd"]) for r in g) for g in groups]))
        fr = FR[sym]
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
            entry, exit_ = float(w["open"].iloc[i + 1]), float(w["close"].iloc[i + 1 + hold])
            rows.append({"symbol": sym, "entry_time": w.index[i + 1].isoformat(),
                         "exit_time": w.index[i + 1 + hold].isoformat(),
                         "entry_ref_px": entry, "entry_px": entry, "exit_px": exit_, "notional_usd": notional,
                         "pnl_usd": L.pnl_of(entry, exit_, notional), "reason": "عشوائي", "stage": 0,
                         "bars_held": hold, "entry_bar": i + 1, "exit_bar": i + 1 + hold})
    return rows


# ───────────────────────────── المرحلة ج: التشريح ─────────────────────────────
def prior_low_series(sym: str) -> pd.Series:
    daily = pd.read_parquet(DAILY / f"{sym}_1d.parquet")
    pl = daily["low"].shift(1).rolling(C.LONG_CYCLE_DAILY_LOOKBACK,
                                       min_periods=max(30, C.LONG_CYCLE_DAILY_LOOKBACK // 3)).min()
    known = pd.DataFrame({"prior_low": pl}, index=daily.index + pd.Timedelta(days=1))
    return known.reindex(FR[sym].index, method="ffill")["prior_low"]


def regime_at(sym: str, t) -> str:
    v = REG[sym].get(ts(t).normalize())
    return v if isinstance(v, str) else "غير مصنّف"


def anatomy(rows: list[dict], label: str) -> dict:
    """c1..c4 على سجلّ واحد: شرط الإلغاء الحاكم · توزيع الخسائر · المدد · المناخ."""
    df = pd.DataFrame(rows)
    out = {"ledger": label, "slices": len(df)}
    if df.empty:
        return out
    df["entry_ts"] = df["entry_time"].map(ts)
    df["exit_ts"] = df["exit_time"].map(ts)
    df["days_held"] = df["bars_held"] * 4 / 24
    df["ret_pct"] = 100 * (df["exit_px"] / df["entry_ref_px"] - 1)
    # c1: أي فرع كان الحاكم في كل إلغاء (على مستوى الدورة: كل الشرائح تُغلق معًا)
    canc = df[df["reason"] == "إلغاء-دورة"]
    binding = {"8%-من-أدنى-دخول": 0, "قاع-90يومًا−2%": 0, "الاثنان-متساويان": 0}
    gaps = touches = 0
    cyc_rows = []
    for (sym, ex), g in canc.groupby(["symbol", "exit_ts"]):
        pl = prior_low_series(sym)
        bar = FR[sym].loc[ex]
        lvl_a = float(g["entry_px"].min()) * (1.0 - C.LONG_CYCLE_HARD_INVALIDATION_PCT)
        blow = pl.get(ex)
        lvl_b = float(blow) * 0.98 if blow is not None and np.isfinite(blow) else float("-inf")
        if abs(lvl_a - lvl_b) < 1e-9:
            binding["الاثنان-متساويان"] += 1
        elif lvl_a < lvl_b:
            binding["8%-من-أدنى-دخول"] += 1
        else:
            binding["قاع-90يومًا−2%"] += 1
        fill = float(g["exit_px"].iloc[0])
        if abs(fill - float(bar["open"])) < 1e-9 and float(bar["open"]) < min(lvl_a, lvl_b):
            gaps += 1
        else:
            touches += 1
        cyc_rows.append({"symbol": sym, "exit": str(ex)[:16], "n_tranches": len(g),
                         "cycle_pnl": round(float(g["pnl_usd"].sum()), 2),
                         "notional": round(float(g["notional_usd"].sum()), 2),
                         "drop_from_min_entry_pct": round(100 * (fill / float(g["entry_px"].min()) - 1), 2),
                         "days_from_first_entry": round(float((ex - g["entry_ts"].min()).total_seconds() / 86400), 1),
                         "regime_exit": regime_at(sym, ex), "regime_first_entry": regime_at(sym, g["entry_ts"].min())})
    cyc_df = pd.DataFrame(cyc_rows)
    out["c1_binding_branch"] = binding
    out["c1_fill_kind"] = {"لمس-المستوى": touches, "فجوة-تحت-المستوى(افتتاح)": gaps}
    out["c1_condition"] = ("low ≤ min( أدنى سعر دخول في الدورة × (1−0.08) , أدنى قاع يومي في آخر 90 يومًا (المعروف حتى أمس) × (1−0.02) ) ⇒ "
                           "تُغلق كل شرائح الدورة معًا؛ التعبئة عند الافتتاح إن افتتحت الشمعة تحت المستوى وإلا عند المستوى.")
    # c2: توزيع خسائر الإلغاء على مستوى الدورة
    if not cyc_df.empty:
        losses = cyc_df["cycle_pnl"].sort_values()
        tot = float(losses.sum())
        k = min(5, len(losses))
        out["c2_cancel_cycles"] = int(len(losses))
        out["c2_total"] = round(tot, 2)
        out["c2_mean"] = round(float(losses.mean()), 2)
        out["c2_median"] = round(float(losses.median()), 2)
        out["c2_quantiles"] = {q: round(float(losses.quantile(q)), 2) for q in (0.1, 0.25, 0.5, 0.75, 0.9)}
        out["c2_worst5_share_pct"] = round(100 * float(losses.iloc[:k].sum()) / tot, 1) if tot else None
        out["c2_worst5"] = cyc_df.sort_values("cycle_pnl").head(5).to_dict("records")
        out["c2_positive_cancels"] = int((losses > 0).sum())
        out["c2_drop_pct_median"] = round(float(cyc_df["drop_from_min_entry_pct"].median()), 2)
        out["c2_single_tranche_cycles"] = int((cyc_df["n_tranches"] == 1).sum())
        out["c2_cycle_pnl_by_size"] = {str(int(n)): round(float(g["cycle_pnl"].sum()), 2) for n, g in cyc_df.groupby("n_tranches")}
    # c3: المدد
    out["c3_days_by_reason"] = {
        r: {"n": int(len(g)), "mean_days": round(float(g["days_held"].mean()), 1),
            "median_days": round(float(g["days_held"].median()), 1),
            "pnl": round(float(g["pnl_usd"].sum()), 2), "mean_ret_pct": round(float(g["ret_pct"].mean()), 2)}
        for r, g in df.groupby("reason")}
    if not cyc_df.empty:
        out["c3_cancel_days_from_first_entry"] = {"mean": round(float(cyc_df["days_from_first_entry"].mean()), 1),
                                                  "median": round(float(cyc_df["days_from_first_entry"].median()), 1),
                                                  "under_7_days": int((cyc_df["days_from_first_entry"] < 7).sum())}
    # c4: المناخ
    df["regime_exit"] = [regime_at(s, t) for s, t in zip(df["symbol"], df["exit_ts"])]
    df["regime_entry"] = [regime_at(s, t) for s, t in zip(df["symbol"], df["entry_ts"])]
    out["c4_regime_at_exit_by_reason"] = {r: g["regime_exit"].value_counts().to_dict() for r, g in df.groupby("reason")}
    out["c4_regime_at_entry_by_reason"] = {r: g["regime_entry"].value_counts().to_dict() for r, g in df.groupby("reason")}
    out["c4_pnl_by_entry_regime"] = {r: round(float(g["pnl_usd"].sum()), 2) for r, g in df.groupby("regime_entry")}
    if not cyc_df.empty:
        out["c4_cancel_cycles_by_exit_regime"] = cyc_df["regime_exit"].value_counts().to_dict()
        out["c4_cancel_cycles_by_entry_regime"] = cyc_df["regime_first_entry"].value_counts().to_dict()
    out["cycles_table"] = cyc_rows
    return out


def gap_decomposition(rows: list[dict], coins, window: str, peak: float) -> dict:
    """c5: فارق الاحتفاظ − الاستراتيجية مفكَّكًا بفواصل الأحداث بأسعار الصفقات نفسها (متطابق حسابيًّا).
    الاحتفاظ: كمية q_hold = (الذروة ÷ عدد العملات) ÷ أول افتتاح. الاستراتيجية: q = notional ÷ سعر الدخول لكل شريحة.
    فارق الإجمالي = Σ_خارج السوق q_hold·ΔP + Σ_داخل السوق (q_hold − q_strat)·ΔP ، ثم فرق الكلفة."""
    s, e = ts(WIN[window][0]), ts(WIN[window][1])
    usable = [sym for sym in coins if len(FR[sym][(FR[sym].index >= s) & (FR[sym].index < e)]) >= 2]
    each = peak / len(usable)
    buckets = ["قبل-أول-دخول", "خارج-بعد-إلغاء", "خارج-بعد-توزيع", "خارج-بعد-نهاية-العينة",
               "داخل-كامل", "داخل-بعد-توزيع-جزئي"]
    tot = {b: 0.0 for b in buckets}
    per_sym = {}
    hold_gross_sum = strat_gross_sum = hold_net_sum = strat_net_sum = 0.0
    for sym in usable:
        w = FR[sym][(FR[sym].index >= s) & (FR[sym].index < e)]
        P0, P1 = float(w["open"].iloc[0]), float(w["close"].iloc[-1])
        q_hold = each / P0
        hold_gross = q_hold * (P1 - P0)
        hold_net = L.pnl_of(P0, P1, each)
        ev = []
        srows = [r for r in rows if r["symbol"] == sym]
        for r in srows:
            q = float(r["notional_usd"]) / float(r["entry_ref_px"])
            ev.append((ts(r["entry_time"]), 0, float(r["entry_ref_px"]), q, "entry"))
            ev.append((ts(r["exit_time"]), 1, float(r["exit_px"]), -q, r["reason"]))
        ev.sort(key=lambda x: (x[0], x[1]))
        cur_px, q_s, state = P0, 0.0, "قبل-أول-دخول"
        distributed_partial = False
        b = {k: 0.0 for k in buckets}
        strat_gross = 0.0
        for t, _, px, dq, kind in ev:
            d = px - cur_px
            if q_s > 1e-12:
                key = "داخل-بعد-توزيع-جزئي" if distributed_partial else "داخل-كامل"
                b[key] += (q_hold - q_s) * d
                strat_gross += q_s * d
            else:
                b[state] += q_hold * d
            q_s += dq
            cur_px = px
            if kind == "entry":
                if q_s - dq <= 1e-12:
                    distributed_partial = False
            else:
                if q_s <= 1e-9:
                    q_s = 0.0
                    state = {"إلغاء-دورة": "خارج-بعد-إلغاء", "توزيع-قمة": "خارج-بعد-توزيع",
                             "نهاية-العينة": "خارج-بعد-نهاية-العينة"}[kind]
                    distributed_partial = False
                elif kind == "توزيع-قمة":
                    distributed_partial = True
        d = P1 - cur_px
        if q_s > 1e-12:
            b["داخل-كامل"] += (q_hold - q_s) * d
            strat_gross += q_s * d
        else:
            b[state] += q_hold * d
        strat_net = sum(float(r["pnl_usd"]) for r in srows)
        chk = hold_gross - strat_gross - sum(b.values())
        if abs(chk) > 1e-6:
            raise SystemExit(f"التفكيك لا يتطابق في {sym}: {chk}")
        per_sym[sym] = {"hold_net": round(hold_net, 2), "strat_net": round(strat_net, 2),
                        "gap_net": round(hold_net - strat_net, 2),
                        "hold_gross": round(hold_gross, 2), "strat_gross": round(strat_gross, 2),
                        **{k: round(v, 2) for k, v in b.items()}}
        for k in buckets:
            tot[k] += b[k]
        hold_gross_sum += hold_gross
        strat_gross_sum += strat_gross
        hold_net_sum += hold_net
        strat_net_sum += strat_net
    hold_cost = hold_gross_sum - hold_net_sum
    strat_cost = strat_gross_sum - strat_net_sum
    gap_gross = hold_gross_sum - strat_gross_sum
    gap_net = hold_net_sum - strat_net_sum
    return {"window": window, "coins": len(usable), "peak_capital": peak, "hold_capital_each": round(each, 2),
            "hold_net": round(hold_net_sum, 2), "strat_net": round(strat_net_sum, 2), "gap_net": round(gap_net, 2),
            "hold_gross": round(hold_gross_sum, 2), "strat_gross": round(strat_gross_sum, 2), "gap_gross": round(gap_gross, 2),
            "hold_cost": round(hold_cost, 2), "strat_cost": round(strat_cost, 2),
            "cost_effect(strat−hold)": round(strat_cost - hold_cost, 2),
            "buckets_usd": {k: round(v, 2) for k, v in tot.items()},
            "buckets_pct_of_gap_gross": {k: (round(100 * v / gap_gross, 1) if gap_gross else None) for k, v in tot.items()},
            "identity": "gap_gross = Σ buckets ; gap_net = gap_gross + (strat_cost − hold_cost)",
            "per_symbol": per_sym}


# ───────────────────────────── التشغيل ─────────────────────────────
def main() -> int:
    L.set_cost(COST)
    table: dict = {"universe": list(UNIVERSE), "allowed4": list(ALLOWED)}

    print("══ مرحلة 0 — الهوية وحدّ الأربع ══", flush=True)
    ident = {sym: {"copy_vs_engine": R[sym]["identity_copy_vs_engine"], "n": R[sym]["identity_n"],
                   "engine_real_label_returns": R[sym].get("engine_with_real_label_returns"),
                   "first": R[sym]["first"][:10], "last": R[sym]["last"][:10], "h4_bars": R[sym]["h4_bars"]}
             for sym in L.ALL_FILES}
    ident["BTCUSDT"]["label_swap_BNB_equals_BTC"] = R["BTCUSDT"].get("identity_label_swap")
    dump("identity.json", ident)
    bad = [s for s in L.ALL_FILES if not R[s]["identity_copy_vs_engine"]]
    if bad or not R["BTCUSDT"].get("identity_label_swap"):
        raise SystemExit(f"الهوية فشلت: {bad} / label_swap={R['BTCUSDT'].get('identity_label_swap')} — التوسيع يتوقف")
    for s in L.ALL_FILES:
        if s not in ALLOWED and R[s].get("engine_with_real_label_returns") != 0:
            raise SystemExit(f"{s}: المحرك بالاسم الحقيقي لم يرجع فراغًا — التشخيص خاطئ")
    print(f"  هوية النسخة = المحرك على {len(L.ALL_FILES)}/17 · تبديل التسمية على BTC = متطابق · "
          f"المحرك بالاسم الحقيقي يرجع فراغًا لـ{sum(1 for s in L.ALL_FILES if s not in ALLOWED)} ملفًا", flush=True)

    print("══ مرحلة 0 — إعادة إنتاج L0060 على الأربع ══", flush=True)
    sel4, sel4w = rows_for(R, "open", ALLOWED, "SEL")
    jud4, jud4w = rows_for(R, "open", ALLOWED, "JUD")
    st_sel4 = emit("p0_open4_c00115_SEL", "SEL", "0", sel4, sel4w, ALLOWED, False)
    st_jud4 = emit("p0_open4_c00115_JUD", "JUD", "0", jud4, jud4w, ALLOWED, False)
    ref = {"SEL": (-12.59, 33, 47, 1800.0), "JUD": (417.35, 31, 40, 1350.0)}
    for w, st in (("SEL", st_sel4), ("JUD", st_jud4)):
        n, cy, sl, pk = ref[w]
        if abs(st["net"] - n) > 0.5 or st["cycles"] != cy or st["slices"] != sl or st["peak_concurrent"] != pk:
            raise SystemExit(f"المرحلة 0 خالفت L0060 في {w}: {st['net']}/{st['cycles']}/{st['slices']}/{st['peak_concurrent']}")
    bh_rows, bh = buyhold(ALLOWED, 1350.0, "JUD")
    st_bh4j = emit("p0_hold4_JUD", "JUD", "0", bh_rows, [], ALLOWED, False)
    if abs(bh["net"] - 595.82) > 0.5:
        raise SystemExit(f"احتفاظ الحكم خالف L0060: {bh['net']}")
    bh_rows_s, bh_s = buyhold(ALLOWED, 1800.0, "SEL")
    st_bh4s = emit("p0_hold4_SEL", "SEL", "0", bh_rows_s, [], ALLOWED, False)
    if abs(bh_s["net"] - (-422.15)) > 0.5:
        raise SystemExit(f"احتفاظ الاختيار خالف L0060: {bh_s['net']}")
    # الهابط على الأربع (مرجع L0060: −67.17/30/43 · +536.61/14/20) — تحقق، لا يُحسب
    bsel4, bsel4w = rows_for(R, "bear", ALLOWED, "SEL")
    bjud4, bjud4w = rows_for(R, "bear", ALLOWED, "JUD")
    st_bsel4 = emit("p0_bear4_c00115_SEL", "SEL", "0", bsel4, bsel4w, ALLOWED, False)
    st_bjud4 = emit("p0_bear4_c00115_JUD", "JUD", "0", bjud4, bjud4w, ALLOWED, False)
    # ⚠️ اكتشاف: أرقام الهابط المنشورة في L0060 (−67.17 / +536.61 بوسم 0.115%) لا تُنتَج عند 0.115%
    # بل عند 0.130% بالضبط — تسرّب حالة الكلفة في run_l0060_measure.py: آخر emit(COST_130) ترك
    # C.COMMISSION_PCT=0.0013 قبل run_all("falling"). الصفقات نفسها حرفيًّا؛ الفرق في التسوية فقط.
    st_bsel4_130 = emit("p0_bear4_c00130_SEL", "SEL", "0", reprice(bsel4, COST_130), bsel4w, ALLOWED, False, COST_130)
    st_bjud4_130 = emit("p0_bear4_c00130_JUD", "JUD", "0", reprice(bjud4, COST_130), bjud4w, ALLOWED, False, COST_130)
    l60 = {"SEL": (-67.17, 30, 43), "JUD": (536.61, 14, 20)}
    for w, st115, st130 in (("SEL", st_bsel4, st_bsel4_130), ("JUD", st_bjud4, st_bjud4_130)):
        n, cy, sl = l60[w]
        if st115["cycles"] != cy or st115["slices"] != sl or abs(st130["net"] - n) > 0.5:
            raise SystemExit(f"الهابط على الأربع خالف L0060 حتى بعد تفسير الكلفة: {w} {st115['net']}/{st130['net']}")
    bear_note = {"finding": "أرقام الهابط في L0060 المنشورة بوسم 0.115% هي فعليًّا عند 0.130% (تسرّب set_cost(COST_130) قبل run_all('falling')).",
                 "L0060_published": {"SEL": -67.17, "JUD": 536.61},
                 "reproduced_at_0.130": {"SEL": st_bsel4_130["net"], "JUD": st_bjud4_130["net"]},
                 "correct_at_0.115": {"SEL": st_bsel4["net"], "JUD": st_bjud4["net"]},
                 "trades_identical": True, "verdict_impact": "لا يغيّر حكم L0060 (الاختيار سالب · تحت الاحتفاظ)."}
    print(f"  ⚠️ الهابط4: 0.115% = {st_bsel4['net']}/{st_bjud4['net']} · 0.130% = {st_bsel4_130['net']}/{st_bjud4_130['net']} "
          f"= أرقام L0060 المنشورة بوسم 0.115%", flush=True)
    print("  ✅ المرحلة 0 طابقت L0060 (open4 · hold4 · bear4 بعد تفسير الكلفة)", flush=True)
    table["phase0"] = {"open4": {"SEL": st_sel4, "JUD": st_jud4}, "hold4": {"SEL": bh_s, "JUD": bh},
                       "hold4_stats": {"SEL": st_bh4s, "JUD": st_bh4j},
                       "bear4": {"c00115": {"SEL": st_bsel4, "JUD": st_bjud4}, "c00130": {"SEL": st_bsel4_130, "JUD": st_bjud4_130}},
                       "bear4_cost_finding": bear_note}

    print("══ مرحلة أ — 16 عملة · الفترتان ══", flush=True)
    sel16, sel16w = rows_for(R, "open", UNIVERSE, "SEL")
    jud16, jud16w = rows_for(R, "open", UNIVERSE, "JUD")
    st_sel16 = emit("a_open16_c00115_SEL", "SEL", "أ", sel16, sel16w, UNIVERSE, False)
    st_jud16 = emit("a_open16_c00115_JUD", "JUD", "أ", jud16, jud16w, UNIVERSE, True)   # a1 (الفترتان = قياس واحد)
    st_sel16_130 = emit("a_open16_c00130_SEL", "SEL", "أ", reprice(sel16, COST_130), sel16w, UNIVERSE, False, COST_130)
    st_jud16_130 = emit("a_open16_c00130_JUD", "JUD", "أ", reprice(jud16, COST_130), jud16w, UNIVERSE, True, COST_130)  # a2
    h16s_rows, h16s = buyhold(UNIVERSE, st_sel16["peak_concurrent"], "SEL")
    h16j_rows, h16j = buyhold(UNIVERSE, st_jud16["peak_concurrent"], "JUD")
    st_h16s = emit("a_hold16_SEL", "SEL", "أ", h16s_rows, [], UNIVERSE, False)
    st_h16j = emit("a_hold16_JUD", "JUD", "أ", h16j_rows, [], UNIVERSE, True)  # a3
    bsel16, bsel16w = rows_for(R, "bear", UNIVERSE, "SEL")
    bjud16, bjud16w = rows_for(R, "bear", UNIVERSE, "JUD")
    st_bsel16 = emit("a_bear16_c00115_SEL", "SEL", "أ", bsel16, bsel16w, UNIVERSE, False)
    st_bjud16 = emit("a_bear16_c00115_JUD", "JUD", "أ", bjud16, bjud16w, UNIVERSE, True)  # a4
    table["A"] = {"open16": {"c00115": {"SEL": st_sel16, "JUD": st_jud16}, "c00130": {"SEL": st_sel16_130, "JUD": st_jud16_130}},
                  "hold16": {"SEL": h16s, "JUD": h16j, "stats": {"SEL": st_h16s, "JUD": st_h16j}},
                  "bear16": {"c00115": {"SEL": st_bsel16, "JUD": st_bjud16}},
                  "per_symbol_open16": {w: {s: round(sum(r["pnl_usd"] for r in rows if r["symbol"] == s), 2)
                                            for s in UNIVERSE} for w, rows in (("SEL", sel16), ("JUD", jud16))}}

    print("══ مرحلة ب — الدورة الكاملة ══", flush=True)
    B = {}
    for tag, coins in (("4", ALLOWED), ("16", UNIVERSE)):
        of, ofw = rows_for(R, "open", coins, "FULL")
        st_of = emit(f"b_open{tag}_c00115_FULL", "FULL", "ب", of, ofw, coins, True)
        st_of130 = emit(f"b_open{tag}_c00130_FULL", "FULL", "ب", reprice(of, COST_130), ofw, coins, True, COST_130)
        hr, hs = buyhold(coins, st_of["peak_concurrent"], "FULL")
        st_h = emit(f"b_hold{tag}_FULL", "FULL", "ب", hr, [], coins, True)
        bf, bfw = rows_for(R, "bear", coins, "FULL")
        st_bf = emit(f"b_bear{tag}_c00115_FULL", "FULL", "ب", bf, bfw, coins, True)
        st_bf130 = emit(f"b_bear{tag}_c00130_FULL", "FULL", "ب", reprice(bf, COST_130), bfw, coins, True, COST_130)
        B[tag] = {"open": {"c00115": st_of, "c00130": st_of130}, "hold": hs, "hold_stats": st_h,
                  "bear": {"c00115": st_bf, "c00130": st_bf130},
                  "per_symbol_open": {s: round(sum(r["pnl_usd"] for r in of if r["symbol"] == s), 2) for s in coins},
                  "per_symbol_hold": hs.get("per_symbol")}
        B[tag]["open_rows"] = of
        B[tag]["bear_rows"] = bf
    table["B"] = {k: {kk: vv for kk, vv in v.items() if not kk.endswith("_rows")} for k, v in B.items()}

    print("══ مرحلة ج — تشريح الإلغاء ══", flush=True)
    Cc = {}
    Cc["open4_JUD"] = anatomy(jud4, "open4 · حكم")
    Cc["open4_FULL"] = anatomy(B["4"]["open_rows"], "open4 · الدورة الكاملة")
    Cc["open16_FULL"] = anatomy(B["16"]["open_rows"], "open16 · الدورة الكاملة")
    Cc["open4_SEL"] = anatomy(sel4, "open4 · اختيار")
    for i, nm in enumerate(("c1_شرط_الإلغاء_والفرع_الحاكم", "c2_توزيع_خسائر_الإلغاء", "c3_المدد", "c4_المناخ"), 1):
        log(nm, "حكم open4 (+سياق)", "ج")
    Cc["gap_open4_JUD"] = gap_decomposition(jud4, ALLOWED, "JUD", 1350.0)
    Cc["gap_open4_FULL"] = gap_decomposition(B["4"]["open_rows"], ALLOWED, "FULL", B["4"]["open"]["c00115"]["peak_concurrent"])
    Cc["gap_open16_FULL"] = gap_decomposition(B["16"]["open_rows"], UNIVERSE, "FULL", B["16"]["open"]["c00115"]["peak_concurrent"])
    Cc["gap_open4_SEL"] = gap_decomposition(sel4, ALLOWED, "SEL", 1800.0)
    log("c5_تفكيك_فارق_الاحتفاظ", "حكم open4 (+سياق)", "ج")
    dump("phase_c_anatomy.json", Cc)
    table["C_summary"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("cycles_table", "per_symbol", "c2_worst5")}
                          for k, v in Cc.items()}

    print("══ مرحلة د — أفضل مسار والعشوائي ══", flush=True)
    cands = {"open4": st_jud4["return_pct_on_peak"], "bear4": st_bjud4["return_pct_on_peak"],
             "open16": st_jud16["return_pct_on_peak"], "bear16": st_bjud16["return_pct_on_peak"]}
    order = ["open4", "open16", "bear4", "bear16"]  # ترتيب كسر التعادل: المفتوح ثم الأربع
    best = max(order, key=lambda k: ((-1e18 if cands[k] is None else cands[k]), -order.index(k)))
    print(f"  عوائد الحكم %: {cands} ⇒ الأفضل {best}", flush=True)
    chosen = {"open4": (sel4, jud4, ALLOWED), "bear4": (bsel4, bjud4, ALLOWED),
              "open16": (sel16, jud16, UNIVERSE), "bear16": (bsel16, bjud16, UNIVERSE)}[best]
    rnd = []
    for seed in SEEDS:
        for w, template in (("SEL", chosen[0]), ("JUD", chosen[1])):
            rows = random_book(chosen[2], template, seed, w)
            st = emit(f"d_r_{seed}_{w}", w, "د", rows, [], chosen[2], w == "JUD")
            rnd.append({"seed": seed, "window": w, "net": st["net"], "peak": st["peak_concurrent"],
                        "return_pct_on_peak": st["return_pct_on_peak"], "slices": st["slices"]})
    table["D"] = {"candidates_jud_return_pct": cands, "best": best, "random": rnd,
                  "random_summary": {w: {"mean": round(float(np.mean([x["net"] for x in rnd if x["window"] == w])), 2),
                                         "max": max(x["net"] for x in rnd if x["window"] == w),
                                         "min": min(x["net"] for x in rnd if x["window"] == w)} for w in ("SEL", "JUD")}}

    print("══ الحتمية (pass2) ══", flush=True)
    det = {}
    if len(R2) == len(R):
        checks = [("b_open4_c00115_FULL", "open", ALLOWED, "FULL"), ("b_open16_c00115_FULL", "open", UNIVERSE, "FULL"),
                  ("a_open16_c00115_SEL", "open", UNIVERSE, "SEL"), ("a_open16_c00115_JUD", "open", UNIVERSE, "JUD"),
                  ("b_bear16_c00115_FULL", "bear", UNIVERSE, "FULL"), ("b_bear4_c00115_FULL", "bear", ALLOWED, "FULL"),
                  ("p0_open4_c00115_SEL", "open", ALLOWED, "SEL"), ("p0_open4_c00115_JUD", "open", ALLOWED, "JUD")]
        for name, path, coins, w in checks:
            h1 = hashlib.sha256((OUT / f"trades_{name}.csv").read_bytes()).hexdigest()
            rows2, _ = rows_for(R2, path, coins, w)
            tmp = save_trades(name + "__pass2", rows2)
            h2 = hashlib.sha256(tmp.read_bytes()).hexdigest()
            tmp.unlink()
            det[name] = {"pass1": h1[:16], "pass2": h2[:16], "match": h1 == h2}
            if h1 != h2:
                raise SystemExit(f"الحتمية فشلت في {name}")
        print(f"  sha256 طابق في {len(det)} ملفًا", flush=True)
    else:
        det = {"status": "pass2 غير مكتمل"}
    table["determinism"] = det

    dump("results.json", table)
    dump("ledger.json", LEDGER)
    dump("guard_log.json", GUARD_LOG)
    import importlib
    ver = {m: importlib.import_module(m).__version__ for m in ("pandas", "numpy", "pyarrow")}
    env = {"date": "2026-09-27", "python": sys.version.split()[0], **ver, "platform": platform.platform(),
           "cap": CAP, "counted": len(LEDGER), "ledger": LEDGER,
           "cost": "COMMISSION=0.00115 أو 0.00130 و SLIPPAGE=0 في الذاكرة (كما L0060). ثوابت الملف 0.10%+0.03% لم تُستخدم.",
           "v2": os.getenv("NOVA_LC_V2", "1"), "smc": str(C.SMC_GATE_ENABLED),
           "capital_programmed_per_coin": C.LONG_CYCLE_CAPITAL_USD, "weights": list(C.LONG_CYCLE_STAGE_WEIGHTS),
           "universe16": list(UNIVERSE), "duplicate_excluded": L.DUPLICATE, "allowed4": list(ALLOWED),
           "label_pass": "لغير الأربع مُرِّر 'BTCUSDT' تسميةً إلى LC.run ثم أُعيد الاسم الحقيقي في الغلاف. nova_v8 لم يُمس.",
           "windows": WIN, "archive_first_bar": "2021-09-01 لكل العملات — لا تسخين قبل الاختيار",
           "data_end": "2026-08-30 23:59 (end=2026-08-31 حصري كما في L0060)",
           "frames": str(FRAMES), "records": str(RECS), "regime_py": False,
           "determinism": det, "guard_files": len(GUARD_LOG), "best_path": best}
    (OUT / "env_dump.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"اكتمل. المستهلك {len(LEDGER)}/{CAP}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
