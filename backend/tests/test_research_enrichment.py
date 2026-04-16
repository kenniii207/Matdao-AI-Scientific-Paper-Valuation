"""Tests for local retrieval prefilter and reranker helpers."""

from __future__ import annotations

import asyncio

import pytest

from backend.services import research_enrichment as enrichment


def test_collect_similarity_candidates_normalizes_sources():
    similar_papers = {
        "openalex": [
            {"title": "Graph diffusion for catalysts", "summary": "Catalyst screening"},
            {"title": "Second paper"},
        ],
        "semantic_scholar": [
            {"title": "Catalyst graph optimization", "venue": "Nature"},
        ],
    }
    candidates = enrichment._collect_similarity_candidates(similar_papers)
    assert len(candidates) == 3
    assert candidates[0]["source"] == "openalex"
    assert candidates[0]["source_rank"] == 1
    assert "candidate_text" in candidates[0]


def test_collect_similarity_candidates_dedupes_titles():
    similar_papers = {
        "openalex": [{"title": "Graph diffusion for catalysts"}],
        "semantic_scholar": [{"title": "Graph diffusion for catalysts"}],
    }
    stats = {}
    candidates = enrichment._collect_similarity_candidates(similar_papers, stats=stats)
    assert len(candidates) == 1
    assert stats["dedupe_removed"] == 1
    assert stats["dedupe_remaining"] == 1


def test_rank_candidates_by_embedding_orders_by_similarity():
    candidates = [
        {"title": "A", "candidate_text": "doc_a"},
        {"title": "B", "candidate_text": "doc_b"},
        {"title": "C", "candidate_text": "doc_c"},
    ]

    class FakeEmbeddingModel:
        def encode(self, payload, **kwargs):
            assert payload[0] == "query"
            # Query aligns most with doc_b, then doc_a, then doc_c
            return [
                [1.0, 0.0],  # query
                [0.7, 0.3],  # doc_a
                [0.95, 0.05],  # doc_b
                [0.2, 0.8],  # doc_c
            ]

    ranked = enrichment._rank_candidates_by_embedding(
        query_text="query",
        candidates=candidates,
        model=FakeEmbeddingModel(),
        top_k=2,
    )
    assert len(ranked) == 2
    assert ranked[0]["title"] == "B"
    assert ranked[1]["title"] == "A"


def test_rerank_candidates_reorders_top_n():
    candidates = [
        {"title": "A", "candidate_text": "doc_a"},
        {"title": "B", "candidate_text": "doc_b"},
        {"title": "C", "candidate_text": "doc_c"},
    ]

    class FakeReranker:
        def predict(self, pairs):
            score_map = {"doc_a": 0.1, "doc_b": 0.9, "doc_c": 0.3}
            return [score_map[pair[1]] for pair in pairs]

    reranked = enrichment._rerank_candidates(
        query_text="query",
        candidates=candidates,
        reranker=FakeReranker(),
        top_n=3,
    )
    assert [item["title"] for item in reranked] == ["B", "C", "A"]
    assert "rerank_score" in reranked[0]


@pytest.mark.asyncio
async def test_apply_local_retrieval_phase2_populates_curated(monkeypatch):
    similar_papers = {
        "openalex": [{"title": "Alpha catalyst screening"}],
        "semantic_scholar": [{"title": "Catalyst optimization via graphs"}],
    }
    enriched = {"similar_papers": similar_papers, "source_errors": {}}
    document_profile = {
        "title": "Graph catalyst screening",
        "abstract": "We optimize catalysts with graph methods.",
        "keywords": ["catalyst", "graph", "screening"],
    }

    monkeypatch.setattr(enrichment.settings, "enable_local_prefilter", True)
    monkeypatch.setattr(enrichment.settings, "enable_local_reranker", True)
    monkeypatch.setattr(enrichment.settings, "local_prefilter_top_k", 10)
    monkeypatch.setattr(enrichment.settings, "local_embedding_model", "fake-embed")
    monkeypatch.setattr(enrichment.settings, "local_reranker_model", "fake-reranker")

    class FakeEmbeddingModel:
        def encode(self, payload, **kwargs):
            return [
                [1.0, 0.0],  # query
                [0.6, 0.4],  # alpha
                [0.9, 0.1],  # beta
            ]

    class FakeReranker:
        def predict(self, pairs):
            score_map = {
                "Alpha catalyst screening": 0.2,
                "Catalyst optimization via graphs": 0.95,
            }
            return [score_map[pair[1]] for pair in pairs]

    async def fake_get_embedding_model():
        return FakeEmbeddingModel()

    async def fake_get_reranker_model():
        return FakeReranker()

    monkeypatch.setattr(enrichment, "_get_embedding_model", fake_get_embedding_model)
    monkeypatch.setattr(enrichment, "_get_reranker_model", fake_get_reranker_model)

    await enrichment._apply_local_retrieval_phase2(enriched, document_profile)

    assert "similar_papers_curated" in enriched
    assert enriched["similar_papers_curated"][0]["title"] == "Catalyst optimization via graphs"
    assert enriched["local_retrieval"]["enabled"] is True


@pytest.mark.asyncio
async def test_apply_local_retrieval_phase2_uses_curated_cache(monkeypatch):
    similar_papers = {"openalex": [{"title": "Alpha catalyst screening"}]}
    enriched = {"similar_papers": similar_papers, "source_errors": {}}
    document_profile = {
        "title": "Graph catalyst screening",
        "abstract": "We optimize catalysts with graph methods.",
        "keywords": ["catalyst"],
    }

    monkeypatch.setattr(enrichment.settings, "enable_local_prefilter", True)
    monkeypatch.setattr(enrichment.settings, "enable_local_reranker", False)
    monkeypatch.setattr(enrichment.settings, "enable_curated_cache", True)
    monkeypatch.setattr(enrichment.settings, "curated_cache_ttl_seconds", 86400)
    monkeypatch.setattr(enrichment.settings, "curated_cache_max_entries", 200)

    class FakeEmbeddingModel:
        def encode(self, payload, **kwargs):
            return [[1.0, 0.0], [0.8, 0.2]]

    async def fake_get_embedding_model():
        return FakeEmbeddingModel()

    monkeypatch.setattr(enrichment, "_get_embedding_model", fake_get_embedding_model)
    await enrichment._apply_local_retrieval_phase2(enriched, document_profile)
    assert enriched["local_retrieval"]["curated_cache_hit"] is False

    async def fail_if_called():
        raise AssertionError("Embedding model should not be requested on curated cache hit")

    monkeypatch.setattr(enrichment, "_get_embedding_model", fail_if_called)
    enriched_second = {"similar_papers": similar_papers, "source_errors": {}}
    await enrichment._apply_local_retrieval_phase2(enriched_second, document_profile)
    assert enriched_second["local_retrieval"]["curated_cache_hit"] is True


@pytest.mark.asyncio
async def test_apply_local_retrieval_phase2_skips_when_model_load_times_out(monkeypatch):
    similar_papers = {"openalex": [{"title": "Alpha catalyst screening"}]}
    enriched = {"similar_papers": similar_papers, "source_errors": {}}
    document_profile = {
        "title": "Graph catalyst screening",
        "abstract": "We optimize catalysts with graph methods.",
        "keywords": ["catalyst"],
    }

    monkeypatch.setattr(enrichment.settings, "enable_local_prefilter", True)
    monkeypatch.setattr(enrichment.settings, "enable_local_reranker", False)
    monkeypatch.setattr(enrichment.settings, "enable_curated_cache", False)
    monkeypatch.setattr(enrichment.settings, "local_model_load_timeout_seconds", 1)

    async def slow_embedding_model():
        await asyncio.sleep(1.5)
        return object()

    monkeypatch.setattr(enrichment, "_get_embedding_model", slow_embedding_model)
    await enrichment._apply_local_retrieval_phase2(enriched, document_profile)
    assert "timed out" in enriched["source_errors"]["local_prefilter"]
    assert enriched["local_retrieval"]["enabled"] is False
