"""Session entity for conversation session management.

This module defines the Session entity following Domain-Driven Design principles.
Sessions represent conversation contexts between users and the chatbot, with
hybrid lifecycle management (auto-expire + manual control).
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Literal


class SessionStatus(str, Enum):
    """Session status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    CLOSED = "closed"


@dataclass(frozen=True)
class Session:
    """Session entity representing a conversation session.

    This entity is immutable (frozen) following functional programming principles
    and value object patterns. Any modification creates a new Session instance.

    Attributes:
        id: Unique identifier for the session (UUID)
        user_id: Foreign key to User entity
        status: Session status (active, expired, closed)
        created_at: Timestamp when session was created
        last_activity_at: Timestamp of last activity in session
        closed_at: Timestamp when session was closed (None if not closed)
        metadata: Optional metadata for extensibility
        deleted_at: Soft delete timestamp (None if not deleted)
    """

    id: str
    user_id: str
    status: SessionStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate session attributes after initialization.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate ID
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Session ID must be a non-empty string")

        # Validate user_id
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("User ID must be a non-empty string")

        # Validate status
        if not isinstance(self.status, SessionStatus):
            raise ValueError("Status must be a valid SessionStatus")

        # Validate metadata
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime object")
        if not isinstance(self.last_activity_at, datetime):
            raise ValueError("last_activity_at must be a datetime object")
        if self.closed_at is not None and not isinstance(self.closed_at, datetime):
            raise ValueError("closed_at must be a datetime object or None")
        if self.deleted_at is not None and not isinstance(self.deleted_at, datetime):
            raise ValueError("deleted_at must be a datetime object or None")

    @classmethod
    def create(
        cls,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> "Session":
        """Factory method to create a new Session with generated ID and timestamps.

        Args:
            user_id: ID of the user who owns this session
            metadata: Optional metadata dict

        Returns:
            New Session instance with generated ID and timestamps

        Raises:
            ValueError: If validation fails
        """
        now = datetime.now(UTC)
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            last_activity_at=now,
            closed_at=None,
            metadata=metadata,
            deleted_at=None,
        )

    def update_activity(self, timestamp: datetime | None = None) -> "Session":
        """Create a new Session instance with updated last_activity_at timestamp.

        Args:
            timestamp: Timestamp to set (defaults to current UTC time)

        Returns:
            New Session instance with updated last_activity_at

        Raises:
            ValueError: If timestamp is not a datetime object
        """
        new_timestamp = timestamp or datetime.now(UTC)
        if not isinstance(new_timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")

        return Session(
            id=self.id,
            user_id=self.user_id,
            status=self.status,
            created_at=self.created_at,
            last_activity_at=new_timestamp,
            closed_at=self.closed_at,
            metadata=self.metadata,
            deleted_at=self.deleted_at,
        )

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired based on inactivity timeout.

        Args:
            timeout_minutes: Inactivity timeout in minutes (default: 30)

        Returns:
            True if session is expired, False otherwise
        """
        if self.status != SessionStatus.ACTIVE:
            return False

        now = datetime.now(UTC)
        timeout_delta = timedelta(minutes=timeout_minutes)
        return (now - self.last_activity_at) > timeout_delta

    def expire(self) -> "Session":
        """Create a new Session instance marked as expired.

        Returns:
            New Session instance with EXPIRED status
        """
        return Session(
            id=self.id,
            user_id=self.user_id,
            status=SessionStatus.EXPIRED,
            created_at=self.created_at,
            last_activity_at=self.last_activity_at,
            closed_at=self.closed_at,
            metadata=self.metadata,
            deleted_at=self.deleted_at,
        )

    def close(self) -> "Session":
        """Create a new Session instance marked as closed.

        Returns:
            New Session instance with CLOSED status and closed_at timestamp
        """
        return Session(
            id=self.id,
            user_id=self.user_id,
            status=SessionStatus.CLOSED,
            created_at=self.created_at,
            last_activity_at=self.last_activity_at,
            closed_at=datetime.now(UTC),
            metadata=self.metadata,
            deleted_at=self.deleted_at,
        )

    def reactivate(self) -> "Session":
        """Create a new Session instance reactivated from expired state.

        Returns:
            New Session instance with ACTIVE status

        Raises:
            ValueError: If session is closed (cannot reactivate closed sessions)
        """
        if self.status == SessionStatus.CLOSED:
            raise ValueError("Cannot reactivate a closed session")

        return Session(
            id=self.id,
            user_id=self.user_id,
            status=SessionStatus.ACTIVE,
            created_at=self.created_at,
            last_activity_at=datetime.now(UTC),
            closed_at=self.closed_at,
            metadata=self.metadata,
            deleted_at=self.deleted_at,
        )

    def mark_as_deleted(self) -> "Session":
        """Create a new Session instance marked as soft deleted.

        Returns:
            New Session instance with deleted_at timestamp set
        """
        return Session(
            id=self.id,
            user_id=self.user_id,
            status=self.status,
            created_at=self.created_at,
            last_activity_at=self.last_activity_at,
            closed_at=self.closed_at,
            metadata=self.metadata,
            deleted_at=datetime.now(UTC),
        )

    @property
    def is_active(self) -> bool:
        """Check if session is in active status.

        Returns:
            True if session status is ACTIVE, False otherwise
        """
        return self.status == SessionStatus.ACTIVE

    @property
    def is_closed(self) -> bool:
        """Check if session is in closed status.

        Returns:
            True if session status is CLOSED, False otherwise
        """
        return self.status == SessionStatus.CLOSED

    @property
    def is_deleted(self) -> bool:
        """Check if session is soft deleted.

        Returns:
            True if session has a deleted_at timestamp, False otherwise
        """
        return self.deleted_at is not None

    def can_receive_messages(self) -> bool:
        """Check if session can receive new messages.

        Returns:
            True if session is active or expired (can auto-reactivate),
            False if session is closed
        """
        return self.status != SessionStatus.CLOSED

    def to_dict(self) -> dict[str, Any]:
        """Convert Session to dictionary representation.

        Returns:
            Dictionary with all session fields
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "metadata": self.metadata,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
