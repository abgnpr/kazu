"""Deciding which dates to fetch.

The scheduler never assumes it ran. `catch_up()` walks forward from the newest
date already in the database, so an app left closed for two weeks fills those
sessions on next launch. Dates NSE has no file for are remembered as 'absent'
and skipped, so weekends cost nothing after the first look.
"""

from __future__ import annotations

import datetime as dt
import logging

import httpx

from kazu.data import db
from kazu.sources import nse

log = logging.getLogger(__name__)

# Beyond this, a stale database is filled by an explicit backfill rather than
# firing hundreds of unattended requests at NSE on startup.
CATCH_UP_MAX_DAYS = 90

# On an empty database, how far back to search for the latest trading day.
# Covers a long weekend plus a holiday cluster (e.g. Diwali).
FIRST_RUN_LOOKBACK_DAYS = 10

# The current URL scheme does not reach back further than this.
EARLIEST_AVAILABLE = dt.date(2024, 7, 1)


def _attempted() -> set[dt.date]:
    """Dates already resolved -- ingested or known to have no file."""
    return {r["date"] for r in db.query_rows("SELECT date FROM ingest_log")}


def latest_ingested() -> dt.date | None:
    rows = db.query_rows("SELECT max(date) AS d FROM ingest_log WHERE status = 'ok'")
    return rows[0]["d"] if rows and rows[0]["d"] else None


def pending_dates(
    start: dt.date | None = None,
    end: dt.date | None = None,
    *,
    limit: int | None = None,
) -> list[dt.date]:
    """Weekdays in [start, end] not yet attempted, newest first.

    Newest first matters: a partial run still leaves the most recent data
    present, which is what the UI shows.
    """
    end = end or dt.date.today()
    if start is None:
        last = latest_ingested()
        if last:
            start = last + dt.timedelta(days=1)
        else:
            # First run: today may be a weekend or holiday, so look back far
            # enough to be sure of catching the most recent trading session.
            start = end - dt.timedelta(days=FIRST_RUN_LOOKBACK_DAYS)
    start = max(start, EARLIEST_AVAILABLE)

    done = _attempted()
    out: list[dt.date] = []
    day = end
    while day >= start:
        if day.weekday() < 5 and day not in done:
            out.append(day)
            if limit and len(out) >= limit:
                break
        day -= dt.timedelta(days=1)
    return out


def _run(dates: list[dt.date], *, stop_after_first_hit: bool = False) -> dict:
    """Fetch each date over one connection. One bad date must not stop the rest."""
    stored = failed = absent = 0
    if not dates:
        return {"dates": 0, "rows": 0, "absent": 0, "failed": 0}

    with httpx.Client(headers=nse.HEADERS, timeout=30.0, follow_redirects=True) as client:
        for day in dates:
            try:
                rows = nse.ingest_date(day, client=client)
                if rows:
                    stored += rows
                    if stop_after_first_hit:
                        break
                else:
                    absent += 1
            except Exception as exc:
                # Network/parse trouble: leave the date unlogged so it retries.
                failed += 1
                log.warning("ingest %s failed: %s", day, exc)
    return {"dates": len(dates), "rows": stored, "absent": absent, "failed": failed}


def catch_up() -> dict:
    """Fill everything missed since the last successful ingest.

    On an empty database this stops at the first date that yields data, so a
    first launch costs one or two requests rather than a blind ten.
    """
    first_run = latest_ingested() is None
    dates = pending_dates(limit=CATCH_UP_MAX_DAYS)
    if not dates:
        return {"dates": 0, "rows": 0, "absent": 0, "failed": 0, "note": "up to date"}
    log.info("catching up %d date(s): %s .. %s", len(dates), dates[-1], dates[0])
    return _run(dates, stop_after_first_hit=first_run)


def backfill(days: int = 400) -> dict:
    """Explicitly fetch up to `days` calendar days of history.

    Called on demand, not at startup: the indicators need ~250 sessions and each
    session is one HTTP request.
    """
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    dates = pending_dates(start=start, end=end)
    log.info("backfilling %d date(s)", len(dates))
    return _run(dates)


def coverage() -> dict:
    """What history exists -- drives the UI's "not enough data yet" messaging."""
    row = db.query_rows(
        """
        SELECT count(*) FILTER (WHERE status = 'ok')     AS sessions,
               min(date) FILTER (WHERE status = 'ok')    AS first_date,
               max(date) FILTER (WHERE status = 'ok')    AS last_date,
               count(*) FILTER (WHERE status = 'absent') AS non_trading
        FROM ingest_log
        """
    )[0]
    symbols = db.query_rows("SELECT count(DISTINCT symbol) AS n FROM prices_daily")[0]["n"]
    sessions = row["sessions"] or 0
    return {
        "sessions": sessions,
        "symbols": symbols,
        "first_date": row["first_date"].isoformat() if row["first_date"] else None,
        "last_date": row["last_date"].isoformat() if row["last_date"] else None,
        "non_trading_days": row["non_trading"] or 0,
        # Thresholds the strategy actually needs.
        "has_200dma": sessions >= 200,
        "has_52w": sessions >= 252,
    }
