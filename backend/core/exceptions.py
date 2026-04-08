"""Centralized exception hierarchy for the MatDAO framework."""


class MatDAOBaseError(Exception):
    """Base for all domain errors. Carries HTTP status and error type."""

    status_code: int = 500
    error_type: str = "internal_error"

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message)


class AdapterError(MatDAOBaseError):
    """Raised when an external API adapter fails."""

    status_code = 502
    error_type = "adapter_error"


class RateLimitExceeded(MatDAOBaseError):
    """Raised when upstream API rate limit is hit after retries exhaust."""

    status_code = 429
    error_type = "rate_limit_exceeded"


class RetractionFoundError(MatDAOBaseError):
    """Raised when a retraction is detected — triggers Integrity Gate."""

    status_code = 200  # not an HTTP error, just a signal
    error_type = "retraction_found"


class ScoringError(MatDAOBaseError):
    """Raised when scoring computation fails."""

    status_code = 422
    error_type = "scoring_error"


class PaperNotFoundError(MatDAOBaseError):
    """Raised when a paper cannot be found by DOI."""

    status_code = 404
    error_type = "paper_not_found"
