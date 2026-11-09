# Phase 3V — zero-cost futures research

November 9, 2026 UTC; branch `feat/phase3v`, base `c0cd231`.
**Operator constraint: no spending.** No Databento time series was requested.
**NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE.**

## A. Databento: free preflight only

The key is stored only in ignored `data/security/databento.key` (user-only ACL)
and loaded into process environments; a repository scan found it in no tracked
or report file. Free metadata calls (`reports/phase3v_preflight.json`):

- Authentication **OK**; `GLBX.MDP3` listed, 2010-06-06 → 2026-11-08, all schemas
  offered (ohlcv-1m, trades, tbbo, mbp-1/10, mbo from 2017-05-21, definition…).
- Symbology: `NQ.v.0` / `ES.v.0` resolve with 67 front-month intervals each
  (66 volume rolls), no partial or missing symbols.
- Provider quotes (not purchased): 2-week NQ+ES 1m pilot **$0.0999**; 1m
  2021–2026 **$15.12** (221 MiB, 4.14M rows); 1m 2010–2020 **$26.17** (383 MiB,
  7.17M rows); definitions 2010–2026 $0.0085; trades 1 month $26.55; tbbo
  1 month $44.26; mbp-1 1 week $19.08; trades 2021–2026 $1,527.80.
- Account credit balance is not exposed by the historical API.
- **Defect fixed:** the existing preflight read `range_by_schema`, but the API
  now returns `schema`; every pilot preflight would have failed with
  `PILOT_OUTSIDE_ENTITLED_SCHEMA_RANGE`. Regression test added.

Status: **FUTURES_DATA_BLOCKED by operator policy ($0)**. No quote was approved.

## Free futures data acquired

`collect_yahoo_futures` (existing collector, 2 s spacing, revision ledger):

| Dataset | Rows | Coverage |
|---|---|---|
| NQ / ES daily | 6,600 each | 2000-09-18 → 2026-11-06 |
| NQ / ES 60m | 13,678 / 13,683 | 2024-06-17 → 2026-11-09 |
| NQ / ES 5m | 13,443 / 13,444 | 2026-08-30 → 2026-11-09 |
| NQ / ES 1m | 27,229 each | 2026-10-12 → 2026-11-09 |

Total 154,506 rows, 5.8 MB. Validation found and fixed two collector defects:
Yahoo `range=max` silently returns monthly bars (now explicit epoch bounds),
and the latest 1m/5m bar is a live partial bar with an unaligned timestamp
(now dropped). Bars with missing OHLC are dropped, never imputed.

Session check against hourly bars (569 sessions): the daily bar is the Globex
session (prior 18:00 → 17:00 ET); highs match within 0.5 pt 94.4%, lows 93.0%,
opens 84.0%; the daily close matches only 12.5% because Yahoo's daily close
behaves like settlement, so labels use high/low and settle-to-settle changes.
Roll dates come from free Databento symbology (66 per root) and are committed
as derived dates only (`data/history/free/rolls/`); 462 sessions within ±3
trading days of a roll are excluded from labels. Return features crossing a
roll still contain the unadjusted contract basis (documented limitation).

## B. Strategy backtests (existing engine and strategies)

5m RTH, 49 sessions (2026-08-31 → 11-06), development / validation / holdout
= 50/25/25 of sessions, cashflow-v2 costs, stop-first on same-bar touches,
2-contract positions (1 at TP1, 1 at TP2). Ledger: 217 trades,
`data/studies/phase3v/strategy_trades.csv`.

| Root | Strategy | Trades | Win rate | PF | Expectancy $/position | Net $ | Max DD $ | Verdict |
|---|---|---|---|---|---|---|---|---|
| NQ | Opening range breakout | 42 | 0.500 | 1.31 | 436.67 | 18,340 | 23,330 | INSUFFICIENT_SAMPLE |
| NQ | VWAP pullback | 41 | 0.634 | 1.19 | 222.77 | 9,133 | 17,597 | INSUFFICIENT_SAMPLE |
| NQ | Value rejection | 24 | 0.375 | 0.47 | −780.42 | −18,730 | 22,840 | INSUFFICIENT_SAMPLE |
| ES | Opening range breakout | 44 | 0.409 | 1.14 | 110.45 | 4,860 | 10,275 | INSUFFICIENT_SAMPLE |
| ES | VWAP pullback | 40 | 0.450 | 0.62 | −235.00 | −9,400 | 14,455 | INSUFFICIENT_SAMPLE |
| ES | Value rejection | 26 | 0.615 | 1.40 | 180.38 | 4,690 | 6,710 | INSUFFICIENT_SAMPLE |

Instability example: NQ opening range is −$981/position in development
[−2,198, +236] but +$1,890 in holdout [−1,115, +4,895]. No split's expectancy
CI excludes zero for any strategy. Slippage 0.5 → 2 ticks reduces NQ ORB
holdout expectancy by $40/position. Re-running 72 trades on 1m bars changed
**0** outcomes, so stop-first tie handling did not drive these results.
Per-year results are impossible (one quarter of 5m history).

## C. Machine learning (daily, annual walk-forward 2008–2026)

Embargo 5 days, Platt calibration on the last 250 training rows, development
2008–2023, previously inspected 2024–2026 scored once, trailing-250-session
frequency baselines. Features: 9 price features plus the 14 Phase 3U PIT
features in four families. Full tables: `reports/phase3v_research.md`.

- **Direction (next settle up):** NQ and ES, every configuration **REJECT**:
  significantly worse than the frequency baseline (e.g. NQ price logit Brier
  0.2550 vs 0.2488, Δ +0.0062 [+0.0039, +0.0083]; AUC 0.48–0.51).
- **Compression (next range < 0.6 × ATR20):** only LightGBM with all features
  passes — NQ Δ −0.0073 [−0.0119, −0.0022], holdout −0.0150, AUC 0.719/0.768;
  ES Δ −0.0115 [−0.0182, −0.0041], holdout −0.0194. **ACCEPT_RESEARCH_ONLY.**
- **Large range (next session ≥ N points):** logistic models beat the trailing
  frequency for NQ 100/200/350 and ES 25/50/100 points (e.g. NQ ≥350 with
  volatility features Δ −0.0510 [−0.0788, −0.0265], holdout −0.0456, AUC
  0.785/0.791). NQ ≥500 and ES ≥150 are INCONCLUSIVE. Caveat: point thresholds
  are level-dependent (NQ rose from ~1,500 to ~26,000); by 2024–26 a 100-point
  range occurs almost daily, so holdout gains there are trivial. These models
  mainly capture volatility persistence.
- **Feature families vs price-only (matched sessions):** volatility (VIX/VXN)
  helps NQ ≥350 in both eras (dev −0.0145 [−0.0281, −0.0047], holdout −0.0104)
  and NQ ≥100; rates/credit and positioning mostly **hurt** (e.g. positioning on
  NQ ≥350 +0.0088 [+0.0033, +0.0162]); filings show no detectable increment.
- **Large-move frequencies by regime** (Wilson CIs, model-free): 2024–26 NQ
  P(range ≥ 500) = 0.082 when VIX < 15, 0.324 at 15–25, 0.657 above 25.

## D. Target-before-stop (hourly NQ, 544 sessions)

Entry at the 15:00 UTC hourly open, five geometries (100/100 … 500/250), long
and short, 6h and 24h horizons, 0.75-point costs; 10,840 path records. Holdout
from 2025-11-21. Same-bar ties: resolved with 1m/5m bars when available,
otherwise stop-first (23 ties total). **All 20 cells rejected**: no development
net-EV CI excludes zero (e.g. long 200/100 6h: dev −4.1 [−15.7, +7.4] points,
holdout +11.3 [−5.2, +27.8]).

## E. Signal ranking

`reports/phase3v_signal_ranking.json`: 26 candidates ranked by holdout and
development EV lower bounds; **0 accepted**. Reasons: insufficient sample
(strategies) or development CI including zero (target-before-stop). No
confidence score or recommended entry is produced.

## F. Forward testing and engineering

The NDX shadow is unchanged: 4 issued, 2 matured, 2 audit-blocked, 0 missed.
Historical walk-forward results are retrospective, not forward tests. The
scheduled `FREE_DATA_COLLECTION` now includes Yahoo futures. The Databento DAG
branch remains BLOCKED with zero licensed receipts. 451 tests pass locally
with native parity. Research reruns are byte-identical, including from the
committed roll calendar alone.

## G. To unlock authentic futures research

If the Databento portal shows free credits and no card would be charged,
the full 1m NQ+ES history (~$41.30 quoted) would fit, and only with explicit
approval. Otherwise free data cannot provide raw-contract trades, bid/ask,
aggressor flags or depth; those analyses remain `FUTURES_DATA_BLOCKED`.
