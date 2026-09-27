# -*- coding: utf-8 -*-
"""L0061 — دورة التراكم: القياس العادل (المكتبة + تمريرتا التشغيل).

مكتوب قبل أي رقم جديد للوحدة. لا تطوير. لا تعديل لأي ملف في nova_v8/.

ما يفعله هذا الملف:
  1. يبني كاش الشموع 4h واليومي لكل ملفات الأرشيف (17 ملفًا) في ~/.cache/l0061_h4 و l0061_1d
     من `common.load` نفسه (لا محمّل بديل)، ويتحقق أن شموع الوحدة (_resample) تطابق `to_bars(240)`.
  2. يشغّل محرك `nova_v8.long_cycle.run` **كما هو** على كل عملة، عملة واحدة في الذاكرة في كل مرة
     (الذاكرة 2GB)، ويحفظ سجلّات الشرائح في JSON صغير لكل عملة وكل تمريرة (pass1 / pass2 للحتمية).

حدّ الأربع عملات (المرحلة أ — التشخيص مكتوب هنا قبل القياس):
  `long_cycle.run()` السطر 62: `if symbol not in {"BTCUSDT","BNBUSDT","SOLUSDT","LINKUSDT"}: return []`
  مجموعة حرفية داخل الدالة. لا ثابت في config، لا متغيّر بيئة، لا معامل. الرمز لا يُستعمل في أي
  حساب آخر داخل الدالة (تسمية السجل فقط). ⇒ يمكن تشغيل **المحرك نفسه** على أي عملة بتمرير
  رمز من القائمة كتسمية ثم إعادة التسمية في الغلاف — صفر تعديل في nova_v8. وتُثبَت الهوية:
  (أ) على BTC: المحرك بتسمية BNBUSDT = المحرك بتسمية BTCUSDT (عدا حقل الاسم).
  (ب) على كل عملة: نسخة المختبر `run_gated(..., None)` بلا القائمة = المحرك بالتسمية الممرَّرة.

النوافذ: اختيار 2021-09-01→2023-12-31 (قصّ البيانات عند 2024-01-01 كما في L0060) ·
حكم 2024-01-01→2026-08-31 (تشغيل متصل، ما دخل قبل 2024-01-01 تسخين لا يُحسب) ·
الدورة الكاملة 2021-09-01→2026-08-31 (التشغيل المتصل نفسه بلا استبعاد).
⚠️ الأرشيف يبدأ 2021-09-01 لكل العملات ⇒ لا توجد بيانات تسخين قبل الاختيار (الورقة قالت من 2021-06-01).
"""
from __future__ import annotations

import gc
import json
import os
import pathlib
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
os.environ.setdefault("NOVA_HOME", "/home/user/.nova_scratch/home")

import common as CM  # noqa: E402
import nova_v8.config as C  # noqa: E402
import nova_v8.indicators as ind  # noqa: E402
import nova_v8.long_cycle as LC  # noqa: E402
from nova_v8.execution import market_cost_pct, market_fill, net_fraction, settle_directional, Position  # noqa: E402

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0061"
OUT.mkdir(parents=True, exist_ok=True)
FRAMES = pathlib.Path.home() / ".cache" / "l0061_h4"
DAILY = pathlib.Path.home() / ".cache" / "l0061_1d"
RECS = pathlib.Path.home() / ".cache" / "l0061_records"
for p in (FRAMES, DAILY, RECS):
    p.mkdir(parents=True, exist_ok=True)

DEC_S, CUT = "2021-09-01", "2024-01-01"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
COST = 0.00115
COST_130 = 0.00130
ALLOWED = ("BTCUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT")
ALL_FILES = tuple(sorted(p.name.split("_")[0] for p in (ROOT / "crypto_archive").glob("*USDT_1m.parquet")))
# TONUSDT نسخة مبتورة من GRAMUSDT (994,620 شمعة مشتركة متطابقة حرفيًّا · فرق 0.0) ⇒ عملة واحدة.
DUPLICATE = {"TONUSDT": "GRAMUSDT"}
UNIVERSE = tuple(s for s in ALL_FILES if s not in DUPLICATE)


def set_cost(cost: float) -> None:
    C.COMMISSION_PCT = float(cost)
    C.SLIPPAGE_PCT = 0.0


def pnl_of(entry_px: float, exit_px: float, notional: float) -> float:
    if entry_px <= 0:
        return 0.0
    return float(net_fraction(entry_px, exit_px, 1, 0.0) * notional)


# ───────────────────────── نسخة المختبر (من L0060 حرفيًّا، بلا قائمة الرموز) ─────────────────────────
def run_gated(df1m: pd.DataFrame, symbol: str, entry_ok=None) -> list[dict]:
    """نسخة L0060 من run() مع بوابة على قرار الشراء فقط. الفرق الوحيد عن L0060: حُذف شرط القائمة
    (لأنه موضوع التشخيص). تُستعمل للهابط فقط بعد إثبات تطابقها مع المحرك على كل عملة."""
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

    def rec(tr, exit_i, px, reason):
        pos = Position(symbol=symbol, side=1, entry=tr["entry_px"], entry_px=tr["entry_px"],
                       atr_pct=0.02, trigger="CycleBottom", regime=C.REGIME_BULL,
                       notional=tr["notional"], entry_bar=tr["entry_i"],
                       entry_ref_px=tr["entry_ref"], entry_cost_pct=tr["entry_cost"], series=series)
        net = settle_directional(pos, px, slip_pct=cost_at(exit_i))
        return {
            "symbol": symbol, "stage": int(tr["stage"]), "series": int(series),
            "entry_bar": int(tr["entry_i"]), "exit_bar": int(exit_i),
            "entry_time": pd.Timestamp(idx[tr["entry_i"]]).isoformat(),
            "exit_time": pd.Timestamp(idx[exit_i]).isoformat(),
            "bars_held": int(exit_i - tr["entry_i"]),
            "pnl_usd": net * tr["notional"], "notional_usd": tr["notional"],
            "reason": reason, "entry_px": tr["entry_px"], "entry_ref_px": tr["entry_ref"],
            "exit_px": px,
        }

    def close_tranches(exit_i: int, reason: str, px: float):
        nonlocal tranches, top_seen, next_stage
        for tr in list(tranches):
            records.append(rec(tr, exit_i, px, reason))
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
            records.append(rec(tr, i, c, "توزيع-قمة"))
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


def from_engine(recs: list[dict], symbol: str) -> list[dict]:
    out = []
    for r in recs:
        out.append({
            "symbol": symbol,
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
    return sorted((r["entry_time"], r["exit_time"], r["reason"], int(r["stage"]),
                   round(r["entry_ref_px"], 6), round(r["exit_px"], 6),
                   round(r["pnl_usd"], 6), round(r["notional_usd"], 4)) for r in rows)


def engine_run(df1m: pd.DataFrame, symbol: str) -> list[dict]:
    """تشغيل المحرك نفسه. لغير الأربع تُمرَّر تسمية من القائمة ثم يُعاد الاسم الحقيقي في الغلاف."""
    label = symbol if symbol in ALLOWED else "BTCUSDT"
    return from_engine(LC.run(df1m, label), symbol)


def regime_labels(daily: pd.DataFrame) -> pd.Series:
    """مصنّف المادة 13 حرفيًّا مع shift(1). يومي."""
    c = daily["close"]
    e50 = c.ewm(span=50, adjust=False).mean()
    e200 = c.ewm(span=200, adjust=False).mean()
    slope = e50.diff(10)
    lab = pd.Series("عرضي", index=daily.index)
    lab[(e50 > e200) & (slope > 0)] = "صاعد"
    lab[(e50 < e200) & (slope < 0)] = "هابط"
    return lab.shift(1)


def save_frames(sym: str, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    h4 = LC._resample(df, "4h")
    official = CM.to_bars(df, 240)
    if len(h4) != len(official) or len(h4.index.intersection(official.index)) != len(h4):
        raise SystemExit(f"اصطفاف 4h خالف to_bars في {sym}")
    for col in ("open", "high", "low", "close"):
        if (h4[col] - official[col]).abs().gt(1e-8).any():
            raise SystemExit(f"شموع 4h خالفت to_bars في {sym}")
    broken = ((h4["open"] < h4["low"]) | (h4["open"] > h4["high"])
              | (h4["close"] < h4["low"]) | (h4["close"] > h4["high"])).any()
    if broken:
        raise SystemExit(f"OHLC مكسور في {sym}")
    h4.to_parquet(FRAMES / f"{sym}_4h.parquet")
    daily = CM.to_bars(df, 1440)
    daily.to_parquet(DAILY / f"{sym}_1d.parquet")
    lab = regime_labels(daily)
    lab.rename("regime").to_frame().to_parquet(DAILY / f"{sym}_regime.parquet")
    return h4, daily


def bear_gate(lab: pd.Series):
    lookup = {ts.normalize(): val for ts, val in lab.items()}

    def ok(ts, lookup=lookup):
        return lookup.get(pd.Timestamp(ts).tz_convert("UTC").normalize(), np.nan) == "هابط"
    return ok


def run_symbol(sym: str, pass_tag: str) -> dict:
    t0 = time.time()
    set_cost(COST)
    df = CM.load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), start=WARM, end=JUD_E)
    h4, daily = save_frames(sym, df)
    lab = regime_labels(daily)
    ok = bear_gate(lab)
    cut = df[df.index < pd.Timestamp(CUT, tz="UTC")]
    out = {"symbol": sym, "pass": pass_tag, "first": str(df.index[0]), "last": str(df.index[-1]),
           "h4_bars": int(len(h4)), "daily_bars": int(len(daily)), "cut_rows": int(len(cut))}
    out["open_cut"] = engine_run(cut, sym) if len(cut) else []
    out["open_full"] = engine_run(df, sym)
    out["bear_cut"] = run_gated(cut, sym, ok) if len(cut) else []
    out["bear_full"] = run_gated(df, sym, ok)
    # هوية نسخة المختبر مع المحرك (بلا بوابة) على النافذة الكاملة — لكل عملة
    copy_full = run_gated(df, sym, None)
    out["identity_copy_vs_engine"] = key_of(copy_full) == key_of(out["open_full"])
    out["identity_n"] = len(copy_full)
    # هوية التسمية: على BTC، المحرك بتسمية BNBUSDT مقابل تسميته الحقيقية
    if sym == "BTCUSDT":
        alt = from_engine(LC.run(df, "BNBUSDT"), sym)
        out["identity_label_swap"] = key_of(alt) == key_of(out["open_full"])
        # وعلى عملة خارج القائمة: المحرك يرجع فراغًا بالاسم الحقيقي (توثيق الحدّ)
    if sym not in ALLOWED:
        out["engine_with_real_label_returns"] = len(LC.run(df, sym))
    out["seconds"] = round(time.time() - t0, 1)
    del df, cut, h4, daily
    gc.collect()
    (RECS / f"{pass_tag}_{sym}.json").write_text(json.dumps(out, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"  {sym}: open_cut={len(out['open_cut'])} open_full={len(out['open_full'])} "
          f"bear_cut={len(out['bear_cut'])} bear_full={len(out['bear_full'])} "
          f"identity={out['identity_copy_vs_engine']} ({out['seconds']}s)", flush=True)
    return out


def main(argv: list[str]) -> int:
    pass_tag = argv[1] if len(argv) > 1 else "pass1"
    syms = argv[2].split(",") if len(argv) > 2 else list(ALL_FILES)
    print(f"══ تمريرة {pass_tag} · {len(syms)} ملف ══", flush=True)
    for sym in syms:
        run_symbol(sym, pass_tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
