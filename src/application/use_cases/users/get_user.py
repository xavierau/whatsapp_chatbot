"""Get user use case.

This use case handles retrieving user information by ID or phone number.
"""

import logging

from src.domain.entities.user import User
from src.domain.repositories.user_repository import IUserRepository

logger = logging.getLogger(__name__)


class GetUserUseCase:
    """Use case for retrieving user information.

    This use case encapsulates the business logic for user retrieval.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        """Initialize the use case.

        Args:
            user_repository: Repository for user persistence
        """
        self.user_repository = user_repository

    async def execute_by_id(self, user_id: str) -> User | None:
        """Retrieve a user by ID.

        Args:
            user_id: Unique identifier of the user

        Returns:
            User entity if found, None otherwise

        Raises:
            RuntimeError: If user retrieval fails
        """
        try:
            user = await self.user_repository.get_by_id(user_id)

            if user is None:
                logger.debug("User not found: %s", user_id)
            else:
                logger.debug("User retrieved: %s", user_id)

            return user

        except Exception as e:
            logger.error("Failed to get user by ID: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get user by ID: {e}") from e

    async def execute_by_phone(self, phone_number: str) -> User | None:
        """Retrieve a user by phone number.

        Args:
            phone_number: WhatsApp phone number

        Returns:
            User entity if found, None otherwise

        Raises:
            RuntimeError: If user retrieval fails
        """
        try:
            user = await self.user_repository.get_by_phone_number(phone_number)

            if user is None:
                logger.debug("User not found with phone: %s", phone_number)
            else:
                logger.debug("User retrieved by phone: %s", phone_number)

            return user

        except Exception as e:
            logger.error("Failed to get user by phone: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get user by phone: {e}") from e

    async def get_or_create(
        self,
        phone_number: str,
        display_name: str | None = None,
    ) -> tuple[User, bool]:
        """Get existing user or create new one.

        This is a convenience method for WhatsApp integration where we
        want to ensure a user exists.

        Args:
            phone_number: WhatsApp phone number
            display_name: Optional display name for new users

        Returns:
            Tuple of (User entity, created flag)
            - created=True if user was created
            - created=False if user already existed

        Raises:
            RuntimeError: If operation fails
        """
        try:
            # Try to get existing user
            existing = await self.execute_by_phone(phone_number)

            if existing is not None:
                logger.debug("User already exists: %s", phone_number)
                # Update last_active timestamp
                await self.user_repository.update_last_active(existing.id)
                return existing, False

            # Create new user
            user = User.create(
                phone_number=phone_number,
                display_name=display_name,
            )
            created = await self.user_repository.create(user)

            logger.info("New user created: %s (phone: %s)", created.id, phone_number)
            return created, True

        except Exception as e:
            logger.error("Failed to get or create user: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get or create user: {e}") from e
