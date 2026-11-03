# Phase 3E — validation, replay and forecasting checkpoint

Date: 2026-11-03. Branch: `feat/phase3e`. Decision: **NO_PROMOTION / NO_TRADE**.
Phase 3D release `8bb874b` is verified: local tree clean, GitHub Actions run
completed successfully. This checkpoint covers implemented Phase 3E work, not
completion of every external-data or independent-validation gate.

## 1. Data and provider foundation

The existing authorized CSV import remains operational and now includes explicit
raw-contract coverage and two-source comparison utilities. Databento and ALFRED
adapters were added with synthetic HTTP fixtures only. Neither downloaded real
data: `DATABENTO_API_KEY` and `FRED_API_KEY` are absent. Credential presence
inventory: `reports/phase3e_providers.json`.

Databento requests one explicit raw contract and one UTC day at a time. Raw
response bytes and normalized exports are checksummed; completed requests resume
without re-download; failed HTTP calls are not checkpointed. A raw contract is
required for production basis. One-minute bars are never upsampled. Five-minute
aggregation requires all five aligned minutes and never mixes contracts. Real
entitlements, roll reconciliation and ticks/depth/MBO remain **DATA_BLOCKED**.
No invented bid/ask, trades, volume-at-price or order flow was added.

ALFRED observations retain original date precision and vintage boundaries. They
are conservatively marked available the next UTC day, not at an invented release
time. The adapter cannot provide intraday schedules, consensus or news. Current
FRED context remains excluded from historical model features. Authorized
point-in-time consensus/news remains **DATA_BLOCKED**.

## 2. Direction and consolidation research

The fixed protocol is `PHASE3E_PROTOCOL.md`. It reuses the 10,344 NQ / 10,336 ES
two-hour rows, expanding 60/20/30-day folds and one-hour purging. Latest 20% of
days were not scored. Full row-level predictions:
`reports/phase3e_ablation_predictions.csv.gz`.

| Task | Model | Brier | ECE | Class/ranking detail |
|---|---|---:|---:|---|
| NQ direction | LightGBM | 0.483048 | 0.015122 | balanced accuracy 0.3636; BEAR recall 0.0009 |
| NQ direction | logistic | 0.488603 | 0.023965 | balanced accuracy 0.3416; BEAR recall 0.0026 |
| NQ consolidation | LightGBM | 0.157374 | 0.034094 | AUC 0.8365; recall 0.6248 |
| NQ consolidation | logistic | 0.169650 | — | AUC 0.8045 |
| ES direction | LightGBM | 0.484033 | 0.018423 | balanced accuracy 0.3523; BEAR recall 0.0076 |
| ES direction | logistic | 0.488195 | — | — |
| ES consolidation | LightGBM | 0.154928 | 0.022305 | AUC 0.8358; recall 0.6032 |
| ES consolidation | logistic | 0.165384 | — | AUC 0.8073 |

Frequency Brier is 0.521407 NQ / 0.525225 ES for direction and 0.229892 / 0.225232
for consolidation. Paired three-day block intervals versus frequency are negative
for all four LightGBM models (NQ direction [-0.0444, -0.0320], ES direction
[-0.0474, -0.0350], NQ consolidation [-0.0778, -0.0672], ES consolidation
[-0.0755, -0.0652]). That is aggregate probability-loss evidence, not directional
trading skill. Direction remains dominated by neutral predictions; it is not
useful for bull/bear decisions.

Feature ablation is descriptive and fixed before running. For NQ LightGBM
direction, removing clock worsens Brier to 0.497972, momentum to 0.484564,
volatility to 0.481806 and volume to 0.484292. For NQ LightGBM consolidation,
removing clock worsens to 0.177745, momentum to 0.161867, volatility to 0.174981,
while removing volume changes to 0.157116. ES patterns are similar. Thus volume
features show no reliable incremental value; clock and volatility/range groups
do. These are one dataset, not causal conclusions.

LightGBM is optional (`.[research]`, tested with 4.7.0). It offers no material
direction gain over logistic regression. CatBoost/XGBoost were not justified by
these results and were not added.

## 3. Large destinations and nested targets

The Phase 3D fixed-distance dataset was audited without retuning. Among 856
comparable nested pairs with identical signal, entry, stop, side, horizon and
slippage, there were **zero touch or target-first monotonicity violations**.
Unknown/censored outcomes were excluded, not imputed.

At 24 bars and one tick, ORB had 3 target-first events at 200 points and none at
350/500 (35 candidates each). VWAP had 3/1/1 (33 each); value 2/0/0 (22 each).
These counts are sparse. Many 78-bar RTH scenarios censor at session end. Timing
summaries are conditional on observed touches and are not survival probabilities.
The engine still exposes no production target-touch or target-before-stop model.

## 4. Two-hour range quantiles

Fixed protocol: `PHASE3E_RANGE_PROTOCOL.md`. LightGBM quantile models use
time-separated residual calibration and monotonic rearrangement. Results are total
future high-low range, not directional movement.

| Instrument | Quantile | Pinball loss | Coverage | Baseline coverage | Paired loss interval |
|---|---:|---:|---:|---:|---|
| NQ | 0.5 | 22.0267 | 0.4433 | 0.4246 | [-13.27, -10.47] |
| NQ | 0.8 | 20.8942 | 0.7418 | 0.7440 | [-13.60, -10.43] |
| NQ | 0.9 | 15.8868 | 0.8644 | 0.8643 | [-9.75, -7.02] |
| ES | 0.5 | 4.6017 | 0.4447 | 0.4390 | [-2.94, -2.25] |
| ES | 0.8 | 4.5564 | 0.7472 | 0.7559 | [-2.90, -2.22] |
| ES | 0.9 | 3.6033 | 0.8611 | 0.8761 | [-2.07, -1.52] |

Quantile loss improves in all six comparisons; coverage is approximately nominal,
with undercoverage at 0.8–0.9. This is not a conformal finite-sample guarantee.
Forecast contracts do not yet consume these models.

## 5. Historical replay

`forecast/replay.py` freezes only the available prefix, hashes it, and keeps
forecasts separate from outcome files. A future-mutation test proves forecast
identity is unchanged while evaluation changes. Replay writes to
`data/replay/phase3e/`, never the operational journal. It distinguishes
retrospective replay from live shadow/execution and performs no unvalidated
strategy/model inference.

Fixed development replay generated 12 frozen forecasts (six NQ, six ES) at 16:00
UTC every fifth development session. All 12 V1 horizons matured. The latest 20%
was excluded. These are very small samples and cannot establish calibration.
Range coverage was mixed. Across all V1 replay groups, NQ P80 covered 5/6 and ES
P80 covered 4/6; P50 covered 3/6 and 2/6. P90 covered 5/6 for both. Session
bundle NEW_YORK P80 covered 2/4 for both instruments. These counts are far too
small for calibration claims. ASIA bundle windows were `DATA_BLOCKED` due
incomplete five-minute cache coverage. This is honest missing data, not a
negative forecast.

## 6. Strategy research

`scripts/phase3e_strategies.py` evaluates existing ORB, VWAP and value families on
the first 80% of cached sessions only. This is development evidence, not a
portfolio: the three ledgers are independent, daily correlations are reported,
and a day without a signal contributes zero only to correlation. Regimes are
measured before entry from trailing bars. Costs use the existing engine: $2.50
commission per contract per side plus one tick slippage at the base case, stressed
at three and four ticks.

| Instrument | Strategy | Trades | Expectancy | Profit factor | Max DD | 4-tick net |
|---|---|---:|---:|---:|---:|---:|
| NQ | ORB | 34 | -$272.65 | 0.691 | $18,730 | -$10,800 |
| NQ | VWAP | 35 | +$130.74 | 1.298 | $3,932 | +$3,046 |
| NQ | value | 21 | +$62.38 | 1.140 | $4,160 | +$365 |
| ES | ORB | 36 | -$141.32 | 0.716 | $8,263 | -$9,119 |
| ES | VWAP | 34 | -$139.30 | 0.510 | $6,891 | -$8,693 |
| ES | value | 21 | +$127.74 | 1.717 | $3,118 | +$320 |

NQ VWAP expectancy has a 95% day-block interval of [-$150.69, +$445.36]; ES value
[-$247.65, +$404.57]. Both include zero. Every strategy has fewer than 40 trades
spanning roughly 2026-08-25 to 2026-10-20. Regime cells are smaller still and
unstable. NQ VWAP's apparent gains are
concentrated in STRESS (19 trades, +$7,995) and it loses in EXPANSION; this is
not a defensible regime rule. ORB's poor geometry remains visible. Daily
correlations are low to moderate (NQ ORB/VWAP 0.018; ES VWAP/value -0.046), but
shared underlying features still prevent treating agreement as independent
confirmation. No strategy is promoted or connected to execution.

Meta-labeling was not fitted: fewer than 40 trades per strategy and no independent
holdout cannot support another classifier. The fail-closed promotion checklist
requires that evidence first.


## 7. Promotion and integration

`ml/promotion.py` is a fail-closed checklist. It retains baseline improvement,
binary AUC ≥ 0.55, ECE ≤ 0.05, independent holdout, sample adequacy, provenance,
separate calibration, regime stability, class quality and rollback requirements.
Passing yields `ELIGIBLE_FOR_REVIEW`, never automatic activation.
All eight full-model Phase 3E assessments are `NO_PROMOTION`; missing independent
holdout and provenance are sufficient to block them regardless of Brier gains.

Forecast API/contracts are unchanged and compatible. Production probabilities
remain null where unvalidated. Session bundles remain research-only and `NO_TRADE`.
Frontend, TradingView automation and brokerage execution were not modified.

## 8. Verification and remaining dependencies

Native-enabled suite at this checkpoint: **184 passed**. CLI audit passes. TypeScript
was not changed. GitHub CI for the prior Phase 3D release passed; Phase 3E CI must
be checked after pushing.

Remaining external dependencies: licensed raw-contract one/five-minute history,
ticks/trades/depth/MBO, actual VX futures, authorized point-in-time release
schedules/consensus/news, verified exchange holiday and roll records, and a
genuinely independent future holdout. Remaining engineering: class-conditional
direction calibration, target survival/competing-risk validation on licensed
history, meta-labeling with independent samples, validated forecast fusion,
30m/1h/premarket/remainder-of-day contracts, and automated drift/rollback.
No profitability, live readiness, or completed monitoring is claimed.
