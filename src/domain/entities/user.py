"""User entity for WhatsApp chatbot user management.

This module defines the User entity following Domain-Driven Design principles.
Users are identified by WhatsApp phone numbers and support preferences for
personalized conversation experiences.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class User:
    """User entity representing a WhatsApp user.

    This entity is immutable (frozen) following functional programming principles
    and value object patterns. Any modification creates a new User instance.

    Attributes:
        id: Unique identifier for the user (UUID)
        phone_number: WhatsApp phone number (E.164 format, unique identifier)
        display_name: Optional display name for the user
        preferences: User preferences for conversation agent (stored as dict)
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        last_active_at: Timestamp of last user activity
        deleted_at: Soft delete timestamp (None if not deleted)
    """

    id: str
    phone_number: str
    display_name: str | None = None
    preferences: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate user attributes after initialization.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate ID
        if not self.id or not isinstance(self.id, str):
            raise ValueError("User ID must be a non-empty string")

        # Validate phone_number
        if not isinstance(self.phone_number, str):
            raise ValueError("Phone number must be a string")
        if not self.phone_number.strip():
            raise ValueError("Phone number cannot be empty or whitespace")
        if len(self.phone_number) > 50:
            raise ValueError("Phone number cannot exceed 50 characters")

        # Validate display_name
        if self.display_name is not None:
            if not isinstance(self.display_name, str):
                raise ValueError("Display name must be a string")
            if len(self.display_name) > 255:
                raise ValueError("Display name cannot exceed 255 characters")

        # Validate preferences
        if self.preferences is not None and not isinstance(self.preferences, dict):
            raise ValueError("Preferences must be a dictionary")

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime object")
        if not isinstance(self.updated_at, datetime):
            raise ValueError("updated_at must be a datetime object")
        if not isinstance(self.last_active_at, datetime):
            raise ValueError("last_active_at must be a datetime object")
        if self.deleted_at is not None and not isinstance(self.deleted_at, datetime):
            raise ValueError("deleted_at must be a datetime object or None")

    @classmethod
    def create(
        cls,
        phone_number: str,
        display_name: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> "User":
        """Factory method to create a new User with generated ID and timestamps.

        Args:
            phone_number: WhatsApp phone number (E.164 format recommended)
            display_name: Optional display name
            preferences: Optional user preferences dict

        Returns:
            New User instance with generated ID and timestamps

        Raises:
            ValueError: If validation fails
        """
        now = datetime.now(UTC)
        return cls(
            id=str(uuid.uuid4()),
            phone_number=phone_number.strip(),
            display_name=display_name.strip() if display_name else None,
            preferences=preferences,
            created_at=now,
            updated_at=now,
            last_active_at=now,
            deleted_at=None,
        )

    def update(
        self,
        display_name: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> "User":
        """Create a new User instance with updated fields.

        Since User is immutable, this returns a new instance with updated values
        and a new updated_at timestamp.

        Args:
            display_name: New display name (if provided)
            preferences: New preferences dict (if provided)

        Returns:
            New User instance with updated fields

        Raises:
            ValueError: If validation fails
        """
        return User(
            id=self.id,
            phone_number=self.phone_number,
            display_name=(
                display_name.strip() if display_name is not None else self.display_name
            ),
            preferences=preferences if preferences is not None else self.preferences,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            last_active_at=self.last_active_at,
            deleted_at=self.deleted_at,
        )

    def update_last_active(self, timestamp: datetime | None = None) -> "User":
        """Create a new User instance with updated last_active_at timestamp.

        Args:
            timestamp: Timestamp to set (defaults to current UTC time)

        Returns:
            New User instance with updated last_active_at

        Raises:
            ValueError: If timestamp is not a datetime object
        """
        new_timestamp = timestamp or datetime.now(UTC)
        if not isinstance(new_timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")

        return User(
            id=self.id,
            phone_number=self.phone_number,
            display_name=self.display_name,
            preferences=self.preferences,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            last_active_at=new_timestamp,
            deleted_at=self.deleted_at,
        )

    def mark_as_deleted(self) -> "User":
        """Create a new User instance marked as soft deleted.

        Returns:
            New User instance with deleted_at timestamp set
        """
        return User(
            id=self.id,
            phone_number=self.phone_number,
            display_name=self.display_name,
            preferences=self.preferences,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            last_active_at=self.last_active_at,
            deleted_at=datetime.now(UTC),
        )

    @property
    def is_deleted(self) -> bool:
        """Check if user is soft deleted.

        Returns:
            True if user has a deleted_at timestamp, False otherwise
        """
        return self.deleted_at is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert User to dictionary representation.

        Returns:
            Dictionary with all user fields
        """
        return {
            "id": self.id,
            "phone_number": self.phone_number,
            "display_name": self.display_name,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat(),
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
