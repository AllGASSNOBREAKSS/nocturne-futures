# Phase 3U — free market-data intelligence, backtest and forward cycle

November 9, 2026 UTC; branch `feat/phase3u`, base `632bcaf`.
**NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE / FUTURES_DATA_BLOCKED.**

## Baseline verification

Phase 3T claims re-checked at `632bcaf`: 431 tests passed locally and in an
isolated locked environment (native parity included); CI run 42466314331 green
at `6bd0f75`. Forward journal: 4 issued, 2 verified, 2 audit-blocked, 0 missed.
No frozen forecast, outcome, reconciliation or model byte was changed in 3U.

## A. Data acquisition

New package `src/nocturne/collector/`: polite client (declared user agent,
per-domain spacing, bounded retry with `Retry-After`, byte budget, robots.txt
enforcement for crawl access), content-addressed gzip raw archive, normalized
tables and an append-only revision ledger (appended / removed / revised rows
per acquisition). Each row carries a conservative `available_at`; rows marked
`pit_eligible = false` never enter backtests.

| Source | Status | Datasets | Rows | Coverage | PIT use |
|---|---|---|---|---|---|
| FRED CSV (existing adapter, 10 new series) | COLLECTED | 16 | 101,267 | 1986-01 → 2026-11-06 | 11 daily/weekly market series yes; NFCI, CPI, UNRATE, USREC, NASDAQ100 no |
| CFTC TFF futures-only (Socrata) | COLLECTED | 1 | 4,260 | 2006-06-13 → 2026-11-03 | yes (Tue + 6 days; shutdown backlogs late) |
| Treasury DTS operating cash | COLLECTED | 1 | 16,758 | 2005-10-03 → 2026-11-05 | no (2021 taxonomy change) |
| SEC EDGAR submissions (10 megacaps) | COLLECTED | 1 | 3,039 | 1994-01 → 2026-11-05 | yes (exact acceptance time) |
| Federal Reserve press RSS | COLLECTED | 1 | 20 | 2026-09-18 → 2026-11-05 | forward context only |
| BLS v2 (existing adapter, keyless) | COLLECTED | 1 | 470 | 2017-01 → 2026-10 | no (revised, no release clock) |
| GDELT DOC API | FAILED | 0 | 0 | — | HTTP 429 on three attempts (6 s spacing, backoff) |
| EIA, BEA, Nasdaq Data Link | BLOCKED_KEY_REQUIRED | — | — | — | free keys not configured |
| api.nasdaq.com | NOT USED | — | — | — | undocumented, timed out |
| Forex Factory | NOT CRAWLED | — | — | — | automated-access permission not verified |
| Databento | FUTURES_DATA_BLOCKED | — | — | — | `DATABENTO_API_KEY` absent |

Total **125,814 normalized rows**, 3.7 MB committed under `data/history/free/`
(evidence `reports/phase3u_collection.json`, HTTP log included). `api.bls.gov`
and the CFTC portal disallow crawling in robots.txt; both are documented public
APIs and were called under their published API terms, with robots status
recorded. Fed press items are classified by fixed title rules (no LLM).

The orchestrated research lane re-collected all six scheduled sources into the
ignored operational archive `data/research/free/`; the normalized data
reproduced the committed snapshot exactly (same experiment fingerprint
`de358f79…`), so no provider revision was observed within the phase window.

**Revision incidents:** FRED's Nasdaq-100 close (2-decimal publication) equals
both the original and revised Yahoo reference closes after rounding for both
audit-blocked forecasts (`reports/phase3u_reference_crosscheck.json`). The
±0.00195-point Yahoo revisions are below published precision. FRED has no
high/low, so outcome verification is still impossible: **AUDIT_BLOCKED retained,
nothing applied.**

## B. Historical backtest (pre-registered, index-level)

`src/nocturne/research/free_data_experiment.py`, `scripts/phase3u_backtest.py`;
report `reports/phase3u_backtest.{json,md}`; predictions
`data/studies/phase3u/de358f794e96e44b821dea79/predictions.csv`
(SHA-256 `0eee464e…`, reproduced byte-identically on re-runs).

- **Instrument/data:** ^NDX cash index, frozen checksum-verified Yahoo history
  (10,356 rows, 1985-10 → 2026-11-03). Not NQ futures.
- **Tasks:** next-session close > open (direction); next-session (high−low)/close
  P50/P80/P90 (range).
- **Design:** annual expanding refits 2008–2026, 5-day embargo, last 250 training
  rows for Platt calibration; development years 2008–2023 (3,969 sessions),
  previously-inspected 2024–2026 scored once (655 sessions); 4,624 test sessions.
- **Features:** base = 5 existing price features; free = base + 14 PIT features
  (VIX, VIX 5-day change, VXN−VIX, 10y−2y, 10y 5-day change, Baa spread and
  20-day change, Fed balance-sheet 13-week change, dollar 20-day change, NQ
  asset-manager and leveraged-fund net positioning and 4-week change, ES
  asset-manager net, megacap 10-K/10-Q count in 5 days). Join audit: every
  matched value was published ≥ 2 hours before its cutoff.
- **Baselines:** training-period up-frequency; trailing 250-session empirical
  range quantiles.

| Direction, development | AUC | Bal. acc | Brier | Log loss |
|---|---|---|---|---|
| Frequency | 0.4959 | 0.5000 | 0.24852 | 0.69018 |
| Base logistic (C=0.2) | 0.4896 | 0.4948 | 0.25081 | 0.69498 |
| Free-data logistic (C=0.2) | 0.4838 | 0.4917 | 0.25144 | 0.69622 |

Brier free − frequency **+0.00293 [+0.00136, +0.00445]** (worse); free − base
+0.00063 [−0.00076, +0.00196]. Exposed 2024–26: free AUC 0.5061, Brier 0.25120
vs frequency 0.24884. All C values (0.05/0.2/1.0) and 5/10/20-year/expanding
windows were reported, none selected; every configuration is worse than the
frequency baseline (best: base C=0.05 10-year, Brier 0.25015). **Verdict:
INCONCLUSIVE** under the pre-registered rule (free vs base CI spans zero); in
plain terms, no directional skill was found.

| Range, mean pinball | Development | Exposed | All |
|---|---|---|---|
| Trailing 250-session quantiles | 0.002853 | 0.002359 | 0.002783 |
| LightGBM base features | **0.002022** | 0.001955 | **0.002013** |
| LightGBM base + free | 0.002336 | **0.001831** | 0.002265 |

Coverage (P50/P80/P90, all years): trailing 0.506/0.793/0.885; base
0.576/0.823/0.903; free 0.566/0.805/0.884. Base LightGBM beats the trailing
baseline (development −0.000831 [−0.001204, −0.000528]; exposed −0.000403
[−0.000779, −0.000113]). Adding free features is worse in development
(+0.000314 [+0.000049, +0.000699]) but better in exposed years (−0.000124
[−0.000244, −0.000030]). **Verdict: FAIL.**

Post-hoc observation (not a result): the development loss is concentrated in
2008–2010, when free features had only about 1.5–3.5 years of training history (CFTC data start mid-2006); the
free model has lower pinball than the base model in 14 of 16 years from 2011.
This is a hypothesis to test on future forward data with a pre-declared start,
not a reason to re-score the same history.

Regimes (all years, free logistic AUC): VIX < 15 0.465, 15–25 0.497, > 25 0.477;
below 200-day 0.476; drawdown > 20% 0.454. The free-feature range model improves on
the trailing baseline in every regime except drawdown > 20% (0.006254 vs 0.006154).

Hypothetical index exposure (sign of p, 0.02 dead zone, **not NQ P&L**):
development free-model expectancy +0.0000070 per trade gross,
−0.000193 at 2 bp and −0.000493 at 5 bp; profit factor 1.0016 / 0.953 / 0.885;
max drawdown 53.6% gross. Always-long earned +0.000340 gross over the same
sessions. No signal survives costs.

## C. Forward testing (existing `ndx-range-v1` shadow)

One real cycle at 2026-11-09 02:17 UTC: refresh fetched ^NDX/^VIX through
November 6, generation `ALREADY_ISSUED` (no duplicate), `matured_now = 0`,
operational status `AUDIT_BLOCKED`, exit 1. Next issuance (target November 10)
occurs after the November 9 close via the existing 30-minute scheduler.

| Forecast | Target | P50 / P80 / P90 (points) | Realized | Status |
|---|---|---|---|---|
| `20d48fc4` | Nov 4 | 478 / 738 / 805 | 553.4 | matured: P80, P90 covered |
| `3db9c4cb` | Nov 5 | 479 / 714 / 883 | 1,471.8 | matured: all missed |
| `291aac9c` | Nov 6 | 919 / 1,606 / 1,981 | — | audit-blocked |
| `cd260712` | Nov 9 | 653 / 873 / 1,147 | — | audit-blocked; session not yet complete |

Mean pinball (n = 2, descriptive only): model 0.01016 vs trailing-250 baseline
0.01278; P80 coverage 1/2. Journal hashes recorded in
`reports/phase3u_forward.json`; the report never writes to the journal.

## D. Backend health

- **444 tests pass** locally with native parity (431 + 13 new collector/PIT/
  verdict/job-lane tests). 444 also pass in the isolated hash-locked environment; all five CI jobs green
  at `cfdab28` (run 42551201560) and `76fb02f` (run 42551366785). Evidence: `reports/phase3u_ci.json`,
  `reports/phase3u_tests.json`.
- Research lane executed `FREE_DATA_COLLECTION` (6/6 sources) and
  `FREE_DATA_EXPERIMENT` (fingerprint reuse) in 71 s. Experiment peak working
  set 226 MB, 30 s.
- Scheduler: shadow task 30-minute cadence (exit 1 = quarantine), research task
  6-hour cadence (exit 0).
- Defects found and fixed in this phase: GDELT timestamp parsing; the experiment
  computed every series' transforms on every series (log of negative spreads,
  discarded); timezone loss in the as-of join; the provider registry reported
  unverified free sources as `AVAILABLE` (now `IMPLEMENTED_UNVERIFIED`).

## E. Research readiness

Validated: none for trading. `ndx-range-v1` remains
`RESEARCH_VALIDATED_PENDING_SHADOW` (range only). Unvalidated: all directional
models, free-feature range model, every futures/target-first model. Blocked:
authentic NQ/ES contract, trade, depth and order-flow data
(`FUTURES_DATA_BLOCKED`), EIA/BEA/Nasdaq keys, independent final NDX OHLC for
the two incidents. Frontend gate: **NO_GO**.

## F. Required user actions

1. Optional free keys: `FRED_API_KEY` (ALFRED vintages for revised macro),
   `BLS_API_KEY`, `EIA_API_KEY`, `BEA_API_KEY`, `NASDAQ_DATA_LINK_API_KEY`.
2. Databento GLBX.MDP3 access and explicit quote approval (`PHASE3S_FUTURES_PILOT.md`).
3. An independent final NDX high/low source to clear the two audit-blocked forecasts.
