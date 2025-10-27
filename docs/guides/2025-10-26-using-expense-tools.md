# Using the Expense Tracking System

**Date**: 2025-10-26
**Audience**: Developers and AI Agents
**Status**: Active

## Quick Start

The expense tracking system provides a comprehensive tool for LLM agents to create, manage, and search expenses with semantic (vector-based) search capabilities, multi-currency support, recurring expenses, and powerful analytics.

## Installation & Setup

### 1. Database Setup

First, ensure PostgreSQL with pgvector extension is installed and running:

```bash
# Install pgvector (if not already installed)
# macOS:
brew install pgvector

# Ubuntu/Debian:
sudo apt-get install postgresql-pgvector

# Or via Docker:
docker run -d \
  --name postgres-vector \
  -e POSTGRES_PASSWORD=mypassword \
  -p 5432:5432 \
  ankane/pgvector
```

### 2. Run Database Migration

Apply the expenses table migration:

```bash
# Connect to your database
psql $DATABASE_URL

# Run the migration
\i src/infrastructure/database/migrations/002_create_expenses_table.sql
```

### 3. Configure Environment

Set up your environment variables in `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/whatsapp_chatbot
GEMINI_API_KEY=your_gemini_api_key_here
EMBEDDING_MODEL=gemini-embedding-001
PGVECTOR_DIMENSION=1536
DEFAULT_CURRENCY=HKD
```

### 4. Initialize Dependencies

The expense tools require two dependencies to be configured:

```python
from src.infrastructure.database.repositories.expense_repository import ExpenseRepository
from src.infrastructure.llm.embedding.gemini_embedding_service import GeminiEmbeddingService
from src.infrastructure.llm.tools.expenses import configure_expense_tools, set_user_context
from src.config.settings import settings

# Initialize embedding service
embedding_service = GeminiEmbeddingService(
    api_key=settings.gemini_api_key,
    model_name=settings.embedding_model
)

# Initialize repository (with your database session)
repository = ExpenseRepository(session=your_async_session)

# Configure expense tools
configure_expense_tools(
    session_factory=your_session_factory,
    embedding_service=embedding_service
)

# Set user context (per conversation)
set_user_context(user_id="whatsapp_user_123")
```

## Agent Usage

The agent uses a single function `expense_tools(operation, **kwargs)` for all expense operations.

### Creating Expenses

```python
# Basic expense creation
result = expense_tools(
    operation="create",
    amount=150.50,
    description="Lunch at Italian restaurant",
    category="food",
)
# Returns: "Expense created successfully. ID: abc-123, Amount: 150.50 HKD, Category: 'food', Date: 2025-10-26"

# Expense with all optional fields
result = expense_tools(
    operation="create",
    amount=1500,
    currency="USD",
    description="Monthly rent payment",
    category="housing",
    tags=["rent", "recurring", "essential"],
    expense_date="2025-10-26",
    is_recurring=True,
    recurrence_pattern="monthly",
    receipt_path="/receipts/rent_oct_2025.pdf"
)

# Different currencies
result = expense_tools(
    operation="create",
    amount=100,
    currency="USD",
    description="Online subscription",
    category="subscriptions"
)
```

**Validation Examples**:
```python
# Missing amount - gets helpful error
result = expense_tools(operation="create", description="Test", category="food")
# Returns: "Error: 'amount' is required for creating an expense. Please provide an amount."

# Negative amount - gets helpful error
result = expense_tools(operation="create", amount=-50, description="Test", category="food")
# Returns: "Error: 'amount' cannot be negative."

# Invalid currency code
result = expense_tools(operation="create", amount=100, currency="US", description="Test", category="food")
# Returns: "Error: 'currency' must be a 3-letter ISO 4217 code (e.g., 'HKD', 'USD')."
```

### Updating Expenses

```python
# Update amount and category
result = expense_tools(
    operation="update",
    expense_id="abc-123",
    amount=175.00,
    category="dining"
)

# Update only description (will regenerate embedding)
result = expense_tools(
    operation="update",
    expense_id="abc-123",
    description="Lunch at Italian restaurant with colleagues"
)

# Update multiple fields
result = expense_tools(
    operation="update",
    expense_id="abc-123",
    amount=1600,
    description="Monthly rent - includes utilities",
    tags=["rent", "monthly", "utilities"]
)

# Convert to recurring expense
result = expense_tools(
    operation="update",
    expense_id="abc-123",
    is_recurring=True,
    recurrence_pattern="monthly"
)
```

**Validation Examples**:
```python
# Wrong type for expense_id
result = expense_tools(operation="update", expense_id=123, amount=200)
# Returns: "Error: 'expense_id' must be a non-empty string, not int."

# No fields to update
result = expense_tools(operation="update", expense_id="abc-123")
# Returns: "Error: At least one field must be provided to update."
```

### Getting a Single Expense

```python
result = expense_tools(operation="get", expense_id="abc-123")
# Returns JSON:
# {
#   "id": "abc-123",
#   "user_id": "user123",
#   "amount": "150.50",
#   "currency": "HKD",
#   "description": "Lunch at Italian restaurant",
#   "category": "food",
#   "tags": ["restaurant", "lunch"],
#   "expense_date": "2025-10-26",
#   "is_recurring": false,
#   "recurrence_pattern": null,
#   "receipt_path": null,
#   "created_at": "2025-10-26T10:30:00Z",
#   "updated_at": "2025-10-26T11:00:00Z"
# }

# Expense not found
result = expense_tools(operation="get", expense_id="invalid-id")
# Returns: "Expense not found. ID: invalid-id"
```

### Listing Expenses

```python
# List first 10 expenses (default)
result = expense_tools(operation="list")

# List with pagination
result = expense_tools(operation="list", limit=20, offset=10)

# List expenses in date range
result = expense_tools(
    operation="list",
    date_from="2025-10-01",
    date_to="2025-10-31",
    limit=50
)

# Returns formatted list:
# Found 15 expense(s):
#
# 1. [abc-123] Lunch at Italian restaurant
#    Amount: 150.50 HKD
#    Category: food
#    Date: 2025-10-26
#    Tags: restaurant, lunch
#
# 2. [def-456] Monthly rent
#    Amount: 15000.00 HKD
#    Category: housing
#    Date: 2025-10-01
#    Tags: rent, recurring
# ...
```

### Searching Expenses

#### Semantic Search (Vector-Based)

Best for finding expenses by meaning, not exact keywords:

```python
# Find expenses related to dining (finds "restaurant", "cafe", "food", etc.)
result = expense_tools(
    operation="search",
    query="where did I eat out?",
    search_type="semantic",
    limit=5
)

# Find expenses about transportation
result = expense_tools(
    operation="search",
    query="transportation and commute",
    search_type="semantic"
)

# Find expenses related to a specific event
result = expense_tools(
    operation="search",
    query="client meeting expenses",
    search_type="semantic",
    limit=10
)
```

#### Category Search

Exact category matching:

```python
# Find all food expenses
result = expense_tools(
    operation="search",
    search_type="category",
    category="food",
    limit=20
)

# Find all housing expenses
result = expense_tools(
    operation="search",
    search_type="category",
    category="housing"
)
```

#### Tag-Based Search

Filter by tags:

```python
# Find expenses with any of these tags
result = expense_tools(
    operation="search",
    search_type="tags",
    tags=["business", "client", "meeting"]
)

# Find work-related expenses
result = expense_tools(
    operation="search",
    search_type="tags",
    tags=["work", "business"]
)
```

#### Amount Range Search

Filter by amount:

```python
# Find expenses over 1000 HKD
result = expense_tools(
    operation="search",
    search_type="amount_range",
    amount_min=1000,
    limit=10
)

# Find expenses between 50 and 200 HKD
result = expense_tools(
    operation="search",
    search_type="amount_range",
    amount_min=50,
    amount_max=200
)

# Find small expenses (under 100 HKD)
result = expense_tools(
    operation="search",
    search_type="amount_range",
    amount_max=100
)
```

### Deleting Expenses

```python
result = expense_tools(operation="delete", expense_id="abc-123")
# Returns: "Expense deleted successfully. ID: abc-123"

# Expense not found
result = expense_tools(operation="delete", expense_id="invalid-id")
# Returns: "Expense not found. ID: invalid-id"
```

### Analytics

#### Total by Category

```python
# Total expenses by category (all time)
result = expense_tools(
    operation="analytics",
    analytics_type="total_by_category"
)
# Returns:
# Total expenses by category:
#
# - food: 3250.50 HKD
# - housing: 15000.00 HKD
# - transport: 850.00 HKD
# - entertainment: 1200.00 HKD

# Total by category for date range
result = expense_tools(
    operation="analytics",
    analytics_type="total_by_category",
    date_from="2025-10-01",
    date_to="2025-10-31"
)
```

#### Monthly Summary

```python
# Get summary for October 2025
result = expense_tools(
    operation="analytics",
    analytics_type="monthly_summary",
    year=2025,
    month=10
)
# Returns:
# Monthly summary for 2025-10:
#
# Total: 20500.50 HKD
# Count: 45 expenses
# Average: 455.57 HKD
#
# By category:
# - housing: 15000.00 HKD
# - food: 3250.50 HKD
# - transport: 1450.00 HKD
# - entertainment: 800.00 HKD
```

## Error Handling

All errors are returned as plain English strings to help the agent understand what went wrong:

### Common Errors

**Invalid Operation**:
```python
result = expense_tools(operation="invalid_op")
# "Error: Unknown operation 'invalid_op'. Valid operations are: create, update, delete, get, list, search, analytics."
```

**Type Errors**:
```python
result = expense_tools(operation="create", amount="not-a-number", description="Test", category="test")
# "Error: 'amount' must be a number, got 'not-a-number'."

result = expense_tools(operation="list", limit="ten")
# "Error: 'limit' must be an integer, not str."
```

**Missing Required Fields**:
```python
result = expense_tools(operation="search", search_type="semantic")
# "Error: 'query' is required for semantic search. Please provide a search query."

result = expense_tools(operation="search", search_type="tags")
# "Error: 'tags' parameter is required for tag search. Please provide a list of tags."
```

**Invalid Values**:
```python
result = expense_tools(operation="list", limit=-5)
# "Error: 'limit' must be a positive number."

result = expense_tools(operation="create", amount=-100, description="Test", category="test")
# "Error: 'amount' cannot be negative."
```

## Best Practices

### 1. Use Descriptive Descriptions

```python
# Good
expense_tools(operation="create", amount=50, description="Taxi from office to client meeting at ABC Corp", category="transport")

# Avoid
expense_tools(operation="create", amount=50, description="Taxi", category="transport")
```

### 2. Add Relevant Tags

```python
# Good - specific, categorized
expense_tools(operation="create", amount=150, description="...", category="food", tags=["client-lunch", "reimbursable", "italian"])

# Avoid - too generic
expense_tools(operation="create", amount=150, description="...", category="food", tags=["stuff"])
```

### 3. Choose the Right Search Type

- **Semantic**: Finding concepts, ideas, related topics
  ```python
  # Good for: "Find expenses related to client meetings"
  expense_tools(operation="search", query="client meetings", search_type="semantic")
  ```

- **Category**: Filtering by specific category
  ```python
  # Good for: "Find all food expenses"
  expense_tools(operation="search", search_type="category", category="food")
  ```

- **Tags**: Filtering by characteristics
  ```python
  # Good for: "Find all reimbursable expenses"
  expense_tools(operation="search", search_type="tags", tags=["reimbursable"])
  ```

- **Amount Range**: Finding expenses within budget
  ```python
  # Good for: "Find large expenses over 1000 HKD"
  expense_tools(operation="search", search_type="amount_range", amount_min=1000)
  ```

### 4. Use Appropriate Currency Codes

```python
# Always use 3-letter ISO 4217 codes
expense_tools(operation="create", amount=100, currency="HKD", description="...", category="...")
expense_tools(operation="create", amount=100, currency="USD", description="...", category="...")
expense_tools(operation="create", amount=100, currency="EUR", description="...", category="...")

# Default is HKD if not specified
expense_tools(operation="create", amount=100, description="...", category="...")  # Uses HKD
```

### 5. Track Recurring Expenses

```python
# Mark recurring expenses for better tracking
expense_tools(
    operation="create",
    amount=1500,
    description="Monthly rent",
    category="housing",
    is_recurring=True,
    recurrence_pattern="monthly",
    tags=["rent", "fixed-cost"]
)

# Track subscriptions
expense_tools(
    operation="create",
    amount=9.99,
    currency="USD",
    description="Netflix subscription",
    category="entertainment",
    is_recurring=True,
    recurrence_pattern="monthly",
    tags=["subscription", "streaming"]
)
```

### 6. Attach Receipts When Possible

```python
# Store receipt path for record-keeping
expense_tools(
    operation="create",
    amount=250.50,
    description="Office supplies from ABC Store",
    category="office",
    receipt_path="/receipts/2025/10/abc_store_20251026.pdf",
    tags=["reimbursable", "office-supplies"]
)
```

## Advanced Usage

### Multi-Step Workflows

```python
# 1. Create an expense
create_result = expense_tools(
    operation="create",
    amount=75.50,
    description="Team lunch",
    category="food",
    tags=["team", "reimbursable"]
)

# 2. Extract ID from result
expense_id = create_result.split("ID: ")[1].split(",")[0]

# 3. Update with receipt after uploading
expense_tools(
    operation="update",
    expense_id=expense_id,
    receipt_path="/receipts/team_lunch_20251026.jpg"
)

# 4. Search for similar expenses
expense_tools(
    operation="search",
    query="team lunch expenses",
    search_type="semantic",
    limit=5
)
```

### Monthly Expense Review

```python
# Get October 2025 summary
summary = expense_tools(
    operation="analytics",
    analytics_type="monthly_summary",
    year=2025,
    month=10
)

# Get breakdown by category
by_category = expense_tools(
    operation="analytics",
    analytics_type="total_by_category",
    date_from="2025-10-01",
    date_to="2025-10-31"
)

# List all October expenses
all_expenses = expense_tools(
    operation="list",
    date_from="2025-10-01",
    date_to="2025-10-31",
    limit=100
)
```

### Finding Reimbursable Expenses

```python
# Search by tag
reimbursable = expense_tools(
    operation="search",
    search_type="tags",
    tags=["reimbursable"],
    limit=50
)

# Get total for reimbursement period
total = expense_tools(
    operation="analytics",
    analytics_type="total_by_category",
    date_from="2025-10-01",
    date_to="2025-10-31"
)
```

### Budget Monitoring

```python
# Find large expenses this month
large_expenses = expense_tools(
    operation="search",
    search_type="amount_range",
    amount_min=500
)

# Get monthly food budget usage
food_total = expense_tools(
    operation="search",
    search_type="category",
    category="food",
    limit=100
)

# Check if over budget with monthly summary
monthly = expense_tools(
    operation="analytics",
    analytics_type="monthly_summary",
    year=2025,
    month=10
)
```

## Troubleshooting

### Expenses Not Appearing in Search

**Problem**: Created an expense but semantic search doesn't find it.

**Solution**:
- Check if embedding was generated (look for errors in logs)
- Verify Gemini API key is valid
- Try category or tag search to confirm expense exists

### Slow Vector Search

**Problem**: Semantic search takes too long.

**Solution**:
- Ensure HNSW index is created on `embedding` column
- Reduce `limit` parameter
- Use category or tag search for faster results when appropriate

### "Expense tools not configured" Error

**Problem**: Getting runtime error about configuration.

**Solution**:
```python
from src.infrastructure.llm.tools.expenses import configure_expense_tools

# Ensure this is called at startup
configure_expense_tools(session_factory, embedding_service)
```

### Currency Conversion Issues

**Problem**: Expenses in different currencies not summing correctly.

**Solution**:
- The system stores expenses in their original currency
- For multi-currency analytics, implement conversion at application level
- Track exchange rates separately if needed

## API Reference

### Operations

| Operation | Required Args | Optional Args | Returns |
|-----------|--------------|---------------|---------|
| `create` | `amount`, `description`, `category` | `currency`, `tags`, `expense_date`, `is_recurring`, `recurrence_pattern`, `receipt_path` | Success message with expense ID |
| `update` | `expense_id`, at least one field to update | `amount`, `currency`, `description`, `category`, `tags`, `expense_date`, `is_recurring`, `recurrence_pattern`, `receipt_path` | Success message |
| `delete` | `expense_id` | - | Success or not found message |
| `get` | `expense_id` | - | Expense JSON or not found message |
| `list` | - | `limit`, `offset`, `date_from`, `date_to` | Formatted list of expenses |
| `search` | Depends on `search_type` | `limit` | Formatted search results |
| `analytics` | `analytics_type` | `year`, `month`, `date_from`, `date_to`, `category` | Analytics results |

### Search Types

| Type | Required | Description |
|------|----------|-------------|
| `semantic` | `query` | Vector similarity search (finds related expenses by meaning) |
| `category` | `category` | Exact category match |
| `tags` | `tags` | Filter by tags (any match) |
| `amount_range` | `amount_min` or `amount_max` | Filter by amount range |

### Analytics Types

| Type | Required | Description |
|------|----------|-------------|
| `total_by_category` | - | Sum expenses grouped by category |
| `monthly_summary` | `year`, `month` | Complete month breakdown with totals and averages |

## Performance Tips

1. **Limit Results**: Always specify reasonable `limit` values
2. **Use Category/Tags**: Faster than semantic search for known categories
3. **Pagination**: Use `offset` for large result sets
4. **Specific Queries**: More specific semantic queries return better results
5. **Date Ranges**: Use date filtering to reduce search scope

## Security Notes

- All operations are scoped to the current user (set via `set_user_context`)
- Users cannot access other users' expenses
- Input validation prevents injection attacks
- API keys should never be logged or exposed
- Receipt paths should be validated before storage

## Example Use Cases

### Personal Finance Tracking
```python
# Daily expense logging
expense_tools(operation="create", amount=8.50, description="Morning coffee", category="food", tags=["coffee", "daily"])

# Weekly review
expense_tools(operation="analytics", analytics_type="total_by_category", date_from="2025-10-20", date_to="2025-10-26")
```

### Business Expense Management
```python
# Client meeting expense
expense_tools(operation="create", amount=450, description="Dinner with ABC Corp executives", category="business-meals", tags=["client", "reimbursable", "ABC-Corp"], receipt_path="/receipts/abc_dinner.pdf")

# Monthly report
expense_tools(operation="analytics", analytics_type="monthly_summary", year=2025, month=10)
```

### Budget Tracking
```python
# Set monthly review
expense_tools(operation="analytics", analytics_type="monthly_summary", year=2025, month=10)

# Check overspending categories
expense_tools(operation="analytics", analytics_type="total_by_category", date_from="2025-10-01", date_to="2025-10-31")
```
