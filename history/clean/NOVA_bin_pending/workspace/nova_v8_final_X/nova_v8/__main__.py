"""Command-line entry for NOVA_V8.

Examples:
    python -m nova_v8 selftest          # synthetic end-to-end check
    python -m nova_v8 available         # show which symbols exist in archive
    python -m nova_v8 research          # run the research backtest + report
    python -m nova_v8 status            # resend last saved report to Telegram
"""
from __future__ import annotations

import argparse
import logging
import sys

from . import config as C


def _log():
    logging.basicConfig(
        level=getattr(logging, C.LOG_LEVEL, logging.INFO),
        format="%(levelname)s %(name)s: %(message)s")


def cmd_selftest(_):
    from .tests import selftest
    return selftest.run()


def cmd_available(_):
    from . import feeds
    present, missing = [], []
    for s in C.SYMBOLS:
        if feeds._source_path(s):
            present.append(s)
        else:
            missing.append(s)
    print("أرشيف:", C.ARCHIVE_DIR)
    print("متاح:", ", ".join(present) or "(فارغ)")
    print("ناقص:", ", ".join(missing) or "(كل شيء متوفر)")
    return 0


def _apply_cli_overrides(args):
    """Apply CLI options onto the config module (single source of truth)."""
    if getattr(args, "symbols", None):
        C.SYMBOLS = tuple(s.strip().upper() for s in args.symbols.split(",") if s.strip())
    if getattr(args, "triggers", None):
        C.ENABLE_TRIGGERS = args.triggers
    if getattr(args, "start", None):
        C.START_DATE = args.start
    if getattr(args, "end", None):
        C.END_DATE = args.end
    if getattr(args, "trail_basis", None):
        C.TRAIL_BASIS = args.trail_basis.lower()
    if getattr(args, "experiment", None):
        C.EXPERIMENT_NAME = args.experiment
    if getattr(args, "out", None):
        from pathlib import Path
        d = Path(args.out).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        C.DATA_DIR = d
        C.RESULT_PATH = d / "research_results.csv"
        C.REPORT_PATH = d / "final_report.txt"
        C.STABILITY_PATH = d / "oracle_stability.txt"
        C.FLIP_PATH = d / "slippage_flip_report.txt"
        C.RISK_PATH = d / "portfolio_risk_audit.txt"
        C.QUALITY_PATH = d / "data_quality_report.txt"
        C.LONG_CYCLE_PATH = d / "long_cycle_report.txt"
        C.MARKET_OPEN_PATH = d / "market_open_report.txt"
        C.STRATEGY_SUMMARY_PATH = d / "strategy_sleeve_summary.txt"
    from .execution import clear_profile_cache
    clear_profile_cache()


def cmd_doctor(_):
    """Print an environment / configuration summary (no data needed)."""
    import sys
    from . import feeds
    from .execution import GOOD_PROFIT_THRESHOLD, exit_profile

    def _have(mod):
        try:
            __import__(mod)
            return "OK"
        except Exception:
            return "MISSING"

    print("== NOVA_V8 — ملخص بيئة التشغيل / Environment ==")
    print(f"python            : {sys.version.split()[0]}")
    for m in ("numpy", "pandas", "pyarrow", "aiohttp", "aiosqlite", "websockets"):
        print(f"{m:<18}: {_have(m)}")
    print(f"MODE              : {C.MODE}   (live not implemented)")
    print(f"TF_TRADE          : {C.TF_TRADE}   REGIME_TF: {C.REGIME_TF}"
          f"   candidates: {','.join(C.TF_REGIME_CANDIDATES)}")
    print(f"ARCHIVE_DIR       : {C.ARCHIVE_DIR}")
    print(f"DATA_DIR          : {C.DATA_DIR}")
    print(f"COMMISSION/SIDE   : {C.COMMISSION_PCT*100:.3f}%   "
          f"SLIPPAGE base: {C.SLIPPAGE_PCT*100:.3f}%  tiers: "
          + ", ".join(f"{t*100:.2f}%" for t in C.SLIPPAGE_TIERS))
    print(f"EXECUTION_COST    : effective proxy   market entry: {C.MARKET_COST_ON_ENTRY}")
    print(f"COST_MULTIPLIERS   : x{C.SPREAD_HIGHVOL_MULT} high-vol, "
          f"x{C.SPREAD_SHOCK_MULT} shock; Grid limit fills: commission-only")
    print(f"RISK_MODE          : {C.PORTFOLIO_RISK_MODE}   capital: {C.PORTFOLIO_CAPITAL_USD:.2f}$ "
          f"gross cap: {C.RISK_MAX_GROSS_EXPOSURE_PCT*100:.1f}% "
          f"symbol cap: {C.RISK_MAX_SYMBOL_EXPOSURE_PCT*100:.1f}%")
    print(f"DATA_QUALITY       : {C.DATA_QUALITY_MODE}   max gap: {C.DATA_MAX_GAP_MINUTES} min")
    print(f"SLEEVES            : long_cycle={C.LONG_CYCLE_ENABLED} "
          f"market_open={C.MARKET_OPEN_ENABLED} (explicit research selection recommended)")
    print(f"GOOD_PROFIT thresh: {GOOD_PROFIT_THRESHOLD*100:.3f}%")
    no = [S for S in C.SYMBOLS if not feeds._source_path(S)]
    yes = [S for S in C.SYMBOLS if feeds._source_path(S)]
    print(f"archive available : {len(yes)}/{len(C.SYMBOLS)} symbols"
          + (f"   missing: {','.join(no)}" if no else ""))
    print("exit profile (bull  defaults + overrides):")
    prof = exit_profile(C.REGIME_BULL)
    print("   " + "  ".join(f"{k}={v}" for k, v in list(prof.items())[:8]))
    return 0


def cmd_research(args):
    from . import engine, telegram_notify
    _apply_cli_overrides(args)

    milestones = list(C.PROGRESS_MILESTONES)
    reached = set()

    def on_progress(frac: float):
        pct = int(frac * 100)
        for m in milestones:
            if pct >= m and m not in reached:
                reached.add(m)
                log = logging.getLogger("nova")
                log.info("progress %d%%", pct)
                telegram_notify.send(telegram_notify.milestone_message(pct))
        if pct >= 100 and 100 not in reached:
            reached.add(100)
            telegram_notify.send(telegram_notify.milestone_message(100))

    log = logging.getLogger("nova.research")
    log.info("بدء البحث...")
    result = engine.run_research(on_progress=on_progress, strategies=args.strategies)
    print(engine.render_report(result))
    # send the single final report
    telegram_notify.send(telegram_notify.status_message(result))
    log.info("انتهى البحث -> %s", C.RESULT_PATH)
    return 0


def cmd_status(_):
    from .engine import build_result, render_report
    import pandas as pd
    from . import telegram_notify
    # (build_result / render_report imported above are used here)
    if not C.RESULT_PATH.exists():
        print("لا توجد نتائج محفوظة بعد.")
        return 1
    frame = pd.read_csv(C.RESULT_PATH)
    recs = frame.to_dict("records")
    if C.PORTFOLIO_RISK_MODE == "strict":
        recs = [r for r in recs
                if str(r.get("risk_accepted", "True")).lower()
                in {"true", "1", "yes"}]
    # rebuild minimal result object for rendering
    result = build_result(recs)
    print(render_report(result))
    telegram_notify.send(telegram_notify.status_message(result))
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="nova_v8", description="NOVA_V8 research bot")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest", help="synthetic end-to-end self-check")
    sub.add_parser("available", help="list symbols present in archive")
    sub.add_parser("doctor", help="environment + configuration summary")
    r = sub.add_parser("research", help="run research backtest")
    r.add_argument("--symbols", help="comma list, e.g. BTCUSDT,SOLUSDT")
    r.add_argument("--triggers", help="'all' or comma list, e.g. RSI,EMA")
    r.add_argument("--start", help="start date YYYY-MM-DD")
    r.add_argument("--end", help="end date YYYY-MM-DD")
    r.add_argument("--trail-basis", choices=["atr", "fib"], dest="trail_basis",
                   help="trailing basis (default from config)")
    r.add_argument("--experiment", help="experiment name recorded in the CSV")
    r.add_argument("--out", help="output directory (default ~/nova_v8_out)")
    r.add_argument("--strategies", default=None,
                   help="core, all, or comma list: long_cycle,market_open,...")
    sub.add_parser("status", help="resend last report")
    return p


def main(argv=None):
    _log()
    args = build_parser().parse_args(argv)
    handler = {
        "selftest": cmd_selftest,
        "available": cmd_available,
        "doctor": cmd_doctor,
        "research": cmd_research,
        "status": cmd_status,
    }[args.cmd]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
