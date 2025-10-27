"""Alembic migration environment configuration.

This module configures Alembic for both offline and online migrations,
supporting async SQLAlchemy with asyncpg.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.config.settings import settings

# Import all models to ensure they're registered with Base.metadata
from src.infrastructure.database.models import (  # noqa: F401
    Base,
    MessageModel,
    NoteModel,
    SessionModel,
    UserModel,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata from our models
target_metadata = Base.metadata

# Override sqlalchemy.url with settings from environment
config.set_main_option("sqlalchemy.url", str(settings.database_url))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection.

    Args:
        connection: SQLAlchemy connection to use for migrations
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode (online).

    This is used when we have an async engine and need to
    run migrations within an async context.
    """
    # Get async engine configuration from alembic.ini
    configuration = config.get_section(config.config_ini_section, {})

    # Override URL with our settings
    configuration["sqlalchemy.url"] = str(settings.database_url)

    # Create async engine
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No connection pooling for migrations
    )

    async with connectable.connect() as connection:
        # Run migrations in a sync context within the async connection
        await connection.run_sync(do_run_migrations)

    # Dispose of the engine
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Run async migrations
    asyncio.run(run_async_migrations())


# Determine which mode to run in
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
