"""Dimension 2: Scientific Quality — automated scoring logic.

Factors:
1. Citation Velocity (influentialCitationCount from Semantic Scholar)
2. Venue Rank (relevance_score from OpenAlex)
3. Pre-registration status (OSF / ClinicalTrials.gov)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from backend.models.api_responses import (
    OpenAlexWork,
    SemanticScholarPaper,
    SerpApiScholarPaper,
    OSFRegistration,
)

logger = logging.getLogger(__name__)


def _score_citation_count(count: int, *, high: int, medium: int, low: int, minimal: int) -> float:
    if count >= high:
        return 5.0
    if count >= medium:
        return 4.0
    if count >= low:
        return 3.0
    if count >= minimal:
        return 2.0
    return 1.5


def score_dimension2(
    s2_paper: Optional[SemanticScholarPaper] = None,
    oa_work: Optional[OpenAlexWork] = None,
    serpapi_paper: Optional[SerpApiScholarPaper] = None,
    preregistrations: Optional[list[OSFRegistration]] = None,
) -> tuple[float, str]:
    """Compute Dimension 2 raw score (1-5) from API data.

    Returns:
        (raw_score, origin_snippet)
    """
    sub_scores = []
    snippets = {}

    # 1. Citation Velocity
    if s2_paper and s2_paper.influential_citation_count is not None:
        icc = s2_paper.influential_citation_count
        sub_scores.append(
            _score_citation_count(icc, high=50, medium=20, low=5, minimal=1)
        )
        snippets["influentialCitationCount"] = icc

    # 2. Venue Rank
    if oa_work and oa_work.cited_by_count is not None:
        cbc = oa_work.cited_by_count
        sub_scores.append(
            _score_citation_count(cbc, high=500, medium=100, low=20, minimal=5)
        )
        snippets["cited_by_count"] = cbc

    if serpapi_paper and serpapi_paper.cited_by_count is not None:
        serp_citations = serpapi_paper.cited_by_count
        sub_scores.append(
            _score_citation_count(serp_citations, high=500, medium=100, low=20, minimal=5)
        )
        snippets["google_scholar_cited_by_count"] = serp_citations

    # 3. Pre-registration
    if preregistrations is not None:
        if len(preregistrations) > 0:
            sub_scores.append(5.0)
            snippets["preregistered"] = True
        else:
            sub_scores.append(2.0)
            snippets["preregistered"] = False

    if not sub_scores:
        return 3.0, json.dumps({"note": "no data available for Dimension 2"})

    raw_score = sum(sub_scores) / len(sub_scores)
    raw_score = max(1.0, min(5.0, raw_score))

    return raw_score, json.dumps(snippets, default=str)
