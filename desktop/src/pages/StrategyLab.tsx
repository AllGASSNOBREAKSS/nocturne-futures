import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Play, Plus, Save, Trash2 } from "lucide-react";
import { useAction, useApi } from "@/lib/hooks";
import { ago, cn } from "@/lib/format";
import { Badge, Button, ErrorState, Field, Input, Panel, Query, Segmented, Select } from "@/components/ui";

type Ref = { indicator: string; params?: Record<string, number> } | number;
type Cond = { left: Ref; op: string; right: Ref };

const DEFAULT_RULE = {
  side: "LONG", session: "RTH", horizon_bars: 24, max_trades_per_session: 1, stop: { type: "atr", value: 1.5 }, targets_r: [1, 2],
  conditions: [
    { left: { indicator: "close" }, op: "crosses_above", right: { indicator: "vwap" } },
    { left: { indicator: "rsi", params: { n: 14 } }, op: ">", right: 50 },
  ] as Cond[],
};

function RefEditor({ value, onChange, catalog, allowNumber }: { value: Ref; onChange: (r: Ref) => void; catalog: any; allowNumber?: boolean }) {
  const isNum = typeof value === "number";
  const spec = !isNum ? catalog[(value as any).indicator] : null;
  return (
    <div className="flex min-w-0 flex-1 items-center gap-1">
      <Select className="h-7 min-w-[140px] flex-1 text-[11px]" value={isNum ? "__number" : (value as any).indicator}
        onChange={(e) => onChange(e.target.value === "__number" ? 50 : { indicator: e.target.value })}>
        {allowNumber && <option value="__number">Number…</option>}
        {Object.entries(catalog).map(([k, v]: any) => <option key={k} value={k}>{v.label}</option>)}
      </Select>
      {isNum && <Input className="h-7 w-20 text-[11px]" type="number" value={value as number} onChange={(e) => onChange(Number(e.target.value))} />}
      {spec && Object.entries(spec.params).map(([p, [lo, hi, def]]: any) => (
        <Input key={p} title={`${p} (${lo}–${hi})`} className="h-7 w-14 text-[11px]" type="number" min={lo} max={hi}
          value={(value as any).params?.[p] ?? def} onChange={(e) => onChange({ ...(value as any), params: { ...(value as any).params, [p]: Number(e.target.value) } })} />
      ))}
    </div>
  );
}

export default function StrategyLab() {
  const navigate = useNavigate();
  const catalog = useApi<any>("/v1/indicators/catalog");
  const saved = useApi<any[]>("/v1/configs/strategy");
  const run = useAction<any>("/v1/backtests", ["/v1/backtests"]);
  const save = useAction<any>("/v1/configs/strategy", ["/v1/configs/strategy"]);
  const [name, setName] = useState("VWAP reclaim + RSI>50");
  const [kind, setKind] = useState<string>("rule");
  const [rule, setRule] = useState<any>(DEFAULT_RULE);
  const [params, setParams] = useState<Record<string, number>>({});
  const [ctx, setCtx] = useState({ root: "NQ", interval: "5m", start: "", end: "", contracts: 2, commission: 2.5, slippage: 1 });
  const ind = catalog.data?.indicators ?? {};
  const builtin = catalog.data?.strategies ?? {};
  const setCond = (i: number, c: Cond) => setRule((r: any) => ({ ...r, conditions: r.conditions.map((x: Cond, k: number) => (k === i ? c : x)) }));

  const config = () => ({
    name, root: ctx.root, interval: ctx.interval, start: ctx.start || undefined, end: ctx.end || undefined, contracts: ctx.contracts,
    costs: { commission_per_contract: ctx.commission, slippage_ticks: ctx.slippage },
    strategy: kind === "rule" ? { type: "rule", rule } : { type: kind, params },
  });

  return (
    <div className="grid min-h-full grid-cols-12 gap-3">
      <Panel title="Strategy builder" code="LAB" className="col-span-8" bodyClass="space-y-4">
        <div className="grid grid-cols-3 gap-2">
          <Field label="Strategy name"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label="Algorithm"><Select value={kind} onChange={(e) => { setKind(e.target.value); setParams({}); }}>
            <option value="rule">Rule builder (custom)</option>
            {Object.keys(builtin).map((k) => <option key={k} value={k}>{k.replaceAll("_", " ")}</option>)}</Select></Field>
          <Field label="Instrument · bars"><div className="flex gap-1.5"><Segmented value={ctx.root as "NQ" | "ES"} options={["NQ", "ES"] as const} onChange={(v) => setCtx({ ...ctx, root: v })} />
            <Select value={ctx.interval} onChange={(e) => setCtx({ ...ctx, interval: e.target.value })}>{(catalog.data?.intervals ?? ["5m"]).map((i: string) => <option key={i}>{i}</option>)}</Select></div></Field>
        </div>
        {kind === "rule" ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-2xs uppercase tracking-widest text-ink-400">Enter</span>
              <Segmented value={rule.side} options={["LONG", "SHORT"] as const} onChange={(v) => setRule({ ...rule, side: v })} />
              <span className="font-mono text-2xs uppercase tracking-widest text-ink-400">when ALL hold at bar close · session</span>
              <Select className="h-7 w-32 text-[11px]" value={rule.session} onChange={(e) => setRule({ ...rule, session: e.target.value })}>
                {(catalog.data?.sessions ?? []).map((s: string) => <option key={s}>{s}</option>)}</Select>
            </div>
            {rule.conditions.map((c: Cond, i: number) => (
              <div key={i} className="flex items-center gap-2 rounded-[3px] border border-ink-700 bg-ink-900/60 p-2">
                <span className="w-5 font-mono text-2xs text-amber-500">{i + 1}</span>
                <RefEditor value={c.left} catalog={ind} onChange={(v) => setCond(i, { ...c, left: v })} />
                <Select className="h-7 w-32 text-[11px]" value={c.op} onChange={(e) => setCond(i, { ...c, op: e.target.value })}>
                  {(catalog.data?.operators ?? []).map((o: string) => <option key={o} value={o}>{o.replace("_", " ")}</option>)}</Select>
                <RefEditor value={c.right} catalog={ind} allowNumber onChange={(v) => setCond(i, { ...c, right: v })} />
                <button onClick={() => setRule({ ...rule, conditions: rule.conditions.filter((_: any, k: number) => k !== i) })} className="text-ink-500 hover:text-down"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
            <Button size="sm" variant="outline" disabled={rule.conditions.length >= 8}
              onClick={() => setRule({ ...rule, conditions: [...rule.conditions, { left: { indicator: "close" }, op: ">", right: { indicator: "sma", params: { n: 50 } } }] })}><Plus className="h-3 w-3" />Add condition</Button>
            <div className="grid grid-cols-5 gap-2">
              <Field label="Stop type"><Select value={rule.stop.type} onChange={(e) => setRule({ ...rule, stop: { ...rule.stop, type: e.target.value } })}><option value="atr">ATR multiple</option><option value="points">Points</option></Select></Field>
              <Field label={rule.stop.type === "atr" ? "Stop × ATR14" : "Stop points"}><Input type="number" step="0.25" value={rule.stop.value} onChange={(e) => setRule({ ...rule, stop: { ...rule.stop, value: Number(e.target.value) } })} /></Field>
              <Field label="Targets (R, comma)"><Input value={rule.targets_r.join(",")} onChange={(e) => setRule({ ...rule, targets_r: e.target.value.split(",").map(Number).filter((x) => x > 0) })} /></Field>
              <Field label="Max hold (bars)"><Input type="number" value={rule.horizon_bars} onChange={(e) => setRule({ ...rule, horizon_bars: Number(e.target.value) })} /></Field>
              <Field label="Max trades / session"><Input type="number" value={rule.max_trades_per_session} onChange={(e) => setRule({ ...rule, max_trades_per_session: Number(e.target.value) })} /></Field>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(builtin[kind] ?? {}).map(([p, [lo, hi, def]]: any) => (
              <Field key={p} label={`${p.replaceAll("_", " ")} (${lo}–${hi})`}><Input type="number" value={params[p] ?? def} min={lo} max={hi} step="any" onChange={(e) => setParams({ ...params, [p]: Number(e.target.value) })} /></Field>
            ))}
            <div className="col-span-3 font-mono text-2xs text-ink-500">Existing Nocturne strategy with its documented entry/stop/target rules; RTH sessions on 1m/5m bars.</div>
          </div>
        )}
        <div className="grid grid-cols-6 gap-2 border-t border-ink-800 pt-3">
          <Field label="Start (UTC)"><Input placeholder="optional" value={ctx.start} onChange={(e) => setCtx({ ...ctx, start: e.target.value })} /></Field>
          <Field label="End (UTC)"><Input placeholder="optional" value={ctx.end} onChange={(e) => setCtx({ ...ctx, end: e.target.value })} /></Field>
          <Field label="Contracts"><Select value={ctx.contracts} onChange={(e) => setCtx({ ...ctx, contracts: Number(e.target.value) })}>{[1, 2, 3, 4].map((c) => <option key={c}>{c}</option>)}</Select></Field>
          <Field label="Commission / side"><Input type="number" step="0.25" value={ctx.commission} onChange={(e) => setCtx({ ...ctx, commission: Number(e.target.value) })} /></Field>
          <Field label="Slippage (ticks)"><Input type="number" step="0.5" value={ctx.slippage} onChange={(e) => setCtx({ ...ctx, slippage: Number(e.target.value) })} /></Field>
          <div className="flex items-end gap-2">
            <Button onClick={() => run.mutate(config(), { onSuccess: (r: any) => r.job_id && navigate(`/backtests/${r.job_id}`) })} loading={run.isPending}><Play className="h-3 w-3" />Backtest</Button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => save.mutate({ name, config: kind === "rule" ? rule : { type: kind, params } })} loading={save.isPending}><Save className="h-3 w-3" />Save version</Button>
          {save.data && <span className="font-mono text-2xs text-up">Saved {save.data.name} v{save.data.version}</span>}
          {save.error && <ErrorState error={save.error} />}
          {run.data?.status === "REJECTED" && <ErrorState error={new Error(run.data.errors.join(" · "))} />}
          {run.error && <ErrorState error={run.error} />}
          <span className="ml-auto font-mono text-2xs text-ink-500">Signals act at the next bar open · same-bar stop/target ⇒ stop first · cashflow-v2 costs</span>
        </div>
      </Panel>
      <div className="col-span-4 flex flex-col gap-3">
        <Panel title="Indicator library" code="IND">
          <Query q={catalog}>{(c) => (
            <div className="space-y-1">
              {Object.entries(c.indicators).map(([k, v]: any) => (
                <div key={k} className="flex items-center gap-2 font-mono text-[11px]"><Badge tone={v.panel === "price" ? "amber" : v.panel === "volume" ? "info" : "research"}>{v.panel}</Badge>
                  <span className="text-ink-200">{v.label}</span><span className="ml-auto text-ink-500">{Object.keys(v.params).join(", ")}</span></div>
              ))}
              <div className="mt-2 border-t border-ink-800 pt-2 font-mono text-2xs uppercase tracking-widest text-ink-500">Disabled — authentic order flow required</div>
              {Object.entries(c.unavailable).map(([k, v]: any) => (
                <div key={k} className="flex items-start gap-2 font-mono text-[11px] text-ink-500" title={v}><Badge tone="down">off</Badge><span>{k}</span></div>
              ))}
            </div>
          )}</Query>
        </Panel>
        <Panel title="Saved strategies" code="SAVE">
          <Query q={saved}>{(rows) => rows.length ? (
            <div className="space-y-1">{rows.map((s) => (
              <button key={s.name} onClick={() => { setName(s.name); if (s.config.side) { setKind("rule"); setRule(s.config); } else { setKind(s.config.type); setParams(s.config.params ?? {}); } }}
                className={cn("flex w-full items-center justify-between rounded px-1 py-1 text-left font-mono text-[11px] text-ink-200 hover:bg-ink-800")}>
                <span>{s.name}</span><span className="text-ink-500">v{s.version} · {ago(s.saved_at)}</span></button>
            ))}</div>
          ) : <div className="font-mono text-xs text-ink-500">No saved strategies yet.</div>}</Query>
        </Panel>
      </div>
    </div>
  );
}
