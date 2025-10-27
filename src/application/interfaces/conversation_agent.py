"""Conversation Agent Interface.

This module defines the abstract interface for conversation agents following
the Dependency Inversion Principle (DIP) from SOLID principles.

Note: We use Protocol instead of ABC to avoid metaclass conflicts with DSPy.Module
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Message:
    """Immutable message representation in conversation history.

    Attributes:
        role: The role of the message sender (user, assistant, system)
        content: The message content
        metadata: Optional metadata for the message (timestamps, etc.)
    """

    role: str
    content: str
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate message fields."""
        if not self.role:
            raise ValueError("Message role cannot be empty")
        if not self.content:
            raise ValueError("Message content cannot be empty")
        if self.role not in {"user", "assistant", "system"}:
            raise ValueError(f"Invalid role: {self.role}. Must be 'user', 'assistant', or 'system'")


@dataclass(frozen=True)
class ConversationContext:
    """Immutable conversation context for agent processing.

    Attributes:
        current_message: The current user message to process
        history: Previous conversation history (ordered from oldest to newest)
        metadata: Optional context metadata (user_id, session_id, etc.)
    """

    current_message: str
    history: tuple[Message, ...] = ()
    user_preference:str|None=None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate conversation context."""
        if not self.current_message:
            raise ValueError("Current message cannot be empty")


@dataclass(frozen=True)
class AgentResponse:
    """Immutable agent response.

    Attributes:
        content: The generated response content
        reasoning: Optional chain-of-thought reasoning (if available)
        metadata: Optional response metadata (model info, tokens used, etc.)
    """

    content: str
    reasoning: str | None = None
    metadata: dict[str, Any] | None = None
    trajectory:dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate agent response."""
        if not self.content:
            raise ValueError("Response content cannot be empty")


@runtime_checkable
class IConversationAgent(Protocol):
    """Protocol interface for conversation agents.

    This interface defines the contract that all conversation agent implementations
    must follow, enabling dependency inversion and testability.

    Using Protocol instead of ABC to avoid metaclass conflicts with DSPy.Module.
    """

    def generate_response(self, context: ConversationContext) -> AgentResponse:
        """Generate a response based on conversation context.

        Args:
            context: The conversation context containing current message and history

        Returns:
            AgentResponse containing the generated response and optional metadata

        Raises:
            ValueError: If the context is invalid
            RuntimeError: If response generation fails
        """
        ...

    def configure(self, **kwargs: Any) -> None:
        """Configure the agent with runtime parameters.

        Args:
            **kwargs: Configuration parameters (temperature, max_tokens, etc.)

        Raises:
            ValueError: If configuration parameters are invalid
        """
        ...
