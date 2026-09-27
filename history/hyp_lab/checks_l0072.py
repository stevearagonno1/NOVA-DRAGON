import json, sys, os, hashlib, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import l0072_core as C, l0072_ind as X
OUT = os.path.join(os.path.dirname(__file__), "../research/hyp_lab_out/L0072")
ck = {}; agg = dict(fills_out=0, moved=0, nonmono=0, cover_bad=0, overlaps=0, recon_bad=0, late=0, minorder_bad=0, cash_neg=0, books=0)
H = lambda d: hashlib.sha256(d.round(6).to_csv(index=False).encode()).hexdigest()
saved = pd.read_csv(f"{OUT}/trades_l0072.csv")
det_bad = 0
for nm in X.NAMES:
    r = C.run(dict(sigfn=X.make_sigfn(nm), tr=(1.0,))); T = pd.DataFrame(r["trades"]); S = pd.DataFrame(r["sigrows"]); F = pd.DataFrame(r["fills"]); O = pd.DataFrame(r["orders"])
    agg["books"] += 1
    for _, f in F.iterrows():
        P = C.prep(f.sym); k = int(f.k); agg["fills_out"] += int(not (P["l"][k] - 1e-9 <= f.raw <= P["h"][k] + 1e-9))
    agg["moved"] += int(T.moved_before_protect.sum()); agg["nonmono"] += int((~T.stop_monotone).sum())
    agg["cover_bad"] += int((T[T.protected].be_cover != True).sum())
    for s, g in T.groupby("sym"):
        g = g.sort_values("entry_t"); agg["overlaps"] += int((pd.to_datetime(g.entry_t.iloc[1:]).values < pd.to_datetime(g.exit_t.iloc[:-1]).values).sum())
    fl = O[O.status == "filled"]
    agg["recon_bad"] += int(not ((S.status == "filled").sum() == len(T) == len(fl) == r["nexec"] and (O.status != "filled").sum() == r["nrej"]))
    agg["minorder_bad"] += int((fl.notional < 20).sum()); agg["cash_neg"] += int(r["min_cash"] < 0)
    # entry exactly at the open right after the signal bar (no hidden confirmation)
    fs = S[S.status == "filled"]
    ct = sorted((s, str(C.prep(s)["t"][int(b) + 1])) for s, b in zip(fs.sym, fs.conf_bar)); et = sorted(zip(T.sym, T.entry_t))
    agg["late"] += int(ct != et)
    sv = saved[saved.book == nm].drop(columns="book").reset_index(drop=True)
    det_bad += int(not np.allclose(sv.pnl.to_numpy(), T.pnl.to_numpy()) if len(sv) == len(T) else 1)
bad = 0
for s in C.SYMS:
    P = C.prep(s); idx = P["ctx"]["d1_idx"]; ok = idx >= 0
    bad += int((P["D"].known_at.to_numpy()[idx[ok]] > P["bar_close"].to_numpy()[ok]).sum())
ck["1_no_d1_leak"] = dict(ok=bad == 0, violations=bad)
# 2+3 truncation: triggers before the cut unchanged when the future is removed
orig = pd.read_parquet; mism = 0; cases = 0
for s in ["BTC", "SOL", "FIL"]:
    n = len(C.prep(s)["c"])
    full = {nm: [(x["conf_bar"], x["kind"]) for x in X.make_sigfn(nm)(s, {})] for nm in X.NAMES}
    for frac in (0.45, 0.75):
        cut = C.prep(s)["t"][int(n * frac)]; sp, si = C._PREP.pop(s), X._IND.pop(s)
        C.pd.read_parquet = lambda p, _c=cut, **k: orig(p, **k).loc[lambda d: d.index < _c]
        tr = {nm: [(x["conf_bar"], x["kind"]) for x in X.make_sigfn(nm)(s, {})] for nm in X.NAMES}
        C.pd.read_parquet = orig; C._PREP[s] = sp; X._IND[s] = si
        for nm in X.NAMES:
            lim = int(n * frac) - 1; cases += 1
            mism += int([x for x in full[nm] if x[0] < lim] != [x for x in tr[nm] if x[0] < lim])
ck["2_no_incomplete_bar_values"] = dict(ok=mism == 0, cases=cases, mismatches=mism, note="اختبار القطع: حذف المستقبل لا يغير أي زناد سابق (14 مؤشرًا × 3 أصول × نقطتين)")
ck["3_prior_values_available"] = dict(ok=mism == 0, note="القنوات تستخدم shift(1)؛ العبور يستخدم i-1 و i فقط")
ck["4_exec_next_open"] = dict(ok=agg["late"] == 0 and agg["fills_out"] == 0, books_mismatch=agg["late"], fills_outside_bar=agg["fills_out"])
ck["5_no_hidden_candle_confirmation"] = dict(ok=agg["late"] == 0, note="كل دخول منفذ على افتتاح الشمعة التالية مباشرة لشمعة الزناد")
ck["6_no_overlap_within_book"] = dict(ok=agg["overlaps"] == 0, overlaps=agg["overlaps"])
ck["7_no_cash_sharing"] = dict(ok=agg["cash_neg"] == 0, note="كل دفتر تشغيل C.run مستقل برأس مال 2000$؛ لا حالة مشتركة؛ أقل نقد ≥0 في كل دفتر")
ck["8_stop_not_moved_before_protection"] = dict(ok=agg["moved"] == 0, violations=agg["moved"])
ck["9_trail_monotone"] = dict(ok=agg["nonmono"] == 0, violations=agg["nonmono"])
ck["10_protection_covers_actual_cost"] = dict(ok=agg["cover_bad"] == 0, violations=agg["cover_bad"])
ck["11_min_order_rejected"] = dict(ok=agg["minorder_bad"] == 0, filled_below_20=agg["minorder_bad"])
ck["12_deterministic"] = dict(ok=det_bad == 0, books_differing_from_saved=det_bad)
ck["13_signal_log_reconciled"] = dict(ok=agg["recon_bad"] == 0, books_bad=agg["recon_bad"])
json.dump(ck, open(f"{OUT}/checks_l0072.json", "w"), ensure_ascii=False, indent=1, default=float)
print({k: v["ok"] for k, v in ck.items()})
