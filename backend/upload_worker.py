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
# v10.0.3 — parallel worker concurrency. Default 4 parallel extracts so users
# uploading multiple files (esp. LlamaParse PDFs that block on remote poll) see
# them all running side-by-side instead of one-at-a-time queue head-of-line.
# Each worker task independently claims jobs via atomic UPDATE rowcount=1 so
# no double-claim risk.
WORKER_CONCURRENCY = int(os.getenv("UPLOAD_WORKER_CONCURRENCY", "4"))
# v10.0.0 -- transient errors (Gemini 503, network blips) re-queue up to N times
MAX_AUTO_RETRIES = int(os.getenv("UPLOAD_WORKER_MAX_AUTO_RETRIES", "3"))
STALE_EXTRACT_TIMEOUT_SEC = int(os.getenv("UPLOAD_STALE_TIMEOUT_SEC", "1800"))  # 30 min
MAX_RETRY_ATTEMPTS = int(os.getenv("UPLOAD_MAX_RETRY", "3"))
PROGRESS_DB_THROTTLE_SEC = 1.5  # อย่า update DB ถี่กว่านี้ — กัน lock
HEARTBEAT_FILE = Path(os.getenv("UPLOAD_HEARTBEAT_FILE", "data/worker_heartbeat.txt"))
HEARTBEAT_STALE_SEC = 30  # ถ้า heartbeat เก่ากว่านี้ → /healthz returns 503
WORKER_DISABLED = os.getenv("UPLOAD_WORKER_DISABLED", "").lower() in ("1", "true", "yes")

# ─── Module state ─────────────────────────────────────────────────────
_worker_task: Optional[asyncio.Task] = None
_worker_tasks: list = []  # v10.0.3 — parallel worker pool
_heartbeat_task: Optional[asyncio.Task] = None
_shutdown_event: Optional[asyncio.Event] = None
_worker_started_at: Optional[datetime] = None
# v9.4.6 — main event loop reference, captured at start_worker.
# Why: extract_text runs sync ใน thread pool via asyncio.to_thread → ใน thread
# นั้น asyncio.get_event_loop() return loop คนละตัว (or raises). progress callback
# ต้อง schedule กลับ main loop เพื่อ commit DB write. เก็บ main loop ที่ startup.
_main_loop: Optional[asyncio.AbstractEventLoop] = None

# Rolling average per priority class (TC-4 truthful estimated_wait)
# Updated atomically after each successful extract via update_avg_sec()
_AVG_EXTRACT_SEC: dict[int, float] = {1: 1.0, 2: 15.0, 3: 90.0}
_AVG_SAMPLE_COUNT: dict[int, int] = {1: 0, 2: 0, 3: 0}

# v9.4.8 — cap per-class duration ก่อนเข้า rolling avg.
# Why: PDF text (PyPDF2) ~3s vs PDF image-OCR (20 pages × 60s) ~1200s ใน class-2
# เดียวกัน → 1 OCR pull avg ไป 300+s → text PDF users เห็น estimate "5 นาที" ทั้งที่
# ของจริง ~3s. Cap = "outlier ไม่กระทบ typical-case estimate"
_AVG_CAP_SEC: dict[int, float] = {
    1: 5.0,     # fast (txt/code): cap 5s (anomaly = OS slow)
    2: 60.0,    # doc: cap 60s (text PDF ใช้ <30s, image-OCR > 60s = outlier)
    3: 300.0,   # av/img: cap 300s (Gemini Vision ~10s, video ~90s, huge video = outlier)
}

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
    """Update rolling avg ด้วย exponential smoothing (alpha=0.2).

    v9.4.8: cap duration ที่ _AVG_CAP_SEC[priority_class] ก่อนเข้า formula
    เพื่อกัน outlier (เช่น image-OCR PDF 20 หน้า ใช้ 1200s) ดึง avg ไปทำลาย
    estimate ของ typical case (text PDF ~3s).
    """
    if duration_sec < 0:
        return
    cap = _AVG_CAP_SEC.get(priority_class, duration_sec)
    capped = min(duration_sec, cap)
    cur = _AVG_EXTRACT_SEC.get(priority_class, capped)
    new = 0.8 * cur + 0.2 * capped
    _AVG_EXTRACT_SEC[priority_class] = round(new, 2)
    _AVG_SAMPLE_COUNT[priority_class] = _AVG_SAMPLE_COUNT.get(priority_class, 0) + 1


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

async def start_worker() -> None:
    """เรียกตอน FastAPI startup. Idempotent (no-op ถ้า worker รันอยู่แล้ว).

    Hatch: ตั้ง env UPLOAD_WORKER_DISABLED=true เพื่อปิด worker (rollback Tier 2).
    """
    global _worker_task, _heartbeat_task, _shutdown_event, _worker_started_at

    if WORKER_DISABLED:
        logger.warning("upload_worker.disabled — env UPLOAD_WORKER_DISABLED set")
        return

    if _worker_task and not _worker_task.done():
        logger.info("upload_worker.already_running — skip")
        return

    _shutdown_event = asyncio.Event()
    await _recover_stale_jobs()
    _worker_started_at = datetime.utcnow()
    # v9.4.6 — capture main loop reference สำหรับ cross-thread progress callbacks
    global _main_loop
    _main_loop = asyncio.get_running_loop()
    # v10.0.3 — spawn N parallel worker tasks instead of 1. Each task claims
    # via atomic UPDATE rowcount=1 so no race on duplicate work. Tasks running
    # LlamaParse (blocking REST poll inside thread) won't head-of-line other
    # users' fast uploads anymore.
    _worker_tasks.clear()
    for i in range(WORKER_CONCURRENCY):
        t = asyncio.create_task(_worker_loop(), name=f"upload_worker_{i}")
        _worker_tasks.append(t)
    # Backwards-compat alias — old callers reference _worker_task.
    _worker_task = _worker_tasks[0] if _worker_tasks else None
    # v9.4.5 — separate heartbeat task. เดิม heartbeat write ใน _worker_loop เท่านั้น →
    # job class-3 (video ~90s) ทำให้ heartbeat ค้างเกิน HEARTBEAT_STALE_SEC=30s →
    # /healthz return 503 + frontend show "ระบบประมวลผลหยุด" banner ทั้งที่ worker ยัง busy.
    _heartbeat_task = asyncio.create_task(_heartbeat_loop(), name="upload_heartbeat")
    logger.info(
        "upload_worker.started",
        extra={"event": "started", "concurrency": WORKER_CONCURRENCY},
    )


async def stop_worker() -> None:
    """เรียกตอน FastAPI shutdown. รอ task เสร็จ (max 5s) แล้วยอมแพ้."""
    if _shutdown_event:
        _shutdown_event.set()
    # v10.0.3 — stop all parallel worker tasks + heartbeat
    tasks: list = [(f"worker_{i}", t) for i, t in enumerate(_worker_tasks)]
    if _heartbeat_task:
        tasks.append(("heartbeat", _heartbeat_task))
    for name, task in tasks:
        if not task:
            continue
        try:
            await asyncio.wait_for(task, timeout=5.0)
            logger.info(f"upload_{name}.stopped")
        except asyncio.TimeoutError:
            logger.warning(f"upload_{name}.stop_timeout — task did not finish in 5s")


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
    elif _worker_tasks and all(t.done() for t in _worker_tasks):
        status = "crashed"
    else:
        status = "stopped"

    return {
        "status": status,
        "uptime_sec": uptime,
        "last_heartbeat": last_hb.isoformat() + "Z" if last_hb else None,
        "concurrency": WORKER_CONCURRENCY,
        "active_workers": sum(1 for t in _worker_tasks if not t.done()),
        "avg_extract_sec_by_class": {str(k): v for k, v in _AVG_EXTRACT_SEC.items()},
    }


# ═══════════════════════════════════════════════════════════════════
# Internal — main loop + claim + process
# ═══════════════════════════════════════════════════════════════════

async def _heartbeat_loop() -> None:
    """v9.4.5 — write heartbeat ทุก HEARTBEAT_INTERVAL_SEC bypass _worker_loop.

    Worker loop เขียน heartbeat ก่อน claim/process ของแต่ละ job. Job class-3 (video)
    ใช้ ~90s ต่อตัว → heartbeat ค้างเกิน HEARTBEAT_STALE_SEC=30s → /healthz บอก
    "stopped" + frontend banner เด้ง ทั้งที่ worker ยัง busy. แยก task นี้ทำให้
    heartbeat fresh ตลอดถ้า event loop ยัง responsive.
    """
    interval = max(1.0, HEARTBEAT_STALE_SEC / 6.0)  # 5s default (30/6)
    while not _shutdown_event.is_set():
        try:
            _write_heartbeat()
        except Exception as e:
            logger.warning(f"upload_heartbeat.write_failed (non-fatal): {e}")
        try:
            await asyncio.wait_for(_shutdown_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


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

        v9.4.6 fix: ใช้ _main_loop ที่ capture ตอน start_worker. เดิมเรียก
        asyncio.get_event_loop() ใน thread ที่ extract ทำงาน → ได้ loop คนละตัว
        (or RuntimeError ใน Py 3.12+) → run_coroutine_threadsafe schedule ลง loop
        ที่ไม่มี session → progress write ไม่ commit → tray UI ไม่ update.
        """
        nonlocal last_progress_write
        now = time.monotonic()
        if now - last_progress_write < PROGRESS_DB_THROTTLE_SEC:
            return
        last_progress_write = now
        if _main_loop is None:
            logger.debug("sync_report: main loop not captured yet")
            return
        try:
            asyncio.run_coroutine_threadsafe(
                _write_progress(file_id, step, pct), _main_loop,
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

        # v10.0.2 — HANDOFF Pattern G: collect non-fatal warnings emitted
        # during local-extract path (size, fallback, empty sheet, etc.).
        warnings_json: Optional[str] = None
        try:
            from .extraction import get_last_local_warnings
            warns = get_last_local_warnings()
            if warns:
                import json as _json
                warnings_json = _json.dumps(warns, ensure_ascii=False)
        except Exception:
            pass

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
                    extract_warnings=warnings_json,
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
        # v10.0.0 -- auto-retry on transient errors before giving up.
        # Without this, a single Gemini 503 or network blip permanently
        # marks the file as error and forces the user to click retry.
        code = format_user_error(e)
        TRANSIENT_CODES = {
            "GEMINI_UNAVAILABLE", "NETWORK", "TIMEOUT",
            "FILE_NOT_ACTIVE", "CLIENT_ERROR",
        }
        attempts = (job.get("attempt_count") or 0) + 1
        if code in TRANSIENT_CODES and attempts < MAX_AUTO_RETRIES:
            logger.warning(
                "upload_worker.transient_retry",
                extra={
                    "event": "transient_retry",
                    "file_id": file_id,
                    "code": code,
                    "attempt": attempts,
                    "max": MAX_AUTO_RETRIES,
                },
            )
            await _requeue_for_retry(file_id, attempts)
            return
        logger.error(
            "upload_worker.extract_failed",
            extra={
                "event": "extract_failed",
                "file_id": file_id,
                "duration_sec": round(duration, 2),
                "error_class": type(e).__name__,
                "error_message": str(e)[:200],
                "error_code": code,
                "attempt_count": attempts,
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


async def _requeue_for_retry(file_id: str, attempts: int) -> None:
    """v10.0.0 -- put a failed job back into the queue for one more try.

    Used when ``format_user_error`` returns a transient code (Gemini 503,
    network blip, timeout). The retry attempt is bumped on the row so we
    eventually give up after ``MAX_AUTO_RETRIES``.
    """
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(File).where(File.id == file_id).values(
                    processing_status="queued",
                    attempt_count=attempts,
                    extract_started_at=None,
                    progress_step=f"retry {attempts}/{MAX_AUTO_RETRIES}",
                    progress_pct=None,
                )
            )
            await db.commit()
    except Exception as e:
        logger.error(
            "upload_worker.requeue_failed",
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
    """Reset ALL 'extracting' rows → 'queued' ตอน startup.

    เดิม: cutoff 30 นาที → หลัง deploy/restart ไฟล์ที่ extracting < 30 นาที จะค้าง
    เพราะ worker ใหม่ skip + worker เก่าตายไปแล้ว.
    v9.4.5: ที่ startup ไม่มี worker ตัวอื่นแล้ว → ทุก 'extracting' = orphan ของ
    process เก่า → reset ทั้งหมด ไม่เช็คเวลา. Periodic stale sweep (ระหว่างรัน)
    ยังไม่มี — หากต้องการ implement แยก โดยใช้ STALE_EXTRACT_TIMEOUT_SEC.

    v10.0.0 -- also cleans "phantom queued" rows: queued rows whose raw_path
    is missing on disk.  Such rows can never succeed (worker raises
    FileNotFoundError forever), so we mark them as ``error`` with code
    FILE_MISSING up front.  This is the proactive safety net for the
    upload race fix in main.upload_files -- if a future regression
    re-introduces the race, the orphans get a clear error code at next
    startup instead of "queued forever".
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(File)
                .where(File.processing_status == "extracting")
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
                        "scope": "all_extracting_at_startup",
                    },
                )

            # v10.0.4 -- recover stale 'processing' status set by organize-new.
            # When organize-new crashes mid-pipeline (e.g., LLM timeout or DB
            # constraint), files get stuck at status='processing'. They're not
            # in the worker queue but also not browsable. Reset to 'uploaded'
            # so they show up normally + organize-new can retry.
            stale_processing = await db.execute(
                update(File)
                .where(
                    File.processing_status == "processing",
                    File.extracted_text != "",
                )
                .values(processing_status="uploaded")
            )
            await db.commit()
            if stale_processing.rowcount:
                logger.warning(
                    "upload_worker.recovered_stale_processing",
                    extra={
                        "event": "recovered_stale_processing",
                        "count": stale_processing.rowcount,
                        "scope": "organize_new_orphans",
                    },
                )

            # v10.0.0 -- phantom queued cleanup
            phantom_rows = (await db.execute(
                select(File.id, File.raw_path).where(File.processing_status == "queued")
            )).all()
            phantoms = [fid for fid, path in phantom_rows
                        if not path or not os.path.exists(path)]
            if phantoms:
                await db.execute(
                    update(File)
                    .where(File.id.in_(phantoms))
                    .values(
                        processing_status="error",
                        extraction_status="ocr_failed",
                        extract_error="FILE_MISSING",
                        extract_completed_at=datetime.utcnow(),
                        progress_step=None,
                        progress_pct=None,
                    )
                )
                await db.commit()
                logger.warning(
                    "upload_worker.phantom_queued_cleanup",
                    extra={
                        "event": "phantom_queued_cleanup",
                        "count": len(phantoms),
                        "scope": "queued_with_missing_raw_path",
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

    v10.0.0: check user.storage_mode FIRST -- previously we read the whole
    raw file into memory before checking BYOS, wasting 200MB of I/O for
    every non-BYOS upload.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Lazy import to keep startup light + avoid circulars
            from .storage_router import (
                _get_byos_user_with_connection,
                push_extracted_text_to_drive_if_byos,
                push_raw_file_to_drive_if_byos,
            )

            # 1) cheap DB lookup of File row
            row = await db.execute(select(File).where(File.id == file_id))
            f = row.scalar_one_or_none()
            if not f or not f.raw_path or not os.path.exists(f.raw_path):
                return

            # 2) cheap BYOS check BEFORE expensive file read.
            #    Non-BYOS users (default) bail here -- no disk I/O wasted.
            pair = await _get_byos_user_with_connection(f.user_id, db)
            if not pair:
                return

            # 3) BYOS user: read file + push to Drive
            def _read_file_bytes(path: str) -> bytes:
                with open(path, "rb") as fp:
                    return fp.read()
            contents = await asyncio.to_thread(_read_file_bytes, f.raw_path)
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
