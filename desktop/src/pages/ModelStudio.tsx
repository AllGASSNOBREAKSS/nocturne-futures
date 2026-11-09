import { useState } from "react";
import { Play, Save, Square } from "lucide-react";
import { useAction, useApi } from "@/lib/hooks";
import { ago, cn, num, signed } from "@/lib/format";
import { Badge, Button, ErrorState, Field, Input, KV, Panel, Progress, Query, Segmented, Select, Stat, Table } from "@/components/ui";
import { Bars, Reliability } from "@/components/charts";
import type { Job } from "@/lib/api";

const DEFAULT = { name: "NQ 350pt range · price+vol", source: "databento", root: "NQ", objective: "range_ge_points", threshold_points: 350, threshold_atr: 1.0,
  geometry: "0.5x0.25", side: "long", model: "logistic",
  feature_families: ["price", "volatility"], first_test_year: 2012, last_test_year: 2026, holdout_from: 2023, training_window_years: null as number | null,
  embargo_days: 5, calibration_rows: 250, C: 0.2, n_estimators: 200, learning_rate: 0.03, num_leaves: 15, max_depth: 6 };

export default function ModelStudio() {
  const [cfg, setCfg] = useState<any>(DEFAULT);
  const [selected, setSelected] = useState<string | null>(null);
  const catalog = useApi<any>("/v1/indicators/catalog");
  const jobs = useApi<Job[]>("/v1/training-jobs", { refetchInterval: 3000 });
  const saved = useApi<any[]>("/v1/configs/model");
  const start = useAction<any>("/v1/training-jobs", ["/v1/training-jobs"]);
  const save = useAction<any>("/v1/configs/model", ["/v1/configs/model"]);
  const set = (k: string, v: any) => setCfg((c: any) => ({ ...c, [k]: v }));
  const db = catalog.data?.databento;
  const authentic = cfg.source === "databento";
  const families = (authentic ? db?.feature_families : catalog.data?.feature_families) ?? {};
  const objectives: string[] = (authentic ? db?.objectives : catalog.data?.objectives) ?? [];

  return (
    <div className="grid min-h-full grid-cols-12 gap-3">
      <Panel title="New experiment" code="ML" className="col-span-4" bodyClass="space-y-3">
        <Field label="Experiment name"><Input value={cfg.name} onChange={(e) => set("name", e.target.value)} /></Field>
        <Field label="Data source">
          <Segmented value={cfg.source} options={[{ value: "databento", label: "DATABENTO 2010–2026" }, { value: "yahoo", label: "YAHOO (PHASE 3V)" }]}
            onChange={(v) => setCfg({ ...cfg, source: v, objective: "direction", feature_families: ["price"], first_test_year: v === "databento" ? 2012 : 2008, holdout_from: v === "databento" ? 2023 : 2024 })} />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Instrument"><Segmented value={cfg.root} options={["NQ", "ES"] as const} onChange={(v) => set("root", v)} /></Field>
          <Field label="Model family"><Select value={cfg.model} onChange={(e) => set("model", e.target.value)}>
            {(catalog.data?.models ?? []).map((m: string) => <option key={m} value={m}>{m.replace("_", " ")}</option>)}</Select></Field>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Prediction objective"><Select value={cfg.objective} onChange={(e) => set("objective", e.target.value)}>
            {objectives.map((o) => <option key={o} value={o}>{o.replaceAll("_", " ")}</option>)}</Select></Field>
          {cfg.objective === "range_ge_points" && <Field label="Threshold (points)">{authentic
            ? <Select value={cfg.threshold_points} onChange={(e) => set("threshold_points", Number(e.target.value))}>{(db?.point_thresholds?.[cfg.root] ?? []).map((n: number) => <option key={n} value={n}>{n}</option>)}</Select>
            : <Input type="number" value={cfg.threshold_points} onChange={(e) => set("threshold_points", Number(e.target.value))} />}</Field>}
          {cfg.objective === "range_ge_atr" && <Field label="Threshold (× ATR20)"><Select value={cfg.threshold_atr} onChange={(e) => set("threshold_atr", Number(e.target.value))}>
            {(db?.atr_thresholds ?? []).map((n: number) => <option key={n} value={n}>{n}</option>)}</Select></Field>}
          {cfg.objective === "target_before_stop" && <Field label="Geometry · side (ATR multiples)"><div className="flex gap-1">
            <Select value={cfg.geometry} onChange={(e) => set("geometry", e.target.value)}>{(db?.tbs_geometries ?? []).map((g: string) => <option key={g} value={g}>target {g.replace("x", " / stop ")}</option>)}</Select>
            <Select className="w-24" value={cfg.side} onChange={(e) => set("side", e.target.value)}><option value="long">long</option><option value="short">short</option></Select></div></Field>}
        </div>
        {authentic && db?.descriptions?.[cfg.objective] && <div className="font-mono text-2xs text-ink-500">{db.descriptions[cfg.objective]}</div>}
        <Field label="Feature families (point-in-time)">
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(families).map(([fam, cols]: any) => {
              const on = cfg.feature_families.includes(fam);
              return (
                <button key={fam} title={cols.join(", ")} onClick={() => set("feature_families", on ? cfg.feature_families.filter((f: string) => f !== fam) : [...cfg.feature_families, fam])}
                  className={cn("rounded-[2px] border px-2 py-1 font-mono text-2xs uppercase tracking-wider transition", on ? "border-amber-500/60 bg-amber-500/10 text-amber-300" : "border-ink-700 text-ink-400 hover:text-ink-200")}>
                  {fam.replace("_", " ")} <span className="text-ink-500">{cols.length}</span></button>
              );
            })}
          </div>
        </Field>
        <div className="grid grid-cols-3 gap-2">
          <Field label="First test yr"><Input type="number" value={cfg.first_test_year} onChange={(e) => set("first_test_year", Number(e.target.value))} /></Field>
          <Field label="Holdout from"><Input type="number" value={cfg.holdout_from} onChange={(e) => set("holdout_from", Number(e.target.value))} /></Field>
          <Field label="Last test yr"><Input type="number" value={cfg.last_test_year} onChange={(e) => set("last_test_year", Number(e.target.value))} /></Field>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <Field label="Train window"><Select value={cfg.training_window_years ?? ""} onChange={(e) => set("training_window_years", e.target.value ? Number(e.target.value) : null)}>
            <option value="">Expanding</option>{[3, 5, 10, 15, 20].map((y) => <option key={y} value={y}>{y} years</option>)}</Select></Field>
          <Field label="Embargo days"><Input type="number" value={cfg.embargo_days} onChange={(e) => set("embargo_days", Number(e.target.value))} /></Field>
          <Field label="Calib. rows"><Input type="number" value={cfg.calibration_rows} onChange={(e) => set("calibration_rows", Number(e.target.value))} /></Field>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {cfg.model === "logistic" && <Field label="L2 C"><Input type="number" step="0.05" value={cfg.C} onChange={(e) => set("C", Number(e.target.value))} /></Field>}
          {(cfg.model === "lightgbm" || cfg.model === "random_forest" || cfg.model === "gradient_boosting") && <Field label="Trees"><Input type="number" value={cfg.n_estimators} onChange={(e) => set("n_estimators", Number(e.target.value))} /></Field>}
          {cfg.model === "lightgbm" && <><Field label="Learn rate"><Input type="number" step="0.01" value={cfg.learning_rate} onChange={(e) => set("learning_rate", Number(e.target.value))} /></Field>
            <Field label="Leaves"><Input type="number" value={cfg.num_leaves} onChange={(e) => set("num_leaves", Number(e.target.value))} /></Field></>}
          {cfg.model === "random_forest" && <Field label="Max depth"><Input type="number" value={cfg.max_depth} onChange={(e) => set("max_depth", Number(e.target.value))} /></Field>}
        </div>
        <div className="flex gap-2 pt-1">
          <Button onClick={() => start.mutate(cfg, { onSuccess: (r: any) => r.job_id && setSelected(r.job_id) })} loading={start.isPending}><Play className="h-3 w-3" />Start training</Button>
          <Button variant="outline" onClick={() => save.mutate({ name: cfg.name, config: cfg })} loading={save.isPending}><Save className="h-3 w-3" />Save config</Button>
        </div>
        {start.data?.status === "REJECTED" && <ErrorState error={new Error(start.data.errors.join(" · "))} />}
        {start.error && <ErrorState error={start.error} />}
        {save.data && <div className="font-mono text-2xs text-up">Saved {save.data.name} v{save.data.version}</div>}
        <div className="rounded-[3px] border border-ink-700 bg-ink-900/60 p-2 font-mono text-2xs leading-relaxed text-ink-400">
          Annual walk-forward, embargo, separate Platt calibration slice and a trailing-frequency baseline. Trained models stay research-only; no promotion or trading.
        </div>
        {!!saved.data?.length && (
          <div>
            <div className="mb-1 font-mono text-2xs uppercase tracking-widest text-ink-500">Saved configs</div>
            {saved.data.map((s) => (
              <button key={s.name} onClick={() => setCfg({ ...DEFAULT, ...s.config })} className="flex w-full items-center justify-between rounded px-1 py-1 font-mono text-[11px] text-ink-200 hover:bg-ink-800">
                <span>{s.name}</span><span className="text-ink-500">v{s.version} · {ago(s.saved_at)}</span></button>
            ))}
          </div>
        )}
      </Panel>
      <Panel title="Experiments" code="EXP" className="col-span-8">
        <Query q={jobs}>{(rows) => rows.length ? (
          <Table rows={rows} onRow={(j) => setSelected(j.job_id)} columns={[
            { key: "name", label: "Experiment", render: (j) => <span className={cn("text-ink-100", selected === j.job_id && "text-amber-300")}>{j.name ?? j.job_id.slice(0, 8)}</span> },
            { key: "m", label: "Model", render: (j) => `${j.config.source === "databento" ? "DB" : "YH"} · ${j.config.root} · ${j.config.model}` },
            { key: "o", label: "Objective", render: (j) => j.config.objective + (j.config.objective === "range_ge_points" ? ` ${j.config.threshold_points}` : j.config.objective === "range_ge_atr" ? ` ${j.config.threshold_atr}×ATR` : j.config.objective === "target_before_stop" ? ` ${j.config.side} ${j.config.geometry}` : "") },
            { key: "state", label: "State", render: (j) => j.state === "RUNNING" ? <div className="w-28"><Progress value={j.progress?.percent ?? 2} /></div> : <Badge>{j.state}</Badge> },
            { key: "v", label: "Verdict", render: (j) => j.result?.verdict ? <Badge>{j.result.verdict}</Badge> : j.result?.reason ? <Badge tone="down">{j.result.reason}</Badge> : "—" },
            { key: "d", label: "Dev Δ", align: "right", render: (j) => <span className={j.result?.headline?.development < 0 ? "text-up" : "text-down"}>{signed(j.result?.headline?.development)}</span> },
            { key: "h", label: "Holdout Δ", align: "right", render: (j) => <span className={j.result?.headline?.holdout < 0 ? "text-up" : "text-down"}>{signed(j.result?.headline?.holdout)}</span> },
            { key: "created", label: "Started", align: "right", render: (j) => ago(j.created) }]} />
        ) : <div className="font-mono text-xs text-ink-400">No experiments yet — configure one on the left and start training.</div>}</Query>
        <div className="mt-2 font-mono text-2xs text-ink-500">Δ = model Brier (or pinball) minus trailing baseline; negative is better.</div>
      </Panel>
      {selected && <ExperimentDetail id={selected} />}
    </div>
  );
}

function ExperimentDetail({ id }: { id: string }) {
  const q = useApi<Job>(`/v1/training-jobs/${id}`, { refetchInterval: 2500 });
  const cancel = useAction(`/v1/jobs/${id}/cancel`, ["/v1/training-jobs"]);
  return (
    <Panel title="Experiment detail" code="DTL" className="col-span-12" actions={q.data?.state === "RUNNING" || q.data?.state === "QUEUED" ? <Button size="sm" variant="danger" onClick={() => cancel.mutate({})}><Square className="h-3 w-3" />Cancel</Button> : null}>
      <Query q={q}>{(j) => {
        const r = j.report;
        const quantile = r?.objective === "range_quantile";
        return (
          <div className="grid grid-cols-12 gap-3">
            <div className="col-span-3 space-y-2">
              <KV items={[["Job", j.job_id.slice(0, 12)], ["State", <Badge key="s">{j.state}</Badge>], ["Progress", `${j.progress?.percent ?? 0}% ${j.progress?.message ?? ""}`],
                ["Sessions scored", r?.sessions_scored ?? "—"], ["Artifact", r?.artifact_sha256?.slice(0, 12) ?? "—"], ["Dataset rolls", r?.dataset?.rolls ?? "—"],
                ["Excluded near roll", r?.dataset?.excluded_near_roll ?? "—"], ["Verdict", r?.verdict ? <Badge key="v">{r.verdict}</Badge> : "—"], ["Trading", "NO_TRADE"]]} />
            </div>
            <div className="col-span-5 space-y-2">
              {r?.metrics && Object.entries(r.metrics).map(([era, m]: any) => quantile ? (
                <div key={era} className="grid grid-cols-4 gap-2">
                  <Stat label={`${era} pinball`} value={num(m.model?.mean_pinball, 2)} sub={`baseline ${num(m.baseline?.mean_pinball, 2)}`} />
                  <Stat label="P50 cov" value={num(m.model?.coverage_q50 * 100, 1) + "%"} /><Stat label="P80 cov" value={num(m.model?.coverage_q80 * 100, 1) + "%"} />
                  <Stat label="Δ [95% CI]" value={signed(m.pinball_model_minus_baseline?.mean, 2)} sub={m.pinball_model_minus_baseline?.ci95?.map((x: number) => x.toFixed(2)).join(" … ")} />
                </div>
              ) : (
                <div key={era} className="grid grid-cols-4 gap-2">
                  <Stat label={`${era} AUC`} value={num(m.model?.auc, 3)} sub={`n=${m.model?.n}`} />
                  <Stat label="Brier model" value={num(m.model?.brier, 4)} sub={`baseline ${num(m.baseline?.brier, 4)}`} />
                  <Stat label="Bal. accuracy" value={num(m.model?.balanced_accuracy, 3)} sub={`log loss ${num(m.model?.log_loss, 3)}`} />
                  <Stat label="Δ Brier [95% CI]" value={signed(m.brier_model_minus_baseline?.mean)} valueClass={m.brier_model_minus_baseline?.mean < 0 ? "text-up" : "text-down"}
                    sub={m.brier_model_minus_baseline?.ci95?.map((x: number) => x.toFixed(4)).join(" … ")} />
                </div>
              ))}
              {r?.by_year && <Bars signed height={120} data={Object.entries(r.by_year).map(([y, v]: any) => ({ label: y.slice(2), value: quantile ? v.coverage_q80 - 0.8 : v.brier_baseline - v.brier_model }))}
                format={(v) => v.toFixed(4)} />}
              <div className="font-mono text-2xs text-ink-500">{quantile ? "By year: P80 coverage minus 0.80" : "By year: baseline Brier minus model Brier (green = model better)"}</div>
            </div>
            <div className="col-span-4 space-y-2">
              {r?.metrics?.development?.reliability && <><div className="font-mono text-2xs uppercase tracking-widest text-ink-500">Reliability (development)</div><Reliability bins={r.metrics.development.reliability} height={170} /></>}
              {r?.feature_importance && <Table dense rows={r.feature_importance.slice(0, 10)} columns={[{ key: "feature", label: "Feature" },
                { key: "importance", label: "Importance", align: "right", render: (f) => <div className="flex items-center justify-end gap-2"><div className="h-1.5 rounded bg-amber-500" style={{ width: `${f.importance * 140}px` }} />{(f.importance * 100).toFixed(1)}%</div> }]} />}
            </div>
            {r?.economics && (
              <div className="col-span-12 rounded-[3px] border border-ink-700 p-2">
                <div className="mb-1 font-mono text-2xs uppercase tracking-widest text-amber-500">Economics — {r.economics.rule}</div>
                <Table dense rows={["development", "holdout"].flatMap((era) => ["model_filtered", "always_trade"].map((k) => ({ era, k, ...(r.economics[era]?.[k] ?? {}) })))} columns={[
                  { key: "era", label: "Era" }, { key: "k", label: "Rule", render: (x) => x.k.replace("_", " ") }, { key: "n", label: "Trades", align: "right" },
                  { key: "mean_r", label: "Mean R", align: "right", render: (x) => <span className={x.mean_r > 0 ? "text-up" : "text-down"}>{num(x.mean_r, 3)}</span> },
                  { key: "ci95", label: "95% CI", align: "right", render: (x) => x.ci95 ? `${num(x.ci95[0], 3)} … ${num(x.ci95[1], 3)}` : "—" },
                  { key: "win_rate", label: "Win %", align: "right", render: (x) => x.win_rate != null ? `${(x.win_rate * 100).toFixed(1)}%` : "—" }]} />
              </div>
            )}
            <pre className="col-span-12 max-h-40 overflow-auto rounded-[3px] border border-ink-800 bg-ink-950 p-2 font-mono text-2xs text-ink-400">{j.logs?.["progress.log"] || "No log output yet."}{j.logs?.["stderr.log"] ? `\n${j.logs["stderr.log"]}` : ""}</pre>
          </div>
        );
      }}</Query>
    </Panel>
  );
}
