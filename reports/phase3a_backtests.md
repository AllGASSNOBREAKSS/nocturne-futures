# Phase 3A Backtest Study

Chronological development (first 60%) and holdout (last 40%).
Costs: $2.50/contract/side, 1-tick base slippage; stress at 2/3/4 ticks.
ORB exits are capped at the RTH session; targets are 1R/2R/3R.

| Instrument | Strategy | Split | Trades | Win % | Net $ | PF | Max DD $ | Timeouts |
|---|---|---|---:|---:|---:|---:|---:|---:|
| NQ | orb | development | 27 | 29.6 | -18730.00 | 0.313 | 18730.00 | 26 |
| NQ | orb | holdout | 17 | 76.5 | 23670.00 | 4.799 | 2855.00 | 15 |
| NQ | vwap | development | 27 | 59.3 | 1911.32 | 1.160 | 3932.21 | 4 |
| NQ | vwap | holdout | 15 | 73.3 | 8397.94 | 2.285 | 3130.92 | 1 |
| NQ | value | development | 16 | 56.2 | 2935.00 | 1.538 | 4160.00 | 3 |
| NQ | value | holdout | 12 | 25.0 | -6170.00 | 0.475 | 6555.00 | 1 |
| ES | orb | development | 27 | 33.3 | -5852.50 | 0.580 | 7437.50 | 23 |
| ES | orb | holdout | 19 | 47.4 | 3665.00 | 1.531 | 2410.00 | 16 |
| ES | vwap | development | 28 | 35.7 | -5341.75 | 0.401 | 6891.06 | 4 |
| ES | vwap | holdout | 14 | 64.3 | 1148.75 | 1.358 | 2079.69 | 1 |
| ES | value | development | 14 | 64.3 | -320.00 | 0.902 | 2765.00 | 2 |
| ES | value | holdout | 14 | 64.3 | 2030.00 | 1.907 | 1165.00 | 1 |

## Cost stress (holdout, net dollars)

| Instrument | Strategy | 1 tick | 2 ticks | 3 ticks | 4 ticks |
|---|---|---:|---:|---:|---:|
| NQ | orb | 23670.00 | 23415.00 | 23160.00 | 22905.00 |
| NQ | vwap | 8397.94 | 8182.94 | 7967.94 | 7752.94 |
| NQ | value | -6170.00 | -6350.00 | -6530.00 | -6710.00 |
| ES | orb | 3665.00 | 2952.50 | 2240.00 | 1527.50 |
| ES | vwap | 1148.75 | 548.75 | 48.75 | -595.00 |
| ES | value | 2030.00 | 1505.00 | 980.00 | 455.00 |

