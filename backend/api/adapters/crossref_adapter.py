"""Crossref adapter — retraction detection via update-type:retraction.

CRITICAL: This adapter powers the Dimension 9 Integrity Gate.
A positive retraction match forces Total Score → 0.
"""

from __future__ import annotations

from typing import Any

from backend.api.adapters.base_adapter import BaseAdapter
from backend.core.config import settings
from backend.models.api_responses import CrossrefWork


class CrossrefAdapter(BaseAdapter):
    """Queries api.crossref.org for retraction status and work metadata.
    Uses the 'polite pool' via mailto header for better rate limits."""

    def __init__(self):
        super().__init__(
            base_url=settings.crossref_base_url,
            rate_limit=settings.crossref_rate_limit,
            headers={
                "User-Agent": f"MatDAO/0.1 (mailto:{settings.crossref_email})",
            },
        )

    async def fetch(self, doi: str) -> dict[str, Any]:
        """Fetch work metadata from Crossref."""
        path = f"/works/{doi}"
        data = await self._request("GET", path)
        return data.get("message", data)

    async def check_retraction(self, doi: str) -> CrossrefWork:
        """Check if a DOI has been retracted. This is the Integrity Gate check."""
        data = await self.fetch(doi)

        update_to = data.get("update-to", [])
        is_retracted = any(
            u.get("type") == "retraction" or u.get("label") == "Retraction"
            for u in update_to
        )

        # Also check the relation field
        if not is_retracted:
            relation = data.get("relation", {})
            is_retracted = "is-retracted-by" in relation

        return CrossrefWork(
            doi=data.get("DOI"),
            title=data.get("title", [None])[0] if data.get("title") else None,
            is_retracted=is_retracted,
            update_to=update_to,
            raw_json=data,
        )
