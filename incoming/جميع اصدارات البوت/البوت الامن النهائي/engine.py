"""
NOVA v5 — المحرك الرئيسي (Orchestrator) + Telegram Interactive Wiring
=====================================================================
يُنسّق كل المهام (WebSockets, فلاتر, NB, Scoring, تنفيذ, تليجرام) بحلقة asyncio واحدة.

تدفق لكل عملة (على إغلاق شمعة 1m):
  DATA → MACRO (KAMA+Welford, Premium/Discount, Epsilon, Volatility)
       → QUANT (Swing Death) + TRIGGER (Sweep→MSS→FVG)
       → Naive-Bayes (Diverged = فيتو) → Six-Factor Score → Size 0/50/100%
       → تنفيذ Testnet + تقرير تليجرام

Telegram interactivity (new):
  • On boot the engine pushes "🚀 NOVA HFT Engine Active" to CHAT_ID with an
    inline menu: [📊 Status] [📂 Open Positions] [⏸️ Pause/Resume].
  • The Telegram long-poll loop runs as a concurrent asyncio task on the SAME
    event loop (created with asyncio.create_task) → it can never block or slow
    the Binance WebSocket streams. It only reads shared state and queues
    outbound messages.
  • Pause semantics: "paused" blocks NEW entries only; open positions remain
    fully managed (stop / trail / target / time-stop) exactly as before.
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
from telegram import TelegramBot, coin, CB_STATUS, CB_POSITIONS, CB_PAUSE, CB_LOG, CB_MENU, CB_NOOP
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
        # ── Interactive-Telegram state ────────────────────────────
        self.paused = False              # True ⇒ no NEW entries (positions still managed)
        self._tasks: List[asyncio.Task] = []
        self._stop_event: Optional[asyncio.Event] = None
        self._stopped = False
        # إحصاءات الصفقات
        self.positions: Dict[str, Dict] = {}
        self.trades_book: List[Dict] = []
        self._load_state()
        self.metrics = {"trades": 0, "fees": 0.0, "net_fees": 0.0}
        self.daily: Dict = {"date": None, "trades": 0, "wins": 0, "losses": 0, "net": 0.0}
        self.filters_hits: Dict[str, int] = {"macro": 0, "premium": 0, "epsilon": 0,
                                             "vol": 0, "swing": 0, "flow": 0, "nb": 0,
                                             "score": 0, "paused": 0}
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
        # ⏸️ Pause gate — يمنع الدخول الجديد فقط؛ المراكز المفتوحة تبقى مُدارة.
        if self.paused:
            self.filters_hits["paused"] += 1
            return
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
                self.paused = bool(blob.get("paused", False))
                if self.paused:
                    print("[engine] استعادة الحالة: البوت متوقف مؤقتاً (paused) — "
                          "اضغط ▶️ Resume في تليجرام للاستئناف.")
            except Exception as exc:
                print(f"[state] تعذّر تحميل: {exc}")

    def _save_state(self):
        p = self.cfg.state_file
        try:
            d = os.path.dirname(p)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"positions": self.positions, "paused": self.paused},
                          f, ensure_ascii=False)
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
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    print(f"[engine] خطأ مركز {sym}: {exc}")

    async def _universe_loop(self):
        while self._running:
            await asyncio.sleep(self.cfg.universe_refresh_sec)
            try:
                await self.data.refresh_universe(force=True)
                self._sync_states()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[engine] خطأ تحديث الكون: {exc}")

    def _sync_states(self):
        for s in self.data.universe:
            if s not in self.state:
                self.state[s] = SymbolState(self.cfg, s)

    # ══════════════════════════════════════════════════════════
    # التليجرام التفاعلي — commands + inline buttons
    # ══════════════════════════════════════════════════════════
    async def _build_stats(self) -> str:
        gov_paused = [s.replace("USDT", "") for s, p in self.positions.items()]
        nb_acc = self._avg_nb_accuracy()
        return self.tg.stats_text(self.metrics, self.daily, self.filters_hits,
                                  gov_paused, nb_acc, kama_ok=True)

    def _avg_nb_accuracy(self) -> float:
        """متوسط دقة Naive-Bayes عبر العملات المُدرَّبة (لا نكتفي بأول عملة)."""
        vals = [st.nb.audit_accuracy for st in self.state.values() if st.nb.audit_total > 0]
        if not vals:
            return 0.0
        return sum(vals) / len(vals)

    def _build_positions_text(self) -> str:
        """📂 Open Positions — live view with unrealized PnL.
        Pure sync text-building over shared state (single event loop → safe),
        then one non-blocking queued send."""
        if not self.positions:
            return ("📂 <b>Open Positions</b>\n\n"
                    "No open positions right now.\n"
                    "The engine is scanning — you'll get an alert on every entry.")
        lines = [f"📂 <b>Open Positions</b> — {len(self.positions)} open", ""]
        total_unreal = 0.0
        now = time.time()
        for sym, pos in self.positions.items():
            st = self.state.get(sym)
            price = (st.last_price if st else 0.0) or pos.get("entry", 0.0)
            unreal = (price - pos["entry"]) * pos["qty"]
            pct = ((price - pos["entry"]) / pos["entry"] * 100.0) if pos.get("entry") else 0.0
            total_unreal += unreal
            icon = "🟢" if unreal >= 0 else "🔴"
            age = max(0, int(now - pos.get("open_time", now)))
            hh, mm = age // 3600, (age % 3600) // 60
            tags = []
            if pos.get("be_armed"):
                tags.append("BE🔒")
            if pos.get("trailing"):
                tags.append("TRAIL↗")
            lines.append(
                f"{icon} <b>{coin(sym)}</b>  {pct:+.2f}%  ({unreal:+.4f}$)\n"
                f"   entry <code>{pos['entry']:g}</code> → last <code>{price:g}</code>"
                f" | qty <code>{pos['qty']:g}</code>\n"
                f"   stop <code>{pos['stop']:g}</code> | target <code>{pos['target']:g}</code>"
                f" | age {hh}h{mm:02d}m"
                + (f" | {' '.join(tags)}" if tags else "")
            )
        lines.append("")
        lines.append(f"Σ Unrealized (gross): <b>{total_unreal:+.4f}$</b>")
        if self.paused:
            lines.append("⏸️ Engine is PAUSED — open positions stay managed, new entries disabled.")
        return "\n".join(lines)

    async def _handle_tg(self, upd: Dict):
        """Single entry point for every authorized Telegram update."""
        cb = upd.get("callback_query")
        if cb is not None:
            # 1) Ack FIRST → the user's client stops spinning even if routing fails.
            await self.tg.answer_callback(cb.get("id", ""))
            data = (cb.get("data") or "").strip()
            source = cb.get("message") or {}
            try:
                await self._route_command(data, source_message=source)
            except Exception as exc:
                print(f"[telegram] callback error: {exc}")
            return
        msg = upd.get("message")
        if msg is None:
            return
        txt = (msg.get("text") or "").strip()
        if not txt:
            return
        if txt.startswith("/"):
            txt = txt.split("@", 1)[0].lstrip("/")   # strip "/cmd@botname"
        try:
            await self._route_command(txt.lower())
        except Exception as exc:
            print(f"[telegram] command error: {exc}")

    async def _route_command(self, cmd: str, source_message: Optional[Dict] = None):
        kb = self.tg.main_keyboard(self.paused)
        if cmd in ("start", "menu", "help", "home", CB_MENU, "🏠"):
            # /start → (re)send the interactive menu
            await self.tg.send_async(self.tg.menu_text(), kb)
        elif cmd in ("status", "stats", "🔄", "📊", CB_STATUS):
            await self.tg.send_async(await self._build_stats(), kb)
        elif cmd in ("positions", "pos", "📂", "📂 open positions", CB_POSITIONS):
            await self.tg.send_async(self._build_positions_text(), kb)
        elif cmd == CB_PAUSE:
            await self._toggle_pause(source_message)
        elif cmd == "pause":
            if self.paused:
                await self.tg.send_async("⏸️ Engine is already paused.", kb)
            else:
                await self._toggle_pause(None)
        elif cmd == "resume":
            if not self.paused:
                await self.tg.send_async("▶️ Engine is already running.", kb)
            else:
                await self._toggle_pause(None)
        elif cmd.startswith("log") or cmd.startswith(CB_LOG):
            parts = cmd.split(":")
            try:
                page = int(parts[-1])
            except (ValueError, IndexError):
                page = 0
            text, log_kb = await self.tg.log_view(self.trades_book, page)
            await self.tg.send_async(text, log_kb)
        elif cmd == CB_NOOP:
            return  # decorative button (e.g. page indicator)
        else:
            await self.tg.send_async("❓ Unknown command — here is the menu:", kb)

    async def _toggle_pause(self, source_message: Optional[Dict] = None):
        """⏸️/▶️ Flip the entry gate. New entries stop; open positions keep
        being managed (stops/trails/targets). State persists across restarts.
        If the press came from the menu message, we edit that message in place
        so the button label flips live."""
        self.paused = not self.paused
        self._save_state()
        if self.paused:
            text = ("⏸️ <b>Engine PAUSED</b>\n"
                    "• New entries are disabled.\n"
                    "• Open positions remain fully managed "
                    "(stop / trail / target / time-stop).")
        else:
            text = ("▶️ <b>Engine RESUMED</b>\n"
                    "• New entries are enabled again.")
        kb = self.tg.main_keyboard(self.paused)
        sent = False
        mid = (source_message or {}).get("message_id")
        if mid:
            sent = await self.tg.edit_async(self.cfg.telegram_chat_id, int(mid), text, kb)
        if not sent:
            await self.tg.send_async(text, kb)
        print(f"[engine] paused={self.paused} (toggled via Telegram)")

    # ── تشغيل ────────────────────────────────────────────────
    async def run(self):
        await self.data.start()
        await self.exec.start()
        await self.tg.start()
        self._sync_states()

        # 🚀 Boot message + interactive menu (queued → non-blocking).
        await self.tg.send_boot(
            env="TESTNET" if self.cfg.is_testnet else "LIVE",
            universe=len(self.data.universe) or None,
            paused=self.paused,
        )

        # ربط تدفقات WebSocket لكل مجموعة رموز (دفعات لتجنّب طول الـ URL)
        batch = 15
        stream_tasks = []
        for i in range(0, len(self.data.universe), batch):
            chunk = self.data.universe[i:i + batch]
            stream_tasks.append(asyncio.create_task(self.data.stream_loop(chunk),
                                                    name=f"ws-{i // batch}"))
        self._stop_event = asyncio.Event()
        self._tasks = [
            asyncio.create_task(self._kline_worker(), name="kline-worker"),
            asyncio.create_task(self._position_loop(), name="position-loop"),
            asyncio.create_task(self._universe_loop(), name="universe-loop"),
            # 🔁 Telegram polling loop — concurrent with every WS stream on the
            # same loop; it only awaits aiohttp I/O and never touches the
            # market-data hot path.
            asyncio.create_task(self.tg.poll(self._handle_tg, self._stop_event),
                                name="tg-poll"),
        ] + stream_tasks
        print(f"[engine] ✅ تشغيل كامل — {len(self._tasks)} مهمة متوازية "
              f"(WebSockets + Telegram تفاعلي)")
        # Supervisor: if ANY task dies unexpectedly, surface it loudly and
        # return so main()'s finally → stop() tears the rest down cleanly
        # (بديل أفضل من gather المكتوم — لا نبقى نعمل بذاعة ناقصة بصمت).
        done, _pending = await asyncio.wait(self._tasks,
                                            return_when=asyncio.FIRST_COMPLETED)
        if not self._stopped:
            for t in done:
                exc = t.exception()
                if exc and not isinstance(exc, asyncio.CancelledError):
                    print(f"[engine] ⛔ مهمة '{t.get_name()}' توقفت: {exc!r} "
                          f"— سيتم الإيقاف النظيف")

    async def stop(self):
        if self._stopped:
            return
        self._stopped = True
        self._running = False
        if self._stop_event is not None:
            self._stop_event.set()          # ← كانت مفقودة سابقاً: الآن توقف الاستطلاع فعلياً
        try:
            await self.tg.send_async("🛑 <b>NOVA HFT Engine stopped</b> — open positions saved.")
        except Exception:
            pass
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._save_state()
        await self.tg.close()
        await self.exec.close()
        await self.data.close()
