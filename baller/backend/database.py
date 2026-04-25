"""
Database connection and session management for Baller backend.

Uses SQLAlchemy async engine with asyncpg driver.
All configuration is loaded from environment variables — no hardcoded credentials.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    # READ COMMITTED isolation — SELECT … FOR UPDATE NOWAIT relies on this
    isolation_level="READ COMMITTED",
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# Dependency — FastAPI
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an :class:`AsyncSession` and guarantees
    the session is closed after the request, whether it succeeded or raised.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Health-check helper
# ---------------------------------------------------------------------------


async def check_db_health() -> bool:
    """
    Execute a trivial query to verify database reachability.

    Returns ``True`` when the database is reachable, ``False`` otherwise.
    Does **not** raise — callers should handle the bool themselves.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Startup / shutdown helpers (called from app lifespan)
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """
    Create all tables that are registered on :data:`Base`.

    In production the schema is managed by Alembic migrations; this function
    is useful for tests that spin up an in-process SQLite / PostgreSQL
    database.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine connection pool gracefully on shutdown."""
    await engine.dispose()
