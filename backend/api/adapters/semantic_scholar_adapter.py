"""Semantic Scholar adapter — influentialCitationCount, citation velocity."""

from __future__ import annotations

from typing import cast, TypedDict

from backend.api.adapters.base_adapter import BaseAdapter, JSONObject, JSONValue
from backend.core.config import settings
from backend.models.api_responses import SemanticScholarPaper


class SemanticScholarSearchResult(TypedDict):
    paper_id: str | None
    title: str | None
    citation_count: int | None
    influential_citation_count: int | None
    year: int | None
    venue: str | None


class SemanticScholarAdapter(BaseAdapter):
    """Queries api.semanticscholar.org for citation impact metrics."""

    FIELDS = "paperId,title,influentialCitationCount,citationCount,year,venue,authors"
    SEARCH_FIELDS = "paperId,title,influentialCitationCount,citationCount,year,venue"

    def __init__(self):
        headers = {}
        if settings.semantic_scholar_api_key:
            headers["x-api-key"] = settings.semantic_scholar_api_key

        super().__init__(
            base_url=settings.semantic_scholar_base_url,
            rate_limit=settings.semantic_scholar_rate_limit,
            headers=headers,
        )

    async def fetch(self, doi: str) -> JSONObject:
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

    async def search_papers(self, query: str, limit: int = 5) -> list[SemanticScholarSearchResult]:
        """Search Semantic Scholar for semantically similar papers."""
        if not query.strip():
            return []
        data = await self._request(
            "GET",
            "/paper/search",
            params={
                "query": query,
                "limit": self._bounded(limit),
                "fields": self.SEARCH_FIELDS,
            },
        )
        papers_value = data.get("data")
        if not isinstance(papers_value, list):
            return []

        return cast(
            list[SemanticScholarSearchResult],
            self._normalize_items(
                cast(list[JSONValue], papers_value),
                lambda paper: {
                    "paper_id": paper.get("paperId"),
                    "title": paper.get("title"),
                    "citation_count": paper.get("citationCount"),
                    "influential_citation_count": paper.get("influentialCitationCount"),
                    "year": paper.get("year"),
                    "venue": paper.get("venue"),
                },
            ),
        )
