"""Tests for CrossrefAdapter retraction signal parsing."""

from backend.api.adapters.crossref_adapter import CrossrefAdapter


def test_detects_retraction_from_update_to():
    message = {"update-to": [{"type": "retraction"}]}
    assert CrossrefAdapter._is_retracted(message) is True


def test_detects_retraction_from_relation():
    message = {"relation": {"is-retracted-by": [{"id": "10.1234/retract"}]}}
    assert CrossrefAdapter._is_retracted(message) is True


def test_non_retracted_when_no_signal_present():
    message = {"title": ["Clean paper"]}
    assert CrossrefAdapter._is_retracted(message) is False
