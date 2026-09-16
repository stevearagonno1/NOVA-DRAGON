"""
NOVA v5 — التنفيذ المُوقّع + إدارة المراكز (M8)
===============================================
ملاحظة: «لا REST» مقصود به حلقة الفحص (المؤشرات). إرسال الأوامر يظل بـ REST
الموقّع (ضروري للأمان/العمق). التنفيذ الحقيقي يُفعَّل على Testnet حصراً.
"""

from __future__ import annotations
import asyncio
import hashlib
import hmac
import json
import time
import uuid
from typing import Dict, List, Optional

import aiohttp

REST_TEST = "https://testnet.binance.vision"
REST_LIVE = "https://api.binance.com"


class BinanceExec:
    def __init__(self, cfg):
        self.cfg = cfg
        self.session: Optional[aiohttp.ClientSession] = None
        self._path = REST_TEST if cfg.is_testnet else REST_LIVE
        self._time_offset_ms = 0

    async def start(self):
        self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(self._path + "/api/v3/time", timeout=10) as r:
                data = await r.json()
                self._time_offset_ms = int(data.get("serverTime", 0)) - int(time.time() * 1000)
        except Exception:
            pass

    async def close(self):
        if self.session:
            await self.session.close()

    def _params(self, params: Dict) -> Dict:
        p = dict(params)
        p["timestamp"] = int(time.time() * 1000 + self._time_offset_ms)
        p["recvWindow"] = 10000
        return p

    def _sign(self, params: Dict) -> Dict:
        qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        sig = hmac.new(self.cfg.api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params

    async def _signed(self, method: str, path: str, params: Dict, retry: bool = True) -> dict:
        p = self._sign(self._params(params))
        url = self._path + path
        headers = {"X-MBX-APIKEY": self.cfg.api_key}
        for attempt in range(2 if retry else 1):
            try:
                async with self.session.request(method, url, params=p, headers=headers, timeout=15) as r:
                    body = await r.text()
                    if r.status >= 400:
                        raise BinanceExecError(f"HTTP {r.status}: {body[:200]}")
                    return json.loads(body) if body else {}
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if attempt == 0 and retry:
                    await asyncio.sleep(0.5)
                    continue
                raise
        return {}

    async def account_free(self, asset: str) -> float:
        try:
            acc = await self._signed("GET", "/api/v3/account", {})
            for b in acc.get("balances", []):
                if b.get("asset") == asset:
                    return float(b.get("free", 0.0))
        except Exception:
            pass
        return 0.0

    async def new_limit(self, symbol: str, side: str, qty: str, price: str) -> dict:
        params = {"symbol": symbol, "side": side, "type": "LIMIT_MAKER",
                  "quantity": qty, "price": price,
                  "timeInForce": "GTC", "newClientOrderId": "no-" + uuid.uuid4().hex[:12]}
        return await self._signed("POST", "/api/v3/order", params)

    async def new_oco(self, symbol: str, qty: str, price: str, stop_price: str,
                      stop_limit_price: str, limit_tp: str) -> dict:
        # وُضع في النموذج ASYNC — لكن Binance Spot OCO يستخدم order+stopLimit.
        params = {"symbol": symbol, "side": "SELL", "quantity": qty,
                  "price": limit_tp, "stopPrice": stop_price,
                  "stopLimitPrice": stop_limit_price, "stopLimitTimeInForce": "GTC",
                  "listClientOrderId": "oco-" + uuid.uuid4().hex[:12]}
        return await self._signed("POST", "/api/v3/orderList/oco", params)

    async def cancel_all(self, symbol: str) -> None:
        try:
            await self._signed("DELETE", "/api/v3/openOrders", {"symbol": symbol})
        except Exception:
            pass

    async def market_sell(self, symbol: str, qty: str) -> dict:
        return await self._signed("POST", "/api/v3/order",
                                  {"symbol": symbol, "side": "SELL", "type": "MARKET", "quantity": qty})

    async def get_order(self, symbol: str, order_id: Optional[int] = None, client_id: Optional[str] = None) -> dict:
        params = {"symbol": symbol}
        if order_id is not None:
            params["orderId"] = order_id
        if client_id:
            params["origClientOrderId"] = client_id
        return await self._signed("GET", "/api/v3/order", params)


class BinanceExecError(Exception):
    pass
