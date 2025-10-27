"""PostgreSQL implementation of User repository.

This module implements the IUserRepository protocol using SQLAlchemy
and asyncpg for PostgreSQL database operations.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.infrastructure.database.models.user_model import UserModel

logger = logging.getLogger(__name__)


class UserRepository:
    """PostgreSQL implementation of User repository.

    This repository handles all database operations for User entities,
    including entity-to-model mapping and error handling.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    def _to_entity(self, model: UserModel) -> User:
        """Convert UserModel to User entity.

        Args:
            model: SQLAlchemy UserModel instance

        Returns:
            User entity instance
        """
        return User(
            id=model.id,
            phone_number=model.phone_number,
            display_name=model.display_name,
            preferences=model.preferences,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_active_at=model.last_active_at,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: User) -> UserModel:
        """Convert User entity to UserModel.

        Args:
            entity: User entity instance

        Returns:
            SQLAlchemy UserModel instance
        """
        return UserModel(
            id=entity.id,
            phone_number=entity.phone_number,
            display_name=entity.display_name,
            preferences=entity.preferences,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_active_at=entity.last_active_at,
            deleted_at=entity.deleted_at,
        )

    async def create(self, user: User) -> User:
        """Create a new user in the database.

        Args:
            user: User entity to create

        Returns:
            Created User entity

        Raises:
            ValueError: If user with same phone_number already exists
            RuntimeError: If database operation fails
        """
        try:
            # Check if user with phone number already exists
            existing = await self.get_by_phone_number(user.phone_number)
            if existing is not None:
                raise ValueError(
                    f"User with phone number {user.phone_number} already exists"
                )

            # Convert entity to model and add to session
            model = self._to_model(user)
            self.session.add(model)
            await self.session.flush()  # Flush to get any DB-generated values

            logger.info("Created user: %s (phone: %s)", model.id, model.phone_number)
            return self._to_entity(model)

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to create user: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to create user: {e}") from e

    async def get_by_id(self, user_id: str) -> User | None:
        """Retrieve a user by ID.

        Args:
            user_id: Unique identifier of the user

        Returns:
            User entity if found and not deleted, None otherwise

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            stmt = select(UserModel).where(
                UserModel.id == user_id,
                UserModel.deleted_at.is_(None),
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                logger.debug("User not found: %s", user_id)
                return None

            logger.debug("Retrieved user: %s", user_id)
            return self._to_entity(model)

        except Exception as e:
            logger.error("Failed to get user by ID: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get user by ID: {e}") from e

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        """Retrieve a user by phone number.

        Args:
            phone_number: WhatsApp phone number (unique identifier)

        Returns:
            User entity if found and not deleted, None otherwise

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            stmt = select(UserModel).where(
                UserModel.phone_number == phone_number,
                UserModel.deleted_at.is_(None),
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                logger.debug("User not found with phone: %s", phone_number)
                return None

            logger.debug("Retrieved user by phone: %s", phone_number)
            return self._to_entity(model)

        except Exception as e:
            logger.error("Failed to get user by phone number: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get user by phone number: {e}") from e

    async def update(self, user: User) -> User:
        """Update an existing user in the database.

        Args:
            user: User entity with updated fields

        Returns:
            Updated User entity

        Raises:
            ValueError: If user with given ID doesn't exist
            RuntimeError: If database operation fails
        """
        try:
            # Check if user exists
            existing = await self.get_by_id(user.id)
            if existing is None:
                raise ValueError(f"User with ID {user.id} not found")

            # Update the model
            stmt = (
                update(UserModel)
                .where(UserModel.id == user.id)
                .values(
                    phone_number=user.phone_number,
                    display_name=user.display_name,
                    preferences=user.preferences,
                    updated_at=user.updated_at,
                    last_active_at=user.last_active_at,
                    deleted_at=user.deleted_at,
                )
            )
            await self.session.execute(stmt)
            await self.session.flush()

            # Fetch updated user
            updated = await self.get_by_id(user.id)
            if updated is None:
                raise RuntimeError("Failed to retrieve updated user")

            logger.info("Updated user: %s", user.id)
            return updated

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to update user: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to update user: {e}") from e

    async def delete(self, user_id: str) -> bool:
        """Soft delete a user by ID.

        Args:
            user_id: Unique identifier of the user to delete

        Returns:
            True if user was deleted, False if user not found

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            # Check if user exists
            existing = await self.get_by_id(user_id)
            if existing is None:
                logger.debug("User not found for deletion: %s", user_id)
                return False

            # Soft delete by setting deleted_at timestamp
            stmt = (
                update(UserModel)
                .where(UserModel.id == user_id)
                .values(deleted_at=datetime.now(UTC))
            )
            await self.session.execute(stmt)
            await self.session.flush()

            logger.info("Soft deleted user: %s", user_id)
            return True

        except Exception as e:
            logger.error("Failed to delete user: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to delete user: {e}") from e

    async def update_last_active(self, user_id: str) -> None:
        """Update the last_active_at timestamp for a user.

        Args:
            user_id: Unique identifier of the user

        Raises:
            ValueError: If user with given ID doesn't exist
            RuntimeError: If database operation fails
        """
        try:
            # Check if user exists
            existing = await self.get_by_id(user_id)
            if existing is None:
                raise ValueError(f"User with ID {user_id} not found")

            # Update last_active_at timestamp
            stmt = (
                update(UserModel)
                .where(UserModel.id == user_id)
                .values(last_active_at=datetime.now(UTC))
            )
            await self.session.execute(stmt)
            await self.session.flush()

            logger.debug("Updated last_active_at for user: %s", user_id)

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to update last_active: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to update last_active: {e}") from e

    async def exists(self, phone_number: str) -> bool:
        """Check if a user with given phone number exists.

        Args:
            phone_number: WhatsApp phone number to check

        Returns:
            True if user exists (not soft-deleted), False otherwise

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            user = await self.get_by_phone_number(phone_number)
            return user is not None

        except Exception as e:
            logger.error("Failed to check user existence: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to check user existence: {e}") from e
