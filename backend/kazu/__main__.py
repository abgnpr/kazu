"""Entrypoint for `python -m kazu` and the PyInstaller-built sidecar binary."""

from __future__ import annotations

import logging

import uvicorn

from kazu.config import settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    # Import by path so uvicorn's reloader can work in dev.
    uvicorn.run(
        "kazu.app:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
