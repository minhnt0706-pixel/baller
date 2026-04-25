"""
Baller — FastAPI backend entry point.

All configuration is pulled from environment variables (see config.py).
No secrets are hardcoded here.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limiter  # noqa: F401
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.config import get_settings
from backend.database import engine, Base
from backend.limiter import limiter
from backend.routers import courts, bookings, health, tasks

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup (Alembic handles migrations in prod)."""
    settings = get_settings()
    logger.info("Starting Baller backend (env=%s)", settings.app_env)

    # Import models so Base.metadata is populated
    import backend.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start background scheduler
    from backend.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    from backend.scheduler import stop_scheduler
    stop_scheduler()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Baller",
        description="Hanoi court booking platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------ #
    # Rate limiting (slowapi + Redis)
    # ------------------------------------------------------------------ #
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

    # Block wildcard '*' outside development
    if settings.app_env != "development":
        safe_origins = [o for o in origins if o != "*"]
    else:
        safe_origins = origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=safe_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    # Routers
    # ------------------------------------------------------------------ #
    app.include_router(health.router)
    app.include_router(courts.router, prefix="/api/v1")
    app.include_router(bookings.router, prefix="/api/v1")
    app.include_router(tasks.router, prefix="/tasks")

    return app


def _rate_limit_handler(request, exc):  # type: ignore[no-untyped-def]
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."},
    )


app = create_app()
