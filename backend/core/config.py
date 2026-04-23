"""Centralized configuration loaded from environment variables."""

import os
from typing import Any

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings — loaded from .env or environment."""

    # API Keys
    openalex_api_key: str = Field(default="", alias="OPENALEX_API_KEY")
    semantic_scholar_api_key: str = Field(default="", alias="SEMANTIC_SCHOLAR_API_KEY")
    zai_api_key: str = Field(default="", alias="ZAI_API_KEY")
    serpapi_api_key: str = Field(default="", alias="SERPAPI_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    glm_model: str = Field(default="glm-4.7-flash", alias="GLM_MODEL")
    glm_vision_model: str = Field(default="glm-4.6v-flash", alias="GLM_VISION_MODEL")
    glm_ocr_model: str = Field(default="glm-ocr", alias="GLM_OCR_MODEL")
    glm_ocr_layout_endpoint: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4/layout_parsing",
        alias="GLM_OCR_LAYOUT_ENDPOINT",
    )
    glm_ocr_timeout_seconds: int = Field(
        default=30,
        alias="GLM_OCR_TIMEOUT_SECONDS",
    )
    llm_fallback_order: str = Field(
        default="gemini,glm,openrouter,qwen,manus,kimi,minimax,liquid",
        alias="LLM_FALLBACK_ORDER",
    )
    llm_provider_timeout_seconds: int = Field(
        default=120,
        alias="LLM_PROVIDER_TIMEOUT_SECONDS",
    )
    llm_adaptive_routing_enabled: bool = Field(
        default=True,
        alias="LLM_ADAPTIVE_ROUTING_ENABLED",
    )
    llm_complexity_low_chars: int = Field(
        default=3500,
        alias="LLM_COMPLEXITY_LOW_CHARS",
    )
    llm_complexity_high_chars: int = Field(
        default=9000,
        alias="LLM_COMPLEXITY_HIGH_CHARS",
    )
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_api_url: str = Field(
        default="https://openrouter.ai/api/v1/chat/completions",
        alias="OPENROUTER_API_URL",
    )
    openrouter_models: str = Field(
        default=(
            "z-ai/glm-4.5-air:free,"
            "minimax/minimax-m2.5:free,"
            "google/gemma-4-31b-it:free,"
            "openai/gpt-oss-120b:free,"
            "nousresearch/hermes-3-llama-3.1-405b:free,"
            "nvidia/nemotron-3-nano-30b-a3b:free"
        ),
        alias="OPENROUTER_MODELS",
    )
    openrouter_max_models_per_eval: int = Field(
        default=3,
        alias="OPENROUTER_MAX_MODELS_PER_EVAL",
    )
    openrouter_reasoning_enabled: bool = Field(default=True, alias="OPENROUTER_REASONING_ENABLED")
    openrouter_site_url: str = Field(default="", alias="OPENROUTER_SITE_URL")
    openrouter_site_name: str = Field(default="", alias="OPENROUTER_SITE_NAME")
    kimi_api_key: str = Field(default="", alias="KIMI_API_KEY")
    kimi_base_url: str = Field(default="https://api.moonshot.cn/v1", alias="KIMI_BASE_URL")
    kimi_model: str = Field(default="kimi-k2-latest", alias="KIMI_MODEL")
    minimax_api_key: str = Field(default="", alias="MINIMAX_API_KEY")
    minimax_base_url: str = Field(default="", alias="MINIMAX_BASE_URL")
    minimax_model: str = Field(default="", alias="MINIMAX_MODEL")
    liquid_ai_api_key: str = Field(default="", alias="LIQUID_AI_API_KEY")
    liquid_ai_base_url: str = Field(default="", alias="LIQUID_AI_BASE_URL")
    liquid_ai_model: str = Field(default="", alias="LIQUID_AI_MODEL")
    qwen_api_key: str = Field(default="", alias="QWEN_API_KEY")
    qwen_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="QWEN_BASE_URL",
    )
    qwen_model: str = Field(default="qwen-plus", alias="QWEN_MODEL")
    manus_api_key: str = Field(default="", alias="MANUS_API_KEY")
    manus_base_url: str = Field(default="", alias="MANUS_BASE_URL")
    manus_model: str = Field(default="", alias="MANUS_MODEL")
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
    evaluation_job_poll_interval_seconds: float = Field(
        default=1.5,
        alias="EVALUATION_JOB_POLL_INTERVAL_SECONDS",
    )
    evaluation_job_lease_seconds: int = Field(
        default=240,
        alias="EVALUATION_JOB_LEASE_SECONDS",
    )
    evaluation_job_max_retries: int = Field(
        default=5,
        alias="EVALUATION_JOB_MAX_RETRIES",
    )
    evaluation_job_retry_base_seconds: int = Field(
        default=8,
        alias="EVALUATION_JOB_RETRY_BASE_SECONDS",
    )
    evaluation_stale_sweep_interval_seconds: int = Field(
        default=30,
        alias="EVALUATION_STALE_SWEEP_INTERVAL_SECONDS",
    )
    lightonocr_enabled: bool = Field(default=False, alias="LIGHTONOCR_ENABLED")
    lightonocr_base_url: str = Field(default="", alias="LIGHTONOCR_BASE_URL")
    lightonocr_timeout_seconds: int = Field(default=45, alias="LIGHTONOCR_TIMEOUT_SECONDS")
    lightonocr_health_timeout_seconds: int = Field(
        default=3,
        alias="LIGHTONOCR_HEALTH_TIMEOUT_SECONDS",
    )
    lightonocr_readiness_cache_seconds: int = Field(
        default=15,
        alias="LIGHTONOCR_READINESS_CACHE_SECONDS",
    )
    lightonocr_include_text_prompt: bool = Field(
        default=False,
        alias="LIGHTONOCR_INCLUDE_TEXT_PROMPT",
    )
    lightonocr_model_path: str = Field(default="", alias="LIGHTONOCR_MODEL_PATH")
    lightonocr_mmproj_path: str = Field(default="", alias="LIGHTONOCR_MMPROJ_PATH")
    lightonocr_require_local_paths: bool = Field(
        default=False,
        alias="LIGHTONOCR_REQUIRE_LOCAL_PATHS",
    )
    lightonocr_canary_percent: int = Field(default=0, alias="LIGHTONOCR_CANARY_PERCENT")
    ocr_fallback_order: str = Field(
        default="pdf_text,glm_ocr,lighton_ocr",
        alias="OCR_FALLBACK_ORDER",
    )
    ocr_max_upload_bytes: int = Field(
        default=25_000_000,
        alias="OCR_MAX_UPLOAD_BYTES",
    )
    ocr_max_pages_sync_text: int = Field(
        default=30,
        alias="OCR_MAX_PAGES_SYNC_TEXT",
    )
    ocr_render_max_pixels: int = Field(
        default=4_000_000,
        alias="OCR_RENDER_MAX_PIXELS",
    )
    ocr_fallback_timeout_seconds: int = Field(
        default=75,
        alias="OCR_FALLBACK_TIMEOUT_SECONDS",
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

    # API Base URLs (defaults per spec, override via env if needed)
    openalex_base_url: str = Field(default="https://api.openalex.org", alias="OPENALEX_BASE_URL")
    semantic_scholar_base_url: str = Field(
        default="https://api.semanticscholar.org/graph/v1",
        alias="SEMANTIC_SCHOLAR_BASE_URL",
    )
    serpapi_base_url: str = Field(default="https://serpapi.com", alias="SERPAPI_BASE_URL")
    osf_base_url: str = Field(default="https://api.osf.io/v2", alias="OSF_BASE_URL")
    clinical_trials_base_url: str = Field(
        default="https://clinicaltrials.gov/api/v2",
        alias="CLINICAL_TRIALS_BASE_URL",
    )

    # Rate Limits (requests per second)
    openalex_rate_limit: float = 100.0
    semantic_scholar_rate_limit: float = 100.0
    serpapi_rate_limit: float = 10.0
    osf_rate_limit: float = 10.0
    clinical_trials_rate_limit: float = 10.0

    @field_validator(
        "openalex_base_url",
        "semantic_scholar_base_url",
        "serpapi_base_url",
        "osf_base_url",
        "clinical_trials_base_url",
        "kimi_base_url",
        "minimax_base_url",
        "liquid_ai_base_url",
        "qwen_base_url",
        "manus_base_url",
        "lightonocr_base_url",
        mode="before",
    )
    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        text = str(value or "").strip()
        return text.rstrip("/") if text else text

    @field_validator("openrouter_api_url", mode="before")
    @classmethod
    def _normalize_openrouter_url(cls, value: str) -> str:
        text = str(value or "").strip()
        return text.rstrip("/") if text else text

    @field_validator("glm_ocr_layout_endpoint", mode="before")
    @classmethod
    def _normalize_glm_ocr_layout_endpoint(cls, value: str) -> str:
        text = str(value or "").strip()
        return text.rstrip("/") if text else text

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @field_validator(
        "llm_provider_timeout_seconds",
        "evaluation_pipeline_timeout_seconds",
        "glm_ocr_timeout_seconds",
        "lightonocr_timeout_seconds",
        "ocr_fallback_timeout_seconds",
        mode="before",
    )
    @classmethod
    def _clamp_timeout_values(cls, value: Any) -> int:
        parsed = cls._coerce_int(value, 30)
        return max(5, min(parsed, 1800))

    @field_validator("lightonocr_health_timeout_seconds", mode="before")
    @classmethod
    def _clamp_lighton_health_timeout(cls, value: Any) -> int:
        parsed = cls._coerce_int(value, 3)
        return max(1, min(parsed, 30))

    @field_validator("lightonocr_readiness_cache_seconds", mode="before")
    @classmethod
    def _clamp_lighton_cache_ttl(cls, value: Any) -> int:
        parsed = cls._coerce_int(value, 15)
        return max(0, min(parsed, 300))

    @field_validator("lightonocr_canary_percent", mode="before")
    @classmethod
    def _clamp_lighton_canary_percent(cls, value: Any) -> int:
        parsed = cls._coerce_int(value, 0)
        return max(0, min(parsed, 100))

    @field_validator("openrouter_max_models_per_eval", mode="before")
    @classmethod
    def _clamp_openrouter_max_models(cls, value: Any) -> int:
        parsed = cls._coerce_int(value, 3)
        return max(1, min(parsed, 8))

    @field_validator("ocr_max_pages_sync_text", mode="before")
    @classmethod
    def _clamp_ocr_max_pages_sync_text(cls, value: Any) -> int:
        parsed = cls._coerce_int(value, 30)
        return max(1, min(parsed, 200))

    @field_validator("ocr_max_upload_bytes", mode="before")
    @classmethod
    def _clamp_ocr_max_upload_bytes(cls, value: Any) -> int:
        parsed = cls._coerce_int(value, 25_000_000)
        return max(1_000_000, min(parsed, 200_000_000))

    @field_validator("ocr_render_max_pixels", mode="before")
    @classmethod
    def _clamp_ocr_render_max_pixels(cls, value: Any) -> int:
        parsed = cls._coerce_int(value, 4_000_000)
        return max(250_000, min(parsed, 40_000_000))

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
