"""Unit tests for Note entity.

Tests cover:
- Entity creation and validation
- Immutability
- Factory methods
- Update operations
- Edge cases and error handling
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities.note import Note


class TestNoteCreation:
    """Test Note entity creation and validation."""

    def test_create_note_with_all_fields(self) -> None:
        """Test creating a note with all fields specified."""
        note_id = "test-id-123"
        user_id = "user-456"
        title = "Test Note"
        content = "This is test content"
        tags = ("work", "important")
        embedding = tuple([0.1] * 1536)
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        note = Note(
            id=note_id,
            user_id=user_id,
            title=title,
            content=content,
            tags=tags,
            embedding=embedding,
            created_at=created_at,
            updated_at=updated_at,
        )

        assert note.id == note_id
        assert note.user_id == user_id
        assert note.title == title
        assert note.content == content
        assert note.tags == tags
        assert note.embedding == embedding
        assert note.created_at == created_at
        assert note.updated_at == updated_at

    def test_create_note_with_minimal_fields(self) -> None:
        """Test creating a note with only required fields."""
        note = Note(
            id="test-id",
            user_id="user-id",
            title="Title",
            content="Content",
        )

        assert note.id == "test-id"
        assert note.user_id == "user-id"
        assert note.title == "Title"
        assert note.content == "Content"
        assert note.tags == tuple()
        assert note.embedding is None
        assert isinstance(note.created_at, datetime)
        assert isinstance(note.updated_at, datetime)

    def test_create_note_factory_method(self) -> None:
        """Test Note.create factory method."""
        note = Note.create(
            user_id="user-123",
            title="Factory Note",
            content="Created via factory",
            tags=["tag1", "tag2"],
        )

        assert note.id  # Should be auto-generated UUID
        assert note.user_id == "user-123"
        assert note.title == "Factory Note"
        assert note.content == "Created via factory"
        assert note.tags == ("tag1", "tag2")
        assert note.embedding is None
        assert isinstance(note.created_at, datetime)
        assert isinstance(note.updated_at, datetime)

    def test_create_note_factory_strips_whitespace(self) -> None:
        """Test that factory method strips whitespace from fields."""
        note = Note.create(
            user_id="user-123",
            title="  Title with spaces  ",
            content="  Content with spaces  ",
            tags=["  tag1  ", "  tag2  "],
        )

        assert note.title == "Title with spaces"
        assert note.content == "Content with spaces"
        assert note.tags == ("tag1", "tag2")


class TestNoteValidation:
    """Test Note validation rules."""

    def test_empty_id_raises_error(self) -> None:
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="Note ID must be a non-empty string"):
            Note(id="", user_id="user-123", title="Title", content="Content")

    def test_invalid_id_type_raises_error(self) -> None:
        """Test that non-string ID raises ValueError."""
        with pytest.raises(ValueError, match="Note ID must be a non-empty string"):
            Note(id=123, user_id="user-123", title="Title", content="Content")  # type: ignore

    def test_empty_user_id_raises_error(self) -> None:
        """Test that empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="User ID must be a non-empty string"):
            Note(id="note-123", user_id="", title="Title", content="Content")

    def test_empty_title_raises_error(self) -> None:
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty or whitespace"):
            Note(id="note-123", user_id="user-123", title="   ", content="Content")

    def test_title_non_string_raises_error(self) -> None:
        """Test that non-string title raises ValueError."""
        with pytest.raises(ValueError, match="Title must be a string"):
            Note(id="note-123", user_id="user-123", title=123, content="Content")  # type: ignore

    def test_title_too_long_raises_error(self) -> None:
        """Test that title exceeding 255 chars raises ValueError."""
        long_title = "a" * 256
        with pytest.raises(ValueError, match="Title cannot exceed 255 characters"):
            Note(id="note-123", user_id="user-123", title=long_title, content="Content")

    def test_empty_content_raises_error(self) -> None:
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be empty or whitespace"):
            Note(id="note-123", user_id="user-123", title="Title", content="   ")

    def test_content_non_string_raises_error(self) -> None:
        """Test that non-string content raises ValueError."""
        with pytest.raises(ValueError, match="Content must be a string"):
            Note(id="note-123", user_id="user-123", title="Title", content=123)  # type: ignore

    def test_tags_not_tuple_raises_error(self) -> None:
        """Test that non-tuple tags raises ValueError."""
        with pytest.raises(ValueError, match="Tags must be a tuple of strings"):
            Note(
                id="note-123",
                user_id="user-123",
                title="Title",
                content="Content",
                tags=["tag1", "tag2"],  # type: ignore
            )

    def test_tags_with_non_string_raises_error(self) -> None:
        """Test that tags containing non-strings raises ValueError."""
        with pytest.raises(ValueError, match="All tags must be strings"):
            Note(
                id="note-123",
                user_id="user-123",
                title="Title",
                content="Content",
                tags=(123, "tag2"),  # type: ignore
            )

    def test_tags_with_empty_string_raises_error(self) -> None:
        """Test that tags containing empty strings raises ValueError."""
        with pytest.raises(ValueError, match="Tags cannot be empty or whitespace"):
            Note(
                id="note-123",
                user_id="user-123",
                title="Title",
                content="Content",
                tags=("tag1", "  "),
            )

    def test_embedding_wrong_dimension_raises_error(self) -> None:
        """Test that embedding with wrong dimensions raises ValueError."""
        wrong_embedding = tuple([0.1] * 100)  # Should be 1536
        with pytest.raises(ValueError, match="Embedding must have exactly 1536 dimensions"):
            Note(
                id="note-123",
                user_id="user-123",
                title="Title",
                content="Content",
                embedding=wrong_embedding,
            )

    def test_embedding_not_tuple_raises_error(self) -> None:
        """Test that non-tuple embedding raises ValueError."""
        with pytest.raises(ValueError, match="Embedding must be a tuple of floats"):
            Note(
                id="note-123",
                user_id="user-123",
                title="Title",
                content="Content",
                embedding=[0.1] * 1536,  # type: ignore
            )

    def test_embedding_non_float_values_raises_error(self) -> None:
        """Test that embedding with non-float values raises ValueError."""
        bad_embedding = tuple([1] * 1536)  # Integers instead of floats
        with pytest.raises(ValueError, match="All embedding values must be floats"):
            Note(
                id="note-123",
                user_id="user-123",
                title="Title",
                content="Content",
                embedding=bad_embedding,  # type: ignore
            )


class TestNoteImmutability:
    """Test that Note is immutable (frozen dataclass)."""

    def test_cannot_modify_title(self) -> None:
        """Test that title cannot be modified after creation."""
        note = Note.create(user_id="user-123", title="Original", content="Content")

        with pytest.raises(Exception):  # FrozenInstanceError
            note.title = "Modified"  # type: ignore

    def test_cannot_modify_content(self) -> None:
        """Test that content cannot be modified after creation."""
        note = Note.create(user_id="user-123", title="Title", content="Original")

        with pytest.raises(Exception):  # FrozenInstanceError
            note.content = "Modified"  # type: ignore

    def test_cannot_modify_tags(self) -> None:
        """Test that tags cannot be modified after creation."""
        note = Note.create(user_id="user-123", title="Title", content="Content", tags=["tag1"])

        with pytest.raises(Exception):  # FrozenInstanceError
            note.tags = ("tag2",)  # type: ignore


class TestNoteUpdate:
    """Test Note update method (creates new instance)."""

    def test_update_title(self) -> None:
        """Test updating note title creates new instance."""
        original = Note.create(user_id="user-123", title="Original Title", content="Content")
        updated = original.update(title="New Title")

        assert original.title == "Original Title"
        assert updated.title == "New Title"
        assert updated.content == original.content
        assert updated.id == original.id
        assert updated.user_id == original.user_id
        assert updated.created_at == original.created_at
        assert updated.updated_at > original.updated_at

    def test_update_content(self) -> None:
        """Test updating note content creates new instance."""
        original = Note.create(user_id="user-123", title="Title", content="Original Content")
        updated = original.update(content="New Content")

        assert original.content == "Original Content"
        assert updated.content == "New Content"
        assert updated.title == original.title

    def test_update_tags(self) -> None:
        """Test updating note tags creates new instance."""
        original = Note.create(user_id="user-123", title="Title", content="Content", tags=["old"])
        updated = original.update(tags=["new1", "new2"])

        assert original.tags == ("old",)
        assert updated.tags == ("new1", "new2")

    def test_update_embedding(self) -> None:
        """Test updating note embedding creates new instance."""
        original = Note.create(user_id="user-123", title="Title", content="Content")
        new_embedding = [0.5] * 1536
        updated = original.update(embedding=new_embedding)

        assert original.embedding is None
        assert updated.embedding == tuple(new_embedding)

    def test_update_multiple_fields(self) -> None:
        """Test updating multiple fields at once."""
        original = Note.create(user_id="user-123", title="Old", content="Old content")
        updated = original.update(title="New", content="New content", tags=["tag"])

        assert updated.title == "New"
        assert updated.content == "New content"
        assert updated.tags == ("tag",)

    def test_update_strips_whitespace(self) -> None:
        """Test that update strips whitespace from fields."""
        original = Note.create(user_id="user-123", title="Title", content="Content")
        updated = original.update(title="  New Title  ", tags=["  tag  "])

        assert updated.title == "New Title"
        assert updated.tags == ("tag",)


class TestNoteToDict:
    """Test Note to_dict conversion."""

    def test_to_dict_with_all_fields(self) -> None:
        """Test converting note with all fields to dict."""
        embedding = [0.1] * 1536
        note = Note.create(
            user_id="user-123",
            title="Title",
            content="Content",
            tags=["tag1", "tag2"],
            embedding=embedding,
        )

        result = note.to_dict()

        assert result["id"] == note.id
        assert result["user_id"] == "user-123"
        assert result["title"] == "Title"
        assert result["content"] == "Content"
        assert result["tags"] == ["tag1", "tag2"]
        assert result["embedding"] == embedding
        assert result["created_at"] == note.created_at.isoformat()
        assert result["updated_at"] == note.updated_at.isoformat()

    def test_to_dict_without_embedding(self) -> None:
        """Test converting note without embedding to dict."""
        note = Note.create(user_id="user-123", title="Title", content="Content")

        result = note.to_dict()

        assert result["embedding"] is None

    def test_to_dict_returns_new_dict(self) -> None:
        """Test that to_dict returns a new dict instance."""
        note = Note.create(user_id="user-123", title="Title", content="Content")

        dict1 = note.to_dict()
        dict2 = note.to_dict()

        assert dict1 is not dict2
        assert dict1 == dict2
