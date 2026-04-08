"""NIH RePORTER adapter — funding verification and grant history.

Rate limit: strictly 1 req/sec.
"""

from __future__ import annotations

from typing import Any

from backend.api.adapters.base_adapter import BaseAdapter
from backend.core.config import settings
from backend.models.api_responses import NIHGrant


class NIHReporterAdapter(BaseAdapter):
    """Queries api.reporter.nih.gov for grant records and funding verification."""

    def __init__(self):
        super().__init__(
            base_url=settings.nih_reporter_base_url,
            rate_limit=settings.nih_reporter_rate_limit,  # 1 req/sec
        )

    async def fetch(self, identifier: str) -> dict[str, Any]:
        """Search projects by text query (PI name, project number, or keywords)."""
        payload = {
            "criteria": {"advanced_text_search": {"search_text": identifier}},
            "limit": 10,
            "offset": 0,
        }
        return await self._request("POST", "/projects/search", json_body=payload)

    async def search_grants(self, query: str) -> list[NIHGrant]:
        """Search and return validated grant records."""
        data = await self.fetch(query)
        results = data.get("results", [])
        grants = []
        for r in results:
            grants.append(
                NIHGrant(
                    project_num=r.get("project_num"),
                    project_title=r.get("project_title"),
                    pi_name=(r.get("contact_pi_name") or r.get("principal_investigators", [{}])[0].get("full_name")),
                    organization=r.get("organization", {}).get("org_name"),
                    total_cost=r.get("award_amount"),
                    fiscal_year=r.get("fiscal_year"),
                    raw_json=r,
                )
            )
        return grants
