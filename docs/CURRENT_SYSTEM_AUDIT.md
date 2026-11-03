# Current System Audit

**Audit date:** 2026-11-03  
**Repository:** `https://github.com/AllGASSNOBREAKSS/nocturne-futures`  
**Branch:** `feat/backend-v2`  
**Baseline commit:** `f3ac7f9` (README chart update)  
**Baseline test result:** 12 passed

This audit was performed before any v2 backend code was added. It records what
actually exists, what was verified by running it, and what is missing relative to
`Nocturne_System_Architecture_v2.md`.

## 1. Runtime and toolchain

| Item | Version / status |
|---|---|
| Python | 3.14.6 |
| pandas | 3.0.3 |
| numpy | 2.5.0 |
| matplotlib | 3.11.2 |
| pytest | 9.1.1 |
| scikit-learn | 1.9.1 |
| scipy | 1.18.1 |
| Node | 24.15.0 |
| npm | 11.9.0 |
| pydantic | 2.14.2 (installed for v2) |
| FastAPI | 0.162.0 (installed for v2) |
| C++ toolchain | **absent** — no `cmake`, `g++`, or `pybind11` |
| Parquet/Arrow | **absent** |

The absence of a C++ toolchain is a real blocker for native kernels. The Python
reference remains the source of truth; C++ is deferred, not faked.

## 2. Existing code inventory

| Path | What it does | Verified |
|---|---|---|
| `src/nocturne/models.py` | Dataclasses for `Call`, `Instrument`, `Scenario`, `Level` | Loads the committed call |
| `src/nocturne/stats.py` | ATR, realized vol, event/seasonality summaries | Unit tests pass |
| `src/nocturne/levels.py` | Level utilities, round numbers, ATR envelope | Unit tests pass |
| `src/nocturne/scenarios.py` | Expected close, down probability, bucket lookup | Unit tests pass |
| `src/nocturne/score.py` | Scores a call against settlement | Known 2026-10-28 scorecard passes |
| `src/nocturne/report.py` | Markdown, matplotlib charts, HTML dashboard | Build produces 5 artifacts |
| `src/nocturne/cli.py` | `build`, `score`, `dashboard` | Works |
| `ts/` | Yahoo fetch + zod validation | `npm run typecheck` and `validate` pass |
| `data/snapshots/` | Dated call and actual artifacts | Committed |
| `data/studies/` | 15y CSVs + FOMC/seasonality study | Reproducible |
| `reports/` | Call, scorecard, charts, dashboard | Generated |
| `tests/` | 12 tests | Pass |

## 3. Data inventory

| Data | Coverage | Granularity | Rights / caveat |
|---|---|---|---|
| ES, NQ, GC, SI daily | 15 years | Daily OHLCV | Yahoo public endpoint; front-month, not roll-adjusted |
| ES, NQ, GC, SI intraday | 5 days | 5m / 15m | Yahoo public endpoint |
| VIX, DXY, 10Y, S&P, Nasdaq | 10 days to 15 years | Daily | Public proxies, not exchange feeds |
| Treasury curve | Daily | 1M–30Y | US Treasury public |
| FOMC calendar/statements | 2024–2026 | Event | Federal Reserve public |
| Economic calendar | Current week | Event | ForexFactory JSON; **no redistribution** |
| Earnings calendar | Selected dates | Event | Nasdaq public endpoint |
| Tick / DOM / MBO / footprint | **none** | — | **DATA_BLOCKED** |
| True traded volume-at-price | **none** | — | **DATA_BLOCKED** |
| CFE VX futures curve | **none** | — | **DATA_BLOCKED**; `^VIX` spot is a labeled proxy |
| ZN/ZB futures | not yet wired | — | Yahoo `ZN=F` / `ZB=F` available but unverified |

## 4. What the existing system does not have

- No canonical event envelope with `event_time` / `available_at` / `received_at`.
- No instrument registry with exchange, expiry, tick value, or roll rules.
- No immutable event store or as-of replay.
- No true volume profile, TPO profile, IB, value migration, or AMT state.
- No order-flow/DOM interfaces or data gates.
- No intermarket/premarket state object.
- No executable strategy specs or event-driven backtester.
- No triple-barrier labels, calibration, or model registry.
- No risk gate, forecast journal, or read-only API.
- No C++ kernel or parity harness.
- The existing call/report pipeline is a **research artifact**, not a calibrated
  prediction system.

## 5. What must be preserved

- The dated call artifacts and the scorecard pipeline.
- The 15-year study and its committed CSVs.
- The TypeScript ingestion/validation path.
- All 12 existing tests.
- The public README claims must be corrected as the backend grows; do not
  retroactively claim the prototype was a validated model.

## 6. Conflicts between the package and the repo

| Package assumption | Actual repo | Resolution |
|---|---|---|
| Existing frontend/apps | None; only reports/TS | No frontend to preserve |
| Tick/DOM history | None | Interfaces + gates; mark `DATA_BLOCKED` |
| True volume-at-price | None | Python algorithm + synthetic fixtures; bar approximation labeled |
| C++ toolchain | Absent | Python reference; native source deferred |
| LightGBM | Not installed | sklearn baseline first; LightGBM optional |
| Parquet/Arrow | Not installed | Append-only JSONL event store first |
| CFE VX / ZN / ZB | Not wired | Registry + adapters; VX marked proxy until real data |

## 7. Baseline commands

```bash
python -m pytest -q
python -m nocturne build --date 2026-10-27
cd ts && npm run typecheck && npm run validate -- ../data/snapshots/2026-10-27/call.json
```

All three passed at audit time.
