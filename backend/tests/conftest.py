"""Test fixtures and shared configuration."""

import pytest


@pytest.fixture
def sample_doi():
    return "10.1038/s41586-020-2649-2"


@pytest.fixture
def retracted_doi():
    return "10.1234/retracted-paper-example"
