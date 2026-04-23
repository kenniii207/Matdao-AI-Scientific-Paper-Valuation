"""LightOnOCR adapter for external llama-server OCR fallback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, TypedDict

import httpx

from backend.api.adapters.base_adapter import JSONObject
from backend.core.config import settings
from backend.core.exceptions import AdapterError

logger = logging.getLogger(__name__)


class LightOnOCRParseResult(TypedDict):
    text: str
    status: str
    model_id: str
    raw_json: JSONObject


class LightOnOCRAdapter:
    """Calls an external llama-server endpoint for LightOnOCR extraction."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        health_timeout_seconds: Optional[int] = None,
        include_text_prompt: Optional[bool] = None,
    ):
        self.base_url = (base_url or settings.lightonocr_base_url or "").strip().rstrip("/")
        self.timeout_seconds = max(5, int(timeout_seconds or settings.lightonocr_timeout_seconds))
        self.health_timeout_seconds = max(
            1,
            int(health_timeout_seconds or settings.lightonocr_health_timeout_seconds),
        )
        self.include_text_prompt = bool(
            settings.lightonocr_include_text_prompt
            if include_text_prompt is None
            else include_text_prompt
        )
        self._client: Optional[httpx.AsyncClient] = None

    @staticmethod
    def runtime_contract_errors() -> list[str]:
        if not bool(settings.lightonocr_require_local_paths):
            return []
        errors: list[str] = []
        model_path = (settings.lightonocr_model_path or "").strip()
        mmproj_path = (settings.lightonocr_mmproj_path or "").strip()
        if not model_path:
            errors.append("lighton_model_path_missing")
        if not mmproj_path:
            errors.append("lighton_mmproj_path_missing")

        if model_path and not Path(model_path).exists():
            errors.append(f"lighton_model_path_not_found:{model_path}")
        if mmproj_path and not Path(mmproj_path).exists():
            errors.append(f"lighton_mmproj_path_not_found:{mmproj_path}")
        return errors

    def _chat_endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"Content-Type": "application/json"},
                timeout=float(self.timeout_seconds),
            )
        return self._client

    @staticmethod
    def _is_ready_health_payload(payload: Any) -> bool:
        if isinstance(payload, dict):
            status = str(payload.get("status") or "").strip().lower()
            return status in {"ok", "healthy", "ready"}
        if isinstance(payload, str):
            return "ok" in payload.lower()
        return False

    async def health_check(self) -> bool:
        """Probe /health then /v1/health and accept only explicit healthy status."""
        if not self.base_url:
            return False
        client = await self._get_client()
        for path in ("/health", "/v1/health"):
            target = f"{self.base_url}{path}"
            try:
                resp = await client.get(target, timeout=float(self.health_timeout_seconds))
            except Exception:
                continue
            if resp.status_code != 200:
                continue
            try:
                payload = resp.json()
            except Exception:
                payload = resp.text
            if self._is_ready_health_payload(payload):
                return True
        return False

    @staticmethod
    def _extract_content(payload: Any) -> str:
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
            parts = [str(item.get("text") or "").strip() for item in content if isinstance(item, dict)]
            return "\n".join(part for part in parts if part).strip()
        return ""

    async def parse_image(
        self,
        image_base64: str,
        prompt: str = "OCR this scientific document. Preserve equations and table structure.",
    ) -> LightOnOCRParseResult:
        if not self.base_url:
            raise AdapterError("LightOnOCR: LIGHTONOCR_BASE_URL is not configured")
        client = await self._get_client()
        user_content: list[dict[str, Any]] = []
        if self.include_text_prompt and prompt.strip():
            user_content.append({"type": "text", "text": prompt})
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"},
            }
        )
        payload = {
            "model": "lightonocr",
            "messages": [
                {"role": "system", "content": ""},
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
            "temperature": 0.0,
            "max_tokens": 4096,
        }

        try:
            resp = await client.post(self._chat_endpoint(), json=payload)
            resp.raise_for_status()
            result = resp.json()
            text = self._extract_content(result)
            if not text:
                raise AdapterError("LightOnOCR: empty response content")
            return {
                "text": text,
                "status": "success",
                "model_id": "lightonocr",
                "raw_json": result,
            }
        except httpx.HTTPStatusError as exc:
            body = ""
            try:
                body = exc.response.text.replace("\n", " ").strip()
            except Exception:
                body = ""
            raise AdapterError(
                f"LightOnOCR: HTTP {exc.response.status_code} — {body[:160]}"
            ) from exc
        except httpx.RequestError as exc:
            raise AdapterError(f"LightOnOCR: request failed — {exc}") from exc

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
