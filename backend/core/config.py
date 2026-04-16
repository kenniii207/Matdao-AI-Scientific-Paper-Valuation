"""Centralized configuration loaded from environment variables."""

import os

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings — loaded from .env or environment."""

    # API Keys
    openalex_api_key: str = Field(default="", alias="OPENALEX_API_KEY")
    semantic_scholar_api_key: str = Field(default="", alias="SEMANTIC_SCHOLAR_API_KEY")
    zai_api_key: str = Field(default="", alias="ZAI_API_KEY")
    serpapi_api_key: str = Field(default="", alias="SERPAPI_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    evaluation_text_max_chars: int = Field(default=12000, alias="EVALUATION_TEXT_MAX_CHARS")
    theme_search_results_per_source: int = Field(default=5, alias="THEME_SEARCH_RESULTS_PER_SOURCE")
    max_parallel_evaluations: int = Field(default=2, alias="MAX_PARALLEL_EVALUATIONS")
    enable_local_prefilter: bool = Field(default=False, alias="ENABLE_LOCAL_PREFILTER")
    enable_local_reranker: bool = Field(default=False, alias="ENABLE_LOCAL_RERANKER")
    local_prefilter_top_k: int = Field(default=10, alias="LOCAL_PREFILTER_TOP_K")
    local_embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="LOCAL_EMBEDDING_MODEL")
    local_reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L6-v2",
        alias="LOCAL_RERANKER_MODEL",
    )
    local_model_device: str = Field(default="cpu", alias="LOCAL_MODEL_DEVICE")
    local_model_cache_dir: str = Field(default="", alias="LOCAL_MODEL_CACHE_DIR")
    local_model_load_timeout_seconds: int = Field(
        default=12,
        alias="LOCAL_MODEL_LOAD_TIMEOUT_SECONDS",
    )
    enable_external_api_cache: bool = Field(default=True, alias="ENABLE_EXTERNAL_API_CACHE")
    external_api_cache_ttl_seconds: int = Field(default=86400, alias="EXTERNAL_API_CACHE_TTL_SECONDS")
    external_api_cache_max_entries: int = Field(default=500, alias="EXTERNAL_API_CACHE_MAX_ENTRIES")
    enable_curated_cache: bool = Field(default=True, alias="ENABLE_CURATED_CACHE")
    curated_cache_ttl_seconds: int = Field(default=86400, alias="CURATED_CACHE_TTL_SECONDS")
    curated_cache_max_entries: int = Field(default=500, alias="CURATED_CACHE_MAX_ENTRIES")
    evaluation_pipeline_timeout_seconds: int = Field(
        default=120,
        alias="EVALUATION_PIPELINE_TIMEOUT_SECONDS",
    )

    # Service URLs
    database_url: str = Field(
        default="postgresql+asyncpg://matdao:matdao_secret@localhost:5432/matdao_db",
        alias="DATABASE_URL",
    )

    @property
    def async_database_url(self) -> str:
        url = os.environ.get("POSTGRES_URL", self.database_url)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # App
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    frontend_port: int = Field(default=3000, alias="FRONTEND_PORT")

    # API Base URLs (not user-configured — hardcoded per spec)
    openalex_base_url: str = "https://api.openalex.org"
    semantic_scholar_base_url: str = "https://api.semanticscholar.org/graph/v1"
    serpapi_base_url: str = "https://serpapi.com"
    osf_base_url: str = "https://api.osf.io/v2"
    clinical_trials_base_url: str = "https://clinicaltrials.gov/api/v2"

    # Rate Limits (requests per second)
    openalex_rate_limit: float = 100.0
    semantic_scholar_rate_limit: float = 100.0
    serpapi_rate_limit: float = 10.0
    osf_rate_limit: float = 10.0
    clinical_trials_rate_limit: float = 10.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
