import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Crosshair, RefreshCw, Sparkles } from "lucide-react";
import { useAction, useApi } from "@/lib/hooks";
import { cn, num, pct, when } from "@/lib/format";
import { Badge, Button, ErrorState, Panel, Segmented } from "@/components/ui";
import { PriceChart } from "@/components/charts";
import type { Bar, Root } from "@/lib/api";

type Level = { name: string; price: number; kind: string; basis: string; distance_points: number; side: string; touch_probability: number; bound: string | null; method: string; base_rate?: number };

const KIND = { projection: "bg-amber-500", reference: "bg-ink-300", auction: "bg-research", session: "bg-info" } as Record<string, string>;
const FEATURE = (f: string) => ({ range_atr: "Last range vs ATR", atr20_pts: "ATR level", close_location: "Close position in range", vix: "VIX", vix_chg5: "VIX 5-day change",
  vxn_minus_vix: "VXN − VIX", rth_range_atr: "RTH range", on_range_atr: "Overnight range", ib_range_atr: "Initial balance", vwap_distance_atr: "Close vs VWAP",
  ret_1: "1-day return", ret_5: "5-day return", ret_20: "20-day return", vol_20: "20-day volatility", pos_20: "Position in 20-day range", volume_z: "Volume surprise",
  rth_return: "RTH return", last_hour_return: "Last-hour return", log_level: "Price level" } as Record<string, string>)[f] ?? f;

function Big({ label, value, sub, tone, children }: { label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: string; children?: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="rounded-[4px] border border-ink-700 bg-ink-850 p-4">
      <div className="font-mono text-2xs uppercase tracking-[0.16em] text-ink-400">{label}</div>
      <div className={cn("mt-1 font-mono text-2xl font-semibold tabular-nums", tone ?? "text-ink-100")}>{value}</div>
      {sub && <div className="mt-1 font-mono text-[11px] text-ink-400">{sub}</div>}
      {children}
    </motion.div>
  );
}

export default function Predict() {
  const [root, setRoot] = useState<Root>("NQ");
  const [view, setView] = useState<"LEVELS" | "MARKET">("LEVELS");
  const run = useAction<any>(`/v1/predict/${root}`, []);
  const warm = useApi<any>(`/v1/predict/${root}/status`, { refetchInterval: 4000 });
  const refresh = useAction<any>("/v1/data/refresh", ["/v1/system"]);
  const bars = useApi<{ bars: Bar[] }>(`/v1/markets/${root}/bars?interval=1h&limit=160`);
  const p = run.data;
  useEffect(() => { run.reset(); }, [root]); // eslint-disable-line react-hooks/exhaustive-deps

  const chartLevels = useMemo(() => (p?.levels ?? [])
    .filter((l: Level) => l.kind === "projection" || ["Prior session high", "Prior session low", "Prior session VWAP", "POC"].includes(l.name))
    .map((l: Level) => ({ name: l.name, price: l.price, kind: l.kind === "projection" ? "reference" : l.kind, basis: l.basis })), [p]);
  const ladder: (Level | { settle: true })[] = useMemo(() => {
    if (!p) return [];
    const above = p.levels.filter((l: Level) => l.price >= p.reference_close);
    const below = p.levels.filter((l: Level) => l.price < p.reference_close);
    return [...above, { settle: true }, ...below];
  }, [p]);

  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3 rounded-[4px] border border-ink-700 bg-gradient-to-r from-ink-850 to-ink-900 p-3">
        <Segmented value={root} options={["NQ", "ES"] as const} onChange={setRoot} />
        <Button className="h-10 px-6 text-xs" onClick={() => run.mutate({})} loading={run.isPending}>
          <Crosshair className="h-4 w-4" />{run.isPending ? "Running every model…" : "Predict next session"}
        </Button>
        <Segmented value={view} options={[{ value: "LEVELS", label: "Levels" }, { value: "MARKET", label: "Market outlook" }]} onChange={setView} />
        <div className="ml-auto flex items-center gap-3 font-mono text-[11px] text-ink-400">
          {warm.data && !warm.data.ready && <span className="flex items-center gap-1 text-warn"><Sparkles className="h-3 w-3 animate-pulse" />Preparing models ({warm.data.state})</span>}
          {p && <span>Data through <span className="text-ink-100">{p.data_through}</span> · {p.source}</span>}
          {p && <span>Target <span className="text-amber-400">{p.target_session}</span></span>}
          <Button size="sm" variant="ghost" onClick={() => refresh.mutate({})} loading={refresh.isPending}><RefreshCw className="h-3 w-3" />Refresh data</Button>
        </div>
      </div>

      {run.error && <ErrorState error={run.error} />}
      {!p && !run.isPending && (
        <div className="grid h-[420px] place-items-center rounded-[4px] border border-dashed border-ink-700 text-center">
          <div>
            <Crosshair className="mx-auto mb-3 h-8 w-8 text-amber-500" />
            <div className="font-mono text-sm text-ink-100">Press <span className="text-amber-400">Predict next session</span></div>
            <div className="mt-1 max-w-md font-mono text-[11px] text-ink-500">Runs the calibrated level models, regime classifiers, indicators and the strategy check on 16 years of NQ/ES contract data, then maps tomorrow's key levels with the probability of each being reached.</div>
          </div>
        </div>
      )}

      {p && (
        <>
          <div className="grid grid-cols-4 gap-3">
            <Big label="Expected range" value={`${num(p.expected_range_points.p50, 0)} pts`} sub={`80% band: ${num(p.expected_range_points.p80_low, 2)} – ${num(p.expected_range_points.p80_high, 2)}`} />
            <Big label="Volatility outlook" value={p.regime.expansion.probability > p.regime.expansion.base_rate * 1.3 ? "Expansion risk" : p.regime.compression.probability > p.regime.compression.base_rate * 1.3 ? "Quiet / compression" : "Normal"}
              tone={p.regime.expansion.probability > p.regime.expansion.base_rate * 1.3 ? "text-down" : "text-ink-100"}
              sub={`Big day ${pct(p.regime.expansion.probability, 0)} (usual ${pct(p.regime.expansion.base_rate, 0)}) · Quiet day ${pct(p.regime.compression.probability, 0)} (usual ${pct(p.regime.compression.base_rate, 0)})`} />
            <Big label="Direction" value="No edge" tone="text-ink-300" sub={`Model ${pct(p.direction.p_up, 0)} up vs ${pct(p.direction.base_rate, 0)} usual — failed validation, treat as 50/50`} />
            <Big label="Measured accuracy (2013–2026)" value={`${pct(p.track_record.coverage.up.p90, 0)} / ${pct(p.track_record.coverage.dn.p90, 0)}`}
              sub={`of highs/lows stayed inside the 90% levels (${num(p.track_record.sessions, 0)} sessions) · prior-high calls >70%: hit ${pct(p.track_record.classifiers.touch_prior_high.hit_rate_when_p_over_70, 0)}`} tone="text-up" />
          </div>

          {view === "LEVELS" ? (
            <div className="grid grid-cols-12 gap-3">
              <Panel title={`${root} levels for ${p.target_session}`} code="LVL" className="col-span-5" bodyClass="p-0">
                <div className="divide-y divide-ink-800">
                  {ladder.map((l, i) => "settle" in l ? (
                    <div key="settle" className="flex items-center gap-2 bg-amber-500/10 px-3 py-1.5 font-mono text-[11px]">
                      <span className="h-2 w-2 rounded-full bg-amber-500" /><span className="flex-1 font-semibold text-amber-300">Last settle</span>
                      <span className="tabular-nums text-amber-300">{num(p.reference_close, 2)}</span><span className="w-16" /><span className="w-[150px]" />
                    </div>
                  ) : (
                    <motion.div key={l.name + i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.015 }}
                      className="flex items-center gap-2 px-3 py-1.5 font-mono text-[11px] hover:bg-ink-800/60" title={`${l.basis} · ${l.method}`}>
                      <span className={cn("h-2 w-2 rounded-full", KIND[l.kind] ?? "bg-ink-500")} />
                      <span className={cn("flex-1 truncate", l.kind === "projection" ? "text-amber-200" : "text-ink-200")} title={l.name}>{l.name}</span>
                      {(l as any).confluence > 1 && <Badge tone="info">{(l as any).confluence}×</Badge>}
                      <span className="tabular-nums text-ink-100">{num(l.price, 2)}</span>
                      <span className={cn("w-16 text-right tabular-nums", l.distance_points >= 0 ? "text-up" : "text-down")}>{l.distance_points >= 0 ? "+" : ""}{num(l.distance_points, 0)}</span>
                      <div className="flex w-[150px] items-center gap-2">
                        <div className="h-1.5 flex-1 overflow-hidden rounded bg-ink-700">
                          <motion.div className={cn("h-full rounded", l.touch_probability >= 0.7 ? "bg-up" : l.touch_probability >= 0.4 ? "bg-amber-500" : "bg-ink-400")}
                            initial={{ width: 0 }} animate={{ width: `${Math.max(2, l.touch_probability * 100)}%` }} transition={{ duration: 0.5 }} />
                        </div>
                        <span className="w-10 text-right tabular-nums text-ink-100">{l.bound ?? pct(l.touch_probability, 0)}</span>
                      </div>
                    </motion.div>
                  ))}
                </div>
                <div className="border-t border-ink-800 px-3 py-2 font-mono text-2xs text-ink-500">Bar = probability the next session trades at the level. Amber rows are the model's projected high/low zones.</div>
              </Panel>
              <Panel title={`${root} · last ~7 sessions with tomorrow's levels`} code="GP" className="col-span-7" bodyClass="p-0">
                {bars.data ? <PriceChart bars={bars.data.bars} levels={chartLevels} height={560} /> : null}
              </Panel>
            </div>
          ) : (
            <div className="grid grid-cols-12 gap-3">
              <Panel title="What drives this forecast" code="WHY" className="col-span-6">
                {p.drivers.map((d: any) => (
                  <div key={d.model} className="mb-3">
                    <div className="mb-1 font-mono text-2xs uppercase tracking-widest text-ink-500">{d.model === "expansion" ? "Big-day probability" : "Prior-high touch probability"}</div>
                    {d.top.map((t: any) => (
                      <div key={t.feature} className="flex items-center gap-2 py-0.5 font-mono text-[12px]">
                        <Badge tone={t.effect === "raises" ? "up" : "down"}>{t.effect}</Badge>
                        <span className="text-ink-200">{FEATURE(t.feature)}</span><span className="ml-auto tabular-nums text-ink-400">{t.value ?? "—"}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </Panel>
              <Panel title="Indicators (last session)" code="IND" className="col-span-3">
                <div className="grid grid-cols-2 gap-2 font-mono text-[12px]">
                  {[["RSI 14", p.indicators.rsi14], ["ADX 14", p.indicators.adx14], ["ATR 20", p.indicators.atr20], ["VIX", p.indicators.vix],
                    ["vs SMA 50", `${num(p.indicators.close_vs_sma50, 1)}%`], ["vs SMA 200", `${num(p.indicators.close_vs_sma200, 1)}%`],
                    ["Close in range", pct(p.indicators.close_location, 0)], ["Last range", `${num(p.indicators.last_range_atr, 2)}× ATR`]].map(([k, v]) => (
                    <div key={k as string} className="rounded-[3px] border border-ink-700 p-2"><div className="text-2xs uppercase tracking-widest text-ink-500">{k}</div><div className="text-ink-100">{v ?? "—"}</div></div>
                  ))}
                </div>
              </Panel>
              <Panel title="Model checks" code="CHK" className="col-span-3">
                <div className="space-y-2 font-mono text-[11px] text-ink-300">
                  <div>Strategies: <span className="text-down">{p.strategies.accepted ?? 0} / {p.strategies.candidates ?? 0} validated</span> — {p.strategies.message}</div>
                  {Object.entries(p.track_record.classifiers).map(([k, v]: any) => (
                    <div key={k} className="flex justify-between"><span>{k.replaceAll("_", " ")}</span><span className="text-ink-100">AUC {num(v.auc, 2)} · Brier {num(v.brier, 3)} vs {num(v.baseline_brier, 3)}</span></div>
                  ))}
                  <div className="pt-1 text-ink-500">Live record: {p.journal.issued} issued · {p.journal.evaluated} scored{p.journal.high_band_hit_rate != null ? ` · highs inside 10–90% band ${pct(p.journal.high_band_hit_rate, 0)}` : ""}</div>
                  <div className="text-ink-500">Model {p.model_version} · trained through {p.trained_through} · {when(new Date().toISOString())}</div>
                </div>
              </Panel>
            </div>
          )}
        </>
      )}
    </div>
  );
}
