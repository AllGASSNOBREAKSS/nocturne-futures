# Phase 3D research protocol (fixed before rerunning models)

The cached intraday period was examined in Phase 3B. It cannot supply an
untouched final evaluation period. All new metrics are retrospective development
diagnostics; promotion remains NO_PROMOTION regardless of their values.

- Keep the latest 20% of session days out of this experiment. Do not score them.
- Rebuild only complete 5-minute analytical windows. Record feature and label
  availability, including the next session's end time.
- Expanding and 12-day rolling training; initial 12 training groups, six
  calibration groups, four test groups. Purge entire day/signal groups whose
  labels reach the next partition. One-hour elapsed embargo at both boundaries.
- Frequency, persistence/transition, regularized logistic and existing shallow
  gradient boosting; no hyperparameter search or new neural models.
- Original direction and range-contraction labels are primary. Compare a fixed
  sqrt-duration normalization and a 0.5 ATR sqrt(horizon-bars) neutral band as
  diagnostics only. The diffusion scaling assumption is not validated.
- Report raw and time-separated calibrated probabilities, multiclass sum Brier
  and log loss, binary Brier, AUC, ECE, class/sample counts, date ranges and
  per-session/current-efficiency-stratum metrics.
- Uncertainty: 1,000 moving-block replicates of three consecutive day groups;
  keep all correlated observations within each sampled day. Also report paired
  Brier difference versus frequency. Small intervals are not promotion evidence.
- Official FRED latest-vintage downloads are context-only. Do not use their
  revised historical values as point-in-time training features.
- Multi-year futures expansion requires an authorized export/provider. No
  synthetic padding, forward-filled missing bars or invented contract mapping.

Existing promotion gates remain unchanged. A fresh independent period, correct
event definitions, usable calibration and adequate sample size are still needed.

## Hourly expansion protocol (before hourly experiments)

Yahoo's two-year hourly data are a separate dataset. Two contiguous future hours,
positive-volume labels, no cross-closure horizon. Direction uses 0.5 current
24-hour-bar ATR times sqrt(2); contraction compares the next two-bar range with
0.8 times the last two-bar range. Inputs are trailing only. Keep the last 20%
of days unscored. Initial train/calibration/test groups: 60/20/30 days; rolling
train window 120 days; same purge, embargo, baselines and bootstrap as above.
Run NQ and ES separately. Do not tune against results. Missing raw-contract/roll
mapping and historical-vintage verification prohibit promotion. This does not
expand the five-minute session dataset.
