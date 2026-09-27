"""L0072 — independent indicator-trigger books (no candle confirmation). Engine derived from l0071_core.
Rules: history/research/hyp_lab_out/L0072/preregistration_l0072.json
"""
import numpy as np, pandas as pd, os

SYMS = ["ATOM", "BNB", "BTC", "ETH", "FIL", "GRAM", "HNT", "IMX", "LINK", "RENDER", "SOL", "VET", "XLM"]
CACHE = os.path.expanduser(os.environ.get("L007X_4H", "~/l007x_4h"))
END_T = pd.Timestamp("2026-08-31", tz="UTC")
FEE = 0.001
BAR = pd.Timedelta(hours=4)

BASE = dict(dd_L=120, dd_thr=0.25, eql=0.5, reclaim=0.0, cat="cat1", k_stop=1.0, risk=0.01, cap=0.25,
            margin=0.002, trail_start=1.5, k_trail=1.5, buf=0.25, bear_margin=0.0, cooldown=6,
            protect=True, trail=True, first_touch=False, tr=(0.15, 0.25, 0.30, 0.30), add_win=30,
            life=60, conf_win=2, max_ext=2.0)


def slip_layer(layer, mult):
    return {"c115": 0.0, "measured": 0.0003 * mult, "stress_mid": 0.001, "stress_high": 0.003}[layer]


def fee_layer(layer):
    return 0.00115 if layer == "c115" else FEE


def wilder(x, n):
    out = np.full(len(x), np.nan); s = np.nan
    for i, v in enumerate(x):
        if np.isnan(v): continue
        s = v if np.isnan(s) else s + (v - s) / n
        out[i] = s
    return out


def pivots(lo, hi, L, R):
    n = len(lo); pl = np.zeros(n, bool); ph = np.zeros(n, bool)
    for j in range(L, n - R):
        w = lo[j - L:j + R + 1]
        if lo[j] == w.min() and lo[j] < lo[j - L:j].min(): pl[j] = True
        w = hi[j - L:j + R + 1]
        if hi[j] == w.max() and hi[j] > hi[j - L:j].max(): ph[j] = True
    return pl, ph


_PREP = {}


def prep(sym):
    if sym in _PREP: return _PREP[sym]
    d = pd.read_parquet(f"{CACHE}/{sym}USDT_4h.parquet")
    d = d[(d.minutes > 0) & (d.index < END_T)].copy()
    o, h, l, c, v = (d[k].to_numpy(float) for k in ["open", "high", "low", "close", "volume"])
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    atr = wilder(tr, 14)
    vr = atr / pd.Series(atr).rolling(100).mean().to_numpy()
    mult = np.where(vr >= 1.5, 3.0, np.where(vr >= 1.2, 2.0, 1.0))
    volmed = pd.Series(v).shift(1).rolling(20).median().to_numpy()  # completed bars before bar i
    # D1 from complete days (6 bars)
    day = d.index.floor("D")
    g = d.groupby(day)
    D = pd.DataFrame({"close": g.close.last(), "n": g.size()})
    D = D[D.n == 6]
    D["e50"] = D.close.ewm(span=50, adjust=False).mean()
    D["e200"] = D.close.ewm(span=200, adjust=False).mean()
    D["cnt"] = np.arange(len(D))
    for L in (90, 120, 180):
        D[f"hc{L}"] = D.close.rolling(L).max()
    D["known_at"] = D.index + pd.Timedelta(days=1)  # D1 close time
    bar_close = d.index + BAR
    idx = np.searchsorted(D.known_at.to_numpy(), bar_close.to_numpy(), side="right") - 1  # last day with close<=bar close
    ctx = {}
    for k in ["close", "e50", "e200", "cnt", "hc90", "hc120", "hc180"]:
        a = D[k].to_numpy(); ctx[k] = np.where(idx >= 0, a[np.clip(idx, 0, None)], np.nan)
    ctx["d1_idx"] = idx
    regime = np.where(ctx["close"] > ctx["e200"], np.where(ctx["e50"] > ctx["e200"], 2, 1), 0)
    valid = (ctx["cnt"] >= 200) & ~np.isnan(atr) & ~np.isnan(vr)
    mpl, mph = pivots(l, h, 2, 2)
    Mpl, _ = pivots(l, h, 5, 5)
    P = dict(t=d.index, o=o, h=h, l=l, c=c, v=v, atr=atr, mult=mult, volmed=volmed, regime=regime, valid=valid,
             ctx=ctx, mpl=mpl, mph=mph, Mpl=Mpl, D=D, bar_close=bar_close)
    _PREP[sym] = P
    return P


def signals(sym, cfg):
    """Causal signal list for one asset. Returns list of dicts (decision bar c -> entry at c+1)."""
    P = prep(sym); o, h, l, c, atr = P["o"], P["h"], P["l"], P["c"], P["atr"]
    n = len(c); hc = P["ctx"][f"hc{cfg['dd_L']}"]; dclose = P["ctx"]["close"]
    levels = []  # dict(px, born, major)
    minor_lows = []  # (conf_bar, j, px)
    minor_highs = []  # (conf_bar, j, px)
    out = []; pend = None
    for i in range(n):
        # pivots confirmed at close of i
        j = i - 2
        if j >= 2 and P["mpl"][j]:
            px = l[j]
            for (_, _, q) in minor_lows[-20:]:
                if not np.isnan(atr[i]) and abs(q - px) <= cfg["eql"] * atr[i]:
                    levels.append(dict(px=min(px, q), born=i, kind="EQL"))
            minor_lows.append((i, j, px))
        if j >= 2 and P["mph"][j]: minor_highs.append((i, j, h[j]))
        j5 = i - 5
        if j5 >= 5 and P["Mpl"][j5]: levels.append(dict(px=l[j5], born=i, kind="MAJOR"))
        levels = [x for x in levels if i - x["born"] <= cfg["life"]]
        if not P["valid"][i] or np.isnan(hc[i]):
            continue
        dd = 1 - dclose[i] / hc[i]
        # pending confirmation
        if pend is not None:
            if c[i] < pend["level"]:
                pend = None
            elif c[i] > pend["sh"]:
                ext = (c[i] - pend["level"]) / atr[i]
                mss = pend["mss_px"] is not None and c[i] > pend["mss_px"]
                s = dict(pend, conf_bar=i, conf_high=h[i], mss=bool(mss), ext=float(ext), reject="")
                if ext > cfg["max_ext"]: s["reject"] = "extension"
                elif cfg["cat"] in ("cat2", "cat4") and not mss: s["reject"] = "no_mss"
                elif cfg["cat"] in ("cat3", "cat4") and not s["vol_ok"]: s["reject"] = "low_volume"
                out.append(s); pend = None
            elif i - pend["sweep_bar"] >= cfg["conf_win"]:
                pend = None
        if pend is not None or dd < cfg["dd_thr"] or i < 1:
            continue
        # we require the level to be known before bar i (born < i)
        cand = [x for x in levels if x["born"] < i and l[i] < x["px"] - cfg["reclaim"] * atr[i]]
        if not cand: continue
        lv = min(cand, key=lambda x: x["px"])
        for x in cand: levels.remove(x)  # consumed
        mh = [q for (cb, _, q) in minor_highs if cb < i]
        base = dict(sym=sym, sweep_bar=i, level=lv["px"], kind=lv["kind"], sl=l[i], sh=h[i], dd=float(dd),
                    regime=int(P["regime"][i]), mss_px=(mh[-1] if mh else None),
                    vol_ok=bool(P["v"][i] > P["volmed"][i]) if not np.isnan(P["volmed"][i]) else False)
        if cfg["first_touch"]:
            out.append(dict(base, conf_bar=i, conf_high=h[i], mss=False, ext=0.0, reject=""))
            continue
        if not (c[i] > lv["px"] and c[i] >= (h[i] + l[i]) / 2):
            continue
        pend = base
    return out


def run(cfg, capital=2000.0, layer="measured", syms=SYMS, t0=None, t1=None):
    """Portfolio simulation. Execution path always at the given layer."""
    cfg = dict(BASE, **cfg)
    Ps = {s: prep(s) for s in syms}
    sigs = {}
    for s in syms:
        for q in (cfg["sigfn"](s, cfg) if cfg.get("sigfn") else signals(s, cfg)):
            sigs.setdefault((s, q["conf_bar"]), q)
    grid = sorted(set().union(*[set(Ps[s]["t"]) for s in syms]))
    if t0 is not None: grid = [t for t in grid if t >= t0]
    if t1 is not None: grid = [t for t in grid if t < t1]
    pos_of = {s: {t: k for k, t in enumerate(Ps[s]["t"])} for s in syms}
    cash = capital; pos = {}; last_close = {}; cool = {s: -10 ** 9 for s in syms}
    trades, fills, sigrows, eq_curve, orders = [], [], [], [], []
    pending = []  # orders to fill at next open: (sym, kind, qty or tranche)
    nexec = nrej = 0; min_cash = cash; max_conc = 0
    fee = fee_layer(layer)

    def equity():
        return cash + sum(p["qty"] * last_close[s] for s, p in pos.items())

    for t in grid:
        # 1) fills at open
        todo = sorted(pending, key=lambda x: (x[0], x[1] != "exit")); pending = []
        for (s, kind, info) in todo:
            k = pos_of[s].get(t)
            if k is None: pending.append((s, kind, info)); continue
            P = Ps[s]; op = P["o"][k]; sl = slip_layer(layer, P["mult"][k])
            if kind == "exit":
                p = pos.get(s)
                if p is None: continue
                reason = info
                if op <= p["stop"]: reason = "stop_gap"
                px = op * (1 - sl); cash += p["qty"] * px * (1 - fee)
                fills.append(dict(sym=s, t=str(t), side="sell", raw=op, qty=p["qty"], mult=P["mult"][k], k=k))
                close_trade(trades, p, s, t, k, op, reason, layer, fee, sl); cool[s] = k; del pos[s]
                continue
            # buy tranche
            qty, tr_i, sig = info[:3]
            px = op * (1 + sl); cost = qty * px * (1 + fee)
            rec = dict(sym=s, t=str(t), tranche=tr_i, notional=qty * px, status="")
            if s in pos and tr_i == 0: rec["status"] = "reject_dup"
            elif s not in pos and tr_i > 0: rec["status"] = "reject_nopos"
            elif qty * px < 20: rec["status"] = "reject_min_order"
            elif cost > cash: rec["status"] = "reject_cash"
            else: rec["status"] = "filled"
            orders.append(rec)
            if rec["status"] != "filled":
                nrej += 1
                if tr_i == 0: sigrows.append(dict(sig_row(sig), status=rec["status"]))
                continue
            nexec += 1; cash -= cost
            fills.append(dict(sym=s, t=str(t), side="buy", raw=op, qty=qty, mult=P["mult"][k], k=k))
            if tr_i == 0:
                sigrows.append(dict(sig_row(sig), status="filled"))
                if sig.get("stop_from_fill"):
                    sig = dict(sig, stop=op - sig["k_atr"])
                pos[s] = dict(sig=sig, qty=qty, cost=qty * px * (1 + fee), raw_cost=qty * op, entry_t=str(t), entry_k=k,
                              stop=sig["stop"], stop0=sig["stop"], tr_done=1, Q=info[3] if len(info) > 3 else sig["Q"],
                              protected=False, trail_on=False, hi_close=-1, prot_bar=None, trail_bar=None,
                              weak=None, soft=False, hl=None, stops_log=[sig["stop"]], k_last_hl=None, tr_list=[k])
            else:
                p = pos[s]; p["qty"] += qty; p["cost"] += qty * px * (1 + fee); p["raw_cost"] += qty * op
                p["tr_done"] += 1; p["tr_list"].append(k)
        # 2) intrabar stop
        for s in list(pos):
            k = pos_of[s].get(t)
            if k is None: continue
            P = Ps[s]; p = pos[s]
            if k == p["entry_k"] and False: pass
            if P["l"][k] <= p["stop"]:
                raw = min(P["o"][k], p["stop"]); sl = slip_layer(layer, P["mult"][k])
                cash += p["qty"] * raw * (1 - sl) * (1 - fee)
                fills.append(dict(sym=s, t=str(t), side="sell", raw=raw, qty=p["qty"], mult=P["mult"][k], k=k))
                why = "stop_protect" if p["protected"] and not p["trail_on"] else ("stop_trail" if p["trail_on"] else "stop_hard")
                close_trade(trades, p, s, t, k, raw, why, layer, fee, sl); cool[s] = k; del pos[s]
                pending = [x for x in pending if x[0] != s]
        # 3) close: mark, manage, new signals
        for s in syms:
            k = pos_of[s].get(t)
            if k is not None: last_close[s] = Ps[s]["c"][k]
        eq = equity(); eq_curve.append((t, eq)); min_cash = min(min_cash, cash); max_conc = max(max_conc, len(pos))
        for s in syms:
            k = pos_of[s].get(t)
            if k is None: continue
            P = Ps[s]
            if s in pos:
                manage(pos[s], P, k, cfg, layer, pending, s, eq)
            elif k - cool[s] > cfg["cooldown"] and (s, k) in sigs:
                sig = dict(sigs[(s, k)])
                if sig["reject"]:
                    sigrows.append(dict(sig_row(sig), status="reject_" + sig["reject"])); continue
                if not any(x[0] == s for x in pending):
                    a = P["atr"][k]; e = P["c"][k]
                    stop = (e - cfg["k_stop"] * a) if sig.get("stop_from_fill") else sig["sl"] - cfg["k_stop"] * a
                    sig["k_atr"] = cfg["k_stop"] * a
                    if stop <= 0 or e <= stop:
                        sigrows.append(dict(sig_row(sig), status="reject_bad_stop")); continue
                    Q = min(cfg["risk"] * eq / (e - stop), cfg["cap"] * eq / e)
                    sig.update(stop=stop, Q=Q)
                    pending.append((s, "buy", (Q * cfg["tr"][0], 0, sig, Q)))
            elif (s, k) in sigs:
                sigrows.append(dict(sig_row(sigs[(s, k)]), status="reject_cooldown_or_open"))
    # close open positions at last close (marked, flagged unrealised)
    for s, p in list(pos.items()):
        P = Ps[s]; k = pos_of[s][max(tt for tt in pos_of[s] if tt <= grid[-1])]
        raw = P["c"][k]; sl = slip_layer(layer, P["mult"][k])
        cash += p["qty"] * raw * (1 - sl) * (1 - fee)
        close_trade(trades, p, s, grid[-1], k, raw, "end_mark", layer, fee, sl)
    return dict(trades=trades, eq=eq_curve, cash_end=cash, capital=capital, orders=orders, sigrows=sigrows,
                nexec=nexec, nrej=nrej, min_cash=min_cash, max_conc=max_conc, fills=fills)


def sig_row(s):
    return {k: (round(v, 8) if isinstance(v, float) else v) for k, v in s.items() if k not in ("mss_px",)}


def close_trade(trades, p, s, t, k, raw, reason, layer, fee, sl):
    proceeds = p["qty"] * raw * (1 - sl) * (1 - fee)
    trades.append(dict(sym=s, entry_t=p["entry_t"], exit_t=str(t), bars=k - p["entry_k"], qty=p["qty"],
                       tranches=p["tr_done"], cost=p["cost"], proceeds=proceeds, pnl=proceeds - p["cost"],
                       raw_entry=p["raw_cost"] / p["qty"], raw_exit=raw, reason=reason, protected=p["protected"],
                       trail=p["trail_on"], regime=p["sig"]["regime"], kind=p["sig"]["kind"], mss=p["sig"]["mss"],
                       stop0=p["stop0"], stop_monotone=all(b >= a - 1e-12 for a, b in zip(p["stops_log"], p["stops_log"][1:])),
                       moved_before_protect=p.get("moved_early", False), be_cover=p.get("be_cover", None)))


def manage(p, P, k, cfg, layer, pending, s, eq):
    if any(x[0] == s and x[1] == "exit" for x in pending): return
    c, h, l, a = P["c"][k], P["h"][k], P["l"][k], P["atr"][k]
    sig = p["sig"]; qty = p["qty"]
    avg = p["cost"] / qty  # actual realised entry incl. fees+slippage
    f_out = FEE + slip_layer(layer, P["mult"][k])
    be = avg / (1 - f_out)
    # minor pivots after entry (confirmed at k)
    j = k - 2
    if j > p["entry_k"] and P["mpl"][j]:
        if P["l"][j] > sig["sl"]: p["hl"] = P["l"][j]; p["k_last_hl"] = k
    new_stop = p["stop"]
    if cfg["protect"] and not p["protected"] and c >= be * (1 + cfg["margin"]):
        p["protected"] = True; new_stop = max(new_stop, be * (1 + cfg["margin"]))
        p["be_cover"] = (be * (1 + cfg["margin"])) * (1 - f_out) >= avg - 1e-9
    if p["protected"] and cfg["trail"]:
        if not p["trail_on"] and c >= avg + cfg["trail_start"] * a: p["trail_on"] = True; p["hi_close"] = c
        if p["trail_on"]:
            p["hi_close"] = max(p["hi_close"], c)
            cand = p["hi_close"] - cfg["k_trail"] * a
            if p["hl"] is not None: cand = max(cand, p["hl"] - cfg["buf"] * a)
            new_stop = max(new_stop, cand)
    if new_stop > p["stop"] + 1e-12 and not p["protected"]: p["moved_early"] = True
    if new_stop > p["stop"]: p["stop"] = new_stop; p["stops_log"].append(new_stop)
    # bearish reversal: weakness then confirmation
    if p["weak"] is not None and k > p["weak"][1] and c < p["weak"][0] - cfg["bear_margin"] * a:
        pending.append((s, "exit", "bear_confirm")); return
    if p["weak"] is None or k > p["weak"][1] + 1:
        p["weak"] = None
        mh = P["mph"]; jj = k - 2
        # bearish sweep of a confirmed minor high after entry
        lastmh = None
        for q in range(jj, p["entry_k"], -1):
            if q >= 0 and mh[q]: lastmh = P["h"][q]; break
        if lastmh is not None and h > lastmh and c < lastmh: p["weak"] = (l, k)
        elif p["hl"] is not None and c < p["hl"]: p["weak"] = (p["hl"], k)
    # soft invalidation / adds
    if c < sig["level"]: p["soft"] = True
    if p["soft"] or p["protected"] or k - p["entry_k"] > cfg["add_win"] or p["tr_done"] >= len(cfg["tr"]): return
    if sig["regime"] == 0 and not (sig["mss"] or (sig["mss_px"] is not None and c > sig["mss_px"])): return
    t = p["tr_done"]; ok = False
    if t == 1: ok = l <= sig["level"] + 0.25 * a and c > sig["level"]
    elif t == 2: ok = c > sig["conf_high"] or (sig["mss_px"] is not None and c > sig["mss_px"])
    elif t == 3:
        if p["hl"] is not None and p["hl"] > sig["sl"]:
            mh = [P["h"][q] for q in range(p["k_last_hl"] - 2, k - 1) if P["mph"][q]] if p["k_last_hl"] else []
            ok = bool(mh) and c > mh[-1]
    if ok:
        pending.append((s, "buy", (p["Q"] * cfg["tr"][t], t, sig)))


def eq_series(res):
    return pd.Series([e for _, e in res["eq"]], index=[t for t, _ in res["eq"]])
