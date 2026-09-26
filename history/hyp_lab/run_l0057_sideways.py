# -*- coding: utf-8 -*-
"""L0057 — العرضي. قياس وحكم. لا تطوير حرّ.

القواعد مكتوبة هنا قبل أي رقم.

السقف 36.
  مرحلة 0 لا تُحسب. أي فرق يوقف الجولة قبل العتبة وقبل الشبكة.
  مرحلة أ (3 من 12): خريطة 10$ على الفترتين، وخريطة 5$ على الاختيار.
      خريطة 20$ إن طابقت 10$ لا تُعاد. المقاعد الفارغة لا تُملأ.
  مرحلة ب (2 من 4): مسبار شبكة ثابتة وديناميكية على BTC، أول مقطع عرضي مؤهّل.
      مخالفة تعبئة واحدة توقف الجولة. لا إصلاح للمحرك. لا تفسير لربح الشبكة.
  مرحلة ج (14 من 14) إن اجتازت ب: ثابتة وديناميكية في الفترتين، ثم 10 بذور
      على الأفضل في الاختيار فقط. الأفضل يُكتب قبل الحكم.
  مرحلة د تتجاوز سقف 6: 0.130% في الفترتين للخريطة المشدّدة، و10 بذور عند 0.115%.
      المجموع يبقى دون 36. البذور لا تُقطع.

بذور: 110057 210057 310057 410057 510057.

الشبكة تُقاد من أصناف nova_v8 بلا تعديل ملف. المناخ اليومي shift(1)، لا regime.py.
لا تُجمع دولارات الشبكة مع دولارات المحفظة.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import platform
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path("/home/user/l0057")
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

src = (ROOT / "history" / "hyp_lab" / "run_l0056_widen_book.py").read_text(encoding="utf-8")
src = src.replace('pathlib.Path("/home/user/l0056")', 'pathlib.Path("/home/user/l0057")')
src = src.replace('if __name__ == "__main__":', 'if False:')
patched = pathlib.Path("/tmp/r56_l0057.py")
patched.write_text(src, encoding="utf-8")
spec = importlib.util.spec_from_file_location("r56_l0057", patched)
R56 = importlib.util.module_from_spec(spec)
sys.modules["r56_l0057"] = R56
spec.loader.exec_module(R56)

import nova_v8.grid as G
import nova_v8.dynamic_grid as DG
import nova_v8.config as VC
import nova_v8.oracle as oracle

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0057"
OUT.mkdir(parents=True, exist_ok=True)
R56.OUT = OUT
R56.DAILY = pathlib.Path.home() / ".cache" / "l0057_daily"
R56.DAILY.mkdir(parents=True, exist_ok=True)
ONE_M = pathlib.Path.home() / ".cache" / "l0057_1m"
ONE_M.mkdir(parents=True, exist_ok=True)

COST = 0.00115
COST_130 = 0.00130
SEEDS = (110057, 210057, 310057, 410057, 510057)
CAP = 36
WINNER = R56.WINNER
LEDGER: list[dict] = []

RULE = (
    "تُقبل الخانة إذا صافي ملف L0051 ≥ العتبة و صافي الصفقة = الصافي/الصفقات ≥ 0.05 "
    "و الصفقات ≥ 30. تُطبَّق على الـ21 بالتساوي. لا استثناء لخانة رابحة. "
    "العتبة الأساسية 10$. الحساسية 5$ و20$ تغيّر سقف الصافي فقط."
)


def log(name: str, window: str, phase: str) -> None:
    if len(LEDGER) >= CAP:
        raise SystemExit(f"تجاوز السقف {CAP}")
    LEDGER.append({"#": len(LEDGER) + 1, "المرحلة": phase, "القياس": name, "الفترة": window})


def dump(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def apply_rule(cells: list[dict], floor: float) -> list[list[str]]:
    out = []
    for c in cells:
        per = (c["net"] / c["trades"]) if c["trades"] else None
        if c["net"] >= floor and per is not None and per >= 0.05 and c["trades"] >= 30:
            out.append([c["column"], c["regime"]])
    return sorted(out)


def regime_book(rows: list[dict]) -> dict:
    out = {}
    if not rows:
        return out
    t = pd.DataFrame(rows)
    for reg, g in t.groupby(t["regime"].fillna("غير مصنّف")):
        p = g["pnl"].to_numpy(float)
        out[str(reg)] = {
            "net": round(float(p.sum()), 2),
            "trades": int(len(g)),
            "per": round(float(p.sum()) / len(g), 5),
            "win_pct": round(100 * float((p > 0).mean()), 1),
        }
    return out


def gate(label: str, st: dict, net: float, n: int) -> None:
    print(f"  تحقق {label}: {st['net']}$ / {st['trades']} مرجع {net}$ / {n}", flush=True)
    if abs(st["net"] - net) > 0.5 or st["trades"] != n or st["overlapping_trades"]:
        raise SystemExit(f"الواقع خالف الورقة: {label} = {st}. أوقف.")


def run_port(name, fname, enabled, s0, s1, window, cost, phase, counted) -> tuple[dict, list]:
    R56.use_syms(R56.archive_symbols())
    rec, rows = R56.run_book(
        name, fname, R56.routed(enabled), WINNER, s0, s1, window, cost, False, phase,
        {"basket": 17},
    )
    if counted:
        log(name, window, phase)
    return rec, rows


def write_rule(cells: list[dict]) -> dict:
    maps = {str(f): apply_rule(cells, f) for f in (5, 10, 20)}
    payload = {
        "rule": RULE,
        "per_definition": "صافي الملف / صفقات الملف. لا إعادة قياس للخلية.",
        "source": "L0051/routing_map.json",
        "source_sha256": hashlib.sha256(R56.MAP_SRC.read_bytes()).hexdigest(),
        "floors": maps,
        "written_before_any_measurement": True,
        "bias_disclosure": "فكرة التشديد خطرت بعد رؤية خسارة العرضي في الحكم. العتبة كُتبت قبل إعادة الاشتقاق وتُطبَّق على الكل.",
    }
    dump(OUT / "acceptance_rule_l0057.json", payload)
    return payload


def segments_of(reg: pd.Series) -> list[dict]:
    return oracle.RegimeTransitions.segments(reg)


def load_1m(sym: str) -> pd.DataFrame:
    path = ONE_M / f"{sym}_1m.parquet"
    if not path.exists():
        d1 = R56.C.load(str(ROOT / "crypto_archive" / f"{sym}_1m.parquet"), start=R56.WARM, end=R56.JUD_E)
        if d1.index.tz is None:
            d1.index = d1.index.tz_localize("UTC")
        d1.to_parquet(path)
        print(f"  1m {sym} {len(d1)}", flush=True)
    df = pd.read_parquet(path)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def map_regime_1m(sym: str, df: pd.DataFrame) -> pd.Series:
    daily = R56.REG4H[sym]
    if daily.empty:
        return pd.Series("غير مصنّف", index=df.index)
    lookup = {}
    for ts, val in daily.items():
        lookup[pd.Timestamp(ts).normalize()] = val
    return pd.Series([lookup.get(ts.normalize(), np.nan) for ts in df.index], index=df.index, dtype=object)


_OBS = {"log": None, "bar": None, "installed": False}


def install_cell_observer() -> None:
    if _OBS["installed"]:
        return
    orig = G._Cell.on_bar
    flat = G._Cell.flatten_usd

    def on_bar(self, o, h, l, c):
        was, cyc = self.open, self.cycles
        orig(self, o, h, l, c)
        log, bar = _OBS["log"], _OBS["bar"]
        if log is None or not bar:
            return
        if not was and self.open:
            log.append({"kind": "buy", "px": float(self.buy), "ts": bar["ts"], "lo": l, "hi": h})
        if self.cycles > cyc:
            log.append({"kind": "sell", "px": float(self.sell), "ts": bar["ts"], "lo": l, "hi": h})

    def flatten(self, cur, market_slip_pct=None):
        was = self.open
        out = flat(self, cur, market_slip_pct)
        log, bar = _OBS["log"], _OBS["bar"]
        if was and log is not None and bar:
            log.append({"kind": "flatten", "px": float(cur), "ts": bar["ts"], "lo": bar["l"], "hi": bar["h"]})
        return out

    G._Cell.on_bar = on_bar
    G._Cell.flatten_usd = flatten
    _OBS["installed"] = True


def arm_static(grid, bar, log) -> None:
    install_cell_observer()
    _OBS["log"] = log
    _OBS["bar"] = bar
    del grid


def outside(px, lo, hi) -> bool:
    tol = 1e-6 * max(abs(lo), abs(hi), 1e-9)
    return (lo - px) > tol or (px - hi) > tol


def pair_trades(sym: str, log: list[dict], cost: float) -> list[dict]:
    open_buy = []
    rows = []
    for ev in log:
        if ev["kind"] == "buy":
            open_buy.append(ev)
        elif ev["kind"] in ("sell", "flatten") and open_buy:
            buy = open_buy.pop(0)
            rows.append({
                "symbol": sym,
                "entry_time": buy["ts"],
                "exit_time": ev["ts"],
                "entry": buy["px"] * (1 + cost),
                "exit": ev["px"] * (1 - cost),
                "market_entry": buy["px"],
                "market_exit": ev["px"],
                "entry_lo": buy["lo"], "entry_hi": buy["hi"],
                "exit_lo": ev["lo"], "exit_hi": ev["hi"],
                "kind": ev["kind"],
                "pnl": 0.0,
                "notional": VC.GRID_CAPITAL_USD,
                "bars_held": 1,
            })
    return rows


def local_violations(rows: list[dict]) -> list[dict]:
    bad = []
    for r in rows:
        if outside(r["market_entry"], r["entry_lo"], r["entry_hi"]) or outside(r["market_exit"], r["exit_lo"], r["exit_hi"]):
            bad.append(r)
    return bad


def synthetic_probe() -> dict:
    cell = G._Cell(105.0, 110.0, 100.0)
    cell.on_bar(100.0, 102.0, 99.0, 101.0)
    buy_outside = cell.open and outside(105.0, 99.0, 102.0)
    cell2 = G._Cell(90.0, 95.0, 100.0)
    cell2.open = True
    cell2.on_bar(100.0, 102.0, 99.0, 101.0)
    sell_outside = cell2.cycles == 1 and outside(95.0, 99.0, 102.0)
    # 95 is inside [99, 102]? 95 < 99, yes outside. h>=95 so they sell.
    return {
        "buy_fills_above_high": bool(buy_outside),
        "sell_fills_below_low": bool(sell_outside),
        "note": "استدعاء مباشر لـ _Cell.on_bar. ليس قياس سوق. يثبت أن الشرط l<=buy لا يشترط buy<=high.",
    }


def run_static_symbol(sym: str, df: pd.DataFrame, reg: pd.Series, s0: str, s1: str) -> tuple[list[dict], list[dict]]:
    win = df[(df.index >= s0) & (df.index <= s1)]
    if len(win) < VC.GRID_RANGE_LOOKBACK_BARS + VC.GRID_MIN_LIFE_BARS:
        return [], []
    reg_w = reg.reindex(win.index)
    units = []
    fills = []
    look = VC.GRID_RANGE_LOOKBACK_BARS
    o = win["open"].to_numpy(float)
    h = win["high"].to_numpy(float)
    l = win["low"].to_numpy(float)
    c = win["close"].to_numpy(float)
    idx = win.index
    for seg in segments_of(reg_w.fillna("غير مصنّف")):
        if seg["regime"] != "عرضي":
            continue
        s_pos = int(idx.searchsorted(seg["start"], side="left"))
        e_pos = int(idx.searchsorted(seg["end"], side="right")) - 1
        if e_pos - s_pos < VC.GRID_MIN_LIFE_BARS or s_pos < look:
            continue
        lo = float(np.nanmin(l[s_pos - look:s_pos]))
        hi = float(np.nanmax(h[s_pos - look:s_pos]))
        mid = (hi + lo) / 2.0
        span = (hi - lo) / mid if mid > 0 else 0.0
        if not (VC.GRID_RANGE_MIN_PCT <= span <= VC.GRID_RANGE_MAX_PCT):
            continue
        bar = {}
        log_ev = []
        grid = G.Grid(sym, s_pos, lo, hi, float(c[s_pos - 1]))
        arm_static(grid, bar, log_ev)
        for j in range(s_pos, min(e_pos + 1, len(win))):
            if grid.closed:
                break
            bar.update(ts=idx[j], o=o[j], h=h[j], l=l[j], c=c[j])
            grid.on_bar(float(o[j]), float(h[j]), float(l[j]), float(c[j]), j, market_slip_pct=0.0)
        if not grid.closed:
            close_i = min(e_pos, len(win) - 1)
            bar.update(ts=idx[close_i], o=o[close_i], h=h[close_i], l=l[close_i], c=c[close_i])
            grid.close(close_i, "نهاية-الحالة", float(c[close_i]), market_slip_pct=0.0)
        if grid.bars < VC.GRID_MIN_LIFE_BARS:
            continue
        units.append({
            "symbol": sym, "start": str(idx[s_pos]), "end": str(idx[grid.close_bar or e_pos]),
            "bars": int(grid.bars), "net": float(grid.net_usd), "cycles": int(grid.cycles),
            "capital": float(VC.GRID_CAPITAL_USD), "reason": grid.close_reason,
        })
        fills.extend(pair_trades(sym, log_ev, COST))
    return units, fills


def set_grid_cost() -> None:
    VC.COMMISSION_PCT = COST
    G._BUY_FEE = COST
    G._SELL_FEE = COST


def official_guard(path: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
         "--trades", str(path), "--frames", str(ONE_M), "--cost", str(COST), "--bar-tag", "1m"],
        capture_output=True, text=True,
    )


def stop_grid(reason: str, examples: list) -> None:
    dump(OUT / "grid_fill_stop.json", {"stopped": True, "reason": reason, "examples": examples[:8]})
    print(f"  أوقف الشبكة: {reason}", flush=True)
    raise SystemExit(2)


def main() -> int:
    t0 = time.time()
    print("═" * 74)
    print(" L0057 — العرضي. السقف 36. الشبكة تُفحص قبل ربحها.")
    print("═" * 74)
    mp = json.loads(R56.MAP_SRC.read_text(encoding="utf-8"))
    digest = hashlib.sha256(R56.MAP_SRC.read_bytes()).hexdigest()
    if not digest.startswith("14df873e") or len(mp["cells"]) != 21:
        raise SystemExit("الخريطة ليست مرجع L0051")
    rule = write_rule(mp["cells"])
    print("  خرائط مكتوبة قبل القياس", {k: len(v) for k, v in rule["floors"].items()})
    can = R56.run_canary()
    R56.run_selftests()
    R56.prepare()
    R56.build_regimes(R56.archive_symbols())
    set_grid_cost()

    print("\n══ مرحلة 0 ══")
    enabled = set(R56.ENABLED)
    rec, rows = run_port("محفظة 17", "p0_c00130_JUD", enabled, R56.JUD_S, R56.JUD_E, "حكم", COST_130, "0", False)
    gate("0.130% حكم", rec, 30.99, 464)
    rec, rows = run_port("محفظة 17", "p0_c00115_JUD", enabled, R56.JUD_S, R56.JUD_E, "حكم", COST, "0", False)
    gate("0.115% حكم", rec, 33.24, 464)
    split = regime_book(rows)
    side = split.get("عرضي", {"net": None, "trades": None})
    print(f"  عرضي الحكم: {side}", flush=True)
    if side["net"] is None or abs(side["net"] - (-12.61)) > 0.5 or side["trades"] != 24:
        raise SystemExit(f"العرضي خالف الورقة: {side}. أوقف.")
    rec_sel, rows_sel = run_port("محفظة 17", "p0_c00115_SEL", enabled, R56.DEC_S, R56.DEC_E, "اختيار", COST, "0", False)
    gate("0.115% اختيار", rec_sel, 45.66, 328)
    dump(OUT / "phase0_regimes.json", {"judgement": split, "selection": regime_book(rows_sel)})
    print("  ✅ الأربعة طابقت")

    print("\n══ مرحلة أ ══")
    map10 = {tuple(x) for x in rule["floors"]["10"]}
    map5 = {tuple(x) for x in rule["floors"]["5"]}
    map20 = {tuple(x) for x in rule["floors"]["20"]}
    dump(OUT / "routing_map_l0057.json", {
        "rule": RULE, "enabled": rule["floors"]["10"], "n_enabled": len(map10),
        "dropped_from_frozen": [list(x) for x in sorted(R56.FROZEN_ENABLED - map10)],
        "added_vs_frozen": [list(x) for x in sorted(map10 - R56.FROZEN_ENABLED)],
        "written_before_judgement": True,
    })
    a_sel, _ = run_port("خريطة 10$", "a10_c00115_SEL", map10, R56.DEC_S, R56.DEC_E, "اختيار", COST, "أ", True)
    a_jud, a_jrows = run_port("خريطة 10$", "a10_c00115_JUD", map10, R56.JUD_S, R56.JUD_E, "حكم", COST, "أ", True)
    a5, _ = run_port("خريطة 5$", "a5_c00115_SEL", map5, R56.DEC_S, R56.DEC_E, "اختيار", COST, "أ", True)
    same_20 = map20 == map10
    print(f"  خريطة 20$ تطابق 10$: {same_20}")
    if not same_20:
        run_port("خريطة 20$", "a20_c00115_SEL", map20, R56.DEC_S, R56.DEC_E, "اختيار", COST, "أ", True)
    dump(OUT / "phase_a.json", {
        "map10_sel": R56.slim(a_sel), "map10_jud": R56.slim(a_jud),
        "map5_sel": R56.slim(a5), "map20_equals_10": same_20,
        "jud_regimes": regime_book(a_jrows),
    })

    print("\n══ مرحلة ب: سلامة الشبكة ══")
    synth = synthetic_probe()
    dump(OUT / "grid_logic_probe.json", synth)
    print("  مسار الشراء فوق القمة:", synth["buy_fills_above_high"], "البيع تحت القاع:", synth["sell_fills_below_low"])
    btc = load_1m("BTCUSDT")
    reg = map_regime_1m("BTCUSDT", btc)
    units, fills = run_static_symbol("BTCUSDT", btc, reg, "2021-09-01", "2021-10-31")
    log("مسبار شبكة ثابتة BTC", "اختيار", "ب")
    probe = OUT / "trades_grid_probe_static.csv"
    pd.DataFrame(fills).to_csv(probe, index=False, encoding="utf-8-sig")
    bad = local_violations(fills)
    print(f"  مسبار ثابت: وحدات={len(units)} صفقات={len(fills)} مخالفات محلية={len(bad)}")
    if bad:
        stop_grid("تعبئة خارج الشمعة في المسبار الثابت", bad)
    if fills:
        st = official_guard(probe)
        print(st.stdout[-400:])
        if st.returncode != 0 or "مخالفات الدخول=0" not in st.stdout or "مخالفات الخروج=0" not in st.stdout:
            stop_grid("حارس التعبئة رفض مسبار الشبكة", [{"stdout": st.stdout[-800:], "stderr": st.stderr[-400:]}])
    else:
        print("  المسبار لم يفتح شبكة. المسار المعيب مثبت بالكود، ولم يُمارَس على هذا المقطع.")
    dump(OUT / "grid_probe.json", {"units": units, "fills": len(fills), "local_violations": len(bad)})
    print(f"انتهى الجزء الأول في {time.time()-t0:.0f}s  العدّ={len(LEDGER)}/{CAP}")
    dump(OUT / "ledger_partial.json", LEDGER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
