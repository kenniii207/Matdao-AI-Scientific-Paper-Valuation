"""Tests for Dimension 9 Integrity Gate via governance red-flag detection."""

import pytest

from backend.services.scoring.dimension9 import score_dimension9
from backend.models.api_responses import NIHGrant


class TestDimension9Scoring:
    """Dimension 9 scoring with governance red-flag detection."""

    def test_red_flag_detected_returns_score_1(self):
        """A governance red-flag must score 1.0 on Dimension 9."""
        score, snippet, is_retracted = score_dimension9(
            governance_red_flag=True,
            governance_evidence=[{"type": "retraction", "label": "Retraction"}],
        )
        assert score == 1.0
        assert is_retracted is True
        assert "is_red_flag" in snippet

    def test_clean_paper_scores_above_1(self):
        """A non-retracted paper should score above 1."""
        score, snippet, is_retracted = score_dimension9(governance_red_flag=False)
        assert score > 1.0
        assert is_retracted is False

    def test_with_nih_grants_boosts_score(self):
        """NIH grant verification increases governance score."""
        grants = [
            NIHGrant(project_num="R01-AI12345", project_title="Test Grant")
        ]
        score, snippet, is_retracted = score_dimension9(
            governance_red_flag=False, nih_grants=grants
        )
        assert score >= 4.0
        assert is_retracted is False

    def test_high_h_index_boosts_score(self):
        """High author h-index improves governance score."""
        score, _, _ = score_dimension9(
            governance_red_flag=False, author_h_indices=[45, 50, 38]
        )
        assert score >= 4.0

    def test_no_data_returns_neutral(self):
        """No API data returns neutral-ish score."""
        score, _, is_retracted = score_dimension9()
        assert 2.0 <= score <= 5.0
        assert is_retracted is False
