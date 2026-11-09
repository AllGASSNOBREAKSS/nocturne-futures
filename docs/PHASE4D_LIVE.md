# Phase 4D — live session levels, R:R backtests, news

November 9, 2026. Branch `feat/live-confluence`. Research only, **NO_TRADE**, no broker.

## What the app does now

**Predict → Today (live)** (default screen)
- Free Yahoo intraday bars (≈10 min delayed; not an exchange feed), refreshed every 60 s.
- Asia (18:00–03:00 ET), London (03:00–09:30) and New York (09:30–16:00) open/high/low,
  15/30-minute opening ranges, initial balance, VWAP with ±1σ/±2σ bands.
- 40 candidate levels (prior day, value area, sessions, VWAP bands, pivots, 5/20-day
  extremes, daily EMA/SMA, out-of-sample ML projections) each with the probability of
  trading before 16:00 ET, re-scored at 03:00, 09:30, 10:30, 12:00 and 14:00 ET; levels
  already traded are marked HIT with the time.
- Take-profit list: nearest open levels on each side with ≥25% probability.
- Market state: daily trend label, intraday VWAP/opening-range state, volatility regime,
  each shown with how often that state was historically followed by a higher close.
- Chart: own chart with the levels, or the TradingView embed (index CFD: TradingView's free
  widget does not license CME futures).
- News: worldwide RSS headlines (CNBC, MarketWatch, Federal Reserve, BBC, Google News) with
  category, tone and the NQ/ES move since publication; this week's economic calendar with the
  measured reaction on comparable past days.

**Backtest** — contracts 1–50, reward:risk 1:0.5–1:20 (any mix), date range; one-click
backtest per strategy, or **Backtest everything**: 3 algos, 12 indicator rules and 6 model
strategies × every chosen R:R, ranked by win rate or profit, each with a two-half verdict.

## Measured results (authentic Databento bars, out-of-sample)

### Level touch model (walk-forward annual refits, 3,564 sessions × 5 cutoffs)

| | NQ | ES |
|---|---|---|
| AUC (model) | 0.893 | 0.888 |
| AUC (distance only) | 0.871 | 0.866 |
| Confluence features add | 0.000 AUC | 0.000 AUC |
| Levels ≥¼ ATR away rated >80%: hit rate | 61.6% (1,013) | 65.8% (606) |
| Levels rated 90–95%: hit rate / median distance | 95.5% / 0.02 ATR | 95.2% / 0.02 ATR |

Stacking levels ("confluence") does not add information beyond distance from price: stacked
levels hit more often only because they tend to be closer. Near-certain touches exist, but
they are levels price is already sitting on — useless as targets.

### Direction
- Rest-of-day: at 10:30 ET, closes finished higher 57% when price was above VWAP vs 52% below
  (base 55%). Weak, trend-following.
- Daily trend label → next day: Uptrend/Downtrend/Range all within ±2 pts of the 55.5% base.
- Next-session ML direction remains REJECTED (Phase 4C).

### News / scheduled events (NQ, 2010–2026)
| Event | Days | NY range vs normal | Big-day odds | Closed up |
|---|---|---|---|---|
| FOMC decision (official Fed calendar) | 125 | 1.25× | 11.2% vs 6.3% | 47% vs 54% |
| Payrolls (08:30 surge, first Friday) | 180 | 1.09× | 7.2% | 53% |
| Other 08:30 data (CPI/PPI/retail…) | 588 | 1.04× | 6.1% | 55% |

Events raise volatility; none gives a reliable direction. Headline tone is shown but was not
validated as predictive (no free historical headline archive is reachable from this host;
GDELT rate-limits it).

### Backtest everything (NQ, 2019–2026, 1 contract, $2.50 + 1 tick)
Highest win rate ≥100 trades: VWAP + ORB trend (10:30) at 1:0.5 — 67.8% wins, +$24,323.
Highest profit: same strategy at 1:3 — 45.3% wins, +$148,919, PF 1.22. EMA 9/21 cross up at
1:0.5 wins 66% and **loses** $27,040. No combination is profitable with a positive 95%
interval in both halves of the period. Win rate is controlled by the R:R you choose, not by
the signal: there is no 99%-win configuration that makes money.

## Verification
- 31/31 UI steps through the real app (`desktop/qa/scenario-live.json`): live screen NQ/ES,
  TradingView, next-session view, 3-contract sweep, single backtest report; TP prices on
  screen = API (5/5); 3-contract dollars = 3 × 1-contract dollars.
- Unit tests: no-lookahead levels, whole-contract scale-out, R:R rewrite, out-of-sample model
  signals, offline news parsing, calibration (`tests/test_live_confluence.py`).
