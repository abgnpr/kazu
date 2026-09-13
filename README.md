# Kazu

Local-first desktop app for NSE market data analysis. Single user, single
machine, one database file.

*By [abgnpr](https://github.com/abgnpr). MIT licensed.*

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

Platform system packages:

```bash
# Fedora
sudo dnf install webkit2gtk4.1-devel gtk3-devel librsvg2-devel openssl-devel

# Debian / Ubuntu
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev librsvg2-dev libssl-dev \
    build-essential curl wget file
```

On Windows, see [Building a release → Windows](#windows). On macOS, Xcode
Command Line Tools (`xcode-select --install`).

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

## Layout

```
backend/kazu/
├── app.py            FastAPI app, CORS, token middleware, lifespan
├── __main__.py       uvicorn entrypoint (also the PyInstaller target)
├── config.py         KAZU_* settings
├── jobs.py           scheduler + staleness ledger
├── api/routes.py     HTTP endpoints
├── analytics/        SQL indicators and the breakout screen
├── sources/          NSE bhavcopy fetch + ingest scheduling
└── data/             DuckDB access and schema

frontend/src/
├── api/              typed client + TanStack Query hooks
├── components/       BreakoutTable, ScreenerTable, PriceChart, CoverageBar
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

## Everyday commands

```bash
npm run dev            # Python service + Tauri window
npm run dev:api        # just the service; docs at :8765/docs
npm run dev:ui         # just Vite, in a normal browser

npm run lint           # ruff + oxlint
npm run typecheck      # tsc over the frontend
npm run format         # ruff format
```

`npm run dev` starts the Python service first and waits for it to answer before
opening the window, so the UI never loads against a dead backend.

`npm run lint` reports two expected `react(incompatible-library)` warnings on
`useVirtualizer` in the table components: it returns functions the React
Compiler cannot memoize, so those components opt out of auto-memoization. No
virtualizer values are passed into memoized children, so this is benign.

The API is self-documenting: with the service running, open
<http://127.0.0.1:8765/docs> for live Swagger UI covering every endpoint below.

| Endpoint | What it does |
|---|---|
| `GET /api/health` | Service status and instrument count |
| `GET /api/coverage` | How much history exists, and whether it is enough for the 200 DMA |
| `GET /api/instruments` | Every known symbol with name, exchange, sector |
| `GET /api/screener` | Latest snapshot per instrument with derived metrics |
| `GET /api/breakouts` | The CAR + DMA screen; `?only_passing=true` to filter |
| `GET /api/instruments/{symbol}/history` | OHLCV plus SMA30/50/200, RSI, 52w high |
| `GET/PUT/DELETE /api/watchlist` | Read and edit a named watchlist |
| `GET /api/jobs`, `POST /api/jobs/refresh` | Scheduler state; force a refresh |
| `POST /api/ingest/backfill?days=N` | Fetch history on demand |

## Building a release

```bash
npm run build            # Linux:   AppImage
npm run build:windows    # Windows: NSIS .exe installer
```

Either command does the same two things: package the Python service into a
single executable with PyInstaller, then bundle it with the Tauri app. Output
lands in `frontend/src-tauri/target/release/bundle/`.

The person installing needs no Python, Node or Rust — it is all inside.

**You can only build for the platform you are on.** Tauri bundles natively:
there is no cross-compiling to Windows from Linux. A Windows installer needs a
Windows machine or a Windows CI runner; the same goes for macOS.

### Linux

Produces `Kazu_0.1.0_amd64.AppImage` — one portable file that runs on any
distro, no installation:

```bash
chmod +x Kazu_0.1.0_amd64.AppImage
./Kazu_0.1.0_amd64.AppImage
```

The build sets `NO_STRIP=1`. linuxdeploy bundles an old `strip` that cannot
parse the `.relr.dyn` section in current glibc libraries and aborts on nearly
every library; stripping only saves space, so it is skipped. Without it the
build fails with an unhelpful `failed to run linuxdeploy`.

To also emit `.deb` or `.rpm`, install `dpkg-dev` or `rpm-build` and change
`--bundles appimage` in `frontend/package.json` to `--bundles appimage,deb,rpm`.

### Windows

One-time setup on the Windows machine:

1. **Visual Studio Build Tools** with the *Desktop development with C++*
   workload — Rust needs the MSVC linker.
   <https://visualstudio.microsoft.com/visual-cpp-build-tools/>
2. **WebView2 runtime** — preinstalled on Windows 11 and current Windows 10. On
   older builds, install the Evergreen runtime.
   <https://developer.microsoft.com/microsoft-edge/webview2/>
3. **Rust** via <https://rustup.rs> (pick the `x86_64-pc-windows-msvc` host),
   **Node.js 20+**, **Python 3.12+**, and **uv**:
   ```powershell
   winget install --id=astral-sh.uv -e
   ```
4. **Git Bash** (ships with Git for Windows) — `scripts/build-sidecar.sh` is a
   bash script. Run the build from a Git Bash prompt, not PowerShell.

Then:

```bash
cd backend && uv sync --extra dev && cd ..
cd frontend && npm install && cd ..
npm run build:windows
```

That writes `Kazu_0.1.0_x64-setup.exe` to
`frontend/src-tauri/target/release/bundle/nsis/`.

For an MSI instead of an NSIS installer, use `--bundles msi` (it needs the WiX
toolset, which Tauri downloads on first use).

Note that `--bundles` only accepts values the *current* platform can build:
`tauri build --help` on Linux lists only `deb, rpm, appimage`, and `nsis`/`msi`
appear only when run on Windows. That is why `build:windows` is a separate
script rather than something you can invoke from here.

Two Windows details the build already handles: PyInstaller emits
`kazu-service.exe`, and Tauri expects the `.exe` to come *after* the target
triple (`kazu-service-x86_64-pc-windows-msvc.exe`) — `build-sidecar.sh` renames
it accordingly. The sidecar's parent-process watchdog is `os.kill(pid, 0)`,
which works on Windows as well.

### Building all three without three machines

`.github/workflows/release.yml` builds Linux, Windows and macOS installers on
GitHub's runners and uploads them as artifacts. Push a tag:

```bash
git tag v0.1.0 && git push --tags
```

or trigger it manually from the Actions tab. This is the practical way to get a
Windows `.exe` without keeping a Windows machine around — the runner does the
same `build-sidecar.sh` + `tauri build` that you would run locally.

### Distributing

An unsigned installer will be flagged. On Windows, SmartScreen shows
"Windows protected your PC" until the binary builds reputation or you sign it
with a code-signing certificate; on macOS, Gatekeeper blocks unsigned apps
outright. Tauri supports signing on both — see
<https://tauri.app/distribute/sign/>. For a personal or small-audience tool,
unsigned is usually fine as long as people know to expect the warning.

Bumping the version means three files, which must agree:
`package.json`, `frontend/src-tauri/tauri.conf.json`, and
`frontend/src-tauri/Cargo.toml`.

Tauri also has a built-in updater if you later want the app to update itself:
<https://tauri.app/plugin/updater/>.

### If a build fails

| Symptom | Cause |
|---|---|
| `resource path binaries/kazu-service-... doesn't exist` | Sidecar not built — run `npm run build:sidecar` |
| `failed to run linuxdeploy` | Missing `NO_STRIP=1` (see above) |
| `Error loading ASGI app. Could not import module "kazu.app"` | A frozen build was handed uvicorn an import string instead of the app object |
| `failed to read configuration file` | `--config` resolves relative to `frontend/`, so the path must be `src-tauri/tauri.release.conf.json` |
| Port 8765 already in use | An orphaned `kazu-service` — the watchdog should prevent this; kill it and report the case |

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

## License

MIT — see [LICENSE](LICENSE).

Kazu reads publicly published NSE end-of-day data. Its screening output is a
research tool, not investment advice.
