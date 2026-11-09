import { useEffect, useRef } from "react";
import { createChart, CrosshairMode, LineStyle, type IChartApi, type UTCTimestamp, type SeriesMarker, type Time } from "lightweight-charts";
import type { Bar, Level } from "@/lib/api";

const NY = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
const NYDAY = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", month: "short", day: "2-digit" });
const NYTIME = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit", hour12: false });

const base = (el: HTMLElement) => createChart(el, {
  autoSize: true,
  layout: { background: { color: "transparent" }, textColor: "#8592a3", fontFamily: "IBM Plex Mono", fontSize: 10 },
  grid: { vertLines: { color: "rgba(38,49,66,0.35)" }, horzLines: { color: "rgba(38,49,66,0.35)" } },
  crosshair: { mode: CrosshairMode.Normal, vertLine: { color: "#ffab0080", labelBackgroundColor: "#9c6400" }, horzLine: { color: "#ffab0080", labelBackgroundColor: "#9c6400" } },
  rightPriceScale: { borderColor: "#1b2431" },
  timeScale: { borderColor: "#1b2431", timeVisible: true, secondsVisible: false,
    tickMarkFormatter: (t: Time) => { const d = new Date((t as number) * 1000); return d.getUTCHours() === 0 && d.getUTCMinutes() === 0 ? NYDAY.format(d) : NYTIME.format(d); } },
  localization: { timeFormatter: (t: Time) => `${NY.format(new Date((t as number) * 1000))} ET` },
});

const LEVEL_COLORS: Record<string, string> = { reference: "#8592a3", session: "#39c5ff", auction: "#a78bfa" };
export const LINE_COLORS = ["#ffab00", "#39c5ff", "#a78bfa", "#2ee6a6", "#ff8fab", "#ffd27a"];

export function PriceChart({ bars, overlays = {}, levels = [], markers = [], height = "100%", showVolume = true }: {
  bars: Bar[]; overlays?: Record<string, { t: number; v: number }[]>; levels?: Level[]; markers?: SeriesMarker<Time>[]; height?: string | number; showVolume?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  useEffect(() => {
    if (!ref.current) return;
    const c = base(ref.current);
    chart.current = c;
    const candles = c.addCandlestickSeries({ upColor: "#2ee6a6", downColor: "#ff4d6a", borderVisible: false, wickUpColor: "#2ee6a6", wickDownColor: "#ff4d6a", priceLineColor: "#ffab00" });
    candles.setData(bars.map((b) => ({ time: b.t as UTCTimestamp, open: b.o, high: b.h, low: b.l, close: b.c })));
    if (showVolume) {
      const vol = c.addHistogramSeries({ priceScaleId: "vol", priceFormat: { type: "volume" } });
      c.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      vol.setData(bars.map((b) => ({ time: b.t as UTCTimestamp, value: b.v, color: b.c >= b.o ? "rgba(46,230,166,0.28)" : "rgba(255,77,106,0.28)" })));
    }
    Object.entries(overlays).forEach(([name, series], i) => {
      const line = c.addLineSeries({ color: LINE_COLORS[i % LINE_COLORS.length], lineWidth: 1, priceLineVisible: false, lastValueVisible: true, title: name.toUpperCase() });
      line.setData(series.map((p) => ({ time: p.t as UTCTimestamp, value: p.v })));
    });
    levels.forEach((lv) => candles.createPriceLine({ price: lv.price, color: LEVEL_COLORS[lv.kind] ?? "#5d6b80", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: lv.name }));
    if (markers.length) candles.setMarkers([...markers].sort((a, b) => (a.time as number) - (b.time as number)));
    c.timeScale().fitContent();
    return () => { c.remove(); chart.current = null; };
  }, [bars, overlays, levels, markers, showVolume]);
  return <div ref={ref} style={{ height }} className="w-full" />;
}

export function TimeLine({ series, height = 180, area = true, baseline }: {
  series: { name: string; points: { t: number; v: number }[]; color?: string }[]; height?: number; area?: boolean; baseline?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const c = base(ref.current);
    // Sparklines are too small for the logo; attribution is shown in the status bar.
    if (height < 100) c.applyOptions({ layout: { attributionLogo: false } });
    c.applyOptions({ timeScale: { timeVisible: false, tickMarkFormatter: (t: Time) => NYDAY.format(new Date((t as number) * 1000)) } });
    series.forEach((s, i) => {
      const color = s.color ?? LINE_COLORS[i % LINE_COLORS.length];
      const data = [...s.points].sort((a, b) => a.t - b.t).filter((p, k, arr) => k === 0 || p.t > arr[k - 1].t).map((p) => ({ time: p.t as UTCTimestamp, value: p.v }));
      if (baseline !== undefined && i === 0) {
        const b = c.addBaselineSeries({ baseValue: { type: "price", price: baseline }, topLineColor: "#2ee6a6", bottomLineColor: "#ff4d6a",
          topFillColor1: "rgba(46,230,166,0.25)", topFillColor2: "rgba(46,230,166,0.02)", bottomFillColor1: "rgba(255,77,106,0.02)", bottomFillColor2: "rgba(255,77,106,0.25)", lineWidth: 2 });
        b.setData(data);
      } else if (area && i === 0) {
        const a = c.addAreaSeries({ lineColor: color, topColor: `${color}40`, bottomColor: `${color}00`, lineWidth: 2, priceLineVisible: false });
        a.setData(data);
      } else {
        c.addLineSeries({ color, lineWidth: 1, priceLineVisible: false, title: s.name }).setData(data);
      }
    });
    c.timeScale().fitContent();
    return () => c.remove();
  }, [series, area, baseline]);
  return <div ref={ref} style={{ height }} className="w-full" />;
}

export function Bars({ data, height = 140, format = (v: number) => v.toFixed(0), signed = false }: {
  data: { label: string; value: number }[]; height?: number; format?: (v: number) => string; signed?: boolean;
}) {
  const max = Math.max(1e-9, ...data.map((d) => Math.abs(d.value)));
  const plot = height - 16;
  const mid = signed ? plot / 2 : plot;
  const w = 100 / Math.max(1, data.length);
  const every = Math.max(1, Math.ceil(data.length / 10));
  return (
    <div className="w-full">
      <svg viewBox={`0 0 100 ${plot}`} preserveAspectRatio="none" className="w-full" style={{ height: plot }}>
        {signed && <line x1="0" x2="100" y1={mid} y2={mid} stroke="#263142" strokeWidth="0.3" vectorEffect="non-scaling-stroke" />}
        {data.map((d, i) => {
          const h = (Math.abs(d.value) / max) * (signed ? plot / 2 - 2 : plot - 2);
          const y = signed ? (d.value >= 0 ? mid - h : mid) : mid - h;
          const fill = signed ? (d.value >= 0 ? "#2ee6a6" : "#ff4d6a") : "#ffab00";
          return <rect key={i} x={i * w + w * 0.15} width={w * 0.7} y={y} height={Math.max(0.5, h)} fill={fill} opacity={0.82}><title>{`${d.label}: ${format(d.value)}`}</title></rect>;
        })}
      </svg>
      <div className="flex h-4 font-mono text-[9px] text-ink-500">
        {data.map((d, i) => <span key={i} className="truncate text-center" style={{ width: `${w}%` }}>{i % every === 0 ? d.label : ""}</span>)}
      </div>
    </div>
  );
}

export function Reliability({ bins, height = 180 }: { bins: { bin: string; n: number; mean_predicted: number; observed: number }[]; height?: number }) {
  const s = 100;
  return (
    <svg viewBox={`-8 -4 ${s + 12} ${s + 14}`} className="w-full" style={{ height }}>
      {[0, 0.25, 0.5, 0.75, 1].map((g) => (
        <g key={g}>
          <line x1={0} x2={s} y1={s - g * s} y2={s - g * s} stroke="#1b2431" strokeWidth="0.4" />
          <text x={-2} y={s - g * s + 1} fontSize="3" fill="#5d6b80" textAnchor="end" fontFamily="IBM Plex Mono">{g}</text>
        </g>
      ))}
      <line x1={0} y1={s} x2={s} y2={0} stroke="#3a475b" strokeDasharray="2 2" strokeWidth="0.5" />
      <polyline fill="none" stroke="#ffab00" strokeWidth="0.9" points={bins.map((b) => `${b.mean_predicted * s},${s - b.observed * s}`).join(" ")} />
      {bins.map((b) => (
        <circle key={b.bin} cx={b.mean_predicted * s} cy={s - b.observed * s} r={Math.min(4, 1 + Math.sqrt(b.n) / 6)} fill="#ffab00" opacity={0.85}>
          <title>{`${b.bin}: predicted ${b.mean_predicted}, observed ${b.observed} (n=${b.n})`}</title>
        </circle>
      ))}
      <text x={s / 2} y={s + 8} fontSize="3.2" fill="#8592a3" textAnchor="middle" fontFamily="IBM Plex Mono">PREDICTED PROBABILITY →</text>
    </svg>
  );
}
