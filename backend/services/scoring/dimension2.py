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
        if icc >= 50:
            sub_scores.append(5.0)
        elif icc >= 20:
            sub_scores.append(4.0)
        elif icc >= 5:
            sub_scores.append(3.0)
        elif icc >= 1:
            sub_scores.append(2.0)
        else:
            sub_scores.append(1.5)
        snippets["influentialCitationCount"] = icc

    # 2. Venue Rank
    if oa_work and oa_work.cited_by_count is not None:
        cbc = oa_work.cited_by_count
        if cbc >= 500:
            sub_scores.append(5.0)
        elif cbc >= 100:
            sub_scores.append(4.0)
        elif cbc >= 20:
            sub_scores.append(3.0)
        elif cbc >= 5:
            sub_scores.append(2.0)
        else:
            sub_scores.append(1.5)
        snippets["cited_by_count"] = cbc

    if serpapi_paper and serpapi_paper.cited_by_count is not None:
        serp_citations = serpapi_paper.cited_by_count
        if serp_citations >= 500:
            sub_scores.append(5.0)
        elif serp_citations >= 100:
            sub_scores.append(4.0)
        elif serp_citations >= 20:
            sub_scores.append(3.0)
        elif serp_citations >= 5:
            sub_scores.append(2.0)
        else:
            sub_scores.append(1.5)
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
