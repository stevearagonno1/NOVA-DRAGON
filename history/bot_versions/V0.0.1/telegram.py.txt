"""
NOVA v5 — Interactive Async Telegram (M6 — Refactored)
======================================================

HFT-safety guarantees (this module can never slow the trading bot down):
• ONE shared aiohttp ClientSession; every network operation is async.
• All outbound messages are pushed into a BOUNDED asyncio.Queue drained by a
  dedicated sender task → the entry/exit hot paths never wait for Telegram
  RTT. If the queue is full the message is dropped + logged instead of
  stalling the engine.
• A single long-polling /getUpdates loop runs as its own task (launched with
  asyncio.create_task() from engine.run()) and handles commands + inline
  buttons, hardened with exponential backoff and clean cancellation.

Interactive features:
• Boot message "🚀 NOVA HFT Engine Active" with an inline menu:
      [ 📊 Status | 📂 Open Positions | ⏸️ Pause/Resume ]
      [ 📋 Trade Log | 🏠 Menu ]
• /start, /menu, /help  → re-send the menu.
• /status /positions /pause /resume /log → text aliases of the buttons.
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
CB_LOG = "menu:log"          # payload: f"{CB_LOG}:{page}"
CB_MENU = "menu:home"
CB_NOOP = "noop"


def esc(value) -> str:
    return html.escape(str(value))


def coin(sym: str) -> str:
    return str(sym).replace("USDT", "")


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
             {"text": "🏠 Menu", "callback_data": CB_MENU}],
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
        lines.append(f"• Boot: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("Use the buttons below 👇")
        return "\n".join(lines)

    async def send_boot(self, env: str, universe: Optional[int] = None,
                        paused: bool = False):
        await self.send_async(self.boot_text(env, universe, paused),
                              self.main_keyboard(paused))

    def menu_text(self) -> str:
        return (
            "🤖 <b>NOVA HFT Control</b>\n"
            "• 📊 Status — engine stats & filter hits\n"
            "• 📂 Open Positions — live PnL per position\n"
            "• ⏸️ Pause/Resume — toggle new entries "
            "(open positions stay managed)\n"
            "• 📋 Trade Log — paginated closed trades\n"
            "Commands: /status /positions /pause /resume /log /menu"
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
        return (
            f"🟩 <b>ENTRY {coin(sig['symbol'])}</b>\n"
            f"• Price <code>{sig['price']:g}</code> | Qty <code>{sig['qty']:g}</code>\n"
            f"• Confidence: Score {sig['score']:.1f}/100 — {sig['tier']}\n"
            f"• Naive-Bayes flow: <b>{sig['nb']}</b>\n"
            f"• Stop <code>{sig['stop']:g}</code> | Target <code>{sig['target']:g}</code>\n"
            f"• Plan: ATR {sig['atr_pct']:.2f}% · displacement {sig['displacement']:.2f}×ATR"
        )

    def exit_message(self, txn: Dict) -> str:
        net = txn.get("net", 0.0)
        icon = "🟢" if net >= 0 else "🔴"
        return (
            f"{icon} <b>EXIT {coin(txn['symbol'])}</b>\n"
            f"• Entry <code>{txn['entry']:g}</code> → Exit <code>{txn['exit']:g}</code>\n"
            f"• Gross {txn['pnl']:+.4f}$ | Fee −{txn['fee']:.4f}$\n"
            f"• <b>Net after fees: {net:+.4f}$</b>  ← the real number\n"
            f"• Reason: {esc(txn['reason'])}"
        )

    def stats_text(self, metrics: Dict, daily: Dict, filters: Dict,
                   gov_paused: List[str], nb_acc: float, kama_ok: bool) -> str:
        L = ["📊 <b>NOVA v5 — ZERO-WAIT QUANT</b>", ""]
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
        L.append(f"🧠 Naive-Bayes calibration: {nb_acc * 100:.0f}% — "
                 f"{'healthy' if kama_ok else 'may need recalibration'}")
        if gov_paused:
            L.append(f"⚖️ Symbols with open positions: {', '.join(gov_paused)} — rest keeps trading")
        top = sorted(filters.items(), key=lambda kv: kv[1], reverse=True)[:4]
        line = " | ".join(f"{k}: {v}" for k, v in top if int(v) > 0)
        if line:
            L.append(f"🚧 Filter rejections: {line}")
        L.append("")
        L.append("💡 Tap 📋 Trade Log for the paginated history, or 🏠 Menu.")
        return "\n".join(L)

    # ── Paginated trade log (text + nav keyboard) ────────────────
    async def log_view(self, book: List[Dict], page: int) -> Tuple[str, List[List[Dict]]]:
        size = int(getattr(self.cfg, "log_page_size", 8) or 8)
        total = max(1, (len(book) + size - 1) // size)
        page = max(0, min(int(page), total - 1))
        chunk = list(reversed(book))              # newest first
        rows = chunk[page * size: page * size + size]
        L = [f"📋 <b>Trade Log</b> — page {page + 1}/{total} ({len(book)} trades)", ""]
        if not rows:
            L.append("No closed trades yet — the journal builds itself as trades close.")
        for r in rows:
            icon = "🟢" if r.get("net", 0) >= 0 else "🔴"
            t = datetime.fromtimestamp(r["t"]).strftime("%H:%M:%S")
            L.append(
                f"{icon} <b>{coin(r['symbol'])}</b> | {t}\n"
                f"   entry <code>{r['entry']:g}</code> → exit <code>{r['exit']:g}</code> "
                f"(qty {r['qty']:g})\n"
                f"   Score {r.get('score', 0):.0f} | NB {r.get('nb', '—')} | "
                f"gross {r['pnl']:+.4f}$ | fee −{r.get('fee', 0):.4f}$ "
                f"| <b>net {r['net']:+.4f}$</b>\n"
                f"   Reason: {esc(r['reason'])}"
            )
        kb: List[List[Dict]] = []
        if total > 1:
            nav: List[Dict] = []
            if page > 0:
                nav.append({"text": "◀️ Prev", "callback_data": f"{CB_LOG}:{page - 1}"})
            nav.append({"text": f"📄 {page + 1}/{total}", "callback_data": CB_NOOP})
            if page < total - 1:
                nav.append({"text": "Next ▶️", "callback_data": f"{CB_LOG}:{page + 1}"})
            kb.append(nav)
        kb.extend(self.main_keyboard())
        return "\n".join(L), kb
