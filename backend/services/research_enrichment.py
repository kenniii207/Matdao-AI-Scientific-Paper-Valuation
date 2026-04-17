"""Document parsing and multi-source enrichment for paper evaluation."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import re
import time
from collections import Counter
from typing import Any, Callable

from backend.api.adapters.openalex_adapter import OpenAlexAdapter
from backend.api.adapters.semantic_scholar_adapter import SemanticScholarAdapter
from backend.api.adapters.serpapi_scholar_adapter import SerpApiScholarAdapter
from backend.core.config import settings
from backend.core.exceptions import AdapterError

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
_CACHE_LOCK = asyncio.Lock()
_EXTERNAL_API_CACHE: dict[str, tuple[float, Any]] = {}
_CURATED_CACHE: dict[str, tuple[float, Any]] = {}
_SOURCE_HEALTH_COUNTS: dict[str, dict[str, int]] = {
    "openalex": {"success": 0, "error": 0, "cache_hit": 0},
    "semantic_scholar": {"success": 0, "error": 0, "cache_hit": 0},
    "google_scholar": {"success": 0, "error": 0, "cache_hit": 0},
}
logger = logging.getLogger(__name__)


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


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


def _cache_key(prefix: str, payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _normalize_dedupe_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())[:160]


async def _cache_get(
    cache: dict[str, tuple[float, Any]],
    key: str,
    ttl_seconds: int,
    enabled: bool,
) -> Any | None:
    if not enabled:
        return None
    async with _CACHE_LOCK:
        record = cache.get(key)
        if not record:
            return None
        expires_at, payload = record
        if expires_at < time.time():
            cache.pop(key, None)
            return None
        return copy.deepcopy(payload)


async def _cache_set(
    cache: dict[str, tuple[float, Any]],
    key: str,
    value: Any,
    ttl_seconds: int,
    max_entries: int,
    enabled: bool,
) -> None:
    if not enabled:
        return
    async with _CACHE_LOCK:
        cache[key] = (time.time() + max(1, ttl_seconds), copy.deepcopy(value))
        if len(cache) > max_entries:
            expired_keys = [cache_key for cache_key, (expires_at, _) in cache.items() if expires_at < time.time()]
            for expired_key in expired_keys:
                cache.pop(expired_key, None)
        if len(cache) > max_entries:
            oldest_keys = sorted(cache.items(), key=lambda item: item[1][0])[: len(cache) - max_entries]
            for oldest_key, _ in oldest_keys:
                cache.pop(oldest_key, None)


async def _record_source_health(source: str, field: str) -> None:
    if source not in _SOURCE_HEALTH_COUNTS:
        _SOURCE_HEALTH_COUNTS[source] = {"success": 0, "error": 0, "cache_hit": 0}
    async with _CACHE_LOCK:
        _SOURCE_HEALTH_COUNTS[source][field] = _SOURCE_HEALTH_COUNTS[source].get(field, 0) + 1


async def _source_health_snapshot() -> dict[str, dict[str, int]]:
    async with _CACHE_LOCK:
        return copy.deepcopy(_SOURCE_HEALTH_COUNTS)


async def _get_source_payload(
    *,
    source: str,
    cache_key: str,
    factory: Callable[[], Any],
    timeout_seconds: float,
    source_errors: dict[str, str],
    error_key: str,
) -> Any | None:
    cached_payload = await _cache_get(
        _EXTERNAL_API_CACHE,
        cache_key,
        settings.external_api_cache_ttl_seconds,
        settings.enable_external_api_cache,
    )
    if cached_payload is not None:
        await _record_source_health(source, "cache_hit")
        await _record_source_health(source, "success")
        return cached_payload
    try:
        payload = await _with_timeout(factory(), timeout_seconds=timeout_seconds)
    except (asyncio.TimeoutError, AdapterError, ValueError, TypeError) as exc:
        source_errors[error_key] = str(exc)
        await _record_source_health(source, "error")
        return None
    await _cache_set(
        _EXTERNAL_API_CACHE,
        cache_key,
        payload,
        settings.external_api_cache_ttl_seconds,
        settings.external_api_cache_max_entries,
        settings.enable_external_api_cache,
    )
    await _record_source_health(source, "success")
    return payload


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


def _collect_similarity_candidates(
    similar_papers: dict[str, Any],
    stats: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_dedupe_keys: set[str] = set()
    duplicate_count = 0
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
            dedupe_key = _normalize_dedupe_key(str(candidate.get("title") or candidate_text))
            if dedupe_key and dedupe_key in seen_dedupe_keys:
                duplicate_count += 1
                continue
            if dedupe_key:
                seen_dedupe_keys.add(dedupe_key)
            candidate["candidate_text"] = candidate_text
            candidates.append(candidate)
    if stats is not None:
        stats["dedupe_removed"] = duplicate_count
        stats["dedupe_remaining"] = len(candidates)
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
    stage_timings = enriched.setdefault("stage_timings_ms", {})
    stage_start = time.perf_counter()
    if not settings.enable_local_prefilter:
        stage_timings["local_prefilter_ms"] = _elapsed_ms(stage_start)
        return

    dedupe_stats: dict[str, int] = {}
    candidates = enriched.get("similar_papers_deduped")
    if not isinstance(candidates, list):
        candidates = _collect_similarity_candidates(enriched.get("similar_papers", {}), stats=dedupe_stats)
    else:
        dedupe_stats["dedupe_removed"] = int(enriched.get("retrieval_quality", {}).get("dedupe_removed", 0))
        dedupe_stats["dedupe_remaining"] = len(candidates)

    if not candidates:
        enriched["source_errors"]["local_prefilter"] = "Skipped: no candidates from external sources"
        stage_timings["local_prefilter_ms"] = _elapsed_ms(stage_start)
        return

    query_text = _build_query_text(document_profile)
    if len(query_text) < 12:
        enriched["source_errors"]["local_prefilter"] = "Skipped: query text too short"
        stage_timings["local_prefilter_ms"] = _elapsed_ms(stage_start)
        return

    try:
        curated_cache_key = _cache_key(
            "curated_topk",
            {
                "query": query_text,
                "top_k": max(3, settings.local_prefilter_top_k),
                "reranker": settings.enable_local_reranker,
                "candidates": [
                    {
                        "source": candidate.get("source"),
                        "title": candidate.get("title"),
                        "result_id": candidate.get("result_id"),
                        "paper_id": candidate.get("paper_id"),
                    }
                    for candidate in candidates
                ],
            },
        )
        cached_prefiltered = await _cache_get(
            _CURATED_CACHE,
            curated_cache_key,
            settings.curated_cache_ttl_seconds,
            settings.enable_curated_cache,
        )
        if cached_prefiltered is not None:
            prefiltered = cached_prefiltered
            cache_hit = True
        else:
            cache_hit = False
            model_load_timeout = max(1, int(settings.local_model_load_timeout_seconds))
            embedding_model = await asyncio.wait_for(
                _get_embedding_model(),
                timeout=model_load_timeout,
            )
            prefiltered = await asyncio.to_thread(
                _rank_candidates_by_embedding,
                query_text,
                candidates,
                embedding_model,
                max(3, settings.local_prefilter_top_k),
            )
            if settings.enable_local_reranker:
                reranker = await asyncio.wait_for(
                    _get_reranker_model(),
                    timeout=model_load_timeout,
                )
                prefiltered = await asyncio.to_thread(
                    _rerank_candidates,
                    query_text,
                    prefiltered,
                    reranker,
                    10,
                )
            await _cache_set(
                _CURATED_CACHE,
                curated_cache_key,
                prefiltered,
                settings.curated_cache_ttl_seconds,
                settings.curated_cache_max_entries,
                settings.enable_curated_cache,
            )

        for rank, item in enumerate(prefiltered, start=1):
            item["retrieval_rank"] = rank

        enriched["similar_papers_curated"] = prefiltered
        enriched["retrieval_quality"] = {
            **enriched.get("retrieval_quality", {}),
            **dedupe_stats,
            "curated_cache_hit": cache_hit,
        }
        enriched["local_retrieval"] = {
            "enabled": True,
            "embedding_model": settings.local_embedding_model,
            "reranker_model": settings.local_reranker_model if settings.enable_local_reranker else None,
            "prefilter_top_k": settings.local_prefilter_top_k,
            "candidate_count": len(candidates),
            "curated_count": len(prefiltered),
            "curated_cache_hit": cache_hit,
        }
    except asyncio.TimeoutError:
        enriched["source_errors"]["local_prefilter"] = (
            f"Skipped: local model load timed out after {max(1, int(settings.local_model_load_timeout_seconds))}s"
        )
        enriched["local_retrieval"] = {
            "enabled": False,
            "skipped_reason": "model_load_timeout",
        }
    except (RuntimeError, ValueError, TypeError, OSError, ImportError) as exc:
        enriched["source_errors"]["local_prefilter"] = str(exc)
        enriched["local_retrieval"] = {
            "enabled": False,
            "skipped_reason": str(exc),
        }
    finally:
        stage_timings["local_prefilter_ms"] = _elapsed_ms(stage_start)


async def build_external_enrichment(
    doi: str,
    document_profile: dict[str, Any],
) -> dict[str, Any]:
    """Fetch DOI metadata + theme-similar papers from OpenAlex/S2/Scholar."""
    total_start = time.perf_counter()
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
        "stage_timings_ms": {},
    }
    stage_timings = enriched["stage_timings_ms"]

    try:
        doi_lookup_start = time.perf_counter()
        if doi and not doi.startswith("10.matdao/"):
            doi_tasks = await asyncio.gather(
                _get_source_payload(
                    source="openalex",
                    cache_key=_cache_key("openalex_doi", {"doi": doi}),
                    factory=lambda: openalex.get_work(doi=doi),
                    timeout_seconds=12.0,
                    source_errors=enriched["source_errors"],
                    error_key="openalex_doi",
                ),
                _get_source_payload(
                    source="semantic_scholar",
                    cache_key=_cache_key("semantic_scholar_doi", {"doi": doi}),
                    factory=lambda: semantic.get_paper(doi=doi),
                    timeout_seconds=12.0,
                    source_errors=enriched["source_errors"],
                    error_key="semantic_scholar_doi",
                ),
            )
            if doi_tasks[0] is not None:
                enriched["openalex"] = doi_tasks[0]
            if doi_tasks[1] is not None:
                enriched["semantic_scholar"] = doi_tasks[1]
        stage_timings["doi_lookup_ms"] = _elapsed_ms(doi_lookup_start)

        theme_search_start = time.perf_counter()
        if queries and len(queries[0]) >= 12:
            theme_coroutines: list[tuple[str, Any]] = [
                (
                    "openalex",
                    _get_source_payload(
                        source="openalex",
                        cache_key=_cache_key(
                            "openalex_theme",
                            {"query": queries[0], "limit": per_source_limit},
                        ),
                        factory=lambda: openalex.search_works(queries[0], per_page=per_source_limit),
                        timeout_seconds=10.0,
                        source_errors=enriched["source_errors"],
                        error_key="openalex_theme_search",
                    ),
                ),
                (
                    "semantic_scholar",
                    _get_source_payload(
                        source="semantic_scholar",
                        cache_key=_cache_key(
                            "semantic_scholar_theme",
                            {"query": queries[0], "limit": per_source_limit},
                        ),
                        factory=lambda: semantic.search_papers(queries[0], limit=per_source_limit),
                        timeout_seconds=10.0,
                        source_errors=enriched["source_errors"],
                        error_key="semantic_scholar_theme_search",
                    ),
                ),
            ]
            if serpapi is not None:
                theme_coroutines.append(
                    (
                        "google_scholar",
                        _get_source_payload(
                            source="google_scholar",
                            cache_key=_cache_key(
                                "google_scholar_theme",
                                {"query": queries[0], "limit": per_source_limit},
                            ),
                            factory=lambda: serpapi.search_papers(queries[0], limit=per_source_limit),
                            timeout_seconds=10.0,
                            source_errors=enriched["source_errors"],
                            error_key="google_scholar_theme_search",
                        ),
                    )
                )
            else:
                enriched["source_errors"]["google_scholar_theme_search"] = "Skipped: SERPAPI_API_KEY not configured"

            theme_tasks = await asyncio.gather(*(coroutine for _, coroutine in theme_coroutines))
            for (source_name, _), payload in zip(theme_coroutines, theme_tasks):
                if payload is not None:
                    enriched["similar_papers"][source_name] = payload
        elif not queries:
            enriched["source_errors"]["theme_search"] = "Skipped: no document query seed available"
        else:
            enriched["source_errors"]["theme_search"] = "Skipped: extracted query too short"
        stage_timings["theme_search_ms"] = _elapsed_ms(theme_search_start)

        dedupe_stats: dict[str, int] = {}
        deduped_candidates = _collect_similarity_candidates(
            enriched.get("similar_papers", {}),
            stats=dedupe_stats,
        )
        enriched["similar_papers_deduped"] = deduped_candidates
        enriched["retrieval_quality"] = dedupe_stats

        await _apply_local_retrieval_phase2(enriched, document_profile)
        enriched["source_health"] = await _source_health_snapshot()
    finally:
        await openalex.close()
        await semantic.close()
        if serpapi is not None:
            await serpapi.close()

    stage_timings["build_external_enrichment_ms"] = _elapsed_ms(total_start)
    logger.info(
        "Enrichment completed doi=%s timings_ms=%s source_errors=%s",
        doi,
        stage_timings,
        list((enriched.get("source_errors") or {}).keys()),
    )

    return enriched
