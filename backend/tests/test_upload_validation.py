"""Tests for upload PDF validation helpers."""

from types import SimpleNamespace

from backend.api.routes.upload import _is_likely_pdf


def test_is_likely_pdf_accepts_known_pdf_content_type():
    file = SimpleNamespace(content_type="application/pdf", filename="paper.pdf")
    assert _is_likely_pdf(file, b"random bytes")


def test_is_likely_pdf_accepts_octet_stream_with_pdf_header():
    file = SimpleNamespace(content_type="application/octet-stream", filename="paper.bin")
    assert _is_likely_pdf(file, b"%PDF-1.7 some content")


def test_is_likely_pdf_rejects_non_pdf_payload():
    file = SimpleNamespace(content_type="text/plain", filename="notes.txt")
    assert _is_likely_pdf(file, b"not a pdf") is False
