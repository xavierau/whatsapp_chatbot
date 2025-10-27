"""Database session management.

This module provides async database session factory and utilities
for PostgreSQL connection management using SQLAlchemy 2.0 AsyncIO.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Global engine instance (initialized once)
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the global async database engine.

    Returns:
        AsyncEngine instance configured for asyncpg

    Raises:
        RuntimeError: If DATABASE_URL is not configured
    """
    global _engine

    if _engine is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not configured in settings")

        # Get database name for logging (safely handle MultiHostUrl)
        db_url_str = str(settings.database_url)
        logger.info(
            "Creating async database engine: %s",
            db_url_str.split("@")[-1] if "@" in db_url_str else db_url_str,
        )

        _engine = create_async_engine(
            str(settings.database_url),
            echo=settings.is_development,  # SQL logging in development
            pool_size=10,  # Connection pool size
            max_overflow=20,  # Additional connections when pool is full
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

        logger.info("Database engine created successfully")

    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the global async session maker.

    Returns:
        async_sessionmaker configured with the engine

    Raises:
        RuntimeError: If engine cannot be created
    """
    global _async_session_maker

    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects accessible after commit
            autoflush=False,  # Manual flush control
            autocommit=False,  # Explicit transaction control
        )

        logger.info("Async session maker created successfully")

    return _async_session_maker


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions.

    Yields:
        AsyncSession instance

    Example:
        async with get_db_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

    Raises:
        Exception: Any exception from database operations (rolls back transaction)
    """
    session_maker = get_session_maker()
    session = session_maker()

    try:
        logger.debug("Database session started")
        yield session
        await session.commit()
        logger.debug("Database session committed")
    except Exception as e:
        logger.error("Database session error, rolling back: %s", e, exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()
        logger.debug("Database session closed")


async def init_db() -> None:
    """Initialize database connection and verify connectivity.

    This function should be called during application startup
    to ensure database is accessible.

    Raises:
        RuntimeError: If database connection fails
    """
    try:
        logger.info("Initializing database connection...")
        engine = get_engine()

        # Test connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")  # type: ignore

        logger.info("Database connection initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e, exc_info=True)
        raise RuntimeError(f"Database initialization failed: {e}") from e


async def close_db() -> None:
    """Close database connections and dispose of the engine.

    This function should be called during application shutdown
    to gracefully close all database connections.
    """
    global _engine, _async_session_maker

    if _engine is not None:
        logger.info("Closing database connections...")
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
        logger.info("Database connections closed")


# Dependency injection helper for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Use this as a dependency in FastAPI route handlers:

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()

    Yields:
        AsyncSession instance
    """
    async with get_db_session() as session:
        yield session
