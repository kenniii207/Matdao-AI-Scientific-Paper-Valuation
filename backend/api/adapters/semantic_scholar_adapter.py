"""Semantic Scholar adapter — influentialCitationCount, citation velocity."""

from __future__ import annotations

from typing import Any

from backend.api.adapters.base_adapter import BaseAdapter
from backend.core.config import settings
from backend.models.api_responses import SemanticScholarPaper


class SemanticScholarAdapter(BaseAdapter):
    """Queries api.semanticscholar.org for citation impact metrics."""

    FIELDS = "paperId,title,influentialCitationCount,citationCount,year,venue,authors"

    def __init__(self):
        headers = {}
        if settings.semantic_scholar_api_key:
            headers["x-api-key"] = settings.semantic_scholar_api_key

        super().__init__(
            base_url=settings.semantic_scholar_base_url,
            rate_limit=settings.semantic_scholar_rate_limit,
            headers=headers,
        )

    async def fetch(self, doi: str) -> dict[str, Any]:
        """Fetch paper by DOI from Semantic Scholar."""
        path = f"/paper/DOI:{doi}"
        return await self._request("GET", path, params={"fields": self.FIELDS})

    async def get_paper(self, doi: str) -> SemanticScholarPaper:
        """Fetch and validate paper data."""
        data = await self.fetch(doi)
        return SemanticScholarPaper(
            paper_id=data.get("paperId"),
            title=data.get("title"),
            influential_citation_count=data.get("influentialCitationCount"),
            citation_count=data.get("citationCount"),
            year=data.get("year"),
            venue=data.get("venue"),
            authors=data.get("authors", []),
            raw_json=data,
        )
