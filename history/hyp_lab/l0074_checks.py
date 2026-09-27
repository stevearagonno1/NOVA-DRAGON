"""L0074 leak-prevention & integrity checks (§10). Writes checks_l0074.json.
A critical failure (checks 1,2,3,4,5,6,9) invalidates L0074."""
import os, sys, json, re, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import l0073_study as L
import l0074_study as X

OUT = X.OUT
ck = {}
rng = np.random.default_rng(7401)
SAMPLE_SYMS = ["BTC", "SOL", "FIL", "GRAM", "IMX"]

# ---- 1 & 5: classic condition at i uses data <= i (truncation invariance) ----
# ---- 2: same-bar confirmation does not use bar i+1 (future perturbation) ----
mism_cut = mism_pert = cases = 0
for s in SAMPLE_SYMS:
    df = L.load(s); cond = X.classic_conditions(df); n = len(df)
    for frac in (0.3, 0.6, 0.9):
        cut = int(n * frac); cases += 1
        ct = X.classic_conditions(df.iloc[:cut + 1])
        mism_cut += sum(int(not np.array_equal(cond[k][:cut + 1], ct[k])) for k in cond)
        dp = df.copy(); idx = dp.index[cut + 1:]
        noise = rng.uniform(0.5, 1.5, (len(idx), 1))
        dp.loc[idx, ["open", "high", "low", "close"]] = dp.loc[idx, ["open", "high", "low", "close"]].to_numpy() * noise
        dp.loc[idx, "high"] = dp.loc[idx, ["open", "high", "low", "close"]].max(axis=1)
        dp.loc[idx, "low"] = dp.loc[idx, ["open", "high", "low", "close"]].min(axis=1)
        cp = X.classic_conditions(dp)
        mism_pert += sum(int(not np.array_equal(cond[k][:cut + 1], cp[k][:cut + 1])) for k in cond)
ck["1_classic_uses_data_le_i"] = dict(ok=mism_cut == 0, cases=cases, mismatches=mism_cut,
    note="قطع الإطار بعد i لا يغيّر أي شرط تأكيد كلاسيكي عند ≤ i (المؤشرات السبعة، اتجاهان)")
ck["2_same_bar_no_future"] = dict(ok=mism_pert == 0, cases=cases, mismatches=mism_pert,
    note="تشويش عشوائي (±50%) لكل شمعة بعد i لا يغيّر أي شرط تأكيد عند ≤ i — التأكيد على i سببي")

# ---- 3: one-bar-lag decision uses classic at i+1 only, not beyond ----
mism_lag = 0; lcases = 0
for s in SAMPLE_SYMS:
    df = L.load(s); cond = X.classic_conditions(df); n = len(df)
    for frac in (0.3, 0.6, 0.9):
        cut = int(n * frac); lcases += 1
        dp = df.copy(); idx = dp.index[cut + 2:]                 # perturb strictly after i+1 (i=cut)
        noise = rng.uniform(0.5, 1.5, (len(idx), 1))
        dp.loc[idx, ["open", "high", "low", "close"]] = dp.loc[idx, ["open", "high", "low", "close"]].to_numpy() * noise
        dp.loc[idx, "high"] = dp.loc[idx, ["open", "high", "low", "close"]].max(axis=1)
        dp.loc[idx, "low"] = dp.loc[idx, ["open", "high", "low", "close"]].min(axis=1)
        cp = X.classic_conditions(dp)
        mism_lag += sum(int(not np.array_equal(cond[k][:cut + 2], cp[k][:cut + 2])) for k in cond)
ck["3_lag_decision_at_i_plus_1_only"] = dict(ok=mism_lag == 0, cases=lcases, mismatches=mism_lag,
    note="تشويش كل الشموع بعد i+1 لا يغيّر شرط التأكيد عند i+1؛ نافذة النتيجة للمسار المتأخر تبدأ بنيويًا عند i+2 (decision_bar=i+1)")

# ---- 3b: lag outcome window structurally starts after the confirmation bar ----
CONF = pd.read_csv(f"{OUT}/outcomes_l0074.csv")
lag_ok = bool((CONF[CONF.path == "lag"].decision_bar == CONF[CONF.path == "lag"].bar + 1).all())
same_ok = bool((CONF[CONF.path == "same"].decision_bar == CONF[CONF.path == "same"].bar).all())
ck["3b_decision_bar_construction"] = dict(ok=lag_ok and same_ok,
    note="same: decision_bar=i؛ lag: decision_bar=i+1 (نتيجة i+1 تقيس من i+2..) — تحقق بنيوي من الجدول")

# ---- 4 & 6: raw structure signals identical to L0073 (no priority deletion, count unchanged) ----
S74 = pd.read_csv(f"{OUT}/signals_l0074.csv")
S73 = pd.read_csv(os.path.join(os.path.dirname(OUT), "L0073/signals_l0073.csv"))
S73c = S73[~S73.signal.str.contains(r"\+")]                       # components only
c74 = S74.groupby(["structure", "direction"]).size().to_dict()
c73 = S73c.groupby(["signal", "direction"]).size().to_dict()
same_counts = all(c74.get((sig, d), 0) == n for (sig, d), n in c73.items()) and \
    all(c73.get((sig, d), 0) == n for (sig, d), n in c74.items())
# exact same (sym,bar,structure,direction) set
key74 = set(map(tuple, S74[["sym", "bar", "structure", "direction"]].itertuples(index=False, name=None)))
key73 = set(map(tuple, S73c[["sym", "bar", "signal", "direction"]].itertuples(index=False, name=None)))
strk = lambda dd: {f"{a}_{b}": int(v) for (a, b), v in dd.items()}
ck["4_no_priority_deletion_counts_eq_L0073"] = dict(ok=same_counts and key74 == key73,
    counts_L0074=strk(c74), counts_L0073=strk(c73), exact_set_match=key74 == key73,
    note="عدد ومطابقة إشارات البنية الخام (MSS/FVG/SFP، اتجاهان) = L0073 حرفيًا — لا حذف بالأولوية")

# hash stability
res = X.main()  # recompute (writes files again identically)
ck["6_raw_signal_hash_stable"] = dict(ok=res["sig_hash_before"] == res["sig_hash_after"],
    hash=res["sig_hash_before"], note="قائمة إشارات البنية لا تتغير قبل/بعد حساب النتائج")

# ---- 7: no costs / trade management / stop in the study code (identifiers only, ignoring docstrings/comments) ----
import ast, tokenize, io
banned = {"fee", "fees", "slippage", "slip", "commission", "stop", "stoploss", "trail", "trailing",
          "position", "positions", "qty", "capital", "pnl", "leverage", "notional", "risk", "cooldown"}
src_code = open(os.path.join(HERE, "l0074_study.py")).read()
idents = set()
for node in ast.walk(ast.parse(src_code)):
    if isinstance(node, ast.Name):
        idents.add(node.id.lower())
    elif isinstance(node, ast.Attribute):
        idents.add(node.attr.lower())
    elif isinstance(node, (ast.FunctionDef, ast.arg)):
        idents.add(getattr(node, "name", getattr(node, "arg", "")).lower())
hits = sorted(idents & banned)
ck["7_no_costs_or_trade_mgmt"] = dict(ok=len(hits) == 0, offending_identifiers=hits,
    note="لا رسوم/وقف/إدارة صفقة/رأس مال كمعرّفات فعلية في كود الدراسة (تُتجاهل السلاسل الوصفية والتعليقات)")

# ---- 8: no selection from results — constants match preregistration ----
prereg = json.load(open(f"{OUT}/preregistration_l0074.json"))
p_classic = prereg["classic_confirmation_indicators"]["list"]
p_cons = prereg["confirmation_paths"]["consensus"]["thresholds"]
p_paths = ["same_bar", "one_bar_lag"]
ok8 = (X.CLASSIC == p_classic and X.CONSENSUS == p_cons and X.SEED == prereg["random_control"]["seed"]
       and sorted(X.CFG.keys()) == ["base", "sens"])
ck["8_no_selection_from_results"] = dict(ok=bool(ok8), classic=X.CLASSIC, consensus=X.CONSENSUS,
    seed=X.SEED, note="أسماء المؤشرات السبعة وعتبات الإجماع ونوافذ التأكيد والبذرة مقفلة في التسجيل المسبق، غير مختارة من النتائج")

# ---- 9: no secrets / access tokens in any L0074 output file ----
pat = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|api[_-]?key\s*[:=]|secret\s*[:=]|-----BEGIN [A-Z ]*PRIVATE KEY)", re.I)
leaks = []
for f in os.listdir(OUT):
    p = os.path.join(OUT, f)
    try:
        with open(p, "r", errors="ignore") as fh:
            for ln, line in enumerate(fh, 1):
                if pat.search(line):
                    leaks.append(f"{f}:{ln}")
    except Exception:
        pass
ck["9_no_secrets_in_outputs"] = dict(ok=len(leaks) == 0, hits=leaks, note="فحص كل ملفات L0074 من الأسرار ورموز الوصول")

CRITICAL = ["1_classic_uses_data_le_i", "2_same_bar_no_future", "3_lag_decision_at_i_plus_1_only",
            "3b_decision_bar_construction", "4_no_priority_deletion_counts_eq_L0073",
            "6_raw_signal_hash_stable", "9_no_secrets_in_outputs"]
passed = sum(1 for v in ck.values() if v["ok"])
ck["_summary"] = dict(passed=passed, total=len(ck) - 0, all_ok=all(v["ok"] for k, v in ck.items() if k != "_summary"),
    critical_ok=all(ck[k]["ok"] for k in CRITICAL), critical_checks=CRITICAL,
    verdict="L0074 صالح" if all(ck[k]["ok"] for k in CRITICAL) else "L0074 غير صالح")
json.dump(ck, open(f"{OUT}/checks_l0074.json", "w"), ensure_ascii=False, indent=1, default=bool)
print(json.dumps(ck["_summary"], ensure_ascii=False, indent=1))

if __name__ == "__main__":
    pass
