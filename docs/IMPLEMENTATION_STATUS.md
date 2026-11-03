# Implementation Status

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
| Event-driven bar backtester with costs | DONE | `backtest/engine.py`, 5 tests |
| Conservative intrabar ambiguity | DONE | Stop-first on same-bar stop+target |
| Walk-forward evaluation | PARTIAL | Chronological split implemented; full rolling report pending |

## Phase 4 — ML prediction v1

| Item | Status | Evidence |
|---|---|---|
| Triple-barrier labels | DONE | `research/labels.py`, 4 tests; ambiguity excluded |
| Historical-frequency baseline | DONE | `ml/baseline.py`; NQ walk-forward Brier 0.2474 |
| Logistic baseline | DONE | NQ Brier 0.2493 (worse than frequency) |
| Gradient-boosted challenger (sklearn) | DONE | NQ Brier 0.2488 (worse than frequency) |
| Calibration (Brier, reliability, ECE) | DONE | `ml/calibration.py`, Platt + metrics |
| Model registry | DONE | `models/registry/NQ-frequency-*`, metadata + joblib |
| Read-only forecast API + journal | DONE | FastAPI, append-only JSONL, 7 API tests |

## Phase 5 — Intermarket / premarket

| Item | Status | Evidence |
|---|---|---|
| ES/NQ relative state | DONE | `intermarket/context.py`; beta 1.82, corr 0.95 on 2026-11-02 |
| VX curve (CFE) | DATA_BLOCKED | `^VIX` spot proxy only; flag `VX_FUTURES_UNAVAILABLE` |
| ZN/ZB adapters | DONE | Yahoo front-month proxies; flag `ZN_ZB_YAHOO_PROXY` |
| PremarketState | DONE | `premarket.py`; real 2026-11-03 state built |
| Event/critical-day gates | PLANNED | Phase 8 |

## Phase 6 — Tape / DOM

| Item | Status | Evidence |
|---|---|---|
| Typed trade/quote/book interfaces | PLANNED | — |
| Aggressor classification + CVD | PLANNED | — |
| Footprint / DOM imbalance | PLANNED | — |
| C++ kernels | TOOLCHAIN_BLOCKED | No cmake/g++/pybind11 |

## Phase 7 — Knowledge / discretion

| Item | Status | Evidence |
|---|---|---|
| Analyst thesis record | PLANNED | — |
| Vault indexing | DATA_BLOCKED | Private vault; do not publish |

## Phase 8 — Hardening

| Item | Status | Evidence |
|---|---|---|
| CI Python + TypeScript | PARTIAL | Existing CI; v2 tests to be added |
| Drift/coverage/latency monitoring | PLANNED | — |
| Promotion/rollback | PLANNED | — |

## Current truth boundary

No calibrated model or profitable strategy is claimed. The existing 15-year
direction baseline did **not** beat the always-up rate on ES, NQ, or GC. The
2026-10-30 and 2026-11-02 calls are recorded misses and must remain in the
archive. New modules will report `DATA_BLOCKED` where the required data does not
exist.
