"""حاضنة تشغيل غير متصلة (V6.2): تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي."""
import asyncio
import importlib.util
import json
import os
import sys
import time

BOT_PATH = os.getenv("NOVA_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "NOVA.py")
spec = importlib.util.spec_from_file_location("nv5", BOT_PATH)
m = importlib.util.module_from_spec(spec)
sys.modules["nv5"] = m
spec.loader.exec_module(m)

FAIL = []

def ok(name, cond, extra=""):
    print(("✅ " if cond else "❌ ") + name + (f"  {extra}" if extra else ""))
    if not cond:
        FAIL.append(name)

STEP = 300_000
NOW_MS = int(time.time() * 1000)

def synth_rows(n=140, last_open=None):
    last_open = last_open if last_open is not None else NOW_MS // STEP * STEP
    rows = []
    for i in range(n):
        t = last_open - (n - 1 - i) * STEP
        if i <= n - 4:
            rows.append([t, "100.0", "100.5", "99.5", "100.0", "1000", 0, "0", "1", "0", "0", "0"])
        elif i == n - 3:
            rows.append([t, "100.2", "109.2", "100.1", "109.0", "5000", 0, "0", "1", "0", "0", "0"])
        elif i == n - 2:
            rows.append([t, "105.0", "110.3", "104.0", "110.0", "4000", 0, "0", "1", "0", "0", "0"])
        else:
            rows.append([t, "109.5", "110.4", "109.0", "110.0", "1500", 0, "0", "1", "0", "0", "0"])
    return rows

def synth_15m(n=220):
    step15 = 900_000
    last = NOW_MS // step15 * step15
    return [[last - (n - 1 - i) * step15, "100", "100.6", "99.6", "100.2", "900", 0, "0", "1", "0", "0", "0"]
            for i in range(n)]

def synth_btc_1m(n=64):
    step = 60_000
    last = NOW_MS // step * step
    rows = []
    for i in range(n):
        t = last - (n - 1 - i) * step
        rows.append([t, "60000", "60060", "59940", "60000", "500", i, "0", "1" if i < n - 1 else "0", "0", "0", "0"])
    return rows

SYMBOLS_LIST = [f"C{i}USDT" for i in range(30)]

class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.headers = {"X-MBX-USED-WEIGHT-1M": "120"}
    async def json(self, content_type=None): return self.payload
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False

class FakeWS:
    def __init__(self):
        self.closed = False
        self.sent = []
    async def send_json(self, obj): self.sent.append(obj)
    def __aiter__(self): return self
    async def __anext__(self):
        for _ in range(400): await asyncio.sleep(0.01)
        raise StopAsyncIteration
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False

class FakeSession:
    INSTANCES = []
    def __init__(self, *a, **k):
        self.ws_calls = []
        self.http_calls = []
        FakeSession.INSTANCES.append(self)
    def ws_connect(self, url, **kw):
        ws = FakeWS()
        self.ws_calls.append((url, kw))
        return ws
    def request(self, method, url, headers=None, timeout=None):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        path = parsed.path
        self.http_calls.append((method, path))
        if path == "/api/v3/time": return FakeResponse({"serverTime": int(time.time() * 1000)})
        if path == "/api/v3/exchangeInfo": return FakeResponse(EXCHANGE_INFO)
        if path == "/api/v3/klines":
            symbol = parse_qs(parsed.query).get("symbol", [""])[0]
            interval = parse_qs(parsed.query).get("interval", [""])[0]
            if symbol == m.BTC_CONTEXT_SYMBOL and interval == "1m": return FakeResponse(synth_btc_1m())
            if interval == m.MICRO_INTERVAL: return FakeResponse(synth_rows())
            return FakeResponse(synth_rows())
        if path == "/api/v3/ticker/24hr": return FakeResponse(TICKERS)
        if path == "/api/v3/ticker/bookTicker": return FakeResponse({"symbol": parse_qs(parsed.query).get("symbol", [""])[0], "bidPrice": "109.9", "bidQty": "20", "askPrice": "110.0", "askQty": "10"})
        if path == "/api/v3/aggTrades": return FakeResponse([[i, "110.0", "20", "1", "2", "1", str(NOW_MS - i * 250), "true", "true", "true"] for i in range(6)][::-1])
        if path == "/api/v3/account": return FakeResponse({"balances": [{"asset": "USDT", "free": "5000", "locked": "0"}]})
        if path in ("/api/v3/openOrders", "/api/v3/order", "/api/v3/orderList"): return FakeResponse([] if path == "/api/v3/openOrders" else {"status": "CANCELED", "executedQty": "0"})
        return FakeResponse({})
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False

class FakeAiohttp:
    TCPConnector = lambda *a, **k: None
    ClientSession = FakeSession
    ClientTimeout = dict
    ClientError = Exception
    WSMsgType = type("T", (), {"TEXT": 1, "CLOSED": 2, "CLOSING": 3, "ERROR": 4})

LIVE_PROBE = {"on": False, "entry": [], "oco": []}
TICKERS = [{"symbol": s, "lastPrice": "110", "priceChangePercent": "1.2", "quoteVolume": str(90_000_000 - i * 1000)} for i, s in enumerate(SYMBOLS_LIST)]
EXCHANGE_INFO = {"symbols": [{"symbol": s, "status": "TRADING", "baseAsset": s[:-4], "quoteAsset": "USDT", "filters": [{"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001", "maxQty": "900000"}, {"filterType": "MARKET_LOT_SIZE", "stepSize": "0.001", "minQty": "0.001", "maxQty": "900000"}, {"filterType": "PRICE_FILTER", "tickSize": "0.01"}, {"filterType": "NOTIONAL", "minNotional": "5"}]} for s in SYMBOLS_LIST]}

async def scenario():
    m.aiohttp = FakeAiohttp()
    m.SESSION = FakeSession()
    m.REST = m.BinanceRest(m.SESSION)
    m.DRY_RUN = True
    m.AUTO_TRADE = True
    try:
        await asyncio.wait_for(m.amain({"--once"}), timeout=60)
        ok("amain(--once) أكمل مسار الإقلاع بنجاح", True)
    except Exception as e:
        ok("amain(--once) فشل", False, str(e))

rc = asyncio.run(scenario())
print("\nالحصيلة:", "FAIL ❌ " if FAIL else "ALL PASS ✅")
sys.exit(1 if FAIL else 0)

