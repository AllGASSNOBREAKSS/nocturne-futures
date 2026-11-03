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

## Backtest: ORB on NQ, 60 days of 5-minute bars

Command:

```bash
python -m nocturne backtest --instrument NQ --days 60
```

Result (costs: $2.50/contract/side, 1 tick slippage, 1 contract):

| Metric | Value |
|---|---:|
| Trades | 44 |
| Win rate | 50.0% |
| Net dollars | **+$8,137.50** |
| Net points | +439.88 |
| Profit factor | 1.247 |
| Expectancy | +$184.94/trade |
| Max drawdown | **$16,105.00** |
| Long side | +$292.50 |
| Short side | +$7,845.00 |
| Timeout exits | 40 / 44 |

### Honest reading

- The result is **not** a validated edge. Forty of 44 trades exited at the
  horizon, not at a target. The strategy is effectively a directional hold with
  a wide stop, and the P&L is concentrated on the short side.
- The sample is 60 days in one regime. It is not walk-forward parameter
  selection, and it does not include a second instrument.
- The max drawdown is roughly twice the net profit. Position sizing would need
  to be conservative even if the result survived out-of-sample testing.
- The raw trade ledger is committed at `reports/backtest_orb_NQ.json`.

## Promotion rule

A strategy is not promoted unless it survives:

1. multiple instruments and volatility regimes,
2. walk-forward parameter selection with a held-out final window,
3. cost/slippage stress (2–4 ticks),
4. ablation against the no-strategy baseline,
5. a minimum trade count and drawdown constraint.

None of the three candidates has passed this gate.
