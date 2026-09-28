"""L0081 P4 — preregistered confirmation of the SINGLE frozen candidate on NEW assets (Option A).

Cross-sectional out-of-sample: assets never used in L0072-L0080, SAME window 2024-09-04..2026-08-30,
frozen definitions applied verbatim (no re-tuning). This is the decisive gate G4.

Candidate (frozen in selection_l0081.json, committed before this read): GATE_ADX|FVG_3BAR_BASE|CONF_MACD
  gate = ADXDI_20_22 active dir-matched ; trigger = FVG_3BAR_BASE edge ; conf = MACD_8_21_5 dir-matched
  target = PRIMARY +1 ATR before -1 ATR within 6 bars, RR=1.
"""
import os, sys, json, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from nova_v8 import indicators as IND
import l0073_study as L
import l0079_variants as V
import stats_core as SC
import l0081_p2_cost as P2

OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0081")
NEWCACHE = os.path.expanduser("~/l007x_4h/newassets")
WIN_START = pd.Timestamp("2024-09-04", tz="UTC")
WIN_END = pd.Timestamp("2026-08-31", tz="UTC")
TGT = (1.0, 1.0, 6)   # PRIMARY
RR = 1.0
H = 6


def load_new(sym):
    df = pd.read_parquet(f"{NEWCACHE}/{sym}USDT_4h.parquet")
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    return df


def candidate_signals(df):
    """Return arrays: bar indices (in df) of candidate fires within the eval window, with state & dir."""
    ed, atr = V.structure_edges(df)
    cond = V.indicator_levels(df)
    OA = {d: L.outcome_arrays(df, atr, d, *TGT) for d in (1, -1)}
    times = df.index
    bars = []; states = []; dirs = []
    for d in (1, -1):
        trig = ed[("FVG_3BAR_BASE", d)]
        gate = cond[("ADXDI_20_22", d)]
        conf = cond[("MACD_8_21_5", d)]
        fire = trig & gate & conf
        for i in np.flatnonzero(fire):
            i = int(i)
            if not (WIN_START <= times[i] < WIN_END):
                continue
            bars.append(i); states.append(OA[d][0][i]); dirs.append(d)
    return np.array(bars, int), np.array(states, object), np.array(dirs, int), df


def wr_exp(states):
    P = int((states == "positive_before_negative").sum())
    N = int((states == "negative_before_positive").sum())
    dec = P + N
    wr = P / dec if dec else np.nan
    exp = (2 * wr - 1) if dec else np.nan
    return P, N, dec, wr, exp


def cost_for(df):
    dfh = df[(df.index >= WIN_START) & (df.index < WIN_END)]
    atr = IND.wilder_atr(dfh, 14).to_numpy(float); close = dfh.close.to_numpy(float)
    atr_frac = float(np.nanmedian(atr / close))
    dvol = float(np.nanmedian(dfh.volume.to_numpy(float) * close))
    spread = P2.tiered_spread(dvol)
    cost_tt = (spread + 2 * P2.TAKER + P2.SLIP) / atr_frac
    cost_mt = (0.5 * spread + P2.MAKER + P2.TAKER + P2.SLIP) / atr_frac
    return atr_frac, dvol, spread, cost_tt, cost_mt


def main():
    os.makedirs(OUT, exist_ok=True)
    sel = json.load(open(f"{OUT}/selection_l0081.json"))
    cand = sel["p4_candidate_frozen"]
    assert cand == "GATE_ADX|FVG_3BAR_BASE|CONF_MACD", cand
    syms = sorted(s.split("/")[-1].replace("USDT_4h.parquet", "")
                  for s in glob.glob(f"{NEWCACHE}/*USDT_4h.parquet"))
    per_rows = []
    all_states = []; per_series = []; costs_tt = []; costs_mt = []
    pos_dir_assets = 0; n_assets = 0
    for s in syms:
        df = load_new(s)
        if len(df) < 3000:
            print(f"skip {s}: only {len(df)} bars"); continue
        bars, states, dirs, dfr = candidate_signals(df)
        P, N, dec, wr, exp = wr_exp(states)
        if dec < 30:
            print(f"note {s}: only {dec} decided"); 
        atr_frac, dvol, spread, cost_tt, cost_mt = cost_for(df)
        costs_tt.append((dec, cost_tt)); costs_mt.append((dec, cost_mt))
        n = len(df)
        starts = bars; ends = np.minimum(bars + H, n - 1)
        per_series.append((starts, ends, n))
        all_states.append(states)
        if pd.notna(wr) and wr > 0.50:
            pos_dir_assets += 1
        n_assets += 1
        per_rows.append(dict(asset=s, decided=dec, wins=P, losses=N, win_rate=wr,
                             expectancy_pre_cost_R=exp, atr_pct=atr_frac * 100, cost_R_taker=cost_tt,
                             cost_R_maker=cost_mt, expectancy_after_taker_R=(exp - cost_tt) if pd.notna(exp) else np.nan))
    per = pd.DataFrame(per_rows)
    per.to_csv(f"{OUT}/confirmation_l0081.csv", index=False)

    # pooled
    states = np.concatenate(all_states)
    P, N, dec, wr, exp = wr_exp(states)
    Neff, Nlab, mu = SC.effective_n_multi(per_series)
    valid = len(states); neff_dec = Neff * (dec / valid) if valid else np.nan
    # trade-weighted average cost
    tot = sum(d for d, _ in costs_tt)
    avg_cost_tt = sum(d * c for d, c in costs_tt) / tot if tot else np.nan
    avg_cost_mt = sum(d * c for d, c in costs_mt) / tot if tot else np.nan
    exp_after_tt = exp - avg_cost_tt
    exp_after_mt = exp - avg_cost_mt
    breakeven_tt = (1 + avg_cost_tt) / 2
    lo_nom, _ = SC.wilson(P, dec)
    lo_eff, _ = SC.wilson_p(wr, neff_dec)

    # locked success criteria
    crit = {
        "N_eff_ge_200": bool(neff_dec >= 200),
        "wilson_lo_neff_above_breakeven_after_cost": bool(pd.notna(lo_eff) and lo_eff > breakeven_tt),
        "expectancy_after_measured_cost_pos": bool(pd.notna(exp_after_tt) and exp_after_tt > 0),
        "positive_direction_majority_assets": bool(pos_dir_assets > n_assets / 2),
    }
    g4_pass = all(crit.values())

    result = dict(
        method="Option A cross-sectional OOS (new assets, same window, frozen defs verbatim)",
        candidate=cand, new_assets=syms, n_assets=n_assets,
        window=[str(WIN_START.date()), str(WIN_END.date())],
        pooled=dict(decided=dec, wins=P, losses=N, valid=valid, win_rate=wr, expectancy_pre_cost_R=exp,
                    concurrency=(Nlab / Neff) if Neff else None, average_uniqueness=mu, N_eff=neff_dec,
                    wilson_lo_nominal=lo_nom, wilson_lo_neff=lo_eff),
        cost=dict(avg_cost_R_taker=avg_cost_tt, avg_cost_R_maker=avg_cost_mt,
                  breakeven_winrate_after_taker=breakeven_tt),
        expectancy_after_cost=dict(taker=exp_after_tt, maker=exp_after_mt),
        positive_direction_assets=f"{pos_dir_assets}/{n_assets}",
        success_criteria=crit, G4_PASS=g4_pass,
        note="Binding scenario taker/taker. Single frozen candidate; read once.")
    json.dump(result, open(f"{OUT}/confirmation_summary_l0081.json", "w"), ensure_ascii=False, indent=1, default=float)

    print(per.to_string(index=False))
    print(f"\nPOOLED new assets: decided={dec} win_rate={wr:.4f} exp_pre={exp:+.4f}")
    print(f"N_eff={neff_dec:.0f} (conc {Nlab/Neff:.3f})  Wilson_lo_nominal={lo_nom:.4f}  Wilson_lo_neff={lo_eff:.4f}")
    print(f"avg cost taker={avg_cost_tt:.4f} -> breakeven wr={breakeven_tt:.4f} | exp_after_taker={exp_after_tt:+.4f}  exp_after_maker={exp_after_mt:+.4f}")
    print(f"positive-direction assets: {pos_dir_assets}/{n_assets}")
    print("\nSUCCESS CRITERIA:")
    for k, v in crit.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print(f"\n=== G4 {'PASS' if g4_pass else 'FAIL'} ===")


if __name__ == "__main__":
    main()
