# LLM Infrastructure

This directory contains the LLM (Large Language Model) infrastructure implementations for the WhatsApp chatbot.

## Modules

### ConversationAgent

DSPy-based conversation agent for handling contextual WhatsApp conversations.

**Files:**
- `/Users/xavierau/Code/python/whatsapp_chatbot/src/infrastructure/llm/conversation_agent.py` - Implementation
- `/Users/xavierau/Code/python/whatsapp_chatbot/src/application/interfaces/conversation_agent.py` - Interface
- `/Users/xavierau/Code/python/whatsapp_chatbot/tests/unit/infrastructure/test_conversation_agent.py` - Tests

**Documentation:**
- [Usage Guide](/Users/xavierau/Code/python/whatsapp_chatbot/docs/guides/2025-10-25-conversation-agent-usage.md)
- [Architecture Design](/Users/xavierau/Code/python/whatsapp_chatbot/docs/architecture/2025-10-25-conversation-agent-design.md)

**Key Features:**
- Type-safe Pydantic-based DSPy signatures
- SOLID principles compliance
- Immutable data structures (frozen dataclasses)
- Comprehensive error handling
- 93% test coverage
- Protocol-based interface (no metaclass conflicts)
- ChainOfThought reasoning
- Runtime configuration

**Quick Start:**

```python
from src.infrastructure.llm.conversation_agent import ConversationAgent
from src.application.interfaces.conversation_agent import ConversationContext

# Initialize agent
agent = ConversationAgent()

# Create context
context = ConversationContext(
    current_message="Hello, how are you?",
    metadata={"user_id": "user123"}
)

# Generate response
response = agent.generate_response(context)
print(response.content)
print(response.reasoning)
```

**Testing:**

```bash
# Run all tests
pytest tests/unit/infrastructure/test_conversation_agent.py -v

# Run with coverage
pytest tests/unit/infrastructure/test_conversation_agent.py --cov=src/infrastructure/llm/conversation_agent

# Skip integration tests
pytest tests/unit/infrastructure/test_conversation_agent.py -m "not integration"
```

**Test Results:**
- Total Tests: 30 (all passing)
- Coverage: 93%
- Integration Tests: 1 (marked skip by default)

## Configuration

Set the following environment variables in `.env`:

```bash
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key

# LLM Configuration
DEFAULT_LLM_MODEL=gemini/gemini-2.5-flash
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1024
```

## Architecture

The LLM infrastructure follows Clean Architecture principles:

1. **Application Layer**: Interfaces and protocols
2. **Infrastructure Layer**: Concrete implementations
3. **Domain Layer**: Business logic (separate)

### Dependency Flow

```
Interface Layer (Protocol)
        ▲
        │ implements
        │
Infrastructure Layer (DSPy Module)
        ▲
        │ uses
        │
DSPy Framework & LLM
```

## SOLID Principles

- **Single Responsibility**: Each module handles one aspect of LLM interaction
- **Open/Closed**: Extensible via configuration and subclassing
- **Liskov Substitution**: All implementations are interchangeable
- **Interface Segregation**: Minimal, focused interfaces
- **Dependency Inversion**: Depends on abstractions (Protocols)

## Future Modules

Planned additions to this directory:

- `embedding_generator.py` - Generate embeddings for semantic search
- `text_classifier.py` - Classify message intent
- `summarizer.py` - Summarize long conversations
- `prompt_manager.py` - Manage and optimize prompts

## Contributing

When adding new LLM modules:

1. Define interface in `/Users/xavierau/Code/python/whatsapp_chatbot/src/application/interfaces/`
2. Implement in this directory
3. Write tests in `/Users/xavierau/Code/python/whatsapp_chatbot/tests/unit/infrastructure/`
4. Follow TDD approach
5. Ensure SOLID compliance
6. Document architecture decisions
7. Achieve >90% test coverage

## Resources

- [DSPy Documentation](https://github.com/stanfordnlp/dspy)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Clean Architecture Guide](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
