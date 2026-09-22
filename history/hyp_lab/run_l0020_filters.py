# -*- coding: utf-8 -*-
"""L0020 — جولة الفلاتر + استخراج الدرس (أمر القائد: نتعلم من تقنياتها)."""
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd
_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))
HIST = pathlib.Path(__file__).resolve().parents[1]; ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C
from common import atr, simulate, trade_rows
from measure_l0010_gate import drawdown_stats, longest_losing_streak, psr_dsr
import run_l0019_unified as R19
OUT = HIST / "research" / "hyp_lab_out" / "L0020"
TS, TE = "2025-01-01", "2026-08-31"; BAR = 4*3600
YEARS = (pd.Timestamp(TE, tz="UTC") - pd.Timestamp(TS, tz="UTC")).days / 365.25
MA_LEN, SLOPE_LB, FLAT_LB, FLAT_R = 200, 20, 50, 1.0
def f_ma(df): return df["close"] > df["close"].rolling(MA_LEN, min_periods=MA_LEN).mean()
def f_slope(df):
    ma = df["close"].rolling(MA_LEN, min_periods=MA_LEN).mean(); return ma > ma.shift(SLOPE_LB)
def f_flat(df):
    rng = df["close"].rolling(FLAT_LB).max() - df["close"].rolling(FLAT_LB).min()
    return rng > (FLAT_R * atr(df) * np.sqrt(FLAT_LB))
FILTERS = {"فوق المتوسط": f_ma, "ليس هابطًا": f_slope, "ليس عرضيًا": f_flat}
VARIANTS = [("بلا فلتر (المحفظة كما هي)", []), ("فوق المتوسط", ["فوق المتوسط"]),
            ("ليس هابطًا", ["ليس هابطًا"]), ("ليس عرضيًا", ["ليس عرضيًا"]),
            ("الثلاثي كاملًا", list(FILTERS))]
def pf(p):
    g, l = p[p>0].sum(), -p[p<0].sum(); return float(g/l) if l>0 else (np.inf if g>0 else 0.0)
def run_cell(c, df, names):
    win = df[(df.index>=TS)&(df.index<=TE)]
    if c["driver"] == "F_213_breakers":
        import F_213_breakers as M
        sig = M.make_signals(df, trigger=c["combo"]["trigger"])
        kw = {"exit_mode":"dual","dual":M.make_dual_spec()} if c["combo"]["exit"]=="dual" else {"exit_mode":"std"}
    else:
        import F_197_dual_trail as M197, run_l0017 as R17
        sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"])
        kw = {"exit_mode":"dual","dual":M197.make_dual_spec(trig=0.0025, lock=0.0045)}
    if names:
        ok = pd.Series(True, index=df.index)
        for n in names: ok &= FILTERS[n](df).reindex(df.index).fillna(False)
        sig = sig.where(ok, 0)
    sig = sig.loc[win.index]
    _, tr = simulate(win, sig, atr(win), notional=C.TRADE_USD, bar_secs=BAR, **kw)
    rows = trade_rows(c["symbol"], c["driver"], tr)
    for r in rows: r["driver"] = c["driver"]
    return rows
def block(name, d, nt):
    if d.empty: return {"التركيبة":name,"صفقات":0,"صافي$":0.0}
    d = d.copy(); d["exit_time"]=pd.to_datetime(d["exit_time"],utc=True); d=d.sort_values("exit_time")
    p = d["pnl"].to_numpy(float); dd, dys, _ = drawdown_stats(d["exit_time"], p)
    day = d.groupby(d["exit_time"].dt.date)["pnl"].sum(); z = psr_dsr(p, YEARS, nt)
    w, l = p[p>0], p[p<0]
    return {"التركيبة":name,"عملات":int(d["symbol"].nunique()),"صفقات":len(d),
        "صافي$":round(float(p.sum()),2),"عامل الربح":round(pf(p),4),
        "فوز%":round(100*float((p>0).mean()),2),"نصيب الصفقة$":round(float(p.sum()/len(d)),4),
        "متوسط الرابحة$":round(float(w.mean()),4) if len(w) else 0.0,
        "متوسط الخاسرة$":round(float(l.mean()),4) if len(l) else 0.0,
        "نسبة العائد":round(float(w.mean()/abs(l.mean())),4) if len(l) and len(w) else 0.0,
        "أقصى هبوط$":round(dd,2),"مدة الهبوط(يوم)":round(dys,1),
        "أسوأ يوم$":round(float(day.min()),2),"أطول سلسلة خسائر":longest_losing_streak(p),
        "عمولات$":round(2*0.0013*C.TRADE_USD*len(d),2),"DSR":z["dsr"],"z":z["dsr_z"]}
def main():
    t0=time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"], capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok": print("الكاناري فشل", file=sys.stderr); return 1
    print(f"الكاناري: PASS (net={cj['got']['net']})\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 260)
    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    store = {v[0]: [] for v in VARIANTS}
    for s in syms:
        df = R19.frame(s); mine=[x for x in cells if x["symbol"]==s]
        for vn, fn in VARIANTS:
            for c in mine: store[vn].extend(run_cell(c, df, fn))
        print(f"  {s}: تمّت", flush=True); del df
    nt = 32*13 + (36+27)*8; rows=[]
    for i,(vn,_) in enumerate(VARIANTS):
        t = pd.DataFrame(store[vn]); t.to_csv(OUT/f"trades_{i}.csv", index=False, encoding="utf-8-sig")
        rows.append(block(vn, t, nt))
    summ = pd.DataFrame(rows); b = rows[0]
    summ["فرق الصافي$"]=[round(r["صافي$"]-b["صافي$"],2) for r in rows]
    summ["فرق الهبوط$"]=[round(r.get("أقصى هبوط$",0)-b["أقصى هبوط$"],2) for r in rows]
    summ["ربح لكل دولار خطر"]=(summ["صافي$"]/summ["أقصى هبوط$"]).round(2)
    summ.to_csv(OUT/"filters_compare_4h.csv", index=False, encoding="utf-8-sig")
    print("\n"+"="*130); print("أثر الفلاتر على المحفظة الموحدة — مسطرة 20$/صفقة"); print("="*130)
    print(summ[["التركيبة","صفقات","صافي$","فرق الصافي$","عامل الربح","متوسط الخاسرة$",
                "نسبة العائد","أقصى هبوط$","فرق الهبوط$","أسوأ يوم$","ربح لكل دولار خطر"]].to_string(index=False), flush=True)
    # ===== الدرس: ماذا حذف كل فلتر بالضبط =====
    d = {v[0]: pd.DataFrame(store[v[0]]) for v in VARIANTS}
    base = d[VARIANTS[0][0]]; key=["symbol","driver","entry_time"]; L=[]
    for vn,_ in VARIANTS[1:]:
        m = base.merge(d[vn][key], on=key, how="left", indicator=True)
        rem = m[m["_merge"]=="left_only"]; w=rem[rem.pnl>0]; l=rem[rem.pnl<0]
        L.append({"الفلتر":vn,"حذف":len(rem),"منها رابحة":len(w),"منها خاسرة":len(l),
                  "ربح ضائع$":round(w.pnl.sum(),2),"خسارة موفَّرة$":round(-l.pnl.sum(),2),
                  "صافي المحذوف$":round(rem.pnl.sum(),2),
                  "ضيّع مقابل كل دولار وفّره":round(w.pnl.sum()/-l.pnl.sum(),2) if l.pnl.sum()!=0 else 0.0})
    ld = pd.DataFrame(L); ld.to_csv(OUT/"lesson_removed_4h.csv", index=False, encoding="utf-8-sig")
    print("\n— الدرس: ماذا حذف كل فلتر —"); print(ld.to_string(index=False), flush=True)
    worst = base.nsmallest(30,"pnl"); W=[]
    for vn,_ in VARIANTS[1:]:
        m = worst.merge(d[vn][key], on=key, how="left", indicator=True)
        W.append({"الفلتر":vn,"أبقى من أسوأ 30":int((m["_merge"]=="both").sum()),
                  "منع منها":int((m["_merge"]=="left_only").sum())})
    wd = pd.DataFrame(W); wd.to_csv(OUT/"lesson_worst30_4h.csv", index=False, encoding="utf-8-sig")
    print(f"\n— هل يمسّ الفلترُ الألمَ الحقيقي؟ (أسوأ 30 صفقة = {worst.pnl.sum():.2f}$) —")
    print(wd.to_string(index=False), flush=True)
    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nnotional={C.TRADE_USD}$\nwindow={TS}→{TE}\ncost=0.13%/side\n"
        f"ma={MA_LEN} slope={SLOPE_LB} flat={FLAT_LB}/{FLAT_R}\ncells={len(cells)} symbols={len(syms)}\n"
        f"note=لا إعادة اختيار — الفلتر وحده المتغيّر\n", encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True); return 0
if __name__ == "__main__": raise SystemExit(main())
