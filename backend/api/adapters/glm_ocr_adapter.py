"""GLM-OCR adapter — multimodal OCR for complex document understanding.

Uses GLM-OCR (0.9B model) for tables, formulas, charts, and scientific figures.
Supports cloud MaaS API (Zhipu) or self-hosted vLLM/SGLang deployment.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from backend.core.config import settings
from backend.core.exceptions import AdapterError

logger = logging.getLogger(__name__)


class GLMOCRAdapter:
    """Sends images/PDFs to GLM-OCR for layout-aware OCR."""

    def __init__(
        self,
        api_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        use_maas: bool = True,
    ):
        self.api_url = api_url
        self.use_maas = use_maas
        self.api_key = settings.zai_api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                headers=headers, timeout=120.0
            )
        return self._client

    async def parse_image(self, image_base64: str, prompt: str = "OCR this document.") -> dict[str, Any]:
        """Send base64-encoded image to GLM-OCR for recognition."""
        client = await self._get_client()
        payload = {
            "model": "glm-ocr",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": f"data:image/png;base64,{image_base64}",
                        },
                    ],
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1,
        }

        try:
            response = await client.post(self.api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return {"text": content, "status": "success", "raw_json": result}
        except httpx.HTTPStatusError as exc:
            raise AdapterError(
                f"GLM-OCR: HTTP {exc.response.status_code}"
            ) from exc
        except (KeyError, IndexError) as exc:
            raise AdapterError(
                f"GLM-OCR: unexpected response format — {exc}"
            ) from exc

    async def health_check(self) -> bool:
        """Check if GLM-OCR API is reachable."""
        try:
            client = await self._get_client()
            response = await client.get(self.api_url.rsplit("/", 1)[0])
            return response.status_code < 500
        except Exception:
            return False

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
