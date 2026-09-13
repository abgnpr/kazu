"""Indicators and screener metrics, computed in DuckDB.

These are window-function queries rather than pandas pipelines: the data already
lives in the database, and pushing the work down means we never load 500 rows x
N symbols into Python just to compute a mean.
"""

from __future__ import annotations

from kazu.data import db

# Close, SMA20/50, and a Wilder-style RSI(14) approximated with a simple mean of
# gains/losses -- close enough for screening, and one pass over the table.
_HISTORY_SQL = """
WITH base AS (
    SELECT date, open, high, low, close, volume,
           close - lag(close) OVER (ORDER BY date) AS chg
    FROM prices_daily
    WHERE symbol = ?
),
steps AS (
    SELECT *,
           greatest(chg, 0)      AS gain,
           greatest(-chg, 0)     AS loss
    FROM base
),
rolled AS (
    -- 30/50/200 to match the breakout screen exactly. A chart showing different
    -- averages than the strategy tests is worse than no chart.
    SELECT *,
           avg(close) OVER (ORDER BY date ROWS BETWEEN 29  PRECEDING AND CURRENT ROW) AS sma30,
           avg(close) OVER (ORDER BY date ROWS BETWEEN 49  PRECEDING AND CURRENT ROW) AS sma50,
           avg(close) OVER (ORDER BY date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) AS sma200,
           avg(gain)  OVER (ORDER BY date ROWS BETWEEN 13  PRECEDING AND CURRENT ROW) AS avg_gain,
           avg(loss)  OVER (ORDER BY date ROWS BETWEEN 13  PRECEDING AND CURRENT ROW) AS avg_loss,
           count(*)   OVER (ORDER BY date ROWS BETWEEN 29  PRECEDING AND CURRENT ROW) AS n30,
           count(*)   OVER (ORDER BY date ROWS BETWEEN 49  PRECEDING AND CURRENT ROW) AS n50,
           count(*)   OVER (ORDER BY date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) AS n200,
           -- Running 52-week high, so the chart can mark the level the CAR
           -- window is measured from.
           max(high)  OVER (ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) AS high_52w
    FROM steps
)
SELECT date, open, high, low, close, volume,
       -- NULL until the window is actually full, so no misleading partial average.
       CASE WHEN n30  >= 30  THEN round(sma30, 2)  END AS sma30,
       CASE WHEN n50  >= 50  THEN round(sma50, 2)  END AS sma50,
       CASE WHEN n200 >= 200 THEN round(sma200, 2) END AS sma200,
       round(high_52w, 2) AS high_52w,
       CASE
           WHEN avg_loss IS NULL THEN NULL
           WHEN avg_loss = 0 THEN 100.0
           ELSE round(100 - (100 / (1 + avg_gain / avg_loss)), 2)
       END AS rsi14
FROM rolled
ORDER BY date
"""


def history(symbol: str, limit: int | None = None) -> list[dict]:
    """OHLCV plus SMA20/SMA50/RSI14 for one symbol, oldest first.

    `limit` keeps the most recent N rows but still computes indicators over the
    full series, so the first visible SMA50 is correct rather than truncated.
    """
    rows = db.query_rows(_HISTORY_SQL, [symbol])
    if limit is not None and limit > 0:
        rows = rows[-limit:]
    for r in rows:
        r["date"] = r["date"].isoformat()
    return rows


_SCREENER_SQL = """
WITH ranked AS (
    SELECT symbol, date, close, volume,
           row_number() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn
    FROM prices_daily
),
latest AS (
    SELECT symbol, date, close, volume FROM ranked WHERE rn = 1
),
prev AS (
    SELECT symbol, close AS prev_close FROM ranked WHERE rn = 2
),
window_stats AS (
    SELECT symbol,
           avg(CASE WHEN rn <= 30 THEN volume END)              AS avg_vol_30,
           avg(CASE WHEN rn <= 30 THEN close END)               AS sma30,
           avg(CASE WHEN rn <= 50 THEN close END)               AS sma50,
           avg(CASE WHEN rn <= 200 THEN close END)              AS sma200,
           max(CASE WHEN rn = 66  THEN close END)               AS close_3m,
           max(CASE WHEN rn = 252 THEN close END)               AS close_1y,
           stddev_samp(CASE WHEN rn <= 252 THEN close END)
               / nullif(avg(CASE WHEN rn <= 252 THEN close END), 0) * 100 AS volatility
    FROM ranked
    GROUP BY symbol
)
SELECT l.symbol,
       i.name,
       i.sector,
       l.date,
       round(l.close, 2)                                                   AS close,
       round((l.close - p.prev_close) / nullif(p.prev_close, 0) * 100, 2)   AS change_pct,
       l.volume,
       round(w.avg_vol_30, 0)                                              AS avg_vol_30,
       round(l.volume / nullif(w.avg_vol_30, 0), 2)                        AS rel_volume,
       round(w.sma30, 2)                                                   AS sma30,
       round(w.sma50, 2)                                                   AS sma50,
       round(w.sma200, 2)                                                  AS sma200,
       round((l.close - w.close_3m) / nullif(w.close_3m, 0) * 100, 2)       AS return_3m,
       round((l.close - w.close_1y) / nullif(w.close_1y, 0) * 100, 2)      AS return_1y,
       round(w.volatility, 2)                                              AS volatility,
       f.pe_ratio,
       f.market_cap
FROM latest l
JOIN window_stats w USING (symbol)
LEFT JOIN prev p USING (symbol)
LEFT JOIN instruments i ON i.symbol = l.symbol
LEFT JOIN (
    SELECT symbol, pe_ratio, market_cap,
           row_number() OVER (PARTITION BY symbol ORDER BY as_of DESC) AS rn
    FROM fundamentals
) f ON f.symbol = l.symbol AND f.rn = 1
ORDER BY l.symbol
"""


def screener() -> list[dict]:
    """One row per instrument with the metrics a watchlist/screener table wants."""
    rows = db.query_rows(_SCREENER_SQL)
    for r in rows:
        if r.get("date") is not None:
            r["date"] = r["date"].isoformat()
    return rows
