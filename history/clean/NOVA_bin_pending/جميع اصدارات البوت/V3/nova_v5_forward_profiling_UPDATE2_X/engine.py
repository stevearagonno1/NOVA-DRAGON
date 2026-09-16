"""
NOVA v5 — المحرك الرئيسي (Orchestrator) + Telegram Interactive Wiring
=====================================================================
⚗️ BUILD: FORWARD PROFILING / EXHAUSTIVE LOGGING (zero-threshold)

تدفق لكل عملة (على إغلاق شمعة 1m):
  DATA → KAMA (اتجاه + قوة) — THE ONLY CORE TRIGGER
       → Naive-Bayes: evaluated & RECORDED only (entry floor forced to 0%)
       → تنفيذ Testnet لكل إشارة مولّدة + طباعة تشخيصية كاملة + تليجرام

Zero-threshold execution (this phase):
  • NOVA executes EVERY generated core signal (KAMA) on the Testnet regardless
    of its NB posterior. The legacy rule (Bull ≥ 55%, Diverged = veto) is no
    longer applied — it is only *measured*: for every signal we log what the NB
    score WAS and whether the legacy gate *would have* rejected it.
  • Flip back anytime: nb.ZERO_THRESHOLD_MODE = False, or set
    Config.nb_zero_threshold = False.

Exhaustive Termux console logging:
  Every evaluated signal prints its full journey:
    [DIAGNOSTIC] 🟡 SIGNAL: BTCUSDT | Trigger: KAMA | NB Score: 38.125% | Action: Executing LONG...
    [DIAGNOSTIC] 🔓 NB-BYPASS: ... | ✅ EXECUTED: ... | 🔒/📈 defense events |
    [DIAGNOSTIC] ⏹️ CLOSED: ... | ⏭️ SKIP/BLOCKED/REJECTED variants.

Telegram interactivity:
  • Boot pushes "🚀 NOVA HFT Engine Active" with an inline menu:
      [📊 Status] [📂 Open Positions] [⏸️ Pause/Resume]
      [📋 Trade Log (paginated 5–7 per page, Next ➡️ / ⬅️ Previous)]
      [📥 Download Full Log (.txt)] — uploads the exhaustive journal as a doc.
  • The Telegram long-poll loop runs as a concurrent asyncio task on the SAME
    event loop (created with asyncio.create_task) → it can never block or slow
    the Binance WebSocket streams. It only reads shared state and queues
    outbound messages.
  • Pause semantics: "paused" blocks NEW entries only; open positions remain
    fully managed (stop / trail / target / time-stop) exactly as before.

Persistence for the profiling phase:
  • state_file keeps positions + paused + trade-id counter (as before),
  • a sibling append-only JSONL journal (state_file + ".journal.jsonl")
    stores every closed trade's full anatomy so the history survives restarts
    and feeds the 📥 .txt export.
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
from telegram import (TelegramBot, coin, CB_STATUS, CB_POSITIONS, CB_PAUSE,
                      CB_LOG, CB_EXPORT, CB_MENU, CB_NOOP)
from indicators import AnchoredKAMA, atr
from nb import NaiveBayes, ZERO_THRESHOLD_MODE, LEGACY_NB_MIN_ENTRY_PROB
import risk as RISK


def _fmt_ts(t) -> str:
    try:
        return datetime.fromtimestamp(float(t)).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return "—"


def _fmt_px(v, dash: str = "—") -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return dash
    return f"{f:g}" if f > 0 else dash


def _num(v, default: float = 0.0) -> float:
    """Safe numeric coercion — corrupt hand-edited journal rows must render
    as defaults, never crash the export/log builders."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if f == f else default   # NaN → default


def _fmt_score(v, ready: bool = True) -> str:
    """Exact NB score (3 decimals on the 0–100 scale) or an explicit n/a."""
    if v is None:
        return "n/a (NB warm-up)" if not ready else "n/a"
    try:
        s = f"{float(v) * 100.0:.3f}%"
    except (TypeError, ValueError):
        return "n/a"
    return s + (" (NB warm-up)" if not ready else "")


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
        self.last_price = 0.0
        self.atr_value = 0.0
        self.kama = AnchoredKAMA(power=cfg.kama_power)
        self.nb = NaiveBayes(warmup=cfg.nb_warmup_labels, z_window=cfg.nb_z_window,
                             roc=cfg.nb_roc)
        self.nb_class = "unknown"        # أحدث تصنيف (من كل شمعة مغلقة — غير متحيز)
        self.nb_posts: Dict = {}
        self.bar_count = 0

    def push_bar(self, open_, high, low, close, volume):
        self.o.append(open_); self.h.append(high); self.l.append(low)
        self.c.append(close); self.v.append(volume)
        cap = 260
        for lst in (self.o, self.h, self.l, self.c, self.v):
            if len(lst) > cap:
                del lst[: len(lst) - cap]


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
        self.next_trade_id = 1           # monotonic id → journal + Telegram rows
        self._journal_total = 0          # rows persisted on disk (≥ in-memory view if capped)
        self._diag_ts: Dict[str, float] = {}   # anti-flood clock for SKIP lines
        self._load_state()
        self._load_journal()
        self.metrics = {"trades": 0, "fees": 0.0, "net_fees": 0.0}
        self.daily: Dict = {"date": None, "trades": 0, "wins": 0, "losses": 0, "net": 0.0}
        self.filters_hits: Dict[str, int] = {"macro": 0, "premium": 0, "epsilon": 0,
                                             "vol": 0, "swing": 0, "flow": 0, "nb": 0,
                                             "score": 0, "paused": 0,
                                             # ⚗️ forward-profiling counters:
                                             "kama": 0, "pos_open": 0, "blocked_live": 0,
                                             "cap": 0, "short_unsupported": 0}
        self._kline_queue: asyncio.Queue = asyncio.Queue()
        self._running = True
        if self._zero_threshold():
            print("⚗️" * 34)
            print("[engine] 🧪 FORWARD PROFILING ACTIVE — ZERO-THRESHOLD EXECUTION")
            print("[engine]    • NB entry floor forced to 0% (legacy was "
                  f"{LEGACY_NB_MIN_ENTRY_PROB * 100:.0f}%) + Diverged veto bypassed")
            print("[engine]    • EVERY generated core (KAMA) signal executes on Testnet")
            print("[engine]    • Exact NB score is recorded per trade (console/Telegram/journal)")
            print("[engine]    • Journal file: " + self._journal_path())
            print("⚗️" * 34)

    # ── وضع التشخيص ─────────────────────────────────────────
    def _zero_threshold(self) -> bool:
        """Zero-threshold master: Config.nb_zero_threshold overrides nb module."""
        return bool(getattr(self.cfg, "nb_zero_threshold", ZERO_THRESHOLD_MODE))

    def _journal_path(self) -> str:
        p = getattr(self.cfg, "journal_file", None)
        if p:
            return str(p)
        base = str(getattr(self.cfg, "state_file", "nova_state.json")) or "nova_state.json"
        return base + ".journal.jsonl"

    def _diag(self, msg: str):
        print(msg)

    def _diag_throttled(self, key: str, msg: str, every: float = 60.0):
        """Same SKIP reason for the same symbol repeats every 1m candle —
        print it at most once per `every` seconds to keep Termux usable."""
        now = time.time()
        if now - self._diag_ts.get(key, 0.0) >= every:
            self._diag_ts[key] = now
            print(msg)

    # ── واردات البيانات ──────────────────────────────────────
    def _on_trade(self, d: Dict):
        s = d["symbol"]
        st = self.state.get(s)
        if not st:
            return
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
        if close <= 0 or atr_value <= 0:
            return  # غير كافٍ بعد لحساب الوقف/الهدف

        # ── 1) KAMA — المحفّز CORE الوحيد في هذا الطور ────────
        st.kama.update(price)
        if st.kama.direction <= 0:
            self.filters_hits["macro"] += 1
            self.filters_hits["kama"] += 1
            return
        if st.kama.strength < cfg.kama_strength_min:
            self.filters_hits["macro"] += 1
            self.filters_hits["kama"] += 1
            return

        side = "LONG" if st.kama.direction > 0 else "SHORT"

        # ── 2) Naive-Bayes — تقييم وتسجيل فقط (zero-threshold) ──
        # (التدريب تم في _process_kline؛ هنا نقرأ الاحتمال المحسوب فقط)
        gate = self._nb_gate(st)

        # ── 3) 🔬 تشخيص شامل لكل إشارة مُقيَّمة (Termux console) ──
        score_txt = _fmt_score(gate["bull"], gate["ready"])
        self._diag(f"[DIAGNOSTIC] 🟡 SIGNAL: {st.symbol} | Trigger: KAMA | "
                   f"NB Score: {score_txt} | Action: Executing {side}...")
        if gate["zero_threshold"] and gate["why"]:
            self._diag(f"[DIAGNOSTIC] 🔓 NB-BYPASS: {st.symbol} — {gate['why']} "
                       f"| NB treated as OBSERVER (threshold = 0%) → executing anyway.")

        # Legacy-mode rejection (only reachable when zero-threshold is OFF).
        if gate["would_reject"]:
            self.filters_hits["nb"] += 1
            self._diag(f"[DIAGNOSTIC] ⛔ REJECTED: {st.symbol} | Trigger: KAMA | "
                       f"NB gate: {gate['why']}")
            return

        # ── 4) تنفيذ Testnet ─────────────────────────────────
        await self._open_trade(st, gate, side)

    def _nb_gate(self, st: SymbolState) -> Dict:
        """⚗️ Zero-threshold: NB is evaluated & recorded, NEVER rejecting.

        Returns a diagnostic dict carried all the way into the position and
        the journal: {zero_threshold, class, bull, bull_pct, ready, why,
        would_reject}. With zero-threshold ON, `would_reject` is always False
        and `why` explains what the LEGACY gate (Bull ≥ 55%, no Diverged)
        would have said — pure profiling information."""
        zero = self._zero_threshold()
        nb_class = st.nb_class or "unknown"
        bull: Optional[float] = None
        if st.nb_posts:
            try:
                bull = float(st.nb_posts.get("Bull", 0.0))
            except (TypeError, ValueError):
                bull = None
        legacy_min = float(getattr(self.cfg, "nb_min_entry_prob",
                                   LEGACY_NB_MIN_ENTRY_PROB))
        info: Dict = {"zero_threshold": zero, "class": nb_class,
                      "bull": bull,
                      "bull_pct": (bull * 100.0) if bull is not None else None,
                      "ready": bool(st.nb.ready),
                      "legacy_min_pct": legacy_min * 100.0,
                      "why": "", "would_reject": False}
        why = ""
        if nb_class == "Diverged":
            why = "class=Diverged (veto bypassed)" if zero else "Diverged veto"
        elif not st.nb.ready:
            why = (f"model warm-up {st.nb.labels_seen}/{st.nb.warmup} labels (bypassed)"
                   if zero else f"model warm-up {st.nb.labels_seen}/{st.nb.warmup} labels")
        elif bull is not None and bull < legacy_min:
            why = (f"Bull posterior {bull * 100.0:.3f}% < legacy floor "
                   f"{legacy_min * 100.0:.0f}% (bypassed)" if zero
                   else f"Bull posterior {bull * 100.0:.3f}% < {legacy_min * 100.0:.0f}% floor")
        if why and zero:
            why = why[0].upper() + why[1:]
        info["why"] = why
        if why and not zero:
            info["would_reject"] = True
        return info

    def _has_position(self, st: SymbolState) -> bool:
        """يمنع الدخول المكرر لنفس العملة بمركز مفتوح قائم."""
        return st.symbol in self.positions

    async def _open_trade(self, st: SymbolState, gate: Dict, side: str):
        cfg = self.cfg
        bull = gate.get("bull")
        score_txt = _fmt_score(bull, gate.get("ready", True))
        # ⏸️ Pause gate — يمنع الدخول الجديد فقط؛ المراكز المفتوحة تبقى مُدارة.
        if self.paused:
            self.filters_hits["paused"] += 1
            self._diag_throttled(
                f"paused:{st.symbol}",
                f"[DIAGNOSTIC] ⏭️ SKIP: {st.symbol} | Trigger: KAMA | NB Score: {score_txt} | "
                f"Action: SUPPRESSED — engine PAUSED (new entries off).")
            return
        if self._has_position(st):
            self.filters_hits["pos_open"] += 1
            cur = self.positions.get(st.symbol, {})
            self._diag_throttled(
                f"posopen:{st.symbol}",
                f"[DIAGNOSTIC] ⏭️ SKIP: {st.symbol} | Trigger: KAMA | NB Score: {score_txt} | "
                f"Action: SKIPPED — already holding #{cur.get('trade_id', '?')} "
                f"(no pyramiding; managing open position).", 120.0)
            return
        # SAFETY: the position manager (stop below entry / target above / trailing
        # ratchets up) is LONG-only. Today KAMA can only emit longs (direction>0
        # is hard-gated upstream), but if a future build ever yields a SHORT side,
        # refuse it loudly instead of managing it with the wrong exit formula.
        if side != "LONG":
            self.filters_hits["short_unsupported"] += 1
            self._diag(f"[DIAGNOSTIC] 🚫 BLOCKED: {st.symbol} | {side} signal — "
                       f"position manager is LONG-only; signal NOT executed.")
            return
        # Optional concurrency cap (default 0/unlimited — profiling wants ALL
        # signals executed; set Config.max_open_positions to throttle exposure).
        try:
            max_pos = int(getattr(cfg, "max_open_positions", 0) or 0)
        except (TypeError, ValueError):
            max_pos = 0
        if 0 < max_pos <= len(self.positions):
            self.filters_hits["cap"] += 1
            self._diag_throttled(
                f"cap:{st.symbol}",
                f"[DIAGNOSTIC] ⏭️ SKIP: {st.symbol} | Trigger: KAMA | NB Score: {score_txt} | "
                f"Action: SKIPPED — concurrent-positions cap reached "
                f"({len(self.positions)}/{max_pos}).", 120.0)
            return
        if not cfg.is_testnet:
            # يبقى مقيّداً بـ Testnet حصراً (M: مُقفل) — يُسجَّل في الكتاب ولا يُنفَّذ
            # (dedup: no position blocks re-firing, so record at most one row
            # per symbol per 5 min — else every trending bar appends + writes)
            last_blk = self._diag_ts.get(f"blocked:{st.symbol}", 0.0)
            if time.time() - last_blk < 300.0:
                return
            self._diag_ts[f"blocked:{st.symbol}"] = time.time()
            rec = {"t": time.time(), "symbol": st.symbol, "entry": 0.0,
                   "exit": 0.0, "qty": 0.0, "pnl": 0.0, "fee": 0.0,
                   "net": 0.0, "reason": "live disabled", "score": bull,
                   "nb": gate.get("class", "—"), "side": side, "trigger": "KAMA",
                   "trade_id": self.next_trade_id, "nb_ready": gate.get("ready"),
                   "nb_note": gate.get("why", ""), "zero_threshold": gate["zero_threshold"],
                   "status": "BLOCKED"}
            self.next_trade_id += 1
            self.trades_book.append(rec)
            self._append_journal(rec)   # persist too — BLOCKED rows survive restart like CLOSED ones
            self.filters_hits["blocked_live"] += 1
            self._save_state()
            self._diag(f"[DIAGNOSTIC] 🚫 BLOCKED: {st.symbol} | Trigger: KAMA | "
                       f"NB Score: {score_txt} | Action: RECORDED ONLY — live trading "
                       f"is disabled (testnet-only build). #{rec['trade_id']}")
            return
        entry = st.last_price or st.c[-1]
        plan = RISK.compute_stop_target(cfg, entry, st.atr_value)
        if not plan:
            self.filters_hits["score"] += 1
            self._diag(f"[DIAGNOSTIC] ⚠️ SKIP: {st.symbol} | Trigger: KAMA | "
                       f"NB Score: {score_txt} | Action: NO TRADE — risk plan unavailable "
                       f"(ATR/price invalid).")
            return
        qty = RISK.position_qty(cfg, 1.0, entry)   # حجم كامل — لا تدرّج بالنتيجة
        if qty <= 0:
            self._diag(f"[DIAGNOSTIC] ⚠️ SKIP: {st.symbol} | Trigger: KAMA | "
                       f"NB Score: {score_txt} | Action: NO TRADE — qty rounded to 0 "
                       f"(min notional?).")
            return
        tid = self.next_trade_id
        self.next_trade_id += 1
        # تسجيل المركز — كامل التشريح (anatomy) ليصل إلى الكتاب والتليجرام
        pos = {
            "entry": entry, "qty": qty, "stop": plan["stop"], "target": plan["target"],
            "stop_pct": plan["stop_pct"], "target_pct": plan["target_pct"],
            "open_time": time.time(), "score": bull, "nb": gate.get("class", "unknown"),
            "side": side, "trigger": "KAMA", "trade_id": tid,
            "nb_ready": gate.get("ready", False),
            "nb_note": gate.get("why", ""),
            "zero_threshold": gate["zero_threshold"],
            "atr_pct": (st.atr_value / entry * 100.0) if entry > 0 else 0.0,
            "confidence": bull if bull is not None else 0.0,   # ثقة NB (0–1)
            "be_armed": False, "trailing": False,
        }
        self.positions[st.symbol] = pos
        # Crash-safety: persist the OPEN trade immediately (a kill between entry
        # and close must not lose the position nor re-issue its trade_id).
        self._save_state()
        sig = {"symbol": st.symbol, "price": entry, "qty": qty,
               "side": side, "trigger": "KAMA", "trade_id": tid,
               "score": (bull * 100.0 if bull is not None else 0.0),  # 0–100
               "nb_score": bull,
               "tier": f"NB {(bull * 100.0) if bull is not None else 0.0:.1f}%"
                       + (" [zero-threshold]" if gate["zero_threshold"] else ""),
               "nb": gate.get("class", "unknown"),
               "nb_note": gate.get("why", ""),
               "zero_threshold": gate["zero_threshold"],
               "stop": plan["stop"], "target": plan["target"],
               "atr_pct": pos["atr_pct"],
               "displacement": 0.0}                 # لم يعد يُحتسب (لا MSS)
        self._diag(f"[DIAGNOSTIC] ✅ EXECUTED: {st.symbol} {side} @ {entry:g} | "
                   f"qty {qty:g} | Trigger: KAMA | NB {gate.get('class', '—')} "
                   f"{score_txt} | stop {plan['stop']:g} → target {plan['target']:g} "
                   f"| #{tid} — paper-ledger on Testnet prices "
                   f"(same execution path as before this phase).")
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
        if entry <= 0:
            # Corrupted/stale restored position (old state file) — refuse to
            # divide by zero; drop it from the book with a loud diagnostic.
            self.positions.pop(st.symbol, None)
            self._save_state()
            print(f"[DIAGNOSTIC] ⚠️ DROPPED: {st.symbol} — restored position has "
                  f"entry<=0 (corrupt state); removed from management.")
            return
        gain_pct = (price - entry) / entry * 100.0
        # Breakeven lock
        if not pos["be_armed"] and gain_pct >= cfg.breakeven_trigger_pct:
            pos["be_armed"] = True
            pos["stop"] = max(pos["stop"], RISK.break_even_lock_price(cfg, entry))
            self._diag(f"[DIAGNOSTIC] 🔒 {st.symbol} #{pos.get('trade_id', '?')}: "
                       f"breakeven armed — stop raised to {pos['stop']:g} "
                       f"(gain {gain_pct:+.2f}%)")
        # Trailing — لا يُفعَّل إلا إذا كانت ATR محمّلّة (وليس صفراً)
        if st.atr_value > 0:
            if not pos["trailing"] and gain_pct >= (cfg.trail_activation_atr * st.atr_value / entry * 100.0):
                pos["trailing"] = True
                self._diag(f"[DIAGNOSTIC] 📈 {st.symbol} #{pos.get('trade_id', '?')}: "
                           f"trailing engaged at gain {gain_pct:+.2f}%")
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

    async def _close_trade(self, st: SymbolState, exit_price: float, reason: str):
        pos = self.positions.pop(st.symbol, None)
        if not pos:
            return
        now = time.time()
        net = RISK.fee_net(self.cfg, pos["entry"] * pos["qty"], exit_price * pos["qty"])
        txn = {"t": now, "symbol": st.symbol, "entry": pos["entry"],
               "exit": exit_price, "qty": pos["qty"],
               "pnl": (exit_price - pos["entry"]) * pos["qty"],
               "fee": (pos["entry"] + exit_price) * pos["qty"] * (self.cfg.fee_bps / 10000.0),
               "net": net, "reason": reason, "score": pos.get("score", 0),
               "nb": pos.get("nb", "—"),
               # ⚗️ full anatomy (journal + Telegram log + .txt export):
               "trade_id": pos.get("trade_id"), "side": pos.get("side", "LONG"),
               "trigger": pos.get("trigger", "KAMA"), "status": "CLOSED",
               "open_t": pos.get("open_time"), "close_t": now,
               "hold_sec": max(0.0, now - float(pos.get("open_time", now))),
               "stop": pos.get("stop"), "target": pos.get("target"),
               "stop_pct": pos.get("stop_pct"), "target_pct": pos.get("target_pct"),
               "atr_pct": pos.get("atr_pct", 0.0),
               "nb_ready": pos.get("nb_ready", True), "nb_note": pos.get("nb_note", ""),
               "zero_threshold": pos.get("zero_threshold", True),
               "be_armed": pos.get("be_armed", False),
               "trailing": pos.get("trailing", False)}
        self.trades_book.append(txn)
        self._append_journal(txn)
        self.metrics["trades"] += 1
        self.metrics["fees"] += txn["fee"]
        self.metrics["net_fees"] += txn["net"]
        self._bump_daily(txn)
        self._save_state()
        win = "🟢 WIN" if net >= 0 else "🔴 LOSS"
        self._diag(f"[DIAGNOSTIC] ⏹️ CLOSED: {st.symbol} {txn['side']} #{txn.get('trade_id', '?')} | "
                   f"{win} | entry {pos['entry']:g} → exit {exit_price:g} | "
                   f"gross {txn['pnl']:+.4f}$ | fee −{txn['fee']:.4f}$ | NET {net:+.4f}$ | "
                   f"reason {reason} | held {txn['hold_sec']:.0f}s | "
                   f"NB at entry: {txn['nb']} {_fmt_score(txn['score'], txn['nb_ready'])}")
        await self.tg.send_async(self.tg.exit_message(txn))

    # ── الحالة / التخزين / الكتاب ────────────────────────────
    def _load_state(self):
        p = self.cfg.state_file
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    blob = json.load(f)
                self.positions = blob.get("positions", {})
                self.paused = bool(blob.get("paused", False))
                self.next_trade_id = int(blob.get("next_trade_id", 1)) or 1
                # id-safety: restored positions may hold ids ≥ the saved counter
                # (e.g. state saved by an older build) — never reuse an id.
                for p_ in self.positions.values():
                    if isinstance(p_, dict):
                        tid = p_.get("trade_id")
                        if isinstance(tid, int) and tid >= self.next_trade_id:
                            self.next_trade_id = tid + 1
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
                json.dump({"positions": self.positions, "paused": self.paused,
                           "next_trade_id": self.next_trade_id},
                          f, ensure_ascii=False)
        except Exception as exc:
            print(f"[state] تعذّر الحفظ: {exc}")

    def _load_journal(self):
        """استرجاع الكتاب append-only بعد إعادة التشغيل."""
        p = self._journal_path()
        if not os.path.exists(p):
            return
        loaded, skipped = 0, 0
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    self._journal_total += 1
                    try:
                        txn = json.loads(line)
                        # strict validation: rows must carry symbol + timestamp,
                        # anything older/corrupt is skipped (file stays as-is).
                        if (isinstance(txn, dict) and "symbol" in txn
                                and isinstance(txn.get("t"), (int, float))):
                            self.trades_book.append(txn)
                            loaded += 1
                            tid = txn.get("trade_id")
                            if isinstance(tid, int) and tid >= self.next_trade_id:
                                self.next_trade_id = tid + 1
                        else:
                            skipped += 1
                    except Exception:
                        skipped += 1
            self._trim_book()   # memory cap only — the file on disk stays the full record
            if loaded:
                extra = f", {skipped} corrupt row(s) skipped" if skipped else ""
                print(f"[journal] ♻️ loaded {loaded} closed trades from {p}{extra}")
        except Exception as exc:
            print(f"[journal] تعذّر التحميل: {exc}")

    def _trim_book(self):
        """Bound the in-memory journal view (Config.journal_max_rows, default
        4000). Keeps the NEWEST rows; the append-only .journal.jsonl file is
        the durable full history and is never trimmed here."""
        try:
            cap = int(getattr(self.cfg, "journal_max_rows", 4000) or 4000)
        except (TypeError, ValueError):
            cap = 4000
        if cap > 0 and len(self.trades_book) > cap:
            del self.trades_book[: len(self.trades_book) - cap]

    def _append_journal(self, txn: Dict):
        """كل صفقة مغلقة تُكتب فوراً — الكتاب لا يضيع بموت العملية."""
        try:
            p = self._journal_path()
            d = os.path.dirname(p)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(txn, ensure_ascii=False) + "\n")
            self._journal_total += 1
            self._trim_book()
        except Exception as exc:
            print(f"[journal] تعذّر الكتابة: {exc}")

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
                                  gov_paused, nb_acc, kama_ok=True,
                                  zt=self._zero_threshold())

    def _avg_nb_accuracy(self) -> float:
        """متوسط دقة Naive-Bayes عبر العملات المُدرَّبة (لا نكتفي بأول عملة)."""
        vals = [st.nb.audit_accuracy for st in self.state.values() if st.nb.audit_total > 0]
        if not vals:
            return 0.0
        return sum(vals) / len(vals)

    def _build_positions_pages(self) -> List[str]:
        """📂 Open Positions — live view with unrealized PnL, auto-PAGINATED.

        Zero-threshold profiling can hold one position per trending symbol;
        a single message would then blow past Telegram's 4096-char limit and
        get rejected. So: pure sync text-building over shared state (single
        event loop → safe), chunked into ≤3800-char pages, each queued as its
        own non-blocking send."""
        if not self.positions:
            return ["📂 <b>Open Positions</b>\n\n"
                    "No open positions right now.\n"
                    "The engine is scanning — you'll get an alert on every entry."]
        LIMIT = 3800
        header0 = f"📂 <b>Open Positions</b> — {len(self.positions)} open"
        blocks: List[str] = []
        total_unreal = 0.0
        now = time.time()
        for sym, pos in self.positions.items():
            pe = _num(pos.get("entry")); pq = _num(pos.get("qty"))
            if pe <= 0:
                continue  # corrupt restored state — skip view (manager drops it loudly)
            st = self.state.get(sym)
            price = _num((st.last_price if st else 0.0) or pe) or pe
            unreal = (price - pe) * pq
            pct = (price - pe) / pe * 100.0
            total_unreal += unreal
            icon = "🟢" if unreal >= 0 else "🔴"
            age = max(0, int(now - _num(pos.get("open_time"), now)))
            hh, mm = age // 3600, (age % 3600) // 60
            tags = []
            if pos.get("be_armed"):
                tags.append("BE🔒")
            if pos.get("trailing"):
                tags.append("TRAIL↗")
            sc = _fmt_score(pos.get("score"), pos.get("nb_ready", False))
            blocks.append(
                f"{icon} <b>{pos.get('side', 'LONG')} {coin(sym)}</b>  {pct:+.2f}%  ({unreal:+.4f}$)\n"
                f"   entry <code>{pe:g}</code> → last <code>{price:g}</code>"
                f" | qty <code>{pq:g}</code>\n"
                f"   stop <code>{_fmt_px(pos.get('stop'))}</code> | target <code>{_fmt_px(pos.get('target'))}</code>"
                f" | age {hh}h{mm:02d}m"
                + (f" | {' '.join(tags)}" if tags else "")
                + f"\n   #{pos.get('trade_id', '—')} · {pos.get('trigger', 'KAMA')} · NB {pos.get('nb', '—')} {sc}"
            )
        # greedy chunking: header + blocks per page
        pages: List[str] = []
        cur: List[str] = [header0, ""]
        cur_len = len(header0) + 1
        for b in blocks:
            if cur_len + len(b) + 1 > LIMIT and len(cur) > 2:
                pages.append("\n".join(cur))
                cur = [header0, ""]
                cur_len = len(header0) + 1
            cur.append(b)
            cur_len += len(b) + 1
        pages.append("\n".join(cur))
        footer = [f"Σ Unrealized (gross): <b>{total_unreal:+.4f}$</b>"]
        if self.paused:
            footer.append("⏸️ Engine is PAUSED — open positions stay managed, new entries disabled.")
        m = len(pages)
        out: List[str] = []
        for i, p in enumerate(pages):
            if m > 1:
                p = p.replace(header0, f"{header0}  ·  page {i + 1}/{m}", 1)
            if i == m - 1:
                foot = "\n".join(footer)
                if len(p) + len(foot) + 2 <= LIMIT:
                    p += "\n\n" + foot
                else:
                    out.append(p)
                    out.append(f"📂 <b>Open Positions</b> — summary\n{foot}")
                    continue
            out.append(p)
        return out

    def _build_positions_text(self) -> str:
        """Back-compat single-page view (first page only). Telegram routing
        uses _build_positions_pages(); this stays for any external caller."""
        return self._build_positions_pages()[0]

    # ── 📥 الكتاب الشامل → ملف .txt (Forward Profiling Journal) ─────────
    def _build_journal_text(self) -> str:
        """Exhaustive historical journal: header + summary + every executed
        and closed trade with its full anatomy + currently open positions.
        Plain text, fixed sections — meant to be read and grep-able."""
        book = self.trades_book
        closed = [r for r in book if _num(r.get("entry")) > 0]
        blocked = [r for r in book if _num(r.get("entry")) <= 0]
        W = 70
        L: List[str] = []
        line = lambda ch="═": L.append(ch * W)

        line("═")
        L.append("NOVA v5 — FORWARD PROFILING JOURNAL")
        L.append(f"Generated      : {_fmt_ts(time.time())}")
        L.append(f"Mode           : {'TESTNET' if self.cfg.is_testnet else 'LIVE'}"
                 f" | ⚗️ ZERO-THRESHOLD EXECUTION"
                 f" | NB entry floor: 0% (legacy {LEGACY_NB_MIN_ENTRY_PROB * 100:.0f}%)")
        L.append(f"Core trigger   : KAMA (direction + strength ≥ "
                 f"{self.cfg.kama_strength_min}) | NB = observer/recorder only")
        L.append(f"Engine state   : {'⏸️ PAUSED' if self.paused else '🟢 RUNNING'}"
                 f" | Universe: {len(self.state)} symbols")
        if self._journal_total > len(book):
            L.append(f"NOTE           : in-memory view capped to the newest {len(book)} "
                     f"of {self._journal_total} persisted rows (Config.journal_max_rows); "
                     f"full history stays in {self._journal_path()}")
        L.append("═" * W)

        # ── summary block ──────────────────────────────────────
        n = len(closed)
        wins = [r for r in closed if _num(r.get("net")) >= 0]
        losses = [r for r in closed if _num(r.get("net")) < 0]
        tot_gross = sum(_num(r.get("pnl")) for r in closed)
        tot_fee = sum(_num(r.get("fee")) for r in closed)
        tot_net = sum(_num(r.get("net")) for r in closed)
        wr = (len(wins) / n * 100.0) if n else 0.0
        best = max(closed, key=lambda r: _num(r.get("net"))) if closed else None
        worst = min(closed, key=lambda r: _num(r.get("net"))) if closed else None

        def _avg_scores(rows):
            vals = [_num(r["score"]) for r in rows if r.get("score") is not None]
            return (sum(vals) / len(vals) * 100.0) if vals else None

        L.append("")
        L.append("SUMMARY")
        L.append(f"  Recorded rows          : {len(book)}  "
                 f"(closed: {n} | blocked/recorded-only: {len(blocked)} | open: {len(self.positions)})")
        L.append(f"  Win / Loss             : {len(wins)} / {len(losses)}   (win rate {wr:.1f}%)")
        L.append(f"  Gross PnL              : {tot_gross:+.4f}$")
        L.append(f"  Fees (both sides)      : -{tot_fee:.4f}$   (@ {self.cfg.fee_bps:g} bps/side)")
        L.append(f"  NET PnL after fees     : {tot_net:+.4f}$")
        if best:
            L.append(f"  Best trade             : #{best.get('trade_id', '—')} {best['symbol']} "
                     f"{float(best.get('net', 0)):+.4f}$ ({best.get('reason', '—')})")
        if worst:
            L.append(f"  Worst trade            : #{worst.get('trade_id', '—')} {worst['symbol']} "
                     f"{float(worst.get('net', 0)):+.4f}$ ({worst.get('reason', '—')})")
        aw = _avg_scores(wins)
        al = _avg_scores(losses)
        if aw is not None or al is not None:
            L.append("  Profiling — avg NB score at entry (winners vs losers):")
            L.append(f"     winners: {('%0.3f%%' % aw) if aw is not None else 'n/a'}   "
                     f"losers : {('%0.3f%%' % al) if al is not None else 'n/a'}")
        L.append("─" * W)

        # ── closed trades ──────────────────────────────────────
        L.append("")
        L.append(f"CLOSED TRADES — {n}  (chronological; full anatomy per trade)")
        if not closed:
            L.append("  (none yet — every executed signal will appear here the moment it closes)")
        for r in closed:
            net = _num(r.get("net"))
            tag = "WIN 🟢" if net >= 0 else "LOSS 🔴"
            dur = r.get("hold_sec")
            dur_s = ""
            if dur is not None:
                s = int(_num(dur)); h, rem = divmod(s, 3600); m, ss = divmod(rem, 60)
                dur_s = f"{h}h{m:02d}m{ss:02d}s" if h else f"{m}m{ss:02d}s"
            L.append("")
            L.append(f"  TRADE #{r.get('trade_id', '—')} | {tag} | {r['symbol']} | {r.get('side', 'LONG')}")
            L.append(f"    Entry        : {_num(r.get('entry')):g}   @ {_fmt_ts(r.get('open_t') or r.get('t'))}")
            L.append(f"    Exit         : {_num(r.get('exit')):g}   @ {_fmt_ts(r.get('close_t') or r.get('t'))}"
                     + (f"   (held {dur_s})" if dur_s else ""))
            L.append(f"    Qty          : {_num(r.get('qty')):g}")
            L.append(f"    Trigger      : {r.get('trigger', 'KAMA')} — core signal"
                     + (" | executed under ZERO-THRESHOLD (no NB gate)"
                        if r.get("zero_threshold", True) else ""))
            L.append(f"    NB classifier: class={r.get('nb', '—')} | "
                     f"exact score={_fmt_score(r.get('score'), r.get('nb_ready', True))}"
                     + (f" | note: {r.get('nb_note')}" if r.get("nb_note") else ""))
            L.append(f"    Risk plan    : stop {_fmt_px(r.get('stop'))}"
                     f" ({_num(r.get('stop_pct')):+.2f}%) → "
                     f"target {_fmt_px(r.get('target'))}"
                     f" ({_num(r.get('target_pct')):+.2f}%) | ATR@entry "
                     f"{_num(r.get('atr_pct')):.2f}%")
            L.append(f"    Defense      : breakeven={'armed' if r.get('be_armed') else 'no'} | "
                     f"trailing={'engaged' if r.get('trailing') else 'no'}")
            L.append(f"    PnL          : gross {_num(r.get('pnl')):+.4f}$ | "
                     f"fee -{_num(r.get('fee')):.4f}$ | FINAL PnL (net) {net:+.4f}$")
            L.append(f"    Exit reason  : {r.get('reason', '—')}")
        L.append("")
        L.append("─" * W)

        # ── open positions ─────────────────────────────────────
        L.append("")
        L.append(f"OPEN POSITIONS (executed, not yet closed) — {len(self.positions)}")
        if not self.positions:
            L.append("  (none — all executed trades are closed)")
        else:
            now = time.time()
            for sym, pos in self.positions.items():
                pe = _num(pos.get("entry")); pq = _num(pos.get("qty"))
                if pe <= 0:
                    continue  # corrupt entry — skip rendering, manager guard handles removal
                st = self.state.get(sym)
                price = _num((st.last_price if st else 0.0) or pe) or pe
                unreal = (price - pe) * pq
                pct = (price - pe) / pe * 100.0
                age = int(max(0.0, now - _num(pos.get("open_time"), now)))
                L.append(f"  #{pos.get('trade_id', '—')} | {sym} | {pos.get('side', 'LONG')} | "
                         f"entry {pe:g} → last {price:g} ({pct:+.2f}%, {unreal:+.4f}$) | "
                         f"NB {pos.get('nb', '—')} {_fmt_score(pos.get('score'), pos.get('nb_ready', False))} | "
                         f"stop {_fmt_px(pos.get('stop'))} target {_fmt_px(pos.get('target'))} | "
                         f"age {age // 60}m | "
                         f"{'BE🔒' if pos.get('be_armed') else ''}"
                         f"{'TRAIL↗' if pos.get('trailing') else ''}".rstrip())
        if blocked:
            L.append("")
            L.append("─" * W)
            L.append(f"BLOCKED / RECORDED-ONLY ROWS (live-disabled etc.) — {len(blocked)}")
            for r in blocked:
                L.append(f"  #{r.get('trade_id', '—')} | {r['symbol']} | {r.get('side', 'LONG')} | "
                         f"NB {_fmt_score(r.get('score'), r.get('nb_ready', True))} | "
                         f"reason: {r.get('reason', '—')} | {r.get('nb_note', '')}")
        L.append("")
        L.append("═" * W)
        L.append("END OF JOURNAL — NOVA v5 forward-profiling build")
        L.append("═" * W)
        return "\n".join(L)

    async def _export_journal_document(self):
        """📥 Button handler: compile + upload the exhaustive .txt journal."""
        kb = self.tg.main_keyboard(self.paused)
        text = self._build_journal_text()
        n_closed = len(self.trades_book)
        n_open = len(self.positions)
        fname = "nova_forward_journal_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
        self._diag(f"[DIAGNOSTIC] 📥 JOURNAL EXPORT: {n_closed} recorded + {n_open} open "
                   f"→ {fname} ({len(text):,} chars)")
        if n_closed == 0 and n_open == 0:
            await self.tg.send_async(
                "📥 Journal is still empty — no signals have executed yet. "
                "The file will include every executed + closed trade once they do.", kb)
            return
        caption = (f"📒 <b>NOVA v5 — Forward Profiling Journal</b>\n"
                   f"• Recorded: {n_closed} | Open: {n_open}\n"
                   f"• Net after fees: <b>{self.metrics['net_fees']:+.4f}$</b>\n"
                   f"• ⚗️ Zero-threshold — every core signal executed, NB score recorded")
        ok = await self.tg.send_document(fname, text, caption)
        if not ok:
            await self.tg.send_async(
                "⚠️ Journal upload failed — see the Termux console for the Telegram API error.",
                kb)

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
            for ptext in self._build_positions_pages():
                await self.tg.send_async(ptext, kb)
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
        elif cmd == CB_EXPORT or cmd in ("export", "journal", "txt", "log.txt",
                                         "download"):
            await self._export_journal_document()
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
        if self._zero_threshold():
            print("[engine] 🧪 forward profiling: zero-threshold ACTIVE — "
                  "every core (KAMA) signal executes on Testnet")
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
            await self.tg.send_async("🛑 <b>NOVA HFT Engine stopped</b> — open positions + journal saved.")
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
