#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0067 — بوابة المطابقة: محرك المختبر (M0، بلا حد زمني) = ملفات L0064 (sha256) على 16 عملة، بالتشغيل المقطوع
وبعرض النافذة (تشغيل متصل + إغلاق عند نهاية النافذة). ثم يبني كاش السجلات لكل (M, T) × عملة على المدى الكامل.
    python3 history/hyp_lab/run_l0067_match.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab" / "l0067_replication_b"))  # التكرار المستقل (ب) يسبق ملفات التنفيذ الأول
import cycle_engine67 as CE  # noqa: E402
import run_l0061_measure as M  # noqa: E402  (FR, save_trades, rows_for نمط)

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0067" / "replication_b"
OUT.mkdir(parents=True, exist_ok=True)
OUT64 = ROOT / "history" / "research" / "hyp_lab_out" / "L0064"
FRAMES = pathlib.Path.home() / ".cache" / "l0061_h4"
DAILY = pathlib.Path.home() / ".cache" / "l0061_1d"
RECS = pathlib.Path.home() / ".cache" / "l0067b_records"
RECS.mkdir(parents=True, exist_ok=True)
FULL16 = ("ATOMUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "FILUSDT", "GRAMUSDT", "HNTUSDT", "IMXUSDT", "LINKUSDT",
          "PEPEUSDT", "RENDERUSDT", "SHIBUSDT", "SOLUSDT", "VETUSDT", "XLMUSDT")
CUT = pd.Timestamp("2024-01-01", tz="UTC")
COST = 0.00115
MARKETS = ("M0", "M1", "M2")
TLIMITS = (None, 90, 180, 365)


def frames(sym: str, end: pd.Timestamp | None = None):
    h4 = pd.read_parquet(FRAMES / f"{sym}_4h.parquet")
    d1 = pd.read_parquet(DAILY / f"{sym}_1d.parquet")
    if end is not None:
        h4 = h4[h4.index < end]
        d1 = d1[d1.index < end]
    return h4, d1


def window_view(rows: list[dict], h4: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, cost: float) -> list[dict]:
    """صفقات النافذة: الدخول داخل [start, end)؛ ما بقي مفتوحًا عند النهاية يُغلق على آخر إغلاق قبلها (نهاية-العينة)."""
    sub = h4[h4.index < end]
    if not len(sub):
        return []
    last_i = len(sub) - 1
    last_ts = sub.index[-1]
    last_close = float(sub["close"].iloc[-1])
    out = []
    for r in rows:
        et = pd.Timestamp(r["entry_time"])
        if not (start <= et < end):
            continue
        q = dict(r)
        if pd.Timestamp(r["exit_time"]) >= end:
            q["exit_time"] = last_ts.isoformat(); q["exit_px"] = last_close; q["exit_bar"] = last_i
            q["bars_held"] = last_i - int(r["entry_bar"]); q["reason"] = "نهاية-العينة"
        g = q["exit_px"] / q["entry_px"]
        q["pnl_usd"] = float(((g * (1.0 - cost) - (1.0 + cost)) / (1.0 + cost)) * q["notional_usd"])
        out.append(q)
    return out


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> int:
    t0 = time.time()
    btc_h4, btc_d1 = frames("BTCUSDT")
    btc_ok = CE.btc_market_ok(btc_d1)
    report = {"per_symbol": {}, "files": {}, "btc_market_days": {m: int(btc_ok[m].sum()) for m in ("M1", "M2")}, "btc_days": int(len(btc_d1))}
    ok_all = True
    rows_sel_cut, rows_sel_view, rows_jud, rows_full = [], [], [], []
    for sym in FULL16:
        h4, d1 = frames(sym)
        ctx = CE.CoinContext(sym, h4, d1, btc_ok)
        cache = {"symbol": sym}
        for m in MARKETS:
            for tl in TLIMITS:
                r = CE.run(ctx, m, tl)
                CE.price_pnl(r, COST)
                cache[f"{m}_{'none' if tl is None else tl}"] = r
        (RECS / f"{sym}.json").write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        base = cache["M0_none"]
        # التشغيل المقطوع عند 2024-01-01 (كما فعلت L0061–L0064)
        h4c, d1c = frames(sym, CUT)
        ctx_c = CE.CoinContext(sym, h4c, d1c, btc_ok)
        cut_rows = CE.run(ctx_c, "M0", None)
        CE.price_pnl(cut_rows, COST)
        view_rows = window_view(base, h4, pd.Timestamp("2021-09-01", tz="UTC"), CUT, COST)
        keyf = lambda rows: sorted((r["entry_time"], r["exit_time"], r["reason"], r["stage"], round(r["entry_px"], 8), round(r["exit_px"], 8), round(r["pnl_usd"], 6)) for r in rows)
        same = keyf(cut_rows) == keyf(view_rows)
        report["per_symbol"][sym] = {"n_full": len(base), "n_cut": len(cut_rows), "n_view": len(view_rows), "cut_equals_view": same,
                                     "n_by_version": {k: len(v) for k, v in cache.items() if k != "symbol"}}
        ok_all &= same
        rows_sel_cut.extend(cut_rows); rows_sel_view.extend(view_rows)
        rows_jud.extend([r for r in base if pd.Timestamp(r["entry_time"]) >= CUT]); rows_full.extend(base)
        print(f"  {sym}: full={len(base)} cut={len(cut_rows)} view={len(view_rows)} cut=view:{same} ({time.time()-t0:.0f}s)", flush=True)
    M.OUT = OUT
    for name, rows, ref in (("SEL_cut", rows_sel_cut, "trades_strategy_FULL16_SEL.csv"), ("SEL_view", rows_sel_view, "trades_strategy_FULL16_SEL.csv"),
                            ("JUD", rows_jud, "trades_strategy_FULL16_JUD.csv"), ("FULL", rows_full, "trades_strategy_FULL16_FULL.csv")):
        p = M.save_trades(f"match_M0_{name}", rows)
        h_new, h_old = sha(p), sha(OUT64 / ref)
        report["files"][name] = {"sha_engine67": h_new, "sha_L0064": h_old, "match": h_new == h_old, "rows": len(rows)}
        ok_all &= (h_new == h_old)
        print(f"  {name}: {h_new} vs L0064 {h_old} → {'✅' if h_new == h_old else '❌'} ({len(rows)} صفًّا)", flush=True)
    report["MATCH_GATE_PASSED"] = bool(ok_all)
    report["engine_sha256"] = sha(ROOT / "history" / "hyp_lab" / "cycle_engine67.py")
    (OUT / "match_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"بوابة المطابقة: {'✅ نجحت' if ok_all else '❌ فشلت'} · BTC أيام M1={report['btc_market_days']['M1']} M2={report['btc_market_days']['M2']} من {report['btc_days']}", flush=True)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
