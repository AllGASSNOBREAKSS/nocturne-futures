import { useState } from "react";
import { useApi } from "@/lib/hooks";
import { cn, num, pct, tone, usd } from "@/lib/format";
import { Badge, KV, Panel, Query, Segmented, Stat, Table } from "@/components/ui";
import { Bars } from "@/components/charts";

export default function Signals() {
  const q = useApi<any>("/v1/signals");
  const research = useApi<any>("/v1/research");
  const [filter, setFilter] = useState<"ALL" | "ACCEPTED" | "REJECTED">("ALL");
  const [pick, setPick] = useState<number[]>([1, 2]);

  return (
    <Query q={q}>{(d) => {
      const rows: any[] = d.ranking?.ranking ?? [];
      const shown = rows.filter((r) => filter === "ALL" || (filter === "ACCEPTED" ? r.validation_status !== "REJECTED" : r.validation_status === "REJECTED"));
      const chosen = pick.map((rank) => rows.find((r) => r.rank === rank)).filter(Boolean);
      return (
        <div className="grid min-h-full grid-cols-12 gap-3">
          <div className="col-span-12 grid grid-cols-5 gap-2">
            <Stat label="Candidates ranked" value={d.ranking?.candidates ?? 0} sub="Phase 3V evidence" />
            <Stat label="Accepted" value={d.ranking?.accepted ?? 0} valueClass={(d.ranking?.accepted ?? 0) ? "text-up" : "text-down"} sub="independent dev + holdout" />
            <Stat label="Rejected" value={rows.filter((r) => r.validation_status === "REJECTED").length} valueClass="text-down" />
            <Stat label="Studio backtests" value={d.studio_backtests.length} sub="your runs" />
            <Stat label="Trading decision" value="NO_TRADE" valueClass="text-warn" sub="regardless of rank" />
          </div>
          <Panel title="Signal ranking — all candidates incl. rejected" code="SIG" className="col-span-8"
            actions={<Segmented value={filter} options={["ALL", "ACCEPTED", "REJECTED"] as const} onChange={setFilter} />}>
            <Table dense rows={shown} onRow={(r) => setPick(([first]) => (first === r.rank ? [first, pick[1]] : [r.rank, first]))} columns={[
              { key: "rank", label: "#", render: (r) => <span className={cn(pick.includes(r.rank) && "text-amber-400")}>{r.rank}</span> },
              { key: "signal", label: "Signal", render: (r) => <span className="block max-w-[300px] truncate text-ink-100" title={r.signal}>{r.signal.replace(" from 15:00 UTC open", "").replace(" (existing strategy, 5m)", " · 5m")}</span> },
              { key: "dn", label: "Dev n", align: "right", render: (r) => r.development.n },
              { key: "dev", label: "Dev EV pts [CI]", align: "right", render: (r) => <span className={tone(r.development.ev)}>{num(r.development.ev, 2)} {r.development.ev_ci95 ? `[${num(r.development.ev_ci95[0], 1)}, ${num(r.development.ev_ci95[1], 1)}]` : ""}</span> },
              { key: "hn", label: "Hold n", align: "right", render: (r) => r.holdout.n },
              { key: "hold", label: "Hold EV pts [CI]", align: "right", render: (r) => <span className={tone(r.holdout.ev)}>{num(r.holdout.ev, 2)} {r.holdout.ev_ci95 ? `[${num(r.holdout.ev_ci95[0], 1)}, ${num(r.holdout.ev_ci95[1], 1)}]` : ""}</span> },
              { key: "tf", label: "Target-first", align: "right", render: (r) => r.holdout.target_first ? pct(r.holdout.target_first.p) : pct(r.holdout.win_rate) },
              { key: "st", label: "Status", render: (r) => <Badge>{r.validation_status}</Badge> },
              { key: "why", label: "Reason", render: (r) => <span className="text-ink-400">{r.rejection_reason ?? "—"}</span> }]} />
            <div className="mt-2 font-mono text-2xs text-ink-500">{d.ranking?.note} Click rows to compare. Win rate alone never ranks a signal; EV lower bounds do.</div>
          </Panel>
          <Panel title="Side-by-side" code="CMP" className="col-span-4">
            <div className="grid grid-cols-2 gap-3">
              {chosen.map((r: any) => (
                <div key={r.rank} className="space-y-2 rounded-[3px] border border-ink-700 p-2">
                  <div className="font-mono text-[11px] text-amber-400">#{r.rank}</div>
                  <div className="min-h-[34px] font-mono text-2xs text-ink-200">{r.signal}</div>
                  <KV items={[["Family", r.family], ["Dev EV", num(r.development.ev, 2)], ["Hold EV", num(r.holdout.ev, 2)],
                    ["Dev n / hold n", `${r.development.n} / ${r.holdout.n}`], ["Status", r.validation_status]]} />
                  {r.regime_target_first?.holdout && <Bars height={80} data={Object.entries(r.regime_target_first.holdout).map(([k, v]: any) => ({ label: k, value: v.target_first ?? 0 }))} format={(v) => pct(v)} />}
                </div>
              ))}
            </div>
            <div className="mt-2 font-mono text-2xs text-ink-500">Bars: holdout target-first rate by VIX regime.</div>
          </Panel>
          <Panel title="Phase 4C evidence ranking — every tested strategy, setup and ML filter" code="RANK" className="col-span-12" accent="info">
            <Query q={research}>{(r) => r.phase4c_signals ? (
              <>
                <div className="mb-2 font-mono text-2xs text-ink-400">{r.phase4c_signals.candidates} candidates · {r.phase4c_signals.accepted} accepted · {r.phase4c_signals.note}</div>
                <Table dense maxRows={60} rows={r.phase4c_signals.ranking} columns={[
                  { key: "rank", label: "#" }, { key: "signal", label: "Signal", render: (x: any) => <span className="block max-w-[340px] truncate text-ink-100" title={x.signal}>{x.signal}</span> },
                  { key: "origin", label: "Origin" }, { key: "instrument", label: "Inst" },
                  { key: "w", label: "Win %", align: "right", render: (x: any) => pct(x.win_rate ?? x.eras.holdout?.win_rate) },
                  { key: "pts", label: "Mean pts", align: "right", render: (x: any) => num(x.mean_points, 1) },
                  ...["development", "holdout"].map((era) => ({ key: era, label: `${era.slice(0, 4)} n · EV [CI]`, align: "right" as const,
                    render: (x: any) => { const m = x.eras[era] ?? {}; return <span><span className="text-ink-400">{m.n} · </span><span className={tone(m.ev_points)}>{num(m.ev_points, 2)}</span> {m.ev_ci95 ? `[${num(m.ev_ci95[0], 2)}, ${num(m.ev_ci95[1], 2)}]` : ""}</span>; } })),
                  { key: "s", label: "Status", render: (x: any) => <Badge>{x.status}</Badge> },
                  { key: "reason", label: "Reason", render: (x: any) => <span className="text-ink-400">{x.reason ?? "—"}</span> }]} />
                <div className="mt-3 font-mono text-2xs uppercase tracking-widest text-ink-500">Large NQ days — what the strategies actually captured</div>
                <Table dense rows={Object.entries(r.phase4c_signals.large_move_capture).flatMap(([name, rows]: any) => Object.entries(rows).map(([k, v]: any) => ({ name, k, ...v })))} columns={[
                  { key: "name", label: "Strategy" }, { key: "k", label: "Day range" }, { key: "sessions_in_history", label: "Sessions", align: "right" },
                  { key: "trades", label: "Trades", align: "right" }, { key: "w", label: "Win %", align: "right", render: (x: any) => pct(x.win_rate) },
                  { key: "m", label: "Mean pts", align: "right", render: (x: any) => <span className={tone(x.mean_points)}>{num(x.mean_points, 1)}</span> },
                  { key: "s", label: "Share of range", align: "right", render: (x: any) => pct(x.share_of_day_range_captured) },
                  { key: "b", label: "Best pts", align: "right", render: (x: any) => num(x.best_points, 1) }]} />
              </>
            ) : <div className="font-mono text-xs text-ink-400">Not generated yet.</div>}</Query>
          </Panel>
          <Panel title="16-year strategy backtests — authentic Databento contract bars (2010–2026)" code="DB16" className="col-span-12" accent="info">
            <Query q={research}>{(r) => r.phase4_backtests ? (
              <Table dense rows={Object.entries(r.phase4_backtests.results).map(([name, v]: any) => ({ name, ...v }))} columns={[
                { key: "name", label: "Strategy", render: (x) => <span className="text-ink-100">{x.name.replaceAll("_", " ")}</span> },
                { key: "t", label: "Trades", align: "right", render: (x) => x.summary.trades }, { key: "w", label: "Win %", align: "right", render: (x) => pct(x.summary.win_rate) },
                { key: "pf", label: "PF", align: "right", render: (x) => num(x.summary.profit_factor, 2) },
                { key: "n", label: "Net", align: "right", render: (x) => <span className={tone(x.summary.net_pnl)}>{usd(x.summary.net_pnl)}</span> },
                { key: "dd", label: "Max DD", align: "right", render: (x) => usd(x.summary.max_drawdown) },
                ...["development", "validation", "holdout"].map((era) => ({ key: era, label: `${era.slice(0, 4)} exp [CI]`, align: "right" as const,
                  render: (x: any) => { const m = x.eras[era]; return <span className={tone(m.expectancy)}>{usd(m.expectancy)}{m.expectancy_ci95 ? ` [${usd(m.expectancy_ci95[0])}, ${usd(m.expectancy_ci95[1])}]` : ""}</span>; } })),
                { key: "v", label: "Verdict", render: (x) => <Badge>{x.verdict}</Badge> }]} />
            ) : <div className="font-mono text-xs text-ink-400">Not run yet.</div>}</Query>
            <div className="mt-2 font-mono text-2xs text-ink-500">Existing default parameters, no optimisation; eras by date: development 2010–18, validation 2019–22, holdout 2023–26. Per 2-contract position.</div>
          </Panel>
          <Panel title="Your studio backtests" code="USR" className="col-span-7">
            {d.studio_backtests.length ? (
              <Table dense rows={d.studio_backtests} columns={[{ key: "name", label: "Name", render: (b) => b.name ?? b.job_id.slice(0, 8) },
                { key: "m", label: "Market", render: (b) => `${b.config.root} ${b.config.interval}` }, { key: "t", label: "Trades", align: "right", render: (b) => b.summary?.trades },
                { key: "w", label: "Win %", align: "right", render: (b) => pct(b.summary?.win_rate) }, { key: "pf", label: "PF", align: "right", render: (b) => num(b.summary?.profit_factor, 2) },
                { key: "e", label: "Expectancy", align: "right", render: (b) => <span className={tone(b.summary?.expectancy)}>{usd(b.summary?.expectancy)}</span> },
                { key: "v", label: "Verdict", render: (b) => <Badge>{b.verdict}</Badge> }]} />
            ) : <div className="font-mono text-xs text-ink-400">Run backtests from the Strategy Lab to see them ranked here.</div>}
          </Panel>
          <Panel title="NQ target-before-stop — authentic bars 2010–2026" code="TBS" className="col-span-12" accent="info">
            <Query q={research}>{(r) => r.phase4_target_study ? (
              <Table dense rows={r.phase4_target_study.cells} columns={[
                { key: "g", label: "Geometry", render: (c) => `${c.horizon} · T${c.target}/S${c.stop} · ${c.side}` },
                ...["development", "validation", "holdout"].map((era) => ({ key: era, label: `${era.slice(0, 4)} n · target-first · EV pts [CI]`, align: "right" as const,
                  render: (c: any) => { const m = c[era]; return <span><span className="text-ink-400">{m.n} · </span>{pct(m.target_first)} · <span className={tone(m.net_ev_points)}>{num(m.net_ev_points, 2)}</span> {m.net_ev_ci95 ? `[${num(m.net_ev_ci95[0], 1)}, ${num(m.net_ev_ci95[1], 1)}]` : ""}</span>; } })),
                { key: "v", label: "Verdict", render: (c) => <Badge>{c.verdict}</Badge> }]} />
            ) : <div className="font-mono text-xs text-ink-400">Not run yet.</div>}</Query>
            <div className="mt-2 font-mono text-2xs text-ink-500">Entry 10:00 ET; same-contract 5m paths, ties resolved on 1m, else stop-first; paths crossing a roll skipped; 0.75 pt costs.</div>
          </Panel>
          <Panel title="Existing strategies — Phase 3V splits" code="STR" className="col-span-5">
            <Query q={research}>{(r) => (
              <Table dense rows={Object.entries(r.strategies?.roots ?? {}).flatMap(([root, e]: any) => Object.entries(e.strategies).map(([name, s]: any) => ({ root, name, ...s })))} columns={[
                { key: "x", label: "Strategy", render: (s) => `${s.root} ${s.name.replaceAll("_", " ")}` },
                ...["development", "validation", "holdout"].map((era) => ({ key: era, label: era.slice(0, 4), align: "right" as const,
                  render: (s: any) => { const m = s.by_slippage_ticks["1.0"][era]; return <span className={tone(m.expectancy)}>{m.trades}·{usd(m.expectancy)}</span>; } })),
                { key: "v", label: "Verdict", render: (s) => <Badge>{s.verdict}</Badge> }]} />
            )}</Query>
          </Panel>
        </div>
      );
    }}</Query>
  );
}
