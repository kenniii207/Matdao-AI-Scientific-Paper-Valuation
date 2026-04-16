"""Tests for evaluation quality signal helpers."""

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
