"""Update Note use case."""

import logging

from src.application.interfaces.embedding_service import IEmbeddingService
from src.domain.entities.note import Note
from src.domain.repositories.note_repository import INoteRepository

logger = logging.getLogger(__name__)


class UpdateNoteUseCase:
    """Use case for updating an existing note.

    Updates the note and regenerates embedding if content/title changed.
    """

    def __init__(
        self,
        repository: INoteRepository,
        embedding_service: IEmbeddingService,
    ) -> None:
        """Initialize the use case with dependencies.

        Args:
            repository: Repository for persisting notes
            embedding_service: Service for generating embeddings
        """
        self._repository = repository
        self._embedding_service = embedding_service

    async def execute(
        self,
        user_id: str,
        note_id: str,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
    ) -> Note:
        """Update an existing note.

        Regenerates embedding if title or content changed.

        Args:
            user_id: User ID who owns the note
            note_id: ID of the note to update
            title: New title (optional)
            content: New content (optional)
            tags: New tags (optional)

        Returns:
            Updated Note entity

        Raises:
            ValueError: If note not found or doesn't belong to user
            RuntimeError: If update fails
        """
        logger.info("Updating note %s for user %s", note_id, user_id)

        try:
            # Retrieve existing note
            existing_note = await self._repository.get_by_id(user_id, note_id)
            if existing_note is None:
                raise ValueError(f"Note {note_id} not found for user {user_id}")

            # Check if embedding needs regeneration
            needs_reembedding = title is not None or content is not None

            embedding = existing_note.embedding
            if needs_reembedding:
                # Use new or existing values
                new_title = title if title is not None else existing_note.title
                new_content = content if content is not None else existing_note.content
                embedding_text = f"{new_title}\n{new_content}"

                embedding_list = await self._embedding_service.generate_embedding(embedding_text)
                embedding = tuple(embedding_list)
                logger.debug("Regenerated embedding with %d dimensions", len(embedding))

            # Update note
            updated_note = existing_note.update(
                title=title,
                content=content,
                tags=tags,
                embedding=list(embedding) if embedding else None,
            )

            # Persist updates
            result = await self._repository.update(updated_note)

            logger.info("Successfully updated note %s", note_id)
            return result

        except ValueError as e:
            logger.error("Validation error updating note: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to update note: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to update note: {e}") from e
