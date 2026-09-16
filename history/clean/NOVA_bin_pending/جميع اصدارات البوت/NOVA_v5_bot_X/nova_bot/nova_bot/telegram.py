"""
NOVA v5 — تليجرام Async (M6) عبر aiohttp
=========================================
- جلسة aiohttp واحدة غير حابسة.
- لا يوقف WebSockets (يقرأ الحالة المشتركة، ويرسل ثم يغلق).
- رسائل دخول/خروج + صافي بعد العمولة + صفحة سجل مبوّبة + تقرير يومي.
- البنود المٌقفلة: Net-after-fees في كل رسالة، والتقرير اليومي.
"""

from __future__ import annotations
import asyncio
import html
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp

HTML = "HTML"


def esc(value) -> str:
    return html.escape(str(value))


def coin(sym: str) -> str:
    return str(sym).replace("USDT", "")


class TelegramBot:
    def __init__(self, token: str, chat_id: str, cfg):
        self.token = token
        self.chat_id = chat_id
        self.cfg = cfg
        self.session: Optional[aiohttp.ClientSession] = None
        self._base = "https://api.telegram.org"
        self._send_lock = asyncio.Lock()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._last_daily_key: Optional[str] = None

    async def start(self):
        self.session = aiohttp.ClientSession()
        asyncio.create_task(self._sender_loop())

    async def close(self):
        if self.session:
            await self.session.close()

    # ── حلقة إرسال غير حابسة ─────────────────────────────────
    async def _sender_loop(self):
        while True:
            item = await self._queue.get()
            try:
                await self._send(item)
            except Exception as exc:
                print(f"[telegram] فشل إرسال: {exc}")
            finally:
                self._queue.task_done()

    async def send_async(self, text: str, buttons: Optional[List[List[Dict]]] = None):
        await self._queue.put({"text": text, "buttons": buttons})

    async def _send(self, payload):
        data = {
            "chat_id": self.chat_id,
            "text": payload["text"],
            "parse_mode": HTML,
            "disable_web_page_preview": True,
        }
        if payload.get("buttons"):
            data["reply_markup"] = {"inline_keyboard": payload["buttons"]}
        url = f"{self._base}/bot{self.token}/sendMessage"
        async with self._send_lock:
            async with self.session.post(url, json=data, timeout=20) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    print(f"[telegram] HTTP {resp.status}: {body[:200]}")

    # ── رسائل الرسائل ───────────────────────────────────────
    def entry_message(self, sig: Dict) -> str:
        return (
            f"🚀 <b>دخول {coin(sig['symbol'])}</b>\n"
            f"• السعر <code>{sig['price']:g}</code> | كمية <code>{sig['qty']:g}</code>\n"
            f"• <b>ثقة الفرصة:</b> Score {sig['score']:.1f}/100 — {sig['tier']}\n"
            f"• تدفق Naive-Bayes: <b>{sig['nb']}</b>\n"
            f"• وقف <code>{sig['stop']:g}</code> | هدف <code>{sig['target']:g}</code>\n"
            f"• مُخطط: ATR {sig['atr_pct']:.2f}% · إزاحة {sig['displacement']:.2f}·ATR"
        )

    def exit_message(self, txn: Dict) -> str:
        net = txn.get("net", 0.0)
        icon = "🟢" if net >= 0 else "🔴"
        return (
            f"{icon} <b>خروج {coin(txn['symbol'])}</b>\n"
            f"• دخول <code>{txn['entry']:g}</code> ← خروج <code>{txn['exit']:g}</code>\n"
            f"• خام {txn['pnl']:+.4f}$ | عمولة −{txn['fee']:.4f}$\n"
            f"• <b>صافي بعد العمولة: {net:+.4f}$</b>  ← الرقم الحقيقي\n"
            f"• السبب: {esc(txn['reason'])}"
        )

    def stats_text(self, state: Dict, metrics: Dict, daily: Dict, filters: Dict,
                   gov_paused: List[str], nb_acc: float, kama_ok: bool) -> str:
        L = ["📊 <b>NOVA v5 — ZERO-WAIT QUANT</b>", ""]
        if daily.get("date"):
            L.append(
                f"📅 اليوم {daily['date']}: {daily.get('trades', 0)} صفقة | "
                f"🟢 {daily.get('wins', 0)} / 🔴 {daily.get('losses', 0)} | "
                f"صافي بعد العمولة <b>{daily.get('net', 0.0):+.4f}$</b>"
            )
        L.append(
            f"🧮 كلي: {metrics.get('trades', 0)} صفقة | "
            f"صافي بعد العمولة <b>{metrics.get('net_fees', 0.0):+.4f}$</b> "
            f"(عمولات {metrics.get('fees', 0.0):.4f}$)"
        )
        L.append(f"🧠 ضبط Naive-Bayes: {nb_acc * 100:.0f}% — {('منتظم' if kama_ok else 'قد يحتاج إعادة ضبط')}")
        if gov_paused:
            L.append(f"⚖️ تحت العقوبة: {', '.join(gov_paused)} — بقية السوق يتداول")
        top = sorted(filters.items(), key=lambda kv: kv[1], reverse=True)[:4]
        line = " | ".join(f"{k}: {v}" for k, v in top if int(v) > 0)
        if line:
            L.append(f"🚧 الفلاتر رفضت: {line}")
        L.append("")
        L.append("💡 أرسل 📋 لسجل الصفقات صفحةً صفحة، أو 🏠 للقائمة.")
        return "\n".join(L)

    def _main_keyboard(self) -> List[List[Dict]]:
        return [
            [{"text": "📊 الإحصاء", "callback_data": "stats"}],
            [{"text": "📋 سجل الصفقات", "callback_data": "log:0"}],
            [{"text": "🏠 القائمة", "callback_data": "help"}, {"text": "🔄 تحديث", "callback_data": "stats"}],
        ]

    async def log_page(self, book: List[Dict], page: int) -> str:
        total = max(1, (len(book) + self.cfg.log_page_size - 1) // self.cfg.log_page_size)
        page = max(0, min(int(page), total - 1))
        chunk = list(reversed(book))
        start = page * self.cfg.log_page_size
        rows = chunk[start:start + self.cfg.log_page_size]
        L = [f"📋 <b>سجل الصفقات</b> — صفحة {page + 1}/{total} ({len(book)} صفقة)", ""]
        if not rows:
            L.append("لا صفقات بعد — السجل يُبنى تلقائياً.")
        for r in rows:
            icon = "🟢" if r.get("net", 0) >= 0 else "🔴"
            t = datetime.fromtimestamp(r["t"]).strftime("%H:%M:%S")
            L.append(
                f"{icon} <b>{coin(r['symbol'])}</b> | {t}\n"
                f"   دخول <code>{r['entry']:g}</code> ← خروج <code>{r['exit']:g}</code> "
                f"(كمية {r['qty']:g})\n"
                f"   Score {r.get('score', 0):.0f} | NB {r.get('nb', '—')} | "
                f"خام {r['pnl']:+.4f}$ | عمولة −{r.get('fee', 0):.4f}$ "
                f"| <b>صافي {r['net']:+.4f}$</b>\n"
                f"   السبب: {esc(r['reason'])}"
            )
        return "\n".join(L)

    # ── استطلاع الأوامر التفاعلية (Pagination) ─────────────
    async def poll(self, handle, stop_event: asyncio.Event):
        offset = 0
        url = f"{self._base}/bot{self.token}/getUpdates"
        while not stop_event.is_set():
            try:
                params = {"offset": offset, "timeout": 50,
                          "allowed_updates": json.dumps(["message", "callback_query"])}
                async with self.session.get(url, params=params, timeout=60) as resp:
                    data = await resp.json()
                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    await handle(upd)
            except Exception as exc:
                print(f"[telegram] خطأ استطلاع: {exc}")
                await asyncio.sleep(2)

    async def answer_callback(self, callback_id: str, text: str = ""):
        try:
            url = f"{self._base}/bot{self.token}/answerCallbackQuery"
            async with self.session.post(url, json={"callback_query_id": callback_id, "text": text}) as resp:
                await resp.read()
        except Exception:
            pass

    async def maybe_daily_report(self, state: Dict):
        now = datetime.now()
        key = now.strftime("%Y-%m-%d")
        if now.hour == self.cfg.daily_report_hour and self._last_daily_key != key:
            self._last_daily_key = key
            await self.send_async(self.stats_text(*state.get("_report_args", ())), self._main_keyboard())
