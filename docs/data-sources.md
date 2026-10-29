# Data sources

All timestamps are US Eastern. The 2026-10-27 call used the snapshot at **20:51 ET**.

| Source | Endpoint / page | Used for | Accessed |
|---|---|---|---|
| Yahoo Finance chart API | `query2.finance.yahoo.com/v8/finance/chart/{symbol}` | Daily OHLC, 5m/15m session structure, quotes | 2026-10-27 20:51 ET |
| US Treasury | Daily par yield curve CSV | 1M–30Y yields, curve shape | 2026-10-27 |
| Federal Reserve | FOMC calendar and statement pages | Meeting dates, policy rate, statement language | 2026-10-27 / 2026-10-28 |
| ForexFactory | `nfs.faireconomy.media/ff_calendar_thisweek.json` | Event calendar, consensus, previous | 2026-10-27 |
| Nasdaq | `api.nasdaq.com/api/calendar/earnings` | Earnings dates and session (pre/post) | 2026-10-27 |
| Motley Fool | Market midday column | Intraday context and index levels | 2026-10-27 |

## Symbols

| Code | Yahoo symbol | Contract | Settlement |
|---|---|---|---|
| ES | `ES=F` | E-mini S&P 500, Dec 2026 | 16:00 ET |
| NQ | `NQ=F` | E-mini Nasdaq-100, Dec 2026 | 16:00 ET |
| GC | `GC=F` | Gold, Dec 2026 | 13:30 ET |
| SI | `SI=F` | Silver, Dec 2026 | 13:30 ET |
| VIX | `^VIX` | Cboe volatility index | 16:15 ET |
| DXY | `DX-Y.NYB` | US dollar index | 17:00 ET |
| 10Y | `^TNX` | 10-year yield × 10 | 15:00 ET |

## Data-quality notes

- **Yahoo is not an exchange feed.** It is free, delayed in places, and occasionally
  prints bad bars. The 2026-10-28 silver daily bar, for example, prints `high = open`
  (53.925) while 5-minute data shows an intraday high near 54.40. The scorecard flags
  this rather than silently fixing it.
- **Futures daily bars are session-based.** Yahoo aligns futures days to midnight ET,
  which means the "daily close" can differ from the 16:00 ET settlement. The scorecard
  uses the official settlement and reports the 16:00 mark separately.
- **COMEX metals settle at 13:30 ET.** Gold and silver can move materially between the
  settlement and the equity close. On 2026-10-28, gold settled at 4,051.6 and traded
  4,089.1 at 16:00. Scoring on the settlement is the conservative, exchange-defined
  choice.
- **Contract rolls.** The Dec 2026 contracts are front-month in this sample. Continuous
  back-adjusted series are not used; the study uses the front contract as printed by
  Yahoo, which can create small roll gaps.

## Reproducing a snapshot

```bash
cd ts
npm install
npm run fetch -- 2026-10-27
```

This writes `data/raw/2026-10-27/*.json`. The committed `data/raw/history_1mo.json` is
the small history file used by the chart; per-run dumps are gitignored.
