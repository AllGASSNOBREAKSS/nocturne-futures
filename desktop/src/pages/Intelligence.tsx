import { useApi } from "@/lib/hooks";
import { num, pct, signed, when } from "@/lib/format";
import { Badge, Panel, Query, Table } from "@/components/ui";
import { TimeLine } from "@/components/charts";

const ts = (d: string) => Math.floor(new Date(d).getTime() / 1000);

export default function Intelligence() {
  const q = useApi<any>("/v1/intel");
  return (
    <Query q={q}>{(d) => (
      <div className="grid min-h-full grid-cols-12 gap-3">
        <div className="col-span-12 grid grid-cols-5 gap-3">
          {Object.entries(d.macro).slice(0, 10).map(([k, m]: any) => (
            <Panel key={k} title={m.label} code={k} bodyClass="p-2">
              <div className="flex items-baseline justify-between font-mono">
                <span className="text-lg font-semibold tabular-nums text-ink-100">{num(m.value, k === "WALCL" ? 0 : 2)}</span>
                <span className={`text-2xs ${m.change_20 >= 0 ? "text-up" : "text-down"}`}>{signed(m.change_20, k === "WALCL" ? 0 : 2)} 20obs</span>
              </div>
              <TimeLine height={60} series={[{ name: k, points: m.history.map((p: any) => ({ t: ts(p.date), v: p.value })) }]} />
              <div className="flex justify-between font-mono text-2xs text-ink-500"><span>obs {m.date}</span>{!m.pit_eligible && <Badge tone="warn">revisable</Badge>}</div>
            </Panel>
          ))}
        </div>
        <Panel title="CFTC positioning — net % of open interest" code="COT" className="col-span-7" bodyClass="p-1">
          <TimeLine height={220} area={false} series={Object.entries(d.positioning).flatMap(([label, rows]: any) => [
            { name: `${label} asset mgr`, points: rows.map((r: any) => ({ t: ts(r.report_date), v: r.asset_manager_net_pct * 100 })) },
            { name: `${label} leveraged`, points: rows.map((r: any) => ({ t: ts(r.report_date), v: r.leveraged_net_pct * 100 })) }])} />
          <div className="px-2 pb-1 font-mono text-2xs text-ink-500">Traders in Financial Futures, futures-only. Tuesday positions, treated as available the following Monday 21:00 UTC.</div>
        </Panel>
        <Panel title="Federal Reserve releases" code="FED" className="col-span-5">
          <div className="space-y-1">{d.fed_press.slice(0, 14).map((f: any) => (
            <div key={f.link} className="border-b border-ink-800 py-1">
              <div className="flex items-center gap-2 font-mono text-2xs text-ink-500"><span>{when(f.published_at)}</span><Badge tone={f.event_type.startsWith("FOMC") || f.event_type === "MONETARY_POLICY" ? "amber" : "muted"}>{f.event_type}</Badge></div>
              <div className="truncate font-sans text-[12px] text-ink-200" title={f.title}>{f.title}</div>
            </div>
          ))}</div>
        </Panel>
        <Panel title="Megacap SEC filings" code="SEC" className="col-span-6">
          <Table dense maxRows={25} rows={d.sec_filings} columns={[{ key: "available_at", label: "Accepted (UTC)", render: (f) => f.available_at.slice(0, 16) },
            { key: "ticker", label: "Ticker", render: (f) => <span className="text-amber-400">{f.ticker}</span> }, { key: "form", label: "Form" },
            { key: "event_type", label: "Type" }, { key: "report_date", label: "Period" }, { key: "items", label: "8-K items" }]} />
        </Panel>
        <Panel title="BLS latest" code="BLS" className="col-span-3">
          <Table dense rows={d.bls_latest} columns={[{ key: "series", label: "Series" }, { key: "date", label: "Period" }, { key: "value", label: "Value", align: "right", render: (r) => num(r.value, 1) }]} />
          <div className="mt-2 font-mono text-2xs text-ink-500">Revised series; context only (no release-time vintages).</div>
        </Panel>
        <Panel title="News & events" code="NEWS" className="col-span-3">
          <Badge tone="down">{d.news.status}</Badge>
          <div className="mt-2 font-mono text-2xs text-ink-400">{d.news.detail}</div>
          <div className="mt-3 font-mono text-2xs text-ink-500">{d.attribution}</div>
          <div className="mt-2 font-mono text-2xs text-ink-500">Asset-manager NQ net: {pct((d.positioning["E-mini Nasdaq-100"] ?? []).at(-1)?.asset_manager_net_pct)}</div>
        </Panel>
      </div>
    )}</Query>
  );
}
