#!/usr/bin/env python3
"""Run the expense table migration."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.config.settings import settings
from src.infrastructure.database.session import get_engine


async def run_migration():
    """Run the expenses table migration."""
    print("=" * 60)
    print("Running Expense Table Migration")
    print("=" * 60)

    # Read migration file
    migration_file = project_root / "src/infrastructure/database/migrations/002_create_expenses_table.sql"

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    print(f"\n📄 Reading migration from: {migration_file}")
    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    # Get database engine
    print(f"\n🔌 Connecting to database...")
    print(f"   URL: {settings.database_url}")

    engine = get_engine()

    try:
        async with engine.begin() as conn:
            print("\n🚀 Executing migration...")

            # Split SQL into individual statements
            # Handle dollar-quoted strings properly
            statements = []
            current_statement = []
            in_dollar_quote = False
            dollar_tag = None

            for line in migration_sql.split('\n'):
                # Skip standalone comment lines
                stripped = line.strip()
                if not current_statement and (not stripped or stripped.startswith('--')):
                    continue

                # Check for dollar-quote markers
                if '$$' in line:
                    if not in_dollar_quote:
                        # Starting a dollar-quoted string
                        in_dollar_quote = True
                        # Extract tag if present (e.g., $body$ or just $$)
                        if '$' in line:
                            dollar_tag = '$$'  # Simplify: just track $$
                    else:
                        # Ending a dollar-quoted string
                        in_dollar_quote = False
                        dollar_tag = None

                current_statement.append(line)

                # Check if line ends with semicolon (statement terminator)
                # But only if we're not inside a dollar-quoted string
                if not in_dollar_quote and stripped.endswith(';'):
                    stmt = '\n'.join(current_statement).strip()
                    if stmt:
                        statements.append(stmt)
                    current_statement = []

            print(f"   Found {len(statements)} SQL statements to execute")

            # Execute each statement
            for i, stmt in enumerate(statements, 1):
                try:
                    # Show what we're executing (first 60 chars)
                    preview = stmt[:60].replace('\n', ' ')
                    if len(stmt) > 60:
                        preview += "..."
                    print(f"   [{i}/{len(statements)}] {preview}")

                    await conn.execute(text(stmt))
                except Exception as e:
                    # Some statements might fail if already exists, which is OK
                    error_msg = str(e).lower()
                    if 'already exists' in error_msg or 'duplicate' in error_msg:
                        print(f"         ⚠️  Already exists (OK)")
                    else:
                        print(f"         ❌ Error: {e}")
                        raise

            print(f"\n   ✅ All statements executed successfully")

        print("\n✅ Migration completed successfully!")
        print("\n📊 Created:")
        print("   - expenses table")
        print("   - Indexes (user_id, date, category, tags, embedding)")
        print("   - Constraints (amount >= 0, recurrence pattern validation)")
        print("   - Triggers (auto-update timestamps)")

        # Verify table exists
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'expenses'")
            )
            count = result.scalar()

            if count > 0:
                print("\n✅ Verification: expenses table exists")

                # Get column count
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'expenses'")
                )
                col_count = result.scalar()
                print(f"   - {col_count} columns created")
            else:
                print("\n❌ Verification failed: expenses table not found")
                return False

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()
        print("\n🔌 Database connection closed")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Expense Tracking System - Database Migration")
    print("=" * 60 + "\n")

    success = asyncio.run(run_migration())

    if success:
        print("\n" + "=" * 60)
        print("✅ MIGRATION SUCCESSFUL")
        print("=" * 60)
        print("\nYou can now:")
        print("  1. Run test_expense_tools.ipynb to test the system")
        print("  2. Use expense_tools() in your application")
        print("  3. Check docs/guides/2025-10-26-using-expense-tools.md for usage")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ MIGRATION FAILED")
        print("=" * 60)
        print("\nPlease check:")
        print("  1. PostgreSQL is running")
        print("  2. DATABASE_URL in .env is correct")
        print("  3. pgvector extension is installed")
        sys.exit(1)
