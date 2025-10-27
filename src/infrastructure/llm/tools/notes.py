"""Note-taking tools for LLM agent with 3-layer architecture.

This module implements a note-taking system with:
- Layer 1: Agent interface (note_tools)
- Layer 2: Validation
- Layer 3: Operation handlers

The architecture provides clear separation of concerns and plain English error messages.

Async Support:
- Internal handlers are fully async (_create_note, _update_note, etc.)
- Main note_tools() function is synchronous (required for DSPy compatibility)
- Handles async operations internally using ThreadPoolExecutor for isolation
- When used with dspy.Tool wrapper, supports async execution via acall()
- Example: tool = dspy.Tool(note_tools); await tool.acall(operation="create", title="...", content="...")
"""

import json
import logging
from datetime import datetime
from typing import Any, Literal

from src.application.interfaces.embedding_service import IEmbeddingService
from src.application.use_cases.notes.create_note import CreateNoteUseCase
from src.application.use_cases.notes.delete_note import DeleteNoteUseCase
from src.application.use_cases.notes.get_note import GetNoteUseCase
from src.application.use_cases.notes.list_notes import ListNotesUseCase
from src.application.use_cases.notes.search_notes import SearchNotesUseCase
from src.application.use_cases.notes.update_note import UpdateNoteUseCase
from src.domain.repositories.note_repository import INoteRepository

logger = logging.getLogger(__name__)

# Global dependencies (will be injected via dependency injection)
_session_factory: Any | None = None  # async_sessionmaker[AsyncSession]
_embedding_service: IEmbeddingService | None = None
_current_user_id: str = "default-user"  # Will be set by context


def configure_note_tools(
    session_factory: Any,  # async_sessionmaker[AsyncSession]
    embedding_service: IEmbeddingService,
) -> None:
    """Configure note tools with dependencies.

    Args:
        session_factory: Async session factory for creating database sessions
        embedding_service: Embedding service implementation
    """
    global _session_factory, _embedding_service
    _session_factory = session_factory
    _embedding_service = embedding_service
    logger.info("Note tools configured with session factory")


def set_user_context(user_id: str) -> None:
    """Set the current user context for note operations.

    Args:
        user_id: User ID to use for note operations
    """
    global _current_user_id
    _current_user_id = user_id


# ========== Layer 2: Validation ==========


def validate_operation(operation: str, **kwargs: Any) -> str | None:
    """Validate operation and arguments.

    Returns None if valid, or plain English error message if invalid.

    Args:
        operation: Operation name
        **kwargs: Operation arguments

    Returns:
        Error message if invalid, None if valid
    """
    validators = {
        "create": _validate_create,
        "update": _validate_update,
        "edit": _validate_update,  # alias
        "delete": _validate_delete,
        "get": _validate_get,
        "list": _validate_list,
        "search": _validate_search,
    }

    if operation not in validators:
        valid_ops = ", ".join(validators.keys())
        return f"Error: Unknown operation '{operation}'. Valid operations are: {valid_ops}."

    return validators[operation](**kwargs)


def _validate_create(
    title: str | None = None,
    content: str | None = None,
    tags: list[str] | None = None,
    **extra: Any,
) -> str | None:
    """Validate create operation arguments."""
    if title is None:
        return "Error: 'title' is required for creating a note. Please provide a title."
    if not isinstance(title, str) or not title.strip():
        return "Error: 'title' must be a non-empty string."
    if len(title) > 255:
        return "Error: 'title' cannot exceed 255 characters. Please shorten your title."

    if content is None:
        return "Error: 'content' is required for creating a note. Please provide content."
    if not isinstance(content, str) or not content.strip():
        return "Error: 'content' must be a non-empty string."

    if tags is not None:
        if not isinstance(tags, list):
            return "Error: 'tags' must be a list of strings, e.g., ['work', 'meeting']."
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                return "Error: All tags must be non-empty strings."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}. Valid params for 'create': title, content, tags."

    return None


def _validate_update(
    note_id: str | None = None,
    title: str | None = None,
    content: str | None = None,
    tags: list[str] | None = None,
    **extra: Any,
) -> str | None:
    """Validate update operation arguments."""
    if note_id is None:
        return "Error: 'note_id' is required for updating a note. Please provide the note ID."
    if not isinstance(note_id, str) or not note_id.strip():
        return f"Error: 'note_id' must be a non-empty string, not {type(note_id).__name__}. Please provide note_id as a string."

    # Check that at least one field to update is provided
    if title is None and content is None and tags is None:
        return "Error: At least one field must be provided to update: title, content, or tags."

    # Validate individual fields if provided
    if title is not None:
        if not isinstance(title, str) or not title.strip():
            return "Error: 'title' must be a non-empty string."
        if len(title) > 255:
            return "Error: 'title' cannot exceed 255 characters."

    if content is not None:
        if not isinstance(content, str) or not content.strip():
            return "Error: 'content' must be a non-empty string."

    if tags is not None:
        if not isinstance(tags, list):
            return "Error: 'tags' must be a list of strings."
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                return "Error: All tags must be non-empty strings."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}. Valid params for 'update': note_id, title, content, tags."

    return None


def _validate_delete(note_id: str | None = None, **extra: Any) -> str | None:
    """Validate delete operation arguments."""
    if note_id is None:
        return "Error: 'note_id' is required for deleting a note. Please provide the note ID."
    if not isinstance(note_id, str) or not note_id.strip():
        return f"Error: 'note_id' must be a non-empty string, not {type(note_id).__name__}."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}. Valid params for 'delete': note_id."

    return None


def _validate_get(note_id: str | None = None, **extra: Any) -> str | None:
    """Validate get operation arguments."""
    if note_id is None:
        return "Error: 'note_id' is required for retrieving a note. Please provide the note ID."
    if not isinstance(note_id, str) or not note_id.strip():
        return f"Error: 'note_id' must be a non-empty string, not {type(note_id).__name__}."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}. Valid params for 'get': note_id."

    return None


def _validate_list(
    limit: int | None = None,
    offset: int | None = None,
    **extra: Any,
) -> str | None:
    """Validate list operation arguments."""
    if limit is not None:
        if not isinstance(limit, int):
            return f"Error: 'limit' must be an integer, not {type(limit).__name__}."
        if limit <= 0:
            return "Error: 'limit' must be a positive number."

    if offset is not None:
        if not isinstance(offset, int):
            return f"Error: 'offset' must be an integer, not {type(offset).__name__}."
        if offset < 0:
            return "Error: 'offset' cannot be negative."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}. Valid params for 'list': limit, offset."

    return None


def _validate_search(
    query: str | None = None,
    search_type: str | None = None,
    tags: list[str] | None = None,
    limit: int | None = None,
    **extra: Any,
) -> str | None:
    """Validate search operation arguments."""
    search_type = search_type or "semantic"

    valid_types = ["semantic", "keyword", "tag", "date"]
    if search_type not in valid_types:
        return f"Error: Invalid search_type '{search_type}'. Valid types are: {', '.join(valid_types)}."

    # For semantic and keyword search, query is required
    if search_type in ["semantic", "keyword"]:
        if query is None or not query.strip():
            return f"Error: 'query' is required for {search_type} search. Please provide a search query."

    # For tag search, tags are required
    if search_type == "tag":
        if not tags:
            return "Error: 'tags' parameter is required for tag search. Please provide a list of tags."
        if not isinstance(tags, list):
            return "Error: 'tags' must be a list of strings."

    if limit is not None:
        if not isinstance(limit, int) or limit <= 0:
            return "Error: 'limit' must be a positive integer."

    return None


# ========== Layer 3: Operation Handlers ==========


async def _create_note(
    user_id: str,
    title: str,
    content: str,
    tags: list[str] | None = None,
) -> str:
    """Create a new note.

    Args:
        user_id: User ID who owns the note
        title: Note title
        content: Note content
        tags: Optional tags

    Returns:
        Success message with note ID
    """
    if _session_factory is None or _embedding_service is None:
        raise RuntimeError("Note tools not configured")

    # Import here to avoid circular dependency
    from src.infrastructure.database.repositories.note_repository import NoteRepository

    # Create a new session for this operation
    session = _session_factory()
    try:
        repository = NoteRepository(session)
        use_case = CreateNoteUseCase(repository, _embedding_service)
        note = await use_case.execute(user_id, title, content, tags)
        await session.commit()
        return f"Note created successfully. ID: {note.id}, Title: '{note.title}'"
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def _update_note(
    user_id: str,
    note_id: str,
    title: str | None = None,
    content: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Update an existing note.

    Args:
        user_id: User ID who owns the note
        note_id: Note ID to update
        title: New title (optional)
        content: New content (optional)
        tags: New tags (optional)

    Returns:
        Success message
    """
    if _session_factory is None or _embedding_service is None:
        raise RuntimeError("Note tools not configured")

    from src.infrastructure.database.repositories.note_repository import NoteRepository

    session = _session_factory()
    try:
        repository = NoteRepository(session)
        use_case = UpdateNoteUseCase(repository, _embedding_service)
        note = await use_case.execute(user_id, note_id, title, content, tags)
        await session.commit()
        return f"Note updated successfully. ID: {note.id}, Title: '{note.title}'"
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def _delete_note(user_id: str, note_id: str) -> str:
    """Delete a note.

    Args:
        user_id: User ID who owns the note
        note_id: Note ID to delete

    Returns:
        Success or not found message
    """
    if _session_factory is None:
        raise RuntimeError("Note tools not configured")

    from src.infrastructure.database.repositories.note_repository import NoteRepository

    session = _session_factory()
    try:
        repository = NoteRepository(session)
        use_case = DeleteNoteUseCase(repository)
        deleted = await use_case.execute(user_id, note_id)
        await session.commit()

        if deleted:
            return f"Note deleted successfully. ID: {note_id}"
        else:
            return f"Note not found. ID: {note_id}"
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def _get_note(user_id: str, note_id: str) -> str:
    """Get a single note.

    Args:
        user_id: User ID who owns the note
        note_id: Note ID to retrieve

    Returns:
        Note details as formatted string
    """
    if _session_factory is None:
        raise RuntimeError("Note tools not configured")

    from src.infrastructure.database.repositories.note_repository import NoteRepository

    session = _session_factory()
    try:
        repository = NoteRepository(session)
        use_case = GetNoteUseCase(repository)
        note = await use_case.execute(user_id, note_id)

        if note is None:
            return f"Note not found. ID: {note_id}"

        return json.dumps(
            {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "tags": list(note.tags),
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
            },
            indent=2,
        )
    finally:
        await session.close()


async def _list_notes(user_id: str, limit: int = 10, offset: int = 0) -> str:
    """List user's notes.

    Args:
        user_id: User ID who owns the notes
        limit: Maximum number to return
        offset: Number to skip

    Returns:
        List of notes as formatted string
    """
    if _session_factory is None:
        raise RuntimeError("Note tools not configured")

    from src.infrastructure.database.repositories.note_repository import NoteRepository

    session = _session_factory()
    try:
        repository = NoteRepository(session)
        use_case = ListNotesUseCase(repository)
        notes = await use_case.execute(user_id, limit, offset)

        if not notes:
            return "No notes found."

        result = f"Found {len(notes)} note(s):\n\n"
        for i, note in enumerate(notes, 1):
            result += f"{i}. [{note.id}] {note.title}\n"
            result += f"   Tags: {', '.join(note.tags) if note.tags else 'none'}\n"
            result += f"   Updated: {note.updated_at.isoformat()}\n\n"

        return result
    finally:
        await session.close()


async def _search_notes(
    user_id: str,
    query: str | None = None,
    search_type: Literal["semantic", "keyword", "tag", "date"] = "semantic",
    tags: list[str] | None = None,
    limit: int = 5,
) -> str:
    """Search notes.

    Args:
        user_id: User ID who owns the notes
        query: Search query
        search_type: Type of search
        tags: Tags to filter by
        limit: Maximum results

    Returns:
        Search results as formatted string
    """
    if _session_factory is None or _embedding_service is None:
        raise RuntimeError("Note tools not configured")

    from src.infrastructure.database.repositories.note_repository import NoteRepository

    session = _session_factory()
    try:
        repository = NoteRepository(session)
        use_case = SearchNotesUseCase(repository, _embedding_service)
        notes = await use_case.execute(
            user_id=user_id,
            query=query,
            search_type=search_type,
            tags=tags,
            limit=limit,
        )

        if not notes:
            return f"No notes found matching your {search_type} search."

        result = f"Found {len(notes)} note(s) for {search_type} search:\n\n"
        for i, note in enumerate(notes, 1):
            result += f"{i}. [{note.id}] {note.title}\n"
            result += f"   Preview: {note.content[:100]}...\n"
            result += f"   Tags: {', '.join(note.tags) if note.tags else 'none'}\n\n"

        return result
    finally:
        await session.close()


# ========== Layer 1: Agent Interface ==========


def note_tools(operation: str, **kwargs: Any) -> str:
    """Universal note-taking tool for LLM agent.

    This is the single entry point for all note operations. It validates
    inputs and routes to appropriate operation handlers.

    Operations:
    - create: Create a new note (title, content, tags)
    - update/edit: Update existing note (note_id, title?, content?, tags?)
    - delete: Delete a note (note_id)
    - get: Get a single note (note_id)
    - list: List notes (limit?, offset?)
    - search: Search notes (query?, search_type?, tags?, limit?)

    Args:
        operation: Operation to perform
        **kwargs: Operation-specific arguments

    Returns:
        Operation result or error message (plain English)

    Examples:
        >>> note_tools(operation="create", title="Meeting Notes", content="Discussed Q4 goals")
        "Note created successfully. ID: abc-123, Title: 'Meeting Notes'"

        >>> note_tools(operation="search", query="roadmap", search_type="semantic", limit=3)
        "Found 3 note(s) for semantic search:..."

        >>> note_tools(operation="update", note_id=123, title="New Title")
        "Error: 'note_id' must be a non-empty string, not int. Please provide note_id as a string."
    """
    logger.info("note_tools called with operation=%s, kwargs=%s", operation, kwargs)

    # Step 1: Validate
    validation_error = validate_operation(operation, **kwargs)
    if validation_error:
        logger.warning("Validation failed: %s", validation_error)
        return validation_error

    # Step 2: Execute operation
    try:
        user_id = _current_user_id

        # Route to appropriate handler
        # Note: These are async functions, but DSPy tools must be synchronous
        # We need to handle both regular and already-running event loops
        import asyncio

        async def _execute() -> str:
            """Execute the async operation."""
            if operation == "create":
                return await _create_note(
                    user_id, kwargs["title"], kwargs["content"], kwargs.get("tags")
                )
            elif operation in ["update", "edit"]:
                return await _update_note(
                    user_id,
                    kwargs["note_id"],
                    kwargs.get("title"),
                    kwargs.get("content"),
                    kwargs.get("tags"),
                )
            elif operation == "delete":
                return await _delete_note(user_id, kwargs["note_id"])
            elif operation == "get":
                return await _get_note(user_id, kwargs["note_id"])
            elif operation == "list":
                return await _list_notes(user_id, kwargs.get("limit", 10), kwargs.get("offset", 0))
            elif operation == "search":
                return await _search_notes(
                    user_id,
                    kwargs.get("query"),
                    kwargs.get("search_type", "semantic"),
                    kwargs.get("tags"),
                    kwargs.get("limit", 5),
                )
            else:
                return f"Error: Operation '{operation}' not implemented."

        # Run async code from sync context
        # DSPy tools must be synchronous, but our operations are async
        # Solution: Create new event loop in separate thread
        # Note: ThreadPoolExecutor ensures database sessions are isolated per operation
        import asyncio
        import concurrent.futures

        # Check if event loop is running
        try:
            asyncio.get_running_loop()
            # Event loop exists - use ThreadPoolExecutor with new loop
            def _run_in_thread():
                """Execute async code in isolated thread with fresh event loop."""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(_execute())
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(None)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = executor.submit(_run_in_thread).result()
        except RuntimeError:
            # No event loop - safe to use asyncio.run()
            result = asyncio.run(_execute())

        logger.info("Operation %s completed successfully", operation)
        return result

    except Exception as e:
        error_msg = f"Error executing {operation}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg
