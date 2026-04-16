"""SerpAPI Google Scholar adapter for supplemental citation metadata."""

from __future__ import annotations

from typing import Any

from backend.api.adapters.base_adapter import BaseAdapter
from backend.core.config import settings
from backend.models.api_responses import SerpApiScholarPaper


class SerpApiScholarAdapter(BaseAdapter):
    """Queries SerpAPI google_scholar engine and normalizes top result metadata."""

    def __init__(self):
        super().__init__(
            base_url=settings.serpapi_base_url,
            rate_limit=settings.serpapi_rate_limit,
        )

    async def fetch(self, query: str) -> dict[str, Any]:
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
