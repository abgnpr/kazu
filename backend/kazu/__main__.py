"""Entrypoint for `python -m kazu` and the PyInstaller-built sidecar binary."""

from __future__ import annotations

import logging
import os
import sys
import threading

import uvicorn

from kazu.config import settings

log = logging.getLogger(__name__)


def _wait_for_parent_exit(pid: int, interval: float = 2.0) -> None:
    """Block until process `pid` exits.

    POSIX and Windows need different mechanisms, and getting this wrong on
    Windows is destructive: `os.kill(pid, 0)` there does NOT test for existence
    the way it does on POSIX -- any signal other than CTRL_C_EVENT/
    CTRL_BREAK_EVENT calls TerminateProcess, so the "check" would kill the very
    process we are watching.
    """
    if sys.platform == "win32":
        import ctypes

        SYNCHRONIZE = 0x00100000
        INFINITE = 0xFFFFFFFF
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return  # already gone, or not visible to us
        try:
            kernel32.WaitForSingleObject(handle, INFINITE)
        finally:
            kernel32.CloseHandle(handle)
        return

    # POSIX: signal 0 performs permission/existence checks without delivering.
    import time

    while True:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(interval)


def _watch_parent(pid: int, server: uvicorn.Server) -> None:
    """Shut the service down when the process that spawned it goes away.

    The desktop shell kills this sidecar on a normal quit, but a hard kill or a
    crash never reaches that handler -- without this the service would survive,
    keep holding the port, and block the next launch.

    Asking uvicorn to stop (rather than signalling ourselves) lets the lifespan
    shutdown run, so DuckDB is closed cleanly instead of leaving a stale lock.
    """

    def loop() -> None:
        _wait_for_parent_exit(pid)
        log.info("parent %s is gone, shutting down", pid)
        server.should_exit = True

    threading.Thread(target=loop, daemon=True, name="parent-watchdog").start()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    # A PyInstaller bundle has no importable "kazu.app" module path, so uvicorn
    # cannot resolve an import string there -- hand it the app object instead.
    # In dev the string form is kept so the reloader still works.
    if getattr(sys, "frozen", False):
        from kazu.app import app as application

        target: object = application
    else:
        target = "kazu.app:app"

    config = uvicorn.Config(
        target,  # type: ignore[arg-type]
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)

    parent = os.environ.get("KAZU_PARENT_PID")
    if parent and parent.isdigit():
        _watch_parent(int(parent), server)

    server.run()


if __name__ == "__main__":
    main()
