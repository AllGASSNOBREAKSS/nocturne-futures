# Model Validation

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

## Reproduce

```bash
python -m nocturne train --instrument NQ
```

The command writes a new `NQ-<model>-<timestamp>/` directory with
`metadata.json`, `model.joblib` and `summary.json`.
