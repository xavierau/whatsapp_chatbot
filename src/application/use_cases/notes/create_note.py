"""Create Note use case.

This use case handles the creation of new notes with embedding generation.
Follows Single Responsibility Principle and Dependency Inversion.
"""

import logging

from src.application.interfaces.embedding_service import IEmbeddingService
from src.domain.entities.note import Note
from src.domain.repositories.note_repository import INoteRepository

logger = logging.getLogger(__name__)


class CreateNoteUseCase:
    """Use case for creating a new note with embedding.

    This use case coordinates between the embedding service and repository
    to create a new note. It follows the Single Responsibility Principle
    by focusing only on note creation logic.

    Dependencies are injected following Dependency Inversion Principle.
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
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> Note:
        """Create a new note with generated embedding.

        Args:
            user_id: User ID who owns the note
            title: Title of the note
            content: Content of the note
            tags: Optional list of tags

        Returns:
            Created Note entity

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If creation fails
        """
        logger.info("Creating note for user %s with title: %s", user_id, title[:50])

        try:
            # Generate embedding for the content
            embedding_text = f"{title}\n{content}"
            embedding = await self._embedding_service.generate_embedding(embedding_text)

            logger.debug("Generated embedding with %d dimensions", len(embedding))

            # Create note entity
            note = Note.create(
                user_id=user_id,
                title=title,
                content=content,
                tags=tags,
                embedding=embedding,
            )

            # Persist note
            created_note = await self._repository.create(note)

            logger.info("Successfully created note with ID: %s", created_note.id)
            return created_note

        except ValueError as e:
            logger.error("Validation error creating note: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to create note: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to create note: {e}") from e
