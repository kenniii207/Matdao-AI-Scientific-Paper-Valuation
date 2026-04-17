"""Tests for evaluation quality signal helpers."""

import pytest

from backend.services import evaluation as evaluation_service


def test_detect_generic_output_flags_known_generic_phrase():
    evaluation_service._RECENT_INSIGHTS.clear()
    payload = {
        "insight": "Your research shows strong scientific rigor but limited commercialization signals.",
        "warnings": ["No go-to-market strategy"],
    }
    result = evaluation_service._detect_generic_output(payload)
    assert result["generic_output_detected"] is True
    assert "contains_generic_phrase" in result["generic_output_reasons"]


def test_detect_generic_output_flags_recent_repeat_pattern():
    evaluation_service._RECENT_INSIGHTS.clear()
    payload = {"insight": "Paper is promising for translational pathway with strong reproducibility."}
    evaluation_service._detect_generic_output(payload)
    evaluation_service._detect_generic_output(payload)
    result = evaluation_service._detect_generic_output(payload)
    assert result["generic_output_detected"] is True
    assert "recent_repeat_pattern" in result["generic_output_reasons"]


def test_attach_quality_signals_sets_stage_timing_and_provider():
    evaluation_service._RECENT_INSIGHTS.clear()
    evaluator = evaluation_service.ScientificEvaluator()
    enriched = evaluator._attach_quality_signals(
        {"insight": "Specific insight tied to evidence."},
        provider="gemini",
        llm_stage_ms=123.45,
    )
    assert enriched["stage_timings_ms"]["llm_stage_ms"] == 123.45
    assert enriched["_quality_signals"]["llm_provider"] == "gemini"


def test_validate_and_repair_schema_normalizes_dimension_payload():
    evaluator = evaluation_service.ScientificEvaluator()
    repaired = evaluator._validate_and_repair_schema(
        {
            "scores": {
                "1": {"score": "9.7", "rationale": "", "origin_snippet": ""},
                "2": {"score": "bad", "rationale": "Provided rationale", "origin_snippet": "snippet"},
            },
            "insight": "",
        },
        metadata={"source_errors": {}},
    )
    assert set(repaired["scores"].keys()) == {str(index) for index in range(1, 10)}
    assert repaired["scores"]["1"]["score"] == 5.0
    assert repaired["scores"]["2"]["score"] == 3.0
    assert repaired["scores"]["1"]["rationale"]
    assert repaired["scores"]["1"]["origin_snippet"]
    assert repaired["_quality_signals"]["schema_repair_applied"] is True
    assert repaired["_quality_signals"]["schema_repair_count"] > 0


def test_validate_and_repair_schema_applies_insufficient_evidence_template():
    evaluator = evaluation_service.ScientificEvaluator()
    repaired = evaluator._validate_and_repair_schema(
        {"scores": {}},
        metadata={"source_errors": {"openalex": "timeout", "semantic_scholar": "503"}},
    )
    assert repaired["_quality_signals"]["insufficient_evidence"] is True
    assert repaired["executive_summary"] == evaluation_service._INSUFFICIENT_EVIDENCE_SUMMARY
    assert repaired["investment_recommendation"] == evaluation_service._INSUFFICIENT_EVIDENCE_RECOMMENDATION
    assert any("manual analyst review" in warning.lower() for warning in repaired["warnings"])


def test_validate_and_repair_schema_keeps_high_evidence_without_template_override():
    evaluator = evaluation_service.ScientificEvaluator()
    repaired = evaluator._validate_and_repair_schema(
        {
            "scores": {
                str(index): {
                    "score": 4.0,
                    "rationale": f"Rationale {index}",
                    "origin_snippet": f"Concrete snippet {index}",
                }
                for index in range(1, 10)
            },
            "executive_summary": "Tailored summary",
            "insight": "Tailored insight",
            "investment_recommendation": "Tier B",
            "investor_fit": ["Specialist fund"],
            "warnings": ["Needs additional customer interviews"],
        },
        metadata={"source_errors": {}},
    )
    assert repaired["_quality_signals"]["insufficient_evidence"] is False
    assert repaired["executive_summary"] == "Tailored summary"
    assert repaired["insight"] == "Tailored insight"


def test_has_structured_scores_requires_minimum_dimensions():
    assert evaluation_service._has_structured_scores({"scores": {"1": {"score": 4.0}}}) is False
    assert (
        evaluation_service._has_structured_scores(
            {
                "scores": {
                    str(idx): {"score": 3.0}
                    for idx in range(1, 7)
                }
            }
        )
        is True
    )


@pytest.mark.asyncio
async def test_evaluate_content_falls_back_to_glm_when_gemini_fails(monkeypatch):
    monkeypatch.setattr(evaluation_service.settings, "gemini_api_key", "test-gemini")
    monkeypatch.setattr(evaluation_service.settings, "zai_api_key", "test-zai")
    evaluator = evaluation_service.ScientificEvaluator()
    evaluator.api_key = "test-zai"

    async def fake_gemini(_prompt: str):
        return {"error": "gemini_503"}

    async def fake_glm(_prompt: str):
        return {
            "scores": {
                str(idx): {"score": 3.7, "rationale": f"R{idx}", "origin_snippet": f"S{idx}"}
                for idx in range(1, 10)
            },
            "insight": "Fallback analysis ties scorecard outputs to concrete manuscript evidence and metadata.",
            "executive_summary": "Fallback summary",
            "warnings": ["Fallback warning"],
        }

    monkeypatch.setattr(evaluator, "_evaluate_with_gemini", fake_gemini)
    monkeypatch.setattr(evaluator, "_evaluate_with_glm", fake_glm)

    result = await evaluator.evaluate_content("paper text", {"document_profile": {"title": "T"}})
    assert result["_quality_signals"]["llm_provider"] == "glm_fallback"
    assert result["insight"].startswith("Fallback analysis ties scorecard")
    assert result["_quality_signals"]["provider_errors"]["gemini"] == "gemini_503"
    assert result["_quality_signals"].get("llm_hard_failure") is not True


@pytest.mark.asyncio
async def test_evaluate_content_marks_hard_failure_when_all_providers_fail(monkeypatch):
    monkeypatch.setattr(evaluation_service.settings, "gemini_api_key", "test-gemini")
    monkeypatch.setattr(evaluation_service.settings, "zai_api_key", "test-zai")
    evaluator = evaluation_service.ScientificEvaluator()
    evaluator.api_key = "test-zai"

    async def fake_fail(_prompt: str):
        return {"error": "service_unavailable"}

    monkeypatch.setattr(evaluator, "_evaluate_with_gemini", fake_fail)
    monkeypatch.setattr(evaluator, "_evaluate_with_glm", fake_fail)

    result = await evaluator.evaluate_content("paper text", {"document_profile": {"title": "T"}})
    assert result["_quality_signals"]["llm_hard_failure"] is True
    assert result["_quality_signals"]["llm_provider"] == "none"
    assert "provider_errors" in result["_quality_signals"]


@pytest.mark.asyncio
async def test_evaluate_content_uses_openrouter_fallback_from_order(monkeypatch):
    monkeypatch.setattr(
        evaluation_service.settings,
        "llm_fallback_order",
        "gemini,openrouter,glm",
    )
    monkeypatch.setattr(evaluation_service.settings, "gemini_api_key", "test-gemini")
    monkeypatch.setattr(evaluation_service.settings, "openrouter_api_key", "test-openrouter")
    evaluator = evaluation_service.ScientificEvaluator()

    async def fake_gemini(_prompt: str):
        return {"error": "gemini_503"}

    async def fake_openrouter(_prompt: str):
        return {
            "scores": {
                str(idx): {"score": 4.1, "rationale": f"R{idx}", "origin_snippet": f"S{idx}"}
                for idx in range(1, 10)
            },
            "insight": "OpenRouter fallback produced structured evidence-linked output for this paper.",
        }

    monkeypatch.setattr(evaluator, "_evaluate_with_gemini", fake_gemini)
    monkeypatch.setattr(evaluator, "_evaluate_with_openrouter", fake_openrouter)

    result = await evaluator.evaluate_content("paper text", {"document_profile": {"title": "T"}})
    assert result["_quality_signals"]["llm_provider"] == "openrouter_fallback"
    assert result["scores"]["1"]["score"] == 4.1
    assert result["_quality_signals"]["provider_errors"]["gemini"] == "gemini_503"


@pytest.mark.asyncio
async def test_evaluate_content_uses_qwen_fallback_from_order(monkeypatch):
    monkeypatch.setattr(
        evaluation_service.settings,
        "llm_fallback_order",
        "gemini,qwen,glm",
    )
    monkeypatch.setattr(evaluation_service.settings, "gemini_api_key", "test-gemini")
    monkeypatch.setattr(evaluation_service.settings, "qwen_api_key", "test-qwen")
    evaluator = evaluation_service.ScientificEvaluator()

    async def fake_gemini(_prompt: str):
        return {"error": "gemini_503"}

    async def fake_qwen(_prompt: str):
        return {
            "scores": {
                str(idx): {"score": 4.0, "rationale": f"R{idx}", "origin_snippet": f"S{idx}"}
                for idx in range(1, 10)
            },
            "insight": "Qwen fallback produced structured evidence-linked output for this paper.",
        }

    monkeypatch.setattr(evaluator, "_evaluate_with_gemini", fake_gemini)
    monkeypatch.setattr(evaluator, "_evaluate_with_qwen", fake_qwen)

    result = await evaluator.evaluate_content("paper text", {"document_profile": {"title": "T"}})
    assert result["_quality_signals"]["llm_provider"] == "qwen_fallback"
    assert result["scores"]["1"]["score"] == 4.0
    assert result["_quality_signals"]["provider_errors"]["gemini"] == "gemini_503"


@pytest.mark.asyncio
async def test_evaluate_content_adaptive_routing_prefers_qwen_for_low_complexity(monkeypatch):
    monkeypatch.setattr(evaluation_service.settings, "llm_adaptive_routing_enabled", True)
    monkeypatch.setattr(
        evaluation_service.settings,
        "llm_fallback_order",
        "gemini,glm,openrouter,qwen",
    )
    evaluator = evaluation_service.ScientificEvaluator()
    call_order: list[str] = []

    async def fake_fail(name: str):
        async def _inner(_prompt: str):
            call_order.append(name)
            return {"error": f"{name}_failed"}
        return _inner

    async def fake_qwen(_prompt: str):
        call_order.append("qwen")
        return {
            "scores": {
                str(idx): {"score": 3.9, "rationale": f"R{idx}", "origin_snippet": f"S{idx}"}
                for idx in range(1, 10)
            },
            "insight": "Low complexity routing selected qwen first.",
        }

    monkeypatch.setattr(evaluator, "_evaluate_with_gemini", await fake_fail("gemini"))
    monkeypatch.setattr(evaluator, "_evaluate_with_glm", await fake_fail("glm"))
    monkeypatch.setattr(evaluator, "_evaluate_with_openrouter", await fake_fail("openrouter"))
    monkeypatch.setattr(evaluator, "_evaluate_with_qwen", fake_qwen)

    result = await evaluator.evaluate_content(
        "Short abstract about a catalyst.",
        {
            "document_profile": {"title": "T"},
            "source_errors": {"openalex": "timeout"},
        },
    )
    assert call_order == ["qwen"]
    assert result["_quality_signals"]["llm_provider"] == "qwen"
    routing = result["_quality_signals"]["provider_routing"]
    assert routing["complexity_band"] == "low"
    assert routing["effective_order"][0] == "qwen"
