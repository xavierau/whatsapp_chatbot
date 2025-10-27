"""Close session use case.

This use case handles manually closing conversation sessions.
"""

import logging

from src.domain.repositories.session_repository import ISessionRepository

logger = logging.getLogger(__name__)


class CloseSessionUseCase:
    """Use case for closing sessions.

    This use case encapsulates the business logic for manual session closure.
    """

    def __init__(self, session_repository: ISessionRepository) -> None:
        """Initialize the use case.

        Args:
            session_repository: Repository for session persistence
        """
        self.session_repository = session_repository

    async def execute(self, session_id: str) -> bool:
        """Close a session.

        This method manually closes a session, setting its status to closed
        and recording the closure timestamp.

        Args:
            session_id: Unique identifier of the session to close

        Returns:
            True if session was closed, False if session not found

        Raises:
            RuntimeError: If session closure fails
        """
        try:
            closed = await self.session_repository.close_session(session_id)

            if closed:
                logger.info("Session closed: %s", session_id)
            else:
                logger.debug("Session not found for closure: %s", session_id)

            return closed

        except Exception as e:
            logger.error("Failed to close session: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to close session: {e}") from e

    async def close_user_sessions(
        self,
        user_id: str,
        close_all: bool = False,
    ) -> int:
        """Close sessions for a user.

        Args:
            user_id: Unique identifier of the user
            close_all: If True, close all sessions; if False, only close active

        Returns:
            Number of sessions closed

        Raises:
            RuntimeError: If operation fails
        """
        try:
            # Get user sessions
            sessions = await self.session_repository.get_user_sessions(
                user_id=user_id,
                limit=100,  # Reasonable limit to prevent excessive queries
                include_expired=close_all,
            )

            # Close each session
            closed_count = 0
            for session in sessions:
                if session.status != "closed":  # Avoid closing already closed sessions
                    success = await self.session_repository.close_session(session.id)
                    if success:
                        closed_count += 1

            logger.info(
                "Closed %d sessions for user: %s",
                closed_count,
                user_id,
            )

            return closed_count

        except Exception as e:
            logger.error("Failed to close user sessions: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to close user sessions: {e}") from e
