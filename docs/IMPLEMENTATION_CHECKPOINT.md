# Implementation Checkpoint

## Current resume point — Phase 3I, 2026-11-04 UTC

Branch `feat/phase3i`, base `e963981`. Read `PHASE3I_FINDINGS.md` first.
Local verification: **241 passed including native C++ parity**. Base CI was
verified green. Current commit and remote CI: inspect `git log -1` and the
`feat/phase3i` Actions run; do not substitute base CI for new changes.

Forward state remains **1 issued / 0 matured / 1 pending / 0 missed**. Original
timestamp is `2026-11-04T02:53:30.237804+00:00` (supersedes the older 02:50 text
below). Journal bytes match `e963981`; never change the first forecast.

Important defect: original runtime omitted frozen residual adjustments. Fixed
runtime uses `inference_revision=residual-adjusted-v1`; original remains
`legacy-unadjusted` and must be scored separately, exactly as issued. No
retraining; original model/metadata unchanged. Runtime reproduces stored metrics
on the already-used 712-row holdout. This does not create independent evidence.

Windows task `Nocturne-NDX-ReadOnly-Shadow` was registered: 30-minute runs plus
logon, current logged-in user only. Host must be awake. Inspect actual task
result; registration alone is not demonstrated ongoing operation. Disable with
`Disable-ScheduledTask -TaskName Nocturne-NDX-ReadOnly-Shadow` when needed.

Observed scheduled cycle: 2026-11-04 04:47 UTC, exit code 0, fresh receipts,
`ALREADY_ISSUED`, no duplicate. This is one observed cycle, not an uptime history.

```powershell
Get-ScheduledTask -TaskName Nocturne-NDX-ReadOnly-Shadow | Get-ScheduledTaskInfo
python scripts/phase3h_shadow.py --evaluate-only --refresh
python scripts/phase3i_forward_report.py
python scripts/phase3i_readiness.py
$env:PYTHONPATH='D:\nocturne-futures\native\build'; python -m pytest -o addopts=''
```

Real refresh ended November 3. November 4 outcome is not available before its
completion/availability bound (November 5 00:00 UTC in this adapter). No forward
performance statistics exist. Operational market cache is separate and ignored;
receipt/checksum/completeness checks forbid fallback to frozen research data.

Next: verify real scheduled exit/refresh, append the first verified matured
outcome, accumulate corrected-inference samples without tuning, and obtain
Databento entitlement. Databento/FRED/BLS keys are absent; authentic futures,
order flow and authorized PIT calendar/news remain blocked. Contract-target and
schedule-proximity modules are tested infrastructure, not validated forecasts.
Only NDX range is shadow-active; all other models remain `NO_PROMOTION`, trading
remains `NO_TRADE`. Phase 3I is an engineering checkpoint, not full acceptance of
future-dependent statistical or logout-independent production requirements.

## Previous resume point — Phase 3H, 2026-11-04

Branch `feat/phase3h`, base `016d5d0` (Phase 3G, CI success).
Read `PHASE3H_FINDINGS.md`, `FUTURES_DATA_REQUIREMENTS.md` and
`PHASE3G_FINDINGS.md` before changing anything. Decision remains **NO_TRADE**.

Implemented: frozen NDX range artifact with holdout reproduction, immutable
append-only shadow store, fail-closed eligibility, maturation-only evaluation,
run-once and loop scheduler, forward monitoring report, and read-only API
endpoints for shadow status/history/evaluation/data health.

**Forward state:** 1 forecast stored (`20d48fc41c2cc0f5c0ae4f2d`, target
2026-11-04, generated 2026-11-04T02:50Z), 0 matured. Do not claim forward
accuracy. After the 2026-11-04 session bar becomes available (2026-11-05 00:00
UTC), run:

```powershell
python scripts/phase3h_shadow.py --evaluate-only --refresh
python scripts/phase3h_shadow_report.py
```

That appends exactly one outcome and updates the report. Never edit
`data/shadow/ndx_range/forecasts.jsonl` or `outcomes.jsonl` by hand.

Reproduce and verify:

```powershell
python scripts/phase3h_freeze_model.py     # must reproduce the holdout within 1e-6
python scripts/phase3h_shadow.py --once
python scripts/phase3h_shadow.py --loop --interval-minutes 60 --refresh
python scripts/phase3h_shadow_report.py
$env:PYTHONPATH='D:\nocturne-futures\native\build'; python -m pytest   # 212 passed
```

Operational market cache `data/shadow/market/` is gitignored so frozen research
history is never overwritten. The forward journal is committed.

Next Phase 3I milestone: accumulate >= 30 matured forward predictions before
reporting coverage; in parallel obtain Databento `GLBX.MDP3` entitlement and
ingest a bounded raw-contract sample per `docs/FUTURES_DATA_REQUIREMENTS.md`.
Direction and target-before-stop models stay `NO_PROMOTION` until licensed
order-flow data exists.

**Date:** 2026-11-04
**Previous branch:** `feat/phase3g`
**Latest backend commit:** see `git log --oneline -1`
**CI:** `04def4b` passed all jobs (python, typescript, native).

## Phase 3A — backtest validation and predictive foundation

Completed on 2026-11-03:

- Reproduced the suite: **154 passed + 1 native skip**; **155 passed** with the
  C++ module on PYTHONPATH.
- Built the C++20 `nocturne_native` kernel with MSVC 19.51 and pybind11 3.1;
  the parity test passes. CI now has an Ubuntu native build/parity job.
- Fixed backtest accounting: commission per partial exit, `gross_dollars`,
  `costs`, `risk_points`, `mfe_r`, `mae_r`, `stop_price`, `target_prices`.
- Added conservative rules: one target per bar, gap-beyond-target skip, RTH-only
  session bars, config validation, target-side validation.
- Added regression tests for gaps, stop/target ambiguity, session boundaries,
  costs, NQ vs ES sizing, partial exits, timeouts and rolls.
- Cached 60-day 5m NQ/ES bars with SHA-256; the study is reproducible.
- Ran the held-out, cost-stressed study across NQ/ES × ORB/VWAP/value.
- Diagnosed the ORB timeouts (40 in the original ledger, 41 after the RTH-only
  fix): median risk 208.9 points, median MFE 0.26R, 4.5% reach 1R, 0% reach 2R,
  41/41 timeouts below 1R.
- Audited four label geometries: frequency wins every Brier comparison; the
  lower Brier in tight-stop/long-horizon configs is class imbalance.
- Added the target-level dataset interface and four committed datasets.
- Added `reports/ml_audit_NQ.md`, `reports/phase3a_backtests.md`,
  `docs/PHASE3A_FINDINGS.md`.

Verification commands:

```bash
python -m pytest -q
python -m nocturne study
python -m nocturne dataset --instrument NQ --strategy vwap
python scripts/ml_audit.py
PYTHONPATH=native/build python -m pytest tests/test_native_parity.py -q
```

Blocked: true tick/DOM/volume-at-price, CFE VX futures, point-in-time calendar.

Next exact step: train a target-first model on
`data/research/target_dataset_NQ_vwap.csv` with a chronological split; require a
holdout Brier improvement over frequency before adding features.

## Phase 3B — predictive intelligence V1

Completed on 2026-11-03:

- Added point-in-time intraday features: time of day, ATR, realized vol, OR/IB
  size, distance from VWAP/POC/VAH/VAL/session/prior/overnight levels, momentum,
  trend strength, range compression, volatility percentile, ES/NQ relative,
  VIX, risk/target ATR.
- Added signal-grouped chronological splits so multiple targets from one signal
  never cross train/test.
- Combined VWAP + revised-ORB + value datasets: 123 binary rows from 75 signals,
  base rate 0.520. Test: frequency Brier 0.2688, logistic 0.2735, GBM 0.2447;
  GBM AUC 0.4107, ECE 0.1535. **NO_PROMOTION** due to class shift and no ranking
  skill.
- Added `price_levels/engine.py`: prior RTH/week, overnight, Asia/London/NY,
  IB/OR, POC/VAH/VAL, HVN/LVN, VWAP/vol bands, 8-tick clustering, empirical
  touch/reaction stats.
- Added `research/range_model.py`: empirical forward-range quantiles by ATR
  bucket; NQ p50 260, p80 402, p90 512; P(≥200) 0.705, P(≥350) 0.270,
  P(≥500) 0.112.
- Added `regime.py`: ADX/efficiency/overlap/vol-percentile state and empirical
  transition probabilities. Current NQ state: COMPRESSION.
- Added `forecast/v1.py` and `GET /v1/forecast/v1`; research-only contract with
  null probabilities and `decision=NO_TRADE`.
- Added `docs/PHASE3B_FINDINGS.md`, `reports/phase3b_target_model.md/json`.

Verification commands:

```bash
python -m pytest -q                 # 154 passed, 1 skipped (155 with native)
python scripts/train_target_model.py
python -m nocturne forecast-v1 --instrument NQ
python -m nocturne levels --instrument NQ
python -m nocturne range --instrument NQ
python -m nocturne regime --instrument NQ
```

Blocked: authentic tick/DOM/volume-at-price, CFE VX futures, point-in-time
calendar. No model or forecast is promoted.

Next exact step: expand the target dataset beyond 60 days, rerun the grouped
target model with feature ablations, and require holdout Brier improvement with
AUC ≥ 0.55 and ECE ≤ 0.05 before shadow promotion. Build session-specific
datasets rather than pooling all sessions.

## Phase 3B.3 / 3C — sessions, reachability and macro risk

Completed on 2026-11-03:

- Added `sessions.py`: DST-aware ASIA/LONDON/PREMARKET/NEW_YORK analytical
  windows, exchange RTH/OVERNIGHT/ETH, early-close dates and point-in-time
  `SessionSnapshot`.
- Added `research/session_dataset.py`: 147 rows / 49 days; next-same-session
  direction (BULL 72 / BEAR 69 / NEUTRAL 6) and range-state labels.
- Added `ml/session_model.py`: frequency, logistic and GBM direction models with
  multiclass Brier/log-loss/ECE/confusion, plus consolidation evaluation.
- Results: direction frequency log loss 0.8650 beats logistic 2.5272 and GBM
  1.3781; NEUTRAL is absent from the 30-row test split. Consolidation logistic
  Brier 0.1496 / AUC 0.8995 / ECE 0.1925 vs frequency 0.2333; **NO_PROMOTION**
  because ECE and sample size fail the gate.
- Added `price_levels/reachability.py`: empirical forward-MFE touch probability
  conditioned on ATR distance; explicitly not target-before-stop.
- Added `macro/calendar.py` and `data/macro/sample_events.json`: point-in-time
  event schema/store, `upcoming`/`recent`/`event_risk`, and critical-day states
  with `directional_bias=None`. The sample has null consensus; no authorized
  live calendar is wired.
- Added `forecast/bundle.py`: ASIA/LONDON/NY/NEXT_DAY research outlooks with
  expected range, levels, touch probabilities and `NO_TRADE`.
- Added `forecast/evaluation.py` and `scripts/evaluate_forecasts.py`: realized
  range, p50/p80/p90 coverage, target touches and explicit `NOT_MATURED`.
- Added `docs/PHASE3B3_FINDINGS.md`,
  `reports/phase3b3_session_models.md/json`,
  `reports/forecast_evaluation.json`.

Verification commands:

```bash
python -m pytest -q                 # 154 passed, 1 skipped (155 with native)
python scripts/train_session_models.py
python -m nocturne forecast-bundle --instrument NQ
python -m nocturne evaluate-forecast --instrument NQ
python scripts/evaluate_forecasts.py
```

Blocked: authorized economic-calendar/news history, authentic tick/DOM/true
volume-at-price, CFE VX futures. Current V1 forecast is `NOT_MATURED`; no model
or forecast is promoted.

Next exact step: add an authorized point-in-time calendar adapter, expand the
session dataset beyond 60 days, and rerun session models with purged walk-forward
splits. Promotion gates: holdout Brier improvement, AUC ≥ 0.55, ECE ≤ 0.05 and
adequate sample size.

## Completed

Phase 0 — audit
- Read the full v2 package; audited the existing repo.
- Documented the gap analysis, decisions and status.

Phase 1 — contracts and data
- Pydantic event/level/prediction contracts.
- Instrument registry (NQ, MNQ, ES, MES, VX, ZN, ZB).
- DST-safe sessions, holidays, roll dates.
- Append-only JSONL event store with as-of replay.
- Yahoo bar adapter with provenance and incomplete-bar rejection.

Phase 2 — auction
- True trade-derived volume profile with POC/VAH/VAL, HVN/LVN and conservation.
- TPO profile, separate from volume.
- IB, opening range and VWAP.
- AMT balance/acceptance/value migration.

Phase 3 — strategies and backtest
- ORB/IB, VWAP pullback, VAH/VAL rejection.
- Bar backtester with costs, gap handling, stop-first ambiguity and a defined
  50/50 TP1/TP2 exit schedule.
- Real 60-day NQ 5m ORB result: 44 trades, 47.7% win, +$4,940, PF 1.1475,
  max drawdown $18,730, 41/44 timeouts. Development −$18,730 vs holdout
  +$23,670. Not promoted.

Phase 4 — models and API
- Triple-barrier labels and leak-safe features.
- Frequency, logistic and HistGradientBoosting baselines.
- Chronological walk-forward + Platt calibration.
- NQ result: frequency best (Brier 0.2474); logistic 0.2493; boosted 0.2488.
  `RESEARCH_ONLY`; no promotion.
- Model registry, append-only journal, read-only FastAPI.

Phase 5 — context
- ES/NQ relative state, beta, correlation, spread z-score.
- `^VIX` spot proxy (CFE VX blocked), ZN/ZB Yahoo proxies.
- Premarket state built from real 15m bars: 2026-11-03 NQ gap +0.46%,
  ES +0.05%, NQ led, VIX 21.41, ZN/ZB connected.

Phase 6 — order flow interfaces
- Typed trades/quotes, aggressor classification, CVD, footprint.
- Book reconstruction with sequence-gap invalidation.
- Data gate returns `UNAVAILABLE` without tick/quote history.

Phase 7 — knowledge
- Analyst thesis registry, separate from runtime inputs.

Phase 8 — safety
- Deterministic risk gates: stale data, low coverage, event lock, extreme
  volatility, expired signal, duplicate, negative EV -> `NO_TRADE`.
- Read-only API; no broker adapter or order endpoint.

## Verification

```bash
python -m pytest -q                 # 154 passed, 1 skipped (155 with native)
python -m nocturne audit
python -m nocturne train --instrument NQ
python -m nocturne forecast --instrument NQ
python -m nocturne context
python -m nocturne backtest --instrument NQ --days 60
python -m nocturne serve
```

## Blockers

- No true trade-by-price, tick, quote, DOM, or MBO history. Profile/order-flow
  code is tested with fixtures; live features are `DATA_BLOCKED`.
- No CFE VX futures history. `^VIX` spot is a labelled proxy.
- No licensed economic calendar redistribution; event gate is not wired to a
  live calendar.
- No C++ toolchain. Native source and parity contract exist, but no native
  module is built or claimed.

## Next exact step

1. Connect an authorized trade-by-price adapter and replace the bar
   approximation in the profile demo.
2. Add CFE VX front/back futures and a point-in-time calendar adapter.
3. Run the ORB/VWAP/value strategies across ES and NQ with a held-out final
   window and 2–4 tick cost stress.
4. Only after those gates: consider promotion, paper shadowing and a separate
   execution review.
