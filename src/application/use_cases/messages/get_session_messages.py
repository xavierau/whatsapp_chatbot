"""Get session messages use case.

This use case handles retrieving all messages for a session with pagination.
"""

import logging

from src.domain.entities.message import Message
from src.domain.repositories.message_repository import IMessageRepository

logger = logging.getLogger(__name__)


class GetSessionMessagesUseCase:
    """Use case for retrieving session messages.

    This use case encapsulates the business logic for fetching all messages
    in a session with pagination support.
    """

    def __init__(self, message_repository: IMessageRepository) -> None:
        """Initialize the use case.

        Args:
            message_repository: Repository for message persistence
        """
        self.message_repository = message_repository

    async def execute(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages for a session with pagination.

        Args:
            session_id: Unique identifier of the session
            limit: Maximum number of messages to retrieve (default: 50)
            offset: Number of messages to skip (default: 0)

        Returns:
            List of Message entities ordered by creation time

        Raises:
            ValueError: If limit or offset are invalid
            RuntimeError: If retrieval fails
        """
        try:
            if limit <= 0:
                raise ValueError("Limit must be positive")
            if offset < 0:
                raise ValueError("Offset must be non-negative")

            messages = await self.message_repository.get_session_messages(
                session_id=session_id,
                limit=limit,
                offset=offset,
            )

            logger.debug(
                "Retrieved %d messages for session: %s (offset: %d)",
                len(messages),
                session_id,
                offset,
            )

            return messages

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to get session messages: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get session messages: {e}") from e

    async def get_message_count(self, session_id: str) -> int:
        """Get total message count for a session.

        Args:
            session_id: Unique identifier of the session

        Returns:
            Total number of messages in the session

        Raises:
            RuntimeError: If count fails
        """
        try:
            count = await self.message_repository.count_session_messages(session_id)

            logger.debug(
                "Message count for session %s: %d",
                session_id,
                count,
            )

            return count

        except Exception as e:
            logger.error("Failed to count session messages: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to count session messages: {e}") from e

    async def get_all_messages(self, session_id: str) -> list[Message]:
        """Get all messages for a session without pagination.

        Warning: Use with caution for sessions with many messages.

        Args:
            session_id: Unique identifier of the session

        Returns:
            Complete list of Message entities

        Raises:
            RuntimeError: If retrieval fails
        """
        try:
            # Get total count first
            total = await self.get_message_count(session_id)

            if total == 0:
                return []

            # Fetch all messages
            messages = await self.message_repository.get_session_messages(
                session_id=session_id,
                limit=total,
                offset=0,
            )

            logger.debug(
                "Retrieved all %d messages for session: %s",
                len(messages),
                session_id,
            )

            return messages

        except Exception as e:
            logger.error("Failed to get all session messages: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get all session messages: {e}") from e
