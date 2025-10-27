"""User repository protocol (interface).

This module defines the repository interface for User entity following
the Repository pattern and Dependency Inversion Principle (SOLID).
"""

from typing import Protocol

from src.domain.entities.user import User


class IUserRepository(Protocol):
    """Interface for User repository.

    This protocol defines the contract that any User repository implementation
    must follow, enabling dependency injection and testability.
    """

    async def create(self, user: User) -> User:
        """Create a new user in the repository.

        Args:
            user: User entity to create

        Returns:
            Created User entity with any repository-generated fields

        Raises:
            ValueError: If user with same phone_number already exists
            RuntimeError: If database operation fails
        """
        ...

    async def get_by_id(self, user_id: str) -> User | None:
        """Retrieve a user by ID.

        Args:
            user_id: Unique identifier of the user

        Returns:
            User entity if found, None otherwise (excludes soft-deleted users)

        Raises:
            RuntimeError: If database operation fails
        """
        ...

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        """Retrieve a user by phone number.

        Args:
            phone_number: WhatsApp phone number (unique identifier)

        Returns:
            User entity if found, None otherwise (excludes soft-deleted users)

        Raises:
            RuntimeError: If database operation fails
        """
        ...

    async def update(self, user: User) -> User:
        """Update an existing user in the repository.

        Args:
            user: User entity with updated fields

        Returns:
            Updated User entity

        Raises:
            ValueError: If user with given ID doesn't exist
            RuntimeError: If database operation fails
        """
        ...

    async def delete(self, user_id: str) -> bool:
        """Soft delete a user by ID.

        This method marks the user as deleted without actually removing it
        from the database, supporting audit trails and GDPR compliance.

        Args:
            user_id: Unique identifier of the user to delete

        Returns:
            True if user was deleted, False if user not found

        Raises:
            RuntimeError: If database operation fails
        """
        ...

    async def update_last_active(self, user_id: str) -> None:
        """Update the last_active_at timestamp for a user.

        This is a convenience method for updating user activity without
        loading the entire entity.

        Args:
            user_id: Unique identifier of the user

        Raises:
            ValueError: If user with given ID doesn't exist
            RuntimeError: If database operation fails
        """
        ...

    async def exists(self, phone_number: str) -> bool:
        """Check if a user with given phone number exists.

        Args:
            phone_number: WhatsApp phone number to check

        Returns:
            True if user exists (not soft-deleted), False otherwise

        Raises:
            RuntimeError: If database operation fails
        """
        ...
