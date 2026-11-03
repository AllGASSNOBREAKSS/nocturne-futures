# Phase 3D — historical expansion and validation checkpoint

Date: 2026-11-03. Branch: `feat/phase3d`. Decision: **NO_PROMOTION**.
This is a verified engineering/research milestone, not completion of all Phase 3D gates.

## History actually acquired

- Yahoo public/unofficial NQ: 11,433 hourly bars; ES: 11,435. Both span
  2024-11-03 through 2026-11-03. No contract identifiers or verified roll mapping.
  Zero-volume rows: NQ 415, ES 421. Elapsed gaps include exchange closures;
  they are not a count of missing exchange bars.
- Official FRED DGS10/DGS2: 10,215 nonmissing observations each; DFF: 14,916;
  CPIAUCSL/UNRATE: 488 each. Coverage begins in 1986. Raw and normalized
  SHA-256 manifests are retained. These are latest vintages, not historical
  publication-time records, and are ineligible for historical features.
- Existing daily futures/index-proxy history covers about 15 years. Existing
  five-minute futures history remains about 60 days. No licensed expansion of
  five-minute futures, tick, depth, MBO or VX was obtained.
- Inventory: `reports/phase3d_history_inventory.json`; acquisition details:
  `phase3d_hourly_inventory.json` and `phase3d_macro_inventory.json`.

The authorized-export ingester preserves raw bytes, validates OHLCV and timestamps,
deduplicates exact rows, rejects conflicting revisions, checks hashes on resume,
and separates raw/normalized/manifests. It does not infer rolls, repair missing
bars, or grant provider entitlements. CSV is retained without a Parquet dependency.
Network sources use explicit request timeouts. Native authenticated futures API
adapters and provider entitlement discovery remain unfinished; no supported key
was present in this session. Export import is operational.

## Leakage and event-definition corrections

Complete five-minute timestamp coverage is now required for session labels;
elapsed wall time alone is insufficient. Dataset size falls from 147 to 86 rows
across 49 days. Future labels use the next trading day, not the next available
sample, and carry feature-availability and label-end timestamps.

Validation purges entire day/signal groups whose inclusive label intervals reach
the next partition, with a one-hour embargo. Expanding and rolling folds have
separate calibration samples. The last 20% of days are quarantined and unscored.
Previously examined dates cannot be called a pristine final holdout.

The original same-session contraction label is preserved. A fixed sqrt-duration
comparison and volatility-scaled neutral band are descriptive experiments, not
threshold searches. The exact protocol is hashed in the session report.

Target datasets now use exactly the configured number of bars; truncated windows
are censored, gap-beyond-target entries are skipped, and ambiguous labels are
not forced to false. Excursions are full observed-horizon statistics, not
executable exit profits. Rebuilt ORB: 115 timeout, 12 censored, 3 stop-first,
2 target-first; VWAP: 33 stop-first, 32 target-first, 19 timeout; value: 14
stop-first, 10 target-first, 4 timeout. Target rows share signals and are dependent.

## Results

All exact metrics, fold date ranges, class counts, raw/calibrated comparisons,
per-session/efficiency strata and predictions are committed under `reports/phase3d*`.
Intervals use 1,000 moving-block replicates of three consecutive day groups.
They describe this evaluation sample, not guaranteed future performance.

Complete-session expanding direction Brier: frequency 0.578842, GBM 0.561142,
logistic 0.664988. Consolidation: frequency 0.211697, logistic 0.204805,
GBM 0.254672. Rolling results are mixed; sample size remains inadequate.

Separate two-hour datasets contain 10,344 NQ and 10,336 ES observations across
574 UTC days. Labels require two contiguous positive-volume hourly bars.
Expanding out-of-fold evaluation has 6,786 NQ / 6,777 ES rows over 378 day groups.
The latest 20% are not scored.

- NQ direction GBM Brier 0.485373 versus frequency 0.521407; ECE 0.021315.
  Paired Brier difference 95% block interval: [-0.042428, -0.029191].
- ES direction GBM Brier 0.486192 versus frequency 0.525225; ECE 0.017979.
  Paired difference interval: [-0.045768, -0.032508].
- NQ consolidation GBM Brier 0.157294 versus 0.229892; ECE 0.029537.
  Paired difference interval: [-0.077887, -0.067101].
- ES consolidation GBM Brier 0.154749 versus 0.225232; ECE 0.025968.
  Paired difference interval: [-0.075879, -0.065159].

Rolling hourly GBM also improves Brier over frequency. However, direction balanced
accuracy is only 0.3601 NQ / 0.3517 ES; neutral dominates and bearish recall is
0.0009 / 0.0051. Better aggregate probability loss is not useful directional
trading accuracy. Consolidation predicts range contraction relative to recent
range; it does not establish breakout timing, direction or profitability.

## Forecast and macro truth boundaries

Forecast V1 explicitly uses the next 78 observed five-minute bars. Session bundles
use complete same-session empirical ranges with a minimum 20 observations; sparse
sessions return null. Immediate rolling-bar touch estimates are no longer
misrepresented as delayed next-session touch probabilities. Consolidation and
target-before-stop production probabilities remain null. No fusion model is enabled.

Evaluation no longer scores a partial V1 horizon or an incomplete bundle window.
Current journal: two V1 entries, neither matured, and two bundles. Old journal
entries remain intact; corrected builders use distinct identifiers.

Economic schedules require their own availability timestamp. Future release values
and consensus are redacted before their availability. Event revisions are stored
as distinct vintages. The sample calendar cannot establish an authorized calendar;
critical-day output therefore reports unavailable data. FRED downloads supply
context, not live event consensus or ALFRED vintage integration.

## Verification and remaining work

Baseline reproduced: 154 passed, one native skip. Updated: 169 passed, one skip;
170 passed with native enabled. TypeScript typecheck and CLI audit pass. No C++
changes. Remote CI is checked separately after pushing; local success is not a
claim that remote CI passed.

Still required: authorized contract-level intraday history, explicit roll and
holiday reconciliation, point-in-time release/consensus/news feeds, a genuinely
fresh final period, LightGBM comparison, horizon-specific target calibration,
200/350/500-point barrier and cost studies, survival/competing risks, validated
fusion, replay monitoring/drift/rollback, and 30m/1h/premarket/remainder-of-day
contracts. No claims of completed monitoring, profitable strategy, or promotion.
