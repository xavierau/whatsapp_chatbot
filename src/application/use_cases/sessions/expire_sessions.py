"""Expire sessions use case.

This use case handles automatic expiration of inactive sessions.
Designed to be run as a background task.
"""

import logging

from src.domain.repositories.session_repository import ISessionRepository

logger = logging.getLogger(__name__)


class ExpireSessionsUseCase:
    """Use case for expiring inactive sessions.

    This use case encapsulates the business logic for automatic session
    expiration based on inactivity timeout. Intended for background tasks.
    """

    def __init__(self, session_repository: ISessionRepository) -> None:
        """Initialize the use case.

        Args:
            session_repository: Repository for session persistence
        """
        self.session_repository = session_repository

    async def execute(self, timeout_minutes: int = 30) -> int:
        """Expire inactive sessions.

        This method marks all active sessions that have been inactive for
        longer than the timeout period as expired.

        Args:
            timeout_minutes: Inactivity timeout in minutes (default: 30)

        Returns:
            Number of sessions expired

        Raises:
            ValueError: If timeout_minutes is invalid
            RuntimeError: If expiration fails
        """
        try:
            if timeout_minutes <= 0:
                raise ValueError("Timeout minutes must be positive")

            expired_count = await self.session_repository.expire_inactive_sessions(
                timeout_minutes=timeout_minutes
            )

            if expired_count > 0:
                logger.info(
                    "Expired %d inactive sessions (timeout: %d minutes)",
                    expired_count,
                    timeout_minutes,
                )
            else:
                logger.debug(
                    "No sessions to expire (timeout: %d minutes)",
                    timeout_minutes,
                )

            return expired_count

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to expire sessions: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to expire sessions: {e}") from e
