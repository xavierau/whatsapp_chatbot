"""Get conversation history use case.

This use case handles retrieving conversation history optimized for LLM context.
"""

import logging

from src.domain.entities.message import Message
from src.domain.repositories.message_repository import IMessageRepository

logger = logging.getLogger(__name__)


class GetConversationHistoryUseCase:
    """Use case for retrieving conversation history.

    This use case encapsulates the business logic for fetching conversation
    history optimized for LLM integration (excludes system messages, proper ordering).
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
        max_messages: int = 10,
    ) -> list[Message]:
        """Get conversation history for LLM context.

        This method retrieves the most recent conversation messages,
        excluding system messages and ordered from oldest to newest
        for proper LLM context building.

        Args:
            session_id: Unique identifier of the session
            max_messages: Maximum number of messages to retrieve (default: 10)

        Returns:
            List of Message entities ordered from oldest to newest

        Raises:
            RuntimeError: If retrieval fails
        """
        try:
            messages = await self.message_repository.get_conversation_history(
                session_id=session_id,
                max_messages=max_messages,
            )

            logger.debug(
                "Retrieved %d conversation messages for session: %s",
                len(messages),
                session_id,
            )

            return messages

        except Exception as e:
            logger.error("Failed to get conversation history: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get conversation history: {e}") from e

    async def format_for_llm(
        self,
        session_id: str,
        max_messages: int = 10,
    ) -> str:
        """Get conversation history formatted for LLM.

        Args:
            session_id: Unique identifier of the session
            max_messages: Maximum number of messages to retrieve

        Returns:
            Formatted conversation string ready for LLM context

        Raises:
            RuntimeError: If retrieval or formatting fails
        """
        try:
            messages = await self.execute(
                session_id=session_id,
                max_messages=max_messages,
            )

            if not messages:
                return ""

            formatted_lines = [msg.format_for_llm() for msg in messages]
            formatted_text = "\n".join(formatted_lines)

            logger.debug(
                "Formatted %d messages for LLM (session: %s)",
                len(messages),
                session_id,
            )

            return formatted_text

        except Exception as e:
            logger.error("Failed to format conversation for LLM: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to format conversation for LLM: {e}") from e

    async def get_messages_with_tools(self, session_id: str) -> list[Message]:
        """Get messages that contain tool results.

        Useful for analytics and debugging tool usage patterns.

        Args:
            session_id: Unique identifier of the session

        Returns:
            List of Message entities that have tool_result data

        Raises:
            RuntimeError: If retrieval fails
        """
        try:
            messages = await self.message_repository.get_messages_with_tool_results(
                session_id=session_id
            )

            logger.debug(
                "Retrieved %d messages with tool results (session: %s)",
                len(messages),
                session_id,
            )

            return messages

        except Exception as e:
            logger.error("Failed to get messages with tools: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get messages with tools: {e}") from e
