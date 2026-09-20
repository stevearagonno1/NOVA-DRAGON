#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""إعادة قراءة جداول المختبر من مسطرة 1000$/صفقة إلى 20$/صفقة (الدستور §27).

لا يعيد تشغيل الإشارات. يضرب أعمدة الدولار في 0.02 ويترك عامل الربح والصفقات ونسبة الفوز.

    python3 tools/restate_lab_dollars.py --in path.csv --out path.csv
"""
from __future__ import annotations

import argparse
import pathlib

import pandas as pd

SCALE = 20.0 / 1000.0
DOLLAR_COLS = {
    "net", "gross", "costs", "pnl", "avg_win", "avg_loss", "max_dd",
    "drawdown", "worst_day", "hold_net", "usd_cost_drag", "notional",
    "risk_total", "expectancy",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--scale", type=float, default=SCALE)
    args = ap.parse_args()
    src = pathlib.Path(args.src)
    df = pd.read_csv(src, encoding="utf-8-sig")
    for c in df.columns:
        key = c.strip().lower()
        if key in DOLLAR_COLS or key.endswith("_usd") or key.endswith("_$"):
            df[c] = pd.to_numeric(df[c], errors="coerce") * args.scale
    if "notional" in df.columns:
        df["notional"] = 20.0
    dst = pathlib.Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dst, index=False, encoding="utf-8-sig")
    print(f"scale={args.scale} rows={len(df)} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
