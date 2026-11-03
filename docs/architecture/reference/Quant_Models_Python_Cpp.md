# Quantitative Modeling, Python/C++ Runtime and Research Protocol

## 1. Language strategy

**Python primary:** canonical schemas (Pydantic), data access/ETL, pandas/Polars/DuckDB, scientific computing (NumPy/SciPy), statsmodels, LightGBM/other ML, calibrators, backtest/replay control, experiment registry and read-only FastAPI.

**C++20 conditional:** deterministic book reconstruction, high-rate tick processing, profile aggregation, replay simulation and latency-sensitive kernels *only when Python reference is correct and benchmarks show it is necessary*. Add CMake/scikit-build-core/pybind11; preserve memory/ABI contracts; avoid installing a separate C++ microservice before profiling. Require numerical and event-sequence parity with Python reference, compiler sanitizer checks and repeatable benchmarks.

## 2. Mathematical basis

### Probability and calibrated market outcomes

For entry rule `E`, target `G`, stop `B` and horizon `H`, predict `P(G first | E filled, F_t)` and `P(E filled | F_t)`. Also report competing outcomes stop-first, timeout, never-entered, ambiguity; ensure probabilities refer to mutually exclusive events when summed, and use nested monotonicity checks for compatible target distances. Prediction confidence is based on calibration/coverage, not subjective model voting.

### Time series

- Price returns, volatility clustering, multiscale realized volatility, change points and seasonality.
- ARIMA/ARIMAX for baseline return/level dynamics; GARCH or HAR-RV for volatility benchmark; rolling quantile and empirical baseline; Kalman/state-space for latent regime research.
- Test autocorrelation/persistence, fat tails, nonstationarity and economic-event structural breaks. Re-evaluate intermarket rolling relationships after contract changes.

### Stochastic calculus / processes

- Itô-process, Brownian/diffusion, jump-diffusion and OU/null models as mathematical benchmarks; financial paths are not assumed to follow a simple diffusion.
- Path simulation/first-passage probabilities are baselines and sensitivity tools for barriers, *not* proof that a level will be touched.
- Hawkes/self-exciting arrival models only with event-quality tick data; apply stability/identifiability checks.
- Scenario simulation: stress volatility, jump events, slippage, news freezes and order-book deterioration.

### Primary ML V1

1. Candidate strategy and level detection deterministic with as-of timestamps.
2. Triple-barrier/competing-outcome labels with fill and ambiguity handling.
3. Logistic/historical frequency baselines; then LightGBM target probability.
4. Quantile regression for MAE/MFE and expected range; calibrated regime flag.
5. Calibrate on separate chronological slice; evaluate Brier/log-loss, expected calibration error, reliability by target distance, session, volatility and event proximity.
6. Return `NO_TRADE` if missing necessary data, uncalibrated coverage, adverse net EV or violated deterministic risk constraints.

## 3. Source of truth for metrics

No hardcoded win percentages, no fabricated backtests, and no self-scored A+ model confidence. Record: raw dataset and feature snapshot checksum, label spec, training window, model weights/version, validation horizon, calibration method, transaction-cost assumptions, contract+tick/roll rules and real forecast outcomes. Use chronological walk-forward and purge/embargo where outcome intervals overlap. Limit repeated tuning against final holdout.

## 4. Integration boundaries

`Python reference -> typed array/Arrow/IPC boundary -> optional C++ kernel -> parity/performance harness -> feature snapshot -> Python ML inference -> deterministic risk gate`. Native kernels do not own risk decisions, macro event provenance, training-set splits or order privileges. Any C++ dependency must remain optional where possible; Python fallback stays correct and tested.

## 5. Performance metrics

Measure **end-to-end event-to-prediction latency** (p50/p95/p99), feed dropout recovery, memory footprint, max book messages per second, replay speed versus historical rate, C++ vs Python correctness and profile speedups. Optimize only measured bottlenecks; do not sacrifice reproducibility for raw throughput.

## 6. Model promotion policy

A candidate model requires correctness/parity checks, data-coverage validation, out-of-sample predictive calibration, economic performance after realistic costs, ablation against comparable baselines, stability under changed market regimes and a rollback-ready versioned artifact. Nonimprovement is a valid experiment result. The platform should continue working in research/no-trade mode if no model qualifies.
