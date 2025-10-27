# Database Setup and Migration Guide

**Date:** 2025-10-25
**Version:** 1.0
**Status:** Implementation Complete

---

## Overview

This guide explains how to set up and manage the PostgreSQL database for the WhatsApp chatbot, including running migrations, testing the database connection, and understanding the database structure.

---

## Prerequisites

1. **PostgreSQL 15+** installed with **pgvector** extension
2. **Python 3.13+** environment with uv
3. **Environment variables** configured in `.env`

---

## Quick Start

### 1. Configure Database URL

Update your `.env` file with your PostgreSQL connection:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/whatsapp_chatbot
```

**Important:** Use `postgresql+asyncpg://` prefix for async SQLAlchemy support.

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE whatsapp_chatbot;

# Enable pgvector extension (if needed for future features)
\c whatsapp_chatbot
CREATE EXTENSION IF NOT EXISTS vector;

# Exit psql
\q
```

### 3. Run Migrations

```bash
# Initialize Alembic (already done)
# alembic init src/infrastructure/database/migrations

# Run migrations to create tables
uv run alembic upgrade head

# Verify migration
uv run alembic current
```

### 4. Verify Database Setup

```bash
# Connect to database
psql -U postgres -d whatsapp_chatbot

# List tables
\dt

# Should see:
# - users
# - sessions
# - messages
# - notes (from previous migration)
# - alembic_version

# Check table structure
\d users
\d sessions
\d messages

# Exit
\q
```

---

## Database Structure

### Tables Created

**users**
- Stores WhatsApp user accounts
- Unique phone numbers (E.164 format)
- User preferences (JSONB)
- Soft delete support

**sessions**
- Conversation sessions
- Links to users (FK with CASCADE)
- Status: active, expired, closed
- Auto-expiry support (30min default)
- Soft delete support

**messages**
- Individual conversation messages
- Links to sessions (FK with CASCADE)
- Role: user, assistant, system
- Tool result storage (JSONB)
- LLM performance metrics
- Soft delete support

### Indexes

**Performance Optimizations:**
- `users.phone_number` - Unique index for fast user lookup
- `users.last_active_at` - For activity tracking queries
- `users.deleted_at` - Partial index (WHERE deleted_at IS NULL)
- `sessions.user_id` - For user's session queries
- `sessions.status` - For filtering active/expired sessions
- `sessions.last_activity_at` - For expiry checks
- `sessions.deleted_at` - Partial index
- `messages.session_id` - For conversation history
- `messages.created_at` - For chronological ordering
- `messages.whatsapp_message_id` - For WhatsApp API tracking
- `messages.deleted_at` - Partial index

---

## Migration Commands

### Common Operations

```bash
# Check current migration version
uv run alembic current

# Show migration history
uv run alembic history --verbose

# Upgrade to latest
uv run alembic upgrade head

# Upgrade one version
uv run alembic upgrade +1

# Downgrade one version
uv run alembic downgrade -1

# Downgrade to specific version
uv run alembic downgrade 001_initial

# Downgrade all migrations
uv run alembic downgrade base
```

### Creating New Migrations

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "Add new field to users"

# Create empty migration (for data migrations)
uv run alembic revision -m "Populate user preferences"

# Edit the generated file in:
# src/infrastructure/database/migrations/versions/
```

---

## Testing Database Connection

### Python Script Test

Create `test_db_connection.py`:

```python
import asyncio
from src.infrastructure.database.session import init_db, close_db, get_db_session
from src.infrastructure.database.models import UserModel
from sqlalchemy import select

async def test_connection():
    """Test database connection and query."""
    try:
        # Initialize database
        await init_db()
        print("✅ Database connection successful")

        # Test query
        async with get_db_session() as session:
            result = await session.execute(select(UserModel))
            users = result.scalars().all()
            print(f"✅ Query successful: Found {len(users)} users")

        # Cleanup
        await close_db()
        print("✅ Database closed successfully")

    except Exception as e:
        print(f"❌ Database test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

Run test:
```bash
uv run python test_db_connection.py
```

### FastAPI Integration Test

```python
# In src/main.py

from src.infrastructure.database.session import init_db, close_db

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await init_db()
    logger.info("Application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown."""
    await close_db()
    logger.info("Application shutdown complete")
```

---

## Troubleshooting

### Connection Issues

**Problem:** `ConnectionRefusedError`

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start if needed
sudo systemctl start postgresql

# Check connection manually
psql -U postgres -d whatsapp_chatbot
```

**Problem:** `asyncpg.exceptions.InvalidCatalogNameError: database "whatsapp_chatbot" does not exist`

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE whatsapp_chatbot;"
```

### Migration Issues

**Problem:** `Target database is not up to date`

```bash
# Check current version
uv run alembic current

# Upgrade to latest
uv run alembic upgrade head
```

**Problem:** `Can't locate revision identified by '001_initial'`

```bash
# Verify migration files exist
ls src/infrastructure/database/migrations/versions/

# Re-run migration
uv run alembic upgrade head
```

### ENUM Type Conflicts

**Problem:** `type "session_status" already exists`

This happens if you run migrations multiple times. Fix:

```bash
# Connect to database
psql -U postgres -d whatsapp_chatbot

# Drop conflicting types
DROP TYPE IF EXISTS session_status CASCADE;
DROP TYPE IF EXISTS message_role CASCADE;

# Re-run migration
uv run alembic upgrade head
```

---

## Data Management

### Backup Database

```bash
# Backup entire database
pg_dump -U postgres whatsapp_chatbot > backup_$(date +%Y%m%d).sql

# Backup specific tables
pg_dump -U postgres -t users -t sessions -t messages whatsapp_chatbot > backup_core.sql
```

### Restore Database

```bash
# Restore from backup
psql -U postgres -d whatsapp_chatbot < backup_20251025.sql
```

### Clear All Data (Keep Schema)

```bash
psql -U postgres -d whatsapp_chatbot

TRUNCATE messages, sessions, users CASCADE;
```

---

## Performance Monitoring

### Check Table Sizes

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Monitor Index Usage

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Find Slow Queries

```sql
-- Enable query logging in postgresql.conf
-- log_min_duration_statement = 1000  # Log queries > 1 second

-- View slow query log
tail -f /var/log/postgresql/postgresql-15-main.log | grep "duration:"
```

---

## Next Steps

After database setup is complete:

1. ✅ **Test database connection** using the test script
2. ✅ **Run all entity tests** to verify models: `uv run pytest tests/unit/domain/ -v`
3. ⏭️ **Implement repositories** (UserRepository, SessionRepository, MessageRepository)
4. ⏭️ **Create integration tests** for database operations
5. ⏭️ **Implement use cases** for business logic
6. ⏭️ **Integrate with FastAPI** endpoints

---

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/en/latest/)
- [SQLAlchemy AsyncIO](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/15/index.html)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/current/)

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-25 | Claude | Initial database setup guide |
