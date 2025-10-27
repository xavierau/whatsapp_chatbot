"""ConversationAgent DSPy Module Implementation.

This module implements a conversation agent using DSPy framework with:
- Pydantic-based signatures for type safety
- SOLID principles for maintainability
- Proper error handling and logging
- Support for conversation history and context
"""

import logging
from typing import Any

import dspy
from langfuse import get_client, observe

from src.application.interfaces.conversation_agent import (
    AgentResponse,
    ConversationContext,
    Message,
)
from src.config.settings import settings
from src.infrastructure.llm.tools import compute, expense_tools, jot, note_tools

logger = logging.getLogger(__name__)

# Initialize Langfuse client for trace tracking
langfuse_client = get_client()

# Sofia's system prompt - defines personality and capabilities
SOFIA_SYSTEM_PROMPT = """You are Sofia, a personal assistant with a warm, friendly, and professional personality.

Core characteristics:
- Name: Sofia
- Role: Personal assistant dedicated to helping users with their daily tasks and information needs
- Personality: Friendly, warm, and professional - you create a welcoming atmosphere while maintaining professionalism
- Communication style: Use emojis naturally to add warmth and clarity to your responses 😊
- Capabilities: You are equipped with powerful tools including:
  * Advanced computation for math, statistics, finance, and engineering problems
  * Note-taking system with smart search to remember important information
  * Expense tracking with categories, tags, search, and analytics for managing personal finances
  * Multi-hop reasoning for complex questions that require multiple steps

Your approach:
- Be conversational and approachable while staying helpful and efficient
- Use emojis to add personality and make interactions more engaging
- Leverage your tools proactively when they can help solve problems
- Remember context from conversations and notes to provide personalized assistance
- Help users track and analyze their expenses to maintain financial awareness
- Always aim to be helpful, accurate, and trustworthy"""


class ConversationSignature(dspy.Signature):
    """Generate contextual responses as Sofia, your personal assistant."""

    __doc__ = SOFIA_SYSTEM_PROMPT

    current_message: str = dspy.InputField(desc="The current user message that needs a response")
    conversation_history: str = dspy.InputField(
        desc=(
            "Previous conversation messages formatted as: "
            "'User: <message>\\nAssistant: <response>\\n...'. "
            "Use 'No previous conversation.' if there is no history."
        ),
        default="No previous conversation.",
    )
    user_preference: str = dspy.InputField(
        desc="Optional user preferences to consider when generating the response",
        default="",
    )
    playbook: str = dspy.InputField(
        desc="The information it needs to answer questions and execute tasks",
        default="",
    )

    response: str = dspy.OutputField(
        desc="A helpful, contextual response to the user's current message"
    )


class ConversationAgent(dspy.Module):
    """DSPy-based conversation agent for WhatsApp chatbot.

    This agent implements the IConversationAgent Protocol and uses DSPy's
    ReAct module for generating contextual responses with tools.

    Attributes:
        model: LLM model identifier
        temperature: Temperature parameter for response generation
        max_tokens: Maximum tokens for response generation
        _generator: DSPy ChainOfThought module for response generation
    """

    def __init__(self, model: str | None = None, **config_kwargs: Any) -> None:
        """Initialize the ConversationAgent.

        Args:
            model: Optional LLM model identifier (defaults to settings)
            **config_kwargs: Additional configuration parameters
        """
        super().__init__()

        # Store configuration as instance variables (DSPy-compatible)
        self.model = model or settings.default_llm_model
        self.temperature = config_kwargs.get("temperature", settings.llm_temperature)
        self.max_tokens = config_kwargs.get("max_tokens", settings.llm_max_tokens)
        self._extra_config = {
            k: v for k, v in config_kwargs.items() if k not in ("temperature", "max_tokens")
        }

        # Initialize DSPy language model
        self._initialize_dspy()

        # Initialize tools for the ReAct agent
        tools = [
            compute,  # For complex computational problems (math, stats, finance, engineering)
            jot,  # For working memory and multi-hop reasoning
            note_tools,  # For note-taking with vector search (create, update, delete, get, list, search)
            expense_tools,  # For expense tracking (create, update, delete, get, list, search, analytics)
        ]

        # Initialize the ReAct generator with tools
        self._generator = dspy.ReAct(ConversationSignature, tools=tools)

        logger.info(
            "ConversationAgent initialized with model=%s, temperature=%s, max_tokens=%s, tools=%d",
            self.model,
            self.temperature,
            self.max_tokens,
            len(tools),
        )

    def _initialize_dspy(self) -> None:
        """Initialize DSPy with the configured language model.

        Raises:
            RuntimeError: If DSPy initialization fails
        """
        try:
            self.lm = dspy.LM(
                model=self.model,
                api_key=settings.gemini_api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            logger.debug("DSPy configured successfully with model: %s", self.model)
        except Exception as e:
            logger.error("Failed to initialize DSPy: %s", e)
            raise RuntimeError(f"Failed to initialize DSPy: {e}") from e

    def configure(self, model: str | None = None, **kwargs: Any) -> None:
        """Configure the agent with runtime parameters.

        This method allows dynamic reconfiguration of the agent without
        recreating the instance, following the Open/Closed principle.

        Args:
            model: Optional new model identifier
            **kwargs: Configuration parameters (temperature, max_tokens, etc.)

        Raises:
            ValueError: If configuration parameters are invalid
        """
        # Validate temperature
        if "temperature" in kwargs:
            temp = kwargs["temperature"]
            if not isinstance(temp, (int, float)) or not 0.0 <= temp <= 2.0:
                raise ValueError(f"temperature must be a number between 0.0 and 2.0, got: {temp}")

        # Validate max_tokens
        if "max_tokens" in kwargs:
            tokens = kwargs["max_tokens"]
            if not isinstance(tokens, int) or tokens <= 0:
                raise ValueError(f"max_tokens must be a positive integer, got: {tokens}")

        # Update configuration
        if model is not None:
            self.model = model
        if "temperature" in kwargs:
            self.temperature = kwargs["temperature"]
        if "max_tokens" in kwargs:
            self.max_tokens = kwargs["max_tokens"]

        # Store any extra config
        self._extra_config.update(
            {k: v for k, v in kwargs.items() if k not in ("temperature", "max_tokens")}
        )

        # Reinitialize DSPy with new configuration
        self._initialize_dspy()

        logger.info("ConversationAgent reconfigured with model=%s, kwargs=%s", model, kwargs)

    def generate_response(self, context: ConversationContext) -> AgentResponse:
        """Generate a response based on conversation context.

        This method implements the core conversation logic, using DSPy's
        ChainOfThought to generate contextual responses with reasoning.

        Args:
            context: The conversation context containing current message and history

        Returns:
            AgentResponse containing the generated response and reasoning

        Raises:
            ValueError: If the context is invalid
            RuntimeError: If response generation fails
        """
        # Validate input
        if context is None:
            raise ValueError("Context cannot be None")

        if not isinstance(context, ConversationContext):
            raise ValueError(f"Context must be ConversationContext, got: {type(context).__name__}")

        try:
            # Format conversation history
            formatted_history = self._format_conversation_history(context.history)

            logger.debug(
                "Generating response for message: %s (history entries: %d)",
                context.current_message[:50],
                len(context.history) if context.history else 0,
            )

            # Extract session_id and user_id from metadata for Langfuse tracking
            session_id = context.metadata.get("session_id") if context.metadata else None
            user_id = context.metadata.get("user_id") if context.metadata else None

            # Update Langfuse trace with session_id and user_id
            if session_id or user_id:
                try:
                    trace_update = {}
                    if session_id:
                        trace_update["session_id"] = session_id
                    if user_id:
                        trace_update["user_id"] = user_id
                    langfuse_client.update_current_trace(**trace_update)
                    logger.debug("Updated Langfuse trace with session_id=%s, user_id=%s", session_id, user_id)
                except Exception as e:
                    logger.warning("Failed to update Langfuse trace: %s", e)

            # Generate response using DSPy
            # Get user preference from metadata if available
            user_pref = ""
            if context.metadata and "user_preference" in context.metadata:
                user_pref = context.metadata["user_preference"] or ""

            # Get playbook from metadata if available
            playbook = ""
            if context.metadata and "playbook" in context.metadata:
                playbook = context.metadata["playbook"] or ""

            with dspy.context(lm=self.lm):
                prediction = self._generator(
                    current_message=context.current_message,
                    conversation_history=formatted_history,
                    user_preference=user_pref,
                    playbook=playbook,
                )

            # Extract response and reasoning
            response_content = prediction.response
            reasoning = prediction.reasoning if hasattr(prediction, "reasoning") else None

            # Create metadata
            metadata = {
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "history_length": len(context.history) if context.history else 0,
            }

            # Add context metadata if available
            if context.metadata:
                metadata["context_metadata"] = context.metadata

            logger.info("Response generated successfully (length: %d chars)", len(response_content))

            print("response_content", response_content)
            return AgentResponse(
                content=response_content,
                reasoning=reasoning,
                metadata=metadata,
            )

        except Exception as e:
            logger.error("Failed to generate response: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to generate response: {e}") from e

    def _format_conversation_history(self, history: tuple[Message, ...]) -> str:
        """Format conversation history for the LLM.

        This method converts the structured Message history into a formatted
        string that the LLM can understand.

        Args:
            history: Tuple of Message objects representing conversation history

        Returns:
            Formatted conversation history string
        """
        if not history:
            return "No previous conversation."

        formatted_parts: list[str] = []

        for message in history:
            # Map role to display name
            role_display = {
                "user": "User",
                "assistant": "Assistant",
                "system": "System",
            }.get(message.role, message.role.capitalize())

            formatted_parts.append(f"{role_display}: {message.content}")

        return "\n".join(formatted_parts)

    @observe(name="Conversation ReAct")
    def forward(
        self,
        current_message: str,
        conversation_history: str = "No previous conversation.",
        user_preference: str = "",
        playbook: str = "",
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> dspy.Prediction:
        """DSPy Module forward method for direct module usage.

        This method allows the ConversationAgent to be used as a standalone
        DSPy module in optimization pipelines.

        Args:
            current_message: The current user message
            conversation_history: Formatted conversation history
            user_preference: Optional user preferences
            playbook: Optional playbook information for answering questions and executing tasks
            session_id: Optional session ID for Langfuse tracking
            user_id: Optional user ID for Langfuse tracking

        Returns:
            DSPy Prediction containing response and reasoning
        """
        # Update Langfuse trace with session_id and user_id if provided
        if session_id or user_id:
            try:
                trace_update = {}
                if session_id:
                    trace_update["session_id"] = session_id
                if user_id:
                    trace_update["user_id"] = user_id
                langfuse.update_current_trace(**trace_update)
                logger.debug("Updated Langfuse trace with session_id=%s, user_id=%s", session_id, user_id)
            except Exception as e:
                logger.warning("Failed to update Langfuse trace: %s", e)

        return self._generator(
            current_message=current_message,
            conversation_history=conversation_history,
            user_preference=user_preference,
            playbook=playbook,
        )

    @observe(name="Conversation ReAct")
    async def aforward(
        self,
        current_message: str,
        conversation_history: str = "No previous conversation.",
        user_preference: str = "",
        playbook: str = "",
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> dspy.Prediction:
        """Async DSPy Module forward method for async operations.

        This method provides async support for the ConversationAgent following
        DSPy's async pattern. Use this when working with async tools or when
        you need non-blocking operations.

        Args:
            current_message: The current user message
            conversation_history: Formatted conversation history
            user_preference: Optional user preferences
            playbook: Optional playbook information for answering questions and executing tasks
            session_id: Optional session ID for Langfuse tracking
            user_id: Optional user ID for Langfuse tracking

        Returns:
            DSPy Prediction containing response and reasoning
        """
        # Update Langfuse trace with session_id and user_id if provided
        if session_id or user_id:
            try:
                trace_update = {}
                if session_id:
                    trace_update["session_id"] = session_id
                if user_id:
                    trace_update["user_id"] = user_id
                langfuse.update_current_trace(**trace_update)
                logger.debug("Updated Langfuse trace with session_id=%s, user_id=%s", session_id, user_id)
            except Exception as e:
                logger.warning("Failed to update Langfuse trace: %s", e)

        return await self._generator.acall(
            current_message=current_message,
            conversation_history=conversation_history,
            user_preference=user_preference,
            playbook=playbook,
        )

    async def agenerate_response(self, context: ConversationContext) -> AgentResponse:
        """Async version of generate_response for high-throughput scenarios.

        This method provides async support for response generation, useful for:
        - High-throughput production services
        - Concurrent request handling
        - Working with async-only tools
        - Building scalable systems

        Args:
            context: The conversation context containing current message and history

        Returns:
            AgentResponse containing the generated response and reasoning

        Raises:
            ValueError: If the context is invalid
            RuntimeError: If response generation fails
        """
        # Validate input
        if context is None:
            raise ValueError("Context cannot be None")

        if not isinstance(context, ConversationContext):
            raise ValueError(f"Context must be ConversationContext, got: {type(context).__name__}")

        try:
            # Format conversation history
            formatted_history = self._format_conversation_history(context.history)

            logger.debug(
                "Async generating response for message: %s (history entries: %d)",
                context.current_message[:50],
                len(context.history) if context.history else 0,
            )

            # Extract session_id and user_id from metadata for Langfuse tracking
            session_id = context.metadata.get("session_id") if context.metadata else None
            user_id = context.metadata.get("user_id") if context.metadata else None

            # Update Langfuse trace with session_id and user_id
            if session_id or user_id:
                try:
                    trace_update = {}
                    if session_id:
                        trace_update["session_id"] = session_id
                    if user_id:
                        trace_update["user_id"] = user_id
                    langfuse_client.update_current_trace(**trace_update)
                    logger.debug("Updated Langfuse trace with session_id=%s, user_id=%s", session_id, user_id)
                except Exception as e:
                    logger.warning("Failed to update Langfuse trace: %s", e)

            # Generate response using DSPy async
            # Get user preference from metadata if available
            user_pref = ""
            if context.metadata and "user_preference" in context.metadata:
                user_pref = context.metadata["user_preference"] or ""

            # Get playbook from metadata if available
            playbook = ""
            if context.metadata and "playbook" in context.metadata:
                playbook = context.metadata["playbook"] or ""

            with dspy.context(lm=self.lm):
                prediction = await self._generator.acall(
                    current_message=context.current_message,
                    conversation_history=formatted_history,
                    user_preference=user_pref,
                    playbook=playbook,
                )

            # Extract response and reasoning
            response_content = prediction.response
            reasoning = prediction.reasoning if hasattr(prediction, "reasoning") else None

            # Create metadata
            metadata = {
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "history_length": len(context.history) if context.history else 0,
                "async": True,
            }

            # Add context metadata if available
            if context.metadata:
                metadata["context_metadata"] = context.metadata

            logger.info("Async response generated successfully (length: %d chars)", len(response_content))

            print("response_content", response_content)
            return AgentResponse(
                content=response_content,
                reasoning=reasoning,
                metadata=metadata,
            )

        except Exception as e:
            logger.error("Failed to generate async response: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to generate async response: {e}") from e
