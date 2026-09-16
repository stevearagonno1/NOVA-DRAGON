"""
NOVA v5 — Interactive Async Telegram (M6 — Forward-Profiling Refactor)
=======================================================================

HFT-safety guarantees (this module can never slow the trading bot down):
• ONE shared aiohttp ClientSession; every network operation is async.
• All outbound messages are pushed into a BOUNDED asyncio.Queue drained by a
  dedicated sender task → the entry/exit hot paths never wait for Telegram
  RTT. If the queue is full the message is dropped + logged instead of
  stalling the engine.
• A single long-polling /getUpdates loop runs as its own task (launched with
  asyncio.create_task() from engine.run()) and handles commands + inline
  buttons, hardened with exponential backoff and clean cancellation.

Interactive features (updated for the ⚗️ FORWARD-PROFILING phase):
• Boot message "🚀 NOVA HFT Engine Active" with an inline menu:
      [ 📊 Status | 📂 Open Positions | ⏸️ Pause/Resume ]
      [ 📋 Trade Log | 📥 Download Full Log (.txt) ]
      [ 🏠 Menu ]
• 📋 Trade Log — now a detailed per-trade anatomy view (Trade Type, Symbol,
  Entry/Exit prices, Trigger Source, EXACT NB Score, Final PnL) paginated at
  5–7 trades per message with Next ➡️ / ⬅️ Previous inline buttons, and a hard
  character guard so a page can never exceed Telegram's 4096-char limit.
• 📥 Download Full Log (.txt) — NEW: the engine compiles the exhaustive
  historical journal (every executed + closed trade with its full anatomy)
  into a formatted .txt and uploads it via sendDocument (multipart).
• Entry / exit alerts now carry: trade #id, side (LONG/SHORT), trigger source,
  exact NB score (3 decimals) and the zero-threshold note.
• /start, /menu, /help → re-send the menu.
• /status /positions /pause /resume /log [page] /export → text aliases.
• Callback queries are answered instantly (no endless spinner on the client).
• Only the configured CHAT_ID is authorized to interact (anti-abuse).
"""

from __future__ import annotations
import asyncio
import html
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

HTML = "HTML"

# ── Callback data tokens (must stay short & stable) ──────────────────────
CB_STATUS = "menu:status"
CB_POSITIONS = "menu:positions"
CB_PAUSE = "menu:pause"
CB_LOG = "menu:log"            # payload: f"{CB_LOG}:{page}"
CB_EXPORT = "menu:export_txt"  # 📥 compile + upload the full .txt journal
CB_MENU = "menu:home"
CB_NOOP = "noop"

# Telegram hard limit is 4096; we cap a little lower (buttons/caption room).
TG_TEXT_SAFE_LIMIT = 4000

# Trade-Log pagination: STRICTLY 5–7 trades per message (user spec) —
# clamped here even if Config.log_page_size is out of range.
LOG_PAGE_MIN = 5
LOG_PAGE_MAX = 7
LOG_PAGE_DEFAULT = 6


def esc(value) -> str:
    return html.escape(str(value))


def fnum(v, default: float = 0.0) -> float:
    """Safe numeric coercion — corrupt/hand-edited journal rows render as
    defaults instead of crashing the log view."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if f == f else default


def coin(sym: str) -> str:
    return str(sym).replace("USDT", "")


# ── Small formatting helpers shared by log / entry / exit / journal ──────
def fmt_px(v, dash: str = "—") -> str:
    """Price/quantity formatter that tolerates missing + zero (blocked rows)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return dash
    return f"{f:g}" if f > 0 else dash


def fmt_score_pct(v, dash: str = "n/a") -> str:
    """Exact NB score on a 0–100 scale, 3 decimals (profiling-grade)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return dash
    return f"{f * 100.0:.3f}%"


def fmt_dur(sec) -> str:
    try:
        s = max(0, int(float(sec)))
    except (TypeError, ValueError):
        return "—"
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


class TelegramBot:
    """Fully async, non-blocking Telegram client + interactive menu."""

    def __init__(self, token: str, chat_id: str, cfg):
        self.token = str(token or "")
        self.chat_id = str(chat_id or "")
        self.cfg = cfg
        self.session: Optional[aiohttp.ClientSession] = None
        self._base = "https://api.telegram.org"
        # Normal API calls: short timeout. Long-poll: must exceed Telegram's
        # own `timeout=50` so the socket isn't cut before the server answers.
        self._timeout = aiohttp.ClientTimeout(total=25, sock_connect=10)
        # Documents can be bigger (journal .txt) — allow a slightly longer budget.
        self._doc_timeout = aiohttp.ClientTimeout(total=45, sock_connect=10)
        self._poll_timeout = aiohttp.ClientTimeout(total=60, sock_connect=10)
        self._send_lock = asyncio.Lock()          # serialize outbound API calls
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=250)
        self._sender_task: Optional[asyncio.Task] = None
        self._running = False
        self._offset = 0

    # ════════════════════════════════════════════════════════════════
    # Lifecycle
    # ════════════════════════════════════════════════════════════════
    async def start(self):
        self._running = True
        self.session = aiohttp.ClientSession()
        # Boot diagnostic: this is the #1 reason a bot is "silent" — bad token.
        me = await self._api("getMe", timeout=aiohttp.ClientTimeout(total=10, sock_connect=10))
        if isinstance(me, dict) and me.get("ok"):
            print(f"[telegram] ✅ connected as @{me['result'].get('username', '?')}")
        else:
            desc = (me or {}).get("description", "no response") if isinstance(me, dict) else "no response"
            print(f"[telegram] ⚠️ getMe failed ({desc}) — "
                  f"check TELEGRAM_TOKEN in .env; the bot will stay silent until fixed.")
        self._sender_task = asyncio.create_task(self._sender_loop(), name="tg-sender")

    async def close(self):
        self._running = False
        # Give the queued messages (incl. the shutdown note) a chance to flush.
        try:
            await asyncio.wait_for(self._queue.join(), timeout=5.0)
        except asyncio.TimeoutError:
            pass
        if self._sender_task:
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        if self.session and not self.session.closed:
            await self.session.close()

    # ════════════════════════════════════════════════════════════════
    # Low-level API helpers
    # ════════════════════════════════════════════════════════════════
    async def _api(self, method: str, payload: Optional[Dict] = None,
                   timeout: Optional[aiohttp.ClientTimeout] = None) -> Optional[Dict]:
        """POST {method}. Returns parsed JSON or None. Never raises outward."""
        if not self.session or self.session.closed:
            return None
        url = f"{self._base}/bot{self.token}/{method}"
        try:
            async with self._send_lock:
                async with self.session.post(url, json=payload,
                                             timeout=timeout or self._timeout) as resp:
                    try:
                        return await resp.json(content_type=None)
                    except Exception:
                        raw = await resp.text()
                        print(f"[telegram] {method} non-JSON HTTP {resp.status}: {raw[:160]}")
                        return None
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[telegram] {method} network error: {exc}")
            return None

    # ════════════════════════════════════════════════════════════════
    # Outbound queue — producers NEVER wait on the network
    # ════════════════════════════════════════════════════════════════
    async def send_async(self, text: str, buttons: Optional[List[List[Dict]]] = None,
                         chat_id: Optional[str] = None):
        """Queue a message. Non-blocking by construction: if the bounded queue
        is full (Telegram down for a while) we drop + log instead of stalling
        the trading pipeline."""
        item = {"kind": "send", "chat_id": chat_id or self.chat_id,
                "text": text, "buttons": buttons}
        try:
            self._queue.put_nowait(item)
        except asyncio.QueueFull:
            print("[telegram] ⚠️ send queue full — message dropped (engine kept unblocked)")

    async def edit_async(self, chat_id: str, message_id: int, text: str,
                         buttons: Optional[List[List[Dict]]] = None) -> bool:
        """In-place edit (used by the Pause/Resume toggle). Direct call — it is
        user-triggered and rare, and the caller wants to know the outcome."""
        data = {"chat_id": chat_id, "message_id": message_id, "text": text,
                "parse_mode": HTML, "disable_web_page_preview": True}
        if buttons:
            data["reply_markup"] = {"inline_keyboard": buttons}
        body = await self._api("editMessageText", data)
        return bool(isinstance(body, dict) and body.get("ok"))

    async def send_document(self, filename: str, content: str, caption: str = "") -> bool:
        """📥 Upload a text document via sendDocument (multipart/form-data).

        Used by the Forward-Profiling journal export. This is a DIRECT call
        (not queued) — like edit_async it is user-triggered and rare, and the
        caller needs the success/failure answer to message the user back.
        Returns True on accepted upload. Never raises outward."""
        if not self.session or self.session.closed:
            print("[telegram] ⚠️ sendDocument skipped — session not open")
            return False
        url = f"{self._base}/bot{self.token}/sendDocument"

        def _build_form() -> "aiohttp.FormData":
            form = aiohttp.FormData()
            form.add_field("chat_id", self.chat_id)
            if caption:
                form.add_field("caption", caption)
                form.add_field("parse_mode", HTML)
            form.add_field("document", content.encode("utf-8"),
                           filename=filename, content_type="text/plain")
            return form

        for attempt in (1, 2):
            try:
                async with self._send_lock:
                    async with self.session.post(url, data=_build_form(),
                                                 timeout=self._doc_timeout) as resp:
                        body = await resp.json(content_type=None)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[telegram] sendDocument network error: {exc}")
                return False
            if isinstance(body, dict) and body.get("ok"):
                print(f"[telegram] 📥 document uploaded: {filename} "
                      f"({len(content):,} chars)")
                return True
            params = (body or {}).get("parameters") or {} if isinstance(body, dict) else {}
            retry_after = params.get("retry_after")
            if isinstance(body, dict) and body.get("error_code") == 429 and retry_after and attempt == 1:
                await asyncio.sleep(min(float(retry_after), 30.0) + 0.5)
                continue
            desc = str((body or {}).get("description", body))[:160] if isinstance(body, dict) else str(body)[:160]
            print(f"[telegram] sendDocument rejected ({(body or {}).get('error_code') if isinstance(body, dict) else '?'}): {desc}")
            return False
        return False

    async def _sender_loop(self):
        while True:
            item = await self._queue.get()
            try:
                await self._send(item)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[telegram] فشل إرسال: {exc}")
            finally:
                self._queue.task_done()

    async def _send(self, item: Dict):
        data = {
            "chat_id": item.get("chat_id") or self.chat_id,
            "text": item["text"],
            "parse_mode": HTML,
            "disable_web_page_preview": True,
        }
        if item.get("buttons"):
            data["reply_markup"] = {"inline_keyboard": item["buttons"]}
        for attempt in (1, 2):
            body = await self._api("sendMessage", data)
            if body is None:                       # network error → one retry
                if attempt == 1:
                    await asyncio.sleep(1.0)
                    continue
                return
            if body.get("ok"):
                return
            params = body.get("parameters") or {}
            retry_after = params.get("retry_after")
            if body.get("error_code") == 429 and retry_after:
                await asyncio.sleep(min(float(retry_after), 30.0) + 0.5)
                continue
            desc = str(body.get("description", ""))[:160]
            print(f"[telegram] sendMessage rejected ({body.get('error_code')}): {desc}")
            if body.get("error_code") == 403 and "initiate" in desc:
                print("[telegram] 💡 افتح محادثة مع البوت واضغط Start أولاً — "
                      "البوت لا يستطيع مراسلة مستخدم لم يبدأ المحادثة.")
            elif body.get("error_code") == 400 and "chat not found" in desc:
                print("[telegram] 💡 CHAT_ID غير صحيح — للخاص يجب أن يكون الرقم "
                      "الرقمي (مثل 123456789) وليس @username.")
            return

    # ════════════════════════════════════════════════════════════════
    # Boot message & menus
    # ════════════════════════════════════════════════════════════════
    def main_keyboard(self, paused: bool = False) -> List[List[Dict]]:
        pause_label = "▶️ Resume" if paused else "⏸️ Pause"
        return [
            [{"text": "📊 Status", "callback_data": CB_STATUS},
             {"text": "📂 Open Positions", "callback_data": CB_POSITIONS},
             {"text": pause_label, "callback_data": CB_PAUSE}],
            [{"text": "📋 Trade Log", "callback_data": f"{CB_LOG}:0"},
             {"text": "📥 Download Full Log (.txt)", "callback_data": CB_EXPORT}],
            [{"text": "🏠 Menu", "callback_data": CB_MENU}],
        ]

    def boot_text(self, env: str, universe: Optional[int] = None,
                  paused: bool = False) -> str:
        state = "⏸️ PAUSED" if paused else "🟢 RUNNING"
        lines = [
            "🚀 <b>NOVA HFT Engine Active</b>",
            f"• Mode: <b>{esc(env)}</b>  |  State: {state}",
        ]
        if universe:
            lines.append(f"• Universe: {universe} USDT pairs on live streams")
        lines.append("• ⚗️ Phase: <b>FORWARD PROFILING</b> — zero-threshold; "
                     "every core (KAMA) signal executes; NB score recorded only")
        lines.append(f"• Boot: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("Use the buttons below 👇")
        return "\n".join(lines)

    async def send_boot(self, env: str, universe: Optional[int] = None,
                        paused: bool = False):
        await self.send_async(self.boot_text(env, universe, paused),
                              self.main_keyboard(paused))

    def menu_text(self) -> str:
        return (
            "🤖 <b>NOVA HFT Control</b> — ⚗️ Forward Profiling\n"
            "• 📊 Status — engine stats &amp; filter hits\n"
            "• 📂 Open Positions — live PnL per position\n"
            "• ⏸️ Pause/Resume — toggle new entries "
            "(open positions stay managed)\n"
            "• 📋 Trade Log — detailed anatomy per trade, paginated "
            "(Next ➡️ / ⬅️ Previous)\n"
            "• 📥 Download Full Log (.txt) — exhaustive journal as a "
            "text document (all executed + closed trades)\n"
            "Commands: /status /positions /pause /resume /log [page] "
            "/export /menu"
        )

    # ════════════════════════════════════════════════════════════════
    # Long-polling loop — the ONLY inbound task; fully non-blocking
    # ════════════════════════════════════════════════════════════════
    def _authorized(self, upd: Dict) -> bool:
        """Only the configured chat may talk to the bot (buttons included)."""
        if not self.chat_id:
            return True  # no chat configured → don't lock the owner out
        chat = None
        msg = upd.get("message") or upd.get("edited_message")
        if msg:
            chat = (msg.get("chat") or {}).get("id")
        cb = upd.get("callback_query")
        if cb:
            chat = ((cb.get("message") or {}).get("chat") or {}).get("id") or chat
        if chat is None:
            return False
        return str(chat) == str(self.chat_id)

    async def poll(self, handle, stop_event: asyncio.Event):
        """Continuous /getUpdates long-poll. `handle` receives each authorized
        update; exceptions in handlers are contained — polling never dies."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        backoff = 1.0
        url = f"{self._base}/bot{self.token}/getUpdates"
        print("[telegram] polling loop started (long-poll /getUpdates)")
        while self._running and not stop_event.is_set():
            try:
                params = {"offset": self._offset, "timeout": 50,
                          "allowed_updates": json.dumps(["message", "callback_query"])}
                async with self.session.get(url, params=params,
                                            timeout=self._poll_timeout) as resp:
                    data = await resp.json(content_type=None)
                if not isinstance(data, dict) or not data.get("ok"):
                    code = data.get("error_code", "?") if isinstance(data, dict) else "?"
                    desc = str(data.get("description", ""))[:160] if isinstance(data, dict) else "?"
                    print(f"[telegram] getUpdates rejected ({code}): {desc}")
                    if code == 409:
                        # A webhook is set on this token → long-poll can't work.
                        await self._api("deleteWebhook", {"drop_pending_updates": False})
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30.0)
                    continue
                backoff = 1.0
                for upd in data.get("result", []):
                    self._offset = upd.get("update_id", 0) + 1
                    if not self._authorized(upd):
                        cb = upd.get("callback_query")
                        if cb:
                            await self.answer_callback(cb.get("id", ""), "⛔ Not authorized")
                        continue
                    try:
                        await handle(upd)
                    except Exception as exc:
                        print(f"[telegram] handler error: {exc}")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[telegram] خطأ استطلاع: {exc} — إعادة المحاولة بعد {backoff:.0f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
        print("[telegram] polling loop stopped")

    async def answer_callback(self, callback_id: str, text: str = ""):
        """Ack a callback FAST so the user's client doesn't spin forever."""
        if not callback_id:
            return
        await self._api("answerCallbackQuery",
                        {"callback_query_id": callback_id, "text": text or None,
                         "show_alert": False})

    # ════════════════════════════════════════════════════════════════
    # Message builders (English UI)
    # ════════════════════════════════════════════════════════════════
    def entry_message(self, sig: Dict) -> str:
        side = sig.get("side", "LONG")
        icon = "🟩" if side == "LONG" else "🟥"
        zt = "yes — executed regardless of score" if sig.get("zero_threshold") else "no (legacy gate)"
        note = sig.get("nb_note") or "passed gate"
        L = [
            f"{icon} <b>ENTRY {side} {coin(sig['symbol'])}</b>  <code>#{sig.get('trade_id', '—')}</code>",
            f"• Trigger: <b>{esc(sig.get('trigger', 'KAMA'))}</b> (core) | Zero-threshold: {zt}",
            f"• Price <code>{fmt_px(sig['price'])}</code> | Qty <code>{fmt_px(sig['qty'])}</code>",
            f"• Naive-Bayes: <b>{esc(sig.get('nb', '—'))}</b> — exact score "
            f"<b>{fmt_score_pct(sig.get('nb_score'))}</b> ({esc(note)})",
            f"• Stop <code>{fmt_px(sig['stop'])}</code> | Target <code>{fmt_px(sig['target'])}</code>",
            f"• Plan: ATR {fnum(sig.get('atr_pct')):.2f}% · displacement {fnum(sig.get('displacement')):.2f}×ATR",
        ]
        return "\n".join(L)

    def exit_message(self, txn: Dict) -> str:
        net = txn.get("net", 0.0)
        icon = "🟢" if net >= 0 else "🔴"
        side = txn.get("side", "LONG")
        score_txt = fmt_score_pct(txn.get("score"))
        if not txn.get("nb_ready", True):
            score_txt += " (NB warm-up)"
        hold = fmt_dur(txn.get("hold_sec"))
        return (
            f"{icon} <b>EXIT {side} {coin(txn['symbol'])}</b>  <code>#{txn.get('trade_id', '—')}</code>\n"
            f"• Trigger: {esc(txn.get('trigger', 'KAMA'))} | NB at entry: "
            f"{esc(txn.get('nb', '—'))} {score_txt}\n"
            f"• Entry <code>{fmt_px(txn['entry'])}</code> → Exit <code>{fmt_px(txn['exit'])}</code> (qty {fmt_px(txn['qty'])})\n"
            f"• Gross {txn['pnl']:+.4f}$ | Fee −{txn.get('fee', 0):.4f}$\n"
            f"• <b>Final PnL (net after fees): {net:+.4f}$</b>  ← the real number\n"
            f"• Reason: {esc(txn['reason'])} | Held {hold}"
        )

    def stats_text(self, metrics: Dict, daily: Dict, filters: Dict,
                   gov_paused: List[str], nb_acc: float, kama_ok: bool,
                   zt: bool = True) -> str:
        L = ["📊 <b>NOVA v5 — FORWARD PROFILING</b>", ""]
        L.append("🧪 Mode: <b>ZERO-THRESHOLD</b> — every core (KAMA) signal executes "
                 "on Testnet; NB score recorded, never gating"
                 if zt else
                 "🧪 Mode: LEGACY — NB Bull floor + Diverged veto enforced")
        if daily.get("date"):
            L.append(
                f"📅 Today {daily['date']}: {daily.get('trades', 0)} trades | "
                f"🟢 {daily.get('wins', 0)} / 🔴 {daily.get('losses', 0)} | "
                f"net after fees <b>{daily.get('net', 0.0):+.4f}$</b>"
            )
        L.append(
            f"🧮 Total: {metrics.get('trades', 0)} trades | "
            f"net after fees <b>{metrics.get('net_fees', 0.0):+.4f}$</b> "
            f"(fees {metrics.get('fees', 0.0):.4f}$)"
        )
        L.append(f"🧠 Naive-Bayes calibration (observer): {nb_acc * 100:.0f}% — "
                 f"{'healthy' if kama_ok else 'may need recalibration'}")
        if gov_paused:
            L.append(f"⚖️ Symbols with open positions: {', '.join(gov_paused)} — rest keeps trading")
        top = sorted(filters.items(), key=lambda kv: kv[1], reverse=True)[:5]
        line = " | ".join(f"{k}: {v}" for k, v in top if int(v) > 0)
        if line:
            L.append(f"🚧 Rejection/skip counters: {line}")
        L.append("")
        L.append("💡 📋 Trade Log = detailed paginated history · "
                 "📥 Download Full Log (.txt) = exhaustive journal document.")
        return "\n".join(L)

    # ── Paginated trade log (text + nav keyboard) ────────────────────────
    async def log_view(self, book: List[Dict], page: int) -> Tuple[str, List[List[Dict]]]:
        """📋 Trade Log — one anatomy block per trade, 5–7 trades per message.

        Each row shows: Trade Type (side), Symbol, Entry/Exit prices, Trigger
        Source, EXACT NB Score and Final PnL (net + gross). Pagination is hard
        clamped to ≤ 7 rows AND trimmed again against a character budget, so a
        page can never hit Telegram's 4096-char ceiling."""
        size = int(getattr(self.cfg, "log_page_size", LOG_PAGE_DEFAULT) or LOG_PAGE_DEFAULT)
        size = max(LOG_PAGE_MIN, min(size, LOG_PAGE_MAX))        # 5..7 strict
        n = len(book)
        total = max(1, (n + size - 1) // size)
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 0
        page = max(0, min(page, total - 1))
        chunk = list(reversed(book))              # newest first
        rows_src = chunk[page * size: page * size + size]

        rows: List[str] = []
        for r in rows_src:
            net = fnum(r.get("net"))
            blocked = fnum(r.get("entry")) <= 0     # recorded-only rows (live-locked…)
            if blocked:
                icon = "🚫"
            else:
                icon = "🟢" if net >= 0 else "🔴"
            ts = r.get("t")
            try:
                t = datetime.fromtimestamp(float(ts)).strftime("%H:%M:%S") if ts else "--:--:--"
            except (TypeError, ValueError, OSError):
                t = "--:--:--"        # corrupt hand-edited journal row → render, never crash
            side = r.get("side", "LONG")
            score = r.get("score", None)
            score_txt = fmt_score_pct(score)
            if score is not None and not r.get("nb_ready", True):
                score_txt += " (warm-up)"
            zt_note = " · zero-threshold" if r.get("zero_threshold") is True and fnum(r.get("entry")) > 0 else ""
            reason = esc(r.get("reason", "—"))
            hold = fmt_dur(r.get("hold_sec")) if r.get("hold_sec") is not None else None
            lines = [
                f"{icon} <b>{side} {coin(r['symbol'])}</b> <code>#{r.get('trade_id', '—')}</code> — {t}",
                f"   Trigger: {esc(r.get('trigger', 'KAMA'))}{zt_note} | NB {esc(r.get('nb', '—'))} → {score_txt}",
                f"   Entry <code>{fmt_px(r.get('entry'))}</code> → Exit <code>{fmt_px(r.get('exit'))}</code> (qty {fmt_px(r.get('qty'))})",
                f"   Gross {fnum(r.get('pnl')):+.4f}$ | Fee −{fnum(r.get('fee')):.4f}$ | <b>Final PnL {net:+.4f}$</b>",
                f"   Reason: {reason}" + (f" | Held {hold}" if hold else ""),
            ]
            rows.append("\n".join(lines))

        header = (f"📋 <b>Trade Log</b> — page {page + 1}/{total} · {n} recorded · "
                  f"{size}/page · ⚗️ zero-threshold")
        L = [header, ""]
        if not rows:
            L.append("No closed trades yet — the journal builds itself as trades close. "
                     "Every executed signal lands here with its full anatomy.")
        L.extend(rows)
        text = "\n".join(L)
        # Absolute safety trim: rows are ~250 chars, but if any pathological
        # symbol/reason string pushes the page past the budget we drop trailing
        # rows until it fits (last line of defence vs Telegram's 4096 limit).
        if len(text) > TG_TEXT_SAFE_LIMIT:
            while len(text) > TG_TEXT_SAFE_LIMIT and len(rows) > 1:
                rows.pop()
                text = "\n".join([header, ""] + rows)
            text += ("\n\n… page trimmed to fit Telegram's message limit — "
                     "press 📥 Download Full Log (.txt) for everything.")
        kb: List[List[Dict]] = []
        if total > 1:
            nav: List[Dict] = []
            if page > 0:
                nav.append({"text": "⬅️ Previous", "callback_data": f"{CB_LOG}:{page - 1}"})
            nav.append({"text": f"📄 {page + 1}/{total}", "callback_data": CB_NOOP})
            if page < total - 1:
                nav.append({"text": "Next ➡️", "callback_data": f"{CB_LOG}:{page + 1}"})
            kb.append(nav)
        kb.append([{"text": "📥 Download Full Log (.txt)", "callback_data": CB_EXPORT}])
        kb.extend(self.main_keyboard())
        return text, kb
