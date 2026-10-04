# L0084-ENTRY-MIX — VERDICT (proposed; Lead re-derives)

- Lane: L0084-ENTRY-MIX (one paper, one theme)
- Frozen candidate: null (CASH)
- Freeze UTC: 2026-10-04T15:10:39Z
- Integrity: PASS (18 of 18 checks recorded, plus 16b full-run confirmation)

## before / after / why / period

| item | before | after | why | period |
|---|---|---|---|---|
| entry rule | singletons only (L0083) | pair/triple mix of the locked 52-grid, 3 modes | paper §6 screening | 2021-01-01..2026-09-27, 8 rolling prefixes |
| container | close-price proxy ±1/6 | next-open fill, ±1.5 ATR, 18 bars, gaps first | paper §7 | same |
| cost | cheaper legacy table | $0.052 round trip once, identical to all | constitution v2 | same |

Status vocabulary: an eligible hypothesis is a screening result only. No adoption, no live orders, no profit forecast.

## why nothing qualified (descriptive, not a selection input)

- Attempts per prefix: 52 singletons + 3,978 pair modes = 4,030 measured; triples measured: 0 (no pair qualified, criteria were not relaxed).
- The fixed container needs a high barrier win rate just to break even: median actual-cost breakeven reference across pairs in 2026H1 is 0.5459 (0.5 + mean(cost_ATR)/3), with mean cost_ATR ≈ 0.12 ATR.
- The contemporaneous no-signal book (buy whenever flat, same container and costs) loses money in EVERY window: barrier win 43.98%-54.87%, net expectancy from -0.1576 to -0.0045 dollars per trade; the best fragments of the grid reach only ≈1.6 PF for a single window and fail the all-window gates.
- Gate failure census (pairs, final prefix): 3,850 fail the ≥8-positive-assets gate in at least one inner window, 3,788 fail PF ≥ 1.3, 3,790 fail the positive lower bound, 3,792 fail the paired-superiority lower bound; 0 pass everything.

## rolling selections

| prefix | selected | stage | target n | target expectancy$ |
|---|---|---|---|---|
| 2023H1 | CASH | cash | 0 | not measured |
| 2023H2 | CASH | cash | 0 | not measured |
| 2024H1 | CASH | cash | 0 | not measured |
| 2024H2 | CASH | cash | 0 | not measured |
| 2025H1 | CASH | cash | 0 | not measured |
| 2025H2 | CASH | cash | 0 | not measured |
| 2026H1 | CASH | cash | 0 | not measured |
| 2026H2p | CASH | cash | 0 | not measured |