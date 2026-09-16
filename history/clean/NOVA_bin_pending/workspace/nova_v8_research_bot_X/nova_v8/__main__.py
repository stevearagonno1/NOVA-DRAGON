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


def cmd_research(args):
    from . import engine, telegram_notify

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
    result = engine.run_research(on_progress=on_progress)
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
    sub.add_parser("research", help="run research backtest")
    sub.add_parser("status", help="resend last report")
    return p


def main(argv=None):
    _log()
    args = build_parser().parse_args(argv)
    handler = {
        "selftest": cmd_selftest,
        "available": cmd_available,
        "research": cmd_research,
        "status": cmd_status,
    }[args.cmd]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
