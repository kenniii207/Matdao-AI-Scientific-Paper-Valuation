"""Tests for low-confidence review queue assessment."""

from backend.api.routes.upload import _assess_low_confidence


def test_assess_low_confidence_flags_review_when_quality_is_poor():
    eval_results = {
        "error": "timeout",
        "_quality_signals": {
            "insufficient_evidence": True,
            "schema_repair_count": 8,
            "snippet_coverage_ratio": 0.22,
            "generic_output_detected": True,
        },
    }
    enriched_data = {"source_errors": {"openalex": "timeout", "semantic_scholar": "timeout"}}
    raw_scores = {1: 3.0, 2: 3.0}

    assessment = _assess_low_confidence(eval_results, enriched_data, raw_scores)

    assert assessment["needs_review"] is True
    assert assessment["confidence_score"] < 0.7
    assert "insufficient_evidence" in assessment["reasons"]
    assert "multiple_source_errors" in assessment["reasons"]


def test_assess_low_confidence_skips_queue_when_signals_are_clean():
    eval_results = {
        "_quality_signals": {
            "schema_repair_count": 0,
            "snippet_coverage_ratio": 1.0,
            "generic_output_detected": False,
            "insufficient_evidence": False,
        }
    }
    enriched_data = {"source_errors": {}}
    raw_scores = {index: 4.0 for index in range(1, 10)}

    assessment = _assess_low_confidence(eval_results, enriched_data, raw_scores)

    assert assessment["needs_review"] is False
    assert assessment["confidence_score"] == 1.0
    assert assessment["reasons"] == []
