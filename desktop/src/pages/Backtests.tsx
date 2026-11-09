import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Download, Square } from "lucide-react";
import { useAction, useApi } from "@/lib/hooks";
import { ago, cn, num, pct, tone, usd } from "@/lib/format";
import { parseCsv } from "@/lib/csv";
import { Badge, Button, Panel, Progress, Query, Segmented, Stat, Table } from "@/components/ui";
import { Bars, TimeLine } from "@/components/charts";
import type { Job } from "@/lib/api";

const breakdownCols = [
  { key: "k", label: "Group" }, { key: "trades", label: "Trades", align: "right" as const },
  { key: "win_rate", label: "Win %", align: "right" as const, render: (r: any) => pct(r.win_rate) },
  { key: "profit_factor", label: "PF", align: "right" as const, render: (r: any) => num(r.profit_factor, 2) },
  { key: "expectancy", label: "Expect.", align: "right" as const, render: (r: any) => <span className={tone(r.expectancy)}>{usd(r.expectancy)}</span> },
  { key: "ci", label: "95% CI", align: "right" as const, render: (r: any) => r.expectancy_ci95 ? `${usd(r.expectancy_ci95[0])} … ${usd(r.expectancy_ci95[1])}` : "—" },
  { key: "net_pnl", label: "Net", align: "right" as const, render: (r: any) => <span className={tone(r.net_pnl)}>{usd(r.net_pnl)}</span> },
  { key: "max_drawdown", label: "Max DD", align: "right" as const, render: (r: any) => usd(r.max_drawdown) },
];

export default function Backtests() {
  const { id } = useParams();
  const navigate = useNavigate();
  const list = useApi<Job[]>("/v1/backtests", { refetchInterval: 3000 });
  const selected = id ?? list.data?.find((j) => j.state === "SUCCEEDED")?.job_id;
  return (
    <div className="grid min-h-full grid-cols-12 gap-3">
      <Panel title="Backtest runs" code="BT" className="col-span-3">
        <Query q={list}>{(rows) => rows.length ? (
          <div className="space-y-1">
            {rows.map((j) => (
              <button key={j.job_id} onClick={() => navigate(`/backtests/${j.job_id}`)}
                className={cn("w-full rounded-[3px] border px-2 py-1.5 text-left transition", selected === j.job_id ? "border-amber-500/60 bg-amber-500/5" : "border-ink-800 hover:border-ink-600")}>
                <div className="flex items-center gap-2 font-mono text-[11px]"><span className="flex-1 truncate text-ink-100">{j.name ?? j.job_id.slice(0, 8)}</span><Badge>{j.state}</Badge></div>
                <div className="mt-0.5 flex items-center gap-2 font-mono text-2xs text-ink-500">
                  <span>{j.config.root} · {j.config.interval} · {j.config.strategy?.type}</span><span className="ml-auto">{ago(j.created)}</span></div>
                {j.state === "RUNNING" && <div className="mt-1"><Progress value={j.progress?.percent ?? 2} /></div>}
                {j.result?.summary && <div className="mt-0.5 flex gap-2 font-mono text-2xs"><span className="text-ink-400">{j.result.summary.trades} trades</span>
                  <span className={tone(j.result.summary.net_pnl)}>{usd(j.result.summary.net_pnl)}</span><Badge className="ml-auto">{j.result.verdict}</Badge></div>}
              </button>
            ))}
          </div>
        ) : <div className="font-mono text-xs text-ink-400">No backtests yet. Build one in the Strategy Lab.</div>}</Query>
      </Panel>
      <div className="col-span-9">{selected ? <Detail id={selected} /> : <Panel title="Backtest" code="BT"><div className="font-mono text-xs text-ink-400">Select a run.</div></Panel>}</div>
    </div>
  );
}

function Detail({ id }: { id: string }) {
  const q = useApi<Job>(`/v1/backtests/${id}`, { refetchInterval: 3000 });
  const cancel = useAction(`/v1/jobs/${id}/cancel`, ["/v1/backtests"]);
  const [trades, setTrades] = useState<Record<string, string>[]>([]);
  const [outcome, setOutcome] = useState("ALL");
  const [group, setGroup] = useState<"era" | "year" | "session" | "regime">("era");
  const done = q.data?.state === "SUCCEEDED";
  useEffect(() => {
    let live = true;
    if (done) window.nocturne?.request("GET", `/v1/backtests/${id}/trades.csv`, undefined, true).then((r) => live && setTrades(r.ok ? parseCsv(String(r.data)) : []));
    return () => { live = false; };
  }, [id, done]);
  const filtered = useMemo(() => trades.filter((t) => outcome === "ALL" || (outcome === "WIN" ? Number(t.net) > 0 : outcome === "LOSS" ? Number(t.net) <= 0 : t.outcome === outcome)), [trades, outcome]);

  return (
    <Query q={q}>{(j) => {
      const r = j.report;
      if (!r) return (
        <Panel title={j.name ?? "Backtest"} code="BT" actions={(j.state === "RUNNING" || j.state === "QUEUED") && <Button size="sm" variant="danger" onClick={() => cancel.mutate({})}><Square className="h-3 w-3" />Cancel</Button>}>
          <div className="space-y-2 font-mono text-xs text-ink-300"><Badge>{j.state}</Badge><Progress value={j.progress?.percent ?? 1} /><div>{j.progress?.message ?? "Waiting for worker"}</div>
            {j.result?.reason && <div className="text-down">{j.result.reason} {(j.result.errors ?? []).join(" · ")}</div>}</div>
        </Panel>
      );
      const s = r.summary;
      const groups: Record<string, any> = { era: r.by_era, year: r.by_year, session: r.by_session, regime: r.by_regime };
      return (
        <div className="grid grid-cols-12 gap-3">
          <Panel title={`${j.name ?? "Backtest"} — ${r.config.root} ${r.config.interval}`} code="BT" className="col-span-12"
            actions={<>
              <Badge>{r.verdict}</Badge>
              <Button size="sm" variant="outline" onClick={() => window.nocturne?.saveFile(`${(j.name ?? id).replaceAll(" ", "_")}_report.json`, JSON.stringify(r, null, 2))}><Download className="h-3 w-3" />Report</Button>
              <Button size="sm" variant="outline" onClick={async () => { const t = await window.nocturne!.request("GET", `/v1/backtests/${id}/trades.csv`, undefined, true); if (t.ok) window.nocturne!.saveFile(`${(j.name ?? id).replaceAll(" ", "_")}_trades.csv`, String(t.data)); }}><Download className="h-3 w-3" />Trades CSV</Button>
            </>}>
            <div className="grid grid-cols-9 gap-2">
              <Stat label="Trades" value={s.trades} sub={`${s.wins}W / ${s.losses}L`} />
              <Stat label="Win rate" value={pct(s.win_rate)} sub={`loss ${pct(s.loss_rate)}`} />
              <Stat label="Profit factor" value={num(s.profit_factor, 2)} valueClass={s.profit_factor >= 1 ? "text-up" : "text-down"} />
              <Stat label="Net P&L" value={usd(s.net_pnl)} valueClass={tone(s.net_pnl)} sub={`gross ${usd(s.gross_pnl)} · costs ${usd(s.costs)}`} />
              <Stat label="Expectancy" value={usd(s.expectancy)} valueClass={tone(s.expectancy)} sub={s.expectancy_ci95 ? `95% ${usd(s.expectancy_ci95[0])}…${usd(s.expectancy_ci95[1])}` : ""} />
              <Stat label="Max drawdown" value={usd(s.max_drawdown)} valueClass="text-down" />
              <Stat label="Avg / median pts" value={`${num(s.avg_points, 1)} / ${num(s.median_points, 1)}`} sub={`best ${num(s.largest_win_points, 1)} · worst ${num(s.largest_loss_points, 1)}`} />
              <Stat label="TP1 / TP2 / TP3" value={s.tp1_hit_rate != null ? `${pct(s.tp1_hit_rate, 0)}/${pct(s.tp2_hit_rate, 0)}/${pct(s.tp3_hit_rate, 0)}` : "—"} sub={`target touched ${pct(s.target_hit_rate)}`} />
              <Stat label="Target touched" value={pct(s.target_hit_rate)} sub={`stop-first ${pct(s.stop_first_rate)} · timeout ${pct(s.timeout_rate)} · ${num(s.avg_bars_held, 1)} bars`} />
            </div>
            <div className="mt-2 flex flex-wrap gap-3 font-mono text-2xs text-ink-500">
              <span>{r.bars} bars · {r.first_bar} → {r.last_bar}</span><span>{r.position}</span><span>MFE {num(s.avg_mfe_points, 1)} / MAE {num(s.avg_mae_points, 1)} pts avg</span>
              <span className="text-warn">{r.scope}</span></div>
          </Panel>
          <Panel title="Equity curve (net, per position)" code="EQ" className="col-span-8" bodyClass="p-1">
            {r.equity_curve?.length ? <TimeLine height={230} baseline={0} series={[{ name: "equity", points: r.equity_curve.map((p: any) => ({ t: Math.floor(new Date(p.time).getTime() / 1000), v: p.equity })) }]} /> : <div className="p-3 font-mono text-xs text-ink-400">No trades.</div>}
          </Panel>
          <Panel title="Slippage stress" code="SLIP" className="col-span-4">
            <Table dense rows={Object.entries(r.slippage_stress).map(([k, v]: any) => ({ k: `${k} ticks`, ...v }))} columns={breakdownCols.slice(0, 7)} />
          </Panel>
          <Panel title="Monthly net P&L" code="MTH" className="col-span-6">
            <Bars signed height={150} data={Object.entries(r.by_month ?? {}).map(([m, v]: any) => ({ label: m.slice(2), value: v }))} format={(v) => usd(v)} />
          </Panel>
          <Panel title="Points distribution" code="DIST" className="col-span-6">
            <Bars height={150} data={(r.points_histogram ?? []).map((v: number, i: number) => ({ label: num(r.points_bins[i], 0), value: v }))} />
          </Panel>
          <Panel title="Breakdown" code="BRK" className="col-span-12" actions={<Segmented value={group} options={["era", "year", "session", "regime"] as const} onChange={setGroup} />}>
            <Table dense rows={Object.entries(groups[group] ?? {}).map(([k, v]: any) => ({ k, ...v }))} columns={breakdownCols} />
            {group === "era" && <div className="mt-2 font-mono text-2xs text-ink-500">Chronological split by trade order: development 50% · validation 25% · holdout 25%. A candidate needs positive 95% lower bounds in development and holdout with ≥100 trades.</div>}
          </Panel>
          <Panel title={`Trade ledger (${filtered.length})`} code="LEDG" className="col-span-12"
            actions={<Segmented value={outcome} options={["ALL", "WIN", "LOSS", "STOP", "TIMEOUT"] as const} onChange={setOutcome} />}>
            <Table dense maxRows={400} rows={filtered} columns={[
              { key: "entry_time", label: "Entry (UTC)", render: (t) => t.entry_time.slice(0, 16) }, { key: "session", label: "Sess" }, { key: "side", label: "Side", render: (t) => <span className={t.side === "LONG" ? "text-up" : "text-down"}>{t.side}</span> },
              { key: "entry", label: "Entry", align: "right", render: (t) => num(Number(t.entry), 2) }, { key: "stop", label: "Stop", align: "right", render: (t) => num(Number(t.stop), 2) },
              { key: "tp1", label: "TP1", align: "right", render: (t) => num(Number(t.tp1), 2) }, { key: "tp2", label: "TP2", align: "right", render: (t) => t.tp2 ? num(Number(t.tp2), 2) : "—" },
              { key: "exit", label: "Exit", align: "right", render: (t) => num(Number(t.exit), 2) }, { key: "outcome", label: "Outcome", render: (t) => <Badge tone={Number(t.net) > 0 ? "up" : "down"}>{t.outcome}</Badge> },
              { key: "bars_held", label: "Bars", align: "right" }, { key: "points", label: "Pts", align: "right", render: (t) => <span className={tone(Number(t.points))}>{num(Number(t.points), 2)}</span> },
              { key: "mfe_points", label: "MFE", align: "right", render: (t) => num(Number(t.mfe_points), 1) }, { key: "mae_points", label: "MAE", align: "right", render: (t) => num(Number(t.mae_points), 1) },
              { key: "costs", label: "Costs", align: "right", render: (t) => usd(Number(t.costs)) }, { key: "net", label: "Net", align: "right", render: (t) => <span className={tone(Number(t.net))}>{usd(Number(t.net))}</span> }]} />
          </Panel>
        </div>
      );
    }}</Query>
  );
}
