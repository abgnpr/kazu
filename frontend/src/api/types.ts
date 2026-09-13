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
  sma30: number | null;
  sma50: number | null;
  sma200: number | null;
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
  /** 30/50/200 mirror the breakout screen's conditions exactly. */
  sma30: number | null;
  sma50: number | null;
  sma200: number | null;
  /** Running 52-week high: the level the CAR window is measured from. */
  high_52w: number | null;
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

export type BreakoutRow = {
  symbol: string;
  name: string | null;
  date: string;
  close: number;
  change_pct: number | null;
  sma30: number | null;
  sma50: number | null;
  sma200: number | null;
  dist_200dma_pct: number | null;
  high_52w: number | null;
  from_52w_high_pct: number | null;
  high_date: string | null;
  volume: number;
  rel_volume: number | null;
  car_value: number | null;
  car_sessions: number;
  car_positive: boolean;
  above_30dma: boolean;
  above_50dma: boolean;
  above_200dma: boolean;
  breakout: boolean;
};

export type Coverage = {
  sessions: number;
  symbols: number;
  first_date: string | null;
  last_date: string | null;
  non_trading_days: number;
  has_200dma: boolean;
  has_52w: boolean;
};

export type BreakoutResponse = {
  coverage: Coverage;
  passing: number;
  rows: BreakoutRow[];
};

export type BackfillResult = {
  dates: number;
  rows: number;
  absent: number;
  failed: number;
  note?: string;
};
