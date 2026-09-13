/** TanStack Query hooks. Query keys are centralised so invalidation stays sane. */

import { useQuery } from "@tanstack/react-query";

import { api } from "./client";
import type { History, JobStatus, ScreenerRow } from "./types";

export const keys = {
  screener: ["screener"] as const,
  watchlist: ["watchlist"] as const,
  jobs: ["jobs"] as const,
  history: (symbol: string, limit: number) => ["history", symbol, limit] as const,
};

export function useScreener() {
  return useQuery({ queryKey: keys.screener, queryFn: () => api<ScreenerRow[]>("/api/screener") });
}

export function useWatchlist() {
  return useQuery({
    queryKey: keys.watchlist,
    queryFn: () => api<ScreenerRow[]>("/api/watchlist"),
  });
}

export function useHistory(symbol: string | null, limit = 250) {
  return useQuery({
    queryKey: keys.history(symbol ?? "", limit),
    queryFn: () => api<History>(`/api/instruments/${symbol}/history?limit=${limit}`),
    enabled: Boolean(symbol),
  });
}

export function useJobs() {
  return useQuery({
    queryKey: keys.jobs,
    queryFn: () => api<JobStatus[]>("/api/jobs"),
    refetchInterval: 60_000,
  });
}
