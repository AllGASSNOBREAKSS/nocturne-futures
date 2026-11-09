import { useEffect, useMemo, useState } from "react";
import { parseCsv } from "@/lib/csv";
import type { SeriesMarker, Time } from "lightweight-charts";
import { useApi } from "@/lib/hooks";
import { cn, num, when } from "@/lib/format";
import { Badge, Dot, Panel, Query, Segmented, Select, Table } from "@/components/ui";
import { PriceChart, TimeLine } from "@/components/charts";
import type { Bar, Job, Level, Root } from "@/lib/api";

const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"] as const;
const OVERLAYS = [
  { id: "vwap", label: "VWAP" }, { id: "sma:20", label: "SMA 20" }, { id: "sma:50", label: "SMA 50" }, { id: "sma:200", label: "SMA 200" },
  { id: "ema:21", label: "EMA 21" }, { id: "bb_upper:20:2", label: "BB up" }, { id: "bb_lower:20:2", label: "BB low" },
];
const OSC = [{ id: "rsi:14", label: "RSI 14" }, { id: "adx:14", label: "ADX 14" }, { id: "atr:14", label: "ATR 14" }, { id: "macd_hist:12:26:9", label: "MACD hist" }];

export default function Market() {
  const [root, setRoot] = useState<Root>("NQ");
  const [interval, setInterval] = useState<(typeof INTERVALS)[number]>("5m");
  const [overlays, setOverlays] = useState<string[]>(["vwap", "sma:50"]);
  const [osc, setOsc] = useState("rsi:14");
  const [showLevels, setShowLevels] = useState(true);
  const [tradeJob, setTradeJob] = useState("");
  const limit = interval === "1m" ? 2000 : interval === "1d" || interval === "1w" ? 1500 : 1200;
  const bars = useApi<{ bars: Bar[]; meta: any }>(`/v1/markets/${root}/bars?interval=${interval}&limit=${limit}`);
  const ind = useApi<{ series: Record<string, { t: number; v: number }[]> }>(
    `/v1/markets/${root}/indicators?interval=${interval}&limit=${limit}&names=${[...overlays, osc].join(",") || "close"}`);
  const levels = useApi<{ levels: Level[]; last_price: number; as_of: string }>(`/v1/levels/${root}`);
  const regime = useApi<any>(`/v1/markets/${root}/regime`);
  const sessions = useApi<any>(`/v1/markets/${root}/sessions`);
  const backtests = useApi<Job[]>("/v1/backtests");

  const overlaySeries = useMemo(() => Object.fromEntries(overlays.map((o) => [o, ind.data?.series?.[o] ?? []]).filter(([, s]) => (s as any[]).length)), [ind.data, overlays]);
  const tradeRows = useTrades(tradeJob);
  const tradeMarkers = useMemo<SeriesMarker<Time>[]>(() => tradeRows.flatMap((t) => [
    { time: Math.floor(new Date(t.entry_time).getTime() / 1000) as Time, position: t.side === "LONG" ? "belowBar" : "aboveBar", color: t.side === "LONG" ? "#2ee6a6" : "#ff4d6a", shape: t.side === "LONG" ? "arrowUp" : "arrowDown", text: t.side[0] },
    { time: Math.floor(new Date(t.exit_time).getTime() / 1000) as Time, position: "inBar", color: Number(t.net) > 0 ? "#ffab00" : "#8592a3", shape: "circle", text: t.outcome },
  ] as SeriesMarker<Time>[]), [tradeRows]);
  const eligible = (backtests.data ?? []).filter((j) => j.state === "SUCCEEDED" && j.config.root === root);

  return (
    <div className="grid h-full min-h-[860px] grid-cols-12 grid-rows-[1fr_220px] gap-3">
      <Panel title={`${root} continuous front-month · ${interval}`} code="GP" className="col-span-9" bodyClass="flex flex-col p-0"
        actions={<>
          <Segmented value={root} options={["NQ", "ES"] as const} onChange={(v) => { setRoot(v); setTradeJob(""); }} />
          <Segmented value={interval} options={INTERVALS} onChange={setInterval} />
        </>}>
        <div className="flex flex-wrap items-center gap-1.5 border-b border-ink-800 px-3 py-1.5">
          {OVERLAYS.map((o) => (
            <button key={o.id} onClick={() => setOverlays((s) => s.includes(o.id) ? s.filter((x) => x !== o.id) : [...s, o.id])}
              className={cn("rounded-[2px] border px-1.5 py-0.5 font-mono text-2xs uppercase tracking-wider transition",
                overlays.includes(o.id) ? "border-amber-500/50 bg-amber-500/10 text-amber-300" : "border-ink-700 text-ink-400 hover:text-ink-200")}>{o.label}</button>
          ))}
          <label className="ml-2 flex items-center gap-1 font-mono text-2xs text-ink-300"><input type="checkbox" checked={showLevels} onChange={(e) => setShowLevels(e.target.checked)} />LEVELS</label>
          <Select className="ml-auto h-6 w-[260px] text-2xs" value={tradeJob} onChange={(e) => setTradeJob(e.target.value)}>
            <option value="">Overlay backtest trades…</option>
            {eligible.map((j) => <option key={j.job_id} value={j.job_id}>{j.name ?? j.job_id.slice(0, 8)} · {j.config.interval} · {j.result?.summary?.trades} trades</option>)}
          </Select>
        </div>
        <div className="min-h-0 flex-1">
          <Query q={bars} label="Loading bars">{(d) => <PriceChart bars={d.bars} overlays={overlaySeries} levels={showLevels ? levels.data?.levels ?? [] : []} markers={tradeMarkers} />}</Query>
        </div>
        <div className="flex items-center gap-3 border-t border-ink-800 px-3 py-1 font-mono text-2xs text-ink-500">
          <span>{bars.data?.meta?.dataset}</span><span>retrieved {when(bars.data?.meta?.retrieved_at)}</span>
          <Badge tone="warn">{bars.data?.meta?.freshness ?? "HISTORICAL"}</Badge><span className="ml-auto">times in America/New_York · bars available at close</span>
        </div>
      </Panel>
      <div className="col-span-3 row-span-2 flex min-h-0 flex-col gap-3">
        <Panel title="Levels" code="LVL" className="flex-1">
          <Query q={levels}>{(d) => (
            <div className="space-y-0.5">
              {d.levels.map((l) => (
                <div key={l.name} className="flex items-center gap-2 py-0.5 font-mono text-[11px]" title={l.basis}>
                  <Dot tone={l.kind === "auction" ? "info" : l.kind === "session" ? "amber" : "muted"} />
                  <span className="flex-1 truncate text-ink-300">{l.name}</span>
                  <span className={cn("tabular-nums", l.price >= d.last_price ? "text-up" : "text-down")}>{num(l.price, 2)}</span>
                </div>
              ))}
              <div className="pt-1 font-mono text-2xs text-ink-500">POC/VAH/VAL: bar approximation, not traded volume-at-price.</div>
            </div>
          )}</Query>
        </Panel>
        <Panel title="Regime" code="RGM">
          <Query q={regime}>{(r) => (
            <div className="space-y-2 font-mono text-[11px]">
              <div className="flex gap-1.5"><Badge>{r.state}</Badge><Badge tone={r.trend === "UPTREND" ? "up" : r.trend === "DOWNTREND" ? "down" : "warn"}>{r.trend}</Badge></div>
              <div className="grid grid-cols-2 gap-1 text-ink-300">
                <span>ATR20</span><span className="text-right text-ink-100">{num(r.atr20, 1)}</span>
                <span>SMA50</span><span className="text-right text-ink-100">{num(r.sma50, 1)}</span>
                <span>SMA200</span><span className="text-right text-ink-100">{num(r.sma200, 1)}</span>
                <span>VIX</span><span className="text-right text-ink-100">{num(r.vix?.value, 2)}</span>
              </div>
            </div>
          )}</Query>
        </Panel>
        <Panel title="Session ranges (last 5)" code="SESS">
          <Query q={sessions}>{(s) => (
            <Table dense rows={[...s.sessions].reverse().slice(0, 15)} columns={[
              { key: "session_date", label: "Date" }, { key: "session", label: "Session" },
              { key: "range", label: "Range", align: "right", render: (r) => num(r.range, 1) }]} />
          )}</Query>
        </Panel>
      </div>
      <Panel title="Oscillator" code="OSC" className="col-span-9" bodyClass="p-0"
        actions={<Segmented value={osc} options={OSC.map((o) => ({ value: o.id, label: o.label }))} onChange={setOsc} />}>
        <Query q={ind}>{(d) => <TimeLine area={false} height={175} series={[{ name: osc, points: d.series[osc] ?? [], color: "#39c5ff" }]} />}</Query>
      </Panel>
    </div>
  );
}

function useTrades(jobId: string) {
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  useEffect(() => {
    let live = true;
    if (!jobId) { setRows([]); return; }
    window.nocturne?.request("GET", `/v1/backtests/${jobId}/trades.csv`, undefined, true)
      .then((r) => { if (live) setRows(r.ok ? parseCsv(String(r.data)) : []); });
    return () => { live = false; };
  }, [jobId]);
  return rows;
}
