import { AnimatePresence, motion } from "framer-motion";
import { Activity, BarChart3, Binary, BrainCircuit, CandlestickChart, Command, Crosshair, FlaskConical, Gauge, Globe2, LayoutDashboard, Server, Target, Rocket } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useApi, useBackendStatus, useClock } from "@/lib/hooks";
import { cn, num, ago } from "@/lib/format";
import { Dot } from "./ui";
import { ErrorBoundary } from "./ErrorBoundary";

export const NAV = [
  { to: "/", code: "PRED", label: "Predict", icon: Crosshair, key: "F1", primary: true },
  { to: "/market", code: "CHART", label: "Chart", icon: CandlestickChart, key: "F2", primary: true },
  { to: "/test", code: "TEST", label: "Backtest", icon: Rocket, key: "F3", primary: true },
  { to: "/models", code: "ML", label: "Models", icon: BrainCircuit, key: "F4", primary: true },
  { to: "/ops", code: "DATA", label: "Data & status", icon: Server, key: "F5", primary: true },
  { to: "/backtests", code: "BT", label: "Backtest results", icon: BarChart3, key: "F6" },
  { to: "/signals", code: "SIG", label: "Signal ranking", icon: Target, key: "F7" },
  { to: "/performance", code: "PERF", label: "Model accuracy", icon: Gauge, key: "F8" },
  { to: "/intel", code: "INTL", label: "Macro & news", icon: Globe2, key: "F9" },
  { to: "/overview", code: "OVR", label: "Overview", icon: LayoutDashboard, key: "F10" },
  { to: "/predictions", code: "SESS", label: "Session forecasts", icon: Activity, key: "F11" },
  { to: "/lab", code: "RULE", label: "Rule builder", icon: FlaskConical, key: "F12" },
];

function Clock({ zone, label }: { zone: string; label: string }) {
  const now = useClock();
  const t = now.toLocaleTimeString("en-GB", { timeZone: zone, hour12: false });
  return (
    <div className="flex items-baseline gap-1.5 font-mono">
      <span className="text-2xs tracking-widest text-ink-500">{label}</span>
      <span className="text-[11px] tabular-nums text-ink-200">{t}</span>
    </div>
  );
}

function Ticker({ root }: { root: "NQ" | "ES" }) {
  const live = useApi<any>(`/v1/live/${root}/quote`, { refetchInterval: 60_000 });
  const arc = useApi<any>(live.error ? `/v1/markets/${root}/regime` : null, { refetchInterval: 120_000 });
  const d = live.data;
  return (
    <div className="flex items-center gap-2 border-l border-ink-700 pl-3 font-mono" title={d ? `Delayed free quote · last bar ${d.last_bar}` : "Archive close (live quote unavailable)"}>
      <span className="text-[11px] font-semibold text-amber-500">{root}1!</span>
      <span className="text-[12px] tabular-nums text-ink-100">{d ? num(d.price, 2) : arc.data ? num(arc.data.close, 2) : "—"}</span>
      {d?.change != null && <span className={cn("text-2xs tabular-nums", d.change >= 0 ? "text-up" : "text-down")}>{d.change >= 0 ? "+" : ""}{num(d.change, 2)} ({d.change >= 0 ? "+" : ""}{num(d.change_pct, 2)}%)</span>}
      {!d && arc.data && <span className="text-2xs text-ink-500">archive</span>}
    </div>
  );
}

function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const items = useMemo(() => NAV.filter((n) => `${n.code} ${n.label}`.toLowerCase().includes(query.toLowerCase())), [query]);
  useEffect(() => { if (open) setQuery(""); }, [open]);
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[14vh] backdrop-blur-[2px]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
          <motion.div onClick={(e) => e.stopPropagation()} initial={{ y: -10, scale: 0.98 }} animate={{ y: 0, scale: 1 }} exit={{ y: -10, opacity: 0 }}
            className="w-[560px] overflow-hidden rounded border border-amber-500/40 bg-ink-850 shadow-2xl shadow-black">
            <div className="flex items-center gap-2 border-b border-ink-700 px-3">
              <Command className="h-4 w-4 text-amber-500" />
              <input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Type a function code: OVR, MKT, ML, BT…"
                onKeyDown={(e) => { if (e.key === "Enter" && items[0]) { navigate(items[0].to); onClose(); } if (e.key === "Escape") onClose(); }}
                className="h-11 flex-1 bg-transparent font-mono text-sm text-ink-100 outline-none placeholder:text-ink-500" />
              <kbd className="font-mono text-2xs text-ink-500">ESC</kbd>
            </div>
            <div className="max-h-80 overflow-auto p-1">
              {items.map((n) => (
                <button key={n.to} onClick={() => { navigate(n.to); onClose(); }} className="flex w-full items-center gap-3 rounded px-3 py-2 text-left hover:bg-amber-500/10">
                  <n.icon className="h-4 w-4 text-ink-300" />
                  <span className="w-12 font-mono text-xs font-semibold text-amber-500">{n.code}</span>
                  <span className="font-sans text-sm text-ink-100">{n.label}</span>
                  <span className="ml-auto font-mono text-2xs text-ink-500">{n.key}</span>
                </button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const status = useBackendStatus();
  const location = useLocation();
  const navigate = useNavigate();
  const [palette, setPalette] = useState(false);
  const ready = status.state === "ready";
  const health = useApi<any>(ready ? "/v1/system/health" : null, { refetchInterval: 10_000 });
  const jobs = useApi<any[]>(ready ? "/v1/backtests" : null, { refetchInterval: 8_000 });
  const training = useApi<any[]>(ready ? "/v1/training-jobs" : null, { refetchInterval: 8_000 });
  const running = [...(jobs.data ?? []), ...(training.data ?? [])].filter((j) => j.state === "RUNNING" || j.state === "QUEUED").length;
  const current = NAV.find((n) => (n.to === "/" ? location.pathname === "/" : location.pathname.startsWith(n.to))) ?? NAV[0];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((p) => !p); }
      const index = /^F(\d{1,2})$/.exec(e.key);
      if (index && NAV[Number(index[1]) - 1]) { e.preventDefault(); navigate(NAV[Number(index[1]) - 1].to); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-ink-950 bg-[radial-gradient(ellipse_at_top,rgba(255,171,0,0.05),transparent_55%)]">
      <header className="drag flex h-[38px] shrink-0 items-center gap-4 border-b border-ink-700/80 bg-ink-950 pl-3 pr-[150px]">
        <div className="flex items-center gap-2">
          <div className="grid h-5 w-5 place-items-center rounded-[3px] bg-amber-500 shadow-[0_0_14px_-2px_rgba(255,171,0,0.8)]"><Binary className="h-3.5 w-3.5 text-ink-950" /></div>
          <span className="font-mono text-[12px] font-bold tracking-[0.28em] text-ink-100">NOCTURNE</span>
          <span className="font-mono text-2xs tracking-widest text-ink-500">QUANT TERMINAL</span>
        </div>
        <button onClick={() => setPalette(true)} className="no-drag flex h-6 w-[300px] items-center gap-2 rounded-[3px] border border-ink-700 bg-ink-900 px-2 text-left font-mono text-2xs text-ink-500 hover:border-amber-500/50">
          <span className="font-semibold text-amber-500">{current.code}</span><span className="text-ink-300">{current.label}</span>
          <span className="ml-auto">CTRL K</span>
        </button>
        {ready && <><Ticker root="NQ" /><Ticker root="ES" /></>}
        <div className="ml-auto flex items-center gap-4">
          <Clock zone="America/New_York" label="NY" /><Clock zone="Europe/London" label="LDN" /><Clock zone="Asia/Tokyo" label="TKY" />
        </div>
      </header>
      <div className="flex min-h-0 flex-1">
        <nav className="flex w-[58px] shrink-0 flex-col items-center gap-0.5 border-r border-ink-700/80 bg-ink-950 py-2">
          {NAV.map((n, i) => (<div key={n.to} className="contents">
            {i === 5 && <div className="my-1 w-8 border-t border-ink-700" title="More research views" />}
            <NavLink to={n.to} end={n.to === "/"} title={`${n.label} (${n.key})`}
              className={({ isActive }) => cn("group relative flex w-12 flex-col items-center justify-center gap-0.5 rounded-[3px] transition-colors", n.primary ? "h-12" : "h-9 opacity-70 hover:opacity-100",
                isActive ? "bg-amber-500/10 text-amber-400" : "text-ink-400 hover:bg-ink-800 hover:text-ink-100")}>
              {({ isActive }) => (<>
                {isActive && <motion.span layoutId="rail" className="absolute left-[-5px] top-2 h-7 w-[3px] rounded-r bg-amber-500" />}
                <n.icon className="h-4 w-4" />
                <span className="font-mono text-[8.5px] font-semibold tracking-wider">{n.code}</span>
              </>)}
            </NavLink>
          </div>))}
        </nav>
        <main className="min-w-0 flex-1 overflow-hidden">
          {ready ? (
            <AnimatePresence mode="wait">
              <motion.div key={location.pathname} className="h-full overflow-auto p-3" initial={{ opacity: 0, x: 6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -6 }} transition={{ duration: 0.16 }}>
                <ErrorBoundary resetKey={location.pathname}>{children}</ErrorBoundary>
              </motion.div>
            </AnimatePresence>
          ) : <Boot status={status} />}
        </main>
      </div>
      <footer className="flex h-6 shrink-0 items-center gap-4 border-t border-ink-700/80 bg-ink-950 px-3 font-mono text-2xs text-ink-400">
        <span className="flex items-center gap-1.5"><Dot tone={ready ? "up" : status.state === "error" ? "down" : "warn"} pulse={!ready} />BACKEND {status.state.toUpperCase()}</span>
        <span className="flex items-center gap-1.5"><Dot tone={health.data?.worker?.alive ? "up" : "muted"} />WORKER {health.data?.worker?.alive ? "ALIVE" : "—"}</span>
        <span className="flex items-center gap-1.5"><Activity className="h-3 w-3" />{running} JOB{running === 1 ? "" : "S"} ACTIVE</span>
        <span>REFRESH {health.data?.refresh?.state ?? "IDLE"}{health.data?.refresh?.finished_at ? ` · ${ago(health.data.refresh.finished_at)}` : ""}</span>
        <span className="ml-auto text-warn">HISTORICAL / DELAYED DATA — NOT REAL-TIME</span>
        <span className="text-ink-300">RESEARCH ONLY · NO_TRADE · NO BROKER</span>
        <span className="text-ink-500" title="Charts: TradingView Lightweight Charts (Apache-2.0), https://www.tradingview.com/">CHARTS © TRADINGVIEW LWC</span>
        <span className="text-ink-500">v{health.data?.version ?? "—"}</span>
      </footer>
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  );
}

function Boot({ status }: { status: { state: string; detail: string } }) {
  return (
    <div className="grid h-full place-items-center">
      <div className="w-[420px] text-center">
        <div className="mx-auto mb-5 grid h-12 w-12 place-items-center rounded bg-amber-500 shadow-[0_0_40px_-6px_rgba(255,171,0,0.8)]"><Binary className="h-7 w-7 text-ink-950" /></div>
        <div className="font-mono text-sm font-bold tracking-[0.4em] text-ink-100">NOCTURNE</div>
        <div className="relative mx-auto mt-5 h-[2px] w-56 overflow-hidden rounded bg-ink-700">
          {status.state !== "error" && <div className="absolute inset-y-0 w-1/3 animate-scan bg-amber-500" />}
        </div>
        <div className={cn("mt-4 font-mono text-xs", status.state === "error" ? "text-down" : "text-ink-300")}>{status.detail}</div>
        {status.state === "error" && <button onClick={() => window.nocturne?.revealLog()} className="mt-3 font-mono text-2xs text-amber-400 underline">Open backend log</button>}
      </div>
    </div>
  );
}
