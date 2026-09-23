# -*- coding: utf-8 -*-
"""L0033 — ملاحقة انحدار الحافة: هل تتآكل الاستراتيجية أم تغيّر السوق؟

L0032 كشف انحدارًا مطّردًا في عامل الربح: 7.87 → 4.29 → 4.08 → 4.56 → 3.78 → 3.23.
هذا أخطر إشارة ظهرت. لكن الانحدار وحده **لا يثبت تآكلًا** — له ثلاثة تفسيرات
بريئة يجب استبعادها قبل إعلان الخطر:

  ① **تغيّر تركيبة العملات:** 2021 كان بـ12 عملة، و2026 بـ15.
     عملات جديدة أضعف تجرّ المتوسط لأسفل بلا أي تآكل.
  ② **تغيّر السوق نفسه:** إن كان السوق كله صار أصعب، فالانحدار خارجي لا داخلي.
     المقياس: أداء الاحتفاظ البسيط في كل سنة.
  ③ **عامل الربح مقياس نسبي مضلّل:** قد ينخفض بينما الدخل بالدولار يرتفع.
     الحكم بالدولار (§23 مبدأ 8) لا بالنسب.

الاختبار الحاسم: **سلة ثابتة** من العملات الحاضرة في السنوات الست كلها،
تُقاس سنة بسنة. إن انحدرت الحافة على سلة ثابتة وسوق ثابت ⇒ تآكل حقيقي.

🔒 **سقف المحاولات المعلَن = 1 قياس** (إعدادات الفائزة مجمَّدة، تشخيص لا تحسين).

    python3 history/hyp_lab/run_l0033_decay.py
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
from common import load, to_bars
from measure_l0010_gate import drawdown_stats

OUT = HIST / "research" / "hyp_lab_out" / "L0033"
SRC = HIST / "research" / "hyp_lab_out" / "L0032" / "trades_5y.csv"
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]


def pf(p):
    g, l = p[p > 0].sum(), -p[p < 0].sum()
    return float(g/l) if l > 0 else (np.inf if g > 0 else 0.0)


def main():
    t0 = time.time()
    can = subprocess.run([sys.executable, str(ROOT/"tools"/"canary.py"), "--json"],
                         capture_output=True, text=True)
    cj = json.loads(can.stdout[can.stdout.index("{"):]) if can.stdout else {}
    if cj.get("canary") != "ok":
        print("الكاناري فشل — إيقاف.", file=sys.stderr); return 1
    print(f"الكاناري: PASS · سقف المحاولات المعلن: 1\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True); pd.set_option("display.width", 250)

    if not SRC.exists():
        print(f"مصدر L0032 مفقود: {SRC}", file=sys.stderr); return 1
    d = pd.read_csv(SRC, encoding="utf-8-sig")
    d["exit_time"] = pd.to_datetime(d["exit_time"], utc=True)
    d["entry_time"] = pd.to_datetime(d["entry_time"], utc=True)
    d["سنة"] = d["exit_time"].dt.year

    # ① أي عملات حاضرة في كل السنوات؟ (سلة ثابتة)
    per = d.groupby(["symbol", "سنة"]).size().unstack(fill_value=0)
    stable = sorted(per.index[(per[YEARS] > 0).all(axis=1)])
    print(f"السلة الثابتة (حاضرة في السنوات الست): {len(stable)} عملة")
    print("  " + ", ".join(s.replace("USDT", "") for s in stable), flush=True)
    newer = sorted(set(d["symbol"]) - set(stable))
    print(f"الوافدة لاحقًا: {', '.join(s.replace('USDT','') for s in newer)}\n")

    # ② الانحدار: كل العملات مقابل السلة الثابتة
    rows = []
    ds = d[d["symbol"].isin(stable)]
    for y in YEARS:
        a = d[d["سنة"] == y]["pnl"].to_numpy(float)
        b = ds[ds["سنة"] == y]["pnl"].to_numpy(float)
        rows.append({"السنة": y,
                     "كل العملات — عامل": round(pf(a), 4),
                     "كل العملات — صافي$": round(float(a.sum()), 2),
                     "السلة الثابتة — عامل": round(pf(b), 4),
                     "السلة الثابتة — صافي$": round(float(b.sum()), 2),
                     "السلة — صفقات": len(b),
                     "السلة — ربح الصفقة$": round(float(b.mean()), 4) if len(b) else 0.0})
    cmp = pd.DataFrame(rows)
    cmp.to_csv(OUT/"decay_stable_basket.csv", index=False, encoding="utf-8-sig")
    print("=== ① الانحدار: كل العملات مقابل سلة ثابتة ===")
    print(cmp.to_string(index=False), flush=True)

    # ③ هل السوق نفسه صار أصعب؟ الاحتفاظ البسيط سنة بسنة
    print("\n=== ② هل تغيّر السوق؟ أداء الاحتفاظ البسيط (20$/عملة) ===")
    bh = []
    for y in YEARS:
        s0, s1 = f"{y}-01-01", f"{y}-12-31"
        tot, n = 0.0, 0
        for sym in stable:
            try:
                df = to_bars(load(str(ROOT/"crypto_archive"/f"{sym}_1m.parquet"),
                                  start=s0, end=s1), 240)
            except Exception:
                continue
            if len(df) < 50:
                continue
            r = df["close"].iloc[-1] / df["close"].iloc[0] - 1.0
            tot += 20.0 * r; n += 1
        bh.append({"السنة": y, "احتفاظ$": round(tot, 2), "عملات": n})
        print(f"  {y}: احتفاظ {tot:>8.2f}$ ({n} عملة)", flush=True)
    bdf = pd.DataFrame(bh)
    bdf.to_csv(OUT/"buyhold_by_year.csv", index=False, encoding="utf-8-sig")

    # ④ الحكم بالدولار لا بالنسبة + تطبيع على الفرص
    m = cmp.merge(bdf, on="السنة")
    m["تفوّق على الاحتفاظ$"] = (m["السلة الثابتة — صافي$"] - m["احتفاظ$"]).round(2)
    m.to_csv(OUT/"verdict_table.csv", index=False, encoding="utf-8-sig")
    print("\n=== ③ الحكم بالدولار: الاستراتيجية مقابل الاحتفاظ (سلة ثابتة) ===")
    print(m[["السنة", "السلة الثابتة — صافي$", "احتفاظ$", "تفوّق على الاحتفاظ$",
             "السلة الثابتة — عامل", "السلة — ربح الصفقة$"]].to_string(index=False), flush=True)

    # ⑤ الاستنتاج الآلي
    st_pf = m["السلة الثابتة — عامل"].to_numpy(float)
    st_tr = m["السلة — ربح الصفقة$"].to_numpy(float)
    x = np.arange(len(st_pf))
    sl_pf = float(np.polyfit(x, st_pf, 1)[0])
    sl_tr = float(np.polyfit(x, st_tr, 1)[0])
    print("\n=== ④ الاستنتاج ===")
    print(f"  ميل عامل الربح (سلة ثابتة): {sl_pf:+.4f}/سنة")
    print(f"  ميل ربح الصفقة بالدولار   : {sl_tr:+.5f}$/سنة")
    if sl_pf < -0.15 and sl_tr < -0.002:
        v = "⚠️ تآكل حقيقي — النسبة والدولار ينحدران معًا على سلة ثابتة"
    elif sl_pf < -0.15:
        v = "🟡 انحدار في النسبة فقط · ربح الصفقة بالدولار صامد ⇒ ليس تآكلًا مؤكدًا"
    else:
        v = "✅ لا انحدار مؤكد على السلة الثابتة — الانحدار كان أثر تركيبة العملات"
    print(f"  الحكم: {v}")

    (OUT/"env_dump.txt").write_text(
        f"python={platform.python_version()}\npandas={pd.__version__}\nnumpy={np.__version__}\n"
        f"canary={cj['got']['net']}\nsource=L0032/trades_5y.csv\nstable_basket={stable}\n"
        f"newer={newer}\nslope_pf={sl_pf:.6f}\nslope_trade={sl_tr:.6f}\nverdict={v}\n"
        f"measurements=1 (declared cap)\n", encoding="utf-8")
    print(f"\n→ {OUT}\n{time.time()-t0:.1f} ث", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
