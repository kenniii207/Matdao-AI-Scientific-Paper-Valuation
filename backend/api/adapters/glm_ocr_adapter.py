"""GLM-OCR adapter — multimodal OCR for complex document understanding.

Uses GLM-OCR (0.9B model) for tables, formulas, charts, and scientific figures.
Supports cloud MaaS API (Zhipu) or self-hosted vLLM/SGLang deployment.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict

import httpx

from backend.api.adapters.base_adapter import JSONObject
from backend.core.config import settings
from backend.core.exceptions import AdapterError

logger = logging.getLogger(__name__)


class GLMOCRParseResult(TypedDict):
    text: str
    status: str
    model_id: str
    error_chain: list[str]
    raw_json: JSONObject


class GLMOCRAdapter:
    """Sends images/PDFs to GLM-OCR for layout-aware OCR."""

    def __init__(
        self,
        layout_endpoint: Optional[str] = None,
        chat_endpoint: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        use_maas: bool = True,
        timeout_seconds: Optional[int] = None,
    ):
        self.layout_endpoint = self._resolve_endpoint(
            layout_endpoint or settings.glm_ocr_layout_endpoint
        )
        self.chat_endpoint = self._resolve_endpoint(chat_endpoint)
        self.use_maas = use_maas
        self.api_key = settings.zai_api_key
        self.ocr_model = (settings.glm_ocr_model or "glm-ocr").strip()
        self.vision_model = (settings.glm_vision_model or "glm-4.6v-flash").strip()
        self.timeout_seconds = max(5, int(timeout_seconds or settings.glm_ocr_timeout_seconds))
        self._client: Optional[httpx.AsyncClient] = None

    @staticmethod
    def _resolve_endpoint(value: str) -> str:
        clean = (value or "").strip()
        if not clean:
            return ""
        if clean.startswith("http://") or clean.startswith("https://"):
            return clean
        if not clean.startswith("/"):
            clean = f"/{clean}"
        return f"https://open.bigmodel.cn{clean}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            timeout = httpx.Timeout(
                connect=min(10.0, float(self.timeout_seconds)),
                read=float(self.timeout_seconds),
                write=float(self.timeout_seconds),
                pool=5.0,
            )
            limits = httpx.Limits(
                max_connections=8,
                max_keepalive_connections=4,
                keepalive_expiry=20.0,
            )
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                limits=limits,
            )
        return self._client

    @staticmethod
    def _safe_error_message(exc: Exception, max_len: int = 220) -> str:
        text = str(exc).replace("\n", " ").strip()
        if not text:
            text = exc.__class__.__name__
        return text[:max_len]

    @staticmethod
    def _extract_layout_text(payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""
        direct_keys = ("text", "markdown", "content", "result")
        for key in direct_keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        data_obj = payload.get("data")
        if isinstance(data_obj, dict):
            for key in direct_keys:
                value = data_obj.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        if isinstance(data_obj, list):
            parts: list[str] = []
            for item in data_obj:
                if isinstance(item, dict):
                    for key in direct_keys:
                        value = item.get(key)
                        if isinstance(value, str) and value.strip():
                            parts.append(value.strip())
                            break
            if parts:
                return "\n".join(parts).strip()
        return ""

    @staticmethod
    def _extract_chat_text(payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first, dict) else {}
        content = message.get("content") if isinstance(message, dict) else ""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            chunks = [str(item.get("text") or "").strip() for item in content if isinstance(item, dict)]
            joined = "\n".join(chunk for chunk in chunks if chunk)
            return joined.strip()
        return ""

    async def _parse_with_layout(self, image_base64: str) -> GLMOCRParseResult:
        client = await self._get_client()
        if not self.layout_endpoint or not self.ocr_model:
            raise AdapterError("GLM-OCR layout parsing endpoint/model is not configured")

        payload = {
            "model": self.ocr_model,
            "file": f"data:image/png;base64,{image_base64}",
        }
        response = await client.post(self.layout_endpoint, json=payload)
        response.raise_for_status()
        result = response.json()
        text = self._extract_layout_text(result)
        if not text:
            raise AdapterError("GLM-OCR layout parsing returned empty text")
        return {
            "text": text,
            "status": "success",
            "model_id": self.ocr_model,
            "error_chain": [],
            "raw_json": result,
        }

    async def _parse_with_vision_fallback(
        self,
        image_base64: str,
        prompt: str,
        error_chain: list[str],
    ) -> GLMOCRParseResult:
        client = await self._get_client()
        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1,
        }
        response = await client.post(self.chat_endpoint, json=payload)
        response.raise_for_status()
        result = response.json()
        text = self._extract_chat_text(result)
        if not text:
            raise AdapterError("GLM vision fallback returned empty text")
        return {
            "text": text,
            "status": "success_fallback",
            "model_id": self.vision_model,
            "error_chain": error_chain,
            "raw_json": result,
        }

    async def parse_image(self, image_base64: str, prompt: str = "OCR this document.") -> GLMOCRParseResult:
        """Send base64-encoded image to GLM OCR, then fallback to GLM vision if needed."""
        if not self.api_key:
            raise AdapterError("GLM-OCR: missing ZAI_API_KEY")
        error_chain: list[str] = []

        try:
            return await self._parse_with_layout(image_base64)
        except Exception as exc:
            logger.warning("GLM-OCR layout parsing failed; trying GLM vision fallback: %s", exc)
            error_chain.append(self._safe_error_message(exc))

        try:
            return await self._parse_with_vision_fallback(image_base64, prompt, error_chain)
        except Exception as exc:
            error_chain.append(self._safe_error_message(exc))
            raise AdapterError(
                "GLM OCR failed after layout + vision fallback: "
                + " | ".join(error_chain[-2:])
            ) from exc

    async def health_check(self) -> bool:
        """Check if GLM-OCR API is reachable."""
        try:
            client = await self._get_client()
            target = self.layout_endpoint or self.chat_endpoint
            if not target:
                return False
            response = await client.get(target.rsplit("/", 1)[0])
            return response.status_code < 500
        except Exception:
            return False

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
