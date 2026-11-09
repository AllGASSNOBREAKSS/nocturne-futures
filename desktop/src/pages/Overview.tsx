import { useNavigate } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { ago, cn, num, pct, when } from "@/lib/format";
import { Badge, Button, Dot, KV, Panel, Query, Stat, Table } from "@/components/ui";
import { PriceChart } from "@/components/charts";
import type { Bar, Job, Level } from "@/lib/api";

function RegimeCard({ root }: { root: "NQ" | "ES" }) {
  const q = useApi<any>(`/v1/markets/${root}/regime`);
  return (
    <Panel title={`${root} regime`} code={root}>
      <Query q={q}>{(r) => (
        <div className="space-y-2">
          <div className="grid grid-cols-3 gap-2">
            <Stat label="Last settle" value={num(r.close, 2)} sub={when(r.as_of)} />
            <Stat label="ATR 20" value={num(r.atr20, 1)} sub={`last range ${num(r.last_range, 1)}`} />
            <Stat label="Range pctl" value={pct(r.range_percentile_250, 0)} sub="vs 250 sessions" />
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge tone={r.state === "EXPANSION" ? "down" : r.state === "COMPRESSION" ? "info" : "muted"}>{r.state}</Badge>
            <Badge tone={r.trend === "UPTREND" ? "up" : r.trend === "DOWNTREND" ? "down" : "warn"}>{r.trend}</Badge>
            {r.vix && <Badge tone={r.vix.value > 25 ? "down" : r.vix.value < 15 ? "up" : "warn"}>VIX {num(r.vix.value, 2)}</Badge>}
            <span className="ml-auto font-mono text-2xs text-ink-500">rule-based descriptive regime</span>
          </div>
        </div>
      )}</Query>
    </Panel>
  );
}

export default function Overview() {
  const navigate = useNavigate();
  const bars = useApi<{ bars: Bar[]; meta: any }>("/v1/markets/NQ/bars?interval=1h&limit=360");
  const levels = useApi<{ levels: Level[]; last_price: number; as_of: string }>("/v1/levels/NQ");
  const forecasts = useApi<any>("/v1/forecasts/sessions?root=NQ");
  const research = useApi<any>("/v1/research");
  const backtests = useApi<Job[]>("/v1/backtests", { refetchInterval: 8000 });
  const training = useApi<Job[]>("/v1/training-jobs", { refetchInterval: 8000 });
  const ops = useApi<any>("/v1/operations");
  const recent = [...(backtests.data ?? []), ...(training.data ?? [])].sort((a, b) => b.created.localeCompare(a.created)).slice(0, 8);
  const latest = forecasts.data?.forecasts?.at(-1);

  return (
    <div className="grid h-full min-h-[880px] grid-cols-12 grid-rows-[auto_1fr_1fr] gap-3">
      <div className="col-span-12 grid grid-cols-2 gap-3"><RegimeCard root="NQ" /><RegimeCard root="ES" /></div>
      <Panel title="NQ continuous — 1H" code="GP" className="col-span-8" bodyClass="p-0"
        actions={<Button size="sm" variant="ghost" onClick={() => navigate("/market")}>Open chart <ArrowUpRight className="h-3 w-3" /></Button>}>
        <Query q={bars}>{(d) => <PriceChart bars={d.bars} levels={(levels.data?.levels ?? []).filter((l) => ["Prior session high", "Prior session low", "Prior POC"].includes(l.name))} />}</Query>
      </Panel>
      <Panel title="Key levels — NQ" code="LVL" className="col-span-4">
        <Query q={levels}>{(d) => (
          <div className="space-y-1">
            {d.levels.map((l) => {
              const dist = l.price - d.last_price;
              return (
                <div key={l.name} className="flex items-center gap-2 border-b border-ink-800 py-1 font-mono text-[11px]">
                  <Dot tone={l.kind === "auction" ? "info" : l.kind === "session" ? "amber" : "muted"} />
                  <span className="flex-1 truncate text-ink-200">{l.name}</span>
                  <span className="tabular-nums text-ink-100">{num(l.price, 2)}</span>
                  <span className={cn("w-16 text-right tabular-nums", dist >= 0 ? "text-up" : "text-down")}>{dist >= 0 ? "+" : ""}{num(dist, 1)}</span>
                </div>
              );
            })}
            <div className="pt-1 font-mono text-2xs text-ink-500">Last {num(d.last_price, 2)} · as of {when(d.as_of)}</div>
          </div>
        )}</Query>
      </Panel>
      <Panel title="Next-session range forecast — NQ" code="PRED" className="col-span-4"
        actions={<Button size="sm" variant="ghost" onClick={() => navigate("/predictions")}>Center <ArrowUpRight className="h-3 w-3" /></Button>}>
        <Query q={forecasts}>{() => latest ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 font-mono text-2xs text-ink-400">TARGET <span className="text-ink-100">{latest.target_session}</span><Badge tone="research">{latest.validation_status}</Badge></div>
            <Table dense columns={[{ key: "s", label: "Session" }, { key: "p50", label: "P50", align: "right" }, { key: "p80", label: "P80", align: "right" }, { key: "p90", label: "P90", align: "right" }]}
              rows={Object.entries(latest.quantiles_points).map(([s, q]: any) => ({ s, p50: num(q.p50, 0), p80: num(q.p80, 0), p90: num(q.p90, 0) }))} />
            <div className="font-mono text-2xs text-ink-500">Range in points · issued {ago(latest.issued_at)} · direction withheld (no validated model)</div>
          </div>
        ) : <div className="font-mono text-xs text-ink-400">No session forecast issued yet. Open the Prediction Center to issue one.</div>}</Query>
      </Panel>
      <Panel title="Research verdicts" code="RSCH" className="col-span-4">
        <Query q={research}>{(r) => {
          const nq = r.phase3v?.NQ?.tasks ?? {};
          return (
            <div className="space-y-1.5">
              {Object.entries(nq).map(([task, cfgs]: any) => {
                const best = cfgs.price_logit ?? Object.values(cfgs)[0];
                return (
                  <div key={task} className="flex items-center gap-2 font-mono text-[11px]">
                    <span className="flex-1 truncate text-ink-200">{task.replaceAll("_", " ")}</span>
                    <Badge>{best?.verdict}</Badge>
                  </div>
                );
              })}
              <div className="mt-2 flex items-center gap-2 border-t border-ink-800 pt-2 font-mono text-[11px]">
                <span className="flex-1 text-ink-200">Ranked signals accepted</span>
                <span className="text-down">{r.signal_ranking?.accepted ?? 0} / {r.signal_ranking?.candidates ?? 0}</span>
              </div>
            </div>
          );
        }}</Query>
      </Panel>
      <Panel title="Recent research jobs" code="JOBS" className="col-span-4">
        {recent.length ? (
          <Table dense rows={recent} onRow={(j) => navigate(j.kind === "STUDIO_BACKTEST" ? `/backtests/${j.job_id}` : "/models")}
            columns={[{ key: "kind", label: "Type", render: (j) => j.kind === "STUDIO_BACKTEST" ? "BACKTEST" : "TRAINING" },
              { key: "name", label: "Name", render: (j) => <span className="text-ink-100">{j.name ?? j.job_id.slice(0, 8)}</span> },
              { key: "state", label: "State", render: (j) => <Badge>{j.state}</Badge> },
              { key: "v", label: "Verdict", render: (j) => j.result?.verdict ? <Badge>{j.result.verdict}</Badge> : "—" }]} />
        ) : <div className="font-mono text-xs text-ink-400">No jobs yet. Start one from ML Model Studio or the Strategy Lab.</div>}
        <Query q={ops}>{(o) => (
          <div className="mt-3 border-t border-ink-800 pt-2">
            <KV items={[["Datasets", `${o.datasets.filter((d: any) => d.status === "AVAILABLE").length} available`],
              ["Databento", <Badge key="db" tone="down">BLOCKED</Badge>],
              ...o.scheduler.map((s: any) => [s.name.replace("Nocturne-", ""), s["Last Result"] !== undefined ? `last ${s["Last Result"]}` : s.status] as [string, string])]} />
          </div>
        )}</Query>
      </Panel>
    </div>
  );
}
