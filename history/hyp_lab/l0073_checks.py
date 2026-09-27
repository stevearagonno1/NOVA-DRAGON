import os, sys, json, re, hashlib, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import l0073_study as L
OUT = L.OUT; ck = {}
S = pd.read_csv(f"{OUT}/signals_l0073.csv"); O = pd.read_csv(f"{OUT}/outcomes_l0073.csv")
rng = np.random.default_rng(7301)

# 1+2: truncation and future perturbation — signals at bars <= i unchanged
mism_cut = mism_pert = cases = 0
for s in ["BTC", "SOL", "FIL", "GRAM", "IMX"]:
    df = L.load(s); F, _ = L.fires(df); n = len(df)
    for frac in (0.3, 0.6, 0.9):
        cut = int(n * frac); cases += 1
        Ft, _ = L.fires(df.iloc[:cut + 1])
        mism_cut += sum(int(not np.array_equal(F[k][:cut + 1], Ft[k])) for k in F)
        dp = df.copy(); idx = dp.index[cut + 1:]
        noise = rng.uniform(0.5, 1.5, (len(idx), 1))
        dp.loc[idx, ["open", "high", "low", "close"]] = dp.loc[idx, ["open", "high", "low", "close"]].to_numpy() * noise
        dp.loc[idx, "high"] = dp.loc[idx, ["open", "high", "low", "close"]].max(axis=1); dp.loc[idx, "low"] = dp.loc[idx, ["open", "high", "low", "close"]].min(axis=1)
        Fp, _ = L.fires(dp)
        mism_pert += sum(int(not np.array_equal(F[k][:cut + 1], Fp[k][:cut + 1])) for k in F)
ck["1_trigger_uses_data_le_i"] = dict(ok=mism_cut == 0, cases=cases, mismatches=mism_cut, note="قطع البيانات بعد i لا يغير أي زناد ≤ i (مكونات وتركيبات، اتجاهان)")
ck["2_bar_i_plus_1_not_used"] = dict(ok=mism_pert == 0, cases=cases, mismatches=mism_pert, note="تشويش كل الشموع من i+1 عشوائيًا (±50%) لا يغير MSS/FVG/SFP ≤ i")

# 3: MAE/MFE start at i+1 — independent slow recomputation on a sample
bad3 = 0; samp = O[O.config == "base"].sample(400, random_state=73)
cache = {}
for _, r in samp.iterrows():
    if r.sym not in cache: df = L.load(r.sym); cache[r.sym] = (df, L.fires(df)[1])
    df, atr = cache[r.sym]; i = int(r.bar); a = atr[i]; c = df.close.iat[i]
    w = df.iloc[i + 1:i + 7]
    if len(w) == 0: continue
    if r.direction == "long": mfe, mae = (w.high.max() - c) / a, (c - w.low.min()) / a
    else: mfe, mae = (c - w.low.min()) / a, (w.high.max() - c) / a
    bad3 += int(not (np.isclose(mfe, r.mfe, equal_nan=True) and np.isclose(mae, r.mae, equal_nan=True)))
ck["3_mae_mfe_from_next_bar"] = dict(ok=bad3 == 0, sample=len(samp), mismatches=bad3)

# 4: no priority deletion — every edge of every component is present
miss = 0; simult = 0
for s in L.SYMS:
    df = L.load(s); F, _ = L.fires(df)
    for (name, d), f in F.items():
        n_file = int(((S.sym == s) & (S.signal == name) & (S.direction == ("long" if d == 1 else "short"))).sum())
        miss += abs(int(f.sum()) - n_file)
    for d in (1, -1):
        simult += int((np.sum([F[(c, d)] for c in L.COMP], axis=0) >= 2).sum())
ck["4_no_priority_deletion"] = dict(ok=miss == 0, count_mismatch=miss, bars_with_2plus_components_same_direction=simult,
                                    note="عدد الإشارات في الملف = مجموع الحواف لكل مكوّن؛ الإشارات المتزامنة محفوظة كلها")
aux = json.load(open(f"{OUT}/aux_l0073.json"))
S2 = L.build_signals({s: (lambda df: (df,) + L.fires(df))(L.load(s)) for s in L.SYMS})
h_file = hashlib.sha256(S.to_csv(index=False).encode()).hexdigest()
ck["5_signals_unchanged_by_outcomes"] = dict(ok=aux["signal_hash_before_outcomes"] == aux["signal_hash_after_outcomes"] == hashlib.sha256(S2.to_csv(index=False).encode()).hexdigest(),
                                             hash=aux["signal_hash_before_outcomes"][:16])
src = open(os.path.join(os.path.dirname(__file__), "l0073_study.py")).read()
code = "\n".join(x for x in src.splitlines() if not x.strip().startswith("#") and '"""' not in x)
hits = [w for w in ["fee", "commission", "slippage", "stop_loss", "capital", "equity", "position", "trail", "protect"] if re.search(rf"\b{w}\b", code, re.I)]
ck["6_no_costs_or_trade_management"] = dict(ok=not hits, found=hits)
pr = json.load(open(f"{OUT}/preregistration_l0073.json"))
ck["7_params_as_preregistered"] = dict(ok=L.CFG == {"base": (1.0, 1.0, 6), "sens": (2.0, 1.0, 18)} and L.COMBO_WIN == 3 and L.PRE == 3 and L.SEED == 73 and L.NDRAW == 1000
                                       and pr["random_control"]["seed"] == 73 and pr["outcome_sensitivity"]["horizon"] == 18,
                                       nova_defaults="mss L=5، sfp look=20، ATR 14 — قيم nova_v8 الافتراضية دون تمرير")
pat = re.compile("(" + "|".join(["gh" + "p_[A-Za-z0-9]{20,}", "github" + "_pat_", "x-access" + "-token", "AK" + "IA[0-9A-Z]{16}", "-----BEG" + "IN"]) + ")")
root = L.ROOT; found = []
for p in [f"{OUT}/{f}" for f in os.listdir(OUT)] + [os.path.join(os.path.dirname(__file__), f) for f in ("l0073_study.py", "l0073_checks.py")]:
    if os.path.isfile(p) and pat.search(open(p, errors="ignore").read()): found.append(os.path.basename(p))
ck["8_no_secrets"] = dict(ok=not found, files=found)
ck["all_ok"] = all(v["ok"] for v in ck.values() if isinstance(v, dict))
json.dump(ck, open(f"{OUT}/checks_l0073.json", "w"), ensure_ascii=False, indent=1, default=float)
print({k: (v["ok"] if isinstance(v, dict) else v) for k, v in ck.items()})
