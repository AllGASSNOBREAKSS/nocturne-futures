import { useState } from "react";
import { Send } from "lucide-react";
import { useAction, useApi } from "@/lib/hooks";
import { ago, num, pct, when } from "@/lib/format";
import { Badge, Button, ErrorState, KV, Panel, Query, Segmented, Stat, Table } from "@/components/ui";
import type { Root } from "@/lib/api";

const SESSIONS = ["ASIA", "LONDON", "NEW_YORK", "FULL_DAY"];

export default function Predictions() {
  const [root, setRoot] = useState<Root>("NQ");
  const q = useApi<any>(`/v1/forecasts/sessions?root=${root}`);
  const shadow = useApi<any>("/v1/forecasts/ndx-shadow");
  const issue = useAction(`/v1/forecasts/sessions/${root}/issue`, ["/v1/forecasts"]);
  const latest = q.data?.forecasts?.at(-1);

  return (
    <div className="grid min-h-full grid-cols-12 gap-3">
      <div className="col-span-12 flex items-center gap-3">
        <Segmented value={root} options={["NQ", "ES"] as const} onChange={setRoot} />
        <Button onClick={() => issue.mutate({})} loading={issue.isPending}><Send className="h-3 w-3" />Issue next-session forecast</Button>
        {issue.data && <Badge tone={issue.data.forecast.status === "ISSUED" ? "up" : "muted"}>{issue.data.forecast.status} · {issue.data.outcomes_written} outcomes evaluated</Badge>}
        {issue.error && <div className="max-w-lg"><ErrorState error={issue.error} /></div>}
        <span className="ml-auto font-mono text-2xs text-ink-500">Method trailing-empirical-v1 · append-only journal · direction withheld until a model validates</span>
      </div>
      <Panel title={`Latest ${root} session forecast`} code="PRED" className="col-span-8">
        <Query q={q}>{() => latest ? (
          <div className="space-y-3">
            <div className="grid grid-cols-4 gap-2">
              <Stat label="Target session" value={latest.target_session} sub={`issued ${ago(latest.issued_at)}`} />
              <Stat label="Data as of" value={when(latest.data_as_of)} sub={latest.freshness} valueClass="text-sm" />
              <Stat label="Regime" value={latest.regime?.state} sub={latest.regime?.trend} />
              <Stat label="Validation" value={<Badge tone="research">{latest.validation_status}</Badge>} sub={latest.forecast_id} />
            </div>
            <div className="grid grid-cols-4 gap-2">
              {SESSIONS.map((s) => {
                const fq = latest.quantiles_points[s];
                const outcome = latest.outcomes?.find((o: any) => o.session === s);
                return (
                  <div key={s} className="rounded-[3px] border border-ink-700 bg-ink-900/70 p-3">
                    <div className="mb-2 flex items-center justify-between font-mono text-2xs uppercase tracking-widest text-amber-500">{s.replace("_", " ")}
                      {outcome && <Badge tone={outcome.covered.p80 ? "up" : "down"}>{outcome.covered.p80 ? "IN P80" : "OUTSIDE P80"}</Badge>}</div>
                    <RangeBar q={fq} realized={outcome?.realized_range} />
                    <KV items={[["P50", num(fq.p50, 1)], ["P80", num(fq.p80, 1)], ["P90", num(fq.p90, 1)], ["Realized", outcome ? num(outcome.realized_range, 1) : "pending"]]} />
                  </div>
                );
              })}
            </div>
            <div className="rounded-[3px] border border-warn/25 bg-warn/5 p-2 font-mono text-2xs text-warn">{latest.direction_note} {latest.event_risk}</div>
          </div>
        ) : <div className="font-mono text-xs text-ink-400">No forecast issued for {root} yet.</div>}</Query>
      </Panel>
      <Panel title="Retrospective calibration (same method, last 500 sessions)" code="CAL" className="col-span-4">
        <Query q={q}>{(d) => (
          <div className="space-y-3">
            <Table dense rows={Object.entries(d.retrospective.coverage).map(([s, c]: any) => ({ s, ...c }))} columns={[
              { key: "s", label: "Session" }, { key: "n", label: "n", align: "right" },
              { key: "p50", label: "P50 cov", align: "right", render: (r) => pct(r.p50) }, { key: "p80", label: "P80 cov", align: "right", render: (r) => pct(r.p80) },
              { key: "p90", label: "P90 cov", align: "right", render: (r) => pct(r.p90) }]} />
            <div className="font-mono text-2xs text-ink-500">Retrospective walk of the baseline method; ideal coverage 50/80/90%. Not forward evidence.</div>
            <div className="border-t border-ink-800 pt-2"><KV items={[["Forward forecasts issued", d.summary.issued], ["Sessions evaluated", d.summary.evaluated_sessions],
              ["Forward P80 coverage", pct(d.summary.coverage.p80)]]} /></div>
          </div>
        )}</Query>
      </Panel>
      <Panel title={`${root} forecast journal`} code="JRNL" className="col-span-7">
        <Query q={q}>{(d) => d.forecasts.length ? (
          <Table dense rows={[...d.forecasts].reverse()} columns={[
            { key: "forecast_id", label: "ID", render: (f) => f.forecast_id.slice(0, 10) }, { key: "target_session", label: "Target" },
            { key: "issued_at", label: "Issued", render: (f) => when(f.issued_at) },
            { key: "ny", label: "NY P50/P80", align: "right", render: (f) => `${num(f.quantiles_points.NEW_YORK.p50, 0)} / ${num(f.quantiles_points.NEW_YORK.p80, 0)}` },
            { key: "o", label: "Evaluated", align: "right", render: (f) => `${f.outcomes.length}/4` },
            { key: "c", label: "P80 hits", align: "right", render: (f) => f.outcomes.length ? `${f.outcomes.filter((o: any) => o.covered.p80).length}/${f.outcomes.length}` : "—" }]} />
        ) : <div className="font-mono text-xs text-ink-400">Journal empty.</div>}</Query>
      </Panel>
      <Panel title="NDX range shadow model (ndx-range-v1)" code="SHDW" className="col-span-5" accent="research">
        <Query q={shadow}>{(s) => (
          <div className="space-y-2">
            <div className="flex items-center gap-2"><Badge tone={s.operational_status === "AUDIT_BLOCKED" ? "warn" : "up"}>{s.operational_status}</Badge>
              <span className="font-mono text-2xs text-ink-500">status {ago(s.status_at)}</span></div>
            <Table dense rows={s.forecasts} columns={[
              { key: "target_date", label: "Target" },
              { key: "q", label: "P50/P80/P90 %", align: "right", render: (f) => `${pct(f.quantiles.p50)} / ${pct(f.quantiles.p80)} / ${pct(f.quantiles.p90)}` },
              { key: "r", label: "Realized", align: "right", render: (f) => { const o = (s.outcomes ?? []).find((x: any) => x.forecast_id === f.forecast_id); return o ? pct(o.realized_range_pct) : "—"; } },
              { key: "st", label: "Status", render: (f) => (s.outcomes ?? []).some((x: any) => x.forecast_id === f.forecast_id) ? <Badge tone="up">MATURED</Badge> : (s.quarantined ?? []).includes(f.forecast_id) ? <Badge tone="warn">AUDIT_BLOCKED</Badge> : <Badge>PENDING</Badge> }]} />
            {s.report?.aggregate_descriptive_only && <KV items={[["Mean pinball — model", num(s.report.aggregate_descriptive_only.mean_pinball_model, 4)],
              ["Mean pinball — trailing baseline", num(s.report.aggregate_descriptive_only.mean_pinball_trailing_baseline, 4)],
              ["P80 coverage", pct(s.report.aggregate_descriptive_only.p80_coverage)]]} />}
            <div className="font-mono text-2xs text-ink-500">Mean pinball, n={s.report?.aggregate_descriptive_only?.n}: descriptive only. Immutable journal; never edited.</div>
          </div>
        )}</Query>
      </Panel>
    </div>
  );
}

function RangeBar({ q, realized }: { q: { p50: number; p80: number; p90: number }; realized?: number }) {
  const max = Math.max(q.p90, realized ?? 0) * 1.1;
  const x = (v: number) => `${(v / max) * 100}%`;
  return (
    <div className="relative mb-3 h-5 rounded-sm bg-ink-800">
      <div className="absolute inset-y-0 left-0 rounded-sm bg-amber-500/15" style={{ width: x(q.p90) }} />
      <div className="absolute inset-y-0 left-0 rounded-sm bg-amber-500/30" style={{ width: x(q.p80) }} />
      <div className="absolute inset-y-0 left-0 rounded-sm bg-amber-500/60" style={{ width: x(q.p50) }} />
      {realized !== undefined && <div className="absolute inset-y-[-3px] w-[2px] bg-info shadow-[0_0_6px_#39c5ff]" style={{ left: x(realized) }} title={`realized ${realized}`} />}
    </div>
  );
}
