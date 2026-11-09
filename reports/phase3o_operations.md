# Component health

As of 2026-11-09T02:17:26.863294+00:00

Core: DEGRADED

- service_execution: **COMPLETED_WITH_QUARANTINE** — Fresh cycle result only; source quarantine is not a process crash. Aggregate alerts and nonzero exits remain.
- forecast_issuance: **ISSUED** — Current generation result; no claim about future uptime or deadline success
- shadow_cycle: **BLOCKED** — AUDIT_BLOCKED
- forecast_integrity: **BLOCKED** — see forecast audit issues; reconciliation is evidence-bound, not a health override
- provider_refresh: **HEALTHY** — latest timestamped cycle refresh results; not an uptime guarantee
- outcome_evaluation: **PARTIAL_QUARANTINE** — pending horizons are expected work, not fabricated outcomes; evaluation requires availability and audit gates
- DATA_VALIDATION / aef7680ef54546f538a0847e: **HEALTHY** — SUCCEEDED
- FEATURE_BUILD / 6c5abbdc35131e1c28fe4596: **HEALTHY** — SUCCEEDED
- HISTORICAL_BACKTEST / 0d1c9bdb4d4add7cd173fd7d: **HEALTHY** — SUCCEEDED
- WALK_FORWARD_VALIDATION / 777d85d11d0c796dbb875b1f: **HEALTHY** — SUCCEEDED
- MODEL_TRAINING / e7f72a81f7f1c095f207357a: **HEALTHY** — SUCCEEDED
- MODEL_EVALUATION / 7c6dbabbfd52cf319ff955e9: **HEALTHY** — SUCCEEDED
- FEATURE_BUILD / 03080fe1019c73164d273ba8: **HEALTHY** — SUCCEEDED
- HISTORICAL_BACKTEST / bbe71518fdcebdb4c077a2a8: **HEALTHY** — SUCCEEDED
- WALK_FORWARD_VALIDATION / 46ea566985c00e43d4dfdd97: **HEALTHY** — SUCCEEDED
- MODEL_TRAINING / 804c1127316b5d4e5a01d21b: **HEALTHY** — SUCCEEDED
- MODEL_EVALUATION / 60d102ffabcb24efa44c9104: **HEALTHY** — SUCCEEDED
- HISTORICAL_BACKTEST / 178923b71b51206a027758eb: **BLOCKED** — AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- RESEARCH_REPORT / 2b38f82cd432bbafd092efd2: **HEALTHY** — SUCCEEDED
- DATA_REFRESH / 7cd1831eef7b20d18ffa1825: **BLOCKED** — COMPONENT_COMPLETED_WITH_QUARANTINE
- SHADOW_FORECAST / 169fb2adcc2be9f8adef9e04: **BLOCKED** — COMPONENT_COMPLETED_WITH_QUARANTINE
- FORECAST_MATURITY_CHECK / acf64a1af0033e46aeb84767: **BLOCKED** — COMPONENT_COMPLETED_WITH_QUARANTINE
- FORWARD_EVALUATION / 99ada9b5f1eacdae0dcb41f8: **HEALTHY** — SUCCEEDED
- MODEL_DRIFT_MONITOR / 077692ad757ec5c2e67328d7: **HEALTHY** — SUCCEEDED
- RESEARCH_REPORT / 85717b5f3f369cf088cac99b: **HEALTHY** — SUCCEEDED
- HISTORICAL_BACKTEST / a9715adfe952f45c39945767: **BLOCKED** — AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- HISTORICAL_BACKTEST / 9cb95320b29b8d1e41e80d9a: **BLOCKED** — AUTHENTIC_CONTRACT_HISTORY_REQUIRED

Futures availability is separate from core software health. NO_PROMOTION / NO_TRADE.
No new challenger protocol enabled by default. Awake, logged-in host required.
