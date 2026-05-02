"""Smart text chunker for big-file map-reduce processing (v7.5.0).

Strategy (in order of preference — falls back if chunks too large):
  1. Markdown headings (`#`, `##`, `###`) — Docling output has structure
  2. Double newline (paragraph boundary)
  3. Sentence boundary (. ! ? ฯลฯ)
  4. Hard char split (last resort, may break mid-word)

Why these specific values:
- CHUNK_SIZE=10K chars → ~2-3K tokens (fits well within Gemini Flash 32K context
  with room for system prompt + meta + reduce-step concat)
- OVERLAP=500 chars → 5% of chunk, kept low to avoid duplicate cost in vector
  index. Enough to preserve context across heading boundaries.
- MIN_CHUNK_SIZE=2K → tiny chunks merged with next (avoid LLM overhead per chunk
  when content is small)

Used by:
- backend/organizer.py — _generate_summary_mapreduce() for files where
  len(extracted_text) > LARGE_FILE_THRESHOLD (30K chars from config.py)
"""
from __future__ import annotations

import re
from typing import List

CHUNK_SIZE = 10_000          # target chars per chunk
CHUNK_OVERLAP = 500          # gun context loss ที่ขอบ heading/paragraph
MIN_CHUNK_SIZE = 2_000       # chunks smaller than this merge with next
MAX_CHUNK_SIZE = 15_000      # if a chunk would exceed this, hard-split it


def chunk_text(text: str) -> List[str]:
    """Split text into ~CHUNK_SIZE-char chunks at semantic boundaries.

    Returns list of chunks (always ≥ 1 element). Each chunk has ≤ MAX_CHUNK_SIZE
    chars. Adjacent chunks may share up to CHUNK_OVERLAP chars to preserve context.

    Empty / very short input returns [text] unchanged (no overlap, no split).
    """
    if not text:
        return [""]
    if len(text) <= CHUNK_SIZE:
        return [text]

    # Try strategies in order — pick first that produces all-valid chunks
    for strategy in (_split_by_heading, _split_by_paragraph, _split_by_sentence):
        chunks = strategy(text)
        chunks = _merge_small(chunks)
        # Hard-split any that are still oversized
        chunks = _split_oversized(chunks)
        if chunks and all(len(c) <= MAX_CHUNK_SIZE for c in chunks):
            return _add_overlap(chunks)

    # Final fallback — pure char split
    return _hard_split(text, CHUNK_SIZE)


# ─── Strategies ─────────────────────────────────────────────────────


_HEADING_RE = re.compile(r"^(#{1,6})\s+", re.MULTILINE)


def _split_by_heading(text: str) -> List[str]:
    """Split at markdown headings — keep heading line with its section."""
    # Find heading positions
    positions = [m.start() for m in _HEADING_RE.finditer(text)]
    if not positions:
        return [text]
    # If first heading not at position 0, the prefix is its own chunk (e.g., front matter)
    chunks = []
    if positions[0] > 0:
        chunks.append(text[:positions[0]])
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        chunks.append(text[start:end])
    return [c for c in chunks if c.strip()]


def _split_by_paragraph(text: str) -> List[str]:
    """Split at double-newline boundaries, accumulating into ~CHUNK_SIZE blocks."""
    paragraphs = re.split(r"\n\s*\n", text)
    return _accumulate(paragraphs, joiner="\n\n")


_SENTENCE_RE = re.compile(r"(?<=[.!?ฯ])\s+")


def _split_by_sentence(text: str) -> List[str]:
    """Split at sentence boundaries — last resort before hard char split."""
    sentences = _SENTENCE_RE.split(text)
    return _accumulate(sentences, joiner=" ")


def _accumulate(parts: List[str], joiner: str) -> List[str]:
    """Greedy fill: accumulate parts until adding next would exceed CHUNK_SIZE."""
    chunks = []
    current = ""
    for part in parts:
        if not part:
            continue
        if not current:
            current = part
        elif len(current) + len(joiner) + len(part) <= CHUNK_SIZE:
            current += joiner + part
        else:
            chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks


# ─── Cleanup ────────────────────────────────────────────────────────


def _merge_small(chunks: List[str]) -> List[str]:
    """Merge chunks below MIN_CHUNK_SIZE with their neighbor."""
    if len(chunks) < 2:
        return chunks
    out = []
    i = 0
    while i < len(chunks):
        c = chunks[i]
        # If next chunk is small AND they fit together, merge them
        if (i + 1 < len(chunks)
                and len(chunks[i + 1]) < MIN_CHUNK_SIZE
                and len(c) + len(chunks[i + 1]) <= CHUNK_SIZE):
            out.append(c + "\n\n" + chunks[i + 1])
            i += 2
        else:
            out.append(c)
            i += 1
    return out


def _split_oversized(chunks: List[str]) -> List[str]:
    """Hard-split any chunk that exceeds MAX_CHUNK_SIZE."""
    out = []
    for c in chunks:
        if len(c) <= MAX_CHUNK_SIZE:
            out.append(c)
        else:
            out.extend(_hard_split(c, CHUNK_SIZE))
    return out


def _hard_split(text: str, size: int) -> List[str]:
    """Pure char-based split. May break mid-word."""
    return [text[i:i + size] for i in range(0, len(text), size)]


def _add_overlap(chunks: List[str]) -> List[str]:
    """Prefix each chunk (except first) with last CHUNK_OVERLAP chars of previous.

    Why: heading-based split can lose context where a topic spans the boundary.
    Overlap ensures the LLM summary for chunk N has enough preceding context.
    """
    if len(chunks) < 2 or CHUNK_OVERLAP <= 0:
        return chunks
    out = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-CHUNK_OVERLAP:]
        out.append(prev_tail + chunks[i])
    return out
