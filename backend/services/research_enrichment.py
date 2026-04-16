"""Document parsing and multi-source enrichment for paper evaluation."""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from typing import Any

from backend.api.adapters.openalex_adapter import OpenAlexAdapter
from backend.api.adapters.semantic_scholar_adapter import SemanticScholarAdapter
from backend.api.adapters.serpapi_scholar_adapter import SerpApiScholarAdapter

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "have", "has", "had", "into", "their", "than", "then", "such", "using", "used",
    "between", "within", "without", "across", "study", "paper", "results", "method",
    "methods", "analysis", "based", "novel", "approach", "model", "models", "data",
    "our", "we", "they", "can", "may", "not", "also", "these", "those", "which",
}


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())


def _extract_title(text: str, fallback_title: str | None = None) -> str:
    for line in text.splitlines()[:25]:
        candidate = _clean_line(line)
        if 20 <= len(candidate) <= 220 and not candidate.lower().startswith(("abstract", "keywords")):
            return candidate
    return (fallback_title or "Untitled research paper").strip()


def _extract_abstract(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    abstract_match = re.search(
        r"(?is)\babstract\b[:\s]*(.{200,3500}?)(?:\n\s*\n|\n\s*(?:introduction|background|methods?|materials))",
        normalized,
    )
    if abstract_match:
        return _clean_line(abstract_match.group(1))[:1800]

    first_block = _clean_line(" ".join(normalized.splitlines()[:60]))
    return first_block[:1800]


def _extract_keywords(text: str, max_keywords: int = 8) -> list[str]:
    kw_match = re.search(r"(?is)\bkeywords?\b[:\s]*(.{0,300})", text)
    if kw_match:
        raw = kw_match.group(1)
        candidates = [
            _clean_line(part).strip(".,;")
            for part in re.split(r"[,;•·|]", raw)
        ]
        normalized = [token for token in candidates if 3 <= len(token) <= 60]
        if normalized:
            return normalized[:max_keywords]

    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z\-]{3,}\b", text.lower())
    freq = Counter(token for token in tokens if token not in STOPWORDS)
    return [word for word, _ in freq.most_common(max_keywords)]


def build_document_profile(text: str, fallback_title: str | None = None) -> dict[str, Any]:
    """Extract LLM- and search-friendly structure from OCR/PDF text."""
    title = _extract_title(text, fallback_title=fallback_title)
    abstract = _extract_abstract(text)
    keywords = _extract_keywords(text)
    query_seed = " ".join([title] + keywords[:4]).strip()
    return {
        "title": title,
        "abstract": abstract,
        "keywords": keywords,
        "query_seed": query_seed,
    }


async def build_external_enrichment(
    doi: str,
    document_profile: dict[str, Any],
) -> dict[str, Any]:
    """Fetch DOI metadata + theme-similar papers from OpenAlex/S2/Scholar."""
    openalex = OpenAlexAdapter()
    semantic = SemanticScholarAdapter()
    serpapi = SerpApiScholarAdapter()

    query_seed = (document_profile.get("query_seed") or "").strip()
    title = (document_profile.get("title") or "").strip()
    queries: list[str] = []
    for query in [title, query_seed]:
        if query and query not in queries:
            queries.append(query)
    queries = queries[:2]

    enriched: dict[str, Any] = {
        "document_profile": document_profile,
        "similar_papers": {},
        "source_errors": {},
    }

    try:
        if doi and not doi.startswith("10.matdao/"):
            doi_tasks = await asyncio.gather(
                openalex.get_work(doi=doi),
                semantic.get_paper(doi=doi),
                return_exceptions=True,
            )
            if isinstance(doi_tasks[0], Exception):
                enriched["source_errors"]["openalex_doi"] = str(doi_tasks[0])
            else:
                enriched["openalex"] = doi_tasks[0]
            if isinstance(doi_tasks[1], Exception):
                enriched["source_errors"]["semantic_scholar_doi"] = str(doi_tasks[1])
            else:
                enriched["semantic_scholar"] = doi_tasks[1]

        if queries:
            theme_tasks = await asyncio.gather(
                openalex.search_works(queries[0], per_page=5),
                semantic.search_papers(queries[0], limit=5),
                serpapi.search_papers(queries[0], limit=5),
                return_exceptions=True,
            )
            sources = ("openalex", "semantic_scholar", "google_scholar")
            for source_name, payload in zip(sources, theme_tasks):
                if isinstance(payload, Exception):
                    enriched["source_errors"][f"{source_name}_theme_search"] = str(payload)
                else:
                    enriched["similar_papers"][source_name] = payload
    finally:
        await openalex.close()
        await semantic.close()
        await serpapi.close()

    return enriched
