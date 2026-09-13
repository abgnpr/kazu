"""DuckDB access. This process is the single owner/writer of the database file.

DuckDB connections are not thread-safe, and FastAPI runs `def` endpoints in a
threadpool, so every statement goes through `_LOCK`. For a one-user app the
contention is irrelevant and the simplicity is worth a lot.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from typing import Any

import duckdb
import pandas as pd

from kazu.config import settings

_LOCK = threading.RLock()
_CONN: duckdb.DuckDBPyConnection | None = None


DDL = [
    """
    CREATE TABLE IF NOT EXISTS instruments (
        symbol    VARCHAR PRIMARY KEY,
        name      VARCHAR,
        exchange  VARCHAR,
        sector    VARCHAR,
        isin      VARCHAR,
        series    VARCHAR,
        currency  VARCHAR DEFAULT 'INR'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS prices_daily (
        symbol   VARCHAR NOT NULL,
        date     DATE    NOT NULL,
        open     DOUBLE,
        high     DOUBLE,
        low      DOUBLE,
        close    DOUBLE,
        volume   BIGINT,
        turnover DOUBLE,
        trades   BIGINT,
        PRIMARY KEY (symbol, date)
    )
    """,
    # One row per attempted trading date. `status` is 'ok' when a bhavcopy was
    # ingested and 'absent' when NSE has no file (weekend/holiday) -- absent
    # dates are remembered so they are never re-requested.
    """
    CREATE TABLE IF NOT EXISTS ingest_log (
        date     DATE PRIMARY KEY,
        status   VARCHAR NOT NULL,
        rows     BIGINT,
        fetched  TIMESTAMP DEFAULT current_timestamp,
        note     VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fundamentals (
        symbol      VARCHAR NOT NULL,
        as_of       DATE    NOT NULL,
        market_cap  DOUBLE,
        pe_ratio    DOUBLE,
        eps         DOUBLE,
        book_value  DOUBLE,
        PRIMARY KEY (symbol, as_of)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlists (
        name   VARCHAR NOT NULL,
        symbol VARCHAR NOT NULL,
        added  TIMESTAMP DEFAULT current_timestamp,
        PRIMARY KEY (name, symbol)
    )
    """,
    # Staleness ledger: the scheduler trusts these timestamps, not its own timers,
    # because laptops get closed. See jobs.py.
    """
    CREATE TABLE IF NOT EXISTS job_status (
        job           VARCHAR PRIMARY KEY,
        last_success  TIMESTAMP,
        last_attempt  TIMESTAMP,
        last_error    VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key   VARCHAR PRIMARY KEY,
        value VARCHAR
    )
    """,
]


def connect() -> duckdb.DuckDBPyConnection:
    """Return the process-wide connection, creating the file and schema on first call."""
    global _CONN
    with _LOCK:
        if _CONN is None:
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            _CONN = duckdb.connect(str(settings.db_path))
            for stmt in DDL:
                _CONN.execute(stmt)
        return _CONN


def close() -> None:
    global _CONN
    with _LOCK:
        if _CONN is not None:
            _CONN.close()
            _CONN = None


def query_df(sql: str, params: Sequence[Any] | None = None) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame."""
    conn = connect()
    with _LOCK:
        return conn.execute(sql, params or []).df()


def query_rows(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """Run a SELECT and return plain dicts, ready for JSON."""
    conn = connect()
    with _LOCK:
        cur = conn.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def execute(
    sql: str,
    params: Sequence[Any] | None = None,
    *,
    _register: tuple[str, pd.DataFrame] | None = None,
) -> None:
    """Run a statement. `_register` exposes a DataFrame to the SQL under a name,
    so INSERT ... SELECT can read from it (used for upserts with ON CONFLICT)."""
    conn = connect()
    with _LOCK:
        if _register is None:
            conn.execute(sql, params or [])
            return
        name, frame = _register
        conn.register(name, frame)
        try:
            conn.execute(sql, params or [])
        finally:
            conn.unregister(name)


def upsert_df(table: str, df: pd.DataFrame, keys: Sequence[str]) -> int:
    """Insert `df` into `table`, replacing rows that collide on `keys`.

    DuckDB has no ON CONFLICT for arbitrary column lists in every version, so we
    delete the incoming keys and insert. Both statements run in one transaction.
    """
    if df.empty:
        return 0
    conn = connect()
    with _LOCK:
        conn.register("_incoming", df)
        try:
            cond = " AND ".join(f"t.{k} = i.{k}" for k in keys)
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                f"DELETE FROM {table} AS t WHERE EXISTS "  # noqa: S608 - table is internal
                f"(SELECT 1 FROM _incoming AS i WHERE {cond})"
            )
            cols = ", ".join(df.columns)
            conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _incoming")  # noqa: S608
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.unregister("_incoming")
    return len(df)
