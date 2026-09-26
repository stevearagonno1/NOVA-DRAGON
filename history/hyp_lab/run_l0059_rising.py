# -*- coding: utf-8 -*-
"""L0059 — إعداد الصاعد وحده. قياس وحكم. لا تفصيل بعد الرؤية.

السقف 18. مكتوب قبل أي رقم.
  مرحلة 0 لا تُحسب. أي فرق يوقف الجولة.
  أ (5 من 8): k للصاعد فقط 2.0 2.5 3.0 4.0 4.5 على الاختيار. k=3.5 هو مرجع المرحلة 0 ولا يُعاد.
  ب (3 من 4): تهدئة الصاعد 0 و1 و6 على الاختيار. 3 هو المرجع ولا يُعاد.
  لا تركيب بين k الفائز والتهدئة. ذلك لم يُعلَن، والعيّنة 62 صفقة.
  ج: الجار = القيمة المجاورة في الشبكة المعلنة. جار صافي محفظته ≤ 0 يُسقط الفائز. لا يُقاس على الحكم.
  د (2 من 2) إن عبر الفائز: حكم 0.115% ثم 0.130%. لا مقعد ثالث.
  العشوائي 5 بذور × فترتين = 10. لا يتسع لسقف د. لم يُقَس. لذلك معيار القبول لا يكتمل. لا اعتماد.
  المقاعد الفارغة لا تُملأ بعد الرؤية.

البذور المعلنة غير المصروفة: 110059 210059 310059 410059 510059.
الفائز = أعلى صافٍ للمحفظة كاملة في الاختيار بين المؤهّلين (صفقات صاعد ≥ 60).
التعادل يُحسم للمرجع k=3.5 وتهدئة 3. لا إعداد جديد عند التعادل.
الهابط والعرضي يبقيان على k=3.5 وتهدئة 3.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/l0059")
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

src = (ROOT / "history" / "hyp_lab" / "run_l0056_widen_book.py").read_text(encoding="utf-8")
src = src.replace('pathlib.Path("/home/user/l0056")', 'pathlib.Path("/home/user/l0059")')
src = src.replace('if __name__ == "__main__":', "if False:")
patched = pathlib.Path("/tmp/r56_l0059.py")
patched.write_text(src, encoding="utf-8")
spec = importlib.util.spec_from_file_location("r56_l0059", patched)
R56 = importlib.util.module_from_spec(spec)
sys.modules["r56_l0059"] = R56
spec.loader.exec_module(R56)

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0059"
OUT.mkdir(parents=True, exist_ok=True)
R56.OUT = OUT
R56.DAILY = pathlib.Path.home() / ".cache" / "l0059_daily"
R56.DAILY.mkdir(parents=True, exist_ok=True)
FRAMES = pathlib.Path.home() / ".cache" / "l0046_frames"

COST = 0.00115
COST_130 = 0.00130
CAP = 18
K_GRID = (2.0, 2.5, 3.0, 3.5, 4.0, 4.5)
COOL_GRID = (0, 1, 3, 6)
K_OTHER = 3.5
COOL_OTHER = 3
SEEDS = (110059, 210059, 310059, 410059, 510059)
LEDGER: list[dict] = []
RULE = {
    "written_before_measurement": True,
    "winner": "أعلى صافٍ للمحفظة كاملة في الاختيار بين من صفقات صاعده ≥ 60. التعادل للمرجع.",
    "neighbor": "الجار المباشر في الشبكة المعلنة. صافي المحفظة ≤ 0 يسقط الفائز. لا يُقاس على الحكم.",
    "no_combination": "لا تركيب بين k والتهدئة. لم يُعلَن.",
    "random": "لم يُقَس. 10 قياسات لا تتسع لسقف المرحلة د (2). معيار القبول لا يكتمل.",
    "seeds_declared_unused": list(SEEDS),
    "cap_plan": {"A": 5, "B": 3, "C": 0, "D": 2, "cap": 18},
}


def dump(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def log(name: str, window: str, phase: str) -> None:
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف {CAP}")
    LEDGER.append({"#": len(LEDGER) + 1, "المرحلة": phase, "القياس": name, "الفترة": window})


def rising_stats(rows: list[dict], cost: float) -> dict:
    t = pd.DataFrame(rows)
    if t.empty or "regime" not in t.columns:
        return {"net": 0.0, "trades": 0, "per": None, "move": None}
    g = t[t["regime"] == "صاعد"]
    if g.empty:
        return {"net": 0.0, "trades": 0, "per": None, "move": None}
    p = g["pnl"].to_numpy(float)
    net = float(p.sum())
    n = len(g)
    qty = g["notional"].to_numpy(float) / g["entry"].to_numpy(float)
    gross = float((qty * (g["exit"].to_numpy(float) - g["entry"].to_numpy(float))).sum()
                  + (qty * cost * (g["entry"].to_numpy(float) + g["exit"].to_numpy(float))).sum())
    return {
        "net": round(net, 2),
        "trades": int(n),
        "per": round(net / n, 5),
        "move": round(gross / n, 5),
    }


def guard_file(name: str, cost: float) -> None:
    path = OUT / f"trades_{name}.csv"
    st = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
         "--trades", str(path), "--frames", str(FRAMES), "--cost", str(cost), "--bar-tag", "4h"],
        capture_output=True, text=True,
    )
    if st.returncode != 0 or "مخالفات الدخول=0" not in st.stdout or "تُخطّي=0" not in st.stdout:
        raise SystemExit(f"حارس التعبئة فشل على {name}: {(st.stdout or st.stderr)[-400:]}")
    au = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
         "--trades", str(path), "--require-zero"],
        capture_output=True, text=True,
    )
    if au.returncode != 0:
        raise SystemExit(f"تداخل في {name}: {(au.stdout or au.stderr)[-300:]}")


def run_rising(name: str, k_rising: float, cool_rising: int, s0: str, s1: str,
               cost: float, counted: bool, phase: str) -> tuple[dict, list[dict], dict]:
    R56.set_cost(cost)
    rows: list[dict] = []
    sig_in = sig_out = cool_blocked = 0
    rising_in = rising_out = rising_cool = 0
    try:
        enabled, _ = R56.load_frozen_map()
        for sym in R56.SYMS:
            df = R56.R46.frames(sym)
            win = R56.R48.window(df, s0, s1)
            if len(win) < 100:
                continue
            base = R56.routed_signal(df, sym, enabled)
            vol = df["volume"]
            vol_ma = vol.shift(1).rolling(20, min_periods=20).mean()
            er = R56.entry_regime(sym, df.index)
            rising = (er == "صاعد").fillna(False)
            ok = vol_ma.notna()
            keep = (rising & ok & (vol > k_rising * vol_ma)) | (~rising & ok & (vol > K_OTHER * vol_ma))
            sg = (base & keep).reindex(win.index, fill_value=False).fillna(False).astype(bool)
            base_w = base.reindex(win.index, fill_value=False).fillna(False).astype(bool)
            er_w = er.reindex(win.index)
            sig_in += int(base_w.sum())
            sig_out += int(sg.sum())
            rising_in += int((base_w & (er_w == "صاعد")).sum())
            rising_out += int((sg & (er_w == "صاعد")).sum())
            outcomes = R56.outcomes_for(sym, s0, s1)
            accepted = np.zeros(len(win), dtype=bool)
            last_exit = -1
            cool_until = -1
            er_win = er_w.to_numpy()
            for i in np.flatnonzero(sg.to_numpy()):
                if i >= len(outcomes) or outcomes[i] is None:
                    continue
                if last_exit > i:
                    continue
                if i <= cool_until:
                    cool_blocked += 1
                    if er_win[i] == "صاعد":
                        rising_cool += 1
                    continue
                rec = outcomes[i]
                accepted[i] = True
                last_exit = int(rec["exit_j"])
                if round(float(rec["pnl"]), 4) < 0:
                    ncool = cool_rising if er_win[i] == "صاعد" else COOL_OTHER
                    cool_until = max(cool_until, int(rec["exit_j"]) + ncool - 1)
            rows.extend(R56.R48.rows_from_chosen(sym, name, R56.R48.greedy(outcomes, accepted)))
        rows = R56.tag_regime(rows)
    finally:
        R56.restore_cost()
    R56.save_trades(name, rows)
    guard_file(name, cost)
    rec = R56.record(name, "اختيار" if s0.startswith("2021") else "حكم", rows, cost, None, False, phase, {
        "k_rising": k_rising, "cool_rising": cool_rising,
        "sig_in": sig_in, "sig_out": sig_out, "cool_blocked": cool_blocked,
    })
    rise = rising_stats(rows, cost)
    reject = None if rising_in == 0 else round(1.0 - rising_out / rising_in, 4)
    extra = {
        "rising": rise,
        "rising_sig_in": rising_in,
        "rising_sig_out": rising_out,
        "rising_vol_reject": reject,
        "rising_cool_blocked": rising_cool,
        "portfolio_net": rec["net"],
        "portfolio_trades": rec["trades"],
        "move": rec["move"],
    }
    if counted:
        log(name, rec["الفترة"], phase)
        print(f"  [{len(LEDGER)}/{CAP}] {name}: محفظة={rec['net']} / {rec['trades']} صاعد={rise['trades']} حركة_صاعد={rise['move']}", flush=True)
    else:
        print(f"  [لا يُحسب] {name}: محفظة={rec['net']} / {rec['trades']} صاعد={rise['trades']}", flush=True)
    return rec, rows, extra


def neighbors(kind: str, value: float) -> list[float]:
    grid = K_GRID if kind == "k" else COOL_GRID
    xs = list(grid)
    i = xs.index(value)
    out = []
    if i > 0:
        out.append(xs[i - 1])
    if i + 1 < len(xs):
        out.append(xs[i + 1])
    return out


def main() -> int:
    dump(OUT / "acceptance_rule_l0059.json", RULE)
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"], capture_output=True, text=True)
    raw = can.stdout
    cj = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
    print(f"  كاناري: {cj.get('canary')} net={cj.get('got', {}).get('net')}", flush=True)
    if cj.get("canary") != "ok":
        raise SystemExit("الكاناري ليس ok")
    dump(OUT / "canary.json", cj)
    R56.prepare()
    R56.build_regimes(R56.archive_symbols())
    R56.use_syms(R56.archive_symbols())
    enabled, mp = R56.load_frozen_map()
    fp = hashlib.sha256((ROOT / "history/research/hyp_lab_out/L0051/routing_map.json").read_bytes()).hexdigest()
    if not fp.startswith("14df873e"):
        raise SystemExit(f"بصمة الخريطة خالفت الورقة: {fp[:16]}")
    print(f"  خريطة {fp[:16]} خانات={len(enabled)}", flush=True)

    print("══ مرحلة 0 ══", flush=True)
    rec, rows = R56.run_book("p0_c00115_JUD", "p0_c00115_JUD", R56.routed(enabled), R56.WINNER,
                             "2024-01-01", "2026-08-31", "حكم", COST, False, "0")
    guard_file("p0_c00115_JUD", COST)
    if abs(rec["net"] - 33.24) > 0.5 or rec["trades"] != 464:
        raise SystemExit(f"حكم 0.115 خالف الورقة: {rec['net']} / {rec['trades']}")
    rise = rising_stats(rows, COST)
    print(f"  صاعد الحكم: {rise} مرجع 25.74 / 156 / 0.1650", flush=True)
    if abs(rise["net"] - 25.74) > 0.5 or rise["trades"] != 156 or abs(rise["per"] - 0.1650) > 0.00015:
        raise SystemExit(f"صاعد الحكم خالف الورقة: {rise}")
    rec, rows = R56.run_book("p0_c00115_SEL", "p0_c00115_SEL", R56.routed(enabled), R56.WINNER,
                             "2021-09-01", "2023-12-31", "اختيار", COST, False, "0")
    guard_file("p0_c00115_SEL", COST)
    if abs(rec["net"] - 45.66) > 0.5 or rec["trades"] != 328:
        raise SystemExit(f"اختيار 0.115 خالف الورقة: {rec['net']} / {rec['trades']}")
    rise_sel = rising_stats(rows, COST)
    print(f"  صاعد الاختيار: {rise_sel} الورقة تقدّر ~62", flush=True)
    rec, _ = R56.run_book("p0_c00130_JUD", "p0_c00130_JUD", R56.routed(enabled), R56.WINNER,
                          "2024-01-01", "2026-08-31", "حكم", COST_130, False, "0")
    guard_file("p0_c00130_JUD", COST_130)
    if abs(rec["net"] - 30.99) > 0.5 or rec["trades"] != 464:
        raise SystemExit(f"حكم 0.130 خالف الورقة: {rec['net']} / {rec['trades']}")
    print("  ✅ الأربعة طابقت", flush=True)

    print("══ مطابقة المسار الخاص عند المرجع ══", flush=True)
    rec_m, rows_m, extra_m = run_rising("match_k35_c3_SEL", 3.5, 3, "2021-09-01", "2023-12-31", COST, False, "0")
    if abs(rec_m["net"] - 45.66) > 0.5 or rec_m["trades"] != 328:
        raise SystemExit(f"مسار الصاعد لم يُعد إنتاج الاختيار: {rec_m['net']} / {rec_m['trades']}")
    if rising_stats(rows_m, COST)["trades"] != rise_sel["trades"]:
        raise SystemExit("صاعد الاختيار اختلف بين المسارين")
    rec_j, rows_j, _ = run_rising("match_k35_c3_JUD", 3.5, 3, "2024-01-01", "2026-08-31", COST, False, "0")
    if abs(rec_j["net"] - 33.24) > 0.5 or rec_j["trades"] != 464 or rising_stats(rows_j, COST)["trades"] != 156:
        raise SystemExit(f"مسار الصاعد لم يُعد إنتاج الحكم: {rec_j['net']} / {rec_j['trades']}")
    print("  ✅ المسار الخاص طابق المرجع", flush=True)

    table = {"k": {}, "cool": {}}
    table["k"]["3.5"] = {"portfolio_net": 45.66, "portfolio_trades": 328, **extra_m, "counted": False, "source": "match"}
    table["cool"]["3"] = table["k"]["3.5"]

    print("══ مرحلة أ: k للصاعد ══", flush=True)
    for k in (2.0, 2.5, 3.0, 4.0, 4.5):
        rec, rows, extra = run_rising(f"a_k{k:.1f}_SEL", k, 3, "2021-09-01", "2023-12-31", COST, True, "أ")
        table["k"][f"{k:.1f}"] = extra | {"portfolio_net": rec["net"], "portfolio_trades": rec["trades"], "counted": True}

    print("══ مرحلة ب: تهدئة الصاعد ══", flush=True)
    for cool in (0, 1, 6):
        rec, rows, extra = run_rising(f"b_c{cool}_SEL", 3.5, cool, "2021-09-01", "2023-12-31", COST, True, "ب")
        table["cool"][str(cool)] = extra | {"portfolio_net": rec["net"], "portfolio_trades": rec["trades"], "counted": True}
    dump(OUT / "selection_table.json", table)

    candidates = []
    for k, row in table["k"].items():
        candidates.append({"kind": "k", "value": float(k), "cool": 3, "k": float(k), **row})
    for c, row in table["cool"].items():
        if int(c) == 3:
            continue
        candidates.append({"kind": "cool", "value": float(c), "cool": int(c), "k": 3.5, **row})
    eligible = [c for c in candidates if c["rising"]["trades"] >= 60]
    eligible.sort(key=lambda c: (-c["portfolio_net"], 0 if c["kind"] == "k" and c["value"] == 3.5 else 1))
    winner = eligible[0]
    is_ref = winner["kind"] == "k" and winner["value"] == 3.5
    neigh = []
    rejected = False
    reason = "المرجع أعلى المؤهلين أو تعادل. لا إعداد جديد."
    if not is_ref:
        for v in neighbors(winner["kind"], winner["value"]):
            src = table["k" if winner["kind"] == "k" else "cool"]
            key = f"{v:.1f}" if winner["kind"] == "k" else str(int(v))
            row = src[key]
            item = {"value": v, "portfolio_net": row["portfolio_net"], "positive": row["portfolio_net"] > 0}
            neigh.append(item)
            if row["portfolio_net"] <= 0:
                rejected = True
        reason = "جار خاسر. مرفوض. لا حكم." if rejected else "عبر الاختيار والجوار. يُقاس الحكم مرة."
    choice = {
        "written_before_judgement": True,
        "winner": winner,
        "is_reference": is_ref,
        "neighbors": neigh,
        "rejected_by_neighbor": rejected,
        "reason": reason,
        "eligible_count": len(eligible),
    }
    dump(OUT / "rising_choice.json", choice)
    print(f"  أُودع: {reason} الفائز={winner['kind']} {winner['value']} محفظة={winner['portfolio_net']}", flush=True)

    judged = None
    if not is_ref and not rejected:
        print("══ مرحلة د ══", flush=True)
        k = winner["k"]
        cool = winner["cool"]
        rec1, rows1, ex1 = run_rising("d_win_c00115_JUD", k, cool, "2024-01-01", "2026-08-31", COST, True, "د")
        rec2, rows2, ex2 = run_rising("d_win_c00130_JUD", k, cool, "2024-01-01", "2026-08-31", COST_130, True, "د")
        judged = {"c00115": ex1 | {"portfolio_net": rec1["net"], "portfolio_trades": rec1["trades"]},
                  "c00130": ex2 | {"portfolio_net": rec2["net"], "portfolio_trades": rec2["trades"]}}
        dump(OUT / "judgement.json", judged)

    # حتمية: أعد قياسات الاختيار المعدودة وقارن sha256
    print("══ حتمية ══", flush=True)
    hashes = {}
    for path in sorted(OUT.glob("trades_*.csv")):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    R56.OUTCOME_CACHE.clear()
    mismatch = []
    for k in (2.0, 2.5, 3.0, 4.0, 4.5):
        name = f"a_k{k:.1f}_SEL"
        run_rising(name, k, 3, "2021-09-01", "2023-12-31", COST, False, "أ")
        h2 = hashlib.sha256((OUT / f"trades_{name}.csv").read_bytes()).hexdigest()
        if h2 != hashes[f"trades_{name}.csv"]:
            mismatch.append(name)
    for cool in (0, 1, 6):
        name = f"b_c{cool}_SEL"
        run_rising(name, 3.5, cool, "2021-09-01", "2023-12-31", COST, False, "ب")
        h2 = hashlib.sha256((OUT / f"trades_{name}.csv").read_bytes()).hexdigest()
        if h2 != hashes[f"trades_{name}.csv"]:
            mismatch.append(name)
    if mismatch:
        raise SystemExit(f"الحتمية فشلت: {mismatch}")
    print("  ✅ sha256 طابق", flush=True)

    dump(OUT / "ledger.json", LEDGER)
    dump(OUT / "env_dump.txt", {
        "cap": CAP, "counted": len(LEDGER), "canary": cj.get("canary"),
        "canary_net": cj.get("got", {}).get("net"),
        "root_patch": "/home/user/l0056 -> /home/user/l0059 in memory",
        "regime_py": False, "random": "لم يُقَس", "seeds": list(SEEDS),
        "selection_rising_trades": rise_sel["trades"],
        "determinism": "sha256 match",
    })
    (OUT / "sha256.txt").write_text("\n".join(f"{h}  {n}" for n, h in hashes.items()) + "\n", encoding="utf-8")
    print(f"اكتمل. المستهلك {len(LEDGER)}/{CAP}. صاعد الاختيار={rise_sel['trades']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
