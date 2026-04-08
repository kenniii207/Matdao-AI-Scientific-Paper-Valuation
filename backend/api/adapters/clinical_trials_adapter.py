"""ClinicalTrials.gov v2 adapter — trial status check for governance scoring."""

from __future__ import annotations

from typing import Any

from backend.api.adapters.base_adapter import BaseAdapter
from backend.core.config import settings
from backend.models.api_responses import ClinicalTrial


class ClinicalTrialsAdapter(BaseAdapter):
    """Queries clinicaltrials.gov API v2 for study status."""

    def __init__(self):
        super().__init__(
            base_url=settings.clinical_trials_base_url,
            rate_limit=settings.clinical_trials_rate_limit,
        )

    async def fetch(self, query: str) -> dict[str, Any]:
        """Search studies by query term."""
        params = {
            "query.term": query,
            "pageSize": 10,
            "format": "json",
        }
        return await self._request("GET", "/studies", params=params)

    async def check_trials(self, query: str) -> list[ClinicalTrial]:
        """Search and return validated trial records. Flags terminated/suspended."""
        data = await self.fetch(query)
        trials = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            status_module = protocol.get("statusModule", {})
            overall_status = status_module.get("overallStatus", "")

            trials.append(
                ClinicalTrial(
                    nct_id=protocol.get("identificationModule", {}).get("nctId"),
                    brief_title=protocol.get("identificationModule", {}).get("briefTitle"),
                    overall_status=overall_status,
                    has_results=study.get("hasResults", False),
                    is_terminated_or_suspended=overall_status.upper() in (
                        "TERMINATED", "SUSPENDED", "WITHDRAWN"
                    ),
                    raw_json=study,
                )
            )
        return trials
