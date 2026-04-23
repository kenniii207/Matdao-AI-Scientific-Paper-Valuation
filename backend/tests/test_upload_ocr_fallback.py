"""Tests for OCR fallback ordering and extraction quality signal helpers."""

from backend.api.routes.upload import (
    _build_public_ocr_failure_detail,
    _build_ocr_quality_signals,
    _client_safe_ocr_codes,
    _compute_page_render_scale,
    _is_upload_size_exceeded,
    _merge_with_ocr_quality_signals,
    _ocr_page_indices,
    _resolve_ocr_fallback_order,
    _should_route_lighton,
)


def test_resolve_ocr_fallback_order_uses_defaults_when_empty():
    assert _resolve_ocr_fallback_order("") == ["pdf_text", "glm_ocr", "lighton_ocr"]


def test_resolve_ocr_fallback_order_filters_invalid_and_dedupes():
    order = _resolve_ocr_fallback_order("lighton_ocr,foo,glm_ocr,lighton_ocr")
    assert order == ["pdf_text", "lighton_ocr", "glm_ocr"]


def test_build_ocr_quality_signals_contains_provider_and_error_chain():
    signals = _build_ocr_quality_signals(
        provider="lighton-ocr-fallback",
        fallback_used=True,
        error_chain={"glm_ocr": "http_503"},
        model_id="lightonocr",
    )
    assert signals["ocr_provider"] == "lighton-ocr-fallback"
    assert signals["ocr_fallback_used"] is True
    assert signals["ocr_error_chain"]["glm_ocr"] == "http_503"
    assert signals["ocr_model_id"] == "lightonocr"


def test_should_route_lighton_respects_bounds():
    assert _should_route_lighton("paper-a", canary_percent=0) is False
    assert _should_route_lighton("paper-a", canary_percent=100) is True


def test_should_route_lighton_is_deterministic_for_same_key():
    first = _should_route_lighton("stable-paper-key", canary_percent=25)
    second = _should_route_lighton("stable-paper-key", canary_percent=25)
    assert first == second


def test_ocr_page_indices_caps_to_top_three():
    assert _ocr_page_indices(10, max_pages=3) == [0, 1, 2]
    assert _ocr_page_indices(2, max_pages=3) == [0, 1]


def test_compute_page_render_scale_downscales_large_pages():
    scale = _compute_page_render_scale(width=4000, height=4000, max_pixels=4_000_000)
    assert 0.1 <= scale < 1.0


def test_is_upload_size_exceeded_respects_limit():
    assert _is_upload_size_exceeded(size_bytes=25_000_001, max_upload_bytes=25_000_000) is True
    assert _is_upload_size_exceeded(size_bytes=24_999_999, max_upload_bytes=25_000_000) is False


def test_client_safe_ocr_codes_and_public_detail_are_sanitized():
    chain = {
        "glm_ocr": "HTTP 500 -- /tmp/private/path stacktrace",
        "lighton_ocr": "request timeout after 30s",
    }
    codes = _client_safe_ocr_codes(chain)
    assert "glm_ocr:failed" in codes
    assert "lighton_ocr:timeout" in codes
    detail = _build_public_ocr_failure_detail(chain)
    assert "/tmp/private/path" not in detail
    assert "stacktrace" not in detail


def test_merge_with_ocr_quality_signals_preserves_existing_signals():
    payload = {"status": "completed"}
    merged = _merge_with_ocr_quality_signals(payload, {"ocr_provider": "glm-ocr-fallback"})
    assert merged["status"] == "completed"
    assert merged["ocr_quality_signals"]["ocr_provider"] == "glm-ocr-fallback"
