"""Note repository protocol defining data access contract.

This module defines the interface for note persistence following
the Repository pattern and Dependency Inversion Principle.
"""

from datetime import datetime
from typing import Protocol

from src.domain.entities.note import Note


class INoteRepository(Protocol):
    """Protocol defining the contract for note data access.

    This protocol follows the Repository pattern, abstracting data access
    logic from business logic. Implementations can use different storage
    backends (PostgreSQL, SQLite, in-memory, etc.) as long as they
    implement this interface.

    All methods are async to support non-blocking I/O operations.
    """

    async def create(self, note: Note) -> Note:
        """Persist a new note to the repository.

        Args:
            note: Note entity to persist

        Returns:
            The persisted Note entity

        Raises:
            ValueError: If note with same ID already exists
            RuntimeError: If persistence fails
        """
        ...

    async def get_by_id(self, user_id: str, note_id: str) -> Note | None:
        """Retrieve a note by its ID, scoped to the user.

        Args:
            user_id: User ID who owns the note
            note_id: Unique identifier of the note

        Returns:
            Note if found and belongs to user, None otherwise

        Raises:
            RuntimeError: If retrieval fails
        """
        ...

    async def update(self, note: Note) -> Note:
        """Update an existing note in the repository.

        Args:
            note: Note entity with updated fields

        Returns:
            The updated Note entity

        Raises:
            ValueError: If note doesn't exist
            RuntimeError: If update fails
        """
        ...

    async def delete(self, user_id: str, note_id: str) -> bool:
        """Delete a note from the repository.

        Args:
            user_id: User ID who owns the note
            note_id: Unique identifier of the note

        Returns:
            True if deleted, False if note not found

        Raises:
            RuntimeError: If deletion fails
        """
        ...

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Note]:
        """List all notes for a user with pagination.

        Results are ordered by updated_at timestamp in descending order
        (most recently updated first).

        Args:
            user_id: User ID who owns the notes
            limit: Maximum number of notes to return (default: 10)
            offset: Number of notes to skip (default: 0)

        Returns:
            List of notes ordered by updated_at DESC

        Raises:
            ValueError: If limit or offset are invalid
            RuntimeError: If retrieval fails
        """
        ...

    async def search_by_vector(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[tuple[Note, float]]:
        """Search notes using vector similarity (semantic search).

        Uses cosine similarity to find notes with similar meaning to the query.

        Args:
            user_id: User ID who owns the notes
            query_embedding: Vector embedding of the search query
            limit: Maximum number of results to return (default: 5)
            similarity_threshold: Minimum similarity score (0-1, default: 0.7)

        Returns:
            List of (Note, similarity_score) tuples ordered by similarity DESC

        Raises:
            ValueError: If query_embedding has wrong dimensions
            RuntimeError: If search fails
        """
        ...

    async def search_by_keyword(
        self,
        user_id: str,
        keyword: str,
        limit: int = 10,
    ) -> list[Note]:
        """Search notes using keyword/full-text search.

        Searches in title and content fields.

        Args:
            user_id: User ID who owns the notes
            keyword: Keyword or phrase to search for
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of matching notes ordered by relevance

        Raises:
            RuntimeError: If search fails
        """
        ...

    async def search_by_tags(
        self,
        user_id: str,
        tags: list[str],
        match_all: bool = False,
        limit: int = 10,
    ) -> list[Note]:
        """Search notes by tags.

        Args:
            user_id: User ID who owns the notes
            tags: List of tags to search for
            match_all: If True, note must have all tags; if False, any tag (default: False)
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of matching notes ordered by updated_at DESC

        Raises:
            RuntimeError: If search fails
        """
        ...

    async def search_by_date_range(
        self,
        user_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 10,
    ) -> list[Note]:
        """Search notes by creation date range.

        Args:
            user_id: User ID who owns the notes
            date_from: Start date (inclusive), None for no lower bound
            date_to: End date (inclusive), None for no upper bound
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of matching notes ordered by created_at DESC

        Raises:
            ValueError: If date_from > date_to
            RuntimeError: If search fails
        """
        ...

    async def count_by_user(self, user_id: str) -> int:
        """Count total number of notes for a user.

        Args:
            user_id: User ID who owns the notes

        Returns:
            Total count of notes

        Raises:
            RuntimeError: If count fails
        """
        ...