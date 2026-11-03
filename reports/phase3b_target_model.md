# Phase 3B.1 Target-First Model

Binary rows: **123** from **75** signals; base rate **0.520**.
Strategies: {'vwap_value_aligned_pullback': 65, 'opening_range_ib_breakout_retest': 42, 'vah_val_failed_auction': 16}.
Split: train 79 / validation 22 / test 22 rows.

| Model | Brier | Log loss | Accuracy | ECE | AUC |
|---|---:|---:|---:|---:|---:|
| frequency | 0.2688 | 0.7309 | 0.364 | 0.1933 | 0.5 |
| logistic | 0.2735 | 0.7752 | 0.591 | 0.2001 | 0.4554 |
| gbm | 0.2447 | 0.6961 | 0.682 | 0.1535 | 0.4107 |

## Expanding-window folds

| Model | Folds | Mean Brier | Mean log loss | Mean accuracy |
|---|---:|---:|---:|---:|
| frequency | 3 | 0.2801 | 0.7539 | 0.330 |
| logistic | 3 | 0.2687 | 0.7739 | 0.608 |
| gbm | 3 | 0.2652 | 0.8145 | 0.630 |

## Decision

**NO_PROMOTION.** Best test Brier is 0.2447 (gbm); AUC=0.4107; ECE=0.1535; test n=22; test positive rate=0.636 vs train 0.443. A Brier gain without ranking skill or calibration is a class-shift artifact, not a validated edge.

The sample is small (three strategies, 60 days of 5-minute bars). No model is promoted unless it beats the frequency baseline on the untouched test split and the expanding folds, with acceptable calibration.

