# Nocturne Futures

**A Python-first research platform for auction-market analysis, executable strategy tests, calibrated probability research, and a read-only forecast API.**

> **Maturity: research / non-production.** No broker connection, no order placement, no validated live edge. The first NQ model is `RESEARCH_ONLY`; the ORB backtest is a 60-day research result, not a promotion. Missing tick/DOM/VX data is marked **DATA_BLOCKED**, never filled with a guess.

---

## What is implemented

### Phase 3V — zero-cost futures research

Operator policy is **$0 spend**: Databento was used only for free metadata (auth
OK, GLBX.MDP3 2010–2026, quotes on file, nothing purchased). Free Yahoo NQ=F/ES=F
1m/5m/60m/daily history (154,506 rows) runs through the existing engines with
roll dates from free Databento symbology. Results: direction **rejected** for
NQ and ES; next-session compression (LightGBM) and large-range probabilities
beat trailing baselines (volatility persistence); VIX/VXN help 350-point NQ
range forecasts while positioning/rates mostly hurt; existing strategies have
insufficient samples (24–44 trades); all 20 hourly target-before-stop geometries
and **all 26 ranked signals rejected**. 451 tests pass. See
[findings](docs/PHASE3V_FINDINGS.md) and [tables](reports/phase3v_research.md).

### Phase 3U — free-data collection, backtest and forward cycle

`nocturne.collector` gathers keyless official data with a declared user agent,
per-domain rate limits, retry/backoff, content-addressed raw archives and a
revision ledger: FRED (16 series), CFTC Traders in Financial Futures, Treasury
DTS, SEC EDGAR filings, Federal Reserve press releases and BLS — **125,814
rows**. GDELT was rate-limited (HTTP 429). EIA/BEA/Nasdaq Data Link need free
keys. Every row carries a conservative `available_at`; revised macro series are
context only.

A pre-registered ^NDX walk-forward (2008–2026, 4,624 sessions) tested 14
point-in-time macro/positioning/filing features. Direction: no model beats the
frequency baseline (verdict INCONCLUSIVE, no skill). Range: base LightGBM
quantiles beat trailing quantiles (mean pinball 0.00202 vs 0.00285 in
development), but adding free features is worse in development (verdict FAIL).
One real shadow cycle ran: 4 issued / 2 matured / 2 audit-blocked. FRED closes
confirm both reference revisions are below published precision; outcomes
remain unverified. **444 tests pass.** New research-lane jobs
`FREE_DATA_COLLECTION` and `FREE_DATA_EXPERIMENT` run on the existing schedule.
**NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE / FUTURES_DATA_BLOCKED.** See
[findings](docs/PHASE3U_FINDINGS.md), [backtest](reports/phase3u_backtest.md)
and [free-data architecture](docs/architecture/free_data.md).

### Phase 3T — incident dispositions and quarantine isolation

Both pending forecast incidents are classified as observed provider revisions with
unverified finality. Exact original issuance inputs/inference reproduce; neither
incident is independently cleared or force-evaluated. **4 issued / 2 verified
matured / 2 pending / 0 missed**; four alerts remain open.

Execution, issuance and outcome-integrity health are now distinct. Exclusive
per-attempt research receipts let five genuine shadow operations complete despite
historical quarantine, retaining exit 1 and BLOCKED component health. Failed
generation/refresh, stale/missing receipts and exceptions are not forgiven. Local
alert acknowledgement retains OPEN; no HTTP mutation capability was added.

**431 tests pass locally and in isolation**, native parity included; five CI jobs
green at `6bd0f75` (run 42466314331). All four issued forecasts replay exactly. Two exercised
completions per task retain shadow exit 1 / research exit 0, with full lifecycle
receipts. Existing encrypted backup restores/replays 765 files in 20.64s, same
host only; independent recovery remains unverified.

No licensed futures data, new market fits, paid consumption or directional/
target-first finding. **USER_ACTION_REQUIRED / OFF_HOST_VERIFICATION_REQUIRED**.
**NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE**, no unsupported 70% claim. See
[findings](docs/PHASE3T_FINDINGS.md), [readiness](docs/BACKEND_READINESS.md),
[operator data checklist](docs/PHASE3S_FUTURES_PILOT.md),
[incident dispositions](reports/phase3t_incidents.json) and
[acceptance evidence](reports/phase3t_acceptance.json). Earlier phases below are historical.

### Phase 3S — protected APIs and authenticated private recovery

Reader/admin authentication, deny-by-default artifact access, bounded rate/request
limits, secret-safe fail-closed audits and isolated verified TLS are implemented.
Local/future always-on profiles preserve pythonw scheduling; unattended activation
still requires operator approval. AES-256-GCM backup packaging restores/replays a
real private snapshot in a fresh isolated environment, without activating it.

**408 tests pass locally and in isolation**, including native parity; the final
isolated suite tested `c5de881`; all five CI jobs are green at that commit in
run 42464277742 (`reports/phase3s_ci.json`).
Security-profile offline bootstrap verifies 58 wheel hashes,
13,458 installed files and exact inference for all four issued forecasts. Same-host encrypted
recovery is verified, but **OFF_HOST_VERIFICATION_REQUIRED** remains.

November 8 state: **4 issued / 2 verified matured / 2 pending**. Provider revisions
block both pending forecast audits; shadow exits 1, research exits 0, four alerts
are open. November 6 is not an evaluated outcome merely because time has elapsed.
Separate revision investigations preserve all predictions/denominators and remain
unapplied. No licensed futures receipts or paid consumption.

**NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE**; no arbitrary 70% claim. See
[findings](docs/PHASE3S_FINDINGS.md),
[secure deployment/recovery](docs/PHASE3S_SECURITY_DEPLOYMENT.md),
[bounded futures activation](docs/PHASE3S_FUTURES_PILOT.md),
[architecture](docs/ARCHITECTURE_PHASE3S.md),
[acceptance evidence](reports/phase3s_acceptance.json) and
[readiness gates](docs/BACKEND_READINESS.md). Sections below are historical.

### Phase 3R — hash-locked bootstrap and exact frozen inference

55 reviewed wheel hashes support offline Windows/CPython-3.14 bootstrap; installed
integrity checks cover 13,290 hashed files. A new venv/clone/native build passes
384 tests, as does the local suite. All five implementation CI jobs passed.
Frozen model loading rejects numerical-library drift before inference, and all
three original issued rows reproduce exact quantiles without changing artifacts.

A real backup/scheduled-tick collision was retained and fixed with admission and
bounded coordination, not hidden as success. Repeated real task completions pass.
Same-host recovery works; independent-host/encrypted off-host recovery remains
unverified. API path-query inputs are hardened, but deployment access controls
remain incomplete. Tasks still need an awake, logged-in host.

Forward state remains **3 issued / 2 verified matured / 1 pending**; authentic
futures access is **USER_ACTION_REQUIRED**. No new market model or trading edge.
**NO-GO frontend / NO_PROMOTION / NO_TRADE.** See
[findings](docs/PHASE3R_FINDINGS.md),
[reproducibility and recovery](docs/PHASE3R_REPRODUCIBILITY.md),
[acceptance evidence](reports/phase3r_acceptance.json) and
[readiness gates](docs/BACKEND_READINESS.md). Earlier sections are historical.

### Phase 3Q — scheduled recovery and isolated-environment proof

Existing Windows runners now launch without consoles; three genuine Task Scheduler
completions per task have complete zero-exit lifecycle receipts. A hidden-window
attempt still failed and remains recorded; the original control-event sender is
unconfirmed. Principals/settings/triggers unchanged; awake/logged-in host still
required. No 24/7 or unattended-account claim.

Fresh venv, independent clone and native build pass 362 tests, including parity.
Real proof replay exposed dependency drift that fixture tests missed; pinned
NumPy/pandas restore exact issuance/outcome checks without changing records.
A 654-file private restore verifies three forecasts/two outcomes. This remains
same-host recovery, not off-host durability or separate-host deployment.

Current forward state: **3 issued / 2 verified matured / 1 pending**; November 5
missed all range quantiles. Zero licensed futures rows: **USER_ACTION_REQUIRED**.
No new market model or independent futures result. **NO-GO frontend;
NO_PROMOTION / NO_TRADE.** See [findings](docs/PHASE3Q_FINDINGS.md),
[deployment procedure](docs/PHASE3Q_DEPLOYMENT.md),
[acceptance evidence](reports/phase3q_acceptance.json) and
[readiness gates](docs/BACKEND_READINESS.md). Earlier sections are historical.

### Phase 3P — private-evidence recovery, quantitative gates still blocked

Bounded local snapshots and a separate-location offline restore verify source
proofs, immutable forecasts/outcomes, SQLite state and six cached challenger
files. Two existing fixed index diagnostics reproduce exactly, not new predictive
evidence. 355 local tests including native parity and TypeScript passed.

Before November 6 00:00 UTC: two issued / one verified legacy matured / one
pending corrected forecast. Zero licensed futures rows; no new model fitting,
independent holdout scoring, paid consumption or unsupported target probabilities.
Direct shadow runner succeeds, but both scheduled tasks currently return
0xC000013A: **scheduled operation DEGRADED**, despite healthy core reports.
Same-host restore is not off-host durability or clean-host recovery.

See [current findings](docs/PHASE3P_FINDINGS.md),
[acquisition decision](docs/PHASE3P_DATA_ACCESS.md),
[timestamped evidence](reports/phase3p_evidence.json) and
[readiness gates](docs/BACKEND_READINESS.md). **Pre-frontend gate NOT PASSED;
NO_PROMOTION / NO_TRADE.** Earlier sections are historical checkpoints.

### Phase 3O — recovered audits, explicit dependency health

The pending forecast's Yahoo revision is reconciled against exact archived
issuance data, without rewriting forecasts, outcomes or denominators. Runtime
audits pass and genuine alert-resolution records are appended. New full-bar
proofs block again on changed observations or missing/corrupt evidence.

Component reports distinguish healthy services, blocked data, disabled training
and actual failures. An isolated seven-job fixture test exercises real research
workers end-to-end; it is not market performance. Actual futures access remains
**BLOCKED**, with zero licensed rows and no paid consumption.

See [recovery findings](docs/PHASE3O_FINDINGS.md),
[component health](reports/phase3o_operations.md),
[operator data checklist](docs/PHASE3O_DATA_ACCESS.md),
[architecture](docs/ARCHITECTURE_PHASE3O.md) and
[pre-frontend gates](docs/BACKEND_READINESS.md). **NO_PROMOTION / NO_TRADE**.
Historical checkpoint sections below describe their then-current state.

### Phase 3N — guarded futures pilot, still data-blocked

The existing Databento adapter now requires a fresh provider quote and explicit
request-bound operator approval before metered or credit-consuming downloads.
Metadata-only preflight, durable no-blind-retry reservations, bounded raw archives
and stronger ID/timestamp/tick/volume checks are implemented.

Verified receipts connect to the existing ORB/bar-VWAP backtester and target labels
through the Phase 3M orchestrator. The full path is fixture-tested; **actual NQ/ES
jobs remain BLOCKED with zero licensed rows**. Cost and account-credit eligibility
remain unknown. No new predictive model fit or promotion is claimed.
Versioned cashflow-v2 also corrects legacy slippage/commission arithmetic without
rewriting old results; actual execution assumptions remain unvalidated.
Default research no longer repeats old index experiments; futures jobs reuse
identity across dates unless receipts or research code change.
Current shadow state is 2 issued / 1 verified matured / 1 pending; the pending
forecast is `AUDIT_BLOCKED` by a newly detected Yahoo reference-close revision.
The first outcome still verifies; alerts remain open and forecasts are unchanged.

```powershell
python scripts/phase3n_futures.py --public-docs --research-check
```

This command does not download time-series data. See the
[acquisition decision and authorization steps](docs/PHASE3N_DATA_DECISION.md),
[findings](docs/PHASE3N_FINDINGS.md), [architecture](docs/ARCHITECTURE_PHASE3N.md)
and [backend readiness](docs/BACKEND_READINESS.md). Trading stays `NO_TRADE`.

### Phase 3M — bounded autonomous research backend

Persistent job state now connects real data validation, versioned features,
historical diagnostics, purged/calibrated logistic experiments, shadow adapters
and JSON/Markdown reporting. Separate process/lock lanes isolate research from
inference; unchanged experiment identities reuse saved models/results.

Executed two index-context backtests and two 750-observation development model
diagnostics. These are **not NQ/ES trading results or independent validation**.
Licensed futures jobs remain blocked; all trading stays `NO_TRADE`.

A separate six-hour Windows research task is deployed and observed successful;
the existing shadow task is unchanged. Both currently require an awake host and
interactive login. Forward state remains **2 issued / 1 verified matured / 1 pending**.

See [Phase 3M findings](docs/PHASE3M_FINDINGS.md),
[backend readiness evidence](docs/BACKEND_READINESS.md),
[execution architecture](docs/ARCHITECTURE_PHASE3M.md), and
[exact data-acquisition dependency](docs/DATA_ACQUISITION_PHASE3M.md).

```powershell
python scripts/phase3m_research.py --lane research
```

### Phase 3L checkpoint — 2026-11-05 UTC

The scheduler produced the first real research-grade outcome and the next
pre-open forecast: **2 issued, 1 verified matured, 1 pending**. November 4 NDX
range was **553.4434 points (1.96394%)**: above issued P50, below P80/P90.
Original forecast bytes and denominator are unchanged. This is one legacy
unadjusted observation, not proof of corrected-model calibration or a trading edge.

Added independent outcome verification, explicitly registered baseline comparisons,
receipt-validated contract replay and NQ target-grid labeling. Fixed AJ censoring
and observation-duration errors; old survival reports require review/recomputation.
Authentic futures data remains blocked, so no new directional or target model is
promoted. FRED/BLS context probes now succeed but are not historical PIT features.

See [Phase 3L findings](docs/PHASE3L_FINDINGS.md),
[architecture diagram](docs/ARCHITECTURE_PHASE3L.md),
[forward audit](reports/phase3l_forward_audit.json), and
[data-access readiness](reports/phase3l_readiness.json). Trading stays `NO_TRADE`.

### Phase 3K checkpoint — 2026-11-04 UTC

The Yahoo discrepancy is verified as an upstream **OHLCV revision**, not a local
parser error. Archived pre-issuance inputs exactly reproduce the original
forecast features. A separate hash-bound reconciliation permits the original
as-issued contract without changing its denominator or predictions. Yahoo's
internal reason and official exchange finality remain unconfirmed.

New acquisitions retain immutable hashed raw/normalized snapshots, HTTP response
bodies and revision lineage. Runtime forecasts link exact snapshot versions;
frozen model checksums and a research-history refresh guard prevent silent
replacement. **1 issued, 0 matured**; no outcome or forward accuracy is invented.
See [Phase 3K findings](docs/PHASE3K_FINDINGS.md) for evidence and limitations.

### Phase 3J checkpoint — 2026-11-04 UTC

Added durable local incident transitions, a read-only operational-health endpoint,
one-shot failure reporting, per-forecast outcome quarantine and task execution
logs. Password-backed unattended task installation is supported and dry-run
tested, but not activated without authorized account credentials. The existing
interactive task remains in place.

**1 issued, 0 matured.** The November 4 outcome is unavailable. A revision to the
prior NDX close also triggers an audit block; the original forecast is unchanged.
No new forward accuracy or trading claim is made. See
[Phase 3J findings](docs/PHASE3J_FINDINGS.md) for the blocker and deployment limits.

### Phase 3I checkpoint — 2026-11-04 UTC

Shadow operation now has OS locks, durable serialized journals, revised-snapshot
duplicate prevention, missed-deadline recovery, strict operational source checks,
completed-bar guards and 30/60/90 forward monitoring. A Windows 30-minute task is
installed on the authorized host **while the user is logged in and host awake**.

Runtime residual calibration was corrected without retraining. The original
forecast remains immutable and explicitly flagged as legacy unadjusted inference.
**1 issued, 0 matured**; no forward accuracy claim. Licensed futures and authorized
PIT calendar/news remain blocked. Contract-specific target-dataset gates and
event-proximity interfaces are fixture-tested, not empirical trading evidence.
See [Phase 3I findings](docs/PHASE3I_FINDINGS.md) and
[checkpoint](docs/IMPLEMENTATION_CHECKPOINT.md). All trading remains `NO_TRADE`.

### Phase 3H checkpoint — 2026-11-04

The validated NDX cash-session range model now runs as a **read-only shadow
service**. Forecasts are frozen before outcomes, stored append-only, and evaluated
only after the target session bar is available. Eligibility fails closed on stale,
missing or late data, and the service survives restarts through deterministic ids
and durable storage.

One forward forecast is stored for 2026-11-04; none has matured, so no forward
accuracy is claimed. New read-only endpoints expose shadow status, history,
evaluation and data health. Trading remains `NO_TRADE`.

Licensed NQ/ES futures data is still `DATA_BLOCKED`; exact requirements are in
[docs/FUTURES_DATA_REQUIREMENTS.md](docs/FUTURES_DATA_REQUIREMENTS.md). See
[Phase 3H findings](docs/PHASE3H_FINDINGS.md) and
[checkpoint](docs/IMPLEMENTATION_CHECKPOINT.md).

### Phase 3G checkpoint — 2026-11-04

Decades of free daily history are ingested with checksums and cross-source
validation: S&P 500 from 1927, Nasdaq-100 from 1985, Treasury yields from 1962,
VIX from 1990, plus ETFs and continuous futures proxies. The official BLS API is
verified; Databento and Bloomberg remain paid dependencies.

Four decades of walk-forward testing confirm that public price and macro context
does not predict next-day direction: AUC 0.498–0.508, and the 1990s edge decays
to 0.459 by the 2020s. Historical analogues add no value. Price-level touch
probabilities are strongly distance-dependent and are now measured with explicit,
separate event definitions.

All models remain `NO_PROMOTION`; forecasts remain `NO_TRADE`. One exception is
scoped: the frozen NDX daily range-quantile model kept near-nominal coverage
(0.534/0.816/0.920) and improved pinball loss on a one-shot 2024–2026 holdout, so
it is `RESEARCH_VALIDATED_PENDING_SHADOW` for the cash-session index range only —
not NQ futures, and not a trading decision. See
[Phase 3G findings](docs/PHASE3G_FINDINGS.md),
[protocol](docs/PHASE3G_PROTOCOL.md),
[data providers](docs/DATA_PROVIDERS.md) and
[checkpoint](docs/IMPLEMENTATION_CHECKPOINT.md).

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
