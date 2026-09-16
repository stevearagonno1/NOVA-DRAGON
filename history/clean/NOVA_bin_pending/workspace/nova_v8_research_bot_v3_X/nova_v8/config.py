"""NOVA_V8 — central configuration (single source of truth).

All tunable research / execution constants live here, derived from the final
design document (تصميم_NOVA_V8_النهائي.txt). Kept environment-driven where
needed (Termux-friendly).
"""
from __future__ import annotations

import os
from pathlib import Path

# ------------------------------------------------------------------ modes
MODE = os.getenv("NOVA_MODE", "backtest").lower()      # backtest | live
LOG_LEVEL = os.getenv("NOVA_LOG", "INFO").upper()

# ------------------------------------------------------------ target universe
SYMBOLS: tuple[str, ...] = (
    "BTCUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT", "XLMUSDT", "TONUSDT",
    "ATOMUSDT", "RENDERUSDT", "VETUSDT", "FILUSDT", "IMXUSDT", "HNTUSDT",
)
# historical aliases when loading archives (GRAM->TON, RNDR->RENDER)
SYMBOL_ALIASES: dict[str, tuple[str, ...]] = {
    "TONUSDT": ("GRAMUSDT", "GRAM"),
    "RENDERUSDT": ("RNDRUSDT",),
}

# -------------------------------------------------------------- data paths
ARCHIVE_DIR = Path(os.getenv("NOVA_ARCHIVE", "~/crypto_archive")).expanduser()
DATA_DIR = Path(os.getenv("NOVA_HOME", "~/nova_v8_out")).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = DATA_DIR / "research_results.csv"
REPORT_PATH = DATA_DIR / "final_report.txt"
STABILITY_PATH = DATA_DIR / "oracle_stability.txt"
FLIP_PATH = DATA_DIR / "slippage_flip_report.txt"
START_DATE = os.getenv("NOVA_START", "")               # e.g. "2021-01-01"
END_DATE = os.getenv("NOVA_END", "")                   # e.g. "2026-01-01"
MATRIX_CACHE_VER = 3                                   # bump on logic change

# ------------------------------------------------------------ financial rules
COMMISSION_PCT = 0.001        # 0.1% per side (entry and exit)
SLIPPAGE_PCT = 0.0003         # 0.03% on every market exit and stop fill
NOTIONAL_BASE = 20.0          # nominal $ per unit position (equal sizing)
# research is equal-positions per decision; real confidence sizing deferred to live
# slippage sensitivity tiers (% / side) used in the flip-point report
SLIPPAGE_TIERS = (0.0003, 0.001, 0.003)      # 0.03% / 0.10% / 0.30%
# volatility-driven spread model (execution realism for crises / thin liquidity)
SPREAD_MODE = "vol"                 # "const" | "vol"  (vol = widen with vol/shock)
SPREAD_HIGHVOL_VR = 1.2             # if VR (atr/atr_sma) above this -> widened spread
SPREAD_HIGHVOL_MULT = 2.0           # spread/slippage x this when VR high
SPREAD_SHOCK_MULT = 3.0             # spread/slippage x this in Shock/crisis

# ------------------------------------------------------------- memory policy
# process one symbol's full replay at a time then free memory
ONE_SYMBOL_AT_A_TIME = os.getenv("NOVA_ONE_SYMBOL", "1") == "1"

# ------------------------------------------------------------ timeframes
TF_TRADE = "1m"               # execution timeframe
TF_REGIME_CANDIDATES = ("5m", "15m")   # try both, pick truth (config flag)
REGIME_TF = os.getenv("NOVA_REGIME_TF", "15m")   # default higher TF

# ---------------------------------------------------- indicator parameters
RSI_LEN = 14
EMA_FAST, EMA_SLOW = 50, 200
BB_LEN, BB_STD = 20, 2.0
MACD_FAST, MACD_SLOW, MACD_SIG = 12, 26, 9
ADX_LEN = 14
STOCH_K, STOCH_D, STOCH_SMOOTH = 14, 3, 3
SUPERTREND_ATR, SUPERTREND_MULT = 10, 3.0
ATR_LEN = 14
ALMA_LEN, ALMA_OFFSET, ALMA_SIGMA = 200, 0.85, 5.0
RSI_FAST = 7
ATR_HYST = 53
HURST_LEN = 100
KAMA_BAND_K = 2.0

# ------------------------------------------------------ regime classification
VR_SHOCK = 1.5                # atr14 / atr_sma100 > 1.5 -> Shock
ADX_TREND = 22.0

# ------------------------------------------------------ market state tags
REGIME_BULL = "صاعد"          # Trending Bull
REGIME_BEAR = "هابط"          # Trending Bear
REGIME_CHOP = "عرضي"          # Choppy
REGIME_SHOCK = "متفجّر"       # Shock

# ------------------------------------------------------ directional exit engine
# hard stop
HARD_STOP_ATR_MULT = 1.15
HARD_STOP_MIN_PCT = 0.003     # never tighter than 0.30%
HARD_STOP_MAX_PCT = 0.030     # never wider than 3.0%
# break-even
BE_TRIGGER_ATR_MULT = 1.0     # lock when profit >= 1.0 * ATR
BE_LOCK_ATR_MULT = 0.45       # lift stop a touch above (relative to ATR)
# trailing (no fixed target)
TRAIL_ACT_ATR_MULT = 1.5      # activate trailing when profit >= 1.5 * ATR
TRAIL_PHASE1_DIST = 1.2       # distance in phase 1 (x ATR)
TRAIL_PHASE2_PROFIT = 2.5     # when peak profit >= 2.5 ATR switch phase2
TRAIL_PHASE2_DIST = 0.5       # tighter distance in phase 2 (x ATR)
# golden-ratio / Fibonacci retracement trail (directional mode, switchable)
#   basis "atr" keeps the classic ATR-distance trail above.
#   basis "fib" protects a *fraction of the achieved run* from its peak, using
#   the golden-ratio retracements — applied to a leg measured from entry to the
#   running peak (justified use of the golden ratio, not numerology).
TRAIL_BASIS = os.getenv("NOVA_TRAIL_BASIS", "fib").lower()  # atr | fib
FIB_ACT_ATR_MULT = 1.0        # start protecting once profit >= this x ATR
FIB_RETRACE_P1 = 0.618        # wide phase: give back up to 0.618 of the run
FIB_RETRACE_P2 = 0.382        # tight phase: give back only 0.382 (after run grows)
FIB_P2_TRIGGER = 2.0          # run >= this x ATR -> switch to the tight retrace
# time stop (~1 bar = 60 s at 1m)
TIME_STOP_BARS = 1
TIME_STOP_MIN_PROFIT_ATR = 0.25   # profit threshold relative to ATR

# directional trades only allowed in these regimes
TRADE_REGIMES = (REGIME_BULL, REGIME_BEAR)
CHOP_GRID_REGIMES = (REGIME_CHOP,)
# Shock -> avoid trading (wait for stability)

# ------------------------------------------------- 'good profit' for re-entry
# covers the cost of TWO round-trips + margin
GOOD_PROFIT_COST_COVER = 2.0      # x (entry+exit commission+slippage)
GOOD_PROFIT_MARGIN = 0.001        # +0.1% margin on top
# doubling chain cap (2x then 4x then stop)
MAX_DOUBLE_STEPS = 2              # 1 -> 2x ; 2 -> 4x ; >2 no new doubling
# chapter 6 "new signal" rule
REENTRY_ENABLED = True            # harvest-on-good-profit + doubling rule
# when a follow-up signal arrives while profit is small (not "good"), grant the
# open trade more time before its short time-stop fires (case b of ch6).
FOLLOWUP_TIME_GRACE_BARS = 30     # extra 1m bars of grace on each such signal
EXPERIMENT_NAME = os.getenv("NOVA_EXPERIMENT", "baseline")

# ------------------------------------------------------------- structure truth
TRUTH_WINDOW_MIN, TRUTH_WINDOW_MAX = 3, 5   # bars window for confirmation
TRUTH_ROLL = 5000                # recent rolling window (signals) for oracle
MIN_CONFIRM_SAMPLES = 40         # min observations before oracle "trusts"
# after a favourable structure break appears, it must be followed by a real
# profitable move to credit the indicator ("break succeeded financially").
TRUTH_PROFIT_EXTRA_BARS = 6      # scan these bars after the break
TRUTH_PROFIT_MIN_MOVE = 0.0      # min favourable close move (fraction) to credit
# hysteresis: a regime label must persist this many bars before it may change
# (prevents single-bar flicker); Shock is still allowed to appear immediately.
REGIME_HYSTERESIS_BARS = 3

# -------------------------------------------------------------- grid (choppy)
GRID_LEVELS_MIN, GRID_LEVELS_MAX = 6, 10
GRID_LEVELS_DEFAULT = 8          # levels per grid (clamped into MIN..MAX)
GRID_RANGE_LOOKBACK_BARS = 60 * 24      # ~1 day of 1m bars (range source)
GRID_RANGE_MIN_PCT = 0.005       # if range < 0.5% -> grid not worth it
GRID_RANGE_MAX_PCT = 0.06        # if range > 6% -> too wild, skip grid
GRID_MAX_OPEN_GRIDS_PER_SYMBOL = 1
GRID_CAPITAL_USD = 1000.0       # fixed $ deployed per grid (equal across cells)
# grid must run at least this many bars to count as a meaningful unit
GRID_MIN_LIFE_BARS = 30

# ------------------------------------------------------------------- BTC module
BTC_SYMBOL = "BTCUSDT"
BTC_CORR_WINDOW_BARS = 60 * 24 * 7     # 7-day rolling correlation window
BTC_CORR_MIN = 0.60                     # min corr to consider coin 'lagging'
BTC_EXCLUDE = {"HNTUSDT", "TONUSDT"}    # weak/independent per report (default)
BTC_MOVE_THRESH_PCT = 0.005             # BTC strong move threshold (0.5%)
BTC_STRUCTURE_CONFIRM = True            # require structure break on altcoin
BTC_STRUCTURE_ON_BTC = True            # (b) also require an MSS bullish break on BTC
BTC_DIRECTION = "long_only"             # per report: lag useful on up-moves only
# trailing profit exit for BTC-unit longs (per ch9c: "وقف حماية + تتبّع ربح")
BTC_TRAIL_ACT_ATR = 2.0                 # start trailing after gain >= this * ATR
BTC_TRAIL_DIST_ATR = 2.5                # trail distance behind watermark (x ATR)
# exit horizon per coin speed (bars at 1m). Defaults tuned at backtest.
BTC_EXIT_HORIZON_FAST = 60 * 24 * 3     # BNB/SOL ~ days
BTC_EXIT_HORIZON_MED = 60 * 24 * 20
BTC_EXIT_HORIZON_SLOW = 60 * 24 * 60    # XLM/VET/FIL ~ months
BTC_HORIZON_BY_COIN = {
    "BNBUSDT": BTC_EXIT_HORIZON_FAST,
    "SOLUSDT": BTC_EXIT_HORIZON_FAST,
    "LINKUSDT": 60 * 24 * 15,
    "ATOMUSDT": 60 * 24 * 20,
    "RENDERUSDT": 60 * 24 * 20,
    "XLMUSDT": BTC_EXIT_HORIZON_SLOW,
    "VETUSDT": BTC_EXIT_HORIZON_SLOW,
    "FILUSDT": BTC_EXIT_HORIZON_SLOW,
}
BTC_MIN_CORR_SAMPLES = 60 * 24 * 3     # warm-up for corr
# protective ATR stop for BTC-unit long positions (no fixed target there)
BTC_STOP_ATR_MULT = 3.0                 # exit if alt retraces >= 3x entry ATR
BTC_STOP_FALLBACK_PCT = 0.05            # fallback 5% stop if ATR not usable

# ------------------------------------------------------------------- trigger set
# each entry trigger has its own truth evaluator; a trigger opening a position
# tags the trade with its name.
ENABLE_TRIGGERS = os.getenv("NOVA_TRIGGERS", "all")  # "all" or comma names

# --------------------------------------------------------------- recording
# categories recorded independently in the report
CAT_DIRECTIONAL = "اتجاهي"
CAT_GRID = "شبكة"
CAT_BTC = "بيتكوين"

# milestone notifications (%) during research replay
PROGRESS_MILESTONES = (10, 25, 50, 75, 90, 100)

# ---------------------------------------------------------- telegram (research)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TG_POLL_TIMEOUT = 30
