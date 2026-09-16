"""
NOVA v5 — الإعدادات والسريّة (M0: الأمان)
==========================================
- يقرأ الأسرار من ملف `.env` فقط (لا أسرار في الكود).
- يحمّل كل القيم القابلة للمعايرة في CONFIG (قابل للتعديل عبر Backtest).

البند المُقفل من المستخدم:
  KAMA power=2 · EPS=2.8·ATR · Score 50/70/85 · NB>=0.70 · ~50 عملة · جلسات UTC · Net-after-fees.
"""

from __future__ import annotations
import os
from decimal import Decimal
from typing import Dict, Any


# ═══════════════════════════════════════════════════════════════
# أسماء البيئة المطلوبة
# ═══════════════════════════════════════════════════════════════
REQUIRED_ENV = (
    "BINANCE_ENV",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
)


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(float(os.environ.get(key, default)))
    except (TypeError, ValueError):
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, "").strip().lower()
    if not v:
        return default
    return v in {"1", "true", "yes", "y", "on"}


class Config:
    """حمّال الإعدادات + كل القيم القابلة للمعايرة (CONFIG)."""

    def __init__(self) -> None:
        # ── الأسرار (.env) ────────────────────────────────────
        self.binance_env: str = os.environ.get("BINANCE_ENV", "testnet").lower()
        self.api_key: str = os.environ.get("BINANCE_API_KEY", "")
        self.api_secret: str = os.environ.get("BINANCE_API_SECRET", "")
        self.telegram_token: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id: str = os.environ.get("TELEGRAM_CHAT_ID", "")
        self.auto_trade: bool = _env_bool("AUTO_TRADE", True)

        # ── التداول / المحفظة ─────────────────────────────────
        self.quote_asset: str = os.environ.get("QUOTE_ASSET", "USDT")
        self.trade_notional_usd: float = _env_float("TRADE_NOTIONAL_USD", 10.0)
        self.max_positions: int = _env_int("MAX_POSITIONS", 3)

        # ── قائمة العملات (M: مُقفل ~50 أعلى سيولة، تُحدَّث كل 10د) ──
        self.top_n_symbols: int = _env_int("TOP_N_SYMBOLS", 50)
        self.universe_refresh_sec: int = _env_int("UNIVERSE_REFRESH_SEC", 600)

        # ── الويب سوكيت / البيانات ────────────────────────────
        self.signal_interval: str = "1m"
        self.kline_limit: int = _env_int("KLINE_LIMIT", 220)
        self.max_closed: int = _env_int("MIN_CLOSED_CANDLES", 30)
        self.ws_heartbeat_sec: float = _env_float("WS_HEARTBEAT_SEC", 180)

        # ── M2: فلاتر الماكرو ─────────────────────────────────
        # KAMA (مُقفل power=2) + Welford
        self.kama_power: float = _env_float("KAMA_POWER", 2.0)
        self.kama_strength_min: float = _env_float("KAMA_STRENGTH_MIN", 0.5)
        # Premium/Discount (منطقة الغَلاء تُرفض > 50%)
        self.premium_reject_pct: float = _env_float("PREMIUM_REJECT_PCT", 50.0)
        self.premium_window: int = _env_int("PREMIUM_WINDOW", 50)
        # Epsilon (مُقفل 2.8·ATR)
        self.eps_mult: float = _env_float("EPS_MULT", 2.8)
        self.eps_atr_period: int = _env_int("EPS_ATR_PERIOD", 53)
        self.eps_range: int = _env_int("EPS_RANGE", 200)
        # Volatility Filter
        self.vol_hi_pct: float = _env_float("VOL_HI_PCT", 95.0)
        self.vol_lo_pct: float = _env_float("VOL_LO_PCT", 5.0)
        self.vol_lookback: int = _env_int("VOL_LOOKBACK", 1440)

        # ── M3: الكوانت ──────────────────────────────────────
        self.swing_death_touches: int = _env_int("SWING_DEATH_TOUCHES", 3)
        self.ms_sweep_win: int = _env_int("MSS_SWEEP_WIN", 12)
        self.ms_displace_atr: float = _env_float("MS_DISPLACE_ATR", 0.6)
        self.fvg_min_atr: float = _env_float("FVG_MIN_ATR", 0.2)
        self.fvg_lookback: int = _env_int("FVG_LOOKBACK", 8)
        self.mss_body_ratio: float = _env_float("MSS_BODY_RATIO", 0.55)
        self.mss_min_range_atr: float = _env_float("MSS_MIN_RANGE_ATR", 0.5)
        self.mss_lookback: int = _env_int("MSS_LOOKBACK", 20)
        self.mss_max_age: int = _env_int("MSS_MAX_AGE", 3)
        self.flow_buy_ratio_min: float = _env_float("FLOW_BUY_RATIO_MIN", 0.58)

        # ── M4: Naive-Bayes (مُقفل NB>=0.70 + Diverged فيتو) ──
        self.nb_warmup_labels: int = _env_int("NB_WARMUP_LABELS", 100)
        self.nb_long_min: float = _env_float("NB_LONG_MIN", 0.70)
        self.nb_high_tier: float = _env_float("NB_HIGH_TIER", 0.85)
        self.nb_z_window: int = _env_int("NB_Z_WINDOW", 50)
        self.nb_roc: int = _env_int("NB_ROC", 14)

        # ── M5: Six-Factor Scoring (مُقفل 50/70/85) ───────────
        self.score_reject: float = _env_float("SCORE_REJECT", 50.0)
        self.score_half: float = _env_float("SCORE_HALF", 70.0)
        self.score_full: float = _env_float("SCORE_FULL", 85.0)
        self.zw_weights = {  # أوزان Six-Factor (KB §4.1)
            "wick": 1.0, "atr": 1.0, "vol": 0.8, "body": 1.0, "ema": 0.6, "eq": 0.8,
        }

        # ── إدارة المخاطر (مُحافظة من v4.0.2) ─────────────────
        self.sl_min_pct: float = _env_float("SL_MIN_PCT", 0.30)
        self.sl_max_pct: float = _env_float("SL_MAX_PCT", 3.0)
        self.sl_atr_mult: float = _env_float("SL_ATR_MULT", 1.15)
        self.target_min_pct: float = _env_float("MIN_TARGET_PCT", 0.35)
        self.breakeven_trigger_pct: float = _env_float("BREAKEVEN_TRIGGER_PCT", 0.50)
        self.breakeven_lock_pct: float = _env_float("BREAKEVEN_LOCK_PCT", 0.45)
        self.trail_activation_atr: float = _env_float("TRAIL_ACTIVATION_ATR_MULT", 1.5)
        self.trail_distance_atr: float = _env_float("TRAIL_DISTANCE_ATR_MULT", 1.2)
        self.time_stop_sec: float = _env_float("TIME_STOP_SEC", 60.0)
        self.min_atr_move_pct: float = _env_float("MIN_ATR_MOVE_PCT", 0.08)
        self.min_volume_ratio: float = _env_float("MIN_VOLUME_RATIO", 1.2)
        self.gov_max_losses: int = _env_int("GOV_MAX_LOSSES", 3)
        self.gov_cooldown_sec: float = _env_float("GOV_SYMBOL_COOLDOWN", 600.0)
        self.order_budget_max: int = _env_int("ORDER_BUDGET_MAX", 40)
        self.max_spread_pct: float = _env_float("MAX_SPREAD_PCT", 0.20)
        self.fee_bps: float = _env_float("FEE_BPS", 20.0)  # ~0.20% ذهاباً وإياباً

        # ── Telegram ─────────────────────────────────────────
        self.daily_report_hour: int = _env_int("DAILY_REPORT_HOUR", 20)
        self.log_page_size: int = _env_int("LOG_PAGE_SIZE", 8)

        # ── عام ──────────────────────────────────────────────
        self.data_dir: str = os.environ.get("DATA_DIR", os.path.join(os.getcwd(), "data"))
        self.state_file: str = os.path.join(self.data_dir, "state.json")
        self.trades_file: str = os.path.join(self.data_dir, "trades.csv")

    # ── المساعدات ────────────────────────────────────────────
    @property
    def is_testnet(self) -> bool:
        return self.binance_env == "testnet"

    def as_dict(self) -> Dict[str, Any]:
        """كل القيم القابلة للمعايرة (بدون الأسرار) ليعرضها Backtest/الإحصاء."""
        skip = {"api_key", "api_secret", "telegram_token", "telegram_chat_id"}
        return {k: v for k, v in self.__dict__.items() if k not in skip}

    def validate(self):
        """فحص أن الجودة مقبولة: الأسرار موجودة، وبيئة التداول معروفة."""
        errs = []
        if not self.api_key or not self.api_secret:
            errs.append("مفتاحا Binance مفقودان (أدخلهما في .env)")
        if not self.telegram_token or not self.telegram_chat_id:
            errs.append("إعدادات تليجرام مفقودة (أدخلها في .env)")
        if self.binance_env not in ("testnet", "live"):
            errs.append(f"بيئة تداول غير معروفة: {self.binance_env!r} (توقّع testnet|live)")
        if self.binance_env == "live" and not self.auto_trade:
            errs.append("AUTO_TRADE=0 مع بيئة live: لا تداول — سيتوقف البوت.")
        return errs
