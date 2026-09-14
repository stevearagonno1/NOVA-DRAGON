# HFT Edge Extraction — Batch 4 (Files 61–81)

**Scope:** 20 Pine files in `/home/user/uploads/`, 19 unique (`luxy OB.txt` is an md5-identical duplicate of `Luxy BIG beautiful Dynamic.txt` — extracted once). 18,826 source lines total.

**Files:** Jackson_Zones · iqfxpro · Liquidity sweep (1;2RR) · LyroRS v1 · Lion Trend · Market Matrice · Liquidity Reaper · Million Moves Alga · iOB · JOAT (Prismatic Depth) · MELONA · Money Moves (MM PREMIUM v2) · Key Levels (Bjorgum) · Joker · MONEY ALGORITHM · Mirage Liquidity Sweep Pro · KD System · Liquidity Trail Matrix (LTM) · Luxy BIG beautiful Dynamic ORB v5.

**House rules (standing):** no repaint/lookahead mechanisms (salvage as prior-period values), no lagging-crossover triggers, no GUI, no derivatives logic. Output = Python pseudo-code / precise math + why it suits a zero-wait tick engine (Binance Spot HFT: 1m klines + aggTrade + bookTicker).

---

## Red-Line Disposition (Batch 4)

| Source | Excluded mechanism | Salvage |
|---|---|---|
| Jackson_Zones | `lookahead_on` prev-day fetch | prev-day PVP ladder (recompute at 00:00 UTC) |
| Market Matrice | HTF fetch `lookahead_on` | AlphaTrend is TF-local — fully salvageable |
| Million Moves Alga | `securityNoRep` MTF ADX (`lookahead_on`) | TF-local ST/SMA/EMA200 gate salvageable |
| Joker / MONEY ALGORITHM | 12-TF `securityNoRep` fan (`lookahead_on`) | TF-local Trend Shifter / ST / dchannel salvageable |
| KD System | Pivot-levels HTF fetch (`lookahead_on`); ALMA-system 8×TF (`lookahead_on`) | pivot values as prior-period; same-TF double-SMA kernel |
| KD System | RSI7 80/20 extremes; Elder Impulse (MACD/EMA slopes) | — (standard lagging oscillators) |
| MELONA | RSI 70/30 cross + RSI-linreg(140) band | — (standard) |
| Mirage / LTM | `request.security([close[1], ema[1]], lookahead_on)` | **Not** lookahead: this is the standard *confirmed-HTF* idiom — value of the last closed HTF bar. Port as "last closed HTF value" |
| JOAT | `FER` function defined, never called | — (dead code) |
| Luxy | — (all `lookahead_off`; FX-rate fetch is cosmetic) | full logic salvageable |

No derivatives/leverage logic found in any Batch 4 file. All GUI (tables, boxes, labels, barcolor, watermarks, Telegram promo tables) dropped.

---

## §1 — Wildcards & Innovative Edges

### W1. Volume-Weighted Ratio MA ("VWRA") Oscillator — *LyroRS v1*

**The construct.** Any moving-average kernel `K(src, L)` can be *volume-weighted* without being VWMA: divide the kernel applied to `src·vol` by the kernel applied to `vol`:

```python
# L = kernel length; w_i = kernel weights (works for SMA/EMA/KAMA/FRAMA/ALMA...)
K_x   = kernel(src * vol, L)   # e.g. EMA(src*vol, L)
K_v   = kernel(vol, L)         # EMA(vol, L)
vwra  = K_x / K_v              # volume-weighted generalization of VWMA

osc = (src - vwra) / vwra * 100.0
# Asymmetric volatility bands (EMA-smoothed, alpha = 0.8):
up_band  = ema_smooth( vwra + 1.80 * sigma27, 0.8 )   # sigma27 = rolling stdev
dn_band  = ema_smooth( vwra - 0.85 * sigma27, 0.8 )
signal_bull = cross_up(osc, 0)      # zero-line cross in VWRA space
signal_bear = cross_dn(osc, 0)
# band context: touches of up_band/dn_band define over/under-extension
```

**Mechanics.** This is a mean-reversion oscillator whose reference line is the *trade-weighted* price: heavy-volume bars pull the reference much harder than light ones, so the oscillator measures distance from "where capital actually is", not the arithmetic mean. The asymmetric bands (1.8σ above / 0.85σ below) encode the empirical bias that downside extensions are shorter and sharper. Generalizing VWMA to arbitrary kernels (KAMA/FRAMA/ALMA) buys adaptive lag *and* volume weighting simultaneously — most retail VWMA code cannot do either.

**Why zero-wait.** Every component is a streaming kernel: O(1) per tick. On Binance, `vol` is native (aggTrade volume) — the `K_v` denominator is never zero, so the construct is strictly more accurate here than on forex feeds (where source files must fall back to range-weighted proxies). Zero close-wait: the cross evaluates tick-to-tick on the forming bar.

---

### W2. AlphaTrend — MFI-Gated One-Way ATR Ratchet — *Market Matrice*

**The construct.** A supertrend-style one-way ratchet line whose *up-steps are gated by money flow*:

```python
MFI14 = money_flow_index(14)          # standard
ATR   = atr(14)

# Up-side ratchet: line may only rise when positive money flow confirms
if MFI14[1] >= 50:
    candidate = low[1] - ATR[1]
    line      = max(candidate, line[1])     # one-way up ratchet
else:
    line      = ratchet_down(line, low, ATR)  # normal supertrend down-band logic

# Direction trigger (either):
slope_flip   = sign(line[1] - line[2]) != sign(line[0] - line[1])   # 2-bar slope change
big_move     = abs(close[1] - close[2]) > 2 * ATR and close crossed line
direction    = +1 if (slope_flip or big_move) and line rising else -1

# Alternation filter: a new signal is only valid if the previous signal
# was the OPPOSITE direction (no same-direction re-fires in one regime).
signal = trigger and (prev_signal_dir != direction)
SL = line;  TP = 1R / 2R / 3R from entry
```

**Mechanics.** Vanilla supertrend ratchets on price alone; here the *up* leg requires MFI ≥ 50 (net positive money flow over the last 14 bars). The line therefore only ratchets upward while buyers are actually participating — it flattens/freezes in distribution and keeps ratcheting down in genuine selling pressure. The 2-bar-slope trigger reacts to *the line's own curvature change* (a lag-1 derivative of a ratcheted series = a regime-change detector), and the 2·ATR big-move OR-branch catches impulse bars that jump the line outright. The alternation filter kills the classic ratchet weakness: repeated same-direction re-entries after scalp flips.

**Why zero-wait.** MFI and ATR are streaming; the ratchet is one comparison per tick; the slope flip is a state comparison (`line` has at most one new candidate per tick). All logic runs on the forming bar — no close wait.

---

### W3. RSI-Space Supertrend (Trend Shifter, contrarian) — *Joker, MONEY ALGORITHM*

**The construct.** Full supertrend machinery transplanted into oscillator space, with the cross used *contrarian* in extreme zones:

```python
Rs     = ema(rsi(close, 50), 30)                    # double-smoothed RSI
dRs    = abs(Rs - Rs[1])
volr   = ema(ema(dRs, 50), 50)                      # double-smoothed oscillator volatility
band   = 4.236 * volr
TsFast = Rs
# Ratcheted slow line in oscillator space:
if Rs > TsSlow[1] and Rs[1] < TsSlow[1]:  TsSlow = TsFast - band   # cross up  -> lower band
elif Rs < TsSlow[1] and Rs[1] > TsSlow[1]:TsSlow = TsFast + band   # cross dn  -> upper band
else:                                    TsSlow = TsSlow[1]

# CONTRARIAN signals (this is the twist):
bull = cross_up(Rs, TsSlow)  and Rs < 45     # cross up *inside the low zone*
bear = cross_dn(Rs, TsSlow)  and Rs > 55     # cross down *inside the high zone*
cont_bull_zone = Rs < 40;  cont_bear_zone = Rs > 60
```

**Mechanics.** The 4.236×ATR-in-oscillator-space kernel (identical to the Haper/Fresh family, Batch 3 — cross-reference) creates a self-scaling channel around double-smoothed RSI. Standard supertrend usage is trend-following (trade the cross in its direction). Here the cross is only actionable *when RSI is already in an extreme*: a slow-line break-out from oversold = exhaustion flip (long), break-down from overbought = exhaustion flip (short). The 45/55 gates keep you out of mid-range where the cross is pure noise. MONEY ALGORITHM is the same engine with ST(2.4,15) instead of ST(3.1,25) for the companion trend trigger.

**Why zero-wait.** Two streaming series + a ratchet state; the cross is an event on tick arrival. Contrarian entries are exactly the kind of counter-trend, volatility-compression break that a tick engine executes best (inward book pressure at the extreme).

---

### W4. 4-Band Proportional ATR Ratchet Stack + Selectable Flip Band — *Liquidity Trail Matrix*

**The construct.** Not one supertrend line but **four concentric one-way ratchet bands with *proportional* spacing**:

```python
# Presets: Scalping (2.5, 0.20) · Balanced (4.0, 0.25) · Deep (6.0, 0.30)
m1 = base
mK = base * (1 + K * step)     # K = 1..3  ->  Balanced: 4.0 / 5.0 / 6.0 / 7.0 × ATR13

# One-way ratchet per band, in the trend direction:
if trend == +1:
    tsK = max(src - mK*ATR, tsK[1])      # bands trail below price, only ratchet up
else:
    tsK = min(src + mK*ATR, tsK[1])
# FLIP on the CHOSEN band (default K=3 = 6×ATR; "Fast" K=1; "Deep" K=3 outer):
flip_down = trend == +1 and src < ts_flip[1]
flip_up   = trend == -1 and src > ts_flip[1]
# on flip: reset all four bands to the opposite side, start new segment
```

**Mechanics.** Spacing `mK = base·(1+K·step)` keeps band geometry *scale-consistent*: doubling the base multiplier doubles every gap, so the stack looks identical at any volatility regime (fixed +1/+2/+3 ATR stacks do not — they bunch up in calm markets and spread uselessly in wild ones). The four bands form a hierarchy: band 1 = retest trigger, band 3 = trend flip, band 4 = committed-trend stop / heatmap edge. This is the backbone of the LTM retest engine (S2) and gives the engine a continuous, tiered "how far did we pull back" measurement (depth 1–4) instead of a binary cross.

**Why zero-wait.** Four independent ratchets = O(4) state updates per tick; flip is a plain crossing of a frozen-until-touched line; segment boundaries are event-stamped (used by the volume profile in M7).

---

### W5. MTF-Safe Heikin-Ashi Bias Oscillator — *KD System*

**The construct.** Heikin-Ashi is recursive (`ha_open = (ha_open[1] + ha_close[1])/2`) and therefore **cannot be computed inside a higher-timeframe `request.security`** — most MTF HA indicators either repaint or are fake. The fix: pre-smooth the four components, so the "HA" is built from *streaming, MTF-safe* series:

```python
ha_o, ha_c, ha_h, ha_l = ema(open,100), ema(close,100), ema(high,100), ema(low,100)
ha_close = (ha_o + ha_h + ha_l + ha_c) / 4
ha_open  = (ha_open[1] + ha_close[1]) / 2        # recursion now lives on *EMA'd* values
ha_high  = max(ha_h, ha_open, ha_close);  ha_low = min(ha_l, ha_open, ha_close)

ha_c2, ha_o2 = ema(ha_close, 100), ema(ha_open, 100)   # double smoothing
osc   = 100 * (ha_c2 - ha_o2)
smooth = ema(osc, 7)
# 4-state hysteresis:
state = (osc > 0) * (osc >= smooth)  # 1: bull strengthening
                | (osc > 0) * (osc < smooth)  # 0: bull fading
                | (osc < 0) * (osc <= -smooth)  # -1: bear strengthening
                | (osc < 0) * (osc > -smooth)   # -2: bear fading
```

**Mechanics.** The oscillator is the gap between double-smoothed HA-close and HA-open — i.e., *net candle-body pressure after two generations of smoothing*. Because the components are EMAs, the whole stack is (a) composable under any timeframe request, (b) O(1) per tick, and (c) far less laggy than a raw EMA200 while being far smoother than a raw HA bar color. The EMA7 comparison adds a 4-state hysteresis (strengthening/fading × bull/bear) instead of a binary color — the "fading" states are the early-warning signals.

**Why zero-wait.** Pure streaming EMAs; 4-state is discrete hysteresis evaluated per tick; no recursion over raw OHLC, so no bar-confirmation dependency.

---

### W6. QQE with Ratcheted Adaptive Bands — *Joker / MONEY ALGORITHM dashboards*

**The construct.** (Dashboard-only in source, but the math is a portable low-lag oscillator state machine.)

```python
rsiMa = ema(rsi(close, 6), 6)
delta = ema(ema(abs(mom(rsiMa, 1)), 11), 11) * 1.618
# Long band ratchets UP only while rsiMa is rising:
longBand  = max(longBand[1],  rsiMa - delta) if rsiMa > rsiMa[1] and rsiMa[1] > longBand[1] else rsiMa - delta
shortBand = min(shortBand[1], rsiMa + delta) if rsiMa < rsiMa[1] and rsiMa[1] < shortBand[1] else rsiMa + delta
trend     = +1 if cross(rsiMa, shortBand[1]) else -1 if cross(rsiMa, longBand[1]) else trend[1]
```

**Mechanics.** Ratcheted bands that *open on the move and lock on the pause*: the long band can only ratchet upward while momentum is rising, then freezes — so a pullback that breaks the frozen band is a structural failure, not noise. The 1.618-scaled double-EMA delta is self-tuning to oscillator volatility. Useful as a mid-frequency state to gate W3/M4-style entries.

**Why zero-wait.** Two ratchets + one EMA; O(1) per tick.

---

## §2 — Macro Directional Filters (low-lag trend math)

### D1. EMA-Fan Position Regime — *Lion Trend*

```python
fan = [ema(close, L) for L in (9, 21, 55, 100, 200, 300)]
regime =  +1 if close > max(fan) else -1 if close < min(fan) else 0   # above-all / below-all / between
entry_long  = st_flip_up(10, 3)  and (regime == +1 or fan_aligned_up)
entry_short = st_flip_dn(10, 3)  and (regime == -1 or fan_aligned_dn)
SL = 2/2-fractal extreme ∓ 4 bps;   TP = 1R / 2R / 3.5R
```

**Mechanics.** A *positional* (not crossover) trend classifier: no line crosses any line — the price is simply compared to six fan EMAs. Positional tests have zero crossing-lag, cannot whipsaw on re-crosses, and cost six comparisons per tick. The supertrend flip provides the timing; the fan provides the regime. The 4bp SL pad on fractal stops is a spread/fee-aware micro-detail worth keeping on a Spot HFT engine (Binance taker fee ≈ 0.1% needs either a wider pad or maker entries).

**Why zero-wait.** Six `close > ema` comparisons per tick; the ST flip is a ratchet crossing.

---

### D2. Supertrend-on-OPEN + Mean-Reversion Gate — *Million Moves Alga*

```python
STo = supertrend(src=open, factor=2.5, len=11)     # NOTE: source = OPEN, not close
gate_mr = close >= sma(close, 13) and ema200_was_below_2_bars_ago   # state flag
long  = st_flip_up and gate_mr
short = st_flip_dn and (mirror gate)
direction = last C-signal direction   # dir sticks until opposite signal
```

**Mechanics.** Two deliberate low-lag choices: (1) supertrend computed on **open** — the open is known at bar start, and a band built on open reacts to the *session displacement* rather than the close-confirmed move, shaving one confirmation step; (2) the EMA200 gate is not "close > EMA200" (trend-following) but **"EMA200 was below 2 bars ago and price is now above SMA13"** — i.e., entry on *reclaim*, the mean-reversion flip at the macro average. ADX-vs-own-SMA(14) ±20% gate (TF-local part) filters dead trend. The MTF ADX variant (`lookahead_on`) is excluded; the TF-local core stands.

**Why zero-wait.** Open-based band = fully computable at bar start; "EMA200 was below 2 bars ago" is a two-bar state flag; everything evaluates tick-to-tick.

---

### D3. Prev-Day PVP Fibonacci Ladder — *Jackson_Zones* (salvage)

```python
# Computed ONCE at 00:00 UTC from the fully closed previous UTC day:
PVP = (H + L + C) / 3                    # previous value point
dp  = 2 * PVP - (H + L) / 2              # displacement from day midpoint
ladder = { PVP + r*dp for r in (+0.5, +0.618, +1, +1.382, +2.74,
                                -0.5, -0.618, -1, -1.382, -2.74) }
```

**Mechanics.** The source fetches these with `lookahead_on` (excluded as a mechanism) — but the values are just *yesterday's* OHLC, which a HFT engine already has. PVP (Fisher's Previous Value Point) plus the extension ladder (±0.5 … ±2.74) gives a static, pre-computed set of 10 intraday magnets/levels. The 2.74 extension (≈1.618²) is the aggressive "measured move" target.

**Why zero-wait.** A daily batch job produces a frozen 10-level table; intraday cost = 10 crossing checks per tick. Zero recomputation, zero repaint by construction.

---

### D4. OLS(200) Channel Retest Strategy — *Key Levels*

```python
# Hand-rolled OLS over 200 bars (port: running sums of x, y, xy, y^2 -> O(1)/tick)
slope, intercept = ols(close, 200)
sigma = stdev(residuals)
upper, lower = intercept_line + sigma, intercept_line - sigma
channel_dir = +1 if intercept_end > intercept_start else -1    # rising/falling channel

long = (channel_dir == +1)                                   # rising channel
     and close < lower                                        # retest below 1st support
     and bull_pattern_in_bull_pivot_zone                      # zone-context pattern (Bjorgum lib, visual-only in source)
     and htf_ok                                               # HTF channel rising, OR HTF falling & close < HTF midline
short = mirror
```

**Mechanics.** The edge is the *retest below the first support band of a statistically fitted rising channel*: OLS over 200 bars gives a drift line whose ±1σ envelope is the "fair value corridor"; price dipping below the lower edge inside a rising channel is a mean-reversion pullback, and the zone-pattern condition demands it happens *at* support, not in free fall. The HTF alignment rule (rising channel OK; falling HTF channel only long below its midline) is a clean two-case filter.

**Why zero-wait.** OLS via running sums is O(1) per tick; channel bands are slowly moving lines (recompute-on-change); the retest is a crossing event; the HTF part uses last-closed-HTF values only.

---

### D5. 8×TF Double-SMA Close/Open Cross + %-Level State Machine — *KD System* ("ALMA" system)

**The construct (flagged).** The "ALMA/TEMA/Hull" switch in source **always returns `SMA(SMA(x, 2), 2)`** — a code smell that reveals the real kernel: a *double 2-period SMA* of the close series crossed against the same of the open series, evaluated on a higher timeframe (8× chart TF), with `lookahead_on` (excluded). The same-TF / correctly-resampled kernel:

```python
# On an 8x-resampled feed, using ONLY closed resampled bars:
cS = sma(sma(close, 2), 2)
oS = sma(sma(open,  2), 2)
le = cross_up(cS, oS);  se = cross_dn(cS, oS)

# State machine (fixed %-levels from entry):
state: 0 = flat
  0 -> +1  on le      (long entry at close)
  0 -> -1  on se      (short entry at close)
  +1 -> +1.1 on high >= entry*(1 + 0.30%)   # TP1
  +1.1 -> +1.2 on high >= entry*(1 + 0.75%) # TP2
  any +x -> 0 on low <= SL (SL = entry*(1 - 0.20%)) or on se
  # (short mirrors)
```

**Mechanics.** Double-SMA(2,2) on an 8× timeframe is a *very* short, very smoothed trend detector — effectively "is the recent 8× bar's close-center above its open-center, sustained over 2 bars". The value is the state machine, not the cross: fixed %-levels (SL 0.2 / TP1 0.3 / TP2 0.75) make it a pure expectancy engine whose R-multiples are known a priori — ideal for Kelly-style position sizing. Note TP1 (0.3%) > SL (0.2%) ⇒ TP1 already is +1.5R.

**Why zero-wait (with flag).** The cross is a 4-bar state on closed resampled bars (port: 8m confirmed-bar stream — no lookahead needed). %-levels are frozen at entry; triggers are crossing events.

---

### D6. Multi-Stage Session-Anchored ORB Machine — *Luxy BIG beautiful Dynamic ORB v5*

**The construct.** Four nested opening-range stages built incrementally from session open, each frozen at completion:

```python
# Stages M in {5, 15, 30, 60} minutes from session open (crypto: fixed UTC anchor)
stage_M = { high: max(high over [open, open+M]), low: min(...), mid, range }
# Stages are cumulative: ORB15 inherits ORB5's final range and extends it.
active = largest COMPLETED stage

# Breakout (CLOSE-confirmed, no repaint):
buf_up = 0.002 * active.high                       # 0.2% buffer
crossed_up = close > active.high + buf_up and close[1] <= active.high + buf_up
# Filters:
volume_ok   = vol >= 1.5 * sma(vol, 20)                 # pass
strong_vol  = vol >= 2.0 * sma(vol, 20)                 # BYPASSES trend filter
trend_ok    = close > vwap / ema12 / ST(10,3) per mode
htf_ok      = daily_ema20_bias with |close - ema|/ema >= 2.0%   # strength-gated
entry       = OPEN of the NEXT bar after the breakout bar      # pending-entry pattern
```

**Cycle machine (the real edge).**

```python
committed = bars_outside >= 2                          # must hold outside ≥2 bars
went_far  = close traveled >= 0.5% beyond the edge     # min excursion
retest    = had_break and went_far and price back inside range and committed
failed    = had_break and (bars_since_break <= 5) and back inside and NOT committed
rebreak   = retest resolved -> breakout flag re-armed -> new cycle (max 6/day/dir)
# FVG filter: breakout edge must lie inside/near an unfilled 3-candle FVG:
fvg_bull = high[2] < low[0];  near = |level - gap_edge| <= 2 * gap_size
# EOD: at session end, close the trade at floating R (mark-to-R accounting)
```

**Mechanics.** The ORB gives *frozen structural levels* (each stage is a constant for the rest of the session), and the break→commit→retest→failed-break state machine classifies every excursion: a "break" that fails within 5 bars without commitment is a **trap** (the label flips, the cycle counter is *decremented* — the engine learns the fakeout), while a committed break that returns to range is a **re-entry** (the best-risk entry of the day, often better than the breakout bar itself). The next-bar-open entry removes breakout-bar slippage entirely. Strong-volume (2×) overriding the trend filter encodes "institutional volume trumps indicator direction".

**Why zero-wait (crypto adaptation).** Anchor stages to a fixed UTC session (00:00 UTC daily, or rolling 15-min "mini-ORBs" for 24/7). Stage high/low = running max/min, O(1) per tick; levels freeze at completion → a per-session 4×2 level table; breaks are crossing events; commit/fail counters are bar counters; the retest is a crossing of a frozen line. Nothing requires intra-bar history — the whole machine is a finite-state automaton on (price, time-from-open).

---

### D7. WaveTrend Dual-Zone Trap (consolidated) — *Joker / MONEY ALGORITHM / Money Moves / KD System*

```python
[wt1, wt2] = wavetrend(close, 5*t, 10*t)     # t = 1..5 (MSTuner)
pullback_long  = cross_up(wt1, wt2)  and wt2 <= -60   # pullback-signal zone
pullback_short = cross_dn(wt1, wt2)  and wt2 >=  60
# Dual-zone 5-bar-fractal divergence on wt2:
div_bull  = f_findDivs(wt2,  15, -40)   # fractal top requires wt2 >= 15
div_bull2 = f_findDivs(wt2,  45, -65)   # stronger second zone
div_bear  = f_findDivs(wt2, -15,  40) ...
```

**Mechanics.** Identical engine across four files (cross-reference Batch 3 Money Moves entry): WaveTrend (normalized CI) with two *zoned* divergence detectors — divergences only count when the oscillator fractal sits in an extreme zone (15/−40 weak, 45/−65 strong), which is what separates "divergence in a trend" (actionable trap) from mid-range divergence (noise). KD System adds the WT(9,12) ±53 "mild" cross as a third, softer tier.

**Why zero-wait.** Streaming EMAs; fractals confirm 2 bars after formation (fixed, bounded lag); the cross is an event.

---

## §3 — Market Microstructure (OB / FVG / sweeps without close-wait)

### M1. Displacement-Validated CVD Supply/Demand Zones — *KD System* (batch flagship)

**The construct.**

```python
# Displacement validation (2-bar pattern on confirmed bars):
is_demand_brk = (close[2] < open[2]) and (close[1] > open[1]) \
                and abs(close[1] - open[1]) >= 1.0 * atr(14)[1]    # ATR-scaled displacement body
# Zone = the LAST OPPONENT candle before displacement (the classic OB):
demand_zone = [low[2], high[2]]     # supply mirrors
# Overlap de-dup: reject if zB <= existing.top and zT >= existing.bottom
# Cap: 10 zones/side, FIFO
# Mitigation: demand zone dies when close <= zB (full close through far edge)
#             supply zone dies when close >= zT

# Per-zone LIVE CVD trace (the unique part):
delta_k = +volume[k] if close[k] > open[k] else -volume[k] if close[k] < open[k] else 0
CVD_z(t) = sum(delta_k for k from zone_bar to t)        # running sum, O(1)/tick
# normalized: CVD_z / max|CVD_z| mapped into the zone box (visual in source;
# the *value* is a live order-imbalance gauge for the zone)
```

**Mechanics.** Standard OB creation is "big candle after a base"; here the base candle (the zone) is *explicitly validated by the displacement bar's body size in ATR units* — a 0.4·ATR "displacement" doesn't qualify. The overlap de-dup keeps the zone set thin. The genuinely new element is the **per-zone cumulative volume delta**: each zone carries its own running signed-volume trace from its birth bar, so the engine can see whether demand zones are being *defended by buy volume* or bleeding net sell flow before price even touches them. A demand zone with rising CVD is a live buy program; one with falling CVD is decaying.

**Why zero-wait.** 2-bar pattern on confirmed bars (worst case 1 bar); zones are frozen boxes; CVD is a running sum updated per tick — and on Binance the candle-sign proxy should be **replaced with `isBuyerMaker`-signed aggTrade delta**, which is the real order-flow delta and strictly more information than the kline proxy. Mitigation is a plain crossing event. This is the single strongest order-flow construct in all four batches.

---

### M2. iOB — Inversion Order Block State Machine — *iOB*

**The construct.** Full OB → iOB lifecycle as a bounded state machine:

```python
# Displacement bar:
disp = (high - low) >= 0.85 * atr(14) \
       and abs(close - open) / (high - low) >= 0.50 \
       and close breaks prior 10-bar extreme
# OB = nearest OPPOSING candle within 5 bars before the displacement bar
# Memory: <= 150 zones, total expiry 300 bars

lifecycle:
  born -> tested   (wick enters zone)
       -> mitigated (wick/close fully fills zone, or >= 50% consumed)
       -> broken    (CLOSE past far edge; record breakBar, keep as memory)
# iOB creation:
# a NEW opposing OB that OVERLAPS a broken opposite-side memory,
# within 30 bars of the break (or gap <= 0.25*ATR)
#   => iOB = the OVERLAP zone (min size 0.05*ATR)
#   => all regular OBs in that region are invalidated
```

**Mechanics.** Inversion OB theory (ICT) in machine form: a broken order block *flips polarity* — and the only place a flip is trusted is the **overlap** between the new opposing block and the broken one (the zone where both narratives agree). The 30-bar / 0.25·ATR freshness window prevents ancient blocks from inverting; the 0.05·ATR minimum overlap kills dust; the 150-zone / 300-bar bounds make memory O(1) amortized. The tested/mitigated/broken states are exactly the state an execution engine needs to decide "is this zone still live, and from which side".

**Why zero-wait.** Every transition is a crossing event against frozen zone edges (wick-touch = aggTrade price cross; break = close-past-edge on kline close). Zone creation is a 6-bar lookback pattern. Perfect finite-state fit.

---

### M3. SCOB — 3-Bar Sweep-then-Impulse Order Block — *MELONA*

```python
scob_bull = (close[2] < open[2])                          # bar[2] bearish
          and (close[1] > open[1]) and (low[1] < low[2])  # bar[1] bullish, sweeps below prior low
          and (close > high[1])                           # current close above bar[1] high (impulse)
zone = [low[1], high[1]]                                   # the sweep+impulse bar's range
# Optional filter: ATR > SMA(ATR, 200) (only in genuine volatility expansion)
# Overlap de-dup, cap 20 zones, mitigation on close through far edge
```

**Mechanics.** Most OB detectors mark "last down candle before an up candle". SCOB encodes the *narrative* in exactly three bars: bar[2] sells, bar[1] **sweeps the bar[2] low and closes up** (liquidity grab), close > high[1] **impulses through** (displacement). The zone is the sweep bar itself — the bar that grabbed liquidity. This is the most explicit "stop-run + displacement" signature in the batch, and it's fully checkable tick-by-tick: the moment a forming bar's high exceeds `high[1]` (given the prior two bars match), the SCOB is confirmed — no close wait needed if you accept the forming-bar high (which aggTrade gives you instantly).

**Why zero-wait.** 3-bar pattern; fires intrabar on the impulse high; zone frozen at creation.

---

### M4. Sweep Quality Scoring (0–100) + Pending → CHoCH Confirmation — *Mirage Liquidity Sweep Pro* (batch flagship)

**The construct.**

```python
# Liquidity pools: pivot 21/21 swings, <= 25 stored/side, levels <= 80 bars old.
# A level is CONSUMED (no signal) when CLOSE crosses it;
# a SWEEP when the wick crosses and the close comes back:
bull_sweep = low < lvl and close > lvl        # same bar (wick-through + close-back)
# EQH/EQL: |pivot - prev_pivot| <= 0.15 * ATR14  -> "equal levels" (stronger magnets)

# QUALITY SCORE (the unique part) — all terms in ATR units:
wick     = min(open, close) - low                 # rejection wick (bull)
reclaim  = close - lvl                            # close recovery beyond the level
closePos = (close - low) / (high - low)
volComp  = clamp((vol / volMA21 - 1) / (1.5 - 1), 0, 1)    # 0 at avg, 1 at 1.5x
htfComp  = 1.0 if last-closed-4H close > last-closed-4H EMA50 else 0
score = 100 * (0.30*clamp(wick/ATR,0,1) + 0.25*clamp(reclaim/ATR,0,1)
             + 0.20*closePos + 0.15*volComp + 0.10*htfComp)
fire when score >= 50
# Both-sides sweep on one bar => ABORT (no clear direction) — ambiguity veto

# CHoCH confirmation mode:
# sweep => PENDING (stores wick extreme + level + score), expires after 13 bars
# fire when close breaks the last minor (8/8) pivot high (bull)
# => entry is on STRUCTURE BREAK after the sweep, not on the sweep bar
```

**Risk/target geometry (shared with LTM — see R1/R2):** SL = sweep wick extreme ∓ 0.25·ATR (min distance 0.5·ATR); TP 1/2/3R; BE after TP1; **target projection = nearest un-swept opposite-side level** (draw-on-liquidity: the trade's destination is the next resting liquidity pool, computed at entry from the same pool arrays).

**Mechanics.** The score decomposes *why a sweep is credible* into five measurable terms: how deep the grab (wick, 30%), how hard the rejection (reclaim, 25%), where the close sits (20%), participation (15%), and HTF alignment (10%, soft by design). Normalizing every price term by ATR makes the score regime-invariant. The pending→CHoCH stage converts "sweep happened" (information) into "structure broke after the sweep" (action) with a hard 13-bar expiry — the setup decays, which is what makes it a setup rather than a standing order. The both-sides veto is a genuinely useful microstructure insight: a bar that raids *both* pools is a volatility event, not a directional one.

**Why zero-wait.** Score = function of one confirmed bar + streaming state (O(1)); pending = a countdown; CHoCH = crossing of a frozen minor pivot — enterable at the tick that breaks it (source waits for the close; the engine can go intra-bar with identical math since all inputs are frozen at sweep time). EQH detection is a one-comparison on pivot confirmation.

---

### M5. Pivot-Zone Polarity Flip + False-Break Detector — *Key Levels*

```python
# Zone box from ASYMMETRIC pivots (20 left / 15 right), source = high/low (or HA body):
band = min(0.5 * ATR30, 5% * price) / 2           # ATR-capped, %-capped zone width
box  = [pivot - band, pivot + band], extended to present;
# _align: merge overlapping boxes (recurring zones accumulate into one bigger zone)
# Polarity flip on close break:
close > box.top  => box := BULL (support)      # "resistance broken is support"
close < box.bot  => box := BEAR (resistance)
# Breakout state: ALL active boxes are BULL (price above every zone) => breakOut
# FALSE-BREAK (trap) detector, <= 2-bar window on the ZONE-COUNT series:
#   bull-zone count went up (zone flipped) then back within 2 bars,
#   AND price just printed a 5-bar close extreme (wasLows/wasHigh)
#   => failed break / trap signal at the zone
```

**Mechanics.** The polarity flip is the standard "broken resistance = support" rule formalized as a box state. The novel part is the **false-break detector via count hysteresis**: instead of watching price, it watches the *number of zones of each polarity* — a flip that reverses within 2 bars (the zone changed its mind) combined with a local close extreme is a trapped-break signature (price broke, everyone piled in, price came back through the zone → those break-traders are the exit liquidity). This is a structural, not oscillatory, trap detector.

**Why zero-wait.** Boxes freeze at creation (merge is O(n) at creation only); polarity is a crossing event; the false-break check is two integer comparisons per tick.

---

### M6. ATR99 S/D POI Zones with Midpoint De-Dup + Break-to-Line — *KD System*

```python
buf = 0.2 * atr(99)                                  # ATR99 = ~quarter-month volatility
supply = [swingHigh - buf, swingHigh]                 # swing = 4/4 pivot
demand = [swingLow, swingLow + buf]
# de-dup: reject new zone if its midpoint is within 2 * ATR99 of any existing midpoint
# break: close crosses the FAR edge => zone converts to a flat LEVEL LINE
#        (zone "burns out" into a single line of resistance/support)
# cap 8 zones/side
```

**Mechanics.** ATR99 scaling makes these zones *regional* (weeks of price), and the 2·ATR99 midpoint de-dup aggressively thins the level set — you get at most a handful of macro zones. The break-to-line conversion models zone exhaustion: once price closes through the far edge, the zone stops being an area and becomes a line (the memory of the failed defense) — cheaper to check (1 level vs 1 box) and a classic retest target.

**Why zero-wait.** Pivot confirmations are events; zones freeze; conversion is a crossing event.

---

### M7. Trend-Segment Volume Profile with Range-Distributed Volume + LVN Break — *Liquidity Trail Matrix* (batch flagship)

**The construct.**

```python
# Window = CURRENT TREND SEGMENT (since last flip), capped at 500 bars
window = [min(low), max(high)] over segment
bins   = N=30 bins over window
# RANGE-DISTRIBUTED accumulation (not close-binning):
for each bar in segment:
    for each bin overlapping [bar.low, bar.high]:
        vol[bin] += bar.volume * (overlap_fraction)     # volume split by overlap
# zero-volume fallback: weight = bar range (TR proxy)

POC = argmax bin
# Value Area 70%: expand OUT from POC, alternating sides by which adjacent
# bin holds more volume, until 70% of segment volume is enclosed => VAH/VAL
HVN = local volume maxima with vol >= 0.55 * POC_vol    # acceptance shelves
LVN = local volume minima with vol <= 0.30 * POC_vol, inside VA   # volume vacuums

# LVN BREAK trigger: close crosses an LVN between bars:
lvn_break = (close[1] < lvl and close >= lvl) or (close[1] > lvl and close <= lvl)
```

**Mechanics.** Two accuracy upgrades over naive profiles: (1) **range-distributed volume** — a bar's volume is attributed to every price bin its range actually traded, so the profile shows where volume *traded*, not where bars happened to close; (2) **segment scoping** — the profile describes only the *current trend leg*, so POC/VAH/VAL are the magnet structure *of this move*, not of an arbitrary 720-bar window. HVN (≥0.55×POC) marks acceptance shelves where price stalls; LVN (≤0.30×POC inside VA) marks vacuums price traverses fast — hence the **LVN close-cross = acceleration trigger** ("price entering a volume vacuum often accelerates").

**Why zero-wait (crypto upgrade).** The Pine version rebuilds the profile on the last bar (expensive loop). A tick engine does better with O(1) per tick: maintain a running per-bin histogram for the active segment; each aggTrade adds its volume to the bin of its trade price (exact price-location, strictly better than bar-overlap approximation); recompute POC/VA/HVN/LVN **only when the argmax or a node threshold actually changes** (event-driven, amortized O(1)). LVN levels are frozen between recomputes → crossing checks cost one comparison per LVN per tick.

---

### M8. Consolidated Sweep-Cluster (pivot-pool sweep → bounded confirmation)

Three files implement the same family with different parameters — one engine, three configs:

| File | Pools | Raid | Confirmation | SL / TP |
|---|---|---|---|---|
| Liquidity sweep (1;2RR) | pivot 5/5 | same-bar wick-through + close-back | none (immediate) | wick extreme / 2R |
| Liquidity Reaper | pivot 8/8, ≤12 FIFO/side | wick pierce (raid) | ≤3 bars: `close < lvl AND close < open AND vol ≥ 1.1·SMA(vol,20) AND wick ≥ 25% of raid-bar range` | 1.5·ATR or 1% / 1,2,3R |
| Mirage (M4) | pivot 21/21, ≤25/side | same-bar wick-through + close-back | score ≥ 50 (+ optional CHoCH ≤13 bars) | wick ∓ 0.25·ATR / 1,2,3R |

**Mechanics.** The Reaper confirmation battery is the strictest: the raid bar must be *directionally confirmed* (bearish close below the raided level), *participated* (volume ≥ 110% of baseline), and the raid itself *meaningful* (wick ≥ 25% of the raid bar's range — a 1-tick poke doesn't count). Bounded confirmation windows (≤3 bars) are what make this HFT-portable: the engine waits a fixed, small number of bars and then either fires or discards.

**Why zero-wait.** Pool maintenance = FIFO on pivot confirmations; raid = crossing event; each confirmation term is O(1) per tick, so the engine can fire the *moment* the confirmation bar's conditions are all simultaneously true (intra-bar if volume/wick already qualify) — up to ~3 bars of bounded latency, no historical lookback.

---

## §4 — Dynamic Risk (adaptive SL / trailing on real-time volatility)

### R1. Wick-Anchored SL with Buffer + Minimum-Distance Guard — *Mirage / LTM / Luxy*

```python
sl_bull = low_of_signal_bar - 0.25 * ATR14
sl_bull = max(sl_bull, entry - 0.5 * ATR14)     # MIN-DISTANCE GUARD: widen if too tight
sl_bear = mirror
# ATR-mode alternative: entry ∓ 1.5 * ATR14 (Balanced preset)
```

**Mechanics.** The stop sits *beyond the structure that justified the entry* (the sweep wick) plus a 0.25·ATR noise buffer; the 0.5·ATR floor prevents the pathological case where entry ≈ wick (tiny risk → oversized position → fee-dominated). All three Willy-family files converge on exactly this geometry — it's the batch's default stop.

**Why zero-wait.** One tick computation at entry; the wick extreme is known at signal-bar close (or from the live low/high stream).

---

### R2. Break-Even After TP1 + "Win = TP1-Touch" Accounting — *Mirage / LTM*

```python
on TP1 touch:  SL := entry            # break-even, one-way
close on:      SL hit | TP3 hit | opposite-signal reversal
trade_is_win  = tp1Reached             # BE stop-out AFTER TP1 counts as a WIN
```

**Mechanics.** This redefines the trade: TP1 (1R) is the *security* level, not the exit. Once 1R is banked, realized risk goes to zero and the remainder (TP3 or reversal) is a free runner. Accounting wins at TP1 keeps the statistics honest for a system whose equity curve is "many +1R/BE, some +3R, rare −1R". The SL-first pessimistic resolution when SL and TP land on the same bar is the correct conservative default (a tick engine resolves chronologically — strictly better, same math).

**Why zero-wait.** Four price levels + one boolean; every transition is a crossing event.

---

### R3. Signal-Driven Reversal Engine — *LTM*

```python
# EVERY confirmed signal (scored retest OR flip) acts, exactly one position:
flat              -> open in signal direction
opposite position -> CLOSE + RE-ENTER opposite, same bar
same direction    -> ignore (no pyramiding)
# Closure paths are exactly: SL | BE-stop | TP3 | reversal — nothing else.
```

**Mechanics.** A complete, closed state machine: the engine always knows its position (exactly one or none), every close path is explicit, and a new signal *cannot be dropped* (flat ⇒ open; opposite ⇒ reverse). This is the cleanest possible position model for a tick engine — no partial states, no orphaned orders, and reversal-on-opposite-signal converts the LTM flip signal into a momentum-following exit without any trailing-stop bookkeeping.

**Why zero-wait.** Signal = event; reversal = two atomic order actions at the signal tick.

---

### R4. RSI TP Ladder with barssince Sequence Guards — *Million Moves Alga / Joker / MONEY ALGORITHM*

```python
# Long: TP1 = RSI crosses 70, TP2 = 75, TP3 = 80  (short mirrors 30/25/20)
tp1 = cross_up(rsi, 70) and barssince(tp1)[1] > bars_since_entry   # first cross SINCE entry
tp2 = cross_up(rsi, 75) and barssince(tp1) <= bars_since_entry     # requires TP1 already done
tp3 = cross_up(rsi, 80) and barssince(tp2) <= bars_since_entry
```

**Mechanics.** The `barssince` chain makes the ladder **ordered and idempotent per trade**: TP2 can only fire if TP1's cross happened *after entry*, TP3 only after TP2 — a pre-entry RSI at 72 cannot consume TP1. Volatility-adaptive exits: in a strong move RSI prints 70→75→80 quickly (full scale-out); in a weak move it never reaches 70 and the trade manages itself elsewhere.

**Why zero-wait.** RSI is streaming; each TP is a crossing event gated by a monotone event-id comparison (port: "event bar index > entry bar index").

---

### R5. Dual-ATR Ratchet Trailing with TP3-Overshoot Re-Entry — *iqfxpro*

```python
# HADYAN-family 2*ATR25 dual ratchet (Batch 2/3 cross-reference):
stop_bull ratchets up with price (2*ATR25 band), never down; entry on stop-cross
# UNIQUE mechanic — trailing re-entry on overshoot:
if in_position_long and close > TP3 (+1.5*ATR above entry):
    entry := close                       # reset the entry anchor
    rebuild TP at 0.5 / 1.0 / 1.5 * ATR from new entry
    rebuild SL at 2 * ATR below new entry
    # => the position "re-enters" higher: the whole trade geometry ratchets up
```

**Mechanics.** Instead of a trailing *stop* (which exits), iqfxpro trails the *entry itself*: when price outruns TP3, the trade is rebuilt one ATR-ladder higher, banking the first leg and re-arming a fresh 0.5/1.0/1.5·ATR scale-out. This is a ladder-climb exit system with zero lookahead: you never exit on the move, you just keep re-anchoring until the move finally dies into the rebuilt SL.

**Why zero-wait.** Ratchet = O(1) state per tick; the reset is an event on a fixed offset; rebuilding is 4 assignments.

---

### R6. Smart Trail — Spike-Capped True Range + 78.6% Fib Secondary — *KD System*

```python
HiLo  = min(high - low, 1.5 * sma(high - low, 13))   # spike-capped bar range
HRef  = high - close[1] - 0.5*max(0, low - high[1])  # gap-adjusted (standard TR components)
LRef  = mirror
trueRange = max(HiLo, HRef, LRef)                     # "modified" mode
dist    = 4 * wilder(trueRange, 13)                   # Wilder MA (O(1) per tick)
# One-way ratchet bands around close (supertrend-style, flip on close-cross)
stEx    = running extreme since last trend flip        # max high (bull) / min low (bear)
f2st    = stEx + 0.786 * (trailLine - stEx)            # 78.6% fib between flip extreme and trail
# trailLine = active stop line; f2st = secondary stop/target (the "Fib 2" level)
```

**Mechanics.** The spike cap (`min(range, 1.5·SMA(range,13))`) prevents a single wick spike from inflating the volatility measure for 13 bars — standard TR/ATR is contaminated by exactly the kind of liquidity-run wick an HFT engine cares about. The 78.6% level between the *flip extreme* and the *current trail line* is a static fib computed from two running values: it acts as a tighter "trailing of the trail" — if price retraces 78.6% of the progress from the extreme, the move has given back too much.

**Why zero-wait.** Wilder MA is O(1); stEx is a running max/min; f2st is one multiply-add per tick.

---

### R7. ATR% Tiered Adaptive Stop with Absolute Minima — *Luxy*

```python
atr_pct = ATR14 / entry * 100
# "Smart Adaptive":
mult = 1.5 if atr_pct > 3 else 1.0 if atr_pct > 1.5 else 0.7
sl = min(entry - ATR*mult, orbLow - 0.3*orbRange)        # conservative = farther
# "Scaled ATR": mult = 2.5/2.0/1.5/1.2 by same tiers
# MIN-DISTANCE GUARDS (two layers):
sl_dist >= min( ATR * asset_min )      # crypto 1.0 / forex 0.3 / stocks 0.5-1.5 by tier
sl_dist >= absolute_min_pct * entry    # crypto 1.0% / forex 0.2% / stocks 0.3%
# Luxy dual-anchored TPs: TP_k = entry + min( orbWidth*k, risk*k*priceAdj ),
# priceAdj = 1.0 / 0.8 / 0.6 for entry < 1000 / < 5000 / >= 5000
```

**Mechanics.** Stops scaled to *volatility-as-percent-of-price* (not absolute ATR) — the right normalization for a multi-asset engine — with a 4-tier discrete state machine and two independent minimum-distance floors (volatility floor AND price floor). The dual-anchored TP is the complement: targets are capped by **both** 1/1.5/2/3× the ORB range *and* R-multiples, taking the nearer — so wide ranges don't produce unreachable targets and narrow ranges don't produce fee-dominated scalps.

**Why zero-wait.** ATR% is streaming; tier switches are hysteresis-free 4-state comparisons; TP/SL are frozen at entry.

---

## §5 — Confluence & Scoring Systems

### S1. JOAT 8-Pillar Weighted Score (100 points) — *JOAT "Prismatic Depth"* (batch flagship)

**The construct.** Eight independent pillars, each bounded 0–weight, additive:

| Pillar | Weight | Math (all streaming, O(1)/tick) |
|---|---|---|
| Structure | 12 | 10/10 pivot chain direction + close beyond last pivot low/high (BOS state) |
| Volume | 12 | OBV = Σ sign(Δclose)·vol; linreg(20) slope of OBV > 0 (flow direction) |
| Momentum | 12 | Partial credit = (votes/3)·weight from {KAMA21 direction, RSI50 side, WPR ±40 zone} |
| Liquidity | 12 | same-bar sweep of the LAST pivot: `low < lastPivotLow and close > lastPivotLow` (bull) |
| Volatility | 12 | ATR14/SMA(ATR,100) ∈ [0.8, 1.6] (healthy vol) AND momentum votes ≥ 2 |
| Session | 14 | position vs daily-range midpoint: below-mid credit scales with \|dist to mid\|; above-mid flat 0.4w |
| HTF | 14 | last-closed 4H close vs last-closed 4H EMA50 (confirmed idiom) |
| Delta | 12 | signed-candle-volume cumDelta crosses its SMA(14) AND pressure = 40 + 35·volComp + 25·bodyComp > 50 |

```python
score_bull, score_bear = sum of per-pillar bull/bear credits
signal_long  = score_bull >= 70 and (score_bull - score_bear) >= 20 and gates
gates = close > VWMA200 and st(10, 3.5) == +1 and hma20_osc > 286 and ADX >= 20
cooldown = 5 bars between signals
```

**Mechanics.** The strongest confluence design in the batch because of three structural choices: (1) **bounded additive scoring** — every pillar is clamped to [0, weight], so no single input can dominate and the total is always meaningful 0–100; (2) **a margin requirement** (bull − bear ≥ 20) — not just "bull score high" but "bull clearly wins", which kills the mushy 60-vs-55 states; (3) **hard AND-gates** (VWMA200, ST, ADX≥20) as a separate veto layer — the score decides *quality*, the gates decide *permission*. Partial-credit momentum (votes/3) instead of boolean momentum is a smoothness trick worth stealing. (The `HMA20 > 286` threshold appears to be an oscillator-value gate — verify units on port; keep as tunable.)

**Why zero-wait.** Eight bounded computations, all streaming; total = 8 adds per tick; signal = 3 comparisons. No close-wait anywhere in the scoring itself (structure/delta pillars use confirmed-bar state that updates on kline close — bounded 1-bar latency on those pillars only).

---

### S2. LTM Retest Score (0–100) with Sweet-Spot Depth — *Liquidity Trail Matrix*

```python
# Pullback depth into the 4-band stack (pending, 8-bar window, resets on flip):
depthPts = {band1: 15, band2: 25, band3: 18, band4: 10}[deepest_band_touched]
# NOTE the sweet spot: band-2 touch scores HIGHEST.
#   Too shallow (band 1) = no real pullback; too deep (band 4) = trend risk.
candlePts = 20 if closePos > 0.7 else 12 if closePos > 0.5 else 5   # reclaim candle body
volPts    = 20 if vol > 1.2*volBase else 12 if vol > volBase else 5
          # volBase = SMA(vol,20)[1]  <- SPIKE DOES NOT DAMPEN ITS OWN BASELINE
agePts    = 15 if 10 <= bars_since_flip <= 150 else 8 if < 10 else 5
biasPts   = 20 if HTF aligned else 10 if neutral else 0
score = depthPts + candlePts + volPts + agePts + biasPts     # fire >= 80 (default)
cooldown = 5 bars, SHARED across both directions (anti-whipsaw)
reclaim = pending > 0 and close > band1 and close > open     # directional candle required
```

**Mechanics.** The depth curve {15, 25, 18, 10} is the interesting artifact: it *penalizes both* trivial wicks and capitulation dips — the best retest stops at the second band (a real pullback that hasn't threatened the trend). The **self-non-diluting volume baseline** (`SMA[1]`) fixes a subtle bug in naive volume-spike filters: comparing the spike bar against an average that already includes the spike bar understates the spike. The trend-age term (10–150 bars best) avoids both brand-new flips (no context) and ancient trends (exhaustion). One shared cooldown across directions is an explicit anti-whipsaw device.

**Why zero-wait.** Five bounded O(1) components; depth = a pending integer with countdown; reclaim = crossing + candle-direction check at close (or tick, if you accept forming-bar close as a running value).

---

### S3. Sweep Score (cross-reference) — *Mirage*

See M4: the same additive 0–100 pattern (wick 30 / reclaim 25 / closePos 20 / vol 15 / HTF 10) — the batch converges on **five-term ATR-normalized additive scoring** as the quality gate idiom (S1 = 8-pillar version, S2 = 5-term version).

---

### S4. Strong-Volume Override (asymmetric gate) — *Luxy*

```python
pass   = vol >= 1.5 * SMA(vol, 20)     # ordinary pass
strong = vol >= 2.0 * SMA(vol, 20)     # BYPASSES the trend filter entirely
```

**Mechanics.** Two thresholds with different semantics: 1.5× says "participation is normal", 2.0× says "institutional-size participation — the trend filter may be wrong, let the move through". An asymmetric override is worth generalizing: any *rare, expensive-to-fake* signal (volume, spread dislocation, queue imbalance on bookTicker) should be allowed to veto a *continuous, cheap* filter (trend, bias).

**Why zero-wait.** Two comparisons per tick against a streaming SMA.

---

### S5. HTF Bias with Minimum-Strength Gate — *Luxy / KD*

```python
# daily EMA20, last-CLOSED daily bar only (lookahead_off — clean):
bias_bull = close_d > ema20_d and abs(close_d - ema20_d)/ema20_d >= 2.0%
bias_bear = close_d < ema20_d and abs(...) >= 2.0%
else: bias = NEUTRAL     # weak-trend => no bias at all (no flicker)
```

**Mechanics.** The `≥ 2%` distance gate is the whole edge: without it, a price oscillating around the daily EMA flips the bias every bar (hysteresis-free flicker). The explicit NEUTRAL third state lets the caller *subtract* bias credit (S2: 10/20 points) instead of guessing. Same confirmed-bar idiom as W5 — no repaint.

**Why zero-wait.** Updated once per closed daily bar; held as a constant in between; a two-comparison state.

---

## §6 — Integration Blueprint (delta over Batch 3 L0–L5)

The Batch 3 blueprint (L0 regime → L1 levels → L2 triggers → L3 entry → L4 risk → L5 frozen risk) still stands. Batch 4 adds/refines:

- **L0 regime.** Pick ONE ratchet family as the single regime source: LTM 4-band stack (W4) is the most complete (flip band selectable, segment-stamped). Alternatives: AlphaTrend (W2) when money-flow gating matters, Lion fan (D1) as a zero-crossover veto. JOAT (S1) or strength-gated HTF (S5) as overlay bias.
- **L1 level table (frozen, per session).** Pre-compute and freeze: ORB stage edges (4×2, D6), PVP ladder (10, D3), Key-Levels polarity boxes (M5), ATR99 POI zones (M6), pivot pools 21/21 + EQH@0.15·ATR (M4), OB/iOB memory (M2, ≤150), CVD S/D zones (M1, ≤10/side), SCOB zones (M3, ≤20). All are frozen boxes/lines after creation → per-tick cost is pure crossing checks.
- **L2 triggers.** Event set, each O(1): ORB cross (buffered), sweep+score (≥50) → pending CHoCH (≤13 bars), CVD-zone creation, band retest (score ≥80), SCOB impulse, W1–W3 oscillator crosses, LVN close-cross (M7), failed-ORB-break (D6). Every trigger either (a) crosses a **frozen** level → tick-executable, (b) completes a pattern on **confirmed** bars → ≤1-bar latency, or (c) is a **countdown** → tick counter. No trigger needs intra-bar *history*.
- **L3 entry.** Tick-entry at the crossing for LTM retests / Mirage CHoCH / LVN breaks; **next-open entry** (Luxy pattern, D6) for session-anchored ORB events to avoid breakout-bar slippage. Entry price = event tick (or next open).
- **L4 risk.** Default: R1 wick-anchored SL (min 0.5·ATR) or R7 adaptive; R2 BE-after-TP1 with win=TP1 accounting; R3 reversal-on-opposite-signal (single-position model); R4 RSI ladder with sequence guards as the volatility-adaptive scale-out; R6 78.6% secondary trail as the runner manager; R5 entry-ratchet for multi-day rides (optional).
- **L5 bounded memory.** Hard FIFO caps everywhere, as the sources do: 25 pools/side, 12 reaper levels/side, 10 CVD zones/side, 8 POI/side, 20 SCOB, 150 OB/iOB, 6 ORB cycles/day/dir, 5-bar shared cooldown, 13-bar CHoCH expiry. 24/7 feeds make unbounded arrays a real memory-leak vector — the caps are mandatory, not cosmetic.
- **Tick vs close.** The Batch 3 principle holds and is *strengthened* here: Batch 4's most valuable constructs (M1 CVD zones, M7 segment profile, S1/S2 scores) are all running-state objects whose per-tick update is O(1) and whose decision boundary is a crossing of a frozen level — i.e., the exact shape a zero-wait tick engine wants. The only latency in the whole set is the ≤1-bar confirmation of bar patterns (SCOB, displacement OB, pivot pools), which is bounded and known a priori.

---

## Appendix A — Per-File Exclusions (19 files)

| File | Excluded (red line) | Kept / cross-referenced |
|---|---|---|
| Jackson_Zones | `lookahead_on` fetch as mechanism | D3 (prev-day PVP ladder) |
| iqfxpro | — (GUI only) | R5 (full) |
| Liquidity sweep (1;2RR) | — (GUI) | M8 (row 1) |
| LyroRS v1 | 16 MA kernels live in external import `LyroRS/LMAs/1` — only the ratio construction is observable | W1 (full) |
| Lion Trend | — (GUI) | D1 (full) |
| Market Matrice | HTF fetch `lookahead_on` (mechanism) | W2 (AlphaTrend TF-local) |
| Liquidity Reaper | — (GUI) | M8 (row 2) |
| Million Moves Alga | `securityNoRep` MTF ADX (`lookahead_on`); garbled UTF-8 strings (harmless) | D2 (full TF-local core); OB block = cross-ref M2 family |
| iOB | — (box drawing) | M2 (full) |
| JOAT | `FER` fn (dead code) | S1 (full) |
| MELONA | RSI 70/30 cross + RSI-linreg(140) band (standard); harmonic time/risk ratios computed but unused | M3 (SCOB); harmonics = cross-ref Batch 3 |
| Money Moves (MM PREMIUM v2) | — (GUI) | cross-ref Batch 3 MM family; D7 (WT trap); pyramiding section counters (noted, not extracted — visual section tracking) |
| Key Levels | Bjorgum pattern lib = external import/visual | M5, D4 (full) |
| Joker | 12-TF `securityNoRep` fan (`lookahead_on`); MACD(2,4,3) candle colors; 13-consecutive-close gradient; dormant consolidation detector (`showCons=false`, math noted) | W3, W6, D7, R4; divergence engine (below) |
| MONEY ALGORITHM | same 12-TF MTF (twin of Joker, ST 2.4/15 vs 3.1/25) | W3 (cross-ref) |
| Mirage Liquidity Sweep Pro | — (`[close[1],ema[1]]`+`lookahead_on` = confirmed-HTF idiom, salvageable) | M4, R1, R2 (full) |
| KD System | Pivot HTF fetch (`lookahead_on`); ALMA 8×TF (`lookahead_on`); RSI7 80/20 extremes; Elder Impulse (standard MACD/EMA); AOE "institutional zones" (buggy — uses close/open arrays instead of high/low, and trivial); VWAP/MA/PSAR (standard) | M1, M6, W5, D5, R6 (full) |
| Liquidity Trail Matrix | — (confirmed-HTF idiom salvageable) | W4, M7, S2, R1, R2, R3 (full) |
| Luxy BIG beautiful Dynamic ORB | — (all clean; FX-rate security is cosmetic) | D6, R7, S4, S5 (full) |

**Notable cross-file duplicates (extract once):** Joker ≡ MONEY ALGORITHM (same engine, ST params differ); Luxy pair = md5-identical; WaveTrend trap appears in 4 files (Joker, MONEY ALGORITHM, Money Moves, KD System); the Willy family (Mirage ≡ LTM risk engine, "Mirage-grade" per source comment) shares R1/R2 verbatim.

---

## Appendix B — Porting Notes (Binance Spot HFT: 1m klines + aggTrade + bookTicker)

1. **Volume is native.** Crypto feeds have real per-trade volume — every `MA(vol)` denominator in the batch (LyroRS, Mirage, LTM, Luxy, JOAT) works without the forex range-proxy fallbacks the sources need. Build SMA baselines from aggTrade cumulative volume.
2. **CVD zones (M1): upgrade the proxy.** Replace candle-sign delta (`±volume` by close>open) with `isBuyerMaker`-signed aggTrade delta per trade. The per-zone running CVD becomes a *true* order-flow gauge — feed it into the JOAT delta pillar (S1) as well.
3. **Segment profile (M7): O(1) per tick.** Maintain a running per-bin histogram for the active LTM segment; each aggTrade adds its volume to the bin of its trade price (exact price location — better than the source's bar-overlap approximation). Recompute POC/VA/HVN/LVN only when the argmax or a node threshold changes (event-driven). LVN levels freeze between recomputes → crossing checks are one comparison each.
4. **ORB on 24/7 (D6).** Anchor stages to a fixed UTC session (00:00 UTC daily) or run rolling 15-min "mini-ORBs" for continuous operation. Stage high/low = running max/min; freeze on completion into the per-session level table (D6 already gives the state machine).
5. **PVP ladder (D3).** Daily batch at 00:00 UTC from the closed prior-UTC-day 1d kline — no lookahead needed, no security call.
6. **Confirmed-HTF idiom (Mirage/LTM/KD/Luxy).** The `[close[1], ema[1]] + lookahead_on` pattern is *not* lookahead — it's "last closed HTF bar value". Port as: from the 15m/1h/4h/1d kline streams, always use the last **closed** bar. Never the forming one.
7. **Wick-anchored SL (R1).** aggTrade running low/high since the signal bar gives the exact wick extreme at entry time (bar close) — or intra-bar if you accept the forming wick. The 0.5·ATR minimum-distance guard is mandatory to keep fee-adjusted R sane.
8. **barssince sequence guards (R4).** Port as a monotone event log: each TP cross gets a bar-id; a TP fires only if its event bar-id is greater than the entry bar-id and its predecessor TP's event bar-id. Idempotent per trade by construction.
9. **Bounded memory (L5).** The sources' caps (25/12/10/8/6/20/150 + 300-bar expiry) are the port's memory model. On a 24/7 feed, every state array needs a hard cap with FIFO eviction or it leaks.
10. **Shared cooldown (S2).** One global `last_signal_bar` across both directions (LTM's anti-whipsaw choice) — port as a global tick timestamp, not per-direction.
11. **SL-first pessimistic resolution (Mirage/LTM).** On bar data, SL and TP in the same bar ⇒ count SL. A tick engine resolves by actual tick chronology — same math, strictly better fill assumption. Keep the pessimistic rule for backtests on klines.
12. **Win=TP1 accounting (R2).** Mark trades "secured" at TP1 (SL→BE ⇒ zero remaining risk). Optional HFT extension: scale in *more* at TP1 on secured status (risk-free added exposure) — the accounting model makes this cleanly measurable.
13. **Strong-volume override (S4).** On 1m crypto, raw 2×SMA(20) volume is rarer and spikier than on equities — consider normalizing against the same-time-of-UTC-day average (session-normalized volume) for the override tier.
14. **JOAT HMA20>286 gate (S1).** The threshold appears to be an oscillator-value gate (units not visible in context). Keep as a tunable constant and calibrate empirically on the port before trusting it as a hard gate.
15. **ORB strong-volume vs trend (D6/S4).** The "2× volume bypasses trend filter" rule interacts with L0 regime: implement it as `signal = breakout and (volume_ok and (trend_ok or strong_vol))` — the bypass is an OR inside the AND, not a separate path.

---

*Batch 4 complete: 19 unique files → 33 concepts (W1–W6, D1–D7, M1–M8, R1–R7, S1–S5). Batch totals: 46 + 37 + 52 + 33 = 168 concepts across 81 files (79 unique).*
