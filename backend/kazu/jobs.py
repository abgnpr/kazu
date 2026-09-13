"""Background refresh jobs.

The scheduler does not assume it ran: laptops sleep. Every job records
last_success in job_status, and `run_due_jobs()` compares that timestamp against
a max-age. Startup calls it once for catch-up, then a timer re-checks.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from dataclasses import dataclass

from kazu.data import db
from kazu.sources import ingest

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Job:
    name: str
    max_age: dt.timedelta
    fn: Callable[[], None]


def _last_success(job: str) -> dt.datetime | None:
    rows = db.query_rows("SELECT last_success FROM job_status WHERE job = ?", [job])
    return rows[0]["last_success"] if rows else None


def _mark(job: str, *, error: str | None = None) -> None:
    now = dt.datetime.now()
    db.execute(
        """
        INSERT INTO job_status (job, last_success, last_attempt, last_error)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (job) DO UPDATE SET
            last_attempt = excluded.last_attempt,
            last_error   = excluded.last_error,
            last_success = CASE WHEN excluded.last_error IS NULL
                                THEN excluded.last_success
                                ELSE job_status.last_success END
        """,
        [job, None if error else now, now, error],
    )


def is_stale(job: str, max_age: dt.timedelta) -> bool:
    last = _last_success(job)
    return last is None or (dt.datetime.now() - last) > max_age


def _refresh_prices() -> None:
    """Pull any NSE bhavcopies published since the last successful ingest."""
    result = ingest.catch_up()
    log.info(
        "prices: %d date(s), %d rows, %d non-trading, %d failed",
        result["dates"], result["rows"], result["absent"], result["failed"],
    )
    # A date that failed outright should not mark the job fresh, or the gap
    # would not be retried until the next max_age elapses.
    if result["failed"]:
        raise RuntimeError(f"{result['failed']} date(s) failed to ingest")


JOBS: list[Job] = [
    # NSE publishes end-of-day, so checking a few times a day is plenty.
    Job("daily_prices", dt.timedelta(hours=6), _refresh_prices),
]


def run_due_jobs(force: bool = False) -> dict[str, str]:
    """Run every job whose data is older than its max_age. Safe to call anytime."""
    results: dict[str, str] = {}
    for job in JOBS:
        if not force and not is_stale(job.name, job.max_age):
            results[job.name] = "fresh"
            continue
        try:
            job.fn()
            _mark(job.name)
            results[job.name] = "refreshed"
        except Exception as exc:  # a failing job must not take down the others
            log.exception("job %s failed", job.name)
            _mark(job.name, error=str(exc))
            results[job.name] = f"error: {exc}"
    return results


def status() -> list[dict]:
    rows = db.query_rows(
        "SELECT job, last_success, last_attempt, last_error FROM job_status ORDER BY job"
    )
    known = {j.name: j for j in JOBS}
    for r in rows:
        for key in ("last_success", "last_attempt"):
            if r[key] is not None:
                r[key] = r[key].isoformat()
        job = known.get(r["job"])
        r["stale"] = is_stale(r["job"], job.max_age) if job else None
    return rows
