# -*- coding: utf-8 -*-
"""L0012 — مسح تغطية البيانات للرموز غير الممتحنة (تشخيصي، لا ينتج أرقاماً معتمدة).

يقرأ الباركيه كاملاً بالبثّ ويطبع: أول/آخر شمعة، عدّ شموع 4h، وعدد شموع التدريب
(2023-09-01→2024-12-31) والاختبار (2025-01-01→2026-08-31) والنافذة العمياء
(2021-09-01→2023-08-31) — ليكون القبول/الاستبعاد بدليل مقاس لا بافتراض.
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_breakers as RB  # noqa: E402

REF = "b27052e87d9c810ce401c4f64ec359944b164eaf"
SYMS = ["HNTUSDT", "IMXUSDT", "PEPEUSDT", "SHIBUSDT", "TONUSDT", "VETUSDT"]
T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731


def main() -> int:
    print("symbol,first_1m,last_1m,bars_4h,train_bars,test_bars,blind_bars,sha,bytes", flush=True)
    for s in SYMS:
        try:
            df, sha, nbytes = RB.stream_symbol(s, REF)
            b4 = RB.to_bars(df, RB.TF_MINUTES["4h"])
            ix = b4.index
            tr = int(((ix >= T(RB.TRAIN_START)) & (ix <= T(RB.TRAIN_END + " 23:59:59"))).sum())
            te = int(((ix >= T(RB.TEST_START)) & (ix <= T(RB.TEST_END + " 23:59:59"))).sum())
            bl = int(((ix >= T("2021-09-01")) & (ix <= T("2023-08-31 23:59:59"))).sum())
            print(f"{s},{df.index[0]},{df.index[-1]},{len(b4)},{tr},{te},{bl},{sha},{nbytes}",
                  flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"{s},ERROR,{type(e).__name__}:{e}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
