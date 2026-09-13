# Kazu

Local-first desktop app for market data analysis. Single user, single machine,
one database file.

```
┌──────────────────────────────────────────────┐
│ Tauri 2 (Rust shell — window + lifecycle)    │
│                                              │
│  React 19 + TypeScript + Vite                │
│  Mantine · TanStack Query/Table · Recharts   │
│                                              │
│              HTTP 127.0.0.1:8765             │
│                     │                        │
│  Python sidecar — FastAPI + APScheduler      │
│  pandas · httpx · BeautifulSoup              │
│                     │                        │
│              DuckDB (single file)            │
└──────────────────────────────────────────────┘
```

## Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- Rust (stable) — only to build the shell; there is no application Rust to write
- Linux: `webkit2gtk4.1-devel`, `gtk3-devel`, `librsvg2-devel`, `openssl-devel`

## Getting started

```bash
cd backend && uv sync --extra dev && cd ..
cd frontend && npm install && cd ..

npm run dev          # Python service + Tauri window
```

On first run the service downloads the most recent NSE bhavcopy (~2,700
equities) so the app is usable in seconds. The breakout screen needs ~250
sessions of history, which is one HTTP request per trading day — click
**Backfill 2 years** in the app when you want it (about a minute). Delete
`~/.local/share/kazu/kazu.duckdb` to reset.

Useful alternatives:

```bash
npm run dev:api      # just the Python service (reachable at :8765/docs)
npm run dev:ui       # just Vite, in a browser instead of the Tauri window
```

## Layout

```
backend/kazu/
├── app.py            FastAPI app, CORS, token middleware, lifespan
├── __main__.py       uvicorn entrypoint (also the PyInstaller target)
├── config.py         KAZU_* settings
├── jobs.py           scheduler + staleness ledger
├── api/routes.py     HTTP endpoints
├── analytics/        SQL indicators and screener metrics
└── data/             DuckDB access, schema, sample seed

frontend/src/
├── api/              typed client + TanStack Query hooks
├── components/       ScreenerTable, PriceChart, StatusBar
├── theme/            Mantine theme and formatters
└── src-tauri/        Rust shell: spawns and supervises the sidecar
```

## How the pieces connect

**The Python service owns the database.** Nothing else opens the DuckDB file.
The UI only speaks HTTP, which keeps locking, caching and migrations in one
place.

**Analysis happens in SQL.** Indicators (SMA, RSI) and screener metrics are
DuckDB window functions, so the wire carries a few hundred rows instead of the
full history.

**Freshness is tracked, not assumed.** Laptops sleep, so jobs record
`last_success` in `job_status`; on startup and every 15 minutes the scheduler
runs whatever has aged past its max-age rather than trusting a timer.

**Dev and packaged builds differ deliberately.** In a release build the Rust
shell spawns the sidecar and kills it on exit. In dev it does not — you run
`npm run dev:api` yourself, so Python restarts without rebuilding Rust.

**The API is not open.** It binds to `127.0.0.1` only, and packaged builds
require an `X-Kazu-Token` header generated at launch. The token is empty in dev.

## Building a release

```bash
npm run build
```

This packages the service with PyInstaller into
`frontend/src-tauri/binaries/kazu-service-<target-triple>`, then bundles it with
the Tauri app via `tauri.release.conf.json`, the overlay that declares the
sidecar. It is kept out of the base config so `npm run dev` does not require a
PyInstaller build. Installers land in `frontend/src-tauri/target/release/bundle/`.
The user installs one file and needs no Python, Node or Rust.

## Data source: NSE bhavcopy

The daily end-of-day file NSE publishes for the whole cash market:

```
https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip
```

Worth knowing before relying on it:

- **One file per trading date.** There is no bulk or date-range endpoint, so
  history is built one request at a time.
- **This URL scheme reaches back about two years.** Earlier dates use a
  different legacy format and are not supported.
- **A 404 is normal, not a failure.** Weekends and holidays have no file. Those
  dates are recorded in `ingest_log` as `absent` so they are never re-requested.
- **EQ and BE series only**, with ETF/fund symbols excluded, since those distort
  volume ranking.

Because the app owns an `ingest_log`, catch-up is about *missed dates* rather
than a fixed lookback: leave the app closed for two weeks and the next launch
fills in those sessions, capped at 90 days (beyond that, use backfill).

## The breakout screen

`analytics/breakout.py` implements the CAR + DMA rule:

```
close > SMA30  AND  close > SMA50  AND  close > SMA200  AND  CAR rising 10 sessions
```

CAR is the expanding mean of closes measured from the date of the 52-week high.
Results are ranked by distance from the 200 DMA ascending — the stocks earliest
in their move.

It runs as DuckDB window functions over the entire market (~2,300 eligible
symbols in about 0.2s) rather than a per-ticker Python loop.

Two deliberate differences from the original:

- **Near-misses stay visible.** The original drops any stock whose 52-week high
  is under 10 sessions old. Here the row is kept with `car_positive = false` and
  a `car_sessions` count, so you can see why it did not qualify. Toggle
  "Only passing" to filter.
- **The CAR check is one SQL pass.** An expanding mean rises exactly when the
  new close exceeds the mean of everything before it, so no Python loop is
  needed. Equality is treated as non-failing, matching pandas'
  `is_monotonic_increasing`.

Verified against a direct pandas port of the original logic: SMA30/50/200, CAR
status, breakout flag, and 200-DMA distance agree on every symbol tested.

## Deferred decisions

- **Background service.** The sidecar dies with the app. If data should refresh
  while the UI is closed, promote the same executable to a systemd user service
  (or LaunchAgent / Windows startup task); the Rust shell already handles
  attaching to a service it did not spawn via the `managed` flag.
- **Parquet.** DuckDB alone is right until price history gets large. It reads
  Parquet directly, so moving bulk history out later is not a rewrite.
- **WebSockets.** REST is enough for daily data; FastAPI supports WS natively
  when live quotes arrive.
