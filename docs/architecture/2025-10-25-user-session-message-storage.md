# User, Session & Message Storage Architecture

**Date:** 2025-10-25
**Version:** 1.0
**Status:** Implementation

---

## Overview

This document describes the architecture for storing users, conversation sessions, and messages in PostgreSQL for the WhatsApp chatbot. The design follows Clean Architecture principles and supports:

- User management with WhatsApp phone numbers as identifiers
- Session lifecycle with hybrid management (auto-expire + manual control)
- Message storage with tool result tracking
- Soft deletes for audit compliance
- LLM performance metrics (response time tracking)

---

## Domain Model

### Entity Relationships

```
User (1) ──< (N) Session (1) ──< (N) Message
```

### User Entity

**Purpose:** Represents a WhatsApp user interacting with the chatbot.

**Attributes:**
- `id: str` - Unique identifier (UUID)
- `phone_number: str` - WhatsApp phone number (unique identifier)
- `display_name: str | None` - Optional display name
- `preferences: dict[str, Any] | None` - User preferences for conversation agent
- `created_at: datetime` - Account creation timestamp
- `updated_at: datetime` - Last update timestamp
- `last_active_at: datetime` - Last activity timestamp
- `deleted_at: datetime | None` - Soft delete timestamp

**Business Rules:**
- Phone number must be unique and non-empty
- Phone number format: E.164 standard (e.g., +1234567890)
- Preferences stored as JSONB for flexibility
- Immutable entity (frozen dataclass)

### Session Entity

**Purpose:** Represents a conversation session between user and chatbot.

**Attributes:**
- `id: str` - Unique identifier (UUID)
- `user_id: str` - Foreign key to User
- `status: Literal['active', 'expired', 'closed']` - Session status
- `created_at: datetime` - Session start timestamp
- `last_activity_at: datetime` - Last message timestamp
- `closed_at: datetime | None` - Session close timestamp
- `metadata: dict[str, Any] | None` - Extensible metadata
- `deleted_at: datetime | None` - Soft delete timestamp

**Business Rules:**
- Sessions auto-expire after 30 minutes of inactivity (configurable)
- Users can have multiple sessions (sequential conversations)
- Only one active session per user at a time
- Sessions can be manually closed
- Expired sessions can be reactivated if within grace period

**Lifecycle States:**
```
active -> expired (30min inactivity)
active -> closed (manual close)
expired -> closed (cleanup)
```

### Message Entity

**Purpose:** Represents a single message in a conversation session.

**Attributes:**
- `id: str` - Unique identifier (UUID)
- `session_id: str` - Foreign key to Session
- `role: Literal['user', 'assistant', 'system']` - Message sender role
- `content: str` - Message text content
- `tool_result: dict[str, Any] | None` - DSPy tool execution results (JSONB)
- `whatsapp_message_id: str | None` - WhatsApp API message ID
- `response_time_ms: int | None` - LLM generation time in milliseconds
- `created_at: datetime` - Message timestamp
- `metadata: dict[str, Any] | None` - Extensible metadata
- `deleted_at: datetime | None` - Soft delete timestamp

**Business Rules:**
- Messages must belong to a session
- Content cannot be empty for user/assistant messages
- Tool results stored as structured JSON for analysis
- Messages ordered by created_at for conversation history
- System messages used for context injection

---

## Database Schema

### users table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    preferences JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_users_phone_number ON users(phone_number);
CREATE INDEX idx_users_last_active ON users(last_active_at);
CREATE INDEX idx_users_deleted ON users(deleted_at) WHERE deleted_at IS NULL;
```

### sessions table

```sql
CREATE TYPE session_status AS ENUM ('active', 'expired', 'closed');

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status session_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP,
    metadata JSONB,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_last_activity ON sessions(last_activity_at);
CREATE INDEX idx_sessions_deleted ON sessions(deleted_at) WHERE deleted_at IS NULL;
```

### messages table

```sql
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role message_role NOT NULL,
    content TEXT NOT NULL,
    tool_result JSONB,
    whatsapp_message_id VARCHAR(255),
    response_time_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_whatsapp_id ON messages(whatsapp_message_id);
CREATE INDEX idx_messages_deleted ON messages(deleted_at) WHERE deleted_at IS NULL;
```

---

## Repository Interfaces (Protocols)

### IUserRepository

```python
class IUserRepository(Protocol):
    async def create(self, user: User) -> User
    async def get_by_id(self, user_id: str) -> User | None
    async def get_by_phone_number(self, phone_number: str) -> User | None
    async def update(self, user: User) -> User
    async def delete(self, user_id: str) -> bool  # soft delete
    async def update_last_active(self, user_id: str) -> None
```

### ISessionRepository

```python
class ISessionRepository(Protocol):
    async def create(self, session: Session) -> Session
    async def get_by_id(self, session_id: str) -> Session | None
    async def get_active_session_for_user(self, user_id: str) -> Session | None
    async def get_user_sessions(self, user_id: str, limit: int) -> list[Session]
    async def update(self, session: Session) -> Session
    async def close_session(self, session_id: str) -> bool
    async def expire_inactive_sessions(self, timeout_minutes: int) -> int
    async def delete(self, session_id: str) -> bool  # soft delete
```

### IMessageRepository

```python
class IMessageRepository(Protocol):
    async def create(self, message: Message) -> Message
    async def get_by_id(self, message_id: str) -> Message | None
    async def get_session_messages(
        self, session_id: str, limit: int | None
    ) -> list[Message]
    async def get_conversation_history(
        self, session_id: str, max_messages: int
    ) -> list[Message]
    async def delete(self, message_id: str) -> bool  # soft delete
```

---

## Use Cases

### User Management

1. **CreateUser** - Register new WhatsApp user
2. **GetUser** - Retrieve user by ID or phone number
3. **UpdateUser** - Update user preferences/display name
4. **DeleteUser** - Soft delete user account

### Session Management

1. **CreateSession** - Start new conversation session
2. **GetSession** - Retrieve session by ID
3. **GetActiveSession** - Get user's active session
4. **CloseSession** - Manually close session
5. **CheckSessionExpiry** - Background task to expire inactive sessions
6. **GetUserSessions** - List user's session history

### Message Management

1. **StoreMessage** - Save user/assistant/system message
2. **GetSessionMessages** - Retrieve all messages in session
3. **GetConversationHistory** - Get recent N messages for LLM context
4. **DeleteMessage** - Soft delete message (admin/compliance)

---

## Integration with ConversationAgent

### Message Flow

```
1. User sends WhatsApp message
2. API receives webhook
3. GetOrCreateUser(phone_number)
4. GetOrCreateActiveSession(user_id)
5. StoreMessage(role='user', content=message)
6. GetConversationHistory(session_id, max=10)
7. ConversationAgent.generate_response(context)
8. StoreMessage(role='assistant', content=response, tool_result, response_time)
9. Send response to WhatsApp
10. Update session.last_activity_at
```

### Tool Result Storage

When DSPy tools are executed (compute, jot, note_tools), the results are stored in `tool_result` JSONB field:

```json
{
  "tool_calls": [
    {
      "tool": "compute",
      "input": "calculate 2+2",
      "output": "4",
      "execution_time_ms": 120
    },
    {
      "tool": "note_tools",
      "action": "search_notes",
      "query": "meeting notes",
      "results_count": 3
    }
  ]
}
```

---

## Session Expiry Strategy

### Hybrid Approach

**Auto-Expiry:**
- Background task runs every 5 minutes
- Marks sessions as 'expired' if `last_activity_at` > 30 minutes ago
- Keeps expired sessions for 24 hours before archival

**Manual Control:**
- Users can explicitly close sessions (e.g., "end conversation")
- Closed sessions cannot be reactivated
- API endpoint: `POST /sessions/{session_id}/close`

**Grace Period:**
- Expired sessions can receive new messages (auto-reactivate)
- Closed sessions require new session creation

---

## Soft Delete Strategy

All entities support soft deletion for audit compliance:

- `deleted_at` timestamp marks deletion
- Queries filter `WHERE deleted_at IS NULL` by default
- Admin queries can include deleted records
- Permanent deletion via scheduled cleanup jobs
- GDPR compliance: hard delete on explicit user request

---

## Performance Considerations

### Indexing Strategy

- Primary keys: UUID with indexed lookups
- Foreign keys: All indexed for join performance
- Composite index: `(user_id, status)` for active session lookup
- Partial index: `WHERE deleted_at IS NULL` for soft deletes
- Timestamp indexes: For expiry checks and message ordering

### Query Optimization

- Connection pooling with asyncpg
- Prepared statements for repeated queries
- Limit conversation history to last N messages (default: 10)
- Pagination for session/message listing
- Background tasks for cleanup (non-blocking)

---

## Security & Privacy

### Data Protection

- Phone numbers hashed before storage (consider for production)
- No sensitive data in metadata fields
- Tool results sanitized (no API keys/secrets)
- Soft deletes for audit trails

### Compliance

- GDPR Right to Erasure: Hard delete on request
- Data retention: 90 days for inactive users
- Audit logs: Track all user/session/message operations
- WhatsApp compliance: 24-hour message window enforced

---

## Migration Strategy

### Initial Migration

```
Version: 001_create_users_sessions_messages_tables
- Create users table with indexes
- Create sessions table with foreign keys
- Create messages table with foreign keys
- Create ENUM types (session_status, message_role)
- Add constraints and indexes
```

### Future Migrations

- Add embedding support for semantic search (Phase 2)
- Add analytics tables for metrics (Phase 3)
- Add archival tables for old sessions (Phase 4)

---

## Testing Strategy

### Unit Tests

- Entity validation (frozen dataclasses)
- Factory methods (User.create, Session.create, Message.create)
- Business rule enforcement

### Integration Tests

- Repository CRUD operations
- Foreign key constraints
- Soft delete behavior
- Session expiry logic
- Transaction rollback scenarios

### End-to-End Tests

- Complete message flow (user -> agent -> storage)
- Session lifecycle (create -> active -> expired -> closed)
- Tool result persistence
- Conversation history retrieval

---

## Monitoring & Observability

### Metrics to Track

- Active users count
- Active sessions count
- Messages per session (avg/p95)
- Session duration (avg/p95)
- Database query latency (p50/p95/p99)
- Tool usage frequency
- Response time distribution

### Alerts

- Session expiry job failures
- Database connection pool exhaustion
- Slow queries (>500ms)
- Failed message storage

---

## Future Enhancements

### Phase 2: Semantic Search
- Add embedding field to messages table
- Vector similarity search for context retrieval
- RAG pattern implementation

### Phase 3: Analytics
- Conversation analytics dashboard
- User engagement metrics
- Tool usage patterns
- LLM performance analysis

### Phase 4: Multi-tenancy
- Support multiple bot instances
- Tenant isolation
- Shared vs dedicated databases

---

## References

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [SQLAlchemy AsyncIO](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Migrations](https://alembic.sqlalchemy.org/en/latest/)
- [GDPR Compliance](https://gdpr.eu/right-to-be-forgotten/)

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-25 | Claude | Initial architecture design |
