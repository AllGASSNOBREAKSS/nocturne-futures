import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, bridge, type BackendStatus } from "./api";

export function useBackendStatus() {
  const [status, setStatus] = useState<BackendStatus>({ state: "starting", detail: "Connecting" });
  useEffect(() => {
    let off = () => {};
    try {
      bridge().status().then(setStatus);
      off = bridge().onStatus(setStatus);
    } catch (e) {
      setStatus({ state: "error", detail: String((e as Error).message) });
    }
    return off;
  }, []);
  return status;
}

export function useApi<T = any>(path: string | null, options: { refetchInterval?: number | false; enabled?: boolean } = {}) {
  return useQuery<T>({
    queryKey: [path],
    queryFn: () => api.get<T>(path as string),
    enabled: !!path && options.enabled !== false,
    refetchInterval: options.refetchInterval ?? false,
    staleTime: 15_000,
    retry: 1,
  });
}

export function useAction<T = any>(path: string, invalidate: string[] = []) {
  const client = useQueryClient();
  return useMutation<T, Error, unknown>({
    mutationFn: (body) => api.post<T>(path, body),
    onSuccess: () => invalidate.forEach((key) => client.invalidateQueries({ predicate: (q) => String(q.queryKey[0] ?? "").startsWith(key) })),
  });
}

export function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}
