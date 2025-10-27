"""List Notes use case."""

import logging

from src.domain.entities.note import Note
from src.domain.repositories.note_repository import INoteRepository

logger = logging.getLogger(__name__)


class ListNotesUseCase:
    """Use case for listing user's notes with pagination."""

    def __init__(self, repository: INoteRepository) -> None:
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for retrieving notes
        """
        self._repository = repository

    async def execute(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Note]:
        """List notes for a user with pagination.

        Args:
            user_id: User ID who owns the notes
            limit: Maximum number of notes to return
            offset: Number of notes to skip

        Returns:
            List of notes ordered by updated_at DESC

        Raises:
            ValueError: If limit or offset are invalid
            RuntimeError: If retrieval fails
        """
        logger.info("Listing notes for user %s (limit=%d, offset=%d)", user_id, limit, offset)

        # Validate parameters
        if limit <= 0:
            raise ValueError("Limit must be positive")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        try:
            notes = await self._repository.list_by_user(user_id, limit, offset)

            logger.debug("Retrieved %d notes for user %s", len(notes), user_id)
            return notes

        except ValueError as e:
            logger.error("Validation error listing notes: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to list notes: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to list notes: {e}") from e
