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
    """Placeholder for the real daily-price fetch.

    Replace the body with a call into kazu/sources/ once a data source is chosen;
    the surrounding staleness bookkeeping stays as-is.
    """
    log.info("refresh_prices: no source wired yet, nothing to do")


def _refresh_fundamentals() -> None:
    log.info("refresh_fundamentals: no source wired yet, nothing to do")


JOBS: list[Job] = [
    Job("daily_prices", dt.timedelta(hours=6), _refresh_prices),
    Job("fundamentals", dt.timedelta(days=1), _refresh_fundamentals),
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
