# -*- coding: utf-8 -*-
"""L0045 — آلة E3 (مسار الدقيقة) بمعالجة مُجزَّأة وحفظ تدريجي — نسخة موفّرة للذاكرة.

تُقاس على مسار الدقيقة الحقيقي:
  • الأساس (الأعمدة السبعة الحالية) على فترتي القرار والحكم.
  • الفرضيات العشر (قرار + حكم).
التعبئة ممكنة دائماً (لا سعر خارج مدى السوق)، والوقف/التتبّع يُحترمان على المسار.
تكتب ملفاً جزئياً لكل عملة في out/parts ثم تجمعها.
"""
from __future__ import annotations
import gc, json, os, pathlib, subprocess, sys, time
import numpy as np, pandas as pd

ROOT = pathlib.Path("/home/user/work")
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
HIST = ROOT / "history"
sys.path.insert(0, str(HIST / "hyp_lab")); sys.path.insert(0, str(ROOT))

import pyarrow.parquet as pq
import common as C
from common import atr
import run_l0019_unified as R19
import run_l0036_more as L36
import F_213_breakers as M213
import L0017_F_001_rsi2_snap as E001
import nova_v8.indicators as ind
import nova_v8.config as NC
import L0045_signals as S
import run_l0017 as R17

OUT = HIST / "research" / "hyp_lab_out" / "L0045" / "engine_1m"
PARTS = OUT / "parts"; PARTS.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / ".cache" / "l0045_frames"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
COST = 0.0013
WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060, "wide": 0.0020, "tight": 0.0008}
CHUNK = 200_000


def load_lean(path, start, end):
    """قارئ موفّر للذاكرة: أعمدة محددة + تقييد المدى بدون نسخ وسيطة (يجب أن تكون الصفوف مرتبة)."""
    tb = pq.read_table(path, columns=["open_time", "open", "high", "low", "close"])
    ot = tb.column("open_time").to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
    unit = "ms" if abs(int(ot[0])) < 10**14 else "us"
    idx = pd.to_datetime(ot, unit=unit, utc=True)
    m = (idx >= pd.Timestamp(start, tz="UTC")) & (idx < pd.Timestamp(end, tz="UTC"))
    if not m.all():
        idx = idx[m]
    out = {}
    for c in ("open", "high", "low", "close"):
        a = tb.column(c).to_numpy(zero_copy_only=False).astype(np.float64, copy=False)
        out[c] = a[m]
    del tb
    return pd.DataFrame(out, index=idx, copy=False)


def run_one_coin(df4, df1, sig4, a4):
    """يعيد قائمة pnl لكل صفقة على مسار الدقيقة (تعبئة ممكنة + مسار حقيقي)."""
    t4 = df4.index.asi8
    t1 = df1.index.asi8
    o1 = df1["open"].to_numpy(); h1 = df1["high"].to_numpy()
    l1 = df1["low"].to_numpy(); c1 = df1["close"].to_numpy()
    end_t = int(t4[-1])                                     # نهاية النافذة (4h)
    sa = np.asarray(a4, dtype=float)
    sig_idx = np.flatnonzero(sig4.to_numpy())
    t_after = df4.index[1:].asi8                            # افتتاح الشمعة التالية
    pnls, exits = [], []
    busy_until = 0
    for i in sig_idx:
        if i >= len(t_after):
            continue
        te = int(t_after[i])
        if te <= busy_until or not np.isfinite(sa[i]):
            continue
        s = int(np.searchsorted(t1, te, side="left"))
        if s >= len(t1) or t1[s] > end_t:
            continue
        entry = float(o1[s]) * (1 + COST)
        hard = entry - WIN["stop"] * sa[i]
        lock_px = entry * (1 + WIN["lock"])
        peak = -np.inf; ptr = s; j = -1; px = None
        while ptr <= np.searchsorted(t1, end_t, side="right") - 1:
            e = min(ptr + CHUNK, int(np.searchsorted(t1, end_t, side="right")))
            sh = h1[ptr:e]; sl = l1[ptr:e]; so = o1[ptr:e]
            if e <= ptr:
                break
            rp = np.maximum(np.maximum.accumulate(sh), peak)
            armed = rp >= entry * (1 + WIN["trig"])
            lock = rp >= lock_px
            trail = np.where(rp <= entry * 1.01, WIN["wide"], WIN["tight"])
            eff = np.full(e - ptr, hard)
            eff = np.where(armed, np.maximum(eff, rp * (1 - trail)), eff)
            eff = np.where(lock, np.maximum(eff, lock_px), eff)
            hit = sl <= eff
            if hit.any():
                k = int(np.argmax(hit))
                j = ptr - s + k
                lvl = float(eff[k])
                px = lvl if so[k] <= lvl else float(so[k])   # فجوة → الافتتاح
                break
            peak = float(rp[-1]); ptr = e
        if j < 0:                                                # لا وقف → إغلاق عند نهاية النافذة
            j = int(np.searchsorted(t1, end_t, side="right")) - 1 - s
            j = max(j, 0)
            px = float(c1[s + j])
        fill = px * (1 - COST)
        pnls.append(C.TRADE_USD / entry * (fill - entry))
        exits.append(int(t1[s + j]))
        busy_until = int(t1[s + j])
    return pnls, exits


def main():
    t0 = time.time()
    subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"], capture_output=True)
    L36.set_core(); NC.EMA_FAST = 8; M213._cache.clear(); C.STOP_ATR = WIN["stop"]
    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    only = sys.argv[1:] or None
    if only:
        syms = [s for s in syms if s in only]
    EX = [
        ("F-042 Donchian_High_20", lambda df: (df["close"] > df["high"].shift(1).rolling(20).max()).fillna(False)),
        ("F-055 MACD_Cross_Zero", lambda df: ((ind.compute_matrix(df)["macd"] > 0) & (ind.compute_matrix(df)["macd"].shift(1) <= 0)).fillna(False)),
        ("F-063 BB_Lower_Bounce", lambda df: ((df["low"] <= ind.compute_matrix(df)["bb_low"]) & (df["close"] > df["open"])).fillna(False)),
        ("F-001 RSI2_Snap os15", lambda df: E001.make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5)),
    ]

    for si, sym in enumerate(syms, 1):
        pf_out = PARTS / f"{sym}.json"
        if pf_out.exists():
            print(f"  [{si}/{len(syms)}] {sym} — موجود مسبقاً", flush=True); continue
        ts = time.time()
        df4 = pd.read_parquet(CACHE / f"{sym}_4h.parquet")
        df1 = load_lean(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), WARM, JUD_E)
        res = {}
        for tag, (s0, s1) in (("DEC", (DEC_S, DEC_E)), ("JUD", (JUD_S, JUD_E))):
            w4 = df4[(df4.index >= s0) & (df4.index <= s1)]
            if len(w4) < 100:
                continue
            a4 = atr(w4)
            base_p, base_x = [], []
            for c in [x for x in cells if x["symbol"] == sym]:
                if c["driver"] == "F_213_breakers":
                    sg = M213.make_signals(df4, trigger=c["combo"]["trigger"]).loc[w4.index]
                else:
                    sg = R17.EXPS[c["driver"]].make_signals(df4, **c["combo"]).loc[w4.index]
                p, x = run_one_coin(w4, df1, sg, a4)
                base_p += p; base_x += x
            res[f"BASE3_{tag}_p"] = base_p; res[f"BASE3_{tag}_x"] = base_x
            for nm, fn in EX:
                p, x = run_one_coin(w4, df1, fn(df4).loc[w4.index], a4)
                res[f"{nm}_{tag}_p"] = p; res[f"{nm}_{tag}_x"] = x
            for hid, name, fn in S.HYPOTHESES:
                p, x = run_one_coin(w4, df1, fn(df4).loc[w4.index], a4)
                res[f"{hid}_{tag}_p"] = p; res[f"{hid}_{tag}_x"] = x
        pf_out.write_text(json.dumps(res), encoding="utf-8")
        del df1, df4; gc.collect()
        print(f"  [{si}/{len(syms)}] {sym} — {time.time()-ts:.0f}s", flush=True)

    # التجميع
    keys = {}
    for sym in syms:
        d = json.loads((PARTS / f"{sym}.json").read_text(encoding="utf-8"))
        for k, v in d.items():
            keys.setdefault(k, []).extend(v)
    rows = []
    for tag in ("DEC", "JUD"):
        agg = {"BASE3": []}
        for nm, _ in EX: agg[nm] = []
        for hid, name, fn in S.HYPOTHESES: agg[hid] = []
        for k in list(agg):
            agg[k] = np.array(keys.get(f"{k}_{tag}_p", []), dtype=float)
            x = np.array(keys.get(f"{k}_{tag}_x", []), dtype=np.int64)
            agg[k] = (agg[k], x)
        allb = np.concatenate([agg["BASE3"][0]] + [agg[nm][0] for nm, _ in EX])
        allx = np.concatenate([agg["BASE3"][1]] + [agg[nm][1] for nm, _ in EX])
        s = summ(allb, allx); rows.append({"البند": "الأساس (7 أعمدة)", "الفترة": tag, **s})
        print(f"★ الأساس على مسار الدقيقة [{tag}]: {s}")
        for nm, _ in EX:
            s = summ(*agg[nm]); rows.append({"البند": nm, "الفترة": tag, **s})
        for hid, name, fn in S.HYPOTHESES:
            s = summ(*agg[hid]); rows.append({"البند": f"{hid} {name}", "الفترة": tag, **s})
    pd.DataFrame(rows).to_csv(OUT / "all_columns_1m.csv", index=False, encoding="utf-8-sig")

    hyp = []
    for hid, name, fn in S.HYPOTHESES:
        d = summ(*agg0(keys, hid, "DEC")); j = summ(*agg0(keys, hid, "JUD"))
        gate = bool(d["net"] > 0 and d["pf"] >= 1.3 and d["trades"] >= 30)
        hyp.append({"الرمز": hid, "الاسم": name, "صافي_القرار$": d["net"], "صفقات_القرار": d["trades"],
                    "PF_القرار": d["pf"], "بوابة_القبول": "✓" if gate else "✗",
                    "صافي_الحكم$": j["net"], "صفقات_الحكم": j["trades"], "PF_الحكم": j["pf"],
                    "هبوط_الحكم$": j["mdd"]})
        print(f"  {hid} {name[:30]:30s} | قرار {d['net']:>8.2f}$ ({d['trades']:5d}) gate={'✓' if gate else '✗'}"
              f" | حكم {j['net']:>8.2f}$ ({j['trades']:5d})")
    pd.DataFrame(hyp).to_csv(OUT / "phase2_hypotheses_1m.csv", index=False, encoding="utf-8-sig")
    print(f"\n→ {OUT}\nالزمن الكلي {time.time()-t0:.0f}s")
    return 0


def agg0(keys, hid, tag):
    return (np.array(keys.get(f"{hid}_{tag}_p", []), dtype=float),
            np.array(keys.get(f"{hid}_{tag}_x", []), dtype=np.int64))


def summ(p, x):
    if len(p) == 0:
        return {"net": 0.0, "trades": 0, "pf": 0.0, "per": 0.0, "mdd": 0.0}
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    pf = float(g / l) if l > 0 else (np.inf if g > 0 else 0.0)
    o = np.argsort(x, kind="stable")
    eq = np.cumsum(p[o]); peak = np.maximum.accumulate(eq)
    net = round(float(p.sum()), 2)
    return {"net": net, "trades": len(p), "pf": round(pf, 4), "per": round(net / len(p), 5),
            "mdd": round(float(np.max(peak - eq)), 2)}


if __name__ == "__main__":
    raise SystemExit(main())
