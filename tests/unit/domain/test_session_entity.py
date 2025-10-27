"""Unit tests for Session entity."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import pytest

from src.domain.entities.session import Session, SessionStatus


class TestSessionCreation:
    """Test Session.create factory method."""

    def test_create_session_with_required_fields(self) -> None:
        """Test creating session with only required fields."""
        user_id = str(uuid.uuid4())
        session = Session.create(user_id=user_id)

        assert session.id is not None
        assert uuid.UUID(session.id)  # Valid UUID
        assert session.user_id == user_id
        assert session.status == SessionStatus.ACTIVE
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity_at, datetime)
        assert session.closed_at is None
        assert session.metadata is None
        assert session.deleted_at is None

    def test_create_session_with_metadata(self) -> None:
        """Test creating session with metadata."""
        user_id = str(uuid.uuid4())
        metadata = {"source": "whatsapp", "language": "en"}
        session = Session.create(user_id=user_id, metadata=metadata)

        assert session.metadata == metadata

    def test_create_session_with_empty_metadata(self) -> None:
        """Test creating session with empty metadata dict."""
        user_id = str(uuid.uuid4())
        session = Session.create(user_id=user_id, metadata={})

        assert session.metadata == {}

    def test_created_at_and_last_activity_at_are_same(self) -> None:
        """Test that created_at and last_activity_at are initially the same."""
        user_id = str(uuid.uuid4())
        session = Session.create(user_id=user_id)

        # Should be very close in time (within 1 second)
        time_diff = abs((session.created_at - session.last_activity_at).total_seconds())
        assert time_diff < 1


class TestSessionValidation:
    """Test Session entity validation rules."""

    def test_id_must_be_non_empty_string(self) -> None:
        """Test that id must be a non-empty string."""
        with pytest.raises(ValueError, match="Session ID must be a non-empty string"):
            Session(
                id="",
                user_id=str(uuid.uuid4()),
                status=SessionStatus.ACTIVE,
                created_at=datetime.now(UTC),
                last_activity_at=datetime.now(UTC),
            )

    def test_user_id_must_be_non_empty_string(self) -> None:
        """Test that user_id must be a non-empty string."""
        with pytest.raises(ValueError, match="User ID must be a non-empty string"):
            Session(
                id=str(uuid.uuid4()),
                user_id="",
                status=SessionStatus.ACTIVE,
                created_at=datetime.now(UTC),
                last_activity_at=datetime.now(UTC),
            )

    def test_status_must_be_valid_session_status(self) -> None:
        """Test that status must be a valid SessionStatus."""
        with pytest.raises(ValueError, match="Status must be a valid SessionStatus"):
            Session(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                status="invalid",  # type: ignore
                created_at=datetime.now(UTC),
                last_activity_at=datetime.now(UTC),
            )

    def test_metadata_must_be_dict_if_provided(self) -> None:
        """Test that metadata must be a dict when provided."""
        with pytest.raises(ValueError, match="Metadata must be a dictionary"):
            Session(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                status=SessionStatus.ACTIVE,
                metadata="invalid",  # type: ignore
                created_at=datetime.now(UTC),
                last_activity_at=datetime.now(UTC),
            )

    def test_timestamps_must_be_datetime_objects(self) -> None:
        """Test that all timestamps must be datetime objects."""
        with pytest.raises(ValueError, match="created_at must be a datetime object"):
            Session(
                id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                status=SessionStatus.ACTIVE,
                created_at="2025-01-01",  # type: ignore
                last_activity_at=datetime.now(UTC),
            )

    def test_closed_at_can_be_none(self) -> None:
        """Test that closed_at can be None."""
        session = Session.create(user_id=str(uuid.uuid4()))
        assert session.closed_at is None

    def test_deleted_at_can_be_none(self) -> None:
        """Test that deleted_at can be None."""
        session = Session.create(user_id=str(uuid.uuid4()))
        assert session.deleted_at is None


class TestSessionImmutability:
    """Test that Session entity is immutable."""

    def test_session_is_frozen(self) -> None:
        """Test that Session cannot be modified after creation."""
        session = Session.create(user_id=str(uuid.uuid4()))

        with pytest.raises(Exception):  # FrozenInstanceError
            session.status = SessionStatus.CLOSED  # type: ignore

    def test_update_creates_new_instance(self) -> None:
        """Test that update methods return a new Session instance."""
        session = Session.create(user_id=str(uuid.uuid4()))
        updated_session = session.update_activity()

        assert session is not updated_session
        assert session.id == updated_session.id
        assert session.user_id == updated_session.user_id


class TestSessionActivity:
    """Test Session activity tracking."""

    def test_update_activity(self) -> None:
        """Test updating last_activity_at timestamp."""
        session = Session.create(user_id=str(uuid.uuid4()))
        original_activity = session.last_activity_at

        # Wait a tiny bit to ensure timestamp difference
        import time

        time.sleep(0.01)

        updated = session.update_activity()

        assert updated.last_activity_at > original_activity
        assert updated.id == session.id
        assert updated.status == session.status

    def test_update_activity_with_custom_timestamp(self) -> None:
        """Test updating activity with a custom timestamp."""
        session = Session.create(user_id=str(uuid.uuid4()))
        custom_time = datetime.now(UTC) + timedelta(hours=1)

        updated = session.update_activity(custom_time)

        assert updated.last_activity_at == custom_time

    def test_is_expired_returns_false_for_recent_activity(self) -> None:
        """Test that recently active session is not expired."""
        session = Session.create(user_id=str(uuid.uuid4()))

        assert session.is_expired(timeout_minutes=30) is False

    def test_is_expired_returns_true_for_old_activity(self) -> None:
        """Test that session with old activity is expired."""
        user_id = str(uuid.uuid4())
        old_time = datetime.now(UTC) - timedelta(minutes=45)

        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            created_at=old_time,
            last_activity_at=old_time,
        )

        assert session.is_expired(timeout_minutes=30) is True

    def test_is_expired_with_different_timeout(self) -> None:
        """Test is_expired with different timeout values."""
        user_id = str(uuid.uuid4())
        old_time = datetime.now(UTC) - timedelta(minutes=15)

        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            created_at=old_time,
            last_activity_at=old_time,
        )

        assert session.is_expired(timeout_minutes=10) is True
        assert session.is_expired(timeout_minutes=20) is False


class TestSessionLifecycle:
    """Test Session lifecycle state transitions."""

    def test_expire_session(self) -> None:
        """Test expiring an active session."""
        session = Session.create(user_id=str(uuid.uuid4()))
        expired = session.expire()

        assert expired.status == SessionStatus.EXPIRED
        assert expired.id == session.id
        assert session.status == SessionStatus.ACTIVE

    def test_close_session(self) -> None:
        """Test closing a session."""
        session = Session.create(user_id=str(uuid.uuid4()))
        closed = session.close()

        assert closed.status == SessionStatus.CLOSED
        assert closed.closed_at is not None
        assert isinstance(closed.closed_at, datetime)
        assert closed.id == session.id
        assert session.closed_at is None

    def test_reactivate_expired_session(self) -> None:
        """Test reactivating an expired session."""
        session = Session.create(user_id=str(uuid.uuid4()))
        expired = session.expire()
        reactivated = expired.reactivate()

        assert reactivated.status == SessionStatus.ACTIVE
        assert reactivated.id == session.id
        assert expired.status == SessionStatus.EXPIRED

    def test_is_active_property(self) -> None:
        """Test is_active property for different statuses."""
        session = Session.create(user_id=str(uuid.uuid4()))
        assert session.is_active is True

        expired = session.expire()
        assert expired.is_active is False

        closed = session.close()
        assert closed.is_active is False

    def test_is_closed_property(self) -> None:
        """Test is_closed property."""
        session = Session.create(user_id=str(uuid.uuid4()))
        assert session.is_closed is False

        closed = session.close()
        assert closed.is_closed is True

    def test_can_receive_messages_active_session(self) -> None:
        """Test that active sessions can receive messages."""
        session = Session.create(user_id=str(uuid.uuid4()))
        assert session.can_receive_messages() is True

    def test_can_receive_messages_expired_session(self) -> None:
        """Test that expired sessions can receive messages (auto-reactivate)."""
        session = Session.create(user_id=str(uuid.uuid4()))
        expired = session.expire()
        assert expired.can_receive_messages() is True

    def test_can_receive_messages_closed_session(self) -> None:
        """Test that closed sessions cannot receive messages."""
        session = Session.create(user_id=str(uuid.uuid4()))
        closed = session.close()
        assert closed.can_receive_messages() is False


class TestSessionSoftDelete:
    """Test Session soft delete functionality."""

    def test_mark_as_deleted(self) -> None:
        """Test marking session as deleted."""
        session = Session.create(user_id=str(uuid.uuid4()))
        deleted = session.mark_as_deleted()

        assert deleted.deleted_at is not None
        assert isinstance(deleted.deleted_at, datetime)
        assert deleted.id == session.id

    def test_is_deleted_property(self) -> None:
        """Test is_deleted property."""
        session = Session.create(user_id=str(uuid.uuid4()))
        assert session.is_deleted is False

        deleted = session.mark_as_deleted()
        assert deleted.is_deleted is True


class TestSessionDict:
    """Test Session.to_dict method."""

    def test_to_dict_with_minimal_fields(self) -> None:
        """Test to_dict with only required fields."""
        user_id = str(uuid.uuid4())
        session = Session.create(user_id=user_id)
        session_dict = session.to_dict()

        assert session_dict["id"] == session.id
        assert session_dict["user_id"] == user_id
        assert session_dict["status"] == "active"
        assert "created_at" in session_dict
        assert "last_activity_at" in session_dict
        assert session_dict["closed_at"] is None
        assert session_dict["metadata"] is None
        assert session_dict["deleted_at"] is None

    def test_to_dict_with_all_fields(self) -> None:
        """Test to_dict with all fields populated."""
        user_id = str(uuid.uuid4())
        metadata = {"source": "whatsapp"}
        session = Session.create(user_id=user_id, metadata=metadata)
        closed = session.close()
        closed_dict = closed.to_dict()

        assert closed_dict["status"] == "closed"
        assert closed_dict["metadata"] == metadata
        assert closed_dict["closed_at"] is not None

    def test_to_dict_iso_format_timestamps(self) -> None:
        """Test that timestamps are ISO formatted strings."""
        session = Session.create(user_id=str(uuid.uuid4()))
        session_dict = session.to_dict()

        # Should be valid ISO format strings
        datetime.fromisoformat(session_dict["created_at"])
        datetime.fromisoformat(session_dict["last_activity_at"])
