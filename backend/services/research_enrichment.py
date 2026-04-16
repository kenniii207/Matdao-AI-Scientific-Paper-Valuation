"""Document parsing and multi-source enrichment for paper evaluation."""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from typing import Any

from backend.api.adapters.openalex_adapter import OpenAlexAdapter
from backend.api.adapters.semantic_scholar_adapter import SemanticScholarAdapter
from backend.api.adapters.serpapi_scholar_adapter import SerpApiScholarAdapter
from backend.core.config import settings

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "have", "has", "had", "into", "their", "than", "then", "such", "using", "used",
    "between", "within", "without", "across", "study", "paper", "results", "method",
    "methods", "analysis", "based", "novel", "approach", "model", "models", "data",
    "our", "we", "they", "can", "may", "not", "also", "these", "those", "which",
}

_EMBEDDING_MODEL: Any = None
_RERANKER_MODEL: Any = None
_MODEL_LOCK = asyncio.Lock()


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


async def _with_timeout(coro: Any, timeout_seconds: float = 12.0) -> Any:
    return await asyncio.wait_for(coro, timeout=timeout_seconds)


def _candidate_text(candidate: dict[str, Any]) -> str:
    parts = [
        candidate.get("title"),
        candidate.get("summary"),
        candidate.get("snippet"),
        candidate.get("publication_info_summary"),
        candidate.get("venue"),
    ]
    cleaned = [_clean_line(str(part)) for part in parts if part]
    return " ".join(cleaned).strip()


def _collect_similarity_candidates(similar_papers: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for source, items in (similar_papers or {}).items():
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            candidate = {
                **item,
                "source": source,
                "source_rank": index + 1,
            }
            candidate_text = _candidate_text(candidate)
            if not candidate_text:
                continue
            candidate["candidate_text"] = candidate_text
            candidates.append(candidate)
    return candidates


def _build_query_text(document_profile: dict[str, Any]) -> str:
    title = _clean_line(str(document_profile.get("title") or ""))
    abstract = _clean_line(str(document_profile.get("abstract") or ""))[:600]
    keywords = document_profile.get("keywords") or []
    if isinstance(keywords, list):
        keyword_text = ", ".join(_clean_line(str(keyword)) for keyword in keywords[:6] if keyword)
    else:
        keyword_text = ""
    return " ".join(part for part in [title, abstract, keyword_text] if part).strip()


def _rank_candidates_by_embedding(
    query_text: str,
    candidates: list[dict[str, Any]],
    model: Any,
    top_k: int,
) -> list[dict[str, Any]]:
    if not query_text or not candidates:
        return []
    payload = [query_text] + [candidate["candidate_text"] for candidate in candidates]
    vectors = model.encode(
        payload,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=32,
    )
    query_vector = vectors[0]
    ranked: list[dict[str, Any]] = []
    for idx, candidate in enumerate(candidates, start=1):
        candidate_vector = vectors[idx]
        try:
            similarity = float((query_vector * candidate_vector).sum())
        except Exception:
            similarity = float(
                sum(float(a) * float(b) for a, b in zip(query_vector, candidate_vector))
            )
        ranked.append({**candidate, "semantic_score": round(similarity, 6)})
    ranked.sort(key=lambda item: item["semantic_score"], reverse=True)
    final_top = max(1, min(top_k, len(ranked)))
    return ranked[:final_top]


def _rerank_candidates(
    query_text: str,
    candidates: list[dict[str, Any]],
    reranker: Any,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    if not query_text or not candidates:
        return candidates

    rerank_limit = max(1, min(top_n, len(candidates)))
    head = candidates[:rerank_limit]
    tail = candidates[rerank_limit:]
    pairs = [[query_text, candidate["candidate_text"]] for candidate in head]
    scores = reranker.predict(pairs)
    scored = []
    for candidate, score in zip(head, scores):
        scored.append({**candidate, "rerank_score": round(float(score), 6)})
    scored.sort(key=lambda item: item["rerank_score"], reverse=True)
    return scored + tail


def _load_embedding_model() -> Any:
    from sentence_transformers import SentenceTransformer

    kwargs: dict[str, Any] = {}
    if settings.local_model_cache_dir.strip():
        kwargs["cache_folder"] = settings.local_model_cache_dir.strip()
    if settings.local_model_device.strip():
        kwargs["device"] = settings.local_model_device.strip()
    return SentenceTransformer(settings.local_embedding_model.strip(), **kwargs)


def _load_reranker_model() -> Any:
    from sentence_transformers import CrossEncoder

    kwargs: dict[str, Any] = {}
    if settings.local_model_cache_dir.strip():
        kwargs["cache_folder"] = settings.local_model_cache_dir.strip()
    if settings.local_model_device.strip():
        kwargs["device"] = settings.local_model_device.strip()
    return CrossEncoder(settings.local_reranker_model.strip(), **kwargs)


async def _get_embedding_model() -> Any:
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is not None:
        return _EMBEDDING_MODEL
    async with _MODEL_LOCK:
        if _EMBEDDING_MODEL is None:
            _EMBEDDING_MODEL = await asyncio.to_thread(_load_embedding_model)
    return _EMBEDDING_MODEL


async def _get_reranker_model() -> Any:
    global _RERANKER_MODEL
    if _RERANKER_MODEL is not None:
        return _RERANKER_MODEL
    async with _MODEL_LOCK:
        if _RERANKER_MODEL is None:
            _RERANKER_MODEL = await asyncio.to_thread(_load_reranker_model)
    return _RERANKER_MODEL


async def _apply_local_retrieval_phase2(
    enriched: dict[str, Any],
    document_profile: dict[str, Any],
) -> None:
    if not settings.enable_local_prefilter:
        return

    candidates = _collect_similarity_candidates(enriched.get("similar_papers", {}))
    if not candidates:
        enriched["source_errors"]["local_prefilter"] = "Skipped: no candidates from external sources"
        return

    query_text = _build_query_text(document_profile)
    if len(query_text) < 12:
        enriched["source_errors"]["local_prefilter"] = "Skipped: query text too short"
        return

    try:
        embedding_model = await _get_embedding_model()
        prefiltered = await asyncio.to_thread(
            _rank_candidates_by_embedding,
            query_text,
            candidates,
            embedding_model,
            max(3, settings.local_prefilter_top_k),
        )
        if settings.enable_local_reranker:
            reranker = await _get_reranker_model()
            prefiltered = await asyncio.to_thread(
                _rerank_candidates,
                query_text,
                prefiltered,
                reranker,
                10,
            )

        for rank, item in enumerate(prefiltered, start=1):
            item["retrieval_rank"] = rank

        enriched["similar_papers_curated"] = prefiltered
        enriched["local_retrieval"] = {
            "enabled": True,
            "embedding_model": settings.local_embedding_model,
            "reranker_model": settings.local_reranker_model if settings.enable_local_reranker else None,
            "prefilter_top_k": settings.local_prefilter_top_k,
            "candidate_count": len(candidates),
            "curated_count": len(prefiltered),
        }
    except Exception as exc:
        enriched["source_errors"]["local_prefilter"] = str(exc)


async def build_external_enrichment(
    doi: str,
    document_profile: dict[str, Any],
) -> dict[str, Any]:
    """Fetch DOI metadata + theme-similar papers from OpenAlex/S2/Scholar."""
    openalex = OpenAlexAdapter()
    semantic = SemanticScholarAdapter()
    serpapi = SerpApiScholarAdapter() if settings.serpapi_api_key else None
    per_source_limit = max(3, min(int(settings.theme_search_results_per_source), 10))

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
                _with_timeout(openalex.get_work(doi=doi), timeout_seconds=12.0),
                _with_timeout(semantic.get_paper(doi=doi), timeout_seconds=12.0),
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

        if queries and len(queries[0]) >= 12:
            theme_coroutines: list[Any] = [
                _with_timeout(
                    openalex.search_works(queries[0], per_page=per_source_limit),
                    timeout_seconds=10.0,
                ),
                _with_timeout(
                    semantic.search_papers(queries[0], limit=per_source_limit),
                    timeout_seconds=10.0,
                ),
            ]
            sources = ["openalex", "semantic_scholar"]
            if serpapi is not None:
                theme_coroutines.append(
                    _with_timeout(serpapi.search_papers(queries[0], limit=per_source_limit), timeout_seconds=10.0)
                )
                sources.append("google_scholar")
            else:
                enriched["source_errors"]["google_scholar_theme_search"] = "Skipped: SERPAPI_API_KEY not configured"

            theme_tasks = await asyncio.gather(*theme_coroutines, return_exceptions=True)
            for source_name, payload in zip(sources, theme_tasks):
                if isinstance(payload, Exception):
                    enriched["source_errors"][f"{source_name}_theme_search"] = str(payload)
                else:
                    enriched["similar_papers"][source_name] = payload
        elif not queries:
            enriched["source_errors"]["theme_search"] = "Skipped: no document query seed available"
        else:
            enriched["source_errors"]["theme_search"] = "Skipped: extracted query too short"

        await _apply_local_retrieval_phase2(enriched, document_profile)
    finally:
        await openalex.close()
        await semantic.close()
        if serpapi is not None:
            await serpapi.close()

    return enriched
