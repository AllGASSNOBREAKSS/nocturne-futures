// Typed access to the local Nocturne backend through the Electron IPC bridge.
// The renderer never holds a credential; the main process authenticates.

export type BackendStatus = { state: "starting" | "ready" | "stopped" | "error"; detail: string; port?: number; repo?: string; logPath?: string; at?: string };

type Bridge = {
  request: (method: string, path: string, body?: unknown, raw?: boolean) => Promise<{ ok: boolean; status: number; data: any; error: string | null }>;
  status: () => Promise<BackendStatus>;
  onStatus: (cb: (s: BackendStatus) => void) => () => void;
  saveFile: (name: string, content: string) => Promise<{ saved: boolean; filePath?: string }>;
  revealLog: () => Promise<void>;
};

declare global {
  interface Window { nocturne?: Bridge }
}

export const bridge = (): Bridge => {
  if (!window.nocturne) throw new Error("Nocturne desktop bridge unavailable — run inside the Electron app.");
  return window.nocturne;
};

export class ApiError extends Error {
  constructor(message: string, public status: number, public details?: unknown) { super(message); }
}

async function call<T>(method: string, path: string, body?: unknown, raw = false): Promise<T> {
  const r = await bridge().request(method, path, body, raw);
  if (!r.ok) throw new ApiError(r.error || `HTTP ${r.status}`, r.status, r.data);
  return r.data as T;
}

export const api = {
  get: <T = any>(path: string) => call<T>("GET", path),
  post: <T = any>(path: string, body?: unknown) => call<T>("POST", path, body ?? {}),
  text: (path: string) => call<string>("GET", path, undefined, true),
};

export type Bar = { t: number; o: number; h: number; l: number; c: number; v: number };
export type Level = { name: string; price: number; kind: string; basis: string };
export type Job = {
  job_id: string; kind: string; state: string; attempts: number; created: string; updated: string; name?: string;
  config: any; result: any; progress?: { percent: number; message: string; at: string };
  logs?: Record<string, string>; report?: any;
};
export type Root = "NQ" | "ES";
