"""NOVA_V8 — central configuration (single source of truth).

All tunable research / execution constants live here, derived from the final
design document (تصميم_NOVA_V8_النهائي.txt). Kept environment-driven where
needed (Termux-friendly).
"""
from __future__ import annotations

import os
from pathlib import Path

# ------------------------------------------------------------------ modes
# MODE: "backtest" is the only implemented mode today. "live" is intentionally
# not implemented yet (live trading/training deferred by design).
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
DATA_QUALITY_MODE = os.getenv("NOVA_DATA_QUALITY_MODE", "warn").lower()  # warn|strict
DATA_MAX_GAP_MINUTES = int(os.getenv("NOVA_MAX_GAP_MINUTES", "5"))
RESULT_PATH = DATA_DIR / "research_results.csv"
REPORT_PATH = DATA_DIR / "final_report.txt"
STABILITY_PATH = DATA_DIR / "oracle_stability.txt"
FLIP_PATH = DATA_DIR / "slippage_flip_report.txt"
RISK_PATH = DATA_DIR / "portfolio_risk_audit.txt"
QUALITY_PATH = DATA_DIR / "data_quality_report.txt"
LONG_CYCLE_PATH = DATA_DIR / "long_cycle_report.txt"
MARKET_OPEN_PATH = DATA_DIR / "market_open_report.txt"
DYNAMIC_GRID_PATH = DATA_DIR / "dynamic_grid_report.txt"
DONCHIAN_PATH = DATA_DIR / "donchian_report.txt"
ADAPTIVE_TREND_PATH = DATA_DIR / "adaptive_trend_report.txt"
STRATEGY_SUMMARY_PATH = DATA_DIR / "strategy_sleeve_summary.txt"
START_DATE = os.getenv("NOVA_START", "")               # e.g. "2021-01-01"
END_DATE = os.getenv("NOVA_END", "")                   # e.g. "2026-01-01"
MATRIX_CACHE_VER = 5                                   # bump on logic change (TF_TRADE 1m->5m)

# ------------------------------------------------------------ financial rules
COMMISSION_PCT = 0.001        # 0.1% per side (entry and exit)
SLIPPAGE_PCT = 0.0003         # 0.03% effective market cost per side (base)
# Market-cost policy: Directional/BTC entries + exits and forced Grid flattening
# use the volatility-reactive effective proxy. Grid limit fills use commission
# only; no order-book spread is claimed without live depth data.
MARKET_COST_ON_ENTRY = True
NOTIONAL_BASE = 20.0          # nominal $ per unit position (equal sizing)
# Per-strategy portfolio notionals (user order 2026-09-10: every technique has
# its own dedicated portfolio). Defaults equal NOTIONAL_BASE so the research
# Baseline stays byte-identical; the per-portfolio execution mode rescales
# them from PER_PORTFOLIO_TOTAL_USD (see below).
DIRECTIONAL_NOTIONAL = NOTIONAL_BASE
MARKET_OPEN_NOTIONAL = NOTIONAL_BASE
BTC_NOTIONAL = NOTIONAL_BASE
# research is equal-positions per decision; real confidence sizing deferred to live
# slippage sensitivity tiers (% / side) used in the flip-point report
SLIPPAGE_TIERS = (0.0003, 0.001, 0.003)      # 0.03% / 0.10% / 0.30%
# volatility-driven *effective execution-cost* proxy (not measured order-book spread)
SPREAD_MODE = "vol"                 # "const" | "vol"  (vol = widen with vol/shock)
SPREAD_HIGHVOL_VR = 1.2             # if VR (atr/atr_sma) above this -> widened spread
SPREAD_HIGHVOL_MULT = 2.0           # spread/slippage x this when VR high
SPREAD_SHOCK_MULT = 3.0             # spread/slippage x this in Shock/crisis

# ------------------------------------------------------ strategy / risk policy
# Research starts in audit mode: all independent sleeves remain visible, while
# the guard reports which records would be blocked by portfolio limits. Strict
# filtering is available for a later combined-paper/live-like simulation; it is
# not silently allowed to change the historical baseline.
PORTFOLIO_RISK_MODE = os.getenv("NOVA_RISK_MODE", "audit").lower()  # audit|strict
PORTFOLIO_CAPITAL_USD = float(os.getenv("NOVA_PORTFOLIO_CAPITAL", "10000"))
RISK_MAX_GROSS_EXPOSURE_PCT = 0.60
RISK_MAX_SYMBOL_EXPOSURE_PCT = 0.15
RISK_MAX_STRATEGY_EXPOSURE_PCT = 0.40
RISK_MAX_OPEN_POSITIONS = 12
RISK_MAX_OPEN_PER_SYMBOL = 1
RISK_MAX_DRAWDOWN_PCT = 0.20
RISK_MAX_DAILY_LOSS_PCT = 0.05
RISK_HALT_ON_DATA_ERROR = True
NO_LEVERAGE = True
LIVE_TRADING_ENABLED = False

# ---------------------------------- per-strategy portfolios (all-active mode)
# User order (2026-09-10): every technique works with its OWN dedicated
# portfolio, and no strategy may be stopped or blocked. When this mode is on:
#   * ALL eight strategies always run (explicit selection is ignored);
#   * each strategy gets an equal slice of PER_PORTFOLIO_TOTAL_USD and trades
#     only with its own slice — its wins/losses never touch another portfolio;
#   * each slice is divided over the strategy's max concurrent units, so a
#     portfolio can never deploy more than its allocation;
#   * the risk guard stays in audit (observe-only) role — nothing is blocked.
# Off by default: the research Baseline (core selection + risk mode) is
# untouched. Same architecture carries to the later paper/live phase.
PER_PORTFOLIO_MODE = os.getenv("NOVA_PER_PORTFOLIO", "0") == "1"
PER_PORTFOLIO_TOTAL_USD = float(os.getenv("NOVA_PER_PORTFOLIO_TOTAL",
                                          str(PORTFOLIO_CAPITAL_USD)))
PER_PORTFOLIO_UNITS = {
    "directional": 12,        # max concurrent positions
    "grid": 12,               # one grid per symbol
    "btc_leadlag": 12,
    "market_open": 12,
    "long_cycle": 12,
    "dynamic_grid": 12,       # one unit per symbol
    "donchian": 24,           # two systems per symbol
    "adaptive_trend": 12,
}
PER_PORTFOLIO_PATH = DATA_DIR / "portfolios_report.txt"


# ------------------------------------------------------- independent sleeves
# These are deliberately not part of the default core Baseline.  They can be
# selected explicitly in research after their own self-checks.
LONG_CYCLE_ENABLED = os.getenv("NOVA_LONG_CYCLE", "0") == "1"
LONG_CYCLE_CAPITAL_USD = 1000.0
LONG_CYCLE_STAGE_WEIGHTS = (0.15, 0.25, 0.30, 0.30)
LONG_CYCLE_DAILY_LOOKBACK = 90
LONG_CYCLE_ZONE_BUFFER_PCT = 0.03
LONG_CYCLE_STAGE_GAP_PCT = 0.015
LONG_CYCLE_HARD_INVALIDATION_PCT = 0.08
LONG_CYCLE_CONFIRM_BARS_4H = 6

MARKET_OPEN_ENABLED = os.getenv("NOVA_MARKET_OPEN", "0") == "1"
MARKET_OPEN_DIRECTION = "long_only"  # conservative until instrument is agreed
MARKET_OPEN_PRE_MINUTES = 60
MARKET_OPEN_POST_MINUTES = 60
MARKET_OPEN_TIMEFRAME = "5min"
MARKET_OPEN_BREAK_BUFFER_ATR = 0.10
MARKET_OPEN_CHASE_BUFFER_ATR = 4.0
MARKET_OPEN_MAX_HOLD_BARS = 48      # 4 hours on 5m bars
MARKET_OPEN_TIME_STOP_BARS = 12     # 1 hour without meaningful progress
MARKET_OPEN_TIME_STOP_ATR = 0.25
MARKET_OPEN_TRAIL_ACT_ATR = 1.5
MARKET_OPEN_TRAIL_DIST_ATR = 1.0
MARKET_OPEN_SESSIONS = (
    ("Asia", "Asia/Tokyo", 9, 0),
    ("London", "Europe/London", 8, 0),
    ("NewYork", "America/New_York", 9, 30),
)

# ------------------------------------------------------------- memory policy
# process one symbol's full replay at a time then free memory
ONE_SYMBOL_AT_A_TIME = os.getenv("NOVA_ONE_SYMBOL", "1") == "1"

# ------------------------------------------------------------ timeframes
TF_TRADE = os.getenv("NOVA_TF_TRADE", "5m")   # execution timeframe (5m — was 1m; 1m costs eat edge)
# candidate higher timeframes for reading state; both are kept as candidates and
# the "truthful" one is chosen once historical data is available (design ch.3).
TF_REGIME_CANDIDATES = ("5m", "15m")
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
HURST_LEN = 100

# ---- RESERVED (not used by any module today) ----
# Kept explicitly so they are not mistaken for active parameters. They refer to
# indicator variants that were folded into the active set (regime hysteresis is
# now REGIME_HYSTERESIS_BARS; the "KAMA" trigger is a close-vs-ALMA filter).
#   ATR_HYST    = 53      # hysteresis window (superseded by REGIME_HYSTERESIS_BARS)
#   KAMA_BAND_K = 2.0     # KAMA band width (no true KAMA indicator implemented)

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
TRAIL_BASIS = os.getenv("NOVA_TRAIL_BASIS", "fib").lower()  # atr | fib | chandelier
FIB_ACT_ATR_MULT = 1.0        # start protecting once profit >= this x ATR
FIB_RETRACE_P1 = 0.618        # wide phase: give back up to 0.618 of the run
FIB_RETRACE_P2 = 0.382        # tight phase: give back only 0.382 (after run grows)
FIB_P2_TRIGGER = 2.0          # run >= this x ATR -> switch to the tight retrace
# Chandelier trail (variant basis "chandelier"). Stop hangs from the running
# peak at a fixed distance of CHANDELIER_ATR_MULT x ATR (regime-TF ATR, frozen
# at entry) and ratchets in the trade's favour only. Activation mirrors fib so
# the A/B vs fib isolates the trail shape. The LeBeau 22/3 classic is a daily-
# frame recipe; on 1m execution the 1m ATR is the wrong yardstick, so the
# distance uses the regime-TF ATR (same decision scale as the regime read).
CHANDELIER_ACT_ATR_MULT = 1.0   # activate trailing at profit >= this x ATR(1m)
CHANDELIER_ATR_MULT = 3.0       # distance behind the running peak (x ATR regime TF)
# time stop (~1 bar = 60 s at 1m)
TIME_STOP_BARS = 1
TIME_STOP_MIN_PROFIT_ATR = 0.25   # profit threshold relative to ATR

# ------------------------------------------- retest entry filter (variant)
# Anti-whipsaw entry filter for Directional (independent experiment; default
# OFF so the Baseline keeps entering at the trigger's next open). When ON, a
# new-signal entry is NOT taken at the next open; the engine waits for one of
# two confirmations, always decided on a CLOSED bar and executed at the NEXT
# bar's open (same no-lookahead model as everything else):
#   (1) RETEST: price runs beyond the trigger bar's close by more than the
#       tolerance, then pulls back to within RETEST_TOL_ATR_MULT x ATR(1m) of
#       that level, and a LATER closed bar closes back beyond it in the trade
#       direction (the breakout level "held");
#   (2) SECOND PULSE: a same-direction allowed trigger fires again before
#       expiry (a fresh momentum pulse in the same direction).
# The wait is aborted by: an opposite-direction trigger, a close back on the
# wrong side of the level beyond RETEST_INVALIDATE_ATR_MULT x ATR (the
# breakout failed), or expiry after RETEST_MAX_WAIT_BARS bars (no chase).
# The filter only gates fresh entries — the chapter-6 re-entry rule on an
# already-open position is untouched.
# Temporary assumptions (tolerance, invalidation, wait): uncalibrated; they are
# kept as flags for the later one-variable-at-a-time phase on real data.
RETEST_FILTER_ENABLED = os.getenv("NOVA_RETEST", "1") == "1"
RETEST_MAX_WAIT_BARS = 12          # give-up window (1m bars)
RETEST_TOL_ATR_MULT = 0.5          # retest tolerance (x ATR 1m at trigger)
RETEST_INVALIDATE_ATR_MULT = 1.0   # close beyond level by this (x ATR) = abort

# ---- per-regime exit overrides (design ch.5: "لكل حالة قيم قد تختلف") ----
# Every key is optional; anything omitted falls back to the global defaults
# above. Empty dicts now = a single unified profile, ready to be tuned per
# regime during the (deferred) one-variable-at-a-time optimisation phase.
# Recognised keys: hard_stop_mult, hard_stop_min, hard_stop_max, be_trigger,
# be_lock, trail_basis, trail_act, trail_p1, trail_p2, trail_p2_profit,
# fib_act, fib_p1, fib_p2, fib_p2_trigger, chand_act, chand_mult,
# time_bars, time_min_profit.
REGIME_EXIT_OVERRIDES: dict[str, dict] = {
    REGIME_BULL: {},
    REGIME_BEAR: {},
    REGIME_CHOP: {},
    REGIME_SHOCK: {},
}

# ------------------------------------------- Wyckoff/SMC entry gate (variant)
# Optional confirmation layer (spec 8.9/8.10) as a toggleable feature inside
# Directional and Long-Cycle (approved design: context features, no
# MSS/FVG/SFP duplication). When on, an entry additionally requires ALL of,
# on the decision bar's frame (1m for Directional, 4h for Long-Cycle):
#   1) SWEEP of the recent swing extreme with the close back inside (first);
#   2) the close in the discount (long) / premium (short) half of the range;
#   3) a prior SOS (long) / SOW (short) close beyond the window extreme
#   ("no entry before SOS"). Off by default; the Baseline is untouched.
# Temporary assumption: the lookback length.
SMC_GATE_ENABLED = os.getenv("NOVA_SMC_GATE", "0") == "1"
SMC_GATE_LOOKBACK = 50

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

# ------------------------------------------------- dynamic grid (DGT sleeve)
# Independent research variant of the static Grid sleeve (approved design:
# ATR spacing + cash reserve + limited conditional reset; detailed spec 8.7 of
# الملف الشامل الموحد). Outside the default Baseline — selected explicitly.
# The static Grid sleeve, the next-open execution model, and the cost model are
# untouched by this sleeve. Temporary assumptions (spacing scale, cooldown,
# stop) are kept as flags for the one-variable-at-a-time phase.
DYNAMIC_GRID_ENABLED = os.getenv("NOVA_DYNAMIC_GRID", "0") == "1"
DGT_CAPITAL_USD = float(os.getenv("NOVA_DGT_CAP", "1000.0"))  # $ per grid unit
DGT_LEVELS_MAX = int(os.getenv("NOVA_DGT_LEVELS", "16"))  # levels (cells = levels-1)
DGT_SPACING_ATR_MULT = 1.0           # k = ATR(regime TF) * mult / P
DGT_SPACING_MIN_PCT = 0.0025         # cost floor: a cell edge must clear the
                                     # round trip (2 commissions) + margin
DGT_MAX_UNITS_PER_SYMBOL = int(os.getenv("NOVA_DGT_UNITS", "1"))
DGT_BREAK_BUFFER_PCT = 0.02          # break when close leaves range by 2%
DGT_MAX_RESETS = 3                   # limited rebuilds per unit (approved)
DGT_RESET_COOLDOWN_BARS = 60         # min bars before a rebuild (anti-thrash)
DGT_STOP_NET_PCT = float(os.getenv("NOVA_DGT_STOP", "0.15"))  # hard unit stop
DGT_MIN_LIFE_BARS = 30
# Asymmetric mode (spec 8.7: "تكثيف بيع علوي في تحيز صاعد (والعكس)"): when on,
# each (re)build skews the cell capital toward the cells on the bias side —
# up-bias (price above the 15m EMA200) intensifies the UPPER sell cells, the
# reverse for a down-bias. Temporary assumption: bias magnitude 0.10.
DGT_ASYMMETRIC = os.getenv("NOVA_DGT_ASYMMETRIC", "0") == "1"
DGT_ASYM_BIAS = 0.10                 # +/- weight skew on the bias-side cells

# -------------------------------------------------------------- Donchian sleeve
# Classic Turtle-style Donchian breakout, LONG-ONLY, as an independent
# research sleeve and a public null-hypothesis mirror (breakouts vs the NOVA
# regime/trigger logic). Outside the default Baseline — explicit research
# selection only (--strategies donchian|all; NOVA_DONCHIAN documents intent).
# The 20/10 and 55/20 numbers are daily-frame Turtle lookbacks; on 1m
# execution the channels are computed on the regime TF (completed bars only,
# causal) — a temporary assumption, uncalibrated, kept as flags. Entry: a 1m
# close beyond the N-bar channel high, executed at the next open; exit: a 1m
# close below the M-bar channel low, executed at the next open. No pyramiding
# (one unit at a time per symbol/system); no new entries in Shock.
DONCHIAN_ENABLED = os.getenv("NOVA_DONCHIAN", "0") == "1"
# Daily-style channels (entry, exit) in REGIME_TF bars: 96x15m = 24h / 288x15m = 72h
# — the classic Turtle daily system; the old ((20,10),(55,20)) on 15m was noise.
_e1 = int(os.getenv("NOVA_DON_ENTRY1", "288"))   # الملك: sweep 80 تركيبة + هضبة
_x1 = int(os.getenv("NOVA_DON_EXIT1", "192"))
_e2 = int(os.getenv("NOVA_DON_ENTRY2", str(_e1 * 3)))
_x2 = int(os.getenv("NOVA_DON_EXIT2", str(_e1 // 2)))
DONCHIAN_SYSTEMS = ((_e1, _x1), (_e2, _x2))
DONCHIAN_CAPITAL_USD = 1000.0            # equal research notional per unit

# ---------------------------------------------------- Adaptive Trend sleeve
# Spec 8.2 "الاتجاه + الارتداد إلى القيمة" as an independent research sleeve
# (off by default; explicit selection). Gate/Setup/Trigger/Invalidation:
#   Gate:   4h EMA50 vs EMA200 + EMA50 slope + HH/HL (causal completed 4h bars)
#   Setup:  price pulled back into the 4h EMA20-EMA50 zone within the window
#   Trigger: a closed bar breaking the local-high close, bullish body, close in
#           the upper half (no long lower wick), volume >= its 20-bar average
#   Invalidation: stop under the pullback structure + ATR margin; then an
#           ATR trail behind the running peak (ch.8.2: follow with a trail)
#   Abstain:  over-extended from the trend average, or a dead narrow range
# Cost-aware turnover: entries carry the effective market cost on both sides,
# so a trigger that cannot clear the round-trip edge loses to it. Temporary
# assumptions (4h frame, lookbacks, ATR margins) are uncalibrated flags.
ADAPTIVE_TREND_ENABLED = os.getenv("NOVA_ADAPTIVE_TREND", "0") == "1"
# Spot is long-only (approved constraint): the short research side stays off
# unless explicitly enabled. Applied in adaptive_trend.py at side selection.
ADAPTIVE_TREND_ALLOW_SHORT = os.getenv("NOVA_AT_SHORT", "0") == "1"
ADAPTIVE_TREND_TF = "4h"                 # the trend frame (spec: H4 or H1)
ADAPTIVE_TREND_CAPITAL_USD = 1000.0      # equal research notional per unit
ADAPTIVE_TREND_PULLBACK_BARS = int(os.getenv("NOVA_AT_PB", "864"))  # 3 days on 5m (pullback needs days not hours)
ADAPTIVE_TREND_TRIGGER_BARS = int(os.getenv("NOVA_AT_TRIG", "12"))  # local-high lookback (5m bars)
ADAPTIVE_TREND_STOP_ATR = 0.5            # stop margin beyond the structure
ADAPTIVE_TREND_TRAIL_ATR = float(os.getenv("NOVA_AT_TRAIL", "5.0"))  # trail distance ×ATR-4h
ADAPTIVE_TREND_MAX_EXT_ATR = 3.0         # abstain when extended beyond this
ADAPTIVE_TREND_MIN_RANGE_PCT = 0.005     # abstain in dead narrow ranges (4h)

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
ENABLE_TRIGGERS = os.getenv("NOVA_TRIGGERS", "MACD,EMA,KAMA,OBV,ADX,Stochastic,SFP,MSS")  # elite set (A/B-verified: -79% cost bleed)

# --------------------------------------------------------------- recording
# categories recorded independently in the report
CAT_DIRECTIONAL = "اتجاهي"
CAT_GRID = "شبكة"
CAT_BTC = "بيتكوين"
CAT_LONG_CYCLE = "دورة-طويلة"
CAT_MARKET_OPEN = "افتتاح-سوق"
CAT_DYNAMIC_GRID = "شبكة-ديناميكية"
CAT_DONCHIAN = "دوناتشيان"
CAT_ADAPTIVE_TREND = "اتجاه-تكيفي"

# milestone notifications (%) during research replay
PROGRESS_MILESTONES = (10, 25, 50, 75, 90, 100)

# ---------------------------------------------------------- telegram (research)
TELEGRAM_TOKEN = __REDACTED__"TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TG_POLL_TIMEOUT = 30
