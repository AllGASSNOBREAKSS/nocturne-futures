# Architecture Decisions

**Date:** 2026-11-03

## Phase 3I — operational integrity without model promotion

- Preserve the original frozen model bytes and forecast journal. Apply the
  already-frozen residual adjustments at runtime, identifying corrected inference
  separately from the legacy first forecast. Never repair issued predictions.
- Enforce one model/instrument/horizon/date issuance under host-local OS locks;
  revised snapshots cannot produce a second forecast. Fsync appends, reject
  corrupt journals and recover locks through OS process lifecycle, not lock age.
- Separate cash-equity DST/early-close maturity from futures calendars. Calendar
  support is bounded; unsupported years and incomplete outcomes fail closed.
- Operational sources require actual fresh receipts and matching raw/normalized
  hashes; frozen historical context cannot silently become a current snapshot.
- Windows Task Scheduler provides host persistence only for the configured
  logged-in principal. No uptime SLA or logout-independent service is implied.
- Contract target datasets share barrier labels, not unreviewed Phase 3F fitted
  probabilities. Structural readiness is not provenance, authenticity or promotion.
- PIT schedule proximity needs explicit coverage; missing schedules cannot mean
  no event risk. Event risk never implies price direction.

## Phase 3D — horizon contracts and independent evidence

- Public hourly futures proxies are a separate two-hour research stream, never
  upsampled into five-minute session or barrier data. Contract/roll mapping is
  unknown, which blocks production promotion.
- Official FRED current-vintage context is stored separately and excluded from
  historical features until publication/vintage records are available.
- Raw/normalized/checksum manifests use CSV without a new columnar dependency.
  Conflicting revisions fail closed; no automatic back-adjustment or gap filling.
- Inclusive label-end purging and one-hour embargo operate on whole signal/day
  groups. Calibration is time-separated. The final 20% is unscored, but dates
  inspected previously are not called an untouched final holdout.
- Complete session grids and exact bar-count barrier horizons replace permissive
  partial labels. Right-censoring is distinct from timeout and stop loss.
- Keep existing promotion gates. Aggregate Brier improvements do not override
  weak class recall, unknown roll provenance or missing independent validation.
- Production session probabilities cannot reuse immediate rolling-bar event
  estimates. Return null when the correct event has no validated model.

## AD-001 — Modular monolith, Python-first

The existing repository is a small Python package plus a TypeScript ingestion
helper. v2 stays a modular monolith. Python owns contracts, data, auction logic,
features, strategies, backtests, models, risk, API, and journal. TypeScript stays
the fetch/validation helper. No microservices.

## AD-002 — JSONL event store before Parquet

The environment has no PyArrow/Parquet. An append-only JSONL store partitioned by
instrument and UTC date is sufficient for the first replay implementation and is
easy to audit. The store interface is provider-agnostic; a Parquet backend can be
added later without changing callers.

## AD-003 — Pydantic v2 contracts at boundaries

The package schemas are JSON Schema. Pydantic models mirror them and are used at
the adapter, API, and journal boundaries. Extra fields are forbidden on the
canonical contracts. Internal research objects may be dataclasses.

## AD-004 — Point-in-time replay is mandatory

Every canonical event carries `event_time_utc`, `available_at_utc`, and
`received_at_utc`. Replay filters on `available_at_utc <= asof`, then sorts by
event time and source sequence. Features must use the replay stream, never the
raw file order.

## AD-005 — True volume profile vs bar approximation

True volume-at-price requires executed trades with quantity. The implementation
supports it and is tested with synthetic trades. Because the repo has no tick
data, the demo may compute a **bar approximation** by distributing bar volume
across the bar range. It is always labeled `BAR_APPROXIMATION` and never described
as exchange-accurate POC/VAH/VAL.

## AD-006 — TPO is not volume profile

TPO counts time-bracket occupancy; volume profile sums traded quantity. They have
separate modules, separate field names (`tpo_poc`, `tpo_vah`, `tpo_val`), and a
test that proves they differ on a fixture.

## AD-007 — Order flow is gated, not inferred

Tape, quotes, DOM, footprint, and CVD are optional adapters. If the data is
absent, the feature gate returns `UNAVAILABLE` with a reason. OHLCV is never
relabeled as order flow. No hidden-order or spoofing claims.

## AD-008 — Models start with null and logistic baselines

The first model is a historical-frequency / logistic baseline with walk-forward
validation. The gradient-boosted challenger is sklearn's
`HistGradientBoostingClassifier` until LightGBM is installed. Calibration is
reported with Brier, log loss, and reliability tables. A model that does not beat
the baseline is not promoted.

## AD-009 — C++ is deferred, not faked

No `cmake`, `g++`, or `pybind11` is available. The Python reference is the source
of truth. Native kernel source and parity fixtures can be added when the
toolchain exists; no claim of a built native module will be made before then.

## AD-010 — No live trading, no broker endpoints

The API is read-only. There is no order placement, no TradingView auto-drawing,
and no broker credential handling. `NO_TRADE` is a valid and default decision when
data quality or calibration coverage is insufficient.

## AD-011 — Data licensing and provenance

Yahoo Finance is a public, unofficial endpoint; it is labeled as such. Treasury
and Federal Reserve data are public. ForexFactory calendar payloads are not
committed or redistributed. The private Obsidian vault is not published. Every
stored event records its source and license scope.

## AD-012 — Preserve the existing call/report pipeline

The dated call artifacts, scorecards, 15-year study, and TypeScript validation
remain. New backend modules are additive. The existing CLI subcommands continue
to work.

## AD-013 — Signal-grouped chronological splits

Multiple candidate targets from one signal are correlated examples. All rows
from one `signal_id` stay in the same train, validation or test partition. The
target model uses chronological signal splits and expanding folds; it does not
randomly shuffle rows.

## AD-014 — Research forecasts use null probabilities

`Forecast V1` never invents direction or target probabilities. When no validated
model exists, `direction_probability` and every `target.probability_before_stop`
are `null`, `validation_status` is `research_only`, and `decision` is `NO_TRADE`.
Levels, range and regime may still be published as research context.

## AD-015 — Level strength is confluence plus empirical interaction

A level zone records its independent structural sources, touch count and
reaction rate. Ranking is by confluence, then empirical reaction rate, then touch
count. It is not an arbitrary score. Touch statistics use only bars available at
the as-of timestamp.

## AD-016 — Range forecasts are empirical and volatility-conditioned

The expected-range model uses the historical distribution of forward high-low
ranges, conditioned on the current ATR quartile. It reports the sample size and
bucket. It does not force 200/350/500-point targets; those are probabilities, not
promises.

## AD-017 — Current regime is rules-based; future regime is empirical

Current regime labels use ADX, range efficiency, overlap and volatility
percentile. Future-regime probabilities come from historical transitions of the
same rules, not from an unvalidated classifier. They are research estimates and
are reported with their limitations.

## AD-018 — Asia/London/New York are analytical windows

ASIA, LONDON, PREMARKET and NEW_YORK are documented America/New_York analytical
windows, not official exchange sessions. RTH, OVERNIGHT and ETH use the exchange
calendar. Early-close dates are explicit. Every session snapshot is point-in-time
and records `available_at` provenance.

## AD-019 — Critical-day risk has no directional bias

Critical-day detection is an event-risk overlay. It may return `PRE_EVENT_LOCK`,
`SCHEDULED_HIGH_IMPACT`, `LIQUIDITY_STRESS`, `NORMAL` or `DATA_UNAVAILABLE`.
`directional_bias` is always null. An event alert must not be interpreted as a
bullish or bearish signal.

## AD-020 — Reachability is not target-before-stop

`price_levels/reachability.py` estimates the probability that a level is touched
within a horizon, conditioned on ATR-normalized distance. It is not the
probability that a target is reached before a stop. Forecast targets keep
`probability_before_stop` null and expose the touch estimate separately with its
method and sample size.

## AD-021 — The committed calendar is a sample, not live consensus

`data/macro/sample_events.json` is a public-schedule sample with null consensus
and actual values. It exists to exercise the schema and critical-day rules.
Production ingestion requires an authorized point-in-time provider, publication
and availability timestamps, and licensing compliance.
