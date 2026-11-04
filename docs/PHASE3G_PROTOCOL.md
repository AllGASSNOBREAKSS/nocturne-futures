# Phase 3G fixed protocol

Locked before the Phase 3G experiments.

## Data

Free sources first. Yahoo daily history is unofficial and stored with raw bytes and
manifests. Index levels, ETFs, futures proxies and rates stay separate. Continuous
futures proxies are never treated as raw contracts. No 40-year NQ intraday claim.

## Reserved periods

- Daily direction: 2024-01-01 onward is reserved and unscored.
- Analogues: same reservation; queries start 1995 with expanding history only.
- Level reactions: first 80% of cached sessions only.
- Seasonality: descriptive on all history, but its features are only tested in the
  daily walk-forward, which respects the reservation.

## Walk-forward

Expanding annual folds on ^NDX, 1990-2023, two-year calibration block, five-day
embargo between partitions. Frequency base rate and time-separated Platt
calibration. Brier, AUC, accuracy and per-decade breakdown. No hyperparameter
search; logistic C=0.2 fixed.

## Feature families

Each family is added separately to the price/volatility baseline: volatility
context (VIX), rates context (TNX), cross-market (S&P and futures relative), and
seasonality. A family is only useful if it improves out-of-sample Brier and AUC.

## Analogues

Eight scale-free features, Euclidean distance, k in {50, 100, 250}, weighted
neighbour vote, 5-day embargo, minimum 500 history windows. Compare against the
frequency base rate. Similarity is not causation.

## Seasonality

Year-block bootstrap (whole years resampled) for 95% intervals and
Benjamini-Hochberg control within each calendar family. Minimum 30 observations
per group. Effect size matters more than significance at n > 20,000.

## Level reactions

Levels built one hour after the RTH open from point-in-time data. Forward horizon
48 bars. Distinct events: touch, acceptance (3 closes beyond), rejection (0.5 ATR
adverse without 1 ATR progress), break-through (1 ATR progress), target-before-stop
(2 ATR target versus 1 ATR stop from the touch). Same-bar target+stop is ambiguous
and excluded from the binary outcome. Wilson intervals reported.

## Promotion

Unchanged fail-closed gates. Passing yields review eligibility only.
