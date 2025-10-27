"""Unit tests for User entity."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities.user import User


class TestUserCreation:
    """Test User.create factory method."""

    def test_create_user_with_required_fields(self) -> None:
        """Test creating user with only required fields."""
        phone = "+1234567890"
        user = User.create(phone_number=phone)

        assert user.id is not None
        assert uuid.UUID(user.id)  # Valid UUID
        assert user.phone_number == phone
        assert user.display_name is None
        assert user.preferences is None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        assert isinstance(user.last_active_at, datetime)
        assert user.deleted_at is None

    def test_create_user_with_all_fields(self) -> None:
        """Test creating user with all optional fields."""
        phone = "+1234567890"
        display_name = "John Doe"
        preferences = {"language": "en", "theme": "dark"}

        user = User.create(
            phone_number=phone,
            display_name=display_name,
            preferences=preferences,
        )

        assert user.phone_number == phone
        assert user.display_name == display_name
        assert user.preferences == preferences

    def test_create_user_strips_whitespace(self) -> None:
        """Test that phone number and display name are stripped."""
        user = User.create(
            phone_number="  +1234567890  ",
            display_name="  John Doe  ",
        )

        assert user.phone_number == "+1234567890"
        assert user.display_name == "John Doe"

    def test_create_user_with_empty_preferences(self) -> None:
        """Test creating user with empty preferences dict."""
        user = User.create(phone_number="+1234567890", preferences={})

        assert user.preferences == {}


class TestUserValidation:
    """Test User entity validation rules."""

    def test_phone_number_required(self) -> None:
        """Test that phone_number cannot be empty."""
        with pytest.raises(ValueError, match="Phone number cannot be empty"):
            User.create(phone_number="")

    def test_phone_number_cannot_be_whitespace(self) -> None:
        """Test that phone_number cannot be only whitespace."""
        with pytest.raises(ValueError, match="Phone number cannot be empty"):
            User.create(phone_number="   ")

    def test_phone_number_must_be_string(self) -> None:
        """Test that phone_number must be a string."""
        with pytest.raises(ValueError, match="Phone number must be a string"):
            User(
                id=str(uuid.uuid4()),
                phone_number=123,  # type: ignore
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                last_active_at=datetime.now(UTC),
            )

    def test_phone_number_max_length(self) -> None:
        """Test that phone_number cannot exceed 50 characters."""
        long_phone = "+" + "1" * 60
        with pytest.raises(ValueError, match="Phone number cannot exceed 50 characters"):
            User.create(phone_number=long_phone)

    def test_display_name_must_be_string_if_provided(self) -> None:
        """Test that display_name must be a string when provided."""
        with pytest.raises(ValueError, match="Display name must be a string"):
            User(
                id=str(uuid.uuid4()),
                phone_number="+1234567890",
                display_name=123,  # type: ignore
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                last_active_at=datetime.now(UTC),
            )

    def test_display_name_max_length(self) -> None:
        """Test that display_name cannot exceed 255 characters."""
        long_name = "A" * 300
        with pytest.raises(ValueError, match="Display name cannot exceed 255 characters"):
            User.create(phone_number="+1234567890", display_name=long_name)

    def test_display_name_can_be_none(self) -> None:
        """Test that display_name can be None."""
        user = User.create(phone_number="+1234567890", display_name=None)
        assert user.display_name is None

    def test_preferences_must_be_dict_if_provided(self) -> None:
        """Test that preferences must be a dict when provided."""
        with pytest.raises(ValueError, match="Preferences must be a dictionary"):
            User(
                id=str(uuid.uuid4()),
                phone_number="+1234567890",
                preferences="invalid",  # type: ignore
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                last_active_at=datetime.now(UTC),
            )

    def test_id_must_be_non_empty_string(self) -> None:
        """Test that id must be a non-empty string."""
        with pytest.raises(ValueError, match="User ID must be a non-empty string"):
            User(
                id="",
                phone_number="+1234567890",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                last_active_at=datetime.now(UTC),
            )

    def test_timestamps_must_be_datetime_objects(self) -> None:
        """Test that all timestamps must be datetime objects."""
        with pytest.raises(ValueError, match="created_at must be a datetime object"):
            User(
                id=str(uuid.uuid4()),
                phone_number="+1234567890",
                created_at="2025-01-01",  # type: ignore
                updated_at=datetime.now(UTC),
                last_active_at=datetime.now(UTC),
            )

    def test_deleted_at_can_be_none(self) -> None:
        """Test that deleted_at can be None."""
        user = User.create(phone_number="+1234567890")
        assert user.deleted_at is None


class TestUserImmutability:
    """Test that User entity is immutable."""

    def test_user_is_frozen(self) -> None:
        """Test that User cannot be modified after creation."""
        user = User.create(phone_number="+1234567890")

        with pytest.raises(Exception):  # FrozenInstanceError
            user.phone_number = "+9876543210"  # type: ignore

    def test_update_creates_new_instance(self) -> None:
        """Test that update() returns a new User instance."""
        user = User.create(phone_number="+1234567890", display_name="John")
        updated_user = user.update(display_name="Jane")

        assert user is not updated_user
        assert user.id == updated_user.id
        assert user.display_name == "John"
        assert updated_user.display_name == "Jane"


class TestUserUpdate:
    """Test User.update method."""

    def test_update_display_name(self) -> None:
        """Test updating display name."""
        user = User.create(phone_number="+1234567890", display_name="John")
        updated = user.update(display_name="Jane")

        assert updated.display_name == "Jane"
        assert updated.phone_number == user.phone_number
        assert updated.id == user.id
        assert updated.updated_at > user.updated_at

    def test_update_preferences(self) -> None:
        """Test updating preferences."""
        user = User.create(phone_number="+1234567890", preferences={"theme": "light"})
        new_prefs = {"theme": "dark", "language": "en"}
        updated = user.update(preferences=new_prefs)

        assert updated.preferences == new_prefs
        assert user.preferences == {"theme": "light"}

    def test_update_strips_whitespace(self) -> None:
        """Test that update strips whitespace from display_name."""
        user = User.create(phone_number="+1234567890")
        updated = user.update(display_name="  Jane Doe  ")

        assert updated.display_name == "Jane Doe"

    def test_update_with_none_keeps_original(self) -> None:
        """Test that passing None doesn't change the field."""
        user = User.create(
            phone_number="+1234567890",
            display_name="John",
            preferences={"theme": "light"},
        )
        updated = user.update(display_name=None, preferences=None)

        assert updated.display_name == "John"
        assert updated.preferences == {"theme": "light"}

    def test_update_last_active(self) -> None:
        """Test updating last_active_at timestamp."""
        user = User.create(phone_number="+1234567890")
        original_last_active = user.last_active_at

        new_timestamp = datetime.now(UTC) + timedelta(hours=1)
        updated = user.update_last_active(new_timestamp)

        assert updated.last_active_at == new_timestamp
        assert updated.last_active_at > original_last_active
        assert updated.updated_at > user.updated_at


class TestUserSoftDelete:
    """Test User soft delete functionality."""

    def test_mark_as_deleted(self) -> None:
        """Test marking user as deleted."""
        user = User.create(phone_number="+1234567890")
        deleted = user.mark_as_deleted()

        assert deleted.deleted_at is not None
        assert isinstance(deleted.deleted_at, datetime)
        assert deleted.id == user.id
        assert deleted.phone_number == user.phone_number

    def test_is_deleted_property(self) -> None:
        """Test is_deleted property."""
        user = User.create(phone_number="+1234567890")
        assert user.is_deleted is False

        deleted = user.mark_as_deleted()
        assert deleted.is_deleted is True


class TestUserDict:
    """Test User.to_dict method."""

    def test_to_dict_with_minimal_fields(self) -> None:
        """Test to_dict with only required fields."""
        user = User.create(phone_number="+1234567890")
        user_dict = user.to_dict()

        assert user_dict["id"] == user.id
        assert user_dict["phone_number"] == "+1234567890"
        assert user_dict["display_name"] is None
        assert user_dict["preferences"] is None
        assert "created_at" in user_dict
        assert "updated_at" in user_dict
        assert "last_active_at" in user_dict
        assert user_dict["deleted_at"] is None

    def test_to_dict_with_all_fields(self) -> None:
        """Test to_dict with all fields populated."""
        user = User.create(
            phone_number="+1234567890",
            display_name="John Doe",
            preferences={"theme": "dark"},
        )
        user_dict = user.to_dict()

        assert user_dict["display_name"] == "John Doe"
        assert user_dict["preferences"] == {"theme": "dark"}

    def test_to_dict_iso_format_timestamps(self) -> None:
        """Test that timestamps are ISO formatted strings."""
        user = User.create(phone_number="+1234567890")
        user_dict = user.to_dict()

        # Should be valid ISO format strings
        datetime.fromisoformat(user_dict["created_at"])
        datetime.fromisoformat(user_dict["updated_at"])
        datetime.fromisoformat(user_dict["last_active_at"])
