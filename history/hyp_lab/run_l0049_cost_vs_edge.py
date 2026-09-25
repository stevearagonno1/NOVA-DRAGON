# -*- coding: utf-8 -*-
"""L0049 — هل الكلفة هي التي تخفي الحافة؟

قياس وحكم فقط. لا تحسين ولا فرضية جديدة ولا لمس لإشارة أو لقانون الخروج.
السقف = 40. الشبكة مكتوبة هنا قبل أي رقم، ولا يُضاف بند بعد رؤية الحكم.

الخروج مثبَّت: وقف قاسٍ 2.5×ATR + تتبّع 4×ATR، بلا تسليح ولا قفل ولا هدف.
مركز واحد لكل عملة (strict_single=True). كلفة الافتراضي في common.py لا تُغيَّر
في الملف؛ تُبدَّل كمعامل ثم تُعاد. الإطار يُمرَّر كمعامل. bar_secs يطابق الإطار.

مرحلة 0 (لا تُحسب): إعادة إنتاج كتاب L0048
  الاختيار +10.76$ / 1,067  ·  الحكم −154.84$ / 1,791  ضمن ±0.5$.
  ثم مطابقة بذور العشوائي المنشورة. أي فشل = إيقاف قبل القياس.

الشبكة المحسوبة (40) — مُعلَنة قبل النتائج:
  0.00% و 0.05%: محفظة + 5 بذور × فترتين = 24
  0.10% و 0.02%: محفظة فقط × فترتين = 4
      (موجب بلا بذور لا يُحتسب فوزًا، ولا تُضاف بذور بعد الرؤية)
  يومي 1440 دقيقة، bar_secs=86400، كلفة 0.13%: محفظة + 5 بذور × فترتين = 12
  المجموع 40.

لم يُقَس، ومكتوب كذلك قبل النتائج: 8 ساعات، 12 ساعة، يومان، 0.075%،
وعشوائي عند 0.10% و 0.02%. سقف المرحلة ج لا يتسع لخمس بذور × فترتين.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/nova")
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
os.environ.setdefault("NOVA_HOME", "/home/user/.nova_scratch/home")
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import run_l0046_basis_repair as R46
import run_l0048_entry_value as R48
import run_l0036_more as L36
import nova_v8.config as NC
import F_213_breakers as M213
import common as C
import position_sequencing_audit as psa

# المستودع هنا، لا في /home/user/work الذي يثبّته مشغّل L0048 عند الاستيراد.
R46.ROOT = ROOT
R48.ROOT = ROOT

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0049"
OUT.mkdir(parents=True, exist_ok=True)
DAILY_CACHE = pathlib.Path.home() / ".cache" / "l0049_frames"
DAILY_CACHE.mkdir(parents=True, exist_ok=True)

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
WARM = "2021-06-01"
SEEDS = (110048, 210048, 310048, 410048, 510048)
CAP = 40
DEFAULT_COST = 0.0013
STOP = 2.5
TRAIL = 4.0

# أرقام L0048 المنشورة في measurements.csv — بوابة المرحلة 0.
P0_BOOK = {
    "SEL": {"net": 10.76, "trades": 1067},
    "JUD": {"net": -154.84, "trades": 1791},
}
P0_SEEDS = {
    "SEL": {
        110048: (-43.04, 1061),
        210048: (-66.26, 1055),
        310048: (-64.38, 1069),
        410048: (-33.44, 1055),
        510048: (-61.72, 1085),
    },
    "JUD": {
        110048: (-208.07, 1785),
        210048: (-161.93, 1786),
        310048: (-160.19, 1792),
        410048: (-228.55, 1785),
        510048: (-204.06, 1786),
    },
}
L0048_COINS = {
    "ATOMUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "FILUSDT", "GRAMUSDT",
    "IMXUSDT", "LINKUSDT", "PEPEUSDT", "RENDERUSDT", "SHIBUSDT", "SOLUSDT",
    "TONUSDT", "VETUSDT", "XLMUSDT",
}

LEDGER: list[dict] = []
MEASURED: list[dict] = []


def log_measurement(name: str, window: str, extra: dict | None = None) -> int:
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف: محاولة تسجيل قياس بعد {CAP}")
    row = {"#": len(LEDGER) + 1, "القياس": name, "الفترة": window}
    if extra:
        row.update(extra)
    LEDGER.append(row)
    return row["#"]


def set_cost(cost: float) -> None:
    """معامل فقط. common.COST_PER_SIDE في الملف يبقى 0.0013."""
    C.COST_PER_SIDE = float(cost)
    R48.COST = float(cost)


def restore_cost() -> None:
    set_cost(DEFAULT_COST)


def summarize(rows: list[dict], cost: float) -> dict:
    if not rows:
        return {"net": 0.0, "trades": 0, "per": 0.0, "gross": 0.0, "costs": 0.0,
                "median_hold": 0.0, "overlap_ratio": 0.0, "max_concurrent": 0,
                "overlapping_trades": 0}
    t = pd.DataFrame(rows)
    p = t["pnl"].to_numpy(float)
    net = round(float(p.sum()), 2)
    qty = t["notional"].to_numpy(float) / t["entry"].to_numpy(float)
    entry = t["entry"].to_numpy(float)
    exit_ = t["exit"].to_numpy(float)
    costs = float((qty * cost * (entry + exit_)).sum())
    gross = round(float((qty * (exit_ - entry)).sum() + costs), 2)
    hold = t["bars_held"].to_numpy(float)
    au = psa.audit_frame(t)
    n = len(t)
    return {
        "net": net,
        "trades": int(n),
        "per": round(net / n, 5) if n else 0.0,
        "gross": gross,
        "costs": round(costs, 2),
        "median_hold": float(np.median(hold)) if n else 0.0,
        "overlap_ratio": au["overlap_ratio"],
        "max_concurrent": au["max_concurrent"],
        "overlapping_trades": au["overlapping_trades"],
    }


def save_trades(name: str, rows: list[dict]) -> pathlib.Path:
    path = OUT / f"trades_{name}.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def targets_of(rows: list[dict], syms: list[str]) -> dict[str, int]:
    t = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol"])
    out = {}
    for sym in syms:
        if t.empty:
            out[sym] = 0
        else:
            out[sym] = int((t["symbol"] == sym).sum())
    return out


def direct_book(s0: str, s1: str) -> list[dict]:
    return R48.run_mask(R48.portfolio_signal, s0, s1, strict=True, atr_trail=TRAIL,
                        dual=None, exp="book")


def build_outcomes(syms: list[str], s0: str, s1: str) -> dict:
    outs = {}
    for sym in syms:
        df = R48.frames(sym)
        win = R48.window(df, s0, s1)
        if len(win) < 100:
            continue
        outs[sym] = R48.outcomes_for(sym, s0, s1)
    return outs


def cache_book(outs: dict, s0: str, s1: str) -> list[dict]:
    rows = []
    for sym, table in outs.items():
        df = R48.frames(sym)
        win = R48.window(df, s0, s1)
        sg = (R48.portfolio_signal(df, sym)
              .reindex(win.index, fill_value=False).fillna(False).astype(bool).to_numpy())
        rows.extend(R48.rows_from_chosen(sym, "cache", R48.greedy(table, sg)))
    return rows


def random_book(outs: dict, seed: int, target: dict[str, int]) -> list[dict]:
    rows = []
    for sym, table in outs.items():
        u = R48.uniforms(seed, sym, len(table))
        p = R48.match_p(table, u, target.get(sym, 0))
        rows.extend(R48.rows_from_chosen(sym, f"rnd{seed}", R48.greedy(table, u < p)))
    return rows


def assert_equiv(name: str, direct: list[dict], cached: list[dict], cost: float) -> None:
    ds, cs = summarize(direct, cost), summarize(cached, cost)
    if abs(ds["net"] - cs["net"]) > 0.01 or ds["trades"] != cs["trades"]:
        raise SystemExit(f"تكافؤ الجدول فشل عند {name}: مباشر {ds} ≠ جدول {cs}")
    print(f"  ✅ تكافؤ {name}: {ds['net']}$ / {ds['trades']}")


def record(name: str, window: str, rows: list[dict], cost: float, frame: str,
           bar_secs: int, seed: int | None, counted: bool) -> dict:
    st = summarize(rows, cost)
    if st["overlapping_trades"] != 0:
        save_trades(name + "_" + window + "_OVERLAP", rows)
        raise SystemExit(f"تداخل ≠ 0 في {name} {window}: {st}")
    rec = {
        "القياس": name, "الفترة": window, "counted": counted,
        "cost": cost, "frame": frame, "bar_secs": bar_secs, "seed": seed,
        **st,
    }
    if counted:
        log_measurement(name, window, {"cost": cost, "frame": frame, "seed": seed})
        MEASURED.append(rec)
    tag = f"{len(LEDGER)}/{CAP}" if counted else "مرحلة0"
    print(f"  [{tag}] {name} {window}: net={st['net']} صفقات={st['trades']} "
          f"للصفقة={st['per']} إجمالي={st['gross']} كلفة={st['costs']} "
          f"وسيط_الاحتفاظ={st['median_hold']}", flush=True)
    return rec


def prove_bar_secs() -> None:
    """على شريحة واحدة: هل يغيّر bar_secs ناتج strict_single؟ ليس قياسًا."""
    sym = "BTCUSDT"
    df = R48.frames(sym)
    win = R48.window(df, "2024-01-01", "2024-06-30")
    sg = (R48.portfolio_signal(df, sym)
          .reindex(win.index, fill_value=False).fillna(False).astype(bool))
    old = C.STOP_ATR
    C.STOP_ATR = STOP
    try:
        _, a = C.simulate(win, sg, C.atr(win), notional=C.TRADE_USD, bar_secs=14400,
                          strict_single=True, atr_trail=TRAIL)
        _, b = C.simulate(win, sg, C.atr(win), notional=C.TRADE_USD, bar_secs=86400,
                          strict_single=True, atr_trail=TRAIL)
    finally:
        C.STOP_ATR = old
    same = len(a) == len(b) and all(
        abs(x["pnl"] - y["pnl"]) < 1e-9 and x["entry_j"] == y["entry_j"]
        for x, y in zip(a, b)
    )
    print(f"  bar_secs على شريحة BTC: 14400 و86400 {'متطابقان' if same else 'مختلفان'} "
          f"(صفقات={len(a)}/{len(b)})")
    if not same:
        raise SystemExit("bar_secs غيّر ناتج strict_single — أوقف وأبلغ، لا قياس")


def run_canary() -> dict:
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    raw = can.stdout
    cj = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
    print(f"  كاناري المحرك الحي: {cj.get('canary')} net={cj.get('got', {}).get('net')}")
    if cj.get("canary") != "ok":
        print(can.stdout[-1500:])
        print(can.stderr[-1500:])
        raise SystemExit("الكاناري لم يُرجع canary=ok — أوقف")
    return cj


def run_selftests() -> None:
    for tool in ("fill_invariant_check.py", "position_sequencing_audit.py"):
        st = subprocess.run([sys.executable, str(ROOT / "tools" / tool), "--selftest"],
                            capture_output=True, text=True)
        tail = (st.stdout or st.stderr).strip().splitlines()
        print(f"  {tool}: {(tail[-1] if tail else 'بلا مخرج')} (exit={st.returncode})")
        if st.returncode != 0:
            print(st.stdout[-1500:])
            print(st.stderr[-800:])
            raise SystemExit(f"{tool} selftest فشل — أوقف")


def lab_canary_status() -> str:
    csv = ROOT / "history" / "research" / "hyp_lab_out" / "L0046" / "phase3_basis_repaired.csv"
    if not csv.exists():
        msg = "لم يُشغَّل: phase3_basis_repaired.csv غير موجود في المستودع. لم يُصنَّع بديل."
        print(f"  كاناري المختبر: {msg}")
        return msg
    st = subprocess.run([sys.executable, str(ROOT / "tools" / "canary_lab.py"), "--json"],
                        capture_output=True, text=True)
    print(st.stdout.strip() or st.stderr[-400:])
    return st.stdout.strip()


def prepare() -> list[str]:
    L36.set_core()
    NC.EMA_FAST = 8
    M213._cache.clear()
    R48._SIG.clear()
    C.STOP_ATR = STOP
    restore_cost()
    if abs(C.COST_PER_SIDE - DEFAULT_COST) > 1e-15:
        raise SystemExit("كلفة الافتراضي ليست 0.0013")
    cells = R48._cells()
    syms = sorted({c["symbol"] for c in cells})
    print(f"  خلايا={len(cells)} عملات={len(syms)}: {', '.join(syms)}")
    if set(syms) != L0048_COINS:
        raise SystemExit(f"سلة العملات تختلف عن L0048: {sorted(set(syms) ^ L0048_COINS)}")
    R48.SYMS = syms
    R46.build_cache(syms)
    return syms


def phase0(syms: list[str]) -> dict:
    print("\n══ مرحلة 0: إعادة إنتاج كتاب L0048 (لا تُحسب) ══")
    restore_cost()
    R48.BAR = 4 * 3600
    out = {"book": {}, "seeds": []}
    books = {}
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        rows = direct_book(s0, s1)
        st = summarize(rows, DEFAULT_COST)
        save_trades(f"phase0_{lbl}", rows)
        exp = P0_BOOK[lbl]
        delta = abs(st["net"] - exp["net"])
        print(f"  كتاب {lbl}: {st['net']}$ / {st['trades']}  (مرجع {exp['net']}$ / {exp['trades']})"
              f"  فرق={delta:.4f}")
        if delta > 0.5 or st["trades"] != exp["trades"]:
            raise SystemExit("أساس L0048 لم يُعَد إنتاجه ضمن ±0.5$ وعدد الصفقات. أوقف. لا قياس.")
        if st["overlapping_trades"] != 0:
            raise SystemExit("تداخل المرحلة 0 ≠ 0 — أوقف")
        books[lbl] = rows
        out["book"][lbl] = st
    print("  ✅ أساس الكتاب مطابق")
    prove_bar_secs()

    print("  مطابقة بذور L0048 (مرحلة 0، لا تُحسب)...")
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        outs = build_outcomes(syms, s0, s1)
        cached = cache_book(outs, s0, s1)
        assert_equiv(f"p0-{lbl}", books[lbl], cached, DEFAULT_COST)
        tgt = targets_of(books[lbl], list(outs))
        for seed in SEEDS:
            rows = random_book(outs, seed, tgt)
            st = summarize(rows, DEFAULT_COST)
            exp_net, exp_n = P0_SEEDS[lbl][seed]
            print(f"    بذرة {seed} {lbl}: {st['net']}$ / {st['trades']}  مرجع {exp_net}$ / {exp_n}")
            if abs(st["net"] - exp_net) > 0.5 or st["trades"] != exp_n:
                raise SystemExit("بذرة L0048 لم تُطابق. آلة العشوائي ليست نفسها. أوقف.")
            out["seeds"].append({"seed": seed, "window": lbl, **st})
    print("  ✅ البذور مطابقة. آلة L0048 هي آلة هذا القياس.")
    return out


def counted_cost(syms: list[str], cost: float, with_seeds: bool) -> None:
    tag = f"c{int(round(cost * 10000)):03d}"
    print(f"\n══ كلفة {cost:.4%} إطار 4h بذور={with_seeds} ══")
    set_cost(cost)
    R48.BAR = 4 * 3600
    R48.frames = R46.frames
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        rows = direct_book(s0, s1)
        save_trades(f"{tag}_{lbl}", rows)
        record(f"محفظة كلفة {cost:.2%}", "اختيار" if lbl == "SEL" else "حكم",
               rows, cost, "4h", 14400, None, True)
        if not with_seeds:
            continue
        outs = build_outcomes(syms, s0, s1)
        cached = cache_book(outs, s0, s1)
        assert_equiv(f"{tag}-{lbl}", rows, cached, cost)
        tgt = targets_of(rows, list(outs))
        for seed in SEEDS:
            rrows = random_book(outs, seed, tgt)
            save_trades(f"{tag}_s{seed}_{lbl}", rrows)
            record(f"عشوائي كلفة {cost:.2%} بذرة {seed}",
                   "اختيار" if lbl == "SEL" else "حكم",
                   rrows, cost, "4h", 14400, seed, True)
    restore_cost()


def build_daily(syms: list[str]) -> None:
    print("\n══ بناء شموع اليوم (1440 دقيقة، origin الافتراضي لـ to_bars) ══")
    daily = {}
    for sym in syms:
        path = DAILY_CACHE / f"{sym}_1d.parquet"
        if not path.exists():
            t0 = time.time()
            d1 = C.load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"),
                        start=WARM, end=JUD_E)
            C.to_bars(d1, 1440).to_parquet(path)
            del d1
            print(f"  كاش يومي {sym} ({time.time()-t0:.1f}s)", flush=True)
        df = pd.read_parquet(path)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        daily[sym] = df
        first = df.index.min()
        if first.hour != 0 or first.minute != 0:
            raise SystemExit(f"شمعة اليوم ليست على منتصف الليل UTC: {sym} {first}")
    # إثبات أن الفرق الشائع يوم واحد حيث لا فجوة.
    btc = daily["BTCUSDT"]
    diffs = btc.index.to_series().diff().dropna()
    mode = diffs.mode().iloc[0]
    print(f"  أول شمعة BTC={btc.index.min()}  الفرق الشائع={mode}  عدد={len(btc)}")
    if mode != pd.Timedelta(days=1):
        raise SystemExit(f"شبكة اليوم ليست 1D: {mode}")

    def frames_1d(sym: str) -> pd.DataFrame:
        return daily[sym]

    R48.frames = frames_1d
    R48.BAR = 86400
    R48._SIG.clear()
    M213._cache.clear()
    restore_cost()


def counted_daily(syms: list[str]) -> None:
    print("\n══ إطار يومي، كلفة 0.13%، محفظة + 5 بذور ══")
    cost = DEFAULT_COST
    set_cost(cost)
    for lbl, s0, s1 in (("SEL", DEC_S, DEC_E), ("JUD", JUD_S, JUD_E)):
        rows = direct_book(s0, s1)
        save_trades(f"d1_{lbl}", rows)
        record("محفظة إطار يومي", "اختيار" if lbl == "SEL" else "حكم",
               rows, cost, "1d", 86400, None, True)
        outs = build_outcomes(syms, s0, s1)
        cached = cache_book(outs, s0, s1)
        assert_equiv(f"d1-{lbl}", rows, cached, cost)
        tgt = targets_of(rows, list(outs))
        for seed in SEEDS:
            rrows = random_book(outs, seed, tgt)
            save_trades(f"d1_s{seed}_{lbl}", rrows)
            record(f"عشوائي إطار يومي بذرة {seed}",
                   "اختيار" if lbl == "SEL" else "حكم",
                   rrows, cost, "1d", 86400, seed, True)
    restore_cost()


def guards() -> None:
    print("\n══ حرّاس ملفات الصفقات ══")
    groups = [
        (DEFAULT_COST, "4h", pathlib.Path.home() / ".cache" / "l0046_frames", "phase0_"),
        (0.0, "4h", pathlib.Path.home() / ".cache" / "l0046_frames", "c000_"),
        (0.0005, "4h", pathlib.Path.home() / ".cache" / "l0046_frames", "c005_"),
        (0.0010, "4h", pathlib.Path.home() / ".cache" / "l0046_frames", "c010_"),
        (0.0002, "4h", pathlib.Path.home() / ".cache" / "l0046_frames", "c002_"),
        (DEFAULT_COST, "1d", DAILY_CACHE, "d1_"),
    ]
    bad = []
    for cost, tag, frames, prefix in groups:
        files = sorted(OUT.glob(f"trades_{prefix}*.csv"))
        if not files:
            bad.append(f"لا ملفات للبادئة {prefix}")
            continue
        for f in files:
            st = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
                 "--trades", str(f), "--frames", str(frames),
                 "--cost", str(cost), "--bar-tag", tag],
                capture_output=True, text=True)
            print(st.stdout.strip())
            if st.returncode != 0 or "تُخطّي=0" not in st.stdout or "شموع ناقصة=0" not in st.stdout:
                # السطر فيه «تُخطّي=0» إن لم يُتخطَّ شيء. نفحص الحقل أيضًا عبر إعادة خفيفة.
                bad.append(f"{f.name}: exit={st.returncode}")
            au = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "position_sequencing_audit.py"),
                 "--trades", str(f), "--require-zero"],
                capture_output=True, text=True)
            if au.returncode != 0:
                bad.append(f"تسلسل {f.name}: {au.stdout[-200:]} {au.stderr[-200:]}")
    if bad:
        print("فشل الحراس:")
        for b in bad:
            print(" -", b)
        raise SystemExit("حارس فشل")
    print("  ✅ التعبئة والتسلسل على كل ملف")


def write_outputs(canary: dict, lab: str, p0: dict) -> None:
    meas = pd.DataFrame(MEASURED)
    meas.to_csv(OUT / "measurements.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(LEDGER).to_csv(OUT / "attempt_ledger.csv", index=False, encoding="utf-8-sig")
    # ملخص العشوائي حيث وُجد
    rnd = meas[meas["seed"].notna()] if "seed" in meas.columns else meas.iloc[0:0]
    rows = []
    if len(rnd):
        for (frame, cost, window), g in rnd.groupby(["frame", "cost", "الفترة"]):
            rows.append({
                "frame": frame, "cost": cost, "الفترة": window,
                "mean": round(float(g["net"].mean()), 2),
                "min": round(float(g["net"].min()), 2),
                "max": round(float(g["net"].max()), 2),
                "n": int(len(g)),
            })
    pd.DataFrame(rows).to_csv(OUT / "random_summary.csv", index=False, encoding="utf-8-sig")
    env = {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "cost_default_file": DEFAULT_COST,
        "stop": STOP,
        "trail": TRAIL,
        "seeds": list(SEEDS),
        "cap": CAP,
        "counted": len(LEDGER),
        "canary": canary.get("canary"),
        "canary_net": canary.get("got", {}).get("net"),
        "canary_lab": lab,
        "phase0_sel": p0["book"]["SEL"]["net"],
        "phase0_jud": p0["book"]["JUD"]["net"],
    }
    (OUT / "env_dump.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    blobs = []
    for name in ("measurements.csv", "random_summary.csv", "attempt_ledger.csv"):
        data = (OUT / name).read_bytes()
        blobs.append(f"{name} {hashlib.sha256(data).hexdigest()}")
    (OUT / "sha256.txt").write_text("\n".join(blobs) + "\n", encoding="utf-8")
    print("\n".join(blobs))
    print(f"العدّ = {len(LEDGER)}/{CAP}")
    if len(LEDGER) != CAP:
        raise SystemExit(f"العدّ {len(LEDGER)} ≠ {CAP}")


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0049 — كلفة مقابل حافة. قياس فقط. السقف 40.")
    print("═" * 74)
    (OUT / "grid_precommitted.txt").write_text(
        "شبكة مُعلَنة قبل أي رقم حكم:\n"
        "0.00% و 0.05%: محفظة+5 بذور × فترتين = 24\n"
        "0.10% و 0.02%: محفظة فقط × فترتين = 4\n"
        "يومي 1440 / bar_secs=86400 / كلفة 0.13%: محفظة+5 بذور × فترتين = 12\n"
        "المجموع 40.\n"
        "لم يُقَس: 8h, 12h, 2d, 0.075%, عشوائي عند 0.10% و 0.02%.\n"
        "لا تُضاف بذور بعد رؤية الحكم حتى لو كان 0.10 أو 0.02 موجبًا.\n",
        encoding="utf-8")
    canary = run_canary()
    run_selftests()
    lab = lab_canary_status()
    syms = prepare()
    p0 = phase0(syms)
    counted_cost(syms, 0.0, True)
    counted_cost(syms, 0.0005, True)
    counted_cost(syms, 0.0010, False)
    counted_cost(syms, 0.0002, False)
    build_daily(syms)
    counted_daily(syms)
    restore_cost()
    if abs(C.COST_PER_SIDE - DEFAULT_COST) > 1e-15:
        raise SystemExit("لم تُعَد كلفة الافتراضي")
    write_outputs(canary, lab, p0)
    guards()
    print(f"انتهى في {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
