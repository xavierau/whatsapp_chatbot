"""Message repository protocol (interface).

This module defines the repository interface for Message entity following
the Repository pattern and Dependency Inversion Principle (SOLID).
"""

from typing import Protocol

from src.domain.entities.message import Message


class IMessageRepository(Protocol):
    """Interface for Message repository.

    This protocol defines the contract that any Message repository implementation
    must follow, enabling dependency injection and testability.
    """

    async def create(self, message: Message) -> Message:
        """Create a new message in the repository.

        Args:
            message: Message entity to create

        Returns:
            Created Message entity with any repository-generated fields

        Raises:
            ValueError: If message creation fails validation
            RuntimeError: If database operation fails
        """
        ...

    async def get_by_id(self, message_id: str) -> Message | None:
        """Retrieve a message by ID.

        Args:
            message_id: Unique identifier of the message

        Returns:
            Message entity if found, None otherwise (excludes soft-deleted messages)

        Raises:
            RuntimeError: If database operation fails
        """
        ...

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
            (excludes soft-deleted messages)

        Raises:
            RuntimeError: If database operation fails
        """
        ...

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
            (excludes soft-deleted and system messages for cleaner context)

        Raises:
            RuntimeError: If database operation fails
        """
        ...

    async def get_messages_with_tool_results(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[Message]:
        """Get messages that have tool execution results.

        Useful for analytics and debugging tool usage patterns.

        Args:
            session_id: Unique identifier of the session
            limit: Maximum number of messages to return (default: 50)

        Returns:
            List of Message entities that have non-null tool_result field
            (excludes soft-deleted messages)

        Raises:
            RuntimeError: If database operation fails
        """
        ...

    async def delete(self, message_id: str) -> bool:
        """Soft delete a message by ID.

        This method marks the message as deleted without actually removing it
        from the database, supporting audit trails and compliance.

        Args:
            message_id: Unique identifier of the message to delete

        Returns:
            True if message was deleted, False if message not found

        Raises:
            RuntimeError: If database operation fails
        """
        ...

    async def count_session_messages(self, session_id: str) -> int:
        """Count the number of messages in a session.

        Args:
            session_id: Unique identifier of the session

        Returns:
            Number of messages in the session (excludes soft-deleted messages)

        Raises:
            RuntimeError: If database operation fails
        """
        ...

    async def get_latest_message(self, session_id: str) -> Message | None:
        """Get the most recent message in a session.

        Args:
            session_id: Unique identifier of the session

        Returns:
            Most recent Message entity if found, None if session has no messages
            (excludes soft-deleted messages)

        Raises:
            RuntimeError: If database operation fails
        """
        ...
