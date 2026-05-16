"""LlamaParse PDF processor -- v10.0.0.

Opt-in PDF parser via LlamaParse cloud (https://cloud.llamaindex.ai).
Activated by setting `USE_LLAMAPARSE_FOR_PDF=true` + `LLAMA_CLOUD_API_KEY=...`
in env. If either is missing, callers should fall back to Docling/pypdf/OCR.

Why LlamaParse for PDF (HANDOFF Decision 5):
  - Docling drops ~50% of Thai diacritics on font-encoded PDFs.
  - LlamaParse balanced mode preserves diacritics well (lab tested).
  - 3 credits/page = b0.10/page ~ b2 per typical 20-page PDF.

Local-cache strategy:
  Result is cached by sha256(file_bytes) under DATA_DIR/.llamaparse_cache/<hash>.md.
  Re-uploading the same file -- or running e2e_verify twice -- doesn't double-spend.
  Cache hit returns instantly.
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

from ..config import (
    DATA_DIR,
    LLAMA_CLOUD_API_KEY,
    LLAMA_PARSE_MODE,
)
from .safety import retry_with_backoff

logger = logging.getLogger(__name__)


# ============================================================
# Cache
# ============================================================
_CACHE_DIR = Path(DATA_DIR) / ".llamaparse_cache"


def _ensure_cache_dir() -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _hash_file(filepath: str) -> str:
    """Return sha256 hex of file bytes -- used as cache key."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _cache_path_for(file_hash: str, mode: str) -> Path:
    return _CACHE_DIR / f"{file_hash}.{mode}.md"


def cache_get(file_hash: str, mode: str) -> Optional[str]:
    p = _cache_path_for(file_hash, mode)
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def cache_set(file_hash: str, mode: str, text: str) -> None:
    _ensure_cache_dir()
    p = _cache_path_for(file_hash, mode)
    try:
        p.write_text(text, encoding="utf-8")
    except Exception as e:
        logger.warning("llamaparse cache write failed: %s", e)


def purge_cache_for_file(filepath: str) -> int:
    """Remove all LlamaParse cache entries for this file (all modes).

    Used on file delete / account reset so extracted text doesn't survive
    on disk after the source file is removed (privacy). Returns the number
    of cache files removed; safe to call when raw file no longer exists
    (returns 0).
    """
    try:
        if not filepath or not os.path.exists(filepath):
            return 0
        file_hash = _hash_file(filepath)
    except Exception as e:
        logger.warning("purge_cache_for_file hash failed for %s: %s", filepath, e)
        return 0
    if not _CACHE_DIR.exists():
        return 0
    removed = 0
    for p in _CACHE_DIR.glob(f"{file_hash}.*.md"):
        try:
            p.unlink()
            removed += 1
        except OSError as e:
            logger.warning("purge_cache_for_file unlink %s failed: %s", p, e)
    return removed


def purge_cache_by_hash(file_hash: str) -> int:
    """Remove all LlamaParse cache entries for a precomputed sha256 hex.

    Useful when raw file already deleted but caller captured its hash earlier.
    """
    if not _CACHE_DIR.exists() or not file_hash:
        return 0
    removed = 0
    for p in _CACHE_DIR.glob(f"{file_hash}.*.md"):
        try:
            p.unlink()
            removed += 1
        except OSError as e:
            logger.warning("purge_cache_by_hash unlink %s failed: %s", p, e)
    return removed


# ============================================================
# Parser
# ============================================================
_LLAMAPARSE_BASE = "https://api.cloud.llamaindex.ai/api/v1/parsing"
_POLL_INTERVAL = 2
_POLL_TIMEOUT = 300

# HANDOFF Lesson 1: LlamaParse renamed parse_mode enum.
# Friendly aliases → actual API values (so .env stays readable).
_MODE_ALIASES = {
    "fast": "parse_page_without_llm",
    "balanced": "parse_page_with_llm",
    "premium": "parse_page_with_lvm",
    "accurate": "parse_page_with_agent",
}


def _resolve_mode(mode: str) -> str:
    """Map friendly mode names to LlamaParse API enum. Pass-through if already valid."""
    return _MODE_ALIASES.get(mode.lower(), mode)


@retry_with_backoff(max_attempts=3, base_delay=2.0)
def _parse_via_llamaparse(
    filepath: str,
    mode: str = "balanced",
    language: str = "th",
    progress_callback=None,
) -> str:
    """Sync REST client for LlamaParse (no SDK dependency).

    v10.0.1 — switched from `llama-parse` SDK to direct REST API to avoid
    version-conflict hell in the llama-index ecosystem. Three-step flow per
    llamaparse_guide.md section 9: upload → poll → fetch markdown.

    v10.0.3 — progress_callback(step: str, pct: int|None) called at each phase:
      "ส่งไฟล์ไป LlamaParse"           (10%)
      "LlamaParse กำลังประมวลผล (Ns)"  (None — Pct unknown)
      "ดาวน์โหลด markdown"             (90%)

    Wrapped in retry_with_backoff — transient 429/503/timeout are retried,
    deterministic 400/401 errors raise immediately.
    """
    import time
    import httpx

    if not LLAMA_CLOUD_API_KEY:
        raise RuntimeError("LLAMA_CLOUD_API_KEY not set")

    def _emit(step, pct=None):
        if progress_callback is None:
            return
        try:
            progress_callback(step, pct)
        except Exception as e:
            logger.debug("LlamaParse progress_callback error: %s", e)

    headers = {"Authorization": f"Bearer {LLAMA_CLOUD_API_KEY}"}
    filename = os.path.basename(filepath)
    api_mode = _resolve_mode(mode)

    # v10.0.14 — wrap httpx calls ใน Client() context manager
    # share connection pool ระหว่าง upload + poll + fetch (3 HTTP calls ไป host เดียวกัน)
    # → ใช้ TCP connection เดิม, auto-close ตอนออกจาก block, ไม่มี resource leak.
    with httpx.Client(timeout=120) as client:
        # Step 1: upload
        _emit("ส่งไฟล์ไป LlamaParse", 10)
        with open(filepath, "rb") as f:
            files = {"file": (filename, f, "application/pdf")}
            data = {"parse_mode": api_mode, "language": language}
            r = client.post(
                f"{_LLAMAPARSE_BASE}/upload",
                headers=headers, files=files, data=data,
            )
        r.raise_for_status()
        job_id = r.json()["id"]
        logger.info("LlamaParse job=%s (mode=%s, file=%s)", job_id, mode, filename)

        # Step 2: poll — emit progress per attempt so UI sees forward motion.
        # pct=None per TC-1 (don't fake progress when LlamaParse doesn't tell us %).
        elapsed = 0
        _emit(f"LlamaParse กำลังประมวลผล (0s)", None)
        while elapsed < _POLL_TIMEOUT:
            time.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL
            r = client.get(f"{_LLAMAPARSE_BASE}/job/{job_id}", headers=headers, timeout=30)
            r.raise_for_status()
            status = r.json().get("status", "").upper()
            _emit(f"LlamaParse กำลังประมวลผล ({elapsed}s, status={status.lower() or 'pending'})", None)
            if status == "SUCCESS":
                break
            if status in ("ERROR", "FAILED", "CANCELLED"):
                raise RuntimeError(f"LlamaParse job {job_id} {status}: {r.json()}")
        else:
            raise TimeoutError(f"LlamaParse job {job_id} not done after {_POLL_TIMEOUT}s")

        # Step 3: fetch markdown
        _emit("ดาวน์โหลด markdown", 90)
        r = client.get(f"{_LLAMAPARSE_BASE}/job/{job_id}/result/markdown", headers=headers, timeout=60)
        r.raise_for_status()
        md = r.json().get("markdown", "")
        return md.strip()


def parse_pdf(filepath: str, language: str = "th", progress_callback=None) -> str:
    """Public entry -- parse PDF via LlamaParse with disk-cache.

    Args:
        filepath: absolute path to a .pdf on disk
        language: "th" / "en" (LlamaParse OCR hint)
        progress_callback: optional sync callable (step:str, pct:int|None) -- forwarded
                           to _parse_via_llamaparse so the upload tray gets live
                           "LlamaParse กำลังประมวลผล (Ns)" updates per poll.

    Returns:
        markdown text. Caller should treat the empty string as a soft failure
        and trigger fallback.

    Raises:
        RuntimeError if llama-parse not installed.
        Other exceptions on auth / quota -- caller can catch + fallback.
    """
    if not LLAMA_CLOUD_API_KEY:
        raise RuntimeError("LLAMA_CLOUD_API_KEY not set")

    mode = LLAMA_PARSE_MODE
    file_hash = _hash_file(filepath)

    cached = cache_get(file_hash, mode)
    if cached is not None:
        logger.info("llamaparse cache hit: %s (%s)", os.path.basename(filepath), mode)
        return cached

    logger.info("llamaparse parse: %s (mode=%s, lang=%s)", os.path.basename(filepath), mode, language)
    text = _parse_via_llamaparse(filepath, mode=mode, language=language, progress_callback=progress_callback)

    if text:
        cache_set(file_hash, mode, text)
    return text


# ============================================================
# Cost estimate (used by /api/admin/extraction-stats)
# ============================================================
_CREDITS_PER_PAGE = {
    "fast": 1, "balanced": 3, "premium": 15, "accurate": 45,
}


def estimate_cost_cents(num_pages: int, mode: Optional[str] = None) -> int:
    """Estimate satang (1/100 baht) for a parse job. Pro plan ~b0.001/credit."""
    mode = mode or LLAMA_PARSE_MODE
    credits = num_pages * _CREDITS_PER_PAGE.get(mode, 3)
    # Pro plan: $50/mo for 50k credits -- assume b35/USD -> b1750 / 50000 credits
    # = b0.035/credit = 3.5 satang/credit
    return int(credits * 3.5)
