#!/usr/bin/env bash
# Package the Python service into a single executable and place it where Tauri
# expects sidecars: src-tauri/binaries/kazu-service-<target-triple>
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
DEST="$ROOT/frontend/src-tauri/binaries"

# Tauri matches the sidecar filename against the Rust host triple.
TRIPLE="$(rustc -vV | awk '/^host:/ {print $2}')"
[ -n "$TRIPLE" ] || { echo "could not determine rust host triple" >&2; exit 1; }

echo "==> building sidecar for $TRIPLE"
cd "$BACKEND"
uv sync --extra dev

uv run pyinstaller \
    --name kazu-service \
    --onefile \
    --clean \
    --noconfirm \
    --distpath "$BACKEND/dist" \
    --workpath "$BACKEND/build" \
    --specpath "$BACKEND/build" \
    --collect-all duckdb \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets.auto \
    kazu/__main__.py

mkdir -p "$DEST"
cp "$BACKEND/dist/kazu-service" "$DEST/kazu-service-$TRIPLE"
chmod +x "$DEST/kazu-service-$TRIPLE"

echo "==> sidecar ready: $DEST/kazu-service-$TRIPLE"
