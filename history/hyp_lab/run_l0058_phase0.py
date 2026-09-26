# -*- coding: utf-8 -*-
"""L0058 phase 0 only. Uncounted. A miss stops the round."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

import pandas as pd

ROOT = pathlib.Path("/home/user/l0058")
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

src = (ROOT / "history" / "hyp_lab" / "run_l0056_widen_book.py").read_text(encoding="utf-8")
src = src.replace('pathlib.Path("/home/user/l0056")', 'pathlib.Path("/home/user/l0058")')
src = src.replace('if __name__ == "__main__":', "if False:")
patched = pathlib.Path("/tmp/r56_l0058.py")
patched.write_text(src, encoding="utf-8")
spec = importlib.util.spec_from_file_location("r56_l0058", patched)
R56 = importlib.util.module_from_spec(spec)
sys.modules["r56_l0058"] = R56
spec.loader.exec_module(R56)

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0058"
OUT.mkdir(parents=True, exist_ok=True)
R56.OUT = OUT
R56.DAILY = pathlib.Path.home() / ".cache" / "l0058_daily"
R56.DAILY.mkdir(parents=True, exist_ok=True)


def gate(label, st, net, n):
    print(f"  تحقق {label}: {st['net']}$ / {st['trades']} مرجع {net}$ / {n}", flush=True)
    if abs(st["net"] - net) > 0.5 or st["trades"] != n or st["overlapping_trades"]:
        raise SystemExit(f"الواقع خالف الورقة: {label} = {st}. أوقف.")


def main() -> int:
    can = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
        capture_output=True, text=True,
    )
    raw = can.stdout
    cj = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
    print(f"  كاناري: {cj.get('canary')} net={cj.get('got', {}).get('net')}", flush=True)
    if cj.get("canary") != "ok":
        raise SystemExit("الكاناري ليس ok")
    (OUT / "canary.json").write_text(json.dumps(cj, ensure_ascii=False, indent=2), encoding="utf-8")

    R56.prepare()
    R56.build_regimes(R56.archive_symbols())
    R56.use_syms(R56.archive_symbols())
    enabled, _ = R56.load_frozen_map()

    rec, rows = R56.run_book(
        "مرحلة0 0.130 حكم", "trades_p0_c00130_JUD", R56.routed(enabled),
        R56.WINNER, "2024-01-01", "2026-08-31", "حكم", 0.00130, False, "0",
    )
    gate("0.130% حكم", rec, 30.99, 464)
    rec, rows = R56.run_book(
        "مرحلة0 0.115 حكم", "trades_p0_c00115_JUD", R56.routed(enabled),
        R56.WINNER, "2024-01-01", "2026-08-31", "حكم", 0.00115, False, "0",
    )
    gate("0.115% حكم", rec, 33.24, 464)
    t = pd.DataFrame(rows)
    side = t[t["regime"] == "عرضي"]
    snet = round(float(side["pnl"].sum()), 2) if len(side) else 0.0
    print(f"  عرضي الحكم: {snet}$ / {len(side)} مرجع -12.61$ / 24", flush=True)
    if abs(snet - (-12.61)) > 0.5 or len(side) != 24:
        raise SystemExit(f"عرضي الحكم خالف الورقة: {snet} / {len(side)}")
    rec, _ = R56.run_book(
        "مرحلة0 0.115 اختيار", "trades_p0_c00115_SEL", R56.routed(enabled),
        R56.WINNER, "2021-09-01", "2023-12-31", "اختيار", 0.00115, False, "0",
    )
    gate("0.115% اختيار", rec, 45.66, 328)
    print("  ✅ الأربعة طابقت", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
