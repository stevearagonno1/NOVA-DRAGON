# HFT Edge Extraction — BATCH 7 (files 122–130)

**Scope.** 9 Pine files, **6 unique codebases** (3 confirmed duplicate pairs — see dedup table).
**Focus.** Wildcard/innovative edges, low-lag directional math, microstructure (OB/FVG/MSS without delayed-closure waits), dynamic risk, confluence scoring.
**Output convention.** No raw Pine/MQL — Python pseudo-code / closed-form math + why each primitive suits a zero-wait tick engine (Binance Spot HFT on 1m klines, `aggTrade`, `bookTicker`).
**Red lines enforced.** (1) repaint/lookahead mechanisms excluded (port notes where salvageable); (2) lagging-indicator slow crosses excluded as *triggers*; (3) all GUI/plotting/label/table/Telegram-dashboard code excluded (alert *logic* kept); (4) derivatives logic excluded (none present this batch).

**Dedup table (B7).**

| File | Relation |
|---|---|
| Xpert Algo.txt | byte-level cosmetic twin of `X.txt` — diff = 15 lines (title, license header, Telegram handle only). Extracted once as **X-family**. |
| XALGOX-15M_1H_1D.txt | cosmetic twin of `XALGOX.txt` — diff = Telegram handle + end-of-file. Extracted once. |
| ZZ Algo  Signals & Overlays.txt | cosmetic twin of `ZZ Algo.txt` — diff = handle only. Extracted once. |
| ZZ Algo.txt | same codebase family as `X.txt` (shared RSI-SuperTrend, trap detector, consolidation box, ratchet-Ichimoku, MTF wrapper); deltas: sensitivity 4.5 (vs 2.4), Ichimoku *Kumo* fill added, `f_sl_crossed` uses the trailing-stop line, SMC module and auto-trendline removed, TsSlow flip branch variant. Cross-referenced, not double-extracted. |

**Batch flagships.** `Viprasol` (online Naive-Bayes order-flow classifier — first probabilistic signal grader in the corpus), `WaveTrend` (auto-period log-regression trend channel + Elliott-wave rule engine with projected completion boxes + Ehlers IIR filter zoo), `X-family` (RSI-space SuperTrend, extreme-arrest consolidation detector, fib-buffered MSB).

---

## Red-line exclusion table (B7)

| File | Excluded mechanism | Red line |
|---|---|---|
| WaveTrend.txt | WaveTrend oscillator signals (wt.o×wt.s cross at ±60/±75/±125 extremities, midline crosses); XTL double-CCI ±37 threshold crosses; EWO SMA5−SMA34 cross + EWO signal cross; EWO2 ratio-cross signals; Squeeze-momentum release arrows (xref B1) | (2) |
| WaveTrend.txt | HTF EMA(13) trend levels at 6h/12h/1D — `gaps_off + lookahead_on` on the **unindexed** expression = live-forming HTF value in realtime (display only) | (1)-flag |
| X.txt / Xpert / ZZ | **trigger = SuperTrend(2.4/4.5, 10) cross** + lagging confluence (MACD>0 rising, EMA150>EMA250, HMA55 slope, ADX>20, Donchian-30 state) | (2) |
| X-family | QQE oscillator cross triggers (ratchet-band *math* kept as D3); Heikin-Ashi EMA(5/9/21) trend cloud, MACD-histogram bar-color gradients, 13-bar close<close[4] trend coloring, 365-box bar history | (3) + (2) |
| ZZ Algo.txt | `securityNoRep` higher-TF branch uses `gaps_off + lookahead_on` on **unindexed** src → live-forming HTF EMA200 (the X/Xpert version uses `lookahead_off` = confirmed — clean; flag is ZZ-variant only) | (1)-flag, ZZ variant |
| XALGOX.txt | **trigger = ALMA(50, off 2, σ5)-on-close vs ALMA(50)-on-open cross** — two 50-period Gaussian MAs crossing = slow lagging cross (the close-vs-open *concept* is xref B6 D1; the 50-period realization is the excluded class); `reso()` HTF resample uses `gaps_off + lookahead_on` on the live expression → live-forming HTF values | (2) + (1)-flag |
| (all files) | plot/plotshape/plotchar/plotcandle/barcolor/bgcolor/line/label/box/polyline/fill/table code; all dashboards (X-family Smart Panel, VCR panel, WaveTrend tables); all Telegram cells (`@simpleforextools`, `@mrexpert_ai`); all alertcondition *wiring* (conditions kept where extracted) | (3) |
| (all files) | — no leverage/liquidation/futures/settlement-IV logic present in this batch | (4) n/a |

---

## §1 — WILDCARD / INNOVATIVE EDGES

### W1 · Online Naive-Bayes order-flow classifier *(Viprasol)*

A self-supervised three-class Gaussian Naive Bayes trained **online, in O(1) per bar, with zero stored samples** — it classifies the current bar as *Bull / Bear / Diverged* from cumulative-volume-delta features, and fires only when the posterior clears a probability threshold.

**Flow features (per bar; per-tick in port).**

```
hl    = high - low + mintick
delta = volume * (close - low)/hl - volume * (high - close)/hl   # wick-split delta
CVD  += delta

cvdRoc  = (CVD - CVD[n]) / (|CVD[n]| + eps)          # n = 14, normalized CVD velocity
priceRoc= (close - close[n]) / close[n]
slopeR  = linreg(CVD, 10, 0) - linreg(CVD, 10, 1)    # first difference of the CVD fit

F1 = z50(cvdRoc)    # rolling z-score, window 50
F2 = z50(priceRoc - cvdRoc)   # price/flow DIVERGENCE (signed)
F3 = z50(slopeR)     # CVD regression slope
```

**Online training (running sums, no sample storage).**

```
label from bar [1] (realized, non-lookahead):
    Bull    = priceRoc > 0 and cvdRoc > 0     # price and flow agree up
    Bear    = priceRoc < 0 and cvdRoc < 0     # agree down
    Diverged = otherwise                      # explicit NO-TRADE class

per class c in {Bull, Bear, Div}:  maintain (n_c, ΣF_k, ΣF_k²) for k=1..3
    μ_ck = ΣF_k / n_c
    σ_ck = sqrt(max(ΣF_k²/n_c - μ_ck², 1e-4))
prior_c = n_c / Σ n_c                        # empirical frequency (fallback 0.5/0.25/0.25)

posterior_c = prior_c · Π_k N(F_k ; μ_ck, σ_ck)  /  Σ_d (same for d)
warmup = (Σ n_c >= 100)
```

**Signal stack.**

```
long  = warmup and postBull >= 0.70 and close > EMA(50) and CVD > CVD[1]
short = warmup and postBear >= 0.70 and close < EMA(50) and CVD < CVD[1]
fire  = cluster-head (state[1] false) and bar-close gate and cooldown(5 bars)
        and (optional) volume > 1.5 · SMA(volume, 20)
confidence tiers: posterior >= 0.85 (high) / >= 0.75 (mid)
self-audit: 1-bar-ahead hit rate = [# argmax-posterior[1] == realized class[0]] / evals
regime flip event = currentRegime in {+1,-1} changed (regime = threshold+EMA-side state)
SL = 1.5·ATR(14);  TP = 2.0 · SL
```

**Mechanics.** The label rule is the heart: *bullish* = price and CVD rising together; *diverged* = they disagree. The classifier learns, per symbol, what the joint (F1,F2,F3) signature of each state looks like, and the posterior is a continuous confidence in [0,1] rather than a binary cross. The Diverged class is first-class: a flow-price disagreement is an explicit *no-trade* state, not a fallback.

**Why it suits a zero-wait engine.** This is the cheapest real classifier in the corpus to port: 9 running sums (3 classes × 3 features, each needing Σ and Σ² plus n) + 3 sliding-window z-score accumulators + 3 Gaussian PDF evaluations — pure O(1) per tick, no arrays, no backtest data, no training phase beyond the 100-bar warmup. CVD is even *more* accurate on a tick feed than on bars (aggTrade carries the maker/taker flag, so `delta` can be exact per trade instead of the wick-split estimate). Because the posterior is continuous, the engine can **size continuously by probability** (e.g. position ∝ postBull − postBear) and can react the moment a threshold is crossed *intrabar* — the bar-close gate in the file is conservative, not structural. The self-audit counter is a built-in degradation monitor (if hit-rate decays, the regime's statistics have shifted — the running sums adapt, and the audit tells you how fast).

### W2 · RSI-space SuperTrend with neutral-zone flip gate *(X-family: X, Xpert, ZZ — identical block, 3 corroboration instances)*

A SuperTrend (ratchet ATR-band flip-flop) applied **to an oscillator instead of price**, with the band width taken from the *oscillator's own smoothed volatility*, and entries allowed only when the flip occurs while the oscillator is in its neutral zone.

```
RsFast = EMA( RSI(close, 50), 30 )                 # heavily smoothed RSI

# ATR OF THE OSCILLATOR (true range of the RSI series):
tr_rsi = |RsFast - RsFast[1]|
WWMA   = EMA(tr_rsi, 50)                           # alpha = 1/50
ATRRSI = EMA(WWMA, 50)                             # double-smoothed oscillator vol

TsUP = RsFast + 4.236 * ATRRSI                     # 4.236 = fib extension multiplier
TsDN = RsFast - 4.236 * ATRRSI

# SuperTrend flip-flop in RSI space:
TsSlow = TsUP < TsSlow[1] ? TsUP :                                  # below lower band -> hold lower
         RsFast > TsSlow[1] and RsFast[1] < TsSlow[1] ? TsDN :       # broke UP through band -> flip up
         TsDN > TsSlow[1] ? TsDN :                                   # band ratchets down
         TsDN < TsSlow[1] and RsFast > TsSlow[1] ? TsUP :            # broke DOWN through band -> flip down
         TsSlow[1]

BullSignal  = crossover (RsFast, TsSlow) and RsFast < 45   # flip while still in neutral zone
BearSignal  = crossunder(RsFast, TsSlow) and RsFast > 55
```

**Mechanics.** Three nested ideas: (1) RSI(50)→EMA30 gives a slow, stable "flow position" estimate; (2) its *own* volatility (double-EMA of |ΔRSI|) sizes the bands, so the band widens exactly when the oscillator itself is twitchy — an adaptive, self-calibrating envelope, with the 4.236× fib-extension giving wide, infrequent bands; (3) the ratchet makes the envelope a *state* (it can only ratchet in the protective direction until broken — the standard SuperTrend hysteresis). The `< 45 / > 55` gate is the edge: a flip is only actionable if it happened *from* the 45–55 neutral band — i.e. a fresh flip, not the late stage of an extended swing. That converts a lagging oscillator into a **freshness-gated** mean-reversion entry.

**Why it suits a zero-wait engine.** Every component is a running EMA (O(1) register) plus one comparison per tick; the ratchet state is a single float with direction logic. The neutral-zone gate is evaluable the instant the crossover becomes true intrabar — no bar-close wait. Because RSI(50) is dominated by ~1–2 hours of 1m data, the whole state is responsive on the HFT timescale yet stable enough to avoid oscillator chatter. Three independent files carrying the identical block makes this a canonical pattern in this corpus.

### W3 · Extreme-arrest consolidation detector *(X-family)*

Compression measured as **the absence of new swing extremes** — no new 10-bar high/low for N consecutive bars — rather than ATR ratios or band containment. Third independent coil formulation after B6 W1 (ATR-ratio coil) and B6 D4 (SMA-band containment).

```
hb_ = highestbars(high, 10) == 0 ? high : na      # a new 10-bar high made THIS bar (zero-latency swing)
lb_ = lowestbars (low , 10) == 0 ? low  : na
dir := hb_ and na(lb_) ? +1 : lb_ and na(hb_) ? -1 : dir      # whichever extreme fires first

# walk back through the current same-direction leg:
for x = 0..1000 while dir == dir[x]:
    pp = running extreme (max if dir=+1 else min) of the leg's swing points

# ARREST counter:
if pp changed this bar:                        # a new same-direction extreme -> not arrested
    if consCnt > 5 and pp > condHi: breakUp = true     # box already established -> BREAK event
    if consCnt > 5 and pp < condLo: breakDn = true
    consCnt = (pp inside [condLo, condHi]) ? consCnt + 1 : 0
else:
    consCnt += 1

if consCnt >= 5:                               # 5 bars with NO new 10-bar extreme = arrested
    if consCnt == 5:  condHi, condLo = highest(high,5), lowest(low,5)   # box seeded
    else:             condHi = max(condHi, high);  condLo = min(condLo, low)   # box grows only while inside
```

**Mechanics.** A *trend* in the file's sense is a sequence of advancing 10-bar extremes; the market is **arrested** when that advance halts — the running leg extreme `pp` stops moving while price stays inside the seeded 5-bar box. The box then accretes the arrested segment's high/low (it can only grow while price remains inside), so it is exactly the consolidation range. The break of the accreted box *after* arrest is the event.

**Why it suits a zero-wait engine.** `highestbars(x,10)==0` is a running-max comparison — evaluable per tick, and it is a *zero-confirmation* swing (the 10-bar high is registered the instant it is made, unlike pivot(left,right) which needs `right` confirming bars). The detector itself is one direction flag, one integer counter, two floats: a complete compression→break machine in four registers. It is price-action-pure (no ATR, no MA), so it works identically across vol regimes without rescaling.

### W4 · Auto-period log-regression trend channel (Pearson-R² period selection) *(WaveTrend → "Adaptive Trend Finder")*

The trend's **native time scale is selected by linearity**: fit a straight line to log-price over each of 19 candidate windows; the window whose fit has the highest correlation is the current trend's period; the channel bands are ±2× the fit's residual σ.

```
for L in [20, 30, ..., 200]  (short mode)  |  [300, ..., 1200] (long mode):
    y_i = ln(price),  x_i = 1..L                      # fit ln P = int + slope·x
    slope = (L·Σxy - Σx·Σy) / (L·Σx² - (Σx)²)
    int   = mean(y) - slope·mean(x) + slope
    R²    = corr(y, ŷ)²                                # their loop: Pearson R of price vs fit progression
    σ_res = sqrt( Σ (y_i - (int + slope·x_i))² / (L-1) )   # residual std-dev of the FIT

L* = argmax_L R²(L)                                    # period selection = max linearity
midline(t) = exp(int + slope·(L* - 1) ... )            # straight line in log-space -> exp back
bands = midline × exp( ± 2.0 · σ_res )                 # devMultiplier = 2
display: CAGR = (close / close[L*])^(periods-per-year / L*) - 1
```

**Mechanics.** Log-space makes the model *return-based* (a 10% move costs the same fit-error whether price is 1 or 10,000), the line's slope is the per-bar log-return drift, and R² measures how much of the recent price action is *linear* — i.e. trend-like. A regime shift (chop) lowers R² at every period and the selected L* migrates to shorter windows; a clean trend holds at long L* with tight residual bands. The channel width is *model error*, not an arbitrary ATR multiple: it is literally "how far the last L* bars deviate from the best straight line."

**Why it suits a zero-wait engine.** Each (slope, int, R², σ) is a set of running sums (Σx, Σy, Σxy, Σx² are constants per L; only Σy, Σxy, Σy² update per bar) — 19 candidate fits cost ~19×4 float updates per bar, O(1) per tick. Period *selection by max-R²* gives the engine an endogenous time-scale estimate (use L* as the lookback for any other primitive — stops, zones, S/R — and the whole stack auto-adapts). No windowed storage beyond the longest candidate's rolling sums.

### W5 · Elliott-wave rule engine with projected completion boxes *(WaveTrend → EW module)*

A fully arithmetic Elliott counter: zigzag pivots feed a **motive-wave validator** (the classical impulse rules), then a **fib-validated ABC**, and finally a **projected completion box** whose break is a target/invalidation event.

```
zigzag: pivots(pivothigh(low, len, 1)); keep the 6 most recent swing points p1..p6
        (same-direction new extreme EXTENDS the last point; opposite direction PUSHES)

MOTIVE 1-2-3-4-5 (bull case; points L,H,L,H,L,H):
    W1 = p2.y - p1.y      (wave 1 size)
    W3 = p4.y - p3.y      (wave 3 size)
    W5 = p6.y - p5.y      (wave 5 size)
    isWave =  W3 != min(W1, W3, W5)       # rule: wave 3 is NOT the shortest of 1/3/5
             and p6.y > p4.y              # rule: top of 5 > top of 3
             and p3.y > p1.y              # rule: low of 2 stays above origin
             and p5.y > p2.y              # rule: low of 4 does not enter wave-1 territory
    (mirror for bear: inequalities flipped)

ABC CORRECTIVE (after a completed 5-wave of opposite direction):
    a = leg p3->p4,  b = p4->p5,  c = p5->p6
    diff = |fiveTop - fiveLow|             # the motive wave's full range (from wave 0 to 5)
    isValid =  c starts exactly at the 5-wave terminal
             and p6.y < fiveLow + 0.854·diff    # c-termination within 85.4% of motive range
             and p4.y < fiveLow + 0.854·diff    # b-peak likewise bounded
             and p5.y >  fiveLow                   # c begins above the 5-wave low
COMPLETION BOX:
    width  = x_c - x_a                       # the time-width of the a→c span
    box    = [c_end_x, c_end_x + width] × price [fiveLow .. bTop]
    EVENT  = price crossing the box boundary while inside the box's right bound
             -> target reached (or pattern invalidated)
"new (1)" marker: after motive+corrective complete, the next impulse start is flagged
```

**Mechanics.** The impulse rules are implemented as *exactly four comparisons* on zigzag leg sizes — no subjective counting. The fib factor 0.854 bounds corrective depth (a corrective that re-traces more than 85.4% of the motive is not a corrective — the motive is dead). The novel part is the **completion box**: the a→c time-width is projected forward from the c-termination as a bounded region where the corrective is *expected to finish* — a target zone with an explicit spatial bound and an invalidation trigger (crossing the far boundary).

**Why it suits a zero-wait engine.** Zigzags from `pivothigh(low, len, 1)` need only 1 confirming bar — near-minimal swing latency, and in a tick engine the 1-bar confirmation can be relaxed to a tick-persistence rule. The entire validator is a 6-point ring buffer plus size comparisons — O(1) state. A projected *box* (not a line) is directly executable: passive limit orders along the box's price band, with the far boundary as the hard cancel/flip level. Pattern→target pipelines that output executable geometry (not just labels) are rare in this corpus; this is the cleanest.

---

## §2 — DIRECTIONAL / TREND MATH (non-lagging)

### D1 · Linearized-WMA channel with 2·RMSE error bands *(X-family → "Auto Trendlines")*

A WMA is approximated by the straight line through its two exact endpoint values, and the channel half-width is **twice the RMSE of price against that line** — a model-fit uncertainty band.

```
a = WMA(src, n);  b = SMA(src, n)          # n = 50
A = 4b - 3a        # WMA value at the LEFT endpoint  (exact linearization identity)
B = 3a - 2b        # WMA value at the RIGHT endpoint
m = (A - B) / (n - 1)                       # per-bar slope of the linearized WMA
line_i = B + m·i                            # i = 0 (current bar) .. n-1
rmse   = 2 · sqrt( Σ_{i=0..n-1} (src[i] - line_i)² / (n - 1) )
channel = { A + rmse, B + rmse (midline, extended), B - rmse }  # i.e. line ± 2·RMSE
```

**Mechanics.** For a *linear* weighted MA the endpoint values are exact linear combinations of the WMA and SMA (4b−3a / 3a−2b) — the WMA's curvature is replaced by its chord. The band is then honest model error: "the last 50 bars sit within ±2·RMSE of the best line through the WMA's endpoints." Unlike ATR bands it measures *fit quality* — in chop the RMSE swells (bands widen, midline flattens); in a trend it tightens (bands contract, slope locks).

**Why it suits a zero-wait engine.** WMA/SMA are O(1) recurrences; the RMSE loop is O(n) once per bar (n=50) with running-sum updates per tick (Σsrc, Σsrc²). It pairs naturally with W4: W4's log-space global fit picks the *period*, D1's chord+RMSE gives a cheap *band* at that period — together they form a self-sizing trend channel.

### D2 · Ratchet ATR bands as Ichimoku basis lines *(X-family → Ichimoku section)*

Ichimoku components built from **ratcheted ATR bands** — the upper band can only ratchet *down* while price is below it, and snaps to the live band on a breakout; the basis lines are 365-bar averages of the ratcheted extremes.

```
for mult in {3, 7, 10}:                       # tenkan / kijun / senkouB roles
    up = hl2 + mult·ATR(50);  dn = hl2 - mult·ATR(50)
    upper := src[1] < upper[1] ? min(up, upper[1]) : up     # ratchet DOWN while below, snap on break
    lower := src[1] > lower[1] ? max(dn, lower[1]) : dn     # ratchet UP while above, snap on break
    os  := src > upper ? 1 : src < lower ? 0 : os[1]        # state: above / inside / below
    spt = os == 1 ? lower : upper                          # pivot = the OPPOSITE band
    max := cross(src, spt) ? max(src, max[1]) : os == 1 ? max(src, max[1]) : spt
    min := mirror
    line(mult) = (max + min) / 2                    # averaged ratcheted envelope
```

**Mechanics.** The ratchet ("hold the band until proven otherwise") is a chandelier-like memory: once price falls below the upper ATR band, that band's ceiling *freezes* (and can only descend), so the envelope remembers the pre-break high — a structural resistance with vol-scaled width, updated only on proven breaks. Averaging the ratcheted max/min over 365 bars produces smoothed basis lines (tenkan/kijun/senkouB analogues) that are less twitchy than raw donchian midlines.

**Why it suits a zero-wait engine.** Three band pairs × (2 floats + 1 int state + 1 max + 1 min) — trivial per-tick state. The ratchet semantics ("freeze until broken") is exactly what a tick engine can maintain exactly, and the frozen bands are *known price levels* — rest orders at them. The same ratchet primitive also appears in B5 M6 / B6 D3 (sticky anchors) and in this batch's D3 (oscillator ratchet bands) — see §6.

### D3 · Fixed-coefficient IIR smoother zoo + one-sided ratchet oscillator bands *(WaveTrend MA-zoo; XALGOX variant zoo; WaveTrend EWO/QQE)*

Five low-lag smoothers defined as fixed-coefficient recurrences (all O(1) per tick), plus two **one-sided ratchet bands on oscillators** (a chandelier pattern applied to oscillator space).

```
# --- Ehlers UltimateSmoother (all-pass minus high-pass; near-zero phase distortion) ---
a1 = e^(-1.414·π/L);  c2 = 2·a1·cos(1.414·π/L);  c3 = -a1²;  c1 = (1 + c2 - c3)/4
us_t = (1-c1)·x_t + (2c1-c2)·x_{t-1} - (c1+c3)·x_{t-2} + c2·us_{t-1} + c3·us_{t-2}

# --- Ehlers SuperSmoother (XALGOX v12) ---
a1 = e^(-1.414·3.14159/L);  c2 = 2·a1·cos(1.414·π/L);  c3 = -a1²;  c1 = 1 - c2 - c3
y_t = c1·(x_t + x_{t-1})/2 + c2·y_{t-1} + c3·y_{t-2}

# --- Jurik MA (3-state IIR with phase control) ---
beta = 0.45(L-1) / (0.45(L-1) + 2);  alpha = beta^power        # power = 2
e0 = (1-alpha)·x + alpha·e0[1]
e1 = (x - e0)·(1-beta) + beta·e1[1]
e2 = (e0 + pr·e1 - y[1])·(1-alpha)² + alpha²·e2[1]             # pr = 1.5 + phase/100 (50 -> 2.0)
y  = e2 + y[1]

# --- T3 (sixth-order EMA binomial blend, b = 0.7) ---
x1..x6 = chained EMA(x, L)
y = -b³x6 + (3b²+3b³)x5 + (-6b²-3b-3b³)x4 + (1+3b+b³+3b²)x3

# --- VAMA: volume-LENGTH moving average (unique) ---
v2i_t = vol_t / (meanVol_window · 0.67)          # volume as "length units"
walk back from t:  S_w += src[i]·v2i[i];  S_v += v2i[i]
stop when S_v >= L (or i == L under strict rule)
VAMA = (S_w - (S_v - L)·src[i_stop]) / L         # window always sums to L "volume units"

# --- one-sided RATCHET oscillator bands (EWO "Breaking Bands" / QQE) ---
EWO:  ewo1 = SMA(hl2,5) - SMA(hl2,34)
      UpperBand_t = ewo1 > 0 ? UpperBand_{t-1} + 0.0555·(ewo1 - UpperBand_{t-1}) : UpperBand_{t-1}
      (ratchets toward ewo1 ONLY while ewo1 > 0; freezes otherwise)
      breakout = ewo1 crossing ABOVE the frozen band          # the signal (trigger excluded per red line)
QQE:  delta = EMA(EMA(|Δ rsiMa|, 2L-1), 2L-1) · factor
      longBand_t  = rsiMa rising ? max(longBand_{t-1}, rsiMa - delta) : rsiMa - delta
      (band can only ratchet UP while the oscillator rises; flip = cross(rsiMa, opposite band))
```

**Mechanics.** The IIR group is the corpus's answer to "low-lag trend base without lookback windows": 2–6 float registers, constant multiplies, per-tick O(1). VAMA is the standout: it normalizes each bar's volume to a *length unit* and defines the MA window as "L volume-units" — quiet bars contribute little, heavy bars dominate, and the effective bar-window adapts to participation without any separate volume indicator. The ratchet oscillator bands are the same chandelier idea as D2, transplanted to oscillator space: a band that freezes against you and only relaxes in your direction, so "breaking" the band is a genuine persistence event on the oscillator.

**Why it suits a zero-wait engine.** These are the most tick-native trend bases in the entire corpus so far — no window, no sort, no pivot: a handful of registers per filter. VAMA's backward walk is bounded (cap L·10) and only runs on bar close; between closes the value is static. Ratchet bands are single-float states with one comparison — and "band frozen" is a *known price/oscillator level* you can rest monitors on.

### D4 · Composite volatility-state score with directional range imbalance *(Volatility Covenant Ribbon)*

A single score in [−100, 100] that fuses **ATR percentile** (vol regime), a **range-split-by-candle-polarity imbalance**, an EMA-spread trend term, and a location term — then classifies Expansion-Up / Expansion-Down / Compression states and launches a scaffold with a sign-flip kill switch.

```
ATR%  = percent_rank(ATR(14) over last 160 bars)                    # 0..100
bullR = EMA21( (close > open) ? (high - low) : 0 )                  # smoothed BULL range
bearR = EMA21( (close < open) ? (high - low) : 0 )                  # smoothed BEAR range
dirImb = (bullR - bearR) / ATR(14)                                  # ATR-normalized polarity split

score = clamp( (ATR% - 50)                     # vol expansion term
             + 20 · dirImb                     # directional persistence term
             + 18 · (EMA21 - EMA55) / ATR(14)  # trend-basis term
             + 16 · (close - EMA55) / ATR(14), # location term
             -100, 100 )

ExpansionUp    = ATR% >= 80 and score >= +12   (bar-close confirmed)
ExpansionDown  = ATR% >= 80 and score <= -12
Compression    = ATR% <= 25
newState = state and not state[1]                       # edge-triggered

# scaffold on new expansion event:
entry = close;  SL = entry ∓ 1.6·ATR(14);  TP1/TP2/TP3 = entry ± {1,2,3}R
KILL:  long scaffold dies when score < 0 on a confirmed bar (composite flips sign)
```

**Mechanics.** The distinctive statistic is `dirImb`: the 21-bar EMA of *range*, separated by candle polarity. A market where bullish candles are systematically wider than bearish candles is *persistently* directional — this measures that directly, in ATR units, with no price cross involved. The composite is a weighted sum of four non-correlated vol/structure terms, each ATR-normalized (scale-free), and the ±12 threshold on a vol-expanded bar is a genuine state transition (vol expansion *plus* directional persistence *plus* location).

**Why it suits a zero-wait engine.** All four terms are O(1) recurrences (percentile = a 160-slot running count or histogram bucket; the two polarity-ranged EMAs are two EMA registers with a candle-color gate). The score is a 4-term dot product per tick. Expansion events are edge-triggered states — in a tick engine the *edge* fires the instant the conditions first hold, and the sign-flip kill is a single comparison that can terminate the position intrabar (the file's bar-close confirmation is conservative).

---

## §3 — MARKET MICROSTRUCTURE

### M1 · Fib-buffered MSB + origin-candle OB + BB/MB block lifecycle *(X-family → SMC module)*

Structure breaks gated by a **minimum break size** (a fraction of the preceding leg), order blocks from the leg's origin candle, and a second block type from the pre-break window.

```
zigzag_len = 9
to_up = high >= highest(9);  to_down = low <= lowest(9)
trend flips on whichever breaks; on flip, record the PREVIOUS leg's extreme:
    bull flip: low_val = lowest(low, barsSince(prev to_up))      # the low the up-leg started from
    bear flip: high_val = highest(high, barsSince(prev to_down))

h0,h1 = two most recent swing highs (value, bar-index);  l0,l1 = two most recent swing lows

MSB (market state) flip with FIB BUFFER (fib_factor = 0.33):
    bull -> bear:  l0 < l1  and  l0 < l1 - |h0 - l1| · 0.33
    bear -> bull:  h0 > h1  and  h0 > h1 + |h1 - l0| · 0.33
    (a new swing must undercut/overrun the previous swing by >= 33% of the prior leg size;
     otherwise it is treated as noise, not a break)

ORIGIN OB:   Bu-OB = last BEARISH candle scanned between h1i and l0i (the up-leg's origin)
             Be-OB = last BULLISH candle scanned between l1i and h0i
BB/MB BLOCK: last bearish candle in the PRE-BREAK window [h1i - 9 .. l1i]
             labelled "BB" (new-low leg) if l0 < l1 else "MB" (mitigated block)

lifecycle per zone:  close beyond FAR edge -> delete
                     close inside zone    -> "price in zone" event (resting-limit signal)
                     otherwise            -> extend right
```

**Mechanics.** The fib buffer is the new parameter in the corpus's MSB family: a break that doesn't exceed 33% of the preceding leg is *not* a structure break — it filters out the whipsaw breaks that consume the standard pivot-based MSB (xref B6 M1/M2). The origin OB is the B6 M2 primitive again (last opposite-color candle of the leg), now paired with a **BB/MB distinction**: the block at the new-extreme leg (BB — the actual origin of the break) vs the block at the prior leg (MB — previously mitigated, weaker interest). Two block types with different validity gives the engine a priority order for retest targets.

**Why it suits a zero-wait engine.** The 9-bar donchian break (`high >= highest(9)`) is a running-max comparison — zero confirmation latency; the 33% buffer is one extra comparison at break time; the origin scan is a bounded O(leg) backward walk that runs once per structure event (≤ 18 bars); zone lifecycle is per-zone (top, bot, type) with two comparison events. All state is integer/float registers — no bar-close waits anywhere in the chain.

### M2 · Zero-latency swing feed + fib next-level state machine *(WaveTrend → AutoFib Trend Scouter)*

Swings detected by **"a new N-bar extreme made right now"** (no confirming-bar delay), buffered in a 7-coordinate deque, with each fib level carrying a 6-state machine and the engine publishing *next support / next resistance*.

```
# zero-latency swing: current bar IS the N-bar extreme (vs pivot(L,R) which needs R bars after)
newHigh = highestbars(src, 21) == 0 ? src : na
newLow  = lowestbars (src, 21) == 0 ? src : na
dir flips to +1 on newHigh (absent simultaneous newLow), -1 on newLow

# 7-coordinate deque (value, time, price-at-confirmation) per scale:
on dir change:  push (extreme, time, price)
while dir holds: if a NEW same-direction extreme: replace slot 0

# fib ladder from the deque's min/max:
levels = { 0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0 } · (H - L) + L     (direction-aware)
dir = sign(t_max - t_min)

# per-level state machine (relative to close and neighbors prev/this/next):
0 = source actively moving up      1 = far resistance (or crossed)
2 = NEXT resistance                3 = NEXT support
4 = far support                    5 = source actively moving down

nextUp   = index of first level in state 2     # the nearest resistance
nextDown = index of first level in state 3     # the nearest support
publish: next levels always; far levels within N steps
```

**Mechanics.** Two primitives. First: `highestbars(x, N) == 0` is a **real-time swing** — the N-bar high is registered the instant it is printed, with zero bars of confirmation latency (the corpus's standard `pivot(left, right)` swings wait `right` bars; here the delay is 0). Second: each fib level is not just a price but a *state* (is it the next target up? already crossed? far?) — a 7-element comparison table that answers "what is the next level in each direction" in O(7).

**Why it suits a zero-wait engine.** The swing feed is a running max/min over 21 bars — one comparison per tick, and it *is* the event (no confirmation). The deque is 21 floats. The level state machine is 7×(3 comparisons) per tick. Together they give the engine a live, always-fresh S/R ladder with explicit next-target semantics — the natural input for passive order placement (rest limits at `nextUp`/`nextDown`, cancel on state change).

---

## §4 — DYNAMIC RISK

### R1 · Percentage TP-ladder state machine with scalp-front / runner-tail geometry *(XALGOX)*

Exits defined as **percent-of-price** levels with a staged-quantity ladder and a single float that *is* the exit stage:

```
levels (percent of entry price):
    SL  = 0.5%     TP1 = 0.2% (exit 80% qty)     TP2 = 0.5% (10%)     TP3 = 7.0% (2%)
geometry in R:   R = 0.5%  ->  TP1 = 0.4R,  TP2 = 1.0R,  TP3 = 14.0R

stage: condition float in {0, ±1.0, ±1.1, ±1.2, ±1.3}
    0        -> flat
    ±1.0     -> entry (body-momentum trigger; excluded class, see red-line table)
    ±1.1     -> TP1 touched (80% exited, 20% continues)
    ±1.2     -> TP2 touched (10% exited)
    ±1.3     -> TP3 touched (full close)
    any >= ±1.0 and SL touched -> 0
    opposite trigger while in position -> 0 (early exit on regime flip)
orders: process_on_close, pyramiding 0, size = 1% equity (spot)
```

**Mechanics.** A two-phase geometry in one ladder: the **front** (90% of volume) is win-rate-first — TP1 at 0.4R is deliberately *inside* the stop distance (xref B6 R5); the **tail** (2% of volume) is a regime-runner with a 14R target — a 7% move against a 0.5% stop. The `condition` float is a clean, portable exit-stage machine: one variable fully describes the trade's phase, and every exit action is a stage transition. The early-exit rule (opposite trigger closes) is a regime-flip invalidation layered on top of the ladders.

**Why it suits a zero-wait engine.** The stage machine is a single float with a 12-case transition table — trivially portable. Percent-of-price levels are computed at entry and never change (static standing orders). The 80/10/2 quantity split is an explicit expected-value posture the engine can A/B against the B6 R5/R6 ladders on the same entry stream.

### R2 · Oscillator-saturation TP ladder + 5-bar micro-stop *(X-family → TP labels / SL cross)*

Take profits defined at **momentum saturation** (RSI extreme crossings) instead of fixed R multiples, with strict sequential gating; stops defined at recent micro-structure.

```
LONG ladder (each must be the FIRST crossing of its level since entry):
    TP1 = RSI(14) crosses 70
    TP2 = RSI(14) crosses 75   (only valid after TP1 has crossed within this trade)
    TP3 = RSI(14) crosses 80   (only valid after TP2)
SHORT ladder: 30 / 25 / 20 (mirror)
gating: tp2 requires barssince(tp1_cross) <= barsSinceEntry; tp3 likewise after tp2

SL detection (alert logic, kept):
    X/Xpert:  long SL = low < lowest(low, 5) with low[1] >= that low     # 5-bar micro-structure stop
    ZZ variant: SL = cross of the trailing stop (2.2·ATR(14) ratchet, xref B6 R2 family)
```

**Mechanics.** The TP ladder is *adaptive in price space*: in a fast trend RSI-80 sits far from entry (big target), in chop it sits close (quick exit) — the target auto-scales with momentum, which fixed R ladders cannot do. The sequential gating (TP2 only after TP1, TP3 only after TP2, all relative to entry time) guarantees the ladder is consumed in order and prevents stale crossings from before entry from firing. The 5-bar micro-stop is a structural stop at the most recent 5-bar extreme — tighter than any ATR multiple in fast tape, and it is the *exact* price an HFT engine would use (a standing order at the 5-bar low).

**Why it suits a zero-wait engine.** RSI(14) is an O(1) Wilder recurrence; the three level-crossings are comparisons per tick; the sequential gate is three barssince counters. The 5-bar stop is a running min/max — a known price every tick. Occurred in three files (X, Xpert, ZZ) = canonical for this codebase family (xref B4 R4 RSI-ladder TP — third corpus occurrence).

---

## §5 — CONFLUENCE / SCORING

### S1 · S/D zone engine + % -of-range S/R clustering *(XALGOX)*

Third and fourth corpus copies of the zone/cluster family (xref B6 M8 / B6 S3) — recorded for the parameter set:

```
S/D zones:
    pivots 10/10 (pivothigh/pivotlow)
    box = pivot ∓ ATR(50) · (2.5/10)               # 0.25·ATR50 box width
    dedup: reject if |newPOI - existingPOI| <= 2·ATR(50)   (midpoint distance)
    history: keep 20 zones per side
    break: close beyond outer edge -> zone deleted, replaced by BOS LINE at zone midpoint

S/R clustering:
    pivots 10/10; scan last 284 bars, at most 40 pivots
    touch window = ± 10% of the 284-bar high-low range   # % -of-range clustering (vs B6 S3's TR·1/30)
    strength = touch count >= 2; keep first 21 qualifying levels
    extreme levels: highest/lowest pivot in window
    zone width = 2% of the 300-bar range
```

**Why it suits a zero-wait engine.** Same port as B6 M8/S3: pivot events + per-level touch counters with hysteresis + ATR-scaled dedup. The 10%-of-284-range touch window is another scale-free variant (the corpus now has two: % of long-range — XALGOX/X-family S/R — and TR·(1/30) local-noise — B6 S3); the tick engine can run both and let the level set be their union.

### S2 · X-family regime-gate toolkit *(X / Xpert / ZZ)*

The trigger itself is excluded (ST cross + MACD confluence, red line 2); the surrounding **filter stack** is retained as a confluence toolkit — every element is an O(1) running state:

```
MTF side:    close > EMA(200) at each of 5m / 15m / 30m / 1h / 4h
             (non-repaint fetch: HTF = gaps_off + lookahead_off  [X/Xpert — confirmed]
                                       + lookahead_on             [ZZ variant — live-forming, flag];
              LTF = request.security_lower_tf + pop() of last completed LTF value — clean)
TVR gate:    TVR < 15 = no-trend, 15-25 = ranging, > 25 = trending   (DMI-based; usable as trade gate)
vol gauge:   atrr = 3·ATR(10); env = SMA20(atrr) ± 2·STDEV20(atrr)
             percentVol = 30 + 40·(atrr - bottom) / (top - bottom)    # 30-70% gauge, mid = 50
RVOL:        "institutional activity" = volume > 1.44 · RMA(volume, 21)
tension:     ADX > 20 (consistency gate);  EMA150 vs EMA250 (regime);  EMA9 slope (pressure)
```

**Mechanics.** Each gate answers one question (what side on each timeframe / is there a trend / where in its own vol envelope / is participation elevated / is the move consistent) from an independent statistic family — the standard non-correlated-factor construction. The vol gauge is a nice self-normalizing construct: the ATR measured *inside its own ±2σ envelope* gives a 0-100 (here 30-70) "vol temperature" that needs no external calibration.

**Why it suits a zero-wait engine.** MTF states are five booleans refreshed at HTF bar-close events (in-process resample of the 1m feed — port note); TVR/ADX are O(1) Wilder recurrences; the vol gauge is a running mean+stdev of 3·ATR10; RVOL is a ratio of two running sums. As a *gate stack* (AND of regime conditions) applied to whatever microstructure trigger the engine uses (W1/W2/W3/M1/M2), it is pure state inspection per tick.

---

## §6 — Delta over batch 6 (what B7 adds)

1. **First ML-style classifier in the corpus (W1).** An online Naive Bayes with running Gaussian accumulators and an explicit *diverged* (no-trade) class — probabilistic signal grading replaces threshold crossings; O(1) per tick, self-supervised per symbol. The self-audit (1-bar-ahead hit rate) is a built-in regime-drift monitor.
2. **"Ratchet band" is now a corpus family** — appearing on price (SuperTrend, D2 ratchet-ATR Ichimoku, B5 M6/B6 D3 sticky anchors) *and on oscillators* (W2 RSI-SuperTrend, D3 EWO/QQE one-sided bands). Canonical primitive: a band that freezes against you, ratchets in your direction, and flips only on a proven break — a persistence test in one float.
3. **Compression/coil detection now has 4 independent formulations**: B6 W1 (ATR-ratio + violation tolerance), B6 D4 (SMA-band containment), B7 W3 (extreme-arrest: no new swing for N bars), B1 squeeze (BB-in-KC). The template is stable: `compressed AND bounded-age AND break → event`; W3's pure-price-action version is the cheapest to run.
4. **Auto-timescale trend detection (W4 + D1).** Model-fit channels: period selected by argmax R² over candidate log-regressions; band width = 2× residual RMSE (or the WMA-chord RMSE). The corpus's trend filters just stopped using fixed periods — the model picks its own timescale.
5. **Pattern → executable geometry (W5).** First file that outputs a *projected target box with an invalidation trigger* (Elliott completion box) instead of a level or a label. The 4-comparison impulse validator is a reusable pattern gate.
6. **Zero-latency swing feed (M2).** `highestbars(x,N)==0` as a real-time swing (0 confirming bars) vs the corpus-standard pivot(left,right) (right confirming bars) — a distinct, faster primitive for tick engines; combined with a 7-coordinate deque and per-level state machines ("next support/resistance" queries).
7. **Fib-buffered MSB (M1).** A *minimum break size* gate on structure breaks (33% of prior leg) — the noise filter the B6 MSB family lacked; plus BB/MB block typing (new-extreme-leg block vs pre-break block).
8. **Ehlers fixed-coefficient IIR zoo (D3).** UltimateSmoother / SuperSmoother / JMA / T3 / VAMA — 2–6-register O(1) smoothers; VAMA (volume-length MA) is unique to the corpus.
9. **Two-phase exit geometry (R1).** The scalp-front (TP1 at 0.4R, 80% qty) / runner-tail (TP3 at 14R, 2% qty) ladder in one state machine — extends B6 R5 (win-rate-first) with an explicit trend-runner tail.

---

## Appendix A — Full exclusion list (B7)

**GUI/visual (red line 3):** all plot/plotshape/plotchar/plotcandle/barcolor/bgcolor/line/label/box/fill/table code across all 9 files; X-family Smart Panel (MTF cells, Market State, Volatility, Institutional Activity, Session, Trend Pressure), VCR dashboard, WaveTrend EW wave-labels/boxes/fib lines/zz lines, XALGOX entry/SL/TP line+label queues, all color palettes and transparency settings; all Telegram cells (`@simpleforextools`, `@mrexpert_ai`); all alertcondition wiring (logic conditions kept where extracted: W1 entries, W3 breaks, M1 zone events, R2 SL/TP crosses).

**Lagging-trigger exclusions (red line 2):** WaveTrend oscillator cross/threshold signals (WT ±60/±75/±125, midline crosses); XTL double-CCI ±37 crosses; EWO / EWO2 MA-diff and signal crosses; X-family SuperTrend cross + MACD/EMA150-250/HMA55/ADX confluence trigger (the *stack's filters* kept as S2); QQE crosses (ratchet-band math kept as D3); XALGOX ALMA(50) close-vs-open cross (50-period lagging; close-vs-open *concept* xref B6 D1); squeeze-release arrows as triggers (xref B1, display only).

**Repaint/lookahead flags (red line 1):** WaveTrend HTF EMA(13)×3 levels (live-forming via unindexed `gaps_off+lookahead_on` — port to confirmed HTF bar-close events); ZZ-variant `securityNoRep` HTF branch (live-forming — the X/Xpert version's `lookahead_off` branch is clean); XALGOX `reso()` HTF body-momentum resample (live-forming — port to confirmed values); X-family `cond(_offset)` MTF module uses `[1]` shift in realtime (confirmed idiom — *salvageable as-is*); XALGOX Heikin-Ashi source via same-TF `lookahead_off` security (confirmed idiom — clean).

**Structure notes (kept as observations, not extracted):** X-family trap detector (5-bar centered fractal `src[4]<src[2], src[3]<src[2], src[2]>src[1], src[2]>src[0]` on the WaveTrend-2 line with `d = EMA(|src−esa|)` adaptive denominator; price-new-extreme + oscillator-lower-extreme divergence, two tiers at 10/−35 and 40/−70 — xref B5 D2 divergence family, the WT-variant denominator noted); WaveTrend 4-type pivot divergence engine (left/right 15/10, range 5-100, `barstate.ishistory or isconfirmed` non-repaint gate — xref B5 D2); WaveTrend MFI blend histogram (0.5·MFI(L/1.33) + 0.5·MFI(L·1.33) → SMA2 → `sign(t)·|t|^0.75` power transform — amplitude-boosting nonlinearity, display); XALGOX Heikin-Ashi option; X-family buySetup/sellSetup 13-bar close<close[4] coloring (display); XALGOX Keltner multipliers 10.5/9.5/8/3 (display scaffolds); WaveTrend Gann/EWO display elements; ZZ Kumo fill (display of the D2 ratchet-Ichimoku).

---

## Appendix B — Porting notes for a zero-wait tick engine (Binance Spot, 1m klines + aggTrade + bookTicker)

| Primitive | Tick-engine realization |
|---|---|
| W1 NB classifier | per symbol: 9 class-accumulators (3×(n,Σ,Σ²) per feature), 3 sliding z-windows (running Σ/Σ² over 50), 3 PDF evaluations. CVD from aggTrade taker flag (exact) or wick-split (bar-accurate). Posterior per tick; size ∝ probability; warmup = 100 labeled bars. Self-audit = 2 counters. |
| W2 RSI-SuperTrend | RSI50 (Wilder register) → EMA30 → |Δ| → EMA50 → EMA50; one ratchet float; flip + neutral-band check per tick. |
| W3 extreme-arrest | running 10-bar max/min (zero-latency swing), 1 dir flag, 1 integer counter, 2 box floats. Break = comparison vs box. |
| W4 auto-period channel | 19 sets of running sums (Σy, Σxy, Σy² per L; Σx, Σx² constant); argmax R² over 19; exp() back; bands ×exp(±2σ_res). Recompute on each 1m close; static between closes. |
| W5 EW engine | 6-point zigzag ring buffer from 1-confirming pivots (or tick-persistence swings); 4-comparison impulse validator; ABC fib check (0.854); completion box = (x_c − x_a) width × [fiveLow, bTop]; boundary-cross = event. |
| D1 RMSE channel | WMA+SMA registers; A=4b−3a, B=3a−2b; O(n) residual sum per bar (n=50) or running-sum O(1) per tick. |
| D2 ratchet Ichimoku | 3 band pairs × (2 floats + state int + max + min) over 365-bar averages; frozen bands are rest-order prices. |
| D3 IIR zoo | fixed coefficients precomputed per L; 2–6 float registers per filter, per tick. VAMA: backward walk bounded by L·10 on bar close. Ratchet oscillator bands: 1 float + comparison each. |
| D4 vol-state score | 160-slot percentile (histogram or running count), 2 polarity-gated EMA registers, EMA21/55, 4-term dot product per tick; edge-triggered states; sign-flip kill per tick. |
| M1 fib-buffer MSB | 9-bar running max/min; 2×2 swing point buffer; break + 33% buffer comparison; bounded origin scan per event; per-zone (top,bot,type) with 2 lifecycle comparisons. |
| M2 swing feed + fib states | 21-bar running max/min (zero-latency swings); 21-float deque; 7-level state table (O(7) comparisons/tick); nextUp/nextDown = first state-2 / state-3 index. |
| R1 stage machine | 1 float, 12-case transition table; static % levels as standing orders at entry; 80/10/2 quantity split; opposite-trigger early exit. |
| R2 oscillator TP | RSI14 register; 3 level-cross comparisons; 3 barssince counters for sequential gating; SL = running 5-bar min/max (standing order). |
| S1 zones/clusters | pivot events + touch counters with hysteresis; ATR50·0.25 boxes; 2·ATR50 dedup; 10%-of-284-range window; break→line-at-midpoint. |
| S2 gate stack | 5 MTF booleans at HTF close events (in-process resample); TVR/ADX Wilder registers; vol gauge = running mean+stdev of 3·ATR10; RVOL = 2 running sums; AND-gate per tick. |

**General port rules (re-stated, confirmed by B7):** (1) anything from `request.security` becomes an in-process resample of the 1m feed, evaluated on *confirmed* HTF bars — the ZZ-variant `lookahead_on` unindexed fetches and XALGOX `reso()` must be re-derived from confirmed values; (2) "close" in a trigger reads as price persistence beyond a level — tick engines get strictly earlier signal from the same condition (W2's flip, W3's break, M1's MSB all qualify); (3) every box/box-projection in these files (W5 completion box, M1 zones, W3 arrest box) is a *resting order zone* with a known cancel/flip boundary; (4) ATR-normalization (D4, M1 buffer, S1 dedup) keeps all thresholds scale-free across symbols; (5) the running-accumulator pattern (W1's sums, D3's registers, S2's gates) is the batch's core porting insight — **every flagship in this batch is expressible as O(1) registers + comparisons**, i.e. the entire batch's logic sits inside the per-tick budget of a tick-based engine.

**B7 totals:** 9 files (6 unique codebases) → **15 concepts** (W1–W5, D1–D4, M1–M2, R1–R2, S1–S2) + 9 cross-referenced rows. Running corpus across B1–B7: 245 concepts / 129 files (126 unique).
