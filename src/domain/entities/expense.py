"""Expense entity for expense tracking functionality.

This module defines the Expense entity following Domain-Driven Design principles.
Expenses are owned by users and support vector embeddings for semantic search.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Expense:
    """Expense entity representing a user's expense with vector embedding support.

    This entity is immutable (frozen) following functional programming principles
    and value object patterns. Any modification creates a new Expense instance.

    Attributes:
        id: Unique identifier for the expense
        user_id: WhatsApp user ID who owns this expense
        amount: Expense amount (stored as Decimal for precision)
        currency: Currency code (ISO 4217, e.g., 'HKD', 'USD', 'EUR')
        description: Description of the expense
        category: Category for grouping (e.g., 'food', 'transport', 'entertainment')
        tags: List of tags for additional categorization
        expense_date: Date when the expense occurred
        is_recurring: Whether this is a recurring expense
        recurrence_pattern: Pattern for recurring expenses ('daily', 'weekly', 'monthly', 'yearly')
        receipt_path: Optional path or URL to receipt image
        embedding: Vector embedding for semantic search (1536 dimensions for Gemini)
        created_at: Timestamp when expense was created
        updated_at: Timestamp when expense was last updated
    """

    id: str
    user_id: str
    amount: Decimal
    currency: str
    description: str
    category: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    expense_date: date = field(default_factory=date.today)
    is_recurring: bool = False
    recurrence_pattern: str | None = None
    receipt_path: str | None = None
    embedding: tuple[float, ...] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate expense attributes after initialization.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate ID
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Expense ID must be a non-empty string")

        # Validate user_id
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("User ID must be a non-empty string")

        # Validate amount
        if not isinstance(self.amount, Decimal):
            raise ValueError("Amount must be a Decimal")
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

        # Validate currency
        if not isinstance(self.currency, str):
            raise ValueError("Currency must be a string")
        if not self.currency.strip():
            raise ValueError("Currency cannot be empty or whitespace")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter ISO 4217 code (e.g., 'HKD', 'USD')")
        if not self.currency.isupper():
            raise ValueError("Currency code must be uppercase")

        # Validate description
        if not isinstance(self.description, str):
            raise ValueError("Description must be a string")
        if not self.description.strip():
            raise ValueError("Description cannot be empty or whitespace")

        # Validate category
        if not isinstance(self.category, str):
            raise ValueError("Category must be a string")
        if not self.category.strip():
            raise ValueError("Category cannot be empty or whitespace")
        if len(self.category) > 100:
            raise ValueError("Category cannot exceed 100 characters")

        # Validate tags
        if not isinstance(self.tags, tuple):
            raise ValueError("Tags must be a tuple of strings")
        for tag in self.tags:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
            if not tag.strip():
                raise ValueError("Tags cannot be empty or whitespace")

        # Validate expense_date
        if not isinstance(self.expense_date, date):
            raise ValueError("expense_date must be a date object")

        # Validate is_recurring
        if not isinstance(self.is_recurring, bool):
            raise ValueError("is_recurring must be a boolean")

        # Validate recurrence_pattern
        if self.recurrence_pattern is not None:
            if not isinstance(self.recurrence_pattern, str):
                raise ValueError("recurrence_pattern must be a string")
            valid_patterns = ['daily', 'weekly', 'monthly', 'yearly']
            if self.recurrence_pattern not in valid_patterns:
                raise ValueError(
                    f"recurrence_pattern must be one of {valid_patterns}, got '{self.recurrence_pattern}'"
                )
            if not self.is_recurring:
                raise ValueError("recurrence_pattern can only be set when is_recurring is True")

        # Validate receipt_path
        if self.receipt_path is not None:
            if not isinstance(self.receipt_path, str):
                raise ValueError("receipt_path must be a string")
            if not self.receipt_path.strip():
                raise ValueError("receipt_path cannot be empty or whitespace")

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
        amount: Decimal | float | int,
        currency: str,
        description: str,
        category: str,
        tags: list[str] | None = None,
        expense_date: date | None = None,
        is_recurring: bool = False,
        recurrence_pattern: str | None = None,
        receipt_path: str | None = None,
        embedding: list[float] | None = None,
    ) -> "Expense":
        """Factory method to create a new Expense with generated ID and timestamps.

        Args:
            user_id: WhatsApp user ID who owns this expense
            amount: Expense amount (will be converted to Decimal)
            currency: Currency code (ISO 4217)
            description: Description of the expense
            category: Category for grouping
            tags: Optional list of tags
            expense_date: Date of expense (defaults to today)
            is_recurring: Whether this is a recurring expense
            recurrence_pattern: Pattern for recurring expenses
            receipt_path: Optional path to receipt image
            embedding: Optional vector embedding

        Returns:
            New Expense instance with generated ID and timestamps

        Raises:
            ValueError: If validation fails
        """
        # Convert amount to Decimal for precision
        if isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        elif not isinstance(amount, Decimal):
            raise ValueError(f"amount must be Decimal, int, or float, not {type(amount).__name__}")

        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            amount=amount,
            currency=currency.upper().strip(),
            description=description.strip(),
            category=category.strip(),
            tags=tuple(tag.strip() for tag in tags) if tags else tuple(),
            expense_date=expense_date or date.today(),
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern,
            receipt_path=receipt_path.strip() if receipt_path else None,
            embedding=tuple(embedding) if embedding else None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def update(
        self,
        amount: Decimal | float | int | None = None,
        currency: str | None = None,
        description: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        expense_date: date | None = None,
        is_recurring: bool | None = None,
        recurrence_pattern: str | None = None,
        receipt_path: str | None = None,
        embedding: list[float] | None = None,
    ) -> "Expense":
        """Create a new Expense instance with updated fields.

        Since Expense is immutable, this returns a new instance with updated values
        and a new updated_at timestamp.

        Args:
            amount: New amount (if provided, will be converted to Decimal)
            currency: New currency (if provided)
            description: New description (if provided)
            category: New category (if provided)
            tags: New tags (if provided)
            expense_date: New expense date (if provided)
            is_recurring: New is_recurring flag (if provided)
            recurrence_pattern: New recurrence pattern (if provided)
            receipt_path: New receipt path (if provided)
            embedding: New embedding (if provided)

        Returns:
            New Expense instance with updated fields

        Raises:
            ValueError: If validation fails
        """
        # Convert amount to Decimal if provided
        if amount is not None:
            if isinstance(amount, (int, float)):
                amount = Decimal(str(amount))
            elif not isinstance(amount, Decimal):
                raise ValueError(f"amount must be Decimal, int, or float, not {type(amount).__name__}")

        return Expense(
            id=self.id,
            user_id=self.user_id,
            amount=amount if amount is not None else self.amount,
            currency=currency.upper().strip() if currency is not None else self.currency,
            description=description.strip() if description is not None else self.description,
            category=category.strip() if category is not None else self.category,
            tags=tuple(tag.strip() for tag in tags) if tags is not None else self.tags,
            expense_date=expense_date if expense_date is not None else self.expense_date,
            is_recurring=is_recurring if is_recurring is not None else self.is_recurring,
            recurrence_pattern=recurrence_pattern if recurrence_pattern is not None else self.recurrence_pattern,
            receipt_path=receipt_path.strip() if receipt_path is not None else self.receipt_path,
            embedding=tuple(embedding) if embedding is not None else self.embedding,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
        )

    def to_dict(self) -> dict:
        """Convert Expense to dictionary representation.

        Returns:
            Dictionary with all expense fields
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "description": self.description,
            "category": self.category,
            "tags": list(self.tags),
            "expense_date": self.expense_date.isoformat(),
            "is_recurring": self.is_recurring,
            "recurrence_pattern": self.recurrence_pattern,
            "receipt_path": self.receipt_path,
            "embedding": list(self.embedding) if self.embedding else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
