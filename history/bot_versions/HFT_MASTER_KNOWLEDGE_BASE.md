# MASTER KNOWLEDGE BASE — Zero-Wait Tick Execution Edge Library

**Consolidated from:** 7 extraction batches · 129 source files (126 unique codebases) · ~245 raw concepts → **68 deduplicated master entries**.
**Target engine:** Binance Spot HFT — 1m klines + `aggTrade` + `bookTicker`, event-driven, sub-50µs fast path.
**Method:** overlapping concepts merged into a single canonical (most optimized) version; every entry keeps the exact Python pseudo-code / closed-form math and a compressed technical justification for zero-wait, tick-based execution.

---

## 0.1 CONSOLIDATION & DEDUPLICATION MAP (major merges)

| Merged family | Originating batches/entries | Canonical home |
|---|---|---|
| Log-linear argmax-R² adaptive channel | B2 §1.1 ≡ B7 W4 (+ WMA-chord RMSE B7 D1, OLS channels B4 D4 / B3-IFT) | §1.3 |
| Oscillator-space SuperTrend ratchet | B1 §1.4 (TrendShift) ≡ B4 W3 ≡ B7 W2; QQE ratchets B1 §2.8 / B4 W6 | §1.10 |
| Recursive Gaussian IIR + filter library | B1 §2.5 ≡ B2 §1.12 ≡ B6 W5; filter zoo B7 D3, B2 App-A | §1.5 |
| Smoothed range filter (multi-scale) | B1 §1.6 ≡ B3 §2.3 ≡ B3 §2.2 (sens-consensus) | §1.6 |
| Instantaneous-range SuperTrend | B1 §1.7 ≡ B3 §2.7 | §1.7 |
| EMA stack / positional classifiers | B1 §2.6 ≡ B2 §2.1 ≡ B4 D1 ≡ B3 §1.8 | §1.11 |
| Bar-drift close-vs-open cross | B1 §2.3 ≡ B4 D5 ≡ B6 D1 (+ open-lead variant B5 D1) | §1.14 |
| MTF voting / confirmed-HTF idiom | B2 §2.4 ≡ B3 §2.1 ≡ B4 S5 ≡ B6/B7 port rules | §1.15 |
| Volume profiles (all binning schemes) | B2 §3.2/§3.10 ≡ B4 M7 ≡ B5 W2 ≡ B6 S4 | §1.18 |
| Premium/discount + frozen fib arrays | B2 §3.6 ≡ B3 §3.8 (OTE) ≡ B4 D3 (PVP) | §1.19 |
| Compression/coil detectors (5 variants) | B2 §1.9 ≡ B2 §1.4 ≡ B6 W1 ≡ B6 D4 ≡ B7 W3 | §1.22 |
| Sticky regime anchors | B1 §1.5 ≡ B5 M6 ≡ B6 D3 | §1.24 |
| Structure-shift FSMs (BOS/CHoCH/MSS) | B1 §3.1 ≡ B3 §2.4/§2.5 ≡ B6 D2/M1/M2/M7 ≡ B7 M1 | §2.1 |
| Sweep / SFP / EQ-level engines | B1 §1.12/§3.5 ≡ B3 §3.6/§3.11 ≡ B4 M4/M8 ≡ B5 M5 ≡ B6 M6 | §2.2 |
| FVG / imbalance lifecycle | B1 §3.4/§3.7 ≡ B2 §3.9 ≡ B3 §3.3/§3.4/§3.5 ≡ B5 W3/M8 ≡ B6 M5 | §2.3 |
| Order-block taxonomy & lifecycle | B1 §1.9/§3.2/§3.3 ≡ B2 §3.3 ≡ B3 §3.1/§3.2 ≡ B4 M1/M2/M3 ≡ B5 M2/M3/W4/W8 ≡ B6 M2/M3/M4 ≡ B7 M1 | §2.4 |
| ATR-scaled S/D zone registries (POI dedup, polarity flip, break-to-line, false-break trap) | B2 §3.4 ≡ B4 M5/M6 ≡ B6 M8 ≡ B7 S1 | §2.4C + §3.7 + §3.8 |
| Trailing-stop ratchet family | B1 §4.3 ≡ B3 §2.6 ≡ B6 R2/R4 ≡ B4 R5 ≡ B5 R2 | §3.2 |
| %-stage exit machines (80/10/2) | B2 §4.5 ≡ B4 D5 ≡ B7 R1 | §3.4 |
| RSI-extreme TP ladders (5 sources) | B1 §4.7, B3 §4.3, B4 R4, B6 R5-adjacent, B7 R2 | **excluded** → substituted, see Appendix A |
| Oscillator-crossover graders/votes | B2 §5.2, B5 D6/S5, B6 S2-vote, B7 MACDV | **excluded/substituted**, see Appendix A |

## 0.2 TICK-ENGINE CONVENTIONS (binding for every entry)

1. **SLOW STATE vs FAST PATH.** Anything computable from closed 1m bars is *slow state* (refreshed on kline close). Anything on the live trade print is *fast path*. Signals that depend on bar-close facts commit on kline close; everything else fires on the tick.
2. **Confirmed-HTF rule.** Every higher-timeframe quantity is the value of the **last closed** bar of that TF, obtained by in-process resampling of the 1m feed. Forming-HTF values are never read. This is the only legitimate MTF semantics in this document.
3. **Break semantics.** "break of level L" = the first aggTrade (or mid) print crossing L. "Confirmed break" = the 1m kline *close* beyond L. "Price persists beyond L" = a tick-count/dwell threshold — the tick-native substitute for close-confirmation when lower latency is required.
4. **Pivot policy.** Confirmed pivots (left/right window complete) define *levels* and never re-classify. Forming/zero-latancy swings (running-extreme tests) are used only as *gates* and are updated in place.
5. **Native delta rule.** Wherever a source used a close/open-sign volume proxy, the engine substitutes true signed flow: `delta_tick = +q if isBuyerMaker == False else -q` per aggTrade; bar and cumulative deltas are running sums of it. The close-location-value (CLV) split `V·(C−L)/(H−L)` is retained only as kline-replay fallback.
6. **Bounded memory.** Every registry (zones, pools, lines, profiles) carries a hard FIFO cap + TTL (master table in Appendix C).

**Notation:** `x[k]` = value of series x k bars ago (`x[0]` = current closed bar unless marked *live*); `ATR(n)`, `EMA`, `SMA`, `WMA`, `RMA` = standard recurrences; `rolling_max/min(src,n)`; `cross_up(a,b) ≡ a > b and a[1] <= b[1]`; `is_new_high(src,N) ≡ argmax(src, N) == 0` (the extreme is printing *now*); `cumsum` = running sum; `R` = |entry − SL|; all state O(1) per tick unless stated.

---
---

# SECTION 1 — MACRO-FILTERS & REGIME DETECTION

*Single-purpose layer: direction permission, regime classification, fair-value surfaces, compression states, no-trade gates. Nothing in this section is an entry trigger; it sets the side, the size multiplier, and the kill flags consumed by Sections 2–4.*

---

## 1.1 Quantized Epsilon-Midpoint Hysteresis Band ("stepped Keltner state machine")
`sources: B1 §1.1 (AI SWING)`

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

**Mechanics:** Hysteresis band that quantizes trend state into ATR-spaced steps. Direction only changes when price pays a full `ε` to displace the state — structurally rejects chop (in a range, price oscillates inside `m±ε` and no step occurs). Using the *previous* bar's band edges is a lookback-free hysteresis that prevents same-tick flip-flops.
**Zero-wait value:** All state is O(1) per tick — compare live price against two frozen numbers (`m±ε` from the last closed bar). No indicator recomputation; the step event itself is the signal, firing at the breakout tick.

---

## 1.2 Anchored Powered KAMA with Online (Welford) σ Bands
`sources: B1 §2.1 (AI Vanga / LuxAlgo variant)`

```python
# anchor = session boundary
on_new_session:  counter = 1; kama = price; welford = 0
per bar/tick:
    counter += 1
    ER = abs(price - price_anchor) / sum(|price - price_prev| since anchor)  # efficiency ratio
    SC = ER ** 2                                 # "powered" (power=2)
    kama = SC * price + (1 - SC) * kama_prev
    welford += (price - kama_prev) * (price - kama)      # online sum of squared deviation
    sigma = sqrt(welford / counter)
bands: kama ± σ (inner), kama ± 2σ (outer)
```

**Mechanics:** KAMA's smoothing constant is the efficiency ratio (net move / total path since anchor) squared: ER≈1 in clean trend → KAMA tracks ~1:1 (zero lag); ER≈0 in chop → KAMA freezes (zero noise). The Welford accumulator yields a running σ of deviation-from-KAMA — the filter's own confidence interval, O(1), no window storage. Session anchoring measures "efficiency of today's move" — the correct regime question for a scalper.
**Zero-wait value:** Four scalar accumulators total (counter, Σ|Δp|, welford, kama). Direction = `sign(price − kama)`, strength = `|price − kama|/σ` — the canonical streaming regime scalar.

---

## 1.3 Model-Fit Regression Channels (adaptive period by linearity)
`sources: B2 §1.1 ≡ B7 W4 (Adaptive Trend Finder); B7 D1 (WMA-chord RMSE); B4 D4 (OLS retest)`

**(a) Log-linear Pearson-R channel — the most rigorous macro regime primitive in the corpus.** For each candidate window, fit a line to log-price; keep the window with the highest correlation:

```python
# SLOW STATE — recompute every 5 bars; each fit O(L) via rolling moments
candidate_short = [20, 30, ..., 200]        # 19 windows, step 10
candidate_long  = [300, 350, ..., 1200]     # 19 windows, step 50

def loglin(y):            # y = ln(close) over last L bars, x = 1..L
    n = len(y)
    slope, intercept = ols(x=1..n, y)
    resid = y - (intercept + slope * x)
    sigma = sqrt(sum(resid**2) / (n - 1))       # residual stdev in LOG space
    R     = pearson(y, intercept + slope * x)   # trend "purity", |R| <= 1
    return slope, intercept, sigma, R

best = argmax_R over all candidate windows          # period selection = max linearity
M_now  = exp(intercept*)                            # midline at current bar
upper  = M_now * exp(dev * sigma*);  lower = M_now * exp(-dev * sigma*)   # dev = 2.0
direction  = sign(slope*)
confidence = bucket(|R*|): <0.2 ExtremelyWeak … 0.94 Strong, 0.96 VeryStrong,
              0.98 ExceptionallyStrong, else UltraStrong
# freeze (L*, slope, intercept, σ) between re-evaluations; per-tick midline projection:
M_tick = exp(intercept* + slope* * t)
```

**Mechanics:** A log-linear fit is a constant compound-growth-rate model; Pearson-R against the fit measures how purely exponential the recent path has been. `argmax_R` is a change-point-free adaptive timescale — the detector answers "how long has this trend been running." Residual σ in log space is *relative* volatility, so the ±2σ channel auto-scales with price level. Unique output: an explicit confidence scalar for sizing.
**Zero-wait value:** Maintain rolling Σy, Σxy, Σy² per window (Σx, Σx² are constants) — ~19×3 float updates per bar, argmax every 5 bars (<1 ms). Fast path receives four frozen numbers; "price crosses projected midline/edge" is one comparison per tick.

**(b) WMA-chord ± 2·RMSE channel (cheap band at any period):**

```python
a = WMA(src, n); b = SMA(src, n)          # n = 50
A = 4*b - 3*a        # exact WMA value at LEFT endpoint (linearization identity)
B = 3*a - 2*b        # exact WMA value at RIGHT endpoint
m = (A - B) / (n - 1)
line_i = B + m*i                              # i = 0..n-1
rmse = 2 * sqrt( sum_{i=0..n-1}(src[i] - line_i)**2 / (n - 1) )
channel = line ± rmse      # band width = honest model-fit error, not an ATR multiple
```

**(c) OLS(200) retest mode:** `long = channel_dir == +1 and close < lower` (retest below the 1σ edge of a rising 200-bar fit), gated by zone context — the mean-reversion usage of the same fit. Pairs with (a): (a) picks the period, (b) bands it.

---

## 1.4 Kalman-Smoother Trend Stack (KHST) + Per-Class Presets
`sources: B3 §1.4 (Beluga KHST), preset table B3 §5.8`

```python
def kalman(x, R, Q, state):              # 1-D smoother: 4 float ops per update
    est, err = state
    pred_err = err + Q
    K = pred_err / (pred_err + R)
    est = est + K * (x - est)
    err = (1.0 - K) * pred_err
    return est, (est, err)

def khma(src, R, Q):                     # DEMA-style combo of two Kalman passes, re-smoothed
    a = kalman1d(src, R/2.0, Q)          # fast pass
    b = kalman1d(src, R,     Q)          # slow pass
    return kalman1d(2*a - b, sqrt(R), Q)

khma = khma(close, R=10.0, Q=0.010)
direction, stline = supertrend_ratchet(khma, ATR_len=12, factor=1.7)   # ratchet on SMOOTHED price
```

```python
# per-asset-class preset tuple (R, Q, ATRlen, ST factor, entry/TP1/TP2/SL ATR mults,
#                              adx_min, early-flip thresh, adx-slope thresh)
GOLD:  R=10.0 Q=0.010 ATR=12 f=1.60  e/t1/t2/sl = 0.60/1.00/1.70/1.20  adx>=16 ef=0.10 slope>=0.25
US100: R=12.0 Q=0.012 ATR=14 f=1.70  0.60/1.00/1.80/1.30               adx>=18 ef=0.12 slope>=0.35
US30:  R=14.0 Q=0.015 ATR=14 f=1.80  0.70/1.10/2.00/1.40               adx>=18 ef=0.14 slope>=0.45
FX:    R=16.0 Q=0.020 ATR=12 f=1.50  0.50/0.90/1.50/1.10               adx>=15 ef=0.08 slope>=0.25
```

**Mechanics:** R = trust in the raw tick (large R → heavy smoothing), Q = allowed drift of the underlying. The gain K adapts every bar: sharp tracking during displacement, flat in chop — exactly the source a ratcheted band wants (fewer whipsaw flips in ranges, faster flips in real moves). The R/Q pair subsumes the "length" parameter of every MA in this document; the preset table makes parameters *data, not code* — one dict per symbol class, every module reads from it.
**Zero-wait value:** Runs natively on the forming close (last aggTrade price) — trend state is continuous; only the committed flip is defined on the confirmed close.

---

## 1.5 Recursive Gaussian IIR Trend (+ Linreg Flattening) & Low-Lag Filter Library
`sources: B1 §2.5 ≡ B2 §1.12 ≡ B6 W5 (two variants); filter zoo: B1 §2.5-companions, B7 D3, B2 App-A`

```python
freq = 2*pi/15
factorB = (1 - cos(freq)) / (1.414**(2/3) - 1)
alpha  = -factorB + sqrt(factorB**2 + 2*factorB)
# 3rd-order cascaded Gaussian (IIR, binomial coefficients):
y1 = alpha*x + (1-alpha)*y1'
y2 = alpha**2*x + 2*(1-alpha)*y2' - (1-alpha)**2*y2''
y3 = alpha**3*x + 3*(1-alpha)*y3' - 3*(1-alpha)**2*y3'' + (1-alpha)**3*y3'''
final = linreg(y3, len=22, offset=7)       # nonzero offset FLATTENS output (de-waves)
trend  = sign(final - final[1])
ranging = sign(trend) * sign(final - supertrend(final, 0.15, 21)) < 0   # slope vs whisper-band disagree
```

**Variant B — fixed-coefficient 3-pole "dollar" channel (Gaussian on price AND on true range):**

```python
Sv = exp(-sqrt(2)*pi/200);  f = -Sv**2
vf = 2*Sv*cos(sqrt(2)*pi/200);  fg = 1 - vf - f
mid_t    = fg*hlc3_t + vf*mid_{t-1}  + f*mid_{t-2}
dollar_t = fg*TR_t   + vf*dollar_{t-1} + f*dollar_{t-2}
inner = mid ± pi*2.415 * dollar
outer = mid ± (pi*2.415 ± 2.0) * dollar       # 6-band low-lag channel
```

**Mechanics:** A true Gaussian filter as a recursive cascade — an IIR approximation of the zero-phase FIR Gaussian at a fraction of the cost (FIR Gaussians of 15+ bars carry 7+ bars of phase lag; this costs nothing). The offset-7 linreg is a deliberate flattening trick producing a piecewise-flat trend that only turns on sustained displacement. The `ranging` flag (slope vs its own 0.15×ATR hugging band) is a genuine low-lag regime discriminator. Variant B applies the *same* filter to TR, giving a volatility channel in filter form.
**Zero-wait value:** 3–4 float registers per pole section, fixed multiplies, O(1) per tick; the linreg is maintained via rolling moments.

**Filter library (all fixed-coefficient O(1) recurrences — swap-in trend bases):**

```python
# SuperSmoother (Ehlers): a1=e^(-sqrt(2)*pi/L); c2=2*a1*cos(sqrt(2)*pi/L); c3=-a1**2; c1=1-c2-c3
y = c1*(x + x')/2 + c2*y' + c3*y''

# UltimateSmoother: a1=e^(-1.414*pi/L); c2=2*a1*cos(1.414*pi/L); c3=-a1**2; c1=(1+c2-c3)/4
us = (1-c1)*x + (2*c1-c2)*x' - (c1+c3)*x'' + c2*us' + c3*us''

# AMLAG adaptive-lag ribbon composite (18 alphas b=0.10..0.95, averaged):
l0=(1-b)*x+b*l0'; l1=-b*l0+l0'+b*l1'; l2=-b*l1+l1'+b*l2'; l3=-b*l2+l2'+b*l3'
A = (l0 + 2*l1 + 2*l2 + l3)/6          # the multi-alpha AVERAGE is the edge (single alphas still lag)

# T3 (6-chained EMAs, alpha = 2/(2+(per-1)/2), per=14 -> ~0.235): signal = cross(stage0, stage5)
x1..x6 = chained_EMA(x); y = -b**3*x6 + (3*b**2+3*b**3)*x5 + (-6*b**2-3*b-3*b**3)*x4 + (1+3*b+b**3+3*b**2)*x3

# JMA (Jurik): beta=0.45*(L-1)/(0.45*(L-1)+2); a=beta**power
e0=(1-a)*x+a*e0'; e1=(x-e0)*(1-beta)+beta*e1'; e2=(e0+pr*e1-y')*(1-a)**2+a**2*e2'; y=e2+y'   # pr=1.5+phase/100

# FRAMA (fractal-dimension adaptive): N1=(HH(len/2)-LL(len/2))/(len/2); N2 = one window earlier;
#   N3=(HH(len)-LL(len))/len; D=log2((N1+N2)/N3); a1=exp(ln(2/(SC+1))*(D-1)) clamp[0.01,1];
#   N=(SC-FC)*((2-a1)/a1 - 1)/(SC-1)+FC; alpha=2/(N+1); out=alpha*x+(1-alpha)*out'

# VAMA (volume-LENGTH average — window defined in volume units, unique):
v2i = vol / (meanVol * 0.67)
walk back: S_w += src[i]*v2i[i]; S_v += v2i[i];  stop when S_v >= L
VAMA = (S_w - (S_v - L)*src[i_stop]) / L        # window always sums to L "volume units"

# McGinley (self-damping): mg = mg' + (src - mg') / (len * (src/mg')**4)
```

---

## 1.6 Smoothed Range-Filter Family (deadband width = smoothed |Δprice|, multi-scale consensus)
`sources: B1 §1.6 ≡ B3 §2.3 ≡ B3 §2.2`

```python
def smoothrng(x, t, m):
    return EMA(EMA(abs(x - x[1]), t), 2*t - 1) * m        # 2-stage smoothed absolute delta

# (a) dual-tier (B1): fast t=13,m=8 ; slow t=200,m=2.8 ; standard = avg(fast, slow)
r = smoothrng(close, t, m)
if x > filt_prev: filt = max(filt_prev, x - r)       # one-sided ratchet: only steps up
else:             filt = min(filt_prev, x + r)       # only steps down
up += 1 while filt rising; up = 0 when filt falls
bull_cond = x > filt and up > 0
signal = bull_cond and last_state == -1               # state FLIP only (edge-triggered)

# (b) blended width (B3): smrng = 0.5*smoothrng(close,27,1.5) + 0.5*smoothrng(close,55,3.0)

# (c) scale-space consensus (B3 flop): run (a) at 5 sensitivities; rng = ATR14*0.8*sens/8, sens ∈ {3,5,6,12,16}
score_sens = 2*(trend(12) == dir) + 1*(trend(16) == dir)   # slow scales weighted higher
```

**Mechanics:** `r` is a double-EMA of the absolute increment — a volatility estimate of the *price path* (not bar range). The filter moves only when price displaces more than that noise estimate; the flip semantics (trade the state change, not the state) give natural entry/exit symmetry. The multi-scale variant scores a trend by whether it survives tightened and loosened noise thresholds — scale-space consensus, cheaper than an MTF stack and continuous (no TF quantization).
**Zero-wait value:** One comparison + one max/min per tick per sensitivity; five parallel instances ≈ 10 flops.

---

## 1.7 Instantaneous-Range SuperTrend (band width = current bar range)
`sources: B1 §1.7 ≡ B3 §2.7`

```python
rangec = 2 * (high - low)                     # SMA term cancels; band from the RAW bar range
upper = src + factor * rangec / 2             # factor = 2.8  ->  src + 2.8*(H-L)
lower = src - factor * rangec / 2
# standard SuperTrend final-band ratchet on {upper, lower}; flip on cross
```

**Mechanics:** Replacing ATR (averaged range) with the *current* bar's range makes band width an instantaneous volatility gauge: after a spike bar the bands are instantly wide (no trailing-stop whipsaw inside the spike's own noise); in a lull they collapse (fast flip). The noise floor is local rather than smoothed.
**Zero-wait value:** On 1m the band rebuilds continuously from the forming bar's running H/L (live aggTrade quantities) — intra-bar band updates with zero kline wait, while the committed flip stays close-confirmed. The most reactive trend line in the corpus; pair with a consensus gate (§1.6c) rather than trading it raw.

---

## 1.8 Volatility-Percentile SuperTrend (ATR multiplier as regime lookup)
`sources: B2 §1.2 (ELITE)`

```python
Hv    = YangZhang(log_ret, period=10, a=1.34)     # any §3.1 estimator
avgHV = SMA(Hv, 55)
r = Hv / avgHV                                     # dimensionless vol position vs own baseline
mult = (3.0  if r < 0.2   else 2.85 if r < 0.6  else 3.0 if r < 1.0
        else 3.15 if r < 1.4 else 3.5 if r < 1.8 else 3.6 if r < 2.4 else 4.0)
band = SuperTrend(ohlc4, factor=mult, len=10)
# signal: cross of close and band
```

**Mechanics:** Band width follows the volatility regime via a lookup table with a deliberate asymmetry: the quietest regime (r<0.6) gets the *tightest* band (2.85–3.0) — calm tape → band hugs price → scalping mode; expansion widens slowly to 4.0 — swing mode, flips only on genuine displacement. Input `Hv/avgHV` is regime-independent.
**Zero-wait value:** One HV estimator + one SMA + one division per bar; the multiplier changes rarely so the ratchet runs quasi-static; the flip fires on the cross tick. Drop-in upgrade for any ratchet in §1.12/§3.2.

---

## 1.9 TQI Trend-Quality Index + Efficiency-Weighted ATR + Quality-Indexed Asymmetric SuperTrend
`sources: B5 W5 + W6 (SELF-AWARE TREND SYSTEM)`

```python
# efficiency (Kaufman):  ER = |c - c[20]| / sum_{i<20}(|c[i] - c[i+1]|)      # 0..1
tqiEr     = clamp(ER, 0, 1)
tqiVol    = mapClamp(zscore(volume, 20), -1, +2, 0, 1)     # fallback: mapClamp(ATR/ATR(100), 0.6, 1.8, 0, 1)
pos       = (c - rolling_min(low,20)) / (rolling_max(high,20) - rolling_min(low,20))
tqiStruct = abs(2*pos - 1)                                 # 0 mid-range, 1 at extreme
tqiMom    = (#bars in last 10 with sign(delta_c) == sign(c - c[10])) / 10
TQI = (0.35*tqiEr + 0.20*tqiVol + 0.25*tqiStruct + 0.20*tqiMom) / sum(weights)

effAtr = ATR * (0.5 + 0.5*ER)          # clean-trend vol counts full; chop vol halved
```

```python
# quality-indexed ASYMMETRIC ratchet (width = f(quality), sides differ):
qDev    = (1 - TQI) ** 1.5                     # severe collapses widen fast, mild dips barely
tqiMult = 1 - Q + Q * (0.6 + 0.8*qDev)         # Q = quality strength (0.4); 0.6..1.4 × base
sym     = baseMult * legacyERfactor * tqiMult
active  = sym * (1 - A*0.3*TQI)                # side IN trend direction TIGHTENS
passive = sym * (1 + A*0.4*TQI)                # side BEHIND trend WIDENS
# both multipliers EMA-smoothed (alpha 0.15) so the ratchet cannot stick
flip = price crosses ratcheted band
       OR CHARACTER FLIP: TQI[1] > 0.55 and TQI < 0.25 and trendAge >= 5 and close crossed source
```

**Mechanics:** TQI is a continuous per-bar estimate of "how trend-like is this market" from four orthogonal channels (path efficiency, participation, position-in-range, bar-sign persistence). The payoff is `effAtr` (bands tighten in chop, open in clean trends) and the asymmetric ratchet: strong trends produce a self-accelerating exit line that hugs price from behind while the re-entry distance grows. The character flip exits on quality collapse alone — a regime-change exit that never waits for a band break.
**Zero-wait value:** All inputs are ≤20-bar running statistics; the whole pipeline is scalar → multiplier → ratchet, O(1) per tick.

---

## 1.10 Oscillator-Space Ratchet Machines (hysteresis state machines, not oscillator crosses)
`sources: B1 §1.4 (TrendShift/ASK) ≡ B4 W3 (Joker/MONEY ALGORITHM) ≡ B7 W2 (X-family, 3 corroborations); QQE ratchets B1 §2.8 / B4 W6`

```python
# Canonical: SuperTrend skeleton transplanted onto a double-smoothed momentum scalar
M     = EMA(RSI(close, 50), 30)              # slow "flow position" scalar
tr_r  = abs(M - M[1])                        # "true range" OF THE OSCILLATOR
WWMA  = EMA(tr_r, 50);  ATRM = EMA(WWMA, 50) # self-adaptive band width (vol of vol)
band  = 4.236 * ATRM                         # fib-extension multiplier

up = M + band;  dn = M - band
# RATCHET (SuperTrend final-band logic in oscillator space):
while M above slow line: slow = max(slow, dn)      # ratchets up only
while M below slow line: slow = min(slow, up)      # ratchets down only
direction flips when M crosses the slow line

# NEUTRAL-ZONE GATE (the edge): a flip is actionable ONLY from the 45–55 band
BUY  = cross_up(M, slow) and M < 45      # fresh flip out of the low zone
SELL = cross_dn(M, slow) and M > 55      # fresh flip out of the high zone
```

```python
# QQE ratchet-bands variant (fast oscillator source):
rsiMa = EMA(RSI(close, 6), 6)
delta = EMA(EMA(abs(rsiMa - rsiMa[1]), 11), 11) * 1.618     # (B1 variant uses 3.0)
longBand  = max(longBand',  rsiMa - delta) if rsiMa rising else rsiMa - delta  # ratchets up only
shortBand = min(shortBand', rsiMa + delta) if rsiMa falling else rsiMa + delta # ratchets down only
trend = +1 on cross_up(rsiMa, shortBand') ;  -1 on cross_dn(rsiMa, longBand')   # band break
```

**Mechanics:** The band width is the double-smoothed |Δoscillator| — an "ATR of the oscillator" — so the envelope widens when the oscillator itself is choppy and tightens in calm momentum; the 4.236× multiple yields wide, infrequent flips. The ratchet makes the envelope a *state* (it only tightens protectively until broken), and the 45/55 gate restricts entries to flips that occur *from* the neutral band — i.e. fresh reversals, not the late stage of an extended swing. This converts a lagging oscillator family into a freshness-gated, self-volatility-scaled hysteresis machine. (Compliance note: the trigger is a ratcheted *band break*, never a raw oscillator threshold cross — see Appendix A.)
**Zero-wait value:** 5 EMA registers + one ratchet float + one comparison per tick; the flip test is evaluable the instant the ordering flips intrabar.

---

## 1.11 Positional & Slope MA-Stack Classifiers (no line-cross anywhere)
`sources: B1 §2.6 ≡ B2 §2.1 ≡ B4 D1 (Lion) ≡ B3 §1.8 (6-phase)`

```python
# (a) Fibonacci-scale slope+stack (B1): EMAs {5, 8, 13, 21, 34, 55}
all_rising = all(ema_i > ema_i[1] for i in scales)              # 6-dim SLOPE state
trend_up   = all_rising and not all_rising[1]                   # edge-triggered
mega_up    = all_rising and (ema5>ema8>ema13>ema21>ema34>ema55)  # slope AND full ordering

# (b) tightly-spaced all-rising (B2): EMAs {30,35,40,45,50,60}
stacked_up = all(E[i] > E[i][1]);  entry = stacked_up and not stacked_up[1]   # rare 6-way alignment

# (c) positional fan (B4): fan = EMAs {9,21,55,100,200,300}
regime = +1 if close > max(fan) else -1 if close < min(fan) else 0   # above-all / below-all / between

# (d) six-phase arrangement machine (B3): C=close, M1=EMA50, M2=EMA200
if   C>M1 and C>M2 and M1<M2: phase="ACCUMULATION"      # above both, cross unconfirmed
elif C>M1 and C>M2 and M1>M2: phase="RUNNING UP"
elif C<M1 and C>M2 and M1>M2: phase="RE-ACCUMULATION"   # pullback inside uptrend
elif C<M1 and C<M2 and M1>M2: phase="DISTRIBUTION"
elif C<M1 and C<M2 and M1<M2: phase="RE-DISTRIBUTION"
else:                         phase="NO-TRADE WAIT"     # whipsaw arrangement
```

**Mechanics:** "Trend" as a multi-dimensional *positional/slope* state rather than a line crossing: positional tests have zero crossing-lag and cannot whipsaw on re-crosses. The all-rising tests demand every scale agree on direction *right now* (one lagging scale kills the stack — all-or-nothing); the six-phase machine separates trend (M1>M2) from position-within-trend and treats the pre-cross accumulation state as a distinct phase.
**Zero-wait value:** Six comparisons per tick; discrete states (up/down/ranging/phase) feed the strategy router directly (e.g., scalp-long only when mega_up, else maker-only).

---

## 1.12 Ratchet Hierarchies (major/minor nesting, proportional band stacks, flow-gated ratchets)
`sources: B2 §2.2 (Double SuperTrend); B4 W4 (LTM); B4 W2 (AlphaTrend)`

```python
# (a) nested minor/major with dip-buy inversion (B2):
minor = SuperTrend(ATR(10), mult = 3.0)     # entry timing
major = SuperTrend(ATR(14), mult = 6.0)     # regime (2x width)
LONG     = minor flips UP  AND major already UP      # pullback finished inside major uptrend
BUY_DIP  = major UP AND minor just flipped DOWN      # the dip ITSELF is the re-entry signal

# (b) 4-band PROPORTIONAL stack (B4): mK = base*(1 + K*step), K=0..3
#    Scalping (2.5, 0.20) | Balanced (4.0, 0.25) | Deep (6.0, 0.30)
if trend == +1: tsK = max(src - mK*ATR, tsK')        # 4 one-way ratchets, only up
else:           tsK = min(src + mK*ATR, tsK')
flip on the CHOSEN band (default K=3 outer; "Fast" K=1)
# band1 = retest trigger, band3 = flip, band4 = committed stop; depth-read 1..4 feeds §4.5

# (c) MFI-gated one-way ratchet (B4 AlphaTrend): the UP leg requires money flow
if MFI14[1] >= 50: line = max(low[1] - ATR[1], line')        # ratchet up only w/ positive flow
else:              line = ratchet_down(line, low, ATR)
trigger = (2-bar slope flip of the line) or (|close[1]-close[2]| > 2*ATR and close crossed line)
alternation filter: new signal valid only if previous signal was OPPOSITE direction
```

**Mechanics:** Two ratchets at different vol scales form a hierarchy: the wide band defines regime, the narrow band times entries — and the minor's *downward* flip inside a major uptrend is a pullback-entry object with a defined resolution event (the minor's up-flip). The proportional stack (`mK = base·(1+K·step)`) keeps band geometry scale-consistent (doubling base doubles every gap) and yields a continuous pullback-depth measurement instead of a binary cross. The flow-gated variant only ratchets up while buyers actually participate.
**Zero-wait value:** Each ratchet is one comparison per tick; entries are state-pairs evaluated at flip events; segment boundaries are event-stamped for §1.18's profile scoping.

---

## 1.13 ZLEMA + Max-ATR Hysteresis Deadband
`source: B2 §2.3 (Combined Algo v5)`

```python
L = 70
zlema = EMA(x + (x - x[(L-1)//2]), L)              # zero-lag EMA (lag = (L-1)/2)
V = 1.2 * rolling_max(ATR(L), 3*L)                 # 1.2 x max ATR over last 210 bars
state = +1 if close > zlema + V
      = -1 if close < zlema - V
      = hold previous otherwise                     # deadband of width 2V
```

**Mechanics:** The state flips only when price displaces from the ZLEMA by more than 1.2× the *maximum* ATR of the last 210 bars — a ceiling on recent extreme volatility. The band is guaranteed wider than any normal recent oscillation, so a flip is by construction a move the market has not made in ~3.5 hours of 1m bars: a self-calibrating "genuine regime move" test.
**Zero-wait value:** One recurrence + one rolling max (monotonic deque) + two comparisons per tick. This state is the permission gate of the 7-factor re-entry pattern (§4.13).

---

## 1.14 Bar-Drift Cross Family (close-channel vs open-channel)
`sources: B1 §2.3 ≡ B4 D5 ≡ B6 D1; open-lead variant B5 D1`

```python
# (a) ultra-short kernel (ALLOWED class): ALMA(len=2, offset=0.85, sigma=5)
closeS = ALMA(close, 2, 0.85, 5);  openS = ALMA(open, 2, 0.85, 5)
signal = cross_up/close_dn(closeS, openS)     # net bar-drift sign flip; fires on FIRST tick

# (b) double-SMA(2,2) on an 8x-resampled CONFIRMED stream (B4): cS = SMA(SMA(close,2),2), oS = same(open)
#     state machine (%-level exits) -> §3.4; only closed resampled bars are consumed

# (c) open-lead momentum (B5): lead = deltaHMA(open,5) - deltaHMA(close,12)
#     lead rising while price stretched = makers pushing opens ahead of closes (early drift read)
```

**Mechanics:** Comparing a smoothed *close* series to a smoothed *open* series measures intra-bar directionality (net body-mass drift) rather than price level. A 2-length asymmetric kernel piles its mass on the newest sample — effectively "is this bar's close drifting above its open, now". Within a bar the open side is frozen, so the fast path watches one live scalar cross one frozen scalar.
**Compliance note:** only the near-instantaneous kernels (len ≤ 2) are admissible; the 50-period ALMA close/open cross found in one source is a lagging MA slow-cross and was **excluded** (Appendix A).

---

## 1.15 Multi-Timeframe Voting & Alignment (confirmed-value pattern + grace window + strength gate)
`sources: B2 §2.4 ≡ B3 §2.1 ≡ B4 S5 ≡ B6/B7 port rules`

```python
# porting rule replacing every HTF fetch in the corpus:
#   maintain each indicator on its own TF kline stream; consume the LAST CLOSED bar of that TF.
tf_state[tf] = (direction, updated_at_kline_close)      # a vote = count over the table

# (a) per-TF votes: close > EMA(200) per TF  |  SuperTrend(15, x5) direction per TF  |  KHST dir per TF
#     (5 TFs: >=3/5 agreement required in the B2-v5 engine; 10-TF variants as dashboards)
# (b) alignment + GRACE WINDOW (B3): aligned = all(dir_tf == dir_main)
align_turn_on = aligned and not aligned_prev
alignOK = aligned or (bars_since(align_turn_on) <= 6)    # no instant revoke on 1-TF flicker
# (c) min-strength HTF bias (B4): daily EMA20, last closed daily bar
bias_bull = close_d > ema20_d and abs(close_d - ema20_d)/ema20_d >= 0.02   # 2% strength gate
else: bias = NEUTRAL      # weak trend => no bias at all (no flicker)
```

**Mechanics:** MTF voting is dimensionality reduction: a 1m signal requiring 3+ of 5 higher-TF agreements multiplies its false-positive rate by the per-TF error rate. The grace window kills the flicker naive vote filters produce exactly when one TF flips a bar or two early (the normal case at a genuine turn). The ≥2% distance gate prevents a price oscillating around the HTF MA from flipping bias every bar.
**Zero-wait value:** TF states change at most once per TF-bar (D1: once/day); the vote is a cached integer refreshed on TF close — the 1m fast path reads one integer.

---

## 1.16 Anchored / Session VWAP Z-Score (streaming mean-displacement)
`source: B1 §2.4 (Anchored VWAP Trade Planner)`

```python
# session reset (src = hlc3):   S_pv += price*volume;  S_v += volume;   vwap = S_pv / S_v
d = price - vwap
z = d / rolling_stdev(d, 20)
LONG  when price > vwap and z >= +1.5      (cooldown 20 bars)
SHORT when price < vwap and z <= -1.5
```

**Mechanics:** "Price is >1.5 historical-σ beyond volume-weighted fair value and on the far side of it" — a displacement/extreme condition, not a cross. The rolling σ of `d` normalizes the session's own mean-reversion envelope so 1.5σ has identical rarity every day.
**Zero-wait value:** VWAP is two running sums; `d` and its σ are O(1) per tick; the σ-boundary price (`vwap ± 1.5·σ_d`) is known in advance for pre-placed orders — fires the instant the tick crosses it.

---

## 1.17 Session Engine (drift classifier, persistent extremes, killzones)
`sources: B2 §1.7 (DTC session engine); killzone note B3/B6`

```python
sessions = NY 13:00-22:00Z, LONDON 07:00-16:00Z, TOKYO 00:00-09:00Z    # on crypto: UTC activity
on session start: open_s = open of first bar
during session:   hi_s = max(high); lo_s = min(low)
range_s = hi_s - lo_s
TREND_UP   = close > open_s + 0.3*range_s        # scale-free: closed in top 30% of OWN range
TREND_DOWN = close < open_s - 0.3*range_s
else SIDEWAYS
on session end: persist hi_s/lo_s as levels, active until broken OR age > 48h (TTL)
volume-spike gate: V > 2.5*SMA(V,50) counts only INSIDE NY or LONDON
```

**Mechanics:** Drift is normalized by the session's own range (scale-free across instruments). Persisting session extremes with an explicit 2-day TTL models where algorithms defend first, with a hard expiry so stale levels are never traded. Session-gated volume encodes "volume only means something where participants are present."
**Zero-wait value:** Three (open, hi, lo) triples by running max/min; persistent extremes are frozen trigger prices with known TTL — ideal resting-order anchors. Killzone windows (e.g., 02:00–05:00, 09:30–11:00 exchange time) are retained as *time priors* only, default OFF on 24/7 crypto.

---

## 1.18 Volume-Profile Family (all binning schemes consolidated; POC / Value Area / two-sided decomposition)
`sources: B2 §3.10 (session 24-bin) ≡ B2 §3.2 (CLV split) ≡ B4 M7 (segment, range-distributed, LVN) ≡ B5 W2 (wick-weighted two-sided) ≡ B6 S4 (adaptive ORB bins)`

```python
# --- (a) session profile (24 bins over running session [low, high]; volume at bar mid-price)
VWAP = sum(bin_vol*bin_mid)/sum(bin_vol);  POC = argmax(bin)
target = 0.70 * total_vol                    # VALUE AREA: expand from POC,
VA expansion: at each step add the adjacent bin (either side) with LARGER volume; stop at >= target
VAH, VAL = final bin edges

# --- (b) CLV two-sided split per bar (kline fallback; superseded by native delta rule §0.2-5)
buy_i  = V_i*(close_i - low_i)/(high_i - low_i);   sell_i = V_i - buy_i
# distribute buy_i/sell_i over bins by [low_i, high_i] overlap -> buy-histogram, sell-histogram

# --- (c) segment profile (window = CURRENT TREND SEGMENT, cap 500 bars; 30 bins):
for each bar: for each bin overlapping [bar.low, bar.high]:
    vol[bin] += bar.volume * overlap_fraction            # RANGE-DISTRIBUTED (not close-binned)
HVN = local maxima with vol >= 0.55*POC_vol              # acceptance shelves (price stalls)
LVN = local minima with vol <= 0.30*POC_vol inside VA    # vacuums (price traverses fast)
LVN_break = close crosses an LVN                          # ACCELERATION TRIGGER -> §2

# --- (d) wick-weighted two-sided partition (B5): per bar, W=150, Nbins=500
tot = body + 2*tw + 2*bw                     # wick lengths double-weighted so partition sums to V
body volume -> buy side if c>=o else sell side; wick volumes split 50/50 per side of body
# per-bin up/down volumes => local buy/sell imbalance map (order-flow asymmetry surface)

# --- (e) adaptive-bin ORB profile (B6): bin_tick = max(mintick, orRange/vpRows)
```

**Mechanics:** One fair-value/magnet framework, four accuracy tiers: close-binning → CLV split → wick-weighted partition → range-distributed / native-tick attribution. Segment scoping makes POC/VAH/VAL describe *this trend leg* rather than an arbitrary window; HVN/LVN convert the profile into tradable physics (shelf vs vacuum), with the LVN close-cross as an acceleration event.
**Zero-wait value (native upgrade):** maintain a running per-bin histogram for the active segment; each aggTrade adds its volume at its exact trade price — strictly better than every bar-approximation above. Recompute POC/VA/nodes only when the argmax or a node threshold changes (event-driven, amortized O(1)); LVN/POC/VAH/VAL are frozen levels between recomputes → one comparison per level per tick.

---

## 1.19 Premium/Discount & Frozen Fibonacci Arrays (pinned levels, OTE, PVP ladder)
`sources: B2 §3.6 ≡ B3 §3.8 (OTE) ≡ B4 D3 (PVP)`

```python
# (a) PINNED fib (non-repainting by construction): swing values FROZEN until next pivot confirms
fib_k = swingLow + (swingHigh - swingLow)*k,  k in {0, .236, .382, .5, .618, .786, 1}
# ATR-TOLERANCE REBOUND (band touch, not knife-edge):  tol = 0.3*ATR14
touched   = |low - fib382| <= tol
confirmed = touched and close > fib382 and close > open and V > 1.2*SMA(V,20) and MTF_aligned

# (b) OTE from the STRUCTURE-BREAK LEG (B3): leg = last_swing_low..last_swing_high at the break
OTE_zone = [0.618, 0.786] retrace of the leg
triggered    = wick into zone AND close back inside zone
invalidated  = close beyond the origin extreme of the leg
overlap flags: "OTE+OB" / "OTE+FVG" / "OTE+OB+FVG" (any live zone inside -> triple confluence)

# (c) previous-day PVP ladder (B4) — computed ONCE at 00:00 UTC from the closed prior day:
PVP = (H + L + C)/3;   dp = 2*PVP - (H + L)/2
ladder = { PVP + r*dp for r in (+0.5, +0.618, +1, +1.382, +2.74, -0.5, -0.618, -1, -1.382, -2.74) }
```

**Mechanics:** Level *pinning to confirmed pivots* is the correct non-repainting fib construction (rolling-highest/lowest variants move under price). The ATR-tolerance touch band formalizes what actually happens on liquid books (price stops ticks away from the level). OTE anchored to the leg that just broke structure retraces the displacement itself and composes with OB/FVG zones. The PVP ladder is a frozen 10-level magnet table computed from data the engine already has — zero intraday recomputation.
**Zero-wait value:** All arrays are static prices between pivot confirmations; per tick = N crossing checks. Rebound/OTE triggers are band-entry + close-out tests (§2.11 pattern).

---

## 1.20 Nadaraya–Watson Envelope (nonparametric fair-value curve, compact-kernel form)
`source: B1 §2.7 (Advanced SMC)`

```python
# Gaussian-kernel local regression, bandwidth h = 10, over 500 bars:
y_i = sum_j x_j * exp(-(i-j)**2 / (2*h**2)) / sum_j exp(-(i-j)**2 / (2*h**2))
MAE = (1/N) * sum_j |x_j - y_j|
upper = y_i + 3*MAE  (fit on lows) ;  lower = y_i - 3*MAE (fit on highs)
# usage: gate entries — trade only outside the ±3·MAE band in the trend direction
```

**Mechanics:** A nonparametric fair-value surface with data-driven band width (mean-absolute-error of the fit, not σ). Adapts shape to any curvature — trend, cycle, flat — with no model assumption.
**Zero-wait value:** The O(N²) naive form is inadmissible, but the kernel has compact support: with h=10, weights < 1e-6 beyond |i|≈22 → a **45-term** weighted average, only the newest point recomputed per bar (O(45)/bar, O(1) amortized/tick).

---

## 1.21 Ratchet-Band Ichimoku (chandelier averages) + Volatility-Adaptive Donchian Period
`sources: B3 §1.3 (Fresh Algo) ≡ B7 D2 (X-family); B1 §2.2 (adaptive Donchian)`

```python
def chandelier_avg(mult):                     # the ONLY primitive: 3 lines differ by mult only
    atr = ATR(50)
    up, dn = hl2 + atr*mult, hl2 - atr*mult
    upper = min(up, upper') if src' < upper' else up     # ratchets DOWN only while price below
    lower = max(dn, lower') if src' > lower' else dn     # ratchets UP only while price above
    state = 1 if src > upper else 0 if src < lower else state
    spt   = lower if state == 1 else upper               # active side = OPPOSITE band
    maxv  = max(src, maxv') if (cross_up(spt) or state==1) else spt
    minv  = min(src, minv') if (cross_dn(spt) or state==0) else spt
    return (maxv + minv)/2

tenkan = chandelier_avg(3); kijun = chandelier_avg(7); spanB = chandelier_avg(10)
senkouA = (tenkan + kijun)/2
```

```python
# volatility-adaptive Donchian period (companion variant, B1):
vol_ratio = (atr - min(atr,50)) / (max(atr,50) - min(atr,50))          # 0..1
len_t = round(base * (1 + s*(1 - 2*vol_ratio)))                        # s=0.4, clamp base*(1 ± s)
line  = (rolling_max(high, len_t) + rolling_min(low, len_t)) / 2                # high vol -> shorter period
```

**Mechanics:** The ratchet band is a chandelier that only tightens from the outside; the frozen band remembers the pre-break extreme — structural S/R with volatility-locked width. Averaging the running max/min envelope yields trend lines whose *speed is vol-locked* (ATR50) and whose separation is scale-free (3/7/10× one unit). Behaves like Ichimoku but survives crypto fat-tail vol; the adaptive-Donchian variant instead adapts the *window length* (period shrinks when vol spikes — structure caught faster).
**Zero-wait value:** Three scalar recurrences per line per tick; the frozen bands are known prices — resting-order levels by construction.

---

## 1.22 Compression & Coil Detection (5 independent formulations + the coil FSM)
`sources: B2 §1.9 (TTM 5-condition) ≡ B2 §1.4 (body compression) ≡ B6 W1 (VCE) ≡ B6 D4 (SMA-band) ≡ B7 W3 (extreme arrest); break triggers → §2.10`

```python
# (a) TTM squeeze w/ dwell + flow gates (B2): squeeze_on = BB(20,2) strictly inside KC(20,1.5)
#     AND ATR14 < 0.7*SMA(ATR14,20)  AND volume < SMA(volume,20);  regime only if sustained >= 5 bars
release_bull = squeeze_on[1] and not squeeze_on and close > KC_upper

# (b) body-size compression (B2): body=|close-open|; compressed = cross_dn(WMA(body,99), EMA(body,99))
#     (linear-weighted avg of bodies falls below exponential-weighted avg = leading contraction)

# (c) VCE coil FSM (B6) — the canonical multi-bar machine:
bgAtr = ATR(20); localAtr = ATR(4); medianRng = percentile(high-low, 50, 50)
isContracted = (localAtr < 0.82*bgAtr) or ((high-low) < 0.65*medianRng) \
               or (any bar in 1..5 had range > 1.5*bgAtr and localAtr < 1.10*bgAtr)  # post-impulse coil
tol = 0.50*bgAtr;  MAX_VIOLATIONS = 2                      # violation-TOLERANT box
if isContracted:
    if compLen == 0: compLen, compHi, compLo, viol = 1, high, low, 0
    elif high <= compHi+tol and low >= compLo-tol:
        compLen += 1; compHi = max(compHi,high); compLo = min(compLo,low)
    else:
        viol += 1
        if viol <= MAX_VIOLATIONS: compLen += 1; extend box    # pokes tolerated
        else: reset coil to this bar
else: compLen -= 1                                            # 1-bar grace, then 0
if compLen > compMax: reset                                   # stale consolidation dies
# EXTREME-ZONE ARMING (direction comes from WHERE the coil forms):
zoneTop = sessHi - 0.35*(sessHi - sessLo);  zoneBot = sessLo + 0.35*(sessHi - sessLo)   # 50-bar sess
compAtHigh = compHigh >= zoneTop  -> arms SHORT watch ;  compAtLow -> arms LONG watch
WATCH_EXPIRY = 10 bars after the coil stops qualifying       # freshness primitive

# (d) SMA-band containment (B6): in_range = ALL of last 20 closes within ±ATR(500) of SMA(20)
#     -> box [ma-band, ma+band]; break of box = state os = ±1  (hard containment, 2nd independent vote)

# (e) extreme arrest (B7) — pure price action, 4 registers:
is_new_high = rolling 10-bar high made THIS bar; dir from whichever extreme prints
pp = running extreme of the current leg's swing points
if pp changed: if consCnt > 5 and pp > condHi: BREAK_UP ... ; consCnt = inside ? +1 : 0
else: consCnt += 1
if consCnt >= 5: seed box = 5-bar [high, low]; box only GROWS while price stays inside
```

**Mechanics:** The template is stable across all five: `compressed AND at-extreme AND bounded-age ⇒ reversal/expansion watch`. (a) demands geometric + absolute-vol + flow + dwell agreement; (c) adds violation tolerance (a wick through the box ≠ death — statistical, not knife-edge) and arm-direction from session-extreme location; (d) is a hard-containment second vote (two independent detectors agreeing at a range edge = high conviction); (e) measures compression as *absence of new swing extremes* — no ATR, no MA, regime-free.
**Zero-wait value:** Every variant is a handful of registers (counters, box floats, one expiry). In a tick engine the watched coil box is a *resting-order zone*: passive limits just outside `watchHigh/watchLow` the moment the watch arms; the "trigger" is your order being swept intrabar, and violation/expiry are kill conditions evaluated per tick.

---

## 1.23 Volatility-Regime Gauges, Directional Composite & No-Trade Gates
`sources: B1 §4.6; B2 §4.3, §1.8; B3 §4.9, §2.10, §4.11; B7 D4; B4 D7-family; B6 R6-CI`

```python
# --- gauges (all O(1); pick 2-3, expose as one vol-state vector) ---
nATR   = (ATR14 - min(ATR14,20)) / (max(ATR14,20) - min(ATR14,20))     # position in own 20-bar range
vol_pct= 40*(ATR14 - (mu20 - 2*sd20)) / (4*sd20) + 30                  # z-gauge vs own 20-bar moments
vol_ratio = ATR14 / SMA(ATR14, 200)                                    # vs ~3h baseline (>1 expanding)
atr_rank  = rank(ATR14 within last 60) / 60 * 100                      # percentile
expanding = ATR(5) >= EMA(ATR(5), 5)                                   # vol inflection (earliest turn)
chop      = 100*log10(sum(TR,14) / (HH(14) - LL(14))) / log10(14)      # Choppiness Index

# --- asymmetric direction gates (B1): long needs vol out of bottom 20%, short needs top 50%
long_gate = nATR > 0.2 ;  short_gate = nATR > 0.5 ;  extra: ATR14 > ATR14[2] (vol rising)
# downside crypto moves are sharper => shorts demand ~2x the vol floor

# --- vol-climax penalty (B3): PENALIZE top-20% vol (entering at climax = bad fills)
score_vol = (atr_rank < 80) + (atr_norm < percentile_60(atr_norm))

# --- NO-TRADE kill gates (B3) — highest-leverage filter in the corpus, 4 comparisons:
no_trade = (ATR14 < atr_floor) or (range_20 <= ATR14*1.2) or (ADX14 < adx_min)
adx_rising_ok = (ADX14 >= adx_min) or (ADX14 - ADX14[6] >= 0.25)   # slope forgives weak level

# --- directional range-imbalance composite (B7 D4) — score in [-100, 100]:
bullR = EMA21( (close>open) ? (high-low) : 0 ) ;  bearR = EMA21( (close<open) ? (high-low) : 0 )
dirImb = (bullR - bearR) / ATR14                    # ATR-normalized polarity split of RANGES
score = clamp( (ATRpct - 50) + 20*dirImb + 18*(EMA21-EMA55)/ATR14 + 16*(close-EMA55)/ATR14, -100, 100 )
ExpansionUp   = ATRpct >= 80 and score >= +12   (edge-triggered; sign-flip of score kills the scaffold)
```

**Mechanics:** A dimensionless vol-state vector (position-in-own-range, z-score, ratio-to-baseline, percentile, inflection) feeds every consumer: asymmetric direction floors, climax penalties, no-trade kills, and TP scaling (§3.4). `dirImb` is the distinctive statistic — bullish candles systematically wider than bearish candles is *persistent directionality* measured directly, with no price cross involved. The choppiness index (path length vs net displacement) and ADX-slope escape hatch (a strengthening-from-weak-base trend is tradable; a flat one is not) complete the gate set.
**Zero-wait value:** All O(1) running statistics; the gates are booleans that switch engine *mode* (e.g., maker-only below floor) at zero per-tick cost.

---

## 1.24 Sticky Regime Anchors (jump-reset levels, walking channel, offset bands)
`sources: B1 §1.5 ≡ B5 M6 ≡ B6 D3`

```python
# core anchor (B1, gate = ATR(200)*15):
if abs(close - level) > gate:   level = close;  hold = gate/2      # regime jump (teleport)
else:                           level += os * (hold/50)            # os = ±1 (own slope); fixed drift

# walking-channel variant (B6):  T = 15*ATR(200);  anchor += os*hold_atr/50 ;  R1..S2 = anchor ± {0.5, 1.0}*hold
# offset-band variant (B5, gate = 8*ATR50):
if |close - anchor| > 8*ATR50: anchor = close;  hold_atr = 8*ATR50
support    = [anchor - hold/8,   anchor - hold/16]                 # 0.5*ATR50-thick band
resistance = [anchor + hold/16,  anchor + hold/8]
```

**Mechanics:** A level that is almost frozen: it drifts at a fixed ATR-fraction per bar in its own direction and teleports only on a true regime break (8–15× long-ATR displacement). Between extremes it is an immutable memory of "where price settled last" — institutional anchoring that never repaints and never decays; the walk prevents staleness. One scalar + one sign per symbol.
**Zero-wait value:** The ideal maker object: the exact level price is known in advance; pre-place working orders at `level ± hold/2`. "Anchor jumped" is itself a regime-change event worth a fresh book layout.

---

## 1.25 MA-Intersection Matrix (convergence-price map)
`source: B6 W3 (TrendFilter)`

```python
def cross_value(s1, s2):                      # exact price where two smoothed series will meet
    m1, m2 = s1 - s1[1], s2 - s2[1]
    if sign(s1 - s2) != sign(s1[1] - s2[1]):
        sf = (s1 - s2) / (m1 - m2)
        return s1 - sf*m1                     # 1-bar linear extrapolation intersection
def intersection_matrix(lens=range(10,21)):
    smas = [ (cumsum_i)/i for i in lens ]     # O(1) each via running cumsums
    M = { (i,j): cross_value(a,b)  for pairs with sign-flip of gap this bar }
# quantity (1 - sf) on each intersection = which leg is decelerating
```

**Mechanics:** N moving averages become N·(N−1)/2 *prices* — a live map of "where SMA(i) and SMA(j) converge". A cluster of predicted intersections near current price is a quantitative momentum-convergence read; the map generates pullback targets without any cross signal.
**Zero-wait value:** Cumsum SMAs + O(1) pair checks per tick; pure arithmetic, no charting.

---

## 1.26 Trend-Speed Wave Statistics (wave dominance scoring)
`source: B1 §1.10 (AI Vanga Trend Speed)`

```python
# dynamic trend line: EMA with volatility-normalized length + impulse accelerator
L_dyn = 5 + norm(|close|, 200)*45                                   # 5..50
alpha = (2/(L_dyn+1)) * (1 + 5.0*(|d_close| / max|d_close|_200))    # accelerates on impulses
trend = EMA with time-varying alpha
# wave = sum (RMA(close,10) - RMA(open,10)) since last trend-line cross   (net-flow proxy per bar)
bull_avg, bull_max = mean/max of bullish waves (deque 100) ;  bear mirrors
dominance_avg = bull_avg - |bear_avg|          # net directional power
ratio_avg     = current_wave / bull_avg        # is THIS wave historically strong?  (>1 = anomalous)
```

**Mechanics:** A wave accumulates the close-minus-open delta (≈ net buy pressure per bar) until the dynamic trend line is crossed; comparing the current wave to the distribution of past waves is a change-point detector that flags impulses unusual *for this market's own volatility state*.
**Zero-wait value:** `speed += (RMA(c,10) − RMA(o,10))` is O(1)/bar; per tick accumulate `±Δprice` directly; wave stats are a bounded deque; the current-wave ratio fires mid-wave, not at wave end.

---

## 1.27 MTF-Safe Smoothed Heikin-Ashi Bias Oscillator
`source: B4 W5 (KD System)`

```python
ha_o, ha_c, ha_h, ha_l = EMA(open,100), EMA(close,100), EMA(high,100), EMA(low,100)
ha_close = (ha_o + ha_h + ha_l + ha_c)/4
ha_open  = (ha_open' + ha_close')/2             # recursion lives on EMA'd values -> composable
ha_high  = max(ha_h, ha_open, ha_close); ha_low = min(ha_l, ha_open, ha_close)
osc    = 100*(EMA(ha_close,100) - EMA(ha_open,100))
smooth = EMA(osc, 7)
state  = bull-strengthening / bull-fading / bear-strengthening / bear-fading   # 4-state hysteresis
```

**Mechanics:** Raw HA recursion cannot be resampled (path-dependence); pre-smoothing the four components makes the whole stack composable under any timeframe aggregation. The oscillator is net candle-body pressure after two generations of smoothing; the 4-state hysteresis (vs its own EMA7) makes "fading" the early-warning state.
**Zero-wait value:** Pure streaming EMAs, O(1)/tick; far smoother than raw HA color, far less laggy than a long EMA.

---

## 1.28 VWRA — Volume-Weighted Kernel Oscillator (generalized VWMA for any kernel)
`source: B4 W1 (LyroRS)`

```python
# works for SMA/EMA/KAMA/FRAMA/ALMA kernels:
K_x = kernel(src*vol, L) ;  K_v = kernel(vol, L)
vwra = K_x / K_v                     # volume-weighted generalization of VWMA
osc  = (src - vwra)/vwra * 100
up_band = ema_smooth(vwra + 1.80*sigma27, 0.8)     # ASYMMETRIC bands (EMA alpha 0.8)
dn_band = ema_smooth(vwra - 0.85*sigma27, 0.8)     # downside extensions shorter/sharper
signal_bull = cross_up(osc, 0)                     # = price reclaiming trade-weighted fair value
```

**Mechanics:** The reference line is where *capital actually is* (heavy bars pull harder), not the arithmetic mean; asymmetric σ bands encode the empirical downside-sharpness bias. Generalizing VWMA to arbitrary kernels buys adaptive lag and volume weighting simultaneously.
**Zero-wait value:** Two streaming kernels + ratio; on Binance `vol` is native (aggTrade), so the denominator never degenerates; the zero-cross evaluates tick-to-tick on the forming bar.

---

## 1.29 SuperTrend-on-Open + Mean-Reversion Reclaim Gate
`source: B4 D2 (Million Moves Alga)`

```python
STo = supertrend(src=open, factor=2.5, len=11)        # source = OPEN (known at bar start)
gate_mr = close >= SMA(close,13) and ema200_was_below_2_bars_ago     # state flag
long  = st_flip_up and gate_mr        # entry on RECLAIM of the macro average
```

**Mechanics:** Two low-lag choices: a band built on *open* reacts to session displacement rather than close-confirmation; the gate is not "close > EMA200" (trend-following) but "EMA200 was below 2 bars ago and price is back above SMA13" — the mean-reversion flip at the macro average, captured as a 2-bar state flag.
**Zero-wait value:** Open-based band is fully computable at bar start; the gate is a sticky boolean; everything evaluates tick-to-tick.

---

## 1.30 Outlier-Clamped Trend (input-censored smoothing)
`source: B2 §1.3 (Clear Trend)`

```python
sig5   = rolling_std(close, 5)
cprice = clip(close, WMA5 - 0.3*sig5, WMA5 + 0.3*sig5)     # spikes truncated to ±0.3 sigma
REMA   = WMA(WMA(cprice, 200), 3)                          # 200-bar trend, double-smoothed
signal = sign(REMA - REMA')                                 # direction FLIP only
band   = REMA ± 0.1*ATR14 ;  SL = 3*ATR14
```

**Mechanics:** Censoring the *input* before smoothing strips single-bar spike information: a lone wick contributes at most 0.3σ to each affected average, so the trend line moves only on sustained displacement. Same philosophy as the MAD/MAAD robust estimators in §3.1 — applied to the trend source itself.
**Zero-wait value:** Clamp = two comparisons against a frozen (WMA5, σ5) pair; `REMA ± 0.1·ATR14` are known-in-advance trigger prices.

---
---

# SECTION 2 — MICRO-TRIGGERS & ENTRY MECHANICS

*Event layer: everything here fires on a level-crossing, a pattern completion on confirmed bars, or a bounded countdown — never on a lagging indicator cross. Latency budget per trigger: tick-executable (frozen level) ≤1 comparison; bar-confirmed patterns ≤1 bar; countdowns bounded and known a priori.*

---

## 2.1 Market-Structure-Shift Engine (canonical: swing feeds → BOS/CHoCH FSM → sweep→MSS→tap pipeline)
`merged from: B1 §3.1; B3 §2.4, §2.5; B6 D2, M1, M2, M7; B7 M1, M2`

### (A) Swing feeds — three speeds, one policy (confirmed pivots define levels; forming swings only gate)

```python
# 1. CONFIRMED pivot (left=right=L complete; never re-classifies): for levels
# 2. MONOTONIC fractal (B1; fastest deterministic confirm, length L=5, p=2):
dh = sum_{i=0..p-1}( sign(high[p-i] - high[p-i+1]) )        # last p bar-to-bar signs
bull_fractal at bar (now-p) <=> dh == -p and dh_at(now-p) == +p and high[p] == max(high[-L:])
#    strictly monotone up-then-down peak; no ties => deterministic, no repaint
# 3. ZERO-LATENCY swing (B1 live zigzag / B7): is_new_high(src, N) == True  -> forming swing NOW
dir = +1 on new high (absent simultaneous new low); -1 on new low
on direction FLIP: push (extreme, bar, price) onto deque (len ~12); else update last point in place
classification of last 3 points: HH / LH / HL / LL
```

### (B) Structure FSM — close-confirmed crosses, typed breaks, level swap, two-step IDM confirmation

```python
# ATR+leg-scaled swing tracker (B3): flip_threshold = ATR14 + |point - prev_point|*buffer
#    (bigger counter-move required after a big leg -> fewer false swings)
# EVENT = confirmed CLOSE crossing the prior swing price (never the wick):
if close[1] <= swing.price < close:  event = BOS if state==Up else MSS(=CHoCH);  state = Up
if close[1] >= swing.price > close:  event = BOS if state==Down else MSS;        state = Down
new_support = min(low between broken pivot and now)      # next level installed AT the break

# typed breaks + level SWAP (B3 FTR):  type = "BB" if close > BoS_level else "BW"  (body vs wick)
if close < ChoCh_level: ChoCh_level, BoS_level = BoS_level, low ; trend = Down   # symmetric swap
elif low < ChoCh_level: ChoCh_level = low                                          # wick: level follows

# DISPLACEMENT GATE (B6 TJR): |close - open| > 0.6*ATR(14) required for the confirming break
# FIB BUFFER on MSB flips (B7): bull->bear requires l0 < l1 - |h0 - l1|*0.33
#                               (a new swing must undercut by >= 33% of prior leg = noise filter)
# IDM TWO-STEP (B6/B3): a CHoCH candidate is CONFIRMED only if the counter-pullback survives:
#    after close > lastH, rest a monitor at idmLow; low < idmLow => flip VOIDED (rolled back)
# STRONG POINTS (B3): on BoS_up create strong_low = opposite swing low; expires on confirmed close below
# SWEEP RECLASSIFICATION (B6): level wicked (high > lvl and close < lvl) => level RECLASSIFIED
#    as liquidity-tag line (swept, not broken) — still tradeable, role changes in real time
# CISD momentum bit (B3): close beyond open of last opposite candle = 1 stored float + 1 comparison
```

### (C) TJR pipeline — sweep → MSS → zone-tap (the reference 3-stage FSM)

```python
pivots = 8/8, each level consumed once (shBroken flag); BSL/SSL = latest swing high/low
# stage 1 SWEEP (arm):  sweep_low  = low  < SSL and close > SSL        (wick pierce + close back)
# stage 2 MSS (confirm, within 12 bars of sweep, displacement per gate above):
MSS_up = close > sweeped level with |close-open| > 0.6*ATR14
# entry zone adopted AT MSS: fresh FVG >= 0.2*ATR14 -> that FVG
#                            else 50% equilibrium band of leg [sweep extreme, MSS-bar extreme] ± 0.1*ATR14
# stage 3 TAP (fire, zone TTL 20 bars):
bull_tap = low <= zone.top and close >= zone.bottom and close >= open     # zone consumed on fire
# SL = swept low - 0.5*ATR14 (BEYOND the swept liquidity); TP = 1R/2R/3R; debounce 10 bars
conviction = 100*min(1, 0.40*(stage/2) + 0.25*SMT + 0.15*killzone + 0.20*signal)   # -> §4 sizing
```

**Mechanics:** The merged grammar across seven independent implementations: consumed-once pivots; sweep = wick-pierce + close-back (reclassifies, does not consume); displacement-gated confirmation; origin-candle OBs (→ §2.4); close-based mitigation. The level-swap keeps two live anchors that are exactly "what breaks = reversal, what holds = continuation"; the fib buffer and IDM monitor are the two proven answers to "when is a flip real"; the TJR pipeline converts a sweep (information) into a structure break (action) into a zone tap (entry) with bounded TTLs.
**Zero-wait value:** Every stage is a 1–3 comparison predicate on live price against frozen levels — the whole machine runs per tick on <100 floats. Stage 1 can arm the instant the wick pierces (before the close-back even prints); the level the break installs is known at the break tick, so the exit is placeable while entering.

---

## 2.2 Liquidity Sweep / SFP / Equal-Level Family
`merged from: B1 §1.12, §3.5; B3 §3.6, §3.11; B4 M4, M8; B5 M5; B6 M6`

```python
# --- STRICT SFP (B1; five independent conditions, evaluable at the sweep bar's close tick):
pLow = confirmed pivot low (20/20)
bull_SFP = (low < pLow) and (close > pLow) and (open > pLow)        # open ALSO back = same-bar rejection
           and (low == rolling_min(low, 20))                               # sweep bar IS the extreme
           and (rolling_min(close, 20) >= pLow)                            # level was real before the sweep
signal = SFP[3] and close > pLow over 3 consecutive closes and bars_since_last >= 10
# tick-native: relax the 3-close hold to "price persists beyond the level for N ticks / X ms"

# --- EQH/EQL CLUSTERING (three tolerance units; count = resting-stop estimate):
#  B1: zigzag pivots within ATR(10)/6.9 (≈0.145 ATR); count > 2 => zone [avg ± ATR/6.9]
#  B3: |p1-p2|/p1 <= 0.15% of PRICE (stop clusters sit at identical prices)
#  B5: three consecutive swings within 0.2% of price => level = mean(p1,p2,p3)  (rarest, strongest)
#  B5-phantom: ATR(200)-tolerance variant for deep-regime EQ detection
# touch counter increments on every merge; swept => level consumed

# --- SWEEP CLUSTERS w/ bounded confirmation (B3 zzLiq):
#  cluster: consecutive sweep extremes staying within ±1*ATR of the FIRST grab (escape => cluster dies)
#  CONFIRM: close <= sweep_low - ATR  (down) / close >= sweep_high + ATR (up)  -> emit sweep box
#  post-sweep FVG filter: keep ONLY FVGs formed AFTER the grab (displacement follows the liquidity)

# --- PENDING -> CHoCH with decay (B4 Mirage): sweep => PENDING (wick extreme, level, score stored)
#  expires after 13 bars; FIRE when close breaks the last minor (8/8) pivot high (bull)
#  entry is on STRUCTURE BREAK after the sweep, not on the sweep bar; both-sides sweep one bar => ABORT

# --- one-shot LIQUIDITY PRINT (B6): print = high > lvl and close < lvl and high > high[1]
#  (wick + impulse + close-back); armed once per level, re-arms on next pivot

# --- body-dominance reclaim filter (B5): (close - low) > (high - close) required
#  (the reclaim body must be LONGER than the opposite wick); extreme window EXCLUDES current bar
```

**Sweep-confirmation config table (three bounded-latency tiers):**

| Config | Pool | Raid | Confirmation | SL / TP |
|---|---|---|---|---|
| Fast | pivot 5/5 | same-bar wick-through + close-back | none (immediate) | wick extreme / 2R |
| Reaper | pivot 8/8, ≤12/side | wick pierce | ≤3 bars: close beyond + directional close + vol ≥ 1.1·SMA20 + wick ≥ 25% of raid range | 1.5·ATR / 1-2-3R |
| Scored | pivot 21/21, ≤25/side | same-bar | score ≥ 50 (§4.1) + optional CHoCH ≤ 13 bars | wick ∓ 0.25·ATR / 1-2-3R |

**Mechanics:** The unified theory: equal levels are one level with a *touch count* (each touch = another stop cluster); a sweep is validated by rejection geometry (open+close back inside), persistence (cluster stays in the grab zone), participation (volume), and *sequencing* (probe-fail-then-sweep is the highest-information signature; structure must break after the grab). Bounded confirmation windows (≤3 or ≤13 bars) make every configuration HFT-portable — the engine waits a fixed, small count, then fires or discards.
**Zero-wait value:** Pools are FIFO on pivot events; the raid is a crossing event; each confirmation term is O(1) and can be satisfied intrabar (the moment volume/wick already qualify). Target projection = nearest un-swept opposite-side level — the trade's destination computed at entry from the same arrays.

---

## 2.3 FVG / Imbalance Engine (non-lagging detection, depleting-inventory lifecycle)
`merged from: B1 §3.4, §3.7; B2 §3.9; B3 §3.3, §3.4, §3.5, §1.10; B5 W3, M8; B6 M5`

```python
# --- DETECTION (evaluable during the 2nd/3rd bar of the pattern, before completion):
bull_fvg = low > high[2]                                  # zone [high[2], low] ; bear mirrored
stricter containment (B2): low > high[2] and low[1] <= high[2] and high[1] >= low
two-leg BODY imbalance (B1): (low[2] <= open[1]) and (high >= close[1]) and (low[2] - high) > 0
                             -> zone [high, low[2]]   (bodies bracket the displacement; earliest detect)

# --- SIZE GATES (choose per instrument; all single comparisons):
gap >= 0.25*ATR14 | gap > 0.2*ATR20 | gap >= 1.5% of 300-bar range | displacement body > 2*cum-mean body%
displacement-grade gate (B3): creation requires gap_atr >= 0.25 and body_ratio[1] >= 0.45

# --- LIFECYCLE (depleting inventory):
CE = (top + bot)/2                        # consequent encroachment = the 50% magnet
mitigated at CE touch (bull: high >= CE) ; full fill (high >= top) tracked separately
INCREMENTAL CLIPPING (B3): wick enters from below -> top = min(top, low)   # zone SHRINKS as it fills
                             # the CE follows the clip => step-wise tightening remaining-depth object
INVERSE CONVERSION (B2/B3): close through the far edge => IFVG: same box, polarity FLIPPED
                             armed -> retested (first touch) -> mitigated (close through)
BPR (B3): bullish-bearish FVG pair overlap within 6 bars -> BPR zone (two-sided imbalance; strongest
          single zone type); invalidation = close beyond far edge by MORE than one zone-height
RAID flag (B6): price returning into an active gap marks it raided; raid level = secondary objective
SESSION FVG (B1/B6): track only the FIRST gap of the session; mitigated when close passes far edge
INVENTORY POLICY (B2): evict if close beyond far edge ± 2*ATR14 (irrelevant distance) or age > 50 bars
                       caps: <= 12 active (B1), max 2/side + 2 inverse (B2), 220-bar expiry, 14 live (B3)
```

**Mechanics:** The CE/full-fill distinction encodes the magnet: a half-consumed gap still attracts completion. Clipping turns mitigation into *measured depletion* — the remaining unfilled depth is the live counterparty inventory, directly usable for sizing. Inversion formalizes "the flow that broke the gap now defends the other side," with a two-stage armed-then-broken state whose failure-after-retest is the stronger signal. Size gates in ATR units, %-of-range, and cumulative-mean-body units are three scale-free noise floors.
**Zero-wait value:** Creation is 1–2 comparisons on the 3-bar window (fires before the third bar closes); every transition is a crossing event; the clipped CE is a resting limit price known in advance.

---

## 2.4 Order-Block Engine (taxonomy + canonical lifecycle + volumetric attributes)
`merged from: B1 §1.9, §3.2, §3.3; B2 §3.3; B3 §3.1, §3.2, §3.10; B4 M1, M2, M3; B5 M2, M3, W4, W8; B6 M2, M3, M4; B7 M1`

### (A) Detection taxonomy — one template, six velocity detectors

| # | Detector | Rule (bull side) | Source |
|---|---|---|---|
| a | **Origin-of-leg** (canonical) | on BOS above confirmed swing: OB = bar holding the impulse low; top = that bar's high; accept if height <= 3.5·ATR10 | B1/B2/B6 |
| b | Velocity ROC | 4-bar open-to-open ROC crosses −0.28% → OB = first opposite-color candle in bars 4..15 | B6 W2 |
| c | Impulse gap | bar[5] red, close[4] ≥ open[5], next 3 lows > high[5] → OB at bar[4]/[5] (lower low) | B6 M4 |
| d | Consecutive-candle | opposite candle at t=6 ago + 5 same-direction candles after + min % move | B6 M4 |
| e | Consolidation-origin | scan back to swing; bars with range < 2×(ATR or cum-mean range); OB = extreme of those | B6 M4 |
| f | Volume-pivot | OB anchored at a pivot on the VOLUME series (20/20 vol pivot; participation peak) | B5 W8 |
| g | SCOB 3-bar sweep | bar[2] bearish, bar[1] bullish AND sweeps bar[2] low, close > high[1] → zone = bar[1] range | B4 M3 |
| h | Spike-parsed | bars with range ≥ 2·ATR200 get extremes INVERTED before the anchor scan (wick spikes can't anchor) | B5 W4 |

All reduce to: **OB = origin region of a fast move, identified by "abandonment" — price left and did not return.**

### (B) Canonical lifecycle (superset state machine)

```python
# creation filters: 0.5*ATR14 <= height <= 3.0*ATR14 (one-leg blocks only); displacement validation:
is_demand_brk = close[2] < open[2] and close[1] > open[1] and |close[1]-open[1]| >= 1.0*ATR14
# states: FRESH -> TESTED (wick re-enters; box dims) -> MITIGATED (50% consumed / mode-dependent)
#         -> BREAKER (close past far edge: POLARITY FLIPS, geometry kept, break volume recorded)
#         -> FILLED/INVALIDATED (close beyond opposite edge = consumed; deleted)
# TF-adaptive mitigation depth (B3): TF <= 15m -> 25% line ; else 50% line
# modes: Close / Wick / Avg(midline) — Avg is earliest & strictest
# mother-bar expansion (B6): if bar[2] was an inside bar, zone expands to the MOTHER bar's full range
# BB/MB typing (B7): block at the new-extreme leg (BB = origin of break) vs prior-leg block (MB,
#                    mitigated, weaker) -> priority order for retest targets
```

### (C) Merge/dedup & volumetric attributes

```python
# MERGE (B1): same-direction OBs with IoU > 0 -> union box, volumes summed
#             (B6): |new.top-last.top| < 0.1*(last.top-last.bot) or containment -> union
# DEDUP (prevention): reject creation if any |POI_new - POI_existing| < 2*ATR_scale (one zone per
#                     2-ATR neighborhood); overlap dedupe incl. cross-polarity (B3)
# VALIDATION SCORE at creation (B3, /8 -> graded in §4.8):
score = 2*sweep + 2*displacement(any FVG within 6 bars) + 1*killzone + 1*discount + 2*htf_aligned
# VOLUME-PROFILE GRID inside the OB (B1): split box into G=10 slices; per overlapping bar:
slice.vol += overlap/(bar.H-bar.L) * bar.V ;  POI_slice = argmax        # resting-limit = POC slice
# PER-ZONE CVD (B4): delta_z = sum(signed volume from zone birth to now)  # rising = defended program
# SIDE-VOLUME % (B5): buyV = V*(C-L)/(H-L); pct vs 300-bar max side-volume -> imbalance label
# PER-ZONE REJECTION ACCOUNTING -> §3.8
```

**Mechanics:** The origin-of-leg construction (a) is the most defensible: the literal bar that sourced the move, found by one O(leg) scan per structure event. A broken block does not die — it *converts* (breaker with recorded break volume; the iOB overlap variant trusts a flip only where the new opposing block overlaps the broken one, within 30 bars / 0.25·ATR). Volumetric attributes (slice grid, per-zone CVD, side-%) convert each box from geometry into a *relative-order-flow object*.
**Zero-wait value:** Creation is event-driven (one confirmed swing + one cross); lifecycle is ≤3 comparisons per box per tick; the POC slice, CE, and equilibrium line are pre-placeable resting limits the moment the box exists.

---

## 2.5 Delta / CVD Order-Flow Zones & Flow Events (the order-flow flagship)
`merged from: B2 §3.1 (Delta Reaction Zones); B4 M1 (CVD S/D); B2 §1.10 (absorption/climax)`

```python
# --- cumulative-delta pivot zones (canonical):
delta  = sign(close - open)*volume            # REPLACE with native per-trade signed volume (§0.2-5)
smooth = EMA(delta, 3);  cum += smooth        # running cum-delta (O(1)/tick on native feed)
if cum makes a 12/12 pivot HIGH:  RESISTANCE zone at that bar's price HIGH      # flow structure!
if cum makes a 12/12 pivot LOW:   SUPPORT    zone at that bar's price LOW
half_width = 0.35*ATR14 (frozen at creation)
# impulse statistics at creation (100-bar window):
pos_pct = sum(max(delta,0),100)/sum(abs(delta),100) ;  net = sum(delta,100)
label = SELL_FLOW if pos_pct >= 0.60 else BUY_FLOW if neg_pct >= 0.60 else MIXED
# MERGE (the distinctive rule): same-type zones overlapping or within 20 ticks:
#   union price range; pos_pct/neg_pct weighted by |net| of each; nets summed; earliest creation
# inventory <= 8 zones; zone dies when CLOSE crosses its far edge
# SIGNALS: support reclaim = close crosses back ABOVE zone midline (early: midline, not far edge)

# --- per-zone CVD trace (B4): each S/D zone carries its own running signed volume since birth
#    (demand zone with rising CVD = live buy program; falling = decaying)

# --- flow-vs-displacement EVENTS (B2):
vol_ma = SMA(volume, 20)
absorption = V > 1.5*vol_ma and |close-open| < 0.3*ATR14      # big flow, NO displacement = soaked
climax     = V > 3.0*vol_ma and (high-low) > 1.5*ATR14       # big flow + displacement = final sweep
cum_delta += sign(close - close_prev)*V ;  delta_norm = SMA(cum_delta,20)/SMA(V,20)
```

**Mechanics:** Cumulative delta has its *own market structure*: where the flow integral stops making progress (a cumdelta pivot), price has finished an impulse into opposition — the zone anchored there is where the next leg's flow fights. Impulse labels say *which side* built the zone; the |net|-weighted merge makes repeated flow at one price ONE stronger zone. Absorption vs climax split large-volume bars by what the flow *did* — exactly the microstructure question "did price move on this volume or not."
**Zero-wait value:** This is the one family that becomes **sharper**, not just cheaper, on the native feed: `isBuyerMaker`-signed aggTrade volume gives true per-trade delta; the 12/12 pivot test on the live cum series forms the zone the moment the left side completes. Zone portfolio ≤8 × five floats; per tick = 8 two-sided level tests + 8 midline tests.

---

## 2.6 Liquidity Voids (ATR200-scaled displacement gaps with fill-map)
`source: B1 §3.6 (Advanced SMC)`

```python
bull_void = (low - high[2]) > ATR(200) and low > high[2] and close[1] > high[2]
# zone = [high[2], low], subdivided into 13 equal slices
# invalidation: a CLOSE crosses any slice midline (the void starts filling)
# aging: slices gray out after 21 bars unfilled
```

**Mechanics:** Displacement larger than a full long-horizon ATR leaves a hole no orders filled; the 13-slice subdivision is a fill-tracker (each midline crossed = 1/13 of the displacement re-priced). ATR200 as the scale makes the detector regime-independent.
**Zero-wait value:** Three comparisons per tick against maintained ATR200/bar extremes; the 12 slice midlines are pre-computed — a full ladder of resting orders as the void backfills.

---

## 2.7 Dual Thrust with Trend-Discounted Asymmetric Coefficients (session-frozen levels)
`source: B1 §1.3 (AI Vanga)`

```python
# SLOW STATE at session open, from previous bars:
hh3, hc3, lc3, ll3  = max(H,-3), max(C,-3), min(C,-3), min(L,-3)     # mlen = 3
hh12, hc12, lc12, ll12 = ...                                          # nlen = 12 (ASYMMETRIC windows)
range_buy  = max(hh3 - lc3,  hc3 - ll3)
range_sell = max(hh12 - lc12, hc12 - ll12)
BT = open_session + k_buy  * range_buy
ST = open_session - k_sell * range_sell
# trend discount: uptrend -> k_buy = 0.35, k_sell = 1.05 (long gate tighter WITH trend)
#                 downtrend -> k_buy = 1.05, k_sell = 0.35
entry_long  when price >= BT and uptrend context (filter: ATR(1) > ATR(10))
entry_short when price <= ST and downtrend context
```

**Mechanics:** Buy/sell trigger distances from *different* volatility memories (3 vs 12 bars), and coefficients shifted ±50% by prevailing direction — the breakout threshold is itself a trend filter, easier to trigger with the trend.
**Zero-wait value:** Both levels **frozen at session open** (12 historical bars + the open). Afterwards: two `if price >= level` checks per aggTrade — the purest zero-wait execution object in the corpus.

---

## 2.8 Opening-Range Machines (multi-stage ORB + cycle classification + one-break rule)
`merged from: B4 D6 (Luxy ORB v5); B5 D5 (single-break); profile pointer §1.18e`

```python
# stages M in {5,15,30,60} min from a fixed UTC anchor; each stage = running max/min, FROZEN at completion
# (stages cumulative: ORB15 inherits ORB5's range); active = largest completed stage
crossed_up = close > active.high + 0.002*active.high            # 0.2% buffer; CLOSE-confirmed
volume_ok  = vol >= 1.5*SMA(vol,20) ;  strong_vol = vol >= 2.0*SMA(vol,20)   # strong BYPASSES trend
entry      = OPEN of the NEXT bar (pending-entry pattern: removes breakout-bar slippage)

# CYCLE MACHINE (the real edge):
committed = bars_outside >= 2                       # must hold outside >= 2 bars
went_far  = close traveled >= 0.5% beyond the edge  # minimum excursion
retest    = had_break and went_far and back inside and committed    # best-risk re-entry of the day
failed    = had_break and bars_since_break <= 5 and back inside and NOT committed
#         -> TRAP label; cycle counter DECREMENTED (the engine learns the fakeout)
rebreak   = retest resolved -> breakout re-armed -> new cycle (max 6/day/direction)
# FVG filter: breakout edge must lie within 2*gap_size of an unfilled 3-candle FVG
# ONE-BREAK RULE (B5): shared fire flag across BOTH directions — first break consumes the setup
# EOD: close at floating R (mark-to-R accounting)
```

**Mechanics:** The ORB supplies frozen structural levels; the cycle machine classifies every excursion (break → commit → retest → rebreak, or break → fail → trap), decrementing the budget on fakeouts. "2× volume bypasses the trend filter" encodes institutional participation trumping indicator direction.
**Zero-wait value:** Stage extremes are running max/min (O(1)/tick) that freeze into a per-session level table; breaks are crossing events; commit/fail/retest are bar counters; the whole machine is a finite automaton on (price, time-from-open). On 24/7 crypto: fixed UTC anchor or rolling 15-minute mini-ORBs.

---

## 2.9 Compression-Break Triggers (box breakout, dry bar, squeeze release, coil break)
`sources: B1 §3.13; B5 W7; B2 §1.9a; B6 W1 (break stage)`

```python
# (a) body-relative consolidation breakout (B1):
avgBody = SMA(|close-open|, 20);  consolidating = |body| < 2*avgBody
valid_box = (boxHigh - boxLow) <= 6*avgBody_at_start
LONG = |body| >= 1.5*avgBody_at_start and |body| > maxBody_during_consol
       and close > open and close > boxHigh            # evaluable on the LIVE body mid-bar

# (b) dry-bar displacement (B5): band = SMA(close,55) ± 0.2*stdev(close,55)   # ultra-narrow 0.2 sigma
dryUp = rolling_min(low, 1) > band.top            # ENTIRE prior bar (wicks incl.) outside the band
buy_limit = high of the dry bar;  SL = band.bottom captured at the event;  TP 1:1 / 2:2
#    risk auto-scales: stop distance IS the displacement width

# (c) squeeze release (B2): release_bull = squeeze_on[1] and not squeeze_on and close > KC_upper
#    live: during the forming bar, the moment price breaks KC_upper while last closed bar was
#    in the 5-condition squeeze -> event known BEFORE the close

# (d) coil break (B6 VCE): shortBreak = close < watchLow
#        or (low < watchLow and close < open and (open-close) > 0.40*(high-low))  # body-dominant
#    fire gated by direction-from-extreme-zone (§1.22c), watch active, 8-bar post-outcome cooldown
```

**Mechanics:** (a) is a two-sample significance test on the bar's own distribution (breaker must exceed both the 20-bar average AND the largest bar that built the range); (b) detects displacement via a 0.2σ band — only genuine moves put a *whole* bar outside it, and risk self-sizes to the move; (c)/(d) convert the §1.22 compression states into directional events at the earliest possible tick.
**Zero-wait value:** All live-evaluable on the forming bar's running body/high/low; boxes and watch-bands are frozen levels; cooldowns are counters.

---

## 2.10 Break-and-Retest Machines (level FSM, cloud-edge retest, fib band rebound)
`merged from: B5 M4; B1 §3.12; B2 §3.6 (rebound code); pointers to §1.3c/§1.19`

```python
# (a) 20-bar retest FSM (B5): lvl = last 5/5 pivot
ARMED on close crossing lvl (store brkBar)
LONG  = bar - brkBar <= 20 and low <= lvl + 0.3*ATR and close > lvl and close > open
# pending-level refresh: a NEW pivot forming DURING the window is held pending, activated on expiry

# (b) kumo-edge break + retest (B1): break_up = close > kumoTop and close[1] <= kumoTop[1]
#      and volume > 1.3*SMA(vol,20) ; retest_bull = 1 <= bars_since_break <= 10
#      and low <= kumoTop and close > kumoTop
#      THIN-CLOUD VETO: kumoThickness < 0.3*SMA(thickness,50) => no signal (no flow in a flat cloud)

# (c) ATR-band fib rebound (B2): tol = 0.3*ATR14
touched   = |low - fib382| <= tol ;  confirmed = touched and close > fib382 and close > open
            and V > 1.2*SMA(V,20) and MTF_aligned          # five facts about one bar
```

**Mechanics:** A retest is a two-sided level test (wick in, close out) — the same object as an SFP, applied to broken levels, cloud edges, and fib arrays alike. The 0.3·ATR tolerance band is what liquid books actually do (stops ticks away from the level); the pending-refresh rule prevents level churn mid-setup; the thin-cloud veto removes breaks that carry no order flow.
**Zero-wait value:** State = 4 scalars per side; each test is one low-comparison + one close-comparison; the *approach* into the band is a maker-friendly pre-arm (`place at level+tol` when the MTF gate is already up).

---

## 2.11 Trendline & Channel Break Engines (violation budgets, chains, max-touch enumeration, lagged volAdj band)
`merged from: B1 §3.11; B2 §1.6, §1.11, §3.8; B3 §1.6, §2.8`

```python
# (a) two-pivot channel with validity projection (B1): two consecutive same-type pivots (5/5)
#     pad = min(ATR(200)*0.1, price*0.001)*space ; VALIDITY: base line projected BACKWARD must not
#     have been touched by any low between the pivots (a pre-tested channel is invalid)
#     break = one linear inequality vs the PROJECTED line (slope known) -> fires at the crossing tick

# (b) VIOLATION-BUDGET trendlines (B2): violations = count(low[b] < line(t_b)) for b in
#     [created .. now-3]   # last 3 bars EXEMPT (grace)
#     line retired when violations > maxViolation (0 conservative, 1-2 "two-strike")
# (c) pivot-chain lines (B2): consecutive same-type pivots only; death = close cross OR age > 500 bars
# (d) max-touch pair enumeration (B3): last 7 pivots/side; all C(7,2) lines; keep the one
#     violating fewest subsequent pivots; ties -> higher future value; redrawn only on new pivot
# (e) volAdj lagged band (B2): Z = min(ATR30*0.3, close*0.003) lagged 20 bars, /2
#     break = close crosses line while inside [line ± 2Z], with Z*0.1 hysteresis
#     and slope-sign validity (only break WITH the line's intended direction)
# (f) BB-close-break -> one-way ATR-ratchet level (B3): up_event: level = max(level, low - ATR5)
#     down_event: level = min(level, high + ATR5) ; direction = sign(level - level')
#     the level is the HIGHEST DEFENDED LOW of the leg — directly orderable falsification price
```

**Mechanics:** Trendlines as *statistical* objects: a noise budget (b), an explicit TTL (c), a support-maximizing fit (d), and a deliberately **lagged** break band (e — a slow band of a fast band stabilizes the threshold across the event; removing the lag re-creates the whipsaw it filters). The backward-projection validity test (a) is a structural sanity check most channel tools lack.
**Zero-wait value:** Each line is (slope, intercept, width) — 3–4 floats; per tick = one linear evaluation + budget check; a 20-line portfolio ≈ 80 numbers, one pass per tick; all breaks fire at the crossing tick of the *projected* line.

---

## 2.12 Pattern → Executable Geometry (harmonic XABCD, Elliott completion boxes)
`sources: B3 §1.2; B7 W5`

```python
# --- harmonic completion on a rolling zigzag (4 parallel zigzags 24/24/35/35; last 6 points X-A-B-C-D)
TOL = 0.18
PATTERNS = {  # (xab, abc, xad) ratio ranges
 "Gartley": ((0.588,0.648),(0.382,0.886),(0.866,0.886)),  "Crab": ((0.382,0.618),(0.382,0.886),(1.802,1.902)),
 "DeepCrab":((0.886,0.936),(0.382,0.886),(1.802,1.902)), "Bat": ((0.382,0.550),(0.382,0.886),(0.886,0.886)),
 "Butterfly":((0.755,0.816),(0.382,0.886),(1.272,1.272)),"Shark":((0.382,0.618),(1.130,1.618),(1.000,1.130))}
xab = |b-a|/|x-a|;  abc = |c-b|/|a-b|;  xad = |d-a|/|x-a|
guards: B strictly inside extremes; ABCD leg direction consistent
risk, reward = |b-d|, |c-d|                       # stop beyond B, target at C — template-fixed spec

# --- Elliott impulse validator (4 comparisons on zigzag leg sizes; 1-bar-confirmed pivots):
W1 = p2-p1 ; W3 = p4-p3 ; W5 = p6-p5
isWave = (W3 != min(W1,W3,W5)) and p6 > p4 and p3 > p1 and p5 > p2      # wave-3 not shortest etc.
# ABC corrective: valid if c terminates within 0.854 of the motive range (deeper = motive dead)
# COMPLETION BOX: width = x_c - x_a projected forward from c-end ; price band [fiveLow, bTop]
# EVENT = price crossing the box boundary inside the right time bound (target reached / invalidated)
```

**Mechanics:** Both engines emit *executable geometry*, not labels: harmonic risk/reward is fixed by the template; the Elliott completion box is a bounded target zone with an explicit invalidation trigger. Tolerance bands (±18%, 0.854 fib bound) are what make exact-ratio patterns fire on noisy data.
**Zero-wait value:** Zigzag = 2-state machine over live extremes; validation is O(1) per new swing; the completion box's price band is a ladder of passive limits with the far boundary as the hard cancel level.

---

## 2.13 Bounded-Lag Divergence Traps (zoned fractal divergences, asymmetric pivots)
`merged from: B1 §1.2 (RQ-kernel WaveTrend); B4 D7; B5 D2; B6 nested-depth note`

```python
# --- asymmetric pivot engine (the machinery is oscillator-agnostic):
pivotL = pivot_low(osc, left=47, right=1)          # huge left = significant swings; R=1 => 1-bar confirm,
prev  = snapshot at previous confirmed pivot (value, price, bar)   # NON-repainting by construction
window = 5 <= bars_since(prev) <= 60       # bounded window: old comparisons are void
regular bull: low[1] < prev.priceLow and osc[1] > prev.osc
hidden  bull: low[1] > prev.priceLow and osc[1] < prev.osc          # + bear mirrors
valid = raw AND NOT opposite-raw (same-bar mutual exclusion) AND trend filter

# --- zoned fractal divergence (only divergences AT EXTREMES count):
fractal on wt2 with 5-bar window confirms 2 bars after the peak (minimum possible)
bull zones: fractal top requires wt2 >= 15 (weak) / >= 45 (strong); bear mirrors (−40 / −65)
div_bull = price HH at fractal while wt2 LH, INSIDE a zone

# --- RQ-kernel oscillator source (B1): kernel weights w(i) = (1 + i^2/(2*r*L^2))**(-r), L=8, r=8
esa = EMA(x,10); d = EMA(abs(x-esa),10); wt1 = EMA((x-esa)/(0.015*d), 21); wt2 = SMA(wt1,4)
# self-normalized by its own volatility d; kernel = 8-term circular buffer, incrementally updated
```

**Mechanics:** Divergence-in-a-trend is the actionable trap; mid-range divergence is noise — hence the extreme-zone requirement (two tiers). The 47/1 asymmetric pivot fixes over-detection (big left) while keeping 1-bar latency; the 5–60 bounded window voids stale comparisons; mutual exclusion prevents a bar being both signals. The RQ kernel gives a different noise/impulse tradeoff than an EMA-based oscillator (faster turn on impulses, still suppresses single-tick noise).
**Zero-wait value:** Fractal confirmation is fixed at 2 bars (bounded, known); pivots confirm at R=1; the kernel is an 8-term incremental sum. A tick engine may relax "2-bar fractal" to tick-persistence for sub-bar latency.

---

## 2.14 Stretched-State Fades (linearity fade, percentile-normalized deviation, cross-symbol SMT)
`sources: B5 W1; B5 W9; B1 §3.8`

```python
# (a) Pearson linearity fade: r = pearson(arange(20), last-20 closes)   # bounded [-1,1], scale-free
LONG  = cross_dn(r, -0.7)      # a too-straight DOWN line statistically snaps back
SHORT = cross_up(r, +0.7)      # a too-straight UP line fades
# five running sums (sum x, y, xy, x^2, y^2) -> r in O(1); exits: SL 1.5*ATR14, TP 2.0/3.5*ATR14

# (b) percentile-normalized deviation oscillator (B5):
oscDiff = hl2 - MA(hl2, 40)
oscRange = percentile(oscDiff, 1000, 99)                  # 99th pct of own 1000-bar magnitude
osc = HMA( (oscDiff/oscRange) - (oscDiff/oscRange)[15], 10 )     # 15-bar rate of change
BUY  = cross_up(osc, osc[2]) and osc < -0.5               # turn detected WHILE still stretched
# "0.5" always means half of THIS instrument's extreme deviations -> one parameter set everywhere

# (c) SMT cross-symbol divergence (B1): matched pivots (3/3) on two correlated symbols (BTC vs ETH)
SMT_div = (y2 - y1)*(sym_y2 - sym_y1) < 0                 # swing directions disagree => weaker one
#   pivot-counter sync resets on either instrument's fresh extreme (maps to BTC vs ETH, or TF vs TF)
```

**Mechanics:** Three independent stretch metrics — geometric (fit-to-line), distributional (percentile of own history), relational (correlated instrument fails) — each firing *while the stretch is still on*, before it unwinds. (a) and (b) are regime-invariant by construction (bounded r; self-normalized amplitude); (c) is information no single-symbol indicator contains.
**Zero-wait value:** (a) five running sums; (b) one sorted 1000-ring + two HMA registers; (c) one sign product per rare pivot event.

---

## 2.15 Reclaim & Dwell Triggers (VWAP dwell-reclaim, EMA touch-reclaim geometry)
`sources: B5 D3, D4`

```python
# (a) VWAP dwell-then-reclaim: belowRun = consecutive closes < session VWAP
LONG  = cross_up(close, VWAP) and belowRun[1] >= 6 and vol >= 1.0*SMA(vol,20)
forming = belowRun >= 6 and close > close[1] and (VWAP - close) < 0.4*ATR    # pre-arm state
# (b) EMA touch-and-reclaim (9/21/50 used as GEOMETRY, never crossed):
trend   = EMA21 > EMA50 and EMA50 > EMA50[3]                # 50-slope = direction
touched = bars_since(low <= EMA21) <= 3                     # pullback reached the middle MA
LONG = close > EMA9 and close > open and close > high[1] and vol >= 1.0*SMA(vol,20)   # expansion close
```

**Mechanics:** The dwell requirement (≥6 closed bars one side) converts a noisy VWAP cross into "rejected, soaked, now reclaimed"; the EMA stack is pure geometry — which line is the touch target, which is the reclaim line — with the trigger an expansion close above the prior high, so no MA cross ever gates the entry.
**Zero-wait value:** Integer run-counters + crossing events; (b)'s expansion condition is watchable live (`|live_close − open|` vs body threshold).

---

## 2.16 Early-Flip Slope-Acceleration Trigger (vol-adaptive second derivative)
`source: B3 §1.5 (Beluga)`

```python
slope = khma - khma[1] ;  accel = slope - slope[1]
atr_base  = SMA(ATR14, 200) ;  vol_ratio = ATR14/max(atr_base, eps)
accel_norm = accel / max(ATR14, mintick)
thresh = base_thresh * (1.0 + (vol_ratio - 1.0)*K)          # base 0.08-0.14 per class, K=1.0
early_buy  = slope > 0 and slope[1] <= 0 and accel_norm >  thresh     # velocity sign change +
early_sell = slope < 0 and slope[1] >= 0 and accel_norm < -thresh     # material acceleration
```

**Mechanics:** Fires *before* the trend band flips: first bar the smoothed slope turns (velocity sign change), second difference materially positive, threshold scaled linearly by the 200-bar vol baseline (vol expansion raises the bar; vol collapse lowers it). One code path across symbols and regimes — the only second-derivative trigger in the corpus.
**Zero-wait value:** O(1) state; maps to the engine's two-level signal design: pre-position on `early` (pending), execute on the flip.

---

## 2.17 Exhaustion Triggers (streak-climax counter, consecutive-close exhaustion)
`sources: B2 §1.5 (lele); B1-ASK consecutive-close note; B4 D6-family`

```python
run_up += 1 while close > close[4]        # each bar above its OWN 4-bars-ago close (4-bar momentum run)
TOP    = run_up > 13 and close < open and high >= rolling_max(high, 40)
#    => 13-bar non-reverting drift + reversal close AT the 40-bar extreme (climax top); counter resets
minor = same with (qual=5, len=5)
# companion: 13 consecutive closes < close[4] = trend-exhaustion state (context flag)
```

**Mechanics:** A run of 13 means thirteen consecutive bars each above their own 4-bar-ago value — sustained non-reverting drift; the climax requires (a) streak length, (b) a close *against* the drift, (c) a fresh N-bar extreme, all at once. Counter-reset prevents re-signaling.
**Zero-wait value:** One counter + one comparison per bar; the confirmation candle is watchable live (forming close against the drift at the extreme = knowable before close). Pair with §2.5's volume climax detector.

---
---

# SECTION 3 — DYNAMIC RISK & POSITION SIZING

*Architecture: one volatility state vector (two timescales) drives every stop, target, ladder, gate, and size multiplier. Stops are structural objects with ATR clamps; exits are finite-state machines; levels carry lifecycles and retirement policies; sizing is fractional, tiered, and regime-scaled.*

---

## 3.1 Two-Timescale Volatility Architecture & Estimator Library
`sources: B6 R3; B2 §4.1; B1 §1.8`

```python
# ARCHITECTURE (recurring across the corpus — preserve it):
deepATR = ATR(200..500)   -> zone GEOMETRY (box depth, FVG floors, liquidity pads, channel widths)
#   a 200-500-bar ATR is a slowly-varying constant in tick time (~0.4%/bar drift): compute once per
#   bar close, treat as FIXED between closes -> the level map is STABLE while risk is reactive
fastATR = ATR(10..20)     -> stop DISTANCE, buffers, trigger thresholds
deep_smooth = SMA(ATR(200), 200)               # ~400-bar smoothed (TP ladder 5/10/15 x this in one file)
cum_atr = cumsum(ATR(140)) / (t + 1)   # t = bars elapsed   # lifetime mean ATR — STATIONARY volatility spine that
#   never decays (rolling ATR breathes with the very regime that knocks out its own stops); use for
#   fixed Fibonacci risk maps: dev_base = 2.618*cum_atr ; dev_add = 0.618*cum_atr ; stop ratchet
#   at price ∓ dev_base ; ladder at stop ± {dev_base, dev_base+dev_add}
```

```python
# ESTIMATOR LIBRARY (run 2-3 in parallel: YZ for regime tables, EWMA for fast bands, MAD as floor)
r = ln(c/c_prev)
# 1 Close-to-Close:  sigma = sqrt(sum((r - r_mean)^2)/(n-1))
# 2 Parkinson:       sigma^2 = (1/(4*ln2*n)) * sum(ln(H/L)^2)
# 3 Garman-Klass:    sigma^2 = (1/n)*sum[ 0.5*ln(H/L)^2 - (2ln2-1)*ln(C/O)^2 ]
# 4 Rogers-Satchell: sigma^2 = (1/n)*sum[ ln(H/C)ln(H/O) + ln(L/C)ln(L/O) ]        # drift-free
# 5 GK-Yang-Zhang:   GK + ln(O/C_prev)^2 term                                    # + open gap
# 6 Yang-Zhang:      sigma^2 = Vo + k*Vc + (1-k)*Vrs ;  k = (a-1)/(a + (n+1)/(n-1)), a=1.34
# 7 EWMA:            v = lambda*v' + (1-lambda)*r^2 ;  lambda = (n-1)/(n+1)
# 8 MAD:             sigma ~= sqrt(pi/2)*mean(|r - r_mean|)
# 9 MAAD:            sigma ~= sqrt(2)*mean(|r - median(r)|)
```

**Mechanics:** The estimators are a bias-variance ladder for one question: CTC is cheap/noisy (blind to wicks); Parkinson uses only range; GK/RS use all four OHLC; Yang-Zhang adds open-gap variance (the only one robust to open/close asymmetry — hence its default use in §1.8); EWMA is fastest-responding; MAD/MAAD are outlier-immune.
**Zero-wait value:** Every estimator is O(1) per bar — a full volatility *state vector* at ~10 flops; the deep/fast split keeps geometry frozen (maker-friendly) and risk reactive (taker-protective).

---

## 3.2 Trailing-Stop Engines (ratchet family, spike-capped vol, momentum-adaptive offset)
`merged from: B1 §4.3; B3 §2.6; B6 R2, R4; B4 R5; B5 R2`

```python
# (a) chandelier ratchets (B1, five variants — same skeleton, one max/min per tick):
stop_long  = max(stop, low  - 2.2*ATR14)        # bar-extreme based
stop_long  = max(stop, maxHighSinceEntry - 2.2*ATR14)
post-TP2:  stop = max(stop', high - 3*ATR22)    # chandelier variant
# (b) UT-Bot ATR(1):  nLoss = 2*ATR(1) = 2*TR(last bar)      # stop re-prices EVERY bar, zero smoothing
#    floor on port: nLoss = max(2*ATR(1), 3*mintick_spread)  # else spread alone stops you out
# (c) HADYAN dual-ratchet (signal and stop are ONE object):
if close > stop' and close' > stop': stop = max(stop', close - nLoss)    # 2 bars same side: ratchet
elif close < stop' and close' < stop': stop = min(stop', close + nLoss)
elif close > stop': stop = close - nLoss          # single bar through: FLIP side
else:               stop = min(stop', close + nLoss)
# (d) Super Duper (B6): dist = 2.2*ATR10; longStop ratchets up ONLY when low' > longStopPrev
#     doji guard: if O=C=H=L -> hold previous stop
# (e) amplitude-window ratchet (B6): anchor = window extreme (2-bar highest/min), width = ATR(100)
# (f) spike-capped TR (B6 Smart Trail):
HiLo = min(high-low, 1.5*SMA(high-low,13))               # ONE wick spike cannot inflate vol 13 bars
HRef = high - close' - 0.5*max(0, low - high') ;  LRef = mirror ;  TR_mod = max(HiLo, HRef, LRef)
dist = 4*RMA(TR_mod, 13)
f2st = flip_extreme + 0.786*(trailLine - flip_extreme)   # secondary stop: 78.6% giveback of progress
# (g) momentum-adaptive offset (B5): momDist = |EMA(RSI(13),3) - 50|/50    # 0 center .. 1 extreme
effMult = baseMult*(1 - adapt*momDist*0.4)               # up to 40% TIGHTER into strong momentum
vol    = (ATR(13) + stdev(close,13))/2                   # hybrid range+dispersion
trail  = ratchet(anchor_MA -/+ vol*effMult)              # anchor = ALMA(21) default
# (h) entry-ratchet re-entry (B4): if close > TP3: entry = close; rebuild TP 0.5/1.0/1.5*ATR and
#     SL 2*ATR from NEW entry — the trade "re-enters" higher, banking the first leg geometrically
```

**Mechanics:** All share the one-directional ratchet (`extreme ∓ k·vol`, never loosens). The differentiated refinements: ATR(1) gives zero-smoothing-lag re-pricing (needs the spread floor); the two-bar-same-side rule distinguishes ratchet from flip and makes signal and stop the *same object*; the spike cap stops a single stop-run wick from inflating the trail for 13 bars; the 78.6% secondary converts "gave back too much progress" into a standalone level; momentum-adaptive width locks the runner faster exactly when continuation probability is highest (complementary to §1.9's quality-adaptive width).
**Zero-wait value:** Every variant is O(1) per tick (one max/min + comparisons); between bar closes the stop is a static price — a standing order, no recomputation.

---

## 3.3 Initial-Stop Policies (structural anchors + ATR buffers + clamps + guards)
`merged from: B1 §4.4; B4 R1; B5 R1; B3 §3.7, §4.5, §4.6; B6 R1; B7 R2`

```python
# wick/structure-anchored + noise buffer + MIN-DISTANCE GUARD (canonical, B4/B5):
sl_bull = signal_bar_low - 0.25*ATR14
sl_bull = max(sl_bull, entry - 0.5*ATR14)              # widen if too tight (fee/risk floor)
# hybrid structure/ATR switch (three policies, one line each — B5):
sl = max(entry - k*ATR, swingLow - 0.2*ATR)            # wider-of-two: structural realism
sl = min(pivotLow - k*ATR, entry - k*ATR)              # narrower-of-two: risk-first
# structure + fraction-of-ATR buffer (B1): swing/kumo-edge/fractal - {0.5..0.8}*ATR
# GAP-PROTECTED, ATR-CLAMPED (B3 — the object-protection template):
stop = min(gap_far_edge - 0.2*ATR14, entry + 1.5*ATR14)     # beyond the OBJECT that justifies trade
stop_dist = clamp(|entry - stop|, 0.4*ATR14, 4.0*ATR14)     # floor = noise; ceiling = macro
# ZONE-ANCHORED (B3): SL = min over touched zones of (ob.bottom, fvg.bottom, ote.legLow, breaker.bot)
#                      TP = opposite structural extreme (liquidity pool) — R:R out of structure
# SL BEYOND THE SWEPT EXTREME (B6 TJR): swept_low - 0.5*ATR14  (invalidation = re-sweep)
# 5-bar micro-stop (B7): SL = running 5-bar extreme — the tightest structural stop in fast tape
# ATR%-tiered with absolute minima (B4, multi-asset):
atr_pct = ATR14/entry*100 ;  mult = 1.5 if atr_pct > 3 else 1.0 if atr_pct > 1.5 else 0.7
sl = min(entry - ATR*mult, orbLow - 0.3*orbRange)          # conservative = farther
guard: sl_dist >= ATR*asset_min  AND  sl_dist >= absolute_min_pct*entry
# same-bar tie-break: SL checked FIRST (pessimistic; a tick engine instead resolves by chronology)
```

**Mechanics:** The stop is placed *beyond the structure that justifies the trade* (gap edge, sweep extreme, zone bottom, leg origin) — risk distance = distance to the falsification price, a structural quantity — then clamped in ATR units so R:R stays comparable across setups and the 0.4·ATR floor keeps the stop outside the instrument's own microstructure noise. The 0.5·ATR minimum-distance guard prevents the zero-wick-bar → oversized-position pathology.
**Zero-wait value:** All inputs are running extremes + one ATR scalar; placement is O(1) at the signal tick; the stop is then a standing order.

---

## 3.4 Take-Profit Ladder Architectures
`merged from: B1 §4.1, §4.2; B2 §4.4; B3 §1.9, §4.2; B4 D5/R1/B7 R1; B5 R3; B6 R5, R6; B7 R1`

```python
# (a) displacement-fibonacci plan from anchored VWAP (B1): d = entry - vwap
TP1 = vwap + 2.618*d ; TP2 = vwap + 4.236*d ; TP3 = vwap + 5.236*d        # RR 2.6 / 5.2 / 6.9
SL  = vwap + 0.382*d - 0.25*ATR14            # thesis dies at 61.8% giveback of displacement
# (b) fib-of-the-active-leg (B1): ex = running extreme since last flip
f1 = ex + (trail - ex)*0.500 ; f2 = ...*0.618 ; f3 = ...*0.786            # targets breathe with trail
# (c) PREDICTUM fib-decay ladder (B3): tp[n] = tp[n-1] + (tp[n-1]-entry)*0.618
#     sequence 1R, 1.618R, 1.99R, 2.215R ... -> asymptote 1/(1-0.618) = 2.618R  (closed form O(1))
# (d) %-of-price STAGE MACHINE (B2/B4/B7): one float IS the exit stage
SL=0.5%  TP1=0.2% (exit 80%)  TP2=0.5% (10%)  TP3=7.0% (2% runner)   # = 0.4R / 1R / 14R geometry
state: 0 -> ±1 (entry) -> ±1.1 (TP1) -> ±1.2 (TP2) -> ±1.3 (TP3); any -> 0 on SL or opposite trigger
#     port note: map the STRUCTURE (bulk at T1 ≈ 0.5-1 ATR, 2% tail at 9-14R) onto ATR ladders
# (e) ATR / HTF-ATR ladders (B2): SL = k*ATR14 (k ∈ 1.5..6) ; TPs 0.5/1/1.5R or 1.5/3/5/9*ATR14;
#     TP scaled by 4H ATR while SL uses 1m ATR = "local stop, macro target" asymmetry
# (f) dynamic band TP (B3): tp_dynamic = close beyond BB(20,2) outer band (target expands/contracts
#     with live vol); static cap tp = entry + 3*entry_risk_unit ("don't be greedy")
# (g) TQI-scaled ladder with PROPORTIONAL FLOORS + order-fix (B5):
volComp = mapClamp(ATR/ATR(100), 0.5, 2.0, 0, 1) ;  raw = (TQI*0.6 + volComp*0.4)
scale   = minScale + raw*(maxScale - minScale)                  # [0.5, 2.0]
tp_i    = clamp(base_i*scale, floor_i, 8R) ;  floors ∝ each level's base share (keeps ladder SHAPE)
tp1, tp3 = min(tps), max(tps) ;  tp2 = sum(tps) - tp1 - tp3     # order-fix: no preset can invert it
# (h) win-rate-first geometry (B6): TR = 2*ATR14 ; TPs = {0.8, 1.6, 2.8}*TR ; SL = 1.2*TR
#     (TP1 INSIDE the stop distance — frequency-first; payoff from the 2.33R tail)
# (i) event-gated unlocks (B6): TP2+ placed ONLY IF vol > 1.2*SMA20 or close right side of fast MA
#     at TP1 (scale up only on proof); dual-anchored caps (B4): TP_k = entry + min(orbWidth*k, risk*k*priceAdj)
```

**Mechanics:** Every ladder is a frozen set of price offsets at entry (static standing orders), differing in *posture*: displacement-fib (structure RR), decay (most profit early, asymptote 2.618R), scalp-front/runner-tail 80/10/2 (expected-value tail vs immediate win-rate), win-rate-first (TP1 < SL), macro-target asymmetry (HTF-ATR targets, local stops). The TQI-scaling + proportional floors is the only *regime-adaptive* ladder: targets stretch in high-quality/high-vol regimes and compress in chop without collapsing onto each other.
**Zero-wait value:** All computable at the entry tick from streaming scalars; register N limit orders, zero further computation; the band-TP and event-gated variants add one running comparison each.

---

## 3.5 Trade-Lifecycle State Machines (break-even, partials, re-anchor, reversal parity, chronology, win accounting)
`merged from: B1 §4.5; B2 §4.5; B3 §4.1, §4.8; B4 R2, R3; B5 R4, R5, R6; B6 R6`

```python
# position model (B4, the closed automaton): exactly one position or none;
flat -> open on signal ; opposite signal -> CLOSE + RE-ENTER opposite same tick ; same-dir -> ignore
closure paths exactly: SL | BE-stop | TP3 | reversal — nothing else

# break-even + caution (B3): at profit >= 1.0*entry_risk_unit: stop = entry (one-way ratchet)
#   waspada/caution flag: distance_to_stop < 0.75*entry_risk_unit -> pre-stage the reduce order
# partials: 50/30/20 at TP1/2/3 (B1) | 1/3 per tier (B5) | 80/10/2 (§3.4d)
# re-anchor (B1/B4): at TP3 (or close > TP3): entry = close; rebuild the whole geometry
#   -> the win becomes the new risk baseline; after TP1 the loss profile is zero by construction

# chronology rules (B5 — the difference between modeling bars and modeling events):
entry-bar guard:   no TP/SL checks on the entry bar
bar-start snapshot: a stop moved to BE THIS bar CANNOT stop out THIS bar (capture stop state at bar
                    open; on a tick engine this is simply event ordering by timestamp)
same-bar priority: SL-first (conservative) vs TP-first (optimistic) = backtest-parity knobs only

# expiry as a FIRST-CLASS outcome (B5/B6): 60-100 bars without TP1 -> "expired", booked separately
#   per setup (a setup whose trades mostly expire has no follow-through edge -> §4.12)
# lifecycle gates: one-way lock (long open => shorts dropped) ; cooldown N bars after resolution ;
#   maxOpen concurrency ; EOD force-flat ; stoppedOut flag blocks same-day re-entry
# frozen pending template w/ staleness (B3): freeze (entry=close±0.6ATR, TP1=+1ATR, TP2=+1.7ATR,
#   SL=+1.2ATR) at the flip; re-freeze only if stale > 6 bars at next alignment — decouples signal
#   time from execution time (cancel-and-replace semantics)

# --- realized-R accounting family (4 schemes — the variable that most distorts backtest edge) ---
R = sum_{i hit}(w_i * tp_iR) - sum_{i unhit}(w_i)          # weights = per-tier size fractions
TP3-only (strictest) | best-TP-reached (what got paid) | 1/3-split partial model | TP1-touch (win
once TP1 prints, even if stopped later at BE)
breakeven_win_rate = SL / (TP1 + SL)                        # accounting identity for win=TP1 systems
#   (e.g. SL 1.5, TP1 0.5 -> need > 75% TP1-touch; the engine's own EV monitor)
```

**Mechanics:** The exit plan as a finite automaton: every level-cross is a pre-declared transition; break-even-at-1R makes post-TP1 risk zero; re-anchoring converts winners into fresh baseline trades; reversal parity guarantees no signal is ever dropped; expiry/outcome classes feed the measurement layer. The chronology rules remove the phantom same-bar BE stop-out and the entry-bar self-stop — the classic kline-backtest artifacts.
**Zero-wait value:** A handful of floats + counters; each transition is a level-cross event; the accounting schemes are backtest-parity knobs while the live engine simply orders events by timestamp.

---

## 3.6 Volatility-Adjusted Sizing, Tiered Gates & Parameter Presets
`merged from: B1 §4.5; B2 §4.2; B3 §5.8; B4 R7; B6 S4; B3 §4.10`

```python
# base sizing — fixed-fractional from stop distance (risk $ per trade constant):
lot = (capital * risk_pct) / |entry - SL|                  # re-prices with the regime automatically

# Aladdin composite regime tier (B2) — the OUTERMOST multiplier:
vol_risk = min(100, ATR14/SMA(ATR14,100)*50)
chop     = 100*log10(sum(ATR(1),20)) / log10(rolling_max(high,20) - rolling_min(low,20))
systemic = 0.5*vol_risk + 0.5*chop
SIZE: systemic < 25 -> FULL | < 50 -> NORMAL | < 75 -> HALF | else CASH (no new entries)
# CASH is an entry veto only — open positions keep their own risk management

# confidence multipliers: R-tier from §1.3 (|Pearson-R| bucket) x score tier from §4 (50/70/90)
# vol-climax penalty (B3 §4.11): skip/downsize when ATR rank in top 20% (stops widest, fills worst)
# ATR%-tiered stop scaling + absolute minima -> §3.3 ; per-class preset tuples -> §1.4

# N-PARALLEL STOP OPTIMIZER (B6 — the only online what-if in the corpus):
simulate the SAME open trade under 5 stop widths (1.0/1.5/2.0/2.5/3.0 * ATR14)
-> N copies of the exit FSM sharing one price feed (N x few floats)
-> switch the live stop to the currently-optimal width (with hysteresis to avoid churn)

# wide-stop swing preset (B3 HalfTrend): atr2 = ATR(100)/2 ; SL = 3*atr2 = 1.5*ATR(100) ; TP 1/2/3R
#   (long-period half-ATR stop absorbs 1m noise on a ~1.5h vol scale; few, wide, high-RR trades)
```

**Mechanics:** Sizing is fractional (risk-constant), then regime-scaled by two orthogonal environment facts (vol level vs baseline, path efficiency), then confidence-scaled by the model's own quality outputs (R-tier, score tier), with a vol-climax penalty against the worst entry regime. The parallel stop optimizer is live re-optimization of an *open* trade, known before the trade ends. Per-asset preset tables make the entire parameter stack data, not code.
**Zero-wait value:** All inputs O(1); tiers are one comparison at decision time; the optimizer is N float copies of the exit machine updated per tick.

---

## 3.7 Level Lifecycle & Retirement (swing death, violation budgets, TTLs, age tiers, break-to-line)
`merged from: B1 §3.5 (swing death); B2 §1.6, §1.11; B6 W4; B2 §3.4 / B4 M6 / B6 M8 (break-to-line)`

```python
# SWING DEATH (B1): after 5 consecutive closes beyond a swing level, the swing is INVALIDATED and
#   its line retired — levels that keep failing stop being traded (failure-count policy)
# violation budgets (B2): a level survives up to maxViolation wick-throughs; last 3 bars exempt
# time expiry (B2): trendline/pivot-chain death at age > 500 bars (no liquidity memory that old)
# zone TTLs & eviction -> Appendix C master table (2-ATR irrelevance rule, FIFO caps)

# HTF UNMITIGATED AGE-STACK (B6): registry of still-unmitigated 15m highs/lows
register on HTF close only; mitigate on wick touch; keep <= 5 most recent per side
age = session_count_now - session_created ;  tiers 0-1 | 2-3 | 4+ | 7+    # fresher = more reactive
structure classifier per HTF bar: inside | expansion-up | expansion-down | both (new HH AND LL)
bands: bracket between 1st and 2nd unmitigated level per side; proximity = |close - level|

# BREAK-TO-LINE conversion (B2/B4/B6): a zone broken by close through the far edge is NOT deleted —
#   it collapses to a LINE at its midpoint/POI (BOS line): the level's memory of record, a classic
#   retest target, and 1 comparison instead of a box test
# polarity flip on break (B4): close > box.top => box = BULL support (broken resistance = support)
```

**Mechanics:** Levels are objects with lifecycles: they age out, die on repeated failure, convert to lines when consumed, and carry explicit freshness priors (session-age tiers). The unmitigated stack is a *magnet registry* — every unmitigated HTF extreme is a resting objective weighted by freshness. Break-to-line preserves the memory of failed defenses at one float instead of a box.
**Zero-wait value:** Sorted lists with O(log n) insert/mitigate; every death/conversion rule is a counter or single comparison evaluated per tick; the retirement policies are what keep the level set bounded and honest on a 24/7 feed.

---

## 3.8 Touch-Count Strength & Tested-Zone Accounting (levels graded by survival, not birth)
`merged from: B1 §3.9; B3 §1.11; B5 M1; B6 M8, S3; B7 S1`

```python
# --- CLUSTER STRENGTH (canonical S/R construction, 5-file family):
cwidth variants: 2% of 200-bar range | 5% of 300-bar range | 10% of 284-bar range | TR(pivot)/30
for each pivot (10-15/10-15, window 200-300 bars):
    cluster pivots within cwidth of the seed ;  strength = 20*(#pivots) + #bars whose [low,high]
    touched the cluster ;  rank top-5/6 ;  SUPPRESS any cluster nested inside a stronger one
# touch tolerance = the bar's OWN noise scale: |p1 - p2| <= TR*(1/30)   # regime-free clustering
# zone half-width = (ATR30/price)*(100/3) % ;  min 3 touching pivots to exist at all

# --- FALSE-BREAK VETO (the volume-validated break — best "is this break real" test in the corpus):
break = first CLOSE beyond the level since last touch
TRUE break requires (avg(vol,2 bars after) - avg(vol,15 bars before)) / 15-bar avg >= 0.30
#   a break without a 30% volume impulse is not a break; on failure the level is UN-broken
#   (state rollback — trivial in a state machine, impossible in a charting tool)
# retest = touch within TR/30 of the broken level, >= 3 bars after previous retest, pre-break only

# --- TESTED-ZONE ACCOUNTING (zone quality as an accumulated STATISTIC, not a creation property):
every k bars after creation (k = 15/20): if price inside box AND adverse-flow count >= m
   (>= 7 of last 15 bearish candles for a demand zone; or >= 10 of 20):
       zone.rejections += 1                     # a tally of SUCCESSFUL DEFENSES
# per-zone NET SIGNED DELTA: delta_z = sum(+vol bull candles) - sum(vol bear candles) over lifetime
# swing-volume strength ratio: vol[swing_bar]/rolling_max(vol,100) -> >=0.30 Strong | 0.20 High | 0.10 Balanced
# touch counting with HYSTERESIS: count += 1 when price enters band; must LEAVE before recounting
#   (a "touch" is a state-transition event — zero bar-close latency)
# false-BREAK TRAP DETECTOR via count hysteresis (B4): bull-zone count rose then fell back within
#   2 bars + local 5-bar close extreme => trapped break (break-traders are the exit liquidity)
```

**Mechanics:** Each touch implies another cluster of resting orders — the count *is* the liquidity estimate, known before price arrives (sizing weight). A zone's edge is its *demonstrated* defense record (rejection counters, net delta, volume tier), not its birth geometry. The false-break veto and count-hysteresis trap detector are structural (not oscillatory) break-quality tests.
**Zero-wait value:** Clusters rebuilt only on pivot events (every ~10–20 bars); between events per tick = "within tolerance of ≤6 levels?" with pre-computed weights; audits run on per-zone bar timers with running sums.

---
---

# SECTION 4 — CONFLUENCE & SCORING ENGINES

*Every engine here grades a candidate 0–100 (or 0–N) from bounded, precomputed factors at the decision event — never standalone triggers. Pattern to note: bounded additive scores + a margin/separation requirement + hard AND-gates as a separate permission layer.*

---

## 4.1 Six-Factor Liquidity-Sweep Score (0–100) — the reference scorer
`merged from: B1 §5.1 (Advanced Liquidity Sweep) ≡ B4 M4 (Mirage 5-term variant)`

```python
def sweep_score(bullish, pierce, touches):
    rng  = max(high - low, mintick)
    wick = (close - low)/rng if bullish else (high - close)/rng      # rejection ratio
    body = min(max(directional_body, 0)/rng, 1)                      # close-through body
    atr  = min(pierce / ATR, 1)                                      # depth in ATR units
    vol  = min(volume / (2*SMA(vol,20)), 1)                          # volume impulse (cap 2x)
    ema  = min(abs(close - EMA50)/(3*ATR), 1)                        # extension from trend (fuel)
    eq   = min(touches / 3, 1)                                       # equal-H/L cluster strength
    w = dict(wick=1.0, atr=1.0, vol=0.8, body=1.0, ema=0.6, eq=0.8)
    return 100 * sum(w[k]*c[k]) / sum(w.values())
# gates: >= 50 to signal ; >= 70 STRONG tier ; tiers -> position size
# Conservative preset -> weight wick/body (clean rejection); Aggressive -> vol/equal-cluster (flow)

# Mirage 5-term variant (same idiom, all ATR-normalized):
score = 100*(0.30*clamp(wick/ATR,0,1) + 0.25*clamp(reclaim/ATR,0,1) + 0.20*closePos
           + 0.15*clamp((vol/volMA21 - 1)/0.5, 0, 1) + 0.10*htf_bias)
```

**Mechanics:** Six mutually informative factors: how hard price rejected (wick), how deep it penetrated (pierce/ATR), how much volume the sweep carried, whether the close reversed through the level (body), whether price was 3σ+ extended from trend (mean-reversion fuel), and how many stops were resting there (touch count). ATR normalization makes every term regime-invariant; the preset-dependent weight vector is a transparent precision dial.
**Zero-wait value:** All inputs known at the sweep bar's close tick (or intrabar once volume/wick qualify); six divisions + one sum → compute per sweep event and size by tier in the same loop iteration.

---

## 4.2 JOAT 8-Pillar Bounded Score (100 points, margin requirement, separate hard gates)
`source: B4 S1 (JOAT "Prismatic Depth")`

```python
# eight pillars, each CLAMPED to [0, weight] (no input can dominate):
Structure(12): 10/10 pivot-chain direction + close beyond last pivot (BOS state)
Volume(12):    OBV slope: linreg(sign(delta_close)*vol, 20) > 0
Momentum(12):  PARTIAL CREDIT = (votes/3)*w from {KAMA21 dir, momentum-50 side, WPR ±40 zone}
Liquidity(12): same-bar sweep of last pivot: low < lastPivotLow and close > lastPivotLow (bull)
Volatility(12): ATR14/SMA(ATR,100) in [0.8, 1.6] (healthy vol) AND momentum votes >= 2
Session(14):   position vs daily-range midpoint; below-mid credit scales with |dist to mid|
HTF(14):       last-closed-4H close vs last-closed-4H EMA50 (confirmed idiom)
Delta(12):     cumDelta crosses its SMA(14) AND pressure = 40 + 35*volComp + 25*bodyComp > 50
signal_long = score_bull >= 70 AND (score_bull - score_bear) >= 20 AND gates
gates        = close > VWMA200 and ratchet_dir(10,3.5) == +1 and ADX >= 20 ; cooldown 5 bars
```

**Mechanics:** Three structural choices make this the strongest confluence design: (1) bounded additive scoring — every pillar clamped so correlated inputs cannot compound; (2) a **margin requirement** (bull − bear ≥ 20: "clearly wins", killing the mushy 60-vs-55 states); (3) hard AND-gates as a separate *permission* layer — the score decides quality, the gates decide permission. Partial-credit momentum (votes/3) is a smoothness trick worth stealing.
**Zero-wait value:** Eight bounded O(1) computations; total = 8 adds per tick; signal = 3 comparisons; the delta pillar consumes the native aggTrade CVD directly.

---

## 4.3 ICT 0–11 Zone Confluence with Mandatory Gates (+ the CISD bit)
`source: B3 §5.1 (ICT Validated SMC)`

```python
long_score = 2*(at active bull OB) + 1*(at active bull FVG)
           + 2*(at active bull OTE) + 1*(at un-retested bull breaker)
           + 1*(HTF aligned) + 1*(in killzone) + 1*(in discount)
           + 1*(swing structure bullish) + 1*(bullish CISD)
signal = (any zone touched) and score >= 4 and HTF_ok and CISD_ok and cooldown_ok
# CISD (change-in-state-of-delivery) = close beyond the open of the last opposite candle:
#   ONE stored float (lastBearishOpen) + ONE comparison — cheapest momentum-confirmation bit found
```

**Mechanics:** Zones (where) carry weight 2; context (when/why) carries 1; the signal is the intersection of a minimum score AND mandatory gates. The per-zone booleans are the same level-occupancy tests the order manager already runs — the confluence decision reuses existing state.
**Zero-wait value:** ~10 XOR/ADD ops on the confirmed bar; gates are 3 booleans; marginal cost of the confluence decision ≈ zero.

---

## 4.4 floop 0–14 Strength Score with Subtractive Chop Penalty
`source: B3 §5.3 (floop pro)`

```python
score = score_htf(1) + score_mtf(0..4: range-filter direction on 1m/5m/15m/1h/4h)
      + score_sens(0..3: multi-scale consensus §1.6c -> +2/+1)
      + score_ema(0..4: alignment + sign-agreement of ROC5/10/20: all three = aligned, fast only
                  = partial half-credit)
      + score_vol(0..2: percentile gate §1.23)
      - chop_penalty(1 per failed anti-chop filter: ADX>=20, ChoppinessIndex <= 61.8, cooldown>=5)
tiers: >= 11 HIGH | >= 8 MED | >= 6 LOW | else WEAK
```

**Mechanics:** The most granular integer score in the corpus. Two notable choices: momentum graded by *sign agreement of three ROC horizons* (three independent displacement windows, not an oscillator); and the chop penalty is **subtracted, not gating** — a signal firing against chop is downgraded, not deleted, preserving information while hard gates block the worst cases.
**Zero-wait value:** Online comparisons on the confirmed bar; the 14-point integer is the most informative quality scalar attachable to a trend-flip entry.

---

## 4.5 LTM Retest Score (0–100) with Sweet-Spot Depth Curve
`source: B4 S2 (Liquidity Trail Matrix)`

```python
# pullback depth into the 4-band ratchet stack (§1.12b), pending window 8 bars:
depthPts = {band1: 15, band2: 25, band3: 18, band4: 10}[deepest_band_touched]
#    NOTE the curve: band-2 scores HIGHEST — too shallow = no real pullback; band-4 = trend risk
candlePts = 20 if closePos > 0.7 else 12 if closePos > 0.5 else 5
volPts    = 20 if vol > 1.2*volBase else 12 if vol > volBase else 5
volBase   = SMA(vol,20)[1]          # SPIKE DOES NOT DILUTE ITS OWN BASELINE (self-non-diluting)
agePts    = 15 if 10 <= bars_since_flip <= 150 else 8 if < 10 else 5    # avoids new-flip & exhaustion
biasPts   = 20 if HTF aligned else 10 if neutral else 0
score = depthPts + candlePts + volPts + agePts + biasPts      # fire >= 80
reclaim = pending > 0 and close > band1 and close > open ;  cooldown 5 bars SHARED both directions
```

**Mechanics:** The depth curve {15,25,18,10} penalizes *both* trivial wicks and capitulation dips — the best retest stops at the second band. The `[1]`-shifted volume baseline fixes a subtle bug (comparing the spike bar to an average that already contains it); trend-age avoids both brand-new flips (no context) and ancient trends (exhaustion); one shared cooldown is an explicit anti-whipsaw device.
**Zero-wait value:** Five bounded O(1) components; depth = a pending integer with countdown; reclaim = crossing + candle-direction check (tick-acceptable).

---

## 4.6 Direction-Probability Engine (weighted score → probability, adaptive threshold, mandatory delta veto)
`source: B5 S1 (NEXT CANDLE PREDICTOR V4)`

```python
# seven 0-100 sub-scores (banded 100/85/70/50/25 per component):
longScore = .23*ST_trend + .18*MACD_g + .15*delta + .12*RSI_g + .12*stoch_g + .10*ADX + .10*volume
#   [zero-oscillator build: set the MACD/RSI/stoch grader weights to 0 and renormalize — see App. A]
longPct  = longScore / (longScore + shortScore) * 100      # softmax-like DIRECTION PROBABILITY

thr = 55 if ADX > 30 else 60 if ADX > 25 else 65 if ADX > 20 else 70
#   (strong trend = lower bar: continuation is the prior; weak trend demands 70%)

p = percentile_rank(ATR14, 100) ;  scale = 0.85 if p > 75 else 1.15 if p < 25 else 1.0
#   high-vol regimes RELAX the threshold (sizing handles width); low-vol STRICTER

delta   = V*((C-L) - (H-C))/(H-L)          # close-location volume delta (CVR-style)
deltaOK = sign(delta) == side and delta > EMA(delta,10)      # THE VETO — flow direction non-negotiable
PERFECT = ST_dir AND longPct >= thr*scale AND conf8 >= 5 AND volume >= 0.8*SMA(vol,20)
          AND momentum_side AND deltaOK
```

**Mechanics:** Three layered calibrations on a plain weighted vote: normalization to a direction probability (symmetric, bounded, "clearly wins" semantics); an ADX-adaptive fire threshold; an ATR-percentile regime multiplier. The mandatory delta veto is the design lesson: a perfect score cannot override flow direction — vetoes live in a different variable family than scores and cannot be gamed by correlated components.
**Zero-wait value:** Running scalars + a 100-deep ATR ring; the veto is a sign comparison; the delta term upgrades to exact signed aggTrade volume.

---

## 4.7 Eight-Component Weighted Score (0–100, no-family-dominance property)
`source: B2 §5.1 (Fibonacci "AI Score")`

```python
# component tiers in {3,5,7,8,10}; score = sum(w_k*c_k)/sum(w_k)
w = { momentum_hist:15, rsi_band:10, delta:20, obv_deriv:10, adx:10, structure:15, pressure:10, mtf:10 }
delta:     delta_norm > 0.3 -> 10 ; > 0.1 -> 7 ; < -0.3 -> 10 ; < -0.1 -> 7 ; else 3     # weight 20 (largest)
structure: >= 2 consecutive HH or LL -> 10 ; else 3
obv_deriv: |delta OBV(5)| expanding vs its own 5-bar lag -> 10 : 5
adx:      > 25 and rising(3) -> 10 ; > 20 -> 7 ; else 4
pressure: bullish candles in last 10 > 6 -> 10 ; < 4 -> 10 ; else 5
mtf:      3-TF alignment -> 10 ; else 3
#   momentum/oscillator grader rows (original weights 15/10): EXCLUDED per mandate — set to 0,
#   renormalize; the no-dominance property below is weight-structural and survives any weights
SIGNAL: score >= 75 AND regime not in SQUEEZE AND kill switch off
         AND volume > 1.2*SMA(V,20) AND close on the signal side of open
```

**Mechanics:** The design property: **no single family can carry the score** — with flow+structure maxed at (20·10+15·10)/100 = 35, at least three independent families must agree. Weights are a transparent precision dial; the score's *argument vector* (which components are low) drives partial sizing.
**Zero-wait value:** Eight maintained scalars + tiers + one weighted sum per candidate (event-driven).

---

## 4.8 Zone-Quality Graders (frozen at creation — the executor consults, never re-scores)
`merged from: B3 §1.10, §5.2; B2 §5.6`

```python
# FVG grade 0-10 (B3):
gap_atr = (top - bot)/ATR14
size_score = min(gap_atr/1.0, 1.0)                    # 1.0 ATR gap = full marks
disp_score = min((H[1]-L[1])/ATR14/2.0, 1.0)          # impulse-bar range in ATR units
vol_score  = min(volume[1]/SMA(volume,20), 2.0)/2.0
grade = min(10, (0.40*size_score + 0.35*disp_score + 0.25*vol_score)*10)   # >= 4 required to trade

# OB validation score /8 (B3): 2*sweep + 2*displacement(FVG within 6 bars) + 1*killzone
#   + 1*discount + 2*htf_aligned ;  emit if >= 3 ;  star tiers 3..5 (4..7 pts)
# per-zone weight from the volumetric grid (§2.4C): slice-POC volume share / absorption %

# Retracement-probability scorer (B2) — applied at level-approach events:
fibpos = 100 if price in ideal zone (long 38.2-50% of pinned swing; short 61.8-78.6%)
        = 60 if outside 0-38.2 / 78.6-100 ;  = 80 in the 50-61.8 equilibrium band
mtf = 100 if aligned else 30 ;  vol = 100 if V > 1.5*SMA else 70 if V > SMA else 40
rebond = 20 if a confirmed §2.10c rebound active else 0
P = 0.4*AI_score + 0.25*fibpos + 0.2*mtf + 0.1*vol + 0.05*rebond    # clip 0..100
confidence: >= 80 VERY HIGH | >= 65 HIGH | >= 50 MEDIUM | else LOW
```

**Mechanics:** A gap's *existence* is binary; its quality is not — size (vacuum left), displacement (violence of the creating impulse), participation (relative volume) predict respect-on-return. The OB score encodes mechanism (sweep+displacement, weight 2) vs context (time/zone/HTF, weight 1). The retracement scorer weights the full confluence score at only 40% — a perfect zone with a failing score never carries a trade.
**Zero-wait value:** All frozen attributes at creation; O(1) lookups at tap time; grades feed size tiers directly.

---

## 4.9 Veto Layers (hard environment kills — a veto cannot be gamed by correlated scores)
`merged from: B2 §5.4, §5.5; B4 S4; B3 §5.4; B4 M4`

```python
# composite kill switch (B2): evaluated once per candidate; existing positions unaffected
kill = (ADX < 18)                              # no trend strength at all
     or (volume < 0.5*SMA(volume,20))          # flow dried up to < 50% of normal
     or (squeeze active and not yet released)  # inside the coil — no entries
directional veto: delta_norm < -0.2 blocks BUYs ; > +0.2 blocks SELLs     # one side at a time

# strong-volume OVERRIDE (B4, the asymmetric gate): pass = vol >= 1.5*SMA20 ; strong = vol >= 2.0*SMA20
#   strong BYPASSES the trend filter: rare, expensive-to-fake signals veto cheap continuous filters
#   implement as: signal = breakout and (volume_ok and (trend_ok or strong_vol))   # OR inside the AND

# proximity (SNR) veto (B3): no buy within 2*ATR of nearest pivot high / no sell near pivot low
# both-sides sweep veto (B4): a bar raiding BOTH pools = volatility event, no direction -> ABORT
# market pressure composite (B2, permission gauge):
pressure = clip(0.4*imbalance + 0.3*ema_slope_norm + 1.5*(ADX-20) + 50, 0, 100)
imbalance = (cum_buy - cum_sell)/cum_total*100 ;  pressure_buy = pressure > 60 ; sell < 40
#   flow dominant (40%), slope scale-free (30%), dead market pinned to 50 by construction
```

**Mechanics:** Veto layers are the correct home for hard environment rules because each kill condition comes from a different variable family — a score can be gamed by correlated components, a veto cannot. The override asymmetry generalizes: any rare, expensive-to-fake event (volume, spread dislocation, queue imbalance) should be allowed to veto a continuous filter.
**Zero-wait value:** Maintained scalars; each veto is one comparison; the kill flag is the global "stop opening positions" bit.

---

## 4.10 ECHO — k-NN Historical Pattern Prior (statistical score with built-in horizon)
`source: B3 §1.1 (Historical Pattern Projection)`

```python
W, N, TOPK = 30, 500, 3
def fingerprint(closes):                    # z-scored 30-bar window (shape only: level & scale removed)
    w = closes[-W:] ;  return (w - w.mean())/max(w.std(), 1e-9)
znow = fingerprint(closes)
for k in range(N - W):                      # self-normalized library windows
    r = pearson(znow, fingerprint(closes[k:k+W]))
    outcome = (closes[k+W+20] - closes[k+W])/closes[k+W]*100      # realized 20-bar forward move
    scores.append(((r+1)/2*100, outcome, k))
top = sorted(scores, reverse=True)[:TOPK]
bias = mean(o for _, o, _ in top)
if min(match scores) >= 80 and abs(bias) > 0.5:                   # all top-3 >= 80 AND |bias| > 0.5%
    ghost = best_window_forward_path * (price/base)              # conditional-expectation template
    cone  = ATR14 * (1 + 0.1*t)                                  # expanding uncertainty band
```

**Mechanics:** A directional *prior* with an explicit 20-bar horizon — no oscillator in the corpus provides that. Requiring all top-3 matches ≥ 80% correlation plus non-trivial mean forward bias filters "shape matches, no edge" hits; the ghost path is a conditional-expectation template, not a forecast.
**Zero-wait value:** Ring buffer of 530 closes; one 500×30 batched correlation per confirmed close (tens of µs); top-k in a heap; fires only on confirmed bars — no lookahead by construction (the library is history).

---

## 4.11 Online Naive-Bayes Order-Flow Classifier (probabilistic grading + self-audit)
`source: B7 W1 (Viprasol)`

```python
# features per bar (per-tick in port):
delta = volume*((close-low) - (high-close))/(high-low)     # wick-split -> replace w/ native delta
CVD += delta
cvdRoc   = (CVD - CVD[14])/(|CVD[14]| + eps)
priceRoc = (close - close[14])/close[14]
slopeR   = linreg(CVD,10,0) - linreg(CVD,10,1)
F1 = z50(cvdRoc) ;  F2 = z50(priceRoc - cvdRoc) ;  F3 = z50(slopeR)     # rolling 50-bar z-scores

# ONLINE TRAINING — running sums only, zero stored samples; label from bar[1] (realized):
Bull = priceRoc > 0 and cvdRoc > 0 ;  Bear = both < 0 ;  Diverged = otherwise   # first-class NO-TRADE
per class c: (n_c, sum F_k, sum F_k^2)  ->  mu_ck, sigma_ck ;  prior_c = n_c/sum(n_c)
posterior_c = prior_c * prod_k Gaussian(F_k; mu_ck, sigma_ck) / normalizer
warmup at >= 100 labeled bars

long  = posterior_Bull >= 0.70 and close > EMA50 and CVD > CVD[1]      # short mirrored
tiers: posterior >= 0.85 high / >= 0.75 mid ;  size ∝ posterior_Bull - posterior_Bear
self-audit = rolling hit-rate of argmax-posterior[1] vs realized class[0]   # drift monitor
```

**Mechanics:** The label rule is the heart: *bullish* = price and CVD rising together; *diverged* = they disagree — an explicit no-trade class, not a fallback. The posterior is continuous confidence in [0,1], so the engine sizes by probability and degrades detectably (self-audit decay = regime statistics shifted; the running sums adapt, the audit says how fast).
**Zero-wait value:** 9 running sums + 3 z-windows + 3 Gaussian PDFs — O(1) per tick, no arrays, no training phase. On a tick feed the CVD is *exact* (aggressor flag), making the classifier strictly sharper than the bar version; the threshold can be crossed intrabar.

---

## 4.12 Measurement-Driven Meta Layer (per-setup scoreboards, regime-grid R-monitor, per-level hit-rates)
`merged from: B5 S3, W10; B6 S4; B5/B4 win-accounting`

```python
# (a) PER-SETUP SCOREBOARD + ARBITER (B5): N independent setup state machines under one gate
state per setup: off | dormant | forming | long | short
fire gate: room (openTrades < maxOpen) and cooldown and dirOk (not oneWay OR same-direction)
counters per setup: fired, reachedTP1, reachedTP2, reachedTP3, stop, expired
->TP1% = cTP1/cFired (display greyed below minSamp = 10)      # live A/B edge measurement per setup
SELECTIVE gating (documented negative result): volume REQUIRED for VWAP/EMA/sweep setups;
   deliberately OFF for break-retest / divergence / ORB (a valid retest is often quiet)

# (b) REGIME-GRID R-MONITOR + SELF-ADAPTING GAIN (B5):
cell = erBin(ER)*3 + volBin(ATR/ATR100)          # 3x3 grid: chop/mixed/trend x low/norm/high
EWMA(alpha=0.2) of realized R per cell; rolling 20-signal winRate, avgR, minRun (max DD in R units)
if avgR(20) < 0.0 and >= 5 signals since last step: Q += -0.05 if Q > base else +0.05 ; clamp [0.1,0.9]
elif avgR(20) > 0.7: freeze stepping                          # edge is good — stop touching it

# (c) PER-LEVEL HIT-RATE (B6): for each ORB extension level (0.382/0.618/1.0 x range):
track day-reached flags across last N days -> "reached on X% of sessions" per level
#   a level at 80% reach = near-certain target for resting limits; 15% = lottery ticket
```

**Mechanics:** The corpus's only *measurement-driven* controls: component-level edge accounting (which setups actually convert → size or disable them), regime-conditioned performance (9 cells of EWMA'd R with a clamped, cooldown-protected gain nudging the engine's own parameters), and per-level binomial statistics that decide which levels deserve resting orders. The selective-gating rationale is itself a documented negative result: not every setup wants the same gate.
**Zero-wait value:** Counters and EWMA scalars updated on close events; the gain step is the only writer to engine parameters, clamped and rate-limited.

---

## 4.13 Structure × Flow AND-Gates (the "tape alignment" pattern)
`merged from: B1 §5.3 (confBull); B2 §5.3 (7-factor re-entry); B3 §5.4 (reason-reporting gate)`

```python
# (a) confBull (B1) — five independent regime facts from five different scales/families:
confBull = (supertrend_flip OR (supertrend_flip[1] AND donchian_was_bear))    # structure EVENT
         AND momentum_sign AND momentum_slope                                  # (grader terms per App. A)
         AND ema150 > ema250                                                   # long-scale order
         AND hma55 > hma55[2]                                                  # medium-scale slope
         AND donchian30_state > 0                                              # 30-bar regime
# (b) 7-factor pullback re-entry (B2) — the cross *times* the state; the state *permits*:
entry_LONG = cross_up(close, ZLEMA70)            # timing: pullback just ended
         AND trend_state == +1                   # permission: max-ATR hysteresis state (§1.13)
         AND MTF_votes >= 3/5 AND close > open   # scale agreement + candle direction
         AND ZLEMA70 rising
         AND |close-open| > 1.1*avgBody(70)      # one-sample significance test on the re-entry bar
# (c) explainable gate (B3): AND-chain of 7 online filters; on a BLOCKED signal report pass-count
#     and failing factors ("Buy Blocked (5/7)") -> post-mortem filter attribution at zero extra cost
```

**Mechanics:** The cheapest high-precision pattern: an event (flip/cross) evaluated only against a cached multi-family AND-chain — the cross is the *timing*, the state is the *permission*. The `(flip[1] AND regime_was_opposite)` clause catches the one-bar-late flip the faster regime already pre-signaled; the body-significance term demands the re-entry be a real move; the reason-reporting variant makes the filter set auditable.
**Zero-wait value:** All factors are maintained scalars/booleans; evaluation only on flip events (event-driven, not per-tick); the blocked-reason log line is built only on rare blocked candidates.

---
---

# APPENDIX A — COMPLIANCE AUDIT (final-check dispositions)

| Check | Disposition |
|---|---|
| **Repainting / lookahead** | ZERO. All higher-timeframe values are last-**closed**-HTF-bar values via in-process resampling of the 1m feed (§0.2-2, §1.15). Confirmed pivots define levels and never re-classify; forming swings only gate (§2.1A). Every zone/level/box is frozen at creation; lifecycles only move forward (FRESH→…→consumed). Frozen pending templates and cached TF votes are the only cross-bar state, both timestamped. |
| **Lagging-oscillator crosses** | ZERO as triggers/engines. **Excluded outright:** the 7-band ATR-normalized MACD-derivative regime machine (MACD-core); RSI 70/75/80 (30/25/20) take-profit ladders from five batches (substituted by ATR-extension / R-multiple / dynamic-band ladders in §3.4 and the band-TP in §3.4f); oscillator-extreme reclaim entries; pure oscillator popcount votes (5-oscillator and 5-indicator counters — their breadth idea survives via the multi-family scores §4.2/§4.4/§4.7); EMA/MA slow crosses (incl. the 50-period ALMA close/open realization, §1.14 note); oscillator-run zone construction (subsumed by absorption/climax + dry-bar detection). **Retained, with justification:** (i) oscillator-**space ratchet machines** (§1.10) — the trigger is a break of a self-volatility-scaled ratcheted band (hysteresis state flip with a neutral-zone gate), categorically not a threshold cross; (ii) bounded **grader** rows inside composite scores (§4.6/§4.7) — ≤20%-weight bounded inputs that can never independently trigger; each scorer carries a zero-oscillator build (set grader weights to 0, renormalize — the no-dominance/margin properties are weight-structural); (iii) divergence-**at-extreme** traps (§2.13) — fractal-pivot confirmation machinery, not crosses. |
| **Source-platform syntax** | ZERO. All logic re-expressed in the Python pseudo-code shown; indexing conventions and helper functions defined once in §0.2; no plotting/label/table/dashboard code carried over; alert conditions converted to boolean predicates. |

**Additional invariants:** no derivatives/leverage logic anywhere; fixed-percentage risk ladders excluded (structure retained in ATR-mapped form, §3.4d); same-bar TP/SL ambiguity resolved SL-first in backtests and by event chronology live (§3.5).

---

# APPENDIX B — INTEGRATION BLUEPRINT (layered composition, all modules O(1) per tick)

```
L0 REGIME (per symbol)     vol state vector (§3.1, §1.23) · TQI/effAtr (§1.9) · no-trade kills (§1.23)
                           MTF vote table + grace (§1.15) · direction gates (§1.23) · session object (§1.17)
L1 TREND / FAIR VALUE      ONE ratchet family as primary: TQI-asymmetric ST (§1.9) | LTM 4-band stack
                           (§1.12b) | KHST (§1.4) | loglin channel (§1.3a) — each supplies direction,
                           confidence scalar, and frozen levels. Oscillator-space machines (§1.10) as
                           freshness gates; profiles (§1.18) + premium/discount arrays (§1.19) as surfaces.
L2 STRUCTURE (1m closed)   swing feeds (§2.1A) -> structure FSM (§2.1B) -> TJR pipeline (§2.1C);
                           zone registry: OB (§2.4), FVG/IFVG/BPR (§2.3), S/D-POI (§2.4C),
                           delta zones (§2.5), sweeps/EQ (§2.2), clusters (§3.8)
L3 SIGNAL (event)          trigger (§2.x) -> direction gate (L1) -> confluence (§4.1-4.8) -> vetoes (§4.9)
                           -> size = risk$/|entry-SL| x tier multipliers (§3.6)
L4 RISK (frozen at entry)  SL policy (§3.3) ; TP ladder (§3.4) ; BE/caution/partials/re-anchor (§3.5)
                           trailing engines (§3.2) once TP1 books
L5 META (event)            scoreboards, regime-grid monitor, hit-rates (§4.12) ; level retirement (§3.7)

TICK/CLOSE SPLIT           aggTrade: forming-close state (khma, ratchets, CVD, tap tracking, band TP,
                           live body tests) — continuous, never commits alone.
                           1m close: structure events, zone transitions, signal commits, risk freeze.
                           This split IS the zero-wait property: nothing that can change within a bar
                           is ever used as a trade decision, yet every decision object is a frozen
                           level the tick path can act on the instant it prints.
MAKER-SIDE RESTING LEVELS  sticky anchor ± hold (§1.24) · FVG CE + slice midlines (§2.3/§2.6) · OB POC
                           slice + equilibrium (§2.4) · delta-zone midlines (§2.5) · PVP/fib arrays
                           (§1.19) · POC/VAH/VAL (§1.18) · coil watch-box edges (§1.22) · break-to-line
                           midpoints (§3.7) — all known in advance; the taker fast path manages entries.
```

---

# APPENDIX C — BOUNDED-MEMORY MASTER TABLE (hard caps; FIFO eviction; 24/7-safe)

| Registry | Cap / TTL (source-optimal) |
|---|---|
| Delta/CVD zones | ≤ 8, far-edge close death |
| FVG inventory | ≤ 12 active / ≤ 2+2 inverse per side; 50-bar distance rule, 220-bar TTL |
| Order blocks / iOB | ≤ 10/side (FIFO) — ≤ 150 with 300-bar TTL in the iOB variant; ≤ 6 (TJR) |
| S/D POI zones | ≤ 8/side (ATR99) · ≤ 20/side (ATR50) · ≤ 20/side + 2·ATR dedup |
| Liquidity pools | ≤ 25/side (21/21) · ≤ 12/side (8/8) · levels ≤ 80 bars old |
| S/R clusters | top 5–6, nested suppression; ≤ 21 levels (10% window) |
| Trendlines / chains | violation budget ≤ 0–2; 500-bar TTL |
| Sweep pendings | 13-bar expiry; Reaper confirm ≤ 3 bars; debounce 10 bars |
| Zone/coil watches | 10–15 bar expiry; MAX_VIOLATIONS 2 |
| ORB cycles | ≤ 6/day/direction; one fire (single-break variant) |
| Trade gates | cooldown 5–10 bars (shared across directions); maxOpen 1; EOD force-flat |
| Profile windows | 24–500 bins/segment, segment cap 500 bars; ring 530 closes (ECHO); 1000-bar percentile ring |
| Stops optimizer | N = 5 parallel exit FSMs |

---

*Master file generated by consolidating batches 1–7 under deduplication, strict four-category categorization, and the final compliance check (Appendix A). Every entry is O(1) per tick unless explicitly noted, consumes only {1m klines, aggTrade, bookTicker}, and commits decisions exclusively on closed-bar state or frozen-level crossings.*
