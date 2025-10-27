"""Expense repository protocol defining data access contract.

This module defines the interface for expense persistence following
the Repository pattern and Dependency Inversion Principle.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from src.domain.entities.expense import Expense


class IExpenseRepository(Protocol):
    """Protocol defining the contract for expense data access.

    This protocol follows the Repository pattern, abstracting data access
    logic from business logic. Implementations can use different storage
    backends (PostgreSQL, SQLite, in-memory, etc.) as long as they
    implement this interface.

    All methods are async to support non-blocking I/O operations.
    """

    async def create(self, expense: Expense) -> Expense:
        """Persist a new expense to the repository.

        Args:
            expense: Expense entity to persist

        Returns:
            The persisted Expense entity

        Raises:
            ValueError: If expense with same ID already exists
            RuntimeError: If persistence fails
        """
        ...

    async def get_by_id(self, user_id: str, expense_id: str) -> Expense | None:
        """Retrieve an expense by its ID, scoped to the user.

        Args:
            user_id: User ID who owns the expense
            expense_id: Unique identifier of the expense

        Returns:
            Expense if found and belongs to user, None otherwise

        Raises:
            RuntimeError: If retrieval fails
        """
        ...

    async def update(self, expense: Expense) -> Expense:
        """Update an existing expense in the repository.

        Args:
            expense: Expense entity with updated fields

        Returns:
            The updated Expense entity

        Raises:
            ValueError: If expense doesn't exist
            RuntimeError: If update fails
        """
        ...

    async def delete(self, user_id: str, expense_id: str) -> bool:
        """Delete an expense from the repository.

        Args:
            user_id: User ID who owns the expense
            expense_id: Unique identifier of the expense

        Returns:
            True if deleted, False if expense not found

        Raises:
            RuntimeError: If deletion fails
        """
        ...

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Expense]:
        """List all expenses for a user with pagination.

        Results are ordered by expense_date in descending order
        (most recent first).

        Args:
            user_id: User ID who owns the expenses
            limit: Maximum number of expenses to return (default: 10)
            offset: Number of expenses to skip (default: 0)

        Returns:
            List of expenses ordered by expense_date DESC

        Raises:
            ValueError: If limit or offset are invalid
            RuntimeError: If retrieval fails
        """
        ...

    async def list_by_date_range(
        self,
        user_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Expense]:
        """List expenses within a date range.

        Args:
            user_id: User ID who owns the expenses
            date_from: Start date (inclusive), None for no lower bound
            date_to: End date (inclusive), None for no upper bound
            limit: Maximum number of expenses to return (default: 100)
            offset: Number of expenses to skip (default: 0)

        Returns:
            List of expenses within date range, ordered by expense_date DESC

        Raises:
            ValueError: If date_from > date_to or invalid pagination params
            RuntimeError: If retrieval fails
        """
        ...

    async def search_by_vector(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[tuple[Expense, float]]:
        """Search expenses using vector similarity (semantic search).

        Uses cosine similarity to find expenses with similar meaning to the query.

        Args:
            user_id: User ID who owns the expenses
            query_embedding: Vector embedding of the search query
            limit: Maximum number of results to return (default: 5)
            similarity_threshold: Minimum similarity score (0-1, default: 0.7)

        Returns:
            List of (Expense, similarity_score) tuples ordered by similarity DESC

        Raises:
            ValueError: If query_embedding has wrong dimensions
            RuntimeError: If search fails
        """
        ...

    async def search_by_category(
        self,
        user_id: str,
        category: str,
        limit: int = 10,
    ) -> list[Expense]:
        """Search expenses by category.

        Args:
            user_id: User ID who owns the expenses
            category: Category to filter by
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of matching expenses ordered by expense_date DESC

        Raises:
            RuntimeError: If search fails
        """
        ...

    async def search_by_tags(
        self,
        user_id: str,
        tags: list[str],
        match_all: bool = False,
        limit: int = 10,
    ) -> list[Expense]:
        """Search expenses by tags.

        Args:
            user_id: User ID who owns the expenses
            tags: List of tags to search for
            match_all: If True, expense must have all tags; if False, any tag (default: False)
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of matching expenses ordered by expense_date DESC

        Raises:
            RuntimeError: If search fails
        """
        ...

    async def search_by_amount_range(
        self,
        user_id: str,
        amount_min: Decimal | None = None,
        amount_max: Decimal | None = None,
        limit: int = 10,
    ) -> list[Expense]:
        """Search expenses by amount range.

        Args:
            user_id: User ID who owns the expenses
            amount_min: Minimum amount (inclusive), None for no lower bound
            amount_max: Maximum amount (inclusive), None for no upper bound
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of matching expenses ordered by expense_date DESC

        Raises:
            ValueError: If amount_min > amount_max
            RuntimeError: If search fails
        """
        ...

    async def get_total_by_category(
        self,
        user_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Decimal]:
        """Get total expenses grouped by category.

        Args:
            user_id: User ID who owns the expenses
            date_from: Start date (inclusive), None for no lower bound
            date_to: End date (inclusive), None for no upper bound

        Returns:
            Dictionary mapping category to total amount

        Raises:
            ValueError: If date_from > date_to
            RuntimeError: If query fails
        """
        ...

    async def get_monthly_summary(
        self,
        user_id: str,
        year: int,
        month: int,
    ) -> dict[str, Decimal | int]:
        """Get summary of expenses for a specific month.

        Args:
            user_id: User ID who owns the expenses
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Dictionary with keys:
            - 'total': Total amount spent
            - 'count': Number of expenses
            - 'average': Average expense amount
            - 'by_category': Dict of category totals

        Raises:
            ValueError: If month is not 1-12
            RuntimeError: If query fails
        """
        ...

    async def count_by_user(self, user_id: str) -> int:
        """Count total number of expenses for a user.

        Args:
            user_id: User ID who owns the expenses

        Returns:
            Total count of expenses

        Raises:
            RuntimeError: If count fails
        """
        ...
