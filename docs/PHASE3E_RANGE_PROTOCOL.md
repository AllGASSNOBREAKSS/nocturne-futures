# Fixed two-hour range quantile comparison

Use the unchanged hourly two-hour datasets and first 80% day groups only.
Purged expanding folds: 60 train, 20 calibration, 30 test days; one-hour embargo.
Train-only unconditional empirical quantiles are the baseline. Fit LightGBM
quantile regressors at 0.5/0.8/0.9, 100 trees, seven leaves, min child samples 50,
learning rate .05, seed 7, one worker, existing trailing numeric features.
Adjust each quantile by its calibration residual quantile, then monotonically
rearrange outputs. Report pinball loss, coverage, negative-value clipping and
crossing count, with paired three-day block intervals versus baseline.
No tuning or independent-final-period scoring. These are total future high-low
ranges, not directional movement or target-before-stop probabilities. No
exchangeability or finite-sample conformal coverage guarantee is claimed.
