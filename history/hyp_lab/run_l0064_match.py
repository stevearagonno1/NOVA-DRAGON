#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0064 — بوابة المطابقة قبل أي قياس: المحرك بالعلم NOVA_LC_V3=1 يجب أن يعيد صفقات مسار L0062/L0063
(الهابط على 16 عملة) حرفيًّا، والمحرك بالعلم مطفأً يجب أن يبقى النسخة القديمة حرفيًّا (L0060/L0061).

المخرجات: ~/.cache/l0064_records/{sym}.json (سجلات المحرك)، وملفات SEL/JUD/FULL في hyp_lab_out/L0064،
و match_report.json (المطابقة + فحص تسرّب المستقبل). أي اختلاف ⇒ رمز خروج 1 ولا يُقرأ أي ربح.

التشغيل (بعد `run_l0061_lc.py pass1` لبناء سجلات نسخة المختبر والإطارات):
    python3 history/hyp_lab/run_l0064_match.py
"""
from __future__ import annotations

import gc
import hashlib
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

import run_l0061_lc as L  # noqa: E402
import nova_v8.long_cycle as LC  # noqa: E402

CM = L.CM
OUT61 = ROOT / "history" / "research" / "hyp_lab_out" / "L0061"
OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0064"
OUT.mkdir(parents=True, exist_ok=True)
RECS64 = pathlib.Path.home() / ".cache" / "l0064_records"
RECS64.mkdir(parents=True, exist_ok=True)
CUT = pd.Timestamp(L.CUT, tz="UTC")
TRUNC_DATES = ("2022-09-01", "2023-06-01", "2025-03-01")
TRUNC_COINS = ("BTCUSDT", "ETHUSDT", "ATOMUSDT", "SHIBUSDT")


def v3(on: bool) -> None:
    os.environ["NOVA_LC_V3"] = "1" if on else "0"


def engine(df: pd.DataFrame, sym: str) -> list[dict]:
    return L.from_engine(LC.run(df, sym), sym)


def entry_keys(rows):
    return sorted((r["entry_time"], int(r["stage"]), round(r["entry_ref_px"], 8), round(r["notional_usd"], 4)) for r in rows)


def main() -> int:
    L.set_cost(L.COST)
    report = {"per_symbol": {}, "leakage": {}, "legacy": {}, "files": {}}
    ok_all = True
    for sym in L.ALL_FILES:
        t0 = time.time()
        lab = json.loads((L.RECS / f"pass1_{sym}.json").read_text(encoding="utf-8"))
        df = CM.load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), start=L.WARM, end=L.JUD_E)
        cut = df[df.index < CUT]
        entry = {"in_v3_universe": sym in LC.LC_V3_UNIVERSE, "in_legacy": sym in LC.LC_LEGACY_UNIVERSE}
        # ── المحرك V3 ──
        v3(True)
        full = engine(df, sym)
        part = engine(cut, sym) if len(cut) else []
        if sym in LC.LC_V3_UNIVERSE:
            entry["v3_full_matches_lab_bear_full"] = L.key_of(full) == L.key_of(lab["bear_full"])
            entry["v3_cut_matches_lab_bear_cut"] = L.key_of(part) == L.key_of(lab["bear_cut"])
            entry["v3_full_exact_dicts"] = json.dumps(full, sort_keys=True) == json.dumps(lab["bear_full"], sort_keys=True)
            entry["n_full"], entry["n_cut"] = len(full), len(part)
            ok_all &= entry["v3_full_matches_lab_bear_full"] and entry["v3_cut_matches_lab_bear_cut"]
        else:
            entry["v3_returns_empty"] = (len(full) == 0)
            ok_all &= entry["v3_returns_empty"]
        # ── المحرك القديم (العلم مطفأ) ──
        v3(False)
        lf = engine(df, sym)
        lc = engine(cut, sym) if len(cut) else []
        if sym in LC.LC_LEGACY_UNIVERSE:
            entry["legacy_full_matches_lab_open_full"] = L.key_of(lf) == L.key_of(lab["open_full"])
            entry["legacy_cut_matches_lab_open_cut"] = L.key_of(lc) == L.key_of(lab["open_cut"])
            ok_all &= entry["legacy_full_matches_lab_open_full"] and entry["legacy_cut_matches_lab_open_cut"]
        else:
            entry["legacy_returns_empty"] = (len(lf) == 0)
            ok_all &= entry["legacy_returns_empty"]
        # ── تسرّب المستقبل (عيّنة عملات) ──
        if sym in TRUNC_COINS:
            v3(True)
            daily_full = LC._resample(df, "1D")
            lab_full = LC._regime_labels(daily_full)
            leak = {}
            for T in TRUNC_DATES:
                Tt = pd.Timestamp(T, tz="UTC")
                tr = df[df.index < Tt]
                lab_tr = LC._regime_labels(LC._resample(tr, "1D"))
                common = lab_tr.index.intersection(lab_full.index)
                labels_equal = bool((lab_tr.loc[common].fillna("∅") == lab_full.loc[common].fillna("∅")).all())
                rows_tr = engine(tr, sym)
                before = [r for r in full if pd.Timestamp(r["entry_time"]) < Tt]
                same_entries = entry_keys(rows_tr) == entry_keys(before)
                closed_before = [r for r in before if pd.Timestamp(r["exit_time"]) < Tt]
                tr_by_key = {(r["entry_time"], int(r["stage"])): r for r in rows_tr}
                same_exits = all(
                    (k := (r["entry_time"], int(r["stage"]))) in tr_by_key
                    and tr_by_key[k]["exit_time"] == r["exit_time"] and tr_by_key[k]["reason"] == r["reason"]
                    and abs(tr_by_key[k]["exit_px"] - r["exit_px"]) < 1e-9
                    for r in closed_before)
                open_at_T = [r for r in before if pd.Timestamp(r["exit_time"]) >= Tt]
                open_ok = all(tr_by_key.get((r["entry_time"], int(r["stage"])), {}).get("reason") == "نهاية-العينة" for r in open_at_T)
                leak[T] = {"labels_equal_on_common_days": labels_equal, "same_entries_before_T": same_entries,
                           "same_exits_for_trades_closed_before_T": same_exits, "open_at_T_closed_as_end_of_sample": open_ok,
                           "n_before_T": len(before), "n_open_at_T": len(open_at_T)}
                ok_all &= labels_equal and same_entries and same_exits and open_ok
            # (ج) اضطراب إغلاق يوم D لا يغيّر وسم اليوم D (يغيّر D+1 فقط إن غيّر شيئًا)
            D = daily_full.index[len(daily_full) // 2]
            pert = daily_full.copy()
            pert.loc[D, "close"] = pert.loc[D, "close"] * 0.5
            lab_p = LC._regime_labels(pert)
            leak["perturb_day_D_close"] = {"day": str(D.date()), "label_at_D_unchanged": bool(lab_p.loc[D] == lab_full.loc[D]) or (pd.isna(lab_p.loc[D]) and pd.isna(lab_full.loc[D])),
                                           "labels_before_D_unchanged": bool((lab_p.loc[:D].fillna("∅") == lab_full.loc[:D].fillna("∅")).all()),
                                           "first_day_changed": next((str(d.date()) for d in lab_full.index if str(lab_p.loc[d]) != str(lab_full.loc[d])), None)}
            ok_all &= leak["perturb_day_D_close"]["label_at_D_unchanged"] and leak["perturb_day_D_close"]["labels_before_D_unchanged"]
            report["leakage"][sym] = leak
        # ── حفظ سجلات المحرك ──
        (RECS64 / f"{sym}.json").write_text(json.dumps({"symbol": sym, "bear_cut": part, "bear_full": full,
                                                         "open_cut": lc, "open_full": lf}, ensure_ascii=False), encoding="utf-8")
        entry["seconds"] = round(time.time() - t0, 1)
        report["per_symbol"][sym] = entry
        print(f"  {sym}: " + " · ".join(f"{k}={v}" for k, v in entry.items() if k not in ("seconds",)) + f" ({entry['seconds']}s)", flush=True)
        del df, cut
        gc.collect()

    # ── ملفات SEL/JUD/FULL من سجلات المحرك مقابل L0061 (sha256) ──
    import run_l0061_measure as M  # noqa: E402  (يحمّل الإطارات؛ السجلات القديمة لا تُستعمل هنا)
    M.OUT = OUT
    R64 = {sym: json.loads((RECS64 / f"{sym}.json").read_text(encoding="utf-8")) for sym in L.UNIVERSE}
    L.set_cost(L.COST)
    for name, w in (("a_bear16_c00115_SEL", "SEL"), ("a_bear16_c00115_JUD", "JUD"), ("b_bear16_c00115_FULL", "FULL")):
        rows, _ = M.rows_for(R64, "bear", L.UNIVERSE, w)
        p = M.save_trades(f"engine_v3_{w}", rows)
        h_new = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        h_old = hashlib.sha256((OUT61 / f"trades_{name}.csv").read_bytes()).hexdigest()[:16]
        report["files"][w] = {"engine_v3_file": p.name, "sha_engine": h_new, "sha_L0061": h_old, "match": h_new == h_old, "rows": len(rows)}
        ok_all &= (h_new == h_old)
        print(f"  {w}: sha {h_new} vs L0061 {h_old} → {'✅' if h_new == h_old else '❌'} ({len(rows)} صفًّا)", flush=True)
    # القديم على الأربع بالعلم مطفأً
    for w in ("SEL", "JUD", "FULL"):
        rows, _ = M.rows_for(R64, "open", L.ALLOWED, w)
        report["legacy"][w] = {"net": round(sum(r["pnl_usd"] for r in rows), 2), "slices": len(rows), "cycles": len(M.cycles(rows))}
    ref = {"SEL": -12.59, "JUD": 417.35, "FULL": 404.76}
    report["legacy"]["matches_L0060_L0061"] = all(abs(report["legacy"][w]["net"] - ref[w]) < 0.01 for w in ref)
    ok_all &= report["legacy"]["matches_L0060_L0061"]
    report["long_cycle_py_sha256"] = hashlib.sha256((ROOT / "nova_v8" / "long_cycle.py").read_bytes()).hexdigest()[:16]
    report["MATCH_GATE_PASSED"] = bool(ok_all)
    (OUT / "match_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"بوابة المطابقة: {'✅ نجحت' if ok_all else '❌ فشلت'} · القديم: {report['legacy']}", flush=True)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
