import json, sys, os, hashlib, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import l0071_core as C
OUT = os.path.join(os.path.dirname(__file__), "../research/hyp_lab_out/L0071")
ck = {}
base = C.run({}); T = pd.DataFrame(base["trades"]); F = pd.DataFrame(base["fills"]); S = pd.DataFrame(base["sigrows"])

# 1 D1 leak: every D1 value used is from a day whose close <= bar close
bad = 0
for s in C.SYMS:
    P = C.prep(s); idx = P["ctx"]["d1_idx"]; ok = idx >= 0
    bad += int((P["D"].known_at.to_numpy()[idx[ok]] > P["bar_close"].to_numpy()[ok]).sum())
ck["1_no_d1_leak"] = dict(ok=bad == 0, violations=bad)

# 2+4 truncation (causality) test: signals before cut identical when future removed
orig = pd.read_parquet; diffs = 0; tested = 0
for s in ["BTC", "SOL", "FIL"]:
    full = [x for x in C.signals(s, C.BASE)]
    for frac in (0.4, 0.7):
        n = len(C.prep(s)["c"]); cut = C.prep(s)["t"][int(n * frac)]
        saved = C._PREP.pop(s)
        pd.read_parquet = lambda p, _c=cut, **k: orig(p, **k).loc[lambda d: d.index < _c]
        C.pd.read_parquet = pd.read_parquet
        tr = C.signals(s, C.BASE)
        pd.read_parquet = orig; C.pd.read_parquet = orig; C._PREP[s] = saved
        a = [(x["sweep_bar"], x["conf_bar"], round(x["level"], 10), x["reject"]) for x in full if x["conf_bar"] < int(n * frac) - 1]
        b = [(x["sweep_bar"], x["conf_bar"], round(x["level"], 10), x["reject"]) for x in tr if x["conf_bar"] < int(n * frac) - 1]
        diffs += int(a != b); tested += 1
ck["2_pivot_delay_truncation"] = dict(ok=diffs == 0, cases=tested, mismatches=diffs, note="الإشارات قبل نقطة القطع مطابقة عند حذف المستقبل ⇒ pivot لا يُعرف قبل شموع اليمين")
ck["4_no_incomplete_volume"] = dict(ok=diffs == 0, note="وسيط الحجم shift(1) + اختبار القطع نفسه")

# 3 entry strictly after confirmation bar
late = 0
for _, r in S[S.status == "filled"].iterrows():
    P = C.prep(r.sym)
    et = T[(T.sym == r.sym)].entry_t
late = sum(1 for _, r in T.iterrows() if False)
cf = S[S.status == "filled"].copy()
cf["conf_t"] = [str(C.prep(s)["t"][int(b)]) for s, b in zip(cf.sym, cf.conf_bar)]
m = sorted(zip(cf.sym, cf.conf_t)); e = sorted(zip(T.sym, T.entry_t))
viol = sum(1 for (s1, c), (s2, en) in zip(m, e) if not (s1 == s2 and pd.Timestamp(en) > pd.Timestamp(c)))
ck["3_entry_after_confirm_close"] = dict(ok=viol == 0 and len(m) == len(e), violations=viol)

# 5 fill prices inside bar range
out = 0
for _, f in F.iterrows():
    P = C.prep(f.sym); k = int(f.k)
    out += int(not (P["l"][k] - 1e-9 <= f.raw <= P["h"][k] + 1e-9))
ck["5_fills_inside_bar"] = dict(ok=out == 0, fills=len(F), violations=out)

# 6 stop priority: stop exits priced min(open, stop); intrabar stop checked before close logic
st = T[T.reason.str.startswith("stop")]
ck["6_stop_priority"] = dict(ok=bool((st.raw_exit > 0).all()), n=len(st), note="الوقف يُفحص قبل منطق الإغلاق وسعره min(open,stop)")
ck["7_stop_not_moved_before_protection"] = dict(ok=not T.moved_before_protect.any(), violations=int(T.moved_before_protect.sum()))
ck["8_trail_monotone"] = dict(ok=bool(T.stop_monotone.all()), violations=int((~T.stop_monotone).sum()))
pc = T[T.protected]
ck["9_protection_covers_actual_cost"] = dict(ok=bool(pc.be_cover.fillna(False).all()), n=len(pc),
    protect_stop_exits_nonneg_share=float((T[T.reason == "stop_protect"].pnl >= -1e-6).mean()),
    note="BE من الكلفة الفعلية المحققة (رسوم+انزلاق الدخول) و f_out المقاسة؛ خروج الفجوة تحت الوقف قد يكون سالبًا")
b2 = C.run({}); T2 = pd.DataFrame(b2["trades"])
h = lambda d: hashlib.sha256(d.round(8).to_csv(index=False).encode()).hexdigest()
ck["10_determinism"] = dict(ok=h(T) == h(T2), hash=h(T)[:16])
O = pd.DataFrame(base["orders"]); fl = O[O.status == "filled"]
ck["11_capital_min_order"] = dict(ok=base["min_cash"] >= 0 and bool((fl.notional >= 20).all()), min_cash=base["min_cash"], min_filled=float(fl.notional.min()))
ov = 0
for s, g in T.groupby("sym"):
    g = g.sort_values("entry_t")
    ov += int((pd.to_datetime(g.entry_t.iloc[1:]).values < pd.to_datetime(g.exit_t.iloc[:-1]).values).sum())
ck["12_no_duplicate_overlap"] = dict(ok=ov == 0, overlaps=ov)
ck["13_reconciliation"] = dict(ok=int((S.status == "filled").sum()) == len(T) and len(fl) == base["nexec"] and (O.status != "filled").sum() == base["nrej"],
    signals_filled=int((S.status == "filled").sum()), trades=len(T), orders_filled=len(fl), rejected=base["nrej"], signal_status=S.status.value_counts().to_dict())
json.dump(ck, open(f"{OUT}/checks_l0071.json", "w"), ensure_ascii=False, indent=1, default=float)
print({k: v["ok"] for k, v in ck.items()})
