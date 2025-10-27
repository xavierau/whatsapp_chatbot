"""Unit tests for CreateNoteUseCase."""

import pytest

from src.application.use_cases.notes.create_note import CreateNoteUseCase
from src.domain.entities.note import Note


class MockRepository:
    """Mock repository for testing."""

    def __init__(self) -> None:
        self.created_note: Note | None = None

    async def create(self, note: Note) -> Note:
        """Mock create method."""
        self.created_note = note
        return note


class MockEmbeddingService:
    """Mock embedding service for testing."""

    def __init__(self, embedding: list[float] | None = None) -> None:
        self.embedding = embedding or [0.1] * 1536
        self.generated_text: str | None = None

    async def generate_embedding(self, text: str) -> list[float]:
        """Mock generate_embedding method."""
        self.generated_text = text
        return self.embedding

    def get_dimension(self) -> int:
        """Mock get_dimension method."""
        return 1536

    def get_model_name(self) -> str:
        """Mock get_model_name method."""
        return "mock-model"


class TestCreateNoteUseCase:
    """Test CreateNoteUseCase."""

    @pytest.mark.asyncio
    async def test_create_note_success(self) -> None:
        """Test successful note creation."""
        repository = MockRepository()
        embedding_service = MockEmbeddingService()
        use_case = CreateNoteUseCase(repository, embedding_service)

        result = await use_case.execute(
            user_id="user-123",
            title="Test Note",
            content="Test content",
            tags=["tag1", "tag2"],
        )

        # Verify note was created
        assert result is not None
        assert result.user_id == "user-123"
        assert result.title == "Test Note"
        assert result.content == "Test content"
        assert result.tags == ("tag1", "tag2")
        assert result.embedding is not None
        assert len(result.embedding) == 1536

        # Verify repository was called
        assert repository.created_note == result

        # Verify embedding was generated with correct text
        assert embedding_service.generated_text == "Test Note\nTest content"

    @pytest.mark.asyncio
    async def test_create_note_without_tags(self) -> None:
        """Test creating note without tags."""
        repository = MockRepository()
        embedding_service = MockEmbeddingService()
        use_case = CreateNoteUseCase(repository, embedding_service)

        result = await use_case.execute(
            user_id="user-123",
            title="Test Note",
            content="Test content",
        )

        assert result.tags == tuple()

    @pytest.mark.asyncio
    async def test_create_note_generates_id(self) -> None:
        """Test that note creation generates unique ID."""
        repository = MockRepository()
        embedding_service = MockEmbeddingService()
        use_case = CreateNoteUseCase(repository, embedding_service)

        result1 = await use_case.execute(
            user_id="user-123",
            title="Note 1",
            content="Content 1",
        )

        result2 = await use_case.execute(
            user_id="user-123",
            title="Note 2",
            content="Content 2",
        )

        assert result1.id != result2.id

    @pytest.mark.asyncio
    async def test_create_note_invalid_title(self) -> None:
        """Test that invalid title raises ValueError."""
        repository = MockRepository()
        embedding_service = MockEmbeddingService()
        use_case = CreateNoteUseCase(repository, embedding_service)

        with pytest.raises(ValueError):
            await use_case.execute(
                user_id="user-123",
                title="",
                content="Valid content",
            )

    @pytest.mark.asyncio
    async def test_create_note_invalid_content(self) -> None:
        """Test that invalid content raises ValueError."""
        repository = MockRepository()
        embedding_service = MockEmbeddingService()
        use_case = CreateNoteUseCase(repository, embedding_service)

        with pytest.raises(ValueError):
            await use_case.execute(
                user_id="user-123",
                title="Valid title",
                content="   ",
            )

    @pytest.mark.asyncio
    async def test_create_note_repository_failure(self) -> None:
        """Test handling of repository failures."""

        class FailingRepository(MockRepository):
            async def create(self, note: Note) -> Note:
                raise Exception("Database error")

        repository = FailingRepository()
        embedding_service = MockEmbeddingService()
        use_case = CreateNoteUseCase(repository, embedding_service)

        with pytest.raises(RuntimeError, match="Failed to create note"):
            await use_case.execute(
                user_id="user-123",
                title="Test",
                content="Test",
            )

    @pytest.mark.asyncio
    async def test_create_note_embedding_failure(self) -> None:
        """Test handling of embedding service failures."""

        class FailingEmbeddingService(MockEmbeddingService):
            async def generate_embedding(self, text: str) -> list[float]:
                raise Exception("API error")

        repository = MockRepository()
        embedding_service = FailingEmbeddingService()
        use_case = CreateNoteUseCase(repository, embedding_service)

        with pytest.raises(RuntimeError, match="Failed to create note"):
            await use_case.execute(
                user_id="user-123",
                title="Test",
                content="Test",
            )
