import { motion } from "framer-motion";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import type { ReactNode, SelectHTMLAttributes, InputHTMLAttributes, ButtonHTMLAttributes } from "react";
import { cn, verdictTone } from "@/lib/format";

export function Panel({ title, code, actions, children, className, bodyClass, accent = "amber" }: {
  title: string; code?: string; actions?: ReactNode; children: ReactNode; className?: string; bodyClass?: string; accent?: "amber" | "info" | "research";
}) {
  const bar = { amber: "bg-amber-500", info: "bg-info", research: "bg-research" }[accent];
  return (
    <motion.section initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22, ease: "easeOut" }}
      className={cn("relative flex min-h-0 flex-col overflow-hidden rounded-[3px] border border-ink-700/80 bg-ink-850/90 shadow-[0_0_0_1px_rgba(0,0,0,0.4)]", className)}>
      <header className="flex h-8 shrink-0 items-center gap-2 border-b border-ink-700/80 bg-gradient-to-r from-ink-800 to-ink-850 px-3">
        <span className={cn("h-3 w-[3px] rounded-sm", bar)} />
        {code && <span className="font-mono text-2xs font-semibold tracking-wider text-amber-500">{code}</span>}
        <h2 className="truncate font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-ink-200">{title}</h2>
        <div className="ml-auto flex items-center gap-1.5">{actions}</div>
      </header>
      <div className={cn("min-h-0 flex-1 overflow-auto p-3", bodyClass)}>{children}</div>
    </motion.section>
  );
}

export function Stat({ label, value, sub, valueClass, hint }: { label: string; value: ReactNode; sub?: ReactNode; valueClass?: string; hint?: string }) {
  return (
    <div className="min-w-0 rounded-[3px] border border-ink-700/60 bg-ink-900/70 px-3 py-2" title={hint}>
      <div className="truncate font-mono text-2xs uppercase tracking-[0.14em] text-ink-400">{label}</div>
      <div className={cn("mt-0.5 truncate font-mono font-semibold tabular-nums text-ink-100", typeof value === "string" && value.length > 11 ? "text-sm leading-7" : "text-lg", valueClass)}>{value}</div>
      {sub && <div className="truncate font-mono text-2xs text-ink-400">{sub}</div>}
    </div>
  );
}

const toneClass: Record<string, string> = {
  up: "border-up/30 bg-up/10 text-up", down: "border-down/30 bg-down/10 text-down", warn: "border-warn/30 bg-warn/10 text-warn",
  info: "border-info/30 bg-info/10 text-info", research: "border-research/30 bg-research/10 text-research",
  amber: "border-amber-500/40 bg-amber-500/10 text-amber-400", muted: "border-ink-600 bg-ink-800 text-ink-300",
};

export function Badge({ children, tone, className }: { children: ReactNode; tone?: string; className?: string }) {
  const t = tone ?? verdictTone(typeof children === "string" ? children : "");
  return <span className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-[2px] border px-1.5 py-[1px] font-mono text-2xs font-medium uppercase tracking-wider", toneClass[t] ?? toneClass.muted, className)}>{children}</span>;
}

export function Button({ variant = "primary", size = "md", loading, className, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "outline" | "danger"; size?: "sm" | "md"; loading?: boolean;
}) {
  const styles = {
    primary: "bg-amber-500 text-ink-950 hover:bg-amber-400 shadow-[0_0_18px_-6px_rgba(255,171,0,0.7)]",
    ghost: "text-ink-200 hover:bg-ink-700/70 hover:text-ink-100",
    outline: "border border-ink-600 text-ink-200 hover:border-amber-500/60 hover:text-amber-300",
    danger: "border border-down/40 text-down hover:bg-down/10",
  }[variant];
  return (
    <button {...props} disabled={props.disabled || loading}
      className={cn("no-drag inline-flex items-center justify-center gap-1.5 rounded-[3px] font-mono font-semibold uppercase tracking-wider transition-all duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40",
        size === "sm" ? "h-6 px-2 text-2xs" : "h-8 px-3 text-[11px]", styles, className)}>
      {loading && <Loader2 className="h-3 w-3 animate-spin" />}
      {children}
    </button>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="flex min-w-0 flex-col gap-1">
      <span className="font-mono text-2xs uppercase tracking-[0.14em] text-ink-400" title={hint}>{label}</span>
      {children}
    </label>
  );
}

const control = "h-8 w-full rounded-[3px] border border-ink-600 bg-ink-900 px-2 font-mono text-xs text-ink-100 outline-none transition focus:border-amber-500/70 focus:ring-1 focus:ring-amber-500/30";

export const Select = ({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) => (
  <select {...props} className={cn(control, "cursor-pointer", className)}>{children}</select>
);

export const Input = ({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) => <input {...props} className={cn(control, className)} />;

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: readonly T[] | { value: T; label: string }[]; onChange: (v: T) => void }) {
  const items = (options as any[]).map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  return (
    <div className="no-drag inline-flex rounded-[3px] border border-ink-600 bg-ink-900 p-0.5">
      {items.map((o) => (
        <button key={o.value} onClick={() => onChange(o.value)}
          className={cn("relative h-6 rounded-[2px] px-2 font-mono text-2xs font-semibold uppercase tracking-wider transition-colors",
            value === o.value ? "text-ink-950" : "text-ink-300 hover:text-ink-100")}>
          {value === o.value && <motion.span layoutId={`seg-${items.map((i) => i.value).join("")}`} className="absolute inset-0 rounded-[2px] bg-amber-500" transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
          <span className="relative">{o.label}</span>
        </button>
      ))}
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex h-full min-h-[80px] flex-col justify-center gap-2 p-2">
      {[0, 1, 2].map((i) => (
        <div key={i} className="relative h-3 overflow-hidden rounded-sm bg-ink-800" style={{ width: `${90 - i * 18}%` }}>
          <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-ink-600/40 to-transparent" />
        </div>
      ))}
      <span className="font-mono text-2xs uppercase tracking-widest text-ink-500">{label}…</span>
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  return (
    <div className="flex items-start gap-2 rounded-[3px] border border-down/30 bg-down/5 p-3 font-mono text-xs text-down">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span className="break-words">{(error as Error)?.message ?? String(error)}</span>
    </div>
  );
}

export function Empty({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="flex h-full min-h-[100px] flex-col items-center justify-center gap-1 text-center">
      <Inbox className="h-5 w-5 text-ink-500" />
      <div className="font-mono text-xs uppercase tracking-wider text-ink-300">{title}</div>
      {detail && <div className="max-w-md font-mono text-2xs text-ink-500">{detail}</div>}
    </div>
  );
}

export function Query<T>({ q, children, label }: { q: { isLoading: boolean; error: unknown; data: T | undefined }; children: (d: T) => ReactNode; label?: string }) {
  if (q.isLoading) return <Loading label={label} />;
  if (q.error) return <ErrorState error={q.error} />;
  if (q.data === undefined) return <Empty title="No data" />;
  return <>{children(q.data)}</>;
}

export function Table({ columns, rows, onRow, dense, maxRows, rowKey }: {
  columns: { key: string; label: string; align?: "right" | "left"; render?: (row: any) => ReactNode; className?: string }[];
  rows: any[]; onRow?: (row: any) => void; dense?: boolean; maxRows?: number; rowKey?: (row: any, i: number) => string;
}) {
  const shown = maxRows ? rows.slice(0, maxRows) : rows;
  return (
    <div className="overflow-auto">
      <table className="w-full border-collapse font-mono text-[11px] tabular-nums">
        <thead className="sticky top-0 z-10 bg-ink-850">
          <tr>{columns.map((c) => (
            <th key={c.key} className={cn("whitespace-nowrap border-b border-ink-700 px-2 py-1.5 text-2xs font-medium uppercase tracking-[0.12em] text-ink-400", c.align === "right" ? "text-right" : "text-left")}>{c.label}</th>
          ))}</tr>
        </thead>
        <tbody>
          {shown.map((row, i) => (
            <tr key={rowKey ? rowKey(row, i) : i} onClick={onRow ? () => onRow(row) : undefined}
              className={cn("border-b border-ink-800/80 transition-colors hover:bg-amber-500/[0.04]", onRow && "cursor-pointer")}>
              {columns.map((c) => (
                <td key={c.key} className={cn("whitespace-nowrap px-2", dense ? "py-1" : "py-1.5", c.align === "right" ? "text-right" : "text-left", c.className)}>
                  {c.render ? c.render(row) : row[c.key] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {maxRows && rows.length > maxRows && <div className="px-2 py-1 font-mono text-2xs text-ink-500">Showing {maxRows} of {rows.length}</div>}
    </div>
  );
}

export function KV({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 font-mono text-[11px]">
      {items.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="whitespace-nowrap uppercase tracking-wider text-ink-400">{k}</dt>
          <dd className="truncate text-right text-ink-100 tabular-nums">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Dot({ tone = "up", pulse }: { tone?: string; pulse?: boolean }) {
  const c = { up: "bg-up", down: "bg-down", warn: "bg-warn", info: "bg-info", muted: "bg-ink-500", amber: "bg-amber-500" }[tone] ?? "bg-ink-500";
  return <span className={cn("inline-block h-1.5 w-1.5 rounded-full", c, pulse && "animate-pulseDot")} />;
}

export function Progress({ value }: { value: number }) {
  return (
    <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
      <motion.div className="h-full rounded-full bg-gradient-to-r from-amber-600 to-amber-400" initial={{ width: 0 }} animate={{ width: `${Math.max(2, Math.min(100, value))}%` }} transition={{ duration: 0.4 }} />
    </div>
  );
}
