"""Dimension 9: Governance & Transparency — automated scoring logic.

Acts as BINARY GATE: governance red flag found → score = 1 → total = 0.

Factors:
1. Governance Red Flag (binary gate)
2. Funding Audit (NIH RePORTER verification)
3. Author Credentials (h-index from OpenAlex/Semantic Scholar)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from backend.models.api_responses import NIHGrant

logger = logging.getLogger(__name__)


def score_dimension9(
    governance_red_flag: bool = False,
    governance_evidence: Optional[list[dict]] = None,
    nih_grants: Optional[list[NIHGrant]] = None,
    author_h_indices: Optional[list[int]] = None,
) -> tuple[float, str, bool]:
    """Compute Dimension 9 raw score (1-5).

    Returns:
        (raw_score, origin_snippet, is_red_flag_found)

    If governance red flag is found, raw_score = 1.0 and is_red_flag_found = True.
    The scoring engine will then force total to 0 via Integrity Gate.
    """
    snippets = {}

    # 1. GOVERNANCE RED FLAG — BINARY GATE
    if governance_red_flag:
        logger.critical(
            "GOVERNANCE RED FLAG DETECTED — Integrity Gate will force total to 0"
        )
        snippets["is_red_flag"] = True
        snippets["evidence"] = (governance_evidence or [])[:3]  # truncate
        return 1.0, json.dumps(snippets, default=str), True

    snippets["is_red_flag"] = False
    sub_scores = [4.0]  # no retraction = base 4

    # 2. Funding Audit
    if nih_grants is not None:
        if len(nih_grants) > 0:
            sub_scores.append(5.0)
            snippets["nih_grants_found"] = len(nih_grants)
        else:
            sub_scores.append(3.0)
            snippets["nih_grants_found"] = 0

    # 3. Author Credentials (average h-index)
    if author_h_indices:
        avg_h = sum(author_h_indices) / len(author_h_indices)
        if avg_h >= 40:
            sub_scores.append(5.0)
        elif avg_h >= 20:
            sub_scores.append(4.0)
        elif avg_h >= 10:
            sub_scores.append(3.0)
        else:
            sub_scores.append(2.0)
        snippets["avg_h_index"] = round(avg_h, 1)

    raw_score = sum(sub_scores) / len(sub_scores)
    raw_score = max(1.0, min(5.0, raw_score))

    return raw_score, json.dumps(snippets, default=str), False
