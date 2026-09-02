"""
The Witness Network – Database Core
=====================================
Async SQLAlchemy engine + session factory using aiosqlite.
Provides the `get_db` dependency for FastAPI route injection.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# ── Async Engine ──────────────────────────────────────────────────────
# `echo=True` in DEBUG mode prints all generated SQL for inspection.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# ── Session Factory ───────────────────────────────────────────────────
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative Base ──────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models in the application."""
    pass


# ── Dependency Injection ──────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields an async database session.
    Automatically closes the session when the request is done.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Table Initialisation ─────────────────────────────────────────────
async def init_db() -> None:
    """
    Create all tables that don't yet exist.
    Called once during application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
