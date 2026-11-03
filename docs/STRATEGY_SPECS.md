# Strategy Specifications

Three executable candidates. Each is a research hypothesis, not a validated
edge. All use RTH bars and the session clock.

## 1. Opening Range / Initial Balance breakout

- **ID:** `opening_range_ib_breakout_retest`
- **Entry:** RTH close beyond the 60-minute IB high/low by 2 ticks.
- **Stop:** opposite side of the IB.
- **Targets:** 1R / 2R / 3R.
- **Horizon:** 24 bars.
- **Data:** RTH bars, session clock.
- **Known limitation:** a one-shot rule; no retest confirmation in the default
  configuration (`retest_only` is a reserved flag).

## 2. VWAP trend pullback

- **ID:** `vwap_value_aligned_pullback`
- **Entry:** price above a rising session VWAP, pullback within 0.25 × ATR of
  VWAP, close back above VWAP.
- **Stop:** recent 3-bar low or VWAP − 0.75 × ATR, whichever is lower.
- **Targets:** 1R / 2R.
- **Horizon:** 18 bars.
- **Data:** RTH bars and volume.
- **Known limitation:** VWAP is computed from bars, not true trades; with true
  trades the VWAP would be exact.

## 3. VAH/VAL failed auction

- **ID:** `vah_val_failed_auction`
- **Entry:** excursion beyond prior VAH/VAL by 2 ticks, then a close back inside
  value.
- **Stop:** beyond the excursion extreme.
- **Target:** prior POC (or 1R if POC is on the wrong side).
- **Horizon:** 18 bars.
- **Data:** prior session profile.
- **Known limitation:** the demo uses a **bar-approximation** profile. It is
  labelled `BAR_APPROXIMATION`; it is not exchange-accurate volume-at-price.

## Phase 3A held-out study

Command:

```bash
python -m nocturne study
```

Chronological split: first 60% development, last 40% holdout. Costs:
$2.50/contract/side, 1-tick base slippage, 1 contract.

| Instrument | Strategy | Split | Trades | Win % | Net $ | PF | Max DD $ | Timeouts |
|---|---|---|---:|---:|---:|---:|---:|---:|
| NQ | ORB | development | 27 | 29.6 | −18,730 | 0.313 | 18,730 | 26 |
| NQ | ORB | holdout | 17 | 76.5 | +23,670 | 4.799 | 2,855 | 15 |
| NQ | VWAP | development | 27 | 59.3 | +1,911 | 1.160 | 3,932 | 4 |
| NQ | VWAP | holdout | 15 | 73.3 | +8,398 | 2.285 | 3,131 | 1 |
| NQ | value | development | 16 | 56.2 | +2,935 | 1.538 | 4,160 | 3 |
| NQ | value | holdout | 12 | 25.0 | −6,170 | 0.475 | 6,555 | 1 |
| ES | ORB | development | 27 | 33.3 | −5,853 | 0.580 | 7,438 | 23 |
| ES | ORB | holdout | 19 | 47.4 | +3,665 | 1.531 | 2,410 | 16 |
| ES | VWAP | development | 28 | 35.7 | −5,342 | 0.401 | 6,891 | 4 |
| ES | VWAP | holdout | 14 | 64.3 | +1,149 | 1.358 | 2,080 | 1 |
| ES | value | development | 14 | 64.3 | −320 | 0.902 | 2,765 | 2 |
| ES | value | holdout | 14 | 64.3 | +2,030 | 1.907 | 1,165 | 1 |

Cost stress (holdout net dollars):

| Instrument | Strategy | 1 tick | 2 ticks | 3 ticks | 4 ticks |
|---|---|---:|---:|---:|---:|
| NQ | ORB | 23,670 | 23,415 | 23,160 | 22,905 |
| NQ | VWAP | 8,398 | 8,183 | 7,968 | 7,753 |
| NQ | value | −6,170 | −6,350 | −6,530 | −6,710 |
| ES | ORB | 3,665 | 2,953 | 2,240 | 1,528 |
| ES | VWAP | 1,149 | 549 | 49 | −595 |
| ES | value | 2,030 | 1,505 | 980 | 455 |

### Why 41 ORB trades timed out

Median risk (entry to opposite IB) is **208.9 NQ points**; median MFE is only
**0.26R**; 4.5% of trades reach 1R and 0% reach 2R. All 41 timeouts had MFE
below 1R. The 60-minute IB is too wide for a 24-bar horizon, so the 1R/2R/3R
targets are structurally unreachable.

### Honest reading

- The ORB development is deeply negative and the holdout is strongly positive:
  a regime sign flip, not an edge. Fifteen of 17 holdout trades still time out.
- NQ VWAP is positive in both splits; ES VWAP is negative in development. The
  value strategy flips sign between instruments and splits.
- No strategy survives the promotion gate. The raw ledgers are in
  `reports/phase3a_*.json`; the summary is `reports/phase3a_backtests.md`.

## Promotion rule

A strategy is not promoted unless it survives:

1. multiple instruments and volatility regimes,
2. walk-forward parameter selection with a held-out final window,
3. cost/slippage stress (2–4 ticks),
4. ablation against the no-strategy baseline,
5. a minimum trade count and drawdown constraint.

None of the three candidates has passed this gate.
