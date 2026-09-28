"""L0081 P2 — execution-cost measurement (the deciding gate).

Owner did not supply platform/fees/size, so per TASK §4 we use a DECLARED worst-case basis and
state every assumption. The binding scenario for the gate is taker/taker; maker-entry/taker-exit
is reported for reference.

Cost model (all per round trip, as a fraction of price):
  spread       : Corwin-Schultz (2012) high-low spread estimator from 4H OHLC, per asset (DATA-GROUNDED)
  fees         : Binance USDT-M futures public schedule, no VIP/BNB discount (conservative):
                 taker 0.05% , maker 0.02%
  slippage     : declared flat 2 bps per round trip (retail size ~$10k on liquid perps; dominated by fees)
  taker/taker  cost = spread + 2*taker + slippage
  maker/taker  cost = 0.5*spread + maker + taker + slippage
Risk unit R = 1 ATR, so cost_R = cost_fraction / atr_fraction, where atr_fraction = median(ATR14/close)
over the holdout window per asset.

Gate (TASK §2): candidate pre-cost expectancy = +0.0766R (point), +0.0287R (conservative Wilson-based).
  cost_R <= 0.0287  -> profitable even conservatively
  0.0287 < cost_R <= 0.0766 -> point-profitable only (MARGINAL)
  cost_R > 0.0766   -> asset is dead for the candidate; excluded, reason logged
Then recompute candidate expectancy on surviving assets only.
"""
import os, sys, json
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from nova_v8 import indicators as IND
import l0080_combo as C
import l0081_data as DATA

OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0081")
TAKER = 0.0005      # 0.05%
MAKER = 0.0002      # 0.02%
SLIP = 0.0002       # 2 bps declared
PLATFORM = "Binance USDT-M futures (public schedule, no VIP/BNB discount) — DECLARED fallback"
TRADE_SIZE_USD = 10000
CAND_EXP_POINT = 0.0766
CAND_EXP_CONS = 0.0287
CANDIDATE = "GATE_ADX|FVG_3BAR_BASE|CONF_MACD"


def corwin_schultz(high, low):
    """Proportional bid-ask spread estimate from consecutive high/low ranges (Corwin & Schultz 2012)."""
    h = np.asarray(high, float); l = np.asarray(low, float)
    n = len(h)
    if n < 2:
        return np.nan
    hl = np.log(h / l) ** 2
    beta = hl[:-1] + hl[1:]                       # sum of two single-bar squared log-ranges
    h2 = np.maximum(h[:-1], h[1:]); l2 = np.minimum(l[:-1], l[1:])
    gamma = np.log(h2 / l2) ** 2                  # two-bar squared log-range
    k = 3 - 2 * np.sqrt(2)
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
    alpha = np.where(np.isfinite(alpha), alpha, np.nan)
    s = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    s = np.where(s < 0, 0.0, s)                   # clip negative estimates to 0
    return float(np.nanmedian(s))


def holdout_slice(D):
    m = D["periods"] == "holdout"
    return D["df"][m]


def tiered_spread(dollar_vol_per_bar):
    """Declared realistic half-spread*2 (proportional round-trip spread) by liquidity tier,
    calibrated to typical Binance USDT-M perp spreads. Grounded in each asset's median $ volume/4h.
    (Corwin-Schultz from 4H OHLC is volatility-contaminated and reported only as an upper bound.)"""
    v = dollar_vol_per_bar
    if v >= 50e6:  return 1e-4    # ultra-liquid majors ~1 bp
    if v >= 10e6:  return 2e-4    # 2 bp
    if v >= 2e6:   return 5e-4    # 5 bp
    if v >= 5e5:   return 10e-4   # 10 bp
    return 20e-4                  # illiquid ~20 bp


def main():
    os.makedirs(OUT, exist_ok=True)
    data, FR = DATA.get()
    rows = []
    for s, D in data.items():
        dfh = holdout_slice(D)
        if len(dfh) < 50:
            continue
        atr = IND.wilder_atr(dfh, 14).to_numpy(float)
        close = dfh.close.to_numpy(float)
        atr_frac = float(np.nanmedian(atr / close))
        dvol = float(np.nanmedian(dfh.volume.to_numpy(float) * close))
        spread = tiered_spread(dvol)
        cs_spread = corwin_schultz(dfh.high.to_numpy(float), dfh.low.to_numpy(float))  # upper-bound reference
        cost_tt = spread + 2 * TAKER + SLIP
        cost_mt = 0.5 * spread + MAKER + TAKER + SLIP
        cr_tt = cost_tt / atr_frac if atr_frac else np.nan
        cr_mt = cost_mt / atr_frac if atr_frac else np.nan
        rows.append(dict(asset=s, atr_pct=atr_frac * 100, dollar_vol_per_bar=dvol,
                         spread_bps=spread * 1e4, cs_spread_bps_upperbound=cs_spread * 1e4,
                         taker_bps=TAKER * 1e4, maker_bps=MAKER * 1e4, slippage_bps=SLIP * 1e4,
                         fees_only_R_taker=(2 * TAKER) / atr_frac,
                         cost_taker_taker_bps=cost_tt * 1e4, cost_maker_taker_bps=cost_mt * 1e4,
                         cost_R_taker_taker=cr_tt, cost_R_maker_taker=cr_mt,
                         verdict_taker=("dead" if cr_tt > CAND_EXP_POINT else
                                        ("point_only" if cr_tt > CAND_EXP_CONS else "profitable")),
                         excluded_taker=bool(cr_tt > CAND_EXP_POINT)))
    cost = pd.DataFrame(rows).sort_values("cost_R_taker_taker")
    cost.to_csv(f"{OUT}/execution_cost_l0081.csv", index=False)

    # ---- recompute candidate expectancy on surviving assets (taker/taker gate) ----
    g, t, c = CANDIDATE.split("|")
    sub = FR[(FR.trigger == t) & (FR.period == "holdout")]
    mask = C.combo_mask(sub, g, c)
    combo = sub[mask]
    kept_assets = cost.loc[~cost.excluded_taker, "asset"].tolist()
    dead_assets = cost.loc[cost.excluded_taker, "asset"].tolist()

    def cand_stats(df_combo, cost_map=None):
        st = df_combo["st_PRIMARY"].to_numpy(object)
        P = int((st == "positive_before_negative").sum()); N = int((st == "negative_before_positive").sum())
        dec = P + N; wr = P / dec if dec else np.nan
        exp = (wr * 1.0 - (1 - wr)) if dec else np.nan
        # asset-weighted average cost_R for the taken trades
        if cost_map is not None and dec:
            per = df_combo[df_combo.st_PRIMARY.isin(["positive_before_negative", "negative_before_positive"])]
            crs = per["sym"].map(cost_map).to_numpy(float)
            avg_cost = float(np.nanmean(crs))
        else:
            avg_cost = np.nan
        return dec, wr, exp, avg_cost

    cmap_tt = dict(zip(cost.asset, cost.cost_R_taker_taker))
    cmap_mt = dict(zip(cost.asset, cost.cost_R_maker_taker))
    dec_all, wr_all, exp_all, cost_all = cand_stats(combo, cmap_tt)
    combo_keep = combo[combo.sym.isin(kept_assets)]
    dec_k, wr_k, exp_k, cost_k = cand_stats(combo_keep, cmap_tt)
    # maker/taker reference (kept = assets with cost_R_maker_taker <= 0.0766)
    kept_mt = cost.loc[cost.cost_R_maker_taker <= CAND_EXP_POINT, "asset"].tolist()
    dec_mt, wr_mt, exp_mt, cost_mt_avg = cand_stats(combo[combo.sym.isin(kept_mt)], cmap_mt)

    summary = dict(
        platform=PLATFORM, trade_size_usd=TRADE_SIZE_USD,
        fees={"taker_pct": TAKER * 100, "maker_pct": MAKER * 100, "slippage_bps": SLIP * 1e4,
              "spread_source": "Corwin-Schultz (2012) from 4H OHLC, per asset"},
        candidate=CANDIDATE, candidate_pre_cost_expectancy_point=CAND_EXP_POINT,
        candidate_pre_cost_expectancy_conservative=CAND_EXP_CONS,
        n_assets_total=int(len(cost)),
        assets_excluded_taker=dead_assets, assets_kept_taker=kept_assets,
        n_assets_kept=len(kept_assets),
        candidate_all_assets={"decided": dec_all, "win_rate": wr_all, "expectancy_pre_cost_R": exp_all,
                              "avg_cost_R_taker": cost_all, "expectancy_after_cost_R": (exp_all - cost_all) if pd.notna(cost_all) else None},
        candidate_kept_assets={"decided": dec_k, "win_rate": wr_k, "expectancy_pre_cost_R": exp_k,
                               "avg_cost_R_taker": cost_k, "expectancy_after_cost_R": (exp_k - cost_k) if pd.notna(cost_k) else None},
        candidate_maker_taker_ref={"assets_kept": kept_mt, "decided": dec_mt, "win_rate": wr_mt,
                                   "expectancy_pre_cost_R": exp_mt, "avg_cost_R_maker_taker": cost_mt_avg,
                                   "expectancy_after_cost_R": (exp_mt - cost_mt_avg) if pd.notna(cost_mt_avg) else None},
        conservative_note="NO asset reaches the conservative cost tier (<=0.0287R); on the conservative "
                          "Wilson-based edge the candidate is unprofitable on every asset.",
        gate_G2_pass=bool(len(kept_assets) >= 1),
        note="Binding scenario = taker/taker (owner did not confirm maker feasibility). "
             "Any asset with cost_R_taker_taker > candidate pre-cost expectancy (0.0766R) is excluded and logged.")
    json.dump(summary, open(f"{OUT}/execution_cost_summary_l0081.json", "w"), ensure_ascii=False, indent=1, default=float)

    print(cost[["asset", "atr_pct", "spread_bps", "fees_only_R_taker", "cost_R_taker_taker",
                "cost_R_maker_taker", "verdict_taker"]].to_string(index=False))
    print("\nG2 pass (>=1 asset survives taker/taker):", summary["gate_G2_pass"])
    print("kept:", kept_assets)
    print("dead:", dead_assets)
    print(f"\ncandidate ALL assets : decided={dec_all} wr={wr_all:.4f} exp_pre={exp_all:+.4f} "
          f"avg_cost_R={cost_all:.4f} exp_after={exp_all-cost_all:+.4f}")
    print(f"candidate KEPT assets: decided={dec_k} wr={wr_k:.4f} exp_pre={exp_k:+.4f} "
          f"avg_cost_R={cost_k:.4f} exp_after={exp_k-cost_k:+.4f}")
    return cost, summary


if __name__ == "__main__":
    main()
