"""Unit tests for classify_extraction_status (v7.5.0 Phase 2)."""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADMIN_PASSWORD", "test1234")

from backend.extraction import classify_extraction_status as cls  # noqa: E402


def test_normal_text_is_ok():
    assert cls("hello world this is real content") == "ok"


def test_empty_string_is_empty():
    assert cls("") == "empty"


def test_whitespace_only_is_empty():
    assert cls("   \n\n  \t") == "empty"


def test_encrypted_marker_detected():
    assert cls("[PDF encrypted: password-protected — unlock before re-uploading]") == "encrypted"
    assert cls("[Encrypted file]") == "encrypted"
    assert cls("[Password-protected document]") == "encrypted"


def test_ocr_failed_marker_detected():
    assert cls("[Image: no text detected]") == "ocr_failed"
    assert cls("[No text content found in PDF]") == "ocr_failed"
    assert cls("[OCR found no text in PDF images]") == "ocr_failed"
    assert cls("[OCR error: tesseract crashed]") == "ocr_failed"


def test_unsupported_marker_detected():
    assert cls("[Unsupported file type: heic]") == "unsupported"


def test_extraction_error_classified_as_ocr_failed():
    """Generic extraction errors land in ocr_failed bucket (closest semantic fit)."""
    assert cls("[Extraction error: file corrupt]") == "ocr_failed"


def test_unknown_bracket_marker_safe_default_ok():
    """Defensive — never block file because of unknown marker."""
    assert cls("[Some completely unknown marker]") == "ok"


def test_text_starting_with_bracket_but_real_content():
    """Real content that happens to start with bracket — needs explicit marker
    keywords to classify as error. Without keywords → ok."""
    # This is a known limitation: "[Note]: real content here" → ok (no keyword)
    assert cls("[NOTE]: this is actually a normal annotation") == "ok"
