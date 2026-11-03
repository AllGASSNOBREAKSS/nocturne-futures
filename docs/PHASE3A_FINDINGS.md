# Phase 3A Findings — Backtest Validation and Predictive Foundation

**Date:** 2026-11-03  
**Branch:** `feat/phase3a` (merged to `main`)  
**Data:** cached 60-day 5-minute NQ/ES bars; 15-year daily NQ research bars.  
**Status:** validation complete for the feasible scope; no strategy or model promoted.

## Executive summary

1. **The ORB timeouts are explained, not a fill bug.** The originally reported
   ledger had 40; after the RTH-only session fix the reproducible ledger has
   **41**. Median risk is **208.9 NQ points**, median MFE is only **0.26R**,
   4.5% of trades reach 1R, and **0%** reach 2R. All 41 timeouts had MFE < 1R.
   The target/stop geometry is too wide for a 24-bar (2-hour) horizon.
2. **The ORB P&L is regime-dependent.** Development: 27 trades, **−$18,730**,
   PF 0.313. Holdout: 17 trades, **+$23,670**, PF 4.799, with 15/17 timeouts.
   The sign flip is a regime artifact, not an edge.
3. **The daily barrier models do not beat the frequency baseline.** Across four
   label geometries, frequency has the lowest Brier. Price-only features show
   no stable signal; the high-threshold economic check is sparse and not
   validated.

## 1. Backtest audit

### Why 41 trades timed out

| Metric | Value |
|---|---:|
| Trades | 44 |
| Timeouts | 41 |
| Median risk (entry − stop) | 208.9 points |
| Risk range | 126.2–577.2 |
| Median MFE | 0.26R |
| Trades reaching 1R | 4.5% |
| Trades reaching 2R | 0.0% |
| Median MAE | −0.34R |
| Timeouts with MFE < 1R | 41 / 41 |

The 60-minute initial balance is wide; using its opposite side as the stop
produces a 200-point risk. A 2-hour session rarely travels 1R, so the 1R/2R/3R
targets are unreachable. Only 2 TP1 fills and zero TP2/TP3 fills occurred.

### Accounting checks

- `dollars = gross_dollars − costs` for every trade.
- `gross_dollars = points × multiplier` for every trade.
- Costs now charge commission on entry **and each partial exit**: a full stop
  is two commissions, TP1+TP2 is three.
- Slippage is one tick on entry and one tick-equivalent on the total exit.
- The trade ledger now records `stop_price`, `target_prices`, `risk_points`,
  `mfe_r`, `mae_r`, `gross_dollars` and `costs`.

### Correctness fixes

- Maximum **one target per bar** (conservative; avoids filling TP1 and TP2 from
  one bar's range).
- A gap beyond the first target **skips the entry** instead of filling at a
  worse price.
- Session-bound backtests use **RTH bars only**; the horizon cannot run into the
  overnight session.
- `BacktestConfig` rejects unsupported ambiguity policies, zero contracts,
  negative costs, and exit fractions above 1.0.
- `Signal` rejects targets on the wrong side of entry.

## 2. Held-out, cost-stressed study

Chronological split: first 60% development, last 40% holdout. Base costs:
$2.50/contract/side, 1 tick slippage, 1 contract.

| Instrument | Strategy | Split | Trades | Win % | Net $ | PF | Max DD $ | Timeouts |
|---|---|---|---:|---:|---:|---:|---:|---:|
| NQ | ORB | development | 27 | 29.6 | **−18,730** | 0.313 | 18,730 | 26 |
| NQ | ORB | holdout | 17 | 76.5 | **+23,670** | 4.799 | 2,855 | 15 |
| NQ | VWAP | development | 27 | 59.3 | +1,911 | 1.160 | 3,932 | 4 |
| NQ | VWAP | holdout | 15 | 73.3 | +8,398 | 2.285 | 3,131 | 1 |
| NQ | value | development | 16 | 56.2 | +2,935 | 1.538 | 4,160 | 3 |
| NQ | value | holdout | 12 | 25.0 | **−6,170** | 0.475 | 6,555 | 1 |
| ES | ORB | development | 27 | 33.3 | −5,853 | 0.580 | 7,438 | 23 |
| ES | ORB | holdout | 19 | 47.4 | +3,665 | 1.531 | 2,410 | 16 |
| ES | VWAP | development | 28 | 35.7 | −5,342 | 0.401 | 6,891 | 4 |
| ES | VWAP | holdout | 14 | 64.3 | +1,149 | 1.358 | 2,080 | 1 |
| ES | value | development | 14 | 64.3 | −320 | 0.902 | 2,765 | 2 |
| ES | value | holdout | 14 | 64.3 | +2,030 | 1.907 | 1,165 | 1 |

### Cost stress (holdout net dollars)

| Instrument | Strategy | 1 tick | 2 ticks | 3 ticks | 4 ticks |
|---|---|---:|---:|---:|---:|
| NQ | ORB | 23,670 | 23,415 | 23,160 | 22,905 |
| NQ | VWAP | 8,398 | 8,183 | 7,968 | 7,753 |
| NQ | value | −6,170 | −6,350 | −6,530 | −6,710 |
| ES | ORB | 3,665 | 2,953 | 2,240 | 1,528 |
| ES | VWAP | 1,149 | 549 | 49 | −595 |
| ES | value | 2,030 | 1,505 | 980 | 455 |

**Reading:** the ORB holdout is positive but its development is deeply negative,
and 15/17 holdout trades still time out. The VWAP is the only strategy positive
in both splits on NQ, but ES development is negative. The value strategy flips
sign between instruments and splits. None is robust enough to promote.

## 3. ML audit

### Label geometry

| Config | TP | SL | Timeout | Ambiguous | Binary n | Base rate |
|---|---:|---:|---:|---:|---:|---:|
| 1.5 ATR / 1.0 ATR / 5d | 1,218 | 1,722 | 811 | 10 | 2,940 | 41.4% |
| 1.0 / 1.0 / 3d | 1,584 | 1,374 | 778 | 25 | 2,958 | 53.5% |
| 1.0 / 0.5 / 5d | 1,320 | 2,258 | 111 | 72 | 3,578 | 36.9% |
| 2.0 / 1.0 / 10d | 1,166 | 2,109 | 479 | 7 | 3,275 | 35.6% |

### Walk-forward Brier

| Config | Frequency | Logistic | GBM |
|---|---:|---:|---:|
| 1.5 / 1.0 / 5d | **0.2474** | 0.2493 | 0.2483 |
| 1.0 / 1.0 / 3d | **0.2509** | 0.2525 | — |
| 1.0 / 0.5 / 5d | **0.2321** | 0.2332 | — |
| 2.0 / 1.0 / 10d | **0.2327** | 0.2343 | — |

Frequency wins in every geometry. The lower Brier in the tight-stop and
long-horizon configs reflects a more imbalanced class distribution (36–37% TP),
not better skill. Cross-config Brier comparisons are misleading.

### Regime stability (current config, logistic)

| Regime | n | Brier | Accuracy | ECE |
|---|---:|---:|---:|---:|
| Low volatility | 1,084 | 0.2535 | 0.522 | 0.065 |
| High volatility | 1,083 | 0.2452 | 0.595 | 0.097 |

Yearly Brier ranges from **0.229** (2022) to **0.266** (2019); accuracy ranges
from **0.457** (2017) to **0.700** (2022). The model is not stable across
regimes.

### Economic threshold check (logistic, current config)

| Threshold | Trades | Win % | Avg R | Net $ | Max DD $ |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 217 | 39.6 | −0.009 | **−36,590** | 80,888 |
| 0.55 | 42 | 47.6 | +0.191 | +42,152 | 19,309 |
| 0.60 | 18 | 61.1 | +0.528 | +46,045 | 7,931 |

The 0.55/0.60 results look attractive but rest on **42 and 18 trades** selected
after seeing the walk-forward output. That is not a validated edge. At the
inclusive 0.50 threshold the strategy loses after costs.

## 4. Target-level dataset

Interface: `src/nocturne/research/target_dataset.py`.  
Builder: `python -m nocturne dataset --instrument NQ --strategy vwap`.

Each row is one `(signal, candidate target)` and records:

`strategy_id, instrument_id, signal_asof, side, entry_time, entry_price,
stop_price, target_id, target_price, r_multiple, horizon_bars, outcome,
target_first, bars_to_target, bars_to_stop, mfe_points, mae_points, mfe_r, mae_r`.

Committed datasets:

| File | Rows | TP | SL | Timeout |
|---|---:|---:|---:|---:|
| `target_dataset_NQ_orb.csv` (1/2/3R, 24 bars) | 132 | 2 | 3 | 127 |
| `target_dataset_NQ_orb_diag.csv` (0.5/1/1.5R, 78 bars) | 132 | 24 | 18 | 90 |
| `target_dataset_NQ_vwap.csv` (1/2R, 18 bars) | 84 | 32 | 33 | 19 |
| `target_dataset_NQ_value.csv` (POC, 18 bars) | 28 | 10 | 14 | 4 |

The ORB actual-target dataset is **not trainable** (2 positives). The diagnostic
geometry and the VWAP dataset are the usable starting points. Any model built on
them must split chronologically and keep the last 40% untouched.

## 5. Native parity

The C++20 kernel was built locally with MSVC 19.51 and pybind11 3.1:

```text
nocturne_native.cp314-win_amd64.pyd
tests/test_native_parity.py -> passed
```

With the module on `PYTHONPATH`: **155 passed**. Without it: **154 passed,
1 skipped**. CI adds an Ubuntu native build/parity job.

## 6. Still blocked

- True trades-by-price, tick, quote, DOM, MBO: **DATA_BLOCKED**.
- CFE VX futures: **DATA_BLOCKED**; `^VIX` spot is a labelled proxy.
- Point-in-time economic calendar: not wired.
- No promotion, no paper/live execution, no TradingView automation.

## 7. Next exact step

Use the VWAP target dataset as the first trainable set, split chronologically,
and model `target_first` with the same frequency/logistic/GBM baselines. Require
a Brier improvement over frequency on the untouched holdout before adding
features. In parallel, rebuild the ORB geometry around a tighter stop or a
full-session horizon, but evaluate it on the existing holdout only once.
