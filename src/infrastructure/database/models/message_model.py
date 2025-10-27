"""SQLAlchemy Message model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.entities.message import MessageRole
from src.infrastructure.database.models.user_model import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.session_model import SessionModel


class MessageModel(Base):
    """SQLAlchemy model for conversation messages.

    This model represents individual messages with support for tool
    results, LLM performance tracking, and soft deletes.
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole, name="message_role", create_type=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    whatsapp_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    message_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )

    # Relationships
    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="messages")

    def __repr__(self) -> str:
        """String representation of message."""
        content_preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<Message(id='{self.id}', role='{self.role.value}', content='{content_preview}')>"
