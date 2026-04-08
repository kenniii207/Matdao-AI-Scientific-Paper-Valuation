"""Pydantic v2 models for the 9-dimension scoring system."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


GRADE_LABELS = {
    Grade.A: "Highly Recommended (Alpha Tier)",
    Grade.B: "Recommended (Beta Tier)",
    Grade.C: "Neutral (Gamma Tier)",
    Grade.D: "Not Recommended (Delta Tier)",
    Grade.F: "Rejected (Omega Tier)",
}

DIMENSION_NAMES = {
    1: "Return on Research Investment (RORI)",
    2: "Scientific Quality & Rigor",
    3: "Market Size & Scalability",
    4: "Competitive Moat & IP Defensibility",
    5: "Team Quality & Track Record",
    6: "Societal Impact & ESG Alignment",
    7: "Research Pipeline & Portfolio Risk",
    8: "Risk & Uncertainty Profile",
    9: "Governance & Transparency",
}

# MVP: equal weights (1/9 each)
DEFAULT_WEIGHTS = {i: 1.0 / 9.0 for i in range(1, 10)}


class DimensionScore(BaseModel):
    """Score for a single dimension."""

    dimension_id: int = Field(ge=1, le=9)
    dimension_name: str = ""
    raw_score: float = Field(ge=1.0, le=5.0, description="Raw score 1-5")
    weight: float = Field(description="Dimension weight (sum to 1.0)")
    origin_snippet: Optional[str] = Field(
        default=None,
        description="API JSON or PDF text fragment that produced this score",
    )
    automated: bool = Field(
        default=False, description="True if score was computed automatically"
    )

    @computed_field
    @property
    def weighted_contribution(self) -> float:
        """This dimension's contribution to the total score."""
        return (self.raw_score * self.weight / 5.0) * 100.0


class ScoringResult(BaseModel):
    """Complete scoring output for a paper."""

    doi: str
    dimensions: list[DimensionScore] = Field(default_factory=list)
    integrity_gate_triggered: bool = Field(
        default=False,
        description="True if Dimension 9 = 1 → total forced to 0",
    )

    @computed_field
    @property
    def total_score(self) -> float:
        if self.integrity_gate_triggered:
            return 0.0
        return round(sum(d.weighted_contribution for d in self.dimensions), 6)

    @computed_field
    @property
    def grade(self) -> Grade:
        score = self.total_score
        if score >= 90:
            return Grade.A
        if score >= 80:
            return Grade.B
        if score >= 70:
            return Grade.C
        if score >= 60:
            return Grade.D
        return Grade.F

    @computed_field
    @property
    def investment_status(self) -> str:
        return GRADE_LABELS[self.grade]
