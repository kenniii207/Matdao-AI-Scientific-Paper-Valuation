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
    openalex_email: str = Field(default="ops@matdao.ai", alias="OPENALEX_EMAIL")

    # Rate Limits (requests per second)
    openalex_rate_limit: float = 100.0
    semantic_scholar_rate_limit: float = 100.0
    serpapi_rate_limit: float = 10.0
    osf_rate_limit: float = 10.0
    clinical_trials_rate_limit: float = 10.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
