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

## Databento acquisition (credit-bounded, completed)

Operator supplied a rotated key and authorized up to $125 of promotional credits
(2026-11-09). The key lives only in ignored `data/security/databento.key`.
**The previous key still authenticated after rotation — revoke it in the portal.**

- Fresh quotes, then `scripts/phase4_databento_acquire.py`: definitions → 2-week pilot →
  pilot gate → yearly chunks 2010–2026. Each chunk re-quoted, checked against a $50 run cap
  and the $125 ceiling, and reserved in an append-only spend ledger before download; an
  uncompleted reservation is never retried (no double charge). Tests cover all guards.
- **Quoted spend: $41.30** (18 chunks: definitions $0.0085, pilot $0.10, years $41.19).
  Remaining against the ceiling: **$83.70** (quotes, not invoices — confirm in the portal).
- Pilot gate PASSED: 27,600 bars, minute-aligned, 0 off-tick, 0 OHLC errors, 0 unknown
  instruments; Databento 5m closes vs independent Yahoo 5m: median |diff| 0.0 pts.
- Acquired: **NQ 5,567,303** and **ES 5,742,093** one-minute bars, 2010-06-07 → 2026-11-06,
  67 contracts / 66 rolls each, every bar tagged with its contract (e.g. `NQZ6-2026`);
  0 structural issues across all chunks; 35 multi-day gaps per root (holidays/closures).
- Raw provider bytes (zstd CSV) and normalized tables stay in ignored `data/licensed/`;
  only aggregate statistics are committed (`reports/phase4_databento_*.json`).
- The app now defaults to Databento bars (1m/5m/15m/1h/4h/1d/1w aggregated within a
  contract, never across a roll) with Yahoo as a selectable fallback.

## 16-year results on authentic contract bars

Existing strategies, default parameters (no optimisation), 5m RTH, 2 contracts, cashflow-v2
costs, eras by date (development 2010–18, validation 2019–22, holdout 2023–26)
(`reports/phase4_backtests.md`):

| Strategy | Trades | Win % | PF | Net $ | Dev exp [95% CI] | Holdout exp [95% CI] | Verdict |
|---|---|---|---|---|---|---|---|
| NQ opening range | 3,846 | 49.0 | 1.05 | +134,340 | −17 [−50, 15] | +191 [−56, 438] | REJECTED |
| NQ VWAP pullback | 3,607 | 50.5 | 0.91 | −153,541 | −26 [−46, −7] | −21 [−181, 139] | REJECTED |
| NQ value rejection | 2,722 | 44.9 | 0.89 | −124,430 | −36 [−57, −14] | −78 [−263, 106] | REJECTED |
| ES opening range | 3,900 | 45.3 | 0.86 | −234,763 | −62 [−89, −34] | +13 [−111, 138] | REJECTED |
| ES VWAP pullback | 3,721 | 50.0 | 0.79 | −236,682 | −46 [−62, −31] | −106 [−186, −26] | REJECTED |
| ES value rejection | 2,462 | 45.0 | 0.76 | −175,820 | −65 [−85, −44] | −82 [−180, 16] | REJECTED |

NQ opening range's profit comes almost entirely from 2021–2026 (larger point values) and
92.8% of its trades time out; its development era is negative, so it is not a candidate.

NQ target-before-stop (`reports/phase4_target_study.json`): 4,220 sessions, 117,740 path
records, entry 10:00 ET, 50/50 … 500/250 point geometries, RTH and 24h horizons,
same-contract 5m paths with 1m tie resolution: **0 of 28 accepted**. In 2010–2018 (NQ
~2,000–7,000) 200–500-point targets were almost never reached; holdout EV intervals all
span zero.

## Not done / blocked

- Trades/TBBO/MBP/MBO order-flow history (not purchased; order-flow features stay disabled).
- Vercel deployment: replaced by the desktop app per operator instruction.
- Code signing of the executable; macOS/Linux packages.
- Directional forecasts remain withheld; no model is promoted.
