# HFT Edge Extraction — Batch 3 (20 files)

Source set: the 20 Pine v5/v6 indicators in `/home/user/uploads/` (batch 3). All concepts below were
reverse-engineered from the actual math in the scripts. Raw Pine/MQL is intentionally **not** reproduced;
each concept is given as Python pseudo-code or closed-form math, the mechanics in technical English, and
the reason it transfers to a **zero-wait, tick-based engine** (Binance Spot: `aggTrade`, `bookTicker`,
1m `kline` stream).

---

## Red-line exclusions applied (same policy as batches 1–2)

| # | Red line | How it appears in this batch | Disposition |
|---|----------|------------------------------|-------------|
| 1 | Repainting / lookahead | `request.security(..., lookahead=barmerge.lookahead_on)` in: FLI (PVP fib), floop pro (prior-period pivots), HADYAN (daily pivots), Infinity & Sniper (`securityNoRep1` MTF + prior-day H/L/C), ICT Validated SMC (PDH/PWH), Institutional Flow MMDV (MTF H/L + 5-TF MACDV dashboard), ICT Master Suite (PBH/PBL) | Mechanism **excluded**; where the level is simply "previous confirmed period H/L/C" the *level* is salvageable (noted per file) |
| 2 | Lagging indicators used for slow crosses | EMA21/50 cross (HADYAN filter), EMA ribbon EMA11/EMA34 cross (IFT MMDV signal), EMA10/20 "trend catcher" (Infinity), EMA60/200 cross (floop, only as a score component), standard MACD 12/26/9 as trigger | Excluded as *triggers*; kept only where used as a state/position filter inside a non-lagging core (noted) |
| 3 | GUI / visual code | Dashboard tables, Telegram banners, bar/line/box/label drawing, stoch mini-charts, HTF "ghost candles", theme palettes, color gradients | Excluded entirely. `alert()` **conditions** were read as logic where they encode a real rule (e.g. S/R break detection in Infinity) |
| 4 | Derivatives logic | None found in this batch (leverage/liquidation/futures) | n/a |

Files that turned out to be duplicates / near-duplicates:
- **`Fresh Algo (1).txt`** = *Fresh Algo v24*: line-level diff vs v25 shows only version strings, label text
  and removal of cosmetic input-gating conditionals. **Math core identical** — extracted once.
- **`Haper Trend.txt`** and **`Fresh Algo.txt`** are the same codebase (LuxAlgo HyperTrend + "Money
  Moves" TrendVR mash-up) with different default parameters — extracted once, deltas noted.

---

## §1 Wildcard / innovative edges

### 1.1 ECHO — k-NN pattern matcher on z-scored close fingerprints
**Source:** `Historical Pattern Projection.txt`

The strongest wildcard of the batch. Build a 30-bar fingerprint of recent closes, standardize it, and
correlate it against a rolling library of 500 self-normalized historical 30-bar windows. The top-3
matches' *realized forward outcomes* set direction; the matched history, price-scaled, is projected
forward as a "ghost path" with an ATR-expanding cone.

```python
W, N, TOPK = 30, 500, 3
def fingerprint(closes):                      # last W bars, z-scored
    w = closes[-W:]
    return (w - w.mean()) / max(w.std(), 1e-9)

def echo(closes, atr14, price):
    znow = fingerprint(closes)
    scores = []
    for k in range(N - W):                    # candidate window, self-normalized
        zc = fingerprint(closes[k:k+W])
        r  = pearson(znow, zc)
        outcome = (closes[k+W+20] - closes[k+W]) / closes[k+W] * 100.0   # 20-bar forward move %
        scores.append(((r + 1) / 2 * 100.0, outcome, k))
    top = sorted(scores, reverse=True)[:TOPK]
    bias = mean(o for _, o, _ in top)
    if min(s for s, _, _ in top) >= 80 and abs(bias) > 0.5:        # score >= 80, |bias| > 0.5%
        base = closes[best_k + W]
        ghost = history[best_k+W : best_k+W+20] * (price / base)   # price-scaled projection
        cone  = atr14 * (1 + 0.1 * t)                              # expanding band vs path index t
        return dir(sign(bias)), ghost, cone
# trade at close: entry band 0.25*ATR14 wide, SL 1.5*ATR14, TP 1/2/3*ATR14
```

**Mechanics.** The z-score normalization removes level and scale, so the matcher is comparing *shape*
only (local momentum texture). Requiring the top-3 all ≥ 80% correlation plus a non-trivial mean forward
bias (>0.5% over 20 bars) filters out "shape matches, no edge" hits. The ghost path is not a forecast per
se — it is a *conditional-expectation template*: given 30 bars that look like this, this is what followed
in the 3 best historical analogs, rescaled to current price.

**Why tick-powerful.** The fingerprint is a 30-dim vector over 1m closes; the correlation test is a
single 30-dim dot product (sub-µs in numpy). On each confirmed 1m close you rebuild the library in O(1)
amortized (ring buffer) and evaluate in O(N·30) ≈ 15k flops — trivially inside a 1s budget, and the
feature is a pure function of the kline stream (no bar-state ambiguity). It gives a *directional prior
with a built-in horizon* (20 bars) that no oscillator in this batch provides.

---

### 1.2 Harmonic XABCD completion detector on a rolling zigzag
**Source:** `Infinity and Sniper by Leo.txt`

Four parallel zigzags (pivot length 24/24/35/35) keep the last 6 swing points X-A-B-C-D. On every new
swing the three leg ratios are computed and matched against six harmonic templates with ±18% tolerance:

```python
TOL = 0.18                       # err_min = 1-TOL, err_max = 1+TOL
PATTERNS = {                       # (xab range, abc range, xad range)
  "Gartley":   ((0.588, 0.648), (0.382, 0.886), (0.866, 0.886)),
  "Crab":      ((0.382, 0.618), (0.382, 0.886), (1.802, 1.902)),
  "DeepCrab":  ((0.886, 0.936), (0.382, 0.886), (1.802, 1.902)),
  "Bat":       ((0.382, 0.550), (0.382, 0.886), (0.886, 0.886)),
  "Butterfly": ((0.755, 0.816), (0.382, 0.886), (1.272, 1.272)),
  "Shark":     ((0.382, 0.618), (1.130, 1.618), (1.000, 1.130)),
}
xab = abs(b - a) / abs(x - a)
abc = abs(c - b) / abs(a - b)
xad = abs(d - a) / abs(x - a)
# structural guards:
#   B must be strictly inside (min(x..d), max(x..d))
#   ABCD leg direction must be consistent (all up / all down)
risk, reward = abs(b - d), abs(c - d)          # stop beyond B, target at C
```

**Mechanics.** Classic harmonic geometry (PRZ at D), but implemented *statefully on a live zigzag* with a
tolerance band rather than exact ratios — which is what makes it fire on real noisy data. The tolerance
is applied multiplicatively per ratio; B-inside-extremes and ABCD-direction guards kill degenerate
matches. Risk/reward is fixed by the template (stop at B, target at C), so the detector directly emits a
complete trade spec.

**Why tick-powerful.** A zigzag over 1m extremes is a 2-state machine (direction ± extreme); ratios are
O(1) on each new swing; the six template checks are six interval tests. Completion (D leg) is detected at
the swing — no waiting for a full bar to "confirm the pattern" the way classical harmonic tools do, and
no repaint because the swing is defined by 24 confirmed 1m bars.

---

### 1.3 ATR-band Ichimoku — tenkan/kijun/spanB as chandelier-ratchet averages
**Source:** `Fresh Algo.txt` (v25)

All three "Ichimoku" lines are built from the same primitive: a Keltner-style band ratcheted around
hl2 at `k · ATR50`, then averaged over its running max/min envelope. The `length` argument is
**ignored by the code** — the lines differ only by the ATR multiplier (3×/7×/10×):

```python
def chandelier_avg(mult):
    atr = ATR(50)
    up, dn = hl2 + atr*mult, hl2 - atr*mult
    upper = min(up, upper_prev) if src_prev < upper_prev else up    # only ratchels down
    lower = max(dn, lower_prev) if src_prev > lower_prev else dn    # only ratchels up
    state = 1 if src > upper else 0 if src < lower else state       # breakout state
    spt   = lower if state == 1 else upper                          # active side
    maxv  = max(src, maxv_prev) if (cross_up(spt) or state == 1) else spt
    minv  = min(src, minv_prev) if (cross_dn(spt) or state == 0) else spt
    return (maxv + minv) / 2

tenkan = chandelier_avg(3); kijun = chandelier_avg(7); spanB = chandelier_avg(10)
senkouA = (tenkan + kijun) / 2
```

**Mechanics.** The ratchet band is a *chandelier that only tightens from the outside*: the upper bound can
only move down while price is below it, the lower bound only up while price is above it. Averaging the
running max/min of the band around it yields a trend line whose *speed is volatility-locked* (ATR50) and
whose *separation is scale-free* (3/7/10× the same unit). It behaves like Ichimoku (stack of
increasingly smoothed lines, senkouA cloud) but adapts to crypto's fat-tailed vol where fixed-period
extremes misfire.

**Why tick-powerful.** Three scalar recurrences per tick (band, state, envelope) — no buffers, no
lookback, trivially online. ATR50 on the 1m stream is the only state. The 3×/7×/10× stack gives a
cheap multi-scale trend read (fast/mid/slow) with one volatility parameter.

---

### 1.4 KHST — Kalman-filter price smoothed into a SuperTrend (Kalman Hull Supertrend)
**Source:** `Indicator GG Beluga KHST.txt`

A one-dimensional Kalman smoother (measurement noise R = "measNoise", process noise Q = "procNoise")
replaces the EMA in a DEMA/Hull construction ("KHMA"), and a ratcheted SuperTrend is run **on the
smoothed price** instead of raw close:

```python
def kalman(x, R, Q, state):
    est, err = state
    pred_err = err + Q
    K = pred_err / (pred_err + R)
    est = est + K * (x - est)
    err = (1.0 - K) * pred_err
    return est, (est, err)

def khma(src, R, Q):
    a = kalman1d(src, R/2.0, Q)          # fast pass (R/2)
    b = kalman1d(src, R,     Q)          # slow pass
    return kalman1d(2*a - b, math.sqrt(R), Q)   # DEMA combo, re-smoothed

khma = khma(close, R=10.0, Q=0.010)                       # per-symbol-class presets
dir, stline = supertrend_ratchet(khma, ATR_len=12, factor=1.7)
```

**Mechanics.** R plays the role of "how much to trust the raw tick" — large R = heavy smoothing = slow
line; Q = allowed drift of the underlying. Because the Kalman gain K adapts every bar, the smoother
sharply tracks during displacement and flattens in chop, which is exactly what a SuperTrend source wants:
fewer whipsaw flips in ranges, faster flips in real moves. The trend line is anchored to `khma ±
factor·ATR`, ratcheted in the standard way (band only tightens in the favorable direction).

**Why tick-powerful.** The Kalman recursion is 4 float ops per update — the cheapest adaptive smoother
that exists. It runs natively on the *forming* 1m close (aggTrade last price), so the trend state is
continuous and zero-wait, while the committed flip is still defined on the confirmed close. The R/Q pair
is a 2-D dial that subsumes the "length" parameter of every MA in the batch (and the preset table in
Appendix A gives calibrated values per asset class).

---

### 1.5 Early Flip — volatility-adaptive slope-acceleration trigger
**Source:** `Indicator GG Beluga KHST.txt`

Fires **before** the SuperTrend flips, as a heads-up "pending" signal:

```python
slope = khma - khma[1]
accel = slope - slope[1]
atr_base  = SMA(ATR14, 200)                 # long-term volatility baseline
vol_ratio = ATR14 / max(atr_base, eps)
accel_norm = accel / max(ATR14, mintick)
thresh = base_thresh * (1.0 + (vol_ratio - 1.0) * K)    # base 0.08–0.14 per class, K=1.0
early_buy  = slope > 0 and slope[1] <= 0 and accel_norm >  thresh
early_sell = slope < 0 and slope[1] >= 0 and accel_norm < -thresh
```

**Mechanics.** Three requirements: (a) first bar the smoothed slope has turned (sign change of the
*velocity*), (b) the acceleration (second difference) is materially positive, (c) the normalized
acceleration clears a threshold that **scales linearly with the current volatility regime** (200-bar ATR
baseline). In a vol expansion, a "normal" acceleration is noise, so the bar to clear rises; in a vol
collapse the bar falls and small genuine accelerations count. This is a self-tuning event detector on
the trend's second derivative — the only second-derivative trigger in the whole three-batch corpus.

**Why tick-powerful.** O(1) state (khma, ATR14, 200-bar ATR SMA). Because the threshold is computed from
live volatility, one code path works across symbols and regimes — no per-market retuning. The
pending/NOW split (early = alert only, flip = trade) maps directly onto a tick engine's two-level
signal design: pre-position on pending, execute on flip.

---

### 1.6 Pair-enumeration "max-touch" trendlines
**Source:** `Infinity and Sniper by Leo.txt`

Keep the last 7 pivot highs (21/21 confirmed) and 7 pivot lows. Enumerate **all pairs** (n·(n−1)/2
candidate lines) and select the line that *violates the fewest subsequent pivots*, with more touches
winning and, on ties, the higher future value winning:

```python
pivots = last_7_confirmed_pivot_highs      # (t_i, p_i)
best, best_cnt = None, -1
for i, j in combinations(range(len(pivots)), 2):
    line = line_through(pivots[i], pivots[j])
    cnt = sum(1 for (t, p) in pivots if line.value_at(t) >= p)   # top line: must stay ABOVE
    if cnt > best_cnt or (cnt == best_cnt and line.future_value > best.future_value):
        best, best_cnt = line, cnt
# bottom line: mirror (line must stay BELOW all pivots)
```

**Mechanics.** Unlike "last two pivots" trendlines (one touch, instant obsolescence) this is the
*support-maximizing* line through the recent pivot set — the line that best "explains" the swing
structure, in the same spirit as the violation-tolerant trendline of batch 2 (ExProfit) but with exact
pair enumeration and a touch-count score instead of a violation budget. It is redrawn only when a new
pivot is confirmed.

**Why tick-powerful.** ≤21 line fits and ≤21 touch tests per new pivot — negligible. The selected line is
a (slope, intercept) pair updated event-driven (on pivot confirmation), so the level is always available
to the tick executor with zero recomputation cost between pivots.

---

### 1.7 MACDV — ATR-normalized MACD with a 7-band state machine
**Source:** `Institutional Flow Toolkit MMDV.txt` (dashboard core)

```python
macdv = (EMA(close, 14) - EMA(close, 26)) / ATR(close, 26) * 100.0
signal = EMA(macdv, 9)
if   macdv > 150:            state = "WAIT-continue/reversal (climax)"
elif macdv > 50:             state = "BUY G0" if macdv > signal else "BUY RETEST"
elif macdv < -50:            state = "SHORT G0" if macdv > signal else "SHORT RETEST"
elif macdv < -150:           state = "WAIT-continue/reversal (climax)"
else:                        state = "SIDEWAYS"
```

**Mechanics.** Dividing the MACD by ATR makes the oscillator *scale-free* — the 50/150 thresholds mean
something identical on a 30k coin and a 1.2 FX pair. The ±50 band is a "no-momentum" dead zone; ±150 is
a climax zone where continuation is exhausted. Inside the momentum band, position relative to its own
9-EMA separates **G0** (fresh breakout of the oscillator — first bars of the move) from **RETEST**
(oscillator pulled back — second entry). This is the only oscillator in the corpus with an explicit
*entry-quality* classification rather than just a direction.

**Why tick-powerful.** Fully online (3 EMAs + 1 ATR + 1 comparison). The 7-state output is a compact
market-regime label that can gate higher-conviction entries (G0) vs. lower (RETEST) without any
bar-counting logic.

---

### 1.8 Six-phase MA-arrangement state machine
**Source:** `Institutional Flow Toolkit MMDV.txt` (dashboard core)

```python
C, M1, M2 = close, EMA(close, 50), EMA(close, 200)
if   C>M1 and C>M2 and M1<M2: phase = "ACCUMULATION"     # above both, cross unconfirmed
elif C>M1 and C>M2 and M1>M2: phase = "RUNNING UP"       # full trend
elif C<M1 and C>M2 and M1>M2: phase = "RE-ACCUMULATION"  # pullback inside uptrend
elif C<M1 and C<M2 and M1>M2: phase = "DISTRIBUTION"     # below both, cross unconfirmed
elif C<M1 and C<M2 and M1<M2: phase = "RE-DISTRIBUTION"  # bounce inside downtrend
else:                        phase = "NO-TRADE WAIT"     # C>M1, C<M2, M1<M2 (whipsaw state)
```

**Mechanics.** Six of the eight possible arrangements of {price vs M1, price vs M2, M1 vs M2}; the two
remaining are the symmetric "C>M1, C<M2" whipsaw states, one of which is labeled no-trade. The taxonomy
separates *trend* (M1>M2) from *position within trend* (price vs M1), and treats "price above both but
cross not yet confirmed" (accumulation) as a distinct, pre-signal phase.

**Why tick-powerful.** Six boolean tests per tick. It is a pure *context* state: it never generates a
signal by itself, but it tells the executor which of {load, add, hold, stop-adding, exit-setup,
stand-aside} applies — exactly the decision a tick engine needs to size and time orders within a
swing.

---

### 1.9 PREDICTUM — Fibonacci-decaying TP ladder (asymptote ≈ 2.618R)
**Source:** `Indicator MM ALGO PREMIUM for TradingView.txt`

```python
tp[1] = entry + 1.0 * R
tp[n] = tp[n-1] + (tp[n-1] - entry) * 0.618      # each step = 61.8% of the previous step
# tp: 1R, 1.618R, 1.99R, 2.215R, 2.35R, ... -> asymptote at 1/(1-0.618) = 2.618R
```

**Mechanics.** Standard R-multiples assume each take-profit adds a *full* R of extra work; PREDICTUM
assumes diminishing marginal effort — each new target only extends 61.8% of the last leg, so the ladder
converges at 2.618R (a golden-ratio number, no coincidence). The ladder encodes the empirical shape of
moves: most of the profit is captured early, the tail is cheap to hold but unlikely to be reached in
full.

**Why tick-powerful.** Closed form: `tp[n] = entry + R · (1 − 0.618^n)/(0.382)`… computable O(1) per
level at entry time; the engine just registers N limit orders. No state, no re-computation, no waiting.

---

### 1.10 FVG quality grading (size + displacement + volume, 40/35/25)
**Source:** `FVG Sniper.txt`

Every 3-bar FVG is scored 0–10 at creation:

```python
gap_atr = (top - bot) / ATR14
size_score  = min(gap_atr / 1.0, 1.0)                 # 1.0 ATR gap = full marks
disp_score  = min((H[1] - L[1]) / ATR14 / 2.0, 1.0)   # impulse bar range in ATR units
vol_score   = min(volume[1] / SMA(volume, 20), 2.0) / 2.0
grade = min(10, (0.40*size_score + 0.35*disp_score + 0.25*vol_score) * 10)
# creation filters: gap_atr >= 0.25 and body_ratio[1] = |c-o|/(H-L) >= 0.45
```

**Mechanics.** A gap's *existence* is binary; its *quality* is not. Size (how much of a vacuum was left),
displacement (how violent the impulse that created it was) and participation (relative volume) are the
three quantities that predict whether price respects the gap on return. The 0.45 body-ratio gate excludes
gaps created by weak doji-like impulses.

**Why tick-powerful.** All inputs are known the moment the middle bar confirms — the grade is frozen at
creation, O(1) to compute, and becomes a static attribute of the zone object that the tick executor
consults at tap time (see §3.7 rejection rule, which requires grade ≥ 4).

---

### 1.11 Pivot-cluster S/R — channels anchored at the newest pivot
**Source:** `Infinity and Sniper by Leo.txt` ("Support Resistance - Dynamic by leo")

```python
on each new confirmed pivot (10/10):
    cwidth = (highest(284) - lowest(284)) * 0.10       # channel half-width = 10% of 284-bar range
    anchor = pivot extreme (rebuild ALL levels on every new pivot)
    upl, dnl = anchor + cwidth, anchor - cwidth
    cluster = [p for p in all_other_pivots_in_lookback
               if p.extreme in [dnl, upl] and p not yet "used"]
    if len(cluster) >= 2:
        emit S/R level at anchor; mark anchor+cluster pivots as "used"
    # else: discard (single-touch pivot = noise)
# level break detection: close crosses level (resistance_broken / support_broken)
```

**Mechanics.** A level is only a level if *multiple* pivots agree — the "channel" is an ATR-independent
price band (10% of the 284-bar range) around the newest pivot, and the level fires when ≥2 older pivots
sit inside it. The "used" flag prevents the same pivots from re-creating duplicate levels on the next
pivot (clusters are disjoint). Rebuilding on every pivot keeps the level set strictly fresh.

**Why tick-powerful.** Level set is rebuilt O(pivots) only on pivot confirmation (rare event); between
events the executor holds a static list of levels. The 284-bar range normalization makes the cluster
tolerance auto-scale with the instrument's recent amplitude.

---

## §2 Macro directional filters (low-lag trend math)

### 2.1 KHST MTF direction alignment with grace window
**Source:** `Indicator GG Beluga KHST.txt`

```python
dir_tf = khst_direction(auto_tf = current_TF * {1, 2, 3, 4})   # same KHST on each, lookahead_off
aligned = all(d == dir_main for d in dir_tf)
align_turn_on = aligned and not aligned_prev
grace = 6 bars
alignOK = aligned or (bars_since(align_turn_on) <= grace)     # hysteresis: no instant revoke
```

**Mechanics.** Multi-timeframe agreement on a *state* (KHST direction) rather than on lagging levels.
The grace window is the subtle part: once alignment turns YES, a transient misalignment on any one TF
does not revoke it for 6 bars — this kills the flicker that naive MTF-vote filters produce exactly when
one TF flips a bar or two ahead of the others (the normal case at a genuine turn).

**Why tick-powerful.** Each TF direction is a 1-bit state updated event-driven on that TF's kline close;
the alignment check is 3 XORs. The grace timer is one integer. Total cost per tick: ~0.

### 2.2 Range-filter sensitivity cross-check (scale-space consensus)
**Source:** `floop pro.txt`

Run the *same* ATR-hysteresis range filter in parallel at four sensitivities (band = `ATR14 · 0.8 ·
sens/8`; sens ∈ {3, 5, 6(main), 12, 16}); score the trend that survives the most scales:

```python
def range_filter(src, sens, atr14):
    rng = atr14 * 0.8 * sens / 8.0
    filt = (src - rng) if src > filt_prev + rng else (src + rng) if src < filt_prev - rng else filt_prev
    trend = 1 if filt > filt_prev else -1 if filt < filt_prev else trend_prev
    return filt, trend
score_sens = 2*(trend(12) == dir) + 1*(trend(16) == dir)   # slow scales weighted higher
```

**Mechanics.** A trend is *robust* if it persists when the noise threshold is tightened (sens 3, fast)
and loosened (sens 16, slow). The 12/16 pairing is the "ML-recommended" cross-check in the source: the
slower bands are the ones that separate real trends from noise, so they carry the weight. This is
scale-space consensus applied within a single indicator family — cheaper than an MTF stack and
continuous (no TF quantization).

**Why tick-powerful.** Five one-step recurrences (one per sens) per tick. The score is an integer you can
threshold at any level; it also degrades gracefully — with one sens you have a plain range filter.

### 2.3 Dual-scale smoothed-range filter
**Source:** `Infinity and Sniper by Leo.txt` (Optimum Sniper)

```python
def smoothrng(x, t, m):
    return EMA(EMA(abs(x - x[1]), t), 2*t - 1) * m          # 2-stage smoothed absolute delta
smrng = 0.5 * smoothrng(close, 27, 1.5) + 0.5 * smoothrng(close, 55, 3.0)
filt  = rngfilt(close, smrng)    # standard deadband: move only if |Δsrc| > smrng
bull  = (close > filt) and (filt_rising_count > 0)          # includes down-close pullbacks
signal = bull and last_state == -1                           # edge from bear state
```

**Mechanics.** The deadband width is itself an *ensemble of two volatility estimates at different time
scales* (27-bar and 55-bar smoothed |Δprice|, both double-EMA'd to kill spiky ranges). The filter only
moves when price moves more than that blended noise estimate, and the "up2" counter requires the filter
itself to have recently risen — so a price that sits above a *falling* filter does not count as bull.

**Why tick-powerful.** Two EMA pairs + a deadband comparator per tick. The dual-scale width is the
interesting property: it auto-widens in vol expansions at two lags, so the filter's flip frequency is
vol-locked without any explicit ATR input.

### 2.4 BOS/ChoCh level-swap state machine (body vs wick taxonomy)
**Source:** `FTR.txt` ("FTR Rules BoS/ChoCh Markup")

```python
# state: BoS_level, ChoCh_level, trend ∈ {Up, Down}, candidates, timestamps
# UPtrend (mirror for Down):
#  track Lowest_Low since last BoS; a new low is a CHoCH *candidate* if:
#     (a) it lands exactly 1 bar after last BoS AND low < BoS_Up_Low   (immediate failure), or
#     (b) >= 2 bars after last BoS AND (wick re-break of BoS with bullish body), or
#     (c) simply >= 2 bars after last BoS
#  if high > BoS_level:                                   # structure break (wick or body)
#     if close >= ChoCh_level or close > open:            # not a same-bar CHoCH body-break
#         type = "BB" if close > BoS_level else "BW"      # body-break vs wick-break
#         if candidate and >= 2 bars: ChoCh_level = Lowest_Low
#         BoS_level, Lowest_Low, BoS_Up_Low = high, high, low
#  if close < ChoCh_level:                                # FULL regime flip — the swap:
#     ChoCh_level, BoS_level = BoS_level, low; trend = Down
#  elif low < ChoCh_level:                                # wick only: level follows the low
#     ChoCh_level = low                                    # (CW type)
```

**Mechanics.** Two live levels at all times with a *symmetric swap* on regime flip (old structure-break
level becomes the new reversal level, and vice versa). Breaks are typed BB (body) / BW (wick) / CB (CHoCh
close) / CW (CHoCh wick), which lets a consumer weight body breaks higher. The "1 bar after BoS with a
lower low than the breaking bar's low" rule is an explicit **immediate-failure detector** (the break was
trapped). The candidate timing rules prevent a CHoCh level from being set by noise that occurs too close
to the break it would invalidate.

**Why tick-powerful.** Pure event-driven state machine over confirmed closes/extremes — O(1) per kline,
no buffers. On a tick engine the two levels are always-known order-management anchors (they are exactly
the "what breaks = reversal, what holds = continuation" prices), and the BB/BW typing is free because the
body/wick distinction is already in the kline feed.

### 2.5 Close-confirmed BoS/MSS with ATR-scaled swing tracker + strong points
**Source:** `Indicator ICT Master Suite.txt`

```python
# swing tracker (continuous, no fixed pivot delay):
point = running_extreme;  # flip direction when the opposite side exceeds by:
flip_threshold = ATR14 + abs(point - prev_point) * buffer     # scales with leg size
# structure event = CONFIRMED CLOSE crossing the prior swing price (never wick):
if close[1] <= swing.price < close:        event = BoS if state==Up else MSS(=CHoCH), state:=Up
if close[1] >= swing.price > close:        event = BoS if state==Down else MSS, state:=Down
# strong points:
on BoS_up:   strong_low  = opposite swing low   (created)
on BoS_down: strong_high = opposite swing high  (created)
strong_high expires on confirmed close below; strong_low on confirmed close above
```

**Mechanics.** Swing *size* is ATR-scaled and leg-size-scaled (`buffer`), so the tracker needs a bigger
counter-move to flip after a big leg — fewer false swings in trends, same count in chop. Structure
events are defined exclusively by **closed crosses** of the swing price (the user-selectable "Candle
Close" mode is the default), which is what the zero-wait requirement asks for: no event exists until the
bar confirms, but the event's *time* is the close, not close+delay. "Strong points" (the origin swings of
a BoS) are the natural stop/retrace anchors, and they are *consumed* only by closes — consistent with
the entry rule.

**Why tick-powerful.** The tracker is a handful of scalars updated per tick (running extreme + threshold
recompute). The ATR+buffer threshold makes it adapt to displacement without any parameter per market.
Strong-point expiry is a level-cross test the tick executor already runs.

### 2.6 ATR-offset trailing-stop cross engine (dual ratchet + flip)
**Source:** `HADYAN NEW SCALPING V 2.9.txt`

```python
nLoss = a * ATR(c)                      # (a,c) per style preset: (1.0,10)/(0.8,8)/(2.0,15)
# stop state:
if   close > stop[1] and close[1] > stop[1]: stop = max(stop[1], close - nLoss)   # ratchet up
elif close < stop[1] and close[1] < stop[1]: stop = min(stop[1], close + nLoss)   # ratchet down
elif close > stop[1]:                       stop = close - nLoss                  # flip to long side
else:                                       stop = min(stop[1], close + nLoss)    # short side
# ANTI-FICKER signal (confirmed):
buy  = close[2] < stop[2] and close[1] > stop[2] and all_filters[1]
sell = close[2] > stop[2] and close[1] < stop[2] and all_filters[1]
```

**Mechanics.** The stop is both the *signal generator* (cross of the stop = entry) and the *trade
stop* (same object after entry) — one object, two roles. The two-bar ratchet (both bars above →
ratchet; single bar above → flip) means the stop can only tighten while price is consistently on one
side, and a one-bar spike through it flips the side immediately (the stop "snaps" to the new side at
a·ATR). The anti-flicker signal evaluates the cross on bars [2]→[1] with filters at [1], i.e. it is
*permanently true at the moment the previous bar confirms* — the Pine "anti-kedip" property, which in a
tick engine is simply: commit the signal on kline close, using only confirmed quantities.

**Why tick-powerful.** The stop is a scalar updated per tick; the cross test is two comparisons. Because
signal and stop share the object, there is zero ambiguity between "what I entered on" and "what I'm
stopped at" — a common bug source in tick systems with separate signal/exit modules.

### 2.7 Range-based SuperTrend (zero-lag volatility from the forming bar)
**Source:** `Infinity and Sniper by Leo.txt`

```python
ma     = SMA(src, 10)
width  = high - low                          # CURRENT bar range — no ATR smoothing at all
upb    = src + factor * 2 * width            # factor = sensitivity (default 2.0)
dnb    = src - factor * 2 * width
# standard ratchet + flip (band only tightens in the favorable direction)
```

**Mechanics.** Replacing ATR with 2× the *current* bar range makes the SuperTrend's volatility term
update every bar with zero lag and zero memory. In a vol expansion the bands flare instantly (the trend
line steps away, giving the move room before it flips back); in compression the bands hug price and the
flip comes fast. It is the most reactive trend line in the corpus — at the cost of extra flips in
spiky data, which is why the source pairs it with a braid filter (§3.7) rather than trading it raw.

**Why tick-powerful.** The forming bar's high/low are live aggTrade quantities — the band can be updated
*intra-bar* with zero kline wait, making this the natural "real-time" trend state for the tick engine,
while the committed direction still comes from the confirmed-close flip.

### 2.8 BB-trigger → ATR-ratchet level engine (GBS family)
**Source:** `GBS.txt`, `FLI.txt` (same author family)

```python
# trigger: close breaks BB(21, 1.0)
# level ratchet (state, one per direction):
if up_event:    level = max(level, low  - ATR5)     # ratchet only up
if down_event:  level = min(level, high + ATR5)     # ratchet only down
else:           hold
direction = sign(level - level_prev)
signal = flip of direction;  band = level ± 0.5*ATR5
```

**Mechanics.** A Bollinger close-break (the only "lagging" part — used as a *trigger*, not a cross
signal) awakens a one-way ratchet: the level can only move in the impulse direction, by ATR5 increments,
and it holds during consolidation. The level is therefore the *highest defended low* (or lowest
defended high) of the current leg — a structural stop that tightens monotonically. Direction flips only
when the ratchet is forced across.

**Why tick-powerful.** Two scalars (level, direction) updated on events. The ratchet is a max/min per
tick — and the level is directly order-able (it is the price that, if broken, falsifies the leg), which
is exactly the object a tick engine wants for stop-placement.

### 2.9 McGinley MA + braid spread gate
**Source:** `Infinity and Sniper by Leo.txt`

```python
# McGinley: self-damping MA — step size shrinks with the 4th power of the deviation ratio
mg = mg_prev + (src - mg_prev) / (len * (src/mg_prev)**4)
# braid: three MAs of different source/period
ma01, ma02, ma03 = McGinley(close, 3), McGinley(open, 7), McGinley(close, 20)
spread = max(ma01, ma02, ma03) - min(ma01, ma02, ma03)
gate   = spread > ATR14 * 0.60            # "trending enough" filter
bull   = ma01 > ma02 and gate             # fast vs slow (different sources too)
```

**Mechanics.** The braid is a *dispersion* measure of the trend: if the fast, mid and slow MAs are
all within 0.6 ATR of each other, the market is not trending enough to take a directional signal —
regardless of their order. Using `open` as the middle source (instead of close) de-correlates the three
lines slightly.

**Why tick-powerful.** McGinley is one add + one pow per tick; the gate is three max/min + one ATR
comparison. It is a clean *trend-strength* gate that does not depend on ADX (which lags by construction)
and works identically on any symbol.

### 2.10 NO-TRADE regime + ADX-rising soft gate
**Source:** `Indicator GG Beluga KHST.txt`

```python
no_trade = (ATR14 < atr_floor)                                   # dead volatility
        or (range_20 = highest(20)-lowest(20) <= ATR14 * 1.2)    # compressed chop
        or (use_adx_base and ADX14 < adx_min)
adx_rising_ok = (ADX14 >= adx_min) or (ADX14 - ADX14[6] >= 0.25) # level OR slope
```

**Mechanics.** Two complementary filters: a hard **regime** gate that *forbids* trading when volatility
is below an absolute floor or the 20-bar range is compressed to ~1.2×ATR (the market is coiling — any
entry has negative edge), and a **soft** momentum gate that *forgives* a weak ADX level if ADX is
*rising fast enough* (a trend that is strengthening from a weak base is tradable; one that is flat is
not). The slope escape-hatch (≥0.25 ADX points over 6 bars) is the non-obvious part — it trades the
*derivative* of trend strength, which leads the level.

**Why tick-powerful.** Everything is online (ATR, 20-bar range, ADX, 6-bar lag). As a global kill-switch
it is the single highest-leverage gate in the corpus: it removes the "chop grind" loss mode that kills
trend systems, and it is expressible in 4 comparisons per tick.

---

## §3 Market microstructure (OB / FVG / MSS — no delayed-closure waits)

### 3.1 Validated order block: sweep + displacement + KZ + zone + HTF (score /8)
**Source:** `ICT Validated SMC v1.txt`

```python
# bullish OB = last bearish candle at the new confirmed swing low (10/10 pivot)
sweep  = ob.low < last_swing_low            # OB candle swept prior liquidity
disp   = any 3-bar FVG within next 6 bars   # displacement left a gap
score  = 2*sweep + 2*disp + 1*in_killzone + 1*in_discount + 2*htf_aligned      # 0..8
emit OB if score >= min_score(3)
mitigate on close < ob.bottom  ->  spawn bearish BREAKER at same box
```

**Mechanics.** An OB is only created if it has a *narrative*: it swept liquidity (someone's stops were
taken at that candle), the reaction displaced price enough to leave an FVG, and the context agrees
(killzone time, premium/discount, HTF structure). The weights (2/2/1/1/2) encode that sweep and
displacement are the *mechanism* and time/zone/HTF are *context*. Mitigation is a **close** through the
far edge (not a wick) — consistent with the close-confirmed entry philosophy — and the mitigated OB is
promoted to a breaker (same box, flipped polarity) rather than deleted, because a broken OB is precisely
where the original orders now defend the other side.

**Why tick-powerful.** The OB is identified the bar the swing confirms (pivot delay is the structural
delay, not a closure wait); all validation inputs are confirmed quantities at that moment; the score is
frozen on creation. At tap time (wick into the box + close back out) the executor already knows the
score, HTF state and killzone — O(1) lookup. The breaker promotion is a free, high-quality S/R level
with no extra detection cost.

### 3.2 KOSAI scan-based OBs: ATR200 padding, 3-mode mitigation, breaker promotion, overlap dedupe, volume metrics
**Source:** `Institutional Flow Toolkit MMDV.txt`

```python
atr200 = ATR(200)
# OB location = scan back from the structure point for the extreme bar;
# if the NEXT bar extended the extreme (displacement bar), anchor the OB there:
#   bullish OB:  top = min(high_bull_bar, low_bull_bar + atr200)
#                bottom = max(low_bull_bar, low_bull_bar + ... )  # box = bar ± up to 1*ATR200, clipped
# mitigation (selectable):
#   'Close': close crosses far edge   (first cross -> breaker; second -> deleted)
#   'Wick' : wick crosses far edge
#   'Avg'  : cross of the 50% midline  (earliest, strictest)
# overlap dedupe: when two same- or cross-polarity boxes overlap, remove one
#   (prefer keeping 'Recent' or 'Old' — user-selectable)
# volume metric: OB carries volume[creation]; displayed as % of sum over last N OBs
#   box is shaded buy-side above its midline, sell-side below
```

**Mechanics.** Three differences from the ICT validator: (1) the OB anchor is found by *scanning for the
extreme bar* (with the displacement-bar correction), not by candle-order heuristics — more robust when
the leg is multi-bar; (2) the box is **padded by ATR200** (a very long volatility scale), so the zone
covers the "intent" region, not just one candle; (3) mitigation has three selectable strictnesses —
close/wick/avg — letting the operator choose how early a failed OB becomes a breaker. The overlap
dedupe (including cross-polarity: a bull box overlapping a bear box) keeps the level list minimal, and
the volume-share metric converts each zone into a *relative-order-flow* read (big-volume OB = bigger
footprint).

**Why tick-powerful.** The scan runs only on a structure event (O(window)); everything else is state per
box. Three mitigation modes = three pre-registered price events per box; the dedupe keeps the active
set bounded (≤ last N OBs), so tap-time checks stay O(1) per level. Volume at creation is a free
attribute of the kline already in the feed.

### 3.3 Incremental FVG clipping (zone shrinks as it fills)
**Source:** `FTR.txt`, `Institutional Flow Toolkit MMDV.txt`

```python
# bullish FVG [bot, top], unfilled:
if wick enters from below (low > bot, high < top):
    top = min(top, low)                       # clip the zone to the remaining unfilled part
    ce  = (bot + top) / 2                      # consequent encroachment follows the clip
if close passes the far edge:
    FTR :  delete (mitigated)
    IFT :  delete  (or mark mitigated; 'reduce' option clips instead)
```

**Mechanics.** Binary mitigation (alive → dead) loses information: a half-filled gap is still a
reference level, just a smaller one. Clipping makes the zone's *current* bounds equal to its *current*
unfilled part, so the CE (50%) line tracks the price that actually matters on the next pass, and a
sequence of partial fills produces a step-wise tightening zone — the market "digesting" the imbalance is
visible in the geometry itself.

**Why tick-powerful.** The clip is `top = min(top, low)` — one comparison per tick, no state beyond the
two bounds. The executor's order management can treat the clipped zone as a live, shrinking limit zone:
each partial fill is a free re-estimation of where the rest of the imbalance sits.

### 3.4 IFVG — inversion FVG with retest-then-mitigate lifecycle
**Source:** `ICT Validated SMC v1.txt`

```python
when a FVG is mitigated by a CLOSE through the far edge:
    spawn IFVG at the same box, polarity flipped
    state: armed -> retested (first touch: high>=bot and low<=top) -> mitigated (close through)
```

**Mechanics.** A FVG that price closed through has just *re-established* itself as support/resistance
from the other side (the orders that filled the gap are now defending it). The lifecycle matters: an
untouched IFVG is merely a level; once *retested* (price entered it and is being accepted) it is armed —
a break after retest is a much stronger failure signal than a first-touch break. The same armed-then-
broken pattern is applied to breakers and to the OTE zones, giving the whole zone system a consistent
two-stage state machine.

**Why tick-powerful.** Two booleans per zone (retested, mitigated) and three price tests per tick. The
"retest" event is a pure level-entry test the tick engine already evaluates for order placement — the
state transition is free.

### 3.5 BPR — balanced price range (opposite FVG overlap)
**Source:** `ICT Validated SMC v1.txt`

```python
for the last 8 active FVGs:
    for each bullish-bearish pair (i, j within 6 of i):
        overlap = [max(bot_bull, bot_bear), min(top_bull, top_bear)]
        if overlap is non-empty:
            if not nearly_duplicate(existing): emit BPR zone
# invalidation: close beyond far edge by MORE than one zone-height
```

**Mechanics.** A bullish FVG and a bearish FVG overlapping is a *two-sided imbalance* — displacement
pushed through the zone in both directions, leaving resting interest on both sides of the same band.
These are rarer and, per the source's own labeling, the strongest single zone type in the file (the
panel flags active BPRs with a ◆). The "one zone-height beyond" invalidation is proportional: a thin
BPR is broken by a thin move, a deep one needs a real displacement.

**Why tick-powerful.** Overlap is computed once at FVG creation (pair check over ≤8 zones); the
invalidation is one comparison per active BPR per tick. The dedupe-by-proximity prevents the same
overlap from being re-emitted as new FVGs keep forming around it.

### 3.6 Liquidity sweep clusters + post-sweep FVG filter
**Source:** `Indicator ICT Master Suite.txt` (`zzLiq`)

```python
# swing extremes tracked with threshold = ATR + |leg| * buffer
# sweep candidate: opposite extreme exceeded by ATR*(10-strength)  (strength 5 -> 5*ATR)
# cluster: consecutive sweep extremes that stay within ±1*ATR of the FIRST sweep extreme
#          (price "stays in the grab zone" -> cluster grows; escapes -> cluster dies)
# CONFIRMATION on the confirmed bar:
#   close <= sweep_low - ATR   (down sweep) / close >= sweep_high + ATR (up sweep)
#   -> emit sweep box [min cluster .. max cluster], first sweep time -> now
# onlyFVGliq mode: after a confirmed sweep, keep ONLY FVGs formed between
#   the sweep time and now (displacement that FOLLOWS the grab)
```

**Mechanics.** A single wick above a high is noise; a *cluster* of wicks that keep returning to the same
±1 ATR band is liquidity being collected; and the confirmation — closing back beyond 1 ATR on the
opposite side — is the stop-hunt signature (sweep + reject). The cluster persistence test (stay within
±ATR of the first grab) is what separates a real sweep sequence from random spikes. The post-sweep FVG
filter is the ICT "displacement after liquidity" rule made mechanical: only the imbalance created *after*
the grab is tradable.

**Why tick-powerful.** The cluster is a running (min, max, first) triple — O(1) per tick. Confirmation
is a single close-cross test evaluated once per bar. The post-sweep FVG filter is a time-window predicate
on an existing FVG list. No waiting beyond the confirmation bar, which is the bar the rule is *defined*
on.

### 3.7 FVG rejection signal + gap-protected stop
**Source:** `FVG Sniper.txt`

```python
# rejection (long example, bullish FVG [bot, top], live):
if wick taps into [bot, top] and close back out (close > bot)
   and directional close (close > open)
   and grade >= 4
   and HTF_EMA50_4H bias >= 0:
    signal LONG          # each gap may fire ONCE (reacted flag)
# stop = just beyond the far edge of the gap, clamped:
stop = min(bot - 0.2*ATR14, entry + 1.5*ATR14)      # protection: thesis is "gap holds"
stop = clamp(stop, 0.4*ATR14 .. 4*ATR14 from entry)
TP = 1R / 2R / 3R;  zone expires after 220 bars; max 14 live gaps
```

**Mechanics.** The stop is placed *outside the object that justifies the trade*: if the gap's far edge is
broken, the FVG thesis is dead, so the stop sits just beyond it (0.2 ATR buffer) — never wider than 1.5
ATR from entry, never tighter than 0.4 ATR (noise floor), never looser than 4 ATR. This makes risk a
*structural* quantity (distance to the falsification price) rather than an arbitrary multiple. The
one-shot reacted flag + 220-bar expiry + 14-zone cap keep the level list bounded and prevent re-signaling
on the same object.

**Why tick-powerful.** The tap test is a level-entry + close-out test on the kline close; grade/HTF are
frozen attributes; the stop is computable at signal time as a pure function of (entry, gap edge, ATR).
For the tick engine this is the cleanest "object-protected stop" template in all three batches.

### 3.8 OTE zones from the structure-break leg (with OB/FVG overlap detection)
**Source:** `ICT Validated SMC v1.txt`

```python
on a structure break, leg = last_swing_low .. last_swing_high (or mirror)
OTE zone = [61.8%, 78.6%] retrace of the leg
triggered  = wick into zone AND close back inside zone
invalidated = close beyond the origin extreme of the leg
labels: "OTE" / "OTE+OB" / "OTE+FVG" / "OTE+OB+FVG"  (any active OB/FVG box inside the zone)
```

**Mechanics.** The OTE is anchored to the *leg that just broke structure* — not an arbitrary swing — so
it is the retracement of the displacement move itself. The overlap flags turn the OTE into a composite:
an OTE containing a validated OB and an unmitigated FVG is the triple-confluence the panel highlights.
Invalidation is a close through the leg origin (the retrace "completed and rejected" = the leg's origin
was taken = the setup is dead).

**Why tick-powerful.** Zone bounds are two closed-form numbers from the leg extremes at break time;
trigger/invalidation are close-based tests; the overlap flags are static booleans set at creation
(re-checked only when OB/FVG lists change). O(1) per active zone.

### 3.9 Buy-side / sell-side ATR liquidity zones (KOSAI)
**Source:** `Institutional Flow Toolkit MMDV.txt`

```python
on a BOS with a sweep:
    id = extreme bar of the swept swing
    sellside zone = [high_id - ATR200, high_id]     # buy-side liquidity above the high
    buyside  zone = [low_id,  low_id + ATR200]      # sell-side liquidity below the low
    zone carries volume[id]; label shows % vs the opposing zone's volume
    zone removed when price CLOSES through its outer edge
```

**Mechanics.** The zone is the ATR-thick band *around* the liquidity pool (the swing extreme), marking
where the resting stop-orders sit. It is emitted only when the BOS is preceded by a sweep of that very
pool (the stops were just hit — the zone is "active"). The volume-% label compares the two facing zones
(who has more resting liquidity) — a relative-strength read of the next leg.

**Why tick-powerful.** Two levels + one volume attribute per zone; removal is a close-cross test. The
"active only after sweep" condition makes these event-driven rather than a standing grid — the executor
sees a zone appear at the exact bar the liquidity was grabbed.

### 3.10 TF-adaptive OB mitigation threshold (25% vs 50%)
**Source:** `FTR.txt`

```python
# each OB box carries 25/50/75% lines; mitigation threshold depends on CHART timeframe:
if TF <= 15m:  mitigate when price crosses the 25% line   # scalping: first fill kills it
else:          mitigate when price crosses the 50% line   # swing: half-fill only
```

**Mechanics.** A fill that is significant on a 5-minute chart (25% of the box) is trivial on a 4-hour
chart. The mitigation depth is therefore a *scale* parameter, chosen by the timeframe the levels are
traded on, not by the timeframe they were found on (the file runs the same machine on 1m, HTF and HHTF
and renders each at its own mitigation rule).

**Why tick-powerful.** One comparison constant per box selected at creation; the 25/50/75 lines are
precomputed. It generalizes the §3.2 three-mode mitigation from *operator choice* to *automatic by
scale* — a clean default for a multi-TF tick engine.

### 3.11 EQH/EQL at 0.15% tolerance + wick-reject sweeps
**Source:** `ICT Validated SMC v1.txt`

```python
EQH/EQL: two swing highs (lows) with |p1 - p2|/p1 <= 0.15%      # "equal" = liquidity pool
sweep (strict mode): wick through the swing price + close back inside,
   AND the previous candle had a rejection wick > max(body, 0.1*ATR14)
```

**Mechanics.** Equal highs/lows are the *purpose-built* liquidity (traders' stops cluster at the visible
double-top/bottom), so they get their own level type. The strict sweep mode adds a pre-condition: the
bar *before* the sweep must already show rejection (a long opposing wick that closed back) — i.e. the
market first probed, failed, then the sweep bar took the level. That "probe-fail-then-sweep" sequence is
the stop-hunt signature with the highest information content.

**Why tick-powerful.** EQ detection is a pairwise test on the last 8 confirmed swings (O(1) per new
swing). The wick-reject precondition is one comparison on the prior bar's geometry — already in the
kline feed. Both are evaluated at bar close with zero additional delay.

### 3.12 Inducement (IDM) — internal-swing trap levels
**Source:** `ICT Validated SMC v1.txt`

```python
in bullish swing trend: every internal (5/5) swing LOW that is not within 0.1% of the
                        swing low itself  ->  IDM level (a trap for early shorts)
triggered  = wick below IDM + close back above        # the trap sprung
expired    = swing structure flipped, or 20 bars after trigger
```

**Mechanics.** IDM encodes the sequencing insight that *internal* structure is taken out *before* the
real move, to induce early positions. An internal low that gets wicked while the swing trend holds is
the classic "shorts trap" — its sweep is therefore a *long* signal (in an up trend), not a breakdown.
The "not within 0.1% of the swing extreme" filter keeps the IDM distinct from the real support, and the
20-bar expiry / structure-flip invalidation keeps the level list fresh.

**Why tick-powerful.** IDM levels are created on internal pivot confirmation (5-bar delay, inherent to
any pivot); trigger/expire are close-based. For the tick engine it is one more level type in the same
registry with a polarity *opposite* to its surface direction — which is exactly the kind of nuance a
static S/R line cannot represent.

---

## §4 Dynamic risk (adaptive SL / trailing / TP on real-time volatility)

### 4.1 ATR-offset trailing stop with breakeven ratchet (core + "waspada")
**Source:** `HADYAN NEW SCALPING V 2.9.txt`

```python
stop = a*ATR trailing stop (see §2.6)
# auto-breakeven:
if in_position and profit >= breakeven_factor * entry_nloss:      # 1.0R
    stop = max(stop, entry) if long else min(stop, entry)         # ratchet only in favorable dir
# "waspada" (caution) flag:
waspada = in_position and distance_to_stop < 0.75 * entry_nloss
```

**Mechanics.** Three zones of the trade, all derived from one risk unit (entry_nloss): *caution* when
price comes within 0.75R of the stop (warn / pre-stage exit), *breakeven* at +1R (stop jumps to entry —
the trade becomes risk-free), then *run* on the trailing stop. The breakeven move is a one-way ratchet
(it can only improve the stop), and it is triggered by *profit in R units*, so it scales with the
entry's volatility.

**Why tick-powerful.** Two extra comparisons per tick on top of the trailing stop already being
maintained. The 0.75R caution zone is a free pre-alert that a tick engine can use to stage a reduce
order *before* the stop is hit — turning a reactive stop into a managed exit.

### 4.2 Dynamic TP on Bollinger outer band + RSI-extreme profit lock
**Source:** `HADYAN NEW SCALPING V 2.9.txt`

```python
tp_static  = entry + 3.0 * entry_nloss                  # "jangan tamak" (don't be greedy)
tp_dynamic = close > BB_upper(20,2)  (long) / close < BB_lower (short)   # vol-adaptive outer band
exit_warn  = profit > 1R and (RSI14 > 70 long / RSI14 < 30 short)        # "TP NOW" lock
```

**Mechanics.** The take-profit is either a fixed 3R or the *live* outer Bollinger band — i.e. the target
expands with volatility and contracts with it. The RSI-extreme lock is a separate, earlier trigger: once
the trade is ≥1R in profit *and* momentum is extended, take it — don't wait for the band. The two
mechanisms are asymmetric: the band catches the big runs, the RSI lock protects the small ones from
giveback.

**Why tick-powerful.** BB band and RSI are online; both tests are per-tick comparisons. The "profit
state" (1R threshold) is one stored float. This is the most complete *exit-state machine* in the batch:
{caution, breakeven, RSI-lock, band-TP, trailing-stop} in one file.

### 4.3 RSI-ladder TPs (70/75/80 and 30/20/15)
**Source:** `Haper Trend.txt` / `Fresh Algo.txt` (TP ladder); `Infinity and Sniper by Leo.txt` (TEX)

```python
# Haper/Fresh (exit ladder in the direction of the trade):
long: TP1 = RSI14 crosses 70, TP2 = crosses 75, TP3 = crosses 80   (gated: each must occur
#      after the previous one, measured from entry bar)
short: TP1..TP3 = RSI crosses 30 / 25 / 20
# Infinity TEX (trend-exhaustion ladder, symmetric mirror):
long exits: RSI22 crosses back up through 30 / 20 / 15
short exits: RSI22 crosses back down through 70 / 80 / 85
```

**Mechanics.** Instead of price targets, the take-profits are *oscillator-exhaustion events*: the further
RSI must climb into overbought territory, the later the TP tier. The tiers are ordered by construction
(RSI must cross 70 before 75), so the ladder self-sequences without bookkeeping. The TEX variant uses the
*return* of RSI from the extreme (crossing back through 30/20/15) as the exhaustion signature for a
long — momentum fading back through the lows = the move is dying.

**Why tick-powerful.** RSI is online; each tier is a level-cross test on a scalar. The ordering property
means the engine can pre-register all three tiers as conditional limits and let the oscillator sequence
them — zero per-tick logic beyond updating RSI.

### 4.4 PREDICTUM Fibonacci-decay ladder
**Source:** `Indicator MM ALGO PREMIUM for TradingView.txt` — see §1.9 (lives here too: it is a risk
mechanism, not just a target). Partial exits are sized `100/(numTP-1)` per tier (equal splits), which
combined with the decaying spacing means *most of the position is exited in the first 1.618R*.

### 4.5 Gap-protected, ATR-clamped stops
**Source:** `FVG Sniper.txt` — see §3.7 for the formula; the risk property: stop distance =
f(entry, object edge, ATR) clamped to [0.4, 4]·ATR. The 0.4·ATR floor is the key tick-engine detail:
below it, the stop is inside the instrument's own noise (and the tick feed's) and will be hit by
microstructure alone.

### 4.6 Zone-anchored SL/TP (structure as the risk unit)
**Source:** `ICT Validated SMC v1.txt`

```python
long signal at a zone touch:
    SL = min over touched zones of (ob.bottom, fvg.bottom, ote.legLow, breaker.bottom)
    TP = last_swing_high                    # opposite structural extreme
short: mirror
```

**Mechanics.** The stop is the *far edge of the object being traded* (or the leg origin for OTEs) — the
price at which the thesis is falsified — and the target is the *opposite swing extreme* (where the next
liquidity sits). R:R therefore comes out of structure, not chosen. The signal also carries a 10-bar
same-direction cooldown to prevent re-signaling while price lingers in the zone.

**Why tick-powerful.** SL/TP are two closed-form numbers emitted with the signal; no trailing logic
needed for the base case. The tick engine registers SL as a stop-market and TP as a limit and does
nothing else until one triggers — the lowest-overhead execution pattern available.

### 4.7 NO-TRADE volatility floor + tight-range compression
**Source:** `Indicator GG Beluga KHST.txt` — see §2.10; as a risk mechanism it is a *pre-entry*
volatility filter: no position is ever opened when ATR < floor or the 20-bar range ≤ 1.2·ATR. For a
tick engine this is the difference between "no edge, but we trade anyway" and "no edge, we stand
aside" — and it is computed from the same ATR the stops use, so the floor and the stop are
consistently scaled.

### 4.8 Frozen entry/TP/SL levels with stale re-freeze
**Source:** `Indicator GG Beluga KHST.txt`

```python
on flip (or on alignment turning YES if levels are stale > 6 bars):
    freeze: entry = close ± 0.6*ATR ; TP1 = +1.0*ATR ; TP2 = +1.7*ATR ; SL = +1.2*ATR  (from entry)
    # levels remain FIXED until re-frozen (stale > 6 bars at next alignment YES)
```

**Mechanics.** A "pending order template" that survives a few bars of price movement: the levels are
computed once at the flip and *frozen*, so a late entry still targets the same structure. If the market
moves on and the template becomes stale (>6 bars), the next alignment event re-freezes it. This
decouples *signal time* from *execution time* — important in a tick engine where the signal may fire
on kline close but the actual fill arrives seconds later.

**Why tick-powerful.** Four frozen floats + a timestamp. The re-freeze rule is one age check. It is the
only explicit "stale order" semantics in the corpus — directly portable to a real order manager
(cancel-and-replace when stale).

### 4.9 200-bar ATR baseline for volatility-regime scaling
**Source:** `Indicator GG Beluga KHST.txt` (Early Flip); cf. `Institutional Flow MMDV.txt` (ATR200 for
OB padding)

```python
atr_base  = SMA(ATR14, 200)
vol_ratio = ATR14 / atr_base        # >1 = vol expanding vs own history, <1 = contracting
```

**Mechanics.** A 200-bar (on 1m: ~3h) baseline of ATR gives a *regime* variable: current vol relative to
the recent normal. Two files in this batch independently use ATR200 as the "structural" volatility
scale (Beluga for threshold adaptation, KOSAI for OB padding) — a strong signal that 200-bar ATR is the
right length for separating *regime* from *noise* at the 1m horizon.

**Why tick-powerful.** One rolling SMA over an online ATR. The ratio is a single division; every
volatility-scaled quantity in the engine (stops, thresholds, zone padding) can reference the same
regime number, keeping the whole risk stack consistently scaled.

### 4.10 ATR100/2 wide-stop sizing (HalfTrend)
**Source:** `HalfTrend.txt` — `atr2 = ATR100/2`; SL = 3·atr2 (= 1.5·ATR100), TP 1/2/3R. The long-
period half-ATR stop is deliberately *wide* — sized to absorb 1m noise on a 100-bar (≈1.5h) volatility
scale — paired with the §2.8-style ratchet entry, so the system trades few, wide, high-RR setups.
Useful as the "swing" risk preset in a multi-preset tick engine (cf. HADYAN's (a,c) style triples).

### 4.11 Percentile-gated volatility score
**Source:** `floop pro.txt`

```python
atr_rank = (number of last 60 ATR14 values <= current ATR14) / 60 * 100
score_vol = (atr_rank < 80 ? 1 : 0) + (atr_norm < percentile_60(atr_norm) ? 1 : 0)
```

**Mechanics.** The score *penalizes* being in the top 20% of recent volatility — entering at a vol
climax (where stops are widest and fills worst) is a bad trade even if everything else aligns. It is a
volatility *regression-to-mean* gate: trade mid-vol, not max-vol.

**Why tick-powerful.** A 60-element ring buffer of ATR14 with a rank count — O(60) per kline close at
most, O(1) amortized with a sorted structure. As a ±1 term in the §5.3 score it is cheap insurance
against vol-climax entries.

---

## §5 Confluence / scoring systems

### 5.1 0–11 signal score with hard zone requirement (ICT Validated SMC)
**Source:** `ICT Validated SMC v1.txt`

```python
long_score = 2*(at active bull OB) + 1*(at active bull FVG)
           + 2*(at active bull OTE) + 1*(at un-retested bull breaker)
           + 1*(HTF aligned) + 1*(in killzone)
           + 1*(in discount) + 1*(swing structure bullish) + 1*(bullish CISD)
signal = (any zone touched) and score >= 4 and HTF_ok and KZ_ok and CISD_ok and cooldown_ok
```

**Mechanics.** Zones (where) carry the weight (2 each), context (when/why) carries 1 each; the signal is
the *intersection* of a minimum score AND the mandatory gates (HTF, optional KZ/CISD). CISD
(change-in-state-of-delivery = close beyond the open of the last opposite candle) is the cheapest
momentum-confirmation bit in the corpus: one stored float (lastBearishOpen/lastBullishOpen) and one
comparison.

**Why tick-powerful.** The score is an integer sum of precomputed booleans evaluated on the confirmed
bar; the gates are 3 booleans. In a tick engine the per-zone booleans are the same level-occupancy tests
the order manager runs anyway — the score reuses existing state, so the marginal cost of the confluence
decision is ~10 XOR/ADD ops.

### 5.2 OB validation score /8 (§3.1) — 2/2/1/1/2 weights
Sweep + displacement (mechanism) weighted 2, killzone + zone (context) 1, HTF 2. Emitted at creation,
star-rank displayed (3★=4pts … 5★=7pts). A frozen attribute — the executor never re-scores a zone.

### 5.3 0–14 strength score with chop penalty (floop pro)
**Source:** `floop pro.txt`

```python
score = score_htf(1) + score_mtf(0..4: 1m/5m/15m/1h/4h range-filter direction)
      + score_sens(0..3: sens 12 → +2, sens 16 → +1)
      + score_ema(0..4: EMA60/200 alignment + ROC5/10/20 alignment/partial)
      + score_vol(0..2: §4.11 percentile gate)
      + chop_penalty(-1 per failed anti-chop filter: ADX>=20, CI<=61.8, cooldown>=5)
tiers: >=11 HIGH, >=8 MED, >=6 LOW, else WEAK
```

**Mechanics.** The most granular score in the batch (14 points, 6 components). Notable: the momentum
component uses the *sign agreement of three ROC horizons* (5/10/20) rather than an oscillator — all three
same sign = "aligned", only the fast one = "partial" (half credit). The chop penalty is *subtracted*
rather than gating: a signal that fires against chop is not deleted, it is downgraded — preserving
information for the operator while the hard gates (EMA alignment + chop gate) already block the worst
cases.

**Why tick-powerful.** Each component is a set of online comparisons on the confirmed bar; the ROC-
agreement test is 6 sign checks. The 14-point integer is the single most informative *quality* number
the engine can attach to a trend-flip entry.

### 5.4 7-filter AND gate with per-filter reason reporting (HADYAN)
**Source:** `HADYAN NEW SCALPING V 2.9.txt`

```python
filterBuy = EMA_ok AND RSI_ok AND candle_ok AND volume_ok AND ADX_ok AND SNR_ok AND confirm_ok
# on a blocked raw cross, report exactly which filters passed:
block_reason = "Buy Blocked (5/7)"
```

**Mechanics.** The AND gate is standard; the *diagnostic* is the value: on every blocked signal the
engine records the pass-count and (in the full implementation) the failing factors, so a post-mortem can
attribute losses to specific filters. The SNR filter is a *proximity veto*: no buy within 2·ATR of the
nearest pivot high, no sell within 2·ATR of the nearest pivot low (don't buy into resistance). The
midpoint-confirm (close beyond prior bar's (H+L)/2) is a one-bar momentum veto.
Note: the volume filter's 0.3×SMA20 threshold is near-tautological (almost always true) — treat it as
disabled.

**Why tick-powerful.** All seven are online comparisons; the reason string is built only on blocked
signals (rare). For a tick engine this is the template for *explainable gating*: same cost as a plain
AND, plus a log line that makes the filter set auditable.

### 5.5 FVG grade 0–10 (§1.10) as a signal gate
Rejection signals (§3.7) require grade ≥ 4; IFVG/OTE confluence checks use the grade implicitly.
The grade is computed once at creation (size/displacement/volume) — the executor consults, never
recomputes.

### 5.6 ECHO score ≥ 80 as a directional prior (§1.1)
The k-NN score itself is a confluence number: ≥80 on all top-3 matches *and* |mean forward bias| >
0.5% is the fire condition. It is the only *statistical* (distributional) score in the corpus — the
others are boolean counts.

### 5.7 MACDV band + 6-phase as dual regime gates (IFT MMDV)
The dashboard's two columns (MACDV state §1.7, phase §1.8) form a 7×6 regime matrix; the tradable
cells are the {G0/RETEST} × {RUNNING UP/RE-ACCUMULATION} quadrants. Excluded from extraction as a
*repainting* MTF version (lookahead_on dashboard), but the *chart-TF* computation is clean and
portable as a 2-bit regime tag (momentum band, phase) attached to every tick.

### 5.8 Preset parameter regimes (per asset class / per style)
**Sources:** `Indicator GG Beluga KHST.txt` (Gold/US100/US30/FX), `HADYAN NEW SCALPING V 2.9.txt`
(style presets), `Indicator MM ALGO PREMIUM for TradingView.txt` (Default/Scalping/Intraday/Swing),
`floop pro.txt` (sens presets)

```python
# Beluga per-class regime table (R, Q, ATRlen, ST factor, entry/TP1/TP2/SL ATR mults,
# ADX min, early-flip threshold, ADX-slope threshold)
GOLD:  R=10.0 Q=0.010 ATR=12 f=1.60  e/t1/t2/sl = 0.60/1.00/1.70/1.20  adx≥16 ef=0.10 slope≥0.25
US100: R=12.0 Q=0.012 ATR=14 f=1.70  0.60/1.00/1.80/1.30               adx≥18 ef=0.12 slope≥0.35
US30:  R=14.0 Q=0.015 ATR=14 f=1.80  0.70/1.10/2.00/1.40               adx≥18 ef=0.14 slope≥0.45
FX:    R=16.0 Q=0.020 ATR=12 f=1.50  0.50/0.90/1.50/1.10               adx≥15 ef=0.08 slope≥0.25
```

**Mechanics.** Every "magic number" in the trend/risk stack is grouped into a per-class tuple: higher
cost-of-trade / higher-noise assets get *wider* smoothing (R), *wider* ST factors and *wider* stops,
plus *stricter* ADX and early-flip gates. The pattern (vol class → every parameter shifts together) is
the single most reusable engineering artifact of the batch: one dict per asset class, and the whole
stack (smoother, trend, gates, risk) rescales coherently.

**Why tick-powerful.** Presets are data, not code — the tick engine loads one dict per symbol and every
module reads its parameters from it. This is the difference between "tuned" and "configurable" in a
multi-symbol HFT context.

---

## §6 Integration blueprint (zero-wait tick engine, Binance Spot, 1m)

Layered composition of the batch-3 machinery (each block = one stateful module, all O(1) per tick except
where noted):

```
L0 REGIME (per symbol)
    atr14, atr200 = ATR(14), ATR(200)            # online
    vol_ratio     = atr14 / SMA(atr14, 200)      # §4.9
    NO_TRADE      = atr14 < floor OR range20 <= 1.2*atr14 OR ADX < min     # §2.10
    ADX_ok        = ADX >= min OR ADX_slope6 >= 0.25                       # §2.10

L1 TREND (per symbol, per TF ∈ {1m, 2m, 4m, 12m})
    khma  = KHMA(close, R_class, Q_class)        # §1.4  (running on FORMING close)
    dir   = SuperTrend_ratchet(khma, ATR12, f_class)                  # §1.4
    align = all(dir_tf == dir_1m) OR grace<=6 bars after align turn   # §2.1
    sens5 = {range_filter_trend(s) for s in 3,5,6,12,16}              # §2.2 (consensus score)

L2 STRUCTURE (per symbol, 1m confirmed bars)
    swings10, swings5 = ATR+buffer swing trackers (10/5 scales)        # §2.5
    events: BoS/MSS on CONFIRMED CLOSE cross of swing price            # §2.4/2.5
    strong_points: created on BoS, expire on close                      # §2.5

L3 ZONES (event-driven registry, bounded)
    OB   (validated: sweep+displacement+score/8; ATR200 padded variant)  # §3.1/3.2
    FVG  (3-bar, displacement>=1*ATR, graded 0-10, clipped as filled)    # §1.10/3.3
    IFVG / Breaker (spawn on close-mitigation; retested->mitigated)      # §3.4
    BPR  (opposite-FVG overlap)                                          # §3.5
    OTE  (structure-leg 61.8-78.6%, wick-trigger, close-invalidate)      # §3.8
    sweeps (cluster ±1ATR, confirm >1ATR, post-sweep FVG only)           # §3.6
    IDM  (internal-swing traps, polarity-flipped)                        # §3.12
    EQH/EQL (0.15%), buy/sell-side ATR zones                             # §3.9/3.11
    -> all zones: {bounds, grade/score, retested, mitigated, expiry}     # O(1) tap test

L4 SIGNAL (on 1m kline CLOSE only — the "confirmed" commit point)
    candidate = zone tap (wick-in, close-out) in trend direction
    score     = 0-11 confluence (§5.1) or 0-14 (§5.3) depending on entry type
    gates     = L0 not NO_TRADE, ADX_ok, align, (killzone optional), CISD
    extras    = ECHO prior (§1.1, score>=80), harmonic completion (§1.2),
                Early-Flip pending already raised (§1.5)
    cooldown  = 10 bars same direction

L5 RISK (frozen at signal)
    SL  = zone far edge / leg origin, clamped [0.4, 4]*ATR14             # §4.5/4.6
    TP  = opposite swing extreme, or ladder: 1/2/3R | RSI 70/75/80 |
          PREDICTUM decay (asymptote 2.618R) | BB(20,2) outer band       # §4.2-4.4
    BE  = ratchet stop to entry at +1R; caution flag at 0.75R-to-stop    # §4.1
    stale = re-freeze pending template after 6 bars                      # §4.8
```

**Execution mapping to the tick stream.** `aggTrade` updates: forming-close state (khma, L1 dir, stop
ratchets, zone tap tracking — all the "live" quantities), bookTicker: no direct role in these models.
1m `kline` close: commit L2 structure events, L3 zone state transitions (mitigation/retest), L4 signal
evaluation, L5 risk freeze. This is the batch's central finding: **every model in the corpus is
expressible as (a) tick-updated continuous state + (b) a decision function that fires only on the kline
close** — i.e. genuinely zero-wait (no lookahead, no intra-bar signal that later vanishes), while still
using intra-bar information for pre-positioning (pending markers, caution flags, tap tracking).

---

## Appendix A — Per-file exclusions (batch 3)

| File | Kept (see sections) | Excluded (red line) |
|---|---|---|
| `FVG+Fractals.txt` | — (36L) | Whole file: bare 3-bar FVG + fractal pivots; only detail = tick-quantized min-gap filter (N·mintick) — subsumed by §1.10 displacement gate |
| `GBS.txt` | §2.8 ATR-ratchet level engine (BB(21,1) close-break trigger noted as red-line-2 usage) | BB as the *signal* per se (lagging trigger) |
| `GainzAlgo Pro.txt` | §2 primitive: engulfing ∧ body/TR > 0.5 ∧ RSI14 < 50 (position, not cross) ∧ close < close[5] displacement precondition | RSI as a cross (not used as such) |
| `GainzAlgo V2.txt` | Same core, 0.7 body threshold, RSI < 80 position, close[10] precondition; SL = 1·ATR14, TP = 1/2/3×SL | — |
| `FLI.txt` | §2.8 ratchet family; day-high/low tracker gating patterns (mechanics noted) | PVP fib *mechanism* (lookahead_on) — levels salvageable as prior-period fib; RSI 3-bar-OR reversal (lagging) |
| `HalfTrend.txt` | §4.10 ATR100/2 risk; trend matrix + 5-symbol scanner (scanner concept already in batch 1) | — |
| `Historical Pattern Projection.txt` | §1.1 ECHO (full) | — |
| `FVG Sniper.txt` | §1.10 grade, §3.7 rejection + gap-protected stop | — |
| `floop pro.txt` | §2.2 sensitivity cross-check, §4.11 vol percentile, §5.3 score, §2 (range filter core) | Pivot *mechanism* (lookahead_on; levels salvageable as prior-period pivots); EMA60/200 cross as signal (kept only as score component); dashboards |
| `FTR.txt` | §2.4 BOS/ChoCh swap machine, §3.10 TF-adaptive OB mitigation, §3.3 FVG clipping | — |
| `Haper Trend.txt` | §1 (Trend Shifter), §4.3 RSI TP ladder, §2 (ST 3.1/25 confBull sans MACD, dchannel, vol filter), consolidation detector (noted), percentVol | `securityNoRep` MTF emaBull (lookahead_on); MACD 12/26/9 component of confBull (lagging trigger); buySetup/sellSetup gradient (visual); MACD histogram bar-coloring |
| `Fresh Algo.txt` | §1.3 ATR-band Ichimoku; Haper-family deltas (ST 2.4/10, contrarian zones 35/65) | Same as Haper (shared codebase) |
| `Fresh Algo (1).txt` | — (duplicate of Fresh Algo v25 math core) | Entire file as a separate source (version/label differences only) |
| `HADYAN NEW SCALPING V 2.9.txt` | §2.6 stop-cross engine, §4.1 breakeven + waspada, §4.2 dynamic TP + RSI lock, §5.4 7-filter gate, style presets | Daily pivot *mechanism* (lookahead_on; levels salvageable); volume filter (0.3× threshold ≈ tautology); HTF ghost candles, stoch mini-chart, fibo drawing (visual); win/loss counter (hardcoded 50-0 start — cosmetic stat) |
| `Infinity and Sniper by Leo.txt` | §1.2 harmonic, §1.6 pair-enumeration TL, §1.11 channel-cluster S/R, §2.7 range SuperTrend, §2.9 McGinley braid, §4.3 TEX ladder, S/R close-break alert logic | `securityNoRep1` MTF + prior-day H/L/C (lookahead_on); EMA10/20 trend-catcher cross (lagging); RSI21 OB/OS (standard); swing-point HH/LH/HL/LL labels (visual) |
| `ICT Validated SMC v1.txt` | §3.1 OB validator, §3.4 IFVG, §3.5 BPR, §3.8 OTE, §3.11 EQH/EQL + strict sweeps, §3.12 IDM, §4.6 zone-anchored SL/TP, §5.1 score, CISD | PDH/PDL/PWH/PWL *mechanism* (lookahead_on; levels salvageable as prior-period H/L); killzone EST windows kept as time gates (noted: on 24/7 crypto they are arbitrary-but-consistent time filters) |
| `Institutional Flow Toolkit MMDV.txt` | §1.7 MACDV, §1.8 6-phase machine, §3.2 KOSAI OB engine, §3.3 FVG clipping, §2 (OLS regression channel — see below) | EMA ribbon EMA11/34 cross *signal* (lagging); 5-TF MACDV dashboard (lookahead_on); MTF H/L D/W/M/Q/Y (lookahead_on); 14-symbol screener (standard scanner, batch-1 concept) |
| `Indicator ICT Master Suite.txt` | §2.5 close-confirmed BoS/MSS + strong points, §3.6 sweep clusters + post-sweep FVG, range-state OB (logZ≥2 gate), sorted-array level expiry (engineering note) | PBH/PBL *mechanism* (lookahead_on; salvageable); Po3/macros/equalLevels/displacement internals live in external import `Trading-IQ/ICTlibrary` — **not extractable** from this file (noted, not guessed) |
| `Indicator MM ALGO PREMIUM for TradingView.txt` | §1.9 PREDICTUM ladder, §2 (ATR ratchet chandelier incl. len=1 variant), §2.9-adjacent 6-zone EMA state machine (kept as context state, not trigger), VT ±53 top/bottom, 6-MA ensemble cloud (noted), partial-TP sizing | MTF ribbon via nested-EMA security (default lookahead off — kept only as state); volume-spike cloud shading (visual) |
| `Indicator GG Beluga KHST.txt` | §1.4 KHST, §1.5 Early Flip, §2.1 MTF alignment + grace, §2.10 NO-TRADE + ADX gate, §4.8 frozen levels, §5.8 preset table | — (no red lines; all security calls lookahead_off) |

**IFT MMDV OLS regression channel** (kept, condensed): `slope = linreg(src,L,0) − linreg(src,L,1)`;
`ip = SMA(src,L) − slope·floor(L/2) + (1−L%2)/2·slope`; `lst = ip + slope·(L−1)`;
`dev = sqrt(Σ(src[x] − (slope·(L−x) + ip))² / L)` (RMS residual); bands at `lst ± dev·2`;
break = rising ∧ close < lst − 2dev (mirror for falling); fib levels across [−2dev, +2dev] at
0.236/0.382/0.618/0.786. A linear-regression channel with residual-scaled bands — the linear twin of
batch 2's loglin channel.

---

## Appendix B — Porting notes for the tick engine

1. **Kalman/KHMA (Beluga).** Run on the *forming* 1m close (last aggTrade price). State per (symbol,
   TF): (est, err) × 3 passes. R/Q from the §5.8 class table. The committed direction flips on kline
   close — intra-bar khma is used only for Early-Flip pending and live stop placement.
2. **ECHO (Pattern Projection).** Ring buffer of 530 closes (500 library + 30 current) per symbol.
   On each confirmed close: shift one 30-window out, push one in; compute 500 Pearson correlations on
   30-vectors (batched numpy: one 500×30 matmul + norm) ≈ tens of µs. Keep top-3 indices + outcomes in
   a heap. Fire only on confirmed bars — the library is historical, so there is no lookahead by
   construction.
3. **Harmonic (Infinity).** Zigzag per symbol over 1m extremes with 24/35-bar pivot confirmation.
   Maintain 6 swing points; on each new swing do 6 template interval tests + 2 guards. Risk/reward is
   template-fixed (stop B, target C).
4. **Zone registry (ICT VSMC / KOSAI / FVG Sniper).** One unified zone object:
   `{kind, top, bot, grade_or_score, retested, mitigated, polarity, expiry_bar, vol_share}`.
   All state transitions are close-based (mitigation, retest, expiry) → evaluate once per kline close;
   tap tracking (wick-in) is a per-tick min/max vs bounds. Use the sorted-price-array + bulk-slice
   expiry trick from ICT Master Suite when the price permanently leaves a band of levels.
5. **Sweep clusters (Master Suite).** Running (first, min, max, alive) per direction; threshold
   `ATR + leg·buffer` for swings, `5·ATR` for sweep candidates, `±1·ATR` persistence, `>1·ATR` close
   confirmation. O(1) per tick; the box is emitted once at confirmation.
6. **Grace window (Beluga MTF).** Store `align_on_bar`; `alignOK = aligned OR (now − align_on_bar ≤ 6)`.
   Prevents one-TF-ahead flicker at genuine turns. Generalizes to any multi-TF vote.
7. **Frozen levels (Beluga).** On flip: compute (entry, TP1, TP2, SL) once from close + ATR class
   multipliers; store timestamp; re-freeze on next alignment-YES if age > 6 bars. Map directly to
   cancel-and-replace of a pending limit/stop set.
8. **NO-TRADE + ADX gates (Beluga).** Global per-symbol kill switch: `trade_ok = NOT no_trade AND
   adx_rising_ok`. Apply *before* any signal evaluation — cheapest possible high-leverage filter.
9. **Scoring (ICT/floop/HADYAN).** Implement as integer confluence counters with per-factor booleans
   cached on the zone/structure objects; the signal is `score ≥ thr AND hard_gates`. Log the failing
   factors on blocked candidates (HADYAN pattern) — essential for filter attribution.
10. **Preset tables (Beluga/HADYAN/MM).** One dict per asset class holding (R, Q, ATRlen, factor,
    entry/TP/SL ATR multipliers, adx_min, ef_thresh, slope_thresh, style (a,c)). All modules read from
    it; a new symbol class is a new row.
11. **Volatility baseline.** Maintain `SMA(ATR14, 200)` and `ATR200` per symbol; derive `vol_ratio`.
    Every ATR-scaled quantity (stops, thresholds, zone padding, sweep depth) references these, keeping
    the risk stack consistently regime-scaled.
12. **Killzones on crypto.** ICT's EST session windows are FX artifacts; on 24/7 spot they remain valid
    as *time gates* (volatility clustering around US hours), but default them OFF or retune to observed
    high-volume windows.
13. **Commit-point discipline.** Every model here separates *continuous state* (tick-updated: stops,
    khma, tap tracking, pending flags) from *committed decisions* (kline-close: structure events, zone
    transitions, signals, risk freeze). Keeping this split in the engine architecture is what makes the
    whole batch "zero-wait" rather than "repainting": nothing that can change within a bar is ever used
    as a trade decision.
