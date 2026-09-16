"""
NOVA v5 — المحرك الرئيسي (Orchestrator)
=======================================
يُنسّق كل المهام (WebSockets, فلاتر, NB, Scoring, تنفيذ, تليجرام) بحلقة asyncio واحدة.

تدفق لكل عملة (على إغلاق شمعة 1m):
  DATA → MACRO (KAMA+Welford, Premium/Discount, Epsilon, Volatility)
       → QUANT (Swing Death) + TRIGGER (Sweep→MSS→FVG)
       → Naive-Bayes (Diverged = فيتو) → Six-Factor Score → Size 0/50/100%
       → تنفيذ Testnet + تقرير تليجرام
"""

from __future__ import annotations
import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

from config import Config
from data import BinanceData
from execution import BinanceExec
from telegram import TelegramBot
from indicators import AnchoredKAMA, EpsilonBand, atr, ema, premium_position
from quant import SwingDeath, VolatilityFilter
from trigger import detect_sweep, detect_mss, detect_fvg
from nb import NaiveBayes
from scoring import six_factor_score, size_multiplier, tier_label
import risk as RISK


class SymbolState:
    """حالة كل عملة: متسلسلات + فلاتر + نظيفة للعرض."""

    def __init__(self, cfg, symbol: str):
        self.cfg = cfg
        self.symbol = symbol
        self.o: List[float] = []
        self.h: List[float] = []
        self.l: List[float] = []
        self.c: List[float] = []
        self.v: List[float] = []
        self.buy_vol = 0.0
        self.sell_vol = 0.0
        self.last_price = 0.0
        self.atr_value = 0.0
        self.kama = AnchoredKAMA(power=cfg.kama_power)
        self.epsilon = EpsilonBand(fast=cfg.eps_mult, atr_period=cfg.eps_atr_period,
                                   range_n=cfg.eps_range)
        self.swing = SwingDeath(max_touches=cfg.swing_death_touches)
        self.volf = VolatilityFilter(hi_pct=cfg.vol_hi_pct, lo_pct=cfg.vol_lo_pct,
                                     lookback=cfg.vol_lookback)
        self.nb = NaiveBayes(warmup=cfg.nb_warmup_labels, z_window=cfg.nb_z_window,
                             roc=cfg.nb_roc)
        self.nb_class = "unknown"        # أحدث تصنيف (من كل شمعة مغلقة — غير متحيز)
        self.nb_posts: Dict = {}
        self.last_score = 0.0
        self.last_sig: Optional[Dict] = None
        self.bar_count = 0

    def push_bar(self, open_, high, low, close, volume):
        self.o.append(open_); self.h.append(high); self.l.append(low)
        self.c.append(close); self.v.append(volume)
        cap = 260
        for lst in (self.o, self.h, self.l, self.c, self.v):
            if len(lst) > cap:
                del lst[: len(lst) - cap]

    @property
    def flow_ratio(self) -> float:
        tot = self.buy_vol + self.sell_vol
        if tot <= 0:
            return 0.5
        return self.buy_vol / tot

    def frame(self) -> Dict:
        return {"o": self.o, "h": self.h, "l": self.l, "c": self.c, "v": self.v,
                "close": self.c[-1] if self.c else 0.0,
                "live": self.last_price or (self.c[-1] if self.c else 0.0),
                "atr": self.atr_value}


class NovaEngine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.state: Dict[str, SymbolState] = {}
        self.data = BinanceData(cfg, on_kline=self._on_kline,
                                on_trade=self._on_trade, on_book=self._on_book)
        self.exec = BinanceExec(cfg)
        self.tg = TelegramBot(cfg.telegram_token, cfg.telegram_chat_id, cfg)
        # إحصاءات الصفقات
        self.positions: Dict[str, Dict] = {}
        self.trades_book: List[Dict] = []
        self._load_state()
        self.metrics = {"trades": 0, "fees": 0.0, "net_fees": 0.0}
        self.daily: Dict = {"date": none(), "trades": 0, "wins": 0, "losses": 0, "net": 0.0}
        self.filters_hits: Dict[str, int] = {"macro": 0, "premium": 0, "epsilon": 0,
                                             "vol": 0, "swing": 0, "flow": 0, "nb": 0, "score": 0}
        self._kline_queue: asyncio.Queue = asyncio.Queue()
        self._running = True

    # ── واردات البيانات ──────────────────────────────────────
    def _on_trade(self, d: Dict):
        s = d["symbol"]
        st = self.state.get(s)
        if not st:
            return
        if d["delta"] > 0:
            st.buy_vol += d["qty"]
        else:
            st.sell_vol += d["qty"]
        st.nb.feed_delta(d["delta"])
        st.last_price = d["price"]

    def _on_book(self, d: Dict):
        s = d["symbol"]
        st = self.state.get(s)
        if st:
            st.last_price = (d["bid"] + d["ask"]) / 2.0

    def _on_kline(self, d: Dict):
        self._kline_queue.put_nowait(d)

    # ── المعالجة الرئيسية ────────────────────────────────────
    async def _process_kline(self, d: Dict):
        s = d["symbol"]
        st = self.state.get(s)
        if not st:
            return
        st.push_bar(d["open"], d["high"], d["low"], d["close"], d["volume"])
        st.bar_count += 1
        if len(st.c) < 30:
            return
        st.atr_value = atr(st.h, st.l, st.c) or st.atr_value
        atr_pct = (st.atr_value / st.c[-1] if st.c and st.c[-1] else 0.0) * 100.0
        # تدريب Naive-Bayes على كل شمعة مغلقة (غير متحيز) — تُحدَّث لكل بار،
        # ثم تُقرأ النتيجة لاحقاً في الـ pipeline دون إعادة تدريب.
        try:
            cls, posts = st.nb.bar_close(st.c[-1])
            st.nb_class = cls
            st.nb_posts = posts
        except Exception as exc:
            print(f"[engine] خطأ تدريب NB {st.symbol}: {exc}")
        return await self._run_pipeline(st)

    async def _run_pipeline(self, st: SymbolState):
        cfg = self.cfg
        price = st.last_price or st.c[-1]
        close = st.c[-1]
        atr_value = st.atr_value

        # ── 1) فلتر التقلب (Volatility) ──────────────────────
        atr_pct = (atr_value / close * 100.0) if close else 0.0
        st.volf.push(atr_pct)
        if not st.volf.all_clear(atr_pct):
            self.filters_hits["vol"] += 1
            return
        if atr_pct < cfg.min_atr_move_pct:
            self.filters_hits["vol"] += 1
            return

        # ── 2) KAMA (الاتجاه + القوة) ─────────────────────────
        st.kama.update(price)
        if st.kama.direction <= 0:
            self.filters_hits["macro"] += 1
            return
        if st.kama.strength < cfg.kama_strength_min:
            self.filters_hits["macro"] += 1
            return

        # ── 3) Epsilon Band (تصفية الضوضاء) ──────────────────
        st.epsilon.on_closed_bar(st.h[-1], st.l[-1], close, atr_value)
        step = st.epsilon.on_tick(price)
        if step == 0:
            self.filters_hits["epsilon"] += 1
            return

        # ── 4) Premium / Discount ────────────────────────────
        pos = premium_position(st.h, st.l, price, cfg.premium_window)
        if pos > cfg.premium_reject_pct:
            self.filters_hits["premium"] += 1
            return

        # ── 5) Swing Death ───────────────────────────────────
        if st.swing.is_dead(price, atr_value):
            self.filters_hits["swing"] += 1
            return

        # ── 6) محفّز الدخول (MSS + FVG) ──────────────────────
        frame = st.frame()
        mss = detect_mss(frame, cfg)
        if not mss:
            return
        fvg = detect_fvg(frame, cfg)
        if not fvg:
            return
        if price < fvg["mid"]:
            return

        # ── 7) تدفق الأوامر (aggTrade buy ratio) ─────────────
        st.buy_vol *= 0.95; st.sell_vol *= 0.95  # تلاشي النافذة
        flow = st.flow_ratio
        if flow < cfg.flow_buy_ratio_min and not st.nb.ready:
            self.filters_hits["flow"] += 1
            return

        # ── 8) Naive-Bayes (Diverged = فيتو) — نقرأ فقط (التدريب تم فوق) ──
        nb_class = st.nb_class
        nb_posts = st.nb_posts
        nb_bull = nb_posts.get("Bull", 0.0) if nb_posts else 0.0
        if nb_class == "Diverged":
            self.filters_hits["nb"] += 1
            return
        if st.nb.ready and nb_bull < cfg.nb_long_min:
            self.filters_hits["nb"] += 1
            return

        # ── 9) Six-Factor Score + الحجم ──────────────────────
        vol_ma = (sum(st.v[-20:]) / 20) if len(st.v) >= 20 else (st.v[-1] if st.v else 0.0)
        ema50 = ema(st.c, 50) or close
        dir_body = close - st.o[-1]
        pierce = max(0.0, (mss["prior_high"] - st.l[-1]))
        score = six_factor_score(
            cfg, bullish=True, high=st.h[-1], low=st.l[-1],
            open_=st.o[-1], close=close, atr_value=atr_value,
            volume=st.v[-1], vol_ma=vol_ma, ema50=ema50,
            touches=st.swing.log.get("touches", 1), pierce=pierce,
        )
        if score is None:
            return
        st.last_score = score
        mult = size_multiplier(cfg, score)
        st.last_sig = {"score": score, "tier": tier_label(score), "mult": mult,
                       "nb": nb_class, "nb_bull": nb_bull, "flow": flow}
        if mult <= 0:
            self.filters_hits["score"] += 1
            return

        # ── 10) إدارة الصفقة + تنفيذ Testnet ─────────────────
        await self._open_trade(st, score, mult, nb_class, nb_bull, flow, mss, fvg)

    async def _open_trade(self, st, score, mult, nb_class, nb_bull, flow, mss, fvg):
        cfg = self.cfg
        if not cfg.is_testnet:
            # يبقى مقيّداً بـ Testnet حصراً (M: مُقفل)
            self.trades_book.append({"t": time.time(), "symbol": st.symbol, "entry": 0.0,
                                     "exit": 0.0, "qty": 0.0, "pnl": 0.0, "fee": 0.0,
                                     "net": 0.0, "reason": "live disabled", "score": score,
                                     "nb": nb_class})
            return
        entry = st.last_price or st.c[-1]
        plan = RISK.compute_stop_target(cfg, entry, st.atr_value)
        if not plan:
            self.filters_hits["score"] += 1
            return
        qty = RISK.position_qty(cfg, mult, entry)
        if qty <= 0:
            return
        # تسجيل المركز (في testnet نقيّد بالحد الأدنى شرطاً تعليمياً)
        self.positions[st.symbol] = {
            "entry": entry, "qty": qty, "stop": plan["stop"], "target": plan["target"],
            "stop_pct": plan["stop_pct"], "target_pct": plan["target_pct"],
            "open_time": time.time(), "score": score, "nb": nb_class,
            "be_armed": False, "trailing": False,
        }
        sig = {"symbol": st.symbol, "price": entry, "qty": qty, "score": score,
               "tier": tier_label(score), "nb": nb_class,
               "stop": plan["stop"], "target": plan["target"],
               "atr_pct": st.atr_value / entry * 100.0,
               "displacement": mss.get("displacement", 0.0)}
        await self.tg.send_async(self.tg.entry_message(sig))

    # ── إدارة المراكز (على book ticker) ──────────────────────
    async def _manage_position(self, st: SymbolState):
        pos = self.positions.get(st.symbol)
        if not pos:
            return
        cfg = self.cfg
        price = st.last_price
        if price <= 0:
            return
        entry = pos["entry"]
        gain_pct = (price - entry) / entry * 100.0
        # Breakeven lock
        if not pos["be_armed"] and gain_pct >= cfg.breakeven_trigger_pct:
            pos["be_armed"] = True
            pos["stop"] = max(pos["stop"], RISK.break_even_lock_price(cfg, entry))
        # Trailing — لا يُفعَّل إلا إذا كانت ATR محمّلّة (وليس صفراً)
        if st.atr_value > 0:
            if not pos["trailing"] and gain_pct >= (cfg.trail_activation_atr * st.atr_value / entry * 100.0):
                pos["trailing"] = True
            if pos["trailing"]:
                trail_dist = cfg.trail_distance_atr * st.atr_value
                new_stop = price - trail_dist
                if new_stop > pos["stop"]:
                    pos["stop"] = new_stop
        # Exits
        reason = None
        if price <= pos["stop"]:
            reason = "Stop/Trail"
        elif price >= pos["target"]:
            reason = "Target"
        elif RISK.time_stop_due(cfg, time.time() - pos["open_time"], gain_pct,
                                pos["be_armed"], pos["trailing"]):
            reason = "TimeStop"
        if reason:
            await self._close_trade(st, price, reason)

    async def _close_trade(self, st, exit_price, reason):
        pos = self.positions.pop(st.symbol, None)
        if not pos:
            return
        net = RISK.fee_net(self.cfg, pos["entry"] * pos["qty"], exit_price * pos["qty"])
        txn = {"t": time.time(), "symbol": st.symbol, "entry": pos["entry"],
               "exit": exit_price, "qty": pos["qty"],
               "pnl": (exit_price - pos["entry"]) * pos["qty"],
               "fee": (pos["entry"] + exit_price) * pos["qty"] * (self.cfg.fee_bps / 10000.0),
               "net": net, "reason": reason, "score": pos.get("score", 0),
               "nb": pos.get("nb", "—")}
        self.trades_book.append(txn)
        self.metrics["trades"] += 1
        self.metrics["fees"] += txn["fee"]
        self.metrics["net_fees"] += txn["net"]
        self._bump_daily(txn)
        self._save_state()
        await self.tg.send_async(self.tg.exit_message(txn))

    # ── الحالة / التخزين ────────────────────────────────────
    def _load_state(self):
        p = self.cfg.state_file
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    blob = json.load(f)
                self.positions = blob.get("positions", {})
            except Exception as exc:
                print(f"[state] تعذّر تحميل: {exc}")

    def _save_state(self):
        p = self.cfg.state_file
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"positions": self.positions}, f, ensure_ascii=False)
        except Exception as exc:
            print(f"[state] تعذّر الحفظ: {exc}")

    def _bump_daily(self, txn):
        key = datetime.now().strftime("%Y-%m-%d")
        if self.daily.get("date") != key:
            self.daily = {"date": key, "trades": 0, "wins": 0, "losses": 0, "net": 0.0}
        self.daily["trades"] += 1
        self.daily["net"] += txn["net"]
        if txn["net"] >= 0:
            self.daily["wins"] += 1
        else:
            self.daily["losses"] += 1

    # ── المهام اللاحقة ──────────────────────────────────────
    async def _kline_worker(self):
        while self._running:
            try:
                d = await self._kline_queue.get()
                await self._process_kline(d)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[engine] خطأ معالجة الشمعة: {exc}")

    async def _position_loop(self):
        while self._running:
            await asyncio.sleep(1.0)
            for sym, st in list(self.state.items()):
                try:
                    await self._manage_position(st)
                except Exception as exc:
                    print(f"[engine] خطأ مركز {sym}: {exc}")

    async def _universe_loop(self):
        while self._running:
            await asyncio.sleep(self.cfg.universe_refresh_sec)
            await self.data.refresh_universe(force=True)
            self._sync_states()

    def _sync_states(self):
        for s in self.data.universe:
            if s not in self.state:
                self.state[s] = SymbolState(self.cfg, s)

    # ── التليجرام التفاعلي: أوامر/أزرار ──────────────────────
    async def _build_stats(self) -> str:
        gov_paused = [s.replace("USDT", "") for s, p in self.positions.items()]
        nb_acc = self._avg_nb_accuracy()
        return self.tg.stats_text(self.state, self.metrics, self.daily, self.filters_hits,
                                  gov_paused, nb_acc, kama_ok=True)

    def _avg_nb_accuracy(self) -> float:
        """متوسط دقة Naive-Bayes عبر العملات المُدرَّبة (لا نكتفي بأول عملة)."""
        vals = [st.nb.audit_accuracy for st in self.state.values() if st.nb.audit_total > 0]
        if not vals:
            return 0.0
        return sum(vals) / len(vals)

    async def _handle_tg(self, upd: Dict):
        txt = ""
        if upd.get("message") is not None:
            txt = (upd["message"].get("text") or "").strip()
        cb = upd.get("callback_query")
        if cb is not None:
            await self.tg.answer_callback(cb.get("id", ""))
            txt = (cb.get("data") or "").strip()
        try:
            if txt.startswith("log:"):
                page = int(txt.split(":")[1]) if ":" in txt else 0
                msg = await self.tg.log_page(self.trades_book, page)
                await self.tg.send_async(msg)
            elif txt in ("stats", "📊 الإحصاء", "🔄"):
                await self.tg.send_async(await self._build_stats())
            elif txt in ("help", "start", "🏠"):
                await self.tg.send_async(
                    "🤖 <b>NOVA v5</b> — ZERO-WAIT QUANT\n"
                    "• 📊 الإحصاء\n• 📋 سجل الصفقات\n• 🏠 القائمة",
                    [( [{"text": "📊 الإحصاء", "callback_data": "stats"},
                        {"text": "📋 سجل الصفقات", "callback_data": "log:0"}])])
        except Exception as exc:
            print(f"[telegram] خطأ معالجة أمر: {exc}")

    # ── تشغيل ────────────────────────────────────────────────
    async def run(self):
        await self.data.start()
        await self.exec.start()
        await self.tg.start()
        self._sync_states()
        # ربط تدفقات WebSocket لكل مجموعة رموز (دفعات لتجنّب طول الـ URL)
        batch = 15
        streams = []
        for i in range(0, len(self.data.universe), batch):
            chunk = self.data.universe[i:i + batch]
            streams.append(asyncio.create_task(self.data.stream_loop(chunk)))
        stop_event = asyncio.Event()
        tasks = [
            asyncio.create_task(self._kline_worker()),
            asyncio.create_task(self._position_loop()),
            asyncio.create_task(self._universe_loop()),
            asyncio.create_task(self.tg.poll(self._handle_tg, stop_event)),
        ] + streams
        await asyncio.gather(*tasks)

    async def stop(self):
        self._running = False
        self._save_state()
        await self.tg.close()
        await self.exec.close()
        await self.data.close()


def none():
    return None
