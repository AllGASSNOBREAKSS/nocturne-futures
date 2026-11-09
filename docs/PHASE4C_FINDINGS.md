# Phase 4C — operating Nocturne Terminal end to end

November 9, 2026. Branch `feat/phase4c`. All work was driven through the installed
Windows app or its job store; **NO_TRADE**, no live data, no broker.

## A. Historical data (verified, not assumed)

- Ledger: 19 reservations / 19 completions, 0 uncertain; quoted spend **$41.30 of $125**
  (≈ $83.70 remaining); every raw chunk and normalized table matches its SHA-256.
- Coverage: NQ 5,567,303 and ES 5,742,093 one-minute contract bars,
  2010-06-07 → 2026-11-06; 4,230 sessions each; 67 contracts / 66 rolls, all rolls
  matching Databento symbology.
- Missing weekdays (56): 39 federal holidays, 11 Good Fridays, and **6 unexplained
  provider gaps** (2014-06-12, 06-13, 09-23, 09-24, 09-25, 12-31), identical for ES.
  No authenticated request was made in this phase; the gaps are documented, not filled.
- Order flow: only OHLCV purchased — trades/quotes/depth remain unavailable and disabled.

## B. ML performance (110 experiments through the app's job store)

Test years 2012–2026, annual walk-forward, 5-day embargo, Platt calibration, holdout
2023–2026 (**reused**: inspected by Phase 4 backtests). Verdicts: 47 ACCEPT_RESEARCH_ONLY,
44 INCONCLUSIVE, 19 REJECT. Full table: `reports/phase4c_ml.md`; also in the app
(Model Performance, top panel).

| Objective (NQ) | Best model | Dev AUC | Dev Brier vs baseline [Δ CI] | Holdout Δ | Verdict |
|---|---|---|---|---|---|
| Direction (next settle up) | logistic | 0.480 | 0.2525 vs 0.2472 [+0.0024, +0.0083] | +0.0025 | **REJECT** |
| Expansion (> 1.5 ATR) | logistic | 0.699 | 0.1116 vs 0.1215 [−0.0161, −0.0043] | −0.0055 | ACCEPT (research) |
| Compression (< 0.6 ATR) | LightGBM | 0.734 | 0.1285 vs 0.1378 [−0.0148, −0.0035] | −0.0121 | ACCEPT (research) |
| Trend day | LightGBM | 0.628 | 0.1582 vs 0.1611 [−0.0064, +0.0011] | −0.0009 | INCONCLUSIVE |
| Touch prior high | LightGBM | 0.836 | 0.1631 vs 0.2452 [−0.0906, −0.0730] | −0.0698 | ACCEPT (research) |
| Touch prior low | logistic | 0.785 | 0.1848 vs 0.2448 [−0.0692, −0.0499] | −0.0684 | ACCEPT (research) |
| Touch prior VWAP | LightGBM | 0.722 | 0.1893 vs 0.2195 [−0.0381, −0.0226] | −0.0350 | ACCEPT (research) |
| Range ≥ 1.0 ATR | LightGBM | 0.723 | 0.2076 vs 0.2419 [−0.0450, −0.0234] | −0.0300 | ACCEPT (research) |
| Range ≥ 350 pts | logistic | 0.788 | 0.1629 vs 0.2212 [−0.0995, −0.0209] | −0.0219 | ACCEPT (research) |
| Range ≥ 500 pts | logistic | 0.661 | 0.1596 vs 0.1630 [−0.0412, +0.0360] | −0.0219 | INCONCLUSIVE |
| Target-before-stop (8 geometries × 2 models) | — | 0.50–0.60 | none better with CI < 0 | — | 0 accepted |

ES mirrors NQ: direction REJECT (both models), expansion/compression/level touches ACCEPT.
Range quantiles: ES pinball improves on the trailing baseline (Δ −1.47 [−2.09, −0.89]) but
P80 coverage is only 0.67 (NQ 0.60) — **not calibrated**; do not read them as 80% bands.
Feature ablation: no family rescues direction; for expansion all families sit within each
other's intervals (volatility marginally best). `range_ge_1.5atr` duplicates `expansion`.

Target-before-stop economics (trade only when p > break-even): no geometry has a
positive development **and** holdout mean-R interval with ≥100 trades; filtered trade
counts are often tiny (e.g. 3–17 holdout trades).

## C. Strategy performance (authentic 5m, 2 contracts, cashflow-v2 costs)

| Instrument | Strategy | Period | Trades | Win % | PF | Net $ | Verdict |
|---|---|---|---|---|---|---|---|
| NQ | Opening range breakout | 2010–26 | 3,846 | 49.0 | 1.05 | +134,340 | REJECTED |
| NQ | VWAP pullback (re-run from UI) | 2010–26 | 3,607 | 50.5 | 0.91 | −153,541 | REJECTED |
| NQ | Value rejection | 2010–26 | 2,722 | 44.9 | 0.89 | −124,430 | REJECTED |
| ES | Opening range breakout | 2010–26 | 3,900 | 45.3 | 0.86 | −234,763 | REJECTED |
| ES | VWAP pullback | 2010–26 | 3,721 | 50.0 | 0.79 | −236,682 | REJECTED |
| ES | Value rejection | 2010–26 | 2,462 | 45.0 | 0.76 | −175,820 | REJECTED |
| NQ | Trend continuation (UI rule: close×VWAP, ADX>25, close>EMA21; 3 contracts, 1/2/3R) | 2019–26 | 738 | 48.0 | 0.89 | −100,820 | REJECTED |
| ES | Consolidation breakout (UI rule: close×BB-upper, ADX<20) | 2019–26 | 1,171 | 51.2 | 0.93 | −28,098 | REJECTED |

## D. Signal intelligence

69 candidates (strategies, UI rules, fixed geometries, ML filters) ranked by holdout then
development EV lower bound: **0 accepted** (`reports/phase4c_signals.md`; Signal Analytics).
Large NQ days: on sessions with ≥500-point ranges (283 since 2010), opening-range breakout
traded 272 times, won 65.1%, but captured **+35.6 points on average ≈ 4% of the day's range**;
VWAP pullback and value rejection captured ≈0 or negative. A large daily range is not a
profitable signal by itself.

## E. Prediction accuracy

Next-day direction: no validated model (all REJECT). Next-session regime and range
probabilities: validated research-only improvements over baselines (table above). Session
forecasts (Asia/London/NY/day) use the transparent trailing-quantile baseline and are
issued append-only from Prediction Center; forward outcomes accrue only as sessions
complete. The NDX shadow journal is unchanged (SHA-256 identical before/after all runs).

## F. Desktop app verification (real UI automation)

`desktop/electron/qa.cjs` drives the actual renderer (click by visible text, fill by field
label, follow real backend jobs). Evidence: `reports/phase4c_acceptance.json`.

| Run | Steps | Result | Covers |
|---|---|---|---|
| 1 — full workflow | 124 | 124 pass | A market data, B training (+cancel, +invalid config), C 16y VWAP backtest, D custom rules, E signals, F predictions, H latency, J API errors |
| 2 — after restart | 16 | 16 pass | I persistence: saved strategies/configs, experiment detail identical, 3,607-trade ledger |
| 3 — broken Python path | 2 | 2 pass | J startup failure shows an actionable error |

Parity: UI ticker = API close (27,107.50); chart bars 300/300 identical to the stored table;
17/17 levels; experiment detail = stored report (5/5 metrics); UI-launched 16y VWAP backtest
= Phase 4 scripted result exactly. Hard-killed worker → `FAILED / INTERRUPTED_PROCESS_RECOVERY`;
a worker orphaned by closing the app finishes and is recorded on the next start.

**Defects found and fixed:** Electron main crashed (unhandled spawn error) when Python
was missing — now an explicit error state; harness timeouts on error state; Model Studio
lacked authentic-data objectives; backtests lacked TP1/TP2/TP3 fill rates.

**Performance (measured):** 1m chart query 11.5 s / ~990 MB → **0.011 s / ~165 MB**
(memory-mapped column cache, exact parity); session grouping 3.4 s → 0.97 s per 1.15M bars
(identical output); 16-year VWAP backtest from the UI 113 s; 50k 1m bars API 0.85 s.

**Install:** `scripts/install_desktop.ps1` installs to
`%LOCALAPPDATA%\Programs\Nocturne Terminal` with Desktop and Start Menu shortcuts;
the installed copy was launched and all 10 views rendered with 0 errors.

## G. Engineering

483 Python tests pass (incl. native parity; licensed-data tests skip in CI); `tsc` and
`vite build` pass; portable exe + unpacked build produced. CI result recorded in the
commit report.
