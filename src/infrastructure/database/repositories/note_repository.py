"""PostgreSQL implementation of Note repository with pgvector support."""

import logging
from datetime import datetime

from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.note import Note
from src.infrastructure.database.models.note_model import NoteModel

logger = logging.getLogger(__name__)


class NoteRepository:
    """PostgreSQL-based note repository with vector search.

    Implements INoteRepository protocol using SQLAlchemy and pgvector.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self._session = session

    async def create(self, note: Note) -> Note:
        """Persist a new note to the database.

        Args:
            note: Note entity to persist

        Returns:
            The persisted Note entity

        Raises:
            ValueError: If note with same ID already exists
            RuntimeError: If persistence fails
        """
        try:
            # Check if note already exists
            existing = await self._session.get(NoteModel, note.id)
            if existing:
                raise ValueError(f"Note with ID {note.id} already exists")

            # Create model from entity
            model = NoteModel(
                id=note.id,
                user_id=note.user_id,
                title=note.title,
                content=note.content,
                tags=list(note.tags),
                embedding=list(note.embedding) if note.embedding else None,
                created_at=note.created_at,
                updated_at=note.updated_at,
            )

            self._session.add(model)
            await self._session.commit()
            await self._session.refresh(model)

            logger.debug("Created note with ID: %s", note.id)
            return self._model_to_entity(model)

        except ValueError:
            raise
        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to create note: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to create note: {e}") from e

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
        try:
            stmt = select(NoteModel).where(
                and_(NoteModel.id == note_id, NoteModel.user_id == user_id)
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                logger.debug("Note %s not found for user %s", note_id, user_id)
                return None

            return self._model_to_entity(model)

        except Exception as e:
            logger.error("Failed to retrieve note: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to retrieve note: {e}") from e

    async def update(self, note: Note) -> Note:
        """Update an existing note in the database.

        Args:
            note: Note entity with updated fields

        Returns:
            The updated Note entity

        Raises:
            ValueError: If note doesn't exist
            RuntimeError: If update fails
        """
        try:
            model = await self._session.get(NoteModel, note.id)
            if model is None:
                raise ValueError(f"Note with ID {note.id} not found")

            # Update fields
            model.user_id = note.user_id
            model.title = note.title
            model.content = note.content
            model.tags = list(note.tags)
            model.embedding = list(note.embedding) if note.embedding else None
            model.updated_at = note.updated_at

            await self._session.commit()
            await self._session.refresh(model)

            logger.debug("Updated note with ID: %s", note.id)
            return self._model_to_entity(model)

        except ValueError:
            raise
        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to update note: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to update note: {e}") from e

    async def delete(self, user_id: str, note_id: str) -> bool:
        """Delete a note from the database.

        Args:
            user_id: User ID who owns the note
            note_id: Unique identifier of the note

        Returns:
            True if deleted, False if note not found

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            stmt = delete(NoteModel).where(
                and_(NoteModel.id == note_id, NoteModel.user_id == user_id)
            )
            result = await self._session.execute(stmt)
            await self._session.commit()

            deleted = result.rowcount > 0
            logger.debug(
                "Delete note %s for user %s: %s", note_id, user_id, "success" if deleted else "not found"
            )
            return deleted

        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to delete note: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to delete note: {e}") from e

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Note]:
        """List all notes for a user with pagination.

        Results are ordered by updated_at timestamp in descending order.

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
        if limit <= 0:
            raise ValueError("Limit must be positive")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        try:
            stmt = (
                select(NoteModel)
                .where(NoteModel.user_id == user_id)
                .order_by(desc(NoteModel.updated_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            logger.debug("Retrieved %d notes for user %s", len(models), user_id)
            return [self._model_to_entity(model) for model in models]

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to list notes: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to list notes: {e}") from e

    async def search_by_vector(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[tuple[Note, float]]:
        """Search notes using vector similarity (semantic search).

        Uses cosine similarity to find notes with similar meaning.

        Args:
            user_id: User ID who owns the notes
            query_embedding: Vector embedding of the search query
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of (Note, similarity_score) tuples ordered by similarity DESC

        Raises:
            ValueError: If query_embedding has wrong dimensions
            RuntimeError: If search fails
        """
        if len(query_embedding) != 1536:
            raise ValueError(f"Query embedding must be 1536 dimensions, got {len(query_embedding)}")

        try:
            # Calculate cosine similarity: 1 - cosine_distance
            similarity = 1 - NoteModel.embedding.cosine_distance(query_embedding)

            stmt = (
                select(NoteModel, similarity.label("similarity"))
                .where(and_(NoteModel.user_id == user_id, similarity >= similarity_threshold))
                .order_by(desc("similarity"))
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            rows = result.all()

            logger.debug("Vector search returned %d results", len(rows))
            return [(self._model_to_entity(row[0]), float(row[1])) for row in rows]

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to search by vector: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to search by vector: {e}") from e

    async def search_by_keyword(
        self,
        user_id: str,
        keyword: str,
        limit: int = 10,
    ) -> list[Note]:
        """Search notes using keyword/full-text search.

        Searches in title and content fields using PostgreSQL ILIKE.

        Args:
            user_id: User ID who owns the notes
            keyword: Keyword or phrase to search for
            limit: Maximum number of results to return

        Returns:
            List of matching notes ordered by relevance

        Raises:
            RuntimeError: If search fails
        """
        try:
            search_pattern = f"%{keyword}%"
            stmt = (
                select(NoteModel)
                .where(
                    and_(
                        NoteModel.user_id == user_id,
                        or_(
                            NoteModel.title.ilike(search_pattern),
                            NoteModel.content.ilike(search_pattern),
                        ),
                    )
                )
                .order_by(desc(NoteModel.updated_at))
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            logger.debug("Keyword search returned %d results", len(models))
            return [self._model_to_entity(model) for model in models]

        except Exception as e:
            logger.error("Failed to search by keyword: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to search by keyword: {e}") from e

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
            match_all: If True, note must have all tags; if False, any tag
            limit: Maximum number of results to return

        Returns:
            List of matching notes ordered by updated_at DESC

        Raises:
            RuntimeError: If search fails
        """
        try:
            if match_all:
                # Note must contain all tags
                tag_condition = NoteModel.tags.contains(tags)
            else:
                # Note must contain at least one tag
                tag_condition = NoteModel.tags.overlap(tags)

            stmt = (
                select(NoteModel)
                .where(and_(NoteModel.user_id == user_id, tag_condition))
                .order_by(desc(NoteModel.updated_at))
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            logger.debug("Tag search returned %d results", len(models))
            return [self._model_to_entity(model) for model in models]

        except Exception as e:
            logger.error("Failed to search by tags: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to search by tags: {e}") from e

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
            limit: Maximum number of results to return

        Returns:
            List of matching notes ordered by created_at DESC

        Raises:
            ValueError: If date_from > date_to
            RuntimeError: If search fails
        """
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        try:
            conditions = [NoteModel.user_id == user_id]

            if date_from:
                conditions.append(NoteModel.created_at >= date_from)
            if date_to:
                conditions.append(NoteModel.created_at <= date_to)

            stmt = (
                select(NoteModel)
                .where(and_(*conditions))
                .order_by(desc(NoteModel.created_at))
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            logger.debug("Date range search returned %d results", len(models))
            return [self._model_to_entity(model) for model in models]

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to search by date range: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to search by date range: {e}") from e

    async def count_by_user(self, user_id: str) -> int:
        """Count total number of notes for a user.

        Args:
            user_id: User ID who owns the notes

        Returns:
            Total count of notes

        Raises:
            RuntimeError: If count fails
        """
        try:
            stmt = select(func.count()).select_from(NoteModel).where(NoteModel.user_id == user_id)
            result = await self._session.execute(stmt)
            count = result.scalar_one()

            logger.debug("User %s has %d notes", user_id, count)
            return count

        except Exception as e:
            logger.error("Failed to count notes: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to count notes: {e}") from e

    @staticmethod
    def _model_to_entity(model: NoteModel) -> Note:
        """Convert SQLAlchemy model to domain entity.

        Args:
            model: NoteModel instance

        Returns:
            Note entity
        """
        return Note(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            content=model.content,
            tags=tuple(model.tags) if model.tags else tuple(),
            embedding=tuple(float(x) for x in model.embedding) if model.embedding is not None else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
