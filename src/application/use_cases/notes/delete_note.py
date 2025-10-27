"""Delete Note use case."""

import logging

from src.domain.repositories.note_repository import INoteRepository

logger = logging.getLogger(__name__)


class DeleteNoteUseCase:
    """Use case for deleting a note."""

    def __init__(self, repository: INoteRepository) -> None:
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for persisting notes
        """
        self._repository = repository

    async def execute(self, user_id: str, note_id: str) -> bool:
        """Delete a note.

        Args:
            user_id: User ID who owns the note
            note_id: ID of the note to delete

        Returns:
            True if deleted, False if not found

        Raises:
            RuntimeError: If deletion fails
        """
        logger.info("Deleting note %s for user %s", note_id, user_id)

        try:
            result = await self._repository.delete(user_id, note_id)

            if result:
                logger.info("Successfully deleted note %s", note_id)
            else:
                logger.warning("Note %s not found for deletion", note_id)

            return result

        except Exception as e:
            logger.error("Failed to delete note: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to delete note: {e}") from e
