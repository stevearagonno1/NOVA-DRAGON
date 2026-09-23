# -*- coding: utf-8 -*-
"""L0032 — التشخيص الشامل: خمس سنوات، وتفصيل الأداء لكل حالة سوق.

سؤال القائد (2026-09-23): كنّا نختبر على خمس سنوات ونتعلّم؛ والأفضل أن
نجرّب على جميع أحوال السوق.

**اعتراف الوكيل (§4):** كل جولات اليوم حكمت على 19 شهرًا فقط
(2025-01 → 2026-08)، وهي فترة **هابطة على العملات الخمس عشرة كلها**
(الاحتفاظ خسر −196.14$، صفر رابح من 15). فأرقامنا كلها مقيسة في
**حالة سوق واحدة**، ولا نعرف سلوك الفائزة في صاعد قوي أو عرضي ميت.

هذه الجولة تسدّ الثغرة:
  ① تمديد النافذة إلى **خمس سنوات** (2021-09 → 2026-08) بدل 19 شهرًا.
  ② **تفصيل** الأداء لكل حالة سوق (صاعد · هابط · عرضي · متفجّر)
     بدل رقم مجمّع يخفي الحقيقة.
  ③ تفصيل سنوي: أين ربحنا فعلًا وأين كنا عاجزين.

التصنيف يستعمل **مصنّف المحرك الحي نفسه** (nova_v8/regime.py) لا تصنيفًا
مخترعًا — نفس التعريفات التي يعمل بها البوت.

🔒 **سقف المحاولات المعلَن قبل البدء = 1 قياس.**
   إعدادات مثبَّتة (الفائزة)، لا اختيار ولا بحث ولا مسح ⇒ لا خطر انتقاء.
   هذه جولة **تشخيص** لا تحسين؛ لا يجوز أن تخرج منها بإعداد جديد.

⚠️ المسطرة 20$ · 0.13%/طرف · شراء فقط · 4h · خروج الفائزة الموحّد.

    python3 history/hyp_lab/run_l0032_fiveyear.py
"""
from __future__ import annotations
import json, os, pathlib, platform, subprocess, sys, time
import numpy as np, pandas as pd

_S = pathlib.Path(os.environ.get("NOVA_SCRATCH", "~/.nova_scratch")).expanduser()
os.environ.setdefault("NOVA_HOME", str(_S / "home"))
HIST = pathlib.Path(__file__).resolve().parents[1]; ROOT = HIST.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import common as C
from common import atr, simulate, trade_rows, load, to_bars
from measure_l0010_gate import drawdown_stats
import run_l0019_unified as R19
import run_l0017 as R17
import F_197_dual_trail as M197, F_213_breakers as M213
from nova_v8 import regime as RG
from nova_v8 import config as NC

OUT = HIST / "research" / "hyp_lab_out" / "L0032"
FULL_START, FULL_END = "2021-09-01", "2026-08-31"
WARM = "2021-06-01"
BAR = 4*3600
WIN = {"stop": 2.5, "trig": 0.0015, "lock": 0.0060}
MAX_MEASUREMENTS = 1          # السقف المعلن

AR = {"F_213_breakers": "كاسرة النطاق", "F_192_ext_entry": "انحراف الدخول",
      "F_165_score_entry": "التنقيط التعويضي"}


def pf(p):
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    return float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)


def frame_full(sym):
    p = ROOT / "crypto_archive" / f"{sym}_1m.parquet"
    d1 = load(str(p), start=WARM, end=FULL_END)
    return d1, to_bars(d1, 240)


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1
    print(f"الكاناري: PASS (net={cj['got']['net']})")
    print(f"سقف المحاولات المعلن: {MAX_MEASUREMENTS} · إعدادات مثبَّتة، لا اختيار\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    cells = R19.breaker_cells() + R19.new_cells()
    syms = sorted({c["symbol"] for c in cells})

    old = C.STOP_ATR; C.STOP_ATR = WIN["stop"]
    rows, cover = [], []
    try:
        for s in syms:
            try:
                d1, df = frame_full(s)
            except Exception as e:
                print(f"  {s}: تعذّر ({e})"); continue
            win = df[(df.index >= FULL_START) & (df.index <= FULL_END)]
            if len(win) < 300:
                print(f"  {s}: بيانات غير كافية"); continue
            # حالة السوق بمصنّف المحرك الحي نفسه، ثم إسقاطها على شموع 4h
            # (أ) مصنّف المحرك الحي — سريع (15 دقيقة): يصف تقلّب اللحظة
            reg1m = RG.map_regime_to_1m(d1)
            reg = reg1m.reindex(win.index, method="ffill").fillna(NC.REGIME_CHOP)
            # (ب) مصنّف السوق البطيء — يومي: يصف *مناخ السوق* الذي يقصده القائد
            dly = to_bars(d1, 1440)
            cc = dly["close"]
            e50 = cc.ewm(span=50, adjust=False).mean()
            e200 = cc.ewm(span=200, adjust=False).mean()
            slope = e50.diff(10)
            lab = pd.Series("عرضي", index=dly.index)
            lab[(e50 > e200) & (slope > 0)] = "صاعد"
            lab[(e50 < e200) & (slope < 0)] = "هابط"
            lab = lab.shift(1)          # لا استشراف: تُعرف بعد إغلاق اليوم
            mkt = lab.reindex(win.index, method="ffill").fillna("عرضي")
            a_s = atr(win)
            cover.append({"العملة": s.replace("USDT", ""),
                          "أول شمعة": str(win.index[0].date()),
                          "شموع": len(win)})
            for c in [x for x in cells if x["symbol"] == s]:
                if c["driver"] == "F_213_breakers":
                    sig = M213.make_signals(df, trigger=c["combo"]["trigger"]).loc[win.index]
                    if c["combo"]["exit"] == "dual":
                        kw = {"exit_mode": "dual", "dual": {**M213.make_dual_spec(),
                              "trig": WIN["trig"], "lock": WIN["lock"]}}
                    else:
                        kw = {"exit_mode": "std"}
                else:
                    sig = R17.EXPS[c["driver"]].make_signals(df, **c["combo"]).loc[win.index]
                    kw = {"exit_mode": "dual", "dual": {**M197.make_dual_spec(),
                          "trig": WIN["trig"], "lock": WIN["lock"]}}
                _, tr = simulate(win, sig, a_s, notional=C.TRADE_USD, bar_secs=BAR, **kw)
                rr = trade_rows(c["symbol"], c["driver"], tr)
                for r, p_ in zip(rr, tr):
                    r["regime"] = str(reg.iloc[p_["entry_j"]])
                    r["market"] = str(mkt.iloc[p_["entry_j"]])
                rows.extend(rr)
            print(f"  {s}: {len(win)} شمعة من {win.index[0].date()}", flush=True)
            del d1, df
    finally:
        C.STOP_ATR = old

    d = pd.DataFrame(rows)
    d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
    d["entry_time"] = pd.to_datetime(d["entry_time"], utc=True)
    d.to_csv(OUT/"trades_5y.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(cover).to_csv(OUT/"coverage.csv", index=False, encoding="utf-8-sig")

    p = d["pnl"].to_numpy(float)
    dd, _, _ = drawdown_stats(d["exit_time"], p)
    print("\n" + "="*120)
    print(f"الإجمالي على خمس سنوات ({FULL_START} → {FULL_END}) · {len(cover)} عملة")
    print("="*120)
    print(f"  صافي: {p.sum():.2f}$ · صفقات: {len(d)} · عامل الربح: {pf(p):.4f} "
          f"· فوز: {100*(p>0).mean():.2f}% · أقصى هبوط: {dd:.2f}$")

    # ① التفصيل حسب حالة السوق
    reg_rows = []
    for rg, g in d.groupby("regime"):
        q = g["pnl"].to_numpy(float)
        reg_rows.append({"حالة السوق": rg, "صفقات": len(g),
                         "حصة الصفقات%": round(100*len(g)/len(d), 1),
                         "صافي$": round(float(q.sum()), 2),
                         "حصة الدخل%": round(100*float(q.sum())/float(p.sum()), 1),
                         "عامل الربح": round(pf(q), 4),
                         "فوز%": round(100*float((q > 0).mean()), 2),
                         "ربح الصفقة$": round(float(q.mean()), 4)})
    rdf = pd.DataFrame(reg_rows).sort_values("صافي$", ascending=False)
    rdf.to_csv(OUT/"by_regime.csv", index=False, encoding="utf-8-sig")
    print("\n=== ① الأداء مفصّلًا لكل حالة سوق ===")
    print(rdf.to_string(index=False), flush=True)

    # ①-ب مناخ السوق البطيء (اليومي) — هذا ما يقصده القائد بـ"أحوال السوق"
    mk = []
    for mg, g in d.groupby("market"):
        q = g["pnl"].to_numpy(float)
        mk.append({"مناخ السوق": mg, "صفقات": len(g),
                   "حصة الصفقات%": round(100*len(g)/len(d), 1),
                   "صافي$": round(float(q.sum()), 2),
                   "حصة الدخل%": round(100*float(q.sum())/float(p.sum()), 1),
                   "عامل الربح": round(pf(q), 4),
                   "فوز%": round(100*float((q > 0).mean()), 2),
                   "ربح الصفقة$": round(float(q.mean()), 4)})
    mdf = pd.DataFrame(mk).sort_values("صافي$", ascending=False)
    mdf.to_csv(OUT/"by_market.csv", index=False, encoding="utf-8-sig")
    print("\n=== ①-ب مناخ السوق (تصنيف يومي بطيء) — أحوال السوق الحقيقية ===")
    print(mdf.to_string(index=False), flush=True)

    # ② التفصيل السنوي
    d["سنة"] = d["exit_time"].dt.year
    yr = []
    for y, g in d.groupby("سنة"):
        q = g["pnl"].to_numpy(float)
        dom = g.groupby("market").size().idxmax()
        yr.append({"السنة": int(y), "صفقات": len(g), "صافي$": round(float(q.sum()), 2),
                   "عامل الربح": round(pf(q), 4), "فوز%": round(100*float((q > 0).mean()), 2),
                   "الحالة الغالبة": dom})
    ydf = pd.DataFrame(yr)
    ydf.to_csv(OUT/"by_year.csv", index=False, encoding="utf-8-sig")
    print("\n=== ② الأداء سنة بسنة ===")
    print(ydf.to_string(index=False), flush=True)

    # ③ كل عمود × كل حالة
    cr = []
    for drv, g in d.groupby("exp"):
        row = {"العمود": AR.get(drv, drv)}
        for rg in rdf["حالة السوق"]:
            sub = g[g["regime"] == rg]["pnl"]
            row[rg] = round(float(sub.sum()), 2) if len(sub) else 0.0
        row["الكل$"] = round(float(g["pnl"].sum()), 2)
        cr.append(row)
    cdf = pd.DataFrame(cr).sort_values("الكل$", ascending=False)
    cdf.to_csv(OUT/"column_by_regime.csv", index=False, encoding="utf-8-sig")
    print("\n=== ③ كل عمود في كل حالة سوق ($) ===")
    print(cdf.to_string(index=False), flush=True)

    # ④ توزيع الزمن على الحالات (فرصة مهدرة؟)
    print("\n=== ④ مقارنة: حصة الصفقات مقابل حصة الدخل ===")
    for _, r in rdf.iterrows():
        gap = r["حصة الدخل%"] - r["حصة الصفقات%"]
        flag = "✅ مربح فوق حجمه" if gap > 3 else ("⚠️ يستهلك أكثر مما يعطي" if gap < -3 else "متوازن")
        print(f"  {r['حالة السوق']:8s}: صفقات {r['حصة الصفقات%']:5.1f}% · "
              f"دخل {r['حصة الدخل%']:5.1f}% ⇒ {flag}")

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nnotional={C.TRADE_USD}$\nwindow={FULL_START}→{FULL_END}\n"
        f"warm={WARM}\nexit={WIN}\nregime_classifier=nova_v8/regime.py (live engine)\n"
        f"regime_tf={NC.REGIME_TF}\nmeasurements=1 (declared cap)\nsymbols={len(cover)}\n"
        f"trades={len(d)}\nnet={p.sum():.6f}\n", encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
