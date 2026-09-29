"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal, Optional


class Settings(BaseSettings):
    """All configuration from .env with validation."""

    # App
    APP_ENV: Literal["development", "production"] = "development"
    AUTH_MODE: Literal["demo", "jwt"] = "demo"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # LLM
    LLM_PROVIDER: Literal["google", "openai"] = "google"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.0-flash"

    # Embeddings
    EMBEDDING_PROVIDER: Literal["google", "openai"] = "google"
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIM: int = 768

    # Agent limits
    MAX_TOOL_CALLS: int = 5
    LLM_TIMEOUT_S: int = 20
    DB_TIMEOUT_S: int = 5

    # RAG
    RAG_TOP_K: int = 4
    RAG_MIN_SIMILARITY: float = 0.35

    # Logging
    LOG_LEVEL: str = "INFO"

    # Order client
    ORDER_CLIENT: Literal["local", "http"] = "local"

    # Failure simulation (dev only)
    SIMULATE_FAILURE: Optional[str] = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()

# Demo user ID mapping (fixed UUIDs from seed.sql)
DEMO_USERS = {
    "alice": "d0000000-0000-0000-0000-000000000001",
    "bob": "d0000000-0000-0000-0000-000000000002",
    "carol": "d0000000-0000-0000-0000-000000000003",
}
