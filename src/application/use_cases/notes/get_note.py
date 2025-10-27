"""Get Note use case."""

import logging

from src.domain.entities.note import Note
from src.domain.repositories.note_repository import INoteRepository

logger = logging.getLogger(__name__)


class GetNoteUseCase:
    """Use case for retrieving a single note."""

    def __init__(self, repository: INoteRepository) -> None:
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for retrieving notes
        """
        self._repository = repository

    async def execute(self, user_id: str, note_id: str) -> Note | None:
        """Retrieve a note by ID.

        Args:
            user_id: User ID who owns the note
            note_id: ID of the note to retrieve

        Returns:
            Note if found, None otherwise

        Raises:
            RuntimeError: If retrieval fails
        """
        logger.info("Retrieving note %s for user %s", note_id, user_id)

        try:
            note = await self._repository.get_by_id(user_id, note_id)

            if note:
                logger.debug("Found note %s", note_id)
            else:
                logger.debug("Note %s not found", note_id)

            return note

        except Exception as e:
            logger.error("Failed to retrieve note: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to retrieve note: {e}") from e
