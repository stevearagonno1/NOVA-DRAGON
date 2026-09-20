#!/usr/bin/env python3
"""NOVA_V8 — Canary: بوابة سلامة البيانات لكل تجربة (لا تشغيل طويل قبل اجتيازها).

يشغّل المحرك نفسه (بدون أي تعديل) على التركيبة الموثقة النتيجة مسبقاً، ويقارن
بالأرقام المرجعية. أي انحراف = البيئة/البيانات غير صحيحة ⇒ أوقف التجربة فوراً.

    التركيبة: AT_TRAIL=3.0 AT_STOP=0.5 AT_PB=288 AT_TRIG=6 V3A=0 V3B=0 V3C=0
    النافذة:  تدريب 2023-09 → 2024-12
    المرجع الشرعي (§27 — 20$/صفقة): net = -1.9718063239874646 | trades = 68 | win_pct = 19.11764705882353
    الأثر التاريخي على مسطرة 1000$/صفقة (ملغاة): net = -98.59031619937323  (= الشرعي × 50)

الاستخدام:
    python3 tools/canary.py                     # من القرص (crypto_archive/ في المستودع)
    python3 tools/canary.py --source stream     # بثّ من raw.githubusercontent إلى RAM (صفر قرص)
    python3 tools/canary.py --json              # مخرج آلي يُلصق في HANDOFF المسار

ملاحظات:
  • لا يكتب شيئاً داخل nova_v8/ ولا داخل repo/git: كاش المصفوفة يذهب إلى مجلد عمل
    مؤقت (--scratch، افتراضياً ~/.nova_scratch) حتى لا يتسلل ملف >100MB إلى git.
  • يطبع الإصدارات (python/pandas/numpy/pyarrow) لأن المرجع مُثبَّت على
    pandas 2.2.3 / numpy 2.3.5؛ انظر DECISIONS.md.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys

# Constitution §27 (2026-09-20): trade = 20$. Old REF net=-98.59031619937323 was at 1000$/trade.
REF = {"net": -1.9718063239874646, "trades": 68, "win_pct": 19.11764705882353}
REF_LEGACY_1000 = {"net": -98.59031619937323, "trades": 68, "win_pct": 19.11764705882353}
COMBO = {"NOVA_AT_TRAIL": "3.0", "NOVA_AT_STOP": "0.5", "NOVA_AT_PB": "288",
         "NOVA_AT_TRIG": "6", "NOVA_AT_V3A": "0", "NOVA_AT_V3B": "0", "NOVA_AT_V3C": "0"}
REPO = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["disk", "stream"], default="disk")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--ref", default="main", help="git ref المستخدم في البث")
    ap.add_argument("--scratch", default=os.path.expanduser("~/.nova_scratch"),
                    help="مجلد عمل خارج git لكاش المصفوفة")
    ap.add_argument("--tol", type=float, default=1e-9, help="تسامح مقارنة net")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    def say(*a):
        if not args.json:
            print(*a, flush=True)

    say("═" * 66)
    say(" NOVA_V8 CANARY — بوابة سلامة البيانات")
    say("═" * 66)

    # 1) environment fingerprint (reproducibility contract)
    import importlib
    ver = {}
    for m in ("pandas", "numpy", "pyarrow"):
        try:
            ver[m] = importlib.import_module(m).__version__
        except Exception as e:                                    # noqa: BLE001
            ver[m] = f"MISSING ({type(e).__name__})"
    ver["python"] = sys.version.split()[0]
    say("  البيئة:", " | ".join(f"{k}={v}" for k, v in ver.items()))

    scratch = pathlib.Path(args.scratch).expanduser()
    scratch.mkdir(parents=True, exist_ok=True)
    archive = scratch / "archive"
    archive.mkdir(exist_ok=True)
    parquet = archive / f"{args.symbol}_1m.parquet"

    # 2) data — from repo on disk, or streamed into RAM (zero bytes on disk)
    if args.source == "disk":
        src = REPO / "crypto_archive" / f"{args.symbol}_1m.parquet"
        if not src.exists():
            src = pathlib.Path(os.environ.get("NOVA_ARCHIVE", "")).expanduser() / f"{args.symbol}_1m.parquet"
        if not src.exists():
            print(f"❌ لا يوجد {args.symbol}_1m.parquet (جرّب: git lfs pull أو --source stream)", file=sys.stderr)
            return 2
        if not parquet.exists() or parquet.stat().st_size != src.stat().st_size:
            say(f"  تجهيز البيانات من {src} …")
            try:
                os.link(src, parquet)                              # hardlink: صفر نسخة
            except (OSError, AttributeError):        # AttributeError: os.link غير موجود على تيرمكس/أندرويد
                shutil.copy2(src, parquet)
        os.environ["NOVA_ARCHIVE"] = str(archive)
    else:
        import io
        import urllib.request
        url = (f"https://raw.githubusercontent.com/stevearagonno1/NOVA-DRAGON/"
               f"{args.ref}/crypto_archive/{args.symbol}_1m.parquet")
        say(f"  بثّ {url} …")
        buf = io.BytesIO(urllib.request.urlopen(url, timeout=180).read())
        say(f"  وصل {buf.getbuffer().nbytes/1e6:.1f}MB إلى RAM — صفر بايت على القرص")
        import pandas as _pd
        import pyarrow.parquet as _pq
        df = _pq.ParquetFile(buf).read().to_pandas()
        df.to_parquet(parquet)
        os.environ["NOVA_ARCHIVE"] = str(archive)

    # 3) engine, unmodified — combo env must be set BEFORE importing config
    os.environ.update(COMBO)
    sys.path.insert(0, str(REPO))
    import pandas as pd
    from nova_v8 import config as C
    from nova_v8 import feeds
    from nova_v8.sweep_engine import _month_bounds

    C.START_DATE, _ = _month_bounds("2023-09")
    _, C.END_DATE = _month_bounds("2024-12")
    say("  النافذة:", f"{C.START_DATE} → {C.END_DATE}")

    m = feeds.load_matrix(args.symbol)
    if m is None:
        print("❌ تعذّر بناء مصفوفة البيانات (تأكد من NOVA_ARCHIVE/الملف)", file=sys.stderr)
        return 2
    from nova_v8 import adaptive_trend
    recs = adaptive_trend.replay_adaptive_trend(m)
    net = sum(r.get("pnl_usd", 0.0) for r in recs)
    wins = sum(1 for r in recs if r.get("pnl_usd", 0) > 0)
    got = {"net": net, "trades": len(recs),
           "win_pct": 100 * wins / len(recs) if recs else 0.0}
    ok = abs(got["net"] - REF["net"]) <= max(args.tol, abs(REF["net"]) * 1e-9) and got["trades"] == REF["trades"]

    say("  الناتج:", f"net={got['net']!r} trades={got['trades']} win_pct={got['win_pct']!r}")
    say("  المرجع:", f"net={REF['net']!r} trades={REF['trades']} win_pct={REF['win_pct']!r}")
    say(f"  |Δnet| = {abs(got['net']-REF['net']):.3e}")
    say("  الحكم:", "✅ PASS — البيئة والبيانات والمحرك تتطابق مع المرجع الموثق"
        if ok else "❌ FAIL — لا تُشغِّل التجربة: راجع وحدة الطوابع الزمنية/الإصدارات/الملف")
    say("  مجلد العمل المؤقت:", f"{scratch} (خارج git — احذفه متى شئت)")
    say("═" * 66)

    if args.json:
        print(json.dumps({"canary": "ok" if ok else "fail", "source": args.source,
                          "got": got, "expected": REF, "versions": ver},
                         ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
