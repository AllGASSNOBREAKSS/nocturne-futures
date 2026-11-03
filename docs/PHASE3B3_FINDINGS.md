# Phase 3B.3 / 3C Findings — Sessions, Reachability and Macro Risk

**Date:** 2026-11-03  
**Branch:** `feat/phase3b3`  
**Status:** Session infrastructure, session research baselines, level reachability, sample-calendar critical-day rules, multi-session bundle and forecast evaluation are implemented. No model is promoted.

## 1. Session infrastructure

`src/nocturne/sessions.py` adds DST-aware analytical windows:

| Window | New York time | Notes |
|---|---|---|
| ASIA | 19:00–03:00 | analytical, spans prior UTC date |
| LONDON | 03:00–08:00 | analytical |
| PREMARKET | 08:00–09:30 | analytical |
| NEW_YORK | 09:30–16:00 | exchange RTH; early close 13:00 |
| RTH / OVERNIGHT / ETH | exchange calendar | existing `market_clock` |

`SessionSnapshot` records open, high, low, close, volume, VWAP, range, return,
ATR, range/ATR, efficiency, volatility, gap, prior-session extremes, initial
balance, POC/VAH/VAL, profile method and data-quality flags. Every field uses
bars with `available_at <= asof`.

Tests cover DST (13:30 UTC in EDT vs 14:30 UTC in EST), Asia spanning the prior
day, the 2026-11-27 early close, partial/complete snapshots, and future-bar
exclusion.

## 2. Session direction and consolidation research

Dataset: `data/research/session_dataset_NQ.csv`, 60 days of 5-minute bars.

| Item | Value |
|---|---:|
| Rows | **147** |
| Days | **49** |
| Sessions | ASIA 49 / LONDON 49 / NEW_YORK 49 |
| Direction labels | BULL 72 / BEAR 69 / NEUTRAL 6 |
| Range states | EXPANSION 56 / CONSOLIDATION 47 / NORMAL 44 |
| Split rows | 87 / 30 / 30 |

Direction target: next occurrence of the same analytical session; BEAR/BULL
threshold is ±0.5 ATR from the session close. Consolidation target: next session
range ≤ 0.8 × current session range.

### Direction (3-class)

| Model | Log loss | Brier | Accuracy | ECE |
|---|---:|---:|---:|---:|
| Frequency | **0.8650** | **0.5950** | **0.400** | **0.1977** |
| Logistic | 2.5272 | 0.9974 | 0.400 | 0.5198 |
| GBM | 1.3781 | 0.9224 | 0.267 | 0.4789 |

**NO_PROMOTION.** The frequency baseline wins. NEUTRAL is only 6/147 and is
absent from the 30-row test split; the model cannot learn a neutral state from
this sample. The logistic calibration is worse than the baseline.

### Consolidation (binary)

| Model | Brier | Log loss | Accuracy | ECE | AUC |
|---|---:|---:|---:|---:|---:|
| Frequency | 0.2333 | 0.6596 | 0.633 | **0.0333** | 0.500 |
| Logistic | **0.1496** | **0.4677** | **0.800** | 0.1925 | **0.8995** |
| GBM | 0.1947 | 0.5779 | 0.633 | 0.1690 | 0.7656 |

**NO_PROMOTION.** The logistic model has a lower Brier and high AUC, but ECE is
0.1925 and the test set is only 30 rows. This is a promising research signal,
not a calibrated forecast. It must be retested on a larger untouched period.

## 3. Conditional level reachability

`src/nocturne/price_levels/reachability.py` estimates:

> Given the current ATR-normalized distance to a level, how often did comparable
> historical setups touch that level within the horizon?

It uses forward MFE/MAE from bars available at the as-of timestamp. It is **not**
a target-before-stop probability. If fewer than 20 comparable samples exist, the
tolerance widens and the method is labelled `EMPIRICAL_FORWARD_MFE_WIDENED`; if
there is no comparable history, probability is null.

The Forecast V1 targets now carry `touch_probability`, `touch_method` and
`touch_sample_n`; `probability_before_stop` remains null.

## 4. Macro calendar and critical-day rules

`src/nocturne/macro/calendar.py` provides:

- `EconomicEvent` with scheduled/available timestamps, consensus, actual, prior,
  revised prior, source, importance, instruments and quality.
- `CalendarStore` JSONL storage with idempotent append, `upcoming`, `recent` and
  `event_risk`.
- `detect_critical_day` states: `NORMAL`, `SCHEDULED_HIGH_IMPACT`,
  `PRE_EVENT_LOCK`, `LIQUIDITY_STRESS`, `DATA_UNAVAILABLE`.

Critical-day output has `directional_bias = None` by construction. An event-risk
alert never implies bullish or bearish direction.

`data/macro/sample_events.json` is an explicitly labelled **public-schedule
sample** with null consensus and actual values. It is not a live calendar. An
authorized point-in-time provider adapter is still required.

## 5. Multi-session Forecast Bundle

`src/nocturne/forecast/bundle.py` emits ASIA, LONDON, NEW_YORK and NEXT_DAY
outlooks. Every outlook is research-only:

- `decision = NO_TRADE`
- `validation_status = research_only`
- `direction_probability = null`
- `probability_before_stop = null`

Current NQ ASIA outlook (as-of 2026-11-03 20:28 UTC):

| Field | Value |
|---|---:|
| Expected range p50 | 281.75 |
| p80 | 445.25 |
| p90 | 561.50 |
| P(≥200) | 0.7898 |
| P(≥350) | 0.3515 |
| P(≥500) | 0.1482 |
| Critical day | NORMAL |

These are total-range probabilities, not directional target probabilities.

API: `GET /v1/forecast/bundle?instrument=NQ` reads
`data/forecasts/NQ_bundle.json`.

## 6. Forecast evaluation

`src/nocturne/forecast/evaluation.py` evaluates matured Forecast V1 and bundle
outlooks:

- realized high/low/range;
- p50/p80/p90 range coverage;
- target touch versus recorded touch probability;
- direction outcome only when a validated direction probability exists;
- explicit `NOT_MATURED` status.

`scripts/evaluate_forecasts.py` evaluates journaled forecasts and bundles. The
current V1 artifact is `NOT_MATURED` because it is at the end of the cached data.

## 7. Blockers and non-claims

- No authorized economic-calendar or news provider is wired; the committed
  calendar is a sample schedule with null consensus.
- No tick, DOM, MBO or true volume-at-price data.
- No CFE VX futures; `^VIX` remains a labelled proxy.
- Session models are research baselines, not validated forecasts.
- No live orders, frontend or TradingView automation.
- No C++ changes were required in this phase.

## 8. Next exact step

Expand history beyond 60 days, add authorized point-in-time calendar events, and
rerun session direction/consolidation models with purged walk-forward splits and
session-specific samples. Promotion gates remain: holdout Brier improvement,
AUC ≥ 0.55, ECE ≤ 0.05, and adequate sample size.
