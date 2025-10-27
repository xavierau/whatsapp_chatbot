"""Initial migration: create users, sessions, and messages tables.

Revision ID: 001_initial
Revises:
Create Date: 2025-10-25

This migration creates the foundational tables for the WhatsApp chatbot:
- users: WhatsApp user accounts with preferences
- sessions: Conversation sessions with lifecycle management
- messages: Individual messages with tool result support
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create ENUM types (only if they don't exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE session_status AS ENUM ('active', 'expired', 'closed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("phone_number", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_index(
        op.f("ix_users_phone_number"), "users", ["phone_number"], unique=False
    )
    op.create_index(
        op.f("ix_users_last_active_at"), "users", ["last_active_at"], unique=False
    )
    op.create_index(
        op.f("ix_users_deleted_at"),
        "users",
        ["deleted_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "expired", "closed", name="session_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_sessions_status"), "sessions", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_sessions_last_activity_at"),
        "sessions",
        ["last_activity_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sessions_deleted_at"),
        "sessions",
        ["deleted_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", name="message_role"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_result", sa.JSON(), nullable=True),
        sa.Column("whatsapp_message_id", sa.String(length=255), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_messages_session_id"), "messages", ["session_id"], unique=False
    )
    op.create_index(
        op.f("ix_messages_created_at"), "messages", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_messages_whatsapp_message_id"),
        "messages",
        ["whatsapp_message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_messages_deleted_at"),
        "messages",
        ["deleted_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop tables in reverse order (respect foreign keys)
    op.drop_index(
        op.f("ix_messages_deleted_at"), table_name="messages", postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.drop_index(op.f("ix_messages_whatsapp_message_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_created_at"), table_name="messages")
    op.drop_index(op.f("ix_messages_session_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(
        op.f("ix_sessions_deleted_at"), table_name="sessions", postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.drop_index(op.f("ix_sessions_last_activity_at"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_status"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_table("sessions")

    op.drop_index(
        op.f("ix_users_deleted_at"), table_name="users", postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.drop_index(op.f("ix_users_last_active_at"), table_name="users")
    op.drop_index(op.f("ix_users_phone_number"), table_name="users")
    op.drop_table("users")

    # Drop ENUM types
    op.execute("DROP TYPE message_role")
    op.execute("DROP TYPE session_status")
