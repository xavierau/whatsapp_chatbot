"""Update user use case.

This use case handles updating user information such as display name
and preferences.
"""

import logging
from typing import Any

from src.domain.entities.user import User
from src.domain.repositories.user_repository import IUserRepository

logger = logging.getLogger(__name__)


class UpdateUserUseCase:
    """Use case for updating user information.

    This use case encapsulates the business logic for user updates.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        """Initialize the use case.

        Args:
            user_repository: Repository for user persistence
        """
        self.user_repository = user_repository

    async def execute(
        self,
        user_id: str,
        display_name: str | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> User:
        """Update user information.

        Args:
            user_id: Unique identifier of the user
            display_name: New display name (None to keep current)
            preferences: New preferences dict (None to keep current)

        Returns:
            Updated User entity

        Raises:
            ValueError: If user not found
            RuntimeError: If user update fails
        """
        try:
            # Get existing user
            user = await self.user_repository.get_by_id(user_id)
            if user is None:
                raise ValueError(f"User with ID {user_id} not found")

            # Update user entity (creates new instance due to immutability)
            updated_user = user.update(
                display_name=display_name,
                preferences=preferences,
            )

            # Persist updated user
            saved_user = await self.user_repository.update(updated_user)

            logger.info("User updated successfully: %s", user_id)

            return saved_user

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to update user: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to update user: {e}") from e

    async def update_preferences(
        self,
        user_id: str,
        preferences: dict[str, Any],
        merge: bool = True,
    ) -> User:
        """Update user preferences.

        Args:
            user_id: Unique identifier of the user
            preferences: Preferences to set or merge
            merge: If True, merge with existing preferences; if False, replace

        Returns:
            Updated User entity

        Raises:
            ValueError: If user not found
            RuntimeError: If update fails
        """
        try:
            # Get existing user
            user = await self.user_repository.get_by_id(user_id)
            if user is None:
                raise ValueError(f"User with ID {user_id} not found")

            # Merge or replace preferences
            if merge and user.preferences:
                new_preferences = {**user.preferences, **preferences}
            else:
                new_preferences = preferences

            # Update user
            updated_user = user.update(preferences=new_preferences)
            saved_user = await self.user_repository.update(updated_user)

            logger.info("User preferences updated: %s", user_id)

            return saved_user

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to update user preferences: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to update user preferences: {e}") from e
