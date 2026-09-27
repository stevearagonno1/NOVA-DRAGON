#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0063 — المقارنة العادلة لدورة التراكم (نسخة الهابط على 16 عملة، فرضية بحثية فقط).

≥100 دفتر عشوائي مستقل في كل نافذة (هنا 200)، بنفس العملات والفترتين وعدد الدورات ومدد الاحتفاظ
وأحجام الدورات والكلفة، ويُسوَّى كل دفتر إلى نفس ذروة رأس المال المتزامن التي تعرّضت لها الاستراتيجية
في النافذة نفسها. تصميمان: A (توزيع المدد والأحجام الفعلي — الأساسي) و B (مسطرة L0060–L0062 — حساسية).
قاعدة القبول مكتوبة قبل التشغيل في acceptance_rule_l0063.json.

التشغيل (بعد `python3 history/hyp_lab/run_l0061_lc.py pass1`):
    python3 history/hyp_lab/run_l0063_random_fair.py pass1
    python3 history/hyp_lab/run_l0063_random_fair.py pass2      # إعادة مستقلة للحتمية
"""
from __future__ import annotations

import hashlib
import io
import json
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

import run_l0061_measure as M  # noqa: E402  (يحمّل السجلات والإطارات)
import run_l0061_lc as L  # noqa: E402

OUT61 = ROOT / "history" / "research" / "hyp_lab_out" / "L0061"
OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0063"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "samples").mkdir(exist_ok=True)

COINS = M.UNIVERSE
WINDOWS = ("SEL", "JUD")
WCODE = {"SEL": 1, "JUD": 2}
DCODE = {"A": 1, "B": 2}
N_BOOKS = 200
COST, COST_130 = 0.00115, 0.00130
BAR = pd.Timedelta(hours=4)
MAX_TRIES = 200


def pnl_vec(entry, exit_, notional, cost):
    """net_fraction من nova_v8.execution (side=1, slip=0) متّجهيًّا: ((exit/entry)(1−c) − (1+c)) / (1+c) × notional."""
    entry = np.asarray(entry, dtype=float)
    exit_ = np.asarray(exit_, dtype=float)
    notional = np.asarray(notional, dtype=float)
    gross = exit_ / entry
    return ((gross * (1.0 - cost) - (1.0 + cost)) / (1.0 + cost)) * notional


def ts(x) -> pd.Timestamp:
    return M.ts(x)


# ───────────────────────── شبكة النافذة وإغلاقات كل عملة عليها ─────────────────────────
class Window:
    def __init__(self, name: str):
        self.name = name
        self.s, self.e = ts(M.WIN[name][0]), ts(M.WIN[name][1])
        self.grid = pd.date_range(self.s, self.e, freq="4h", tz="UTC", inclusive="left")
        self.n = len(self.grid)
        self.close = {}
        self.frames = {}
        for sym in COINS:
            fr = M.FR[sym]
            w = fr[(fr.index >= self.s) & (fr.index < self.e)]
            self.frames[sym] = w
            self.close[sym] = w["close"].reindex(self.grid).ffill().to_numpy(dtype=float)

    def gi(self, t) -> int:
        k = (ts(t) - self.s) / BAR
        assert float(k).is_integer(), f"طابع زمني خارج الشبكة: {t}"
        return int(k)


WIN: dict[str, Window] = {}


# ───────────────────────── تقييم دفتر (صفوف) ─────────────────────────
def evaluate(rows: list[dict], w: Window, scale_to: float | None) -> dict:
    """يقيس الذروة، ويُسوّي إلى scale_to إن طُلب، ويحسب الصافي عند الكلفتين، والهبوط، وأطول فترة تحت القمة."""
    if not rows:
        return {"empty": True}
    sym = np.array([r["symbol"] for r in rows])
    entry = np.array([float(r["entry_px"]) for r in rows])
    exit_ = np.array([float(r["exit_px"]) for r in rows])
    notional = np.array([float(r["notional_usd"]) for r in rows])
    gi0 = np.array([w.gi(r["entry_time"]) for r in rows])
    gi1 = np.array([w.gi(r["exit_time"]) for r in rows])
    # ذروة رأس المال المتزامن (الخروج قبل الدخول عند الطابع نفسه ⇒ الفترة [gi0, gi1))
    dep = np.zeros(w.n + 1)
    np.add.at(dep, gi0, notional)
    np.add.at(dep, gi1, -notional)
    dep = np.cumsum(dep)[: w.n]
    peak = float(dep.max())
    f = 1.0 if scale_to is None else scale_to / peak
    p115 = pnl_vec(entry, exit_, notional, COST) * f
    p130 = pnl_vec(entry, exit_, notional, COST_130) * f
    # منحنى القيمة المعلَّمة عند 0.115% (محقق + غير محقق على إغلاق 4س)
    eq = np.zeros(w.n)
    for k in range(len(rows)):
        a, b = int(gi0[k]), int(gi1[k])
        if b > a:
            eq[a:b] += pnl_vec(entry[k], w.close[sym[k]][a:b], notional[k] * f, COST)
        eq[b:] += p115[k]
    run_max = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    dd = eq - run_max
    under = dd < -1e-9
    longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    per_coin = {}
    for s_ in np.unique(sym):
        per_coin[str(s_)] = round(float(p115[sym == s_].sum()), 2)
    return {
        "empty": False, "peak_raw": round(peak, 2), "scale": round(f, 6), "peak_scaled": round(peak * f, 2),
        "net115": round(float(p115.sum()), 2), "net130": round(float(p130.sum()), 2),
        "net115_raw": round(float(p115.sum() / f), 2),
        "dd_usd": round(float(dd.min()), 2), "peak_equity": round(float(run_max.max()), 2),
        "longest_underwater_days": round(longest * 4 / 24, 1),
        "max_cycle_notional_scaled": round(float((notional * f).max()), 2),
        "per_coin": per_coin, "slices": len(rows),
        "_p115": p115, "_p130": p130,
    }


# ───────────────────────── قوالب الدورات من الاستراتيجية ─────────────────────────
def cycle_table(rows: list[dict]) -> dict[str, list[tuple[int, float]]]:
    out: dict[str, list[tuple[int, float]]] = {}
    for g in M.cycles(rows):
        sym = g[0]["symbol"]
        t0 = min(ts(r["entry_time"]) for r in g)
        t1 = max(ts(r["exit_time"]) for r in g)
        d = int((t1 - t0) / BAR)
        n = float(sum(float(r["notional_usd"]) for r in g))
        out.setdefault(sym, []).append((max(d, 1), n))
    return out


# ───────────────────────── توليد دفتر عشوائي ─────────────────────────
def make_book(design: str, w: Window, table: dict, book_index: int) -> tuple[list[dict], int]:
    rows, failures = [], 0
    for sym in COINS:
        pairs = table.get(sym, [])
        n = len(pairs)
        if n == 0:
            continue
        fr = w.frames[sym]
        ln = len(fr)
        if ln < 3:
            continue
        seed = np.random.SeedSequence([63, WCODE[w.name], DCODE[design], int(book_index), zlib.crc32(sym.encode()) & 0xFFFFFFFF])
        rng = np.random.default_rng(seed)
        if design == "B":
            d_med = max(int(np.median([d for d, _ in pairs])), 1)
            n_mean = float(np.mean([x for _, x in pairs]))
            pairs = [(d_med, n_mean)] * n
        taken: list[tuple[int, int]] = []
        opens = fr["open"].to_numpy(dtype=float)
        closes = fr["close"].to_numpy(dtype=float)
        idx = fr.index
        for _ in range(n):
            placed = False
            for _try in range(MAX_TRIES):
                d, notional = pairs[int(rng.integers(0, len(pairs)))] if design == "A" else pairs[0]
                hi = ln - 2 - d
                if hi < 0:
                    continue
                i = int(rng.integers(0, hi + 1))
                a, b = i + 1, i + 1 + d
                if all(a > tb or b < ta for ta, tb in taken):
                    taken.append((a, b))
                    rows.append({"symbol": sym, "entry_time": idx[a].isoformat(), "exit_time": idx[b].isoformat(),
                                 "entry_ref_px": float(opens[a]), "entry_px": float(opens[a]), "exit_px": float(closes[b]),
                                 "notional_usd": float(notional), "reason": "عشوائي", "stage": 0, "bars_held": int(d),
                                 "entry_bar": a, "exit_bar": b})
                    placed = True
                    break
            if not placed:
                failures += 1
    return rows, failures


def overlap_violations(rows: list[dict]) -> int:
    v = 0
    by: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]] = {}
    for r in rows:
        by.setdefault(r["symbol"], []).append((ts(r["entry_time"]), ts(r["exit_time"])))
    for iv in by.values():
        iv.sort()
        for k in range(1, len(iv)):
            if iv[k][0] < iv[k - 1][1]:
                v += 1
    return v


def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def guard(path: pathlib.Path) -> str:
    st = subprocess.run([sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"), "--trades", str(path),
                         "--frames", str(M.FRAMES), "--cost", "0", "--bar-tag", "4h"], capture_output=True, text=True)
    line = next((l.strip() for l in st.stdout.splitlines() if "مخالفات" in l and "صفقات=" in l), st.stdout[-300:])
    ok = st.returncode == 0 and "مخالفات الدخول=0" in st.stdout and "مخالفات الخروج=0" in st.stdout and "تُخطّي=0" in st.stdout
    if not ok:
        raise SystemExit(f"حارس التعبئة فشل على {path.name}:\n{st.stdout[-800:]}\n{st.stderr[-400:]}")
    return line


def books_to_frame(all_rows: list[tuple[int, dict, float, float, float]]) -> pd.DataFrame:
    rec = []
    for b, r, f, p115, p130 in all_rows:
        rec.append({"book": b, "symbol": r["symbol"], "entry_time": r["entry_time"], "exit_time": r["exit_time"],
                    "entry": r["entry_px"], "exit": r["exit_px"], "notional": r["notional_usd"],
                    "notional_scaled": round(r["notional_usd"] * f, 4), "pnl115_scaled": round(p115, 4),
                    "pnl130_scaled": round(p130, 4), "pnl": round(p115, 4), "reason": r["reason"], "stage": 0,
                    "bars_held": r["bars_held"]})
    return pd.DataFrame(rec)


def pct_below(values: np.ndarray, x: float) -> float:
    return round(float((values < x).mean()), 4)


def dist(values: np.ndarray) -> dict:
    q = np.percentile(values, [0, 5, 25, 50, 75, 95, 100])
    return {"min": round(float(q[0]), 2), "p5": round(float(q[1]), 2), "p25": round(float(q[2]), 2),
            "median": round(float(q[3]), 2), "p75": round(float(q[4]), 2), "p95": round(float(q[5]), 2),
            "max": round(float(q[6]), 2), "mean": round(float(values.mean()), 2), "std": round(float(values.std(ddof=1)), 2),
            "share_positive": round(float((values > 0).mean()), 4), "n": int(len(values))}


def main(pass_tag: str) -> int:
    rule = json.loads((OUT / "acceptance_rule_l0063.json").read_text(encoding="utf-8"))
    assert rule["random_book_design"]["A_primary"]["books_per_window"] == N_BOOKS
    for w in WINDOWS:
        WIN[w] = Window(w)

    # ───── الاستراتيجية: الصفوف نفسها (sha256 مع L0061) ─────
    print("══ الاستراتيجية (هابط16) — الهوية والقياس ══", flush=True)
    strat, identity, strat_rows, tables = {}, {}, {}, {}
    for w in WINDOWS:
        rows, _ = M.rows_for(M.R, "bear", COINS, w)
        strat_rows[w] = rows
        M.OUT = OUT
        tmp = M.save_trades(f"verify_a_bear16_c00115_{w}", rows)
        h_new = hashlib.sha256(tmp.read_bytes()).hexdigest()[:16]
        h_old = hashlib.sha256((OUT61 / f"trades_a_bear16_c00115_{w}.csv").read_bytes()).hexdigest()[:16]
        identity[w] = {"sha_L0061": h_old, "sha_rebuilt": h_new, "match": h_new == h_old, "rows": len(rows)}
        if h_new != h_old:
            raise SystemExit(f"صفقات الاستراتيجية لا تطابق L0061 في {w}")
        tmp.rename(OUT / f"trades_strategy_bear16_{w}.csv")
        ev = evaluate(rows, WIN[w], None)
        ref_peak = M.peak_capital(rows)
        if abs(ev["peak_raw"] - ref_peak) > 1e-6:
            raise SystemExit(f"ذروة الشبكة ≠ ذروة الأحداث في {w}: {ev['peak_raw']} / {ref_peak}")
        cyc = M.cycles(rows)
        tables[w] = cycle_table(rows)
        strat[w] = {k: v for k, v in ev.items() if not k.startswith("_")}
        strat[w].update({"cycles": len(cyc), "ret_pct": round(100 * ev["net115"] / ev["peak_raw"], 3),
                         "ret_pct_130": round(100 * ev["net130"] / ev["peak_raw"], 3),
                         "dd_pct_of_peak": round(100 * ev["dd_usd"] / ev["peak_raw"], 2),
                         "cycles_per_coin": {s: len(v) for s, v in tables[w].items()},
                         "median_cycle_days": round(float(np.median([d for v in tables[w].values() for d, _ in v])) * 4 / 24, 1),
                         "mean_cycle_notional": round(float(np.mean([n for v in tables[w].values() for _, n in v])), 2)})
        print(f"  {w}: صافي={ev['net115']} (0.130%: {ev['net130']}) دورات={len(cyc)} شرائح={len(rows)} ذروة={ev['peak_raw']} "
              f"عائد%={strat[w]['ret_pct']} هبوط={ev['dd_usd']} أطول تحت القمة={ev['longest_underwater_days']} يوم", flush=True)
    ref = rule["fixed"]["strategy_reference_L0061"]
    for w in WINDOWS:
        if abs(strat[w]["net115"] - ref[w]["net115"]) > 0.01 or abs(strat[w]["peak_raw"] - ref[w]["peak"]) > 0.01 \
                or abs(strat[w]["net130"] - ref[w]["net130"]) > 0.01:
            raise SystemExit(f"أرقام الاستراتيجية خالفت L0061 في {w}: {strat[w]}")
    print("  ✅ الصفقات والأرقام طابقت L0061 (sha256 · صافي · ذروة · 0.130%)", flush=True)

    # ───── الدفاتر العشوائية ─────
    results = {"pass": pass_tag, "strategy": strat, "identity": identity, "books": {}, "guard": [], "determinism": {},
               "overlap_violations_total": 0, "placement_failures_total": 0}
    summaries: dict[str, dict[str, pd.DataFrame]] = {"A": {}, "B": {}}
    for design in ("A", "B"):
        for w in WINDOWS:
            win = WIN[w]
            P = strat[w]["peak_raw"]
            print(f"══ التصميم {design} · {w} · {N_BOOKS} دفتر · تسوية إلى ذروة {P}$ ══", flush=True)
            per_book, all_rows, all_rows_2 = [], [], []
            for b in range(1, N_BOOKS + 1):
                rows, fails = make_book(design, win, tables[w], b)
                rows2, _ = make_book(design, win, tables[w], b)  # الحتمية داخل العملية
                if json.dumps(rows, sort_keys=True) != json.dumps(rows2, sort_keys=True):
                    raise SystemExit("الدفتر العشوائي غير حتمي داخل العملية")
                ov = overlap_violations(rows)
                results["overlap_violations_total"] += ov
                results["placement_failures_total"] += fails
                ev = evaluate(rows, win, P)
                per_coin = ev["per_coin"]
                per_book.append({"book": b, "net115": ev["net115"], "net130": ev["net130"], "net115_raw": ev["net115_raw"],
                                 "ret_pct": round(100 * ev["net115"] / P, 3), "ret_pct_130": round(100 * ev["net130"] / P, 3),
                                 "peak_raw": ev["peak_raw"], "scale": ev["scale"], "dd_usd": ev["dd_usd"],
                                 "dd_pct_of_peak": round(100 * ev["dd_usd"] / P, 2),
                                 "longest_underwater_days": ev["longest_underwater_days"],
                                 "max_cycle_notional_scaled": ev["max_cycle_notional_scaled"], "slices": ev["slices"],
                                 "overlap_violations": ov, "placement_failures": fails,
                                 **{f"coin_{s}": per_coin.get(s, 0.0) for s in COINS}})
                for k, r in enumerate(rows):
                    all_rows.append((b, r, ev["scale"], float(ev["_p115"][k]), float(ev["_p130"][k])))
                if b % 50 == 0:
                    print(f"    {b}/{N_BOOKS}", flush=True)
            df = pd.DataFrame(per_book)
            summaries[design][w] = df
            df.to_csv(OUT / f"books_{design}_{w}.csv", index=False, encoding="utf-8-sig")
            trades = books_to_frame(all_rows)
            tpath = OUT / f"random_books_{design}_{w}.csv"
            trades.to_csv(tpath, index=False, encoding="utf-8-sig")
            results["determinism"][f"sha_random_books_{design}_{w}"] = hashlib.sha256(tpath.read_bytes()).hexdigest()[:16]
            # عيّنات مستقلة لفحص التتابع والحارس
            for b in (1, 2, 3):
                sub = trades[trades.book == b].drop(columns=["book"])
                sub.to_csv(OUT / "samples" / f"trades_random_{design}_{w}_book{b}.csv", index=False, encoding="utf-8-sig")
            results["guard"].append(guard(tpath))
            print(f"    حارس: {results['guard'][-1]}", flush=True)
            v115, v130, vraw = df.net115.to_numpy(), df.net130.to_numpy(), df.net115_raw.to_numpy()
            s_ = strat[w]
            results["books"][f"{design}_{w}"] = {
                "n_books": int(len(df)), "peak_scaled_to": P,
                "net115": dist(v115), "net130": dist(v130), "ret_pct": dist(df.ret_pct.to_numpy()),
                "net115_unscaled": dist(vraw), "peak_raw": dist(df.peak_raw.to_numpy()), "scale": dist(df.scale.to_numpy()),
                "dd_usd": dist(df.dd_usd.to_numpy()), "dd_pct_of_peak": dist(df.dd_pct_of_peak.to_numpy()),
                "longest_underwater_days": dist(df.longest_underwater_days.to_numpy()),
                "max_cycle_notional_scaled": dist(df.max_cycle_notional_scaled.to_numpy()),
                "books_exceeding_1000_per_cycle": int((df.max_cycle_notional_scaled > 1000 + 1e-6).sum()),
                "strategy_pct_below_115": pct_below(v115, s_["net115"]),
                "strategy_pct_below_130": pct_below(v130, s_["net130"]),
                "strategy_pct_below_unscaled": pct_below(vraw, s_["net115"]),
                "strategy_pct_below_dd": pct_below(-df.dd_usd.to_numpy(), -s_["dd_usd"]),
                "median_per_coin": {s: round(float(df[f"coin_{s}"].median()), 2) for s in COINS},
                "placement_failures": int(df.placement_failures.sum()), "overlap_violations": int(df.overlap_violations.sum()),
            }
            print(f"    وسيط الصافي {results['books'][f'{design}_{w}']['net115']['median']}$ · الاستراتيجية {s_['net115']}$ "
                  f"· فوق {100*results['books'][f'{design}_{w}']['strategy_pct_below_115']:.1f}% من الدفاتر", flush=True)

    # ───── الشرط 6: حذف العملة الأكبر مساهمة ─────
    conc = {}
    for w in WINDOWS:
        pc = strat[w]["per_coin"]
        top = max(pc, key=pc.get)
        s_wo = round(strat[w]["net115"] - pc[top], 2)
        entry = {"top_coin": top, "top_coin_net": pc[top], "top_share_pct": round(100 * pc[top] / strat[w]["net115"], 1),
                 "strategy_net_without_top": s_wo}
        for design in ("A", "B"):
            df = summaries[design][w]
            wo = (df.net115 - df[f"coin_{top}"]).to_numpy()
            entry[f"{design}_median_without_top"] = round(float(np.median(wo)), 2)
            entry[f"{design}_pct_below_without_top"] = pct_below(wo, s_wo)
        conc[w] = entry
    results["concentration"] = conc

    # ───── معيار القبول (التصميم A) ─────
    A = {w: results["books"][f"A_{w}"] for w in WINDOWS}
    B = {w: results["books"][f"B_{w}"] for w in WINDOWS}
    c1 = all(strat[w]["net115"] > 0 for w in WINDOWS)
    c2 = all(strat[w]["ret_pct"] > 0 for w in WINDOWS)
    c3 = all(strat[w]["net115"] > A[w]["net115"]["median"] and strat[w]["ret_pct"] > A[w]["ret_pct"]["median"] for w in WINDOWS)
    c4 = A["JUD"]["strategy_pct_below_115"] >= 0.75
    c5 = all(strat[w]["net130"] > 0 for w in WINDOWS)
    c6 = all(conc[w]["strategy_net_without_top"] > conc[w]["A_median_without_top"] for w in WINDOWS)
    c3B = all(strat[w]["net115"] > B[w]["net115"]["median"] for w in WINDOWS)
    c4B = B["JUD"]["strategy_pct_below_115"] >= 0.75
    passed = all([c1, c2, c3, c4, c5, c6])
    invalid = (results["overlap_violations_total"] > 0 or not all(v["match"] for v in identity.values())
               or results["placement_failures_total"] > 0.01 * N_BOOKS * sum(strat[w]["cycles"] for w in WINDOWS))
    if invalid:
        verdict = "القياس غير صالح"
    else:
        verdict = "يمرّ" if passed else "لا يمرّ"
    cause = None
    if not passed and not invalid:
        pj = A["JUD"]["strategy_pct_below_115"]
        if (not c3) or (not c6) or (c3 and not c4 and pj < 0.70):
            cause = "فشل حقيقي"
        elif c3 and not c4 and 0.70 <= pj < 0.75:
            cause = "ضجيج أو عينة غير كافية"
        elif not c5:
            cause = "مشكلة تصميم تحتاج جولة تطوير (حساسة للكلفة)"
        capital_issue = all(strat[w]["net115"] > A[w]["net115_unscaled"]["median"] for w in WINDOWS) and not c3
        if capital_issue:
            cause = "مشكلة رأس مال"
    results["acceptance"] = {
        "1_positive_both_0115": {"pass": c1, "SEL": strat["SEL"]["net115"], "JUD": strat["JUD"]["net115"]},
        "2_ret_positive_both": {"pass": c2, "SEL": strat["SEL"]["ret_pct"], "JUD": strat["JUD"]["ret_pct"]},
        "3_above_median_A_both": {"pass": c3, "median_SEL": A["SEL"]["net115"]["median"], "median_JUD": A["JUD"]["net115"]["median"],
                                  "median_ret_SEL": A["SEL"]["ret_pct"]["median"], "median_ret_JUD": A["JUD"]["ret_pct"]["median"]},
        "4_above_75pct_JUD_A": {"pass": c4, "pct_below": A["JUD"]["strategy_pct_below_115"]},
        "5_positive_both_0130": {"pass": c5, "SEL": strat["SEL"]["net130"], "JUD": strat["JUD"]["net130"],
                                 "pct_below_130_SEL": A["SEL"]["strategy_pct_below_130"], "pct_below_130_JUD": A["JUD"]["strategy_pct_below_130"]},
        "6_concentration": {"pass": c6, **conc},
        "sensitivity_B": {"3_above_median_B_both": c3B, "4_above_75pct_JUD_B": c4B, "pct_below_SEL": B["SEL"]["strategy_pct_below_115"],
                          "pct_below_JUD": B["JUD"]["strategy_pct_below_115"]},
        "pct_below_SEL_A": A["SEL"]["strategy_pct_below_115"],
        "ALL": passed, "invalid": invalid, "verdict": verdict, "cause_if_fail": cause,
    }
    print("══ معيار القبول (A) ══", flush=True)
    for k, v in results["acceptance"].items():
        if isinstance(v, dict) and "pass" in v:
            print(f"  {k}: {'✓' if v['pass'] else '✗'}", flush=True)
    print(f"  الحكم: {verdict}" + (f" — السبب: {cause}" if cause else ""), flush=True)

    # ───── فحوص: تتابع العيّنات + حارس على ملفات الاستراتيجية ─────
    seq = subprocess.run([sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"), "--dir", str(OUT / "samples"), "--json"],
                         capture_output=True, text=True)
    (OUT / "sequencing_audit_samples.json").write_text(seq.stdout, encoding="utf-8")
    for w in WINDOWS:
        results["guard"].append(guard(OUT / f"trades_strategy_bear16_{w}.csv"))
    for p in sorted((OUT / "samples").glob("*.csv")):
        results["guard"].append(guard(p))

    import pandas, numpy, pyarrow  # noqa
    results["env"] = {"date": "2026-09-27", "python": platform.python_version(), "pandas": pandas.__version__,
                      "numpy": numpy.__version__, "pyarrow": pyarrow.__version__, "platform": platform.platform(),
                      "base_branch": "arena/l0062-long-cycle-random16-2026-09-27 @ 6589d77",
                      "n_books_per_window_per_design": N_BOOKS, "designs": ["A", "B"], "windows": list(WINDOWS),
                      "cost": {"actual": COST, "stress": COST_130, "slippage": 0.0}, "seed_scheme": rule["random_book_design"]["A_primary"]["seed_scheme"]}
    text = json.dumps(results, ensure_ascii=False, indent=2, default=str)
    (OUT / f"results_{pass_tag}.json").write_text(text, encoding="utf-8")
    if pass_tag == "pass1":
        (OUT / "results.json").write_text(text, encoding="utf-8")
        (OUT / "env_dump.txt").write_text(json.dumps(results["env"], ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT / "guard_log.json").write_text(json.dumps(results["guard"], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"اكتمل ({pass_tag}). دفاتر={2 * 2 * N_BOOKS} · مخالفات تداخل={results['overlap_violations_total']} · "
          f"فشل وضع={results['placement_failures_total']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pass1"))
