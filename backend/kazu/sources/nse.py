"""NSE daily bhavcopy ingest.

NSE publishes one UDiFF CSV (zipped) per trading date at a predictable URL.
There is no bulk/range endpoint, so history is built one date at a time; the
current URL scheme covers roughly the last two years.

A 404 is a normal outcome, not a failure: weekends, holidays and dates before
the file is published simply have no bhavcopy. Those dates are recorded as
'absent' so they are never requested again.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import zipfile

import httpx
import pandas as pd

from kazu.data import db

log = logging.getLogger(__name__)

BHAVCOPY_URL = (
    "https://nsearchives.nseindia.com/content/cm/"
    "BhavCopy_NSE_CM_0_0_0_{date:%Y%m%d}_F_0000.csv.zip"
)

# NSE rejects requests without a browser-ish User-Agent.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Equity series only. Exclude ETFs and fund units, which distort volume ranking.
WANTED_SERIES = {"EQ", "BE"}
EXCLUDE_KEYWORDS = ("BEES", "ETF", "GOLD", "LIQUID", "SILVER", "LIQ", "CASE")

# The UDiFF header names, with legacy fallbacks in case NSE reverts a column.
_COLS = {
    "symbol": ("TckrSymb", "SYMBOL"),
    "series": ("SctySrs", "SERIES"),
    "name": ("FinInstrmNm",),
    "isin": ("ISIN",),
    "date": ("TradDt", "TIMESTAMP"),
    "open": ("OpnPric", "OPEN"),
    "high": ("HghPric", "HIGH"),
    "low": ("LwPric", "LOW"),
    "close": ("ClsPric", "CLOSE"),
    "volume": ("TtlTradgVol", "TtlTrdQty", "TOTTRDQTY"),
    "turnover": ("TtlTrfVal", "TOTTRDVAL"),
    "trades": ("TtlNbOfTxsExctd", "TOTALTRADES"),
    "instrument": ("FinInstrmTp",),
}


class BhavcopyAbsent(Exception):
    """NSE has no bhavcopy for this date (weekend, holiday, or not yet published)."""


def _resolve(header: list[str]) -> dict[str, str]:
    """Map our field names onto whichever column spellings this file uses."""
    found = {}
    for field, candidates in _COLS.items():
        for c in candidates:
            if c in header:
                found[field] = c
                break
    missing = {"symbol", "date", "close", "volume"} - found.keys()
    if missing:
        raise ValueError(f"bhavcopy missing required columns: {sorted(missing)}")
    return found


def _num(value: str | None) -> float | None:
    if value is None:
        return None
    v = value.strip()
    if not v or v == "-":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def fetch_bhavcopy(date: dt.date, *, client: httpx.Client | None = None) -> list[dict]:
    """Download and parse one date's bhavcopy into equity rows.

    Raises BhavcopyAbsent when NSE has no file for the date.
    """
    url = BHAVCOPY_URL.format(date=date)
    owned = client is None
    client = client or httpx.Client(headers=HEADERS, timeout=30.0, follow_redirects=True)
    try:
        resp = client.get(url)
    finally:
        if owned:
            client.close()

    if resp.status_code == 404:
        raise BhavcopyAbsent(f"no bhavcopy for {date}")
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        name = next((n for n in z.namelist() if n.lower().endswith(".csv")), None)
        if name is None:
            raise ValueError(f"no CSV inside bhavcopy zip for {date}")
        with z.open(name) as fh:
            reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig"))
            if reader.fieldnames is None:
                raise ValueError(f"empty bhavcopy for {date}")
            cols = _resolve([f.strip() for f in reader.fieldnames])
            return _parse(reader, cols, date)


def _parse(reader: csv.DictReader, cols: dict[str, str], date: dt.date) -> list[dict]:
    rows: list[dict] = []
    for raw in reader:
        rec = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}

        series = rec.get(cols.get("series", ""), "")
        if series and series not in WANTED_SERIES:
            continue

        # Derivatives share the file; keep cash-segment stocks only.
        instrument = rec.get(cols.get("instrument", ""), "")
        if instrument and instrument not in ("STK", "EQ"):
            continue

        symbol = rec.get(cols["symbol"], "")
        if not symbol:
            continue
        upper = symbol.upper()
        if any(k in upper for k in EXCLUDE_KEYWORDS):
            continue

        close = _num(rec.get(cols["close"]))
        volume = _num(rec.get(cols["volume"]))
        if close is None:
            continue

        traded = rec.get(cols.get("date", ""), "")
        try:
            trade_date = dt.date.fromisoformat(traded[:10]) if traded else date
        except ValueError:
            trade_date = date

        rows.append(
            {
                "symbol": symbol,
                "date": trade_date,
                "open": _num(rec.get(cols.get("open", ""))),
                "high": _num(rec.get(cols.get("high", ""))),
                "low": _num(rec.get(cols.get("low", ""))),
                "close": close,
                "volume": int(volume) if volume is not None else None,
                "turnover": _num(rec.get(cols.get("turnover", ""))),
                "trades": int(_num(rec.get(cols.get("trades", ""))) or 0) or None,
                "name": rec.get(cols.get("name", ""), "") or None,
                "isin": rec.get(cols.get("isin", ""), "") or None,
                "series": series or None,
            }
        )
    return rows


def ingest_date(date: dt.date, *, client: httpx.Client | None = None) -> int:
    """Fetch one date and write it to the database. Returns rows stored.

    Records the outcome in ingest_log either way, so absent dates are skipped on
    later runs instead of being re-requested.
    """
    try:
        rows = fetch_bhavcopy(date, client=client)
    except BhavcopyAbsent:
        db.execute(
            """
            INSERT INTO ingest_log (date, status, rows, fetched, note)
            VALUES (?, 'absent', 0, current_timestamp, ?)
            ON CONFLICT (date) DO UPDATE SET
                status = 'absent', rows = 0, fetched = excluded.fetched, note = excluded.note
            """,
            [date, "no file published (holiday/weekend)"],
        )
        return 0

    if not rows:
        db.execute(
            """
            INSERT INTO ingest_log (date, status, rows, fetched, note)
            VALUES (?, 'empty', 0, current_timestamp, NULL)
            ON CONFLICT (date) DO UPDATE SET
                status = 'empty', rows = 0, fetched = excluded.fetched
            """,
            [date],
        )
        return 0

    frame = pd.DataFrame(rows)

    instruments = (
        frame[["symbol", "name", "isin", "series"]]
        .drop_duplicates(subset=["symbol"])
        .assign(exchange="NSE", sector=None, currency="INR")
    )
    # Keep any sector already recorded: the bhavcopy does not carry one.
    db.execute(
        """
        INSERT INTO instruments (symbol, name, isin, series, exchange, sector, currency)
        SELECT symbol, name, isin, series, exchange, sector, currency FROM _instr
        ON CONFLICT (symbol) DO UPDATE SET
            name   = coalesce(excluded.name, instruments.name),
            isin   = coalesce(excluded.isin, instruments.isin),
            series = coalesce(excluded.series, instruments.series)
        """,
        _register=("_instr", instruments),
    )

    prices = frame[
        ["symbol", "date", "open", "high", "low", "close", "volume", "turnover", "trades"]
    ]
    stored = db.upsert_df("prices_daily", prices, keys=["symbol", "date"])

    db.execute(
        """
        INSERT INTO ingest_log (date, status, rows, fetched, note)
        VALUES (?, 'ok', ?, current_timestamp, NULL)
        ON CONFLICT (date) DO UPDATE SET
            status = 'ok', rows = excluded.rows, fetched = excluded.fetched, note = NULL
        """,
        [date, stored],
    )
    log.info("ingested %s: %d rows", date, stored)
    return stored
