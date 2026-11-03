# Phase 3E fixed development protocol

No promotion and no final-holdout access. Existing dates have been examined in
prior phases; new experiments remain retrospective development evidence.

Replay: cached five-minute NQ/ES, first 80% of session days, ten-day warmup,
16:00 UTC every fifth development day. Forecast only from available prefix;
evaluate only against development history. Freeze original forecasts separately
from outcome files. Missing macro data remains unavailable. This is not live
shadow or execution. Run future-mutation invariance tests.

Hourly ablation: existing two-hour datasets, original labels and purged folds;
60 train / 20 calibration / 30 test day groups, expanding window, one-hour
embargo. Keep final 20% unscored. Fixed logistic and optional LightGBM (100 trees,
7 leaves, learning rate 0.05, min child samples 50, seed 7, one worker).
Compare full features, without momentum/efficiency, without volume, without
clock, and without volatility/range group. Do not select new thresholds or
hyperparameters from results. Report Brier, class recall, log loss, ECE and
paired day-block uncertainty versus frequency.

Target diagnostics: Phase 3D fixed-distance development rows. Compare only nested
targets with identical signal, stop, entry, horizon and cost assumptions. Check
touch and target-first monotonicity where outcomes are known. Summarize time to
target conditional on observed touches; do not call censor-biased counts survival
probabilities. Strategy candidate PnL is not an executable portfolio ledger.

Authenticated Databento/ALFRED paths use synthetic test transport fixtures when
keys are unavailable. No fixture enters market history or model training.
