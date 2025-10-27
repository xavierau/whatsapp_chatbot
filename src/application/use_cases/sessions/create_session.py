"""Create session use case.

This use case handles creating new conversation sessions for users.
"""

import logging

from src.domain.entities.session import Session
from src.domain.repositories.session_repository import ISessionRepository
from src.domain.repositories.user_repository import IUserRepository

logger = logging.getLogger(__name__)


class CreateSessionUseCase:
    """Use case for creating a new session.

    This use case encapsulates the business logic for session creation,
    including user validation and optional auto-closing of existing sessions.
    """

    def __init__(
        self,
        session_repository: ISessionRepository,
        user_repository: IUserRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            session_repository: Repository for session persistence
            user_repository: Repository for user validation
        """
        self.session_repository = session_repository
        self.user_repository = user_repository

    async def execute(
        self,
        user_id: str,
        close_existing: bool = False,
    ) -> Session:
        """Create a new session for a user.

        Args:
            user_id: Unique identifier of the user
            close_existing: If True, close any existing active session

        Returns:
            Created Session entity

        Raises:
            ValueError: If user not found
            RuntimeError: If session creation fails
        """
        try:
            # Validate user exists
            user = await self.user_repository.get_by_id(user_id)
            if user is None:
                raise ValueError(f"User with ID {user_id} not found")

            # Handle existing active session
            existing = await self.session_repository.get_active_session_for_user(user_id)
            if existing is not None:
                if close_existing:
                    await self.session_repository.close_session(existing.id)
                    logger.info("Closed existing session: %s", existing.id)
                else:
                    logger.info("User already has active session: %s", existing.id)
                    return existing

            # Create new session
            session = Session.create(user_id=user_id)
            created = await self.session_repository.create(session)

            logger.info(
                "Session created successfully: %s (user: %s)",
                created.id,
                user_id,
            )

            return created

        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to create session: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to create session: {e}") from e
