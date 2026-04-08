"""Centralized configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings — loaded from .env or environment."""

    # API Keys
    openalex_api_key: str = Field(default="", alias="OPENALEX_API_KEY")
    semantic_scholar_api_key: str = Field(default="", alias="SEMANTIC_SCHOLAR_API_KEY")
    nih_reporter_email: str = Field(default="", alias="NIH_REPORTER_EMAIL")
    crossref_email: str = Field(default="", alias="CROSSREF_EMAIL")
    zhipu_api_key: str = Field(default="", alias="ZHIPU_API_KEY")

    # Service URLs
    database_url: str = Field(
        default="postgresql+asyncpg://matdao:matdao_secret@localhost:5432/matdao_db",
        alias="DATABASE_URL",
    )
    grobid_url: str = Field(default="http://localhost:8070", alias="GROBID_URL")

    # App
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    frontend_port: int = Field(default=3000, alias="FRONTEND_PORT")

    # API Base URLs (not user-configured — hardcoded per spec)
    openalex_base_url: str = "https://api.openalex.org"
    semantic_scholar_base_url: str = "https://api.semanticscholar.org/graph/v1"
    crossref_base_url: str = "https://api.crossref.org"
    nih_reporter_base_url: str = "https://api.reporter.nih.gov/v2"
    osf_base_url: str = "https://api.osf.io/v2"
    clinical_trials_base_url: str = "https://clinicaltrials.gov/api/v2"

    # Rate Limits (requests per second)
    openalex_rate_limit: float = 100.0
    semantic_scholar_rate_limit: float = 100.0
    crossref_rate_limit: float = 0.83  # 50/min
    nih_reporter_rate_limit: float = 1.0
    osf_rate_limit: float = 10.0
    clinical_trials_rate_limit: float = 10.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
