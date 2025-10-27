# Note-Taking System Architecture

**Date**: 2025-10-25
**Author**: Xavier Au
**Status**: Implemented

## Overview

This document describes the architecture of the note-taking system for LLM agents. The system enables agents to create, manage, and search notes with vector-based semantic search capabilities.

## Design Principles

1. **Clean Architecture**: Clear separation between domain, application, and infrastructure layers
2. **SOLID Principles**: Each component has a single responsibility and depends on abstractions
3. **3-Layer Tool Design**: Agent interface → Validation → Operation handlers
4. **Plain English Errors**: Agent-friendly validation messages for better UX
5. **Type Safety**: Full type hints and Pydantic validation throughout

## System Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Agent (DSPy)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Layer 1: Agent Interface                        │
│         note_tools(operation, **kwargs) → str                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Layer 2: Validation                             │
│         validate_operation(operation, **kwargs)              │
│         Returns: None (valid) or error message (invalid)     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Layer 3: Operation Handlers                     │
│    _create_note, _update_note, _delete_note                 │
│    _get_note, _list_notes, _search_notes                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Application Layer (Use Cases)                   │
│    CreateNoteUseCase, UpdateNoteUseCase, etc.               │
└─────────┬─────────────────────────────────┬─────────────────┘
          │                                 │
          ▼                                 ▼
┌──────────────────┐              ┌──────────────────────┐
│  INoteRepository │              │ IEmbeddingService    │
└─────────┬────────┘              └──────────┬───────────┘
          │                                  │
          ▼                                  ▼
┌──────────────────┐              ┌──────────────────────┐
│  NoteRepository  │              │ GeminiEmbedding      │
│  (PostgreSQL +   │              │ Service              │
│   pgvector)      │              │                      │
└──────────────────┘              └──────────────────────┘
```

## Component Details

### Domain Layer

**Location**: `src/domain/`

#### Note Entity (`entities/note.py`)
- **Responsibility**: Core business entity representing a note
- **Key Features**:
  - Immutable (frozen dataclass)
  - Self-validating with clear error messages
  - Supports 1536-dimensional embeddings (Gemini)
  - Factory method for creation with auto-generated UUIDs

**Validation Rules**:
- Title: Non-empty, max 255 characters
- Content: Non-empty
- Tags: Array of non-empty strings
- Embedding: Exactly 1536 dimensions (if provided)

#### Repository Protocol (`repositories/note_repository.py`)
- **Responsibility**: Define contract for data access
- **Methods**:
  - CRUD: `create`, `get_by_id`, `update`, `delete`
  - Listing: `list_by_user` (with pagination)
  - Search: `search_by_vector`, `search_by_keyword`, `search_by_tags`, `search_by_date_range`
  - Analytics: `count_by_user`

### Application Layer

**Location**: `src/application/`

#### Embedding Service Protocol (`interfaces/embedding_service.py`)
- **Responsibility**: Abstract embedding generation
- **Methods**:
  - `generate_embedding(text)` → list[float]
  - `generate_embeddings(texts)` → list[list[float]]
  - `get_dimension()` → int
  - `get_model_name()` → str

#### Use Cases (`use_cases/notes/`)

Each use case follows Single Responsibility Principle:

1. **CreateNoteUseCase**
   - Generates embedding from title + content
   - Creates note with embedding
   - Persists to repository

2. **UpdateNoteUseCase**
   - Retrieves existing note
   - Regenerates embedding if title/content changed
   - Updates and persists

3. **DeleteNoteUseCase**
   - Deletes note by ID (scoped to user)

4. **GetNoteUseCase**
   - Retrieves single note by ID

5. **ListNotesUseCase**
   - Lists notes with pagination
   - Ordered by updated_at DESC

6. **SearchNotesUseCase**
   - Supports 4 search types:
     - `semantic`: Vector similarity search
     - `keyword`: Full-text search in title/content
     - `tag`: Tag-based filtering
     - `date`: Date range filtering

### Infrastructure Layer

**Location**: `src/infrastructure/`

#### Database

**NoteModel** (`database/models/note_model.py`)
- SQLAlchemy model with pgvector support
- Uses UUID primary keys
- PostgreSQL array type for tags
- Vector(1536) type for embeddings

**NoteRepository** (`database/repositories/note_repository.py`)
- Implements INoteRepository protocol
- Uses AsyncSession for non-blocking I/O
- Vector search uses cosine similarity
- Keyword search uses PostgreSQL ILIKE
- Tag search uses array operators (contains/overlap)

**Indexes**:
- `idx_notes_user_id`: User lookup
- `idx_notes_user_updated`: Pagination
- `idx_notes_tags`: Tag search (GIN index)
- `idx_notes_embedding`: Vector search (HNSW index)

#### Embedding Service

**GeminiEmbeddingService** (`llm/embedding/gemini_embedding_service.py`)
- Uses `gemini-embedding-001` model (1536 dimensions)
- Supports single and batch embedding generation
- Task type: `retrieval_document` for semantic search

#### Tools (3-Layer Architecture)

**Location**: `infrastructure/llm/tools/notes.py`

**Layer 1: Agent Interface**
```python
def note_tools(operation: str, **kwargs) -> str
```
- Single entry point for all note operations
- Operations: `create`, `update`, `edit`, `delete`, `get`, `list`, `search`
- Returns formatted strings (success messages or error messages)

**Layer 2: Validation**
```python
def validate_operation(operation: str, **kwargs) -> str | None
```
- Validates operation name and parameters
- Returns `None` if valid, plain English error if invalid
- Individual validators for each operation:
  - `_validate_create`: Requires title, content
  - `_validate_update`: Requires note_id + at least one field
  - `_validate_delete`: Requires note_id
  - `_validate_get`: Requires note_id
  - `_validate_list`: Validates limit/offset
  - `_validate_search`: Validates search_type and required params

**Error Message Examples**:
```
"Error: 'title' is required for creating a note. Please provide a title."
"Error: 'note_id' must be a non-empty string, not int. Please provide note_id as a string."
"Error: Unknown operation 'invalid_op'. Valid operations are: create, update, delete, get, list, search."
```

**Layer 3: Operation Handlers**
- `_create_note`: Creates note with embedding
- `_update_note`: Updates note and re-embeds if needed
- `_delete_note`: Deletes note
- `_get_note`: Returns note as JSON
- `_list_notes`: Returns formatted list
- `_search_notes`: Performs multi-strategy search

## Data Flow

### Creating a Note

```
1. Agent calls: note_tools(operation="create", title="...", content="...", tags=[...])
2. Layer 1 routes to validation
3. Layer 2 validates:
   - title is non-empty string
   - content is non-empty string
   - tags is list of strings (if provided)
4. Layer 3 (_create_note) executes:
   - Calls CreateNoteUseCase
   - Use case generates embedding (title + content)
   - Use case creates Note entity
   - Repository persists to PostgreSQL
5. Returns: "Note created successfully. ID: abc-123, Title: 'My Note'"
```

### Semantic Search

```
1. Agent calls: note_tools(operation="search", query="what did we discuss?", search_type="semantic")
2. Layer 1 routes to validation
3. Layer 2 validates query is non-empty
4. Layer 3 (_search_notes) executes:
   - Calls SearchNotesUseCase
   - Use case generates query embedding
   - Repository performs vector similarity search
   - Returns notes with similarity > 0.7
5. Returns formatted list with note previews
```

## Database Schema

```sql
CREATE TABLE notes (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_notes_user_id ON notes(user_id);
CREATE INDEX idx_notes_user_updated ON notes(user_id, updated_at DESC);
CREATE INDEX idx_notes_tags ON notes USING gin(tags);
CREATE INDEX idx_notes_embedding ON notes USING hnsw (embedding vector_cosine_ops);
```

## Configuration

**Settings** (`config/settings.py`):
```python
pgvector_dimension: int = 1536  # Gemini embedding dimension
embedding_model: str = "gemini-embedding-001"
```

**Environment Variables**:
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/whatsapp_chatbot
GEMINI_API_KEY=your_gemini_api_key
EMBEDDING_MODEL=gemini-embedding-001
```

## Dependencies

```python
dependencies = [
    "dspy-ai>=2.5.0",              # Agent framework
    "google-generativeai>=0.8.0",  # Gemini API
    "sqlalchemy>=2.0.36",          # ORM
    "asyncpg>=0.30.0",             # Async PostgreSQL
    "pgvector>=0.3.6",             # Vector extension
]
```

## Integration with ConversationAgent

The `note_tools` function is added to the DSPy ReAct agent's tool list:

```python
tools = [
    compute,     # Math/calculations
    jot,         # Working memory
    note_tools,  # Note-taking
]

self._generator = dspy.ReAct(ConversationSignature, tools=tools)
```

## Security Considerations

1. **User Scoping**: All operations are scoped to `user_id` to prevent cross-user access
2. **Input Validation**: All inputs validated before processing
3. **SQL Injection**: Prevented by SQLAlchemy ORM and parameterized queries
4. **Secrets**: API keys stored in environment variables, never in code

## Performance Optimization

1. **Vector Index**: HNSW index for fast similarity search
2. **Tag Index**: GIN index for efficient array operations
3. **Pagination**: Limit/offset support for large result sets
4. **Async I/O**: Non-blocking database operations
5. **Batch Embeddings**: Support for batch embedding generation

## Future Enhancements

1. **Full-Text Search**: PostgreSQL `tsvector` for better keyword search
2. **Note Sharing**: Support for shared notes between users
3. **Attachments**: Support for file attachments
4. **Folders**: Hierarchical organization
5. **Note Templates**: Pre-defined note structures
6. **Export**: Export notes to various formats (PDF, Markdown, etc.)

## Testing Strategy

1. **Unit Tests**: All domain entities, use cases, validators
2. **Integration Tests**: Repository with test database
3. **E2E Tests**: Full flow from agent to database
4. **Mock Tests**: Use cases with mocked dependencies

## Monitoring & Observability

- Logging at all layers (debug, info, error levels)
- Use Langfuse for LLM observability
- Track embedding generation costs
- Monitor vector search performance

## Maintenance

- Regular index maintenance for vector search
- Monitor database size growth
- Review and optimize slow queries
- Keep embedding model up-to-date with Gemini releases
