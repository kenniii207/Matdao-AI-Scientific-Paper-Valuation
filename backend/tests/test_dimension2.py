"""Tests for Dimension 2 Scientific Quality scoring."""

import pytest

from backend.services.scoring.dimension2 import score_dimension2
from backend.models.api_responses import (
    SemanticScholarPaper,
    OpenAlexWork,
    SerpApiScholarPaper,
    OSFRegistration,
)


class TestDimension2Scoring:

    def test_high_citations_high_score(self):
        s2 = SemanticScholarPaper(influential_citation_count=60)
        oa = OpenAlexWork(cited_by_count=600)
        score, snippet = score_dimension2(s2_paper=s2, oa_work=oa)
        assert score == 5.0

    def test_low_citations_low_score(self):
        s2 = SemanticScholarPaper(influential_citation_count=0)
        oa = OpenAlexWork(cited_by_count=2)
        score, _ = score_dimension2(s2_paper=s2, oa_work=oa)
        assert score <= 2.0

    def test_preregistration_boosts_score(self):
        s2 = SemanticScholarPaper(influential_citation_count=10)
        preregs = [OSFRegistration(registration_id="abc", is_preregistration=True)]
        score_with, _ = score_dimension2(s2_paper=s2, preregistrations=preregs)
        score_without, _ = score_dimension2(s2_paper=s2, preregistrations=[])
        assert score_with > score_without

    def test_no_data_returns_neutral(self):
        score, snippet = score_dimension2()
        assert score == 3.0

    def test_serpapi_citations_are_included(self):
        serp = SerpApiScholarPaper(cited_by_count=120)
        score, snippet = score_dimension2(serpapi_paper=serp)
        assert score == 4.0
        assert "google_scholar_cited_by_count" in snippet
