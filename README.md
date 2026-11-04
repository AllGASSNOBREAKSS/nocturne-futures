# Nocturne Futures

**A Python-first research platform for auction-market analysis, executable strategy tests, calibrated probability research, and a read-only forecast API.**

> **Maturity: research / non-production.** No broker connection, no order placement, no validated live edge. The first NQ model is `RESEARCH_ONLY`; the ORB backtest is a 60-day research result, not a promotion. Missing tick/DOM/VX data is marked **DATA_BLOCKED**, never filled with a guess.

---

## What is implemented

### Phase 3F checkpoint — 2026-11-03

Direction diagnostics show the current features predict **activity**, not
**direction**: material-move AUC ≈ 0.70, bull-versus-bear AUC ≈ 0.52. Range
quantiles were recalibrated with rolling residuals and now cover closer to
nominal at every tested quantile. Competing-outcome target survival is implemented
and shows 200–500 point targets are rarely reached before the original stop.

All models remain `NO_PROMOTION`; forecasts remain `NO_TRADE`. Licensed data
credentials are still absent. See
[Phase 3F findings](docs/PHASE3F_FINDINGS.md),
[protocol](docs/PHASE3F_PROTOCOL.md) and
[checkpoint](docs/IMPLEMENTATION_CHECKPOINT.md).

### Phase 3E checkpoint — 2026-11-03

Authenticated Databento and ALFRED adapters are implemented and fixture-tested;
no credentials were present, so real licensed downloads remain **DATA_BLOCKED**.
LightGBM ablations, two-hour range quantiles, nested-target monotonicity audits,
immutable development replay and fail-closed promotion evidence are implemented.
All models remain `NO_PROMOTION`; forecasts remain `NO_TRADE`.

Replay produced 12 frozen development forecasts, all matured. ASIA replay windows
are blocked by incomplete cache coverage. See
[Phase 3E findings](docs/PHASE3E_FINDINGS.md),
[protocol](docs/PHASE3E_PROTOCOL.md) and
[checkpoint](docs/IMPLEMENTATION_CHECKPOINT.md).

### Phase 3D checkpoint — 2026-11-03

Two years of public hourly NQ/ES history and about 40 years of official FRED
context are now downloaded with checksums. Hourly research uses a separate
two-hour contract; it does not extend five-minute session coverage. Latest-vintage
FRED values are excluded from historical model features.

Purged, day/signal-grouped expanding and rolling validation, time-separated
calibration and moving-block uncertainty are implemented. Rebuilt complete-session
data contain 86 rows; hourly datasets contain 10,344 NQ and 10,336 ES rows.
Hourly Brier improvements are retrospective evidence, **not promotion**. Direction
class recall remains weak. Production probabilities remain null and `NO_TRADE`.

See [Phase 3D findings](docs/PHASE3D_FINDINGS.md),
[fixed protocol](docs/PHASE3D_PROTOCOL.md) and
[checkpoint](docs/IMPLEMENTATION_CHECKPOINT.md) for commands, evidence and blockers.

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
| C++ profile/replay kernels | `native/` | Built; parity passes (MSVC/CI) |
| Point-in-time intraday features | `research/intraday_features.py` | Implemented; 2 leakage tests |
| Target-first probability experiment | `ml/target_model.py` | Implemented; **NO_PROMOTION** |
| Significant price-level engine | `price_levels/` | Implemented; confluence + empirical touch stats |
| Expected-range model | `research/range_model.py` | Implemented; ATR-bucket quantiles |
| Regime engine | `regime.py` | Implemented; current + empirical transitions |
| Structured Forecast V1 | `forecast/v1.py` | Implemented; research-only, null probabilities |
| Forecast API | `api/app.py` | `GET /v1/forecast/v1` |
| Session engine | `sessions.py` | Implemented; DST and early-close tests |
| Session direction / consolidation | `ml/session_model.py` | Research; **NO_PROMOTION** |
| Level reachability | `price_levels/reachability.py` | Empirical touch probability; not target-before-stop |
| Macro calendar / critical day | `macro/calendar.py` | Sample schedule only; authorized adapter blocked |
| Multi-session bundle | `forecast/bundle.py` | Research-only; `NO_TRADE` |
| Forecast evaluation | `forecast/evaluation.py` | Implemented; explicit `NOT_MATURED` |

**Test suite:** 154 tests passing, plus one native parity test that is skipped
unless the C++ module is built. With the module on `PYTHONPATH`, 155 pass.

---

## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m pytest

python -m nocturne audit
python -m nocturne train --instrument NQ
python -m nocturne forecast --instrument NQ
python -m nocturne context
python -m nocturne study
python -m nocturne dataset --instrument NQ --strategy vwap
python -m nocturne forecast-v1 --instrument NQ
python -m nocturne forecast-bundle --instrument NQ
python -m nocturne evaluate-forecast --instrument NQ
python -m nocturne levels --instrument NQ
python -m nocturne range --instrument NQ
python -m nocturne regime --instrument NQ
python -m nocturne backtest --instrument NQ
python -m nocturne serve --host 127.0.0.1 --port 8000
python scripts/ml_audit.py
python scripts/train_target_model.py
python scripts/train_session_models.py
python scripts/evaluate_forecasts.py
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

**Phase 3A held-out study** (`python -m nocturne study`): first 60% development,
last 40% holdout, $2.50/contract/side, 1-tick slippage.

| Instrument | Strategy | Dev net $ | Holdout net $ | Dev PF | Holdout PF |
|---|---|---:|---:|---:|---:|
| NQ | ORB | **−18,730** | **+23,670** | 0.313 | 4.799 |
| NQ | VWAP | +1,911 | +8,398 | 1.160 | 2.285 |
| NQ | value | +2,935 | −6,170 | 1.538 | 0.475 |
| ES | ORB | −5,853 | +3,665 | 0.580 | 1.531 |
| ES | VWAP | −5,342 | +1,149 | 0.401 | 1.358 |
| ES | value | −320 | +2,030 | 0.902 | 1.907 |

**The ORB timeouts are explained:** median risk is **208.9 NQ points**,
median MFE is **0.26R**, only **4.5%** of trades reach 1R, **0%** reach 2R, and
all 41 timeouts had MFE below 1R. The 60-minute IB is too wide for a 24-bar
horizon. The ORB sign flip between development and holdout is regime dependence,
not an edge. No strategy is promoted. Full evidence:
[`docs/PHASE3A_FINDINGS.md`](docs/PHASE3A_FINDINGS.md) and
[`docs/STRATEGY_SPECS.md`](docs/STRATEGY_SPECS.md).

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

**Phase 3A audit:** four label geometries (1.5/1.0/5d, 1.0/1.0/3d, 1.0/0.5/5d,
2.0/1.0/10d) all had frequency as the best Brier. The lower Brier in the
tight-stop and long-horizon configs (0.232) reflects a more imbalanced class
distribution, not better skill. At p ≥ 0.50 the threshold strategy loses after
costs; p ≥ 0.55/0.60 is positive on only 42/18 trades and is not validated.
Full audit: [`docs/PHASE3A_FINDINGS.md`](docs/PHASE3A_FINDINGS.md).

### Phase 3B target-first model

Combined VWAP + revised-ORB + value datasets, point-in-time intraday features,
signal-grouped chronological split:

| Item | Value |
|---|---:|
| Binary rows / signals | 123 / 75 |
| Base rate | 0.520 |
| Test rows | 22 |
| Frequency Brier | 0.2688 |
| Logistic Brier | 0.2735 |
| GBM Brier | **0.2447** |

**NO_PROMOTION.** The GBM’s lower Brier comes with **AUC 0.411** (worse than
random), **ECE 0.154**, and a test positive rate of 0.636 vs 0.443 in training.
That is a class-shift artifact, not ranking skill. Full report:
[`docs/PHASE3B_FINDINGS.md`](docs/PHASE3B_FINDINGS.md).

### Levels, range and regime

- **Level engine:** prior RTH/week, overnight, Asia/London/NY, IB/OR, POC/VAH/VAL,
  HVN/LVN, VWAP and volatility bands, clustered at 8 NQ ticks with empirical
  touch/reaction statistics.
- **Expected range:** NQ full-session p50 **260**, p80 **402**, p90 **512** points;
  P(≥200) **0.705**, P(≥350) **0.270**, P(≥500) **0.112**.
- **Regime:** current NQ state **COMPRESSION**, ADX 35.85, volatility percentile
  0.20; empirical 24-bar transitions are reported, not asserted.
- **Forecast V1:** research-only, `decision=NO_TRADE`, null probabilities, with
  levels, range, regime and provenance.

### Phase 3B.3 session models

49 days × 3 analytical sessions = 147 rows; chronological day split 87/30/30.
Direction is BEAR/NEUTRAL/BULL over the next same session; consolidation is next
session range ≤ 0.8× current range.

| Task | Model | Test metric | Result |
|---|---|---|---|
| Direction | Frequency | Log loss 0.8650 / acc 0.400 | **baseline wins** |
| Direction | Logistic | Log loss 2.5272 / acc 0.400 | no |
| Direction | GBM | Log loss 1.3781 / acc 0.267 | no |
| Consolidation | Frequency | Brier 0.2333 / acc 0.633 | baseline |
| Consolidation | Logistic | Brier 0.1496 / AUC 0.8995 / ECE 0.1925 | promising, not calibrated |
| Consolidation | GBM | Brier 0.1947 / AUC 0.7656 / ECE 0.1690 | no |

**NO_PROMOTION.** NEUTRAL is only 6/147 and absent from the 30-row test split.
The consolidation logistic model has a lower Brier and high AUC, but ECE 0.19
and a 30-row test set are not enough for promotion. Details:
[`docs/PHASE3B3_FINDINGS.md`](docs/PHASE3B3_FINDINGS.md).

### Reachability, macro and multi-session contracts

- **Reachability:** empirical touch probability conditioned on ATR distance; it
  is not a target-before-stop probability. Forecast targets carry
  `touch_probability`, `touch_method`, `touch_sample_n`.
- **Macro:** `CalendarStore` + `EconomicEvent` + critical-day states. The
  committed calendar is an explicitly labelled public-schedule sample with null
  consensus; no authorized live calendar adapter is wired.
- **Bundle:** ASIA, LONDON, NEW_YORK and NEXT_DAY outlooks; all research-only
  `NO_TRADE` with null direction and target-before-stop probabilities.
- **Evaluation:** `evaluate_forecast` / `evaluate_bundle`; `NOT_MATURED` is
  explicit. Current V1 artifact is not yet matured.

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
  sessions.py           analytical Asia/London/NY windows + snapshots
  storage/              append-only JSONL event store
  adapters/             Yahoo bar adapter
  auction/              volume profile, TPO, IB, AMT state
  orderflow/            tape, CVD, footprint, book reconstruction
  intermarket/          ES/NQ, VIX proxy, ZN/ZB context
  premarket.py          machine-readable premarket state
  strategies/           ORB, VWAP pullback, VAH/VAL rejection
  backtest/             event-driven bar backtester + held-out study
  price_levels/         candidate zones, clustering, touch/reachability
  forecast/             V1, multi-session bundle, evaluation + journals
  macro/                economic events, calendar store, critical-day rules
  regime.py             current regime + empirical transitions
  research/             features, labels, range, session/target datasets
  ml/                   baselines, target/session models, calibration, registry
  risk/                 deterministic NO_TRADE gates
  journal/              append-only predictions and outcomes
  api/                  read-only FastAPI
  knowledge/            analyst thesis registry
native/                 C++20 volume kernel + pybind11 + parity test
data/
  market/daily/         current backend bars
  market/intraday/      cached 5m bars (sha256, reproducible)
  research/             target-level + session datasets
  forecasts/            Forecast V1 and bundle artifacts
  macro/                sample public schedule (not live consensus)
  studies/daily_15y/    frozen 15-year research bars
  snapshots/            dated call artifacts
  journal/              prediction + forecast + bundle journals
models/registry/        versioned model metadata + artifacts
docs/                   audit, status, architecture, Phase 3A/3B/3B.3 findings
reports/                call, scorecard, backtest ledgers, ML/session audits
scripts/                refresh data, study, ML audit, target/session models, evaluation
tests/                  154 tests + optional native parity
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

- **Immediate (Phase 3C):** add an authorized point-in-time economic calendar and
  news adapter, expand the session dataset beyond 60 days, and rerun direction and
  consolidation models with purged walk-forward splits and session-specific
  samples. Require holdout Brier improvement **plus AUC ≥ 0.55 and ECE ≤ 0.05**
  before shadow promotion.
- **Reachability:** calibrate the empirical touch probabilities by horizon and
  regime; keep them distinct from target-before-stop probabilities.
- **Target geometry:** rebuild ORB around a tighter stop or full-session horizon
  and evaluate once on the existing holdout.
- **Data:** true trade-by-price and licensed tick/DOM adapters; CFE VX futures;
  authorized economic calendar and news history.
- **Then:** purged walk-forward with event embargo; calibration by regime;
  empirical level-ranking calibration; critical-day ML only with adequate history.
- **Only after evidence:** model promotion, paper shadowing, and a separate
  review for any execution path.

See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) and
[`docs/roadmap.md`](docs/roadmap.md).

---

## Disclaimer

Research software, not investment advice. Futures are leveraged. The platform
has no validated live edge, no broker integration, and no order-placement
capability. Do not trade off a single forecast.
