"""OpenAlex adapter — journal rank, topic classification, author metrics."""

from __future__ import annotations

from typing import cast, TypedDict

from backend.api.adapters.base_adapter import BaseAdapter, JSONObject, JSONValue
from backend.core.config import settings
from backend.models.api_responses import OpenAlexWork


class OpenAlexSearchResult(TypedDict):
    id: str | None
    doi: str | None
    title: str | None
    publication_year: int | None
    cited_by_count: int | None
    primary_topic: JSONValue | None
    relevance_score: float | int | None


class OpenAlexAdapter(BaseAdapter):
    """Queries api.openalex.org for work metadata, venue rank, and author data."""

    def __init__(self):
        params = {}
        if settings.openalex_api_key:
            params["api_key"] = settings.openalex_api_key

        super().__init__(
            base_url=settings.openalex_base_url,
            rate_limit=settings.openalex_rate_limit,
            headers={"User-Agent": "MatDAO/0.1"},
        )
        self._default_params = params

    async def fetch(self, doi: str) -> JSONObject:
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

    async def get_author(self, author_id: str) -> JSONObject:
        """Fetch author metrics (h-index, citation count) by OpenAlex author ID."""
        path = f"/authors/{author_id}"
        return await self._request("GET", path, params=self._default_params)

    async def search_works(self, query: str, per_page: int = 5) -> list[OpenAlexSearchResult]:
        """Search OpenAlex works for theme-level similarity when DOI lookup is unavailable."""
        if not query.strip():
            return []
        params = {
            **self._default_params,
            "search": query,
            "per-page": self._bounded(per_page),
            "sort": "relevance_score:desc",
        }
        data = await self._request("GET", "/works", params=params)
        results_value = data.get("results")
        if not isinstance(results_value, list):
            return []

        return cast(
            list[OpenAlexSearchResult],
            self._normalize_items(
                cast(list[JSONValue], results_value),
                lambda item: {
                    "id": item.get("id"),
                    "doi": item.get("doi"),
                    "title": item.get("title"),
                    "publication_year": item.get("publication_year"),
                    "cited_by_count": item.get("cited_by_count"),
                    "primary_topic": item.get("primary_topic"),
                    "relevance_score": item.get("relevance_score"),
                },
            ),
        )
