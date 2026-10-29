# Methodology

Nocturne is a **scenario engine**, not a price oracle. It turns a market snapshot into a
dated, testable call, then grades that call against the official settlement. The value is
in the discipline of writing the call down before the session and scoring it afterwards.

## 1. Data

| Input | Source | Frequency |
|---|---|---|
| Futures OHLC | Yahoo Finance chart API (`ES=F`, `NQ=F`, `GC=F`, `SI=F`) | Daily, 15 years |
| Session structure | Same endpoint, 5-minute and 15-minute bars | 5 days |
| Cross-asset | `^VIX`, `DX-Y.NYB`, `^TNX`, `^GSPC`, `^IXIC` | Daily |
| Yield curve | US Treasury daily par yield curve | Daily |
| Policy calendar | Federal Reserve FOMC calendar and statements | Event |
| Economic calendar | ForexFactory weekly JSON | Weekly |
| Earnings calendar | Nasdaq calendar API | Daily |

Yahoo's chart endpoint is public but undocumented and rate-limits aggressively. The
TypeScript pipeline fetches with a browser user-agent, spaces requests, and writes raw
dumps to `data/raw/<date>/` so a call can be rebuilt without hitting the network again.

## 2. Descriptive statistics

- **ATR(14):** mean of true range over 14 sessions. Used for the expected range and the
  one-ATR envelope around the last price.
- **Realized volatility:** standard deviation of 20 daily log returns, annualized by
  `sqrt(252)`. The one-sigma close move is `price * vol / sqrt(252)`.
- **Moving averages:** SMA(20), SMA(50), SMA(200). Used as trend context, not signals.
- **52-week high/low:** positioning context.
- **Base rates:** close-to-close return and `(high - low) / prior close` for all days,
  FOMC decision days, and the calendar date being traded.

Base rates are descriptive. A 22-observation FOMC sample and an 11-observation
calendar-date sample cannot establish an edge on their own; they are included because
they discipline the narrative, not because they predict the next session.

## 3. Levels

The published call records five levels per instrument:

- **R1 / S1:** the prior session's RTH high and low. These are the first places where
  breakout and breakdown orders sit.
- **R2 / S2:** the nearest meaningful swing level beyond R1/S1 (prior week's extreme,
  overnight extreme, or round number).
- **Pivot:** the prior session VWAP, a proxy for the average participant's cost basis.

`src/nocturne/levels.py` contains the transparent baseline used for candidate
generation: prior RTH and overnight extremes, VWAP, and a half-ATR envelope. The v0.1
levels in `call.json` were analyst-curated from that candidate set. Automating the
selection is a v0.2 item.

## 4. Scenarios and bands

Each call carries three named scenarios with probabilities that sum to 1.0. The
**expected close** is the probability-weighted midpoint of the scenario ranges. The
**bias label** is a separate judgment about the modal outcome.

The published bands are:

- **Predicted close:** the range the analyst expects the settlement to land in.
- **Expected range:** the high-low envelope, anchored on ATR and the event's historical
  range.
- **1σ close:** the published one-sigma move, blending 20-day realized vol with the
  event's typical range.

## 5. Scoring

A call is scored only after the session closes, using the official settlement:

- CME equity index futures: 16:00 ET.
- COMEX metals: 13:30 ET.

Metrics:

| Metric | Definition |
|---|---|
| Direction | Sign of (predicted midpoint − prior close) matches sign of (actual − prior close) |
| Close band | Actual settlement inside the predicted close range |
| Range | Actual high and low both inside the expected range |
| Range partial | Close inside, one extreme outside |
| R1/S1 break | Points by which the session ran past the level; positive = broken |
| Bucket | Published scenario containing the settlement, or `outside` |
| MAE | Mean absolute error of the settlement vs the predicted midpoint, in % |

## 6. Known limitations

1. **Single-axis scenarios.** v0.1 maps outcomes onto a hawkish/dovish line. A patient
   hold can lift equities while higher long yields pressure gold, which the 2026-10-28
   session demonstrated. v0.2 needs a second axis for real yields / growth.
2. **Gaps between buckets.** Three narrow named ranges do not tile the price space.
   Three of four settlements on 2026-10-28 landed outside every bucket.
3. **Small event samples.** The FOMC study covers 22 decisions. That is enough to
   describe the recent regime, not enough to estimate a stable probability.
4. **No order flow or options data.** The engine cannot see dealer gamma, positioning,
   or the options-implied move.
5. **Discretionary levels.** The published levels are curated. The code provides a
   baseline, not a replacement for judgment.
6. **Contract basis.** ES trades above cash S&P by roughly 40 points in this sample.
   Levels are futures levels; do not copy them onto SPX or SPY without adjusting.

## 7. Reproducibility

Every call is a committed JSON artifact with a data timestamp, a source list, and the
exact numbers used. `python -m nocturne build --date <call_id>` regenerates the report,
charts, and dashboard from that artifact. `python scripts/run_study.py` rebuilds the
15-year base rates from the committed CSVs. `python -m pytest` checks the scoring math
and the known 2026-10-28 result.
