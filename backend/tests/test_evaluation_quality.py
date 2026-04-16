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
