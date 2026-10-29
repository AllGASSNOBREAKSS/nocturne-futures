# ML baseline: no edge yet

The friend's suggestion was right in principle: use the historical data to predict the
trend, not a single price. This is the first, deliberately boring attempt.

## Setup

- **Data:** 15 years of daily front-month futures, committed as CSVs in
  `data/studies/daily_15y/`.
- **Features (11):** 1-day, 5-day and 20-day returns; ATR(14)/price; distance to SMA20
  and SMA50; 20-day realized vol; day-of-week dummies (Tuesday–Friday).
- **Target:** next-day close-to-close return.
- **Model:** ridge regression (lambda = 10), refit every 21 trading days on an expanding
  window, first prediction after 750 sessions (~3 years). No shuffling, no leakage.
- **Metric:** out-of-sample directional accuracy, compared with the always-up base rate.

## Results

| Code | n | Direction accuracy | Base rate (always up) | MAE | Correlation |
|---|---:|---:|---:|---:|---:|
| ES | 2,972 | 50.1% | 53.5% | 0.73% | 0.043 |
| NQ | 2,972 | 51.5% | 55.6% | 0.96% | 0.050 |
| GC | 2,971 | 51.3% | 52.6% | 0.74% | 0.018 |
| SI | 2,970 | 52.3% | 52.0% | 1.40% | 0.023 |

## Interpretation

- On ES, NQ and GC the model is **worse than predicting "up" every day**. On silver it is
  0.3 percentage points better, which is noise.
- The correlations are between 0.018 and 0.050. There is almost no linear signal in
  price-derived features at the daily horizon.
- The MAE is roughly the size of an average daily move. The model is not adding
  information; it is predicting near zero with small variation.

This is a useful result. It says the value of the product is **not** a better directional
classifier on price alone. It is the disciplined process: a dated call, explicit levels,
a probability map, and an honest scorecard.

## What would make the ML layer worth using

1. **Better features.** Cross-asset (real yields, DXY, oil, credit spreads), positioning
   (CFTC, ETF flows), options skew, and event windows. Price-only features are exhausted.
2. **A different target.** Predicting the *distribution* of the session range, or the
   probability of touching a level, is more tractable than the sign of the close.
3. **Calibration, not accuracy.** A model that says "60% chance of closing inside this
   band" and is right 60% of the time is more useful than one that is 52% directional.
4. **Event conditioning.** Fit separate models for FOMC days, CPI days, and quiet days.
   Pooling them washes out the only structure that matters.

Until then, the ML layer stays a baseline in the repo, clearly labelled, and the published
call stays a human-reviewed scenario map.
