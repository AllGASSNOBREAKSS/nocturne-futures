# Implementation Status

## Phase 3F update (2026-11-03)

Direction diagnostics: material-move detection works (AUC ≈ 0.70), directional
discrimination does not (bull-vs-bear AUC ≈ 0.52). Hierarchical and vector-scaled
variants were worse; class weighting was rejected as unable to create signal.
Range quantiles improved with rolling residual calibration at every tested
quantile. Competing-outcome target survival is implemented; 200–500 point targets
are rarely reached before the original stop. All 21 promotion assessments are
`NO_PROMOTION`.

Research-only: direction, consolidation, range and target survival. Production
probabilities remain null; every forecast remains `NO_TRADE`. See
`PHASE3F_FINDINGS.md` for measured results and limitations.

Blocked/unfinished: licensed contract-level intraday history, ticks/depth/MBO,
PIT macro consensus/news, independent future holdout, strategy-level meta-labeling
(insufficient trades), and monitoring/rollback.

## Phase 3E update (2026-11-03)

Operational: authenticated raw-contract Databento and ALFRED adapter interfaces,
contract/source validation, LightGBM ablations, range quantiles, nested-target
audits, immutable development replay and fail-closed promotion evidence.
Databento/ALFRED keys are absent, so no real licensed download occurred; adapters
were tested only with synthetic HTTP fixtures.

Research-only: direction remains weak (BEAR recall near zero); consolidation and
range quantiles improve probability/pinball loss on retrospective development
folds. All promotion assessments are `NO_PROMOTION`; production probabilities
remain null and `NO_TRADE` remains. See `PHASE3E_FINDINGS.md` for exact metrics.

Blocked/unfinished: licensed five-minute/tick/depth/MBO history, actual VX
futures, PIT release schedules/consensus/news, independent future holdout,
validated fusion and monitoring/rollback. Older milestone descriptions below must
not be read as completing those gates.

## Phase 3D update (2026-11-03)

Operational: public two-year hourly NQ/ES ingestion, official FRED latest-vintage
context, authorized CSV import with checksums/revision rejection, grouped purged
expanding/rolling validation, calibration and block intervals. See
`PHASE3D_FINDINGS.md` for exact evidence and limitations.

Research-only: 86 complete-session rows and separate 10,344 NQ / 10,336 ES
two-hour observations. Better hourly Brier does not satisfy promotion; direction
recall is poor. No production model probabilities enabled. `NO_TRADE` remains.

Follow-up implemented fixed 200/350/500-point barrier/cost diagnostics and grouped
journal coverage/touch-loss monitoring. Updated native-enabled suite: 176 passed.
No matured journal outcomes exist; monitor scores remain null.

Blocked/unfinished: licensed contract/roll-resolved intraday expansion, PIT macro
consensus/news, independent final evaluation, advanced target/cost research,
LightGBM, validated fusion and monitoring/rollback. Older milestone descriptions
below must not be read as completing those gates.

**Last updated:** 2026-11-03  
**Branch:** `feat/backend-v2`

Status vocabulary: `DONE`, `PARTIAL`, `DATA_BLOCKED`, `TOOLCHAIN_BLOCKED`, `PLANNED`.
A milestone is `DONE` only when code, tests, and a runnable command exist.

## Phase 0 — Repo audit

| Item | Status | Evidence |
|---|---|---|
| Inspect existing code and tests | DONE | `docs/CURRENT_SYSTEM_AUDIT.md` |
| Preserve working call/report pipeline | DONE | 12 baseline tests pass |
| Record conflicts with v2 package | DONE | Audit §6 |
| Create feature branch | DONE | `feat/backend-v2` |

## Phase 1 — Canonical data contracts and replay

| Item | Status | Evidence |
|---|---|---|
| Pydantic event/level/prediction contracts | DONE | `src/nocturne/contracts.py`, 6 contract tests |
| Instrument registry (NQ/MNQ/ES/MES/VX/ZN/ZB) | DONE | `src/nocturne/instruments.py`, 6 registry tests |
| Session/roll calendar with DST | DONE | `src/nocturne/market_clock.py`, 7 clock tests |
| Immutable JSONL event store | DONE | `src/nocturne/storage/event_store.py`, 6 store tests |
| As-of replay and watermark | DONE | `EventStore.replay`, `watermark` |
| Yahoo bar adapter with provenance | DONE | `src/nocturne/adapters/yahoo.py`, 2 adapter tests |
| Replay correctness tests | DONE | Out-of-order write, as-of cutoff, dedupe |

## Phase 2 — Auction / volume profile

| Item | Status | Evidence |
|---|---|---|
| True trade-derived volume profile | DONE | `auction/volume_profile.py`; live data DATA_BLOCKED, synthetic fixtures pass |
| POC/VAH/VAL with deterministic tie-break | DONE | 70% expansion, nearest-VWAP tie-break, 6 tests |
| HVN/LVN with smoothing/prominence | DONE | Smoothed local extrema, configurable |
| TPO profile, separate from volume | DONE | `auction/tpo.py`; TPO-vs-volume test |
| IB / opening range | DONE | `auction/session.py`, 4 tests |
| AMT balance/acceptance/value migration | DONE | `auction/state.py`, 4 tests |
| Bar-approximation profile, explicitly labeled | DONE | `BAR_APPROXIMATION`; never called exchange-accurate |

## Phase 3 — Strategy research and backtester

| Item | Status | Evidence |
|---|---|---|
| ORB/IB strategy spec | DONE | `strategies/opening_range.py`, 3 tests |
| VWAP pullback strategy spec | DONE | `strategies/vwap_pullback.py`, 2 tests |
| VAH/VAL rejection strategy spec | DONE | `strategies/value_rejection.py`, 1 test |
| Event-driven bar backtester with costs | DONE | `backtest/engine.py`, 5 tests; ORB ledger committed |
| Conservative intrabar ambiguity | DONE | Stop-first on same-bar stop+target |
| Walk-forward evaluation | PARTIAL | Chronological development/holdout done; no parameter search |
| Phase 3A held-out NQ/ES study | DONE | `reports/phase3a_backtests.md`, 12 strategy/split cells |
| Cost stress 1–4 ticks | DONE | Holdout net dollars by strategy/instrument |
| ORB timeout diagnosis | DONE | Median risk 208.9, MFE 0.26R, 41/41 timeouts <1R |
| Regression tests: gaps, ambiguity, session, costs, rolls | DONE | `test_backtest_regression.py`, `test_rolls.py` |

## Phase 4 — ML prediction v1

| Item | Status | Evidence |
|---|---|---|
| Triple-barrier labels | DONE | `research/labels.py`, 4 tests; ambiguity excluded |
| Historical-frequency baseline | DONE | `ml/baseline.py`; NQ walk-forward Brier 0.2474 |
| Logistic baseline | DONE | NQ Brier 0.2493 (worse than frequency) |
| Gradient-boosted challenger (sklearn) | DONE | NQ Brier 0.2483–0.2488 (worse than frequency) |
| Calibration (Brier, reliability, ECE) | DONE | `ml/calibration.py`, Platt + metrics |
| Model registry | DONE | `models/registry/NQ-frequency-*`, metadata + joblib |
| Read-only forecast API + journal | DONE | FastAPI, append-only JSONL, 7 API tests |
| Target-level training dataset | DONE | `research/target_dataset.py`; 4 committed CSVs |
| ML audit across 4 label geometries | DONE | `reports/ml_audit_NQ.md`, `scripts/ml_audit.py` |
| Model evaluation report | DONE | Direction, Brier/ECE, regime stability, net expectancy |

## Phase 5 — Intermarket / premarket

| Item | Status | Evidence |
|---|---|---|
| ES/NQ relative state | DONE | `intermarket/context.py`; beta 1.82, corr 0.95 on 2026-11-02 |
| VX curve (CFE) | DATA_BLOCKED | `^VIX` spot proxy only; flag `VX_FUTURES_UNAVAILABLE` |
| ZN/ZB adapters | DONE | Yahoo front-month proxies; flag `ZN_ZB_YAHOO_PROXY` |
| PremarketState | DONE | `premarket.py`; real 2026-11-03 state built |
| Event/critical-day gates | PARTIAL | Risk gates implemented; live calendar adapter not wired |

## Phase 6 — Tape / DOM

| Item | Status | Evidence |
|---|---|---|
| Typed trade/quote/book interfaces | DONE | `orderflow/tape.py`, `orderflow/depth.py` |
| Aggressor classification + CVD | DONE | Quote/tick rule with confidence; 6 tests |
| Footprint / DOM imbalance | DONE | Footprint by side; top-k book imbalance |
| C++ kernels | DONE | MSVC 19.51 build; `nocturne_native` parity passes; CI native job |

## Phase 7 — Knowledge / discretion

| Item | Status | Evidence |
|---|---|---|
| Analyst thesis record | DONE | `knowledge/thesis.py`, 3 tests |
| Vault indexing | DATA_BLOCKED | Private vault; not published |

## Phase 8 — Hardening

| Item | Status | Evidence |
|---|---|---|
| CI Python + TypeScript | DONE | `.github/workflows/ci.yml`; pytest + tsc |
| CI native build/parity | DONE | Ubuntu cmake/ninja/pybind11 job added |
| Drift/coverage/latency monitoring | PARTIAL | Health, coverage, staleness gates; no drift dashboard |
| Promotion/rollback | PARTIAL | Versioned registry + RESEARCH_ONLY gate; manual rollback |

## Phase 3B — Predictive Intelligence V1

| Item | Status | Evidence |
|---|---|---|
| Point-in-time intraday features | DONE | `research/intraday_features.py`; 2 leakage tests |
| Signal-grouped chronological split | DONE | `research/target_training.py`; group-disjoint tests |
| Target-first model experiment | DONE | 123 binary rows / 75 signals; `reports/phase3b_target_model.*` |
| Target-first promotion | **NO_PROMOTION** | GBM Brier 0.2447 but AUC 0.41, ECE 0.15, test n=22 |
| Significant price-level engine | DONE | `price_levels/engine.py`; confluence + touch/reaction stats |
| Expected-range model | DONE | `research/range_model.py`; empirical ATR-bucket quantiles |
| Regime engine | DONE | `regime.py`; current state + empirical transitions |
| Structured Forecast V1 | DONE | `forecast/v1.py`; research-only, null probabilities |
| Forecast API | DONE | `GET /v1/forecast/v1` |
| Multi-session models | PARTIAL | Asia/London/NY levels exist; no separate models |
| Macro / order-flow integration | DATA_BLOCKED | Unchanged from Phase 3A |

Phase 3B evidence:

- Target model: frequency Brier 0.2688, logistic 0.2735, GBM 0.2447 on the
  test split; GBM AUC 0.4107, ECE 0.1535, test positive rate 0.636 vs train
  0.443. The Brier gain is a class-shift artifact, not skill.
- Level engine: prior RTH/week, overnight, Asia/London/NY, IB/OR, POC/VAH/VAL,
  HVN/LVN, VWAP/vol bands; 8-tick clustering; empirical touch/reaction stats.
- Range: NQ full-session p50 260, p80 402, p90 512; P(≥200) 0.705,
  P(≥350) 0.270, P(≥500) 0.112.
- Regime: NQ COMPRESSION, ADX 35.85, efficiency 0.16, vol percentile 0.20;
  future probabilities COMPRESSION 0.33 / BALANCED 0.25 / TREND_DOWN 0.14.
- Forecast V1: `decision=NO_TRADE`, `validation_status=research_only`,
  `direction_probability=null`, `target.probability_before_stop=null`.

## Phase 3B.3 / 3C — sessions, reachability and macro risk

| Item | Status | Evidence |
|---|---|---|
| DST-aware analytical session windows | DONE | `sessions.py`; DST/Asia/early-close tests |
| Point-in-time session snapshots | DONE | open/high/low/VWAP/IB/profile/prior levels |
| Session direction baseline | DONE | 147 rows / 49 days; **NO_PROMOTION** |
| Session consolidation baseline | DONE | logistic Brier 0.1496, AUC 0.8995, ECE 0.1925; **NO_PROMOTION** |
| Conditional level reachability | DONE | `price_levels/reachability.py`; empirical touch probability |
| Economic event schema/store | DONE | `macro/calendar.py`; sample schedule only |
| Critical-day rules | DONE | `NORMAL`/`SCHEDULED_HIGH_IMPACT`/`PRE_EVENT_LOCK`/`LIQUIDITY_STRESS`/`DATA_UNAVAILABLE` |
| Authorized calendar/news adapter | **DATA_BLOCKED** | No provider credentials or licensed history |
| Multi-session outlook bundle | DONE | ASIA/LONDON/NY/NEXT_DAY; research-only `NO_TRADE` |
| Forecast outcome evaluation | DONE | `forecast/evaluation.py`; explicit `NOT_MATURED` |
| Session-specific promoted models | **NO_PROMOTION** | Sample too small; NEUTRAL 6/147 |

Phase 3B.3 evidence:

- Session dataset: 147 rows, 49 days, 49 per session; direction labels BULL 72 /
  BEAR 69 / NEUTRAL 6; range states EXPANSION 56 / CONSOLIDATION 47 / NORMAL 44.
- Direction test: frequency log loss 0.8650; logistic 2.5272; GBM 1.3781.
  NEUTRAL is absent from the 30-row test split.
- Consolidation test: frequency Brier 0.2333; logistic 0.1496 (AUC 0.8995,
  ECE 0.1925); GBM 0.1947. ECE and sample size fail the promotion gate.
- Reachability: empirical forward-MFE touch probability conditioned on ATR
  distance; **not** target-before-stop. Forecast targets record method/sample size.
- Macro: six-event public-schedule sample with null consensus; critical-day output
  has `directional_bias = None`. No authorized live calendar.
- Bundle: ASIA expected range p50 281.75 / p80 445.25 / p90 561.50; P(≥200)
  0.7898, P(≥350) 0.3515, P(≥500) 0.1482; `decision=NO_TRADE`.
- Evaluation: current V1 artifact is `NOT_MATURED`; no outcome is claimed.

## Phase 3A evidence

- **ORB timeouts:** median risk 208.9 NQ points, median MFE 0.26R, 4.5% reach
  1R, 0% reach 2R, 41/41 timeouts below 1R. The 24-bar horizon is too short for
  the 60-minute IB stop.
- **Held-out study:** NQ ORB development −$18,730 vs holdout +$23,670; NQ VWAP
  +$1,911 / +$8,398; NQ value +$2,935 / −$6,170; ES ORB −$5,853 / +$3,665.
  Regime dependence, not a validated edge.
- **Cost stress:** 1–4 tick slippage reported for every strategy/instrument in
  `reports/phase3a_backtests.md`.
- **ML audit:** frequency wins in all four label geometries. The lower Brier in
  tight-stop/long-horizon configs is class imbalance, not skill. At p ≥ 0.50
  the threshold strategy loses after costs; p ≥ 0.55/0.60 is sparse.
- **Target dataset:** `data/research/target_dataset_NQ_vwap.csv` has 84 rows,
  32 TP / 33 SL / 19 timeout; ORB actual targets are 2 TP / 3 SL / 127 timeout.
- **Native parity:** MSVC 19.51 build; parity test passes; 155 tests with the
  module, 154 + 1 skipped without.

## Current truth boundary

No calibrated model or profitable strategy is claimed. The existing 15-year
direction baseline did **not** beat the always-up/frequency rate on ES, NQ, or
GC. The 2026-10-30 and 2026-11-02 calls are recorded misses and must remain in
the archive. Phase 3A found no strategy that survives the development/holdout
and cost-stress gates. Phase 3B's target-first model is **NO_PROMOTION** (AUC
0.41, ECE 0.15, 22-row test); Forecast V1 is research-only `NO_TRADE` with null
probabilities. Phase 3B.3 session models are **NO_PROMOTION**; the macro calendar
is a sample schedule, not live consensus. New modules will report `DATA_BLOCKED`
where the required data does not exist.
