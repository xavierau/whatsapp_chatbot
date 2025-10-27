"""Store message use case.

This use case handles storing conversation messages with tool results
and response time tracking for LLM integration.
"""

import logging
from typing import Any

from src.domain.entities.message import Message, MessageRole
from src.domain.repositories.message_repository import IMessageRepository
from src.domain.repositories.session_repository import ISessionRepository

logger = logging.getLogger(__name__)


class StoreMessageUseCase:
    """Use case for storing conversation messages.

    This use case encapsulates the business logic for message storage,
    including session validation and activity updates.
    """

    def __init__(
        self,
        message_repository: IMessageRepository,
        session_repository: ISessionRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            message_repository: Repository for message persistence
            session_repository: Repository for session validation/updates
        """
        self.message_repository = message_repository
        self.session_repository = session_repository

    async def execute(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        tool_result: dict[str, Any] | None = None,
        whatsapp_message_id: str | None = None,
        response_time_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Store a conversation message.

        Args:
            session_id: Unique identifier of the session
            role: Message role (user, assistant, system)
            content: Message content
            tool_result: Optional DSPy tool execution result
            whatsapp_message_id: Optional WhatsApp message ID
            response_time_ms: Optional LLM response time in milliseconds
            metadata: Optional additional metadata

        Returns:
            Created Message entity

        Raises:
            ValueError: If session not found or cannot receive messages
            RuntimeError: If message storage fails
        """
        try:
            # Validate session exists and can receive messages
            session = await self.session_repository.get_by_id(session_id)
            if session is None:
                raise ValueError(f"Session with ID {session_id} not found")

            if not session.can_receive_messages():
                raise ValueError(
                    f"Session {session_id} cannot receive messages (status: {session.status})"
                )

            # Create message entity
            message = Message.create(
                session_id=session_id,
                role=role,
                content=content,
                tool_result=tool_result,
                whatsapp_message_id=whatsapp_message_id,
                response_time_ms=response_time_ms,
                metadata=metadata,
            )

            # Persist message
            created = await self.message_repository.create(message)

            # Update session activity
            await self.session_repository.update_activity(session_id)

            logger.info(
                "Message stored: %s (session: %s, role: %s)",
                created.id,
                session_id,
                role.value,
            )

            return created

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to store message: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to store message: {e}") from e

    async def store_user_message(
        self,
        session_id: str,
        content: str,
        whatsapp_message_id: str | None = None,
    ) -> Message:
        """Convenience method for storing user messages.

        Args:
            session_id: Unique identifier of the session
            content: Message content
            whatsapp_message_id: Optional WhatsApp message ID

        Returns:
            Created Message entity

        Raises:
            ValueError: If session validation fails
            RuntimeError: If storage fails
        """
        return await self.execute(
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
            whatsapp_message_id=whatsapp_message_id,
        )

    async def store_assistant_message(
        self,
        session_id: str,
        content: str,
        tool_result: dict[str, Any] | None = None,
        response_time_ms: int | None = None,
    ) -> Message:
        """Convenience method for storing assistant messages.

        Args:
            session_id: Unique identifier of the session
            content: Message content
            tool_result: Optional DSPy tool execution result
            response_time_ms: Optional LLM response time in milliseconds

        Returns:
            Created Message entity

        Raises:
            ValueError: If session validation fails
            RuntimeError: If storage fails
        """
        return await self.execute(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content,
            tool_result=tool_result,
            response_time_ms=response_time_ms,
        )

    async def store_system_message(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Convenience method for storing system messages.

        Args:
            session_id: Unique identifier of the session
            content: Message content
            metadata: Optional additional metadata

        Returns:
            Created Message entity

        Raises:
            ValueError: If session validation fails
            RuntimeError: If storage fails
        """
        return await self.execute(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=content,
            metadata=metadata,
        )
