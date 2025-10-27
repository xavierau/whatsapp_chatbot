# ConversationAgent Usage Guide

**Date:** 2025-10-25
**Component:** ConversationAgent DSPy Module
**Location:** `src/infrastructure/llm/conversation_agent.py`

## Overview

The ConversationAgent is a DSPy-based module that handles contextual conversations for the WhatsApp chatbot. It implements clean architecture principles and provides robust conversation handling with history awareness.

## Architecture

The module follows clean architecture with three layers:

1. **Interface Layer** (`src/application/interfaces/conversation_agent.py`)
   - Defines the `IConversationAgent` Protocol
   - Immutable data structures: `Message`, `ConversationContext`, `AgentResponse`

2. **Implementation Layer** (`src/infrastructure/llm/conversation_agent.py`)
   - `ConversationSignature`: Pydantic-based DSPy signature
   - `ConversationAgent`: DSPy Module implementation

3. **Test Layer** (`tests/unit/infrastructure/test_conversation_agent.py`)
   - Comprehensive unit tests with 93% coverage
   - Mock-based testing for LLM interactions

## Key Features

- **Type Safety**: Full type annotations and Pydantic validation
- **Immutability**: All data structures are immutable (frozen dataclasses)
- **Clean Architecture**: Separation of concerns with Protocol-based interfaces
- **Error Handling**: Comprehensive validation and error messages
- **DSPy Integration**: Uses ChainOfThought for reasoning-enhanced responses
- **Configuration**: Runtime configuration without instance recreation

## Basic Usage

### Simple Conversation (No History)

```python
from src.infrastructure.llm.conversation_agent import ConversationAgent
from src.application.interfaces.conversation_agent import ConversationContext

# Initialize the agent
agent = ConversationAgent()

# Create a conversation context
context = ConversationContext(
    current_message="What is the capital of France?",
    metadata={"user_id": "user123"}
)

# Generate response
response = agent.generate_response(context)

print(f"Response: {response.content}")
print(f"Reasoning: {response.reasoning}")
```

### Conversation with History

```python
from src.infrastructure.llm.conversation_agent import ConversationAgent
from src.application.interfaces.conversation_agent import (
    ConversationContext,
    Message,
)

# Initialize the agent
agent = ConversationAgent()

# Build conversation history
history = (
    Message(role="user", content="Hello!"),
    Message(role="assistant", content="Hi! How can I help you today?"),
    Message(role="user", content="Tell me about Paris"),
    Message(
        role="assistant",
        content="Paris is the capital of France, known for the Eiffel Tower..."
    ),
)

# Create context with history
context = ConversationContext(
    current_message="What is its population?",
    history=history,
    metadata={"user_id": "user123", "session_id": "sess456"}
)

# Generate contextual response
response = agent.generate_response(context)

print(f"Response: {response.content}")
# The agent will understand "its" refers to Paris from the history
```

### Custom Configuration

```python
from src.infrastructure.llm.conversation_agent import ConversationAgent

# Initialize with custom model
agent = ConversationAgent(model="gemini/gemini-2.5-pro")

# Configure runtime parameters
agent.configure(
    temperature=0.3,  # More deterministic
    max_tokens=2048,  # Longer responses
)

# Use configured agent
response = agent.generate_response(context)
```

### Using as DSPy Module in Pipelines

```python
import dspy
from src.infrastructure.llm.conversation_agent import ConversationAgent

# Initialize DSPy
dspy.configure(lm=dspy.LM("gemini/gemini-2.5-flash", api_key="YOUR_KEY"))

# Create agent
agent = ConversationAgent()

# Use directly as DSPy module
prediction = agent.forward(
    current_message="Hello!",
    conversation_history="No previous conversation."
)

print(prediction.response)
print(prediction.reasoning)
```

## Data Structures

### Message

Immutable message in conversation history:

```python
from src.application.interfaces.conversation_agent import Message

message = Message(
    role="user",  # "user", "assistant", or "system"
    content="What's the weather like?",
    metadata={"timestamp": "2025-10-25T10:00:00Z"}
)
```

**Validation Rules:**
- `role` must be one of: "user", "assistant", "system"
- `content` cannot be empty
- `metadata` is optional

### ConversationContext

Immutable context for agent processing:

```python
from src.application.interfaces.conversation_agent import ConversationContext

context = ConversationContext(
    current_message="What is 2+2?",
    history=(
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi!"),
    ),
    metadata={"user_id": "user123"}
)
```

**Validation Rules:**
- `current_message` cannot be empty
- `history` is a tuple (immutable) of Message objects
- `metadata` is optional

### AgentResponse

Immutable response from the agent:

```python
from src.application.interfaces.conversation_agent import AgentResponse

response = AgentResponse(
    content="The answer is 4.",
    reasoning="Simple arithmetic calculation.",
    metadata={"model": "gemini-2.5-flash", "tokens": 150}
)
```

**Validation Rules:**
- `content` cannot be empty
- `reasoning` is optional (provided by ChainOfThought)
- `metadata` is optional (includes model info, token count, etc.)

## Error Handling

The module provides comprehensive error handling:

```python
from src.infrastructure.llm.conversation_agent import ConversationAgent
from src.application.interfaces.conversation_agent import ConversationContext

agent = ConversationAgent()

# Invalid context - raises ValueError
try:
    context = ConversationContext(current_message="")
except ValueError as e:
    print(f"Validation error: {e}")

# Invalid configuration - raises ValueError
try:
    agent.configure(temperature=5.0)  # Out of range
except ValueError as e:
    print(f"Configuration error: {e}")

# LLM failure - raises RuntimeError
try:
    response = agent.generate_response(context)
except RuntimeError as e:
    print(f"Generation error: {e}")
```

## DSPy Signature Structure

The `ConversationSignature` defines the task structure:

```python
class ConversationSignature(dspy.Signature):
    """Signature for contextual conversation generation."""

    current_message: str = dspy.InputField(
        desc="The current user message that needs a response"
    )
    conversation_history: str = dspy.InputField(
        desc="Previous conversation messages formatted as: 'User: <message>\\nAssistant: <response>\\n...'"
    )
    response: str = dspy.OutputField(
        desc="A helpful, contextual response to the user's current message"
    )
    reasoning: str = dspy.OutputField(
        desc="Brief explanation of the reasoning behind this response"
    )
```

## SOLID Principles

The implementation follows SOLID principles:

1. **Single Responsibility**: ConversationAgent only handles conversation generation
2. **Open/Closed**: Extensible via configuration without modifying code
3. **Liskov Substitution**: Fully implements IConversationAgent Protocol
4. **Interface Segregation**: Minimal, focused interface with just 2 methods
5. **Dependency Inversion**: Depends on abstractions (IConversationAgent Protocol)

## Testing

Run the test suite:

```bash
# Run all unit tests
pytest tests/unit/infrastructure/test_conversation_agent.py -v

# Run with coverage
pytest tests/unit/infrastructure/test_conversation_agent.py --cov=src/infrastructure/llm/conversation_agent

# Skip integration tests
pytest tests/unit/infrastructure/test_conversation_agent.py -m "not integration"
```

## Integration with WhatsApp Chatbot

Example integration with WhatsApp message handling:

```python
from src.infrastructure.llm.conversation_agent import ConversationAgent
from src.application.interfaces.conversation_agent import ConversationContext, Message

class WhatsAppMessageHandler:
    def __init__(self):
        self.agent = ConversationAgent()
        self.conversation_store = {}  # In production, use a database

    def handle_message(self, user_id: str, message_text: str) -> str:
        # Retrieve conversation history
        history = self.conversation_store.get(user_id, [])

        # Create context
        context = ConversationContext(
            current_message=message_text,
            history=tuple(history),
            metadata={"user_id": user_id}
        )

        # Generate response
        response = self.agent.generate_response(context)

        # Update history
        history.append(Message(role="user", content=message_text))
        history.append(Message(role="assistant", content=response.content))
        self.conversation_store[user_id] = history

        return response.content
```

## Performance Considerations

- **History Length**: Limit conversation history to avoid token limits
- **Caching**: Consider caching for repeated queries
- **Error Recovery**: Implement retry logic for transient LLM failures
- **Rate Limiting**: Apply rate limits to prevent API quota exhaustion

## Future Enhancements

Potential improvements:

1. **Streaming Support**: Add streaming response generation
2. **Multi-turn Optimization**: Use DSPy optimizers (BootstrapFewShot, MIPROv2)
3. **Memory Management**: Implement intelligent history summarization
4. **Tool Integration**: Add function calling capabilities
5. **Evaluation Metrics**: Create custom metrics for conversation quality

## Related Documentation

- [DSPy Documentation](https://github.com/stanfordnlp/dspy)
- [Clean Architecture Principles](../../README.md)
- [Testing Guidelines](../../README.md#testing)

## Troubleshooting

**Q: Getting "RuntimeError: Failed to initialize DSPy"**
A: Ensure the `GEMINI_API_KEY` environment variable is set correctly in `.env`

**Q: Tests failing with metaclass conflict**
A: This was resolved by using Protocol instead of ABC for the interface

**Q: Response quality is poor**
A: Try adjusting temperature (higher for creativity, lower for determinism) or switching to a more capable model like `gemini-2.5-pro`

**Q: Token limit exceeded**
A: Reduce `max_tokens` configuration or limit conversation history length
