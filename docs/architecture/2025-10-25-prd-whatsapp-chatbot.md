# Product Requirements Document: AI WhatsApp Chatbot

**Date:** 2025-10-25
**Version:** 1.1
**Status:** Development Phase

---

## 1. Executive Summary

An AI-powered WhatsApp chatbot development project using Meta Cloud API, deployed on AWS. The system leverages DSPy framework with Gemini LLM, PostgreSQL with pgvector for contextual memory, and Langfuse for observability.

**Current Phase:** Development/MVP - General-purpose conversational AI without specific domain focus.

### Key Objectives
- Build functional WhatsApp chatbot using Meta Cloud API
- Implement conversation context and memory using vector embeddings
- Enable observability and monitoring of LLM interactions via Langfuse
- Create foundation for future domain-specific applications

---

## 2. Technology Stack

### Core Framework
- **Python**: >= 3.13
- **Web Framework**: FastAPI
- **Package Manager**: uv

### AI/LLM Components
- **LLM Framework**: DSPy
- **Default Model**: gemini/gemini-2.5-flash
- **Observability**: Langfuse

### Data Storage
- **Database**: PostgreSQL
- **Vector Extension**: pgvector

### Infrastructure
- **WhatsApp Provider**: Meta Cloud API
- **Cloud Platform**: AWS
- **Deployment**: Development environment initially
- RESTful API for webhook integration
- Asynchronous request handling
- Vector similarity search for context retrieval

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────┐
│  Meta Cloud API │
│  (WhatsApp)     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   FastAPI       │
│   (AWS)         │
├─────────────────┤
│  - Webhooks     │
│  - Message      │
│    Processing   │
│  - Validation   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   DSPy Layer    │
├─────────────────┤
│  - Prompts      │
│  - Signatures   │
│  - Modules      │
│  - Optimization │
└────────┬────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────┐
│   Gemini LLM    │◄────►│  Langfuse    │
│   2.5 Flash     │      │  Monitoring  │
└─────────────────┘      └──────────────┘
         │
         ↓
┌─────────────────┐
│   PostgreSQL    │
│   + pgvector    │
├─────────────────┤
│  - Messages     │
│  - Sessions     │
│  - Embeddings   │
│  - Context      │
└─────────────────┘
```

### 3.2 Component Responsibilities

#### FastAPI Layer
- Receive WhatsApp webhook events
- Validate incoming requests
- Route messages to appropriate handlers
- Send responses back to WhatsApp
- Handle authentication and security
- Manage rate limiting

#### DSPy Layer
- Define conversation signatures
- Implement prompt optimization
- Manage LLM interactions
- Handle context injection
- Process multi-turn conversations

#### Data Layer (PostgreSQL + pgvector)
- Store conversation history
- Maintain user sessions
- Vector embeddings for semantic search
- Context retrieval for RAG patterns
- Analytics and metrics

#### Observability Layer (Langfuse)
- Track LLM calls and costs
- Monitor response quality
- Trace conversation flows
- Debug prompt performance
- A/B testing support

---

## 4. Core Features

### 4.1 MVP Features

#### Message Processing
- **Incoming Message Handling**
  - Receive text messages from WhatsApp
  - Parse message metadata (sender, timestamp, etc.)
  - Queue messages for processing

- **Response Generation**
  - Process messages through DSPy pipeline
  - Generate contextually relevant responses
  - Send responses via WhatsApp API

#### Context Management
- **Session Tracking**
  - Maintain conversation sessions per user
  - Track conversation state
  - Handle session timeouts

- **Memory & Context**
  - Store conversation history
  - Retrieve relevant context using vector search
  - Implement sliding window for recent messages

#### Basic Administration
- **Health Checks**
  - API health endpoints
  - Database connectivity checks
  - LLM availability monitoring

### 4.2 Phase 2 Features (Future)

- Multi-media support (images, documents)
- Multi-language conversations
- Custom bot personalities per use case
- Advanced RAG with document ingestion
- Analytics dashboard
- A/B testing different prompts
- User feedback collection
- Rate limiting per user
- Admin API for bot management

---

## 5. Technical Requirements

### 5.1 API Integration

#### Meta Cloud API (WhatsApp)
- Webhook endpoint for receiving messages from Meta
- Graph API for sending messages
- Message status tracking (delivered, read, failed)
- Webhook signature verification using App Secret
- Media handling (future phase)

**Required Meta Setup:**
- WhatsApp Business Account
- Meta App with WhatsApp Product
- Phone Number ID
- Access Token (temporary for dev, system user token for production)
- Webhook verification token

#### Required Endpoints

```
POST /webhooks/whatsapp
  - Receives incoming messages
  - Validates webhook signatures
  - Returns 200 OK immediately

GET /webhooks/whatsapp
  - Webhook verification endpoint
  - Required by WhatsApp for setup

POST /messages/send
  - Internal API to send messages
  - Handles retry logic

GET /health
  - Health check endpoint

GET /metrics
  - Prometheus-compatible metrics
```

### 5.2 Data Models

#### Core Entities

**User Session**
```python
- session_id: UUID (PK)
- user_phone: str
- created_at: timestamp
- updated_at: timestamp
- metadata: jsonb
- status: enum (active, expired, closed)
```

**Message**
```python
- message_id: UUID (PK)
- session_id: UUID (FK)
- direction: enum (incoming, outgoing)
- content: text
- timestamp: timestamp
- whatsapp_message_id: str
- metadata: jsonb
- embedding: vector (for pgvector)
```

**Conversation Context**
```python
- context_id: UUID (PK)
- session_id: UUID (FK)
- context_summary: text
- embedding: vector
- created_at: timestamp
- relevance_score: float
```

### 5.3 DSPy Architecture

#### Signatures
```python
class ConversationSignature(dspy.Signature):
    """Generate contextual response to user message"""
    user_message: str = dspy.InputField()
    conversation_history: str = dspy.InputField()
    context: str = dspy.InputField()
    response: str = dspy.OutputField()
```

#### Modules
- **MessageProcessor**: Main orchestration module
- **ContextRetriever**: Retrieves relevant context from vector store
- **ResponseGenerator**: Generates responses using LLM
- **HistoryManager**: Manages conversation history window

### 5.4 Infrastructure Requirements

#### Development Environment (Current Phase)
- **Local Development:**
  - Python 3.13+ environment
  - uv for dependency management
  - PostgreSQL 15+ with pgvector extension (local or RDS)
  - Docker for local services

- **AWS Resources:**
  - EC2 instance or Elastic Beanstalk for FastAPI (development tier)
  - RDS PostgreSQL with pgvector extension
  - Elastic IP or ALB for webhook endpoint (must be publicly accessible)
  - AWS Secrets Manager for API keys
  - CloudWatch for logging

- **External Services:**
  - Meta Developer Account (WhatsApp Cloud API)
  - Gemini API key
  - Langfuse account (cloud service recommended for dev)

- **Development Tools:**
  - ngrok or similar for local webhook testing
  - Postman/curl for API testing
  - Meta Graph API Explorer for testing

#### Future Production Considerations
- Docker containers
- Auto-scaling groups
- Multi-AZ RDS
- CloudFront/WAF for security
- Enhanced monitoring

---

## 6. Security & Compliance

### 6.1 Security Requirements
- Validate all WhatsApp webhook signatures
- Encrypt data at rest (database)
- Encrypt data in transit (TLS/HTTPS)
- Secure API key management (environment variables, secrets manager)
- Input validation and sanitization
- Rate limiting to prevent abuse
- OWASP Top 10 compliance

### 6.2 Privacy & Data Handling
- Store minimal user data
- Implement data retention policies
- Support user data deletion requests
- Log data anonymization
- Clear privacy policy for end users
- Compliance with GDPR/CCPA where applicable

### 6.3 WhatsApp Policy Compliance
- Adhere to WhatsApp Business Platform Terms
- 24-hour message window for non-template messages
- Handle opt-out requests
- No spam or unsolicited messages

---

## 7. Performance Requirements

### 7.1 Response Times
- Webhook acknowledgment: < 200ms
- Message processing: < 3 seconds (p95)
- Context retrieval: < 500ms
- End-to-end response: < 5 seconds (p95)

### 7.2 Scalability (Development Phase)
- Support 10-50 concurrent conversations initially
- Database query optimization for vector search
- Async processing for non-blocking operations
- Design for horizontal scaling in future

### 7.3 Reliability
- Graceful error handling
- Basic retry logic with exponential backoff
- Health check endpoints
- Proper logging for debugging

---

## 8. Testing Strategy

### 8.1 Unit Testing
- DSPy modules and signatures
- Message parsing and validation
- Context retrieval logic
- Database operations

### 8.2 Integration Testing
- WhatsApp webhook flow
- LLM API integration
- Database operations with pgvector
- Langfuse tracking

### 8.3 End-to-End Testing
- Full conversation flows
- Multi-turn conversations
- Error scenarios and recovery
- Rate limiting behavior

### 8.4 Load Testing
- Concurrent webhook processing
- Vector search performance
- LLM rate limits handling

---

## 9. Monitoring & Observability

### 9.1 Metrics
- Message processing rate
- Response latency (p50, p95, p99)
- LLM API errors and retries
- Database query performance
- Vector search accuracy

### 9.2 Logging
- Structured logging (JSON format)
- Request/response logging
- Error tracking and alerting
- Audit logs for security events

### 9.3 Langfuse Integration
- Track all LLM calls
- Monitor token usage and costs
- Trace conversation flows
- Evaluate response quality
- A/B test prompt variations

---

## 10. Development Roadmap

### Development Phase (Current Focus)

**Week 1: Foundation**
- [ ] Project setup with uv and FastAPI
- [ ] Local PostgreSQL + pgvector setup
- [ ] Basic project structure following Clean Architecture
- [ ] Environment configuration
- [ ] TDD setup with pytest

**Week 2: WhatsApp Integration**
- [ ] Meta Cloud API webhook endpoint
- [ ] Webhook verification
- [ ] Receive message handling
- [ ] Send message functionality
- [ ] Message signature validation

**Week 3: AI Core**
- [ ] DSPy setup and configuration
- [ ] Gemini LLM integration
- [ ] Basic conversation signatures
- [ ] Langfuse observability integration
- [ ] Simple prompt templates

**Week 4: Context & Memory**
- [ ] Database schema for sessions and messages
- [ ] Vector embedding generation
- [ ] Context retrieval with pgvector
- [ ] Conversation history management
- [ ] Session state tracking

**Week 5: AWS Deployment**
- [ ] Docker containerization
- [ ] AWS RDS PostgreSQL setup with pgvector
- [ ] EC2/Elastic Beanstalk deployment
- [ ] Environment variables and secrets
- [ ] Public webhook URL configuration

**Week 6: Testing & Refinement**
- [ ] Unit tests for core modules
- [ ] Integration tests for WhatsApp flow
- [ ] End-to-end conversation testing
- [ ] Error handling improvements
- [ ] Performance optimization
- [ ] Documentation

### Future Enhancements (Backlog)
- Advanced RAG with document ingestion
- Multi-media support (images, documents)
- Analytics dashboard
- Multiple bot personalities
- Admin API
- Multi-language support

---

## 11. Success Metrics (Development Phase)

### Technical Metrics
- Successful webhook message reception: 100%
- Average response time: < 5s
- Error rate: < 5% (development tolerance)
- Context retrieval accuracy: Monitor and improve

### Development Milestones
- Complete end-to-end conversation flow
- Multi-turn conversations working
- Context retention across messages
- Clean separation of concerns (architecture)
- Test coverage: > 70%
- All critical paths have tests

### Observability
- All LLM calls tracked in Langfuse
- Token usage monitoring
- Error logging and tracking
- Response quality evaluation

---

## 12. Risks & Mitigations

### Technical Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM API downtime | High | Implement fallback responses, queue messages |
| Vector search performance | Medium | Optimize indexes, implement caching |
| WhatsApp rate limits | High | Implement queue system, respect rate limits |
| Database scaling | Medium | Use connection pooling, read replicas |

### Business Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| High LLM costs | Medium | Monitor usage, implement cost controls |
| WhatsApp policy changes | High | Stay updated, design for flexibility |
| Data privacy concerns | High | Implement strong privacy controls |

---

## 13. Technical Decisions

### Confirmed
- **WhatsApp Provider**: Meta Cloud API
- **Hosting**: AWS
- **Use Case**: General-purpose conversational AI (development/learning phase)

### To Be Determined
- **User Authentication**: Phone number-based for now (simple session tracking)
- **Message Templates**: Not required for development (using standard messaging window)
- **Backup LLM**: Not implementing for MVP (can add later)
- **AWS Services**: Specific choices (EC2 vs Elastic Beanstalk, RDS configuration)
- **Langfuse Setup**: Cloud-hosted vs self-hosted

---

## 14. Appendices

### A. Reference Documentation
- [Meta Cloud API (WhatsApp)](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Meta Graph API](https://developers.facebook.com/docs/graph-api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [Langfuse Documentation](https://langfuse.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [AWS Documentation](https://docs.aws.amazon.com/)
- [uv Documentation](https://docs.astral.sh/uv/)

### B. Environment Variables
```bash
# LLM
GEMINI_API_KEY=your_gemini_api_key
DEFAULT_LLM_MODEL=gemini/gemini-2.5-flash

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
PGVECTOR_DIMENSION=1536

# Meta Cloud API (WhatsApp)
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_ACCESS_TOKEN=your_access_token
META_PHONE_NUMBER_ID=your_phone_number_id
META_VERIFY_TOKEN=your_custom_verify_token
META_GRAPH_API_VERSION=v21.0

# Langfuse
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# AWS (for deployment)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-25 | Claude | Initial PRD creation |
| 1.1 | 2025-10-25 | Claude | Updated for development phase: Meta Cloud API, AWS deployment, removed production scaling concerns, focused on MVP development roadmap |
