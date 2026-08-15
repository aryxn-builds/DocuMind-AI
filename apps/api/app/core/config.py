"""
DocuMind AI — FastAPI Configuration.

All settings are loaded from environment variables (via .env file in development).
Never hardcode secrets here.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --------------------------------------------------
    # Application
    # --------------------------------------------------
    app_name: str = "DocuMind AI"
    app_version: str = "0.1.0"
    debug: bool = False

    # --------------------------------------------------
    # CORS
    # --------------------------------------------------
    backend_cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Comma-separated list of allowed CORS origins.",
    )

    # --------------------------------------------------
    # Supabase
    # --------------------------------------------------
    supabase_url: str = Field(default="", description="Supabase project URL.")
    supabase_anon_key: str = Field(default="", description="Supabase anon/public key.")
    supabase_service_role_key: str = Field(
        default="",
        description="Supabase service role key (server-side only).",
    )
    supabase_jwt_secret: str = Field(
        default="",
        description="Supabase JWT secret for token verification.",
    )
    database_url: str = Field(default="", description="PostgreSQL connection string.")

    # --------------------------------------------------
    # Qdrant
    # --------------------------------------------------
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant server URL.")
    qdrant_api_key: str = Field(default="", description="Qdrant API key (optional for local dev).")

    # --------------------------------------------------
    # LLM Providers
    # --------------------------------------------------
    groq_api_key: str = Field(default="", description="Groq API key.")
    gemini_api_key: str = Field(default="", description="Google Gemini API key.")
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server base URL.",
    )

    # --------------------------------------------------
    # AI Configuration
    # --------------------------------------------------
    default_llm_provider: str = Field(
        default="groq",
        description="Default LLM provider: groq | gemini | ollama.",
    )
    default_embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Sentence Transformers model for embeddings.",
    )
    default_vision_provider: str = Field(
        default="gemini",
        description="Vision provider: gemini | ollama.",
    )

    # --------------------------------------------------
    # Langfuse (Observability)
    # --------------------------------------------------
    langfuse_public_key: str = Field(default="", description="Langfuse public key.")
    langfuse_secret_key: str = Field(default="", description="Langfuse secret key.")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse host URL.",
    )

    # --------------------------------------------------
    # Upload Limits
    # --------------------------------------------------
    max_file_size_mb: int = Field(default=25, description="Maximum upload file size in megabytes.")
    allowed_file_types: str = Field(
        default="application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg",
        description="Comma-separated list of allowed MIME types.",
    )


# Singleton settings instance — import this everywhere.
settings = Settings()
