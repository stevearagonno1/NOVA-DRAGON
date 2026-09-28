"""L0081 P1 — recompute L0079 variants and L0080 combos on the EFFECTIVE sample size.

Nothing here re-selects anything or re-runs the L0079/L0080 measurement pipelines; it only
reconstructs the (deterministic, identical) signal SET and augments each measured row with
concurrency / average_uniqueness / N_eff and a Wilson-lower bound recomputed on N_eff.
Outputs go to L0081/ ; the L0079/L0080 stored results are never modified.

Signal-set definitions are imported unchanged:
  - structure variants  : edges of the structure (both directions), per symbol  (l0079_variants.structure_edges)
  - indicator variants  : baseline-structure fires (MSS_L5|FVG_3BAR_BASE|SFP_LOOK20) where the
                          indicator LEVEL is true (both directions), per symbol
  - L0080 combos        : trigger fires filtered by gate & confirmation, per symbol

Label span for concurrency = [i, i+H] with H = 6 (the PRIMARY/base horizon). This is the
conservative choice (maximum holding window -> maximum overlap -> lowest N_eff).
"""
import os, sys, json
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import stats_core as SC
import l0080_combo as C
import l0079_variants as V
import l0081_data as DATA

OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0081")
H_PRIMARY = 6
DECODE = list(C.CODE)  # decided/valid state names


def neff_for_bars(bars_by_sym, n_by_sym):
    """bars_by_sym: {sym: np.array of signal bar indices}. Returns (N_eff, N_labels, mean_uniqueness).
    Concurrency/uniqueness computed PER SYMBOL (different symbols are independent return streams;
    cross-symbol overlap is never counted). Label span = [i, i+H_PRIMARY]."""
    per = []
    for s, bars in bars_by_sym.items():
        if len(bars) == 0:
            continue
        n = n_by_sym[s]
        starts = np.asarray(bars, int)
        ends = np.minimum(starts + H_PRIMARY, n - 1)
        per.append((starts, ends, n))
    return SC.effective_n_multi(per)  # (N_eff, N_labels, mean_uniqueness)


def wr_stats(states):
    st = np.asarray(states, object)
    P = int((st == "positive_before_negative").sum())
    N = int((st == "negative_before_positive").sum())
    dec = P + N
    valid = dec + int((st == "neither_within_window").sum()) + int((st == "ambiguous_same_bar").sum())
    wr = P / dec if dec else np.nan
    return P, N, dec, valid, wr


def recompute_l0080(data, FR):
    """All 27 combos on both periods with N_eff-based Wilson + retention + free-filter zone."""
    rows = []
    n_by_sym = {s: D["n"] for s, D in data.items()}
    for period in ("train", "holdout"):
        for g in C.GATES:
            for t in C.TRIGGERS:
                # trigger-alone concurrency for the free-filter bound
                sub_t = FR[(FR.trigger == t) & (FR.period == period)]
                trig_bars = {s: sub_t[sub_t.sym == s].bar.to_numpy(int) for s in data}
                Neff_trig, Ntrig, _ = neff_for_bars(trig_bars, n_by_sym)
                conc_trig = (Ntrig / Neff_trig) if Neff_trig else np.nan
                ffb = SC.free_filter_bound(conc_trig)
                trig_signals = int(sub_t.st_PRIMARY.isin(DECODE).sum())  # valid trigger signals
                for c in C.CONFS:
                    mask = C.combo_mask(sub_t, g, c)
                    combo = sub_t[mask]
                    bars_by = {s: combo[combo.sym == s].bar.to_numpy(int) for s in data}
                    Neff, Nlab, mu = neff_for_bars(bars_by, n_by_sym)
                    conc = (Nlab / Neff) if Neff else np.nan
                    P, N, dec, valid, wr = wr_stats(combo.st_PRIMARY.to_numpy(object))
                    # decided-scaled N_eff (Wilson uses decided count; scale N_eff by decided/valid share)
                    neff_dec = Neff * (dec / valid) if valid else np.nan
                    lo_nom, hi_nom = SC.wilson(P, dec) if dec else (np.nan, np.nan)
                    lo_eff, hi_eff = SC.wilson_p(wr, neff_dec) if (dec and neff_dec and neff_dec > 0) else (np.nan, np.nan)
                    retention = (valid / trig_signals) if trig_signals else np.nan
                    rows.append(dict(
                        combination=C.combo_id(g, t, c), gate=g, trigger=t, confirmation=c, period=period,
                        signals=int(len(combo)), decided=dec, valid=valid, win_rate=wr,
                        concurrency=conc, average_uniqueness=mu, N_eff=neff_dec, N_eff_valid=Neff,
                        wilson_lo_nominal=lo_nom, wilson_lo_neff=lo_eff,
                        breakeven_050=0.50, survives_neff=bool(pd.notna(lo_eff) and lo_eff > 0.50),
                        retention_fraction=retention, trigger_concurrency=conc_trig,
                        free_filter_bound=ffb, is_free_zone=bool(pd.notna(retention) and pd.notna(ffb) and retention >= ffb)))
    return pd.DataFrame(rows)


def recompute_l0079(data):
    """Structure variants + indicator variants on holdout (base config, RR=1), N_eff-corrected."""
    n_by_sym = {s: D["n"] for s, D in data.items()}
    # base-config outcome arrays already in D['OA'] under 'PRIMARY' key names? L0080 uses TARGETS names.
    rows = []
    period = "holdout"
    # ---- structure variants (edges) ----
    for vid in V.STRUCT_VARIANTS:
        bars_by = {}; states = []
        for s, D in data.items():
            sed = D["sed"]; b = []
            for d in (1, -1):
                if (vid, d) not in sed:
                    continue
                for i in np.flatnonzero(sed[(vid, d)]):
                    i = int(i)
                    if D["periods"][i] != period:
                        continue
                    b.append(i)
                    states.append(D["OA"][("PRIMARY", d)][0][i])
            bars_by[s] = np.array(b, int)
        rows.append(_neff_row(vid, "structure", bars_by, states, n_by_sym))
    # ---- indicator variants (baseline-structure fires filtered by level) ----
    baseline_vids = list(V.BASELINE.values())  # MSS_L5, FVG_3BAR_BASE, SFP_LOOK20
    ind_ids = V.indicator_ids()
    for vid in ind_ids:
        bars_by = {}; states = []
        for s, D in data.items():
            sed = D["sed"]; cond = V.indicator_levels(D["df"])  # recompute levels (deterministic)
            b = []
            for bv in baseline_vids:
                for d in (1, -1):
                    for i in np.flatnonzero(sed[(bv, d)]):
                        i = int(i)
                        if D["periods"][i] != period:
                            continue
                        if not cond[(vid, d)][i]:
                            continue
                        b.append(i)
                        states.append(D["OA"][("PRIMARY", d)][0][i])
            bars_by[s] = np.array(b, int)
        rows.append(_neff_row(vid, "indicator", bars_by, states, n_by_sym))
    return pd.DataFrame(rows)


def _neff_row(vid, track, bars_by, states, n_by_sym):
    Neff, Nlab, mu = neff_for_bars(bars_by, n_by_sym)
    conc = (Nlab / Neff) if Neff else np.nan
    P, N, dec, valid, wr = wr_stats(states)
    neff_dec = Neff * (dec / valid) if valid else np.nan
    lo_nom, _ = SC.wilson(P, dec) if dec else (np.nan, np.nan)
    lo_eff, _ = SC.wilson_p(wr, neff_dec) if (dec and neff_dec and neff_dec > 0) else (np.nan, np.nan)
    return dict(variant_id=vid, track=track, period="holdout", signals=int(sum(len(b) for b in bars_by.values())),
                decided=dec, valid=valid, win_rate=wr, directional_accuracy=wr,
                concurrency=conc, average_uniqueness=mu, N_eff=neff_dec, N_eff_valid=Neff,
                wilson_lo_nominal=lo_nom, wilson_lo_neff=lo_eff,
                survives_neff=bool(pd.notna(lo_eff) and lo_eff > 0.50))


def main():
    os.makedirs(OUT, exist_ok=True)
    print("loading data (cache) ...")
    data, FR = DATA.get()
    print("recompute L0080 ...")
    d80 = recompute_l0080(data, FR)
    d80.to_csv(f"{OUT}/neff_recompute_l0080.csv", index=False)
    print("recompute L0079 ...")
    d79 = recompute_l0079(data)
    d79.to_csv(f"{OUT}/neff_recompute_l0079.csv", index=False)
    # quick console echo of the four reference rows
    print("\n--- L0079 reference rows ---")
    print(d79[d79.variant_id.isin(["ADXDI_20_22", "FVG_3BAR_BASE"])]
          [["variant_id", "decided", "concurrency", "N_eff", "wilson_lo_nominal", "wilson_lo_neff", "survives_neff"]].to_string(index=False))
    print("\n--- L0080 reference rows (holdout) ---")
    ref = d80[(d80.period == "holdout") & (d80.combination.isin(
        ["GATE_ADX|FVG_3BAR_BASE|CONF_MACD", "GATE_EMA200|FVG_3BAR_BASE|CONF_NONE",
         "GATE_NONE|FVG_3BAR_BASE|CONF_NONE"]))]
    print(ref[["combination", "decided", "concurrency", "N_eff", "wilson_lo_nominal", "wilson_lo_neff",
               "retention_fraction", "free_filter_bound", "is_free_zone", "survives_neff"]].to_string(index=False))
    return d79, d80


if __name__ == "__main__":
    main()
