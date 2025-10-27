"""Note entity for note-taking functionality.

This module defines the Note entity following Domain-Driven Design principles.
Notes are owned by users and support vector embeddings for semantic search.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Note:
    """Note entity representing a user's note with vector embedding support.

    This entity is immutable (frozen) following functional programming principles
    and value object patterns. Any modification creates a new Note instance.

    Attributes:
        id: Unique identifier for the note
        user_id: WhatsApp user ID who owns this note
        title: Title of the note (required, non-empty)
        content: Content of the note (required, non-empty)
        tags: List of tags for categorization
        embedding: Vector embedding for semantic search (1536 dimensions for Gemini)
        created_at: Timestamp when note was created
        updated_at: Timestamp when note was last updated
    """

    id: str
    user_id: str
    title: str
    content: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    embedding: tuple[float, ...] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate note attributes after initialization.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate ID
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Note ID must be a non-empty string")

        # Validate user_id
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("User ID must be a non-empty string")

        # Validate title
        if not isinstance(self.title, str):
            raise ValueError("Title must be a string")
        if not self.title.strip():
            raise ValueError("Title cannot be empty or whitespace")
        if len(self.title) > 255:
            raise ValueError("Title cannot exceed 255 characters")

        # Validate content
        if not isinstance(self.content, str):
            raise ValueError("Content must be a string")
        if not self.content.strip():
            raise ValueError("Content cannot be empty or whitespace")

        # Validate tags
        if not isinstance(self.tags, tuple):
            raise ValueError("Tags must be a tuple of strings")
        for tag in self.tags:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
            if not tag.strip():
                raise ValueError("Tags cannot be empty or whitespace")

        # Validate embedding if provided
        if self.embedding is not None:
            if not isinstance(self.embedding, tuple):
                raise ValueError("Embedding must be a tuple of floats")
            if not all(isinstance(x, float) for x in self.embedding):
                raise ValueError("All embedding values must be floats")
            if len(self.embedding) != 1536:
                raise ValueError("Embedding must have exactly 1536 dimensions for Gemini")

        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime object")
        if not isinstance(self.updated_at, datetime):
            raise ValueError("updated_at must be a datetime object")

    @classmethod
    def create(
        cls,
        user_id: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> "Note":
        """Factory method to create a new Note with generated ID and timestamps.

        Args:
            user_id: WhatsApp user ID who owns this note
            title: Title of the note
            content: Content of the note
            tags: Optional list of tags
            embedding: Optional vector embedding

        Returns:
            New Note instance with generated ID and timestamps

        Raises:
            ValueError: If validation fails
        """
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title.strip(),
            content=content.strip(),
            tags=tuple(tag.strip() for tag in tags) if tags else tuple(),
            embedding=tuple(embedding) if embedding else None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def update(
        self,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> "Note":
        """Create a new Note instance with updated fields.

        Since Note is immutable, this returns a new instance with updated values
        and a new updated_at timestamp.

        Args:
            title: New title (if provided)
            content: New content (if provided)
            tags: New tags (if provided)
            embedding: New embedding (if provided)

        Returns:
            New Note instance with updated fields

        Raises:
            ValueError: If validation fails
        """
        return Note(
            id=self.id,
            user_id=self.user_id,
            title=title.strip() if title is not None else self.title,
            content=content.strip() if content is not None else self.content,
            tags=tuple(tag.strip() for tag in tags) if tags is not None else self.tags,
            embedding=tuple(embedding) if embedding is not None else self.embedding,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
        )

    def to_dict(self) -> dict:
        """Convert Note to dictionary representation.

        Returns:
            Dictionary with all note fields
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content,
            "tags": list(self.tags),
            "embedding": list(self.embedding) if self.embedding else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }