# Phase 3F fixed protocol

Locked before running the Phase 3F experiments. Latest 20% of days in every
dataset remains unscored; prior phases already examined this cache, so no result
here is an independent final holdout.

## Direction diagnostics

Unchanged three-class labels. Logistic (C=0.5) and LightGBM (100 trees, 7 leaves,
0.05 learning rate, min child 50, seed 7, one worker), purged 60/20/30-day folds,
one-hour embargo. Compare: existing time-separated calibrator, vector scaling on
log-odds, and a two-stage model (material vs neutral, then bull vs bear given
material). No class weighting is applied; it cannot create directional signal and
would distort probability calibration. Abstention is reported as a coverage/
accuracy trade-off, not as a promoted decision rule. Report material AUC and
bull-vs-bear AUC conditional on material, because aggregate Brier can improve from
activity detection alone.

## Range quantiles

Same labels and folds as Phase 3E. Compare unconditional train quantiles, the
Phase 3E global residual adjustment, expanding rolling residuals with a one-day
gap (minimum 200 residuals), and three volatility buckets with global fallback
when a bucket has fewer than 200 calibration rows. Rearrange monotonically and
clip at zero. Report pinball loss, coverage, median width, coverage by volatility
bucket and paired day-block intervals. Total range only; no directional claim and
no conformal guarantee.

## Session ranges

Complete five-minute windows only, expanding empirical quantiles with a minimum
20 complete sessions, no same-day peeking. ASIA below the minimum is reported as
insufficient rather than estimated.

## Target survival

Fixed 50/100/150/200/350/500 point targets, original strategy stops, 24 complete
five-minute bars, one tick slippage and $2.50 commission per side. Outcomes:
target first, stop first, neither. Same-bar target+stop excluded; truncated windows
censored; timeouts censored, not stop losses. ATR and clock features use only bars
available at the signal. Signals stay whole within folds. Frequency baseline,
multinomial logistic and LightGBM, time-separated calibration. Report per-distance
event counts and Aalen-Johansen incidence. Do not fit a model where the event
count is too small to support it.

## Fusion

Equal-weight average of the two calibrated direction models, declared before
evaluation. No fitted weights and no strategy confluence. If it does not beat the
best standalone model it is not adopted.

## Promotion

Existing gates unchanged: independent holdout, sample adequacy, point-in-time
provenance, separate calibration, regime stability, class quality, rollback
reference, baseline improvement, ECE ≤ 0.05, binary AUC ≥ 0.55. Passing yields
`ELIGIBLE_FOR_REVIEW`, never automatic activation.
