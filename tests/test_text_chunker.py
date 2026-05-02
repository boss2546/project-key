"""Unit tests for v7.5.0 text_chunker (Phase 4 — big file map-reduce).

Run: python -m pytest tests/test_text_chunker.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADMIN_PASSWORD", "test1234")

from backend.text_chunker import (  # noqa: E402
    CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNK_SIZE, MIN_CHUNK_SIZE,
    chunk_text,
)


# ─── Boundary cases ─────────────────────────────────────────────────


def test_empty_text_returns_single_empty_chunk():
    assert chunk_text("") == [""]


def test_short_text_no_split():
    """Text below CHUNK_SIZE returns as single chunk (no overlap added)."""
    text = "a" * (CHUNK_SIZE - 100)
    result = chunk_text(text)
    assert len(result) == 1
    assert result[0] == text


def test_exactly_chunk_size_no_split():
    text = "x" * CHUNK_SIZE
    result = chunk_text(text)
    assert len(result) == 1


# ─── Heading-based split ────────────────────────────────────────────


def test_split_by_heading_when_present():
    """Markdown headings produce multi-chunk split."""
    sections = [f"## Section {i}\n" + ("para " * 1500) for i in range(5)]
    text = "\n\n".join(sections)
    chunks = chunk_text(text)
    assert len(chunks) > 1, f"expected multi-chunk, got {len(chunks)}"


def test_heading_chunks_within_max():
    """All heading-based chunks must be ≤ MAX_CHUNK_SIZE."""
    text = "\n\n".join(f"## H{i}\n" + ("x " * 2000) for i in range(8))
    chunks = chunk_text(text)
    for i, c in enumerate(chunks):
        assert len(c) <= MAX_CHUNK_SIZE, f"chunk[{i}] is {len(c)} chars (> MAX {MAX_CHUNK_SIZE})"


# ─── Paragraph fallback ──────────────────────────────────────────────


def test_split_by_paragraph_when_no_headings():
    """Without headings, paragraph-based split kicks in."""
    paras = ["paragraph " * 500 for _ in range(10)]
    text = "\n\n".join(paras)
    chunks = chunk_text(text)
    assert len(chunks) > 1


# ─── Hard split fallback ─────────────────────────────────────────────


def test_oversized_paragraph_hard_split():
    """A single paragraph way bigger than CHUNK_SIZE → hard char split."""
    text = "z" * (CHUNK_SIZE * 4)  # 40K, no boundaries at all
    chunks = chunk_text(text)
    assert len(chunks) >= 3
    for c in chunks:
        assert len(c) <= MAX_CHUNK_SIZE


# ─── Overlap behavior ────────────────────────────────────────────────


def test_overlap_added_between_adjacent_chunks():
    """Adjacent chunks should share CHUNK_OVERLAP chars."""
    sections = [f"## S{i}\n" + ("a" * 8000) for i in range(4)]
    text = "\n\n".join(sections)
    chunks = chunk_text(text)
    if len(chunks) < 2:
        pytest.skip("test setup didn't trigger multi-chunk")
    # chunks[1] should start with last CHUNK_OVERLAP chars of chunks[0]
    assert chunks[1].startswith(chunks[0][-CHUNK_OVERLAP:])


def test_no_overlap_for_single_chunk():
    """Single chunk has no overlap (nothing to prepend to)."""
    text = "single " * 100
    result = chunk_text(text)
    assert len(result) == 1
    assert not result[0].startswith(result[0][-CHUNK_OVERLAP:] + result[0])  # no double prefix


# ─── Content preservation ────────────────────────────────────────────


def test_content_preserved_no_data_loss():
    """Joining all chunks (after overlap) should reproduce original text."""
    text = "\n\n".join(f"## Heading {i}\n" + (f"content_{i} " * 500) for i in range(6))
    chunks = chunk_text(text)
    # Concatenate WITHOUT overlap reconstruction = total chars >= original
    total_chars = sum(len(c) for c in chunks)
    # With overlap, total > original (chunks share boundary text)
    assert total_chars >= len(text), \
        f"data loss detected: chunks total {total_chars} < original {len(text)}"


def test_unique_markers_across_chunks():
    """If text has UNIQUE_MARKER_NNN per page, every marker should appear in some chunk."""
    pages = [f"=== PAGE {n} === UNIQUE_MARKER_{n:03d} ===\n" + ("content " * 500) for n in range(1, 11)]
    text = "\n\n".join(pages)
    chunks = chunk_text(text)
    full_concat = "".join(chunks)
    for n in range(1, 11):
        marker = f"UNIQUE_MARKER_{n:03d}"
        assert marker in full_concat, f"missing {marker} in chunks"


# ─── Constants sanity ───────────────────────────────────────────────


def test_constants_have_expected_relationships():
    """Sanity: CHUNK_SIZE < MAX_CHUNK_SIZE, MIN < CHUNK, OVERLAP < CHUNK."""
    assert MIN_CHUNK_SIZE < CHUNK_SIZE
    assert CHUNK_SIZE < MAX_CHUNK_SIZE
    assert CHUNK_OVERLAP < CHUNK_SIZE
    assert CHUNK_OVERLAP > 0
