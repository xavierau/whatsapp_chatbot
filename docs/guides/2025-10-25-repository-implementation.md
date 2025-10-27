# Repository Implementation Guide

**Date:** 2025-10-25
**Version:** 1.0
**Status:** Complete ✅

---

## Overview

This guide documents the PostgreSQL repository implementations for User, Session, and Message entities. All repositories follow Clean Architecture principles, implement their respective protocols, and provide comprehensive error handling.

---

## Repository Architecture

### Design Principles

**Clean Architecture:**
- ✅ Implements domain repository protocols (IUserRepository, ISessionRepository, IMessageRepository)
- ✅ Uses dependency injection (AsyncSession passed to constructor)
- ✅ No business logic in repositories (pure data access)
- ✅ Entity ↔ Model mapping isolated

**Error Handling:**
- ✅ Comprehensive try-except blocks
- ✅ Specific error types (ValueError for validation, RuntimeError for DB errors)
- ✅ Detailed logging at all levels
- ✅ Proper error propagation

**Async/Await:**
- ✅ All methods are async
- ✅ Uses SQLAlchemy AsyncSession
- ✅ Proper session management (flush, no commit in repository)

---

## UserRepository

**File:** `src/infrastructure/database/repositories/user_repository.py`

### Features

✅ **CRUD Operations:**
- `create(user)` - Create new user with duplicate phone check
- `get_by_id(user_id)` - Retrieve by UUID
- `get_by_phone_number(phone)` - Retrieve by phone (unique)
- `update(user)` - Update existing user
- `delete(user_id)` - Soft delete

✅ **Additional Operations:**
- `update_last_active(user_id)` - Update activity timestamp
- `exists(phone_number)` - Check existence by phone

✅ **Soft Delete Support:**
- All queries filter `deleted_at IS NULL`
- Delete sets `deleted_at` timestamp
- Maintains audit trail

### Usage Example

```python
from src.infrastructure.database.session import get_db_session
from src.infrastructure.database.repositories import UserRepository
from src.domain.entities.user import User

async def example():
    async with get_db_session() as session:
        repo = UserRepository(session)

        # Create user
        user = User.create(
            phone_number="+1234567890",
            display_name="John Doe",
            preferences={"language": "en"}
        )
        created = await repo.create(user)

        # Get user by phone
        found = await repo.get_by_phone_number("+1234567890")

        # Update user
        updated = found.update(display_name="Jane Doe")
        saved = await repo.update(updated)

        # Soft delete
        deleted = await repo.delete(created.id)
```

### Error Handling

```python
try:
    user = await repo.create(duplicate_user)
except ValueError as e:
    # Handle duplicate phone number
    print(f"Validation error: {e}")
except RuntimeError as e:
    # Handle database error
    print(f"Database error: {e}")
```

---

## SessionRepository

**File:** `src/infrastructure/database/repositories/session_repository.py`

### Features

✅ **Session Lifecycle:**
- `create(session)` - Create new session
- `get_by_id(session_id)` - Retrieve by UUID
- `get_active_session_for_user(user_id)` - Get user's active session
- `update(session)` - Update session
- `close_session(session_id)` - Close session with timestamp
- `delete(session_id)` - Soft delete

✅ **Session Management:**
- `get_user_sessions(user_id, limit, include_expired)` - User's session history
- `expire_inactive_sessions(timeout_minutes)` - Bulk expiry (background task)
- `update_activity(session_id)` - Update activity timestamp

✅ **Query Features:**
- Status filtering (active/expired/closed)
- Ordering by most recent first
- Pagination support
- Soft delete filtering

### Usage Example

```python
from src.infrastructure.database.repositories import SessionRepository
from src.domain.entities.session import Session

async def example():
    async with get_db_session() as session:
        repo = SessionRepository(session)

        # Create session
        new_session = Session.create(user_id="user-123")
        created = await repo.create(new_session)

        # Get active session for user
        active = await repo.get_active_session_for_user("user-123")

        # Update activity
        await repo.update_activity(created.id)

        # Close session
        closed = await repo.close_session(created.id)

        # Expire inactive sessions (background task)
        expired_count = await repo.expire_inactive_sessions(timeout_minutes=30)
        print(f"Expired {expired_count} sessions")
```

### Background Task: Session Expiry

```python
import asyncio
from src.infrastructure.database.session import get_db_session
from src.infrastructure.database.repositories import SessionRepository

async def expire_sessions_task():
    """Background task to expire inactive sessions."""
    while True:
        try:
            async with get_db_session() as session:
                repo = SessionRepository(session)
                count = await repo.expire_inactive_sessions(timeout_minutes=30)
                if count > 0:
                    print(f"Expired {count} inactive sessions")
        except Exception as e:
            print(f"Error expiring sessions: {e}")

        # Run every 5 minutes
        await asyncio.sleep(300)

# Start background task
asyncio.create_task(expire_sessions_task())
```

---

## MessageRepository

**File:** `src/infrastructure/database/repositories/message_repository.py`

### Features

✅ **Message Operations:**
- `create(message)` - Store new message
- `get_by_id(message_id)` - Retrieve by UUID
- `get_session_messages(session_id, limit, offset)` - Paginated messages
- `delete(message_id)` - Soft delete

✅ **Conversation Features:**
- `get_conversation_history(session_id, max_messages)` - LLM context (excludes system messages)
- `get_messages_with_tool_results(session_id, limit)` - Analytics/debugging
- `get_latest_message(session_id)` - Most recent message
- `count_session_messages(session_id)` - Message count

✅ **Query Optimizations:**
- Chronological ordering (oldest to newest for LLM)
- Tool result filtering
- Role filtering (exclude system messages from history)
- Pagination support

### Usage Example

```python
from src.infrastructure.database.repositories import MessageRepository
from src.domain.entities.message import Message, MessageRole

async def example():
    async with get_db_session() as session:
        repo = MessageRepository(session)

        # Store user message
        user_msg = Message.create(
            session_id="session-123",
            role=MessageRole.USER,
            content="Hello, how are you?",
            whatsapp_message_id="wamid.abc123"
        )
        await repo.create(user_msg)

        # Store assistant message with tool result
        assistant_msg = Message.create(
            session_id="session-123",
            role=MessageRole.ASSISTANT,
            content="I'm doing well!",
            tool_result={"tool": "greeting", "response": "positive"},
            response_time_ms=1500
        )
        await repo.create(assistant_msg)

        # Get conversation history for LLM (last 10 messages)
        history = await repo.get_conversation_history("session-123", max_messages=10)

        # Format for LLM context
        context = "\n".join([msg.format_for_llm() for msg in history])

        # Get messages with tool results (for analytics)
        tool_messages = await repo.get_messages_with_tool_results("session-123")
```

### LLM Integration

```python
from src.infrastructure.llm.conversation_agent import ConversationAgent
from src.application.interfaces.conversation_agent import ConversationContext, Message

async def generate_response(session_id: str, user_message: str):
    """Generate LLM response with conversation history."""
    async with get_db_session() as db_session:
        msg_repo = MessageRepository(db_session)

        # Get conversation history
        history_entities = await msg_repo.get_conversation_history(
            session_id,
            max_messages=10
        )

        # Convert to application layer Messages
        history = tuple([
            Message(role=msg.role.value, content=msg.content)
            for msg in history_entities
        ])

        # Create context
        context = ConversationContext(
            current_message=user_message,
            history=history
        )

        # Generate response
        agent = ConversationAgent()
        response = agent.generate_response(context)

        return response.content
```

---

## Common Patterns

### Entity ↔ Model Mapping

All repositories implement bidirectional mapping:

```python
def _to_entity(self, model: UserModel) -> User:
    """Convert SQLAlchemy model to domain entity."""
    return User(
        id=model.id,
        phone_number=model.phone_number,
        # ... all fields
    )

def _to_model(self, entity: User) -> UserModel:
    """Convert domain entity to SQLAlchemy model."""
    return UserModel(
        id=entity.id,
        phone_number=entity.phone_number,
        # ... all fields
    )
```

### Session Management

Repositories don't commit transactions - that's the use case's responsibility:

```python
# ❌ DON'T DO THIS IN REPOSITORY
async def create(self, user: User) -> User:
    model = self._to_model(user)
    self.session.add(model)
    await self.session.commit()  # ❌ Don't commit in repository!
    return self._to_entity(model)

# ✅ DO THIS INSTEAD
async def create(self, user: User) -> User:
    model = self._to_model(user)
    self.session.add(model)
    await self.session.flush()  # ✅ Flush to get DB values, no commit
    return self._to_entity(model)
```

Transaction management happens at use case level:

```python
async def create_user_use_case(phone: str, name: str):
    async with get_db_session() as session:  # Auto-commits on success
        repo = UserRepository(session)
        user = User.create(phone_number=phone, display_name=name)
        created = await repo.create(user)
        # Session commits here automatically
    return created
```

### Error Handling Pattern

```python
async def some_operation(self, id: str) -> Result:
    try:
        # Check existence
        existing = await self.get_by_id(id)
        if existing is None:
            raise ValueError(f"Entity with ID {id} not found")

        # Perform operation
        stmt = update(Model).where(Model.id == id).values(...)
        await self.session.execute(stmt)
        await self.session.flush()

        return result

    except ValueError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error("Operation failed: %s", e, exc_info=True)
        raise RuntimeError(f"Operation failed: {e}") from e
```

---

## Testing Repositories

### Integration Test Example

```python
import pytest
from src.infrastructure.database.session import get_db_session
from src.infrastructure.database.repositories import UserRepository
from src.domain.entities.user import User

@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_repository_create_and_get():
    """Test user repository CRUD operations."""
    async with get_db_session() as session:
        repo = UserRepository(session)

        # Create user
        user = User.create(phone_number="+1234567890", display_name="Test User")
        created = await repo.create(user)

        assert created.id is not None
        assert created.phone_number == "+1234567890"

        # Retrieve user
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.phone_number == created.phone_number

        # Cleanup
        await repo.delete(created.id)
```

### Run Integration Tests

```bash
# Setup test database
psql -U postgres -c "CREATE DATABASE whatsapp_chatbot_test;"

# Run migrations
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/whatsapp_chatbot_test \
  uv run alembic upgrade head

# Run integration tests
uv run pytest tests/integration/ -v -m integration
```

---

## Performance Considerations

### Indexes Used

All queries leverage existing indexes:

**UserRepository:**
- `users.phone_number` (unique) - O(1) lookup
- `users.last_active_at` - Activity queries
- `users.deleted_at` (partial) - Soft delete filtering

**SessionRepository:**
- `sessions.user_id` - User's sessions
- `sessions.status` - Status filtering
- `sessions.last_activity_at` - Expiry checks
- Composite: `(user_id, status)` for active session lookup

**MessageRepository:**
- `messages.session_id` - Session messages
- `messages.created_at` - Chronological ordering
- `messages.whatsapp_message_id` - WhatsApp tracking

### Query Optimization

```python
# ✅ GOOD: Single query with filter
stmt = select(SessionModel).where(
    SessionModel.user_id == user_id,
    SessionModel.status == SessionStatus.ACTIVE
).limit(1)

# ❌ BAD: Multiple queries
all_sessions = await get_all_sessions(user_id)
active = [s for s in all_sessions if s.status == 'active'][0]
```

### Connection Pooling

Database session factory uses connection pooling:
- Pool size: 10 connections
- Max overflow: 20 connections
- Pre-ping: Verify connection before use
- Pool recycle: 1 hour

---

## Next Steps

1. ✅ Repositories implemented
2. ⏭️ Create integration tests for repositories
3. ⏭️ Implement use cases (business logic layer)
4. ⏭️ Create FastAPI endpoints
5. ⏭️ Add background task for session expiry
6. ⏭️ Performance testing and optimization

---

## References

- [UserRepository Implementation](../../src/infrastructure/database/repositories/user_repository.py)
- [SessionRepository Implementation](../../src/infrastructure/database/repositories/session_repository.py)
- [MessageRepository Implementation](../../src/infrastructure/database/repositories/message_repository.py)
- [SQLAlchemy AsyncIO](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-25 | Claude | Initial repository implementation guide |
