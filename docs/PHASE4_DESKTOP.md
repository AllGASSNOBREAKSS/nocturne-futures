# Phase 4 — Nocturne Terminal (desktop research platform)

November 9, 2026. Branch `feat/phase4-desktop`, base `6ed3ae8`.
Per the operator's instruction, Phase 4 ships a **Windows desktop application**
instead of a Vercel deployment. **NO_TRADE / NO_PROMOTION / no live data / no broker.**

## What was built

```
Electron main (desktop/electron/main.cjs)
  ├─ starts `python -m nocturne.desktop_server --port <random>` with a random
  │  per-launch admin token (env only, never sent to the UI)
  ├─ sandboxed renderer (contextIsolation, sandbox, no Node, CSP, no navigation)
  └─ narrow IPC bridge: allow-listed /v1 paths, GET/POST only, token attached in main
React terminal (desktop/src) — 10 views, F1–F10, Ctrl+K command palette
  └─ every number comes from the local API; failures show per-view errors
Desktop API (src/nocturne/desktop_server.py) on 127.0.0.1 only
  ├─ existing SecurityMiddleware: bearer auth, host allow-list, rate/body limits,
  │  audit log (rotating, secret-free); mutations are an explicit admin allow-list
  └─ src/nocturne/studio/
       market.py      bars (1m/5m/15m/1h/4h/1d/1w), levels, regime, session ranges
       indicators.py  causal SMA/EMA/RSI/MACD/ATR/ADX/Bollinger/VWAP/swings
       rules.py       user rule strategies (≤8 conditions, next-bar entry)
       backtest.py    existing engine + existing strategies or user rules
       training.py    walk-forward models (frequency/logistic/RF/LightGBM)
       forecasts.py   Asia/London/NY/full-day range forecasts (append-only)
       jobs.py        STUDIO_TRAINING / STUDIO_BACKTEST on the existing orchestrator
       insights.py    intelligence, operations, research and saved configs
```

User jobs run in their own orchestrator store (`data/studio/jobs`, ignored), executed by
the existing allow-listed worker subprocess with watchdog, timeout (1,800 s) and crash
recovery. Jobs survive navigating away or closing a view; cancellation is cooperative.

## Views

| Code | View | Backed by |
|---|---|---|
| OVR | Overview — regimes, 1H chart, levels, forecast, verdicts, jobs, health | regime, bars, levels, forecasts, research, jobs, operations |
| MKT | Market Analysis — candles/volume, 7 overlays, oscillators, levels, backtest trade markers | bars, indicators, levels, sessions, trades.csv |
| PRED | Prediction Center — issue/evaluate session forecasts, retrospective calibration, NDX shadow | forecasts/sessions, ndx-shadow |
| ML | Model Studio — configure, train, cancel, compare, reliability, importance, logs | training-jobs, configs/model |
| LAB | Strategy & Indicator Lab — built-ins or rule builder, costs, save versions, backtest | indicators/catalog, configs/strategy, backtests |
| BT | Backtesting Center — metrics, equity, monthly, eras, year/session/regime, slippage, ledger, export | backtests, trades.csv |
| SIG | Signal Analytics — all 26 ranked candidates incl. rejected, compare, studio verdicts | signals, research |
| PERF | Model Performance — every Phase 3V task/config metric, forward record, experiments | research, ndx-shadow, models |
| INTL | Market Intelligence — FRED, CFTC, Fed, SEC, BLS with timestamps | intel |
| OPS | Data & Operations — datasets, Databento status/quotes, scheduler, providers, jobs, refresh | operations, system/health, data/refresh |

## Verification (actual results)

- **Parity:** studio backtest of NQ ORB reproduces Phase 3V exactly (42 trades, $18,340);
  studio training of NQ ≥350-pt range (price+volatility logistic) reproduces Phase 3V
  development/holdout Brier Δ to 1e-12 (−0.0510074 / −0.0456360). Both are tests.
- **Leakage defect found and fixed before release:** the first studio bar loader stamped
  bars available at their *start*, letting session strategies see a bar's close early
  (ORB showed $105,810 instead of $18,340). Bars are now available at their close;
  a regression test enforces it and every indicator is tested against future truncation.
- **Full-stack E2E through the Electron app** (renderer bridge → IPC → API → worker):
  a user rule backtest (NQ 1h, close crosses above VWAP and RSI>50, 1.5 ATR stop, 1R/2R)
  produced 422 trades, 48.1% win rate, PF 0.96, −$39,430 net (holdout expectancy CI
  −$997…$1,787) → **REJECTED**; an ES compression LightGBM (price+volatility) produced
  development Brier Δ −0.0134 [−0.0178, −0.0088], holdout −0.0236 → **ACCEPT_RESEARCH_ONLY**.
  Cancelling a running random-forest job recorded `CANCELLED_BY_USER`.
- **Screenshots** of all 10 views were captured from the dev build and from the packaged
  build; 0 view errors in the renderer console.
- **Tests:** 471 Python tests pass (451 + 20 desktop); `tsc --noEmit` and `vite build` pass.
- **Packaging:** `desktop/release/Nocturne Terminal 4.0.0.exe` (portable, unsigned, 81 MB)
  launches, starts the backend and renders all views.

## Data and Databento

Data shown is the free, checksummed Yahoo continuous-futures archive (daily 2000→,
hourly 2024→, 5m 60 days, 1m 30 days) plus Phase 3U macro/positioning/filing sources —
**historical/delayed, never real-time**. Roll-contaminated bars exist in Yahoo's
continuous series (e.g. 2025-09-16/17 NQ/ES hourly lows ~250 pts below neighbours);
research labels already exclude ±3 sessions around the 66 Databento volume rolls.

**Databento acquisition did not run.** Phase 4 requires a freshly rotated key (the
previous one was exposed in chat) and a verified credit balance before any download;
the historical API does not expose the balance. Status in the app: `BLOCKED`, spend $0.
Quotes on file: full NQ+ES 1-minute 2010–2026 ≈ $41.29; definitions $0.01.

## Not done / blocked

- Databento 2010–2026 download, contract-level validation, and any trades/MBP/MBO
  order-flow features (disabled in the UI and labelled).
- Vercel deployment: replaced by the desktop app per operator instruction.
- Code signing of the executable; macOS/Linux packages.
- Directional forecasts remain withheld; no model is promoted.
