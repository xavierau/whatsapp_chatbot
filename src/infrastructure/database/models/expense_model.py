"""SQLAlchemy model for Expense entity."""

from datetime import UTC, date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, CheckConstraint, Date, DateTime, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.note_model import Base


class ExpenseModel(Base):
    """SQLAlchemy model for expenses table with pgvector support.

    Maps to the expenses table in PostgreSQL, providing ORM
    capabilities for expense persistence.
    """

    __tablename__ = "expenses"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Core fields
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="HKD")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional fields
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrence_pattern: Mapped[str | None] = mapped_column(String(20), nullable=True)
    receipt_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Vector embedding for semantic search
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Table constraints
    __table_args__ = (
        # Amount must be non-negative
        CheckConstraint("amount >= 0", name="check_amount_non_negative"),
        # Recurrence pattern validation
        CheckConstraint(
            "(is_recurring = FALSE AND recurrence_pattern IS NULL) OR (is_recurring = TRUE)",
            name="check_recurrence_pattern",
        ),
        CheckConstraint(
            "recurrence_pattern IS NULL OR recurrence_pattern IN ('daily', 'weekly', 'monthly', 'yearly')",
            name="check_recurrence_pattern_value",
        ),
        # Composite indexes for common queries
        Index("idx_expenses_user_date", "user_id", "expense_date"),
        Index("idx_expenses_user_category", "user_id", "category"),
        Index("idx_expenses_amount", "user_id", "amount"),
        Index("idx_expenses_currency", "user_id", "currency"),
    )

    def __repr__(self) -> str:
        """String representation of expense model."""
        return (
            f"<ExpenseModel(id={self.id}, user_id={self.user_id}, "
            f"amount={self.amount} {self.currency}, category={self.category})>"
        )
