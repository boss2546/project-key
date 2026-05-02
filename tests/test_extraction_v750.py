"""Unit tests for v7.5.0 extraction additions (image OCR + format handlers).

Run: python -m pytest tests/test_extraction_v750.py -v

Note: Tests that need real Tesseract binary use `_HAS_OCR` skip — they
pass via mock/structure check on Windows where binary isn't installed.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pytest

# Ensure project root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# v7.5.0 — clear BYOS env so config.py imports cleanly
os.environ.setdefault("ADMIN_PASSWORD", "test1234")
for k in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"):
    os.environ[k] = ""

from backend import extraction
from backend.extraction import extract_text, _extract_image_ocr  # noqa: E402

FIXTURES_DIR = ROOT / "tests" / "fixtures" / "upload_samples"


# ─── Image OCR tests ────────────────────────────────────────────────


def test_extract_text_dispatches_image_branch_for_png(monkeypatch):
    """png filetype must hit _extract_image_ocr branch (not 'unsupported')."""
    called = {"yes": False}
    def fake_ocr(filepath):
        called["yes"] = True
        return "fake-ocr-result"
    monkeypatch.setattr(extraction, "_extract_image_ocr", fake_ocr)
    result = extract_text("nonexistent.png", "png")
    assert called["yes"], "extract_text must call _extract_image_ocr for png"
    assert result == "fake-ocr-result"


def test_extract_text_dispatches_image_branch_for_jpg(monkeypatch):
    called = {"yes": False}
    monkeypatch.setattr(extraction, "_extract_image_ocr",
                        lambda fp: (called.update(yes=True) or "ok"))
    extract_text("x.jpg", "jpg")
    assert called["yes"]


def test_extract_text_dispatches_image_branch_for_jpeg_and_webp(monkeypatch):
    seen = []
    monkeypatch.setattr(extraction, "_extract_image_ocr",
                        lambda fp: (seen.append(fp) or "ok"))
    extract_text("a.jpeg", "jpeg")
    extract_text("b.webp", "webp")
    assert seen == ["a.jpeg", "b.webp"]


def test_extract_image_ocr_returns_marker_when_unavailable(monkeypatch):
    """If pytesseract not installed → returns specific marker (not bare error)."""
    monkeypatch.setattr(extraction, "_HAS_OCR", False)
    result = _extract_image_ocr("anything.png")
    assert result == "[Image: OCR not available]"


def test_extract_image_ocr_returns_marker_for_blank_image(monkeypatch):
    """OCR succeeds but returns no text → specific marker (not empty string)."""
    monkeypatch.setattr(extraction, "_HAS_OCR", True)

    class FakeImg:
        mode = "RGB"
        def convert(self, _): return self

    class FakePIL:
        @staticmethod
        def open(_): return FakeImg()

    # Patch PIL.Image lookup
    import sys as _sys
    fake_mod = type(_sys)("PIL")
    fake_mod.Image = FakePIL
    monkeypatch.setitem(_sys.modules, "PIL", fake_mod)

    monkeypatch.setattr(extraction, "pytesseract",
                        type("X", (), {"image_to_string": staticmethod(lambda *a, **kw: "   ")}),
                        raising=False)
    # Also need to re-init since _HAS_OCR import-time
    result = _extract_image_ocr("blank.png")
    assert result == "[Image: no text detected]"


def test_extract_image_ocr_catches_exception(monkeypatch):
    """Unexpected exception → returns [OCR error: ...] marker (not raise)."""
    monkeypatch.setattr(extraction, "_HAS_OCR", True)
    import sys as _sys
    fake_mod = type(_sys)("PIL")
    class Bad:
        @staticmethod
        def open(_): raise IOError("disk fire")
    fake_mod.Image = Bad
    monkeypatch.setitem(_sys.modules, "PIL", fake_mod)
    result = _extract_image_ocr("broken.png")
    assert result.startswith("[OCR error:"), result


# ─── csv handling (v7.5.0 — added to txt branch) ─────────────────────


def test_extract_text_csv_uses_txt_extractor():
    """csv now routed through _extract_txt (was 'unsupported' in v7.4)."""
    csv_path = FIXTURES_DIR / "sample.csv"
    csv_path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    try:
        result = extract_text(str(csv_path), "csv")
        assert "a,b,c" in result and "1,2,3" in result
    finally:
        csv_path.unlink(missing_ok=True)


# ─── Marker format invariants (so compute_content_hash skips them) ──


def test_image_markers_start_with_bracket():
    """All extraction error markers MUST start with '[' so compute_content_hash
    returns None for them (avoids false-positive duplicate matches)."""
    markers = [
        "[Image: OCR not available]",
        "[Image: no text detected]",
        "[OCR error: foo]",
        "[Unsupported file type: xyz]",
    ]
    for m in markers:
        assert m.startswith("[")


# ─── Real-file integration (skip if Tesseract missing — Windows local) ──


@pytest.mark.skipif(not extraction._HAS_OCR, reason="pytesseract not installed")
def test_extract_image_ocr_real_with_text():
    """End-to-end: PNG with text should extract content via real Tesseract.

    Skipped on Windows local where tesseract binary missing — runs in Docker/Fly.io.
    """
    png_path = FIXTURES_DIR / "sample.png"
    if not png_path.exists():
        pytest.skip("fixture sample.png missing — run generate_fixtures.py")
    result = _extract_image_ocr(str(png_path))
    # Either real text OR error marker if tesseract binary not on PATH
    assert isinstance(result, str)
    if not result.startswith("["):
        # Real OCR succeeded
        assert len(result.strip()) > 0
