"""Expense tracking tools for LLM agent with 3-layer architecture.

This module implements an expense tracking system with:
- Layer 1: Agent interface (expense_tools)
- Layer 2: Validation
- Layer 3: Operation handlers

The architecture provides clear separation of concerns and plain English error messages.

Async Support:
- Internal handlers are fully async
- Main expense_tools() function is synchronous (required for DSPy compatibility)
- Uses nest_asyncio to allow nested event loops (solves DSPy ReAct async context issue)
"""

import asyncio
import json
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

import nest_asyncio

# Apply nest_asyncio to allow nested event loops
# This allows expense_tools to work when called from async contexts (like DSPy ReAct)
nest_asyncio.apply()

from src.application.interfaces.embedding_service import IEmbeddingService
from src.domain.entities.expense import Expense
from src.domain.repositories.expense_repository import IExpenseRepository

logger = logging.getLogger(__name__)

# Global dependencies (will be injected via dependency injection)
_session_factory: Any | None = None  # async_sessionmaker[AsyncSession]
_embedding_service: IEmbeddingService | None = None
_current_user_id: str = "default-user"  # Will be set by context


def configure_expense_tools(
    session_factory: Any,  # async_sessionmaker[AsyncSession]
    embedding_service: IEmbeddingService,
) -> None:
    """Configure expense tools with dependencies.

    Args:
        session_factory: Async session factory for creating database sessions
        embedding_service: Embedding service implementation
    """
    global _session_factory, _embedding_service
    _session_factory = session_factory
    _embedding_service = embedding_service
    logger.info("Expense tools configured with session factory")


def set_user_context(user_id: str) -> None:
    """Set the current user context for expense operations.

    Args:
        user_id: User ID to use for expense operations
    """
    global _current_user_id
    _current_user_id = user_id


# ========== Layer 2: Validation ==========


def validate_operation(operation: str, **kwargs: Any) -> str | None:
    """Validate operation and arguments.

    Returns None if valid, or plain English error message if invalid.

    Args:
        operation: Operation name
        **kwargs: Operation arguments

    Returns:
        Error message if invalid, None if valid
    """
    validators = {
        "create": _validate_create,
        "update": _validate_update,
        "delete": _validate_delete,
        "get": _validate_get,
        "list": _validate_list,
        "search": _validate_search,
        "analytics": _validate_analytics,
    }

    if operation not in validators:
        valid_ops = ", ".join(validators.keys())
        return f"Error: Unknown operation '{operation}'. Valid operations are: {valid_ops}."

    return validators[operation](**kwargs)


def _validate_create(
    amount: float | int | str | None = None,
    currency: str | None = None,
    description: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    expense_date: str | None = None,
    is_recurring: bool | None = None,
    recurrence_pattern: str | None = None,
    receipt_path: str | None = None,
    **extra: Any,
) -> str | None:
    """Validate create operation arguments."""
    if amount is None:
        return "Error: 'amount' is required for creating an expense. Please provide an amount."

    # Validate amount type and value
    try:
        amount_decimal = Decimal(str(amount))
        if amount_decimal < 0:
            return "Error: 'amount' cannot be negative."
    except (InvalidOperation, ValueError):
        return f"Error: 'amount' must be a number, got '{amount}'."

    if description is None:
        return "Error: 'description' is required for creating an expense. Please provide a description."
    if not isinstance(description, str) or not description.strip():
        return "Error: 'description' must be a non-empty string."

    if category is None:
        return "Error: 'category' is required for creating an expense. Please provide a category."
    if not isinstance(category, str) or not category.strip():
        return "Error: 'category' must be a non-empty string."
    if len(category) > 100:
        return "Error: 'category' cannot exceed 100 characters."

    # Validate currency (optional, defaults to HKD)
    if currency is not None:
        if not isinstance(currency, str):
            return "Error: 'currency' must be a string."
        if len(currency) != 3:
            return "Error: 'currency' must be a 3-letter ISO 4217 code (e.g., 'HKD', 'USD')."

    # Validate tags
    if tags is not None:
        if not isinstance(tags, list):
            return "Error: 'tags' must be a list of strings, e.g., ['food', 'lunch']."
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                return "Error: All tags must be non-empty strings."

    # Validate expense_date (optional)
    if expense_date is not None:
        if not isinstance(expense_date, str):
            return "Error: 'expense_date' must be a string in YYYY-MM-DD format."
        try:
            date.fromisoformat(expense_date)
        except ValueError:
            return f"Error: 'expense_date' must be in YYYY-MM-DD format, got '{expense_date}'."

    # Validate recurring fields
    if is_recurring is not None and not isinstance(is_recurring, bool):
        return "Error: 'is_recurring' must be a boolean (true or false)."

    if recurrence_pattern is not None:
        valid_patterns = ['daily', 'weekly', 'monthly', 'yearly']
        if recurrence_pattern not in valid_patterns:
            return f"Error: 'recurrence_pattern' must be one of {valid_patterns}."
        if not is_recurring:
            return "Error: 'recurrence_pattern' can only be set when 'is_recurring' is true."

    # Validate receipt_path
    if receipt_path is not None:
        if not isinstance(receipt_path, str) or not receipt_path.strip():
            return "Error: 'receipt_path' must be a non-empty string."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}. Valid params for 'create': amount, currency, description, category, tags, expense_date, is_recurring, recurrence_pattern, receipt_path."

    return None


def _validate_update(
    expense_id: str | None = None,
    amount: float | int | str | None = None,
    currency: str | None = None,
    description: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    expense_date: str | None = None,
    is_recurring: bool | None = None,
    recurrence_pattern: str | None = None,
    receipt_path: str | None = None,
    **extra: Any,
) -> str | None:
    """Validate update operation arguments."""
    if expense_id is None:
        return "Error: 'expense_id' is required for updating an expense. Please provide the expense ID."
    if not isinstance(expense_id, str) or not expense_id.strip():
        return f"Error: 'expense_id' must be a non-empty string, not {type(expense_id).__name__}."

    # Check that at least one field to update is provided
    if all(
        v is None
        for v in [amount, currency, description, category, tags, expense_date, is_recurring, recurrence_pattern, receipt_path]
    ):
        return "Error: At least one field must be provided to update."

    # Validate individual fields if provided
    if amount is not None:
        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal < 0:
                return "Error: 'amount' cannot be negative."
        except (InvalidOperation, ValueError):
            return f"Error: 'amount' must be a number, got '{amount}'."

    if currency is not None:
        if not isinstance(currency, str) or len(currency) != 3:
            return "Error: 'currency' must be a 3-letter ISO 4217 code."

    if description is not None:
        if not isinstance(description, str) or not description.strip():
            return "Error: 'description' must be a non-empty string."

    if category is not None:
        if not isinstance(category, str) or not category.strip():
            return "Error: 'category' must be a non-empty string."
        if len(category) > 100:
            return "Error: 'category' cannot exceed 100 characters."

    if tags is not None:
        if not isinstance(tags, list):
            return "Error: 'tags' must be a list of strings."
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                return "Error: All tags must be non-empty strings."

    if expense_date is not None:
        try:
            date.fromisoformat(expense_date)
        except ValueError:
            return f"Error: 'expense_date' must be in YYYY-MM-DD format, got '{expense_date}'."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}."

    return None


def _validate_delete(expense_id: str | None = None, **extra: Any) -> str | None:
    """Validate delete operation arguments."""
    if expense_id is None:
        return "Error: 'expense_id' is required for deleting an expense."
    if not isinstance(expense_id, str) or not expense_id.strip():
        return f"Error: 'expense_id' must be a non-empty string, not {type(expense_id).__name__}."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}. Valid params for 'delete': expense_id."

    return None


def _validate_get(expense_id: str | None = None, **extra: Any) -> str | None:
    """Validate get operation arguments."""
    if expense_id is None:
        return "Error: 'expense_id' is required for retrieving an expense."
    if not isinstance(expense_id, str) or not expense_id.strip():
        return f"Error: 'expense_id' must be a non-empty string, not {type(expense_id).__name__}."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}. Valid params for 'get': expense_id."

    return None


def _validate_list(
    limit: int | None = None,
    offset: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    **extra: Any,
) -> str | None:
    """Validate list operation arguments."""
    if limit is not None:
        if not isinstance(limit, int):
            return f"Error: 'limit' must be an integer, not {type(limit).__name__}."
        if limit <= 0:
            return "Error: 'limit' must be a positive number."

    if offset is not None:
        if not isinstance(offset, int):
            return f"Error: 'offset' must be an integer, not {type(offset).__name__}."
        if offset < 0:
            return "Error: 'offset' cannot be negative."

    # Validate date range
    if date_from is not None:
        try:
            date.fromisoformat(date_from)
        except ValueError:
            return f"Error: 'date_from' must be in YYYY-MM-DD format, got '{date_from}'."

    if date_to is not None:
        try:
            date.fromisoformat(date_to)
        except ValueError:
            return f"Error: 'date_to' must be in YYYY-MM-DD format, got '{date_to}'."

    if extra:
        extra_params = ", ".join(extra.keys())
        return f"Error: Unknown parameters: {extra_params}. Valid params for 'list': limit, offset, date_from, date_to."

    return None


def _validate_search(
    query: str | None = None,
    search_type: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    amount_min: float | int | str | None = None,
    amount_max: float | int | str | None = None,
    limit: int | None = None,
    **extra: Any,
) -> str | None:
    """Validate search operation arguments."""
    # Infer search_type if not provided based on parameters
    if search_type is None:
        if category is not None:
            search_type = "category"
        elif tags is not None and len(tags) > 0:
            search_type = "tags"
        elif amount_min is not None or amount_max is not None:
            search_type = "amount_range"
        elif query is not None and query.strip():
            search_type = "semantic"
        else:
            # No search parameters provided at all
            return "Error: Please provide at least one search parameter (query, category, tags, or amount range)."

    valid_types = ["semantic", "category", "tags", "amount_range"]
    if search_type not in valid_types:
        return f"Error: Invalid search_type '{search_type}'. Valid types are: {', '.join(valid_types)}."

    # For semantic search, query is required
    if search_type == "semantic":
        if query is None or not query.strip():
            return "Error: 'query' is required for semantic search. Please provide a search query."

    # For category search, category is required
    if search_type == "category":
        if not category:
            return "Error: 'category' parameter is required for category search."

    # For tag search, tags are required
    if search_type == "tags":
        if not tags:
            return "Error: 'tags' parameter is required for tag search. Please provide a list of tags."
        if not isinstance(tags, list):
            return "Error: 'tags' must be a list of strings."

    # For amount_range search, at least one bound is required
    if search_type == "amount_range":
        if amount_min is None and amount_max is None:
            return "Error: At least one of 'amount_min' or 'amount_max' is required for amount_range search."

        if amount_min is not None:
            try:
                Decimal(str(amount_min))
            except (InvalidOperation, ValueError):
                return f"Error: 'amount_min' must be a number, got '{amount_min}'."

        if amount_max is not None:
            try:
                Decimal(str(amount_max))
            except (InvalidOperation, ValueError):
                return f"Error: 'amount_max' must be a number, got '{amount_max}'."

    if limit is not None:
        if not isinstance(limit, int) or limit <= 0:
            return "Error: 'limit' must be a positive integer."

    return None


def _validate_analytics(
    analytics_type: str | None = None,
    year: int | None = None,
    month: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    **extra: Any,
) -> str | None:
    """Validate analytics operation arguments."""
    if analytics_type is None:
        return "Error: 'analytics_type' is required. Valid types: total_by_category, monthly_summary."

    valid_types = ["total_by_category", "monthly_summary"]
    if analytics_type not in valid_types:
        return f"Error: Invalid analytics_type '{analytics_type}'. Valid types are: {', '.join(valid_types)}."

    # For monthly_summary, year and month are required
    if analytics_type == "monthly_summary":
        if year is None:
            return "Error: 'year' is required for monthly_summary (e.g., 2025)."
        if not isinstance(year, int) or year < 2000 or year > 2100:
            return "Error: 'year' must be a valid year between 2000 and 2100."

        if month is None:
            return "Error: 'month' is required for monthly_summary (1-12)."
        if not isinstance(month, int) or month < 1 or month > 12:
            return "Error: 'month' must be between 1 and 12."

    # Validate date range for total_by_category
    if date_from is not None:
        try:
            date.fromisoformat(date_from)
        except ValueError:
            return f"Error: 'date_from' must be in YYYY-MM-DD format, got '{date_from}'."

    if date_to is not None:
        try:
            date.fromisoformat(date_to)
        except ValueError:
            return f"Error: 'date_to' must be in YYYY-MM-DD format, got '{date_to}'."

    return None


# ========== Layer 3: Operation Handlers ==========


async def _create_expense(
    user_id: str,
    amount: float | int | str,
    description: str,
    category: str,
    currency: str = "HKD",
    tags: list[str] | None = None,
    expense_date: str | None = None,
    is_recurring: bool = False,
    recurrence_pattern: str | None = None,
    receipt_path: str | None = None,
) -> str:
    """Create a new expense."""
    if _session_factory is None or _embedding_service is None:
        raise RuntimeError("Expense tools not configured")

    from src.infrastructure.database.repositories.expense_repository import ExpenseRepository

    session = _session_factory()
    try:
        repository = ExpenseRepository(session)

        # Convert amount to Decimal
        amount_decimal = Decimal(str(amount))

        # Parse expense_date if provided
        exp_date = date.fromisoformat(expense_date) if expense_date else date.today()

        # Generate embedding from description
        embedding = await _embedding_service.generate_embedding(description)

        # Create expense entity
        expense = Expense.create(
            user_id=user_id,
            amount=amount_decimal,
            currency=currency,
            description=description,
            category=category,
            tags=tags,
            expense_date=exp_date,
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern,
            receipt_path=receipt_path,
            embedding=embedding,
        )

        # Save to repository
        created = await repository.create(expense)
        await session.commit()

        return (
            f"Expense created successfully. "
            f"ID: {created.id}, Amount: {created.amount} {created.currency}, "
            f"Category: '{created.category}', Date: {created.expense_date}"
        )
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def _update_expense(
    user_id: str,
    expense_id: str,
    amount: float | int | str | None = None,
    currency: str | None = None,
    description: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    expense_date: str | None = None,
    is_recurring: bool | None = None,
    recurrence_pattern: str | None = None,
    receipt_path: str | None = None,
) -> str:
    """Update an existing expense."""
    if _session_factory is None or _embedding_service is None:
        raise RuntimeError("Expense tools not configured")

    from src.infrastructure.database.repositories.expense_repository import ExpenseRepository

    session = _session_factory()
    try:
        repository = ExpenseRepository(session)

        # Get existing expense
        expense = await repository.get_by_id(user_id, expense_id)
        if expense is None:
            return f"Expense not found. ID: {expense_id}"

        # Prepare update fields
        update_fields = {}

        if amount is not None:
            update_fields["amount"] = Decimal(str(amount))
        if currency is not None:
            update_fields["currency"] = currency
        if description is not None:
            update_fields["description"] = description
            # Regenerate embedding if description changed
            update_fields["embedding"] = await _embedding_service.generate_embedding(description)
        if category is not None:
            update_fields["category"] = category
        if tags is not None:
            update_fields["tags"] = tags
        if expense_date is not None:
            update_fields["expense_date"] = date.fromisoformat(expense_date)
        if is_recurring is not None:
            update_fields["is_recurring"] = is_recurring
        if recurrence_pattern is not None:
            update_fields["recurrence_pattern"] = recurrence_pattern
        if receipt_path is not None:
            update_fields["receipt_path"] = receipt_path

        # Update expense
        updated = expense.update(**update_fields)
        await repository.update(updated)
        await session.commit()

        return f"Expense updated successfully. ID: {updated.id}, Amount: {updated.amount} {updated.currency}"
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def _delete_expense(user_id: str, expense_id: str) -> str:
    """Delete an expense."""
    if _session_factory is None:
        raise RuntimeError("Expense tools not configured")

    from src.infrastructure.database.repositories.expense_repository import ExpenseRepository

    session = _session_factory()
    try:
        repository = ExpenseRepository(session)
        deleted = await repository.delete(user_id, expense_id)
        await session.commit()

        if deleted:
            return f"Expense deleted successfully. ID: {expense_id}"
        else:
            return f"Expense not found. ID: {expense_id}"
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def _get_expense(user_id: str, expense_id: str) -> str:
    """Get a single expense."""
    if _session_factory is None:
        raise RuntimeError("Expense tools not configured")

    from src.infrastructure.database.repositories.expense_repository import ExpenseRepository

    session = _session_factory()
    try:
        repository = ExpenseRepository(session)
        expense = await repository.get_by_id(user_id, expense_id)

        if expense is None:
            return f"Expense not found. ID: {expense_id}"

        return json.dumps(expense.to_dict(), indent=2)
    finally:
        await session.close()


async def _list_expenses(
    user_id: str,
    limit: int = 10,
    offset: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """List user's expenses."""
    if _session_factory is None:
        raise RuntimeError("Expense tools not configured")

    from src.infrastructure.database.repositories.expense_repository import ExpenseRepository

    session = _session_factory()
    try:
        repository = ExpenseRepository(session)

        # Use date range if provided, otherwise list all
        if date_from or date_to:
            df = date.fromisoformat(date_from) if date_from else None
            dt = date.fromisoformat(date_to) if date_to else None
            expenses = await repository.list_by_date_range(user_id, df, dt, limit, offset)
        else:
            expenses = await repository.list_by_user(user_id, limit, offset)

        if not expenses:
            return "No expenses found."

        result = f"Found {len(expenses)} expense(s):\n\n"
        for i, exp in enumerate(expenses, 1):
            result += f"{i}. [{exp.id}] {exp.description}\n"
            result += f"   Amount: {exp.amount} {exp.currency}\n"
            result += f"   Category: {exp.category}\n"
            result += f"   Date: {exp.expense_date}\n"
            if exp.tags:
                result += f"   Tags: {', '.join(exp.tags)}\n"
            result += "\n"

        return result
    finally:
        await session.close()


async def _search_expenses(
    user_id: str,
    query: str | None = None,
    search_type: Literal["semantic", "category", "tags", "amount_range"] = "semantic",
    category: str | None = None,
    tags: list[str] | None = None,
    amount_min: float | int | str | None = None,
    amount_max: float | int | str | None = None,
    limit: int = 5,
) -> str:
    """Search expenses."""
    if _session_factory is None or _embedding_service is None:
        raise RuntimeError("Expense tools not configured")

    from src.infrastructure.database.repositories.expense_repository import ExpenseRepository

    session = _session_factory()
    try:
        repository = ExpenseRepository(session)

        if search_type == "semantic":
            query_embedding = await _embedding_service.generate_embedding(query)
            results = await repository.search_by_vector(user_id, query_embedding, limit)
            expenses = [exp for exp, _ in results]
        elif search_type == "category":
            expenses = await repository.search_by_category(user_id, category, limit)
        elif search_type == "tags":
            expenses = await repository.search_by_tags(user_id, tags, match_all=False, limit=limit)
        elif search_type == "amount_range":
            min_amt = Decimal(str(amount_min)) if amount_min is not None else None
            max_amt = Decimal(str(amount_max)) if amount_max is not None else None
            expenses = await repository.search_by_amount_range(user_id, min_amt, max_amt, limit)
        else:
            return f"Error: Unknown search_type '{search_type}'"

        if not expenses:
            return f"No expenses found matching your {search_type} search."

        result = f"Found {len(expenses)} expense(s) for {search_type} search:\n\n"
        for i, exp in enumerate(expenses, 1):
            result += f"{i}. [{exp.id}] {exp.description}\n"
            result += f"   Amount: {exp.amount} {exp.currency}\n"
            result += f"   Category: {exp.category}, Date: {exp.expense_date}\n\n"

        return result
    finally:
        await session.close()


async def _get_analytics(
    user_id: str,
    analytics_type: Literal["total_by_category", "monthly_summary"],
    year: int | None = None,
    month: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
) -> str:
    """Get expense analytics."""
    if _session_factory is None:
        raise RuntimeError("Expense tools not configured")

    from src.infrastructure.database.repositories.expense_repository import ExpenseRepository

    session = _session_factory()
    try:
        repository = ExpenseRepository(session)

        if analytics_type == "total_by_category":
            df = date.fromisoformat(date_from) if date_from else None
            dt = date.fromisoformat(date_to) if date_to else None
            totals = await repository.get_total_by_category(user_id, df, dt)

            if not totals:
                return "No expenses found in the specified date range."

            result = "Total expenses by category:\n\n"
            for cat, total in totals.items():
                result += f"- {cat}: {total} HKD\n"

            return result

        elif analytics_type == "monthly_summary":
            summary = await repository.get_monthly_summary(user_id, year, month)

            result = f"Monthly summary for {year}-{month:02d}:\n\n"
            result += f"Total: {summary['total']} HKD\n"
            result += f"Count: {summary['count']} expenses\n"
            result += f"Average: {summary['average']:.2f} HKD\n\n"

            if summary['by_category']:
                result += "By category:\n"
                for cat, total in summary['by_category'].items():
                    result += f"- {cat}: {total} HKD\n"

            return result

        else:
            return f"Error: Unknown analytics_type '{analytics_type}'"

    finally:
        await session.close()


# ========== Layer 1: Agent Interface ==========


def expense_tools(operation: str, **kwargs: Any) -> str:
    """Universal expense tracking tool for LLM agent.

    This is the single entry point for all expense operations. It validates
    inputs and routes to appropriate operation handlers.

    Operations:
    - create: Create new expense (amount, description, category, currency?, tags?, expense_date?, is_recurring?, recurrence_pattern?, receipt_path?)
    - update: Update existing expense (expense_id, amount?, currency?, description?, category?, tags?, expense_date?, is_recurring?, recurrence_pattern?, receipt_path?)
    - delete: Delete expense (expense_id)
    - get: Get single expense (expense_id)
    - list: List expenses (limit?, offset?, date_from?, date_to?)
    - search: Search expenses (query?, search_type, category?, tags?, amount_min?, amount_max?, limit?)
    - analytics: Get analytics (analytics_type, year?, month?, date_from?, date_to?, category?)

    Args:
        operation: Operation to perform
        **kwargs: Operation-specific arguments

    Returns:
        Operation result or error message (plain English)

    Examples:
        >>> expense_tools(operation="create", amount=150.50, description="Lunch", category="food")
        "Expense created successfully. ID: abc-123, Amount: 150.50 HKD, Category: 'food', Date: 2025-10-26"

        >>> expense_tools(operation="search", query="restaurant", search_type="semantic", limit=3)
        "Found 3 expense(s) for semantic search:..."

        >>> expense_tools(operation="analytics", analytics_type="monthly_summary", year=2025, month=10)
        "Monthly summary for 2025-10:..."
    """
    logger.info("expense_tools called with operation=%s, kwargs=%s", operation, kwargs)

    # Step 1: Validate
    validation_error = validate_operation(operation, **kwargs)
    if validation_error:
        logger.warning("Validation failed: %s", validation_error)
        return validation_error

    # Step 2: Execute operation
    try:
        user_id = _current_user_id

        async def _execute() -> str:
            """Execute the async operation."""
            if operation == "create":
                return await _create_expense(
                    user_id,
                    kwargs["amount"],
                    kwargs["description"],
                    kwargs["category"],
                    kwargs.get("currency", "HKD"),
                    kwargs.get("tags"),
                    kwargs.get("expense_date"),
                    kwargs.get("is_recurring", False),
                    kwargs.get("recurrence_pattern"),
                    kwargs.get("receipt_path"),
                )
            elif operation == "update":
                return await _update_expense(
                    user_id,
                    kwargs["expense_id"],
                    kwargs.get("amount"),
                    kwargs.get("currency"),
                    kwargs.get("description"),
                    kwargs.get("category"),
                    kwargs.get("tags"),
                    kwargs.get("expense_date"),
                    kwargs.get("is_recurring"),
                    kwargs.get("recurrence_pattern"),
                    kwargs.get("receipt_path"),
                )
            elif operation == "delete":
                return await _delete_expense(user_id, kwargs["expense_id"])
            elif operation == "get":
                return await _get_expense(user_id, kwargs["expense_id"])
            elif operation == "list":
                return await _list_expenses(
                    user_id,
                    kwargs.get("limit", 10),
                    kwargs.get("offset", 0),
                    kwargs.get("date_from"),
                    kwargs.get("date_to"),
                )
            elif operation == "search":
                return await _search_expenses(
                    user_id,
                    kwargs.get("query"),
                    kwargs.get("search_type", "semantic"),
                    kwargs.get("category"),
                    kwargs.get("tags"),
                    kwargs.get("amount_min"),
                    kwargs.get("amount_max"),
                    kwargs.get("limit", 5),
                )
            elif operation == "analytics":
                return await _get_analytics(
                    user_id,
                    kwargs["analytics_type"],
                    kwargs.get("year"),
                    kwargs.get("month"),
                    kwargs.get("date_from"),
                    kwargs.get("date_to"),
                    kwargs.get("category"),
                )
            else:
                return f"Error: Operation '{operation}' not implemented."

        # Run async code from sync context
        # nest_asyncio allows this to work even when called from async context (DSPy ReAct)
        result = asyncio.run(_execute())
        logger.info("Operation %s completed successfully", operation)
        return result

    except Exception as e:
        error_msg = f"Error executing {operation}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg
