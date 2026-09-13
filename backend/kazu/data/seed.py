"""Deterministic sample data, so the app has something real to render on first run.

This exists purely to make the vertical slice runnable. Delete it once real
sources are wired into kazu/sources/.
"""

from __future__ import annotations

import datetime as dt
import math
import random

import pandas as pd

from kazu.data import db

_INSTRUMENTS = [
    ("RELIANCE", "Reliance Industries", "NSE", "Energy", 1420.0),
    ("TCS", "Tata Consultancy Services", "NSE", "IT", 3180.0),
    ("HDFCBANK", "HDFC Bank", "NSE", "Financials", 1655.0),
    ("INFY", "Infosys", "NSE", "IT", 1490.0),
    ("ITC", "ITC Limited", "NSE", "FMCG", 412.0),
    ("LT", "Larsen & Toubro", "NSE", "Industrials", 3620.0),
    ("SUNPHARMA", "Sun Pharmaceutical", "NSE", "Healthcare", 1725.0),
    ("MARUTI", "Maruti Suzuki", "NSE", "Auto", 12980.0),
]

TRADING_DAYS = 500


def _walk(symbol: str, start_price: float, days: int) -> pd.DataFrame:
    """Geometric random walk with a symbol-seeded RNG, so runs are reproducible."""
    rng = random.Random(hash(symbol) & 0xFFFF)
    today = dt.date.today()
    rows = []
    price = start_price * 0.75
    date = today - dt.timedelta(days=int(days * 1.45))

    while len(rows) < days:
        date += dt.timedelta(days=1)
        if date.weekday() >= 5:  # skip weekends
            continue
        drift = 0.0004
        shock = rng.gauss(0, 0.014)
        price = max(1.0, price * math.exp(drift + shock))
        o = price * (1 + rng.gauss(0, 0.003))
        c = price
        h = max(o, c) * (1 + abs(rng.gauss(0, 0.004)))
        low = min(o, c) * (1 - abs(rng.gauss(0, 0.004)))
        rows.append(
            {
                "symbol": symbol,
                "date": date,
                "open": round(o, 2),
                "high": round(h, 2),
                "low": round(low, 2),
                "close": round(c, 2),
                "volume": int(abs(rng.gauss(4_000_000, 1_500_000))) + 100_000,
            }
        )
    return pd.DataFrame(rows)


def seed_if_empty() -> bool:
    """Populate sample data when the DB has no prices. Returns True if it seeded."""
    existing = db.query_rows("SELECT count(*) AS n FROM prices_daily")[0]["n"]
    if existing:
        return False

    instruments = pd.DataFrame(
        [
            {"symbol": s, "name": n, "exchange": e, "sector": sec, "currency": "INR"}
            for s, n, e, sec, _ in _INSTRUMENTS
        ]
    )
    db.upsert_df("instruments", instruments, keys=["symbol"])

    frames = [_walk(sym, px, TRADING_DAYS) for sym, _, _, _, px in _INSTRUMENTS]
    db.upsert_df("prices_daily", pd.concat(frames, ignore_index=True), keys=["symbol", "date"])

    fundamentals = pd.DataFrame(
        [
            {
                "symbol": sym,
                "as_of": dt.date.today(),
                "market_cap": round(px * random.Random(sym).uniform(1e6, 9e6), 0),
                "pe_ratio": round(random.Random(sym + "pe").uniform(9, 48), 2),
                "eps": round(px / random.Random(sym + "eps").uniform(12, 40), 2),
                "book_value": round(px * random.Random(sym + "bv").uniform(0.2, 0.8), 2),
            }
            for sym, _, _, _, px in _INSTRUMENTS
        ]
    )
    db.upsert_df("fundamentals", fundamentals, keys=["symbol", "as_of"])

    watch = pd.DataFrame(
        [{"name": "default", "symbol": s} for s in ("RELIANCE", "TCS", "HDFCBANK", "INFY")]
    )
    for _, r in watch.iterrows():
        db.execute(
            "INSERT INTO watchlists (name, symbol) VALUES (?, ?) ON CONFLICT DO NOTHING",
            [r["name"], r["symbol"]],
        )
    return True
