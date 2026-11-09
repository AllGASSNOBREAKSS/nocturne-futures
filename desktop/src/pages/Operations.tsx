import { RefreshCw, Square } from "lucide-react";
import { useAction, useApi } from "@/lib/hooks";
import { ago, num, when } from "@/lib/format";
import { Badge, Button, Dot, KV, Panel, Query, Table } from "@/components/ui";
import type { Job } from "@/lib/api";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";

export default function Operations() {
  const ops = useApi<any>("/v1/operations", { refetchInterval: 30_000 });
  const health = useApi<any>("/v1/system/health", { refetchInterval: 5000 });
  const backtests = useApi<Job[]>("/v1/backtests", { refetchInterval: 5000 });
  const training = useApi<Job[]>("/v1/training-jobs", { refetchInterval: 5000 });
  const refresh = useAction<any>("/v1/data/refresh", ["/v1/system", "/v1/data"]);
  const client = useQueryClient();
  const jobs = [...(backtests.data ?? []), ...(training.data ?? [])].sort((a, b) => b.created.localeCompare(a.created));
  const cancel = async (id: string) => { await api.post(`/v1/jobs/${id}/cancel`); client.invalidateQueries(); };

  return (
    <Query q={ops}>{(o) => (
      <div className="grid min-h-full grid-cols-12 gap-3">
        <Panel title="System" code="SYS" className="col-span-4">
          <KV items={[["Backend", health.data?.status], ["Version", health.data?.version], ["Mode", health.data?.mode], ["Worker", health.data?.worker?.alive ? "ALIVE" : "DOWN"],
            ["Last worker tick", health.data?.worker?.last_tick?.status ?? "—"], ["Git", o.git?.head ?? "—"], ["Branch", o.git?.branch ?? "—"],
            ["Live data", "DISABLED"], ["Broker execution", "DISABLED"], ["Trading", "NO_TRADE"]]} />
        </Panel>
        <Panel title="Free data refresh" code="DATA" className="col-span-4"
          actions={<Button size="sm" onClick={() => refresh.mutate({})} loading={refresh.isPending || health.data?.refresh?.state === "RUNNING"}><RefreshCw className="h-3 w-3" />Refresh now</Button>}>
          <KV items={[["State", health.data?.refresh?.state ?? "IDLE"], ["Started", when(health.data?.refresh?.started_at)], ["Finished", when(health.data?.refresh?.finished_at)],
            ...Object.entries(health.data?.refresh?.sources ?? {}).map(([k, v]) => [k, String(v)] as [string, string])]} />
          <div className="mt-2 font-mono text-2xs text-ink-500">Yahoo futures, FRED, CFTC, SEC and Fed into the ignored operational archive; the committed snapshot is never modified.</div>
        </Panel>
        <Panel title="Databento (licensed raw contracts)" code="DBN" className="col-span-4" accent="research">
          <div className="space-y-2">
            <Badge tone="down">BLOCKED</Badge>
            <div className="font-mono text-2xs text-warn">{o.databento.status}</div>
            <KV items={[["Credential file present", o.databento.credential_present ? "yes (value never shown)" : "no"], ["Spend to date", `$${o.databento.spend_usd}`],
              ["Credit ceiling", `$${o.databento.credit_ceiling_usd}`], ["Range", `${o.databento.range?.start?.slice(0, 10)} → ${o.databento.range?.end?.slice(0, 10)}`], ["Preflight", when(o.databento.preflight_at)]]} />
          </div>
        </Panel>
        <Panel title="Datasets" code="DS" className="col-span-7">
          <Table dense rows={o.datasets} columns={[{ key: "id", label: "Dataset" }, { key: "rows", label: "Rows", align: "right", render: (d) => num(d.rows, 0) },
            { key: "first", label: "First", render: (d) => String(d.first ?? "—").slice(0, 16) }, { key: "last", label: "Last", render: (d) => String(d.last ?? "—").slice(0, 16) },
            { key: "status", label: "Status", render: (d) => <Badge>{d.status}</Badge> }, { key: "retrieved_at", label: "Retrieved", render: (d) => ago(d.retrieved_at) }]} />
        </Panel>
        <Panel title="Databento quotes (not purchased)" code="QUOT" className="col-span-5">
          <Table dense rows={Object.entries(o.databento.quotes ?? {}).map(([k, v]: any) => ({ k, ...v }))} columns={[{ key: "k", label: "Tranche", render: (q) => q.k.replaceAll("_", " ") },
            { key: "cost_usd", label: "Cost", align: "right", render: (q) => `$${num(Number(q.cost_usd), 2)}` }, { key: "billable_bytes", label: "MiB", align: "right", render: (q) => num(q.billable_bytes / 2 ** 20, 1) },
            { key: "record_count", label: "Rows", align: "right", render: (q) => num(q.record_count, 0) }]} />
        </Panel>
        <Panel title="Scheduler & orchestrators" code="SCHD" className="col-span-5">
          <div className="space-y-2">
            {o.scheduler.map((s: any) => (
              <div key={s.name} className="flex items-center gap-2 font-mono text-[11px]"><Dot tone={s["Last Result"] === "0" ? "up" : s["Last Result"] ? "warn" : "muted"} />
                <span className="flex-1 text-ink-200">{s.name}</span><span className="text-ink-400">last {s["Last Result"] ?? s.status} · {s["Last Run Time"] ?? ""}</span></div>
            ))}
            <KV items={[["Scheduled research jobs", JSON.stringify(o.orchestrator_jobs)], ["Studio jobs", JSON.stringify(o.studio_jobs)],
              ["Shadow ops", o.shadow_operations?.status ?? "—"], ["Open alerts", (o.shadow_operations?.open_alerts ?? []).length]]} />
            <div className="font-mono text-2xs text-ink-500">Shadow exit 1 = audit quarantine of two NDX forecasts, not a crash.</div>
          </div>
        </Panel>
        <Panel title="Providers" code="PRV" className="col-span-7">
          <Table dense rows={o.providers} columns={[{ key: "name", label: "Provider" }, { key: "category", label: "Category" }, { key: "access", label: "Access" },
            { key: "status", label: "Status", render: (p) => <Badge tone={p.status.startsWith("AVAILABLE") ? "up" : p.status === "BLOCKED" ? "down" : "warn"}>{p.status}</Badge> },
            { key: "credential_present", label: "Key", render: (p) => p.credential_env ? (p.credential_present ? "set" : "missing") : "none needed" }]} />
        </Panel>
        <Panel title="All research jobs" code="JOBS" className="col-span-12">
          <Table dense rows={jobs} columns={[{ key: "job_id", label: "Job", render: (j) => j.job_id.slice(0, 12) }, { key: "kind", label: "Kind" }, { key: "name", label: "Name" },
            { key: "state", label: "State", render: (j) => <Badge>{j.state}</Badge> }, { key: "p", label: "Progress", render: (j) => j.progress ? `${j.progress.percent}% ${j.progress.message}` : "—" },
            { key: "created", label: "Created", render: (j) => when(j.created) },
            { key: "x", label: "", render: (j) => (j.state === "RUNNING" || j.state === "QUEUED") ? <Button size="sm" variant="danger" onClick={() => cancel(j.job_id)}><Square className="h-3 w-3" />Stop</Button> : null }]} />
        </Panel>
      </div>
    )}</Query>
  );
}
