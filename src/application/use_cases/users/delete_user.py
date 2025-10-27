"""Delete user use case.

This use case handles soft deletion of users for audit compliance.
"""

import logging

from src.domain.repositories.user_repository import IUserRepository

logger = logging.getLogger(__name__)


class DeleteUserUseCase:
    """Use case for deleting users (soft delete).

    This use case encapsulates the business logic for user deletion,
    implementing soft delete for audit trails and GDPR compliance.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        """Initialize the use case.

        Args:
            user_repository: Repository for user persistence
        """
        self.user_repository = user_repository

    async def execute(self, user_id: str) -> bool:
        """Soft delete a user.

        This method marks the user as deleted without removing data,
        supporting audit trails and potential data recovery.

        Args:
            user_id: Unique identifier of the user to delete

        Returns:
            True if user was deleted, False if user not found

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            deleted = await self.user_repository.delete(user_id)

            if deleted:
                logger.info("User soft deleted: %s", user_id)
            else:
                logger.debug("User not found for deletion: %s", user_id)

            return deleted

        except Exception as e:
            logger.error("Failed to delete user: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to delete user: {e}") from e
