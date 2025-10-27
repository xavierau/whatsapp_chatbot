"""Search Notes use case."""

import logging
from datetime import datetime
from typing import Literal

from src.application.interfaces.embedding_service import IEmbeddingService
from src.domain.entities.note import Note
from src.domain.repositories.note_repository import INoteRepository

logger = logging.getLogger(__name__)


class SearchNotesUseCase:
    """Use case for searching notes with multiple strategies.

    Supports semantic (vector), keyword, tag, and date-based search.
    """

    def __init__(
        self,
        repository: INoteRepository,
        embedding_service: IEmbeddingService,
    ) -> None:
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for retrieving notes
            embedding_service: Service for generating embeddings
        """
        self._repository = repository
        self._embedding_service = embedding_service

    async def execute(
        self,
        user_id: str,
        query: str | None = None,
        search_type: Literal["semantic", "keyword", "tag", "date"] = "semantic",
        tags: list[str] | None = None,
        match_all_tags: bool = False,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> list[Note]:
        """Search notes using specified strategy.

        Args:
            user_id: User ID who owns the notes
            query: Search query (required for semantic/keyword search)
            search_type: Type of search to perform
            tags: Tags to filter by (for tag search)
            match_all_tags: Whether to require all tags (True) or any tag (False)
            date_from: Start date for date search
            date_to: End date for date search
            limit: Maximum number of results
            similarity_threshold: Minimum similarity for semantic search (0-1)

        Returns:
            List of matching notes

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If search fails
        """
        logger.info(
            "Searching notes for user %s (type=%s, query=%s)",
            user_id,
            search_type,
            query[:50] if query else None,
        )

        try:
            if search_type == "semantic":
                return await self._search_semantic(user_id, query, limit, similarity_threshold)
            elif search_type == "keyword":
                return await self._search_keyword(user_id, query, limit)
            elif search_type == "tag":
                return await self._search_tags(user_id, tags, match_all_tags, limit)
            elif search_type == "date":
                return await self._search_date_range(user_id, date_from, date_to, limit)
            else:
                raise ValueError(f"Invalid search type: {search_type}")

        except ValueError as e:
            logger.error("Validation error searching notes: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to search notes: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to search notes: {e}") from e

    async def _search_semantic(
        self,
        user_id: str,
        query: str | None,
        limit: int,
        similarity_threshold: float,
    ) -> list[Note]:
        """Perform semantic (vector) search."""
        if not query:
            raise ValueError("Query is required for semantic search")

        # Generate embedding for query
        query_embedding = await self._embedding_service.generate_embedding(query)

        # Search by vector similarity
        results = await self._repository.search_by_vector(
            user_id=user_id,
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
        )

        # Extract notes from (note, similarity) tuples
        notes = [note for note, _ in results]

        logger.debug("Semantic search returned %d results", len(notes))
        return notes

    async def _search_keyword(
        self,
        user_id: str,
        query: str | None,
        limit: int,
    ) -> list[Note]:
        """Perform keyword search."""
        if not query:
            raise ValueError("Query is required for keyword search")

        notes = await self._repository.search_by_keyword(
            user_id=user_id,
            keyword=query,
            limit=limit,
        )

        logger.debug("Keyword search returned %d results", len(notes))
        return notes

    async def _search_tags(
        self,
        user_id: str,
        tags: list[str] | None,
        match_all: bool,
        limit: int,
    ) -> list[Note]:
        """Perform tag-based search."""
        if not tags:
            raise ValueError("Tags are required for tag search")

        notes = await self._repository.search_by_tags(
            user_id=user_id,
            tags=tags,
            match_all=match_all,
            limit=limit,
        )

        logger.debug("Tag search returned %d results", len(notes))
        return notes

    async def _search_date_range(
        self,
        user_id: str,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
    ) -> list[Note]:
        """Perform date range search."""
        if date_from is None and date_to is None:
            raise ValueError("At least one date boundary is required for date search")

        notes = await self._repository.search_by_date_range(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )

        logger.debug("Date range search returned %d results", len(notes))
        return notes
