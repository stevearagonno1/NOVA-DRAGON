# HFT Edge Extraction — BATCH 6 (files 102–121)

**Scope.** 20 Pine files, **19 unique** ("Supply and Demand Zones.txt" is a byte-identical duplicate of batch-5 "S&D zones.txt", md5 `911ac2fe…` — excluded, cross-referenced as B5 M1 family).
**Focus.** Wildcard/innovative edges, low-lag directional math, microstructure (OB/FVG/MSS without delayed-closure waits), dynamic risk, confluence scoring.
**Output convention.** No raw Pine/MQL — Python pseudo-code / closed-form math + why each primitive suits a zero-wait tick engine (Binance Spot HFT on 1m klines, `aggTrade`, `bookTicker`).
**Red lines enforced.** (1) repaint/lookahead mechanisms excluded (port notes given where salvageable); (2) lagging-indicator slow crosses excluded as *triggers*; (3) all GUI/plotting/label/table/Telegram-dashboard code excluded (alert *logic* kept); (4) derivatives logic (leverage, liquidations, futures, settlement IV) excluded.

**Batch flagships.** `TJR SMC` (full sweep→MSS→zone-tap FSM with SMT divergence, killzones, conviction score), `VCE` (volatility-coil reversal engine with violation-tolerant compression state machine), `SMC [BigBeluga]` (3-state structure FSM with sweep areas, volumetric OBs, breaker conversion), `SMC Algo Pro E5` (zone lifecycle: merge, breaker flip, mother-bar expansion, IDM-filtered CHoCH, SFP, volume-validated S/R breaks).

---

## Red-line exclusion table (B6)

| File | Excluded mechanism | Red line |
|---|---|---|
| Supply and Demand Zones.txt | entire file — md5 duplicate of B5 "S&D zones.txt" | dedup (not a red line) |
| Stocks Algo.txt | RMI-style ratchet (longStop = highest(close,22) − 3·ATR22, ratchets up while close[1] > prev else reset; dir flip on opposite-band cross = event) | xref B3/B4 ST-ratchet family — no new math; SL 0.5·ATR / TP 1–2·ATR noted |
| sniper entry with tp&sl.txt | **trigger = EMA9/21 cross** (score gates it, but the trigger is the excluded class); HTF 5m RSI fetched live-forming via `request.security("5")` | (2) + (1)-flag |
| TM Sniper Pro.txt | same EMA9/21 cross trigger | (2) |
| Trend Trader Pro.txt | same EMA9/21 cross trigger | (2) |
| simplealgo v3.txt | SuperTrend(7×1, ATR10) cross trigger; CMO-alpha Vidya/KAMA displays; cirrus-cloud fills | (2) |
| strategy with signals.txt | SuperTrend(5,10)+MACD+EMA150/250+HMA55 confluence trigger ("2:1 strategy"); RSI 70/75/80 ladder TP triggers | (2) |
| Smart Money Trades Pro.txt | nothing structural — kept (see R5, M xref); entry *is* a 20/20 pivot break event | — |
| Sniper Trading Algo Pro.txt | all 5 selectable triggers: KAMA(4/EF80)×VIDYA(CMO-α) cross, SSL+TDFI+RSI65-cross, engulfing+RSI50, squeeze-release; 16-way MA selector | (2) |
| SUPER Scalping.txt | Settlement/IV module (settlement ± 0.5–2.5·σ(τ/252) from 21-day log-return stdev) | (4) |
| TrendFilter.txt | **Liquidations module** (5×–100× liquidation prices from pivots: `low/(1+0.20)…high·(1.01)` with volume-spike ladder 1.0–1.2·avgMean) | (4) |
| Unmitigated.txt | HTF-15m level registration uses `lookahead_on` on the **current** (forming) HTF bar for new-TF detection (`high[1]` idiom is fine — that's confirmed; the `curr` value is live) | (1)-flag on curr-value only |
| SMC.txt | PDHL/PWH/PMH/PQH/PYH via `request.security(…, lookahead_on)` on live H/L (display lines) | (1)-flag, display only |
| SMC Algo Pro.txt | HTF liquidity pivots + HTF FVG fed by **plain** `request.security(sym, tf, …)` (no `[1]`, no lookahead) → live-forming HTF values in realtime; key-level lines via `lookahead_on` (confirmed-bar idiom, OK for [1] values, live for unindexed) | (1)-flag on live-variant feeds |
| SWIFT ALGO.txt | `reso()` HTF variant uses the confirmed-bar idiom (`gaps_off + lookahead_on` on plain series → in realtime this returns the *current* HTF value; acceptable only with the `[1]` form) — used as optional alternate TF for the body-cross | (1)-flag on HTF variant |
| (all files) | plotshape/plot/label/line/box/table/box.new/barcolor/bgcolor + `@mrexpert_ai` / `@simpleforextools` Telegram cells | (3) |

---

## §1 — WILDCARD / INNOVATIVE EDGES

### W1 · VCE volatility-coil reversal engine *(VCE - Volatility Coil Edge)*

Detects volatility **compression** (a "coil") forming **at session extremes**, then enters the break of the coil in the *reversal* direction. Coil-at-high ⇒ short; coil-at-low ⇒ long. Fully bar-close confirmed, explicitly non-repainting (no lookahead, no security).

**Compression test (per bar).**

```
bgAtr    = ATR(20)                 # background regime
localAtr = ATR(4)                  # local regime
medianRng= percentile_linear_interp(high - low, 50, 50)

ratioContracted = localAtr < 0.82 * bgAtr            # preset-tunable 0.70/0.82/0.92
driftContracted = (high - low) < 0.65 * medianRng    # absolute floor for flat regimes
catalyst        = any((high[k]-low[k]) > 1.5*bgAtr[k] for k in 1..5)
                 and localAtr < 1.10 * bgAtr         # post-impulse coil
isContracted    = ratioContracted or driftContracted or catalyst
```

**Coil state machine (with violation tolerance).**

```
tol = 0.50 * bgAtr            # Edge tier: Full=0.30, Mid=0.75
MAX_VIOLATIONS = 2            # Full=1, Mid=3

if isContracted:
    if compLen == 0: compLen, compHi, compLo, viol = 1, high, low, 0
    elif (high <= compHi + tol) and (low >= compLo - tol):
        compLen += 1; compHi = max(compHi, high); compLo = min(compLo, low)
    else:                                   # bar pokes outside the coil box
        viol += 1
        if viol <= MAX_VIOLATIONS: compLen += 1; compHi/compLo extended   # tolerated
        else: reset coil to this bar
else:
    compLen -= 1                           # one-bar grace, then 0 (anti-ghost)
if compLen > compMax: reset                # stale drifting consolidation dies
```

Preset table: **Conservative** {min 5, max 12, ratio 0.70, extreme 0.25, Full}, **Balanced** {4, 14, 0.82, 0.35, Edge}, **Aggressive** {3, 16, 0.92, 0.45, Mid}.

**Extreme-zone gate (where the coil forms decides direction).**

```
sessHi, sessLo = highest(high, 50), lowest(low, 50)
zoneTop = sessHi - 0.35 * (sessHi - sessLo)     # top 35% band
zoneBot = sessLo + 0.35 * (sessHi - sessLo)     # bottom 35% band
compAtHigh = compHigh >= zoneTop   (Edge tier; Full: compLow >= zoneTop)  -> arms SHORT watch
compAtLow  = compLow  <= zoneBot   (Edge tier; Full: compHigh <= zoneBot) -> arms LONG  watch
```

**Watched coil + expiry.** When a qualified coil sits in an extreme zone it becomes a *watched coil*: a frozen price box (extended while the coil keeps qualifying). Once the coil stops qualifying, a countdown starts: `WATCH_EXPIRY = 10` bars (Full 5 / Mid 15) — then the setup is cancelled. This is the key freshness primitive: **a coil only means something while it is still coiling, or for a bounded number of bars after.**

**Break trigger (bar-close confirmed).**

```
# Edge tier:
shortBreak = (close < watchLow)
            or (low < watchLow and close < open
                and (open - close) > 0.40 * (high - low))   # body-dominant rejection through the edge
longBreak  = (close > watchHigh)
            or (high > watchHigh and close > open
                and (close - open) > 0.40 * (high - low))
fire = isConfirmed and watchActive and directionMatches and break
       and (bar_index - lastOutcomeBar) > 8                  # 8-bar post-outcome cooldown
```

**Why it suits a zero-wait engine.** Every primitive is O(1) state: two ATRs, a 50-bar high/low, an integer `compLen`, a two-float box, a violation counter, an expiry counter. The coil box is a *limit-order resting zone* in disguise — in a tick engine you pre-place passive orders just outside `watchHigh/watchLow` the moment the watch arms (coil qualified + in extreme zone), and the "trigger" is simply your order being swept/triggered intrabar with no bar-close wait. The violation-tolerant box is exactly what a tick feed provides: you see every poke outside the box and can decide to kill the setup *during* the bar instead of after it. Compression at an extreme is a measurable microstructure state (range contraction = order-book inventory building), not a chart pattern.

### W2 · Velocity-anchored order blocks *(SUPER Scalping → SonarLab OB module)*

An OB is created by a **velocity event**, not by structure: a 4-bar open-to-open ROC crossing a threshold, then the OB is anchored at the *origin candle* of the impulse.

```
pc = (open - open[4]) / open[4] * 100          # 4-bar open-to-open velocity, %

if crossunder(pc, -0.28):                      # fast drop detected (sens = 28 bps)
    if bar_index - last_ob_bar > 5:            # 5-bar dedup
        i = first j in 4..15 with close[j] > open[j]     # first GREEN candle in window
        supply_OB = [low[i], high[i]]          # the candle that started the dump
if crossover(pc, +0.28):
    i = first j in 4..15 with close[j] < open[j]         # first RED candle
    demand_OB = [low[i], high[i]]

# lifecycle:
mitigate   = close through far edge (Close mode) or wick (Wick mode) -> remove
in_zone    = price inside box -> "order flow" alert (resting limit zone)
```

**Why it suits a zero-wait engine.** The trigger is a single rolling 4-bar quantity — computable on every tick from the last four confirmed opens + current open, i.e. *before* the 4th bar closes. In a tick engine you detect `pc` crossing ±28 bps in real time and immediately mark the origin candle's full range as a liquidity zone: it is the *unfilled origin* of an impulse, the level that re-pricing should visit first. Faster and cheaper than any pivot-based OB (no `swing_length` confirmation delay). The 5-bar dedup is a trivial monotonically increasing counter.

### W3 · MA-intersection value & SMA-intersection matrix *(TrendFilter → "challenge" functions)*

On the bar where two smoothed series cross, compute the **exact price** at which their 1-bar linear extrapolations intersect — and do this for an entire *matrix* of SMA pairs.

```
def cross_value(s1, s2):
    m1, m2 = s1 - s1[1], s2 - s2[1]
    if sign(s1 - s2) != sign(s1[1] - s2[1]):          # crossing this bar
        sf = (s1 - s2) / (m1 - m2)                     # common scaling factor
        return s1 - sf * m1                             # intersection price
    return None

def intersection_matrix(lens=range(10, 21)):
    smas = [ (cum - cum[i]) / i for i in lens ]        # O(1) each via cumsum
    prev = smas[1]                                     # previous bar's values
    M = {}
    for i, a in enumerate(smas):
        for j, b in enumerate(smas[i+1:], i+1):
            if (a - b) * (prev[i] - prev[j]) < 0:      # sign flip of the gap
                M[(i, j)] = cross_value(a, b)
    return M                                            # N×N table of cross prices
```

The matrix is a live table of **"where SMA(i) and SMA(j) are about to meet"**: a map of convergence prices across all fast/slow pairs. The quantity `1 − sf` (reported on each intersection) measures *which leg is decelerating*.

**Why it suits a zero-wait engine.** It turns N moving averages into N·(N−1)/2 *price levels* updated O(1) per tick (cumsum SMAs). A cluster of predicted intersection prices near current price is a quantitative "momentum is converging here" read — pullback-target generation without any indicator cross signal. For a tick engine this is pure arithmetic on a running cumsum; no charting, no waiting.

### W4 · HTF unmitigated level age-stack *(Unmitigated)*

A registry of higher-timeframe (15m) highs/lows that are **still unmitigated**, ranked by *age in sessions*, with tiered treatment and band construction from the most recent levels.

```
# registration (on each CONFIRMED 15m bar close — port requirement, see below):
registry.append(level=htf_high or htf_low, side, session_created=session_count)
mitigate(level) when low <= level (for an HTL) or high >= level (for an HTH)  # wick touch
keep:  <= 5 most recent UNMITIGATED per side            (older ones discarded)

# session-age tiers:
age = session_count_now - session_created
tier = 0-1 | 2-3 | 4+ | 7+     # fresher = more reactive

# structure classifier from the HTF bar itself:
strat = 1 if no new H/L      # inside
      = 2U if only new HH    # expansion up
      = 2D if only new LL
      = 3  if both (new HH and new LL)

# bands: bracket between the 1st and 2nd (or 3rd) unmitigated level per side
# proximity alert: |close - level| <= 5.0 (absolute)  + % distance table to all levels
```

**Port flag.** The file's new-TF detection reads the *live-forming* HTF bar via `lookahead_on` (repaint-prone). The level values themselves use the confirmed `[1]` idiom and are fine. Port: register levels on HTF bar-close events from a 1m-resampled feed (B4 confirmed-bar idiom); everything else is tick-native.

**Why it suits a zero-wait engine.** This is a *magnet registry*: every unmitigated HTF high/low is a resting price objective with an explicit freshness prior (session age). In a tick engine the registry is a sorted list with O(log n) insert/mitigate; "proximity" states drive passive-order placement (scale into the level as price approaches, per the % distance table). The age tiers let you weight inventory: a 0–1-session-old level is a hot target; a 7+-session-old level is structural. No lagging indicator anywhere — just levels + counters.

### W5 · Recursive multi-pole Gaussian trend family (two variants) *(strategy with signals; TrendFilter "overlayssd")*

Both files implement **Ehlers-style recursive Gaussian smoothing** as the trend line — causal, O(1) per sample, near-zero phase-lag character compared to EMAs.

**Variant A — pole-order Gaussian + linreg flatten (strategy with signals):**

```
def gaussian_alpha(L, poles):
    freq     = 2*pi / L
    factorB  = (1 - cos(freq)) / (1.414**(2/poles) - 1)
    return -factorB + sqrt(factorB**2 + 2*factorB)          # alpha in (0,1)

# p-th order recursion (their 1..4 pole forms, p=3 shown):
# y_t = a^3 x_t + 3 a^2(1-a) y_{t-1} - 3 a(1-a)^2 y_{t-2} + (1-a)^3 y_{t-3}
y = gaussian_smooth(close, poles=3, alpha=gaussian_alpha(15, 3))
final = linreg(y, 22, offset=7)                              # "flattening" pass

trend   = +1 if final > final[1] else -1
st      = supertrend(final, factor=0.15, atr=21)             # hugging stop on the gaussian
ranging = sign(trend) * sign(final > st) < 0                 # slope and position disagree
mid_signal = ranging flipped this bar                         # mid-trend continuation cue
```

**Variant B — hardcoded 3-pole "dollar" channel (TrendFilter overlayssd):**

```
Sv  = exp(-sqrt(2)*pi/200);  f = -Sv**2
vf  = 2*Sv*cos(sqrt(2)*pi/200);  fg = 1 - vf - f
mid_t    = fg*hlc3_t + vf*mid_{t-1} + f*mid_{t-2}     # gaussian on hlc3
dollar_t = fg*TR_t   + vf*dollar_{t-1} + f*dollar_{t-2}   # SAME filter on true range

inner = mid ± pi*2.415 * dollar        # ≈ ±7.59·dollar
outer = mid ± (pi*2.415 ± 2.0) * dollar  # 6-band low-lag channel
```

**Why it suits a zero-wait engine.** Both are fixed-coefficient IIR filters: constant multiplies + 2–4 previous outputs. On a tick stream that is a handful of float registers updated per tick — no window, no sort, no pivot. The `ranging` flag (Variant A) is a genuine low-lag regime discriminator: it fires exactly when the trend line's *slope* and its *position vs its hugging stop* disagree, i.e. the market is chopping around a trend that is no longer advancing. Variant B's separate "dollar" filter on TR is a volatility channel in filter form (the 2.415π coefficient ≈ a 1σ-ish band on the smoothed range).

---

## §2 — DIRECTIONAL / TREND MATH (non-lagging)

### D1 · Body-momentum dual-channel cross *(SWIFT ALGO)*

The trigger is a cross between **ALMA(close)** and **ALMA(open)** — the same ultra-fast filter applied to the close channel and the open channel:

```
ALMA(len=2, offset=0.85, sigma=5)      # gaussian-kernel MA; with len=2, sigma=5 this is a heavy EMA
closeSeries = ALMA(close);  openSeries = ALMA(open)
long  = crossover (closeSeries, openSeries)      # smoothed close channel rising back through smoothed open channel
short = crossunder(closeSeries, openSeries)
```

**Semantics.** `closeSeries − openSeries` is a smoothed measure of *cumulative body imbalance*: when the smoothed close re-claims the smoothed open, the aggregate body mass has flipped bullish. With a 2-length ALMA this is a ~bar-scale momentum flip, **not** a slow 9/21-style lag cross (that's why it's kept despite red line 2 — same class as a body-direction flip, not a lagging oscillator cross). An optional 8× timeframe resample of both channels (confirmed-bar idiom) makes it a "fast on LTF / confirmed on HTF" variant; a `delayOffset` parameter shifts both inputs to force non-repaint.

**Why it suits a zero-wait engine.** Two O(1) filters on two streams; the cross event is detectable on the *first tick* where the ordering flips (you can fire the moment `closeSeries > openSeries` becomes true intrabar, not at bar close). Body imbalance is directly the quantity an HFT engine already tracks from aggTrade flow — this trigger is just a smoothed version of net-body flow.

### D2 · Dual-scale structure FSM: fast 1/1 BoS + slow 30/30 CHoCH + 3/3 inducement *(TrendFilter → "Market Structure" module)*

Three pivot scales run in parallel, each with its own level and lifecycle:

```
slow pivot  = pivothigh/low(30, 30)      (FTD mode: left leg 15)   -> CHoCH levels
fast pivot  = pivothigh/low(1, 1)                      -> BoS / liquidity levels
idm pivot   = pivothigh/low(3, 3)                      -> inducement levels

trend in {'', Up, Down}
CHoCH (slow level crossed by CLOSE against trend)  -> trend flips; old BoS line cleared
BoS   (fast level crossed by CLOSE with trend)     -> continuation; level armed once
LQDT  (fast level wicked: high > lvl and close < lvl) -> level RECLASSIFIED as
       liquidity-tag line (dotted) — a swept level, not a broken one
inducement = small counter-trend pivot; mitigated by TOTAL (wick) or SWEEP (wick +
       close-back) mode; deleted on close-through
```

**Why it suits a zero-wait engine.** A 1/1 pivot is *the previous bar's extreme* — zero confirmation latency, the minimum possible swing. The 30/30 slow scale is the only delayed piece (10 bars), and it is used only for the *flip* decision, never for the entry. The sweep-vs-break reclassification (wick-through vs close-through on the same level) is exactly the distinction a tick engine makes natively: you watch whether price *closes* (or in tick terms, persists beyond) the level, and you relabel the level's role in real time. Inducement = "the small pullback everyone will short" — in tick terms, the first counter-extreme of ≤3 bars before a move.

### D3 · Sticky-anchor WALKING channel *(strategy with signals → "Trend Levels")*

A channel anchor that only jumps on a large displacement, then **drifts at a fixed walk-slope** until the next jump (B5 M6 had the sticky anchor as a *fixed* line; this adds the walk):

```
T  = 15 * ATR(200)                          # jump threshold
if |close - anchor| > T:                     # displacement event
    anchor = close
    hold_atr = T / 2
os   = +1 if anchor rising else -1
anchor += os * hold_atr / 50                 # walk: half-a-jump per 50 bars
R1, R2, S1, S2 = anchor ± 0.5*hold_atr, anchor ± 1.0*hold_atr
```

**Why it suits a zero-wait engine.** One float, one sign, one threshold comparison per tick. The walk-slope means the channel never goes stale: it migrates with the trend at a rate proportional to the last displacement's size (the vol regime), and the ±0.5·hold_atr bands give a live "value area" around it. In a tick engine the anchor is a running variable; the jump condition is a single comparison — and you can treat "anchor jumped" as a regime-change event worth a fresh order book layout.

### D4 · Flat-range (coil) detector by SMA-band containment *(SMC Algo Pro → "display_third" range module)*

An alternative coil test to W1, framed as *containment of every close in a band*:

```
ma   = SMA(close, 20);  band = ATR(500)            # deep-memory band (see R3)
count = #{ i in 0..19 : |close[i] - ma| > band }
in_range = (count == 0)                            # ALL 20 closes inside ±1·ATR(500) of the 20-SMA

on range start:   box = [ma - band, ma + band]
while in range:   box extends right; merge with a still-active previous box (union)
close > box.top  -> broken UP   (state os = +1)
close < box.bot  -> broken DOWN (state os = -1)
```

**Why it suits a zero-wait engine.** O(20) per bar, O(1) incremental per tick (maintain a count of closes outside the band as each 1m close lands; the ATR(500) and SMA(20) are O(1) recurrences). It is a *different* compression signature from W1 (no ATR-ratio, no violation tolerance — hard containment), useful as a second, independent coil vote: W1 says "volatility is contracting vs background", D4 says "price is boxed by deep-memory vol". Two independent compression detectors agreeing at a range edge is a high-conviction state.

---

## §3 — MARKET MICROSTRUCTURE

### M1 · TJR SMC machine: sweep → MSS → zone-tap FSM *(TJR SMC)*

The batch's cleanest full-cycle microstructure state machine. All levels are consumed-once pivots; all triggers are bar-local (no HTF waits except the optional SMT feed).

```
pivots = pivothigh/low(8, 8); each swing level consumed once (shBroken flag)
BSL/SSL = most recent swing high/low

# stage 1 — SWEEP (arm):
sweep_low  = low  < SSL and close > SSL          # wick pierce + close back inside
sweep_high = high > BSL and close < BSL

# stage 2 — MSS (confirm): within mssWin = 12 bars of the sweep,
#   a break of the sweep-side level WITH displacement:
displacement = |close - open| > 0.6 * ATR(14)
MSS_up   = sweep_low  followed by close > sweeped level with displacement
MSS_dn   = sweep_high followed by close < sweeped level with displacement

# entry zone (adopted at MSS):
if fresh FVG at MSS bar with size >= 0.2*ATR(14):  zone = that FVG
else:  leg   = [sweeped extreme, MSS-bar extreme]
       zone  = 50% equilibrium band of the leg, padded ± 0.1*ATR(14)

# stage 3 — TAP (fire), 20-bar zone validity:
bull_tap = low <= zone.top and close >= zone.bottom and close >= open
short_tap= high >= zone.bottom and close <= zone.top and close <= open
fire consumes the zone (no re-entry into the same zone)

# SL / TP:
SL_long = sweeped low - 0.5*ATR(14)     # BEYOND the swept liquidity (invalidation = re-sweep)
TP = entry ± {1R, 2R, 3R}
win  = TP1 only (win-rate counter)

# SMT divergence (optional gate) vs correlated symbol, same TF, confirmed values:
bear_SMT = we print a HIGHER high than previous swing,
           correlated does NOT make a higher high
bull_SMT = we print a LOWER low, correlated does NOT make a lower low

# killzones (exchange tz): London 02:00-05:00, NY AM 09:30-11:00
# debounce: 10 bars between entries; long/short mutually exclusive

# CONVICTION 0-100:
conviction = 100 * min(1, 0.40*(stage/2) + 0.25*SMT + 0.15*killzone + 0.20*signal)
```

Also: **OB** = last opposite-color candle immediately before the displacement leg (2-bar definition), mitigated when a *close* passes the far edge, cap 6 OBs.

**Why it suits a zero-wait engine.** This is the reference decomposition for a tick engine: (1) a level registry with consumption flags (O(1) pivot events from 1m closes), (2) a 3-stage FSM where *every stage is a single bar-local inequality* — sweep is literally `low < lvl < close`, which a tick stream evaluates continuously (you can arm stage 1 the instant the wick pierces, before the close-back even happens), (3) a zone object with a 20-bar TTL (a simple expiry timestamp), (4) SL placed *beyond the swept extreme* — the structurally correct invalidation (if liquidity is re-swept, the thesis is dead), and (5) a linear convexity score for order sizing. SMT needs a second symbol feed (ETH when trading BTC) — trivial on Binance's multi-symbol WebSocket; the file's `lookahead_off` same-TF request is already a confirmed-value feed.

### M2 · BigBeluga 3-state structure FSM + sweep areas + volumetric OBs *(SMC)*

A heavier FSM with the same grammar as M1 plus three distinctive extras: **sweep-area boxes**, **buy/sell-side volumetric zones**, and **one-shot liquidity prints**.

```
state 0 = init; 1 = CHoCH armed (bos/choch level live); 2 = BOS hunting (trailing main extreme)

BOS candidate is set only when, after a new trend-direction extreme,
TWO consecutive same-direction closes form:
   (downtrend: crossdn and close < open and close[1] < open[1])  -> bos = main low
   (uptrend:   crossup and close > open and close[1] > open[1]) -> bos = main high

SWEEP: wick through the armed level + close back inside
        -> level MOVES to the sweep extreme, marked "x", a fresh level is spawned
BOS:    close through the level -> OB created from the ORIGIN CANDLE of the leg:
        origin = argmax/argmin scan back over the leg; optionally +1 bar if the
        next candle extends the extreme; "Length" mode caps the OB:
            bear OB: [max(low[o], high[o] - 1*ATR(200)), low[o]]
            bull OB: [high[o], min(high[o], low[o] + 1*ATR(200))]
        next CHoCH level = opposite leg extreme found by the same arg-scan
"Adjusted Points": every 2*mslen bars, the CHoCH level may be REPLACED by a newer
        5/5 pivot if it is more favorable (self-updating structure)

SWEEP AREA (unique): after a CHoCH/BOS is armed, watch <= 10 bars (zonethresh):
   if the level is wicked AGAIN (high > zz and close < zz) -> reset counter
   if close re-crosses the level -> emit "Sweep Area" box:
       from min(low of the zone) up to the level   (buy-side liquidity reservoir)
       from max(high of the zone) down to the level (sell-side)

LIQUIDITY PRINT (one-shot): pivots 5/5;
   print = high > level and close < level and high > high[1]   (impulse wick)
   armed once per level; re-arms only when the NEXT pivot prints

BUY/SELL SIDE (volumetric): on a sweep, the origin candle of the sweep leg defines
   an area from the extreme to extreme ± ATR(200) (clamped); label carries
   vol share = vol_area / (vol_buy + vol_sell) * 100

VOLUMETRIC OB: each OB stores its volume; metrics = volume share % across the
   last 5 OBs; activity animation (bl/br position cycling — display, skip)
BREAKER CONVERSION: mitigated OB (close through near edge) -> isbb = true (breaker);
   breaker is deleted only when the OPPOSITE edge is broken (breaker fully failed)
OVERLAP DEDUP: 4-case interval-overlap test between any two zones (containment both
   directions + partial both directions) -> drop one, "Recent" or "Old" priority
```

FVGs here: 3-bar gap (`high[3] < low[1]`), mitigation → gray, full fill → delete, "reduce on fill" option (box shrinks to the remaining unfilled part — same primitive as M5), plus a **raid** flag tracking when price returns into an active gap.

**Why it suits a zero-wait engine.** The "origin-candle OB" is the most defensible OB construction in the batch: it is the *literal bar that sourced the move*, found by a single O(leg) scan that runs once per structure event. The sweep-area box converts a sweep into a *bounded liquidity reservoir with a floor* — in tick terms, a rectangular region where stop-losses are expected to rest; passive limit orders inside it are counterparty to that inventory. The one-shot liquidity print (wick + impulse + close-back, consumed) is the purest tick-native event in the batch: `high > lvl > close` is a 3-comparison predicate on the live bar, and the "re-arm on next pivot" bookkeeping is one flag. The ATR(200)-capped OBs tie zone depth to deep-memory vol (see R3).

### M3 · Zone lifecycle: merge / breaker-flip / mother-bar expansion *(SMC Algo Pro E5)*

A zone registry with an explicit state machine per zone, plus three transformations:

```
# MERGE (on new zone creation, vs the most recent zone):
mergeRatio = 0.1
if new ⊆ last or new ⊇ last
   or |new.top - last.top| < 0.1 * (last.top - last.bottom)
   or |new.bot - last.bot| < 0.1 * (last.top - last.bottom):
    merged = union(new, last); keep last.left; drop last

# LIFECYCLE (per surviving zone):
state 0 = fresh: extends right, untested
wick into zone (high >= bot, was below)   -> state 1: MITIGATED (gray, truncated at touch)
close through zone (low < bot for supply) -> BREAK: delete supply zone AND
    spawn a DEMAND zone at the SAME coordinates          # breaker flip: broken supply = demand
close back through after mitigation      -> state 3: dead (deleted, breaker recorded)
expired (time - left > 2000 bars) or wick-through        -> deleted

# MOTHER-BAR (inside-bar) expansion — "POI" zones:
mother = last NON-inside bar (isb := high < motherHigh and low > motherLow)
3-bar sweep pattern: bar[3] is a local high (high[3] > high[4] and high[3] > high[2])
   -> arm isSweepOBS
confirmation (strong bar after the sweep high) -> supply zone at bar[3] range
if bar[2] was an INSIDE bar:  zone expands to the MOTHER bar's full range
   (the mother bar is the "consolidation origin" the breakout came from)
```

**Why it suits a zero-wait engine.** The breaker flip is the key primitive: **a broken zone is not deleted — it is relabeled with inverted polarity at zero extra cost.** In a tick engine the zone table holds `(top, bot, left, polarity, state)`; a close-through is a 1-comparison event that flips `polarity` and resets `state`, so every level keeps a *memory of which side has already failed* — that is exactly the information a scalper needs for retest entries. The 10%-of-height merge threshold keeps the registry compact (zones that nearly touch are the same level) — O(n) per insert with a bounded n (max 8). Mother-bar expansion is a pure bar-relationship test (3 comparisons), evaluable on the live bar.

### M4 · Order-block taxonomy: four independent definitions (this batch)

Four files define OBs four different ways — the taxonomy is itself the extraction:

| # | Definition | Source | Rule |
|---|---|---|---|
| a | **Velocity ROC** | W2 (SonarLab) | 4-bar open-to-open ROC crosses ±28 bps; OB = first opposite-color candle in 4..15 bar window |
| b | **5-bar impulse gap** | SMC Algo Pro `ob_found` | bar[5] red AND close[4] ≥ open[5] AND the next 3 bars' lows all > high[5] ⇒ *internal bearish OB* at bar[4]/[5] (whichever has the lower low); mirror for bull. i.e. an opposite candle *immediately abandoned by 3 bars* |
| c | **Consecutive-candle** | Simple System "linreg OB" | opposite-color candle at t = periods+1 ago AND all `periods` (5) following candles same-direction AND \|close[t]→close[0]\| ≥ min % move ⇒ zone = [open, low] (bull) / [open, high] (bear) or full wick range |
| d | **Consolidation-origin (range-filtered)** | SWIFT ALGO | on a swing break, scan back to the swing; collect bars whose range < 2·threshold, threshold ∈ {ATR, **cumulative mean range** = cum(high−low)/bar_index}; OB = extreme (min-low for bull) of those bars |

All four reduce to one template: **OB = the origin region of a fast move, identified by "abandonment" (price left and did not return)** — the differences are only the velocity detector (ROC / gap / run-length / pre-break range).

**Why it suits a zero-wait engine.** Every detector is a bounded backward scan (≤ 15 bars) or a running flag (3 consecutive same-color closes = a 3-deep counter). In a tick engine you maintain these as counters and fire the OB *as soon as* the abandonment condition first becomes true — e.g. definition (b) fires the moment the 3rd consecutive bar closes beyond the origin bar's extreme, i.e. with at most a 3-bar delay vs the event, and the zone coordinates are known instantly.

### M5 · FVG toolkit: session-scoped, shrink-on-fill, thresholded *(Simple System; SMC Algo Pro; SMC; TJR SMC)*

```
# 1) SESSION-SCOPED single FVG (Simple System):
#    only the FIRST FVG of the session is tracked (session = daily reset)
#    mitigated when close passes the far edge; alerts: new / mitigated /
#    price-inside / close-cross of the MIDPOINT (50% retrace)
#    -> "the session's gap" is the reference level; its midpoint = 50% zone

# 2) SHRINK-ON-FILL (SMC Algo Pro):
#    mitigation modes: Touch (any wick) / Wicks / Close / Average (midpoint)
#    on partial fill: fill_box.bottom = high (bull gap)  # filled portion recorded
#    the REMAINING unfilled part is the live gap -> the gap object physically
#    shrinks as it is consumed; full fill -> delete
#    minimum size: |gap| >= 1.5% of the 300-bar high-low range (remove_small)
#                  (xref B5 W3: 2× cumulative-mean body threshold — same idea)

# 3) RAID (SMC / BigBeluga): an active gap is flagged "raided" when price
#    returns into it — tracks the raid level as a secondary objective

# 4) TJR: fresh FVG at MSS bar, size >= 0.2*ATR(14), adopted as the entry zone (M1)
```

**Why it suits a zero-wait engine.** FVG creation is the cheapest microstructure event of all: `low > high[2]` (bull) is a 1-bar-2 comparison — no pivots, no lookback, evaluable on the *second* candle of the pattern, i.e. before it closes. Shrink-on-fill makes the gap a *depleting inventory object*: each tick that fills it reduces its remaining depth, which in a tick engine is exactly what you want for sizing (thinner gap = less counterparty resting there). The 300-range % floor and the 0.2·ATR(14) floor are noise filters in price units (scale-free per instrument) — both are single comparisons against a running max/min.

### M6 · Sweep/SFP mechanics with confirmation & one-shot arming *(SMC Algo Pro SFP; SMC; TrendFilter LQDT)*

```
# SFP (swing failure pattern) — E5:
pivots 20/20
bull_SFP = low  < pivotLow and close > pivotLow and open > pivotLow
           and low == lowest(low, 20)              # the failed sweep IS the 20-bar low
           and lowestClose(20) >= pivotLow         # nothing CLOSED below it
signal   = bull_SFP[3]                             # SFP three bars ago
           and close > level[1] > level[2] > level[3]   # 3 consecutive closes above
           and bar_index >= last_signal + 10       # cooldown
# mirror for bear

# one-shot liquidity print (BigBeluga, see M2):
#    wick + impulse (high > high[1]) + close-back, armed once per level

# LQDT reclassification (TrendFilter, see D2):
#    swept-but-not-broken level -> liquidity line, still tradeable
```

**Why it suits a zero-wait engine.** The SFP is a *failure* detector: it requires the sweep bar to be the window extreme AND nothing to close beyond it — that is a bounded-window min/max plus a close comparison, O(20) incremental per tick. The "3 consecutive closes beyond the level" confirmation is a 3-deep counter — in a tick engine you can relax this to "price persists beyond the level for X ms / N ticks" and get the same anti-whipsaw property with far less latency than 3 bars. Cooldown + one-shot arming are single counters.

### M7 · IDM-filtered CHoCH (two-step structure confirmation) *(SMC Algo Pro E5)*

Structure flips require the counter-pullback (IDM — "inducement") to *fail*:

```
lastH/lastL  = most recent structural high/low (updated on every new extreme)
idmHigh/idmLow = most recent COUNTER-direction pullback extreme
   (when a new high forms, idmLow := the previous low; mirror for lows)

CHoCH candidate: close > lastH during downtrend (or close < lastL in uptrend)
   -> findIDM armed
"with IDM" confirmation:
   candidate is CONFIRMED only if the pullback does NOT break the IDM level:
       bull: subsequent low < idmLow  -> structure ROLLS BACK (CHoCH void,
             the "BOS" label is downgraded / lines fixed)
       (i.e. the counter-side inducement got raided => the flip was fake)
BOS: close > lastH with trend (isPrevBos flag) — no IDM step

OB PROMOTION: on any CHoCH/BOS, unmitigated zones whose near edge is at/above the
   old HL price and whose far edge is at/below the new level are CONSUMED and
   promoted to "EXT OB" (structure) or "IDM OB" (inducement) —
   the break *validates* the zones it passed, marking them as active interest
```

**Why it suits a zero-wait engine.** This is the batch's best answer to "when is a structure flip real?": the flip must survive a *return* to the pullback level. In a tick engine, after a close-through of `lastH`, you rest a *monitor* at `idmLow` — if price gets there before printing a higher low, the flip is void and your short-side orders re-arm. It converts a binary event into a two-stage event with a *falsifiable* condition, which is exactly what an execution engine can exploit (you can take the flip early and hedge the IDM-risk leg with a defined stop at the IDM level).

### M8 · Zone registry: ATR-scaled boxes, touch-counting, break-to-line *(SWIFT ALGO; TrendFilter TProtein+)*

```
box = pivot ± 0.25*ATR(50)        (box_width 2.5 -> atr*(2.5/10))
dedup: reject a new zone if its midpoint is within ± 2*ATR(50) of an existing midpoint
cap: 20 zones per side (history_of_demand_to_keep)

TProtein+ adds per-zone TOUCH COUNTING:
   if a bar's high/low lands inside [bot, top]:  zone.count += 1
   (zone label shows "count / TF"; up to 9 independent HTF registries,
    each with its own ATR(50) and pivot scale)

BREAK: close >= top (supply) or close <= bot (demand)
   -> zone deleted, replaced by a LINE at the zone MIDPOINT (dotted)
   -> the broken zone persists as a level, not as a zone
```

**Why it suits a zero-wait engine.** ATR(50)-scaled bins make the registry scale-free; the 2·ATR dedup is one comparison per candidate. Touch-counting is the same primitive as B5 M1 (rejection counter) and the B4/5 touch-count S/R — now with an explicit *count* per zone instead of a boolean. In a tick engine a "touch" is a state-transition event (price enters the band) with hysteresis (leaves the band before it can count again) — zero bar-close latency. The break-to-line conversion preserves the level's history (a broken zone's midpoint remains a level of record) — cheap bookkeeping, meaningful for limit-order placement.

---

## §4 — DYNAMIC RISK

### R1 · VCE structural stop with ATR clamps *(VCE — see W1)*

```
rawSL = coilExtreme ∓ 0.20*ATR(14)              # stop BEYOND the structure that
                                                #   invalidates the setup
dist  = clamp(|entry - rawSL|, 0.30*ATR14, 2.0*ATR14)   # floor & ceiling in ATR units
SL    = entry ∓ dist
TP1,TP2,TP3 = entry ± {1.0, 1.5, 2.0} * dist    # pure R-multiples
TP1/TP2 = MILESTONES (dots only, trade stays open); TP3 and SL are terminal
SL touched before TP3 -> close; same-bar SL+TP3 -> SL WINS (worst-case governs)
post-outcome cooldown = 8 bars
```

**Why it suits a zero-wait engine.** The clamp is the interesting part: the stop is *structural* (coil edge) but *bounded* (0.3–2 ATR), so R:R stays comparable across coil sizes. In a tick engine the coil edge is a hard price level you know the instant the watch arms — the stop is a standing order at a known price, and the 0.3·ATR floor prevents knife-thin stops that noise will pick off. The "SL wins on same-bar touch" rule is a tick-engine-native tie-break (check SL first in the same event loop).

### R2 · One-bar-ATR trailing family *(Simple System UT Bot; SUPER Scalping "Super Duper Trend")*

```
UT Bot:  dist = 2 * ATR(1) = 2 * TR[1]          # ATR of period 1 == last true range
stop_t = max(stop_{t-1}, src_t - dist)  while src > stop     (long; mirror short)
flip when src crosses stop; signal = cross of src and stop
   -> the trail is anchored to the IMMEDIATE previous bar's range:
      a volatile bar -> wide trail, a quiet bar -> tight trail, next bar

Super Duper: dist = 2.2 * ATR(10)
longStop ratchets UP only when lowPrice[1] > longStopPrev   (respect prior bar low)
doji guard: if O=C=H=L -> hold the previous stop (no jump on a zero-range bar)
```

**Why it suits a zero-wait engine.** `ATR(1)` is just the last bar's true range — a single float refreshed once per 1m close; between closes the stop is a static price (no recomputation per tick). The ratchet ("only improve when the prior bar already cleared it") is the classic anti-chop property: the stop can only tighten when the market has *already proven* the move. In a tick engine you implement both as `stop = max(stop, f(last_closed_bar))` — O(1), deterministic, and the doji guard is a 4-equality check.

### R3 · Deep-memory volatility baseline (200–300 bar ATR) as a scaling constant *(TrendFilter; SMC; SMC Algo Pro; strategy with signals)*

Across the batch, **structural** objects are sized by a ~200–300-bar ATR, while **entry risk** uses 10–20 bar ATR — a deliberate two-timescale risk architecture:

```
deepATR   = SMA(ATR(200), 200)          # ~400-bar smoothed ATR (TrendFilter x0.8;
                                        #   TP ladder = 5/10/15 x deepATR)
ATR(200)  # BigBeluga: OB depth cap, buy/sell-side zone span
ATR(300)  # E5: liquidity box = pivot ± 0.25*ATR(300); FVG min-size uses 300-range
ATR(500)  # SMC Algo Pro: flat-range band (D4)
entry R   # 10-20 bar ATR everywhere (TJR 0.5*ATR14 SL pad, VCE 0.2-2*ATR14 clamps...)
```

**Why it suits a zero-wait engine.** A 200–500 bar ATR is a *slowly varying constant* in tick time — it changes ~0.4% per 1m bar at most, so it can be computed once per bar-close and treated as fixed between closes. Using it for *zone geometry* (box depth, FVG floor, liquidity pad) while using fast ATR for *stop distance* means your level map is stable while your risk is reactive — two clocks, two purposes. Cheap to maintain (one RMA per period) and it makes all price thresholds scale-free across symbols.

### R4 · Amplitude-window ratchet trail *(SUPER Scalping "Super Xtrend")*

```
atr2 = ATR(100) / 2;  dev = 2 * atr2 = 1 * ATR(100)
amplitude = 2 bars
# trail state:
downtrend: down1 = min(down1, minHighPrice)   where minHighPrice =
           high[|highestbars(amplitude)|] etc. — ratchet over the amplitude window
flip when SMA(high, 2) / SMA(low, 2) cross the ratcheted extreme
      AND close crosses the prior bar's high/low
stop = trail ∓ dev
```

A chandelier-style trail whose anchor is the *window extreme* (not the running close) and whose width is 1× the 100-bar ATR — slow anchor, wide band: a swing-trading trail. (xref B4 R5 chandelier; kept for the amplitude-window anchor variant.)

### R5 · Win-rate-first geometry: SL wider than TP1 *(Smart Money Trades Pro)*

```
entry at the broken 20/20 pivot (BOS event; body or wick confirmation selectable)
targetRange TR = 2 * ATR(14)
TP1, TP2, TP3 = entry ± {0.8, 1.6, 2.8} * TR
SL            = entry ∓ 1.2 * TR          # SL (1.2 TR) is WIDER than TP1 (0.8 TR)
```

This is the inverse of the usual R:R posture: **TP1 at 0.8R, stop at 1.2R ⇒ the first target is *inside* the stop distance** — a win-rate-maximizing geometry (TP1 hit rate > 50% is easy; TP3 at 2.33R is the payoff). With three partial ladders at 0.8/1.6/2.8R the effective expectancy comes from the tail. **Why it suits a zero-wait engine:** nothing exotic — it's a sizing posture — but it is worth recording because most extracted ladders (VCE 1/1.5/2R, TJR 1/2/3R) are R:R-positive at TP1; this file explicitly optimizes the *other* way (frequency over ratio). A tick engine can A/B both ladders on the same entry stream since the geometry is just three price offsets.

### R6 · Event-gated TP ladder + choppiness gate + EOD force-exit *(Trend Trader Pro)*

Salvageable risk mechanics around its (excluded) EMA9/21 trigger:

```
choppiness CI = 100 * log10( sum(TR, 14) / (HH(14) - LL(14)) ) / log10(14)
gate: trade only when CI < 60                     # filter chop (log ratio of
                                                  #   path length to net move)
staged ladder: TP2+ unlocks ONLY IF vol > 1.2*SMA(vol, 20) OR close is on the
               right side of EMA9 at TP1         # continuation-confirmed scaling
re-entry after SL allowed on EMA9 reclaim        # (one re-arm, not infinite)
EOD: forced flat at 15:59 NY; stoppedOut flag blocks same-day re-entry
HTF 3-min trend via gaps_off + lookahead_on confirmed-bar idiom (legitimate)
```

**Why it suits a zero-wait engine.** CI is a running sum + running max/min (O(1) incremental) and is a *regime* input (trade/no-trade), not a signal — the right place for it in an HFT stack. The volume-gated ladder is the batch's cleanest "scale up only on proof" rule: TP2/TP3 are *not placed* until an RVOL condition fires — in a tick engine that's one `volume_bar / volume_sma20` check. The 15:59 force-exit is a timestamp gate (trivial) and the stoppedOut flag is the standard "no re-entry after a stop today" state.

---

## §5 — CONFLUENCE / SCORING

### S1 · 7-factor boolean score (two independent implementations this batch)

KhanSaab "sniper entry" and "TM Sniper Pro" implement the *same* 7-factor engine — two independent corroboraions of the pattern:

```
factors (bull; mirror for bear):
  1  close > VWAP(session)
  2  RSI(14) > 50
  3  MACD line > signal
  4  EMA9 > EMA21
  5  ADX > 25 AND close > EMA9          # trend-strength AND direction
  6  volume > SMA(volume, 20) AND close > open    # participation + body
  7  HTF RSI(5m) > 50                      # higher-timeframe momentum (confirmed feed)

bullPct = 100 * (#true_bull / 7);  bearPct = 100 * (#true_bear / 7)
STRONG = |bullPct - bearPct| >= 40        # ~3+ factor separation
base signal gate: score >= 4/7
```

TM Sniper Pro additions: TP1 (1.5·ATR14) → SL moved to breakeven; 3-bar cooldown after any exit; 5R target ladder; R = 1.5·ATR14. (Both files' *trigger* is the excluded EMA9/21 cross — the score is the kept part.)

**Why it suits a zero-wait engine.** Seven booleans, each O(1) or O(window) with running state; the score is a popcount. In a tick engine the score *changes state* intrabar as factors flip (VWAP-side and close-vs-open flip mid-bar; RVOL accumulates per tick), so you can size continuously by score rather than once per bar. The |diff| ≥ 40 "strong" tier is a separation, not a threshold — it is immune to a global factor drift (if all 7 factors are noisy, diff stays small).

### S2 · 5-factor signal strength + break-even win-rate display *(Sniper Trading Algo Pro)*

```
factors (bull; mirror):
  1  CCI(5) > 0
  2  ADX > 18 AND +DI > -DI
  3  AccDist > SMA(AccDist, 21)
  4  MFI > SMA(MFI, 9)
  5  linreg(MOM(10), 14) rising
strength = count / 5   (printed on the entry label)

portfolio math (the kept part):
win_rate   = #TP1 hits / #trades          # TP1, not full trade, as the win metric
BE_Rate    = SL / (TP1 + SL) * 100        # breakeven win rate for the R:R
profitable = (TP1% > BE_Rate)
```

**Why it suits a zero-wait engine.** The five factors are all running-state booleans (same popcount pattern as S1, different indicator mix — note the CCI5/AccDist choices are the *fastest* oscillators in the set, appropriate for sub-bar evaluation). The BE_Rate line is the correct accounting identity for partial-target strategies (win = TP1): for SL 1.5%, TP1 0.5%, BE win rate = 1.5/(0.5+1.5) = 75% — useful for the engine's own expected-value monitor.

### S3 · ATR-normalized touch-clustering S/R with volume-validated breaks *(SMC Algo Pro → S/R MTF module)*

The most complete touch-count S/R in the batch, with three distinctive mechanics:

```
pivots 15/15; keep last 15 (7 in memory-optimized mode); cap 250-bar traverse
TOUCH TOLERANCE is ATR-NORMALIZED (unique):
   |p1 - p2| <= TR(pivot) * (1/30)        # touch window scales with the LOCAL
                                          #   bar's true range, not a fixed %
strength = number of touching pivots >= strength (1..4; default 1, up to 3 levels
   per type per TF; cross-TF dedup: same price on 2 TFs -> merged label)
dynamic zone width = (ATR(30)/price)*100/3 %

BREAK with FALSE-BREAK FILTER (unique):
   break bar = first close beyond the level since the last touch
   true break REQUIRES a volume signature:
      (avg(vol of 2 bars after break) - avg(vol of 15 bars before)) / 15-bar avg
            >= 30%                                     # spike, not drift
   break level recorded = the break bar's LOW (resistance break) / HIGH (support)

RETEST: any bar within 1/30*TR of the (broken) level, >= 3 bars after the
        previous retest, only counted before the break time
```

**Why it suits a zero-wait engine.** The TR-normalized touch window is the key improvement over fixed-percentage clustering (B4/5): the tolerance *is* the bar's own noise scale, so the same code works across vol regimes. The false-break volume filter is the batch's best "is this break real" test and is cheap: two running volume sums (2-bar and 15-bar) evaluated at the break tick. A tick engine gets the break event on the first tick that crosses the level; the volume signature can be checked on the *following* bars (or, with aggTrade accumulation, intrabar) — and if the filter fails, the level is *un-broken* (rolled back), which is a state rollback a charting tool can't express but a state machine handles trivially.

### S4 · Live per-level hit-rate statistics + N-parallel stop optimizer *(Ultimate ORB — LuxAlgo)*

The ORB trigger itself (close-cross of the 09:30–10:00 range edge) is standard (xref B4 D6 / B5 D5); the kept parts are the *statistics*:

```
# adaptive volume profile of the opening range:
bin_tick = max(mintick, orRange / vpRows)          # resolution adapts to the range
volMap   = per-bin volume accumulation over the OR session
POC      = argmax(volMap)

# per-level HIT-RATE stats (the unique part):
for each OR extension level (multiples or 0.382/0.618/1.0 x OR range):
    track day-reached flags for U1/U2/U3, D1/D2/D3 across the last N days
    cumulative % reached over totalSessions -> each level carries a live
    "reached on X% of sessions" statistic

# 5-WAY PARALLEL STOP OPTIMIZER (the other unique part):
simulate the SAME trade concurrently under 5 stop widths
    (1.0 / 1.5 / 2.0 / 2.5 / 3.0 x ATR14)
    -> report which width would have produced the best outcome
       (a live what-if over the current open trade, not a backtest)

# one signal per direction per day (canSignalUp/canSignalDown flags)
# trail = 2*ATR14
```

**Why it suits a zero-wait engine.** The parallel-stop optimizer is the only *online* what-if simulator in the whole corpus: it is N copies of the same exit state machine sharing one price feed — in a tick engine that is N×(a few floats) of memory and the best width is known *before* the trade ends, so the live stop can be switched to the currently-optimal width (with a hysteresis to avoid churn). The per-level reach-rate is a per-level binomial counter — the exact statistic a limit-order engine needs to decide which levels to actually rest orders at (a level reached on 80% of sessions is a near-certainty target; one reached on 15% is a lottery ticket). The adaptive bin width makes the VP scale-free.

---

## §6 — Delta over batch 5 (what B6 adds)

1. **SMC FSMs matured into a canonical grammar.** Three independent full implementations this batch (TJR M1, BigBeluga M2, E5 M7 + M3) all converge on the same primitives: consumed-once pivots, sweep = wick-pierce + close-back (reclassifies the level, does not consume it), displacement-gated confirmation (TJR: 0.6·ATR body; BigBeluga: 2 consecutive same-direction closes), origin-candle OB, mitigation modes (close/wick/avg), breaker = flipped polarity. B5 had zone *rejection counters*; B6 adds the full *event sequence* around zones.
2. **Compression detection appears twice, independently** (W1 VCE ATR-ratio coil with violation tolerance; D4 SMA-band containment). B5's W7 "dry bar" was a single-bar vol signature; B6 gives two stateful multi-bar coil machines. Template: `compressed AND at-extreme AND bounded-age ⇒ reversal watch`.
3. **Touch-count S/R is now a 4-file family** (strategy-with-signals clustering, SWIFT, TProtein+, E5 MTF) — canonical set: pivot 10–15/10–15, cluster window = % of 284–300 bar range OR TR·(1/30) (E5's local-TR normalization is the newest), count ≥ 2, cap ~5–20 levels, break → line at midpoint. E5 adds the only *volume-validated* break in the corpus (S3).
4. **Cumulative mean range** (`cum(high−low)/bar_index`) appears as an OB-filter threshold in 3 files (SWIFT, simplealgo v3, SMC Algo Pro) — B5 W3/W4 already used cum-mean for FVG/OB sizing; B6 extends it to *consolidation detection* (bars with range < 2×cum-mean are "quiet origin" bars).
5. **Wick-split volume attribution** (E5: `buyVol = V·(C−L)/(H−L)`, `sellVol = V·(H−C)/(H−L)`) independently re-invents B5 W2's Nostalgia-VP split, now applied per *OB* (volume metrics per zone).
6. **Gaussian IIR trend math** (W5, two files) is new to the corpus — B1–B5 trend filters were all MA/ST/KAMA family; a fixed-coefficient multi-pole Gaussian + linreg flatten is the lowest-lag trend line seen so far.
7. **Online what-if** (S4 parallel stop optimizer) has no precedent in B1–B5 — the only live re-optimization of an open trade.
8. **Level registries with age/weighting** (W4 unmitigated HTF stack, M8 touch-count, S4 hit-rate) mark a shift from "levels as lines" to "levels as objects with lifecycle statistics" — the natural representation for a tick engine's order-placement policy.

---

## Appendix A — Full exclusion list (B6)

**GUI/visual (red line 3):** all plot/plotshape/plotchar/plotcandle/plotcandle/barcolor/bgcolor/line/label/box/polyline/table/linefill code in all 19 files; all dashboards (VCE state HUD, Sniper-Pro PERF HUD, ADX MTF table, SuperScalping logo, trend ribbon, volume histograms, profile boxes); all Telegram link cells (`@mrexpert_ai`, `@simpleforextools`); all color themes/palettes; all alertcondition *wiring* (kept only where the condition is a logic primitive listed above).

**Repaint/lookahead mechanisms (red line 1, excluded; port notes in-line):** Unmitigated HTF `curr` value (use bar-close events); SMC PDHL/PWH/… live H/L (display only — use confirmed-bar idiom); SMC Algo Pro plain `request.security` HTF feeds (liquidity pivots, HTF FVG) — port to 1m-resampled confirmed closes; SWIFT HTF alternate-TF variant (use the `[1]`+lookahead_on idiom only); SUPER Scalping "tomorrow's CPR" (uses today's forming H/L — valid only after daily close); Sniper Trading Algo Pro `request.security(same TF, …[rt?1:0])` realtime shift (port: always use confirmed values).

**Lagging-trigger exclusions (red line 2):** EMA9/21 crosses (KhanSaab, TM Sniper, Trend Trader Pro); SuperTrend crosses (simplealgo v3 ST(7,10); strategy-with-signals ST(5,10)+confluence); KAMA(4/EF80)×VIDYA(CMO-α) cross (Sniper Pro "Confirmation"); SSL+TDFI+RSI-65-cross (Sniper Pro "SRT"); engulfing+RSI50 (Sniper Pro "RE Beta"); squeeze-release as *trigger* (Sniper Pro "MS Beta" — the squeeze math itself is xref B1 Raschke); MACD-signal/RSI-ladder/PSAR/BB/Donchian-envelope displays and their cross triggers; WaveTrend display (TrendFilter; its extreme-cross read is noted, not extracted as a trigger); RSI divergence *as signal* (kept only as the 5-level nested-divergence structure note below).

**Derivatives (red line 4):** TrendFilter liquidation module (leverage 5×–100× liquidation prices, volume-spike liquidation ladder); SUPER Scalping Settlement/IV module (settlement ± σ levels from 21-day log-return stdev, τ/252 scaling); TrendFilter futures-volume blending (`BINANCE:BTCUSDTPERP` volume added to spot — noted as a participation-proxy idea, not extracted).

**Structure notes (kept as observations, not extracted):** SUPER Scalping 5-level *nested* RSI divergence (`div_n` requires all n pivots strictly more extreme in both price and RSI — a depth generalization of B5 D2's 4-type divergence); CPR formulas (standard Camarilla: P=(H+L+C)/3, TC=(H+L)/2, BC=2P−TC, R1=2P−L, R2=P+H−L, R3=H+2(P−L), S-mirrors) — level math only, no signal; OTE golden zone 0.78–0.61 (E5) — standard fib; Gann square-of-9 (strategy-with-signals, Simple System) — esoteric, display only; session levels London/Asia/NY OHL (E5) — standard; 8AM NY candle pip-fib (strategy-with-signals) — FX display only; zigzag extremity channels (E5) — display; auto trendlines (Simple System) — O(n²) display; inside/outside bar markers (E5) — display.

---

## Appendix B — Porting notes for a zero-wait tick engine (Binance Spot, 1m klines + aggTrade + bookTicker)

| Primitive | Tick-engine realization |
|---|---|
| W1 coil FSM | per-symbol state: 2 ATRs (4/20), 50-bar H/L, compLen, box, viol, expiry. Fire passive orders at `watchHigh±tick` the moment the watch arms; kill on violation > 2 or expiry. No bar-close wait — the "trigger" is your order being hit. |
| W2 ROC OB | running 4-bar open array; `pc` updated per tick (current open from last aggTrade); origin-candle zone from a ≤15-bar backward scan at event time. |
| W3 intersection matrix | cumsum-based SMA vector (O(N) per bar, O(1) per pair check per tick); publish intersection-price clusters as pullback targets. |
| W4 unmitigated HTF stack | resample 1m→15m in-process; register on HTF close only; sorted registry with age = session-count delta; mitigate on wick touch (tick-native). |
| W5 Gaussian filter | fixed-coefficient IIR registers (≤4 taps) updated per tick; O(1). The 22-bar linreg flatten is a running linreg (normal equations on a sliding window, O(1) updates). |
| D1 body-momentum | two ALMA(2) recurrences on close/open; cross = ordering flip, evaluable first-tick. |
| D2 dual-scale FSM | 1/1 pivot = previous 1m close bar's extreme (zero latency); 30/30 slow level updated on confirmed bars; sweep-vs-break reclassification on live price persistence. |
| D3/D4 channels | 1 float anchor + threshold compare; 20-close band counter (incremental). |
| M1 TJR FSM | level registry (8/8 pivots from confirmed 1m bars, consumed-once flags), 3-stage FSM with bar-TTLs, zone = FVG-or-50% band, SL beyond swept extreme, SMT via second symbol feed (ETH/BTC), killzone = UTC-offset clock, conviction = linear score. Every stage is a 1–3 comparison predicate — the whole machine runs per tick on < 100 floats. |
| M2 BigBeluga | origin-scan O(leg) once per structure event; sweep-area = min/max over a ≤10-bar window; one-shot print = 3 comparisons + re-arm flag; breaker = polarity flip on close-through. |
| M3 zone lifecycle | zone = (top, bot, left, polarity, state∈{fresh,mitigated,broken}); merge = 4 comparisons vs newest zone; breaker-flip on close-through; mother-bar = 3 comparisons. |
| M4 OB variants | velocity (4-bar open array), impulse (3-deep same-color counter + origin compare), consecutive (5-deep counter + % move), consolidation-origin (leg scan with range < 2×cum-mean test). |
| M5 FVG | creation = `low > high[2]` (second bar of the pattern, no wait); shrink-on-fill = update remaining depth on each filling tick; floor = max(1.5% of 300-range, 0.2·ATR14). |
| M6 SFP | 20/20 pivot + window-min/max + close comparison + 3-deep persistence counter + cooldown. |
| M7 IDM CHoCH | after close-through of lastH/lastL, rest a monitor at the IDM level; void the flip if it is tagged before a new higher low. |
| M8 zone registry | ATR(50)-scaled bins, 2·ATR dedup, touch counter with hysteresis, break→line-at-midpoint. |
| R1–R6 | all stop/TP geometry is static price offsets from known levels — standing orders; clamps and gates (CI < 60, RVOL 1.2, 15:59 EOD, 8/10-bar cooldowns, stoppedOut flag) are counters/timestamps. |
| S1–S4 | popcount scores (7-factor, 5-factor), TR-normalized touch clustering with 2-bar/15-bar volume sums, per-level binomial reach-counters, N-parallel stop state machines (N float copies of the exit FSM). |

**General port rules (re-stated from B1–B5, confirmed by B6):** (1) anything the files get from `request.security` must become an in-process resample of the 1m feed, evaluated on *confirmed* HTF bars only; (2) "close" in a trigger should be read as "price persisting beyond the level" — a tick engine gets strict earlier signal from the same condition; (3) every box/zone in these files is a *resting order zone* — the Pine chart draws it; the engine *trades* it; (4) two-timescale ATR (deep 200–300 for geometry, fast 10–20 for risk) is the recurring architecture and should be preserved; (5) mitigation modes (close/wick/avg) map directly to tick persistence thresholds.

**B6 totals:** 20 files (19 unique) → **27 concepts** (W1–W5, D1–D4, M1–M8, R1–R6, S1–S4) + 12 cross-referenced rows. Running corpus across B1–B6: 230 concepts / 120 unique files.
