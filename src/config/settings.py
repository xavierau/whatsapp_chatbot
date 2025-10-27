"""Application configuration using pydantic-settings."""

from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = Field(..., min_length=32)
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    # Database
    database_url: PostgresDsn
    pgvector_dimension: int = 1536  # Gemini gemini-embedding-001 dimension

    # Meta Cloud API (WhatsApp)
    meta_app_id: str
    meta_app_secret: str
    meta_access_token: str
    meta_phone_number_id: str
    meta_verify_token: str
    meta_graph_api_version: str = "v21.0"
    meta_graph_api_base_url: str = "https://graph.facebook.com"

    # LLM Configuration
    gemini_api_key: str
    default_llm_model: str = "gemini/gemini-2.5-flash"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=4000, gt=0)
    embedding_model: str = "gemini-embedding-001"

    # Langfuse (Observability)
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str = "https://cloud.langfuse.com"

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # Session Configuration
    session_timeout_minutes: int = Field(default=30, gt=0)
    max_conversation_history: int = Field(default=10, gt=0)

    @property
    def allowed_origins_list(self) -> list[str]:
        """Get allowed origins as a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def meta_graph_api_url(self) -> str:
        """Construct the full Meta Graph API URL."""
        return f"{self.meta_graph_api_base_url}/{self.meta_graph_api_version}"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


# Global settings instance
settings = Settings()
