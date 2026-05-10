"""Upload worker — async background processor (v9.4.0).

โมดูลนี้ทำหน้าที่:
1. Poll DB queue ทุก 2 วินาที หาไฟล์ที่ status='queued'
2. Atomic claim 1 ไฟล์ (round-robin per-user + priority by ext-class · ADR-006)
3. รัน extract_text หรือ ai_ingest พร้อม progress callback
4. Update DB row ตอนเสร็จ + push ไป Drive (BYOS)
5. Recovery — reset stale 'extracting' (> 30 นาที) → 'queued' ตอน startup
6. Heartbeat — เขียน timestamp ไป file ทุก loop iteration
7. Track rolling avg extract time per priority class (TC-4 truthful estimated_wait)

⚠️ ห้ามทำ:
- Multi-process parallel (single in-process task เท่านั้น)
- Block event loop ด้วย sync IO (extract_text ต้อง wrap asyncio.to_thread)
- Update progress ถี่กว่า PROGRESS_DB_THROTTLE_SEC (กัน DB lock)

Refs: plans/upload-queue-v9.4.0.md
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy import select, update

from .database import AsyncSessionLocal, File
from .extraction import extract_text, classify_extraction_status, strip_surrogates
from .duplicate_detector import compute_content_hash
from .ai_ingest import ingest_via_ai, is_ai_format

logger = logging.getLogger(__name__)

# ─── Tunable constants (env-overridable) ─────────────────────────────
POLL_INTERVAL_SEC = float(os.getenv("UPLOAD_WORKER_POLL_SEC", "2.0"))
STALE_EXTRACT_TIMEOUT_SEC = int(os.getenv("UPLOAD_STALE_TIMEOUT_SEC", "1800"))  # 30 min
MAX_RETRY_ATTEMPTS = int(os.getenv("UPLOAD_MAX_RETRY", "3"))
PROGRESS_DB_THROTTLE_SEC = 1.5  # อย่า update DB ถี่กว่านี้ — กัน lock
HEARTBEAT_FILE = Path(os.getenv("UPLOAD_HEARTBEAT_FILE", "data/worker_heartbeat.txt"))
HEARTBEAT_STALE_SEC = 30  # ถ้า heartbeat เก่ากว่านี้ → /healthz returns 503
WORKER_DISABLED = os.getenv("UPLOAD_WORKER_DISABLED", "").lower() in ("1", "true", "yes")

# ─── Module state ─────────────────────────────────────────────────────
_worker_task: Optional[asyncio.Task] = None
_shutdown_event: Optional[asyncio.Event] = None
_worker_started_at: Optional[datetime] = None

# Rolling average per priority class (TC-4 truthful estimated_wait)
# Updated atomically after each successful extract via update_avg_sec()
_AVG_EXTRACT_SEC: dict[int, float] = {1: 1.0, 2: 15.0, 3: 90.0}
_AVG_SAMPLE_COUNT: dict[int, int] = {1: 0, 2: 0, 3: 0}

# ─── Ext → priority class mapping (ADR-006 fairness sort) ────────────
PRIORITY_CLASS_FAST = frozenset({  # priority 1 — sub-second extract
    "txt", "md", "csv", "png", "jpg", "jpeg", "webp", "heic", "heif",
    "gif", "bmp", "tiff", "tif", "py", "js", "ts", "jsx", "tsx", "css",
    "scss", "less", "sass", "xml", "yaml", "yml", "toml", "ini", "env",
    "conf", "cfg", "sh", "bash", "zsh", "bat", "ps1", "sql", "java",
    "kt", "swift", "c", "cpp", "h", "hpp", "cs", "go", "rs", "rb", "php",
    "log", "tsv", "vue", "svelte", "json", "html", "rtf",
})
PRIORITY_CLASS_DOC = frozenset({"pdf", "docx", "xlsx", "pptx"})  # priority 2
# audio/video → priority 3 (default)


def get_priority_class(ext: str) -> int:
    """แปลง ext → priority class (1=fast, 2=doc, 3=audio/video)."""
    e = (ext or "").lower()
    if e in PRIORITY_CLASS_FAST:
        return 1
    if e in PRIORITY_CLASS_DOC:
        return 2
    return 3


def get_avg_sec(priority_class: int) -> float:
    """คืน rolling avg extract time (seconds) สำหรับ priority class นี้.

    Used by /api/upload เพื่อคำนวณ estimated_wait_sec ที่ truthful (TC-4).
    """
    return _AVG_EXTRACT_SEC.get(priority_class, 30.0)


def update_avg_sec(priority_class: int, duration_sec: float) -> None:
    """Update rolling avg ด้วย exponential smoothing (alpha=0.2)."""
    if duration_sec < 0:
        return
    cur = _AVG_EXTRACT_SEC.get(priority_class, duration_sec)
    new = 0.8 * cur + 0.2 * duration_sec
    _AVG_EXTRACT_SEC[priority_class] = round(new, 2)
    _AVG_SAMPLE_COUNT[priority_class] = _AVG_SAMPLE_COUNT.get(priority_class, 0) + 1


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

async def start_worker() -> None:
    """เรียกตอน FastAPI startup. Idempotent (no-op ถ้า worker รันอยู่แล้ว).

    Hatch: ตั้ง env UPLOAD_WORKER_DISABLED=true เพื่อปิด worker (rollback Tier 2).
    """
    global _worker_task, _shutdown_event, _worker_started_at

    if WORKER_DISABLED:
        logger.warning("upload_worker.disabled — env UPLOAD_WORKER_DISABLED set")
        return

    if _worker_task and not _worker_task.done():
        logger.info("upload_worker.already_running — skip")
        return

    _shutdown_event = asyncio.Event()
    await _recover_stale_jobs()
    _worker_started_at = datetime.utcnow()
    _worker_task = asyncio.create_task(_worker_loop(), name="upload_worker")
    logger.info("upload_worker.started")


async def stop_worker() -> None:
    """เรียกตอน FastAPI shutdown. รอ task เสร็จ (max 5s) แล้วยอมแพ้."""
    if _shutdown_event:
        _shutdown_event.set()
    if _worker_task:
        try:
            await asyncio.wait_for(_worker_task, timeout=5.0)
            logger.info("upload_worker.stopped")
        except asyncio.TimeoutError:
            logger.warning("upload_worker.stop_timeout — task did not finish in 5s")


def get_worker_health() -> dict:
    """ใช้ใน /api/healthz/queue (§9.1).

    Returns: {status, uptime_sec, last_heartbeat, concurrency, avg_extract_sec_by_class}
    """
    now = datetime.utcnow()
    uptime = int((now - _worker_started_at).total_seconds()) if _worker_started_at else 0
    last_hb = _read_heartbeat()
    is_alive = bool(last_hb and (now - last_hb).total_seconds() < HEARTBEAT_STALE_SEC)

    if WORKER_DISABLED:
        status = "disabled"
    elif is_alive:
        status = "running"
    elif _worker_task and _worker_task.done():
        status = "crashed"
    else:
        status = "stopped"

    return {
        "status": status,
        "uptime_sec": uptime,
        "last_heartbeat": last_hb.isoformat() + "Z" if last_hb else None,
        "concurrency": 1,
        "avg_extract_sec_by_class": {str(k): v for k, v in _AVG_EXTRACT_SEC.items()},
    }


# ═══════════════════════════════════════════════════════════════════
# Internal — main loop + claim + process
# ═══════════════════════════════════════════════════════════════════

async def _worker_loop() -> None:
    """Main loop — poll DB, claim 1 job, process, repeat. Stops on shutdown event."""
    while not _shutdown_event.is_set():
        try:
            _write_heartbeat()
            claimed = await _claim_next_job()
            if claimed is None:
                # Idle — sleep until shutdown OR next poll interval
                try:
                    await asyncio.wait_for(_shutdown_event.wait(), timeout=POLL_INTERVAL_SEC)
                except asyncio.TimeoutError:
                    pass
                continue
            await _process_job(claimed)
        except asyncio.CancelledError:
            logger.info("upload_worker.cancelled")
            return
        except Exception as e:
            # Defense: log + sleep + continue (อย่า die เพราะ exception เดียว)
            logger.error(
                "upload_worker.loop_error",
                extra={
                    "event": "loop_error",
                    "error_class": type(e).__name__,
                    "error_message": str(e)[:200],
                },
                exc_info=True,
            )
            await asyncio.sleep(POLL_INTERVAL_SEC)


def _write_heartbeat() -> None:
    """Write timestamp ไป heartbeat file. Creates parent dir ถ้ายังไม่มี."""
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.write_text(datetime.utcnow().isoformat())
    except Exception as e:
        # Non-fatal — heartbeat fail แค่ทำให้ /healthz รายงานผิด
        logger.warning(
            "upload_worker.heartbeat_write_failed",
            extra={"error": str(e)[:100]},
        )


def _read_heartbeat() -> Optional[datetime]:
    """อ่าน timestamp จาก heartbeat file. None ถ้าหาย/อ่านไม่ได้."""
    try:
        if not HEARTBEAT_FILE.exists():
            return None
        return datetime.fromisoformat(HEARTBEAT_FILE.read_text().strip())
    except Exception:
        return None


async def _claim_next_job() -> Optional[dict]:
    """Atomic claim ของไฟล์ที่ดีที่สุดใน queue.

    Sort key = (user_pos ASC, priority_class ASC, queued_at ASC):
      - user_pos: ROW_NUMBER() per user → round-robin (ADR-006 fairness)
      - priority_class: 1=fast, 2=doc, 3=audio/video (ADR ext-class priority)
      - queued_at: tie-breaker

    M-10 fix: ใช้ SQLAlchemy ORM (select + sort ใน Python + atomic UPDATE)
    แทน raw SQL f-string concat — ปลอดภัยกว่า + อ่านง่ายกว่า.
    Performance OK เพราะ queue depth มัก < 1000 + index hit.
    """
    async with AsyncSessionLocal() as db:
        # 1. หา candidates ทั้งหมดที่ queued — read-only, cheap, index hit
        rows = await db.execute(
            select(
                File.id, File.user_id, File.filename, File.filetype,
                File.raw_path, File.queued_at, File.attempt_count,
            )
            .where(File.processing_status == "queued")
            .order_by(File.queued_at.asc())
        )
        candidates = rows.fetchall()
        if not candidates:
            return None

        # 2. Compute (user_pos, priority_class, queued_at) ใน Python
        per_user_count: dict[str, int] = defaultdict(int)
        ranked: list[tuple] = []
        for c in candidates:
            per_user_count[c.user_id] += 1
            user_pos = per_user_count[c.user_id]
            priority = get_priority_class(c.filetype or "")
            ranked.append((user_pos, priority, c.queued_at, c))

        # 3. Sort: user_pos ASC (round-robin) → priority ASC → queued_at ASC
        ranked.sort(key=lambda r: (r[0], r[1], r[2] or datetime.utcnow()))
        chosen = ranked[0][3]

        # 4. Atomic claim — UPDATE WHERE status='queued' guards race
        # rowcount=1 success · rowcount=0 lost race (defense; worker=1 ไม่น่าเกิด)
        now = datetime.utcnow()
        result = await db.execute(
            update(File)
            .where(File.id == chosen.id, File.processing_status == "queued")
            .values(
                processing_status="extracting",
                extract_started_at=now,
                progress_step="เตรียมเริ่มประมวลผล",
                progress_pct=None,
            )
        )
        await db.commit()

        if result.rowcount != 1:
            logger.warning(
                "upload_worker.claim_lost_race",
                extra={"file_id": chosen.id, "rowcount": result.rowcount},
            )
            return None

        wait_sec = (now - chosen.queued_at).total_seconds() if chosen.queued_at else 0
        priority = ranked[0][1]
        logger.info(
            "upload_worker.claim_job",
            extra={
                "event": "claim_job",
                "file_id": chosen.id,
                "user_id": chosen.user_id,
                "filetype": chosen.filetype,
                "wait_time_sec": round(wait_sec, 2),
                "priority_class": priority,
                "attempt_count": chosen.attempt_count or 0,
            },
        )

        return {
            "id": chosen.id,
            "user_id": chosen.user_id,
            "filename": chosen.filename,
            "filetype": chosen.filetype,
            "raw_path": chosen.raw_path,
            "priority_class": priority,
            "attempt_count": chosen.attempt_count or 0,
        }


async def _process_job(job: dict) -> None:
    """รัน extract สำหรับ 1 ไฟล์ + update progress ระหว่างทาง.

    On success: status='uploaded' + extracted_text + content_hash + Drive push (BYOS)
    On failure: status='error' + extract_error TH message (TC-5)
    """
    file_id = job["id"]
    raw_path = job["raw_path"]
    ext = (job["filetype"] or "").lower()
    started = time.monotonic()

    # Throttled progress writer — กัน DB write spam
    last_progress_write = 0.0

    async def _async_report(step: str, pct: Optional[int] = None) -> None:
        """Report progress (async caller — ai_ingest)."""
        nonlocal last_progress_write
        now = time.monotonic()
        if now - last_progress_write < PROGRESS_DB_THROTTLE_SEC:
            return
        last_progress_write = now
        await _write_progress(file_id, step, pct)

    def _sync_report(step: str, pct: Optional[int] = None) -> None:
        """Report progress (sync caller — extract_text via to_thread).

        Schedule async write via run_coroutine_threadsafe (cross-thread safe).
        """
        nonlocal last_progress_write
        now = time.monotonic()
        if now - last_progress_write < PROGRESS_DB_THROTTLE_SEC:
            return
        last_progress_write = now
        try:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                _write_progress(file_id, step, pct), loop,
            )
        except Exception as e:
            # Non-fatal — progress write fail แค่ทำให้ tray UI หยุด update
            logger.debug(f"sync_report scheduling error: {e}")

    try:
        await _async_report("เตรียมประมวลผล", 5)

        # Verify raw file ยังอยู่ก่อนเริ่ม
        if not raw_path or not os.path.exists(raw_path):
            raise FileNotFoundError(f"raw file gone: {raw_path}")

        # Route ตาม ext
        if is_ai_format(ext):
            # Audio/video → Gemini multimodal API (async)
            await _async_report("อัปโหลดไป Gemini", 15)
            text = await ingest_via_ai(raw_path, ext, progress_callback=_async_report)
        else:
            # Document/image/text → extract_text (sync) wrap ด้วย to_thread
            await _async_report("กำลังอ่านข้อความในไฟล์", 20)
            text = await asyncio.to_thread(
                extract_text, raw_path, ext, progress_callback=_sync_report,
            )

        # Sanitize + classify (TC-1 boundary)
        text = strip_surrogates(text)
        content_hash = compute_content_hash(text)
        ext_status = classify_extraction_status(text)

        await _async_report("บันทึกผลลัพธ์", 95)

        # Final commit — success path
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(File).where(File.id == file_id).values(
                    extracted_text=text,
                    content_hash=content_hash,
                    extraction_status=ext_status,
                    processing_status="uploaded",
                    progress_step=None,
                    progress_pct=100,
                    extract_completed_at=datetime.utcnow(),
                    extract_error=None,
                )
            )
            await db.commit()

        # Update rolling avg (TC-4)
        duration = time.monotonic() - started
        update_avg_sec(job["priority_class"], duration)

        logger.info(
            "upload_worker.extract_done",
            extra={
                "event": "extract_done",
                "file_id": file_id,
                "duration_sec": round(duration, 2),
                "extraction_status": ext_status,
                "text_length": len(text),
                "priority_class": job["priority_class"],
            },
        )

        # BYOS Drive push (post-extract, best-effort)
        await _push_to_drive_if_byos(file_id)

    except Exception as e:
        duration = time.monotonic() - started
        logger.error(
            "upload_worker.extract_failed",
            extra={
                "event": "extract_failed",
                "file_id": file_id,
                "duration_sec": round(duration, 2),
                "error_class": type(e).__name__,
                "error_message": str(e)[:200],
                "attempt_count": job["attempt_count"],
            },
            exc_info=True,
        )
        await _mark_job_failed(file_id, e)


async def _write_progress(file_id: str, step: str, pct: Optional[int]) -> None:
    """Update progress columns. Throttled โดย caller (1.5s window)."""
    # Validate pct (INV-7: 0-100 หรือ NULL)
    if pct is not None and not (0 <= pct <= 100):
        pct = None
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(File).where(File.id == file_id).values(
                    progress_step=(step or "")[:200],  # safety cap
                    progress_pct=pct,
                )
            )
            await db.commit()
    except Exception as e:
        # Non-fatal — progress write fail = ไม่ update tray แต่ extract ยังเดินต่อ
        logger.warning(
            "upload_worker.progress_write_failed",
            extra={"file_id": file_id, "error": str(e)[:100]},
        )


async def _mark_job_failed(file_id: str, exc: Exception) -> None:
    """Set status='error' + write error CODE (frontend translates)."""
    msg = format_user_error(exc)  # v9.4.3 — now returns CODE, e.g. "ENCRYPTED"
    try:
        async with AsyncSessionLocal() as db:
            # Map CODE → extraction_status (for badge filter + retry button gating)
            ext_status = "ocr_failed"  # default — most codes are retryable
            if msg == "ENCRYPTED":
                ext_status = "encrypted"
            # No current code maps to "unsupported" — extraction_status set elsewhere

            await db.execute(
                update(File).where(File.id == file_id).values(
                    processing_status="error",
                    extraction_status=ext_status,
                    extract_completed_at=datetime.utcnow(),
                    extract_error=msg,
                    progress_step=None,
                    progress_pct=None,
                )
            )
            await db.commit()
    except Exception as e:
        logger.error(
            "upload_worker.mark_failed_error",
            extra={"file_id": file_id, "error": str(e)[:100]},
        )


# v9.4.3 — error CODE → (TH, EN) i18n boundary.
# Why: เดิม format_user_error คืน Thai string ดิบ → EN locale user เห็นไทยใน upload tray.
# Fix: คืน machine code, frontend แปล. ไฟล์เก่าใน DB ที่ยังเก็บ Thai message ดิบ →
# frontend fall back display raw (no break).
ERROR_CODES = {
    "ENCRYPTED":         ("ไฟล์เข้ารหัส — ปลดล็อกก่อนอัปโหลดใหม่",                     "Encrypted file — unlock before re-uploading"),
    "FILE_MISSING":      ("ไฟล์ดิบหายไประหว่างประมวลผล — ต้องอัปโหลดใหม่",             "Raw file lost mid-process — re-upload required"),
    "TIMEOUT":           ("ประมวลผลใช้เวลานานเกินกำหนด — ลองแบ่งไฟล์เล็กลงหรือกดลองใหม่", "Processing timed out — split file or retry"),
    "OUT_OF_MEMORY":     ("ไฟล์ใหญ่เกินที่ระบบรับไหว — ลองแบ่งไฟล์เล็กลง",              "File too large for system memory — split smaller"),
    "ENCODING":          ("ไฟล์มี encoding ผิดปกติ — ลอง re-save เป็น UTF-8 แล้วอัปใหม่", "File encoding invalid — re-save as UTF-8 and retry"),
    "QUOTA_EXCEEDED":    ("Gemini API ใช้เกินโควต้า — รอเดือนหน้าหรือเปลี่ยนแพลน",      "Gemini quota exceeded — wait next month or upgrade plan"),
    "GEMINI_UNAVAILABLE":("Gemini ตอบช้ากว่าปกติ — กดลองใหม่อีกครั้ง",                  "Gemini service degraded — please retry"),
    "GEMINI_AUTH":       ("Gemini API key ไม่ถูกต้อง — ติดต่อแอดมิน",                   "Gemini API key invalid — contact admin"),
    "MODEL_DEPRECATED":  ("AI model ปลด/เปลี่ยนชื่อแล้ว — ติดต่อแอดมินอัปเดต GEMINI_FILE_MODEL", "AI model deprecated — admin must update GEMINI_FILE_MODEL"),
    "FILE_NOT_ACTIVE":   ("Gemini เตรียมไฟล์ไม่ทัน — กดลองใหม่อีกครั้ง",                 "Gemini file not ready — please retry"),
    "PERMISSION_DENIED": ("Gemini API ไม่อนุญาต — ตรวจสอบ key permissions",             "Gemini API denied — check key permissions"),
    "CLIENT_ERROR":      ("Gemini ปฏิเสธคำขอ — กดลองใหม่หรือติดต่อแอดมินถ้ายังไม่หาย",   "Gemini rejected request — retry or contact admin"),
    "OCR_FAIL":          ("OCR engine ขัดข้อง — ลองอัปใหม่หรือใช้ไฟล์ text แทนรูป",     "OCR engine failed — retry or use a text file"),
    "NETWORK":           ("ปัญหาเครือข่าย — กดลองใหม่อีกครั้ง",                          "Network issue — please retry"),
    "UNKNOWN":           ("ประมวลผลล้มเหลว — กดลองใหม่หรือติดต่อแอดมิน",                "Processing failed — retry or contact admin"),
}


def format_user_error(exc: Exception) -> str:
    """Return error CODE (frontend translates via ERROR_CODE_LABELS).

    Codes are stable identifiers stored in File.extract_error column.
    Frontend localizes via ERROR_CODE_LABELS map. Legacy rows with raw Thai
    strings still display correctly via fallback.
    """
    name = type(exc).__name__
    s = str(exc)[:200]
    s_lower = s.lower()

    if "encrypted" in s_lower or "password" in s_lower:
        return "ENCRYPTED"
    if "no such file" in s_lower or name == "FileNotFoundError":
        return "FILE_MISSING"
    if "timeout" in s_lower or "timed out" in s_lower or name == "TimeoutError":
        return "TIMEOUT"
    if name == "MemoryError" or "memory" in s_lower:
        return "OUT_OF_MEMORY"
    if name in ("UnicodeDecodeError", "UnicodeEncodeError"):
        return "ENCODING"
    if "quota" in s_lower or "rate limit" in s_lower or "429" in s:
        return "QUOTA_EXCEEDED"
    if "google" in s_lower and ("503" in s or "unavailable" in s_lower):
        return "GEMINI_UNAVAILABLE"
    if "google" in s_lower and "auth" in s_lower:
        return "GEMINI_AUTH"
    if "404" in s and ("not_found" in s_lower or "no longer available" in s_lower):
        return "MODEL_DEPRECATED"
    if "failed_precondition" in s_lower or "not in an active state" in s_lower:
        return "FILE_NOT_ACTIVE"
    if "permission_denied" in s_lower or "permission denied" in s_lower:
        return "PERMISSION_DENIED"
    if "invalid_argument" in s_lower or name == "ClientError":
        return "CLIENT_ERROR"
    if "tesseract" in s_lower:
        return "OCR_FAIL"
    if "connection" in s_lower or "network" in s_lower:
        return "NETWORK"
    return "UNKNOWN"


async def _recover_stale_jobs() -> None:
    """Reset stuck 'extracting' jobs (extract_started_at เก่ากว่า cutoff) → 'queued'.

    เรียกตอน startup. ป้องกัน orphan rows กรณี server crash กลาง extract.
    """
    cutoff = datetime.utcnow() - timedelta(seconds=STALE_EXTRACT_TIMEOUT_SEC)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(File)
                .where(
                    File.processing_status == "extracting",
                    File.extract_started_at < cutoff,
                )
                .values(
                    processing_status="queued",
                    extract_started_at=None,
                    progress_step=None,
                    progress_pct=None,
                )
            )
            await db.commit()
            if result.rowcount:
                logger.warning(
                    "upload_worker.recovered_stale",
                    extra={
                        "event": "recovered_stale",
                        "count": result.rowcount,
                        "cutoff": cutoff.isoformat(),
                    },
                )
    except Exception as e:
        logger.error(
            "upload_worker.recovery_error",
            extra={"error": str(e)[:200]},
        )


async def _push_to_drive_if_byos(file_id: str) -> None:
    """Drive push หลัง extract เสร็จ — best-effort (Drive = mirror, DB = truth).

    เฉพาะ BYOS user (storage_mode='byos'). non-BYOS = no-op.
    """
    try:
        async with AsyncSessionLocal() as db:
            row = await db.execute(select(File).where(File.id == file_id))
            f = row.scalar_one_or_none()
            if not f or not f.raw_path or not os.path.exists(f.raw_path):
                return

            # Read raw bytes + guess mime (lazy import เพื่อกัน circular)
            from .storage_router import (
                push_extracted_text_to_drive_if_byos,
                push_raw_file_to_drive_if_byos,
            )

            with open(f.raw_path, "rb") as fp:
                contents = fp.read()
            mime = _guess_mime_for_drive(f.filetype)

            drive_id = await push_raw_file_to_drive_if_byos(
                f.user_id, db, f.id, f.filename, contents, mime,
            )
            if drive_id and f.extracted_text:
                await push_extracted_text_to_drive_if_byos(
                    f.user_id, db, f.id, f.extracted_text,
                )
    except Exception as e:
        # Best-effort — Drive push fail ไม่กระทบ extract success
        logger.warning(
            "upload_worker.drive_push_failed",
            extra={"file_id": file_id, "error": str(e)[:200]},
        )


# Mime hint สำหรับ Drive push (ไม่ใช้ main._guess_mime เพื่อกัน circular import)
_MIME_BY_EXT = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "md": "text/markdown",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "csv": "text/csv",
    "json": "application/json",
    "html": "text/html",
    "rtf": "application/rtf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "heic": "image/heic",
    "heif": "image/heif",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "mkv": "video/x-matroska",
    "webm": "video/webm",
}


def _guess_mime_for_drive(ext: str) -> str:
    """Conservative mime guess — fallback application/octet-stream."""
    return _MIME_BY_EXT.get((ext or "").lower(), "application/octet-stream")
