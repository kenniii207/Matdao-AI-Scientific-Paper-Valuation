"""Grobid adapter — Layer 1 Neural Extraction for scientific PDF parsing.

Communicates with local Grobid Docker container on port 8070.
Extracts: DOIs, ORCIDs, authors, funding statements, bibliography.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from core.config import settings
from core.exceptions import AdapterError

logger = logging.getLogger(__name__)


class GrobidAdapter:
    """Sends PDFs to local Grobid service for structured extraction (TEI XML → JSON)."""

    def __init__(self):
        self.base_url = settings.grobid_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, timeout=120.0
            )
        return self._client

    async def parse_pdf(self, pdf_bytes: bytes, filename: str = "paper.pdf") -> dict[str, Any]:
        """Send PDF to Grobid /api/processFulltextDocument and return parsed result."""
        client = await self._get_client()
        try:
            response = await client.post(
                "/api/processFulltextDocument",
                files={"input": (filename, pdf_bytes, "application/pdf")},
                data={"consolidateHeader": "1", "consolidateCitations": "1"},
            )
            response.raise_for_status()
            return {
                "tei_xml": response.text,
                "status": "success",
            }
        except httpx.HTTPStatusError as exc:
            raise AdapterError(
                f"Grobid: HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise AdapterError(f"Grobid: connection failed — {exc}") from exc

    async def parse_header(self, pdf_bytes: bytes) -> dict[str, Any]:
        """Extract only header metadata (faster than full processing)."""
        client = await self._get_client()
        try:
            response = await client.post(
                "/api/processHeaderDocument",
                files={"input": ("paper.pdf", pdf_bytes, "application/pdf")},
                data={"consolidateHeader": "1"},
            )
            response.raise_for_status()
            return {"tei_xml": response.text, "status": "success"}
        except httpx.HTTPStatusError as exc:
            raise AdapterError(
                f"Grobid header: HTTP {exc.response.status_code}"
            ) from exc

    async def health_check(self) -> bool:
        """Check if Grobid is alive."""
        try:
            client = await self._get_client()
            response = await client.get("/api/isalive")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
