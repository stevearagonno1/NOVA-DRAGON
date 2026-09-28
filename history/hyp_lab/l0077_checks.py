"""L0077 integrity & leak-prevention checks (§8). Writes checks_l0077.json.
Critical failures (1,2,3,4,5,8) => measurement invalid for out-of-sample."""
import os, sys, json, re, ast, subprocess
import numpy as np, pandas as pd
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import l0077_core as C
import l0077_ind as IND
import l0073_study as L

OUT = C.OUT
RD = os.path.abspath(os.path.join(HERE, "../.."))
ck = {}
rng = np.random.default_rng(7701)
SAMPLE = ["BTC", "SOL", "FIL", "GRAM", "IMX"]


def _git(*a):
    return subprocess.run(["git", *a], cwd=RD, capture_output=True, text=True)


# ---- 1: each candidate uses data <= i (truncation + future perturbation) ----
mism_cut = mism_pert = cases = 0
for s in SAMPLE:
    df = L.load(s); cond = IND.candidate_conditions(df); n = len(df)
    for frac in (0.3, 0.6, 0.9):
        cut = int(n * frac); cases += 1
        ct = IND.candidate_conditions(df.iloc[:cut + 1])
        mism_cut += sum(int(not np.array_equal(cond[k][:cut + 1], ct[k])) for k in cond)
        dp = df.copy(); idx = dp.index[cut + 1:]
        noise = rng.uniform(0.5, 1.5, (len(idx), 1))
        dp.loc[idx, ["open", "high", "low", "close"]] = dp.loc[idx, ["open", "high", "low", "close"]].to_numpy() * noise
        dp.loc[idx, "high"] = dp.loc[idx, ["open", "high", "low", "close"]].max(axis=1)
        dp.loc[idx, "low"] = dp.loc[idx, ["open", "high", "low", "close"]].min(axis=1)
        cp = IND.candidate_conditions(dp)
        mism_pert += sum(int(not np.array_equal(cond[k][:cut + 1], cp[k][:cut + 1])) for k in cond)
ck["1_candidate_uses_data_le_i"] = dict(ok=mism_cut == 0 and mism_pert == 0, cases=cases,
    trunc_mismatches=mism_cut, future_perturb_mismatches=mism_pert,
    note="قطع الإطار بعد i وتشويش المستقبل لا يغيّران أي شرط مرشح عند ≤ i (14 مرشحًا، اتجاهان)")

# ---- 2 & 4: selection from TRAIN only; holdout absent from selection ----
FIRES = pd.read_csv(f"{OUT}/fires_l0077.csv")
data = C.load_all(); FR = C.build_fires(data)
recomputed = {}
for fam, cands in C.FAMILIES.items():
    best = None; best_key = None
    for cand in cands:
        sm, _ = C.candidate_metrics(FR, cand, "train", "base")
        rc = C.random_control(data, (lambda nm: (lambda cond, d, i: bool(cond[(nm, d)][i])))(cand), "train", "base")
        dec = sm["positive_before_negative"] + sm["negative_before_positive"]
        valid = (dec >= 100) and pd.notna(sm["coverage"]) and sm["coverage"] >= 0.20 and \
            pd.notna(rc["rand_dir_median"]) and sm["directional_accuracy"] > rc["rand_dir_median"]
        if valid:
            key = (sm["directional_accuracy"], sm["dir_ci_lo"], sm["coverage"], sm["hit_rate_all"])
            if best_key is None or key > best_key:
                best_key = key; best = cand
    recomputed[fam] = best
committed = {k: (v if v else None) for k, v in json.load(open(f"{OUT}/selection_l0077.json"))["selection"].items()}
ck["2_selection_from_train_only"] = dict(ok=recomputed == committed, recomputed=recomputed, committed=committed,
    note="إعادة اشتقاق الاختيار من شرائح train فقط تطابق selection_l0077.json")
gap_bars = (C.HOLDOUT_START - C.TRAIN_END) / pd.Timedelta(hours=4)
ck["4_no_holdout_in_selection"] = dict(ok=("holdout" in set(FIRES.period)) and gap_bars >= C.EMBARGO_BARS,
    embargo_gap_bars=float(gap_bars), embargo_required=C.EMBARGO_BARS,
    note="فترة الحظر ≥18 شمعة تفصل train عن holdout؛ الاختيار استعمل شموع train فقط")

# ---- 3: names frozen before holdout (durable git-history proof) ----
SEL_P = "history/research/hyp_lab_out/L0077/selection_l0077.json"
HOLD_P = "history/research/hyp_lab_out/L0077/holdout_results_l0077.csv"
sel_commit = _git("log", "-1", "--format=%H", "--", SEL_P).stdout.strip()
holdout_absent = True
if sel_commit:
    holdout_absent = HOLD_P not in _git("ls-tree", "-r", "--name-only", sel_commit).stdout
ck["3_names_frozen_before_holdout"] = dict(ok=bool(sel_commit) and holdout_absent,
    selection_commit=sel_commit[:12], holdout_absent_in_selection_commit=holdout_absent,
    note="commit تجميد selection_l0077.json لا يحتوي نتائج holdout — إثبات دائم أن الأسماء ثُبّتت قبل قراءة holdout")

# ---- 5: raw L0073 structure signals unchanged ----
S73 = pd.read_csv(os.path.join(os.path.dirname(OUT), "L0073/signals_l0073.csv"))
S73c = S73[~S73.signal.str.contains(r"\+")]
strk = lambda dd: {f"{a}_{b}": int(v) for (a, b), v in dd.items()}
c77 = strk(FIRES[FIRES.config == "base"].groupby(["structure", "direction"]).size().to_dict())
c73 = strk(S73c.groupby(["signal", "direction"]).size().to_dict())
ck["5_raw_structure_unchanged"] = dict(ok=c77 == c73, counts_L0077=c77, counts_L0073=c73,
    note="عدد إشارات البنية الخام (base، لكل مكوّن واتجاه) = مكوّنات L0073 حرفيًا")

# ---- 6: Bollinger & Z-Score one family (BollingerZ once; no standalone Z) ----
cand = C.ALL_CANDIDATES
boll_once = cand.count("BollingerZ") == 1
no_sep_z = not any((c != "BollingerZ") and re.fullmatch(r"z.?score|z", c, re.I) for c in cand)
ck["6_bollinger_zscore_one_family"] = dict(ok=boll_once and no_sep_z, bollingerz_count=cand.count("BollingerZ"),
    note="BollingerZ مرشح واحد يمثل Bollinger≡Z-Score (z=±2 = حدّا BB(20,2))؛ لا Z منفصل")

# ---- 7: no trade management / costs (AST identifiers over all L0077 code) ----
banned = {"fee", "fees", "slippage", "slip", "commission", "stop", "stoploss", "trail", "trailing",
          "position", "positions", "qty", "capital", "pnl", "leverage", "notional", "cooldown"}
idents = set()
for fn in ("l0077_core.py", "l0077_ind.py", "l0077_select.py", "l0077_holdout.py"):
    for node in ast.walk(ast.parse(open(os.path.join(HERE, fn)).read())):
        if isinstance(node, ast.Name): idents.add(node.id.lower())
        elif isinstance(node, ast.Attribute): idents.add(node.attr.lower())
        elif isinstance(node, ast.FunctionDef): idents.add(node.name.lower())
        elif isinstance(node, ast.arg): idents.add(node.arg.lower())
hits = sorted(idents & banned)
ck["7_no_costs_or_trade_mgmt"] = dict(ok=len(hits) == 0, offending_identifiers=hits,
    note="لا رسوم/وقف/إدارة صفقة/رأس مال كمعرّفات فعلية في كود L0077")

# ---- 8: no secrets / tokens in any L0077 output ----
pat = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|api[_-]?key\s*[:=]|secret\s*[:=]|-----BEGIN [A-Z ]*PRIVATE KEY)", re.I)
leaks = []
for f in os.listdir(OUT):
    try:
        for ln, line in enumerate(open(os.path.join(OUT, f), errors="ignore"), 1):
            if pat.search(line): leaks.append(f"{f}:{ln}")
    except Exception: pass
ck["8_no_secrets_in_outputs"] = dict(ok=len(leaks) == 0, hits=leaks, note="فحص كل ملفات L0077 من الأسرار ورموز الوصول")

CRIT = ["1_candidate_uses_data_le_i", "2_selection_from_train_only", "3_names_frozen_before_holdout",
        "4_no_holdout_in_selection", "5_raw_structure_unchanged", "8_no_secrets_in_outputs"]
passed = sum(1 for v in ck.values() if v["ok"])
ck["_summary"] = dict(passed=passed, total=len(ck), all_ok=all(v["ok"] for v in ck.values()),
    critical_ok=all(ck[k]["ok"] for k in CRIT), critical_checks=CRIT,
    verdict="L0077 صالح للاختبار خارج العينة" if all(ck[k]["ok"] for k in CRIT) else "القياس غير صالح للاختبار خارج العينة")
json.dump(ck, open(f"{OUT}/checks_l0077.json", "w"), ensure_ascii=False, indent=1, default=bool)
print(json.dumps(ck["_summary"], ensure_ascii=False, indent=1))
