"""Entrypoint for `python -m kazu` and the PyInstaller-built sidecar binary."""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time

import uvicorn

from kazu.config import settings

log = logging.getLogger(__name__)


def _watch_parent(pid: int, interval: float = 2.0) -> None:
    """Exit when the process that spawned us goes away.

    The desktop shell kills this sidecar on a normal quit, but a SIGKILL or a
    crash never reaches that handler -- without this the service would survive,
    keep holding the port, and block the next launch.
    """

    def loop() -> None:
        while True:
            try:
                os.kill(pid, 0)  # signal 0: existence check only
            except OSError:
                log.info("parent %s is gone, shutting down", pid)
                os.kill(os.getpid(), signal.SIGTERM)
                return
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True, name="parent-watchdog").start()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    # A PyInstaller bundle has no importable "kazu.app" module path, so uvicorn
    # cannot resolve an import string there -- hand it the app object instead.
    # In dev the string form is kept so the reloader still works.
    parent = os.environ.get("KAZU_PARENT_PID")
    if parent and parent.isdigit():
        _watch_parent(int(parent))

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
