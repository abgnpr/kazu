/** TanStack Query hooks. Query keys are centralised so invalidation stays sane. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type {
  BackfillResult,
  BreakoutResponse,
  Coverage,
  History,
  JobStatus,
  ScreenerRow,
} from "./types";

export const keys = {
  screener: ["screener"] as const,
  watchlist: ["watchlist"] as const,
  jobs: ["jobs"] as const,
  coverage: ["coverage"] as const,
  breakouts: (onlyPassing: boolean) => ["breakouts", onlyPassing] as const,
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

export function useBreakouts(onlyPassing: boolean) {
  return useQuery({
    queryKey: keys.breakouts(onlyPassing),
    queryFn: () =>
      api<BreakoutResponse>(`/api/breakouts?only_passing=${onlyPassing}`),
  });
}

export function useCoverage() {
  return useQuery({ queryKey: keys.coverage, queryFn: () => api<Coverage>("/api/coverage") });
}

/** Backfill is one HTTP request per trading day, so it is slow by nature and
 *  deliberately user-triggered. Everything derived from prices is invalidated
 *  once it lands. */
export function useBackfill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (days: number) =>
      api<BackfillResult>(`/api/ingest/backfill?days=${days}`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.coverage });
      qc.invalidateQueries({ queryKey: ["breakouts"] });
      qc.invalidateQueries({ queryKey: keys.screener });
      qc.invalidateQueries({ queryKey: keys.watchlist });
    },
  });
}
