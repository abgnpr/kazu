#!/usr/bin/env bash
# Dev loop: Python service with reload + Tauri window (which starts Vite itself).
# In debug builds the Rust shell does NOT spawn a sidecar; it connects to the
# service started here, so Python can restart without rebuilding Rust.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() { [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "==> starting Python service on 127.0.0.1:8765"
( cd "$ROOT/backend" && uv run python -m kazu ) &
API_PID=$!

# Give uvicorn a moment to bind before the UI starts polling it.
for _ in $(seq 1 40); do
    curl -sf http://127.0.0.1:8765/api/health >/dev/null 2>&1 && break
    sleep 0.25
done

echo "==> starting Tauri window"
cd "$ROOT/frontend" && npm run tauri dev
