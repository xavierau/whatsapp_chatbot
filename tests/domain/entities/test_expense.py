"""Tests for Expense entity."""

import pytest
from datetime import date, datetime, UTC
from decimal import Decimal

from src.domain.entities.expense import Expense


class TestExpenseCreation:
    """Test expense creation and validation."""

    def test_create_expense_with_valid_data(self):
        """Test creating expense with all valid required fields."""
        expense = Expense.create(
            user_id="user123",
            amount=100.50,
            currency="HKD",
            description="Lunch at restaurant",
            category="food",
        )

        assert expense.id is not None
        assert expense.user_id == "user123"
        assert expense.amount == Decimal("100.50")
        assert expense.currency == "HKD"
        assert expense.description == "Lunch at restaurant"
        assert expense.category == "food"
        assert expense.tags == tuple()
        assert expense.expense_date == date.today()
        assert expense.is_recurring is False
        assert expense.recurrence_pattern is None
        assert expense.receipt_path is None
        assert expense.embedding is None
        assert isinstance(expense.created_at, datetime)
        assert isinstance(expense.updated_at, datetime)

    def test_create_expense_with_all_fields(self):
        """Test creating expense with all optional fields."""
        expense_date = date(2025, 10, 26)
        embedding = [0.1] * 1536

        expense = Expense.create(
            user_id="user123",
            amount=Decimal("1500.00"),
            currency="hkd",  # Should be converted to uppercase
            description="  Monthly rent  ",  # Should be stripped
            category="  housing  ",  # Should be stripped
            tags=["rent", "monthly"],
            expense_date=expense_date,
            is_recurring=True,
            recurrence_pattern="monthly",
            receipt_path="/receipts/rent_oct_2025.pdf",
            embedding=embedding,
        )

        assert expense.currency == "HKD"
        assert expense.description == "Monthly rent"
        assert expense.category == "housing"
        assert expense.tags == ("rent", "monthly")
        assert expense.expense_date == expense_date
        assert expense.is_recurring is True
        assert expense.recurrence_pattern == "monthly"
        assert expense.receipt_path == "/receipts/rent_oct_2025.pdf"
        assert len(expense.embedding) == 1536

    def test_create_expense_amount_conversion(self):
        """Test amount conversion from int, float, and Decimal."""
        # From int
        expense1 = Expense.create(
            user_id="user123",
            amount=100,
            currency="HKD",
            description="Test",
            category="test",
        )
        assert expense1.amount == Decimal("100")

        # From float
        expense2 = Expense.create(
            user_id="user123",
            amount=99.99,
            currency="HKD",
            description="Test",
            category="test",
        )
        assert expense2.amount == Decimal("99.99")

        # From Decimal
        expense3 = Expense.create(
            user_id="user123",
            amount=Decimal("50.25"),
            currency="HKD",
            description="Test",
            category="test",
        )
        assert expense3.amount == Decimal("50.25")

    def test_create_expense_negative_amount_fails(self):
        """Test that negative amount raises ValueError."""
        with pytest.raises(ValueError, match="Amount cannot be negative"):
            Expense.create(
                user_id="user123",
                amount=-10.00,
                currency="HKD",
                description="Test",
                category="test",
            )

    def test_create_expense_invalid_currency_length(self):
        """Test that currency codes must be 3 characters."""
        with pytest.raises(ValueError, match="Currency must be a 3-letter ISO 4217 code"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="US",  # Too short
                description="Test",
                category="test",
            )

        with pytest.raises(ValueError, match="Currency must be a 3-letter ISO 4217 code"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="USDD",  # Too long
                description="Test",
                category="test",
            )

    def test_create_expense_currency_must_be_uppercase(self):
        """Test that currency is converted to uppercase."""
        expense = Expense.create(
            user_id="user123",
            amount=100,
            currency="usd",
            description="Test",
            category="test",
        )
        assert expense.currency == "USD"

    def test_create_expense_empty_description_fails(self):
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="Description cannot be empty"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="HKD",
                description="   ",  # Whitespace only
                category="test",
            )

    def test_create_expense_empty_category_fails(self):
        """Test that empty category raises ValueError."""
        with pytest.raises(ValueError, match="Category cannot be empty"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="HKD",
                description="Test",
                category="",
            )

    def test_create_expense_category_max_length(self):
        """Test that category cannot exceed 100 characters."""
        long_category = "x" * 101
        with pytest.raises(ValueError, match="Category cannot exceed 100 characters"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="HKD",
                description="Test",
                category=long_category,
            )

    def test_create_expense_recurrence_pattern_validation(self):
        """Test recurrence pattern validation."""
        # Valid patterns
        for pattern in ["daily", "weekly", "monthly", "yearly"]:
            expense = Expense.create(
                user_id="user123",
                amount=100,
                currency="HKD",
                description="Test",
                category="test",
                is_recurring=True,
                recurrence_pattern=pattern,
            )
            assert expense.recurrence_pattern == pattern

        # Invalid pattern
        with pytest.raises(ValueError, match="recurrence_pattern must be one of"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="HKD",
                description="Test",
                category="test",
                is_recurring=True,
                recurrence_pattern="hourly",  # Not supported
            )

    def test_create_expense_recurrence_pattern_without_recurring_fails(self):
        """Test that recurrence_pattern requires is_recurring=True."""
        with pytest.raises(ValueError, match="recurrence_pattern can only be set when is_recurring is True"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="HKD",
                description="Test",
                category="test",
                is_recurring=False,
                recurrence_pattern="monthly",
            )

    def test_create_expense_embedding_dimension_validation(self):
        """Test that embedding must be exactly 1536 dimensions."""
        # Wrong dimensions
        with pytest.raises(ValueError, match="Embedding must have exactly 1536 dimensions"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="HKD",
                description="Test",
                category="test",
                embedding=[0.1] * 512,  # Wrong size
            )

        # Correct dimensions
        expense = Expense.create(
            user_id="user123",
            amount=100,
            currency="HKD",
            description="Test",
            category="test",
            embedding=[0.1] * 1536,
        )
        assert len(expense.embedding) == 1536


class TestExpenseUpdate:
    """Test expense update functionality."""

    def test_update_expense_amount(self):
        """Test updating expense amount."""
        expense = Expense.create(
            user_id="user123",
            amount=100,
            currency="HKD",
            description="Test",
            category="test",
        )

        updated = expense.update(amount=150.50)

        assert updated.id == expense.id
        assert updated.amount == Decimal("150.50")
        assert updated.currency == expense.currency
        assert updated.description == expense.description
        assert updated.updated_at > expense.updated_at

    def test_update_expense_multiple_fields(self):
        """Test updating multiple fields at once."""
        expense = Expense.create(
            user_id="user123",
            amount=100,
            currency="HKD",
            description="Old description",
            category="old_category",
        )

        updated = expense.update(
            amount=200,
            description="New description",
            category="new_category",
            tags=["tag1", "tag2"],
        )

        assert updated.amount == Decimal("200")
        assert updated.description == "New description"
        assert updated.category == "new_category"
        assert updated.tags == ("tag1", "tag2")
        assert updated.created_at == expense.created_at
        assert updated.updated_at > expense.updated_at

    def test_update_expense_recurrence(self):
        """Test updating recurrence settings."""
        expense = Expense.create(
            user_id="user123",
            amount=100,
            currency="HKD",
            description="Test",
            category="test",
        )

        updated = expense.update(
            is_recurring=True,
            recurrence_pattern="monthly",
        )

        assert updated.is_recurring is True
        assert updated.recurrence_pattern == "monthly"

    def test_update_expense_immutability(self):
        """Test that update creates new instance, original unchanged."""
        expense = Expense.create(
            user_id="user123",
            amount=100,
            currency="HKD",
            description="Original",
            category="original",
        )
        original_id = expense.id
        original_amount = expense.amount
        original_updated_at = expense.updated_at

        updated = expense.update(amount=200, description="Updated")

        # Original is unchanged
        assert expense.id == original_id
        assert expense.amount == original_amount
        assert expense.description == "Original"
        assert expense.updated_at == original_updated_at

        # Updated is different instance
        assert updated.id == original_id  # Same ID
        assert updated.amount == Decimal("200")
        assert updated.description == "Updated"
        assert updated.updated_at > original_updated_at


class TestExpenseValidation:
    """Test expense validation rules."""

    def test_empty_user_id_fails(self):
        """Test that empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="User ID must be a non-empty string"):
            Expense.create(
                user_id="",
                amount=100,
                currency="HKD",
                description="Test",
                category="test",
            )

    def test_empty_tags_fail(self):
        """Test that empty tags raise ValueError."""
        with pytest.raises(ValueError, match="Tags cannot be empty"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="HKD",
                description="Test",
                category="test",
                tags=["valid", "  ", "another"],  # Middle tag is whitespace
            )

    def test_receipt_path_validation(self):
        """Test receipt path validation."""
        # Valid path
        expense = Expense.create(
            user_id="user123",
            amount=100,
            currency="HKD",
            description="Test",
            category="test",
            receipt_path="/path/to/receipt.jpg",
        )
        assert expense.receipt_path == "/path/to/receipt.jpg"

        # Empty path fails
        with pytest.raises(ValueError, match="receipt_path cannot be empty"):
            Expense.create(
                user_id="user123",
                amount=100,
                currency="HKD",
                description="Test",
                category="test",
                receipt_path="   ",
            )


class TestExpenseToDict:
    """Test expense serialization."""

    def test_to_dict_complete_expense(self):
        """Test converting expense with all fields to dict."""
        expense_date = date(2025, 10, 26)
        expense = Expense.create(
            user_id="user123",
            amount=Decimal("123.45"),
            currency="HKD",
            description="Test expense",
            category="testing",
            tags=["tag1", "tag2"],
            expense_date=expense_date,
            is_recurring=True,
            recurrence_pattern="monthly",
            receipt_path="/receipts/test.pdf",
            embedding=[0.1] * 1536,
        )

        result = expense.to_dict()

        assert result["id"] == expense.id
        assert result["user_id"] == "user123"
        assert result["amount"] == "123.45"
        assert result["currency"] == "HKD"
        assert result["description"] == "Test expense"
        assert result["category"] == "testing"
        assert result["tags"] == ["tag1", "tag2"]
        assert result["expense_date"] == "2025-10-26"
        assert result["is_recurring"] is True
        assert result["recurrence_pattern"] == "monthly"
        assert result["receipt_path"] == "/receipts/test.pdf"
        assert len(result["embedding"]) == 1536
        assert "created_at" in result
        assert "updated_at" in result

    def test_to_dict_minimal_expense(self):
        """Test converting minimal expense to dict."""
        expense = Expense.create(
            user_id="user123",
            amount=50,
            currency="USD",
            description="Minimal",
            category="misc",
        )

        result = expense.to_dict()

        assert result["tags"] == []
        assert result["is_recurring"] is False
        assert result["recurrence_pattern"] is None
        assert result["receipt_path"] is None
        assert result["embedding"] is None
