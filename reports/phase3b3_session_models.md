# Phase 3B.3 Session Direction and Consolidation

Rows: **147** across **49** days.
Sessions: {'ASIA': 49, 'LONDON': 49, 'NEW_YORK': 49}.
Direction labels: {'BULL': 72, 'BEAR': 69, 'NEUTRAL': 6}.
Range states: {'EXPANSION': 56, 'CONSOLIDATION': 47, 'NORMAL': 44}.
Split: train 87 / validation 30 / test 30 rows.

## Direction (next same session)

| Model | Log loss | Brier | Accuracy | ECE | BEAR recall | NEUTRAL recall | BULL recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| frequency | 0.8650 | 0.5950 | 0.400 | 0.1977 | 0.0 | None | 1.0 |
| logistic | 2.5272 | 0.9974 | 0.400 | 0.5198 | 0.0 | None | 1.0 |
| gbm | 1.3781 | 0.9224 | 0.267 | 0.4789 | 0.0556 | None | 0.5833 |

## Consolidation (next same session range contraction)

| Model | Brier | Log loss | Accuracy | Precision | Recall | ECE | AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| frequency | 0.2333 | 0.6596 | 0.633 | 0.000 | 0.000 | 0.0333 | 0.5 |
| logistic | 0.1496 | 0.4677 | 0.800 | 1.000 | 0.455 | 0.1925 | 0.8995 |
| gbm | 0.1947 | 0.5779 | 0.633 | 0.500 | 0.091 | 0.1690 | 0.7656 |

## Decisions

- Direction: **NO_PROMOTION**. best=frequency; test n=30; log_loss=0.8650; frequency=0.8650
- Consolidation: **NO_PROMOTION**. best=logistic; test n=30; brier=0.1496; frequency=0.2333; auc=0.8995; ece=0.1925

The sample is 60 days of 5-minute bars. The next-session horizon is long
and overlaps macroeconomic regimes; no result here is a validated edge.

