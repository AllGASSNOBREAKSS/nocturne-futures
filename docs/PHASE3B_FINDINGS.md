# Phase 3B Findings — Predictive Intelligence V1

**Date:** 2026-11-03  
**Branch:** `feat/phase3b` (merged to `main`)  
**Status:** Phase 3B.1 and the feasible Phase 3B.2 layers are implemented. No model is promoted.

## 1. Target-first model (Phase 3B.1)

Data: VWAP + revised-ORB + value-area target datasets, 60 days of 5-minute NQ bars, point-in-time features.

| Item | Value |
|---|---:|
| Target rows | 244 |
| Binary rows (TP vs SL) | **123** |
| Originating signals | **75** |
| Base rate | **0.520** |
| VWAP / ORB / value rows | 65 / 42 / 16 |
| Split rows (train/val/test) | 79 / 22 / 22 |
| Train / test positive rate | 0.443 / 0.636 |

Test results:

| Model | Brier | Log loss | Accuracy | ECE | AUC |
|---|---:|---:|---:|---:|---:|
| Frequency | 0.2688 | 0.7309 | 0.364 | 0.1933 | 0.500 |
| Logistic | 0.2735 | 0.7752 | 0.591 | 0.2001 | 0.455 |
| GBM | **0.2447** | 0.6961 | 0.682 | 0.1535 | 0.411 |

Expanding-window folds:

| Model | Folds | Mean Brier | Mean log loss | Mean accuracy |
|---|---:|---:|---:|---:|
| Frequency | 3 | 0.2801 | 0.7539 | 0.330 |
| Logistic | 3 | 0.2687 | 0.7739 | 0.608 |
| GBM | 3 | 0.2652 | 0.8145 | 0.630 |

**Decision: NO_PROMOTION.** The GBM has the lowest test Brier but **AUC 0.41** (worse than random), **ECE 0.15**, and only 22 test rows. The test positive rate is 0.636 vs 0.443 in training, so the Brier gain is a class-shift artifact, not ranking skill. The model remains research-only.

### Feature set

Point-in-time features at `signal_asof`:

- time of day; ATR; ATR %; 20-bar realized vol;
- OR(15) and IB(60) size / ATR;
- distance from VWAP, POC, VAH, VAL;
- distance from RTH high/low, prior RTH high/low/close, overnight high/low;
- 5/20-bar momentum; trend strength; range compression; volatility percentile;
- ES/NQ 1-hour relative return;
- prior-close VIX level and 5-day change;
- setup risk / ATR and target distance / ATR;
- strategy and side dummies.

Missing data is explicit; no future bar is admitted. `profile_method` is recorded as `BAR_APPROXIMATION`.

## 2. Significant price-level engine

`src/nocturne/price_levels/engine.py` builds candidate zones from:

prior RTH high/low/close; prior-week high/low; overnight high/low; Asia, London and
New York highs/lows; IB and OR boundaries; POC, VAH, VAL, HVN, LVN; VWAP and
volatility bands.

Nearby levels are clustered at 8 NQ ticks. Each zone keeps its separate source
types and records:

- `confluence_count` — number of independent structural types;
- `touch_count` — bars in the as-of history that touched the zone;
- `reaction_rate` — fraction of touches followed by a 0.5 ATR move within 6 bars;
- `zone_low` / `zone_high`, `asof`, `source`, `level_id`.

Strength is ranked by confluence, then empirical reaction rate, then touch count.
It is not an arbitrary score. Touch statistics use only bars available at the
as-of timestamp.

## 3. Expected range and large-move probabilities

`src/nocturne/research/range_model.py` uses the empirical distribution of forward
high-low ranges, conditioned on the current ATR quartile. For NQ on 2026-11-03
(full session, 78 bars, ATR 33.18):

| Quantile | NQ points |
|---|---:|
| p50 | 260 |
| p80 | 402 |
| p90 | 512 |

| Threshold | Probability |
|---|---:|
| ≥ 200 points | 70.5% |
| ≥ 350 points | 27.0% |
| ≥ 500 points | 11.2% |

Sample: 3,373 forward ranges in the top ATR quartile. These are empirical
probabilities, not a guarantee, and are not conditioned on direction.

## 4. Regime engine

`src/nocturne/regime.py` computes ADX, range efficiency, bar overlap and
volatility percentile, then labels the current state. Future-regime probabilities
come from historical transitions of the same rules.

Current NQ state (2026-11-03):

| Field | Value |
|---|---|
| Label | COMPRESSION |
| ADX | 35.85 |
| Efficiency | 0.16 |
| Overlap | 1.00 |
| Vol percentile | 0.20 |

Future 24-bar probabilities: COMPRESSION 0.33, BALANCED 0.25, TREND_DOWN 0.14,
EXPANSION 0.11, STRESS 0.087, TREND_UP 0.047, TRANSITION 0.037.

## 5. Structured Forecast V1

`src/nocturne/forecast/v1.py` emits a versioned research-only contract. It does
not fabricate probabilities:

- `direction_probability = null`
- every `target.probability_before_stop = null`
- `validation_status = "research_only"`
- `decision = "NO_TRADE"`
- `model_version = "none"`

The forecast still provides the regime, expected range, candidate entry zone,
targets and data provenance. Current NQ artifact:
`data/forecasts/NQ_v1.json`.

API: `GET /v1/forecast/v1?instrument=NQ`.

## 6. What is not done

- No validated target-first model; no promotion.
- No session-specific models (Asia/London/NY levels exist, but models do not).
- No authentic tick/DOM/volume-at-price; order-flow remains data-blocked.
- No CFE VX futures; `^VIX` is a labelled spot proxy.
- No point-in-time economic calendar; macro warnings are explicit.
- No live orders, frontend or TradingView automation.

## 7. Next exact step

Expand the target dataset beyond 60 days (licensed 1-minute or tick history),
rerun the grouped chronological target model with feature ablations, and require
an untouched-holdout Brier improvement **with AUC ≥ 0.55 and ECE ≤ 0.05** before
any shadow promotion. In parallel, build session-specific datasets for Asia,
London and New York rather than pooling all sessions.
