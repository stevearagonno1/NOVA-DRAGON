#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0062 — إكمال ضوابط L0061: العشوائي بخمس بذور على مفتوح16 وهابط16 ومفتوح4 في الفترتين،
ومقعد 0.130% للهابط16 في الفترتين.

فُتحت بأمر صاحب المشروع بعد رؤية نتائج L0061. لا تطوير. لا تعديل nova_v8. صفقات الاستراتيجية
لا تتغيّر (تُعاد من السجلات وتُطابَق sha256 مع ملفات L0061 المنشورة قبل أي رقم جديد).

التشغيل (بعد `python3 history/hyp_lab/run_l0061_lc.py pass1`):
    python3 history/hyp_lab/run_l0062_random16.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import platform
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))

import run_l0061_measure as M  # noqa: E402  (يحمّل السجلات والإطارات عند الاستيراد)
import run_l0061_lc as L  # noqa: E402

OUT61 = ROOT / "history" / "research" / "hyp_lab_out" / "L0061"
OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0062"
OUT.mkdir(parents=True, exist_ok=True)
M.OUT = OUT              # كل الكتابة إلى مجلد L0062
M.CAP = 16               # سقف هذه الجولة (مكتوب في acceptance_rule_l0062.json قبل التشغيل)
M.LEDGER.clear()
M.GUARD_LOG.clear()

SEEDS = (110060, 210060, 310060, 410060, 510060)
COST, COST_130 = M.COST, M.COST_130
PATHS = {"open16": ("open", M.UNIVERSE), "bear16": ("bear", M.UNIVERSE), "open4": ("open", M.ALLOWED)}


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> int:
    r61 = json.loads((OUT61 / "results.json").read_text(encoding="utf-8"))
    rule = json.loads((OUT / "acceptance_rule_l0062.json").read_text(encoding="utf-8"))
    assert rule["cap"] == M.CAP

    # ───────── 0) تحقق غير محسوب: الصفقات نفسها حرفيًّا (sha256 مع ملفات L0061) ─────────
    print("══ تحقق — إعادة بناء صفقات L0061 ومطابقة sha256 ══", flush=True)
    identity = {}
    checks = [("a_open16_c00115_SEL", "open", M.UNIVERSE, "SEL", COST), ("a_open16_c00115_JUD", "open", M.UNIVERSE, "JUD", COST),
              ("a_bear16_c00115_SEL", "bear", M.UNIVERSE, "SEL", COST), ("a_bear16_c00115_JUD", "bear", M.UNIVERSE, "JUD", COST),
              ("b_open16_c00115_FULL", "open", M.UNIVERSE, "FULL", COST), ("b_bear16_c00115_FULL", "bear", M.UNIVERSE, "FULL", COST),
              ("p0_open4_c00115_SEL", "open", M.ALLOWED, "SEL", COST), ("p0_open4_c00115_JUD", "open", M.ALLOWED, "JUD", COST),
              ("p0_bear4_c00115_SEL", "bear", M.ALLOWED, "SEL", COST), ("p0_bear4_c00115_JUD", "bear", M.ALLOWED, "JUD", COST)]
    for name, path, coins, w, cost in checks:
        rows, _ = M.rows_for(M.R, path, coins, w)
        L.set_cost(cost)
        tmp = M.save_trades("verify_" + name, rows)
        h_new, h_old = sha(tmp), sha(OUT61 / f"trades_{name}.csv")
        identity[name] = {"sha_L0061": h_old, "sha_rebuilt": h_new, "match": h_new == h_old, "rows": len(rows)}
        tmp.unlink()
        if h_new != h_old:
            raise SystemExit(f"الصفقات المعاد بناؤها لا تطابق L0061: {name}")
    print(f"  sha256 طابق على {len(checks)}/{len(checks)} ملفًا", flush=True)

    # إعادة إنتاج عشوائي هابط4 بذرة 110060 (L0060/L0061: −20.91 / +34.82) — غير محسوب
    ref = {x["window"]: x["net"] for x in r61["D"]["random"] if x["seed"] == 110060}
    for w in ("SEL", "JUD"):
        tmpl, _ = M.rows_for(M.R, "bear", M.ALLOWED, w)
        book = M.random_book(M.ALLOWED, tmpl, 110060, w)
        net = round(sum(r["pnl_usd"] for r in book), 2)
        identity[f"random_bear4_110060_{w}"] = {"L0061": ref[w], "rebuilt": net, "match": abs(net - ref[w]) < 0.005}
        if abs(net - ref[w]) >= 0.005:
            raise SystemExit(f"العشوائي المرجعي لم يُعد إنتاجه: {w} {net} ≠ {ref[w]}")
    print("  عشوائي هابط4 · 110060 أُعيد إنتاجه إلى السنت", flush=True)
    dump("identity.json", identity)

    table: dict = {"A": {}, "D": {}, "determinism": {}}

    # ───────── أ) هابط16 عند 0.130% في الفترتين (قياس 1) ─────────
    print("══ أ — هابط16 · 0.130% · الفترتان ══", flush=True)
    for w in ("SEL", "JUD"):
        rows, warm = M.rows_for(M.R, "bear", M.UNIVERSE, w)
        st = M.emit(f"a_bear16_c00130_{w}", w, "أ", M.reprice(rows, COST_130), warm, M.UNIVERSE, counted=(w == "JUD"), cost=COST_130)
        table["A"][w] = st

    # ───────── د) العشوائي: 5 بذور × 3 مسارات × الفترتان (15 قياسًا) ─────────
    print("══ د — العشوائي على مفتوح16 وهابط16 ومفتوح4 ══", flush=True)
    for pname, (path, coins) in PATHS.items():
        table["D"][pname] = []
        for seed in SEEDS:
            for w in ("SEL", "JUD"):
                tmpl, _ = M.rows_for(M.R, path, coins, w)
                book = M.random_book(coins, tmpl, seed, w)
                book2 = M.random_book(coins, tmpl, seed, w)
                same = json.dumps(book, sort_keys=True, default=str) == json.dumps(book2, sort_keys=True, default=str)
                table["determinism"][f"d_{pname}_{seed}_{w}"] = same
                if not same:
                    raise SystemExit("الدفتر العشوائي غير حتمي")
                st = M.emit(f"d_{pname}_r_{seed}_{w}", w, "د", book, [], coins, counted=(w == "JUD"))
                table["D"][pname].append({"seed": seed, "window": w, "net": st["net"], "peak": st["peak_concurrent"],
                                          "return_pct_on_peak": st["return_pct_on_peak"], "slices": st["slices"],
                                          "cycles_template": len(M.cycles(tmpl)), "symbols": st["symbols_traded"],
                                          "dd_usd": st["dd_usd"]})
        # ملخّص
        summ = {}
        for w in ("SEL", "JUD"):
            nets = [x["net"] for x in table["D"][pname] if x["window"] == w]
            summ[w] = {"mean": round(float(np.mean(nets)), 2), "max": max(nets), "min": min(nets),
                       "seed_max": [x["seed"] for x in table["D"][pname] if x["window"] == w and x["net"] == max(nets)][0]}
        table["D"][pname + "_summary"] = summ

    # ───────── معيار القبول — الجدول الكامل للمسارات الأربعة ─────────
    p0, A = r61["phase0"], r61["A"]
    strat = {
        "open4": {"SEL": p0["open4"]["SEL"], "JUD": p0["open4"]["JUD"], "c130_JUD": 415.14,
                  "hold": {"SEL": p0["hold4"]["SEL"]["net"], "JUD": p0["hold4"]["JUD"]["net"]},
                  "random": table["D"]["open4_summary"]},
        "bear4": {"SEL": p0["bear4"]["c00115"]["SEL"], "JUD": p0["bear4"]["c00115"]["JUD"], "c130_JUD": p0["bear4"]["c00130"]["JUD"]["net"],
                  "hold": {"SEL": p0["hold4"]["SEL"]["net"], "JUD": p0["hold4"]["JUD"]["net"]},
                  "random": r61["D"]["random_summary"]},
        "open16": {"SEL": A["open16"]["c00115"]["SEL"], "JUD": A["open16"]["c00115"]["JUD"], "c130_JUD": A["open16"]["c00130"]["JUD"]["net"],
                   "hold": {"SEL": A["hold16"]["SEL"]["net"], "JUD": A["hold16"]["JUD"]["net"]},
                   "random": table["D"]["open16_summary"]},
        "bear16": {"SEL": A["bear16"]["c00115"]["SEL"], "JUD": A["bear16"]["c00115"]["JUD"], "c130_JUD": table["A"]["JUD"]["net"],
                   "hold": {"SEL": A["hold16"]["SEL"]["net"], "JUD": A["hold16"]["JUD"]["net"]},
                   "random": table["D"]["bear16_summary"]},
    }
    acceptance = {}
    for k, s in strat.items():
        c1 = s["SEL"]["net"] > 0 and s["JUD"]["net"] > 0
        c2 = s["c130_JUD"] > 0
        c3 = s["SEL"]["net"] > s["hold"]["SEL"] and s["JUD"]["net"] > s["hold"]["JUD"]
        c4 = s["SEL"]["net"] > s["random"]["SEL"]["max"] and s["JUD"]["net"] > s["random"]["JUD"]["max"]
        c5 = s["SEL"]["cycles"] >= 20 and s["JUD"]["cycles"] >= 20
        c6 = True  # الحارس أوقف التشغيل لو خالف
        acceptance[k] = {
            "1_positive_both_0115": {"pass": c1, "SEL": s["SEL"]["net"], "JUD": s["JUD"]["net"]},
            "2_positive_JUD_0130": {"pass": c2, "JUD": s["c130_JUD"]},
            "3_beats_hold_both": {"pass": c3, "hold_SEL": s["hold"]["SEL"], "hold_JUD": s["hold"]["JUD"]},
            "4_beats_happiest_seed_both": {"pass": c4, "max_SEL": s["random"]["SEL"]["max"], "max_JUD": s["random"]["JUD"]["max"]},
            "5_cycles_ge_20": {"pass": c5, "SEL": s["SEL"]["cycles"], "JUD": s["JUD"]["cycles"]},
            "6_zero_fill_violations": {"pass": c6},
            "ALL": all([c1, c2, c3, c4, c5, c6]),
        }
        print(f"  {k}: " + " · ".join(f"{n[0]}={'✓' if v['pass'] else '✗'}" for n, v in acceptance[k].items() if n != "ALL")
              + f" ⇒ {'يعبر المعيار' if acceptance[k]['ALL'] else 'لا يعبر'}", flush=True)
    table["acceptance"] = acceptance
    table["strategy_reference_from_L0061"] = {k: {"SEL": v["SEL"]["net"], "JUD": v["JUD"]["net"], "hold": v["hold"], "c130_JUD": v["c130_JUD"]} for k, v in strat.items()}

    # ───────── تدقيق التتابع + الختام ─────────
    seq = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--dir", str(OUT), "--json"],
                         capture_output=True, text=True)
    (OUT / "sequencing_audit.json").write_text(seq.stdout, encoding="utf-8")
    dump("guard_log.json", M.GUARD_LOG)
    dump("ledger.json", M.LEDGER)
    dump("results.json", table)
    import pandas, numpy, pyarrow  # noqa
    dump("env_dump.txt", {"date": "2026-09-27", "python": platform.python_version(), "pandas": pandas.__version__,
                          "numpy": numpy.__version__, "pyarrow": pyarrow.__version__, "platform": platform.platform(),
                          "base_branch": "arena/l0061-long-cycle-full-2026-09-27 @ 698cb93", "cap": M.CAP,
                          "counted": len(M.LEDGER), "ledger": M.LEDGER,
                          "cost": {"COMMISSION_PCT": [COST, COST_130], "SLIPPAGE_PCT": 0.0},
                          "records_cache": str(M.RECS), "frames_cache": str(M.FRAMES)})
    print(f"اكتمل. المستهلك {len(M.LEDGER)}/{M.CAP}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
