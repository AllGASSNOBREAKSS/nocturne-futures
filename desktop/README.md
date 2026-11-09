# Nocturne Terminal (desktop)

Electron + React + TypeScript + Tailwind front end for the Nocturne research backend.
The app launches the Python backend itself; there is nothing to host.

## Requirements

- Windows 10/11, Node 20+ and npm.
- Python with the repository requirements installed (the same environment that runs
  `pytest`). Set `NOCTURNE_PYTHON` if `python` on PATH is not that interpreter.
- The repository checkout. The app finds it next to `desktop/`, or set `NOCTURNE_REPO`.

## Run

```powershell
cd desktop
npm install
npm run build      # typecheck + production UI build
npm start          # launches the app and its local backend
npm run dev        # hot-reload UI (Vite on :5173) + Electron
npm run dist       # portable Windows exe in desktop/release/
```

Keyboard: F1–F10 switch views, Ctrl+K opens the command palette.

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
