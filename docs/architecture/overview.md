# Architecture Overview

**Status:** backend research platform, not a production trading system.  
**Diagrams:** [`diagrams/01_system_runtime.svg`](diagrams/01_system_runtime.svg),
[`02_prediction_decision_flow.svg`](diagrams/02_prediction_decision_flow.svg),
[`03_research_training.svg`](diagrams/03_research_training.svg).

## Runtime flow

```text
Yahoo / Treasury / Fed / calendar
        │
        ▼
adapters/yahoo.py ──► contracts.MarketEvent ──► storage.EventStore (JSONL)
        │                                              │
        │                                              ▼
        │                                   replay(asof) / watermark
        │                                              │
        ▼                                              ▼
auction/ (profile, TPO, IB, AMT) ◄──── bars/trades ────┤
orderflow/ (tape, book, gates) ◄────── optional ───────┤
intermarket/ + premarket.py ◄───────── context ────────┤
        │                                              │
        ▼                                              ▼
strategies/ (ORB, VWAP, value) ──► backtest/engine ──► research/ labels
        │                                              │
        ▼                                              ▼
levels/ (candidate zones)                        ml/ baselines + calibration
        │                                              │
        └──────────────► risk/gates.py ◄───────────────┘
                              │
                              ▼
                 journal/ (append-only predictions)
                              │
                              ▼
                 api/ (read-only FastAPI)
```

## Component map

| Component | Module | Status |
|---|---|---|
| Canonical contracts | `contracts.py` | Implemented, 6 tests |
| Instrument registry | `instruments.py` | Implemented, 6 tests |
| Session/DST/roll clock | `market_clock.py` | Implemented, 7 tests |
| Immutable event store | `storage/event_store.py` | Implemented, 6 tests |
| Yahoo bar adapter | `adapters/yahoo.py` | Implemented, 2 tests |
| Volume profile / POC / VA | `auction/volume_profile.py` | Implemented, 7 tests |
| TPO profile | `auction/tpo.py` | Implemented, 2 tests |
| IB / opening range / VWAP | `auction/session.py` | Implemented, 4 tests |
| AMT state | `auction/state.py` | Implemented, 4 tests |
| Tape / quotes / CVD | `orderflow/tape.py` | Interfaces implemented; live data blocked |
| Book reconstruction | `orderflow/depth.py` | Implemented, sequence-gap tests |
| Intermarket context | `intermarket/context.py` | Implemented, real ES/NQ/VIX/ZN/ZB proxies |
| Premarket state | `premarket.py` | Implemented, real 2026-11-03 state |
| Strategy specs | `strategies/` | 3 candidates, 6 tests |
| Backtester | `backtest/engine.py` | Implemented, 5 tests |
| Labels / features | `research/` | Implemented, 6 tests |
| Baselines / calibration | `ml/` | Implemented, 4 tests |
| Risk gates | `risk/gates.py` | Implemented, 6 tests |
| Journal | `journal/store.py` | Implemented, 3 tests |
| Read-only API | `api/` | Implemented, 6 tests |
| Analyst theses | `knowledge/thesis.py` | Implemented, 3 tests |

## Python / TypeScript boundary

- **Python** owns data contracts, replay, auction/profile math, strategies,
  backtests, labels, models, risk, journal and API.
- **TypeScript** (`ts/`) owns the Yahoo fetch helper and zod validation of call
  artifacts. It does not compute features or make trading decisions.
- The boundary is JSON validated on both sides.

## Data gates

The platform distinguishes **available** from **blocked**:

| Data | State | Consequence |
|---|---|---|
| Daily OHLCV (15y) | Available | Research and labels |
| 5m/15m bars (5–60d) | Available | Session structure, ORB backtest |
| True trades by price | **Blocked** | Volume profile is tested with fixtures; bar approximation is labelled |
| Tick/quote/DOM/MBO | **Blocked** | Order-flow features return `UNAVAILABLE` |
| CFE VX futures | **Blocked** | `^VIX` spot is a labelled proxy |
| ZN/ZB futures | Yahoo proxies | Flagged `ZN_ZB_YAHOO_PROXY` |
| Economic calendar | Reference only | Not redistributed; no live event gate yet |

## C++ boundary

The C++20 kernel was built locally with MSVC 19.51 and pybind11 3.1; the parity
test passes. CI builds it on Ubuntu. The Python reference remains the source of
truth; the native path is optional and only used for the profiled aggregation
kernel.

## Safety boundary

There is no broker adapter, no order endpoint, and no TradingView automation.
The API is read-only. `risk/gates.py` can return `NO_TRADE` for stale data,
low coverage, event locks, extreme volatility, expired signals, duplicates, or
negative expected value.
