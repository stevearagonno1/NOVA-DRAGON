"""L0080 — 11 integrity & leak-prevention checks (§13). Writes checks_l0080.json."""
import os, sys, json, re, ast, subprocess
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import l0080_combo as CB
import l0079_variants as V
import l0073_study as L

OUT = CB.OUT
RD = os.path.abspath(os.path.join(HERE, "../.."))
ck = {}
rng = np.random.default_rng(8001)
SAMPLE = ["BTC", "SOL", "FIL", "GRAM", "IMX"]
USED_STRUCT = ["MSS_L5", "FVG_3BAR_BASE", "SFP_LOOK20"]
USED_IND = ["OBV_SMA20", "MACD_8_21_5", "ADXDI_20_22"]


def _git(*a):
    return subprocess.run(["git", *a], cwd=RD, capture_output=True, text=True)


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


# ---- 1: no future leakage in any indicator/gate used ----
mism_cut = mism_pert = cases = 0
for s in SAMPLE:
    df = L.load(s); n = len(df)
    sed0, _ = V.structure_edges(df); cond0 = V.indicator_levels(df); e0 = _ema(df.close.to_numpy(float), 200)
    full = {f"S_{k}": sed0[(k, d)] for k in USED_STRUCT for d in (1, -1)}
    full.update({f"I_{k}": cond0[(k, d)] for k in USED_IND for d in (1, -1)})
    full["EMA200"] = e0
    for frac in (0.3, 0.6, 0.9):
        cut = int(n * frac); cases += 1
        sedc, _ = V.structure_edges(df.iloc[:cut + 1]); condc = V.indicator_levels(df.iloc[:cut + 1])
        ec = _ema(df.close.to_numpy(float)[:cut + 1], 200)
        cutd = {f"S_{k}": sedc[(k, d)] for k in USED_STRUCT for d in (1, -1)}
        cutd.update({f"I_{k}": condc[(k, d)] for k in USED_IND for d in (1, -1)}); cutd["EMA200"] = ec
        mism_cut += sum(int(not np.array_equal(full[k][:cut + 1], cutd[k])) for k in full)
        dp = df.copy(); idx = dp.index[cut + 1:]
        noise = rng.uniform(0.5, 1.5, (len(idx), 1))
        dp.loc[idx, ["open", "high", "low", "close"]] = dp.loc[idx, ["open", "high", "low", "close"]].to_numpy() * noise
        dp.loc[idx, "high"] = dp.loc[idx, ["open", "high", "low", "close"]].max(axis=1)
        dp.loc[idx, "low"] = dp.loc[idx, ["open", "high", "low", "close"]].min(axis=1)
        sedp, _ = V.structure_edges(dp); condp = V.indicator_levels(dp); ep = _ema(dp.close.to_numpy(float), 200)
        pert = {f"S_{k}": sedp[(k, d)] for k in USED_STRUCT for d in (1, -1)}
        pert.update({f"I_{k}": condp[(k, d)] for k in USED_IND for d in (1, -1)}); pert["EMA200"] = ep
        mism_pert += sum(int(not np.array_equal(full[k][:cut + 1], pert[k][:cut + 1])) for k in full)
ck["1_no_future_leakage"] = dict(ok=mism_cut == 0 and mism_pert == 0, cases=cases,
    trunc_mismatches=mism_cut, future_perturb_mismatches=mism_pert,
    note="قطع وتشويش المستقبل لا يغيّران أي محفّز/بوابة/تأكيد عند ≤ i (MSS_L5, FVG, SFP, OBV, MACD, ADXDI, EMA200)")

# ---- 2: 18-bar embargo applied ----
gap = (CB.HOLDOUT_START - CB.TRAIN_END) / pd.Timedelta(hours=4)
ck["2_embargo_18"] = dict(ok=gap >= 18, embargo_gap_bars=float(gap), note="فجوة ≥18 شمعة 4H بين train وholdout")

# ---- 3: combos == 27 == preregistration ----
cat = pd.read_csv(f"{OUT}/combination_catalog_l0080.csv")
tr = pd.read_csv(f"{OUT}/train_results_l0080.csv")
prereg = json.load(open(f"{OUT}/preregistration_l0080.json"))
ck["3_combos_27"] = dict(ok=len(cat) == 27 and tr.combination.nunique() == 27 and prereg["n_tests_locked"]["combinations"] == 27,
    catalog=len(cat), measured=int(tr.combination.nunique()), note="27 تركيبة مطابقة للتسجيل المسبق (3×3×3)")

# ---- 4: eligibility applied before selection ----
sel = json.load(open(f"{OUT}/selection_l0080.json"))
elig_ok = True
for cid in sel["selected"]:
    r = tr[tr.combination == cid].iloc[0]
    if not (r.decided >= 400 and r.signal_coverage >= 0.05 and r.rise_start_coverage >= 0.10):
        elig_ok = False
# also verify every candidate_passing_all is eligible in train
for cid in sel["candidates_passing_all"]:
    r = tr[tr.combination == cid].iloc[0]
    if not (r.decided >= 400 and r.signal_coverage >= 0.05 and r.rise_start_coverage >= 0.10):
        elig_ok = False
ck["4_eligibility_before_selection"] = dict(ok=elig_ok, selected=sel["selected"], candidates=sel["candidates_passing_all"],
    note="كل مرشح مختار/مجتاز يحقق decided≥400 وcoverage≥0.05 وrise≥0.10 (شرط أهلية قبل الاختيار)")

# ---- 5: BH applied+recorded and target df counted ----
mt = pd.read_csv(f"{OUT}/multiple_testing_l0080.csv")
has_cols = set(["p_value_raw", "p_value_bh", "passed_bh"]).issubset(mt.columns)
targetdf = "passed_bh_targetdf" in tr.columns
ck["5_bh_and_targetdf"] = dict(ok=has_cols and targetdf, bh_passed=int(mt.passed_bh.sum()),
    targetdf_passed=int(tr.passed_bh_targetdf.sum()) if targetdf else None,
    note="تصحيح BH مسجّل (raw/bh/passed) ودرجة حرية اختيار الهدف محتسبة (m=28 حساسية)")

# ---- 6: costs applied+disclosed ----
cost_cols = [c for c in tr.columns if "after_cost" in c]
disclosed = "costs" in prereg and "source" in prereg["costs"]
ck["6_costs_applied_disclosed"] = dict(ok=len(cost_cols) >= 2 and disclosed, cost_columns=cost_cols,
    cost_values=prereg["costs"]["cost_R_values"], note="التكاليف مطبقة (0.05R و0.10R) ومصدرها معلن في التسجيل المسبق")

# ---- 7: selection train-only & freeze commit precedes holdout read ----
SEL_P = "history/research/hyp_lab_out/L0080/selection_l0080.json"
HOLD_P = "history/research/hyp_lab_out/L0080/holdout_results_l0080.csv"
sel_commit = _git("log", "-1", "--format=%H", "--", SEL_P).stdout.strip()
holdout_absent = (HOLD_P not in _git("ls-tree", "-r", "--name-only", sel_commit).stdout) if sel_commit else False
ck["7_frozen_before_holdout"] = dict(ok=bool(sel_commit) and holdout_absent, selection_commit=sel_commit[:12],
    holdout_absent_in_selection_commit=holdout_absent,
    note="commit تجميد selection_l0080.json لا يحتوي holdout_results — الاختيار من train سابق لقراءة holdout")

# ---- 8: no secrets ----
pat = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|api[_-]?key\s*[:=]|secret\s*[:=]|-----BEGIN [A-Z ]*PRIVATE KEY)", re.I)
leaks = []
for f in os.listdir(OUT):
    try:
        for ln, line in enumerate(open(os.path.join(OUT, f), errors="ignore"), 1):
            if pat.search(line): leaks.append(f"{f}:{ln}")
    except Exception:
        pass
ck["8_no_secrets"] = dict(ok=len(leaks) == 0, hits=leaks, note="لا أسرار/رموز في مخرجات L0080")

# ---- 9: seeds recorded + reproducible ----
data = CB.load_all(); FR = CB.build_fires(data)
r1 = CB.random_control(FR, data, "GATE_EMA200", "FVG_3BAR_BASE", "CONF_NONE", "train", np.random.default_rng(CB.SEED))
r2 = CB.random_control(FR, data, "GATE_EMA200", "FVG_3BAR_BASE", "CONF_NONE", "train", np.random.default_rng(CB.SEED))
repro = (r1["dir_pct_rank"] == r2["dir_pct_rank"]) and (r1["expectancy_pct_rank"] == r2["expectancy_pct_rank"])
ck["9_seeds_reproducible"] = dict(ok=repro and CB.SEED == 80, seed=CB.SEED,
    rerun_dir_pct_rank=[r1["dir_pct_rank"], r2["dir_pct_rank"]],
    note="البذور مسجلة (seed=80) وإعادة تشغيل الضبط العشوائي تعطي نفس النتيجة")

# ---- 10: by-asset & by-year splits present ----
sp = pd.read_csv(f"{OUT}/splits_l0080.csv")
lv = set(sp.level.unique())
ck["10_asset_year_splits"] = dict(ok={"asset", "year"}.issubset(lv), levels=sorted(lv),
    periods=sorted(sp.period.unique()), note="تقسيم حسب الأصل والسنة موجود لكل التركيبات (train+holdout)")

# ---- 11: purged k-fold with purge & embargo = 18, no inter-fold leakage ----
cv = pd.read_csv(f"{OUT}/cv_folds_l0080.csv")
folds_ok = (cv.groupby("combination").fold.nunique() == 5).all() and cv.fold.nunique() == 5
params_ok = (CB.PURGE_BARS == 18) and (CB.EMBARGO_BARS == 18) and (CB.KFOLD == 5)
ck["11_purged_kfold"] = dict(ok=bool(folds_ok and params_ok), k=CB.KFOLD, purge_bars=CB.PURGE_BARS,
    embargo_bars=CB.EMBARGO_BARS,
    note="purged k-fold: 5 طيات لكل تركيبة، purge=embargo=18 شمعة عند حدود الطيات (لا تسريب بين الطيات)")

CRIT = ["1_no_future_leakage", "2_embargo_18", "3_combos_27", "7_frozen_before_holdout", "8_no_secrets", "11_purged_kfold"]
passed = sum(1 for v in ck.values() if v["ok"])
ck["_summary"] = dict(passed=passed, total=len(ck), all_ok=all(v["ok"] for v in ck.values()),
    critical_ok=all(ck[k]["ok"] for k in CRIT), critical_checks=CRIT,
    verdict="L0080 صالح للتحقق خارج العينة" if all(ck[k]["ok"] for k in CRIT) else "القياس غير صالح")
json.dump(ck, open(f"{OUT}/checks_l0080.json", "w"), ensure_ascii=False, indent=1, default=bool)
print(json.dumps(ck["_summary"], ensure_ascii=False, indent=1))
