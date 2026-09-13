"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from kazu import __version__, jobs
from kazu.api.routes import router
from kazu.config import settings
from kazu.data import db, seed

log = logging.getLogger(__name__)

# The Vite dev server and the Tauri webview are the only legitimate callers.
ALLOWED_ORIGINS = [
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "tauri://localhost",
    "http://tauri.localhost",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.connect()
    if seed.seed_if_empty():
        log.info("seeded sample market data")

    scheduler: BackgroundScheduler | None = None
    if settings.enable_scheduler:
        # Catch-up pass first: whatever went stale while the machine was asleep.
        jobs.run_due_jobs()
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(jobs.run_due_jobs, "interval", minutes=15, id="due_jobs")
        scheduler.start()
        log.info("scheduler started")

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Kazu Service", version=__version__, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    if settings.auth_token:

        @app.middleware("http")
        async def require_token(request: Request, call_next):
            """Stops other local processes and stray browser tabs from calling the API."""
            if request.method == "OPTIONS" or request.url.path in ("/docs", "/openapi.json"):
                return await call_next(request)
            if request.headers.get("X-Kazu-Token") != settings.auth_token:
                # Middleware runs outside the exception handlers, so return the
                # response directly rather than raising HTTPException.
                return JSONResponse(
                    status_code=401, content={"detail": "Invalid or missing X-Kazu-Token"}
                )
            return await call_next(request)

    app.include_router(router)
    return app


app = create_app()
