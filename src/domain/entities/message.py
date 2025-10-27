"""Message entity for conversation message storage.

This module defines the Message entity following Domain-Driven Design principles.
Messages represent individual conversation turns between users and the chatbot,
with support for tool results and LLM performance tracking.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class Message:
    """Message entity representing a conversation message.

    This entity is immutable (frozen) following functional programming principles
    and value object patterns. Any modification creates a new Message instance.

    Attributes:
        id: Unique identifier for the message (UUID)
        session_id: Foreign key to Session entity
        role: Message sender role (user, assistant, system)
        content: Message text content
        tool_result: DSPy tool execution results (stored as dict)
        whatsapp_message_id: WhatsApp API message ID (for tracking)
        response_time_ms: LLM generation time in milliseconds
        created_at: Message timestamp
        metadata: Optional metadata for extensibility
        deleted_at: Soft delete timestamp (None if not deleted)
    """

    id: str
    session_id: str
    role: MessageRole
    content: str
    tool_result: dict[str, Any] | None = None
    whatsapp_message_id: str | None = None
    response_time_ms: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] | None = None
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate message attributes after initialization.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate ID
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Message ID must be a non-empty string")

        # Validate session_id
        if not self.session_id or not isinstance(self.session_id, str):
            raise ValueError("Session ID must be a non-empty string")

        # Validate role
        if not isinstance(self.role, MessageRole):
            raise ValueError("Role must be a valid MessageRole")

        # Validate content
        if not isinstance(self.content, str):
            raise ValueError("Content must be a string")
        if not self.content.strip():
            raise ValueError("Content cannot be empty or whitespace")

        # Validate tool_result
        if self.tool_result is not None and not isinstance(self.tool_result, dict):
            raise ValueError("Tool result must be a dictionary")

        # Validate whatsapp_message_id
        if self.whatsapp_message_id is not None:
            if not isinstance(self.whatsapp_message_id, str):
                raise ValueError("WhatsApp message ID must be a string")
            if len(self.whatsapp_message_id) > 255:
                raise ValueError("WhatsApp message ID cannot exceed 255 characters")

        # Validate response_time_ms
        if self.response_time_ms is not None:
            if not isinstance(self.response_time_ms, int):
                raise ValueError("Response time must be an integer")
            if self.response_time_ms <= 0:
                raise ValueError("Response time must be a positive integer")

        # Validate metadata
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime object")
        if self.deleted_at is not None and not isinstance(self.deleted_at, datetime):
            raise ValueError("deleted_at must be a datetime object or None")

    @classmethod
    def create(
        cls,
        session_id: str,
        role: MessageRole,
        content: str,
        tool_result: dict[str, Any] | None = None,
        whatsapp_message_id: str | None = None,
        response_time_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        """Factory method to create a new Message with generated ID and timestamp.

        Args:
            session_id: ID of the session this message belongs to
            role: Message sender role (user, assistant, system)
            content: Message text content
            tool_result: Optional DSPy tool execution results
            whatsapp_message_id: Optional WhatsApp API message ID
            response_time_ms: Optional LLM generation time in milliseconds
            metadata: Optional metadata dict

        Returns:
            New Message instance with generated ID and timestamp

        Raises:
            ValueError: If validation fails
        """
        return cls(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content.strip(),
            tool_result=tool_result,
            whatsapp_message_id=whatsapp_message_id,
            response_time_ms=response_time_ms,
            created_at=datetime.now(UTC),
            metadata=metadata,
            deleted_at=None,
        )

    def mark_as_deleted(self) -> "Message":
        """Create a new Message instance marked as soft deleted.

        Returns:
            New Message instance with deleted_at timestamp set
        """
        return Message(
            id=self.id,
            session_id=self.session_id,
            role=self.role,
            content=self.content,
            tool_result=self.tool_result,
            whatsapp_message_id=self.whatsapp_message_id,
            response_time_ms=self.response_time_ms,
            created_at=self.created_at,
            metadata=self.metadata,
            deleted_at=datetime.now(UTC),
        )

    @property
    def is_user_message(self) -> bool:
        """Check if message is from user.

        Returns:
            True if message role is USER, False otherwise
        """
        return self.role == MessageRole.USER

    @property
    def is_assistant_message(self) -> bool:
        """Check if message is from assistant.

        Returns:
            True if message role is ASSISTANT, False otherwise
        """
        return self.role == MessageRole.ASSISTANT

    @property
    def is_system_message(self) -> bool:
        """Check if message is a system message.

        Returns:
            True if message role is SYSTEM, False otherwise
        """
        return self.role == MessageRole.SYSTEM

    @property
    def has_tool_result(self) -> bool:
        """Check if message has tool execution results.

        Returns:
            True if tool_result is not None, False otherwise
        """
        return self.tool_result is not None

    @property
    def is_deleted(self) -> bool:
        """Check if message is soft deleted.

        Returns:
            True if message has a deleted_at timestamp, False otherwise
        """
        return self.deleted_at is not None

    def format_for_llm(self) -> str:
        """Format message for LLM conversation history.

        Returns:
            Formatted string for LLM context (e.g., "User: Hello")
        """
        role_display = {
            MessageRole.USER: "User",
            MessageRole.ASSISTANT: "Assistant",
            MessageRole.SYSTEM: "System",
        }.get(self.role, self.role.value.capitalize())

        return f"{role_display}: {self.content}"

    def to_dict(self) -> dict[str, Any]:
        """Convert Message to dictionary representation.

        Returns:
            Dictionary with all message fields
        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role.value,
            "content": self.content,
            "tool_result": self.tool_result,
            "whatsapp_message_id": self.whatsapp_message_id,
            "response_time_ms": self.response_time_ms,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
