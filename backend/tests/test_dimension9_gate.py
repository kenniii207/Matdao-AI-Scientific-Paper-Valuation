"""Tests for Dimension 9 Integrity Gate via Crossref retraction detection."""

import pytest

from backend.services.scoring.dimension9 import score_dimension9
from backend.models.api_responses import CrossrefWork, NIHGrant


class TestDimension9Scoring:
    """Dimension 9 scoring with retraction detection."""

    def test_retraction_detected_returns_score_1(self):
        """A retracted paper must score 1.0 on Dimension 9."""
        crossref = CrossrefWork(
            doi="10.1234/retracted",
            is_retracted=True,
            update_to=[{"type": "retraction", "label": "Retraction"}],
        )
        score, snippet, is_retracted = score_dimension9(crossref_work=crossref)
        assert score == 1.0
        assert is_retracted is True
        assert "is_retracted" in snippet

    def test_clean_paper_scores_above_1(self):
        """A non-retracted paper should score above 1."""
        crossref = CrossrefWork(doi="10.1234/clean", is_retracted=False)
        score, snippet, is_retracted = score_dimension9(crossref_work=crossref)
        assert score > 1.0
        assert is_retracted is False

    def test_with_nih_grants_boosts_score(self):
        """NIH grant verification increases governance score."""
        crossref = CrossrefWork(doi="10.1234/funded", is_retracted=False)
        grants = [
            NIHGrant(project_num="R01-AI12345", project_title="Test Grant")
        ]
        score, snippet, is_retracted = score_dimension9(
            crossref_work=crossref, nih_grants=grants
        )
        assert score >= 4.0
        assert is_retracted is False

    def test_high_h_index_boosts_score(self):
        """High author h-index improves governance score."""
        crossref = CrossrefWork(doi="10.1234/expert", is_retracted=False)
        score, _, _ = score_dimension9(
            crossref_work=crossref, author_h_indices=[45, 50, 38]
        )
        assert score >= 4.0

    def test_no_data_returns_neutral(self):
        """No API data returns neutral-ish score."""
        score, _, is_retracted = score_dimension9()
        assert 2.0 <= score <= 5.0
        assert is_retracted is False
