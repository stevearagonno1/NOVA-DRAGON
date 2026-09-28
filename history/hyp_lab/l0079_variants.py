"""L0079 parameter-variant screen. Two tracks (see preregistration_l0079.json):
  T1 STRUCTURE variants (MSS_L{3,5,8}, FVG_3BAR_BASE, SFP_LOOK{10,20,40}) measured on their
     OWN raw structure edge-signals.
  T2 INDICATOR variants measured as LEVEL confirmations layered on the 3 registered baseline
     structures (MSS_L5, FVG_3BAR, SFP_LOOK20), pooled — L0073/L0077 lineage.
Every variant also gets rise_start_coverage (its long signal preceding L0073 rise-starts).
No indicator combining. No trade management / fees. Registered math reused from L0072/L0077.

Usage:  python3 l0079_variants.py train    # screening on train + variant_catalog + freeze inputs
        python3 l0079_variants.py holdout  # OOS holdout + rise coverage + random control
"""
import os, sys, json
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import l0073_study as L
from nova_v8 import microstructure as M, indicators as IND

OUT = os.path.join(ROOT, "history/research/hyp_lab_out/L0079")
SYMS = L.SYMS
COMP = ["MSS", "FVG", "SFP"]
CFG = L.CFG                      # base (1,1,6), sens (2,1,18)
SEED = 79
NDRAW = 1000
EMBARGO_BARS = 18
PRE = 3                         # rise-start precedence window (bars at or before start)
DECIDED_MIN = 100
CODE = {"positive_before_negative": 0, "negative_before_positive": 1,
        "neither_within_window": 2, "ambiguous_same_bar": 3}

TRAIN_START = pd.Timestamp("2021-09-01", tz="UTC")
TRAIN_END = pd.Timestamp("2024-08-31", tz="UTC")
HOLDOUT_START = pd.Timestamp("2024-09-04", tz="UTC")
HOLDOUT_END = pd.Timestamp("2026-08-31", tz="UTC")


def period_of(ts):
    t = pd.Timestamp(ts)
    if TRAIN_START <= t < TRAIN_END:
        return "train"
    if HOLDOUT_START <= t < HOLDOUT_END:
        return "holdout"
    return "embargo"


# ----------------------------- math helpers (registered) -----------------------------
def _wilder(x, n):
    out = np.full(len(x), np.nan); s = np.nan
    for i, v in enumerate(x):
        if np.isnan(v):
            continue
        s = v if np.isnan(s) else s + (v - s) / n
        out[i] = s
    return out


def _rsi(c, n):
    d = np.diff(c, prepend=np.nan)
    up = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    up[0] = dn[0] = np.nan
    au, ad = _wilder(up, n), _wilder(dn, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + au / ad)
    return np.where(ad == 0, 100.0, r)


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def _sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


# ----------------------------- variant catalog -----------------------------
# each entry: variant_id -> dict(family, track, params, signal_definition)
def build_catalog():
    cat = {}

    def add(vid, family, track, params, sig):
        cat[vid] = dict(variant_id=vid, family=family, track=track, parameters=params,
                        source_file=("nova_v8/microstructure.py" if track == "structure"
                                     else "history/hyp_lab/l0079_variants.py"),
                        signal_definition=sig)

    # ---- structure (T1) ----
    for Lp in (3, 5, 8):
        add(f"MSS_L{Lp}", "MSS", "structure", {"L": Lp},
            f"mss_signal(L={Lp}) edge; long=+1 short=-1")
    add("FVG_3BAR_BASE", "FVG", "structure", {"bars": 3},
        "fvg_levels 3-bar imbalance; long=bull gap, short=bear gap")
    for lk in (10, 20, 40):
        add(f"SFP_LOOK{lk}", "SFP", "structure", {"look": lk},
            f"sfp_signal(look={lk}) with body-inside filter (long: l<prior_lo & body_lo>prior_lo & c>o)")
    # ---- indicators (T2) ----
    for n in (2, 7, 14):
        ob = 85 if n == 2 else 70; os_ = 15 if n == 2 else 30
        add(f"RSI{n}", "RSI", "indicator", {"length": n, "os": os_, "ob": ob},
            f"long: rsi({n})<{os_}; short: rsi({n})>{ob}")
    for f, s, sig in ((8, 21, 5), (12, 26, 9), (19, 39, 9)):
        add(f"MACD_{f}_{s}_{sig}", "MACD", "indicator", {"fast": f, "slow": s, "signal": sig},
            f"long: ema{f}-ema{s}>0; short: <0 (signal period recorded, unused)")
    for f, s in ((10, 30), (20, 50), (50, 200)):
        add(f"EMA_{f}_{s}", "EMA", "indicator", {"fast": f, "slow": s},
            f"long: ema{f}>ema{s}; short: ema{f}<ema{s}")
    for kp, sm, dp in ((9, 3, 3), (14, 3, 3), (21, 5, 5)):
        add(f"STOCH_{kp}_{sm}_{dp}", "STOCH", "indicator", {"k": kp, "smooth": sm, "d": dp},
            f"K={kp} smooth={sm} D={dp}; long: k>d & k<20; short: k<d & k>80")
    for n in (10, 20, 50):
        add(f"OBV_SMA{n}", "OBV", "indicator", {"sma": n},
            f"long: obv>sma(obv,{n}); short: obv<sma(obv,{n})")
    for n in (14, 20, 30):
        add(f"MFI{n}", "MFI", "indicator", {"length": n},
            f"long: mfi({n})<20; short: mfi({n})>80")
    for n in (14, 20, 30):
        add(f"CMF{n}", "CMF", "indicator", {"length": n},
            f"long: cmf({n})>0; short: cmf({n})<0")
    for p, m in ((20, 1.5), (20, 2.0), (50, 2.0)):
        add(f"BB_{p}_{m}", "BB", "indicator", {"period": p, "mult": m},
            f"long: close<=sma{p}-{m}*std{p}; short: close>=sma{p}+{m}*std{p}")
    for pr, thr in ((14, 22), (20, 22), (28, 22)):
        add(f"ADXDI_{pr}_{thr}", "ADXDI", "indicator", {"period": pr, "adx_thr": thr},
            f"long: pdi>ndi & adx>= {thr}; short: ndi>pdi & adx>={thr} (Wilder {pr})")
    for n in (20, 55):
        add(f"TURTLE_{n}", "TURTLE", "indicator", {"look": n},
            f"long: low<lo{n} & close>lo{n}; short: high>hi{n} & close<hi{n} (shift1)")
    for n in (20, 55):
        add(f"DONCHIAN_{n}", "DONCHIAN", "indicator", {"look": n},
            f"long: close>hi{n}; short: close<lo{n} (shift1 rolling)")
    # ---- pending ----
    cat["VPFR_PENDING"] = dict(variant_id="VPFR_PENDING", family="VPFR", track="pending",
        parameters={}, source_file="", signal_definition="PENDING: no source/settings provided; not run")
    return cat


# ----------------------------- per-symbol signal computation -----------------------------
def structure_edges(df):
    """Return {(vid,dir): edge bool array} for MSS/FVG/SFP structure variants + baseline map."""
    o, h, l, c = df.open, df.high, df.low, df.close
    atr = IND.wilder_atr(df, 14).to_numpy(float)
    on, hn, ln, cn = o.to_numpy(float), h.to_numpy(float), l.to_numpy(float), c.to_numpy(float)
    ed = {}
    for Lp in (3, 5, 8):
        mss = M.mss_signal(on, hn, ln, cn, atr, L=Lp)
        ed[(f"MSS_L{Lp}", 1)] = L.edge(mss == 1); ed[(f"MSS_L{Lp}", -1)] = L.edge(mss == -1)
    bt, bb, st_, sb = M.fvg_levels(hn, ln)
    ed[("FVG_3BAR_BASE", 1)] = L.edge(np.isfinite(bt)); ed[("FVG_3BAR_BASE", -1)] = L.edge(np.isfinite(st_))
    for lk in (10, 20, 40):
        sfp = M.sfp_signal(o, h, l, c, look=lk).to_numpy()
        ed[(f"SFP_LOOK{lk}", 1)] = L.edge((sfp == 1) & (cn > on))
        ed[(f"SFP_LOOK{lk}", -1)] = L.edge((sfp == -1) & (cn < on))
    return ed, atr


def indicator_levels(df):
    """Return {(vid,dir): bool level array} for all indicator variants (LEVEL state at bar i)."""
    S = pd.Series
    h = df.high.to_numpy(float); l = df.low.to_numpy(float)
    c = df.close.to_numpy(float); v = df.volume.to_numpy(float)
    B = lambda x: np.asarray(x, dtype=bool)
    cond = {}
    # RSI
    for n in (2, 7, 14):
        r = _rsi(c, n); ob = 85 if n == 2 else 70; os_ = 15 if n == 2 else 30
        cond[(f"RSI{n}", 1)] = B(r < os_); cond[(f"RSI{n}", -1)] = B(r > ob)
    # MACD line vs zero
    for f, s, sig in ((8, 21, 5), (12, 26, 9), (19, 39, 9)):
        ml = _ema(c, f) - _ema(c, s)
        cond[(f"MACD_{f}_{s}_{sig}", 1)] = B(ml > 0); cond[(f"MACD_{f}_{s}_{sig}", -1)] = B(ml < 0)
    # EMA pairs
    for f, s in ((10, 30), (20, 50), (50, 200)):
        ef, es = _ema(c, f), _ema(c, s)
        cond[(f"EMA_{f}_{s}", 1)] = B(ef > es); cond[(f"EMA_{f}_{s}", -1)] = B(ef < es)
    # Stochastic
    for kp, sm, dp in ((9, 3, 3), (14, 3, 3), (21, 5, 5)):
        ll = S(l).rolling(kp).min().to_numpy(); hh = S(h).rolling(kp).max().to_numpy()
        raw = 100 * (c - ll) / np.where(hh - ll == 0, np.nan, hh - ll)
        k = S(raw).rolling(sm).mean().to_numpy(); d = S(k).rolling(dp).mean().to_numpy()
        cond[(f"STOCH_{kp}_{sm}_{dp}", 1)] = B((k > d) & (k < 20))
        cond[(f"STOCH_{kp}_{sm}_{dp}", -1)] = B((k < d) & (k > 80))
    # OBV vs SMA
    obv = np.cumsum(np.sign(np.diff(c, prepend=c[0])) * v)
    for n in (10, 20, 50):
        sm = _sma(obv, n)
        cond[(f"OBV_SMA{n}", 1)] = B(obv > sm); cond[(f"OBV_SMA{n}", -1)] = B(obv < sm)
    # MFI
    tp = (h + l + c) / 3; mf = tp * v; dtp = np.diff(tp, prepend=np.nan)
    for n in (14, 20, 30):
        pos = S(np.where(dtp > 0, mf, 0.0)).rolling(n).sum().to_numpy()
        neg = S(np.where(dtp < 0, mf, 0.0)).rolling(n).sum().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            mfi = np.where(neg == 0, 100.0, 100 - 100 / (1 + pos / neg))
        cond[(f"MFI{n}", 1)] = B(mfi < 20); cond[(f"MFI{n}", -1)] = B(mfi > 80)
    # CMF
    with np.errstate(divide="ignore", invalid="ignore"):
        mfm = np.where(h - l == 0, 0.0, ((c - l) - (h - c)) / (h - l))
    for n in (14, 20, 30):
        cmf = S(mfm * v).rolling(n).sum().to_numpy() / S(v).rolling(n).sum().to_numpy()
        cond[(f"CMF{n}", 1)] = B(cmf > 0); cond[(f"CMF{n}", -1)] = B(cmf < 0)
    # Bollinger
    for p, m in ((20, 1.5), (20, 2.0), (50, 2.0)):
        mp = S(c).rolling(p).mean().to_numpy(); sd = S(c).rolling(p).std(ddof=0).to_numpy()
        lower = mp - m * sd; upper = mp + m * sd
        cond[(f"BB_{p}_{m}", 1)] = B(c <= lower); cond[(f"BB_{p}_{m}", -1)] = B(c >= upper)
    # ADX/DI
    pc = np.r_[np.nan, c[:-1]]; ph = np.r_[np.nan, h[:-1]]; pl = np.r_[np.nan, l[:-1]]
    upm, dnm = h - ph, pl - l
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0); ndm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    pdm[0] = ndm[0] = tr[0] = np.nan
    for pr, thr in ((14, 22), (20, 22), (28, 22)):
        atrp = _wilder(tr, pr)
        with np.errstate(divide="ignore", invalid="ignore"):
            pdi = 100 * _wilder(pdm, pr) / atrp; ndi = 100 * _wilder(ndm, pr) / atrp
            dx = 100 * np.abs(pdi - ndi) / (pdi + ndi)
        adx = _wilder(dx, pr)
        cond[(f"ADXDI_{pr}_{thr}", 1)] = B((pdi > ndi) & (adx >= thr))
        cond[(f"ADXDI_{pr}_{thr}", -1)] = B((ndi > pdi) & (adx >= thr))
    # Turtle & Donchian
    for n in (20, 55):
        lo = S(l).shift(1).rolling(n).min().to_numpy(); hi = S(h).shift(1).rolling(n).max().to_numpy()
        cond[(f"TURTLE_{n}", 1)] = B((l < lo) & (c > lo)); cond[(f"TURTLE_{n}", -1)] = B((h > hi) & (c < hi))
        cond[(f"DONCHIAN_{n}", 1)] = B(c > hi); cond[(f"DONCHIAN_{n}", -1)] = B(c < lo)
    return cond


# ----------------------------- load everything -----------------------------
STRUCT_VARIANTS = [f"MSS_L{p}" for p in (3, 5, 8)] + ["FVG_3BAR_BASE"] + [f"SFP_LOOK{lk}" for lk in (10, 20, 40)]
BASELINE = {"MSS": "MSS_L5", "FVG": "FVG_3BAR_BASE", "SFP": "SFP_LOOK20"}


def load_all():
    data = {}
    for s in SYMS:
        df = L.load(s)
        sed, atr = structure_edges(df)
        cond = indicator_levels(df)
        OA = {(cn, d): L.outcome_arrays(df, atr, d, tg, ad, H)
              for cn, (tg, ad, H) in CFG.items() for d in (1, -1)}
        data[s] = dict(df=df, sed=sed, cond=cond, atr=atr, OA=OA, n=len(df))
    return data


def indicator_ids():
    return [v for v in build_catalog() if build_catalog()[v]["track"] == "indicator"]


# ----------------------------- metric builders -----------------------------
def _summ_from_states(states, mfe, mae, ttt):
    g = pd.DataFrame(dict(state=states, mfe=mfe, mae=mae, bars_to_target=ttt))
    return L.summarize(g)


def baseline_fires_frame(data, period=None):
    """Rows for the 3 REGISTERED baseline structure edge fires (both dirs), with outcomes + all
    indicator level bits at the fire bar. Used for T2 confirmation measurement."""
    ind_ids = [v for v, m in build_catalog().items() if m["track"] == "indicator"]
    rows = []
    for s, D in data.items():
        df = D["df"]
        for comp, vid in BASELINE.items():
            for d in (1, -1):
                f = D["sed"][(vid, d)]
                for i in np.flatnonzero(f):
                    i = int(i); per = period_of(df.index[i])
                    if period and per != period:
                        continue
                    bits = {f"c_{v}": bool(D["cond"][(v, d)][i]) for v in ind_ids}
                    row = dict(sym=s, bar=i, structure=comp, direction=("long" if d == 1 else "short"),
                               period=per)
                    for cn in CFG:
                        st, ttt, mfe, mae = D["OA"][(cn, d)]
                        row[f"state_{cn}"] = st[i]; row[f"ttt_{cn}"] = ttt[i]
                        row[f"mfe_{cn}"] = mfe[i]; row[f"mae_{cn}"] = mae[i]
                    rows.append({**row, **bits})
    return pd.DataFrame(rows)


def indicator_metrics(BF, vid, period, cn):
    """Confirmation metrics for one indicator variant, pooled over baseline structures."""
    m = BF[BF.period == period]
    raw_valid = int(m[f"state_{cn}"].isin(list(CODE)).sum())
    conf = m[m[f"c_{vid}"]]
    sm = _summ_from_states(conf[f"state_{cn}"].to_numpy(), conf[f"mfe_{cn}"].to_numpy(),
                           conf[f"mae_{cn}"].to_numpy(), conf[f"ttt_{cn}"].to_numpy())
    sm["signal_coverage"] = sm["valid"] / raw_valid if raw_valid else np.nan
    sm["raw_ref_valid"] = raw_valid
    return sm, conf


def structure_metrics(data, vid, period, cn):
    """Own raw-structure metrics for one structure variant (both directions pooled)."""
    fam = vid.split("_")[0] if not vid.startswith("MSS") and not vid.startswith("SFP") else ("MSS" if vid.startswith("MSS") else ("SFP" if vid.startswith("SFP") else "FVG"))
    fam = "MSS" if vid.startswith("MSS") else ("SFP" if vid.startswith("SFP") else "FVG")
    states = []; mfe = []; mae = []; ttt = []
    base_valid = 0
    base_vid = BASELINE[fam]
    for s, D in data.items():
        df = D["df"]
        for d in (1, -1):
            st, tt, mf, ma = D["OA"][(cn, d)]
            for i in np.flatnonzero(D["sed"][(vid, d)]):
                i = int(i)
                if period_of(df.index[i]) != period:
                    continue
                states.append(st[i]); mfe.append(mf[i]); mae.append(ma[i]); ttt.append(tt[i])
            for i in np.flatnonzero(D["sed"][(base_vid, d)]):
                i = int(i)
                if period_of(df.index[i]) != period:
                    continue
                if st[i] in CODE:
                    base_valid += 1
    sm = _summ_from_states(np.array(states, object), np.array(mfe, float), np.array(mae, float), np.array(ttt, float))
    sm["signal_coverage"] = sm["valid"] / base_valid if base_valid else np.nan
    sm["raw_ref_valid"] = base_valid
    return sm


# ----------------------------- rise starts (L0073 definition) -----------------------------
def rise_starts(data):
    starts = {}
    for s, D in data.items():
        st = D["OA"][("base", 1)][0]; pos = st == "positive_before_negative"
        last = -10 ** 9; idxs = []
        for i in range(1, len(pos)):
            if pos[i] and not pos[i - 1] and i - last >= 6:
                last = i; idxs.append(i)
        starts[s] = idxs
    return starts


def variant_long_presence(D, vid, track):
    """Per-bar long-signal presence array for a variant (edge fire for structure, level for indicator)."""
    if track == "structure":
        return D["sed"][(vid, 1)]
    return D["cond"][(vid, 1)]


def rise_coverage(data, catalog, starts):
    rows = []
    for vid, meta in catalog.items():
        if meta["track"] == "pending":
            continue
        tot = 0; covered = 0
        for s, D in data.items():
            pres = variant_long_presence(D, vid, meta["track"])
            for i in starts[s]:
                if period_of(D["df"].index[i]) != "train" and period_of(D["df"].index[i]) != "holdout":
                    continue
                tot += 1
                lo = max(0, i - PRE)
                if pres[lo:i + 1].any():
                    covered += 1
        # split by period too
        for per in ("train", "holdout"):
            t = c = 0
            for s, D in data.items():
                pres = variant_long_presence(D, vid, meta["track"])
                for i in starts[s]:
                    if period_of(D["df"].index[i]) != per:
                        continue
                    t += 1; lo = max(0, i - PRE)
                    if pres[lo:i + 1].any():
                        c += 1
            rows.append(dict(variant_id=vid, family=meta["family"], track=meta["track"], period=per,
                             qualifying_starts=t, preceded=c,
                             rise_start_coverage=(c / t if t else np.nan)))
    return pd.DataFrame(rows)


# ----------------------------- random control -----------------------------
def random_control_indicator(data, BF, vid, period, cn, rng):
    m = BF[BF.period == period]
    per_sym = []; P_act = D_act = V_act = 0
    for s, g in m.groupby("sym"):
        codes = np.array([CODE.get(x, -1) for x in g[f"state_{cn}"]])
        real = g[f"c_{vid}"].to_numpy(bool)
        elig = codes[codes >= 0]
        k = int(((codes >= 0) & real).sum())
        rc = codes[(codes >= 0) & real]
        per_sym.append((elig, k))
        P_act += int((rc == 0).sum()); D_act += int(((rc == 0) | (rc == 1)).sum()); V_act += int((rc >= 0).sum())
    return _rand_from_pool(per_sym, P_act, D_act, V_act, rng)


def random_control_structure(data, vid, period, cn, rng):
    per_sym = []; P_act = D_act = V_act = 0
    for s, D in data.items():
        df = D["df"]
        idx_all = []
        for d in (1, -1):
            st = D["OA"][(cn, d)][0]
            fires = [int(i) for i in np.flatnonzero(D["sed"][(vid, d)]) if period_of(df.index[i]) == period]
            # eligible pool: all bars in this direction's period range with valid state
            codesd = np.array([CODE.get(x, -1) for x in st])
            per_bars = np.array([j for j in range(len(df)) if period_of(df.index[j]) == period and codesd[j] >= 0])
            if len(per_bars) == 0:
                continue
            realcodes = codesd[[i for i in fires if codesd[i] >= 0]]
            per_sym.append((codesd[per_bars], len([i for i in fires if codesd[i] >= 0])))
            P_act += int((realcodes == 0).sum()); D_act += int(((realcodes == 0) | (realcodes == 1)).sum())
            V_act += int((realcodes >= 0).sum())
    return _rand_from_pool(per_sym, P_act, D_act, V_act, rng)


def _rand_from_pool(per_sym, P_act, D_act, V_act, rng, ndraw=NDRAW):
    if V_act == 0 or D_act == 0:
        return dict(confirmed=int(V_act), actual_dir_acc=np.nan, rand_dir_median=np.nan,
                    rand_dir_p5=np.nan, rand_dir_p95=np.nan, dir_pct_rank=np.nan)
    act = P_act / D_act
    P = np.zeros(ndraw); Dd = np.zeros(ndraw)
    for pool, k in per_sym:
        if k == 0 or len(pool) == 0:
            continue
        k = min(k, len(pool))
        for t in range(ndraw):
            pick = pool[rng.choice(len(pool), k, replace=False)]
            P[t] += (pick == 0).sum(); Dd[t] += ((pick == 0) | (pick == 1)).sum()
    dacc = P / np.maximum(Dd, 1)
    return dict(confirmed=int(V_act), actual_dir_acc=act, rand_dir_median=float(np.median(dacc)),
                rand_dir_p5=float(np.percentile(dacc, 5)), rand_dir_p95=float(np.percentile(dacc, 95)),
                dir_pct_rank=float((dacc < act).mean()))


# ----------------------------- drivers -----------------------------
def screen(data, catalog, period):
    """Full per-variant metric rows (base + sens) for a period."""
    BF = baseline_fires_frame(data)
    rows = []
    for vid, meta in catalog.items():
        if meta["track"] == "pending":
            continue
        for cn in CFG:
            if meta["track"] == "indicator":
                sm, _ = indicator_metrics(BF, vid, period, cn)
            else:
                sm = structure_metrics(data, vid, period, cn)
            dec = sm["positive_before_negative"] + sm["negative_before_positive"]
            rows.append(dict(variant_id=vid, family=meta["family"], track=meta["track"], period=period,
                config=cn, signals=int(sm["signals"]), decided=int(dec), valid=int(sm["valid"]),
                directional_accuracy=sm["directional_accuracy"], hit_rate_all=sm["hit_rate_all"],
                wilson_lo=sm["dir_ci_lo"], wilson_hi=sm["dir_ci_hi"],
                signal_coverage=sm["signal_coverage"], raw_ref_valid=int(sm["raw_ref_valid"]),
                neither=sm["neither_within_window"], ambiguous=sm["ambiguous_same_bar"],
                mfe_mean=sm["mfe_mean"], mae_mean=sm["mae_mean"], ttt_median=sm["ttt_median"]))
    return pd.DataFrame(rows), BF


def add_random(df_rows, data, BF, period):
    rng = np.random.default_rng(SEED)
    out = []
    for _, r in df_rows[df_rows.config == "base"].iterrows():
        if r.track == "indicator":
            rc = random_control_indicator(data, BF, r.variant_id, period, "base", rng)
        else:
            rc = random_control_structure(data, r.variant_id, period, "base", rng)
        out.append(dict(variant_id=r.variant_id, family=r.family, track=r.track, period=period, **rc))
    return pd.DataFrame(out)


def write_catalog(catalog):
    rows = [dict(variant_id=m["variant_id"], family=m["family"], track=m["track"],
                 parameters=json.dumps(m["parameters"]), source_file=m["source_file"],
                 train_period=f"{TRAIN_START.date()}..{TRAIN_END.date()}",
                 holdout_period=f"{HOLDOUT_START.date()}..{HOLDOUT_END.date()}",
                 signal_definition=m["signal_definition"]) for m in catalog.values()]
    pd.DataFrame(rows).to_csv(f"{OUT}/variant_catalog_l0079.csv", index=False)


def run_train():
    os.makedirs(OUT, exist_ok=True)
    catalog = build_catalog(); write_catalog(catalog)
    data = load_all()
    rows, BF = screen(data, catalog, "train")
    rows.to_csv(f"{OUT}/train_results_l0079.csv", index=False)
    # selection: rank within family (train, base), record best per family + sufficient-sample best
    pooled = rows[rows.config == "base"].copy()
    rnd = add_random(rows, data, BF, "train")
    pooled = pooled.merge(rnd[["variant_id", "rand_dir_median", "dir_pct_rank"]], on="variant_id", how="left")
    pooled["beats_random"] = pooled["directional_accuracy"] > pooled["rand_dir_median"]
    pooled["sufficient"] = pooled["decided"] >= DECIDED_MIN
    sel = {"train_period": [str(TRAIN_START), str(TRAIN_END)], "rank_within_family": True,
           "gate_sufficient_decided": DECIDED_MIN, "chosen_per_family": {}, "reasons": {}}
    for fam, g in pooled.groupby("family"):
        gv = g[g.sufficient].sort_values(["directional_accuracy", "wilson_lo", "signal_coverage"], ascending=False)
        if len(gv) == 0:
            sel["chosen_per_family"][fam] = None
            sel["reasons"][fam] = "لا نسخة بعينة كافية (decided>=100) في هذه العائلة على train"
            continue
        best = gv.iloc[0]
        sel["chosen_per_family"][fam] = best.variant_id
        sel["reasons"][fam] = (f"{best.variant_id}: دقة {best.directional_accuracy:.4f} على {int(best.decided)} محسوم، "
                               f"تغطية {best.signal_coverage:.3f}، Wilson-lo {best.wilson_lo:.4f}، "
                               f"وسيط عشوائي {best.rand_dir_median:.4f}، يتفوق={bool(best.beats_random)}")
    sel["frozen_note"] = "أفضل نسخة لكل عائلة من train فقط (عينة كافية)، تُجمّد قبل قراءة holdout. لا دمج ثلاثي في L0079."
    json.dump(sel, open(f"{OUT}/selection_l0079.json", "w"), ensure_ascii=False, indent=1, default=float)
    rnd.to_csv(f"{OUT}/random_control_l0079.csv", index=False)   # train rows; holdout appended later
    print("TRAIN done.", len(rows), "rows.", "chosen:", sel["chosen_per_family"])


def run_holdout():
    catalog = build_catalog()
    data = load_all()
    rows, BF = screen(data, catalog, "holdout")
    rows.to_csv(f"{OUT}/holdout_results_l0079.csv", index=False)
    rnd = add_random(rows, data, BF, "holdout")
    prev = f"{OUT}/random_control_l0079.csv"
    if os.path.exists(prev):
        old = pd.read_csv(prev); old = old[old.period != "holdout"]
        rnd = pd.concat([old, rnd], ignore_index=True)
    rnd.to_csv(prev, index=False)
    starts = rise_starts(data)
    rc = rise_coverage(data, catalog, starts)
    rc.to_csv(f"{OUT}/rise_coverage_l0079.csv", index=False)
    print("HOLDOUT done.", len(rows), "rows; rise_coverage", len(rc), "rows.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "train"
    if cmd == "train":
        run_train()
    elif cmd == "holdout":
        run_holdout()
    else:
        raise SystemExit("usage: l0079_variants.py [train|holdout]")
