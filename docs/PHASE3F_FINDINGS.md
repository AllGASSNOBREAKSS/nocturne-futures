# Phase 3F — direction diagnostics, range calibration and target survival

Date: 2026-11-03. Branch: `feat/phase3f`. Decision: **NO_PROMOTION / NO_TRADE**.
All results are retrospective development evidence. The latest 20% of days in each
dataset remains unscored.

## 1. Phase 3E verification

`31ed955` is present with a clean tree. The Phase 3E suite (184 tests) and the
reported CI runs were confirmed before new work. Phase 3F rebuilds additive
datasets and verifies that every Phase 3D/3E label is byte-identical
(`reports/phase3f_dataset.json`).

## 2. Directional model diagnostics (3F.1)

### The label is not the problem

The neutral band is `0.5 × ATR(24 hourly true ranges) × √2`. On development rows
the median absolute two-hour move is 0.68 of that threshold and the 64th
percentile is 0.98, so the band sits almost exactly at the median absolute move.
Neutral is 64.6% NQ / 64.2% ES — wide, but not arbitrarily so. Hour-by-hour
neutral shares and monthly drift are committed in `reports/phase3f_direction.json`.

### The failure is directional, not aggregate

| Model | Brier | Material AUC | Bull-vs-bear AUC \| material | ECE |
|---|---:|---:|---:|---:|
| NQ LightGBM | 0.4830 | 0.699 | 0.534 | 0.0151 |
| NQ logistic | 0.4886 | 0.685 | 0.526 | 0.0240 |
| ES LightGBM | 0.4840 | 0.710 | 0.523 | 0.0184 |
| ES logistic | 0.4882 | 0.697 | 0.523 | 0.0210 |

The model detects *whether* a material move is likely (AUC ≈ 0.70) and has almost
no ability to say *which direction* (AUC ≈ 0.52–0.53). Mean predicted bear
probability is 0.18 for true bear rows, 0.14 for true neutral and 0.19 for true
bull: the three classes receive nearly the same distribution. That is why bear
recall is 0.001 while aggregate Brier improves — the gain is entirely from
activity detection.

### Alternative formulations did not help

| Variant | NQ Brier | ES Brier |
|---|---:|---:|
| Three-class, time-separated calibration | 0.4830 | 0.4840 |
| Three-class, vector-scaled probabilities | 0.4868 | 0.4865 |
| Hierarchical (material, then bull/bear) | 0.5568 | 0.5578 |

Vector scaling was worse than the existing calibrator. The hierarchical model
failed for a measurable reason: its stage-A probabilities were badly calibrated
(ECE 0.145/0.141) and stage B was at or below chance (AUC 0.468/0.475). Combining
two weak stages amplified error. Class weighting was not applied: reweighting
cannot create directional signal, and it would distort calibrated probabilities.

Abstention is honest but not useful as a direction product. At a 0.6 confidence
cut the model keeps 64% of rows at 75% accuracy, but almost all retained
predictions are NEUTRAL; at 0.8 it keeps 17% and still cannot identify bear
moves.

**Conclusion:** with these features, direction is not predictable at this horizon.
The defensible products are activity, range and consolidation. Direction
probabilities stay null.

## 3. Range quantile recalibration (3F.2)

The Phase 3E upper-quantile undercoverage was caused by using one fixed residual
adjustment from a 20-day calibration block. Two changes were tested under a fixed
protocol: expanding rolling residual calibration with a one-day gap, and
volatility-bucket residual calibration with global fallback.

| Instrument | Quantile | Global loss | Rolling loss | Global coverage | Rolling coverage |
|---|---:|---:|---:|---:|---:|
| NQ | 0.5 | 22.03 | 21.88 | 0.443 | 0.462 |
| NQ | 0.8 | 20.89 | 20.46 | 0.742 | 0.770 |
| NQ | 0.9 | 15.89 | 15.39 | 0.864 | 0.882 |
| ES | 0.5 | 4.60 | 4.57 | 0.445 | 0.465 |
| ES | 0.8 | 4.56 | 4.47 | 0.747 | 0.776 |
| ES | 0.9 | 3.60 | 3.43 | 0.861 | 0.885 |

Rolling calibration improves both pinball loss and coverage at every quantile.
Coverage is closer to nominal but still slightly low at 0.9. Volatility-bucket
calibration was no better than global (NQ 0.8 loss 20.93 vs 20.89). Intervals
were rearranged to be monotone; no crossings remain in the reported output.

This is a total-range distribution, not directional movement and not a
target-before-stop probability. No conformal finite-sample guarantee is claimed.

### Session ranges

Complete-window expanding empirical quantiles (`reports/phase3f_session_range.json`):

| Session | Instrument | Complete sessions | P80 coverage |
|---|---|---:|---:|
| LONDON | NQ | 45 | 0.76 |
| NEW_YORK | NQ | 48 | 0.71 |
| LONDON | ES | 44 | 0.83 |
| NEW_YORK | ES | 48 | 0.68 |
| ASIA | both | 9 | insufficient |

ASIA is `DATA_BLOCKED`: the cached five-minute history does not cover the full
19:00–03:00 New York window often enough to estimate a distribution. New York P50
coverage is only 0.32, which shows expanding empirical quantiles lag rising
volatility. These are research ranges; the forecast bundle now carries the
calibration status and coverage next to each range.

## 4. Target survival and first-touch intelligence (3F.3)

`research/target_survival.py` implements competing-outcome labels (target first,
stop first, neither), Aalen–Johansen cumulative incidence with censoring, and
point-in-time ATR enrichment. Ambiguous same-bar target+stop rows are excluded,
timeouts are censored, and all targets from one signal stay in the same fold.

Development dataset: 540 rows, 90 signals, 3 strategies, fixed 50/100/150/200/350/500
point targets, 24 complete five-minute bars, one tick per side.

| Distance | Median target ATR | Target first | Stop first | Neither |
|---|---:|---:|---:|---:|
| 50–100 | 1.69 | 45.4% | 27.6% | 27.0% |
| 100–200 | 4.12 | 13.5% | 34.5% | 52.0% |
| 200–350 | 8.26 | 1.2% | 35.7% | 63.1% |
| 350–500+ | 11.80 | 1.2% | 35.7% | 63.1% |

This is the clearest result of the phase: **200–500 point targets are rarely
reached before the original strategy stop within 24 bars.** A large daily range
does not imply a capturable directional move. The 350–500+ bucket contains only
one target-first event, so no model should be fit to it.

Grouped purged validation (16 day groups, 513 resolved rows):

| Model | Multiclass Brier | Target AUC | Stop AUC | Target ECE |
|---|---:|---:|---:|---:|
| Frequency | 0.6284 | 0.456 | 0.382 | 0.008 |
| Logistic | 0.5480 | 0.605 | 0.676 | 0.061 |
| LightGBM | 0.6603 | 0.660 | 0.417 | 0.061 |

Logistic improves aggregate Brier and target ranking, but the paired Brier
difference versus frequency has a 95% day-block interval of
[-0.192, +0.046] — it includes zero — and ECE 0.061 fails the 0.05 gate.
LightGBM is worse than the baseline overall and its stop AUC is below chance.
`NO_PROMOTION`. Target-before-stop fields stay null.

## 5. Fusion (3F.5)

A pre-declared equal-weight average of the two calibrated direction models was
compared with each standalone model. NQ: logistic 0.4886, LightGBM 0.4830, fusion
0.4836. ES: 0.4882, 0.4840, 0.4841. Fusion does not beat the best standalone model,
so it is not adopted. No weights were fitted and no strategy agreement is counted
as independent confirmation.

Strategy-level fusion and meta-labeling remain unsupported: the Phase 3E audit has
fewer than 40 trades per strategy and no independent period. That evidence
requirement has not changed.

## 6. Provider readiness (3F.4)

`reports/phase3f_providers.json` records credential presence without values,
endpoints, required entitlements, local coverage and a volume estimate. Both
`DATABENTO_API_KEY` and `FRED_API_KEY` are absent, so the adapters remain
fixture-tested only and are not described as live integrations. Databento pricing
is deliberately not estimated: callers must query the provider's billable-size
and cost endpoints, because entitlement and volume determine it.

## 7. Promotion decisions

`reports/phase3f_promotion.json` contains 21 assessments; all are
`NO_PROMOTION`. The binding reasons are the absence of an independent holdout,
unverified point-in-time provenance, insufficient sample adequacy, and in several
cases failed calibration or AUC gates. No threshold was relaxed.

## 8. Verification and next steps

Native-enabled suite and CI status are recorded in the implementation checkpoint.
No forecast schema changed. Bundle ranges now include calibration metadata; all
probabilities that lack a validated model remain null and every outlook remains
`NO_TRADE`.

Next: acquire licensed contract-level history, then re-test target survival with
much larger event counts and a genuinely fresh period. Direction should not be
revisited until features with plausible directional content (order flow, depth,
cross-asset lead-lag) are available; more model families on the same features will
not fix an AUC of 0.52.
