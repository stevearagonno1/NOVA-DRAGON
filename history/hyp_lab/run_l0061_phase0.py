# -*- coding: utf-8 -*-
"""L0061 — المرحلة 0 (لا تُحسب من السقف): كاناري المحرك الحي + إعادة إنتاج أرقام المحفظة
كما فعلت L0060 حرفيًّا، قبل أي رقم جديد.

المرجع (ورقة L0061 / تقرير L0060):
  المحفظة · 0.115% · حكم    = +33.24$ / 464
  المحفظة · 0.115% · اختيار = +45.66$ / 328   (تحقق إضافي من L0060)
  الاحتفاظ L0046 · حكم      = −73.29$ / 15 عملة · 20$ · 0.13%
فرق أكبر من 0.5$ ⇒ SystemExit. لا رقم جديد قبل هذا.

ROOT: `run_l0056_widen_book.py` مكتوب فيه `/home/user/l0056`. يُستبدل في الذاكرة إلى
`/home/user/work` (نسخة العمل هنا) ويُسجَّل ذلك. `run_l0046_basis_repair.py` و
`run_l0048_entry_value.py` مكتوب فيهما `/home/user/work` أصلًا فلم يحتاجا استبدالًا.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/user/work")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "history" / "hyp_lab"))
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("NOVA_SCRATCH", "/home/user/.nova_scratch")
os.environ.setdefault("NOVA_HOME", "/home/user/.nova_scratch/home")

OUT = ROOT / "history" / "research" / "hyp_lab_out" / "L0061"
OUT.mkdir(parents=True, exist_ok=True)

DEC_S, DEC_E = "2021-09-01", "2023-12-31"
JUD_S, JUD_E = "2024-01-01", "2026-08-31"
COST = 0.00115
BASE_COINS = (
    "ATOMUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "FILUSDT", "GRAMUSDT",
    "IMXUSDT", "LINKUSDT", "PEPEUSDT", "RENDERUSDT", "SHIBUSDT", "SOLUSDT",
    "TONUSDT", "VETUSDT", "XLMUSDT",
)


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_l56():
    src_path = ROOT / "history" / "hyp_lab" / "run_l0056_widen_book.py"
    src = src_path.read_text(encoding="utf-8")
    assert 'pathlib.Path("/home/user/l0056")' in src, "ROOT المكتوب في run_l0056 تغيّر — راجع"
    src = src.replace('pathlib.Path("/home/user/l0056")', 'pathlib.Path("/home/user/work")')
    src = src.replace('if __name__ == "__main__":', "if False:")
    path = pathlib.Path("/tmp/r56_l0061.py")
    path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("r56_l0061", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["r56_l0061"] = mod
    spec.loader.exec_module(mod)
    mod.OUT = OUT
    return mod


def main() -> int:
    print("══ مرحلة 0 — كاناري المحرك الحي ══", flush=True)
    can = subprocess.run([sys.executable, str(ROOT / "tools" / "canary.py"), "--json"],
                         capture_output=True, text=True)
    raw = can.stdout
    cj = json.loads(raw[raw.index("{"):]) if "{" in raw else {"stderr": can.stderr[-2000:]}
    dump("canary.json", cj)
    print(f"  كاناري: {cj.get('canary')} net={cj.get('got', {}).get('net')}", flush=True)
    if cj.get("canary") != "ok":
        raise SystemExit("الكاناري ليس ok — أوقف")

    print("══ مرحلة 0 — حرّاس selftest ══", flush=True)
    for tool in ("fill_invariant_check.py", "position_sequencing_audit.py"):
        st = subprocess.run([sys.executable, str(ROOT / "tools" / tool), "--selftest"],
                            capture_output=True, text=True)
        tail = (st.stdout or st.stderr).strip().splitlines()
        print(f"  {tool}: {(tail[-1] if tail else 'بلا مخرج')} (exit={st.returncode})", flush=True)
        if st.returncode != 0:
            raise SystemExit(f"{tool} selftest فشل")

    print("══ مرحلة 0 — المحفظة (7 أعمدة · حكم · 0.115%) ══", flush=True)
    R56 = load_l56()
    R56.prepare()
    R56.build_regimes(R56.archive_symbols())
    R56.use_syms(R56.archive_symbols())
    enabled, _ = R56.load_frozen_map()
    fp = hashlib.sha256((ROOT / "history/research/hyp_lab_out/L0051/routing_map.json").read_bytes()).hexdigest()
    if not fp.startswith("14df873e"):
        raise SystemExit(f"بصمة الخريطة خالفت: {fp[:16]}")
    rec_j, _ = R56.run_book("p0_c00115_JUD", "p0_c00115_JUD", R56.routed(enabled), R56.WINNER,
                            JUD_S, JUD_E, "حكم", COST, False, "0")
    print(f"  حكم المحفظة: {rec_j['net']} / {rec_j['trades']} · المرجع +33.24 / 464", flush=True)
    if abs(rec_j["net"] - 33.24) > 0.5 or rec_j["trades"] != 464:
        raise SystemExit(f"حكم المحفظة خالف الورقة: {rec_j['net']} / {rec_j['trades']}")
    rec_s, _ = R56.run_book("p0_c00115_SEL", "p0_c00115_SEL", R56.routed(enabled), R56.WINNER,
                            DEC_S, DEC_E, "اختيار", COST, False, "0")
    print(f"  اختيار المحفظة: {rec_s['net']} / {rec_s['trades']} · المرجع +45.66 / 328", flush=True)
    if abs(rec_s["net"] - 45.66) > 0.5 or rec_s["trades"] != 328:
        raise SystemExit(f"اختيار المحفظة خالف الورقة: {rec_s['net']} / {rec_s['trades']}")

    # الشراء والاحتفاظ كما قيس في L0046/L0060: 20$ · 0.13% · 15 عملة · أول افتتاح وآخر إغلاق
    tot, n = 0.0, 0
    for sym in BASE_COINS:
        w = R56.R46.frames(sym)
        w = w[(w.index >= JUD_S) & (w.index <= JUD_E)]
        if len(w) < 2:
            continue
        e = float(w["open"].iloc[0]) * (1 + 0.0013)
        x = float(w["close"].iloc[-1]) * (1 - 0.0013)
        tot += 20.0 * (x / e - 1.0)
        n += 1
    tot = round(tot, 2)
    print(f"  احتفاظ L0046 · حكم: {tot} / {n} عملة · المرجع −73.29", flush=True)
    if abs(tot - (-73.29)) > 0.5:
        raise SystemExit(f"الاحتفاظ خالف الورقة: {tot}")

    # حارس التعبئة على ملفي المحفظة (كلفة الملف 0.115%)
    for name in ("p0_c00115_JUD", "p0_c00115_SEL"):
        st = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "fill_invariant_check.py"),
             "--trades", str(OUT / f"trades_{name}.csv"),
             "--frames", str(pathlib.Path.home() / ".cache" / "l0046_frames"), "--cost", str(COST)],
            capture_output=True, text=True)
        line = [l for l in st.stdout.splitlines() if "مخالفات" in l]
        print("  حارس:", line[0].strip() if line else st.stdout[-300:], flush=True)
        if st.returncode != 0:
            raise SystemExit(f"حارس التعبئة فشل على {name}")

    dump("phase0_portfolio.json", {
        "canary": cj.get("canary"), "canary_net": cj.get("got", {}).get("net"),
        "portfolio_JUD": {"net": rec_j["net"], "trades": rec_j["trades"], "ref": "33.24/464"},
        "portfolio_SEL": {"net": rec_s["net"], "trades": rec_s["trades"], "ref": "45.66/328"},
        "buyhold_L0046_JUD": {"net": tot, "n": n, "ref": -73.29},
        "root_note": "run_l0056: /home/user/l0056 → /home/user/work في الذاكرة. R46/R48 فيهما /home/user/work أصلًا.",
        "frames_cache": str(pathlib.Path.home() / ".cache" / "l0046_frames"),
    })
    print("  ✅ المرحلة 0 (المحفظة) طابقت", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
