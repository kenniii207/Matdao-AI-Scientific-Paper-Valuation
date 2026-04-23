"""Tests for GLM OCR adapter behavior."""

from __future__ import annotations

import httpx
import pytest

from backend.api.adapters.glm_ocr_adapter import GLMOCRAdapter
from backend.core.config import settings
from backend.core.exceptions import AdapterError


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.com")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]):
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    async def post(self, url: str, json: dict) -> _FakeResponse:  # noqa: A002
        self.calls.append((url, json))
        return self.responses[len(self.calls) - 1]

    async def get(self, _url: str) -> _FakeResponse:
        return _FakeResponse(200, {"status": "ok"})

    @property
    def is_closed(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_parse_image_uses_layout_parsing_first(monkeypatch):
    monkeypatch.setattr(settings, "zai_api_key", "test-zai-key")
    adapter = GLMOCRAdapter(
        layout_endpoint="https://open.bigmodel.cn/api/paas/v4/layout_parsing",
        chat_endpoint="https://open.bigmodel.cn/api/paas/v4/chat/completions",
    )
    fake_client = _FakeClient(
        [_FakeResponse(200, {"data": {"markdown": "layout text"}})]
    )

    async def _fake_get_client():
        return fake_client

    monkeypatch.setattr(adapter, "_get_client", _fake_get_client)
    result = await adapter.parse_image("abc")

    assert len(fake_client.calls) == 1
    assert fake_client.calls[0][0].endswith("/layout_parsing")
    assert fake_client.calls[0][1]["model"] == settings.glm_ocr_model
    assert result["text"] == "layout text"
    assert result["model_id"] == settings.glm_ocr_model


@pytest.mark.asyncio
async def test_parse_image_falls_back_to_glm_vision_when_layout_fails(monkeypatch):
    monkeypatch.setattr(settings, "zai_api_key", "test-zai-key")
    monkeypatch.setattr(settings, "glm_vision_model", "glm-4.6v-flash")
    adapter = GLMOCRAdapter(
        layout_endpoint="https://open.bigmodel.cn/api/paas/v4/layout_parsing",
        chat_endpoint="https://open.bigmodel.cn/api/paas/v4/chat/completions",
    )
    fake_client = _FakeClient(
        [
            _FakeResponse(500, {}, text="layout failed"),
            _FakeResponse(200, {"choices": [{"message": {"content": "vision text"}}]}),
        ]
    )

    async def _fake_get_client():
        return fake_client

    monkeypatch.setattr(adapter, "_get_client", _fake_get_client)
    result = await adapter.parse_image("abc", prompt="OCR this document.")

    assert len(fake_client.calls) == 2
    assert fake_client.calls[0][0].endswith("/layout_parsing")
    assert fake_client.calls[1][0].endswith("/chat/completions")
    assert fake_client.calls[1][1]["model"] == "glm-4.6v-flash"
    assert result["text"] == "vision text"
    assert result["model_id"] == "glm-4.6v-flash"
    assert result["status"] == "success_fallback"


def test_glm_ocr_timeout_is_configurable():
    adapter = GLMOCRAdapter(timeout_seconds=17)
    assert adapter.timeout_seconds == 17


@pytest.mark.asyncio
async def test_parse_image_raises_sanitized_error_on_double_failure(monkeypatch):
    monkeypatch.setattr(settings, "zai_api_key", "test-zai-key")
    adapter = GLMOCRAdapter(
        layout_endpoint="https://open.bigmodel.cn/api/paas/v4/layout_parsing",
        chat_endpoint="https://open.bigmodel.cn/api/paas/v4/chat/completions",
    )
    fake_client = _FakeClient(
        [
            _FakeResponse(500, {}, text="layout failed with a very long body " * 20),
            _FakeResponse(500, {}, text="vision failed with a very long body " * 20),
        ]
    )

    async def _fake_get_client():
        return fake_client

    monkeypatch.setattr(adapter, "_get_client", _fake_get_client)
    with pytest.raises(AdapterError) as exc_info:
        await adapter.parse_image("abc", prompt="OCR this document.")
    message = str(exc_info.value)
    assert "GLM OCR failed after layout + vision fallback" in message
    assert len(message) < 650
