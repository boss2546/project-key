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

# Gemini File-API model สำหรับ audio/video transcription.
# Why constant: Google deprecate gemini-2.0-flash (2026-05-10) → 404 NOT_FOUND
# ทุก ingest. ตั้ง override ด้วย env GEMINI_FILE_MODEL ถ้าต้องเปลี่ยนเร็ว.
GEMINI_FILE_MODEL = os.getenv("GEMINI_FILE_MODEL", "gemini-2.5-flash")

_HAS_GEMINI = False
_genai_client = None
try:
    from google import genai
    _api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if _api_key:
        _genai_client = genai.Client(api_key=_api_key)
        _HAS_GEMINI = True
        logger.info(f"Gemini multimodal API enabled (model={GEMINI_FILE_MODEL})")
    else:
        logger.warning("GOOGLE_API_KEY not set — AI multimodal ingestion disabled")
except ImportError:
    logger.warning("google-genai SDK not installed — AI multimodal disabled")


# ─── Format groups ───────────────────────────────────────────────────

AUDIO_FORMATS = {"mp3", "wav", "m4a", "flac", "aac", "ogg", "opus", "wma"}
VIDEO_FORMATS = {"mp4", "mov", "mkv", "webm", "avi", "wmv", "flv", "m4v", "3gp"}
# v9.4.2 — Vision formats: Gemini 2.5 Flash อ่านข้อความในรูป + อธิบายภาพได้แม่นกว่า
# Tesseract (รองรับไทย+อังกฤษ native, ไม่ต้องลง binary). ก่อนหน้านี้รูปไป Tesseract เท่านั้น
# → ถ้าไม่มี text → "[Image: no text detected]" → user เห็นแต่ marker, ไม่มีข้อมูลภาพ.
AI_VISION_FORMATS = {"jpg", "jpeg", "png", "webp", "heic", "heif", "gif", "bmp", "tiff", "tif"}

ALL_AI_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS | AI_VISION_FORMATS


# ─── Public API ──────────────────────────────────────────────────────


def is_ai_format(filetype: str) -> bool:
    """True ถ้า filetype ต้องใช้ AI multimodal ingest (audio/video)."""
    return filetype.lower() in ALL_AI_FORMATS


def is_available() -> bool:
    """True ถ้า GOOGLE_API_KEY set + google-genai SDK installed."""
    return _HAS_GEMINI


async def _safe_async_progress(progress_callback, step: str, pct=None) -> None:
    """v9.4.0 helper — เรียก async progress_callback แบบปลอดภัย."""
    if progress_callback is None:
        return
    try:
        await progress_callback(step, pct)
    except Exception as e:
        logger.debug(f"async progress_callback raised (non-fatal): {e}")


async def ingest_via_ai(filepath: str, filetype: str, progress_callback=None) -> str:
    """หลักของ AI ingest — route ไป Gemini Files API ตาม format.

    Returns extracted text (transcript / description / analysis).
    On failure: returns "[AI ingest error: ...]" marker (compatible กับ
    classify_extraction_status — จะ flag เป็น ocr_failed)

    Args:
        filepath: absolute path บน disk
        filetype: extension (lowercase, no dot) — e.g. "mp3", "mp4"
        progress_callback: optional async function(step, pct) — TC-1: pct=None ถ้าไม่รู้
                           Gemini transcribe ไม่ stream % ได้ → ใช้ขั้นตอน 3 ขั้น
                           (upload → transcribe → done) แทนการ fake %.
                           Default=None → backward compat (main.py:580 + 1768).
    """
    ext = filetype.lower()

    if not _HAS_GEMINI:
        return "[AI ingest not configured: GOOGLE_API_KEY env var required]"

    try:
        if ext in AUDIO_FORMATS:
            text = await _ingest_audio(filepath, ext, progress_callback)
        elif ext in VIDEO_FORMATS:
            text = await _ingest_video(filepath, ext, progress_callback)
        elif ext in AI_VISION_FORMATS:
            text = await _ingest_image_smart(filepath, ext, progress_callback)
        else:
            return f"[AI ingest unsupported format: {ext}]"
    except Exception as e:
        logger.error(f"AI ingest failed for {filepath}: {e}", exc_info=True)
        return f"[AI ingest error: {type(e).__name__}: {str(e)[:200]}]"

    # v9.3.4 — strip lone surrogates from Gemini output before returning.
    # Gemini occasionally emits surrogate halves when transcribing audio/video
    # that contains rare unicode (emoji combining sequences, malformed input).
    # Defense-in-depth at boundary so DB writes never crash on encode UTF-8.
    from .extraction import strip_surrogates
    return strip_surrogates(text)


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


async def _wait_for_file_active(file_obj, progress_callback=None, timeout: int = 300) -> object:
    """Poll Gemini until file.state == ACTIVE before calling generate_content.

    Why: video uploads ขึ้น state=PROCESSING ก่อน → ใช้ทันที = 400 FAILED_PRECONDITION
    "File X is not in an ACTIVE state". Audio เล็ก-รูป มัก ACTIVE ทันที, video ใหญ่ใช้ 5-30s.
    """
    import asyncio
    state = getattr(file_obj, "state", None)
    state_name = getattr(state, "name", str(state)) if state is not None else "UNKNOWN"
    if state_name == "ACTIVE":
        return file_obj
    loop = asyncio.get_event_loop()
    elapsed = 0
    poll_interval = 2
    while elapsed < timeout:
        await _safe_async_progress(
            progress_callback, f"Gemini เตรียมไฟล์ ({state_name}, {elapsed}s)", None
        )
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
        refreshed = await loop.run_in_executor(
            None, lambda: _genai_client.files.get(name=file_obj.name)
        )
        state = getattr(refreshed, "state", None)
        state_name = getattr(state, "name", str(state)) if state is not None else "UNKNOWN"
        if state_name == "ACTIVE":
            return refreshed
        if state_name == "FAILED":
            raise RuntimeError(f"Gemini file processing FAILED: {file_obj.name}")
    raise TimeoutError(
        f"Gemini file not ACTIVE after {timeout}s (last state={state_name})"
    )


async def _ingest_audio(filepath: str, ext: str, progress_callback=None) -> str:
    """Transcribe audio file via Gemini Audio understanding.

    Gemini Flash supports audio up to 60 minutes in single call.
    For longer audio: caller should split first (not implemented yet).

    v9.4.0 progress reports (TC-1: pct=None ระหว่าง Gemini transcribe):
      "อัปโหลดไป Gemini" 30 → "Gemini ถอดเสียง" None → "รับผลลัพธ์" 90
    """
    logger.info(f"AI audio ingest: {os.path.basename(filepath)} ({ext})")

    await _safe_async_progress(progress_callback, "อัปโหลดไป Gemini Files API", 30)
    file_obj = await _upload_to_gemini(filepath)
    file_obj = await _wait_for_file_active(file_obj, progress_callback)

    prompt = (
        "Transcribe this audio file completely. "
        "Output the transcription in the original language (Thai or English). "
        "If there are multiple speakers, mark them as Speaker 1/2/etc. "
        "Include timestamps every ~30 seconds in [HH:MM:SS] format. "
        "If music or sound effects are present without speech, briefly describe them."
    )

    # TC-1: pct=None — Gemini ไม่ stream progress, ห้ามมั่ว %
    await _safe_async_progress(progress_callback, f"Gemini ถอดเสียง ({ext})", None)

    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: _genai_client.models.generate_content(
            model=GEMINI_FILE_MODEL,
            contents=[file_obj, prompt],
        ),
    )
    text = response.text or "[AI audio: no transcription generated]"
    logger.info(f"AI audio done: {len(text)} chars from {os.path.basename(filepath)}")
    await _safe_async_progress(progress_callback, "รับผลลัพธ์จาก Gemini", 90)
    return text


async def _ingest_video(filepath: str, ext: str, progress_callback=None) -> str:
    """Analyze video — frames + audio transcription combined.

    Gemini Flash supports video up to ~1 hour. Returns:
    - Visual description per scene (every ~30s)
    - Spoken content transcribed
    - On-screen text extracted (slides, captions)

    v9.4.0 progress reports (same 3-stage pattern as audio).
    """
    logger.info(f"AI video ingest: {os.path.basename(filepath)} ({ext})")

    await _safe_async_progress(progress_callback, "อัปโหลดวิดีโอไป Gemini", 25)
    file_obj = await _upload_to_gemini(filepath)
    file_obj = await _wait_for_file_active(file_obj, progress_callback)

    prompt = (
        "Analyze this video comprehensively:\n"
        "1. Transcribe all spoken content (Thai or English original language)\n"
        "2. Describe key visual scenes with [HH:MM:SS] timestamps every ~30s\n"
        "3. Extract any on-screen text (titles, captions, slides)\n"
        "4. Note speaker changes if multiple people\n"
        "Format as structured markdown with sections."
    )

    # TC-1: pct=None — video analysis ใช้เวลานานกว่า audio
    await _safe_async_progress(progress_callback, f"Gemini วิเคราะห์วิดีโอ ({ext})", None)

    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: _genai_client.models.generate_content(
            model=GEMINI_FILE_MODEL,
            contents=[file_obj, prompt],
        ),
    )
    text = response.text or "[AI video: no analysis generated]"
    logger.info(f"AI video done: {len(text)} chars from {os.path.basename(filepath)}")
    await _safe_async_progress(progress_callback, "รับผลลัพธ์จาก Gemini", 90)
    return text


async def _ingest_image_smart(filepath: str, ext: str, progress_callback=None) -> str:
    """Vision describe + OCR text-in-image via Gemini 2.5 Flash.

    Combines: (1) visual scene description (2) extract any embedded text (Thai+English)
    (3) describe charts/diagrams. ไม่ต้อง wait_for_active เพราะรูปเล็ก state=ACTIVE
    ทันทีหลัง upload, แต่ยังเรียกเพื่อ safety (no-op ถ้า ACTIVE แล้ว).

    Returns markdown text. On error returns "[AI vision error: ...]" marker.
    """
    logger.info(f"AI image ingest: {os.path.basename(filepath)} ({ext})")

    await _safe_async_progress(progress_callback, "อัปโหลดรูปไป Gemini", 30)
    file_obj = await _upload_to_gemini(filepath)
    file_obj = await _wait_for_file_active(file_obj, progress_callback, timeout=60)

    prompt = (
        "Analyze this image comprehensively in markdown:\n"
        "1. **Description** — describe what's in the image (objects, people, scene, mood)\n"
        "2. **Text content** — extract ALL visible text exactly as shown "
        "(preserve original language: Thai, English, etc.)\n"
        "3. **Type** — photograph / screenshot / diagram / chart / document / artwork\n"
        "4. **Notable details** — any context useful for search later "
        "(brand names, places, dates, key numbers, etc.)\n"
        "Use Thai if image content is Thai, English otherwise. Skip sections that don't apply."
    )

    await _safe_async_progress(progress_callback, f"Gemini วิเคราะห์รูป ({ext})", None)

    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: _genai_client.models.generate_content(
            model=GEMINI_FILE_MODEL,
            contents=[file_obj, prompt],
        ),
    )
    text = response.text or "[AI image: no description generated]"
    logger.info(f"AI image done: {len(text)} chars from {os.path.basename(filepath)}")
    await _safe_async_progress(progress_callback, "รับผลลัพธ์จาก Gemini", 90)
    return text
