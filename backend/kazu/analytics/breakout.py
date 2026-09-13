"""CAR + DMA breakout screen.

Adapted from Mahesh Chander Kaushik's Colab scanner, reimplemented as DuckDB
window functions over the whole market instead of a per-ticker Python loop.

The rule, unchanged:
    close > SMA30 AND close > SMA50 AND close > SMA200 AND CAR rising 10 days

CAR ("cumulative average return" in the original) is the expanding mean of
closes measured from the date of the 52-week high. It is treated as positive
only when it has risen on every one of the last 10 sessions.

Two notes on the translation:

* The original computes the expanding mean in Python then calls
  `is_monotonic_increasing`. An expanding mean rises on a given day exactly when
  that day's close exceeds the mean of everything before it, so the SQL checks
  the mean directly across a 10-row window -- same signal, one pass, no loop.

* `is_monotonic_increasing` in pandas is non-strict: it holds when values stay
  equal. The SQL matches that by testing `>=` against the running minimum of the
  differences, so an unchanged CAR does not fail the screen.
"""

from __future__ import annotations

from kazu.data import db

# Sessions of history a symbol needs before it can be judged.
MIN_SESSIONS = 200
# Sessions the CAR trend is measured over.
CAR_WINDOW = 10

_BREAKOUT_SQL = f"""
WITH ranked AS (
    SELECT symbol, date, high, close, volume,
           row_number() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn,
           count(*)     OVER (PARTITION BY symbol)                    AS n
    FROM prices_daily
),
eligible AS (
    -- Only symbols with enough history for a 200 DMA.
    SELECT * FROM ranked WHERE n >= {MIN_SESSIONS}
),
dma AS (
    SELECT symbol, date, close, volume, rn, n,
           avg(close) FILTER (WHERE rn <= 30)  OVER (PARTITION BY symbol) AS sma30,
           avg(close) FILTER (WHERE rn <= 50)  OVER (PARTITION BY symbol) AS sma50,
           avg(close) FILTER (WHERE rn <= 200) OVER (PARTITION BY symbol) AS sma200,
           avg(volume) FILTER (WHERE rn <= 30) OVER (PARTITION BY symbol) AS avg_vol_30
    FROM eligible
),
-- The 52-week high and the date it happened on.
high_52w AS (
    SELECT symbol, max(high) AS high_52w,
           arg_max(date, high) AS high_date
    FROM eligible
    WHERE rn <= 252
    GROUP BY symbol
),
-- Closes from the 52-week-high date onward, oldest first, for the expanding mean.
since_high AS (
    SELECT e.symbol, e.date, e.close,
           row_number() OVER (PARTITION BY e.symbol ORDER BY e.date)  AS seq,
           count(*)     OVER (PARTITION BY e.symbol)                  AS len
    FROM eligible e
    JOIN high_52w h ON h.symbol = e.symbol
    WHERE e.date >= h.high_date
),
car AS (
    SELECT symbol, date, seq, len,
           avg(close) OVER (
               PARTITION BY symbol ORDER BY seq
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) AS car_value
    FROM since_high
),
car_delta AS (
    SELECT symbol, date, seq, len, car_value,
           car_value - lag(car_value) OVER (PARTITION BY symbol ORDER BY seq) AS delta
    FROM car
),
-- Did CAR hold up across each of the last CAR_WINDOW sessions?
car_trend AS (
    SELECT symbol,
           arg_max(car_value, seq)                   AS car_value,
           min(delta) FILTER (WHERE seq > len - {CAR_WINDOW}) AS worst_delta,
           max(len)                                  AS car_len
    FROM car_delta
    GROUP BY symbol
),
latest AS (
    SELECT symbol, date, close, volume, sma30, sma50, sma200, avg_vol_30
    FROM dma WHERE rn = 1
),
prev AS (
    SELECT symbol, close AS prev_close FROM dma WHERE rn = 2
)
SELECT l.symbol,
       i.name,
       l.date,
       round(l.close, 2)                                                  AS close,
       round((l.close - p.prev_close) / nullif(p.prev_close, 0) * 100, 2)  AS change_pct,
       round(l.sma30, 2)                                                  AS sma30,
       round(l.sma50, 2)                                                  AS sma50,
       round(l.sma200, 2)                                                 AS sma200,
       round((l.close - l.sma200) / nullif(l.sma200, 0) * 100, 2)         AS dist_200dma_pct,
       round(h.high_52w, 2)                                               AS high_52w,
       round((l.close - h.high_52w) / nullif(h.high_52w, 0) * 100, 2)     AS from_52w_high_pct,
       h.high_date,
       l.volume,
       round(l.volume / nullif(l.avg_vol_30, 0), 2)                       AS rel_volume,
       round(c.car_value, 2)                                              AS car_value,
       c.car_len                                                          AS car_sessions,
       -- CAR counts as positive only with a full window that never fell.
       (c.car_len >= {CAR_WINDOW} AND coalesce(c.worst_delta, -1) >= 0)   AS car_positive,
       (l.close > l.sma30)                                                AS above_30dma,
       (l.close > l.sma50)                                                AS above_50dma,
       (l.close > l.sma200)                                               AS above_200dma,
       (
           l.close > l.sma30 AND l.close > l.sma50 AND l.close > l.sma200
           AND c.car_len >= {CAR_WINDOW} AND coalesce(c.worst_delta, -1) >= 0
       )                                                                  AS breakout
FROM latest l
JOIN car_trend c USING (symbol)
JOIN high_52w  h USING (symbol)
LEFT JOIN prev p USING (symbol)
LEFT JOIN instruments i ON i.symbol = l.symbol
ORDER BY dist_200dma_pct
"""


def breakouts(only_passing: bool = False, limit: int | None = None) -> list[dict]:
    """Screen the whole market.

    Returns every eligible symbol with its per-condition flags, ordered by
    distance from the 200 DMA ascending (the original's ranking). Pass
    `only_passing` to return just the symbols clearing all four conditions.
    """
    rows = db.query_rows(_BREAKOUT_SQL)
    if only_passing:
        rows = [r for r in rows if r["breakout"]]
    if limit:
        rows = rows[:limit]
    for r in rows:
        for key in ("date", "high_date"):
            if r.get(key) is not None:
                r[key] = r[key].isoformat()
    return rows
