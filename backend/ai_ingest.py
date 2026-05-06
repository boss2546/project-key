"""AI multimodal ingestion via Google Gemini Files API (v9.0.0 Phase B v2).

Routes files ที่ Tesseract/Pillow ทำไม่ได้ดี → Google Gemini Vision/Audio/Video API:
- Audio (mp3/wav/m4a/flac/aac/ogg) → transcribe
- Video (mp4/mov/mkv/webm) → analyze frames + extract speech
- Smart image (HEIC ที่ Tesseract อ่านไม่ออก) → Vision describe + OCR

ใช้ google-genai SDK (Gemini direct, ไม่ผ่าน OpenRouter เพราะ OpenRouter รองรับ
multimodal จำกัด)

Architecture decisions (locked 2026-05-07):
  Q1: Files API mode — upload → file_id → reference (auto-delete 48hr)
  Q2: Audio chunk — Gemini handles up to 60min in single call (no chunking needed)
  Q3: Video — full file via Files API (Gemini supports up to 1hr video)
  Q4: Cost gate — uses ai_summary_limit_monthly quota (1 ingest = 1 summary count)
  Q5: Privacy — caller must check user disclosed before calling (frontend modal)
  Q6: Fallback — return [bracket-marker], don't auto-retry, user uses retry button

Configuration:
  GOOGLE_API_KEY env var required. Without it → returns "[AI ingest not configured]"
  marker (graceful degradation, no crash).

Cost (Gemini Flash multimodal):
  Audio: ~$0.0003/second (5min file ≈ $0.09)
  Video: ~$0.001/second (5min video ≈ $0.30)
  Image: ~$0.0001/image (negligible)
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Feature detection ──────────────────────────────────────────────

_HAS_GEMINI = False
_genai_client = None
try:
    from google import genai
    _api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if _api_key:
        _genai_client = genai.Client(api_key=_api_key)
        _HAS_GEMINI = True
        logger.info("Gemini multimodal API enabled (google-genai SDK)")
    else:
        logger.warning("GOOGLE_API_KEY not set — AI multimodal ingestion disabled")
except ImportError:
    logger.warning("google-genai SDK not installed — AI multimodal disabled")


# ─── Format groups ───────────────────────────────────────────────────

AUDIO_FORMATS = {"mp3", "wav", "m4a", "flac", "aac", "ogg", "opus", "wma"}
VIDEO_FORMATS = {"mp4", "mov", "mkv", "webm", "avi", "wmv", "flv", "m4v", "3gp"}
AI_VISION_FORMATS = set()  # reserved for Phase B v3 (smart image describe)

ALL_AI_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS | AI_VISION_FORMATS


# ─── Public API ──────────────────────────────────────────────────────


def is_ai_format(filetype: str) -> bool:
    """True ถ้า filetype ต้องใช้ AI multimodal ingest (audio/video)."""
    return filetype.lower() in ALL_AI_FORMATS


def is_available() -> bool:
    """True ถ้า GOOGLE_API_KEY set + google-genai SDK installed."""
    return _HAS_GEMINI


async def ingest_via_ai(filepath: str, filetype: str) -> str:
    """หลักของ AI ingest — route ไป Gemini Files API ตาม format.

    Returns extracted text (transcript / description / analysis).
    On failure: returns "[AI ingest error: ...]" marker (compatible กับ
    classify_extraction_status — จะ flag เป็น ocr_failed)

    Args:
        filepath: absolute path บน disk
        filetype: extension (lowercase, no dot) — e.g. "mp3", "mp4"
    """
    ext = filetype.lower()

    if not _HAS_GEMINI:
        return "[AI ingest not configured: GOOGLE_API_KEY env var required]"

    try:
        if ext in AUDIO_FORMATS:
            return await _ingest_audio(filepath, ext)
        elif ext in VIDEO_FORMATS:
            return await _ingest_video(filepath, ext)
        elif ext in AI_VISION_FORMATS:
            return await _ingest_image_smart(filepath, ext)
        else:
            return f"[AI ingest unsupported format: {ext}]"
    except Exception as e:
        logger.error(f"AI ingest failed for {filepath}: {e}", exc_info=True)
        return f"[AI ingest error: {type(e).__name__}: {str(e)[:200]}]"


# ─── Internal: Gemini Files API workflow ─────────────────────────────


async def _upload_to_gemini(filepath: str) -> object:
    """Upload file to Gemini Files API → returns File object (id valid 48hr).

    Sync upload — Gemini SDK ไม่มี true async file upload as of late 2026.
    Wrapped in async function for caller convenience.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _genai_client.files.upload(file=filepath),
    )


async def _ingest_audio(filepath: str, ext: str) -> str:
    """Transcribe audio file via Gemini Audio understanding.

    Gemini Flash supports audio up to 60 minutes in single call.
    For longer audio: caller should split first (not implemented yet).
    """
    logger.info(f"AI audio ingest: {os.path.basename(filepath)} ({ext})")
    file_obj = await _upload_to_gemini(filepath)

    prompt = (
        "Transcribe this audio file completely. "
        "Output the transcription in the original language (Thai or English). "
        "If there are multiple speakers, mark them as Speaker 1/2/etc. "
        "Include timestamps every ~30 seconds in [HH:MM:SS] format. "
        "If music or sound effects are present without speech, briefly describe them."
    )

    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: _genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[file_obj, prompt],
        ),
    )
    text = response.text or "[AI audio: no transcription generated]"
    logger.info(f"AI audio done: {len(text)} chars from {os.path.basename(filepath)}")
    return text


async def _ingest_video(filepath: str, ext: str) -> str:
    """Analyze video — frames + audio transcription combined.

    Gemini Flash supports video up to ~1 hour. Returns:
    - Visual description per scene (every ~30s)
    - Spoken content transcribed
    - On-screen text extracted (slides, captions)
    """
    logger.info(f"AI video ingest: {os.path.basename(filepath)} ({ext})")
    file_obj = await _upload_to_gemini(filepath)

    prompt = (
        "Analyze this video comprehensively:\n"
        "1. Transcribe all spoken content (Thai or English original language)\n"
        "2. Describe key visual scenes with [HH:MM:SS] timestamps every ~30s\n"
        "3. Extract any on-screen text (titles, captions, slides)\n"
        "4. Note speaker changes if multiple people\n"
        "Format as structured markdown with sections."
    )

    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: _genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[file_obj, prompt],
        ),
    )
    text = response.text or "[AI video: no analysis generated]"
    logger.info(f"AI video done: {len(text)} chars from {os.path.basename(filepath)}")
    return text


async def _ingest_image_smart(filepath: str, ext: str) -> str:
    """Smart image description via Gemini Vision — better than OCR for charts/diagrams.

    Reserved for Phase B v3 — currently HEIC/etc. use Tesseract OCR.
    """
    return "[AI vision not yet implemented in Phase B v2]"
