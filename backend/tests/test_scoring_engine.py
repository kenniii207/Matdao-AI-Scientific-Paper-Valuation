"""Tests for the Weighted Scoring Engine and Integrity Gate.

Key invariant: A retracted paper (Dimension 9 = 1) MUST always score 0.
"""

from backend.services.scoring.engine import compute_score
from backend.models.scoring import DEFAULT_WEIGHTS, Grade


class TestScoringEngine:
    """Scoring engine determinism and correctness."""

    def test_perfect_scores_yield_100(self):
        """All dimensions at max (5) should give total = 100."""
        raw = {i: 5.0 for i in range(1, 10)}
        result = compute_score("10.1234/test", raw)
        assert abs(result.total_score - 100.0) < 0.01
        assert result.grade == Grade.A

    def test_minimum_scores_trigger_integrity_gate(self):
        """All dims at 1 → Dim9=1 triggers Integrity Gate → total = 0."""
        raw = {i: 1.0 for i in range(1, 10)}
        result = compute_score("10.1234/test", raw)
        assert result.integrity_gate_triggered is True
        assert result.total_score == 0.0
        assert result.grade == Grade.F

    def test_minimum_scores_without_gate(self):
        """All dims at 1 except Dim9=2 (no gate) → total = ~22.2."""
        raw = {i: 1.0 for i in range(1, 10)}
        raw[9] = 2.0  # avoid gate
        result = compute_score("10.1234/test", raw)
        assert result.integrity_gate_triggered is False
        assert result.total_score > 0
        assert result.grade == Grade.F

    def test_neutral_scores_yield_60(self):
        """All dimensions at 3 should give total = 60. Dim9=3 won't trigger gate."""
        raw = {i: 3.0 for i in range(1, 10)}
        result = compute_score("10.1234/test", raw)
        assert result.integrity_gate_triggered is False
        assert abs(result.total_score - 60.0) < 0.01
        assert result.grade == Grade.D

    def test_grade_boundaries(self):
        """Verify grade mapping at boundaries."""
        # Score = 90 → A
        # With equal weights: score_i such that total = 90
        # 90 = Σ(s * (1/9) / 5 * 100) = Σ(s * 100/45) = 9 * s * 100/45
        # 90 = s * 100/5 * 1 = 20s → s = 4.5
        raw = {i: 4.5 for i in range(1, 10)}
        result = compute_score("10.1234/test", raw)
        assert result.grade == Grade.A

    def test_equal_weights_sum_to_one(self):
        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 0.001

    def test_dimensions_count(self):
        raw = {i: 3.0 for i in range(1, 10)}
        result = compute_score("10.1234/test", raw)
        assert len(result.dimensions) == 9

    def test_origin_snippets_preserved(self):
        raw = {i: 3.0 for i in range(1, 10)}
        snippets = {2: '{"influentialCitationCount": 42}'}
        result = compute_score("10.1234/test", raw, origin_snippets=snippets)
        dim2 = [d for d in result.dimensions if d.dimension_id == 2][0]
        assert "42" in dim2.origin_snippet


class TestIntegrityGate:
    """Dimension 9 binary multiplier — THE most critical test suite."""

    def test_retraction_forces_zero(self):
        """If Dimension 9 = 1, total MUST be 0 regardless of other scores."""
        raw = {i: 5.0 for i in range(1, 10)}  # all perfect
        raw[9] = 1.0  # except governance = critical failure
        result = compute_score("10.1234/retracted", raw)

        assert result.integrity_gate_triggered is True
        assert result.total_score == 0.0
        assert result.grade == Grade.F

    def test_retraction_with_mixed_scores(self):
        """Integrity gate overrides even with high scores elsewhere."""
        raw = {1: 5, 2: 5, 3: 5, 4: 5, 5: 5, 6: 5, 7: 5, 8: 5, 9: 1}
        result = compute_score("10.1234/retracted-mixed", raw)
        assert result.total_score == 0.0
        assert result.integrity_gate_triggered is True

    def test_no_retraction_normal_scoring(self):
        """Without retraction, Dimension 9 contributes normally."""
        raw = {i: 4.0 for i in range(1, 10)}
        raw[9] = 4.0  # good governance
        result = compute_score("10.1234/clean", raw)
        assert result.integrity_gate_triggered is False
        assert result.total_score > 0

    def test_dim9_score_of_2_does_not_trigger_gate(self):
        """Only score = 1 triggers the gate, not 2."""
        raw = {i: 3.0 for i in range(1, 10)}
        raw[9] = 2.0
        result = compute_score("10.1234/low-gov", raw)
        assert result.integrity_gate_triggered is False
        assert result.total_score > 0

    def test_dim9_exactly_1_triggers(self):
        """Score of exactly 1.0 triggers the gate."""
        raw = {i: 4.0 for i in range(1, 10)}
        raw[9] = 1.0
        result = compute_score("10.1234/exact-1", raw)
        assert result.integrity_gate_triggered is True
        assert result.total_score == 0.0
