# Phase 3H — read-only shadow forecasting and forward evaluation

Date: 2026-11-04. Branch: `feat/phase3h`. Base `016d5d0` (Phase 3G, CI success).
Decision: **NO_TRADE**; the only active model is the NDX cash-session range
quantile model, status `RESEARCH_VALIDATED_PENDING_SHADOW`.

## 1. Phase 3G verification

`016d5d0` is present with a clean tree. The suite reproduced 200 passed plus one
native skip (201 with the C++ module), and the GitHub Actions run for `016d5d0`
completed successfully. The Phase 3G holdout metrics were re-checked when freezing
the model (below).

## 2. Frozen model artifact

`models/shadow/ndx-range-v1/` contains the exact configuration evaluated in Phase
3G: LightGBM quantile regressors (150 trees, 15 leaves, 0.05 learning rate, min
child 50, seed 7) at 0.5/0.8/0.9, trained through 2021 with a 2022–2023 residual
calibration block.

`scripts/phase3h_freeze_model.py` retrains deterministically and **refuses to save**
unless the holdout reproduces the stored metrics within 1e-6. It reproduced:

| Quantile | Coverage | Pinball loss |
|---|---:|---:|
| P50 | 0.5337 | 0.0021959 |
| P80 | 0.8160 | 0.0019377 |
| P90 | 0.9199 | 0.0014095 |

Metadata records the dataset hash, cutoffs, adjustments, scope and the explicit
`NO_TRADE` decision. A test asserts this reproduction against
`reports/phase3g_daily_range.json`.

## 3. Shadow service

`src/nocturne/shadow/` implements:

- `features.py` — the frozen 11-feature schema with point-in-time filtering.
- `model.py` — artifact loading and monotone quantile prediction.
- `store.py` — append-only forecasts, outcomes and data-quality events.
- `service.py` — eligibility, generation and maturation.

Eligibility is fail-closed. The service forecasts the **current** session before
its 13:30 UTC open, using the previous session's daily bar (which the adapter
marks available at the next UTC midnight). It refuses when:

| Condition | Reason code |
|---|---|
| Index or VIX data absent | `NO_INDEX_DATA`, `NO_VIX_DATA` |
| Latest bar not yet available | `NO_AVAILABLE_INDEX_DATA` |
| Data date is not a trading day | `DATA_DATE_NOT_TRADING_DAY` |
| A more recent session is missing | `STALE_DATA_DATE` |
| Data date is ahead of the target | `DATA_AHEAD_OF_TARGET` |
| Target session already open | `TOO_LATE_FOR_TARGET` |
| VIX older than four days | `STALE_VIX` |

A refusal writes a quality event and **no forecast**. Forecasts are immutable and
idempotent: a retry with identical inputs returns the original record and does not
create a duplicate. Evaluation only runs when the target bar exists and is
available; outcomes are keyed by forecast id and conflicting rewrites are rejected.

## 4. First forward forecast

Generated 2026-11-04T02:53Z, before the target session opened:

| Field | Value |
|---|---|
| forecast_id | `20d48fc41c2cc0f5c0ae4f2d` |
| Model | `ndx-range-v1` 1.0.0 |
| Data date | 2026-11-03 |
| Target date | 2026-11-04 |
| Reference close | 28,180.26 |
| P50 / P80 / P90 | 1.6977% / 2.6183% / 2.8568% |
| Implied points | ≈478 / 738 / 805 |
| Validation status | `RESEARCH_VALIDATED_PENDING_SHADOW` |
| Trading decision | `NO_TRADE` |

This is one prediction. It has **not matured**, so no forward accuracy, coverage
or calibration is reported. The store records `matured=0, pending=1`.

## 5. Monitoring and reporting

`scripts/phase3h_shadow_report.py` writes `reports/phase3h_shadow_report.json`
with forward count, matured count, pending, quality failures and the evaluation
summary. `evaluation_summary` reports coverage, mean pinball loss, median interval
width and coverage by month **only for matured outcomes**, and returns
`INSUFFICIENT_FORWARD_DATA` when none exist.

The status file `reports/phase3h_shadow_status.json` is rewritten each cycle with
the model version, sources, generation result and evaluation.

## 6. Scheduler

`scripts/phase3h_shadow.py` supports:

```powershell
python scripts/phase3h_shadow.py --status
python scripts/phase3h_shadow.py --once
python scripts/phase3h_shadow.py --once --refresh
python scripts/phase3h_shadow.py --evaluate-only
python scripts/phase3h_shadow.py --loop --interval-minutes 60 --refresh
```

`--refresh` fetches into `data/shadow/market/` (gitignored) so the frozen research
history in `data/history/yahoo_daily/` is never overwritten. If refresh fails, the
service falls back to the existing operational copy, then to the frozen research
copy, and records the failure. A cycle exception is logged and the loop continues;
restart safety comes from the append-only store and deterministic forecast ids.

## 7. API

Read-only endpoints, added without changing existing contracts:

| Endpoint | Content |
|---|---|
| `GET /v1/shadow/ndx-range` | Latest status, forecast, evaluation |
| `GET /v1/shadow/history?limit=` | Newest-first immutable forecasts |
| `GET /v1/shadow/evaluation` | Matured-only metrics |
| `GET /v1/data/health` | Provider status, source coverage, last run, warnings |

All responses keep `trading_decision=NO_TRADE` and the model's research status
separate from trading eligibility.

## 8. Futures data (3H.3)

`DATABENTO_API_KEY` is absent, so no licensed download occurred and none is
claimed. `docs/FUTURES_DATA_REQUIREMENTS.md` states the exact dataset, schemas,
symbol type, licensing and validation steps, plus the command to ingest a bounded
sample. The adapter remains fixture-tested only.

Without that entitlement, authentic trades, bid/ask, volume-at-price, depth,
market-by-order and VX futures remain `DATA_BLOCKED`. The 60-day five-minute cache
and the free daily index history cannot substitute for them.

## 9. Directional features (3H.4) and targets (3H.5)

No new directional feature family was added. The order-flow and auction families
that Phase 3G identified as the plausible source of directional information all
require the licensed data above; adding proxies built from OHLCV would repeat the
feature families already shown to have bull-versus-bear AUC ≈ 0.52. Target
research likewise remains bounded by the existing 24-bar, 90-signal development
sample.

This is a deliberate stop, not an omission: the next honest step is data, not more
model families.

## 10. Status and next steps

| Item | Status |
|---|---|
| Shadow service | Implemented and running |
| Forward forecasts | 1 |
| Matured forward outcomes | 0 |
| Forward accuracy claim | None |
| Direction models | `NO_PROMOTION` |
| Target-before-stop | `NO_PROMOTION` |
| Licensed futures data | `DATA_BLOCKED` |
| Trading | Disabled (`NO_TRADE`) |

Tests: 208 passed with the native C++ module enabled. CI status is recorded after
pushing.

Next: let the 2026-11-04 forecast mature, run `--evaluate-only`, and accumulate at
least 30 matured predictions before reporting forward coverage. In parallel,
obtain Databento entitlement and ingest a bounded raw-contract sample.
