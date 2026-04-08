"""OpenAlex adapter — journal rank, topic classification, author metrics."""

from __future__ import annotations

from typing import Any

from backend.api.adapters.base_adapter import BaseAdapter
from backend.core.config import settings
from backend.models.api_responses import OpenAlexWork


class OpenAlexAdapter(BaseAdapter):
    """Queries api.openalex.org for work metadata, venue rank, and author data."""

    def __init__(self):
        params = {}
        if settings.openalex_api_key:
            params["api_key"] = settings.openalex_api_key

        super().__init__(
            base_url=settings.openalex_base_url,
            rate_limit=settings.openalex_rate_limit,
            headers={"User-Agent": f"MatDAO/0.1 (mailto:{settings.crossref_email})"},
        )
        self._default_params = params

    async def fetch(self, doi: str) -> dict[str, Any]:
        """Fetch work by DOI from OpenAlex."""
        path = f"/works/doi:{doi}"
        data = await self._request("GET", path, params=self._default_params)
        return data

    async def get_work(self, doi: str) -> OpenAlexWork:
        """Fetch and validate work data."""
        data = await self.fetch(doi)
        return OpenAlexWork(
            doi=data.get("doi"),
            title=data.get("title"),
            relevance_score=data.get("relevance_score"),
            cited_by_count=data.get("cited_by_count"),
            publication_date=data.get("publication_date"),
            primary_topic=data.get("primary_topic"),
            authorships=data.get("authorships", []),
            raw_json=data,
        )

    async def get_author(self, author_id: str) -> dict[str, Any]:
        """Fetch author metrics (h-index, citation count) by OpenAlex author ID."""
        path = f"/authors/{author_id}"
        return await self._request("GET", path, params=self._default_params)
