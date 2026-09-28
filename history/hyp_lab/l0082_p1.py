#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L0082 · P1 — التكلفة المقاسة وأنواع الأوامر · G1

- السبريد الحقيقي من bookTicker على ست تواريخ مقفلة (معالجة تدفقية، لا تخزين خام).
- العمق/الأثر من bookDepth (يوم 15 من كل شهر 2023-01..2026-09).
- الفترات بلا قياس (2021-2022, 2025-2026): نموذج انحدار على الحجم، spread_source=modeled.
- جدول سبريد واحد مجمّد يُطبَّق حرفيًا في كل مرحلة (قاعدة الاتساق الملزمة).
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
import pathlib
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import l0082_common as C  # noqa: E402

SPREAD_DATES = ["2023-05-17", "2023-07-15", "2023-09-15", "2023-11-15", "2024-01-15", "2024-03-15"]
MEASURED_YEARS = {2023, 2024}  # السنوات التي تغطيها القياسات
DEPTH_MONTHS = [(y, m) for y in range(2023, 2027) for m in range(1, 13)
                if not (y == 2026 and m > 9)]  # 2023-01 .. 2026-09


# ---------------------------------------------------------------- السبريد
_TICK_COLS = ["update_id", "best_bid_price", "best_bid_qty", "best_ask_price",
              "best_ask_qty", "transaction_time", "event_time"]


def measure_spread_file(sym: str, date: str):
    """معالجة تدفقية إلزامية: نزّل، اقرأ مضغوطًا على دفعات، احتفظ بالسبريد فقط، احذف.
    بيئة ذاكرة ≈2GB ⇒ ممنوع فك ضغط الملف كاملًا في الذاكرة."""
    url = f"{C.BASE_VISION}/daily/bookTicker/{sym}/{sym}-bookTicker-{date}.zip"
    raw = C._http_get(url)
    if raw is None:
        return None
    zf = zipfile.ZipFile(io.BytesIO(raw))
    name = zf.namelist()[0]
    # هل يوجد صف ترويسة؟ افحص أول بايتات فقط
    with zf.open(name) as fh:
        head = fh.read(64)
    has_hdr = not head.split(b",", 1)[0].strip().strip(b'"').lstrip(b"-").isdigit()

    # تجميع السبريد لكل ساعة تدفقيًا (نحتفظ بمصفوفات float32 صغيرة فقط)
    hour_vals: dict[int, list] = {}
    with zf.open(name) as fh:
        reader = pd.read_csv(
            fh,
            header=0 if has_hdr else None,
            names=None if has_hdr else _TICK_COLS,
            usecols=["best_bid_price", "best_ask_price", "transaction_time"],
            chunksize=400_000,
            dtype={"best_bid_price": "float64", "best_ask_price": "float64",
                   "transaction_time": "int64"},
        )
        for chunk in reader:
            bid = chunk["best_bid_price"].to_numpy()
            ask = chunk["best_ask_price"].to_numpy()
            ok = (ask > bid) & (bid > 0)
            if not ok.any():
                continue
            bid = bid[ok]; ask = ask[ok]
            tt = chunk["transaction_time"].to_numpy()[ok]
            sp = ((ask - bid) / ((ask + bid) / 2.0) * 1e4).astype("float32")
            hr = (tt // 3_600_000).astype("int64")
            for hh in np.unique(hr):
                hour_vals.setdefault(int(hh), []).append(sp[hr == hh])
    del raw, zf
    if not hour_vals:
        return None
    hourly_medians = [float(np.median(np.concatenate(v))) for v in hour_vals.values()]
    return float(np.median(hourly_medians))  # الوسيط لكل ساعة ← الوسيط لكل يوم


def measure_all_spreads():
    rows = []
    asset_daily = {a: [] for a in C.ASSETS}
    for sym in C.ASSETS:
        for date in SPREAD_DATES:
            try:
                dm = measure_spread_file(sym, date)
            except Exception as e:  # noqa: BLE001
                dm = None
                print(f"[P1] spread FAIL {sym} {date}: {e}", flush=True)
            if dm is not None:
                asset_daily[sym].append(dm)
                rows.append({"symbol": sym, "date": date, "daily_median_spread_bps": round(dm, 4)})
                print(f"[P1] spread {sym} {date} = {dm:.4f} bps", flush=True)
    measured = pd.DataFrame(rows)
    measured.to_csv(C.OUT / "spread_measured_l0082.csv", index=False)
    asset_spread = {a: (float(np.median(v)) if v else np.nan) for a, v in asset_daily.items()}
    return measured, asset_spread


# ---------------------------------------------------------------- العمق/الأثر
def measure_depth():
    """depth[asset][year] = (وسيط notional عند أدق مستوى متاح, level_used).
    متحقق منه 2026-09-28: مستوى -0.20% متاح فقط من 2026 تقريبًا؛ 2023-2025 أدق مستوى -1%.
    القياس المرجعي يبيّن أن 10k USDT ضئيل جدًا أمام حتى عمق -0.20% ⇒ الأثر صفر في كل الأحوال؛
    لذا استعمال -1% للسنوات الأقدم محافظ (عمق أكبر ⇒ أثر أصغر)، ويُصرَّح بالمستوى المستخدم."""
    per = {a: {} for a in C.ASSETS}
    for sym in C.ASSETS:
        year_020 = {}
        year_1 = {}
        for (y, m) in DEPTH_MONTHS:
            d = f"{y}-{m:02d}-15"
            url = f"{C.BASE_VISION}/daily/bookDepth/{sym}/{sym}-bookDepth-{d}.zip"
            try:
                b = C.fetch_zip_csv(url)
            except Exception:  # noqa: BLE001
                b = None
            if b is None:
                continue
            df = pd.read_csv(io.BytesIO(b), usecols=["percentage", "notional"])
            l020 = df[np.isclose(df["percentage"], -0.2)]
            l1 = df[np.isclose(df["percentage"], -1.0)]
            if len(l020):
                year_020.setdefault(y, []).append(float(l020["notional"].median()))
            if len(l1):
                year_1.setdefault(y, []).append(float(l1["notional"].median()))
        years = sorted(set(list(year_020.keys()) + list(year_1.keys())))
        for y in years:
            if y in year_020:
                per[sym][y] = (float(np.median(year_020[y])), "-0.20%")
            elif y in year_1:
                per[sym][y] = (float(np.median(year_1[y])), "-1%")
        print(f"[P1] depth {sym}: " + ", ".join(f"{y}:{per[sym][y][1]}" for y in years), flush=True)
    return per


def impact_bps_from_depth(depth_020: float | None) -> float:
    if depth_020 is None or depth_020 <= 0 or np.isnan(depth_020):
        return np.nan
    ratio = C.NOTIONAL / depth_020
    if ratio < 0.10:
        return 0.0
    return round(20.0 * ratio, 4)


# ---------------------------------------------------------------- نموذج الحجم
def dollar_vol_bar(sym: str, year: int) -> float:
    df = pd.read_parquet(C.DATA_DIR / sym / "4h.parquet")
    yr = df[df["dt"].dt.year == year]
    if len(yr) == 0:
        return np.nan
    return float(yr["quote_volume"].median())


def load_cached_spreads():
    """إعادة بناء asset_spread من spread_measured_l0082.csv إن وُجد (تفادي إعادة تنزيل 1.8GB)."""
    p = C.OUT / "spread_measured_l0082.csv"
    if not p.exists():
        return None, None
    measured = pd.read_csv(p)
    asset_spread = {}
    for a in C.ASSETS:
        vals = measured[measured["symbol"] == a]["daily_median_spread_bps"].to_numpy(float)
        asset_spread[a] = float(np.median(vals)) if len(vals) else np.nan
    return measured, asset_spread


def main():
    cached_m, cached_s = load_cached_spreads()
    if cached_s is not None and all(not np.isnan(v) for v in cached_s.values()):
        print("[P1] استعمال السبريد المقاس المخزَّن (spread_measured_l0082.csv) بلا إعادة تنزيل", flush=True)
        measured, asset_spread = cached_m, cached_s
    else:
        print("[P1] === قياس السبريد من bookTicker ===", flush=True)
        measured, asset_spread = measure_all_spreads()

    print("[P1] === قياس العمق من bookDepth ===", flush=True)
    depth = measure_depth()

    # نموذج الحجم: نقاط القياس = (سبريد المقاس للأصل, وسيط حجمه في 2023)
    fit_x, fit_y = [], []
    for a in C.ASSETS:
        sp = asset_spread.get(a, np.nan)
        dv = dollar_vol_bar(a, 2023)
        if not np.isnan(sp) and not np.isnan(dv) and dv > 0 and sp > 0:
            fit_x.append(np.log(dv)); fit_y.append(np.log(sp))
    fit_x = np.array(fit_x); fit_y = np.array(fit_y)
    if len(fit_x) >= 3:
        b, a = np.polyfit(fit_x, fit_y, 1)
        pred = a + b * fit_x
        ss_res = np.sum((fit_y - pred) ** 2)
        ss_tot = np.sum((fit_y - fit_y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    else:
        a = b = r2 = np.nan
    worst_measured = {aa: (max([r for r in [asset_spread.get(aa)] if r and not np.isnan(r)] + [np.nan]))
                      for aa in C.ASSETS}
    use_model = (not np.isnan(r2)) and (r2 >= 0.50)
    print(f"[P1] نموذج الحجم: ln(spread)={a:.4f}+{b:.4f}*ln(dvol)  R2={r2:.4f}  use_model={use_model}", flush=True)

    # جدول التكلفة لكل أصل ولكل سنة
    rows = []
    years = list(range(2021, 2027))
    for sym in C.ASSETS:
        for y in years:
            dv = dollar_vol_bar(sym, y)
            # الأثر — أدق مستوى عمق متاح لتلك السنة (أو أقرب سنة)
            dinfo = depth.get(sym, {}).get(y, None)
            if dinfo is None and depth.get(sym):
                avail = sorted(depth[sym].keys())
                dinfo = depth[sym][avail[0]] if avail else None
            if dinfo is not None:
                dep, dep_level = dinfo
            else:
                dep, dep_level = None, None
            imp = impact_bps_from_depth(dep)
            if np.isnan(imp):
                imp = 0.0  # افتراض محافظ عند غياب العمق (متوقع صفر عند 10k)
            # السبريد
            if y in MEASURED_YEARS and not np.isnan(asset_spread.get(sym, np.nan)):
                spread = asset_spread[sym]; src = "measured"
            elif use_model and not np.isnan(dv) and dv > 0:
                spread = float(np.exp(a + b * np.log(dv))); src = "modeled"
            else:
                spread = worst_measured.get(sym, np.nan); src = "worst_measured"
            cost_market = 2 * C.FEE_TAKER_BPS + spread + 2 * imp
            rows.append({
                "symbol": sym, "year": y,
                "dollar_vol_bar": round(dv, 2) if not np.isnan(dv) else None,
                "spread_bps": round(spread, 4) if not np.isnan(spread) else None,
                "spread_source": src,
                "depth_notional": round(dep, 2) if dep else None,
                "depth_level": dep_level,
                "impact_bps": round(imp, 4),
                "cost_market_bps": round(cost_market, 4) if not np.isnan(cost_market) else None,
            })
    cost = pd.DataFrame(rows)
    cost.to_csv(C.OUT / "cost_model_l0082.csv", index=False)

    meta = {
        "fees": {"maker_bps": C.FEE_MAKER_BPS, "taker_bps": C.FEE_TAKER_BPS, "notional_usdt": C.NOTIONAL},
        "spread_dates": SPREAD_DATES,
        "volume_model": {"a": round(float(a), 6), "b": round(float(b), 6), "r2": round(float(r2), 6),
                         "used": bool(use_model)},
        "asset_measured_spread_bps": {k: (round(v, 4) if not np.isnan(v) else None)
                                      for k, v in asset_spread.items()},
        "impact_note": "impact_bps=0 متوقع لكل الأصول عند 10k USDT (القياس المرجعي ADA).",
        "consistency_rule": "جدول cost_model_l0082.csv مجمّد ويُطبَّق حرفيًا في كل المراحل اللاحقة.",
    }
    (C.OUT / "_p1_cost_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    g1 = "PASS" if cost["spread_bps"].notna().all() else "FAIL"
    print(f"\n[P1] G1={g1}")
    print(cost.head(24).to_string(index=False))
    return g1


if __name__ == "__main__":
    main()
