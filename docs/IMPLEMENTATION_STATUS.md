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
| ORB/IB strategy spec | PLANNED | — |
| VWAP pullback strategy spec | PLANNED | — |
| VAH/VAL rejection strategy spec | PLANNED | — |
| Event-driven bar backtester with costs | PLANNED | — |
| Conservative intrabar ambiguity | PLANNED | — |
| Walk-forward evaluation | PLANNED | — |

## Phase 4 — ML prediction v1

| Item | Status | Evidence |
|---|---|---|
| Triple-barrier labels | PLANNED | — |
| Historical-frequency baseline | PLANNED | — |
| Logistic baseline | PLANNED | — |
| Gradient-boosted challenger (sklearn) | PLANNED | — |
| Calibration (Brier, reliability, ECE) | PLANNED | — |
| Model registry | PLANNED | — |
| Read-only forecast API + journal | PLANNED | — |

## Phase 5 — Intermarket / premarket

| Item | Status | Evidence |
|---|---|---|
| ES/NQ relative state | PLANNED | — |
| VX curve (CFE) | DATA_BLOCKED | `^VIX` spot proxy only |
| ZN/ZB adapters | PLANNED | Yahoo proxies, unverified |
| PremarketState | PLANNED | — |
| Event/critical-day gates | PLANNED | — |

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
