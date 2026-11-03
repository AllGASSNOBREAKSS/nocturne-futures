# Model Validation

Phase 3D implementation and frozen objectives are documented in
`../PHASE3D_PROTOCOL.md`. `research/validation.py` implements forward-only
day/signal grouping, inclusive label-end purging, elapsed embargo, rolling and
expanding folds, holdout quarantine and day-block bootstrap. Reports in
`reports/phase3d*validation.json` include actual fold counts, dates, class balance,
calibration and uncertainty. Current-vintage FRED values are not model features.
All models remain research-only. Previously inspected history is not a fresh
final holdout, even when withheld from these reruns.

**Instrument:** NQ  
**Data:** 15 years of daily front-month bars, extended to 2026-11-02 in
`data/market/daily/NQ.csv`.  
**Last run:** 2026-11-03  
**Model registry:** `models/registry/NQ-frequency-20261103T165232/`

## Label definition

Triple barrier, long entry at the next session open:

- target: +1.5 × ATR(14)
- stop: −1.0 × ATR(14)
- horizon: 5 sessions
- same-bar stop+target: `AMBIGUOUS`, excluded from binary training
- timeout: excluded from binary training, reported separately

Binary sample: **2,940** resolved TP/SL rows. Base rate of `TP_FIRST`: **42.1%**.

## Validation protocol

- Chronological walk-forward; no shuffling.
- Minimum training window: 750 sessions.
- Test block: 21 sessions.
- Calibration slice: last 20% of each training window, Platt scaling.
- Evaluation: 2,167 out-of-sample predictions.

## Results

| Model | n | Brier | Log loss | Accuracy | ECE |
|---|---:|---:|---:|---:|---:|
| Historical frequency | 2,167 | **0.2474** | **0.6884** | 0.563 | 0.048 |
| Logistic | 2,167 | 0.2493 | 0.6927 | 0.558 | 0.076 |
| Hist. gradient boosting | 2,167 | 0.2488 | 0.6914 | 0.574 | 0.067 |

**Promotion status: `RESEARCH_ONLY`.** The frequency baseline is best; neither
logistic nor boosted trees beat it by the required margin. No model is promoted.

## Interpretation

- The accuracy is mostly the majority-class rate; the base rate is 42.1%
  TP-first, so a model that predicts SL-first often scores 56–57% without skill.
- Brier scores are tightly clustered around the constant-frequency baseline.
- Calibration is imperfect: the 0.30–0.40 bin observed 0.43, the 0.40–0.50 bin
  observed 0.41. The reliability table is stored in the registry metadata.
- This is a **negative result**, and it is recorded as one.

## What this does not prove

- It does not test intraday barriers, tick fills, or order-flow features.
- It does not include CFE VX or true ZN/ZB futures history.
- It does not validate the ORB backtest or any strategy P&L.
- It does not justify live trading.

## Phase 3A audit

Four label geometries were tested with the same walk-forward protocol:

| Config | TP | SL | Timeout | Ambiguous | Binary n | Base rate |
|---|---:|---:|---:|---:|---:|---:|
| 1.5 ATR / 1.0 ATR / 5d | 1,218 | 1,722 | 811 | 10 | 2,940 | 41.4% |
| 1.0 / 1.0 / 3d | 1,584 | 1,374 | 778 | 25 | 2,958 | 53.5% |
| 1.0 / 0.5 / 5d | 1,320 | 2,258 | 111 | 72 | 3,578 | 36.9% |
| 2.0 / 1.0 / 10d | 1,166 | 2,109 | 479 | 7 | 3,275 | 35.6% |

Walk-forward Brier:

| Config | Frequency | Logistic | GBM |
|---|---:|---:|---:|
| 1.5 / 1.0 / 5d | **0.2474** | 0.2493 | 0.2483 |
| 1.0 / 1.0 / 3d | **0.2509** | 0.2525 | — |
| 1.0 / 0.5 / 5d | **0.2321** | 0.2332 | — |
| 2.0 / 1.0 / 10d | **0.2327** | 0.2343 | — |

Frequency wins in every geometry. The lower Brier in the tight-stop and
long-horizon configs reflects a more imbalanced class distribution, not skill.
Cross-config Brier comparisons are misleading.

**Regime stability (current config, logistic):** low-vol Brier 0.2535,
accuracy 0.522; high-vol Brier 0.2452, accuracy 0.595. Yearly Brier ranges
0.229–0.266 and accuracy 0.457–0.700. The model is not stable.

**Economic check:** at p ≥ 0.50 the threshold strategy loses **−$36,590** after
$15/round-trip costs (217 trades, max DD $80,888). At p ≥ 0.55/0.60 it shows
+$42,152/+$46,045 on only **42/18 trades**. That is sparse, post-hoc selection,
not a validated edge.

Full report: `reports/ml_audit_NQ.md` and `reports/ml_audit_NQ.json`.

## Target-level dataset

`src/nocturne/research/target_dataset.py` records one row per `(signal,
candidate target)` with entry, stop, target, horizon, target-first outcome,
MFE/MAE and bars-to-target. Build it with:

```bash
python -m nocturne dataset --instrument NQ --strategy vwap
```

Committed datasets:

| File | Rows | TP | SL | Timeout |
|---|---:|---:|---:|---:|
| `target_dataset_NQ_orb.csv` | 132 | 2 | 3 | 127 |
| `target_dataset_NQ_orb_diag.csv` | 132 | 24 | 18 | 90 |
| `target_dataset_NQ_vwap.csv` | 84 | 32 | 33 | 19 |
| `target_dataset_NQ_value.csv` | 28 | 10 | 14 | 4 |

The ORB actual-target set is not trainable (2 positives). The VWAP set is the
first usable candidate; any model must split chronologically and leave the last
40% untouched.

## Phase 3B target-first model

A second experiment used the VWAP, revised-ORB and value-area target datasets
with point-in-time intraday features and signal-grouped chronological splits:
123 binary rows from 75 signals, base rate 0.520. Test Brier: frequency 0.2688,
logistic 0.2735, GBM 0.2447. The GBM’s AUC is 0.411, ECE 0.154, test n=22, and
the test positive rate is 0.636 vs 0.443 in training. **NO_PROMOTION.** Full
report: `docs/PHASE3B_FINDINGS.md`.

## Phase 3B.3 session models

Session dataset: 147 rows across 49 days (ASIA/LONDON/NEW_YORK), chronological
day split 87/30/30. Direction target is BEAR/NEUTRAL/BULL over the next same
session; consolidation is next-session range ≤ 0.8× current range.

Direction test log loss: frequency 0.8650, logistic 2.5272, GBM 1.3781.
NEUTRAL is only 6/147 and absent from the test split. **NO_PROMOTION.**

Consolidation test Brier: frequency 0.2333, logistic 0.1496 (AUC 0.8995, ECE
0.1925), GBM 0.1947. The logistic result is promising but fails the calibration
and sample-size gates. **NO_PROMOTION.**

Level reachability is an empirical forward-MFE touch probability, not a
target-before-stop probability. Full report: `docs/PHASE3B3_FINDINGS.md`.

## Reproduce

```bash
python -m nocturne train --instrument NQ
python scripts/ml_audit.py
```

The train command writes a new `NQ-<model>-<timestamp>/` directory with
`metadata.json`, `model.joblib` and `summary.json`. The audit writes
`reports/ml_audit_NQ.json` and `.md`.
