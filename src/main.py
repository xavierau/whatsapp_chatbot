"""Main application entry point."""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langfuse import Langfuse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.conversation_agent import ConversationContext, Message
from src.application.use_cases.messages.get_conversation_history import (
    GetConversationHistoryUseCase,
)
from src.application.use_cases.messages.store_message import StoreMessageUseCase
from src.application.use_cases.sessions.create_session import CreateSessionUseCase
from src.application.use_cases.sessions.get_session import GetSessionUseCase
from src.application.use_cases.users.get_user import GetUserUseCase
from src.config.settings import settings
from src.infrastructure.database.repositories.message_repository import (
    MessageRepository,
)
from src.infrastructure.database.repositories.session_repository import (
    SessionRepository,
)
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.session import get_db, get_session_maker
from src.infrastructure.llm.conversation_agent import ConversationAgent
from src.infrastructure.llm.embedding.gemini_embedding_service import GeminiEmbeddingService
from src.infrastructure.llm.tools.notes import configure_note_tools
from src.interface.api.schemas.messages import MessageRequest, MessageResponse
from openinference.instrumentation.dspy import DSPyInstrumentor


# Set Langfuse environment variables for @observe decorator
# The @observe decorator reads directly from environment variables, not from settings
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
os.environ["LANGFUSE_HOST"] = settings.langfuse_host

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

langfuse_client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        environment=settings.environment,
    )

DSPyInstrumentor().instrument()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events.

    This context manager handles:
    - Langfuse client initialization on startup
    - Note tools configuration (repository + embedding service)
    - Langfuse client cleanup on shutdown
    """
    # Startup: Initialize Langfuse
    logger.info("Initializing Langfuse observability...")

    logger.info(
        f"Langfuse initialized successfully (environment: {settings.environment}, host: {settings.langfuse_host})"
    )

    # Store client in app state for access in endpoints if needed
    app.state.langfuse = langfuse_client

    # Initialize note tools with session factory and embedding service
    logger.info("Configuring note tools...")
    try:
        # Create embedding service (singleton)
        embedding_service = GeminiEmbeddingService(
            api_key=settings.gemini_api_key,
            model_name="gemini-embedding-001",
        )

        # Get async session maker for creating sessions on-demand
        session_maker = get_session_maker()

        # Configure note tools with session factory
        # Each operation will create its own session to avoid concurrency issues
        configure_note_tools(
            session_factory=session_maker,
            embedding_service=embedding_service,
        )

        logger.info("Note tools configured successfully with session factory")
    except Exception as e:
        logger.error(f"Failed to configure note tools: {e}", exc_info=True)
        # Don't raise - allow app to start even if note tools fail
        logger.warning("Application starting without note tools functionality")

    yield  # Application is running

    # Shutdown: Cleanup Langfuse
#     logger.info("Shutting down Langfuse...")
#     langfuse_client.flush()
#     logger.info("Langfuse shutdown complete")


# Create FastAPI application with lifespan
app = FastAPI(
    title="WhatsApp AI Chatbot",
    description="AI-powered WhatsApp chatbot using DSPy and Gemini LLM",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Initialize conversation agent (singleton pattern for the application)
conversation_agent = ConversationAgent()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "WhatsApp AI Chatbot API",
        "version": "0.1.0",
    }


@app.post("/messages", response_model=MessageResponse)
async def messages(
    request: MessageRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Handle incoming messages and generate responses using conversation agent.

    This endpoint:
    1. Gets or creates user by phone number
    2. Gets or creates active session for the user
    3. Retrieves conversation history from database
    4. Generates AI response using conversation agent
    5. Stores both user message and assistant response in database
    6. Tracks LLM response time for analytics

    Args:
        request: MessageRequest containing user_id, session_id, and message
        db: Database session (injected by FastAPI)

    Returns:
        MessageResponse containing the agent's response and metadata

    Raises:
        HTTPException: If message processing fails
    """
    try:
        # Initialize repositories
        user_repo = UserRepository(db)
        session_repo = SessionRepository(db)
        message_repo = MessageRepository(db)

        # Initialize use cases
        get_user = GetUserUseCase(user_repo)
        create_session = CreateSessionUseCase(session_repo, user_repo)
        get_session = GetSessionUseCase(session_repo)
        store_message = StoreMessageUseCase(message_repo, session_repo)
        get_history = GetConversationHistoryUseCase(message_repo)

        # Get or create user (using user_id as phone_number for now)
        # In production, you'd extract phone from WhatsApp webhook
        user, user_created = await get_user.get_or_create(
            phone_number=request.user_id,
            display_name=None,
        )

        # Get or create active session
        session, session_created = await get_session.get_or_create_active(
            user_id=user.id,
            create_use_case=create_session,
        )

        # Override session_id in request with actual session ID
        actual_session_id = session.id

        # Store user message first
        await store_message.store_user_message(
            session_id=actual_session_id,
            content=request.message,
        )

        # Get conversation history from database
        history_messages = await get_history.execute(
            session_id=actual_session_id,
            max_messages=20,
        )

        logger.info(
            f"history: {history_messages}"
        )

        # Convert domain Message entities to conversation agent Message format
        history = [
            Message(
                role=msg.role.value,
                content=msg.content,
                metadata=msg.metadata,
            )
            for msg in history_messages
        ]

        # Get user preferences (will implement later)
        user_preference = user.preferences.get("preference", "") if user.preferences else ""

        # Create conversation context
        context = ConversationContext(
            current_message=request.message,
            history=tuple(history[:-1]),  # Exclude the user message we just stored
            user_preference=user_preference,
            metadata={
                "user_id": user.id,
                "session_id": actual_session_id,
            },
        )

        # Track response time
        start_time = time.time()

        # Generate response using conversation agent (async for better performance)
        agent_response = await conversation_agent.agenerate_response(context)

        # Calculate response time in milliseconds
        response_time_ms = int((time.time() - start_time) * 1000)

        # Store assistant response with tool results and response time
        tool_result = (
            agent_response.metadata.get("tool_results") if agent_response.metadata else None
        )
        await store_message.store_assistant_message(
            session_id=actual_session_id,
            content=agent_response.content,
            tool_result=tool_result,
            response_time_ms=response_time_ms,
        )

        # Return response
        return MessageResponse(
            response=agent_response.content,
            session_id=actual_session_id,
            metadata={
                **(agent_response.metadata or {}),
                "user_created": user_created,
                "session_created": session_created,
                "response_time_ms": response_time_ms,
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}") from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
    )
