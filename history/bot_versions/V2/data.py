"""
NOVA v5 — طبقة البيانات WebSockets (M1)
========================================
- يستقرئ تدفقات Binance فقط (kline_1m, aggTrade, bookTicker) عبر aiohttp.
- لا REST في حلقة الفحص (مُقفل) — لا Rate-limit، لا بطء.
- قائمة عملات ديناميكية (~50 أعلى سيولة) تُحدَّث كل 10 دقائق.
- CVD دقيقة من aggTrade (يغذّي Naive-Bayes).
"""

from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, List, Optional

import aiohttp

# عقد تدفقات Binance
WS_LIVE = "wss://stream.binance.com:9443/stream?streams="
WS_TEST = "wss://stream.binance.com:9443/stream?streams="
REST_TEST = "https://testnet.binance.vision"
REST_LIVE = "https://api.binance.com"


class BinanceData:
    def __init__(self, cfg, on_kline=None, on_trade=None, on_book=None):
        self.cfg = cfg
        self.session: Optional[aiohttp.ClientSession] = None
        self.on_kline = on_kline          # callback(stream) لكل شمعة 1m مغلقة
        self.on_trade = on_trade          # callback(stream) لكل aggTrade
        self.on_book = on_book            # callback(stream) لكل bookTicker
        self.universe: List[str] = []
        self.symbol_rules: Dict[str, Dict] = {}
        self._last_refresh = 0.0

    @property
    def ws_url(self):
        return WS_TEST if self.cfg.is_testnet else WS_LIVE

    async def start(self):
        self.session = aiohttp.ClientSession()
        await self.refresh_universe(force=True)

    async def close(self):
        if self.session:
            await self.session.close()

    # ── قائمة العملات الديناميكية (M) ────────────────────────
    async def refresh_universe(self, force: bool = False):
        now = time.time()
        if not force and now - self._last_refresh < self.cfg.universe_refresh_sec:
            return
        self._last_refresh = now
        try:
            url = (REST_TEST if self.cfg.is_testnet else REST_LIVE) + "/api/v3/exchangeInfo"
            async with self.session.get(url, timeout=15) as resp:
                info = await resp.json()
            rules = {}
            candidates = []
            for s in info.get("symbols", []):
                if s.get("quoteAsset") != self.cfg.quote_asset:
                    continue
                if s.get("status") != "TRADING":
                    continue
                if not s.get("isSpotTradingAllowed"):
                    continue
                rules[s["symbol"]] = {"min_notional": s.get("minNotional", "0"),
                                      "tickSize": s.get("tickSize", "0"),
                                      "stepSize": s.get("stepSize", "0"),
                                      "status": "TRADING"}
                candidates.append(s["symbol"])
            # نحدّد الأقوى بالسيولة عبر 24h tickers (استدعاء واحد)
            try:
                tu = (REST_TEST if self.cfg.is_testnet else REST_LIVE) + "/api/v3/ticker/24hr"
                async with self.session.get(tu, timeout=15) as resp:
                    tickers = await resp.json()
                vol = {t["symbol"]: float(t.get("quoteVolume", 0.0)) for t in tickers}
            except Exception:
                vol = {}
            candidates.sort(key=lambda s: vol.get(s, 0.0), reverse=True)
            self.universe = candidates[:self.cfg.top_n_symbols]
            self.symbol_rules = {s: rules[s] for s in self.universe if s in rules}
            print(f"[data] قائمة العملات محدّثة: {len(self.universe)} (أعلى سيولة)")
        except Exception as exc:
            print(f"[data] فشل تحديث قائمة العملات: {exc}")

    # ── WebSocket master loop ────────────────────────────────
    async def stream_loop(self, symbols: List[str]):
        """يربط تدفقها الكامل لرمزٍ واحد. يعيد الاتصال حال الانقطاع."""
        if not symbols:
            await asyncio.sleep(5)
            return
        streams = []
        for s in symbols:
            ls = s.lower()
            streams += [f"{ls}@kline_1m", f"{ls}@aggTrade", f"{ls}@bookTicker"]
        url = self.ws_url + "/".join(streams)
        print(f"[ws] ربط {len(streams)} تدفق لـ {len(symbols)} رمز...")
        while True:
            try:
                async with self.session.ws_connect(url, heartbeat=self.cfg.ws_heartbeat_sec, max_msg_size=4 * 1024 * 1024) as ws:
                    print(f"[ws] متصل: {len(streams)} تدفق")
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            self._dispatch(json.loads(msg.data))
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[ws] خطأ/انقطاع ({exc}) — إعادة اتصال خلال 5ث")
            await asyncio.sleep(5)

    def _dispatch(self, data: Dict):
        stream = data.get("stream", "")
        if "aggTrade" in stream:
            self._handle_trade(data.get("data", {}))
        elif "bookTicker" in stream:
            self._handle_book(data.get("data", {}))
        elif "kline" in stream:
            self._handle_kline(data.get("data", {}))

    def _handle_trade(self, d: Dict):
        if not d:
            return
        q = float(d.get("q", 0.0))
        is_buyer_maker = bool(d.get("m", False))
        delta = q if not is_buyer_maker else -q   # KB §0.2-5: native delta
        if self.on_trade:
            self.on_trade({"symbol": d.get("s"), "price": float(d.get("p", 0.0)),
                           "qty": q, "delta": delta, "ts": d.get("T")})

    def _handle_book(self, d: Dict):
        if not d:
            return
        if self.on_book:
            self.on_book({"symbol": d.get("s"), "bid": float(d.get("b", 0.0)),
                          "ask": float(d.get("a", 0.0))})

    def _handle_kline(self, d: Dict):
        k = d.get("k")
        if not k or not k.get("x"):  # نستهلك الشموع المغلقة فقط
            return
        if self.on_kline:
            self.on_kline({"symbol": d.get("s"),
                           "open": float(k["o"]), "high": float(k["h"]),
                           "low": float(k["l"]), "close": float(k["c"]),
                           "volume": float(k["v"]), "ts": int(k["t"])})
