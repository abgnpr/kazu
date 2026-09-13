"""HTTP endpoints. Keep them thin: SQL lives in analytics/, storage in data/."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from kazu import jobs
from kazu.analytics import indicators
from kazu.config import settings
from kazu.data import db

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    row = db.query_rows("SELECT count(*) AS instruments FROM instruments")[0]
    return {"status": "ok", "instruments": row["instruments"], "db": str(settings.db_path)}


@router.get("/instruments")
def list_instruments() -> list[dict]:
    return db.query_rows(
        "SELECT symbol, name, exchange, sector, currency FROM instruments ORDER BY symbol"
    )


@router.get("/screener")
def screener(
    sector: str | None = Query(None, description="Exact sector match"),
    min_change: float | None = Query(None, description="Minimum 1-day change %"),
) -> list[dict]:
    """Latest snapshot per instrument with derived metrics.

    Filtering happens here rather than in the client so the UI never has to
    receive rows it will not show.
    """
    rows = indicators.screener()
    if sector:
        rows = [r for r in rows if r.get("sector") == sector]
    if min_change is not None:
        rows = [r for r in rows if (r.get("change_pct") or 0) >= min_change]
    return rows


@router.get("/instruments/{symbol}/history")
def history(
    symbol: str,
    limit: int = Query(250, ge=1, le=5000, description="Most recent N sessions"),
) -> dict:
    symbol = symbol.upper()
    rows = indicators.history(symbol, limit=limit)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No price history for {symbol}")
    meta = db.query_rows(
        "SELECT symbol, name, sector, exchange FROM instruments WHERE symbol = ?", [symbol]
    )
    return {"symbol": symbol, "meta": meta[0] if meta else None, "candles": rows}


@router.get("/watchlist")
def watchlist(name: str = "default") -> list[dict]:
    symbols = {
        r["symbol"]
        for r in db.query_rows("SELECT symbol FROM watchlists WHERE name = ?", [name])
    }
    return [r for r in indicators.screener() if r["symbol"] in symbols]


@router.put("/watchlist/{symbol}")
def add_to_watchlist(symbol: str, name: str = "default") -> dict:
    symbol = symbol.upper()
    db.execute(
        "INSERT INTO watchlists (name, symbol) VALUES (?, ?) ON CONFLICT DO NOTHING",
        [name, symbol],
    )
    return {"watchlist": name, "symbol": symbol, "added": True}


@router.delete("/watchlist/{symbol}")
def remove_from_watchlist(symbol: str, name: str = "default") -> dict:
    symbol = symbol.upper()
    db.execute("DELETE FROM watchlists WHERE name = ? AND symbol = ?", [name, symbol])
    return {"watchlist": name, "symbol": symbol, "removed": True}


@router.get("/jobs")
def job_status() -> list[dict]:
    return jobs.status()


@router.post("/jobs/refresh")
def refresh(force: bool = False) -> dict:
    return jobs.run_due_jobs(force=force)
