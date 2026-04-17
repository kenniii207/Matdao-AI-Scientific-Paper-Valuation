"""Tests for scoring response helper formatting."""

from backend.api.routes import scoring


def _sample_dimensions() -> list[dict]:
    return [
        {"dimension_id": index, "raw_score": 3.5}
        for index in range(1, 10)
    ]


def test_derive_executive_summary_is_not_identical_to_insight():
    insight = "Scientific signal present, but translation and execution evidence are still emerging."
    summary = scoring._derive_executive_summary(
        eval_results={"executive_summary": insight},
        insight=insight,
        dimensions=_sample_dimensions(),
        integrity_gate_triggered=False,
        total_score=71.2,
        grade="C",
    )

    assert summary != insight
    assert "Overall score" in summary


def test_derive_executive_summary_prefers_distinct_model_summary():
    summary = scoring._derive_executive_summary(
        eval_results={"executive_summary": "This is a distinct executive summary."},
        insight="Different insight sentence.",
        dimensions=_sample_dimensions(),
        integrity_gate_triggered=False,
        total_score=80.0,
        grade="B",
    )

    assert summary == "This is a distinct executive summary."


def test_derive_confidence_tier_marks_insufficient_evidence_as_low():
    confidence = scoring._derive_confidence_tier(
        scored_by="llm-eval-v1",
        eval_results={"_quality_signals": {"insufficient_evidence": True, "llm_provider": "gemini"}},
    )
    assert confidence == "LOW (INSUFFICIENT_EVIDENCE)"


def test_derive_confidence_tier_uses_llm_high_when_quality_clean():
    confidence = scoring._derive_confidence_tier(
        scored_by="llm-eval-v1",
        eval_results={"_quality_signals": {"llm_provider": "glm"}},
    )
    assert confidence == "HIGH (LLM_ENRICHED)"
