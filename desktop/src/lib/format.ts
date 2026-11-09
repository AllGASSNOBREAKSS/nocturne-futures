import { twMerge } from "tailwind-merge";

export const cn = (...parts: (string | false | null | undefined)[]) => twMerge(parts.filter(Boolean).join(" "));

export const num = (v: unknown, digits = 2) =>
  typeof v === "number" && Number.isFinite(v) ? v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }) : "—";

export const pct = (v: unknown, digits = 1) => (typeof v === "number" && Number.isFinite(v) ? `${(v * 100).toFixed(digits)}%` : "—");

export const usd = (v: unknown, digits = 0) =>
  typeof v === "number" && Number.isFinite(v) ? `${v < 0 ? "−" : ""}$${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}` : "—";

export const signed = (v: unknown, digits = 4) => (typeof v === "number" && Number.isFinite(v) ? `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(digits)}` : "—");

export const tone = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? (v > 0 ? "text-up" : v < 0 ? "text-down" : "text-ink-200") : "text-ink-300");

export const when = (iso?: string | null) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString("en-US", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false, timeZoneName: "short" });
};

export const ago = (iso?: string | null) => {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (!Number.isFinite(s)) return "—";
  if (s < 90) return `${Math.round(s)}s ago`;
  if (s < 5400) return `${Math.round(s / 60)}m ago`;
  if (s < 172800) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
};

export const verdictTone = (v?: string | null) => {
  const s = (v || "").toUpperCase();
  if (s.includes("ACCEPT") || s.includes("CANDIDATE") || s === "SUCCEEDED" || s.includes("HELPS")) return "up";
  if (s.includes("REJECT") || s.includes("FAIL") || s.includes("HURTS") || s.includes("BLOCKED")) return "down";
  if (s.includes("INSUFFICIENT") || s.includes("INCONCLUSIVE") || s.includes("NO_DETECT") || s.includes("QUEUED") || s.includes("RUNNING")) return "warn";
  return "muted";
};
