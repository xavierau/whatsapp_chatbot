"""Create user use case.

This use case handles the creation of new WhatsApp users with validation
and duplicate checking.
"""

import logging
from typing import Any

from src.domain.entities.user import User
from src.domain.repositories.user_repository import IUserRepository

logger = logging.getLogger(__name__)


class CreateUserUseCase:
    """Use case for creating a new user.

    This use case encapsulates the business logic for user creation,
    including validation and duplicate prevention.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        """Initialize the use case.

        Args:
            user_repository: Repository for user persistence
        """
        self.user_repository = user_repository

    async def execute(
        self,
        phone_number: str,
        display_name: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> User:
        """Create a new user.

        Args:
            phone_number: WhatsApp phone number (E.164 format recommended)
            display_name: Optional display name for the user
            preferences: Optional user preferences dict

        Returns:
            Created User entity

        Raises:
            ValueError: If phone number is invalid or already exists
            RuntimeError: If user creation fails
        """
        try:
            # Validate phone number format (basic validation)
            if not phone_number or not phone_number.strip():
                raise ValueError("Phone number cannot be empty")

            # Check if user already exists
            existing = await self.user_repository.get_by_phone_number(phone_number)
            if existing is not None:
                logger.warning("User creation failed: phone number already exists: %s", phone_number)
                raise ValueError(f"User with phone number {phone_number} already exists")

            # Create user entity
            user = User.create(
                phone_number=phone_number,
                display_name=display_name,
                preferences=preferences,
            )

            # Persist user
            created_user = await self.user_repository.create(user)

            logger.info(
                "User created successfully: %s (phone: %s)",
                created_user.id,
                created_user.phone_number,
            )

            return created_user

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to create user: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to create user: {e}") from e
