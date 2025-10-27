# WhatsApp AI Chatbot

AI-powered WhatsApp chatbot using DSPy, Gemini LLM, and Meta Cloud API.

## Tech Stack

- **Framework**: FastAPI
- **AI/LLM**: DSPy + Gemini 2.5 Flash
- **Database**: PostgreSQL + pgvector
- **Observability**: Langfuse
- **WhatsApp**: Meta Cloud API
- **Deployment**: AWS

## Development Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure your credentials
3. Install dependencies:
   ```bash
   uv sync
   ```
4. Run the application:
   ```bash
   uv run uvicorn src.main:app --reload
   ```

## Project Structure

```
src/
├── domain/          # Business entities and repository interfaces
├── application/     # Use cases and application logic
├── infrastructure/  # External integrations (DB, LLM, WhatsApp)
├── interface/       # API routes and schemas
└── config/          # Configuration
```

## Documentation

See `docs/architecture/` for detailed architecture documentation.
