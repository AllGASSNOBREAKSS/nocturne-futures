# Nocturne Futures

**A Python-first research platform for auction-market analysis, executable strategy tests, calibrated probability research, and a read-only forecast API.**

> **Maturity: research / non-production.** No broker connection, no order placement, no validated live edge. The first NQ model is `RESEARCH_ONLY`; the ORB backtest is a 60-day research result, not a promotion. Missing tick/DOM/VX data is marked **DATA_BLOCKED**, never filled with a guess.

---

## What is implemented

| Capability | Module | Status |
|---|---|---|
| Canonical event, level and prediction contracts | `contracts.py` | Implemented |
| Instrument registry: NQ, MNQ, ES, MES, VX, ZN, ZB | `instruments.py` | Implemented |
| DST-safe sessions, holidays, roll dates | `market_clock.py` | Implemented |
| Immutable JSONL event store + as-of replay | `storage/event_store.py` | Implemented |
| Yahoo bar adapter with provenance | `adapters/yahoo.py` | Implemented |
| Volume profile, POC, VAH/VAL, HVN/LVN | `auction/volume_profile.py` | Implemented; true trades required |
| TPO / Market Profile | `auction/tpo.py` | Implemented; separate from volume |
| IB, opening range, VWAP | `auction/session.py` | Implemented |
| AMT balance / acceptance / value migration | `auction/state.py` | Implemented |
| Tape, quotes, CVD, footprint | `orderflow/` | Interfaces + gates; live data blocked |
| DOM book reconstruction | `orderflow/depth.py` | Implemented; sequence gaps handled |
| ES/NQ, VIX proxy, ZN/ZB context | `intermarket/` | Implemented; VX futures blocked |
| Premarket state | `premarket.py` | Implemented |
| ORB, VWAP pullback, VAH/VAL rejection | `strategies/` | Implemented |
| Bar backtester with costs and ambiguity | `backtest/` | Implemented |
| Triple-barrier labels, features | `research/` | Implemented |
| Frequency/logistic/boosted baselines | `ml/` | Trained on NQ |
| Calibration, registry | `ml/calibration.py`, `ml/registry.py` | Implemented |
| Risk gates (`NO_TRADE`) | `risk/gates.py` | Implemented |
| Forecast journal | `journal/` | Append-only |
| Read-only FastAPI | `api/` | Implemented |
| Analyst thesis registry | `knowledge/` | Implemented |
| C++ profile/replay kernels | `native/` | **TOOLCHAIN_BLOCKED** |

**Test suite:** 105 tests passing, plus one optional native parity test skipped
until the C++ toolchain is available.

---

## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m pytest

python -m nocturne audit
python -m nocturne train --instrument NQ
python -m nocturne forecast --instrument NQ
python -m nocturne context
python -m nocturne backtest --instrument NQ --days 60
python -m nocturne serve --host 127.0.0.1 --port 8000
```

TypeScript pipeline:

```bash
cd ts
npm install
npm run typecheck
npm run validate -- ../data/snapshots/2026-10-27/call.json
```

---

## Architecture

The governing diagrams are copied into [`docs/architecture/diagrams/`](docs/architecture/diagrams/):

- [System runtime](docs/architecture/diagrams/01_system_runtime.svg)
- [Prediction / decision flow](docs/architecture/diagrams/02_prediction_decision_flow.svg)
- [Research / training](docs/architecture/diagrams/03_research_training.svg)

```text
bars / trades / macro
        │
        ▼
contracts ──► event store ──► replay(asof)
        │                         │
        ▼                         ▼
auction / orderflow ◄────── session clock
        │
        ▼
strategies ──► backtester ──► labels ──► models ──► calibration
        │                                      │
        ▼                                      ▼
levels / context ──────────► risk gates ──► journal ──► read-only API
```

Python owns data, math, strategies, models, risk and API. TypeScript owns the
fetch/validation helper. JSON is the contract between them.

See [`docs/architecture/overview.md`](docs/architecture/overview.md) for the
component map and data gates.

---

## Auction Market Theory and profiles

- **Volume profile** sums executed quantity by price. POC, VAH/VAL and HVN/LVN
  are computed from that distribution with a deterministic 70% expansion and a
  nearest-VWAP POC tie-break.
- **TPO** counts time-bracket occupancy. It is a separate module and separate
  field names; a test proves the two can disagree on the same session.
- **IB / opening range** are time-boxed RTH windows.
- **AMT state** classifies balance/imbalance, acceptance/rejection and value
  migration. These are candidate features, not guarantees.

The repo has **no true trade-by-price history**. The profile engine is tested on
synthetic trades; the demo path uses a `BAR_APPROXIMATION` label. It is never
described as exchange-accurate POC/VAH/VAL.

---

## Strategies and the honest backtest

| Strategy | Entry | Stop | Targets |
|---|---|---|---|
| **ORB/IB breakout** | close beyond 60m IB ± 2 ticks | opposite IB side | 1R/2R/3R |
| **VWAP pullback** | pullback to rising VWAP, close above | 3-bar low / VWAP − 0.75 ATR | 1R/2R |
| **VAH/VAL rejection** | excursion beyond value, close back inside | beyond excursion | prior POC |

**ORB on NQ, 60 days of 5-minute bars** (`python -m nocturne backtest --instrument NQ --days 60`):

| Metric | Value |
|---|---:|
| Trades | 44 |
| Win rate | 50.0% |
| Net | **+$8,137.50** |
| Profit factor | 1.247 |
| Max drawdown | **$16,105.00** |
| Timeout exits | 40 / 44 |

This is **not** a validated edge. Forty of 44 trades exited at the horizon, the
P&L is concentrated on the short side, and the drawdown is roughly twice the
net profit. The raw ledger is in `reports/backtest_orb_NQ.json`. Full specs and
caveats: [`docs/STRATEGY_SPECS.md`](docs/STRATEGY_SPECS.md).

---

## Models: negative result, recorded

NQ, 15 years of daily bars, triple barrier (+1.5 ATR / −1.0 ATR / 5 sessions),
2,940 binary samples, chronological walk-forward with a separate calibration
slice:

| Model | Brier | Log loss | Accuracy | ECE |
|---|---:|---:|---:|---:|
| Historical frequency | **0.2474** | **0.6884** | 0.563 | 0.048 |
| Logistic | 0.2493 | 0.6927 | 0.558 | 0.076 |
| Hist. gradient boosting | 0.2488 | 0.6914 | 0.574 | 0.067 |

The frequency baseline wins; no model is promoted. `RESEARCH_ONLY` is the
correct status. Details: [`docs/architecture/model_validation.md`](docs/architecture/model_validation.md).

---

## Read-only API

```bash
python -m nocturne serve
```

| Endpoint | Purpose |
|---|---|
| `/health` | status, read-only flag, journal counts |
| `/v1/predictions/latest?instrument=NQ` | latest journaled prediction |
| `/v1/predictions/{id}` | one prediction |
| `/v1/market-state?instrument=NQ` | regime, critical-day state, quality |
| `/v1/auction/profile?instrument=NQ&session=RTH` | profile artifact or reason |
| `/v1/levels?instrument=NQ` | level artifact or reason |
| `/v1/intermarket/state` | ES/NQ/VIX/ZN/ZB context |
| `/v1/premarket/state` | overnight gap/range, prior RTH, leadership |
| `/v1/models/status` | registry metadata |

No order endpoint exists. See [`docs/architecture/api.md`](docs/architecture/api.md)
for an illustrative response.

---

## Data gates and provenance

| Data | State |
|---|---|
| Daily OHLCV, 15 years | Available (Yahoo, public/unofficial) |
| 5m/15m bars, 5–60 days | Available (Yahoo) |
| True trades by price | **DATA_BLOCKED** |
| Tick / quotes / DOM / MBO | **DATA_BLOCKED** |
| CFE VX futures | **DATA_BLOCKED**; `^VIX` is a labelled spot proxy |
| ZN/ZB | Yahoo front-month proxies, flagged |
| Economic calendar | Reference only; not redistributed |

Every stored event carries `event_time_utc`, `available_at_utc`,
`received_at_utc`, source and license scope. Replay filters on availability, so
future revisions cannot leak into earlier features.

---

## Repository layout

```text
src/nocturne/
  contracts.py          Pydantic event/level/prediction contracts
  instruments.py        NQ, MNQ, ES, MES, VX, ZN, ZB
  market_clock.py       sessions, DST, holidays, rolls
  storage/              append-only JSONL event store
  adapters/             Yahoo bar adapter
  auction/              volume profile, TPO, IB, AMT state
  orderflow/            tape, CVD, footprint, book reconstruction
  intermarket/          ES/NQ, VIX proxy, ZN/ZB context
  premarket.py          machine-readable premarket state
  strategies/           ORB, VWAP pullback, VAH/VAL rejection
  backtest/             event-driven bar backtester
  research/             features, labels, walk-forward
  ml/                   baselines, calibration, registry
  risk/                 deterministic NO_TRADE gates
  journal/              append-only predictions and outcomes
  api/                  read-only FastAPI
  knowledge/            analyst thesis registry
data/
  market/daily/         current backend bars
  studies/daily_15y/    frozen 15-year research bars
  snapshots/            dated call artifacts
  journal/              prediction journal
models/registry/        versioned model metadata + artifacts
docs/                   audit, status, architecture, strategy specs
reports/                generated call, scorecard, charts, backtest ledger
tests/                  105 tests
ts/                     TypeScript fetch + zod validation
```

---

## Archive

The first dated call and its scorecard remain in the repository:

- `reports/2026-10-27_call.md`
- `reports/2026-10-28_scorecard.md`
- `reports/2026-10-27_dashboard.html`
- `reports/2026-10-27_levels.png`

Result: 2/4 directions, 1/4 close bands, 2/4 full ranges, 0.64% mean absolute
close error. It is a historical research artifact, not a model track record.

---

## Roadmap

- **Next:** true trade-by-price and licensed tick/DOM adapters; VX futures;
  event calendar with point-in-time vintages; five-bucket probability output.
- **Then:** purged walk-forward with event embargo; ablation of AMT, profile,
  order flow, intermarket and macro features; calibration by regime.
- **Only after evidence:** model promotion, paper shadowing, and a separate
  review for any execution path.

See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) and
[`docs/roadmap.md`](docs/roadmap.md).

---

## Disclaimer

Research software, not investment advice. Futures are leveraged. The platform
has no validated live edge, no broker integration, and no order-placement
capability. Do not trade off a single forecast.
