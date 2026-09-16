# Reverse-Engineered Trading Logic — Distilled for a Tick-Based Binance Spot Engine

**Scope:** 21 Pine Script indicator/strategy files (15.4k lines). Extracted: mathematical cores, state machines, and scoring systems.
**Red lines enforced — the following were found in the source and deliberately EXCLUDED from this document:**

| Excluded class | Where it appeared |
|---|---|
| `lookahead_on` / repaint variants | AlgoX V22 (`_lookahead` mode, ATR factor 0.1), Adaptive Ichimoku (MTF `mtfCalcState()[1]` w/ `lookahead_on` — only the *confirmed* pattern is salvageable, and the non-repaint equivalent is noted), AI Gold Scalping / ASK / 2-1 (`rp_security`), AI Vanga (none active) |
| Bar-close confirmation gates used as "fake zero-lag" | all files (`barstate.isconfirmed`); the *tick-native* equivalents are given instead |
| Lagging oscillator/MA slow crosses | EMA10/20 "trend catcher" (AI Signal), SMA8/9 cross (Ayman), 50/200 "cloud" (Ayman, ASK), RSI(14) 40/60 MTF entry (AI RSI MTF file part 1), Vanga random-walk "forecast", Gann Square of 9 |
| All GUI/drawing/table/label/alert code | every file |
| Derivatives/leverage logic | none present in this batch (all spot-price logic) |

**Tick-adaptation conventions used throughout:**
- A Pine `ta.pivothigh(L,R)` confirms R bars late. In the bot, maintain the same definition over a rolling window of ticks/1m-bars and treat the pivot as *forming* from the moment the left side is complete — i.e., trade the level as soon as it exists, not after R bars.
- "Proximity trigger" (from Ayman Entry: `close > level*0.995` / `low < level*0.999`) is the tick-engine idiom for "break without waiting for the bar close". Where a model says *break*, the bot should fire on the first trade (aggTrade) or mid print (bookTicker) crossing the level.
- `barstate.isconfirmed` → in streaming terms: "the 1m kline closed". Anything computable from closed bars is a *slow state*; anything on live price is *fast path*. The split per concept is marked.

---

## 1. WILDCARDS (Innovative / Non-Traditional Edges)

### 1.1 Quantized Epsilon-Midpoint Band ("stepped Keltner state machine")
`source: AI SWING Algo.txt`

The midpoint `m` is a state variable that moves only in discrete steps of `ε = 2.8·ATR(53)`, and only when price crosses the *previous* band:

```python
# SLOW STATE (per closed 1m bar) ------------------------------
h = rolling_max(src, 200); l = rolling_min(src, 200)   # src = EMA3(close) or close
eps = 2.8 * atr_prev                                    # ATR(53) of last CLOSED bar
upper_prev, lower_prev = m + eps, m - eps

# FAST PATH (every tick) ----------------------------------------
if price crosses ABOVE upper_prev:   m = m + eps        # state step up
if price crosses BELOW  lower_prev:  m = m - eps        # state step down
# trade when price re-crosses m after a step (alternate long/short only)
```

**Mechanics:** This is a hysteresis band that *quantizes* the trend state into ATR-spaced steps. Unlike a continuous MA cross, the direction only changes when price pays a full `ε` to displace the state, which structurally rejects chop: in a range, price oscillates inside `m±ε` and no step occurs. The use of *previous* band edges (not current) is a one-bar lookback-free hysteresis that prevents same-tick flip-flops.
**Why tick-powerful:** All state is O(1) per tick: compare `price` against two frozen numbers (`m±ε` from the last closed bar). No indicator recomputation at all. The step event is itself the signal — it fires *at the breakout tick*, i.e., zero-wait.

---

### 1.2 Rational-Quadratic Kernel WaveTrend
`source: AI Vanga V3.txt`

The raw price fed into WaveTrend is replaced by a **rational-quadratic (RQ) kernel estimate** — an RBF-kernel-weighted average where recency weight decays as a rational function of lag:

```python
# L = lookback = 8 bars, r = relative weight = 8
def rq_kernel(x, L=8, r=8):
    num = den = 0.0
    for i in range(L):                      # x[i] = i bars ago
        w = (1.0 + (i**2) / (2.0 * r * L**2)) ** (-r)
        num += w * x[i]; den += w
    return num / max(den, 1e-3)

x  = rq_kernel(hlc3)
esa = EMA(x, 10);  d = EMA(abs(x - esa), 10)
wt1 = EMA((x - esa) / (0.015 * d), 21)
wt2 = SMA(wt1, 4)
# pullback entries: wt1 crosses wt2 while wt2 <= -60 (buy) / >= +60 (sell)
# divergence: 5-point fractals on wt2 in zones (>=10/-40) & (>=45/-70);
#   bearish div = price makes HH at fractal top while wt2 makes LH
```

**Mechanics:** `w(i) = (1 + i²/(2rL²))^-r` is a rational-quadratic kernel (the RKHS kernel used in Gaussian-process regression). With r=8 it is sharply peaked near i=0 and has heavy tails relative to an exponential EMA — the estimate keeps a memory of the last 8 bars but with *non-exponential* decay, which makes the resulting oscillator less smooth than an EMA-based one (faster turn on impulses) while still suppressing single-tick noise. The rest is classic Lars-Hansen WaveTrend (auto-normalized by its own volatility `d`, hence the 0.015 scaling).
**Why tick-powerful:** The kernel is an 8-term weighted sum — trivially incremental per tick (maintain a circular buffer). It gives a WaveTrend-quality oscillator with a *different noise/impulse tradeoff* than the stock EMA version; the divergence detector is the real edge: it flags momentum failure at extreme readings, which is a mean-reversion trigger that fires at the fractal confirmation tick (2 bars after the peak — the minimum possible confirmation).

---

### 1.3 Dual Thrust with Trend-Discounted Asymmetric Coefficients
`source: AI Vanga V3.txt`

```python
# SLOW STATE: computed once at session open from the PREVIOUS bars
hh3, hc3, lc3, ll3 = max(H,-3), max(C,-3), min(C,-3), min(L,-3)   # mlen = 3
hh12, hc12, lc12, ll12 = ...                                        # nlen = 12
range_buy  = max(hh3 - lc3, hc3 - ll3)
range_sell = max(hh12 - lc12, hc12 - ll12)      # ASYMMETRIC windows

k = 0.7; disc = 0.5
# FAST PATH (ticks within the session, anchored to session OPEN):
BT = open_session + k_buy  * range_buy
ST = open_session - k_sell * range_sell
# trend discount (determined by prior bar direction):
#   uptrend  -> k_buy  = 0.35, k_sell = 1.05   (long gate tighter, short gate looser)
#   downtrend -> k_buy  = 1.05, k_sell = 0.35
entry_long  when price >= BT and uptrend context   (filter: ATR(1)>ATR(10))
entry_short when price <= ST and downtrend context (filter: RSI(vol,14) > HMA(.,10) > 49)
```

**Mechanics:** Classic Dual Thrust, upgraded twice. (a) The buy and sell ranges come from *different lookbacks* (3 vs 12), so the two trigger distances adapt to different volatility memory on each side of the book. (b) The coefficients are multiplied by `1±disc` based on the prevailing direction — the system makes it *easier* to trigger with the trend and *harder* against it, i.e., the breakout threshold is itself a trend filter.
**Why tick-powerful:** This is the single most bot-native concept in the entire batch: both levels are **frozen at the session open** (computable from 12 historical bars + the open price, all present in the first 1m kline of the session). After that it is two `if price >= level` checks per aggTrade — the purest form of zero-wait execution, with a built-in trend asymmetry.

---

### 1.4 TrendShift — SuperTrend Ratchet Applied to the RSI Oscillator, with ATR-of-the-RSI Bands
`source: ASK.txt`

```python
rsi2  = RSI(close, 50)
Rsii  = EMA(rsi2, 30)                       # double-smoothed RSI ("fast line")
tr_r  = abs(Rsii - Rsii_prev)               # "true range" of the oscillator itself
wwma  = WILDERR(tr_r, 50)
atrrsi = WILDERR(wwma, 50)                  # self-adaptive band width
band  = 4.236 * atrrsi

up   = Rsii + band;  dn = Rsii - band       # recompute each bar
# RATCHET (identical final-band logic to SuperTrend, applied to the oscillator):
#   while fast line is ABOVE slow line: slow := max(slow, dn)     (ratchets up)
#   while fast line is BELOW slow line: slow := min(slow, up)     (ratchets down)
#   direction flips when fast line crosses the slow line
BUY  = crossover(Rsii, slow) and Rsii < 45    # flip from oversold side
SELL = crossunder(Rsii, slow)  and Rsii > 55  # flip from overbought side
```

**Mechanics:** This is a genuine novelty in the batch: the SuperTrend *state machine* (ratcheted final band + flip-on-cross) transplanted onto an oscillator instead of price. The band width is the RMA of the RMA of |ΔRSI| — i.e., an "ATR of the RSI" — so the band widens automatically when the oscillator itself is choppy and tightens in calm momentum. The 45/55 gate guarantees flips only occur when momentum is on the correct side of neutral.
**Why tick-powerful:** The band width and fast line are closed-bar states; the *flip test* is a comparison of the live RSI-50/EMA30 against one frozen ratchet level, plus a cross detection. Fires exactly when the oscillator crosses its own trailing band — no bar close needed for the cross event.

---

### 1.5 "Sticky Memory Level" — Regime-Jump + Fixed-Drift Support/Resistance
`source: 2-1 strategy.txt (Trend Levels)`

```python
gate = ATR(200) * 15
# SLOW STATE:
if abs(close - level) > gate:      level = close;  hold = gate / 2     # regime jump
else:                              level += os * (hold / 50)            # os = ±1 (level's own slope)
# FAST PATH: resistance/support = level, with bands at level ± hold/2, level ± hold
```

**Mechanics:** A level that is *almost frozen*: it drifts by a fixed `ATR/100` per bar in the direction of its own trend, and teleports to price only when price has displaced by 15×ATR(200) (a true regime break). Between extremes it behaves like an immutable memory of "where price settled last" — a model of institutional price anchoring that never repaints and never decays.
**Why tick-powerful:** One scalar + one sign per symbol. The level exists forever and is a static trigger price — the ideal object for a limit-order maker: you know the exact price where the level "is" and can pre-place working orders at `level ± hold/2`.

---

### 1.6 Smoothed Range Filter (dual ratcheted band on price)
`source: AI Gold Scalping.txt`

```python
r = EMA(EMA(abs(x - x_prev), t), 2*t - 1) * m        # t=13, m=8 (fast tier); t=200, m=2.8 (slow tier)
# RATCHETED FILTER (the actual state):
if x > filt_prev: filt = max(filt_prev, x - r)       # can only step up
else:             filt = min(filt_prev, x + r)       # can only step down
# STATE MACHINE:
up   += 1 while filt is rising;  up = 0 when filt falls
bull_cond = x > filt and up > 0
signal = bull_cond and last_state == -1               # state FLIP only
# Two tiers in parallel: standard = avg(tier13, tier200); strong = avg(tier13, tier200@20)
```

**Mechanics:** `r` is a double-EMA of the absolute increment — a volatility estimate of the *price path*, not the bar range. The filter is a one-sided ratchet: in an uptrend it only rises (to `x − r`), in a downtrend only falls. A signal is a *state flip* of "price above/below the ratchet with momentum" — the two-tier version (fast + slow range) acts as a built-in resonance filter: strong signals require both time scales to agree.
**Why tick-powerful:** Everything is one comparison + one max/min per tick. The flip semantics (trade only on state change, not while in state) gives you a natural entry/exit symmetry for a scalper: enter on flip, exit on the opposite flip.

---

### 1.7 Instantaneous-Range SuperTrend (band width = current bar range, not ATR)
`source: AI Signal.txt / AI Signal Remastered.txt`

```python
# "Keltner range" here degenerates to the raw bar range:
rangec = 2 * (high - low)                            # SMA(src,len) cancels
upper = src + factor * rangec / 2     # factor = 2.8  ->  src + 2.8*(H-L)
lower = src - 2.8 * (high - low)
# standard SuperTrend final-band ratchet on {upper, lower}; flip on close cross
```

**Mechanics:** Replacing ATR (an averaged range) with the *current* bar's range makes the band width an **instantaneous volatility gauge**: after a spike bar the bands are instantly wide (no trailing-stop whipsaw inside the spike's own noise), and in a lull the bands collapse tight (fast flip). It is a SuperTrend whose noise floor is local rather than smoothed.
**Why tick-powerful:** On a 1m feed the band is rebuilt every minute from two numbers (H, L of the forming bar). In tick mode you can rebuild the candidate band continuously from the current bar's running H/L — the ratchet still uses closed-bar state for the flip decision, so you get an instant-volatility band with a stable trigger.

---

### 1.8 Cumulative (Non-Decaying) ATR as Stop-Band Scale
`source: AlgoX V22 SuperTrend.txt`

```python
cum_atr = cumsum(ATR(140)) / (bar_index + 1)     # lifetime mean ATR, never decays
dev_base  = 2.618 * cum_atr
dev_add   = 0.618 * cum_atr
stop:  if price > stop: stop = max(stop, price - dev_base)
       if price < stop: stop = min(stop, price + dev_base)
bands: stop ± dev_base, stop ± (dev_base + dev_add)   # Fibonacci ladder
```

**Mechanics:** A rolling ATR slowly adapts to regime changes — which is exactly what you do *not* want in a trailing stop: the stop distance breathes with recent volatility and gets knocked out by the very volatility that just widened it. The cumulative average is a **stationary volatility reference** (slowly learning, effectively fixed over a trading day), so stop geometry is stable and comparable across trades; the Fibonacci ladder (1 / 1.618 / 2.618 / 3.236) then gives a fixed risk map around that stable spine.
**Why tick-powerful:** `cum_atr` is one running sum — O(1) update, and the stop is one ratchet comparison per tick. It also gives a *session-level* volatility constant you can pre-compute at startup from the kline history.

---

### 1.9 Volume-Profile Order Block (grid-distributed volume inside the OB)
`source: AI Vanga V3.txt (embedded "Volume Profile Order Blocks" engine, in source comments)`

```python
# trigger: N consecutive same-direction closes (tuning = 7), then the origin bar is N-1 bars ago
origin = bar[-7]
OB = [min(low[-7..]), max(high[-7..])]              # impulse block
# volume distribution: split OB into G=10 horizontal slices
for bar in OB window:
    for slice in slices:
        overlap = max(0, min(bar.H, slice.top) - max(bar.L, slice.bot))
        if bar.H - bar.L > 0:
            slice.vol += overlap / (bar.H - bar.L) * bar.V     # proportional volume
POI = slice with max volume                                # point of interest
# mitigation: close engulfs 25/50/75/100% of the OB height -> zone consumed
# (box width ∝ slice volume => horizontal volume profile, POC = longest bar)
```

**Mechanics:** Instead of treating an order block as an empty rectangle, each price slice carries the *proportionally allocated* volume that traded through it during the impulse. The POC slice is where the institutional footprint is densest — the price the block is most likely to re-attract. The 25/50/75/100%-engulfed mitigation ladder gives a graded consumption: a partial fill ≠ a dead zone.
**Why tick-powerful:** The grid is built once (from 7 closed bars) and never recomputed; every tick it is just "which slice am I in?" The POC is a single price — a natural resting limit level for a maker strategy, with the slice-volume ratio as the confidence weight.

---

### 1.10 Trend-Speed Wave Statistics (wave dominance scoring)
`source: AI Vanga V3.txt (Trend Speed Analyzer)`

```python
# dynamic trend line: dynamic EMA with volatility-normalized length + accelerator
L_dyn = 5 + norm(|close|, 200) * 45                          # 5..50, position within ±max|close|
alpha = (2/(L_dyn+1)) * (1 + 5.0 * (|Δclose| / max|Δclose|200))   # accelerates on impulses
trend = EMA with time-varying alpha
# "speed" = wave size = Σ (RMA(close,10) − RMA(open,10)) since last trend-line cross
# maintain rolling stats of wave sizes:
bull_avg, bull_max = mean/max of bullish waves (lookback 100)
bear_avg, bear_max = mean/max of bearish waves
dominance_avg = bull_avg - |bear_avg|          # net directional power
ratio_avg     = current_wave / bull_avg        # is THIS wave stronger than history?
```

**Mechanics:** A wave = the accumulated close-minus-open delta (a net-order-flow proxy, since on Binance Σ(close−open) ≈ net buy pressure per bar) accumulated until the dynamic trend line is crossed. Comparing the *current* wave to the distribution of past waves (`ratio > 1` = anomalous strength) is a change-point-style detector: it flags when the current impulse is historically unusual *for this market's own volatility state*.
**Why tick-powerful:** `speed += (RMA(c,10) − RMA(o,10))` is O(1) per bar; per tick you accumulate `±(Δprice)` directly. The wave stats are a bounded-deque mean/max. The "current wave ratio" is the trigger — it fires mid-wave, not at wave end.

---

### 1.11 Channel Break with Volume-Tercile Classification
`source: Advanced SMC.txt (Trend Channels With Liquidity Breaks)`

```python
# two consecutive pivot highs with slope <= 0 (atan2(dy, dx) <= 0) => DOWN channel
offset = 6 * ATR(10)
channel lines: pivot_line ± offset/7 (edges), pivot_line − offset (far edge), center
slope dydx extended forward bar-by-bar
# FAST PATH: break = close beyond channel line
# VOLUME CONTEXT at the break:
vol_n = normalize_0_100(WMA(volume, 21) over 100 bars)
rank  = percentile_nearest_rank(vol_n, 75, 100)
tag = "LB" if vol_n < SMA(vol_n)
    else "MB" if vol_n < SMA(rank)
    else "HB"                      # high-volume break = institutional, low-volume = suspect
```

**Mechanics:** The channel is built from two *same-type* pivots (a lower-high pair for the down channel) with ATR-scaled parallel edges — i.e., a regression-free channel whose width is 6 ATR. The break is graded by where the break-bar volume sits within its own 100-bar distribution and its 75th-percentile rank: a low-volume break of a channel is statistically far more likely to be a fake.
**Why tick-powerful:** The channel is two lines (slope, intercept, width) — four floats, O(1) per tick. The volume tag is evaluated once at the break event. This is a clean "structure break + flow confirmation" primitive for the fast path.

---

### 1.12 Equal-High/Low Clustering with ATR Tolerance (multi-touch liquidity)
`source: Advanced SMC.txt + Advanced Liquidity Sweep.txt`

```python
# Advanced SMC: zigzag pivots (len 7, 1-right); tolerance = ATR(10)/6.9 ≈ 0.145·ATR
walk zigzag history from newest:
    count same-side pivots within ±tolerance of current pivot (stop at first beyond range)
    if count > 2:  liquidity zone = [avg(min,max) ± ATR/6.9], origin = first touch bar
break: price beyond zone edge => sweep event; sweep box = level ± 2.3·ATR(10)
# Advanced Liquidity Sweep: same-side pivots within 0.10·ATR(14) merge into one EQH/EQL,
#   touches counter increments on every merge; touched = swept => level consumed
```

**Mechanics:** Both engines formalize "equal highs/lows": identical (within a volatility-scaled epsilon) same-side swing prices are *not* two levels but one level with a *touch count*. The touch count is the liquidity estimate — each touch implies another cluster of resting stop orders. Zone geometry is centered on the cluster mean with ATR-scaled half-thickness.
**Why tick-powerful:** The cluster is a (price, count, origin) triple. As price approaches within `tolerance`, you *already know* the level's strength before the sweep — the count is the weight for sizing. Sweep detection itself is `price > level` + (optionally) close-back-inside, both tick-evaluable.

---

## 2. MACRO DIRECTIONAL FILTERS (Low-Lag, Non-Repainting)

### 2.1 Anchored Powered KAMA with Online (Welford) σ Bands
`source: AI Vanga V3.txt (Anchored Powered KAMA, LuxAlgo variant)`

```python
# anchor = session boundary (auto: intraday chart -> daily anchor)
on_new_session:  counter = 1; kama = price; welford = 0
per bar/tick:
    counter += 1
    ER = abs(price - price_anchor) / sum(|price - price_prev| since anchor)   # efficiency ratio
    SC = ER ** 2                                                              # "powered" (power=2)
    kama = SC * price + (1 - SC) * kama_prev
    welford += (price - kama_prev) * (price - kama)                           # online sum of sq. dev.
    sigma = sqrt(welford / counter)
bands: kama ± σ (inner), kama ± 2σ (outer)
```

**Mechanics:** KAMA's smoothing constant is the efficiency ratio (net move / total path length since anchor) raised to a power. ER ≈ 1 in a clean trend → KAMA tracks nearly 1:1 (zero lag); ER ≈ 0 in chop → KAMA freezes (zero noise). The "powered" form squares ER, exaggerating the difference. The Welford accumulator gives a *running standard deviation of the deviation from the KAMA itself* — the bands are the KAMA's own confidence interval, computed in O(1) with no window storage.
**Why tick-powerful:** This is arguably the single best macro filter in the batch for streaming: every quantity is a scalar accumulator (counter, Σ|Δp|, welford, kama). No arrays, no windows. It is *anchored to the session*, so it measures "efficiency of today's move" — the right regime question for a scalper. Direction = sign(price − kama), strength = |price − kama|/σ.

---

### 2.2 Volatility-Adaptive Donchian Period
`source: Adaptive Ichimoku Nexus.txt`

```python
atr  = ATR(14)
vol_ratio = (atr - min(atr, 50)) / (max(atr, 50) - min(atr, 50))      # 0..1 over 50-bar range
len_t = round(base * (1 + s * (1 - 2*vol_ratio)))   # s = 0.4, clamped to base*(1∓s)
# high volatility (vol_ratio→1) -> period shrinks to base*0.6 (faster line)
# low volatility  (vol_ratio→0) -> period grows to base*1.4 (slower line)
line = (highest(high, len_t) + lowest(low, len_t)) / 2     # adaptive Donchian mid
```

**Mechanics:** The *window length* is the adaptive variable, not the smoothing. When volatility spikes, the reference line tightens its lookback and catches new structure faster; when the market goes quiet, it lengthens to avoid noise. Applied to the Ichimoku Tenkan/Kijun (9/26) it yields a volatility-gated TK-cross.
**Why tick-powerful:** The period only changes when the 50-bar ATR envelope moves (rare); in between, `highest/lowest` are standard rolling extrema maintained per kline. The adaptive length is a *slow* parameter, the Donchian mid is a *fast* state — clean separation.

---

### 2.3 ALMA Close/Open Dual-Series Cross (bar-direction microtrend on MTF ×18)
`source: ALGOX V11.txt`

```python
closeS = ALMA(close, len=2, offset=0.85, sigma=5)     # ultra-short ALMA: weights pile at the tail
openS  = ALMA(open,  len=2, offset=0.85, sigma=5)
signal = crossover(closeS, openS) on TF; confirmed on TF*18 (e.g. 1m -> 18m) with confirmed values
# ALMA weights: w(i) ∝ exp(-i²/(2σ²)), shifted by offset (0.85 -> asymmetric, lag-minimizing)
```

**Mechanics:** Comparing the smoothed *close* series with the smoothed *open* series is a direct measure of **intra-bar directionality** (net bar drift) rather than price level. An ALMA(2, 0.85, 5) is essentially a 2-bar asymmetric kernel whose mass sits on the newest sample — a near-instantaneous "is this bar's close drifting above its open" detector. The cross of the two series = the moment net bar drift flips sign.
**Why tick-powerful:** ALMA is a fixed 2-term weighted sum — computable per tick from (open, close) of the forming bar. In live operation: `ALMA(close_live)` vs `ALMA(open_fixed)` — the open side is constant within the bar, so you are watching one live scalar cross one frozen scalar. The ×18 MTF confirmation just requires the 18m kline stream, which you already have.

---

### 2.4 Anchored VWAP Z-Score (streaming mean-displacement signal)
`source: Anchored VWAP Trade Planner.txt`

```python
# anchored VWAP, session reset (src = hlc3):
S_pv += price*volume;  S_v += volume        # reset at session open
vwap = S_pv / S_v
d = price - vwap
z = d / rolling_stdev(d, 20)                # z-score of displacement from fair value
LONG  when price > vwap and z >= +1.5      (cooldown 20 bars)
SHORT when price < vwap and z <= -1.5
```

**Mechanics:** The signal is "price is more than 1.5 historical-σs away from volume-weighted fair value *and on the far side of it*" — a displacement/extreme condition, not a cross. The rolling stdev of `d` normalizes for the session's own mean-reversion envelope, so 1.5σ has the same rarity every day.
**Why tick-powerful:** VWAP is the canonical streaming quantity: two running sums. `d` and its rolling stdev are O(1) per tick. The z-test fires *the instant* the tick crosses the σ boundary — earlier than any bar-close formulation, and the level (`vwap ± 1.5·σ_d`) is known in advance for pre-placed orders.

---

### 2.5 Gaussian IIR Trend + Flattening LinReg
`source: 2-1 strategy.txt (Smoothed Gaussian Trend Filter, AlgoAlpha)`

```python
freq = 2π/15
factorB = (1 - cos(freq)) / (1.414**(2/3) - 1)
alpha = -factorB + sqrt(factorB**2 + 2*factorB)
# 3rd-order cascaded Gaussian (IIR, binomial coefficients):
y1 = αx + (1-α)y1'
y2 = α²x + 2(1-α)y2' - (1-α)²y2''
y3 = α³x + 3(1-α)y3' - 3(1-α)²y3'' + (1-α)³y3'''
final = linreg(y3, len=22, offset=7)        # offset≠0 -> FLATTENS the slope (de-waves)
state: trend = sign(final - final_prev);  ranging = (trend vs supertrend(final, 0.15, 21) disagree)
```

**Mechanics:** A true Gaussian filter implemented as a *recursive* cascade — an IIR approximation of the zero-phase FIR Gaussian with minimal lag (FIR Gaussians of 15+ bars have 7+ bar phase lag; this costs nothing). The linreg with nonzero offset is a deliberate trick: fitting a line with offset 7 over 22 bars *flattens* the output (reduces curvature), producing a piecewise-flat trend that only turns on sustained displacement. The `ranging` flag (slope vs trailing-band side disagree) is a regime gate that kills signals in chop.
**Why tick-powerful:** Four scalar recurrences + one 22-point linreg (maintain Σx, Σx², Σt, Σt², Σtx). All O(1) per tick. You get an Ehlers-class low-lag trend line at integer-arithmetic cost.

**Companion low-lag filters found in the batch (same class, ready to port):**
- **SuperSmoother** (ALGOX V11): `a1=e^(-√2π/L); b1=2a1·cos(√2π/L); c2=b1; c3=-a1²; c1=1-c2-c3; s=c1·(x+x')/2 + c2·s' + c3·s''` — zero-phase, near-zero-lag 2nd-order IIR.
- **AMLAG** (ABO LANA): `l0=(1-b)a+b·l0'; l1=-b·l0+l0'+b·l1'; l2=-b·l1+l1'+b·l2'; l3=-b·l2+l2'+b·l3'; A=(l0+2l1+2l2+l3)/6` — an adaptive-lag approximation whose 18 alpha-averages (b=0.10…0.95) on `open` form a lag-cancellation ribbon; the multi-alpha average is the edge (single-alphas still lag; the composite does not).
- **T3** (AI SWING): 6 cascaded EMAs, `α = 2/(2+(per-1)/2)` (per=14 → α≈0.235); signal = cross of cascade stage 0 vs 5 — a pure low-lag resonance detector.

---

### 2.6 Multi-Scale Slope+Stack Regime Classifier
`source: AlgoX V22 SuperTrend.txt (MA ribbon) + ASK.txt (Donchian state)`

```python
# Six Fibonacci-scale EMAs {5, 8, 13, 21, 34, 55}:
all_rising  = all(ema_i > ema_i_prev for i in scales)
trend_up    = all_rising and not all_rising_prev            # edge-triggered
mega_up     = all_rising and (ema5>ema8>ema13>ema21>ema34>ema55)   # slope AND full stack

# Donchian state channel (30):
state = +1 if close > highest(30)[:-1]
       = -1 if close < lowest(30)[:-1]
       = hold previous otherwise                                # hysteresis by default
```

**Mechanics:** The ribbon turns "trend" from a line-crossing into a *6-dimensional slope state*: `all_rising` is the weakest form (momentum across scales), the full stack ordering is the strongest (geometric order of volatility scales). The Donchian "hold previous" clause is a state channel: it only changes on a 30-bar extreme, which is what makes it a *regime* filter rather than a signal.
**Why tick-powerful:** Both are comparisons against maintained extrema/EMAs — O(1) per tick, and both are *discrete states* (up/down/ranging), which is exactly what a bot's strategy router needs (e.g., "only scalp-long when mega_up or trend_up, else maker-only").

---

### 2.7 Nadaraya–Watson Envelope (nonparametric fair-value curve + MAE band)
`source: Advanced SMC.txt`

```python
# Gaussian-kernel local regression over a 500-bar window, bandwidth h = 10:
y_i = Σ_j x_j · exp(-(i-j)²/(2h²)) / Σ_j exp(-(i-j)²/(2h²))
MAE = (1/N) · Σ_j |x_j - y_j|
upper band = y_i + 3·MAE   (upper fit on low, lower fit on high)
# signals: SMA7(low) crossing the upper band / SMA30(high) crossing the lower band
```

**Mechanics:** A nonparametric estimate of the *fair-value surface* of the series, with the band width set by the fit's own mean-absolute-error (data-driven, not σ-based). It adapts shape to whatever curvature the market has — trend, cycle, flat — with no model assumption.
**Why tick-powerful (with caveat):** The O(N²) naive form is too heavy per tick, but the kernel has compact support: with h=10, `exp(-i²/200) < 1e-6` beyond |i|≈22 — so it is a **45-term** weighted average per point, and only the newest point needs recomputing per bar (O(45) per bar, O(1) amortized per tick). That is well within budget for a 1m kline loop and gives a genuinely low-lag nonparametric baseline to gate entries (trade only when price is outside the ±3·MAE band in the trend direction).

---

### 2.8 Six-EMA Momentum-Stack + QQE Ratchet Bands (oscillator-side regime)
`source: ASK.txt`

```python
rsiMa = EMA(RSI(close, 6), 6)
delta = EMA(EMA(|ΔrsiMa|, 11), 11) * 3.0
# ratcheted QQE bands:
while rsiMa rising:  long_band  = max(long_band,  rsiMa - delta)
while rsiMa falling: short_band = min(short_band, rsiMa + delta)
trend := +1 on cross(rsiMa, short_band);  -1 on cross(rsiMa, long_band)
```

**Mechanics:** The bands are ratchets (they only move in the favorable direction), so the oscillator must *break its own trailing band* to flip — the same anti-whipsaw machinery as SuperTrend, applied to a 6/6 RSI. The 6/6 RSI is fast enough to be a scalping oscillator while the ratchet kills most of its noise.
**Why tick-powerful:** Two ratchet scalars + a cross. The flip fires at the oscillator cross tick, and the bands are known in advance.

---

## 3. MARKET MICROSTRUCTURE (OB / FVG / MSS / Sweeps — No Delayed Closures)

### 3.1 BOS / CHoCH State Machine on Monotonic Fractals
`source: Advanced SMC.txt`

```python
# O(1) monotonic-pivot test (length L=5, p = L/2 = 2):
#   dh = Σ_{i=0}^{p-1} sign(high[p-i] - high[p-i+1])     (last p bar-to-bar signs)
#   bull_fractal at bar (now-p)  <=>  dh == -p            (all p steps since pivot DOWN)
#                                    and dh at (now-p) == +p   (all p steps before pivot UP)
#                                    and high[p] == max(high[-L:])
#   (strictly monotone up-then-down peak; no ties allowed => deterministic, no repaint)
state: os = 0; last_swing_high = (value, crossed_flag)
on new bull_fractal: last_swing_high = (value, crossed=False)
if close crosses ABOVE last_swing_high and not crossed:
    label = CHoCH if os == -1 else BOS        # first break against prior regime = CHoCH
    os = +1; crossed = True
    new_support = min(low between broken pivot and now)   # next level to defend
# symmetric for bearish
```

**Mechanics:** The fractal is defined by *monotonicity of the sign sequence*, not by comparison against neighbors — a stricter, faster-confirming swing definition (it can confirm the instant the last bar of the pattern prints, and it never re-classifies). The CHoCH/BOS distinction is a *state* question (was the previous regime opposite?), not a pattern question: the first structural break after a bearish regime is a CHoCH, subsequent breaks are BOS. Each break immediately installs the *opposite* extreme as the next level (the lowest low of the impulse that just broke structure) — a self-continuing level ladder.
**Why tick-powerful:** The sign-sum is two counters updated per tick; the cross is one comparison. The MSS event fires on the crossing tick, and the *next* level is known at the moment of the break — you can place the exit at the impulse low while still entering.

---

### 3.2 Volumetric Order Block with Breaker Conversion and IoU Merge
`source: AI RSI MTF STRATEGY.txt (embedded "AI OB MTF" engine)`

```python
# swing: bar where high[len] == max(high[-len-1:])  (len = 21) -> confirmed top
# BULLISH OB: when close breaks above a confirmed swing top:
zone_bot = min(low[i] for i in [swing_bar .. now])          # the impulse low
zone_top = high[bar_of(zone_bot)]                            # high of the SAME bar (origin bar)
accept if (zone_top - zone_bot) <= 3.5 * ATR(10)             # size filter
vol = V[now] + V[1] + V[2]                                   # block footprint volume
# LIFECYCLE:
if low < zone_bot:  state = BREAKER;  record break_time, break_volume    # not deleted!
elif high > zone_top and state == BREAKER:  delete (mitigated breaker consumed)
elif high > zone_top and state == OB:       delete (fully mitigated)
# MERGE: same-direction OBs with IoU > 0 -> union box, volumes summed
# display weight: min(obHighVol, obLowVol)/max(...) = "absorption %" of the block
```

**Mechanics:** Three non-standard ideas: (1) the OB is the **origin bar of the displacement leg** (the bar that made the impulse low, extended to its own high) — the bar where the aggressive order flow actually executed; (2) a block broken by price does not die — it *converts to a breaker*, and its polarity flips (a broken bullish OB becomes a bearish level), with the break volume recorded as strength; (3) overlapping same-direction blocks are unioned by IoU with volumes added, so a cluster of OBs becomes one stronger block.
**Why tick-powerful:** Creation needs one confirmed swing + one level cross (both tick-evaluable). The lifecycle is three comparisons per block per tick. The breaker conversion is a rare, high-information event (a level changing polarity *with recorded volume*) — precisely the kind of signal that cannot be derived from any indicator and is trivial to implement.

---

### 3.3 Order-Block Lifecycle: Origin-of-Leg Boxes with TESTED / FILLED States
`source: 2-1 strategy.txt (Clustering Clouds OB engine)`

```python
# fast pivot: high[1] > high and high[1] > high[2]  (confirms 1 bar after the extreme)
# maintain last-2 swing highs and last-2 swing lows (price + bar index)
# DEMAND box: when a NEW swing high is higher than the previous one (HH confirmed),
#   origin = the most recent swing LOW that predates it
#   box = [pivot_low , min(high[origin], high[origin+1])]      # top trimmed to the leg start
# SUPPLY box: symmetric on LL
# STATE MACHINE (delays: test=3 bars, fill=3 bars):
FRESH -> TESTED:  price re-enters the box from the opposite side  (box dims)
FRESH/TESTED -> FILLED: price closes beyond the far edge           (box removed)
```

**Mechanics:** The box is anchored to the *origin of the leg that just broke structure* (the last LL before the HH that made the demand leg), and its top is trimmed to the first bar of the leg — i.e., the exact price range where the leg *started*, not where it ended. The tested/filled two-stage lifecycle encodes the SMC premise: a first retest (dip back into the box) is the intended entry; a close through the far edge means the orders are exhausted.
**Why tick-powerful:** Pivot is 1-bar-confirmed (the fastest reliable pivot in the batch). Box creation is event-driven; the state transitions are two level comparisons. The TESTED event *is* the entry signal — it fires on the first tick back inside the box after the break.

---

### 3.4 FVG with Consequent-Encroachment Lifecycle and Fill-Counter Alerts
`source: Advanced SMC.txt (FVG + CE engine)`

```python
# 3-candle gap (shifted window in source: big middle candle = bar[2]):
bull_fvg = low[3] > high[1]        # zone [high[1], low[3]]
bear_fvg = high[3] < low[1]        # zone [high[3], low[1]]
CE = midpoint = (top + bottom) / 2
# LIFECYCLE (per gap, max 12 active):
MITIGATED at CE touch:   bull FVG: high >= CE   (removes from "active", counts -1)
FULL FILLED:             bull FVG: high >= top  (separate counter)
# alert semantics: a "threshold crossed" event = the running sum of fill-counters
#   increased (upper gap consumed) or decreased (lower gap consumed)
# session variant: only the FIRST FVG of the session is tracked (session FVG);
#   mitigated when CLOSE passes the far edge
```

**Mechanics:** The distinction between *CE mitigation* (50% filled — the gap is "seen") and *full fill* (the gap is gone) is the key refinement: price that only reaches CE has consumed half the inefficiency, and the remaining half is a *magnet* (price tends to complete the fill). The counter-sum formulation turns a bag of boxes into two scalar streams (upper-fill count, lower-fill count) whose deltas are the alert events.
**Why tick-powerful:** Each FVG is (top, bottom, state). Per tick: up to 12 two-comparison checks. The CE level is a resting limit price in its own right; the first touch of CE is a tick event, and the "magnet" (expectation of full fill) is a known target.

---

### 3.5 Strict Swing-Failure Pattern (SFP) with Cooldown and Swing Death
`source: Advanced SMC.txt`

```python
pLow = pivotlow(low, 20, 20)   # and its value, value-confirmed
bullish_SFP = (low < pLowVal)                       # sweep of the level
            and (close > pLowVal)                   # close back above
            and (open  > pLowVal)                   # OPEN also back above (rejection)
            and (low == lowest(low, 20))            # the sweep bar is the 20-bar extreme
            and (lowest(close, 20) >= pLowVal)      # no close below the level in the window
signal = SFP[3]                                      # wait 3 bars (let the trap run)
       and close > pLowVal and close[1] > pLowVal[1] and close[2] > pLowVal[2]  # 3 closes hold
       and bars_since_last_signal >= 10              # cooldown
# SWING DEATH: after 5 consecutive closes beyond a swing level, the swing is
#   invalidated and its line is stopped (levels that keep failing stop being traded)
```

**Mechanics:** Five independent conditions on the sweep: it must be the extreme bar, both *open and close* must be back inside (the open condition catches the reversal within the same bar — the stop-hunt wick that couldn't even hold the close), and the surrounding window must show no prior close-below (the level was real before the sweep). The 3-bar hold + cooldown convert a one-tick wick into a *confirmed trap*. The swing-death rule is a level-management policy: a level that fails repeatedly is retired, not re-traded.
**Why tick-powerful:** The SFP condition is fully evaluable at the close tick of the sweep bar (open is known, low is known, close is known, and the 20-bar stats are maintained). In a pure tick engine you can fire at the moment `price` returns above the level *and* the bar's open was already above — i.e., during the same bar, one wick earlier than the Pine version.

---

### 3.6 Liquidity Void (ATR200-Scaled Displacement Gap)
`source: Advanced SMC.txt`

```python
bull_void = (low - high[2]) > ATR(200)      # bar's low is >1σ_daily above the 2-bar-ago high
        and low > high[2]
        and close[1] > high[2]
# void zone = [high[2], low], subdivided into 13 equal slices
# invalidation: a CLOSE crosses any slice midline (the void starts filling)
# visual aging: slices gray out after 21 bars unfilled
```

**Mechanics:** A "void" is a displacement so large (more than a full long-horizon ATR) that the market left a hole no orders filled. The 13-slice subdivision turns the void into a fill-tracker: each slice crossed by a close is one-thirteenth of the displacement re-priced. The long ATR (200) as the scale makes the detector regime-independent: a 1.5% move is a void in a quiet regime, noise in a volatile one.
**Why tick-powerful:** Three comparisons per tick against maintained ATR200 and bar extremes. The slice midlines are 12 pre-computed prices — a full fill-map of the displacement, ideal for placing ladder orders as the void backfills.

---

### 3.7 Two-Leg Imbalance (body-based FVG variant)
`source: Advanced SMC.txt (Imbalance Finder)`

```python
top_imb  = (low[2] <= open[1]) and (high >= close[1]) and (low[2] - high) > 0
           -> zone [high, low[2]]     (down-move imbalance, bearish)
bot_imb  = (high[2] >= open[1]) and (low <= close[1]) and (low - high[2]) > 0
           -> zone [high[2], low]     (up-move imbalance, bullish)
```

**Mechanics:** Unlike the 3-candle FVG (wick-to-wick), this tests the **bodies**: the middle candle's open/close brackets where the displacement started/ended. It is the ICT "2-legged" construction: candle 1 sets the range, candle 2 must fully displace through it. The size condition (zone height > 0) rejects doji displacements.
**Why tick-powerful:** Evaluable as soon as the third bar's extreme extends — i.e., *during* the displacement, before it finishes. That is the earliest possible imbalance detection in the batch.

---

### 3.8 SMT (Smart Money Tool) Cross-Symbol Divergence
`source: Advanced SMC.txt`

```python
# matched pivots (3/3) on two correlated instruments (source: ES vs YM):
on new pivot k of symbol X at price y2 (prev pivot y1), with symbol Y's k-th pivot sym_y2:
SMT_div = (y2 - y1) * (sym_y2 - sym_y1) < 0     # directions of the two pivots disagree
# pivot counter sync resets when either instrument makes a fresh extreme
```

**Mechanics:** When two instruments that should move together print *opposite* swing directions on the same swing count, the weaker one has failed — a leading indicator of the move to come. The pivot-counter synchronization (reset on fresh extreme) keeps the two series aligned without a time-sync mechanism.
**Why tick-powerful:** On Binance this maps directly to BTC vs ETH (or BTC vs the same pair's 1m vs 15m). Per symbol you maintain the last two pivots; the test is one sign product per pivot event. Pivot events are rare, so the cost is negligible.

---

### 3.9 Strength-Weighted S/R Clusters with Volume-Confirmed Breaks
`source: AI RSI MTF STRATEGY.txt (All Market Action) + Advanced SMC.txt (LuxAlgo MTF S/R)`

```python
# CLUSTERING (All Market Action variant):
cwidth = 0.02 * (highest(200) - lowest(200))          # cluster radius = 2% of 200-bar range
for each pivot (10/10, within 200 bars):
    cluster all pivots within cwidth of the seed
    strength = 20 * (# pivots in cluster)
    strength += # bars in 200 window whose [low,high] touched the cluster
rank top-5 clusters; suppress any cluster inside a stronger one
# BREAK VALIDATION (LuxAlgo MTF S/R variant):
pivot 15/15; tolerance = TR * (1/30);  a level needs >= 3 touching pivots
break = first CLOSE beyond the level
false-break veto: (avg(vol, 2 bars) - avg(vol, 15 bars)) / avg(vol, 15 bars) >= 0.30
                  # a break without a volume impulse is not a break
retest = touch within TR/30 after the break
zone half-width = (ATR30 / price) * (100/3) %       # dynamic, price-normalized
```

**Mechanics:** Two complementary strength metrics: *structural* (how many pivots and touches the level has — each touch = more orders resting there) and *flow* (does the break bar's short-term volume exceed its 15-bar baseline by 30%+ — the false-break veto). The cluster radius being a fraction of the 200-bar range keeps it scale-free.
**Why tick-powerful:** The cluster list is rebuilt only when a new pivot confirms (every ~10-20 bars); per tick it is "am I within tolerance of one of ≤5 levels?" — with the pre-computed touch count as the weight. The break event (first close beyond) is a kline-close event, but the *approach* to the level is tick-observable for maker logic.

---

### 3.10 Fast (Live) ZigZag Structure — Zero-Confirmation HH/LL/HL/LH
`source: AI RSI MTF STRATEGY.txt + ASK.txt`

```python
ph1 = (highestbars(high, 8) == 0) ? high : na     # current bar IS the 8-bar high -> live swing high
pl1 = (lowestbars(low,  8) == 0) ? low  : na
dir = +1 on ph1 (unless pl1), -1 on pl1
on direction FLIP: push (extreme value, bar_index) onto zigzag deque (len 12)
else: update the last point's extreme
# classification of the last 3 points: HH / LH / HL / LL
```

**Mechanics:** `highestbars(...)==0` means "the extreme is happening *right now*" — this is a **forming** swing, not a confirmed one. Structure (HH/HL/…) is therefore known while it is being made, at the cost of occasional retraction of the current point (which is exactly what the update-in-place logic handles). It is the fastest market-structure read available without lookahead.
**Why tick-powerful:** Two rolling-extrema comparisons per tick. For a scalping engine this is the MSS feed: "price is making a higher high *right now*" is one boolean that gates long-only execution in real time.

---

### 3.11 Pivot-Channel (Two-Pivot) Breakout Zones
`source: AI_TRENDLINE.txt`

```python
# bear channel: two consecutive LOWER pivot highs (p1 > p2, each 5/5 pivot)
#   + the last two highs all below the two preceding highs (double-confirmation)
top_line = line through (p2, p1);  base_line = top_line - pad
pad = min(ATR(200)*0.1, price*0.001) * space     # volatility-capped channel width
# VALIDITY (anti-fake): the base line, projected backward, must not have been
#   touched by any low between the two pivots (a channel that was already tested = invalid)
# FAST PATH: channel projected forward at its own slope;
#   BREAK = close beyond the outer line (plup / pldn events)
```

**Mechanics:** A channel defined by *two* same-direction pivots (a regression-free two-point fit), with width capped at both 10% of long-horizon ATR **and** 0.1% of price (the min() is important on low-priced assets). The backward-projection validity test rejects channels whose inner edge already broke price — a structural sanity check that most channel tools lack.
**Why tick-powerful:** The channel is (slope, intercept, offset) — three floats. Break = one linear inequality per tick, evaluated against the *projected* line, so the break is detected at the exact crossing tick of the sloped line, not at a bar close.

---

### 3.12 Kumo-Edge Breakout + 10-Bar Retest (cloud as level, not filter)
`source: Adaptive Ichimoku Nexus.txt`

```python
break_up   = close > kumoTop and close[1] <= kumoTop[1] and volume > 1.3*SMA(vol,20)
break_down = symmetric
retest_bull = (1 <= bars_since_break <= 10) and low <= kumoTop and close > kumoTop
# veto: thin cloud -> kumoThickness < 0.3 * SMA(thickness, 50)  (no signal in flat cloud)
```

**Mechanics:** The cloud's top edge is treated as a *hard level* (it is — it is a displaced Donchian average, so it is a real price). The retest is the classic "break-and-hold" entry: the level must first be broken (with a volume impulse) and then *revisited from the other side* within 10 bars. The thin-cloud veto encodes that a near-zero-thickness cloud carries no order flow and breaks through it are noise.
**Why tick-powerful:** The edge is a maintained level; the retest is a two-sided level test (wick in, close out) — the same object as an SFP. The volume multiplier on the initial break is evaluated at the break kline.

---

### 3.13 Body-Relative Consolidation Breakout
`source: breakout +TP-SL.txt`

```python
avgBody = SMA(|close - open|, 20)
consolidating = |body| < 2 * avgBody
# track box: highest/lowest during the consolidation; maxBody during it
valid_box = (boxHigh - boxLow) <= 6 * avgBody_at_start
# BREAKOUT (long):
|body| >= 1.5 * avgBody_at_start      # the breaking bar is abnormally strong
and |body| > maxBody_during_consol    # stronger than anything in the range
and close > open and close > boxHigh  # closes through the box
SL = close - 2 * SMA(H-L, 50);  TP_k = close + k * SMA(H-L, 50), k ∈ {2,3,4}
```

**Mechanics:** Consolidation is defined *relative to the market's own body statistics* (not a fixed range): a bar is "quiet" when its body is under twice the average body. The breakout bar must be *doubly* exceptional — larger than the range-average AND larger than the largest bar that formed the range — which is a two-sample significance test on the bar's own distribution. Box validity (height ≤ 6× body) rejects ranges that are tall relative to their bar activity (i.e., not true compression).
**Why tick-powerful:** The state is (in_consolidation, boxHi, boxLo, maxBody, avgBody). The breakout condition is evaluable on the forming bar's live body: the moment `|live_close - open|` passes the larger of the two body thresholds *and* price is outside the box, you can pre-fire before the close.

---

## 4. DYNAMIC RISK MANAGEMENT (Real-Time Volatility-Based)

### 4.1 Fibonacci Extension Plan from Anchored-VWAP Displacement
`source: Anchored VWAP Trade Planner.txt`

```python
d = entry - vwap_anchor
TP1 = vwap + 2.618 * d        # RR = 2.618  (1.618/0.618)
TP2 = vwap + 4.236 * d        # RR = 5.236
TP3 = vwap + 5.236 * d        # RR = 6.854
SL  = vwap + 0.382 * d - 0.25 * ATR(14)        # 0.618-retrace from entry, + ATR buffer
# post-TP2: chandelier trail = max(prev, highest - 3*ATR(22))
```

**Mechanics:** The entire trade geometry is a function of one displacement `d` — the distance from volume-weighted fair value — and the Fibonacci constants are chosen so that each TP is itself a classical extension of the *initial* move, giving built-in RR structure (2.6 / 5.2 / 6.9) without any arbitrary multiplier. The SL at 0.382·d (i.e., the 0.618 retrace of d) encodes "the trend thesis dies if price gives back 61.8% of its displacement from fair value", with a 0.25·ATR noise buffer.
**Why tick-powerful:** `d`, `vwap`, and ATR are all streaming scalars → the whole plan is four prices computable at the entry tick, frozen for the trade. The partial-close ladder (1/3 at TP1/2/3) is the recommended execution on top.

### 4.2 Fibonacci Targets Between Trend Extreme and Live Trailing Line
`source: AlgoX V22 SuperTrend.txt`

```python
ex = max(high) since the last trend flip          # the swing extreme of the active trend
f1 = ex + (trail - ex) * 0.500
f2 = ex + (trail - ex) * 0.618
f3 = ex + (trail - ex) * 0.786
```

**Mechanics:** Instead of static R-multiples, the targets are retracements of the *entire active-trend leg* measured against the *current* trailing stop: f1 is the midpoint between the extreme and where you'd be stopped now. As the trail rises, the targets rise with it — the reward map breathes with the trend while the stop does the actual protection.
**Why tick-powerful:** `ex` and `trail` are each one scalar (max-so-far, ratchet). The three target prices are three multiplications per tick — you can move resting limit orders continuously as the trail moves.

### 4.3 Ratcheting Chandelier Stops — three found variants

```python
# (a) extreme-based ratchet (ASK / 2-1):  stop_long = max(stop, low - 2.2*ATR14)
#     stop_short = min(stop, high + 2.2*ATR14)
# (b) UT-Bot style with ATR(1) (Advanced SMC):  nLoss = 2*ATR(1) = 2*TR(last bar)
#     stop ratchets on price vs stop; direction FLIPS on stop cross
# (c) swing chandelier (2-1):  stop = maxHighSinceEntry - 2.2*ATR14
# (d) post-TP chandelier (AVWAP): after TP2, trail = max(prev, high - 3*ATR22)
# (e) HA-SuperTrend ratchet (ABO LANA): stop = SuperTrend(1.3*ATR14) on Heikin-Ashi close
```

**Mechanics:** All five are the same skeleton — a one-directional ratchet of `extreme ∓ k·vol` — differing only in the extreme (bar low/high, running max, HA close) and the volatility term (ATR14, ATR1=TR, ATR22). The ATR(1) variant is the most aggressive: its stop distance is exactly twice the *last bar's* true range, so the stop re-prices to the most recent volatility observation with zero smoothing lag. The SuperTrend ratchet property (`max` only) guarantees the stop never loosens; flip-on-cross gives a symmetric exit/entry in one object.
**Why tick-powerful:** Each is O(1) per tick: one max/min. (b) is notable because ATR(1) makes the stop *tick-responsive* — every new 1m bar's range re-prices it, and the flip-on-cross means the same object that protects you also generates the next entry.

### 4.4 Structure-Anchored Stops with ATR Buffer
`source: Ayman Entry.txt, Adaptive Ichimoku Nexus.txt, AI Signal.txt`

```python
# Ayman:  SL_long = min(swing_low, ...) - sl_buffer - 0.8*ATR(10)
# Ichi:   SL_long = kumoBottom - 0.5*ATR(14)     (or Kijun - buffer)
# AI Signal: SL = last CONFIRMED fractal low (5-bar fractal, 2-bar confirm)
# TP ladder (AI Signal): TP_k = entry ± k*R, R = |entry - SL|  (1R, 2R, 3R)
```

**Mechanics:** The stop is placed *beyond a known structure* (swing, cloud edge, fractal) plus a fraction of ATR as the noise buffer — the structure says *where* the thesis is invalid, the ATR fraction says *how much noise to allow*. The fractal-2-bar-confirmation is the only deliberate delay in the batch's stop logic, and it is a correctness trade (an unconfirmed fractal can be extended) — in the bot you can place the working stop at the *forming* fractal extreme and only commit once the two bars confirm.
**Why tick-powerful:** Structure levels are maintained by the microstructure engines (§3); the stop is one subtraction per level event.

### 4.5 Sizing, Break-Even, and Re-Anchor State Machines

```python
# fixed-fractional sizing from stop distance (Ayman):
lot = (capital * risk_pct) / (|entry - SL|)                # risk $ per trade constant
# break-even (Ayman): at TP1 (70% of full target): SL := entry + buffer; partial 50%
# TP re-anchor (ABO LANA): at TP3 hit: entry := close; recompute TP1/2/3 from new entry
# staged partials (AlgoX V22): 50% at TP1, 30% at TP2, 20% at TP3; SL stays fixed
# state machine (AVWAP): ENTERED -> TP1_HIT -> TP2_HIT -> TP3_HIT -> EXITED
#   (each transition carries the recommended action: 1/3 close + SL move)
```

**Mechanics:** The re-anchor variant is the interesting one: instead of trailing, the *entire trade geometry* is rebuilt at the third target — the win becomes the new risk baseline. Combined with break-even-at-TP1, the strategy's loss profile after TP1 is zero (breakeven) and the expected-value tail is the re-anchored continuation.
**Why tick-powerful:** All transitions are level-cross events; the action on each (cancel/replace limits, move stop) is a fixed state-machine transition — no computation at decision time.

### 4.6 Volatility-Regime Gates (asymmetric long/short thresholds)
`source: ALGOX V11.txt`

```python
nATR = (ATR14 - min(ATR14, 20)) / (max(ATR14, 20) - min(ATR14, 20))
long_gate  = nATR > 0.2      # longs allowed once volatility is out of the bottom 20%
short_gate = nATR > 0.5      # shorts demand *higher* volatility (top 50%)
extra: ATR14 > ATR14[2] (volatility must be rising)
```

**Mechanics:** The percentile-normalized ATR (position within its own 20-bar range) is a regime constant, not a level. The asymmetry (shorts need 2× the volatility floor) encodes the empirical observation that downside moves in crypto tend to be sharper, so short entries are only taken when the regime supports the speed of the move.
**Why tick-powerful:** Two rolling extrema of ATR — O(1). The gate is a boolean that can switch strategy *mode* (e.g., maker-only below 0.2) with zero per-tick cost.

### 4.7 Extreme-Exhaustion Exit Triggers
`source: ASK.txt (TP labels), AlgoX V22 (RSI exits)`

```python
# staged momentum-exhaustion exits (ASK):
#   long: TP1 when RSI crosses 70, TP2 at 75, TP3 at 80  (sequential, one per cross)
#   short: 30 / 25 / 20
# emergency recovery exit (AlgoX V22):
#   long: exit when RSI(14) crosses back UP through 20 or 15
#   short: exit when RSI crosses back DOWN through 80 or 85
```

**Mechanics:** The first set is a "take profit where momentum is objectively exhausted" ladder — the deeper the RSI extreme, the more of the position you are entitled to close. The second set is the opposite logic: an RSI that has collapsed into the 10s/15s and is now turning is a "the move is over and the market is recovering" signal — exit the long early into the recovery rather than waiting for the stop. Both are RSI *events* (crosses), not states.
**Why tick-powerful:** Four cross-detections on one maintained RSI. The emergency exit is a genuine risk primitive: it converts "deeply underwater + first green tick" into an exit, which a static stop cannot express.

---

## 5. CONFLUENCE / SCORING SYSTEMS

### 5.1 Six-Factor Liquidity-Sweep Score (0–100) — the reference scorer
`source: Advanced Liquidity Sweep.txt`

```python
def sweep_score(bullish, pierce, touches):
    rng = max(high - low, mintick)
    wick = (close - low)/rng if bullish else (high - close)/rng      # rejection ratio
    body = min(max(directional_body, 0)/rng, 1)                       # close-through body
    atr  = min(pierce / ATR, 1)                                       # depth in ATR units
    vol  = min(volume / (2 * SMA(vol, 20)), 1)                        # volume impulse (cap 2x)
    ema  = min(abs(close - EMA50) / (3 * ATR), 1)                     # distance from trend (extended price)
    eq   = min(touches / 3, 1)                                        # equal-H/L cluster strength
    # weights (preset "Balanced"):
    w = dict(wick=1.0, atr=1.0, vol=0.8, body=1.0, ema=0.6, eq=0.8)
    return 100 * sum(w[k]*c[k]) / sum(w.values())
# gates: score >= 50 to signal; >= 70 = STRONG tier
# Conservative preset shifts weight to wick/body (clean rejection);
# Aggressive preset shifts to volume/equal-cluster (flow-heavy)
```

**Mechanics:** Six factors chosen to be *mutually informative*: how hard price rejected (wick), how far it penetrated (pierce/ATR), how much volume the sweep carried, whether the close actually reversed through the level (body), whether price was extended from the trend line (mean-reversion fuel — the `ema` term rewards sweeps that happened at 3σ+ from the EMA), and how many stops were resting there (touches). The weighted average with a preset-dependent weight vector is a transparent, tunable quality gate. The tiers (50/70/90) map directly to position size.
**Why tick-powerful:** All six inputs are known at the sweep bar's close tick (wick/pierce/body from the bar itself; vol/EMA/touches maintained). The score is six divisions and one sum — you can compute it per sweep event and size the order by tier in the same loop iteration.

### 5.2 Eight-Factor Confluence Score (0–100) with Momentum-Pulse Acceleration
`source: Adaptive Ichimoku Nexus.txt`

```python
# momentum pulse (the novel term):
spread  = (tenkan - kijun) / ATR14
pulse   = clip( 40*spread + 100*(spread - spread[3]) + 30*cloud_slope_norm, -100, 100)
pulseS  = EMA(pulse, 5)
# confluence (long), weights in parentheses:
price above cloud (20) / inside (8)
TK aligned (15)
chikou above price-26 (15)
future-cloud slope bull: d(spanA)/3 > d(spanB)/3 (10)
cloud not thin: thickness >= 0.3*SMA(thickness,50) (8 | 2)
volume > 1.2*SMA(vol,20) (10)
pulseS > 20 (12) / > 0 (6)
pulseS rising (10)
# threshold: >= 50 to signal; >= 80 grade "Strong"
```

**Mechanics:** Standard Ichimoku components (position in cloud, TK, chikou, cloud slope, thickness) are combined with **two momentum terms that are not in any textbook**: the pulse itself (position of the TK-spread in ATR units, weighted 40) and its **3-bar derivative** (weighted 100 — the acceleration term dominates the score). A cross with rising pulse gets a materially higher score than a cross with a decaying one, which is exactly the difference between "fresh trend" and "trend about to roll over".
**Why tick-powerful:** The pulse is an EMA of a linear combination of three maintained quantities — O(1). The score is a 10-branch weighted sum; computing it per signal candidate costs nothing, and the *gradient* of the score (which factor is missing) can be exposed to the order handler for partial-size decisions.

### 5.3 Structure × Flow AND-Gates (the "confBull" pattern)
`source: ASK.txt + 2-1 strategy.txt`

```python
confBull = (supertrend_flip OR (supertrend_flip[1] AND donchian_was_bear))   # structure event
         AND macd > 0 AND macd > macd_prev                                     # momentum sign+slope
         AND ema150 > ema250                                                    # long-scale order
         AND hma55 > hma55[2]                                                   # medium-scale slope
         AND donchian30 > 0                                                     # 30-bar regime
```

**Mechanics:** Five independent regime facts (each from a different volatility scale and a different variable family: ratchet band, oscillator, long MA, HMA slope, price extreme) must all agree. The `(flip[1] AND regime_was_opposite)` clause catches the *one-bar-late* flip — the SuperTrend flip that the Donchian already pre-signaled — which is the classic "structure lagging regime" alignment. No single factor is lagging by itself in a way that matters: the Donchian and SuperTrend are the fast ones, the EMAs are the context.
**Why tick-powerful:** Each factor is a maintained scalar/boolean; the gate is a 5-way AND evaluated only when a flip event occurs (event-driven, not per-tick). This is the cheapest high-precision gate in the batch and a good default for "is the tape aligned" before any scalping entry.

### 5.4 Wave-Dominance Regime Score
`source: AI Vanga V3.txt` — see §1.10. `dominance = bull_avg − |bear_avg|`, `current_ratio = current_wave / mean_wave`. A trade is permitted only when `sign(dominance)` matches the trade direction and `current_ratio > 1` (the active wave is stronger than the historical mean for that side). The max-ratio variant (vs `max_wave`) is the breakout-strength detector.

### 5.5 Volume-Tercile Break Grading
`source: Advanced SMC.txt` — see §1.11. LB/MB/HB classification of a channel break by volume position in its own distribution; suggested bot use: full size on HB, half on MB, skip on LB (or maker-only).

### 5.6 RSI-Stack Exit/Entry Scoring (multi-level)
`source: ASK.txt, AlgoX V22` — RSI(14) 40/60 state + RSI-vs-EMA(21) cross (entry permission) + staged 70/75/80 or 20/15/80/85 extremes (exit ladder) — a complete "RSI traffic light" that can be embedded as the exit-side scorer for any of the entry engines above.

---

## 6. INTEGRATION BLUEPRINT (Binance Spot: 1m klines + aggTrade + bookTicker)

**Slow state (per closed 1m kline, <1ms each):**
1. Maintain: ATR(14/53), ATR200 (running), rolling stdev of (close−VWAP), rolling 200-bar high/low, EMA/RMA stacks, RSI(2/6/14/50)+EMA(30), ATR(1)-of-RSI, the ε-midpoint `m`, the sticky level, KAMA-anchor accumulators, wave deque, pivot queues (fast 8-bar live zigzag + 20/20 confirmed), FVG list (≤12), OB list (≤10) with breaker states, EQH/EQL clusters, channel lines, kumo edges, Donchian/SuperTrend/Gaussian states.
2. On kline close: update all pivots; run OB lifecycle (break→breaker, mitigation, IoU merge); rebuild S/R cluster ranking (top-5); score any sweep events with §5.1; advance the trade state machine (§4.5).

**Fast path (per aggTrade, target <50µs):**
1. Direction gate: sign(price − KAMA) & |price−KAMA|/σ (§2.1) + 6-scale regime state (§2.6) → sets allowed side.
2. Triggers (any one, all level comparisons): ε-band step (§1.1) · DTTA level (§1.3, session-anchored) · RQ-WaveTrend flip/divergence (§1.2) · TrendShift cross (§1.4) · Range-filter state flip (§1.6) · range-SuperTrend flip (§1.7) · MSS cross + CHoCH/BOS (§3.1) · SFP (§3.5) · FVG CE touch / full fill (§3.4) · OB tested (§3.3) · breaker conversion (§3.2) · void slice fill (§3.6) · channel break + volume tercile (§1.11) · consolidation body-breakout (§3.13) · kumo retest (§3.12) · z-score VWAP (§2.4) · sticky-level approach (§1.5).
3. Score: §5.1 (sweep) or §5.2 (trend cross) or §5.3 gate → tier → size = risk$/|entry−SL| (§4.5).
4. Plan: SL from structure + 0.5–0.8 ATR (§4.4) or ATR% (§4.6); TPs = 2.618/4.236/5.236·d (§4.1) or fib-of-leg (§4.2) or 1R/2R/3R.
5. Manage: ratchet chandelier (§4.3b is the tick-native one), break-even at TP1, partials 50/30/20 or 1/3 ladders, re-anchor at TP3, emergency RSI-extreme exits (§4.7).

**Pre-placed-order opportunities (maker side):** the sticky level ± band, FVG CE midpoints, OB POC slice (§1.9), void slice midlines (§3.6), S/R cluster edges (§3.9), session-fib grid (2-1 strategy's OSTDV levels: mid±{0.5,1,1.5,2,2.5,3,3.272,3.5,4.5}·range) — all are *known in advance* and can carry resting limits while the fast path manages taker entries.

---

## APPENDIX A — Red-Line Items Found and Discarded (per file)

| File | Discarded content |
|---|---|
| 2-1 strategy | EMA(20/100/200) cloud fills; Gann Square-of-9 lines; 8AM-pip levels (fixed, no statistical basis); all drawing code |
| ABO LANA-𝑀 | RSI(2)+SMA7 status display, ADX display, V/OB-VOS display, dashboard; kept: HA-SuperTrend ratchet, zone dedup, TP re-anchor, AMLAG |
| Adaptive Ichimoku Nexus | MTF `lookahead_on` request (only its *confirmed-value* semantics are legitimate — replicated without lookahead); all dashboard/table/label code |
| Advanced Liquidity Sweep | age-fade rendering, zone-expiry cosmetics, dashboard; the *logic* (clustering, scoring, sweep conditions) is fully extracted |
| Advanced SMC | Nadaraya-Watson O(N²) loop replaced by compact-kernel equivalent; SMT symbol pairs (forex) remapped to crypto; drawing/alert scaffolding; EMA20/50/200 plot; RSI 32/65 momentum block kept only as §5.6 |
| AI Gold Scalping | `rp_security` realtime-branch (repaint pattern); 5-EMA fan visuals; MACD(2,4,3) candle colorer; kept: Range Filter, WaveTrend divs, MTF EMA-bias matrix (as confirmed-value gate) |
| AI RSI MTF STRATEGY | Part 1: RSI(14) 40/60 MTF entry — pure lagging oscillator cross, discarded; backtest-stats tables; kept: clustered S/R strength engine, live zigzag, slope trendline (Linreg slope variant), volumetric OB engine, SFI MTF-SuperTrend |
| AI Signal / AI Signal Remastered | 15-line EMA fan (visual only); 10/20 "trend catcher" cross; fractal TP/SL label machinery; kept: range-Instantaneous SuperTrend, fractal-anchored SL + 1/2/3R ladder |
| AI SWING Algo | Telegram table; T3 fill colors; kept: ε-band, T3 cascade, ATR-ladder SL/TP (1.5/3/4.5/6/7.5·ATR, SL=2.25·ATR) |
| AI Vanga V3 | random-walk "Vanga forecast" (nonsensical future projection — discarded outright); session-dashboards; kept: RQ-kernel WT, DTTA, Trend-Speed waves, anchored powered KAMA, volume-profile OB (from source comments), Gaussian-α formulas |
| AI_TRENDLINE | `backpaint` option (lookahead rendering — discarded); kept: two-pivot channel with ATR-capped pad + validity projection, breakout events |
| ALGOX V11 | monthly/weekly performance tables, per-day trade tables; kept: ALMA close/open cross, SuperSmoother, ATR-percentile asymmetric gate, ADX-Masanov variant, RSI-EMA(30) filter |
| AlgoX V22 SuperTrend | `_lookahead` repaint mode (factor 0.1 SuperTrend — discarded; the non-repaint factor-3 variant is extracted); MA-ribbon *plot* (logic kept as §2.6); RSI tables; kept: cumulative-ATR fib stops, wick-penalized TR SuperTrend, fib-of-leg targets, 50/30/20 partials, RSI extreme exits |
| Alpha Hunter | ADX/RSI/volume display tables; kept: EMA(high/low)±ATR channel, ADX≥20 regime gate, ratchet trailing (max), R-multiple TPs from opposite-band risk |
| Anchored VWAP Trade Planner | dashboard/formatting; everything else extracted (the cleanest file in the batch — fully non-repainting by design) |
| ASK | bar-coloring heatmaps, session tables, candle pattern colorers; kept: TrendShift, WaveTrend trap detector, confBull gate, QQE ratchet, trailingSL, RSI TP ladder, consecutive-close exhaustion (13× close<close[4]), vol-percentile gauge |
| Ayman Entry | all dashboard/PnL/stats code, SMA8/9 cross + 50/200 cloud (lagging — discarded as triggers, kept only as context); kept: BoS-with-0.5% proximity trigger, valuewhen order blocks, FVG fill-removal, strict liquidity-sweep tolerance (1.01/0.99), pin-bar geometry (wick>2×opp & body<25% of range), SL=extreme+buffer+0.8·ATR, fractional sizing, break-even + partial at TP1 |
| breakout +TP-SL | box/line/label drawing; kept: body-statistics consolidation model and its TP/SL |

## APPENDIX B — Notes on Correctness Risks When Porting

1. **Pivot latency is a feature, not a bug.** Confirmed pivots (20/20) never repaint; forming pivots (8-bar `highestbars`) do retract. Use confirmed pivots for *levels* (they define the structure) and forming pivots only for *gates* (they decide when to act). Mixing them backwards is the classic porting error.
2. **`valuewhen`-based order blocks (Ayman) inherit the delay of the BoS event** — fine for a 1m engine, but the zone price is stale by the pivot confirmation; the §3.2/§3.3 engines (origin-bar boxes) are strictly better and were the ones chosen.
3. **ATR(1) in the UT-Bot stop** means the stop distance is set by the *previous* 1m bar's range — in a low-vol bar the stop is tight enough to be stopped out by spread alone. In the Binance port, floor it: `nLoss = max(2*ATR(1), 3*mintick_spread)`.
4. **The ε-band (AI SWING) uses `ATR(53)` of the *previous* bar** — replicate exactly; using the current bar's ATR makes the band width path-dependent on the very move that triggers the step (self-exciting).
5. **Dual Thrust levels must freeze at the session open** — recomputing them intraday (some implementations "re-anchor" at lunch) changes the strategy entirely; the source uses the open of the chart bar as the anchor, which on 1m = the first 1m bar of the chosen session.
6. **Welford-on-KAMA (anchored powered KAMA) is an approximation** of the true variance around the KAMA (the summand is `(x−kama_prev)(x−kama)`, not `(x−kama)²`); it is unbiased in trending regimes and slightly under-estimates in chop — acceptable, and it is what the original computes, so backtests will match.
