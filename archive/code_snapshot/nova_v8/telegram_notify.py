"""Module — Telegram notifications for the research phase.

During a research run the bot only sends:
  * milestone progress notes (10/25/50/75/90/100 %)
  * a single final "تقرير الحالة" (Report Status) when the run finishes.

The final report is split into the three approved sections: General 📊, Grid 🟦,
BTC-followers 🟧. If Telegram is not configured the module silently logs instead
(never crashes the research run).
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from . import config as C
from .engine import render_report

log = logging.getLogger("nova.telegram")

API = "https://api.telegram.org/bot{token}/sendMessage"


def enabled() -> bool:
    return bool(C.TELEGRAM_TOKEN and C.TELEGRAM_CHAT_ID)


def send(text: str) -> bool:
    if not enabled():
        log.debug("telegram not configured — skip send")
        return False
    token=__REDACTED__
    chat = C.TELEGRAM_CHAT_ID
    payload = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(API.format(token=token), data=payload)
    try:
        with urllib.request.urlopen(req, timeout=C.TG_POLL_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        ok = bool(body.get("ok"))
        if not ok:
            log.warning("telegram send not ok: %s", body.get("description"))
        return ok
    except Exception as exc:                       # never break research on tg
        log.warning("telegram send failed: %s", exc)
        return False


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def milestone_message(pct: int, result_counts=None) -> str:
    lines = [f"⏳ NOVA_V8 — البحث قيد التنفيذ: <b>{pct}%</b>"]
    if result_counts:
        parts = ", ".join(f"{k}: {v}" for k, v in result_counts.items())
        lines.append(f"اكتمل حتى الآن: {parts}")
    return "\n".join(lines)


def status_message(result: dict) -> str:
    """The single full 'تقرير الحالة' message with the 3 approved sections."""
    return render_report(result)


def report_lines(result: dict) -> list[str]:
    """Compact 3-line telegram summary (used when a short message is wanted)."""
    d = result["directional"]
    g = result["grid"]
    b = result["btc"]
    return [
        f"📊 التقرير العام: 🟢 {d['win_pct']:.1f}% رابح · 🟥 {d['lose_pct']:.1f}% "
        f"خاسر · 💵 إجمالي المكاسب {d['pnl_usd']:.2f}$ · ✅ نسبة النجاح {d['win_pct']:.1f}%",
        f"🟦 الشبكة: عدد الشبكات المغلقة {g['total']} · نجحت {g['win_pct']:.1f}% · "
        f"صافي {g['pnl_usd']:.2f}$",
        f"🟧 تابعو البيتكوين: عدد الصفقات {b['total']} · نجحت {b['win_pct']:.1f}% · "
        f"صافي {b['pnl_usd']:.2f}$",
    ]
