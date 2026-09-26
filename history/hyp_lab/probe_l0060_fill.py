# -*- coding: utf-8 -*-
"""مرحلة أ — فحص تعبئة long_cycle. لا رقم ربح يُعتمد من هذا الملف."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pandas as pd

ROOT = pathlib.Path("/home/user/l0060")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")

import common as C
import nova_v8.config as NC
import nova_v8.long_cycle as LC

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0060"
OUT.mkdir(parents=True, exist_ok=True)
FRAMES = pathlib.Path.home() / ".cache" / "l0060_probe_h4"
FRAMES.mkdir(parents=True, exist_ok=True)


def gap_formula(o, h, l, level):
    if l <= level:
        return o if o < level else level
    return None


def synthetic() -> list[str]:
    fails = []
    cases = [
        ("فجوة تحت المستوى", 90, 92, 88, 100, 90),
        ("لمس المستوى", 100, 101, 95, 97, 97),
        ("المستوى فوق القمة", 90, 92, 88, 95, 90),
        ("المستوى تحت القاع", 100, 101, 99, 90, None),
    ]
    for name, o, h, l, level, expect in cases:
        got = gap_formula(o, h, l, level)
        if got != expect:
            fails.append(f"{name}: {got} != {expect}")
        if got is not None and not (l <= got <= h):
            fails.append(f"{name}: التعبئة خارج الشمعة")
    return fails


def main() -> int:
    syn = synthetic()
    print("فجوات مصطنعة:", "سليمة" if not syn else syn, flush=True)
    if syn:
        raise SystemExit("صيغة الإلغاء فشلت على الحالات المصطنعة")

    # نافذة قصيرة. إن خلت من الصفقات تُمدَّد وتُسجَّل، لأنها فحص لا قياس ربح.
    windows = [("2022-01-01", "2022-07-01"), ("2021-06-01", "2023-01-01"), ("2021-06-01", "2026-08-31")]
    df = None
    recs = []
    used = None
    for s0, s1 in windows:
        df = C.load(str(ROOT / "crypto_archive" / "BTCUSDT_1m.parquet"), start=s0, end=s1)
        recs = LC.run(df, "BTCUSDT")
        used = (s0, s1, len(df), len(recs))
        print(f"  مسبار {s0}→{s1}: دقائق={len(df)} صفقات={len(recs)}", flush=True)
        if recs:
            break
    if not recs:
        raise SystemExit("لا صفقة في المسبار. الحارس لم يرَ تعبئة. أتوقف ولا أخترع رقمًا.")

    h4 = df.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    official = C.to_bars(df, 240)
    both = h4.index.intersection(official.index)
    mismatch = 0
    if len(both) == 0 or len(h4) != len(official):
        mismatch = -1
    else:
        for col in ("open", "high", "low", "close"):
            mismatch += int((h4[col].reindex(both) - official[col].reindex(both)).abs().gt(1e-9).sum())
    print(f"  اصطفاف 4h مقابل to_bars: فرق={mismatch} شموع_الوحدة={len(h4)} رسمية={len(official)}", flush=True)

    bad_ohlc = int(((h4["open"] < h4["low"]) | (h4["open"] > h4["high"])
                    | (h4["close"] < h4["low"]) | (h4["close"] > h4["high"])
                    | (h4["low"] > h4["high"])).sum())
    print(f"  شموع OHLC مكسورة: {bad_ohlc}", flush=True)

    h4.to_parquet(FRAMES / "BTCUSDT_4h.parquet")
    rows = []
    outside = []
    overhang = 0
    for r in recs:
        ts_e = pd.Timestamp(r["entry_time"])
        ts_x = pd.Timestamp(r["exit_time"])
        if ts_e.tzinfo is None:
            ts_e = ts_e.tz_localize("UTC")
        if ts_x.tzinfo is None:
            ts_x = ts_x.tz_localize("UTC")
        be, bx = h4.loc[ts_e], h4.loc[ts_x]
        entry_mkt = float(r["entry_ref_px"])
        exit_mkt = float(r["exit_px"])
        for side, px, bar in (("entry", entry_mkt, be), ("exit", exit_mkt, bx)):
            if px < float(bar["low"]) - 1e-8 or px > float(bar["high"]) + 1e-8:
                outside.append({"side": side, "px": px, "low": float(bar["low"]), "high": float(bar["high"]),
                                "reason": r["reason"], "time": str(ts_e if side == "entry" else ts_x)})
        if float(r["entry_px"]) > float(be["high"]) + 1e-8 or float(r["entry_px"]) < float(be["low"]) - 1e-8:
            overhang += 1
        # إلغاء: إن لم يكن الافتتاح تحت المستوى فالتعبئة يجب أن تكون داخل [low, open]
        if r["reason"] == "إلغاء-دورة":
            o, lo, hi = float(bx["open"]), float(bx["low"]), float(bx["high"])
            if exit_mkt != o and not (lo - 1e-8 <= exit_mkt <= o + 1e-8 and exit_mkt <= hi + 1e-8):
                outside.append({"side": "invalidation", "px": exit_mkt, "low": lo, "high": hi,
                                "open": o, "reason": r["reason"], "time": str(ts_x)})
        if r["reason"] == "توزيع-قمة" and abs(exit_mkt - float(bx["close"])) > 1e-8:
            outside.append({"side": "distribution_not_close", "px": exit_mkt, "close": float(bx["close"]),
                            "reason": r["reason"], "time": str(ts_x)})
        rows.append({
            "symbol": "BTCUSDT",
            "entry_time": ts_e.isoformat(),
            "exit_time": ts_x.isoformat(),
            "entry": entry_mkt,
            "exit": exit_mkt,
            "reason": r["reason"],
            "notional": r["notional_usd"],
            "stage": json.loads(r["snapshot"])["stage"],
        })
    path = OUT / "trades_probe_btc.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    st = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
         "--trades", str(path), "--frames", str(FRAMES), "--cost", "0", "--bar-tag", "4h"],
        capture_output=True, text=True,
    )
    print(st.stdout, flush=True)
    report = {
        "window": used,
        "ohlc_broken": bad_ohlc,
        "resample_mismatch_vs_to_bars": mismatch,
        "market_outside": outside,
        "engine_entry_px_outside_bar": overhang,
        "guard_stdout": st.stdout,
        "guard_code": st.returncode,
        "default_cost": {"commission": NC.COMMISSION_PCT, "slippage": NC.SLIPPAGE_PCT},
        "v2": os.getenv("NOVA_LC_V2", "1"),
        "reasons": dict(pd.Series([r["reason"] for r in recs]).value_counts()),
    }
    (OUT / "fill_probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if outside or st.returncode != 0 or "مخالفات الدخول=0" not in st.stdout or "تُخطّي=0" not in st.stdout:
        print("إيقاف: مخالفة تعبئة أو تخطٍّ في الحارس. لا إصلاح.", flush=True)
        return 2
    print("المسبار: سعر السوق داخل الشموع. لا مخالفة.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
