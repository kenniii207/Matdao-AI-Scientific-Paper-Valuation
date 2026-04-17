"""SerpAPI Google Scholar adapter for supplemental citation metadata."""

from __future__ import annotations

from typing import cast, TypedDict

from backend.api.adapters.base_adapter import BaseAdapter, JSONObject, JSONValue
from backend.core.config import settings
from backend.models.api_responses import SerpApiScholarPaper


class SerpApiSearchResult(TypedDict):
    title: str | None
    result_id: str | None
    summary: str | None
    cited_by_count: int | None
    snippet: str | None


class SerpApiScholarAdapter(BaseAdapter):
    """Queries SerpAPI google_scholar engine and normalizes top result metadata."""

    def __init__(self):
        super().__init__(
            base_url=settings.serpapi_base_url,
            rate_limit=settings.serpapi_rate_limit,
        )

    async def fetch(self, query: str) -> JSONObject:
        """Fetch Google Scholar results for a DOI or title query."""
        params = {
            "engine": "google_scholar",
            "q": query,
            "api_key": settings.serpapi_api_key,
        }
        return await self._request("GET", "/search", params=params)

    async def get_top_paper(self, query: str) -> SerpApiScholarPaper:
        """Return the first organic result as normalized scoring input."""
        data = await self.fetch(query)
        organic_results = data.get("organic_results", [])
        top_result = organic_results[0] if organic_results else {}
        inline_links = top_result.get("inline_links", {})
        cited_by = inline_links.get("cited_by", {})
        return SerpApiScholarPaper(
            title=top_result.get("title"),
            result_id=top_result.get("result_id"),
            cited_by_count=cited_by.get("total"),
            publication_info_summary=top_result.get("publication_info", {}).get("summary"),
            raw_json=top_result or data,
        )

    async def search_papers(self, query: str, limit: int = 5) -> list[SerpApiSearchResult]:
        """Return top Google Scholar organic results for theme lookup."""
        if not query.strip():
            return []
        data = await self.fetch(query)
        organic_results_value = data.get("organic_results")
        if not isinstance(organic_results_value, list):
            return []

        organic_results = organic_results_value[: self._bounded(limit)]
        return cast(
            list[SerpApiSearchResult],
            self._normalize_items(
                cast(list[JSONValue], organic_results),
                lambda result: {
                    "title": result.get("title"),
                    "result_id": result.get("result_id"),
                    "summary": result.get("publication_info", {}).get("summary")
                    if isinstance(result.get("publication_info"), dict)
                    else None,
                    "cited_by_count": (
                        result.get("inline_links", {})
                        .get("cited_by", {})
                        .get("total")
                        if isinstance(result.get("inline_links"), dict)
                        else None
                    ),
                    "snippet": result.get("snippet"),
                },
            ),
        )
