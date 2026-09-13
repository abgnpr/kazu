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

# PyInstaller appends .exe on Windows, and Tauri expects the extension to be
# preserved after the target triple. Works under Git Bash / MSYS on Windows.
EXT=""
case "$TRIPLE" in
    *windows*) EXT=".exe" ;;
esac

mkdir -p "$DEST"
cp "$BACKEND/dist/kazu-service$EXT" "$DEST/kazu-service-$TRIPLE$EXT"
chmod +x "$DEST/kazu-service-$TRIPLE$EXT" 2>/dev/null || true

# Fail loudly here rather than inside the Rust build, where the error is just
# "resource path doesn't exist".
[ -f "$DEST/kazu-service-$TRIPLE$EXT" ] || {
    echo "sidecar missing: $DEST/kazu-service-$TRIPLE$EXT" >&2
    exit 1
}

echo "==> sidecar ready: $DEST/kazu-service-$TRIPLE$EXT"
