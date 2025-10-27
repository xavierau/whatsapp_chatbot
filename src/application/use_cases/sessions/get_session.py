"""Get session use case.

This use case handles retrieving session information by ID or user.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.entities.session import Session
from src.domain.repositories.session_repository import ISessionRepository

if TYPE_CHECKING:
    from src.application.use_cases.sessions.create_session import CreateSessionUseCase

logger = logging.getLogger(__name__)


class GetSessionUseCase:
    """Use case for retrieving session information.

    This use case encapsulates the business logic for session retrieval.
    """

    def __init__(self, session_repository: ISessionRepository) -> None:
        """Initialize the use case.

        Args:
            session_repository: Repository for session persistence
        """
        self.session_repository = session_repository

    async def execute_by_id(self, session_id: str) -> Session | None:
        """Retrieve a session by ID.

        Args:
            session_id: Unique identifier of the session

        Returns:
            Session entity if found, None otherwise

        Raises:
            RuntimeError: If session retrieval fails
        """
        try:
            session = await self.session_repository.get_by_id(session_id)

            if session is None:
                logger.debug("Session not found: %s", session_id)
            else:
                logger.debug("Session retrieved: %s", session_id)

            return session

        except Exception as e:
            logger.error("Failed to get session by ID: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get session by ID: {e}") from e

    async def get_active_session(self, user_id: str) -> Session | None:
        """Get the active session for a user.

        Args:
            user_id: Unique identifier of the user

        Returns:
            Active Session entity if found, None otherwise

        Raises:
            RuntimeError: If session retrieval fails
        """
        try:
            session = await self.session_repository.get_active_session_for_user(user_id)

            if session is None:
                logger.debug("No active session for user: %s", user_id)
            else:
                logger.debug(
                    "Active session retrieved: %s (user: %s)",
                    session.id,
                    user_id,
                )

            return session

        except Exception as e:
            logger.error("Failed to get active session: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get active session: {e}") from e

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[Session]:
        """Get session history for a user.

        Args:
            user_id: Unique identifier of the user
            limit: Maximum number of sessions to return
            include_expired: If True, include expired sessions

        Returns:
            List of Session entities, ordered by most recent first

        Raises:
            RuntimeError: If session retrieval fails
        """
        try:
            sessions = await self.session_repository.get_user_sessions(
                user_id=user_id,
                limit=limit,
                include_expired=include_expired,
            )

            logger.debug(
                "Retrieved %d sessions for user: %s",
                len(sessions),
                user_id,
            )

            return sessions

        except Exception as e:
            logger.error("Failed to get user sessions: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get user sessions: {e}") from e

    async def get_or_create_active(
        self,
        user_id: str,
        create_use_case: CreateSessionUseCase,
    ) -> tuple[Session, bool]:
        """Get active session or create new one.

        This is a convenience method for WhatsApp integration where we
        want to ensure an active session exists.

        Args:
            user_id: Unique identifier of the user
            create_use_case: CreateSessionUseCase instance for creating new sessions

        Returns:
            Tuple of (Session entity, created flag)
            - created=True if session was created
            - created=False if active session already existed

        Raises:
            RuntimeError: If operation fails
        """
        try:
            # Try to get existing active session
            existing = await self.get_active_session(user_id)

            if existing is not None:
                logger.debug("User already has active session: %s", user_id)
                # Update activity timestamp
                await self.session_repository.update_activity(existing.id)
                return existing, False

            # Create new session
            created = await create_use_case.execute(user_id)
            logger.info("New session created: %s (user: %s)", created.id, user_id)
            return created, True

        except Exception as e:
            logger.error("Failed to get or create session: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to get or create session: {e}") from e
