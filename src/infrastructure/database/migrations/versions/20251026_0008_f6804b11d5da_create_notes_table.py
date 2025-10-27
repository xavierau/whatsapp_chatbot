"""create_notes_table

Revision ID: f6804b11d5da
Revises: 001_initial
Create Date: 2025-10-26 00:08:03.807752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'f6804b11d5da'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - create notes table with pgvector support."""
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create notes table
    op.create_table(
        'notes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(255), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create indexes
    op.create_index('idx_notes_user_updated', 'notes', ['user_id', 'updated_at'], postgresql_using='btree')
    op.create_index('idx_notes_user_created', 'notes', ['user_id', 'created_at'], postgresql_using='btree')
    op.create_index('idx_notes_tags', 'notes', ['tags'], postgresql_using='gin')

    # Create vector index for similarity search (HNSW for performance)
    op.execute(
        'CREATE INDEX idx_notes_embedding ON notes USING hnsw (embedding vector_cosine_ops)'
    )

    # Create function to automatically update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_notes_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER trigger_notes_updated_at
            BEFORE UPDATE ON notes
            FOR EACH ROW
            EXECUTE FUNCTION update_notes_updated_at();
    """)


def downgrade() -> None:
    """Downgrade database schema - drop notes table."""
    # Drop trigger first
    op.execute('DROP TRIGGER IF EXISTS trigger_notes_updated_at ON notes')

    # Drop function
    op.execute('DROP FUNCTION IF EXISTS update_notes_updated_at()')

    # Drop table (indexes will be dropped automatically)
    op.drop_table('notes')

    # Note: We don't drop the vector extension as other tables might use it
