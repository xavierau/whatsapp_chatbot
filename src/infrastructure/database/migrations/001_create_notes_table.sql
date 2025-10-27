-- Migration: Create notes table with pgvector support
-- Created: 2025-10-25

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create notes table
CREATE TABLE IF NOT EXISTS notes (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id);
CREATE INDEX IF NOT EXISTS idx_notes_user_updated ON notes(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_user_created ON notes(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes USING gin(tags);

-- Create vector index for similarity search (using HNSW for better performance)
-- Note: This may take time on large datasets
CREATE INDEX IF NOT EXISTS idx_notes_embedding ON notes USING hnsw (embedding vector_cosine_ops);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_notes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to call the function
DROP TRIGGER IF EXISTS trigger_notes_updated_at ON notes;
CREATE TRIGGER trigger_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_notes_updated_at();

-- Add comments for documentation
COMMENT ON TABLE notes IS 'User notes with vector embeddings for semantic search';
COMMENT ON COLUMN notes.id IS 'Unique identifier (UUID)';
COMMENT ON COLUMN notes.user_id IS 'WhatsApp user ID who owns this note';
COMMENT ON COLUMN notes.title IS 'Note title (max 255 chars)';
COMMENT ON COLUMN notes.content IS 'Note content (unlimited text)';
COMMENT ON COLUMN notes.tags IS 'Array of tags for categorization';
COMMENT ON COLUMN notes.embedding IS 'Vector embedding (1536 dimensions) for semantic search';
COMMENT ON COLUMN notes.created_at IS 'Timestamp when note was created';
COMMENT ON COLUMN notes.updated_at IS 'Timestamp when note was last updated';
