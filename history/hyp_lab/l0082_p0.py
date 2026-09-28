#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0082 · P0 — البيانات والبنية · G0
تنزيل شموع 4h للأصول الاثني عشر 2021-01-01 → 2026-09-27، تخزين parquet،
كتابة data_coverage_l0082.csv. فجوة زمنية > 24h ⇒ استبدال بالاحتياط.
G0 يمر إذا ≥10 أصول مكتملة.
"""
from __future__ import annotations

import json
import sys
import pathlib
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import l0082_common as C  # noqa: E402


def months_between(start: str, end: str):
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    out = []
    cur = s.replace(day=1)
    while cur <= e:
        out.append(cur.strftime("%Y-%m"))
        cur = (cur + pd.offsets.MonthBegin(1))
    return out


def days_in_month_after(month_last_available: str, end: str):
    """أيام مفردة من بداية الشهر التالي لآخر شهر مجمّع حتى end."""
    start = (pd.Timestamp(month_last_available + "-01") + pd.offsets.MonthBegin(1))
    e = pd.Timestamp(end)
    out = []
    cur = start
    while cur <= e:
        out.append(cur.strftime("%Y-%m-%d"))
        cur += pd.Timedelta(days=1)
    return out


def download_symbol(sym: str):
    """يعيد (DataFrame, log). يجرب المجمّع الشهري ثم يكمل بالأيام المفردة."""
    frames = []
    log = {"symbol": sym, "monthly_ok": 0, "monthly_missing": [], "daily_ok": 0, "daily_missing": []}
    months = months_between(C.DATA_START, "2026-08")  # المجمّع حتى 2026-08 (سجل التحقق 10.2)

    def get_month(mo):
        url = f"{C.BASE_VISION}/monthly/klines/{sym}/4h/{sym}-4h-{mo}.zip"
        b = C.fetch_zip_csv(url)
        return mo, b

    with ThreadPoolExecutor(max_workers=8) as ex:
        for mo, b in ex.map(get_month, months):
            if b is None:
                log["monthly_missing"].append(mo)
            else:
                frames.append(C.parse_kline_csv(b))
                log["monthly_ok"] += 1

    # الأيام المفردة 2026-09-01 → 2026-09-27
    days = days_in_month_after("2026-08", C.DATA_END)

    def get_day(d):
        url = f"{C.BASE_VISION}/daily/klines/{sym}/4h/{sym}-4h-{d}.zip"
        b = C.fetch_zip_csv(url)
        return d, b

    with ThreadPoolExecutor(max_workers=8) as ex:
        for d, b in ex.map(get_day, days):
            if b is None:
                log["daily_missing"].append(d)
            else:
                frames.append(C.parse_kline_csv(b))
                log["daily_ok"] += 1

    if not frames:
        return None, log
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["open_time"]).sort_values("open_time").reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)

    # ---- ردم الثغرات الداخلية من الملفات اليومية ----
    # المجمّع الشهري يُسقط أحيانًا أيامًا لبعض الرموز؛ هذه الأيام متاحة في الملفات اليومية.
    # نبني الشبكة المتوقعة كل 4h ونردم كل طابع مفقود من ملف يومه، قبل اللجوء لأي استبدال.
    grid = pd.date_range(df["dt"].iloc[0], df["dt"].iloc[-1], freq="4h", tz="UTC")
    have = set(df["dt"])
    missing_dates = sorted({t.strftime("%Y-%m-%d") for t in grid if t not in have})
    if missing_dates:
        log["backfilled_dates"] = missing_dates

        def get_day2(d):
            url = f"{C.BASE_VISION}/daily/klines/{sym}/4h/{sym}-4h-{d}.zip"
            return d, C.fetch_zip_csv(url)

        bf = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            for d, b in ex.map(get_day2, missing_dates):
                if b is None:
                    log["daily_missing"].append(d)
                else:
                    bf.append(C.parse_kline_csv(b))
        if bf:
            add = pd.concat(bf, ignore_index=True)
            add["dt"] = pd.to_datetime(add["open_time"], unit="ms", utc=True)
            df = pd.concat([df, add], ignore_index=True)
            df = df.drop_duplicates(subset=["open_time"]).sort_values("open_time").reset_index(drop=True)

    # القص على الحدود
    mask = (df["dt"] >= pd.Timestamp(C.DATA_START, tz="UTC")) & (df["dt"] <= pd.Timestamp(C.DATA_END + " 23:59:59", tz="UTC"))
    df = df[mask].reset_index(drop=True)
    return df, log


def coverage_row(sym: str, df: pd.DataFrame):
    dt = df["dt"]
    gaps = dt.diff().dropna()
    # فجوة > 24h
    big = gaps[gaps > pd.Timedelta(hours=24)]
    return {
        "symbol": sym,
        "first": dt.iloc[0].strftime("%Y-%m-%d %H:%M"),
        "last": dt.iloc[-1].strftime("%Y-%m-%d %H:%M"),
        "bars": int(len(df)),
        "gaps_gt_24h": int(len(big)),
        "max_gap_hours": round(float(gaps.max().total_seconds() / 3600.0), 2) if len(gaps) else 0.0,
    }


def main():
    coverage = []
    logs = []
    used = list(C.ASSETS)
    reserve = list(C.RESERVE)
    final_assets = []

    for sym in list(used):
        print(f"[P0] downloading {sym} ...", flush=True)
        df, log = download_symbol(sym)
        logs.append(log)
        if df is None or len(df) == 0:
            print(f"[P0] {sym} فارغ — استبدال بالاحتياط", flush=True)
            continue
        row = coverage_row(sym, df)
        # قاعدة: فجوة > 24h ⇒ استبدال بالاحتياط التالي (P0)
        if row["gaps_gt_24h"] > 0 and reserve:
            rep = reserve.pop(0)
            print(f"[P0] {sym} فيه {row['gaps_gt_24h']} فجوة>24h — استبدال بـ{rep}", flush=True)
            log["replaced_by"] = rep
            row["replaced"] = True
            coverage.append(row)
            dfr, logr = download_symbol(rep)
            logs.append(logr)
            if dfr is not None and len(dfr):
                rowr = coverage_row(rep, dfr)
                coverage.append(rowr)
                (C.DATA_DIR / rep).mkdir(parents=True, exist_ok=True)
                dfr.to_parquet(C.DATA_DIR / rep / "4h.parquet")
                final_assets.append(rep)
            continue
        (C.DATA_DIR / sym).mkdir(parents=True, exist_ok=True)
        df.to_parquet(C.DATA_DIR / sym / "4h.parquet")
        coverage.append(row)
        final_assets.append(sym)

    cov = pd.DataFrame(coverage)
    cov.to_csv(C.OUT / "data_coverage_l0082.csv", index=False)
    (C.OUT / "_p0_download_log.json").write_text(json.dumps(logs, ensure_ascii=False, indent=2))
    (C.OUT / "_p0_final_assets.json").write_text(json.dumps(final_assets, ensure_ascii=False, indent=2))

    complete = len(final_assets)
    g0 = "PASS" if complete >= 10 else "FAIL"
    print(f"\n[P0] الأصول المكتملة: {complete}/12  → G0={g0}")
    print(cov.to_string(index=False))
    if g0 != "PASS":
        print("[P0] INSUFFICIENT — أقل من 10 أصول")
    return g0


if __name__ == "__main__":
    main()
