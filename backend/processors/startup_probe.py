"""Startup probe for ingestion dependencies -- v10.0.2.

HANDOFF Checklist Step 4: "Pre-deploy testing — smoke test routing per format,
verify fallback path, logging RAM + time."

At boot, log a one-line status for each ingestion path so admins can spot
silently-degraded paths (e.g. Tesseract missing, LlamaParse key absent) BEFORE
users start uploading and get cryptic "อ่านไม่ออก" errors.

This is a probe, not a gate -- everything emits WARNING-level logs, nothing
raises. If a path is unavailable, callers already have fallbacks (Decision 7).
"""
from __future__ import annotations

import logging
import os
from typing import List, Tuple

__all__ = ["run_startup_probe", "probe_results"]


def _probe_python_libs() -> List[Tuple[str, bool, str]]:
    """Check optional Python deps. Returns (name, ok, note)."""
    checks: List[Tuple[str, bool, str]] = []

    # Office locals (HANDOFF Decision 4)
    for mod, label in (
        ("docx",         "python-docx"),
        ("pptx",         "python-pptx"),
        ("openpyxl",     "openpyxl"),
    ):
        try:
            __import__(mod)
            checks.append((label, True, "local Office extractor available"))
        except ImportError:
            checks.append((label, False, "MISSING — DOCX/PPTX/XLSX falls back to LlamaParse"))

    # PDF chain
    try:
        import docling  # noqa: F401
        checks.append(("docling", True, "structured PDF + DOCX understanding available"))
    except ImportError:
        checks.append(("docling", False, "missing — PDF falls through to PyPDF2/OCR/Gemini"))

    try:
        import PyPDF2  # noqa: F401
        checks.append(("PyPDF2", True, "PDF text-layer extraction available"))
    except ImportError:
        checks.append(("PyPDF2", False, "MISSING — text-layer PDFs may fail"))

    # OCR
    ocr_module_ok = False
    try:
        import pytesseract  # noqa: F401
        from pdf2image import convert_from_path  # noqa: F401
        ocr_module_ok = True
    except ImportError:
        checks.append(("pytesseract+pdf2image", False, "missing modules — image PDFs use Gemini fallback"))
    if ocr_module_ok:
        # Check binary too
        try:
            import pytesseract as _pyt
            version = _pyt.get_tesseract_version()
            checks.append(("tesseract binary", True, f"v{version} on PATH"))
        except Exception:
            checks.append(("tesseract binary", False, "module loaded but binary NOT on PATH — image PDFs use Gemini fallback"))

    # AI multimodal
    try:
        from google import genai  # noqa: F401
        key = bool(os.getenv("GOOGLE_API_KEY", "").strip())
        if key:
            checks.append(("Gemini (google-genai)", True, "audio/video/image + PDF fallback available"))
        else:
            checks.append(("Gemini (google-genai)", False, "module installed but GOOGLE_API_KEY not set — audio/video upload will fail"))
    except ImportError:
        checks.append(("Gemini (google-genai)", False, "MISSING — audio/video/image cannot extract"))

    return checks


def _probe_llamaparse() -> Tuple[str, bool, str]:
    """LlamaParse uses direct REST (no SDK), so only need API key + flag."""
    try:
        from ..config import is_llamaparse_configured, LLAMA_CLOUD_API_KEY, USE_LLAMAPARSE_FOR_PDF
    except ImportError:
        return ("LlamaParse", False, "config import failed")
    if not USE_LLAMAPARSE_FOR_PDF:
        return ("LlamaParse", False, "USE_LLAMAPARSE_FOR_PDF=false — PDFs use Docling/PyPDF2/OCR/Gemini")
    if not LLAMA_CLOUD_API_KEY:
        return ("LlamaParse", False, "LLAMA_CLOUD_API_KEY not set — PDFs use Docling/PyPDF2/OCR/Gemini")
    if is_llamaparse_configured():
        return ("LlamaParse", True, "REST API ready (httpx) — preferred PDF processor")
    return ("LlamaParse", False, "configured but is_llamaparse_configured() returned false")


# Cached probe result (queried by /api/admin/extraction-stats etc.)
probe_results: List[Tuple[str, bool, str]] = []


def run_startup_probe(logger: logging.Logger) -> None:
    """Log status of each ingestion dependency at boot.

    Records cached in module-level `probe_results` for later inspection
    (admin diagnostics endpoint, dev log panel).
    """
    global probe_results
    results = _probe_python_libs() + [_probe_llamaparse()]
    probe_results = results

    available = sum(1 for _, ok, _ in results if ok)
    total = len(results)

    logger.info(
        "Startup probe: %d/%d ingestion paths available", available, total
    )
    for name, ok, note in results:
        symbol = "OK" if ok else "WARN"
        line = f"  [{symbol}] {name}: {note}"
        if ok:
            logger.info(line)
        else:
            logger.warning(line)

    # Surface any combination that means image-only PDFs would silently fail
    try:
        llama = next((ok for n, ok, _ in results if n == "LlamaParse"), False)
        gem = next((ok for n, ok, _ in results if n.startswith("Gemini")), False)
        tess_bin = next((ok for n, ok, _ in results if n == "tesseract binary"), False)
        docling = next((ok for n, ok, _ in results if n == "docling"), False)
        if not llama and not gem and not tess_bin and not docling:
            logger.error(
                "STARTUP: ALL PDF paths unavailable — image-only PDFs WILL FAIL. "
                "Install at least one of: Tesseract, Docling+RapidOCR, GOOGLE_API_KEY, LLAMA_CLOUD_API_KEY."
            )
    except Exception:
        pass
