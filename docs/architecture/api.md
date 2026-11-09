# Read-Only API

Phase 3T adds separate execution/issuance/quarantine components to the protected
operational view; aggregate health and nonzero integrity exits remain. Alert
acknowledgement is a local operator CLI capability only, not an HTTP mutation route.
All Phase 3S authentication, authorization, input/rate/request bounds and TLS controls
are unchanged. A completed request/job/cycle is not a model/data readiness approval.

## Phase 3S security contract (current)

Authentication is now required for protected routes; anonymous startup/data access
is not the supported interface. Configure separate reader/admin **token-file paths**
and operator TLS certificate/key files, then use the loopback TLS launcher. Exact
instructions, request/rate/audit limits and role boundaries:
`../PHASE3S_SECURITY_DEPLOYMENT.md`.

`/health` and `/health/live` now return only minimal liveness. Detailed API storage
health is `/health/ready` and requires administrator authentication. It is not model
or trading readiness. Research/model/operational/data-verification views require
administrator access; ordinary forecast views require reader or administrator.
No credential enables mutation, job execution, acquisition, promotion or orders.
Docs/OpenAPI HTTP access is disabled; route response contracts otherwise remain.

The endpoint catalog and examples below are historical payload descriptions, not
anonymous access instructions or current predictive/trading approval. The old
plaintext run example requires configured credentials and is loopback-only; prefer
the current TLS deployment procedure. No public deployment has been authorized.

Run:

```bash
python -m nocturne serve --host 127.0.0.1 --port 8000
```

No endpoint places an order, modifies a position, or talks to a broker.

## Endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | status, read-only flag, journal counts, latest model |
| GET | `/v1/predictions/latest?instrument=NQ` | latest journaled prediction |
| GET | `/v1/predictions/{prediction_id}` | one prediction |
| GET | `/v1/market-state?instrument=NQ` | regime, critical-day state, data quality |
| GET | `/v1/auction/profile?instrument=NQ&session=RTH` | profile artifact or explicit reason |
| GET | `/v1/levels?instrument=NQ` | level artifact or explicit reason |
| GET | `/v1/intermarket/state` | ES/NQ/VIX/ZN/ZB context |
| GET | `/v1/premarket/state` | overnight gap/range, prior RTH, leadership |
| GET | `/v1/forecast/v1?instrument=NQ` | research-only Forecast V1 |
| GET | `/v1/forecast/bundle?instrument=NQ` | ASIA/LONDON/NY/NEXT_DAY research bundle |
| GET | `/v1/events/upcoming` | events or `NO_AUTHORIZED_CALENDAR_ADAPTER` |
| GET | `/v1/models/status` | registry metadata |
| GET | `/v1/shadow/ndx-range` | latest shadow status, forecast and evaluation |
| GET | `/v1/shadow/history?limit=50` | newest-first immutable shadow forecasts |
| GET | `/v1/shadow/evaluation` | matured-only coverage and pinball loss |
| GET | `/v1/data/health` | provider status, source coverage, last shadow run, warnings |

Shadow endpoints always report `trading_decision: NO_TRADE`. The model status
`RESEARCH_VALIDATED_PENDING_SHADOW` is a research designation and does not enable
trading. `/v1/shadow/evaluation` returns `INSUFFICIENT_FORWARD_DATA` until at
least one forecast matures.

## Illustrative prediction

Generated from the journal on 2026-11-03. This is `RESEARCH_ONLY`; it is not a
trade recommendation.

```json
{
  "prediction_id": "NQ-20261102-165856",
  "instrument_id": "NQ",
  "asof_utc": "2026-11-02T21:00:00Z",
  "horizon_seconds": 432000,
  "bias": "BEARISH",
  "decision": "WAIT",
  "market_regime": "TREND_DOWN",
  "critical_day_state": "NORMAL",
  "strategy_id": "research_daily_barrier",
  "model_version": "NQ-frequency-20261103T165232",
  "entry": {"lower_price_ticks": 112162, "upper_price_ticks": 113522},
  "stop": {"lower_price_ticks": 109441, "upper_price_ticks": 110801},
  "targets": [
    {"target_id": "TP1", "zone": {"lower_price_ticks": 116243, "upper_price_ticks": 117603}, "event_definition": "close >= target before close <= stop within 5 sessions", "p_target_before_stop_given_fill": null}
  ],
  "data_quality": {"stale": false, "missing": false, "out_of_order": false, "coverage": 1.0},
  "reason_codes": ["RESEARCH_ONLY", "MODEL_NOT_PROMOTED", "CALIBRATED_P_TP_FIRST=0.3938"],
  "research_status": "RESEARCH_ONLY"
}
```

## Missing-data behavior

- No prediction for an instrument: HTTP 404.
- No level artifact: `{"levels": [], "reason": "NO_LEVEL_ARTIFACT"}`.
- No profile: `{"profile": null, "reason": "DATA_BLOCKED_OR_NOT_BUILT"}`.
- No calendar adapter: `{"events": [], "reason": "NO_AUTHORIZED_CALENDAR_ADAPTER"}`.

The API never fills a missing value with a synthetic one.

## Forecast V1

`GET /v1/forecast/v1?instrument=NQ` returns the artifact in
`data/forecasts/NQ_v1.json`. It is research-only:

- `validation_status = "research_only"`
- `decision = "NO_TRADE"`
- `direction_probability = null`
- every `target.probability_before_stop = null`
- `model_version = "none"`

The contract still provides the market regime, empirical expected range,
candidate entry zone, significant levels and data provenance. A missing
validated model does not produce a fabricated confidence number.

## Forecast bundle

`GET /v1/forecast/bundle?instrument=NQ` returns
`data/forecasts/NQ_bundle.json`. It contains `ASIA`, `LONDON`, `NEW_YORK` and
`NEXT_DAY` outlooks. Every outlook has:

- `decision = "NO_TRADE"`
- `validation_status = "research_only"`
- `direction_probability = null`
- `probability_before_stop = null`

Targets may carry an empirical `touch_probability` with `touch_method` and
`touch_sample_n`. This is a conditional forward-MFE touch estimate, **not** a
target-before-stop probability.

`critical_day` is one of `NORMAL`, `SCHEDULED_HIGH_IMPACT`, `PRE_EVENT_LOCK`,
`LIQUIDITY_STRESS` or `DATA_UNAVAILABLE`. Critical-day output never contains a
directional bias. The committed calendar is a public-schedule sample, not live
consensus.

## Evaluation

`python -m nocturne evaluate-forecast --instrument NQ` evaluates the stored V1
artifact when future bars exist. `python scripts/evaluate_forecasts.py` evaluates
the V1 and bundle journals. A forecast without enough future bars returns
`status = "NOT_MATURED"`; it is never scored against incomplete data.
