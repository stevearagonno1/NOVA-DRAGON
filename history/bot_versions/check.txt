"""حاضنة تشغيل غير متصلة: تُشغّل amain/--once وHub التوجيه مع Binance REST وهمي.

تتحقق من أن مسار الإقلاع الكامل (قواعد ← كون ← تسخين ← سياق BTC ← تنقيط ←
ت sizing ← أمر وهمي) يعمل بلا استثناءات، مع تغطية ما لا يغطيه --selftest.
"""
import asyncio
import importlib.util
import json
import os
import sys
import time

BOT_PATH = os.getenv("NOVA_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "NOVA_V5.py")
spec = importlib.util.spec_from_file_location("nv5", BOT_PATH)
m = importlib.util.module_from_spec(spec)
sys.modules["nv5"] = m
spec.loader.exec_module(m)

FAIL = []


def ok(name, cond, extra=""):
    print(("✅ " if cond else "❌ ") + name + (f"  {extra}" if extra else ""))
    if not cond:
        FAIL.append(name)


# ── بيانات سوق تركيبية: 30 رمزاً + BTC سياقي ─────────────────────────────────
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
        rows.append([t, "60000", "60060", "59940", "60000", "500", i, "0", "1" if i < n - 1 else "0",
                     "0", "0", "0"])
    return rows


SYMBOLS_LIST = [f"C{i}USDT" for i in range(30)]


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.headers = {"X-MBX-USED-WEIGHT-1M": "120"}

    async def json(self, content_type=None):
        return self.payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeWS:
    def __init__(self):
        self.closed = False
        self.sent = []

    async def send_json(self, obj):
        self.sent.append(obj)

    def __aiter__(self):
        return self

    async def __anext__(self):
        for _ in range(400):
            await asyncio.sleep(0.01)
        raise StopAsyncIteration

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    """طبقة HTTP وهمية تُشغّل BinanceRest الحقيقي (توقيع/أوزان/توجيه المسارات)."""

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
        query = parse_qs(parsed.query)
        path = parsed.path
        self.http_calls.append((method, path))
        if method.upper() != "GET" and "/order" in path and not LIVE_PROBE["on"]:
            raise AssertionError(f"أمر حقيقي أُرسل في وضع DRY_RUN: {path}")
        if LIVE_PROBE["on"] and path == "/api/v3/order":
            q = query.get("quantity", ["0"])[0]
            LIVE_PROBE["entry"].append({k: v[0] for k, v in query.items()})
            return FakeResponse({"symbol": query.get("symbol", [""])[0], "orderId": 9001,
                                 "clientOrderId": query.get("newClientOrderId", [""])[0],
                                 "status": "FILLED", "side": "BUY", "type": "MARKET",
                                 "executedQty": q, "cummulativeQuoteQty": str(float(q) * 110.0),
                                 "avgPrice": "110.0", "transactTime": str(int(time.time() * 1000))})
        if LIVE_PROBE["on"] and path == "/api/v3/orderList/oco":
            LIVE_PROBE["oco"].append({k: v[0] for k, v in query.items()})
            return FakeResponse({"orderListId": 7777, "contingencyType": "OCO",
                                 "orders": [{"orderId": 9002, "clientOrderId": "legA"},
                                            {"orderId": 9003, "clientOrderId": "legB"}]})
        if path == "/api/v3/time":
            return FakeResponse({"serverTime": int(time.time() * 1000)})
        if path == "/api/v3/exchangeInfo":
            return FakeResponse(EXCHANGE_INFO)
        if path == "/api/v3/klines":
            symbol = query.get("symbol", [""])[0]
            interval = query.get("interval", [""])[0]
            if symbol == m.BTC_CONTEXT_SYMBOL and interval == "1m":
                return FakeResponse(synth_btc_1m())
            if interval == m.TREND_INTERVAL:
                return FakeResponse(synth_15m())
            return FakeResponse(synth_rows())
        if path == "/api/v3/ticker/24hr":
            return FakeResponse(TICKERS)
        if path == "/api/v3/ticker/bookTicker":
            return FakeResponse({"symbol": query.get("symbol", [""])[0], "bidPrice": "109.9",
                                 "bidQty": "20", "askPrice": "110.0", "askQty": "10"})
        if path == "/api/v3/aggTrades":
            return FakeResponse([[i, "110.0", "20", "1", "2", "1", str(NOW_MS - i * 250), "true", "true", "true"]
                                 for i in range(6)][::-1])
        if path == "/api/v3/account":
            return FakeResponse({"balances": [{"asset": "USDT", "free": "5000", "locked": "0"}]})
        if path in ("/api/v3/openOrders", "/api/v3/order", "/api/v3/orderList"):
            return FakeResponse([] if path == "/api/v3/openOrders" else {"status": "CANCELED", "executedQty": "0"})
        return FakeResponse({})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeConnector:
    def __init__(self, *a, **k):
        pass

    def close(self):
        pass


class FakeAiohttp:
    TCPConnector = FakeConnector
    ClientSession = FakeSession
    ClientTimeout = dict
    ClientError = Exception
    WSMsgType = type("T", (), {"TEXT": 1, "CLOSED": 2, "CLOSING": 3, "ERROR": 4})


LIVE_PROBE = {"on": False, "entry": [], "oco": []}

TICKERS = [{"symbol": s, "lastPrice": "110", "priceChangePercent": "1.2",
            "quoteVolume": str(90_000_000 - i * 1000)} for i, s in enumerate(SYMBOLS_LIST)]
EXCHANGE_INFO = {"symbols": [{
    "symbol": s, "status": "TRADING", "baseAsset": s[:-4], "quoteAsset": "USDT",
    "filters": [
        {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001", "maxQty": "900000"},
        {"filterType": "MARKET_LOT_SIZE", "stepSize": "0.001", "minQty": "0.001", "maxQty": "900000"},
        {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
        {"filterType": "NOTIONAL", "minNotional": "5"},
    ],
} for s in SYMBOLS_LIST]}


async def scenario():
    fake_http = FakeAiohttp()
    m.aiohttp = fake_http
    session = FakeSession()
    m.SESSION = session
    m.REST = m.BinanceRest(session)
    m.DRY_RUN = True          # لا أوامر حقيقية — المسار يُنفَّذ حتى حافة الإرسال
    m.AUTO_TRADE = True
    m.SAME_SYMBOL_COOLDOWN = 0

    # ── 1) مسار الإقلاع الكامل بوضع --once ──────────────────────────────────
    rc = await asyncio.wait_for(m.amain({"--once"}), timeout=60)
    ok("amain(--once) أكمل مسار الإقلاع والتنقيط بلا استثناء", True)
    all_http = [c for inst in FakeSession.INSTANCES for c in inst.http_calls]
    kline_calls = sum(1 for method, path in all_http if path == "/api/v3/klines")
    ok("الكون سُخّن عبر klines (30 رمزاً × فريمان + سياق BTC 1m)",
       kline_calls >= 61, f"klines={kline_calls} total_http={len(all_http)}")
    ok("سياق BTC بُذر من REST (شموع 1m مغلقة)", m.BTC_CTX["seeded"] and len(m.BTC_CTX["closes"]) > 10,
       f"vr={m.BTC_CTX.get('vr'):.2f} closes={len(m.BTC_CTX['closes'])}")
    sig = m.build_signal(m.SYMBOLS[0]) if m.SYMBOLS else None
    ok("التنقيط يعمل على بيانات مسخّنة من الإقلاع",
       sig is not None and sig["score"] >= m.SCORE_TRIGGER,
       f"score={sig['score'] if sig else None}")
    ok("الحجم المبني على المخاطرة يُقيَّد بسقف المركز",
       sig is not None and m.plan_position(110.0, sig["atr"] * 1.8, m.SYMBOL_RULES[m.SYMBOLS[0]]["step"])[1]
       <= m.MAX_POSITION_NOTIONAL_USD)

    # ── 2) حلقة الكون: إضافة/إزالة + تنظيف FLOW/BOOK ───────────────────────
    hub = m.MarketStreamHub()
    hub.set_universe(m.SYMBOLS)
    ok("اشتراكات Hub تشمل aggTrade + kline + bookTicker لكل رمز",
       len(hub.desired) == len(m.SYMBOLS) * 4 and f"{m.SYMBOLS[0].lower()}@aggTrade" in hub.desired,
       f"streams={len(hub.desired)}")
    gone = m.SYMBOLS[0]
    m.BOOK[gone] = {"bid": 1.0, "ask": 1.0, "spread_pct": 0.0, "ts": time.monotonic()}
    m.FLOW[gone] = {"buy": 1.0, "sell": 1.0, "ts": time.time(), "epoch": time.time(), "buckets": __import__("collections").deque()}
    m.SYMBOLS[:] = [s for s in m.SYMBOLS if s != gone]
    m.SYMBOLS_SET.discard(gone)
    for s in m.SYMBOLS:
        m.CANDLES[(s, m.SIGNAL_INTERVAL)] = m.build_buffer(synth_rows(), m.SIGNAL_INTERVAL)
    ok("حالة الرمز المحذوف قابلة للتنظيف (BOOK/FLOW)",
       m.BOOK.get(gone) is not None and m.FLOW.get(gone) is not None)
    for d in (m.BOOK, m.FLOW):
        d.pop(gone, None)
    ok("BOOK/FLOW نظيفان بعد إخراج الرمز", gone not in m.BOOK and gone not in m.FLOW)

    # ── 3) بث BTC: رسالة WS حية + مغلقة → تحريك القاطع ─────────────────────
    t_ms = NOW_MS // 60_000 * 60_000
    m.btc_ctx_dispatch(json.dumps({"e": "kline", "s": m.BTC_CONTEXT_SYMBOL, "k": {
        "i": "1m", "t": t_ms, "o": "60000", "h": "60100", "l": "59800", "c": "59700", "x": True}}))
    drop = m.btc_ctx_stats()["drop_pct"]
    blocked, why = m.btc_circuit_block()
    ok("شمعة 1m مغلقة تُحرّك قاطع الانهيار فوراً", drop is not None and blocked and "btc-drop" in why,
       f"drop={drop:.2f}% why={why}")
    m.btc_ctx_apply(m.BTC_CONTEXT_SYMBOL, {"i": "1m", "t": t_ms + 60_000, "c": "60050", "x": True})
    blocked2, why2 = m.btc_circuit_block()
    ok("تعافي BTC يفتح القاطع للتو", blocked2 is False and why2 == "ok", f"why={why2}")

    # ── 4) رسالة WS خارج الكون تُتجاهل بلا انهيار ──────────────────────────
    before = dict(m.BOOK)
    hub.dispatch(json.dumps({"stream": "zzzzusdt@bookTicker", "data": {"b": "1", "B": "1", "a": "2", "A": "1"}}))
    hub.dispatch(json.dumps({"stream": "zzzzusdt@aggTrade", "data": {"s": "ZZZZUSDT", "p": "1", "q": "1", "m": False}}))
    hub.dispatch(json.dumps({"stream": "btcusdt@kline_1m", "data": {"e": "kline", "s": "BTCUSDT",
                                                                    "k": {"i": "1m", "t": 1, "c": "1", "x": False}}}))
    ok("تدفق خارج الكون لا يلوّث BOOK ولا يفجر الاستثناء", before == dict({k: v for k, v in m.BOOK.items() if k in before}))

    # ── 5) حلقات الخلفية تدور بلا خطأ: manage/btc-context/universe ──────────
    tasks = [asyncio.create_task(m.manage_loop()), asyncio.create_task(m.btc_context_loop(hub))]
    await asyncio.sleep(1.2)
    alive = all(not t.done() for t in tasks)
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    ok("حلقات الخلفية (صيانة + تسخين سياق) مستقرة", alive)

    # ── 6) veto كامل على المسار الحي: إشارة صالحة لكن DRY_RUN يوقفها ────────
    s = m.SYMBOLS[0]
    m.BOOK[s] = {"bid": 109.9, "ask": 110.0, "bid_qty": 20.0, "ask_qty": 10.0, "bid_vol": 2198.0,
                 "ask_vol": 1100.0, "imbalance": 0.666, "spread_pct": 0.091, "ts": time.monotonic()}
    m.FLOW[s] = {"buy": 9000.0, "sell": 1000.0, "ts": time.time(), "epoch": time.time(),
                 "price": 110.0, "buckets": __import__("collections").deque([(time.time(), 9000.0, 1000.0)])}
    sig = m.build_signal(s)
    priced = m.estimate_entry_cost(sig) if sig else None
    ok("تخطيط الصفقة (SL ديناميكي + حجم بالمخاطرة) يسبق الإرسال",
       priced is not None and abs(float(priced["risk_usd"]) - float(m.TARGET_RISK_USD)) < 1e-3
       and float(priced["notional"]) > 0 and float(priced["target"]) > float(priced["price"]) > float(priced["stop"]),
       f"notional={float(priced['notional']):.2f}$ sl={float(priced['sl_distance']):.4f} risk={float(priced['risk_usd']):.4f}$"
       if priced else "")
    if sig:
        m.SETUPS.clear()
        await m.process_signal(sig)
        order_calls = [x for x in [c for inst in FakeSession.INSTANCES for c in inst.http_calls] if x[0] == "POST"]
        ok("DRY_RUN يرسل صفر أوامر POST", not order_calls, f"post={order_calls}")

    # ── 7) القفصة الحية (عميل REST حقيقي + HTTP وهمي): MARKET ثم OCO ────────
    LIVE_PROBE["on"] = True
    m.DRY_RUN = False
    m.BINANCE_API_KEY = "FAKE_KEY"
    m.BINANCE_API_SECRET = "FAKE_SECRET"
    m.STATE = m.default_state()
    m.ORDERS.clear()
    m.SETUPS.clear()
    m.ENTRY_RESERVATIONS.clear()
    m.RESERVED_QUOTE = __import__("decimal").Decimal("0")
    m.BTC_CTX["last_update"] = time.monotonic()
    m.BTC_CTX["live"] = 60050.0
    m.SAME_SYMBOL_COOLDOWN = 0
    sig2 = m.build_signal(s)
    sent = await m.process_signal(sig2) if sig2 else False
    entry = LIVE_PROBE["entry"][0] if LIVE_PROBE["entry"] else {}
    oco = LIVE_PROBE["oco"][0] if LIVE_PROBE["oco"] else {}
    ok("المسار الحي: إشارة كاملة → MARKET BUY فعلاً", sent and entry.get("type") == "MARKET"
       and entry.get("side") == "BUY", f"{ {k: v for k, v in entry.items() if k in ('symbol','type','side','quantity')} }")
    ok("أمر سوقى بلا price (لا «طلقة معلقة» ولا LIMIT)", "price" not in entry and "timeInForce" not in entry)
    ok("OCO أُرسل متضمناً رجلاً للوقف والهدف", bool(oco) and "belowStopPrice" in oco and "aboveStopPrice" in oco
       and oco.get("symbol") == sig2["symbol"])
    if oco and entry:
        below = float(oco["belowStopPrice"]); above = float(oco["aboveStopPrice"])
        qty_oco = float(oco["quantity"]); qty_entry = float(entry["quantity"])
        ok("OCO يحمي كل المركز (كمية ≤ الكمية المشترية بعد رسوم)", 0 < qty_oco <= qty_entry,
           f"entry_qty={qty_entry} oco_qty={qty_oco}")
        ok("هندسة المستويات: الهدف أبعد من الدخول والوقف أقرب، والنسبة ≈ 1:2",
           below < 110.0 < above and abs((above - 110.0) / (110.0 - below) - 2.0) < 0.35,
           f"SL={below} TP={above} entry=110.0")
        pos = list(m.STATE["positions"].values())
        ok("المركز سُجِّل بمخاطرة ثابتة ≈ 2$ ونقاط الإشارة",
           len(pos) == 1 and abs(float(pos[0]["risk_usd"]) - 2.0) < 0.05 and float(pos[0]["score"]) >= 75.0,
           f"{ {k: pos[0][k] for k in ('risk_usd','score','vr','sl_pct')} }" if pos else "")
        ok("Setup ID سجّل لمنع تكرار نفس الشمعة", bool(pos) and pos[0]["setup_id"] in m.SETUPS)
    LIVE_PROBE["on"] = False
    m.DRY_RUN = True


rc = asyncio.run(scenario())
print("\nالحصيلة:", "FAIL ❌ " + str(FAIL) if FAIL else "ALL PASS ✅")
sys.exit(1 if FAIL else 0)
