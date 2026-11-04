# Phase 3G — multi-decade history, patterns and level reactions

Date: 2026-11-04. Branch: `feat/phase3g`. Decision: **NO_PROMOTION / NO_TRADE**.
All experiments use development data; the last years of each dataset are reserved
and unscored. Phase 3F was verified at `41be740` before new work.

## 1. Historical data actually acquired

Long daily history via the public Yahoo chart endpoint, stored with raw JSON,
normalized CSV and SHA-256 manifests:

| Symbol | Kind | Rows | First | Span |
|---|---|---|---:|---:|
| ^GSPC | index | 24,828 | 1927-12-30 | 99 y |
| ^NDX | index | 10,353 | 1985-10-01 | 41 y |
| ^VIX | volatility index (spot proxy) | 9,280 | 1990-01-02 | 37 y |
| QQQ | ETF | 6,956 | 1999-03-10 | 27 y |
| SPY | ETF | 8,498 | 1993-01-29 | 33 y |
| ^TNX | 10-year yield index | 16,198 | 1962-01-02 | 64 y |
| TLT | ETF | 6,105 | 2002-07-30 | 24 y |
| NQ=F | continuous futures proxy | 6,573 | 2000-09-18 | 26 y |
| ES=F | continuous futures proxy | 6,587 | 2000-09-18 | 26 y |

Official BLS API verified with a bounded 2024–2025 snapshot: 96 monthly rows
across CPI-U, PPI final demand, nonfarm payrolls and unemployment (94 non-null).
FRED and ALFRED adapters from earlier phases are reused.

Important limits: index levels are not tradable; ETFs are not futures; the
continuous futures proxies have no verified roll mapping; Yahoo is unofficial and
rate-limited; daily bars are marked available at the next UTC midnight, which is
conservative but not the exact close time. No 40-year NQ intraday history is
claimed, because it does not exist and no licensed feed was available.

### Cross-provider checks

| Pair | Overlap | Return correlation |
|---|---:|---:|
| ^NDX vs QQQ | 6,955 | 0.9803 |
| ^GSPC vs SPY | 8,497 | 0.9835 |
| NQ=F vs cached NQ daily | 3,774 | 0.9999 |
| NQ=F vs ES=F | 6,565 | 0.8672 |

^TNX vs FRED DGS10 overlap 10,201 days with mean absolute difference 0.0102
percentage points, consistent with timing and rounding. The cached NQ futures
proxy reproduces the independent NQ daily file almost exactly, which validates the
adapter rather than any trading edge.

## 2. Seasonality (3G.3)

Year-block bootstrap intervals (whole years resampled) and Benjamini–Hochberg
control within each calendar family. Effect sizes are small even where intervals
exclude zero:

| Effect | ^GSPC mean | 95% year-block interval |
|---|---:|---|
| Monday | −0.062% | [−0.112%, −0.017%] |
| Tuesday | +0.046% | [+0.014%, +0.080%] |
| Turn of month | +0.101% | [+0.076%, +0.126%] |
| Non-turn | +0.003% | [−0.013%, +0.020%] |

^NDX: Wednesday +0.162% [0.056%, 0.256%]; turn of month +0.120% [0.060%, 0.175%].
With 99 years, tiny differences become statistically significant; that is not the
same as exploitable edge. The daily direction model that included these seasonal
features did not improve (AUC 0.5006 versus 0.5077 price-only), so they are
descriptive context, not model inputs.

## 3. Direction across decades (3G.4 / 3G.6)

Expanding annual walk-forward on ^NDX, 1990–2023, two-year calibration block,
five-day embargo, 8,565 out-of-sample rows. 2024–2026 reserved and unscored.

| Variant | Brier | Frequency Brier | AUC |
|---|---:|---:|---:|
| Price/volatility only | 0.2490 | 0.2481 | 0.5077 |
| + volatility context | 0.2491 | 0.2481 | 0.5059 |
| + rates context | 0.2490 | 0.2481 | 0.5075 |
| + cross-market | 0.2491 | 0.2481 | 0.5060 |
| + seasonality | 0.2492 | 0.2481 | 0.5006 |
| All groups | 0.2495 | 0.2481 | 0.4979 |

Every variant is worse than the base rate on Brier. Adding VIX, Treasury yields,
S&P relative strength or calendar features does not produce directional skill.
Worse, the apparent 1990s edge decays: price-only AUC by decade is 0.544 (1990s),
0.494 (2000s), 0.482 (2010s) and 0.459 (2020s). This is temporal dataset shift, not
a stable signal.

This independently reproduces the Phase 3F conclusion on a much longer sample:
daily direction is close to unpredictable with public price and macro context.

## 4. Historical analogues (3G.2)

k-nearest-neighbour search on eight scale-free window features (momentum, vol,
efficiency, MA distance, drawdown, volume and range z-scores), 5-day embargo,
expanding history, 7,300 out-of-sample days from 1995–2023.

| k | Brier | Frequency Brier | AUC |
|---:|---:|---:|---:|
| 50 | 0.2517 | 0.2478 | 0.5144 |
| 100 | 0.2497 | 0.2478 | 0.5087 |
| 250 | 0.2486 | 0.2478 | 0.5081 |

Analogues do not beat the base rate and their ranking skill is negligible. A
visually similar historical window is not evidence of a repeat. The engine is
retained as a research tool, not a forecast input.

## 5. Price-level reaction database (3G.5)

40 development sessions per instrument, levels built one hour after the RTH open,
48-bar forward horizon, 927 NQ and 571 ES level-session observations.

Touch rates by distance from the as-of price:

| Distance | NQ touch | ES touch |
|---|---:|---:|
| < 1 ATR | 89.0% | 88.4% |
| 1–2 ATR | 60.4% | 70.8% |
| 2–4 ATR | 29.3% | 38.0% |
| > 4 ATR | 4.2% | 4.4% |

Conditional on a touch (NQ / ES): acceptance 70.1% / 69.2%, break-through 58.1% /
66.9%, rejection 40.4% / 33.1%, and target-before-stop with a 2 ATR target and
1 ATR stop 20.8% / 24.3%. These are distinct events with Wilson intervals in the
report; they are not interchangeable probabilities.

The database is descriptive and correlated within sessions. It is not wired into
production forecasts, and the 2 ATR / 1 ATR barrier geometry is a research
assumption, not a validated strategy.

## 6. Provider registry (3G addition)

`adapters/registry.py` records access class, credential variable, implementation
and verification status for Yahoo, FRED, BLS, Databento, Nasdaq Data Link and
Bloomberg. Status vocabulary distinguishes `AVAILABLE`, `AVAILABLE_NO_KEY`,
`BLOCKED`, `ENTITLEMENT_UNVERIFIED` and `NOT_IMPLEMENTED`. Credentials are read
from environment variables only and never logged. Databento and Bloomberg remain
paid dependencies; Nasdaq Data Link is not implemented because per-dataset rights
must be verified before ingestion.

## 7. What this phase establishes

- Decades of legitimate free daily history are now available with provenance and
  cross-source validation.
- Seasonality exists but is economically small and does not improve direction.
- Historical analogues do not add directional value.
- Level-touch probabilities are strongly distance-dependent and can be measured
  honestly with explicit event definitions.
- Next-day direction remains research-only; the 1990s edge decayed.

Not established: any tradable edge, any validated probability, any intraday
multi-year futures history. Promotion decisions remain fail-closed.
