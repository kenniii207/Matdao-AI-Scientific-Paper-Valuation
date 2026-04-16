"""Crossref adapter — retraction checks for Dimension 9 Integrity Gate."""

from __future__ import annotations

from typing import Any

from backend.api.adapters.base_adapter import BaseAdapter
from backend.core.config import settings
from backend.models.api_responses import CrossrefWork


class CrossrefAdapter(BaseAdapter):
    """Queries Crossref /works and detects retraction signals."""

    def __init__(self):
        super().__init__(
            base_url=settings.crossref_base_url,
            rate_limit=settings.crossref_rate_limit,
            headers={"User-Agent": f"MatDAO/0.1 (mailto:{settings.crossref_email})"},
        )

    async def fetch(self, doi: str) -> dict[str, Any]:
        """Fetch Crossref work payload for DOI."""
        return await self._request("GET", f"/works/{doi}")

    @staticmethod
    def _extract_message(payload: dict[str, Any]) -> dict[str, Any]:
        return payload.get("message", payload)

    @staticmethod
    def _is_retracted(message: dict[str, Any]) -> bool:
        relation = message.get("relation") or {}
        if relation.get("is-retracted-by"):
            return True

        updates = message.get("update-to") or []
        for update in updates:
            update_type = str(update.get("type", "")).lower()
            if "retract" in update_type:
                return True
        return False

    async def check_retraction(self, doi: str) -> CrossrefWork:
        """Return normalized retraction signal used by Dimension 9."""
        if doi.startswith("10.matdao/"):
            return CrossrefWork(doi=doi, title=None, is_retracted=False, update_to=[])

        payload = await self.fetch(doi)
        message = self._extract_message(payload)
        titles = message.get("title") or []
        title = titles[0] if titles else None
        return CrossrefWork(
            doi=message.get("DOI") or doi,
            title=title,
            is_retracted=self._is_retracted(message),
            update_to=message.get("update-to") or [],
            raw_json=message,
        )
