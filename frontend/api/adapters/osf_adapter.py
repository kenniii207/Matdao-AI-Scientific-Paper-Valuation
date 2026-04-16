"""OSF adapter — pre-registration status check for Scientific Quality scoring."""

from __future__ import annotations

from typing import Any

from adapters.base_adapter import BaseAdapter
from core.config import settings
from models.api_responses import OSFRegistration


class OSFAdapter(BaseAdapter):
    """Queries api.osf.io for pre-registration records."""

    def __init__(self):
        super().__init__(
            base_url=settings.osf_base_url,
            rate_limit=settings.osf_rate_limit,
        )

    async def fetch(self, title: str) -> dict[str, Any]:
        """Search registrations by title."""
        path = "/registrations/"
        params = {"filter[title]": title}
        return await self._request("GET", path, params=params)

    async def check_preregistration(self, title: str) -> list[OSFRegistration]:
        """Check if a study title matches any pre-registered study."""
        data = await self.fetch(title)
        registrations = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            registrations.append(
                OSFRegistration(
                    registration_id=item.get("id"),
                    title=attrs.get("title"),
                    is_preregistration=True,
                    date_registered=attrs.get("date_registered"),
                    raw_json=item,
                )
            )
        return registrations
