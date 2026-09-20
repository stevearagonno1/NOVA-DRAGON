# -*- coding: utf-8 -*-
"""L0012 — الشراء والاحتفاظ على نافذتي التدريب والاختبار لكل رمز غير ممتحن (شرط القسم 23).

الطريقة: شراء عند إغلاق أول شمعة 4h من النافذة وبيع عند إغلاق آخر شمعة، بقيمة اسمية
20$ ونفس كلفة الطرفين 0.13% (الدستور القسم 23: العمولات والانزلاق داخل كل رقم).
المخرجات: buyhold_compare.csv بجوار نتائج L0012 — كل رقم قابل لإعادة الاشتقاق بهذا الأمر.
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_breakers as RB  # noqa: E402

REF = "b27052e87d9c810ce401c4f64ec359944b164eaf"
SYMS = ["ATOMUSDT", "BNBUSDT", "DOGEUSDT", "IMXUSDT", "PEPEUSDT", "SHIBUSDT", "TONUSDT", "VETUSDT"]
OUT = HERE.parent / "research" / "hyp_lab_out" / "L0012"
NOTIONAL, COST = 20.0, 0.0013  # §27
T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731


def hold_net(bars: pd.DataFrame, a: str, b: str) -> tuple[float, str, str]:
    w = bars[(bars.index >= T(a)) & (bars.index <= T(b + " 23:59:59"))]
    if len(w) < 2:
        return float("nan"), "", ""
    entry, exit_ = float(w["close"].iloc[0]), float(w["close"].iloc[-1])
    net = NOTIONAL * (exit_ / entry - 1) - NOTIONAL * COST * 2
    return round(net, 4), str(w.index[0]), str(w.index[-1])


def main() -> int:
    rows = []
    for s in SYMS:
        df, sha, _ = RB.stream_symbol(s, REF)
        b4 = RB.to_bars(df, RB.TF_MINUTES["4h"])
        tr_net, tr_a, tr_b = hold_net(b4, RB.TRAIN_START, RB.TRAIN_END)
        te_net, te_a, te_b = hold_net(b4, RB.TEST_START, RB.TEST_END)
        rows.append({"symbol": s, "train_hold_net": tr_net, "test_hold_net": te_net,
                     "test_first_bar": te_a, "test_last_bar": te_b, "sha16": sha})
        print(f"{s}: hold_train={tr_net:.2f}$ hold_test={te_net:.2f}$ ({te_a} → {te_b})",
              flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "buyhold_compare.csv", index=False, encoding="utf-8-sig")
    print(f"\nالمجموع (8 عملات): تدريب {out['train_hold_net'].sum():.2f}$ | "
          f"اختبار {out['test_hold_net'].sum():.2f}$")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
