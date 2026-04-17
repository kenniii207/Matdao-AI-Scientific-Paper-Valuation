"""Weighted Scoring Engine with Integrity Gate.

Formula: Total = Σ(Score_i × Weight_i / 5 × 100) where Σ Weight_i = 1.0
Integrity Gate: If Dimension 9 score = 1 → Total = 0
"""

from __future__ import annotations

import logging

from backend.models.scoring import (
    DEFAULT_WEIGHTS,
    DIMENSION_NAMES,
    DimensionScore,
    ScoringResult,
)

logger = logging.getLogger(__name__)


def compute_score(
    doi: str,
    raw_scores: dict[int, float],
    origin_snippets: dict[int, str] | None = None,
    weights: dict[int, float] | None = None,
    automated_flags: dict[int, bool] | None = None,
    confidence_tier: str = "AUTOMATED_60",
) -> ScoringResult:
    """Compute the weighted total score with Integrity Gate enforcement.

    Args:
        doi: Paper DOI.
        raw_scores: {dimension_id: score} where score is 1.0-5.0.
        origin_snippets: {dimension_id: snippet_json} for auditability.
        weights: Custom weights. Defaults to equal (1/9).
        automated_flags: {dimension_id: bool} marking automated scores.

    Returns:
        ScoringResult with total, grade, and integrity gate status.
    """
    weights = weights or DEFAULT_WEIGHTS
    origin_snippets = origin_snippets or {}
    automated_flags = automated_flags or {}

    # Validate weights sum to ~1.0
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 0.01:
        logger.warning("Weights sum to %.4f, expected 1.0. Normalizing.", weight_sum)
        weights = {k: v / weight_sum for k, v in weights.items()}

    # Check Integrity Gate FIRST
    dim9_score = raw_scores.get(9, 3.0)
    integrity_gate_triggered = dim9_score <= 1.0

    if integrity_gate_triggered:
        logger.warning(
            "INTEGRITY GATE TRIGGERED for %s — Dimension 9 score = %.1f. Total forced to 0.",
            doi,
            dim9_score,
        )

    # Build dimension scores
    dimensions = []
    for dim_id in range(1, 10):
        score = raw_scores.get(dim_id, 3.0)  # default neutral
        dimensions.append(
            DimensionScore(
                dimension_id=dim_id,
                dimension_name=DIMENSION_NAMES.get(dim_id, f"Dimension {dim_id}"),
                raw_score=max(1.0, min(5.0, score)),  # clamp 1-5
                weight=weights.get(dim_id, 1.0 / 9.0),
                origin_snippet=origin_snippets.get(dim_id),
                automated=automated_flags.get(dim_id, False),
            )
        )

    return ScoringResult(
        doi=doi,
        dimensions=dimensions,
        integrity_gate_triggered=integrity_gate_triggered,
        confidence_tier=confidence_tier,
    )
