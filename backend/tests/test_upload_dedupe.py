"""Tests for upload dedupe re-run decision helpers."""

from types import SimpleNamespace

from backend.api.routes.upload import _should_rerun_existing_score


def _score_row(total_score: float = 60.0) -> SimpleNamespace:
    dims = {f"dim{index}_score": 3.0 for index in range(1, 10)}
    return SimpleNamespace(total_score=total_score, scored_by="llm-eval-v1", **dims)


def test_should_rerun_existing_score_for_insufficient_evidence():
    row = _score_row()
    rerun, reasons = _should_rerun_existing_score(
        row,
        {"_quality_signals": {"insufficient_evidence": True}},
    )
    assert rerun is True
    assert "insufficient_evidence" in reasons


def test_should_rerun_existing_score_for_flat_neutral_grid():
    row = _score_row(total_score=60.0)
    rerun, reasons = _should_rerun_existing_score(row, {})
    assert rerun is True
    assert "flat_neutral_score" in reasons


def test_should_not_rerun_when_score_quality_is_good():
    row = SimpleNamespace(
        total_score=82.0,
        scored_by="llm-eval-v1",
        dim1_score=4.0,
        dim2_score=4.2,
        dim3_score=3.8,
        dim4_score=4.0,
        dim5_score=4.1,
        dim6_score=3.7,
        dim7_score=4.0,
        dim8_score=3.6,
        dim9_score=4.2,
    )
    rerun, reasons = _should_rerun_existing_score(
        row,
        {"_quality_signals": {"llm_provider": "gemini"}},
    )
    assert rerun is False
    assert reasons == []
