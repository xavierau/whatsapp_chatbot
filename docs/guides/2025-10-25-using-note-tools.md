# Using the Note-Taking System

**Date**: 2025-10-25
**Audience**: Developers and AI Agents
**Status**: Active

## Quick Start

The note-taking system provides a comprehensive tool for LLM agents to create, manage, and search notes with semantic (vector-based) search capabilities.

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

Apply the notes table migration:

```bash
# Connect to your database
psql $DATABASE_URL

# Run the migration
\i src/infrastructure/database/migrations/001_create_notes_table.sql
```

### 3. Configure Environment

Set up your environment variables in `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/whatsapp_chatbot
GEMINI_API_KEY=your_gemini_api_key_here
EMBEDDING_MODEL=gemini-embedding-001
PGVECTOR_DIMENSION=1536
```

### 4. Initialize Dependencies

The note tools require two dependencies to be configured:

```python
from src.infrastructure.database.repositories.note_repository import NoteRepository
from src.infrastructure.llm.embedding.gemini_embedding_service import GeminiEmbeddingService
from src.infrastructure.llm.tools.notes import configure_note_tools, set_user_context
from src.config.settings import settings

# Initialize embedding service
embedding_service = GeminiEmbeddingService(
    api_key=settings.gemini_api_key,
    model_name=settings.embedding_model
)

# Initialize repository (with your database session)
repository = NoteRepository(session=your_async_session)

# Configure note tools
configure_note_tools(
    repository=repository,
    embedding_service=embedding_service
)

# Set user context (per conversation)
set_user_context(user_id="whatsapp_user_123")
```

## Agent Usage

The agent uses a single function `note_tools(operation, **kwargs)` for all note operations.

### Creating Notes

```python
# Basic note creation
result = note_tools(
    operation="create",
    title="Meeting Notes",
    content="Discussed Q4 roadmap and priorities. Focus on customer retention.",
    tags=["work", "meeting", "q4"]
)
# Returns: "Note created successfully. ID: abc-123, Title: 'Meeting Notes'"

# Without tags
result = note_tools(
    operation="create",
    title="Shopping List",
    content="Milk, eggs, bread, coffee"
)
```

**Validation Examples**:
```python
# Missing title - gets helpful error
result = note_tools(operation="create", content="Some content")
# Returns: "Error: 'title' is required for creating a note. Please provide a title."

# Empty content - gets helpful error
result = note_tools(operation="create", title="Title", content="   ")
# Returns: "Error: 'content' must be a non-empty string."
```

### Updating Notes

```python
# Update title and content
result = note_tools(
    operation="update",
    note_id="abc-123",
    title="Updated Meeting Notes",
    content="Discussed Q4 roadmap, priorities, and timeline. Focus on customer retention and new features."
)

# Update only tags
result = note_tools(
    operation="update",
    note_id="abc-123",
    tags=["work", "meeting", "q4", "important"]
)

# Update content only (will regenerate embedding)
result = note_tools(
    operation="update",
    note_id="abc-123",
    content="Updated content with more details..."
)
```

**Validation Examples**:
```python
# Wrong type for note_id
result = note_tools(operation="update", note_id=123, title="New")
# Returns: "Error: 'note_id' must be a non-empty string, not int. Please provide note_id as a string."

# No fields to update
result = note_tools(operation="update", note_id="abc-123")
# Returns: "Error: At least one field must be provided to update: title, content, or tags."
```

### Getting a Single Note

```python
result = note_tools(operation="get", note_id="abc-123")
# Returns JSON:
# {
#   "id": "abc-123",
#   "title": "Meeting Notes",
#   "content": "Discussed Q4 roadmap...",
#   "tags": ["work", "meeting", "q4"],
#   "created_at": "2025-10-25T10:30:00Z",
#   "updated_at": "2025-10-25T11:00:00Z"
# }

# Note not found
result = note_tools(operation="get", note_id="invalid-id")
# Returns: "Note not found. ID: invalid-id"
```

### Listing Notes

```python
# List first 10 notes (default)
result = note_tools(operation="list")

# List with pagination
result = note_tools(operation="list", limit=20, offset=10)

# Returns formatted list:
# Found 15 note(s):
#
# 1. [abc-123] Meeting Notes
#    Tags: work, meeting, q4
#    Updated: 2025-10-25T11:00:00Z
#
# 2. [def-456] Shopping List
#    Tags: personal
#    Updated: 2025-10-24T15:30:00Z
# ...
```

### Searching Notes

#### Semantic Search (Vector-Based)

Best for finding notes by meaning, not exact keywords:

```python
# Find notes related to "roadmap" (finds "priorities", "planning", etc.)
result = note_tools(
    operation="search",
    query="what did we discuss about the product roadmap?",
    search_type="semantic",
    limit=5
)

# Find notes about a concept
result = note_tools(
    operation="search",
    query="customer retention strategies",
    search_type="semantic"
)
```

#### Keyword Search

Exact text matching in title and content:

```python
result = note_tools(
    operation="search",
    query="Q4",
    search_type="keyword",
    limit=10
)

# Case-insensitive search
result = note_tools(
    operation="search",
    query="customer",
    search_type="keyword"
)
```

#### Tag-Based Search

Filter by tags:

```python
# Find notes with any of these tags
result = note_tools(
    operation="search",
    search_type="tag",
    tags=["work", "meeting"]
)

# Implementation note: match_all parameter not exposed in current version
# Future: Support requiring all tags vs. any tag
```

#### Date-Based Search

Filter by creation date:

```python
# Implementation note: Date search requires datetime objects
# Future enhancement: Accept ISO date strings from agent
```

### Deleting Notes

```python
result = note_tools(operation="delete", note_id="abc-123")
# Returns: "Note deleted successfully. ID: abc-123"

# Note not found
result = note_tools(operation="delete", note_id="invalid-id")
# Returns: "Note not found. ID: invalid-id"
```

## Error Handling

All errors are returned as plain English strings to help the agent understand what went wrong:

### Common Errors

**Invalid Operation**:
```python
result = note_tools(operation="invalid_op")
# "Error: Unknown operation 'invalid_op'. Valid operations are: create, update, delete, get, list, search."
```

**Type Errors**:
```python
result = note_tools(operation="create", title=123, content="text")
# "Error: 'title' must be a non-empty string."

result = note_tools(operation="list", limit="ten")
# "Error: 'limit' must be an integer, not str."
```

**Missing Required Fields**:
```python
result = note_tools(operation="search", search_type="semantic")
# "Error: 'query' is required for semantic search. Please provide a search query."

result = note_tools(operation="search", search_type="tag")
# "Error: 'tags' parameter is required for tag search. Please provide a list of tags."
```

**Invalid Values**:
```python
result = note_tools(operation="list", limit=-5)
# "Error: 'limit' must be a positive number."

result = note_tools(operation="list", offset=-1)
# "Error: 'offset' cannot be negative."
```

## Best Practices

### 1. Use Descriptive Titles

```python
# Good
note_tools(operation="create", title="Q4 Planning Meeting - Oct 25", content="...")

# Avoid
note_tools(operation="create", title="Notes", content="...")
```

### 2. Add Relevant Tags

```python
# Good - specific, categorized
note_tools(operation="create", title="...", content="...", tags=["work", "project-alpha", "urgent"])

# Avoid - too generic
note_tools(operation="create", title="...", content="...", tags=["stuff"])
```

### 3. Choose the Right Search Type

- **Semantic**: Finding concepts, ideas, related topics
  ```python
  # Good for: "Find notes about customer feedback"
  note_tools(operation="search", query="customer feedback", search_type="semantic")
  ```

- **Keyword**: Finding exact mentions
  ```python
  # Good for: "Find notes containing 'Project Alpha'"
  note_tools(operation="search", query="Project Alpha", search_type="keyword")
  ```

- **Tag**: Filtering by category
  ```python
  # Good for: "Find all work-related notes"
  note_tools(operation="search", search_type="tag", tags=["work"])
  ```

### 4. Update vs. Create

Always check if a note exists before creating:

```python
# Good pattern
result = note_tools(operation="get", note_id="abc-123")
if "Note not found" in result:
    # Create new
    note_tools(operation="create", ...)
else:
    # Update existing
    note_tools(operation="update", note_id="abc-123", ...)
```

### 5. Handle Errors Gracefully

```python
result = note_tools(operation="create", title="Test", content="Test")

if result.startswith("Error:"):
    # Parse error and retry or ask user for clarification
    print(f"Failed to create note: {result}")
else:
    # Extract note ID from success message
    # "Note created successfully. ID: abc-123, Title: 'Test'"
    note_id = result.split("ID: ")[1].split(",")[0]
```

## Advanced Usage

### Multi-Step Workflows

```python
# 1. Create a note
create_result = note_tools(
    operation="create",
    title="Research Notes",
    content="Initial findings...",
    tags=["research"]
)

# 2. Extract ID from result
note_id = create_result.split("ID: ")[1].split(",")[0]

# 3. Update with more info
note_tools(
    operation="update",
    note_id=note_id,
    content="Initial findings... Additional research shows..."
)

# 4. Search for related notes
note_tools(
    operation="search",
    query="research findings",
    search_type="semantic"
)
```

### Batch Operations

```python
# Create multiple notes
notes = [
    {"title": "Note 1", "content": "Content 1", "tags": ["tag1"]},
    {"title": "Note 2", "content": "Content 2", "tags": ["tag2"]},
]

for note_data in notes:
    result = note_tools(operation="create", **note_data)
    print(result)
```

## Troubleshooting

### Notes Not Appearing in Search

**Problem**: Created a note but semantic search doesn't find it.

**Solution**:
- Check if embedding was generated (look for errors in logs)
- Verify Gemini API key is valid
- Try keyword search to confirm note exists

### Slow Vector Search

**Problem**: Semantic search takes too long.

**Solution**:
- Ensure HNSW index is created on `embedding` column
- Reduce `limit` parameter
- Increase `similarity_threshold` to filter more aggressively

### "Note tools not configured" Error

**Problem**: Getting runtime error about configuration.

**Solution**:
```python
from src.infrastructure.llm.tools.notes import configure_note_tools

# Ensure this is called at startup
configure_note_tools(repository, embedding_service)
```

## API Reference

### Operations

| Operation | Required Args | Optional Args | Returns |
|-----------|--------------|---------------|---------|
| `create` | `title`, `content` | `tags` | Success message with note ID |
| `update` | `note_id`, at least one of: `title`, `content`, `tags` | - | Success message |
| `delete` | `note_id` | - | Success or not found message |
| `get` | `note_id` | - | Note JSON or not found message |
| `list` | - | `limit`, `offset` | Formatted list of notes |
| `search` | Depends on `search_type` | `limit` | Formatted search results |

### Search Types

| Type | Required | Description |
|------|----------|-------------|
| `semantic` | `query` | Vector similarity search (finds related concepts) |
| `keyword` | `query` | Text matching in title/content |
| `tag` | `tags` | Filter by tags |
| `date` | `date_from` or `date_to` | Filter by creation date |

## Performance Tips

1. **Limit Results**: Always specify reasonable `limit` values
2. **Use Tags**: Tag organization is faster than full search
3. **Pagination**: Use `offset` for large result sets
4. **Specific Queries**: More specific semantic queries return better results

## Security Notes

- All operations are scoped to the current user (set via `set_user_context`)
- Users cannot access other users' notes
- Input validation prevents injection attacks
- API keys should never be logged or exposed
