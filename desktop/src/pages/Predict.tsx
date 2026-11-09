import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, CircleDot, Newspaper, Radio, RefreshCw } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { cn, num, pct } from "@/lib/format";
import { Badge, Button, ErrorState, Loading, Panel, Segmented } from "@/components/ui";
import { PriceChart } from "@/components/charts";
import type { Root } from "@/lib/api";
import NextSession from "./NextSession";

type Lv = { key: string; name: string; group: string; price: number; distance: number; probability: number; status: string; hit_at: string | null; confluence: string[]; tp?: string };
// The free TradingView embed does not license CME futures; it shows the index CFDs that track them.
const TV = { NQ: "OANDA:NAS100USD", ES: "OANDA:SPX500USD" } as const;
const GROUP_DOT: Record<string, string> = { session: "bg-info", vwap: "bg-research", auction: "bg-violet-400", indicator: "bg-ink-300", reference: "bg-ink-400", ml: "bg-amber-500" };
const MOOD: Record<string, string> = { Bullish: "text-up", "Leaning bullish": "text-up", Bearish: "text-down", "Leaning bearish": "text-down", "Consolidation likely": "text-warn" };

function Card({ label, value, tone, sub, delay = 0 }: { label: string; value: React.ReactNode; tone?: string; sub?: React.ReactNode; delay?: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }} className="rounded-[4px] border border-ink-700 bg-ink-850 p-3">
      <div className="font-mono text-2xs uppercase tracking-[0.16em] text-ink-400">{label}</div>
      <div className={cn("mt-1 font-mono text-xl font-semibold", tone ?? "text-ink-100")}>{value}</div>
      {sub && <div className="mt-1 font-mono text-[11px] leading-snug text-ink-400">{sub}</div>}
    </motion.div>
  );
}

function ProbBar({ p }: { p: number }) {
  return (
    <div className="flex w-[120px] items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded bg-ink-700">
        <motion.div className={cn("h-full rounded", p >= 0.7 ? "bg-up" : p >= 0.4 ? "bg-amber-500" : "bg-ink-400")} initial={{ width: 0 }} animate={{ width: `${Math.max(2, p * 100)}%` }} />
      </div>
      <span className="w-9 text-right tabular-nums text-ink-100">{pct(p, 0)}</span>
    </div>
  );
}

function Targets({ side, rows }: { side: "up" | "down"; rows: Lv[] }) {
  const Icon = side === "up" ? ArrowUpRight : ArrowDownRight;
  return (
    <div>
      <div className={cn("mb-1 flex items-center gap-1 font-mono text-2xs uppercase tracking-widest", side === "up" ? "text-up" : "text-down")}>
        <Icon className="h-3 w-3" />{side === "up" ? "Upside targets" : "Downside targets"}
      </div>
      {rows.length === 0 && <div className="font-mono text-[11px] text-ink-500">No open level with ≥25% probability on this side.</div>}
      {rows.map((l) => (
        <div key={l.key} className="flex items-center gap-2 border-b border-ink-800 py-1.5 font-mono text-[12px]" title={l.confluence.length ? `Within 0.1 ATR: ${l.confluence.join(", ")}` : "No other level nearby"}>
          <Badge tone={side === "up" ? "up" : "down"}>{l.tp}</Badge>
          <span className="flex-1 truncate text-ink-200">{l.name}{l.confluence.length > 0 && <span className="ml-1 text-info">+{l.confluence.length}</span>}</span>
          <span className="tabular-nums text-ink-100">{num(l.price, 2)}</span>
          <span className={cn("w-14 text-right tabular-nums", l.distance >= 0 ? "text-up" : "text-down")}>{l.distance >= 0 ? "+" : ""}{num(l.distance, 0)}</span>
          <ProbBar p={l.probability} />
        </div>
      ))}
    </div>
  );
}

function Live({ root }: { root: Root }) {
  const live = useApi<any>(`/v1/live/${root}`, { refetchInterval: 60_000 });
  const news = useApi<any>(`/v1/news/${root}`, { refetchInterval: 300_000 });
  const [chart, setChart] = useState<"LEVELS" | "TRADINGVIEW">("LEVELS");
  const [showAll, setShowAll] = useState(false);
  const d = live.data;
  const chartLevels = useMemo(() => {
    if (!d) return [];
    const out = [...d.targets.up, ...d.targets.down].map((l: Lv) => ({ name: `${l.tp} ${l.name} ${pct(l.probability, 0)}`, price: l.price, kind: "reference", basis: "" }));
    if (d.vwap) out.push({ name: "VWAP", price: d.vwap.vwap, kind: "auction", basis: "" });
    for (const [k, s] of Object.entries<any>(d.sessions)) if (s) { out.push({ name: `${k} H`, price: s.high, kind: "session", basis: "" }, { name: `${k} L`, price: s.low, kind: "session", basis: "" }); }
    return out;
  }, [d]);
  if (live.isLoading) return <Loading label="Fetching today's session" />;
  if (live.error) return <ErrorState error={live.error} />;
  const s = d.state;
  const im = s.intraday?.measured;
  const ut = d.model.useful_targets;
  const src = `https://s.tradingview.com/widgetembed/?symbol=${encodeURIComponent(TV[root])}&interval=5&theme=dark&style=1&timezone=America%2FNew_York&withdateranges=1&hide_side_toolbar=0&allow_symbol_change=1&saveimage=0&studies=VWAP%40tv-basicstudies`;
  const shownLevels: Lv[] = showAll ? d.levels : d.levels.filter((l: Lv) => Math.abs(l.distance) <= 1.2 * d.atr20);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-4 font-mono text-[11px] text-ink-400">
        <span className="flex items-center gap-1.5"><Radio className="h-3 w-3 animate-pulse text-up" /><span className="text-xl font-semibold text-ink-100 tabular-nums">{num(d.price, 2)}</span></span>
        <span>Session {d.session}</span>
        <span className={d.delay_minutes > 20 ? "text-warn" : ""}>Delayed {num(d.delay_minutes, 0)} min (free feed)</span>
        <span>Probabilities as of <span className="text-amber-400">{d.cutoff_label ?? "pre-London (no cutoff yet)"}</span></span>
        <span>ATR {num(d.atr20, 0)}</span>
        <Button size="sm" variant="ghost" className="ml-auto" onClick={() => { live.refetch(); news.refetch(); }}><RefreshCw className="h-3 w-3" />Refresh</Button>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <Card label="Market now" value={s.headline} tone={MOOD[s.headline]} delay={0}
          sub={im ? <>From here, closes higher <span className="text-ink-100">{pct(im.p_close_higher, 0)}</span> of the time (usual {pct(s.intraday.baseline, 0)}) · {s.confidence} signal</> : "Intraday state forms after 03:00 ET"} />
        <Card label="Daily trend" value={s.daily.label} tone={s.daily.label === "Uptrend" ? "text-up" : s.daily.label === "Downtrend" ? "text-down" : "text-ink-200"} delay={0.05}
          sub={s.daily.measured ? <>Next day up after this label: {pct(s.daily.measured.p_next_up, 0)} (usual {pct(s.daily.baseline.p_next_up, 0)}) · ADX {num(s.daily.adx, 0)}</> : null} />
        <Card label="Position vs VWAP" value={d.vwap ? `${d.vwap.position_sd >= 0 ? "+" : ""}${num(d.vwap.position_sd, 2)}σ` : "—"} delay={0.1}
          tone={d.vwap && d.vwap.position_sd > 0 ? "text-up" : "text-down"}
          sub={d.vwap ? <>VWAP {num(d.vwap.vwap, 2)} · ±1σ {num(d.vwap.l1, 0)}–{num(d.vwap.u1, 0)} · ±2σ {num(d.vwap.l2, 0)}–{num(d.vwap.u2, 0)}</> : null} />
        <Card label="Level model accuracy" value={pct(ut.p_over_80.hit_rate ?? ut.p_over_70.hit_rate, 0)} tone="text-up" delay={0.15}
          sub={<>Real targets (≥¼ ATR away) rated &gt;80% hit this often · {num(ut.p_over_80.n, 0)} cases · AUC {num(d.model.auc, 2)}</>} />
      </div>

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-4 flex flex-col gap-3">
          <Panel title="Take-profit levels" code="TP">
            <div className="space-y-3">
              <Targets side="up" rows={d.targets.up} />
              <Targets side="down" rows={d.targets.down} />
              <div className="font-mono text-2xs leading-relaxed text-ink-500">Nearest open levels ≥0.1 ATR away with ≥25% chance of trading before 16:00 ET. "+n" = other levels within 0.1 ATR (confluence); measured: it adds no accuracy beyond distance.</div>
            </div>
          </Panel>
          <Panel title="Sessions today" code="SES" bodyClass="p-0">
            <table className="w-full font-mono text-[12px] tabular-nums">
              <thead><tr className="text-2xs uppercase tracking-widest text-ink-500"><th className="px-3 py-1 text-left">Session</th><th className="text-right">Open</th><th className="text-right">High</th><th className="text-right">Low</th><th className="px-3 text-right">Range</th></tr></thead>
              <tbody>
                {Object.entries<any>(d.sessions).map(([k, v]) => (
                  <tr key={k} className="border-t border-ink-800">
                    <td className="px-3 py-1.5 text-ink-200">{k}{v && !v.complete && <span className="ml-1 text-2xs text-amber-400">live</span>}</td>
                    <td className="text-right">{v ? num(v.open, 2) : "—"}</td><td className="text-right text-up">{v ? num(v.high, 2) : "—"}</td>
                    <td className="text-right text-down">{v ? num(v.low, 2) : "—"}</td><td className="px-3 text-right text-ink-300">{v ? num(v.high - v.low, 0) : "—"}</td>
                  </tr>
                ))}
                {[["15m opening range", d.orb15], ["30m opening range", d.orb30], ["Initial balance (1h)", d.ib]].map(([k, v]: any) => (
                  <tr key={k} className="border-t border-ink-800 text-ink-300">
                    <td className="px-3 py-1.5">{k}</td><td /><td className="text-right text-up">{v ? num(v.high, 2) : "pending"}</td>
                    <td className="text-right text-down">{v ? num(v.low, 2) : ""}</td><td className="px-3 text-right">{v ? num(v.high - v.low, 0) : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>
        <Panel title={`${root} · today`} code="GP" className="col-span-8" bodyClass="p-0"
          actions={<Segmented value={chart} options={[{ value: "LEVELS", label: "Levels" }, { value: "TRADINGVIEW", label: "TradingView" }]} onChange={setChart} />}>
          {chart === "LEVELS" ? <PriceChart bars={d.bars} levels={chartLevels} height={560} /> :
            <div><iframe title="TradingView" src={src} className="h-[536px] w-full border-0" sandbox="allow-scripts allow-same-origin allow-popups" referrerPolicy="no-referrer" />
              <div className="px-3 py-1 font-mono text-2xs text-ink-500">TradingView free embed shows {TV[root]} (index CFD, tracks {root} but prices differ by the futures basis). CME futures charts need a TradingView account.</div></div>}
        </Panel>
      </div>

      <div className="grid grid-cols-12 gap-3">
        <Panel title="All levels" code="LVL" className="col-span-6" bodyClass="p-0"
          actions={<button className="font-mono text-2xs text-amber-400 hover:underline" onClick={() => setShowAll(!showAll)}>{showAll ? "Near price only" : `Show all ${d.levels.length}`}</button>}>
          <div className="max-h-[420px] overflow-auto">
            {shownLevels.map((l) => (
              <div key={l.key} className={cn("flex items-center gap-2 border-b border-ink-800 px-3 py-1 font-mono text-[11px]", l.status === "HIT" && "opacity-60")}>
                <span className={cn("h-2 w-2 rounded-full", GROUP_DOT[l.group])} />
                <span className="flex-1 truncate text-ink-200">{l.name}</span>
                <span className="tabular-nums text-ink-100">{num(l.price, 2)}</span>
                <span className={cn("w-14 text-right tabular-nums", l.distance >= 0 ? "text-up" : "text-down")}>{l.distance >= 0 ? "+" : ""}{num(l.distance, 0)}</span>
                {l.status === "HIT" ? <span className="w-[120px] text-right text-up"><CircleDot className="mr-1 inline h-3 w-3" />hit {l.hit_at}</span> : <ProbBar p={l.probability} />}
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="News & events" code="NEWS" className="col-span-6" bodyClass="p-0">
          {news.isLoading ? <Loading label="Loading headlines" /> : news.error ? <ErrorState error={news.error} /> : (
            <div className="max-h-[420px] overflow-auto">
              {news.data.calendar.events.filter((e: any) => e.country === "USD").slice(0, 8).map((e: any) => (
                <div key={e.time + e.title} className="border-b border-ink-800 px-3 py-1.5 font-mono text-[11px]">
                  <div className="flex items-center gap-2">
                    <Badge tone={e.impact === "High" ? "down" : "warn"}>{e.impact}</Badge>
                    <span className="text-ink-100">{e.title}</span>
                    <span className="ml-auto text-ink-400">{new Date(e.time).toLocaleString("en-US", { weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: "America/New_York" })} ET</span>
                  </div>
                  {e.measured_impact && <div className="mt-0.5 text-ink-400">Measured on {e.measured_impact.sessions} past days: NY range {num(e.measured_impact.ny_range_vs_normal, 2)}× normal · big-day odds {pct(e.measured_impact.big_day_rate, 0)} vs {pct(e.measured_impact.normal_big_day_rate, 0)} · closed up {pct(e.measured_impact.p_ny_close_up, 0)} (usual {pct(e.measured_impact.normal_p_ny_close_up, 0)})</div>}
                </div>
              ))}
              {news.data.headlines.slice(0, 30).map((h: any) => (
                <a key={h.link} href={h.link} target="_blank" rel="noreferrer" className="block border-b border-ink-800 px-3 py-1.5 font-mono text-[11px] hover:bg-ink-800/60">
                  <div className="flex items-start gap-2">
                    <Newspaper className={cn("mt-0.5 h-3 w-3 shrink-0", h.tone === "positive" ? "text-up" : h.tone === "negative" ? "text-down" : "text-ink-500")} />
                    <span className="flex-1 text-ink-200">{h.title}</span>
                    {typeof h.move_since === "number" && <span className={cn("shrink-0 tabular-nums", h.move_since >= 0 ? "text-up" : "text-down")}>{h.move_since >= 0 ? "+" : ""}{num(h.move_since, 0)} since</span>}
                  </div>
                  <div className="ml-5 text-2xs text-ink-500">{h.source} · {new Date(h.published_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", timeZone: "America/New_York" })} ET · {h.categories.join(", ")}</div>
                </a>
              ))}
              <div className="px-3 py-2 font-mono text-2xs text-ink-500">{news.data.note}</div>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}

export default function Predict() {
  const [root, setRoot] = useState<Root>("NQ");
  const [mode, setMode] = useState<"LIVE" | "NEXT">("LIVE");
  return (
    <div className="mx-auto flex max-w-[1500px] flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3 rounded-[4px] border border-ink-700 bg-gradient-to-r from-ink-850 to-ink-900 p-3">
        <Segmented value={root} options={["NQ", "ES"] as const} onChange={setRoot} />
        <Segmented value={mode} options={[{ value: "LIVE", label: "Today (live)" }, { value: "NEXT", label: "Next session" }]} onChange={setMode} />
        <span className="ml-auto font-mono text-2xs text-ink-500">Research only · NO_TRADE · free delayed data, not a broker feed</span>
      </div>
      {mode === "LIVE" ? <Live key={root} root={root} /> : <NextSession root={root} />}
    </div>
  );
}
