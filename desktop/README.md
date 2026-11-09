# Nocturne Terminal (desktop)

Electron + React + TypeScript + Tailwind front end for the Nocturne research backend.
The app launches the Python backend itself; there is nothing to host.

## Requirements

- Windows 10/11, Node 20+ and npm.
- Python with the repository requirements installed (the same environment that runs
  `pytest`). Set `NOCTURNE_PYTHON` if `python` on PATH is not that interpreter.
- The repository checkout. The app finds it next to `desktop/`, or set `NOCTURNE_REPO`.

## Install for everyday use (recommended)

```powershell
cd desktop; npm install; npm run build; npx electron-builder --win portable dir
powershell -ExecutionPolicy Bypass -File ..\scripts\install_desktop.ps1
```

This copies the app to `%LOCALAPPDATA%\Programs\Nocturne Terminal`, records the repo and
Python paths in `nocturne.json`, and adds **Nocturne Terminal** shortcuts to the Desktop and
Start Menu. Re-run both lines after pulling updates.

## Run

```powershell
cd desktop
npm install
npm run build      # typecheck + production UI build
npm start          # launches the app and its local backend
npm run dev        # hot-reload UI (Vite on :5173) + Electron
npm run dist       # portable Windows exe in desktop/release/
```

Keyboard: F1–F11 switch views, Ctrl+K opens the command palette.

## Predict (home screen)

Pick NQ or ES and press **Predict next session**. One click runs the calibrated level
models, the validated regime classifiers, the indicators and the strategy check, then shows:

- the expected range and a calibrated 80% high/low band;
- a level ladder (prior high/low/VWAP, overnight, RTH, initial balance, value area, POC,
  5/20-session extremes, projected 50/25/10% zones) with the probability each is traded;
- volatility outlook vs the usual rate, and direction reported as **no edge** (it failed
  validation);
- the measured 2013–2026 walk-forward accuracy of the same method.

Each prediction is journaled once per target session and scored when that session's bars
arrive. Models train in the background on first start (~25 s per instrument) and are cached.

## Security model

- Backend binds to `127.0.0.1` on a random port with a random per-launch admin token.
- The token lives only in the Electron main process; the sandboxed renderer calls a
  narrow IPC bridge that allow-lists `/v1/...` paths and GET/POST.
- POST is accepted only for: start/cancel research jobs, issue session forecasts, save
  configurations, refresh free data. No order, broker or live-data endpoints exist.
- No provider credentials are read by the UI. The Databento key (if present) stays in the
  ignored `data/security/` folder and is never sent to the renderer.

## QA modes

- `NOCTURNE_CAPTURE=<dir>`: visits every view, saves screenshots, writes
  `renderer-console.log` next to `<dir>`, exits.
- `NOCTURNE_E2E=<dir>`: through the real renderer bridge, submits a rule backtest and a
  training job, waits for the worker, screenshots results and writes `e2e.json`.

Charts use TradingView Lightweight Charts (Apache-2.0).
