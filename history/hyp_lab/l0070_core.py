# -*- coding: utf-8 -*-
"""L0070 — محاكي الاتجاه والقوة النسبية على الإطار اليومي (سببي، تنفيذ على افتتاح اليوم التالي).
لا يستورد nova_v8. كل المؤشرات محسوبة هنا."""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd

CACHE = pathlib.Path.home() / ".cache" / "l0070"
MEMES = ("DOGEUSDT", "SHIBUSDT", "PEPEUSDT")
TARGET13 = ("ATOMUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "FILUSDT", "GRAMUSDT", "HNTUSDT", "IMXUSDT", "LINKUSDT", "RENDERUSDT", "SOLUSDT", "VETUSDT", "XLMUSDT")
FULL16 = tuple(sorted(TARGET13 + MEMES))
UNIT = 20.0
ANCHOR = pd.Timestamp("2021-09-06", tz="UTC")
LAYERS = ("c115", "measured", "stress_mid", "stress_high")


def ema(x: np.ndarray, span: int) -> np.ndarray:
    a = 2.0 / (span + 1.0); out = np.full_like(x, np.nan); prev = np.nan
    for i, v in enumerate(x):
        if np.isnan(v):
            out[i] = prev; continue
        prev = v if np.isnan(prev) else a * v + (1 - a) * prev
        out[i] = prev
    return out


class Panel:
    """مصفوفات [يوم × عملة] على تقويم يومي موحد. NaN = لا بيانات."""

    def __init__(self, coins, end: pd.Timestamp | None = None):
        fr = {s: pd.read_parquet(CACHE / f"{s}_1d.parquet") for s in coins}
        if end is not None:
            fr = {s: f[f.index < end] for s, f in fr.items()}
        idx = pd.DatetimeIndex(sorted(set().union(*[set(f.index) for f in fr.values()])))
        self.idx, self.coins = idx, list(coins)
        g = lambda col: np.column_stack([fr[s][col].reindex(idx).to_numpy(float) for s in coins])
        self.o, self.h, self.l, self.c, self.qv, self.mins = g("open"), g("high"), g("low"), g("close"), g("qv"), g("minutes")
        n, m = self.c.shape
        self.age = np.zeros((n, m))
        for j in range(m):
            has = ~np.isnan(self.c[:, j]); self.age[:, j] = np.where(has, np.cumsum(has), 0)
        self.e = {k: np.column_stack([ema(self.c[:, j], k) for j in range(m)]) for k in (50, 100, 200)}
        lr = np.log(self.c / np.vstack([np.full((1, m), np.nan), self.c[:-1]]))
        self.lr = lr
        self.sig60 = pd.DataFrame(lr).rolling(60, min_periods=40).std().to_numpy()
        tr = np.fmax(self.h - self.l, np.fmax(np.abs(self.h - np.vstack([np.full((1, m), np.nan), self.c[:-1]])),
                                              np.abs(self.l - np.vstack([np.full((1, m), np.nan), self.c[:-1]]))))
        atr = pd.DataFrame(tr).ewm(alpha=1 / 14, adjust=False).mean()
        self.vr = (atr / atr.rolling(100, min_periods=100).mean()).to_numpy()
        self.low10 = pd.DataFrame(self.l).shift(1).rolling(10).min().to_numpy()
        self.ret = {L: self.c / pd.DataFrame(self.c).shift(L).to_numpy() - 1 for L in (20, 65, 150, 200)}
        self._cache = {}
        # السيولة: وسيط qv لآخر 30 يومًا (أيام مكتملة ≤ D) مقابل مئين qv المجمّع لآخر 180 يومًا
        qv_ok = np.where(self.mins >= 1380, self.qv, np.nan)
        self.qv30 = pd.DataFrame(qv_ok).rolling(30, min_periods=20).median().to_numpy()
        self.liq_thr = {}
        for q in (25, 50, 75):
            thr = np.full(n, np.nan)
            for i in range(n):
                blk = qv_ok[max(0, i - 179):i + 1].ravel(); blk = blk[np.isfinite(blk)]
                if len(blk) >= 100: thr[i] = np.percentile(blk, q)
            self.liq_thr[q] = thr
        bi = self.coins.index("BTCUSDT") if "BTCUSDT" in self.coins else None
        self.btc = bi

    def strength(self, method: str, L: int) -> np.ndarray:
        key = (method, L)
        if key in self._cache: return self._cache[key]
        if method == "simple":
            s = self.ret[L]
        elif method == "exp":
            hl = max(L / 3, 1); w = 0.5 ** (np.arange(L)[::-1] / hl); w /= w.sum()
            lr = np.nan_to_num(self.lr, nan=0.0); s = np.full_like(lr, np.nan)
            cs = np.array([np.convolve(lr[:, j], w[::-1], mode="full")[:len(lr)] for j in range(lr.shape[1])]).T * L
            s = np.where(self.age >= L + 1, cs, np.nan)
        elif method == "voladj":
            s = self.ret[L] / (self.sig60 * np.sqrt(L))
        elif method == "blend":
            ranks = []
            for LL in (20, 65, 150, 200):
                r = pd.DataFrame(self.ret[LL]).rank(axis=1, pct=True).to_numpy(); ranks.append(r)
            s = np.mean(ranks, axis=0)
            s = np.where(np.all([np.isfinite(self.ret[LL]) for LL in (20, 65, 150, 200)], axis=0), s, np.nan)
        else:
            raise ValueError(method)
        self._cache[key] = s
        return s


def run(P: Panel, cfg: dict, capital: float = 2000.0, log_orders: bool = False):
    """يرجع: قائمة الصفقات، مصفوفة PnL يومية لكل طبقة [يوم × عملة] (قيمة سوقية للمقاسة؛ الطبقات الأخرى تختلف في الكلفة فقط)،
    والسجل (أوامر منفذة/مرفوضة/غير منفذة، التزامن، أدنى نقد)."""
    n, m = P.c.shape
    L, meth, K = cfg["L"], cfg["method"], cfg["K"]
    S = P.strength(meth, L)
    tf = cfg["trend"]
    if tf == "posmom":
        T = (np.mean([P.ret[x] for x in (20, 65, 150, 200)], axis=0) > 0) if meth == "blend" else (P.ret[L] > 0)
    elif tf == "e50_200":
        T = P.e[50] > P.e[200]
    else:
        T = P.c > P.e[{"c50": 50, "c100": 100, "c200": 200}[tf]]
    data_ok = (P.age >= 250) & np.isfinite(P.c)
    liq = P.qv30 >= P.liq_thr[cfg["liq_q"]][:, None]
    elig = data_ok & liq & np.isfinite(S)
    mk = cfg["market"]
    if mk == "always":
        M = np.ones(n, bool)
    elif mk in ("btc200", "btc200_50"):
        b = P.btc; M = P.c[:, b] > P.e[200][:, b]
        if mk == "btc200_50": M &= P.e[50][:, b] > P.e[200][:, b]
        M = np.nan_to_num(M, nan=0).astype(bool)
    elif mk == "breadth50":
        above = (P.c > P.e[200]) & data_ok
        cnt = data_ok.sum(1); M = np.where(cnt > 0, above.sum(1) / np.maximum(cnt, 1) > 0.5, False)
    rb_n = cfg["rebalance"]
    days_from = ((P.idx - ANCHOR).days).to_numpy()
    rb = (days_from >= 0) & (days_from % rb_n == 0)
    H = {"base": None, "H5": 5, "H20": 20, "H65": 65, "weak10": None}[cfg["exit"]]
    weak = cfg["exit"] == "weak10"
    cap = {"equal": None, "iv40": 0.40, "iv30": 0.30, "iv20": 0.20}[cfg["weights"]]
    fee_sl = {"c115": (0.00115, None), "measured": (0.0010, "vr"), "stress_mid": (0.0010, 0.0010), "stress_high": (0.0010, 0.0030)}

    def slip(layer, i, j):
        f, s = fee_sl[layer]
        if s is None: return 0.0
        if s == "vr":
            v = P.vr[i - 1, j] if i > 0 else np.nan
            return 0.0003 * (3.0 if v >= 1.5 else 2.0 if v >= 1.2 else 1.0) if np.isfinite(v) else 0.0003
        return s

    pos = {}                                  # j -> dict(units, ei, ep)
    pend_buy, pend_sell = {}, set()
    trades, orders = [], {"executed_units": 0, "rejected_units": 0, "below_min": 0, "entries": 0, "exits": 0}
    cash = capital; min_cash = cash; max_conc = 0
    pnl = {L_: np.zeros((n, m)) for L_ in LAYERS}
    deployed = np.zeros(n)
    for i in range(n):
        # 1) تنفيذ على الافتتاح (قرارات الأمس)
        for j in sorted(pend_sell):
            if j in pos and np.isfinite(P.o[i, j]):
                p = pos.pop(j); N = p["units"] * UNIT
                rec = {"coin": P.coins[j], "j": j, "entry_i": p["ei"], "exit_i": i, "units": p["units"], "entry_px": p["ep"], "exit_px": float(P.o[i, j]), "reason": p.get("why", "")}
                for L_ in LAYERS:
                    f = fee_sl[L_][0]; se = slip(L_, p["ei"], j); sx = slip(L_, i, j)
                    net = ((P.o[i, j] * (1 - sx)) / (p["ep"] * (1 + se)) * (1 - f) - (1 + f)) / (1 + f) * N
                    rec[L_] = float(net)
                cash += N + rec["measured"]; trades.append(rec); orders["exits"] += 1
                # تصحيح القيمة السوقية: أزل الربح غير المحقق المتراكم وأضف المحقق
                for L_ in LAYERS:
                    pnl[L_][i, j] += rec[L_] - p["mtm"]
        pend_sell = set()
        for j, units in sorted(pend_buy.items()):
            if j in pos or not np.isfinite(P.o[i, j]): continue
            can = int(cash // UNIT); take = min(units, can)
            orders["rejected_units"] += units - take
            if take <= 0: continue
            cash -= take * UNIT; min_cash = min(min_cash, cash)
            pos[j] = {"units": take, "ei": i, "ep": float(P.o[i, j]), "mtm": 0.0}
            orders["executed_units"] += take; orders["entries"] += 1
        pend_buy = {}
        # 2) قيمة سوقية على الإغلاق (إجمالي؛ الكلفة تُحتسب عند الإغلاق)
        for j, p in pos.items():
            if np.isfinite(P.c[i, j]):
                cur = p["units"] * UNIT * (P.c[i, j] / p["ep"] - 1)
                for L_ in LAYERS:
                    pnl[L_][i, j] += cur - p["mtm"]
                p["mtm"] = cur
        deployed[i] = sum(p["units"] for p in pos.values()) * UNIT
        max_conc = max(max_conc, len(pos))
        # 3) قرارات على الإغلاق للتنفيذ غدًا
        if i == n - 1: break
        complete = P.mins[i] >= 1380
        for j, p in pos.items():
            why = None
            if not np.isfinite(P.c[i, j]) or not np.isfinite(P.o[i + 1, j]):
                why = "انقطاع-بيانات" if not np.isfinite(P.o[i + 1, j]) else None
            if why is None and not T[i, j]: why = "فقدان-الاتجاه"
            if why is None and not M[i]: why = "مرشح-السوق"
            if why is None and H is not None and (i - p["ei"] + 1) >= H: why = f"أفق-{H}"
            if why is None and weak and P.c[i, j] < P.low10[i, j]: why = "ضعف-يومي"
            if why: p["why"] = why; pend_sell.add(j)
        if not rb[i]: continue
        cand = np.where(elig[i] & complete)[0]
        order = cand[np.argsort(-S[i, cand], kind="stable")]
        rank = {j: r for r, j in enumerate(order)}
        for j, p in pos.items():
            if j not in pend_sell and rank.get(j, 10 ** 6) >= K + 2:
                p["why"] = "خارج-الترتيب"; pend_sell.add(j)
        if not M[i]: continue
        keep = [j for j in pos if j not in pend_sell]
        free = K - len(keep)
        if free <= 0: continue
        picks = [j for j in order[:K] if j not in pos and T[i, j]][:free]
        if not picks: continue
        sig = P.sig60[i, cand]; med = np.nanmedian(sig) if np.isfinite(sig).any() else np.nan
        for j in picks:
            if cap is None:
                w = 1.0 / K
            else:
                sj = P.sig60[i, j]
                w = min((1.0 / K) * (med / sj), cap) if np.isfinite(sj) and sj > 0 and np.isfinite(med) else min(1.0 / K, cap)
            units = int((w * capital) // UNIT)
            if units < 1:
                orders["below_min"] += 1; continue
            pend_buy[j] = units
        tot = sum(pend_buy.values()) * UNIT + sum(p["units"] for j, p in pos.items() if j not in pend_sell) * UNIT
        if tot > capital:  # المجموع ≤ 100%: تقليص نسبي معلن
            f = capital / tot
            for j in list(pend_buy):
                u = int(pend_buy[j] * f)
                if u < 1: orders["below_min"] += 1; del pend_buy[j]
                else: pend_buy[j] = u
    # نهاية العينة: إغلاق على آخر إغلاق (مسجل)
    i = n - 1
    for j, p in list(pos.items()):
        px = P.c[i, j] if np.isfinite(P.c[i, j]) else P.c[:, j][np.isfinite(P.c[:, j])][-1]
        N = p["units"] * UNIT
        rec = {"coin": P.coins[j], "j": j, "entry_i": p["ei"], "exit_i": i, "units": p["units"], "entry_px": p["ep"], "exit_px": float(px), "reason": "نهاية-العينة"}
        for L_ in LAYERS:
            f = fee_sl[L_][0]; se = slip(L_, p["ei"], j); sx = slip(L_, i, j)
            rec[L_] = float(((px * (1 - sx)) / (p["ep"] * (1 + se)) * (1 - f) - (1 + f)) / (1 + f) * N)
            pnl[L_][i, j] += rec[L_] - p["mtm"]
        cash += N + rec["measured"]; trades.append(rec)
    orders.update({"max_concurrent": max_conc, "min_cash": round(float(min_cash), 2), "cash_never_negative": bool(min_cash >= -1e-9)})
    return trades, pnl, orders, deployed
