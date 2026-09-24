# -*- coding: utf-8 -*-
"""L0045 — دفعة فرضيات دخول ثانية (عمود ثامن مستقل).

🔒 القرار: 2021-09-01 → 2023-12-31 · الحكم: 2024-01-01 → 2026-08-31 · تسخين 2021-06-01
🔒 المسطرة: 20$/صفقة · 0.13%/طرف · شراء فقط · 4h
🔒 قانون الخروج الموحّد (المعلَن في ورقة المهمة): وقف 2.5×ATR · تسليح 0.0015 · قفل 0.0060
🔒 سقف المحاولات المعلَن = 45 (تأسيس/تحقق ≤10 + مرحلة 2 = 30 + مرحلة 3 = 15)

ملاحظة المادة 1 (مقيسة لا مفترضة): أعمدة L0044 الأربعة المضافة (F-042/F-055/F-063/F-001)
قِيست فعلاً بوقف 2.0×ATR بينما الأعمدة الثلاثة القديمة بوقف 2.5×ATR (الدليل: F-042 بوقف 2.0
= 729.01$/2929 صفقة مطابقة للمودع). هذه الجولة توحّد القانون على 2.5×ATR المعلَن، وتُعيد
قياس الأعمدة الأربعة به لتأسيس أساس موحّد مقاس.
"""
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

ROOT = pathlib.Path("/home/user/work")
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
HIST = ROOT / "history"
sys.path.insert(0, str(HIST / "hyp_lab"))
sys.path.insert(0, str(ROOT))

import common as C
from common import atr, simulate, trade_rows
import run_l0019_unified as R19
import run_l0036_more as L36
import F_213_breakers as M213
import F_197_dual_trail as M197
import L0017_F_001_rsi2_snap as E001
import nova_v8.indicators as ind
import nova_v8.config as NC
import L0045_signals as S

OUT = HIST / "research" / "hyp_lab_out" / "L0045"
CACHE = ROOT / ".cache" / "l0045_frames"
DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
BAR = 4 * 3600
WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060}     # قانون الخروج الموحّد المعلَن
DECLARED_TOTAL, CAP_P2, CAP_P3 = 45, 30, 15

_FR, _USED = {}, {"prep": 0, "p2": 0, "p3": 0}


def frames(sym):
    if sym not in _FR:
        _FR[sym] = pd.read_parquet(CACHE / f"{sym}_4h.parquet")
    return _FR[sym]


def summarize(rows):
    if not rows:
        return {"net": 0.0, "trades": 0, "pf": 0.0, "per": 0.0, "mdd": 0.0}
    t = pd.DataFrame(rows)
    p = t["pnl"].to_numpy(float)
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    pf = float(g / l) if l > 0 else (np.inf if g > 0 else 0.0)
    ts = t.sort_values("exit_time")
    eq = np.cumsum(ts["pnl"].to_numpy(float))
    peak = np.maximum.accumulate(eq)
    mdd = float(np.max(peak - eq)) if len(eq) else 0.0
    net = round(float(p.sum()), 2)
    return {"net": net, "trades": len(t), "pf": round(pf, 4),
            "per": round(net / len(t), 5), "mdd": round(mdd, 2)}


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if "{" in can.stdout else {}
    if cj.get("canary") != "ok":
        print(f"الكاناري فشل ({cj.get('canary')}) — إيقاف.", file=sys.stderr); return 1
    print(f"الكاناري: ok · net={cj['got']['net']}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 250)

    # ═══ الإعدادات السارية في الذاكرة (لا تعديل على nova_v8) ═══
    L36.set_core()                     # نواة كسر البنية: جسم 0.40 · مدى 0.60 · نظر 10
    NC.EMA_FAST = 8                    # المتوسط السريع (L0041) — الافتراضي في الكود 50
    M213._cache.clear()
    C.STOP_ATR = WIN["stop"]           # قانون الخروج الموحّد المعلَن 2.5×ATR

    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})
    print(f"خلايا الأساس: {len(cells)} · عملات: {len(syms)}", flush=True)

    kw_col = {"exit_mode": "dual",
              "dual": {**M197.make_dual_spec(), "trig": WIN["trig"], "lock": WIN["lock"]}}

    def sim_rows(sig_fn, s0, s1, name):
        rows = []
        for sym in syms:
            df = frames(sym)
            win = df[(df.index >= s0) & (df.index <= s1)]
            if len(win) >= 100:
                _, tr = simulate(win, sig_fn(df).loc[win.index], atr(win),
                                 notional=C.TRADE_USD, bar_secs=BAR, **kw_col)
                rows.extend(trade_rows(sym, name, tr))
        return rows

    # ═══ المرحلة 0 — تأسيس الأساس الموحّد (تحقق المادة 1) ═══
    print("\n" + "=" * 78)
    print("المرحلة 0 — تأسيس الأساس (الأعمدة السبعة) بالقانون الموحّد 2.5×ATR")
    print("=" * 78)
    rows_base3 = {"JUD": None, "DEC": None}
    for tag, (s0, s1) in (("DEC", (DEC_S, DEC_E)), ("JUD", (JUD_S, JUD_E))):
        _, df = L36.run(cells, s0, s1)
        rows_base3[tag] = df.to_dict("records")
        _USED["prep"] += 1
        s = summarize(rows_base3[tag])
        print(f"  الأساس (3 أعمدة قديمة) {tag}: {s}")

    EXISTING = [
        ("F-042: Donchian_High_20", lambda df: (df["close"] > df["high"].shift(1).rolling(20).max()).fillna(False)),
        ("F-055: MACD_Cross_Zero", lambda df: ((ind.compute_matrix(df)["macd"] > 0) & (ind.compute_matrix(df)["macd"].shift(1) <= 0)).fillna(False)),
        ("F-063: BB_Lower_Bounce", lambda df: ((df["low"] <= ind.compute_matrix(df)["bb_low"]) & (df["close"] > df["open"])).fillna(False)),
        ("F-001: RSI2_Snap (os=15)", lambda df: E001.make_signals(df, rsi2_os=15, sma_trend=200, sma_pull=5)),
    ]
    rows_ex = {"JUD": [], "DEC": []}
    ex_tbl = []
    for name, fn in EXISTING:
        for tag, (s0, s1) in (("DEC", (DEC_S, DEC_E)), ("JUD", (JUD_S, JUD_E))):
            r = sim_rows(fn, s0, s1, name)
            rows_ex[tag] += r
            _USED["prep"] += 1
            s = summarize(r)
            ex_tbl.append({"العمود": name, "الفترة": tag, **s})
            print(f"  {name} {tag}: {s}")
    pd.DataFrame(ex_tbl).to_csv(OUT / "phase0_existing_columns.csv", index=False, encoding="utf-8-sig")

    rows7 = {"JUD": rows_base3["JUD"] + rows_ex["JUD"], "DEC": rows_base3["DEC"] + rows_ex["DEC"]}
    basis = {t: summarize(rows7[t]) for t in ("DEC", "JUD")}
    print(f"\n  ★ الأساس الموحّد (7 أعمدة، وقف 2.5): قرار={basis['DEC']} | حكم={basis['JUD']}")
    print(f"  (المودع من L0044 بوقف مختلط: 5749.34$ / 30641 صفقة)")

    # ═══ المرحلة 1 — الفرضيات العشر (مكتوبة قبل القياس) ═══
    print("\n" + "=" * 78)
    print("المرحلة 2 — قياس عشر فرضيات دخول على فترة الاختيار (2021-09→2023-12)")
    print("=" * 78)

    p2 = []
    for hid, name, fn in S.HYPOTHESES:
        r = sim_rows(fn, DEC_S, DEC_E, f"{hid} {name}")
        _USED["p2"] += 1
        s = summarize(r)
        gate = bool(s["net"] > 0 and s["pf"] >= 1.3 and s["trades"] >= 30)
        p2.append({"hid": hid, "name": name, "fn": fn, "rows_dec": r, "dec": s, "gate": gate})
        print(f"  {hid} {name[:38]:38s} | قرار: {s['net']:>8.2f}$ ({s['trades']:5d} ص, PF={s['pf']:.3f}, "
              f"ربح/صفقة={s['per']:.5f}) | البوابة: {'✓' if gate else '✗'}", flush=True)

    p2.sort(key=lambda x: x["dec"]["net"], reverse=True)
    for i, it in enumerate(p2, 1):
        it["rank"] = i

    # الحكم على العابرين فقط (بالترتيب) — بلا اجتهاد
    passers = [x for x in p2 if x["gate"]]
    for it in passers:
        if _USED["p2"] >= CAP_P2:
            print(f"  ⚠ سقف المرحلة 2 استُنفد — {it['hid']} لم يُقَس على فترة الحكم (يُكتب: لم يُقَس)")
            it["jud"] = None
            continue
        r = sim_rows(it["fn"], JUD_S, JUD_E, f"{it['hid']} {it['name']}")
        _USED["p2"] += 1
        it["rows_jud"] = r
        it["jud"] = summarize(r)
        print(f"  ↳ {it['hid']} حكم: {it['jud']}", flush=True)
    for it in p2:
        if not it["gate"]:
            it["jud"] = None

    rows_p2 = []
    for it in p2:
        j = it.get("jud") or {"net": None, "trades": None, "pf": None, "per": None}
        rows_p2.append({
            "الترتيب_بالقرار": it["rank"], "الرمز": it["hid"], "الاسم": it["name"],
            "صافي_القرار$": it["dec"]["net"], "صفقات_القرار": it["dec"]["trades"],
            "PF_القرار": it["dec"]["pf"], "ربح_صفقة_القرار$": it["dec"]["per"],
            "أقصى_هبوط_القرار$": it["dec"]["mdd"],
            "بوابة_القبول": "✓" if it["gate"] else "✗",
            "صافي_الحكم$": j["net"], "صفقات_الحكم": j["trades"], "PF_الحكم": j["pf"],
            "ربح_صفقة_الحكم$": j["per"], "أقصى_هبوط_الحكم$": j.get("mdd"),
        })
    pd.DataFrame(rows_p2).to_csv(OUT / "phase2_hypotheses_ranked.csv", index=False, encoding="utf-8-sig")

    # ═══ المرحلة 3 — التراكم وأقصى الهبوط ═══
    print("\n" + "=" * 78)
    print("المرحلة 3 — التراكم فوق الأساس الموحّد، بترتيب فترة الاختيار")
    print("=" * 78)

    survivors = [x for x in passers if x.get("jud") and x["jud"]["net"] > 0]
    print(f"  العابرون: {len(passers)} · صمدوا في فترة الحكم: {len(survivors)}")

    acc_rows, prev_net, prev_mdd = [], basis["JUD"]["net"], basis["JUD"]["mdd"]
    acc_rows.append({"التركيب": "الأساس (7 أعمدة)", "العمود_المضاف": "—",
                     **{k: basis["JUD"][k] for k in ("net", "trades", "per", "pf", "mdd")},
                     "صافي_القرار$": basis["DEC"]["net"], "صفقات_القرار": basis["DEC"]["trades"],
                     "الزيادة_عن_الأساس$": 0.0, "الزيادة_عن_السابق$": 0.0,
                     "فرق_الهبوط_عن_السابق$": 0.0})
    print(f"  الأساس: {basis['JUD']}")
    cur = list(rows7["JUD"])
    for i, it in enumerate(passers[:5], 1):          # العابرون بالترتيب الحرفي لفترة الاختيار
        cur = cur + it["rows_jud"]
        _USED["p3"] += 1
        s = summarize(cur)
        acc_rows.append({"التركيب": f"+{i} عمود", "العمود_المضاف": f"{it['hid']} {it['name']}",
                         **{k: s[k] for k in ("net", "trades", "per", "pf", "mdd")},
                         "صافي_القرار$": None, "صفقات_القرار": None,
                         "الزيادة_عن_الأساس$": round(s["net"] - basis["JUD"]["net"], 2),
                         "الزيادة_عن_السابق$": round(s["net"] - prev_net, 2),
                         "فرق_الهبوط_عن_السابق$": round(s["mdd"] - prev_mdd, 2)})
        print(f"  +{i} {it['hid']:6s}: صافي={s['net']:>8.2f}$ | صفقات={s['trades']:6d} | ربح/صفقة={s['per']:.5f} "
              f"| PF={s['pf']:.4f} | هبوط={s['mdd']:>6.2f}$ | مضاف={s['net']-prev_net:>+8.2f}$ | Δهبوط={s['mdd']-prev_mdd:>+6.2f}$")
        prev_net, prev_mdd = s["net"], s["mdd"]
    pd.DataFrame(acc_rows).to_csv(OUT / "phase3_accumulation.csv", index=False, encoding="utf-8-sig")

    # ═══ الفحوص الأربعة للفائز الأول الصامد ═══
    if not survivors:
        print("\nلا فائز صمد — لا فحوص.")
        winner = None
    else:
        winner = survivors[0]
        print("\n" + "=" * 78)
        print(f"الفحوص الأربعة للفائز: {winner['hid']} {winner['name']}")
        print("=" * 78)

        AX = {
            "F-046": ("adx_min", [20, 22, 25, 28, 30]),
            "F-007": ("kc_mult", [1.2, 1.5, 1.8, 2.0]),
            "F-054": ("look", [16, 18, 20, 22, 24]),
            "F-032": ("adx_min", [16, 18, 20, 22, 24]),
            "F-009": ("adx_min", [20, 22, 25, 28, 30]),
            "F-074": ("tol", [0.003, 0.004, 0.005, 0.006, 0.008]),
            "F-069": ("vol_mult", [0.96, 1.08, 1.2, 1.32, 1.44]),
            "F-013": ("adx_min", [16, 18, 20, 22, 24]),
            "F-067": ("sma_lvl", [50, 100, 200]),
            "F-130": ("min_atr", [0.00, 0.05, 0.10]),
        }
        axis, vals = AX[winner["hid"]]
        nb = []
        for v in vals:
            r = sim_rows(lambda df, _v=v: winner["fn"](df, **{axis: _v}), JUD_S, JUD_E, f"{winner['hid']}_{axis}{v}")
            _USED["p3"] += 1
            s = summarize(r)
            nb.append({"الإعداد": f"{axis}={v}", **s, "رابح": s["net"] > 0})
            print(f"  الجوار {axis}={v}: {s}")
        pd.DataFrame(nb).to_csv(OUT / "winner_neighborhood.csv", index=False, encoding="utf-8-sig")

        costs = [(0.0020, 0.0015, 0.0005, "0.20%"), (0.0030, 0.0023, 0.0007, "0.30%"),
                 (0.0040, 0.0030, 0.0010, "0.40%")]
        st = []
        for tot, f_s, s_s, lbl in costs:
            of, osl, oc = C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE
            C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE = f_s, s_s, f_s + s_s
            try:
                r = sim_rows(winner["fn"], JUD_S, JUD_E, f"{winner['hid']}_stress")
                _USED["p3"] += 1
                s = summarize(r)
            finally:
                C.FEE_PER_SIDE, C.SLIP_PER_SIDE, C.COST_PER_SIDE = of, osl, oc
            st.append({"كلفة_الطرف": lbl, **s, "صامد": s["net"] > 0})
            print(f"  الإجهاد {lbl}: {s}")
        pd.DataFrame(st).to_csv(OUT / "winner_stress.csv", index=False, encoding="utf-8-sig")

    # ═══ مخرجات ═══
    used_total = sum(_USED.values())
    env = (f"python={platform.python_version()}\npandas={pd.__version__}\npyarrow=25.0.1\n"
           f"canary={cj['got']['net']}\ncanary_field={cj.get('canary')}\n"
           f"decision={DEC_S}→{DEC_E}\njudgement={JUD_S}→{JUD_E}\n"
           f"exit_law=stop{WIN['stop']}xATR/trig{WIN['trig']}/lock{WIN['lock']}\n"
           f"ema_fast={NC.EMA_FAST}\ncore=body0.40/range0.60/look10\n"
           f"declared_total_cap={DECLARED_TOTAL}\nused_prep={_USED['prep']}\nused_p2={_USED['p2']}\n"
           f"used_p3={_USED['p3']}\nused_total={used_total}\n"
           f"basket_symbols={len(syms)}\ncells={len(cells)}\n"
           f"winner={winner['hid'] if winner else 'none'} {winner['name'] if winner else ''}\n")
    (OUT / "env_dump.txt").write_text(env, encoding="utf-8")
    print(f"\n→ {OUT}\nالسقف: {used_total}/{DECLARED_TOTAL} "
          f"(تحقق {_USED['prep']} · مرحلة2 {_USED['p2']}/30 · مرحلة3 {_USED['p3']}/15)\n"
          f"الزمن: {time.time()-t0:.1f} ث")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
