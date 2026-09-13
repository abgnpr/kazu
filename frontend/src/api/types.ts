/** Shapes returned by the Python service. Keep in sync with kazu/api/routes.py. */

export type ScreenerRow = {
  symbol: string;
  name: string | null;
  sector: string | null;
  date: string;
  close: number;
  change_pct: number | null;
  volume: number;
  avg_vol_30: number | null;
  rel_volume: number | null;
  sma20: number | null;
  sma50: number | null;
  return_3m: number | null;
  return_1y: number | null;
  volatility: number | null;
  pe_ratio: number | null;
  market_cap: number | null;
};

export type Candle = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma20: number | null;
  sma50: number | null;
  rsi14: number | null;
};

export type History = {
  symbol: string;
  meta: { symbol: string; name: string; sector: string; exchange: string } | null;
  candles: Candle[];
};

export type JobStatus = {
  job: string;
  last_success: string | null;
  last_attempt: string | null;
  last_error: string | null;
  stale: boolean | null;
};
