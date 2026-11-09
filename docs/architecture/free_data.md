# Free-data pipeline (Phase 3U)

```
official APIs / permitted feeds
      │  PoliteClient: declared UA, per-domain spacing, retry + Retry-After,
      │  byte budget, robots.txt enforced for crawl access
      ▼
Archive (data/history/free | data/research/free)
      raw/<sha256>.gz            immutable source bytes
      normalized/<sha256>.csv    typed rows + available_at + pit_eligible
      manifest.jsonl             NEW / UNCHANGED / UPDATED, appended,
                                 removed and revised row counts
      ▼
free_data_experiment.free_features
      merge_asof(cutoff = feature_available_at, backward, staleness tolerance)
      pit_eligible=false rows rejected
      ▼
walk-forward models (logistic direction, LightGBM range quantiles)
      ▼
reports/phase3u_backtest.{json,md}, data/studies/phase3u/<fingerprint>/
```

## Availability rules

| Source | `available_at` |
|---|---|
| VIX, VXN, overnight RRP | observation date 22:00 UTC |
| H.15 yields/spreads, EFFR, Baa spread | +1 business day 22:00 UTC |
| Fed H.4.1 total assets | +2 business days |
| Broad dollar index (H.10) | +7 business days |
| CFTC TFF | report Tuesday + 6 days 21:00 UTC; 2013, 2018–19 and 2025 shutdown backlogs use late fixed dates |
| SEC filings | EDGAR acceptance time (US/Eastern → UTC) |
| Treasury DTS | +2 business days (context only) |
| CPI, UNRATE, NFCI, USREC, BLS, Fed RSS, GDELT | not PIT-eligible |

## Orchestration

`scripts/phase3m_research.py` enqueues `FREE_DATA_COLLECTION` (daily bucket)
then `FREE_DATA_EXPERIMENT`, which reuses the stored result when data, code and
protocol are unchanged. Both are research-lane only and cannot touch shadow
inference. A collection job succeeds when at least one source is collected and
lists every failed source; detected revisions are returned in the job result.
