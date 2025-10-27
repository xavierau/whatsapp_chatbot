"""PostgreSQL implementation of Message repository.

This module implements the IMessageRepository protocol using SQLAlchemy
and asyncpg for PostgreSQL database operations.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.message import Message, MessageRole
from src.infrastructure.database.models.message_model import MessageModel

logger = logging.getLogger(__name__)


class MessageRepository:
    """PostgreSQL implementation of Message repository.

    This repository handles all database operations for Message entities,
    including conversation history retrieval and tool result queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    def _to_entity(self, model: MessageModel) -> Message:
        """Convert MessageModel to Message entity.

        Args:
            model: SQLAlchemy MessageModel instance

        Returns:
            Message entity instance
        """
        return Message(
            id=model.id,
            session_id=model.session_id,
            role=model.role,
            content=model.content,
            tool_result=model.tool_result,
            whatsapp_message_id=model.whatsapp_message_id,
            response_time_ms=model.response_time_ms,
            created_at=model.created_at,
            metadata=model.message_metadata,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Message) -> MessageModel:
        """Convert Message entity to MessageModel.

        Args:
            entity: Message entity instance

        Returns:
            SQLAlchemy MessageModel instance
        """
        return MessageModel(
            id=entity.id,
            session_id=entity.session_id,
            role=entity.role,
            content=entity.content,
            tool_result=entity.tool_result,
            whatsapp_message_id=entity.whatsapp_message_id,
            response_time_ms=entity.response_time_ms,
            created_at=entity.created_at,
            message_metadata=entity.metadata,
            deleted_at=entity.deleted_at,
        )

    async def create(self, message: Message) -> Message:
        """Create a new message in the database.

        Args:
            message: Message entity to create

        Returns:
            Created Message entity

        Raises:
            ValueError: If message creation fails validation
            RuntimeError: If database operation fails
        """
        try:
            # Convert entity to model and add to session
            model = self._to_model(message)
            self.session.add(model)
            await self.session.flush()

            logger.info(
                "Created message: %s (session: %s, role: %s)",
                model.id,
                model.session_id,
                model.role.value,
            )
            return self._to_entity(model)

        except Exception as e:
            logger.error("Failed to create message: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to create message: {e}") from e

    async def get_by_id(self, message_id: str) -> Message | None:
        """Retrieve a message by ID.

        Args:
            message_id: Unique identifier of the message

        Returns:
            Message entity if found and not deleted, None otherwise

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            stmt = select(MessageModel).where(
                MessageModel.id == message_id,
                MessageModel.deleted_at.is_(None),
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                logger.debug("Message not found: %s", message_id)
                return None

            logger.debug("Retrieved message: %s", message_id)
            return self._to_entity(model)

        except Exception as e:
            logger.error("Failed to get message by ID: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get message by ID: {e}") from e

    async def get_session_messages(
        self,
        session_id: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Message]:
        """Get all messages for a session, ordered by creation time.

        Args:
            session_id: Unique identifier of the session
            limit: Maximum number of messages to return (None for all)
            offset: Number of messages to skip (for pagination)

        Returns:
            List of Message entities ordered by created_at ascending

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            # Build query
            stmt = (
                select(MessageModel)
                .where(
                    MessageModel.session_id == session_id,
                    MessageModel.deleted_at.is_(None),
                )
                .order_by(MessageModel.created_at.asc())
                .offset(offset)
            )

            # Apply limit if specified
            if limit is not None:
                stmt = stmt.limit(limit)

            result = await self.session.execute(stmt)
            models = result.scalars().all()

            logger.debug(
                "Retrieved %d messages for session: %s", len(models), session_id
            )
            return [self._to_entity(model) for model in models]

        except Exception as e:
            logger.error("Failed to get session messages: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get session messages: {e}") from e

    async def get_conversation_history(
        self,
        session_id: str,
        max_messages: int = 10,
    ) -> list[Message]:
        """Get recent conversation history for LLM context.

        Returns the most recent N messages from the session, ordered by
        creation time (oldest to newest) for LLM conversation context.

        Args:
            session_id: Unique identifier of the session
            max_messages: Maximum number of recent messages to return (default: 10)

        Returns:
            List of Message entities ordered by created_at ascending

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            # Get most recent messages (excluding system messages for cleaner context)
            stmt = (
                select(MessageModel)
                .where(
                    MessageModel.session_id == session_id,
                    MessageModel.role != MessageRole.SYSTEM,
                    MessageModel.deleted_at.is_(None),
                )
                .order_by(MessageModel.created_at.desc())
                .limit(max_messages)
            )

            result = await self.session.execute(stmt)
            models = list(result.scalars().all())

            # Reverse to get chronological order (oldest to newest)
            models.reverse()

            logger.debug(
                "Retrieved %d messages for conversation history (session: %s)",
                len(models),
                session_id,
            )
            return [self._to_entity(model) for model in models]

        except Exception as e:
            logger.error("Failed to get conversation history: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get conversation history: {e}") from e

    async def get_messages_with_tool_results(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[Message]:
        """Get messages that have tool execution results.

        Args:
            session_id: Unique identifier of the session
            limit: Maximum number of messages to return (default: 50)

        Returns:
            List of Message entities that have non-null tool_result field

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            stmt = (
                select(MessageModel)
                .where(
                    MessageModel.session_id == session_id,
                    MessageModel.tool_result.isnot(None),
                    MessageModel.deleted_at.is_(None),
                )
                .order_by(MessageModel.created_at.desc())
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            models = result.scalars().all()

            logger.debug(
                "Retrieved %d messages with tool results (session: %s)",
                len(models),
                session_id,
            )
            return [self._to_entity(model) for model in models]

        except Exception as e:
            logger.error("Failed to get messages with tool results: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get messages with tool results: {e}") from e

    async def delete(self, message_id: str) -> bool:
        """Soft delete a message by ID.

        Args:
            message_id: Unique identifier of the message to delete

        Returns:
            True if message was deleted, False if message not found

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            # Check if message exists
            existing = await self.get_by_id(message_id)
            if existing is None:
                logger.debug("Message not found for deletion: %s", message_id)
                return False

            # Soft delete by setting deleted_at timestamp
            stmt = (
                update(MessageModel)
                .where(MessageModel.id == message_id)
                .values(deleted_at=datetime.now(UTC))
            )
            await self.session.execute(stmt)
            await self.session.flush()

            logger.info("Soft deleted message: %s", message_id)
            return True

        except Exception as e:
            logger.error("Failed to delete message: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to delete message: {e}") from e

    async def count_session_messages(self, session_id: str) -> int:
        """Count the number of messages in a session.

        Args:
            session_id: Unique identifier of the session

        Returns:
            Number of messages in the session (excludes soft-deleted messages)

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            stmt = select(func.count(MessageModel.id)).where(
                MessageModel.session_id == session_id,
                MessageModel.deleted_at.is_(None),
            )
            result = await self.session.execute(stmt)
            count = result.scalar_one()

            logger.debug("Counted %d messages for session: %s", count, session_id)
            return count

        except Exception as e:
            logger.error("Failed to count session messages: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to count session messages: {e}") from e

    async def get_latest_message(self, session_id: str) -> Message | None:
        """Get the most recent message in a session.

        Args:
            session_id: Unique identifier of the session

        Returns:
            Most recent Message entity if found, None if session has no messages

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            stmt = (
                select(MessageModel)
                .where(
                    MessageModel.session_id == session_id,
                    MessageModel.deleted_at.is_(None),
                )
                .order_by(MessageModel.created_at.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                logger.debug("No messages found for session: %s", session_id)
                return None

            logger.debug("Retrieved latest message for session: %s", session_id)
            return self._to_entity(model)

        except Exception as e:
            logger.error("Failed to get latest message: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get latest message: {e}") from e
