# Read-Only API

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
| GET | `/v1/events/upcoming` | events or `NO_AUTHORIZED_CALENDAR_ADAPTER` |
| GET | `/v1/models/status` | registry metadata |

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
