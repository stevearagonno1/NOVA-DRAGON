"""L0074 — classic indicators as CONFIRMATION of structure signals (MSS/FVG/SFP).

Signals only: no trade management, no stops, no costs, no capital, no live.
Structure signals + outcome engine are reused unchanged from l0073_study (same
MSS/FVG/SFP, same outcome_arrays, same summarize/wilson). Classic confirmation
conditions come from nova_v8.triggers.build_triggers (level, not edge) computed
on nova_v8.indicators.compute_matrix. Rules locked in preregistration_l0074.json.
"""
import os, sys, json, hashlib
import numpy as np, pandas as pd

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import l0073_study as L                       # structure signals + outcome engine (unchanged)
from nova_v8 import indicators as IND, triggers as TR

SYMS = L.SYMS
COMP = ["MSS", "FVG", "SFP"]
CLASSIC = ["RSI", "MACD", "Bollinger", "EMA", "ADX", "Stochastic", "OBV"]
CFG = L.CFG                                   # {"base": (1,1,6), "sens": (2,1,18)}
CONSENSUS = [2, 3]
SEED = 74
NDRAW = 1000
OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0074")

# outcome-state integer codes for fast random control
CODE = {"positive_before_negative": 0, "negative_before_positive": 1,
        "neither_within_window": 2, "ambiguous_same_bar": 3}


def classic_conditions(df):
    """{(name, dir): bool ndarray} for the 7 locked classic indicators, LEVEL (not edge).
    Uses compute_matrix columns + build_triggers conditions unchanged."""
    m = IND.compute_matrix(df)
    trig = TR.build_triggers(m)
    cond = {}
    for name in CLASSIC:
        cond[(name, 1)] = trig["long"][name].fillna(False).to_numpy(bool)
        cond[(name, -1)] = trig["short"][name].fillna(False).to_numpy(bool)
    return cond


def main():
    os.makedirs(OUT, exist_ok=True)
    data = {}
    for s in SYMS:
        df = L.load(s)
        F, atr = L.fires(df)                  # structure fires (components + combos) — we use components
        cond = classic_conditions(df)
        # outcome arrays per bar for every (config, direction)
        OA = {(cn, d): L.outcome_arrays(df, atr, d, tg, ad, H)
              for cn, (tg, ad, H) in CFG.items() for d in (1, -1)}
        data[s] = dict(df=df, F=F, atr=atr, cond=cond, OA=OA, n=len(df))

    # ---------- raw structure signal list (must equal L0073 components) ----------
    sig_rows = []
    for s, D in data.items():
        df, F, atr, cond = D["df"], D["F"], D["atr"], D["cond"]
        for comp in COMP:
            for d in (1, -1):
                for i in np.flatnonzero(F[(comp, d)]):
                    i = int(i)
                    row = dict(sym=s, bar=i, time=str(df.index[i]), structure=comp,
                               direction="long" if d == 1 else "short",
                               close=float(df.close.iat[i]), atr14=float(atr[i]))
                    for name in CLASSIC:
                        row[f"same_{name}"] = bool(cond[(name, d)][i])
                        row[f"lag_{name}"] = bool(cond[(name, d)][i + 1]) if i + 1 < D["n"] else False
                    row["consensus_same"] = int(sum(cond[(name, d)][i] for name in CLASSIC))
                    sig_rows.append(row)
    S = pd.DataFrame(sig_rows).sort_values(["sym", "bar", "structure", "direction"]).reset_index(drop=True)
    sig_hash_before = hashlib.sha256(
        S[["sym", "bar", "time", "structure", "direction", "close", "atr14"]].to_csv(index=False).encode()).hexdigest()
    S.to_csv(f"{OUT}/signals_l0074.csv", index=False)

    # ---------- raw baseline outcomes (= L0073 component outcomes) ----------
    raw_rows = []
    for s, D in data.items():
        df = D["df"]
        for comp in COMP:
            for d in (1, -1):
                dirn = "long" if d == 1 else "short"
                for cn in CFG:
                    st, ttt, mfe, mae = D["OA"][(cn, d)]
                    for i in np.flatnonzero(D["F"][(comp, d)]):
                        i = int(i)
                        raw_rows.append(dict(sym=s, bar=i, time=str(df.index[i]), structure=comp,
                                             direction=dirn, config=cn, state=st[i],
                                             bars_to_target=ttt[i], mfe=mfe[i], mae=mae[i]))
    RAW = pd.DataFrame(raw_rows)

    # ---------- confirmed outcomes (same-bar, one-bar-lag, consensus) ----------
    conf_rows = []
    for s, D in data.items():
        df, cond, n = D["df"], D["cond"], D["n"]
        for comp in COMP:
            for d in (1, -1):
                dirn = "long" if d == 1 else "short"
                fires = [int(i) for i in np.flatnonzero(D["F"][(comp, d)])]
                for cn in CFG:
                    st, ttt, mfe, mae = D["OA"][(cn, d)]
                    for i in fires:
                        # same-bar: decision at i
                        for name in CLASSIC:
                            if cond[(name, d)][i]:
                                conf_rows.append(dict(sym=s, bar=i, decision_bar=i, time=str(df.index[i]),
                                    structure=comp, classic=name, direction=dirn, path="same", config=cn,
                                    state=st[i], bars_to_target=ttt[i], mfe=mfe[i], mae=mae[i]))
                        # one-bar-lag: classic at i+1, decision at i+1, window starts i+2
                        if i + 1 < n:
                            for name in CLASSIC:
                                if cond[(name, d)][i + 1]:
                                    conf_rows.append(dict(sym=s, bar=i, decision_bar=i + 1, time=str(df.index[i]),
                                        structure=comp, classic=name, direction=dirn, path="lag", config=cn,
                                        state=st[i + 1], bars_to_target=ttt[i + 1], mfe=mfe[i + 1], mae=mae[i + 1]))
                        # consensus at i (same-bar)
                        cc = sum(cond[(name, d)][i] for name in CLASSIC)
                        for thr in CONSENSUS:
                            if cc >= thr:
                                conf_rows.append(dict(sym=s, bar=i, decision_bar=i, time=str(df.index[i]),
                                    structure=comp, classic=f"CONSENSUS{thr}", direction=dirn, path="consensus", config=cn,
                                    state=st[i], bars_to_target=ttt[i], mfe=mfe[i], mae=mae[i]))
    CONF = pd.DataFrame(conf_rows)
    CONF.to_csv(f"{OUT}/outcomes_l0074.csv", index=False)

    # ---------- summaries ----------
    def summ_block(g):
        return L.summarize(g)

    # baseline per (config, structure, [direction/all])
    base_all = {}   # (config, structure) -> summary dict (both directions)
    base_dir = {}   # (config, structure, dirn)
    base_asset = {} # (config, structure, sym) -> summary (both directions per asset)
    for (cn, comp), g in RAW.groupby(["config", "structure"]):
        base_all[(cn, comp)] = summ_block(g)
    for (cn, comp, dirn), g in RAW.groupby(["config", "structure", "direction"]):
        base_dir[(cn, comp, dirn)] = summ_block(g)
    for (cn, comp, sym), g in RAW.groupby(["config", "structure", "sym"]):
        base_asset[(cn, comp, sym)] = summ_block(g)

    rows = []
    # baseline rows
    for (cn, comp), sm in base_all.items():
        rows.append(dict(config=cn, structure=comp, classic="(raw structure)", path="raw",
                         direction="all", level="all", **sm))
    for (cn, comp, dirn), sm in base_dir.items():
        rows.append(dict(config=cn, structure=comp, classic="(raw structure)", path="raw",
                         direction=dirn, level="direction", **sm))
    # confirmed rows: all-directions, per-direction
    for keys, lvl in [(["config", "structure", "classic", "path"], "all"),
                      (["config", "structure", "classic", "path", "direction"], "direction")]:
        for k, g in CONF.groupby(keys):
            k = k if isinstance(k, tuple) else (k,)
            d = dict(zip(keys, k))
            comp, cn = d["structure"], d["config"]
            sm = summ_block(g)
            base = base_all.get((cn, comp)) if lvl == "all" else base_dir.get((cn, comp, d["direction"]))
            raw_acc = base["directional_accuracy"]; raw_valid = base["valid"]
            gain = sm["directional_accuracy"] - raw_acc if pd.notna(sm["directional_accuracy"]) and pd.notna(raw_acc) else np.nan
            cov = sm["valid"] / raw_valid if raw_valid else np.nan
            d.setdefault("direction", "all")
            rows.append(dict(**d, level=lvl,
                             raw_structure_dir_acc=raw_acc, raw_structure_valid=raw_valid,
                             accuracy_gain=gain, coverage=cov, rejection_rate=(1 - cov) if pd.notna(cov) else np.nan, **sm))
    # ensure every one of the 21 pairs is present at level=all for same & lag paths (even if 0 confirmed)
    EMPTY = dict(signals=0, valid=0, positive_before_negative=0, negative_before_positive=0,
                 neither_within_window=0, ambiguous_same_bar=0, invalid=0, hit_rate_all=np.nan,
                 hit_all_ci_lo=np.nan, hit_all_ci_hi=np.nan, directional_accuracy=np.nan,
                 dir_ci_lo=np.nan, dir_ci_hi=np.nan, ambiguous_rate=np.nan, neither_rate=np.nan,
                 ttt_mean=np.nan, ttt_median=np.nan, ttt_q1=np.nan, ttt_q3=np.nan,
                 mfe_mean=np.nan, mfe_median=np.nan, mae_mean=np.nan, mae_median=np.nan)
    present = {(r["config"], r["structure"], r["classic"], r["path"]) for r in rows if r.get("level") == "all"}
    for cn in CFG:
        for comp in COMP:
            for name in CLASSIC:
                for path in ("same", "lag"):
                    if (cn, comp, name, path) not in present:
                        base = base_all.get((cn, comp))
                        rows.append(dict(config=cn, structure=comp, classic=name, path=path, direction="all", level="all",
                                         raw_structure_dir_acc=base["directional_accuracy"], raw_structure_valid=base["valid"],
                                         accuracy_gain=np.nan, coverage=0.0, rejection_rate=1.0, **EMPTY))
    SU = pd.DataFrame(rows)
    SU.to_csv(f"{OUT}/summary_l0074.csv", index=False)

    # per-asset confirmed (for concentration) — same-bar base only
    pa_rows = []
    sub = CONF[(CONF.path == "same") & (CONF.config == "base")]
    for (comp, name, sym), g in sub.groupby(["structure", "classic", "sym"]):
        sm = summ_block(g)
        b = base_asset.get(("base", comp, sym), None)
        raw_acc = b["directional_accuracy"] if b else np.nan
        pa_rows.append(dict(structure=comp, classic=name, sym=sym,
                            confirmed_dir_acc=sm["directional_accuracy"], decided=sm["positive_before_negative"] + sm["negative_before_positive"],
                            raw_dir_acc=raw_acc))
    PA = pd.DataFrame(pa_rows)
    PA.to_csv(f"{OUT}/concentration_by_asset_l0074.csv", index=False)

    # per-pair concentration of the improvement (share carried by the single most contributing asset)
    conc_rows = []
    for (comp, name), g in PA.groupby(["structure", "classic"]):
        contrib = ((g.confirmed_dir_acc - g.raw_dir_acc) * g.decided)
        pos = contrib[contrib > 0]
        total_pos = float(pos.sum())
        top_share = float(pos.max() / total_pos) if total_pos > 0 else np.nan
        top_asset = g.loc[contrib.idxmax(), "sym"] if len(contrib) else None
        conc_rows.append(dict(structure=comp, classic=name, total_positive_contrib=total_pos,
                              top_asset=top_asset, top_asset_share=top_share,
                              concentration_ok=bool(np.isnan(top_share) or top_share <= 0.35)))
    CONC = pd.DataFrame(conc_rows)
    CONC.to_csv(f"{OUT}/concentration_l0074.csv", index=False)

    # ---------- random control (same-bar, base config) ----------
    rng = np.random.default_rng(SEED)
    rc_rows = []
    for comp in COMP:
        for name in CLASSIC:
            for scope, dirs in [("all", (1, -1)), ("long", (1,)), ("short", (-1,))]:
                # gather per-sym B outcome codes and real confirmed count
                per_sym = []
                P_act = D_act = V_act = 0
                for s, Dd in data.items():
                    st = Dd["OA"][("base", 1)][0]  # placeholder; recomputed per dir below
                    for d in dirs:
                        stc = Dd["OA"][("base", d)][0]
                        codes_all = np.array([CODE.get(x, -1) for x in stc])
                        Bf = np.flatnonzero(Dd["F"][(comp, d)])
                        Bf = Bf[codes_all[Bf] >= 0]                       # valid-outcome structure bars only
                        if len(Bf) == 0:
                            continue
                        real_mask = Dd["cond"][(name, d)][Bf]
                        real_codes = codes_all[Bf][real_mask]
                        k = int(real_mask.sum())
                        Bcodes = codes_all[Bf]
                        per_sym.append((Bcodes, k))
                        P_act += int((real_codes == 0).sum())
                        D_act += int(((real_codes == 0) | (real_codes == 1)).sum())
                        V_act += int((real_codes >= 0).sum())
                if V_act == 0 or D_act == 0:
                    rc_rows.append(dict(structure=comp, classic=name, scope=scope, confirmed=int(V_act),
                                        actual_hit_rate_all=np.nan, actual_dir_acc=np.nan,
                                        rand_hit_mean=np.nan, rand_dir_mean=np.nan, rand_dir_median=np.nan,
                                        rand_dir_p5=np.nan, rand_dir_p95=np.nan, dir_pct_rank=np.nan, hit_pct_rank=np.nan))
                    continue
                act_hit = P_act / V_act; act_dir = P_act / D_act
                P = np.zeros(NDRAW); Dd_ = np.zeros(NDRAW); V = np.zeros(NDRAW)
                for Bcodes, k in per_sym:
                    if k == 0:
                        continue
                    for t in range(NDRAW):
                        pick = Bcodes[rng.choice(len(Bcodes), k, replace=False)]
                        P[t] += (pick == 0).sum(); Dd_[t] += ((pick == 0) | (pick == 1)).sum(); V[t] += (pick >= 0).sum()
                hit = P / np.maximum(V, 1); dacc = P / np.maximum(Dd_, 1)
                rc_rows.append(dict(structure=comp, classic=name, scope=scope, confirmed=int(V_act),
                    actual_hit_rate_all=act_hit, actual_dir_acc=act_dir,
                    rand_hit_mean=float(hit.mean()), rand_dir_mean=float(dacc.mean()), rand_dir_median=float(np.median(dacc)),
                    rand_dir_p5=float(np.percentile(dacc, 5)), rand_dir_p95=float(np.percentile(dacc, 95)),
                    dir_pct_rank=float((dacc < act_dir).mean()), hit_pct_rank=float((hit < act_hit).mean())))
    RC = pd.DataFrame(rc_rows)
    RC.to_csv(f"{OUT}/random_control_l0074.csv", index=False)

    sig_hash_after = hashlib.sha256(
        S[["sym", "bar", "time", "structure", "direction", "close", "atr14"]].to_csv(index=False).encode()).hexdigest()

    return dict(data=data, S=S, RAW=RAW, CONF=CONF, SU=SU, PA=PA, RC=RC,
                base_all=base_all, base_dir=base_dir, base_asset=base_asset,
                sig_hash_before=sig_hash_before, sig_hash_after=sig_hash_after)


if __name__ == "__main__":
    main()
