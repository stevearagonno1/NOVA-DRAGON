# Reverse-Engineered Trading Logic — Batch 2 — Distilled for a Tick-Based Binance Spot Engine

**Scope:** 20 Pine Script files (14,138 lines; 19 unique — `Delta zones.txt` is an exact duplicate of `Delta Reaction Zones.txt`, and `Breakout Lines + TPSL.txt` is byte-identical to `Breakout Lines.txt` except a trailing newline). Extracted: mathematical cores, state machines, volatility models, and scoring systems.
**Companion document:** `/home/user/hft_edge_extraction.md` (batch 1 — 46 concepts). This batch is organized with the same five focus areas; cross-references to batch 1 use `§n.n`.

**Red lines enforced — found in source, deliberately EXCLUDED from this document:**

| Excluded class | Where it appeared |
|---|---|
| `lookahead_on` / repaint variants | ELITE SMART + Clustering Clouds v2 (`securityNoRep` HTF branch), Eyops (`securityNoRep`, `sr_tf` request), ExProfit (`reso()`, `securityNoRep1`), DTC FX+ (daily-candle overlay — visual only). The *pattern* (read HTF state) is salvageable and is re-specified with confirmed values in §2.4 |
| Lagging indicator slow-crosses used as triggers | Edge Algo pro (RSI+MACD confluence), Cute Dragon (ST(11,4)+SMA13 cross), Fibonacci (HMA50 pump/dump snake, RSI 5/5 divergence), ExProfit Supertrend I/II as raw triggers (kept only as a nested-ratchet note), MACD bar-colorers (Eyops, ExProfit), StochRSI panel (Eyops) |
| Fixed-percentage risk ladders | DTC V1/V1.35 (0.25% SL), Eyops (0.2/0.5/7% TP ladder, 0.5% SL — structure kept as §4.5), ExProfit SAIYAN (same % ladder) |
| All GUI/table/label/drawing/alert-code | every file (incl. the `@mrexpert_ai` Telegram dashboard present in all 20 files) |
| Derivatives/leverage logic | Eyops Fx Premium (Zignaly futures JSON with `entryLeverage`, `exchangeAccountType: futures`; "10-20x leverage" alert text) — excluded in full |

**Tick-adaptation conventions:** identical to batch 1 — pivots traded as *forming* from the moment the left side completes; "break" = first aggTrade/bookTicker print crossing the level; `barstate.isconfirmed` = "1m kline closed"; SLOW STATE vs FAST PATH marked per concept.

---

## 1. WILDCARDS (Innovative / Non-Traditional Edges)

### 1.1 Log-Linear Pearson-R Adaptive Channel ("auto-period trend finder")
`source: ExProfit SuperTrend.txt (Adaptive Trend Finder, ×2 instances: short-term + long-term)`

The most statistically rigorous trend model in the batch. For each candidate window length, fit a line to **log-price** and keep the window with the **highest Pearson correlation**:

```python
# SLOW STATE — recompute every N bars (e.g. 5); each fit is O(L)
candidate_short = [20, 30, ..., 200]        # 19 windows, step 10
candidate_long  = [300, 350, ..., 1200]     # 19 windows, step 50

def loglin(y):            # y = ln(close) over the last L bars, y[0] = newest, x = 1..L (x=L newest)
    n = len(y)
    slope, intercept = lstsq(x=1..n, y)                     # OLS
    resid = y - (intercept + slope * x)
    sigma = sqrt(sum(resid**2) / (n - 1))                   # unbiased residual stdev
    R     = pearson(y, intercept + slope * x)               # trend "purity", |R| <= 1
    return slope, intercept, sigma, R

best = argmax_R over all candidate windows
# midline is the exponential of the fit: at current bar  M_now  = exp(intercept*)
#                                                     at start  M_start = exp(intercept* + slope* * (L* - 1))
# channel (MULTIPLICATIVE, log-space):
upper = M_now * exp(dev * sigma)      # dev = 2.0
lower = M_now * exp(-dev * sigma)
direction  = sign(slope*)
confidence = bucket(|R|):  <0.2 ExtremelyWeak ... 0.8 Moderate, 0.9 ModeratelyStrong,
                          0.94 Strong, 0.96 VeryStrong, 0.98 ExceptionallyStrong, else UltraStrong
# annualized trend rate (daily/weekly TFs only): CAGR = (close/close[L*-1])**(365/L*) - 1
```

**Mechanics:** A log-linear fit is a *constant compound-growth rate* model. Pearson-R against the fit measures how purely exponential the recent path has been — 0.95 means price has been a near-perfect geometric trend for that window, 0.6 means it has barely trended at all. Selecting `argmax_R` is a **change-point-free adaptive timescale**: the detector itself answers "how long has the current trend been running" by finding the window in which linearity is maximal. The residual σ, computed in log space, is a *relative* volatility, so the ±2σ channel width in price terms scales with price level automatically (a Keltner in log-space). The 12-bucket confidence label is a transparent quality tier.
**Why tick-powerful:** The full detector is 19 OLS fits of ≤1200 points — trivially amortizable: maintain rolling Σx, Σy, Σxx, Σxy, Σyy per window (O(1) per bar) and re-evaluate the argmax every 5 bars (<1 ms). Output to the fast path is four frozen numbers — `M_now` (recomputed as a one-point projection each tick: `M_tick = exp(intercept* + slope* * t)`), `upper`, `lower`, `direction` — plus the R-tier for sizing. "Price crosses the projected midline/channel edge" is a single comparison per tick, and unlike any MA it carries an explicit **confidence scalar** that no other batch concept provides. This is the batch's best *macro regime* primitive.

---

### 1.2 Volatility-Percentile SuperTrend (ATR-multiplier as a regime function)
`source: ELITE SMART.txt (Auto Sensitivity)`

The SuperTrend's ATR multiplier is not a constant — it is a piecewise function of where the current historical volatility sits relative to its own 55-bar mean:

```python
Hv    = YangZhang(log_ret, period=10, a=1.34)     # any of the 9 estimators, §4.1
avgHV = SMA(Hv, 55)
r = Hv / avgHV                                     # volatility position vs its own baseline
mult = (3.0  if r < 0.2     else
        2.85 if r < 0.6     else
        3.0  if r < 1.0     else
        3.15 if r < 1.4     else
        3.5  if r < 1.8     else
        3.6  if r < 2.4     else 4.0)
band = SuperTrend(ohlc4, factor=mult, len=10)
# signal: crossover/crossunder(close, band)
```

**Mechanics:** This is "band width follows the volatility regime" done with a lookup table instead of a continuous formula — and the table encodes a deliberate asymmetry: as volatility rises the multiplier widens *slowly* (3.0 → 4.0 across a 12× vol spread), while the quietest regime (r < 0.6) gets the *tightest* band (2.85–3.0). Effect: in calm tape the SuperTrend hugs price and flips fast (scalping mode); in expansion it stands back and only flips on genuine displacement (swing mode). The input to the table, `Hv/avgHV`, is dimensionless and regime-independent.
**Why tick-powerful:** One HV estimator + one 55-SMA + one division per bar. The multiplier changes rarely (bands are wide), so the SuperTrend state machine (§2.2-style ratchet) runs with a quasi-static factor; the flip fires on the cross tick as usual. It is a drop-in upgrade for any SuperTrend in the engine — the same idea also sizes the band of the *channel-breakout* engine in §3.8.

---

### 1.3 Outlier-Clamped Price Trend (input-censored REMA)
`source: Clear Trend Algo.txt`

The price series is **censored before smoothing**: each bar's close is clamped to within ±0.3·σ of the 5-bar WMA before feeding a 200-period double-WMA:

```python
sig5   = rolling_std(close, 5)
cprice = clip(close, WMA5 - 0.3*sig5, WMA5 + 0.3*sig5)   # spikes truncated to 0.3σ
REMA   = WMA(WMA(cprice, 200), 3)                        # 200-bar trend, double-smoothed
signal = sign(REMA - REMA_prev)                           # direction FLIP only
band   = REMA ± 0.1*ATR14                                 # trade band
SL     = 3 * ATR14
```

**Mechanics:** Capping the input at ±0.3σ of a 5-bar window strips wick-level and single-bar spike information from the trend estimate — the trend line can only move on *sustained* displacement, because a lone spike contributes at most 0.3σ to each affected average. The result is a 200-bar trend with the lag of a 200-WMA but the noise rejection of an outlier-filtered estimator (structurally similar to the MAD/median-based estimators in §4.1). Direction is a sign flip, so entries are edge-triggered, not state-held.
**Why tick-powerful:** The clamp is two comparisons per tick against a frozen (WMA5, σ5) pair; REMA is a maintained recurrence. The flip test is one comparison per tick, and `REMA ± 0.1·ATR14` are known-in-advance trigger prices — pre-placeable.

---

### 1.4 Body-Size Compression Detector (WMA-vs-EMA of bar bodies)
`source: Breakout Targets.txt`

Compression is defined as a *crossing of two different MA families over the bar-body size series*, not over price:

```python
body = |close - open|
compressed = crossunder(WMA(body, 99), EMA(body, 99))   # linear-weighted avg of bodies
                                                  # falls below exponential-weighted avg
# box: nearest pivot (49/49) anchors the range; box spans pivot -> running extreme
buffer = ATR(99) / 2
LONG  = close crosses above  box_top + buffer   (short mirror)
SL = 5 * ATR14;  TP = 0.5R / 1.0R / 1.5R
```

**Mechanics:** WMA and EMA of the same 99-window series are nearly equal in a steady regime; when bars are getting *relatively smaller* (bodies shrinking toward the recent tail), the recency-weighted EMA drops below the linear WMA first — the crossunder is a leading detector of body contraction. It is a compression gauge built from the bar *distribution itself*, orthogonal to ATR (which includes wicks) and to range-based squeezes. The ATR(99)/2 buffer around the pivot box rejects micro-breaks.
**Why tick-powerful:** Two maintained 99-term MAs on a 1-term-per-bar series. The cross event is bar-granular; the box edges are frozen levels — the fast path is `price > boxTop + buffer` per tick.

---

### 1.5 Streak-Climax Exhaustion Counter (trend exhaustion on consecutive same-side closes)
`source: Eyops Fx Premium.txt (`lele` function)`

```python
def lele(qual, len):
    # run counter: consecutive bars whose close is above its close 4 bars earlier
    run_up  += 1 while close > close[4]      (reset to 0 on any close <= close[4])
    run_dn  += 1 while close < close[4]
    TOP    = run_up > qual and close < open and high >= highest(high, len)   # then reset run_up
    BOTTOM = run_dn > qual and close > open and low  <= lowest(low,  len)    # then reset run_dn
major = lele(qual=13, len=40)     # 13-bar up-streak + bearish close at a 40-bar high  -> climax top
minor = lele(qual=5,  len=5)      # 5-bar streak + confirm candle at a 5-bar extreme  -> minor top
```

**Mechanics:** `close > close[4]` is a 4-bar momentum test per bar, so a run of 13 is *thirteen consecutive bars each above its own 4-bar-ago value* — a sustained, non-reverting up-drift. The climax fires only when three facts coincide: (a) the drift has been long enough (streak), (b) the current bar *closes against* the drift (reversal confirmation), (c) the bar prints a fresh N-bar extreme (the reversal happens exactly at the top, not mid-way). It is a change-point detector for momentum exhaustion with built-in confirmation — the counter-reset on fire prevents re-signaling.
**Why tick-powerful:** One counter + one comparison per bar; the extreme filter is a maintained rolling max/min. The confirmation candle can be watched live: the moment the forming bar's close is back against the drift at the extreme, the signal is knowable before bar close.

---

### 1.6 Violation-Tolerant Trend Lines (max-violation + grace bars)
`source: ExProfit SuperTrend.txt (Trend Lines, Supports and Resistances)`

Instead of "one touch kills the line", the line carries a **violation budget**:

```python
# uptrend line through two lowest-of (pivots 20/20), oldest lower than newest
violations = count of bars b in [created .. now - exceptBars] with low[b] < line(t_b)
#   exceptBars = 3  -> the 3 most recent bars are EXEMPT from counting (grace period)
if violations > maxViolation (default 0):  line = VIOLATED  (retired, no more signals)
BREAK SIGNAL: while line active:  low <= line(t_now)
# S/R variant: support from a pair of consecutive lows (lower of the two), resistance
# from a pair of consecutive highs; drawn only if historical violations <= maxViolation
```

**Mechanics:** A trendline in a liquid market gets wicked through on noise constantly; the classic "break on first touch" definition therefore produces mostly false breaks. Giving the line a tolerance — "it survives up to K violation bars, and the last G bars never count" — turns the line into a *statistical* object: only a break that persists beyond the line's noise envelope counts. With `maxViolation = 0` but `exceptBars = 3`, a single 1m wick-through still kills it (conservative); with `maxViolation = 1-2` it becomes a "2-strike" line. The same budget applies to horizontal S/R levels drawn from pivot pairs.
**Why tick-powerful:** Per line: one counter increment when `price < line(t)` (t = current bar index → line price is a linear function of bar index, O(1)) and a comparison against two constants. The break *event* (violation count exceeding budget, or a fresh touch of an active line) fires at the crossing tick. Lines are four floats each — a 20-line portfolio is 80 numbers and one pass per tick.

---

### 1.7 Session Drift Classifier + Persistent Session Extremes
`source: DTC.txt (DTC FX+ session engine)`

```python
sessions = NY 13:00-22:00Z, LONDON 07:00-16:00Z, TOKYO 00:00-09:00Z   # fixed UTC
on session start:  open_s = open of first bar
during session:    hi_s = max(high), lo_s = min(low)
# drift classification (range-relative, not fixed pips):
range_s = hi_s - lo_s
TREND_UP     = close > open_s + 0.3 * range_s
TREND_DOWN   = close < open_s - 0.3 * range_s
else SIDEWAYS
on session end:  persist hi_s / lo_s as horizontal levels,
                 active until broken (high/low cross) OR age > 2 days (48h expiry)
volume spike gate: V > 2.5 * SMA(V, 50), counted only INSIDE NY or LONDON
```

**Mechanics:** The drift test normalizes by the session's *own* range, so "trend day" means "closed in the top 30% of its own range" — scale-free across instruments and regimes. Persisting the session high/low as levels with an explicit 2-day lifetime models the real behavior (prior-session levels are the first place algorithms defend); the expiry prevents a stale level from being traded indefinitely. The session-gated volume filter encodes that volume only means something where participants are present.
**Why tick-powerful:** Three (open, hi, lo) triples maintained by max/min per tick; the classification is two comparisons per session bar. The persistent extremes are frozen trigger prices with a known TTL — ideal resting-order anchors (the batch's session profile §3.10 adds VWAP/POC/value-area to the same boxes).

---

### 1.8 Volatility-Inflection Regime Gate (ATR crossing its own EMA)
`source: Eyops Fx Premium.txt (Sideways Filtering)`

```python
a = ATR(5);  m = EMA(a, 5)
expanding   = a >= m        # ATR crossing UP through its 5-EMA  (volatility inflection)
contracting = a <= m
rsi_band    = (10 < RSI(7) < 45)
sideways    = contracting and rsi_band
# seven filter modes: ATR only / RSI only / OR / AND / none / sideways-OR / sideways-AND
# entry gate: SuperTrend(15, ×5) crossover AND selected trendType
```

**Mechanics:** The ATR is itself the signal: a 5-bar ATR crossing its 5-EMA is the earliest possible "volatility is turning" event (two short EMAs of the range — a volatility-EMA cross, the RSI-of-ATR idiom). The regime logic: entries taken while volatility is *contracting* and RSI sits in the mid-low band are mean-reversion entries (range market); entries while *expanding* are momentum entries. The 7-mode table makes the gate a single switchable boolean.
**Why tick-powerful:** Two 5-EMAs of TR — O(1). The flip is a cross event; per tick it is two comparisons that only matter at the flip. It is the cheapest "am I in range or trend" filter in the batch.

---

### 1.9 TTM Squeeze with Dwell-Time, ATR% and Volume Gates (5-condition compression)
`source: Fibonacci.txt (Market Regime Detector)`

```python
squeeze_on = BB(20, 2.0) strictly INSIDE KC(20, 1.5)          # classic TTM
          and ATR14 < 0.7 * SMA(ATR14, 20)                    # vol actually compressed
          and volume < SMA(volume, 20)                        # flow dried up
squeeze_regime = squeeze_on sustained >= 5 bars               # dwell time (no 1-bar blips)
release_bull = squeeze_on[1] and not squeeze_on and close > KC_upper   # expansion bar
release_bear = squeeze_on[1] and not squeeze_on and close < KC_lower
# regime precedence: SQUEEZE > TREND (EMA21>50, close>EMA200, ADX>20, 2×HH or 2×LL structure)
#                    > RANGE (|EMA21-EMA50|/price < 0.5% and ADX < 20) > NEUTRAL
```

**Mechanics:** Stock TTM Squeeze fires constantly on 1-bar BB-in-KC flickers. This version requires *five* independent facts: the geometric containment, an absolute volatility compression (ATR under 70% of its 20-bar mean), a volume dry-up, and a 5-bar dwell. The *release* is the signal — the first bar that exits the squeeze, classified by which Keltner edge it breaks — i.e., "the coiled state just released, and here is the direction".
**Why tick-powerful:** All components are maintained scalars (BB edges, KC edges, ATR14 + its SMA, volume SMA, a 5-bar counter). `squeeze_on` can flip only on bar data, but the *release detection* is live: during the forming bar, the moment price breaks KC_upper while the squeeze state was active on the last closed bar, the event is known — before close.

---

### 1.10 Absorption Bar and Volume-Climax Detector (flow-vs-displacement events)
`source: Fibonacci.txt (Synthetic Order Flow)`

```python
vol_ma = SMA(volume, 20)
absorption = V > 1.5*vol_ma and |close - open| < 0.3*ATR14    # big flow, NO displacement
climax     = V > 3.0*vol_ma and (high - low) > 1.5*ATR14      # big flow + displacement
# flow direction proxy (bar-level):
cum_delta += sign(close - close_prev) * V
delta_norm = SMA(cum_delta, 20) / SMA(V, 20)                   # bounded cumulative-flow gauge
```

**Mechanics:** The two detectors split large-volume bars by what the flow *did*: absorption (huge volume, body under 0.3 ATR) is the signature of a market order flow being **soaked** by passive liquidity — one side is giving up; climax (huge volume AND a 1.5 ATR range) is the signature of the *final* aggressive sweep that precedes exhaustion (use with §1.5). The distinction is exactly the microstructure question "did price move on this volume or not".
**Why tick-powerful:** Four maintained scalars; both events are fully determined by the forming bar's running (V, body, range) — evaluable mid-bar, so the engine can react at the moment the volume threshold crosses, not at close. The `delta_norm` term is the bar-level stand-in for the full delta engine in §3.1.

---

### 1.11 Consecutive-Pivot Trendline Chains with Time Expiry
`source: Breakout Lines.txt`

```python
pivots = 20/20
for each type (highs / lows):
    maintain the chain of CONSECUTIVE same-type pivots in proper order
    (support line: each new pivot low ABOVE the previous one; resistance: below)
line_k = line through (pivot_{k-1}, pivot_k), extended at its own slope
death:  close crosses the line  OR  line age > 500 bars
signal: the break itself (close-cross); SL = 1.5*ATR14; TP = 1R / 2R / 3R
```

**Mechanics:** Chaining *consecutive* pivots (rather than arbitrary pairs, as in §1.6/§3.8) means each line is a fresh structure leg — the chain is a self-renewing ladder of support/resistance trendlines, always anchored to the most recent confirmed pivot geometry. The 500-bar expiry retires lines that price has simply walked away from (a trendline 13 "days" old on 1m has no liquidity memory).
**Why tick-powerful:** Per side: a deque of the last two pivots + one line each. Line price at bar index t is linear in t — O(1) per tick. The break fires at the crossing tick of the *projected* line.

---

### 1.12 (Note) Smoothed Gaussian Trend Filter reappears
`source: Clustering Clouds v2.txt (embedded "AlgoAlpha" module)`

The Gaussian-cascade IIR (L=15, poles=3) + `linreg(22, offset=7)` flattening + ultra-tight `SuperTrend(line, 0.15, 21)` + slope-vs-band "ranging" state + `±2·SMA(|c−o|,100)` bands is **the same engine** already extracted in batch 1 §2.5 (from `2-1 strategy.txt` — same author family). No new math; the `pine_supertrend(final, 0.15, 21)` instance confirms the 0.15×ATR "whisper band" variant is used as a *state* (agree/disagree with the slope → ranging flag), not a signal.

---

## 2. MACRO DIRECTIONAL FILTERS (Low-Lag, Non-Repainting)

### 2.1 Six-EMA Full-Stack State Machine
`source: DTC_V1.txt, DTC V1.35.txt`

```python
E = [EMA(close, p) for p in (30, 35, 40, 45, 50, 60)]
stacked_up   = all(E[i] > E[i][1] for i in range(6))     # ALL six rising simultaneously
stacked_down = all(E[i] < E[i][1] for i in range(6))
entry_long_edge  = stacked_up   and not stacked_up[1]    # entering the stacked state
entry_short_edge = stacked_down and not stacked_down[1]
# V1.35 adds a 15m..1D EMA20/50 MTF *dashboard* (lookahead_off, display only — excluded)
# V1.35 risk: fixed 0.25% SL + 1..4R TPs (excluded — fixed % risk)
```

**Mechanics:** Requiring *all six* EMAs of a tightly-spaced band (30–60) to be rising is a much stricter trend test than any single MA stack ordering: every scale in the 30–60 window must agree on direction *right now* (slope, not position). The edge trigger (entering the state, not being in it) converts a state into a rare event — the market must align six correlated series in the same bar, which is essentially "a clean impulse just happened". The spacing (Δ5) means the stack is sensitive: one lagging scale kills the stack, so the state is genuinely all-or-nothing.
**Why tick-powerful:** Six maintained EMAs; the test is six comparisons per bar (once per tick if desired — EMAs update per tick from the live close). The edge fires at the first bar where the sixth EMA turns — no confirmation lag by construction.

---

### 2.2 Nested Double-SuperTrend Ratchet (major/minor with dip-breakout)
`source: Double SuperTrend.txt`

```python
minor = SuperTrend(ATR(10), mult = 3.0)     # fast ratchet
major = SuperTrend(ATR(14), mult = 6.0)     # slow, wide ratchet (2× width, longer ATR)
LONG  = minor flips UP  AND major already UP      # pullback finished inside a major uptrend
BUY_DIP = major UP  AND minor just flipped DOWN   # the dip itself = re-entry signal
# short mirror (minor flips down while major down)
```

**Mechanics:** Two ratchets at different volatility scales form a *hierarchy*: the major band defines the regime (a 6×ATR14 band only flips on a full trend reversal), the minor band defines the entry timing (3×ATR10 flips on pullbacks). The `BUY_DIP` rule is the interesting inversion: the minor's *downward* flip inside a major uptrend is not an exit — it is the *pullback entry* (the dip that is expected to end when the minor flips back up). Same nested-ratchet pattern, noted as a reoccurrence, in ExProfit (ST(14,×3) entries / ST(3,×3) exits) and ELITE (ST(ohlc4, sensitivity, 10) + trendcloud ST(4/7)).
**Why tick-powerful:** Two standard ratchet state machines (each O(1) per tick); the entry is a state pair, and the flip events fire at the cross tick. The minor's down-flip inside a major-up state is a *known-in-advance* expectation object: once it fires, the target (minor's upward flip) is a defined event the fast path waits for.

---

### 2.3 ZLEMA Trend with Max-ATR Hysteresis (extreme-volatility gate)
`source: Combined Algo v5.txt`

```python
L = 70
zlema = EMA(x + (x - x[(L-1)//2]), L)               # zero-lag EMA (lag = (L-1)/2)
V = 1.2 * highest(ATR(L), 3*L)                       # = 1.2 × max ATR over last 210 bars
state = +1  if close > zlema + V
      = -1  if close < zlema - V
      = hold previous otherwise                       # hysteresis deadband of width 2V
```

**Mechanics:** ZLEMA removes the (L−1)/2 lag of the raw EMA by forward-projecting the input — a low-lag trend line. The innovation is the **hysteresis deadband**: the state only changes when price is displaced from the ZLEMA by more than `1.2 × the maximum ATR seen in the last 3L bars`. The max (not the mean) ATR over 210 bars is a *ceiling on recent extreme volatility* — the band is guaranteed to be wider than any normal oscillation the market has shown recently, so the state flip is, by construction, a move the market has not yet made in 3 months of 1m bars. That is a self-calibrating "this is a genuine regime move" test.
**Why tick-powerful:** ZLEMA is one recurrence; the 210-bar max ATR is a maintained rolling max (O(1) with a monotonic deque). The state machine is two comparisons per tick. The 7-factor entry built on this state (§5.3) is the full pattern.

---

### 2.4 Multi-Timeframe Trend Voting (confirmed-value pattern)
`sources: Fibonacci.txt, ELITE SMART.txt, ExProfit SuperTrend.txt, Combined Algo v5.txt`

Four independent MTF constructions, all with the same porting rule:

```python
# (a) Fibonacci:  D1: close > EMA(200)
#                 H4: close > EMA(50)
#                 H1: MACD(12,26,9) > 0 AND RSI(14) > 45
#                 aligned_bull = all three
# (b) ELITE:      for TF in {1m,3m,5m,10m,15m,30m,60m,120m,240m,D}: vote = close > EMA(200) on TF
# (c) ExProfit:   for TF in {1m,3m,5m,15m,30m,60m,120m,240m,D}: vote = SuperTrend(15, ×5) direction on TF
# (d) Combined Algo v5: 5 TFs (5m..1d), each contributing a trend vote (>=3/5 required, §5.3)
```

**Porting rule (replaces every `request.security` in the batch):** each TF is just another kline stream the bot already subscribes to. Maintain the indicator (EMA200 / SuperTrend / MACD) **on each TF's own stream**, and consume the value of the **last closed bar** of that TF. That is exactly the non-repainting semantics the legitimate (lookahead_off) calls intend, with zero Pine-specific machinery. In the bot this is a table: `tf_state[tf] = (direction, updated_at_kline_close)` — a vote is a count over the table, O(#TF) per decision.

**Mechanics:** MTF voting is a *dimensionality-reduction* filter: a 1m signal that requires 3+ of 5 higher-TF agreements has its false-positive rate multiplied by the per-TF error rate — cheap, since each TF state costs nothing per tick. The (a) variant's H1 clause (MACD>0 *and* RSI in (45, 100)) is a momentum+position conjunction, not a bare MA position.
**Why tick-powerful:** TF states change at most once per TF-bar (for D1: once per day). The vote is a cached integer refreshed on TF-bar close — the 1m fast path reads one integer.

---

## 3. MARKET MICROSTRUCTURE (OB / FVG / S-D / Sessions — No Delayed Closures)

### 3.1 Delta Reaction Zones (cumulative-delta pivot zones) — the batch's core order-flow engine
`source: Delta Reaction Zones.txt` (duplicate: `Delta zones.txt`)

```python
# per 1m bar (proxy flow):
delta  = sign(close - open) * volume
smooth = EMA(delta, 3)
cum    += smooth                        # running cumdelta
# alt pivot source: cumRoC = cum - cum[12]

# PIVOTS ON THE CUM SERIES (12/12):
if cum makes a 12/12 pivot HIGH:   zone = RESISTANCE anchored at that bar's price HIGH
if cum makes a 12/12 pivot LOW:    zone = SUPPORT    anchored at that bar's price LOW
half_width = 0.35 * ATR14   (frozen at creation)

# IMPULSE STATISTICS at creation (100-bar window):
pos_pct = sum(max(delta,0), 100) / sum(abs(delta), 100)
neg_pct = 1 - pos_pct;   net = sum(delta, 100)
label = SELL_FLOW if pos_pct >= 0.60 else BUY_FLOW if neg_pct >= 0.60 else MIXED

# MERGE RULE (the distinctive part):
#   same-type zones that overlap OR are within 20 ticks of each other:
#     zone.price_range = union
#     zone.pos_pct / neg_pct = weighted by |net_impulse| of each zone
#     zone.net = sum of nets;  zone.created = earliest of the two
#   (i.e., repeated flow at the same price = ONE stronger zone, not two weak ones)
# inventory: max 8 zones;  zone dies when CLOSE crosses its far edge

# SIGNALS (fast path):
support reclaim  = close crosses back ABOVE  the midline of a SUPPORT zone
resistance re-entry = close crosses back BELOW the midline of a RESISTANCE zone
```

**Mechanics:** The insight is that **cumulative delta has its own market structure**: where the *flow integral* stops making progress (a cumdelta pivot), price has just finished an impulse into resistance (or out of support) — the zone anchored at that price extreme is where the next impulse's opposing flow will fight. The 100-bar impulse statistics *label* the zone by which side dominated the flow that built it (SELL FLOW = sellers dominated the impulse that made the high → expect them defending it). The impulse-weighted merge encodes "more net flow at the same price = stronger zone", converting a bag of zones into a ranked liquidity map. Midline reclaim (not full-zone break) is the early signal: price returning through the middle of a zone is the first proof the zone's flow is being consumed.
**Why tick-powerful:** `cum` is one running sum (O(1) per tick when fed true per-trade delta). A 12/12 pivot on `cum` confirms with 12 bars of *left-side* data — in the bot, run the same test on the live cum series so the zone forms the moment the left side completes. Zone portfolio: ≤8 × (bot, top, net, pos_pct, created) = one bounded array; per tick: 8 two-sided level tests + 8 midline tests.
**The porting upgrade (the whole point for Binance):** `sign(close−open)·volume` is a 1-of-2-outcome proxy. On `aggTrade`, replace it with **true per-trade signed volume**: `delta_tick = q if isBuyerMaker == False else −q`, accumulated per 1m bar (or, for tick-granularity zones, run the cum + pivot logic directly on the tick-accumulated delta with the 12/12 left-side rule evaluated per tick). Everything downstream — zones, labels, merges, midlines — is unchanged. This is the only concept in the batch that becomes *sharper*, not just cheaper, on the native feed.

---

### 3.2 Buy/Sell-Split Volume Profile (close-location-value decomposition)
`source: ELITE SMART.txt (Elite Volume Profile)`

```python
# per bar i in a 100-bar lookback:
buy_i  = V_i * (close_i - low_i)  / (high_i - low_i)     # CLV split
sell_i = V_i * (high_i - close_i) / (high_i - low_i)
# distribute buy_i over the 100 price slices by [low_i, high_i] overlap;
# sell_i the same -> two histograms (buy-profile, sell-profile) per slice
POC per slice family = argmax slice volume
```

**Mechanics:** The classic close-location-value heuristic: a bar that closes in its top decile "bought" its whole volume. Splitting the profile into buy-histogram and sell-histogram exposes *where buying and selling each concentrated*, not just where volume was — e.g., a slice with equal total volume but sell-heavy composition is a different object than one that is buy-heavy. It is a coarse but fully computable footprint model.
**Why tick-powerful:** 100 bars × 100 slices = 10k-cell grid rebuilt on each 1m close (or incrementally: add the closing bar's split, drop the exiting bar's — O(100) per close). Per tick: two slice lookups. On Binance the native upgrade is again `aggTrade` signed volume — the split then comes from actual prints, and the profile becomes a true trade footprint with per-slice buy/sell imbalance (which feeds §3.1-style labeling directly).

---

### 3.3 Order Block State Machine with ATR Size Filter and Equilibrium Line
`source: Fibonacci.txt (Advanced Order Blocks)`

```python
pivots = 5/5                                   # fast structure
bull BOS: close crosses ABOVE the last confirmed pivot high
OB candidate = the bar at the time of the last confirmed pivot LOW,
               only if its bar index is 1..50 bars before the BOS (lookback validity)
size filter:  0.5*ATR14 <= (top - bottom) <= 3.0*ATR14        # ATR-normalized block size
equilibrium  = (top + bottom) / 2                            # midpoint line
# LIFECYCLE (explicit three-state):
VALID -> MITIGATED:     low re-enters [bottom, top]   (first retest; zone "seen")
VALID/MITIGATED -> INVALIDATED: close < bottom        (thesis dead; zone removed)
# (bear mirror: BOS on close < last pivot low; OB = origin bar of that low; high >= top)
```

**Mechanics:** Same origin-bar-of-the-leg idea as batch 1 §3.2/§3.3, with two refinements: (a) the **ATR size filter** — a block smaller than half an ATR is noise (spread-scale), bigger than 3 ATR is not a block but a whole range; the filter keeps only "one-leg" blocks; (b) the explicit **equilibrium line** as a first-class level — in ICT terms the 50% level, the highest-probability retest target and the strongest magnet inside the zone. The three-state lifecycle (VALID/MITIGATED/INVALIDATED) is the full state machine a zone should have, and invalidation is close-based (wick touches don't kill it).
**Why tick-powerful:** 5/5 pivots confirm in 1 bar; block creation is event-driven; per tick ≤N zones × two level tests (retest edge, invalidation edge). The equilibrium price is a pre-placeable resting limit the moment the block exists.

---

### 3.4 ATR-Scaled Supply/Demand with POI Collision Suppression and BOS Conversion
`source: ExProfit SuperTrend.txt (SAIYAN OCC crypto-scalping engine)`

```python
swing = pivothigh/pivotlow(10, 10)
on confirmed swing HIGH:  SUPPLY zone = [swing_high - 0.25*ATR50, swing_high]   # width = box_width/10 * ATR50
on confirmed swing LOW:   DEMAND zone = [swing_low, swing_low + 0.25*ATR50]
POI = zone midpoint
# COLLISION SUPPRESSION: do not create the zone if any existing zone (either family)
# has |POI_existing - POI_new| < 2 * ATR50      # one zone per 2-ATR neighborhood
# inventory: keep 20 zones per family (FIFO)
# BOS CONVERSION:
if close >= supply_zone.top:  zone collapses to a single line at its POI, labeled BOS (deleted from zones)
if close <= demand_zone.bot:  symmetric
```

**Mechanics:** Three policies in one engine: (1) zone width = 0.25·ATR50 — the width is a fraction of *long* ATR, so zones are structurally thin relative to the regime; (2) POI-collision suppression — the map can never accumulate more than one zone per 2-ATR neighborhood, which is an explicit "price space is crowded here" deduplication (compare the IoU-merge in batch 1 §3.2; here it is *prevention* rather than merge); (3) **conversion instead of deletion** — a broken zone does not simply vanish; it converts into a level at its POI marked BOS, i.e., the zone's *center of gravity* becomes the new structural reference (the price where the most volume of the zone traded). That is a polarity/role change of the level, analogous to the breaker conversion in batch 1 §3.2 but with a specific rule for where the survivor line sits.
**Why tick-powerful:** Per zone: (top, bot, POI) + family. Per tick: ≤40 three-comparison checks (creation suppression is only on swing events). The conversion event fires at the crossing tick and installs a new level *immediately* — the level set is self-updating.

---

### 3.5 Equal-High/Low Clustering with Price-Percentage Tolerance + SFP Wick-Ratio
`source: Fibonacci.txt (Liquidity Maps)`

```python
swings = pivothigh/pivotlow(10, 10), keep last 10 of each
EQ_HIGH: three CONSECUTIVE swing highs with
         |p1 - p2| < 0.002*p1 and |p2 - p3| < 0.002*p1        # 0.2% of PRICE (not ATR)
         level = mean(p1, p2, p3)
EQ_LOW:  symmetric
SFP_bull = low < prev_swing_low and close > prev_swing_low
          and wick_size > 0.4*ATR14 where wick_size = (prev_swing_low - low)/ATR14
```

**Mechanics:** The tolerance is a **fixed percentage of price** (0.2%), not ATR-scaled — a deliberate choice: equal-high *detection* is about "is this the same stop cluster", and stop clusters are placed at round/identical prices, so a percentage tolerance is the right unit (batch 1 §1.12 used ATR tolerance; both are valid, this one is price-anchored). Requiring three consecutive qualifying swings (not a running pair) makes EQH a rarer, higher-liquidity object than pairwise clustering. The SFP adds a *minimum wick in ATR units* (0.4·ATR) to the sweep-and-close-back test — the wick must be a real displacement, not a tick.
**Why tick-powerful:** ≤10 swing values per side; EQH detection is O(1) per new pivot (three comparisons). SFP is evaluable live: the instant `price` returns above `prev_swing_low` with the bar's wick already ≥ 0.4·ATR, the pattern is complete — one wick earlier than the bar-close version.

---

### 3.6 Confirmed-Pivot Fibonacci Levels with ATR-Tolerance Rebound (and OTE zone)
`source: Fibonacci.txt (Fibonacci Retracements + OTE Zone modules)`

```python
# LEVELS: 4H high/low, pivots 50/50; the swing values are FROZEN until the next
# pivot confirms (no rolling max/min -> no repaint, levels never move under price)
fib_k = swingLow + (swingHigh - swingLow) * k,  k in {0, .236, .382, .5, .618, .786, 1}
# REBOUND confirmation (long, at 38.2%):
tol = 0.3 * ATR14
touched   = |low - fib382| <= tol            # wick reached the level WITHIN an ATR band
closed_up = close > fib382
confirmed = touched and closed_up and close > open and V > 1.2*SMA(V,20) and MTF_aligned
# (short mirror at 61.8%)
# OTE zone: 0.618-0.790 of the last confirmed swing pair (20/20), buy if last swing was high
```

**Mechanics:** Two ideas worth keeping. (1) *Level pinning to confirmed pivots* is the correct non-repainting fib construction — levels exist as immutable prices between pivot confirmations (the rolling-highest/lowest variant repaints every tick). (2) The **ATR-tolerance rebound** formalizes "price touched the level": the wick need only come within 0.3·ATR of the level — the touch is a *band*, not a knife-edge, which is what actually happens on liquid books (price stops 2 ticks above the level all the time). Confirmed rebound = band-touch + close-back-inside + direction + volume + MTF — five independent facts about one bar. The OTE zone (61.8–79.0) is the same pinned-swing machinery applied to the "discount/premium" band.
**Why tick-powerful:** Levels are frozen prices; the touch test is `|price − level| <= tol` per tick (a band, so it is robust to spread). All five confirmation terms are known at the close tick — but the *approach* into the band is a maker-friendly pre-arming signal (place the order at `level + tol` when the MTF gate is already up).

---

### 3.7 CISD — Pullback-then-Break Structure Levels
`source: DTC.txt (CISD Levels)`

```python
# PULLBACK STATE:
on a bearish bar (c<o): enter bearish-pullback; anchor top = open of that bar
   while in pullback: top = max of subsequent opens that exceed it  (track the pullback peak)
on a bullish bar (c<o): symmetric pullback, track the trough open
# BREAK -> LEVEL:
if high > currentStructure.top  (bullish break of structure):
    if a bearish pullback was active:
        LEVEL_RESISTANCE = pullback peak (max high of the two break bars)
        mark it, extend right; the level is "completed" (valid S/R) when
        price later CLOSES beyond it
# i.e.: a level only exists where a pullback was broken; it becomes active S/R
# after price first closes through it (the first break converts pullback -> level)
```

**Mechanics:** The construction is "pullback → break = level; break → completion". A level is *born* at the extreme of the pullback leg that the break consumed — structurally the same origin-bar logic as the OB engines, but applied to the pullback rather than the impulse, and with a two-stage activation (drawn on the break, "completed" on the first close beyond it). It is a self-generating S/R ladder: every new structure break deposits a level at the leg it consumed.
**Why tick-powerful:** State = (pullback_active, pullback_extreme, structure_top, structure_bottom). The break is one comparison per tick; the level it deposits is known at the break tick; the completion test is a close-cross (kline event). Cheap, and it keeps the level set bounded (one level per structure break).

---

### 3.8 Multi-Pivot S/R Channel Clustering + volAdj Band Break Engine
`source: Combined Trendlines Breakouts.txt (three stacked engines; the clustering one below)`

```python
# CLUSTERING:
pivots 10/10 within 290-bar loopback
cwidth = 5% of (highest(300) - lowest(300))
for each seed pivot: greedily extend the channel to include every later pivot
                    whose price is within cwidth of the current [lo, hi]
strength = 20 * (# pivots in channel) + (# bars in loopback whose [low,high] touched it)
select TOP-6 strongest channels, suppress any channel nested inside a stronger one
BREAK: close crosses a channel bound while price is OUTSIDE all channels

# CHANNEL-TRENDLINE BREAK engine:
# two-pivot trendline (10/5) through the last two pivots, projected forward;
volAdj = min(ATR30 * 0.3, close * 0.003)  -- then [20] (20-bar lagged) -- then / 2
band   = line ± 1*Z and ± 2*Z,  Z = volAdj
BREAK  = close crosses the line while inside the band, with Z*0.1 hysteresis
         and slope-sign validity (only break "with" the line's intended direction)
TP = +20*Z; SL = -20*Z (symmetric), stateful until hit
```

**Mechanics:** The clustering is the same strength-family as batch 1 §3.9 (20/pivot + 1/touch) with its own geometry (5% of 300-bar range as cluster radius; top-6; nested suppression) — its appearance in a second file confirms it as the author family's standard S/R construction. The **volAdj band** is the distinctive piece: the break band width is `min(0.3·ATR30, 0.3% of price)` — capped by BOTH volatility and a price fraction (so on cheap instruments the band can't be absurd, on rich instruments it can't be tight) — and it is **20 bars lagged** before use: a deliberately slow band of a fast band, so the break threshold is stable over the few bars around the event. The Z*0.1 hysteresis (the line's "cross zone" must be entered, not merely touched) is the same one-strike philosophy as §1.6.
**Why tick-powerful:** Channels: ≤6 × (lo, hi, strength) rebuilt per new pivot; per tick = "am I inside any channel?" (6 interval tests). The trendline-break band is (slope, intercept, Z) — three floats; the cross-with-hysteresis test is two comparisons per tick against the *projected* line, firing at the crossing tick.

---

### 3.9 FVG Inventory Policy: Containment Detection, ATR Size Gate, Distance Cleanup, Inverse Conversion
`source: DTC.txt (Gap Analysis + Gap Violations)`

```python
# DETECTION (3-bar with middle-bar containment — stricter than bare low>high[2]):
bull_fvg = low > high[2] and low[1] <= high[2] and high[1] >= low     # zone [high[2], low]
bear_fvg = high < low[2] and high[1] >= low[2] and low[1] <= high     # zone [high, low[2]]
# SIZE GATE: accept only if zone height > 0.2 * ATR20                   # 2/10 of cleanup distance
# CLEANUP (per bar, per zone):
#   remove if (bull: close < bottom - 2*ATR14) or (bear: close > top + 2*ATR14)
#   remove if age > 50 bars
# INVERSE CONVERSION (the wildcard half):
#   bull FVG: close < bottom  -> the gap becomes an INVERSE zone (polarity flip:
#                                former support gap now acts as resistance),
#                                original zone deleted, inverse zone inherits geometry
#   inverse cleanup: close back beyond the opposite edge removes it
# inventory: max 2 per side for normal, max 2 for inverse (oldest-first eviction)
```

**Mechanics:** The middle-bar containment conditions reject "gaps" where the middle candle did not actually displace (a doji middle bar creates a fake 3-candle gap) — detection is stricter than the common `low > high[2]` alone. The management policy is the real content: zones have a **minimum size in ATR units** (sub-ATR gaps are noise), a **maximum lifetime** (50 bars), and a **maximum distance from price** (2 ATR14 away = already irrelevant — the zone is evicted *before* it is broken). The inverse conversion formalizes the ICT "inverse FVG": a gap that price *closes through* does not die — it flips polarity, because the flow that broke it is now the flow that would defend the opposite side.
**Why tick-powerful:** Per zone: (top, bot, kind, created). Per tick: ≤8 three-comparison checks (distance, break, inverse-break). All events fire at the crossing tick; the inverse conversion installs a *new* level at the break moment — the level set re-polarizes in real time.

---

### 3.10 Session Volume Profile (VWAP / POC / 70% Value Area)
`source: DTC.txt (Session Volume Profile Logic)`

```python
# per session (NY/LDN/TKY), 24 price bins over the session's running [low, high]:
#   price for each 1m bar = (high + low) / 2;  its volume -> bin containing that price
VWAP = Σ bin_vol·bin_mid / Σ bin_vol
POC  = argmax bin
# VALUE AREA (market-profile algorithm):
target = 0.70 * total_vol
expand from POC: at each step add the adjacent bin (low side or high side)
                  whose volume is LARGER; stop when accumulated >= target
VAH, VAL = final bin edges
# maintained live: profile recomputed on each session bar over the session window
# (source keeps a 20-bar rolling window of bar mid-prices/volumes per session)
```

**Mechanics:** A compact, exact market-profile: 24 bins, volume allocated at the bar's mid-price, and the value area grown by the classic "add the bigger neighbor" rule until 70% of the session's volume is inside. The three outputs are the session's **fair value** (VWAP), **acceptance center** (POC), and **acceptance envelope** (VAH/VAL). Combined with §1.7's drift classifier, the session object is: *where value is, where it's moving, and whether the close is inside the accepted range* — the full session-context picture in three price pairs + a sign.
**Why tick-powerful:** 24 bins × 3 sessions = 72 counters; per 1m close: one bin update (O(1)); per tick: nothing (mid-price of the forming bar is not yet known, so the profile is a kline-granular state — correct, it is context, not a trigger). VWAP/POC/VAH/VAL are four pre-placeable levels per session; "close at session end outside the value area" is a computable session-exit flag.

---

## 4. DYNAMIC RISK MANAGEMENT (Real-Time Volatility-Based)

### 4.1 Nine Academic Volatility Estimators (complete reference library)
`source: ELITE SMART.txt` — all nine implemented; the formulas are the standard ones, given here as the port-ready set:

```python
r = ln(c/c_prev)                                  # log return
# 1. Close-to-Close:        σ = sqrt(Σ(r - r̄)² / (n-1))
# 2. Parkinson:             σ² = (1/(4·ln2·n)) · Σ ln(H/L)²
# 3. Garman-Klass:          σ² = (1/n) · Σ [ ½·ln(H/L)² − (2ln2 − 1)·ln(C/O)² ]
# 4. Rogers-Satchell:       σ² = (1/n) · Σ [ ln(H/C)·ln(H/O) + ln(L/C)·ln(L/O) ]
#                           (drift-free; uses all four prices, no drift assumption)
# 5. Garman-Klass-Yang-Zhang: GK + ln(O/C_prev)² term   (adds the overnight/open gap)
# 6. Yang-Zhang:            σ² = Vo + k·Vc + (1-k)·Vrs
#        Vo = var(ln O/C_prev),  Vc = var(ln C/O),  Vrs = Rogers-Satchell term
#        k  = (a - 1) / (a + (n+1)/(n-1)),  a = 1.34
# 7. EWMA:                  v = λ·v' + (1-λ)·r²,  λ = (n-1)/(n+1)
# 8. MAD (mean abs dev):    σ ≈ sqrt(π/2) · mean(|r - r̄|)
# 9. MAAD (median abs dev): σ ≈ sqrt(2) · mean(|r - median(r)|)
# (source annualizes with sqrt(period); the bot keeps raw per-bar estimates)
```

**Mechanics:** The estimators form a *bias-variance ladder for the same question*: CTC ignores wicks (cheap, noisy); Parkinson uses only the range (efficient under no drift, blind to open/close); Garman-Klass and Rogers-Satchell use all four OHLC prices and are the standard "bar-data is free" estimators; **Yang-Zhang** is the composite that adds the open-gap variance and is the only one robust to the open/close asymmetry — which is exactly why the file's auto-sensitivity engine (§1.2) defaults to it with a=1.34. EWMA(λ=(n−1)/(n+1)) is the exponentially-decayed member (fastest regime response); MAD/MAAD are the robust (outlier-resistant) members.
**Why tick-powerful:** Every estimator is an O(1) recurrence or a fixed-n window sum — run 2–3 of them in parallel (recommended: YZ for the regime table, EWMA for the fast band, MAD for the outlier-safe floor) and you have a full volatility *state vector* at ~10 flops per bar. This is the batch's most directly reusable code block: it is literally a volatility-estimator library.

---

### 4.2 Aladdin Composite Risk Score → Position-Size Tiers
`source: Fibonacci.txt (Aladdin Risk Engine)`

```python
vol_risk  = min(100, ATR14 / SMA(ATR14, 100) * 50)        # current vol vs long baseline
chop      = 100 * log10( Σ ATR(1), 20 ) / log10( highest(high,20) - lowest(low,20) )
          # standard Choppiness Index: high when path length >> net displacement
systemic  = 0.5 * vol_risk + 0.5 * chop
SIZE:  systemic < 25  -> FULL
       systemic < 50  -> NORMAL
       systemic < 75  -> HALF
       else           -> CASH (no new entries)
```

**Mechanics:** Two *orthogonal* risk facts: (a) volatility level relative to a 100-bar baseline (are we more volatile than usual?), and (b) path efficiency over 20 bars (is price trending or chopping — the Choppiness Index is 100 in a pure oscillation and approaches 0 in a straight line). Half-and-half weighted, the composite answers "is this a good *environment* to hold risk at all" — a regime size gate, independent of any entry signal. The four-tier mapping (FULL/NORMAL/HALF/CASH) is a discrete, testable policy.
**Why tick-powerful:** ATR14 + its 100-SMA, a 20-bar path-sum, a 20-bar high/low — all O(1) maintained. The tier is one comparison at decision time. It slots in as the outermost sizing multiplier above the per-trade risk-based sizing of batch 1 §4.5.

---

### 4.3 ATR Z-Score Volatility Gauge
`source: Eyops Fx Premium.txt (dashboard volatility)`

```python
vol_pct = 40 * (ATR14 - (μ20 - 2σ20)) / (4·σ20) + 30      # μ20/σ20 = SMA/stdev of ATR14 over 20 bars
# i.e., ATR's position within its own 20-bar [μ-2σ, μ+2σ] envelope, mapped to ~0..100
```

**Mechanics:** A one-line "volatility is at the X-th percentile of its recent normal range" gauge — the z-score of the ATR against its own recent distribution, rescaled to a 0–100 with the ±2σ band mapped to 30–70. Useful as a *displayable* scalar that is also directly usable as a gate (e.g., no new longs below 35, no shorts below 50 — the batch-1 §4.6 asymmetry, applied to this gauge).
**Why tick-powerful:** Two maintained moments of ATR14 — O(1) per bar; per-tick cost zero (gauge is bar-granular).

---

### 4.4 ATR-Anchored SL/TP Ladders (cross-file synthesis)

| File | SL | TP ladder | Notes |
|---|---|---|---|
| Eyops Fx Premium | 6·ATR14 | 1.5 / 3 / 5 / 9 · ATR14 | 4-stage, partials 30/30/30/10% (§4.5); SL = 4×TP1 (wide, swing-hold) |
| Fibonacci | 1.6·ATR14 | 0.5·ATR(14 on 4H) / 1.0·ATR(4H) | **TPs scaled to a HIGHER-TF ATR** — targets are regime-sized, stop is local-sized |
| Clear Trend Algo | 3·ATR14 | — (band-based) | band REMA±0.1·ATR14 is the entry zone |
| Breakout Lines | 1.5·ATR14 | 1R / 2R / 3R | R = |entry − SL| |
| Breakout Targets | 5·ATR14 | 0.5R / 1R / 1.5R | anchored to pivot box, ATR99/2 buffer |

**Mechanics:** The family's consensus is "SL = k·ATR14, k ∈ [1.5, 6]" with TPs either in R-multiples or in ATR multiples — i.e., *every* geometry is a function of one live volatility scalar, so the whole trade plan re-prices with the regime. Two non-trivial details: (a) Eyops' SL = 6·ATR with TP3 = 9·ATR is a deliberately *wide* swing structure (the stop is meant to survive full pullbacks; the payoff is the 9-ATR leg); (b) Fibonacci scaling the **TPs by the 4H ATR while the SL uses the 1m/15m ATR** is a genuine "local stop, macro target" asymmetry — risk per trade stays small while targets reach regime-scale prices.
**Why tick-powerful:** One ATR (and optionally one HTF ATR) maintained → the entire plan is a set of frozen prices at entry; trailing variants (batch 1 §4.3) reuse the same scalars. The HTF-ATR target is computed at entry from the HTF kline stream already present in the bot.

---

### 4.5 Skewed Partial-Exit Architecture (80/10/2) + RSI-Stage Exits (recurring)
`sources: Eyops Fx Premium (SAIYAN risk block); ExProfit (same ladder); RSI exits: ELITE SMART / Clustering Clouds v2`

```python
# SAIYAN partial ladder (percent form; structure is the point — map % -> ATR in the bot):
TP1 = +0.2%  -> close 80% of the position
TP2 = +0.5%  -> close 10%
TP3 = +7.0%  -> close 2%      (free runner)
SL  = -0.5%
# implemented as an explicit state code: 0 (flat) -> ±1 (entered) -> ±1.1 (TP1)
# -> ±1.2 (TP2) -> ±1.3 (TP3); SL resets to flat from any state
# RSI staged exits (recurring, identical to batch 1 §4.7):
#   long: TP1 at RSI cross 70, TP2 at 75, TP3 at 80 (sequential)
#   short: 30 / 25 / 20
```

**Mechanics:** The 80/10/2 split is the "scalp the bulk, keep a tail" architecture: the vast majority of the position exits at a *tiny* target (0.2% — essentially the first meaningful tick-cluster beyond entry), which converts most trades into small wins almost immediately, while 2% of the position rides to a 35×-larger target (7%) with a tight stop — the expected value of the tail covers the cost of the structure. The state-code implementation (0/±1/±1.1/±1.2/±1.3) is the correct machine representation: the exit plan is a finite automaton, each level-cross is a transition, and the transitions are pre-declared. (Fixed-% values are excluded per the red line; the *architecture* — bulk at T1, tail at T3, explicit states — is what transfers.)
**Why tick-powerful:** Four price events, one 5-state machine; per tick = up to 4 comparisons. The 2% tail becomes a maker opportunity: re-quote the runner's limit at its trailing stop (batch 1 §4.3) while the 80/10 legs are already booked.

---

## 5. CONFLUENCE / SCORING SYSTEMS

### 5.1 Eight-Component Weighted "AI Score" (0–100)
`source: Fibonacci.txt (AI Score System)`

```python
# component c_k in {3, 5, 7, 8, 10} by tier; score = Σ w_k·c_k / Σ w_k
w = { MACD:15, RSI:10, delta:20, OBV:10, ADX:10, structure:15, pressure:10, MTF:10 }
MACD:      |hist| > |hist[1]| ? 10 : 5;    × 0.5 if hist < 0        (expansion + side)
RSI:       50<rsi<70 -> 10;  30<rsi<50 -> 10;  extremes -> 8;  else 5
delta:     delta_norm > 0.3 -> 10;  > 0.1 -> 7;  < -0.3 -> 10;  < -0.1 -> 7;  else 3
OBV:       |ΔOBV(5)| > |ΔOBV(5)[5]| ? 10 : 5                          (5-bar derivative expanding)
ADX:       > 25 and rising(3) -> 10;  > 20 -> 7;  else 4
structure: (>=2 consecutive HH) or (>=2 LL)  -> 10;  else 3
pressure:  bullish_candles_in_last_10 > 6 -> 10;  < 4 -> 10;  else 5
MTF:       3-TF alignment (§2.4a) -> 10;  else 3
SIGNAL:  score >= 75 (threshold input)  AND  regime/squeeze not in SQUEEZE  AND  kill switch off
         AND  volume > 1.2·SMA(V,20)  AND  close on the signal side of open
```

**Mechanics:** Eight factors spanning *momentum expansion* (MACD histogram derivative, OBV derivative), *position* (RSI band), *flow* (cumulative delta norm — weight 20, the largest), *trend strength* (ADX+rise), *structure* (HH/LL count), *candle flow* (10-bar bullish-candle ratio), and *scale agreement* (MTF). The design property is that **no single family can carry the score**: the maximum from flow+structure alone is (20·10 + 15·10)/100 = 35 — you need at least three families agreeing. The MACD component uses the *derivative* (is momentum expanding?) rather than the sign — a deliberate anti-stale-momentum choice even though MACD itself is lagging (the lagging part is contained in one 15%-weighted input, not used as a cross trigger).
**Why tick-powerful:** All eight inputs are maintained scalars; the score is 8 tiers + one weighted sum, computed per candidate (event-driven). The 75 threshold is a tunable precision dial, and the score's *argument vector* (which components are low) can drive partial sizing — same pattern as batch 1 §5.2's gradient exposure.

---

### 5.2 Five-Oscillator Trend-Confidence Vote
`source: ELITE SMART.txt (Trend Confidence block)`

```python
long votes (short = mirror):
  CCI(14) > 0
  ADX(21, 21) > 34 AND +DI > -DI                 # strong trend, correct DI
  A/D line > SMA(A/D, 34)                         # flow above its own baseline
  MFI(21) > SMA(MFI, 21, 13)                      # money flow above its baseline
  linreg(momentum(21), 28) > its previous value   # momentum TREND (slope of slope)
strength = count of votes (0..5) -> label "B5".."B0" / "S5".."S0"
# used: 5-vote = "smart" signal; lower votes = weaker tier
```

**Mechanics:** Five oscillators from five different families (price-deviation CCI, trend-strength ADX/DI, cumulative flow A/D, volume-price MFI, and a *second-order momentum* — the linreg of momentum is literally the slope of the momentum line, i.e., momentum acceleration). The last is the most non-standard: requiring the *trend of momentum* to be rising filters "momentum is positive but dying" — exactly the late-trend trap. The vote count is the strength label; nothing is a hard gate, so the count can be mapped continuously to size.
**Why tick-powerful:** Five maintained oscillators + one 28-point linreg (rolling moments, O(1)). Vote count is one popcount at decision time.

---

### 5.3 Seven-Factor Pullback Re-Entry Confluence
`source: Combined Algo v5.txt`

```python
trend_state = +1 via §2.3 (ZLEMA70 + max-ATR hysteresis)
MTF_votes   = # of 5 higher TFs (5m..1d) in the same trend direction   (>= 3 required)
entry_LONG = crossover(close, ZLEMA70)          # the pullback just ended
         AND trend_state == +1                  # regime still up (state, not the cross)
         AND MTF_votes >= 3/5
         AND close > open                       # the crossing bar is bullish
         AND ZLEMA70 rising
         AND |close-open| > 1.1 * avgBody(70)   # the bar is abnormally strong
         AND RSI14 > 50
# short = full mirror (RSI < 50)
```

**Mechanics:** This is the batch's cleanest *entry* pattern: a **pullback re-cross** (price crosses its own zero-lag trend line from below while the trend state is still up) plus six context facts from six different families (scale agreement, candle direction, trend-line slope, bar-strength significance, oscillator position). The `body > 1.1·avgBody(70)` term is a one-sample significance test on the re-entry bar itself — the crossing must be a real move, not a drift. The `trend_state == +1` clause is the key structural choice: the cross is the *timing*, the state is the *permission* — the state was set by the max-ATR hysteresis (§2.3), so permission can only come from a move the market has not yet shown recently.
**Why tick-powerful:** All seven terms are maintained; the cross is the only event, so the gate is evaluated once per ZLEMA-cross (rare). The body term is watchable live: the moment `|live_close − open|` exceeds 1.1·avgBody, the last factor is satisfied and the entry can fire before the close.

---

### 5.4 Kill-Switch Composite Veto
`source: Fibonacci.txt (Kill-Switch System)`

```python
kill = (ADX < 18)                                  # no trend strength at all
     or (volume < 0.5 * SMA(volume, 20))           # flow dried up to < 50% of normal
     or (squeeze active and not yet released)      # inside the coil (§1.9) — no entries
# directional veto (separate):  delta_norm < -0.2 blocks BUY signals; > +0.2 blocks SELLs
# final:  signal = base_signal AND MTF-aligned AND pressure_ok AND NOT kill
```

**Mechanics:** A *veto* layer, not a scoring layer: three independent "the environment is dead" facts (strength, flow, regime-coil) plus a flow-direction conflict test that can kill one side while the other side stays live. Veto layers are the correct place to put *hard* environment rules because a score can be gamed by correlated components while a veto cannot — each kill condition is a different variable family.
**Why tick-powerful:** Three maintained scalars + delta_norm; evaluated once per candidate. As a bot primitive it is the global "stop opening new positions" flag (existing positions keep their own risk management).

---

### 5.5 Market Pressure Composite (flow + slope + strength)
`source: Fibonacci.txt (Market Pressure)`

```python
imbalance  = (cum_buy - cum_sell) / cum_total * 100     # cumulative (since chart start)
ema_angle  = (EMA21 - EMA21[5]) / close * 100           # normalized 5-bar slope of the trend
pressure   = clip( 0.4*imbalance + 0.3*ema_angle + 1.5*(ADX - 20) + 50, 0, 100 )
pressure_buy  = pressure > 60
pressure_sell = pressure < 40
```

**Mechanics:** A single 0–100 "which way is the push" scalar blending **net flow** (40% — the only flow term), **trend-line slope** (30% — normalized by price so it is scale-free), and **trend strength offset** (1.5×(ADX−20) — a dead market is pinned to 50 by construction). The +50 centering makes 50 = "no pressure" and the asymmetric 0.4/0.3 weights make flow dominant. It is a directional gauge, not a timing signal: `pressure_buy` is a *permission* used inside the §5.1 signal chain.
**Why tick-powerful:** Two running sums (flow), one EMA + its 5-bar value, one ADX — O(1); evaluated per candidate.

---

### 5.6 Retracement-Probability Scorer (zone position × quality factors)
`source: Fibonacci.txt (Retracement Probability)`

```python
fibpos = 100 if price in ideal zone (long: 38.2-50% fib, short: 61.8-78.6% of pinned swing)
        = 60 if outside 0-38.2 / 78.6-100   (acceptable, deeper)
        = 80 otherwise                      (equilibrium 50-61.8 band)
mtf = 100 if aligned (per §2.4a) else 30
vol = 100 if V > 1.5·SMA else 70 if V > SMA else 40
rebond = 20 if a §3.6 confirmed rebound is active else 0
P = 0.4·AI_score + 0.25·fibpos + 0.2·mtf + 0.1·vol + 0.05·rebond      (clipped 0..100)
confidence: >= 80 "VERY HIGH", >= 65 "HIGH", >= 50 "MEDIUM", else "LOW"
```

**Mechanics:** A *conditional* probability estimate: given that a fib level is being approached, what is the chance the retrace holds? The 40% weight on the full AI score means the zone alone can never carry a trade — a perfect zone with a failing score is still ≤ 40+25+20+10 = 95·(weights) only if everything else agrees. The "ideal zone" concept (38.2–50 for longs, 61.8–78.6 for shorts) encodes the classic "buy in the first half of the discount, sell in the first half of the premium" rule as a hard band.
**Why tick-powerful:** All inputs are maintained; computed per level-approach event (when price enters the §3.6 touch band). Output is a size tier — the same "score → tier → size" pipeline as §5.1/§5.2, applied to the *level* rather than the *signal*.

---

## 6. INTEGRATION BLUEPRINT — BATCH 2 ADDITIONS TO THE BATCH 1 ENGINE

**New SLOW state (per closed 1m kline):**
1. Log-linear channel (§1.1): 19 rolling OLS moment-sets; re-evaluate argmax every 5 bars → `{midline, upper, lower, direction, R-tier}`.
2. Volatility bank (§4.1): YangZhang(10) + EWMA(10) + MAD(10) + their 55-SMA → vol-percentile ST multiplier (§1.2) + ATR z-gauge (§4.3) + Aladdin tier (§4.2).
3. Delta flow (§3.1): per-trade signed delta accumulator → `cum`; 12/12 pivot test on `cum` → zone creation; zone list ≤8 with impulse stats, merge-on-creation, far-edge death.
4. Session object (§1.7 + §3.10): 3×(open, hi, lo) + 24-bin profile → VWAP/POC/VAH/VAL + drift class; session-extreme levels with 48h TTL.
5. Structure ladder: 6-EMA stack state (§2.1), nested ST minor(10,3.0)/major(14,6.0) (§2.2), ZLEMA70 + 210-max-ATR state (§2.3), MTF vote table (§2.4), pivot-chain lines (§1.11), violation-budget lines (§1.6), CISD levels (§3.7), channel clusters top-6 (§3.8), FVG/inverse list (§3.9), OB list with 3-state lifecycle (§3.3), ATR S/D list with POI suppression (§3.4), EQH/EQL clusters (§3.5), pinned fib levels (§3.6).
6. Regime flags: squeeze 5-condition state + released (§1.9), vol-inflection (§1.8), absorption/climax events (§1.10), exhaustion counters (§1.5).

**New FAST-path triggers (per aggTrade, all level-comparisons):**
- Channel: price vs projected loglin midline/edges (§1.1); vol-percentile ST flip (§1.2).
- Flow: delta-zone midline reclaim / far-edge break (§3.1); FVG CE touch, inverse conversion (§3.9); OB retest/invalidation (§3.3); S/D POI + BOS conversion (§3.4); EQH/EQL sweep + SFP (§3.5).
- Levels: fib touch-band entry (§3.6), session VWAP/POC/VAH/VAL approach (§3.10), session-extreme approach (§1.7), pinned S/R + violation-budget break (§1.6/§3.8), CISD completion (§3.7).
- Regime events: squeeze release (live KC-edge break), exhaustion confirmation candle, body-compression box break (§1.4).

**Entry pipeline:** trigger → direction gate (§2.1 state or §2.2 major) → confluence gate (§5.3 7-factor or §5.1 AI≥75 + §5.4 kill-check) → level quality (§5.6 if level-based) → size = risk$/|entry−SL| × Aladdin tier (§4.2) × R-tier (§1.1) → plan (§4.4 ladder, HTF-ATR targets) → manage (§4.5 state machine + batch 1 §4.3 ratchet + RSI-stage exits).

**Maker-side resting levels (known in advance):** delta-zone midlines & POIs (§3.1), FVG CE + inverse edges (§3.9), OB equilibrium (§3.3), S/D POI (§3.4), fib touch-band edges (§3.6), session VWAP/POC/VAH/VAL (§3.10), loglin channel edges (§1.1), violation-budget lines (§1.6).

---

## APPENDIX A — Red-Line Items Found and Discarded (per file)

| File | Discarded content |
|---|---|
| DTC_V1 | fixed 0.25% SL + 1..4R TP ladder (fixed-% risk); GUI. Kept: 6-EMA full-stack state + edge trigger |
| Double SuperTrend | none — fully extracted (§2.2) |
| Edge Algo pro | RSI(14) + MACD-histogram confluence as the *trigger* (lagging oscillator cross family); fixed-% SL ladder; all dashboard. Kept: nothing structural |
| Clear Trend Algo | none — fully extracted (§1.3) |
| Cute Dragon | ST(11,4) crossover + SMA13 filter as trigger (lagging band cross); `[1]`-shifted non-repaint idiom noted but the core is excluded. Kept: nothing structural |
| Breakout Targets | box drawing; kept: body-compression detector + pivot-box breakout (§1.4) |
| DTC V1.35 | MTF dashboard (15m..1d EMA20/50, `lookahead_off` but display-only — not a signal); fixed 0.25% SL. Kept: nothing new vs DTC_V1 |
| Breakout Lines / Breakout Lines + TPSL | `+ TPSL` file is byte-identical (trailing-newline diff only) → duplicate; drawing. Kept: pivot-chain lines + expiry (§1.11), 1.5·ATR SL / 1-2-3R |
| Combined Algo v5 | none — fully extracted (§2.3, §5.3) |
| Drone Arrows | 7-TF EMA50 dashboard vote (display only); ST(10, ×7·ATR) as *primary* trigger (very wide, laggy) discarded as trigger. Kept: min-impulse displacement filter `|c−c[1]| > 0.1·ATR14` + volume + SMA20 position (useful as an entry-quality gate) |
| Delta Reaction Zones / Delta zones | `Delta zones.txt` = exact duplicate (md5 `ad18a016…`); GUI. Kept: full engine (§3.1) — the batch's highest-value extraction |
| Combined Trendlines Breakouts | drawing; kept: all three engines (§1.6-adjacent pivot TL, §3.8 channel+volAdj, §3.8 clustering) |
| Fibonacci (Rachid Berkane) | HMA50 pump/dump snake as signal (lagging MA slope flip); RSI 5/5 divergence module (classic lagging divergence); OTE box *drawing* (zone math kept in §3.6 note); all 14 dashboards. MTF uses `lookahead_off` (legitimate — kept as §2.4a). Kept: §1.9, §1.10, §3.3, §3.5, §3.6, §4.2, §4.4, §5.1, §5.4, §5.5, §5.6 |
| ELITE SMART | `securityNoRep` HTF `lookahead_on` branch (re-specified confirmed-value in §2.4); MACD momentum bar-colorer; StochRSI panel; RSI 70/75/80 TP labels kept as recurring note (§4.5); dashboard. Kept: §1.2, §3.2, §4.1, §5.2 |
| Clustering Clouds v2 | same `securityNoRep` `lookahead_on` exclusion; the Gaussian module is a re-occurrence of batch 1 §2.5 (noted, not re-extracted); dashboard. Kept: reference for the ELITE engine family |
| DTC (DTC FX+) | daily-candle overlay `request.security(..., lookahead_on)` (visual only); all session-box/watermark drawing. Kept: §1.7, §3.7, §3.9, §3.10 |
| Eyops Fx Premium | **Zignaly futures/leverage JSON + "10-20x leverage" alerts (derivatives — excluded in full per red line 4)**; `securityNoRep`/`sr_tf` `lookahead_on`; MACD bar-colorer; EMA150/200/250 cloud fills; fixed % TP/SL ladder (structure kept as §4.5). Kept: §1.5, §1.8, §4.3, §4.4, FRAMA, JMA/KAMA/VIDA/CMA/REMA MA family (low-lag filter primitives — see note below), linreg-projection band (`intercept + slope·(len−offset)` projected to current bar, ±2·stdev(close,150) cross = regression-channel reversion), ATR-sized S/D boxes (1×ATR14 width), 9-TF ST dashboard (context only) |
| ExProfit SuperTrend | `reso()`/`securityNoRep1` `lookahead_on`; Supertrend I(14,×3)/II(3,×3) as raw triggers (nested-ratchet re-occurrence of §2.2, noted); fixed-% SAIYAN ladder (structure kept as §4.5); drawing. Kept: §1.1, §1.6, §3.4 |

**Notable un-extracted primitives worth keeping on file (filter library, not signals):**
- **FRAMA** (Eyops): `N1=(HH(len/2)−LL(len/2))/(len/2)`, `N2` = same one window earlier, `N3=(HH(len)−LL(len))/len`; `D = log2((N1+N2)/N3)` (fractal dimension); `alpha = exp(ln(2/(SC+1))·(D−1))` clamped [0.01, 1]; `N = (SC−FC)·((2−alpha)/alpha − 1)/(SC−1) + FC`; `alpha = 2/(N+1)` clamped; `out = alpha·x + (1−alpha)·out'` — volatility-adaptive MA (fast in trends, slow in chop).
- **JMA (Jurik)** (Eyops): `beta = 0.45(L−1)/(0.45(L−1)+2); alpha = beta^power; e0 = (1−α)x + αe0'; e1 = (x−e0)(1−β) + βe1'; e2 = (e0 + phaseRatio·e1 − jma')(1−α)² + α²e2'; jma = e2 + jma'` — near-zero-lag two-stage IIR.
- **KAMA / VIDA / CMA / REMA / TMA / GMMA / SSMA (Ehlers SuperSmoother)** (Eyops + ExProfit): standard low-lag adaptive MAs; SSMA: `a1=e^{−√2π/L}; c2=2a1·cos(√2π/L); c3=−a1²; c1=1−c2−c3; s = c1(x+x')/2 + c2·s' + c3·s''`.

## APPENDIX B — Notes on Correctness Risks When Porting

1. **Delta quality is the whole edge of §3.1.** The bar-level `sign(c−o)·V` proxy has only two outcomes per bar; on Binance `aggTrade` use `isBuyerMaker == false → +q, else −q` (a buy-initiated trade has `isBuyerMaker=false`). If you keep the 1m-bar delta, the EMA(3) smoothing of the source should be dropped (the bar delta is already the aggregated value) — or keep it if you feed per-tick deltas. The 12/12 pivot on `cum` must be evaluated on the *left-complete* definition so the zone forms at the pivot's right edge, not 12 bars later.
2. **The 20-tick merge distance in §3.1 is price-space, not bar-space.** On a tick grid it is 20×tick size; on 1m bars it should be re-expressed as a fraction of price (e.g., 0.02%·price ≈ 20 ticks for a 1-cent-tick instrument). Do not implement it as "20 bars".
3. **Loglin channel (§1.1) must freeze between re-evaluations.** The argmax selection is unstable bar-to-bar (two windows can share the top-R within noise). Re-evaluate on a 5-bar cadence and hold the selected (L, slope, intercept, σ) constant between evaluations — the "auto-period" is a slow parameter, the projected midline is the fast object. Also: with 19 windows of up to 1200 bars, use rolling sums (O(1)/bar) rather than refitting; a naive refit is 19×1200 ≈ 23k multiplies, still fine every 5 bars, but the rolling form costs nothing.
4. **Yang-Zhang's `a = 1.34` and `n−1` denominators matter for matching backtests.** The `k = (a−1)/(a+(n+1)/(n−1))` weight for the close-variance term is specific to n=10 (k ≈ 0.357); do not "simplify" it to 0.34.
5. **Session times in §1.7/§3.10 are FX conventions (NY/LDN/TKY UTC).** On 24/7 crypto, either keep them as "European/US/Asian activity windows" (they do approximate real liquidity clusters) or re-anchor to the exchange's own session logic. The drift classifier and value area are session-agnostic — only the windows change.
6. **`[20]` lag on volAdj (§3.8) is deliberate.** The band-of-the-band (min(0.3·ATR30, 0.3%·price) shifted 20 bars) stabilizes the break threshold across the event; removing the lag makes the band chase the break and re-create the whipsaw it was meant to filter.
7. **Exhaustion counter (§1.5) runs are measured against `close[4]`, not `close[1]`.** A "13-run" means 13 consecutive bars each above their own 4-bars-ago close — a 4-bar-lagged momentum streak. Implementing it as consecutive up-closes (`close > close[1]`) is a different, much noisier detector.
8. **The 80/10/2 ladder (§4.5) must not be ported at its literal 0.2% TP1.** On 1m crypto with realistic spread, 0.2% is noise; map the *structure* (bulk at T1 ≈ 0.5–1 ATR, tail at T3 ≈ 9 ATR with 2% of size) onto the §4.4 ATR ladders instead.
9. **Aladdin CASH tier (§4.2) is an entry veto, not an exit.** The source only gates *new* position size; in the bot, existing positions keep their risk management (batch 1 §4.3 ratchets) regardless of the tier.
10. **`request.security` on the *same* timeframe appears in several files** (e.g., ExProfit's `request.security(ticker.standard(syminfo.tickerid), timeframe.period, close)`) — this is a no-op self-reference used to force confirmed-bar semantics; on the bot it maps to "use the last closed bar's value", nothing more.
