# Implementation Checkpoint

**Date:** 2026-11-03  
**Branch:** `feat/phase3a` (merged to `main`)  
**Base:** `f3ac7f9`  
**Latest backend commit:** see `git log --oneline -1`

## Phase 3A — backtest validation and predictive foundation

Completed on 2026-11-03:

- Reproduced the suite: **121 passed + 1 native skip**; **122 passed** with the
  C++ module on PYTHONPATH`.
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
python -m pytest -q                 # 121 passed, 1 skipped (122 with native)
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
