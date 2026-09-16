"""Application settings.

All runtime configuration is read from environment variables (and the local
``.env`` file).  Environment variables always win over ``.env`` values, which
keeps production deployments and the test-suite (which injects its own values)
predictable.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Healthcare Assistant backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application -----------------------------------------------------
    app_name: str = "Healthcare Assistant API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # --- Database --------------------------------------------------------
    # SQLite is the default so the project runs with zero external services.
    database_url: str = "sqlite:///./healthcare_assistant.db"
    auto_create_tables: bool = True

    # --- Security --------------------------------------------------------
    jwt_secret_key: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60 * 24, gt=0)

    # --- CORS ------------------------------------------------------------
    cors_allow_origins: list[str] = ["*"]

    # --- Memory Agent / RAG (Module 4) -----------------------------------
    # The two Chroma collections (``patient_records`` / ``medical_knowledge``)
    # live inside ``chroma_persist_directory``; ``chroma_mode=ephemeral`` keeps
    # everything in memory, which the test-suite uses.
    chroma_persist_directory: str = "./chroma_store"
    chroma_mode: str = "persistent"
    collection_patient_records: str = "patient_records"
    collection_medical_knowledge: str = "medical_knowledge"

    # ``sentence-transformers`` is the production embedding provider; the
    # deterministic ``hashing`` provider is an offline fallback (no model
    # download) used by tests and air-gapped environments.
    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = Field(default=384, gt=0)

    # RAG chunking / retrieval tuning.
    rag_chunk_size: int = Field(default=800, gt=0)
    rag_chunk_overlap: int = Field(default=120, ge=0)
    rag_top_k: int = Field(default=5, gt=0)
    rag_relevance_distance: float = Field(default=0.9, ge=0, le=2)
    rag_max_query_length: int = Field(default=1000, gt=0)
    rag_max_excerpt_length: int = Field(default=600, gt=0)

    # Patient document storage (metadata stays in the relational database).
    document_storage_directory: str = "./storage/patient_documents"
    max_document_size_mb: int = Field(default=20, gt=0)
    max_documents_per_page: int = Field(default=100, gt=0)
    medical_knowledge_directory: str = "./medical_knowledge"

    # --- Continuous vital monitoring / escalation (Module 6) -------------
    vital_simulator_interval_seconds: float = Field(default=5.0, gt=0)
    alert_ack_timeout_seconds: float = Field(default=300.0, gt=0)
    caretaker_phone_number: str | None = None
    sms_provider: str = "mock"
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_phone_number: str | None = None
    twilio_timeout_seconds: float = Field(default=10.0, gt=0)
    hospital_provider: str = "mock"
    # Meta WhatsApp Cloud API is optional.  When either credential is unset the
    # provider safely skips delivery, allowing the local mock-SMS workflow to
    # remain the default.
    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_api_version: str = "v22.0"
    whatsapp_timeout_seconds: float = Field(default=10.0, gt=0)

    # Optional Acno AI intelligence provider. Disabled when unset; the
    # deterministic risk engine remains the safety authority.
    acno_ai_api_key: str | None = None
    acno_ai_base_url: str | None = None
    acno_ai_model: str = ""
    acno_ai_timeout_seconds: float = Field(default=5.0, gt=0)

    # AI Care chat.  The model can answer general questions and is grounded
    # with patient-owned report excerpts when RAG finds relevant context.
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    groq_timeout_seconds: float = Field(default=30.0, gt=0)
    ai_care_max_context_excerpts: int = Field(default=5, gt=0)

    @property
    def is_sqlite(self) -> bool:
        """Return ``True`` when the configured database is SQLite."""
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return the cached :class:`Settings` instance."""
    return Settings()


settings = get_settings()
