"""Create database tables directly using SQLAlchemy.

This script creates all tables for the WhatsApp chatbot database.
Run this instead of Alembic migrations if you encounter ENUM conflicts.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine

from src.config.settings import settings
from src.infrastructure.database.models.user_model import Base


async def create_tables():
    """Create all database tables."""
    if not settings.database_url:
        print("ERROR: DATABASE_URL is not configured")
        return

    print(f"Connecting to database...")
    engine = create_async_engine(str(settings.database_url), echo=True)

    async with engine.begin() as conn:
        print("Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)

        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("\n✅ Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
