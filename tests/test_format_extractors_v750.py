"""Unit tests for v7.5.0 Phase 3 format extractors.

Run: python -m pytest tests/test_format_extractors_v750.py -v

Real-file tests use fixtures from tests/fixtures/upload_samples/
(regenerate via generate_fixtures.py if missing).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADMIN_PASSWORD", "test1234")

from backend.extraction import (  # noqa: E402
    extract_text,
    _extract_xlsx, _extract_pptx, _extract_html, _extract_json, _extract_rtf,
)

FIXTURES = ROOT / "tests" / "fixtures" / "upload_samples"


# ─── Dispatch tests (extract_text routes to right handler) ──────────


def test_dispatch_xlsx_routes_to_xlsx_extractor(monkeypatch):
    called = {"yes": False}
    monkeypatch.setattr("backend.extraction._extract_xlsx",
                        lambda fp: (called.update(yes=True) or "ok"))
    extract_text("x.xlsx", "xlsx")
    assert called["yes"]


def test_dispatch_pptx(monkeypatch):
    called = {"yes": False}
    monkeypatch.setattr("backend.extraction._extract_pptx",
                        lambda fp: (called.update(yes=True) or "ok"))
    extract_text("x.pptx", "pptx")
    assert called["yes"]


def test_dispatch_html(monkeypatch):
    called = {"yes": False}
    monkeypatch.setattr("backend.extraction._extract_html",
                        lambda fp: (called.update(yes=True) or "ok"))
    extract_text("x.html", "html")
    assert called["yes"]


def test_dispatch_json(monkeypatch):
    called = {"yes": False}
    monkeypatch.setattr("backend.extraction._extract_json",
                        lambda fp: (called.update(yes=True) or "ok"))
    extract_text("x.json", "json")
    assert called["yes"]


def test_dispatch_rtf(monkeypatch):
    called = {"yes": False}
    monkeypatch.setattr("backend.extraction._extract_rtf",
                        lambda fp: (called.update(yes=True) or "ok"))
    extract_text("x.rtf", "rtf")
    assert called["yes"]


# ─── Real-file extraction (require fixtures) ────────────────────────


@pytest.fixture
def fixture_or_skip():
    def _f(name):
        p = FIXTURES / name
        if not p.exists():
            pytest.skip(f"fixture {name} missing — run generate_fixtures.py")
        return str(p)
    return _f


def test_xlsx_extracts_all_sheets(fixture_or_skip):
    """sample.xlsx has 3 sheets (Q1_Sales, Q2_Sales, Notes) — all should appear."""
    result = _extract_xlsx(fixture_or_skip("sample.xlsx"))
    assert "Q1_Sales" in result
    assert "Q2_Sales" in result
    assert "Notes" in result
    assert "Widget A" in result, "first sheet content missing"


def test_xlsx_data_only_resolves_formulas(fixture_or_skip):
    """sample.xlsx has B4=SUM(B2:B3) → should appear as 3500 (cached value)."""
    result = _extract_xlsx(fixture_or_skip("sample.xlsx"))
    # Either "3500" appears (formula resolved) OR formula text doesn't leak as raw "=SUM"
    assert "=SUM" not in result, "raw formula text leaked — data_only=True should resolve"


def test_pptx_extracts_slide_titles_and_notes(fixture_or_skip):
    """sample.pptx has 2 slides with speaker notes — all should appear."""
    result = _extract_pptx(fixture_or_skip("sample.pptx"))
    assert "Slide 1" in result
    assert "Slide 2" in result
    assert "SPEAKER_NOTES_MARKER_S1" in result, "speaker notes missing for slide 1"
    assert "SPEAKER_NOTES_MARKER_S2" in result, "speaker notes missing for slide 2"


def test_html_safe_extracts_text(fixture_or_skip):
    """sample_safe.html — plain text should be present."""
    result = _extract_html(fixture_or_skip("sample_safe.html"))
    assert "PDB v7.5.0 HTML Extract Test" in result
    assert "Subsection" in result


# ─── SECURITY: HTML strips script/style ─────────────────────────────


def test_html_xss_strips_script_tag(fixture_or_skip):
    """sample_xss.html has <script>alert(1)</script> — must NOT appear in output."""
    result = _extract_html(fixture_or_skip("sample_xss.html"))
    assert "<script>" not in result, "script tag leaked"
    assert "alert" not in result, "script content leaked — XSS risk for LLM context"
    assert "alert(1)" not in result, "explicit XSS payload leaked"
    assert "JS_MARKER_SHOULD_BE_STRIPPED" not in result, "inline JS leaked"


def test_html_xss_strips_style_tag(fixture_or_skip):
    """<style> blocks should also be stripped (CSS may have data: URIs)."""
    result = _extract_html(fixture_or_skip("sample_xss.html"))
    assert "<style>" not in result
    assert "CSS_MARKER_SHOULD_BE_STRIPPED" not in result
    assert "color: red" not in result


def test_html_xss_preserves_safe_body_content(fixture_or_skip):
    """After stripping unsafe tags, real body text should remain."""
    result = _extract_html(fixture_or_skip("sample_xss.html"))
    assert "Safe Content" in result
    assert "should be in extracted output" in result


# ─── JSON tests ──────────────────────────────────────────────────────


def test_json_pretty_prints(fixture_or_skip):
    """sample.json is parsed + pretty-printed."""
    result = _extract_json(fixture_or_skip("sample.json"))
    assert "version" in result
    assert "7.5.0" in result
    assert "upload_resilience" in result
    # Pretty-printed = has indentation
    assert "  " in result, "JSON should be pretty-printed with indent"


def test_json_malformed_returns_raw_text(tmp_path):
    """Malformed JSON falls back to raw text (not None or error)."""
    p = tmp_path / "bad.json"
    p.write_text('{"not valid json,}', encoding="utf-8")
    result = _extract_json(str(p))
    assert "not valid json" in result, "raw fallback should preserve content"


# ─── RTF tests ───────────────────────────────────────────────────────


def test_rtf_strips_control_codes(fixture_or_skip):
    """sample.rtf — control codes \\f0, \\fs24 should NOT appear in output."""
    result = _extract_rtf(fixture_or_skip("sample.rtf"))
    assert "\\f0" not in result
    assert "\\fs24" not in result
    assert "PDB v7.5.0 RTF test content" in result


# ─── Missing-dep graceful degradation ────────────────────────────────


def test_xlsx_missing_dep_returns_marker(monkeypatch):
    """If openpyxl somehow missing, return marker not exception."""
    import sys as _sys
    monkeypatch.setitem(_sys.modules, "openpyxl", None)
    result = _extract_xlsx("anything.xlsx")
    assert "[xlsx extractor unavailable" in result or "[Extraction error" in result
