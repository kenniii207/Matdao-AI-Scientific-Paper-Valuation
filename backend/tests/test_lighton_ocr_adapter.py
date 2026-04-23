"""Tests for LightOn OCR adapter and preflight behavior."""

from __future__ import annotations

import pytest

from backend.api.adapters.lighton_ocr_adapter import LightOnOCRAdapter
from backend.api.routes import upload as upload_route
from backend.api.routes.upload import _lighton_preflight_error
from backend.core.config import settings


class _FakeHealthResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


class _FakeHealthClient:
    def __init__(self, responses: list[_FakeHealthResponse]):
        self.responses = responses
        self.get_calls: list[str] = []

    async def get(self, url: str, timeout: float | None = None) -> _FakeHealthResponse:
        self.get_calls.append(url)
        return self.responses[len(self.get_calls) - 1]

    @property
    def is_closed(self) -> bool:
        return False


def test_runtime_contract_requires_model_and_mmproj_paths(monkeypatch):
    monkeypatch.setattr(settings, "lightonocr_require_local_paths", True)
    monkeypatch.setattr(settings, "lightonocr_model_path", "")
    monkeypatch.setattr(settings, "lightonocr_mmproj_path", "")
    errors = LightOnOCRAdapter.runtime_contract_errors()
    assert "lighton_model_path_missing" in errors
    assert "lighton_mmproj_path_missing" in errors


def test_runtime_contract_accepts_existing_model_and_mmproj(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "lightonocr_require_local_paths", True)
    model_path = tmp_path / "LightOnOCR-2-1B.i1-Q5_K_M.gguf"
    mmproj_path = tmp_path / "LightOnOCR-2-1B.mmproj-f16.gguf"
    model_path.write_text("fake")
    mmproj_path.write_text("fake")
    monkeypatch.setattr(settings, "lightonocr_model_path", str(model_path))
    monkeypatch.setattr(settings, "lightonocr_mmproj_path", str(mmproj_path))
    errors = LightOnOCRAdapter.runtime_contract_errors()
    assert errors == []


def test_runtime_contract_skips_local_checks_when_not_required(monkeypatch):
    monkeypatch.setattr(settings, "lightonocr_require_local_paths", False)
    monkeypatch.setattr(settings, "lightonocr_model_path", "")
    monkeypatch.setattr(settings, "lightonocr_mmproj_path", "")
    errors = LightOnOCRAdapter.runtime_contract_errors()
    assert errors == []


@pytest.mark.asyncio
async def test_health_check_probes_health_then_v1_health(monkeypatch):
    adapter = LightOnOCRAdapter(base_url="http://localhost:8080")
    fake_client = _FakeHealthClient(
        [
            _FakeHealthResponse(503, {"status": "loading"}),
            _FakeHealthResponse(200, {"status": "ok"}),
        ]
    )

    async def _fake_get_client():
        return fake_client

    monkeypatch.setattr(adapter, "_get_client", _fake_get_client)
    healthy = await adapter.health_check()
    assert healthy is True
    assert fake_client.get_calls[0].endswith("/health")
    assert fake_client.get_calls[1].endswith("/v1/health")


def test_lighton_health_timeout_is_separate_from_inference_timeout(monkeypatch):
    monkeypatch.setattr(settings, "lightonocr_timeout_seconds", 45)
    monkeypatch.setattr(settings, "lightonocr_health_timeout_seconds", 3)
    adapter = LightOnOCRAdapter(base_url="http://localhost:8080")
    assert adapter.timeout_seconds == 45
    assert adapter.health_timeout_seconds == 3


@pytest.mark.asyncio
async def test_lighton_preflight_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "lightonocr_enabled", False)
    upload_route._LIGHTON_PREFLIGHT_CACHE.update(
        {"checked_monotonic": 0.0, "checked_unix": 0.0, "error": "not_checked", "enabled": False, "base_url": ""}
    )
    error = await _lighton_preflight_error()
    assert error == "lighton_disabled"


@pytest.mark.asyncio
async def test_lighton_preflight_uses_cache_ttl(monkeypatch):
    monkeypatch.setattr(settings, "lightonocr_enabled", True)
    monkeypatch.setattr(settings, "lightonocr_base_url", "http://localhost:8080")
    monkeypatch.setattr(settings, "lightonocr_require_local_paths", False)
    monkeypatch.setattr(settings, "lightonocr_readiness_cache_seconds", 60)

    call_count = {"health": 0}

    async def _fake_health(self):  # noqa: ANN001
        call_count["health"] += 1
        return True

    async def _fake_close(self):  # noqa: ANN001
        return None

    monkeypatch.setattr(LightOnOCRAdapter, "runtime_contract_errors", staticmethod(lambda: []))
    monkeypatch.setattr(LightOnOCRAdapter, "health_check", _fake_health)
    monkeypatch.setattr(LightOnOCRAdapter, "close", _fake_close)
    upload_route._LIGHTON_PREFLIGHT_CACHE.update(
        {"checked_monotonic": 0.0, "checked_unix": 0.0, "error": "not_checked", "enabled": False, "base_url": ""}
    )

    first = await _lighton_preflight_error()
    second = await _lighton_preflight_error()

    assert first is None
    assert second is None
    assert call_count["health"] == 1

    monkeypatch.setattr(settings, "lightonocr_readiness_cache_seconds", 0)
    third = await _lighton_preflight_error()
    assert third is None
    assert call_count["health"] == 2
