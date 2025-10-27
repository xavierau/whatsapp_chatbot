"""PostgreSQL implementation of Expense repository with pgvector support."""

import logging
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import and_, delete, desc, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.expense import Expense
from src.infrastructure.database.models.expense_model import ExpenseModel

logger = logging.getLogger(__name__)


class ExpenseRepository:
    """PostgreSQL-based expense repository with vector search.

    Implements IExpenseRepository protocol using SQLAlchemy and pgvector.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        self._session = session

    async def create(self, expense: Expense) -> Expense:
        """Persist a new expense to the database.

        Args:
            expense: Expense entity to persist

        Returns:
            The persisted Expense entity

        Raises:
            ValueError: If expense with same ID already exists
            RuntimeError: If persistence fails
        """
        try:
            # Check if expense already exists
            existing = await self._session.get(ExpenseModel, expense.id)
            if existing:
                raise ValueError(f"Expense with ID {expense.id} already exists")

            # Create model from entity
            model = ExpenseModel(
                id=expense.id,
                user_id=expense.user_id,
                amount=expense.amount,
                currency=expense.currency,
                description=expense.description,
                category=expense.category,
                tags=list(expense.tags),
                expense_date=expense.expense_date,
                is_recurring=expense.is_recurring,
                recurrence_pattern=expense.recurrence_pattern,
                receipt_path=expense.receipt_path,
                embedding=list(expense.embedding) if expense.embedding else None,
                created_at=expense.created_at,
                updated_at=expense.updated_at,
            )

            self._session.add(model)
            await self._session.commit()
            await self._session.refresh(model)

            logger.debug("Created expense with ID: %s", expense.id)
            return self._model_to_entity(model)

        except ValueError:
            raise
        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to create expense: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to create expense: {e}") from e

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
        try:
            stmt = select(ExpenseModel).where(
                and_(ExpenseModel.id == expense_id, ExpenseModel.user_id == user_id)
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                logger.debug("Expense %s not found for user %s", expense_id, user_id)
                return None

            return self._model_to_entity(model)

        except Exception as e:
            logger.error("Failed to retrieve expense: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to retrieve expense: {e}") from e

    async def update(self, expense: Expense) -> Expense:
        """Update an existing expense in the database.

        Args:
            expense: Expense entity with updated fields

        Returns:
            The updated Expense entity

        Raises:
            ValueError: If expense doesn't exist
            RuntimeError: If update fails
        """
        try:
            model = await self._session.get(ExpenseModel, expense.id)
            if model is None:
                raise ValueError(f"Expense with ID {expense.id} not found")

            # Update fields
            model.user_id = expense.user_id
            model.amount = expense.amount
            model.currency = expense.currency
            model.description = expense.description
            model.category = expense.category
            model.tags = list(expense.tags)
            model.expense_date = expense.expense_date
            model.is_recurring = expense.is_recurring
            model.recurrence_pattern = expense.recurrence_pattern
            model.receipt_path = expense.receipt_path
            model.embedding = list(expense.embedding) if expense.embedding else None
            model.updated_at = expense.updated_at

            await self._session.commit()
            await self._session.refresh(model)

            logger.debug("Updated expense with ID: %s", expense.id)
            return self._model_to_entity(model)

        except ValueError:
            raise
        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to update expense: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to update expense: {e}") from e

    async def delete(self, user_id: str, expense_id: str) -> bool:
        """Delete an expense from the database.

        Args:
            user_id: User ID who owns the expense
            expense_id: Unique identifier of the expense

        Returns:
            True if deleted, False if expense not found

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            stmt = delete(ExpenseModel).where(
                and_(ExpenseModel.id == expense_id, ExpenseModel.user_id == user_id)
            )
            result = await self._session.execute(stmt)
            await self._session.commit()

            deleted = result.rowcount > 0
            logger.debug(
                "Delete expense %s for user %s: %s",
                expense_id,
                user_id,
                "success" if deleted else "not found",
            )
            return deleted

        except Exception as e:
            await self._session.rollback()
            logger.error("Failed to delete expense: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to delete expense: {e}") from e

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Expense]:
        """List all expenses for a user with pagination.

        Results are ordered by expense_date in descending order.

        Args:
            user_id: User ID who owns the expenses
            limit: Maximum number of expenses to return
            offset: Number of expenses to skip

        Returns:
            List of expenses ordered by expense_date DESC

        Raises:
            ValueError: If limit or offset are invalid
            RuntimeError: If retrieval fails
        """
        if limit <= 0:
            raise ValueError("Limit must be positive")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        try:
            stmt = (
                select(ExpenseModel)
                .where(ExpenseModel.user_id == user_id)
                .order_by(desc(ExpenseModel.expense_date), desc(ExpenseModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            logger.debug("Retrieved %d expenses for user %s", len(models), user_id)
            return [self._model_to_entity(model) for model in models]

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to list expenses: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to list expenses: {e}") from e

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
            limit: Maximum number of expenses to return
            offset: Number of expenses to skip

        Returns:
            List of expenses within date range, ordered by expense_date DESC

        Raises:
            ValueError: If date_from > date_to or invalid pagination params
            RuntimeError: If retrieval fails
        """
        if limit <= 0:
            raise ValueError("Limit must be positive")
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        try:
            conditions = [ExpenseModel.user_id == user_id]

            if date_from:
                conditions.append(ExpenseModel.expense_date >= date_from)
            if date_to:
                conditions.append(ExpenseModel.expense_date <= date_to)

            stmt = (
                select(ExpenseModel)
                .where(and_(*conditions))
                .order_by(desc(ExpenseModel.expense_date), desc(ExpenseModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            logger.debug("Date range search returned %d results", len(models))
            return [self._model_to_entity(model) for model in models]

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to list expenses by date range: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to list expenses by date range: {e}") from e

    async def search_by_vector(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[tuple[Expense, float]]:
        """Search expenses using vector similarity (semantic search).

        Uses cosine similarity to find expenses with similar meaning.

        Args:
            user_id: User ID who owns the expenses
            query_embedding: Vector embedding of the search query
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of (Expense, similarity_score) tuples ordered by similarity DESC

        Raises:
            ValueError: If query_embedding has wrong dimensions
            RuntimeError: If search fails
        """
        if len(query_embedding) != 1536:
            raise ValueError(f"Query embedding must be 1536 dimensions, got {len(query_embedding)}")

        try:
            # Calculate cosine similarity: 1 - cosine_distance
            similarity = 1 - ExpenseModel.embedding.cosine_distance(query_embedding)

            stmt = (
                select(ExpenseModel, similarity.label("similarity"))
                .where(and_(ExpenseModel.user_id == user_id, similarity >= similarity_threshold))
                .order_by(desc("similarity"))
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            rows = result.all()

            logger.debug("Vector search returned %d results", len(rows))
            return [(self._model_to_entity(row[0]), float(row[1])) for row in rows]

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to search by vector: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to search by vector: {e}") from e

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
            limit: Maximum number of results to return

        Returns:
            List of matching expenses ordered by expense_date DESC

        Raises:
            RuntimeError: If search fails
        """
        try:
            stmt = (
                select(ExpenseModel)
                .where(and_(ExpenseModel.user_id == user_id, ExpenseModel.category == category))
                .order_by(desc(ExpenseModel.expense_date), desc(ExpenseModel.created_at))
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            logger.debug("Category search returned %d results", len(models))
            return [self._model_to_entity(model) for model in models]

        except Exception as e:
            logger.error("Failed to search by category: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to search by category: {e}") from e

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
            match_all: If True, expense must have all tags; if False, any tag
            limit: Maximum number of results to return

        Returns:
            List of matching expenses ordered by expense_date DESC

        Raises:
            RuntimeError: If search fails
        """
        try:
            if match_all:
                # Expense must contain all tags
                tag_condition = ExpenseModel.tags.contains(tags)
            else:
                # Expense must contain at least one tag
                tag_condition = ExpenseModel.tags.overlap(tags)

            stmt = (
                select(ExpenseModel)
                .where(and_(ExpenseModel.user_id == user_id, tag_condition))
                .order_by(desc(ExpenseModel.expense_date), desc(ExpenseModel.created_at))
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            logger.debug("Tag search returned %d results", len(models))
            return [self._model_to_entity(model) for model in models]

        except Exception as e:
            logger.error("Failed to search by tags: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to search by tags: {e}") from e

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
            limit: Maximum number of results to return

        Returns:
            List of matching expenses ordered by expense_date DESC

        Raises:
            ValueError: If amount_min > amount_max
            RuntimeError: If search fails
        """
        if amount_min and amount_max and amount_min > amount_max:
            raise ValueError("amount_min cannot be greater than amount_max")

        try:
            conditions = [ExpenseModel.user_id == user_id]

            if amount_min is not None:
                conditions.append(ExpenseModel.amount >= amount_min)
            if amount_max is not None:
                conditions.append(ExpenseModel.amount <= amount_max)

            stmt = (
                select(ExpenseModel)
                .where(and_(*conditions))
                .order_by(desc(ExpenseModel.expense_date), desc(ExpenseModel.created_at))
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            logger.debug("Amount range search returned %d results", len(models))
            return [self._model_to_entity(model) for model in models]

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to search by amount range: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to search by amount range: {e}") from e

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
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        try:
            conditions = [ExpenseModel.user_id == user_id]

            if date_from:
                conditions.append(ExpenseModel.expense_date >= date_from)
            if date_to:
                conditions.append(ExpenseModel.expense_date <= date_to)

            stmt = (
                select(ExpenseModel.category, func.sum(ExpenseModel.amount).label("total"))
                .where(and_(*conditions))
                .group_by(ExpenseModel.category)
                .order_by(desc("total"))
            )

            result = await self._session.execute(stmt)
            rows = result.all()

            totals = {row[0]: Decimal(str(row[1])) for row in rows}
            logger.debug("Category totals: %s", totals)
            return totals

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to get total by category: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get total by category: {e}") from e

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
        if month < 1 or month > 12:
            raise ValueError(f"Month must be between 1 and 12, got {month}")

        try:
            # Calculate date range for the month
            _, last_day = monthrange(year, month)
            date_from = date(year, month, 1)
            date_to = date(year, month, last_day)

            # Get all expenses for the month
            conditions = [
                ExpenseModel.user_id == user_id,
                ExpenseModel.expense_date >= date_from,
                ExpenseModel.expense_date <= date_to,
            ]

            # Get total and count
            stmt = select(
                func.sum(ExpenseModel.amount).label("total"),
                func.count(ExpenseModel.id).label("count"),
                func.avg(ExpenseModel.amount).label("average"),
            ).where(and_(*conditions))

            result = await self._session.execute(stmt)
            row = result.one()

            total = Decimal(str(row[0])) if row[0] else Decimal("0")
            count = row[1] or 0
            average = Decimal(str(row[2])) if row[2] else Decimal("0")

            # Get category breakdown
            by_category = await self.get_total_by_category(user_id, date_from, date_to)

            summary = {
                "total": total,
                "count": count,
                "average": average,
                "by_category": by_category,
            }

            logger.debug("Monthly summary for %s-%s: %s", year, month, summary)
            return summary

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to get monthly summary: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get monthly summary: {e}") from e

    async def count_by_user(self, user_id: str) -> int:
        """Count total number of expenses for a user.

        Args:
            user_id: User ID who owns the expenses

        Returns:
            Total count of expenses

        Raises:
            RuntimeError: If count fails
        """
        try:
            stmt = select(func.count()).select_from(ExpenseModel).where(ExpenseModel.user_id == user_id)
            result = await self._session.execute(stmt)
            count = result.scalar_one()

            logger.debug("User %s has %d expenses", user_id, count)
            return count

        except Exception as e:
            logger.error("Failed to count expenses: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to count expenses: {e}") from e

    @staticmethod
    def _model_to_entity(model: ExpenseModel) -> Expense:
        """Convert SQLAlchemy model to domain entity.

        Args:
            model: ExpenseModel instance

        Returns:
            Expense entity
        """
        return Expense(
            id=model.id,
            user_id=model.user_id,
            amount=model.amount,
            currency=model.currency,
            description=model.description,
            category=model.category,
            tags=tuple(model.tags) if model.tags else tuple(),
            expense_date=model.expense_date,
            is_recurring=model.is_recurring,
            recurrence_pattern=model.recurrence_pattern,
            receipt_path=model.receipt_path,
            embedding=tuple(float(x) for x in model.embedding) if model.embedding is not None else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
