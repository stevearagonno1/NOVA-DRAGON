"""L0079 integrity & leak-prevention checks (§8). Writes checks_l0079.json.
Critical failures (1,2,3,6,8) => measurement invalid for out-of-sample."""
import os, sys, json, re, ast, subprocess
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import l0079_variants as V
import l0073_study as L

OUT = V.OUT
RD = os.path.abspath(os.path.join(HERE, "../.."))
ck = {}
rng = np.random.default_rng(7901)
SAMPLE = ["BTC", "SOL", "FIL", "GRAM", "IMX"]


def _git(*a):
    return subprocess.run(["git", *a], cwd=RD, capture_output=True, text=True)


# ---- 1: every variant causal (truncation + future perturbation) ----
mism_cut = mism_pert = cases = 0
for s in SAMPLE:
    df = L.load(s); n = len(df)
    sed0, _ = V.structure_edges(df); cond0 = V.indicator_levels(df)
    full = {**sed0, **cond0}
    for frac in (0.3, 0.6, 0.9):
        cut = int(n * frac); cases += 1
        sedc, _ = V.structure_edges(df.iloc[:cut + 1]); condc = V.indicator_levels(df.iloc[:cut + 1])
        cutd = {**sedc, **condc}
        mism_cut += sum(int(not np.array_equal(full[k][:cut + 1], cutd[k])) for k in full)
        dp = df.copy(); idx = dp.index[cut + 1:]
        noise = rng.uniform(0.5, 1.5, (len(idx), 1))
        dp.loc[idx, ["open", "high", "low", "close"]] = dp.loc[idx, ["open", "high", "low", "close"]].to_numpy() * noise
        dp.loc[idx, "high"] = dp.loc[idx, ["open", "high", "low", "close"]].max(axis=1)
        dp.loc[idx, "low"] = dp.loc[idx, ["open", "high", "low", "close"]].min(axis=1)
        sedp, _ = V.structure_edges(dp); condp = V.indicator_levels(dp)
        pert = {**sedp, **condp}
        mism_pert += sum(int(not np.array_equal(full[k][:cut + 1], pert[k][:cut + 1])) for k in full)
ck["1_variants_causal"] = dict(ok=mism_cut == 0 and mism_pert == 0, cases=cases,
    trunc_mismatches=mism_cut, future_perturb_mismatches=mism_pert,
    note="قطع الإطار بعد i وتشويش المستقبل لا يغيّران أي إشارة نسخة عند ≤ i (بنية + مؤشرات)")

# ---- 2: every measured variant_id has a registered setting in catalog + preregistration ----
cat = pd.read_csv(f"{OUT}/variant_catalog_l0079.csv")
measured = set(pd.read_csv(f"{OUT}/train_results_l0079.csv").variant_id) | set(pd.read_csv(f"{OUT}/holdout_results_l0079.csv").variant_id)
cat_ids = set(cat.variant_id)
prereg = json.load(open(f"{OUT}/preregistration_l0079.json"))
missing_params = [r.variant_id for _, r in cat.iterrows() if r.track != "pending" and (pd.isna(r.parameters) or r.parameters in ("", "{}"))]
ck["2_every_variant_registered"] = dict(ok=measured.issubset(cat_ids) and len(missing_params) == 0,
    measured=len(measured), catalog=len(cat_ids), unregistered=sorted(measured - cat_ids), missing_params=missing_params,
    note="كل variant_id مُقاس له سطر في variant_catalog مع parameters وsignal_definition مسجّلين")

# ---- 3: names frozen before holdout (durable git-history proof) ----
SEL_P = "history/research/hyp_lab_out/L0079/selection_l0079.json"
HOLD_P = "history/research/hyp_lab_out/L0079/holdout_results_l0079.csv"
sel_commit = _git("log", "-1", "--format=%H", "--", SEL_P).stdout.strip()
holdout_absent = True
if sel_commit:
    holdout_absent = HOLD_P not in _git("ls-tree", "-r", "--name-only", sel_commit).stdout
ck["3_frozen_before_holdout"] = dict(ok=bool(sel_commit) and holdout_absent,
    selection_commit=sel_commit[:12], holdout_absent_in_selection_commit=holdout_absent,
    note="commit تجميد selection_l0079.json لا يحتوي holdout_results — إثبات دائم أن الاختيار سبق قراءة holdout")

# ---- 4: Bollinger & Z-Score one family (only BB_* variants; no standalone Z) ----
bb_fam = set(cat[cat.family == "BB"].variant_id)
no_z = not any(re.search(r"(?<![A-Za-z])z(?:score|_)?", v, re.I) and not v.startswith("BB_") for v in cat.variant_id)
ck["4_bollinger_zscore_one_family"] = dict(ok=(len(bb_fam) == 3) and no_z, bb_variants=sorted(bb_fam),
    note="عائلة Bollinger/Z واحدة: نسخ BB_* فقط؛ لا نسخة Z مستقلة (BB_20_2.0 long ≡ z<=-2 عند p=20)")

# ---- 5: VPFR uses no manual range chosen after seeing a chart ----
vpfr = cat[cat.family == "VPFR"]
vpfr_pending = (len(vpfr) == 1) and (vpfr.iloc[0].track == "pending") and (vpfr.iloc[0].variant_id == "VPFR_PENDING")
vpfr_not_measured = "VPFR_PENDING" not in measured and not any(v.startswith("VPFR") and v != "VPFR_PENDING" for v in cat_ids)
ck["5_vpfr_no_manual_range"] = dict(ok=vpfr_pending and vpfr_not_measured,
    note="VPFR مسجّل PENDING فقط ولم يُشغّل؛ لا نطاق يدوي اختير بعد رؤية الرسم")

# ---- 6: train separated from holdout (embargo >= 18 bars, disjoint periods) ----
gap_bars = (V.HOLDOUT_START - V.TRAIN_END) / pd.Timedelta(hours=4)
disjoint = V.TRAIN_END <= V.HOLDOUT_START
ck["6_train_holdout_separated"] = dict(ok=(gap_bars >= V.EMBARGO_BARS) and disjoint,
    embargo_gap_bars=float(gap_bars), embargo_required=V.EMBARGO_BARS,
    note="فترة الحظر ≥18 شمعة 4H تفصل train عن holdout والفترتان غير متداخلتين")

# ---- 7: no trade management / costs (AST identifiers) ----
banned = {"fee", "fees", "slippage", "slip", "commission", "stop", "stoploss", "trail", "trailing",
          "position", "positions", "qty", "capital", "pnl", "leverage", "notional", "cooldown"}
idents = set()
for node in ast.walk(ast.parse(open(os.path.join(HERE, "l0079_variants.py")).read())):
    if isinstance(node, ast.Name): idents.add(node.id.lower())
    elif isinstance(node, ast.Attribute): idents.add(node.attr.lower())
    elif isinstance(node, ast.FunctionDef): idents.add(node.name.lower())
    elif isinstance(node, ast.arg): idents.add(node.arg.lower())
hits = sorted(idents & banned)
ck["7_no_costs_or_trade_mgmt"] = dict(ok=len(hits) == 0, offending_identifiers=hits,
    note="لا رسوم/وقف/إدارة صفقة/رأس مال كمعرّفات فعلية في كود L0079")

# ---- 8: no secrets / tokens in any L0079 output ----
pat = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|api[_-]?key\s*[:=]|secret\s*[:=]|-----BEGIN [A-Z ]*PRIVATE KEY)", re.I)
leaks = []
for f in os.listdir(OUT):
    try:
        for ln, line in enumerate(open(os.path.join(OUT, f), errors="ignore"), 1):
            if pat.search(line): leaks.append(f"{f}:{ln}")
    except Exception:
        pass
ck["8_no_secrets_in_outputs"] = dict(ok=len(leaks) == 0, hits=leaks, note="فحص كل ملفات L0079 من الأسرار ورموز الوصول")

CRIT = ["1_variants_causal", "2_every_variant_registered", "3_frozen_before_holdout",
        "6_train_holdout_separated", "8_no_secrets_in_outputs"]
passed = sum(1 for v in ck.values() if v["ok"])
ck["_summary"] = dict(passed=passed, total=len(ck), all_ok=all(v["ok"] for v in ck.values()),
    critical_ok=all(ck[k]["ok"] for k in CRIT), critical_checks=CRIT,
    verdict="L0079 صالح للاختبار خارج العينة" if all(ck[k]["ok"] for k in CRIT) else "القياس غير صالح للاختبار خارج العينة")
json.dump(ck, open(f"{OUT}/checks_l0079.json", "w"), ensure_ascii=False, indent=1, default=bool)
print(json.dumps(ck["_summary"], ensure_ascii=False, indent=1))
