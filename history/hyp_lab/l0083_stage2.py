#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0083 · المرحلة 2/3 — المزج، مسح عتبة التدفق، المرشّحون خارج العينة، جدول الاضمحلال.
يعيد استعمال محرّك l0083_run. المحجوز يُقرأ مرة واحدة على مرشّحين معلنين مسبقًا من التدريب.
"""
from __future__ import annotations
import json, sys, pathlib
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import l0082_common as C  # noqa
import l0083_run as R  # noqa

OUT = R.OUT; ALT = R.ALT


def main():
    panel, settings = R.build_panel()
    pans = {k: R.period_slice(panel, v) for k, v in
            {"train": R.TRAIN, "holdout": R.HOLDOUT, "forward": R.FORWARD}.items()}
    base = {k: R.baseline_stats(pans[k])[0] for k in pans}

    # ---------- مسح عتبة التدفق × مستوى الحجم (جدول القسم 3) ----------
    sweep_rows = []
    for zlevel in (2.0, 2.5, 3.0):
        for flow in (None, 0.48, 0.50, 0.52):
            for k in ("train", "holdout"):
                p = pans[k]
                m = (p["vol_z"] >= zlevel)
                if flow is not None:
                    m = m & (p["ratio"] > flow)
                st = R.stat_setting(p[m], base[k])
                sweep_rows.append({"period": k, "vol_z": zlevel,
                                   "flow_gt": flow if flow else "none",
                                   **({} if st is None else st)})
    sweep = pd.DataFrame(sweep_rows)
    sweep.to_csv(OUT / "flow_threshold_sweep.csv", index=False)

    # ---------- المزج: مشغّل × شرط + ثلاثيات ----------
    combo_defs = {
        "VOL2.5": lambda p: p["vol_z"] >= 2.5,
        "VOL2.5+FLOW.50": lambda p: (p["vol_z"] >= 2.5) & (p["ratio"] > 0.50),
        "VOL2.5+FLOW.50+notH08": lambda p: (p["vol_z"] >= 2.5) & (p["ratio"] > 0.50) & (p["hour"] != 8),
        "VOL2.0+FLOW.52": lambda p: (p["vol_z"] >= 2.0) & (p["ratio"] > 0.52),
        "FLOWZ2.0": lambda p: p["ratio_z"] >= 2.0,
        "FLOWZ2.0+VOL2.0": lambda p: (p["ratio_z"] >= 2.0) & (p["vol_z"] >= 2.0),
        "RSIdeep_agg": lambda p: p["S_RSI21_xup_25"] | p["S_RSI14_xup_20"],
        "RSIdeep_state": lambda p: (R.I.rsi(p["close"].to_numpy(), 21) < 25),  # placeholder; غير مستعمل
    }
    combo_rows = []
    for name, fn in combo_defs.items():
        if name == "RSIdeep_state":
            continue
        for k in pans:
            p = pans[k]
            st = R.stat_setting(p[fn(p)], base[k])
            combo_rows.append({"combo": name, "period": k, **({} if st is None else st)})
    combos = pd.DataFrame(combo_rows)
    combos.to_csv(OUT / "combos_all.csv", index=False)
    combos.to_csv(ALT / "combos_all.csv", index=False)

    # ---------- المرشّحون معلنون من التدريب فقط، ثم يُقرأ المحجوز مرة واحدة ----------
    trig = pd.read_csv(OUT / "triggers_all.csv")
    elig = trig[(trig["train_n_eff"].fillna(0) >= 100)].copy()
    finalists = elig.sort_values("train_lift", ascending=False).head(4)["setting"].tolist()
    witnesses = ["Hammer", "FVG_single"]  # شاهد سالب + شاهد L0082
    stage3 = trig[trig["setting"].isin(finalists)][
        ["setting", "train_n_signals", "train_win_rate", "train_lift", "train_net_R"]]
    stage3.to_csv(OUT / "stage3_train.csv", index=False)
    stage3.to_csv(ALT / "stage3_train.csv", index=False)

    cols = ["setting", "train_lift", "holdout_lift", "forward_lift",
            "holdout_win_rate", "holdout_net_R", "holdout_pos_assets", "holdout_p_value"]
    fin = trig[trig["setting"].isin(finalists + witnesses)][cols]
    fin.to_csv(OUT / "finalists_oos.csv", index=False)
    fin.to_csv(ALT / "finalists_oos.csv", index=False)

    # ---------- جدول الاضمحلال ----------
    decay = trig[["setting", "train_n_signals", "train_lift", "holdout_lift", "forward_lift",
                  "train_net_R", "holdout_net_R", "forward_net_R"]].copy()
    decay.to_csv(OUT / "decay.csv", index=False)
    decay.to_csv(ALT / "decay.csv", index=False)

    # ---------- الخيوط الناجية ----------
    flow_survivor = trig[trig["setting"].str.startswith("TakerRatioZ")][
        ["setting", "train_lift", "holdout_lift", "forward_lift",
         "forward_pos_assets", "forward_tot_assets"]]

    out = {
        "finalists_preregistered": finalists,
        "finalists_oos": fin.round(3).to_dict("records"),
        "flow_threshold_monotone_train": sweep[sweep["period"] == "train"][
            ["vol_z", "flow_gt", "win_rate", "lift"]].round(3).to_dict("records"),
        "flow_survivor_takerZ": flow_survivor.round(3).to_dict("records"),
        "best_combo_holdout": combos[(combos["combo"] == "VOL2.5+FLOW.50+notH08")].round(3).to_dict("records"),
    }
    (OUT / "_stage2_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
