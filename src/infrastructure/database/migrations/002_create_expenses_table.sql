-- Migration: Create expenses table with pgvector support
-- Created: 2025-10-26

-- Ensure pgvector extension is enabled (already created in 001_create_notes_table.sql)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create expenses table
CREATE TABLE IF NOT EXISTS expenses (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL CHECK (amount >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'HKD',
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    tags TEXT[] DEFAULT '{}',
    expense_date DATE NOT NULL,
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_pattern VARCHAR(20),
    receipt_path TEXT,
    embedding vector(1536),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraint: recurrence_pattern can only be set if is_recurring is true
    CONSTRAINT check_recurrence_pattern
        CHECK (
            (is_recurring = FALSE AND recurrence_pattern IS NULL) OR
            (is_recurring = TRUE)
        ),

    -- Constraint: recurrence_pattern must be valid
    CONSTRAINT check_recurrence_pattern_value
        CHECK (
            recurrence_pattern IS NULL OR
            recurrence_pattern IN ('daily', 'weekly', 'monthly', 'yearly')
        )
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, expense_date DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON expenses(user_id, category);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_tags ON expenses USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_expenses_amount ON expenses(user_id, amount);
CREATE INDEX IF NOT EXISTS idx_expenses_currency ON expenses(user_id, currency);
CREATE INDEX IF NOT EXISTS idx_expenses_is_recurring ON expenses(user_id, is_recurring) WHERE is_recurring = TRUE;

-- Create vector index for similarity search (using HNSW for better performance)
-- Note: This may take time on large datasets
CREATE INDEX IF NOT EXISTS idx_expenses_embedding ON expenses USING hnsw (embedding vector_cosine_ops);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_expenses_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to call the function
DROP TRIGGER IF EXISTS trigger_expenses_updated_at ON expenses;
CREATE TRIGGER trigger_expenses_updated_at
    BEFORE UPDATE ON expenses
    FOR EACH ROW
    EXECUTE FUNCTION update_expenses_updated_at();

-- Add comments for documentation
COMMENT ON TABLE expenses IS 'User expenses with vector embeddings for semantic search';
COMMENT ON COLUMN expenses.id IS 'Unique identifier (UUID)';
COMMENT ON COLUMN expenses.user_id IS 'WhatsApp user ID who owns this expense';
COMMENT ON COLUMN expenses.amount IS 'Expense amount (non-negative, up to 15 digits with 2 decimal places)';
COMMENT ON COLUMN expenses.currency IS '3-letter ISO 4217 currency code (default: HKD)';
COMMENT ON COLUMN expenses.description IS 'Description of the expense';
COMMENT ON COLUMN expenses.category IS 'Category for grouping expenses (max 100 chars)';
COMMENT ON COLUMN expenses.tags IS 'Array of tags for additional categorization';
COMMENT ON COLUMN expenses.expense_date IS 'Date when the expense occurred';
COMMENT ON COLUMN expenses.is_recurring IS 'Whether this is a recurring expense';
COMMENT ON COLUMN expenses.recurrence_pattern IS 'Pattern for recurring expenses (daily/weekly/monthly/yearly)';
COMMENT ON COLUMN expenses.receipt_path IS 'Optional path or URL to receipt image';
COMMENT ON COLUMN expenses.embedding IS 'Vector embedding (1536 dimensions) for semantic search';
COMMENT ON COLUMN expenses.created_at IS 'Timestamp when expense was created';
COMMENT ON COLUMN expenses.updated_at IS 'Timestamp when expense was last updated';
