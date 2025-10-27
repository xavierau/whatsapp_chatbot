"""Unit tests for Message entity."""

import uuid
from datetime import UTC, datetime

import pytest

from src.domain.entities.message import Message, MessageRole


class TestMessageCreation:
    """Test Message.create factory method."""

    def test_create_user_message(self) -> None:
        """Test creating a user message."""
        session_id = str(uuid.uuid4())
        content = "Hello, how are you?"

        message = Message.create(
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
        )

        assert message.id is not None
        assert uuid.UUID(message.id)  # Valid UUID
        assert message.session_id == session_id
        assert message.role == MessageRole.USER
        assert message.content == content
        assert message.tool_result is None
        assert message.whatsapp_message_id is None
        assert message.response_time_ms is None
        assert isinstance(message.created_at, datetime)
        assert message.metadata is None
        assert message.deleted_at is None

    def test_create_assistant_message_with_tool_result(self) -> None:
        """Test creating assistant message with tool result."""
        session_id = str(uuid.uuid4())
        content = "The answer is 42"
        tool_result = {
            "tool_calls": [
                {
                    "tool": "compute",
                    "input": "calculate 40+2",
                    "output": "42",
                    "execution_time_ms": 120,
                }
            ]
        }

        message = Message.create(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content,
            tool_result=tool_result,
            response_time_ms=1500,
        )

        assert message.role == MessageRole.ASSISTANT
        assert message.tool_result == tool_result
        assert message.response_time_ms == 1500

    def test_create_message_with_whatsapp_id(self) -> None:
        """Test creating message with WhatsApp message ID."""
        session_id = str(uuid.uuid4())
        whatsapp_id = "wamid.HBgLMTIzNDU2Nzg5MAA=="

        message = Message.create(
            session_id=session_id,
            role=MessageRole.USER,
            content="Test message",
            whatsapp_message_id=whatsapp_id,
        )

        assert message.whatsapp_message_id == whatsapp_id

    def test_create_system_message(self) -> None:
        """Test creating a system message."""
        session_id = str(uuid.uuid4())
        content = "Context information injected"

        message = Message.create(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=content,
        )

        assert message.role == MessageRole.SYSTEM

    def test_create_message_strips_whitespace(self) -> None:
        """Test that content is stripped of leading/trailing whitespace."""
        session_id = str(uuid.uuid4())

        message = Message.create(
            session_id=session_id,
            role=MessageRole.USER,
            content="  Hello World  ",
        )

        assert message.content == "Hello World"

    def test_create_message_with_metadata(self) -> None:
        """Test creating message with metadata."""
        session_id = str(uuid.uuid4())
        metadata = {"model": "gemini-2.5-flash", "temperature": 0.7}

        message = Message.create(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="Response",
            metadata=metadata,
        )

        assert message.metadata == metadata


class TestMessageValidation:
    """Test Message entity validation rules."""

    def test_id_must_be_non_empty_string(self) -> None:
        """Test that id must be a non-empty string."""
        with pytest.raises(ValueError, match="Message ID must be a non-empty string"):
            Message(
                id="",
                session_id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content="Test",
                created_at=datetime.now(UTC),
            )

    def test_session_id_must_be_non_empty_string(self) -> None:
        """Test that session_id must be a non-empty string."""
        with pytest.raises(ValueError, match="Session ID must be a non-empty string"):
            Message(
                id=str(uuid.uuid4()),
                session_id="",
                role=MessageRole.USER,
                content="Test",
                created_at=datetime.now(UTC),
            )

    def test_role_must_be_valid_message_role(self) -> None:
        """Test that role must be a valid MessageRole."""
        with pytest.raises(ValueError, match="Role must be a valid MessageRole"):
            Message(
                id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                role="invalid",  # type: ignore
                content="Test",
                created_at=datetime.now(UTC),
            )

    def test_content_cannot_be_empty(self) -> None:
        """Test that content cannot be empty."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            Message.create(
                session_id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content="",
            )

    def test_content_cannot_be_whitespace(self) -> None:
        """Test that content cannot be only whitespace."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            Message.create(
                session_id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content="   ",
            )

    def test_content_must_be_string(self) -> None:
        """Test that content must be a string."""
        with pytest.raises(ValueError, match="Content must be a string"):
            Message(
                id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content=123,  # type: ignore
                created_at=datetime.now(UTC),
            )

    def test_tool_result_must_be_dict_if_provided(self) -> None:
        """Test that tool_result must be a dict when provided."""
        with pytest.raises(ValueError, match="Tool result must be a dictionary"):
            Message(
                id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content="Test",
                tool_result="invalid",  # type: ignore
                created_at=datetime.now(UTC),
            )

    def test_whatsapp_message_id_must_be_string_if_provided(self) -> None:
        """Test that whatsapp_message_id must be a string when provided."""
        with pytest.raises(ValueError, match="WhatsApp message ID must be a string"):
            Message(
                id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content="Test",
                whatsapp_message_id=123,  # type: ignore
                created_at=datetime.now(UTC),
            )

    def test_whatsapp_message_id_max_length(self) -> None:
        """Test that whatsapp_message_id cannot exceed 255 characters."""
        long_id = "x" * 300
        with pytest.raises(ValueError, match="WhatsApp message ID cannot exceed 255 characters"):
            Message.create(
                session_id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content="Test",
                whatsapp_message_id=long_id,
            )

    def test_response_time_ms_must_be_positive_if_provided(self) -> None:
        """Test that response_time_ms must be positive when provided."""
        with pytest.raises(ValueError, match="Response time must be a positive integer"):
            Message.create(
                session_id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content="Test",
                response_time_ms=-100,
            )

    def test_response_time_ms_must_be_int_if_provided(self) -> None:
        """Test that response_time_ms must be an integer when provided."""
        with pytest.raises(ValueError, match="Response time must be an integer"):
            Message(
                id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content="Test",
                response_time_ms="invalid",  # type: ignore
                created_at=datetime.now(UTC),
            )

    def test_metadata_must_be_dict_if_provided(self) -> None:
        """Test that metadata must be a dict when provided."""
        with pytest.raises(ValueError, match="Metadata must be a dictionary"):
            Message(
                id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content="Test",
                metadata="invalid",  # type: ignore
                created_at=datetime.now(UTC),
            )

    def test_created_at_must_be_datetime(self) -> None:
        """Test that created_at must be a datetime object."""
        with pytest.raises(ValueError, match="created_at must be a datetime object"):
            Message(
                id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content="Test",
                created_at="2025-01-01",  # type: ignore
            )

    def test_deleted_at_can_be_none(self) -> None:
        """Test that deleted_at can be None."""
        message = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content="Test",
        )
        assert message.deleted_at is None


class TestMessageImmutability:
    """Test that Message entity is immutable."""

    def test_message_is_frozen(self) -> None:
        """Test that Message cannot be modified after creation."""
        message = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content="Test",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            message.content = "Modified"  # type: ignore


class TestMessageRoles:
    """Test Message role helper properties."""

    def test_is_user_message(self) -> None:
        """Test is_user_message property."""
        user_msg = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content="Test",
        )
        assistant_msg = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content="Response",
        )

        assert user_msg.is_user_message is True
        assert assistant_msg.is_user_message is False

    def test_is_assistant_message(self) -> None:
        """Test is_assistant_message property."""
        user_msg = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content="Test",
        )
        assistant_msg = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content="Response",
        )

        assert user_msg.is_assistant_message is False
        assert assistant_msg.is_assistant_message is True

    def test_is_system_message(self) -> None:
        """Test is_system_message property."""
        system_msg = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.SYSTEM,
            content="System info",
        )
        user_msg = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content="Test",
        )

        assert system_msg.is_system_message is True
        assert user_msg.is_system_message is False

    def test_has_tool_result(self) -> None:
        """Test has_tool_result property."""
        msg_without_tool = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content="Response",
        )
        msg_with_tool = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content="Response",
            tool_result={"tool": "compute", "result": "42"},
        )

        assert msg_without_tool.has_tool_result is False
        assert msg_with_tool.has_tool_result is True


class TestMessageSoftDelete:
    """Test Message soft delete functionality."""

    def test_mark_as_deleted(self) -> None:
        """Test marking message as deleted."""
        message = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content="Test",
        )
        deleted = message.mark_as_deleted()

        assert deleted.deleted_at is not None
        assert isinstance(deleted.deleted_at, datetime)
        assert deleted.id == message.id
        assert deleted.content == message.content

    def test_is_deleted_property(self) -> None:
        """Test is_deleted property."""
        message = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content="Test",
        )
        assert message.is_deleted is False

        deleted = message.mark_as_deleted()
        assert deleted.is_deleted is True


class TestMessageDict:
    """Test Message.to_dict method."""

    def test_to_dict_minimal_fields(self) -> None:
        """Test to_dict with only required fields."""
        session_id = str(uuid.uuid4())
        message = Message.create(
            session_id=session_id,
            role=MessageRole.USER,
            content="Test message",
        )
        msg_dict = message.to_dict()

        assert msg_dict["id"] == message.id
        assert msg_dict["session_id"] == session_id
        assert msg_dict["role"] == "user"
        assert msg_dict["content"] == "Test message"
        assert msg_dict["tool_result"] is None
        assert msg_dict["whatsapp_message_id"] is None
        assert msg_dict["response_time_ms"] is None
        assert "created_at" in msg_dict
        assert msg_dict["metadata"] is None
        assert msg_dict["deleted_at"] is None

    def test_to_dict_all_fields(self) -> None:
        """Test to_dict with all fields populated."""
        session_id = str(uuid.uuid4())
        tool_result = {"tool": "compute", "result": "42"}
        metadata = {"model": "gemini"}

        message = Message.create(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="The answer is 42",
            tool_result=tool_result,
            whatsapp_message_id="wamid.123",
            response_time_ms=1200,
            metadata=metadata,
        )
        msg_dict = message.to_dict()

        assert msg_dict["role"] == "assistant"
        assert msg_dict["tool_result"] == tool_result
        assert msg_dict["whatsapp_message_id"] == "wamid.123"
        assert msg_dict["response_time_ms"] == 1200
        assert msg_dict["metadata"] == metadata

    def test_to_dict_iso_format_timestamp(self) -> None:
        """Test that created_at is ISO formatted string."""
        message = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content="Test",
        )
        msg_dict = message.to_dict()

        # Should be valid ISO format string
        datetime.fromisoformat(msg_dict["created_at"])


class TestMessageForConversationHistory:
    """Test Message formatting for conversation history."""

    def test_format_for_llm_user_message(self) -> None:
        """Test formatting user message for LLM context."""
        message = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content="What is 2+2?",
        )
        formatted = message.format_for_llm()

        assert "User:" in formatted
        assert "What is 2+2?" in formatted

    def test_format_for_llm_assistant_message(self) -> None:
        """Test formatting assistant message for LLM context."""
        message = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content="The answer is 4",
        )
        formatted = message.format_for_llm()

        assert "Assistant:" in formatted
        assert "The answer is 4" in formatted

    def test_format_for_llm_system_message(self) -> None:
        """Test formatting system message for LLM context."""
        message = Message.create(
            session_id=str(uuid.uuid4()),
            role=MessageRole.SYSTEM,
            content="Context loaded",
        )
        formatted = message.format_for_llm()

        assert "System:" in formatted
        assert "Context loaded" in formatted
