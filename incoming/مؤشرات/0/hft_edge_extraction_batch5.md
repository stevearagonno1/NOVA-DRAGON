# HFT Edge Extraction — Batch 5 (Files 82–101)

**Scope.** 20 files in `uploads/` (19 unique — `PSniper.txt` is md5-identical to `PRECISION SNIPER.txt`, read once). Reverse-engineered per the standing red-line policy: no repaint/lookahead triggers, no slow-cross lagging-indicator triggers, no GUI/visual code, no derivatives/leverage logic. Output: Python pseudo-code / precise math + mechanics + why it suits a zero-wait tick engine (Binance Spot HFT: 1m klines, aggTrade, bookTicker).

**Batch character.** This batch is dominated by (a) *quality-indexed* trend engines (a 4-factor Trend Quality Index that rescales band width, ATR, and TP distances per bar), (b) *tested-zone accounting* (supply/demand zones that accumulate "rejection points" every time they defend against adverse flow), (c) *bounded-lag divergence and reclaim* state machines, and (d) *per-setup edge instrumentation* (scoreboards that measure each setup's own →TP1 conversion). Several files are kitchen-sink mashups; only the novel constructs are extracted, cross-referenced to batches 1–4.

**Cosmetic exclusion (all files).** Telegram watermark dashboards (`@mrexpert_ai`, WillyAlgoTrader, `SimpleForexTools` branding), theme/color engines, table/label/box/line drawing code — excluded in every file; none of it feeds a signal.

---

## Red-Line Disposition (Batch 5)

| File | Excluded (red-line) | Salvaged |
|---|---|---|
| `PSniper.txt` | md5-duplicate of `PRECISION SNIPER.txt` | nothing (no double extraction) |
| `short and long.txt` | triple mintick-unit zigzag — pivots confirmed 1+ bar after the fact (lagging by construction); no independent signal | none |
| `SFI MAGIC.txt` | smoothrng(100)×2.3 deadband *flip trigger* = B3/4 range-filter family (cross-ref B3 §2.3) | ST-on-SMA10 ratchet + 1.5·ATR book-profit exit |
| `NAS Ultimate Algo Remastered.txt` | ST(4,11)+SMA13 cross trigger (cross-ref Haper/Fresh family, B3); 61-tier RSI color gradient | none (no new math) |
| `Pearson SLTP.txt` | — (trigger is a custom bounded oscillator, not a lagging indicator) | W1 full; dead 4th strength term (EMA50-vs-EMA200, constant) dropped |
| `NEXT CANDLE PREDICTOR V4.txt` | EMA8/21 cross *as the buy trigger* (slow cross, red-line #2) | S1 full scoring/threshold/velocity engine; CVR-style delta |
| `NOVA ALGO.txt` | ST cross trigger (family cross-ref); ALMA trend tracers, Hullma 600 cloud | M1 rejection counter; volume-strength ratio (computed, never rendered — latent feature) |
| `RSI entry.txt` | signal-EMA(9)-cross (panel-only oscillation cross) | D6 extreme-reclaim trigger + 5R runner; SL mode set |
| `Scalper.txt` | HTF "trend candle" renderer, KC-based fake "200 EMA", percentVol dashboard, RSI-tier bar colors | M1 parameter set v2; FVG close-mitigation rule |
| `PRECISION SNIPER.txt` | EMA fast/slow cross trigger; HTF via `[ema[1]] + lookahead_on` = *confirmed-bar* idiom (salvage note, not lookahead) | S2 score + presets; R1 hybrid SL; ratchet trail; backtest R-accounting |
| `phantom flow.txt` | SuperTrend flip trigger (family cross-ref); FVG `security(..., lookahead_on)` mechanism flagged (same-TF version salvageable) | W3, W4, W9, plus 2-scale leg structure + ATR200-tolerance EQH |
| `Setup Scanner [GBB].txt` | none in signal math (EMA 9/21/50 used as *touch/reclaim structure*; trigger = expansion close, not MA cross) | S3 full; M4, M5; D3, D5 |
| `NOSTRADAMUS.txt` | ST+SMA15 trigger; KC 80-stack "channel balance"; PAC channel; EMA200 long/short; percentVol; MTF SMA50 slope panel | W2 Nostalgia VP; PREDICTUM TP cross-ref (≡ B3 §1.9); 150-bar LR deviation channel (noted, low novelty) |
| `SELF-AWARE TREND SYSTEM.txt` | — (trigger *is* the adaptive band flip; mechanism extracted as W6) | W5, W6, R1, R3, R4 (SATS rows) |
| `Reactive Trail System.txt` | — (trigger = close-cross of the ratcheted adaptive trail; mechanism extracted as R2) | R2, R5, R6 |
| `River Strategy.txt` | dual smoothrng flip trigger (B3/4 family); WaveTrend fractal-divergence display; auto-trendlines; SMMA33/144 crosses; candle patterns | W7 dry-bar entry; W8 volume-pivot OB; 5σ volume level detector; touch-count S/R |
| `Order&Breake.txt` | engulfing+RSI reversal trigger (lagging pattern + oscillator, red-line #2); FVG "deletion on far-edge cross" mislabeled as fill | M2, M3, M6, M7, M8; S5 contrarian vote |
| `RSI divergence entry.txt` | HTF trend filter via `lookahead_off` = live HTF value (slightly leaky while the HTF bar forms; flagged, not used in extraction) | D2 full; R4 (RSI-div rows) |

---

## §1 — Wildcards & Innovative Edges

### W1. Pearson-R Linearity-Fade Oscillator — *Pearson SLTP*

```python
N = 20
x = arange(N); y = last-N closes
r = pearson(x, y)                      # slope-normalized: r in [-1, +1]
# r -> +1 : price has been moving in a near-perfect straight UP line
# r -> -1 : near-perfect straight DOWN line
LONG  = crossunder(r, -0.7)            # perfectly linear collapse => fade it
SHORT = crossover (r, +0.7)            # perfectly linear rip    => fade it
# optional confirm: r rising while price falls over 5 bars (divergence confirm)
# strength (0-4): vol > SMA20 + |r| > 0.8 + |Δr| > 0.05  (+1 degenerate term, dropped)
# exits: SL 1.5*ATR14, TP 2.0/3.5*ATR14, 50/50 split, reverse on opposite signal
```

**Mechanics.** Pearson r between price and bar index is a *bounded* (∈[−1,1]) measure of price-linearity over the window — a trend-strength oscillator that is scale-free by construction. The edge thesis: a move that has been *too* straight (|r| > 0.7) is statistically stretched — every bar contributed to the same slope with almost no noise — so it is more likely to snap back than to continue. This is the same "stretched state → fade" family as B5's other mean-reversion triggers, but the stretching metric is geometric (fit-to-a-line) instead of oscillator-based (RSI) or band-based (BB). Because r is bounded and continuous, it can be evaluated on every tick with running sums (Σx, Σy, Σxy, Σx², Σy² — O(1) update).

**Why zero-wait.** Five running sums over a 20-deep ring buffer; cross events are comparisons; no bar-close wait in the math (the Pine version signals on close; a tick port can fire the cross the moment |r| crosses 0.7).

---

### W2. Nostalgia Volume Profile — Wick-Weighted Buy/Sell Decomposition + POC/VA — *NOSTRADAMUS*

```python
W, Nbins = 150, 500
lo, hi = lowest(low, W), highest(high, W)
bins = linspace(lo, hi, Nbins)
up = dn = zeros(Nbins)                     # per-side volume
for bar in last W bars:
    body = |c-o|;  tw = H - max(c,o);  bw = min(c,o) - L
    tot  = body + 2*tw + 2*bw              # wick lengths double-weighted
    v_body = V*body/tot;  v_wick = V*(2*tw + 2*bw)/tot
    for each bin overlapping [max(c,o), H]: up/dn split wick volume 50/50
    for each bin overlapping [min(c,o), L]: up/dn split wick volume 50/50
    if c >= o: attribute v_body to up[] on body bins   else to dn[]
total = up + dn
POC = argmax(total)
# Value Area: expand OUT from POC, each step take the RICHER adjacent bin,
# until 70% of total volume is enclosed  => VAH / VAL
```

**Mechanics.** Three upgrades over a naive profile: (1) **wick-length volume partition** — a bar's volume is split body/upper-wick/lower-wick in proportion to length (wicks double-weighted so the partition sums to V), so *where in the bar's range* the volume happened is modeled, not just where it closed; (2) **side attribution** — body volume goes to the buy side on green bars and the sell side on red bars (wicks split 50/50), giving per-bin **up-volume vs down-volume** — a two-sided imbalance profile (the profile's local buy/sell ratio is a direct order-flow asymmetry map); (3) **POC + 70% value-area expansion by richer-adjacent-bin**, the classic VPVA rule. The Pine version computes only on the last bar (display); the math is fully portable to a rolling recompute per closed 1m bar (O(W·Nbins) ≈ 75k ops — trivial) with incremental aggTrade updates intrabar. POC/VAH/VAL become live magnet/acceptance levels: price inside VA = acceptance (fade edges), price outside VA = rejection (trade back to POC).

**Why zero-wait.** One vectorized pass per bar close; intrabar delta adds one bar's partition increment; POC/VA queries are O(1) lookups into the bin array.

---

### W3. Self-Calibrating FVG Displacement Threshold (cumulative mean body) — *phantom flow*

```python
# standard 3-candle FVG: bullish iff low > high[2] and close[1] > high[2]
bodyPct = (c[1] - o[1]) / o[1]                          # displacement bar body, %
meanBodyPct = ta.cum(|bodyPct on new-htf-bar|) / bar_index   # lifetime running mean
require |bodyPct| > 2 * meanBodyPct                      # THE filter
```

**Mechanics.** Most FVG implementations accept any gap; this one demands the *displacement bar's body* exceed **2× the running average body size** of the instrument (cumulative mean, so it self-calibrates to the pair's normal impulse magnitude and drifts as regimes change). A gap produced by a sub-average bar is noise; a gap produced by a body twice the normal is genuine displacement. Priced as: `threshold_t = 2·(Σ_{i≤t}|Δ%_i| / t)` — one running sum, O(1)/bar. (The Pine version computes the FVG on an HTF via `lookahead_on` — mechanism flagged; the same-TF version is what a 1m engine should run.)

**Why zero-wait.** One cumulative scalar; the gap test is two price comparisons on the just-closed 3-bar window.

---

### W4. Volatility-Parsed Order Blocks (spike-bar extreme inversion) — *phantom flow*

```python
vol_measure = ATR(200)                 # alt: ta.cum(TR)/bar_index = lifetime mean range
spike = (H - L) >= 2 * vol_measure
parsedHigh = spike ? L : H             # <-- extremes INVERTED on spike bars
parsedLow  = spike ? H : L
# on a BOS (close crosses last swing level):
#   walk back from pivot bar to now on the PARSED series:
bullOB = bar with min(parsedLow) in pullback region   # zone = that bar's H/L
bearOB = bar with max(parsedHigh) in pullback region
mitigate: bullOB dies when mitigation src < ob.low  (close or wick basis)
cap 100 blocks
```

**Mechanics.** Standard OB anchoring picks the extreme bar of the last opposing leg — but wick spikes pollute that anchor (a 5-tick stop-hunt wick becomes the "zone edge"). Here any bar whose range ≥ 2×ATR200 is *parsed with inverted extremes*: its wick tip stops qualifying as an anchor; instead the body-side extreme is used. The OB therefore anchors to where the *leg* actually originated, not where a single stop-run reached. Combined with the cumulative-mean-range volatility option (lifetime, not rolling — an instrument's native range), this is a robust "origin of the last opposing impulse" detector.

**Why zero-wait.** Per-bar spike flag + parsed series; the min/max walk happens once per structure break (O(leg length)).

---

### W5. TQI — 4-Factor Trend Quality Index + Efficiency-Weighted ATR — *SELF-AWARE TREND SYSTEM*

```python
# efficiency (Kaufman):
ER = |c - c[L]| / Σ_{i<L}|c[i] - c[i+1]| ,  L = 20        # 0..1
# four 0..1 factors:
tqiEr     = clamp(ER, 0, 1)
tqiVol    = mapClamp(zscore(volume, 20), -1, +2, 0, 1)      # no-volume fallback:
             #            mapClamp(ATR/ATR(100), 0.6, 1.8, 0, 1)
pos       = (c - lowest(20)) / (highest(20) - lowest(20))
tqiStruct = |2*pos - 1|                                     # 0 mid-range, 1 at an extreme
tqiMom    = (# bars in last 10 with sign(Δc_i) == sign(c - c[10])) / 10
TQI = (0.35*tqiEr + 0.20*tqiVol + 0.25*tqiStruct + 0.20*tqiMom) / Σweights

effAtr = ATR * (0.5 + 0.5*ER)      # clean trend vol counts full; noisy vol halved
```

**Mechanics.** TQI is a *continuous per-bar* estimate of "how trend-like is this market right now," blending four orthogonal evidence channels: path efficiency (net move vs path length), participation (volume z-score, asymmetric map so heavy up-volumes saturate at z=2), position-in-range (a trend is where price *lives* at the extreme of its own recent range), and bar-sign persistence (fraction of bars agreeing with the net move). The **efficiency-weighted ATR** is the practical payoff: in a chop (low ER) the effective volatility is halved → bands tighten in chop (fewer false breaks) and open to full ATR in clean trends. Both TQI and effAtr are O(window) scalars — cheap to run on every tick.

**Why zero-wait.** ER, z-score, min/max, and sign-persistence are all running-stat quantities over ≤20 bars; TQI is a weighted sum.

---

### W6. Asymmetric Quality-Indexed SuperTrend + Character Flip — *SELF-AWARE TREND SYSTEM*

```python
qDev    = (1 - TQI) ** 1.5                        # curve power 1.5
tqiMult = 1 - Q + Q * (0.6 + 0.8*qDev)            # Q = quality strength (0.4)
sym     = baseMult * legacyERfactor * tqiMult     # band width, 0.6..1.4 x base
# ASYMMETRY (the "ratchet-with-leverage"):
active  = sym * (1 - A*0.3*TQI)                   # side IN trend direction tightens
passive = sym * (1 + A*0.4*TQI)                   # side BEHIND trend widens
# both multipliers EMA-smoothed (alpha 0.15) to stop the ratchet sticking
band = standard ratchet: lowerBand ratchets up while close above, etc.
flip = price crosses ratcheted band  OR  CHARACTER FLIP:
charFlip = TQI[1] > 0.55 and TQI < 0.25 and trendAge >= 5
           and close crossed source
```

**Mechanics.** Three stacked ideas: (1) **band width is a function of measured trend quality** — in high-quality trends the band compresses to ~0.6×base (tighter trailing, earlier exits), in collapse it widens to ~1.4×base (noise tolerance); the 1.5-power curve makes mild quality dips barely widen the band while a severe collapse widens it fast; (2) **asymmetry** — the active side tightens *and* the passive side widens in proportion to TQI, so a strong trend produces a self-accelerating ratchet (exit line hugs price from behind) while the opposite trigger distance grows; (3) the **character flip** lets the system exit on *quality collapse alone* (TQI falling 0.55→0.25 in one bar with close through source) — a regime-change exit that never waits for a full ATR band break. The EMA-smoothed multipliers prevent the ratchet from freezing at a compressed width after the regime ends.

**Why zero-wait.** Everything is a per-bar scalar pipeline (TQI → multipliers → ratchet); the flip is a crossing event on the live trail line.

---

### W7. Ultra-Narrow-Band "Dry Bar" Displacement Entry — *River Strategy*

```python
band  = SMA(close, 55) ± 0.2 * stdev(close, 55)    # 0.2 sigma = "river"
dryUp   = lowest(low, 1)  > band.top                # ENTIRE prior bar above band
dryDown = highest(high, 1) < band.bottom
# on the FIRST dry bar of an excursion:
buy_limit  = high  (limit at the dry bar's high)
stop_loss  = band.bottom captured at the event
tp1, tp2   = 1:1 and 2:2 on (entry - stop)
```

**Mechanics.** A 0.2σ band hugs the 55-bar mean so tightly that a *full bar* sitting outside it can only happen during genuine displacement (the whole bar's range, wicks included, is displaced). The strategy is pure continuation: enter on a limit at the extreme of the first dry bar, stop back at the band (risk = displacement width), scale 1:1/2:2. In HFT terms this is a *displacement detector with self-sized risk*: the stop distance IS the displacement magnitude, so risk auto-scales to the move. Port: SMA/stdev via running sums; `lowest(low,1) > band.top` is one comparison on each closed 1m bar.

**Why zero-wait.** The dry test is evaluated on bar close (or, in a tick port, the moment the forming bar's low stops making new lows above the band — an early, bounded-latency version).

---

### W8. Volume-Pivot-Anchored Order Blocks — *River Strategy*

```python
phv = pivothigh(volume, 20, 20)          # pivot on the VOLUME series
state: low[20] < lowest(low,20)[1]  => bullish regime (impulse up from here)
       high[20] > highest(high,20)[1] => bearish regime
bullOB (when phv fires inside bullish regime):
    anchor bar = 20 bars back (the big-volume bar)
    zone = [hl2[20], low[20]]
mitigate: lowest(close, 20) < zone.bottom   (close basis)
          or lowest(low, 20) < zone.bottom  (wick basis)
```

**Mechanics.** Instead of anchoring an OB to a *price* pivot, this anchors it to a **volume pivot**: the bar whose volume made a 20-bar extreme. The implicit model: the order block is where *participation* peaked before the impulse leg — the big print marks institutional work, the subsequent impulse marks the move away from it. The zone geometry ([hl2, low] of the anchor bar) and mitigation (full close through the far edge) are standard; the *selection criterion* (volume pivot, not price pivot) is what differentiates it. Port: maintain a 20-bar rolling volume pivot (20 bars of confirmation — bounded, non-repainting).

**Why zero-wait.** One pivot detector on the volume channel; zones freeze at creation; mitigation is a running-min comparison.

---

### W9. Percentile-Normalized HMA Contrarian Oscillator — *phantom flow*

```python
maBase  = MA(hl2, 40)                       # SMA/EMA/KAMA/WMA/VWMA selectable
oscDiff = hl2 - maBase
oscRange = percentile_linear_interpolation(oscDiff, 1000, 99)   # 99th pct, 1000 bars
osc = HMA( change(oscDiff / oscRange, 15), 10 )
BUY  = crossover (osc, osc[2]) and osc < -0.5    # contrarian cross INSIDE extreme band
SELL = crossunder(osc, osc[2]) and osc > +0.5
```

**Mechanics.** The oscillator is the rate-of-change of (price − slow MA), **normalized by the 99th percentile of its own 1000-bar magnitude** — a regime-invariant amplitude: the threshold "0.5" always means "half of what this instrument's extreme deviations look like," so one parameter set works across volatility regimes and instruments. Double HMA smoothing (15 then 10) removes bar noise. The signal is *contrarian*: a 2-bar cross that happens while still inside the extreme band (below −0.5 or above +0.5) — i.e., a turn detected while the deviation is still stretched, not after it has unwound. Same family as B4 W3 (RSI-space supertrend contrarian) but with adaptive normalization.

**Why zero-wait.** Percentile from a sorted 1000-float ring (O(log n) insert); HMA is a running filter; signals are crossing events on the live series.

---

### W10. Regime-Grid Edge Monitor with Self-Adapting Gain — *SELF-AWARE TREND SYSTEM*

```python
# 3x3 regime grid: ER bin (chop/mixed/trend) x vol-ratio bin (low/norm/high)
cell = erBin(ER)*3 + volBin(ATR/ATR100)
EWMA(alpha=0.2) of realized R per cell; rolling window 20 signals:
    winRate, avgR, minRun (min cumulative-R = max DD in R units)
# auto-calibration (the meta part):
if avgR(20) < 0.0 and >= 5 signals since last step:
    Q += -0.05 if Q was above base else +0.05       # nudge quality strength
    clamp Q to [0.1, 0.9]
elif avgR(20) > 0.7: freeze stepping (edge is good)
```

**Mechanics.** Two instruments in one: (1) a **regime-conditioned performance monitor** — realized edge is tracked *per market regime* (the 3×3 ER×vol grid), so "this strategy makes money in trends but bleeds in chop" is visible per cell with O(1) state (9 EWMA scalars + counters); (2) a **self-adapting gain** — if rolling edge in the *current* regime goes negative, the system nudges its own quality-influence gain (which controls how aggressively TQI tightens bands) by ±0.05, clamped, with a 5-signal cooldown; if edge is healthy (>0.7R avg) it freezes. This is the only file in five batches that closes the loop on its *own* parameter — deliberately experimental in the source, but the mechanism (regime-conditional R-accounting → gain modulation) is directly portable as a size/kill switch for any strategy.

**Why zero-wait.** 9 scalars + 20-deep R ring; update on trade close (an event).

---

## §2 — Macro Directional Filters (low-lag trend math)

### D1. Open-vs-Close HMA Momentum-Lead CMO — *sfi scalper 1.0*

```python
lead = ΔHMA(open, 5)  -  ΔHMA(close, 12)     # fast open-lead minus close-follow
cmo  = CMO(lead, 20)                          # (lead - lo20)/(hi20 - lo20) * 100
LONG  = pivot_low(low, 2) and RSI(9) < 25  and cmo >  50
SHORT = pivot_high(high, 2) and RSI(9) > 75 and cmo < -50
# exits: dual-band supertrend (src ∓ 2*ATR ratchet) + fixed 2% SL, TP 1/2/3R
```

**Mechanics.** The HMA of *open* reacts to where each bar starts; the HMA of *close* to where it ends. Their delta is a **momentum-lead indicator**: when market makers are pushing the open ahead of the close follow (e.g., gaps/impulses opening higher each bar while closes haven't caught up), `lead` is rising. Combined with a 2-bar price pivot + RSI9 extreme (the stretched state), it fires a mean-reversion entry *when the open-lead has already turned but price is still stretched* — an earlier read than waiting for close-momentum to confirm. CMO keeps the scale at ±100. All terms are running filters over ≤20 bars.

**Why zero-wait.** Two HMAs (open channel and close channel) on the same ring buffer; CMO is a min/max-normalized ratio; pivot/RSI are standard bounded-lag confirmations.

---

### D2. Asymmetric RSI-Pivot Divergence Engine (47-left / 1-right, bounded window, 4 types) — *RSI divergence entry*, variant in *Setup Scanner*

```python
RSI = RSI(14)
pivotL = pivotlow(RSI, L=47, R=1)          # 1-bar confirmation -> NON-repainting
prev   = valuewhen(pivotL, rsi[1], 1)      # PREVIOUS confirmed pivot (rsi, price, bar)
window = 5 <= bars_since(prev) <= 60       # divergence must form in a bounded window
regular bull: low[1] < prev.priceLow  and rsi[1] > prev.rsi   and window
hidden  bull: low[1] > prev.priceLow  and rsi[1] < prev.rsi   and window
(bear mirrors on highs: HH+LH regular, LH+HH hidden)
valid = raw AND NOT opposite-raw (same-bar mutual exclusion) AND trend filter
```

**Mechanics.** Three deliberate design choices, each fixing a classic divergence defect: (1) **asymmetric pivot (47 left / 1 right)** — a huge left lookback finds *significant* RSI swings (a 5/5 pivot over-detects in noisy RSI), while a 1-bar right confirmation keeps latency to one bar and is non-repainting by construction (the pivot bar is fully in the past); (2) **bounded 5–60 bar window** between the two pivots — a divergence against a pivot from 3 weeks ago is not a signal, so comparisons older than 60 bars are void; (3) **four-type symmetry** (regular + hidden, both polarities) with same-bar mutual exclusion so a bar can't be both a buy and a sell. The Setup Scanner variant (M-family file) uses *price* pivots 5/5 with RSI sampled at the pivot and a 60-bar pivot gap cap, explicitly "late by construction, honest by design" — cross-reference for the price-pivot flavor.

**Why zero-wait.** Pivot confirm at R=1 = one bar; the comparison is against a frozen `valuewhen` snapshot; the window is two integer comparisons.

---

### D3. VWAP Dwell-Then-Reclaim — *Setup Scanner*

```python
belowRun = consecutive bars with close < session VWAP
LONG  = crossover(close, VWAP) and belowRun[1] >= 6 and vol >= 1.0 * SMA(vol, 20)
SHORT = mirror (aboveRun[1] >= 6)
forming = belowRun >= 6 and close > close[1] and VWAP - close < 0.4*ATR   # arming state
```

**Mechanics.** A plain VWAP cross is a noisy trigger; the **dwell requirement** (≥6 closed bars on one side before the reclaim *counts*) converts it into a "price was rejected, now it's back" signature — the 6-bar side-soak means the reclaim comes *away from* a zone where flow was consistently one-directional. The 0.4·ATR approach state (`forming`) lets an engine pre-arm. Session VWAP from aggTrade is exact (Σp·v / Σv over the UTC day).

**Why zero-wait.** An integer run-counter on closed bars + one crossing event + a volume ratio.

---

### D4. 3-EMA Touch-And-Reclaim Pullback (9/21/50) — *Setup Scanner*

```python
trend   = EMA21 > EMA50 and EMA50 > EMA50[3]      # 50-slope = trend direction
touched = barssince(low <= EMA21) <= 3             # pullback reached the 21 within 3 bars
LONG = close > EMA9 and bullBar and close > high[1] and vol >= 1.0*SMA(vol,20)
```

**Mechanics.** The EMA stack is used as *geometry, not cross*: 50-slope says which way, 21 is the *touch target*, 9 is the *reclaim line*, and the trigger is an **expansion close** (bull bar closing above the prior high) — a pullback-into-the-middle-MA-with-resume pattern with a hard trend gate. No MA cross is the trigger, so this stays outside red-line #2; every clause is a bounded lookback (≤3 bars for the touch).

**Why zero-wait.** barssince counter + three comparisons; fires on the expansion bar's close (or tick port: the moment price reclaims EMA9 with momentum).

---

### D5. Single-Break Opening Range (one ORB trigger per session) — *Setup Scanner*

```python
range = [min low, max high] over first orMin (15) minutes of session  # 0930-1600 NY
        (crypto: configurable UTC anchor, same math)
LONG  = close > orHigh and not orFired      # orFired is SHARED across both directions
SHORT = close < orLow  and not orFired
orFired := true on either                        # ONE break per session, first direction wins
```

**Mechanics.** Cross-ref B4 D6 (multi-stage ORB). The difference is the **one-break-per-session rule with a shared fire flag**: the first break — either direction — consumes the setup; no opposite re-entry off the same range. This is a strict anti-churn constraint (an ORB range is only information *once*; re-trading it is mean-reversion noise). The 15-minute range also doubles as the volatility normalizer for the session.

**Why zero-wait.** Two level comparisons against frozen session extremes; the fire flag is one boolean.

---

### D6. EMA-Smoothed RSI Extreme Reclaim + High-Multiple Runner — *RSI entry*

```python
rsiS = EMA(RSI(14), 5)
LONG  = crossover(rsiS, 20) on closed bar      # reclaim UP through the EXTREME zone
SHORT = crossunder(rsiS, 80)
SL  = min(signal-candle extreme, 1.0*ATR, 0.5%)     # 3 selectable modes, tightest wins
TP  = 5.0 R                                       # fixed high-multiple runner
same-bar ambiguity: SL counted first (conservative, configurable)
```

**Mechanics.** This is *not* an oscillator cross (70/30) — it is a **stretched-state release** trigger: RSI smoothed by EMA5 must climb *out of* the ≤20 (or fall out of ≥80) extreme zone, i.e., the stretch has bottomed and turned. The 5-bar EMA on RSI suppresses the single-tick RSI spikes that make raw RSI-20 crosses fire on noise. Paired with a **5R fixed runner** (SL-first on ambiguity), the design is "high-multiple, low-frequency, let-winners-run" — the payoff profile (win = 5R, lose = 1R) needs only ~20% win rate to break even, which extreme-reclaim setups historically approach. Cross-ref: D1 is the same thesis with a CMO-based stretch metric; this is the RSI-flavored instance.

**Why zero-wait.** One EMA on RSI + one crossing event against a constant; SL/TP are event-driven lines.

---

## §3 — Market Microstructure (OB / FVG / sweeps without close-wait)

### M1. Tested-Zone Accounting — S/D Zones with Rejection Counters + Swing-Volume Strength (3-file family)

```python
# ============ family core (identical in all three) ============
# zone creation from a swing/extreme event; box height ATR-scaled;
# overlap de-dup by MIDPOINT distance; cap N/side FIFO;
# BOS: close through the FAR edge => zone deleted.

# ============ the unique parts ============
# (a) REJECTION COUNTER (NOVA / Scalper):
every k bars after creation (NOVA k=15, Scalper k=20):
    if price is within the box AND
       adverse-flow count >= m  (NOVA: >=7 of last 15 bearish for demand;
                                 Scalper: >=10 of last 20 bearish for demand):
        zone.rejections += 1        # zone "held" against adverse flow again
# (b) PER-ZONE NET SIGNED DELTA (S&D zones / BigBeluga):
#     creation: 3 consecutive same-direction candles + bar[1] volume > SMA(vol, 1000)
#     anchor  : the OPPOSING candle within 5 bars back
#     supply  = [low(anchor), low(anchor) + 2*ATR200]; demand mirror
#     delta_z = Σ(+vol on bull candles in zone lifetime) - Σ(vol on bear candles)
# (c) SWING-VOLUME STRENGTH (Scalper, actually rendered; NOVA computes it, never uses it):
#     strength = volume[swing_bar] / highest(volume, 100)
#     tiers: >=0.30 Strong | >=0.20 High | >=0.10 Balanced | else Low
```

**Parameter table.**

| File | Creation trigger | ATR scale / box | De-dup | Rejection audit | Volume label |
|---|---|---|---|---|---|
| S&D zones (BigBeluga) | 3 same-dir candles + vol > SMA(vol,**1000**) | ATR**200** ×2 one side | boundary-inclusion | signed-delta gauge | — |
| NOVA | 8/8 pivot | ATR**50** ×0.4 | mid within 2·ATR50 | 15 bars / ≥7-of-15 adverse | ratio computed, unused |
| Scalper | 2/2 pivot | ATR**100** (demand 1.3×) | mid within 2.5·ATR100 | 20 bars / ≥10-of-20 adverse | 100-bar-max tiers |

**Mechanics.** The unifying idea is **zone quality as an accumulated statistic, not a creation-time property**. A zone's *age + test count* is its edge: a demand zone that has *held* (price inside it, majority adverse candles, price rejected back out) repeatedly has demonstrable defense — the rejection counter is literally a tally of successful defenses. The BigBeluga variant stores the analog as **net signed volume** (per-zone flow imbalance: more sell-volume absorbed = stronger bid). Scalper's strength ratio normalizes the swing bar's volume against the *100-bar* max — a long-memory reference so "big volume" means big *for this instrument recently*. All three keep standard de-dup (midpoint within k·ATR) and far-edge-close invalidation.

**Why zero-wait.** Zone creation is a pivot/event; the audit runs on a per-zone bar timer (every 15/20 bars — a counter); each audit is O(1) counters (adverse-candle counts are running sums); invalidation is a close-crossing.

---

### M2. OB → Breaker Polarity Flip with Re-Entry Confirmation — *Order&Breake*

```python
# swings(10): direction state os = 0 if high[10] > highest(10) (swing high),
#                              1 if low[10] < lowest(10)  (swing low)
bullOB creation: FIRST close > an unbroken swing high:
    walk back from bar 1 to (now - swing.x - 1):
        ob.btm = min(low) in region
        ob.top = high OF THE BAR HOLDING THE MIN LOW        # full range of the
        ob.loc = that bar's time                             # last push-down bar
breaker flip:  if min(close, open) < ob.btm    # BODY (not wick) intrudes opposite side
    ob.breaker = true; ob.break_loc = now      # polarity inverted, geometry kept
invalidate:    close > ob.top                  # full pass-through burns the zone
confirm:       a NEW swing high forms STRICTLY INSIDE an existing zone
    => re-entry flag ('?' marker) — price is back working the zone
```

**Mechanics.** Three state transitions the standard OB model lacks: (1) **breaker flip on body intrusion** — a bullish OB that gets *body*-traded through its bottom (open or close below, deliberately stricter than a wick) inverts to a bearish zone with its original geometry (the classic "failed support = resistance" ICT breaker, formalized as a state flag, not a new zone); (2) **burn on full pass-through** — close beyond the far edge deletes it; (3) **re-entry confirmation** — a fresh swing *inside* an intact zone marks the zone as actively contested (price is re-engaging it). The anchor selection (bar holding the region's min low, full H/L of that bar) is the "last opposing impulse" bar.

**Why zero-wait.** Swing states are events; the walk-back runs once per structure break; flip/confirm/invalid are all crossings against frozen zone bounds.

---

### M3. Range-Capped 5-Bar "Two-Push" Internal OB with Side-Volume % — *Order&Breake*

```python
# pattern on bars [5]/[4]/[3]/[1]/now  (bearish internal OB example):
open[5] > close[5] and close[4] >= open[5] and low[1] > high[5] and low > high[5]
    => two pushes down (bar 5), close reclaims (bar 4), two bars of separation
    => OB anchor = bar with the LOWER LOW of {4, 5}
# zone height CAPPED: max = min + 1.5% * (highest(300) - lowest(300))
# SIDE VOLUME on the anchor bar (close-location split):
buyV  = round(V * (C - L) / (H - L));  sellV = V - buyV
t_vol = (buyV + sellV) / 2
b_pct = buyV  / highest(t_vol, 300) * 100      # % of 300-bar max side-volume
s_pct = sellV / highest(t_vol, 300) * 100
# de-dup: a NEW OB inside an OLDER OB's box => delete the new one
```

**Mechanics.** A micro-pattern OB detector: the "two pushes + reclaim" 5-bar shape is the *impulse origin* of an internal leg, and the zone is the *capped* range of its anchor bar — the 1.5%-of-300-bar-range cap kills wick-inflated zones (no OB taller than 1.5% of the instrument's recent range). The **side-volume %** is a per-zone imbalance label: how much of that anchor bar's volume was buy-side vs sell-side, normalized to the 300-bar maximum side-volume (so 100% = the biggest one-sided print in ~300 bars). Overlap de-dup keeps the zone set thin.

**Why zero-wait.** The pattern is five fixed-bar comparisons (no waiting); volume split is one ratio; the 300-bar max is a running max.

---

### M4. Break-And-Retest State Machine (20-bar window, pending-level refresh) — *Setup Scanner*

```python
lvl = last 5/5 pivot (high for short side, low for long side)
ARMED on: close crosses lvl (state stored, brkBar = now)
LONG (retest):  bar_index - brkBar <= 20 and low <= lvl + 0.3*ATR and close > lvl and bullBar
SHORT: mirror
# pending refresh: if a NEW pivot forms DURING the window, it is held as pending
#   and becomes the active level once the window expires (no level churn mid-setup)
```

**Mechanics.** A break-and-retest as a **finite state machine**: pivot → armed-on-break → retest-or-expire (20 bars) → consumed. The 0.3·ATR tolerance means the retest may *tag* the level from either side but must close back through it; the pending-level rule prevents a fresh pivot from resetting the clock mid-setup. Cross-ref B4 M5 (pivot-zone polarity flip) for the zone-level version — this is the *single-level* instance with an explicit retest window.

**Why zero-wait.** State is 4 scalars per side; the retest test is one low-comparison + one close-comparison per bar.

---

### M5. Liquidity Sweep Reversal with Body-Dominance Filter — *Setup Scanner*

```python
extreme = lowest(low, 20)[1]                 # 20-bar extreme EXCLUDING current bar
LONG = low < extreme and close > extreme     # wick takes it out, body closes back in
     and bullBar
     and (close - low) > (high - close)      # body LONGER than the opposite wick
     and vol >= 1.0 * SMA(vol, 20)
```

**Mechanics.** Standard sweep-reclaim, but the **body-dominance clause** (the reclaim body must be longer than the bar's opposite-side wick) filters out half-hearted reclaims: a bar that wicked below the extreme and then *barely* closed back in is not a sweep-reversal — the close must be a decisive majority of the bar's range in the reclaim direction. The `[1]` on the extreme window excludes the sweeping bar itself from the reference (otherwise the bar's own wick extends the extreme it's sweeping). Cross-ref B4 M4 (sweep quality scoring) — this is the minimal 1-bar version with a body-quality gate.

**Why zero-wait.** A running 20-bar min + four comparisons on the forming/closing bar; a tick port can arm the sweep the instant the low breaks the extreme and confirm on body position.

---

### M6. Sticky-Anchor S/R Bands (8·ATR50 reset threshold) — *Order&Breake*

```python
anchor = sticky scalar:
    if |close - anchor| > 8 * ATR(50):  anchor = close;  hold_atr = 8*ATR50 now
    # otherwise anchor FROZEN (can sit for hundreds of bars)
os = sign of the last anchor move
on the anchor bar (close == anchor):
    support zone    = [anchor - hold_atr/8, anchor - hold_atr/16]   # [a-ATR50, a-0.5ATR50]
    resistance zone = [anchor + hold_atr/16, anchor + hold_atr/8]
    (i.e., 0.5·ATR50-thick band half an ATR50 away from the anchor)
```

**Mechanics.** A regime anchor that only moves on **8·ATR50 displacement** — in practice the anchor is the level price last made a *genuinely new* move from. From it, support/resistance are generated at fixed ATR offsets (0.5–1.0 × ATR50). Because the anchor is sticky, the bands are *stable* (they don't wobble with noise) yet *volation-anchored* (they sit where the last regime shift actually happened). Port: two scalars + one comparison per bar.

**Why zero-wait.** Stateful but O(1); levels are known between anchor updates.

---

### M7. RSI-Extreme-Run Zones (demand/supply from oscillator episodes) — *Order&Breake*

```python
run = consecutive bars with RSI(14) < 30,  count >= 3
demand zone = [min(low), max(high)] OVER THE RUN
supply zone = mirror over RSI > 70 runs
```

**Mechanics.** Zones defined in *oscillator-episode space* rather than price-swing space: the price range during which RSI was pinned in the extreme IS the supply/demand zone — the extreme episode marks capitulation (buyers absorbing sellers at those prices). The 3-bar minimum run filters single-bar RSI dips. Complementary to M1 (price-structure zones) — together they give zones from both the price and the momentum lens.

**Why zero-wait.** A run-length counter + running min/max over the run; zone freezes when RSI exits the extreme.

---

### M8. Range-Relative FVG Minimum Size — *Order&Breake* (family cross-refs)

```python
thold = (highest(300) - lowest(300)) * 0.015     # 1.5% of the 300-bar range
create FVG only if gap width > thold
# cross-refs: Scalper -> FVG dies on CLOSE through far edge (wick option);
#             Order&Breake -> FVG deleted on far-edge cross ("break" semantics)
```

**Mechanics.** A size filter expressed as a *fraction of the instrument's own recent range* (not ATR, not fixed points): gaps must be ≥1.5% of the 300-bar range to count, so the FVG set auto-scales across instruments and regimes. Cross-ref W3 (displacement-body threshold) — the two filters are complementary (one on the gap's size, one on the *bar that made it*).

**Why zero-wait.** One running 300-bar range + one comparison per candidate gap.

---

## §4 — Dynamic Risk (adaptive SL / trailing on real-time volatility)

### R1. Hybrid Structure/ATR SL — three placement policies in the batch

```python
# PRECISION SNIPER (wider of the two — structural realism):
sl = max(entry - k*ATR, swingLow - 0.2*ATR)          # k = 1.5 default
   = MIN distance 0.5*ATR enforced
# SELF-AWARE TREND SYSTEM (narrower of the two — tighter risk):
sl = min(pivotLow - k*ATR, entry - k*ATR)             # k = 1.5 preset-dependent
# REACTIVE TRAIL SYSTEM (wick-anchored, min-distance floor):
sl = min(signal_bar.low - 0.25*ATR, entry - 0.5*ATR)
```

**Mechanics.** The batch contains all three policies for combining an ATR stop with a structural stop: **max()** (Sniper — never tighter than the structure allows: "more realistic stop placement"), **min()** (SATS — never looser than the ATR budget: risk-first), and **wick-anchored-with-floor** (RTS — the signal bar's own wick edge is the natural invalidation point, with a 0.5·ATR minimum so a zero-wick bar can't produce a zero-risk trade). For a tick engine the policy is a one-line choice; the structural extreme (swing low, signal-bar low) is a running min/max either way.

**Why zero-wait.** Running extreme + one ATR scalar; placement at entry is O(1).

---

### R2. Momentum-Adaptive Trail Offset (tightens into strength) — *Reactive Trail System*

```python
momDist  = |EMA(RSI(13), 3) - 50| / 50                # 0 dead-center .. 1 extreme
effMult  = baseMult * (1 - adapt * momDist * 0.4)     # up to 40% TIGHTER in strong momentum
vol      = (ATR(13) + stdev(close, 13)) / 2           # hybrid: range + dispersion
trail    = ratchet(anchor_MA ∓ vol * effMult)         # anchor = ALMA(21) default
flip     = close crosses ratcheted trail
score0_100 = min(momDist/0.6, 1)*40
           + clamp(V/SMA20 - 0.5, 0, 2)/2*30          # (15 if no volume)
           + (HTF_close > HTF_EMA50 ? 30 : 10)
```

**Mechanics.** The trail width is a *function of momentum*: when RSI is stretched (strong move), the stop tightens up to 40% toward price — locking in the runner faster exactly when continuation probability is highest; when momentum is centered (chop), the trail opens to its base width to survive noise. The hybrid vol (ATR + stdev average) measures both range and close-to-close dispersion. Contrast W6: there *quality* rescales the band (SATS); here *momentum distance* rescales the offset (RTS) — complementary knobs (TQI says "is this a trend", RSI-distance says "how hard is it pushing"). The 0–100 score (momentum 40 / volume 30 / HTF 30) is a signal-strength label, not a gate.

**Why zero-wait.** All scalars are running filters; the ratchet is one max/min per tick; the flip is a crossing.

---

### R3. TQI/Vol Dynamic TP Scaling with Per-Level Floors + Order Fix — *SELF-AWARE TREND SYSTEM*

```python
volComp = mapClamp(ATR/ATR(100), 0.5, 2.0, 0, 1)
raw     = (TQI*0.6 + volComp*0.4) / 1.0               # 0..1
scale   = minScale + raw*(maxScale - minScale)         # [0.5, 2.0]
tp_i    = clamp(base_i * scale, floor_i, ceil)         # floor PROPORTIONAL to base R share
          # base 1/2/3 -> floors 0.5/1.0/1.5 (from TP1 floor), ceil 8R
# ORDER FIX (runs on the INPUT too, so bad presets can't invert the ladder):
tp1 = min(tps); tp3 = max(tps); tp2 = sum(tps) - tp1 - tp3
```

**Mechanics.** Targets are *regime-scaled*: high TQI + high vol regime → scale toward 2.0 (wider targets, let the trend run); low TQI + low vol → 0.5 (tight targets, take what chop gives). The **proportional floors** are the subtle part: without them, a low scale would collapse TP1/TP2/TP3 onto each other; floors derived from each level's share of the base spread keep the ladder *shaped* at any scale. The order-fix (min/sum-residual/max) guarantees tp1≤tp2≤tp3 under any input combination — a small defensive trick worth stealing for any parameterized ladder.

**Why zero-wait.** Two scalars (TQI, vol-ratio) → one multiplier → three multiplications per entry.

---

### R4. Realized-R & Win-Definition Family (4 accounting schemes)

| File | Position split | Win definition | Same-bar TP+SL |
|---|---|---|---|
| RSI divergence entry | 100% at TP3 | **TP3 only** (grossProfit += 6R) | **SL first** (conservative, explicit) |
| PRECISION SNIPER | 3× partials (1R/2R/3R) | best TP reached before stop; R booked at that TP's R | trail ratchet (BE→TP1→TP2) |
| SELF-AWARE TREND SYSTEM | **1/3 per TP** | TP3 = (tp1+tp2+tp3)/3 R; stop after TP1 = (1/3·tp1R) − (2/3) | SL first |
| Reactive Trail System | partials 1/2/3R | **TP1 touch** (win once TP1 prints, even if stopped later at BE) | **TP first** (optimistic, *disclosed* as optimistic intrabar model) |

```python
# SATS 1/3-split realized R (the most complete partial-fill model):
R = Σ_{i hit} (1/3 * tp_iR)  -  (1/3 * #{unhit TPs at stop})
timeout: R = Σ hit (1/3 * tp_iR), clamped to [-1, tp3R]
```

**Mechanics.** The batch shows the full spectrum of *how a trade's R is booked*, which is the variable that most distorts backtest edge: (a) **TP3-only win** — the strictest, measures true follow-through; (b) **best-TP-reached** — what actually got paid before the stop; (c) **1/3 split with proportional R** — models a real partial-close strategy (1/3 off each TP, remainder stopped); (d) **TP1-touch win with TP-first same-bar** — the most optimistic (and the only one the source *discloses* as optimistic). A tick engine resolves same-bar ambiguity by actual event order, so all four remain as backtest-parity knobs. Cross-ref B3 §1.9 PREDICTUM (0.618-decay ladder) — NOSTRADAMUS's "PREDICTUM" TP mode is the identical math (tp_{i+1} = tp_i + 0.618·(tp_i − entry), asymptote ≈ 2.618R), not re-extracted.

**Why zero-wait.** All four are event-driven bookkeeping on TP/SL crossings.

---

### R5. Intrabar Chronology Rules (bar-start snapshots & priority) — *Reactive Trail System*, *Setup Scanner*

```python
entry-bar guard:  no TP/SL checks on the entry bar itself (bar_index > entryBar)
BE snapshot:      a stop moved to break-even THIS bar CANNOT stop out this bar
                  (beActiveAtBarStart captured before the move)
same-bar priority:
    RTS:            TP touches register regardless of SL in the same bar  (optimistic)
    GBB / SATS:     SL wins if both touched                                    (conservative)
closure order (RTS alert pipeline, mirrors state order):
    management (BE -> TP1 -> TP2) -> closures (TP3 / SL) -> reversal -> entry
```

**Mechanics.** The *bar-start snapshot* is the genuinely useful rule: when TP1 prints and the stop jumps to entry, using the NEW stop for the rest of that same bar creates a phantom same-bar BE stop-out that never happens in reality (the move happened after the TP1 print). Capturing the stop state at bar start (and on a tick engine, at the exact event order) removes it. The entry-bar guard prevents the entry bar's own wick from counting as a stop. Together these two rules are the difference between a backtest that *models bars* and one that *models events*.

**Why zero-wait.** Two booleans captured at bar open; a tick engine simply orders events by timestamp.

---

### R6. Trade Lifecycle Gates — expiry, reversal parity, one-way lock, cooldown

```python
# EXPIRY (a third outcome class, not just TP/SL):
GBB : 60 bars without TP1 => "expired" (counted separately per setup)
SATS: 100-bar timeout => book the partial R already hit
# REVERSAL PARITY (opposite signal closes AND re-enters in the new direction):
RTS/Sniper: opposite confirmed flip => close at mark, open new position same bar
# ONE-WAY LOCK (GBB): while a long is open, short signals are dropped (and vice versa)
# COOLDOWN (GBB): N bars after any resolution before the next entry (default 0 = off)
# CONCURRENCY (GBB): maxOpen simultaneous trades (default 1)
```

**Mechanics.** GBB contributes the **expiry as a first-class outcome** — a trade that never reaches TP1 within 60 bars is its own category ("expired"), and its share is tracked *per setup* in the scoreboard (a setup whose trades mostly expire has no follow-through edge). Reversal parity (close-and-flip on the opposite signal) is the standard HFT posture for always-in systems; the one-way lock + cooldown + concurrency cap are the anti-churn trio that keeps an always-in engine from round-tripping through noise.

**Why zero-wait.** All are counters/flags evaluated on signal and close events.

---

## §5 — Confluence & Scoring Systems

### S1. 7-Factor Weighted Probability Score + ADX-Adaptive Threshold + ATR-Percentile Regime Scaling + Mandatory Delta Veto — *NEXT CANDLE PREDICTOR V4*

```python
# seven 0-100 sub-scores (discrete bands 100/85/70/50/25 per component):
longScore  = .23*ST_trend + .18*MACD + .15*delta + .12*RSI + .12*stoch + .10*ADX + .10*volume
longPct    = longScore / (longScore + shortScore) * 100       # softmax-like direction probability

# ADX-adaptive fire threshold (strong trend = lower bar):
thr = ADX > 30 ? 55 : ADX > 25 ? 60 : ADX > 20 ? 65 : 70

# volatility-regime scaling via ATR percentile rank:
p = percentrank(ATR14, 100)
scale = p > 75 ? 0.85 : p < 25 ? 1.15 : 1.0     # high vol damps conviction, low vol amplifies

# close-location volume delta (CVR-style) — THE VETO:
delta   = V * ( (C - L) - (H - C) ) / (H - L)        # = V*(2(C-L)/(H-L) - 1)
deltaOK = sign(delta) == side and delta > EMA(delta, 10)

PERFECT = ST_dir AND longPct >= thr*scale AND conf8 >= 5
          AND volume >= 0.8*SMA(vol,20) AND RSI > 50 AND deltaOK
# conf8: ST dir, EMA8>EMA21, MACD line, stoch K>D, vol, ADX>25, RSI-50, delta-sign
```

**Mechanics.** A complete *conviction-calibrated* scoring engine: (1) the weighted 7-factor score is normalized to a **direction probability** (long/(long+short)) rather than a raw sum — symmetric and bounded; (2) the **fire threshold is a function of trend strength** (ADX) — in a strong trend, 55% directional probability suffices (continuation is the prior); in a weak trend you need 70% (fading the mean); (3) the **ATR-percentile regime multiplier** damps conviction in high-vol regimes (noisy, so require less score to act — wait, the opposite: 0.85× threshold in HIGH vol means *easier* to fire when vol is high… the intent is that high vol = wider moves = the same score is worth less, so the threshold is relaxed toward action while risk sizing handles the width; low vol = 1.15× = *stricter*) — a two-way vol-regime gate; (4) the **mandatory delta veto** (the V4 "fix"): even a perfect score can't fire if the close-location volume delta disagrees in sign — flow direction is non-negotiable. The MACD/stoch/RSI components are *graders, not triggers* (the red-line exclusion applies to their use as slow-cross triggers, not as score inputs).

**Why zero-wait.** All seven sub-scores are running scalars; the percentile rank needs a 100-deep ATR ring; the veto is a sign comparison.

---

### S2. 10-Point Fractional Confluence + TF Auto-Preset Profiles — *PRECISION SNIPER*

```python
score += 1.0 * each of: EMAf>EMAs, C>EMA55, 50<RSI<75, MACD hist>0, MACD>sig,
                        C>VWAP, V>1.2*SMA20, ADX>20 & DI+>DI-
      + 1.5 * HTF bias (heaviest weight)
      + 0.5 * C>EMAfast (proximity bonus)
grade: >=8 A+ | >=6.5 A | >=5 B | else C
# trigger = EMA cross (excluded) + momentum + RSI-not-extreme + score >= threshold
# FRACTIONAL weights: the HTF term (1.5) can outweigh any single LTF term;
# the 0.5 proximity term is a soft bonus, not a full vote

# TF AUTO-PRESET (full parameter profile per timeframe):
#  <=5m:  EMA 5/13/34, RSI8, ATR10, minScore 4, SL 0.8
#  <=60m: EMA 9/21/55, RSI13, ATR14, minScore 5, SL 1.5
#  <=240m: EMA 8/18/50, RSI11, ATR12, minScore 3, SL 1.2   ("Aggressive")
#  else:  EMA 13/34/89, RSI21, ATR20, minScore 6, SL 2.5  ("Swing")
```

**Mechanics.** The fractional scoring is the detail that matters: **HTF bias is worth 1.5 votes** (deliberately overweighting the higher-timeframe prior over any single low-timeframe condition), while close-proximity to the fast EMA is a 0.5 bonus — a graded, not boolean, confluence. The auto-preset engine bundles *every* parameter (EMA lengths, RSI, ATR, threshold, SL) into timeframe profiles — the recognition that the correct parameter set is a function of the bar period, selected automatically. Cross-ref B4 S-concepts (boolean 0–10 counts): this is the fractional-weight generalization.

**Why zero-wait.** Ten comparisons + one weighted sum; the preset table is static config.

---

### S3. 6-Setup Portfolio Arbiter + Per-Setup Edge Scoreboard — *Setup Scanner* (batch flagship)

```python
setups = {VWAP_reclaim, EMA_pullback, break_retest, sweep_reversal,
          rsi_divergence, ORB_break}          # each = D3/D4/M4/M5/D2-variant/D5
state per setup: off | dormant | forming | long | short
# fire gate (all must pass):
room    = openTrades < maxOpen              (default 1)
cool    = bars since last resolution >= reentry (default 0)
dirOk   = not oneWay OR no open trade OR same-direction
# per-setup SCOREBOARD (the instrument):
fired[s], reachedTP1[s], reachedTP2[s], reachedTP3[s], stop[s], expired[s]
display: fired count and ->TP1% = cT1/cFired  (greyed out below minSamp=10)
# SELECTIVE volume gating (documented in source):
volume REQUIRED for VWAP / EMA / SWEEP     (participation is part of the thesis)
volume deliberately OFF for B&R / DIV / ORB (a valid retest is often quiet;
                                             divergence confirms late; ORB range
                                             is its own filter)
```

**Mechanics.** The most HFT-relevant construct in the batch: a **portfolio of independent setup state machines under one arbiter**, each setup carrying its *own* lifetime statistics (fired / →TP1 / →TP2 / →TP3 / stop / expired). This turns the indicator into an **edge-measurement instrument**: after enough samples you can read which setups actually convert (→TP1% per row) and allocate size accordingly — a live A/B scoreboard per strategy component, with the sample floor (10) to avoid reading noise. The selective volume gating (with its written rationale) is a documented *negative* result worth respecting: not every setup wants the same gate. Cross-ref B4 D6 (ORB machine) and M4 (sweep scoring) — this file is their arbiter, not their replacement.

**Why zero-wait.** Six small state machines + integer counters; the scoreboard is incremented on close events; O(6) per bar.

---

### S4. 0–100 Momentum/Volume/HTF Signal-Strength Score — *Reactive Trail System*

```python
score = min(momDist/0.6, 1.0) * 40                    # momentum distance (RSI-based)
      + clamp(V/SMA20 - 0.5, 0, 2) / 2 * 30           # volume excess (15 flat if no vol)
      + (HTF_close > HTF_EMA50 ? 30 : 10)              # HTF alignment (10 for misaligned)
```

**Mechanics.** A compact three-channel strength label (momentum 40 / participation 30 / higher-timeframe 30) attached to every flip — a quality tag for sizing or filtering, not a gate. The momentum channel saturates at momDist 0.6 (RSI 80/20) so extreme readings don't inflate past a strong reading; the volume channel measures *excess* over average (below-average volume scores 0). Useful as a universal signal-quality scalar; cross-ref S1/S2 for the heavier-weighted engines.

**Why zero-wait.** Three running scalars + one HTF comparison.

---

### S5. 5-Indicator Contrarian Vote (extreme-zone agreement counter) — *Order&Breake*

```python
LONG_VOTE = count of (each true):
    CCI(20) < -140            # deep negative CCI
    ADX > 18 and DI+ > DI-    # trend present, buyers in control
    RSI(14) < 40              # momentum washed out
    MFI(14) < 40              # money-flow washed out
    RVI(10) < 40              # relative volatility washed out
# signal = engulfing pattern AND stable_candle (|C-O|/TR > stability 0.4..0.9)
#          AND vote >= StrengthFilter   (default ~0)
```

**Mechanics.** A simple **extreme-agreement counter**: five independent oscillators (price-momentum CCI, trend DI, momentum RSI, flow MFI, relative-vol RVI) each vote when they're in their washed-out zone, and the pattern signal is gated by how many agree. It's a poor man's S1 without normalization — the value is the *breadth* requirement (multiple independent measurements agreeing the stretch is real). The engulfing+stability trigger itself is red-line (lagging pattern + oscillator), excluded; the vote counter is salvageable as a stretch-breadth gate for any mean-reversion entry.

**Why zero-wait.** Five running oscillators + one integer counter.

---

## §6 — Integration Blueprint (delta over Batch 4's L0–L5)

- **L0 Data (no new feeds).** Everything in this batch is OHLCV-computable from 1m klines; where the source approximates flow (close-location delta, side-volume splits), replace with **real aggTrade aggressor-side volume** (isBuyerMaker) — strictly better, zero extra infrastructure.
- **L1 Indicators (add):** running **Pearson r** via 5 sums (W1); **TQI** pipeline (W5: ER, z-vol, range-position, sign-persistence) + **effAtr** (W5); **99th-percentile** tracker over 1000 bars (W9 — sorted ring or t-digest); **CLV delta + EMA10** (S1); long-memory ATR family (ATR100/200/300 baselines for S1 scaling, M6, W4, M8); **cumulative mean body %** (W3); **sticky 8·ATR50 anchor** (M6).
- **L2 Structure (add):** **rejection-counter zone registry** with per-zone audit timers (M1 — 15/20-bar cadence, adverse-candle running counts); **OB→breaker state flag** with body-intrusion flip + re-entry confirm (M2); **volume-pivot OB** channel (W8); **range-capped internal OB** with side-% (M3); **RSI-run zones** (M7); **FVG 1.5%-of-range floor** (M8) on top of B4's CVD-zone and sweep machinery.
- **L3 Signals (add):** dry-bar displacement (W7); asymmetric 47/1 RSI-pivot divergence with 5–60 window + mutual exclusion (D2); dwell-reclaim (D3); touch-reclaim (D4); ORB single-break (D5); **6-setup arbiter** with one-way lock / cooldown / expiry (S3) as the top-level gate for L3 as a whole.
- **L4 Risk (add):** hybrid-SL policy switch max/min/wick (R1); **momentum-adaptive trail offset** (R2) — pair with W6's quality-adaptive band as two independent width knobs; **TQI TP scaling + proportional floors + ladder order-fix** (R3); **chronology policy** (R5: bar-start snapshots; same-bar priority as a backtest knob; tick engine resolves by event order); **1/3-split realized-R** accounting (R4); lifecycle gates (R6).
- **L5 Meta (new layer):** **per-setup scoreboard** (S3) — track →TP1/→TP3/stop/expired per strategy component on rolling windows and use it to size or disable components; **regime-grid R-monitor + gain auto-calibration** (W10) — 9 EWMA cells + clamped gain step; both are *measurement-driven* controls, the first of their kind across the five batches, and the highest-leverage additions for a live HFT engine.

---

## Appendix A — Per-File Exclusions (19 files)

1. **short and long** — entire file (mintick zigzag = lagging by construction; no signal survives the red lines).
2. **SFI MAGIC** — smoothrng(100)×2.3 deadband flip trigger (B3/4 family cross-ref); 61-style visual tail. Salvaged: ST-on-SMA10 ratchet, 1.5·ATR book-profit-then-ST-break exit.
3. **S&D zones (BigBeluga)** — nothing beyond M1 (the file *is* M1's first variant). CC-BY-NC-SA header noted.
4. **sfi scalper 1.0** — visual tail (close[13]/close[50] bar coloring, VWAP plot); fixed 2% SL kept in D1 only as context.
5. **NAS Ultimate Algo Remastered** — entire file (ST(4,11)+SMA13 = Haper/Fresh family, B3 cross-ref; 61-tier RSI gradient visual; pta_plot import visual-only).
6. **Pearson SLTP** — dead 4th strength term (EMA50>EMA200, a degenerate constant); nothing else.
7. **NEXT CANDLE PREDICTOR V4** — EMA8/21 cross trigger (red-line #2); "75% win rate" marketing claim (unverified, ignored).
8. **NOVA ALGO** — ST cross trigger; ALMA trend tracers; Hullma(600) trend cloud; ADX<15 sideways bar-coloring. Salvaged: M1 rejection counter + (latent) swing-volume ratio.
9. **RSI entry** — signal-EMA(9) oscillation cross (panel-only); 7-row status panel. Salvaged: D6.
10. **Scalper** — HTF trend-candle renderer; KC(3,4.5)-EMA "200 EMA"; percentVol(40·dev+30) dashboard; RSI-tier candle colors; OB/structure type scaffolding never wired to a signal. Salvaged: M1 v2 + FVG close-mitigation.
11. **PRECISION SNIPER** — EMA cross trigger (red-line #2); theme engine; webhook formatting. Salvaged: S2, R1 row, ratchet trail, backtest R-accounting (R4 row).
12. **phantom flow** — SuperTrend flip trigger (family cross-ref); FVG `security` with `lookahead_on` (mechanism flagged; same-TF salvageable); MTF high/low levels (display). Salvaged: W3, W4, W9, 2-scale leg structure (5/50), ATR200-tolerance EQH/EQL.
13. **Setup Scanner [GBB]** — nothing beyond S3/M4/M5/D3/D5 (the file *is* the portfolio arbiter). Telegram footer excluded.
14. **NOSTRADAMUS** — ST+SMA15 trigger; 4×KC(80) channel-balance fills; PAC channel; EMA200 long/short; percentVol(40·dev+30); 10-TF SMA50 slope panel; zigzag. Salvaged: W2 (flagship), PREDICTUM TP (≡ B3 §1.9, cross-ref only), 150-bar LR deviation channel (noted: standard OLS + max-deviation bands, low novelty).
15. **SELF-AWARE TREND SYSTEM** — nothing beyond W5/W6/R1/R3/R4 (the file *is* the TQI engine). Theme engine + dashboard excluded.
16. **Reactive Trail System** — nothing beyond R2/R4/R5/R6/S4 (the file *is* the reactive trail). KAMA/T3 implementations kept inline (standard). Theme + dashboard excluded.
17. **River Strategy** — dual smoothrng flip trigger (B3/4 family); WaveTrend(5,10) + 5-bar-fractal divergence (display-only, commented-out plotshapes); auto-trendlines (Lonesomeblue); SMMA33/144 crosses; candle-pattern barcolors; ORB (duplicate of D5 family, kept there); pivots/CPR/Camarilla/Fib-pivot level engines (standard formulas, no edge math); volume-S/R 5σ level detector kept inline in W8 notes. Salvaged: W7, W8, touch-count S/R (noted: pivot-touch counting over a 284-bar window, ≥6 touches in a 10%-width band — standard, low novelty).
18. **Order&Breake** — engulfing + RSI reversal trigger (red-line #2); RSI-tier barcolors; 7-tier RSI coloring; "Predicted Reversal" dashboard text. Salvaged: M2, M3, M6, M7, M8, S5.
19. **RSI divergence entry** — HTF trend filter via `lookahead_off` (live HTF value — flagged, excluded from extraction); all theme/label/box code. Salvaged: D2, R4 row.

---

## Appendix B — Porting Notes (Binance Spot HFT: 1m klines + aggTrade + bookTicker)

1. **Running Pearson r (W1).** Maintain Σx, Σy, Σxy, Σx², Σy² over a 20-deep ring of 1m closes; r in O(1) per bar; tick refinement: update with the running trade price instead of close for sub-minute latency. Cross at |r|=0.7 fires as an event.
2. **TQI (W5) tick cost.** ER: one rolling sum of |Δclose| over 20 bars (deque, O(1) amortized). z-volume: SMA/stdev via running sums. Range position: rolling min/max deque. Sign persistence: 10-integer sign buffer. Total < 1µs-class per bar; recompute on every closed 1m bar, not every tick (TQI is a *bar* quantity).
3. **99th percentile (W9).** Sorted 1000-float ring (bisect insert, O(n) worst case = 1000 — fine at 1/bar) or a t-digest for constant time. The normalization only needs to be *stable*, not exact.
4. **Nostalgia VP (W2).** Full recompute per closed 1m bar: 150 bars × 500 bins ≈ 75k multiply-adds (well under 1ms in C/numba, vectorizable in numpy). Intrabar: apply the same partition incrementally to the forming bar from aggTrade. Store up[]/dn[]/total[]; POC = argmax; VA70 expansion is O(Nbins).
5. **Real flow (S1 delta, M3 side-volume).** Replace close-location approximations with aggTrade's `isBuyerMaker` flag: buyVol += qty when isBuyerMaker==false (buyer-aggressor), sellVol += qty otherwise. The CLV formula stays as the fallback for kline-only replay.
6. **Volume-pivot OB (W8).** Rolling 20/20 pivot on the volume channel (confirmation = 20 closed bars). Zones freeze; mitigation = running-min(close, 20) vs zone bottom.
7. **Rejection audits (M1).** Per-zone `barsSinceCreation` counter; run the audit when `barsSinceCreation % k == 0` (k=15 or 20). Adverse-candle counts are running sums over the audit window — O(1) update.
8. **Sticky anchor (M6).** Two scalars; the anchor only moves on |Δ| > 8·ATR50 — ATR50 itself is a running sum.
9. **Dry-bar test (W7).** SMA55/stdev55 via running sums; on each closed 1m bar compare `min(low of prior bar) > band.top` — one comparison.
10. **Asymmetric RSI pivot (D2).** Maintain candidate pivot lows (RSI < all of prior 47 bars); confirm 1 bar later; store (rsi, price, barIndex) snapshots; the 5–60 bar window is `barIndex - prev.barIndex`.
11. **Dwell-run counters (D3/D4).** Integer run-counters on closed bars (belowRun, aboveRun, barssince-touch); reset on the opposite condition.
12. **Setup arbiter (S3).** Six state machines + per-setup 6-integer counters; fire gate = 3 boolean checks; the scoreboard's →TP1% is `cT1/cFired` with a 10-sample floor. This is the natural home for **live component sizing**: allocate order size ∝ rolling →TP1% (with a floor) per setup.
13. **Regime grid (W10).** 9 EWMA scalars + counters; update only on trade close. The gain step (±0.05, clamped [0.1, 0.9], 5-signal cooldown) maps directly to "modulate the TQI band-width strength, or the global size, per measured regime edge."
14. **Chronology (R5).** The tick engine resolves same-bar TP/SL by actual event order — the Pine optimistic/conservative policies are backtest-parity knobs only. Keep the bar-start BE snapshot: on TP1 print, raise the stop *after* recording the bar's open state.
15. **Watermark/dashboard noise.** 10 of 19 files (all @mrexpert_ai / WillyAlgoTrader / SimpleForexTools) carry top-center Telegram dashboards and theme engines — pure visual, zero signal content; no porting action.
