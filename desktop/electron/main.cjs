// Nocturne Terminal — Electron main process.
// Launches the local Python research backend on a random loopback port with a
// fresh per-launch admin token. The renderer is sandboxed and never sees the
// token: every API call goes through the narrow IPC bridge below.
const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const { spawn, execFile } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");

const DEV = process.env.NOCTURNE_DEV === "1";
let backend = null;
let port = null;
let token = null;
let status = { state: "starting", detail: "Launching research backend" };
let win = null;

// Installed copies carry nocturne.json next to the executable: {"repo": "...", "python": "..."}.
function installConfig() {
  try { return JSON.parse(fs.readFileSync(path.join(path.dirname(process.execPath), "nocturne.json"), "utf8")); } catch { return {}; }
}

function findRepo() {
  const candidates = [process.env.NOCTURNE_REPO, installConfig().repo, path.resolve(__dirname, "..", ".."),
    path.resolve(path.dirname(process.execPath), ".."), "D:\\nocturne-futures"].filter(Boolean);
  return candidates.find((c) => fs.existsSync(path.join(c, "src", "nocturne", "desktop_server.py")));
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port: p } = server.address();
      server.close(() => resolve(p));
    });
  });
}

function setStatus(next) {
  status = { ...status, ...next, at: new Date().toISOString() };
  if (win && !win.isDestroyed()) win.webContents.send("nocturne:status", status);
}

async function startBackend() {
  const repo = findRepo();
  if (!repo) {
    setStatus({ state: "error", detail: "Repository not found. Set NOCTURNE_REPO to the nocturne-futures folder." });
    return;
  }
  port = await freePort();
  token = crypto.randomBytes(32).toString("base64url");
  const logPath = path.join(app.getPath("userData"), "backend.log");
  const log = fs.createWriteStream(logPath, { flags: "a" });
  const python = process.env.NOCTURNE_PYTHON || installConfig().python || "python";
  const env = { ...process.env, NOCTURNE_DESKTOP_TOKEN: token, PYTHONUNBUFFERED: "1",
    PYTHONPATH: [path.join(repo, "src"), path.join(repo, "native", "build"), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter) };
  backend = spawn(python, ["-m", "nocturne.desktop_server", "--port", String(port)], { cwd: repo, env, windowsHide: true });
  backend.stdout.pipe(log);
  backend.stderr.pipe(log);
  let spawnFailed = false;
  backend.on("error", (err) => {
    // e.g. ENOENT when NOCTURNE_PYTHON points nowhere: report it, never hang.
    spawnFailed = true;
    log.write(`[main] backend spawn failed: ${err.code || err.message}\n`);
    setStatus({ state: "error", detail: `Python backend could not start (${err.code || err.message}) using "${python}". Set NOCTURNE_PYTHON to a valid interpreter. Log: ${logPath}`, logPath });
  });
  backend.on("exit", (code) => setStatus({ state: code === 0 ? "stopped" : "error", detail: `Backend exited (code ${code}). Log: ${logPath}`, logPath }));
  setStatus({ state: "starting", detail: `Backend starting on 127.0.0.1:${port}`, repo });
  for (let i = 0; i < 120; i++) {
    if (spawnFailed || backend.exitCode !== null) return;
    try {
      const r = await fetch(`http://127.0.0.1:${port}/health`);
      if (r.ok) { setStatus({ state: "ready", detail: "Backend ready", port, repo, logPath }); return; }
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 500));
  }
  setStatus({ state: "error", detail: `Backend did not start. See ${logPath}` });
}

function stopBackend() {
  if (!backend || backend.exitCode !== null) return;
  if (process.platform === "win32") execFile("taskkill", ["/PID", String(backend.pid), "/T", "/F"], () => {});
  else backend.kill("SIGTERM");
}

const ALLOWED = /^\/(health|v1\/[A-Za-z0-9_\-/.]+)(\?[A-Za-z0-9_\-=&%:.,^+]*)?$/;

async function request({ method = "GET", path: p, body, raw = false }) {
  if (status.state !== "ready") return { ok: false, status: 0, error: status.detail };
  if (!["GET", "POST"].includes(method) || typeof p !== "string" || !ALLOWED.test(p)) return { ok: false, status: 400, error: "request not allowed" };
  try {
    const r = await fetch(`http://127.0.0.1:${port}${p}`, {
      method, headers: { Authorization: `Bearer ${token}`, ...(body ? { "Content-Type": "application/json" } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await r.text();
    let data = text;
    if (!raw) { try { data = JSON.parse(text); } catch { /* keep text */ } }
    return { ok: r.ok, status: r.status, data, error: r.ok ? null : (data && data.detail) || `HTTP ${r.status}` };
  } catch (e) {
    return { ok: false, status: 0, error: String(e && e.message || e) };
  }
}
ipcMain.handle("nocturne:request", (_event, args) => request(args));
ipcMain.handle("nocturne:status", () => status);
ipcMain.handle("nocturne:save-file", async (_e, { name, content }) => {
  const { canceled, filePath } = await dialog.showSaveDialog(win, { defaultPath: name });
  if (canceled || !filePath) return { saved: false };
  fs.writeFileSync(filePath, content, "utf8");
  return { saved: true, filePath };
});
ipcMain.handle("nocturne:reveal-log", () => status.logPath && shell.showItemInFolder(status.logPath));

function createWindow() {
  win = new BrowserWindow({
    width: 1600, height: 960, minWidth: 1180, minHeight: 720, backgroundColor: "#06080b", show: false,
    titleBarStyle: "hidden", titleBarOverlay: { color: "#06080b", symbolColor: "#8592a3", height: 38 },
    icon: path.join(__dirname, "icon.png"),
    webPreferences: { preload: path.join(__dirname, "preload.cjs"), contextIsolation: true, sandbox: true, nodeIntegration: false },
  });
  win.once("ready-to-show", () => win.show());
  win.webContents.on("will-navigate", (e) => e.preventDefault());
  // News links open in the user's browser; nothing opens inside the app.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https:\/\//.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  if (DEV) win.loadURL("http://localhost:5173");
  else win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
}

// QA mode: NOCTURNE_CAPTURE=<dir> visits every page and saves screenshots, then exits.
async function capture(dir) {
  fs.mkdirSync(dir, { recursive: true });
  const routes = ["/", "/market", "/predictions", "/models", "/lab", "/backtests", "/signals", "/performance", "/intel", "/ops"];
  for (let i = 0; i < 240 && status.state !== "ready"; i++) await new Promise((r) => setTimeout(r, 500));
  for (const route of routes) {
    await win.webContents.executeJavaScript(`location.hash = "#${route}"`);
    await new Promise((r) => setTimeout(r, Number(process.env.NOCTURNE_CAPTURE_WAIT || 6000)));
    const image = await win.webContents.capturePage();
    fs.writeFileSync(path.join(dir, `${route === "/" ? "overview" : route.slice(1)}.png`), image.toPNG());
  }
  app.quit();
}

// E2E mode: NOCTURNE_E2E=<dir> drives the real renderer bridge -> IPC -> backend -> worker.
async function e2e(dir) {
  fs.mkdirSync(dir, { recursive: true });
  for (let i = 0; i < 240 && status.state !== "ready"; i++) await new Promise((r) => setTimeout(r, 500));
  const call = (method, p, body) => win.webContents.executeJavaScript(`window.nocturne.request(${JSON.stringify(method)}, ${JSON.stringify(p)}, ${JSON.stringify(body ?? null)})`);
  const out = { started: new Date().toISOString(), steps: [] };
  const rule = { side: "LONG", session: "ETH", horizon_bars: 24, max_trades_per_session: 1, stop: { type: "atr", value: 1.5 }, targets_r: [1, 2],
    conditions: [{ left: { indicator: "close" }, op: "crosses_above", right: { indicator: "vwap" } }, { left: { indicator: "rsi", params: { n: 14 } }, op: ">", right: 50 }] };
  const bt = await call("POST", "/v1/backtests", { name: "E2E VWAP reclaim + RSI", root: "NQ", interval: "1h", contracts: 2, costs: { slippage_ticks: 1 }, strategy: { type: "rule", rule } });
  const tr = await call("POST", "/v1/training-jobs", { name: "E2E ES compression LGBM", root: "ES", objective: "compression", model: "lightgbm", feature_families: ["price", "volatility"] });
  out.steps.push({ submit_backtest: bt.data, submit_training: tr.data });
  for (const [kind, job] of [["backtests", bt.data.job_id], ["training-jobs", tr.data.job_id]]) {
    let r;
    for (let i = 0; i < 600; i++) {
      r = await call("GET", `/v1/${kind}/${job}`);
      if (r.ok && !["QUEUED", "RUNNING"].includes(r.data.state)) break;
      await new Promise((res) => setTimeout(res, 1000));
    }
    out.steps.push({ kind, job, state: r.data.state, result: r.data.result });
  }
  await win.webContents.executeJavaScript(`location.hash = "#/backtests/${bt.data.job_id}"`);
  await new Promise((r) => setTimeout(r, 6000));
  fs.writeFileSync(path.join(dir, "e2e-backtest.png"), (await win.webContents.capturePage()).toPNG());
  await win.webContents.executeJavaScript(`location.hash = "#/models"`);
  await new Promise((r) => setTimeout(r, 3000));
  await win.webContents.executeJavaScript(`[...document.querySelectorAll("tr")].find((tr) => tr.textContent.includes("E2E ES compression"))?.click()`);
  await new Promise((r) => setTimeout(r, 5000));
  fs.writeFileSync(path.join(dir, "e2e-model.png"), (await win.webContents.capturePage()).toPNG());
  out.finished = new Date().toISOString();
  fs.writeFileSync(path.join(dir, "e2e.json"), JSON.stringify(out, null, 2));
  app.quit();
}

app.whenReady().then(() => {
  if (process.env.NOCTURNE_E2E) setTimeout(() => e2e(process.env.NOCTURNE_E2E), 0);
  createWindow();
  startBackend();
  if (process.env.NOCTURNE_QA) {
    win.webContents.once("did-finish-load", () => require("./qa.cjs")
      .run(win, (method, p, body) => request({ method, path: p, body }), process.env.NOCTURNE_QA, process.env.NOCTURNE_QA_OUT, () => status)
      .finally(() => app.quit()));
  }
  if (process.env.NOCTURNE_CAPTURE) {
    const consoleLog = fs.createWriteStream(path.join(process.env.NOCTURNE_CAPTURE, "..", "renderer-console.log"));
    win.webContents.on("console-message", (_e, level, message, line, source) => consoleLog.write(`[${level}] ${message} (${source}:${line})
`));
    win.webContents.once("did-finish-load", () => capture(process.env.NOCTURNE_CAPTURE));
  }
});
app.on("window-all-closed", () => { stopBackend(); app.quit(); });
app.on("before-quit", stopBackend);
