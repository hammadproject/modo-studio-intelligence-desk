from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class BusinessConfig(BaseModel):
    version: int
    identity: str
    assistant_name: str
    instructions: list[str]
    fallback_message: str
    handoff_offer: str


class AssistantResponseConfig(BaseModel):
    response: str


class AssistantGeneralBehaviorConfig(BaseModel):
    unknown_business_detail: AssistantResponseConfig
    ambiguous_message: AssistantResponseConfig
    off_topic: AssistantResponseConfig


class AssistantIntentConfig(BaseModel):
    id: str
    priority: int = 0
    examples: list[str] = Field(default_factory=list)
    responses: list[str] = Field(default_factory=list)
    behavior: str | None = None
    retrieval_required: bool = False


class AssistantIntentMatchingConfig(BaseModel):
    predefined_intents: list[AssistantIntentConfig] = Field(default_factory=list)


class AssistantCustomerLanguageConfig(BaseModel):
    preferred_uncertainty_phrases: list[str]
    internal_terms_to_avoid: list[str]


class AssistantFailureMessagesConfig(BaseModel):
    temporary_service_error: str


class AssistantIdentityConfig(BaseModel):
    name: str
    role: str


class AssistantConfig(BaseModel):
    version: int
    assistant: AssistantIdentityConfig
    intent_matching: AssistantIntentMatchingConfig
    general_behavior: AssistantGeneralBehaviorConfig
    customer_facing_language: AssistantCustomerLanguageConfig
    failure_messages: AssistantFailureMessagesConfig

    @property
    def customer_facing_instructions(self) -> str:
        avoided = ", ".join(self.customer_facing_language.internal_terms_to_avoid)
        preferred = " ".join(
            self.customer_facing_language.preferred_uncertainty_phrases
        )
        return (
            "Speak directly as Modo Studio's assistant. Never expose internal "
            f"implementation language or mention these terms: {avoided}. "
            "When a detail is unavailable, use natural customer-facing business "
            f"language such as: {preferred}"
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_name: str = "Modo Studio Intelligence Desk API"
    environment: Literal["local", "test", "demo", "production"] = "local"
    provider_mode: Literal["live", "deterministic"] = "live"
    database_url: str = "postgresql+asyncpg://chirpy:chirpy@localhost:5432/chirpy"
    admin_api_key: str = "local-admin-change-me"
    admin_display_name: str = "Modo Studio"
    admin_session_hours: int = Field(default=12, ge=1, le=168)
    visitor_session_days: int = Field(default=30, ge=1, le=365)
    visitor_presence_seconds: int = Field(default=75, ge=30, le=600)
    conversation_archive_after_hours: int = Field(default=24, ge=1, le=8760)
    visitor_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    conversation_token_pepper: str = "local-pepper-change-me"
    business_config_path: Path = Path("config/business.v1.json")
    assistant_config_path: Path = Path("config/assistant.v1.json")
    cors_allow_origins: str = (
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"
    )
    log_level: str = "INFO"
    log_conversation_content: bool = False

    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    groq_api_key: str | None = None
    embedding_provider: str = "cloudflare"
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    embedding_dimension: int = 768
    cloudflare_account_id: str | None = None
    cloudflare_api_token: str | None = None
    cloudflare_embedding_model: str = "@cf/baai/bge-base-en-v1.5"
    vector_provider: str = "pinecone"
    reranker_provider: str = "jina"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    jina_api_key: str | None = None
    jina_reranker_model: str = "jina-reranker-v3.5"
    pinecone_api_key: str | None = None
    vector_index_name: str = "modo-studio-knowledge"
    vector_collection: str = "modo-studio-v1"
    retrieval_top_k: int = Field(default=5, ge=1, le=20)
    retrieval_candidate_k: int = Field(default=10, ge=1, le=50)
    retrieval_relevance_threshold: float = Field(default=0.60, ge=-1, le=1)
    provider_timeout_seconds: float = Field(default=20, gt=0, le=120)
    provider_max_retries: int = Field(default=2, ge=0, le=5)

    history_token_budget: int = Field(default=1800, ge=128)
    summary_trigger_tokens: int = Field(default=2400, ge=256)
    max_message_chars: int = Field(default=1500, ge=1)
    max_upload_bytes: int = Field(default=5_000_000, ge=1024)
    chunk_size_chars: int = Field(default=1200, ge=100)
    chunk_overlap_chars: int = Field(default=150, ge=0)
    requests_per_minute: int = Field(default=60, ge=1)
    admin_requests_per_minute: int = Field(default=600, ge=1)

    @property
    def async_database_url(self) -> str:
        url = make_url(self.database_url).set(drivername="postgresql+asyncpg")
        query = dict(url.query)
        sslmode = query.pop("sslmode", None)
        # asyncpg calls this option `ssl`; Neon connection strings use the
        # libpq-compatible `sslmode` spelling. Channel binding is handled by
        # libpq/psycopg but is not an asyncpg connection argument.
        if sslmode:
            query["ssl"] = sslmode
        query.pop("channel_binding", None)
        return url.set(query=query).render_as_string(hide_password=False)

    @property
    def sync_database_url(self) -> str:
        url = make_url(self.database_url).set(drivername="postgresql+psycopg")
        query = dict(url.query)
        ssl = query.pop("ssl", None)
        if ssl:
            query["sslmode"] = ssl
        return url.set(query=query).render_as_string(hide_password=False)

    @property
    def cors_origins(self) -> list[str]:
        return [
            item.strip() for item in self.cors_allow_origins.split(",") if item.strip()
        ]

    @model_validator(mode="after")
    def validate_configuration(self) -> Settings:
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError(
                "CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS"
            )
        if self.retrieval_candidate_k < self.retrieval_top_k:
            raise ValueError(
                "RETRIEVAL_CANDIDATE_K must be greater than or equal to RETRIEVAL_TOP_K"
            )
        if self.environment == "production":
            if self.provider_mode != "live":
                raise ValueError("Production requires PROVIDER_MODE=live")
            required = {
                "GROQ_API_KEY": self.groq_api_key,
                "PINECONE_API_KEY": self.pinecone_api_key,
            }
            if self.embedding_provider == "cloudflare":
                required.update(
                    {
                        "CLOUDFLARE_ACCOUNT_ID": self.cloudflare_account_id,
                        "CLOUDFLARE_API_TOKEN": self.cloudflare_api_token,
                    }
                )
            if self.reranker_provider == "jina":
                required["JINA_API_KEY"] = self.jina_api_key
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(
                    f"Missing production configuration: {', '.join(missing)}"
                )
            if self.admin_api_key == "local-admin-change-me":
                raise ValueError("ADMIN_API_KEY must be changed in production")
            if self.conversation_token_pepper == "local-pepper-change-me":
                raise ValueError(
                    "CONVERSATION_TOKEN_PEPPER must be changed in production"
                )
        return self

    def load_business_config(self) -> BusinessConfig:
        path = self.business_config_path
        if not path.is_absolute():
            path = Path.cwd() / path
        return BusinessConfig.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )

    def load_assistant_config(self) -> AssistantConfig:
        path = self.assistant_config_path
        if not path.is_absolute():
            path = Path.cwd() / path
        return AssistantConfig.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
