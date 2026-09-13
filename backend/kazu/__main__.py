"""Entrypoint for `python -m kazu` and the PyInstaller-built sidecar binary."""

from __future__ import annotations

import logging
import sys

import uvicorn

from kazu.config import settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    # A PyInstaller bundle has no importable "kazu.app" module path, so uvicorn
    # cannot resolve an import string there -- hand it the app object instead.
    # In dev the string form is kept so the reloader still works.
    frozen = getattr(sys, "frozen", False)
    if frozen:
        from kazu.app import app as application

        target: object = application
    else:
        target = "kazu.app:app"

    uvicorn.run(
        target,  # type: ignore[arg-type]
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
