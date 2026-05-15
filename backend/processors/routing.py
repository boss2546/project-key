"""File-type -> processor routing -- v10.0.0.

The single source of truth for "which extractor should this file use?".

Decision flow (HANDOFF section 7):
  1. Python-lib supported (DOCX/PPTX/XLSX/HTML/JSON/RTF/TXT/MD) -> local extract
  2. AI multimodal (audio/video) -> ai_ingest (Gemini)
  3. PDF -> LlamaParse if configured, else Docling/pypdf/OCR fallback chain
  4. Image -> AI smart vision (preferred) or OCR (fallback)
  5. Everything else -> vault-only (filename indexed but no text)

This module produces *Decisions* but does NOT run them -- extraction.py /
upload_worker.py call .extract_text(filepath, filetype) with the returned
processor name. Pure logic, no side effects, easy to unit-test.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from ..config import (
    LOCAL_EXTRACT_MAX_MB,
    USE_LLAMAPARSE_FOR_PDF,
    is_llamaparse_configured,
)


# ============================================================
# Format families
# ============================================================
LOCAL_TEXT_FORMATS = {"txt", "md", "csv", "log", "rst"}
LOCAL_OFFICE_FORMATS = {"docx", "pptx", "xlsx"}
LOCAL_WEB_FORMATS = {"html", "htm", "json", "rtf", "xml"}

PDF_FORMATS = {"pdf"}

# Routed through ai_ingest (Gemini multimodal). Image formats below are
# also AI-eligible but we have OCR fallback for them; audio/video have
# none -- if Gemini isn't configured, they go to vault.
AUDIO_FORMATS = {"mp3", "wav", "m4a", "ogg", "flac", "aac", "wma"}
VIDEO_FORMATS = {"mp4", "mov", "webm", "mkv", "avi", "wmv", "flv"}
IMAGE_FORMATS = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "tiff", "heic", "heif"}


# ============================================================
# Decision dataclass
# ============================================================
@dataclass
class Decision:
    """Which processor + fallback to use, plus reasoning for logging."""

    processor: str          # "local" | "llamaparse" | "ai_ingest" | "ocr" | "vault"
    fallback: Optional[str] = None  # next processor if primary raises
    reason: str = ""
    # Estimate, satang (1/100 baht). 0 = free / unknown. Used for
    # admin stats + budget guard, not user-facing.
    cost_cents_estimate: int = 0
    warnings: list[str] = field(default_factory=list)


# ============================================================
# Public decision function
# ============================================================
def decide(filename: str, file_size_bytes: int = 0) -> Decision:
    """Pick a processor for a given file.

    Args:
        filename:         original filename (used for extension lookup)
        file_size_bytes:  0 if unknown -- size threshold logic skips then

    Returns:
        Decision with processor + fallback + estimated cost.
    """
    ext = _file_ext(filename)
    size_mb = (file_size_bytes / (1024 * 1024)) if file_size_bytes else 0.0

    # ---- Plain text (cheapest path) ----
    if ext in LOCAL_TEXT_FORMATS:
        return Decision(
            processor="local",
            reason=f"{ext} -> local text extractor (free)",
        )

    # ---- Office (DOCX/PPTX/XLSX) ----
    if ext in LOCAL_OFFICE_FORMATS:
        warnings = []
        if size_mb > LOCAL_EXTRACT_MAX_MB:
            # Big Office file -- still try local first but flag it. lab-validated
            # local is 5-6x faster + 40-76x cheaper even at >10 MB; we keep the
            # warning so admin can monitor RAM via /api/admin/extraction-stats.
            warnings.append(f"file {size_mb:.1f}MB > LOCAL_EXTRACT_MAX_MB={LOCAL_EXTRACT_MAX_MB}")
        return Decision(
            processor="local",
            reason=f"{ext} -> python-docx/pptx/openpyxl (local, fast, Thai-safe)",
            cost_cents_estimate=6,  # ~b0.06 (Gemini summary pass)
            warnings=warnings,
        )

    # ---- Web/structured text ----
    if ext in LOCAL_WEB_FORMATS:
        return Decision(
            processor="local",
            reason=f"{ext} -> local web/text extractor",
        )

    # ---- PDF -- the big one ----
    if ext in PDF_FORMATS:
        if is_llamaparse_configured():
            return Decision(
                processor="llamaparse",
                fallback="local",  # docling/pypdf if LlamaParse fails
                reason="pdf -> LlamaParse (better Thai diacritic preservation)",
                cost_cents_estimate=200,  # ~b2 balanced mode
            )
        return Decision(
            processor="local",
            reason=(
                "pdf -> Docling/pypdf/OCR fallback chain "
                "(LlamaParse not configured: " + _why_no_llamaparse() + ")"
            ),
        )

    # ---- Audio / Video -> Gemini ----
    if ext in AUDIO_FORMATS:
        return Decision(
            processor="ai_ingest",
            fallback="vault",
            reason=f"{ext} -> Gemini audio transcription",
            cost_cents_estimate=20,
        )
    if ext in VIDEO_FORMATS:
        return Decision(
            processor="ai_ingest",
            fallback="vault",
            reason=f"{ext} -> Gemini video understanding",
            cost_cents_estimate=100,
        )

    # ---- Images -> AI smart vision (preferred), OCR fallback ----
    if ext in IMAGE_FORMATS:
        return Decision(
            processor="ai_ingest",
            fallback="ocr",
            reason=f"{ext} -> Gemini vision (OCR fallback)",
            cost_cents_estimate=2,
        )

    # ---- Unknown / unsupported ----
    return Decision(
        processor="vault",
        reason=f"{ext or '(no extension)'} -> vault only (filename-indexed)",
        warnings=[f"unsupported format: .{ext}"],
    )


# ============================================================
# Helpers
# ============================================================
def _file_ext(filename: str) -> str:
    """Lower-case extension without dot, '' if no dot."""
    if not filename:
        return ""
    base = os.path.basename(filename)
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[1].lower()


def _why_no_llamaparse() -> str:
    """Human-readable reason if LlamaParse path is unavailable -- for logs."""
    if not USE_LLAMAPARSE_FOR_PDF:
        return "USE_LLAMAPARSE_FOR_PDF=false"
    if not os.getenv("LLAMA_CLOUD_API_KEY"):
        return "LLAMA_CLOUD_API_KEY not set"
    try:
        import llama_parse  # noqa: F401
    except ImportError:
        return "llama-parse package not installed"
    return "configured but disabled"


def is_supported(filename: str) -> bool:
    """True if we have any non-vault path for this file type."""
    return decide(filename).processor != "vault"
