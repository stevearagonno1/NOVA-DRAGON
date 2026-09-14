# -*- coding: utf-8 -*-
"""NOVA hyp_lab — شغّل الجولة الأولى (L0004).

الاستخدام:
    python3 hyp_lab/run_lab.py --symbols BTCUSDT,BNBUSDT,LINKUSDT,SOLUSDT \
        --start 2026-06-01 --end 2026-09-01 --out research/hyp_lab_out/L0004 \
        [--exp F_126,F_127]

كل تجربة = مجلد مستقل بـ sweep_train.csv (utf-8-sig) متوافق مع tools/audit_lane.py
+ trades.csv لكل رمز + env_dump.txt (بروتوكول D-0013).
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402
import F_001_rsi2_snapback as M001   # noqa: E402
import F_008_turtle_soup as M008     # noqa: E402
import F_015_zscore_regime as M015   # noqa: E402
import F_126_mss_core as M126        # noqa: E402
import F_127_disp_gate as M127       # noqa: E402
import F_192_ext_dive as M192        # noqa: E402
import F_197_dual_trail as M197      # noqa: E402
import F_204_r_parity as M204        # noqa: E402
import F_205_cooldown as M205        # noqa: E402

EXP = {
    "F_001": dict(mod=M001, tf="5m", mode="std",
                  grid={"NOVA_RSI2_OS": M001.SWEEP_PARAMS["rsi2_os"],
                        "NOVA_SMA_TREND": M001.SWEEP_PARAMS["sma_trend"],
                        "NOVA_SMA_PULL": M001.SWEEP_PARAMS["sma_pull"]},
                  pmap={"rsi2_os": "NOVA_RSI2_OS", "sma_trend": "NOVA_SMA_TREND", "sma_pull": "NOVA_SMA_PULL"}),
    "F_008": dict(mod=M008, tf="5m", mode="std",
                  grid={"NOVA_LB": M008.SWEEP_PARAMS["lookback"],
                        "NOVA_WICK": M008.SWEEP_PARAMS["wick_ratio"]},
                  pmap={"lookback": "NOVA_LB", "wick_ratio": "NOVA_WICK"}),
    "F_015": dict(mod=M015, tf="5m", mode="std",
                  grid={"NOVA_ZP": M015.SWEEP_PARAMS["z_p"],
                        "NOVA_ZTH": M015.SWEEP_PARAMS["z_th"],
                        "NOVA_WICK": M015.SWEEP_PARAMS["wick_ratio"]},
                  pmap={"z_p": "NOVA_ZP", "z_th": "NOVA_ZTH", "wick_ratio": "NOVA_WICK"}),
    "F_126": dict(mod=M126, tf="5m", mode="std",
                  grid={"NOVA_BODY": M126.SWEEP_PARAMS["body_ratio"],
                        "NOVA_RNG_ATR": M126.SWEEP_PARAMS["range_atr"],
                        "NOVA_LB": M126.SWEEP_PARAMS["lookback"]},
                  pmap={"body_ratio": "NOVA_BODY", "range_atr": "NOVA_RNG_ATR", "lookback": "NOVA_LB"}),
    "F_127": dict(mod=M127, tf="5m", mode="std",
                  grid={"NOVA_DISP_MIN": M127.SWEEP_PARAMS["disp_min"]},
                  pmap={"disp_min": "NOVA_DISP_MIN"}),
    "F_192": dict(mod=M192, tf="5m", mode="std",
                  grid={"NOVA_EXT_MAX": M192.SWEEP_PARAMS["ext_max"]},
                  pmap={"ext_max": "NOVA_EXT_MAX"}),
    "F_197": dict(mod=M197, tf="1m", mode="dual",
                  grid={"NOVA_EXIT": ["std", "dual"],
                        "NOVA_TRIG": M197.SWEEP_PARAMS["trig"],
                        "NOVA_LOCK": M197.SWEEP_PARAMS["lock"]},
                  pmap={"exit": "NOVA_EXIT", "trig": "NOVA_TRIG", "lock": "NOVA_LOCK"}),
    "F_204": dict(mod=M204, tf="5m", mode="sizing",
                  grid={"NOVA_R": M204.SWEEP_PARAMS["R"],
                        "NOVA_CAP": M204.SWEEP_PARAMS["cap"],
                        "NOVA_HALVE": M204.SWEEP_PARAMS["halve_vr"]},
                  pmap={"R": "NOVA_R", "cap": "NOVA_CAP", "halve_vr": "NOVA_HALVE"}),
    "F_205": dict(mod=M205, tf="1m", mode="posmgmt",
                  grid={"NOVA_COOL_S": M205.SWEEP_PARAMS["cooldown_s"],
                        "NOVA_MAX_PER": M205.SWEEP_PARAMS["max_per"]},
                  pmap={"cooldown_s": "NOVA_COOL_S", "max_per": "NOVA_MAX_PER"}),
}


def write_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def run_exp(key: str, symbols: list[str], data_dir: Path, start: str, end: str, out: Path):
    spec = EXP[key]
    mod, tf, mode = spec["mod"], spec["tf"], spec["mode"]
    grid = spec["grid"]
    pmap = spec["pmap"]
    axis_names = list(grid.keys())
    combos = [dict(zip(axis_names, vals)) for vals in itertools.product(*(grid[k] for k in axis_names))]

    exp_dir = out / key
    all_rows: list[dict] = []
    t0 = time.time()
    for sym in symbols:
        p1m = data_dir / f"{sym}_1m.parquet"
        if not p1m.exists():
            print(f"  ⚠️ {sym}: لا يوجد {p1m} — يُهمَل")
            continue
        df1m = C.load(str(p1m), start=start, end=end)
        if tf == "5m":
            frame = C.to_5m(df1m)
            atrf = C.atr(frame)
            bar_secs = 300
            base5 = M126.mss_signal(frame) if mode in ("dual", "sizing") else None
        else:
            frame = df1m
            atrf = C.atr(frame)
            bar_secs = 60
            # تخطيط إشارة 5m (نواة MSS) إلى شبكة الدقي عند لحظة العلم السببية
            f5 = C.to_5m(df1m)
            base5 = M126.mss_signal(f5)
            a5 = C.atr(f5)
            tgt = (base5[base5].index + pd.Timedelta(minutes=5))
            tgt = tgt[tgt.isin(frame.index)]   # حماية من فجوات الدقائق (شمعة مفقودة)
            base1 = pd.Series(False, index=frame.index)
            base1.loc[tgt] = True
            atr_mapped = pd.Series(np.nan, index=frame.index)
            atr_mapped.loc[tgt] = a5.reindex(tgt)
            atrf = atr_mapped if mode in ("dual", "sizing") else C.atr(frame)

        sym_trades: list[dict] = []
        for combo in combos:
            vals = {p: combo[c] for p, c in pmap.items()}
            if mode in ("std", "posmgmt") and key != "F_205":
                sig = mod.make_signals(frame, **vals)
            elif key == "F_205":
                sig = mod.make_signals(frame)
            elif key == "F_197":
                sig = base1 if tf == "1m" else mod.make_signals(frame)
            elif key == "F_204":
                sig = base5
            else:
                sig = mod.make_signals(frame, **vals)

            dual = None
            if key == "F_197" and combo["NOVA_EXIT"] == "dual":
                dual = M197.make_dual_spec(trig=combo["NOVA_TRIG"], lock=combo["NOVA_LOCK"])
            sizing = None
            if key == "F_204":
                sizing = M204.make_sizing_spec(frame, R=combo["NOVA_R"], cap=combo["NOVA_CAP"],
                                               halve_vr=combo["NOVA_HALVE"])
            kw = {}
            if key == "F_205":
                kw = dict(max_per=int(combo["NOVA_MAX_PER"]), cooldown_s=combo["NOVA_COOL_S"])
            stats, trades = C.simulate(frame, sig, atrf,
                                       exit_mode="dual" if (key == "F_197" and combo["NOVA_EXIT"] == "dual") else "std",
                                       dual=dual, sizing=sizing, bar_secs=bar_secs, **kw)
            row = {k: combo[k] for k in axis_names}
            row.update({"symbol": sym, "net": round(stats["net"], 2),
                        "trades": stats["trades"], "win_pct": stats["win_pct"],
                        "gross": round(stats["gross"], 2), "costs": round(stats["costs"], 2),
                        "risk_total": round(stats["risk_total"], 2)})
            all_rows.append(row)
            for t in C.trade_rows(sym, key, trades):
                t2 = {k: combo[k] for k in axis_names}
                t2.update(t)
                sym_trades.append(t2)
        sym_df = pd.DataFrame([r for r in all_rows if r["symbol"] == sym])
        write_csv(sym_df, exp_dir / sym / "sweep_train.csv")   # مسار تدقيق مستقل (رمز واحد)
        write_csv(pd.DataFrame(sym_trades), exp_dir / sym / "trades.csv")
        print(f"  {sym}: {len(combos)} تركيبة — جاهز")

    train = pd.DataFrame(all_rows)
    write_csv(train, exp_dir / "all_symbols.csv")   # مرجعي غير مُدقَّق (تجميع الرموز الأربعة)

    # env dump (بروتوكول D-0013)
    import platform
    ver = (f"pandas {pd.__version__} numpy {np.__version__} python {platform.python_version()}\n")
    env = (f"# {pd.Timestamp.utcnow().isoformat()}\n{ver}"
           f"window={start}→{end} tf={tf} symbols={','.join(symbols)}\n"
           f"cost_per_side={C.COST_PER_SIDE} (fee {C.FEE_PER_SIDE} + slip {C.SLIP_PER_SIDE})\n"
           f"exit_std: stop={C.STOP_ATR}×ATR14 tp={C.TP_ATR}×ATR14 · notional={C.BASE_NOTIONAL}\n")
    (exp_dir / "env_dump.txt").write_text(env, encoding="utf-8")

    # ملخص
    if train.empty:
        (exp_dir / "summary.txt").write_text(f"# {key}: لا بيانات — لا صفوف\n", encoding="utf-8")
        return train
    top = train.sort_values("net", ascending=False).head(8)
    summ = [f"# {key} — {start}→{end} — {len(symbols)} رموز — {len(combos)} تركيبة — {time.time()-t0:.1f} ث"]
    for _, r in top.iterrows():
        summ.append(f"  net={r['net']:>10.2f}$ trades={int(r['trades']):>4} win={r['win_pct']:>5.1f}% "
                    + " ".join(f"{k}={r[k]}" for k in axis_names) + f" | {r['symbol']}")
    (exp_dir / "summary.txt").write_text("\n".join(summ) + "\n", encoding="utf-8")
    print(f"  {key}: {len(train)} سطر — أفضل: {top.iloc[0]['net']}${' '}({top.iloc[0]['symbol']})")
    return train


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="BTCUSDT,BNBUSDT,LINKUSDT,SOLUSDT")
    ap.add_argument("--start", default="2026-06-01")
    ap.add_argument("--end", default="2026-09-01")
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="research/hyp_lab_out/L0004")
    ap.add_argument("--exp", default=",".join(EXP.keys()))
    a = ap.parse_args()
    symbols = [s.strip() for s in a.symbols.split(",") if s.strip()]
    exps = [e.strip() for e in a.exp.split(",") if e.strip()]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"hyp_lab L0004 — {len(exps)} تجربة × {len(symbols)} رمز — {a.start}→{a.end}")
    for key in exps:
        print(f"[{key}]")
        run_exp(key, symbols, Path(a.data), a.start, a.end, out)
    print("انتهت الجولة.")


if __name__ == "__main__":
    main()
