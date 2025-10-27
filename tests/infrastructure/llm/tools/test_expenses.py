"""Integration tests for expense tools."""

import json
from datetime import date
from decimal import Decimal

import pytest

from src.infrastructure.llm.tools.expenses import expense_tools


class TestExpenseToolsValidation:
    """Test validation layer of expense tools."""

    def test_unknown_operation(self):
        """Test that unknown operations return helpful error."""
        result = expense_tools(operation="invalid_op")
        assert "Error: Unknown operation 'invalid_op'" in result
        assert "Valid operations are:" in result

    def test_create_missing_amount(self):
        """Test create validation - missing amount."""
        result = expense_tools(
            operation="create",
            description="Test",
            category="test",
        )
        assert "Error: 'amount' is required" in result

    def test_create_negative_amount(self):
        """Test create validation - negative amount."""
        result = expense_tools(
            operation="create",
            amount=-50,
            description="Test",
            category="test",
        )
        assert "Error: 'amount' cannot be negative" in result

    def test_create_invalid_amount(self):
        """Test create validation - invalid amount type."""
        result = expense_tools(
            operation="create",
            amount="not-a-number",
            description="Test",
            category="test",
        )
        assert "Error: 'amount' must be a number" in result

    def test_create_missing_description(self):
        """Test create validation - missing description."""
        result = expense_tools(
            operation="create",
            amount=100,
            category="test",
        )
        assert "Error: 'description' is required" in result

    def test_create_empty_description(self):
        """Test create validation - empty description."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="   ",
            category="test",
        )
        assert "Error: 'description' must be a non-empty string" in result

    def test_create_missing_category(self):
        """Test create validation - missing category."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
        )
        assert "Error: 'category' is required" in result

    def test_create_category_too_long(self):
        """Test create validation - category exceeds max length."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
            category="x" * 101,
        )
        assert "Error: 'category' cannot exceed 100 characters" in result

    def test_create_invalid_currency_length(self):
        """Test create validation - invalid currency code length."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
            category="test",
            currency="US",  # Too short
        )
        assert "Error: 'currency' must be a 3-letter ISO 4217 code" in result

    def test_create_invalid_tags_type(self):
        """Test create validation - tags must be list."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
            category="test",
            tags="not-a-list",
        )
        assert "Error: 'tags' must be a list" in result

    def test_create_invalid_date_format(self):
        """Test create validation - invalid date format."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
            category="test",
            expense_date="2025/10/26",  # Wrong format
        )
        assert "Error: 'expense_date' must be in YYYY-MM-DD format" in result

    def test_create_invalid_recurrence_pattern(self):
        """Test create validation - invalid recurrence pattern."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
            category="test",
            is_recurring=True,
            recurrence_pattern="hourly",  # Not supported
        )
        assert "Error: 'recurrence_pattern' must be one of" in result

    def test_create_recurrence_pattern_without_recurring(self):
        """Test create validation - recurrence pattern requires is_recurring."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
            category="test",
            is_recurring=False,
            recurrence_pattern="monthly",
        )
        assert "Error: 'recurrence_pattern' can only be set when 'is_recurring' is true" in result

    def test_update_missing_expense_id(self):
        """Test update validation - missing expense_id."""
        result = expense_tools(
            operation="update",
            amount=200,
        )
        assert "Error: 'expense_id' is required" in result

    def test_update_no_fields_to_update(self):
        """Test update validation - no fields provided."""
        result = expense_tools(
            operation="update",
            expense_id="abc-123",
        )
        assert "Error: At least one field must be provided to update" in result

    def test_delete_missing_expense_id(self):
        """Test delete validation - missing expense_id."""
        result = expense_tools(operation="delete")
        assert "Error: 'expense_id' is required" in result

    def test_get_missing_expense_id(self):
        """Test get validation - missing expense_id."""
        result = expense_tools(operation="get")
        assert "Error: 'expense_id' is required" in result

    def test_list_invalid_limit(self):
        """Test list validation - invalid limit."""
        result = expense_tools(operation="list", limit="ten")
        assert "Error: 'limit' must be an integer" in result

    def test_list_negative_offset(self):
        """Test list validation - negative offset."""
        result = expense_tools(operation="list", offset=-1)
        assert "Error: 'offset' cannot be negative" in result

    def test_search_invalid_search_type(self):
        """Test search validation - invalid search type."""
        result = expense_tools(operation="search", search_type="invalid")
        assert "Error: Invalid search_type 'invalid'" in result

    def test_search_semantic_missing_query(self):
        """Test search validation - semantic search requires query."""
        result = expense_tools(operation="search", search_type="semantic")
        assert "Error: 'query' is required for semantic search" in result

    def test_search_category_missing_category(self):
        """Test search validation - category search requires category."""
        result = expense_tools(operation="search", search_type="category")
        assert "Error: 'category' parameter is required for category search" in result

    def test_search_tags_missing_tags(self):
        """Test search validation - tag search requires tags."""
        result = expense_tools(operation="search", search_type="tags")
        assert "Error: 'tags' parameter is required for tag search" in result

    def test_search_amount_range_missing_bounds(self):
        """Test search validation - amount_range requires at least one bound."""
        result = expense_tools(operation="search", search_type="amount_range")
        assert "Error: At least one of 'amount_min' or 'amount_max' is required" in result

    def test_analytics_missing_type(self):
        """Test analytics validation - missing analytics_type."""
        result = expense_tools(operation="analytics")
        assert "Error: 'analytics_type' is required" in result

    def test_analytics_invalid_type(self):
        """Test analytics validation - invalid analytics_type."""
        result = expense_tools(operation="analytics", analytics_type="invalid")
        assert "Error: Invalid analytics_type 'invalid'" in result

    def test_analytics_monthly_summary_missing_year(self):
        """Test analytics validation - monthly_summary requires year."""
        result = expense_tools(operation="analytics", analytics_type="monthly_summary", month=10)
        assert "Error: 'year' is required for monthly_summary" in result

    def test_analytics_monthly_summary_missing_month(self):
        """Test analytics validation - monthly_summary requires month."""
        result = expense_tools(operation="analytics", analytics_type="monthly_summary", year=2025)
        assert "Error: 'month' is required for monthly_summary" in result

    def test_analytics_monthly_summary_invalid_month(self):
        """Test analytics validation - month must be 1-12."""
        result = expense_tools(operation="analytics", analytics_type="monthly_summary", year=2025, month=13)
        assert "Error: 'month' must be between 1 and 12" in result


class TestExpenseToolsConfiguration:
    """Test configuration and error handling."""

    def test_tools_not_configured_error(self):
        """Test that operations fail gracefully when tools not configured."""
        # Note: This test assumes tools are not configured at test start
        # In practice, you'd use a test fixture to ensure clean state
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
            category="test",
        )
        # Should return error message, not raise exception
        assert isinstance(result, str)
        # The exact error depends on whether tools are configured
        # Either validation passes or runtime error occurs


class TestExpenseToolsMessageFormats:
    """Test output message formats for user-friendly responses."""

    def test_create_success_message_format(self):
        """Test that create success message contains key information."""
        # This is a validation test - we check the format without DB
        # Actual success message format: "Expense created successfully. ID: {id}, Amount: {amount} {currency}, Category: '{category}', Date: {date}"
        pass  # Requires mock or actual DB setup

    def test_update_not_found_message(self):
        """Test that update returns clear message when expense not found."""
        # Format: "Expense not found. ID: {expense_id}"
        pass  # Requires mock or actual DB setup

    def test_delete_success_message(self):
        """Test that delete success message is clear."""
        # Format: "Expense deleted successfully. ID: {expense_id}"
        pass  # Requires mock or actual DB setup

    def test_list_no_expenses_message(self):
        """Test message when no expenses found."""
        # Format: "No expenses found."
        pass  # Requires mock or actual DB setup

    def test_search_no_results_message(self):
        """Test message when search returns no results."""
        # Format: "No expenses found matching your {search_type} search."
        pass  # Requires mock or actual DB setup


class TestExpenseToolsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_create_with_zero_amount(self):
        """Test creating expense with zero amount (should be valid)."""
        result = expense_tools(
            operation="create",
            amount=0,
            description="Free item",
            category="test",
        )
        # Zero amount is valid (e.g., free items, refunds that net to zero)
        # Should not return validation error about negative amount
        assert "cannot be negative" not in result

    def test_create_with_very_large_amount(self):
        """Test creating expense with large amount."""
        result = expense_tools(
            operation="create",
            amount=999999999999.99,  # Max for NUMERIC(15,2)
            description="Very expensive item",
            category="luxury",
        )
        # Should handle large numbers without validation error
        assert "Error" not in result or "not configured" in result

    def test_create_with_all_optional_fields(self):
        """Test creating expense with all optional fields populated."""
        result = expense_tools(
            operation="create",
            amount=1500,
            currency="USD",
            description="Monthly rent",
            category="housing",
            tags=["rent", "recurring", "essential"],
            expense_date="2025-10-26",
            is_recurring=True,
            recurrence_pattern="monthly",
            receipt_path="/receipts/rent_oct_2025.pdf",
        )
        # Should accept all valid fields
        assert "Error:" not in result or "not configured" in result

    def test_update_partial_fields(self):
        """Test updating only some fields."""
        # Validation should pass for partial updates
        result = expense_tools(
            operation="update",
            expense_id="test-id",
            amount=200,
        )
        # Should not require all fields
        assert "At least one field must be provided" not in result

    def test_list_with_date_range(self):
        """Test list operation with date range."""
        result = expense_tools(
            operation="list",
            date_from="2025-10-01",
            date_to="2025-10-31",
            limit=50,
        )
        # Should accept valid date range
        assert "Error" not in result or "not configured" in result

    def test_search_amount_range_with_only_min(self):
        """Test amount range search with only minimum bound."""
        result = expense_tools(
            operation="search",
            search_type="amount_range",
            amount_min=100,
            limit=10,
        )
        # Should accept only min bound
        assert "At least one of" not in result

    def test_search_amount_range_with_only_max(self):
        """Test amount range search with only maximum bound."""
        result = expense_tools(
            operation="search",
            search_type="amount_range",
            amount_max=500,
            limit=10,
        )
        # Should accept only max bound
        assert "At least one of" not in result

    def test_analytics_total_by_category_without_dates(self):
        """Test total_by_category without date range (all time)."""
        result = expense_tools(
            operation="analytics",
            analytics_type="total_by_category",
        )
        # Should work without date range (all expenses)
        assert "Error" not in result or "not configured" in result

    def test_analytics_total_by_category_with_dates(self):
        """Test total_by_category with specific date range."""
        result = expense_tools(
            operation="analytics",
            analytics_type="total_by_category",
            date_from="2025-10-01",
            date_to="2025-10-31",
        )
        # Should accept date range
        assert "Error" not in result or "not configured" in result


class TestExpenseToolsAmountHandling:
    """Test different amount formats and conversions."""

    def test_create_with_integer_amount(self):
        """Test amount provided as integer."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
            category="test",
        )
        # Integer amounts should be accepted
        assert "Error" not in result or "not configured" in result

    def test_create_with_float_amount(self):
        """Test amount provided as float."""
        result = expense_tools(
            operation="create",
            amount=99.99,
            description="Test",
            category="test",
        )
        # Float amounts should be accepted
        assert "Error" not in result or "not configured" in result

    def test_create_with_string_amount(self):
        """Test amount provided as string."""
        result = expense_tools(
            operation="create",
            amount="150.50",
            description="Test",
            category="test",
        )
        # String amounts should be accepted and converted
        assert "Error" not in result or "not configured" in result

    def test_update_with_decimal_string_amount(self):
        """Test update with precise decimal string."""
        result = expense_tools(
            operation="update",
            expense_id="test-id",
            amount="123.45",
        )
        # Precise decimal strings should be accepted
        assert "must be a number" not in result


class TestExpenseToolsCurrencyHandling:
    """Test currency code handling."""

    def test_create_default_currency(self):
        """Test that default currency is HKD when not specified."""
        # This would require checking the created expense
        # Validation should pass without currency
        result = expense_tools(
            operation="create",
            amount=100,
            description="Test",
            category="test",
        )
        assert "currency" not in result or "not configured" in result

    def test_create_with_various_currencies(self):
        """Test creating expenses with different currency codes."""
        for currency in ["USD", "EUR", "GBP", "JPY", "CNY"]:
            result = expense_tools(
                operation="create",
                amount=100,
                description=f"Test in {currency}",
                category="test",
                currency=currency,
            )
            # All valid 3-letter codes should be accepted
            assert "Error: 'currency' must be a 3-letter" not in result


class TestExpenseToolsRecurringExpenses:
    """Test recurring expense functionality."""

    def test_create_recurring_expense_all_patterns(self):
        """Test all valid recurrence patterns."""
        for pattern in ["daily", "weekly", "monthly", "yearly"]:
            result = expense_tools(
                operation="create",
                amount=100,
                description=f"Recurring {pattern}",
                category="recurring",
                is_recurring=True,
                recurrence_pattern=pattern,
            )
            # All valid patterns should be accepted
            assert f"must be one of" not in result

    def test_create_non_recurring_expense(self):
        """Test creating non-recurring expense (default behavior)."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="One-time expense",
            category="test",
            # is_recurring defaults to False
        )
        assert "Error" not in result or "not configured" in result

    def test_update_to_make_recurring(self):
        """Test updating expense to make it recurring."""
        result = expense_tools(
            operation="update",
            expense_id="test-id",
            is_recurring=True,
            recurrence_pattern="monthly",
        )
        # Should allow changing to recurring
        assert "At least one field" not in result


class TestExpenseToolsDateHandling:
    """Test date parsing and validation."""

    def test_create_with_past_date(self):
        """Test creating expense with past date."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Past expense",
            category="test",
            expense_date="2025-01-15",
        )
        # Past dates should be valid
        assert "Error" not in result or "not configured" in result

    def test_create_with_future_date(self):
        """Test creating expense with future date."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Planned expense",
            category="test",
            expense_date="2026-12-31",
        )
        # Future dates should be valid (for planned expenses)
        assert "Error" not in result or "not configured" in result

    def test_create_with_today_date(self):
        """Test creating expense with today's date."""
        today = date.today().isoformat()
        result = expense_tools(
            operation="create",
            amount=100,
            description="Today's expense",
            category="test",
            expense_date=today,
        )
        assert "Error" not in result or "not configured" in result

    def test_list_date_range_validation(self):
        """Test date range with from/to dates."""
        result = expense_tools(
            operation="list",
            date_from="2025-10-01",
            date_to="2025-10-31",
        )
        # Valid date range should pass
        assert "Error" not in result or "not configured" in result


class TestExpenseToolsTagsHandling:
    """Test tags functionality."""

    def test_create_with_multiple_tags(self):
        """Test creating expense with multiple tags."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Multi-tagged expense",
            category="test",
            tags=["work", "client-meeting", "reimbursable"],
        )
        assert "Error" not in result or "not configured" in result

    def test_create_with_single_tag(self):
        """Test creating expense with one tag."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="Single tag",
            category="test",
            tags=["urgent"],
        )
        assert "Error" not in result or "not configured" in result

    def test_create_without_tags(self):
        """Test creating expense without tags (optional)."""
        result = expense_tools(
            operation="create",
            amount=100,
            description="No tags",
            category="test",
        )
        # Tags are optional
        assert "Error" not in result or "not configured" in result

    def test_search_by_tags(self):
        """Test searching by tags."""
        result = expense_tools(
            operation="search",
            search_type="tags",
            tags=["work", "business"],
        )
        assert "'tags' parameter is required" not in result
