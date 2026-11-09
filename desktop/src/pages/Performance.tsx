import { useState } from "react";
import { useApi } from "@/lib/hooks";
import { num, pct, signed } from "@/lib/format";
import { Badge, Panel, Query, Segmented, Stat, Table } from "@/components/ui";
import type { Job } from "@/lib/api";

export default function Performance() {
  const [root, setRoot] = useState<"NQ" | "ES">("NQ");
  const research = useApi<any>("/v1/research");
  const shadow = useApi<any>("/v1/forecasts/ndx-shadow");
  const models = useApi<any>("/v1/models");
  return (
    <div className="grid min-h-full grid-cols-12 gap-3">
      <Panel title="Authentic Databento walk-forward — Phase 4C sweep (2012–2026, holdout 2023+ reused)" code="DB" className="col-span-12" accent="info">
        <Query q={research}>{(r) => r.phase4c_ml ? (
          <>
            <div className="mb-2 flex gap-2">{Object.entries(r.phase4c_ml.verdicts).map(([k, v]: any) => <Badge key={k}>{`${k} ${v}`}</Badge>)}</div>
            <Table dense maxRows={200} rows={r.phase4c_ml.rows.filter((x: any) => x.group === "main" && x.development)} columns={[
              { key: "root", label: "Root" },
              { key: "o", label: "Objective", render: (x: any) => `${x.objective.replaceAll("_", " ")}${x.threshold_points ? " " + x.threshold_points : ""}${x.threshold_atr ? " " + x.threshold_atr + "×ATR" : ""}${x.geometry ? ` ${x.side} ${x.geometry}` : ""}` },
              { key: "model", label: "Model" },
              { key: "auc", label: "Dev AUC", align: "right", render: (x: any) => num(x.development.auc, 3) },
              { key: "bal", label: "Bal. acc", align: "right", render: (x: any) => num(x.development.balanced_accuracy, 3) },
              { key: "brier", label: "Brier (base)", align: "right", render: (x: any) => x.development.brier != null ? `${num(x.development.brier, 4)} (${num(x.development.baseline_brier, 4)})` : `${num(x.development.pinball, 1)} (${num(x.development.baseline_pinball, 1)})` },
              { key: "ll", label: "Log loss", align: "right", render: (x: any) => num(x.development.log_loss, 3) },
              { key: "d", label: "Dev Δ [CI]", align: "right", render: (x: any) => <span className={x.development.delta < 0 ? "text-up" : "text-down"}>{signed(x.development.delta)} [{signed(x.development.ci95?.[0])}, {signed(x.development.ci95?.[1])}]</span> },
              { key: "h", label: "Hold Δ", align: "right", render: (x: any) => <span className={(x.holdout?.delta ?? 0) < 0 ? "text-up" : "text-down"}>{signed(x.holdout?.delta)}</span> },
              { key: "cal", label: "Cal. gap", align: "right", render: (x: any) => num(x.development.max_calibration_gap, 3) },
              { key: "v", label: "Verdict", render: (x: any) => <Badge>{x.verdict}</Badge> }]} />
          </>
        ) : <div className="font-mono text-xs text-ink-400">Phase 4C sweep not run yet.</div>}</Query>
      </Panel>
      <Panel title={`Phase 3V Yahoo-proxy walk-forward — ${root} (retrospective, superseded by Databento above)`} code="HIST" className="col-span-12"
        actions={<Segmented value={root} options={["NQ", "ES"] as const} onChange={setRoot} />}>
        <Query q={research}>{(r) => {
          const tasks = r.phase3v?.[root]?.tasks ?? {};
          const rows = Object.entries(tasks).flatMap(([task, cfgs]: any) => Object.entries(cfgs).map(([cfg, m]: any) => ({ task, cfg, ...m })));
          return (
            <>
              <Table dense rows={rows} columns={[
                { key: "task", label: "Objective", render: (x) => <span className="text-ink-100">{x.task.replaceAll("_", " ")}</span> },
                { key: "cfg", label: "Features · model", render: (x) => x.cfg.replaceAll("_", " ") },
                { key: "dev_auc", label: "Dev AUC", align: "right", render: (x) => num(x.dev_auc, 3) },
                { key: "dev_brier", label: "Dev Brier", align: "right", render: (x) => num(x.dev_brier, 4) },
                { key: "dev_baseline_brier", label: "Baseline", align: "right", render: (x) => num(x.dev_baseline_brier, 4) },
                { key: "dev_delta", label: "Dev Δ [95% CI]", align: "right", render: (x) => <span className={x.dev_delta < 0 ? "text-up" : "text-down"}>{signed(x.dev_delta)} {x.dev_ci ? `[${signed(x.dev_ci[0])}, ${signed(x.dev_ci[1])}]` : ""}</span> },
                { key: "holdout_auc", label: "Hold AUC", align: "right", render: (x) => num(x.holdout_auc, 3) },
                { key: "holdout_delta", label: "Hold Δ", align: "right", render: (x) => <span className={x.holdout_delta < 0 ? "text-up" : "text-down"}>{signed(x.holdout_delta)}</span> },
                { key: "increment", label: "vs price-only", render: (x) => x.increment ? <Badge>{x.increment}</Badge> : "—" },
                { key: "verdict", label: "Verdict", render: (x) => <Badge>{x.verdict}</Badge> }]} />
              <div className="mt-2 font-mono text-2xs text-ink-500">Brier Δ = model − trailing-frequency baseline (negative is better). Each metric is reported separately; there is no blended “accuracy score”. Generated {r.phase3v_generated_at}.</div>
            </>
          );
        }}</Query>
      </Panel>
      <Panel title="Genuine forward record — NDX range shadow" code="FWD" className="col-span-5" accent="research">
        <Query q={shadow}>{(s) => {
          const agg = s.report?.aggregate_descriptive_only;
          return (
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Issued" value={(s.forecasts ?? []).length} /><Stat label="Matured" value={(s.outcomes ?? []).length} />
                <Stat label="Audit-blocked" value={(s.quarantined ?? []).length} valueClass="text-warn" />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Mean pinball" value={num(agg?.mean_pinball_model, 4)} sub={`baseline ${num(agg?.mean_pinball_trailing_baseline, 4)}`} />
                <Stat label="P80 coverage" value={pct(agg?.p80_coverage)} sub={`n=${agg?.n}`} />
                <Stat label="Status" value={<Badge tone="warn">{s.operational_status}</Badge>} />
              </div>
              <div className="font-mono text-2xs text-ink-500">Two matured observations cannot establish calibration. Historical metrics above are retrospective and labelled as such.</div>
            </div>
          );
        }}</Query>
      </Panel>
      <Panel title="Studio experiments" code="EXP" className="col-span-7">
        <Query q={models}>{(m) => m.experiments.length ? (
          <Table dense rows={m.experiments} columns={[{ key: "n", label: "Experiment", render: (j: Job) => j.name ?? j.job_id.slice(0, 8) },
            { key: "o", label: "Objective", render: (j: Job) => `${j.config.root} ${j.config.objective}` }, { key: "m", label: "Model", render: (j: Job) => j.config.model },
            { key: "d", label: "Dev Δ", align: "right", render: (j: Job) => signed(j.result?.headline?.development) },
            { key: "h", label: "Hold Δ", align: "right", render: (j: Job) => signed(j.result?.headline?.holdout) },
            { key: "v", label: "Verdict", render: (j: Job) => <Badge>{j.result?.verdict}</Badge> }]} />
        ) : <div className="font-mono text-xs text-ink-400">No completed studio experiments yet.</div>}</Query>
        <div className="mt-2 font-mono text-2xs text-ink-500">{models.data?.governance}</div>
      </Panel>
    </div>
  );
}
