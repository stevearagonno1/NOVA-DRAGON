# -*- coding: utf-8 -*-
"""L0007 — إعادة المقاسات على 5 سنوات (بروتوكول تدريب/اختبار)

البروتوكول (الدستور):
  - النوافذ: تدريب 2023-09-01→2024-12-31 | اختبار 2025-01-01→2026-08-31
  - الاختيار يتم على التدريب فقط — من بين التركيبات غير المتحللة (≥100 صفقة)
    (إلا لذلك سيكون «الأفضل» دائماً التركيبة الفارغة: 0 صفقات، صافي 0)
  - الحكم على الاختبار فقط — نافذة لم تُستعمل في أي اختيار
  - بوابة القبول على الاختبار: net>0 AND PF≥1.3 AND trades≥100

الرموز: قائمة التداول المعتمدة (8) من crypto_archive/ (بيانات 1m → شبكة 5m).
الكاناري (tools/canary.py) بوابة سابقة إلزامية قبل أي تشغيل.

المخرجات: research/hyp_lab_out/L0007/<exp>/<sym>/{sweep_train.csv, test_selected.csv}
          + <exp>/all_symbols_{train,test}.csv + env_dump.txt + summary.txt
حتمية: بلا عشوائية — إعادة التشغيل مطابقة بايت-ببايت (عدا سطر مدة التشغيل).
"""
from __future__ import annotations
import hashlib
import itertools
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import load, to_5m, atr, simulate  # noqa: E402

import F_126_mss_core as M126  # noqa: E402
import F_127_disp_gate as M127  # noqa: E402
import F_192_ext_dive as M192  # noqa: E402
import F_197_dual_trail as M197  # noqa: E402
import F_205_cooldown as M205  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
ARCHIVE = REPO / "crypto_archive"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XLMUSDT", "LINKUSDT", "GRAMUSDT", "RENDERUSDT", "FILUSDT"]
WARM_START = "2023-06-01"          # دفء المؤشرات قبل بداية التدريب
TRAIN_START, TRAIN_END = "2023-09-01", "2024-12-31"
TEST_START, TEST_END = "2025-01-01", "2026-08-31"
GATE_PF, GATE_TRADES = 1.3, 100

EXPS = {
    "F_126": M126,
    "F_127": M127,
    "F_192": M192,
    "F_197": M197,
    "F_205": M205,
}


def combos_for(exp: str) -> list[dict]:
    mod = EXPS[exp]
    if exp == "F_197":
        # شكل L‑0006 (12): std مكرر على كل trig/lock (صفوف متطابقة — أمانة A10) + dual 6
        rows = [{"exit": "std", "trig": t, "lock": l}
                for t in mod.SWEEP_PARAMS["trig"] for l in mod.SWEEP_PARAMS["lock"]]
        rows += [{"exit": "dual", "trig": t, "lock": l}
                 for t in mod.SWEEP_PARAMS["trig"] for l in mod.SWEEP_PARAMS["lock"]]
        return rows
    names = list(mod.SWEEP_PARAMS)
    vals = [mod.SWEEP_PARAMS[n] for n in names]
    return [dict(zip(names, v)) for v in itertools.product(*vals)]


def param_cols(exp: str) -> list[str]:
    if exp == "F_197":
        return ["NOVA_EXIT", "NOVA_TRIG", "NOVA_LOCK"]
    return [f"NOVA_{n.upper()}" for n in EXPS[exp].SWEEP_PARAMS]


def combo_row(exp: str, combo: dict) -> dict:
    if exp == "F_197":
        return {"NOVA_EXIT": combo["exit"], "NOVA_TRIG": combo["trig"], "NOVA_LOCK": combo["lock"]}
    return {f"NOVA_{n.upper()}": combo[n] for n in EXPS[exp].SWEEP_PARAMS}


def signals_for(exp: str, df: pd.DataFrame, combo: dict) -> pd.Series:
    if exp == "F_197":
        return M126.mss_signal(df)  # سائق MSS (نواة F-126 بالقيم الافتراضية) — نفس L‑0006
    if exp == "F_205":
        return M205.make_signals(df)  # سائق MSS على الشبكة (هنا 5m) — التهديئة في simulate
    return EXPS[exp].make_signals(df, **combo)


def sim_kwargs(exp: str, combo: dict) -> dict:
    if exp == "F_197":
        if combo["exit"] == "dual":
            return {"exit_mode": "dual",
                    "dual": M197.make_dual_spec(trig=combo["trig"], lock=combo["lock"])}
        return {"exit_mode": "std"}
    if exp == "F_205":
        return {"max_per": int(combo["max_per"]), "cooldown_s": float(combo["cooldown_s"])}
    return {}


def pf_of(trades: list[dict]) -> float:
    g = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    lo = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    if lo > 0:
        return g / lo
    return float("inf") if g > 0 else 0.0


def stats_row(st: dict, trades: list[dict]) -> dict:
    return {"net": st["net"], "trades": st["trades"], "win_pct": st["win_pct"], "pf": pf_of(trades)}


def run_exp(exp: str, frames: dict[str, pd.DataFrame], out: pathlib.Path) -> list[dict]:
    mod = EXPS[exp]
    base = out / exp
    base.mkdir(parents=True, exist_ok=True)
    train_rows, test_rows = [], []
    for sym in SYMBOLS:
        df_full = frames[sym]
        tr = df_full[(df_full.index >= TRAIN_START) & (df_full.index <= TRAIN_END)]
        te = df_full[(df_full.index >= TEST_START) & (df_full.index <= TEST_END)]
        tr_a, te_a = atr(tr), atr(te)
        symdir = base / sym
        symdir.mkdir(exist_ok=True)

        rows = []
        for combo in combos_for(exp):
            sig = signals_for(exp, tr, combo)
            st, trades = simulate(tr, sig, tr_a, notional=1000, bar_secs=300, **sim_kwargs(exp, combo))
            r = {"symbol": sym}
            r.update(combo_row(exp, combo))
            r.update(stats_row(st, trades))
            rows.append(r)
        tdf = pd.DataFrame(rows)
        tdf.to_csv(symdir / "sweep_train.csv", index=False, encoding="utf-8-sig")

        # الاختيار على التدريب فقط — من بين التركيبات غير المتحللة (≥100 صفقة)
        cand = tdf[tdf["trades"] >= GATE_TRADES]
        if len(cand) == 0:
            trow = {"symbol": sym, "n_ties_train": 0, "sel_status": "بلا تركيبة غير متحللة (تدريب <100 صفقة)",
                    "train_net": np.nan, "train_trades": 0,
                    "test_net": 0.0, "test_trades": 0, "test_win_pct": 0.0, "test_pf": 0.0,
                    "gate": False}
            for k in param_cols(exp):
                trow[f"sel_{k}"] = np.nan
            pd.DataFrame([trow]).to_csv(symdir / "test_selected.csv", index=False, encoding="utf-8-sig")
            train_rows.append(tdf)
            test_rows.append(pd.DataFrame([trow]))
            print(f"  {exp}/{sym}: بلا تركيبة غير متحللة (كل تركيبات التدريب <100 صفقة)", flush=True)
            continue
        best_i = int(cand["net"].idxmax())
        best = cand.iloc[best_i]
        n_ties = int((cand["net"] == best["net"]).sum())
        bc = {k: best[k] for k in param_cols(exp)}
        if exp == "F_197":
            bcombo = {"exit": bc["NOVA_EXIT"], "trig": float(bc["NOVA_TRIG"]), "lock": float(bc["NOVA_LOCK"])}
        elif exp == "F_205":
            bcombo = {"cooldown_s": float(bc["NOVA_COOLDOWN_S"]), "max_per": int(bc["NOVA_MAX_PER"])}
        else:
            bcombo = {n: (int(bc[k]) if float(bc[k]) == int(bc[k]) else float(bc[k]))
                      for n, k in zip(mod.SWEEP_PARAMS, param_cols(exp))}
        trow_status = "ok"

        sig_t = signals_for(exp, te, bcombo)
        st_t, trades_t = simulate(te, sig_t, te_a, notional=1000, bar_secs=300, **sim_kwargs(exp, bcombo))
        trow = {"symbol": sym, "n_ties_train": n_ties, "sel_status": trow_status,
                "train_net": best["net"], "train_trades": int(best["trades"]),
                "test_net": st_t["net"], "test_trades": st_t["trades"],
                "test_win_pct": st_t["win_pct"], "test_pf": pf_of(trades_t),
                "gate": bool(st_t["net"] > 0 and pf_of(trades_t) >= GATE_PF and st_t["trades"] >= GATE_TRADES)}
        for k in param_cols(exp):
            trow[f"sel_{k}"] = bc[k]
        tdf_t = pd.DataFrame([trow])
        tdf_t.to_csv(symdir / "test_selected.csv", index=False, encoding="utf-8-sig")
        train_rows.append(tdf)
        test_rows.append(tdf_t)
        print(f"  {exp}/{sym}: تدريب {len(tr)} شمعة → اختبار {len(te)} شمعة | "
              f"أفضل تدريب net={best['net']:.2f}$ → اختبار net={st_t['net']:.2f}$ "
              f"({st_t['trades']} صفقة، PF={pf_of(trades_t):.2f}) gate={'✓' if trow['gate'] else '✗'}", flush=True)

    allt = pd.concat(train_rows, ignore_index=True)
    allt.to_csv(base / "all_symbols_train.csv", index=False, encoding="utf-8-sig")
    allt = pd.concat(test_rows, ignore_index=True)
    allt.to_csv(base / "all_symbols_test.csv", index=False, encoding="utf-8-sig")
    return allt.to_dict("records")


def main() -> int:
    t0 = time.time()
    out = REPO / "research" / "hyp_lab_out" / "L0007"
    out.mkdir(parents=True, exist_ok=True)

    # 0) الكاناري إلزامي (بوابة سلامة)
    import subprocess
    can = subprocess.run([sys.executable, str(REPO / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    canary = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if canary.get("canary") != "ok":
        print("الكاناري فشل — إيقاف L0007 (بوابة سلامة).", file=sys.stderr)
        print(can.stdout)
        return 1
    print(f"الكاناري: PASS (net={canary['got']['net']} trades={canary['got']['trades']})", flush=True)

    # 1) تحميل + شبكة 5m + بصمات
    frames, sha = {}, {}
    for sym in SYMBOLS:
        p = ARCHIVE / f"{sym}_1m.parquet"
        sha[sym] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        df1m = load(str(p), start=WARM_START, end=TEST_END)
        frames[sym] = to_5m(df1m)
        print(f"{sym}: {len(frames[sym]):,} شمعة 5m ({frames[sym].index[0]} → {frames[sym].index[-1]})", flush=True)

    # 2) الجولات
    verdicts = {}
    for exp in EXPS:
        print(f"[{exp}]", flush=True)
        verdicts[exp] = run_exp(exp, frames, out)

    # 3) env dump + summary
    import platform
    (out / "env_dump.txt").write_text(
        f"python={platform.python_version()}\n"
        f"pandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"window: train={TRAIN_START}→{TRAIN_END} | test={TEST_START}→{TEST_END}\n"
        f"cost=0.13%/side | notional=1000$ | bar=5m | canary={canary['got']['net']}\n"
        + "".join(f"sha256[:16] {k}={v}\n" for k, v in sha.items()), encoding="utf-8")
    lines = ["# L0007 — إعادة المقاسات على 5 سنوات — أفضل (اختبار) لكل تجربة×رمز",
             f"# مدة التشغيل: {time.time()-t0:.1f} ث"]
    for exp, rows in verdicts.items():
        df = pd.DataFrame(rows).sort_values("test_net", ascending=False)
        for _, x in df.head(4).iterrows():
            lines.append(f"  {exp} {x['symbol']}: test_net={x['test_net']:.2f}$ "
                         f"trades={int(x['test_trades'])} win={x['test_win_pct']:.1f}% "
                         f"PF={x['test_pf']:.2f} gate={'نعم' if x['gate'] else 'لا'} "
                         f"| sel={ {k: x[f'sel_{k}'] for k in param_cols(exp)} } "
                         f"| train_net={x['train_net']:.2f}$ "
                         f"| {x['sel_status']}")
    (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines), flush=True)
    print(f"الكل: {time.time()-t0:.1f} ث → {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
