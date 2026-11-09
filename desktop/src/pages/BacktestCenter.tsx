import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Play, Rocket, Trophy } from "lucide-react";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { cn, num, pct, usd, verdictTone } from "@/lib/format";
import { Badge, Button, ErrorState, Field, Input, Panel, Progress, Segmented, Table } from "@/components/ui";
import type { Root } from "@/lib/api";

const RR_CHOICES = [0.5, 1, 2, 3, 5, 8];
const FAMILY_LABEL: Record<string, string> = { algo: "Algo", indicator: "Indicator", model: "ML model" };
const VERDICT_LABEL: Record<string, string> = { VALIDATED_BOTH_HALVES: "Validated", PROFITABLE_NOT_SIGNIFICANT: "Profitable, not proven",
  LOSES_MONEY: "Loses money", INSUFFICIENT_SAMPLE: "Too few trades" };

export default function BacktestCenter() {
  const navigate = useNavigate();
  const catalog = useApi<any>("/v1/indicators/catalog");
  const sweeps = useApi<any>("/v1/sweeps", { refetchInterval: 5000 });
  const [root, setRoot] = useState<Root>("NQ");
  const [contracts, setContracts] = useState(1);
  const [rr, setRr] = useState<number[]>([1, 2, 3, 5, 8]);
  const [custom, setCustom] = useState("");
  const [start, setStart] = useState("2019-01-01");
  const [end, setEnd] = useState("");
  const [sort, setSort] = useState<"win_rate" | "net_pnl">("win_rate");
  const [sweepId, setSweepId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const startSweep = useAction<any>("/v1/sweeps", ["/v1/sweeps"]);

  useEffect(() => {
    if (!sweepId && sweeps.data?.jobs?.length) setSweepId(sweeps.data.jobs[0].job_id);
  }, [sweeps.data, sweepId]);
  const job = useApi<any>(sweepId ? `/v1/jobs/${sweepId}` : null, { refetchInterval: 2500 });
  const running = job.data && ["QUEUED", "RUNNING"].includes(job.data.state);
  const report = job.data?.report;

  const rrList = useMemo(() => {
    const extra = parseFloat(custom);
    return [...new Set([...rr, ...(Number.isFinite(extra) && extra >= 0.25 && extra <= 20 ? [extra] : [])])].sort((a, b) => a - b);
  }, [rr, custom]);
  const singleRR = rrList.length ? rrList[Math.min(1, rrList.length - 1)] : 1;

  const base = () => ({ root, interval: "5m", source: "databento", start, ...(end ? { end } : {}), contracts,
    costs: { commission_per_contract: 2.5, slippage_ticks: 1 } });

  async function runOne(strategy: any, label: string, rrValue: number) {
    setError(null); setBusy(label + rrValue);
    const exit: any = { rr: [rrValue] };
    if (["ml_direction", "session_trend"].includes(strategy.type)) exit.stop = { type: "atr", value: 0.25 };
    try {
      const r: any = await api.post("/v1/backtests", { ...base(), name: `${label} 1:${rrValue}`, strategy, exit });
      if (r.status === "REJECTED") setError(r.errors.join("; "));
      else navigate(`/backtests/${r.job_id}`);
    } catch (e: any) { setError(String(e.message ?? e)); }
    setBusy(null);
  }

  const rows = useMemo(() => {
    const lb = (report?.leaderboard ?? []).filter((r: any) => r.trades > 0);
    return [...lb].sort((a: any, b: any) => (b[sort] ?? -1e18) - (a[sort] ?? -1e18));
  }, [report, sort]);
  const best = rows.find((r: any) => r.trades >= 100);

  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-3">
      <Panel title="Backtest setup" code="SET">
        <div className="flex flex-wrap items-end gap-4">
          <Field label="Instrument"><Segmented value={root} options={["NQ", "ES"] as const} onChange={setRoot} /></Field>
          <Field label="Contracts (1–50)"><Input type="number" min={1} max={50} value={contracts} className="w-24"
            onChange={(e) => setContracts(Math.max(1, Math.min(50, parseInt(e.target.value || "1"))))} /></Field>
          <Field label="Reward : risk (pick any)">
            <div className="flex gap-1">
              {RR_CHOICES.map((v) => (
                <button key={v} onClick={() => setRr(rr.includes(v) ? rr.filter((x) => x !== v) : [...rr, v])}
                  className={cn("rounded-[3px] border px-2 py-1 font-mono text-[11px]", rr.includes(v) ? "border-amber-500 bg-amber-500/15 text-amber-300" : "border-ink-700 text-ink-400 hover:text-ink-200")}>1:{v}</button>
              ))}
              <Input placeholder="custom" value={custom} onChange={(e) => setCustom(e.target.value)} className="w-20" />
            </div>
          </Field>
          <Field label="From"><Input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></Field>
          <Field label="To (blank = latest)"><Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></Field>
          <Button className="ml-auto h-10 px-5" loading={startSweep.isPending || running} disabled={!rrList.length}
            onClick={() => startSweep.mutate({ root, contracts, rr: rrList, start, ...(end ? { end } : {}) },
              { onSuccess: (r: any) => (r.status === "REJECTED" ? setError(r.errors.join("; ")) : setSweepId(r.job_id)) })}>
            <Rocket className="h-4 w-4" />Backtest everything
          </Button>
        </div>
        <div className="mt-2 font-mono text-2xs text-ink-500">
          Authentic CME contract bars (Databento 5m), $2.50/contract commission, 1 tick slippage, stop-first when a bar hits both. Dollar results use your contract count.
          Win rate rises as reward:risk falls — a 1:0.5 target wins more often but each loss costs twice a win.
        </div>
        {error && <div className="mt-2 font-mono text-[11px] text-down">{error}</div>}
      </Panel>

      {sweepId && job.data && (
        <Panel title={`Leaderboard · ${job.data.config?.root} · ${job.data.config?.contracts} contract(s) · R:R ${(job.data.config?.rr ?? []).map((x: number) => `1:${x}`).join(", ")}`} code="RANK" bodyClass="p-0"
          actions={<Segmented value={sort} options={[{ value: "win_rate", label: "By win rate" }, { value: "net_pnl", label: "By profit" }]} onChange={setSort} />}>
          {running && <div className="space-y-1 p-3 font-mono text-[11px] text-ink-300"><Progress value={job.data.progress?.percent ?? 0} /><div>{job.data.progress?.message ?? "queued"}</div></div>}
          {job.data.state === "FAILED" && <div className="p-3"><ErrorState error={new Error(job.data.result?.reason ?? "sweep failed")} /></div>}
          {report && (
            <>
              {best && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-wrap items-center gap-4 border-b border-ink-700 bg-amber-500/5 px-3 py-2 font-mono text-[12px]">
                  <Trophy className="h-4 w-4 text-amber-400" />
                  <span className="text-ink-300">Top by {sort === "win_rate" ? "win rate" : "profit"} (≥100 trades):</span>
                  <span className="text-ink-100">{best.label} 1:{best.rr}</span>
                  <span>win {pct(best.win_rate, 1)}</span><span className={best.net_pnl >= 0 ? "text-up" : "text-down"}>{usd(best.net_pnl)}</span>
                  <Badge tone={verdictTone(best.verdict === "VALIDATED_BOTH_HALVES" ? "ACCEPT" : best.net_pnl > 0 ? "INCONCLUSIVE" : "REJECT")}>{VERDICT_LABEL[best.verdict] ?? best.verdict}</Badge>
                  <span className="text-ink-500">{report.validated.length} of {report.leaderboard.length} combinations validated in both halves</span>
                </motion.div>
              )}
              <div className="max-h-[560px] overflow-auto">
                <Table dense rows={rows} rowKey={(r) => r.label + r.rr} columns={[
                  { key: "label", label: "Strategy", render: (r) => <span className="text-ink-100">{r.label}</span> },
                  { key: "family", label: "Type", render: (r) => <Badge tone={r.family === "model" ? "research" : r.family === "algo" ? "info" : undefined}>{FAMILY_LABEL[r.family]}</Badge> },
                  { key: "rr", label: "R:R", align: "right", render: (r) => `1:${r.rr}` },
                  { key: "trades", label: "Trades", align: "right", render: (r) => num(r.trades, 0) },
                  { key: "win_rate", label: "Win rate", align: "right", render: (r) => <span className={r.win_rate >= 0.6 ? "text-up" : ""}>{pct(r.win_rate, 1)}</span> },
                  { key: "net_pnl", label: "Net $", align: "right", render: (r) => <span className={r.net_pnl >= 0 ? "text-up" : "text-down"}>{usd(r.net_pnl)}</span> },
                  { key: "profit_factor", label: "PF", align: "right", render: (r) => num(r.profit_factor, 2) },
                  { key: "expectancy", label: "$ / trade", align: "right", render: (r) => usd(r.expectancy, 2) },
                  { key: "max_drawdown", label: "Max DD", align: "right", render: (r) => usd(-r.max_drawdown) },
                  { key: "halves", label: "1st / 2nd half", align: "right", render: (r) => <span>{usd(r.first_half_net)} / {usd(r.second_half_net)}</span> },
                  { key: "verdict", label: "Verdict", render: (r) => <Badge tone={verdictTone(r.verdict === "VALIDATED_BOTH_HALVES" ? "ACCEPT" : r.verdict === "PROFITABLE_NOT_SIGNIFICANT" ? "INCONCLUSIVE" : "REJECT")}>{VERDICT_LABEL[r.verdict] ?? r.verdict}</Badge> },
                  { key: "run", label: "", render: (r) => <Button size="sm" variant="ghost" loading={busy === r.label + r.rr} onClick={() => runOne(r.config.strategy, r.label, r.rr)}><Play className="h-3 w-3" />Full report</Button> },
                ]} />
              </div>
            </>
          )}
        </Panel>
      )}

      <Panel title="Backtest one strategy" code="ONE" bodyClass="p-0">
        {catalog.data && (
          <Table dense rows={catalog.data.sweep.catalog} rowKey={(r) => r.label} columns={[
            { key: "label", label: "Strategy", render: (r) => <span className="text-ink-100">{r.label}</span> },
            { key: "family", label: "Type", render: (r) => <Badge tone={r.family === "model" ? "research" : r.family === "algo" ? "info" : undefined}>{FAMILY_LABEL[r.family]}</Badge> },
            { key: "run", label: `Run at 1:${singleRR} · ${contracts} contract(s)`, render: (r) => (
              <Button size="sm" loading={busy === r.label + singleRR} onClick={() => runOne(r.strategy, r.label, singleRR)}><Play className="h-3 w-3" />Backtest</Button>) },
          ]} />
        )}
        <div className="px-3 py-2 font-mono text-2xs text-ink-500">Your own rule strategies are in Rule builder. ML strategies use only out-of-sample predictions (models never saw the day they trade).</div>
      </Panel>
    </div>
  );
}
