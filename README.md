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

On first run the service creates its database and seeds sample instruments, so
the UI has data immediately. Delete `~/.local/share/kazu/kazu.duckdb` to reset.

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
the Tauri app. Installers land in `frontend/src-tauri/target/release/bundle/`.
The user installs one file and needs no Python, Node or Rust.

## Adding a real data source

The seed data exists only to make the app runnable. To replace it:

1. Add a module under `backend/kazu/sources/` that fetches and normalises data
   into a DataFrame.
2. Call it from `_refresh_prices()` in `jobs.py` and write with
   `db.upsert_df(...)`; the staleness bookkeeping around it already works.
3. Delete `data/seed.py` and the `seed_if_empty()` call in `app.py`.

## Deferred decisions

- **Background service.** The sidecar dies with the app. If data should refresh
  while the UI is closed, promote the same executable to a systemd user service
  (or LaunchAgent / Windows startup task); the Rust shell already handles
  attaching to a service it did not spawn via the `managed` flag.
- **Parquet.** DuckDB alone is right until price history gets large. It reads
  Parquet directly, so moving bulk history out later is not a rewrite.
- **WebSockets.** REST is enough for daily data; FastAPI supports WS natively
  when live quotes arrive.
