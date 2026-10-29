# Roadmap

## v0.2 — distribution first

- Replace the three named scenarios with five overlapping price buckets per instrument.
- Publish a modal outcome and an expected close separately; flag disagreements.
- Add a real-yield axis: 10Y TIPS proxy, 2s10s slope, DXY.
- Add options-implied moves: VIX for ES, GVX for gold, VXSLV for silver.
- Automate level selection from the candidate book, with a review step.
- Add a running scorecard: direction, band, range, Brier, MAE by instrument and event type.

## v0.3 — event-aware ML

- Feature set: cross-asset returns, real yields, DXY, oil, credit spreads, VIX term
  structure, CFTC positioning, ETF flows, event dummies.
- Targets: probability of touching R1/S1, probability of closing inside each bucket,
  expected absolute range.
- Validation: purged walk-forward with an embargo around events; log loss and Brier,
  not accuracy alone.
- Baseline to beat: the always-up rate and the ATR range. If it cannot beat both, do not
  ship it.

## v1.0 — execution and accountability

- Paper-trade every published call; track slippage and fill assumptions.
- Risk module: position sizing by ATR, max loss per call, correlation across ES/NQ.
- Live dashboard that updates the scorecard after the settlement.
- Public archive of every call, including the misses. The archive is the product.

## Non-goals

- A single "price will be X" number.
- Intraday scalping signals.
- Anything that requires a proprietary exchange feed to be useful.
